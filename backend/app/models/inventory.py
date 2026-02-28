from __future__ import annotations
from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Index, Integer, String, Float, Boolean, DateTime, ForeignKey, Numeric
from sqlalchemy.sql import func
from database.base import Base

if TYPE_CHECKING:
    from models.product import Product

class Inventory(Base):
    __tablename__ = "inventory"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )
    quantity_on_hand: Mapped[int] = mapped_column(Integer, default=0)
    last_updated: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    product: Mapped[Product] = relationship("Product")

    __table_args__ = (
        Index("idx_inventory_product_id", "product_id"),
    )