from pydantic import BaseModel, Field
from typing import Optional

class CreateProductRequest(BaseModel):
    sku: str = Field(json_schema_extra={"example": "SKU-IPHONE-15"})
    name: str = Field(json_schema_extra={"example": "iPhone 15"})
    category: Optional[str] = Field(
        default=None,
        json_schema_extra={"example": "Smartphone"}
    )
    unit_price: float = Field(
        ge=0,
        json_schema_extra={"example": 999.99}
    )

class UpdateProductRequest(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    unit_price: Optional[float] = Field(default=None, ge=0)
    is_active: Optional[bool] = None

class ProductResponse(BaseModel):
    id: int
    sku: str
    name: str
    category: Optional[str]
    unit_price: float
    is_active: bool
