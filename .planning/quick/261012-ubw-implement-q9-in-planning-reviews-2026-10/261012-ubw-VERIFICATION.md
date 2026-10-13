---
phase: quick-261012-ubw
verified: 2026-10-13T15:45:00Z
status: passed
score: 7/7 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Quick 261012-ubw (Q9: help-box I/O oracle) Verification Report

**Goal:** Implement Q9 of `.planning/reviews/2026-10-11-fix-plan.md`: `python3 tools/audit_db.py --help-io`, a committed baseline, and a requires_max regression test. No DB fixes.
**Verified:** 2026-10-13, on `main` at a8bce3a (merge of 678172c, b885da7 and 917fd14; base cd5a885).
**Re-verification:** No, initial verification.

## Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `--help-io` scans the bundle and package help dirs, skips gen~/rnbo~/jit.gen internals, prints a summary, `--json` writes a report, and the default audit is unchanged | VERIFIED | I ran `python3 tools/audit_db.py --help-io --json <scratch>`. It scanned 2114 bundle files plus 14 packages (1316 files), skipped 1431 internal patchers, and printed the install, sources, boxes, mismatch and help-version lines. In `tools/help_io.py` the walk checks `GEN_RNBO_CONTAINERS` and `SKIPPED_NAMESPACES` (lines 275-276). The default `audit_db.py` run still prints its normal report. The only deleted lines in the `audit_db.py` diff are the docstring text and the `parse_args` line. |
| 2 | Box I/O is compared with `compute_io_counts` and `get_outlet_types`, content-defined/unresolved/malformed boxes are counted but not compared, and OQ1-A adds non-newobj boxes | VERIFIED | The summary shows 21417 content-defined, 894 unresolved and 4 malformed boxes, kept apart from the 126700 compared. `CONTENT_DEFINED` is imported from `patcher.CONTENT_DEFINED_NAMES` and `validation._CONTAINER_NAMES`. The baseline has `spectroscope~` as `count args=0 max=2,1 db=2,0`, 57/57, a non-newobj box. |
| 3 | `--write-baseline` writes a canonical, deterministic file, goes through `guard_output_path`, exits 1 with no file when the bundle is unavailable, and exits 2 without `--help-io` | VERIFIED | Two runs gave identical bytes (`cmp`), and both match the committed file. `json.dumps(sort_keys=True, indent=1) + "\n"` equals the file text. The file has no `generated_at` and no `/Users` path. Target `patches/x.json` gave exit 2 with a refusal. With `--max-app /nonexistent/Max.app` the exit was 1 and no file was created. `--write-baseline` without `--help-io` gave exit 2 and no file. |
| 4 | `diff_baselines` flags a regression only when a name has more count or type mismatches live, for sources at the same version, with stale/new/missing sources excluded, a schema other than 1 raising ValueError, and unit tests on the mini fixture | VERIFIED | The logic at `tools/help_io.py:578-636` matches. A version mismatch goes to `stale_sources` and is not compared. `new_sources` and `missing_sources` are reported only. Schema is checked on both sides. `TestDiff` has 12 cases, including stale, new, missing and schema (parametrized on both sides), plus `test_mini_fixture_is_canonical`. |
| 5 | The committed baseline exists, is canonical and under 400 KB, and records the review's evidence | VERIFIED | `tests/fixtures/help_io_baseline.json` is 124,258 bytes with schema 1 and max_version 9.2.0. It records `sel` (328 boxes, all count mismatches), `r` (473/473, `max=0,1 db=1,1`), `unpack` (59), `pack` (27), `route` (432/432), `coll` (113/113, `max=1,4 db=2,4`), `sfrecord~` (3 type mismatches), `pitchshift~` (1 type mismatch) and `spectroscope~` (57). |
| 6 | The requires_max live test passes here, skips under `MAXPAT_TEST_MAX_APP=/nonexistent/Max.app`, skips on a Max version change, and detects a decremented count as one regression | VERIFIED | With Max present, `tests/test_help_io.py` gave 36 passed. With `MAXPAT_TEST_MAX_APP=/nonexistent/Max.app` it gave 34 passed and 2 skipped ("requires the Max application bundle"). `TestLiveOracle.test_a_regression_is_detected_on_live_data` exists. The stale-version skip is implemented in the live fixture. I did not re-run it with a doctored version. |
| 7 | Nothing under `.claude/max-objects`, `src`, `patches`, CLAUDE.md, TECHNICAL.md, README.md or `.claude/skills` changed, and the full suite stays green | VERIFIED | `git diff --stat cd5a885 HEAD -- .claude src patches CLAUDE.md TECHNICAL.md README.md` is empty. The full diff touches only the 5 planned files. `python3 -m pytest -q` gave **2727 passed, 1 xfailed, 1 xpassed, 29 warnings**, which is 2691 plus the 36 new tests. The `ast.parse(..., feature_version=(3, 10))` gate passes on all 3 `.py` files. I did not re-run the uv Python 3.10 pytest run. |

