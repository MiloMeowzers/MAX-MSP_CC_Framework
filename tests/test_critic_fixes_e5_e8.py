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
        # One defect, one finding (quick 261022-ud6 IN-02): the fan-out check
        # owns a single outlet feeding both sides; hot/cold no longer repeats it.
        assert _hc(results) == []
        assert [r.severity for r in results if r.finding.startswith("Fan-out without trigger")] == ["blocker"]

    def test_same_outlet_through_a_hop_still_warns(self, db):
        """The fan-out check does not own a fan-out it never sees: button ->
        t b (one cord) whose single outlet feeds both pack inlets is still a
        fan-out at the trigger -- reported there; the hot/cold check names the
        divergence box only when no fan-out finding covers it."""
        boxes = [
            _box("obj-2", "button", 1, 1, maxclass="button", outlettype=["bang"]),
            _box("obj-3", "pack 0 0", 2, 1, outlettype=["list"]),
            _box("obj-5", "unpack 0 0", 1, 2, outlettype=["int", "int"]),
        ]
        lines = [
            _line("obj-2", 0, "obj-5", 0),
            _line("obj-5", 0, "obj-3", 0), _line("obj-5", 0, "obj-3", 1),
        ]
        results = _structure(_patch(boxes, lines), db)
        assert _hc(results) == []
        fans = [r for r in results if r.finding.startswith("Fan-out without trigger")]
        assert [r.severity for r in fans] == ["blocker"] and fans[0].box_ids[0] == "obj-5"

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


# ---------------------------------------------------------------------------
# E6 -- gain safety and DB-driven DSP roles
# ---------------------------------------------------------------------------


_UG = "Unsafe gain source: "


def _dsp(d, db=None):
    from src.maxpat.critics.dsp_critic import review_dsp
    return review_dsp(d, db=db)


def _ug(results):
    return [r for r in results if _UG in r.finding]


def _mul(box_id="obj-9", text="*~", name=None):
    return _box(box_id, text, 2, 1, outlettype=["signal"])


def _line_tilde(box_id="obj-8"):
    return _box(box_id, "line~", 2, 2, outlettype=["signal", "bang"])


def _msg(box_id, text):
    return _box(box_id, text, 2, 1, maxclass="message", outlettype=[""])


def _ctlin(box_id="obj-1"):
    return _box(box_id, "ctlin", 1, 3, outlettype=["int", "int", "int"])


def _osc(box_id="obj-7"):
    return _box(box_id, "cycle~ 440", 2, 1, outlettype=["signal"])


def _msg_line_gain(text, feeders=(), feeder_lines=()):
    """message obj-2 -> line~ obj-8 -> *~ obj-9 inlet 1 (cycle~ obj-7 on inlet 0)."""
    boxes = [_msg("obj-2", text), _line_tilde(), _mul(), _osc()] + list(feeders)
    lines = [
        _line("obj-2", 0, "obj-8", 0),
        _line("obj-8", 0, "obj-9", 1),
        _line("obj-7", 0, "obj-9", 0),
    ] + list(feeder_lines)
    return _patch(boxes, lines)


def _chain_gain(*middle, source=None):
    """source obj-1 -> middle boxes obj-2.. -> *~ obj-9 inlet 1 (cycle~ on inlet 0)."""
    source = source if source is not None else _ctlin()
    boxes = [source]
    ids = ["obj-1"]
    for n, text in enumerate(middle, start=2):
        boxes.append(_box(f"obj-{n}", text, 2, 1, outlettype=[""]))
        ids.append(f"obj-{n}")
    boxes += [_mul(), _osc()]
    lines = [_line(a, 0, b, 0) for a, b in zip(ids, ids[1:])]
    lines += [_line(ids[-1], 0, "obj-9", 1), _line("obj-7", 0, "obj-9", 0)]
    return _patch(boxes, lines)


