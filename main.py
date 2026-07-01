from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware

from database.db import init_db
from routers import admin, cart, orders, products


class CacheControlMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        path = request.url.path
        if path.startswith("/static/uploads/"):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        elif path.startswith("/static/"):
            response.headers["Cache-Control"] = "public, max-age=86400"
        else:
            response.headers["Cache-Control"] = "no-cache"
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


_templates = Jinja2Templates(directory="templates")

app = FastAPI(lifespan=lifespan)
app.add_middleware(CacheControlMiddleware)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(products.router)
app.include_router(cart.router)
app.include_router(orders.router)
app.include_router(admin.router)


@app.exception_handler(404)
async def not_found_handler(request: Request, exc) -> HTMLResponse:
    return _templates.TemplateResponse("404.html", {"request": request}, status_code=404)
