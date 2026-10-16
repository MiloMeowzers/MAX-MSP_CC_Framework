"""Critic-precision fixes for fix-plan Q26 (review findings E5-E8).

One test class per change:

* E8 -- RNBO critic: positional ``param`` names (TestRnboParamNames) and a
  missing in~ as a note (TestRnboMissingIn);
* E5 -- hot/cold ordering warns only on a shared upstream event that updates
  a cold inlet after the hot one (TestHotColdSharedAncestor);
* E6 -- gain safety: message parsing, value bounds, both ``*~`` inlets and
  DB-driven gain-stage / terminal sets (TestGainMessageParsing,
  TestGainBounds, TestGainBothInlets, TestDspRoles);
* E7 -- theme-aware text contrast in the critic and the generator
  (TestThemeAwareContrast, TestContrastGenerator).

Each class also carries robustness (junk values never raise) and purity (the
patch is unchanged by review) cases.
"""

from __future__ import annotations

import copy
import json

import pytest

from src.maxpat.critics import review_patch
from src.maxpat.critics.rnbo_critic import review_rnbo
from src.maxpat.db_lookup import ObjectDatabase
from tests.conftest import MAX_APP_PATH
from tests.test_critics_recursive import _box, _container, _inner, _line, _patch


@pytest.fixture(scope="module")
def db():
    return ObjectDatabase()


# ---------------------------------------------------------------------------
# E8 -- RNBO critic
# ---------------------------------------------------------------------------


def _rnbo(box_id, inner_boxes, inner_lines=None):
    return _container(box_id, "rnbo~", _inner(inner_boxes, inner_lines, classnamespace="rnbo"),
                      1, 1, outlettype=["signal"])


def _io():
    return [
        _box("obj-5", "in~ 1", 1, 1, outlettype=["signal"]),
        _box("obj-6", "out~ 1", 1, 0, outlettype=[]),
    ]


def _param(box_id, text):
    return _box(box_id, text, 1, 2, outlettype=["", ""])


class TestRnboParamNames:
    def test_positional_duplicate(self):
        r = _rnbo("obj-2", _io() + [_param("obj-10", "param freq 440"),
                                    _param("obj-11", "param freq 220")])
        results = review_rnbo(_patch([r]))
        dups = [x for x in results if x.finding.startswith("Duplicate RNBO param name 'freq'")]
        assert [x.severity for x in dups] == ["blocker"]
        assert len([x for x in results if "Duplicate" in x.finding]) == 1

    def test_mixed_name_and_positional_duplicate(self):
        r = _rnbo("obj-2", _io() + [_param("obj-10", "param @name gain"),
                                    _param("obj-11", "param gain 0.5")])
        results = review_rnbo(_patch([r]))
        dups = [x for x in results if x.finding.startswith("Duplicate RNBO param name 'gain'")]
        assert [x.severity for x in dups] == ["blocker"]

    def test_positional_naming_warning(self):
        r = _rnbo("obj-2", _io() + [_param("obj-10", "param MyGain 0")])
        results = review_rnbo(_patch([r]))
        naming = [x for x in results if "naming convention" in x.finding]
        assert [x.severity for x in naming] == ["warning"]
        assert naming[0].finding.startswith("RNBO param 'MyGain'")
        assert "my_gain" in naming[0].suggestion

    @pytest.mark.parametrize("text", ["param @min 0", "param 5", "param", "param @min 0 @max 1"])
    def test_no_name_no_finding(self, text):
        r = _rnbo("obj-2", _io() + [_param("obj-10", text), _param("obj-11", text)])
        results = review_rnbo(_patch([r]))
        assert results == []

    def test_name_attr_wins_over_positional(self):
        from src.maxpat.critics.rnbo_critic import _extract_param_name
        assert _extract_param_name("param foo @name bar") == "bar"
        assert _extract_param_name("param foo 0") == "foo"
        assert _extract_param_name("param -3") is None
        assert _extract_param_name("param 1e3") is None
        assert _extract_param_name(None) is None
        assert _extract_param_name(7) is None


_IN_NOTE = ("rnbo~ 'obj-2' inner patcher has no in~ object -- it takes no audio "
            "input, which is expected for a generator")
_IN_SUGGESTION = "If the patch should process audio input, add an 'in~ 1' object to the inner RNBO patcher"


