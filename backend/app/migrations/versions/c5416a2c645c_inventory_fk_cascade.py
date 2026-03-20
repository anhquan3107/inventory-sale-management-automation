"""inventory fk cascade

Revision ID: c5416a2c645c
Revises: 45a8c9163676
Create Date: 2026-03-20 05:41:25.760936

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'c5416a2c645c'
down_revision: Union[str, Sequence[str], None] = '45a8c9163676'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint('inventory_product_id_fkey', 'inventory', type_='foreignkey')
    op.create_foreign_key(
        'inventory_product_id_fkey',
        'inventory',
        'products',
        ['product_id'],
        ['id'],
        ondelete='CASCADE',
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('inventory_product_id_fkey', 'inventory', type_='foreignkey')
    op.create_foreign_key(
        'inventory_product_id_fkey',
        'inventory',
        'products',
        ['product_id'],
        ['id'],
    )
