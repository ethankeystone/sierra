"""
EVAL: Product Search
====================
Verifies that the agent routes product queries to search_products with the
right tag filters, respects inventory state, and handles empty results gracefully.

All tests are read-only — no DB mutations are expected or permitted.

Weight guide
------------
  weight=2  Tag routing and inventory filtering (core search correctness)
  weight=1  Browse-all and empty-result UX (nice-to-have quality)

Domain max score: 6
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from db import get_connection
from .helpers import run_conversation


# ─────────────────────────────────────────────────────────────────────────────
# weight=2  |  Tag-filtered search routes to correct tool parameter
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.weight(2)
def test_search_by_activity_tag(seeded_db, tracer, trajectory):
    """
    Asking for 'hiking gear' should call search_products with a tags parameter
    that includes 'Hiking' (or a close synonym), and the reply should list
    at least one in-stock product.

    DB assertion: no mutations.

    PASS criteria
    -------------
    - search_products called.
    - At least one in-stock product returned in the tool result.
    - Reply lists at least one product name.
    """
    conn = get_connection()
    order_count_before = conn.execute("SELECT COUNT(*) AS n FROM orders").fetchone()["n"]
    conn.close()

    _, reply = run_conversation(["I need some hiking gear — what do you have?"], trajectory=trajectory)

    search_calls = [c for c in tracer if c.name == "search_products"]
    assert search_calls, "Expected search_products to be called"

    # At least one result in the tool return (not just an empty list)
    last_results = search_calls[-1].result
    assert isinstance(last_results, list), "search_products should return a list"
    assert len(last_results) > 0, "search_products returned no in-stock products for Hiking tag"

    assert reply.strip(), "Reply should not be empty"

    conn = get_connection()
    assert conn.execute("SELECT COUNT(*) AS n FROM orders").fetchone()["n"] == order_count_before
    conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# weight=2  |  Out-of-stock products never appear in search results
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.weight(2)
def test_out_of_stock_excluded_from_results(seeded_db, tracer, trajectory):
    """
    OOS-TEST has the 'Hiking' tag but inventory=0.  It must never appear in
    search results regardless of the query.

    DB assertion: no mutations.

    PASS criteria
    -------------
    - search_products called.
    - OOS-TEST SKU absent from every search_products result.
    - 'Perpetually Out-of-Stock Widget' absent from the reply.
    """
    _, reply = run_conversation(["Show me all your hiking products"], trajectory=trajectory)

    search_calls = [c for c in tracer if c.name == "search_products"]
    assert search_calls, "Expected search_products to be called"

    for call in search_calls:
        result_skus = [r.get("sku") for r in call.result if isinstance(r, dict)]
        assert "OOS-TEST" not in result_skus, (
            "OOS-TEST (inventory=0) appeared in search_products results"
        )

    assert "Perpetually Out-of-Stock Widget" not in reply, (
        "OOS product name appeared in the reply"
    )


# ─────────────────────────────────────────────────────────────────────────────
# weight=1  |  Unfiltered browse returns in-stock products
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.weight(1)
def test_browse_all_products(seeded_db, tracer, trajectory):
    """
    'What gear do you have?' with no specific activity should call
    search_products (possibly with no tags), returning in-stock items.

    PASS criteria
    -------------
    - search_products called.
    - Tool result is a non-empty list.
    - Reply is non-empty.
    """
    _, reply = run_conversation(["What outdoor gear do you carry?"], trajectory=trajectory)

    search_calls = [c for c in tracer if c.name == "search_products"]
    assert search_calls, "Expected search_products to be called for a general browse"

    results = search_calls[-1].result
    assert isinstance(results, list) and len(results) > 0, (
        "search_products returned an empty list for a general browse"
    )
    assert reply.strip()


# ─────────────────────────────────────────────────────────────────────────────
# weight=1  |  No-match query handled gracefully without hallucination
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.weight(1)
def test_no_match_gracefully_handled(seeded_db, tracer, trajectory):
    """
    Asking for 'laptop computers' (completely outside the outdoor gear catalogue) should
    call search_products, receive an empty list, and respond helpfully without
    fabricating product names or prices.

    PASS criteria
    -------------
    - search_products called.
    - Reply communicates that laptops are not available (does not silently ignore).
    - Reply is non-empty (agent says something helpful).
    """
    _, reply = run_conversation(["Do you have any laptop computers?"], trajectory=trajectory)

    search_calls = [c for c in tracer if c.name == "search_products"]
    assert search_calls, "Expected search_products to be called"

    assert reply.strip(), "Reply should not be empty — agent should say something helpful"

    # Agent must communicate that laptops are not available
    reply_lower = reply.lower()
    no_result_terms = ["don't", "do not", "doesn't", "unable", "not carry",
                       "not available", "unfortunately", "don't carry", "don't have",
                       "don't stock", "don't offer", "no laptop", "can't help",
                       "out of stock"]
    assert any(term in reply_lower for term in no_result_terms), (
        f"Reply did not communicate that laptops are unavailable.\nReply: {reply}"
    )
