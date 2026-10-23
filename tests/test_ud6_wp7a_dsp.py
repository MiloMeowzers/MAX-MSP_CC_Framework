"""WP7a (quick 261022-ud6): WP3 follow-up -- an LFO depth ``*~`` whose
output sets a filter's cutoff / resonance / delay-time inlet scales Hz, not
audio, and is not judged as a gain stage (CR-01). The same ``*~`` into the
filter's audio inlet 0 is still a gain stage.
"""
from __future__ import annotations

import pytest

from src.maxpat.critics import review_patch
from src.maxpat.db_lookup import ObjectDatabase
from tests.test_critics_recursive import _box, _line, _patch


@pytest.fixture(scope="module")
def db():
    return ObjectDatabase()


def _sig(box_id, text, n_in=2, n_out=1):
    return _box(box_id, text, n_in, n_out, outlettype=["signal"] * n_out)


def _unsafe(results):
    return [r for r in results if r.rule == "unsafe_gain_sources"]


def _lfo_patch(filter_text, n_in, dst_inlet):
    """cycle~ 2 -> *~ <- flonum 0..2000; *~ -> +~ 1000 -> <filter> dst_inlet;
    noise~ -> <filter> 0 -> *~ 0.2 -> dac~."""
    boxes = [
        _sig("obj-1", "cycle~ 2"),
        _box("obj-2", None, 1, 2, maxclass="flonum", outlettype=["", "bang"],
             minimum=0.0, maximum=2000.0),
        _sig("obj-3", "*~"),
        _sig("obj-4", "+~ 1000."),
        _sig("obj-5", "noise~", 1, 1),
        _sig("obj-6", filter_text, n_in, 1),
        _sig("obj-7", "*~ 0.2"),
        _box("obj-99", "dac~", 2, 0, outlettype=[]),
    ]
    lines = [
        _line("obj-1", 0, "obj-3", 0), _line("obj-2", 0, "obj-3", 1),
        _line("obj-3", 0, "obj-4", 0), _line("obj-4", 0, "obj-6", dst_inlet),
        _line("obj-6", 0, "obj-7", 0),
        _line("obj-7", 0, "obj-99", 0), _line("obj-7", 0, "obj-99", 1),
    ]
    if dst_inlet != 0:
        lines.append(_line("obj-5", 0, "obj-6", 0))
    return _patch(boxes, lines)


@pytest.mark.parametrize("filter_text,n_in,inlet", [
    ("lores~", 3, 1), ("lores~", 3, 2), ("svf~", 3, 1), ("onepole~", 2, 1),
    ("reson~", 4, 2), ("cross~", 2, 1), ("mc.lores~", 3, 1),
])
def test_lfo_into_filter_parameter_is_not_a_gain(db, filter_text, n_in, inlet):
    results = review_patch(_lfo_patch(filter_text, n_in, inlet), db=db, is_new=True)
    assert _unsafe(results) == []


@pytest.mark.parametrize("filter_text,n_in,inlet", [
    ("lores~", 3, 0), ("reson~", 4, 1),
])
def test_same_product_into_audio_or_gain_inlet_still_blocks(db, filter_text, n_in, inlet):
    """lores~ 0 is the audio input; reson~ 1 is its input gain."""
    results = review_patch(_lfo_patch(filter_text, n_in, inlet), db=db, is_new=True)
    assert len(_unsafe(results)) == 1
    assert _unsafe(results)[0].severity == "blocker"
