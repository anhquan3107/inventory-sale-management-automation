from collections import defaultdict
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models.forecast_accuracy import ForecastAccuracy
from models.forecast_prediction import ForecastPrediction
from models.forecast_run import ForecastRun
from models.product import Product
from models.replenishment import InventoryRecommendation, ReplenishmentPolicy
from schemas.inventory_exceptions import (
    ExceptionClassification, ExceptionMode, InventoryException, InventoryExceptionPage, ReviewStatus,
)
from services.recommendation_diagnostics import DIAGNOSTICS_RULES_VERSION
from services.replenishment import snapshot_diagnostics, validate_forecast_periods


PRIORITY = {
    "shortage_within_lead_time": 0,
    "shortage_after_lead_time": 1,
    "planned_replenishment": 2,
    "excess_stock_review": 3,
    "insufficient_evidence": 4,
    "unsupported_snapshot": 4,
    "not_generated": 4,
    "no_exception": 5,
}

EVIDENCE_REASONS = {
    "unknown_coverage": "Sales coverage was unknown for this forecast.",
    "coverage_ends_before_cutoff": "Sales coverage ended before the forecast cutoff.",
    "insufficient_history": "The forecast had insufficient sales history.",
    "no_sales_signal": "The covered sales history had no recorded demand.",
}


def list_exceptions(
    db: Session,
    run: ForecastRun,
    mode: ExceptionMode,
    limit: int,
    offset: int,
    classification: ExceptionClassification | None,
    review_status: ReviewStatus | None,
) -> InventoryExceptionPage:
    accuracy = {row.product_id: row for row in db.scalars(select(ForecastAccuracy).where(
        ForecastAccuracy.run_ref_id == run.id, ForecastAccuracy.granularity == "weekly"))}
    settings = run.settings or {}
    product_ids = settings.get("product_ids")
    if product_ids is None:
        predicted_ids = db.scalars(select(ForecastPrediction.product_id).where(
            ForecastPrediction.run_ref_id == run.id, ForecastPrediction.granularity == "weekly").distinct())
        product_ids = set(accuracy).union(predicted_ids)

    # The mode lives in the existing JSON snapshot. Pick the newest row before applying review filters.
    recommendations = InventoryRecommendation
    saved_mode = func.coalesce(recommendations.snapshot["mode"].as_string(),
                               recommendations.snapshot["request"]["mode"].as_string())
    latest_ids = select(func.max(recommendations.id)).where(
        recommendations.run_ref_id == run.id, recommendations.product_id.in_(product_ids),
        saved_mode == mode).group_by(recommendations.product_id)
    latest = {row.product_id: row for row in db.scalars(select(recommendations).where(
        recommendations.id.in_(latest_ids)))}
    products = list(db.scalars(select(Product).where(Product.id.in_(product_ids))))

    needs_forecast = set(product_ids) - latest.keys()
    predictions = defaultdict(list)
    if needs_forecast:
        for row in db.scalars(select(ForecastPrediction).where(
            ForecastPrediction.run_ref_id == run.id, ForecastPrediction.granularity == "weekly",
            ForecastPrediction.product_id.in_(needs_forecast)).order_by(ForecastPrediction.horizon_step)):
            predictions[row.product_id].append(row)
    policies = {row.product_id: row for row in db.scalars(select(ReplenishmentPolicy).where(
        ReplenishmentPolicy.product_id.in_(needs_forecast)))} if needs_forecast else {}

    items = [classify_exception(product, latest.get(product.id), run, accuracy.get(product.id),
                                predictions.get(product.id, []), policies.get(product.id)) for product in products]
    matching = [item for item in items if (classification is None or item.classification == classification)
                and (review_status is None or item.review_status == review_status)]
    matching.sort(key=lambda item: (PRIORITY[item.classification], item.first_shortage_step or 0, item.product_id))
    return InventoryExceptionPage(run_id=run.run_id, as_of_date=run.as_of_date, mode=mode,
                                  rules_version=DIAGNOSTICS_RULES_VERSION, total=len(matching), scope_total=len(items),
                                  missing_recommendations=sum(item.recommendation_id is None for item in items),
                                  items=matching[offset:offset + limit])


