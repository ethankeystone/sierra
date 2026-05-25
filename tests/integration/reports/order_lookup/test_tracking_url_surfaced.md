# ✅ test_tracking_url_surfaced

**Domain:** Order Lookup  
**Date:** 2026-05-25

---

## What this test checks

> When Alice asks about TORD-001 (which has tracking number TRK-TEST-001),
> the agent should include the full USPS tracking URL in its reply.

> PASS criteria
> -------------
> - get_order called for TORD-001.
> - Reply contains the full USPS tracking URL for TRK-TEST-001.

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

> **Sierra Outfitters:** Base camp confirmed, Alice! 🏕️ Great to have you back on the trail with us. I noticed you've recently equipped yourself with a JetBoil Flash Backpacking Stove System and some TrailBuddy gear. If there's anything else you'd like to explore or if you have questions about your orders, just let me know! 🌲

> **User:** Can you look up order TORD-001 for me?

**🔧 `get_order`**

**Args:**
```json
{
  "order_id": "TORD-001",
  "customer_email": "alice@test.com"
}
```

**Result:**
```json
{
  "order_id": "TORD-001",
  "status": "in_transit",
  "tracking_number": "TRK-TEST-001",
  "tracking_url": "https://tools.usps.com/go/TrackConfirmAction?tLabels=TRK-TEST-001",
  "customer_name": "Alice Anderson",
  "items": [
    {
      "sku": "SOAP001",
      "product_name": "QuickStep Lightweight Trail Runners"
    }
  ]
}
```

> **Sierra Outfitters:** Your order TORD-001 is currently "in transit" with the QuickStep Lightweight Trail Runners trekking towards you. 🏃‍♀️

You can track the progress of your supplies using the following link: 

[Track Your Order](https://tools.usps.com/go/TrackConfirmAction?tLabels=TRK-TEST-001)

If you have more questions or need anything else, just let me know! 🌄
