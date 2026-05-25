# ✅ test_no_active_promos_no_hallucination

**Domain:** Promotions  
**Date:** 2026-05-25

---

## What this test checks

> When all promotions are expired (active promo deleted), the agent must call
> get_active_promotions, receive an empty list, and NOT invent a promo code.

> PASS criteria
> -------------
> - get_active_promotions called and returns [].
> - No promo code pattern (e.g. ALL-CAPS words like TRAIL20, SAVE10) fabricated.
> - Reply is non-empty.

## Outcome

**PASSED** — all assertions met.

## Conversation

> **User:** Hi, any promotions on right now?

> **Sierra Outfitters:** Onward into the unknown! Currently, there are no active promotions. If you need help charting your course with some gear, feel free to reach out with what you're looking for, and I can help guide you!
