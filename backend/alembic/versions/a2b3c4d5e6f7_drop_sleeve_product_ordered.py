"""drop ordered column from sleeve products

Revision ID: a2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-10-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a2b3c4d5e6f7'
down_revision: Union[str, None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

__all__ = ['revision', 'down_revision', 'branch_labels', 'depends_on']


def upgrade() -> None:
    """Sleeve inventory is tracked by in_stock only; packs-on-order is no longer used"""
    with op.batch_alter_table('sleeve_products') as batch_op:
        batch_op.drop_constraint('valid_product_ordered', type_='check')
        batch_op.drop_column('ordered')


def downgrade() -> None:
    with op.batch_alter_table('sleeve_products') as batch_op:
        batch_op.add_column(sa.Column('ordered', sa.Integer(), nullable=False, server_default='0'))
        batch_op.create_check_constraint('valid_product_ordered', 'ordered >= 0')
