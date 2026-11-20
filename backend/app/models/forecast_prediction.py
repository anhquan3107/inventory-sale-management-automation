from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from database.base import Base

if TYPE_CHECKING:
    from models.forecast_run import ForecastRun


class ForecastPrediction(Base):
    __tablename__ = "forecast_predictions"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_ref_id: Mapped[int] = mapped_column(
        ForeignKey("forecast_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )
    granularity: Mapped[str] = mapped_column(String(10), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    horizon_step: Mapped[int] = mapped_column(Integer, nullable=False)
    selected_model: Mapped[str] = mapped_column(String(40), nullable=False)
    predicted_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    confidence_lower: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    confidence_upper: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    fallback_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    run: Mapped["ForecastRun"] = relationship("ForecastRun", back_populates="predictions")

    __table_args__ = (
        UniqueConstraint(
            "run_ref_id",
            "product_id",
            "granularity",
            "horizon_step",
            name="uq_forecast_predictions_run_product_step",
        ),
        Index("idx_forecast_predictions_run_ref_id", "run_ref_id"),
        Index("idx_forecast_predictions_product_id", "product_id"),
        Index("idx_forecast_predictions_period_start", "period_start"),
    )
