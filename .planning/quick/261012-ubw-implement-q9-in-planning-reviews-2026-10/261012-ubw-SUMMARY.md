---
phase: quick-261012-ubw
plan: 01
subsystem: tools/audit
status: complete
tags: [Q9, S6, help-io, oracle, audit_db, baseline]
requires: []
provides:
  - "python3 tools/audit_db.py --help-io (help-box I/O oracle, --packages-dir, --write-baseline)"
  - "tools/help_io.py public API: box_args, signal_class, discover_sources, scan_help_io, build_baseline, dump_baseline, diff_baselines, format_help_io_summary"
  - "tests/fixtures/help_io_baseline.json (Max 9.2.0 + this Mac's 14 packages)"
affects: [Q10, Q11, Q33, Q38]
tech-stack:
  added: []
  patterns:
    - "Committed canonical baseline + requires_max live diff that skips on a Max version change"
key-files:
  created:
    - tools/help_io.py
    - tests/test_help_io.py
    - tests/fixtures/help_io_mini_baseline.json
    - tests/fixtures/help_io_baseline.json
  modified:
    - tools/audit_db.py
decisions:
  - "OQ1 resolved by default with option A: newobj boxes plus non-newobj boxes whose maxclass resolves in the DB (keyed by maxclass, no args)"
  - "Baseline keyed by literal names (sel/select, r/receive, t/trigger separate); help_io never imports tools.audit_db"
  - "Live test diffs only sources at equal version; a stale bundle skips with the re-baseline command"
metrics:
  duration: "~13 min"
  completed: 2026-10-13
commits: 3
plan_head_before: cd5a88524d97b06372738c2e9180a7963153605a
plan_head_after: 917fd14d32f42920be52c9d9678c5a897193ea14
actuals:
  tokens: 46700
  tasks: 3
  commits: 3
---

# Phase quick-261012-ubw Plan 01: Help-box I/O oracle (Q9) Summary

`python3 tools/audit_db.py --help-io` compares the I/O MAX saved into 3,430 help files (the 9.2.0 bundle plus 14 installed packages) with `compute_io_counts` and `get_outlet_types`. Its committed baseline records 441 mismatching names, and a `requires_max` test fails if any name's mismatch count goes up.

## Commits

| Task | Commit | Message |
|---|---|---|
| 1 (tracer) | 678172c | feat(audit): audit_db.py --help-io compares MAX help-box I/O with compute_io_counts; JSON report, summary, canonical baseline and baseline diff (Q9) |
| 2 | b885da7 | feat(audit): help-io scans installed packages' help dirs, skips gen~/rnbo~/jit.gen internals and content-defined boxes, compares signal roles, records signatures, examples and help appversions (Q9) |
| 3 | 917fd14 | test(audit): committed Max 9.2.0 help-box I/O baseline and a requires_max regression test that fails when mismatches increase; diff logic unit-tested on a tiny fixture (Q9) |

Task 2 needed no `tools/audit_db.py` change: Task 1's `run_help_io` already passes the packages dir and its reason through. So commit b885da7 touches only `tools/help_io.py` and `tests/test_help_io.py`.

## Execution notes

- Ran in worktree `worktree-agent-a2c80a308cde3d500`, not on `main` as the plan's rules section assumed. Base HEAD `cd5a885` was unchanged. The staged set was empty at start, `git stash list` was empty before and after, and nothing was pushed.
- **Tests before:** 2691 passed, 1 xfailed, 1 xpassed, 29 warnings (51.5 s).
- **Tests after:** 2727 passed, 1 xfailed, 1 xpassed, 29 warnings (49.7 s). That is +36, all new tests in `tests/test_help_io.py`. The warning count is unchanged.
- **Red counts before each GREEN step:**
  - Task 1: collection error (`tools.help_io` missing).
  - Task 2: 4 failed, 6 passed. The bad-file, depth-cap, determinism and missing-bundle cases already passed on the Task 1 slice.
  - Task 3: 13 failed, 23 passed. Failures were the stale/new/missing/schema diff cases, the missing committed baseline, and the live class.
