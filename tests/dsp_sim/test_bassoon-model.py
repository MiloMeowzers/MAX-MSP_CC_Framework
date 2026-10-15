"""Live-patch gate for patches/bassoon-model/generated/bassoon-model.maxpat.

Per CONTEXT.md D-06/D-07: the filename matches the patch stem, so
max-dsp-agent's filename discovery runs this gate when the bassoon patch is
saved. Under D-07 filename presence is the gate; the D-10 opt-out is
deleting or `pytest.skip(...)`-ing the test.

Q25 / H3 rewrite. Before Q25 the gate swept only the post-loop bell_bright
against a stale topology (no phase-delay compensation, old reed), so it
passed without testing the loop that ships. Now:

  - test_topology_matches_shipped_codebox renders the LIVE codebox from
    patches/bassoon-model/generated/bassoon.gendsp with
    patches/bassoon-model/tools/genrun.py and compares it sample for sample
    (<= 1e-9) with reed_bore_post_radiation. The gate therefore fails as
    soon as the topology and the shipped codebox diverge: re-port the loop
    or skip-mark this fixture (D-10).
  - The sweeps exercise the in-loop bore_damp at 58.27/110/220/440 Hz and
    the 58.27-440 Hz register, plus the original bell_bright sweep, all with
    the D-05 default thresholds and the shipped Param defaults.

xfail policy (Q25 planner decision 7): a sweep the shipped loop fails is
marked xfail(strict=True, raises=AssertionError) with the measured verdict
in its reason. The body still asserts `verdict == "pass"` with default
thresholds -- nothing is loosened. Strict means a fix turns the mark XPASS,
which fails, so the mark must then be removed.

The v0.4.1 regression mirror now reads no_oscillation (DC-only at low
bell_bright under the fixed detector, Q25 planner decision 3); v0.4.0 is
still phase_drift.

Measured verdicts (Q25, shipped v0.18 loop, default thresholds):

  sweep                         verdict      range (cents)
  bell_bright 0..1 @ 220 Hz     pass          0.00   (+4.51 every step)
  bore_damp 0..1 @ 58.27 Hz     pass          4.69   (limit 5.0)
  bore_damp 0..1 @ 110 Hz       phase_drift   6.78
  bore_damp 0..1 @ 220 Hz       phase_drift  10.22
  bore_damp 0..1 @ 440 Hz       phase_drift   9.06
  freq 58.27..440 Hz            phase_drift   6.10

This file uses a hyphen in the filename, which is non-standard for
Python modules but VALID for pytest collection (pytest matches file
paths, not module imports). Do not import this file from other modules.
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest

from src.maxpat.dsp_sim import run_simulation
from src.maxpat.dsp_sim.topologies import ReedBorePostRadiation


_REPO = Path(__file__).resolve().parents[2]
_BASSOON_DIR = _REPO / "patches" / "bassoon-model"
_GENDSP = _BASSOON_DIR / "generated" / "bassoon.gendsp"
_TOOLS = _BASSOON_DIR / "tools"
_PATCH = "patches/bassoon-model/generated/bassoon-model.maxpat"
_SR = 44100

# Shipped defaults: every declared PARAM at its codebox default.
SHIPPED = {
    "freq": 220.0,
    "breath": 0.6,
    "cone_loss": 0.85,
    "reed_stiff": 0.5,
    "reed_aper": 0.0,
    "bell_bright": 0.5,
    "bore_damp": 0.3,
    "reed_res_freq": 1500.0,
    "reed_res_q": 2.5,
    "register": 0.0,
    "attack_time": 15.0,
    "release_time": 30.0,
}

# Codebox layers the port fixes off (Q25 planner decision 5).
_OFF = {
    "vib_depth": 0.0,
    "vib_amp": 0.0,
    "noise_amt": 0.0,
    "chiff_amt": 0.0,
    "drift_on": 0.0,
    "tongue_trig": 0.0,
}

_NOT_CODEBOX_PARAMS = {"freq", "breath", "cone_loss"}


# ===========================================================================
# Live codebox + genrun
# ===========================================================================


def _shipped_codebox() -> str:
    """Return the `code` of the codebox in bassoon.gendsp (read only)."""
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
    """Import patches/bassoon-model/tools/genrun.py in isolation.

    genrun runs `from core import analyze, SR` against its sibling core.py,
    so the tools dir goes on sys.path[0] for the import. Teardown removes it
    and restores any pre-existing `core` / `genrun` modules so nothing
    shadows later imports.
    """
    saved = {name: sys.modules.get(name) for name in ("core", "genrun")}
    for name in saved:
        sys.modules.pop(name, None)
    tools = str(_TOOLS)
    sys.path.insert(0, tools)
    try:
        # importlib, not `import genrun`: genrun is a repo-local tool under
        # patches/, not a third-party dependency (test_release scans imports).
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


# ===========================================================================
# Parity: the topology IS the shipped loop (Q25 / H3)
# ===========================================================================


_PARITY_CASES = [
    pytest.param({}, id="a-defaults-220Hz"),
    pytest.param(
        {"freq": 58.27, "breath": 1.0, "bore_damp": 0.0, "reed_stiff": 0.9},
        id="b-58Hz-full-breath",
    ),
    pytest.param(
        {
            "freq": 440.0, "breath": 0.45, "bore_damp": 1.0, "register": 1.0,
            "bell_bright": 1.0, "reed_res_freq": 2500.0, "reed_res_q": 6.0,
            "reed_aper": 0.2, "attack_time": 3.0, "release_time": 100.0,
        },
        id="c-440Hz-extremes",
    ),
]


@pytest.mark.parametrize("overrides", _PARITY_CASES)
def test_topology_matches_shipped_codebox(genrun, overrides, request):
    """reed_bore_post_radiation matches the live codebox via genrun within 1e-9."""
    label = request.node.callspec.id
    params = dict(SHIPPED)
    params.update(overrides)
    dur = 0.25
    freq = params["freq"]
    breath = params["breath"]
    codebox_params = {
        k: v for k, v in params.items() if k not in _NOT_CODEBOX_PARAMS
    }
    ref, _ = genrun.render(
        _shipped_codebox(), freq, lambda t: breath, dur=dur, **codebox_params, **_OFF
    )
    stepper = ReedBorePostRadiation(sample_rate=_SR, params=params)
    got = np.array([stepper.step(freq, breath) for _ in range(ref.size)])
    diff = np.abs(got - ref)
    bad = np.nonzero(~(diff <= 1e-9))[0]
    if bad.size:
        i = int(bad[0])
        pytest.fail(
            f"{label}: sample {i} differs by {diff[i]:.3e} "
            f"(topology {float(got[i])!r}, codebox {float(ref[i])!r}). "
            "reed_bore_post_radiation is stale against bassoon.gendsp, or genrun "
            "cannot transpile it. Re-port the loop (Q25 / H3) or skip-mark this "
            "fixture per D-10."
        )
    assert np.max(np.abs(ref)) > 1e-3, f"{label}: codebox render is silent"


# ===========================================================================
# Sweeps (default thresholds; shipped defaults as base params)
# ===========================================================================


def _assert_pass(r) -> None:
    cents = ", ".join(f"{m.cents_offset:+.2f}" for m in r.measurements)
    assert r.verdict == "pass", (
        f"shipped bassoon loop: {r.verdict!r} -- {r.reason}. "
        f"Per-step cents: [{cents}]"
    )
    assert r.worst_step is None
    assert r.suggested_fix is None


def _sweep(param: str, sweep: tuple[float, float, int], **base):
    params = dict(SHIPPED)
    params.update(base)
    return run_simulation(
        patch_path=_PATCH,
        topology="reed_bore_post_radiation",
        params=params,
        sweep_param=param,
        sweep=sweep,
    )


def test_bassoon_bell_bright_sweep_stable():
    """Post-loop bell_bright (0..1, 32 steps) at 220 Hz must not detune the loop."""
    _assert_pass(_sweep("bell_bright", (0.0, 1.0, 32), freq=220.0))


def _honest_xfail(verdict: str, cents_range: float, sweep: str):
    """Strict xfail carrying the measured verdict (Q25 planner decision 7)."""
    return pytest.mark.xfail(
        strict=True,
        raises=AssertionError,
        reason=(
            f"shipped v0.18 loop: {verdict} {cents_range:.2f} cents over {sweep} "
            f"(limit 5) - Q25 honest verdict, thresholds unchanged"
        ),
    )


@pytest.mark.parametrize("freq", [
    pytest.param(58.27, id="58.27Hz"),
    pytest.param(110.0, id="110Hz", marks=_honest_xfail(
        "phase_drift", 6.78, "bore_damp 0..1 @ 110 Hz")),
    pytest.param(220.0, id="220Hz", marks=_honest_xfail(
        "phase_drift", 10.22, "bore_damp 0..1 @ 220 Hz")),
    pytest.param(440.0, id="440Hz", marks=_honest_xfail(
        "phase_drift", 9.06, "bore_damp 0..1 @ 440 Hz")),
])
def test_bassoon_bore_damp_sweep(freq):
    """In-loop bore_damp (0..1, 11 steps) must stay within the 5-cent drift limit."""
    _assert_pass(_sweep("bore_damp", (0.0, 1.0, 11), freq=freq))


@_honest_xfail("phase_drift", 6.10, "freq 58.27..440 Hz @ bore_damp 0.3")
def test_bassoon_freq_sweep():
    """The 58.27-440 Hz register (12 steps, bore_damp 0.3) must track pitch within 5 cents."""
    _assert_pass(_sweep("freq", (58.27, 440.0, 12), bore_damp=0.3))
