# api/routers/buy_list.py
"""
'Games to add' API endpoints: a curated, gap-aware list of candidate games
to add to the collection. Admin-only.

Replaces the earlier price-tracking buy list (BoardGameOracle scraping,
LPG RRP/status) now that games are bought through direct distributor
accounts rather than being hunted for the best online price.
"""
import csv
import io
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, joinedload

from api.dependencies import require_admin_auth
from bgg_service import get_hot_games
from database import get_db
from models import BuyListGame, Game, HLStockLink
from schemas import (
    BuyListGameCreate,
    BuyListGameUpdate,
    BuyListReorderRequest,
    HLStockSignalLinkRequest,
    SuggestGamesRequest,
)
from services.award_winners import get_award_winners
from services.game_suggestion_service import SuggestionServiceError, generate_suggestions
from services.gap_analysis import annotate_candidate, compute_library_gaps
from services.hl_stock_matching import find_best_title_match
from services.hl_stock_service import HLStockServiceError, fetch_hl_board_game_signals

logger = logging.getLogger(__name__)
_sl = lambda v: str(v).replace('\n', ' ').replace('\r', ' ')  # sanitize for logs

# Create router with prefix and tags
router = APIRouter(prefix="/api/admin/buy-list", tags=["buy-list"])


def build_buy_list_response(
    buy_list_entry: BuyListGame, gaps: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Build a 'games to add' response, optionally annotated with gap matches."""
    result = {
        "id": buy_list_entry.id,
        "game_id": buy_list_entry.game_id,
        "rank": buy_list_entry.rank,
        "notes": buy_list_entry.notes,
        "on_buy_list": buy_list_entry.on_buy_list,
        "created_at": buy_list_entry.created_at.replace(tzinfo=timezone.utc).isoformat(),
        "updated_at": buy_list_entry.updated_at.replace(tzinfo=timezone.utc).isoformat(),
        # Game details
        "title": buy_list_entry.game.title if buy_list_entry.game else None,
        "cloudinary_url": (
            buy_list_entry.game.cloudinary_url if buy_list_entry.game else None
        ),
        "image_url": (
            buy_list_entry.game.image if buy_list_entry.game else None
        ),
        "bgg_id": buy_list_entry.game.bgg_id if buy_list_entry.game else None,
        "mana_meeple_category": (
            buy_list_entry.game.mana_meeple_category if buy_list_entry.game else None
        ),
        "players_min": buy_list_entry.game.players_min if buy_list_entry.game else None,
        "players_max": buy_list_entry.game.players_max if buy_list_entry.game else None,
        "gap_match": None,
    }

    if gaps is not None and buy_list_entry.game:
        result["gap_match"] = annotate_candidate(buy_list_entry.game, gaps)

    return result


def _gaps_filled_count(result: Dict[str, Any]) -> int:
    """How many library gaps a 'games to add' entry's gap_match would fill."""
    gap_match = result.get("gap_match") or {}
    count = 1 if gap_match.get("category_is_gap") else 0
    count += len(gap_match.get("matching_player_count_gaps") or [])
    count += 1 if gap_match.get("complexity_is_gap") else 0
    count += 1 if gap_match.get("playtime_is_gap") else 0
    return count


# ------------------------------------------------------------------------------
# Library Gap Analysis
# ------------------------------------------------------------------------------


@router.get("/gaps", dependencies=[Depends(require_admin_auth)])
async def get_library_gaps(db: Session = Depends(get_db)):
    """
    Where the owned collection is thin: category balance and player-count
    coverage, each compared against an even split across their own buckets.
    """
    try:
        return compute_library_gaps(db)
    except Exception as e:
        logger.error(f"Error computing library gaps: {e}")
        raise HTTPException(status_code=500, detail="Failed to compute library gaps")


@router.get("/trending", dependencies=[Depends(require_admin_auth)])
async def get_trending_games(
    limit: int = Query(20, ge=1, le=50, description="How many trending games to return"),
    db: Session = Depends(get_db),
):
    """
    BoardGameGeek's current "Hotness" list, annotated with whether each game
    is already owned or already on the games-to-add list.
    """
    try:
        hot_games = await get_hot_games(limit=limit)
    except Exception as e:
        logger.error(f"Error fetching BGG trending list: {e}")
        raise HTTPException(status_code=502, detail="Failed to fetch trending games from BoardGameGeek")

    bgg_ids = [g["bgg_id"] for g in hot_games]
    if not bgg_ids:
        return {"trending": []}

    games_by_bgg_id = {
        game.bgg_id: game
        for game in db.execute(select(Game).where(Game.bgg_id.in_(bgg_ids))).scalars().all()
    }
    game_ids = [game.id for game in games_by_bgg_id.values()]
    queued_game_ids = set()
    if game_ids:
        queued_game_ids = {
            game_id
            for (game_id,) in db.execute(
                select(BuyListGame.game_id).where(
                    BuyListGame.on_buy_list == True,  # noqa: E712
                    BuyListGame.game_id.in_(game_ids),
                )
            ).all()
        }

    results = []
    for hot in hot_games:
        game = games_by_bgg_id.get(hot["bgg_id"])
        if game and game.status == "OWNED":
            status = "owned"
        elif game and game.id in queued_game_ids:
            status = "on_buy_list"
        else:
            status = "new"
        results.append({**hot, "status": status})

    return {"trending": results}


@router.get("/award-winners", dependencies=[Depends(require_admin_auth)])
async def list_award_winners(
    years: int = Query(6, ge=1, le=20, description="How many most-recent award years to include, per award"),
    db: Session = Depends(get_db),
):
    """
    Spiel des Jahres / Kennerspiel des Jahres / Kinderspiel des Jahres
    winners from recent years, annotated with whether each is already owned
    or already on the games-to-add list. Hand-curated (see
    services/award_winners.py) rather than scraped from BGG, since there's
    no API for "every winner of award X".
    """
    try:
        winners = await get_award_winners(db, years=years)
    except Exception as e:
        logger.error(f"Error computing award winners: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve award winners")

    return {"award_winners": winners}


@router.post("/suggest", dependencies=[Depends(require_admin_auth)])
async def suggest_games(data: SuggestGamesRequest, db: Session = Depends(get_db)):
    """
    Ask Claude for games worth adding, grounded in this library's actual
    collection and gap analysis. Each suggestion is best-effort matched to a
    BGG ID via BGG search so the frontend can offer a one-click add; a
    suggestion with no confident match still gets a BGG search link.
    """
    try:
        suggestions = await generate_suggestions(db, count=data.count)
        return {"suggestions": suggestions}
    except SuggestionServiceError as e:
        logger.warning(f"Suggestion request unavailable: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating game suggestions: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate game suggestions")


# ------------------------------------------------------------------------------
# 'Games to Add' Management Endpoints
# ------------------------------------------------------------------------------


@router.get("/games", dependencies=[Depends(require_admin_auth)])
async def list_buy_list_games(
    db: Session = Depends(get_db),
    on_buy_list: Optional[bool] = Query(None, description="Filter by on_buy_list status"),
    sort_by: str = Query("rank", description="Sort field: rank, title, updated_at, gaps_filled"),
    sort_desc: bool = Query(False, description="Sort in descending order"),
):
    """
    Get all candidate games on the 'games to add' list, annotated with which
    library gaps (if any) each one would help fill. Supports filtering and sorting.
    """
    try:
        gaps = compute_library_gaps(db)

        stmt = select(BuyListGame).options(joinedload(BuyListGame.game))

        # Default to active entries only; an explicit on_buy_list param overrides that.
        stmt = stmt.where(BuyListGame.on_buy_list == (True if on_buy_list is None else on_buy_list))

        if sort_by == "rank":
            stmt = stmt.order_by(
                desc(BuyListGame.rank) if sort_desc else BuyListGame.rank.nullslast()
            )
        elif sort_by == "title":
            stmt = stmt.join(Game).order_by(
                desc(Game.title) if sort_desc else Game.title
            )
        elif sort_by == "updated_at":
            stmt = stmt.order_by(
                desc(BuyListGame.updated_at) if sort_desc else BuyListGame.updated_at
            )
        else:
            # gaps_filled (and any unrecognized value) - gap count isn't a column,
            # so fetch in a stable base order and sort in Python below.
            stmt = stmt.order_by(BuyListGame.rank.nullslast())

        buy_list_entries = db.execute(stmt).scalars().all()
        results = [build_buy_list_response(entry, gaps) for entry in buy_list_entries]

        if sort_by == "gaps_filled":
            results.sort(key=_gaps_filled_count, reverse=sort_desc)

        return {"total": len(results), "items": results}

    except Exception as e:
        logger.error(f"Error listing games to add: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve games to add")


@router.post("/games", dependencies=[Depends(require_admin_auth)])
async def add_to_buy_list(
    data: BuyListGameCreate, db: Session = Depends(get_db)
):
    """
    Add a candidate game to the 'games to add' list by BGG ID.
    If the game doesn't exist in the database, it will be imported from BoardGameGeek first.
    """
    try:
        # Import BGG service for auto-import
        from bgg_service import fetch_bgg_thing

        # Check if game with this BGG ID already exists
        game = db.execute(
            select(Game).where(Game.bgg_id == data.bgg_id)
        ).scalar_one_or_none()

        if not game:
            # Game doesn't exist - import from BGG using the game service for full data population
            logger.info(f"Game with BGG ID {data.bgg_id} not found, importing from BGG...")

            try:
                bgg_data = await fetch_bgg_thing(data.bgg_id)
            except Exception as e:
                logger.error(f"Failed to fetch from BGG: {e}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to import game from BGG ID {data.bgg_id}: {str(e)}"
                )

            # Use the game service so all derived fields (nz_designer, mana_meeple_category, etc.)
            # are populated the same way as the main import flow
            from services.game_service import GameService
            game_service = GameService(db)
            game, _ = game_service.create_or_update_from_bgg(bgg_id=data.bgg_id, bgg_data=bgg_data)
            # Override the default OWNED status — this game is being added to the buy list
            game.status = "BUY_LIST"
            db.flush()
            logger.info(f"Imported game '{game.title}' from BGG ID {data.bgg_id} for buy list")

        else:
            # Game exists - guard against silently demoting an owned game
            if game.status == "OWNED":
                raise HTTPException(
                    status_code=400,
                    detail=f"'{game.title}' is already in your owned collection. Remove it from the library first if you want to add it to the buy list."
                )
            elif game.status != "BUY_LIST":
                game.status = "BUY_LIST"
                logger.info(f"Updated game '{game.title}' status to BUY_LIST")

        # Check if already on buy list
        existing = db.execute(
            select(BuyListGame).where(BuyListGame.game_id == game.id)
        ).scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=400, detail="Game already on buy list"
            )

        # Create buy list entry
        buy_list_entry = BuyListGame(
            game_id=game.id,
            rank=data.rank,
            notes=data.notes,
            on_buy_list=True,
        )

        db.add(buy_list_entry)
        db.commit()
        db.refresh(buy_list_entry)

        # Accessing the game relationship will trigger lazy loading
        # No need to explicitly refresh it
        _ = buy_list_entry.game  # Access to ensure it's loaded

        logger.info(f"Added game '{game.title}' (BGG ID {data.bgg_id}) to buy list")

        return build_buy_list_response(buy_list_entry, compute_library_gaps(db))

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
    """Update a 'games to add' entry (rank, notes, on_buy_list)"""
    try:
        buy_list_entry = db.execute(
            select(BuyListGame).where(BuyListGame.id == buy_list_id)
        ).scalar_one_or_none()
        if not buy_list_entry:
            raise HTTPException(status_code=404, detail="Buy list entry not found")

        # Update fields
        if data.rank is not None:
            buy_list_entry.rank = data.rank
        if data.notes is not None:
            buy_list_entry.notes = data.notes
        if data.on_buy_list is not None:
            buy_list_entry.on_buy_list = data.on_buy_list

        buy_list_entry.updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(buy_list_entry)

        # Access game relationship to ensure it's loaded
        _ = buy_list_entry.game

        logger.info(f"Updated buy list entry {_sl(buy_list_id)}")

        return build_buy_list_response(buy_list_entry, compute_library_gaps(db))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating buy list game: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update buy list game")


