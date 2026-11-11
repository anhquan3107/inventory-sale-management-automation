from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class GenerateForecastRequest(BaseModel):
    weekly_horizon: int = Field(default=8, ge=1, le=26)
    monthly_horizon: int = Field(default=6, ge=1, le=24)
    product_ids: list[int] | None = None


class ForecastGenerationResponse(BaseModel):
    run_id: str
    generated_at: datetime
    total_products: int
    forecasts_created: int


class ForecastPredictionItem(BaseModel):
    product_id: int
    product_name: str
    product_sku: str
    granularity: str
    period_start: date
    period_end: date
    horizon_step: int
    selected_model: str
    predicted_quantity: Decimal
    confidence_lower: Decimal | None
    confidence_upper: Decimal | None
    fallback_reason: str | None


class ForecastPredictionListResponse(BaseModel):
    run_id: str
    generated_at: datetime
    granularity: str
    items: list[ForecastPredictionItem]


class ForecastAccuracyItem(BaseModel):
    product_id: int
    product_name: str
    product_sku: str
    granularity: str
    selected_model: str
    mape: Decimal | None
    mae: Decimal | None
    rmse: Decimal | None
    training_points: int


class ForecastAccuracyListResponse(BaseModel):
    run_id: str
    generated_at: datetime
    granularity: str
    items: list[ForecastAccuracyItem]
