from pydantic import BaseModel, Field
from typing import List
from decimal import Decimal

class CreateSaleItem(BaseModel):
    product_id: int = Field(
        json_schema_extra={"example": 1}
    )
    quantity: int = Field(
        gt=0,
        json_schema_extra={"example": 2}
    )
    unit_price: Decimal = Field(
        ge=0,
        json_schema_extra={"example": "100.00"}
    )


class CreateSaleRequest(BaseModel):
    sales_channel: str = Field(
        default="OFFLINE",
        json_schema_extra={"example": "ONLINE"}
    )
    items: List[CreateSaleItem]


class CreateSaleResponse(BaseModel):
    order_id: int
    total_amount: Decimal
