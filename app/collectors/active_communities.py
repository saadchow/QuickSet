from __future__ import annotations
from typing import List, Dict, Any
import logging
import requests
from bs4 import BeautifulSoup
from zoneinfo import ZoneInfo
from ..settings import settings
from .common import Facility, normalize_record

log = logging.getLogger(__name__)

def collect_from_active(facility: Facility, tz: ZoneInfo) -> List[Dict[str, Any]]:
    """
    Parse server-rendered Active Communities "Activity Search" results for volleyball.
    Structure may change; use resilient lookups.
    """
    if not facility.active_search_url:
        return []
    headers = { "User-Agent": settings.app.user_agent }
    resp = requests.get(facility.active_search_url, headers=headers, timeout=settings.app.request_timeout_seconds)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    rows = []
    for card in soup.select("div,li,section"):
        text = card.get_text(" ", strip=True).lower()
        if "volleyball" not in text:
            continue

        program_name = "Volleyball Drop-in"
        heading = card.find(["h2","h3","h4"])
        if heading and "volleyball" in heading.get_text(strip=True).lower():
            program_name = heading.get_text(strip=True)

        time_text = None
        age_text = None
        fee_text = None
        reserve_required = "register" in text or "reserve" in text

        frag = card.find(string=lambda s: isinstance(s, str) and ("am" in s.lower() or "pm" in s.lower()))
        if frag:
            time_text = frag.strip()

        aget = card.find(string=lambda s: isinstance(s, str) and ("ages" in s.lower() or "+" in s))
        if aget:
            age_text = aget.strip()

        feet = card.find(string=lambda s: isinstance(s, str) and ("$" in s))
        if feet:
            fee_text = feet.strip()

        day_date = None
        dates = card.find_all("time")
        if dates:
            try:
                from dateutil import parser as dateparser
                day_date = dateparser.parse(dates[0].get("datetime") or dates[0].get_text(strip=True)).date()
            except Exception:
                day_date = None

        if day_date is None:
            import re
            try:
                from dateutil import parser as dateparser
                m = re.search(r"(Mon|Tue|Wed|Thu|Fri|Sat|Sun)[,\s]+([A-Za-z]{3})\s+(\d{1,2}),\s*(\d{4})", card.get_text(" ", strip=True))
                if m:
                    day_date = dateparser.parse(m.group(0)).date()
            except Exception:
                day_date = None

        if not (time_text and day_date):
            continue

        rows.append(normalize_record(
            facility=facility,
            program_name=program_name,
            age_text=age_text,
            day_date=day_date,
            time_text=time_text,
            fee_text=fee_text,
            reserve_required=reserve_required,
            source_url=facility.active_search_url,
            tz=tz
        ))
    log.info("Active search parsed %d entries for %s", len(rows), facility.facility_name)
    return rows
