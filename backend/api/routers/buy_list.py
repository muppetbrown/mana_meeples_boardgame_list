# api/routers/buy_list.py
"""
Buy List API endpoints for managing games to purchase and tracking prices.
Admin-only endpoints for managing buy list, LPG status, and price data.
"""
import json
import logging
import os
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func
from sqlalchemy.orm import Session, joinedload

from api.dependencies import require_admin_auth
from database import get_db
from models import BuyListGame, Game, PriceOffer, PriceSnapshot
from schemas import BuyListGameCreate, BuyListGameOut, BuyListGameUpdate

logger = logging.getLogger(__name__)

# Create router with prefix and tags
router = APIRouter(prefix="/api/admin/buy-list", tags=["buy-list"])


def compute_buy_filter(
    best_price: Optional[float],
    lpg_status: Optional[str],
    lpg_rrp: Optional[float],
    discount_pct: Optional[float],
) -> bool:
    """
    Compute whether a game should be filtered/highlighted for buying.

    Excel formula logic:
    =LET(
      b, [@BEST],
      s, [@[LPG_Status]],
      r, [@[LPG_RRP]],
      d, [@Discount],
      OR(
        AND(
          OR(s={"AVAILABLE","BACK_ORDER"}),
          IF(ISNUMBER(b), AND(b<>0, b*2<=r), FALSE)
        ),
        AND(
          OR(s={"NOT_FOUND","BACK_ORDER_OOS"}),
          d>30
        )
      )
    )
    """
    if not lpg_status:
        return False

    # Condition 1: Status is AVAILABLE or BACK_ORDER, and best price * 2 <= RRP
    if lpg_status in ["AVAILABLE", "BACK_ORDER"]:
        if best_price and lpg_rrp and best_price > 0:
            if best_price * 2 <= lpg_rrp:
                return True

    # Condition 2: Status is NOT_FOUND or BACK_ORDER_OOS, and discount > 30%
    if lpg_status in ["NOT_FOUND", "BACK_ORDER_OOS"]:
        if discount_pct and discount_pct > 30:
            return True

    return False


def build_buy_list_response(
    buy_list_entry: BuyListGame, latest_price: Optional[PriceSnapshot] = None
) -> Dict[str, Any]:
    """Build buy list response with computed buy_filter field"""
    # Convert to dict
    result = {
        "id": buy_list_entry.id,
        "game_id": buy_list_entry.game_id,
        "rank": buy_list_entry.rank,
        "bgo_link": buy_list_entry.bgo_link,
        "lpg_rrp": float(buy_list_entry.lpg_rrp) if buy_list_entry.lpg_rrp else None,
        "lpg_status": buy_list_entry.lpg_status,
        "on_buy_list": buy_list_entry.on_buy_list,
        "created_at": buy_list_entry.created_at.isoformat(),
        "updated_at": buy_list_entry.updated_at.isoformat(),
        # Game details
        "title": buy_list_entry.game.title if buy_list_entry.game else None,
        "thumbnail_url": (
            buy_list_entry.game.thumbnail_url if buy_list_entry.game else None
        ),
        "bgg_id": buy_list_entry.game.bgg_id if buy_list_entry.game else None,
        # Latest price data
        "latest_price": None,
        "buy_filter": None,
    }

    if latest_price:
        result["latest_price"] = {
            "id": latest_price.id,
            "game_id": latest_price.game_id,
            "checked_at": latest_price.checked_at.isoformat(),
            "low_price": (
                float(latest_price.low_price) if latest_price.low_price else None
            ),
            "mean_price": (
                float(latest_price.mean_price) if latest_price.mean_price else None
            ),
            "best_price": (
                float(latest_price.best_price) if latest_price.best_price else None
            ),
            "best_store": latest_price.best_store,
            "discount_pct": (
                float(latest_price.discount_pct) if latest_price.discount_pct else None
            ),
            "delta": float(latest_price.delta) if latest_price.delta else None,
        }

        # Compute buy filter
        result["buy_filter"] = compute_buy_filter(
            best_price=(
                float(latest_price.best_price) if latest_price.best_price else None
            ),
            lpg_status=buy_list_entry.lpg_status,
            lpg_rrp=float(buy_list_entry.lpg_rrp) if buy_list_entry.lpg_rrp else None,
            discount_pct=(
                float(latest_price.discount_pct) if latest_price.discount_pct else None
            ),
        )

    return result


