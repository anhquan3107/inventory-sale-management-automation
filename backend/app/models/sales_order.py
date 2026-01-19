from sqlalchemy import Column, Integer, DateTime, Float, String
from sqlalchemy.sql import func
from database.base import Base

class SalesOrder(Base):
    __tablename__ = "sales_orders"

    id = Column(Integer, primary_key=True)
    order_date = Column(DateTime(timezone=True), server_default=func.now())
    total_amount = Column(Float)
    sales_channel = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
