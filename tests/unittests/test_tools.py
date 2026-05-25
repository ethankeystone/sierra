"""Unit tests for tools.py — uses an in-memory SQLite DB, never touches sierra.db."""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from db import _SCHEMA, _INDEXES


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def conn():
    """In-memory SQLite connection seeded with schema + test data."""
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    c.executescript(_SCHEMA + _INDEXES)

    c.executemany(
        "INSERT INTO customers (id, name, email) VALUES (?,?,?)",
        [
            ("C1", "Alice Smith", "alice@example.com"),
            ("C2", "Bob Jones",  "bob@example.com"),
        ],
    )
    c.executemany(
        "INSERT INTO products (sku, name, inventory, description) VALUES (?,?,?,?)",
        [
            ("BOOT-01", "Trail Boot",   5, "Sturdy hiking boot"),
            ("TENT-01", "Base Tent",    3, "3-season tent"),
            ("PACK-01", "Day Pack",     0, "Out-of-stock pack"),
        ],
    )
    c.executemany(
        "INSERT INTO product_tags (sku, tag) VALUES (?,?)",
        [
            ("BOOT-01", "Hiking"),
            ("BOOT-01", "Adventure"),
            ("TENT-01", "Camping"),
            ("TENT-01", "Adventure"),
            ("PACK-01", "Hiking"),
        ],
    )
    c.executemany(
        "INSERT INTO orders (id, customer_id, status, tracking_number) VALUES (?,?,?,?)",
        [
            ("W001", "C1", "in_transit", "TRK-AAA"),
            ("W002", "C1", "delivered", None),
            ("W003", "C2", "pending",   None),
        ],
    )
    c.executemany(
        "INSERT INTO order_items (order_id, sku) VALUES (?,?)",
        [
            ("W001", "BOOT-01"),
            ("W002", "TENT-01"),
            ("W002", "BOOT-01"),
            ("W003", "TENT-01"),
        ],
    )
    c.executemany(
        "INSERT INTO promotions (id, title, code, discount_pct, valid_from, valid_until, description) VALUES (?,?,?,?,?,?,?)",
        [
            ("P1", "Summer Sale",  "SUMMER10", 10, "2020-01-01 00:00:00", "2099-12-31 23:59:59", "10% off"),
            ("P2", "Expired Deal", "OLD50",    50, "2000-01-01 00:00:00", "2000-12-31 23:59:59", "long gone"),
        ],
    )
    c.execute("INSERT INTO promotion_tags (promo_id, tag) VALUES (?,?)", ("P1", "Hiking"))
    c.commit()
    return c


# ── GetOrderTool ──────────────────────────────────────────────────────────────

class TestGetOrderTool:
    @pytest.fixture(autouse=True)
    def tool(self, conn):
        from tools import GetOrderTool
        self.t = GetOrderTool(conn)

    def test_found_single_item(self):
        result = self.t.execute(order_id="W001", customer_email="alice@example.com")
        assert result["order_id"] == "W001"
        assert result["status"] == "in_transit"
        assert result["tracking_number"] == "TRK-AAA"
        assert result["tracking_url"] == "https://tools.usps.com/go/TrackConfirmAction?tLabels=TRK-AAA"
        assert result["customer_name"] == "Alice Smith"
        assert len(result["items"]) == 1
        assert result["items"][0]["sku"] == "BOOT-01"

    def test_found_multiple_items(self):
        result = self.t.execute(order_id="W002", customer_email="alice@example.com")
        assert result["order_id"] == "W002"
        assert result["tracking_number"] is None
        assert result["tracking_url"] is None
        skus = {i["sku"] for i in result["items"]}
        assert skus == {"TENT-01", "BOOT-01"}

    def test_strips_leading_hash(self):
        result = self.t.execute(order_id="#W001", customer_email="alice@example.com")
        assert result["order_id"] == "W001"

    def test_wrong_email_returns_error(self):
        result = self.t.execute(order_id="W001", customer_email="bob@example.com")
        assert "error" in result
        assert "W001" in result["error"]

    def test_nonexistent_order_returns_error(self):
        result = self.t.execute(order_id="W999", customer_email="alice@example.com")
        assert "error" in result

    def test_openai_schema_shape(self):
        schema = self.t.openai_schema()
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "get_order"
        required = schema["function"]["parameters"]["required"]
        assert set(required) == {"order_id", "customer_email"}


# ── GetOrdersByCustomerTool ───────────────────────────────────────────────────

