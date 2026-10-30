"""allow several distro code links per sleeve product

Replaces the single hl_distributor/hl_distro_code pair on sleeve_products with
a link table, since the same sleeve is often sold by more than one distributor.
Existing single links are carried over.

Revision ID: d2e3f4a5b6c7
Revises: c9d1e2f3a4b5
Create Date: 2026-10-31 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd2e3f4a5b6c7'
down_revision: Union[str, None] = 'c9d1e2f3a4b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

__all__ = ['revision', 'down_revision', 'branch_labels', 'depends_on']


def upgrade() -> None:
    op.create_table(
        'sleeve_product_distro_links',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('sleeve_product_id', sa.Integer(), sa.ForeignKey('sleeve_products.id', ondelete='CASCADE'), nullable=False),
        sa.Column('hl_distributor', sa.String(100), nullable=False),
        sa.Column('hl_distro_code', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_unique_constraint(
        'uq_sleeve_product_distro_link', 'sleeve_product_distro_links',
        ['sleeve_product_id', 'hl_distributor', 'hl_distro_code'],
    )
    op.create_index('ix_sleeve_product_distro_links_sleeve_product_id', 'sleeve_product_distro_links', ['sleeve_product_id'])
    op.execute(
        "INSERT INTO sleeve_product_distro_links (sleeve_product_id, hl_distributor, hl_distro_code) "
        "SELECT id, hl_distributor, hl_distro_code FROM sleeve_products "
        "WHERE hl_distributor IS NOT NULL AND hl_distro_code IS NOT NULL"
    )
    op.drop_column('sleeve_products', 'hl_distro_code')
    op.drop_column('sleeve_products', 'hl_distributor')


def downgrade() -> None:
    op.add_column('sleeve_products', sa.Column('hl_distributor', sa.String(100), nullable=True))
    op.add_column('sleeve_products', sa.Column('hl_distro_code', sa.String(100), nullable=True))
    # Keep the oldest link per product
    op.execute(
        "UPDATE sleeve_products sp SET hl_distributor = l.hl_distributor, hl_distro_code = l.hl_distro_code "
        "FROM (SELECT DISTINCT ON (sleeve_product_id) sleeve_product_id, hl_distributor, hl_distro_code "
        "      FROM sleeve_product_distro_links ORDER BY sleeve_product_id, id) l "
        "WHERE l.sleeve_product_id = sp.id"
    )
    op.drop_index('ix_sleeve_product_distro_links_sleeve_product_id', table_name='sleeve_product_distro_links')
    op.drop_table('sleeve_product_distro_links')
