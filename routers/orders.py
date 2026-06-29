import json
import re

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from database.db import get_db

router = APIRouter()
templates = Jinja2Templates(directory="templates")

PHONE_RE = re.compile(r"^[6-9]\d{9}$")
WA_PHONE = "918826662645"


@router.get("/checkout", response_class=HTMLResponse)
async def checkout_page(request: Request):
    return templates.TemplateResponse("checkout.html", {"request": request, "error": "", "items_json": ""})


@router.post("/checkout")
async def checkout_submit(
    request: Request,
    customer_name: str = Form(...),
    phone: str = Form(...),
    address: str = Form(...),
    items_json: str = Form(...),
):
    phone = phone.strip()

    if not PHONE_RE.match(phone):
        return templates.TemplateResponse(
            "checkout.html",
            {
                "request": request,
                "error": "Enter a valid 10-digit mobile number starting with 6, 7, 8, or 9.",
                "customer_name": customer_name,
                "phone": phone,
                "address": address,
                "items_json": items_json,
            },
            status_code=422,
        )

    try:
        raw_items = json.loads(items_json)
    except (json.JSONDecodeError, ValueError):
        return RedirectResponse("/cart", status_code=303)

    if not raw_items:
        return RedirectResponse("/cart", status_code=303)

    items_for_db = []
    for i in raw_items:
        try:
            product_id = int(str(i["key"]).split("_")[0])
        except (KeyError, ValueError, IndexError):
            product_id = 0
        items_for_db.append({
            "product_id": product_id,
            "name": i["name"],
            "size": i.get("size", ""),
            "qty": int(i["qty"]),
            "price": int(i["price"]) * 100,  # ₹ → paise
        })

    total_paise = sum(it["price"] * it["qty"] for it in items_for_db)

    async with get_db() as db:
        cursor = await db.execute(
            "INSERT INTO orders (customer_name, phone, address, items, total) VALUES (?, ?, ?, ?, ?)",
            (customer_name.strip(), phone, address.strip(), json.dumps(items_for_db), total_paise),
        )
        await db.commit()
        order_id = cursor.lastrowid

    return RedirectResponse(f"/confirm/{order_id}", status_code=303)


@router.get("/confirm/{order_id}", response_class=HTMLResponse)
async def confirm_page(request: Request, order_id: int):
    async with get_db() as db:
        async with db.execute("SELECT * FROM orders WHERE id = ?", (order_id,)) as cursor:
            row = await cursor.fetchone()

    if row is None:
        return RedirectResponse("/", status_code=303)

    order = dict(row)
    items = json.loads(order["items"])
    total_inr = order["total"] // 100

    lines = []
    for it in items:
        size_str = f" (Size: {it['size']})" if it.get("size") else ""
        line_total = (it["price"] // 100) * it["qty"]
        lines.append(f"*{it['name']}*{size_str} ×{it['qty']} — ₹{line_total:,}")

    wa_msg = (
        "Hi, I want to order from DRIP:\n\n"
        + "\n".join(lines)
        + f"\n\nTotal: ₹{total_inr:,}\nFree delivery please."
        + f"\n\nName: {order['customer_name']}\nPhone: {order['phone']}\nAddress: {order['address']}"
    )

    return templates.TemplateResponse("confirm.html", {
        "request": request,
        "order": order,
        "items": items,
        "total_inr": total_inr,
        "wa_msg": wa_msg,
        "wa_phone": WA_PHONE,
    })
