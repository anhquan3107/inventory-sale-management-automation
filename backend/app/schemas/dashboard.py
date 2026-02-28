from pydantic import BaseModel
from datetime import date, datetime
from decimal import Decimal


class DashboardSummaryResponse(BaseModel):
    revenue_today: Decimal
    revenue_month: Decimal
    orders_today: int
    low_stock_count: int


class RevenueTrendItem(BaseModel):
    date: date
    revenue: Decimal


class TopProductItem(BaseModel):
    product_id: int
    product_name: str
    total_quantity_sold: int


class LowStockItem(BaseModel):
    product_id: int
    product_name: str
    current_stock: int


class RecentSaleItem(BaseModel):
    sale_id: int
    total_amount: Decimal
    sales_channel: str
    created_at: datetime

    class Config:
        from_attributes = True