class TestRnboMissingIn:
    def test_generator_is_note(self):
        r = _rnbo("obj-2", [_box("obj-6", "out~ 1", 1, 0, outlettype=[])])
        results = review_rnbo(_patch([r]))
        assert [(x.severity, x.finding, x.suggestion) for x in results] == [
            ("note", _IN_NOTE, _IN_SUGGESTION)
        ]

    def test_nested_note_path_and_prefix(self):
        r = _rnbo("obj-2", [_box("obj-6", "out~ 1", 1, 0, outlettype=[])])
        d = _patch([_container("obj-1", "p synth", _inner([r]))])
        results = review_rnbo(d)
        assert [(x.severity, x.path) for x in results] == [("note", "obj-1")]
        assert results[0].finding == "[p synth] " + _IN_NOTE

    def test_missing_out_still_blocker(self):
        r = _rnbo("obj-2", [_box("obj-5", "in~ 1", 1, 1, outlettype=["signal"])])
        results = review_rnbo(_patch([r]))
        assert [(x.severity, x.finding) for x in results] == [(
            "blocker",
            "rnbo~ 'obj-2' inner patcher has no out~ object -- audio output will not work",
        )]

    def test_review_patch_generator_no_rnbo_blocker(self, db):
        r = _rnbo("obj-2", [_box("obj-6", "out~ 1", 1, 0, outlettype=[])])
        results = review_patch(_patch([r]), db=db)
        rnbo = [x for x in results if x.finding.startswith("rnbo~ ")]
        assert [x.severity for x in rnbo] == ["note"]
        assert not [x for x in rnbo if x.severity == "blocker"]

    def test_junk_never_raises_and_pure(self):
        r = _rnbo("obj-2", [
            _box("obj-6", "out~ 1", 1, 0, outlettype=[]),
            {"box": {"id": "obj-7", "maxclass": "newobj", "text": 7}},
            {"box": {"id": "obj-9", "maxclass": "newobj", "text": ["param", "x"]}},
            _param("obj-8", "param \"a b\" 3"),
            {"box": 5},
            "junk",
        ])
        d = _patch([r])
        before = copy.deepcopy(d)
        review_rnbo(d)
        assert d == before

    @pytest.mark.requires_max
    def test_bundle_rnbo_triangle_help(self):
        p = MAX_APP_PATH / "Contents/Resources/C74/packages/RNBO/help/rnbo_triangle~.maxhelp"
        if not p.exists():
            pytest.skip(f"{p} not installed")
        d = json.loads(p.read_text(errors="replace"))
        results = review_rnbo(d)
        assert not [x for x in results if x.severity == "blocker" and "in~" in x.finding]


# ---------------------------------------------------------------------------
# E5 -- hot/cold ordering on a shared upstream event
# ---------------------------------------------------------------------------


_HC = "Hot/cold inlet ordering issue: "


def _structure(d, db):
    from src.maxpat.critics.structure_critic import review_structure
    return review_structure(d, db=db)


def _hc(results):
    return [r for r in results if _HC in r.finding]


def _number(box_id):
    return _box(box_id, None, 1, 2, maxclass="number", outlettype=["", "bang"])


def _reversed_unpack(target, target_id="obj-4", hot_outlet=1, cold_outlet=0):
    """number obj-2 -> unpack 0 0 obj-3; unpack *hot_outlet* -> target inlet 0,
    unpack *cold_outlet* -> target inlet 1."""
    boxes = [
        _number("obj-2"),
        _box("obj-3", "unpack 0 0", 1, 2, outlettype=["int", "int"]),
        target,
    ]
    lines = [
        _line("obj-2", 0, "obj-3", 0),
        _line("obj-3", hot_outlet, target_id, 0),
        _line("obj-3", cold_outlet, target_id, 1),
    ]
    return boxes, lines


def _plus(box_id="obj-4", text="+"):
    return _box(box_id, text, 2, 1, outlettype=["int"])


