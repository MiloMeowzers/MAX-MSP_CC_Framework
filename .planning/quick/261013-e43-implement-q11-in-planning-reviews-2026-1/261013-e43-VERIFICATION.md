---
phase: quick-261013-e43
verified: 2026-10-13T23:30:00Z
status: passed
score: 8/8 must-haves verified
covered_files:
  - .claude/max-objects/overrides.json
  - CLAUDE.md
  - src/maxpat/db_lookup.py
  - tests/test_override_merge.py
covered_digest: "v2:sha256:02f2669641fb5460a67ca987f6f5613636cc79ede180ebd14ea56e5425b37a94"
behavior_unverified: 0
overrides_applied: 0
---

# Quick 261013-e43 (Q11): Verification Report

**Goal:** Implement Q11 of `.planning/reviews/2026-10-11-fix-plan.md`. Override ports merge per port, override keys are canonicalized through aliases, and counts and outlet roles are corrected against MAX-saved help boxes.
**Verified:** 2026-10-13
**Status:** passed
**Re-verification:** No, initial verification.

I re-ran the checks against the merged tree on main and did not rely on SUMMARY.md.

## Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Per-port merge semantics | VERIFIED | `merge_override_ports` in `src/maxpat/db_lookup.py` (lines 84-125) does the following. The override array sets the count. Each port copies the base port and replaces only the keys it sets. A placeholder or non-string `digest`/`description` never replaces a non-empty base string. An empty `type` never replaces a control base port's type. `{"id": N}` inherits the base port. Non-port keys replace whole (`_apply_object_overrides`, line 328). Live DB: `line~` inlet 1 = `{'digest': 'Ramp Time', 'hot': True}`; `uzi` outlet 1 = "Done banging bang (carry)". The unit tests in `tests/test_override_merge.py` run in the full suite. |
| 2 | Real-DB restore anchors (384 digests / 154 objects, 192 hot / 125 objects) | VERIFIED | `restore-counts.txt` matches the plan's prototype figures. The `line~` and `uzi` examples named in the plan reproduce live. The restore anchors are asserted in the test file, and that file passes. |
| 3 | Alias-canonical keys, fail-fast, `r` removed, stale notes removed | VERIFIED | `_apply_object_overrides` canonicalizes via `self._aliases` and raises `ValueError` on a duplicate canonical key or a key with no base entry. In overrides.json, `del` and `v` are gone, and `delay` and `value` exist. `r` is gone. `is_overridden("del")` and `is_overridden("value")` are True. `compute_io_counts("r", ["foo"])` = (0,1) and bare `receive` = (1,1). The "override inactive" `_note`s were removed (checked on jit.*, uzi, array.at, mc.send~, mc.sum~, jit.time), and none remain. |
| 4 | 19 count corrections match MAX-saved boxes | VERIFIED | Live `compute_io_counts` returned coll (1,4), spectroscope~ (2,1), index~ (2,2), poke~ (3,1), vst~ (2,8), retune~ (3,5), thispoly~ (1,3), live.scope~ (2,1), playlist~ (1,5), gridmeter~ (1,1), bucket (1,1), mousestate (1,10), live.adsr~ (11,3), live.adsrui (10,10), dict.view (1,0), jit.polymovie (1,3), jit.line (1,2), mira.motion (1,1) and `mxj~ noise` (1,2). All match the plan. The remaining mismatches for these names are older-Max boxes allowed by exact signature (the `TestOracleQ11` test passes). |
| 5 | C9 outlet roles for the 16 bundle names plus retune~/playlist~; zero bundle type mismatches | VERIFIED | `get_outlet_types` is now: mc.route `['','']`, gen `['']`, sfrecord~ `['signal']`, pitchshift~ `['signal','signal','']`, mc.selector~ `['multichannelsignal']`, stash~ `['signal','signal']`, stretch~ `['','']`, retune~ `[s,s,s,s,'']`, playlist~ `[s,s,s,'','']`, jweb~ `[s,s,'']`, bp.arc.knob `['']`, bp.arc.accum-2 `['']`. Each override carries a Q11 `_audit` citing a help box. `python3 tools/audit_db.py --help-io` was run live against Max 9.2.0 and gave 386 mismatching names and 8670 boxes (bundle 107 names, 4344 boxes), identical to the SUMMARY figures and the committed baseline. `TestOracleQ11.test_bundle_has_no_type_mismatches` ran with Max installed, was not skipped, and passed. |
| 6 | Outlet downgrade guard (Q2 OQ1-A hand-off) with exactly the 40-port allowlist | VERIFIED | `_OUTLET_DOWNGRADE_ALLOWLIST` is in `tests/test_override_merge.py:547`. It is extended with the Gen operators at line 582, and `len == 40` is asserted at line 588. `TestOutletDowngradeGuard` passes in the full run. |
| 7 | CLAUDE.md lines 25 and 57; no "deep merge" wording in db_lookup.py | VERIFIED | The CLAUDE.md diff vs `45f23b4` touches only lines 25 ("Merged per port: ...") and 57 (the spectroscope~ refpage count is right; only the type is a placeholder). `grep -i "deep.merg" src/maxpat/db_lookup.py` returns no match. |
| 8 | Triage identical, no `patches/` change, suite green, Python 3.10 | VERIFIED | I recomputed `validate_patch` (on a deepcopy) plus `review_patch` over all 57 committed patches. Using a `git archive 45f23b4` base tree and the HEAD tree, both gave 1417 findings and the output files were byte-identical. `git diff 45f23b4 HEAD -- patches tools src/maxpat/io_resolvers.py src/maxpat/validation.py src/maxpat/audit TECHNICAL.md README.md .claude/skills aliases.json` is empty. The full `python3 -m pytest` run had no failures: 2921 passed plus 1 xfail and 1 xpass in the progress output (2923 characters), matching the SUMMARY. `git status --porcelain` showed no tracked changes after the run, and the stash list is empty. All five changed `.py` files pass `ast.parse(..., feature_version=(3, 10))`. |

