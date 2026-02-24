"""Layer 1: WorkingCalendar — datetime-based, horizon-free calendar."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Iterator


def _parse_time(s: str) -> time:
    """Parse 'HH:MM' string to time object."""
    parts = s.split(":")
    return time(int(parts[0]), int(parts[1]))


def _is_overnight(start: time, end: time) -> bool:
    """True if end <= start, meaning the period crosses midnight.

    Special case: time(0, 0) as end means midnight (end of day),
    which is overnight when start > 00:00.
    """
    if end == time(0, 0) and start != time(0, 0):
        return True
    return end < start


class WorkingCalendar:
    """Horizon-free calendar. Answers time queries by lazy day-by-day walk.

    Rules define recurring weekly patterns. Exceptions override specific dates.
    All datetimes are naive (facility local time).
    """

    def __init__(
        self,
        pattern_id: str,
        rules: dict[int, list[tuple[str, str]]],
        exceptions: dict[str, list[dict]],
    ) -> None:
        self.pattern_id = pattern_id

        # Parse rules: weekday int -> sorted list of (start_time, end_time)
        self._rules: dict[int, list[tuple[time, time]]] = {}
        for day_key, periods in rules.items():
            day = int(day_key)
            parsed = []
            for start_str, end_str in periods:
                parsed.append((_parse_time(start_str), _parse_time(end_str)))
            # Sort by start time
            parsed.sort(key=lambda p: p[0])
            self._rules[day] = parsed

        # Parse exceptions: ISO date string -> list of exception entries
        self._exceptions: dict[str, list[dict]] = {}
        for date_str, entries in exceptions.items():
            self._exceptions[date_str] = entries

    def periods_for_date(self, d: date) -> list[tuple[time, time]]:
        """Return the working periods for a specific date.

        Resolves weekly rules, overnight carryover from previous day,
        and planned exceptions. Returns sorted list of (start, end) time pairs.
        Half-open intervals: [start, end).
        """
        date_str = d.isoformat()

        # Check if there are exceptions for this date
        if date_str in self._exceptions:
            return self._resolve_exceptions(d)

        # No exceptions: build from rules + overnight carryover
        return self._resolve_rules(d)

    def _resolve_rules(self, d: date) -> list[tuple[time, time]]:
        """Resolve working periods from weekly rules for a date."""
        weekday = d.weekday()
        periods: list[tuple[time, time]] = []

        # Same-day periods from this day's rules
        if weekday in self._rules:
            for start, end in self._rules[weekday]:
                if _is_overnight(start, end):
                    # Overnight: only the same-day portion (start to midnight)
                    periods.append((start, time(0, 0)))
                else:
                    periods.append((start, end))

        # Carryover from previous day's overnight rules
        prev_date = d - timedelta(days=1)
        prev_weekday = prev_date.weekday()
        if prev_weekday in self._rules:
            for start, end in self._rules[prev_weekday]:
                if _is_overnight(start, end) and end != time(0, 0):
                    # Next-day portion: midnight to end
                    periods.append((time(0, 0), end))

        # Sort by start time
        periods.sort(key=lambda p: (p[0], p[1]))
        return periods

    def _resolve_exceptions(self, d: date) -> list[tuple[time, time]]:
        """Resolve working periods when exceptions exist for a date."""
        date_str = d.isoformat()
        entries = self._exceptions[date_str]

        # Process exceptions in order:
        # 1. If any is_working=False with no time range, it removes the entire day
        # 2. is_working=True entries add periods
        # 3. is_working=False with time range removes specific periods (not yet needed)

        has_full_removal = any(
            not entry.get("is_working", True)
            and "start" not in entry
            and "end" not in entry
            for entry in entries
        )

        if has_full_removal:
            # Start from empty, then add any is_working=True entries
            periods: list[tuple[time, time]] = []
            for entry in entries:
                if entry.get("is_working", False):
                    start = _parse_time(entry["start"])
                    end = _parse_time(entry["end"])
                    periods.append((start, end))
        else:
            # Start from rules, then apply modifications
            periods = self._resolve_rules(d)
            for entry in entries:
                if not entry.get("is_working", True):
                    # Remove specific period (future: implement partial removal)
                    pass
                elif entry.get("is_working", False):
                    start = _parse_time(entry["start"])
                    end = _parse_time(entry["end"])
                    periods.append((start, end))

        periods.sort(key=lambda p: p[0])
        return periods

    # ------------------------------------------------------------------
    # Layer 1 public API: time arithmetic (FR-001 through FR-005, FR-009)
    # ------------------------------------------------------------------

    def _datetime_intervals_for_date(
        self, d: date
    ) -> list[tuple[datetime, datetime]]:
        """Convert time-based periods to datetime intervals for a date."""
        periods = self.periods_for_date(d)
        result: list[tuple[datetime, datetime]] = []
        for p_start, p_end in periods:
            dt_start = datetime.combine(d, p_start)
            if p_end == time(0, 0):
                # Midnight = end of this day
                dt_end = datetime.combine(d + timedelta(days=1), time(0, 0))
            else:
                dt_end = datetime.combine(d, p_end)
            result.append((dt_start, dt_end))
        return result

    def add_minutes(self, start: datetime, minutes: int) -> datetime:
        """Forward walk: start + minutes of working time -> finish datetime.

        FR-001: Compute finish given start and working duration.
        FR-009: No horizon limit — walks day-by-day on demand.
        """
        if minutes == 0:
            return start

        remaining = minutes
        current_date = start.date()
        current_time = start

        while remaining > 0:
            intervals = self._datetime_intervals_for_date(current_date)

            for iv_start, iv_end in intervals:
                if iv_end <= current_time:
                    continue

                effective_start = max(iv_start, current_time)
                available = int((iv_end - effective_start).total_seconds()) // 60

                if available <= 0:
                    continue

                if remaining <= available:
                    return effective_start + timedelta(minutes=remaining)
                else:
                    remaining -= available
                    current_time = iv_end

            current_date += timedelta(days=1)
            current_time = datetime.combine(current_date, time(0, 0))

        return current_time

    def subtract_minutes(self, end: datetime, minutes: int) -> datetime:
        """Backward walk: end - minutes of working time -> start datetime.

        FR-002: Compute start given finish and working duration.
        """
        if minutes == 0:
            return end

        remaining = minutes
        current_date = end.date()
        current_time = end

        while remaining > 0:
            intervals = self._datetime_intervals_for_date(current_date)

            for iv_start, iv_end in reversed(intervals):
                if iv_start >= current_time:
                    continue

                effective_end = min(iv_end, current_time)
                available = int((effective_end - iv_start).total_seconds()) // 60

                if available <= 0:
                    continue

                if remaining <= available:
                    return effective_end - timedelta(minutes=remaining)
                else:
                    remaining -= available
                    current_time = iv_start

            current_date -= timedelta(days=1)
            current_time = datetime.combine(
                current_date + timedelta(days=1), time(0, 0)
            )

        return current_time

    def working_minutes_between(self, start: datetime, end: datetime) -> int:
        """Count working minutes in [start, end). FR-003."""
        if start >= end:
            return 0

        total = 0
        current_date = start.date()
        end_date = end.date()

        while current_date <= end_date:
            intervals = self._datetime_intervals_for_date(current_date)

            for iv_start, iv_end in intervals:
                effective_start = max(iv_start, start)
                effective_end = min(iv_end, end)

                if effective_start < effective_end:
                    minutes = int(
                        (effective_end - effective_start).total_seconds()
                    ) // 60
                    total += minutes

            current_date += timedelta(days=1)

        return total

    def working_intervals_in_range(
        self, start: datetime, end: datetime
    ) -> Iterator[tuple[datetime, datetime]]:
        """Yield (interval_start, interval_end) for working periods in [start, end).

        FR-004: Enumerate individual working intervals.
        """
        current_date = start.date()
        end_date = end.date()

        while current_date <= end_date:
            intervals = self._datetime_intervals_for_date(current_date)

            for iv_start, iv_end in intervals:
                effective_start = max(iv_start, start)
                effective_end = min(iv_end, end)

                if effective_start < effective_end:
                    yield (effective_start, effective_end)

            current_date += timedelta(days=1)
