"""DSP critic fixes (quick 261022-ud6 WP3): CR-01 / WR-04 gain stage only,
CR-03 gen~ I/O ports, purity.
"""

from __future__ import annotations

import copy

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
# CR-01 / WR-04 -- unsafe gain only on a gain stage
# ---------------------------------------------------------------------------


class TestGainStageOnly:
    def test_pitch_sweep_into_oscillator_passes(self, db):
        """[0, 1 1000( -> line~ -> *~ 440. -> +~ 220. -> cycle~ -> *~ 0.2 -> dac~."""
        boxes = [
            _msg("obj-1", "0, 1 1000"),
            _box("obj-2", "line~", 2, 2, outlettype=["signal", "bang"]),
            _sig_box("obj-3", "*~ 440."),
            _sig_box("obj-4", "+~ 220."),
            _sig_box("obj-5", "cycle~"),
            _sig_box("obj-6", "*~ 0.2"),
            _dac(),
        ]
        lines = [
            _line("obj-1", 0, "obj-2", 0), _line("obj-2", 0, "obj-3", 0),
            _line("obj-3", 0, "obj-4", 0), _line("obj-4", 0, "obj-5", 0),
            _line("obj-5", 0, "obj-6", 0), _line("obj-6", 0, "obj-99", 0),
            _line("obj-6", 0, "obj-99", 1),
        ]
        results = review_patch(_patch(boxes, lines), db=db, is_new=True)
        assert _rule(results, "unsafe_gain_sources") == []

    def test_ramp_times_constant_no_audio_operand_passes(self, db):
        """[220 500( -> line~ -> *~ 2.: arithmetic, no audio operand."""
        boxes = [
            _msg("obj-1", "220 500"),
            _box("obj-2", "line~", 2, 2, outlettype=["signal", "bang"]),
            _sig_box("obj-3", "*~ 2."),
        ]
        lines = [_line("obj-1", 0, "obj-2", 0), _line("obj-2", 0, "obj-3", 0)]
        assert _rule(review_patch(_patch(boxes, lines), db=db), "unsafe_gain_sources") == []

    def test_scaled_ramp_reaching_a_gain_still_blocks(self, db):
        """[0, 100 500( -> line~ -> *~ 0.5 -> *~ inlet 1 (cycle~ on inlet 0):
        the product 0..50 is the gain value of the second *~."""
        boxes = [
            _msg("obj-1", "0, 100 500"),
            _box("obj-2", "line~", 2, 2, outlettype=["signal", "bang"]),
            _sig_box("obj-3", "*~ 0.5"),
            _sig_box("obj-7", "cycle~ 440"),
            _sig_box("obj-9", "*~"),
        ]
        lines = [
            _line("obj-1", 0, "obj-2", 0), _line("obj-2", 0, "obj-3", 0),
            _line("obj-3", 0, "obj-9", 1), _line("obj-7", 0, "obj-9", 0),
        ]
        ug = _rule(review_patch(_patch(boxes, lines), db=db), "unsafe_gain_sources")
        assert len(ug) == 1
        assert ug[0].finding.startswith(
            "Unsafe gain source: message '0, 100 500' (obj-1) reaches '*~' (obj-9) inlet 1 via line~"
        )
        assert "(range 0 to 50)" in ug[0].finding

    def test_envelope_vca_on_inlet_0_still_blocks(self, db):
        """line~ envelope on inlet 0, audio on inlet 1 is a VCA."""
        boxes = [
            _msg("obj-1", "0, 5 100"),
            _box("obj-2", "line~", 2, 2, outlettype=["signal", "bang"]),
            _sig_box("obj-7", "cycle~ 440"),
            _sig_box("obj-9", "*~"),
        ]
        lines = [
            _line("obj-1", 0, "obj-2", 0), _line("obj-2", 0, "obj-9", 0),
            _line("obj-7", 0, "obj-9", 1),
        ]
        ug = _rule(review_patch(_patch(boxes, lines), db=db), "unsafe_gain_sources")
        assert len(ug) == 1 and "inlet 0 via line~" in ug[0].finding

    def test_fm_depth_in_hz_passes(self, db):
        """WR-04: cycle~ 5 -> *~ 100. (flonum 0..500 on inlet 1) -> +~ 440. -> cycle~."""
        boxes = [
            _sig_box("obj-1", "cycle~ 5"),
            _box("obj-2", None, 1, 2, maxclass="flonum", outlettype=["", "bang"],
                 minimum=0.0, maximum=500.0),
            _sig_box("obj-3", "*~ 100."),
            _sig_box("obj-4", "+~ 440."),
            _sig_box("obj-5", "cycle~"),
            _sig_box("obj-6", "*~ 0.2"),
            _dac(),
        ]
        lines = [
            _line("obj-1", 0, "obj-3", 0), _line("obj-2", 0, "obj-3", 1),
            _line("obj-3", 0, "obj-4", 0), _line("obj-4", 0, "obj-5", 0),
            _line("obj-5", 0, "obj-6", 0), _line("obj-6", 0, "obj-99", 0),
        ]
        results = review_patch(_patch(boxes, lines), db=db, is_new=True)
        assert _rule(results, "unsafe_gain_sources") == []

    def test_mc_fm_depth_passes(self, db):
        boxes = [
            _box("obj-1", "mc.cycle~ 5", 2, 1, outlettype=["multichannelsignal"]),
            _box("obj-2", None, 1, 2, maxclass="flonum", outlettype=["", "bang"],
                 minimum=0.0, maximum=500.0),
            _box("obj-3", "mc.*~ 100.", 2, 1, outlettype=["multichannelsignal"]),
            _box("obj-5", "mc.phasor~", 2, 1, outlettype=["multichannelsignal"]),
        ]
        lines = [
            _line("obj-1", 0, "obj-3", 0), _line("obj-2", 0, "obj-3", 1),
            _line("obj-3", 0, "obj-5", 0),
        ]
        assert _rule(review_patch(_patch(boxes, lines), db=db), "unsafe_gain_sources") == []

    def test_audio_gain_into_dac_still_blocks(self, db):
        """The classic unsafe shape is unchanged: cycle~ -> *~ (flonum 0..127) -> dac~."""
        boxes = [
            _sig_box("obj-1", "cycle~ 440"),
            _box("obj-2", None, 1, 2, maxclass="flonum", outlettype=["", "bang"]),
            _sig_box("obj-3", "*~"),
            _dac(),
        ]
        lines = [
            _line("obj-1", 0, "obj-3", 0), _line("obj-2", 0, "obj-3", 1),
            _line("obj-3", 0, "obj-99", 0),
        ]
        ug = _rule(review_patch(_patch(boxes, lines), db=db), "unsafe_gain_sources")
        assert len(ug) == 1 and ug[0].severity == "blocker"


