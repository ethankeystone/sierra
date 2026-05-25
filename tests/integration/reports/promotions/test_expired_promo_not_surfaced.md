# ✅ test_expired_promo_not_surfaced

**Domain:** Promotions  
**Date:** 2026-05-25

---

## What this test checks

> The expired promotion (code OLD99) must never appear in any reply,
> regardless of what the customer asks.

> PASS criteria
> -------------
> - 'OLD99' absent from the reply.
> - get_active_promotions called (to confirm the tool ran and filtered correctly).

## Outcome

**PASSED** — all assertions met.

## Conversation

> **User:** Hello, do you have any deals right now?

> **Sierra Outfitters:** Onward into the unknown! 🌄 Right now, we have the Trail Blazer Sale, where you can get 20% off with the code TRAIL20. 🏕️

Can I grab your email address so we can chart the course for any orders or details you might need?
