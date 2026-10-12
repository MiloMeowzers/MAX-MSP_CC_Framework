"""Q3 critic-precision regression tests (quick 261012-di7).

Covers `.planning/reviews/2026-10-11-fix-plan.md` Q3 and review findings:
  - E1: fan-out without trigger -- display-only sinks and preset membership
    outlets are skipped, signal-ness comes from outlettype (not the `~` name),
    trigger outlets are checked, and only reconvergent fan-out (two branches
    meeting one box at different inlets) is a blocker; everything else warns.
  - E4: Bach-llll -- command sources exempt, note severity.
  - E2: the control-rate-to-signal-rate check is removed (OQ2-A).
  - Comment `#N` (review §4.1 class 7 / §4.4 R3): comments fed by a
    `set ... #N` message box are not flagged.

Committed patches are opened read-only and every critic/validator call gets a
freshly loaded dict. No committed patch file is ever written.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.maxpat.critics.structure_critic import review_structure
from tests.test_critics import _make_patch
from tests.test_integration_patches import _FANOUT_RE

_REPO_ROOT = Path(__file__).resolve().parent.parent

_FAN_PREFIX = "Fan-out without trigger"


def _load(rel: str) -> dict:
    """Load a committed patch read-only (fresh dict on every call)."""
    with open(_REPO_ROOT / rel) as f:
        return json.load(f)


def _box(box_id, text="", maxclass="newobj", numinlets=1, numoutlets=1,
         outlettype=None, with_outlettype=True):
    box = {
        "id": box_id,
        "maxclass": maxclass,
        "text": text,
        "numinlets": numinlets,
        "numoutlets": numoutlets,
    }
    if with_outlettype:
        box["outlettype"] = outlettype if outlettype is not None else [""] * numoutlets
    return box


def _ln(src, outlet, dst, inlet):
    return {"source": [src, outlet], "destination": [dst, inlet]}


def _fan(results):
    """Fan-out findings, as (result, source_id, outlet)."""
    out = []
    for r in results:
        if r.finding.startswith(_FAN_PREFIX):
            m = _FANOUT_RE.search(r.finding)
            assert m, f"Fan-out finding breaks the prefix contract: {r.finding}"
            out.append((r, m.group(1), int(m.group(2))))
    return out


def _fan_for(results, src_id, outlet=None):
    return [
        r for r, sid, o in _fan(results)
        if sid == src_id and (outlet is None or o == outlet)
    ]


# Reusable boxes
def _number(box_id="obj-1"):
    return _box(box_id, maxclass="number", numinlets=1, numoutlets=2,
                outlettype=["", "bang"])


def _plus(box_id="obj-9"):
    return _box(box_id, text="+", numinlets=2, numoutlets=1, outlettype=["int"])


def _counter(box_id):
    return _box(box_id, text="counter 0 10", numinlets=5, numoutlets=4,
                outlettype=["", "", "", ""])


def _toggle(box_id):
    return _box(box_id, maxclass="toggle", numinlets=1, numoutlets=1,
                outlettype=["int"])


# ===========================================================================
# E1: fan-out unit fixtures
# ===========================================================================

class TestFanOutPrecision:

    def test_display_sink_flonum_skipped(self):
        """scale -> flonum (no outgoing cord) + send: no fan finding."""
        boxes = [
            _box("obj-1", text="scale 0 127 0. 1.", numinlets=6, numoutlets=1,
                 outlettype=[""]),
            _box("obj-2", maxclass="flonum", numinlets=1, numoutlets=2,
                 outlettype=["", "bang"]),
            _box("obj-3", text="s cutoff", numinlets=1, numoutlets=0,
                 outlettype=[]),
        ]
        lines = [_ln("obj-1", 0, "obj-2", 0), _ln("obj-1", 0, "obj-3", 0)]
        assert _fan(review_structure(_make_patch(boxes, lines))) == []

    def test_display_box_with_outgoing_cord_is_a_branch(self):
        """flonum that feeds *~ is a real branch: one fan warning."""
        boxes = [
            _box("obj-1", text="scale 0 127 0. 1.", numinlets=6, numoutlets=1,
                 outlettype=[""]),
            _box("obj-2", maxclass="flonum", numinlets=1, numoutlets=2,
                 outlettype=["", "bang"]),
            _box("obj-3", text="s cutoff", numinlets=1, numoutlets=0,
                 outlettype=[]),
            _box("obj-4", text="*~ 0.5", numinlets=2, numoutlets=1,
                 outlettype=["signal"]),
        ]
        lines = [
            _ln("obj-1", 0, "obj-2", 0),
            _ln("obj-1", 0, "obj-3", 0),
            _ln("obj-2", 0, "obj-4", 1),
        ]
        fans = _fan(review_structure(_make_patch(boxes, lines)))
        assert [r.severity for r, _, _ in fans] == ["warning"]

    def _preset_patch(self, outlet):
        boxes = [
            _box("obj-1", maxclass="preset", numinlets=1, numoutlets=5,
                 outlettype=["", "", "", "", ""]),
        ]
        lines = []
        for k in range(2):
            tid = f"obj-t{k}"
            boxes.append(_toggle(tid))
            lines.append(_ln("obj-1", outlet, tid, 0))
        return _make_patch(boxes, lines)

    def test_preset_membership_outlets_skipped(self):
        """preset outlets 0/2/4 are include/exclude/capture cords."""
        for outlet in (0, 2, 4):
            fans = _fan(review_structure(self._preset_patch(outlet)))
            assert fans == [], f"outlet {outlet}: {[r.finding for r, _, _ in fans]}"

    def test_preset_outlet1_still_checked(self):
        boxes = [
            _box("obj-1", maxclass="preset", numinlets=1, numoutlets=5,
                 outlettype=["", "", "", "", ""]),
            _counter("obj-2"),
            _toggle("obj-3"),
        ]
        lines = [_ln("obj-1", 1, "obj-2", 0), _ln("obj-1", 1, "obj-3", 0)]
        fans = _fan(review_structure(_make_patch(boxes, lines)))
        assert [r.severity for r, _, _ in fans] == ["warning"]

    def test_signal_outlettype_on_tildeless_name_skipped(self):
        """`p fx` with outlettype signal -> 2 *~: no fan finding."""
        boxes = [
            _box("obj-1", text="p fx", numinlets=1, numoutlets=1,
                 outlettype=["signal"]),
            _box("obj-2", text="*~ 0.5", numinlets=2, numoutlets=1,
                 outlettype=["signal"]),
            _box("obj-3", text="*~ 0.3", numinlets=2, numoutlets=1,
                 outlettype=["signal"]),
        ]
        lines = [_ln("obj-1", 0, "obj-2", 0), _ln("obj-1", 0, "obj-3", 0)]
        assert _fan(review_structure(_make_patch(boxes, lines))) == []

    def test_control_outlet_on_tilde_object_checked(self):
        """buffer~ outlet 1 (bang) -> 2 non-display boxes: fan finding."""
        boxes = [
            _box("obj-1", text="buffer~ snd", numinlets=1, numoutlets=2,
                 outlettype=["float", "bang"]),
            _counter("obj-2"),
            _toggle("obj-3"),
        ]
        lines = [_ln("obj-1", 1, "obj-2", 0), _ln("obj-1", 1, "obj-3", 0)]
        fans = _fan(review_structure(_make_patch(boxes, lines)))
        assert len(fans) == 1
        assert fans[0][1:] == ("obj-1", 1)

    def test_missing_outlettype_falls_back_to_tilde_name(self):
        boxes = [
            _box("obj-1", text="cycle~ 440", numinlets=2, numoutlets=1,
                 with_outlettype=False),
            _box("obj-2", text="*~ 0.5", numinlets=2, numoutlets=1,
                 outlettype=["signal"]),
            _box("obj-3", text="*~ 0.3", numinlets=2, numoutlets=1,
                 outlettype=["signal"]),
        ]
        lines = [_ln("obj-1", 0, "obj-2", 0), _ln("obj-1", 0, "obj-3", 0)]
        assert _fan(review_structure(_make_patch(boxes, lines))) == []

    def test_trigger_outlet_fan_out_warns(self):
        boxes = [
            _box("obj-1", text="t b b", numinlets=1, numoutlets=2,
                 outlettype=["bang", "bang"]),
            _counter("obj-2"),
            _toggle("obj-3"),
        ]
        lines = [_ln("obj-1", 0, "obj-2", 0), _ln("obj-1", 0, "obj-3", 0)]
        fans = _fan(review_structure(_make_patch(boxes, lines)))
        assert [r.severity for r, _, _ in fans] == ["warning"]

    def test_trigger_outlet_reconvergent_blocks(self):
        boxes = [
            _box("obj-1", text="t b b", numinlets=1, numoutlets=2,
                 outlettype=["bang", "bang"]),
            _plus("obj-9"),
        ]
        lines = [_ln("obj-1", 0, "obj-9", 0), _ln("obj-1", 0, "obj-9", 1)]
        fans = _fan(review_structure(_make_patch(boxes, lines)))
        assert [r.severity for r, _, _ in fans] == ["blocker"]

    def test_metro_counter_toggle_print_warns(self):
        from tests.test_critics import _fan_out_no_trigger_patch
        fans = _fan(review_structure(_fan_out_no_trigger_patch()))
        assert [r.severity for r, _, _ in fans] == ["warning"]

    def test_number_to_plus_both_inlets_blocks(self):
        boxes = [_number("obj-1"), _plus("obj-9")]
        lines = [_ln("obj-1", 0, "obj-9", 0), _ln("obj-1", 0, "obj-9", 1)]
        fans = _fan(review_structure(_make_patch(boxes, lines)))
        assert [r.severity for r, _, _ in fans] == ["blocker"]
        assert "'+' (obj-9)" in fans[0][0].finding.split("--", 1)[1]

    def test_two_hop_reconvergence_blocks(self):
        boxes = [
            _number("obj-1"),
            _box("obj-2", text="i", numinlets=2, numoutlets=1, outlettype=["int"]),
            _box("obj-3", maxclass="button", numinlets=1, numoutlets=1,
                 outlettype=["bang"]),
            _plus("obj-9"),
        ]
        lines = [
            _ln("obj-1", 0, "obj-2", 0),
            _ln("obj-1", 0, "obj-3", 0),
            _ln("obj-2", 0, "obj-9", 1),
            _ln("obj-3", 0, "obj-9", 0),
        ]
        fans = _fan_for(review_structure(_make_patch(boxes, lines)), "obj-1")
        assert [r.severity for r in fans] == ["blocker"]

    def test_same_inlet_meeting_warns(self):
        boxes = [
            _number("obj-1"),
            _box("obj-2", text="prepend a", numinlets=1, numoutlets=1),
            _box("obj-3", text="prepend b", numinlets=1, numoutlets=1),
            _box("obj-4", text="route a b", numinlets=1, numoutlets=3),
        ]
        lines = [
            _ln("obj-1", 0, "obj-2", 0),
            _ln("obj-1", 0, "obj-3", 0),
            _ln("obj-2", 0, "obj-4", 0),
            _ln("obj-3", 0, "obj-4", 0),
        ]
        fans = _fan_for(review_structure(_make_patch(boxes, lines)), "obj-1")
        assert [r.severity for r in fans] == ["warning"]

    def test_all_hot_meeting_warns(self):
        boxes = [
            _number("obj-1"),
            _box("obj-2", text="i", numinlets=2, numoutlets=1, outlettype=["int"]),
            _box("obj-5", text="js x.js", numinlets=2, numoutlets=1),
        ]
        lines = [
            _ln("obj-1", 0, "obj-5", 0),
            _ln("obj-1", 0, "obj-2", 0),
            _ln("obj-2", 0, "obj-5", 1),
        ]
        fans = _fan_for(review_structure(_make_patch(boxes, lines)), "obj-1")
        assert [r.severity for r in fans] == ["warning"]


# ===========================================================================
# E1: committed-patch repros (read-only)
# ===========================================================================

class TestFanOutCommittedPatches:

    def test_timestretch_preset_exclude_outlet(self):
        res = review_structure(_load("patches/timestretch/generated/timestretch.maxpat"))
        assert _fan_for(res, "obj-51", 2) == []

    def test_minitaur_zero_fan_blockers(self):
        res = review_structure(_load("patches/minitaur/generated/minitaur.maxpat"))
        blockers = [r for r, _, _ in _fan(res) if r.severity == "blocker"]
        assert blockers == [], [r.finding for r in blockers]

    def test_mixer_strip_plus_is_warning(self):
        res = review_structure(_load("patches/mixer/generated/mixer-strip.maxpat"))
        fans = _fan_for(res, "obj-14", 0)
        assert [r.severity for r in fans] == ["warning"]

    def test_slot_buffer_bang_reconverges_on_waveform(self):
        res = review_structure(_load("patches/rhythmic-sampler/generated/slot.maxpat"))
        fans = _fan_for(res, "obj-1", 1)
        assert [r.severity for r in fans] == ["blocker"]
        assert "'waveform~' (obj-4)" in fans[0].finding

    def test_calibration_shapes_are_warnings(self):
        cases = [
            ("patches/gong-model/generated/gong-model.maxpat", ["obj-335", "obj-349"]),
            ("patches/kicksynth/generated/kicksynth.maxpat", ["obj-129"]),
            ("patches/scala-synth/generated/scala-synth-voice.maxpat", ["obj-6"]),
            ("patches/scala-synth/generated/scala-synth.maxpat", ["obj-13", "obj-14"]),
        ]
        for rel, ids in cases:
            res = review_structure(_load(rel))
            for src_id in ids:
                fans = _fan_for(res, src_id)
                assert fans, f"{rel} {src_id}: expected a fan warning"
                assert all(r.severity == "warning" for r in fans), (
                    f"{rel} {src_id}: {[(r.severity, r.finding) for r in fans]}"
                )
