---
phase: 261022-ud6-review-q1-q40-improvements-for-regressio
area: dsp_sim (GenExpr interpreter, codebox smoke test, pitch measure, runner, topologies)
reviewed: 2026-10-22
depth: deep
diff_range: 0f96a6f1..HEAD
files_reviewed_list:
  - src/maxpat/dsp_sim/genexpr_interp.py
  - src/maxpat/dsp_sim/smoke.py
  - src/maxpat/dsp_sim/measure.py
  - src/maxpat/dsp_sim/classifier.py
  - src/maxpat/dsp_sim/runner.py
  - src/maxpat/dsp_sim/cli.py
  - src/maxpat/dsp_sim/__init__.py
  - src/maxpat/dsp_sim/topologies/__init__.py
  - src/maxpat/dsp_sim/topologies/reed_bore.py
  - src/maxpat/dsp_sim/topologies/reed_bore_post_radiation.py
  - src/maxpat/dsp_sim/README.md
findings:
  critical: 1
  warning: 5
  info: 6
  total: 12
status: issues_found
---

# dsp_sim regression review (Q25, Q32, Q35 + 261022-cmr fix round)

`tools/genrun.py` does not exist. The genrun reference is `patches/bassoon-model/tools/genrun.py`, which was unchanged in the range.

## Baseline (all run, nothing edited)

- **Test suite.** `pytest tests/dsp_sim tests/test_genexpr_parse.py tests/test_genexpr_lint.py`: 691 passed, 4 xfailed on Python 3.14.2. Same result on Python 3.10.19 (a uv venv in scratch with numpy/scipy/pytest).
- **Repo-wide smoke.** Every git-tracked `.gendsp`, and every `.maxpat` containing `gen~`, went through `smoke_file(path, seconds=0.25)` (script: `/private/tmp/claude-501/dspsim/sweep.py`, output `sweep.json`).
  - 104 entries: **87 pass, 13 fail, 2 unsupported, 2 skipped**.
  - The 13 FAILs are 11 distinct codeboxes from 7 projects; the other 2 are .gendsp/.maxpat duplicates. Almost every one belongs to a user-confirmed-in-MAX project.
  - The 4 FAILs at the default corner reproduce with the CLI at its default 1 s (below).
  - The 261022-cmr SUMMARY's "repo-wide check" was **parse-only**. Verdicts on committed patches were never examined.
- **Bassoon drift cross-check (re the open Q25 decision).** I measured the `reed_bore_post_radiation` output two ways: with `measure_fundamental`, and with an independent Hann + 4M-point zero-padded FFT peak on harmonics 1–3.
  - They agree to within 0.05 c. Examples: 440 Hz at bore_damp 0 / 0.5 / 1 reads +11.67 / +5.77 / +2.95 c (NACF) and +11.62 / +5.78 / +2.95 c (FFT); 110 Hz reads +7.89 / +1.85 / +1.11 c on both.
  - So the strict-xfail drift is **real loop behaviour, not a detector artifact**. I did not re-report it.

## Critical Issues

### CR-01: smoke FAILs (exit 1) correct, MAX-confirmed codeboxes: `peak > 4` treats every outN as audio

**File:** `src/maxpat/dsp_sim/smoke.py:381-388` (peak FAIL), `:402-409` (silence FAIL), `:455-461` (self_sustain FAIL); the default stimulus is set at `:314-322`.

**Defect.** Every output is judged as an audio signal driven by ±0.1 noise. Codeboxes whose outlets carry Hz, ms, sample indices, voice ids or state flags, or whose inlets are triggers, frequencies or gates, get FAIL verdicts. `max-dsp-agent/SKILL.md:294-300` tells the agent to "Report any FAIL ... to the user", so these false alarms reach the user and invite "fixes" to working code.

**Evidence** (CLI, default 1 s, `--corners default`; all exit 1):

