---
phase: quick-261015-m9b
verified: 2026-10-15T23:56:46Z
status: passed
score: 7/7 must-haves verified
covered_files:
  - .planning/quick/261015-m9b-implement-q25-in-planning-reviews-2026-1/261015-m9b-PLAN.md
  - .planning/quick/261015-m9b-implement-q25-in-planning-reviews-2026-1/261015-m9b-SUMMARY.md
  - src/maxpat/dsp_sim/classifier.py
  - src/maxpat/dsp_sim/measure.py
  - src/maxpat/dsp_sim/runner.py
  - src/maxpat/dsp_sim/topologies/reed_bore_post_radiation.py
  - tests/dsp_sim/test_bassoon-model.py
covered_digest: "v2:sha256:0a6d8b45b395ea0171962255b00e3c27ab1b33ec5d45eda03c0349fde7bce58b"
behavior_unverified: 0
overrides_applied: 0
---

# Quick Task 261015-m9b: Q25 dsp_sim correctness (H1-H4) Verification Report

**Goal:** Implement Q25 of `.planning/reviews/2026-10-11-fix-plan.md`: fix the dsp_sim pitch detector, close the false-PASS paths, and make the bassoon gate test the shipped loop.
**Verified:** 2026-10-15
**Status:** passed
**Re-verification:** No, initial verification.

All checks below were run by the verifier against the working tree at HEAD (8c4774ad). SUMMARY claims were not taken as evidence.

## Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | H1: 58.27 Hz sine reads 58.27; 440 Hz saw reads 440; 50-1000 Hz sine/saw/pulse grid within 0.5 cents; null inputs return 0.0 | VERIFIED | Direct call: sine 58.269999874, saw 439.99739514 (within 0.01 Hz). Independent grid of 40 geometric pitches x 3 phases x {sine, saw, 25% pulse}: worst error 0.047 cents. Constant 0.3 and all-zeros return 0.0. |
| 2 | H1 end to end: 58.27 Hz sine and 440 Hz saw mirrors PASS through `run_simulation` | VERIFIED | Covered by `TestPitchEndToEnd` in `tests/dsp_sim/test_runner.py`. All of `tests/dsp_sim` passes (377 passed, 4 xfailed). |
| 3 | H2: the early exit tests the post-settle record; an early exit is never pass | VERIFIED | Ran the repro myself. Transient-then-clean sweeps all 8 steps and gives `pass`. Transient-then-runaway gives `runaway`, worst_step 4, 5 measurements, reason "...sweep stopped early at step 4 of 8". `runner.py` breaks on `m.peak_amplitude` (the record just appended) and forces RUNAWAY if the verdict were somehow pass. |
| 4 | H4: no pitch or DC-only is `no_oscillation`; AC RMS is used; `classify([])` is not pass | VERIFIED | `classifier.py` returns NO_OSCILLATION when `measured_hz <= 0` or non-finite, and for an empty list. `runner._measure_step` uses `measure_ac_rms`. Priority order (runaway first) is preserved. Tests present and passing. |
| 5 | H4: topologies declare `PARAMS`; undeclared sweep or base params raise `TopologyError` before rendering; CLI exits 2 | VERIFIED | `run_simulation(sweep_param="bel_brigth")` raised TopologyError naming `bel_brigth` and listing declared names. CLI `--param bel_brigth` exits 2. |
| 6 | `bore_only` removed | VERIFIED | `get_topology("bore_only")` raises TopologyError. CLI `--topology bore_only` exits 2. The file is deleted. The registry contains only reed_bore and reed_bore_post_radiation. |
| 7 | H3: `reed_bore_post_radiation` is a port of the shipped codebox, with genrun parity <= 1e-9, and the gate sweeps bore_damp and 58-440 Hz honestly | VERIFIED | `test_topology_matches_shipped_codebox` (3 cases) passes. It loads the live codebox from `bassoon.gendsp` and renders it with `genrun.render`. I re-ran every sweep with default thresholds: bell_bright pass (0.00); bore_damp @58.27 pass (4.69); @110 phase_drift (6.78); @220 phase_drift (10.22); @440 phase_drift (9.06); freq sweep phase_drift (6.10). These match the SUMMARY table and the strict-xfail reasons. The four `xfail(strict=True, raises=AssertionError)` marks are accurate. Each is a genuine phase_drift above the 5-cent limit, not a coding error. |

**Score:** 7/7 truths verified.

## Constraint Checks

| Constraint | Status | Evidence |
|-----------|--------|----------|
| No file under `patches/` changed | VERIFIED | `git diff --name-only adc753c2 8c4774ad` has 0 `patches/` entries. `git status --porcelain -- patches src tests` is empty. |
| `ClassifierThresholds` defaults not loosened | VERIFIED | Defaults in `measure.py` are 5.0, 50.0, 1e-4, 10.0, 100, 32, 44100. The commit diff does not touch these lines. The bassoon tests pass no threshold or settle kwargs. |
| No `git stash` use | VERIFIED | `git stash list` is empty. |
| At least 3 `(Q25)` commits | VERIFIED | 0cd2103b, 360a98b1, 8c4774ad. All end in `(Q25)`. |
| Full suite green | VERIFIED | Full run: 4782 passed, 5 xfailed, 1 xpassed. This matches the SUMMARY: +4 strict bassoon xfails against the baseline of 4478 passed, 1 xfailed, 1 xpassed. |
| No debt markers in dsp_sim | VERIFIED | `grep` for TODO/FIXME/XXX/TBD in `src/maxpat/dsp_sim` returned nothing. |

## Anti-Patterns

None found. The one deviation reported in SUMMARY is the `importlib.import_module("genrun")` in the test fixture. It is justified by the `test_release` import scan, restores `sys.path` and `sys.modules` on teardown, and is not a stub.

## Notes for the User (not gaps)

- **Open decision from SUMMARY (A/B/C):** keep the 4 strict xfails (the current state), remove them so the gate hard-blocks every bassoon save, or open a retune task. The shipped bassoon loop genuinely fails the 5-cent `phase_drift` gate on bore_damp at 110, 220 and 440 Hz and on the freq sweep. This is reported honestly and is outside the Q25 scope, since fixing it would mean editing a committed patch.
- **Behaviour change:** any later DSP edit to `bassoon.gendsp` now fails the parity test until the topology is re-ported or the fixture is skip-marked (D-10).
- **Doc impact not edited (rule 8):** `TECHNICAL.md:616` and `.claude/skills/max-dsp-agent/SKILL.md:336` still list `bore_only`.
- **Optional MAX check:** a tuner check at 220 Hz comparing bore_damp 0 against 1. The sim predicts about +12 cents against +2 cents.

---

_Verified: 2026-10-15_
_Verifier: Claude (gsd-verifier)_
