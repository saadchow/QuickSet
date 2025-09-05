from __future__ import annotations
import logging
from fastapi import FastAPI, Query, Response, status, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from typing import Optional
from zoneinfo import ZoneInfo
from datetime import datetime
from .settings import settings
from .db import get_engine, query_dropins
from .refresh import run_refresh
from .ics import rows_to_ics

logging.basicConfig(level=getattr(logging, settings.app.log_level.upper(), "INFO"))
log = logging.getLogger(__name__)

app = FastAPI(title="Toronto Volleyball Drop-ins")
templates = Jinja2Templates(directory="app/templates")

DAY_MAP = {
    "Mon": "Monday",
    "Tue": "Tuesday",
    "Wed": "Wednesday",
    "Thu": "Thursday",
    "Fri": "Friday",
    "Sat": "Saturday",
    "Sun": "Sunday",
}

def parse_after(s: Optional[str]) -> Optional[int]:
    if not s:
        return None
    try:
        parts = s.split(":")
        hh = int(parts[0])
        mm = int(parts[1]) if len(parts) > 1 else 0
        return hh * 60 + mm
    except Exception:
        return None

def parse_age_filter(s: Optional[str]) -> Optional[int]:
    if not s:
        return None
    try:
        if s.endswith("+"):
            return int(s[:-1])
        return int(s)
    except Exception:
        return None

def _determine_day_param(day_param: str | None) -> str:
    if day_param in DAY_MAP:
        return day_param
    tz = ZoneInfo(settings.app.toronto_tz)
    idx = datetime.now(tz).weekday()  # 0=Mon
    return ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"][idx]

def _age_text(age_min, age_max):
    if age_min is None and age_max is None:
        return None
    if age_min is not None and age_max is None:
        return f"{age_min}+"
    if age_min is None and age_max is not None:
        return f"≤{age_max}"
    return f"{age_min}-{age_max}"

@app.get("/", response_class=HTMLResponse)
def homepage(request: Request, day: str | None = None):
    selected = _determine_day_param(day)
    eng = get_engine()
    rows = query_dropins(eng, day=selected)

    tz = ZoneInfo(settings.app.toronto_tz)
    by_fac = {}
    for r in rows:
        fid = r["facility_id"]
        by_fac.setdefault(fid, {
            "facility_name": r["facility_name"],
            "address": r.get("address",""),
            "district": r.get("district",""),
            "reserve_required": r.get("reserve_required", False),
            "entries": []
        })
        s = r["start_datetime"].astimezone(tz)
        e = r["end_datetime"].astimezone(tz)
        time_fmt = s.strftime("%-I:%M %p") + " – " + e.strftime("%-I:%M %p")
        by_fac[fid]["entries"].append({
            "time_fmt": time_fmt,
            "program_name": r["program_name"],
            "age_text": _age_text(r.get("age_min"), r.get("age_max")),
            "fee_cad": r.get("fee_cad"),
            "source_url": r.get("source_url"),
        })

    groups = list(by_fac.values())
    groups.sort(key=lambda g: (g["district"], g["facility_name"]))
    days = [{"value":k, "label":v} for k,v in DAY_MAP.items()]

    return templates.TemplateResponse("home.html", {
        "request": request,
        "days": days,
        "selected_day": selected,
        "selected_day_full": DAY_MAP[selected],
        "groups": groups
    })

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

@app.get("/dropins")
def get_dropins(
    day: Optional[str] = Query(default=None, description="Mon|Tue|Wed|Thu|Fri|Sat|Sun"),
    after: Optional[str] = Query(default=None, description="Time like 18:00 (24h)"),
    district: Optional[str] = Query(default=None, description="City district (e.g., South/East/West/North)"),
    age: Optional[str] = Query(default=None, description="Age or min like 19+ or 19")
):
    day = day if day in {"Mon","Tue","Wed","Thu","Fri","Sat","Sun"} else None
    after_minutes = parse_after(after)
    age_num = parse_age_filter(age)
    eng = get_engine()
    rows = query_dropins(eng, day=day, district=district, after_minutes=after_minutes, age=age_num)
    for r in rows:
        r["start_datetime"] = r["start_datetime"].isoformat()
        r["end_datetime"] = r["end_datetime"].isoformat()
        r["last_seen"] = r["last_seen"].isoformat()
    return {"count": len(rows), "items": rows}

@app.post("/refresh", status_code=200)
def post_refresh():
    try:
        n = run_refresh()
        return {"status": "ok", "processed": n}
    except Exception as e:
        log.exception("Refresh failed: %s", e)
        return Response(content=f"Refresh failed: {e}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

@app.get("/ics")
def get_ics(id: Optional[str] = Query(default=None, description="facility_id to export")):
    if not id:
        return Response(content="Missing id", status_code=400)
    eng = get_engine()
    rows = query_dropins(eng)
    rows = [r for r in rows if r["facility_id"] == id]
    data = rows_to_ics(rows)
    return Response(content=data, media_type="text/calendar")
