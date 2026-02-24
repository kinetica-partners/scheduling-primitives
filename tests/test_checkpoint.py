"""Tests for checkpoint/restore/copy on OccupancyBitmap (T039-T042).

Test data loaded from: data/fixtures/scenarios/checkpoint.json
"""

from __future__ import annotations

import pytest

from conftest import load_scenarios, make_bitmap

_data = load_scenarios("checkpoint")


class TestCheckpointRestore:
    """checkpoint() and restore() for speculative planning."""

    def test_single_undo(self):
        """Checkpoint before allocate, restore undoes it."""
        from scheduling_primitives.occupancy import allocate

        spec = _data["checkpoint_restore"][0]
        bm = make_bitmap(spec["calendar"])
        snap = bm.checkpoint()
        bits_before = bytes(bm.bits)

        a = spec["allocate"]
        allocate(bm, a["operation_id"],
                 earliest_start=a["earliest_start"],
                 work_units=a["work_units"])
        assert bytes(bm.bits) != bits_before, "allocate should change bits"

        bm.restore(snap)
        assert bytes(bm.bits) == bits_before, spec["notes"]

    def test_multiple_undo(self):
        """Checkpoint before two allocates, restore undoes both."""
        from scheduling_primitives.occupancy import allocate

        spec = _data["checkpoint_restore"][1]
        bm = make_bitmap(spec["calendar"])
        snap = bm.checkpoint()
        bits_before = bytes(bm.bits)

        for step in spec["sequence"]:
            allocate(bm, step["operation_id"],
                     earliest_start=step["earliest_start"],
                     work_units=step["work_units"])

        bm.restore(snap)
        assert bytes(bm.bits) == bits_before, spec["notes"]

    def test_restore_to_earlier(self):
        """Two checkpoints; restoring to earlier undoes both allocations."""
        from scheduling_primitives.occupancy import allocate

        spec = _data["checkpoint_restore"][2]
        bm = make_bitmap(spec["calendar"])

        snapshots: dict[str, bytes] = {}
        for step in spec["steps"]:
            if step["action"] == "checkpoint":
                snapshots[step["label"]] = bm.checkpoint()
            elif step["action"] == "allocate":
                allocate(bm, step["operation_id"],
                         earliest_start=step["earliest_start"],
                         work_units=step["work_units"])
            elif step["action"] == "restore":
                bm.restore(snapshots[step["label"]])

        # After restoring to snap_0, should be identical to initial state
        bm_fresh = make_bitmap(spec["calendar"])
        assert bytes(bm.bits) == bytes(bm_fresh.bits), spec["notes"]

    def test_keep_allocation(self):
        """Checkpoint after allocate preserves the allocation on restore."""
        from scheduling_primitives.occupancy import allocate

        spec = _data["checkpoint_restore"][3]
        bm = make_bitmap(spec["calendar"])

        a = spec["allocate"]
        record = allocate(bm, a["operation_id"],
                          earliest_start=a["earliest_start"],
                          work_units=a["work_units"])
        bits_after_alloc = bytes(bm.bits)

        snap = bm.checkpoint()

        # Allocate something else
        allocate(bm, "OP-EXTRA", earliest_start=480, work_units=60)

        bm.restore(snap)
        assert bytes(bm.bits) == bits_after_alloc, spec["notes"]


class TestCopy:
    """copy() for branching — deep independence."""

    def test_deep_independence(self):
        """Allocating on copy does not affect original."""
        from scheduling_primitives.occupancy import allocate

        spec = _data["copy"][0]
        bm = make_bitmap(spec["calendar"])
        bits_original = bytes(bm.bits)

        copy = bm.copy()
        a = spec["allocate_on_copy"]
        allocate(copy, a["operation_id"],
                 earliest_start=a["earliest_start"],
                 work_units=a["work_units"])

        assert bytes(bm.bits) == bits_original, spec["notes"]
        assert bytes(copy.bits) != bits_original, "copy should be modified"

    def test_mutation_isolation(self):
        """Allocating on original does not affect copy."""
        from scheduling_primitives.occupancy import allocate

        spec = _data["copy"][1]
        bm = make_bitmap(spec["calendar"])
        copy = bm.copy()
        bits_copy = bytes(copy.bits)

        a = spec["allocate_on_original"]
        allocate(bm, a["operation_id"],
                 earliest_start=a["earliest_start"],
                 work_units=a["work_units"])

        assert bytes(copy.bits) == bits_copy, spec["notes"]
        assert bytes(bm.bits) != bits_copy, "original should be modified"
