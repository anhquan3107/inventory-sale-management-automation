"""Add reproducible forecast metadata and backtest evidence; preserve legacy runs."""
from alembic import op
import sqlalchemy as sa

revision = "77d12eabc901"
down_revision = "0b743d43e0b6"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("sales_orders", sa.Column("external_reference", sa.String(160), nullable=True))
    op.create_index("uq_sales_orders_external_reference", "sales_orders", ["external_reference"], unique=True)
    op.add_column("forecast_runs", sa.Column("as_of_date", sa.Date(), nullable=True))
    op.add_column("forecast_runs", sa.Column("settings", sa.JSON(), nullable=True))
    op.add_column("forecast_accuracy", sa.Column("details", sa.JSON(), nullable=True))
    op.create_table(
        "forecast_coverage",
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), primary_key=True),
        sa.Column("observed_from", sa.Date(), nullable=False),
        sa.Column("observed_through", sa.Date(), nullable=False),
        sa.Column("source", sa.String(80), nullable=False),
        sa.Column("dataset_version", sa.String(100), nullable=False),
        sa.Column("configuration", sa.JSON(), nullable=False),
        sa.CheckConstraint("observed_through >= observed_from", name="ck_forecast_coverage_dates"),
    )
    op.create_table(
        "forecast_backtest_points",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_ref_id", sa.Integer(), sa.ForeignKey("forecast_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("granularity", sa.String(10), nullable=False),
        sa.Column("model_name", sa.String(40), nullable=False),
        sa.Column("split", sa.String(12), nullable=False),
        sa.Column("origin", sa.Date(), nullable=False),
        sa.Column("target_period", sa.Date(), nullable=False),
        sa.Column("horizon_step", sa.Integer(), nullable=False),
        sa.Column("actual", sa.Numeric(14, 4), nullable=False),
        sa.Column("predicted", sa.Numeric(14, 4), nullable=False),
        sa.UniqueConstraint("run_ref_id", "product_id", "granularity", "model_name", "split",
                            "origin", "horizon_step", name="uq_backtest_point"),
    )
    op.create_index("idx_backtest_run_product", "forecast_backtest_points", ["run_ref_id", "product_id"])


def downgrade():
    op.drop_index("idx_backtest_run_product", table_name="forecast_backtest_points")
    op.drop_table("forecast_backtest_points")
    op.drop_table("forecast_coverage")
    op.drop_column("forecast_accuracy", "details")
    op.drop_column("forecast_runs", "settings")
    op.drop_column("forecast_runs", "as_of_date")
    op.drop_index("uq_sales_orders_external_reference", table_name="sales_orders")
    op.drop_column("sales_orders", "external_reference")
