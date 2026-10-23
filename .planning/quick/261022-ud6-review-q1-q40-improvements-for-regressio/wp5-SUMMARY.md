---
quick_id: 261022-ud6
work_package: WP5
subsystem: dsp_sim (GenExpr smoke test, pitch measure, legacy CLI)
status: complete
completed: 2026-10-22
branch: worktree-agent-a4d59cc687aff65d2
commits: 6
plan_head_before: 8ddcdc496ab59093bbd9b28f74ed6e0d99e50cb9
plan_head_after: 3791150851554c404ae5dfba61c21d8695826d8c
key-files:
  created:
    - src/maxpat/dsp_sim/host_graph.py
    - tests/dsp_sim/test_smoke_ports_ud6.py
    - tests/dsp_sim/test_smoke_lint_ud6.py
    - tests/dsp_sim/test_smoke_repo.py
    - tests/dsp_sim/fixtures/repo_smoke_verdicts.json
  modified:
    - src/maxpat/dsp_sim/smoke.py
    - src/maxpat/dsp_sim/genexpr_interp.py
    - src/maxpat/dsp_sim/measure.py
    - src/maxpat/dsp_sim/cli.py
    - src/maxpat/dsp_sim/README.md
    - tests/dsp_sim/test_measure.py
    - tests/dsp_sim/test_genexpr_interp.py
    - tests/dsp_sim/test_cli.py
    - tests/dsp_sim/test_topologies.py
    - tests/dsp_sim/test_smoke.py
---

# 261022-ud6 WP5: dsp_sim review fixes

The smoke test now gets each codebox's port kinds from its host patch, so outlets carrying Hz, ms, indices or flags no longer fail as audio. Every review finding (CR-01, WR-01..05, IN-01..06) and every listed spec gap is fixed. Repo-wide verdicts went from 87 pass / 13 fail to 100 pass / 1 fail. The one remaining fail is explained below.

## Repo-wide smoke: before and after

The run covers every git-tracked `.gendsp` and every `.maxpat` containing `gen~`, using `smoke_file(path, seconds=0.25)` with all corners. This matches the review's setting. The same 104 entries were run before and after.

| | pass | fail | unsupported | skipped |
|---|---|---|---|---|
| before (8ddcdc49) | 87 | 13 | 2 | 2 |
| after (37911508) | **100** | **1** | **1** | 2 |

**Fixed: the 13 FAILs (11 distinct codeboxes, 7 projects) and the hidden mc.gen~.**
- All 10 project codeboxes now pass:
  - minitaur p filter
  - minitaur p glide
  - granular-sched (.gendsp and .maxpat)
  - kicksynth
  - sample-layers-slot
  - stutter-engine (.gendsp and .maxpat)
  - terrain-osc
  - terrain-osc-b
  - terrain-voice codebox #4
  - timestretch
- The ji-harmonizer `mc.gen~` is now discovered and passes (WR-01). Before, it was "unsupported: gen~ without embedded patcher".

**Still non-pass, both explained:**
- `patterns/gen/timing/swing-generator.gendsp`: **fail** (peak 5 at swing=min).
  - It is a phasor-domain pattern with no host patch, so its ports default to audio and bipolar noise drives `in1`.
  - Its Q35 acceptance test already feeds it `--input 1=phasor:2` and passes.
  - This is not a defect and not a user-confirmed project patch. The fix is a one-line directive, which needs an edit outside WP5's files (see Handoffs).
- `patches/max-bridge/fixtures/fx-genfail.maxpat`: **unsupported** ("assignment to Param 'g'"). This is a deliberate compile-failure fixture for the max-bridge live check. Correct.

The repo pin test `tests/dsp_sim/test_smoke_repo.py` and the fixture `tests/dsp_sim/fixtures/repo_smoke_verdicts.json` now hold these verdicts.

## Findings

