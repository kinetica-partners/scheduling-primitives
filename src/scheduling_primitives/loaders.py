"""Data loading utilities for calendar definitions and fixtures."""

from __future__ import annotations

import json
from pathlib import Path

from scheduling_primitives.calendar import WorkingCalendar
from scheduling_primitives.schema import validate_exceptions, validate_rules


def load_calendar_json(path: str | Path) -> WorkingCalendar:
    """Load a WorkingCalendar from a JSON fixture file.

    The JSON file must have the cross-platform contract format:
    {
        "id": "...",
        "calendar": {
            "rules": { "0": [["08:00","17:00"]], ... },
            "exceptions": { ... }
        }
    }

    Raises ValueError if validation fails.
    """
    path = Path(path)
    with open(path) as f:
        data = json.load(f)

    cal_data = data.get("calendar", data)
    rules_raw = cal_data["rules"]
    exceptions = cal_data.get("exceptions", {})

    # Convert string keys to int
    rules = {int(k): v for k, v in rules_raw.items()}

    # Validate
    errors = validate_rules(rules)
    errors.extend(validate_exceptions(exceptions))
    if errors:
        raise ValueError(
            f"Validation errors in {path.name}:\n"
            + "\n".join(f"  - {e}" for e in errors)
        )

    pattern_id = data.get("id", path.stem)
    return WorkingCalendar(pattern_id, rules, exceptions)


def load_multi_resource_json(
    path: str | Path,
) -> dict[str, WorkingCalendar]:
    """Load multiple resource calendars from a JSON fixture file.

    The JSON must have the resource_variety format:
    {
        "resources": {
            "RES-1": { "rules": {...}, "exceptions": {...} },
            ...
        }
    }
    """
    path = Path(path)
    with open(path) as f:
        data = json.load(f)

    calendars: dict[str, WorkingCalendar] = {}
    for resource_id, res_data in data["resources"].items():
        rules = {int(k): v for k, v in res_data["rules"].items()}
        exceptions = res_data.get("exceptions", {})

        errors = validate_rules(rules)
        errors.extend(validate_exceptions(exceptions))
        if errors:
            raise ValueError(
                f"Validation errors for {resource_id} in {path.name}:\n"
                + "\n".join(f"  - {e}" for e in errors)
            )

        calendars[resource_id] = WorkingCalendar(resource_id, rules, exceptions)

    return calendars
