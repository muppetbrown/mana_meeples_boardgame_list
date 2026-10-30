# tests/test_services/test_sleeve_distro.py
"""Tests for services/sleeve_distro.py and distributor-stock-aware to-order ranking."""
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from models import Game, Sleeve, SleeveProduct, SleeveProductDistroLink
from services import sleeve_distro
from services.hl_stock_service import HLStockServiceError
from services.sleeve_distro import parse_pack_size, parse_size_mm, product_availability, stock_state, unlisted_sleeves
from services.sleeve_matching import compute_to_order_list


def _row(distributor, code, name, qty=None, cost=5.0):
    return {
        "distributor": distributor, "distro_code": code, "name": name,
        "cost_price_ex_gst": cost, "qty_available": qty,
        "qty_updated_at": datetime(2026, 10, 1, tzinfo=timezone.utc),
        "hl_internal_id": None, "hl_stock": None,
    }


class TestParsing:
    @pytest.mark.parametrize("name,code,expected", [
        ("Sleeve Kings Mini American (41mm x 63mm) (55 Sleeves per Pack)", "", (41.0, 63.0)),
        ("45 Mini Euro Card Sleeves (46 x 69 mm)", "", (46.0, 69.0)),
        ("100 Standard Size Card Sleeves | 68X88Mm", "", (68.0, 88.0)),
        ("Paladin Hazel (44 x 63.5 mm)", "", (44.0, 63.5)),
        ("BCW Board Game Sleeves Standard European (59mm x 9", "03BCW1-BG-59X92", (59.0, 92.0)),
        ("Phantom Sleeves 90mm x 50mm", "", (50.0, 90.0)),  # oriented width <= height
        ("11x17 Print Sleeves", "03BCW1-11X17SLV", None),  # not card sized
        ("Board Game Sleeves Clear - Mini", "02AT-10405", None),
    ])
    def test_parse_size(self, name, code, expected):
        assert parse_size_mm(name, code) == expected

    @pytest.mark.parametrize("name,expected", [
        ("Mini Euro (55 Sleeves per Pack)", 55),
        ("Dragon Shield Matte 100ct", 100),
        ("Phantom Sleeves: Red Size (45mm x 68mm) - Gloss/Gloss (50)", 50),
        ("100 Standard Size Card Sleeves | 68X88Mm", 100),
        ("Board Game Sleeves Clear - Mini", None),
    ])
    def test_parse_pack(self, name, expected):
        assert parse_pack_size(name) == expected

    def test_stock_state_treats_zero_and_negative_as_out(self):
        assert [stock_state(q) for q in (None, 5, 0, -99)] == ["unknown", "in_stock", "out_of_stock", "out_of_stock"]


def _game(db, title="G", bgg_id=1):
    g = Game(title=title, bgg_id=bgg_id, status="OWNED", has_sleeves="found")
    db.add(g)
    db.commit()
    return g


def _product(db, name, price=5.0, per_pack=50, w=59, h=91, in_stock=0, link=None, dist="LPG"):
    p = SleeveProduct(distributor=dist, name=name, width_mm=w, height_mm=h,
                      sleeves_per_pack=per_pack, price=price, in_stock=in_stock)
    for key in ([link] if isinstance(link, tuple) else link or []):
        p.distro_links.append(SleeveProductDistroLink(hl_distributor=key[0], hl_distro_code=key[1]))
    db.add(p)
    db.commit()
    return p


class TestProductAvailability:
    def test_returns_live_option_for_linked_products_only(self, db_session):
        linked = _product(db_session, "A", link=("LPG", "1"))
        _product(db_session, "B")
        with patch("services.sleeve_distro.fetch_distro_codes_by_key", return_value=[_row("LPG", "1", "A", qty=7)]):
            result = product_availability(db_session.query(SleeveProduct).all())
        assert list(result) == [linked.id]
        assert result[linked.id]["stock_state"] == "in_stock"

    def test_none_when_hl_unreachable(self, db_session):
        _product(db_session, "A", link=("LPG", "1"))
        with patch("services.sleeve_distro.fetch_distro_codes_by_key", side_effect=HLStockServiceError("down")):
            assert product_availability(db_session.query(SleeveProduct).all()) is None


    def test_multiple_links_pick_best_supplier_and_keep_all_options(self, db_session):
        p = _product(db_session, "A", link=[("LPG", "1"), ("VR", "2"), ("GEEK CULTURE", "3"), ("VR", "gone")])
        rows = [
            _row("LPG", "1", "A", qty=0, cost=3.0),
            _row("VR", "2", "A", qty=5, cost=4.0),
            _row("GEEK CULTURE", "3", "A", qty=9, cost=3.5),
        ]
        with patch("services.sleeve_distro.fetch_distro_codes_by_key", return_value=rows):
            best = product_availability(db_session.query(SleeveProduct).all())[p.id]
        assert (best["distributor"], best["distro_code"]) == ("GEEK CULTURE", "3")  # in stock, cheaper than VR
        assert [o["distro_code"] for o in best["options"]] == ["3", "2", "1", "gone"]
        assert best["options"][-1]["inactive"] is True

    def test_all_links_inactive_is_neutral(self, db_session):
        p = _product(db_session, "A", link=("LPG", "gone"))
        with patch("services.sleeve_distro.fetch_distro_codes_by_key", return_value=[]):
            best = product_availability(db_session.query(SleeveProduct).all())[p.id]
        assert best["stock_state"] == "unknown" and best["inactive"] and len(best["options"]) == 1


