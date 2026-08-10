from __future__ import annotations

import sqlite3
from collections import defaultdict
from datetime import datetime
from statistics import mean

PERIODS = {
    "morning": (8, 11),
    "midday": (11, 14),
    "afternoon": (14, 17),
    "late": (17, 19),
}


def _hour(iso_value: str) -> int:
    return datetime.fromisoformat(iso_value).hour


def _period_for_hour(hour: int) -> str:
    for name, (start, end) in PERIODS.items():
        if start <= hour < end:
            return name
    return "other"


def _rate(occupied: int, total: int) -> float:
    return round((occupied / total * 100.0) if total else 0.0, 1)


def fetch_observations(conn: sqlite3.Connection, layout_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT
            o.id,
            o.observed_at,
            o.occupied,
            o.approximate_duration_minutes,
            d.id AS desk_id,
            d.desk_code,
            d.zone,
            d.desk_type,
            d.nearby_facilities
        FROM observations o
        JOIN desks d ON d.id = o.desk_id
        WHERE d.layout_id = ? AND d.active = 1
        ORDER BY o.observed_at, d.zone, d.desk_code
        """,
        (layout_id,),
    ).fetchall()


def dashboard_metrics(
    conn: sqlite3.Connection,
    layout_id: int,
    period: str = "all",
) -> dict:
    rows = fetch_observations(conn, layout_id)
    if period != "all":
        start, end = PERIODS[period]
        rows = [row for row in rows if start <= _hour(row["observed_at"]) < end]

    if not rows:
        return {
            "layout_id": layout_id,
            "overall_utilization_rate": 0.0,
            "observations": 0,
            "occupied_observations": 0,
            "average_occupied_duration_minutes": 0.0,
            "zone_utilization": [],
            "time_period_utilization": [],
            "heatmap": [],
            "peak_periods": [],
            "unused_areas": [],
            "desk_type_utilization": [],
        }

    occupied = sum(int(row["occupied"]) for row in rows)
    durations = [
        row["approximate_duration_minutes"]
        for row in rows
        if row["occupied"] and row["approximate_duration_minutes"] is not None
    ]

    zone_counts: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    period_counts: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    heat_counts: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0])
    desk_type_counts: dict[str, list[int]] = defaultdict(lambda: [0, 0])

    for row in rows:
        occ = int(row["occupied"])
        zone_counts[row["zone"]][0] += occ
        zone_counts[row["zone"]][1] += 1
        bucket = _period_for_hour(_hour(row["observed_at"]))
        period_counts[bucket][0] += occ
        period_counts[bucket][1] += 1
        heat_counts[(row["zone"], bucket)][0] += occ
        heat_counts[(row["zone"], bucket)][1] += 1
        desk_type_counts[row["desk_type"]][0] += occ
        desk_type_counts[row["desk_type"]][1] += 1

    zone_utilization = [
        {
            "zone": zone,
            "utilization_rate": _rate(values[0], values[1]),
            "occupied": values[0],
            "observations": values[1],
        }
        for zone, values in sorted(zone_counts.items())
    ]

    period_order = ["morning", "midday", "afternoon", "late", "other"]
    time_period_utilization = [
        {
            "period": bucket,
            "utilization_rate": _rate(period_counts[bucket][0], period_counts[bucket][1]),
            "observations": period_counts[bucket][1],
        }
        for bucket in period_order
        if bucket in period_counts
    ]

    heatmap = []
    for zone in sorted(zone_counts):
        for bucket in ["morning", "midday", "afternoon", "late"]:
            values = heat_counts.get((zone, bucket), [0, 0])
            heatmap.append(
                {
                    "zone": zone,
                    "period": bucket,
                    "utilization_rate": _rate(values[0], values[1]),
                    "observations": values[1],
                }
            )

    peak_periods = sorted(
        time_period_utilization,
        key=lambda item: item["utilization_rate"],
        reverse=True,
    )[:3]

    unused_areas = [
        item
        for item in sorted(zone_utilization, key=lambda item: item["utilization_rate"])
        if item["utilization_rate"] < 35.0
    ]

    desk_type_utilization = [
        {
            "desk_type": desk_type,
            "utilization_rate": _rate(values[0], values[1]),
            "observations": values[1],
        }
        for desk_type, values in sorted(desk_type_counts.items())
    ]

    return {
        "layout_id": layout_id,
        "overall_utilization_rate": _rate(occupied, len(rows)),
        "observations": len(rows),
        "occupied_observations": occupied,
        "average_occupied_duration_minutes": round(mean(durations), 1) if durations else 0.0,
        "zone_utilization": zone_utilization,
        "time_period_utilization": time_period_utilization,
        "heatmap": heatmap,
        "peak_periods": peak_periods,
        "unused_areas": unused_areas,
        "desk_type_utilization": desk_type_utilization,
    }


def compare_layouts(conn: sqlite3.Connection, before_layout_id: int, after_layout_id: int) -> dict:
    before = dashboard_metrics(conn, before_layout_id)
    after = dashboard_metrics(conn, after_layout_id)

    before_by_zone = {item["zone"]: item["utilization_rate"] for item in before["zone_utilization"]}
    after_by_zone = {item["zone"]: item["utilization_rate"] for item in after["zone_utilization"]}
    zones = sorted(set(before_by_zone) | set(after_by_zone))

    zone_changes = [
        {
            "zone": zone,
            "before_rate": before_by_zone.get(zone, 0.0),
            "after_rate": after_by_zone.get(zone, 0.0),
            "change_points": round(after_by_zone.get(zone, 0.0) - before_by_zone.get(zone, 0.0), 1),
        }
        for zone in zones
    ]

    return {
        "before_layout_id": before_layout_id,
        "after_layout_id": after_layout_id,
        "before_overall_rate": before["overall_utilization_rate"],
        "after_overall_rate": after["overall_utilization_rate"],
        "overall_change_points": round(
            after["overall_utilization_rate"] - before["overall_utilization_rate"], 1
        ),
        "zone_changes": zone_changes,
        "summary": _comparison_summary(before, after),
    }


def _comparison_summary(before: dict, after: dict) -> str:
    delta = round(after["overall_utilization_rate"] - before["overall_utilization_rate"], 1)
    if delta >= 5:
        return f"Utilization improved by {delta} percentage points after the layout change."
    if delta <= -5:
        return f"Utilization decreased by {abs(delta)} percentage points after the layout change."
    return f"Overall utilization was broadly stable, changing by {delta} percentage points."
