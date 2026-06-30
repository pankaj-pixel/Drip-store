from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from database.db import get_db
from models.product import Product
from models.reel import Reel

router = APIRouter()
templates = Jinja2Templates(directory="templates")

SPORTSWEAR_CATEGORIES = ["jersey", "t-shirt", "shorts", "vest", "joggers", "lowers"]


@router.get("/", response_class=HTMLResponse)
async def home(request: Request, category: str | None = Query(default=None)):
    active = category.lower().strip() if category else ""
    async with get_db() as db:
        cat_cursor = await db.execute(
            "SELECT DISTINCT category FROM products WHERE in_stock = 1 ORDER BY category"
        )
        cat_rows = await cat_cursor.fetchall()

        if active:
            prod_cursor = await db.execute(
                "SELECT * FROM products WHERE in_stock = 1 AND category = ?", (active,)
            )
        else:
            prod_cursor = await db.execute("SELECT * FROM products WHERE in_stock = 1")
        prod_rows = await prod_cursor.fetchall()

        reel_cursor = await db.execute(
            """SELECT r.id, r.video, r.instagram_url, r.product_id, r.caption,
                      r.created_at, p.name AS product_name
               FROM reels r
               LEFT JOIN products p ON p.id = r.product_id
               ORDER BY r.id DESC"""
        )
        reel_rows = await reel_cursor.fetchall()

    categories = [row[0] for row in cat_rows]
    products_list = [Product(**dict(row)) for row in prod_rows]
    reels = [Reel(**dict(row)) for row in reel_rows]
    return templates.TemplateResponse(
        "home.html",
        {
            "request": request,
            "products": products_list,
            "categories": categories,
            "active_category": active,
            "reels": reels,
        },
    )


@router.get("/sportswear", response_class=HTMLResponse)
async def sportswear(request: Request, category: str | None = Query(default=None)):
    active = category.lower().strip() if category else ""
    placeholders = ",".join("?" * len(SPORTSWEAR_CATEGORIES))
    async with get_db() as db:
        if active and active in SPORTSWEAR_CATEGORIES:
            cursor = await db.execute(
                f"SELECT * FROM products WHERE in_stock = 1 AND category = ? ORDER BY id",
                (active,),
            )
        else:
            cursor = await db.execute(
                f"SELECT * FROM products WHERE in_stock = 1 AND category IN ({placeholders}) ORDER BY id",
                SPORTSWEAR_CATEGORIES,
            )
        rows = await cursor.fetchall()
    products_list = [Product(**dict(row)) for row in rows]
    return templates.TemplateResponse(
        "sportswear.html",
        {
            "request": request,
            "products": products_list,
            "categories": SPORTSWEAR_CATEGORIES,
            "active_category": active,
        },
    )


@router.get("/product/{product_id}", response_class=HTMLResponse)
async def product_detail(request: Request, product_id: int):
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Product not found")
    product = Product(**dict(row))
    return templates.TemplateResponse(
        "product.html", {"request": request, "product": product}
    )