class TestToOrderUsesDistributorStock:
    def _setup(self, db):
        g = _game(db)
        db.add(Sleeve(game_id=g.id, width_mm=59, height_mm=91, quantity=100, is_sleeved=False))
        db.commit()
        tight = _product(db, "Tight fit", price=4.0, h=91, link=("LPG", "T"))
        loose = _product(db, "Loose fit", price=5.0, h=93, link=("LPG", "L"))
        return tight, loose

    def test_without_availability_prefers_tightest_fit(self, db_session):
        tight, _ = self._setup(db_session)
        [row] = compute_to_order_list(db_session)
        assert row["product"]["product_id"] == tight.id

    def test_out_of_stock_at_distributor_loses_to_one_that_ships(self, db_session):
        tight, loose = self._setup(db_session)
        availability = {
            tight.id: {"stock_state": "out_of_stock", "qty_available": 0, "cost_price_ex_gst": 3.0, "distro_code": "T"},
            loose.id: {"stock_state": "in_stock", "qty_available": 50, "cost_price_ex_gst": 4.0, "distro_code": "L"},
        }
        [row] = compute_to_order_list(db_session, availability=availability)
        assert row["product"]["product_id"] == loose.id
        assert row["product"]["distributor_stock"] == 50
        assert [a["product_id"] for a in row["product"]["alternatives"]] == [tight.id]
        assert row["product"]["alternatives"][0]["distributor_stock_state"] == "out_of_stock"


class TestUnlistedSleeves:
    def test_surfaces_catalogue_sleeves_that_fit_a_needed_size(self, db_session):
        g = _game(db_session)
        db_session.add(Sleeve(game_id=g.id, width_mm=46, height_mm=69, quantity=45, is_sleeved=False))
        db_session.commit()
        _product(db_session, "Listed", w=59, h=91, link=("LPG", "LISTED"))
        catalogue = [
            _row("VR", "129356", "45 Mini Euro Card Sleeves (46 x 69 mm)", qty=19, cost=5.88),
            _row("LPG", "LISTED", "Linked sleeve (59 x 91 mm)"),
            _row("LPG", "X", "Unrelated Sleeves (70 x 120 mm)"),
            _row("LPG", "Y", "Apex Legends - Card Sleeves"),
        ]
        with patch("services.sleeve_distro.fetch_sleeve_catalogue", return_value=catalogue):
            items = unlisted_sleeves(db_session)
            all_items = unlisted_sleeves(db_session, include_all=True)

        assert [i["distro_code"] for i in items] == ["129356"]
        hit = items[0]
        assert hit["fills_gap"] is True and hit["fits"][0]["total_needed"] == 45
        assert hit["sleeves_per_pack"] == 45 and hit["cost_per_sleeve"] == pytest.approx(0.131, abs=1e-3)
        assert {i["distro_code"] for i in all_items} == {"129356", "X"}  # linked + unparseable excluded


