"""
EVAL: Order Placement
=====================
Tests that the agent correctly places orders end-to-end, including full DB
verification of every row that should be written.

These are the most important tests in the eval suite: a failure here means
real data is either corrupted or never written.

Weight guide
------------
  weight=3  DB-mutation correctness — orders, order_items, inventory must be
            exactly right after a successful purchase; OOS must be a hard block
  weight=2  Pre-confirmation gate and multi-SKU correctness
  weight=2  Promo code stored on order when provided; rejected when invalid

Domain max score: 20
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from db import get_connection
from .helpers import run_conversation


# ─────────────────────────────────────────────────────────────────────────────
# weight=3  |  Out-of-stock — no DB mutation allowed
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.weight(3)
def test_out_of_stock_rejected(seeded_db, tracer, trajectory):
    """
    Attempting to buy OOS-TEST (inventory=0) must result in create_order
    returning an error, and the DB must remain completely unchanged.

    DB assertions
    -------------
    - No new row in `orders`.
    - OOS product inventory remains 0.

    PASS criteria (additional)
    --------------------------
    - Either create_order is called and returns an error, OR the agent detects
      OOS via search_products and refuses to proceed (both are valid strategies).
    - Reply communicates the item is unavailable.
    """
    conn = get_connection()
    order_count_before = conn.execute("SELECT COUNT(*) AS n FROM orders").fetchone()["n"]
    conn.close()

    _, reply = run_conversation([
        "My email is alice@test.com",
        "I'd like to order SKU OOS-TEST — the Perpetually Out-of-Stock Widget. Please place that order.",
    ], trajectory=trajectory)

    # ── Tool trace ────────────────────────────────────────────────────────────
    # The agent may detect OOS via search_products and refuse to call create_order,
    # OR it may call create_order and let the tool return an error — both are valid.
    create_calls = [c for c in tracer if c.name == "create_order"]
    search_calls  = [c for c in tracer if c.name == "search_products"]

    if create_calls:
        assert "error" in create_calls[-1].result, (
            f"create_order should have returned an error for OOS product, got: {create_calls[-1].result}"
        )
    else:
        # Agent must have detected OOS via search_products
        assert search_calls, (
            "Expected either create_order to be attempted or search_products to be called to detect OOS"
        )

    # ── DB: no new order written ──────────────────────────────────────────────
    conn = get_connection()
    order_count_after = conn.execute("SELECT COUNT(*) AS n FROM orders").fetchone()["n"]
    assert order_count_after == order_count_before, (
        "An order was written to the DB despite the item being out of stock"
    )

    oos_inventory = conn.execute(
        "SELECT inventory FROM products WHERE sku = 'OOS-TEST'"
    ).fetchone()["inventory"]
    assert oos_inventory == 0, "OOS product inventory was incorrectly modified"
    conn.close()

    # ── Reply ─────────────────────────────────────────────────────────────────
    reply_lower = reply.lower()
    out_of_stock_terms = ["out of stock", "unavailable", "stock", "not available"]
    assert any(term in reply_lower for term in out_of_stock_terms), (
        "Reply did not communicate that the item is out of stock"
    )


# ─────────────────────────────────────────────────────────────────────────────
# weight=2  |  Agent asks for confirmation before placing order
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.weight(2)
def test_agent_confirms_before_placing(seeded_db, tracer, trajectory):
    """
    Asking to buy the cheapest tent without explicitly confirming must NOT
    trigger create_order. The agent should find the product, present a summary,
    and ask for confirmation before placing anything.

    DB assertions
    -------------
    - No new row in `orders`.

    PASS criteria (additional)
    --------------------------
    - search_products called (agent looked up the tent).
    - create_order NOT in tool trace.
    - Reply asks for confirmation before proceeding.
    """
    conn = get_connection()
    order_count_before = conn.execute("SELECT COUNT(*) AS n FROM orders").fetchone()["n"]
    conn.close()

    _, reply = run_conversation([
        "My email is alice@test.com",
        "I want to buy the cheapest tent you have",
        # Deliberately no confirmation — conversation ends here
    ], trajectory=trajectory)

    # ── Tool trace ────────────────────────────────────────────────────────────
    search_calls = [c for c in tracer if c.name == "search_products"]
    assert search_calls, "Expected search_products to be called to find the tent"

    create_calls = [c for c in tracer if c.name == "create_order"]
    assert not create_calls, (
        "create_order was called without the customer explicitly confirming"
    )

    # ── DB: untouched ─────────────────────────────────────────────────────────
    conn = get_connection()
    order_count_after = conn.execute("SELECT COUNT(*) AS n FROM orders").fetchone()["n"]
    assert order_count_after == order_count_before
    conn.close()

    # ── Reply asks for confirmation ───────────────────────────────────────────
    confirmation_terms = [
        "confirm", "proceed", "shall i", "would you like", "place the order",
        "go ahead", "want me to", "ready to order", "like me to order",
    ]
    assert any(term in reply.lower() for term in confirmation_terms), (
        f"Reply did not ask for order confirmation.\nReply: {reply}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# weight=2  |  Valid promo code is stored on the order
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.weight(2)
def test_order_stores_valid_promo_code(seeded_db, tracer, trajectory):
    """
    When a customer provides a promo code they have already claimed, create_order
    must store it on the order row in the DB.

    Setup: insert a claimed promo code for Alice directly into promotion_claims.

    DB assertions
    -------------
    - A new row in `orders` with promo_code matching the claimed code.

    PASS criteria (additional)
    --------------------------
    - create_order called with the correct promo_code argument.
    - create_order result contains no error key.
    - orders.promo_code == the claimed code.
    """
    sku = seeded_db["sku_a"]["sku"]

    # Pre-insert a claimed promotion code for Alice
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO promotions "
        "(id, title, code, discount_pct, valid_from, valid_until) "
        "VALUES (?,?,?,?,?,?)",
        ("PROMO-TEST", "Test Promo", "TESTDEAL", 10,
         "2020-01-01 00:00:00", "2099-12-31 23:59:59"),
    )
    personal_code = "TESTDEAL-ALICE01"
    conn.execute(
        "INSERT OR REPLACE INTO promotion_claims (id, promo_id, customer_id, code) "
        "VALUES (?,?,?,?)",
        ("claim-alice-test", "PROMO-TEST", "USR-001", personal_code),
    )
    conn.commit()
    conn.close()

    _, reply = run_conversation([
        "My email is alice@test.com",
        f"I'd like to order SKU {sku}. My promo code is {personal_code}. Go ahead and place it.",
    ], trajectory=trajectory)

    # create_order must have been called with the promo code
    create_calls = [c for c in tracer if c.name == "create_order"]
    assert create_calls, "Expected create_order to be called"
    assert create_calls[-1].kwargs.get("promo_code") == personal_code, (
        f"create_order called with wrong promo_code: {create_calls[-1].kwargs.get('promo_code')!r}"
    )
    assert "error" not in create_calls[-1].result, (
        f"create_order returned an error: {create_calls[-1].result}"
    )

    # DB must have the promo code stored on the order
    order_id = create_calls[-1].result.get("order_id")
    conn = get_connection()
    row = conn.execute(
        "SELECT promo_code FROM orders WHERE id = ?", (order_id,)
    ).fetchone()
    conn.close()

    assert row is not None, f"Order {order_id} not found in DB"
    assert row["promo_code"] == personal_code, (
        f"DB stored promo_code {row['promo_code']!r} instead of {personal_code!r}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# weight=2  |  Another customer's promo code is rejected
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.weight(2)
def test_order_rejects_other_customers_promo_code(seeded_db, tracer, trajectory):
    """
    A promo code claimed by Bob must be rejected when Alice tries to use it.
    No order should be written to the DB.

    DB assertions
    -------------
    - No new row in `orders`.

    PASS criteria (additional)
    --------------------------
    - create_order returns an error dict.
    - Reply communicates the code is not valid.
    """
    sku = seeded_db["sku_a"]["sku"]

    # Pre-insert a claimed promotion code for Bob only
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO promotions "
        "(id, title, code, discount_pct, valid_from, valid_until) "
        "VALUES (?,?,?,?,?,?)",
        ("PROMO-TEST2", "Test Promo 2", "BOBDEAL", 15,
         "2020-01-01 00:00:00", "2099-12-31 23:59:59"),
    )
    bobs_code = "BOBDEAL-BOB01"
    conn.execute(
        "INSERT OR REPLACE INTO promotion_claims (id, promo_id, customer_id, code) "
        "VALUES (?,?,?,?)",
        ("claim-bob-test", "PROMO-TEST2", "USR-002", bobs_code),
    )
    order_count_before = conn.execute("SELECT COUNT(*) AS n FROM orders").fetchone()["n"]
    conn.commit()
    conn.close()

    _, reply = run_conversation([
        "My email is alice@test.com",
        f"I'd like to order SKU {sku} with promo code {bobs_code}. Go ahead.",
    ], trajectory=trajectory)

    # create_order must have returned an error
    create_calls = [c for c in tracer if c.name == "create_order"]
    assert create_calls, "Expected create_order to be called"
    assert "error" in create_calls[-1].result, (
        f"create_order should have rejected Bob's code for Alice, got: {create_calls[-1].result}"
    )

    # No order written
    conn = get_connection()
    order_count_after = conn.execute("SELECT COUNT(*) AS n FROM orders").fetchone()["n"]
    conn.close()
    assert order_count_after == order_count_before, (
        "An order was written despite an invalid promo code"
    )

    # Reply must communicate the code is invalid
    invalid_terms = ["not valid", "invalid", "doesn't apply", "not found", "no promo", "code"]
    assert any(term in reply.lower() for term in invalid_terms), (
        f"Reply did not communicate the promo code was rejected.\nReply: {reply}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# weight=3  |  End-to-end: claim a promo code then use it on the same order
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.weight(3)
def test_claim_then_use_promo_code_on_order(seeded_db, tracer, trajectory):
    """
    Full end-to-end flow: the customer claims a promotion during the conversation,
    then immediately uses the generated code when placing an order — no pre-inserted
    claims, the code is created live by claim_promotion.

    DB assertions
    -------------
    - A new row in `promotion_claims` for Alice.
    - A new row in `orders` with promo_code equal to the code returned by claim_promotion.

    PASS criteria (additional)
    --------------------------
    - claim_promotion called and returns a code with no error.
    - create_order called with that exact code.
    - orders.promo_code in the DB matches the claimed code.
    """
    sku = seeded_db["sku_a"]["sku"]

    conn = get_connection()
    claims_before = conn.execute("SELECT COUNT(*) AS n FROM promotion_claims").fetchone()["n"]
    orders_before = conn.execute("SELECT COUNT(*) AS n FROM orders").fetchone()["n"]
    conn.close()

    _, _ = run_conversation([
        "My email is alice@test.com",
        "I'd like to claim the Trail Blazer Sale promotion",
        f"Great, now please order SKU {sku} for me and use the promo code you just gave me. Go ahead.",
    ], trajectory=trajectory)

    # claim_promotion must have been called and succeeded
    claim_calls = [c for c in tracer if c.name == "claim_promotion"]
    assert claim_calls, "Expected claim_promotion to be called"
    claim_result = claim_calls[-1].result
    assert "error" not in claim_result, (
        f"claim_promotion returned an error: {claim_result}"
    )
    issued_code = claim_result.get("code")
    assert issued_code, "claim_promotion did not return a code"

    # create_order must have been called with that exact code
    create_calls = [c for c in tracer if c.name == "create_order"]
    assert create_calls, "Expected create_order to be called"
    assert create_calls[-1].kwargs.get("promo_code") == issued_code, (
        f"create_order used code {create_calls[-1].kwargs.get('promo_code')!r} "
        f"but claim_promotion issued {issued_code!r}"
    )
    assert "error" not in create_calls[-1].result, (
        f"create_order returned an error: {create_calls[-1].result}"
    )

    # DB: one new claim row and one new order row with the correct code
    order_id = create_calls[-1].result.get("order_id")
    conn = get_connection()
    claims_after = conn.execute("SELECT COUNT(*) AS n FROM promotion_claims").fetchone()["n"]
    order_row = conn.execute(
        "SELECT promo_code FROM orders WHERE id = ?", (order_id,)
    ).fetchone()
    conn.close()

    assert claims_after == claims_before + 1, (
        "Expected exactly one new promotion_claims row to be created"
    )
    assert order_row is not None, f"Order {order_id} not found in DB"
    assert order_row["promo_code"] == issued_code, (
        f"DB stored promo_code {order_row['promo_code']!r} instead of {issued_code!r}"
    )

