from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from database.base import Base

if TYPE_CHECKING:
    from models.forecast_run import ForecastRun


class ForecastAccuracy(Base):
    __tablename__ = "forecast_accuracy"

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
    selected_model: Mapped[str] = mapped_column(String(40), nullable=False)
    mape: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    mae: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    rmse: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    training_points: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    run: Mapped["ForecastRun"] = relationship("ForecastRun", back_populates="accuracies")

    __table_args__ = (
        UniqueConstraint(
            "run_ref_id",
            "product_id",
            "granularity",
            name="uq_forecast_accuracy_run_product_granularity",
        ),
        Index("idx_forecast_accuracy_run_ref_id", "run_ref_id"),
        Index("idx_forecast_accuracy_product_id", "product_id"),
    )
