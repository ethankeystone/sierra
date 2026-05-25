# ✅ test_claim_within_window_succeeds

**Domain:** Promotion Claims  
**Date:** 2026-05-25

---

## What this test checks

> When the Early Risers promo has an 8–10 AM window and the current hour is
> mocked to 9 AM PT, the agent must call claim_promotion and return a code.

> PASS criteria
> -------------
> - claim_promotion called.
> - Tool returns a code (no error).
> - The code appears in the agent's reply.

## Outcome

**PASSED** — all assertions met.

## Conversation

> **User:** Hi! My email is alice@test.com. I'd like to claim the Early Risers promotion please.

**🔧 `lookup_customer`**

**Args:**
```json
{
  "customer_email": "alice@test.com"
}
```

**Result:**
```json
{
  "known_customer": true,
  "name": "Alice Anderson",
  "email": "alice@test.com",
  "profile": null,
  "recent_orders": [
    {
      "order_id": "W001",
      "status": "delivered",
      "items": [
        "TrailBuddy Solo Tent",
        "JetBoil Flash Backpacking Stove System"
      ]
    },
    {
      "order_id": "TORD-002",
      "status": "delivered",
      "items": [
        "SummitTread Mid Waterproof Hiking Boots"
      ]
    },
    {
      "order_id": "TORD-001",
      "status": "in_transit",
      "items": [
        "QuickStep Lightweight Trail Runners"
      ]
    }
  ]
}
```

**🔧 `get_active_promotions`**

**Args:**
```json
{}
```

**Result:**
```json
[
  {
    "id": "PROMO-ACTIVE",
    "title": "Trail Blazer Sale",
    "code": "TRAIL20",
    "discount_pct": 20,
    "applies_to_tags": "Hiking",
    "valid_from": "2020-01-01 00:00:00",
    "valid_until": "2099-12-31 23:59:59",
    "description": "20% off all hiking gear for early risers."
  },
  {
    "id": "PROMO-WINDOW",
    "title": "Early Risers",
    "code": "EARLY10",
    "discount_pct": 10,
    "applies_to_tags": null,
    "valid_from": "2020-01-01 00:00:00",
    "valid_until": "2099-12-31 23:59:59",
    "description": "10% off for early shoppers (8\u201310 AM PT).",
    "daily_window_pt": "08:00\u201310:00 PT"
  }
]
```

**🔧 `claim_promotion`**

**Args:**
```json
{
  "promo_id": "PROMO-WINDOW",
  "customer_email": "alice@test.com"
}
```

**Result:**
```json
{
  "code": "EARLY10-B9F455D4",
  "discount_pct": 10,
  "already_claimed": false
}
```

> **Sierra Outfitters:** Base camp confirmed, Alice! Your Early Risers promotion is secured. Use your unique code **EARLY10-B9F455D4** to enjoy a 10% discount on your next adventure gear purchase. 🏕️

Let me know if there's any gear you're looking to bring on your next expedition! 🌲