def classify_exception(
    product: Product,
    recommendation: InventoryRecommendation | None,
    run: ForecastRun,
    accuracy: ForecastAccuracy | None,
    predictions: list[ForecastPrediction],
    policy: ReplenishmentPolicy | None,
) -> InventoryException:
    reasons = [] if product.is_active else ["This product is inactive."]
    item = InventoryException(product_id=product.id, sku=product.sku, product_name=product.name,
                              product_active=product.is_active,
                              recommendation_id=recommendation.id if recommendation else None,
                              review_status=recommendation.status if recommendation else None,
                              classification="insufficient_evidence", reasons=reasons,
                              data_basis="saved_recommendation_snapshot" if recommendation else "forecast_run")
    if not run.as_of_date or run.as_of_date.weekday() != 0 or (run.settings or {}).get("version") != "baseline-v2":
        item.reasons.append("This forecast run is unsupported for weekly recommendations.")
        return item
    status = (accuracy.details or {}).get("status") if accuracy else None
    if status != "evaluated":
        item.reasons.append(EVIDENCE_REASONS.get(status, "Evaluated weekly forecast evidence is unavailable."))
        return item

    if recommendation is None:
        if not predictions or (policy and len(predictions) < policy.lead_time_weeks + policy.review_interval_weeks):
            item.reasons.append("Weekly predictions are missing or the horizon is too short for the saved policy.")
            return item
        try:
            validate_forecast_periods(predictions, run.as_of_date)
        except ValueError:
            item.reasons.append("Weekly forecast periods are not consecutive from the review date.")
            return item
        item.classification = "not_generated"
        item.reasons.append("No recommendation has been generated for this run and mode.")
        if policy is None:
            item.reasons.append("A replenishment policy is required to generate a recommendation.")
        return item

    diagnostic = snapshot_diagnostics(recommendation.snapshot)
    if diagnostic["status"] != "available":
        item.classification = "unsupported_snapshot"
        item.reasons.append("The saved recommendation has incomplete diagnostic evidence.")
        return item

    item.first_shortage_step = diagnostic["first_shortage_step"]
    if diagnostic["first_shortage_period_start"] is not None:
        item.first_shortage_period_start = date.fromisoformat(diagnostic["first_shortage_period_start"])
    item.first_shortage_quantity = diagnostic["first_shortage_quantity"]
    item.maximum_projected_deficit = diagnostic["maximum_projected_deficit"]
    item.shortage_during_lead_time = diagnostic["shortage_during_lead_time"]
    item.excess_stock_review = diagnostic["excess_stock_review"]
    item.zero_demand_stock_review = diagnostic["zero_demand_stock_review"]
    item.suggested_quantity = recommendation.suggested_quantity

    if item.first_shortage_period_start:
        item.classification = "shortage_within_lead_time" if item.shortage_during_lead_time else "shortage_after_lead_time"
        timing = "within lead time" if item.shortage_during_lead_time else "after lead time"
        item.reasons.append(f"Projected shortage of {item.first_shortage_quantity} units in the week beginning "
                            f"{item.first_shortage_period_start}, {timing}.")
    elif item.suggested_quantity > 0:
        item.classification = "planned_replenishment"
        item.reasons.append("Inventory position is below target, with no projected shortage in the protection period.")
    elif item.excess_stock_review or item.zero_demand_stock_review:
        item.classification = "excess_stock_review"
    else:
        item.classification = "no_exception"
        item.reasons.append("No shortage, replenishment order, or excess-stock flag is projected.")

    if item.excess_stock_review:
        item.reasons.append(f"Inventory position exceeds the review threshold of {diagnostic['excess_stock_threshold']} "
                            f"units ({diagnostic['excess_stock_factor']} times target stock).")
    if item.zero_demand_stock_review:
        item.reasons.append("Inventory position is positive with a target stock of zero.")
    return item
