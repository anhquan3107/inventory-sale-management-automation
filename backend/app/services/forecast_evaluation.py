"""Pure forecasting and chronological evaluation functions shared by tests and API."""
from math import sqrt
from statistics import mean


MODEL_NAMES = ("naive", "moving_average", "exponential_smoothing")
MODEL_CONFIG = {"moving_average_window": 4, "smoothing_alpha": 0.35}


def predict(history: list[float], horizon: int, model_name: str) -> list[float]:
    if not history or horizon < 1 or model_name not in MODEL_NAMES:
        raise ValueError("A supported model, nonempty history, and positive horizon are required")
    if any(value < 0 for value in history):
        raise ValueError("Sales quantities must be nonnegative")
    if model_name == "naive":
        return [history[-1]] * horizon
    if model_name == "exponential_smoothing":
        level = history[0]
        for value in history[1:]:
            level = 0.35 * value + 0.65 * level
        return [level] * horizon
    values = history[:]
    predictions = []
    for _ in range(horizon):
        prediction = mean(values[-4:])
        predictions.append(prediction)
        values.append(prediction)
    return predictions


def metrics(points: list[dict]) -> dict:
    if not points:
        return dict(mae=None, rmse=None, mape=None, bias=None, wape=None, points=0)
    errors = [p["predicted"] - p["actual"] for p in points]
    nonzero = [p for p in points if p["actual"] != 0]
    total = sum(p["actual"] for p in points)
    return {
        "mae": mean(abs(e) for e in errors),
        "rmse": sqrt(mean(e * e for e in errors)),
        "mape": mean(abs((p["predicted"] - p["actual"]) / p["actual"])
                     for p in nonzero) * 100 if nonzero else None,
        "bias": mean(errors),
        "wape": sum(abs(e) for e in errors) / total * 100 if total else None,
        "points": len(points),
    }


def evaluate(history: list[dict], horizon: int, granularity: str) -> dict:
    values = [row["quantity"] for row in history]
    minimum = 8 if granularity == "weekly" else 4
    result = {"status": "insufficient_history", "selected_model": "unavailable",
              "points": [], "comparison": {}, "test_metrics": metrics([])}
    if len(values) < minimum:
        return result
    if not any(values):
        result["status"] = "no_sales_signal"
        return result
    result.update(status="insufficient_evaluation", selected_model="moving_average")
    test_start = len(values) - horizon
    origins = sorted(i for i in (test_start - horizon * k for k in (1, 2, 3)) if i >= minimum)
    if not origins:
        return result
    points = []
    comparison = {}
    for name in MODEL_NAMES:
        for split, starts in (("validation", origins), ("test", [test_start])):
            for origin in starts:
                forecasts = predict(values[:origin], horizon, name)
                for step, forecast in enumerate(forecasts, start=1):
                    points.append({"model_name": name, "split": split,
                                   "origin": history[origin]["period_start"],
                                   "target_period": history[origin + step - 1]["period_start"],
                                   "horizon_step": step, "actual": values[origin + step - 1],
                                   "predicted": forecast})
        model_points = [p for p in points if p["model_name"] == name]
        comparison[name] = {
            split: {
                "overall": metrics([p for p in model_points if p["split"] == split]),
                "by_horizon": {str(h): metrics([p for p in model_points
                                                if p["split"] == split and p["horizon_step"] == h])
                               for h in range(1, horizon + 1)},
            } for split in ("validation", "test")
        }
    # Only validation chooses the winner; final test results never influence selection.
    selected = min(MODEL_NAMES, key=lambda name: comparison[name]["validation"]["overall"]["mae"])
    result.update(status="evaluated", selected_model=selected, points=points, comparison=comparison,
                  test_metrics=comparison[selected]["test"]["overall"])
    return result
