from pydantic import BaseModel
from datetime import datetime
from decimal import Decimal
from typing import List


class SaleItemRead(BaseModel):
    product_id: int
    quantity: int
    unit_price: Decimal
    line_total: Decimal

    class Config:
        from_attributes = True


class SaleRead(BaseModel):
    id: int
    order_date: datetime
    sales_channel: str
    total_amount: Decimal

    class Config:
        from_attributes = True


class SaleDetailRead(BaseModel):
    id: int
    order_date: datetime
    sales_channel: str
    total_amount: Decimal
    items: List[SaleItemRead]

    class Config:
        from_attributes = True
