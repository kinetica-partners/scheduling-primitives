# Quickstart: scheduling-primitives

## Install

```bash
uv add scheduling-primitives
```

## 1. Define a calendar

```python
from scheduling_primitives import WorkingCalendar

# Mon-Fri 08:00-17:00, Tuesday is a holiday, Saturday overtime 10:00-14:00
rules = {
    "standard": {
        0: [("08:00", "17:00")],  # Monday
        1: [("08:00", "17:00")],  # Tuesday
        2: [("08:00", "17:00")],  # Wednesday
        3: [("08:00", "17:00")],  # Thursday
        4: [("08:00", "17:00")],  # Friday
    }
}
exceptions = {
    "standard": {
        "2025-01-07": [{"is_working": False}],                           # Tuesday holiday
        "2025-01-11": [{"is_working": True, "start": "10:00", "end": "14:00"}],  # Saturday overtime
    }
}
cal = WorkingCalendar("standard", rules, exceptions)
```

## 2. Ask time questions (Layer 1)

```python
from datetime import datetime

start = datetime(2025, 1, 6, 16, 30)  # Monday 16:30

# "If I start a 60-minute job at 4:30pm Monday, when does it finish?"
finish = cal.add_minutes(start, 60)
# → Wednesday 09:30 (skips Tuesday holiday, 30 min Monday + 30 min Wednesday)

# "How many working minutes between Monday 09:00 and Wednesday 12:00?"
count = cal.working_minutes_between(
    datetime(2025, 1, 6, 9, 0),
    datetime(2025, 1, 8, 12, 0),
)
# → 660 (480 Monday + 0 Tuesday + 180 Wednesday morning)
```

## 3. Track capacity (Layer 2)

```python
from scheduling_primitives import OccupancyBitmap, allocate, deallocate, MINUTE

epoch = datetime(2025, 1, 6, 0, 0)
bitmap = OccupancyBitmap.from_calendar(
    cal,
    horizon_start=datetime(2025, 1, 6, 0, 0),
    horizon_end=datetime(2025, 1, 12, 0, 0),
    epoch=epoch,
    resolution=MINUTE,
)

# Allocate a 120-minute non-splittable job starting Monday 09:00
record = allocate(bitmap, "JOB-001", earliest_start=540, work_units=120)
# record.start=540, record.finish=660 (Mon 09:00-11:00)
# record.spans = ((540, 660),)

# Allocate a 60-minute splittable job starting Monday 16:30
record2 = allocate(bitmap, "JOB-002", earliest_start=990, work_units=60, allow_split=True)
# record2.spans = ((990, 1020), (2460, 2490))
# 30 min Monday 16:30-17:00 + 30 min Wednesday 09:00-09:30
```

## 4. Backtracking (speculative planning)

```python
snap = bitmap.checkpoint()

# Try an allocation
record3 = allocate(bitmap, "JOB-003", earliest_start=660, work_units=480)

# Didn't like it? Restore.
bitmap.restore(snap)
# bitmap is now identical to before JOB-003 was allocated
```

## 5. Dynamic exceptions (mid-run changes)

```python
from scheduling_primitives import apply_dynamic_exception

# Machine breaks down Wednesday 10:00-12:00
affected = apply_dynamic_exception(bitmap, begin=2520, end=2640, is_working=False)
# affected = [list of allocation records that overlap the breakdown window]
# Caller decides how to handle affected allocations

# Approve overtime Saturday 10:00-14:00
apply_dynamic_exception(bitmap, begin=7260, end=7500, is_working=True)
# Capacity added — walk can now use Saturday
```

## 6. Visual verification (development)

```python
from scheduling_primitives.debug import show_bitmap

show_bitmap(bitmap, resolution=MINUTE, epoch=epoch)
# Prints ASCII representation to stdout:
#   Mon 06  ░░░AAAA····················░░░
#   Tue 07  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  (holiday)
#   Wed 08  BB·························░░░
#   ...
```
