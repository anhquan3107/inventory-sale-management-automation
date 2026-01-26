from datetime import datetime
from pydantic import BaseModel


class InventoryLogResponse(BaseModel):
    id: int
    product_id: int
    change_quantity: int
    quantity_before: int
    quantity_after: int
    log_type: str
    reference_id: int | None
    log_date: datetime

    class Config:
        from_attributes = True
