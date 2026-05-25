# ✅ test_unknown_order_id_gracefully_handled

**Domain:** Order Lookup  
**Date:** 2026-05-25

---

## What this test checks

> Asking for a non-existent order (W999) should surface a helpful message,
> not crash or hallucinate order details.

> PASS criteria
> -------------
> - get_order called and returns an error dict.
> - Reply does not fabricate order data.
> - Reply is not an empty string.

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

> **Sierra Outfitters:** Onward into the unknown, Alice! 

I see you've been equipped with some excellent gear recently, like the TrailBuddy Solo Tent and SummitTread Mid Waterproof Hiking Boots. Currently, your QuickStep Lightweight Trail Runners are still on the trail, making their way to you.

If you have any expedition questions or need further assistance, just let me know! 🏕️⛺️

> **User:** Can you look up order W999 for me?

**🔧 `get_order`**

**Args:**
```json
{
  "order_id": "W999",
  "customer_email": "alice@test.com"
}
```

**Result:**
```json
{
  "error": "Order W999 not found or does not belong to alice@test.com."
}
```

> **Sierra Outfitters:** It appears that Order W999 is not found in our camp records for your account, Alice. It might belong to a different adventurer, or the order number could be a bit off course. 🌲🧭

If you need help tracking a different order or have other inquiries, feel free to ask!
