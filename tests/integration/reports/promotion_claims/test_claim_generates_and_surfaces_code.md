# ✅ test_claim_generates_and_surfaces_code

**Domain:** Promotion Claims  
**Date:** 2026-05-25

---

## What this test checks

> When a logged-in customer explicitly requests the Early Risers promotion,
> the agent must call claim_promotion and include the generated code in the reply.

> PASS criteria
> -------------
> - claim_promotion called with the correct promo_id.
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
    "id": "PROMO-EARLY",
    "title": "Early Risers",
    "code": "EARLY10",
    "discount_pct": 10,
    "applies_to_tags": null,
    "valid_from": "2020-01-01 00:00:00",
    "valid_until": "2099-12-31 23:59:59",
    "description": "10% off for early shoppers (8\u201310 AM PT)."
  }
]
```

**🔧 `claim_promotion`**

**Args:**
```json
{
  "promo_id": "PROMO-EARLY",
  "customer_email": "alice@test.com"
}
```

**Result:**
```json
{
  "code": "EARLY10-DA1C2AA8",
  "discount_pct": 10,
  "already_claimed": false
}
```

> **Sierra Outfitters:** Alice, your personal adventure awaits! Here's your unique promo code for the Early Risers promotion: **EARLY10-DA1C2AA8**. Use it to receive 10% off your next order. 🌄

Your recent excursions have included the TrailBuddy Solo Tent and QuickStep Lightweight Trail Runners. If you need anything else, just let me know!
