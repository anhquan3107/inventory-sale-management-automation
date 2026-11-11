# Dataset Seeding Guide

This project can use two portfolio datasets:

1. Generated demo sales data.
2. Public UCI Online Retail data.

Use generated demo data first because it is clean, controlled, and designed to show weekly/monthly forecasting behavior. Use the public dataset second to show that the project can process external retail transactions.

## 1. Generated Demo Data

Script:

```bash
docker compose exec backend python utils/scripts/seed_demo_sales.py
```

What it creates:

- 12 demo products with `DEMO-` SKU prefix.
- Inventory rows for those products.
- One year of sales orders and sales items.
- Sales patterns with weekly behavior, seasonal spikes, random noise, slow movers, fast movers, and holiday demand.

Why it is useful:

- Good for testing moving average and exponential smoothing quickly.
- Good for portfolio screenshots because product names and demand patterns are understandable.
- Repeatable because the script uses a fixed random seed.

After seeding, generate forecasts from the API:

```bash
curl -X POST http://localhost:8000/forecast/generate \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"weekly_horizon":8,"monthly_horizon":6}'
```

Then inspect:

```bash
curl "http://localhost:8000/forecast/predictions?granularity=weekly" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

```bash
curl "http://localhost:8000/forecast/accuracy?granularity=weekly" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## 2. Public UCI Online Retail Data

Download source:

```text
https://archive.ics.uci.edu/dataset/352/online+retail
```

The original file is commonly provided as Excel. Convert it to CSV first and place it somewhere mounted into the backend container, for example:

```text
backend/app/data/online_retail.csv
```

Then run:

```bash
docker compose exec backend python utils/scripts/import_uci_online_retail.py data/online_retail.csv
```

Optional row limit:

```bash
docker compose exec backend python utils/scripts/import_uci_online_retail.py data/online_retail.csv --limit-rows 50000
```

Mapping:

```text
StockCode   -> products.sku, prefixed with UCI-
Description -> products.name
InvoiceNo   -> grouped into one sales order
InvoiceDate -> sales_orders.order_date
Quantity    -> sales_items.quantity
UnitPrice   -> sales_items.unit_price
```

Filtering:

- Cancelled invoices are skipped.
- Rows with quantity <= 0 are skipped.
- Rows with invalid dates are skipped.
- Empty stock codes are skipped.

Important portfolio note:

Use generated demo data when explaining controlled forecasting behavior. Use UCI data when explaining public-data ingestion and real-world messy transaction cleanup.

