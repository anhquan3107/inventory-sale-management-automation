from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models.forecast_evidence import ForecastCoverage
from models.product import Product
from models.sales_item import SalesItem
from models.sales_order import SalesOrder


def add_period(value: date, granularity: str, steps: int = 1) -> date:
    if granularity == "weekly":
        return value + timedelta(weeks=steps)
    if granularity == "monthly":
        year = value.year + (value.month - 1 + steps) // 12
        month = (value.month - 1 + steps) % 12 + 1
        return date(year, month, 1)
    raise ValueError("Unsupported granularity")


def period_start(value: date, granularity: str) -> date:
    if granularity == "weekly":
        return value - timedelta(days=value.weekday())
    if granularity == "monthly":
        return value.replace(day=1)
    raise ValueError("Unsupported granularity")


def build_future_periods(last_period_start: date, granularity: str, horizon: int) -> list[tuple[date, date]]:
    return [(add_period(last_period_start, granularity, step),
             add_period(last_period_start, granularity, step + 1) - timedelta(days=1))
            for step in range(1, horizon + 1)]


def list_active_product_ids(db: Session, product_ids: list[int] | None = None) -> list[int]:
    if product_ids is not None and (not product_ids or any(p < 1 for p in product_ids)):
        raise ValueError("product_ids must be omitted or contain positive product IDs")
    stmt = select(Product.id).where(Product.is_active.is_(True)).order_by(Product.id)
    if product_ids is not None:
        stmt = stmt.where(Product.id.in_(product_ids))
    ids = list(db.scalars(stmt))
    missing = sorted(set(product_ids or []) - set(ids))
    if missing:
        raise ValueError(f"Active products not found: {missing}")
    return ids


def get_history(db: Session, product_id: int, granularity: str, as_of_date: date) -> dict:
    cutoff = period_start(as_of_date, granularity)
    coverage = db.get(ForecastCoverage, product_id)
    base = {"status": "unknown_coverage", "rows": [], "cutoff": cutoff.isoformat(),
            "dataset_version": None, "source": None}
    if coverage is None:
        return base
    base.update(dataset_version=coverage.dataset_version, source=coverage.source,
                coverage_from=coverage.observed_from.isoformat(),
                coverage_through=coverage.observed_through.isoformat(),
                configuration=coverage.configuration)
    if coverage.observed_through < cutoff - timedelta(days=1):
        base["status"] = "coverage_ends_before_cutoff"
        return base
    first = period_start(coverage.observed_from, granularity)
    if first < coverage.observed_from:
        first = add_period(first, granularity)
    # Fixed lookback does not change when the requested prediction horizon changes.
    first = max(first, add_period(cutoff, granularity, -156 if granularity == "weekly" else -60))
    # PostgreSQL timestamps are stored with time zones; bucket them in UTC explicitly.
    order_timestamp = (func.timezone("UTC", SalesOrder.order_date)
                       if db.get_bind().dialect.name == "postgresql" else SalesOrder.order_date)
    daily = func.date(order_timestamp)
    rows = db.execute(
        select(daily.label("day"), func.sum(SalesItem.quantity).label("quantity"))
        .join(SalesOrder, SalesOrder.id == SalesItem.sales_order_id)
        .where(SalesItem.product_id == product_id, daily >= first.isoformat(), daily < cutoff.isoformat())
        .group_by(daily)
    ).all()
    quantities = {}
    for row in rows:
        day = date.fromisoformat(row.day) if isinstance(row.day, str) else row.day
        bucket = period_start(day, granularity)
        quantities[bucket] = quantities.get(bucket, 0.0) + float(row.quantity)
    series = []
    pointer = first
    while pointer < cutoff:
        series.append({"period_start": pointer, "quantity": quantities.get(pointer, 0.0)})
        pointer = add_period(pointer, granularity)
    base.update(status="ready", rows=series)
    return base
