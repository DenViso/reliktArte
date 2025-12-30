from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, APIRouter
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from .middlewares.request_logger import RequestAuditMiddleware
app.add_middleware(RequestAuditMiddleware)



from .core.config import settings
from .core.caching import init_caching
from .user.router import router as user_router
from .product.router import router as product_router
from .order.router import router as order_router
from .nova_post.router import router as nova_post_router
from .letter.router import router as letter_router


# Lifespan events
@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa
    # Initialize the cache backend
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



app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://relikt-c7kep6ss6-denvisos-projects.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

    @app.middleware("http")
async def redirect_https(request, call_next):
    if request.url.scheme != "https":
    url = request.url.replace(scheme="https")
    return RedirectResponse(url)
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

# Mount static directory (optional - only if directory exists)
static_path = Path(settings.static.directory)
if static_path.exists() and static_path.is_dir():
    app.mount(
        f"/{settings.static.directory}",
        StaticFiles(directory=settings.static.directory),
        name="static"
    )
else:
    print(f"Warning: Static directory '{settings.static.directory}' not found, skipping static files")