class TestGainMessageParsing:
    def test_comma_segments_ramp_times_ignored(self, db):
        assert _ug(_dsp(_msg_line_gain("0, 0.8 2000"), db)) == []

    def test_comma_segment_target_over_one(self, db):
        ug = _ug(_dsp(_msg_line_gain("0.5, 100 500"), db))
        assert [r.finding for r in ug] == [
            "Unsafe gain source: message '0.5, 100 500' (obj-2) reaches '*~' (obj-9) "
            "inlet 1 via line~ with values up to 100 (range 0.5 to 100) -- gain "
            "inputs must stay within 0.0-1.0"
        ]
        assert ug[0].severity == "blocker"
        assert ug[0].suggestion == (
            "Normalize before the gain input, e.g. 'scale 0 127 0. 1.' or '/ 127.' "
            "for a 0-127 int source ('scale 0. 127. 0. 1.' for a float source: "
            "all-int arguments make scale truncate floats), so the value stays within 0.0-1.0"
        )

    def test_dollar_continues_to_feeder(self, db):
        d = _msg_line_gain("$1 20", [_ctlin("obj-1")], [_line("obj-1", 0, "obj-2", 0)])
        ug = _ug(_dsp(d, db))
        assert len(ug) == 1
        assert ug[0].finding.startswith("Unsafe gain source: 'ctlin' (obj-1) reaches '*~' (obj-9) inlet 1 via line~")
        assert "(range 0 to 127)" in ug[0].finding

    def test_pack_fed_ramp_message_stops(self, db):
        feeders = [
            _box("obj-1", None, 1, 1, maxclass="dial", outlettype=["float"]),
            _box("obj-3", "pack f f f", 3, 1, outlettype=[""]),
        ]
        d = _msg_line_gain("$1 $2 0. $3", feeders,
                           [_line("obj-1", 0, "obj-3", 1), _line("obj-3", 0, "obj-2", 0)])
        assert _ug(_dsp(d, db)) == []

    def test_constant_through_multiply_safe(self, db):
        d = _chain_gain("* 0.01", source=_msg("obj-1", "64"))
        assert _ug(_dsp(d, db)) == []

    def test_constant_through_multiply_unsafe_no_via(self, db):
        d = _chain_gain("* 0.01", source=_msg("obj-1", "200"))
        ug = _ug(_dsp(d, db))
        assert len(ug) == 1
        assert "via line~" not in ug[0].finding
        assert ug[0].finding.startswith("Unsafe gain source: message '200' (obj-1) reaches '*~' (obj-9) inlet 1 with values up to 2 ")

    def test_command_message_no_value(self, db):
        assert _ug(_dsp(_chain_gain(source=_msg("obj-1", "set 5")), db)) == []

    def test_remote_part_ignored(self, db):
        assert _ug(_dsp(_chain_gain(source=_msg("obj-1", "; foo 100")), db)) == []
        assert _ug(_dsp(_chain_gain(source=_msg("obj-1", "0.5; foo 100")), db)) == []


def _flonum(**attrs):
    return _box("obj-1", None, 1, 2, maxclass="flonum", outlettype=["", "bang"], **attrs)


