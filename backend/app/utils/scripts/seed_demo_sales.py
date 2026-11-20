from __future__ import annotations

import argparse
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
import random
import sys

sys.path.append(str(Path(__file__).resolve().parents[2]))

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.forecast_evidence import ForecastCoverage
from models.inventory import Inventory
from models.inventory_log import InventoryLog
from models.product import Product
from models.replenishment import ReplenishmentPolicy
from models.sales_item import SalesItem
from models.sales_order import SalesOrder


RANDOM_SEED = 20260623
DEFAULT_END = date(2026, 11, 16)  # Exclusive Monday cutoff, deliberately not today's date.
GENERATOR_VERSION = "demo-v2"
DEMO_PRODUCTS = [
    ("COF-001", "Arabica Coffee Beans 500g", "Coffee", "12.50", 7.8),
    ("COF-002", "Cold Brew Bottle 250ml", "Coffee", "3.20", 14.0),
    ("TEA-001", "Jasmine Green Tea Box", "Tea", "8.40", 5.4),
    ("TEA-002", "Oolong Tea Tin", "Tea", "11.90", 3.7),
    ("SNK-001", "Chocolate Protein Bar", "Snack", "2.80", 12.5),
    ("SNK-002", "Sea Salt Crackers", "Snack", "3.10", 8.2),
    ("HOM-001", "Ceramic Mug", "Home", "6.50", 2.6),
    ("HOM-002", "Reusable Bottle", "Home", "9.90", 3.4),
    ("PER-001", "Hand Cream 50ml", "Personal Care", "5.75", 4.9),
    ("PER-002", "Lip Balm", "Personal Care", "2.25", 6.8),
    ("SEA-001", "Holiday Gift Box", "Seasonal", "18.00", 1.8),
    ("SEA-002", "Summer Iced Tea Kit", "Seasonal", "15.50", 1.5),
]


def build_demo_dataset(days: int = 1092, end_date: date = DEFAULT_END, seed: int = RANDOM_SEED) -> dict:
    if not 28 <= days <= 3650:
        raise ValueError("days must be between 28 and 3650")
    if end_date > date.today():
        raise ValueError("end_date cannot be in the future")
    start = end_date - timedelta(days=days)
    config = {"generator": GENERATOR_VERSION, "seed": seed, "days": days,
              "start_date": start.isoformat(), "end_date_exclusive": end_date.isoformat(),
              "timezone": "UTC", "inventory": "simulated opening stock covers all sales plus ending stock"}
    rng = random.Random(seed)
    orders = []
    totals = [0] * len(DEMO_PRODUCTS)
    for offset in range(days):
        day = start + timedelta(days=offset)
        items = []
        for idx, (sku, name, category, price, base) in enumerate(DEMO_PRODUCTS):
            weekend = 1.25 if day.weekday() in (4, 5, 6) else 0.88
            seasonal = 1.45 if day.month in (11, 12) else (1.18 if day.month in (6, 7, 8) else 1.0)
            if sku == "SEA-001":
                seasonal = 4.0 if day.month in (11, 12) else 0.35
            elif sku == "SEA-002":
                seasonal = 3.0 if day.month in (6, 7, 8) else 0.4
            quantity = round(base * weekend * seasonal * (1 + offset / 365 * 0.06) * rng.uniform(0.55, 1.45))
            if rng.random() < 0.18:
                quantity = 0
            if rng.random() < 0.035:
                quantity += rng.randint(6, 18)
            if quantity:
                items.append({"product_index": idx, "quantity": quantity, "unit_price": price})
                totals[idx] += quantity
        if items:
            orders.append({"date": day.isoformat(), "channel": rng.choice(("ONLINE", "OFFLINE", "MARKETPLACE")),
                           "items": items})
    checksum = sha256(json.dumps({"config": config, "products": DEMO_PRODUCTS, "orders": orders}, sort_keys=True,
                                separators=(",", ":")).encode()).hexdigest()
    return {"config": config, "checksum": checksum, "version": f"{GENERATOR_VERSION}-{checksum[:16]}",
            "orders": orders, "totals": totals}


