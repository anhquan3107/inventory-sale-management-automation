from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from database.base import Base

if TYPE_CHECKING:
    from models.forecast_accuracy import ForecastAccuracy
    from models.forecast_prediction import ForecastPrediction


class ForecastRun(Base):
    __tablename__ = "forecast_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    weekly_horizon: Mapped[int] = mapped_column(Integer, nullable=False)
    monthly_horizon: Mapped[int] = mapped_column(Integer, nullable=False)
    total_products: Mapped[int] = mapped_column(Integer, nullable=False)
    generated_by_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="completed", nullable=False)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    predictions: Mapped[list["ForecastPrediction"]] = relationship(
        "ForecastPrediction",
        back_populates="run",
        cascade="all, delete-orphan",
    )
    accuracies: Mapped[list["ForecastAccuracy"]] = relationship(
        "ForecastAccuracy",
        back_populates="run",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_forecast_runs_run_id", "run_id"),
        Index("idx_forecast_runs_generated_at", "generated_at"),
    )