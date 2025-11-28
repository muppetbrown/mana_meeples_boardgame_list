#!/usr/bin/env python3
"""
Test script to verify PostgreSQL database connection and table structure.
Run this before deploying to Render to ensure everything is configured correctly.
"""
import os
import sys
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.pool import QueuePool

# Set the DATABASE_URL to the PostgreSQL instance
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://tcg_admin:1FhON1ZvCR7bRry4L9UoonvorMD4BjAR@dpg-d3i3387diees738trbg0-a.singapore-postgres.render.com/tcg_singles"
)

def test_connection():
    """Test basic database connection."""
    print("=" * 70)
    print("PostgreSQL Database Connection Test")
    print("=" * 70)

    try:
        # Create engine with PostgreSQL pooling settings
        print(f"\n1. Creating database engine...")
        print(f"   Database: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'unknown'}")

        engine = create_engine(
            DATABASE_URL,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=3600,
            pool_pre_ping=True,
            echo=False
        )

        print("   ✓ Engine created successfully")

        # Test connection
        print(f"\n2. Testing database connection...")
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            print(f"   ✓ Connected to PostgreSQL")
            print(f"   Version: {version[:50]}...")

        # Check if boardgames table exists
        print(f"\n3. Checking for 'boardgames' table...")
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        if 'boardgames' in tables:
            print(f"   ✓ 'boardgames' table exists")

            # Get column information
            print(f"\n4. Inspecting 'boardgames' table structure...")
            columns = inspector.get_columns('boardgames')
            print(f"   Found {len(columns)} columns:")

            key_columns = ['id', 'title', 'bgg_id', 'mana_meeple_category', 'nz_designer',
                          'designers', 'mechanics', 'complexity', 'average_rating']

            for col in columns:
                if col['name'] in key_columns:
                    col_type = str(col['type'])
                    nullable = "NULL" if col['nullable'] else "NOT NULL"
                    print(f"      - {col['name']:25} {col_type:20} {nullable}")

            # Count records
            print(f"\n5. Counting records...")
            with engine.connect() as conn:
                result = conn.execute(text("SELECT COUNT(*) FROM boardgames;"))
                count = result.fetchone()[0]
                print(f"   ✓ Found {count} board games in database")

                # Sample a few records
                if count > 0:
                    print(f"\n6. Sample records (first 3)...")
                    result = conn.execute(text(
                        "SELECT id, title, year, mana_meeple_category, nz_designer "
                        "FROM boardgames ORDER BY id LIMIT 3;"
                    ))
                    for row in result:
                        print(f"      ID {row[0]}: {row[1]} ({row[2]}) - "
                              f"Category: {row[3]}, NZ Designer: {row[4]}")
        else:
            print(f"   ✗ ERROR: 'boardgames' table not found!")
            print(f"   Available tables: {', '.join(tables)}")
            return False

        # Test JSON columns
        print(f"\n7. Testing JSON column support...")
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT title, designers, mechanics "
                "FROM boardgames "
                "WHERE designers IS NOT NULL LIMIT 1;"
            ))
            row = result.fetchone()
            if row:
                print(f"   ✓ JSON columns working correctly")
                print(f"   Sample: {row[0]}")
                print(f"   Designers: {row[1][:100] if row[1] else 'None'}...")

        print("\n" + "=" * 70)
        print("✓ All tests passed! Database is ready for deployment.")
        print("=" * 70)
        return True

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        print("\nPlease check:")
        print("  1. Database credentials are correct")
        print("  2. Database server is accessible")
        print("  3. 'boardgames' table exists with correct schema")
        print("  4. psycopg2-binary is installed: pip install psycopg2-binary")
        return False
    finally:
        if 'engine' in locals():
            engine.dispose()

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
