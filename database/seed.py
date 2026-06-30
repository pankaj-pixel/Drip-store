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


SPORTSWEAR_CATEGORIES = ("jersey", "t-shirt", "shorts", "vest", "joggers", "lowers")

SPORTSWEAR_PRODUCTS = [
    {
        "name": "India Cricket Jersey",
        "category": "jersey",
        "price": 129900,
        "sizes": json.dumps(["S", "M", "L", "XL"]),
        "image": "jersey-india-cricket.jpg",
        "description": "Replica jersey in moisture-wicking fabric. Rep the team at the gym or on the field.",
        "in_stock": 1,
    },
    {
        "name": "Dry-Fit Training T-Shirt",
        "category": "t-shirt",
        "price": 69900,
        "sizes": json.dumps(["S", "M", "L", "XL"]),
        "image": "sport-tshirt-dryfit.jpg",
        "description": "Lightweight dry-fit tee with mesh panels. Keeps you cool through every set.",
        "in_stock": 1,
    },
    {
        "name": "Compression Gym Shorts",
        "category": "shorts",
        "price": 79900,
        "sizes": json.dumps(["S", "M", "L", "XL"]),
        "image": "sport-shorts-compression.jpg",
        "description": "7-inch inseam compression shorts with inner liner and zip side pocket.",
        "in_stock": 1,
    },
    {
        "name": "Muscle Tank Vest",
        "category": "vest",
        "price": 59900,
        "sizes": json.dumps(["S", "M", "L", "XL"]),
        "image": "sport-vest-muscle.jpg",
        "description": "Dropped armhole tank in breathable cotton-blend. Built for the rack.",
        "in_stock": 1,
    },
    {
        "name": "Tapered Training Joggers",
        "category": "joggers",
        "price": 109900,
        "sizes": json.dumps(["S", "M", "L", "XL"]),
        "image": "sport-joggers-tapered.jpg",
        "description": "Slim tapered fit with ribbed ankle cuffs and deep zip pockets. Gym to street.",
        "in_stock": 1,
    },
    {
        "name": "Relaxed Fit Track Lowers",
        "category": "lowers",
        "price": 89900,
        "sizes": json.dumps(["S", "M", "L", "XL"]),
        "image": "sport-lowers-track.jpg",
        "description": "Loose track lowers in soft fleece. Wide leg, elastic waist, side pockets.",
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


async def seed_sportswear():
    placeholders = ",".join("?" * len(SPORTSWEAR_CATEGORIES))
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            f"SELECT DISTINCT category FROM products WHERE category IN ({placeholders})",
            SPORTSWEAR_CATEGORIES,
        )
        existing = {row[0] for row in await cursor.fetchall()}
        if existing == set(SPORTSWEAR_CATEGORIES):
            print("Sportswear already seeded. Skipping.")
            return

        # Remove stale sportswear products (old categories like gym-wear)
        await db.execute(
            "DELETE FROM products WHERE category IN ('jersey', 'gym-wear', 't-shirt', 'shorts', 'vest', 'joggers', 'lowers')"
        )
        await db.executemany(
            """
            INSERT INTO products (name, category, price, sizes, image, description, in_stock)
            VALUES (:name, :category, :price, :sizes, :image, :description, :in_stock)
            """,
            SPORTSWEAR_PRODUCTS,
        )
        await db.commit()
        print(f"Seeded {len(SPORTSWEAR_PRODUCTS)} sportswear products.")


if __name__ == "__main__":
    asyncio.run(seed())
    asyncio.run(seed_sportswear())
