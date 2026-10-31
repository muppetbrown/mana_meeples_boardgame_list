from decimal import Decimal

from models import SleeveProduct
from services.sleeve_matching import find_matching_products, best_match_for_order, to_decimal


def _product(db, name, w, h):
    p = SleeveProduct(distributor="D", name=name, width_mm=w, height_mm=h,
                      sleeves_per_pack=100, price=Decimal("5.00"), in_stock=0)
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
    # One product fits both card sizes; 30 in stock
    p = _product(db_session, "Standard", 64.5, 90.0)
    p.in_stock = 30
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
    # 250 needed - 30 stock = 220 -> 3 packs (stock counted once)
    assert row["deficit"] == 220
    assert row["product"]["packs_to_buy"] == 3
    assert row["games_count"] == 2
    assert row["game_names"] == ["A", "B"]


def test_to_order_prefers_cheapest_order_given_existing_stock(db_session):
    """Same size: 300 of the 50-pack already held, so 5 more cheap packs beats 150-packs."""
    from services.sleeve_matching import compute_to_order_list
    big = SleeveProduct(distributor="D", name="150 pack", width_mm=59, height_mm=91,
                        sleeves_per_pack=150, price=Decimal("5.29"), in_stock=0)
    small = SleeveProduct(distributor="D", name="50 pack", width_mm=59, height_mm=91,
                          sleeves_per_pack=50, price=Decimal("1.96"), in_stock=300)
    db_session.add_all([big, small])
    db_session.commit()
    g = _game(db_session, "Monikers")
    _sleeve(db_session, g, 59, 91, 550)

    rows = compute_to_order_list(db_session)

    assert len(rows) == 1
    assert rows[0]["product"]["product_id"] == small.id
    assert rows[0]["product"]["packs_to_buy"] == 5
    assert [a["product_id"] for a in rows[0]["product"]["alternatives"]] == [big.id]


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


def test_fits_card_size_used_for_matching(db_session):
    # Sleeve is 59x91 but rated for cards up to 57x89
    p = _product(db_session, "Fits 57x89", 59, 91)
    p.card_width_mm = 57
    p.card_height_mm = 89
    db_session.commit()
    assert [m.id for m in find_matching_products(57, 89, db_session)] == [p.id]
    # The sleeve's own size no longer counts as the card size it fits
    assert find_matching_products(59, 91, db_session) == []
    from services.sleeve_matching import pick_best_product
    assert pick_best_product([p], 57, 89).id == p.id
    assert pick_best_product([p], 59, 91) is None
