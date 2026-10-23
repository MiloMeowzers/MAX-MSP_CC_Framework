"""Unit tests for dsp_sim measurement primitives.

Per Phase 32 CONTEXT.md D-03 (StepMeasurement fields) and D-05 (default
thresholds).
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from src.maxpat.dsp_sim.measure import (
    ClassifierThresholds,
    StepMeasurement,
    cents_offset,
    measure_fundamental,
    measure_peak,
    measure_rms,
)


# ===========================================================================
# Q25 / H1 regression-grid helpers
# ===========================================================================

_SR = 44100
_N = 22050  # 0.5 s, the runner's post-settle window
_GRID_HZ = sorted(
    set(round(float(f), 3) for f in np.geomspace(50.0, 1000.0, 24))
    | {50.0, 58.27, 110.0, 220.0, 440.0, 1000.0}
)
_WAVES = ("sine", "saw", "pulse")
_START_PHASES = (0.0, 0.37, 1.9)


def _wave(kind: str, freq: float, phi: float, n: int = _N) -> np.ndarray:
    """Sine, naive saw (2p - 1) or 25%-duty 0/1 pulse with start phase phi (rad)."""
    t = np.arange(n) / _SR
    if kind == "sine":
        return np.sin(2 * np.pi * freq * t + phi)
    p = np.mod(freq * t + phi / (2 * np.pi), 1.0)
    if kind == "saw":
        return 2.0 * p - 1.0
    return (p < 0.25).astype(np.float64)


# ===========================================================================
# Measurement primitives
# ===========================================================================


class TestMeasureFundamental:
    """Verify autocorrelation-based pitch tracking."""

    def test_pure_sine_220_hz_recovered(self):
        """A 220 Hz sine on a 4096-sample buffer recovers within +/- 0.5 Hz."""
        sample_rate = 44100
        n = 4096
        t = np.arange(n) / sample_rate
        buf = np.sin(2 * np.pi * 220.0 * t)
        measured = measure_fundamental(buf, sample_rate)
        assert measured == pytest.approx(220.0, abs=0.5)

    @pytest.mark.parametrize("phase", _START_PHASES)
    @pytest.mark.parametrize("wave", _WAVES)
    @pytest.mark.parametrize("freq", _GRID_HZ)
    def test_grid_50_to_1000_hz_within_half_cent(self, freq, wave, phase):
        """Q25 / H1: sine, naive saw and 25%-duty pulse 50-1000 Hz read within 0.5 cents.

        Before Q25 the detector read low sines as 4009 Hz (58.27 / 70 Hz) and
        harmonic-rich saws an octave low (220 / 440 Hz -> 109.99 Hz).
        """
        buf = _wave(wave, freq, phase)
        measured = measure_fundamental(buf, _SR)
        assert measured > 0.0, f"{wave} {freq:.2f} Hz phase {phase}: no pitch"
        err = 1200.0 * math.log2(measured / freq)
        assert abs(err) < 0.5, (
            f"{wave} {freq:.2f} Hz phase {phase}: read {measured:.4f} Hz "
            f"({err:+.3f} cents)"
        )

    def test_bassoon_low_b_flat_sine_reads_58_27(self):
        """Q25 / H1: a 58.27 Hz sine (low B-flat 1) reads 58.27 Hz, not 4009 Hz."""
        measured = measure_fundamental(_wave("sine", 58.27, 0.0), _SR)
        assert measured == pytest.approx(58.27, abs=0.01)

    def test_440_hz_saw_reads_440(self):
        """Q25 / H1: a 440 Hz naive saw reads 440 Hz, not an octave low."""
        measured = measure_fundamental(_wave("saw", 440.0, 0.0), _SR)
        assert measured == pytest.approx(440.0, abs=0.01)

    def test_dc_plus_noise_on_low_sine(self):
        """Q25 / H1: DC 0.3 + 0.5 sine 58.27 Hz + 0.01 Gaussian noise reads within 1 cent."""
        rng = np.random.default_rng(1)
        buf = 0.3 + 0.5 * _wave("sine", 58.27, 0.0) + 0.01 * rng.standard_normal(_N)
        measured = measure_fundamental(buf, _SR)
        assert measured > 0.0
        assert abs(1200.0 * math.log2(measured / 58.27)) < 1.0


# ===========================================================================
# 261022-ud6 WR-02: bright waveforms across the whole 40 Hz - 4 kHz window
# ===========================================================================


def _bright(kind: str, freq: float, phi: float, n: int = _N) -> np.ndarray:
    """Naive square or a 0/1 pulse of the given duty ("p05", "p10", "p25")."""
    t = np.arange(n) / _SR
    p = np.mod(freq * t + phi / (2 * np.pi), 1.0)
    if kind == "square":
        return (p < 0.5).astype(np.float64)
    if kind == "saw":
        return 2.0 * p - 1.0
    duty = {"p05": 0.05, "p10": 0.10, "p25": 0.25}[kind]
    return (p < duty).astype(np.float64)


def _cents(measured: float, freq: float) -> float:
    return 1200.0 * math.log2(measured / freq) if measured > 0.0 else float("inf")


# Saw, square and 25% pulse: the whole window. 5% / 10% pulses: up to the
# frequency where the high part is 2 samples wide (duty * SR / f >= 2); a
# narrower naive pulse is ambiguous at the sample level (its sampled shape
# only repeats every few periods), which the README documents.
_WR02_GRID = (
    [("saw", f) for f in np.geomspace(50.0, 4000.0, 40)]
    + [("square", f) for f in np.geomspace(50.0, 4000.0, 40)]
    + [("p25", f) for f in np.geomspace(50.0, 4000.0, 40)]
    + [("p10", f) for f in np.geomspace(50.0, 0.10 * _SR / 2.0, 40)]
    + [("p05", f) for f in np.geomspace(50.0, 0.05 * _SR / 2.0, 40)]
)


class TestWr02BrightWaveforms:
    """WR-02: corner-shaped NACF peaks sampled off their apex no longer read an octave low."""

    @pytest.mark.parametrize("phase", (0.0, 1.9))
    @pytest.mark.parametrize(
        "kind,freq", _WR02_GRID, ids=[f"{k}-{f:.1f}" for k, f in _WR02_GRID]
    )
    def test_grid_within_one_cent(self, kind, freq, phase):
        measured = measure_fundamental(_bright(kind, freq, phase), _SR)
        err = _cents(measured, freq)
        assert abs(err) < 1.0, f"{kind} {freq:.2f} Hz: read {measured:.3f} Hz ({err:+.2f} c)"

    @pytest.mark.parametrize(
        "kind,freq",
        [("p05", 434.5), ("p05", 457.0), ("p10", 856.5), ("saw", 1603.0),
         ("saw", 1604.0), ("square", 2262.0), ("saw", 3206.0), ("p25", 3600.0)],
    )
    def test_review_repros(self, kind, freq):
        """The review's failing points (each read an octave or more low before)."""
        measured = measure_fundamental(_bright(kind, freq, 0.0), _SR)
        assert abs(_cents(measured, freq)) < 1.0, measured

    @pytest.mark.parametrize("freq", (220.0, 1000.0, 1764.0, 3520.0))
    def test_strong_second_harmonic_is_not_read_an_octave_up(self, freq):
        """Control: a weak fundamental (0.3) under a strong 2nd harmonic still reads f."""
        t = np.arange(_N) / _SR
        buf = 0.3 * np.sin(2 * np.pi * freq * t) + np.sin(4 * np.pi * freq * t)
        assert abs(_cents(measure_fundamental(buf, _SR), freq)) < 1.0

    def test_runner_5_percent_pulse_is_not_mode_competition(self):
        """The review's public-API repro: a 457 Hz 5% pulse mirror passes."""
        from src.maxpat.dsp_sim import run_simulation

        def mirror(sample_rate, params):
            def render(n, p):
                t = np.arange(n) / sample_rate
                return ((p["freq"] * t) % 1.0 < p["duty"]).astype(float)
            return render

        report = run_simulation(
            mirror=mirror, params={"freq": 457.0, "duty": 0.05},
            sweep_param="duty", sweep=(0.05, 0.05, 2),
        )
        assert report.verdict == "pass", report.reason


