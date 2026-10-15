"""Reed + bore + post-radiation waveguide topology -- the shipped bassoon loop.

Provenance (Q25 / H3): a statement-by-statement port of the codebox in
patches/bassoon-model/generated/bassoon.gendsp, DSP as of v0.18.0 and
unchanged through v0.19.1. It is parity-tested sample for sample (<= 1e-9)
against patches/bassoon-model/tools/genrun.py running the live codebox, in
tests/dsp_sim/test_bassoon-model.py, so the D-07 bassoon gate fails as soon
as this port and the shipped codebox diverge.

Lineage: this is the v0.4.2+ post-loop-radiation shape -- the resonant
sections (reed BPF, body formant, bell LPF) sit in the radiation path, never
inside the feedback loop (CLAUDE.md Gen~ rule "Waveguide loop filters").
The v0.4.0 (group-delay compensation) and v0.4.1 (in-loop bell biquad)
regressions are reproduced by mirrors in tests/dsp_sim/fixtures/, NOT here.

Ported path, in the codebox's own order and operand order:
  de-hoist (srs) -> asymmetric breath smoothing (attack_time / release_time)
  -> 30 Hz Param smoothing (bell_bright, bore_damp, reed_res_freq,
  reed_res_q, register) -> body-formant and bell RBJ coefficients ->
  analytic phase-delay compensation of the bore-damp onepole (with the
  register bias) on a half-period loop -> integer tap + first-order allpass
  (frac in [0.1, 1.1)) -> DC-blocked, inverted, lossy cone reflection ->
  Bernoulli reed (flow = 1.75 * p_close * sqrt(x) * (1 - x)) with the
  breath gate -> post-loop reed BPF (DF2T) -> bore injection -> body formant
  (DF1) -> bell LPF (DF1) -> output trim 0.25.

Excluded layers, fixed at the off value the port assumes (with these values
the codebox output is bit-identical to this port):
  - vibrato FM            vib_depth   = 0
  - reed onset drift      drift_on    = 0
  - tremolo AM            vib_amp     = 0
  - breath noise          noise_amt   = 0
  - attack chiff          chiff_amt   = 0
  - tongue burst          tongue_trig = 0
They are not in PARAMS, so sweeping one raises TopologyError rather than
silently passing. vib_rate, vib_onset_time, vib_ramp_time, vib_rate_jit and
vib_amp_lag only shape the (off) vibrato layer and are not ported.

Params are clamped to the codebox Param min/max, as gen~ does. `cone_loss`
is a sim-only knob (default 0.85 = the codebox constant; not clamped).

T-04 bounds (the codebox clamps): delta_p in [0, 1], reed_x <= 1,
cone_return in [-1.5, 1.5], bore injection in [-2, 2], loop delay in
[4, 8190] samples of an 8192-sample bore.

Per CLAUDE.md "Gen~ (GenExpr DSP Code)" Gen~ -> numpy mapping.
Per CONTEXT.md D-01 (curated catalog), D-06 (bassoon shape covered here).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import ClassVar

import numpy as np


_BORE_BUFFER_SIZE = 8192
_TWOPI = 2 * math.pi

# Codebox Param (default, min, max).
_CODEBOX_PARAMS: dict[str, tuple[float, float, float]] = {
    "reed_stiff": (0.5, 0.0, 1.0),
    "reed_aper": (0.0, -1.0, 1.0),
    "bell_bright": (0.5, 0.0, 1.0),
    "bore_damp": (0.3, 0.0, 1.0),
    "reed_res_freq": (1500.0, 500.0, 2500.0),
    "reed_res_q": (2.5, 1.0, 6.0),
    "register": (0.0, 0.0, 1.0),
    "attack_time": (15.0, 1.0, 200.0),
    "release_time": (30.0, 5.0, 500.0),
}


def _clamp(x: float, lo: float, hi: float) -> float:
    return min(max(x, lo), hi)


@dataclass
class ReedBorePostRadiation:
    """The shipped bassoon.gendsp loop + post-loop radiation chain.

    Args:
        sample_rate: Sample rate in Hz.
        params: Any of PARAMS. freq / breath are carried for the runner (the
            stepper reads in1 / in2); codebox Params are clamped to their
            codebox ranges; cone_loss defaults to 0.85.
    """

    # Declared param surface (Q25 / H4): run_simulation(topology=...) rejects
    # any sweep_param or params key outside this set with TopologyError.
    PARAMS: ClassVar[frozenset[str]] = frozenset({
        "freq", "breath", "reed_stiff", "reed_aper", "bell_bright",
        "bore_damp", "reed_res_freq", "reed_res_q", "register",
        "attack_time", "release_time", "cone_loss",
    })

    sample_rate: float
    params: dict[str, float]
    _bore: np.ndarray = field(init=False)
    _s: list = field(init=False)

    def __post_init__(self) -> None:
        p: dict[str, float] = {}
        for name, (default, lo, hi) in _CODEBOX_PARAMS.items():
            p[name] = _clamp(float(self.params.get(name, default)), lo, hi)
        self._p = p
        self._cone_loss = float(self.params.get("cone_loss", 0.85))
        self._bore = np.zeros(_BORE_BUFFER_SIZE, dtype=np.float64)

        one = 1.0
        srs = float(self.sample_rate) * one
        self._srs = srs
        k_attack_time = p["attack_time"] * one
        k_release_time = p["release_time"] * one
        self._k_reed_stiff = p["reed_stiff"] * one

        # Breath smoothing coefficients (state-independent).
        atk_s = max(k_attack_time, 0.5) * 0.001
        rel_s = max(k_release_time, 0.5) * 0.001
        self._breath_a_atk = 1.0 - math.exp(-1.0 / (srs * atk_s))
        self._breath_a_rel = 1.0 - math.exp(-1.0 / (srs * rel_s))

        # 30 Hz Param smoothing coefficient.
        param_fc = 30.0
        self._param_a = 1.0 - math.exp(-_TWOPI * param_fc / srs)

        # Body formant: RBJ peaking EQ (fixed).
        bf_fc = 500.0
        bf_q = 3.0
        bf_a = 1.41421356
        bf_w = _TWOPI * bf_fc / srs
        bf_cos = math.cos(bf_w)
        bf_sin = math.sin(bf_w)
        bf_alph = bf_sin / (2.0 * bf_q)
        bf_b0u = 1.0 + bf_alph * bf_a
        bf_b1u = -2.0 * bf_cos
        bf_b2u = 1.0 - bf_alph * bf_a
        bf_a0u = 1.0 + bf_alph / bf_a
        bf_a1u = -2.0 * bf_cos
        bf_a2u = 1.0 - bf_alph / bf_a
        bf_inv = 1.0 / bf_a0u
        self._bf = (
            bf_b0u * bf_inv, bf_b1u * bf_inv, bf_b2u * bf_inv,
            bf_a1u * bf_inv, bf_a2u * bf_inv,
        )

        # Loop state, in History order. Smoothed Params start at their
        # codebox History initial values (not at the Param values).
        self._s = [
            0.0,     # 0  ap_x_prev
            0.0,     # 1  ap_y_prev
            0.0,     # 2  bell_x1
            0.0,     # 3  bell_x2
            0.0,     # 4  bell_y1
            0.0,     # 5  bell_y2
            0.0,     # 6  bf_x1
            0.0,     # 7  bf_x2
            0.0,     # 8  bf_y1
            0.0,     # 9  bf_y2
            0.0,     # 10 cone_dc
            0.0,     # 11 bore_lp
            0.0,     # 12 bore_wi
            0.0,     # 13 breath_state
            0.0,     # 14 reed_bp_v1
            0.0,     # 15 reed_bp_v2
            0.5,     # 16 bell_bright_s
            0.3,     # 17 bore_damp_s
            1500.0,  # 18 reed_res_freq_s
            2.5,     # 19 reed_res_q_s
            0.0,     # 20 register_s
        ]

    def step(self, in1: float, in2: float) -> float:
        """One sample of the shipped loop. in1 = freq Hz, in2 = breath 0..1."""
        (ap_x_prev, ap_y_prev, bell_x1, bell_x2, bell_y1, bell_y2,
         bf_x1, bf_x2, bf_y1, bf_y2, cone_dc, bore_lp, bore_wi,
         breath_state, reed_bp_v1, reed_bp_v2, bell_bright_s, bore_damp_s,
         reed_res_freq_s, reed_res_q_s, register_s) = self._s
        p = self._p
        srs = self._srs
        bore = self._bore
        exp = math.exp
        sin = math.sin
        cos = math.cos

        # --- Breath smoothing: asymmetric onepole ---
        breath_in = _clamp(in2, 0.0, 1.0)
        breath_a = (
            self._breath_a_atk if breath_in > breath_state else self._breath_a_rel
        )
        breath_state = breath_state + breath_a * (breath_in - breath_state)

        # --- Param smoothing: 30 Hz onepole ---
        param_a = self._param_a
        bell_bright_s = bell_bright_s + param_a * (p["bell_bright"] - bell_bright_s)
        bore_damp_s = bore_damp_s + param_a * (p["bore_damp"] - bore_damp_s)
        reed_res_freq_s = reed_res_freq_s + param_a * (p["reed_res_freq"] - reed_res_freq_s)
        reed_res_q_s = reed_res_q_s + param_a * (p["reed_res_q"] - reed_res_q_s)
        register_s = register_s + param_a * (p["register"] - register_s)

        # Tremolo, breath noise, chiff, tongue and vibrato FM are off.
        breath = breath_state
        freq_mod = max(in1, 20.0)

        # --- Bell radiation LPF: RBJ Butterworth (variable fc) ---
        bell_fc = 1500.0 + bell_bright_s * 3500.0
        bell_q = 0.7071068
        wc = _TWOPI * bell_fc / srs
        cos_wc = cos(wc)
        sin_wc = sin(wc)
        alpha_bq = sin_wc / (2.0 * bell_q)
        b0u = (1.0 - cos_wc) * 0.5
        b1u = 1.0 - cos_wc
        b2u = (1.0 - cos_wc) * 0.5
        a0u = 1.0 + alpha_bq
        a1u = -2.0 * cos_wc
        a2u = 1.0 - alpha_bq
        inv_a0 = 1.0 / a0u
        b0 = b0u * inv_a0
        b1 = b1u * inv_a0
        b2 = b2u * inv_a0
        a1 = a1u * inv_a0
        a2 = a2u * inv_a0

        # --- Analytic phase-delay compensation (half-period loop) ---
        w = _TWOPI * freq_mod / srs
        bore_damp_eff = bore_damp_s * (1.0 - register_s) + 0.6 * register_s
        bore_fc = 1000.0 + bore_damp_eff * 7000.0
        bore_a = 1.0 - exp(-_TWOPI * bore_fc / srs)
        bore_b = 1.0 - bore_a
        bore_pd_den = 1.0 - bore_b * cos(w)
        bore_pd_num = bore_b * sin(w)
        bore_pd_samples = math.atan(bore_pd_num / bore_pd_den) / max(w, 0.0001)

        half_period = srs / (2.0 * freq_mod)
        adjusted = half_period - bore_pd_samples
        adjusted = max(adjusted, 4.0)
        adjusted = min(adjusted, 8190.0)
        int_part = math.floor(adjusted - 0.1)
        frac = adjusted - int_part
        eta = (1.0 - frac) / (1.0 + frac)

        # --- Bore read: integer tap + first-order allpass ---
        wi = bore_wi
        ri = wi - int_part
        if ri < 0:
            ri = ri + 8192
        x_int = float(bore[int(ri)])
        bore_return = eta * x_int + ap_x_prev - eta * ap_y_prev
        ap_x_prev = x_int
        ap_y_prev = bore_return

        # --- Cone apex reflection: DC-blocked, inverted, lossy ---
        cone_alpha = 0.0002
        cone_loss = self._cone_loss
        cone_dc_n = cone_dc + cone_alpha * (bore_return - cone_dc)
        cone_hp = bore_return - cone_dc_n
        cone_dc = cone_dc_n
        bore_lp_n = bore_lp + bore_a * (cone_hp - bore_lp)
        bore_lp = bore_lp_n
        reg_refl_gain = 1.0 - register_s * 0.3
        cone_return = -bore_lp_n * cone_loss * reg_refl_gain
        cone_return = _clamp(cone_return, -1.5, 1.5)

        # --- Bernoulli reed ---
        k_reed_stiff = self._k_reed_stiff
        p_close = 0.65 + 0.35 * k_reed_stiff
        delta_p = breath * 0.9 - cone_return + p["reed_aper"]
        delta_p = _clamp(delta_p, 0.0, 1.0)
        reed_x = min(delta_p / p_close, 1.0)
        reed_flow = 1.75 * p_close * math.sqrt(reed_x) * (1.0 - reed_x)
        reed_gate = _clamp(breath_state * 8.0, 0.0, 1.0)
        reed_flow = reed_flow * reed_gate
        stiff_gain = 0.75 - k_reed_stiff * 0.45
        reed_sig = reed_flow * stiff_gain

        # --- Reed resonance BPF (post-loop, DF2T) ---
        rw = _TWOPI * reed_res_freq_s / srs
        rsin = sin(rw)
        ralpha = rsin / (2.0 * max(reed_res_q_s, 0.1))
        ra0 = 1.0 + ralpha
        r_inv_a0 = 1.0 / ra0
        rb0 = rsin * 0.5 * r_inv_a0
        rb2 = -rb0
        ra1 = -2.0 * cos(rw) * r_inv_a0
        ra2 = (1.0 - ralpha) * r_inv_a0
        reed_filt = rb0 * reed_sig + reed_bp_v1
        reed_bp_v1 = reed_bp_v2 - ra1 * reed_filt
        reed_bp_v2 = rb2 * reed_sig - ra2 * reed_filt

        # --- Bore injection ---
        bore_in_s = reed_sig + cone_return
        bore_in_s = _clamp(bore_in_s, -2.0, 2.0)
        bore[int(wi)] = bore_in_s
        bore_wi = wi + 1
        if bore_wi >= 8192:
            bore_wi = 0

        # --- Radiation chain (post-loop): body formant -> bell LPF, DF1 ---
        bf_b0, bf_b1, bf_b2, bf_a1, bf_a2 = self._bf
        rad_in = cone_hp + reed_filt
        bf_out = (bf_b0 * rad_in
                  + bf_b1 * bf_x1
                  + bf_b2 * bf_x2
                  - bf_a1 * bf_y1
                  - bf_a2 * bf_y2)
        bf_x2 = bf_x1
        bf_x1 = rad_in
        bf_y2 = bf_y1
        bf_y1 = bf_out
        rad_out = (b0 * bf_out
                   + b1 * bell_x1
                   + b2 * bell_x2
                   - a1 * bell_y1
                   - a2 * bell_y2)
        bell_x2 = bell_x1
        bell_x1 = bf_out
        bell_y2 = bell_y1
        bell_y1 = rad_out

        self._s = [
            ap_x_prev, ap_y_prev, bell_x1, bell_x2, bell_y1, bell_y2,
            bf_x1, bf_x2, bf_y1, bf_y2, cone_dc, bore_lp, bore_wi,
            breath_state, reed_bp_v1, reed_bp_v2, bell_bright_s, bore_damp_s,
            reed_res_freq_s, reed_res_q_s, register_s,
        ]
        return rad_out * 0.25
