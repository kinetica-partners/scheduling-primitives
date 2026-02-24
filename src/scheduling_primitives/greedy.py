"""Reference scheduler: simple greedy composition of scheduling primitives.

This module demonstrates how the library's primitives compose into a working
scheduler. It is documentation in code form -- a teaching tool for
practitioners and a usage guide for contributors. It is not a production
scheduler.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from scheduling_primitives.occupancy import OccupancyBitmap, allocate
from scheduling_primitives.types import AllocationRecord


@dataclass
class Operation:
    """A unit of work to be scheduled on a specific resource."""

    operation_id: str
    resource_id: str
    work_units: int
    earliest_start: int = 0
    allow_split: bool = False
    min_split: int = 1
    deadline: int | None = None


def greedy_schedule(
    operations: list[Operation],
    resources: dict[str, OccupancyBitmap],
) -> list[AllocationRecord]:
    """Schedule operations greedily in input order.

    Each operation is allocated to its resource's bitmap at the earliest
    available slot. The input order determines priority -- earlier operations
    get first choice of capacity.

    Args:
        operations: Ordered list of operations to schedule.
        resources: Mapping of resource_id to OccupancyBitmap.

    Returns:
        List of AllocationRecords in the same order as the input operations.

    Raises:
        KeyError: If an operation references a resource not in the dict.
        InfeasibleError: If an operation cannot be scheduled (deadline, etc).
    """
    results: list[AllocationRecord] = []
    for op in operations:
        bitmap = resources[op.resource_id]
        record = allocate(
            bitmap,
            op.operation_id,
            earliest_start=op.earliest_start,
            work_units=op.work_units,
            allow_split=op.allow_split,
            min_split=op.min_split,
            deadline=op.deadline,
        )
        results.append(record)
    return results
