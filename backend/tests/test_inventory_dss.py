from datetime import date, timedelta
from decimal import Decimal
import unittest

from test_forecast_dss import DatabaseFixture

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from database.dependencies import get_db
from models.forecast_accuracy import ForecastAccuracy
from models.forecast_prediction import ForecastPrediction
from models.forecast_run import ForecastRun
from models.inventory import Inventory
from models.product import Product
from models.replenishment import InventoryRecommendation, RecommendationDecision
from models.user import User
from routers.decisions import router
from services.recommendation_diagnostics import diagnose_recommendation
from services.replenishment import calculate_replenishment, generate_recommendation, put_policy, review_recommendation
from utils.security.bearer import require_auth


REVIEW_DATE = date(2026, 11, 16)
DEMAND = Decimal("65.89")
POLICY = {"lead_time_weeks": 2, "review_interval_weeks": 1, "safety_stock": 20,
          "minimum_order_quantity": 0, "pack_size": 12}


def add_forecast(db, run, product_id, status="evaluated", weeks=3):
    db.add(ForecastAccuracy(run_ref_id=run.id, product_id=product_id, granularity="weekly",
                            selected_model="naive", training_points=30, details={"status": status}))
    if status == "evaluated":
        for index in range(weeks):
            period = run.as_of_date + timedelta(weeks=index)
            db.add(ForecastPrediction(run_ref_id=run.id, product_id=product_id, granularity="weekly",
                                      horizon_step=index + 1, selected_model="naive", period_start=period,
                                      period_end=period + timedelta(days=6), predicted_quantity=DEMAND))


def add_run(db, run_id, product_ids=None, review_date=REVIEW_DATE):
    settings = {"version": "baseline-v2"}
    if product_ids is not None:
        settings["product_ids"] = product_ids
    run = ForecastRun(run_id=run_id, as_of_date=review_date, weekly_horizon=3,
                      monthly_horizon=1, total_products=len(product_ids or []), settings=settings)
    db.add(run)
    db.flush()
    return run


def request_for(run_id, product_id, key="simulation-1", on_hand=50, receipts=()):
    return {"request_key": key, "run_id": run_id, "product_id": product_id, "mode": "simulation",
            "simulated_on_hand": on_hand, "simulated_receipts": list(receipts), "confirms_no_incoming_orders": False}


