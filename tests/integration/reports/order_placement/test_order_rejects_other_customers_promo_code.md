# ✅ test_order_rejects_other_customers_promo_code

**Domain:** Order Placement  
**Date:** 2026-05-25

---

## What this test checks

> A promo code claimed by Bob must be rejected when Alice tries to use it.
> No order should be written to the DB.

> DB assertions
> -------------
> - No new row in `orders`.

> PASS criteria (additional)
> --------------------------
> - create_order returns an error dict.
> - Reply communicates the code is not valid.

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

> **Sierra Outfitters:** Welcome back, Alice! 🌲 It looks like you've recently received some gear, like the TrailBuddy Solo Tent and JetBoil Flash Backpacking Stove System. Plus, your QuickStep Lightweight Trail Runners are still on the trail to your doorstep.

Don't forget, we have some active promotions you might be interested in: 
- Trail Blazer Sale for 20% off with code: TRAIL20
- Test Promo 2 for 15% off with code: BOBDEAL

If you need to place an order or have any questions, just let me know! 🏕️

> **User:** I'd like to order SKU SOAP001 with promo code BOBDEAL-BOB01. Go ahead.

**🔧 `create_order`**

**Args:**
```json
{
  "customer_email": "alice@test.com",
  "skus": [
    "SOAP001"
  ],
  "promo_code": "BOBDEAL-BOB01"
}
```

**Result:**
```json
{
  "error": "Promo code 'BOBDEAL-BOB01' is not valid for this account."
}
```

> **Sierra Outfitters:** It seems the promo code "BOBDEAL-BOB01" is not valid for your account. 😕 Would you like to proceed with the order without a promo code, or is there anything else I can assist you with? 🏔️
