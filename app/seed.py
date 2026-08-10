from __future__ import annotations

import csv
from pathlib import Path

from app.config import get_settings
from app.db import db_session, initialize_database

ROOT = Path(__file__).resolve().parent.parent
SAMPLE_DATA = ROOT / "sample_data"


def seed_database(database_path: Path | str) -> None:
    initialize_database(database_path)
    with db_session(database_path) as conn:
        existing = conn.execute("SELECT COUNT(*) AS count FROM observations").fetchone()["count"]
        if existing:
            return

        with (SAMPLE_DATA / "offices.csv").open(newline="", encoding="utf-8") as handle:
            conn.executemany(
                "INSERT INTO offices(id, name, city, state, country, timezone) VALUES(:id,:name,:city,:state,:country,:timezone)",
                csv.DictReader(handle),
            )

        with (SAMPLE_DATA / "layouts.csv").open(newline="", encoding="utf-8") as handle:
            conn.executemany(
                "INSERT INTO layouts(id, office_id, name, effective_from, effective_to, description) VALUES(:id,:office_id,:name,:effective_from,:effective_to,:description)",
                csv.DictReader(handle),
            )

        with (SAMPLE_DATA / "desks.csv").open(newline="", encoding="utf-8") as handle:
            conn.executemany(
                "INSERT INTO desks(id, layout_id, desk_code, zone, desk_type, nearby_facilities, active) VALUES(:id,:layout_id,:desk_code,:zone,:desk_type,:nearby_facilities,:active)",
                csv.DictReader(handle),
            )

        with (SAMPLE_DATA / "observations.csv").open(newline="", encoding="utf-8") as handle:
            rows = []
            for row in csv.DictReader(handle):
                rows.append(
                    {
                        "desk_id": int(row["desk_id"]),
                        "observed_at": row["observed_at"],
                        "occupied": int(row["occupied"]),
                        "approximate_duration_minutes": (
                            int(row["approximate_duration_minutes"])
                            if row["approximate_duration_minutes"]
                            else None
                        ),
                        "source": row.get("source") or "sample",
                    }
                )
            conn.executemany(
                """
                INSERT INTO observations(
                    desk_id, observed_at, occupied, approximate_duration_minutes, source
                ) VALUES(:desk_id,:observed_at,:occupied,:approximate_duration_minutes,:source)
                """,
                rows,
            )


if __name__ == "__main__":
    settings = get_settings()
    seed_database(settings.database_path)
    print(f"Seeded {settings.database_path}")
