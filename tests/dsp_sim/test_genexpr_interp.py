"""GenExpr interpreter unit tests (Q35, quick 261021-urs).

Short codeboxes through parse_codebox(code).build(...).run(inputs, n), plus
the bit-exact parity test against patches/bassoon-model/tools/genrun.py on
the shipped bassoon codebox.
"""

from __future__ import annotations

import importlib
import json
import math
import random
import sys
from pathlib import Path

import numpy as np
import pytest

from src.maxpat.dsp_sim.genexpr_interp import (
    GEN_CONSTANTS,
    STATE_CAP,
    Unsupported,
    parse_codebox,
)

_REPO = Path(__file__).resolve().parents[2]
_BASSOON_DIR = _REPO / "patches" / "bassoon-model"
_GENDSP = _BASSOON_DIR / "generated" / "bassoon.gendsp"
_TOOLS = _BASSOON_DIR / "tools"


def run(code, inputs=None, n=8, **build):
    cb = parse_codebox(code)
    if inputs is None:
        inputs = [np.zeros(n) for _ in range(cb.n_in)]
    return cb.build(**build).run(inputs, n)


def impulse(n, at=0, value=1.0):
    x = np.zeros(n)
    x[at] = value
    return x


def unsupported(code, match, n=1, **build):
    with pytest.raises(Unsupported, match=match):
        run(code, n=n, **build)


# ===========================================================================
# Operators, constants, History, locals
# ===========================================================================


def test_precedence():
    (o,) = run("out1 = 1 + 2 * 3 - 4 / 2;", n=1)
    assert o[0] == 5.0
    (o,) = run("out1 = -2 * -3;", n=1)
    assert o[0] == 6.0


def test_ternary_is_right_associative():
    o1, o2 = run("out1 = 0 ? 1 : 1 ? 2 : 3; out2 = 1 ? 5 : 0 ? 2 : 3;", n=1)
    assert o1[0] == 2.0
    assert o2[0] == 5.0


def test_comparisons_give_one_or_zero():
    outs = run(
        "out1 = 2 < 3; out2 = 3 < 2; out3 = 2 == 2; out4 = 2 != 2; "
        "out5 = 1 && 0; out6 = 1 || 0;",
        n=1,
    )
    assert [o[0] for o in outs] == [1.0, 0.0, 1.0, 0.0, 0.0, 1.0]


def test_safediv_and_fmod():
    o1, o2, o3 = run("out1 = 1 / 0; out2 = -7 % 3; out3 = 5 % 0;", n=1)
    assert o1[0] == 0.0
    assert o2[0] == -1.0
    assert o3[0] == 0.0
    x = np.array([0.0, 2.0])
    (o,) = run("out1 = 1 / in1;", inputs=[x], n=2)
    assert o.tolist() == [0.0, 0.5]


def test_compound_assignment_on_locals_and_history():
    (o,) = run("x = 2; x += 3; x -= 1; x *= 4; x /= 2; out1 = x;", n=2)
    assert o.tolist() == [8.0, 8.0]
    (o,) = run("History h(1); h *= 2; out1 = h;", n=3)
    assert o.tolist() == [2.0, 4.0, 8.0]


def test_constants():
    outs = run("out1 = pi; out2 = TWOPI; out3 = HALFPI; out4 = phi; out5 = PI;", n=1)
    assert [o[0] for o in outs] == [
        math.pi, 2 * math.pi, math.pi / 2, (1 + math.sqrt(5)) / 2, math.pi,
    ]
    assert GEN_CONSTANTS["twopi"] == GEN_CONSTANTS["TWOPI"]


def test_assignment_to_constant_is_ignored_with_warning():
    cb = parse_codebox("e = 5; out1 = e;")
    (o,) = cb.build().run([], 1)
    assert o[0] == math.e
    assert len(cb.warnings) == 1 and "'e'" in cb.warnings[0]


def test_history_is_sequential():
    x = np.array([1.0, 2.0, 3.0, 4.0])
    o1, o2 = run("History h(0); out1 = h; h = in1; out2 = h;", inputs=[x], n=4)
    assert o1.tolist() == [0.0, 1.0, 2.0, 3.0]
    assert o2.tolist() == x.tolist()


