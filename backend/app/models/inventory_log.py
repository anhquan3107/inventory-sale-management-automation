from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Index, Integer, String, Float, Boolean, DateTime, ForeignKey, Numeric
from sqlalchemy.sql import func
from database.base import Base

class InventoryLog(Base):
    __tablename__ = "inventory_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    change_quantity: Mapped[int] = mapped_column(Integer)
    quantity_before: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_after: Mapped[int] = mapped_column(Integer, nullable=False)
    log_type: Mapped[str] = mapped_column(String)  # SALE, RESTOCK, ADJUSTMENT
    reference_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    log_date: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    __table_args__ = (
        Index("idx_inventory_log_product_id", "product_id"),
        Index("idx_inventory_log_log_date", "log_date"),
    )