- **Python 3.10:** the `ast` 3.10 syntax gate passes on all three `.py` files. Under uv Python 3.10.19 with the `requirements-dev.txt` venv:
  - `tests/test_help_io.py` + `tests/test_audit_db.py` with `MAXPAT_TEST_MAX_APP=/nonexistent/Max.app`: 75 passed, 2 skipped (`requires the Max application bundle`);
  - `TestLiveOracle` with Max: 2 passed.
  - The plan's `HOME=<scratch>` redirect was refused by the worktree sandbox, so the 3.10 run used the real HOME. This doesn't affect the result, because hermetic tests always pass an explicit packages dir.
- **`TestLiveOracle` on this Mac:** 2 passed, not skipped. With `MAXPAT_TEST_MAX_APP=/nonexistent/Max.app` it skips with the requires_max reason. With a doctored bundle version (9.1.5) it skips with the re-baseline command.
- **Tests leave the tree clean:** `git status --porcelain` was the same before and after every test run.
- **Protected trees unchanged:** `git diff --quiet cd5a885 HEAD`, and the working tree, show no change under `.claude/max-objects`, `src`, `patches`, CLAUDE.md, TECHNICAL.md, README.md or `.claude/skills`.

## OQ1

**Resolved by default with option A.** The user resumed with "continue" and didn't pick an option. The oracle compares newobj boxes plus non-newobj boxes whose maxclass resolves in the DB. Those are keyed by maxclass with no args, and the content-defined exclusion still applies (bpatcher, jsui, v8ui, `*codebox*`). Report entries carry `kinds`, and the summary splits newobj names from other names.

## Oracle figures (real run)

- **Install:** Max 9.2.0, build e9c80e453de.
- **Baseline file:** 124,258 bytes, generated against the code at b885da7 plus Task 3's diff-only changes. It reproduces byte-for-byte at HEAD 917fd14.

| source | version | files | compared (newobj) | content-defined | unresolved | internal skipped | mismatching names | mismatching boxes |
|---|---|---|---|---|---|---|---|---|
| bundle | 9.2.0 | 2114 | 77909 (24043) | 13380 | 341 | 762 | 164 | 6867 |
| package:CNMAT Externals | 1.0.5 | 58 | 4444 (1216) | 298 | 10 | 0 | 61 | 524 |
| package:FlowSwing | 2.6.1 | 7 | 664 (233) | 80 | 3 | 0 | 18 | 101 |
| package:FluidCorpusManipulation | 1.0.9 | 78 | 7312 (2889) | 1144 | 84 | 0 | 67 | 1391 |
| package:RNBO | 1.4.3 | 563 | 2605 (699) | 1337 | 0 | 662 | 13 | 110 |
| package:Rhythm and Time Toolkit | 1.0.0 | 27 | 1654 (408) | 326 | 133 | 3 | 15 | 236 |
| package:abclib | 1.1.2 | 67 | 5278 (2118) | 966 | 141 | 0 | 15 | 452 |
| package:bach | 0.8.3 | 240 | 11991 (3876) | 2247 | 85 | 0 | 73 | 1694 |
| package:cv.jit | 2.0.2 | 70 | 3041 (587) | 108 | 57 | 2 | 14 | 178 |
| package:dada | 0.3.1 | 31 | 2353 (448) | 386 | 1 | 0 | 39 | 278 |
| package:ears | 0.1.0 | 103 | 4327 (1214) | 792 | 9 | 0 | 110 | 722 |
| package:ease | 1.2.3 | 6 | 377 (143) | 54 | 4 | 2 | 6 | 24 |
| package:grainflow | 2.1.2 | 45 | 2389 (838) | 102 | 24 | 0 | 35 | 292 |
| package:ml.star | 1.3.0 | 17 | 1850 (535) | 179 | 2 | 0 | 11 | 138 |
| package:nn_tilde | v1.6.0 | 4 | 506 (172) | 18 | 0 | 0 | 11 | 77 |

**Totals across 15 sources:**
- 3,430 files, 0 bad files;
- 126,700 boxes compared, 39,419 of them newobj;
- 21,417 content-defined, 894 unresolved, 4 malformed;
- 1,431 internal patchers skipped, 0 depth-capped, 0 compare errors;
- 13,084 mismatching boxes: 6,265 newobj and 6,819 other.

**Mismatching names:**

