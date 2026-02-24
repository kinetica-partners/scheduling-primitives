"""ASCII visualisation for development-time verification.

This module is dev-only and not imported by production code.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta


def show_calendar(
    cal: "WorkingCalendar",  # noqa: F821 — avoid circular import
    start: date,
    end: date,
) -> str:
    """Print ASCII calendar view showing working periods for a date range.

    Each row is one day. Working periods are shown as blocks.
    Returns the string and also prints to stdout.

    Args:
        cal: WorkingCalendar instance
        start: First date to show (inclusive)
        end: Last date to show (exclusive)
    """
    lines: list[str] = []
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    # 24-hour timeline, each char = 30 minutes (48 chars per day)
    chars_per_day = 48
    minutes_per_char = 30

    # Header
    header_hours = "".join(f"{h:02d}" if h % 3 == 0 else "  " for h in range(24))
    lines.append(f"{'':>16s}  {header_hours}")

    current = start
    while current < end:
        day_name = day_names[current.weekday()]
        label = f"{day_name} {current.strftime('%d %b')}"

        periods = cal.periods_for_date(current)

        # Build the row: '.' = non-working, '#' = working
        row = list("." * chars_per_day)

        for p_start, p_end in periods:
            start_min = p_start.hour * 60 + p_start.minute
            if p_end == time(0, 0):
                end_min = 24 * 60
            else:
                end_min = p_end.hour * 60 + p_end.minute

            start_char = start_min // minutes_per_char
            end_char = end_min // minutes_per_char

            for i in range(start_char, min(end_char, chars_per_day)):
                row[i] = "#"

        row_str = "".join(row)
        lines.append(f"{label:>16s}  {row_str}")

        current += timedelta(days=1)

    result = "\n".join(lines)
    print(result)
    return result


def show_bitmap(
    bitmap: "OccupancyBitmap",  # noqa: F821
    resolution: "TimeResolution",  # noqa: F821
    epoch: datetime,
) -> str:
    """Print ASCII bitmap view with allocations.

    Legend: '.' = non-working, '-' = free, 'A'-'Z' = allocated (by operation)
    Each row is one day, each char = 30 minutes (at minute resolution).
    Returns the string and also prints to stdout.
    """
    lines: list[str] = []
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    chars_per_day = 48
    minutes_per_char = 30

    # Build allocation label map: operation_id -> letter
    op_labels: dict[str, str] = {}
    label_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    for alloc in bitmap._allocations:
        if alloc.operation_id not in op_labels:
            idx = len(op_labels) % len(label_chars)
            op_labels[alloc.operation_id] = label_chars[idx]

    # Build per-unit ownership: unit -> label char
    unit_owner: dict[int, str] = {}
    for alloc in bitmap._allocations:
        label = op_labels[alloc.operation_id]
        for span_begin, span_end in alloc.spans:
            for u in range(span_begin, span_end):
                unit_owner[u] = label

    # Header
    header_hours = "".join(f"{h:02d}" if h % 3 == 0 else "  " for h in range(24))
    lines.append(f"{'':>16s}  {header_hours}")

    # Determine date range
    dt_start = resolution.to_datetime(bitmap.horizon_begin, epoch)
    dt_end = resolution.to_datetime(bitmap.horizon_end, epoch)
    current_date = dt_start.date()
    end_date = dt_end.date()

    while current_date <= end_date:
        day_name = day_names[current_date.weekday()]
        label = f"{day_name} {current_date.strftime('%d %b')}"

        row = list("." * chars_per_day)
        day_offset_minutes = int(
            (datetime.combine(current_date, time(0, 0)) - epoch).total_seconds()
        ) // 60

        for char_idx in range(chars_per_day):
            minute_start = day_offset_minutes + char_idx * minutes_per_char
            minute_end = minute_start + minutes_per_char

            # Check what's in this 30-minute block
            has_free = False
            has_alloc = False
            alloc_label = None

            for m in range(minute_start, minute_end):
                bit_idx = m - bitmap.horizon_begin
                if 0 <= bit_idx < len(bitmap.bits):
                    if m in unit_owner:
                        has_alloc = True
                        alloc_label = unit_owner[m]
                    elif bitmap.bits[bit_idx] == 1:
                        has_free = True

            if has_alloc and alloc_label:
                row[char_idx] = alloc_label
            elif has_free:
                row[char_idx] = "-"
            # else: stays '.' (non-working)

        row_str = "".join(row)
        lines.append(f"{label:>16s}  {row_str}")
        current_date += timedelta(days=1)

    # Legend
    if op_labels:
        legend_parts = [f"{v}={k}" for k, v in op_labels.items()]
        lines.append(f"\nLegend: . = non-working, - = free, {', '.join(legend_parts)}")

    result = "\n".join(lines)
    print(result)
    return result


def show_multi_resource(
    resources: dict[str, "OccupancyBitmap"],  # noqa: F821
    resolution: "TimeResolution",  # noqa: F821
    epoch: datetime,
) -> str:
    """Print ASCII multi-resource view.

    Shows one section per resource, each with the standard bitmap layout.
    Returns the string and also prints to stdout.
    """
    import io
    import sys

    sections: list[str] = []

    for resource_id, bitmap in resources.items():
        sections.append(f"=== {resource_id} ===")
        # Capture show_bitmap output without double-printing
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        section = show_bitmap(bitmap, resolution, epoch)
        sys.stdout = old_stdout
        sections.append(section)
        sections.append("")

    result = "\n".join(sections)
    print(result)
    return result
