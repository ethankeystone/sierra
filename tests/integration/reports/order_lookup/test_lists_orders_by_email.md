# ✅ test_lists_orders_by_email

**Domain:** Order Lookup  
**Date:** 2026-05-25

---

## What this test checks

> After Alice identifies, asking 'what are my orders?' should call
> get_orders_by_customer and surface both TORD-001 and TORD-002 in the reply.

> DB assertion: row count unchanged.

> PASS criteria
> -------------
> - get_orders_by_customer called with alice@test.com.
> - Reply mentions TORD-001 and TORD-002 (or their statuses: in_transit / delivered).

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

> **Sierra Outfitters:** Welcome back, Alice Anderson! 🎒 It's great to see you again. It looks like you recently received some fantastic gear, including a TrailBuddy Solo Tent and a JetBoil Flash Backpacking Stove System. 🏕️ If you're keen to know where your QuickStep Lightweight Trail Runners are, feel free to ask!

Onward into the unknown, let me know if you need any help exploring our latest gear or promotions! 🌲

> **User:** What are all my orders?

**🔧 `get_orders_by_customer`**

**Args:**
```json
{
  "customer_email": "alice@test.com"
}
```

**Result:**
```json
[
  {
    "order_id": "TORD-001",
    "status": "in_transit",
    "tracking_number": "TRK-TEST-001",
    "tracking_url": "https://tools.usps.com/go/TrackConfirmAction?tLabels=TRK-TEST-001"
  },
  {
    "order_id": "TORD-002",
    "status": "delivered",
    "tracking_number": "TRK-TEST-002",
    "tracking_url": "https://tools.usps.com/go/TrackConfirmAction?tLabels=TRK-TEST-002"
  },
  {
    "order_id": "W001",
    "status": "delivered",
    "tracking_number": "TRK123456789",
    "tracking_url": "https://tools.usps.com/go/TrackConfirmAction?tLabels=TRK123456789"
  }
]
```

> **Sierra Outfitters:** Here are your recent orders, Alice:

1. **Order ID:** TORD-001
   - **Status:** In Transit
   - **Tracking Number:** TRK-TEST-001
   - **Tracking URL:** [https://tools.usps.com/go/TrackConfirmAction?tLabels=TRK-TEST-001](https://tools.usps.com/go/TrackConfirmAction?tLabels=TRK-TEST-001)

2. **Order ID:** TORD-002
   - **Status:** Delivered
   - **Tracking Number:** TRK-TEST-002
   - **Tracking URL:** [https://tools.usps.com/go/TrackConfirmAction?tLabels=TRK-TEST-002](https://tools.usps.com/go/TrackConfirmAction?tLabels=TRK-TEST-002)

3. **Order ID:** W001
   - **Status:** Delivered
   - **Tracking Number:** TRK123456789
   - **Tracking URL:** [https://tools.usps.com/go/TrackConfirmAction?tLabels=TRK123456789](https://tools.usps.com/go/TrackConfirmAction?tLabels=TRK123456789)

Your QuickStep Lightweight Trail Runners are on their way. Feel free to follow the trail to check their journey! 🧭
