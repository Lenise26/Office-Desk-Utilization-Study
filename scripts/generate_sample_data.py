"""Generate deterministic synthetic U.S.-only sample data for the demo repository."""
from __future__ import annotations

import csv
import random
from datetime import date, datetime, time, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "sample_data"
RNG = random.Random(20260810)

OFFICE = {
    "id": 1,
    "name": "Northstar Creative Services LLC",
    "city": "Columbus",
    "state": "Ohio",
    "country": "USA",
    "timezone": "America/New_York",
}

LAYOUTS = [
    {
        "id": 1,
        "office_id": 1,
        "name": "Baseline Layout — Q1 2026",
        "effective_from": "2026-01-05",
        "effective_to": "2026-03-31",
        "description": "Original shared-office plan with a central bench, individual window desks, a quiet corner, client touchdown desks, and a small team commons.",
    },
    {
        "id": 2,
        "office_id": 1,
        "name": "Collaboration Refresh — Q2 2026",
        "effective_from": "2026-04-06",
        "effective_to": "",
        "description": "Furniture refresh with more sit-stand choices, additional team-commons seats, improved quiet-corner positioning, and a simplified client touchdown zone.",
    },
]

ZONE_CONFIGS = {
    1: [
        ("Window Row", 6, ["standard", "standard", "standard", "sit-stand", "standard", "sit-stand"], "Meeting Rooms|Printer", 0.68),
        ("Central Bench", 6, ["standard"] * 6, "Kitchen|Printer|Restrooms", 0.52),
        ("Quiet Corner", 4, ["sit-stand", "standard", "sit-stand", "standard"], "Wellness Room|Restrooms", 0.24),
        ("Client Hub", 4, ["touchdown"] * 4, "Reception|Meeting Rooms|Coffee Station", 0.32),
        ("Team Commons", 4, ["collaboration"] * 4, "Kitchen|Meeting Rooms|Whiteboards", 0.55),
    ],
    2: [
        ("Window Row", 6, ["sit-stand", "sit-stand", "standard", "sit-stand", "standard", "sit-stand"], "Meeting Rooms|Printer", 0.73),
        ("Central Bench", 5, ["standard", "standard", "sit-stand", "standard", "accessible"], "Kitchen|Printer|Restrooms", 0.57),
        ("Quiet Corner", 5, ["sit-stand", "sit-stand", "standard", "sit-stand", "accessible"], "Wellness Room|Restrooms|Lockers", 0.48),
        ("Client Hub", 4, ["touchdown"] * 4, "Reception|Meeting Rooms|Coffee Station", 0.44),
        ("Team Commons", 6, ["collaboration", "collaboration", "touchdown", "collaboration", "touchdown", "collaboration"], "Kitchen|Meeting Rooms|Whiteboards", 0.69),
    ],
}

TIME_FACTORS = {
    8: 0.68,
    9: 1.03,
    10: 1.14,
    11: 1.08,
    12: 0.78,
    13: 0.95,
    14: 1.10,
    15: 1.06,
    16: 0.86,
    17: 0.55,
}

DESK_TYPE_FACTORS = {
    "standard": 0.98,
    "sit-stand": 1.09,
    "touchdown": 0.88,
    "collaboration": 1.03,
    "accessible": 0.84,
}


def business_days(start: date, count: int) -> list[date]:
    days = []
    current = start
    while len(days) < count:
        if current.weekday() < 5:
            days.append(current)
        current += timedelta(days=1)
    return days


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def generate_desks() -> list[dict]:
    rows = []
    desk_id = 1
    for layout_id, configs in ZONE_CONFIGS.items():
        for zone_index, (zone, count, desk_types, facilities, _) in enumerate(configs, start=1):
            for seat in range(1, count + 1):
                prefix = ["WR", "CB", "QC", "CH", "TC"][zone_index - 1]
                rows.append(
                    {
                        "id": desk_id,
                        "layout_id": layout_id,
                        "desk_code": f"{prefix}-{seat:02d}",
                        "zone": zone,
                        "desk_type": desk_types[seat - 1],
                        "nearby_facilities": facilities,
                        "active": 1,
                    }
                )
                desk_id += 1
    return rows


def duration_for(hour: int, desk_type: str) -> int:
    if desk_type == "touchdown":
        options = [15, 30, 30, 45, 60, 60, 90]
    elif desk_type == "collaboration":
        options = [30, 45, 60, 60, 90, 120]
    else:
        options = [30, 45, 60, 60, 90, 120, 120, 180]
    if hour >= 16:
        options = [15, 30, 30, 45, 60, 90]
    return RNG.choice(options)


def generate_observations(desks: list[dict]) -> list[dict]:
    starts = {1: date(2026, 2, 2), 2: date(2026, 5, 4)}
    days_by_layout = {layout: business_days(start, 15) for layout, start in starts.items()}
    base_by_zone = {
        layout_id: {zone: base for zone, _, _, _, base in configs}
        for layout_id, configs in ZONE_CONFIGS.items()
    }
    rows = []
    for desk in desks:
        layout_id = int(desk["layout_id"])
        base = base_by_zone[layout_id][desk["zone"]]
        for day_index, day in enumerate(days_by_layout[layout_id]):
            weekday_factor = {0: 0.93, 1: 1.07, 2: 1.10, 3: 1.05, 4: 0.82}[day.weekday()]
            week_factor = 0.98 + (day_index // 5) * 0.025
            for hour in range(8, 18):
                observed_at = datetime.combine(day, time(hour, 30))
                probability = base * TIME_FACTORS[hour] * DESK_TYPE_FACTORS[desk["desk_type"]] * weekday_factor * week_factor
                # Small stable seat-to-seat variation avoids unrealistically uniform zones.
                seat_variation = 0.94 + ((int(desk["id"]) * 17) % 11) / 100
                probability = min(0.96, max(0.04, probability * seat_variation))
                occupied = RNG.random() < probability
                duration = duration_for(hour, desk["desk_type"]) if occupied else ""
                rows.append(
                    {
                        "desk_id": desk["id"],
                        "observed_at": observed_at.isoformat(timespec="minutes"),
                        "occupied": 1 if occupied else 0,
                        "approximate_duration_minutes": duration,
                        "source": "sample",
                    }
                )
    return rows


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    desks = generate_desks()
    observations = generate_observations(desks)
    write_csv(OUT / "offices.csv", list(OFFICE.keys()), [OFFICE])
    write_csv(OUT / "layouts.csv", list(LAYOUTS[0].keys()), LAYOUTS)
    write_csv(
        OUT / "desks.csv",
        ["id", "layout_id", "desk_code", "zone", "desk_type", "nearby_facilities", "active"],
        desks,
    )
    write_csv(
        OUT / "observations.csv",
        ["desk_id", "observed_at", "occupied", "approximate_duration_minutes", "source"],
        observations,
    )
    print(f"Generated {len(desks)} desks and {len(observations)} observations in {OUT}")


if __name__ == "__main__":
    main()
