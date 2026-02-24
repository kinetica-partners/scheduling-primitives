"""scheduling-primitives: Mechanical foundations for finite capacity scheduling."""

from scheduling_primitives.calendar import WorkingCalendar
from scheduling_primitives.greedy import Operation, greedy_schedule
from scheduling_primitives.occupancy import (
    OccupancyBitmap,
    allocate,
    apply_dynamic_exception,
    deallocate,
    walk,
)
from scheduling_primitives.resolution import HOUR, MINUTE, TimeResolution
from scheduling_primitives.types import AllocationRecord, InfeasibleError

__all__ = [
    "AllocationRecord",
    "HOUR",
    "InfeasibleError",
    "MINUTE",
    "OccupancyBitmap",
    "Operation",
    "TimeResolution",
    "WorkingCalendar",
    "allocate",
    "apply_dynamic_exception",
    "deallocate",
    "greedy_schedule",
    "walk",
]
