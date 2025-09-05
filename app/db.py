from __future__ import annotations
from sqlalchemy import (
    create_engine, MetaData, Table, Column, Integer, String, DateTime, Boolean, Float,
    UniqueConstraint, text, select
)
from sqlalchemy.engine import Engine
from typing import Optional, List, Dict, Any
from .settings import settings

metadata = MetaData()

dropins = Table(
    "dropins",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("facility_id", String, nullable=False),
    Column("facility_name", String, nullable=False),
    Column("address", String, nullable=True),
    Column("district", String, nullable=True),
    Column("program_name", String, nullable=False),
    Column("age_min", Integer, nullable=True),
    Column("age_max", Integer, nullable=True),
    Column("weekday", String, nullable=False),
    Column("start_datetime", DateTime(timezone=True), nullable=False),
    Column("end_datetime", DateTime(timezone=True), nullable=False),
    Column("fee_cad", Float, nullable=True),
    Column("reserve_required", Boolean, nullable=False, server_default=text("0")),
    Column("source_url", String, nullable=False),
    Column("last_seen", DateTime(timezone=True), nullable=False),
    UniqueConstraint("facility_id", "start_datetime", "program_name", name="uq_event"),
)

_engine: Optional[Engine] = None

def get_engine() -> Engine:
    """Build a pooled engine for either SQLite or Postgres."""
    global _engine
    if _engine is None:
        _engine = create_engine(
            settings.app.db_url,
            future=True,
            pool_pre_ping=True,   # heal stale connections (esp. serverless Postgres)
        )
        metadata.create_all(_engine)
    return _engine

def insert_or_ignore(engine: Engine, rows: List[Dict[str, Any]]) -> int:
    """
    Idempotent bulk insert:
      - SQLite: 'INSERT OR IGNORE'
      - Postgres: ON CONFLICT DO NOTHING (constraint uq_event)
    """
    if not rows:
        return 0
    dialect = engine.dialect.name

    if dialect == "postgresql":
        # Use Postgres upsert (do-nothing) on our unique constraint
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        stmt = pg_insert(dropins).values(rows).on_conflict_do_nothing(
            constraint="uq_event"
        )
        with engine.begin() as conn:
            result = conn.execute(stmt)
            # rowcount may exclude conflicted rows; OK to return best-effort
            return result.rowcount or 0

    elif dialect == "sqlite":
        # Use native INSERT OR IGNORE
        inserted = 0
        sql = text("""
            INSERT OR IGNORE INTO dropins
            (facility_id, facility_name, address, district, program_name,
             age_min, age_max, weekday, start_datetime, end_datetime, fee_cad,
             reserve_required, source_url, last_seen)
            VALUES
            (:facility_id, :facility_name, :address, :district, :program_name,
             :age_min, :age_max, :weekday, :start_datetime, :end_datetime, :fee_cad,
             :reserve_required, :source_url, :last_seen)
        """)
        with engine.begin() as conn:
            for r in rows:
                conn.execute(sql, r)
                inserted += 1
        return inserted

    else:
        # Fallback: naive per-row try/except (works for other DBs but slower)
        inserted = 0
        with engine.begin() as conn:
            for r in rows:
                try:
                    conn.execute(
                        text("""
                            INSERT INTO dropins
                            (facility_id, facility_name, address, district, program_name,
                             age_min, age_max, weekday, start_datetime, end_datetime, fee_cad,
                             reserve_required, source_url, last_seen)
                            VALUES
                            (:facility_id, :facility_name, :address, :district, :program_name,
                             :age_min, :age_max, :weekday, :start_datetime, :end_datetime, :fee_cad,
                             :reserve_required, :source_url, :last_seen)
                        """),
                        r,
                    )
                    inserted += 1
                except Exception:
                    # assume conflict; ignore
                    pass
        return inserted

def query_dropins(
    engine: Engine,
    day: Optional[str] = None,
    district: Optional[str] = None,
    after_minutes: Optional[int] = None,
    age: Optional[int] = None,
) -> List[Dict[str, Any]]:
    sel = select(dropins)
    clauses = []
    if day:
        clauses.append(dropins.c.weekday == day)
    if district:
        clauses.append(dropins.c.district == district)
    if age is not None:
        from sqlalchemy import and_
        clauses.append(
            and_(
                (dropins.c.age_min.is_(None)) | (dropins.c.age_min <= age),
                (dropins.c.age_max.is_(None)) | (dropins.c.age_max >= age),
            )
        )
    if clauses:
        from sqlalchemy import and_ as _and
        sel = sel.where(_and(*clauses))
    sel = sel.order_by(dropins.c.start_datetime.asc())

    results: List[Dict[str, Any]] = []
    with engine.connect() as conn:
        rows = conn.execute(sel).mappings().all()
        for r in rows:
            if after_minutes is not None:
                tod = r["start_datetime"].hour * 60 + r["start_datetime"].minute
                if tod < after_minutes:
                    continue
            results.append(dict(r))
    return results
