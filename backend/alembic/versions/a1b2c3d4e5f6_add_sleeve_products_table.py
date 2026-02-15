"""Add sleeve_products table and matched_product_id to sleeves

Revision ID: a1b2c3d4e5f6
Revises: f37582e531b4
Create Date: 2026-02-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'f37582e531b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create sleeve_products table
    op.create_table(
        'sleeve_products',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('distributor', sa.String(length=200), nullable=False),
        sa.Column('item_id', sa.String(length=100), nullable=True),
        sa.Column('name', sa.String(length=300), nullable=False),
        sa.Column('width_mm', sa.Integer(), nullable=False),
        sa.Column('height_mm', sa.Integer(), nullable=False),
        sa.Column('sleeves_per_pack', sa.Integer(), nullable=False),
        sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('in_stock', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('ordered', sa.Integer(), nullable=False, server_default='0'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('in_stock >= 0', name='valid_product_stock'),
        sa.CheckConstraint('ordered >= 0', name='valid_product_ordered'),
        sa.CheckConstraint('sleeves_per_pack > 0', name='valid_pack_size'),
        sa.CheckConstraint('price > 0', name='valid_product_price'),
    )
    op.create_index('idx_sleeve_product_size', 'sleeve_products', ['width_mm', 'height_mm'])
    op.create_index('idx_sleeve_product_distributor', 'sleeve_products', ['distributor'])

    # Add matched_product_id FK to sleeves table
    op.add_column('sleeves', sa.Column('matched_product_id', sa.Integer(), nullable=True))
    op.create_index('ix_sleeves_matched_product_id', 'sleeves', ['matched_product_id'])
    op.create_foreign_key(
        'fk_sleeves_matched_product_id',
        'sleeves', 'sleeve_products',
        ['matched_product_id'], ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    # Remove FK and column from sleeves
    op.drop_constraint('fk_sleeves_matched_product_id', 'sleeves', type_='foreignkey')
    op.drop_index('ix_sleeves_matched_product_id', table_name='sleeves')
    op.drop_column('sleeves', 'matched_product_id')

    # Drop sleeve_products table
    op.drop_index('idx_sleeve_product_distributor', table_name='sleeve_products')
    op.drop_index('idx_sleeve_product_size', table_name='sleeve_products')
    op.drop_table('sleeve_products')
