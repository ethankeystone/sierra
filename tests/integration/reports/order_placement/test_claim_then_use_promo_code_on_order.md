# ✅ test_claim_then_use_promo_code_on_order

**Domain:** Order Placement  
**Date:** 2026-05-25

---

## What this test checks

> Full end-to-end flow: the customer claims a promotion during the conversation,
> then immediately uses the generated code when placing an order — no pre-inserted
> claims, the code is created live by claim_promotion.

> DB assertions
> -------------
> - A new row in `promotion_claims` for Alice.
> - A new row in `orders` with promo_code equal to the code returned by claim_promotion.

> PASS criteria (additional)
> --------------------------
> - claim_promotion called and returns a code with no error.
> - create_order called with that exact code.
> - orders.promo_code in the DB matches the claimed code.

## Outcome

**PASSED** — all assertions met.

## Conversation

> **User:** My email is alice@test.com

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

> **Sierra Outfitters:** Onward into the unknown, Alice Anderson! 🏕️

It looks like you've received some essential gear like the TrailBuddy Solo Tent and a JetBoil Flash Backpacking Stove System recently. Your QuickStep Lightweight Trail Runners are currently on the trail to you.

If there's anything else you need for your next expedition, just let me know! 🏔️

Remember, we have the Trail Blazer Sale ongoing — use code TRAIL20 for 20% off your next adventure. 🌲

> **User:** I'd like to claim the Trail Blazer Sale promotion

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
  }
]
```

**🔧 `claim_promotion`**

**Args:**
```json
{
  "promo_id": "PROMO-ACTIVE",
  "customer_email": "alice@test.com"
}
```

**Result:**
```json
{
  "code": "TRAIL20-EDC8B9BD",
  "discount_pct": 20,
  "already_claimed": false
}
```

> **Sierra Outfitters:** Your exclusive Trail Blazer Sale promotion is ready, Alice! 🎒

- **Promo Code:** TRAIL20-EDC8B9BD
- **Discount:** 20% off

Feel free to use this on your next order for some exciting hiking gear. 🧭

> **User:** Great, now please order SKU SOAP001 for me and use the promo code you just gave me. Go ahead.

**🔧 `create_order`**

**Args:**
```json
{
  "customer_email": "alice@test.com",
  "skus": [
    "SOAP001"
  ],
  "promo_code": "TRAIL20-EDC8B9BD"
}
```

**Result:**
```json
{
  "order_id": "W011",
  "status": "pending",
  "items": [
    {
      "sku": "SOAP001",
      "name": "QuickStep Lightweight Trail Runners",
      "price": 89.99
    }
  ],
  "total": 89.99,
  "promo_code": "TRAIL20-EDC8B9BD"
}
```

> **Sierra Outfitters:** Base camp confirmed, Alice! 🌄

Your order for the "QuickStep Lightweight Trail Runners" has been placed successfully with your exclusive promo code.

- **Order ID:** W011
- **Price:** $89.99
- **Status:** Pending

Your new gear will soon be on the trail to you. Happy adventuring! 🏔️
