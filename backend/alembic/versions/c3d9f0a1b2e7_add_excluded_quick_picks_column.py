"""add excluded_quick_picks column

Revision ID: c3d9f0a1b2e7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-08 12:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c3d9f0a1b2e7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

__all__ = ['revision', 'down_revision', 'branch_labels', 'depends_on']


def upgrade() -> None:
    """Add excluded_quick_picks column to boardgames table"""
    bind = op.get_bind()
    json_type = postgresql.JSONB() if bind.dialect.name == 'postgresql' else sa.JSON()
    op.add_column('boardgames', sa.Column('excluded_quick_picks', json_type, nullable=True))


def downgrade() -> None:
    """Remove excluded_quick_picks column from boardgames table"""
    op.drop_column('boardgames', 'excluded_quick_picks')
