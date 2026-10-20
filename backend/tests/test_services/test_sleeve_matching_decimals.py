from decimal import Decimal

from models import SleeveProduct
from services.sleeve_matching import find_matching_products, best_match_for_order, to_decimal


def _product(db, name, w, h):
    p = SleeveProduct(distributor="D", name=name, width_mm=w, height_mm=h,
                      sleeves_per_pack=100, price=Decimal("5.00"), in_stock=0, ordered=0)
    db.add(p)
    db.commit()
    return p


def test_decimal_dimensions_round_trip(db_session):
    p = _product(db_session, "Mini", 41.5, 63.5)
    db_session.refresh(p)
    assert p.width_mm == Decimal("41.50")
    assert p.height_mm == Decimal("63.50")


def test_matching_with_float_inputs(db_session):
    near = _product(db_session, "Near", 63.5, 89.5)
    _product(db_session, "TooWide", 65.0, 89.5)
    matches = find_matching_products(63.0, 88.9, db_session)
    assert [m.id for m in matches] == [near.id]
    assert best_match_for_order(63.0, 88.9, db_session).id == near.id


def test_to_decimal_handles_float_noise():
    assert to_decimal(0.1 + 0.2) == Decimal("0.30")


def _game(db, title):
    from models import Game
    g = Game(title=title, status="OWNED")
    db.add(g)
    db.commit()
    return g


def _sleeve(db, game, w, h, qty):
    from models import Sleeve
    db.add(Sleeve(game_id=game.id, width_mm=w, height_mm=h, quantity=qty))
    db.commit()


def test_to_order_merges_sizes_that_map_to_same_product(db_session):
    from services.sleeve_matching import compute_to_order_list
    # One product fits both card sizes; 30 in stock, 1 pack (100) on order
    p = _product(db_session, "Standard", 64.5, 90.0)
    p.in_stock = 30
    p.ordered = 1
    db_session.commit()
    a, b = _game(db_session, "A"), _game(db_session, "B")
    _sleeve(db_session, a, 63.8, 88.0, 150)
    _sleeve(db_session, b, 64.0, 89.0, 100)

    rows = compute_to_order_list(db_session)

    assert len(rows) == 1  # one product, not one row per size
    row = rows[0]
    assert row["product"]["product_id"] == p.id
    assert len(row["sizes"]) == 2
    assert row["total_needed"] == 250
    # 250 needed - 30 stock - 100 on order = 120 -> 2 packs (stock counted once)
    assert row["deficit"] == 120
    assert row["product"]["packs_to_buy"] == 2
    assert row["games_count"] == 2
    assert row["game_names"] == ["A", "B"]


def test_to_order_keeps_unmatched_sizes_separate(db_session):
    from services.sleeve_matching import compute_to_order_list
    g = _game(db_session, "Odd")
    _sleeve(db_session, g, 10.0, 10.0, 5)
    _sleeve(db_session, g, 20.0, 20.0, 7)

    rows = compute_to_order_list(db_session)

    assert len(rows) == 2
    assert all(r["product"] is None for r in rows)
    assert sorted(r["deficit"] for r in rows) == [5, 7]


def test_exact_size_match_59x91(db_session):
    exact = _product(db_session, "Exact", 59, 91)
    assert [m.id for m in find_matching_products(59, 91, db_session)] == [exact.id]
    from services.sleeve_matching import pick_best_product
    assert pick_best_product([exact], 59, 91).id == exact.id
