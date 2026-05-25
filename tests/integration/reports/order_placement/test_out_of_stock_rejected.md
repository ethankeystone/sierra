# ✅ test_out_of_stock_rejected

**Domain:** Order Placement  
**Date:** 2026-05-25

---

## What this test checks

> Attempting to buy OOS-TEST (inventory=0) must result in create_order
> returning an error, and the DB must remain completely unchanged.

> DB assertions
> -------------
> - No new row in `orders`.
> - OOS product inventory remains 0.

> PASS criteria (additional)
> --------------------------
> - Either create_order is called and returns an error, OR the agent detects
>   OOS via search_products and refuses to proceed (both are valid strategies).
> - Reply communicates the item is unavailable.

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

> **Sierra Outfitters:** Onward into the unknown, Alice! It's great to have you back at Sierra Outfitters. 🏕️ I see your recent adventures included the TrailBuddy Solo Tent and the JetBoil Flash Backpacking Stove System. Looks like your QuickStep Lightweight Trail Runners are currently on the trail, making their way to you. 🌲

If there's anything else you need for your next expedition, just let me know! 🎒 Don't forget, we have a Trail Blazer Sale going on — use code TRAIL20 for 20% off.

> **User:** I'd like to order SKU OOS-TEST — the Perpetually Out-of-Stock Widget. Please place that order.

**🔧 `create_order`**

**Args:**
```json
{
  "customer_email": "alice@test.com",
  "skus": [
    "OOS-TEST"
  ]
}
```

**Result:**
```json
{
  "error": "Out of stock: Perpetually Out-of-Stock Widget"
}
```

> **Sierra Outfitters:** It seems the Perpetually Out-of-Stock Widget is indeed living up to its name and is out of stock at the moment. 🏔️ If there's something else you'd like for your trail gear, or if you have any alternative plans, feel free to let me know! 🌄
