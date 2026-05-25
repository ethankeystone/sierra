from __future__ import annotations

import abc
import sqlite3
import uuid
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from db import init_schema


_pt_hour_override: int | None = None

def set_pt_hour_override(hour: int | None) -> None:
    global _pt_hour_override
    _pt_hour_override = hour

def _current_pt_hour() -> int:
    if _pt_hour_override is not None:
        return _pt_hour_override
    return datetime.now(ZoneInfo("America/Los_Angeles")).hour


def _in_daily_window(start_hour: int | None, end_hour: int | None) -> bool:
    """Return True if the current PT hour falls within [start_hour, end_hour)."""
    if start_hour is None or end_hour is None:
        return True
    return start_hour <= _current_pt_hour() < end_hour


def _next_customer_id(conn: sqlite3.Connection) -> str:
    row = conn.execute("SELECT MAX(CAST(SUBSTR(id, 5) AS INTEGER)) AS n FROM customers").fetchone()
    return f"USR-{(row['n'] or 0) + 1:03d}"


def _next_order_id(conn: sqlite3.Connection) -> str:
    row = conn.execute("SELECT MAX(CAST(SUBSTR(id, 2) AS INTEGER)) AS n FROM orders").fetchone()
    return f"W{(row['n'] or 0) + 1:03d}"


# ── Base ──────────────────────────────────────────────────────────────────────

class Tool(abc.ABC):
    """A single callable tool: schema + implementation in one place."""

    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema object for the function's arguments
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def openai_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    @abc.abstractmethod
    def execute(self, **kwargs) -> Any:
        ...


# ── Tool implementations ───────────────────────────────────────────────────────

def _usps_tracking_url(tracking_number: str | None) -> str | None:
    if not tracking_number:
        return None
    return f"https://tools.usps.com/go/TrackConfirmAction?tLabels={tracking_number}"


class GetOrderTool(Tool):
    name = "get_order"
    description = (
        "Look up a specific order by order ID. "
        "Verifies ownership via the customer's email — only returns the order "
        "if the email matches the account that placed it."
    )
    parameters = {
        "type": "object",
        "properties": {
            "order_id": {
                "type": "string",
                "description": "The order ID (e.g. W001). Strip any leading # before calling.",
            },
            "customer_email": {
                "type": "string",
                "description": "Customer email address used for ownership verification.",
            },
        },
        "required": ["order_id", "customer_email"],
    }

    def execute(self, order_id: str, customer_email: str) -> dict[str, Any]:
        order_id = order_id.lstrip("#")
        rows = self.conn.execute(
            """
            SELECT
                o.id, o.status, o.tracking_number,
                c.name, c.email,
                i.sku, p.name AS product_name
            FROM orders o
            JOIN customers c   ON c.id       = o.customer_id
            JOIN order_items i ON i.order_id = o.id
            JOIN products p    ON p.sku      = i.sku
            WHERE o.id = ? AND c.email = ?
            """,
            (order_id, customer_email),
        ).fetchall()

        if not rows:
            return {"error": f"Order {order_id} not found or does not belong to {customer_email}."}

        first = rows[0]
        tracking_number = first["tracking_number"]
        tracking_url = _usps_tracking_url(tracking_number)
        return {
            "order_id": first["id"],
            "status": first["status"],
            "tracking_number": tracking_number,
            "tracking_url": tracking_url,
            "customer_name": first["name"],
            "items": [{"sku": r["sku"], "product_name": r["product_name"]} for r in rows],
        }


