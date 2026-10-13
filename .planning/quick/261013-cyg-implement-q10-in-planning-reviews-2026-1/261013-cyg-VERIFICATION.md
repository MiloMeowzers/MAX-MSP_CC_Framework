---
phase: quick-261013-cyg
verified: 2026-10-13T00:00:00Z
status: passed
score: 7/7 must-haves verified
behavior_unverified: 0
overrides_applied: 0
human_verification_advisory:
  - test: "In MAX, create bare `route`, bare `routepass`, bare `trigger`/`t`; check inlet/outlet counts"
    expected: "route (2,2), routepass (2,2), t (1,2)"
    why_human: "These counts come from refpage text, not MAX-saved boxes. This is advisory; the executor already flagged it, and it does not block."
covered_files_note: "gsd_run is unavailable in this environment, so covered_digest was not generated."
---

# Quick Task 261013-cyg (Q10): argument-dependent I/O counts. Verification Report

**Goal:** Implement Q10 of `.planning/reviews/2026-10-11-fix-plan.md` and correct argument-dependent I/O counts (C1, S6).
**Verified:** 2026-10-13
**Status:** passed
**Re-verification:** No, initial verification.

## Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | The tokenizer respects quotes and stops at `@attributes`. Pre-split and quote-joined args give the same answer. | VERIFIED | `t` with `'"LCD Text / Icon (Inactive)"'` and with the pre-split tokens both give (1,1). `combine sound 74 @triggers 1` gives (2,2). `gate~ 3 @ramptime 100` gives (2,3). |
| 2 | `r`/`receive` with a name is (0,1). Bare `receive` is (1,1). | VERIFIED | `r todrive` (0,1), `receive bem` (0,1), `receive` (1,1). All confirmed in my own script. |
| 3 | select/sel/route/routepass with N args give (N+1,N+1). Bare is (2,2). | VERIFIED | `sel` (2,2), `sel 0` (2,2), `sel 0 1` (3,3), `select 1..7` (8,8), `route point` (2,2), `route time transport` (3,3), three quoted args (4,4), `routepass 0 1` (3,3), bare route/routepass (2,2). |
| 4 | expr/vexpr/if/sprintf/pipe/notein/ctlin follow the spec. | VERIFIED | All evidence rows pass: expr `$i3*$i1+$i2` (3,1), `if … out2` (1,2) and (3,2), sprintf with escaped commas (6,1), `pipe` with 13 args (13,12), `notein` (1,3), (1,2) and (1,3), and the full `ctlin` set (1,3), (1,2), (1,1), (1,2), (1,2). |
| 5 | Bare pack/pak/unpack/trigger/t/combine, switch, b/bangbang, gate~, bucket, buddy, unjoin, groove~, tapout~, record~, jit.pack, jit.unpack and mc.route match the evidence. matrix~, mc.matrix~ and play~ keep Q2's counts. | VERIFIED | My script checked 77 rows (every Task 1-3 evidence row plus the aliases) with 0 mismatches. `matrix~ 2 3` gives (2,4), `mc.matrix~ 2 3` gives (2,5), `play~ buf 2` gives (1,3). `groove~ a 4` gives 5 signal outlets and `unjoin 4` gives 5 outlets, so trailing outlets work. |
| 6 | Non-formula rules are resolver callables. SUPPORTED_IO_FORMULAS is unchanged. No object has both a resolver and a rule. The in-memory `variable_io` is True. The domain JSON is untouched. | VERIFIED | `IO_RESOLVERS` has 11 keys (ctlin, expr, if, notein, pipe, receive, route, routepass, select, sprintf, vexpr). `SUPPORTED_IO_FORMULAS` has exactly the 10 base strings. The intersection with `_variable_io_rules` is empty. `lookup("receive"/"gate~"/"mc.route"/"sel"/"t")["variable_io"]` is True. `git diff 5587b1c HEAD` over the domain `objects.json` files, aliases and patches is empty. |
| 7 | The live oracle shows 0 count mismatches on every Q10 target. The baseline's only regression is the unmasked mc.route type mismatch. Patch triage is identical. The suite is green. Python 3.10 syntax is OK. | VERIFIED | See below. |

**Score:** 7/7 truths verified.

### Truth 7 evidence

