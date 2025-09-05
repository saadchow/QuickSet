from __future__ import annotations
from typing import List, Dict, Any
from icalendar import Calendar, Event

def rows_to_ics(rows: List[Dict[str, Any]]) -> bytes:
    cal = Calendar()
    cal.add("prodid", "-//Toronto Drop-ins//EN")
    cal.add("version", "2.0")
    for r in rows:
        ev = Event()
        ev.add("summary", f"{r['program_name']} @ {r['facility_name']}")
        ev.add("dtstart", r["start_datetime"])
        ev.add("dtend", r["end_datetime"])
        ev.add("location", f"{r['facility_name']}, {r.get('address','')}")
        ev.add("description", f"Age: {r.get('age_min','?')}-{r.get('age_max','?')} | Fee: {r.get('fee_cad')} | Source: {r.get('source_url')}")
        cal.add_component(ev)
    return cal.to_ical()
