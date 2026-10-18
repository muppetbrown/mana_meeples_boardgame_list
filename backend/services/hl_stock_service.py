# services/hl_stock_service.py
"""
Reads board-game stock/sales signals directly from the HL Timaru retail
database (a separate Postgres instance in the same Render workspace,
reached with a dedicated read-only role - see HL_STOCK_DATABASE_URL).

Adapts sql/reports/best_sellers_by_category.sql from the hl-timaru-stock
repo: trailing-window units sold from stock_history, joined to
current_stock. Unlike that report, this LEFT JOINs the sales window so
in-stock-but-not-selling board games are still returned - "in stock but
not moving" is also a useful signal here, not just "selling well".

This is a demand signal (is this game selling at retail), not a
price-tracking subsystem - it only reads current_stock.price, already
computed server-side by HL for its own reporting.
"""
import logging

from sqlalchemy import bindparam, text

from config import HL_STOCK_SALES_WINDOW_DAYS
from database import HLStockSessionLocal

logger = logging.getLogger(__name__)

_BEST_SELLERS_QUERY = text("""
    WITH sales AS (
        SELECT
            internal_id,
            SUM(old_qty - new_qty) FILTER (WHERE new_qty < old_qty) AS units_sold,
            COUNT(DISTINCT changed_date) FILTER (WHERE new_qty < old_qty) AS sale_days,
            MAX(changed_date) FILTER (WHERE new_qty < old_qty) AS last_sale_date
        FROM stock_history
        WHERE changed_date >= CURRENT_DATE - (:window_days || ' days')::interval
        GROUP BY internal_id
    )
    SELECT
        p.internal_id,
        cs.name,
        cs.sku,
        cs.quantity AS current_stock,
        cs.price,
        COALESCE(s.units_sold, 0) AS units_sold,
        s.sale_days,
        s.last_sale_date,
        ROUND(COALESCE(s.units_sold, 0) * cs.price, 2) AS approx_revenue
    FROM products p
    JOIN current_stock cs ON cs.internal_id = p.internal_id
    LEFT JOIN sales s ON s.internal_id = p.internal_id
    WHERE p.product_type = 'stock'
      AND p.category = 'Board Games'
      AND NOT p.do_not_reorder
    ORDER BY units_sold DESC, cs.quantity DESC
    LIMIT 500
""")


class HLStockServiceError(Exception):
    """Raised when the HL stock-signal query can't be run (not configured, or a DB error)."""


def fetch_hl_board_game_signals() -> list[dict]:
    """Board-game stock + sales velocity from HL Timaru, as a list of dicts.

    Raises HLStockServiceError if HL_STOCK_DATABASE_URL isn't configured or
    the query fails - a sync failure here just means stale/empty signals in
    one admin panel, not a request that should hard-fail.
    """
    if HLStockSessionLocal is None:
        raise HLStockServiceError("HL_STOCK_DATABASE_URL not configured")

    db = HLStockSessionLocal()
    try:
        rows = db.execute(
            _BEST_SELLERS_QUERY, {"window_days": HL_STOCK_SALES_WINDOW_DAYS}
        ).mappings().all()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"HL stock-signal query failed: {e}")
        raise HLStockServiceError(f"Failed to read HL stock data: {e}") from e
    finally:
        db.close()


# Board-game rows from the distributor catalogue (distro_codes, loaded by the
# hl-timaru-stock repo's scripts/import_distro_codes.py). Rows already linked to
# a product are limited to Board Games so TCG / miniatures / RPG codes don't
# bloat the match pool; unlinked rows (internal_id IS NULL) are kept because
# a game we've never stocked is exactly what a suggestion usually is.
_DISTRO_CATALOGUE_QUERY = text("""
    SELECT
        dc.distributor,
        dc.distro_code,
        dc.distro_product_name AS name,
        dc.cost_price_ex_gst,
        dc.qty_available,
        dc.qty_updated_at
    FROM distro_codes dc
    LEFT JOIN products p ON p.internal_id = dc.internal_id
    WHERE dc.active
      AND dc.distro_product_name IS NOT NULL
      AND (dc.internal_id IS NULL OR p.category = 'Board Games')
""")


def fetch_distro_catalogue() -> list[dict]:
    """Active distributor catalogue rows (name, cost ex GST, stock) from HL Timaru.

    Raises HLStockServiceError if HL_STOCK_DATABASE_URL isn't configured or the
    query fails, same as fetch_hl_board_game_signals.
    """
    if HLStockSessionLocal is None:
        raise HLStockServiceError("HL_STOCK_DATABASE_URL not configured")

    db = HLStockSessionLocal()
    try:
        rows = db.execute(_DISTRO_CATALOGUE_QUERY).mappings().all()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"HL distro catalogue query failed: {e}")
        raise HLStockServiceError(f"Failed to read HL distributor catalogue: {e}") from e
    finally:
        db.close()


_DISTRO_SELECT = """
    SELECT
        dc.distributor,
        dc.distro_code,
        dc.distro_product_name AS name,
        dc.cost_price_ex_gst,
        dc.qty_available,
        dc.qty_updated_at
    FROM distro_codes dc
"""

_DISTRO_SEARCH_QUERY = text(
    _DISTRO_SELECT
    + """
    WHERE dc.active
      AND (dc.distro_product_name ILIKE :pattern OR dc.distro_code ILIKE :pattern)
    ORDER BY dc.distro_product_name, dc.distributor
    LIMIT :limit
"""
)

_DISTRO_BY_KEY_QUERY = text(
    _DISTRO_SELECT
    + """
    WHERE dc.active
      AND (dc.distributor, dc.distro_code) IN :keys
"""
).bindparams(bindparam("keys", expanding=True))


def _run_distro_query(query, params: dict) -> list[dict]:
    if HLStockSessionLocal is None:
        raise HLStockServiceError("HL_STOCK_DATABASE_URL not configured")

    db = HLStockSessionLocal()
    try:
        return [dict(row) for row in db.execute(query, params).mappings().all()]
    except Exception as e:
        logger.error(f"HL distro_codes query failed: {e}")
        raise HLStockServiceError(f"Failed to read HL distributor catalogue: {e}") from e
    finally:
        db.close()


def search_distro_codes(query: str, limit: int = 20) -> list[dict]:
    """Active distro_codes rows whose name or code contains `query` (case-insensitive)."""
    escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return _run_distro_query(_DISTRO_SEARCH_QUERY, {"pattern": f"%{escaped}%", "limit": limit})


def fetch_distro_codes_by_key(keys: list[tuple[str, str]]) -> list[dict]:
    """Active distro_codes rows for exact (distributor, distro_code) pairs."""
    if not keys:
        return []
    return _run_distro_query(_DISTRO_BY_KEY_QUERY, {"keys": [tuple(k) for k in keys]})
