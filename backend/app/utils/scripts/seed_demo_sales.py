from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
import random
import sys

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.append(str(BASE_DIR))

from database.session import SessionLocal
from models.inventory import Inventory
from models.inventory_log import InventoryLog
from models.product import Product
from models.sales_item import SalesItem
from models.sales_order import SalesOrder
from models.enums.inventory_log_type import InventoryLogType


RANDOM_SEED = 20260623
DEMO_SKU_PREFIX = "DEMO-"
DEMO_CHANNELS = ("ONLINE", "OFFLINE", "MARKETPLACE")

DEMO_PRODUCTS = [
    ("DEMO-COF-001", "Arabica Coffee Beans 500g", "Coffee", "12.50", 7.8),
    ("DEMO-COF-002", "Cold Brew Bottle 250ml", "Coffee", "3.20", 14.0),
    ("DEMO-TEA-001", "Jasmine Green Tea Box", "Tea", "8.40", 5.4),
    ("DEMO-TEA-002", "Oolong Tea Tin", "Tea", "11.90", 3.7),
    ("DEMO-SNK-001", "Chocolate Protein Bar", "Snack", "2.80", 12.5),
    ("DEMO-SNK-002", "Sea Salt Crackers", "Snack", "3.10", 8.2),
    ("DEMO-HOM-001", "Ceramic Mug", "Home", "6.50", 2.6),
    ("DEMO-HOM-002", "Reusable Bottle", "Home", "9.90", 3.4),
    ("DEMO-PER-001", "Hand Cream 50ml", "Personal Care", "5.75", 4.9),
    ("DEMO-PER-002", "Lip Balm", "Personal Care", "2.25", 6.8),
    ("DEMO-SEA-001", "Holiday Gift Box", "Seasonal", "18.00", 1.8),
    ("DEMO-SEA-002", "Summer Iced Tea Kit", "Seasonal", "15.50", 1.5),
]


def _money(value: str | float) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"))


def _clear_demo_data(db: Session) -> None:
    demo_product_ids = [
        row.id
        for row in db.execute(
            select(Product.id).where(Product.sku.like(f"{DEMO_SKU_PREFIX}%"))
        ).all()
    ]

    if not demo_product_ids:
        return

    order_ids = [
        row.sales_order_id
        for row in db.execute(
            select(SalesItem.sales_order_id)
            .where(SalesItem.product_id.in_(demo_product_ids))
            .distinct()
        ).all()
    ]

    if order_ids:
        db.execute(delete(SalesItem).where(SalesItem.sales_order_id.in_(order_ids)))
        db.execute(delete(SalesOrder).where(SalesOrder.id.in_(order_ids)))

    db.execute(delete(InventoryLog).where(InventoryLog.product_id.in_(demo_product_ids)))
    db.execute(delete(Inventory).where(Inventory.product_id.in_(demo_product_ids)))
    db.execute(delete(Product).where(Product.id.in_(demo_product_ids)))
    db.flush()


def _daily_quantity(rng: random.Random, base_demand: float, current_date: datetime) -> int:
    weekday_multiplier = 1.25 if current_date.weekday() in (4, 5, 6) else 0.88
    month_multiplier = 1.0

    if current_date.month in (11, 12):
        month_multiplier = 1.45
    elif current_date.month in (6, 7, 8):
        month_multiplier = 1.18
    elif current_date.month in (2,):
        month_multiplier = 0.82

    trend_multiplier = 1 + ((current_date.timetuple().tm_yday - 1) / 365) * 0.18
    noise = rng.uniform(0.55, 1.45)
    expected = base_demand * weekday_multiplier * month_multiplier * trend_multiplier * noise

    quantity = int(round(expected))

    if rng.random() < 0.18:
        quantity = 0
    if rng.random() < 0.035:
        quantity += rng.randint(6, 18)

    return max(0, quantity)


def seed_demo_sales(days: int = 365, replace: bool = True) -> None:
    rng = random.Random(RANDOM_SEED)
    db: Session = SessionLocal()

    try:
        if replace:
            _clear_demo_data(db)

        existing_demo = db.execute(
            select(Product.id).where(Product.sku.like(f"{DEMO_SKU_PREFIX}%")).limit(1)
        ).scalar_one_or_none()
        if existing_demo:
            print("Demo data already exists. Use replace=True in the script to reseed.")
            return

        products: list[tuple[Product, float]] = []
        for sku, name, category, unit_price, base_demand in DEMO_PRODUCTS:
            product = Product(
                sku=sku,
                name=name,
                category=category,
                unit_price=_money(unit_price),
                is_active=True,
            )
            db.add(product)
            products.append((product, base_demand))

        db.flush()

        for product, _base_demand in products:
            initial_quantity = rng.randint(900, 1800)
            db.add(
                Inventory(
                    product_id=product.id,
                    quantity_on_hand=initial_quantity,
                )
            )
            db.add(
                InventoryLog(
                    product_id=product.id,
                    change_quantity=initial_quantity,
                    quantity_before=0,
                    quantity_after=initial_quantity,
                    log_type=InventoryLogType.INIT.value,
                    reference_id=None,
                    log_date=datetime.now(),
                )
            )

        start_date = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0) - timedelta(days=days)
        orders_created = 0
        items_created = 0

        for day_offset in range(days):
            current_date = start_date + timedelta(days=day_offset)
            daily_items: list[tuple[Product, int]] = []

            for product, base_demand in products:
                quantity = _daily_quantity(rng, base_demand, current_date)
                if quantity > 0:
                    daily_items.append((product, quantity))

            if not daily_items:
                continue

            rng.shuffle(daily_items)
            chunk_size = rng.randint(2, 5)

            for chunk_start in range(0, len(daily_items), chunk_size):
                chunk = daily_items[chunk_start : chunk_start + chunk_size]
                order_date = current_date.replace(
                    hour=rng.randint(8, 21),
                    minute=rng.randint(0, 59),
                    second=rng.randint(0, 59),
                )
                order = SalesOrder(
                    order_date=order_date,
                    created_at=order_date,
                    sales_channel=rng.choice(DEMO_CHANNELS),
                    total_amount=Decimal("0.00"),
                )
                db.add(order)
                db.flush()

                total_amount = Decimal("0.00")

                for product, quantity in chunk:
                    line_total = (product.unit_price * quantity).quantize(Decimal("0.01"))
                    db.add(
                        SalesItem(
                            sales_order_id=order.id,
                            product_id=product.id,
                            quantity=quantity,
                            unit_price=product.unit_price,
                            line_total=line_total,
                        )
                    )
                    total_amount += line_total
                    items_created += 1

                order.total_amount = total_amount
                orders_created += 1

        db.commit()

        print("Demo sales data seeded successfully.")
        print(f"Products created: {len(products)}")
        print(f"Sales orders created: {orders_created}")
        print(f"Sales items created: {items_created}")
        print(f"History window: {days} days")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_sales()
