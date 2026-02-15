"""Remove deprecated thumbnail columns

Revision ID: pending_remove_thumbnails
Revises: f37582e531b4
Create Date: 2026-01-20

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'pending_remove_thumbnails'
down_revision = 'f37582e531b4'
branch_labels = None
depends_on = None


def upgrade():
    """
    Remove deprecated thumbnail columns from boardgames table.
    """
    op.drop_column('boardgames', 'thumbnail_url')
    op.drop_column('boardgames', 'thumbnail_file')


def downgrade():
    """
    Restore thumbnail columns if needed for rollback.
    """
    op.add_column('boardgames',
                  sa.Column('thumbnail_url', sa.String(length=512), nullable=True))
    op.add_column('boardgames',
                  sa.Column('thumbnail_file', sa.String(length=256), nullable=True))