class TestHotColdSharedAncestor:
    def test_reversed_order_warns_once(self, db):
        boxes, lines = _reversed_unpack(_plus())
        hc = _hc(_structure(_patch(boxes, lines), db))
        assert [(r.severity, r.finding, r.suggestion) for r in hc] == [(
            "warning",
            "Hot/cold inlet ordering issue: '+' (obj-4) gets hot inlet 0 and cold "
            "inlet(s) 1 from one event at 'unpack 0 0' (obj-3), but outlet 0 (cold) "
            "fires after outlet 1 (hot) -- '+' outputs with a stale cold value",
            "Feed both from one 'trigger' (t) with the hot inlet on its lowest "
            "outlet: trigger outlets fire right to left, so the cold inlets are set first.",
        )]

    def test_swapped_cords_clean(self, db):
        boxes, lines = _reversed_unpack(_plus(), hot_outlet=0, cold_outlet=1)
        assert _hc(_structure(_patch(boxes, lines), db)) == []

    def test_independent_sources_clean(self, db):
        boxes = [_number("obj-2"), _number("obj-3"), _plus()]
        lines = [_line("obj-2", 0, "obj-4", 0), _line("obj-3", 0, "obj-4", 1)]
        assert _hc(_structure(_patch(boxes, lines), db)) == []

    def test_same_outlet_fanout(self, db):
        boxes = [
            _box("obj-2", "button", 1, 1, maxclass="button", outlettype=["bang"]),
            _box("obj-3", "pack 0 0", 2, 1, outlettype=["list"]),
        ]
        lines = [_line("obj-2", 0, "obj-3", 0), _line("obj-2", 0, "obj-3", 1)]
        results = _structure(_patch(boxes, lines), db)
        hc = _hc(results)
        assert [r.finding for r in hc] == [
            "Hot/cold inlet ordering issue: 'pack' (obj-3) gets hot inlet 0 and "
            "cold inlet(s) 1 from one event at 'button' (obj-2) outlet 0, which fans "
            "out to both in undefined order -- 'pack' may output with a stale cold value"
        ]
        assert [r.severity for r in results if r.finding.startswith("Fan-out without trigger")] == ["blocker"]

    @pytest.mark.parametrize("target", [
        _container("obj-4", "p x", _inner([
            _box("obj-20", None, 1, 1, maxclass="inlet"),
            _box("obj-21", None, 1, 1, maxclass="inlet"),
        ]), 2, 1),
        _container("obj-4", None, _inner(), 2, 1, maxclass="bpatcher"),
        _box("obj-4", "js foo.js", 2, 1),
        _box("obj-4", "gate 2", 2, 2),
        _box("obj-4", "pak 0 0", 2, 1),
        _box("obj-4", "i", 2, 1),
    ], ids=["p", "bpatcher", "js", "gate", "pak", "i"])
    def test_skipped_targets(self, db, target):
        boxes, lines = _reversed_unpack(target)
        assert _hc(_structure(_patch(boxes, lines), db)) == []

    def test_exclusive_router_divergence_clean(self, db):
        boxes = [
            _number("obj-2"),
            _box("obj-3", "route a b", 2, 3, outlettype=["", "", ""]),
            _plus(),
        ]
        lines = [
            _line("obj-2", 0, "obj-3", 0),
            _line("obj-3", 1, "obj-4", 0),
            _line("obj-3", 0, "obj-4", 1),
        ]
        assert _hc(_structure(_patch(boxes, lines), db)) == []

    @pytest.mark.parametrize("target_text", ["int", "+"])
    def test_cold_inlet_stops_walk(self, db, target_text):
        boxes = [
            _box("obj-2", "notein", 1, 3, outlettype=["int", "int", "int"]),
            _box("obj-3", "poly 4", 2, 4, outlettype=["int", "int", "int", "int"]),
            _box("obj-4", target_text, 2, 1, outlettype=["int"]),
        ]
        lines = [
            _line("obj-2", 0, "obj-3", 0),
            _line("obj-2", 1, "obj-3", 1),
            _line("obj-3", 1, "obj-4", 1),
            _line("obj-3", 0, "obj-4", 0),
        ]
        assert _hc(_structure(_patch(boxes, lines), db)) == []

    def test_jitter_setter_hop_stops_walk(self, db):
        boxes = [
            _box("obj-10", "loadbang", 1, 1, outlettype=["bang"]),
            _box("obj-11", "exprfill 0 snorm[0]", 2, 1, maxclass="message", outlettype=[""]),
            _box("obj-12", "exprfill 0 snorm[1]", 2, 1, maxclass="message", outlettype=[""]),
            _box("obj-13", "jit.matrix 1 float32 64 64", 1, 2, outlettype=["jit_matrix", ""]),
            _box("obj-14", "jit.matrix 1 float32 64 64", 1, 2, outlettype=["jit_matrix", ""]),
            _box("obj-19", "jit.pack 3", 3, 2, outlettype=["jit_matrix", ""]),
        ]
        lines = [
            _line("obj-10", 0, "obj-11", 0),
            _line("obj-10", 0, "obj-12", 0),
            _line("obj-11", 0, "obj-13", 0),
            _line("obj-12", 0, "obj-14", 0),
            _line("obj-13", 0, "obj-19", 0),
            _line("obj-14", 0, "obj-19", 1),
        ]
        assert _hc(_structure(_patch(boxes, lines), db)) == []

    def test_deep_reversed_order_outside_q21_reach(self, db):
        boxes = [
            _box("obj-2", "t i i", 1, 2, outlettype=["int", "int"]),
            _box("obj-3", "+ 1", 2, 1, outlettype=["int"]),
            _box("obj-4", "-", 2, 1, outlettype=["int"]),
        ]
        lines = [
            _line("obj-2", 1, "obj-3", 0),
            _line("obj-3", 0, "obj-4", 0),
            _line("obj-2", 0, "obj-4", 1),
        ]
        results = _structure(_patch(boxes, lines), db)
        hc = _hc(results)
        assert len(hc) == 1
        assert hc[0].finding.startswith(
            "Hot/cold inlet ordering issue: '-' (obj-4) gets hot inlet 0 and cold "
            "inlet(s) 1 from one event at 't i i' (obj-2), but outlet 0 (cold) fires "
            "after outlet 1 (hot)"
        )
        assert not [r for r in results if r.finding.startswith("Trigger order: ")]

    def test_q21_boundary_trigger_order_only(self, db):
        boxes = [_box("obj-2", "t i b", 1, 2, outlettype=["int", "bang"]), _plus()]
        lines = [_line("obj-2", 1, "obj-4", 0), _line("obj-2", 0, "obj-4", 1)]
        results = _structure(_patch(boxes, lines), db)
        assert _hc(results) == []
        assert [r.severity for r in results if r.finding.startswith("Trigger order: ")] == ["blocker"]

    def test_q21_idiom_gives_neither(self, db):
        boxes = [_box("obj-2", "t f f", 1, 2, outlettype=["float", "float"]),
                 _box("obj-4", "- 0.", 2, 1, outlettype=["float"])]
        lines = [_line("obj-2", 1, "obj-4", 0), _line("obj-2", 0, "obj-4", 1)]
        results = _structure(_patch(boxes, lines), db)
        assert _hc(results) == []
        assert not [r for r in results if r.finding.startswith("Trigger order: ")]

    def _ears(self):
        return _box("obj-4", "ears.slice~", 2, 2, outlettype=["signal", ""])

    def test_msp_control_inlets_one_hop_reported_by_q21_only(self, db):
        boxes = [_box("obj-2", "t l b", 1, 2, outlettype=["", "bang"]), self._ears()]
        lines = [_line("obj-2", 1, "obj-4", 0), _line("obj-2", 0, "obj-4", 1)]
        results = _structure(_patch(boxes, lines), db)
        assert _hc(results) == []
        assert len([r for r in results if r.finding.startswith("Trigger order: ")]) == 1

    def test_msp_control_inlets_two_hops_reported_by_hot_cold(self, db):
        boxes = [
            _box("obj-2", "t l b", 1, 2, outlettype=["", "bang"]),
            _box("obj-5", "prepend set", 1, 1, outlettype=[""]),
            _box("obj-6", "prepend foo", 1, 1, outlettype=[""]),
            self._ears(),
        ]
        lines = [
            _line("obj-2", 1, "obj-4", 0),
            _line("obj-2", 0, "obj-5", 0),
            _line("obj-5", 0, "obj-6", 0),
            _line("obj-6", 0, "obj-4", 1),
        ]
        results = _structure(_patch(boxes, lines), db)
        assert len(_hc(results)) == 1
        assert not [r for r in results if r.finding.startswith("Trigger order: ")]

    def test_signal_cords_never_count(self, db):
        boxes = [
            _box("obj-2", "cycle~ 440", 2, 1, outlettype=["signal"]),
            _box("obj-3", "unpack 0 0", 1, 2, outlettype=["int", "int"]),
            _number("obj-5"),
            _box("obj-4", "ears.slice~", 2, 2, outlettype=["signal", ""]),
        ]
        lines = [
            _line("obj-5", 0, "obj-3", 0),
            _line("obj-2", 0, "obj-4", 0),
            _line("obj-3", 0, "obj-4", 1),
        ]
        assert _hc(_structure(_patch(boxes, lines), db)) == []

    def test_nested_path_and_prefix(self, db):
        boxes, lines = _reversed_unpack(_plus())
        d = _patch([_container("obj-1", "p a", _inner(boxes, lines))])
        hc = _hc(_structure(d, db))
        assert [r.path for r in hc] == ["obj-1"]
        assert hc[0].finding.startswith("[p a] Hot/cold inlet ordering issue: '+' (obj-4)")

    def test_junk_never_raises_and_pure(self, db):
        boxes, lines = _reversed_unpack(_plus())
        boxes += [
            {"box": {"id": "obj-30", "maxclass": "newobj", "text": 7}},
            {"box": {"id": "obj-31", "maxclass": "newobj", "text": "nosuchobject 1 2"}},
            {"box": {"id": "obj-32", "maxclass": 5}},
            {"box": 3},
        ]
        lines += [
            _line("obj-2", 0, "obj-31", 0),
            _line("obj-30", 0, "obj-31", 1),
            _line("obj-2", "x", "obj-31", 1),
            _line("obj-2", 0, "obj-99", 0),
            _line("obj-99", 0, "obj-4", 1),
            _line("obj-32", 0, "obj-4", 0),
            {"patchline": {"source": None, "destination": ["obj-4", 0]}},
        ]
        d = _patch(boxes, lines)
        before = copy.deepcopy(d)
        _structure(d, db)
        assert d == before
