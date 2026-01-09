"""
Comprehensive database analysis script for Render PostgreSQL
Tests indexes, schema, query performance, and JSON queries
"""
import os
from sqlalchemy import create_engine, text
import json
from datetime import datetime

# Database connection
DATABASE_URL = "postgresql://tcg_admin:1FhON1ZvCR7bRry4L9UoonvorMD4BjAR@dpg-d3i3387diees738trbg0-a.singapore-postgres.render.com/tcg_singles"
engine = create_engine(DATABASE_URL, echo=False)

def print_section(title):
    """Print a formatted section header"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")

def run_query(conn, query, description):
    """Run a query and print results"""
    print(f"\n--- {description} ---")
    print(f"Query: {query[:200]}..." if len(query) > 200 else f"Query: {query}")
    print()
    result = conn.execute(text(query))
    rows = result.fetchall()
    for row in rows:
        print(row)
    return rows

def main():
    with engine.connect() as conn:

        # 1. DATABASE OVERVIEW
        print_section("1. DATABASE OVERVIEW")

        run_query(conn,
            "SELECT version();",
            "PostgreSQL Version")

        run_query(conn,
            "SELECT COUNT(*) as total_games FROM boardgames;",
            "Total Games Count")

        run_query(conn,
            """
            SELECT
                pg_size_pretty(pg_database_size('tcg_singles')) as database_size,
                pg_size_pretty(pg_total_relation_size('boardgames')) as boardgames_table_size;
            """,
            "Database Size")

        # 2. TABLE STRUCTURE
        print_section("2. TABLE STRUCTURE & SCHEMA")

        run_query(conn,
            """
            SELECT
                column_name,
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_name = 'boardgames'
            ORDER BY ordinal_position;
            """,
            "Boardgames Table Columns")

        # 3. INDEXES
        print_section("3. CURRENT INDEXES")

        run_query(conn,
            """
            SELECT
                indexname,
                indexdef
            FROM pg_indexes
            WHERE tablename = 'boardgames'
            ORDER BY indexname;
            """,
            "All Indexes on Boardgames Table")

        run_query(conn,
            """
            SELECT
                schemaname,
                relname as tablename,
                indexrelname as indexname,
                pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
            FROM pg_stat_user_indexes
            WHERE relname = 'boardgames'
            ORDER BY pg_relation_size(indexrelid) DESC;
            """,
            "Index Sizes")

        # 4. DATA STATISTICS
        print_section("4. DATA STATISTICS")

        run_query(conn,
            """
            SELECT
                mana_meeple_category,
                COUNT(*) as game_count
            FROM boardgames
            GROUP BY mana_meeple_category
            ORDER BY game_count DESC;
            """,
            "Games by Category")

        run_query(conn,
            """
            SELECT
                COUNT(*) FILTER (WHERE nz_designer = true) as nz_designer_games,
                COUNT(*) FILTER (WHERE nz_designer = false OR nz_designer IS NULL) as non_nz_games,
                COUNT(*) as total
            FROM boardgames;
            """,
            "NZ Designer Statistics")

        run_query(conn,
            """
            SELECT
                COUNT(*) FILTER (WHERE designers IS NOT NULL) as games_with_designers,
                COUNT(*) FILTER (WHERE mechanics IS NOT NULL) as games_with_mechanics,
                COUNT(*) FILTER (WHERE complexity IS NOT NULL) as games_with_complexity,
                COUNT(*) FILTER (WHERE bgg_id IS NOT NULL) as games_with_bgg_id
            FROM boardgames;
            """,
            "Data Completeness")

        # 5. SAMPLE DATA
        print_section("5. SAMPLE DATA")

        rows = run_query(conn,
            """
            SELECT
                id, title, mana_meeple_category, nz_designer,
                complexity, average_rating,
                designers::text as designers_json
            FROM boardgames
            ORDER BY id
            LIMIT 5;
            """,
            "First 5 Games")

        # 6. QUERY PERFORMANCE - Basic Filters
        print_section("6. QUERY PERFORMANCE - BASIC FILTERS")

        run_query(conn,
            """
            EXPLAIN ANALYZE
            SELECT id, title, mana_meeple_category, complexity
            FROM boardgames
            WHERE mana_meeple_category = 'CORE_STRATEGY'
            ORDER BY title
            LIMIT 20;
            """,
            "Category Filter Performance (Should use index)")

        run_query(conn,
            """
            EXPLAIN ANALYZE
            SELECT id, title, nz_designer
            FROM boardgames
            WHERE nz_designer = true
            ORDER BY title
            LIMIT 20;
            """,
            "NZ Designer Filter Performance (Should use index)")

        # 7. QUERY PERFORMANCE - Search
        print_section("7. QUERY PERFORMANCE - SEARCH")

        run_query(conn,
            """
            EXPLAIN ANALYZE
            SELECT id, title, description
            FROM boardgames
            WHERE LOWER(title) LIKE LOWER('%catan%')
            ORDER BY title
            LIMIT 20;
            """,
            "Title Search Performance (ILIKE pattern)")

        run_query(conn,
            """
            EXPLAIN ANALYZE
            SELECT id, title
            FROM boardgames
            WHERE title ILIKE '%pandemic%'
            ORDER BY title
            LIMIT 20;
            """,
            "Title Search with ILIKE")

        # 8. QUERY PERFORMANCE - JSON Queries
        print_section("8. QUERY PERFORMANCE - JSON QUERIES")

        run_query(conn,
            """
            EXPLAIN ANALYZE
            SELECT id, title, designers
            FROM boardgames
            WHERE designers @> '["Reiner Knizia"]'::jsonb
            LIMIT 20;
            """,
            "Designer JSON Search (Exact match with @> operator)")

        run_query(conn,
            """
            EXPLAIN ANALYZE
            SELECT id, title, designers
            FROM boardgames
            WHERE designers::text ILIKE '%knizia%'
            LIMIT 20;
            """,
            "Designer JSON Search (Text cast with ILIKE)")

        run_query(conn,
            """
            EXPLAIN ANALYZE
            SELECT id, title, mechanics
            FROM boardgames
            WHERE mechanics @> '["Deck, Bag, and Pool Building"]'::jsonb
            LIMIT 20;
            """,
            "Mechanics JSON Search (Exact match)")

        # 9. COMPLEX QUERIES
        print_section("9. COMPLEX MULTI-FILTER QUERIES")

        run_query(conn,
            """
            EXPLAIN ANALYZE
            SELECT id, title, mana_meeple_category, complexity, designers
            FROM boardgames
            WHERE
                mana_meeple_category = 'GATEWAY_STRATEGY'
                AND complexity >= 2.0
                AND complexity <= 3.0
                AND designers IS NOT NULL
            ORDER BY complexity DESC
            LIMIT 20;
            """,
            "Category + Complexity Range Filter")

        run_query(conn,
            """
            EXPLAIN ANALYZE
            SELECT id, title, nz_designer, designers
            FROM boardgames
            WHERE
                nz_designer = true
                AND (
                    title ILIKE '%%'
                    OR description ILIKE '%game%'
                    OR designers::text ILIKE '%%%'
                )
            ORDER BY title
            LIMIT 20;
            """,
            "NZ Designer + Text Search Combined")

        # 10. SORTING PERFORMANCE
        print_section("10. SORTING PERFORMANCE")

        run_query(conn,
            """
            EXPLAIN ANALYZE
            SELECT id, title, year
            FROM boardgames
            ORDER BY year DESC NULLS LAST
            LIMIT 20;
            """,
            "Sort by Year")

        run_query(conn,
            """
            EXPLAIN ANALYZE
            SELECT id, title, average_rating
            FROM boardgames
            WHERE average_rating IS NOT NULL
            ORDER BY average_rating DESC
            LIMIT 20;
            """,
            "Sort by Rating (with NULL filter)")

        run_query(conn,
            """
            EXPLAIN ANALYZE
            SELECT id, title, playtime_min
            FROM boardgames
            WHERE playtime_min IS NOT NULL
            ORDER BY playtime_min ASC
            LIMIT 20;
            """,
            "Sort by Playtime")

        # 11. TABLE STATISTICS
        print_section("11. TABLE STATISTICS & HEALTH")

        run_query(conn,
            """
            SELECT
                schemaname,
                relname as tablename,
                n_live_tup as live_rows,
                n_dead_tup as dead_rows,
                n_tup_ins as inserts,
                n_tup_upd as updates,
                n_tup_del as deletes,
                last_vacuum,
                last_autovacuum,
                last_analyze,
                last_autoanalyze
            FROM pg_stat_user_tables
            WHERE relname = 'boardgames';
            """,
            "Table Statistics (Vacuum & Analyze Status)")

        # 12. SAMPLE QUERIES FOR REAL-WORLD USE
        print_section("12. REAL-WORLD QUERY EXAMPLES")

        rows = run_query(conn,
            """
            SELECT id, title, designers, average_rating, complexity
            FROM boardgames
            WHERE mana_meeple_category = 'CORE_STRATEGY'
            ORDER BY average_rating DESC NULLS LAST
            LIMIT 10;
            """,
            "Top 10 Core Strategy Games by Rating")

        rows = run_query(conn,
            """
            SELECT id, title, designers, year
            FROM boardgames
            WHERE nz_designer = true
            ORDER BY year DESC NULLS LAST
            LIMIT 10;
            """,
            "Recent NZ Designer Games")

        print("\n" + "="*80)
        print("  ANALYSIS COMPLETE")
        print("="*80)
        print("\nKey things to look for in EXPLAIN ANALYZE output:")
        print("  - 'Index Scan' = Good (using index)")
        print("  - 'Seq Scan' = May need optimization (full table scan)")
        print("  - 'Bitmap Index Scan' = Good for multiple conditions")
        print("  - Execution time < 10ms = Excellent")
        print("  - Execution time 10-50ms = Good")
        print("  - Execution time > 50ms = May need optimization")

if __name__ == "__main__":
    main()
