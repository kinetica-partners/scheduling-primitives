"""Shared types: AllocationRecord and InfeasibleError."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AllocationRecord:
    """Immutable record of a committed or candidate allocation.

    Invariants:
        - sum(end - begin for begin, end in spans) == work_units
        - All spans are within [start, finish)
        - Spans are sorted by begin and non-overlapping
    """

    operation_id: str
    resource_id: str
    start: int
    finish: int
    work_units: int
    allow_split: bool
    spans: tuple[tuple[int, int], ...]

    @property
    def wall_time(self) -> int:
        """Total elapsed time including non-working gaps."""
        return self.finish - self.start

    def is_complete(self, required_work_units: int) -> bool:
        """Whether this allocation fulfils the required work."""
        return self.work_units >= required_work_units


class InfeasibleError(Exception):
    """Raised when work cannot be scheduled before deadline or horizon end."""

    def __init__(
        self,
        operation_id: str,
        work_units_remaining: int,
        work_units_requested: int,
        reason: str,
    ) -> None:
        self.operation_id = operation_id
        self.work_units_remaining = work_units_remaining
        self.work_units_requested = work_units_requested
        self.reason = reason
        super().__init__(
            f"Infeasible: operation {operation_id!r} cannot complete — "
            f"{work_units_remaining}/{work_units_requested} units remaining "
            f"(reason: {reason})"
        )