@pytest.mark.parametrize(
    "code,name,line",
    [
        ("if (in1 > 0) {\n y = 1;\n} else {\n y = 0.5;\n}\nout1 = y * in1;", "y", 6),
        ("out1 = y;\ny = in1;", "y", 1),
        ("if (in1 > 0) { y = 1; } out1 = y;", "y", 1),
        ("y += in1; out1 = y;", "y", 1),
        ("for (i = 0; i < 4; i += 1) { acc += 1; } out1 = acc;", "acc", 1),
        ("for (i = 0; i < 4; i += 1) { t = i; } out1 = i;", "i", 1),
        ("x = x + 1; out1 = x;", "x", 1),
    ],
    ids=["if-else-only", "read-then-assign", "if-only", "compound", "for-body",
         "for-counter-leak", "self-read"],
)
def test_local_read_before_assignment_is_unsupported(code, name, line):
    """CR-01: gen~ refuses a local read before it is assigned on every path
    ('not defined'); names first assigned in an if/else or for block do not
    leak out of it. Replaces test_locals_reset_every_sample, whose codebox
    ``x = x + 1; out1 = x;`` is exactly this read-before-assign form."""
    with pytest.raises(Unsupported, match=rf"local '{name}' is read before it is assigned") as ei:
        parse_codebox(code)
    assert ei.value.line == line


def test_definitely_assigned_locals_still_run():
    x = np.array([1.0, -1.0])
    (o,) = run(
        "y = 0; if (in1 > 0) { y = 1; } else { y = 0.5; } out1 = y * in1;", inputs=[x], n=2
    )
    assert o.tolist() == [1.0, -0.5]
    # Block-local: first assigned and read inside the same block.
    (o,) = run("if (in1 > 0) { t = in1 * 2; out1 = t; }", inputs=[x], n=2)
    assert o.tolist() == [2.0, 0.0]
    # Loop-carried locals assigned before the loop (the terrain-cheby form).
    (o,) = run(
        "x = in1; t0 = 1; t1 = x; acc = t0 + t1; "
        "for (i = 2; i < 6; i += 1) { t2 = 2 * x * t1 - t0; t0 = t1; t1 = t2; acc += t2; } "
        "out1 = acc;",
        inputs=[np.ones(2)], n=2,
    )
    assert o.tolist() == [6.0, 6.0]
    cb = parse_codebox("e = 5; out1 = e;")
    assert cb.build().run([], 1)[0][0] == math.e and len(cb.warnings) == 1


def test_tab_char_lint():
    """WR-03: a tab is a WARN naming its first line (not Unsupported)."""
    lint = parse_codebox("out1 =\tin1 * 0.5;").lint
    assert [c for c, _d in lint] == ["tab_char"]
    assert "line 1" in lint[0][1]
    lint = parse_codebox("x = in1;\nout1 =\tx;\ny =\tx;").lint
    assert [c for c, _d in lint] == ["tab_char"]
    assert "line 2" in lint[0][1]
    assert parse_codebox("out1 = in1;").lint == []


@pytest.mark.parametrize(
    "code,name",
    [("out1 = in1; ou2 = in1 * 2;", "ou2"), ("Out1 = in1; out1 = in1;", "Out1")],
)
def test_output_typo_lint(code, name):
    """CR-02: a local that looks like a misspelled output warns."""
    lint = parse_codebox(code).lint
    assert [c for c, _d in lint] == ["output_typo"]
    assert f"'{name}'" in lint[0][1]


def test_param_default_and_overrides_are_clamped():
    """WR-04: gen~ clamps a Param to its declared range (param refpage)."""
    cb = parse_codebox("Param p(5, min=0, max=1); out1 = p;")
    assert cb.params[0]["default"] == 1.0
    assert cb.build().run([], 1)[0][0] == 1.0
    assert cb.build(params={"p": 9}).run([], 1)[0][0] == 1.0
    assert cb.build(params={"p": -3}).run([], 1)[0][0] == 0.0
    assert parse_codebox("Param p(min=0.5, max=1); out1 = p;").params[0]["default"] == 0.5
    cb = parse_codebox("Param p(7); out1 = p;")
    assert cb.params[0]["default"] == 7.0
    assert cb.build(params={"p": -40}).run([], 1)[0][0] == -40.0


