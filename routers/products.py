from fastapi import APIRouter, Request
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