| | literal | alias-resolved | count mismatches | signal-role mismatches | newobj | other |
|---|---|---|---|---|---|---|
| all sources | 441 | 439 | 363 | 88 | 394 | 47 |
| bundle | 164 | 162 | 151 | 15 | 143 | 21 |

In the bundle, 133 newobj names have count mismatches (131 alias-resolved). These match the planning prototype exactly. The bundle unresolved count also matches: 341 = 268 newobj + 73 non-newobj (markup, gswitch2, progress, pianoroll).

**Top 15 names by mismatching boxes (all sources), as mismatching/compared:** inlet 2805/2805, outlet 2530/2530, route 1332/1332, r 678/678, sel 431/431, live.scope~ 224/224, bach.hypercomment 203/203, mxj 203/212, select 201/201, live.gain~ 199/440, expr 194/276, coll 169/169, dict.view 127/127, mc.live.gain~ 109/109, vexpr 86/124.

**Help appversion histogram (files, all sources, 70 distinct):** 9.0.0 ×1059, 8.6.5 ×926, 9.1.0 ×151, 9.0.3 ×123, 9.0.6 ×117, 8.2.0 ×110, 7.3.4 ×76, 7.0.3 ×73, 8.6.4 ×69, 6.1.2 ×66, 7.0.0 ×55, 7.0.2 ×44, 8.3.1 ×40, 9.2.0 ×39, 8.3.0 ×38, then 55 more.

## The "~119" reconciliation

Under this plan's definition, the bundle has **164** mismatching literal names. Of those, **143** are newobj names, **133** newobj names have count mismatches, and **131** of those remain after alias resolution.

The review's ~119 does not reproduce exactly because the figure depends on the definition. This oracle:
- recurses into `p` and bpatcher subpatchers;
- keeps literal names (`sel` and `select` both count);
- stops arguments at `@` while still comparing boxes that carry attributes;
- adds UI boxes (OQ1-A, +21 names).

Planning-time variants gave 98 (core `help/` only), 111 (boxes with `@attrs` excluded) and 131-143 (canonical vs literal, count only vs any). Adding the packages raises the all-sources figure to 441. No test asserts any of these figures.

## Spot-checked evidence (`names.bundle` in the committed baseline)

- `sel`: `count args=1 max=2,2 db=1,2` in 166 of 328 boxes.
- `r`: `count args=1 max=0,1 db=1,1` in 473 of 473.
- `unpack`: `count args=0 max=1,2 db=1,0` in 59 of 419.
- `pack`: `count args=0 max=2,1 db=0,1` in 27 of 449.
- `route`: 432 of 432 boxes mismatch on count. The biggest signatures are `args=1 max=2,2 db=1,2` (292) and `args=2 max=3,3 db=1,3` (65).
- `coll`: 113 of 113 mismatch on count, with saved (1,4) vs DB (2,4).
- `sfrecord~`: `type max=signal db=control` ×3.
- `pitchshift~`: `type max=signal/signal/control db=control/control/control` ×1.
- `spectroscope~` (OQ1-A): `count args=0 max=2,1 db=2,0` in 57 of 57.

## Hand-offs

**Q10:**
- After each fix, regenerate with `python3 tools/audit_db.py --help-io --write-baseline tests/fixtures/help_io_baseline.json` so the baseline shrinks. Commit the shrunken file; `git diff` shows each improvement.
- When the quote-aware tokenizer lands, replace `help_io.box_args` with it.
- The baseline is keyed by literal names, so `sel`/`select`, `r`/`receive` and `t`/`trigger` are separate entries.
- Non-newobj boxes are compared with no args, so attribute-driven UI I/O shows as several signatures. For example, `live.gain~` saved (24,27), (6,9) and (64,67) come from `@channels`.

**Q11:** take override values from the `--json` signatures and examples.
- UI boxes (OQ1-A), MAX saved vs DB:
  - spectroscope~ (2,1) vs (2,0), 57/57;
  - live.scope~ (2,1) vs (2,0), 111/111;
  - gridmeter~ (1,1) vs (1,0), 6/6;
  - playlist~ (1,5) vs (1,3), 25/25;
  - live.adsrui (10,10) vs (1,1), 23/23;
  - dict.view (1,0) vs (1,1), 70/70;
  - inlet (0,1) vs (1,1), 1845/1845;
  - outlet (1,0) vs (2,0), 1629/1629.
