from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Sequence

from models.inventory_log import InventoryLog
from models.enums.inventory_log_type import InventoryLogType


def get_inventory_logs(
    db: Session,
    product_id: int | None = None,
    log_type: InventoryLogType | None = None,
    limit: int = 100,
    offset: int = 0
) -> Sequence[InventoryLog]:
    query = select(InventoryLog)

    if product_id is not None:
        query = query.where(InventoryLog.product_id == product_id)

    if log_type is not None:
        query = query.where(InventoryLog.log_type == log_type.value)

    query = query.order_by(InventoryLog.log_date.desc())
    query = query.limit(limit).offset(offset)

    return db.execute(query).scalars().all()
