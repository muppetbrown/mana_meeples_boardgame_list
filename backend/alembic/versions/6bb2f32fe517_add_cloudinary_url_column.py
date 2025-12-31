"""add cloudinary_url column

Revision ID: 6bb2f32fe517
Revises: a879cc066239
Create Date: 2025-12-31 05:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6bb2f32fe517'
down_revision: Union[str, None] = 'a879cc066239'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add cloudinary_url column to boardgames table"""
    op.add_column('boardgames', sa.Column('cloudinary_url', sa.String(length=512), nullable=True))


def downgrade() -> None:
    """Remove cloudinary_url column from boardgames table"""
    op.drop_column('boardgames', 'cloudinary_url')
