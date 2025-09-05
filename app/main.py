# app/main.py
from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy import text

from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .db import get_engine, insert_or_ignore

app = FastAPI(title="QuickSet")

# Directories (override via env if you want)
TEMPLATES_DIR = os.getenv("TEMPLATES_DIR", "app/templates")
STATIC_DIR = os.getenv("STATIC_DIR", "app/static")

# Mount /static if the folder exists (optional)
if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

templates = Jinja2Templates(directory=os.getenv("TEMPLATES_DIR", "app/templates"))

# Timezone (Render env var keys you showed)
TZ = os.getenv("APP__TORONTO_TZ") or os.getenv("TZ") or "America/Toronto"

def _resolve_day(day: str) -> date:
    day = (day or "today").lower()
    today = date.today()
    if day in ("", "today"):
        return today
    if day == "tomorrow":
        return today + timedelta(days=1)
    return date.fromisoformat(day)

@app.get("/health", include_in_schema=True)
async def health():
    return {"status": "ok"}

@app.get("/__routes__", include_in_schema=True)
def routes():
    return [getattr(r, "path", None) for r in app.router.routes]

@app.get("/", response_class=HTMLResponse)
def home(request: Request, day: str = Query(default="today")):
    selected = _resolve_day(day)
    return templates.TemplateResponse(
        "home.html",
        {"request": request, "selected": selected.isoformat(), "rows": []},
    )

def _determine_day_param(day: str | None) -> date:
    """
    Accepts: today | tomorrow | yesterday | YYYY-MM-DD
    Defaults to 'today' if invalid or missing.
    """
    day = (day or "today").lower()
    now = datetime.now(ZoneInfo(TZ)).date()
    if day == "today":
        return now
    if day == "tomorrow":
        return date.fromordinal(now.toordinal() + 1)
    if day == "yesterday":
        return date.fromordinal(now.toordinal() - 1)
    try:
        return date.fromisoformat(day)
    except ValueError:
        return now


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def homepage(request: Request, day: str | None = Query(default=None)):
    selected = _determine_day_param(day)

    # TODO: Replace with your real data (DB/query/etc.)
    sample_rows = [
        {"time": "09:00", "title": "Example item A"},
        {"time": "13:30", "title": "Example item B"},
        {"time": "17:00", "title": "Example item C"},
    ]

    return templates.TemplateResponse(
        "home.html",
        {
            "request": request,
            "selected": selected.isoformat(),
            "rows": sample_rows,
            "tz": TZ,
        },
    )


@app.get("/health", include_in_schema=False)
def health():
    return {"status": "ok"}


@app.get("/db_ping", include_in_schema=True)
def db_ping():
    eng = get_engine()
    with eng.begin() as conn:
        one = conn.execute(text("SELECT 1")).scalar()
    return {"ok": one == 1}

@app.post("/refresh", include_in_schema=True)
def refresh_now():
    """
    TEMP seeder so you can see rows on the page.
    Replace later with your real collectors.
    """
    now = datetime.now(tz=TZ)
    start = now.replace(hour=19, minute=0, second=0, microsecond=0)
    end   = now.replace(hour=21, minute=0, second=0, microsecond=0)

    sample = [{
        "facility_id": "demo-cc",
        "facility_name": "Demo Community Centre",
        "district": "Toronto & East York",
        "address": "123 Example St, Toronto",
        "program_name": "Volleyball Drop-in",
        "age_min": 16,
        "age_max": 99,
        "weekday": start.weekday(),
        "start_datetime": start,
        "end_datetime": end,
        "fee_cad": 3.5,
        "reserve_required": False,
        "source_url": "https://www.toronto.ca",
        "last_seen": now,
    }]

    eng = get_engine()
    inserted = insert_or_ignore(eng, sample)
    return {"status": "ok", "inserted": inserted}

@app.get("/", response_class=HTMLResponse)
def home(request: Request, day: str = Query(default="today")):
    selected = _resolve_day(day)
    eng = get_engine()
    q = """
    SELECT facility_name, program_name, start_datetime, end_datetime, address, fee_cad
    FROM dropins
    WHERE DATE(start_datetime AT TIME ZONE 'America/Toronto') = :ymd
    ORDER BY start_datetime, facility_name
    """
    with eng.begin() as conn:
        rows = [dict(r._mapping) for r in conn.execute(text(q), {"ymd": selected.isoformat()})]
    return templates.TemplateResponse("home.html",
        {"request": request, "selected": selected.isoformat(), "rows": rows})
