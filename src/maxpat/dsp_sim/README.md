# `dsp_sim` — Bassoon Waveguide Pre-Flight Stability Harness

## Scope

This module is a **bassoon-waveguide-specific pre-flight stability harness**, **not** a
general-purpose DSP simulator. It is the offline numpy simulator for the `bassoon-model`
patch: it renders a topology over a parameter sweep and classifies the output so waveguide
failures — pitch-lock / mode competition / runaway / no-oscillation — are caught **before a
bassoon patch ships**, without needing MAX running.

It exists to serve the CLAUDE.md Gen~ rule:

> **Pre-flight any new in-loop waveguide filter with a numpy simulation before committing** —
> sweep the filter's controlling Param across its full range at several target freqs and measure
> the output fundamental. If pitch moves more than a few cents across the sweep, the architecture
> is wrong.

The `smoke` subcommand (Q35) is the general-purpose exception: a GenExpr codebox smoke test for
any gen~ codebox (see [below](#python--m-srcmaxpatdsp_sim-smoke-genexpr-codebox-smoke-test)).

The two curated topologies encode the canonical bassoon signal path. If you need to broaden
this into a general DSP simulator (arbitrary gain chains, filter cascades, etc.), that is a
deferred v6.0 roadmap item — see [Scope & Future Work](#scope--future-work) below.

## The Two Topologies

Both mirror `patches/bassoon-model/generated/bassoon.gendsp` and are registered in
`topologies/__init__.py` (`TOPOLOGIES`, `get_topology(name)`):

| Name | Class | What it is |
|------|-------|------------|
| `reed_bore` | `ReedBore` | Bore + McIntyre-Woodhouse reed. The **v0.3.x ancestor** shape. |
| `reed_bore_post_radiation` | `ReedBorePostRadiation` | The genrun-parity-tested port of the **shipped** `bassoon.gendsp` loop (v0.18 DSP): phase-delay compensation, Bernoulli reed, DC-blocked cone reflection, then the post-loop reed BPF, body formant and bell LPF. Encodes the CLAUDE.md "resonant filters go POST-LOOP" invariant — the resonant sections sit in the radiation/output path, never inside the feedback loop. |

`bore_only` was removed in Q25: under constant drive it settled to DC at every setting, an impulse ring-down mostly fell below the amplitude floor, and a pitch-locked drive would measure the drive rather than the bore, so it could not pre-flight anything.

`topology=` runs reject any `sweep_param` or `params` key outside the class's `PARAMS` with `TopologyError` (before rendering); `mirror=` runs are not validated.

## The `mirror=` Escape Hatch

For off-catalogue patches you do not want to add as a permanent topology, pass a callable
instead of a topology name:

```python
run_simulation(mirror=my_stepper_factory, ...)  # mutually exclusive with topology=
```

`mirror` is a callable `(sample_rate, params) -> stepper`, where the stepper either exposes a
`.step(in1, in2) -> float` method or is itself a callable `(n_samples, params) -> ndarray`
(vectorised form). The `mirror=` callable comes from dev-authored test code only — there is no
string `eval`/`exec` and no third-party plugin loading (Phase 32 threat T-01). `topology=` and
`mirror=` are mutually exclusive; supplying both (or neither) raises `TopologyError`.

## When & How to Run

### `run_simulation(...)` API

Single entry point (`src.maxpat.dsp_sim.run_simulation`). Supply **either** `topology=` **or**
`mirror=`, a base `params` dict, the `sweep_param` name, and a `sweep=(lo, hi, n)` triple:

```python
from src.maxpat.dsp_sim import run_simulation, SimulationReport

report = run_simulation(
    patch_path="patches/bassoon-model/generated/bassoon-model.maxpat",
    topology="reed_bore_post_radiation",
    params={"freq": 220.0, "breath": 0.6},
    sweep_param="bell_bright",
    sweep=(0.0, 1.0, 32),
)
assert report.verdict == "pass", report.reason
```

The swept parameter overrides `params[sweep_param]` at each of the `n` linear steps. `freq` is
taken as the target Hz for pitch measurement. The report carries `verdict`, per-step
`measurements`, `worst_step`, a human-readable `reason`, and (on failure) a `suggested_fix`
lifted from the waveguide loop phase-comp notes.

**Pitch measurement** (`measure.measure_fundamental`). A normalized autocorrelation over a
40 Hz - 4 kHz window: the first strong peak, then a sub-multiple test (the shortest P/k whose
peaks at every j*P/k have a corner apex >= 0.95x the apex at P; 261022-ud6 WR-02), then
multi-period refinement. Sines, naive saws, squares and 25% pulses read within 1 cent across
the window; 5% / 10% pulses do while the pulse is at least 2 samples wide
(duty x samplerate / f >= 2, so up to ~1.1 kHz / ~2.2 kHz at 44.1 kHz). A narrower naive
pulse is ambiguous at the sample level: its sampled shape only repeats every few periods.

**Verdict priority cascade** (D-09) — the report reports the highest-priority failure present:

```
runaway  >  no_oscillation  >  mode_competition  >  phase_drift  >  pass
```

Runaway short-circuits the sweep so divergent topologies never run unbounded. The early exit
tests the post-settle slice of the step just measured (NaN/Inf or peak above
`runaway_amplitude`), and a sweep that stops early is reported as `runaway` ("stopped early at
step k of n"), never `pass`.

### `python -m src.maxpat.dsp_sim` CLI

The CLI wraps `run_simulation` and prints the verdict, a per-step table, and a sparkline (plus
the suggested fix on failure). Its exit code mirrors the verdict priority, so it drops into a
shell gate directly:

| Verdict | Exit code |
|---------|-----------|
| `pass` | 0 |
| `phase_drift` | 1 |
| `mode_competition` | 2 |
| `no_oscillation` | 3 |
| `runaway` | 4 |
| usage error, nothing ran | 64 |

Exit 64 (BSD `EX_USAGE`) covers argparse usage errors, a malformed `--sweep` / `--params` /
`--mirror`, and a `TopologyError` such as an undeclared `--param` or `--params` key. It is
deliberately not 2: argparse's default usage code would read as `mode_competition`.

### `python -m src.maxpat.dsp_sim smoke`: GenExpr codebox smoke test

**Advisory: not a save gate (Q35, D-07).** Nothing in the save path imports `smoke` or
`genexpr_interp` (a test pins this). Run it after writing or editing a gen~ codebox and report
FAIL / UNSUPPORTED findings; the stereo-feedback-delay v0.1.0 `tanh(x*g)/tanh(g)` runaway is
the motivating bug.

```bash
python3 -m src.maxpat.dsp_sim smoke patches/<project>/generated/<name>.maxpat
python3 -m src.maxpat.dsp_sim smoke engine.gendsp --seconds 0.25 --input 1=phasor:2 --json
```

| Flag | Default | Meaning |
|------|---------|---------|
| `PATH` | (required) | a `.gendsp` or `.maxpat` |
| `--seconds S` | `1.0` | seconds per corner run, in (0, 60] |
| `--samplerate HZ` | `44100` | in [1000, 384000] |
| `--seed N` | `1` | stimulus noise and `noise()` seed; a non-negative integer (a negative seed is a usage error naming `--seed`) |
| `--corners all\|default` | `all` | `default` runs only the default corner |
| `--no-ringout` | off | skip the ring-out checks (self_sustain, dc latch) |
| `--input K=SPEC` | by inlet kind | per-inlet stimulus override, repeatable; a K above a codebox's inlet count is not applied and gives an `unused_input` WARN on that codebox |
| `--buffer NAME=FRAMES[:CHANS]` | `48000:1` | size of the Buffer bound to buffer~ NAME, repeatable |
| `--json` | off | print one JSON object (path, seconds, samplerate, seed, corners, exit_code, codeboxes[label, verdict, reason, corners, ports{inputs, outputs, notes, host}, findings[check, severity, corner, output, detail]]) |

**Discovery.**
- `.gendsp`: the top-level gen patcher. Its ports come from every `gen~` / `mc.gen~` box in a
  sibling `.maxpat` (same directory) that loads it by name; with no such host every port is
  audio.
- `.maxpat`: every `gen~` / `mc.gen~` newobj, recursively through `p` / bpatcher / poly~
  embedded patchers (depth <= 32). An embedded gen patcher is used directly: `box["patcher"]`,
  or `box["data"]["patcher"]`, where MAX saves an `mc.gen~` wrapper's patcher (with
  `wrapper_uniquekey`). A gen~ without one is external: its name is the value after `@gen`,
  else the first non-`@` token after the object name, and only
  `<the patch's own directory>/<name>.gendsp` is opened (a name with `/`, `\` or `..` is
  unsupported). `jit.gen` / `jit.pix` / `jit.gl.pix` boxes are reported as `skipped`
  (embedded patcher or not). Comment boxes are ignored.
- A gen patcher may hold only `in N` / `out N` newobjs, codeboxes, comments and panels. Any other
  box (a `* 0.5`, a `history`, ...) makes the whole gen patcher **unsupported** (D-04).
- Each codebox runs standalone, with its port kinds taken from the host patch (below). Labels read
  `<file> > [<subpatcher> > ]<box text> > codebox K`, numbered `(#2)` when repeated.

**Ports (261022-ud6 CR-01).** Every codebox outlet is `audio` or `control`, and every inlet
`audio`, `control`, `trigger` or `zero`. The kinds come from the host patch graph
(`host_graph.py`); the text report prints them on a `ports:` line with the deciding sink or
source, and the JSON carries a `ports` block.

- **Outlets** are traced downstream through patch cords. A path that reaches `dac~`, `ezdac~`,
  `plugout~`, `out~`, `gain~` / `live.gain~`, `meter~` / `levelmeter~` / `live.meter~`,
  `sfrecord~` or `adoutput~` makes the outlet **audio**. Signal objects pass the signal on from
  their left inlet (a `*~` gain stage, a filter's input); `+~` / `-~` / `mc.pack~` /
  `mc.combine~` / `matrix~` pass every inlet, `selector~` / `gate~` their right inlets.
  `send~ X` continues at every `receive~ X` in the file, and `p` / bpatcher / poly~ /
  abstraction boxes (a sibling `<name>.maxpat`) are entered and left through their
  inlet / outlet (`in~` / `out~`) objects. A downstream `gen~` passes the value on only where its
  own codebox's value dataflow says so (`value_dependencies`): its first inlet to every outlet
  whose value depends on it, a later inlet only to the same-numbered outlet (a stereo pair).
  Index, rate, time and condition arguments carry no value.
- Everything else ends a path as **control**: parameter inlets (`*~` right inlet, a filter
  cutoff, a gen~ inlet whose value goes nowhere), generator rate inlets (`cycle~`, `phasor~`,
  `play~`, `tapout~`, ...), displays (`snapshot~`, `number~`, `scope~`) and control objects. An
  unconnected outlet is control.
- An unknown host is **audio** (full checks): a `send~` with no `receive~` in the file, an
  abstraction outlet with no instance in a sibling `.maxpat`, or a search over its budget.
- **Inlets** are traced upstream: `click~`, `train~` and signal comparisons (`>~` ... `!=~`)
  are **trigger**; `sig~`, `line~`, `curve~`, `adsr~`, `number~` and a gen~ outlet that is itself
  control are **control**; any other signal source (adc~, plugin~, oscillators, an audio gen~
  outlet, an unresolvable host) is **audio**; no signal at all (unconnected, or messages only)
  is **zero**, which is what MAX feeds the inlet. Math objects (`+~`, `*~`, `mtof~`, `slide~`,
  ...) take their strongest input kind (audio > trigger > control).
- A codebox port not wired to an `in N` / `out N` object inside the gen patcher is zero /
  control.

**`// smoke:` directives** in the codebox override the host graph (and a standalone `.gendsp`'s
all-audio default). One or more comment lines of the form

```
// smoke: control out2 out4 trigger in1 in3=phasor:2
```

A kind word applies to the ports after it: outlets take `audio` or `control`; inlets take
`audio`, `control`, `trigger` (alias `gate`) or `zero`. `inN=SPEC` sets inlet N's stimulus to
any `--input` SPEC. `--input` on the command line still wins. A token that cannot be applied (an
unknown word, a port out of range, an outlet given an inlet kind) is a `smoke_directive` WARN.

**Stimulus (D-03, D-06).** Each inlet's stimulus follows its kind; `--input K=SPEC` (or an
`inN=SPEC` directive) replaces it:

| SPEC | Signal | Default for |
|------|--------|-------------|
| `impulse+noise` | 0.25 impulse at n = 0 plus seeded uniform +-0.1 noise (`np.random.default_rng((seed, inlet))`) over the first half of the run, then zeros | audio and control inlets |
| `gate` | two 1.0 gates of `GATE_FRACTION` (0.02) x the driven window, at its start and middle, then zeros | trigger inlets |
| `zero` | zeros | zero inlets |
| `const:V` / `dc:V` | constant V for the whole run | - |
| `phasor:HZ` | 0..1 ramp at HZ (phasor-domain patterns such as swing-generator) | - |
| `sine:HZ` | sine at HZ, amplitude 0.25 | - |

The driven window is the first half whenever an inlet carries `impulse+noise` or `gate` (both
stop there), else the whole run. The second half is the ring-out window, used when
`--no-ringout` is off, some inlet carries `impulse+noise` or `gate`, and no inlet holds a
`const` / `phasor` / `sine` signal.

**Corners (D-02).** `default` (every Param at its default), then per Param in declaration order
`NAME=min (V)` and `NAME=max (V)` with the other Params at default: 1 + 2N runs. A side whose
min/max is undeclared or equal to the default is skipped. Every finding names its corner.
Param defaults and `params=` overrides are clamped to the declared [min, max] (the gen `param`
refpage: "Incoming values out of range will be clamped"; RNBO genexpr_js clamps the initial
value the same way), so `Param p(min=0.5, max=1);` runs at 0.5, not 0.

**Checks** (per output; the small self-sustain run is labelled `<corner> @0.01x`). Audio outputs
get every output check; control outputs get only `nonfinite` and `denormal` (a frequency, a
sample index or a flag is not judged by audio level, CR-01):

| Check | Definition | Constant (value) | Severity | Outputs |
|-------|------------|------------------|----------|---------|
| `nonfinite` | any NaN / inf sample; reports the first index | - | FAIL (skips the other checks for that output) | all |
| `denormal` | subnormal samples (0 < abs < 2.2e-308) in the main run; reports the count and the first index | `DENORMAL_MAX` | WARN | all |
| `peak` | max abs > limit | `PEAK_LIMIT` (4.0) | FAIL | audio |
| `silence` | the last `TAIL_FRACTION` of the driven window stays below the floor after the earlier driven window exceeded `ACTIVITY_FLOOR` (1e-6). Runs only when some audio inlet still changes over that tail (ptp > `ACTIVITY_FLOOR`), so it is skipped for 0-inlet codeboxes, all-const/zero inputs and trigger/control-only codeboxes. A hit is confirmed by a loud rerun (the audio inlets' noise raised to +-`LOUD_NOISE_AMP` = 0.25): FAIL when that run also goes silent, WARN when it stays active (a gate, threshold or one-shot that the +-0.1 noise can no longer open; WR-03) | `SILENCE_FLOOR` (1e-9), `TAIL_FRACTION` (0.1) | FAIL / WARN | audio |
| `silent` | the output never exceeds `ACTIVITY_FLOOR` | `ACTIVITY_FLOOR` (1e-6) | WARN | audio |
| `dc` | abs mean over the driven window | `DC_DRIVEN_LIMIT` (0.1) | WARN | audio |
| `dc` (dc latch) | abs mean over the last 10% of the ring-out | `DC_TAIL_LIMIT` (0.05) | WARN | audio |
| `self_sustain` | rerun with the audio inlets on `impulse+noise` and the Buffer backing at `SUSTAIN_SCALE` x (trigger / control inlets keep their stimulus; same seeds); small = detrended RMS (linear fit removed, `np.polyfit` degree 1) of the last 10% of the ring-out; FAIL when small > `SUSTAIN_ABS` and small / nominal > `SUSTAIN_RATIO`; nonfinite and peak also run on the small run. Skipped when no audio inlet is on `impulse+noise` (a codebox driven only by trigger / control inlets is a generator) | `SUSTAIN_SCALE` (0.01), `SUSTAIN_ABS` (0.01), `SUSTAIN_RATIO` (0.5) | FAIL | audio |
| `constant_assign` | an assignment to a built-in constant name (ignored; the constant wins) | - | WARN | build |
| `unsupported` | an interpreter error or unsupported construct at one corner (printed `UNSUPPORTED [<corner>] codebox: <detail>`); the other corners still run; an identical error at every corner collapses to one finding at `all corners` | - | UNSUPPORTED | build |
| `tab_char` | a tab character anywhere in the codebox; names its first line (the project's safe-construct rules say spaces only; a WARN, not unsupported, because 26 of the 54 codeboxes in Max 9.2's own Examples/gen contain tabs) | - | WARN | build |
| `output_typo` | a local such as `ou2` or `Out1` (letters within edit distance 1 of `out`, then digits) that is never read, so it never reaches an outlet (a read local such as `cut1` is not flagged) | - | WARN | build |
| `loop_bound_param` | a `for` bound that reads a Param, `samplerate` or `vectorsize`. The simulator folds it per corner, but genexpr-rules.md says CONSTANT bounds with a variable inner guard | - | WARN | build |
| `hoist_alias` | a statement whose whole right-hand side (or if condition) is Param-only and reads a bare local alias (`sr = samplerate;`, `RING = 1344000;`); genexpr-rules.md "No local aliases in Param-only expressions". Computed setup locals (`td = tanh(drive);`) and Param-only sub-expressions inside a per-sample statement are not flagged: confirmed codeboxes compile with both | - | WARN | build |
| `implicit_channel` | `peek(buf, i)` / `poke(buf, v, i)` without the channel argument the safe-construct rules require, aggregated per construct with its (first) line | - | WARN | build |
| `unused_input` | an `--input K=SPEC` with K above this codebox's inlet count | - | WARN | build |
| `smoke_directive` | a `// smoke:` token that cannot be applied | - | WARN | build |
| `branch_state` | a stateful call or write inside an if/else body: `noise phasor cycle latch dcblock poke` and `<delay>.write()`, aggregated per construct with its (first) line. Top-level if conditions, `?:` operands, History assignments and pure reads (`peek dim channels selector`) are not flagged. See the `if` limit below | - | INFO (never changes the verdict or the exit code) | build |

DC is a warning, never a fail (D-06): phasors, envelopes, random walks and sample-and-hold sit
off zero by design.

**Verdict rules.** Fail beats unsupported beats pass: any FAIL finding gives `fail` (reason
`<n> failing check(s)`, plus `; unsupported at <k> corner(s)` when a corner errored); else any
corner error gives `unsupported` (reason: the first error's text, plus ` (<k> of <M> corners)`
when only some corners errored); else `pass`. `corners` counts the corners that completed. The
severity values are `fail`, `warn`, `unsupported` and `info`, in the text report and the JSON;
`info` never changes the verdict, the exit code or the summary's warning count.

**Why self-sustain (D-05).** A `tanh(x*g)/tanh(g)` feedback loop is bounded by tanh, so it never
peaks above 4 or goes NaN; it latches into a limit cycle instead. genexpr-rules.md "In-loop
saturation" gives the reason: the small-signal loop gain is `feedback * g / tanh(g)`, above
unity at every setting. A stable (or linear) loop's tail scales with the stimulus (ratio
~0.01); a latched loop's tail does not (ratio ~1). Measured: the `Delay` fixture in
`tests/dsp_sim/test_smoke.py` (drive 4, feedback 0.6, 10 ms) has small = nominal = 0.589 and
fails at `default`, `drive=max` and `feedback=max`; its `/ drive` twin passes.

**Buffer / Data backing.** MAX's buffer~ contents are not available offline. Each `Buffer` is
48000 frames x 1 channel holding `0.25 * sin(2*pi*220*n/samplerate)`, deliberately not the run
length; `--buffer NAME=FRAMES[:CHANS]` resizes the Buffer bound to buffer~ NAME (the string
argument, else the declared name). The self-sustain rerun scales the backing by
`SUSTAIN_SCALE` with the stimulus, so a looping Buffer player is not read as a latched loop.
`Data` is zero-filled.

**Interpreter** (`genexpr_interp.py`, D-01). A tree-walking AST evaluator: lexer over Q22's
`mask()`, recursive descent plus Pratt parser, resolver, and a closure compiler (Params bound
as constants per corner, constant subtrees folded). It never generates source text and never
calls eval / exec / compile (an AST test pins it). It reproduces `patches/bassoon-model/tools/genrun.py`
on the bassoon codebox within 1e-12. Supported: Param, History (sequential), Delay
read/write, Data / Buffer peek / poke / dim / channels, if / else, constant-bound for,
`+= -= *= /=`, ternary, the math built-ins, `noise phasor cycle latch dcblock triangle selector
mc_channel`, the lowercase constants plus `phi` and the uppercase `PI TWOPI HALFPI`.
Definite assignment is checked at parse time: a local read before it is assigned on every path
is unsupported (gen's "not defined"). Names first assigned inside an if/else or for block are
local to that block, and a for loop's counter and body names do not leak past the loop, so a
value used after the block must be assigned before it. A codebox with no `outN` is unsupported
(nothing to check).
Semantics assumptions (full table in the module docstring):
- `[ASSUMED]` `/` is safediv (0 for a zero divisor); `%` is C `fmod`, 0 for a zero divisor.
- `[ASSUMED]` `noise()` is uniform in [-1, 1); `wrap` / `fold` with `hi == lo` return `lo`.
- `[ASSUMED]` `peek` floors a fractional index; out of range gives 0 (refpage boundmode ignore);
  `poke` out of range writes nothing.
- `[ASSUMED]` Delay `read(t)` clamps t to [1, N] with linear interpolation; heads advance at the
  end of the sample, so a write-then-read sees the previous samples.
- `[ASSUMED]` History is sequential: a read before the assignment sees the previous sample.
- `[ASSUMED]` comparisons, `&&`, `||` evaluate both sides and give 1.0 / 0.0; `cycle` is
  `sin(2*pi*phase)`; `selector` clamps an index above the count to the last input.
- `[ASSUMED]` a Param's initial value is clamped to [min, max] like incoming values (RNBO
  genexpr_js does this).

**Exit codes.** `0` every codebox passed (warnings allowed); `1` any FAIL; `2` usage or read
error; `3` any unsupported codebox (and no FAIL), or nothing to smoke (no gen~, only skipped
jit.gen).

**Limits.**
- Codeboxes only: gen patchers with other operators, and constructs outside the subset
  (`while`, `else if`, user functions, unimplemented Gen operators such as `sah` / `accum`,
  ...), are **unsupported**, never pass.
- `if` runs only the taken branch. This is the simulator's choice and is unconfirmed in MAX.
  The Max 9.2 GenExpr guide, RNBO genexpr_js and shipped Examples/gen (e.g.
  gen~.chopper_repeat) point to conditional execution, while genexpr-rules.md says both
  branches always execute. So a stateful call in a branch advances or writes only when that
  branch runs, and smoke flags each such codebox with an INFO `branch_state` finding. A MAX
  test is pending.
- Port inference reads one directory: hosts, abstractions and external `.gendsp` files are
  found only next to the patch (no Max search path), so a codebox hosted elsewhere is all
  audio unless a `// smoke:` directive says otherwise.
- A later inlet of a downstream gen~ passes audio on only to the same-numbered outlet. A
  mixer's second input (osc B into `in2` of a one-outlet mix codebox) therefore reads as
  control, and the upstream outlet gets the lighter checks: less coverage, never a false FAIL.
  `// smoke: audio outN` restores the full checks.
- Port kinds are object-name heuristics. A sink or source object outside the lists above is
  judged by its name: a `~` object passes its left inlet on, anything else ends the path.
- A constant-driven generator that dies (every inlet `const`/`zero`) is not caught by
  `silence`: the check needs an audio inlet that still changes. The same holds for a codebox
  driven only by trigger / control inlets.
- `--input` keys above a codebox's inlet count warn `unused_input` (in a multi-codebox file a
  smaller codebox warns too).
- A `const` / `phasor` / `sine` input (from `--input` or a directive) or `--no-ringout`
  disables the ring-out checks: such an inlet never goes quiet, so self-sustain cannot be
  judged. A generator whose only inlets are trigger / control is not judged for self-sustain;
  a generator with an audio inlet still can trip it by design: mark its inlets with a
  `// smoke:` directive or use `--no-ringout`.
- Speed (one machine, measured 2026-10-22; Python 3.10.19 and 3.14.2 within 10% of each
  other): ~1.4 us/sample for `patterns/gen/dsp/compressor.gendsp` and ~27-29 us/sample for the
  537-line bassoon codebox (about 1.2-1.3 s per simulated second). A full 37-corner bassoon
  run (`--input 1=const:220 --input 2=const:0.6`, 1 s per corner) takes about a minute; use
  `--corners default` and `--seconds` for quick checks. Expect other machines to differ.

**Repo-wide verdict pin.** `tests/dsp_sim/test_smoke_repo.py` smokes every committed `.gendsp`
and gen~ `.maxpat` and compares each codebox's verdict with
`tests/dsp_sim/fixtures/repo_smoke_verdicts.json`, so a change to the checks shows its
false-FAIL delta. The default run uses the default corner at 0.05 s (about 10 s);
`DSP_SIM_REPO_SWEEP=1` adds the full sweep at 0.25 s per corner over every corner (about
15 minutes), the setting of the 261022-ud6 review.

### Live-patch gate: `tests/dsp_sim/test_<stem>.py`

The pre-flight gate convention is a pytest file named for the patch stem: the live bassoon patch
`bassoon-model.maxpat` gets `tests/dsp_sim/test_bassoon-model.py`, which runs the topology sweeps
and asserts `report.verdict == "pass"` where the loop is expected to pass. Since Q25 it also
carries strict xfails for the measured phase_drift over the bore_damp and 58.27-440 Hz freq sweeps (the open 6-10 c
decision): they fail the suite if the drift ever disappears, so the decision gets revisited.
This is the harness referenced by the `max-dsp-agent` SKILL.md pre-flight gate (DSPSIM-01..05):
a new or modified in-loop waveguide filter must pass its `tests/dsp_sim/` sweep before the patch
is committed.

## Scope & Future Work

This module is **intentionally scoped to the bassoon waveguide today**. Broadening it with
general topologies — a simple gain chain, a feedback delay, a filter cascade — is a deferred
**v6.0 roadmap item** tracked in `.planning/PROJECT.md` (`### Future`). Until then, use the
`mirror=` escape hatch for one-off, off-catalogue patches rather than adding non-bassoon
topologies to the curated library.
