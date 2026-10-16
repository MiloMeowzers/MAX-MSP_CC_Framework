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
