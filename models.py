"""Store POS - Database Models"""
import sqlite3
import os
from datetime import datetime, date, timedelta

DB_PATH = os.environ.get('DB_PATH') or os.path.join(os.path.dirname(__file__), 'store.db')


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_db()

    # Create products + orders + other tables with v2.1 schema
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL CHECK(price >= 0),
            category TEXT DEFAULT '',
            stock INTEGER DEFAULT 0 CHECK(stock >= 0),
            discount REAL DEFAULT 0 CHECK(discount >= 0),
            discount_type TEXT DEFAULT 'percent',
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            total_amount REAL NOT NULL,
            item_count INTEGER NOT NULL,
            note TEXT DEFAULT '',
            status TEXT DEFAULT 'pending'
                CHECK(status IN ('pending', 'paid', 'completed', 'refunded', 'cancelled')),
            payment_status TEXT DEFAULT 'unpaid',
            paid_amount REAL DEFAULT 0,
            change_amount REAL DEFAULT 0,
            payment_method TEXT DEFAULT '',
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
            multi_select INTEGER DEFAULT 0,
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

    # ── v2.2 Migration: multi_select on product_options ──────
    try:
        conn.execute("ALTER TABLE product_options ADD COLUMN multi_select INTEGER DEFAULT 0")
    except (sqlite3.OperationalError, sqlite3.IntegrityError):
        pass  # Column already exists

    # ── v2.2 Migration: add 'completed' to orders status ──────
    # SQLite can't ALTER CHECK, so recreate the table if needed
    try:
        conn.execute("INSERT INTO orders (id, total_amount, item_count, status) VALUES (-2, 0, 0, 'completed')")
        conn.execute("DELETE FROM orders WHERE id=-2")
    except (sqlite3.OperationalError, sqlite3.IntegrityError):
        conn.executescript("""
            PRAGMA foreign_keys=OFF;
            BEGIN TRANSACTION;
            CREATE TABLE orders_v3 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                total_amount REAL NOT NULL,
                item_count INTEGER NOT NULL,
                note TEXT DEFAULT '',
                status TEXT DEFAULT 'pending'
                    CHECK(status IN ('pending', 'paid', 'completed', 'refunded', 'cancelled')),
                payment_status TEXT DEFAULT 'unpaid',
                paid_amount REAL DEFAULT 0,
                change_amount REAL DEFAULT 0,
                payment_method TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now','localtime'))
            );
            INSERT INTO orders_v3 SELECT * FROM orders;
            DROP TABLE orders;
            ALTER TABLE orders_v3 RENAME TO orders;
            COMMIT;
            PRAGMA foreign_keys=ON;
        """)

    # ── v2.1 Migration: discount_type + REAL discount ──────────
    # Check if discount_type column exists
    cols = [r['name'] for r in conn.execute("PRAGMA table_info(products)").fetchall()]
    needs_discount_migration = 'discount_type' not in cols

    if needs_discount_migration:
        # Products table needs discount_type column and REAL discount
        conn.executescript("""
            PRAGMA foreign_keys=OFF;
            BEGIN TRANSACTION;

            CREATE TABLE IF NOT EXISTS products_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                price REAL NOT NULL CHECK(price >= 0),
                category TEXT DEFAULT '',
                stock INTEGER DEFAULT 0 CHECK(stock >= 0),
                discount REAL DEFAULT 0 CHECK(discount >= 0),
                discount_type TEXT DEFAULT 'percent',
                created_at TEXT DEFAULT (datetime('now','localtime'))
            );

            INSERT INTO products_new
                (id, name, price, category, stock, discount, discount_type, created_at)
            SELECT
                id, name, price, category, stock, CAST(discount AS REAL), 'percent', created_at
            FROM products;

            DROP TABLE products;
            ALTER TABLE products_new RENAME TO products;

            COMMIT;
            PRAGMA foreign_keys=ON;
        """)
    else:
        # Just make sure the discount column is REAL (SQLite flexible typing)
        pass

    # ── Migration from v1.x (status='completed' → 'paid') ──
    needs_check_migration = False
    try:
        conn.execute("ALTER TABLE orders ADD COLUMN payment_method TEXT DEFAULT ''")
        needs_check_migration = True
    except (sqlite3.OperationalError, sqlite3.IntegrityError):
        pass

    if not needs_check_migration:
        try:
            conn.execute("INSERT INTO orders (id, total_amount, item_count, status) VALUES (-1, 0, 0, 'pending')")
            conn.execute("DELETE FROM orders WHERE id=-1")
        except (sqlite3.OperationalError, sqlite3.IntegrityError):
            needs_check_migration = True

    if needs_check_migration:
        conn.executescript("""
            PRAGMA foreign_keys=OFF;
            BEGIN TRANSACTION;

            CREATE TABLE IF NOT EXISTS orders_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                total_amount REAL NOT NULL,
                item_count INTEGER NOT NULL,
                note TEXT DEFAULT '',
                status TEXT DEFAULT 'pending'
                    CHECK(status IN ('pending', 'paid', 'completed', 'refunded', 'cancelled')),
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
