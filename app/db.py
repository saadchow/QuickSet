# app/db.py
from __future__ import annotations
import os
from typing import Iterable, Dict, Any
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

_engine: Engine | None = None

def _normalize(url: str) -> str:
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if url.startswith("postgresql://") and "+psycopg" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    if "neon.tech" in url and "sslmode=" not in url:
        url += ("&" if "?" in url else "?") + "sslmode=require"
    return url

def get_engine() -> Engine:
    global _engine
    if _engine is not None:
        return _engine
    raw = os.getenv("APP__DB_URL") or os.getenv("DATABASE_URL")
    if not raw:
        raise RuntimeError("APP__DB_URL not set")
    _engine = create_engine(_normalize(raw), pool_pre_ping=True)
    _init_schema(_engine)
    return _engine

def _init_schema(engine: Engine) -> None:
    ddl = """
    CREATE TABLE IF NOT EXISTS dropins (
        id BIGSERIAL PRIMARY KEY,
        facility_id TEXT NOT NULL,
        facility_name TEXT NOT NULL,
        district TEXT,
        address TEXT,
        program_name TEXT NOT NULL,
        age_min INT,
        age_max INT,
        weekday INT,
        start_datetime TIMESTAMPTZ NOT NULL,
        end_datetime   TIMESTAMPTZ NOT NULL,
        fee_cad NUMERIC,
        reserve_required BOOLEAN,
        source_url TEXT,
        last_seen TIMESTAMPTZ NOT NULL,
        CONSTRAINT uq_dropin UNIQUE (facility_id, start_datetime, program_name)
    );
    """
    with engine.begin() as c:
        c.execute(text(ddl))

def insert_or_ignore(engine: Engine, rows: Iterable[Dict[str, Any]]) -> int:
    rows = list(rows)  # safe for generators
    if not rows:
        return 0
    sql = """
    INSERT INTO dropins (
      facility_id, facility_name, district, address, program_name,
      age_min, age_max, weekday, start_datetime, end_datetime,
      fee_cad, reserve_required, source_url, last_seen
    ) VALUES (
      :facility_id, :facility_name, :district, :address, :program_name,
      :age_min, :age_max, :weekday, :start_datetime, :end_datetime,
      :fee_cad, :reserve_required, :source_url, :last_seen
    )
    ON CONFLICT ON CONSTRAINT uq_dropin DO NOTHING
    """
    inserted = 0
    with engine.begin() as c:
        for r in rows:
            res = c.execute(text(sql), r)
            # rowcount is 1 for inserted, 0 for conflict (Postgres)
            inserted += (res.rowcount or 0)
    return inserted
