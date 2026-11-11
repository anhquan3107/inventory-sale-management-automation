from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import Date, cast, func, select
from sqlalchemy.orm import Session

from models.product import Product
from models.sales_item import SalesItem
from models.sales_order import SalesOrder


SUPPORTED_GRANULARITIES = {"weekly", "monthly"}


def _month_start(value: date) -> date:
    return value.replace(day=1)


def _add_months(value: date, months: int) -> date:
    year = value.year + (value.month - 1 + months) // 12
    month = (value.month - 1 + months) % 12 + 1
    return date(year, month, 1)


def add_period(value: date, granularity: str, steps: int = 1) -> date:
    if granularity == "weekly":
        return value + timedelta(weeks=steps)
    if granularity == "monthly":
        return _add_months(value, steps)
    raise ValueError("Unsupported granularity")


def _normalize_period_start(value: date, granularity: str) -> date:
    if granularity == "weekly":
        return value - timedelta(days=value.weekday())
    if granularity == "monthly":
        return _month_start(value)
    raise ValueError("Unsupported granularity")


def list_active_product_ids(db: Session, product_ids: list[int] | None = None) -> list[int]:
    stmt = select(Product.id).where(Product.is_active == True)

    if product_ids:
        stmt = stmt.where(Product.id.in_(product_ids))

    rows = db.execute(stmt).all()
    ids = [row.id for row in rows]

    if product_ids:
        missing_ids = sorted(set(product_ids) - set(ids))
        if missing_ids:
            raise ValueError(f"Active products not found: {missing_ids}")

    return ids


def get_period_demand_history(
    db: Session,
    product_id: int,
    granularity: str,
    periods_back: int,
) -> list[dict]:
    if granularity not in SUPPORTED_GRANULARITIES:
        raise ValueError("Unsupported granularity")

    if periods_back < 2:
        raise ValueError("periods_back must be at least 2")

    today = date.today()
    current_period = _normalize_period_start(today, granularity)
    first_period = add_period(current_period, granularity, -periods_back + 1)

    period_expr = cast(func.date_trunc(granularity[:-2], SalesOrder.order_date), Date)

    stmt = (
        select(
            period_expr.label("period_start"),
            func.coalesce(func.sum(SalesItem.quantity), 0).label("quantity"),
        )
        .join(SalesOrder, SalesItem.sales_order_id == SalesOrder.id)
        .where(
            SalesItem.product_id == product_id,
            cast(SalesOrder.order_date, Date) >= first_period,
        )
        .group_by(period_expr)
        .order_by(period_expr)
    )

    rows = db.execute(stmt).all()
    quantity_by_period = {row.period_start: float(row.quantity) for row in rows}

    series: list[dict] = []
    pointer = first_period

    while pointer <= current_period:
        series.append(
            {
                "period_start": pointer,
                "quantity": quantity_by_period.get(pointer, 0.0),
            }
        )
        pointer = add_period(pointer, granularity)

    return series


def build_future_periods(last_period_start: date, granularity: str, horizon: int) -> list[tuple[date, date]]:
    periods: list[tuple[date, date]] = []

    for step in range(1, horizon + 1):
        period_start = add_period(last_period_start, granularity, step)
        next_start = add_period(period_start, granularity)
        period_end = next_start - timedelta(days=1)
        periods.append((period_start, period_end))

    return periods
