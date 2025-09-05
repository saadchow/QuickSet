from __future__ import annotations
from typing import List, Dict, Any
import logging, random, asyncio, re
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from zoneinfo import ZoneInfo
from datetime import timedelta
from ..settings import settings
from .common import Facility, normalize_record
from ..parsers import parse_week_header

log = logging.getLogger(__name__)

async def _fetch_html(url: str) -> str:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(user_agent=settings.app.user_agent)
        await page.goto(url, wait_until="networkidle", timeout=settings.app.request_timeout_seconds * 1000)
        html = await page.content()
        await asyncio.sleep(random.uniform(settings.app.polite_delay_seconds_min, settings.app.polite_delay_seconds_max))
        await browser.close()
        return html

async def collect_from_dropin_page_async(facility: Facility, tz: ZoneInfo) -> List[Dict[str, Any]]:
    if not facility.dropin_page_url:
        return []
    html = await _fetch_html(facility.dropin_page_url)
    soup = BeautifulSoup(html, "lxml")

    week_ref_date = None
    header = soup.find(string=lambda s: isinstance(s, str) and "week of" in s.lower())
    if header:
        week_ref_date = parse_week_header(header)
    if week_ref_date is None:
        from datetime import datetime
        now = datetime.now(tz).date()
        while now.weekday() != 0:
            now = now - timedelta(days=1)
        week_ref_date = now

    items: List[Dict[str, Any]] = []
    day_names = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    for i, day_label in enumerate(day_names):
        for heading in soup.find_all(lambda tag: tag.name in ["h2","h3","h4"] and day_label.lower() in tag.get_text(strip=True).lower()):
            day_date = week_ref_date + timedelta(days=i)
            sib = heading.find_next_sibling()
            while sib and sib.name not in ["h2","h3","h4"]:
                text = sib.get_text(" ", strip=True)
                if "volleyball" in text.lower():
                    m = re.search(r"(\d{1,2}:?\d{0,2}\s*(?:AM|PM|am|pm)\s*[-–—to]+\s*\d{1,2}:?\d{0,2}\s*(?:AM|PM|am|pm))", text)
                    timefrag = m.group(1) if m else None
                    m2 = re.search(r"(\d+\s*\+|\d+\s*[–-]\s*\d+|All ages|all ages|Adults.*\d+)", text)
                    age_text = m2.group(1) if m2 else None
                    m3 = re.search(r"\$\s*\d+(?:\.\d{2})?", text)
                    fee_text = m3.group(0) if m3 else None
                    reserve_required = "reserve" in text.lower() or "register" in text.lower()
                    if timefrag:
                        items.append(normalize_record(
                            facility=facility,
                            program_name="Volleyball Drop-in",
                            age_text=age_text,
                            day_date=day_date,
                            time_text=timefrag,
                            fee_text=fee_text,
                            reserve_required=reserve_required,
                            source_url=facility.dropin_page_url,
                            tz=tz
                        ))
                sib = sib.find_next_sibling()
    log.info("Facility page parsed %d entries for %s", len(items), facility.facility_name)
    return items
