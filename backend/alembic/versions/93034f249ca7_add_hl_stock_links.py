"""add hl_stock_links table

Persists the link between an HL Timaru retail product (by internal_id, read
directly from the HL Timaru Postgres database) and a game in this library,
once a staff member confirms a fuzzy-matched suggestion - so the match never
needs re-resolving on a later sync. Also caches the last-synced HL stock/sales
snapshot for display, and a dismissed flag for products that aren't real
board-game candidates (e.g. a miscategorized item).

Revision ID: 93034f249ca7
Revises: e5f6a7b8c9d0
Create Date: 2026-10-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '93034f249ca7'
down_revision: Union[str, None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

__all__ = ['revision', 'down_revision', 'branch_labels', 'depends_on']


def upgrade() -> None:
    op.create_table(
        'hl_stock_links',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('hl_internal_id', sa.Integer(), nullable=False),
        sa.Column('game_id', sa.Integer(), sa.ForeignKey('boardgames.id', ondelete='SET NULL'), nullable=True),
        sa.Column('dismissed', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('hl_product_name', sa.Text(), nullable=False),
        sa.Column('hl_current_stock', sa.Integer(), nullable=True),
        sa.Column('hl_units_sold', sa.Integer(), nullable=True),
        sa.Column('hl_last_sale_date', sa.Date(), nullable=True),
        sa.Column('hl_approx_revenue', sa.Numeric(10, 2), nullable=True),
        sa.Column('match_confidence', sa.Float(), nullable=True),
        sa.Column('last_synced_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_unique_constraint('uq_hl_stock_links_internal_id', 'hl_stock_links', ['hl_internal_id'])
    op.create_index('ix_hl_stock_links_hl_internal_id', 'hl_stock_links', ['hl_internal_id'])
    op.create_index('ix_hl_stock_links_game_id', 'hl_stock_links', ['game_id'])
    op.create_index('idx_hl_stock_links_status', 'hl_stock_links', ['dismissed', 'game_id'])


def downgrade() -> None:
    op.drop_index('idx_hl_stock_links_status', table_name='hl_stock_links')
    op.drop_index('ix_hl_stock_links_game_id', table_name='hl_stock_links')
    op.drop_index('ix_hl_stock_links_hl_internal_id', table_name='hl_stock_links')
    op.drop_table('hl_stock_links')
