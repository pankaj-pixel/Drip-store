import io
import json
import os
import uuid
from pathlib import Path
from typing import List

from PIL import Image

from dotenv import load_dotenv
from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from itsdangerous import BadSignature, URLSafeSerializer

from database.db import get_db
from models.product import Product
from models.reel import Reel

load_dotenv()

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory="templates")

ADMIN_PASS = os.getenv("ADMIN_PASS", "drip123")
SECRET_KEY = os.getenv("SECRET_KEY", "change-me")
_signer = URLSafeSerializer(SECRET_KEY, salt="admin-session")
COOKIE = "drip_admin"

UPLOAD_DIR = Path("static/uploads")
ALLOWED_IMAGES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_VIDEO = {"video/mp4", "video/quicktime"}
MAX_PHOTO_BYTES = 5 * 1024 * 1024
MAX_VIDEO_BYTES = 20 * 1024 * 1024

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


def _compress_image(data: bytes) -> bytes:
    img = Image.open(io.BytesIO(data))
    if img.mode in ("RGBA", "P", "LA"):
        img = img.convert("RGB")
    w, h = img.size
    if max(w, h) > 1200:
        scale = 1200 / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    out = io.BytesIO()
    img.save(out, format="WEBP", quality=80, method=4)
    return out.getvalue()


async def _save_file(
    file: UploadFile | None,
    allowed_types: set,
    max_bytes: int,
) -> tuple:
    if not file or not file.filename:
        return None, None
    content = await file.read()
    if len(content) > max_bytes:
        mb = max_bytes // (1024 * 1024)
        return None, f'"{file.filename}" exceeds {mb} MB limit.'
    if file.content_type not in allowed_types:
        return None, f'"{file.filename}": file type not allowed.'
    if file.content_type in ALLOWED_IMAGES:
        content = _compress_image(content)
        ext = ".webp"
    else:
        ext = Path(file.filename).suffix.lower()
    fname = f"{uuid.uuid4().hex}{ext}"
    (UPLOAD_DIR / fname).write_bytes(content)
    return fname, None


async def _get_categories() -> list:
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT DISTINCT category FROM products ORDER BY category"
        )
        return [row[0] for row in await cursor.fetchall()]


# ── Auth / login ──────────────────────────────────────────

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


@router.get("/logout")
async def admin_logout():
    response = RedirectResponse("/admin", status_code=302)
    response.delete_cookie(COOKIE)
    return response


# ── Orders ────────────────────────────────────────────────

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


# ── Products list ─────────────────────────────────────────

@router.get("/products", response_class=HTMLResponse)
async def admin_products(request: Request):
    if not _is_auth(request):
        return RedirectResponse("/admin", status_code=302)
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM products ORDER BY id DESC")
        rows = await cursor.fetchall()
    products = [Product(**dict(row)) for row in rows]
    return templates.TemplateResponse(
        "admin_products.html", {"request": request, "products": products}
    )


# ── New product ───────────────────────────────────────────

@router.get("/products/new", response_class=HTMLResponse)
async def admin_product_new_form(request: Request):
    if not _is_auth(request):
        return RedirectResponse("/admin", status_code=302)
    categories = await _get_categories()
    return templates.TemplateResponse(
        "admin_product_form.html",
        {"request": request, "product": None, "categories": categories, "error": ""},
    )


