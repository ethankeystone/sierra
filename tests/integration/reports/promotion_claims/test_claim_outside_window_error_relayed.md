# ✅ test_claim_outside_window_error_relayed

**Domain:** Promotion Claims  
**Date:** 2026-05-25

---

## What this test checks

> When the Early Risers promo has a daily window that is currently closed,
> the agent must call claim_promotion, receive the timing error from the tool,
> and relay the restriction to the customer rather than silently ignoring it.

> PASS criteria
> -------------
> - claim_promotion called.
> - Tool returns an error containing 'Pacific Time'.
> - The agent's reply mentions the time restriction.

## Outcome

**PASSED** — all assertions met.

## Conversation

> **User:** Hi, my email is alice@test.com. I'd like to claim the Early Risers promotion please.

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
    "id": "PROMO-NIGHT-OWL",
    "title": "Early Risers",
    "code": "EARLY10",
    "discount_pct": 10,
    "applies_to_tags": null,
    "valid_from": "2020-01-01 00:00:00",
    "valid_until": "2099-12-31 23:59:59",
    "description": "10% off for early shoppers. Available 2:00\u20133:00 AM Pacific Time only.",
    "daily_window_pt": "02:00\u201303:00 PT"
  }
]
```

**🔧 `claim_promotion`**

**Args:**
```json
{
  "promo_id": "PROMO-NIGHT-OWL",
  "customer_email": "alice@test.com"
}
```

**Result:**
```json
{
  "error": "This promotion is only available from 02:00\u201303:00 Pacific Time."
}
```

> **Sierra Outfitters:** Alice, it looks like the Early Risers promotion 🌅 is only available for claiming between 2:00 and 3:00 AM Pacific Time. Unfortunately, it's outside that window right now, so I can't fetch a personal code for you. 

If you have any other adventures or orders you'd like to prep for, just let me know! 🧭
