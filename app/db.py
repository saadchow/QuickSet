# app/db.py
from __future__ import annotations

import os
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

_engine: Optional[Engine] = None


def _normalize_db_url(raw: str) -> str:
    """Normalize Postgres URLs for SQLAlchemy + psycopg3."""
    if raw.startswith("postgres://"):
        raw = raw.replace("postgres://", "postgresql://", 1)
    if raw.startswith("postgresql://") and "+psycopg" not in raw:
        raw = raw.replace("postgresql://", "postgresql+psycopg://", 1)
    return raw


def get_engine() -> Engine:
    """Create (or reuse) a global SQLAlchemy engine."""
    global _engine
    if _engine is not None:
        return _engine

    # Prefer your Render env var, then common fallbacks.
    raw = (
        os.getenv("APP__DB_URL")
        or os.getenv("DATABASE_URL")
        or os.getenv("DATABASE__URL")
    )

    if not raw:
        raise RuntimeError(
            "No database URL found. Set APP__DB_URL (or DATABASE_URL)."
        )

    url = _normalize_db_url(raw)
    _engine = create_engine(url, pool_pre_ping=True)
    return _engine
