from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from database.db import get_db
from models.product import Product

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM products WHERE in_stock = 1")
        rows = await cursor.fetchall()
    products_list = [Product(**dict(row)) for row in rows]
    return templates.TemplateResponse(
        "home.html", {"request": request, "products": products_list}
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
