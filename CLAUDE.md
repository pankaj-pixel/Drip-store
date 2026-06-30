# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**DRIP** — Men's clothing e-commerce store serving all of Delhi.
- Target customers: men aged 18–35 across Delhi NCR
- No user login. No payment gateway. Orders placed via WhatsApp.
- Free delivery on all orders.
- Mobile-first UI (primary device for the target demographic).

## Stack

- **Backend**: FastAPI
- **Templating**: Jinja2 (server-rendered HTML)
- **Database**: SQLite via `aiosqlite` (async)
- **Frontend**: Vanilla CSS + JS, mobile-first responsive design

## Common Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run dev server
uvicorn main:app --reload

# Seed the database
python database/seed.py
```

## Architecture

- **`main.py`** — Creates the FastAPI app, includes routers, mounts static files, and configures Jinja2 templates.
- **`database/db.py`** — Async SQLite connection setup using `aiosqlite`; provides a DB session dependency.
- **`database/seed.py`** — Populates the DB with initial product data.
- **`models/product.py`** — Product schema (name, price, category, images, sizes, etc.).
- **`models/order.py`** — Order schema; orders are captured for WhatsApp handoff, no payment state.
- **`routers/product.py`** — Product listing and detail pages.
- **`routers/cart.py`** — Cart logic (likely session-based or JS-managed since no login).
- **`routers/orders.py`** — Order summary and WhatsApp redirect with pre-filled order message.
- **`templates/base.html`** — Base layout extended by all pages; includes mobile viewport, nav, footer.
- **`templates/home.html`** — Landing/product grid page.
- **`templates/product.html`** — Single product detail page.
- **`templates/cart.html`** — Cart review page.
- **`templates/checkout.html`** — Final order form before WhatsApp redirect.
- **`static/css/style.css`** — All styles; mobile-first (min-width breakpoints).
- **`static/js/main.js`** — Cart state management, UI interactions.
- **`static/uploads/`** — Product images.

## Key Design Decisions

- **No auth**: All flows are anonymous. Cart state lives in the browser (localStorage or cookies) or server session — no user accounts.
- **WhatsApp ordering**: The checkout flow ends with a `wa.me` deep link pre-filled with the order summary, customer name, and address. No order is "confirmed" until the WhatsApp message is sent.
- **Async DB**: All database calls use `aiosqlite` — use `async def` route handlers and `await` all DB operations.
- **Mobile-first CSS**: Write base styles for mobile, then use `@media (min-width: ...)` for larger screens. Avoid desktop-first patterns.



## Session Log
| # | Name | Feature | Status | Date |
|---|---|---|---|---|
| 1 | db-setup | DB init, models, seed data | ✅ Done | 2026-06-28 |


2 | product-listing | main.py, products router, home page UI | ✅ Done | 2026-06-28 |

| 3 | product-detail | product page, size selector, WhatsApp button | ✅ Done | 2026-06-28 |

| 4 | cart | localStorage cart, badge, cart page, WhatsApp order | ✅ Done | 2026-06-28 |

| 5 | checkout | checkout form, phone validation, order saved to DB, WhatsApp redirect, confirm page | ✅ Done | 2026-06-29 |
| 6 | admin | password-protected admin panel, order dashboard, status toggle (pending→confirmed→delivered) | ✅ Done | 2026-06-29 |