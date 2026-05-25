# Sierra Outfitters Agent Chat Loop — System Design

## Overview

A conversational agent loop that handles three domains:
- **Order tracking** — look up order status and shipping info
- **Product recommendations** — suggest products based on user preferences/history
- **Early riser promotions** — surface time-sensitive deals for early shoppers

---

## Architecture

```
User Input
    │
    ▼
┌─────────────────────────────────────┐
│           Agent Loop                │
│  - Maintain conversation history    │
│  - Route intent to tools            │
│  - Format responses                 │
└────────────┬────────────────────────┘
             │  tool_use calls
     ┌───────┴────────────────────┐
     │                            │
     ▼                            ▼
Tool Definitions             Data Layer (SQLite)
  get_order()                  sierra.db
  get_orders_by_customer()       ├── customers  (+ profile)
  search_products()           ├── orders
  get_active_promotions()        ├── order_items
                                 ├── products
                                 ├── product_tags
                                 ├── promotions
                                 ├── promotion_tags
                                 └── sessions
```

---

## Database Layer (SQLite)

### Source Data Structure

**`customer_orders.json`** — each record contains:
- `CustomerName`, `Email` — extracted into the `customers` table on seed
- `OrderNumber` — becomes `orders.id` (# prefix stripped → `W001`)
- `ProductsOrdered` — array of SKUs, expanded into `order_items` rows
- `Status` — normalized on seed (see status mapping below)
- `TrackingNumber` — maps directly to `orders.tracking_number`

**`products.json`** — each record contains:
- `SKU`, `ProductName`, `Inventory`, `Description` — map directly to `products`
- `Tags` — array of strings, expanded into `product_tags` rows

**Fields not in the source data** (absent by design for this mock):
- Orders: `carrier`, `placed_at`, `estimated_delivery`
- Products: `price`, `rating`, `category`
- Order items: `qty`, `unit_price`

### Status Normalization (seed-time mapping)

| JSON value | Condition | DB value |
|---|---|---|
| `delivered` | — | `delivered` |
| `in-transit` | — | `in_transit` |
| `fulfilled` | tracking number present | `shipped` |
| `fulfilled` | no tracking number | `processing` |
| `error` | — | `failed` |

### Schema

```sql
-- Customers (extracted from customer_orders.json at seed time)
CREATE TABLE customers (
    id                  TEXT PRIMARY KEY,  -- e.g. USR-001, generated on seed
    name                TEXT NOT NULL,     -- from CustomerName
    email               TEXT UNIQUE NOT NULL, -- from Email
    profile             TEXT,              -- LLM-generated profile, updated on exit
    profile_updated_at  TEXT,
    created_at          TEXT DEFAULT (datetime('now'))
);

-- Orders (from customer_orders.json)
CREATE TABLE orders (
    id              TEXT PRIMARY KEY,     -- OrderNumber stripped of #, e.g. W001
    customer_id     TEXT NOT NULL REFERENCES customers(id),
    status          TEXT NOT NULL
                    CHECK(status IN (
                        'pending','processing','shipped',
                        'in_transit','out_for_delivery',
                        'delivered','cancelled','failed'
                    )),
    tracking_number TEXT                  -- null if not yet shipped
);

-- Order line items — one row per SKU in ProductsOrdered
CREATE TABLE order_items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id    TEXT NOT NULL REFERENCES orders(id),
    sku         TEXT NOT NULL REFERENCES products(sku)
);

-- Products (from products.json)
CREATE TABLE products (
    sku         TEXT PRIMARY KEY,         -- e.g. SOBP001
    name        TEXT NOT NULL,            -- from ProductName
    inventory   INTEGER DEFAULT 0,        -- from Inventory
    description TEXT                      -- from Description
);

-- Product tags — one row per entry in Tags array
CREATE TABLE product_tags (
    sku     TEXT NOT NULL REFERENCES products(sku),
    tag     TEXT NOT NULL,
    PRIMARY KEY (sku, tag)
);

-- Promotions (no source file — inserted directly at seed time)
CREATE TABLE promotions (
    id           TEXT PRIMARY KEY,        -- e.g. PROMO-2026-05
    title        TEXT NOT NULL,
    code         TEXT UNIQUE NOT NULL,
    discount_pct INTEGER NOT NULL,
    valid_from   TEXT NOT NULL,           -- ISO datetime
    valid_until  TEXT NOT NULL,           -- ISO datetime
    description  TEXT
);

-- Promotion tag targets — one row per tag; no rows = applies to all products
CREATE TABLE promotion_tags (
    promo_id    TEXT NOT NULL REFERENCES promotions(id),
    tag         TEXT NOT NULL,
    PRIMARY KEY (promo_id, tag)
);

-- Sessions — one row per conversation, written on exit
CREATE TABLE sessions (
    id          TEXT PRIMARY KEY,         -- uuid generated at session start
    customer_id TEXT REFERENCES customers(id),  -- null until customer identifies themselves
    summary     TEXT,                     -- LLM-generated summary, written on exit
    started_at  TEXT DEFAULT (datetime('now')),
    ended_at    TEXT
);
```

### Indexes

```sql
CREATE INDEX idx_orders_customer   ON orders(customer_id);
CREATE INDEX idx_order_items_order ON order_items(order_id);
CREATE INDEX idx_order_items_sku   ON order_items(sku);
CREATE INDEX idx_product_tags_tag  ON product_tags(tag);
CREATE INDEX idx_promotions_window    ON promotions(valid_from, valid_until);
CREATE INDEX idx_promotion_tags_tag   ON promotion_tags(tag);
```

---

## Tools

### 1. `get_order`
- **Input**: `order_id: str`, `customer_email: str` (ownership check via email)
- **Query**:
```sql
SELECT
    o.id, o.status, o.tracking_number,
    c.name, c.email,
    i.sku, p.name AS product_name
FROM orders o
JOIN customers c      ON c.id       = o.customer_id
JOIN order_items i    ON i.order_id = o.id
JOIN products p       ON p.sku      = i.sku
WHERE o.id = ? AND c.email = ?
```
- **Output**:
```json
{
  "order_id": "W001",
  "status": "in_transit",
  "tracking_number": "TRK123456789",
  "customer_name": "John Doe",
  "items": [
    { "sku": "SOBP001", "product_name": "Bhavish's Backcountry Blaze Backpack" },
    { "sku": "SOWB004", "product_name": "Beth's Caffeinated Energy Drink" }
  ]
}
```

### 2. `get_orders_by_customer`
- **Input**: `customer_email: str`
- **Query**:
```sql
SELECT
    o.id, o.status, o.tracking_number
FROM orders o
JOIN customers c ON c.id = o.customer_id
WHERE c.email = ?
ORDER BY o.id
```
- **Output**:
```json
[
  { "order_id": "W001", "status": "in_transit",  "tracking_number": "TRK123456789" },
  { "order_id": "W004", "status": "delivered",   "tracking_number": "TRK987654321" }
]
```
- Used when a customer asks "where are my orders?" without supplying an order ID. The agent calls this first, then calls `get_order` on any specific order the customer wants to drill into.

### 3. `search_products`
- **Input**: `tags?: list[str]`, `limit?: int`
- **Query**:
```sql
-- tags filter expanded dynamically as IN (?, ?, ...)
SELECT DISTINCT
    p.sku, p.name, p.description,
    GROUP_CONCAT(pt.tag, ', ') AS tags
FROM products p
JOIN product_tags pt ON pt.sku = p.sku
WHERE p.inventory > 0
  AND (? IS NULL OR pt.tag IN (/* tag placeholders */))
GROUP BY p.sku
ORDER BY p.name
LIMIT ?
```
- **Output**:
```json
[
  {
    "sku": "SOBP001",
    "name": "Bhavish's Backcountry Blaze Backpack",
    "description": "Conquer the wilderness...",
    "tags": "Backpack, Hiking, Adventure, Outdoor Gear"
  }
]
```

### 4. `get_active_promotions`
- **Input**: _(none)_
- **Query**:

Promotion windows are stored and evaluated in **Pacific Time** (America/Los_Angeles), regardless of the server's local timezone. Before querying, the current time is converted to Pacific Time in Python:

```python
from zoneinfo import ZoneInfo
from datetime import datetime

now_pacific = datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%Y-%m-%d %H:%M:%S")
```

```sql
SELECT
    p.id, p.title, p.code, p.discount_pct,
    GROUP_CONCAT(pt.tag, ', ') AS applies_to_tags,
    p.valid_from, p.valid_until, p.description
FROM promotions p
LEFT JOIN promotion_tags pt ON pt.promo_id = p.id
WHERE p.valid_from  <= ?
  AND p.valid_until >= ?
GROUP BY p.id
ORDER BY p.discount_pct DESC
```

The two `?` parameters are both bound to `now_pacific`. Promotion `valid_from`/`valid_until` values are stored as Pacific Time strings (no UTC conversion). DST is handled automatically by `zoneinfo`.
- **Output**:
```json
[
  {
    "id": "PROMO-2026-05",
    "title": "Early Riser: 20% Off Adventure Gear",
    "code": "EARLYBIRD20",
    "discount_pct": 20,
    "applies_to_tags": "Adventure, Hiking",
    "valid_from": "2026-05-22T06:00:00",
    "valid_until": "2026-05-22T10:00:00",
    "description": "Shop before 10am and save 20% on adventure gear."
  }
]
```
- `applies_to_tags` is `null` when no rows exist in `promotion_tags` for that promo (applies to all products).

---

## Agent Loop Design

```python
# Pseudocode

class Session:
    def __init__(self, db):
        self.db = db
        self.id = str(uuid.uuid4())
        self.messages = []
        self._customer_id = None       # private — set at most once via identify()
        self._customer_profile = ""    # private — set at most once via identify()
        db.execute("INSERT INTO sessions (id) VALUES (?)", [self.id])

    def identify(self, email):
        # Idempotent — safe to call on every tool invocation that carries an email.
        # Only the first call does work; subsequent calls are no-ops.
        if self._customer_id is not None:
            return
        row = self.db.execute(
            "SELECT id, profile FROM customers WHERE email = ?", [email]
        ).fetchone()
        if row:
            self._customer_id = row["id"]
            self._customer_profile = row["profile"] or ""
            self.db.execute(
                "UPDATE sessions SET customer_id = ? WHERE id = ?",
                [self._customer_id, self.id]
            )

    def system_prompt(self):
        if self._customer_profile:
            return BASE_PROMPT + "\n\n## Returning Customer\n" + self._customer_profile
        return BASE_PROMPT

    def execute_tools(self, content_blocks):
        results = []
        for block in content_blocks:
            if block.type != "tool_use":
                continue
            if block.name == "get_order":
                self.identify(block.input["customer_email"])
                result = get_order(block.input["order_id"], block.input["customer_email"])
            elif block.name == "get_orders_by_customer":
                self.identify(block.input["customer_email"])
                result = get_orders_by_customer(block.input["customer_email"])
            elif block.name == "search_products":
                result = search_products(block.input.get("tags"), block.input.get("limit"))
            elif block.name == "get_active_promotions":
                result = get_active_promotions()
            results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps(result),
            })
        return results

    def persist(self):
        # Call 1 — generate and store session summary
        summary = client.chat.completions.create(...)  # prompt: summarize customer preferences
        self.db.execute(
            "UPDATE sessions SET summary = ?, ended_at = ? WHERE id = ?", [...]
        )
        # Call 2 — update customer profile (skipped for anonymous sessions)
        if self._customer_id:
            profile = client.chat.completions.create(...)  # prompt: merge old profile + summary
            self.db.execute(
                "UPDATE customers SET profile = ?, profile_updated_at = ? WHERE id = ?", [...]
            )


session = Session(db)

try:
    while True:
        user_input = input("> ")
        if user_input.lower() in ("exit", "quit"):
            break
        session.messages.append({"role": "user", "content": user_input})

        while True:                          # inner tool-use loop
            response = client.chat.completions.create(
                model=MODEL,
                system=session.system_prompt(),
                tools=TOOL_DEFINITIONS,
                messages=session.messages,
            )

            session.messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "end_turn":
                print(response.content[0].text)
                break

            if response.stop_reason == "tool_use":
                tool_results = session.execute_tools(response.content)
                session.messages.append({"role": "user", "content": tool_results})
                # loop continues — model sees tool results and responds
finally:
    session.persist()   # always runs — clean exit, Ctrl-C, or crash
```

### System Prompt Goals
- Greet users and offer the three domains
- Always verify order ownership before returning order details
- Surface active early riser promos proactively if they exist
- Keep responses concise; use bullet points for order/product info

### Persona
The model should maintain an outdoor adventure personality throughout the entire conversation:
- Use adventure-themed language ("Onward into the unknown", "Let's chart your course", "Base camp confirmed", "Gear secured")
- Use relevant emojis naturally (🏔️ 🎒 🧭 🌲 ✅ 🏕️)
- Frame domain responses in adventure terms:
  - Order delivered → "Your gear has arrived at base camp"
  - Order in transit → "Your supplies are on the trail"
  - Product recommendation → "Here's what we'd pack for your next expedition"
  - Active promotion → "A rare weather window — grab this before it closes"
- Tone should be enthusiastic but not overwhelming — like a knowledgeable trail guide, not a hype man

---

## Session Lifecycle

### Session start
1. Generate a new session `id` (uuid) and insert a row into `sessions` with `customer_id = NULL`
2. Initialize `customer_profile = ""` — profile is absent until the customer identifies

### Customer identification (mid-session or at first prompt)
When the customer provides their email, `on_customer_identified(email)` is called **exactly once**:
- Looks up the customer and sets `session.customer_id`
- Loads `customers.profile` into `customer_profile` (empty string if none exists)
- From this point forward, `build_system_prompt()` returns `BASE_PROMPT + profile`
- `BASE_PROMPT` is never mutated; `customer_profile` is never changed again this session

This keeps a strict separation: agent behavior lives in `BASE_PROMPT`, customer context lives in `customer_profile`, and the conversation history (`messages`) contains only real conversational turns — no synthetic injections.

Turns that occurred before identification proceed without profile context; this is acceptable since those turns are anonymous by definition.

### During conversation
- Conversation history lives entirely in the in-memory `messages` list
- No writes to the DB mid-session

### On exit
Triggered by the user typing `exit` / `quit`, a keyboard interrupt (Ctrl-C), or any unhandled exception — the exit logic runs inside a `try/finally` block so it fires even on unexpected termination. Two sequential API calls are made:

**Call 1 — Generate session summary**
```
Prompt: "Summarize this conversation focusing on what you learned about the customer's
         preferences. Extract: events or activities they're shopping for,
         reasons for purchase, and any specific product interests mentioned."
Input:  full messages list
Output: written to sessions.summary, sessions.ended_at
```

**Call 2 — Update customer profile**
```
Prompt: "Given this existing customer profile and this new session summary,
         write a single updated profile focused on their preferences: activities,
         events they shop for, and reasons for buying. Merge new information with existing
         — do not discard prior preferences unless the customer explicitly changed them."
Input:  customers.profile (may be null) + sessions.summary from Call 1
Output: written to customers.profile, customers.profile_updated_at
```

Both calls use the same model as the chat loop.

### On next session start
When the customer identifies, `on_customer_identified` queries:
```sql
SELECT id, profile FROM customers WHERE email = ?
```
If `profile` is non-null, it is composed into the system prompt via `build_system_prompt()` for all subsequent API calls in that session.

---

## File Structure

```
sierra/
├── design.md                  ← this file
├── agent.py                   # main chat loop
├── tools.py                   # tool handler + SQL queries
├── db.py                      # SQLite connection + schema init
├── seed.py                    # loads customer_orders.json + products.json → sierra.db
├── customer_orders.json       # source data: orders + customers
├── products.json              # source data: products + tags
├── sierra.db                  # SQLite database (git-ignored)
└── requirements.txt
```

---


## Open Questions

1. Security? Prevent users from looking at other users orders / information.
2. Truncate or compress complete chat history sent to the model
