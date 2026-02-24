"""Boundary: TimeResolution — datetime ↔ integer conversion."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


def _reject_aware(dt: datetime, name: str) -> None:
    """Reject timezone-aware datetimes (FR-035)."""
    if dt.tzinfo is not None:
        raise TypeError(
            f"{name} must be a naive datetime (no tzinfo), "
            f"got tzinfo={dt.tzinfo!r}. "
            f"All datetimes are assumed to be in facility local time."
        )


@dataclass(frozen=True)
class TimeResolution:
    """Converts between datetime and integer time. Immutable.

    The time unit is a parameter set once at the boundary.
    All internal engine arithmetic uses integers.
    """

    unit_seconds: int
    label: str

    def to_int(self, dt: datetime, epoch: datetime) -> int:
        """Convert datetime to integer units from epoch.

        Raises TypeError if dt or epoch is timezone-aware.
        Raises ValueError if dt is not aligned to the resolution.
        """
        _reject_aware(dt, "dt")
        _reject_aware(epoch, "epoch")

        delta_seconds = int((dt - epoch).total_seconds())
        remainder = delta_seconds % self.unit_seconds
        if remainder != 0:
            raise ValueError(
                f"datetime {dt.isoformat()} does not align to {self.label} "
                f"resolution (unit_seconds={self.unit_seconds}). "
                f"Remainder: {remainder}s. "
                f"No implicit rounding — caller must ensure alignment."
            )
        return delta_seconds // self.unit_seconds

    def to_datetime(self, t: int, epoch: datetime) -> datetime:
        """Convert integer units from epoch to datetime."""
        _reject_aware(epoch, "epoch")
        from datetime import timedelta

        return epoch + timedelta(seconds=t * self.unit_seconds)


MINUTE = TimeResolution(unit_seconds=60, label="minute")
HOUR = TimeResolution(unit_seconds=3600, label="hour")
