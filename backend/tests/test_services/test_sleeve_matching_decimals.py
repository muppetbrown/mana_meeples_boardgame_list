from decimal import Decimal

from models import Sleeve, SleeveProduct
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
