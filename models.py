"""Store POS - Database Models"""
import sqlite3
import os
from datetime import datetime, date, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), 'store.db')


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_db()

    # Create orders table with v2 schema (CHECK allows all new statuses)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            total_amount REAL NOT NULL,
            item_count INTEGER NOT NULL,
            note TEXT DEFAULT '',
            status TEXT DEFAULT 'pending'
                CHECK(status IN ('pending', 'paid', 'refunded', 'cancelled')),
            payment_status TEXT DEFAULT 'unpaid',
            paid_amount REAL DEFAULT 0,
            change_amount REAL DEFAULT 0,
            payment_method TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL CHECK(price >= 0),
            category TEXT DEFAULT '',
            stock INTEGER DEFAULT 0 CHECK(stock >= 0),
            discount INTEGER DEFAULT 0 CHECK(discount >= 0 AND discount <= 100),
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

        CREATE TABLE IF NOT EXISTS product_options (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            group_name TEXT NOT NULL,
            option_name TEXT NOT NULL,
            price_adjustment REAL DEFAULT 0 CHECK(price_adjustment >= 0),
            sort_order INTEGER DEFAULT 0,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            method TEXT NOT NULL CHECK(method IN ('cash', 'alipay', 'wechat', 'other')),
            amount REAL NOT NULL CHECK(amount > 0),
            created_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
        );
    """)

    # ── Migration from v1.x (status='completed' → 'paid') ──

    # Check if we need to migrate: try adding a v2 column; if it succeeds,
    # then the table had old schema and needs CHECK constraint migration
    needs_check_migration = False
    try:
        conn.execute("ALTER TABLE orders ADD COLUMN payment_method TEXT DEFAULT ''")
        # Column didn't exist → old schema → needs full migration
        needs_check_migration = True
    except sqlite3.OperationalError:
        # Column already exists, check if CHECK constraint allows 'pending'
        pass

    if not needs_check_migration:
        # Verify CHECK constraint allows new statuses
        try:
            conn.execute("INSERT INTO orders (id, total_amount, item_count, status) VALUES (-1, 0, 0, 'pending')")
            conn.execute("DELETE FROM orders WHERE id=-1")
        except sqlite3.OperationalError:
            needs_check_migration = True

    if needs_check_migration:
        # Table exists with old CHECK constraint — recreate it
        conn.executescript("""
            PRAGMA foreign_keys=OFF;
            BEGIN TRANSACTION;

            CREATE TABLE IF NOT EXISTS orders_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                total_amount REAL NOT NULL,
                item_count INTEGER NOT NULL,
                note TEXT DEFAULT '',
                status TEXT DEFAULT 'pending'
                    CHECK(status IN ('pending', 'paid', 'refunded', 'cancelled')),
                payment_status TEXT DEFAULT 'unpaid',
                paid_amount REAL DEFAULT 0,
                change_amount REAL DEFAULT 0,
                payment_method TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now','localtime'))
            );

            INSERT INTO orders_new
                (id, total_amount, item_count, note, status,
                 payment_status, paid_amount, change_amount, payment_method, created_at)
            SELECT
                id, total_amount, item_count,
                COALESCE(note, ''),
                CASE WHEN status='completed' THEN 'paid' ELSE status END,
                CASE WHEN status='completed' THEN 'paid' ELSE 'unpaid' END,
                0, 0, '',
                created_at
            FROM orders;

            DROP TABLE orders;
            ALTER TABLE orders_new RENAME TO orders;

            COMMIT;
            PRAGMA foreign_keys=ON;
        """)

    # Backfill payments for existing paid orders that don't have one
    existing = conn.execute(
        "SELECT o.id, o.total_amount, o.payment_method FROM orders o "
        "WHERE o.status='paid' AND o.id NOT IN (SELECT DISTINCT order_id FROM payments)"
    ).fetchall()
    for o in existing:
        method = o['payment_method'] if o['payment_method'] else 'other'
        conn.execute(
            "INSERT INTO payments (order_id, method, amount) VALUES (?,?,?)",
            (o['id'], method, o['total_amount'])
        )

    conn.commit()
    conn.close()
