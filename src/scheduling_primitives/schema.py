"""Input validation for calendar rules and exceptions."""

from __future__ import annotations

from datetime import date, time


def validate_rules(rules: dict[int, list[list[str]]]) -> list[str]:
    """Validate weekly rules. Returns list of error messages (empty = valid).

    Checks:
    - Weekday keys are 0-6
    - Time strings parse as valid times
    - Periods within a day do not overlap (unless overnight)
    """
    errors: list[str] = []

    for weekday, periods in rules.items():
        if not isinstance(weekday, int) or weekday < 0 or weekday > 6:
            errors.append(f"Invalid weekday key: {weekday} (must be 0-6)")
            continue

        parsed_periods: list[tuple[time, time]] = []
        for i, period in enumerate(periods):
            if not isinstance(period, list) or len(period) != 2:
                errors.append(
                    f"Weekday {weekday}, period {i}: "
                    f"expected [start, end], got {period}"
                )
                continue

            try:
                start = time.fromisoformat(period[0])
                end = time.fromisoformat(period[1])
            except (ValueError, TypeError) as e:
                errors.append(
                    f"Weekday {weekday}, period {i}: invalid time - {e}"
                )
                continue

            parsed_periods.append((start, end))

        # Check for overlapping non-overnight periods
        day_periods = [
            (s, e) for s, e in parsed_periods if e > s  # skip overnight
        ]
        day_periods.sort()
        for j in range(1, len(day_periods)):
            prev_end = day_periods[j - 1][1]
            curr_start = day_periods[j][0]
            if curr_start < prev_end:
                errors.append(
                    f"Weekday {weekday}: overlapping periods "
                    f"{day_periods[j-1]} and {day_periods[j]}"
                )

    return errors


def validate_exceptions(
    exceptions: dict[str, list[dict]],
) -> list[str]:
    """Validate exception entries. Returns list of error messages.

    Checks:
    - Date strings parse as valid dates
    - Each entry has is_working boolean
    - Working entries have valid start/end times
    """
    errors: list[str] = []

    for date_str, entries in exceptions.items():
        try:
            date.fromisoformat(date_str)
        except (ValueError, TypeError):
            errors.append(f"Invalid date: {date_str}")
            continue

        if not isinstance(entries, list):
            errors.append(f"Date {date_str}: entries must be a list")
            continue

        for i, entry in enumerate(entries):
            if "is_working" not in entry:
                errors.append(
                    f"Date {date_str}, entry {i}: missing 'is_working'"
                )
                continue

            if not isinstance(entry["is_working"], bool):
                errors.append(
                    f"Date {date_str}, entry {i}: "
                    f"'is_working' must be boolean"
                )

            if entry["is_working"]:
                for field in ("start", "end"):
                    if field in entry:
                        try:
                            time.fromisoformat(entry[field])
                        except (ValueError, TypeError):
                            errors.append(
                                f"Date {date_str}, entry {i}: "
                                f"invalid {field} time '{entry[field]}'"
                            )

    return errors
