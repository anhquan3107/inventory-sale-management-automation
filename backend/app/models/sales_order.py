from __future__ import annotations
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Index, Integer, String, Float, Boolean, DateTime, ForeignKey, Numeric
from sqlalchemy.sql import func
from database.base import Base
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models import SalesItem

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

    items: Mapped[list["SalesItem"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan"
    )