# ===========================================================================
# WR-02: taken-branch if/else (pinned) and the branch_state advisory
# ===========================================================================

_WR02_PROBE = "History c; if (c > 1e9) { out1 = noise(); } out1 = in1;"


def test_untaken_noise_does_not_advance_the_stream():
    """Taken-branch semantics are the simulator's choice (unconfirmed in MAX):
    an untaken noise() draws nothing."""
    code = "if (in1 > 0) { y = noise(); out2 = y; } out1 = noise();"
    rng = random.Random(7)
    draws = [-1 + 2 * rng.random() for _ in range(8)]
    o1, o2 = run(code, inputs=[np.zeros(4)], n=4, seed=7)
    assert o1.tolist() == draws[:4]
    assert o2.tolist() == [0.0] * 4
    o1, o2 = run(code, inputs=[np.ones(4)], n=4, seed=7)
    assert o2.tolist() == draws[0::2]
    assert o1.tolist() == draws[1::2]


def test_conditional_poke_writes_only_when_taken():
    (o,) = run(
        "Data d(4); if (in1 > 0) { poke(d, 1, 0, 0); } out1 = peek(d, 0, 0);",
        inputs=[np.array([0.0, 0.0, 1.0, 0.0])], n=4,
    )
    assert o.tolist() == [0.0, 0.0, 1.0, 1.0]


def test_branch_state_advisory_on_review_probe():
    adv = parse_codebox(_WR02_PROBE).advisories
    assert [c for c, _d in adv] == ["branch_state"]
    assert "noise() (line 1)" in adv[0][1]
    assert "unconfirmed in MAX" in adv[0][1]


@pytest.mark.parametrize(
    "decl,stmt,named",
    [
        ("", "noise();", "noise()"),
        ("", "phasor(1);", "phasor()"),
        ("", "cycle(1);", "cycle()"),
        ("", "latch(in1, 1);", "latch()"),
        ("", "dcblock(in1);", "dcblock()"),
        ("Data d(4); ", "poke(d, 1, 0, 0);", "poke()"),
        ("Delay dl(10); ", "dl.write(in1);", "dl.write()"),
    ],
    ids=["noise", "phasor", "cycle", "latch", "dcblock", "poke", "delay-write"],
)
def test_branch_state_flags_each_construct(decl, stmt, named):
    adv = parse_codebox(f"{decl}if (in1 > 0) {{ {stmt} out1 = 1; }}").advisories
    assert [c for c, _d in adv] == ["branch_state"], adv
    assert f"{named} (line 1)" in adv[0][1]


@pytest.mark.parametrize(
    "code",
    [
        "if (in1 > 0) { out1 = 1; } else { out1 = noise(); }",
        "if (in1 > 0) { if (in1 > 1) { out1 = noise(); } }",
        "if (in1 > 0) { for (i = 0; i < 4; i += 1) { out1 += noise(); } }",
    ],
    ids=["else-body", "nested-if", "for-in-if"],
)
def test_branch_state_fires_from_every_branch_position(code):
    adv = parse_codebox(code).advisories
    assert [c for c, _d in adv] == ["branch_state"], adv
    assert "noise() (line 1)" in adv[0][1]


def test_branch_state_aggregates_per_construct():
    code = (
        "Data d(4);\nif (in1 > 0) {\n poke(d, 1, 0, 0);\n poke(d, 2, 1, 0);\n"
        " out1 = noise();\n}"
    )
    (adv,) = parse_codebox(code).advisories
    detail = adv[1]
    assert "poke() x2 (first at line 3)" in detail
    assert "noise() (line 5)" in detail
    assert detail.index("poke()") < detail.index("noise()")


@pytest.mark.parametrize(
    "code",
    [
        "out1 = noise();",
        "if (noise() > 0) { out1 = 1; }",
        "out1 = in1 > 0 ? noise() : 0;",
        "History h; if (in1 > 0) { h = in1; } out1 = h;",
        "Data d(4); if (in1 > 0) { out1 = peek(d, 0, 0) + dim(d) + channels(d) "
        "+ selector(1, in1, 0); }",
    ],
    ids=["no-if", "if-condition", "ternary", "history-assign", "pure-reads"],
)
def test_branch_state_not_flagged(code):
    assert parse_codebox(code).advisories == []