@router.put("/reorder", dependencies=[Depends(require_admin_auth)])
async def reorder_buy_list(data: BuyListReorderRequest, db: Session = Depends(get_db)):
    """
    Re-rank 'games to add' entries to match a given display order: the Nth id
    in ordered_ids gets rank N (1-based). Used by the "Re-rank" action, which
    captures whatever order the list is currently sorted in (e.g. by gaps
    filled) and turns it into persisted priority numbers.
    """
    try:
        entries = db.execute(
            select(BuyListGame).where(BuyListGame.id.in_(data.ordered_ids))
        ).scalars().all()
        entries_by_id = {entry.id: entry for entry in entries}

        missing = [i for i in data.ordered_ids if i not in entries_by_id]
        if missing:
            raise HTTPException(
                status_code=404, detail=f"Buy list entries not found: {missing}"
            )

        now = datetime.now(timezone.utc)
        for position, entry_id in enumerate(data.ordered_ids, start=1):
            entry = entries_by_id[entry_id]
            entry.rank = position
            entry.updated_at = now

        db.commit()

        gaps = compute_library_gaps(db)
        stmt = (
            select(BuyListGame)
            .options(joinedload(BuyListGame.game))
            .where(BuyListGame.on_buy_list == True)  # noqa: E712
            .order_by(BuyListGame.rank.nullslast())
        )
        buy_list_entries = db.execute(stmt).scalars().all()
        results = [build_buy_list_response(entry, gaps) for entry in buy_list_entries]

        logger.info(f"Re-ranked {len(data.ordered_ids)} buy list entries")

        return {"total": len(results), "items": results}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error re-ranking buy list: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to re-rank buy list")


