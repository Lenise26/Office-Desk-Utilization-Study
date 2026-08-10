from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_env: str
    database_path: Path
    auto_seed: bool
    cors_origins: tuple[str, ...]


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def get_settings() -> Settings:
    database_path = Path(os.getenv("DATABASE_PATH", "data/office_desk_utilization.sqlite3"))
    origins = tuple(
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:8000").split(",")
        if origin.strip()
    )
    return Settings(
        app_name=os.getenv("APP_NAME", "Office Desk Utilization Study"),
        app_env=os.getenv("APP_ENV", "development"),
        database_path=database_path,
        auto_seed=_as_bool(os.getenv("AUTO_SEED"), default=True),
        cors_origins=origins,
    )