@router.post("/products/new")
async def admin_product_create(
    request: Request,
    name: str = Form(...),
    category: str = Form(...),
    new_category: str = Form(default=""),
    price_inr: int = Form(...),
    description: str = Form(default=""),
    sizes: List[str] = Form(default=[]),
    in_stock: str = Form(default=""),
    photo_0: UploadFile | None = File(default=None),
    photo_1: UploadFile | None = File(default=None),
    photo_2: UploadFile | None = File(default=None),
    video_file: UploadFile | None = File(default=None),
):
    if not _is_auth(request):
        return RedirectResponse("/admin", status_code=302)

    actual_category = new_category.strip() if category == "__new__" else category
    errors: list = []
    images: list = []

    for photo in [photo_0, photo_1, photo_2]:
        fname, err = await _save_file(photo, ALLOWED_IMAGES, MAX_PHOTO_BYTES)
        if err:
            errors.append(err)
        elif fname:
            images.append(fname)

    video = None
    v_fname, v_err = await _save_file(video_file, ALLOWED_VIDEO, MAX_VIDEO_BYTES)
    if v_err:
        errors.append(v_err)
    else:
        video = v_fname

    if errors or not actual_category or not name.strip():
        categories = await _get_categories()
        return templates.TemplateResponse(
            "admin_product_form.html",
            {
                "request": request,
                "product": None,
                "categories": categories,
                "error": " ".join(errors) if errors else "Name and category are required.",
            },
            status_code=422,
        )

    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO products (name, category, price, sizes, image, images, video, description, in_stock)
            VALUES (?, ?, ?, ?, '', ?, ?, ?, ?)
            """,
            (
                name.strip(),
                actual_category,
                price_inr * 100,
                json.dumps(sizes),
                json.dumps(images),
                video,
                description.strip(),
                1 if in_stock else 0,
            ),
        )
        await db.commit()
    return RedirectResponse("/admin/products", status_code=303)


# ── Edit product ──────────────────────────────────────────

@router.get("/products/{product_id}/edit", response_class=HTMLResponse)
async def admin_product_edit_form(request: Request, product_id: int):
    if not _is_auth(request):
        return RedirectResponse("/admin", status_code=302)
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        row = await cursor.fetchone()
    if not row:
        return RedirectResponse("/admin/products", status_code=302)
    categories = await _get_categories()
    product = Product(**dict(row))
    return templates.TemplateResponse(
        "admin_product_form.html",
        {"request": request, "product": product, "categories": categories, "error": ""},
    )


@router.post("/products/{product_id}/edit")
async def admin_product_update(
    request: Request,
    product_id: int,
    name: str = Form(...),
    category: str = Form(...),
    new_category: str = Form(default=""),
    price_inr: int = Form(...),
    description: str = Form(default=""),
    sizes: List[str] = Form(default=[]),
    in_stock: str = Form(default=""),
    existing_0: str = Form(default=""),
    existing_1: str = Form(default=""),
    existing_2: str = Form(default=""),
    remove_0: str = Form(default=""),
    remove_1: str = Form(default=""),
    remove_2: str = Form(default=""),
    photo_0: UploadFile | None = File(default=None),
    photo_1: UploadFile | None = File(default=None),
    photo_2: UploadFile | None = File(default=None),
    existing_video: str = Form(default=""),
    remove_video: str = Form(default=""),
    video_file: UploadFile | None = File(default=None),
):
    if not _is_auth(request):
        return RedirectResponse("/admin", status_code=302)

    actual_category = new_category.strip() if category == "__new__" else category
    errors: list = []

    existing_slots = [existing_0, existing_1, existing_2]
    remove_slots = [remove_0 == "1", remove_1 == "1", remove_2 == "1"]
    photo_slots = [photo_0, photo_1, photo_2]
    images: list = []

    for i in range(3):
        existing = existing_slots[i]
        remove = remove_slots[i]
        photo = photo_slots[i]

        if photo and photo.filename:
            fname, err = await _save_file(photo, ALLOWED_IMAGES, MAX_PHOTO_BYTES)
            if err:
                errors.append(err)
            else:
                if existing:
                    (UPLOAD_DIR / existing).unlink(missing_ok=True)
                if fname:
                    images.append(fname)
        elif existing and not remove:
            images.append(existing)
        elif existing and remove:
            (UPLOAD_DIR / existing).unlink(missing_ok=True)

    video = None
    if video_file and video_file.filename:
        v_fname, v_err = await _save_file(video_file, ALLOWED_VIDEO, MAX_VIDEO_BYTES)
        if v_err:
            errors.append(v_err)
        else:
            if existing_video:
                (UPLOAD_DIR / existing_video).unlink(missing_ok=True)
            video = v_fname
    elif existing_video and remove_video != "1":
        video = existing_video
    elif existing_video and remove_video == "1":
        (UPLOAD_DIR / existing_video).unlink(missing_ok=True)

    if errors:
        async with get_db() as db:
            cursor = await db.execute("SELECT * FROM products WHERE id = ?", (product_id,))
            row = await cursor.fetchone()
        categories = await _get_categories()
        product = Product(**dict(row)) if row else None
        return templates.TemplateResponse(
            "admin_product_form.html",
            {
                "request": request,
                "product": product,
                "categories": categories,
                "error": " ".join(errors),
            },
            status_code=422,
        )

    async with get_db() as db:
        await db.execute(
            """
            UPDATE products SET
                name = ?, category = ?, price = ?, sizes = ?,
                images = ?, video = ?, description = ?, in_stock = ?
            WHERE id = ?
            """,
            (
                name.strip(),
                actual_category,
                price_inr * 100,
                json.dumps(sizes),
                json.dumps(images),
                video,
                description.strip(),
                1 if in_stock else 0,
                product_id,
            ),
        )
        await db.commit()
    return RedirectResponse("/admin/products", status_code=303)


# ── Delete / toggle stock ─────────────────────────────────

@router.post("/products/{product_id}/delete")
async def admin_product_delete(request: Request, product_id: int):
    if not _is_auth(request):
        return RedirectResponse("/admin", status_code=302)
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT images, video FROM products WHERE id = ?", (product_id,)
        )
        row = await cursor.fetchone()
        if row:
            for fname in json.loads(row["images"] or "[]"):
                (UPLOAD_DIR / fname).unlink(missing_ok=True)
            if row["video"]:
                (UPLOAD_DIR / row["video"]).unlink(missing_ok=True)
            await db.execute("DELETE FROM products WHERE id = ?", (product_id,))
            await db.commit()
    return RedirectResponse("/admin/products", status_code=303)


@router.get("/reels", response_class=HTMLResponse)
async def admin_reels(request: Request):
    if not _is_auth(request):
        return RedirectResponse("/admin", status_code=302)
    async with get_db() as db:
        cursor = await db.execute(
            """SELECT r.id, r.video, r.instagram_url, r.product_id, r.caption,
                      r.created_at, p.name AS product_name
               FROM reels r
               LEFT JOIN products p ON p.id = r.product_id
               ORDER BY r.id DESC"""
        )
        reel_rows = await cursor.fetchall()
        prod_cursor = await db.execute(
            "SELECT id, name FROM products ORDER BY name"
        )
        prod_rows = await prod_cursor.fetchall()
    reels = [Reel(**dict(row)) for row in reel_rows]
    products = [{"id": r["id"], "name": r["name"]} for r in prod_rows]
    return templates.TemplateResponse(
        "admin_reels.html",
        {"request": request, "reels": reels, "products": products, "error": ""},
    )


@router.post("/reels/new")
async def admin_reel_create(
    request: Request,
    instagram_url: str = Form(default=""),
    product_id: str = Form(default=""),
    caption: str = Form(default=""),
    video_file: UploadFile | None = File(default=None),
):
    if not _is_auth(request):
        return RedirectResponse("/admin", status_code=302)

    video_fname, video_err = await _save_file(video_file, ALLOWED_VIDEO, MAX_VIDEO_BYTES)

    async def _reels_form_ctx(err: str):
        async with get_db() as db:
            cursor = await db.execute(
                """SELECT r.id, r.video, r.instagram_url, r.product_id, r.caption,
                          r.created_at, p.name AS product_name
                   FROM reels r
                   LEFT JOIN products p ON p.id = r.product_id
                   ORDER BY r.id DESC"""
            )
            reel_rows = await cursor.fetchall()
            prod_cursor = await db.execute("SELECT id, name FROM products ORDER BY name")
            prod_rows = await prod_cursor.fetchall()
        return {
            "reels": [Reel(**dict(r)) for r in reel_rows],
            "products": [{"id": r["id"], "name": r["name"]} for r in prod_rows],
            "error": err,
        }

    if video_err:
        ctx = await _reels_form_ctx(video_err)
        return templates.TemplateResponse("admin_reels.html",
                                          {"request": request, **ctx}, status_code=422)
    if not video_fname:
        ctx = await _reels_form_ctx("A video file is required.")
        return templates.TemplateResponse("admin_reels.html",
                                          {"request": request, **ctx}, status_code=422)

    pid = int(product_id) if product_id.strip().isdigit() else None
    url = instagram_url.strip()
    async with get_db() as db:
        await db.execute(
            """INSERT INTO reels (video, instagram_url, product_id, caption)
               VALUES (?, ?, ?, ?)""",
            (video_fname, url, pid, caption.strip()),
        )
        await db.commit()
    return RedirectResponse("/admin/reels", status_code=303)


@router.post("/reels/{reel_id}/delete")
async def admin_reel_delete(request: Request, reel_id: int):
    if not _is_auth(request):
        return RedirectResponse("/admin", status_code=302)
    async with get_db() as db:
        cursor = await db.execute("SELECT video FROM reels WHERE id = ?", (reel_id,))
        row = await cursor.fetchone()
        if row and row["video"]:
            (UPLOAD_DIR / row["video"]).unlink(missing_ok=True)
        await db.execute("DELETE FROM reels WHERE id = ?", (reel_id,))
        await db.commit()
    return RedirectResponse("/admin/reels", status_code=303)


@router.post("/products/{product_id}/toggle-stock")
async def admin_product_toggle_stock(request: Request, product_id: int):
    if not _is_auth(request):
        return RedirectResponse("/admin", status_code=302)
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT in_stock FROM products WHERE id = ?", (product_id,)
        )
        row = await cursor.fetchone()
        if row:
            await db.execute(
                "UPDATE products SET in_stock = ? WHERE id = ?",
                (0 if row["in_stock"] else 1, product_id),
            )
            await db.commit()
    return RedirectResponse("/admin/products", status_code=303)