class TestMeasureFundamentalNullInputs:
    """Q25 / H1: inputs with no period return exactly 0.0, never a bogus pitch."""

    def test_constant_returns_zero(self):
        assert measure_fundamental(np.full(_N, 0.3), _SR) == 0.0

    def test_zeros_return_zero(self):
        assert measure_fundamental(np.zeros(_N), _SR) == 0.0

    def test_white_noise_returns_zero(self):
        rng = np.random.default_rng(0)
        assert measure_fundamental(rng.uniform(-1.0, 1.0, _N), _SR) == 0.0

    def test_nan_returns_zero(self):
        buf = _wave("sine", 220.0, 0.0)
        buf[100] = np.nan
        assert measure_fundamental(buf, _SR) == 0.0

    def test_inf_returns_zero(self):
        buf = _wave("sine", 220.0, 0.0)
        buf[100] = np.inf
        assert measure_fundamental(buf, _SR) == 0.0

    def test_short_buffer_returns_zero(self):
        buf = np.sin(2 * np.pi * 220.0 * np.arange(32) / _SR)
        assert measure_fundamental(buf, _SR) == 0.0

    @pytest.mark.parametrize("seed", range(20))
    def test_random_inputs_finite_and_in_window(self, seed):
        """Noise, decaying sines and near-silent sines never read negative or non-finite."""
        rng = np.random.default_rng(seed)
        t = np.arange(_N) / _SR
        kind = seed % 3
        if kind == 0:
            buf = rng.standard_normal(_N) * rng.uniform(1e-6, 1.0)
        elif kind == 1:
            f = rng.uniform(30.0, 2000.0)
            buf = np.exp(-t * rng.uniform(1.0, 60.0)) * np.sin(2 * np.pi * f * t)
        else:
            f = rng.uniform(30.0, 2000.0)
            buf = 1e-9 * np.sin(2 * np.pi * f * t + rng.uniform(0, 6.28))
        measured = measure_fundamental(buf, _SR)
        assert math.isfinite(measured)
        assert measured == 0.0 or 40.0 <= measured <= 4000.0, measured


