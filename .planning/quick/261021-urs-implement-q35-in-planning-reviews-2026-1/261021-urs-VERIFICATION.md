---
phase: quick-261021-urs
verified: 2026-10-22T00:00:00Z
status: passed
score: 6/6 must-haves verified
covered_files:
  - .planning/quick/261021-urs-implement-q35-in-planning-reviews-2026-1/261021-urs-PLAN.md
  - .planning/quick/261021-urs-implement-q35-in-planning-reviews-2026-1/261021-urs-SUMMARY.md
  - src/maxpat/dsp_sim/README.md
  - src/maxpat/dsp_sim/cli.py
  - src/maxpat/dsp_sim/genexpr_interp.py
  - src/maxpat/dsp_sim/smoke.py
  - tests/dsp_sim/test_genexpr_interp.py
  - tests/dsp_sim/test_smoke.py
covered_digest: "v2:sha256:76a36695e8ddce9dae90616b09e07dbd4d47d24df7deed9b8e4e396c5f45d629"
behavior_unverified: 0
overrides_applied: 0
---

# Quick 261021-urs (Q35): GenExpr interpreter + codebox smoke test Verification

**Goal:** Implement Q35: a GenExpr interpreter plus a `smoke` subcommand that runs every gen~ codebox at the Param corners and reports NaN/inf, peak > 4, DC, permanent silence and self-sustain. Unsupported never passes. Patterns pass, the `tanh/tanh(g)` fixture fails, the bassoon codebox runs. No save gating.
**Re-verification:** No, initial verification.

## Observable Truths

| # | Truth | Status | Evidence (commands I ran) |
|---|-------|--------|---------------------------|
| 1 | `smoke` runs every codebox, default 1 s at 44.1 kHz, default plus per-Param min/max corners, seeded impulse+noise, and the report names codebox, corner, output and check | VERIFIED | `smoke patterns/gen/gain/safe-gain.gendsp` printed `3 corners`, header `seconds=1 samplerate=44100 seed=1 corners=all`. Findings read `WARN silent [gain=min (0)] out1`. Help lists `--input`, `--seconds`, `--corners`, `--no-ringout`, `--buffer` and `--json`, and spells out every SPEC form. |
| 2 | Verdict and exit-code semantics: FAIL on NaN/inf, peak, silence and self-sustain. DC is WARN only. Exit 0/1/2/3 | VERIFIED | NaN codebox gives FAIL `nonfinite`, rc=1. `out1 = frobnicate(in1)` gives UNSUPPORTED, rc=3. A nonexistent file gives rc=2. `--seconds 0` gives rc=2. DC WARNs on patterns (swing, subdivider, terrain) still exit 0. |
| 3 | Unsupported never passes (unknown function, non-codebox operators, interpreter error) | VERIFIED | `frobnicate` gives `unsupported: unknown function: frobnicate (line 1)`, rc=3. A .gendsp with an extra `cycle 440` gives `UNSUPPORTED non-codebox gen operators: cycle 440`, rc=3. |
| 4 | All 19 patterns pass. The `tanh(tap*drive)/tanh(drive)` Delay fixture FAILs self-sustain at default, drive=max and feedback=max, and its `/drive` twin passes. Bassoon runs from .gendsp and .maxpat | VERIFIED | Looped all 19 `patterns/gen/*/*.gendsp` at 0.25 s: 17 gave rc=0. subdivider and swing-generator gave rc=2, but only because my zsh loop did not word-split `$extra`. Rerun by hand with `--input 1=phasor:2`, both PASS, rc=0. The fixture from tests (`_UNSTABLE_DELAY`) at 1 s gave 3 self_sustain FAILs: default (0.589 vs 0.589), drive=max and feedback=max (0.95 vs 0.95), rc=1. The twin PASSed all 5 corners, rc=0. `bassoon-model.maxpat` and `bassoon.gendsp`, with `--corners default --seconds 0.1 --input 1=const:220 --input 2=const:0.6`, both gave PASS, 0 warnings, rc=0. |
| 5 | The interpreter is a closure-compiled AST evaluator with no eval/exec/compile/__import__, and it matches genrun.py to 1e-12 | VERIFIED | grep finds no `eval(`, `exec(`, `compile(` or `__import__(` except `re.compile` regexes. `pytest test_genexpr_interp.py -k "parity or eval or ast"` gave 2 passed (parity plus the AST guard). |
| 6 | Regression and scope: genrun.py, test_bassoon-model.py and test_cli.py are unchanged. The legacy `--topology` help remains. No module outside dsp_sim imports smoke or genexpr_interp. The full-suite junit diff is clean. patches/ and patterns/ are untouched. No stash. | VERIFIED | `git diff --quiet 6bfbf1ab HEAD` on the three files shows them byte-identical. `dsp_sim --help` still lists `--topology`. grep of src outside dsp_sim finds no importer. `git diff --stat` over the task commits touches only src/maxpat/dsp_sim, tests/dsp_sim, SKILL.md and the foreign allowlist from e942ee81. `git status` is clean for src, tests, patches and patterns. `git stash list` is empty. `junit_diff.py` gave `base=5563 new=5662 added=99 offenders=0`, rc=0. |

