from datetime import date
from zoneinfo import ZoneInfo
from app.parsers import parse_age_range, parse_time_range, parse_week_header

TZ = ZoneInfo("America/Toronto")

def test_parse_age_range():
    assert parse_age_range("19+") == (19, None)
    assert parse_age_range("13–18") == (13, 18)
    assert parse_age_range("13-18") == (13, 18)
    assert parse_age_range("All ages") == (None, None)
    assert parse_age_range("Adults (19 years and older)") == (19, None)

def test_parse_time_range():
    s, e = parse_time_range("07:30 PM - 09:30 PM", date(2025, 9, 1), TZ)
    assert s.hour == 19 and e.hour == 21
    s2, e2 = parse_time_range("11:00 PM - 01:00 AM", date(2025, 9, 1), TZ)
    assert e2.day == 2

def test_parse_week_header():
    from app.parsers import parse_week_header
    d = parse_week_header("For the week of 2025-09-01")
    assert d.isoformat() == "2025-09-01"
