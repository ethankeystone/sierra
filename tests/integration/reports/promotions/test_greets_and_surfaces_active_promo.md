# ✅ test_greets_and_surfaces_active_promo

**Domain:** Promotions  
**Date:** 2026-05-25

---

## What this test checks

> On the very first user message, the agent must call get_active_promotions
> and mention the active deal (code TRAIL20) in the reply.

> PASS criteria
> -------------
> - get_active_promotions called.
> - 'TRAIL20' (or the promo title 'Trail Blazer Sale') present in the reply.

## Outcome

**PASSED** — all assertions met.

## Conversation

> **User:** Hello

> **Sierra Outfitters:** Onward into the unknown! We're currently running the Trail Blazer Sale with a 20% discount using the code TRAIL20. 🏞️ Can I have your email to get your adventure started?
