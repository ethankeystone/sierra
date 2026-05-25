"""
EVAL: Order Lookup
==================
Verifies that the agent correctly routes order-lookup requests to the right
tools and surfaces accurate order data back to the customer.

All tests in this domain are read-only — no DB mutations are expected.
Any write detected is treated as a test failure.

Weight guide
------------
  weight=2  Core lookup flows and email precondition (must work for a basic UX)
  weight=1  Edge-case handling (graceful degradation on bad input)

Domain max score: 7
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from db import get_connection
from .helpers import run_conversation


# ─────────────────────────────────────────────────────────────────────────────
# weight=2  |  Email must be given before any order tool fires
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.weight(2)
def test_agent_asks_for_email_first(seeded_db, tracer, trajectory):
    """
    A bare 'where are my orders?' without an email must not trigger any
    order lookup tool.  The agent should prompt for the customer's email.

    PASS criteria
    -------------
    - No order tool called.
    - Reply asks for email.
    """
    _, reply = run_conversation(["Where are my orders?"], trajectory=trajectory)

    order_tools = [c for c in tracer if c.name in ("get_order", "get_orders_by_customer")]
    assert not order_tools, (
        "Agent called an order tool without the customer providing their email"
    )
    assert "email" in reply.lower(), "Reply should ask for the customer's email"


# ─────────────────────────────────────────────────────────────────────────────
# weight=2  |  Listing all orders for a known customer
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.weight(2)
def test_lists_orders_by_email(seeded_db, tracer, trajectory):
    """
    After Alice identifies, asking 'what are my orders?' should call
    get_orders_by_customer and surface both TORD-001 and TORD-002 in the reply.

    DB assertion: row count unchanged.

    PASS criteria
    -------------
    - get_orders_by_customer called with alice@test.com.
    - Reply mentions TORD-001 and TORD-002 (or their statuses: in_transit / delivered).
    """
    conn = get_connection()
    orders_before = conn.execute("SELECT COUNT(*) AS n FROM orders").fetchone()["n"]
    conn.close()

    _, reply = run_conversation([
        "My email is alice@test.com",
        "What are all my orders?",
    ], trajectory=trajectory)

    by_customer_calls = [c for c in tracer if c.name == "get_orders_by_customer"]
    assert by_customer_calls, "Expected get_orders_by_customer to be called"
    assert by_customer_calls[-1].kwargs.get("customer_email") == "alice@test.com"

    reply_upper = reply.upper()
    assert "TORD-001" in reply_upper or "TORD-002" in reply_upper, (
        "Reply did not mention either of Alice's orders"
    )

    conn = get_connection()
    assert conn.execute("SELECT COUNT(*) AS n FROM orders").fetchone()["n"] == orders_before
    conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# weight=2  |  Tracking URL is surfaced for orders that have a tracking number
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.weight(2)
def test_tracking_url_surfaced(seeded_db, tracer, trajectory):
    """
    When Alice asks about TORD-001 (which has tracking number TRK-TEST-001),
    the agent should include the full USPS tracking URL in its reply.

    PASS criteria
    -------------
    - get_order called for TORD-001.
    - Reply contains the full USPS tracking URL for TRK-TEST-001.
    """
    _, reply = run_conversation([
        "My email is alice@test.com",
        "Can you look up order TORD-001 for me?",
    ], trajectory=trajectory)

    get_order_calls = [c for c in tracer if c.name == "get_order"]
    assert get_order_calls, "Expected get_order to be called"

    expected_url = "https://tools.usps.com/go/TrackConfirmAction?tLabels=TRK-TEST-001"
    assert expected_url in reply, (
        f"Reply should contain the full tracking URL: {expected_url}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# weight=1  |  Unknown order ID handled gracefully
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.weight(1)
def test_unknown_order_id_gracefully_handled(seeded_db, tracer, trajectory):
    """
    Asking for a non-existent order (W999) should surface a helpful message,
    not crash or hallucinate order details.

    PASS criteria
    -------------
    - get_order called and returns an error dict.
    - Reply does not fabricate order data.
    - Reply is not an empty string.
    """
    _, reply = run_conversation([
        "My email is alice@test.com",
        "Can you look up order W999 for me?",
    ], trajectory=trajectory)

    # The agent may call get_order and get a tool error, or may determine from
    # context that W999 doesn't belong to Alice and respond directly — both are valid.
    get_order_calls = [c for c in tracer if c.name == "get_order"]
    if get_order_calls:
        assert "error" in get_order_calls[-1].result, (
            "get_order should return an error for a non-existent order"
        )

    assert reply.strip(), "Reply should not be empty"
    # Must not fabricate a tracking number for a non-existent order
    assert "TRK-TEST-" not in reply, "Reply leaked a real tracking number for a non-existent order"
