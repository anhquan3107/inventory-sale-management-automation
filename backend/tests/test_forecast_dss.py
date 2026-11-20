import importlib.util
from io import StringIO
import os
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
import sys
import tempfile
import unittest

APP = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP))
os.environ.setdefault("SECRET_KEY", "test-only-key-not-for-deployment")

from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, event, func, inspect, select, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from database.base import Base
import models
from models.forecast_accuracy import ForecastAccuracy
from models.forecast_evidence import ForecastBacktestPoint, ForecastCoverage
from models.forecast_prediction import ForecastPrediction
from models.forecast_run import ForecastRun
from models.inventory import Inventory
from models.inventory_log import InventoryLog
from models.product import Product
from models.replenishment import InventoryRecommendation, RecommendationDecision, ReplenishmentPolicy
from models.sales_item import SalesItem
from models.sales_order import SalesOrder
from models.user import User
from services.forecast_data_prep import get_history
from services.forecast_engine import generate_forecast_run, list_forecast_accuracy
from services.forecast_evaluation import evaluate, metrics, predict
from services.replenishment import calculate_replenishment, generate_recommendation, put_policy, review_recommendation
from utils.scripts.seed_demo_sales import build_demo_dataset, seed_demo_sales
from utils.scripts.import_uci_online_retail import import_uci_online_retail, load_dataset


def history(values):
    return [{"period_start": date(2025, 1, 6) + timedelta(weeks=i), "quantity": float(v)}
            for i, v in enumerate(values)]


class ForecastMathTests(unittest.TestCase):
    def test_ma_recursive_and_ses(self):
        self.assertEqual(predict([20, 30, 25, 45], 2, "moving_average"), [30, 32.5])
        self.assertEqual(predict([10, 20], 3, "exponential_smoothing"), [13.5] * 3)
        self.assertEqual(predict([10, 20], 2, "naive"), [20, 20])

    def test_unknown_and_all_zero_are_not_perfect_scores(self):
        self.assertIsNone(metrics([])["mae"])
        self.assertEqual(evaluate(history([0] * 40), 8, "weekly")["status"], "no_sales_signal")
        self.assertIsNone(evaluate(history([1] * 10), 8, "weekly")["test_metrics"]["mae"])

    def test_metrics_zeros_and_bias(self):
        score = metrics([{"actual": 0, "predicted": 2}, {"actual": 10, "predicted": 8}])
        self.assertEqual(score["mae"], 2)
        self.assertEqual(score["mape"], 20)
        self.assertEqual(score["bias"], 0)
        self.assertEqual(score["wape"], 40)

    def test_final_test_does_not_select_model(self):
        values = list(range(1, 49))
        first = evaluate(history(values), 8, "weekly")
        second = evaluate(history(values[:-8] + [10000] * 8), 8, "weekly")
        self.assertEqual(first["selected_model"], second["selected_model"])
        for name in first["comparison"]:
            self.assertEqual(first["comparison"][name]["validation"], second["comparison"][name]["validation"])
        self.assertNotEqual(first["test_metrics"]["mae"], second["test_metrics"]["mae"])

    def test_multistep_does_not_read_actuals_inside_horizon(self):
        result = evaluate(history(list(range(1, 49))), 8, "weekly")
        point = next(p for p in result["points"] if p["split"] == "test"
                     and p["model_name"] == "moving_average" and p["horizon_step"] == 2)
        expected = predict(list(range(1, 41)), 8, "moving_average")[1]
        self.assertEqual(point["predicted"], expected)
        self.assertEqual(point["target_period"], point["origin"] + timedelta(weeks=1))

    def test_seed_is_deterministic_and_date_explicit(self):
        first = build_demo_dataset(days=56)
        self.assertEqual(first, build_demo_dataset(days=56))
        self.assertNotEqual(first["checksum"], build_demo_dataset(days=56, seed=123)["checksum"])


