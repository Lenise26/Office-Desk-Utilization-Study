from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture()
def client(tmp_path: Path):
    settings = Settings(
        app_name="Office Desk Utilization Study Test",
        app_env="test",
        database_path=tmp_path / "test.sqlite3",
        auto_seed=True,
        cors_origins=("http://testserver",),
    )
    app = create_app(settings)
    with TestClient(app) as test_client:
        yield test_client
