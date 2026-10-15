"""DSP pre-flight simulator orchestrator.

Per Phase 32 CONTEXT.md D-01 (topology library + mirror escape hatch --
one API, two on-ramps), D-03 (SimulationReport shape), D-05 (default
thresholds), D-09 (verdict priority).

Public surface:
  - run_simulation(...) -- single entry point.
  - SimulationReport -- dataclass returned by run_simulation.
  - TopologyError -- raised on unknown topology, mirror/topology conflict, or
    (topology= path) a sweep_param / params key the topology does not declare.

Q25 hardening (review H2 / H4):
  - The runaway early exit tests the post-settle slice of the step just
    measured -- the exact record the classifier reads -- so a startup
    transient no longer ends the sweep, and a sweep that stops early is
    reported as runaway, never pass.
  - rms_amplitude is the AC RMS (mean removed), so DC cannot defeat the
    no_oscillation floor.
  - topology= runs validate sweep_param and every params key against the
    class's PARAMS before rendering; a misspelled param would otherwise be
    ignored and the sweep would pass without testing anything. mirror=
    callables are dev-authored and declare nothing, so they are not
    validated.

Threat refs (Phase 32 32-01-PLAN <threat_model>):
  - T-01 (Elevation): mirror= callable comes from dev-authored test code,
    no string eval/exec, no third-party plugin loading.
  - T-04 (DoS): per-step buffer is bounded by `settle_samples + 0.5*sample_rate`;
    runaway early-exit short-circuits the sweep loop on a NaN/Inf or
    above-runaway_amplitude post-settle peak so divergent topologies cannot
    run unbounded.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import numpy as np

from src.maxpat.dsp_sim.classifier import (
    PASS,
    RUNAWAY,
    _SUGGESTED_FIX,
    Verdict,
    classify,
)
from src.maxpat.dsp_sim.measure import (
    ClassifierThresholds,
    StepMeasurement,
    cents_offset as _cents_offset,
    measure_ac_rms,
    measure_fundamental,
    measure_peak,
)


# ===========================================================================
# Exceptions
# ===========================================================================


class TopologyError(Exception):
    """Raised on an unknown topology, a mirror/topology conflict, or an undeclared param."""


# ===========================================================================
# Result shape (D-03)
# ===========================================================================


@dataclass
class SimulationReport:
    """Result of a run_simulation(...) call.

    Attributes:
        verdict: One of 'pass', 'phase_drift', 'mode_competition',
            'no_oscillation', 'runaway' (D-03, D-09 priority cascade).
        measurements: One StepMeasurement per sweep step. Shorter than the
            sweep only when a post-settle runaway stopped the sweep early
            (Q25 / H2); the verdict is then always 'runaway'.
        worst_step: Index of the step that triggered the failure; None on pass.
        reason: Human-readable diagnostic string.
        suggested_fix: Lifted from the CLAUDE.md Gen~ rule "Waveguide loop filters";
            None on pass.
        sweep_param: The parameter that was swept.
        sweep_range: (lo, hi, n) triple driving the sweep.
        sample_rate: Sample rate used for the simulation.
        patch_path: Reference path; carried through for reproducibility (DSPSIM-05).
    """

    verdict: Verdict
    measurements: list[StepMeasurement]
    worst_step: int | None
    reason: str
    suggested_fix: str | None
    sweep_param: str
    sweep_range: tuple[float, float, int]
    sample_rate: int
    patch_path: str | None = None


# ===========================================================================
# Mirror/topology resolution (D-01)
# ===========================================================================


def _resolve_stepper_factory(
    topology: str | None,
    mirror: Callable | None,
) -> tuple[Callable, frozenset[str] | None]:
    """Return (factory, declared_params).

    factory is a callable (sample_rate, params) -> stepper. Stepper has
    either a .step(in1, in2) -> float method or is itself a callable
    (n_samples, params) -> ndarray. Topology classes use the .step(...)
    form per D-01.

    declared_params is the topology class's PARAMS frozenset (Q25 / H4), or
    None for mirror= callables, which declare nothing and are not validated.

    Mutually exclusive with topology= per D-01.
    """
    if topology is not None and mirror is not None:
        raise TopologyError("topology= and mirror= are mutually exclusive (D-01)")
    if topology is None and mirror is None:
        raise TopologyError("must supply either topology= or mirror= (D-01)")
    if mirror is not None:
        return mirror, None
    # topology= path -- import topology library lazily so 32-01 can ship
    # before 32-02 lands the actual topology classes.
    try:
        from src.maxpat.dsp_sim.topologies import get_topology  # type: ignore[import-not-found]
    except ImportError as exc:
        raise TopologyError(
            f"topology library not available: {exc}. "
            f"Use mirror= until 32-02 lands."
        )
    cls = get_topology(topology)  # raises TopologyError on miss

    def factory(sample_rate, params):
        return cls(sample_rate=sample_rate, params=params)

    return factory, frozenset(getattr(cls, "PARAMS", frozenset()))


def _validate_params(
    topology: str | None,
    declared: frozenset[str] | None,
    sweep_param: str,
    params: dict[str, float],
) -> None:
    """Raise TopologyError if sweep_param or a params key is undeclared (Q25 / H4)."""
    if declared is None:
        return
    names = {sweep_param, *params.keys()}
    unknown = sorted(n for n in names if n not in declared)
    if unknown:
        raise TopologyError(
            f"topology '{topology}' does not declare param(s) "
            f"{', '.join(unknown)}; the run would ignore them and pass "
            f"without testing anything. Declared: "
            f"{', '.join(sorted(declared))}"
        )


# ===========================================================================
# Sweep execution
# ===========================================================================


def _render_step(
    stepper: Any,
    n_samples: int,
    params: dict[str, float],
) -> np.ndarray:
    """Run the stepper for n_samples and return the output buffer.

    Excitation: in1 = params['freq'] (Hz scalar), in2 = params.get('breath', 0.6).
    Per CONTEXT.md "Claude's Discretion" the settle window swallows the
    excitation transient; no explicit ramp is applied.

    Stepper protocol:
      - Object with `.step(in1, in2) -> float` method, OR
      - Callable accepting (n_samples, params) -> np.ndarray (vectorised mirrors).
    """
    in1 = float(params.get("freq", 220.0))
    in2 = float(params.get("breath", 0.6))
    if hasattr(stepper, "step"):
        out = np.zeros(n_samples, dtype=np.float64)
        for i in range(n_samples):
            out[i] = stepper.step(in1, in2)
        return out
    # Callable mirror form -- mirror returns a buffer directly.
    return stepper(n_samples, params)


def _measure_step(
    buf: np.ndarray,
    settle_samples: int,
    sample_rate: int,
    target_hz: float,
    param_value: float,
) -> StepMeasurement:
    """Reduce a buffer to a StepMeasurement; skip the first settle_samples."""
    tail = buf[settle_samples:] if buf.size > settle_samples else buf
    measured = measure_fundamental(tail, sample_rate)
    return StepMeasurement(
        param_value=param_value,
        target_hz=target_hz,
        measured_hz=measured,
        cents_offset=_cents_offset(measured, target_hz),
        rms_amplitude=measure_ac_rms(tail),
        peak_amplitude=measure_peak(tail),
    )


# ===========================================================================
# Public entry point (D-01)
# ===========================================================================


def run_simulation(
    *,
    patch_path: str | Path | None = None,
    topology: str | None = None,
    mirror: Callable | None = None,
    params: dict[str, float],
    sweep_param: str,
    sweep: tuple[float, float, int],
    sample_rate: int = 44100,
    settle_ms: int = 100,
    sweep_steps: int | None = None,
    cents_drift_limit: float = 5.0,
    mode_competition_jump: float = 50.0,
    amplitude_floor: float = 1e-4,
    runaway_amplitude: float = 10.0,
) -> SimulationReport:
    """Run a parameter sweep against a topology or custom mirror.

    Per CONTEXT.md D-01 (topology + mirror on-ramps), D-03 (SimulationReport
    fields), D-05 (default thresholds), D-09 (verdict priority).

    Args:
        patch_path: Reference path; carried in the report for reproducibility
            (DSPSIM-05). Optional -- fixtures using mirror= often pass a
            synthetic stub.
        topology: Name of a curated topology
            (mutually exclusive with mirror=).
        mirror: Callable (sample_rate, params) -> stepper
            (mutually exclusive with topology=).
        params: Base parameter dict. The swept parameter overrides
            params[sweep_param] per step.
        sweep_param: Name of the swept parameter.
        sweep: (lo, hi, n) -- n linear steps from lo to hi inclusive.
        sample_rate: Hz; default 44100.
        settle_ms: Skip this many ms before measuring (transient swallow).
        sweep_steps: Override the third element of `sweep` when supplied.
        cents_drift_limit, mode_competition_jump, amplitude_floor,
            runaway_amplitude: D-05 threshold overrides.

    Returns:
        SimulationReport with verdict, measurements, worst_step, reason,
        suggested_fix.

    Raises:
        TopologyError: Unknown topology, topology+mirror conflict, or (on the
            topology= path) a sweep_param or params key outside the class's
            PARAMS. Raised before any rendering (Q25 / H4).
    """
    factory, declared = _resolve_stepper_factory(topology, mirror)
    _validate_params(topology, declared, sweep_param, params)
    lo, hi, n = sweep
    if sweep_steps is not None:
        n = sweep_steps
    if n < 2:
        raise TopologyError(f"sweep must have >= 2 steps; got n={n}")
    settle_samples = int(settle_ms / 1000.0 * sample_rate)
    # T-04 mitigation: per-step buffer is bounded by this fixed window.
    n_samples = settle_samples + int(0.5 * sample_rate)  # 500ms post-settle

    thresholds = ClassifierThresholds(
        cents_drift_limit=cents_drift_limit,
        mode_competition_jump=mode_competition_jump,
        amplitude_floor=amplitude_floor,
        runaway_amplitude=runaway_amplitude,
        settle_ms=settle_ms,
        sweep_steps=n,
        sample_rate=sample_rate,
    )

    # ---- Sweep phase ----
    measurements: list[StepMeasurement] = []
    stopped_at: int | None = None
    for i in range(n):
        param_value = lo + i * (hi - lo) / (n - 1)
        step_params = dict(params)
        step_params[sweep_param] = param_value
        target_hz = float(step_params.get("freq", 220.0))
        stepper = factory(sample_rate=sample_rate, params=step_params)
        buf = _render_step(stepper, n_samples, step_params)
        m = _measure_step(buf, settle_samples, sample_rate, target_hz, param_value)
        measurements.append(m)
        # T-04 mitigation: early-exit on runaway so divergent topologies
        # don't waste cycles. Q25 / H2: test the record just appended (the
        # post-settle peak), the exact slice the classifier reads, so a
        # startup transient cannot end the sweep and an early exit always
        # classifies as runaway (D-09 priority 1).
        if (not np.isfinite(m.peak_amplitude)
                or m.peak_amplitude > runaway_amplitude):
            if i < n - 1:
                stopped_at = i
            break

    # ---- Classify phase ----
    verdict, worst_step, reason, suggested_fix = classify(measurements, thresholds)
    if stopped_at is not None:
        reason = f"{reason}; sweep stopped early at step {stopped_at} of {n}"
        if verdict == PASS:
            # Defensive: an early exit is never pass (Q25 / H2).
            verdict = RUNAWAY
            worst_step = stopped_at
            suggested_fix = _SUGGESTED_FIX[RUNAWAY]

    return SimulationReport(
        verdict=verdict,
        measurements=measurements,
        worst_step=worst_step,
        reason=reason,
        suggested_fix=suggested_fix,
        sweep_param=sweep_param,
        sweep_range=(lo, hi, n),
        sample_rate=sample_rate,
        patch_path=str(patch_path) if patch_path is not None else None,
    )
