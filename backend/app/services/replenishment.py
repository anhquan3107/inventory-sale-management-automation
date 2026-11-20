from datetime import date, timedelta
from decimal import Decimal, ROUND_CEILING

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.forecast_accuracy import ForecastAccuracy
from models.forecast_prediction import ForecastPrediction
from models.inventory import Inventory
from models.product import Product
from models.replenishment import InventoryRecommendation, RecommendationDecision, ReplenishmentPolicy
from services.forecast_engine import resolve_run


def calculate_replenishment(forecasts: list[Decimal], on_hand: int, receipts: list[dict], policy: dict) -> dict:
    lead = policy["lead_time_weeks"]
    protection = lead + policy["review_interval_weeks"]
    if len(forecasts) < protection:
        raise ValueError("Forecast does not cover lead time plus review interval")
    if on_hand < 0 or any(r["quantity"] <= 0 or r["arrival_week"] < 1 for r in receipts):
        raise ValueError("Invalid inventory inputs")
    incoming = sum(r["quantity"] for r in receipts)
    position = on_hand + incoming
    demand = sum(forecasts[:protection], Decimal(0))
    target = demand + policy["safety_stock"]
    shortage = max(Decimal(0), target - position)
    quantity = int(shortage.to_integral_value(rounding=ROUND_CEILING))
    if quantity:
        quantity = max(quantity, policy["minimum_order_quantity"])
        pack = policy["pack_size"]
        quantity = ((quantity + pack - 1) // pack) * pack
    # Receipts arrive at the start of their numbered week; new suggested orders are excluded.
    balance = Decimal(on_hand)
    projected = []
    for week in range(1, protection + 1):
        balance += sum(r["quantity"] for r in receipts if r["arrival_week"] == week)
        balance -= forecasts[week - 1]
        projected.append(str(balance))
    risk = any(Decimal(value) < 0 for value in projected)
    return {"inventory_position": position, "protection_weeks": protection,
            "lead_time_demand": str(sum(forecasts[:lead], Decimal(0))),
            "protection_demand": str(demand), "target_stock": str(target),
            "suggested_quantity": quantity, "action": "reorder" if quantity else "no_action",
            "stockout_risk": risk, "projected_week_end_stock": projected,
            "explanation": f"Weekly periodic review: target {target} minus inventory position {position}; "
                           f"order {quantity} after MOQ and pack rounding. "
                           "Stockout risk uses existing receipts only, not the suggested order."}


def policy_dict(policy):
    return {c.name: getattr(policy, c.name) for c in ReplenishmentPolicy.__table__.columns}


def put_policy(db: Session, product_id: int, values: dict):
    product = db.scalar(select(Product).where(Product.id == product_id).with_for_update())
    if product is None or not product.is_active:
        raise ValueError("Active product not found")
    row = db.get(ReplenishmentPolicy, product_id)
    if row is None:
        row = ReplenishmentPolicy(product_id=product_id, version=1, **values)
        db.add(row)
    elif any(getattr(row, k) != v for k, v in values.items()):
        for key, value in values.items():
            setattr(row, key, value)
        row.version += 1
    db.commit()
    return policy_dict(row)


def serialize_recommendation(row, decision=None):
    result = {c.name: getattr(row, c.name) for c in InventoryRecommendation.__table__.columns}
    result["decision"] = ({c.name: getattr(decision, c.name) for c in RecommendationDecision.__table__.columns}
                          if decision else None)
    return result


def generate_recommendation(db: Session, payload: dict, user_id: int):
    # Product lock serializes duplicate generation requests for the same product.
    product = db.scalar(select(Product).where(Product.id == payload["product_id"]).with_for_update())
    if product is None or not product.is_active:
        raise ValueError("Active product not found")
    existing = db.scalar(select(InventoryRecommendation).where(
        InventoryRecommendation.request_key == payload["request_key"]))
    if existing:
        if existing.snapshot["request"] != payload:
            raise ValueError("request_key already belongs to different inputs")
        decision = db.scalar(select(RecommendationDecision).where(
            RecommendationDecision.recommendation_id == existing.id))
        return serialize_recommendation(existing, decision)
    run = resolve_run(db, payload["run_id"])
    if run.as_of_date is None or not run.settings or run.settings.get("version") != "baseline-v2":
        raise ValueError("Generate a baseline-v2 forecast first; legacy runs cannot drive recommendations")
    if run.as_of_date.weekday() != 0:
        raise ValueError("Weekly decisions require a Monday as_of_date; partial-week decisions are not supported")
    policy = db.scalar(select(ReplenishmentPolicy).where(
        ReplenishmentPolicy.product_id == product.id).with_for_update())
    if policy is None:
        raise ValueError("Configure a replenishment policy first")
    accuracy = db.scalar(select(ForecastAccuracy).where(
        ForecastAccuracy.run_ref_id == run.id, ForecastAccuracy.product_id == product.id,
        ForecastAccuracy.granularity == "weekly"))
    if accuracy is None or not accuracy.details or accuracy.details.get("status") != "evaluated":
        raise ValueError("An evaluated weekly forecast is required; insufficient/unknown history cannot drive orders")
    inventory = None
    if payload["mode"] == "live":
        if run.as_of_date != date.today():
            raise ValueError("Live decisions require a forecast for today's Monday review")
        if not payload.get("confirms_no_incoming_orders"):
            raise ValueError("Confirm that no incoming supplier orders exist before using live mode")
        inventory = db.scalar(select(Inventory).where(Inventory.product_id == product.id).with_for_update())
        if inventory is None:
            raise ValueError("Inventory not initialized")
        on_hand = inventory.quantity_on_hand
    else:
        on_hand = payload["simulated_on_hand"]
    forecasts = list(db.scalars(select(ForecastPrediction).where(
        ForecastPrediction.run_ref_id == run.id, ForecastPrediction.product_id == product.id,
        ForecastPrediction.granularity == "weekly").order_by(ForecastPrediction.horizon_step)))
    for idx, row in enumerate(forecasts):
        if row.period_start != run.as_of_date + timedelta(weeks=idx):
            raise ValueError("Forecast periods are not contiguous with the decision date")
    values = policy_dict(policy)
    result = calculate_replenishment([row.predicted_quantity for row in forecasts], on_hand,
                                      payload["simulated_receipts"], values)
    snapshot = {"request": payload, "policy": values, "on_hand": on_hand,
                "committed": 0, "commitment_assumption": "Completed sales already deducted; reservations unsupported",
                "decision_date": run.as_of_date.isoformat(), "mode": payload["mode"],
                "forecast": [{"period_start": f.period_start.isoformat(), "quantity": str(f.predicted_quantity)}
                             for f in forecasts],
                "model": accuracy.selected_model, "dataset_version": accuracy.details.get("dataset_version"),
                "result": result, "policy_type": "weekly_periodic_review_v1",
                "warning": "Advisory only. No purchase order or stock mutation. Receipt timing is weekly."}
    row = InventoryRecommendation(request_key=payload["request_key"], run_ref_id=run.id,
                                  product_id=product.id, snapshot=snapshot,
                                  suggested_quantity=result["suggested_quantity"], action=result["action"],
                                  status="pending", created_by_user_id=user_id)
    db.add(row)
    db.commit()
    db.refresh(row)
    return serialize_recommendation(row)


def review_recommendation(db: Session, recommendation_id: int, values: dict, user_id: int):
    row = db.scalar(select(InventoryRecommendation).where(
        InventoryRecommendation.id == recommendation_id).with_for_update())
    if row is None:
        raise ValueError("Recommendation not found")
    if row.status != "pending":
        raise ValueError("Recommendation has already been reviewed")
    action = values["action"]
    if action != "rejected":
        product = db.scalar(select(Product).where(Product.id == row.product_id).with_for_update())
        if product is None or not product.is_active:
            raise ValueError("Product is no longer active")
        policy = db.scalar(select(ReplenishmentPolicy).where(
            ReplenishmentPolicy.product_id == row.product_id).with_for_update())
        if policy is None or policy_dict(policy) != row.snapshot["policy"]:
            raise ValueError("Policy changed; generate a new recommendation")
        if row.snapshot["mode"] == "live":
            stock = db.scalar(select(Inventory).where(Inventory.product_id == row.product_id).with_for_update())
            if (row.snapshot["decision_date"] != date.today().isoformat() or stock is None
                    or stock.quantity_on_hand != row.snapshot["on_hand"]):
                raise ValueError("Inventory snapshot is stale; generate a new recommendation")
    quantity = 0 if action == "rejected" else (values["quantity"] if action == "modified" else row.suggested_quantity)
    policy = row.snapshot["policy"]
    if quantity and (quantity < policy["minimum_order_quantity"] or quantity % policy["pack_size"]):
        raise ValueError("Reviewed quantity must respect MOQ and pack size")
    decision = RecommendationDecision(recommendation_id=row.id, action=action, quantity=quantity,
                                      reason=values.get("reason"), user_id=user_id)
    db.add(decision)
    row.status = action
    db.commit()
    db.refresh(decision)
    return serialize_recommendation(row, decision)
