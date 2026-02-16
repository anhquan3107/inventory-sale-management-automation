from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select
from typing import Sequence
from datetime import datetime

from models.sales_order import SalesOrder
from models.sales_item import SalesItem


def list_sales(
    db: Session,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    sales_channel: str | None = None,
    product_id: int | None = None,
) -> Sequence[SalesOrder]:
    stmt = select(SalesOrder)

    if date_from:
        stmt = stmt.where(SalesOrder.order_date >= date_from)

    if date_to:
        stmt = stmt.where(SalesOrder.order_date <= date_to)

    if sales_channel:
        stmt = stmt.where(SalesOrder.sales_channel == sales_channel)

    if product_id:
        stmt = (
            stmt.join(SalesItem)
            .where(SalesItem.product_id == product_id)
            .distinct()
        )

    stmt = stmt.order_by(SalesOrder.order_date.desc())

    return db.execute(stmt).scalars().all()


def get_sale_detail(
    db: Session,
    order_id: int
) -> SalesOrder | None:
    stmt = (
        select(SalesOrder)
        .where(SalesOrder.id == order_id)
        .options(joinedload(SalesOrder.items))
    )

    return db.execute(stmt).scalars().first()
