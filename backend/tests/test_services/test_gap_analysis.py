"""
Tests for backend/services/gap_analysis.py — category balance and
player-count coverage analysis used by the 'games to add' dashboard.
"""

from models import Game
from services.gap_analysis import (
    compute_category_gaps,
    compute_complexity_gaps,
    compute_library_gaps,
    compute_player_count_gaps,
    compute_playtime_gaps,
    annotate_candidate,
    games_needed_values,
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
        assert by_category["CORE_STRATEGY"]["games_needed"] == 0
        for key in CATEGORY_KEYS:
            if key != "CORE_STRATEGY":
                assert by_category[key]["is_gap"] is True
                # threshold is 10% of 10 games = 1 game; each gapped category has 0
                assert by_category[key]["games_needed"] == 1

    def test_games_needed_scales_with_collection_size(self, db_session):
        # 20 games all CORE_STRATEGY -> threshold is 10% of 20 = 2 games
        for i in range(20):
            _add_owned_game(db_session, title=f"Game {i}", bgg_id=i, mana_meeple_category="CORE_STRATEGY")
        db_session.commit()

        by_category = {g["category"]: g for g in compute_category_gaps(db_session)}
        assert by_category["KIDS_FAMILIES"]["games_needed"] == 2

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


class TestComputeComplexityGaps:
    def test_empty_collection_flags_nothing(self, db_session):
        gaps = compute_complexity_gaps(db_session)
        assert len(gaps) == 3  # light, medium, heavy
        assert all(g["is_gap"] is False for g in gaps)
        assert all(g["count"] == 0 for g in gaps)

    def test_games_bucketed_by_weight(self, db_session):
        _add_owned_game(db_session, title="Light", bgg_id=1, complexity=1.2)
        _add_owned_game(db_session, title="Medium", bgg_id=2, complexity=2.5)
        _add_owned_game(db_session, title="Heavy", bgg_id=3, complexity=4.0)
        _add_owned_game(db_session, title="Boundary low", bgg_id=4, complexity=2.0)
        _add_owned_game(db_session, title="Boundary high", bgg_id=5, complexity=3.0)
        db_session.commit()

        by_band = {g["complexity_band"]: g for g in compute_complexity_gaps(db_session)}
        assert by_band["light"]["count"] == 1  # 1.2
        assert by_band["medium"]["count"] == 2  # 2.5 and the 2.0 boundary (medium starts at >=2.0)
        assert by_band["heavy"]["count"] == 2  # 4.0 and the 3.0 boundary (heavy starts at >=3.0)

    def test_underrepresented_band_is_flagged(self, db_session):
        # 10 games, all heavy -> light and medium are gaps
        for i in range(10):
            _add_owned_game(db_session, title=f"Game {i}", bgg_id=i, complexity=4.0)
        db_session.commit()

        by_band = {g["complexity_band"]: g for g in compute_complexity_gaps(db_session)}
        assert by_band["heavy"]["is_gap"] is False
        assert by_band["light"]["is_gap"] is True
        assert by_band["medium"]["is_gap"] is True

    def test_unrated_games_excluded_from_counts(self, db_session):
        _add_owned_game(db_session, title="Unrated", bgg_id=1, complexity=None)
        db_session.commit()

        gaps = compute_complexity_gaps(db_session)
        assert sum(g["count"] for g in gaps) == 0


class TestComputePlaytimeGaps:
    def test_empty_collection_flags_nothing(self, db_session):
        gaps = compute_playtime_gaps(db_session)
        assert len(gaps) == 4  # quick, standard, long, epic
        assert all(g["is_gap"] is False for g in gaps)
        assert all(g["count"] == 0 for g in gaps)

    def test_games_bucketed_by_playtime(self, db_session):
        _add_owned_game(db_session, title="Quick", bgg_id=1, playtime_min=15, playtime_max=15)
        _add_owned_game(db_session, title="Standard", bgg_id=2, playtime_min=30, playtime_max=45)
        _add_owned_game(db_session, title="Long", bgg_id=3, playtime_min=60, playtime_max=90)
        _add_owned_game(db_session, title="Epic", bgg_id=4, playtime_min=120, playtime_max=240)
        db_session.commit()

        by_band = {g["playtime_band"]: g for g in compute_playtime_gaps(db_session)}
        assert by_band["quick"]["count"] == 1
        assert by_band["standard"]["count"] == 1
        assert by_band["long"]["count"] == 1
        assert by_band["epic"]["count"] == 1

    def test_uses_max_over_min_when_both_present(self, db_session):
        # A 20-90 min game should land in "long" (uses the upper bound), not "quick"
        _add_owned_game(db_session, title="Variable length", bgg_id=1, playtime_min=20, playtime_max=90)
        db_session.commit()

        by_band = {g["playtime_band"]: g for g in compute_playtime_gaps(db_session)}
        assert by_band["long"]["count"] == 1
        assert by_band["quick"]["count"] == 0

    def test_falls_back_to_min_when_max_missing(self, db_session):
        _add_owned_game(db_session, title="No max", bgg_id=1, playtime_min=25, playtime_max=None)
        db_session.commit()

        by_band = {g["playtime_band"]: g for g in compute_playtime_gaps(db_session)}
        assert by_band["quick"]["count"] == 1

    def test_underrepresented_band_is_flagged(self, db_session):
        # 10 quick games -> standard, long, epic are all gaps
        for i in range(10):
            _add_owned_game(db_session, title=f"Game {i}", bgg_id=i, playtime_min=15, playtime_max=15)
        db_session.commit()

        by_band = {g["playtime_band"]: g for g in compute_playtime_gaps(db_session)}
        assert by_band["quick"]["is_gap"] is False
        assert by_band["epic"]["is_gap"] is True

    def test_games_with_no_playtime_data_excluded(self, db_session):
        _add_owned_game(db_session, title="No data", bgg_id=1, playtime_min=None, playtime_max=None)
        db_session.commit()

        gaps = compute_playtime_gaps(db_session)
        assert sum(g["count"] for g in gaps) == 0


class TestAnnotateCandidate:
    def test_flags_category_and_player_count_matches(self):
        game = Game(
            title="Candidate", mana_meeple_category="PARTY_ICEBREAKERS",
            players_min=7, players_max=12, complexity=1.5,
            playtime_min=20, playtime_max=20,
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
            "complexity_gaps": [
                {"complexity_band": "light", "count": 0, "pct_of_collection": 0.0, "is_gap": True},
                {"complexity_band": "heavy", "count": 10, "pct_of_collection": 100.0, "is_gap": False},
            ],
            "playtime_gaps": [
                {"playtime_band": "quick", "count": 0, "pct_of_collection": 0.0, "is_gap": True},
                {"playtime_band": "epic", "count": 10, "pct_of_collection": 100.0, "is_gap": False},
            ],
        }

        result = annotate_candidate(game, gaps)
        assert result["category_is_gap"] is True
        assert set(result["matching_player_count_gaps"]) == {"7", "9+"}
        assert result["complexity_is_gap"] is True
        assert result["playtime_is_gap"] is True
        assert games_needed_values(result) != []

    def test_no_matches_when_candidate_fills_no_gap(self):
        game = Game(
            title="Candidate", mana_meeple_category="CORE_STRATEGY", players_min=2, players_max=4,
            complexity=2.5, playtime_min=45, playtime_max=45,
        )
        gaps = {
            "total_games": 10,
            "category_gaps": [
                {"category": "CORE_STRATEGY", "count": 10, "pct_of_collection": 100.0, "is_gap": False},
            ],
            "player_count_gaps": [
                {"player_count": "9+", "games_supporting": 0, "pct_of_collection": 0.0, "is_gap": True},
            ],
            "complexity_gaps": [
                {"complexity_band": "medium", "count": 10, "pct_of_collection": 100.0, "is_gap": False},
            ],
            "playtime_gaps": [
                {"playtime_band": "standard", "count": 10, "pct_of_collection": 100.0, "is_gap": False},
            ],
        }

        result = annotate_candidate(game, gaps)
        assert result["category_is_gap"] is False
        assert result["matching_player_count_gaps"] == []
        assert result["complexity_is_gap"] is False
        assert result["playtime_is_gap"] is False

    def test_no_match_when_candidate_missing_complexity_or_playtime(self):
        game = Game(title="Candidate", mana_meeple_category="CORE_STRATEGY")
        gaps = {
            "total_games": 10,
            "category_gaps": [
                {"category": "CORE_STRATEGY", "count": 10, "pct_of_collection": 100.0, "is_gap": False},
            ],
            "player_count_gaps": [],
            "complexity_gaps": [
                {"complexity_band": "light", "count": 0, "pct_of_collection": 0.0, "is_gap": True},
            ],
            "playtime_gaps": [
                {"playtime_band": "quick", "count": 0, "pct_of_collection": 0.0, "is_gap": True},
            ],
        }

        result = annotate_candidate(game, gaps)
        assert result["complexity_is_gap"] is False
        assert result["playtime_is_gap"] is False


class TestAnnotateCandidateGamesNeeded:
    def test_games_needed_carried_through_from_gap_entries(self):
        game = Game(
            title="Candidate", mana_meeple_category="PARTY_ICEBREAKERS",
            players_min=9, players_max=12, complexity=1.5, playtime_min=20, playtime_max=20,
        )
        gaps = {
            "total_games": 10,
            "category_gaps": [
                {"category": "PARTY_ICEBREAKERS", "count": 0, "pct_of_collection": 0.0, "is_gap": True, "games_needed": 2},
            ],
            "player_count_gaps": [
                {"player_count": "9+", "games_supporting": 1, "pct_of_collection": 10.0, "is_gap": True, "games_needed": 1},
            ],
            "complexity_gaps": [
                {"complexity_band": "light", "count": 0, "pct_of_collection": 0.0, "is_gap": True, "games_needed": 3},
            ],
            "playtime_gaps": [
                {"playtime_band": "quick", "count": 5, "pct_of_collection": 50.0, "is_gap": False, "games_needed": 0},
            ],
        }

        result = annotate_candidate(game, gaps)
        assert result["category_games_needed"] == 2
        assert result["player_count_games_needed"] == {"9+": 1}
        assert result["complexity_games_needed"] == 3
        assert result["playtime_is_gap"] is False
        assert sorted(games_needed_values(result)) == [1, 2, 3]

    def test_games_needed_values_empty_when_nothing_matches(self):
        assert games_needed_values(None) == []
        assert games_needed_values({"category_is_gap": False, "complexity_is_gap": False, "playtime_is_gap": False}) == []


class TestComputeLibraryGaps:
    def test_full_payload_shape(self, db_session):
        _add_owned_game(
            db_session, title="Game", bgg_id=1, mana_meeple_category="CORE_STRATEGY",
            players_min=2, players_max=4, complexity=2.5, playtime_min=45, playtime_max=45,
        )
        db_session.commit()

        result = compute_library_gaps(db_session)
        assert result["total_games"] == 1
        assert len(result["category_gaps"]) == len(CATEGORY_KEYS)
        assert len(result["player_count_gaps"]) == 9
        assert len(result["complexity_gaps"]) == 3
        assert len(result["playtime_gaps"]) == 4
