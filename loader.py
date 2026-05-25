"""Seed sierra.db from products.json and customer_orders.json."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from db import init_schema

BASE = Path(__file__).parent / "data"

STATUS_MAP = {
    "fulfilled": "fulfilled",
    "in-transit": "in_transit",
    "delivered": "delivered",
    "error": "failed",
}


def load_products(conn: sqlite3.Connection) -> None:
    with open(BASE / "products.json") as f:
        raw = json.load(f)

    for p in raw:
        conn.execute(
            "INSERT OR REPLACE INTO products (sku, name, inventory, price, description) VALUES (?,?,?,?,?)",
            (p["SKU"], p["ProductName"], p["Inventory"], p.get("Price", 0), p["Description"]),
        )
        for tag in p.get("Tags", []):
            conn.execute(
                "INSERT OR IGNORE INTO product_tags (sku, tag) VALUES (?,?)",
                (p["SKU"], tag),
            )

    conn.commit()
    print(f"Loaded {len(raw)} products.")


def load_customers_and_orders(conn: sqlite3.Connection) -> None:
    with open(BASE / "customer_orders.json") as f:
        raw = json.load(f)

    customers_seen: dict[str, str] = {}  # email → customer_id

    for i, record in enumerate(raw, 1):
        email = record["Email"]

        # Insert customer once per unique email
        if email not in customers_seen:
            customer_id = f"USR-{len(customers_seen) + 1:03d}"
            conn.execute(
                "INSERT OR IGNORE INTO customers (id, name, email) VALUES (?,?,?)",
                (customer_id, record["CustomerName"], email),
            )
            customers_seen[email] = customer_id
        customer_id = customers_seen[email]

        # Normalise order status
        raw_status = record["Status"]
        tracking = record.get("TrackingNumber")
        status = STATUS_MAP.get(raw_status, raw_status)

        order_id = record["OrderNumber"].lstrip("#")
        conn.execute(
            "INSERT OR REPLACE INTO orders (id, customer_id, status, tracking_number) VALUES (?,?,?,?)",
            (order_id, customer_id, status, tracking),
        )

        for sku in record.get("ProductsOrdered", []):
            # Skip SKUs not in products (guards against stale test data)
            exists = conn.execute(
                "SELECT 1 FROM products WHERE sku = ?", (sku,)
            ).fetchone()
            if exists:
                conn.execute(
                    "INSERT OR IGNORE INTO order_items (order_id, sku) VALUES (?,?)",
                    (order_id, sku),
                )

    conn.commit()
    print(f"Loaded {len(customers_seen)} customers and {len(raw)} orders.")


def load_promotions(conn: sqlite3.Connection) -> None:
    with open(BASE / "promotions.json") as f:
        raw = json.load(f)

    for p in raw:
        conn.execute(
            "INSERT OR REPLACE INTO promotions "
            "(id, title, code, discount_pct, valid_from, valid_until, description, "
            "daily_start_hour, daily_end_hour) VALUES (?,?,?,?,?,?,?,?,?)",
            (
                p["id"], p["title"], p["code"], p["discount_pct"],
                p["valid_from"], p["valid_until"], p.get("description"),
                p.get("daily_start_hour"), p.get("daily_end_hour"),
            ),
        )
        for tag in p.get("tags", []):
            conn.execute(
                "INSERT OR IGNORE INTO promotion_tags (promo_id, tag) VALUES (?,?)",
                (p["id"], tag),
            )

    conn.commit()
    print(f"Loaded {len(raw)} promotions.")


if __name__ == "__main__":
    from db import get_connection
    conn = get_connection()
    init_schema(conn)
    load_products(conn)
    load_customers_and_orders(conn)
    load_promotions(conn)
    conn.close()
