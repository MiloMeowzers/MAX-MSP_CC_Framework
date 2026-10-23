"""Measurement primitives for the DSP pre-flight simulator.

Per Phase 32 CONTEXT.md D-03 (StepMeasurement fields) and D-05 (default
thresholds). Measurement output feeds the classifier; one StepMeasurement
per sweep step.

The primitives are intentionally small and pure (no I/O, no global state)
so the classifier can be tested against synthetic StepMeasurement lists
without driving real numpy buffers.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import scipy.signal


# ===========================================================================
# Per-step measurement record (D-03)
# ===========================================================================


@dataclass(frozen=True)
class StepMeasurement:
    """Measurement output for a single sweep step.

    Attributes:
        param_value: The swept parameter's value at this step.
        target_hz: Expected fundamental (typically `params['freq']`).
        measured_hz: Detected fundamental from autocorrelation/FFT.
        cents_offset: 1200 * log2(measured_hz / target_hz); 0 on perfect match.
        rms_amplitude: Post-settle RMS after mean removal (measure_ac_rms), which
            is what the amplitude_floor check reads; DC cannot lift a dead
            loop over the floor (Q25 / H4).
        peak_amplitude: Post-settle |peak|; NaN if any NaN in buffer.
    """

    param_value: float
    target_hz: float
    measured_hz: float
    cents_offset: float
    rms_amplitude: float
    peak_amplitude: float


# ===========================================================================
# Threshold knobs (D-05) -- frozen so classifier branches are referentially safe
# ===========================================================================


@dataclass(frozen=True)
class ClassifierThresholds:
    """Default failure-mode thresholds (D-05 LOCKED).

    All values overridable via run_simulation(...) kwargs but the override
    path is a quiet escape hatch, not the documented default.

    Attributes:
        cents_drift_limit: phase_drift trip if |max - min| cents > this.
        mode_competition_jump: mode_competition trip on |cents_offset| > this at any step.
        amplitude_floor: no_oscillation trip if rms_amplitude < this at any step.
        runaway_amplitude: runaway trip if peak_amplitude > this (or NaN/Inf).
        settle_ms: skip this many ms before measuring (transient swallow).
        sweep_steps: default linear-sweep step count.
        sample_rate: Hz; default audio rate.
    """

    cents_drift_limit: float = 5.0
    mode_competition_jump: float = 50.0
    amplitude_floor: float = 1e-4
    runaway_amplitude: float = 10.0
    settle_ms: int = 100
    sweep_steps: int = 32
    sample_rate: int = 44100


# ===========================================================================
# Measurement primitives
# ===========================================================================


def measure_rms(buf: np.ndarray) -> float:
    """RMS amplitude of a buffer.

    Returns 0.0 for an empty buffer; NaN if any sample is non-finite so that
    the classifier's runaway branch (D-09 priority 1) can short-circuit.
    """
    if buf.size == 0:
        return 0.0
    if not np.all(np.isfinite(buf)):
        return float("nan")
    return float(np.sqrt(np.mean(buf * buf)))


def measure_peak(buf: np.ndarray) -> float:
    """Absolute peak amplitude.

    Returns 0.0 for an empty buffer; NaN if any sample is NaN/Inf so the
    classifier's runaway branch sees a clear signal (D-09 priority 1).
    """
    if buf.size == 0:
        return 0.0
    if not np.all(np.isfinite(buf)):
        return float("nan")
    return float(np.max(np.abs(buf)))


def measure_ac_rms(buf: np.ndarray) -> float:
    """RMS amplitude after removing the buffer mean (Q25 / H4).

    A DC-only buffer reads 0.0, so a constant offset cannot defeat the
    classifier's amplitude_floor (no_oscillation) check. Returns 0.0 for an
    empty buffer and NaN if any sample is non-finite, the same contract as
    measure_rms.
    """
    if buf.size == 0:
        return 0.0
    if not np.all(np.isfinite(buf)):
        return float("nan")
    x = buf - np.mean(buf)
    return float(np.sqrt(np.mean(x * x)))


# Pitch-detector inspection window and peak-picking knobs (Q25 / H1).
_FMIN_HZ = 40.0
_FMAX_HZ = 4000.0
_CLARITY = 0.5
_PEAK_FRACTION = 0.9
# WR-02 (261022-ud6): sub-multiple test. A candidate period P/k is taken when
# every peak near j*P/k (j = 1..k-1) is a local maximum whose corner apex is
# at least this fraction of the corner apex at P.
_SUBMULTIPLE_FRACTION = 0.95
_SUBMULTIPLE_MAX = 8


def _corner_apex(y: np.ndarray, k: int) -> float:
    """Apex height of the NACF peak at local maximum k, modelled as a corner.

    Harmonic-rich waves (naive saw, square, pulse) have corner-shaped NACF
    peaks. Sampled half a lag off its apex, such a peak reads well below its
    true height, so its raw (or parabolic) height says nothing about how
    periodic the signal is there. Two lines, one through the two samples
    rising to the peak and one through the two falling from it, meet at the
    corner apex; that intersection is exact for a corner and slightly
    over-reads a smooth peak. Returns y[k] when the line fit does not apply.
    """
    if k < 2 or k > y.size - 3:
        return float(y[k])
    if y[k + 1] >= y[k - 1]:
        a0, a1, b0, b1 = k - 1, k, k + 1, k + 2
    else:
        a0, a1, b0, b1 = k - 2, k - 1, k, k + 1
    sa = float(y[a1] - y[a0])
    sb = float(y[b1] - y[b0])
    if not (sa > 0.0 and sb < 0.0):
        return float(y[k])
    x = (float(y[b0]) - float(y[a1]) + sa * a1 - sb * b0) / (sa - sb)
    x = min(max(x, float(a1)), float(b0))
    return float(y[a1]) + sa * (x - a1)


def _local_max_near(y: np.ndarray, centre: float):
    """The index of the largest sample within one lag of ``centre``, or None
    when it is not a local maximum (or falls off the array)."""
    lo = max(1, int(math.floor(centre)) - 1)
    hi = min(y.size - 2, int(math.ceil(centre)) + 1)
    if hi < lo:
        return None
    k = lo + int(np.argmax(y[lo:hi + 1]))
    if y[k] >= y[k - 1] and y[k] >= y[k + 1]:
        return k
    return None


def _shortest_submultiple(y: np.ndarray, period: float, start: int) -> float:
    """WR-02: the shortest true period dividing ``period``.

    The first-strong-peak rule can still land on 2T, 3T, ... when the peak at
    T is a corner sampled off its apex (a 5% pulse at 434.5 Hz read 217.2 Hz,
    a saw at 1604 Hz read 802 Hz). P/k is accepted when every peak near
    j*P/k (j = 1..k-1) is a local maximum whose corner apex is at least
    _SUBMULTIPLE_FRACTION of the apex at P. The bar is stricter than the 0.9
    first-peak rule, so a genuinely weak sub-period (a weak fundamental under
    a strong 2nd harmonic) is not read an octave up.
    """
    kp = _local_max_near(y, period)
    if kp is None:
        return period
    ref = _corner_apex(y, kp)
    if not ref > 0.0:
        return period
    best = period
    for k in range(2, _SUBMULTIPLE_MAX + 1):
        cand = period / k
        if cand < start:
            break
        ok = True
        for j in range(1, k):
            kj = _local_max_near(y, j * cand)
            if kj is None or _corner_apex(y, kj) < _SUBMULTIPLE_FRACTION * ref:
                ok = False
                break
        if ok:
            best = cand
    if best == period:
        return period
    kb = _local_max_near(y, best)
    return _parabolic(y, kb) if kb is not None else best


def _parabolic(y: np.ndarray, k: int) -> float:
    """Sub-sample peak position around index k; returns k at array edges."""
    if k < 1 or k > y.size - 2:
        return float(k)
    y0, y1, y2 = float(y[k - 1]), float(y[k]), float(y[k + 1])
    denom = y0 - 2.0 * y1 + y2
    if abs(denom) <= 1e-12:
        return float(k)
    offset = 0.5 * (y0 - y2) / denom
    offset = max(-1.0, min(1.0, offset))
    return float(k) + offset


def measure_fundamental(buf: np.ndarray, sample_rate: float) -> float:
    """Estimate the fundamental with a normalized autocorrelation (NACF).

    Algorithm (Q25 / H1):
      1. Reject buffers shorter than 64 samples or holding any non-finite
         sample; remove the mean; reject near-silence (max |x| < 1e-9).
      2. Raw autocorrelation via one FFT (scipy.signal.correlate,
         method="fft"), positive lags 0..N//2, each lag normalized by the
         energy of its overlapping region, r(k) / sqrt(E_head(k) * E_tail(k)),
         so long lags are not penalized by the shrinking overlap.
      3. Find the first zero crossing of the NACF. In the region from there
         (or the 4 kHz lag, whichever is later) to the 40 Hz lag, take the
         maximum M; below a clarity of 0.5 there is no pitch.
      4. The period is the FIRST lag whose NACF exceeds 0.9 * M, climbed to
         its local maximum and parabolic-interpolated. Taking the first
         strong peak (not the global maximum) is what stops sub-octave
         errors; starting after the zero crossing is what stops the zero-lag
         lobe being read as a 4 kHz pitch.
      4b. Sub-multiple test (261022-ud6 WR-02): a corner-shaped peak sampled
         half a lag off its apex can fall below 0.9 * M while a later
         multiple lands on an integer lag, so step 4 can still pick 2T, 3T,
         ... The shortest P/k (k <= 8) whose peaks at every j*P/k have a
         corner apex (two-line fit) >= 0.95 x the apex at P is taken.
      5. Multi-period refinement: re-locate the NACF peak near 2T, 4T, 8T, ...
         and divide by the multiple. Harmonic-rich waves (naive saw, pulse,
         square) have corner-shaped NACF peaks, so a single parabolic fit is
         biased by up to a few cents; the error stays constant per peak while
         the lag grows, so dividing by the multiple shrinks it.

    Before Q25 the detector took the global ACF maximum over the window: a
    58.27 Hz sine read 4009.09 Hz and 220 / 440 Hz saws read 109.99 Hz.

    Inspection window: [40 Hz, 4 kHz] (50 Hz, the lowest tested pitch, has
    margin). Sines, naive saws, squares and 25% pulses read within 1 cent
    across the window; 5% / 10% pulses do while the high part is at least 2
    samples wide (duty * sample_rate / f >= 2). A narrower naive pulse is
    ambiguous at the sample level: its sampled shape only repeats every few
    periods. Returns 0.0 when no clear period is found (silence, DC, noise,
    non-finite input, or a result outside the window); never a negative or
    non-finite value.

    T-04 (DoS): one FFT autocorrelation of the buffer plus O(log N)
    refinement steps; every region is bounded by the buffer size.
    """
    if buf.size < 64 or not np.all(np.isfinite(buf)):
        return 0.0
    x = np.asarray(buf, dtype=np.float64) - float(np.mean(buf))
    if float(np.max(np.abs(x))) < 1e-9:
        return 0.0
    n = x.size
    half = n // 2
    corr = scipy.signal.correlate(x, x, mode="full", method="fft")
    corr = corr[n - 1:n - 1 + half + 1]  # lags 0..N//2
    # Energy of the overlapping head x[0:N-k] and tail x[k:N] for each lag.
    csum = np.concatenate(([0.0], np.cumsum(x * x)))
    lags = np.arange(half + 1)
    e_head = csum[n - lags]
    e_tail = csum[n] - csum[lags]
    nacf = corr / np.maximum(np.sqrt(np.maximum(e_head * e_tail, 0.0)), 1e-20)

    lag_min = max(2, int(math.floor(sample_rate / _FMAX_HZ)))
    lag_max = min(half, int(math.ceil(sample_rate / _FMIN_HZ)) + 1)
    if lag_max <= lag_min:
        return 0.0
    below = np.nonzero(nacf[1:lag_max + 1] < 0.0)[0]
    if below.size == 0:
        return 0.0
    z = int(below[0]) + 1
    start = max(z, lag_min)
    if start >= lag_max:
        return 0.0
    region = nacf[start:lag_max + 1]
    peak_max = float(np.max(region))
    if peak_max < _CLARITY:
        return 0.0
    k = start + int(np.nonzero(region > _PEAK_FRACTION * peak_max)[0][0])
    while k + 1 <= half and nacf[k + 1] > nacf[k]:
        k += 1
    period = _parabolic(nacf, k)
    if not (math.isfinite(period) and period > 0.0):
        return 0.0
    # WR-02: test the sub-multiples before refining. Refinement re-locates
    # peaks within period/4 of m*period, so it must start from the true
    # period or it can lock onto a neighbouring multiple.
    period = _shortest_submultiple(nacf, period, start)
    if not (math.isfinite(period) and period > 0.0):
        return 0.0

    m = 2
    while m * period + period / 4.0 < half:
        centre = int(round(m * period))
        width = max(2, int(period / 4.0))
        lo = max(1, centre - width)
        hi = min(half, centre + width)
        if hi <= lo:
            break
        local = int(np.argmax(nacf[lo:hi + 1])) + lo
        refined = _parabolic(nacf, local) / m
        if not (math.isfinite(refined) and refined > 0.0):
            break
        period = refined
        m *= 2

    freq = float(sample_rate / period)
    if not math.isfinite(freq) or freq < _FMIN_HZ or freq > _FMAX_HZ:
        return 0.0
    return freq


def cents_offset(measured_hz: float, target_hz: float) -> float:
    """1200 * log2(measured / target).

    Returns 0.0 if either input is non-positive (avoids log of zero).
    """
    if measured_hz <= 0.0 or target_hz <= 0.0:
        return 0.0
    return 1200.0 * math.log2(measured_hz / target_hz)
