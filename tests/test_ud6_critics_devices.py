"""Device / layout / package critic fixes (quick 261022-ud6 WP3): WR-02 M4L
helper abstraction, IN-01 malformed rects, IN-04 bach @out per outlet,
Q26 follow-up MIDI-only RNBO patch.
"""

from __future__ import annotations

import pytest

from src.maxpat.critics import review_patch
from src.maxpat.db_lookup import ObjectDatabase
from tests.test_critics_recursive import _box, _container, _inner, _line, _patch


@pytest.fixture(scope="module")
def db():
    return ObjectDatabase()


def _rule(results, rule, severity=None):
    return [r for r in results if r.rule == rule and (severity is None or r.severity == severity)]


def _blockers(results):
    return [r for r in results if r.severity == "blocker"]


def _sig_box(box_id, text, n_in=2, n_out=1):
    return _box(box_id, text, n_in, n_out, outlettype=["signal"] * n_out)


def _msg(box_id, text):
    return _box(box_id, text, 2, 1, maxclass="message", outlettype=[""])


def _dac(box_id="obj-99"):
    return _box(box_id, "dac~", 2, 0, outlettype=[])


# ---------------------------------------------------------------------------
# WR-02 -- live.thisdevice helper abstraction
# ---------------------------------------------------------------------------


class TestM4LAbstraction:
    def _helper(self):
        boxes = [
            _box("obj-1", "inlet", 0, 1, maxclass="inlet", outlettype=[""]),
            _box("obj-2", "live.thisdevice", 1, 3, outlettype=["bang", "int", "int"]),
            _box("obj-3", "t b", 1, 1, outlettype=["bang"]),
            _box("obj-4", "outlet", 1, 0, maxclass="outlet", outlettype=[]),
        ]
        lines = [_line("obj-2", 0, "obj-3", 0), _line("obj-3", 0, "obj-4", 0)]
        return _patch(boxes, lines)

    def test_detected_as_abstraction(self):
        from src.maxpat.critics.m4l_critic import detect_m4l_device_type
        assert detect_m4l_device_type(self._helper()) == "m4l_abstraction"

    def test_no_completeness_or_quality(self, db):
        results = review_patch(self._helper(), db=db, is_new=True)
        assert _rule(results, "device_completeness") == []
        assert _rule(results, "device_quality") == []
        assert _blockers(results) == []

    def test_midiin_still_midi_effect(self):
        from src.maxpat.critics.m4l_critic import detect_m4l_device_type
        d = self._helper()
        d["patcher"]["boxes"].append(_box("obj-5", "midiin", 1, 1, outlettype=["int"]))
        assert detect_m4l_device_type(d) == "midi_effect"

    def test_abstraction_keeps_per_scope_checks(self, db):
        d = self._helper()
        d["patcher"]["boxes"].append(_box("obj-6", "ezdac~", 2, 0, maxclass="ezdac~", outlettype=[]))
        assert len(_rule(review_patch(d, db=db), "gain_plugout")) == 1

    def test_export_refuses_abstraction(self, tmp_path):
        from src.maxpat.m4l_device import export_amxd
        with pytest.raises(ValueError):
            export_amxd(self._helper(), tmp_path / "helper.amxd")


# ---------------------------------------------------------------------------
# IN-01 -- malformed patching_rect never crashes the layout critic
# ---------------------------------------------------------------------------


class TestLayoutMalformedRect:
    @pytest.mark.parametrize("rect", [5, ["a", "b", "c", "d"], [1, 2], None, [True, 0, 0, 0]])
    def test_no_crash(self, db, rect):
        a = _box("obj-1", "loadbang", 1, 1, outlettype=["bang"])
        b = _box("obj-2", "print", 1, 0, outlettype=[])
        a["box"]["patching_rect"] = rect
        b["box"]["patching_rect"] = [600.0, 600.0, 50.0, 22.0]
        d = _patch([a, b], [_line("obj-1", 0, "obj-2", 0)])
        review_patch(d, db=db)
        b["box"]["patching_rect"] = rect
        a["box"]["patching_rect"] = [600.0, 600.0, 50.0, 22.0]
        review_patch(d, db=db)

    def test_bad_port_count_no_crash(self, db):
        a = _box("obj-1", "loadbang", 1, "x", outlettype=["bang"])
        b = _box("obj-2", "print", None, 0, outlettype=[])
        b["box"]["patching_rect"] = [600.0, 600.0, 50.0, 22.0]
        review_patch(_patch([a, b], [_line("obj-1", 0, "obj-2", 0)]), db=db)


# ---------------------------------------------------------------------------
# IN-04 -- @out letters map to llll outlets
# ---------------------------------------------------------------------------


class TestBachOutPerOutlet:
    def _slice(self, out_attr, outlet, db):
        text = "bach.slice 2" + (f" @out {out_attr}" if out_attr else "")
        boxes = [
            _box("obj-1", text, 2, 2, outlettype=["", ""]),
            _box("obj-2", "print", 1, 0, outlettype=[]),
        ]
        d = _patch(boxes, [_line("obj-1", outlet, "obj-2", 0)])
        return _rule(review_patch(d, db=db), "bach_out_mode")

    def test_text_outlet_not_flagged(self, db):
        assert self._slice("tn", 0, db) == []

    def test_native_outlet_flagged(self, db):
        found = self._slice("tn", 1, db)
        assert len(found) == 1 and found[0].port == 1

    def test_max_mode_and_disabled_readable(self, db):
        assert self._slice("mx", 0, db) == []
        assert self._slice("mx", 1, db) == []

    def test_short_value_covers_later_outlets(self, db):
        assert self._slice("t", 1, db) == []

    def test_default_native_flagged(self, db):
        assert len(self._slice(None, 0, db)) == 1


# ---------------------------------------------------------------------------
# Q26 follow-up -- MIDI-only RNBO patch
# ---------------------------------------------------------------------------


def _rnbo(inner_boxes):
    return _container("obj-1", "rnbo~", _inner(inner_boxes, [], classnamespace="rnbo"),
                      1, 1, outlettype=[""])


class TestRnboEventOnly:
    @pytest.mark.parametrize("text", ["midiout", "noteout", "outport notes", "out 1"])
    def test_event_output_not_blocker(self, db, text):
        d = _patch([_rnbo([_box("r-1", "notein", 1, 3, outlettype=["", "", ""]),
                           _box("r-2", text, 1, 0, outlettype=[])])])
        io = _rule(review_patch(d, db=db), "io_completeness")
        assert [r.severity for r in io if "out~" in r.finding] == ["note"]

    def test_no_output_at_all_still_blocks(self, db):
        d = _patch([_rnbo([_box("r-1", "cycle~ 440", 2, 1, outlettype=["signal"])])])
        io = _rule(review_patch(d, db=db), "io_completeness", "blocker")
        assert len(io) == 1
