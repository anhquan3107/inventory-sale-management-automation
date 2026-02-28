from __future__ import annotations
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Index, Integer, String, Float, Boolean, DateTime, ForeignKey, Numeric
from sqlalchemy.sql import func
from database.base import Base
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models import SalesOrder

class SalesItem(Base):
    __tablename__ = "sales_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    sales_order_id: Mapped[int] = mapped_column(ForeignKey("sales_orders.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12,2), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(12,2), nullable=False)

    __table_args__ = (
        Index("idx_sales_items_order_id", "sales_order_id"),
        Index("idx_sales_items_product_id", "product_id"),
    )
    order: Mapped["SalesOrder"] = relationship(
            back_populates="items"
    )