class DatabaseFixture(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        @event.listens_for(self.engine, "connect")
        def enable_fk(connection, record):
            connection.execute("PRAGMA foreign_keys=ON")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def product(self):
        product = Product(sku="TEST", name="Test", unit_price=Decimal(2), is_active=True)
        self.db.add(product)
        self.db.flush()
        return product

    def sale(self, product_id, day, quantity):
        order = SalesOrder(order_date=datetime.combine(day, datetime.min.time(), timezone.utc),
                           total_amount=quantity * 2, sales_channel="TEST")
        self.db.add(order)
        self.db.flush()
        self.db.add(SalesItem(sales_order_id=order.id, product_id=product_id, quantity=quantity,
                              unit_price=2, line_total=quantity * 2))
        self.db.flush()


class DatabaseTests(DatabaseFixture):
    def test_completed_periods_bounded_by_cutoff_and_coverage(self):
        product = self.product()
        self.db.add(ForecastCoverage(product_id=product.id, observed_from=date(2026, 1, 7),
                    observed_through=date(2026, 3, 1), source="test", dataset_version="v1", configuration={}))
        self.sale(product.id, date(2026, 1, 8), 100)  # Incomplete first week, excluded.
        self.sale(product.id, date(2026, 1, 12), 10)
        self.sale(product.id, date(2026, 1, 19), 999)  # Current week, excluded.
        self.sale(product.id, date(2026, 2, 2), 888)   # Future, excluded.
        self.db.commit()
        result = get_history(self.db, product.id, "weekly", date(2026, 1, 21))
        self.assertEqual(result["rows"], [{"period_start": date(2026, 1, 12), "quantity": 10.0}])
        monthly = get_history(self.db, product.id, "monthly", date(2026, 2, 10))
        self.assertEqual(monthly["rows"], [])  # January did not have complete coverage.

    def test_unknown_and_stale_coverage(self):
        product = self.product()
        self.assertEqual(get_history(self.db, product.id, "weekly", date(2026, 1, 19))["status"], "unknown_coverage")
        self.db.add(ForecastCoverage(product_id=product.id, observed_from=date(2025, 1, 1),
                    observed_through=date(2025, 12, 31), source="test", dataset_version="v1", configuration={}))
        self.db.flush()
        self.assertEqual(get_history(self.db, product.id, "weekly", date(2026, 1, 19))["status"],
                         "coverage_ends_before_cutoff")

    def seeded_run(self, days=364, horizon=8):
        seeded = seed_demo_sales(self.db, days=days)
        run = generate_forecast_run(self.db, 1, horizon, 3, [seeded["product_ids"][0]], date(2026, 11, 16))
        return seeded, run

    def test_seed_idempotence_inventory_reconciliation_and_no_deletion(self):
        product = self.product()
        self.db.commit()
        seeded = seed_demo_sales(self.db, days=56)
        ids = seeded["product_ids"]
        counts = self.db.scalar(select(func.count()).select_from(SalesOrder))
        self.assertFalse(seed_demo_sales(self.db, days=56)["created"])
        self.assertEqual(counts, self.db.scalar(select(func.count()).select_from(SalesOrder)))
        self.assertIsNotNone(self.db.get(Product, product.id))
        for pid in ids:
            stock = self.db.scalar(select(Inventory).where(Inventory.product_id == pid))
            logs = list(self.db.scalars(select(InventoryLog).where(InventoryLog.product_id == pid).order_by(InventoryLog.id)))
            balance = 0
            for log in logs:
                self.assertEqual(log.quantity_before, balance)
                balance += log.change_quantity
                self.assertEqual(log.quantity_after, balance)
            self.assertEqual(balance, stock.quantity_on_hand)
        second = seed_demo_sales(self.db, days=56, seed=99)
        self.assertTrue(set(ids).isdisjoint(second["product_ids"]))

    def test_forecast_evidence_persisted_and_repeatable(self):
        seeded, run = self.seeded_run()
        again = generate_forecast_run(self.db, 1, 8, 3, [seeded["product_ids"][0]], date(2026, 11, 16))
        first = list_forecast_accuracy(self.db, "weekly", run["run_id"])["items"][0]
        second = list_forecast_accuracy(self.db, "weekly", again["run_id"])["items"][0]
        self.assertEqual(first, second)
        self.assertEqual(first["training_points"], 52)
        self.assertEqual(first["details"]["status"], "evaluated")
        record = self.db.scalar(select(ForecastRun).where(ForecastRun.run_id == run["run_id"]))
        forecasts = list(self.db.scalars(select(ForecastPrediction).where(ForecastPrediction.run_ref_id == record.id,
                         ForecastPrediction.granularity == "weekly").order_by(ForecastPrediction.horizon_step)))
        self.assertEqual(forecasts[0].period_start, date(2026, 11, 16))
        self.assertTrue(all(f.confidence_upper is None for f in forecasts))
        points = list(self.db.scalars(select(ForecastBacktestPoint).where(ForecastBacktestPoint.run_ref_id == record.id)))
        self.assertEqual({p.model_name for p in points}, {"naive", "moving_average", "exponential_smoothing"})
        self.assertEqual({p.split for p in points}, {"validation", "test"})

    def test_default_three_year_seed_supports_weekly_and_monthly_evaluation(self):
        seeded = seed_demo_sales(self.db)
        run = generate_forecast_run(self.db, 1, 8, 6, seeded["product_ids"], date(2026, 11, 16))
        self.assertEqual(run["forecasts_created"], 12 * 14)
        for granularity in ("weekly", "monthly"):
            rows = list_forecast_accuracy(self.db, granularity, run["run_id"])["items"]
            self.assertEqual(len(rows), 12)
            self.assertTrue(all(r["details"]["status"] == "evaluated" for r in rows))

    def test_partial_week_and_unvalidated_forecasts_cannot_drive_decisions(self):
        seeded, run = self.seeded_run(days=56)
        payload = {"request_key": "unevaluated", "run_id": run["run_id"],
                   "product_id": seeded["product_ids"][0], "mode": "simulation",
                   "simulated_on_hand": 10, "simulated_receipts": []}
        with self.assertRaisesRegex(ValueError, "evaluated weekly forecast"):
            generate_recommendation(self.db, payload, 1)
        self.db.rollback()
        midweek = generate_forecast_run(self.db, 1, 1, 1, [payload["product_id"]], date(2026, 11, 18))
        payload.update(run_id=midweek["run_id"], request_key="midweek")
        with self.assertRaisesRegex(ValueError, "Monday"):
            generate_recommendation(self.db, payload, 1)

    def test_monthly_current_period_is_not_a_training_label(self):
        product = self.product()
        self.db.add(ForecastCoverage(product_id=product.id, observed_from=date(2025, 1, 1),
                    observed_through=date(2026, 10, 31), source="test", dataset_version="v1", configuration={}))
        self.sale(product.id, date(2026, 9, 30), 10)
        self.sale(product.id, date(2026, 10, 1), 999)
        self.db.commit()
        result = get_history(self.db, product.id, "monthly", date(2026, 10, 20))
        self.assertEqual(result["rows"][-1], {"period_start": date(2026, 9, 1), "quantity": 10.0})

    def test_live_historical_forecast_is_rejected(self):
        seeded, run = self.seeded_run()
        payload = {"request_key": "live", "run_id": run["run_id"], "product_id": seeded["product_ids"][0],
                   "mode": "live", "simulated_on_hand": None, "simulated_receipts": []}
        from unittest.mock import patch
        class LaterDate(date):
            @classmethod
            def today(cls):
                return cls(2026, 11, 23)
        with patch("services.replenishment.date", LaterDate):
            with self.assertRaisesRegex(ValueError, "today's Monday"):
                generate_recommendation(self.db, payload, 1)

    def test_unknown_product_has_null_accuracy_no_predictions(self):
        product = self.product()
        self.db.commit()
        run = generate_forecast_run(self.db, 1, 8, 6, [product.id], date(2026, 11, 16))
        self.assertEqual(run["forecasts_created"], 0)
        self.assertEqual(run["unavailable_series"], 2)
        accuracy = list_forecast_accuracy(self.db, "weekly", run["run_id"])["items"][0]
        self.assertIsNone(accuracy["mae"])
        self.assertEqual(accuracy["details"]["status"], "unknown_coverage")

    def test_recommendation_is_advisory_idempotent_and_reviewed_once(self):
        seeded, run = self.seeded_run()
        pid = seeded["product_ids"][0]
        stock = self.db.scalar(select(Inventory).where(Inventory.product_id == pid))
        before = stock.quantity_on_hand
        payload = {"request_key": "demo-request", "run_id": run["run_id"], "product_id": pid,
                   "mode": "simulation", "simulated_on_hand": 5, "simulated_receipts": []}
        recommendation = generate_recommendation(self.db, payload, 1)
        self.assertEqual(generate_recommendation(self.db, payload, 1)["id"], recommendation["id"])
        reviewed = review_recommendation(self.db, recommendation["id"],
                                         {"action": "approved", "quantity": None, "reason": None}, 1)
        self.assertEqual(reviewed["status"], "approved")
        self.db.refresh(stock)
        self.assertEqual(stock.quantity_on_hand, before)
        with self.assertRaisesRegex(ValueError, "already been reviewed"):
            review_recommendation(self.db, recommendation["id"], {"action": "rejected"}, 1)

    def test_policy_changes_block_approval_and_short_horizon_blocks_generation(self):
        seeded, run = self.seeded_run(horizon=2)
        pid = seeded["product_ids"][0]
        payload = {"request_key": "short", "run_id": run["run_id"], "product_id": pid,
                   "mode": "simulation", "simulated_on_hand": 0, "simulated_receipts": []}
        with self.assertRaisesRegex(ValueError, "does not cover"):
            generate_recommendation(self.db, payload, 1)
        self.db.rollback()
        policy = self.db.get(ReplenishmentPolicy, pid)
        put_policy(self.db, pid, {"lead_time_weeks": 1, "review_interval_weeks": 1,
                                 "safety_stock": 0, "minimum_order_quantity": 0, "pack_size": 1})
        row = generate_recommendation(self.db, payload, 1)
        put_policy(self.db, pid, {"lead_time_weeks": 1, "review_interval_weeks": 1,
                                 "safety_stock": 10, "minimum_order_quantity": 0, "pack_size": 1})
        with self.assertRaisesRegex(ValueError, "Policy changed"):
            review_recommendation(self.db, row["id"], {"action": "approved"}, 1)

    def test_public_import_has_no_fake_inventory_and_uses_external_reference(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "retail.csv"
            path.write_text("InvoiceNo,StockCode,Description,Quantity,InvoiceDate,UnitPrice\n"
                            "1,A,Item,3,01/01/2011 10:00,2.00\n"
                            "2,A,Item,4,01/02/2011 10:00,2.00\n"
                            "3,A,Item,5,01/03/2011 10:00,2.00\n"
                            "4,A,Item,6,01/04/2011 10:00,2.00\n"
                            "C5,A,Item,6,01/03/2011 10:00,2.00\n", encoding="utf-8")
            result = import_uci_online_retail(self.db, path)
            self.assertEqual(result["rows_imported"], 2)
            self.assertFalse(import_uci_online_retail(self.db, path)["created"])
            self.assertEqual(self.db.scalar(select(func.count()).select_from(Inventory)), 0)
            order = self.db.scalar(select(SalesOrder).limit(1))
            self.assertEqual(order.sales_channel, "PUBLIC")
            self.assertTrue(order.external_reference.startswith("uci-v2-"))

    def test_public_import_fails_on_unknown_data_gaps(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.csv"
            path.write_text("InvoiceNo,StockCode,Description,Quantity,InvoiceDate,UnitPrice\n"
                            "1,A,Item,3,not-a-date,2.00\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Malformed CSV row"):
                import_uci_online_retail(self.db, path)
            self.assertEqual(self.db.scalar(select(func.count()).select_from(Product)), 0)


class DecisionMathTests(unittest.TestCase):
    def test_rounding_and_late_receipts(self):
        policy = dict(lead_time_weeks=2, review_interval_weeks=1, safety_stock=15,
                      minimum_order_quantity=0, pack_size=12)
        result = calculate_replenishment([Decimal(30)] * 3, 50, [{"arrival_week": 2, "quantity": 20}], policy)
        self.assertEqual(result["inventory_position"], 70)
        self.assertEqual(result["suggested_quantity"], 36)
        late = calculate_replenishment([Decimal(30)] * 3, 10, [{"arrival_week": 4, "quantity": 100}], policy)
        self.assertEqual(late["suggested_quantity"], 0)
        self.assertTrue(late["stockout_risk"])

    def test_moq_and_no_negative_order(self):
        policy = dict(lead_time_weeks=1, review_interval_weeks=1, safety_stock=0,
                      minimum_order_quantity=20, pack_size=12)
        result = calculate_replenishment([Decimal(10)] * 2, 19, [], policy)
        self.assertEqual(result["suggested_quantity"], 24)
        self.assertEqual(calculate_replenishment([Decimal(10)] * 2, 100, [], policy)["suggested_quantity"], 0)


class MigrationTests(unittest.TestCase):
    def migrations(self):
        modules = []
        for filename in ("77d12eabc901_forecast_evidence.py", "88d12eabc902_replenishment.py"):
            spec = importlib.util.spec_from_file_location(filename[:-3], APP / "migrations" / "versions" / filename)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            modules.append(module)
        return modules

    def test_additive_migrations_preserve_legacy_rows_and_downgrade(self):
        from alembic.migration import MigrationContext
        from alembic.operations import Operations
        engine = create_engine("sqlite://")
        metadata = MetaData()
        Table("products", metadata, Column("id", Integer, primary_key=True))
        Table("sales_orders", metadata, Column("id", Integer, primary_key=True))
        Table("forecast_runs", metadata, Column("id", Integer, primary_key=True), Column("run_id", String))
        Table("forecast_accuracy", metadata, Column("id", Integer, primary_key=True))
        metadata.create_all(engine)
        modules = self.migrations()
        with engine.begin() as connection:
            connection.execute(text("INSERT INTO forecast_runs (id, run_id) VALUES (1, 'legacy')"))
            with Operations.context(MigrationContext.configure(connection)):
                for module in modules:
                    module.upgrade()
                self.assertEqual(connection.execute(text("SELECT run_id, as_of_date, settings FROM forecast_runs")).one(),
                                 ("legacy", None, None))
                expected = {"forecast_coverage", "forecast_backtest_points", "replenishment_policies",
                            "inventory_recommendations", "recommendation_decisions"}
                self.assertTrue(expected.issubset(set(inspect(connection).get_table_names())))
                for name in expected:
                    actual = {c["name"] for c in inspect(connection).get_columns(name)}
                    self.assertEqual(actual, set(Base.metadata.tables[name].columns.keys()))
                for module in reversed(modules):
                    module.downgrade()
                self.assertEqual(connection.execute(text("SELECT run_id FROM forecast_runs")).scalar(), "legacy")
        engine.dispose()

    def test_postgres_migration_sql_compiles(self):
        from alembic.migration import MigrationContext
        from alembic.operations import Operations
        output = StringIO()
        context = MigrationContext.configure(dialect_name="postgresql", opts={"as_sql": True, "output_buffer": output})
        with Operations.context(context):
            for module in self.migrations():
                module.upgrade()
        sql = output.getvalue()
        self.assertIn("ALTER TABLE forecast_runs ADD COLUMN as_of_date DATE", sql)
        self.assertIn("CREATE TABLE inventory_recommendations", sql)
        self.assertNotIn("DELETE FROM", sql)


class ApiTests(DatabaseFixture):
    def setUp(self):
        super().setUp()
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from database.dependencies import get_db
        from routers.forecast import router as forecast_router
        from routers.decisions import router as decision_router
        from utils.security.bearer import require_auth
        app = FastAPI()
        app.include_router(forecast_router)
        app.include_router(decision_router)
        self.claims = {"sub": "1", "role": "admin"}
        app.dependency_overrides[require_auth] = lambda: self.claims
        def session():
            try:
                yield self.db
            finally:
                self.db.rollback()
        app.dependency_overrides[get_db] = session
        self.client = TestClient(app)
        self.db.add(User(id=1, username="test", email="test@example.com", password_hash="unused",
                         role="admin", is_active=True))
        self.db.commit()

    def tearDown(self):
        self.client.close()
        super().tearDown()

    def test_validation_and_authorization(self):
        self.assertEqual(self.client.post("/forecast/generate", json={"product_ids": [0]}).status_code, 422)
        self.assertEqual(self.client.post("/forecast/generate", json={"product_ids": []}).status_code, 422)
        self.claims = {"sub": "1", "role": "staff"}
        self.assertEqual(self.client.post("/forecast/generate", json={}).status_code, 403)
        user = self.db.get(User, 1)
        user.role = "staff"
        self.db.commit()
        self.assertEqual(self.client.get("/decisions/policies").status_code, 403)

    def test_live_requires_explicit_zero_incoming_confirmation(self):
        response = self.client.post("/decisions/generate", json={
            "request_key": "live", "run_id": "not-yet-needed", "product_id": 1, "mode": "live"})
        self.assertEqual(response.status_code, 422)

    def test_coverage_declaration_is_explicit_and_versioned(self):
        product = self.product()
        self.db.commit()
        payload = {"observed_from": "2025-01-01", "observed_through": "2026-11-15", "source": "manual",
                   "dataset_version": "v1", "confirms_complete_sales": True}
        self.assertEqual(self.client.put(f"/forecast/coverage/{product.id}", json=payload).status_code, 200)
        self.assertEqual(self.client.put(f"/forecast/coverage/{product.id}", json=payload).status_code, 200)
        payload["observed_from"] = "2025-02-01"
        self.assertEqual(self.client.put(f"/forecast/coverage/{product.id}", json=payload).status_code, 409)
        payload["dataset_version"] = "v2"
        self.assertEqual(self.client.put(f"/forecast/coverage/{product.id}", json=payload).status_code, 200)

    def test_forecast_and_decision_api(self):
        seeded = seed_demo_sales(self.db, days=364)
        pid = seeded["product_ids"][0]
        response = self.client.post("/forecast/generate", json={"product_ids": [pid],
                                    "as_of_date": "2026-11-16", "weekly_horizon": 8, "monthly_horizon": 3})
        self.assertEqual(response.status_code, 200, response.text)
        run_id = response.json()["run_id"]
        accuracy = self.client.get("/forecast/accuracy", params={"run_id": run_id}).json()
        self.assertEqual(accuracy["items"][0]["details"]["status"], "evaluated")
        points = self.client.get("/forecast/backtest-points", params={"run_id": run_id, "product_id": pid})
        self.assertEqual(points.status_code, 200)
        self.assertTrue(points.json())
        rec = self.client.post("/decisions/generate", json={"request_key": "api", "run_id": run_id,
                               "product_id": pid, "mode": "simulation", "simulated_on_hand": 5})
        self.assertEqual(rec.status_code, 200, rec.text)
        reviewed = self.client.patch(f"/decisions/recommendations/{rec.json()['id']}", json={"action": "approved"})
        self.assertEqual(reviewed.status_code, 200, reviewed.text)
        duplicate = self.client.patch(f"/decisions/recommendations/{rec.json()['id']}", json={"action": "approved"})
        self.assertEqual(duplicate.status_code, 409)


if __name__ == "__main__":
    unittest.main()
