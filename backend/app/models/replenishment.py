from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from database.base import Base


class ReplenishmentPolicy(Base):
    __tablename__ = "replenishment_policies"
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), primary_key=True)
    lead_time_weeks: Mapped[int] = mapped_column()
    review_interval_weeks: Mapped[int] = mapped_column()
    safety_stock: Mapped[int] = mapped_column()
    minimum_order_quantity: Mapped[int] = mapped_column()
    pack_size: Mapped[int] = mapped_column()
    version: Mapped[int] = mapped_column(default=1)

    __table_args__ = (
        CheckConstraint("lead_time_weeks >= 1 AND review_interval_weeks >= 1", name="ck_policy_weeks"),
        CheckConstraint("safety_stock >= 0 AND minimum_order_quantity >= 0 AND pack_size >= 1",
                        name="ck_policy_quantities"),
    )


class InventoryRecommendation(Base):
    __tablename__ = "inventory_recommendations"
    id: Mapped[int] = mapped_column(primary_key=True)
    request_key: Mapped[str] = mapped_column(String(100), unique=True)
    run_ref_id: Mapped[int] = mapped_column(ForeignKey("forecast_runs.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    snapshot: Mapped[dict] = mapped_column(JSON)
    suggested_quantity: Mapped[int] = mapped_column()
    action: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_by_user_id: Mapped[int] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RecommendationDecision(Base):
    __tablename__ = "recommendation_decisions"
    id: Mapped[int] = mapped_column(primary_key=True)
    recommendation_id: Mapped[int] = mapped_column(ForeignKey("inventory_recommendations.id"))
    action: Mapped[str] = mapped_column(String(20))
    quantity: Mapped[int] = mapped_column()
    reason: Mapped[str | None] = mapped_column(String, nullable=True)
    user_id: Mapped[int] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("recommendation_id", name="uq_recommendation_decision"),)
