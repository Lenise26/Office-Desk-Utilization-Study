from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS offices (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    city TEXT NOT NULL,
    state TEXT NOT NULL,
    country TEXT NOT NULL DEFAULT 'USA',
    timezone TEXT NOT NULL DEFAULT 'America/New_York'
);

CREATE TABLE IF NOT EXISTS layouts (
    id INTEGER PRIMARY KEY,
    office_id INTEGER NOT NULL REFERENCES offices(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    effective_from TEXT NOT NULL,
    effective_to TEXT,
    description TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS desks (
    id INTEGER PRIMARY KEY,
    layout_id INTEGER NOT NULL REFERENCES layouts(id) ON DELETE CASCADE,
    desk_code TEXT NOT NULL,
    zone TEXT NOT NULL,
    desk_type TEXT NOT NULL,
    nearby_facilities TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    UNIQUE(layout_id, desk_code)
);

CREATE TABLE IF NOT EXISTS observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    desk_id INTEGER NOT NULL REFERENCES desks(id) ON DELETE CASCADE,
    observed_at TEXT NOT NULL,
    occupied INTEGER NOT NULL CHECK (occupied IN (0, 1)),
    approximate_duration_minutes INTEGER,
    source TEXT NOT NULL DEFAULT 'observer',
    CHECK (
        approximate_duration_minutes IS NULL
        OR approximate_duration_minutes BETWEEN 0 AND 480
    )
);

CREATE INDEX IF NOT EXISTS idx_observations_desk_time
ON observations(desk_id, observed_at);

CREATE INDEX IF NOT EXISTS idx_desks_layout_zone
ON desks(layout_id, zone);
"""


def connect(database_path: Path | str) -> sqlite3.Connection:
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db_session(database_path: Path | str) -> Iterator[sqlite3.Connection]:
    conn = connect(database_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def initialize_database(database_path: Path | str) -> None:
    with db_session(database_path) as conn:
        conn.executescript(SCHEMA)
