from sqlalchemy.orm import Session
from sqlalchemy import select, func, cast, Date
from decimal import Decimal
from datetime import datetime, date, timedelta

from models.sales_order import SalesOrder
from models.sales_item import SalesItem
from models.inventory import Inventory
from models.product import Product

LOW_STOCK_THRESHOLD = 10


def get_dashboard_summary(db: Session) -> dict:
    today = date.today()
    first_of_month = today.replace(day=1)

    # revenue_today
    stmt_rev_today = select(
        func.coalesce(func.sum(SalesOrder.total_amount), 0)
    ).where(
        cast(SalesOrder.order_date, Date) == today
    )
    revenue_today = db.execute(stmt_rev_today).scalar_one()

    # revenue_month
    stmt_rev_month = select(
        func.coalesce(func.sum(SalesOrder.total_amount), 0)
    ).where(
        cast(SalesOrder.order_date, Date) >= first_of_month
    )
    revenue_month = db.execute(stmt_rev_month).scalar_one()

    # orders_today
    stmt_orders_today = select(
        func.count()
    ).select_from(SalesOrder).where(
        cast(SalesOrder.order_date, Date) == today
    )
    orders_today = db.execute(stmt_orders_today).scalar_one()

    # low_stock_count
    stmt_low_stock = select(
        func.count()
    ).select_from(Inventory).where(
        Inventory.quantity_on_hand <= LOW_STOCK_THRESHOLD
    )
    low_stock_count = db.execute(stmt_low_stock).scalar_one()

    return {
        "revenue_today": Decimal(str(revenue_today)),
        "revenue_month": Decimal(str(revenue_month)),
        "orders_today": orders_today,
        "low_stock_count": low_stock_count,
    }


def get_revenue_trend(db: Session, days: int = 7) -> list[dict]:
    start_date = date.today() - timedelta(days=days - 1)

    stmt = (
        select(
            cast(SalesOrder.order_date, Date).label("date"),
            func.coalesce(func.sum(SalesOrder.total_amount), 0).label("revenue"),
        )
        .where(cast(SalesOrder.order_date, Date) >= start_date)
        .group_by(cast(SalesOrder.order_date, Date))
        .order_by(cast(SalesOrder.order_date, Date))
    )

    rows = db.execute(stmt).all()

    return [
        {"date": row.date, "revenue": Decimal(str(row.revenue))}
        for row in rows
    ]


def get_top_products(db: Session, limit: int = 5) -> list[dict]:
    stmt = (
        select(
            SalesItem.product_id,
            Product.name.label("product_name"),
            func.sum(SalesItem.quantity).label("total_quantity_sold"),
        )
        .join(Product, SalesItem.product_id == Product.id)
        .group_by(SalesItem.product_id, Product.name)
        .order_by(func.sum(SalesItem.quantity).desc())
        .limit(limit)
    )

    rows = db.execute(stmt).all()

    return [
        {
            "product_id": row.product_id,
            "product_name": row.product_name,
            "total_quantity_sold": row.total_quantity_sold,
        }
        for row in rows
    ]


def get_low_stock_products(db: Session) -> list[dict]:
    stmt = (
        select(
            Inventory.product_id,
            Product.name.label("product_name"),
            Inventory.quantity_on_hand.label("current_stock"),
        )
        .join(Product, Inventory.product_id == Product.id)
        .where(Inventory.quantity_on_hand <= LOW_STOCK_THRESHOLD)
        .order_by(Inventory.quantity_on_hand.asc())
    )

    rows = db.execute(stmt).all()

    return [
        {
            "product_id": row.product_id,
            "product_name": row.product_name,
            "current_stock": row.current_stock,
        }
        for row in rows
    ]


def get_recent_sales(db: Session, limit: int = 5) -> list[dict]:
    stmt = (
        select(SalesOrder)
        .order_by(SalesOrder.created_at.desc())
        .limit(limit)
    )

    orders = db.execute(stmt).scalars().all()

    return [
        {
            "sale_id": order.id,
            "total_amount": order.total_amount,
            "sales_channel": order.sales_channel,
            "created_at": order.created_at,
        }
        for order in orders
    ]
