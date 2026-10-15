"""
Tests for backend/services/gap_analysis.py — category balance and
player-count coverage analysis used by the 'games to add' dashboard.
"""

from models import Game
from services.gap_analysis import (
    compute_category_gaps,
    compute_library_gaps,
    compute_player_count_gaps,
    annotate_candidate,
)
from utils.helpers import CATEGORY_KEYS


def _add_owned_game(db_session, **kwargs):
    defaults = {"status": "OWNED", "bgg_id": None}
    defaults.update(kwargs)
    game = Game(**defaults)
    db_session.add(game)
    return game


class TestComputeCategoryGaps:
    def test_empty_collection_flags_nothing(self, db_session):
        gaps = compute_category_gaps(db_session)
        assert len(gaps) == len(CATEGORY_KEYS)
        assert all(g["is_gap"] is False for g in gaps)
        assert all(g["count"] == 0 for g in gaps)

    def test_even_split_flags_nothing(self, db_session):
        for i, category in enumerate(CATEGORY_KEYS):
            for j in range(4):
                _add_owned_game(db_session, title=f"{category}-{j}", bgg_id=i * 10 + j, mana_meeple_category=category)
        db_session.commit()

        gaps = compute_category_gaps(db_session)
        assert all(g["is_gap"] is False for g in gaps)

    def test_underrepresented_category_is_flagged(self, db_session):
        # 10 games all in CORE_STRATEGY; every other category has 0% share
        for i in range(10):
            _add_owned_game(db_session, title=f"Game {i}", bgg_id=i, mana_meeple_category="CORE_STRATEGY")
        db_session.commit()

        gaps = compute_category_gaps(db_session)
        by_category = {g["category"]: g for g in gaps}

        assert by_category["CORE_STRATEGY"]["count"] == 10
        assert by_category["CORE_STRATEGY"]["is_gap"] is False
        for key in CATEGORY_KEYS:
            if key != "CORE_STRATEGY":
                assert by_category[key]["is_gap"] is True

    def test_uncategorized_games_excluded_from_counts(self, db_session):
        _add_owned_game(db_session, title="Uncategorized", bgg_id=1, mana_meeple_category=None)
        db_session.commit()

        gaps = compute_category_gaps(db_session)
        assert sum(g["count"] for g in gaps) == 0

    def test_non_owned_games_excluded(self, db_session):
        _add_owned_game(db_session, title="Wishlist Game", bgg_id=1, mana_meeple_category="CORE_STRATEGY", status="WISHLIST")
        db_session.commit()

        gaps = compute_category_gaps(db_session)
        by_category = {g["category"]: g for g in gaps}
        assert by_category["CORE_STRATEGY"]["count"] == 0


class TestComputePlayerCountGaps:
    def test_empty_collection_flags_nothing(self, db_session):
        gaps = compute_player_count_gaps(db_session)
        assert len(gaps) == 9  # 1-8 plus "9+"
        assert all(g["is_gap"] is False for g in gaps)

    def test_game_supports_its_player_range(self, db_session):
        _add_owned_game(db_session, title="4-player", bgg_id=1, players_min=2, players_max=4)
        db_session.commit()

        gaps = {g["player_count"]: g for g in compute_player_count_gaps(db_session)}
        assert gaps["2"]["games_supporting"] == 1
        assert gaps["3"]["games_supporting"] == 1
        assert gaps["4"]["games_supporting"] == 1
        assert gaps["1"]["games_supporting"] == 0
        assert gaps["5"]["games_supporting"] == 0

    def test_unbounded_max_counts_as_supporting_large_groups(self, db_session):
        _add_owned_game(db_session, title="Party game", bgg_id=1, players_min=4, players_max=None)
        db_session.commit()

        gaps = {g["player_count"]: g for g in compute_player_count_gaps(db_session)}
        assert gaps["9+"]["games_supporting"] == 1

    def test_large_group_gap_is_flagged(self, db_session):
        # 10 games, all 2-4 players: nothing supports 7, 8, or 9+ players
        for i in range(10):
            _add_owned_game(db_session, title=f"Game {i}", bgg_id=i, players_min=2, players_max=4)
        db_session.commit()

        gaps = {g["player_count"]: g for g in compute_player_count_gaps(db_session)}
        assert gaps["9+"]["is_gap"] is True
        assert gaps["2"]["is_gap"] is False

    def test_game_with_no_players_min_never_counted(self, db_session):
        _add_owned_game(db_session, title="No player data", bgg_id=1, players_min=None, players_max=None)
        db_session.commit()

        gaps = compute_player_count_gaps(db_session)
        assert all(g["games_supporting"] == 0 for g in gaps)


class TestAnnotateCandidate:
    def test_flags_category_and_player_count_matches(self):
        game = Game(
            title="Candidate", mana_meeple_category="PARTY_ICEBREAKERS",
            players_min=7, players_max=12,
        )
        gaps = {
            "total_games": 10,
            "category_gaps": [
                {"category": "PARTY_ICEBREAKERS", "count": 0, "pct_of_collection": 0.0, "is_gap": True},
                {"category": "CORE_STRATEGY", "count": 10, "pct_of_collection": 100.0, "is_gap": False},
            ],
            "player_count_gaps": [
                {"player_count": "7", "games_supporting": 0, "pct_of_collection": 0.0, "is_gap": True},
                {"player_count": "9+", "games_supporting": 0, "pct_of_collection": 0.0, "is_gap": True},
            ],
        }

        result = annotate_candidate(game, gaps)
        assert result["category_is_gap"] is True
        assert set(result["matching_player_count_gaps"]) == {"7", "9+"}

    def test_no_matches_when_candidate_fills_no_gap(self):
        game = Game(title="Candidate", mana_meeple_category="CORE_STRATEGY", players_min=2, players_max=4)
        gaps = {
            "total_games": 10,
            "category_gaps": [
                {"category": "CORE_STRATEGY", "count": 10, "pct_of_collection": 100.0, "is_gap": False},
            ],
            "player_count_gaps": [
                {"player_count": "9+", "games_supporting": 0, "pct_of_collection": 0.0, "is_gap": True},
            ],
        }

        result = annotate_candidate(game, gaps)
        assert result["category_is_gap"] is False
        assert result["matching_player_count_gaps"] == []


class TestComputeLibraryGaps:
    def test_full_payload_shape(self, db_session):
        _add_owned_game(db_session, title="Game", bgg_id=1, mana_meeple_category="CORE_STRATEGY", players_min=2, players_max=4)
        db_session.commit()

        result = compute_library_gaps(db_session)
        assert result["total_games"] == 1
        assert len(result["category_gaps"]) == len(CATEGORY_KEYS)
        assert len(result["player_count_gaps"]) == 9
