"""Add periodic-review policies and auditable advisory decisions."""
from alembic import op
import sqlalchemy as sa

revision = "88d12eabc902"
down_revision = "77d12eabc901"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "replenishment_policies",
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), primary_key=True),
        sa.Column("lead_time_weeks", sa.Integer(), nullable=False),
        sa.Column("review_interval_weeks", sa.Integer(), nullable=False),
        sa.Column("safety_stock", sa.Integer(), nullable=False),
        sa.Column("minimum_order_quantity", sa.Integer(), nullable=False),
        sa.Column("pack_size", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.CheckConstraint("lead_time_weeks >= 1 AND review_interval_weeks >= 1", name="ck_policy_weeks"),
        sa.CheckConstraint("safety_stock >= 0 AND minimum_order_quantity >= 0 AND pack_size >= 1",
                           name="ck_policy_quantities"),
    )
    op.create_table(
        "inventory_recommendations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("request_key", sa.String(100), nullable=False, unique=True),
        sa.Column("run_ref_id", sa.Integer(), sa.ForeignKey("forecast_runs.id"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("suggested_quantity", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "recommendation_decisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("recommendation_id", sa.Integer(), sa.ForeignKey("inventory_recommendations.id"), nullable=False),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("recommendation_id", name="uq_recommendation_decision"),
    )


def downgrade():
    op.drop_table("recommendation_decisions")
    op.drop_table("inventory_recommendations")
    op.drop_table("replenishment_policies")