| ID | Status | How | Commit |
|---|---|---|---|
| CR-01 | fixed (locked approach) | New `host_graph.py` traces each gen~ / mc.gen~ outlet downstream; detail below. | a6f05d5e |
| WR-01 | fixed | MAX saves an mc.gen~ codebox under `box["data"]["patcher"]`; discovery now reads it there, and the port tracer reads it too. README Discovery bullet corrected. | a6f05d5e |
| WR-02 | fixed | Added a sub-multiple test to the pitch detector; detail below. | b8f11dd8 |
| WR-03 | fixed | A silence hit now triggers a "loud rerun" with the audio inlets' noise raised to ±0.25. FAIL only if that run also goes silent; otherwise a `silence` WARN naming the gate / threshold / one-shot case. The positive control (`out1 = in1 * (n < 2000)`) still FAILs. | a6f05d5e |
| WR-04 | fixed | `exp2` is now `2.0 ** x` under the existing OverflowError guard. Tests cover values, overflow → inf, and a run with `math.exp2` deleted. Also verified on Python 3.10.19. | 27531d3b |
| WR-05 | fixed | Usage errors in the legacy CLI exit `EXIT_USAGE = 64` (EX_USAGE) instead of 2, which means mode_competition there. This covers TopologyError (undeclared `--param` / `--params`), argparse errors (`_UsageParser`) and a malformed `--sweep` / `--params` / `--mirror`. Documented in the module docstring, `--help` and the README exit table. The `smoke` subcommand keeps 2 = usage/read error, which is unambiguous within that subcommand. | 218bb9a6 |
| IN-01 | fixed | Three new build-time WARN lints; detail below. | 93c1c6a4 |
| IN-02 | fixed | `output_typo` fires only on locals that are never read. `cut1` and `oct2` are clean; `ou2` still warns. | 93c1c6a4 |
| IN-03 | fixed | `--seed` uses `_seed_arg`, which raises "argument --seed: must be a non-negative integer" (exit 2). `smoke_codebox(seed=-1)` raises ValueError. | a6f05d5e |
| IN-04 | fixed | README live-gate paragraph now names `test_bassoon-model.py` and describes its strict xfails. | 37911508 |
| IN-05 | fixed | README speed figures re-measured on Python 3.10.19 and 3.14.2 (within 10%), and labelled as one machine. | 37911508 |
| IN-06 | fixed | Any `jit.gen` / `jit.pix` / `jit.gl.pix` newobj is now reported as `skipped`, with or without an embedded patcher. | a6f05d5e |

### CR-01 detail

- **Outlets** are traced downstream from each gen~ / mc.gen~ box:
  - Reaching `dac~`, `ezdac~`, `plugout~`, `out~`, `gain~`, `live.gain~`, the meters, `sfrecord~` or `adoutput~` through signal consumers makes the outlet **audio**.
  - `*~` and filters pass the signal on from their left inlet.
  - The tracer follows `send~` → `receive~`, enters and leaves `p` / bpatcher / poly~ / abstraction boxes, and looks for sibling host instances of an abstraction.
  - A downstream gen~ is routed by its own codebox's value dataflow (the new `value_dependencies`).
  - Every other path is **control**.
  - An unknown host counts as audio.
- **Inlets** are traced upstream:
  - `click~` and signal comparisons → trigger
  - `sig~`, `line~`, `curve~`, `adsr~` → control
  - no signal → zero
  - anything else → audio
- **Checks by kind.** Control outputs get only the nonfinite FAIL and the new `denormal` WARN. Audio outputs get every check.
- **Standalone `.gendsp`.** Its host is found among sibling `.maxpat` files. With no host, every port is audio.
- **Directives.** `// smoke: control out2 trigger in1 in3=phasor:2` overrides the inferred kinds. Bad tokens give a `smoke_directive` WARN. The syntax is documented in the README, the CLI epilog and the `parse_directives` docstring.
- **Trigger inlets** get a `gate` stimulus (also a new `--input` SPEC).
- **Self-sustain.**
  - The rerun scales only the audio inlets plus the offline Buffer backing (new `buffer_scale` build argument).
  - With no audio inlet the codebox counts as a generator, and self-sustain is skipped.
  - The positive controls (the tanh/tanh(g) Delay fixture and the History latch) still FAIL.
- **Report.** The text report adds a `ports:` line; the JSON adds a `ports` block.

### WR-02 detail