@router.delete("/games/{buy_list_id}", dependencies=[Depends(require_admin_auth)])
async def remove_from_buy_list(buy_list_id: int, db: Session = Depends(get_db)):
    """Remove a game from the 'games to add' list"""
    try:
        buy_list_entry = db.execute(
            select(BuyListGame).where(BuyListGame.id == buy_list_id)
        ).scalar_one_or_none()
        if not buy_list_entry:
            raise HTTPException(status_code=404, detail="Buy list entry not found")

        db.delete(buy_list_entry)
        db.commit()

        logger.info(f"Removed buy list entry {_sl(buy_list_id)}")

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
# HL Timaru Stock Signals
# ------------------------------------------------------------------------------


def _build_hl_signal_response(link: HLStockLink, game: Optional[Game]) -> Dict[str, Any]:
    return {
        "hl_internal_id": link.hl_internal_id,
        "hl_product_name": link.hl_product_name,
        "current_stock": link.hl_current_stock,
        "units_sold": link.hl_units_sold,
        "last_sale_date": link.hl_last_sale_date.isoformat() if link.hl_last_sale_date else None,
        "approx_revenue": float(link.hl_approx_revenue) if link.hl_approx_revenue is not None else None,
        "match_status": "linked" if game else "unmatched",
        "match_confidence": link.match_confidence,
        "linked_game": (
            {"id": game.id, "title": game.title, "status": game.status, "bgg_id": game.bgg_id}
            if game else None
        ),
    }


