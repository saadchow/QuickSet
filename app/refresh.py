from __future__ import annotations
import json, asyncio, logging
from typing import List, Dict, Any
from zoneinfo import ZoneInfo
from .settings import settings
from .db import get_engine, insert_or_ignore
from .collectors.common import Facility
from .collectors.active_communities import collect_from_active
from .collectors.facility_pages import collect_from_dropin_page_async

log = logging.getLogger(__name__)

def load_facilities(path: str) -> List[Facility]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    facilities: List[Facility] = []
    for d in data:
        facilities.append(Facility(
            facility_id=d["facility_id"],
            facility_name=d["facility_name"],
            district=d.get("district", ""),
            address=d.get("address", ""),
            active_search_url=d.get("active_search_url"),
            dropin_page_url=d.get("dropin_page_url"),
        ))
    return facilities

async def _run_async(facilities: List[Facility]) -> int:
    tz = ZoneInfo(settings.app.toronto_tz)
    all_rows: List[Dict[str, Any]] = []
    for fac in facilities:
        try:
            rows_a = collect_from_active(fac, tz)
            all_rows.extend(rows_a)
        except Exception as e:
            log.exception("Active search failed for %s: %s", fac.facility_name, e)
        try:
            rows_b = await collect_from_dropin_page_async(fac, tz)
            seen = {(r["facility_id"], r["start_datetime"], r["program_name"]) for r in all_rows}
            for r in rows_b:
                k = (r["facility_id"], r["start_datetime"], r["program_name"])
                if k not in seen:
                    all_rows.append(r)
        except Exception as e:
            log.exception("Facility page failed for %s: %s", fac.facility_name, e)

    engine = get_engine()
    inserted = insert_or_ignore(engine, all_rows)
    log.info("Inserted (or ignored) %d rows", inserted)
    return inserted

def run_refresh() -> int:
    facilities = load_facilities(settings.paths.facilities_file)
    return asyncio.run(_run_async(facilities))

if __name__ == "__main__":
    logging.basicConfig(level=getattr(logging, settings.app.log_level.upper(), "INFO"))
    n = run_refresh()
    print(f"Refresh complete. Rows processed: {n}")
