"""Build-time lint fixes from the 261022-ud6 dsp_sim review (IN-01, IN-02).

IN-01: the codebox safe-construct rules in genexpr-rules.md (constant for
bounds, no local aliases in Param-only expressions, peek/poke with an explicit
channel) surface as WARNs. IN-02: output_typo only fires on a local that is
never read.
"""

from __future__ import annotations

import pytest

from src.maxpat.dsp_sim.genexpr_interp import parse_codebox
from src.maxpat.dsp_sim.smoke import smoke_codebox


def _lint(code: str) -> dict:
    out: dict = {}
    for check, detail in parse_codebox(code).lint:
        out.setdefault(check, []).append(detail)
    return out


# ---------------------------------------------------------------------------
# IN-02: output_typo
# ---------------------------------------------------------------------------


def test_in02_read_locals_are_not_output_typos():
    lint = _lint("cut1 = in1; oct2 = in1 * 0.5; out1 = cut1 + oct2;")
    assert "output_typo" not in lint, lint


def test_in02_unread_typo_still_warns():
    lint = _lint("ou2 = in1 * 0.5; out1 = in1;")
    assert len(lint["output_typo"]) == 1
    assert "'ou2'" in lint["output_typo"][0]


def test_in02_read_only_in_a_loop_condition_counts_as_read():
    lint = _lint("ot1 = 4; s = 0; for (i = 0; i < 4; i += 1) { s += in1 * ot1; } out1 = s;")
    assert "output_typo" not in lint, lint


# ---------------------------------------------------------------------------
# IN-01: loop_bound_param
# ---------------------------------------------------------------------------


def test_in01_param_loop_bound_warns():
    code = (
        "Param taps(4, min=1, max=8);\n"
        "s = 0;\n"
        "for (i = 0; i < taps; i += 1) {\n"
        "    s += in1;\n"
        "}\n"
        "out1 = s * 0.1;\n"
    )
    lint = _lint(code)
    (detail,) = lint["loop_bound_param"]
    assert "line 3" in detail and "'taps'" in detail
    r = smoke_codebox(code, seconds=0.05)
    assert r.verdict == "pass", r.findings      # a WARN, never a verdict change
    assert [f.severity for f in r.findings if f.check == "loop_bound_param"] == ["warn"]


def test_in01_samplerate_loop_bound_warns():
    lint = _lint("s = 0; for (i = 0; i < samplerate / 1000; i += 1) { s += 1; } out1 = in1 * s;")
    assert "'samplerate'" in lint["loop_bound_param"][0]


def test_in01_constant_loop_bound_is_clean():
    lint = _lint("s = 0; for (i = 0; i < 8; i += 1) { s += in1; } out1 = s;")
    assert "loop_bound_param" not in lint, lint


# ---------------------------------------------------------------------------
# IN-01: hoist_alias
# ---------------------------------------------------------------------------


def test_in01_local_alias_in_param_only_expression_warns():
    code = "Param ms(10, min=1, max=100);\nsr = samplerate;\nn = ms * 0.001 * sr;\nout1 = in1 * n * 0.0001;\n"
    (detail,) = _lint(code)["hoist_alias"]
    assert "'sr'" in detail and "line 3" in detail


def test_in01_constant_alias_warns():
    """genexpr-rules.md names RING = 1344000; next to sr = samplerate;."""
    code = "Param ms(10, min=1, max=100); RING = 1344000; n = min(ms * 44.1, RING); out1 = in1 * n * 1e-7;"
    assert "'RING'" in _lint(code)["hoist_alias"][0]


@pytest.mark.parametrize("code", [
    # computed Param-only setup locals: kicksynth (tanh_drive) and FDNVerb
    # (frz) do this and are user-confirmed compiling
    "Param g(1, min=0, max=2); a = g * 2; b = a + 1; out1 = in1 * b;",
    "Param drive(1, min=1, max=10); td = tanh(drive); out1 = tanh(drive * in1) / max(td, 0.001);",
    # an alias inside a per-sample statement (the bassoon jit_fc pattern)
    "History one(1); fc = 0.7; srs = samplerate * one; a = 1 - exp(-TWOPI * fc / srs); out1 = in1 * a;",
    # the de-hoist pattern from genexpr-rules.md
    "Param ms(10, min=1, max=100); History one(1); srs = samplerate * one; "
    "n = ms * 0.001 * srs; out1 = in1 * n * 0.0001;",
    # a Param-only local read as a leaf in a per-sample expression
    "Param g(0, min=-12, max=12); gg = pow(10, g / 20); out1 = in1 * gg;",
    # samplerate written directly (the kicksynth pattern)
    "Param decay(100, min=1, max=1000); out1 = in1 * max(decay * 0.001 * samplerate, 1) * 0.00001;",
])
def test_in01_hoist_safe_forms_are_clean(code):
    assert "hoist_alias" not in _lint(code)


# ---------------------------------------------------------------------------
# IN-01: implicit_channel
# ---------------------------------------------------------------------------


def test_in01_channel_less_peek_and_poke_warn():
    lint = _lint("Data d(10);\npoke(d, in1, 0);\nout1 = peek(d, 0);\n")
    (detail,) = lint["implicit_channel"]
    assert "peek()" in detail and "poke()" in detail and "line 2" in detail


def test_in01_explicit_channel_is_clean():
    assert "implicit_channel" not in _lint(
        "Data d(10); poke(d, in1, 0, 0); out1 = peek(d, 0, 0);"
    )
