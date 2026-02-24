"""Shared test fixtures and data loading for scheduling-primitives.

All test data lives in data/fixtures/ as JSON files.  This module loads
that data and exposes helper functions + pytest fixtures for the tests.

Reference week: Mon 2025-01-06 through Sun 2025-01-12.
Epoch: Mon 2025-01-06 00:00 (minute 0).
"""

from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
FIXTURES_DIR = Path(__file__).resolve().parent.parent / "data" / "fixtures"
SCENARIOS_DIR = FIXTURES_DIR / "scenarios"


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------
def _load_json(path: Path):
    with open(path) as f:
        return json.load(f)


_reference = _load_json(FIXTURES_DIR / "reference.json")
_calendars = _load_json(FIXTURES_DIR / "calendars.json")


# ---------------------------------------------------------------------------
# Reference constants derived from reference.json
# ---------------------------------------------------------------------------
EPOCH = datetime.fromisoformat(_reference["epoch"])
MINUTES_PER_DAY = _reference["minutes_per_day"]
WORK_DAY_MINUTES = _reference["work_day_minutes"]

# Day lookup:  DAYS["mon"] → {"date": date(...), "datetime": datetime(...), ...}
DAYS: dict[str, dict] = {}
for _d in _reference["days"]:
    DAYS[_d["name"]] = {
        "date": date.fromisoformat(_d["date"]),
        "datetime": datetime.fromisoformat(_d["date"] + "T00:00:00"),
        "offset": _d["day_offset"],
        "weekday": _d["weekday"],
    }

# Time lookup:  TIMES["08:00"] → 480
TIMES: dict[str, int] = {t["label"]: t["minutes"] for t in _reference["times"]}


# ---------------------------------------------------------------------------
# Convenience helpers (importable by test modules)
# ---------------------------------------------------------------------------
def offset(day: str, time_label: str) -> int:
    """Absolute offset in minutes from epoch:  day_offset + time_minutes.

    >>> offset("mon", "08:00")
    480
    >>> offset("tue", "08:00")
    1920
    """
    return DAYS[day]["offset"] + TIMES[time_label]


def dt(day: str, time_label: str) -> datetime:
    """Datetime from day name and time label.

    >>> dt("mon", "09:00")
    datetime(2025, 1, 6, 9, 0)
    """
    return EPOCH + timedelta(minutes=offset(day, time_label))


def day_date(day: str) -> date:
    """Date object for a named day."""
    return DAYS[day]["date"]


def day_dt(day: str) -> datetime:
    """Midnight datetime for a named day."""
    return DAYS[day]["datetime"]


def parse_time_pair(pair: list[str]) -> tuple[time, time]:
    """Convert ["08:00", "17:00"] to (time(8,0), time(17,0))."""
    return (
        time.fromisoformat(pair[0]),
        time.fromisoformat(pair[1]),
    )


# ---------------------------------------------------------------------------
# Calendar factory
# ---------------------------------------------------------------------------
def make_calendar(name: str):
    """Build a WorkingCalendar from calendars.json by name."""
    from scheduling_primitives.calendar import WorkingCalendar

    config = _calendars[name]
    rules = {int(k): v for k, v in config["rules"].items()}
    exceptions = config.get("exceptions", {})
    return WorkingCalendar(name, rules, exceptions)


# ---------------------------------------------------------------------------
# Bitmap factory
# ---------------------------------------------------------------------------
def make_bitmap(calendar_name: str = "standard",
                horizon_start: str | None = None,
                horizon_end: str | None = None,
                resolution: str = "minute"):
    """Build an OccupancyBitmap from a named calendar.

    Defaults to the full canonical week (Mon-Sun) at MINUTE resolution.
    Pass resolution="hour" for hour-grain bitmaps.
    """
    from scheduling_primitives.occupancy import OccupancyBitmap
    from scheduling_primitives.resolution import HOUR, MINUTE

    res = HOUR if resolution == "hour" else MINUTE
    cal = make_calendar(calendar_name)
    h_start = datetime.fromisoformat(horizon_start) if horizon_start else day_dt("mon")
    h_end = datetime.fromisoformat(horizon_end) if horizon_end else day_dt("next_mon")
    return OccupancyBitmap.from_calendar(cal, h_start, h_end, EPOCH, res)


# ---------------------------------------------------------------------------
# Scenario loader
# ---------------------------------------------------------------------------
def load_scenarios(name: str):
    """Load a scenario file from data/fixtures/scenarios/{name}.json."""
    return _load_json(SCENARIOS_DIR / f"{name}.json")


# ---------------------------------------------------------------------------
# pytest fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def epoch() -> datetime:
    return EPOCH


@pytest.fixture
def standard_calendar():
    return make_calendar("standard")


@pytest.fixture
def holiday_calendar():
    return make_calendar("holiday")


@pytest.fixture
def simple_calendar():
    return make_calendar("simple")


@pytest.fixture
def standard_bitmap():
    """One-week bitmap from standard calendar (no exceptions). MINUTE resolution."""
    return make_bitmap("standard")


@pytest.fixture
def holiday_bitmap():
    """One-week bitmap with Tuesday holiday. MINUTE resolution."""
    return make_bitmap("holiday")


@pytest.fixture
def short_bitmap():
    """Two-day bitmap (Mon-Tue only) for auto-extension tests. MINUTE resolution."""
    return make_bitmap("standard",
                       horizon_end=DAYS["wed"]["datetime"].isoformat())
