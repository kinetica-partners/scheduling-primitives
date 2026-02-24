#!/usr/bin/env python
"""Visual verification report for scheduling-primitives.

Run:  uv run python scripts/verify.py

Produces a formatted report showing:
  1. Reference data (epoch, day/offset table, time/minute table)
  2. Calendar configurations (rules + exceptions as tables, ASCII week)
  3. Layer 1 tests (add_minutes, subtract_minutes, etc.)  -- input/output tables
  4. Layer 2 tests (bitmap, walk, allocate)  -- input/output tables + ASCII bitmap
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths and data loading
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "data" / "fixtures"
SCENARIOS = FIXTURES / "scenarios"

sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from scheduling_primitives.calendar import WorkingCalendar
from scheduling_primitives.debug import show_calendar, show_bitmap
from scheduling_primitives.occupancy import OccupancyBitmap, allocate, walk
from scheduling_primitives.resolution import MINUTE
from scheduling_primitives.types import InfeasibleError


def _load(path: Path):
    with open(path) as f:
        return json.load(f)


_ref = _load(FIXTURES / "reference.json")
_cals = _load(FIXTURES / "calendars.json")

EPOCH = datetime.fromisoformat(_ref["epoch"])
DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------
WIDTH = 90


def banner(title: str):
    print()
    print("=" * WIDTH)
    print(f"  {title}")
    print("=" * WIDTH)


def heading(title: str):
    print()
    print(f"  {title}")
    print(f"  {'-' * (len(title) + 2)}")


def table(headers: list[str], rows: list[list[str]], indent: int = 4):
    """Print a formatted table with auto-sized columns."""
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(cell))

    pad = " " * indent
    fmt = pad + "  ".join(f"{{:<{w}}}" for w in col_widths)
    sep = pad + "  ".join("-" * w for w in col_widths)

    print(fmt.format(*headers))
    print(sep)
    for row in rows:
        # Pad short rows
        padded = row + [""] * (len(headers) - len(row))
        print(fmt.format(*padded))


def _fmt_dt(iso: str) -> str:
    """Format ISO datetime as 'Mon 06 Jan 09:00'."""
    dt = datetime.fromisoformat(iso)
    day_name = DAY_NAMES[dt.weekday()]
    return f"{day_name} {dt.strftime('%d %b %H:%M')}"


def _make_cal(name: str) -> WorkingCalendar:
    config = _cals[name]
    rules = {int(k): v for k, v in config["rules"].items()}
    exceptions = config.get("exceptions", {})
    return WorkingCalendar(name, rules, exceptions)


def _make_bm(name: str = "standard", horizon_end: str | None = None):
    cal = _make_cal(name)
    h_end = datetime.fromisoformat(horizon_end) if horizon_end else datetime(2025, 1, 13)
    return OccupancyBitmap.from_calendar(cal, EPOCH, h_end, EPOCH, MINUTE)


# ---------------------------------------------------------------------------
# Section 1: Reference Data
# ---------------------------------------------------------------------------
def section_reference():
    banner("REFERENCE DATA")
    print(f"\n    Epoch:          {EPOCH.strftime('%A %Y-%m-%d %H:%M')}")
    print(f"    Minutes/day:    {_ref['minutes_per_day']}")
    print(f"    Work day:       {_ref['work_day_minutes']} min (08:00-17:00)")

    heading("Day / Offset Mapping")
    rows = []
    for d in _ref["days"]:
        dt = datetime.fromisoformat(d["date"] + "T00:00:00")
        day_name = DAY_NAMES[dt.weekday()] if d["name"] != "next_mon" else "Mon"
        rows.append([d["name"], d["date"], day_name, str(d["day_offset"])])
    table(["Name", "Date", "Day", "Offset (min)"], rows)

    heading("Time Label / Minute Mapping")
    rows = []
    for t in _ref["times"]:
        rows.append([t["label"], str(t["minutes"])])
    table(["Time", "Minutes"], rows)

    heading("Quick Offset Formula")
    print("    offset(day, time) = day_offset + time_minutes")
    print("    Example: Tue 08:00 = 1440 + 480 = 1920")
    print("    Example: Fri 16:30 = 5760 + 990 = 6750")


# ---------------------------------------------------------------------------
# Section 2: Calendar Configurations
# ---------------------------------------------------------------------------
def section_calendars():
    banner("CALENDAR CONFIGURATIONS")

    for cal_name, config in _cals.items():
        heading(f"Calendar: {cal_name}")
        print(f"    {config['description']}")

        # Rules table
        print()
        rows = []
        for wd in range(7):
            day_label = DAY_NAMES[wd]
            key = str(wd)
            if key in config["rules"]:
                periods = config["rules"][key]
                period_str = ", ".join(f"{p[0]}-{p[1]}" for p in periods)
            else:
                period_str = "(none)"
            rows.append([day_label, period_str])
        table(["Day", "Working Periods"], rows)

        # Exceptions table
        exc = config.get("exceptions", {})
        if exc:
            print()
            rows = []
            for exc_date, entries in exc.items():
                dt = datetime.fromisoformat(exc_date + "T00:00:00")
                day_label = DAY_NAMES[dt.weekday()]
                for entry in entries:
                    if not entry.get("is_working", True):
                        rows.append([exc_date, day_label, "Holiday (non-working)", ""])
                    else:
                        rows.append([
                            exc_date, day_label, "Overtime (working)",
                            f"{entry['start']}-{entry['end']}",
                        ])
            table(["Date", "Day", "Type", "Hours"], rows)
        else:
            print("    Exceptions: (none)")

        # ASCII week view
        cal = _make_cal(cal_name)
        print()
        show_calendar(cal, date(2025, 1, 6), date(2025, 1, 13))


# ---------------------------------------------------------------------------
# Section 3: Layer 1  -- Calendar Arithmetic
# ---------------------------------------------------------------------------
def section_calendar_arithmetic():
    banner("LAYER 1: CALENDAR ARITHMETIC")

    data = _load(SCENARIOS / "calendar_arithmetic.json")

    # --- add_minutes ---
    heading("Function: cal.add_minutes(start, minutes) -> datetime")
    print("    Walks forward through working time, skipping non-working gaps.\n")
    rows = []
    for s in data["add_minutes"]:
        cal = _make_cal(s["calendar"])
        start = datetime.fromisoformat(s["start"])
        result = cal.add_minutes(start, s["minutes"])
        expected = datetime.fromisoformat(s["expected"])
        match = "OK" if result == expected else "FAIL"
        rows.append([
            s["id"], s["calendar"],
            _fmt_dt(s["start"]), str(s["minutes"]),
            _fmt_dt(s["expected"]), match, s["notes"],
        ])
    table(["ID", "Calendar", "Start", "Min", "Result", "", "Notes"], rows)

    # --- subtract_minutes ---
    heading("Function: cal.subtract_minutes(end, minutes) -> datetime")
    print("    Walks backward through working time.\n")
    rows = []
    for s in data["subtract_minutes"]:
        cal = _make_cal(s["calendar"])
        start = datetime.fromisoformat(s["start"])
        result = cal.subtract_minutes(start, s["minutes"])
        expected = datetime.fromisoformat(s["expected"])
        match = "OK" if result == expected else "FAIL"
        rows.append([
            s["id"], s["calendar"],
            _fmt_dt(s["start"]), str(s["minutes"]),
            _fmt_dt(s["expected"]), match, s["notes"],
        ])
    table(["ID", "Calendar", "End", "Min", "Result", "", "Notes"], rows)

    # --- working_minutes_between ---
    heading("Function: cal.working_minutes_between(start, end) -> int")
    print("    Counts working minutes in [start, end).\n")
    rows = []
    for s in data["working_minutes_between"]:
        cal = _make_cal(s["calendar"])
        start = datetime.fromisoformat(s["start"])
        end = datetime.fromisoformat(s["end"])
        result = cal.working_minutes_between(start, end)
        match = "OK" if result == s["expected"] else "FAIL"
        rows.append([
            s["id"], s["calendar"],
            _fmt_dt(s["start"]), _fmt_dt(s["end"]),
            str(s["expected"]), str(result), match, s["notes"],
        ])
    table(["ID", "Calendar", "Start", "End", "Expected", "Actual", "", "Notes"], rows)

    # --- working_intervals_in_range ---
    heading("Function: cal.working_intervals_in_range(start, end) -> [(dt, dt), ...]")
    print("    Enumerates working intervals within a date range.\n")
    rows = []
    for s in data["working_intervals_in_range"]:
        cal = _make_cal(s["calendar"])
        start = datetime.fromisoformat(s["start"])
        end = datetime.fromisoformat(s["end"])
        intervals = list(cal.working_intervals_in_range(start, end))
        count = len(intervals)
        expected_count = len(s["expected"])
        match = "OK" if count == expected_count else "FAIL"
        if count > 0:
            interval_str = "; ".join(
                f"{_fmt_dt(p[0])}->{_fmt_dt(p[1])}" for p in s["expected"]
            )
        else:
            interval_str = "(none)"
        rows.append([
            s["id"], s["calendar"],
            _fmt_dt(s["start"]), _fmt_dt(s["end"]),
            str(count), match, interval_str,
        ])
    table(["ID", "Calendar", "Start", "End", "Count", "", "Intervals"], rows)

    # --- round_trips ---
    heading("Function: add(subtract(dt, n), n) == dt (round-trip identity)")
    print("    Verifies forward and backward walks are exact inverses.\n")
    rows = []
    for s in data["round_trips"]:
        cal = _make_cal(s["calendar"])
        dt = datetime.fromisoformat(s["datetime"])
        n = s["minutes"]
        if s.get("direction") == "reverse":
            result = cal.subtract_minutes(cal.add_minutes(dt, n), n)
            label = "sub(add(dt,n),n)"
        else:
            result = cal.add_minutes(cal.subtract_minutes(dt, n), n)
            label = "add(sub(dt,n),n)"
        match = "OK" if result == dt else "FAIL"
        rows.append([
            s["id"], s["calendar"], _fmt_dt(s["datetime"]),
            str(n), label, match, s["notes"],
        ])
    table(["ID", "Calendar", "Datetime", "Min", "Direction", "", "Notes"], rows)


# ---------------------------------------------------------------------------
# Section 4: Layer 2  -- Bitmap, Walk, Allocate
# ---------------------------------------------------------------------------
def section_bitmap():
    banner("LAYER 2: OCCUPANCY BITMAP")

    # --- from_calendar ---
    heading("Function: OccupancyBitmap.from_calendar(cal, start, end, epoch, res)")
    print("    Materialises calendar into integer capacity state.\n")
    occ = _load(SCENARIOS / "occupancy.json")
    for s in occ["bitmap_construction"]:
        bm = _make_bm(s["calendar"],
                       horizon_end=s["horizon_end"])
        rows = [
            ["Total bits", str(len(bm.bits)), str(s["expected_total_bits"]),
             "OK" if len(bm.bits) == s["expected_total_bits"] else "FAIL"],
            ["Free bits", str(sum(bm.bits)), str(s["expected_free_bits"]),
             "OK" if sum(bm.bits) == s["expected_free_bits"] else "FAIL"],
            ["horizon_begin", str(bm.horizon_begin), str(s["expected_horizon_begin"]),
             "OK" if bm.horizon_begin == s["expected_horizon_begin"] else "FAIL"],
            ["horizon_end", str(bm.horizon_end), str(s["expected_horizon_end"]),
             "OK" if bm.horizon_end == s["expected_horizon_end"] else "FAIL"],
        ]
        table(["Property", "Actual", "Expected", ""], rows)

    heading("Bit Range Verification")
    print("    Checks specific offset ranges have correct values (0=non-working, 1=free).\n")
    rows = []
    for s in occ["bit_ranges"]:
        bm = _make_bm(s.get("calendar", "standard"))
        ok = all(bm.bits[i] == s["expected_value"]
                 for i in range(s["range_start"], s["range_end"]))
        rows.append([
            s["id"],
            f"{s['range_start']}-{s['range_end']}",
            str(s["expected_value"]),
            "OK" if ok else "FAIL",
            s["notes"],
        ])
    table(["ID", "Range", "Value", "", "Notes"], rows)

    # ASCII view of standard bitmap
    heading("Standard Bitmap  -- Visual (. = non-working, - = free)")
    bm = _make_bm("standard")
    print()
    show_bitmap(bm, MINUTE, EPOCH)


def section_walk():
    banner("LAYER 2: WALK (read-only slot finding)")

    data = _load(SCENARIOS / "walk.json")

    # --- non-splittable ---
    heading("Function: walk(bm, op_id, earliest_start, work_units) -> AllocationRecord")
    print("    Finds earliest contiguous free run. Does NOT mutate bitmap.\n")
    rows = []
    for s in data["non_splittable"]:
        bm = _make_bm(s["calendar"])
        r = walk(bm, s["operation_id"],
                 earliest_start=s["earliest_start"],
                 work_units=s["work_units"])
        match = ("OK" if r.start == s["expected_start"]
                 and r.finish == s["expected_finish"] else "FAIL")
        spans_str = " + ".join(f"[{a},{b})" for a, b in r.spans)
        rows.append([
            s["id"],
            str(s["earliest_start"]), str(s["work_units"]),
            str(r.start), str(r.finish), spans_str,
            match, s["notes"],
        ])
    table(["ID", "From", "Units", "Start", "Finish", "Spans", "", "Notes"], rows)

    # --- non-splittable deadline ---
    heading("walk() with deadline  -- InfeasibleError expected")
    rows = []
    for s in data["non_splittable_deadline"]:
        bm = _make_bm(s["calendar"])
        try:
            walk(bm, s["operation_id"],
                 earliest_start=s["earliest_start"],
                 work_units=s["work_units"],
                 deadline=s["deadline"])
            err = "NO ERROR"
            match = "FAIL"
        except InfeasibleError as e:
            err = f"InfeasibleError(reason={e.reason})"
            match = "OK" if e.reason == s["expected_error"] else "FAIL"
        rows.append([
            s["id"],
            str(s["earliest_start"]), str(s["work_units"]),
            str(s["deadline"]),
            err, match, s["notes"],
        ])
    table(["ID", "From", "Units", "Deadline", "Error", "", "Notes"], rows)

    # --- splittable ---
    heading("walk() with allow_split=True  -- greedy consumption across gaps")
    rows = []
    for s in data["splittable"]:
        bm = _make_bm(s["calendar"])
        r = walk(bm, s["operation_id"],
                 earliest_start=s["earliest_start"],
                 work_units=s["work_units"],
                 allow_split=True)
        expected_spans = tuple(tuple(sp) for sp in s["expected_spans"])
        match = "OK" if r.spans == expected_spans else "FAIL"
        spans_str = " + ".join(f"[{a},{b})" for a, b in r.spans)
        rows.append([
            s["id"],
            str(s["earliest_start"]), str(s["work_units"]),
            str(r.start), str(r.finish), spans_str,
            match, s["notes"],
        ])
    table(["ID", "From", "Units", "Start", "Finish", "Spans", "", "Notes"], rows)


def section_allocate():
    banner("LAYER 2: ALLOCATE + DEALLOCATE")

    data = _load(SCENARIOS / "allocate.json")

    heading("Function: allocate(bm, op_id, start, units) -> AllocationRecord")
    print("    walk + commit: finds slot then marks bits as occupied.\n")

    # Sequential allocation demo with bitmap viz
    heading("Sequential Allocation Demo")
    print("    Three jobs allocated on standard calendar, bitmap before and after.\n")

    bm = _make_bm("standard")
    print("    BEFORE (all working time free):")
    print()
    show_bitmap(bm, MINUTE, EPOCH)

    r1 = allocate(bm, "JOB-A", earliest_start=480, work_units=300)
    r2 = allocate(bm, "JOB-B", earliest_start=480, work_units=480)
    r3 = allocate(bm, "JOB-C", earliest_start=480, work_units=120, allow_split=True)

    rows = [
        ["JOB-A", "480", "300", "False",
         str(r1.start), str(r1.finish),
         " + ".join(f"[{a},{b})" for a, b in r1.spans)],
        ["JOB-B", "480", "480", "False",
         str(r2.start), str(r2.finish),
         " + ".join(f"[{a},{b})" for a, b in r2.spans)],
        ["JOB-C", "480", "120", "True",
         str(r3.start), str(r3.finish),
         " + ".join(f"[{a},{b})" for a, b in r3.spans)],
    ]
    print()
    table(["Job", "From", "Units", "Split?", "Start", "Finish", "Spans"], rows)

    print("\n    AFTER:")
    print()
    show_bitmap(bm, MINUTE, EPOCH)

    # Deallocate demo
    heading("Deallocate Demo")
    print("    Removing JOB-B, then showing bitmap.\n")

    from scheduling_primitives.occupancy import deallocate
    deallocate(bm, r2)

    print("    AFTER removing JOB-B:")
    print()
    show_bitmap(bm, MINUTE, EPOCH)


def section_auto_extend():
    banner("LAYER 2: AUTO-EXTENSION")

    data = _load(SCENARIOS / "auto_extend.json")

    heading("Bitmap auto-extends when work exceeds horizon")
    print("    Initial bitmap covers Mon-Tue only (2880 bits).")
    print("    Allocations that exceed capacity trigger extension.\n")

    spec = next(s for s in data["auto_extend"] if s["id"] == "allocate_three_days")
    bm = _make_bm(spec["calendar"], horizon_end=spec["horizon_end"])
    initial = len(bm.bits)

    print(f"    Initial bitmap size: {initial} bits")
    print(f"    Mon working: 540 min, Tue working: 540 min, Total: 1080 min")
    print()

    rows = []
    for step in spec["sequence"]:
        r = allocate(bm, step["operation_id"],
                     earliest_start=step["earliest_start"],
                     work_units=step["work_units"])
        extended = "Yes" if len(bm.bits) > initial else "No"
        rows.append([
            step["operation_id"],
            str(step["work_units"]),
            str(r.start), str(r.finish),
            str(len(bm.bits)), extended,
        ])
    table(["Job", "Units", "Start", "Finish", "Bitmap Size", "Extended?"], rows)

    print(f"\n    Final bitmap size: {len(bm.bits)} bits "
          f"(grew from {initial})")
    print()
    show_bitmap(bm, MINUTE, EPOCH)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    banner("SCHEDULING-PRIMITIVES   --  VISUAL VERIFICATION REPORT")
    print(f"    Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"    Fixture data: {FIXTURES.relative_to(ROOT)}/")

    section_reference()
    section_calendars()
    section_calendar_arithmetic()
    section_bitmap()
    section_walk()
    section_allocate()
    section_auto_extend()

    banner("END OF REPORT")
    print()


if __name__ == "__main__":
    main()