class GetOrdersByCustomerTool(Tool):
    name = "get_orders_by_customer"
    description = (
        "List all orders for a customer by email. "
        "Call this first when a customer asks about their orders without specifying an order ID, "
        "then offer to drill into a specific one with get_order."
    )
    parameters = {
        "type": "object",
        "properties": {
            "customer_email": {
                "type": "string",
                "description": "Customer email address.",
            },
        },
        "required": ["customer_email"],
    }

    def execute(self, customer_email: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT o.id, o.status, o.tracking_number
            FROM orders o
            JOIN customers c ON c.id = o.customer_id
            WHERE c.email = ?
            ORDER BY o.id
            """,
            (customer_email,),
        ).fetchall()
        return [
            {
                "order_id": r["id"],
                "status": r["status"],
                "tracking_number": r["tracking_number"],
                "tracking_url": _usps_tracking_url(r["tracking_number"]),
            }
            for r in rows
        ]


class SearchProductsTool(Tool):
    name = "search_products"
    description = (
        "Search in-stock products, optionally filtered by one or more tags. "
        "Returns products matching ANY of the provided tags. "
        "Omit tags to browse all available products."
    )

    def __init__(self, conn: sqlite3.Connection, tags: list[str] | None = None):
        super().__init__(conn)
        tags = tags or []
        self.parameters = {
            "type": "object",
            "properties": {
                "tags": {
                    "type": "array",
                    "items": {"type": "string", "enum": tags},
                    "description": (
                        "Optional tag filters — must be values from the enum. "
                        "Products matching any tag are returned."
                    ),
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results to return. Defaults to 30.",
                    "default": 30,
                },
            },
        }

    def execute(self, tags: list[str] | None = None, limit: int | None = None) -> list[dict[str, Any]]:
        if limit is None:
            limit = 30

        if tags:
            placeholders = ",".join("?" * len(tags))
            rows = self.conn.execute(
                f"""
                SELECT p.sku, p.name, p.price, p.description,
                    GROUP_CONCAT(pt.tag, ', ') AS tags
                FROM products p
                JOIN product_tags pt ON pt.sku = p.sku
                WHERE p.inventory > 0
                  AND p.sku IN (
                      SELECT sku FROM product_tags WHERE tag IN ({placeholders})
                  )
                GROUP BY p.sku
                ORDER BY p.name
                LIMIT ?
                """,
                tags + [limit],
            ).fetchall()
        else:
            rows = self.conn.execute(
                """
                SELECT p.sku, p.name, p.price, p.description,
                    GROUP_CONCAT(pt.tag, ', ') AS tags
                FROM products p
                JOIN product_tags pt ON pt.sku = p.sku
                WHERE p.inventory > 0
                GROUP BY p.sku
                ORDER BY p.name
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [
            {
                "sku": r["sku"],
                "name": r["name"],
                "price": r["price"],
                "description": r["description"],
                "tags": r["tags"],
            }
            for r in rows
        ]


class GetActivePromotionsTool(Tool):
    name = "get_active_promotions"
    description = (
        "Retrieve all promotions valid today. "
        "Promotions with a daily_window_pt field are only claimable during that hour range — "
        "claim_promotion enforces the window and will return an error outside it."
    )
    parameters = {
        "type": "object",
        "properties": {},
    }

    def execute(self) -> list[dict[str, Any]]:
        now_str = datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%Y-%m-%d %H:%M:%S")
        rows = self.conn.execute(
            """
            SELECT
                p.id, p.title, p.code, p.discount_pct,
                GROUP_CONCAT(pt.tag, ', ') AS applies_to_tags,
                p.valid_from, p.valid_until, p.description,
                p.daily_start_hour, p.daily_end_hour
            FROM promotions p
            LEFT JOIN promotion_tags pt ON pt.promo_id = p.id
            WHERE p.valid_from  <= ?
              AND p.valid_until >= ?
            GROUP BY p.id
            ORDER BY p.discount_pct DESC
            """,
            (now_str, now_str),
        ).fetchall()
        result = []
        for r in rows:
            start_hour = r["daily_start_hour"]
            end_hour   = r["daily_end_hour"]
            entry = {
                "id": r["id"],
                "title": r["title"],
                "code": r["code"],
                "discount_pct": r["discount_pct"],
                "applies_to_tags": r["applies_to_tags"],
                "valid_from": r["valid_from"],
                "valid_until": r["valid_until"],
                "description": r["description"],
            }
            if start_hour is not None and end_hour is not None:
                entry["daily_window_pt"] = f"{start_hour:02d}:00–{end_hour:02d}:00 PT"
            result.append(entry)
        return result


class LookupCustomerTool(Tool):
    name = "lookup_customer"
    description = (
        "Load a customer's account by email. "
        "Call this immediately whenever the customer provides their email address, "
        "even if they haven't asked about orders yet. "
        "This personalises the session and ensures it is saved against their account."
    )
    parameters = {
        "type": "object",
        "properties": {
            "customer_email": {
                "type": "string",
                "description": "The email address the customer just provided.",
            },
        },
        "required": ["customer_email"],
    }

    def execute(self, customer_email: str) -> dict[str, Any]:
        customer = self.conn.execute(
            "SELECT id, name, email, profile FROM customers WHERE email = ?",
            (customer_email,),
        ).fetchone()

        if not customer:
            return {"known_customer": False, "email": customer_email}

        # Fetch recent orders with product names (up to 5 items across last 3 orders)
        order_rows = self.conn.execute(
            """
            SELECT o.id AS order_id, o.status, p.name AS product_name
            FROM orders o
            JOIN order_items oi ON oi.order_id = o.id
            JOIN products p     ON p.sku       = oi.sku
            WHERE o.customer_id = ?
            ORDER BY o.id DESC
            LIMIT 5
            """,
            (customer["id"],),
        ).fetchall()

        # Group items by order
        orders: dict[str, dict[str, Any]] = {}
        for r in order_rows:
            if r["order_id"] not in orders:
                orders[r["order_id"]] = {"order_id": r["order_id"], "status": r["status"], "items": []}
            orders[r["order_id"]]["items"].append(r["product_name"])

        return {
            "known_customer": True,
            "name": customer["name"],
            "email": customer["email"],
            "profile": customer["profile"] or None,
            "recent_orders": list(orders.values()),
        }


class RegisterCustomerTool(Tool):
    name = "register_customer"
    description = (
        "Create a new customer account with the given name and email. "
        "Only call this after lookup_customer has confirmed the email is not in the system "
        "and the customer has provided their full name."
    )
    parameters = {
        "type": "object",
        "properties": {
            "customer_email": {
                "type": "string",
                "description": "The customer's email address.",
            },
            "customer_name": {
                "type": "string",
                "description": "The customer's full name.",
            },
        },
        "required": ["customer_email", "customer_name"],
    }

    def execute(self, customer_email: str, customer_name: str) -> dict[str, Any]:
        existing = self.conn.execute(
            "SELECT id FROM customers WHERE email = ?", (customer_email,)
        ).fetchone()
        if existing:
            return {"error": "An account with that email already exists."}

        customer_id = _next_customer_id(self.conn)
        self.conn.execute(
            "INSERT INTO customers (id, name, email) VALUES (?, ?, ?)",
            (customer_id, customer_name, customer_email),
        )
        self.conn.commit()
        return {"registered": True, "customer_id": customer_id, "name": customer_name, "email": customer_email}


class CreateOrderTool(Tool):
    name = "create_order"
    description = (
        "Place a new order for a customer. "
        "The customer must already have an account — use lookup_customer and register_customer first if needed. "
        "Validates that every SKU exists and has stock before writing anything. "
        "Always confirm the exact items and total price with the customer before calling this tool."
    )
    parameters = {
        "type": "object",
        "properties": {
            "customer_email": {
                "type": "string",
                "description": "Customer email address.",
            },
            "skus": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Ordered list of product SKUs to include in the order.",
            },
            "promo_code": {
                "type": "string",
                "description": (
                    "Optional personal promotion code to attach to the order. "
                    "Must be a code previously issued to this customer via claim_promotion. "
                    "Only one code per order is allowed."
                ),
            },
        },
        "required": ["customer_email", "skus"],
    }

    def execute(self, customer_email: str, skus: list[str], promo_code: str | None = None) -> dict[str, Any]:
        # 1. Customer must exist
        row = self.conn.execute(
            "SELECT id FROM customers WHERE email = ?", (customer_email,)
        ).fetchone()

        if not row:
            return {"error": "No account found for that email. Please register first."}
        customer_id = row["id"]

        # 2. Validate promo code belongs to this customer
        if promo_code:
            claim = self.conn.execute(
                "SELECT code FROM promotion_claims WHERE code = ? AND customer_id = ?",
                (promo_code, customer_id),
            ).fetchone()
            if not claim:
                return {"error": f"Promo code {promo_code!r} is not valid for this account."}

        # 3. Validate every SKU before touching orders
        invalid_skus, out_of_stock, items = [], [], []
        for sku in skus:
            product = self.conn.execute(
                "SELECT sku, name, price, inventory FROM products WHERE sku = ?", (sku,)
            ).fetchone()
            if not product:
                invalid_skus.append(sku)
            elif product["inventory"] <= 0:
                out_of_stock.append(product["name"])
            else:
                items.append(dict(product))

        if invalid_skus:
            return {"error": f"Unknown SKU(s): {', '.join(invalid_skus)}"}
        if out_of_stock:
            return {"error": f"Out of stock: {', '.join(out_of_stock)}"}

        # 4. Generate next order ID (W001, W002, …)
        order_id = _next_order_id(self.conn)

        # 5. Write order + items, decrement inventory
        self.conn.execute(
            "INSERT INTO orders (id, customer_id, status, promo_code) VALUES (?, ?, 'pending', ?)",
            (order_id, customer_id, promo_code),
        )
        for item in items:
            self.conn.execute(
                "INSERT INTO order_items (order_id, sku) VALUES (?, ?)",
                (order_id, item["sku"]),
            )
            self.conn.execute(
                "UPDATE products SET inventory = inventory - 1 WHERE sku = ?",
                (item["sku"],),
            )
        self.conn.commit()

        total = round(sum(item["price"] for item in items), 2)
        return {
            "order_id": order_id,
            "status": "pending",
            "items": [
                {"sku": item["sku"], "name": item["name"], "price": item["price"]}
                for item in items
            ],
            "total": total,
            "promo_code": promo_code,
        }


