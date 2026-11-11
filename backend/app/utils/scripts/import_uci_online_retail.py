from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
import sys

from sqlalchemy import select
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


PUBLIC_SKU_PREFIX = "UCI-"
DEFAULT_LIMIT_ROWS = 75_000


def _money(value: str | Decimal) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"))


def _parse_date(value: str) -> datetime:
    for fmt in ("%m/%d/%Y %H:%M", "%m/%d/%y %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(value.strip(), fmt)
        except ValueError:
            continue
    raise ValueError(f"Unsupported InvoiceDate format: {value}")


def _clean_sku(value: str) -> str:
    return f"{PUBLIC_SKU_PREFIX}{value.strip().upper()}"


def _load_rows(csv_path: Path, limit_rows: int) -> list[dict]:
    rows: list[dict] = []

    with csv_path.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)

        required_columns = {"InvoiceNo", "StockCode", "Description", "Quantity", "InvoiceDate", "UnitPrice"}
        missing_columns = required_columns - set(reader.fieldnames or [])
        if missing_columns:
            raise ValueError(f"Missing required columns: {sorted(missing_columns)}")

        for raw in reader:
            if len(rows) >= limit_rows:
                break

            try:
                stock_code = raw["StockCode"].strip()
                description = raw["Description"].strip() or stock_code
                quantity = int(raw["Quantity"])
                unit_price = _money(raw["UnitPrice"])
                invoice_date = _parse_date(raw["InvoiceDate"])
                invoice_no = raw["InvoiceNo"].strip()
            except (ValueError, InvalidOperation):
                continue

            if not stock_code or not invoice_no:
                continue
            if invoice_no.upper().startswith("C"):
                continue
            if quantity <= 0 or unit_price < 0:
                continue

            rows.append(
                {
                    "invoice_no": invoice_no,
                    "sku": _clean_sku(stock_code),
                    "name": description[:255],
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "invoice_date": invoice_date,
                    "country": (raw.get("Country") or "PUBLIC").strip() or "PUBLIC",
                }
            )

    return rows


def import_uci_online_retail(csv_path: Path, limit_rows: int = DEFAULT_LIMIT_ROWS) -> None:
    db: Session = SessionLocal()

    try:
        rows = _load_rows(csv_path, limit_rows)
        if not rows:
            raise ValueError("No usable rows found in CSV.")

        product_by_sku: dict[str, Product] = {
            product.sku: product
            for product in db.execute(
                select(Product).where(Product.sku.like(f"{PUBLIC_SKU_PREFIX}%"))
            ).scalars()
        }

        products_created = 0
        for row in rows:
            if row["sku"] in product_by_sku:
                continue

            product = Product(
                sku=row["sku"],
                name=row["name"],
                category="Public Online Retail",
                unit_price=row["unit_price"],
                is_active=True,
            )
            db.add(product)
            product_by_sku[row["sku"]] = product
            products_created += 1

        db.flush()

        inventory_by_product_id: dict[int, Inventory] = {
            inventory.product_id: inventory
            for inventory in db.execute(
                select(Inventory).where(
                    Inventory.product_id.in_([product.id for product in product_by_sku.values()])
                )
            ).scalars()
        }

        inventory_created = 0
        for product in product_by_sku.values():
            if product.id in inventory_by_product_id:
                continue

            initial_quantity = 100_000
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
            inventory_created += 1

        invoice_rows: dict[str, list[dict]] = defaultdict(list)
        for row in rows:
            invoice_rows[row["invoice_no"]].append(row)

        orders_created = 0
        items_created = 0

        for invoice_no, invoice_items in invoice_rows.items():
            first_row = invoice_items[0]
            existing_reference = db.execute(
                select(SalesOrder.id).where(
                    SalesOrder.sales_channel == f"UCI:{invoice_no}"
                )
            ).scalar_one_or_none()
            if existing_reference:
                continue

            order = SalesOrder(
                order_date=first_row["invoice_date"],
                created_at=first_row["invoice_date"],
                sales_channel=f"UCI:{invoice_no}",
                total_amount=Decimal("0.00"),
            )
            db.add(order)
            db.flush()

            total_amount = Decimal("0.00")
            for row in invoice_items:
                product = product_by_sku[row["sku"]]
                line_total = (row["unit_price"] * row["quantity"]).quantize(Decimal("0.01"))
                db.add(
                    SalesItem(
                        sales_order_id=order.id,
                        product_id=product.id,
                        quantity=row["quantity"],
                        unit_price=row["unit_price"],
                        line_total=line_total,
                    )
                )
                total_amount += line_total
                items_created += 1

            order.total_amount = total_amount
            orders_created += 1

        db.commit()

        print("UCI Online Retail data imported successfully.")
        print(f"Rows read: {len(rows)}")
        print(f"Products created: {products_created}")
        print(f"Inventory rows created: {inventory_created}")
        print(f"Sales orders created: {orders_created}")
        print(f"Sales items created: {items_created}")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import UCI Online Retail CSV data into the app schema."
    )
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--limit-rows", type=int, default=DEFAULT_LIMIT_ROWS)
    args = parser.parse_args()

    import_uci_online_retail(args.csv_path, args.limit_rows)


if __name__ == "__main__":
    main()