class TestGainBounds:
    def test_flonum_zero_one_safe(self, db):
        assert _ug(_dsp(_chain_gain(source=_flonum(minimum=0.0, maximum=1.0)), db)) == []

    def test_flonum_max_one_only_safe(self, db):
        assert _ug(_dsp(_chain_gain(source=_flonum(maximum=1.0)), db)) == []

    def test_number_no_limits_unsafe(self, db):
        src = _box("obj-1", None, 1, 2, maxclass="number", outlettype=["", "bang"])
        ug = _ug(_dsp(_chain_gain(source=src), db))
        assert len(ug) == 1
        assert "(range 0 to 127)" in ug[0].finding

    def test_scale_to_unit_safe(self, db):
        assert _ug(_dsp(_chain_gain("scale 0 127 0. 1."), db)) == []

    def test_scale_to_four_unsafe(self, db):
        ug = _ug(_dsp(_chain_gain("scale 0 127 0. 4."), db))
        assert len(ug) == 1
        assert "(range 0 to 4)" in ug[0].finding

    def test_zmap_to_two_unsafe(self, db):
        assert len(_ug(_dsp(_chain_gain("zmap 0 127 0. 2."), db))) == 1

    def test_clip_safe(self, db):
        assert _ug(_dsp(_chain_gain("clip 0. 0.5"), db)) == []

    def test_divide_safe(self, db):
        assert _ug(_dsp(_chain_gain("/ 127."), db)) == []

    def _live_dial(self, valueof):
        extra = {} if valueof is None else {"saved_attribute_attributes": {"valueof": valueof}}
        return _box("obj-1", None, 1, 2, maxclass="live.dial", outlettype=["", "float"], **extra)

    def test_live_dial_unit_range_safe(self, db):
        src = self._live_dial({"parameter_mmin": 0.0, "parameter_mmax": 1.0})
        assert _ug(_dsp(_chain_gain(source=src), db)) == []

    def test_live_dial_default_range_unsafe(self, db):
        assert len(_ug(_dsp(_chain_gain(source=self._live_dial(None)), db))) == 1

    def test_float_dial_size_121_mult_001(self, db):
        src = _box("obj-1", None, 1, 1, maxclass="dial", outlettype=["float"],
                   floatoutput=1, size=121.0, mult=0.01)
        ug = _ug(_dsp(_chain_gain(source=src), db))
        assert len(ug) == 1
        assert "with values up to 1.21 (range 0 to 1.21)" in ug[0].finding

    def test_trigger_bang_outlet_stops(self, db):
        boxes = [_ctlin(), _box("obj-2", "t b f", 1, 2, outlettype=["bang", "float"]), _mul(), _osc()]
        lines = [_line("obj-1", 0, "obj-2", 0), _line("obj-2", 0, "obj-9", 1), _line("obj-7", 0, "obj-9", 0)]
        assert _ug(_dsp(_patch(boxes, lines), db)) == []

    def test_trigger_value_outlet_passes(self, db):
        assert len(_ug(_dsp(_chain_gain("t f"), db))) == 1

    def test_unknown_box_stops(self, db):
        assert _ug(_dsp(_chain_gain("dbtoa"), db)) == []
        assert _ug(_dsp(_chain_gain("scale 0 127 -20. 20.", "dbtoa"), db)) == []


