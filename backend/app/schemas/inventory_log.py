from datetime import datetime
from pydantic import BaseModel
from models.enums.inventory_log_type import InventoryLogType


class InventoryLogResponse(BaseModel):
    id: int
    product_id: int
    change_quantity: int
    quantity_before: int
    quantity_after: int
    log_type: InventoryLogType
    reference_id: int | None
    log_date: datetime

    class Config:
        from_attributes = True