class ShortageTests(unittest.TestCase):
    def analyze(self, on_hand, receipts=(), demand=DEMAND, policy=POLICY):
        protection = policy["lead_time_weeks"] + policy["review_interval_weeks"]
        periods = [REVIEW_DATE + timedelta(weeks=index) for index in range(protection)]
        result = calculate_replenishment([demand] * protection, on_hand, list(receipts), policy)
        return result, diagnose_recommendation(result, periods, policy["lead_time_weeks"])

    def test_earlier_receipt_delays_shortage_without_changing_order(self):
        result, diagnostic = self.analyze(50, [{"arrival_week": 2, "quantity": 20}])
        self.assertEqual(result["target_stock"], "217.67")
        self.assertEqual(result["inventory_position"], 70)
        self.assertEqual(result["suggested_quantity"], 156)
        self.assertEqual(result["projected_week_end_stock"], ["-15.89", "-61.78", "-127.67"])
        self.assertEqual(diagnostic["first_shortage_step"], 1)
        self.assertEqual(diagnostic["first_shortage_period_start"], "2026-11-16")
        self.assertEqual(diagnostic["first_shortage_quantity"], "15.89")
        self.assertEqual(diagnostic["maximum_projected_deficit"], "127.67")
        self.assertTrue(diagnostic["shortage_during_lead_time"])
        result, diagnostic = self.analyze(50, [{"arrival_week": 1, "quantity": 20}])
        self.assertEqual(result["suggested_quantity"], 156)
        self.assertEqual(diagnostic["first_shortage_step"], 2)

    def test_exactly_zero_is_not_a_shortage(self):
        policy = {**POLICY, "lead_time_weeks": 1}
        _, diagnostic = self.analyze(10, demand=Decimal(10), policy=policy)
        self.assertEqual(diagnostic["first_shortage_step"], 2)
        self.assertFalse(diagnostic["shortage_during_lead_time"])
        _, diagnostic = self.analyze(20, demand=Decimal(10), policy=policy)
        self.assertIsNone(diagnostic["first_shortage_step"])
        self.assertIsNone(diagnostic["first_shortage_period_start"])
        self.assertIsNone(diagnostic["first_shortage_quantity"])
        self.assertEqual(diagnostic["maximum_projected_deficit"], "0")

    def test_excess_threshold_does_not_hide_urgent_shortage(self):
        for on_hand in (300, 400):
            result, diagnostic = self.analyze(on_hand)
            self.assertEqual(result["suggested_quantity"], 0)
            self.assertFalse(diagnostic["excess_stock_review"])
        result, diagnostic = self.analyze(500)
        self.assertEqual(result["suggested_quantity"], 0)
        self.assertTrue(diagnostic["excess_stock_review"])
        self.assertEqual(diagnostic["excess_stock_threshold"], "435.34")
        self.assertEqual(diagnostic["excess_above_review_threshold"], "64.66")

        result, diagnostic = self.analyze(0, [{"arrival_week": 4, "quantity": 500}])
        self.assertEqual(result["suggested_quantity"], 0)
        self.assertTrue(diagnostic["excess_stock_review"])
        self.assertTrue(diagnostic["shortage_during_lead_time"])
        self.assertEqual(diagnostic["first_shortage_quantity"], "65.89")

    def test_zero_target_uses_a_separate_flag_and_threshold_is_strict(self):
        _, diagnostic = self.analyze(10, demand=Decimal(0), policy={**POLICY, "safety_stock": 0})
        self.assertTrue(diagnostic["zero_demand_stock_review"])
        self.assertFalse(diagnostic["excess_stock_review"])
        self.assertIsNone(diagnostic["excess_stock_threshold"])
        _, diagnostic = self.analyze(100, demand=Decimal(10))
        self.assertFalse(diagnostic["excess_stock_review"])
        self.assertEqual(diagnostic["excess_above_review_threshold"], "0")


class RecommendationFlowTests(DatabaseFixture):
    def test_one_product_snapshot_retries_and_final_review(self):
        product_id = self.product().id
        run = add_run(self.db, "dss-sku-run", [product_id])
        add_forecast(self.db, run, product_id)
        self.db.add(Inventory(product_id=product_id, quantity_on_hand=90))
        self.db.commit()
        put_policy(self.db, product_id, POLICY)
        payload = request_for(run.run_id, product_id, receipts=[{"arrival_week": 2, "quantity": 20}])

        recommendation = generate_recommendation(self.db, payload, 1)
        recommendation_id = recommendation["id"]
        self.assertEqual(recommendation["status"], "pending")
        self.assertEqual(recommendation["snapshot"]["diagnostics"]["first_shortage_quantity"], "15.89")
        self.assertEqual(generate_recommendation(self.db, payload, 1)["id"], recommendation_id)
        with self.assertRaisesRegex(ValueError, "different inputs"):
            generate_recommendation(self.db, {**payload, "simulated_on_hand": 51}, 1)

        decision = review_recommendation(self.db, recommendation_id, {"action": "approved"}, 1)
        self.assertEqual(decision["status"], "approved")
        self.assertEqual(decision["decision"]["quantity"], 156)
        self.assertEqual(decision["snapshot"], recommendation["snapshot"])
        with self.assertRaisesRegex(ValueError, "already been reviewed"):
            review_recommendation(self.db, recommendation_id, {"action": "approved"}, 1)
        self.assertEqual(self.db.query(Inventory).filter_by(product_id=product_id).one().quantity_on_hand, 90)
        self.assertEqual(self.db.get(InventoryRecommendation, recommendation_id).snapshot, recommendation["snapshot"])