class TestGainBothInlets:
    def test_control_into_inlet_0(self, db):
        boxes = [_ctlin(), _mul(), _osc()]
        lines = [_line("obj-1", 0, "obj-9", 0), _line("obj-7", 0, "obj-9", 1)]
        ug = _ug(_dsp(_patch(boxes, lines), db))
        assert len(ug) == 1
        assert "reaches '*~' (obj-9) inlet 0 " in ug[0].finding

    def test_line_into_inlet_0_with_unit_arg(self, db):
        """``line~ -> *~ 1.`` (inlet 1 empty) is arithmetic, not a gain stage
        (quick 261022-ud6 CR-01); it is judged where it reaches a real gain."""
        boxes = [_msg("obj-2", "100 500"), _line_tilde(), _mul(text="*~ 1.")]
        lines = [_line("obj-2", 0, "obj-8", 0), _line("obj-8", 0, "obj-9", 0)]
        assert _ug(_dsp(_patch(boxes, lines), db)) == []
        boxes += [_mul("obj-10", "*~"), _osc()]
        lines += [_line("obj-9", 0, "obj-10", 1), _line("obj-7", 0, "obj-10", 0)]
        ug = _ug(_dsp(_patch(boxes, lines), db))
        assert len(ug) == 1
        assert "reaches '*~' (obj-10) inlet 1 via line~" in ug[0].finding

    def test_line_into_inlet_0_scaled_by_arg_safe(self, db):
        boxes = [_msg("obj-2", "100"), _line_tilde(), _mul(text="*~ 0.01")]
        lines = [_line("obj-2", 0, "obj-8", 0), _line("obj-8", 0, "obj-9", 0)]
        assert _ug(_dsp(_patch(boxes, lines), db)) == []

    def test_mc_multiply_same_as_multiply(self, db):
        boxes = [_ctlin(), _box("obj-9", "mc.*~", 2, 1, outlettype=["multichannelsignal"]),
                 _box("obj-7", "mc.cycle~ 440", 2, 1, outlettype=["multichannelsignal"])]
        lines = [_line("obj-1", 0, "obj-9", 0), _line("obj-7", 0, "obj-9", 1)]
        ug = _ug(_dsp(_patch(boxes, lines), db))
        assert len(ug) == 1
        assert "reaches 'mc.*~' (obj-9) inlet 0" in ug[0].finding
        d = _chain_gain("scale 0 127 0. 4.")
        d["patcher"]["boxes"][2]["box"]["text"] = "mc.*~"
        assert len(_ug(_dsp(d, db))) == 1

    def test_junk_never_raises_and_pure(self, db):
        boxes = [
            _box("obj-1", None, 1, 1, maxclass="dial", outlettype=["float"], size="x",
                 saved_attribute_attributes=5),
            _box("obj-2", None, 1, 1, maxclass="live.dial", outlettype=["", ""],
                 saved_attribute_attributes={"valueof": 3}),
            {"box": {"id": "obj-3", "maxclass": "message", "text": 7, "outlettype": [""]}},
            _box("obj-4", "scale 0 127", 2, 1, outlettype=[""]),
            _box("obj-5", "* 2", 2, 1, outlettype=[""]),
            _box("obj-6", "* 2", 2, 1, outlettype=[""]),
            _mul(),
            _box("obj-10", "flonum", 1, 2, maxclass="flonum", outlettype=["", ""],
                 minimum="lo", maximum=True),
        ]
        lines = [
            _line("obj-1", 0, "obj-9", 1),
            _line("obj-2", 0, "obj-9", 1),
            _line("obj-3", 0, "obj-9", 1),
            _line("obj-4", 0, "obj-9", 1),
            _line("obj-5", 0, "obj-6", 0),
            _line("obj-6", 0, "obj-5", 0),
            _line("obj-6", 0, "obj-9", 1),
            _line("obj-10", 0, "obj-9", 0),
            _line("obj-1", "x", "obj-9", 1),
            _line("obj-99", 0, "obj-9", 1),
            _line("obj-1", 0, "obj-98", 1),
            _line("obj-1", -3, "obj-9", 1),
        ]
        d = _patch(boxes, lines)
        before = copy.deepcopy(d)
        _dsp(d, db)
        assert d == before


_GAIN_STAGES = frozenset({"*~", "mc.*~", "gain~", "mc.gain~", "live.gain~", "mc.live.gain~"})
_OUTPUTS = frozenset({"dac~", "mc.dac~", "ezdac~", "mc.ezdac~", "plugout~"})
_CHAIN_TERMINALS = _OUTPUTS | {"send~", "mc.send~", "out~", "mc.out~"}


class _NoMcLiveGain:
    """A DB double whose lookup has no mc.live.gain~."""

    def __init__(self, db):
        self._db = db

    def lookup(self, name):
        return None if name == "mc.live.gain~" else self._db.lookup(name)

    def get_effective_restrictions(self, name):
        return self._db.get_effective_restrictions(name)


def _osc_to(dst_text, n_in=2, db=None):
    boxes = [_osc("obj-1"), _box("obj-2", dst_text, n_in, 0, outlettype=[])]
    return _patch(boxes, [_line("obj-1", 0, "obj-2", 0)])


