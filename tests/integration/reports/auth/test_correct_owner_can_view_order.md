# ✅ test_correct_owner_can_view_order

**Domain:** Auth  
**Date:** 2026-05-25

---

## What this test checks

> Alice provides her own email and asks for TORD-001.  The agent must call
> get_order with Alice's email and surface the tracking number.

> DB assertion: no mutations — this is a read-only lookup.

> PASS criteria
> -------------
> - get_order called with customer_email == 'alice@test.com'.
> - The tool result contains no error key.
> - The reply references TORD-001 or Alice's tracking number TRK-TEST-001.

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

> **Sierra Outfitters:** Onward into the unknown, Alice Anderson! 🌄

I see that your QuickStep Lightweight Trail Runners are currently "supplies on the trail" and should be arriving soon. You recently received the TrailBuddy Solo Tent and JetBoil Flash Backpacking Stove System — two great choices for any expedition! 🏕️

If there's anything else you need to explore or any orders you'd like to check on, just let me know! Don't forget, we have a Trail Blazer Sale with the code TRAIL20 for 20% off if you're planning your next order.

> **User:** Can you show me the details for order TORD-001?

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

> **Sierra Outfitters:** Here's the trail report for order **TORD-001**:

- **Status**: In Transit 🏔️
- **Item**: QuickStep Lightweight Trail Runners
- **Tracking**: [Track your order](https://tools.usps.com/go/TrackConfirmAction?tLabels=TRK-TEST-001)

The trail runners are making their way to base camp. 🏕️ If you have any more questions or need further assistance, feel free to ask!
