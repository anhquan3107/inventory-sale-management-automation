# Inventory DSS code flow

## Baseline

The existing replenishment service calculates a weekly order and saves its inputs and result as a recommendation snapshot. `ReplenishmentPolicy` holds the versioned settings for a product. `RecommendationDecision` holds one final review per recommendation. The DSS consumes the saved weekly forecast selected by the forecasting pipeline.

The [implementation checklist](DSS_IMPLEMENTATION_CHECKLIST.md) tracks each phase.

## Phase 1 — One SKU from forecast to review

1. Open **Decisions** at `/decisions`. The admin selects a product, saves its policy, and enters the ID of a saved run in `SavedForecastForm`. The shared Axios client loads weekly evaluation and predictions. The form shows the run's review date and flags missing evidence, a short horizon, or a gap in weekly periods.
2. `ScenarioForm` sends `POST /decisions/generate` with that run, the chosen product, and explicit simulated on-hand and receipts. Live uses current database stock and requires today's Monday run and confirmation of zero incoming orders. An uncertain retry reuses the request key for the same inputs and policy version.
3. `services/replenishment.py` validates the saved run, policy, and weekly evidence. `calculate_replenishment` computes the target, inventory position, and rounded order. The weekly projection adds existing receipts at the start of each week and subtracts forecast demand. All incoming quantities count toward inventory position, including receipts scheduled after the protection period. The weekly projection includes receipts only in their scheduled weeks and excludes the suggested order.
4. `services/recommendation_diagnostics.py` reads the projected balances to find the first week below zero, its deficit, the largest deficit, and whether the first shortage falls within lead time. The backend stores this under `snapshot.diagnostics`. A read of an older snapshot derives its diagnostics from the original saved inputs in memory. Incomplete inputs produce an unsupported-snapshot status.
5. `RecommendationDetail` shows the calculation, dated forecast buckets, and shortage explanation. The admin sends `PATCH /decisions/recommendations/{id}` to approve, modify, or reject. The backend records one final review and the authenticated actor, and checks for stale policy, an inactive product, or changed live inputs before approval or modification. The review leaves inventory and sales evidence untouched.

The controlled fixture uses weekly demand of 65.89, lead time of two weeks, a one-week review interval, safety stock of 20, 50 simulated units on hand, 20 arriving in week 2, and packs of 12. It produces target stock of 217.67, an inventory position of 70, and an order of 156. Week 1 ends at −15.89 and the largest projected deficit is 127.67 units. Moving the receipt to week 1 leaves the order at 156 and moves the first shortage to week 2.

## Phase 2 — Exception workspace

1. `ExceptionWorkspace` sends `GET /decisions/exceptions` with the selected run, mode, filters, and pagination. Generating a recommendation preselects that run and mode. Decisions reload the open exception view after a successful review.
2. `services/inventory_exceptions.py` reads the run's target product IDs. Older runs without a target list fall back to their saved weekly accuracy and prediction rows. The query selects the largest recommendation ID per target product for the selected mode before applying status filters. The exception list reads saved snapshots and forecast evidence and does not read current on-hand stock.
3. The service sorts urgent shortage, later shortage, planned replenishment, and excess-stock review before no exception. Missing forecasts or a horizon that cannot support the policy are reported as insufficient evidence. Eligible SKUs that still need a recommendation are reported separately. An unsupported saved snapshot shows a missing quantity. A calculated zero order remains visible as zero.
4. The versioned excess rule checks whether inventory position is strictly above twice the positive target. The detail shows the factor, threshold, and units above it. A positive position against a zero target has its own reason. A late receipt can trigger both an urgent shortage and excess review.
5. The table sends the selected recommendation ID to the existing detail endpoint. The response includes the original inputs and final review. A historical snapshot with incomplete evidence can still be rejected through the API.

`total` counts matching SKUs before pagination. `scope_total` and `missing_recommendations` describe the full run and mode regardless of filters. The MVP uses the existing JSON snapshot and relational tables. Pagination limits the response size. The server still classifies the run before slicing, so measure large runs in PostgreSQL before deciding whether an index is warranted.

`backend/app/schemas/inventory_exceptions.py` defines the Pydantic response contract for FastAPI and OpenAPI. The exception items are computed when queried. The database models and migrations stay in their existing files. New diagnostics are saved as keys in the existing recommendation snapshot JSON column.

