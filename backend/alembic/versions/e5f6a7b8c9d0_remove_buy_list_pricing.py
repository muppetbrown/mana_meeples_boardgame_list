"""remove buy-list price tracking, add notes to buy_list_games

Price fetching (BoardGameOracle scraping, LPG RRP/status) is no longer
needed now that games are bought through direct distributor accounts.
The buy list is repurposed into a gap-driven "games to add" list, which
only needs a priority rank and freeform curation notes.

Revision ID: e5f6a7b8c9d0
Revises: d4e8a2b3c5f1
Create Date: 2026-10-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, None] = 'd4e8a2b3c5f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

__all__ = ['revision', 'down_revision', 'branch_labels', 'depends_on']


def upgrade() -> None:
    """Drop price-tracking tables/columns, add buy_list_games.notes"""
    op.drop_table('price_offers')
    op.drop_table('price_snapshots')

    with op.batch_alter_table('buy_list_games') as batch_op:
        batch_op.drop_index('idx_buy_list_status')
        batch_op.drop_column('bgo_link')
        batch_op.drop_column('lpg_rrp')
        batch_op.drop_column('lpg_status')
        batch_op.add_column(sa.Column('notes', sa.Text(), nullable=True))


def downgrade() -> None:
    """Recreate price-tracking tables/columns, drop notes"""
    with op.batch_alter_table('buy_list_games') as batch_op:
        batch_op.drop_column('notes')
        batch_op.add_column(sa.Column('lpg_status', sa.String(50), nullable=True))
        batch_op.add_column(sa.Column('lpg_rrp', sa.Numeric(10, 2), nullable=True))
        batch_op.add_column(sa.Column('bgo_link', sa.Text(), nullable=True))
        batch_op.create_index('idx_buy_list_status', ['lpg_status', 'on_buy_list'])

    op.create_table(
        'price_snapshots',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('game_id', sa.Integer(), sa.ForeignKey('boardgames.id', ondelete='CASCADE'), nullable=False),
        sa.Column('checked_at', sa.DateTime(), nullable=False),
        sa.Column('low_price', sa.Numeric(10, 2), nullable=True),
        sa.Column('mean_price', sa.Numeric(10, 2), nullable=True),
        sa.Column('best_price', sa.Numeric(10, 2), nullable=True),
        sa.Column('best_store', sa.Text(), nullable=True),
        sa.Column('discount_pct', sa.Numeric(5, 2), nullable=True),
        sa.Column('disc_mean_pct', sa.Numeric(5, 2), nullable=True),
        sa.Column('delta', sa.Numeric(5, 2), nullable=True),
        sa.Column('source_file', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('idx_price_snapshot_game_date', 'price_snapshots', ['game_id', 'checked_at'])
    op.create_index('idx_price_snapshot_best', 'price_snapshots', ['best_price', 'discount_pct'])

    op.create_table(
        'price_offers',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('game_id', sa.Integer(), sa.ForeignKey('boardgames.id', ondelete='CASCADE'), nullable=False),
        sa.Column('checked_at', sa.DateTime(), nullable=False),
        sa.Column('store', sa.Text(), nullable=True),
        sa.Column('price_nzd', sa.Numeric(10, 2), nullable=True),
        sa.Column('availability', sa.Text(), nullable=True),
        sa.Column('store_link', sa.Text(), nullable=True),
        sa.Column('in_stock', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('idx_price_offer_game_date', 'price_offers', ['game_id', 'checked_at'])
    op.create_index('idx_price_offer_store', 'price_offers', ['store', 'in_stock'])
