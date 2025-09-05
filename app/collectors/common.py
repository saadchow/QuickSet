from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict, Any
from zoneinfo import ZoneInfo
from datetime import datetime, date
import logging
from ..parsers import parse_age_range, parse_time_range, iso_weekday_name

log = logging.getLogger(__name__)

@dataclass
class Facility:
    facility_id: str
    facility_name: str
    district: str
    address: str
    active_search_url: Optional[str] = None
    dropin_page_url: Optional[str] = None

def normalize_record(
    facility: Facility,
    program_name: str,
    age_text: Optional[str],
    day_date: date,
    time_text: str,
    fee_text: Optional[str],
    reserve_required: bool,
    source_url: str,
    tz: ZoneInfo
) -> Dict[str, Any]:
    age_min, age_max = parse_age_range(age_text or "")
    start_dt, end_dt = parse_time_range(time_text, day_date, tz)
    weekday = iso_weekday_name(day_date)
    fee_cad = None
    if fee_text:
        import re
        m = re.search(r"(\d+(?:\.\d{2})?)", fee_text)
        if m:
            fee_cad = float(m.group(1))
    now = datetime.now(tz)
    record = {
        "facility_id": facility.facility_id,
        "facility_name": facility.facility_name,
        "address": facility.address,
        "district": facility.district,
        "program_name": program_name.strip(),
        "age_min": age_min,
        "age_max": age_max,
        "weekday": weekday,
        "start_datetime": start_dt,
        "end_datetime": end_dt,
        "fee_cad": fee_cad,
        "reserve_required": bool(reserve_required),
        "source_url": source_url,
        "last_seen": now,
    }
    log.debug("Normalized record: %s", record)
    return record