**Score:** 6/6 truths verified.

## Required Artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| `src/maxpat/dsp_sim/genexpr_interp.py` | VERIFIED | 1974 lines. Has `class Unsupported` and `parse_codebox`, and imports `mask`, `parse_params` and `io_counts` from `genexpr_parse`. |
| `src/maxpat/dsp_sim/smoke.py` | VERIFIED | 781 lines. `smoke_main` is wired and calls `parse_codebox` at line 494. |
| `src/maxpat/dsp_sim/cli.py` | VERIFIED | Early `argv[0] == "smoke"` dispatch at line 322, with a lazy import. |
| `tests/dsp_sim/test_genexpr_interp.py` | VERIFIED | Contains the parity test, and it passes. |
| `tests/dsp_sim/test_smoke.py` | VERIFIED | Contains the `tanh(tap * drive) / tanh(drive)` fixture. |
| `src/maxpat/dsp_sim/README.md` | VERIFIED | +126 lines for the smoke section. |

## Key Links

| From | To | Status |
|------|----|--------|
| cli.py `main()` | `smoke_main` | WIRED. Ran `python -m src.maxpat.dsp_sim smoke ...` end to end. |
| smoke.py | `parse_codebox` | WIRED |
| genexpr_interp.py | genexpr_parse | WIRED |
| test_genexpr_interp.py | genrun.render | WIRED. The parity test passes. |

## Test Run

`python3 -m pytest tests/dsp_sim -q -p no:cacheprovider` gave **476 passed, 4 xfailed** in 18.5 s, up from the 377 baseline. The final full-suite run recorded in `final-rc.txt` exited 1 for one pre-existing failure. The foreign commit e942ee81 has since fixed it. The junit diff against baseline is clean.

## Anti-Patterns

None found in the new modules: no TODO/FIXME/TBD markers in the files I inspected via the grep above, no stubbed paths (the bassoon codebox with 22 Params, Data peek/poke, noise and ternaries runs, and the parity test matches genrun). Unrelated observation: the executor's note that Delay heads zero on advance is an [ASSUMED] semantic, documented in the README, and it is not a gap.

## Observations (non-blocking)

- Self-sustain fires only when the default stimulus is active on every inlet. `--input` overrides and `--no-ringout` disable it. This is documented, and a test pins it.
- The terrain-synth `.maxpat` run reports 4 pass and 2 skipped (jit.gen) with many DC WARNs, exit 0. This is the intended advisory behaviour.
- A full bassoon run takes about 48 s (37 corners), which is acceptable for an advisory tool.

## Gaps Summary

No gaps. The goal is achieved and is behaviourally evidenced by commands I ran, not by SUMMARY claims.

---

_Verified: 2026-10-22_
_Verifier: Claude (gsd-verifier)_