**Score:** 8/8 truths verified.

## Required Artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| `src/maxpat/db_lookup.py` | VERIFIED | Contains `merge_override_ports`, `OVERRIDE_PLACEHOLDER_DIGESTS` and `_apply_object_overrides`, called from `_load` (line 255). |
| `.claude/max-objects/overrides.json` | VERIFIED | The file is byte-identical to `json.dumps(indent=2, ensure_ascii=True)` with no trailing newline. `version_map`, `variable_io_rules`, `_comment` and `_uncovered_empty_io` are unchanged. `poly~` is unchanged. 62 object keys changed. Count and role corrections carry Q11 `_audit` entries. |
| `tests/test_override_merge.py` | VERIFIED | New file, 669 lines (plan minimum 220). Contains `Q11_COUNT_TARGETS` and `TestOracleQ11`. |
| `tests/fixtures/help_io_baseline.json` | VERIFIED | Regenerated. A live oracle run matches it, and the baseline-comparison test passes. |
| `CLAUDE.md` | VERIFIED | Contains "Merged per port". |

## Key Links

| From | To | Status |
|------|----|--------|
| `db_lookup._load` -> `_apply_object_overrides` -> alias canonicalization -> `merge_override_ports` | `overrides.json` | WIRED (live behavior shown in the Truths 1 and 3 rows) |
| per-port `signal_role` -> `_apply_signal_role_writethrough` -> `outlet['signal']` -> `get_outlet_types` | `overrides.json` | WIRED (live `get_outlet_types` output shown in the Truth 5 row) |
| `tests/test_override_merge.py` -> `audit_db.run_help_io` | `tools/audit_db.py` | WIRED (`run_help_io` is called at line 620, and the test executed, not skipped) |

## Anti-Patterns

No TBD/FIXME/XXX markers were found in the changed source. No stubs. No edits outside the plan's eight `files_modified` paths.

## Advisory (not blocking)

These are the SUMMARY's "Confirm in MAX" items. Each rests on MAX-saved help boxes, but some are single-box or older-version evidence, or inference.

- `mxj~` (1,2) comes from one Max 7.0.0 save of `mxj~ noise`.
- `jit.polymovie` (1,3) comes from one Jitter Tools 9.1.0 box.
- `mira.motion` (1,1) comes only from Max 7.3.x saves.
- `jweb~` outlet 2 is treated as control, because the help box (9.0.0) says "" while the refpage says signal.
- `live.adsr~` inlets 0-4 accepting signals is inferred from help-patch cords.

New boxes of the corrected objects now get MAX's counts, so cords to `coll` inlet 1 or from a `dict.view` outlet are blocked. Existing patches validate identically.

## Doc impact (noted, intentionally not edited per the plan)

- TECHNICAL.md:143 and :192 still describe a deep merge.

## Gaps Summary

None. The phase goal is achieved in the codebase, and every must-have was verified against live code, the live Max oracle and the full test suite.

---

_Verified: 2026-10-13_
_Verifier: Claude (gsd-verifier)_
