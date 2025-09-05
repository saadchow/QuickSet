# app/main.py
from __future__ import annotations

import os
from datetime import date, datetime
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(title="QuickSet")

# Directories (override via env if you want)
TEMPLATES_DIR = os.getenv("TEMPLATES_DIR", "app/templates")
STATIC_DIR = os.getenv("STATIC_DIR", "app/static")

# Mount /static if the folder exists (optional)
if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Timezone (Render env var keys you showed)
TZ = os.getenv("APP__TORONTO_TZ") or os.getenv("TZ") or "America/Toronto"


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
