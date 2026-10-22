---
phase: quick-261021-urs
plan: 01
status: complete
subsystem: dsp_sim
tags: [genexpr, gen~, interpreter, smoke-test, dsp_sim, Q35]
requires:
  - src/maxpat/genexpr_parse.py (Q22 mask / parse_params / io_counts / CONSTANTS)
  - patches/bassoon-model/tools/genrun.py (parity reference, unchanged)
provides:
  - src/maxpat/dsp_sim/genexpr_interp.py (parse_codebox -> Codebox.build -> Program.run, Unsupported)
  - "`python -m src.maxpat.dsp_sim smoke <file.gendsp|file.maxpat>`"
affects:
  - src/maxpat/dsp_sim/cli.py (early `smoke` dispatch; legacy surface unchanged)
  - .claude/skills/max-dsp-agent/SKILL.md (advisory pointer)
tech-stack:
  added: []
  patterns:
    - AST compiled once into nested Python closures over a flat float slot list (no eval/exec)
    - Params bound as constants per corner; constant subtrees folded without reassociation
    - per-call-site state cells for stateful Gen built-ins
    - self-sustain = 0.01x stimulus rerun, detrended tail RMS ratio
key-files:
  created:
    - src/maxpat/dsp_sim/genexpr_interp.py
    - src/maxpat/dsp_sim/smoke.py
    - tests/dsp_sim/test_genexpr_interp.py
    - tests/dsp_sim/test_smoke.py
  modified:
    - src/maxpat/dsp_sim/cli.py
    - src/maxpat/dsp_sim/README.md
    - .claude/skills/max-dsp-agent/SKILL.md
decisions:
  - "Smoke driven window ends at N/2 whenever any inlet carries the default stimulus (not only when ring-out is active) so --no-ringout and mixed overrides cannot raise a false silence FAIL"
  - "Declarations after a statement or inside a block are Unsupported (gen~ requires declarations first; never a false pass)"
  - "Delay head advance zeroes the new head slot, so a sample with no write reads as 0 [ASSUMED]"
  - "Repeated .maxpat labels are numbered (#2); labels carry the subpatcher chain"
  - "Speed rule did not fire (bassoon 1.13 s per simulated second < 3 s); interpreter left unspecialised beyond Task 1 shapes"
  - "No threshold retune: all 19 patterns pass at the planned values"
metrics:
  duration: "~75 min (resumed session; Step 0 baseline done by the previous executor)"
  completed: 2026-10-22
estimate:
  tokens: 230000
  tasks: 3
actuals:
  tokens: 34300
  tasks: 3
  commits: 6
plan_head_before: 6bfbf1ab8c3496c9b7e7097d735389047f954c6b
plan_head_after: e942ee8192eac18282329a584c95351a16678422
---

# Quick 261021-urs Plan 01: GenExpr interpreter + codebox smoke test (Q35) Summary

The new `python -m src.maxpat.dsp_sim smoke` command runs every gen~ codebox in a .gendsp or .maxpat at the default and per-Param min/max corners. It uses a closure-compiled AST interpreter that reproduces genrun.py on the bassoon codebox within 1e-12. NaN/inf, peak > 4, permanent silence and self-sustain FAIL; DC only warns; unsupported never passes. All 19 patterns pass. The `tanh(x*g)/tanh(g)` Delay fixture FAILs self-sustain, and the `/ drive` twin passes.

## Commits

| Task | Commit | Message |
|------|--------|---------|
| 1 (tracer) | 5f384f85 | feat(dsp_sim): GenExpr interpreter core + codebox smoke tracer |
| 2 RED | bc27b906 | test(dsp_sim): failing state-construct and self-sustain tests |
| 2 GREEN | 15dec047 | feat(dsp_sim): Delay/Data/Buffer, for loops, stateful built-ins, self-sustain check, genrun parity |
| 3 RED | d2024717 | test(dsp_sim): Q35 smoke acceptance tests |
| 3 GREEN | 0accfea9 | feat(dsp_sim): smoke .maxpat discovery, --json/--buffer, speed pass, Q35 acceptance + docs |

`commits: 6` is measured as `git rev-list --count 6bfbf1ab..HEAD`. It includes **e942ee81**, `fix(ci): register q29-check in README patch table and Q24 allowlist`. That commit is by Taylor Brook at 08:37, landed on main while the final gate ran, and is not part of this plan. It touches only README.md and tests/uninitialized_state_allowlist.json, and it fixes both baseline failures. This plan made 5 commits.

## What was built

- **genexpr_interp.py** (D-01):
  - The pipeline: lexer over `mask()`, recursive descent for statements, Pratt for expressions, a frozen-dataclass AST, then the resolver and closure compiler.
  - The closures are specialised for `slot op const`, `const op slot` and `slot op slot` binary shapes and for Assign(slot, expr).
  - `Program.run` resets the I/O and locals with one slice assignment per sample.
  - Constructs covered: Param, sequential History, Delay read/write, Data/Buffer peek/poke/dim/channels, if/else, constant-bound for (LOOP_CAP 100000), the math built-ins, and noise/phasor/cycle/latch/dcblock/triangle/selector/mc_channel.
  - Constants: the lowercase names plus `phi` and `PI TWOPI HALFPI`. The 162 GEN_OPERATOR_NAMES come from the Max 9.2.0 refpages.
  - STATE_CAP is 50M samples.