- **Full pytest on current main:** 2843 passed, 1 xfailed, 1 xpassed, 29 warnings. `git status --porcelain` for tracked files was unchanged across the run.
- **TestOracleTargets:** ran without skip (116 passed in `tests/test_io_resolvers.py`, no skips reported). `Q10_TARGETS` has 35 names, including matrix~, mc.matrix~ and play~.
- **Baseline diff (`help_io.diff_baselines`, `5587b1c` against HEAD):** 120 improvements. The only regression is `bundle/mc.route type_mismatches 0 -> 11`. mc.route is a Q10 target with count mismatches now 0, so this is the allowed unmasking. Its cause is the `signal_role: audio` override on int outlets, which belongs to Q11 (C9).
- **Live `audit_db.py --help-io` re-run:** consistent with the SUMMARY's figures. Per-source rows I spot-checked match, for example cv.jit 4 names/113 boxes and dada 33/257.
- **Independent triage:** `validate_patch` (on a deepcopy) and `review_patch` over 57 `patches/**/*.maxpat|*.maxhelp` files gave 1417 findings both with a `git archive` of base `5587b1c` and with HEAD. The output is byte-identical (`cmp`). No file under `patches/` changed.
- **Python 3.10 syntax:** `ast.parse(feature_version=(3,10))` is OK on all six changed `.py` files.

## Required Artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| `src/maxpat/io_resolvers.py` | VERIFIED | 299 lines (min 120). Contains `IO_RESOLVERS`, `split_box_text`, `box_args` and `normalize_args`. |
| `src/maxpat/db_lookup.py` | VERIFIED | Imports `IO_RESOLVERS` and `normalize_args`. The resolver/rule conflict check and the derived `variable_io` flag work (see Truth 6). |
| `.claude/max-objects/overrides.json` | VERIFIED | Format round-trips with `json.dumps(indent=2, ensure_ascii=True)`. Every top-level key except `variable_io_rules` is identical to base. Exactly 22 rule keys changed: 5 removed (expr, route, routepass, select, vexpr), 7 modified (pack, pak, unpack, trigger, combine, switch, unjoin) and 10 added (gate~, bucket, buddy, bangbang, groove~, tapout~, record~, jit.pack, jit.unpack, mc.route). Each has an `_audit` with a source citation. trigger and combine are MEDIUM, as specified. |
| `tests/test_io_resolvers.py` | VERIFIED | 408 lines (min 200). Contains `Q10_TARGETS`. |
| `tests/fixtures/help_io_baseline.json` | VERIFIED | Regenerated. 120 improvements, with the single allowed regression noted above. |

## Key Links

| From | To | Via | Status |
|------|----|-----|--------|
| `db_lookup.compute_io_counts` | `io_resolvers` | `normalize_args`, then `IO_RESOLVERS` | WIRED. Behavior confirmed by the 77-row count check. |
| `tools/help_io.py` | `io_resolvers` | `box_args` delegates | WIRED. The diff shows `help_io.py` changed (25 lines), and the oracle uses the quote-aware tokenizer. |
| `overrides.json` | `db_lookup` | `variable_io_rules`, `trailing_outlets` | WIRED. unjoin, groove~ and jit.unpack show the correct trailing-outlet layouts. |
| `tests/test_io_resolvers.py` | `tools/audit_db.py` | `run_help_io` | WIRED. TestOracleTargets ran and passed. |

## Scope and Protected Trees

`git diff --stat 5587b1c HEAD` outside `.planning` touches exactly 8 files: `overrides.json`, `db_lookup.py`, `io_resolvers.py`, `help_io_baseline.json`, `test_db_lookup.py`, `test_io_resolvers.py`, `test_patcher.py` and `help_io.py`. This is the plan's `files_modified` set. `patches/`, CLAUDE.md, TECHNICAL.md, README.md, `.claude/skills`, aliases and the domain `objects.json` files are untouched. `git stash list` is empty. The three `(Q10)` commits are on local main only (nothing pushed).

## Anti-Patterns

None found in the changed files that block the goal. I made no write to the repo other than this VERIFICATION.md. The scratch scripts and the `git archive` export are in the scratchpad.

## Residual and Non-Blocking Items

- **Pre-existing follow-ups (SUMMARY, rule 7):** the arg-dependent bundle names outside Q10 scope (mxj, dict.pack, print, and others), expr~ (Q12), the record~ inlet layout (S6/Q33) and the mc.route signal-role override (Q11/C9). These are correctly out of scope.
- **Advisory, no gap:** bare route/routepass/trigger counts are refpage-derived. The SUMMARY flags a short MAX check.
- **Doc impact:** TECHNICAL.md and CLAUDE.md need follow-up updates (route/select now gain inlets; quote-aware, `@`-truncated args). They were deliberately not edited (rule 8).

## Gaps Summary

No gaps. Every must-have was checked against the code and an independent run, not just the SUMMARY. The goal is achieved: argument-dependent I/O counts now match MAX-saved boxes for every Q10 object, with tests, a shrunken baseline and identical committed-patch behavior.

---

_Verified: 2026-10-13_
_Verifier: Claude (gsd-verifier)_