# ---------------------------------------------------------------------------
# CR-03 -- gen~ I/O compares the right ports
# ---------------------------------------------------------------------------


def _gen_box(inner, n_in=1, n_out=1, text="gen~"):
    return _container("obj-1", text, _inner(inner[0], inner[1], classnamespace="dsp.gen"),
                      n_in, n_out, outlettype=["signal"] * n_out)


def _gb(box_id, text, n_in=1, n_out=1):
    return _box(box_id, text, n_in, n_out, outlettype=[""] * n_out)


def _cb(box_id, code, n_in, n_out):
    return _box(box_id, None, n_in, n_out, maxclass="codebox", code=code)


def _gen_io(results):
    return _rule(results, "gen_io_match")


class TestGenIOPorts:
    def test_codeboxes_in_series(self, db):
        """in 1 -> codebox A (out1, out2) -> codebox B (in1 * in2) -> out 1; B listed first."""
        inner = (
            [
                _cb("cb-b", "out1 = in1 * in2;", 2, 1),
                _gb("g-in", "in 1", 0, 1),
                _cb("cb-a", "out1 = in1; out2 = in1 * 0.5;", 1, 2),
                _gb("g-out", "out 1", 1, 0),
            ],
            [
                _line("g-in", 0, "cb-a", 0),
                _line("cb-a", 0, "cb-b", 0), _line("cb-a", 1, "cb-b", 1),
                _line("cb-b", 0, "g-out", 0),
            ],
        )
        assert _gen_io(review_patch(_patch([_gen_box(inner)]), db=db)) == []

    def test_param_fed_codebox(self, db):
        """in 1 -> codebox in1, param depth 0.5 -> codebox in2."""
        inner = (
            [
                _gb("g-in", "in 1", 0, 1),
                _gb("g-p", "param depth 0.5", 0, 1),
                _cb("cb", "out1 = in1 * in2;", 2, 1),
                _gb("g-out", "out 1", 1, 0),
            ],
            [
                _line("g-in", 0, "cb", 0), _line("g-p", 0, "cb", 1),
                _line("cb", 0, "g-out", 0),
            ],
        )
        assert _gen_io(review_patch(_patch([_gen_box(inner)]), db=db)) == []

    def test_operator_beyond_box_inlets_blocks(self, db):
        """in 1, in 2 operators but the gen~ box saves only 1 inlet."""
        inner = (
            [
                _gb("g-in1", "in 1", 0, 1), _gb("g-in2", "in 2", 0, 1),
                _cb("cb", "out1 = in1 + in2;", 2, 1),
                _gb("g-out", "out 1", 1, 0),
            ],
            [
                _line("g-in1", 0, "cb", 0), _line("g-in2", 0, "cb", 1),
                _line("cb", 0, "g-out", 0),
            ],
        )
        gen = _gen_io(review_patch(_patch([_gen_box(inner)]), db=db))
        assert len(gen) == 1 and gen[0].severity == "blocker"
        assert gen[0].finding.startswith("gen~ I/O input mismatch")

    def test_add_gen_shape_unwired_inputs_still_blocks(self, db):
        """add_gen layout: code uses in1..in3 but only in 1 exists and is wired."""
        inner = (
            [
                _gb("g-in1", "in 1", 0, 1),
                _cb("cb", "out1 = in1 + in2 + in3;", 3, 1),
                _gb("g-out", "out 1", 1, 0),
            ],
            [_line("g-in1", 0, "cb", 0), _line("cb", 0, "g-out", 0)],
        )
        gen = _gen_io(review_patch(_patch([_gen_box(inner)]), db=db))
        assert len(gen) == 1 and "uses 3 inputs" in gen[0].finding


# ---------------------------------------------------------------------------
# Purity
# ---------------------------------------------------------------------------


def test_review_is_pure(db):
    boxes = [
        _sig_box("obj-1", "cycle~ 5"),
        _box("obj-2", None, 1, 2, maxclass="flonum", outlettype=["", "bang"]),
        _sig_box("obj-3", "*~ 100."),
        _sig_box("obj-5", "cycle~"),
    ]
    lines = [_line("obj-1", 0, "obj-3", 0), _line("obj-2", 0, "obj-3", 1), _line("obj-3", 0, "obj-5", 0)]
    d = _patch(boxes, lines)
    before = copy.deepcopy(d)
    review_patch(d, db=db, is_new=True)
    assert d == before