- **smoke.py**:
  - Discovery: .gendsp; .maxpat with embedded gen~/mc.gen~; the sibling external .gendsp; jit.gen skipped; non-codebox gen operators unsupported.
  - Stimulus: seeded impulse+noise, plus the `--input K=SPEC` overrides.
  - Corners per D-02.
  - Checks: nonfinite, peak, silence, silent, dc, dc latch, self_sustain and constant_assign.
  - Output: a text report and `--json`, with `--buffer`. Exit codes 0/1/2/3.
- **cli.py**: an early `smoke` dispatch before `build_parser()`; the legacy flags, exit codes and test_cli.py are unchanged.
- **Docs**:
  - The README `smoke` section covers usage and flags, discovery, stimulus, corners, the checks table, the self-sustain rationale, Buffer/Data backing, the [ASSUMED] semantics, exit codes, limits, speed and the advisory status.
  - SKILL.md gains a `### Codebox smoke test (advisory)` pointer, with a bash block and no Python block.

## Speed (D-01)

| Codebox | µs/sample | s per simulated second |
|---------|-----------|------------------------|
| patches/bassoon-model/generated/bassoon.gendsp (537 lines, default corner, `1=const:220 2=const:0.6`) | 25.6 | 1.13 |
| patterns/gen/dsp/compressor.gendsp (default corner) | 1.3 | 0.057 |

The rule threshold is about 3 s per simulated second, so it did not fire and genexpr_interp.py was not touched in Task 3. A full bassoon run takes about 48 s wall time: 37 corners, 1 s each, with the const overrides so there is no ring-out rerun. Verdict PASS, 0 warnings.

## 1 s pattern sweep (final gate, `smoke_file` defaults; phasor:2 on in1 for swing-generator and subdivider)

| Pattern | Verdict | Corners | Warnings |
|---------|---------|---------|----------|
| buffer/buffer-player | pass | 6 | silent x2 (start=max, end=min: zero-length range) |
| buffer/buffer-recorder | pass | 3 | dc x1, dc latch x1, silent x2 |
| dsp/compressor | pass | 10 | - |
| dsp/multi-tap-delay | pass | 7 | - |
| dsp/noise-generator | pass | 2 | - |
| dsp/simple-reverb | pass | 7 | - |
| gain/safe-gain | pass | 3 | silent x1 (gain=min) |
| gain/soft-clipper | pass | 2 | - |
| ramps/adsr-envelope | pass | 9 | dc x7, dc latch x7 |
| ramps/ar-envelope | pass | 5 | dc x3, dc latch x1 |
| ramps/exp-curve | pass | 3 | dc x1, silent x1 (curve=max) |
| ramps/smooth-ramp | pass | 3 | - |
| random/random-walk | pass | 8 | dc x8 |
| random/sample-and-hold | pass | 4 | silent x4 (trigger never crosses 0.5) |
| smoothing/lag-processor | pass | 5 | dc latch x2 |
| smoothing/one-pole-smooth | pass | 3 | - |
| timing/master-clock | pass | 5 | dc x5 |
| timing/subdivider | pass | 3 | dc x3 |
| timing/swing-generator | pass | 3 | dc x3 |

No pattern is allowlisted or xfailed, and none was edited.

**Fixture numbers (self_sustain, small at 0.01x vs nominal at 1x, detrended tail RMS):**
- Delay fixture at 1 s:
  - default: 0.589 vs 0.589;
  - drive=max: 0.6 vs 0.6;
  - feedback=max: 0.95 vs 0.95;
  - FAIL at all three, with no finding at drive=min or feedback=min.
- History latch at 0.25 s: 0.983 vs 0.983 at default.
- The `/ drive` twin passes at all 5 corners.

## Threshold retune

None. The values are the planned ones: SILENCE_FLOOR 1e-9, ACTIVITY_FLOOR 1e-6, DC_DRIVEN_LIMIT 0.1, DC_TAIL_LIMIT 0.05, SUSTAIN_ABS 0.01, SUSTAIN_RATIO 0.5, TAIL_FRACTION 0.1, PEAK_LIMIT 4.0.

## Final gate

- Baseline (Step 0, previous executor, base 6bfbf1ab): pytest rc **1**, with 2 failed, 5555 passed, 5 xfailed and 1 xpassed. The two failures:
  - `test_doc_signatures::test_readme_patch_table_lists_every_project` (q29-check missing from the README table);
  - the `test_uninitialized_state` q29-check allowlist case.
