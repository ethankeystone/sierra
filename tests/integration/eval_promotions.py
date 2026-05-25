"""
EVAL: Promotions
================
Verifies that Sierra Outfitters proactively surfaces active promotions at session start,
correctly filters out expired ones, and does not hallucinate promo codes when
no active promotions exist.

All tests are read-only.

Weight guide
------------
  weight=2  Active promo surfaced on first turn; expired promo never mentioned
            (failing either misleads the customer or creates false urgency)
  weight=1  No hallucination when promo table is empty

Domain max score: 5
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from db import get_connection
from .helpers import run_conversation


# ─────────────────────────────────────────────────────────────────────────────
# weight=2  |  Active promo is surfaced on first turn
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.weight(2)
def test_greets_and_surfaces_active_promo(seeded_db, tracer, trajectory):
    """
    On the very first user message, the agent must call get_active_promotions
    and mention the active deal (code TRAIL20) in the reply.

    PASS criteria
    -------------
    - get_active_promotions called.
    - 'TRAIL20' (or the promo title 'Trail Blazer Sale') present in the reply.
    """
    _, reply = run_conversation(["Hello"], trajectory=trajectory)

    promo_calls = [c for c in tracer if c.name == "get_active_promotions"]
    assert promo_calls, "Expected get_active_promotions to be called on first turn"

    # Active promo code or title must appear
    assert "TRAIL20" in reply or "Trail Blazer" in reply, (
        f"Active promo not mentioned in reply. Reply was:\n{reply}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# weight=2  |  Expired promo never appears in the reply
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.weight(2)
def test_expired_promo_not_surfaced(seeded_db, tracer, trajectory):
    """
    The expired promotion (code OLD99) must never appear in any reply,
    regardless of what the customer asks.

    PASS criteria
    -------------
    - 'OLD99' absent from the reply.
    - get_active_promotions called (to confirm the tool ran and filtered correctly).
    """
    _, reply = run_conversation(["Hello, do you have any deals right now?"], trajectory=trajectory)

    promo_calls = [c for c in tracer if c.name == "get_active_promotions"]
    assert promo_calls, "Expected get_active_promotions to be called"

    # Expired code must not leak through
    assert "OLD99" not in reply, (
        "Expired promotion code OLD99 appeared in the reply"
    )

    # Expired title must not leak through
    assert "Ancient Deal" not in reply, (
        "Expired promotion title appeared in the reply"
    )


# ─────────────────────────────────────────────────────────────────────────────
# weight=1  |  No active promos → no hallucinated promo codes
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.weight(1)
def test_no_active_promos_no_hallucination(seeded_db, tracer, trajectory):
    """
    When all promotions are expired (active promo deleted), the agent must call
    get_active_promotions, receive an empty list, and NOT invent a promo code.

    PASS criteria
    -------------
    - get_active_promotions called and returns [].
    - No promo code pattern (e.g. ALL-CAPS words like TRAIL20, SAVE10) fabricated.
    - Reply is non-empty.
    """
    # Remove the active promo so the table has only expired rows
    conn = get_connection()
    conn.execute("DELETE FROM promotion_tags WHERE promo_id = 'PROMO-ACTIVE'")
    conn.execute("DELETE FROM promotions WHERE id = 'PROMO-ACTIVE'")
    conn.commit()
    conn.close()

    _, reply = run_conversation(["Hi, any promotions on right now?"], trajectory=trajectory)

    promo_calls = [c for c in tracer if c.name == "get_active_promotions"]
    assert promo_calls, "Expected get_active_promotions to be called"
    assert promo_calls[-1].result == [], (
        f"Expected empty promotions list, got: {promo_calls[-1].result}"
    )

    assert reply.strip(), "Reply should not be empty"

    # Must not contain a fabricated promo code (uppercase word 4+ chars, no spaces)
    import re
    code_pattern = re.compile(r"\b[A-Z]{4,}[0-9]*\b")
    fabricated = code_pattern.findall(reply)
    # Filter out common non-code words
    noise = {"YOUR", "GEAR", "BEST", "FREE", "SALE", "FROM", "WITH", "THIS",
             "HAVE", "ALSO", "SHOP", "FIND", "MORE", "JUST", "STAY", "BACK",
             "LOOK", "KEEP", "THEN", "THAT", "THAN", "BEEN", "WILL", "WHAT"}
    real_codes = [w for w in fabricated if w not in noise]
    assert not real_codes, (
        f"Agent may have hallucinated promo code(s): {real_codes}\nReply: {reply}"
    )
