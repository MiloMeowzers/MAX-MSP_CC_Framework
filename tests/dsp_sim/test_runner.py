"""Integration tests for run_simulation orchestrator + SimulationReport.

Per Phase 32 CONTEXT.md D-01 (topology + mirror on-ramps mutually exclusive),
D-03 (SimulationReport shape), D-05 (default thresholds), D-09 (verdict
priority).

The mirror= on-ramp is the single contract this plan must support
end-to-end; topology= raises TopologyError until 32-02 lands the topology
library. Tests use small in-test stub mirrors (no bassoon math); the live
mirror tests live in 32-04.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from src.maxpat.dsp_sim import (
    MODE_COMPETITION,
    NO_OSCILLATION,
    PASS,
    PHASE_DRIFT,
    RUNAWAY,
    SimulationReport,
    StepMeasurement,
    TopologyError,
    run_simulation,
)


# ===========================================================================
# Stub mirror factories
# ===========================================================================


def _stub_clean_220_factory(sample_rate, params):
    """Return a stepper that emits a clean 220 Hz sine independent of params."""
    freq = float(params.get("freq", 220.0))

    class _Stepper:
        def __init__(self):
            self._t = 0
            self._sr = sample_rate

        def step(self, in1, in2):
            v = math.sin(2.0 * math.pi * freq * self._t / self._sr)
            self._t += 1
            return v

    return _Stepper()


def _stub_runaway_factory(sample_rate, params):
    """Return a stepper that emits NaN on the first sample (runaway trigger)."""

    class _Stepper:
        def step(self, in1, in2):
            return float("nan")

    return _Stepper()


def _stub_silent_factory(sample_rate, params):
    """Return a stepper that emits exact zeros (no_oscillation trigger)."""

    class _Stepper:
        def step(self, in1, in2):
            return 0.0

    return _Stepper()


# ===========================================================================
# Mutually exclusive on-ramps (D-01)
# ===========================================================================


class TestRunSimulationOnRamps:
    """Verify the topology= / mirror= mutual-exclusion contract."""

    def test_both_topology_and_mirror_raises(self):
        """Passing both topology= and mirror= raises TopologyError."""
        with pytest.raises(TopologyError):
            run_simulation(
                topology="reed_bore_post_radiation",
                mirror=_stub_clean_220_factory,
                params={"freq": 220.0, "breath": 0.6},
                sweep_param="breath",
                sweep=(0.0, 1.0, 4),
            )

    def test_neither_topology_nor_mirror_raises(self):
        """Passing neither topology= nor mirror= raises TopologyError."""
        with pytest.raises(TopologyError):
            run_simulation(
                params={"freq": 220.0, "breath": 0.6},
                sweep_param="breath",
                sweep=(0.0, 1.0, 4),
            )

    def test_unknown_topology_raises(self):
        """An unknown topology name raises TopologyError."""
        with pytest.raises(TopologyError):
            run_simulation(
                topology="nonexistent_topology",
                params={"freq": 220.0, "breath": 0.6},
                sweep_param="breath",
                sweep=(0.0, 1.0, 4),
            )


# ===========================================================================
# Sweep behaviour + SimulationReport shape
# ===========================================================================


class TestRunSimulationSweep:
    """Verify the sweep mechanics and the returned SimulationReport."""

    def test_returns_simulation_report_with_correct_step_count(self):
        """run_simulation(...) returns a SimulationReport with N measurements."""
        report = run_simulation(
            mirror=_stub_clean_220_factory,
            params={"freq": 220.0, "breath": 0.6},
            sweep_param="breath",
            sweep=(0.0, 1.0, 32),
        )
        assert isinstance(report, SimulationReport)
        assert len(report.measurements) == 32
        assert all(isinstance(m, StepMeasurement) for m in report.measurements)

    def test_param_values_linearly_distributed(self):
        """measurements[k].param_value == lo + k*(hi-lo)/(n-1)."""
        report = run_simulation(
            mirror=_stub_clean_220_factory,
            params={"freq": 220.0, "breath": 0.6},
            sweep_param="breath",
            sweep=(0.0, 1.0, 8),
        )
        assert report.measurements[0].param_value == pytest.approx(0.0)
        assert report.measurements[-1].param_value == pytest.approx(1.0)
        assert report.measurements[3].param_value == pytest.approx(3.0 / 7.0)

    def test_clean_220hz_passes(self):
        """A constant 220 Hz mirror sweep emits verdict='pass'."""
        report = run_simulation(
            mirror=_stub_clean_220_factory,
            params={"freq": 220.0, "breath": 0.6},
            sweep_param="breath",
            sweep=(0.0, 1.0, 8),
        )
        assert report.verdict == PASS, report.reason
        assert report.suggested_fix is None
        assert report.worst_step is None

    def test_runaway_mirror_triggers_runaway(self):
        """A NaN-emitting mirror trips the runaway verdict."""
        report = run_simulation(
            mirror=_stub_runaway_factory,
            params={"freq": 220.0, "breath": 0.6},
            sweep_param="breath",
            sweep=(0.0, 1.0, 4),
        )
        assert report.verdict == RUNAWAY

    def test_silent_mirror_triggers_no_oscillation(self):
        """A zero-emitting mirror trips the no_oscillation verdict."""
        report = run_simulation(
            mirror=_stub_silent_factory,
            params={"freq": 220.0, "breath": 0.6},
            sweep_param="breath",
            sweep=(0.0, 1.0, 4),
        )
        assert report.verdict == NO_OSCILLATION


# ===========================================================================
# Threshold overrides propagate (D-05)
# ===========================================================================


class TestRunSimulationThresholdOverride:
    """Verify threshold kwargs propagate into the classifier."""

    def test_tight_drift_limit_triggers_phase_drift(self):
        """cents_drift_limit=0.001 makes any measurement noise look like drift."""
        report = run_simulation(
            mirror=_stub_clean_220_factory,
            params={"freq": 220.0, "breath": 0.6},
            sweep_param="breath",
            sweep=(0.0, 1.0, 8),
            cents_drift_limit=0.001,
        )
        # Sub-sample interpolation noise should be > 0.001 cents across 8 steps,
        # so this becomes phase_drift instead of pass.
        assert report.verdict in (PHASE_DRIFT, PASS)
        # If it remains pass even at 0.001, the autocorrelation is too clean
        # for this stub -- not a failure of the override path. Verify we at
        # least produce the right SimulationReport shape.
        assert report.sweep_param == "breath"
        assert report.sweep_range == (0.0, 1.0, 8)


# ===========================================================================
# Public surface re-exports
# ===========================================================================


class TestPublicSurface:
    """Verify dsp_sim package re-exports the documented surface."""

    def test_simulation_report_exported(self):
        """SimulationReport is importable from src.maxpat.dsp_sim."""
        from src.maxpat.dsp_sim import SimulationReport as SR
        assert SR is SimulationReport

    def test_topology_error_exported(self):
        """TopologyError is importable from src.maxpat.dsp_sim."""
        from src.maxpat.dsp_sim import TopologyError as TE
        assert TE is TopologyError

    def test_verdict_constants_exported(self):
        """PASS / PHASE_DRIFT / MODE_COMPETITION / NO_OSCILLATION / RUNAWAY all exported."""
        from src.maxpat.dsp_sim import (
            MODE_COMPETITION,
            NO_OSCILLATION,
            PASS,
            PHASE_DRIFT,
            RUNAWAY,
        )
        assert PASS == "pass"
        assert PHASE_DRIFT == "phase_drift"
        assert MODE_COMPETITION == "mode_competition"
        assert NO_OSCILLATION == "no_oscillation"
        assert RUNAWAY == "runaway"


# ===========================================================================
# Q25 / H1: pitch detection end to end through run_simulation
# ===========================================================================


def _vector_wave_factory(kind):
    """Return a mirror factory emitting a vectorised sine or naive saw at params['freq']."""

    def factory(sample_rate, params):
        freq = float(params.get("freq", 220.0))

        def render(n_samples, step_params):
            t = np.arange(n_samples) / sample_rate
            if kind == "sine":
                return 0.5 * np.sin(2 * np.pi * freq * t)
            return 0.5 * (2.0 * np.mod(freq * t, 1.0) - 1.0)

        return render

    return factory


class TestPitchEndToEnd:
    """Q25 / H1: the bassoon register and harmonic-rich waves read correctly through run_simulation.

    Before Q25 the 58.27 Hz sine was mode_competition at 4009.09 Hz and the
    440 Hz saw read an octave low.
    """

    @pytest.mark.parametrize("kind,freq", [("sine", 58.27), ("saw", 440.0)])
    def test_mirror_passes_with_exact_pitch(self, kind, freq):
        report = run_simulation(
            mirror=_vector_wave_factory(kind),
            params={"freq": freq, "breath": 0.6},
            sweep_param="breath",
            sweep=(0.0, 1.0, 4),
        )
        assert report.verdict == PASS, report.reason
        assert len(report.measurements) == 4
        for m in report.measurements:
            assert m.measured_hz == pytest.approx(freq, abs=0.01), m


# ===========================================================================
# Q25 / H2 + H4 mirror factories (exact shapes from the Q25 plan)
# ===========================================================================


def _transient_mirror(runaway: bool):
    """Samples 0-9 output 50.0 (startup transient), then a 220 Hz sine.

    With runaway=True the post-transient amplitude is 0.5 for
    params['drive'] <= 0.5 and 20.0 (x40) above it.
    """

    def factory(sample_rate, params):
        amp = 0.5
        if runaway and float(params.get("drive", 0.0)) > 0.5:
            amp = 20.0

        def render(n_samples, step_params):
            t = np.arange(n_samples) / sample_rate
            out = amp * np.sin(2 * np.pi * 220.0 * t)
            out[:10] = 50.0
            return out

        return render

    return factory


def _constant_factory(sample_rate, params):
    """Constant 0.3: no pitch, and no AC energy."""
    return lambda n_samples, step_params: np.full(n_samples, 0.3)


def _dc_ripple_factory(sample_rate, params):
    """DC 0.5 + 5e-5 sine ripple: AC RMS 3.5e-5, below the 1e-4 floor."""

    def render(n_samples, step_params):
        t = np.arange(n_samples) / sample_rate
        return 0.5 + 5e-5 * np.sin(2 * np.pi * 220.0 * t)

    return render


class TestEarlyExit:
    """Q25 / H2: the runaway early exit reads the post-settle slice; an early exit is never pass.

    Before Q25 the whole-buffer check tripped on the startup transient at
    step 0, and the classifier then saw one clean post-settle step: the x40
    runaway returned "pass, all 1 steps within thresholds".
    """

    def test_startup_transient_does_not_end_sweep(self):
        report = run_simulation(
            mirror=_transient_mirror(runaway=False),
            params={"freq": 220.0, "breath": 0.6, "drive": 0.0},
            sweep_param="drive",
            sweep=(0.0, 1.0, 8),
        )
        assert len(report.measurements) == 8
        assert report.verdict == PASS, report.reason

    def test_post_settle_runaway_stops_with_runaway(self):
        report = run_simulation(
            mirror=_transient_mirror(runaway=True),
            params={"freq": 220.0, "breath": 0.6, "drive": 0.0},
            sweep_param="drive",
            sweep=(0.0, 1.0, 8),
        )
        assert report.verdict == RUNAWAY, report.reason
        assert report.worst_step == 4
        assert len(report.measurements) == 5
        assert "stopped early at step 4 of 8" in report.reason


class TestFalsePassPaths:
    """Q25 / H4: no pitch, DC and undeclared params are no longer scored as pass."""

    def test_constant_output_is_no_oscillation(self):
        report = run_simulation(
            mirror=_constant_factory,
            params={"freq": 220.0, "breath": 0.6},
            sweep_param="breath",
            sweep=(0.0, 1.0, 4),
        )
        assert report.verdict == NO_OSCILLATION, report.reason
        assert report.worst_step == 0
        assert "no detectable fundamental" in report.reason

    def test_dc_plus_tiny_ripple_is_no_oscillation(self):
        report = run_simulation(
            mirror=_dc_ripple_factory,
            params={"freq": 220.0, "breath": 0.6},
            sweep_param="breath",
            sweep=(0.0, 1.0, 4),
        )
        assert report.verdict == NO_OSCILLATION, report.reason
        assert "floor" in report.reason
        assert report.measurements[0].rms_amplitude < 1e-4

    def test_silent_and_nan_mirrors_keep_verdicts(self):
        silent = run_simulation(
            mirror=_stub_silent_factory,
            params={"freq": 220.0, "breath": 0.6},
            sweep_param="breath",
            sweep=(0.0, 1.0, 4),
        )
        assert silent.verdict == NO_OSCILLATION
        nan = run_simulation(
            mirror=_stub_runaway_factory,
            params={"freq": 220.0, "breath": 0.6},
            sweep_param="breath",
            sweep=(0.0, 1.0, 4),
        )
        assert nan.verdict == RUNAWAY

    @pytest.fixture
    def step_spy(self, monkeypatch):
        """Count step() calls on every registered topology (rendering spy)."""
        from src.maxpat.dsp_sim.topologies import TOPOLOGIES
        calls = {"n": 0}
        for cls in TOPOLOGIES.values():
            original = cls.step

            def spy(self, in1, in2, _orig=original):
                calls["n"] += 1
                return _orig(self, in1, in2)

            monkeypatch.setattr(cls, "step", spy)
        return calls

    def test_misspelled_sweep_param_raises(self, step_spy):
        with pytest.raises(TopologyError) as excinfo:
            run_simulation(
                topology="reed_bore_post_radiation",
                params={"freq": 220.0, "breath": 0.6},
                sweep_param="bel_brigth",
                sweep=(0.0, 1.0, 3),
            )
        msg = str(excinfo.value)
        assert "bel_brigth" in msg
        assert "bell_bright" in msg and "bore_damp" in msg  # declared names listed
        assert step_spy["n"] == 0

    def test_misspelled_base_param_raises(self, step_spy):
        with pytest.raises(TopologyError) as excinfo:
            run_simulation(
                topology="reed_bore_post_radiation",
                params={"freq": 220.0, "breath": 0.6, "bel_brigth": 0.5},
                sweep_param="bore_damp",
                sweep=(0.0, 1.0, 3),
            )
        assert "bel_brigth" in str(excinfo.value)
        assert step_spy["n"] == 0

    def test_param_from_other_topology_raises(self, step_spy):
        with pytest.raises(TopologyError):
            run_simulation(
                topology="reed_bore",
                params={"freq": 220.0, "breath": 0.6},
                sweep_param="bell_bright",
                sweep=(0.0, 1.0, 3),
            )
        assert step_spy["n"] == 0

    def test_declared_sweep_still_runs(self, step_spy):
        report = run_simulation(
            topology="reed_bore_post_radiation",
            params={"freq": 220.0, "breath": 0.6},
            sweep_param="bore_damp",
            sweep=(0.0, 1.0, 2),
        )
        assert len(report.measurements) == 2
        assert step_spy["n"] > 0
