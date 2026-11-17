"""drop indexes that duplicate another index on the same column

Each of these covers exactly the same column as a primary key, a unique constraint or
another index on the same table, so it is only extra work on every write:

  ix_sleeves_id                      same as sleeves_pkey
  idx_sleeve_game                    same as ix_sleeves_game_id
  ix_hl_stock_links_hl_internal_id   same as uq_hl_stock_links_internal_id
  idx_buy_list_game_id               same as buy_list_games_game_id_key

Revision ID: e7f8a9b0c1d2
Revises: d2e3f4a5b6c7
Create Date: 2026-11-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'e7f8a9b0c1d2'
down_revision: Union[str, None] = 'd2e3f4a5b6c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

__all__ = ['revision', 'down_revision', 'branch_labels', 'depends_on']

_DUPLICATES = (
    ('ix_sleeves_id', 'sleeves', 'id'),
    ('idx_sleeve_game', 'sleeves', 'game_id'),
    ('ix_hl_stock_links_hl_internal_id', 'hl_stock_links', 'hl_internal_id'),
    ('idx_buy_list_game_id', 'buy_list_games', 'game_id'),
)


def upgrade() -> None:
    for name, _table, _column in _DUPLICATES:
        op.execute(f'DROP INDEX IF EXISTS {name}')


def downgrade() -> None:
    for name, table, column in _DUPLICATES:
        op.execute(f'CREATE INDEX IF NOT EXISTS {name} ON {table} ({column})')