def seed_demo_sales(db: Session, days: int = 1092, end_date: date = DEFAULT_END,
                    seed: int = RANDOM_SEED) -> dict:
    dataset = build_demo_dataset(days, end_date, seed)
    version = dataset["version"]
    existing = list(db.scalars(select(ForecastCoverage).where(ForecastCoverage.dataset_version == version)
                              .order_by(ForecastCoverage.product_id)))
    if existing:
        if len(existing) != len(DEMO_PRODUCTS):
            raise ValueError("Incomplete existing dataset; inspect it rather than overwriting evidence")
        return {"dataset_version": version, "checksum": dataset["checksum"],
                "product_ids": [row.product_id for row in existing], "created": False,
                "as_of_date": end_date.isoformat()}
    start = end_date - timedelta(days=days)
    opening_time = datetime.combine(start, time.min, timezone.utc)
    products = []
    inventories = []
    try:
        for idx, (sku, name, category, price, base) in enumerate(DEMO_PRODUCTS):
            product = Product(sku=f"DEMO2-{dataset['checksum'][:12]}-{sku}", name=name, category=category,
                              unit_price=Decimal(price), is_active=True, created_at=opening_time)
            db.add(product)
            db.flush()
            ending = max(5, round(base * 7 * (0.5 if idx % 2 == 0 else 4)))
            opening = dataset["totals"][idx] + ending
            inventory = Inventory(product_id=product.id, quantity_on_hand=opening)
            db.add(inventory)
            db.add(InventoryLog(product_id=product.id, change_quantity=opening, quantity_before=0,
                                quantity_after=opening, log_type="INIT", log_date=opening_time))
            db.add(ForecastCoverage(product_id=product.id, observed_from=start,
                                   observed_through=end_date - timedelta(days=1), source="synthetic",
                                   dataset_version=version,
                                   configuration={**dataset["config"], "checksum": dataset["checksum"],
                                                  "inventory_as_of": end_date.isoformat()}))
            db.add(ReplenishmentPolicy(product_id=product.id, lead_time_weeks=2, review_interval_weeks=1,
                                       safety_stock=round(base * 7), minimum_order_quantity=0,
                                       pack_size=1, version=1))
            products.append(product)
            inventories.append(inventory)
        for record in dataset["orders"]:
            timestamp = datetime.combine(date.fromisoformat(record["date"]), time(12), timezone.utc)
            order = SalesOrder(order_date=timestamp, created_at=timestamp,
                               sales_channel=record["channel"], total_amount=Decimal(0))
            db.add(order)
            db.flush()
            total = Decimal(0)
            for item in record["items"]:
                idx = item["product_index"]
                quantity = item["quantity"]
                price = Decimal(item["unit_price"])
                stock = inventories[idx]
                before = stock.quantity_on_hand
                stock.quantity_on_hand -= quantity
                total += price * quantity
                db.add(SalesItem(sales_order_id=order.id, product_id=products[idx].id, quantity=quantity,
                                 unit_price=price, line_total=price * quantity))
                db.add(InventoryLog(product_id=products[idx].id, change_quantity=-quantity,
                                    quantity_before=before, quantity_after=stock.quantity_on_hand,
                                    log_type="SALE", reference_id=order.id, log_date=timestamp))
            order.total_amount = total
        db.commit()
        return {"dataset_version": version, "checksum": dataset["checksum"],
                "product_ids": [p.id for p in products], "created": True,
                "as_of_date": end_date.isoformat()}
    except Exception:
        db.rollback()
        raise


def main():
    parser = argparse.ArgumentParser(description="Seed an isolated, deterministic dataset; never deletes existing data")
    parser.add_argument("--days", type=int, default=1092)
    parser.add_argument("--end-date", type=date.fromisoformat, default=DEFAULT_END,
                        help="Exclusive end, ideally a Monday for weekly decisions")
    parser.add_argument("--seed", type=int, default=RANDOM_SEED)
    args = parser.parse_args()
    from database.session import SessionLocal
    with SessionLocal() as db:
        print(json.dumps(seed_demo_sales(db, args.days, args.end_date, args.seed), indent=2))


if __name__ == "__main__":
    main()