class TestGetOrdersByCustomerTool:
    @pytest.fixture(autouse=True)
    def tool(self, conn):
        from tools import GetOrdersByCustomerTool
        self.t = GetOrdersByCustomerTool(conn)

    def test_returns_all_orders_for_customer(self):
        results = self.t.execute(customer_email="alice@example.com")
        assert len(results) == 2
        order_ids = {r["order_id"] for r in results}
        assert order_ids == {"W001", "W002"}

    def test_returns_correct_fields(self):
        results = self.t.execute(customer_email="alice@example.com")
        for r in results:
            assert "order_id" in r
            assert "status" in r
            assert "tracking_number" in r
            assert "tracking_url" in r
            if r["tracking_number"]:
                assert r["tracking_url"] == f"https://tools.usps.com/go/TrackConfirmAction?tLabels={r['tracking_number']}"
            else:
                assert r["tracking_url"] is None

    def test_unknown_customer_returns_empty(self):
        results = self.t.execute(customer_email="nobody@example.com")
        assert results == []

    def test_single_order_customer(self):
        results = self.t.execute(customer_email="bob@example.com")
        assert len(results) == 1
        assert results[0]["order_id"] == "W003"
        assert results[0]["status"] == "pending"


# ── SearchProductsTool ────────────────────────────────────────────────────────

class TestSearchProductsTool:
    @pytest.fixture(autouse=True)
    def tool(self, conn):
        from tools import SearchProductsTool
        self.t = SearchProductsTool(conn, ["Hiking", "Camping", "Adventure", "Misc"])

    def test_no_filter_returns_in_stock_only(self):
        results = self.t.execute()
        skus = {r["sku"] for r in results}
        assert "PACK-01" not in skus
        assert "BOOT-01" in skus
        assert "TENT-01" in skus

    def test_tag_filter_hiking(self):
        results = self.t.execute(tags=["Hiking"])
        skus = {r["sku"] for r in results}
        assert "BOOT-01" in skus
        assert "PACK-01" not in skus

    def test_tag_filter_matches_any_tag(self):
        results = self.t.execute(tags=["Camping", "Hiking"])
        skus = {r["sku"] for r in results}
        assert "BOOT-01" in skus
        assert "TENT-01" in skus

    def test_unknown_tag_returns_empty(self):
        results = self.t.execute(tags=["Scuba"])
        assert results == []

    def test_limit_respected(self):
        results = self.t.execute(limit=1)
        assert len(results) == 1

    def test_result_fields(self):
        results = self.t.execute()
        for r in results:
            assert "sku" in r
            assert "name" in r
            assert "description" in r
            assert "tags" in r

    def test_default_limit_is_thirty(self, conn):
        for i in range(32):
            sku = f"EXTRA-{i:02d}"
            conn.execute(
                "INSERT OR IGNORE INTO products (sku, name, inventory) VALUES (?,?,?)",
                (sku, f"Extra {i}", 1),
            )
            conn.execute("INSERT OR IGNORE INTO product_tags (sku, tag) VALUES (?,?)", (sku, "Misc"))
        conn.commit()
        results = self.t.execute()
        assert len(results) <= 30


# ── GetActivePromotionsTool ───────────────────────────────────────────────────

class TestGetActivePromotionsTool:
    @pytest.fixture(autouse=True)
    def tool(self, conn):
        from tools import GetActivePromotionsTool
        self.t = GetActivePromotionsTool(conn)

    def test_returns_active_promotion(self):
        results = self.t.execute()
        codes = {r["code"] for r in results}
        assert "SUMMER10" in codes

    def test_expired_promotion_excluded(self):
        results = self.t.execute()
        codes = {r["code"] for r in results}
        assert "OLD50" not in codes

    def test_result_fields(self):
        results = self.t.execute()
        for r in results:
            for field in ("id", "title", "code", "discount_pct", "applies_to_tags",
                          "valid_from", "valid_until", "description"):
                assert field in r

    def test_promotion_has_correct_tag(self):
        results = self.t.execute()
        summer = next(r for r in results if r["code"] == "SUMMER10")
        assert "Hiking" in summer["applies_to_tags"]

    def test_ordered_by_discount_desc(self, conn):
        conn.execute(
            "INSERT INTO promotions (id, title, code, discount_pct, valid_from, valid_until) "
            "VALUES (?,?,?,?,?,?)",
            ("P3", "Big Sale", "BIG25", 25, "2020-01-01", "2099-12-31"),
        )
        conn.commit()
        results = self.t.execute()
        discounts = [r["discount_pct"] for r in results]
        assert discounts == sorted(discounts, reverse=True)