- Final: `rm -f final-junit.xml` first, then the full run gave pytest rc **1**, with 1 failed, 5655 passed, 5 xfailed and 1 xpassed (161 s).
  - The one failure is the pre-existing README patch table test. Foreign commit e942ee81 fixed it mid-run.
  - The q29-check allowlist case went failed → passed because of that same foreign commit.
  - A rerun of `tests/dsp_sim tests/test_doc_signatures.py tests/test_agent_skills.py tests/test_uninitialized_state.py` at HEAD gives 938 passed, 4 xfailed.
- `junit_diff.py baseline-junit.xml final-junit.xml` exits **0**: `base=5563 new=5662 added=99 offenders=0`. All 99 added tests are under `tests.dsp_sim.test_smoke` / `tests.dsp_sim.test_genexpr_interp` and pass.
- How junit_diff.py classifies a collection error:
  - pytest writes it as a testcase with an empty classname and an `<error>` child, so its key is `::<module>`. That key starts with neither allowed prefix, so it is reported as **FOREIGN**.
  - An aborted run also leaves every baseline test missing, and those are each reported as **REMOVED**.
  - A missing or unparsable junit file makes `ET.parse` raise, and the script exits non-zero.
  - A collection error (pytest rc 2) also fails the gate by itself through the `rc <= 1` check.
- `git status --porcelain patches patterns`: empty. `git stash list`: equals stash-list-before.txt (empty).
- genrun.py, test_bassoon-model.py and test_cli.py are byte-identical to base-sha.

Artifacts in QDIR: final-junit.xml, final-pytest-out.txt, final-rc.txt.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Driven window under `--no-ringout` / mixed overrides**
- **Found during:** Task 1 (smoke core design).
- **Issue:** The plan sets the driven window to [0, N) whenever ring-out is off. The default stimulus still stops at N/2, though. With `--no-ringout`, or with one inlet overridden and another on the default, a decaying linear codebox such as one-pole-smooth reads below 1e-9 over the last 10% of [0, N) and gets a false `silence` FAIL.
- **Fix:** The driven window is [0, N/2) whenever any inlet carries the default stimulus, and [0, N) only when every inlet is overridden or there are no inlets. Ring-out still runs only when every inlet is on the default and ringout is on. This is documented in the README.
- **Files:** src/maxpat/dsp_sim/smoke.py. **Commit:** 5f384f85.

**2. [Rule 1 - Bug] Identical labels for repeated gen~ boxes**
- **Found during:** Task 3 (terrain-synth discovery).
- **Issue:** The two `gen~` boxes in `p terrain-view-a` both produced `... > gen~ > codebox 1`.
- **Fix:** Labels include the subpatcher chain, and repeats get a ` (#2)` suffix.
- **Files:** smoke.py. **Commit:** 0accfea9.

**3. [Rule 1 - Test correction] buffer-player `--buffer bufname=1000:2` expectation**
- **Found during:** Task 3 GREEN.
- **Issue:** My RED test expected exit 0. With a 1000-frame Buffer, though, the one-shot corner `loop=min (0)` legitimately runs off the end within 0.1 s and goes permanently silent.
- **Fix:** The test now asserts exactly that `silence` FAIL at `loop=min (0)` with `--buffer`, and a pass without it. This proves dim reads 1000. A dedicated `dim(buf) / 250 + (channels(buf) != 2) * 10` codebox pins dim and channels. The behaviour is unchanged and the pattern still passes at the default backing.
- **Files:** tests/dsp_sim/test_smoke.py. **Commit:** 0accfea9.

**4. [Rule 2 - Correctness] Declarations after a statement are Unsupported**
- **Found during:** Task 1.
- gen~ rejects a declaration after an expression (CLAUDE.md declaration ordering), so accepting one would be a false pass. Declarations inside a block are also Unsupported.
- **Commit:** 5f384f85.

### Notes
- Delay heads zero the new head slot on advance, so a sample with no `write` reads as 0 rather than stale data from N+2 samples ago. Reads never touch the head index, so the planned read semantics are unchanged. This is [ASSUMED] and documented in the docstring.
- The plan's Task 3 `<verify>` first segment includes test_doc_signatures.py. At this plan's last commit it failed only on the pre-existing q29-check README test, which foreign commit e942ee81 has since fixed (now green at HEAD).
- The plan's README limit text says "45-corner bassoon run". The measured count is 37 corners, because Params whose min or max equals the default are skipped. The README records 37 corners and about 48 s.

## Known Stubs

None.

## Threat Flags

None. The only new surfaces are the planned ones: an offline reader of untrusted .maxpat/.gendsp, and sibling-directory .gendsp resolution. Both are mitigated per T-urs-01..06 and covered by the tests: the AST no-eval guard, the no-save-gate import guard, the plain-file-name check, the caps and the depth limit.

## Self-Check: PASSED

- FOUND: src/maxpat/dsp_sim/genexpr_interp.py, src/maxpat/dsp_sim/smoke.py, tests/dsp_sim/test_genexpr_interp.py, tests/dsp_sim/test_smoke.py
- FOUND commits: 5f384f85, bc27b906, 15dec047, d2024717, 0accfea9
