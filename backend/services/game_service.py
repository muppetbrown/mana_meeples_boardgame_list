# services/game_service.py
"""
Game service layer - handles all business logic for game operations.
Separates business logic from HTTP routing concerns.
"""
import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta

from sqlalchemy import select, func, or_, and_, case
from sqlalchemy.orm import Session

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

        Args:
            game_id: The game's database ID

        Returns:
            Game object or None if not found
        """
        return self.db.get(Game, game_id)

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
        """Get all games (for admin view)"""
        return self.db.execute(select(Game)).scalars().all()

    def get_filtered_games(
        self,
        search: Optional[str] = None,
        category: Optional[str] = None,
        designer: Optional[str] = None,
        nz_designer: Optional[bool] = None,
        players: Optional[int] = None,
        recently_added_days: Optional[int] = None,
        sort: str = "title_asc",
        page: int = 1,
        page_size: int = 24,
    ) -> Tuple[List[Game], int]:
        """
        Get filtered games with pagination.

        Args:
            search: Search query for title, designers, description
            category: Category filter
            designer: Designer name filter
            nz_designer: Filter by NZ designer flag
            players: Filter by player count
            recently_added_days: Filter games added within last N days
            sort: Sort order
            page: Page number (1-indexed)
            page_size: Items per page

        Returns:
            Tuple of (list of Game objects, total count)
        """
        # Build base query - only show OWNED games for public view
        query = select(Game).where(Game.status == "OWNED")

        # Apply search filter - search across title, designers, and description
        if search and search.strip():
            search_term = f"%{search.strip()}%"
            search_conditions = [Game.title.ilike(search_term)]

            # Add designer search if the field exists
            if hasattr(Game, "designers"):
                search_conditions.append(Game.designers.ilike(search_term))

            # Add description search for keyword functionality
            if hasattr(Game, "description"):
                search_conditions.append(Game.description.ilike(search_term))

            query = query.where(or_(*search_conditions))

        # Apply designer filter
        if designer and designer.strip():
            designer_filter = f"%{designer.strip()}%"
            if hasattr(Game, "designers"):
                query = query.where(Game.designers.ilike(designer_filter))

        # Apply NZ designer filter
        if nz_designer is not None:
            query = query.where(Game.nz_designer == nz_designer)

        # Apply player count filter (including games with expansions that support the player count)
        if players is not None:
            from sqlalchemy import alias

            # Create alias for expansion subquery
            Expansion = alias(Game.__table__, name="expansion")

            # Subquery to find games with expansions that extend player count
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

            # Game matches if base player count OR has expansion that supports it
            query = query.where(
                or_(
                    # Base game player count
                    and_(
                        or_(
                            Game.players_min.is_(None), Game.players_min <= players
                        ),
                        or_(
                            Game.players_max.is_(None), Game.players_max >= players
                        ),
                    ),
                    # Has expansion that extends player count to requested amount
                    Game.id.in_(expansion_subquery),
                )
            )

        # Apply recently added filter
        if recently_added_days is not None:
            cutoff_date = datetime.utcnow() - timedelta(
                days=recently_added_days
            )
            if hasattr(Game, "date_added"):
                query = query.where(Game.date_added >= cutoff_date)

        # Apply category filter
        if category and category != "all":
            if category == "uncategorized":
                query = query.where(Game.mana_meeple_category.is_(None))
            else:
                query = query.where(Game.mana_meeple_category == category)

        # Apply sorting
        query = self._apply_sorting(query, sort)

        # Get total count before pagination
        total = self.db.execute(
            select(func.count()).select_from(query.subquery())
        ).scalar()

        # Apply pagination
        games = (
            self.db.execute(
                query.offset((page - 1) * page_size).limit(page_size)
            )
            .scalars()
            .all()
        )

        return games, total

    def _apply_sorting(self, query, sort: str):
        """Apply sorting to query based on sort parameter"""
        if sort == "title_desc":
            return query.order_by(Game.title.desc())
        elif sort == "year_desc":
            return query.order_by(Game.year.desc().nulls_last())
        elif sort == "year_asc":
            return query.order_by(Game.year.asc().nulls_last())
        elif sort == "date_added_desc":
            if hasattr(Game, "date_added"):
                return query.order_by(Game.date_added.desc().nulls_last())
            return query.order_by(Game.title.asc())
        elif sort == "date_added_asc":
            if hasattr(Game, "date_added"):
                return query.order_by(Game.date_added.asc().nulls_last())
            return query.order_by(Game.title.asc())
        elif sort == "rating_desc":
            if hasattr(Game, "average_rating"):
                return query.order_by(Game.average_rating.desc().nulls_last())
            return query.order_by(Game.title.asc())
        elif sort == "rating_asc":
            if hasattr(Game, "average_rating"):
                return query.order_by(Game.average_rating.asc().nulls_last())
            return query.order_by(Game.title.asc())
        elif sort == "time_asc":
            avg_time = case(
                [
                    (
                        and_(
                            Game.playtime_min.isnot(None),
                            Game.playtime_max.isnot(None),
                        ),
                        (Game.playtime_min + Game.playtime_max) / 2,
                    ),
                    (Game.playtime_min.isnot(None), Game.playtime_min),
                    (Game.playtime_max.isnot(None), Game.playtime_max),
                ],
                else_=999999,
            )
            return query.order_by(avg_time.asc())
        elif sort == "time_desc":
            avg_time = case(
                [
                    (
                        and_(
                            Game.playtime_min.isnot(None),
                            Game.playtime_max.isnot(None),
                        ),
                        (Game.playtime_min + Game.playtime_max) / 2,
                    ),
                    (Game.playtime_min.isnot(None), Game.playtime_min),
                    (Game.playtime_max.isnot(None), Game.playtime_max),
                ],
                else_=0,
            )
            return query.order_by(avg_time.desc())
        else:  # Default to title_asc
            return query.order_by(Game.title.asc())

    def get_games_by_designer(self, designer_name: str) -> List[Game]:
        """
        Get all games by a specific designer.

        Args:
            designer_name: Name of the designer to search for

        Returns:
            List of Game objects
        """
        designer_filter = f"%{designer_name}%"
        query = select(Game).where(Game.status == "OWNED")

        if hasattr(Game, "designers"):
            query = query.where(Game.designers.ilike(designer_filter))

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
        # Check if game already exists by BGG ID
        bgg_id = game_data.get("bgg_id")
        if bgg_id:
            existing = self.get_game_by_bgg_id(bgg_id)
            if existing:
                raise ValidationError("Game with this BGG ID already exists")

        # Create game with basic fields
        game = Game(
            title=game_data.get("title", ""),
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
            mana_meeple_category=game_data.get("mana_meeple_category"),
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
        """
        game = self.get_game_by_id(game_id)
        if not game:
            raise GameNotFoundError(f"Game {game_id} not found")

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
        self, game: Game, bgg_data: Dict[str, Any]
    ) -> None:
        """
        Update a Game model instance with BGG data.
        Consolidates logic used by both single import and bulk import.

        Args:
            game: Game object to update
            bgg_data: Dictionary containing BGG data
        """
        # Update basic fields
        game.title = bgg_data.get("title", game.title)
        game.categories = ", ".join(bgg_data.get("categories", []))
        game.year = bgg_data.get("year", game.year)
        game.players_min = bgg_data.get("players_min", game.players_min)
        game.players_max = bgg_data.get("players_max", game.players_max)
        game.playtime_min = bgg_data.get("playtime_min", game.playtime_min)
        game.playtime_max = bgg_data.get("playtime_max", game.playtime_max)

        # Update enhanced fields
        self._update_game_enhanced_fields(game, bgg_data)

        # Re-categorize based on BGG categories
        categories = parse_categories(game.categories)
        game.mana_meeple_category = categorize_game(categories)

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
            "image": "image",
            "thumbnail_url": "thumbnail",  # BGG uses 'thumbnail' key
            # Expansion fields
            "is_expansion": "is_expansion",
            "expansion_type": "expansion_type",
            "modifies_players_min": "modifies_players_min",
            "modifies_players_max": "modifies_players_max",
        }

        for game_field, data_key in enhanced_fields.items():
            if hasattr(game, game_field) and data_key in data:
                setattr(game, game_field, data.get(data_key))

        # Handle thumbnail_url special case where data might have 'thumbnail_url' instead of 'thumbnail'
        if hasattr(game, "thumbnail_url") and "thumbnail_url" in data:
            game.thumbnail_url = data.get("thumbnail_url")

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
        # Validate BGG ID
        if bgg_id <= 0 or bgg_id > 999999:
            raise ValidationError("BGG ID must be between 1 and 999999")

        # Check if already exists
        existing = self.get_game_by_bgg_id(bgg_id)

        if existing and not force_update:
            return existing, True

        if existing:
            # Update existing game
            self.update_game_from_bgg_data(existing, bgg_data)

            # Auto-link to base game if this is an expansion
            self._auto_link_expansion(existing, bgg_data)

            self.db.add(existing)
            self.db.commit()
            self.db.refresh(existing)
            logger.info(
                f"Updated from BGG: {existing.title} (BGG ID: {bgg_id})"
            )
            return existing, True
        else:
            # Create new game
            categories_str = ", ".join(bgg_data.get("categories", []))
            categories = parse_categories(categories_str)

            game = Game(
                title=bgg_data.get("title", ""),
                categories=categories_str,
                year=bgg_data.get("year"),
                players_min=bgg_data.get("players_min"),
                players_max=bgg_data.get("players_max"),
                playtime_min=bgg_data.get("playtime_min"),
                playtime_max=bgg_data.get("playtime_max"),
                bgg_id=bgg_id,
                mana_meeple_category=categorize_game(categories),
            )

            # Add enhanced fields
            self._update_game_enhanced_fields(game, bgg_data)

            # Auto-link to base game if this is an expansion
            self._auto_link_expansion(game, bgg_data)

            self.db.add(game)
            self.db.commit()
            self.db.refresh(game)

            logger.info(f"Imported from BGG: {game.title} (BGG ID: {bgg_id})")
            return game, False

    def get_category_counts(self) -> Dict[str, int]:
        """
        Get counts for each category.

        Returns:
            Dictionary mapping category keys to counts
        """
        from utils.helpers import calculate_category_counts

        # Only select the columns we need - filter to OWNED games only
        games = self.db.execute(
            select(Game.id, Game.mana_meeple_category).where(Game.status == "OWNED")
        ).all()

        return calculate_category_counts(games)
