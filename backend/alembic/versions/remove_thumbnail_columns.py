"""Remove deprecated thumbnail columns

⚠️ IMPORTANT: This migration is PENDING and should only be run after verifying:
1. All systems are using the main 'image' field instead of 'thumbnail_url'
2. Cloudinary is handling all image resizing on-demand
3. No code references thumbnail_url or thumbnail_file fields
4. Backup of production database has been taken

Revision ID: pending_remove_thumbnails
Revises: <latest_revision_id>
Create Date: 2026-01-20

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'pending_remove_thumbnails'
down_revision = 'a1b2c3d4e5f6'  # UPDATE THIS before running
branch_labels = None
depends_on = None


def upgrade():
    """
    Remove deprecated thumbnail columns from boardgames table.
    
    These columns are no longer needed because:
    - Cloudinary handles all image resizing on-demand
    - The 'image' field contains the full-size BGG image URL
    - Local thumbnail caching is no longer used
    """
    # Remove thumbnail_url column (deprecated - use 'image' field instead)
    op.drop_column('boardgames', 'thumbnail_url')
    
    # Remove thumbnail_file column (deprecated - local caching no longer used)
    op.drop_column('boardgames', 'thumbnail_file')


def downgrade():
    """
    Restore thumbnail columns if needed for rollback.
    
    Note: Data will be lost - this is for schema rollback only.
    """
    # Restore thumbnail_url column
    op.add_column('boardgames', 
                  sa.Column('thumbnail_url', sa.String(length=512), nullable=True))
    
    # Restore thumbnail_file column  
    op.add_column('boardgames',
                  sa.Column('thumbnail_file', sa.String(length=256), nullable=True))
