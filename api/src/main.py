from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
# Додаємо цей імпорт для правильної роботи за проксі Railway
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from .middlewares.request_logger import RequestAuditMiddleware
from .core.config import settings
from .core.caching import init_caching
from .user.router import router as user_router
from .product.router import router as product_router
from .order.router import router as order_router
from .nova_post.router import router as nova_post_router
from .letter.router import router as letter_router


# Lifespan events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize cache
    init_caching()
    yield


# App configuration
app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    version=str(settings.app_version),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# 1. Додаємо Middleware для обробки заголовків проксі (Railway)
# Це вирішує проблему Mixed Content на рівні протоколу
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

# 2. Аудит запитів
app.add_middleware(RequestAuditMiddleware)

# 3. Налаштування CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://relikt.vercel.app",
        "https://relikt-arte.vercel.app", # Додав ваш основний домен
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ПРИМІТКА: Старий блок redirect_https видалено, 
# бо він конфліктував з HTTPS-проксі Railway.

# Include routers
routers: list[APIRouter] = [
    user_router,
    product_router,
    order_router,
    nova_post_router,
    letter_router,
]

for router in routers:
    app.include_router(router, prefix=f"/api/v{settings.app_version}")


# Mount static directory if exists
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
    print("✅ Static files mounted successfully at /static")
except Exception as e:
    print(f"⚠️ Warning: Could not mount static directory: {e}")

# Це важливо для Swagger/Docs, щоб вони розуміли, де шукати схеми
@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")