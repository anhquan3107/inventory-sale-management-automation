from datetime import date
from typing import Literal

from pydantic import BaseModel


ExceptionMode = Literal["simulation", "live"]
ReviewStatus = Literal["pending", "approved", "modified", "rejected"]
ExceptionClassification = Literal[
    "shortage_within_lead_time", "shortage_after_lead_time", "planned_replenishment",
    "excess_stock_review", "insufficient_evidence", "not_generated", "unsupported_snapshot", "no_exception",
]


class InventoryException(BaseModel):
    product_id: int
    sku: str
    product_name: str
    product_active: bool
    recommendation_id: int | None = None
    review_status: ReviewStatus | None = None
    classification: ExceptionClassification
    first_shortage_step: int | None = None
    first_shortage_period_start: date | None = None
    first_shortage_quantity: str | None = None
    maximum_projected_deficit: str | None = None
    shortage_during_lead_time: bool | None = None
    excess_stock_review: bool | None = None
    zero_demand_stock_review: bool | None = None
    suggested_quantity: int | None = None
    data_basis: Literal["saved_recommendation_snapshot", "forecast_run"]
    reasons: list[str]


class InventoryExceptionPage(BaseModel):
    run_id: str
    as_of_date: date | None
    mode: ExceptionMode
    rules_version: str
    total: int
    scope_total: int
    missing_recommendations: int
    items: list[InventoryException]