class TestMeasureAcRms:
    """Q25 / H4: RMS after mean removal, so DC cannot defeat the no_oscillation floor."""

    def test_dc_returns_zero(self):
        from src.maxpat.dsp_sim.measure import measure_ac_rms
        assert measure_ac_rms(np.ones(1024)) == 0.0

    def test_unit_sine_whole_periods(self):
        from src.maxpat.dsp_sim.measure import measure_ac_rms
        n = 44100  # 220 whole periods of 220 Hz
        buf = np.sin(2 * np.pi * 220.0 * np.arange(n) / 44100.0)
        assert measure_ac_rms(buf) == pytest.approx(1.0 / math.sqrt(2.0), abs=1e-3)

    def test_nan_propagates(self):
        from src.maxpat.dsp_sim.measure import measure_ac_rms
        assert math.isnan(measure_ac_rms(np.array([np.nan, 0.0, 1.0])))

    def test_empty_returns_zero(self):
        from src.maxpat.dsp_sim.measure import measure_ac_rms
        assert measure_ac_rms(np.zeros(0)) == 0.0


class TestMeasureRms:
    """Verify RMS amplitude primitive."""

    def test_zeros_returns_zero(self):
        """RMS of all-zero buffer is exactly 0.0."""
        assert measure_rms(np.zeros(1024)) == 0.0

    def test_unit_returns_one(self):
        """RMS of all-ones buffer is exactly 1.0."""
        assert measure_rms(np.ones(1024)) == 1.0


class TestMeasurePeak:
    """Verify peak-amplitude primitive (must propagate NaN)."""

    def test_returns_absolute_peak(self):
        """measure_peak picks the largest |sample|."""
        assert measure_peak(np.array([1.0, -2.5, 0.3])) == 2.5

    def test_nan_propagates(self):
        """Any NaN in the buffer collapses to NaN (runaway detector hint)."""
        result = measure_peak(np.array([np.nan, 0.0]))
        assert math.isnan(result)


# ===========================================================================
# Dataclasses (D-03 + D-05)
# ===========================================================================


class TestStepMeasurement:
    """Verify StepMeasurement field surface."""

    def test_fields_exposed(self):
        """All six required fields are float-typed and accessible."""
        m = StepMeasurement(
            param_value=0.5,
            target_hz=220.0,
            measured_hz=219.5,
            cents_offset=-3.94,
            rms_amplitude=0.5,
            peak_amplitude=0.7,
        )
        assert m.param_value == 0.5
        assert m.target_hz == 220.0
        assert m.measured_hz == 219.5
        assert m.cents_offset == pytest.approx(-3.94)
        assert m.rms_amplitude == 0.5
        assert m.peak_amplitude == 0.7


class TestClassifierThresholdsDefaults:
    """Verify D-05 LOCKED defaults are the documented baseline."""

    def test_default_values_locked(self):
        """All seven D-05 thresholds match the locked baseline."""
        t = ClassifierThresholds()
        assert t.cents_drift_limit == 5.0
        assert t.mode_competition_jump == 50.0
        assert t.amplitude_floor == 1e-4
        assert t.runaway_amplitude == 10.0
        assert t.settle_ms == 100
        assert t.sweep_steps == 32
        assert t.sample_rate == 44100


# ===========================================================================
# cents_offset helper
# ===========================================================================


class TestCentsOffset:
    """Verify cents helper."""

    def test_perfect_match_zero(self):
        """measured == target -> 0 cents."""
        assert cents_offset(220.0, 220.0) == 0.0

    def test_octave_up(self):
        """440 over 220 -> +1200 cents."""
        assert cents_offset(440.0, 220.0) == pytest.approx(1200.0)

    def test_zero_input_safe(self):
        """Non-positive input returns 0.0 (not -inf)."""
        assert cents_offset(0.0, 220.0) == 0.0
        assert cents_offset(220.0, 0.0) == 0.0
