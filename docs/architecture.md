# Architecture

The application is intentionally compact for small-business deployments.

- **FastAPI** provides the HTTP API and serves the static frontend.
- **SQLite** stores offices, furniture layouts, desks, and anonymous observations.
- **Vanilla HTML/CSS/JavaScript** keeps the dashboard responsive without a frontend build toolchain.
- **Analytics functions** aggregate utilization by zone, time period, desk type, and layout.
- **Sample CSV files** provide deterministic demo data and can be replaced with organization-specific imports later.

## Privacy boundary

The system models **desks and observations, not employees**. An observation records only the desk, timestamp, occupied status, approximate duration, and source. Desk type and nearby facilities are maintained as desk metadata.

## Production hardening

For an internet-facing production deployment, place the service behind an identity-aware reverse proxy, add centralized logs and backups, and move to PostgreSQL if concurrent writes or larger multi-office datasets outgrow SQLite.
