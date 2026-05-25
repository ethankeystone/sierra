# ✅ test_agent_asks_for_email_first

**Domain:** Order Lookup  
**Date:** 2026-05-25

---

## What this test checks

> A bare 'where are my orders?' without an email must not trigger any
> order lookup tool.  The agent should prompt for the customer's email.

> PASS criteria
> -------------
> - No order tool called.
> - Reply asks for email.

## Outcome

**PASSED** — all assertions met.

## Conversation

> **User:** Where are my orders?

> **Sierra Outfitters:** Let's chart your course to order discovery! I'll need your email address to locate your orders. Could you please provide it?
