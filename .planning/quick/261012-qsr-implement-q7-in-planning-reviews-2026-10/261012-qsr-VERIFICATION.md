---
phase: quick-261012-qsr
verified: 2026-10-12T00:00:00Z
status: passed
score: 8/8 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification: false
---

# Quick 261012-qsr (Q7 automatic save gate) Verification Report

**Goal:** Implement Q7 of `.planning/reviews/2026-10-11-fix-plan.md`. `save_patch_roundtrip` and `write_gendsp` run `validate_patch` (on a deepcopy) and `review_patch` with one cached DB. They refuse new blockers against the original, warn on removed cords, block subpatcher port x-rank changes, refuse any blocker in a new file, and honor `force=True`. The docs match reality.
**Commits:** ac650b2, 0c70800, 4dd8424 (base 676674a)
**Status:** passed
**Re-verification:** No, initial verification.

## Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Both save functions run validate_patch (deepcopy) + review_patch with one cached DB, after the stale check and before mkdir/write/commit. A refused save leaves file, HEAD, staged set and caller dict unchanged. | VERIFIED | `hooks.py`: `_run_save_gate(patch_dict, path, original_text, force=force)` is called after the stale check and before indent detection and write in `save_patch_roundtrip`. In `write_gendsp` it runs before `path.parent.mkdir`. `_blocking_findings` calls `validate_patch(copy.deepcopy(...), db=_gate_db())` and `review_patch(copy.deepcopy(...), db=_gate_db())`. `_gate_db` is `lru_cache(maxsize=1)`. `review_patch` gained keyword-only `db`, threaded into `_has_package_boxes` and `review_packages`; `review_packages` already accepted `db`. Tests assert file, HEAD, staged and dict unchanged on refusal, and `test_clean_save_constructs_no_database` passes. |
| 2 | New file: any blocking validation error (is_new=True semantics, proposed removals count) or critic blocker raises PatchValidationError. | VERIFIED | `_blocking_findings` counts every error except legacy `auto_fixed` without a proposal, plus critic blockers. `baseline_dict is None` makes every finding new. Tests `test_new_file_with_critic_blocker_refused` and `test_new_file_with_proposed_removal_refused` pass. |
| 3 | Existing file: only blockers absent from the baseline raise. Baseline is original_text, else HEAD, else the on-disk file (OQ1-A). Multiset match on a key of origin, rule template, box ids and proposed_removal; finding text is not compared. | VERIFIED | `_finding_key` and the `Counter`-based multiset in `_gate_report`; the baseline order is in `_run_save_gate`. Tests pass for pre-existing blockers saving against original_text, HEAD and disk (`test_oq1_non_git_file_on_disk_is_baseline`), a new reconverging fan-out refused, and a second instance of an existing blocker refused. |
| 4 | Unchanged round-trip of every committed generated `.maxpat`/`.gendsp` (67 files) reports zero new blockers, removed cords and port changes. | VERIFIED | `TestRoundTripNoFalseBlocks` has 67 cases and all pass. My independent check ran `_gate_report` on 55 committed `.maxpat` files against themselves: no new blockers, cords or port changes. One of them carries pre-existing blockers and is correctly exempt. |
| 5 | Cords in HEAD (and original_text) but absent from the new dict, walked recursively with path-qualified keys, give exactly one SaveGateWarning. A save removing no cord emits no gate warning. | VERIFIED | `_cord_set` uses `_iter_patchers` with path-qualified keys. One `warnings.warn(..., SaveGateWarning)` is emitted and the removal is the intersection across references. `TestCordRemoval` covers one warning, a deleted endpoint, a nested cord, an exempt earlier removal and a clean edit. `tests/test_save_safety.py` is unedited and passes, including its `simplefilter("error")` saves. |
| 6 | A changed x-rank of an inlet/outlet present in both versions (top level or embedded subpatcher) raises PatchValidationError, compared with HEAD and with original_text when given. A port appended rightmost does not. | VERIFIED | `_port_ranks` ranks by (patching_rect x, array index) per path, and `_gate_report` flags ports whose rank differs from every reference. `TestPortOrder` covers an inner swap (refused), force, an abstraction outlet swap, a mid-insert (refused), a rightmost append (saves) and an exempt earlier change. |
| 7 | `force=True` bypasses with a SaveGateWarning listing what was bypassed. PatchValidationError carries path, findings and port_changes, and still constructs from a bare message. | VERIFIED | The `force` branch warns `force=True: saving despite ...`. `PatchValidationError.__init__(message, *, path=None, findings=(), port_changes=())`. `write_gendsp` gained keyword-only `force`. `SaveGateWarning` is a `UserWarning` subclass exported from `src/maxpat/__init__.py`. Tests: `test_force_bypasses_with_warning`, `test_patch_validation_error_bare_message`, `test_save_gate_warning_exported`, and gendsp refuse/force. |
| 8 | Docs describe the gate as built. Suite is green, nothing under `patches/` changed, Python 3.10 syntax gate passes. | VERIFIED | The `hooks.py` module docstring, the README Validation Pipeline paragraph and the TECHNICAL.md "Write Hooks" section all describe the gate accurately. The `write_js` report-only claim is also correct. `git diff 676674a HEAD --name-only` shows 0 paths under `patches/`. `ast.parse(feature_version=(3,10))` passes on all 5 changed .py files. |

