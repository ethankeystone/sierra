# ✅ test_order_stores_valid_promo_code

**Domain:** Order Placement  
**Date:** 2026-05-25

---

## What this test checks

> When a customer provides a promo code they have already claimed, create_order
> must store it on the order row in the DB.

> Setup: insert a claimed promo code for Alice directly into promotion_claims.

> DB assertions
> -------------
> - A new row in `orders` with promo_code matching the claimed code.

> PASS criteria (additional)
> --------------------------
> - create_order called with the correct promo_code argument.
> - create_order result contains no error key.
> - orders.promo_code == the claimed code.

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

> **Sierra Outfitters:** Onward into the unknown, Alice Anderson! Welcome back to base camp. 🌲

You've been exploring some great gear recently, like the TrailBuddy Solo Tent and the SummitTread Mid Waterproof Hiking Boots. Your QuickStep Lightweight Trail Runners are currently "supplies on the trail" — they're in transit!

If you're gearing up for another expedition or if I can assist with anything else, just let me know!

> **User:** I'd like to order SKU SOAP001. My promo code is TESTDEAL-ALICE01. Go ahead and place it.

**🔧 `create_order`**

**Args:**
```json
{
  "customer_email": "alice@test.com",
  "skus": [
    "SOAP001"
  ],
  "promo_code": "TESTDEAL-ALICE01"
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
  "promo_code": "TESTDEAL-ALICE01"
}
```

> **Sierra Outfitters:** Your gear is set to arrive at base camp, Alice! 🏕️

- **Product**: QuickStep Lightweight Trail Runners
- **Price**: $89.99
- **Promo Code Applied**: TESTDEAL-ALICE01
- **Order ID**: W011
- **Status**: Pending

Your order will soon join your other "supplies on the trail". If there's anything else you need for your expedition, just give me a shout! 🌄
