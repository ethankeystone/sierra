"""
EVAL: Promotion Claims
======================
Verifies that the agent correctly issues unique personal discount codes via
claim_promotion when a customer explicitly requests a promotion.

Weight guide
------------
  weight=2  Agent calls claim_promotion and surfaces the code in the reply
            (core requirement — the whole feature breaks without this)
  weight=1  Idempotency: a second request returns the same code
  weight=1  Agent relays timing error when claim is outside the valid window

Domain max score: 4
"""
from __future__ import annotations

import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from db import get_connection
from .helpers import run_conversation


# ── Shared fixture ────────────────────────────────────────────────────────────

@pytest.fixture()
def early_risers_promo(seeded_db):
    """
    Seed an Early Risers promotion with no daily window restriction so the
    claim tests pass regardless of what time they run.
    """
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO promotions "
        "(id, title, code, discount_pct, valid_from, valid_until, description, "
        "daily_start_hour, daily_end_hour) VALUES (?,?,?,?,?,?,?,?,?)",
        (
            "PROMO-EARLY", "Early Risers", "EARLY10", 10,
            "2020-01-01 00:00:00", "2099-12-31 23:59:59",
            "10% off for early shoppers (8–10 AM PT).",
            None, None,  # window disabled in tests so the claim always succeeds
        ),
    )
    conn.commit()
    conn.close()
    return {"id": "PROMO-EARLY", "code": "EARLY10"}


# ─────────────────────────────────────────────────────────────────────────────
# weight=2  |  Agent claims promotion when inside the daily window
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.weight(2)
def test_claim_within_window_succeeds(seeded_db, tracer, trajectory):
    """
    When the Early Risers promo has an 8–10 AM window and the current hour is
    mocked to 9 AM PT, the agent must call claim_promotion and return a code.

    PASS criteria
    -------------
    - claim_promotion called.
    - Tool returns a code (no error).
    - The code appears in the agent's reply.
    """
    from unittest.mock import patch

    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO promotions "
        "(id, title, code, discount_pct, valid_from, valid_until, description, "
        "daily_start_hour, daily_end_hour) VALUES (?,?,?,?,?,?,?,?,?)",
        (
            "PROMO-WINDOW", "Early Risers", "EARLY10", 10,
            "2020-01-01 00:00:00", "2099-12-31 23:59:59",
            "10% off for early shoppers (8–10 AM PT).",
            8, 10,
        ),
    )
    conn.commit()
    conn.close()

    with patch("tools._current_pt_hour", return_value=9):
        _, reply = run_conversation(
            ["Hi! My email is alice@test.com. I'd like to claim the Early Risers promotion please."],
            trajectory=trajectory,
        )

    claim_calls = [c for c in tracer if c.name == "claim_promotion"]
    assert claim_calls, "Expected claim_promotion to be called"

    result = claim_calls[-1].result
    assert "error" not in result, f"claim_promotion returned an error: {result['error']}"
    assert "code" in result

    code = result["code"]
    assert code in reply, (
        f"Expected the generated code {code!r} to appear in the reply.\nReply: {reply}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# weight=2  |  Agent calls claim_promotion and returns a unique code
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.weight(2)
def test_claim_generates_and_surfaces_code(early_risers_promo, tracer, trajectory):
    """
    When a logged-in customer explicitly requests the Early Risers promotion,
    the agent must call claim_promotion and include the generated code in the reply.

    PASS criteria
    -------------
    - claim_promotion called with the correct promo_id.
    - Tool returns a code (no error).
    - The code appears in the agent's reply.
    """
    _, reply = run_conversation(
        [
            "Hi! My email is alice@test.com. I'd like to claim the Early Risers promotion please.",
        ],
        trajectory=trajectory,
    )

    claim_calls = [c for c in tracer if c.name == "claim_promotion"]
    assert claim_calls, "Expected claim_promotion to be called"

    result = claim_calls[-1].result
    assert "error" not in result, f"claim_promotion returned an error: {result['error']}"
    assert "code" in result

    code = result["code"]
    assert code in reply, (
        f"Expected the generated code {code!r} to appear in the reply.\nReply: {reply}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# weight=1  |  Repeat request returns the same code (idempotency)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.weight(1)
def test_claim_idempotent(early_risers_promo, tracer, trajectory):
    """
    If a customer already claimed a promotion, claim_promotion must return the
    same code rather than generating a new one.

    PASS criteria
    -------------
    - claim_promotion called.
    - result.already_claimed is True.
    - The pre-existing code is returned unchanged.
    """
    pre_existing_code = "EARLY10-TESTCODE"
    conn = get_connection()
    conn.execute(
        "INSERT OR IGNORE INTO promotion_claims (id, promo_id, customer_id, code) "
        "VALUES (?,?,?,?)",
        (str(uuid.uuid4()), "PROMO-EARLY", "USR-001", pre_existing_code),
    )
    conn.commit()
    conn.close()

    _, reply = run_conversation(
        [
            "Hey, it's alice@test.com — can I get my Early Risers discount code again?",
        ],
        trajectory=trajectory,
    )

    claim_calls = [c for c in tracer if c.name == "claim_promotion"]
    assert claim_calls, "Expected claim_promotion to be called"

    result = claim_calls[-1].result
    assert result.get("already_claimed") is True, (
        f"Expected already_claimed=True, got: {result}"
    )
    assert result.get("code") == pre_existing_code, (
        f"Expected existing code {pre_existing_code!r}, got {result.get('code')!r}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# weight=1  |  Agent relays timing error when outside the valid window
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.weight(1)
def test_claim_outside_window_error_relayed(seeded_db, tracer, trajectory):
    """
    When the Early Risers promo has a daily window that is currently closed,
    the agent must call claim_promotion, receive the timing error from the tool,
    and relay the restriction to the customer rather than silently ignoring it.

    PASS criteria
    -------------
    - claim_promotion called.
    - Tool returns an error containing 'Pacific Time'.
    - The agent's reply mentions the time restriction.
    """
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO promotions "
        "(id, title, code, discount_pct, valid_from, valid_until, description, "
        "daily_start_hour, daily_end_hour) VALUES (?,?,?,?,?,?,?,?,?)",
        (
            "PROMO-NIGHT-OWL", "Early Risers", "EARLY10", 10,
            "2020-01-01 00:00:00", "2099-12-31 23:59:59",
            "10% off for early shoppers. Available 2:00–3:00 AM Pacific Time only.",
            2, 3,
        ),
    )
    conn.commit()
    conn.close()

    from unittest.mock import patch
    with patch("tools._current_pt_hour", return_value=10):  # 10 AM — outside the 2–3 AM window
        _, reply = run_conversation(
            [
                "Hi, my email is alice@test.com. I'd like to claim the Early Risers promotion please.",
            ],
            trajectory=trajectory,
        )

    claim_calls = [c for c in tracer if c.name == "claim_promotion"]
    assert claim_calls, "Expected claim_promotion to be called"

    result = claim_calls[-1].result
    assert "error" in result and "Pacific Time" in result["error"], (
        f"Expected a Pacific Time timing error, got: {result}"
    )

    reply_lower = reply.lower()
    assert any(phrase in reply_lower for phrase in ("2", "3", "pacific", "am", "time", "window")), (
        f"Agent did not relay the timing restriction in the reply.\nReply: {reply}"
    )
