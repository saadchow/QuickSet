# Toronto Volleyball Drop-ins (Weekly Aggregator)

Lightweight app that aggregates **City of Toronto** volleyball drop-in schedules and lets users pick a **weekday** to see all (tracked) community centres hosting volleyball on that day.

## Highlights
- **Hybrid collector**
  1. Prefer City's server-rendered **Active Communities "Activity Search"**.
  2. Fill gaps from facility **"Drop-in Programs"** pages (Playwright).
- **SQLite** normalization, **FastAPI** REST, and a tiny **HTML UI** (Jinja2)
- Nightly refresh at **02:30 America/Toronto** + `POST /refresh`
- Robust parsing for ages (`19+`, `13–18`), headers ("For the week of YYYY-MM-DD"), time ranges (`07:30 PM - 09:30 PM`).
- Idempotent inserts via SQLite `INSERT OR IGNORE` on unique key `(facility_id, start_datetime, program_name)`.

## Quickstart (local)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium

# first refresh to seed DB
python -m app.refresh

# run web app
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/ — choose a day to see centres & times.

## Endpoints
- UI: `GET /` (day dropdown UI)
- API: `GET /dropins?day=Tue&after=18:00&district=South&age=19+`
- `POST /refresh` — run collectors now
- `GET /healthz`
- (optional) `GET /ics?id=<facility_id>`

## Configure
Edit `settings.toml` or use env vars:
- `APP__DB_URL` (e.g., `sqlite:///./data.sqlite3`)
- `APP__TORONTO_TZ` (default `America/Toronto`)
- `PATHS__FACILITIES_FILE` (default `./facilities.json`)

**Important:** Fill `facilities.json` with a small, explicit list of facilities & exact URLs you want to track.

## Nightly Refresh (cron example)
```
# 02:30 America/Toronto daily
30 2 * * * cd /app && /venv/bin/python -m app.refresh >> cron.log 2>&1
```

## Docker
```bash
docker build -t toronto-dropins .
docker run -p 8000:8000 -v $(pwd)/data:/app/data -e APP__DB_URL=sqlite:////app/data/data.sqlite3 toronto-dropins
```

## Render Deploy (suggested)
- Create a Web Service from this repo (Docker).
- Add a **Disk** (mount `/app/data`) and set `APP__DB_URL=sqlite:////app/data/data.sqlite3`.
- Add a **Cron Job**: `30 2 * * *` → `python -m app.refresh` (Toronto time if available).

