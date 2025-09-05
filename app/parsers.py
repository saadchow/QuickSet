from __future__ import annotations
import re
from datetime import datetime, date, timedelta
from dateutil import parser as dateparser
from typing import Optional, Tuple
from zoneinfo import ZoneInfo

WEEKDAY_MAP = {
    0: "Mon",
    1: "Tue",
    2: "Wed",
    3: "Thu",
    4: "Fri",
    5: "Sat",
    6: "Sun",
}

def parse_age_range(text: str) -> Tuple[Optional[int], Optional[int]]:
    s = (text or "").strip().lower()
    if not s:
        return (None, None)
    if "all ages" in s:
        return (None, None)
    m_range = re.search(r"(\d+)\s*[–-]\s*(\d+)", s)
    if m_range:
        return (int(m_range.group(1)), int(m_range.group(2)))
    m_plus = re.search(r"(\d+)\s*\+", s)
    if m_plus:
        return (int(m_plus.group(1)), None)
    m_adult = re.search(r"(\d+)\s*(?:years?)?\s*(?:\+|and\s*older)", s)
    if m_adult:
        return (int(m_adult.group(1)), None)
    return (None, None)

def parse_time_range(text: str, ref_date: date, tz: ZoneInfo):
    s = (text or "").strip()
    parts = re.split(r"\s*(?:-|to|–|—)\s*", s, maxsplit=1, flags=re.IGNORECASE)
    if len(parts) != 2:
        dt = dateparser.parse(s, default=datetime(ref_date.year, ref_date.month, ref_date.day, 0, 0))
        start = dt.replace(tzinfo=tz)
        end = start + timedelta(hours=1)
        return start, end

    left, right = parts
    dleft = dateparser.parse(left, default=datetime(ref_date.year, ref_date.month, ref_date.day, 0, 0))
    dright = dateparser.parse(right, default=datetime(ref_date.year, ref_date.month, ref_date.day, 0, 0))

    start = dleft.replace(tzinfo=tz)
    end = dright.replace(tzinfo=tz)
    if end <= start:
        end = end + timedelta(days=1)
    return start, end

def parse_week_header(text: str) -> Optional[date]:
    if not text:
        return None
    m = re.search(r"week\s+of\s+(\d{4}-\d{2}-\d{2})", text, re.IGNORECASE)
    if m:
        d = dateparser.parse(m.group(1)).date()
        while d.weekday() != 0:
            d = d - timedelta(days=1)
        return d
    return None

def iso_weekday_name(d: date) -> str:
    return WEEKDAY_MAP[d.weekday()]