- After the first-strong-peak pick and before refinement, the detector takes the shortest P/k (k ≤ 8) for which every peak at j·P/k has a corner apex (two-line fit) ≥ 0.95 × the apex at P.
- Running the test before refinement matters: refinement could otherwise lock onto a neighbouring multiple.
- Saw, square and 25% pulse read within 1 c across 40 Hz–4 kHz. 5% and 10% pulses read within 1 c while the pulse is ≥ 2 samples wide; that limit is documented.
- A weak-fundamental control (0.3 fundamental + strong 2nd harmonic) is not read an octave up.
- The runner-level repro (457 Hz 5% pulse) now passes.
- Bassoon strict xfails are unchanged.

### IN-01 detail

- `loop_bound_param`: a `for` bound reads a Param, `samplerate` or `vectorsize`.
- `hoist_alias`: a Param-only statement reads a bare alias such as `sr = samplerate;` or `RING = 1344000;`.
- `implicit_channel`: `peek` / `poke` called without the channel argument.
- `hoist_alias` is deliberately narrow; see MAX-confirmation item 1.

## Spec gaps

1. **Audio vs control outlets:** implemented and documented (CR-01).
2. **Acceptance on committed `patches/**`:** `test_smoke_repo.py` pins all 104 entries.
   - The default suite runs the default corner at 0.05 s, about 9 s.
   - `DSP_SIM_REPO_SWEEP=1` adds every corner at 0.25 s, about 15 minutes.
   - The review's port kinds for the false-FAIL outlets are pinned too.
3. **Constant-bound for vs Param bounds:** the interpreter still runs Param bounds (folded per corner), and `loop_bound_param` WARNs on them.
4. **MAX's `data.patcher` storage for mc wrappers:** documented and tested (WR-01).
5. **Pulse duty and detector window:** duty limit and window documented and tested (WR-02).
6. **Python 3.10:** the full suite passes on 3.10.19, and the `exp2` test also covers the case where `math.exp2` is missing.
7. **Stimulus for trigger / frequency / gate inlets:** these are inferred and keep the ring-out checks. `--input` is no longer the only escape.

## Tests

New test files:
- `tests/dsp_sim/test_smoke_ports_ud6.py`: 40 tests. Covers downstream rules, gen~ dataflow routing, subpatchers, abstractions, sibling hosts, directives, trigger/zero inlets, buffer scaling, denormal, WR-01, WR-03, IN-03, IN-06 and the report surface.
- `tests/dsp_sim/test_smoke_lint_ud6.py`: IN-01 and IN-02.
- `tests/dsp_sim/test_smoke_repo.py`: the repo pin and the review's port kinds.

Added to existing test files:
- `test_measure.py`: the WR-02 grid (saw / square / p25 to 4 kHz; p05 / p10 to the 2-sample limit), the review repros, the weak-fundamental control and the runner repro.
- `test_genexpr_interp.py`: the WR-04 tests.
- `test_cli.py` and `test_topologies.py`: WR-05. The old "exits 2" tests now assert 64.
- `test_smoke.py`: the no-string-evaluation guard now also covers `host_graph.py`.

Every new test was red before its fix.

**Final suite**, the same result on both Python 3.14.2 and 3.10.19:
- `python3 -m pytest -q`: **6784 passed, 1 skipped, 5 xfailed, 1 xpassed**.
- The skip is the opt-in full repo sweep.
- The 5 xfailed are the 4 strict bassoon drift xfails plus 1 elsewhere.
- The 1 xpassed is a non-strict xfail outside dsp_sim (round_trip / integration), not touched by WP5.
- The `tests/dsp_sim` subset alone gives 1028 passed, 1 skipped, 4 xfailed.

## Deviations

- **[Rule 1] `hoist_alias` narrowed after a repo scan.** A broad version fired on 19 committed codeboxes, including user-confirmed kicksynth, FDNVerb, bassoon and gong. The lint now flags only bare aliases read by a statement whose whole right-hand side is Param-only. It still fires on 7 entries (5 distinct codeboxes), all WARN-only: stutter-engine, brickwall-limiter, tape-wobble, stereo-feedback-delay and looper.
- **[Rule 1] gen~ routing uses codebox dataflow, not "inlet 0 only".** The first implementation read stutter's right audio channel as control: it reaches the limiter's `in2`, then dac~. Routing now uses `value_dependencies`:
  - Inlet 0 reaches every outlet whose value depends on it.
  - A later inlet reaches only the same-numbered outlet.
  - Known cost: a mixer's second input reads as control. terrain-osc-b `out1` goes to the terrain-voice mix gen~ `in2`, so it gets the lighter checks. That means less coverage, never a false FAIL. Documented in the README limits.
