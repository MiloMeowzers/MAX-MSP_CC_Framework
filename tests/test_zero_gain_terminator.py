"""WR-04 (review-validation, quick 261022-ud6 WP1): ``*~ 0.`` is the
CLAUDE.md-sanctioned chain terminator ("Always terminate signal chains with
``dac~`` or ``*~ 0.``"), but the unterminated-chain rule flagged it, and
Q19 recursion spread the false positive into every subpatcher
(terrain-synth ``[p terrain-view-a]`` / ``[p terrain-view-b]``).

A ``*~`` / ``mc.*~`` whose first argument is zero and whose right (gain)
inlet has no incoming cord is a mute sink, not an unterminated chain.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from src.maxpat.db_lookup import ObjectDatabase
from src.maxpat.validation import validate_patch
from tests.test_validation import _make_box, _make_line, _make_patch_dict

_REPO = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def db():
    return ObjectDatabase()


def _unterminated(results):
    return [r for r in results if "Unterminated signal chain" in r.message]


def _chain(mul_text, *, gain_cord=False, mc=False):
    sig = "multichannelsignal" if mc else "signal"
    boxes = [
        _make_box("obj-1", text="mc.cycle~ 220" if mc else "cycle~ 220",
                  numinlets=2, numoutlets=1, outlettype=[sig]),
        _make_box("obj-2", text=mul_text, numinlets=2, numoutlets=1,
                  outlettype=[sig]),
    ]
    lines = [_make_line("obj-1", 0, "obj-2", 0)]
    if gain_cord:
        boxes.append(_make_box("obj-3", text="sig~ 0.5", numinlets=1,
                               numoutlets=1, outlettype=["signal"]))
        lines.append(_make_line("obj-3", 0, "obj-2", 1))
    return _make_patch_dict(boxes=boxes, lines=lines)


class TestZeroGainSink:

    @pytest.mark.parametrize("text", ["*~ 0.", "*~ 0", "*~ 0.0", "*~ 0. @foo 1"])
    def test_mute_sink_is_terminated(self, db, text):
        results = validate_patch(_chain(text), db=db)
        assert [r for r in _unterminated(results) if "obj-2" in r.message] == []

    def test_mc_mute_sink_is_terminated(self, db):
        results = validate_patch(_chain("mc.*~ 0.", mc=True), db=db)
        assert [r for r in _unterminated(results) if "obj-2" in r.message] == []

    @pytest.mark.parametrize("text", ["*~ 0.5", "*~", "*~ 1", "*~ #1"])
    def test_non_zero_or_unknown_gain_still_warns(self, db, text):
        results = validate_patch(_chain(text), db=db)
        assert [r for r in _unterminated(results) if "obj-2" in r.message]

    def test_driven_gain_inlet_still_warns(self, db):
        results = validate_patch(_chain("*~ 0.", gain_cord=True), db=db)
        assert [r for r in _unterminated(results) if "obj-2" in r.message]


class TestTerrainSynthViews:

    def test_no_unterminated_warning_on_view_mute_sinks(self, db):
        path = _REPO / "patches/terrain-synth/generated/terrain-synth.maxpat"
        patch = copy.deepcopy(json.loads(path.read_text()))
        rows = [
            r for r in _unterminated(validate_patch(patch, db=db))
            if "terrain-view" in r.message and "'*~'" in r.message
        ]
        assert rows == [], [str(r) for r in rows]
