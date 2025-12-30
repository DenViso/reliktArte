from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

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

# Add middlewares
app.add_middleware(RequestAuditMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[ "http://localhost:5173",          # Vite local
        "http://127.0.0.1:5173",                      # локально
        "https://ТВІЙ-ФРОНТ.vercel.app", ]             # Vercel], 
    allow_origin_regex=r"https://.*\.vercel\.app",  # всі фронтенди на vercel
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# HTTP -> HTTPS redirect middleware
# @app.middleware("http")
# async def redirect_https(request: Request, call_next):
    # if request.method == "OPTIONS":
    #     return await call_next(request)  # пропускаємо preflight
    # if request.url.scheme != "https":
    #     url = request.url.replace(scheme="https")
    #     return RedirectResponse(url=str(url))
    # response = await call_next(request)
    # return response
    
    
    @app.middleware("http")
async def redirect_https(request: Request, call_next):
    if request.method == "OPTIONS":
        return await call_next(request)

    proto = request.headers.get("x-forwarded-proto")
    if proto == "http":
        url = request.url.replace(scheme="https")
        return RedirectResponse(url=str(url), status_code=307)

    return await call_next(request)


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
static_path = Path(settings.static.directory)
if static_path.exists() and static_path.is_dir():
    app.mount(
        f"/{settings.static.directory}",
        StaticFiles(directory=settings.static.directory),
        name="static",
    )
else:
    print(f"Warning: Static directory '{settings.static.directory}' not found, skipping static files")