class TestDspRoles:
    def test_sets_under_repo_db(self, db):
        from src.maxpat import dsp_roles
        assert dsp_roles.gain_stage_names(db) == _GAIN_STAGES
        assert dsp_roles.output_terminal_names(db) == _OUTPUTS
        assert dsp_roles.chain_terminal_names(db) == _CHAIN_TERMINALS
        assert dsp_roles.gain_stage_names() == _GAIN_STAGES

    def test_db_double_drops_missing_variant(self, db):
        from src.maxpat import dsp_roles
        assert dsp_roles.gain_stage_names(_NoMcLiveGain(db)) == _GAIN_STAGES - {"mc.live.gain~"}

    def test_back_compat_exports_pinned(self, db):
        from src.maxpat import dsp_roles
        from src.maxpat.critics.dsp_critic import _GAIN_NAMES, _TERMINAL_NAMES
        assert _GAIN_NAMES == dsp_roles.gain_stage_names(db)
        assert _TERMINAL_NAMES == dsp_roles.output_terminal_names(db)

    def test_live_gain_is_a_gain_stage(self, db):
        boxes = [_osc("obj-1"), _box("obj-2", "live.gain~", 2, 5, outlettype=["signal", "signal", "", "", ""]),
                 _box("obj-3", "dac~", 2, 0, outlettype=[])]
        lines = [_line("obj-1", 0, "obj-2", 0), _line("obj-2", 0, "obj-3", 0)]
        assert not [r for r in _dsp(_patch(boxes, lines), db) if "Missing gain staging" in r.finding]

    def test_mc_dac_is_output(self, db):
        found = [r for r in _dsp(_osc_to("mc.dac~"), db) if "Missing gain staging" in r.finding]
        assert len(found) == 1

    def test_plugout_is_output_suggests_multiply_only(self, db):
        found = [r for r in _dsp(_osc_to("plugout~"), db) if "Missing gain staging" in r.finding]
        assert len(found) == 1
        assert "*~" in found[0].suggestion
        assert "gain~" not in found[0].suggestion

    def test_m4l_gen_synth_not_unterminated(self, db):
        from src.maxpat.patcher import Patcher
        from src.maxpat.validation import validate_patch
        p = Patcher()
        p.add_m4l_gen_synth([("freq", 100.0, 1000.0), ("amp", 0.0, 1.0)])
        res = validate_patch(p.to_dict(), db)
        assert not [r for r in res if "Unterminated signal chain" in r.message]

    def test_validation_uses_monkeypatchable_roles(self, db, monkeypatch):
        from src.maxpat import dsp_roles
        from src.maxpat.validation import validate_patch
        d = _patch([_box("obj-1", "adc~", 1, 2, outlettype=["signal", "signal"])])
        before = [r for r in validate_patch(copy.deepcopy(d), db) if "Unterminated signal chain" in r.message]
        assert len(before) == 1
        real = dsp_roles.chain_terminal_names
        monkeypatch.setattr(dsp_roles, "chain_terminal_names", lambda db=None: real(db) | {"adc~"})
        after = [r for r in validate_patch(copy.deepcopy(d), db) if "Unterminated signal chain" in r.message]
        assert after == []


# ---------------------------------------------------------------------------
# E7 -- theme-aware text contrast
# ---------------------------------------------------------------------------


_LC = "Low contrast text: "
_DARK = [0.20, 0.20, 0.25, 1.0]


def _layout(d):
    from src.maxpat.critics.layout_critic import review_layout
    return review_layout(d)


def _lc(results, severity="warning"):
    return [r for r in results if _LC in r.finding and r.severity == severity]


def _comment(box_id="obj-1", text="label", rect=(50.0, 50.0, 100.0, 20.0), **extra):
    return {"box": dict({
        "id": box_id, "maxclass": "comment", "text": text,
        "patching_rect": list(rect), "numinlets": 1, "numoutlets": 0,
    }, **extra)}


def _panel_box(box_id, rect=(0.0, 0.0, 400.0, 400.0), **extra):
    return {"box": dict({
        "id": box_id, "maxclass": "panel", "patching_rect": None if rect is None else list(rect),
        "numinlets": 1, "numoutlets": 0,
    }, **extra)}


def _gray(v, a=1.0):
    return [v, v, v, a]


