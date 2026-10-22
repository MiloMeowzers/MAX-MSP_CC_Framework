"""GenExpr codebox smoke test (Q35, quick 261021-urs).

`python -m src.maxpat.dsp_sim smoke` runs every gen~ codebox at the Param
corners through src/maxpat/dsp_sim/genexpr_interp.py and reports NaN/inf,
peak > 4, permanent silence and self-sustain (FAIL) plus DC (WARN).
Unsupported never passes. Fixtures are written to tmp_path only.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.maxpat import generate_gendsp
from src.maxpat.dsp_sim.cli import main
from src.maxpat.dsp_sim.smoke import smoke_file

_REPO = Path(__file__).resolve().parents[2]
_SAFE_GAIN = _REPO / "patterns" / "gen" / "gain" / "safe-gain.gendsp"


def _gendsp(tmp_path: Path, name: str, code: str, extra_boxes=()) -> Path:
    """Write a .gendsp holding ``code`` (plus extra newobj boxes) to tmp_path."""
    data = generate_gendsp(code)
    boxes = data["patcher"]["boxes"]
    for k, text in enumerate(extra_boxes):
        boxes.append({"box": {
            "maxclass": "newobj", "text": text, "id": f"obj-extra-{k}",
            "numinlets": 2, "numoutlets": 1, "outlettype": [""],
            "patching_rect": [200.0, 200.0 + 30 * k, 50.0, 22.0],
        }})
    path = tmp_path / f"{name}.gendsp"
    path.write_text(json.dumps(data))
    return path


# ===========================================================================
# Tracer (Task 1)
# ===========================================================================


def test_safe_gain_pattern_passes(capsys):
    rc = main(["smoke", str(_SAFE_GAIN), "--seconds", "0.25"])
    out = capsys.readouterr().out
    assert rc == 0, out
    assert "PASS" in out


def test_report_names_failing_corner(tmp_path, capsys):
    """D-02: the peak FAIL is reported at gain=max only."""
    path = _gendsp(tmp_path, "gain", "Param gain(1, min=0, max=100); out1 = in1 * gain;")
    rc = main(["smoke", str(path), "--seconds", "0.25"])
    out = capsys.readouterr().out
    assert rc == 1, out
    (res,) = smoke_file(path, seconds=0.25)
    assert res.verdict == "fail"
    peaks = [f for f in res.findings if f.check == "peak"]
    assert [f.corner for f in peaks] == ["gain=max (100)"], peaks
    assert all(f.severity == "fail" for f in peaks)
    assert "FAIL peak [gain=max (100)] out1" in out


def test_dc_is_warn_not_fail(tmp_path, capsys):
    """D-06: a DC offset warns, it never fails."""
    path = _gendsp(tmp_path, "dc", "out1 = in1 + 0.5;")
    rc = main(["smoke", str(path), "--seconds", "0.25"])
    out = capsys.readouterr().out
    assert rc == 0, out
    (res,) = smoke_file(path, seconds=0.25)
    assert res.verdict == "pass"
    assert any(f.check == "dc" and f.severity == "warn" for f in res.findings)
    assert "WARN dc" in out


def test_unknown_function_is_unsupported(tmp_path, capsys):
    path = _gendsp(tmp_path, "unknown", "out1 = frobnicate(in1);")
    rc = main(["smoke", str(path), "--seconds", "0.25"])
    out = capsys.readouterr().out
    assert rc == 3, out
    assert "UNSUPPORTED" in out
    assert "frobnicate" in out


@pytest.mark.parametrize(
    "extra",
    [["--seconds", "0"], ["--input", "1=bogus:3"]],
    ids=["seconds-zero", "bogus-input"],
)
def test_bad_arguments_exit_2(extra, capsys):
    assert main(["smoke", str(_SAFE_GAIN)] + extra) == 2


def test_missing_file_exits_2(tmp_path, capsys):
    assert main(["smoke", str(tmp_path / "nope.gendsp")]) == 2


def test_legacy_help_still_lists_topology(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "--topology" in out
    assert "smoke" in out


# ===========================================================================
# Ring-out checks (Task 2): self-sustain (D-05) and dc latch (D-06)
# ===========================================================================

# The real bug class: tanh(x*g)/tanh(g) normalisation inside a feedback loop
# (genexpr-rules.md "In-loop saturation"). Its small-signal loop gain is
# feedback * drive / tanh(drive), above unity at the default corner.
_HISTORY_LATCH = """\
Param drive(4, min=1, max=10);
Param feedback(0.6, min=0, max=0.95);
History y(0);
y = tanh((in1 - feedback * y) * drive) / tanh(drive);
out1 = y;
"""

_UNSTABLE_DELAY = """\
Param drive(4, min=1, max=10);
Param feedback(0.6, min=0, max=0.95);
Delay d(4410);
tap = d.read(441);
sat = tanh(tap * drive) / tanh(drive);
d.write(in1 + feedback * sat);
out1 = tap;
"""

_STABLE_TWIN = _UNSTABLE_DELAY.replace(
    "sat = tanh(tap * drive) / tanh(drive);", "sat = tanh(tap * drive) / drive;"
)


def _sustain_corners(res) -> list:
    return [f.corner for f in res.findings if f.check == "self_sustain"]


def _assert_sustain_pattern(res) -> None:
    corners = _sustain_corners(res)
    for prefix in ("default", "drive=max", "feedback=max"):
        assert any(c.startswith(prefix) for c in corners), (prefix, res.findings)
    for prefix in ("drive=min", "feedback=min"):
        assert not any(c.startswith(prefix) for c in corners), (prefix, res.findings)
    assert all(
        f.severity == "fail" for f in res.findings if f.check == "self_sustain"
    )


def test_history_latch_fails_self_sustain(tmp_path, capsys):
    path = _gendsp(tmp_path, "latch", _HISTORY_LATCH)
    rc = main(["smoke", str(path), "--seconds", "0.25"])
    out = capsys.readouterr().out
    assert rc == 1, out
    (res,) = smoke_file(path, seconds=0.25)
    assert res.verdict == "fail"
    _assert_sustain_pattern(res)


def test_tanh_over_tanh_delay_fixture_fails_self_sustain(tmp_path, capsys):
    """The required unstable fixture FAILs at the 1 s default (D-05)."""
    assert "tanh(tap * drive) / tanh(drive)" in _UNSTABLE_DELAY
    path = _gendsp(tmp_path, "unstable", _UNSTABLE_DELAY)
    (res,) = smoke_file(path)
    assert res.verdict == "fail"
    _assert_sustain_pattern(res)
    assert main(["smoke", str(path)]) == 1


def test_stable_twin_passes(tmp_path, capsys):
    path = _gendsp(tmp_path, "stable", _STABLE_TWIN)
    (res,) = smoke_file(path)
    assert res.verdict == "pass", res.findings
    assert main(["smoke", str(path)]) == 0


@pytest.mark.parametrize(
    "kwargs,argv",
    [
        ({"inputs": {1: "const:0.1"}}, ["--input", "1=const:0.1"]),
        ({"ringout": False}, ["--no-ringout"]),
    ],
    ids=["const-input", "no-ringout"],
)
def test_ringout_needs_default_stimulus(tmp_path, capsys, kwargs, argv):
    """Documented limit: an override or --no-ringout disables self_sustain."""
    path = _gendsp(tmp_path, "unstable", _UNSTABLE_DELAY)
    (res,) = smoke_file(path, seconds=0.25, **kwargs)
    assert _sustain_corners(res) == [], res.findings
    main(["smoke", str(path), "--seconds", "0.25"] + argv)
    assert "self_sustain" not in capsys.readouterr().out


def test_dc_latch_warns_and_passes(tmp_path):
    path = _gendsp(tmp_path, "dc", "out1 = in1 + 0.5;")
    (res,) = smoke_file(path, seconds=0.25)
    assert res.verdict == "pass"
    latch = [f for f in res.findings if f.check == "dc" and "dc latch" in f.detail]
    assert latch and all(f.severity == "warn" for f in latch)
