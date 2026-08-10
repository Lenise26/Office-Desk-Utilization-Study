from __future__ import annotations


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_seeded_layouts_and_dashboard(client):
    layouts = client.get("/api/layouts").json()
    assert len(layouts) == 2

    dashboard = client.get("/api/dashboard", params={"layout_id": layouts[0]["id"]})
    assert dashboard.status_code == 200
    payload = dashboard.json()
    assert 0 <= payload["overall_utilization_rate"] <= 100
    assert payload["observations"] > 100
    assert payload["zone_utilization"]
    assert payload["heatmap"]


def test_compare_layouts(client):
    response = client.get(
        "/api/compare",
        params={"before_layout_id": 1, "after_layout_id": 2},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["before_layout_id"] == 1
    assert payload["after_layout_id"] == 2
    assert payload["zone_changes"]
    assert isinstance(payload["summary"], str)


def test_record_anonymous_observation(client):
    desks = client.get("/api/desks", params={"layout_id": 2}).json()
    response = client.post(
        "/api/observations",
        json={
            "desk_id": desks[0]["id"],
            "observed_at": "2026-08-10T10:30:00",
            "occupied": True,
            "approximate_duration_minutes": 45,
        },
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["message"].startswith("Anonymous")
    assert "employee" not in payload


def test_reject_duration_for_unoccupied_desk(client):
    desks = client.get("/api/desks", params={"layout_id": 2}).json()
    response = client.post(
        "/api/observations",
        json={
            "desk_id": desks[0]["id"],
            "observed_at": "2026-08-10T10:30:00",
            "occupied": False,
            "approximate_duration_minutes": 30,
        },
    )
    assert response.status_code == 422


def test_csv_export_contains_no_identity_columns(client):
    response = client.get("/api/export.csv", params={"layout_id": 1})
    assert response.status_code == 200
    header = response.text.splitlines()[0].lower()
    assert "employee" not in header
    assert "name" not in header
    assert "email" not in header