def test_output_typo_lint_ignores_ordinary_locals():
    assert parse_codebox("t1 = in1; t0 = t1; out1 = t0;").lint == []


# ===========================================================================
# for loops
# ===========================================================================


def test_for_loop_constant_bound():
    (o,) = run("acc = 0; for (i = 0; i < 32; i += 1) { acc += 1; } out1 = acc;", n=2)
    assert o.tolist() == [32.0, 32.0]


def test_for_loop_param_bound_folds_per_corner():
    code = (
        "Param k(4, min=1, max=8); acc = 0; "
        "for (i = 0; i < k; i += 1) { acc += 1; } out1 = acc;"
    )
    (o,) = run(code, n=1)
    assert o[0] == 4.0
    (o,) = run(code, n=1, params={"k": 8})
    assert o[0] == 8.0


def test_for_loop_non_constant_bound_is_unsupported():
    unsupported(
        "acc = 0; for (i = 0; i < in1; i += 1) { acc += 1; } out1 = acc;",
        "for loop bound is not constant",
    )


def test_for_loop_cap_is_unsupported():
    unsupported(
        "acc = 0; for (i = 0; i < 200000; i += 1) { acc += 1; } out1 = acc;",
        "100000",
    )


def test_nested_for_is_unsupported():
    unsupported(
        "acc = 0; for (i = 0; i < 2; i += 1) { "
        "for (j = 0; j < 2; j += 1) { acc += 1; } } out1 = acc;",
        "nested for loop",
    )


# ===========================================================================
# Delay
# ===========================================================================


def test_delay_read_integer_tap():
    (o,) = run("Delay d(10); out1 = d.read(3); d.write(in1);", inputs=[impulse(12)], n=12)
    assert np.nonzero(o)[0].tolist() == [3]
    assert o[3] == 1.0


@pytest.mark.parametrize("tap,at", [(0, 1), (100, 10)], ids=["read0-clamps-1", "read100-clamps-10"])
def test_delay_read_clamps(tap, at):
    code = f"Delay d(10); out1 = d.read({tap}); d.write(in1);"
    (o,) = run(code, inputs=[impulse(14)], n=14)
    assert np.nonzero(o)[0].tolist() == [at]


def test_delay_read_fraction_interpolates_linearly():
    (o,) = run("Delay d(10); out1 = d.read(2.5); d.write(in1);", inputs=[impulse(8)], n=8)
    assert o[2] == pytest.approx(0.5)
    assert o[3] == pytest.approx(0.5)
    assert np.count_nonzero(o) == 2


def test_delay_write_then_read_same_sample_sees_previous():
    (o,) = run("Delay d(10); d.write(in1); out1 = d.read(1);", inputs=[impulse(4)], n=4)
    assert o.tolist() == [0.0, 1.0, 0.0, 0.0]


def test_delay_multiple_taps():
    o1, o2 = run(
        "Delay d(10); out1 = d.read(2); out2 = d.read(5); d.write(in1);",
        inputs=[impulse(8)], n=8,
    )
    assert np.nonzero(o1)[0].tolist() == [2]
    assert np.nonzero(o2)[0].tolist() == [5]


# ===========================================================================
# Data / Buffer
# ===========================================================================


def test_peek_floors_index_and_bounds():
    code = (
        "Data d(4); poke(d, 7, 2, 0); "
        "out1 = peek(d, 2.9, 0); out2 = peek(d, -1, 0); out3 = peek(d, 4, 0); "
        "out4 = peek(d, 2, 1); out5 = peek(d, 2);"
    )
    outs = run(code, n=1)
    assert [o[0] for o in outs] == [7.0, 0.0, 0.0, 0.0, 7.0]


def test_peek_non_finite_index_gives_zero():
    x = np.array([np.nan, np.inf])
    (o,) = run("Data d(4); poke(d, 1, 0, 0); out1 = peek(d, in1, 0);", inputs=[x], n=2)
    assert o.tolist() == [0.0, 0.0]


def test_poke_out_of_range_writes_nothing():
    code = (
        "Data d(4); poke(d, 9, 4, 0); poke(d, 9, -1, 0); poke(d, 9, 0, 1); "
        "out1 = peek(d, 0, 0) + peek(d, 3, 0);"
    )
    (o,) = run(code, n=1)
    assert o[0] == 0.0


