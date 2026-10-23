"""Smoke-test fixes from the 261022-ud6 dsp_sim review.

CR-01: each codebox output's kind (audio / control) is inferred from the
host patch graph; control outputs get only the finite / denormal checks.
Trigger inlets get a gate stimulus. WR-01: mc.gen~ codeboxes saved under
box["data"]["patcher"] are smoked. WR-03: a gate or one-shot that goes
silent once the input drops is not a FAIL. IN-03: --seed is validated.
IN-06: jit.gen without an embedded patcher is reported as skipped.
Fixtures are written to tmp_path only.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.maxpat import generate_gendsp
from src.maxpat.dsp_sim.cli import main
from src.maxpat.dsp_sim.smoke import smoke_codebox, smoke_file

# A codebox whose output is a frequency in Hz (the minitaur p filter shape):
# 20 Hz .. 20 kHz, so any input above ~0.07 peaks over 4.
_HZ = "out1 = 20.0 * pow(1000, clamp(in1, 0, 1));"

# A trigger-driven decay (the kicksynth shape): every rising edge of in1
# adds 1 to the envelope. Noise on in1 retriggers it every few samples, so
# the envelope piles up past 4 and sustains at 0.01x input.
_KICK = (
    "History env(0);\n"
    "History prev(0);\n"
    "trig = (in1 > 0) * (prev <= 0);\n"
    "prev = in1;\n"
    "env = env * 0.9995 + trig;\n"
    "out1 = env * 0.9;\n"
)


# ---------------------------------------------------------------------------
# Patch builders
# ---------------------------------------------------------------------------


def _box(bid, text=None, maxclass="newobj", outlettype=None, x=0.0, **extra):
    box = {"id": bid, "maxclass": maxclass, "patching_rect": [x, 0.0, 60.0, 22.0]}
    if text is not None:
        box["text"] = text
    if outlettype is not None:
        box["outlettype"] = outlettype
    box.update(extra)
    return box


def _gen(bid, code, text="gen~", n_out=1, x=0.0):
    data = generate_gendsp(code)
    return _box(bid, text, outlettype=["signal"] * n_out, x=x, patcher=data["patcher"])


def _line(src, so, dst, di):
    return {"patchline": {"source": [src, so], "destination": [dst, di]}}


def _patcher(boxes, lines):
    return {"boxes": [{"box": b} for b in boxes], "lines": list(lines)}


def _write(tmp_path: Path, name: str, boxes, lines) -> Path:
    path = tmp_path / name
    path.write_text(json.dumps({"patcher": _patcher(boxes, lines)}))
    return path


def _gendsp(tmp_path: Path, name: str, code: str) -> Path:
    path = tmp_path / f"{name}.gendsp"
    path.write_text(json.dumps(generate_gendsp(code)))
    return path


def _only(results):
    (r,) = [r for r in results if r.verdict != "skipped"]
    return r


def _checks(r, severity=None):
    return [f.check for f in r.findings if severity is None or f.severity == severity]


# ---------------------------------------------------------------------------
# CR-01: output kinds from the host graph
# ---------------------------------------------------------------------------


def test_cr01_hz_output_to_snapshot_is_control_and_passes(tmp_path):
    path = _write(tmp_path, "hz.maxpat", [
        _box("src", "line~", outlettype=["signal", "bang"]),
        _gen("gen", _HZ),
        _box("snap", "snapshot~ 50", outlettype=["float"]),
    ], [_line("src", 0, "gen", 0), _line("gen", 0, "snap", 0)])
    r = _only(smoke_file(path, seconds=0.1))
    assert r.verdict == "pass", r.findings
    assert r.outputs == {1: "control"}
    assert "peak" not in _checks(r)
    assert "snapshot~" in r.port_notes["out1"]


def test_cr01_same_code_to_dac_keeps_the_peak_fail(tmp_path):
    path = _write(tmp_path, "hzdac.maxpat", [
        _gen("gen", _HZ),
        _box("dac", "dac~"),
    ], [_line("gen", 0, "dac", 0)])
    r = _only(smoke_file(path, seconds=0.1))
    assert r.outputs == {1: "audio"}
    assert r.verdict == "fail"
    assert "peak" in _checks(r, "fail")


def test_cr01_standalone_gendsp_defaults_to_audio(tmp_path):
    r = _only(smoke_file(_gendsp(tmp_path, "lonely", _HZ), seconds=0.1))
    assert r.verdict == "fail" and "peak" in _checks(r, "fail")
    assert r.outputs == {1: "audio"}


@pytest.mark.parametrize("chain,lines,kind", [
    # *~ left inlet is the gain stage on the way to the dac
    ([_box("g", "*~ 0.5", outlettype=["signal"]), _box("dac", "dac~")],
     [_line("gen", 0, "g", 0), _line("g", 0, "dac", 0)], "audio"),
    # *~ right inlet is a modulator (the gen output is the gain)
    ([_box("g", "*~", outlettype=["signal"]), _box("dac", "dac~")],
     [_line("gen", 0, "g", 1), _line("g", 0, "dac", 0)], "control"),
    # a frequency into cycle~
    ([_box("osc", "cycle~", outlettype=["signal"]), _box("dac", "dac~")],
     [_line("gen", 0, "osc", 0), _line("osc", 0, "dac", 0)], "control"),
    # a cutoff into lores~ inlet 1
    ([_box("f", "lores~", outlettype=["signal"]), _box("dac", "ezdac~", maxclass="ezdac~")],
     [_line("gen", 0, "f", 1), _line("f", 0, "dac", 0)], "control"),
    # send~ -> receive~ -> dac~
    ([_box("s", "send~ bus"), _box("r", "receive~ bus", outlettype=["signal"]), _box("dac", "dac~")],
     [_line("gen", 0, "s", 0), _line("r", 0, "dac", 0)], "audio"),
    # send~ -> receive~ -> second gen~ inlet 2 (the minitaur glide shape)
    ([_box("s", "send~ hz"), _box("r", "receive~ hz", outlettype=["signal"]),
      _gen("gen2", "out1 = in1 * in2 * 0;"), _box("dac", "dac~")],
     [_line("gen", 0, "s", 0), _line("r", 0, "gen2", 1), _line("gen2", 0, "dac", 0)], "control"),
    # the next gen~'s first inlet passes audio on
    ([_gen("gen2", "out1 = in1 * 0.5;"), _box("dac", "dac~")],
     [_line("gen", 0, "gen2", 0), _line("gen2", 0, "dac", 0)], "audio"),
    # gain~ UI object
    ([_box("gain", maxclass="gain~", outlettype=["signal", ""])],
     [_line("gen", 0, "gain", 0)], "audio"),
    # unconnected outlet
    ([], [], "control"),
])
def test_cr01_downstream_rules(tmp_path, chain, lines, kind):
    path = _write(tmp_path, "rules.maxpat", [_gen("gen", "out1 = in1 * 0.5;")] + chain, lines)
    results = smoke_file(path, seconds=0.05, corners="default")
    r = next(x for x in results if x.label.endswith("gen~ > codebox 1"))
    assert r.outputs == {1: kind}, r.port_notes


@pytest.mark.parametrize("downstream,inlet,kind", [
    # stereo limiter: in2 -> out2 -> dac~ (the stutter right channel)
    ("out1 = in1 * 0.5; out2 = in2 * 0.5;", 1, "audio"),
    # one-outlet filter: a frequency into in2 is a coefficient
    ("History y(0); g = clamp(in2 / 20000, 0, 1); y = y + g * (in1 - y); out1 = y;", 1, "control"),
    # sample player: in1 is a trigger read only in a condition, in2 an index
    ("Data d(100); History p(0); if (in1 > 0) { p = in2; } out1 = peek(d, p, 0); "
     "out2 = peek(d, p + 1, 0);", 0, "control"),
    ("Data d(100); History p(0); if (in1 > 0) { p = in2; } out1 = peek(d, p, 0); "
     "out2 = peek(d, p + 1, 0);", 1, "control"),
    # a mono effect: in1 passes on
    ("out1 = tanh(in1 * 2) * 0.5;", 0, "audio"),
])
def test_cr01_downstream_gen_routes_by_value_dataflow(tmp_path, downstream, inlet, kind):
    path = _write(tmp_path, "route.maxpat", [
        _gen("src", "out1 = in1 * 0.5;"),
        _gen("dst", downstream, n_out=2, x=200.0),
        _box("dac", "dac~"),
    ], [_line("src", 0, "dst", inlet), _line("dst", 0, "dac", 0), _line("dst", 1, "dac", 1)])
    results = smoke_file(path, seconds=0.05, corners="default")
    r = next(x for x in results if x.label == "route.maxpat > gen~ > codebox 1")
    assert r.outputs == {1: kind}, r.port_notes


def test_cr01_subpatcher_outlet_is_traced_to_the_parent(tmp_path):
    inner = _patcher([
        _gen("gen", _HZ),
        _box("out", maxclass="outlet"),
    ], [_line("gen", 0, "out", 0)])
    path = _write(tmp_path, "sub.maxpat", [
        _box("p", "p inner", outlettype=["signal"], patcher=inner),
        _box("snap", "snapshot~", outlettype=["float"]),
        _box("dac", "dac~"),
    ], [_line("p", 0, "snap", 0)])
    r = _only(smoke_file(path, seconds=0.05))
    assert r.outputs == {1: "control"} and r.verdict == "pass", r.findings


def test_cr01_abstraction_outlet_without_host_is_audio(tmp_path):
    path = _write(tmp_path, "abs-x.maxpat", [
        _box("in", maxclass="inlet"),
        _gen("gen", _HZ),
        _box("out", maxclass="outlet"),
    ], [_line("in", 0, "gen", 0), _line("gen", 0, "out", 0)])
    r = _only(smoke_file(path, seconds=0.05))
    assert r.outputs == {1: "audio"} and r.verdict == "fail"
    assert "no host" in r.port_notes["out1"]


def test_cr01_abstraction_ports_resolve_through_a_sibling_host(tmp_path):
    abs_path = _write(tmp_path, "abs-x.maxpat", [
        _box("in", maxclass="inlet"),
        _gen("gen", _HZ),
        _box("out", maxclass="outlet"),
    ], [_line("in", 0, "gen", 0), _line("gen", 0, "out", 0)])
    _write(tmp_path, "host.maxpat", [
        _box("sig", "sig~ 0.5", outlettype=["signal"]),
        _box("a", "abs-x", outlettype=["signal"]),
        _box("snap", "snapshot~", outlettype=["float"]),
    ], [_line("sig", 0, "a", 0), _line("a", 0, "snap", 0)])
    r = _only(smoke_file(abs_path, seconds=0.05))
    assert r.outputs == {1: "control"} and r.inputs == {1: "control"}, r.port_notes
    assert r.verdict == "pass", r.findings


def test_cr01_gendsp_uses_its_sibling_host(tmp_path):
    eng = _gendsp(tmp_path, "eng", _HZ)
    _write(tmp_path, "host.maxpat", [
        _box("gen", "gen~ eng", outlettype=["signal"]),
        _box("snap", "snapshot~ 50", outlettype=["float"]),
    ], [_line("gen", 0, "snap", 0)])
    r = _only(smoke_file(eng, seconds=0.05))
    assert r.outputs == {1: "control"} and r.verdict == "pass", r.findings
    assert "host.maxpat" in r.port_host


def test_cr01_control_output_still_fails_nonfinite(tmp_path):
    path = _write(tmp_path, "nan.maxpat", [
        _gen("gen", "out1 = pow(10, 400) * in1;"),
        _box("snap", "snapshot~", outlettype=["float"]),
    ], [_line("gen", 0, "snap", 0)])
    r = _only(smoke_file(path, seconds=0.05))
    assert r.outputs == {1: "control"}
    assert r.verdict == "fail" and "nonfinite" in _checks(r, "fail")


# ---------------------------------------------------------------------------
# CR-01: // smoke: directives
# ---------------------------------------------------------------------------


def test_cr01_directive_control_out_passes_standalone():
    r = smoke_codebox("// smoke: control out1\n" + _HZ, seconds=0.1)
    assert r.verdict == "pass", r.findings
    assert r.outputs == {1: "control"}


def test_cr01_directive_audio_out_overrides_the_host(tmp_path):
    path = _write(tmp_path, "force.maxpat", [
        _gen("gen", "// smoke: audio out1\n" + _HZ),
        _box("snap", "snapshot~", outlettype=["float"]),
    ], [_line("gen", 0, "snap", 0)])
    r = _only(smoke_file(path, seconds=0.05))
    assert r.outputs == {1: "audio"} and r.verdict == "fail"


def test_cr01_directive_inlet_spec_and_trigger():
    r = smoke_codebox("// smoke: in1=phasor:2 control out1\n" + _HZ, seconds=0.1)
    assert r.verdict == "pass", r.findings
    r = smoke_codebox("// smoke: trigger in1\n" + _KICK, seconds=0.25)
    assert r.inputs == {1: "trigger"}
    assert r.verdict == "pass", r.findings


def test_cr01_bad_directive_warns():
    r = smoke_codebox("// smoke: loud out1 out7\nout1 = in1;", seconds=0.05)
    warns = [f for f in r.findings if f.check == "smoke_directive"]
    assert warns and all(f.severity == "warn" for f in warns)
    assert "'loud'" in warns[0].detail
    assert r.verdict == "pass"


# ---------------------------------------------------------------------------
# CR-01: trigger / control / unconnected inlets
# ---------------------------------------------------------------------------


def test_cr01_kick_with_noise_on_its_trigger_inlet_fails():
    """Positive control: the old stimulus false-fails a trigger inlet."""
    r = smoke_codebox(_KICK, seconds=0.25)
    assert r.verdict == "fail"


def test_cr01_click_driven_trigger_inlet_gets_a_gate_and_passes(tmp_path):
    path = _write(tmp_path, "kick.maxpat", [
        _box("click", "click~", outlettype=["signal"]),
        _gen("gen", _KICK),
        _box("dac", "dac~"),
    ], [_line("click", 0, "gen", 0), _line("gen", 0, "dac", 0)])
    r = _only(smoke_file(path, seconds=0.25))
    assert r.inputs == {1: "trigger"} and r.outputs == {1: "audio"}
    assert r.verdict == "pass", r.findings
    assert "self_sustain" not in _checks(r)


def test_cr01_unconnected_and_message_only_inlets_are_zero(tmp_path):
    path = _write(tmp_path, "zero.maxpat", [
        _box("msg", "prepend gain", outlettype=[""]),
        _gen("gen", "Param gain(1, min=0, max=2); out1 = in1 * gain + in2;"),
        _box("dac", "dac~"),
    ], [_line("msg", 0, "gen", 0), _line("gen", 0, "dac", 0)])
    r = _only(smoke_file(path, seconds=0.05))
    assert r.inputs == {1: "zero", 2: "zero"}, r.port_notes


def test_cr01_control_inlet_is_not_scaled_in_the_self_sustain_rerun(tmp_path):
    """A sig~-driven oscillator frequency is control: with no audio inlet the
    codebox is a generator and self_sustain is not judged."""
    osc = "History ph(0); ph = wrap(ph + in1 / samplerate, 0, 1); out1 = sin(TWOPI * ph) * 0.5 + 0 * in1;"
    path = _write(tmp_path, "osc.maxpat", [
        _box("sig", "sig~ 220", outlettype=["signal"]),
        _gen("gen", osc),
        _box("dac", "dac~"),
    ], [_line("sig", 0, "gen", 0), _line("gen", 0, "dac", 0)])
    r = _only(smoke_file(path, seconds=0.1))
    assert r.inputs == {1: "control"}
    assert "self_sustain" not in _checks(r), r.findings


def test_cr01_audio_inlet_self_sustain_still_fails():
    """Positive control kept: the tanh/tanh(g) Delay loop on an audio inlet,
    also when the host graph marks its inlet audio and a second inlet trigger."""
    from tests.dsp_sim.test_smoke import _UNSTABLE_DELAY

    r = smoke_codebox(_UNSTABLE_DELAY, seconds=0.25)
    assert "self_sustain" in _checks(r, "fail"), r.findings
    from src.maxpat.dsp_sim.host_graph import PortKinds

    ports = PortKinds(inputs={1: "audio"}, outputs={1: "audio"}, host="h.maxpat")
    r = smoke_codebox(_UNSTABLE_DELAY, seconds=0.25, ports=ports)
    assert "self_sustain" in _checks(r, "fail"), r.findings


def test_cr01_buffer_backing_scales_in_the_self_sustain_rerun():
    """A looping Buffer player is not a latched loop: its backing scales too."""
    code = 'Buffer b("bb"); History ph(0); ph = (ph + 1) % 48000; out1 = in1 * 0.5 + peek(b, ph, 0);'
    r = smoke_codebox(code, seconds=0.25)
    assert "self_sustain" not in _checks(r), r.findings
    assert r.verdict == "pass", r.findings


# ---------------------------------------------------------------------------
# CR-01: denormal WARN (all outputs)
# ---------------------------------------------------------------------------


def test_cr01_denormal_output_warns(tmp_path):
    code = "History h(1e-300); h = h * 0.5; out1 = in1 * 0 + h;"
    r = smoke_codebox("// smoke: control out1\n" + code, seconds=0.05)
    den = [f for f in r.findings if f.check == "denormal"]
    assert den and den[0].severity == "warn" and r.verdict == "pass"


# ---------------------------------------------------------------------------
# WR-01: mc.gen~ saved by MAX keeps its gen patcher under data.patcher
# ---------------------------------------------------------------------------


def test_wr01_mc_gen_data_patcher_is_discovered(tmp_path):
    data = generate_gendsp("out1 = in1 * 0.5;")
    box = _box("mc", "mc.gen~", outlettype=["multichannelsignal"],
               data={"patcher": data["patcher"]}, wrapper_uniquekey="u123")
    path = _write(tmp_path, "mcgen.maxpat", [box, _box("dac", "mc.dac~")],
                  [_line("mc", 0, "dac", 0)])
    (r,) = smoke_file(path, seconds=0.05)
    assert r.verdict == "pass", (r.verdict, r.reason)
    assert "mc.gen~ > codebox 1" in r.label
    assert r.outputs == {1: "audio"}


# ---------------------------------------------------------------------------
# WR-03: gates and one-shots that go quiet once the input drops
# ---------------------------------------------------------------------------


def test_wr03_noise_gate_at_max_threshold_is_not_a_fail():
    r = smoke_codebox("Param thresh(0.05, min=0, max=0.2); out1 = abs(in1) > thresh ? in1 : 0;",
                      seconds=0.2)
    assert r.verdict == "pass", r.findings
    sil = [f for f in r.findings if f.check == "silence"]
    assert sil and all(f.severity == "warn" for f in sil)
    assert "loud rerun" in sil[0].detail


def test_wr03_one_shot_envelope_is_not_a_fail():
    code = ("History env(0); History prev(0); trig = (in1 > 0.2) * (prev <= 0.2); "
            "prev = in1; env = max(trig, env - 0.001); out1 = env * in1;")
    r = smoke_codebox(code, seconds=0.2)
    assert r.verdict == "pass", r.findings


def test_wr03_output_that_dies_under_loud_input_still_fails():
    r = smoke_codebox("History n(0); n = n + 1; out1 = in1 * (n < 2000);", seconds=0.25)
    sil = [f for f in r.findings if f.check == "silence" and f.corner == "default"]
    assert r.verdict == "fail" and sil and sil[0].severity == "fail", r.findings


# ---------------------------------------------------------------------------
# IN-03 / IN-06
# ---------------------------------------------------------------------------


def test_in03_negative_seed_is_a_named_usage_error(capsys):
    safe = Path(__file__).resolve().parents[2] / "patterns" / "gen" / "gain" / "safe-gain.gendsp"
    assert main(["smoke", str(safe), "--seed", "-1"]) == 2
    err = capsys.readouterr().err
    assert "--seed" in err and "non-negative" in err
    with pytest.raises(ValueError, match="seed"):
        smoke_codebox("out1 = in1;", seconds=0.05, seed=-1)


def test_in06_jit_gen_without_patcher_is_reported_skipped(tmp_path):
    path = _write(tmp_path, "jit.maxpat", [
        _box("j", "jit.gen my-shader", outlettype=["jit_matrix", ""]),
        _box("p", "jit.pix", outlettype=["jit_matrix", ""]),
    ], [])
    results = smoke_file(path, seconds=0.05)
    assert [r.verdict for r in results] == ["skipped", "skipped"]
    assert all("not gen~" in r.reason for r in results)


# ---------------------------------------------------------------------------
# Report surface
# ---------------------------------------------------------------------------


def test_report_prints_and_serialises_ports(tmp_path, capsys):
    path = _write(tmp_path, "rep.maxpat", [
        _box("click", "click~", outlettype=["signal"]),
        _gen("gen", "out1 = in1 * 0.5; out2 = in1 * 1000;", n_out=2),
        _box("dac", "dac~"),
        _box("snap", "snapshot~", outlettype=["float"]),
    ], [_line("click", 0, "gen", 0), _line("gen", 0, "dac", 0), _line("gen", 1, "snap", 0)])
    rc = main(["smoke", str(path), "--seconds", "0.05"])
    out = capsys.readouterr().out
    assert rc == 0, out
    assert "ports: in1 trigger (click~); out1 audio (dac~), out2 control" in out
    main(["smoke", str(path), "--seconds", "0.05", "--json"])
    report = json.loads(capsys.readouterr().out)
    ports = report["codeboxes"][0]["ports"]
    assert ports["inputs"] == {"1": "trigger"}
    assert ports["outputs"] == {"1": "audio", "2": "control"}
    assert "host" in ports and "notes" in ports
