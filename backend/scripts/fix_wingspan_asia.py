#!/usr/bin/env python3
"""
Fix Wingspan Asia expansion type to show it as standalone.

Wingspan Asia (BGG ID 266192) is a standalone expansion that can be played
without the base Wingspan game. This script updates its expansion_type
from 'requires_base' to 'both' so it appears in the public catalogue.
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database import SessionLocal
from models import Game
from sqlalchemy import or_

def fix_wingspan_asia():
    """Update Wingspan Asia to be recognized as standalone expansion."""
    db = SessionLocal()
    try:
        # Find Wingspan Asia by BGG ID
        wingspan_asia = db.query(Game).filter(Game.bgg_id == 266192).first()

        if not wingspan_asia:
            print("❌ Wingspan Asia (BGG ID 266192) not found in database")
            print("   It may not have been imported yet.")
            return False

        print(f"\n✓ Found: {wingspan_asia.title}")
        print(f"  BGG ID: {wingspan_asia.bgg_id}")
        print(f"  Current status:")
        print(f"    - is_expansion: {wingspan_asia.is_expansion}")
        print(f"    - expansion_type: {wingspan_asia.expansion_type}")
        print(f"    - base_game_id: {wingspan_asia.base_game_id}")
        print(f"    - status: {wingspan_asia.status}")

        # Check if it's already set correctly
        if wingspan_asia.expansion_type == "both":
            print("\n✓ Wingspan Asia is already set as standalone expansion")
            return True

        # Update to standalone expansion
        wingspan_asia.expansion_type = "both"

        # Also verify it's marked as expansion
        if not wingspan_asia.is_expansion:
            print("\n  ⚠️  Warning: is_expansion was False, setting to True")
            wingspan_asia.is_expansion = True

        # Commit changes
        db.commit()

        print(f"\n✅ Successfully updated Wingspan Asia!")
        print(f"   expansion_type: {wingspan_asia.expansion_type}")
        print(f"   This game will now appear in the public catalogue.")

        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        db.rollback()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Wingspan Asia Expansion Type Fix")
    print("=" * 60)

    success = fix_wingspan_asia()

    if success:
        print("\n✓ Update complete!")
        sys.exit(0)
    else:
        print("\n✗ Update failed")
        sys.exit(1)
