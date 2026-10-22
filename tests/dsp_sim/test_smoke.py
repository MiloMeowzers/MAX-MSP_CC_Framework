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
from src.maxpat.dsp_sim.smoke import smoke_codebox, smoke_file

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


# ===========================================================================
# Q35 acceptance (Task 3)
# ===========================================================================

_PATTERN_FILES = sorted((_REPO / "patterns" / "gen").glob("**/*.gendsp"))
# Phasor-domain patterns: bipolar noise at swing=min maps -0.1 to -5, so they
# get a 0..1 ramp on in1 (D-06; no verdict allowlist).
_PATTERN_INPUTS = {
    "swing-generator": {1: "phasor:2"},
    "subdivider": {1: "phasor:2"},
}
_BASSOON_GENDSP = _REPO / "patches" / "bassoon-model" / "generated" / "bassoon.gendsp"
_BASSOON_MAXPAT = _REPO / "patches" / "bassoon-model" / "generated" / "bassoon-model.maxpat"
_TERRAIN = _REPO / "patches" / "terrain-synth" / "generated" / "terrain-synth.maxpat"
_BASSOON_INPUTS = {1: "const:220", 2: "const:0.6"}


def test_pattern_glob_finds_19_files():
    assert len(_PATTERN_FILES) == 19, [p.name for p in _PATTERN_FILES]


@pytest.mark.parametrize("path", _PATTERN_FILES, ids=[p.stem for p in _PATTERN_FILES])
def test_pattern_passes(path):
    results = smoke_file(path, seconds=0.25, inputs=_PATTERN_INPUTS.get(path.stem, {}))
    assert results, path
    for r in results:
        detail = "\n".join(
            f"  {f.severity} {f.check} [{f.corner}] out{f.output}: {f.detail}"
            for f in r.findings
        )
        assert r.verdict == "pass", f"{r.label}: {r.verdict} {r.reason}\n{detail}"


def test_corners_default_runs_one_corner():
    (r,) = smoke_file(_PATTERN_FILES[0], seconds=0.1, corners="default")
    assert r.corners == 1


def test_bassoon_gendsp_runs():
    results = smoke_file(
        _BASSOON_GENDSP, seconds=0.1, corners="default", inputs=_BASSOON_INPUTS
    )
    assert len(results) == 1
    (r,) = results
    assert r.verdict != "unsupported", r.reason
    assert r.corners == 1
    assert not [f for f in r.findings if f.check == "nonfinite"], r.findings


def test_bassoon_maxpat_runs_through_sibling_gendsp():
    results = smoke_file(
        _BASSOON_MAXPAT, seconds=0.1, corners="default", inputs=_BASSOON_INPUTS
    )
    assert len(results) == 1, [r.label for r in results]
    (r,) = results
    assert "bassoon.gendsp" in r.label
    assert r.verdict != "unsupported", r.reason
    assert not [f for f in r.findings if f.check == "nonfinite"], r.findings


def _safe_gain_code() -> str:
    data = json.loads(_SAFE_GAIN.read_text())
    (code,) = [
        e["box"]["code"] for e in data["patcher"]["boxes"]
        if e["box"].get("maxclass") == "codebox"
    ]
    return code


def _maxpat(tmp_path: Path, name: str, boxes: list) -> Path:
    data = {"patcher": {"fileversion": 1, "boxes": [{"box": b} for b in boxes], "lines": []}}
    path = tmp_path / f"{name}.maxpat"
    path.write_text(json.dumps(data))
    return path


def test_non_codebox_gen_operator_is_unsupported(tmp_path, capsys):
    path = _gendsp(tmp_path, "mixed", _safe_gain_code(), extra_boxes=["* 0.5"])
    (r,) = smoke_file(path, seconds=0.1)
    assert r.verdict == "unsupported"
    assert "non-codebox" in r.reason and "* 0.5" in r.reason
    assert main(["smoke", str(path), "--seconds", "0.1"]) == 3


def test_embedded_gen_maxpat_is_discovered_and_passes(tmp_path):
    from src.maxpat import Patcher

    patcher = Patcher()
    patcher.add_gen(_safe_gain_code(), 1, 1)
    path = tmp_path / "embedded.maxpat"
    path.write_text(json.dumps(patcher.to_dict()))
    results = smoke_file(path, seconds=0.1)
    assert len(results) == 1
    assert results[0].verdict == "pass", results[0]
    assert "codebox 1" in results[0].label