- Smaller UI and object gaps: textedit (1,3) vs (1,4); preset (1,4) vs (1,5); gain~ (2,2) vs (1,2); live.meter~ (1,1) vs (1,2); plot~ inlets vary.
- Signal roles: mc.playlist~ outlet 2, jweb~ outlet 2, and the 15 bundle type-mismatch names (bp.arc.accum-2, bp.arc.knob, gen, jweb~, mc.adsr~, mc.live.gain~, mc.playlist~, mc.selector~, mc.stash~, mcs.poly~, mcs.tapout~, pitchshift~, sfrecord~, stash~, stretch~).
- Some old help files save `comment`, `live.comment` and `mira.frame` as (0,0) where the DB has (1,0). That is version-dependent, not an override error.

**Q38:** signature `appversions` give the per-version deltas. Each signature lists the help-file appversions it was seen in.

**Q33 (content-defined gaps):**
- pfft~ is excluded only through `validation._CONTAINER_NAMES`; it is not in `patcher.CONTENT_DEFINED_NAMES`.
- `mxj` is compared and mismatches in 201 of 210 bundle boxes. Its outlets vary with the loaded class (`max=1,10`, `1,13`, `1,2` vs DB 1,1), so it is content-defined in practice. `mxj~` shows the same pattern.
- `mcs.poly~` is compared (2 boxes): `count args=2 max=2,4 db=1,1`, plus one type mismatch.
- Neither set was edited.
- `compare_errors`: 0.

## Doc impact (not edited, rule 8)

- **CLAUDE.md "After a Max update, re-sync the DB" (line ~59):** add `python3 tools/audit_db.py --help-io --write-baseline tests/fixtures/help_io_baseline.json`. After a Max update, `TestLiveOracle` skips until this is re-run.
- **TECHNICAL.md:** the tools and test-suite notes should mention `tools/help_io.py`, `--help-io` and `tests/test_help_io.py`.
- **`.claude/skills/references/shared-capabilities.md`:** its audit_db mention could note the help-io mode.

## Residuals

- The live test reads this Mac's `~/Documents/Max 9/Packages`. On another machine those packages appear as `new_sources` or `missing_sources`, which is informational and never a regression. Only `bundle` and same-version packages are compared.
- A Max update makes the live test skip until the baseline is regenerated. This is intentional (S9).
- The user RNBO package is 1.4.3 and the bundled one 1.4.5. They are separate sources (`package:RNBO`, `bundle`), so both are tracked.

## Deviations from Plan

**1. [Rule 1 - Bug] Class-scoped fixture defined as an instance method**
- **Found during:** the Task 3 Python 3.10 run, where pytest raised `PytestRemovedIn10Warning`.
- **Fix:** the `live` fixture became module-scoped and module-level. It still runs once.
- **Files:** tests/test_help_io.py. **Commit:** 917fd14.

**2. [Rule 2 - Clarity] Added `compared_newobj_boxes`, `mismatching_newobj_boxes` and `mismatching_other_boxes`**
- **Why:** with OQ1-A the `compared` total mixes UI and comment boxes (77,909 in the bundle), so the planning-range check (~24k newobj compared) needed a newobj-only figure. The real figure is 24,043.
- **Also added:** `mismatching_names_canonical` per source.
- The S7 field set is a superset of the plan's; nothing was removed.

**3. [Environment] Worktree instead of main; the HOME redirect was refused**
- See Execution notes. No effect on the results.

## Known Stubs

None.

## Threat Flags

None. No new network, auth or schema surface. The only new writes are `--write-baseline` (screened by `guard_output_path`) and `--json`. Help files and `package-info.json` are only parsed with `json.loads`.

## Confirm in MAX (rule 9)

No patch file changed, so nothing needs confirming in MAX or Live.

## Self-Check: PASSED

- FOUND: tools/help_io.py, tools/audit_db.py, tests/test_help_io.py, tests/fixtures/help_io_mini_baseline.json, tests/fixtures/help_io_baseline.json
- FOUND commits: 678172c, b885da7, 917fd14 (3 `(Q9)` commits since cd5a885)
