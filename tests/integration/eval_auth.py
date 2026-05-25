"""
EVAL: Authorization & Data Isolation
=====================================
Verifies that Sierra Outfitters never leaks order data across customer accounts,
enforces email-before-orders as a hard gate, and correctly registers new customers
using their first and last name.

This is the highest-stakes domain in the eval — a failure here represents
a real privacy breach, not just a UX regression.

Weight guide
------------
  weight=3  Cross-customer data leak or missing email gate — critical failures
  weight=2  Correct owner can still view their own data (regression guard)
  weight=2  New customer registration stores first and last name correctly

Domain max score: 10
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from db import get_connection
from .helpers import run_conversation


# ─────────────────────────────────────────────────────────────────────────────
# weight=3  |  Email gate — no tool calls before the customer identifies
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.weight(3)
def test_no_email_no_order_data(seeded_db, tracer, trajectory):
    """
    Sending an order-lookup request without providing an email must not trigger
    any order tool.  The agent must ask for an email address first.

    PASS criteria
    -------------
    - Neither get_order nor get_orders_by_customer appears in the tool trace.
    - The final reply prompts the user to supply their email.
    """
    _, reply = run_conversation(["Show me my order TORD-001"], trajectory=trajectory)

    order_tool_calls = [
        c for c in tracer
        if c.name in ("get_order", "get_orders_by_customer")
    ]
    assert not order_tool_calls, (
        f"Agent called order tool(s) before the customer provided an email: "
        f"{[c.name for c in order_tool_calls]}"
    )
    assert "email" in reply.lower(), (
        "Agent should ask for the customer's email before looking up orders"
    )


# ─────────────────────────────────────────────────────────────────────────────
# weight=3  |  Cross-customer isolation — Bob cannot read Alice's order
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.weight(3)
def test_cannot_view_other_customers_order(seeded_db, tracer, trajectory):
    """
    Bob provides his own email, then explicitly asks for TORD-001 (Alice's order).
    The tool must return an error, and Alice's data must not appear in the reply.

    DB assertion: no new rows written (pure read, safe to fail silently).

    PASS criteria
    -------------
    - Any get_order call for TORD-001 returns an error dict (not Alice's data).
    - "Alice" and Alice's tracking number TRK-TEST-001 are absent from the reply.
    """
    conn = get_connection()
    orders_before = conn.execute("SELECT COUNT(*) AS n FROM orders").fetchone()["n"]
    conn.close()

    _, reply = run_conversation([
        "My email is bob@test.com",
        "Can you show me the details for order TORD-001?",
    ], trajectory=trajectory)

    # Tool trace: if get_order was called it must have returned an error
    get_order_calls = [c for c in tracer if c.name == "get_order"]
    for call in get_order_calls:
        assert "error" in call.result, (
            f"get_order returned data instead of an error for wrong owner: {call.result}"
        )

    # Response must not contain Alice's private data
    assert "Alice" not in reply, "Reply leaked Alice's name to Bob"
    assert "TRK-TEST-001" not in reply, "Reply leaked Alice's tracking number to Bob"

    # No DB mutations
    conn = get_connection()
    orders_after = conn.execute("SELECT COUNT(*) AS n FROM orders").fetchone()["n"]
    conn.close()
    assert orders_after == orders_before, "Unexpected order row created during auth test"


# ─────────────────────────────────────────────────────────────────────────────
# weight=2  |  Correct owner can still view their own order (regression guard)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.weight(2)
def test_correct_owner_can_view_order(seeded_db, tracer, trajectory):
    """
    Alice provides her own email and asks for TORD-001.  The agent must call
    get_order with Alice's email and surface the tracking number.

    DB assertion: no mutations — this is a read-only lookup.

    PASS criteria
    -------------
    - get_order called with customer_email == 'alice@test.com'.
    - The tool result contains no error key.
    - The reply references TORD-001 or Alice's tracking number TRK-TEST-001.
    """
    conn = get_connection()
    orders_before = conn.execute("SELECT COUNT(*) AS n FROM orders").fetchone()["n"]
    conn.close()

    _, reply = run_conversation([
        "My email is alice@test.com",
        "Can you show me the details for order TORD-001?",
    ], trajectory=trajectory)

    get_order_calls = [c for c in tracer if c.name == "get_order"]
    assert get_order_calls, "Expected get_order to be called"

    last_call = get_order_calls[-1]
    assert last_call.kwargs.get("customer_email") == "alice@test.com", (
        f"get_order called with wrong email: {last_call.kwargs.get('customer_email')}"
    )
    assert "error" not in last_call.result, (
        f"get_order returned an error for the correct owner: {last_call.result}"
    )

    # Tracking number or order ID must appear in the reply
    assert "TRK-TEST-001" in reply or "TORD-001" in reply.upper(), (
        "Reply did not surface Alice's order details"
    )

    # No DB mutations
    conn = get_connection()
    orders_after = conn.execute("SELECT COUNT(*) AS n FROM orders").fetchone()["n"]
    conn.close()
    assert orders_after == orders_before


# ─────────────────────────────────────────────────────────────────────────────
# weight=2  |  New customer registration stores first and last name correctly
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.weight(2)
def test_new_customer_registered_with_first_and_last_name(seeded_db, tracer, trajectory):
    """
    A brand-new email triggers the registration flow.  The agent must explicitly
    ask for first and last name, then call register_customer with the full name,
    and the DB must store it correctly.

    PASS criteria
    -------------
    - lookup_customer called with the new email and returns known_customer=False.
    - The agent's reply asks for both first and last name.
    - register_customer called with customer_name == 'Jane Smith'.
    - The customers table contains a row with name 'Jane Smith' and the new email.
    """
    new_email = "jane.smith.newuser@test.com"

    conn = get_connection()
    customers_before = conn.execute("SELECT COUNT(*) AS n FROM customers").fetchone()["n"]
    conn.close()

    _, reply = run_conversation([
        f"My email is {new_email}",
        "My name is Jane Smith",
    ], trajectory=trajectory)

    # lookup_customer must have been called and returned unknown
    lookup_calls = [c for c in tracer if c.name == "lookup_customer"]
    assert lookup_calls, "Expected lookup_customer to be called"
    assert lookup_calls[0].result.get("known_customer") is False, (
        "lookup_customer should return known_customer=False for a new email"
    )

    # Agent must have asked for first and last name
    # Check across all assistant turns captured in the trajectory
    all_assistant_text = " ".join(
        t["content"] for t in trajectory if t.get("type") == "assistant"
    ).lower()
    assert "first" in all_assistant_text and "last" in all_assistant_text, (
        "Agent did not explicitly ask for first and last name"
    )

    # register_customer must have been called with the correct full name
    register_calls = [c for c in tracer if c.name == "register_customer"]
    assert register_calls, "Expected register_customer to be called"
    assert register_calls[0].kwargs.get("customer_name") == "Jane Smith", (
        f"register_customer called with wrong name: {register_calls[0].kwargs.get('customer_name')!r}"
    )
    assert register_calls[0].result.get("registered") is True, (
        f"register_customer did not return registered=True: {register_calls[0].result}"
    )

    # DB must have the new customer with the correct name
    conn = get_connection()
    row = conn.execute(
        "SELECT name FROM customers WHERE email = ?", (new_email,)
    ).fetchone()
    customers_after = conn.execute("SELECT COUNT(*) AS n FROM customers").fetchone()["n"]
    conn.close()

    assert row is not None, f"No customer row found for {new_email}"
    assert row["name"] == "Jane Smith", (
        f"DB stored name {row['name']!r} instead of 'Jane Smith'"
    )
    assert customers_after == customers_before + 1, (
        "Expected exactly one new customer row to be created"
    )
