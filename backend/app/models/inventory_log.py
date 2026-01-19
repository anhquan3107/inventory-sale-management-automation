from sqlalchemy import Column, Integer, ForeignKey, String, DateTime
from sqlalchemy.sql import func
from database.base import Base

class InventoryLog(Base):
    __tablename__ = "inventory_log"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    change_quantity = Column(Integer)
    log_type = Column(String)  # SALE, RESTOCK, ADJUSTMENT
    reference_id = Column(Integer, nullable=True)
    log_date = Column(DateTime(timezone=True), server_default=func.now())
