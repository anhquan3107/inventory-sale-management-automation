from datetime import date, datetime
from decimal import Decimal

from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator


class GenerateForecastRequest(BaseModel):
    weekly_horizon: int = Field(default=8, ge=1, le=26)
    monthly_horizon: int = Field(default=6, ge=1, le=24)
    product_ids: list[Annotated[int, Field(gt=0)]] | None = Field(default=None, min_length=1)
    as_of_date: date = Field(default_factory=date.today)


class ForecastGenerationResponse(BaseModel):
    run_id: str
    generated_at: datetime
    total_products: int
    forecasts_created: int
    as_of_date: date
    unavailable_series: int


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
    as_of_date: date | None = None
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
    details: dict | None = None


class ForecastAccuracyListResponse(BaseModel):
    run_id: str
    generated_at: datetime
    granularity: str
    as_of_date: date | None = None
    items: list[ForecastAccuracyItem]


class CoverageRequest(BaseModel):
    observed_from: date
    observed_through: date
    source: str = Field(min_length=1, max_length=80)
    dataset_version: str = Field(min_length=1, max_length=100)
    configuration: dict = Field(default_factory=dict)
    confirms_complete_sales: Literal[True]

    @model_validator(mode="after")
    def check_dates(self):
        if self.observed_through < self.observed_from:
            raise ValueError("Coverage end must not precede start")
        if self.observed_through >= date.today():
            raise ValueError("Declare coverage only through a completed calendar day")
        return self
