---
phase: quick-261012-qsr
plan: 01
subsystem: save-path
status: complete
tags: [save-gate, validation, critics, git, Q7, A3, R1]
requires: [Q1 proposed_removal semantics, Q5 path-scoped auto-commit + stale check]
provides: [automatic save gate in save_patch_roundtrip/write_gendsp, SaveGateWarning, structured PatchValidationError, review_patch(db=)]
affects: [Q8 CI job, Q19/Q20 recursive validation, Q36 edit_patch sessions, Q39 quick-fix payloads]
tech-stack:
  added: []
  patterns: [baseline multiset diff of findings keyed by rule template + box ids, path-qualified recursive cord/port walkers, lru_cache'd ObjectDatabase]
key-files:
  created: [tests/test_save_gate.py]
  modified: [src/maxpat/hooks.py, src/maxpat/critics/__init__.py, src/maxpat/__init__.py, tests/test_hooks.py, README.md, TECHNICAL.md]
decisions:
  - "Save gate refuses only blockers absent from the baseline (original_text, else HEAD, else on-disk file per OQ1-A); new files refuse every blocker"
  - "Findings matched as a multiset of (origin, rule template, sorted unique box ids, proposed_removal) - never finding text"
  - "Port x-rank = rank of ports present in both versions; mid-insert/mid-delete/swap block, rightmost append does not"
  - "Cord/port changes already present in original_text are exempt (not attributed to this save)"
requirements: [A3, R1]
metrics:
  duration: ~10 min
  completed: 2026-10-12
actuals:
  tokens: 14900
  tasks: 3
  commits: 3
plan_head_before: 676674a2e067883c56e2abc18b9975d3ea03e065
plan_head_after: 4dd8424b199e0b213101c5f874595691861af0d3
---

# Quick 261012-qsr: Q7 Automatic Save Gate Summary

`save_patch_roundtrip` and `write_gendsp` now run `validate_patch` (on a deepcopy) and `review_patch` with one cached DB before writing. They refuse blockers the save introduces (every blocker in a new file) and subpatcher/abstraction port x-rank changes, and they warn on removed cords. `force=True` bypasses the gate with a `SaveGateWarning`.

## Commits

| Task | Commit | Message |
|------|--------|---------|
| 1 | ac650b2 | fix(save): save_patch_roundtrip refuses new validation errors and critic blockers vs original_text/HEAD, force=True bypasses; one cached DB (Q7 A3) |
| 2 | 0c70800 | fix(save): save gate warns on removed cords, refuses subpatcher port x-rank changes, gates write_gendsp with force= (Q7 R1) |
| 3 | 4dd8424 | docs(save): hooks docstring, README and TECHNICAL describe the automatic save gate (Q7 docs) |

Each commit touches only plan-listed paths and was made with `git commit -- <paths>`. HEAD was still `676674a` at Step 0, so no concurrent commit landed. The stash list is unchanged.

## Test Totals

- **Baseline** (Step 0, HEAD 676674a): 2559 passed, 1 xfailed, 1 xpassed, 29 warnings. This matches the recorded baseline.
- **After Task 1:** 2646 passed, 1 xfailed, 1 xpassed, 29 warnings (+87 new tests).
- **After Task 2 and Task 3 (final):** 2661 passed, 1 xfailed, 1 xpassed, 29 warnings. `tests/test_save_gate.py` holds 102 tests in 826 lines.
- The warning count is unchanged (29 before and after), so the gate adds no warning to existing tests.
- **RED counts:**
  - Task 1: 83 failed, 4 passed. The 16 behavior tests failed, plus all 67 round-trip sweep cases, which failed on ImportError of `_gate_report`. The 4 that passed are the pre-existing-blocker guards (a, b, c) and the OQ1 non-git save.
  - Task 2: 9 failed, 93 passed. The 9 RED cases were cord warnings x3, port refusals/force x4 and gendsp refuse/force x2. The guard cases passed already.
- After every run, the MAX repo HEAD and staged set were unchanged by the tests, and `git status --porcelain -- patches/` showed only the pre-existing `.active-project.json`.
- The Python 3.10 `ast.parse(feature_version=(3, 10))` gate passes on every changed .py file.

## OQ1 Resolution

**A, user-chosen 2026-10-12:** when there is no `original_text` and no HEAD version, the file on disk is the baseline. "New file" means no `original_text`, no HEAD version and no file at the path. The test `test_oq1_non_git_file_on_disk_is_baseline` saves a non-git patch that already contains blockers (GAIN + OOR) without `original_text`, and it succeeds.

## Live Line References vs Spec

- TECHNICAL.md "### Write Hooks" is at 460 (spec: 462). The section was 460-470 before and is 460-472 after.
- `save_patch_roundtrip`: lines 226-299 before, 242-331 after.
- `write_gendsp`: lines 381-418 before, 817-872 after. Most of the shift comes from the new save-gate section, which sits just before `write_gendsp`.

## Caller Audit

- The planner's probe found 35 gated calls in 8 test files.
- Exactly one existing caller needed a change: `tests/test_hooks.py::TestWriteAndSync::test_save_patch_roundtrip_uses_sync`. Its data became `{"patcher": {"boxes": [], "lines": []}}`. The old fixture hit the Layer 1 error "Missing or invalid 'lines' array", which the gate now treats as a new-file blocker. The test is about fsync, not validation.
- No src or tools caller exists outside the `src/maxpat/__init__.py` re-export.
- `tests/test_save_safety.py` passes unedited, including both `simplefilter("error")` saves.

## Round-Trip Sweep and Cost

- Every committed `patches/*/generated/*.maxpat` and `*.gendsp` (67 files) was run through `Patcher.from_dict(deepcopy).to_dict()` and then `_gate_report`. Result: 0 new blockers, 0 removed cords and 0 port changes (`TestRoundTripNoFalseBlocks`, 67 cases).
- **Measured cost on terrain-synth (835 boxes):** `_gate_report` (both pipelines on baseline and new, plus the cord and port walks) takes 0.142 s, and `_head_text` (two git calls) takes 0.031 s. The cached `_gate_db()` means a clean save constructs 0 new ObjectDatabases (`test_clean_save_constructs_no_database`).

## Settled Decisions Worth Knowing

- **New proposed removals block on edits** (Q1 hand-off). The gate counts every validation error with `has_blocking_errors(is_new=True)` semantics, and only pre-existing proposed removals are exempted, through the baseline diff.
- **"x-rank" means the rank of ports present in both versions.** A swap, a mid-insert or a mid-delete blocks. A port appended rightmost does not.
- **Changes already in `original_text` are exempt from the cord and port checks.** Example: the user deleted a cord or reordered ports in MAX after the last auto-commit. A cord counts as removed only when every reference (HEAD and `original_text`) has it. A port counts as changed only when its rank differs from every reference.
- **Path elements include the box text** (`(box id, text or maxclass)`), so a regenerated subpatcher reusing an id isn't compared port-for-port. Inner ids collide with outer ids, which is why cord and port keys are path-qualified.
- **Key ids are de-duplicated** (`sorted(set(ids))`). Fan-out messages repeat the same id ("'+' (obj-2), '+' (obj-2)"), and the plan's TestFindingKey bullet expects the id tuple `("obj-1", "obj-2")` for a message naming obj-2 plus a proposal `obj-1 -> obj-2`.

## Deviations from Plan

**1. [Rule 2 - Clarification] Unique box ids in `_finding_key`**
- **Found during:** Task 1 (writing TestFindingKey).
- **Issue:** S4 says "the extracted ids, plus the source and destination ids of proposed_removal". Taken literally, that yields `("obj-1", "obj-2", "obj-2")`, while the behavior bullet requires `("obj-1", "obj-2")`.
- **Fix:** ids are de-duplicated before sorting. Matching strength is unchanged, because the template and `proposed_removal` stay in the key.
- **Commit:** ac650b2.

Otherwise the plan was executed as written.

## Residuals (out of scope)

- Validation and the critics only look at the top level, so findings inside subpatchers are not gated until Q19/Q20. The cord and port checks already recurse.
- A regenerated patch with renumbered box ids produces cord-removal warnings. These are warnings only and never block.
- The DB cache is per process: edits to the DB files are not seen until the process restarts.
- `write_js` stays report-only.
- The CI job / PostToolUse hook from R1 is Q8.
- If a validator or critic crashes on a malformed dict, the exception propagates out of the save. No such crash occurs on any of the 67 committed patches.

## Doc Impact, Not Edited (rule 8)

- **CLAUDE.md Rule #7:** `PatchValidationError`, `SaveGateWarning` and `force` now apply to the gate as well as the stale check.
- **`.claude/skills/references/shared-capabilities.md:147`:** the auto-commit paragraph could mention the gate.
- **`.claude/skills/max-lifecycle/references/project-structure.md:80`:** "hooks which trigger validation on write" is now true for .maxpat/.gendsp, but not for .js.
- **`.claude/skills/max-patch-agent/SKILL.md:314-321`** (R1's "SKILL.md:317-320"): still correct; the gate is a backstop.
- **`.claude/skills/max-critic/SKILL.md:49`:** could note that the save path now re-runs both pipelines.
- **`README.md:172`:** Q5's auto-commit scope.
- **The max-dsp-agent skill's `PatchValidationError(...)` example** (SKILL.md:309-322) still works, because the error still accepts a bare message.

## Hand-offs

- **Q8:** CI must run `tests/test_save_gate.py`. Its tmp repos need git on the runner; the module is skipped when git is missing.
- **Q19/Q20:** once validation recurses, `_finding_key` needs a patcher path, because inner ids collide with outer ids.
- **Q36:** `edit_patch` sessions should reach `_run_save_gate` through `save_patch_roundtrip`.
- **Q39:** quick-fix payloads can attach to `PatchValidationError.findings`.

## Confirm in MAX (rule 9)

No patch file changed, so nothing needs confirming in MAX. Two behavior changes to know about:
- A save that would introduce a blocker, or reorder a subpatcher's ports, now raises `PatchValidationError`. Claude must fix it, or ask before using `force=True`.
- Removed cords now print a `SaveGateWarning`.

## Threat Flags

None. The only new surface is `git rev-parse` / `git show HEAD:<rel>` through `_run_git`: argv with no shell, `rel` derived from resolved paths under the repo root. This is covered by T-qsr-07.

## Self-Check: PASSED

- FOUND: tests/test_save_gate.py
- FOUND: src/maxpat/hooks.py (`_run_save_gate`, `SaveGateWarning`, `db=_gate_db()`)
- FOUND: src/maxpat/critics/__init__.py (`review_packages(patch_dict, db=db)`)
- FOUND commits: ac650b2, 0c70800, 4dd8424
