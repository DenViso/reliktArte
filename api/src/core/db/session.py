from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
)
from ..config import settings


def get_async_engine() -> AsyncEngine:
    # Конвертувати postgresql:// в postgresql+psycopg://
    db_url = str(settings.db.url)
    print(f"ORIGINAL DB URL: {db_url}")  # DEBUG
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)
    print(f"CONVERTED DB URL: {db_url}")  # DEBUG
    
    return create_async_engine(
        db_url,
        echo=True if settings.debug else False,
        future=True,
        pool_pre_ping=True,
        pool_size=50,  # Зменшив з 1000 - Railway має ліміти
        max_overflow=10,  # Зменшив з 150
    )


def create_async_session_maker() -> async_sessionmaker:
    engine: AsyncEngine = get_async_engine()
    return async_sessionmaker(engine, autoflush=False, expire_on_commit=False)