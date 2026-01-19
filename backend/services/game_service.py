# services/game_service.py
"""
Game service layer - handles all business logic for game operations.
Separates business logic from HTTP routing concerns.
"""
import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func, or_, and_, case, inspect, cast, String, delete
from sqlalchemy.orm import Session, selectinload

from models import Game
from exceptions import GameNotFoundError, ValidationError
from utils.helpers import parse_categories, categorize_game, game_to_dict
from config import API_BASE

logger = logging.getLogger(__name__)


class GameService:
    """Service for game-related business logic"""

    def __init__(self, db: Session):
        self.db = db

    def get_game_by_id(self, game_id: int) -> Optional[Game]:
        """
        Get a single game by ID.
        Phase 1 Performance: Eager load expansions and base_game to prevent N+1 queries.

        Args:
            game_id: The game's database ID

        Returns:
            Game object or None if not found
        """
        # Use select with eager loading instead of simple .get()
        result = self.db.execute(
            select(Game)
            .options(selectinload(Game.expansions), selectinload(Game.base_game))
            .where(Game.id == game_id)
        ).scalar_one_or_none()
        return result

    def get_game_by_bgg_id(self, bgg_id: int) -> Optional[Game]:
        """
        Get a game by BoardGameGeek ID.

        Args:
            bgg_id: The BoardGameGeek game ID

        Returns:
            Game object or None if not found
        """
        return self.db.execute(
            select(Game).where(Game.bgg_id == bgg_id)
        ).scalar_one_or_none()

    def get_all_games(self) -> List[Game]:
        """Get all games for admin view - only OWNED games, excluding buy list and wishlist"""
        return self.db.execute(
            select(Game)
            .where(or_(Game.status == "OWNED", Game.status.is_(None)))
            .options(selectinload(Game.sleeves))
        ).scalars().all()

    def get_filtered_games(
        self,
        search: Optional[str] = None,
        category: Optional[str] = None,
        designer: Optional[str] = None,
        nz_designer: Optional[bool] = None,
        players: Optional[int] = None,
        complexity_min: Optional[float] = None,
        complexity_max: Optional[float] = None,
        recently_added_days: Optional[int] = None,
        sort: str = "title_asc",
        page: int = 1,
        page_size: int = 24,
    ) -> Tuple[List[Game], int]:
        """
        Get filtered games with pagination.

        Sprint 12: Performance Optimization - Uses window function for count + pagination
        to eliminate duplicate queries and reduce DB round trips from 2 to 1.

        Args:
            search: Search query for title, designers, description
            category: Category filter
            designer: Designer name filter
            nz_designer: Filter by NZ designer flag
            players: Filter by player count
            complexity_min: Minimum complexity rating (1-5)
            complexity_max: Maximum complexity rating (1-5)
            recently_added_days: Filter games added within last N days
            sort: Sort order
            page: Page number (1-indexed)
            page_size: Items per page

        Returns:
            Tuple of (list of Game objects, total count)
        """
        # Sprint 12: Performance Optimization - Use window function for count + pagination
        # This eliminates the duplicate count query and reduces DB round trips from 2 to 1
        #
        # Strategy: Use a subquery to get IDs + total count, then fetch full objects
        # This works around the limitation that window functions don't work well with eager loading

        # Step 1: Build ID subquery with window function for total count
        # Remove eager loading options for the ID selection
        id_query = select(
            Game.id,
            func.count().over().label('total_count')
        ).where(
            or_(Game.status == "OWNED", Game.status.is_(None))
        ).where(
            ~and_(
                Game.is_expansion == True,
                Game.expansion_type == 'requires_base'
            )
        )

        # Apply all the same filters to id_query (this is the ONLY place filters are applied now)
        if search and search.strip():
            search_term = f"%{search.strip()}%"
            search_conditions = [Game.title.ilike(search_term)]
            if hasattr(Game, "designers"):
                search_conditions.append(cast(Game.designers, String).ilike(search_term))
            if hasattr(Game, "description"):
                search_conditions.append(Game.description.ilike(search_term))
            id_query = id_query.where(or_(*search_conditions))

        if designer and designer.strip():
            designer_filter = f"%{designer.strip()}%"
            if hasattr(Game, "designers"):
                id_query = id_query.where(cast(Game.designers, String).ilike(designer_filter))

        if nz_designer is not None:
            id_query = id_query.where(Game.nz_designer == nz_designer)

        if players is not None:
            from sqlalchemy import alias
            Expansion = alias(Game.__table__, name="expansion")
            expansion_subquery = (
                select(Expansion.c.base_game_id)
                .where(Expansion.c.base_game_id.isnot(None))
                .where(
                    or_(
                        Expansion.c.modifies_players_min.is_(None),
                        Expansion.c.modifies_players_min <= players,
                    )
                )
                .where(
                    or_(
                        Expansion.c.modifies_players_max.is_(None),
                        Expansion.c.modifies_players_max >= players,
                    )
                )
            )
            id_query = id_query.where(
                or_(
                    and_(
                        or_(
                            Game.players_min.is_(None), Game.players_min <= players
                        ),
                        or_(
                            Game.players_max.is_(None), Game.players_max >= players
                        ),
                    ),
                    Game.id.in_(expansion_subquery),
                )
            )

        if complexity_min is not None or complexity_max is not None:
            if complexity_min is not None:
                id_query = id_query.where(
                    and_(
                        Game.complexity.isnot(None),
                        Game.complexity >= complexity_min
                    )
                )
            if complexity_max is not None:
                id_query = id_query.where(
                    and_(
                        Game.complexity.isnot(None),
                        Game.complexity <= complexity_max
                    )
                )

        if recently_added_days is not None:
            cutoff_date = datetime.now(timezone.utc) - timedelta(
                days=recently_added_days
            )
            if hasattr(Game, "date_added"):
                id_query = id_query.where(Game.date_added >= cutoff_date)

        if category and category != "all":
            if category == "uncategorized":
                id_query = id_query.where(Game.mana_meeple_category.is_(None))
            else:
                id_query = id_query.where(Game.mana_meeple_category == category)

        # Apply sorting to ID query
        id_query = self._apply_sorting(id_query, sort)

        # Save the base query before pagination for potential count fallback
        base_id_query = id_query

        # Apply pagination to ID query
        offset = (page - 1) * page_size
        id_query_paginated = id_query.offset(offset).limit(page_size)

        # Execute ID query to get IDs + total count (SINGLE DATABASE ROUND TRIP)
        id_results = self.db.execute(id_query_paginated).all()

        # Extract total count and game IDs
        if id_results:
            total = id_results[0][1]  # total_count from window function
            game_ids = [row[0] for row in id_results]

            # Step 2: Fetch full Game objects with eager loading for these specific IDs
            # This preserves the expansion loading behavior
            games = (
                self.db.execute(
                    select(Game)
                    .options(selectinload(Game.expansions))
                    .where(Game.id.in_(game_ids))
                )
                .scalars()
                .all()
            )

            # Preserve the original sort order from id_query
            # (in_ doesn't guarantee order, so we need to re-sort)
            id_order = {id_: idx for idx, id_ in enumerate(game_ids)}
            games = sorted(games, key=lambda g: id_order[g.id])
        else:
            # Edge case: Page beyond available data
            # Window function returned no rows, so we need to get count separately
            # This is rare (only when requesting page beyond last page)
            games = []

            # Execute count query using the base query (before pagination)
            # Replace the select columns with just a count
            count_query = select(func.count()).select_from(base_id_query.alias())
            total = self.db.execute(count_query).scalar() or 0

        # DEBUG LOGGING: Track pagination issues
        import logging
        logger = logging.getLogger(__name__)
        actual_count = len(games)
        logger.info(
            f"Pagination DEBUG - Category: {category}, Page: {page}, "
            f"PageSize: {page_size}, Offset: {offset}, "
            f"Expected: {min(page_size, total - offset)}, "
            f"Actual returned: {actual_count}, Total count: {total}"
        )

        # Additional logging for suspicious cases
        if actual_count < page_size and offset + actual_count < total:
            logger.warning(
                f"PAGINATION MISMATCH - Returned {actual_count} items but expected "
                f"{min(page_size, total - offset)} (total: {total}, offset: {offset})"
            )

        return games, total

    def _apply_sorting(self, query, sort: str):
        """
        Apply sorting to query based on sort parameter.

        CRITICAL: Always include secondary/tertiary sort (Title, then ID) to ensure
        stable pagination. Without this, games with duplicate sort values (same year,
        rating, etc.) can appear on multiple pages, causing items to be filtered as
        duplicates on the frontend and resulting in incomplete pagination (e.g., "200 of 221").

        Sort order pattern: [Primary Field] → Title → ID
        This gives users alphabetical grouping within each primary value, with ID
        ensuring uniqueness for stable pagination.
        """
        if sort == "title_desc":
            return query.order_by(Game.title.desc(), Game.id.asc())
        elif sort == "year_desc":
            return query.order_by(Game.year.desc().nulls_last(), Game.title.asc(), Game.id.asc())
        elif sort == "year_asc":
            return query.order_by(Game.year.asc().nulls_last(), Game.title.asc(), Game.id.asc())
        elif sort == "date_added_desc":
            if hasattr(Game, "date_added"):
                return query.order_by(Game.date_added.desc().nulls_last(), Game.title.asc(), Game.id.asc())
            return query.order_by(Game.title.asc(), Game.id.asc())
        elif sort == "date_added_asc":
            if hasattr(Game, "date_added"):
                return query.order_by(Game.date_added.asc().nulls_last(), Game.title.asc(), Game.id.asc())
            return query.order_by(Game.title.asc(), Game.id.asc())
        elif sort == "rating_desc":
            if hasattr(Game, "average_rating"):
                return query.order_by(Game.average_rating.desc().nulls_last(), Game.title.asc(), Game.id.asc())
            return query.order_by(Game.title.asc(), Game.id.asc())
        elif sort == "rating_asc":
            if hasattr(Game, "average_rating"):
                return query.order_by(Game.average_rating.asc().nulls_last(), Game.title.asc(), Game.id.asc())
            return query.order_by(Game.title.asc(), Game.id.asc())
        elif sort == "time_asc":
            # SQLAlchemy 2.0: case() takes positional args, not a list
            avg_time = case(
                (
                    and_(
                        Game.playtime_min.isnot(None),
                        Game.playtime_max.isnot(None),
                    ),
                    (Game.playtime_min + Game.playtime_max) / 2,
                ),
                (Game.playtime_min.isnot(None), Game.playtime_min),
                (Game.playtime_max.isnot(None), Game.playtime_max),
                else_=999999,
            )
            return query.order_by(avg_time.asc(), Game.title.asc(), Game.id.asc())
        elif sort == "time_desc":
            # SQLAlchemy 2.0: case() takes positional args, not a list
            avg_time = case(
                (
                    and_(
                        Game.playtime_min.isnot(None),
                        Game.playtime_max.isnot(None),
                    ),
                    (Game.playtime_min + Game.playtime_max) / 2,
                ),
                (Game.playtime_min.isnot(None), Game.playtime_min),
                (Game.playtime_max.isnot(None), Game.playtime_max),
                else_=0,
            )
            return query.order_by(avg_time.desc(), Game.title.asc(), Game.id.asc())
        else:  # Default to title_asc
            return query.order_by(Game.title.asc(), Game.id.asc())

    def get_games_by_designer(self, designer_name: str) -> List[Game]:
        """
        Get all games by a specific designer.

        Args:
            designer_name: Name of the designer to search for

        Returns:
            List of Game objects
        """
        designer_filter = f"%{designer_name}%"
        # Only show OWNED games (or NULL status which defaults to OWNED)
        query = select(Game).where(or_(Game.status == "OWNED", Game.status.is_(None)))

        # Cast JSON to text for searching (works in both SQLite and PostgreSQL)
        if hasattr(Game, "designers"):
            query = query.where(cast(Game.designers, String).ilike(designer_filter))

        return self.db.execute(query).scalars().all()

    def create_game(self, game_data: Dict[str, Any]) -> Game:
        """
        Create a new game.

        Args:
            game_data: Dictionary containing game data

        Returns:
            Created Game object

        Raises:
            ValidationError: If game already exists or data is invalid
        """
        # Validate required fields
        title = game_data.get("title", "").strip()
        if not title:
            raise ValidationError("Title is required and cannot be empty")

        # Check if game already exists by BGG ID
        bgg_id = game_data.get("bgg_id")
        if bgg_id:
            existing = self.get_game_by_bgg_id(bgg_id)
            if existing:
                raise ValidationError("Game with this BGG ID already exists")

        # Validate category if provided
        mana_category = game_data.get("mana_meeple_category")
        if mana_category:
            valid_categories = ["COOP_ADVENTURE", "CORE_STRATEGY", "GATEWAY_STRATEGY", "KIDS_FAMILIES", "PARTY_ICEBREAKERS"]
            if mana_category not in valid_categories:
                raise ValidationError(f"Invalid category. Must be one of: {', '.join(valid_categories)}")

        # Create game with basic fields
        game = Game(
            title=title,
            categories=(
                ",".join(game_data.get("categories", []))
                if isinstance(game_data.get("categories"), list)
                else game_data.get("categories", "")
            ),
            year=game_data.get("year"),
            players_min=game_data.get("players_min"),
            players_max=game_data.get("players_max"),
            playtime_min=game_data.get("playtime_min"),
            playtime_max=game_data.get("playtime_max"),
            bgg_id=bgg_id,
            mana_meeple_category=mana_category,
            status=game_data.get("status", "OWNED"),  # Default to OWNED if not provided
            nz_designer=game_data.get("nz_designer", False),  # Include nz_designer flag
        )

        # Add enhanced fields if they exist in the model
        self._update_game_enhanced_fields(game, game_data)

        # Auto-categorize if no category provided
        if not game.mana_meeple_category and game.categories:
            categories = parse_categories(game.categories)
            game.mana_meeple_category = categorize_game(categories)

        self.db.add(game)
        self.db.commit()
        self.db.refresh(game)

        logger.info(f"Created game: {game.title} (ID: {game.id})")
        return game

    def update_game(self, game_id: int, game_data: Dict[str, Any]) -> Game:
        """
        Update an existing game.

        Args:
            game_id: ID of game to update
            game_data: Dictionary containing fields to update

        Returns:
            Updated Game object

        Raises:
            GameNotFoundError: If game doesn't exist
            ValidationError: If validation fails
        """
        game = self.get_game_by_id(game_id)
        if not game:
            raise GameNotFoundError(f"Game {game_id} not found")

        # Validate category if being updated
        if "mana_meeple_category" in game_data:
            mana_category = game_data["mana_meeple_category"]
            if mana_category:  # Allow None/empty to clear category
                valid_categories = ["COOP_ADVENTURE", "CORE_STRATEGY", "GATEWAY_STRATEGY", "KIDS_FAMILIES", "PARTY_ICEBREAKERS"]
                if mana_category not in valid_categories:
                    raise ValidationError(f"Invalid category. Must be one of: {', '.join(valid_categories)}")

        # Validate title if being updated
        if "title" in game_data:
            title = game_data["title"].strip() if game_data["title"] else ""
            if not title:
                raise ValidationError("Title is required and cannot be empty")
            game_data["title"] = title

        # Convert date_added string to datetime object if needed
        if "date_added" in game_data and game_data["date_added"] is not None:
            if isinstance(game_data["date_added"], str):
                try:
                    # Handle ISO format with or without 'Z' suffix
                    date_str = game_data["date_added"].replace('Z', '+00:00')
                    game_data["date_added"] = datetime.fromisoformat(date_str)
                except (ValueError, TypeError) as e:
                    raise ValidationError(f"Invalid date_added format: {e}")

        # Update allowed fields
        updatable_fields = [
            "title",
            "year",
            "description",
            "mana_meeple_category",
            "players_min",
            "players_max",
            "playtime_min",
            "playtime_max",
            "min_age",
            "nz_designer",
            # Ownership fields
            "status",
            "date_added",
            # Expansion fields
            "is_expansion",
            "expansion_type",
            "base_game_id",
            "modifies_players_min",
            "modifies_players_max",
        ]

        for field in updatable_fields:
            if field in game_data:
                # Check if field exists in model before setting
                if field == "description" and not hasattr(game, "description"):
                    continue
                if field == "min_age" and not hasattr(game, "min_age"):
                    continue
                setattr(game, field, game_data[field])

        self.db.commit()
        self.db.refresh(game)

        logger.info(f"Updated game: {game.title} (ID: {game.id})")
        return game

    def delete_game(self, game_id: int) -> str:
        """
        Delete a game.

        Args:
            game_id: ID of game to delete

        Returns:
            Name of deleted game

        Raises:
            GameNotFoundError: If game doesn't exist
        """
        game = self.get_game_by_id(game_id)
        if not game:
            raise GameNotFoundError(f"Game {game_id} not found")

        game_title = game.title
        self.db.delete(game)
        self.db.commit()

        logger.info(f"Deleted game: {game_title} (ID: {game_id})")
        return game_title

    def update_game_from_bgg_data(
        self, game: Game, bgg_data: Dict[str, Any], commit: bool = True
    ) -> None:
        """
        Update a Game model instance with BGG data.
        Single source of truth for all BGG data mapping.
        Used by: import endpoints, bulk operations, and background tasks.

        Args:
            game: Game object to update
            bgg_data: Dictionary containing BGG data
            commit: Whether to commit changes to database (default True)
        """
        # Update basic fields
        game.title = bgg_data.get("title", game.title)
        game.categories = ", ".join(bgg_data.get("categories", []))
        game.year = bgg_data.get("year", game.year)
        game.players_min = bgg_data.get("players_min", game.players_min)
        game.players_max = bgg_data.get("players_max", game.players_max)
        game.playtime_min = bgg_data.get("playtime_min", game.playtime_min)
        game.playtime_max = bgg_data.get("playtime_max", game.playtime_max)

        # Update enhanced fields (description, designers, publishers, etc.)
        self._update_game_enhanced_fields(game, bgg_data)

        # DISABLED: Pre-generating Cloudinary URLs causes 404s because images aren't uploaded yet
        # The image proxy endpoint will handle Cloudinary upload on first request
        # self._pre_generate_cloudinary_url(game)

        # Auto-link to base game if this is an expansion
        self._auto_link_expansion(game, bgg_data)

        # Re-categorize based on BGG categories (unless manually categorized)
        categories = parse_categories(game.categories)
        game.mana_meeple_category = categorize_game(categories)

        # Add to session
        self.db.add(game)

        # Commit if requested
        if commit:
            self.db.commit()
            self.db.refresh(game)

        # Save sleeve data (requires game.id, so must be after initial commit)
        self._save_sleeve_data(game, bgg_data)

        # Final commit for sleeve data if needed
        if commit:
            self.db.commit()

    def _auto_link_expansion(self, game: Game, bgg_data: Dict[str, Any]) -> None:
        """
        Auto-link expansion to base game if the base game exists in database.

        Args:
            game: Game object to link
            bgg_data: BGG data containing base_game_bgg_id if available
        """
        # Only process if this is an expansion
        if not bgg_data.get("is_expansion", False):
            return

        base_game_bgg_id = bgg_data.get("base_game_bgg_id")
        if not base_game_bgg_id:
            logger.info(f"Expansion {game.title} has no base game BGG ID in data")
            return

        # Try to find base game in database
        base_game = self.get_game_by_bgg_id(base_game_bgg_id)
        if base_game:
            game.base_game_id = base_game.id
            logger.info(
                f"Auto-linked expansion '{game.title}' to base game '{base_game.title}'"
            )
        else:
            logger.info(
                f"Base game BGG ID {base_game_bgg_id} not found in database for expansion '{game.title}'"
            )

    def _update_game_enhanced_fields(
        self, game: Game, data: Dict[str, Any]
    ) -> None:
        """
        Update enhanced fields on a game if they exist in the model.
        Handles both game creation and BGG import data.

        Args:
            game: Game object to update
            data: Dictionary containing field data
        """
        enhanced_fields = {
            "description": "description",
            "designers": "designers",
            "publishers": "publishers",
            "mechanics": "mechanics",
            "artists": "artists",
            "average_rating": "average_rating",
            "complexity": "complexity",
            "bgg_rank": "bgg_rank",
            "users_rated": "users_rated",
            "min_age": "min_age",
            "is_cooperative": "is_cooperative",
            "game_type": "game_type",
            "image": "image",  # Use main image only, Cloudinary handles resizing
            # Expansion fields
            "is_expansion": "is_expansion",
            "expansion_type": "expansion_type",
            "modifies_players_min": "modifies_players_min",
            "modifies_players_max": "modifies_players_max",
        }

        for game_field, data_key in enhanced_fields.items():
            if hasattr(game, game_field) and data_key in data:
                setattr(game, game_field, data.get(data_key))

    def _determine_optimal_bgg_image_quality(self, game: Game) -> str:
        """
        Determine optimal BGG image quality based on game popularity.
        Smart quality selection reduces failed image requests.

        Quality Tiers:
        - _original: Very popular games (likely to have high-res images)
        - _d (detail): Popular games
        - _md (medium): Less popular games
        - _mt (medium-thumb): Unpopular/obscure games

        Args:
            game: Game object with metadata (users_rated, bgg_rank)

        Returns:
            Quality suffix ('original', 'detail', 'medium', 'medium-thumb')
        """
        users_rated = getattr(game, "users_rated", 0) or 0
        bgg_rank = getattr(game, "bgg_rank", None)

        # Very popular games: top 1000 or 10k+ ratings → _original
        if (bgg_rank and bgg_rank <= 1000) or users_rated >= 10000:
            return "original"

        # Popular games: top 5000 or 5k+ ratings → _d (detail)
        elif (bgg_rank and bgg_rank <= 5000) or users_rated >= 5000:
            return "detail"

        # Moderate popularity: 1k+ ratings → _md (medium)
        elif users_rated >= 1000:
            return "medium"

        # Less popular/new games → _mt (medium-thumb)
        # This has highest success rate for obscure games
        else:
            return "medium-thumb"

    def _pre_generate_cloudinary_url(self, game: Game) -> None:
        """
        Pre-generate Cloudinary URL for a game's image.
        Caches the URL in the database to eliminate redirect overhead.

        Uses smart quality selection based on game popularity to reduce
        failed image requests and improve cache hit rates.

        Performance Impact:
        - Eliminates 302 redirect (50-150ms per image)
        - Reduces server load on image proxy endpoint
        - Faster initial page loads
        - Reduces failed image requests for obscure games

        Args:
            game: Game object with image or thumbnail_url
        """
        # Only pre-generate if Cloudinary is enabled
        from services.cloudinary_service import cloudinary_service
        from config import CLOUDINARY_ENABLED

        if not CLOUDINARY_ENABLED:
            return

        # Use main image only - Cloudinary will handle all resizing
        source_url = game.image

        if not source_url:
            return

        # Check if it's a BGG image (Cloudinary only works with BGG images)
        if not source_url or 'cf.geekdo-images.com' not in source_url:
            return

        try:
            # Smart BGG image quality selection based on popularity
            optimal_quality = self._determine_optimal_bgg_image_quality(game)

            # Optimize source URL to use the best quality for this game
            if 'cf.geekdo-images.com' in source_url:
                # BGG uses NEW format with double underscores in path: __SIZE/
                # Example: https://cf.geekdo-images.com/HASH__d/pic123.jpg
                quality_map_new = {
                    'original': '__original/',
                    'detail': '__d/',
                    'medium': '__md/',
                    'medium-thumb': '__mt/',
                    'thumbnail': '__t/'
                }

                # OLD format (deprecated but still handle for legacy URLs)
                quality_map_old = {
                    'original': '_original.',
                    'detail': '_d.',
                    'medium': '_md.',
                    'medium-thumb': '_mt.',
                    'thumbnail': '_t.'
                }

                optimal_suffix_new = quality_map_new.get(optimal_quality, '__md/')
                optimal_suffix_old = quality_map_old.get(optimal_quality, '_md.')

                # Try new format first (most common)
                if '__' in source_url:
                    # Replace new format pattern: __SIZE/
                    import re
                    source_url = re.sub(r'__[a-z]+/', optimal_suffix_new, source_url)
                else:
                    # Fallback to old format: _SIZE.
                    for suffix in quality_map_old.values():
                        source_url = source_url.replace(suffix, optimal_suffix_old)

                logger.debug(f"Using {optimal_quality} quality for game {game.id} (users_rated: {getattr(game, 'users_rated', 0)}, rank: {getattr(game, 'bgg_rank', None)})")

            # Pre-generate optimized Cloudinary URL
            # Use medium size (800x800) as default for game cards
            cloudinary_url = cloudinary_service.generate_optimized_url(
                source_url,
                width=800,
                height=800,
                quality="auto:best",
                format="auto"  # Auto WebP/AVIF
            )

            # Cache in database
            if hasattr(game, "cloudinary_url"):
                game.cloudinary_url = cloudinary_url
                logger.debug(f"Pre-generated Cloudinary URL for game {game.id}: {cloudinary_url}")

        except Exception as e:
            logger.warning(f"Failed to pre-generate Cloudinary URL for game {game.id}: {e}")
            # Don't fail the import if Cloudinary URL generation fails

    def create_or_update_from_bgg(
        self, bgg_id: int, bgg_data: Dict[str, Any], force_update: bool = False
    ) -> Tuple[Game, bool]:
        """
        Create or update a game from BGG data.

        Args:
            bgg_id: BoardGameGeek game ID
            bgg_data: Dictionary containing BGG data
            force_update: Whether to update if game already exists

        Returns:
            Tuple of (Game object, was_cached: bool)
        """
        # Validate BGG ID (only check positive, no upper bound as BGG IDs grow over time)
        if bgg_id <= 0:
            raise ValidationError("BGG ID must be a positive integer")

        # Validate required fields in BGG data
        if not bgg_data.get("title"):
            raise ValidationError("BGG data must include a title")

        # Check if already exists
        existing = self.get_game_by_bgg_id(bgg_id)

        if existing and not force_update:
            return existing, True

        if existing:
            # Update existing game using consolidated method
            self.update_game_from_bgg_data(existing, bgg_data, commit=True)
            logger.info(
                f"Updated from BGG: {existing.title} (BGG ID: {bgg_id})"
            )
            return existing, True
        else:
            # Create new game with minimal data
            game = Game(
                title=bgg_data.get("title", ""),
                bgg_id=bgg_id,
                status="OWNED",  # Default status for BGG imports
            )

            # Use consolidated method to populate all BGG data
            self.update_game_from_bgg_data(game, bgg_data, commit=True)

            logger.info(f"Imported from BGG: {game.title} (BGG ID: {bgg_id})")
            return game, False

    def get_category_counts(self) -> Dict[str, int]:
        """
        Get counts for each category using conditional aggregation.
        Performance: Optimized to use single query with CASE statements (2 queries → 1 query).

        Returns:
            Dictionary mapping category keys to counts
        """
        from utils.helpers import CATEGORY_KEYS

        # PERFORMANCE OPTIMIZATION: Use conditional aggregation to get all counts in SINGLE query
        # This replaces 2 separate queries (total + group by) with 1 optimized query
        # Uses CASE statements to count each category conditionally

        # Build conditional count expressions for each category
        count_expressions = [
            func.count(Game.id).label("all"),  # Total count
        ]

        # Add conditional count for each category
        for category_key in CATEGORY_KEYS:
            count_expressions.append(
                func.count(case((Game.mana_meeple_category == category_key, 1))).label(category_key)
            )

        # Add conditional count for uncategorized (NULL or not in CATEGORY_KEYS)
        count_expressions.append(
            func.count(case((Game.mana_meeple_category.is_(None), 1))).label("uncategorized")
        )

        # Execute single query with all conditional counts
        result = self.db.execute(
            select(*count_expressions).where(
                or_(Game.status == "OWNED", Game.status.is_(None))
            ).where(
                ~and_(
                    Game.is_expansion == True,
                    Game.expansion_type == 'requires_base'
                )
            )
        ).one()

        # Convert result to dictionary
        counts = dict(result._mapping)

        return counts

    def _save_sleeve_data(self, game: Game, bgg_data: Dict[str, Any]) -> None:
        """
        Save sleeve data for a game from BGG data.

        Args:
            game: Game object to save sleeve data for
            bgg_data: BGG data containing sleeve_data field
        """
        from models import Sleeve

        # Get sleeve data from BGG response
        sleeve_data = bgg_data.get('sleeve_data')
        if not sleeve_data:
            logger.info(f"No sleeve data in BGG response for {game.title}")
            return

        # Update has_sleeves status
        game.has_sleeves = sleeve_data.get('status', 'not_found')

        # Delete existing sleeve records for this game
        stmt = delete(Sleeve).where(Sleeve.game_id == game.id)
        self.db.execute(stmt)

        # Save new sleeve records if found
        if sleeve_data.get('status') == 'found' and sleeve_data.get('card_types'):
            notes = sleeve_data.get('notes')
            for card_type in sleeve_data['card_types']:
                # Ensure quantity is never None (fallback to 0)
                quantity = card_type.get('quantity') or 0
                sleeve = Sleeve(
                    game_id=game.id,
                    card_name=card_type.get('name'),
                    width_mm=card_type['width_mm'],
                    height_mm=card_type['height_mm'],
                    quantity=quantity,
                    notes=notes
                )
                self.db.add(sleeve)

            logger.info(f"Saved {len(sleeve_data['card_types'])} sleeve types for {game.title}")
        else:
            logger.info(f"No sleeve data found for {game.title}")
