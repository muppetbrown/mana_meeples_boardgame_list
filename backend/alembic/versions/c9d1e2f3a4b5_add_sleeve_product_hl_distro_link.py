"""link sleeve products to the HL Timaru distro_codes catalogue

Stores the (distributor, distro_code) key only; name, cost and distributor
stock are read live from HL so a link never goes stale.

Revision ID: c9d1e2f3a4b5
Revises: a2b3c4d5e6f7
Create Date: 2026-10-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c9d1e2f3a4b5'
down_revision: Union[str, None] = 'a2b3c4d5e6f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

__all__ = ['revision', 'down_revision', 'branch_labels', 'depends_on']


def upgrade() -> None:
    op.add_column('sleeve_products', sa.Column('hl_distributor', sa.String(100), nullable=True))
    op.add_column('sleeve_products', sa.Column('hl_distro_code', sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column('sleeve_products', 'hl_distro_code')
    op.drop_column('sleeve_products', 'hl_distributor')
