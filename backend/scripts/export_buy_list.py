#!/usr/bin/env python3
# export_buy_list.py
# Export buy list from database to CSV for price scraping

import os
import sys
from pathlib import Path

# Add parent directory to path so we can import from backend
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from config import DATABASE_URL
from models import BuyListGame, Game

def export_buy_list():
    """Export buy list to CSV for price scraping"""
    print(f"Connecting to database...")

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

            # Create empty CSV file so the workflow doesn't fail
            output_dir = Path(__file__).parent.parent / "price_data"
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_dir / "buy_list_export.csv"

            # Write empty CSV with headers
            df_empty = pd.DataFrame(columns=['game_id', 'bgo_link', 'rank', 'name', 'bgg_id'])
            df_empty.to_csv(output_file, index=False)
            print(f"✓ Created empty CSV at {output_file}")
            return

        # Convert to DataFrame
        df = pd.DataFrame(results, columns=['game_id', 'bgo_link', 'rank', 'name', 'bgg_id'])

        # Write to CSV
        output_dir = Path(__file__).parent.parent / "price_data"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / "buy_list_export.csv"

        df.to_csv(output_file, index=False)
        print(f"✓ Exported {len(df)} games to {output_file}")

    finally:
        db.close()

if __name__ == "__main__":
    export_buy_list()
