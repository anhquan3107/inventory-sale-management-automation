from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, JSON, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class ForecastCoverage(Base):
    """Explicit declaration that all sales (including zero-sales days) are recorded."""

    __tablename__ = "forecast_coverage"
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), primary_key=True)
    observed_from: Mapped[date] = mapped_column(Date)
    observed_through: Mapped[date] = mapped_column(Date)
    source: Mapped[str] = mapped_column(String(80))
    dataset_version: Mapped[str] = mapped_column(String(100))
    configuration: Mapped[dict] = mapped_column(JSON)

    __table_args__ = (
        CheckConstraint("observed_through >= observed_from", name="ck_forecast_coverage_dates"),
    )


class ForecastBacktestPoint(Base):
    __tablename__ = "forecast_backtest_points"
    id: Mapped[int] = mapped_column(primary_key=True)
    run_ref_id: Mapped[int] = mapped_column(ForeignKey("forecast_runs.id", ondelete="CASCADE"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    granularity: Mapped[str] = mapped_column(String(10))
    model_name: Mapped[str] = mapped_column(String(40))
    split: Mapped[str] = mapped_column(String(12))
    origin: Mapped[date] = mapped_column(Date)
    target_period: Mapped[date] = mapped_column(Date)
    horizon_step: Mapped[int] = mapped_column()
    actual: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    predicted: Mapped[Decimal] = mapped_column(Numeric(14, 4))

    __table_args__ = (
        UniqueConstraint("run_ref_id", "product_id", "granularity", "model_name", "split",
                         "origin", "horizon_step", name="uq_backtest_point"),
        Index("idx_backtest_run_product", "run_ref_id", "product_id"),
    )
