from sqlalchemy import Column, Integer, ForeignKey, Float
from database.base import Base

class SalesItem(Base):
    __tablename__ = "sales_items"

    id = Column(Integer, primary_key=True)
    sales_order_id = Column(Integer, ForeignKey("sales_orders.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer)
    unit_price = Column(Float)
    line_total = Column(Float)
