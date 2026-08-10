from __future__ import annotations

import csv
import io
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.analytics import compare_layouts, dashboard_metrics
from app.config import Settings, get_settings
from app.db import db_session, initialize_database
from app.schemas import ObservationCreate
from app.seed import seed_database

STATIC_DIR = Path(__file__).resolve().parent / "static"


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or get_settings()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        initialize_database(resolved.database_path)
        if resolved.auto_seed:
            seed_database(resolved.database_path)
        yield

    app = FastAPI(
        title=resolved.app_name,
        version="1.0.0",
        description=(
            "Anonymous desk-utilization analytics for shared workplaces. "
            "The data model intentionally contains no employee identity fields."
        ),
        lifespan=lifespan,
    )
    app.state.settings = resolved
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved.cors_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/health")
    def health() -> dict:
        with db_session(resolved.database_path) as conn:
            conn.execute("SELECT 1").fetchone()
        return {"status": "ok", "service": resolved.app_name}

    @app.get("/api/offices")
    def offices() -> list[dict]:
        with db_session(resolved.database_path) as conn:
            rows = conn.execute(
                "SELECT id, name, city, state, country, timezone FROM offices ORDER BY name"
            ).fetchall()
        return [dict(row) for row in rows]

    @app.get("/api/layouts")
    def layouts(office_id: int | None = Query(default=None, gt=0)) -> list[dict]:
        sql = "SELECT id, office_id, name, effective_from, effective_to, description FROM layouts"
        params: tuple = ()
        if office_id:
            sql += " WHERE office_id = ?"
            params = (office_id,)
        sql += " ORDER BY effective_from"
        with db_session(resolved.database_path) as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    @app.get("/api/desks")
    def desks(layout_id: int = Query(gt=0)) -> list[dict]:
        with db_session(resolved.database_path) as conn:
            rows = conn.execute(
                """
                SELECT id, layout_id, desk_code, zone, desk_type, nearby_facilities
                FROM desks
                WHERE layout_id = ? AND active = 1
                ORDER BY zone, desk_code
                """,
                (layout_id,),
            ).fetchall()
        return [
            {
                **dict(row),
                "nearby_facilities": [item for item in row["nearby_facilities"].split("|") if item],
            }
            for row in rows
        ]

    @app.get("/api/dashboard")
    def dashboard(
        layout_id: int = Query(gt=0),
        period: str = Query(default="all", pattern="^(all|morning|midday|afternoon|late)$"),
    ) -> dict:
        with db_session(resolved.database_path) as conn:
            layout = conn.execute("SELECT id FROM layouts WHERE id = ?", (layout_id,)).fetchone()
            if not layout:
                raise HTTPException(status_code=404, detail="Layout not found")
            return dashboard_metrics(conn, layout_id, period)

    @app.get("/api/compare")
    def compare(
        before_layout_id: int = Query(gt=0),
        after_layout_id: int = Query(gt=0),
    ) -> dict:
        if before_layout_id == after_layout_id:
            raise HTTPException(status_code=400, detail="Choose two different layouts")
        with db_session(resolved.database_path) as conn:
            ids = {
                row["id"]
                for row in conn.execute(
                    "SELECT id FROM layouts WHERE id IN (?, ?)",
                    (before_layout_id, after_layout_id),
                ).fetchall()
            }
            if ids != {before_layout_id, after_layout_id}:
                raise HTTPException(status_code=404, detail="One or both layouts were not found")
            return compare_layouts(conn, before_layout_id, after_layout_id)

    @app.post("/api/observations", status_code=201)
    def create_observation(payload: ObservationCreate) -> dict:
        with db_session(resolved.database_path) as conn:
            desk = conn.execute(
                "SELECT id, desk_code, zone FROM desks WHERE id = ? AND active = 1",
                (payload.desk_id,),
            ).fetchone()
            if not desk:
                raise HTTPException(status_code=404, detail="Desk not found")
            cursor = conn.execute(
                """
                INSERT INTO observations(
                    desk_id, observed_at, occupied, approximate_duration_minutes, source
                ) VALUES (?, ?, ?, ?, 'observer')
                """,
                (
                    payload.desk_id,
                    payload.observed_at.isoformat(timespec="minutes"),
                    int(payload.occupied),
                    payload.approximate_duration_minutes,
                ),
            )
            observation_id = cursor.lastrowid
        return {
            "id": observation_id,
            "desk_id": payload.desk_id,
            "desk_code": desk["desk_code"],
            "zone": desk["zone"],
            "message": "Anonymous desk observation recorded.",
        }

    @app.get("/api/export.csv")
    def export_csv(layout_id: int = Query(gt=0)) -> StreamingResponse:
        with db_session(resolved.database_path) as conn:
            rows = conn.execute(
                """
                SELECT d.desk_code, d.zone, d.desk_type, d.nearby_facilities,
                       o.observed_at, o.occupied, o.approximate_duration_minutes, o.source
                FROM observations o
                JOIN desks d ON d.id = o.desk_id
                WHERE d.layout_id = ?
                ORDER BY o.observed_at, d.zone, d.desk_code
                """,
                (layout_id,),
            ).fetchall()
        if not rows:
            raise HTTPException(status_code=404, detail="No observations found for layout")
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            [
                "desk_code",
                "zone",
                "desk_type",
                "nearby_facilities",
                "observed_at",
                "occupied",
                "approximate_duration_minutes",
                "source",
            ]
        )
        for row in rows:
            writer.writerow(list(row))
        filename = f"desk-utilization-layout-{layout_id}.csv"
        return StreamingResponse(
            iter([buffer.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @app.get("/api/privacy")
    def privacy() -> dict:
        return {
            "identity_collection": False,
            "employee_fields": [],
            "principle": "Observe workspace use, not people.",
            "recommended_retention": "Set a retention period appropriate to your organization and local policy.",
        }

    return app


app = create_app()