class TestAutoLink:
    def test_links_by_code_then_unambiguous_name_and_never_overwrites(self, db_session):
        by_code = _product(db_session, "By code", dist="LPG")
        by_code.item_id = "254223"
        by_name = _product(db_session, "Board Game Sleeves Clear - Mini", dist="Geek Culture")
        ambiguous = _product(db_session, "Dup name", dist="Geek Culture")
        existing = _product(db_session, "Pinned", dist="LPG", link=("LPG", "KEEP"))
        db_session.commit()
        catalogue = [
            _row("LPG", "254223", "Dragon Shield American Mini"),
            _row("GEEK CULTURE", "02AT-10405", "Board Game Sleeves Clear - Mini"),
            _row("GEEK CULTURE", "D1", "Dup name"),
            _row("GEEK CULTURE", "D2", "dup name"),
        ]
        with patch("services.sleeve_distro.fetch_sleeve_catalogue", return_value=catalogue):
            result = sleeve_distro.auto_link_products(db_session)

        assert (result["linked"], result["already_linked"]) == (2, 1)
        assert [u["id"] for u in result["unmatched"]] == [ambiguous.id]
        db_session.refresh(by_code), db_session.refresh(by_name), db_session.refresh(existing)
        assert [(l.hl_distributor, l.hl_distro_code) for l in by_code.distro_links] == [("LPG", "254223")]
        assert [(l.hl_distributor, l.hl_distro_code) for l in by_name.distro_links] == [("GEEK CULTURE", "02AT-10405")]
        assert [l.hl_distro_code for l in existing.distro_links] == ["KEEP"]


class TestLinkEndpoints:
    def test_add_several_links_list_live_and_remove_one(self, client, db_session, admin_headers):
        p = _product(db_session, "A")
        rows = {"99": _row("LPG", "99", "Dragon Shield Mini", qty=0), "7": _row("VR", "7", "DS Mini", qty=12)}

        def fetch(keys):
            return [rows[c] for _, c in keys if c in rows]

        with patch("api.routers.sleeves.fetch_distro_codes_by_key", side_effect=fetch), \
             patch("services.sleeve_distro.fetch_distro_codes_by_key", side_effect=fetch):
            r1 = client.post(f"/api/admin/sleeves/products/{p.id}/distro-links", headers=admin_headers,
                             json={"distributor": "LPG", "distro_code": "99"})
            r2 = client.post(f"/api/admin/sleeves/products/{p.id}/distro-links", headers=admin_headers,
                             json={"distributor": "VR", "distro_code": "7"})
            dup = client.post(f"/api/admin/sleeves/products/{p.id}/distro-links", headers=admin_headers,
                              json={"distributor": "VR", "distro_code": "7"})
            assert r1.status_code == r2.status_code == dup.status_code == 200
            body = dup.json()
            assert [d["distro_code"] for d in body["distros"]] == ["7", "99"]  # in stock first, no duplicate
            assert body["distro"]["distro_code"] == "7"
            listed = client.get("/api/admin/sleeves/products", headers=admin_headers).json()
            assert len(listed[0]["distros"]) == 2

            link_id = body["distros"][1]["link_id"]
            r = client.delete(f"/api/admin/sleeves/products/{p.id}/distro-links/{link_id}", headers=admin_headers)
            assert r.status_code == 200 and [d["distro_code"] for d in r.json()["distros"]] == ["7"]

    def test_create_product_with_link(self, client, admin_headers):
        row = _row("LPG", "5", "X", qty=3)
        with patch("api.routers.sleeves.fetch_distro_codes_by_key", return_value=[row]), \
             patch("services.sleeve_distro.fetch_distro_codes_by_key", return_value=[row]):
            r = client.post("/api/admin/sleeves/products", headers=admin_headers, json={
                "distributor": "LPG", "name": "X", "width_mm": 59, "height_mm": 91, "sleeves_per_pack": 50,
                "price": 4.5, "distro_link": {"distributor": "LPG", "distro_code": "5"}})
        assert r.status_code == 200 and r.json()["distro"]["distro_code"] == "5"

    def test_unlink_of_other_products_link_404s(self, client, db_session, admin_headers):
        a = _product(db_session, "A", link=("LPG", "1"))
        b = _product(db_session, "B")
        r = client.delete(f"/api/admin/sleeves/products/{b.id}/distro-links/{a.distro_links[0].id}", headers=admin_headers)
        assert r.status_code == 404

    def test_link_rejects_unknown_code(self, client, db_session, admin_headers):
        p = _product(db_session, "A")
        with patch("api.routers.sleeves.fetch_distro_codes_by_key", return_value=[]):
            r = client.post(f"/api/admin/sleeves/products/{p.id}/distro-links", headers=admin_headers,
                            json={"distributor": "LPG", "distro_code": "nope"})
        assert r.status_code == 404

    def test_unlisted_endpoint_reports_hl_outage_as_503(self, client, admin_headers):
        with patch("services.sleeve_distro.fetch_sleeve_catalogue", side_effect=HLStockServiceError("down")):
            r = client.get("/api/admin/sleeves/catalogue/unlisted", headers=admin_headers)
        assert r.status_code == 503