class ExceptionApiTests(DatabaseFixture):
    def setUp(self):
        super().setUp()
        app = FastAPI()
        app.include_router(router)
        self.claims = {"sub": "1", "role": "admin"}
        app.dependency_overrides[require_auth] = lambda: self.claims

        def session():
            try:
                yield self.db
            finally:
                self.db.rollback()

        app.dependency_overrides[get_db] = session
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        self.db.add(User(id=1, username="dss-admin", email="dss@example.invalid", password_hash="unused",
                         role="admin", is_active=True))
        self.db.commit()

    def products(self, *skus):
        self.db.add_all(Product(sku=sku, name=sku, unit_price=2, is_active=True) for sku in skus)
        self.db.flush()
        return {product.sku: product.id for product in self.db.scalars(select(Product))}

    def generate(self, run_id, product_id, key, on_hand=50, receipts=()):
        response = self.client.post("/decisions/generate", json=request_for(run_id, product_id, key, on_hand, receipts))
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def exceptions(self, run_id, **params):
        response = self.client.get("/decisions/exceptions", params={"run_id": run_id, **params})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_priority_snapshot_modes_latest_before_review_filter_and_totals(self):
        ids = self.products("urgent", "later", "planned", "excess", "clear", "no-data", "waiting", "short", "gap", "outside")
        run = add_run(self.db, "exceptions-run", [value for sku, value in ids.items() if sku != "outside"])
        for sku, product_id in ids.items():
            if sku != "gap":
                add_forecast(self.db, run, product_id, "coverage_ends_before_cutoff" if sku == "no-data" else "evaluated",
                             weeks=2 if sku == "short" else 3)
        add_forecast(self.db, run, ids["gap"])
        self.db.flush()
        gap_week = self.db.scalar(select(ForecastPrediction).where(ForecastPrediction.product_id == ids["gap"],
                                                                  ForecastPrediction.horizon_step == 2))
        gap_week.horizon_step = 4
        run_ref = run.id
        self.db.commit()
        for sku in ("urgent", "later", "planned", "excess", "clear", "short", "gap", "outside"):
            put_policy(self.db, ids[sku], POLICY)
        self.generate("exceptions-run", ids["urgent"], "old-pending")
        latest = self.generate("exceptions-run", ids["urgent"], "late-supply", 0, [{"arrival_week": 4, "quantity": 500}])
        self.generate("exceptions-run", ids["later"], "later", 140)
        self.generate("exceptions-run", ids["planned"], "planned", 200)
        self.generate("exceptions-run", ids["excess"], "excess", 500)
        self.generate("exceptions-run", ids["clear"], "clear", 300)
        self.generate("exceptions-run", ids["outside"], "outside", 0)
        response = self.client.patch(f"/decisions/recommendations/{latest['id']}", json={"action": "approved"})
        self.assertEqual(response.status_code, 200, response.text)

        # Represent an existing live snapshot for the historical run without bypassing the live generation guard.
        self.db.add(InventoryRecommendation(run_ref_id=run_ref, product_id=ids["urgent"], request_key="live-fixture",
                    snapshot={**latest["snapshot"], "mode": "live"}, suggested_quantity=0,
                    action="no_action", status="pending", created_by_user_id=1))
        self.db.commit()

        first_page = self.exceptions("exceptions-run", limit=2)
        self.assertEqual((first_page["total"], first_page["scope_total"], first_page["missing_recommendations"]), (9, 9, 4))
        self.assertEqual([item["classification"] for item in first_page["items"]],
                         ["shortage_within_lead_time", "shortage_after_lead_time"])
        urgent = first_page["items"][0]
        self.assertEqual((urgent["recommendation_id"], urgent["review_status"], urgent["suggested_quantity"]),
                         (latest["id"], "approved", 0))
        self.assertTrue(urgent["excess_stock_review"])
        self.assertEqual(urgent["first_shortage_period_start"], "2026-11-16")
        other_page = self.exceptions("exceptions-run", offset=2)
        self.assertEqual(other_page["total"], first_page["total"])
        self.assertEqual([item["classification"] for item in other_page["items"]], [
            "planned_replenishment", "excess_stock_review", "insufficient_evidence", "not_generated",
            "insufficient_evidence", "insufficient_evidence", "no_exception",
        ])
        missing_data = self.exceptions("exceptions-run", classification="insufficient_evidence")
        self.assertEqual(missing_data["total"], 3)
        self.assertIsNone(missing_data["items"][0]["suggested_quantity"])
        self.assertIsNone(missing_data["items"][0]["first_shortage_period_start"])
        pending = self.exceptions("exceptions-run", review_status="pending")
        self.assertEqual(pending["total"], 4)
        self.assertNotIn(ids["urgent"], [item["product_id"] for item in pending["items"]])
        live = self.exceptions("exceptions-run", mode="live")
        self.assertEqual(live["missing_recommendations"], 8)
        self.assertEqual(live["items"][0]["review_status"], "pending")

    def test_old_snapshots_are_derived_on_read_and_missing_inputs_are_unsupported(self):
        product_id = self.product().id
        run = add_run(self.db, "old-snapshot-run")
        add_forecast(self.db, run, product_id)
        self.db.commit()
        put_policy(self.db, product_id, POLICY)
        generated = self.generate("old-snapshot-run", product_id, "old-snapshot")
        row = self.db.get(InventoryRecommendation, generated["id"])
        path = f"/decisions/recommendations/{row.id}"
        old_snapshot = {key: value for key, value in row.snapshot.items() if key != "diagnostics"}
        row.snapshot = old_snapshot
        self.db.commit()

        self.assertEqual(self.client.get(path).json()["snapshot"]["diagnostics"]["first_shortage_quantity"], "15.89")
        self.assertEqual(self.exceptions("old-snapshot-run")["items"][0]["classification"], "shortage_within_lead_time")
        self.assertNotIn("diagnostics", row.snapshot)

        row.snapshot = {key: value for key, value in old_snapshot.items() if key != "forecast"}
        self.db.commit()
        unsupported = self.exceptions("old-snapshot-run")["items"][0]
        self.assertEqual(unsupported["classification"], "unsupported_snapshot")
        self.assertIsNone(unsupported["suggested_quantity"])
        self.assertEqual(self.client.get(path).json()["snapshot"]["diagnostics"]["status"], "unsupported_snapshot")
        self.assertEqual(self.client.patch(path, json={"action": "approved"}).status_code, 409)
        self.assertEqual(self.client.patch(path, json={"action": "rejected"}).status_code, 200)

    def test_inactive_and_stale_recommendations_and_authorization(self):
        product_id = self.product().id
        run = add_run(self.db, "review-guard-run", [product_id])
        add_forecast(self.db, run, product_id)
        self.db.commit()
        put_policy(self.db, product_id, POLICY)
        stale = self.generate("review-guard-run", product_id, "stale-test")
        path = f"/decisions/recommendations/{stale['id']}"
        invalid = self.client.patch(path, json={"action": "modified", "quantity": 13, "reason": "one pack plus one"})
        self.assertEqual(invalid.status_code, 409)
        put_policy(self.db, product_id, {**POLICY, "safety_stock": 25})
        self.assertEqual(self.client.patch(path, json={"action": "approved"}).status_code, 409)
        self.db.get(Product, product_id).is_active = False
        self.db.commit()
        self.assertFalse(self.exceptions("review-guard-run")["items"][0]["product_active"])
        self.assertEqual(self.client.patch(path, json={"action": "modified", "quantity": 168, "reason": "one extra pack"}).status_code, 409)
        self.assertEqual(self.client.patch(path, json={"action": "rejected", "reason": "Review inputs"}).status_code, 200)
        self.assertEqual(self.client.patch(path, json={"action": "rejected"}).status_code, 409)
        self.assertEqual(self.db.scalar(select(func.count(RecommendationDecision.id))), 1)

        self.assertEqual(self.client.get("/decisions/exceptions").status_code, 422)
        self.assertEqual(self.client.get("/decisions/exceptions", params={"run_id": "missing"}).status_code, 404)
        self.claims["role"] = "staff"
        self.assertEqual(self.client.get("/decisions/exceptions", params={"run_id": "review-guard-run"}).status_code, 403)
        self.claims["role"] = "admin"
        self.db.get(User, 1).is_active = False
        self.db.commit()
        self.assertEqual(self.client.get("/decisions/exceptions", params={"run_id": "review-guard-run"}).status_code, 403)
