"""Store POS - Database Models"""
import sqlite3
import os
from datetime import datetime, date, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), 'store.db')


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL CHECK(price >= 0),
            category TEXT DEFAULT '',
            stock INTEGER DEFAULT 0 CHECK(stock >= 0),
            discount INTEGER DEFAULT 0 CHECK(discount >= 0 AND discount <= 100),
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            total_amount REAL NOT NULL,
            item_count INTEGER NOT NULL,
            note TEXT DEFAULT '',
            status TEXT DEFAULT 'completed' CHECK(status IN ('completed','refunded')),
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL CHECK(quantity > 0),
            unit_price REAL NOT NULL,
            subtotal REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL
        );
    """)
    # Migration: add discount column to products if missing
    try:
        conn.execute("ALTER TABLE products ADD COLUMN discount INTEGER DEFAULT 0 CHECK(discount >= 0 AND discount <= 100)")
    except sqlite3.OperationalError:
        pass  # column already exists
    # Migration: add note column to orders if missing
    try:
        conn.execute("ALTER TABLE orders ADD COLUMN note TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass  # column already exists
    # Migration: add product_options table
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS product_options (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            group_name TEXT NOT NULL,
            option_name TEXT NOT NULL,
            price_adjustment REAL DEFAULT 0 CHECK(price_adjustment >= 0),
            sort_order INTEGER DEFAULT 0,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
        );
    """)
    conn.commit()
    conn.close()
