# app/db.py
import os
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

try:
    # If you have a settings module, we’ll use its URL as a fallback
    from app.config import settings  # type: ignore
except Exception:  # pragma: no cover
    settings = None  # fallback to env only


_engine: Optional[Engine] = None
_SessionLocal: Optional[sessionmaker] = None


def _normalize_db_url(url: str) -> str:
    """
    Ensure SQLAlchemy uses the psycopg3 driver.
    Render and many libraries still emit postgres:// or postgresql:// without a driver.
    """
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    if url.startswith("postgresql://") and "+psycopg" not in url:
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        raw_url = os.getenv("DATABASE_URL")
        if not raw_url and settings is not None:
            # fall back to your settings object if present
            raw_url = getattr(getattr(settings, "database", settings), "url", None)

        if not raw_url:
            raise RuntimeError(
                "No database URL found. Set DATABASE_URL env or settings.database.url"
            )

        url = _normalize_db_url(raw_url)
        _engine = create_engine(url, pool_pre_ping=True, future=True)
    return _engine


def get_sessionmaker() -> sessionmaker:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False, future=True)
    return _SessionLocal
