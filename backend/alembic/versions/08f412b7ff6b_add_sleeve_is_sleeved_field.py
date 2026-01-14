"""add_sleeve_is_sleeved_field

Revision ID: 08f412b7ff6b
Revises: 69e5f1b3d4e5
Create Date: 2026-01-14 12:31:51.164422

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '08f412b7ff6b'
down_revision: Union[str, None] = '69e5f1b3d4e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add is_sleeved column to sleeves table and remove from boardgames table"""
    # Add is_sleeved to sleeves table (SQLite compatible - leave nullable)
    op.add_column('sleeves', sa.Column('is_sleeved', sa.Boolean(), nullable=True, server_default=sa.text('false')))

    # Set default value for existing rows
    op.execute("UPDATE sleeves SET is_sleeved = false WHERE is_sleeved IS NULL")

    # Remove is_sleeved from boardgames table
    op.drop_column('boardgames', 'is_sleeved')


def downgrade() -> None:
    """Remove is_sleeved from sleeves table and add back to boardgames table"""
    # Add back is_sleeved to boardgames
    op.add_column('boardgames', sa.Column('is_sleeved', sa.Boolean(), nullable=True))

    # Remove from sleeves
    op.drop_column('sleeves', 'is_sleeved')