## Phase 3 — Verification and demonstration

### Demo with the project's synthetic sales seed

1. In a disposable project setup, seed sales using [the dataset guide](../DATASET_SEEDING_GUIDE.md). Use the product IDs returned by the seed. Create a forecast at the historical Monday cutoff `2026-11-16`, with enough weeks for the policy. Copy the run ID from the response. An evaluated forecast has completed the evaluation protocol. Its accuracy still varies by product.
2. Sign in as an active admin and open `/decisions`. Select a seeded product. Set lead time to 2, review interval to 1, safety stock to 20, and pack size to 12. Load the saved forecast by ID. Use **Simulation** with 0 on hand and a receipt of 20 units in week 2. Inspect the first shortage and the order quantity, which depend on the forecast returned by the API.
3. Approve the recommendation in the detail dialog. Close the dialog and inspect the **Approved** status in the exception table and history. Compare the warehouse on-hand count before and after the decision.
4. Generate another recommendation with on-hand stock above twice the displayed target to demonstrate excess review. Load a run with a product whose sales coverage is unknown to demonstrate insufficient evidence. Generate a pending recommendation, edit its policy, and then attempt to approve the old snapshot to reproduce the `409` conflict. Rejection remains available.

### API examples

Use an active admin's bearer token from the demo environment. Set `PRODUCT_ID`, `RUN_ID`, and `RECOMMENDATION_ID` from the actual responses.

```bash
curl -fsS http://localhost:8000/forecast/generate \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d "{\"product_ids\":[$PRODUCT_ID],\"as_of_date\":\"2026-11-16\",\"weekly_horizon\":8,\"monthly_horizon\":3}"

curl -fsS -X PUT "http://localhost:8000/decisions/policies/$PRODUCT_ID" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"lead_time_weeks":2,"review_interval_weeks":1,"safety_stock":20,"minimum_order_quantity":0,"pack_size":12}'

curl -fsS http://localhost:8000/decisions/generate \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d "{\"request_key\":\"$REQUEST_KEY\",\"run_id\":\"$RUN_ID\",\"product_id\":$PRODUCT_ID,\"mode\":\"simulation\",\"simulated_on_hand\":0,\"simulated_receipts\":[{\"arrival_week\":2,\"quantity\":20}]}"

curl -fsS -G http://localhost:8000/decisions/exceptions \
  -H "Authorization: Bearer $TOKEN" \
  --data-urlencode "run_id=$RUN_ID" --data-urlencode 'mode=simulation' \
  --data-urlencode 'limit=10' --data-urlencode 'offset=0'

curl -fsS -X PATCH "http://localhost:8000/decisions/recommendations/$RECOMMENDATION_ID" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"action":"approved"}'
```

Create a fresh `REQUEST_KEY` for each intended recommendation and reuse it when retrying the same request. The approval endpoint returns `409` for repeat reviews and stale-policy approval attempts. The exception endpoint returns `404` for an unknown run and `422` for invalid query parameters.

### Verification performed

- Backend suite via `python -m unittest discover -s backend/tests -v`. The focused DSS fixtures cover shortage timing, excess and zero target, old snapshots, mode and review filters, pagination, authorization, conflicts, and advisory-only review.
- PostgreSQL 15.20 with a disposable cluster on a private Unix socket. Parallel generation returned the same recommendation ID twice. Parallel approval returned one success and one `409`. The exception query returned the approved recommendation, the database held one recommendation and one decision, and on-hand stock stayed at 90.
- Frontend `npm run lint` and `npm run build`. In a browser against a disposable FastAPI fixture, a saved run with 65.89 units of weekly demand produced a 156-unit proposal and a 15.89-unit first-week deficit. Approval refreshed the exception row. At a 390 px viewport the table could scroll horizontally within the page.

### Integration boundary

Sales import supplies product IDs, historical sales, and confirmed sales coverage. A separate forecast run supplies the weekly evidence to DSS. An imported SKU can use an explicit simulation after policy setup, even before warehouse stock has been initialized. The separate Member 3 implementation remains a team integration check. The UI takes a run ID explicitly, and the live mode requires a current Monday run and an explicit confirmation about incoming orders.