**Score:** 8/8 truths verified.

## Spec Checklist (fix-plan Q7)

| Spec item | Status |
|-----------|--------|
| validate_patch (deepcopy) + review_patch, one cached DB, in save_patch_roundtrip and write_gendsp | Met |
| Existing files compared against original_text, else HEAD; only new blockers raise; matched by rule + box ids | Met (plus the OQ1-A disk fallback) |
| `force=True` bypasses with a warning | Met |
| Warn on removed cords vs HEAD | Met |
| Block on subpatcher inlet/outlet x-rank change vs HEAD | Met |
| New files refuse any blocker | Met |
| Tests: reconverging fan-out raises, pre-existing blockers save, cord-removal warning, x-rank swap blocks, force works | All present in `tests/test_save_gate.py` (102 tests, 826 lines) |
| Docs: `hooks.py` docstring, README, TECHNICAL Write Hooks | Matched |

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full suite | `python3 -m pytest -q` | 2661 passed, 1 xfailed, 1 xpassed, 29 warnings (baseline 2559 passed, same xfail/xpass, same warning count) | PASS |
| MAX repo untouched by the tests | Compared HEAD, staged set, `git status -- patches/` and `git stash list` before and after | HEAD and staged set unchanged; only the pre-existing `patches/.active-project.json` is modified; no stash | PASS |
| No false blocks on real patches | Independent `_gate_report` sweep over 55 committed `.maxpat` files | 0 new blockers, cords or port changes | PASS |

## Anti-Patterns

No stubs, TBD/FIXME markers or placeholder returns were found in the changed code. No `git stash` use. No committed patch files were edited.

## Noted Limitations (disclosed in SUMMARY, not gaps)

- Validation and the critics only look at the top level, so findings inside subpatchers are not gated until Q19/Q20. The cord and port checks already recurse.
- The gate raises on a malformed dict if a validator or critic crashes; no such case exists among the committed patches.
- The DB cache is per process.
- CLAUDE.md Rule #7 and several skill references are not updated to mention the gate. The plan did not task this and SUMMARY lists them under doc impact (rule 8).
- A regenerated patch with renumbered box ids can produce cord-removal warnings. These are warnings only and never block.

## Human Verification

None required. No patch file changed, so nothing needs confirming in MAX or Live.

## Gaps

None.

---

_Verified: 2026-10-12_
_Verifier: Claude (gsd-verifier)_
