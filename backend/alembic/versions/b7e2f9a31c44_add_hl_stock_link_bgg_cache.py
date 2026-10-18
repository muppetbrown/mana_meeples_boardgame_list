"""cache BGG details on hl_stock_links

HL Timaru products with no matching library game have no player count,
complexity, playtime or category, so they can't be scored against the
library's gaps. Cache a BGG lookup per link so they can be.

Revision ID: b7e2f9a31c44
Revises: a1c4d7e92b10
Create Date: 2026-10-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7e2f9a31c44'
down_revision: Union[str, None] = 'a1c4d7e92b10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

__all__ = ['revision', 'down_revision', 'branch_labels', 'depends_on']

_COLUMNS = [
    sa.Column('bgg_id', sa.Integer(), nullable=True),
    sa.Column('bgg_title', sa.String(255), nullable=True),
    sa.Column('bgg_year', sa.Integer(), nullable=True),
    sa.Column('bgg_match_score', sa.Float(), nullable=True),
    sa.Column('bgg_players_min', sa.Integer(), nullable=True),
    sa.Column('bgg_players_max', sa.Integer(), nullable=True),
    sa.Column('bgg_playtime_min', sa.Integer(), nullable=True),
    sa.Column('bgg_playtime_max', sa.Integer(), nullable=True),
    sa.Column('bgg_complexity', sa.Float(), nullable=True),
    sa.Column('bgg_category', sa.String(50), nullable=True),
    sa.Column('bgg_enriched_at', sa.DateTime(), nullable=True),
]


def upgrade() -> None:
    for column in _COLUMNS:
        op.add_column('hl_stock_links', column)


def downgrade() -> None:
    for column in reversed(_COLUMNS):
        op.drop_column('hl_stock_links', column.name)
