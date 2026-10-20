"""add fits-card-size dimensions to sleeve products

Revision ID: f1a2b3c4d5e6
Revises: b7e2f9a31c44
Create Date: 2026-10-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, None] = 'b7e2f9a31c44'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

__all__ = ['revision', 'down_revision', 'branch_labels', 'depends_on']


def upgrade() -> None:
    """Optional card size a sleeve is rated to fit (width_mm/height_mm stay the sleeve's own size)"""
    op.add_column('sleeve_products', sa.Column('card_width_mm', sa.Numeric(6, 2), nullable=True))
    op.add_column('sleeve_products', sa.Column('card_height_mm', sa.Numeric(6, 2), nullable=True))


def downgrade() -> None:
    op.drop_column('sleeve_products', 'card_height_mm')
    op.drop_column('sleeve_products', 'card_width_mm')