class TestThemeAwareContrast:
    @pytest.mark.parametrize("keys", [{}, {"editing_bgcolor": _gray(0.333)}, {"bgcolor": _gray(0.235)}])
    def test_missing_textcolor_is_theme_text(self, keys):
        assert _lc(_layout(_patch([_comment()], [], **keys))) == []

    def test_theme_canvas_fallback(self):
        c = _comment(textcolor=_gray(0.7))
        assert _lc(_layout(_patch([c], []))) == []
        warn = _lc(_layout(_patch([copy.deepcopy(c)], [], editing_bgcolor=_gray(0.333))))
        assert len(warn) == 1 and "3.54:1" in warn[0].finding

    @pytest.mark.parametrize("grad1, ratio", [([0.537, 0.537, 0.776, 1.0], "2.30:1"), (_gray(0.94), "1.24:1")])
    def test_e7_evidence_background_panels(self, grad1, ratio):
        panel = _panel_box("obj-2", background=1, grad1=grad1, presentation=1,
                           presentation_rect=[0.0, 0.0, 300.0, 200.0])
        c = _comment(rect=(900.0, 900.0, 100.0, 20.0), presentation=1,
                     presentation_rect=[40.0, 40.0, 100.0, 20.0])
        warn = _lc(_layout(_patch([c, panel], [], bgcolor=_gray(0.235))))
        assert len(warn) == 1
        assert ratio in warn[0].finding

    def test_first_containing_panel_wins(self):
        dark = _panel_box("obj-2", background=1, bgcolor=_gray(0.1))
        light = _panel_box("obj-3", background=1, bgcolor=_gray(0.94))
        c = _comment(textcolor=_DARK)
        assert len(_lc(_layout(_patch([c, dark, light], [])))) == 1
        assert _lc(_layout(_patch([copy.deepcopy(c), copy.deepcopy(light), copy.deepcopy(dark)], []))) == []

    def test_foreground_panel_beats_background_layer(self):
        dark_bg_layer = _panel_box("obj-2", background=1, bgcolor=_gray(0.1))
        light_fg = _panel_box("obj-3", background=0, bgcolor=_gray(0.94))
        c = _comment(textcolor=_DARK)
        assert _lc(_layout(_patch([c, dark_bg_layer, light_fg], []))) == []

    @pytest.mark.parametrize("fill", [_gray(0.0, 0.0), _gray(1.0, 0.2)])
    def test_low_alpha_panel_skipped(self, fill):
        panel = _panel_box("obj-2", background=1, bgcolor=fill)
        assert _lc(_layout(_patch([_comment(), panel], [], bgcolor=_gray(0.235)))) == []

    def test_low_alpha_own_fill_falls_through(self):
        light = _panel_box("obj-2", background=1, bgcolor=_gray(0.94))
        c = _comment(textcolor=_DARK, bgcolor=_gray(0.0, 0.0))
        assert _lc(_layout(_patch([c, light], []))) == []

    def test_opaque_own_fill_is_background(self):
        dark = _panel_box("obj-2", background=1, bgcolor=_gray(0.1))
        c = _comment(textcolor=_DARK, bgcolor=_gray(0.94))
        assert _lc(_layout(_patch([c, dark], []))) == []

    def test_message_without_fill_reads_against_theme_box_fill(self):
        light = _panel_box("obj-2", background=1, bgcolor=_gray(0.94))
        m = {"box": {"id": "obj-1", "maxclass": "message", "text": "start",
                     "textcolor": [0.2, 0.2, 0.25, 1.0], "patching_rect": [50.0, 50.0, 60.0, 22.0],
                     "numinlets": 2, "numoutlets": 1, "outlettype": [""]}}
        warn = _lc(_layout(_patch([m, light], [])))
        assert len(warn) == 1 and "1.12:1" in warn[0].finding
        m2 = copy.deepcopy(m)
        m2["box"]["bgfillcolor"] = {"type": "color", "color": _gray(0.9)}
        assert _lc(_layout(_patch([m2, copy.deepcopy(light)], []))) == []

    def test_junk_never_raises_and_pure(self):
        boxes = [
            _comment("obj-1", textcolor="x"),
            _comment("obj-2", textcolor=[0.1], bgcolor=[1]),
            _panel_box("obj-3", background="yes", bgcolor=[1]),
            _panel_box("obj-4", rect=None, bgcolor=_gray(0.9)),
            {"box": {"id": "obj-5", "maxclass": "panel", "patching_rect": [0, 0],
                     "presentation": 1, "presentation_rect": [1], "bgcolor": _gray(0.9)}},
            {"box": {"id": "obj-6", "maxclass": "panel", "patching_rect": [0, 0, 500, 500],
                     "presentation": 1, "presentation_rect": None, "grad1": ["q", 0, 0, 1]}},
            _comment("obj-7", rect=(1.0, 2.0, 3.0, 4.0), presentation=1, presentation_rect=[0, "z"]),
            {"box": {"id": "obj-8", "maxclass": "comment", "patching_rect": None, "textcolor": [0, 0, 0, 1]}},
            {"box": {"id": "obj-9", "maxclass": "message", "patching_rect": [5, 5, 10, 10],
                     "textcolor": [0, 0, 0], "bgfillcolor": {"color": "x"}}},
        ]
        d = _patch(boxes, [], bgcolor=[1], editing_bgcolor="x")
        before = copy.deepcopy(d)
        _layout(d)
        assert d == before


