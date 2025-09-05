# app/refresh.py
from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
from typing import List
from zoneinfo import ZoneInfo
from datetime import datetime

from .db import get_engine, insert_or_ignore

@dataclass
class Facility:
    facility_id: str
    facility_name: str
    district: str = ""
    address: str = ""
    # names your collectors expect:
    active_search_url: str | None = None
    dropin_page_url: str | None = None

def _resolve_path(path: str) -> Path:
    p = Path(path)
    if not p.is_absolute():
        # repo root relative to app/
        base = Path(__file__).resolve().parent.parent
        p = (base / p).resolve()
    return p

def load_facilities(path: str = "facilities.json") -> List[Facility]:
    p = _resolve_path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    facs: List[Facility] = []
    for d in data:
        facs.append(
            Facility(
                facility_id=d["facility_id"],
                facility_name=d["facility_name"],
                district=d.get("district", ""),
                address=d.get("address", ""),
                # be flexible with possible alt keys in your JSON:
                active_search_url=d.get("active_search_url") or d.get("active_url") or d.get("activeSearchUrl"),
                dropin_page_url=d.get("dropin_page_url") or d.get("dropin_url") or d.get("dropinPageUrl"),
            )
        )
    return facs

# Optional: keep this function if you want a single entry point
def run_refresh() -> int:
    from .collectors.active_communities import collect_from_active
    from .collectors.facility_pages import collect_from_dropin_page_async

    tz = ZoneInfo("America/Toronto")
    facilities = load_facilities("facilities.json")

    all_rows = []

    # A) Active Communities (sync)
    for fac in facilities:
        try:
            rows = collect_from_active(fac, tz)
            all_rows.extend(rows)
        except Exception:
            # don't crash entire run; collectors may fail for some centres
            import logging; logging.exception("Active parse failed for %s", fac.facility_name)

    # B) Facility “Drop-in Programs” pages (async, per-facility)
    import asyncio
    async def go():
        from itertools import chain
        tasks = []
        for fac in facilities:
            if not fac.dropin_page_url:
                continue
            tasks.append(collect_from_dropin_page_async(fac, tz))
        if not tasks:
            return []
        results = await asyncio.gather(*tasks, return_exceptions=True)
        rows = []
        for r in results:
            if isinstance(r, Exception):
                import logging; logging.exception("Facility page task failed: %s", r)
            elif r:
                rows.extend(r)
        return rows

    try:
        rows_b = asyncio.run(go())
        # merge, avoiding duplicates (same unique key as DB)
        seen = {(r["facility_id"], r["start_datetime"], r["program_name"]) for r in all_rows}
        for r in rows_b:
            key = (r["facility_id"], r["start_datetime"], r["program_name"])
            if key not in seen:
                all_rows.append(r)
                seen.add(key)
    except Exception:
        import logging; logging.exception("Facility pages stage failed")

    eng = get_engine()
    return insert_or_ignore(eng, all_rows)
