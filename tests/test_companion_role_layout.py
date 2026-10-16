"""Integration tests for role-driven companion-pair dispatch (Phase 31 LAYOUT-03).

Covers D-11..D-14:
- D-11: Lazy companion placement at apply_layout time (no auto-creation).
- D-12: Role->companion mapping lives as `_ROLE_COMPANION_MAP` constant in
  layout.py (no per-object companion_hint in overrides.json).
- D-13: Augment-don't-replace -- legacy `_COMPANION_NAMES` heuristic remains
  the fall-through for outlets where db.get_signal_role returns None.
- D-14: Six-key role map exactly: audio->meter~/right, status -> no companion
  (Q27 / F1: the status overlay hid its source), trigger/float/data/list -> None.

Source-of-audio for tests: `cycle~` outlet 0 has signal_role: "audio" curated
in `.claude/max-objects/overrides.json` (Phase 28 D-01 canonical fixture).
"""

import pytest

from src.maxpat.patcher import Patcher
from src.maxpat.layout import (
    apply_layout,
    _ROLE_COMPANION_MAP,
    _identify_companions,
    _COMPANION_GAP,
)


class TestRoleDrivenCompanions:
    """Role-first dispatch with fall-through to legacy `_COMPANION_NAMES`."""

    def test_role_companion_map_shape(self):
        """D-14: six keys exactly."""
        assert set(_ROLE_COMPANION_MAP.keys()) == {
            "audio", "status", "trigger", "float", "data", "list",
        }

    def test_role_map_audio_meter(self):
        """D-14: audio -> meter~ on the right."""
        assert _ROLE_COMPANION_MAP["audio"]["companion"] == "meter~"
        assert _ROLE_COMPANION_MAP["audio"]["placement"] == "right"

    def test_role_map_status_overlay(self):
        """Q27 / F1: status has no auto-companion (the overlay hid its source)."""
        assert _ROLE_COMPANION_MAP["status"]["companion"] is None
        assert _ROLE_COMPANION_MAP["status"]["placement"] is None

    def test_role_map_trigger_no_companion(self):
        """D-14: trigger has no auto-companion."""
        assert _ROLE_COMPANION_MAP["trigger"]["companion"] is None
        assert _ROLE_COMPANION_MAP["trigger"]["placement"] is None

    @pytest.mark.parametrize("role", ["float", "data", "list"])
    def test_role_map_no_companion_roles(self, role):
        """D-14: float/data/list have no auto-companion."""
        assert _ROLE_COMPANION_MAP[role]["companion"] is None
        assert _ROLE_COMPANION_MAP[role]["placement"] is None

    def test_audio_role_places_meter_right_of_source(self):
        """Integration: cycle~ (audio outlet) -> meter~ ends up to the right.

        cycle~ outlet 0 is role-stamped `audio` in Phase 30 overrides;
        the role map maps `audio` -> companion meter~ with placement "right".
        """
        p = Patcher()
        src = p.add_box("cycle~", ["440"])
        sink = p.add_box("meter~")
        p.add_connection(src, 0, sink, 0)
        apply_layout(p)
        # meter~ should be to the right of cycle~ (role map: audio -> meter~ right)
        assert sink.patching_rect[0] > src.patching_rect[0]
        # And placed near the right edge of the source (gap is _COMPANION_GAP).
        gap = sink.patching_rect[0] - (
            src.patching_rect[0] + src.patching_rect[2]
        )
        assert 0 <= gap < 50, (
            f"meter~ companion should be ~_COMPANION_GAP={_COMPANION_GAP}px "
            f"to the right of cycle~ source, got gap={gap}"
        )

    def test_role_path_hit_for_audio(self):
        """`_identify_companions` with db=p.db claims meter~ via role pass."""
        p = Patcher()
        src = p.add_box("cycle~", ["440"])
        sink = p.add_box("meter~")
        p.add_connection(src, 0, sink, 0)
        # Direct call into _identify_companions with db threaded through
        result = _identify_companions(
            list(p.boxes), list(p.lines), [], db=p.db,
        )
        assert sink.id in result
        # Plan 31-07: result entries are now (parent, placement) tuples.
        parent, placement = result[sink.id]
        assert parent is src
        assert placement == "right"

    def test_unaudited_role_falls_through_to_heuristic(self):
        """D-13: when db is None, legacy `_COMPANION_NAMES` still places meter~.

        Passing db=None exercises the same fall-through path as an unaudited
        outlet whose `get_signal_role` returns None: Pass A is skipped
        entirely, and Pass B (legacy) catches meter~ by name.
        """
        p = Patcher()
        src = p.add_box("cycle~", ["440"])
        sink = p.add_box("meter~")
        p.add_connection(src, 0, sink, 0)
        result = _identify_companions(
            list(p.boxes), list(p.lines), [], db=None,
        )
        assert sink.id in result, (
            "Legacy _COMPANION_NAMES heuristic must fire when role pass "
            "is bypassed (D-13 fall-through)"
        )

    def test_subpatcher_recursion_companion_placed(self):
        """Pitfall 3: companion placement fires inside subpatchers.

        `add_subpatcher` creates `inner = Patcher(db=self.db, ...)` so the
        recursive `apply_layout(box._inner_patcher, options)` call carries
        db through automatically.
        """
        p = Patcher()
        sp_box, inner = p.add_subpatcher("audio_chain", inlets=0, outlets=0)
        src = inner.add_box("cycle~", ["440"])
        sink = inner.add_box("meter~")
        inner.add_connection(src, 0, sink, 0)
        apply_layout(p)
        # Companion should be placed (role-driven) inside the subpatcher
        assert sink.patching_rect[0] > src.patching_rect[0]

    def test_db_none_uses_only_legacy_heuristic(self):
        """Back-compat: callers without db must still work."""
        p = Patcher()
        src = p.add_box("cycle~", ["440"])
        sink = p.add_box("meter~")
        p.add_connection(src, 0, sink, 0)
        # Should not raise
        result = _identify_companions(
            list(p.boxes), list(p.lines), [], db=None,
        )
        # meter~ is in _COMPANION_NAMES so heuristic still works
        assert sink.id in result

    # ------------------------------------------------------------------
    # Plan 31-07 — WR-01 (overlay placement) and WR-02 (single-parent guard)
    # ------------------------------------------------------------------

    def test_status_role_no_overlay(self, monkeypatch):
        """Q27 / F1: a status outlet -> flonum is laid out as an ordinary row
        box below its source, never stacked on it.

        No MSP outlet has signal_role='status' curated for cycle~, so we
        monkey-patch ObjectDatabase.get_signal_role to return 'status' for a
        fixed (name, outlet) pair.
        """
        from src.maxpat.db_lookup import ObjectDatabase

        original_get_role = ObjectDatabase.get_signal_role

        def fake_get_role(self, name, outlet):
            if name == "cycle~" and outlet == 0:
                return "status"
            return original_get_role(self, name, outlet)

        monkeypatch.setattr(
            ObjectDatabase, "get_signal_role", fake_get_role
        )

        p = Patcher()
        src = p.add_box("cycle~", ["440"])
        readout = p.add_box("flonum")
        p.add_connection(src, 0, readout, 0)
        apply_layout(p)

        sx, sy, sw, sh = src.patching_rect
        rx, ry, rw, rh = readout.patching_rect
        assert not (sx < rx + rw and rx < sx + sw and sy < ry + rh and ry < sy + sh), (
            f"status readout must not overlap its source; "
            f"readout={readout.patching_rect} src={src.patching_rect}"
        )
        assert "ignoreclick" not in readout.extra_attrs
        assert ry > sy
        assert p.boxes[0] is not readout

    def test_status_role_overlay_rect_not_aliased(self, monkeypatch):
        """Pitfall 1 (mirror of add_overlay_readout): mutating the readout's
        patching_rect must NOT mutate the source's patching_rect.
        """
        from src.maxpat.db_lookup import ObjectDatabase

        original_get_role = ObjectDatabase.get_signal_role

        def fake_get_role(self, name, outlet):
            if name == "cycle~" and outlet == 0:
                return "status"
            return original_get_role(self, name, outlet)

        monkeypatch.setattr(
            ObjectDatabase, "get_signal_role", fake_get_role
        )

        p = Patcher()
        src = p.add_box("cycle~", ["440"])
        readout = p.add_box("flonum")
        p.add_connection(src, 0, readout, 0)
        apply_layout(p)

        original_src_x = src.patching_rect[0]
        readout.patching_rect[0] = 9999.0
        assert src.patching_rect[0] == original_src_x, (
            "overlay placement aliased patching_rect — should be a copy"
        )

    def test_pass_a_skips_multi_parent_companion(self):
        """WR-02 fix: a meter~ summing two cycle~ sources is NOT claimed
        by Pass A (single-parent guard matches Pass B's invariant).
        """
        p = Patcher()
        src1 = p.add_box("cycle~", ["440"])
        src2 = p.add_box("cycle~", ["880"])
        sink = p.add_box("meter~")
        p.add_connection(src1, 0, sink, 0)
        p.add_connection(src2, 0, sink, 0)
        result = _identify_companions(
            list(p.boxes), list(p.lines), [], db=p.db,
        )
        # Pass A skips because len(incoming[sink.id]) == 2.
        # Pass B also skips because of its own len(parents) != 1 guard.
        # Therefore meter~ is unclaimed by either pass.
        assert sink.id not in result, (
            "Pass A's single-parent guard (WR-02) should skip a meter~ "
            "with multiple incoming audio sources"
        )

    def test_pass_a_single_parent_still_claimed(self):
        """WR-02 regression check: the happy single-parent case still works."""
        p = Patcher()
        src = p.add_box("cycle~", ["440"])
        sink = p.add_box("meter~")
        p.add_connection(src, 0, sink, 0)
        result = _identify_companions(
            list(p.boxes), list(p.lines), [], db=p.db,
        )
        assert sink.id in result
        # Result entries are now (parent, placement) tuples.
        parent_box, placement = result[sink.id]
        assert parent_box is src
        assert placement == "right"  # audio role -> right placement

    def test_identify_companions_returns_tuple_shape(self):
        """Contract: _identify_companions returns dict[str, tuple[Box, str]].

        Each value is (parent_box, placement) where placement is 'right' or
        'overlay'. Plan 31-07 enforces this shape so _place_companions can
        branch on placement without re-querying the DB.
        """
        p = Patcher()
        src = p.add_box("cycle~", ["440"])
        sink = p.add_box("meter~")
        p.add_connection(src, 0, sink, 0)
        result = _identify_companions(
            list(p.boxes), list(p.lines), [], db=p.db,
        )
        assert sink.id in result
        value = result[sink.id]
        assert isinstance(value, tuple) and len(value) == 2
        parent, placement = value
        assert parent.name == "cycle~"
        assert placement in ("right", "overlay")
