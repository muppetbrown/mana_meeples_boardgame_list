#!/usr/bin/env python3
# export_buy_list.py
# Export buy list from database to CSV for price scraping

import csv
import sys
from pathlib import Path

# Add parent directory to path so we can import from backend
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from config import DATABASE_URL
from models import BuyListGame, Game

COLUMNS = ['game_id', 'bgo_link', 'rank', 'name', 'bgg_id']


def export_buy_list():
    """Export buy list to CSV for price scraping"""
    print("Connecting to database...")

    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        # Query buy list with game details
        results = db.execute(
            select(
                BuyListGame.game_id,
                BuyListGame.bgo_link,
                BuyListGame.rank,
                Game.title,
                Game.bgg_id,
            )
            .join(Game, BuyListGame.game_id == Game.id)
            .where(BuyListGame.on_buy_list == True)
            .where(BuyListGame.bgo_link.isnot(None))
            .order_by(BuyListGame.rank.nullslast(), Game.title)
        ).all()

        if not results:
            print("No games found in buy list with BGO links")

        # Always write the file (header only when empty) so the workflow doesn't fail
        output_dir = Path(__file__).parent.parent / "price_data"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / "buy_list_export.csv"

        with open(output_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(COLUMNS)
            writer.writerows(tuple(row) for row in results)
        print(f"✓ Exported {len(results)} games to {output_file}")

    finally:
        db.close()

if __name__ == "__main__":
    export_buy_list()