# ------------------------------------------------------------------------------
# Buy List Management Endpoints
# ------------------------------------------------------------------------------


@router.get("/games", dependencies=[Depends(require_admin_auth)])
async def list_buy_list_games(
    db: Session = Depends(get_db),
    on_buy_list: Optional[bool] = Query(None, description="Filter by on_buy_list status"),
    lpg_status: Optional[str] = Query(None, description="Filter by LPG status"),
    buy_filter: Optional[bool] = Query(
        None, description="Filter by computed buy_filter value"
    ),
    sort_by: str = Query("rank", description="Sort field: rank, title, updated_at"),
    sort_desc: bool = Query(False, description="Sort in descending order"),
):
    """
    Get all games on the buy list with their latest pricing data.
    Supports filtering and sorting.
    """
    try:
        # Base query with eager loading
        query = (
            db.query(BuyListGame)
            .options(joinedload(BuyListGame.game))
            .filter(BuyListGame.on_buy_list == True)
        )

        # Apply filters
        if on_buy_list is not None:
            query = query.filter(BuyListGame.on_buy_list == on_buy_list)

        if lpg_status:
            query = query.filter(BuyListGame.lpg_status == lpg_status)

        # Apply sorting
        if sort_by == "rank":
            query = query.order_by(
                desc(BuyListGame.rank) if sort_desc else BuyListGame.rank
            )
        elif sort_by == "title":
            query = query.join(Game).order_by(
                desc(Game.title) if sort_desc else Game.title
            )
        elif sort_by == "updated_at":
            query = query.order_by(
                desc(BuyListGame.updated_at) if sort_desc else BuyListGame.updated_at
            )
        else:
            # Default to rank
            query = query.order_by(BuyListGame.rank.nullslast())

        buy_list_entries = query.all()

        # Get latest price snapshots for all games
        game_ids = [entry.game_id for entry in buy_list_entries]
        if game_ids:
            # Subquery to get latest checked_at per game
            latest_dates = (
                db.query(
                    PriceSnapshot.game_id,
                    func.max(PriceSnapshot.checked_at).label("max_date"),
                )
                .filter(PriceSnapshot.game_id.in_(game_ids))
                .group_by(PriceSnapshot.game_id)
                .subquery()
            )

            # Get full price snapshots for latest dates
            latest_prices = (
                db.query(PriceSnapshot)
                .join(
                    latest_dates,
                    (PriceSnapshot.game_id == latest_dates.c.game_id)
                    & (PriceSnapshot.checked_at == latest_dates.c.max_date),
                )
                .all()
            )

            # Create lookup dict
            price_lookup = {price.game_id: price for price in latest_prices}
        else:
            price_lookup = {}

        # Build response with computed buy_filter
        results = []
        for entry in buy_list_entries:
            latest_price = price_lookup.get(entry.game_id)
            result = build_buy_list_response(entry, latest_price)

            # Apply buy_filter filter if requested
            if buy_filter is not None:
                if result["buy_filter"] == buy_filter:
                    results.append(result)
            else:
                results.append(result)

        return {"total": len(results), "items": results}

    except Exception as e:
        logger.error(f"Error listing buy list games: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve buy list")


