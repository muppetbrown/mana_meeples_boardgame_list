"""add fulltext search index

Revision ID: 68d4e9a1b2c3
Revises: 67525c3297b2
Create Date: 2026-01-09 12:00:00.000000

Sprint 9: Full-text search optimization for 400+ games scale

This migration adds PostgreSQL full-text search capabilities to the boardgames table
using TSVECTOR column and GIN index for significantly faster title/description/designer searches.

Performance Impact: 10-100x faster search queries compared to LIKE queries.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic
revision = '68d4e9a1b2c3'
down_revision = '67525c3297b2'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add full-text search index to boardgames table.

    Creates (PostgreSQL only):
    1. search_vector column (TSVECTOR type)
    2. GIN index for efficient full-text search
    3. Trigger to auto-update search_vector on INSERT/UPDATE
    4. Populates existing records

    Note: This migration only runs on PostgreSQL. SQLite (dev) is skipped.
    """
    connection = op.get_bind()

    # Only run on PostgreSQL (production database)
    # SQLite (local dev) doesn't support TSVECTOR and doesn't need this optimization
    if connection.dialect.name != 'postgresql':
        print("Skipping full-text search migration (PostgreSQL only)")
        return

    # Add tsvector column for full-text search
    op.add_column('boardgames',
        sa.Column('search_vector', postgresql.TSVECTOR, nullable=True)
    )

    # Create GIN index for full-text search
    # CONCURRENTLY would be ideal for production, but not supported in transactions
    # Run this migration during low-traffic period
    op.execute("""
        CREATE INDEX idx_boardgames_search_vector
        ON boardgames
        USING gin(search_vector)
    """)

    # Create trigger function to auto-update search_vector
    # Weights: A (highest) for title, B for description, C for designers
    op.execute("""
        CREATE OR REPLACE FUNCTION boardgames_search_vector_update()
        RETURNS trigger AS $$
        BEGIN
            NEW.search_vector :=
                setweight(to_tsvector('english', coalesce(NEW.title, '')), 'A') ||
                setweight(to_tsvector('english', coalesce(NEW.description, '')), 'B') ||
                setweight(to_tsvector('english', coalesce(
                    array_to_string(ARRAY(SELECT jsonb_array_elements_text(NEW.designers)), ' '),
                    ''
                )), 'C');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER boardgames_search_vector_trigger
        BEFORE INSERT OR UPDATE ON boardgames
        FOR EACH ROW
        EXECUTE FUNCTION boardgames_search_vector_update();
    """)

    # Populate existing records with search_vector data
    # This may take a moment for 400+ games but is a one-time operation
    op.execute("""
        UPDATE boardgames
        SET search_vector =
            setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
            setweight(to_tsvector('english', coalesce(description, '')), 'B') ||
            setweight(to_tsvector('english', coalesce(
                array_to_string(ARRAY(SELECT jsonb_array_elements_text(designers)), ' '),
                ''
            )), 'C')
    """)


def downgrade():
    """
    Remove full-text search index and revert to original schema.

    Safe to run - removes trigger, function, index, and column.
    PostgreSQL only - skips on SQLite.
    """
    connection = op.get_bind()

    # Only run on PostgreSQL
    if connection.dialect.name != 'postgresql':
        print("Skipping full-text search migration downgrade (PostgreSQL only)")
        return

    # Drop trigger first
    op.execute("DROP TRIGGER IF EXISTS boardgames_search_vector_trigger ON boardgames")

    # Drop function
    op.execute("DROP FUNCTION IF EXISTS boardgames_search_vector_update()")

    # Drop index
    op.execute("DROP INDEX IF EXISTS idx_boardgames_search_vector")

    # Drop column
    op.drop_column('boardgames', 'search_vector')
