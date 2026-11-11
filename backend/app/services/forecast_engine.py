from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from math import sqrt
from statistics import mean, pstdev
from uuid import uuid4

from sqlalchemy import desc, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from models.forecast_accuracy import ForecastAccuracy
from models.forecast_prediction import ForecastPrediction
from models.forecast_run import ForecastRun
from models.product import Product
from services.forecast_data_prep import (
    build_future_periods,
    get_period_demand_history,
    list_active_product_ids,
)


def _moving_average_next(history: list[float], window: int) -> float:
    if not history:
        return 0.0
    return mean(history[-window:])


def _moving_average_forecast(history: list[float], horizon: int, window: int) -> tuple[list[float], float]:
    values = history[:]
    predictions: list[float] = []

    for _ in range(horizon):
        pred = _moving_average_next(values, window)
        predictions.append(max(0.0, pred))
        values.append(pred)

    residuals: list[float] = []
    for idx in range(1, len(history)):
        pred = _moving_average_next(history[:idx], window)
        residuals.append(history[idx] - pred)

    sigma = pstdev(residuals) if len(residuals) > 1 else 0.0
    return predictions, sigma


def _exponential_smoothing_forecast(
    history: list[float],
    horizon: int,
    alpha: float = 0.35,
) -> tuple[list[float], float]:
    if not history:
        return [0.0 for _ in range(horizon)], 0.0

    level = history[0]
    residuals: list[float] = []

    for value in history[1:]:
        forecast = level
        residuals.append(value - forecast)
        level = alpha * value + (1 - alpha) * level

    predictions = [max(0.0, level) for _ in range(horizon)]
    sigma = pstdev(residuals) if len(residuals) > 1 else 0.0
    return predictions, sigma


def _mape(actuals: list[float], predictions: list[float]) -> float | None:
    ape: list[float] = []

    for actual, pred in zip(actuals, predictions):
        if actual == 0:
            continue
        ape.append(abs((actual - pred) / actual))

    if not ape:
        return None

    return mean(ape) * 100


def _mae(actuals: list[float], predictions: list[float]) -> float:
    if not actuals:
        return 0.0
    return mean([abs(actual - pred) for actual, pred in zip(actuals, predictions)])


def _rmse(actuals: list[float], predictions: list[float]) -> float:
    if not actuals:
        return 0.0
    mse = mean([(actual - pred) ** 2 for actual, pred in zip(actuals, predictions)])
    return sqrt(mse)