class ClaimPromotionTool(Tool):
    name = "claim_promotion"
    description = (
        "Issue a unique personal discount code for an active promotion. "
        "For the Early Risers promotion, only call this when the customer explicitly requests it — "
        "the tool enforces the 8:00–10:00 AM Pacific Time window automatically. "
        "Returns the same code if the customer already claimed this promotion (idempotent)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "promo_id": {
                "type": "string",
                "description": "The promotion ID to claim (from get_active_promotions).",
            },
            "customer_email": {
                "type": "string",
                "description": "The customer's email address.",
            },
        },
        "required": ["promo_id", "customer_email"],
    }

    def execute(self, promo_id: str, customer_email: str) -> dict[str, Any]:
        customer = self.conn.execute(
            "SELECT id FROM customers WHERE email = ?", (customer_email,)
        ).fetchone()
        if not customer:
            return {"error": "No account found for that email."}
        customer_id = customer["id"]

        now_pacific = datetime.now(ZoneInfo("America/Los_Angeles"))
        now_str = now_pacific.strftime("%Y-%m-%d %H:%M:%S")
        promo = self.conn.execute(
            "SELECT * FROM promotions WHERE id = ? AND valid_from <= ? AND valid_until >= ?",
            (promo_id, now_str, now_str),
        ).fetchone()
        if not promo:
            return {"error": f"Promotion {promo_id!r} is not currently active."}

        start_hour = promo["daily_start_hour"]
        end_hour = promo["daily_end_hour"]
        if not _in_daily_window(start_hour, end_hour):
            return {
                "error": (
                    f"This promotion is only available from "
                    f"{start_hour:02d}:00–{end_hour:02d}:00 Pacific Time."
                )
            }

        existing = self.conn.execute(
            "SELECT code FROM promotion_claims WHERE promo_id = ? AND customer_id = ?",
            (promo_id, customer_id),
        ).fetchone()
        if existing:
            return {
                "code": existing["code"],
                "discount_pct": promo["discount_pct"],
                "already_claimed": True,
            }

        suffix = uuid.uuid4().hex[:8].upper()
        code = f"{promo['code']}-{suffix}"
        self.conn.execute(
            "INSERT INTO promotion_claims (id, promo_id, customer_id, code) VALUES (?,?,?,?)",
            (str(uuid.uuid4()), promo_id, customer_id, code),
        )
        self.conn.commit()
        return {
            "code": code,
            "discount_pct": promo["discount_pct"],
            "already_claimed": False,
        }


# ── Registry ──────────────────────────────────────────────────────────────────

class Registry:
    """Holds all tools; exposes the OpenAI schema list and a single dispatch point."""

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, *tools: Tool) -> None:
        for tool in tools:
            self._tools[tool.name] = tool

    def openai_tools(self) -> list[dict[str, Any]]:
        return [t.openai_schema() for t in self._tools.values()]

    def execute(self, name: str, **kwargs) -> Any:
        if name not in self._tools:
            return {"error": f"Unknown tool: {name}"}
        return self._tools[name].execute(**kwargs)


def build_registry(conn: sqlite3.Connection) -> Registry:
    init_schema(conn)  # idempotent — safe to call even if schema already exists
    rows = conn.execute("SELECT DISTINCT tag FROM product_tags ORDER BY tag").fetchall()
    tags = [r["tag"] for r in rows]

    reg = Registry()
    reg.register(
        LookupCustomerTool(conn),
        RegisterCustomerTool(conn),
        GetOrderTool(conn),
        GetOrdersByCustomerTool(conn),
        SearchProductsTool(conn, tags),
        GetActivePromotionsTool(conn),
        ClaimPromotionTool(conn),
        CreateOrderTool(conn),
    )
    return reg