def test_external_gendsp_not_found(tmp_path):
    path = _maxpat(tmp_path, "ext", [{"maxclass": "newobj", "text": "gen~ no-such-engine"}])
    (r,) = smoke_file(path, seconds=0.1)
    assert r.verdict == "unsupported"
    assert "external gendsp not found" in r.reason


@pytest.mark.parametrize(
    "text", ["gen~ ../evil", "gen~ sub/engine", "mc.gen~ @gen ../x.gendsp"],
    ids=["dotdot", "slash", "at-gen-dotdot"],
)
def test_external_gendsp_name_must_be_plain(tmp_path, text):
    path = _maxpat(tmp_path, "ext", [{"maxclass": "newobj", "text": text}])
    (r,) = smoke_file(path, seconds=0.1)
    assert r.verdict == "unsupported"
    assert "not a plain file name" in r.reason


def test_terrain_synth_discovery():
    from src.maxpat.dsp_sim.smoke import discover_codeboxes

    entries = discover_codeboxes(_TERRAIN)
    ok = [e for e in entries if e.status == "ok"]
    skipped = [e for e in entries if e.status == "skipped"]
    assert len(ok) == 4, [e.label for e in entries]
    assert len(skipped) == 2, [e.label for e in entries]
    assert all("jit.gen" in e.reason for e in skipped)
    assert len(entries) == 6


def test_maxpat_without_gen_exits_3(tmp_path, capsys):
    path = _maxpat(tmp_path, "plain", [
        {"maxclass": "newobj", "text": "cycle~ 440"},
        {"maxclass": "comment", "text": "gen~ not really"},
    ])
    assert main(["smoke", str(path), "--seconds", "0.1"]) == 3


def test_json_report(capsys):
    rc = main(["smoke", str(_SAFE_GAIN), "--seconds", "0.1", "--json"])
    report = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert set(report) >= {
        "path", "seconds", "samplerate", "seed", "corners", "exit_code", "codeboxes",
    }
    assert report["exit_code"] == 0
    (cb,) = report["codeboxes"]
    assert set(cb) >= {"label", "verdict", "reason", "corners", "findings"}
    assert cb["findings"], cb
    assert set(cb["findings"][0]) >= {"check", "severity", "corner", "output", "detail"}


def test_buffer_option_resizes_buffer(tmp_path, capsys):
    # dim 1000 and 2 channels -> out1 = 4.0 (passes); anything else peaks > 4.
    code = 'Buffer buf("bufname"); out1 = dim(buf) / 250 + (channels(buf) != 2) * 10;'
    path = _gendsp(tmp_path, "bufdim", code)
    assert main(["smoke", str(path), "--seconds", "0.1"]) == 1
    assert main(["smoke", str(path), "--seconds", "0.1", "--buffer", "bufname=1000:2"]) == 0
    (r,) = smoke_file(path, seconds=0.1, buffers={"bufname": (1000, 2)})
    assert r.verdict == "pass"
    # buffer-player's one-shot corner (loop=min) runs off the end of a
    # 1000-frame Buffer within 0.1 s. A finished one-shot player is correct
    # and the player has no inlets, so silence is not checked (WR-05; the
    # old assertion here expected a silence FAIL and encoded that bug).
    player = _REPO / "patterns" / "gen" / "buffer" / "buffer-player.gendsp"
    (r,) = smoke_file(player, seconds=0.1)
    assert r.verdict == "pass", r.findings
    (r,) = smoke_file(player, seconds=0.1, buffers={"bufname": (1000, 2)})
    assert r.verdict == "pass", r.findings
    assert not [f for f in r.findings if f.check == "silence"], r.findings
    capsys.readouterr()
    assert main(["smoke", str(player), "--seconds", "0.1", "--buffer", "bufname=1000:2"]) == 0


@pytest.mark.parametrize("spec", ["bufname=abc", "bufname=0", "nofmt", "bufname=10:0"])
def test_malformed_buffer_exits_2(spec, capsys):
    assert main(["smoke", str(_SAFE_GAIN), "--buffer", spec]) == 2


# ===========================================================================
# Guards: no string evaluation (T-urs-01) and no save gate (D-07)
# ===========================================================================

_DSP_SIM = _REPO / "src" / "maxpat" / "dsp_sim"


