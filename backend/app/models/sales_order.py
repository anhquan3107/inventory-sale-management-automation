from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Index, Integer, String, Float, Boolean, DateTime, ForeignKey, Numeric
from sqlalchemy.sql import func
from database.base import Base
from decimal import Decimal

class SalesOrder(Base):
    __tablename__ = "sales_orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_date: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12,2), default=0)
    sales_channel: Mapped[str] = mapped_column(String)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("idx_sales_orders_order_date", "order_date"),
        Index("idx_sales_orders_sales_channel", "sales_channel"),
    )

"""class DemandForecast(Base):
    __tablename__ = "demand_forecasts"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))

    forecast_date: Mapped[Date] = mapped_column()
    forecast_quantity: Mapped[int] = mapped_column()

    model_name: Mapped[str] = mapped_column(String)
    model_version: Mapped[str] = mapped_column(String)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )"""