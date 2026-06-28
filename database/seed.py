import asyncio
import json
from pathlib import Path

import aiosqlite
from db import init_db

DB_PATH = Path(__file__).parent.parent / "drip.db"

PRODUCTS = [
    {
        "name": "White Cotton Kurta",
        "category": "kurta",
        "price": 59900,
        "sizes": json.dumps(["S", "M", "L", "XL"]),
        "image": "kurta-white.jpg",
        "description": "Breathable cotton kurta, perfect for daily wear and festive occasions.",
        "in_stock": 1,
    },
    {
        "name": "Slim Fit Dark Jeans",
        "category": "jeans",
        "price": 129900,
        "sizes": json.dumps(["S", "M", "L", "XL"]),
        "image": "jeans-dark-blue.jpg",
        "description": "Classic slim fit jeans in deep indigo wash. Pairs with anything.",
        "in_stock": 1,
    },
    {
        "name": "Oversized Linen Shirt",
        "category": "shirt",
        "price": 79900,
        "sizes": json.dumps(["S", "M", "L", "XL"]),
        "image": "shirt-linen-beige.jpg",
        "description": "Relaxed linen shirt in natural beige. Light and easy all summer.",
        "in_stock": 1,
    },
    {
        "name": "Black Track Joggers",
        "category": "joggers",
        "price": 89900,
        "sizes": json.dumps(["S", "M", "L", "XL"]),
        "image": "joggers-black.jpg",
        "description": "Slim tapered joggers with zip pockets. Gym to street.",
        "in_stock": 1,
    },
    {
        "name": "Olive Bomber Jacket",
        "category": "jacket",
        "price": 179900,
        "sizes": json.dumps(["S", "M", "L", "XL"]),
        "image": "jacket-olive-bomber.jpg",
        "description": "Lightweight bomber in military olive. Statement piece for cooler days.",
        "in_stock": 1,
    },
]


async def seed():
    await init_db()
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM products")
        (count,) = await cursor.fetchone()
        if count > 0:
            print(f"Already seeded ({count} products). Skipping.")
            return

        await db.executemany(
            """
            INSERT INTO products (name, category, price, sizes, image, description, in_stock)
            VALUES (:name, :category, :price, :sizes, :image, :description, :in_stock)
            """,
            PRODUCTS,
        )
        await db.commit()
        print(f"Seeded {len(PRODUCTS)} products.")


if __name__ == "__main__":
    asyncio.run(seed())
