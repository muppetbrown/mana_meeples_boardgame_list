from models import Game
from services.hl_stock_matching import MATCH_CONFIDENCE_THRESHOLD, find_best_title_match


def test_exact_title_match(db_session):
    game = Game(title="Catan")
    db_session.add(game)
    db_session.commit()

    matched, score = find_best_title_match(db_session, "Catan")
    assert matched.id == game.id
    assert score == 100.0


def test_abbreviated_retail_name_above_threshold(db_session):
    game = Game(title="Azul: Summer Pavilion")
    db_session.add(game)
    db_session.commit()

    matched, score = find_best_title_match(db_session, "Azul Summer Pavilion")
    assert matched.id == game.id
    assert score >= MATCH_CONFIDENCE_THRESHOLD


def test_unrelated_name_returns_no_match(db_session):
    db_session.add(Game(title="Catan"))
    db_session.commit()

    matched, score = find_best_title_match(db_session, "Completely Unrelated Thing XYZ")
    assert matched is None
    assert score < MATCH_CONFIDENCE_THRESHOLD


def test_heavily_abbreviated_name_falls_below_threshold_as_unmatched(db_session):
    """Near-miss abbreviations (e.g. 'Euro Exp' for 'European Expansion')
    should surface as unmatched rather than be auto-linked to the wrong
    confidence - the score is still returned so the near-miss is visible."""
    db_session.add(Game(title="Wingspan: European Expansion"))
    db_session.commit()

    matched, score = find_best_title_match(db_session, "Wingspan Euro Exp")
    assert matched is None
    assert 0 < score < MATCH_CONFIDENCE_THRESHOLD


def test_empty_library_returns_no_match(db_session):
    matched, score = find_best_title_match(db_session, "Anything")
    assert matched is None
    assert score == 0.0


def test_picks_best_match_among_several_games(db_session):
    best = Game(title="Wingspan: European Expansion")
    decoy = Game(title="Catan")
    db_session.add_all([best, decoy])
    db_session.commit()

    matched, _ = find_best_title_match(db_session, "Wingspan European Expansion")
    assert matched.id == best.id