**Score:** 7/7 truths verified, 0 behavior-unverified.

## Required Artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| `tools/help_io.py` | VERIFIED | 710 lines, defines `diff_baselines` and the rest of the planned public API. It does not import `tools.audit_db`. |
| `tools/audit_db.py` | VERIFIED | Gains `--help-io`, `--packages-dir` and `--write-baseline`. |
| `tests/test_help_io.py` | VERIFIED | 692 lines, 36 tests, with `requires_max` on the live class. |
| `tests/fixtures/help_io_mini_baseline.json` | VERIFIED | 59 lines, canonical, used by the diff tests. |
| `tests/fixtures/help_io_baseline.json` | VERIFIED | Matches a fresh regeneration byte for byte. |

## Key Links

| From | To | Status |
|------|----|--------|
| `audit_db.py` | `help_io.py` | WIRED. `--help-io` runs the scan and writes the baseline, as the CLI runs above show. |
| `help_io.py` | `db_lookup` | WIRED. Mismatches are computed from the DB per box (e.g. `sel` db=1,2). |
| `help_io.py` | `patcher` / `validation` | WIRED. `CONTENT_DEFINED` is imported, not copied. |
| `test_help_io.py` | committed baseline | WIRED. `TestLiveOracle` diffs a live scan against it. |

## Behavioral Spot-Checks

| Behavior | Result | Status |
|----------|--------|--------|
| `--help-io` end to end | exit 0, summary printed | PASS |
| Baseline determinism and equality with the committed file | identical bytes | PASS |
| Guard, unavailable-bundle and no-`--help-io` exit codes | 2 / 1 / 2, nothing written | PASS |
| `git status --porcelain` after the test and CLI runs | only pre-existing untracked `.planning/` files | PASS |

## Requirements Coverage

| Requirement | Status |
|-------------|--------|
| Q9 | SATISFIED |
| S6 (help-box oracle test half) | SATISFIED |

## Anti-Patterns

I found no TBD, FIXME or XXX markers in the new `.py` files. I saw no stubs: every function in `help_io.py` is substantive and its output is verified above.

## Notes (informational, not gaps)

- The review's "~119 mismatching names" does not reproduce. The bundle gives 164 literal names (143 newobj), and the executor explained why. No test asserts that number, and the plan said not to.
- OQ1 was resolved by default with option A, and SUMMARY.md records it.
- The doc impact (CLAUDE.md re-sync line, TECHNICAL.md, `shared-capabilities.md`) is listed in SUMMARY.md and not edited, as rule 8 requires.
- The executor ran in a worktree, not on `main` as the plan assumed. The result was merged cleanly, and the commit set and base match.
- The live test depends on this Mac's Max 9.2.0 install and its 14 packages. On another machine, extra or missing packages are reported only. A Max update makes the test skip until the baseline is regenerated, which is by design.
- `covered_files` / `covered_digest` fingerprint fields are not written: this is a quick task, not a phase directory.

## Human Verification Required

None. No patch files changed, so nothing needs confirming in MAX or Live.

## Gaps Summary

None. The phase goal is achieved in the codebase, not only in SUMMARY.md.

---

_Verified: 2026-10-13_
_Verifier: Claude (gsd-verifier)_
