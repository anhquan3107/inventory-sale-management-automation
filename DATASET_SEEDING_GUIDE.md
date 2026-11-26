# Reproducible Forecasting and Decision Support

## 1. Apply the additive migrations

Back up any database you care about first. The new migrations add metadata/evidence
and decision tables; they do not delete existing products, sales, or forecasts.
Existing forecast runs remain legacy runs and cannot generate DSS recommendations.

```bash
docker compose up -d --build
docker compose exec backend alembic upgrade head
docker compose exec backend python utils/scripts/seed_admin.py
```

Docker startup still does not migrate or seed automatically. Log in and change the
initial administrator password when required. All examples below use a fresh access
token, not an old token copied from a previous run.

## 2. Generate the isolated synthetic dataset

```bash
docker compose exec backend python utils/scripts/seed_demo_sales.py
```

Defaults are deliberately fixed: 1,092 days ending **before 2026-11-16**, random seed
20260623, generator demo-v2. The exclusive end is a Monday suitable for weekly review.
This supplies three years of controlled sales, not three years of real business evidence.

The output contains `dataset_version`, `checksum`, `product_ids`, `as_of_date`, and
`created`. Copy the actual product IDs into the API request, not Swagger's old `[0]`.

- Same configuration: same generated transactions/checksum; rerun reuses existing products.
- Different configuration: a separate SKU namespace and dataset, never a replacement.
- Old DEMO products and forecast evidence are left untouched.
- Opening stock covers generated sales plus a deterministic ending balance. Every sale
  has a matching inventory deduction and SALE log, so balances reconcile.
- This stock is simulated, not sourced from a business. There are no simulated lost
  sales or supplier purchase orders. Default per-product replenishment policies are examples.
- IDs, forecast UUIDs, and execution timestamps are not reproducibility targets;
  generated event dates, quantities, prices, source configuration, and scores are.

An explicitly configured alternative:

```bash
docker compose exec backend python utils/scripts/seed_demo_sales.py --days 728 --end-date 2026-11-16 --seed 42
```

Do not edit an experiment's historical transactions and expect its version label to
prove immutability. Each forecast stores the actual aggregate history it used so
later edits do not rewrite that run's evidence.

## 3. Forecast with the same cutoff

In Swagger at `/docs`, authorize and submit to `POST /forecast/generate`:

```json
{
  "as_of_date": "2026-11-16",
  "weekly_horizon": 8,
  "monthly_horizon": 6,
  "product_ids": [YOUR_ACTUAL_PRODUCT_ID]
}
```

`YOUR_ACTUAL_PRODUCT_ID` is a placeholder: replace it with a numeric ID from the seed.
Omitting `product_ids` targets all active products, including older products without coverage.

`as_of_date` is an exclusive information cutoff at midnight UTC. Weekly training ends
before the Monday containing that date; monthly training ends before its first day.
The first forecast is for that current full week/month. An unfinished current period
is never used as a completed training label. Mid-period forecasts describe the whole
current period, not its remaining days, and cannot drive the weekly DSS.

Inspect these authenticated endpoints with the returned run ID:

- `GET /forecast/predictions?granularity=weekly&run_id=RUN_ID`
- `GET /forecast/accuracy?granularity=weekly&run_id=RUN_ID`
- `GET /forecast/backtest-points?run_id=RUN_ID&product_id=PRODUCT_ID&granularity=weekly`
- `GET /forecast/coverage`

Accuracy `details` includes the input history, coverage/version, candidate validation
and test metrics, and horizon-specific scores. Backtest points are paginated with
`limit` and `offset`. Bias is predicted minus actual: positive means overforecasting.
MAE selects among naive, MA(4), and SES(alpha=0.35), with simpler models winning ties.
The last complete requested horizon is the final test; up to three earlier disjoint
horizons provide expanding-origin validation. Predictions inside a horizon are recursive,
never updated with that horizon's actuals. The selected model is then refit on all history.

Minimum training history is 8 weekly or 4 monthly periods. Evaluation requires at least
that much history plus two full requested horizons. A shorter but usable series gets
an explicitly unevaluated MA fallback; unknown coverage, too little history, or no
sales signal produces no predictions. Missing evaluation scores are null, never fake zeros.
Only evaluated weekly forecasts may generate recommendations. No calibrated uncertainty
method exists yet, so new prediction bounds are null rather than claimed 95% intervals.

