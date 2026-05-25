# ✅ test_no_email_no_order_data

**Domain:** Auth  
**Date:** 2026-05-25

---

## What this test checks

> Sending an order-lookup request without providing an email must not trigger
> any order tool.  The agent must ask for an email address first.

> PASS criteria
> -------------
> - Neither get_order nor get_orders_by_customer appears in the tool trace.
> - The final reply prompts the user to supply their email.

## Outcome

**PASSED** — all assertions met.

## Conversation

> **User:** Show me my order TORD-001

> **Sierra Outfitters:** Onward into the unknown! Before we dive into the details of your order, could you please provide your email address? This will help me fetch your order information and ensure your adventure goes off without a hitch. 🏔️
