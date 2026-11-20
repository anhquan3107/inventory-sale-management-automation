from typing import Literal

from pydantic import BaseModel, Field, model_validator


class PolicyRequest(BaseModel):
    lead_time_weeks: int = Field(ge=1, le=25)
    review_interval_weeks: int = Field(default=1, ge=1, le=25)
    safety_stock: int = Field(default=0, ge=0)
    minimum_order_quantity: int = Field(default=0, ge=0)
    pack_size: int = Field(default=1, ge=1)

    @model_validator(mode="after")
    def check_horizon(self):
        if self.lead_time_weeks + self.review_interval_weeks > 26:
            raise ValueError("Protection period must fit the maximum 26-week forecast")
        return self


class SimulatedReceipt(BaseModel):
    arrival_week: int = Field(ge=1, le=26)
    quantity: int = Field(gt=0)


class RecommendationRequest(BaseModel):
    request_key: str = Field(min_length=1, max_length=100)
    run_id: str
    product_id: int = Field(gt=0)
    mode: Literal["simulation", "live"] = "simulation"
    simulated_on_hand: int | None = Field(default=None, ge=0)
    simulated_receipts: list[SimulatedReceipt] = Field(default_factory=list, max_length=100)
    confirms_no_incoming_orders: bool = False

    @model_validator(mode="after")
    def check_mode(self):
        if self.mode == "simulation" and self.simulated_on_hand is None:
            raise ValueError("Simulation requires an explicit simulated_on_hand")
        if self.mode == "live" and (self.simulated_on_hand is not None or self.simulated_receipts):
            raise ValueError("Live MVP uses database on-hand only; incoming supply is not yet integrated")
        if self.mode == "live" and not self.confirms_no_incoming_orders:
            raise ValueError("Live mode requires explicit confirmation that no incoming supplier orders exist")
        return self


class DecisionRequest(BaseModel):
    action: Literal["approved", "modified", "rejected"]
    quantity: int | None = Field(default=None, ge=0)
    reason: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def check_action(self):
        if self.action == "modified" and (self.quantity is None or not (self.reason or "").strip()):
            raise ValueError("A modification requires quantity and reason")
        if self.action != "modified" and self.quantity is not None:
            raise ValueError("Only modifications accept a quantity override")
        return self