Legacy products need an explicit declaration before zero-filling is justified:
`PUT /forecast/coverage/PRODUCT_ID` with complete, continuous dates, a source,
`dataset_version`, optional configuration, and `confirms_complete_sales: true`.
Do not declare complete coverage over ingestion outages or unknown periods. Changing
coverage requires a new version. Observed-through is inclusive and cannot include today.

## 4. Configure and generate advisory decisions

The seed creates example policies. To change one, use `PUT /decisions/policies/PRODUCT_ID`:

```json
{
  "lead_time_weeks": 2,
  "review_interval_weeks": 1,
  "safety_stock": 20,
  "minimum_order_quantity": 0,
  "pack_size": 12
}
```

Use `POST /decisions/generate` with an evaluated Monday-cutoff forecast:

```json
{
  "request_key": "demo-review-001",
  "run_id": "RUN_ID",
  "product_id": YOUR_ACTUAL_PRODUCT_ID,
  "mode": "simulation",
  "simulated_on_hand": 50,
  "simulated_receipts": [{"arrival_week": 2, "quantity": 20}]
}
```

This is a simulation. Stock inputs refer to the forecast's Monday review date, not
today's warehouse. Receipts arrive before demand in their numbered week. The service:

1. Requires enough forecast weeks for lead time plus review interval.
2. Calculates position = on-hand + existing incoming receipts (no reservations yet).
3. Calculates target = forecast protection-period demand + configured safety stock.
4. Orders max(0, target - position), rounded up to whole units, MOQ, and pack size.
5. Projects weekly stock using only existing receipts and flags any shortage separately.
6. Saves immutable calculation inputs, policy version, forecast, explanation, and status.

Late receipts can yield a stockout-risk warning even if total inventory position is high.
Risk is a deterministic scenario flag, not a calibrated probability or guarantee.
Changing inputs requires a new request key; retries with the same key/inputs reuse the record.

Review using `PATCH /decisions/recommendations/RECOMMENDATION_ID`:

```json
{"action": "approved"}
```

Or `{"action":"modified","quantity":48,"reason":"Adjusted purchase plan"}`,
or `{"action":"rejected","reason":"Supplier unavailable"}`. Modifications still
respect MOQ/pack size; zero means no purchase. Each record can be reviewed once.
Policy changes block approval until regeneration. Approval never changes stock and
does not create a purchase order. All decision endpoints require an active administrator.

`mode: live` is intentionally restricted: today's Monday review, database on-hand,
no simulated receipts. It assumes zero outstanding supplier orders because purchasing
integration is not implemented; `confirms_no_incoming_orders: true` is required.
Do not use it operationally if incoming supply exists.
Stale date/stock/policy snapshots cannot be approved. Reservations, purchase orders,
receipts, budgets, and calibrated safety stock are later extensions.

## 5. Public UCI data: forecasting only

Source: [UCI Online Retail](https://archive.ics.uci.edu/dataset/352/online+retail).
Convert the complete source to UTF-8 CSV with InvoiceNo, StockCode, Description,
Quantity, InvoiceDate, and UnitPrice; mount it at `backend/app/data/online_retail.csv`.

```bash
docker compose exec backend python utils/scripts/import_uci_online_retail.py data/online_retail.csv
```

The importer hashes the exact file, creates version-isolated UCI2 SKUs, groups complete
invoices, stores external invoice references separately from channel, and reuses an
existing identical import. It excludes cancellations, nonpositive quantities, and
negative prices. Malformed rows or nonfinite prices fail the import instead of silently
creating unknown gaps. Returns are not netted from positive sales.
It reads the whole CSV: row limiting was removed to avoid partial invoices and false
coverage claims. It omits boundary dates as potentially partial days and starts each
SKU's coverage no earlier than its first retained sale. Remaining zero-fill assumes a
complete export; this does not establish stock availability or true unmet demand.

No inventory or replenishment policy is invented. Use an explicit historical cutoff
within the returned coverage, preferably a Monday for simulation. Do not forecast old
transactions using today's cutoff. Changing CSV bytes creates a new dataset, even if
the logical rows happen to be the same.

## 6. Run tests without touching your application database

From the repository root, in a Python 3.11+ virtual environment:

```bash
pip install -r backend/requirements-dev.txt
python -m unittest discover -s backend/tests -v
```

Tests use temporary/in-memory SQLite, override API database dependencies, and never
connect to your application database. They cover model arithmetic, leakage, holdouts,
coverage, seed reproducibility, stock reconciliation, API permissions, decision history,
and additive migrations. PostgreSQL migration SQL is compiled separately; this is not
a substitute for exercising migrations against a disposable PostgreSQL instance.