@router.get("/hl-signals", dependencies=[Depends(require_admin_auth)])
async def list_hl_stock_signals(db: Session = Depends(get_db)):
    """
    Board games selling well / sitting in stock at HL Timaru that aren't yet
    in this library - a demand signal for what to add. Reads live from HL's
    retail database, upserts hl_stock_links (fuzzy-matching any newly-seen
    product against this library's titles), and returns everything that
    isn't dismissed and isn't already owned or already on this buy list -
    those are already tracked, so resurfacing them here would be noise.
    """
    try:
        hl_items = fetch_hl_board_game_signals()
    except HLStockServiceError as e:
        logger.warning(f"HL stock-signal fetch unavailable: {e}")
        raise HTTPException(status_code=503, detail=str(e))

    now = datetime.now(timezone.utc)
    results = []

    try:
        for item in hl_items:
            link = db.execute(
                select(HLStockLink).where(HLStockLink.hl_internal_id == item["internal_id"])
            ).scalar_one_or_none()

            if link is None:
                game, score = find_best_title_match(db, item["name"])
                link = HLStockLink(
                    hl_internal_id=item["internal_id"],
                    hl_product_name=item["name"],
                    game_id=game.id if game else None,
                    match_confidence=score,
                    last_synced_at=now,
                )
                db.add(link)
            else:
                link.hl_product_name = item["name"]
                link.last_synced_at = now
                # Only re-attempt a match while still unlinked - once a staff
                # member confirms or dismisses a link, it's never re-resolved.
                if link.game_id is None and not link.dismissed:
                    game, score = find_best_title_match(db, item["name"])
                    link.game_id = game.id if game else None
                    link.match_confidence = score

            link.hl_current_stock = item.get("current_stock")
            link.hl_units_sold = item.get("units_sold")
            link.hl_last_sale_date = item.get("last_sale_date")
            link.hl_approx_revenue = item.get("approx_revenue")
            link.updated_at = now

            db.flush()

            if link.dismissed:
                continue

            game = db.get(Game, link.game_id) if link.game_id else None
            if game is not None and game.status == "OWNED":
                continue
            if game is not None:
                already_queued = db.execute(
                    select(BuyListGame).where(
                        BuyListGame.game_id == game.id, BuyListGame.on_buy_list == True  # noqa: E712
                    )
                ).scalar_one_or_none()
                if already_queued:
                    continue

            results.append(_build_hl_signal_response(link, game))

        db.commit()
    except Exception as e:
        logger.error(f"Error syncing HL stock signals: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to sync HL stock signals")

    results.sort(key=lambda r: r["units_sold"] or 0, reverse=True)
    return {"total": len(results), "items": results}


