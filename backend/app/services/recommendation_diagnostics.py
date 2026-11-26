from datetime import date
from decimal import Decimal


DIAGNOSTICS_RULES_VERSION = "inventory-exceptions-v1"
EXCESS_STOCK_FACTOR = Decimal("2")


def diagnose_recommendation(result: dict, period_starts: list[date], lead_time_weeks: int) -> dict:
    balances = [Decimal(value) for value in result["projected_week_end_stock"]]
    shortages = [(index, -balance) for index, balance in enumerate(balances) if balance < 0]
    first_index, first_quantity = shortages[0] if shortages else (None, None)
    target = Decimal(result["target_stock"])
    position = Decimal(result["inventory_position"])
    threshold = target * EXCESS_STOCK_FACTOR if target > 0 else None
    excess = max(Decimal(0), position - threshold) if threshold is not None else None
    return {
        "rules_version": DIAGNOSTICS_RULES_VERSION,
        "status": "available",
        "first_shortage_step": first_index + 1 if first_index is not None else None,
        "first_shortage_period_start": period_starts[first_index].isoformat() if first_index is not None else None,
        "first_shortage_quantity": str(first_quantity) if first_quantity is not None else None,
        "maximum_projected_deficit": str(max((quantity for _, quantity in shortages), default=Decimal(0))),
        "shortage_during_lead_time": first_index is not None and first_index < lead_time_weeks,
        "excess_stock_review": excess is not None and excess > 0,
        "excess_stock_factor": str(EXCESS_STOCK_FACTOR),
        "excess_stock_threshold": str(threshold) if threshold is not None else None,
        "excess_above_review_threshold": str(excess) if excess is not None else None,
        "zero_demand_stock_review": target == 0 and position > 0,
    }
