"""add game_distro_links table

Manual links from a game in this library to a distributor product code in the
HL Timaru distro_codes catalogue, for when title fuzzy-matching misses a
listing. Stores only the (distributor, distro_code) key; name/cost/stock are
read live from HL.

Revision ID: a1c4d7e92b10
Revises: 93034f249ca7
Create Date: 2026-10-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1c4d7e92b10'
down_revision: Union[str, None] = '93034f249ca7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

__all__ = ['revision', 'down_revision', 'branch_labels', 'depends_on']


def upgrade() -> None:
    op.create_table(
        'game_distro_links',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('game_id', sa.Integer(), sa.ForeignKey('boardgames.id', ondelete='CASCADE'), nullable=False),
        sa.Column('distributor', sa.String(100), nullable=False),
        sa.Column('distro_code', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_unique_constraint(
        'uq_game_distro_links_game_dist_code', 'game_distro_links', ['game_id', 'distributor', 'distro_code']
    )
    op.create_index('ix_game_distro_links_game_id', 'game_distro_links', ['game_id'])


def downgrade() -> None:
    op.drop_index('ix_game_distro_links_game_id', table_name='game_distro_links')
    op.drop_table('game_distro_links')