@router.post("/games", dependencies=[Depends(require_admin_auth)])
async def add_to_buy_list(
    data: BuyListGameCreate, db: Session = Depends(get_db)
):
    """
    Add a game to the buy list by BGG ID.
    If the game doesn't exist in the database, it will be imported from BoardGameGeek first.
    """
    try:
        # Import BGG service for auto-import
        from bgg_service import fetch_bgg_thing

        # Check if game with this BGG ID already exists
        game = db.query(Game).filter(Game.bgg_id == data.bgg_id).first()

        if not game:
            # Game doesn't exist - import from BGG
            logger.info(f"Game with BGG ID {data.bgg_id} not found, importing from BGG...")

            try:
                bgg_data = await fetch_bgg_thing(data.bgg_id)
            except Exception as e:
                logger.error(f"Failed to fetch from BGG: {e}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to import game from BGG ID {data.bgg_id}: {str(e)}"
                )

            # Create new game entry with BUY_LIST status
            game = Game(
                title=bgg_data.get("title", "Unknown"),
                categories=", ".join(bgg_data.get("categories", [])),
                year=bgg_data.get("year"),
                players_min=bgg_data.get("players_min"),
                players_max=bgg_data.get("players_max"),
                playtime_min=bgg_data.get("playtime_min"),
                playtime_max=bgg_data.get("playtime_max"),
                thumbnail_url=bgg_data.get("thumbnail"),
                image=bgg_data.get("image"),
                bgg_id=data.bgg_id,
                description=bgg_data.get("description"),
                designers=bgg_data.get("designers"),
                publishers=bgg_data.get("publishers"),
                mechanics=bgg_data.get("mechanics"),
                artists=bgg_data.get("artists"),
                average_rating=bgg_data.get("average_rating"),
                complexity=bgg_data.get("complexity"),
                bgg_rank=bgg_data.get("bgg_rank"),
                users_rated=bgg_data.get("users_rated"),
                min_age=bgg_data.get("min_age"),
                is_cooperative=bgg_data.get("is_cooperative"),
                status="BUY_LIST",  # Mark as buy list item
            )
            db.add(game)
            db.flush()  # Get the game ID
            logger.info(f"Imported game '{game.title}' from BGG ID {data.bgg_id}")

        else:
            # Game exists - update status to BUY_LIST if it's not already
            if game.status != "BUY_LIST":
                game.status = "BUY_LIST"
                logger.info(f"Updated game '{game.title}' status to BUY_LIST")

        # Check if already on buy list
        existing = (
            db.query(BuyListGame).filter(BuyListGame.game_id == game.id).first()
        )
        if existing:
            raise HTTPException(
                status_code=400, detail="Game already on buy list"
            )

        # Create buy list entry
        buy_list_entry = BuyListGame(
            game_id=game.id,
            rank=data.rank,
            bgo_link=data.bgo_link,
            lpg_rrp=data.lpg_rrp,
            lpg_status=data.lpg_status,
            on_buy_list=True,
        )

        db.add(buy_list_entry)
        db.commit()
        db.refresh(buy_list_entry)

        # Load game relationship
        db.refresh(buy_list_entry, ["game"])

        logger.info(f"Added game '{game.title}' (BGG ID {data.bgg_id}) to buy list")

        return build_buy_list_response(buy_list_entry)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding game to buy list: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to add game to buy list: {str(e)}")


@router.put("/games/{buy_list_id}", dependencies=[Depends(require_admin_auth)])
async def update_buy_list_game(
    buy_list_id: int, data: BuyListGameUpdate, db: Session = Depends(get_db)
):
    """Update buy list game details (rank, LPG status, etc.)"""
    try:
        buy_list_entry = db.query(BuyListGame).filter(BuyListGame.id == buy_list_id).first()
        if not buy_list_entry:
            raise HTTPException(status_code=404, detail="Buy list entry not found")

        # Update fields
        if data.rank is not None:
            buy_list_entry.rank = data.rank
        if data.bgo_link is not None:
            buy_list_entry.bgo_link = data.bgo_link
        if data.lpg_rrp is not None:
            buy_list_entry.lpg_rrp = data.lpg_rrp
        if data.lpg_status is not None:
            buy_list_entry.lpg_status = data.lpg_status
        if data.on_buy_list is not None:
            buy_list_entry.on_buy_list = data.on_buy_list

        buy_list_entry.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(buy_list_entry)

        # Load game relationship
        db.refresh(buy_list_entry, ["game"])

        # Get latest price
        latest_price = (
            db.query(PriceSnapshot)
            .filter(PriceSnapshot.game_id == buy_list_entry.game_id)
            .order_by(desc(PriceSnapshot.checked_at))
            .first()
        )

        logger.info(f"Updated buy list entry {buy_list_id}")

        return build_buy_list_response(buy_list_entry, latest_price)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating buy list game: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update buy list game")


