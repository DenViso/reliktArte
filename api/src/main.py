from contextlib import asynccontextmanager
from pathlib import Path
import os
from fastapi import FastAPI, APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from fastapi.middleware.cors import CORSMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from .middlewares.request_logger import RequestAuditMiddleware
from .core.config import settings
from .core.caching import init_caching
from .user.router import router as user_router
from .product.router import router as product_router
from .order.router import router as order_router
from .nova_post.router import router as nova_post_router
from .letter.router import router as letter_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_caching()
    yield


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    version=str(settings.app_version),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# 1. ProxyHeaders ПЕРШИМ - для правильної роботи з Railway
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

# 2. CORS ДРУГИМ - ДО RequestAuditMiddleware
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "https://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://relikt.vercel.app",
    "https://relikt-arte.vercel.app",
    "http://reliktarte-production.up.railway.app",
    "https://reliktarte-production.up.railway.app",
]

print(f"🔧 CORS Configuration:")
print(f"   Allowed Origins: {ALLOWED_ORIGINS}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# 3. Request Audit ТРЕТІМ
app.add_middleware(RequestAuditMiddleware)


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


# Mount static directory
# main.py знаходиться в /app/api/src/main.py
# static знаходиться в /app/api/static
# Тому потрібно піднятися на рівень вгору: parent.parent / "static"
BASE_DIR = Path(__file__).resolve().parent  # /app/api/src
STATIC_DIR = BASE_DIR.parent / "static"     # /app/api/static

print(f"🔍 Looking for static at: {STATIC_DIR}")
print(f"   Base dir: {BASE_DIR}")
print(f"   Static exists: {STATIC_DIR.exists()}")

if STATIC_DIR.exists() and STATIC_DIR.is_dir():
    try:
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
        
        # Підрахунок файлів для діагностики
        files_count = sum(1 for f in STATIC_DIR.rglob("*") if f.is_file())
        print(f"✅ Static files mounted from {STATIC_DIR}")
        print(f"📁 Total files in static: {files_count}")
    except Exception as e:
        print(f"❌ Error mounting static: {e}")
else:
    print(f"⚠️ Static directory not found at {STATIC_DIR}")
    # Додаткова діагностика
    if BASE_DIR.parent.exists():
        contents = [item.name for item in BASE_DIR.parent.iterdir()]
        print(f"   Contents of {BASE_DIR.parent}: {contents}")


# Діагностичний endpoint (можна видалити після налагодження)
@app.get("/debug/static-check")
async def check_static():
    """Діагностика статичних файлів"""
    result = {
        "main_py_location": str(Path(__file__).resolve()),
        "base_dir": str(BASE_DIR),
        "static_dir": str(STATIC_DIR),
        "static_exists": STATIC_DIR.exists(),
        "static_is_dir": STATIC_DIR.is_dir() if STATIC_DIR.exists() else False,
    }
    
    if STATIC_DIR.exists() and STATIC_DIR.is_dir():
        try:
            files = [str(f.relative_to(STATIC_DIR)) for f in STATIC_DIR.rglob("*") if f.is_file()]
            result["total_files"] = len(files)
            result["sample_files"] = files[:20]  # Перші 20 файлів
        except Exception as e:
            result["error"] = str(e)
    
    return result


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")