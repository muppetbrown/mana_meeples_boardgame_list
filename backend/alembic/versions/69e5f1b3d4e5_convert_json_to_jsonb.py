"""convert json to jsonb

Revision ID: 69e5f1b3d4e5
Revises: 68d4e9a1b2c3
Create Date: 2026-01-11 05:53:27.000000

Sprint 9: Fix JSON column types to JSONB for full-text search compatibility

This migration converts JSON columns (designers, publishers, mechanics, artists)
to JSONB type for PostgreSQL. This is required for the full-text search trigger
which uses jsonb_array_elements_text().

JSONB is the recommended PostgreSQL type for JSON data as it's more efficient
and supports more operations than the plain JSON type.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic
revision = '69e5f1b3d4e5'
down_revision = '68d4e9a1b2c3'
branch_labels = None
depends_on = None


def upgrade():
    """
    Convert JSON columns to JSONB for PostgreSQL.

    This migration:
    1. Converts designers, publishers, mechanics, artists columns from JSON to JSONB
    2. Preserves all existing data during conversion
    3. Only runs on PostgreSQL (SQLite doesn't have JSONB type)

    Note: The conversion is safe - PostgreSQL can automatically cast JSON to JSONB.
    """
    connection = op.get_bind()

    # Only run on PostgreSQL
    if connection.dialect.name != 'postgresql':
        print("Skipping JSON to JSONB conversion (PostgreSQL only)")
        return

    # Drop the trigger temporarily to avoid errors during column type changes
    op.execute("DROP TRIGGER IF EXISTS boardgames_search_vector_trigger ON boardgames")

    # Convert JSON columns to JSONB
    # PostgreSQL can automatically cast JSON to JSONB, so we use USING clause
    json_columns = ['designers', 'publishers', 'mechanics', 'artists']

    for column in json_columns:
        op.execute(f"""
            ALTER TABLE boardgames
            ALTER COLUMN {column} TYPE jsonb
            USING {column}::jsonb
        """)

    # Recreate the trigger with the correct JSONB types
    op.execute("""
        CREATE TRIGGER boardgames_search_vector_trigger
        BEFORE INSERT OR UPDATE ON boardgames
        FOR EACH ROW
        EXECUTE FUNCTION boardgames_search_vector_update();
    """)


def downgrade():
    """
    Convert JSONB columns back to JSON.

    Safe to run - converts JSONB back to JSON type.
    PostgreSQL only - skips on SQLite.
    """
    connection = op.get_bind()

    # Only run on PostgreSQL
    if connection.dialect.name != 'postgresql':
        print("Skipping JSONB to JSON conversion downgrade (PostgreSQL only)")
        return

    # Drop the trigger temporarily
    op.execute("DROP TRIGGER IF EXISTS boardgames_search_vector_trigger ON boardgames")

    # Convert JSONB columns back to JSON
    json_columns = ['designers', 'publishers', 'mechanics', 'artists']

    for column in json_columns:
        op.execute(f"""
            ALTER TABLE boardgames
            ALTER COLUMN {column} TYPE json
            USING {column}::json
        """)

    # Recreate the trigger
    op.execute("""
        CREATE TRIGGER boardgames_search_vector_trigger
        BEFORE INSERT OR UPDATE ON boardgames
        FOR EACH ROW
        EXECUTE FUNCTION boardgames_search_vector_update();
    """)