class TestContrastGenerator:
    def test_section_header_keeps_header_color(self):
        from src.maxpat.aesthetics import ensure_text_contrast, repair_text_contrast, set_canvas_background
        from src.maxpat.defaults import AESTHETIC_PALETTE
        from src.maxpat.patcher import Patcher
        p = Patcher()
        set_canvas_background(p)
        h = p.add_section_header("Header")
        assert repair_text_contrast(p) == 0
        ensure_text_contrast(p)
        assert h.extra_attrs["textcolor"] == AESTHETIC_PALETTE["header_color"]

    def test_explicit_light_text_on_dark_canvas_kept(self):
        from src.maxpat.aesthetics import repair_text_contrast, set_canvas_background
        from src.maxpat.patcher import Patcher
        p = Patcher()
        set_canvas_background(p)
        c = p.add_comment("light", 50.0, 50.0)
        c.extra_attrs["textcolor"] = [0.9, 0.9, 0.9, 1.0]
        assert repair_text_contrast(p) == 0
        assert c.extra_attrs["textcolor"] == [0.9, 0.9, 0.9, 1.0]

    def test_mid_gray_panel_falls_back_to_black(self):
        from src.maxpat.aesthetics import contrast_ratio, ensure_text_contrast, set_canvas_background
        from src.maxpat.defaults import MIN_CONTRAST_RATIO
        from src.maxpat.patcher import Patcher
        p = Patcher()
        set_canvas_background(p)
        panel = p.add_panel(0, 0, 300, 300, gradient=False)
        panel.extra_attrs["bgcolor"] = _gray(0.5)
        c = p.add_comment("on mid gray", 50.0, 50.0)
        ensure_text_contrast(p)
        assert c.extra_attrs["textcolor"] == [0.0, 0.0, 0.0, 1.0]
        assert contrast_ratio(c.extra_attrs["textcolor"], _gray(0.5)) >= MIN_CONTRAST_RATIO

    def test_missing_textcolor_still_filled(self):
        from src.maxpat.aesthetics import ensure_text_contrast
        from src.maxpat.patcher import Patcher
        p = Patcher()
        c = p.add_comment("plain", 50.0, 50.0)
        assert "textcolor" not in c.extra_attrs
        ensure_text_contrast(p)
        assert isinstance(c.extra_attrs.get("textcolor"), list)

    def test_generator_and_critic_agree(self):
        from src.maxpat.aesthetics import ensure_text_contrast, set_canvas_background
        from src.maxpat.critics.layout_critic import review_layout
        from src.maxpat.patcher import Patcher
        p = Patcher()
        set_canvas_background(p)
        dark = p.add_panel(0, 0, 400, 400, gradient=False)
        dark.extra_attrs["bgcolor"] = _gray(0.1)
        light = p.add_panel(0, 0, 200, 200, gradient=False)
        light.extra_attrs["bgcolor"] = _gray(0.94)
        ghost = p.add_panel(500, 0, 200, 200, gradient=False)
        ghost.extra_attrs["bgcolor"] = [1.0, 1.0, 1.0, 0.2]
        p.add_comment("on both", 50.0, 50.0)
        p.add_comment("on dark only", 300.0, 300.0)
        p.add_comment("on ghost", 550.0, 50.0)
        p.add_section_header("Header")
        p.add_annotation("note")
        ensure_text_contrast(p)
        assert [r.finding for r in review_layout(p.to_dict()) if _LC in r.finding and r.severity == "warning"] == []
