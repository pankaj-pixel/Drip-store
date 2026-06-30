import aiosqlite
from contextlib import asynccontextmanager

DB_PATH = "drip.db"

_CREATE_PRODUCTS = """
CREATE TABLE IF NOT EXISTS products (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    category    TEXT    NOT NULL,
    price       INTEGER NOT NULL,
    sizes       TEXT    NOT NULL,
    image       TEXT    NOT NULL,
    description TEXT    NOT NULL DEFAULT '',
    in_stock    INTEGER NOT NULL DEFAULT 1
)
"""

_CREATE_REELS = """
CREATE TABLE IF NOT EXISTS reels (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    instagram_url TEXT    NOT NULL,
    product_id    INTEGER REFERENCES products(id) ON DELETE SET NULL,
    caption       TEXT    NOT NULL DEFAULT '',
    created_at    TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
)
"""

_CREATE_ORDERS = """
CREATE TABLE IF NOT EXISTS orders (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_name TEXT    NOT NULL,
    phone         TEXT    NOT NULL,
    address       TEXT    NOT NULL,
    items         TEXT    NOT NULL,
    total         INTEGER NOT NULL,
    whatsapp_sent INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
)
"""


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(_CREATE_PRODUCTS)
        await db.execute(_CREATE_REELS)
        await db.execute(_CREATE_ORDERS)
        try:
            await db.execute(
                "ALTER TABLE orders ADD COLUMN status TEXT NOT NULL DEFAULT 'pending'"
            )
        except Exception:
            pass
        try:
            await db.execute(
                "ALTER TABLE products ADD COLUMN images TEXT NOT NULL DEFAULT '[]'"
            )
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE products ADD COLUMN video TEXT")
        except Exception:
            pass
        try:
            await db.execute(
                "ALTER TABLE reels ADD COLUMN video TEXT NOT NULL DEFAULT ''"
            )
        except Exception:
            pass
        # Migrate single image → JSON array for existing rows
        await db.execute(
            "UPDATE products SET images = json_array(image) WHERE images = '[]' AND image != ''"
        )
        await db.commit()


@asynccontextmanager
async def get_db():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db