def test_dim_and_channels():
    o1, o2 = run("Data d(100, 3); out1 = dim(d); out2 = channels(d);", n=1)
    assert (o1[0], o2[0]) == (100.0, 3.0)


def test_default_buffer_backing():
    code = 'Buffer b("snd"); out1 = dim(b); out2 = channels(b); out3 = peek(b, 10, 0);'
    o1, o2, o3 = run(code, n=1)
    assert o1[0] == 48000.0
    assert o2[0] == 1.0
    assert o3[0] == pytest.approx(0.25 * math.sin(2 * math.pi * 220 * 10 / 44100.0))


def test_buffer_resized_by_name():
    code = 'Buffer b("snd"); out1 = dim(b); out2 = channels(b);'
    o1, o2 = run(code, n=1, buffers={"snd": (1000, 2)})
    assert (o1[0], o2[0]) == (1000.0, 2.0)
    o1, _o2 = run("Buffer snd; out1 = dim(snd); out2 = 0;", n=1, buffers={"snd": (64, 1)})
    assert o1[0] == 64.0


def test_data_is_zero_filled():
    (o,) = run("Data d(16); out1 = peek(d, 5, 0);", n=1)
    assert o[0] == 0.0


def test_state_cap_is_unsupported():
    unsupported(f"Data d({STATE_CAP + 1}); out1 = 0;", "STATE_CAP|state cap|exceed")


# ===========================================================================
# Stateful built-ins
# ===========================================================================


def test_noise_matches_python_random_stream():
    o1, o2 = run("out1 = noise(); out2 = noise();", n=4, seed=7)
    rng = random.Random(7)
    expect = [-1 + 2 * rng.random() for _ in range(8)]
    assert o1.tolist() == expect[0::2]
    assert o2.tolist() == expect[1::2]
    again1, _ = run("out1 = noise(); out2 = noise();", n=4, seed=7)
    assert again1.tolist() == o1.tolist()


def test_phasor_period():
    (o,) = run("out1 = phasor(441);", n=1000)
    assert o[0] == 0.0
    wraps = np.nonzero(np.diff(o) < 0)[0]
    assert len(wraps) >= 9
    gaps = np.diff(wraps)
    assert set(gaps.tolist()) <= {99, 100, 101}
    assert abs(float(np.mean(gaps)) - 100.0) <= 0.5


def test_latch_holds_when_control_is_zero():
    x = np.array([1.0, 2.0, 3.0, 4.0])
    c = np.array([1.0, 0.0, 1.0, 0.0])
    (o,) = run("out1 = latch(in1, in2);", inputs=[x, c], n=4)
    assert o.tolist() == [1.0, 1.0, 3.0, 3.0]


def test_dcblock_matches_refpage_genexpr():
    x = np.array([1.0, 1.0, 0.5, -0.25, 0.0])
    (o,) = run("out1 = dcblock(in1);", inputs=[x], n=5)
    y1 = x1 = 0.0
    expect = []
    for v in x:
        y = v - x1 + 0.9997 * y1
        x1, y1 = v, y
        expect.append(y)
    assert o.tolist() == expect


def test_cycle_is_sine_of_internal_phase():
    (o,) = run("out1 = cycle(441);", n=4)
    expect = [math.sin(2 * math.pi * k * 0.01) for k in range(4)]
    assert o.tolist() == pytest.approx(expect, abs=1e-12)


def test_selector_mc_channel_triangle():
    outs = run(
        "out1 = selector(1, 5, 6); out2 = selector(2, 5, 6); out3 = selector(9, 5, 6); "
        "out4 = selector(0, 5, 6); out5 = mc_channel; out6 = mc_channelcount(); "
        "out7 = triangle(0.25, 0.5);",
        n=1,
    )
    assert [o[0] for o in outs] == [5.0, 6.0, 6.0, 0.0, 1.0, 1.0, 0.5]


# ===========================================================================
# Unsupported
# ===========================================================================


