from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database.dependencies import get_db
from utils.security.bearer import require_auth
from schemas.dashboard import (
    DashboardSummaryResponse,
    RevenueTrendItem,
    TopProductItem,
    LowStockItem,
    RecentSaleItem,
)
from services.dashboard import (
    get_dashboard_summary,
    get_revenue_trend,
    get_top_products,
    get_low_stock_products,
    get_recent_sales,
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
    summary="Dashboard KPI summary",
)
def dashboard_summary(
    current_user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
):
    return get_dashboard_summary(db)


@router.get(
    "/revenue-trend",
    response_model=list[RevenueTrendItem],
    summary="Revenue trend for line chart",
)
def revenue_trend(
    days: int = Query(default=7, ge=1, le=90),
    current_user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
):
    return get_revenue_trend(db, days=days)


@router.get(
    "/top-products",
    response_model=list[TopProductItem],
    summary="Top selling products for bar chart",
)
def top_products(
    limit: int = Query(default=5, ge=1, le=20),
    current_user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
):
    return get_top_products(db, limit=limit)


@router.get(
    "/low-stock",
    response_model=list[LowStockItem],
    summary="Low stock alert items",
)
def low_stock(
    current_user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
):
    return get_low_stock_products(db)


@router.get(
    "/recent-sales",
    response_model=list[RecentSaleItem],
    summary="Recent sales activity",
)
def recent_sales(
    limit: int = Query(default=5, ge=1, le=50),
    current_user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
):
    return get_recent_sales(db, limit=limit)
