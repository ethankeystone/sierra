import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "sierra.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (
    id                  TEXT PRIMARY KEY,
    name                TEXT NOT NULL,
    email               TEXT UNIQUE NOT NULL,
    profile             TEXT,
    profile_updated_at  TEXT,
    created_at          TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS products (
    sku         TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    inventory   INTEGER DEFAULT 0,
    price       REAL DEFAULT 0,
    description TEXT
);

CREATE TABLE IF NOT EXISTS product_tags (
    sku     TEXT NOT NULL REFERENCES products(sku),
    tag     TEXT NOT NULL,
    PRIMARY KEY (sku, tag)
);

CREATE TABLE IF NOT EXISTS orders (
    id              TEXT PRIMARY KEY,
    customer_id     TEXT NOT NULL REFERENCES customers(id),
    status          TEXT NOT NULL CHECK(status IN (
        'pending','fulfilled','in_transit','delivered','failed'
    )),
    tracking_number TEXT,
    promo_code      TEXT
);

CREATE TABLE IF NOT EXISTS order_items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id    TEXT NOT NULL REFERENCES orders(id),
    sku         TEXT NOT NULL REFERENCES products(sku)
);

CREATE TABLE IF NOT EXISTS promotions (
    id               TEXT PRIMARY KEY,
    title            TEXT NOT NULL,
    code             TEXT UNIQUE NOT NULL,
    discount_pct     INTEGER NOT NULL,
    valid_from       TEXT NOT NULL,
    valid_until      TEXT NOT NULL,
    description      TEXT,
    daily_start_hour INTEGER,  -- PT hour (0-23) when daily window opens; NULL = no daily restriction
    daily_end_hour   INTEGER   -- PT hour (0-23) when daily window closes (exclusive)
);

CREATE TABLE IF NOT EXISTS promotion_tags (
    promo_id    TEXT NOT NULL REFERENCES promotions(id),
    tag         TEXT NOT NULL,
    PRIMARY KEY (promo_id, tag)
);

CREATE TABLE IF NOT EXISTS promotion_claims (
    id          TEXT PRIMARY KEY,
    promo_id    TEXT NOT NULL REFERENCES promotions(id),
    customer_id TEXT NOT NULL REFERENCES customers(id),
    code        TEXT UNIQUE NOT NULL,
    claimed_at  TEXT DEFAULT (datetime('now')),
    UNIQUE(promo_id, customer_id)
);

CREATE TABLE IF NOT EXISTS sessions (
    id           TEXT PRIMARY KEY,
    customer_id  TEXT REFERENCES customers(id),
    summary      TEXT,
    persist_error TEXT,
    started_at   TEXT DEFAULT (datetime('now')),
    ended_at     TEXT
);
"""

_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_orders_customer      ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_order_items_order    ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_sku      ON order_items(sku);
CREATE INDEX IF NOT EXISTS idx_product_tags_tag     ON product_tags(tag);
CREATE INDEX IF NOT EXISTS idx_promotions_window    ON promotions(valid_from, valid_until);
CREATE INDEX IF NOT EXISTS idx_promotion_tags_tag   ON promotion_tags(tag);
"""


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA + _INDEXES)
    conn.commit()