def _rolling_backtest(history: list[float], model_name: str, granularity: str) -> dict:
    if len(history) < 6:
        return {
            "mape": None,
            "mae": 0.0,
            "rmse": 0.0,
        }

    test_size = max(2, min(8, len(history) // 4))
    if granularity == "monthly":
        test_size = max(2, min(4, len(history) // 3))

    start_idx = len(history) - test_size
    actuals: list[float] = []
    predictions: list[float] = []

    for idx in range(start_idx, len(history)):
        train = history[:idx]

        if model_name == "moving_average":
            prediction = _moving_average_next(train, window=4)
        else:
            prediction = _exponential_smoothing_forecast(train, horizon=1)[0][0]

        actuals.append(history[idx])
        predictions.append(max(0.0, prediction))

    return {
        "mape": _mape(actuals, predictions),
        "mae": _mae(actuals, predictions),
        "rmse": _rmse(actuals, predictions),
    }


def _select_model(history: list[float], granularity: str) -> tuple[str, dict, str | None]:
    if len(history) < 12:
        metrics = _rolling_backtest(history, "moving_average", granularity)
        return "moving_average", metrics, "Insufficient history for exponential smoothing champion check"

    ma_metrics = _rolling_backtest(history, "moving_average", granularity)
    es_metrics = _rolling_backtest(history, "exponential_smoothing", granularity)

    ma_mape = ma_metrics["mape"]
    es_mape = es_metrics["mape"]

    if ma_mape is None and es_mape is None:
        if ma_metrics["mae"] <= es_metrics["mae"]:
            return "moving_average", ma_metrics, None
        return "exponential_smoothing", es_metrics, None

    if ma_mape is None:
        return "exponential_smoothing", es_metrics, None

    if es_mape is None:
        return "moving_average", ma_metrics, None

    if ma_mape < es_mape:
        return "moving_average", ma_metrics, None

    if es_mape < ma_mape:
        return "exponential_smoothing", es_metrics, None

    if ma_metrics["mae"] <= es_metrics["mae"]:
        return "moving_average", ma_metrics, None

    return "exponential_smoothing", es_metrics, None


def _predict_with_model(history: list[float], model_name: str, horizon: int) -> tuple[list[float], list[tuple[float, float]]]:
    if model_name == "moving_average":
        predictions, sigma = _moving_average_forecast(history, horizon, window=4)
    else:
        predictions, sigma = _exponential_smoothing_forecast(history, horizon)

    bounds: list[tuple[float, float]] = []
    for step, pred in enumerate(predictions, start=1):
        spread = 1.96 * sigma * sqrt(step)
        lower = max(0.0, pred - spread)
        upper = max(0.0, pred + spread)
        bounds.append((lower, upper))

    return predictions, bounds


def _to_decimal(value: float | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(round(value, 4)))


def generate_forecast_run(
    db: Session,
    generated_by_user_id: int,
    weekly_horizon: int,
    monthly_horizon: int,
    product_ids: list[int] | None = None,
) -> dict:
    try:
        target_product_ids = list_active_product_ids(db, product_ids)
        if not target_product_ids:
            raise ValueError("No active products available for forecasting")

        run = ForecastRun(
            run_id=str(uuid4()),
            weekly_horizon=weekly_horizon,
            monthly_horizon=monthly_horizon,
            total_products=len(target_product_ids),
            generated_by_user_id=generated_by_user_id,
            status="completed",
        )
        db.add(run)
        db.flush()

        forecasts_created = 0

        horizons = {
            "weekly": weekly_horizon,
            "monthly": monthly_horizon,
        }
        periods_back = {
            "weekly": max(56, weekly_horizon * 4),
            "monthly": max(24, monthly_horizon * 3),
        }

        for product_id in target_product_ids:
            for granularity, horizon in horizons.items():
                history_rows = get_period_demand_history(
                    db=db,
                    product_id=product_id,
                    granularity=granularity,
                    periods_back=periods_back[granularity],
                )
                history_values = [row["quantity"] for row in history_rows]

                selected_model, metrics, fallback_reason = _select_model(history_values, granularity)
                predictions, bounds = _predict_with_model(history_values, selected_model, horizon)
                future_periods = build_future_periods(history_rows[-1]["period_start"], granularity, horizon)

                for step, (period_start, period_end) in enumerate(future_periods, start=1):
                    lower, upper = bounds[step - 1]
                    db.add(
                        ForecastPrediction(
                            run_ref_id=run.id,
                            product_id=product_id,
                            granularity=granularity,
                            period_start=period_start,
                            period_end=period_end,
                            horizon_step=step,
                            selected_model=selected_model,
                            predicted_quantity=Decimal(str(round(predictions[step - 1], 2))),
                            confidence_lower=Decimal(str(round(lower, 2))),
                            confidence_upper=Decimal(str(round(upper, 2))),
                            fallback_reason=fallback_reason,
                        )
                    )
                    forecasts_created += 1

                db.add(
                    ForecastAccuracy(
                        run_ref_id=run.id,
                        product_id=product_id,
                        granularity=granularity,
                        selected_model=selected_model,
                        mape=_to_decimal(metrics["mape"]),
                        mae=_to_decimal(metrics["mae"]),
                        rmse=_to_decimal(metrics["rmse"]),
                        training_points=len(history_values),
                    )
                )

        db.commit()
        db.refresh(run)

        return {
            "run_id": run.run_id,
            "generated_at": run.generated_at,
            "total_products": run.total_products,
            "forecasts_created": forecasts_created,
        }

    except (SQLAlchemyError, ValueError):
        db.rollback()
        raise


def _resolve_run(db: Session, run_id: str | None) -> ForecastRun:
    if run_id:
        stmt = select(ForecastRun).where(ForecastRun.run_id == run_id)
        run = db.execute(stmt).scalars().first()
        if not run:
            raise ValueError("Forecast run not found")
        return run

    stmt_latest = select(ForecastRun).order_by(desc(ForecastRun.generated_at)).limit(1)
    run = db.execute(stmt_latest).scalars().first()
    if not run:
        raise ValueError("No forecast runs available")
    return run


def list_forecast_predictions(
    db: Session,
    granularity: str,
    run_id: str | None = None,
    product_id: int | None = None,
) -> dict:
    if granularity not in {"weekly", "monthly"}:
        raise ValueError("Unsupported granularity")

    run = _resolve_run(db, run_id)

    stmt = (
        select(
            ForecastPrediction,
            Product.name.label("product_name"),
            Product.sku.label("product_sku"),
        )
        .join(Product, ForecastPrediction.product_id == Product.id)
        .where(
            ForecastPrediction.run_ref_id == run.id,
            ForecastPrediction.granularity == granularity,
        )
        .order_by(ForecastPrediction.product_id, ForecastPrediction.horizon_step)
    )

    if product_id is not None:
        stmt = stmt.where(ForecastPrediction.product_id == product_id)

    rows = db.execute(stmt).all()

    items = [
        {
            "product_id": row.ForecastPrediction.product_id,
            "product_name": row.product_name,
            "product_sku": row.product_sku,
            "granularity": row.ForecastPrediction.granularity,
            "period_start": row.ForecastPrediction.period_start,
            "period_end": row.ForecastPrediction.period_end,
            "horizon_step": row.ForecastPrediction.horizon_step,
            "selected_model": row.ForecastPrediction.selected_model,
            "predicted_quantity": row.ForecastPrediction.predicted_quantity,
            "confidence_lower": row.ForecastPrediction.confidence_lower,
            "confidence_upper": row.ForecastPrediction.confidence_upper,
            "fallback_reason": row.ForecastPrediction.fallback_reason,
        }
        for row in rows
    ]

    return {
        "run_id": run.run_id,
        "generated_at": run.generated_at,
        "granularity": granularity,
        "items": items,
    }


def list_forecast_accuracy(
    db: Session,
    granularity: str,
    run_id: str | None = None,
) -> dict:
    if granularity not in {"weekly", "monthly"}:
        raise ValueError("Unsupported granularity")

    run = _resolve_run(db, run_id)

    stmt = (
        select(
            ForecastAccuracy,
            Product.name.label("product_name"),
            Product.sku.label("product_sku"),
        )
        .join(Product, ForecastAccuracy.product_id == Product.id)
        .where(
            ForecastAccuracy.run_ref_id == run.id,
            ForecastAccuracy.granularity == granularity,
        )
        .order_by(ForecastAccuracy.product_id)
    )

    rows = db.execute(stmt).all()

    items = [
        {
            "product_id": row.ForecastAccuracy.product_id,
            "product_name": row.product_name,
            "product_sku": row.product_sku,
            "granularity": row.ForecastAccuracy.granularity,
            "selected_model": row.ForecastAccuracy.selected_model,
            "mape": row.ForecastAccuracy.mape,
            "mae": row.ForecastAccuracy.mae,
            "rmse": row.ForecastAccuracy.rmse,
            "training_points": row.ForecastAccuracy.training_points,
        }
        for row in rows
    ]

    return {
        "run_id": run.run_id,
        "generated_at": run.generated_at,
        "granularity": granularity,
        "items": items,
    }
