"""Add is_sleeved column to boardgames table

Revision ID: f37582e531b4
Revises: 08f412b7ff6b
Create Date: 2026-01-14 14:38:45.607883

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f37582e531b4'
down_revision: Union[str, None] = '08f412b7ff6b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add is_sleeved column to boardgames table
    op.add_column('boardgames', sa.Column('is_sleeved', sa.Boolean(), nullable=True, server_default=sa.false()))

    # Create index for is_sleeved column
    op.create_index(op.f('ix_boardgames_is_sleeved'), 'boardgames', ['is_sleeved'], unique=False)


def downgrade() -> None:
    # Drop index
    op.drop_index(op.f('ix_boardgames_is_sleeved'), table_name='boardgames')

    # Drop is_sleeved column
    op.drop_column('boardgames', 'is_sleeved')
