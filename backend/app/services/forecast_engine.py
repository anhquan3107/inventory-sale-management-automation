from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.forecast_accuracy import ForecastAccuracy
from models.forecast_evidence import ForecastBacktestPoint
from models.forecast_prediction import ForecastPrediction
from models.forecast_run import ForecastRun
from models.product import Product
from services.forecast_data_prep import add_period, get_history, list_active_product_ids, period_start
from services.forecast_evaluation import MODEL_CONFIG, evaluate, predict


def _decimal(value):
    return None if value is None else Decimal(str(round(value, 4)))


def generate_forecast_run(db: Session, generated_by_user_id: int, weekly_horizon: int,
                          monthly_horizon: int, product_ids: list[int] | None = None,
                          as_of_date: date | None = None) -> dict:
    as_of_date = as_of_date or date.today()
    if as_of_date > date.today():
        raise ValueError("as_of_date cannot be in the future")
    if not (1 <= weekly_horizon <= 26 and 1 <= monthly_horizon <= 24):
        raise ValueError("Invalid forecast horizons")
    try:
        ids = list_active_product_ids(db, product_ids)
        if not ids:
            raise ValueError("No active products available for forecasting")
        run = ForecastRun(run_id=str(uuid4()), weekly_horizon=weekly_horizon,
                          monthly_horizon=monthly_horizon, total_products=len(ids),
                          generated_by_user_id=generated_by_user_id, status="completed", as_of_date=as_of_date,
                          settings={"version": "baseline-v2", "models": MODEL_CONFIG,
                                    "selection_metric": "validation_mae", "test": "last_full_horizon",
                                    "interval_method": "not_calibrated_bounds_omitted",
                                    "date_basis": "UTC calendar date", "product_ids": ids})
        db.add(run)
        db.flush()
        count = 0
        unavailable = 0
        for product_id in ids:
            for granularity, horizon in (("weekly", weekly_horizon), ("monthly", monthly_horizon)):
                prepared = get_history(db, product_id, granularity, as_of_date)
                rows = prepared.pop("rows")
                evaluation = evaluate(rows, horizon, granularity)
                if prepared["status"] != "ready":
                    evaluation["status"] = prepared["status"]
                selected = evaluation["selected_model"]
                details = {**prepared, "status": evaluation["status"],
                           "nonzero_points": sum(r["quantity"] > 0 for r in rows),
                           "history": [{"period_start": r["period_start"].isoformat(), "quantity": r["quantity"]}
                                       for r in rows],
                           "comparison": evaluation["comparison"],
                           "selection_metric": "validation_mae", "accuracy_split": "test",
                           "interval_method": "unavailable_until_calibrated"}
                score = evaluation["test_metrics"]
                db.add(ForecastAccuracy(run_ref_id=run.id, product_id=product_id, granularity=granularity,
                                       selected_model=selected, training_points=len(rows), details=details,
                                       mae=_decimal(score["mae"]), rmse=_decimal(score["rmse"]), mape=_decimal(score["mape"])))
                for point in evaluation["points"]:
                    db.add(ForecastBacktestPoint(run_ref_id=run.id, product_id=product_id,
                                                granularity=granularity, **point))
                if selected == "unavailable":
                    unavailable += 1
                    continue
                forecasts = predict([r["quantity"] for r in rows], horizon, selected)
                start = period_start(as_of_date, granularity)
                for step, quantity in enumerate(forecasts, start=1):
                    target = add_period(start, granularity, step - 1)
                    db.add(ForecastPrediction(run_ref_id=run.id, product_id=product_id,
                           granularity=granularity, period_start=target,
                           period_end=add_period(target, granularity) - timedelta(days=1),
                           horizon_step=step, selected_model=selected,
                           predicted_quantity=Decimal(str(round(quantity, 2))),
                           confidence_lower=None, confidence_upper=None,
                           fallback_reason=None if evaluation["status"] == "evaluated" else evaluation["status"]))
                    count += 1
        db.commit()
        db.refresh(run)
        return {"run_id": run.run_id, "generated_at": run.generated_at,
                "as_of_date": run.as_of_date, "total_products": len(ids),
                "forecasts_created": count, "unavailable_series": unavailable}
    except Exception:
        db.rollback()
        raise


def resolve_run(db: Session, run_id: str | None) -> ForecastRun:
    stmt = select(ForecastRun)
    stmt = stmt.where(ForecastRun.run_id == run_id) if run_id else stmt.order_by(ForecastRun.id.desc()).limit(1)
    run = db.scalar(stmt)
    if run is None:
        raise ValueError("Forecast run not found")
    return run


def _list(db, model, granularity, run_id, product_id=None):
    run = resolve_run(db, run_id)
    stmt = select(model, Product.name, Product.sku).join(Product, Product.id == model.product_id).where(
        model.run_ref_id == run.id, model.granularity == granularity).order_by(model.product_id, model.id)
    if product_id is not None:
        stmt = stmt.where(model.product_id == product_id)
    items = []
    for obj, name, sku in db.execute(stmt):
        item = {column.name: getattr(obj, column.name) for column in model.__table__.columns
                if column.name not in {"id", "run_ref_id", "created_at"}}
        item.update(product_name=name, product_sku=sku)
        items.append(item)
    return {"run_id": run.run_id, "generated_at": run.generated_at, "as_of_date": run.as_of_date,
            "granularity": granularity, "items": items}


def list_forecast_predictions(db, granularity, run_id=None, product_id=None):
    return _list(db, ForecastPrediction, granularity, run_id, product_id)


def list_forecast_accuracy(db, granularity, run_id=None):
    return _list(db, ForecastAccuracy, granularity, run_id)


def list_backtest_points(db, run_id, product_id, granularity, limit=500, offset=0):
    run = resolve_run(db, run_id)
    points = db.scalars(select(ForecastBacktestPoint).where(
        ForecastBacktestPoint.run_ref_id == run.id, ForecastBacktestPoint.product_id == product_id,
        ForecastBacktestPoint.granularity == granularity).order_by(ForecastBacktestPoint.id).limit(limit).offset(offset))
    return [{c.name: getattr(p, c.name) for c in ForecastBacktestPoint.__table__.columns} for p in points]