@router.post("/hl-signals/{hl_internal_id}/link", dependencies=[Depends(require_admin_auth)])
async def link_hl_stock_signal(
    hl_internal_id: int, data: HLStockSignalLinkRequest, db: Session = Depends(get_db)
):
    """Manually confirm or correct the link between an HL product and a game already in this library."""
    try:
        link = db.execute(
            select(HLStockLink).where(HLStockLink.hl_internal_id == hl_internal_id)
        ).scalar_one_or_none()
        if not link:
            raise HTTPException(
                status_code=404,
                detail="HL stock signal not found - run GET /hl-signals first to sync it",
            )

        game = db.execute(select(Game).where(Game.id == data.game_id)).scalar_one_or_none()
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")

        link.game_id = game.id
        link.match_confidence = None  # manual link, not a fuzzy-match score
        link.dismissed = False
        link.updated_at = datetime.now(timezone.utc)
        db.commit()

        logger.info(f"Linked HL product {_sl(hl_internal_id)} to game '{game.title}'")

        return {"hl_internal_id": hl_internal_id, "linked_game_id": game.id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error linking HL stock signal: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to link HL stock signal")


@router.post("/hl-signals/{hl_internal_id}/dismiss", dependencies=[Depends(require_admin_auth)])
async def dismiss_hl_stock_signal(hl_internal_id: int, db: Session = Depends(get_db)):
    """Mark an HL product as not a real board-game candidate (e.g. miscategorized at HL)."""
    try:
        link = db.execute(
            select(HLStockLink).where(HLStockLink.hl_internal_id == hl_internal_id)
        ).scalar_one_or_none()
        if not link:
            raise HTTPException(
                status_code=404,
                detail="HL stock signal not found - run GET /hl-signals first to sync it",
            )

        link.dismissed = True
        link.updated_at = datetime.now(timezone.utc)
        db.commit()

        logger.info(f"Dismissed HL stock signal {_sl(hl_internal_id)}")

        return {"hl_internal_id": hl_internal_id, "dismissed": True}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error dismissing HL stock signal: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to dismiss HL stock signal")


async def _bulk_import_buy_list_csv_task(text_content: str) -> None:
    """
    Background task: process the buy-list CSV, auto-importing any BGG IDs
    not already in the database. Each new row can require its own BGG fetch
    (with retry/backoff), so this must not run inline in the request cycle -
    a CSV of more than a handful of rows can easily exceed a platform request
    timeout.
    """
    # Local imports so patches on bgg_service.fetch_bgg_thing and
    # database.SessionLocal (swapped for a test session) are picked up at call time.
    from bgg_service import fetch_bgg_thing
    from database import SessionLocal

    db = SessionLocal()
    try:
        csv_reader = csv.DictReader(io.StringIO(text_content))
        if csv_reader.fieldnames:
            csv_reader.fieldnames = [field.strip() for field in csv_reader.fieldnames]

        added_count = 0
        updated_count = 0
        skipped_count = 0
        error_count = 0

        for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 to account for header
            try:
                # Get BGG ID
                bgg_id_str = row.get("bgg_id", "").strip()
                if not bgg_id_str:
                    skipped_count += 1
                    continue

                try:
                    bgg_id = int(bgg_id_str)
                except ValueError:
                    logger.warning(f"Row {row_num}: Invalid BGG ID '{_sl(bgg_id_str)}'")
                    error_count += 1
                    continue

                # Parse optional fields
                rank = None
                if row.get("rank", "").strip():
                    try:
                        rank = int(row["rank"])
                    except ValueError:
                        logger.warning(f"Row {row_num}: Invalid rank '{_sl(row['rank'])}'")

                notes = row.get("notes", "").strip() or None

                # Check if game exists in database
                game = db.execute(
                    select(Game).where(Game.bgg_id == bgg_id)
                ).scalar_one_or_none()

                if not game:
                    # Auto-import from BGG
                    logger.info(f"Row {row_num}: Importing BGG ID {bgg_id} from BoardGameGeek...")
                    try:
                        bgg_data = await fetch_bgg_thing(bgg_id)
                    except Exception as e:
                        logger.error(f"Row {row_num}: Failed to import BGG ID {bgg_id}: {e}")
                        error_count += 1
                        continue

                    game = Game(
                        title=bgg_data.get("title", "Unknown"),
                        categories=", ".join(bgg_data.get("categories", [])),
                        year=bgg_data.get("year"),
                        players_min=bgg_data.get("players_min"),
                        players_max=bgg_data.get("players_max"),
                        playtime_min=bgg_data.get("playtime_min"),
                        playtime_max=bgg_data.get("playtime_max"),
                        image=bgg_data.get("image"),  # Use main image only, Cloudinary handles resizing
                        bgg_id=bgg_id,
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
                        status="BUY_LIST",
                    )
                    db.add(game)
                    db.flush()
                else:
                    # Update status if needed
                    if game.status != "BUY_LIST":
                        game.status = "BUY_LIST"

                # Check if already on buy list
                existing = db.execute(
                    select(BuyListGame).where(BuyListGame.game_id == game.id)
                ).scalar_one_or_none()

                if existing:
                    # Update existing entry
                    if rank is not None:
                        existing.rank = rank
                    if notes:
                        existing.notes = notes
                    existing.updated_at = datetime.now(timezone.utc)
                    updated_count += 1
                else:
                    # Create new buy list entry
                    buy_list_entry = BuyListGame(
                        game_id=game.id,
                        rank=rank,
                        notes=notes,
                        on_buy_list=True,
                    )
                    db.add(buy_list_entry)
                    added_count += 1

            except Exception as e:
                logger.error(f"Row {row_num} import error: {e}")
                error_count += 1
                continue

        # Commit all changes
        db.commit()

        logger.info(
            f"Buy list bulk CSV import complete: {added_count} added, {updated_count} updated, "
            f"{skipped_count} skipped, {error_count} errors"
        )

    except Exception as e:
        logger.error(f"Error in buy list bulk CSV import: {e}")
        db.rollback()
    finally:
        db.close()


@router.post("/bulk-import-csv", dependencies=[Depends(require_admin_auth)])
async def bulk_import_buy_list_csv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    """
    Bulk import candidate games to the 'games to add' list from CSV file.

    Expected CSV columns: bgg_id, rank, notes
    - bgg_id: Required - BoardGameGeek ID
    - rank: Optional - Numeric rank/priority
    - notes: Optional - Curation notes (e.g. why this fills a gap)

    Games not in database will be auto-imported from BoardGameGeek. Runs in
    the background since new rows require a BGG fetch each - see
    _bulk_import_buy_list_csv_task. Check server logs for results.
    """
    try:
        # Read CSV file
        contents = await file.read()
        # Use utf-8-sig to handle BOM (Byte Order Mark) from Excel/Windows
        text_content = contents.decode("utf-8-sig")
        csv_reader = csv.DictReader(io.StringIO(text_content))

        # Strip whitespace from fieldnames and normalize them
        if csv_reader.fieldnames:
            csv_reader.fieldnames = [field.strip() for field in csv_reader.fieldnames]

        # Validate required column
        if not csv_reader.fieldnames or "bgg_id" not in csv_reader.fieldnames:
            raise HTTPException(
                status_code=400,
                detail=f"CSV must contain 'bgg_id' column. Found columns: {csv_reader.fieldnames}"
            )

        row_count = sum(1 for _ in csv_reader)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to parse buy list CSV: {e}")
        raise HTTPException(status_code=500, detail="Failed to import CSV - check file format")

    background_tasks.add_task(_bulk_import_buy_list_csv_task, text_content)

    return {
        "message": f"Started importing {row_count} row(s) from CSV in the background. Check server logs for results.",
        "count": row_count,
    }