@router.delete("/games/{buy_list_id}", dependencies=[Depends(require_admin_auth)])
async def remove_from_buy_list(buy_list_id: int, db: Session = Depends(get_db)):
    """Remove a game from the buy list"""
    try:
        buy_list_entry = db.query(BuyListGame).filter(BuyListGame.id == buy_list_id).first()
        if not buy_list_entry:
            raise HTTPException(status_code=404, detail="Buy list entry not found")

        db.delete(buy_list_entry)
        db.commit()

        logger.info(f"Removed buy list entry {buy_list_id}")

        return {"message": "Game removed from buy list", "id": buy_list_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing game from buy list: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500, detail="Failed to remove game from buy list"
        )


# ------------------------------------------------------------------------------
# Price Data Endpoints
# ------------------------------------------------------------------------------


@router.post("/import-prices", dependencies=[Depends(require_admin_auth)])
async def import_prices_from_json(
    source_file: str = Query(..., description="Filename of JSON price data"),
    db: Session = Depends(get_db),
):
    """
    Import price data from GitHub Actions JSON output.
    Expected file location: backend/price_data/{source_file}
    """
    try:
        # Load JSON file
        price_data_dir = Path(__file__).parent.parent.parent / "price_data"
        json_file = price_data_dir / source_file

        if not json_file.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Price data file not found: {source_file}",
            )

        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Validate structure
        if "checked_at" not in data or "games" not in data:
            raise HTTPException(
                status_code=400,
                detail="Invalid JSON structure: must contain 'checked_at' and 'games'",
            )

        checked_at = datetime.fromisoformat(data["checked_at"])
        games_data = data["games"]

        imported_count = 0
        skipped_count = 0

        for game_data in games_data:
            try:
                # Find game by BGG ID or title
                game = None
                if "bgg_id" in game_data and game_data["bgg_id"]:
                    game = (
                        db.query(Game)
                        .filter(Game.bgg_id == game_data["bgg_id"])
                        .first()
                    )

                if not game and "name" in game_data:
                    game = (
                        db.query(Game)
                        .filter(Game.title == game_data["name"])
                        .first()
                    )

                if not game:
                    logger.warning(
                        f"Game not found for price import: {game_data.get('name')}"
                    )
                    skipped_count += 1
                    continue

                # Create price snapshot
                price_snapshot = PriceSnapshot(
                    game_id=game.id,
                    checked_at=checked_at,
                    low_price=game_data.get("low_price"),
                    mean_price=game_data.get("mean_price"),
                    best_price=game_data.get("best_price"),
                    best_store=game_data.get("best_store"),
                    discount_pct=game_data.get("discount_pct"),
                    delta=game_data.get("delta"),
                    source_file=source_file,
                )
                db.add(price_snapshot)

                # Import price offers if present
                if "offers" in game_data:
                    for offer_data in game_data["offers"]:
                        price_offer = PriceOffer(
                            game_id=game.id,
                            checked_at=checked_at,
                            store=offer_data.get("store"),
                            price_nzd=offer_data.get("price_nzd"),
                            availability=offer_data.get("availability"),
                            store_link=offer_data.get("store_link"),
                            in_stock=offer_data.get("in_stock"),
                        )
                        db.add(price_offer)

                imported_count += 1

            except Exception as e:
                logger.error(f"Error importing price for game: {e}")
                skipped_count += 1
                continue

        db.commit()

        logger.info(
            f"Imported {imported_count} price snapshots, skipped {skipped_count}"
        )

        return {
            "message": "Price data imported successfully",
            "imported": imported_count,
            "skipped": skipped_count,
            "checked_at": checked_at.isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error importing prices from JSON: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to import price data")


@router.get("/last-updated", dependencies=[Depends(require_admin_auth)])
async def get_last_price_update(db: Session = Depends(get_db)):
    """Get timestamp of last price update"""
    try:
        latest_snapshot = (
            db.query(PriceSnapshot).order_by(desc(PriceSnapshot.checked_at)).first()
        )

        if not latest_snapshot:
            return {"last_updated": None, "source_file": None}

        return {
            "last_updated": latest_snapshot.checked_at.isoformat(),
            "source_file": latest_snapshot.source_file,
        }

    except Exception as e:
        logger.error(f"Error getting last price update: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to get last price update"
        )