| Codebox | Output | Finding |
|---|---|---|
| `patches/minitaur/generated/minitaur.maxpat > p filter` | `out1 = 20.0 * pow(1000, clamp(in1,0,1))` (Hz) | peak 89.16 |
| `minitaur > p glide` | `out1 = 440 * pow(2, (cur-69)/12)` (Hz) | peak 8.279 |
| `patches/granularsynthtest/generated/granular-sched.gendsp` | out2 / out4 (grain start, size in samples) | peak 2.88e4 / 4410 |
| `patches/sample-layers/generated/sample-layers-slot.maxpat` | `out4 = ... / filesr * 1000` (ms) | peak 1088 |
| `patches/terrain-synth/generated/terrain-voice.maxpat` codebox 1 (#4) | `out1 = clamp(in1, 20., ...)` (Hz) | peak 20 |

Other FAILs from the 0.25 s sweep, same class:

- `kicksynth` (trigger inlet): noise retriggers it, giving peak 4.79 and self_sustain, because 0.01x noise has the same sign.
- `stutter-engine`: self_sustain at `stutter_active=max`, which is a loop repeat by design.
- `terrain-osc` / `terrain-osc-b`: self_sustain at `fb=min`, an oscillator.
- `timestretch`: silence on `out2 = max(is_tr, pre)`, a state flag, at `mode=max`.
- `patterns/gen/timing/swing-generator.gendsp`: peak 5 at swing=min.

The README documents only the "generator with an inlet" case.

**Repro:**

```
python3 -m src.maxpat.dsp_sim smoke patches/minitaur/generated/minitaur.maxpat --corners default
```

The output is `FAIL peak [default] out1: peak 89.16 > 4`, and the summary line ends in `exit 1`.

**Fix.** Make `peak` a FAIL only when it indicates runaway: the peak keeps growing (for example, the max over the last quarter of the run is more than 2x the max over the first quarter) or the output is non-finite. Report a bounded large value as a WARN `range`. Also:
- Add `--control-out K` (or a per-codebox `// smoke: control outN` comment) that skips peak, silence and self_sustain for those outlets.
- Run silence and self_sustain only on outlets that are not tagged control.
- Add one repo-wide test that pins the current verdicts of committed codeboxes (verdict counts, not file contents), so a future check change shows its false-FAIL delta.

## Warnings

### WR-01: MAX-saved `mc.gen~` codeboxes are never discovered ("without embedded patcher")

**File:** `src/maxpat/dsp_sim/smoke.py:228-240` (`inner = box.get("patcher")`), message at `:196-199`; README `:130-133`.

**Defect.** MAX saves an mc wrapper's embedded gen patcher under `box["data"]["patcher"]`, with `wrapper_uniquekey` set, not under `box["patcher"]`. Discovery then reports a false reason, "gen~ without embedded patcher or file name", and the codebox is never smoked.

**Evidence.** In `patches/ji-harmonizer/generated/ji-harmonizer.maxpat`, the `mc.gen~` box keys are `['data', ..., 'wrapper_uniquekey']`. `data.patcher` holds `in 1..3`, a 4741-char codebox and `out 1`. The sweep verdict is `unsupported: gen~ without embedded patcher or file name`, exit 3. Smoking the extracted codebox directly runs 19 corners. (It then hits the CR-01 false-silence class: in1 is a frequency.)

**Fix.** Use `inner = box.get("patcher") or (box.get("data") or {}).get("patcher")` when `first in _GEN_OBJECTS`. Add a test fixture with the `data.patcher` shape, and correct the README Discovery bullet.

### WR-02: The pitch detector reads narrow-pulse waves an octave low from about 435 Hz, inside its advertised 40 Hz–4 kHz window

**File:** `src/maxpat/dsp_sim/measure.py:131` (`_PEAK_FRACTION = 0.9`), `:213` (first lag > 0.9·max).

**Defect.** With a non-integer period, the corner-shaped NACF peak at T is sampled off its apex. For bright waveforms its integer-lag height drops below 0.9 × the peak at 2T, which happens to land nearer an integer. The detector then returns T/2 as the frequency, and the runner calls it `mode_competition` (−1200 c).

**Evidence** (dense 0.5 Hz grid, 0.5 s buffers, error > 5 c):

| Waveform | Failing points | First failure |
|---|---|---|
| 25 % pulse, 50–1000 Hz | 0 | none (the only duty the Q25 tests cover) |
| 10 % pulse, 50–1000 Hz | 34 | 856.5 Hz reads 428.2 Hz |
| 5 % pulse, 50–1000 Hz | 385 | 434.5 Hz reads 217.2 Hz |

Naive saw fails from 1603 Hz and square from 2262 Hz, both inside the window. Through the public API, `run_simulation(mirror=<5 % pulse>, params={"freq":457,"duty":0.05}, ...)` gives `mode_competition: step 0 cents_offset=-1200.0` (script: `/private/tmp/claude-501/dspsim/probe_pulse_runner.py`). Reed-flow and register-key waveforms are pulse-like, so a bright future topology in the upper register would be mis-classified. The shipped bassoon at 58–440 Hz is unaffected; the cross-check above shows it reads within 0.05 c.

**Fix.** Choose among candidate peaks by their parabolic-interpolated heights, not the raw integer-lag values. Or, after choosing period P, test the sub-multiples P/2 and P/3: if the NACF has a local max near P/k with interpolated height ≥ 0.8·M, take the shortest such period. Extend the grid test to 5 % and 10 % duty pulses and to saw/square up to 4 kHz, or narrow the documented window.

### WR-03: False "permanent silence" FAIL for correct gates and one-shot triggers whose inputs keep changing

**File:** `src/maxpat/dsp_sim/smoke.py:402-409`. WR-05 in 261022-cmr only covered inputs that do not change; this is a different false-FAIL class.

**Defect.** The 0.25 impulse crosses thresholds that the ±0.1 noise never reaches again. A correct noise gate or a trigger envelope therefore goes silent while the input "is still changing".

**Repro:**
- `Param thresh(0.05, min=0, max=0.2); out1 = abs(in1) > thresh ? in1 : 0;` gives `fail silence thresh=max (0.2)`.
- A one-shot linear-decay envelope triggered on `in1 > 0.2` gives `fail silence default`.
- The hidden ji-harmonizer mc.gen~ codebox gives `fail silence lfodeptha=max (1)`.
- Script: `/private/tmp/claude-501/dspsim/probe1.py`.

**Fix.** Demote `silence` to WARN unless the output also ignored an input that is still loud. For example, FAIL only when the tail of some inlet has |x| comparable to the level that produced the earlier activity, or rerun with the noise scaled to the impulse level and FAIL only if that run also goes silent. Document the remaining limit in the README.

### WR-04: `exp2()` is broken on the declared Python 3.10 target

**File:** `src/maxpat/dsp_sim/genexpr_interp.py:1117-1121` (`math.exp2`, added in Python 3.11), table entry `:1287`.

**Defect.** The repo README says "Python 3.10+". On 3.10, any codebox calling `exp2` raises AttributeError at build, and smoke reports `unsupported interpreter error: AttributeError: module 'math' has no attribute 'exp2'`. The suite does not catch it: 691 tests pass on 3.10 because no test uses `exp2`. No committed codebox uses it yet.

**Repro (3.10 venv):**

```
/private/tmp/claude-501/dspsim/venv310/bin/python -c "from src.maxpat.dsp_sim.smoke import smoke_codebox; print(smoke_codebox('out1 = exp2(in1);', seconds=0.05).reason)"
```

**Fix.** Use `return 2.0 ** x` inside the existing try/except (OverflowError gives inf). Add an `exp2` interpreter test.

### WR-05: The legacy CLI exit code 2 is ambiguous; Q25's new undeclared-param TopologyError returns the same code as `mode_competition`

**File:** `src/maxpat/dsp_sim/cli.py:354-356`, with `_EXIT_CODE` at `:61-67` and the README exit-code table.

**Defect.** Q25 made a misspelled `--param` or `--params` key raise TopologyError (good). The CLI maps that, and argparse usage errors, to exit 2, which the README documents as `mode_competition`. A shell gate keyed on exit codes cannot tell "typo, nothing ran" from "pitch jumped".

**Repro:**

```
python3 -m src.maxpat.dsp_sim --patch x --topology reed_bore --param bore_dmp --sweep 0,1,2 --params freq=220
```

This prints `error: topology 'reed_bore' does not declare param(s) bore_dmp...` and exits 2.

**Fix.** Return a distinct code (for example 5, or 64 for EX_USAGE) for TopologyError and usage errors, and add it to the README table and the parser description.

## Info

### IN-01: Rule-violating codeboxes pass smoke with no finding

**File:** `genexpr_interp.py:1915-1916` (Param bounds fold "per corner"); no lint at all for the other two cases.

The following each return `pass` with zero findings (probes above):
- A `for (i = 0; i < taps; i += 1)` loop with a `Param` bound. The genexpr-rules safe-construct rule says CONSTANT bounds, Params are runtime values in gen, and the Q35 spec says "constant-bound for".
- A local alias in a Param-only expression (`sr = samplerate; n = ms * 0.001 * sr;`). genexpr-rules says this fails to compile with "use of undeclared identifier".
- `peek(d, 0)` / `poke(d, v, 0)` without an explicit channel.

Suggest `loop_bound_param`, `hoist_alias` and `implicit_channel` lint WARNs, in the same style as `tab_char`.

### IN-02: The `output_typo` lint fires on ordinary names that are read

**File:** `genexpr_interp.py:1064-1071`.

`cut1 = ...; oct2 = ...; out1 = cut1 + oct2;` gives two WARNs saying "it never reaches an outlet". Both are wrong, because both names are read. Only flag `<out-like><digits>` locals that are never read.

### IN-03: A negative `--seed` produces an unhelpful error

**File:** `smoke.py:319` (`np.random.default_rng((seed, k))`).

`--seed -1` prints `error: expected non-negative integer` with exit 2 and never names the flag. Validate it in the argparse `type=` function.

### IN-04: README live-gate paragraph is stale

**File:** `README.md:259-262`.

It names `tests/dsp_sim/test_bassoon_model.py` (the file is `test_bassoon-model.py`) and says the gate "asserts verdict == pass". Since Q25 it carries strict xfails. This predates the range, but Q25 rewrote the surrounding README without fixing it.

### IN-05: README speed figures are measured on Python 3.14 only

**File:** `README.md:253-256`.

Those are not the declared 3.10 target. Either state the version as an example or re-measure on 3.10.

### IN-06: `jit.gen` / `jit.pix` without an embedded patcher are silently dropped

**File:** `smoke.py:241-245`.

They are dropped with no `skipped` entry, but README `:134` says they "are skipped" (implying a reported entry). Emit a `skipped` entry whenever `first in _SKIP_OBJECTS`.

## Spec-conformance spot checks

**Q25** (fix-plan §Q25):
- Normalized-ACF detector, early exit on the post-settle slice, AC-RMS no_oscillation, declared `PARAMS` with TopologyError, `bore_only` removed, bassoon port with genrun parity (1e-9 topology, 1e-12 interpreter), and bore_damp + 58–440 Hz sweeps with honest strict xfails: all **done as specified**. Verified by reading the code and running it; the README example runs and passes.
- The "pulse waves" regression grid covers only 25 % duty (WR-02).

**Q32:** The dsp_sim fallback removal is clean. Importing `topologies` alone works, so there is no cycle.

**Q35:**
- Interpreter subset, `smoke` command, corners, stimulus, NaN/peak/DC/silence checks, unsupported-never-passes, the unstable `tanh/tanh(g)` fixture failing, the bassoon codebox running, and "not a save gate" are all present and tested.
- The 261022-cmr review fixes are in place.
- Deferred items (WR-07, IN-01..03, the `else if`/taken-branch rule conflict) were not re-reported.

## Spec gaps

1. **Q35** says smoke "reports … peak > 4" but leaves the severity open and never says outputs can be control-rate. The implementation chose FAIL, which produces CR-01 on about 10 % of committed codeboxes. The spec needs an audio-vs-control outlet notion, or a runaway-only FAIL rule.
2. **Q35** acceptance is "the patterns/gen files pass". No criterion covers committed `patches/**` codeboxes, so the 11 false FAILs and the hidden mc.gen~ were never measured.
3. **Q35** says "constant-bound for" while the implementation accepts Param bounds. The spec does not say whether a Param bound is constant (IN-01).
4. **Q35** does not describe MAX's `data.patcher` storage for mc wrappers (WR-01).
5. **Q25** says "pulse waves" without a duty cycle, and "50–1000 Hz" while the detector window is 40 Hz–4 kHz (WR-02).
6. Neither Q25 nor Q35 requires a Python 3.10 run, which is the declared target (WR-04).
7. The default stimulus (±0.1 noise) has no spec for trigger, frequency or gate inlets. `--input` overrides disable the ring-out checks entirely, so the only escape for those codeboxes also drops self-sustain coverage.

_Reviewer: Claude (gsd-code-reviewer), deep, 2026-10-22_
