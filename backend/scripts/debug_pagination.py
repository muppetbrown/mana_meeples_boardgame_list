#!/usr/bin/env python3
"""
Test script to debug pagination issues.
Run this to check what the database is returning for specific pages.
"""
import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_read_db_session
from services.game_service import GameService


def test_pagination(category="all", page_size=12, start_page=1, end_page=20):
    """Test pagination for a specific category"""
    print("=" * 80)
    print(f"Testing Pagination for Category: {category}")
    print(f"Page size: {page_size}")
    print("=" * 80)

    db = next(get_read_db_session())
    service = GameService(db)

    total_items_collected = 0
    all_ids = set()

    for page in range(start_page, end_page + 1):
        print(f"\n--- Page {page} ---")

        try:
            games, total = service.get_filtered_games(
                search=None,
                category=category if category != "all" else None,
                designer=None,
                nz_designer=None,
                players=None,
                complexity_min=None,
                complexity_max=None,
                recently_added_days=None,
                sort="title_asc",
                page=page,
                page_size=page_size,
            )

            num_games = len(games)
            offset = (page - 1) * page_size
            expected = min(page_size, max(0, total - offset))

            print(f"  Total count: {total}")
            print(f"  Offset: {offset}")
            print(f"  Expected items: {expected}")
            print(f"  Actual items returned: {num_games}")

            if num_games > 0:
                total_items_collected += num_games
                new_ids = {game.id for game in games}
                duplicates = all_ids & new_ids

                if duplicates:
                    print(f"  ⚠️  WARNING: Found {len(duplicates)} duplicate IDs!")
                    print(f"      Duplicate IDs: {duplicates}")

                all_ids.update(new_ids)

                print(f"  First game: {games[0].title}")
                print(f"  Last game: {games[-1].title}")
                print(f"  Cumulative unique items: {len(all_ids)}")
            else:
                print(f"  No items returned")

            # Check for mismatch
            if num_games != expected:
                print(f"  ❌ MISMATCH: Expected {expected} but got {num_games}")
            else:
                print(f"  ✓ Count matches expected")

            # Stop if we've collected all items
            if len(all_ids) >= total:
                print(f"\n✓ All {total} items collected successfully")
                break

            # Stop if page returns no items
            if num_games == 0:
                if len(all_ids) < total:
                    print(f"\n❌ PAGINATION STOPPED EARLY!")
                    print(f"   Collected: {len(all_ids)}")
                    print(f"   Total: {total}")
                    print(f"   Missing: {total - len(all_ids)} items")
                break

        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            break

    print("\n" + "=" * 80)
    print("Summary:")
    print(f"  Unique items collected: {len(all_ids)}")
    print(f"  Total according to count query: {total}")
    print(f"  Match: {'✓ YES' if len(all_ids) == total else '❌ NO'}")
    print("=" * 80)


def main():
    """Run pagination tests for problematic categories"""
    # Test "all" category (reported issue: stops at 200 of 221)
    print("\n\n🔍 Testing 'all' category (reported: 200 of 221)\n")
    test_pagination(category="all", page_size=12, start_page=1, end_page=25)

    # Test "PARTY_ICEBREAKERS" category (reported issue: stops at 59 of 61)
    print("\n\n🔍 Testing 'PARTY_ICEBREAKERS' category (reported: 59 of 61)\n")
    test_pagination(category="PARTY_ICEBREAKERS", page_size=12, start_page=1, end_page=10)

    # Test a working category for comparison
    print("\n\n🔍 Testing 'CORE_STRATEGY' category (for comparison)\n")
    test_pagination(category="CORE_STRATEGY", page_size=12, start_page=1, end_page=10)


if __name__ == "__main__":
    main()