- **Ring-out condition widened.** Before, ring-out needed every inlet on the default stimulus. Now `gate` and `zero` inputs also allow it, and only `const` / `phasor` / `sine` disable it. README and CLI epilog updated.
- **`slow` marker reused.** The opt-in repo sweep uses the existing `slow` marker plus an env gate. `tests/conftest.py` still describes `slow` as "builds the release archive"; that description is not WP5's file (handoff).

## Handoffs

1. **`patterns/gen/timing/swing-generator.gendsp`** (and `subdivider.gendsp`): add `// smoke: in1=phasor:2 control out1` to the codebox, so a bare `smoke` run passes like the pattern test does. After that, update `swing-generator`'s entry in `tests/dsp_sim/fixtures/repo_smoke_verdicts.json` from fail to pass. Owner: the patterns / codegen work package.
2. **`tests/conftest.py`:** broaden the `slow` marker description, for example "slow test (release archive build, full repo smoke sweep)".

## Doc impacts for WP8

- **`.claude/skills/max-dsp-agent/SKILL.md` ~l.294-304 "Codebox smoke test":**
  - Peak / silence / self-sustain now apply only to audio outputs, inferred from the host patch. Control outputs (Hz, ms, indices, flags) get NaN/inf and denormal checks only.
  - Prefer smoking the host `.maxpat`; a lone `.gendsp` finds its host only among sibling `.maxpat` files.
  - Mention the `// smoke:` directive (`control outN`, `trigger inN`, `inN=SPEC`) for standalone code and patterns.
  - A `silence` WARN after a loud rerun is not a defect.
- **`TECHNICAL.md` ~l.617-620 (dsp_sim CLI exit codes):** add `64 = usage error, nothing ran (bad args, undeclared --param)`.
- **`.planning/reviews/2026-10-11-fix-plan.md` Q35 / Q25 text** (spec gaps 1-7):
  - Q35: port kinds and directives; acceptance now includes the committed-patch pin; Param loop bounds WARN.
  - Q25: pulse duty and detector window as tested (40 Hz–4 kHz; narrow pulses down to 2 samples wide).
  - Both: the declared Python 3.10 run.
- **Changelog / release notes for v6.0.0:**
  - smoke port inference and `// smoke:` directives
  - new WARN checks: `denormal`, `loop_bound_param`, `hoist_alias`, `implicit_channel`, `smoke_directive`
  - `gate` input SPEC
  - `ports` in the JSON report
  - legacy CLI usage errors exit 64
  - pitch-detector bright-waveform fix

## MAX-confirmation items

1. **`hoist_alias` vs confirmed-compiling code.** stutter's `brickwall-limiter` uses exactly the rule's failing shape: `sr = samplerate; rel = exp(-1.0 / (0.05 * sr));`. tape-wobble and stereo-feedback-delay do the same with `sr`. These patches are believed to compile in MAX. genexpr-rules.md says that shape fails with "use of undeclared identifier" (reverse-delay v0.2.1), so the rule is likely build-dependent. Confirm on the current Max build whether a bare `sr = samplerate` alias in a Param-only statement compiles; then keep, narrow or retire the rule and the WARN.
2. **Port inference heuristics.** The trigger / control / zero inlet kinds model MAX behaviour. In particular, an unconnected gen~ signal inlet reads 0, and a codebox port not wired to an `in` / `out` object is inert. No new MAX behaviour is assumed beyond that, so nothing needs a MAX test.
3. **Unchanged and still pending:** the `if` taken-branch-only semantics (pre-existing `branch_state` INFO), and the open bassoon 6–10 c drift decision. Its strict xfails were left untouched; this round's detector cross-check reads the same values.

## Self-Check: PASSED

- All files in key-files exist.
- Commits b8f11dd8, 27531d3b, 218bb9a6, 93c1c6a4, a6f05d5e and 37911508 are on branch worktree-agent-a4d59cc687aff65d2.
- `git rev-list --count 8ddcdc49..37911508` = 6.