def test_no_string_evaluation_in_smoke_modules():
    import ast

    for name in ("genexpr_interp.py", "smoke.py", "cli.py"):
        tree = ast.parse((_DSP_SIM / name).read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in {"eval", "exec", "compile", "__import__"}, (
                    name, node.lineno, node.func.id,
                )
            if name != "cli.py" and isinstance(node, (ast.Import, ast.ImportFrom)):
                mods = (
                    [a.name for a in node.names] if isinstance(node, ast.Import)
                    else [node.module or ""]
                )
                assert not any(m.split(".")[0] == "importlib" for m in mods), (name, mods)


def test_smoke_is_not_imported_outside_dsp_sim():
    import ast

    banned = {"src.maxpat.dsp_sim.smoke", "src.maxpat.dsp_sim.genexpr_interp"}
    for path in sorted((_REPO / "src" / "maxpat").rglob("*.py")):
        if _DSP_SIM in path.parents:
            continue
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                names = [mod] + [f"{mod}.{a.name}" for a in node.names]
            else:
                continue
            assert not banned.intersection(names), (str(path), node.lineno, names)


# ===========================================================================
# Q35 review fixes (quick 261022-cmr)
# ===========================================================================

_CR01_IF_ELSE = "if (in1 > 0) {\n y = 1;\n} else {\n y = 0.5;\n}\nout1 = y * in1;"
_CR01_READ_FIRST = "out1 = y;\ny = in1;"


@pytest.mark.parametrize("code", [_CR01_IF_ELSE, _CR01_READ_FIRST], ids=["if-else", "read-first"])
def test_cr01_uninitialized_local_is_unsupported(code):
    r = smoke_codebox(code, seconds=0.1)
    assert r.verdict == "unsupported", (r.verdict, r.reason, r.findings)
    assert "local 'y'" in r.reason and r.corners == 0


def test_cr01_cli_exits_3(tmp_path, capsys):
    path = _gendsp(tmp_path, "cr01", _CR01_IF_ELSE)
    rc = main(["smoke", str(path), "--seconds", "0.1"])
    out = capsys.readouterr().out
    assert rc == 3, out
    assert "UNSUPPORTED" in out and "'y'" in out


@pytest.mark.parametrize(
    "code", ["ou1 = in1;", "Data d(10);\npoke(d, in1, 0, 0);"], ids=["typo", "poke-only"]
)
def test_cr02_zero_output_codebox_is_unsupported(code):
    r = smoke_codebox(code, seconds=0.1)
    assert r.verdict == "unsupported", (r.verdict, r.reason, r.findings)
    assert "no outN outputs" in r.reason
    assert r.corners == 0


def test_cr02_cli_exits_3(tmp_path, capsys):
    path = _gendsp(tmp_path, "cr02", "ou1 = in1;")
    rc = main(["smoke", str(path), "--seconds", "0.1"])
    out = capsys.readouterr().out
    assert rc == 3, out


@pytest.mark.parametrize(
    "code,name",
    [("out1 = in1; ou2 = in1 * 2;", "ou2"), ("Out1 = in1; out1 = in1;", "Out1")],
)
def test_cr02_output_typo_warns(code, name):
    r = smoke_codebox(code, seconds=0.1)
    assert r.verdict == "pass", r.findings
    typos = [f for f in r.findings if f.check == "output_typo"]
    assert len(typos) == 1, r.findings
    assert typos[0].severity == "warn" and typos[0].corner == "build"
    assert f"'{name}'" in typos[0].detail


def test_cr02_no_output_typo_for_ordinary_locals():
    r = smoke_codebox("t1 = in1; out1 = t1;", seconds=0.1)
    assert not [f for f in r.findings if f.check == "output_typo"], r.findings


def test_wr03_tab_char_warns(tmp_path, capsys):
    r = smoke_codebox("out1 =\tin1 * 0.5;", seconds=0.1)
    assert r.verdict == "pass", r.findings
    tabs = [f for f in r.findings if f.check == "tab_char"]
    assert len(tabs) == 1 and tabs[0].severity == "warn" and "line 1" in tabs[0].detail
    path = _gendsp(tmp_path, "tab", "out1 =\tin1 * 0.5;")
    rc = main(["smoke", str(path), "--seconds", "0.1"])
    out = capsys.readouterr().out
    assert rc == 0, out
    assert "WARN tab_char" in out


_WR01_PROBE = (
    "Param g(1, min=0, max=200000); out1 = in1/0*0 + pow(10,400); "
    "for (i = 0; i < g; i += 1) { out1 += 0; }"
)


def test_wr01_corner_error_keeps_fail(tmp_path, capsys):
    """WR-01: an interpreter error at one corner no longer discards FAILs."""
    r = smoke_codebox(_WR01_PROBE, seconds=0.1)
    assert r.verdict == "fail", (r.verdict, r.reason, r.findings)
    assert any(f.check == "nonfinite" and f.severity == "fail" and f.corner == "default"
               for f in r.findings), r.findings
    errs = [f for f in r.findings if f.severity == "unsupported"]
    assert len(errs) == 1, r.findings
    assert errs[0].check == "unsupported" and errs[0].corner == "g=max (200000)"
    assert "100000 iterations" in errs[0].detail
    assert r.corners == 2
    assert "unsupported at 1 corner(s)" in r.reason
    path = _gendsp(tmp_path, "wr01", _WR01_PROBE)
    rc = main(["smoke", str(path), "--seconds", "0.1"])
    out = capsys.readouterr().out
    assert rc == 1, out
    assert "UNSUPPORTED [g=max (200000)]" in out


def test_wr01_partial_error_without_fail_is_unsupported():
    r = smoke_codebox(
        "Param g(1, min=0, max=200000); out1 = in1 * 0.5; "
        "for (i = 0; i < g; i += 1) { out1 += 0; }",
        seconds=0.1,
    )
    assert r.verdict == "unsupported", (r.verdict, r.reason, r.findings)
    assert "1 of 3 corners" in r.reason
    assert r.corners == 2


def test_wr01_identical_errors_collapse_to_all_corners():
    r = smoke_codebox("Param a(1, min=0, max=2); out1 = frobnicate(in1) * a;", seconds=0.1)
    assert r.verdict == "unsupported"
    errs = [f for f in r.findings if f.check == "unsupported"]
    assert [(f.severity, f.corner) for f in errs] == [("unsupported", "all corners")], r.findings
    assert r.reason == "unsupported: unknown function: frobnicate (line 1)"
    assert r.corners == 0


def test_wr04_param_default_clamped_in_smoke():
    r = smoke_codebox("Param p(min=0.5, max=1); out1 = in1 / p;", seconds=0.1)
    assert r.verdict == "pass", r.findings
    assert r.corners == 2
    assert not [f for f in r.findings if f.check == "silent"], r.findings


def test_wr05_zero_inlet_decay_passes(tmp_path, capsys):
    code = "History h(1); out1 = h; h = h * 0.99;"
    r = smoke_codebox(code, seconds=0.1)
    assert r.verdict == "pass", r.findings
    assert not [f for f in r.findings if f.check == "silence"]
    path = _gendsp(tmp_path, "decay", code)
    assert main(["smoke", str(path), "--seconds", "0.1"]) == 0


def test_wr05_const_driven_dc_blocker_passes():
    r = smoke_codebox(
        "History x1(0); History y1(0); y = in1 - x1 + 0.99 * y1; x1 = in1; y1 = y; out1 = y;",
        seconds=0.1, inputs={1: "const:1"},
    )
    assert r.verdict == "pass", r.findings
    assert not [f for f in r.findings if f.check == "silence"]


def test_wr05_silence_still_fails_while_input_active():
    """Positive control: silent while the default noise still runs."""
    r = smoke_codebox("History n(0); n = n + 1; out1 = in1 * (n < 2000);", seconds=0.25)
    assert r.verdict == "fail"
    sil = [f for f in r.findings if f.check == "silence" and f.corner == "default"]
    assert sil and sil[0].severity == "fail", r.findings
    assert sil[0].detail.endswith("while an input is still changing")


def test_wr06_unused_input_warns(tmp_path, capsys):
    r = smoke_codebox("out1 = in1;", seconds=0.1, inputs={5: "const:1"})
    assert r.verdict == "pass", r.findings
    unused = [f for f in r.findings if f.check == "unused_input"]
    assert len(unused) == 1 and unused[0].severity == "warn" and unused[0].corner == "build"
    assert "--input 5=const:1" in unused[0].detail and "1 inlet" in unused[0].detail
    r = smoke_codebox("out1 = in1;", seconds=0.1, inputs={1: "const:1"})
    assert not [f for f in r.findings if f.check == "unused_input"]
    path = _gendsp(tmp_path, "unused", "out1 = in1;")
    rc = main(["smoke", str(path), "--seconds", "0.1", "--input", "5=const:1"])
    out = capsys.readouterr().out
    assert rc == 0, out
    assert "WARN unused_input" in out
