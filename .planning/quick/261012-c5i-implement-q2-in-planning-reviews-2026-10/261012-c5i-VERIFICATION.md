---
phase: quick-261012-c5i
verified: 2026-10-12T16:36:14Z
status: passed
score: 9/9 must-haves verified
covered_files:
  - .claude/max-objects/overrides.json
  - src/maxpat/audit/overrides.py
  - src/maxpat/db_lookup.py
  - src/maxpat/validation.py
  - tests/test_db_lookup.py
  - tests/test_db_signal_ports.py
  - .planning/quick/261012-c5i-implement-q2-in-planning-reviews-2026-10/261012-c5i-PLAN.md
  - .planning/quick/261012-c5i-implement-q2-in-planning-reviews-2026-10/261012-c5i-SUMMARY.md
covered_digest: "v2:sha256:17a41d0a086f2bdc5a08b57257434781d788d2d3f031abf492281690d9ba15ef"
behavior_unverified: 0
overrides_applied: 0
---

# Quick 261012-c5i (Q2): Verification Report

**Goal:** Implement Q2 of `.planning/reviews/2026-10-11-fix-plan.md` by fixing the DB entries that strip or flag valid cords (A1 data part).
**Status:** passed. **Re-verification:** No.

## Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | No override flips a base signal inlet to control, except the reviewed allowlist. The guard also fails on stale or reasonless entries. | VERIFIED | I recomputed the flips independently. The pre-task `overrides.json` (ee723d2) has 64 flips and HEAD has 4: adc~ 0 and peek~ 0/1/2, the allowlist exactly. The guard (`TestOverrideSignalGuard`) rebuilds base entries in `DOMAIN_LOAD_ORDER` and has a stale/reason hygiene test. Against the old overrides it would fail. |
| 2 | `_build_inlet_array(count, obj_name)` copies signal/type by index from the DB. Ports beyond the DB array keep the control default. | VERIFIED | Read `src/maxpat/audit/overrides.py`. Both call sites pass `obj_name`. Alias-canonical, type-guarded. `TestBuildInletArrayNeverDowngrades` has 4 tests, all pass. |
| 3 | Every A1 repro keeps its cord with zero connection findings. | VERIFIED | `TestA1Repros` has 14 parametrized cases: tapin~->tapout~, filtergraph~->biquad~, cycle~ to poly~/pfft~/rnbo~/p/sfrecord~/vst~/pitchshift~/fffb~/mc.snapshot~, in->peek~, matrix~->dac~, play~->dac~. Each asserts no connection findings, the input unmutated and the cord present. All pass. |
| 4 | biquad~ inlet 0 is signal/list. A list into it gives no finding, and a list into `*~` still warns. | VERIFIED | The DB lookup gives `{'type': 'signal/list', 'signal': True}`. The `_classify_role_mismatch` token rule is in validation.py. The `*~` anchor test passes. |
| 5 | `in` outlet role is None. peek~ inlets are control, and a signal cord into peek~ is proposed for removal. | VERIFIED | `get_signal_role('in', 0)` is None. peek~ inlet signal flags are `[False, False, False]`. The anchor test `test_anchor_signal_into_peek_proposed` passes. |
| 6 | matrix~ N M and play~ buf N outlet counts and roles resolve through `trailing_outlets`. A trailing dump or bang into `dac~` still warns. | VERIFIED | `compute_io_counts` gives matrix~ 2 4 -> (2,5) and play~ buf 2 -> (1,3). `second_arg+1` is in `SUPPORTED_IO_FORMULAS` and `_apply_io_formula`. The anchor tests for the trailing outlet into `dac~` pass: one warning, no removal. |
| 7 | mc.matrix~ N M has M audio outlets plus 2 control outlets. | VERIFIED | `compute_io_counts('mc.matrix~', ['2','4'])` gives (2,6). `second_arg+2` is implemented. `test_compute_io_counts_mc_matrix` was rewritten and passes. |
| 8 | mixer-strip, terrain-voice and scala-synth-voice propose 0 removals. scala-synth-voice has 0 connection findings. | VERIFIED | My own script validated deepcopies of all three: proposed `[]`, connection findings 0, input unchanged. The committed tests cover the same. |
| 9 | The failing set equals the baseline. No file under `patches/` changed, and the changed .py files pass the 3.10 syntax gate. | VERIFIED | Full `pytest -q`: 3 failed, 2390 passed, 2 xfailed, 1 xpassed. The 3 failures are the allowed `test_review_patch_no_blockers` cases (minitaur, physics-composition, timestretch). The baseline file shows the same 3 failures with 2345 passed. `git diff --name-only ee723d2 HEAD -- patches` is empty. `ast.parse(feature_version=(3,10))` is ok on all 5 changed .py files. The stash list is empty. |

**Score:** 9/9. `behavior_unverified`: 0.

## Required Artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| `tests/test_db_signal_ports.py` | VERIFIED | Contains `_SIGNAL_DOWNGRADE_ALLOWLIST`. It holds the guard, the generator tests, the A1 repros, the committed-patch tests and the refpage-fact tests. It is substantive and not a stub, and 32 tests pass. |
| `.claude/max-objects/overrides.json` | VERIFIED | Flips 64 -> 4. Contains `second_arg+1`. |
| `src/maxpat/audit/overrides.py` | VERIFIED | `_build_inlet_array` is changed as specified. |
| `src/maxpat/db_lookup.py` | VERIFIED | The formulas are added in both places. |
| `src/maxpat/validation.py` | VERIFIED | `_classify_role_mismatch` has the role-token acceptance. |
| `tests/test_db_lookup.py` | VERIFIED | 13 new tests for trailing outlets. |

## Key Links

All four key links are wired and exercised by passing tests: the guard compares overrides against the pre-override base, the generator reads `self._db._objects`, the `trailing_outlets` rules flow through to the role dispatch, and the dst-inlet type token is read in `_classify_role_mismatch`.

## Requirements

A1 (data part): SATISFIED. C9 (cause only): SATISFIED. The C9 outlet roles are explicitly out of scope, and the user chose OQ1-A.

## Anti-Patterns

No debt markers or stubs were found in the changed code. I did not run the TBD/FIXME/XXX grep on overrides.json because it is a data file.

## Accepted Deferrals (not gaps)

These are per the user-approved OQ answers and are documented in SUMMARY.md.
- 40 outlet signal->control flips on 38 objects are not guarded (OQ1-A, owned by Q11).
- 11 audit-written control inlets sit beyond the base arrays (OQ3-A, owned by Q10). Two still produce proposed removals: `cycle~ -> sfrecord~ 2` inlet 1 and an MC signal into `mc.selector~ 2` inlet 2. The A1 repros in the must-haves only cover sfrecord~ inlet 0.
- Doc impact is listed but not edited: `TECHNICAL.md:159` and `CLAUDE.md:197`.

## Human Verification

None required. No patch files changed and all counts come from MAX-saved help boxes. The optional check in SUMMARY.md is to open a generated `mc.matrix~ 3 2` (expect 4 outlets) and `play~ buf 2` (expect 3 outlets).

---
_Verified: 2026-10-12_
_Verifier: Claude (gsd-verifier)_
