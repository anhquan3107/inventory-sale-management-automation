"""baseline

Revision ID: 45a8c9163676
Revises: 
Create Date: 2026-02-18 15:35:24.513004

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '45a8c9163676'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'products',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('sku', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('unit_price', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('sku'),
    )
    op.create_index('idx_products_sku', 'products', ['sku'], unique=False)

    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('must_change_password', sa.Boolean(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username'),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    op.create_table(
        'sales_orders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('order_date', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('total_amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('sales_channel', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_sales_orders_order_date', 'sales_orders', ['order_date'], unique=False)
    op.create_index('idx_sales_orders_sales_channel', 'sales_orders', ['sales_channel'], unique=False)

    op.create_table(
        'inventory',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('quantity_on_hand', sa.Integer(), nullable=False),
        sa.Column('last_updated', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('product_id'),
    )
    op.create_index('idx_inventory_product_id', 'inventory', ['product_id'], unique=False)

    op.create_table(
        'inventory_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('change_quantity', sa.Integer(), nullable=False),
        sa.Column('quantity_before', sa.Integer(), nullable=False),
        sa.Column('quantity_after', sa.Integer(), nullable=False),
        sa.Column('log_type', sa.String(), nullable=False),
        sa.Column('reference_id', sa.Integer(), nullable=True),
        sa.Column('log_date', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_inventory_log_log_date', 'inventory_log', ['log_date'], unique=False)
    op.create_index('idx_inventory_log_product_id', 'inventory_log', ['product_id'], unique=False)

    op.create_table(
        'sales_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('sales_order_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('unit_price', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('line_total', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_sales_items_order_id', 'sales_items', ['sales_order_id'], unique=False)
    op.create_index('idx_sales_items_product_id', 'sales_items', ['product_id'], unique=False)

    op.create_foreign_key(
        'inventory_product_id_fkey',
        'inventory',
        'products',
        ['product_id'],
        ['id'],
    )
    op.create_foreign_key(
        'inventory_log_product_id_fkey',
        'inventory_log',
        'products',
        ['product_id'],
        ['id'],
    )
    op.create_foreign_key(
        'sales_items_product_id_fkey',
        'sales_items',
        'products',
        ['product_id'],
        ['id'],
    )
    op.create_foreign_key(
        'sales_items_sales_order_id_fkey',
        'sales_items',
        'sales_orders',
        ['sales_order_id'],
        ['id'],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('sales_items_sales_order_id_fkey', 'sales_items', type_='foreignkey')
    op.drop_constraint('sales_items_product_id_fkey', 'sales_items', type_='foreignkey')
    op.drop_constraint('inventory_log_product_id_fkey', 'inventory_log', type_='foreignkey')
    op.drop_constraint('inventory_product_id_fkey', 'inventory', type_='foreignkey')

    op.drop_index('idx_sales_items_product_id', table_name='sales_items')
    op.drop_index('idx_sales_items_order_id', table_name='sales_items')
    op.drop_table('sales_items')

    op.drop_index('idx_inventory_log_product_id', table_name='inventory_log')
    op.drop_index('idx_inventory_log_log_date', table_name='inventory_log')
    op.drop_table('inventory_log')

    op.drop_index('idx_inventory_product_id', table_name='inventory')
    op.drop_table('inventory')

    op.drop_index('idx_sales_orders_sales_channel', table_name='sales_orders')
    op.drop_index('idx_sales_orders_order_date', table_name='sales_orders')
    op.drop_table('sales_orders')

    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')

    op.drop_index('idx_products_sku', table_name='products')
    op.drop_table('products')
