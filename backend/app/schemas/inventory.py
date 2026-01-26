from pydantic import BaseModel, Field
from typing import Optional

class InventoryInitRequest(BaseModel):
    product_id: int = Field(json_schema_extra={"example": 1})
    quantity: int = Field(
        ge=0,
        json_schema_extra={"example": 100}
    )

class InventoryAdjustRequest(BaseModel):
    product_id: int = Field(json_schema_extra={"example": 1})
    change_quantity: int = Field(
        json_schema_extra={"example": -5}
    )

class InventoryResponse(BaseModel):
    product_id: int
    quantity_on_hand: int

