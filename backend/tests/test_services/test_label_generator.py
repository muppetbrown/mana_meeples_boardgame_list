"""Tests for LabelGenerator badge rendering."""
from services.label_generator import LabelGenerator


def _game(**overrides):
    game = {
        'id': 1,
        'title': 'Test Game',
        'players_min': 2,
        'players_max': 4,
        'game_type': 'Strategy',
        'is_cooperative': False,
        'mana_meeple_category': 'GATEWAY_STRATEGY',
    }
    game.update(overrides)
    return game


def _pdf(game):
    return LabelGenerator().generate_pdf([game]).getvalue()


def test_pdf_generated_with_nz_badge():
    assert _pdf(_game(nz_designer=True)).startswith(b'%PDF')


def test_nz_badge_without_game_type():
    assert _pdf(_game(nz_designer=True, game_type=None)).startswith(b'%PDF')
