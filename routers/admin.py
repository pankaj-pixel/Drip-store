import json
import os

from dotenv import load_dotenv
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from itsdangerous import BadSignature, URLSafeSerializer

from database.db import get_db

load_dotenv()

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory="templates")

ADMIN_PASS = os.getenv("ADMIN_PASS", "drip123")
SECRET_KEY = os.getenv("SECRET_KEY", "change-me")
_signer = URLSafeSerializer(SECRET_KEY, salt="admin-session")
COOKIE = "drip_admin"

STATUS_CYCLE = {
    "pending": "confirmed",
    "confirmed": "delivered",
    "delivered": "pending",
}


def _is_auth(request: Request) -> bool:
    token = request.cookies.get(COOKIE)
    if not token:
        return False
    try:
        data = _signer.loads(token)
        return data.get("auth") == 1
    except BadSignature:
        return False


@router.get("", response_class=HTMLResponse)
async def admin_root(request: Request):
    if _is_auth(request):
        return RedirectResponse("/admin/orders", status_code=302)
    return templates.TemplateResponse("admin_login.html", {"request": request, "error": ""})


@router.post("/login")
async def admin_login(request: Request, password: str = Form(...)):
    if password == ADMIN_PASS:
        token = _signer.dumps({"auth": 1})
        response = RedirectResponse("/admin/orders", status_code=303)
        response.set_cookie(COOKIE, token, httponly=True, max_age=86400 * 7)
        return response
    return templates.TemplateResponse(
        "admin_login.html",
        {"request": request, "error": "Wrong password."},
        status_code=401,
    )


@router.get("/orders", response_class=HTMLResponse)
async def admin_orders(request: Request):
    if not _is_auth(request):
        return RedirectResponse("/admin", status_code=302)
    async with get_db() as db:
        async with db.execute("SELECT * FROM orders ORDER BY id DESC") as cursor:
            rows = await cursor.fetchall()
    orders = []
    for row in rows:
        o = dict(row)
        o["order_items"] = json.loads(o["items"])
        o["total_inr"] = o["total"] // 100
        o.setdefault("status", "pending")
        orders.append(o)
    return templates.TemplateResponse(
        "admin_orders.html", {"request": request, "orders": orders}
    )


@router.post("/orders/{order_id}/status")
async def toggle_status(request: Request, order_id: int):
    if not _is_auth(request):
        return RedirectResponse("/admin", status_code=302)
    async with get_db() as db:
        async with db.execute(
            "SELECT status FROM orders WHERE id = ?", (order_id,)
        ) as cursor:
            row = await cursor.fetchone()
        if row:
            next_status = STATUS_CYCLE.get(row["status"] or "pending", "pending")
            await db.execute(
                "UPDATE orders SET status = ? WHERE id = ?", (next_status, order_id)
            )
            await db.commit()
    return RedirectResponse("/admin/orders", status_code=303)


@router.get("/logout")
async def admin_logout():
    response = RedirectResponse("/admin", status_code=302)
    response.delete_cookie(COOKIE)
    return response