@pytest.mark.parametrize(
    "code,match",
    [
        ("out1 = sah(in1, in2, 0.5);", "Gen operator not implemented: sah"),
        ("while (1) { out1 = 1; }", "while"),
        ("if (in1) { out1 = 1; } else if (in1) { out1 = 2; }", "else if"),
        ("if (in1) out1 = 1;", "brace-less"),
        ("x = 0; x++; out1 = x;", r"\+\+"),
        ("out1 = !in1;", "'!'"),
        ("Data d(4); out1 = peek(d, 0, 0, 0);", "peek"),
        ("Data d(4); poke(d, 1, 0, 0, 0); out1 = 0;", "poke"),
        ("Delay d(4); out1 = d.read(1, 2); d.write(in1);", "read"),
    ],
    ids=[
        "sah", "while", "else-if", "braceless-if", "plusplus", "not",
        "peek-4-args", "poke-5-args", "read-2-args",
    ],
)
def test_unsupported_constructs(code, match):
    unsupported(code, match)


def test_math_safety():
    outs = run("out1 = sqrt(-1); out2 = log(0); out3 = pow(-2, 0.5); out4 = exp(1000);", n=1)
    v = [o[0] for o in outs]
    assert math.isnan(v[0])
    assert v[1] == -math.inf
    assert math.isnan(v[2])
    assert v[3] == math.inf


# ===========================================================================
# Parity with patches/bassoon-model/tools/genrun.py
# ===========================================================================


def _shipped_codebox() -> str:
    data = json.loads(_GENDSP.read_text())

    def walk(patcher):
        for entry in patcher.get("boxes", []):
            box = entry.get("box", {})
            if box.get("maxclass") == "codebox":
                return box["code"]
            inner = box.get("patcher")
            if inner:
                found = walk(inner)
                if found is not None:
                    return found
        return None

    code = walk(data["patcher"])
    assert code, f"no codebox found in {_GENDSP}"
    return code


@pytest.fixture(scope="module")
def genrun():
    """Import genrun.py in isolation (same pattern as test_bassoon-model.py)."""
    saved = {name: sys.modules.get(name) for name in ("core", "genrun")}
    for name in saved:
        sys.modules.pop(name, None)
    tools = str(_TOOLS)
    sys.path.insert(0, tools)
    try:
        yield importlib.import_module("genrun")
    finally:
        try:
            sys.path.remove(tools)
        except ValueError:
            pass
        for name, mod in saved.items():
            sys.modules.pop(name, None)
            if mod is not None:
                sys.modules[name] = mod


# Local copies of test_bassoon-model.py's parity dicts (codebox Params only).
_OFF = {
    "vib_depth": 0.0,
    "vib_amp": 0.0,
    "noise_amt": 0.0,
    "chiff_amt": 0.0,
    "drift_on": 0.0,
    "tongue_trig": 0.0,
}
_C_440_EXTREMES = {
    "bore_damp": 1.0, "register": 1.0, "bell_bright": 1.0,
    "reed_res_freq": 2500.0, "reed_res_q": 6.0, "reed_aper": 0.2,
    "attack_time": 3.0, "release_time": 100.0,
}


@pytest.mark.parametrize(
    "freq,breath,over",
    [
        pytest.param(220.0, 0.6, {}, id="a-codebox-defaults"),
        pytest.param(440.0, 0.45, {**_C_440_EXTREMES, **_OFF}, id="b-c-440Hz-extremes-off"),
    ],
)
def test_bassoon_parity_with_genrun(genrun, freq, breath, over):
    """The interpreter reproduces genrun sample for sample within 1e-12."""
    code = _shipped_codebox()
    dur = 0.1
    ref, _ = genrun.render(code, freq, lambda t: breath, dur=dur, seed=1, **over)
    n = ref.size
    got = parse_codebox(code).build(params=over, seed=1).run(
        [np.full(n, freq), np.full(n, breath)], n
    )[0]
    diff = np.abs(got - ref)
    bad = np.nonzero(~(diff <= 1e-12))[0]
    if bad.size:
        i = int(bad[0])
        pytest.fail(
            f"sample {i} differs by {diff[i]:.3e} "
            f"(interpreter {float(got[i])!r}, genrun {float(ref[i])!r})"
        )
    assert np.max(np.abs(ref)) > 1e-3, "genrun render is silent"
    assert np.max(np.abs(got)) > 1e-3, "interpreter render is silent"