# ── ClaimPromotionTool ────────────────────────────────────────────────────────

class TestClaimPromotionTool:
    @pytest.fixture(autouse=True)
    def tool(self, conn):
        from tools import ClaimPromotionTool
        # Seed an always-active promo with no daily window restriction
        conn.execute(
            "INSERT OR REPLACE INTO promotions "
            "(id, title, code, discount_pct, valid_from, valid_until, description, "
            "daily_start_hour, daily_end_hour) VALUES (?,?,?,?,?,?,?,?,?)",
            ("EARLY-RISERS", "Early Risers", "EARLY", 10,
             "2020-01-01 00:00:00", "2099-12-31 23:59:59", "10% off for early shoppers",
             None, None),
        )
        conn.commit()
        self.t = ClaimPromotionTool(conn)

    def test_generates_unique_code(self):
        result = self.t.execute(promo_id="EARLY-RISERS", customer_email="alice@example.com")
        assert "error" not in result
        assert result["code"].startswith("EARLY-")
        assert result["discount_pct"] == 10
        assert result["already_claimed"] is False

    def test_idempotent_returns_same_code(self):
        first = self.t.execute(promo_id="EARLY-RISERS", customer_email="alice@example.com")
        second = self.t.execute(promo_id="EARLY-RISERS", customer_email="alice@example.com")
        assert first["code"] == second["code"]
        assert second["already_claimed"] is True

    def test_different_customers_get_different_codes(self):
        alice = self.t.execute(promo_id="EARLY-RISERS", customer_email="alice@example.com")
        bob = self.t.execute(promo_id="EARLY-RISERS", customer_email="bob@example.com")
        assert alice["code"] != bob["code"]

    def test_unknown_customer_returns_error(self):
        result = self.t.execute(promo_id="EARLY-RISERS", customer_email="nobody@example.com")
        assert "error" in result

    def test_inactive_promo_returns_error(self):
        result = self.t.execute(promo_id="P2", customer_email="alice@example.com")
        assert "error" in result

    def test_nonexistent_promo_returns_error(self):
        result = self.t.execute(promo_id="FAKE-999", customer_email="alice@example.com")
        assert "error" in result

    def test_daily_window_rejects_outside_hours(self, conn):
        from tools import ClaimPromotionTool
        # Window that can never match (start == end)
        conn.execute(
            "INSERT OR REPLACE INTO promotions "
            "(id, title, code, discount_pct, valid_from, valid_until, "
            "daily_start_hour, daily_end_hour) VALUES (?,?,?,?,?,?,?,?)",
            ("NARROW", "Narrow Window", "NARROW10", 10,
             "2020-01-01 00:00:00", "2099-12-31 23:59:59", 0, 0),
        )
        conn.commit()
        t = ClaimPromotionTool(conn)
        result = t.execute(promo_id="NARROW", customer_email="alice@example.com")
        assert "error" in result
        assert "Pacific Time" in result["error"]

    def test_daily_window_accepts_within_hours(self, conn):
        from tools import ClaimPromotionTool

        conn.execute(
            "INSERT OR REPLACE INTO promotions "
            "(id, title, code, discount_pct, valid_from, valid_until, "
            "daily_start_hour, daily_end_hour) VALUES (?,?,?,?,?,?,?,?)",
            ("WIDE", "Wide Window", "WIDE10", 10,
             "2020-01-01 00:00:00", "2099-12-31 23:59:59", 8, 10),
        )
        conn.commit()
        t = ClaimPromotionTool(conn)
        with patch("tools._current_pt_hour", return_value=9):
            result = t.execute(promo_id="WIDE", customer_email="alice@example.com")
        assert "error" not in result
        assert result["code"].startswith("WIDE10-")


# ── Registry ──────────────────────────────────────────────────────────────────

class TestRegistry:
    @pytest.fixture(autouse=True)
    def reg(self, conn):
        from tools import build_registry
        self.reg = build_registry(conn)

    def test_registry_has_all_tools(self):
        names = {s["function"]["name"] for s in self.reg.openai_tools()}
        assert names == {
            "get_order",
            "get_orders_by_customer",
            "search_products",
            "get_active_promotions",
            "claim_promotion",
            "lookup_customer",
            "register_customer",
            "create_order",
        }

    def test_execute_unknown_tool(self):
        result = self.reg.execute("does_not_exist")
        assert "error" in result

    def test_execute_dispatches_correctly(self):
        result = self.reg.execute("get_orders_by_customer", customer_email="alice@example.com")
        assert isinstance(result, list)
        assert any(r["order_id"] == "W001" for r in result)
