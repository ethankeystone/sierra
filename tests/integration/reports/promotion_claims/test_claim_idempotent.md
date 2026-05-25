# ✅ test_claim_idempotent

**Domain:** Promotion Claims  
**Date:** 2026-05-25

---

## What this test checks

> If a customer already claimed a promotion, claim_promotion must return the
> same code rather than generating a new one.

> PASS criteria
> -------------
> - claim_promotion called.
> - result.already_claimed is True.
> - The pre-existing code is returned unchanged.

## Outcome

**PASSED** — all assertions met.

## Conversation

> **User:** Hey, it's alice@test.com — can I get my Early Risers discount code again?

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
  "code": "EARLY10-TESTCODE",
  "discount_pct": 10,
  "already_claimed": true
}
```

> **Sierra Outfitters:** Onward into the unknown, Alice! Your Early Risers discount code is on hand for your next adventure: **EARLY10-TESTCODE**. Use it to receive a 10% discount.

Looks like your QuickStep Lightweight Trail Runners are still "on the trail" to you as we speak. 🏕️ If you need any more gear for your expeditions, just let me know! 🌄
