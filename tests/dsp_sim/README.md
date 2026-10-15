# DSP Pre-Flight Simulation Tests

Numpy-only offline waveguide-stability harness for MAX patches. Catches
the bassoon v0.4-0.5 class of regressions (high-Q-in-loop mode
competition; group-vs-phase-delay drift) before a patch ships. Wired
into `max-dsp-agent` via the filename convention below — see
`.claude/skills/max-dsp-agent/SKILL.md` "DSP Pre-Flight Simulation".

## Filename Convention (D-07)

Test files in this directory MUST be named `test_<patch_stem>.py` where
`<patch_stem>` is `Path(patch).stem`. Examples:

| Patch | Test fixture |
|-------|--------------|
| `patches/bassoon-model/generated/bassoon-model.maxpat` | `tests/dsp_sim/test_bassoon-model.py` |
| `patches/foo-clarinet/generated/foo-clarinet.maxpat`   | `tests/dsp_sim/test_foo-clarinet.py` |

The agent computes the stem at runtime and runs `pytest` on the file.
No registry, no marker — filename presence IS the gate.

## Topology Catalogue

| Topology | Physical model | Param surface |
|----------|---------------|---------------|
| `reed_bore` | Bore + rectified McIntyre-Woodhouse reed; no radiation | `ReedBore.PARAMS`: `freq`, `breath`, `bore_damp`, `reed_stiff`, `reed_aper`, `cone_loss` |
| `reed_bore_post_radiation` | The genrun-parity-tested port of the shipped `bassoon.gendsp` loop + post-loop reed BPF, body formant and bell LPF | `ReedBorePostRadiation.PARAMS`: the codebox Params (minus the off vibrato/noise/chiff/tongue layers) + `freq`, `breath`, `cone_loss` |

On the `topology=` path an undeclared `sweep_param` or `params` key raises `TopologyError`
before rendering (`mirror=` runs are not validated).

Off-catalogue patches use `mirror=callable` instead of `topology=name`
(D-01 escape hatch). The mirror's contract: a callable returning either
an object with `.step(in1, in2) -> float` or itself a callable
`(n_samples, params) -> ndarray`.

## Failure Modes

Verdict priority (D-09 — exclusive, single verdict per run):
`runaway > no_oscillation > mode_competition > phase_drift > pass`.

| Verdict | Threshold knob | Default | Suggested fix |
|---------|----------------|---------|---------------|
| `runaway` | `runaway_amplitude` | 10.0 (or NaN/Inf) | Loop gain >= 1. Add a saturator (tanh, clamp) or reduce reflection scalar to keep |loop_gain| < 1. |
| `no_oscillation` | `amplitude_floor` | 1e-4 | Loop dissipation likely too high. Check cone_loss / damping coefficients; verify excitation reaches the loop. |
| `mode_competition` | `mode_competition_jump` | 50 cents | Move the high-Q (Q > ~1) filter post-loop. In-loop resonant filters compete with the bore's self-excited mode and detune the fundamental. |
| `phase_drift` | `cents_drift_limit` | 5 cents | Use phase delay (atan2-based) compensation, not group delay. Onepole: pd = atan(b*sin(w)/(1-b*cos(w))) / w. Biquad: evaluate B(e^jw)/A(e^jw) phase, subtract. |

(Suggested-fix wording lifted from the archived memory note "Resonant filters belong OUT of a waveguide loop" in `.planning/quick/260703-i0t-de-duplicate-claude-md-against-the-30-fe/260703-i0t-archived-memories.md`; the shipped rule is CLAUDE.md Gen~ "Waveguide loop filters".)

## Threshold Defaults (D-05)

All seven knobs are kwarg-overridable on `run_simulation(...)`. Defaults
are tight and the override path is a quiet escape hatch, not the
documented surface.

| Knob | Default |
|------|---------|
| `cents_drift_limit` | 5.0 |
| `mode_competition_jump` | 50.0 |
| `amplitude_floor` | 1e-4 |
| `runaway_amplitude` | 10.0 |
| `settle_ms` | 100 |
| `sweep_steps` | 32 |
| `sample_rate` | 44100 |

## Writing a New Sim Test

```python
# tests/dsp_sim/test_<your-patch-stem>.py
from src.maxpat.dsp_sim import run_simulation


def test_<your_patch_stable>():
    r = run_simulation(
        patch_path="patches/<project>/generated/<your-patch-stem>.maxpat",
        topology="reed_bore_post_radiation",   # or mirror=...
        params={"freq": 220.0, "breath": 0.6, ...},
        sweep_param="<param-to-sweep>",
        sweep=(0.0, 1.0, 32),
    )
    assert r.verdict == "pass", r.reason
```

Opt-out: delete or `pytest.skip(...)` the test. There is no
`--skip-dsp-sim` flag (D-10) — opt-outs live in git history.
The bassoon gate (`test_bassoon-model.py`) carries strict xfails for the sweeps the shipped loop
fails, with the measured verdict as the reason; the gate file's docstring has the table.

## See Also

- `src/maxpat/dsp_sim/` — module source
- `.claude/skills/max-dsp-agent/SKILL.md` "DSP Pre-Flight Simulation" — agent integration
- `.planning/quick/260703-i0t-de-duplicate-claude-md-against-the-30-fe/260703-i0t-archived-memories.md`, section "Resonant filters belong OUT of a waveguide loop" — canonical phase-delay analysis (archived memory note; the shipped rule is CLAUDE.md Gen~ "Waveguide loop filters")
- `patches/bassoon-model/versions.json` — historical regressions reproduced as fixtures
