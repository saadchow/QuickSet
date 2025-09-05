# app/main.py
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, Response, Query
from zoneinfo import ZoneInfo

from app.db import get_engine

try:
    from app.config import settings  # type: ignore
    TORONTO_TZ = getattr(getattr(settings, "app", settings), "toronto_tz", "America/Toronto")
except Exception:  # pragma: no cover
    TORONTO_TZ = "America/Toronto"

app = FastAPI()


# --- Health / probe endpoints (prevents 405 on Render’s HEAD check) ---
@app.head("/", include_in_schema=False)
def head_root() -> Response:
    # empty 204 keeps it cheap and avoids JSON work on probes
    return Response(status_code=204)


@app.get("/", include_in_schema=False)
def homepage(day: Optional[str] = Query(default=None, description="today|tomorrow|yesterday or YYYY-MM-DD")):
    """
    Keep your existing homepage logic here.
    We ensure the DB engine is constructed with psycopg3 and that zoneinfo is available.
    """
    selected = _determine_day_param(day)

    # Touch the engine so a misconfigured driver fails fast during startup
    _ = get_engine()

    # TODO: Replace the return below with your original response
    # (template rendering / JSON / redirect). This stub ensures a 200 OK.
    return {"status": "ok", "selected": selected}


# --- Helpers -------------------------------------------------------------
def _determine_day_param(day: Optional[str]) -> str:
    """
    Interprets `day` relative to Toronto time. Supports today|tomorrow|yesterday
    plus 'YYYY-MM-DD'. Falls back to 'today'.
    """
    tz = ZoneInfo(TORONTO_TZ)
    now = datetime.now(tz=tz).date()

    if not day:
        return "today"

    lower = day.lower()
    if lower == "today":
        return "today"
    if lower == "tomorrow":
        return (now + timedelta(days=1)).isoformat()
    if lower == "yesterday":
        return (now - timedelta(days=1)).isoformat()

    # Try ISO date
    try:
        _ = datetime.fromisoformat(day).date()
        return day  # valid ISO date string
    except Exception:
        return "today"
