"""Versioned forecasting-only import; no invented stock or supplier information."""
import argparse
import csv
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[2]))

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.forecast_evidence import ForecastCoverage
from models.product import Product
from models.sales_item import SalesItem
from models.sales_order import SalesOrder


def _parse_date(value):
    for fmt in ("%m/%d/%Y %H:%M", "%m/%d/%y %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(value.strip(), fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    raise ValueError(f"Unsupported InvoiceDate: {value}")


def load_dataset(csv_path: Path) -> dict:
    digest = sha256()
    with csv_path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    checksum = digest.hexdigest()
    rows = []
    skipped = 0
    with csv_path.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        required = {"InvoiceNo", "StockCode", "Description", "Quantity", "InvoiceDate", "UnitPrice"}
        if not required.issubset(set(reader.fieldnames or [])):
            raise ValueError("Missing required UCI CSV columns")
        for line_number, raw in enumerate(reader, start=2):
            try:
                invoice = raw["InvoiceNo"].strip()
                sku = raw["StockCode"].strip().upper()
                quantity = int(raw["Quantity"])
                price = Decimal(raw["UnitPrice"])
                timestamp = _parse_date(raw["InvoiceDate"])
                if not sku or not invoice or not price.is_finite():
                    raise ValueError("Missing identifier or nonfinite price")
                if invoice.upper().startswith("C") or quantity <= 0 or price < 0:
                    skipped += 1
                    continue
                price = price.quantize(Decimal("0.01"))
                rows.append({"invoice": invoice, "sku": sku, "name": raw["Description"].strip() or sku,
                             "quantity": quantity, "price": price, "date": timestamp})
            except (ValueError, InvalidOperation, AttributeError, TypeError) as error:
                raise ValueError(f"Malformed CSV row {line_number}; cannot declare complete coverage: {error}") from error
    if not rows:
        raise ValueError("No usable positive-sales rows")
    # Boundary days may be partial in a transaction export; omit both conservatively.
    start = min(r["date"].date() for r in rows) + timedelta(days=1)
    end = max(r["date"].date() for r in rows)
    if start >= end:
        raise ValueError("CSV must span enough dates to contain complete interior days")
    rows = [r for r in rows if start <= r["date"].date() < end]
    return {"rows": rows, "start": start, "end": end, "checksum": checksum,
            "version": f"uci-v2-{checksum[:16]}", "skipped": skipped}


def import_uci_online_retail(db: Session, csv_path: Path) -> dict:
    dataset = load_dataset(csv_path)
    version = dataset["version"]
    existing = list(db.scalars(select(ForecastCoverage).where(ForecastCoverage.dataset_version == version)
                              .order_by(ForecastCoverage.product_id)))
    if existing:
        return {"dataset_version": version, "product_ids": [r.product_id for r in existing], "created": False}
    config = {"checksum": dataset["checksum"], "importer": "uci-v2", "timezone": "UTC",
              "positive_sales_only": True, "returns_excluded": True, "skipped_rows": dataset["skipped"],
              "coverage_assumption": "complete export over interior calendar days; no stockout information",
              "inventory": "unknown; not synthesized"}
    grouped = defaultdict(list)
    first_dates = {}
    for row in dataset["rows"]:
        grouped[row["invoice"]].append(row)
        first_dates[row["sku"]] = min(first_dates.get(row["sku"], row["date"].date()), row["date"].date())
    products = {}
    try:
        for row in dataset["rows"]:
            if row["sku"] in products:
                continue
            product = Product(sku=f"UCI2-{dataset['checksum'][:12]}-{row['sku']}", name=row["name"][:255],
                              category="Public Online Retail", unit_price=row["price"], is_active=True,
                              created_at=datetime.combine(dataset["start"], datetime.min.time(), timezone.utc))
            db.add(product)
            db.flush()
            products[row["sku"]] = product
            # Do not invent pre-listing zeros: coverage begins on this SKU's first observed day.
            first = first_dates[row["sku"]]
            db.add(ForecastCoverage(product_id=product.id, observed_from=first,
                                   observed_through=dataset["end"] - timedelta(days=1),
                                   source="uci_online_retail", dataset_version=version, configuration=config))
        for invoice, rows in sorted(grouped.items()):
            if len({r["date"].date() for r in rows}) != 1:
                raise ValueError(f"Invoice {invoice} spans multiple dates; inspect source")
            reference = f"{version}:{invoice}"
            if len(reference) > 160:
                raise ValueError("External invoice reference too long")
            order = SalesOrder(order_date=rows[0]["date"], created_at=rows[0]["date"], sales_channel="PUBLIC",
                               external_reference=reference, total_amount=Decimal(0))
            db.add(order)
            db.flush()
            for row in rows:
                line = row["price"] * row["quantity"]
                order.total_amount += line
                db.add(SalesItem(sales_order_id=order.id, product_id=products[row["sku"]].id,
                                 quantity=row["quantity"], unit_price=row["price"], line_total=line))
        db.commit()
        return {"dataset_version": version, "product_ids": [p.id for p in products.values()], "created": True,
                "observed_from": dataset["start"].isoformat(), "end_exclusive": dataset["end"].isoformat(),
                "rows_imported": len(dataset["rows"]), "skipped_rows": dataset["skipped"]}
    except Exception:
        db.rollback()
        raise


def main():
    parser = argparse.ArgumentParser(description="Import a complete UCI CSV as an isolated forecasting dataset")
    parser.add_argument("csv_path", type=Path)
    args = parser.parse_args()
    from database.session import SessionLocal
    with SessionLocal() as db:
        print(json.dumps(import_uci_online_retail(db, args.csv_path), indent=2))


if __name__ == "__main__":
    main()
