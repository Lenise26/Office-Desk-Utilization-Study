# Office Desk Utilization Study

A production-style analytics application for small organizations that want to understand how shared desks and workspace zones are actually used **without tracking employee identities**.

The included demo uses a fictional small business in **Columbus, Ohio, USA** and compares a baseline workspace with a later furniture-layout refresh. All sample data is synthetic and anonymous.

## What it does

- Records anonymous occupied/unoccupied desk observations.
- Captures approximate occupied duration, desk type, nearby facilities, and observation time.
- Calculates utilization rates by zone, desk type, and time period.
- Shows a zone-by-time heatmap and peak-use periods.
- Flags underused areas for follow-up.
- Compares before-versus-after workspace layouts.
- Exports observation data to CSV for additional analysis.
- Provides a responsive manager dashboard suitable for desktop, tablet, and mobile.
- Includes automated API and analytics tests.

## Privacy-first design

There are intentionally **no employee name, email, badge, device, or identity fields** in the data model. The project is intended to study workspace use rather than individual behavior.

## Quick start

### Local Python

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

Open `http://localhost:8000`.

The application creates `data/office_desk_utilization.sqlite3` and loads the included synthetic sample data on first run.

### Docker

```bash
docker compose up --build
```

Then open `http://localhost:8000`.

## Tests

```bash
pytest
```

Coverage check:

```bash
pytest --cov=app --cov-report=term-missing
```

## API highlights

- `GET /health`
- `GET /api/offices`
- `GET /api/layouts`
- `GET /api/desks?layout_id=2`
- `GET /api/dashboard?layout_id=2&period=all`
- `GET /api/compare?before_layout_id=1&after_layout_id=2`
- `POST /api/observations`
- `GET /api/export.csv?layout_id=2`
- `GET /api/privacy`
- Interactive API documentation: `/docs`

Example anonymous observation:

```json
{
  "desk_id": 31,
  "observed_at": "2026-08-10T10:30:00",
  "occupied": true,
  "approximate_duration_minutes": 45
}
```

## Sample-data scenario

**Northstar Creative Services LLC** is a fictional 28-person professional-services company in Columbus, Ohio. The demo compares:

1. **Baseline Layout — Q1 2026**: more individual standard desks and a lightly used quiet corner.
2. **Collaboration Refresh — Q2 2026**: more sit-stand/touchdown choices, a revised Client Hub, and better use of collaboration space.

The observations are generated from deterministic synthetic patterns so the dashboard demonstrates realistic peaks, low-use zones, and measurable before/after changes without representing real people.

## Repository structure

```text
app/                 FastAPI app, SQLite access, analytics, seed loader
app/static/          Responsive dashboard frontend
sample_data/         Fictional U.S. office, layouts, desks, observations
tests/               API and analytics tests
 docs/                Architecture notes
.github/workflows/   Continuous integration
```

## GitHub repository description

> Privacy-first desk and workspace utilization analytics for small businesses, with anonymous observations, responsive heatmaps, peak-use insights, underused-area detection, and before/after furniture-layout comparisons.

Suggested topics: `workspace-analytics`, `desk-utilization`, `fastapi`, `sqlite`, `small-business`, `privacy-by-design`, `facilities-management`, `responsive-dashboard`

## Production notes

This repository is structured for a small-business deployment. Before exposing it publicly, add organization authentication/SSO at the proxy layer, HTTPS, monitored backups, and a written data-retention policy. For larger multi-office deployments or higher write concurrency, migrate storage from SQLite to PostgreSQL while keeping the API contract.

## Data ownership

All application code and sample business data in this repository were created specifically for this project. The sample organization and observations are fictional.
