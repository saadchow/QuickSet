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

import traceback, logging
from fastapi import HTTPException
from .refresh import  run_refresh, load_facilities, Facility

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

app = FastAPI(title="QuickSet")

# Paths
TEMPLATES_DIR = os.getenv("TEMPLATES_DIR", "app/templates")
STATIC_DIR = os.getenv("STATIC_DIR", "app/static")

if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Proper tzinfo object (NOT a plain string)
TZ = ZoneInfo(os.getenv("APP__TORONTO_TZ", "America/Toronto"))

@app.get("/count")
def count_rows():
    eng = get_engine()
    with eng.begin() as c:
        n = c.execute(text("SELECT COUNT(*) FROM dropins")).scalar()
    return {"rows": int(n or 0)}

@app.get("/recent")
def recent(limit: int = 25):
    eng = get_engine()
    q = """
    SELECT facility_name, program_name, start_datetime, end_datetime, address, fee_cad
    FROM dropins
    ORDER BY start_datetime DESC
    LIMIT :lim
    """
    with eng.begin() as c:
        rows = [dict(r._mapping) for r in c.execute(text(q), {"lim": limit})]
    return {"rows": rows}


def _resolve_day(day: str | None) -> date:
    day = (day or "today").lower().strip()
    today = date.today()
    if day in ("", "today"):
        return today
    if day == "tomorrow":
        return today + timedelta(days=1)
    if day == "yesterday":
        return today - timedelta(days=1)
    return date.fromisoformat(day)  # YYYY-MM-DD

@app.get("/health", include_in_schema=True)
def health():
    return {"status": "ok"}

@app.get("/__routes__", include_in_schema=True)
def routes():
    return [getattr(r, "path", None) for r in app.router.routes]

@app.get("/db_ping", include_in_schema=True)
def db_ping():
    eng = get_engine()
    with eng.begin() as conn:
        one = conn.execute(text("SELECT 1")).scalar()
    return {"ok": one == 1}

# helper to run collectors without writing to DB
def _run_refresh_debug():
    from .refresh import load_facilities  # your loader
    # try to import collectors; tolerate missing ones
    try:
        from .collectors.active_communities import collect_from_active
    except Exception:
        collect_from_active = None
    try:
        from .collectors.facility_pages import collect_from_dropin_page_async
    except Exception:
        collect_from_dropin_page_async = None

    facs = load_facilities(os.getenv("PATHS__FACILITIES_FILE", "facilities.json"))
    meta = {"active": 0, "facility_pages": 0}
    rows = []

    # A) Active listings (requests/bs4)
    if collect_from_active:
        for fac in facs:
            try:
                found = collect_from_active(fac, TZ)
                meta["active"] += len(found)
                rows.extend(found)
            except Exception as e:
                logging.exception("active parser failed for %s: %s", fac.get("facility_name","?"), e)

    # B) Facility “Drop-in Programs” pages (Playwright)
    if collect_from_dropin_page_async:
        try:
            import asyncio
            async def go():
                return await collect_from_dropin_page_async(facs, TZ)
            found_b = asyncio.run(go()) or []
            meta["facility_pages"] += len(found_b)
            rows.extend(found_b)
        except Exception as e:
            logging.exception("facility pages parser failed: %s", e)

    return rows, meta

from .db import get_engine, insert_or_ignore

@app.post("/refresh", include_in_schema=True)
def refresh_now(dry_run: bool = Query(False)):
    try:
        if dry_run:
            # debug: run both collectors but do NOT write to DB
            facs = load_facilities("facilities.json")
            found_total = 0
            by_source = {"active": 0, "facility_pages": 0}
            rows_preview = []

            # A) Active
            try:
                from .collectors.active_communities import collect_from_active
                for fac in facs:
                    r = collect_from_active(fac, TZ)
                    by_source["active"] += len(r)
                    found_total += len(r)
                    rows_preview.extend(r[:1])  # grab a few
            except Exception:
                logging.exception("active debug failed")

            # B) Facility pages
            try:
                from .collectors.facility_pages import collect_from_dropin_page_async
                import asyncio
                async def go():
                    tasks = [collect_from_dropin_page_async(f, TZ) for f in facs if f.dropin_page_url]
                    if not tasks:
                        return []
                    res = await asyncio.gather(*tasks, return_exceptions=True)
                    out = []
                    for rr in res:
                        if isinstance(rr, Exception):
                            logging.exception("facility debug task failed: %s", rr)
                        else:
                            out.extend(rr)
                    return out
                rows_b = asyncio.run(go())
                by_source["facility_pages"] += len(rows_b)
                found_total += len(rows_b)
                rows_preview.extend(rows_b[:1])
            except Exception:
                logging.exception("facility pages debug failed")

            # JSON-safe preview (datetimes → isoformat)
            for r in rows_preview:
                for k in ("start_datetime","end_datetime","last_seen"):
                    if k in r and hasattr(r[k], "isoformat"):
                        r[k] = r[k].isoformat()

            return {"status":"ok","found":found_total,"by_source":by_source,"sample":rows_preview[:5]}

        # real insert
        inserted = run_refresh()
        return {"status":"ok","inserted":inserted}
    except Exception as e:
        logging.exception("refresh failed")
        tb = traceback.format_exc()
        raise HTTPException(status_code=500, detail={"type":type(e).__name__,"error":str(e),"trace":tb[-1800:]})

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
    return templates.TemplateResponse(
        "home.html",
        {"request": request, "selected": selected.isoformat(), "rows": rows, "tz": TZ},
    )
