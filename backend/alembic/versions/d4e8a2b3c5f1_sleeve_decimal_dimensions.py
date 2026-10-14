"""allow decimal sleeve dimensions

Revision ID: d4e8a2b3c5f1
Revises: c3d9f0a1b2e7
Create Date: 2026-10-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e8a2b3c5f1'
down_revision: Union[str, None] = 'c3d9f0a1b2e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

__all__ = ['revision', 'down_revision', 'branch_labels', 'depends_on']


def upgrade() -> None:
    """Convert sleeve and sleeve_products width/height from INTEGER to NUMERIC(6, 2)"""
    for table in ('sleeves', 'sleeve_products'):
        with op.batch_alter_table(table) as batch_op:
            batch_op.alter_column('width_mm', existing_type=sa.Integer(), type_=sa.Numeric(6, 2), existing_nullable=False)
            batch_op.alter_column('height_mm', existing_type=sa.Integer(), type_=sa.Numeric(6, 2), existing_nullable=False)


def downgrade() -> None:
    """Revert to INTEGER (decimal values are rounded)"""
    for table in ('sleeves', 'sleeve_products'):
        with op.batch_alter_table(table) as batch_op:
            batch_op.alter_column('width_mm', existing_type=sa.Numeric(6, 2), type_=sa.Integer(), existing_nullable=False,
                                  postgresql_using='ROUND(width_mm)::integer')
            batch_op.alter_column('height_mm', existing_type=sa.Numeric(6, 2), type_=sa.Integer(), existing_nullable=False,
                                  postgresql_using='ROUND(height_mm)::integer')
