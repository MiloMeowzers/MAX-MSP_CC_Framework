---
phase: quick-261016-pz8
plan: 01
subsystem: cleanup
tags: [dead-code, q32, s9, refactor]
status: complete
requires: []
provides:
  - tests/test_dead_code_removed.py (permanent removal guard, 35 cases)
affects: [src.maxpat public API, max-patch-agent skill, overrides.json, tools/extract_pkg_io.py, dsp_sim, audit package]
tech-stack:
  added: []
  patterns: [git ls-files reference scan as a removal guard]
key-files:
  created:
    - tests/test_dead_code_removed.py
  modified:
    - TECHNICAL.md
    - README.md
    - .claude/skills/max-patch-agent/SKILL.md
    - .claude/skills/references/shared-capabilities.md
    - .claude/max-objects/overrides.json
    - tools/extract_pkg_io.py
    - src/maxpat/validation.py
    - tests/test_validation.py
    - src/maxpat/{project,aesthetics,__init__,layout,builders,defaults,sizing}.py
    - src/maxpat/dsp_sim/runner.py
    - src/maxpat/dsp_sim/topologies/__init__.py
    - src/maxpat/audit/__init__.py
  deleted:
    - src/maxpat/memory.py
    - tests/test_memory.py
    - scripts/relayout_patch.py
    - .claude/scripts/validate_db.py
    - .claude/scripts/merge_sources.py
    - tests/fixtures/expected/gen_codebox.maxpat
    - .claude/max-objects/verified-objects.json
decisions:
  - "PD-1: DB per-object maxclass field kept (it has test, agent-doc and tool readers)"
  - "PD-5 resolved by user decision (b): Layer 4 GenExpr checks and their 3 tests deleted in a 4th commit"
metrics:
  duration: ~50 min
  completed: 2026-10-16
actuals:
  tokens: 42045
  tasks: 4
  commits: 4
plan_head_before: 7821c0202217510b6bbc07a9c2efd0a0dea285b3
plan_head_after: 71a1914949daecdc393d0371563afaa756c47e89
---

# Quick 261016-pz8: Q32 dead-code removal Summary

Removed 7 dead files, the dead public helpers and internals (including the two Layer 4 GenExpr checks), and the audit package's ImportError swallow. The full behaviour snapshot (DB lookups, aliases, empty-I/O audits, validate_patch on every committed patch file) is byte-identical after every commit. PD-5 was first held back because an existing test exercised it; after the user chose option (b), a 4th commit removed it.

## Decisions to confirm

- **PD-1, DB `maxclass` field: KEPT.** Readers: tests/test_object_schema.py, tests/test_extraction.py (BEAP/Vizzie `bpatcher`), tests/test_sync_max_bundle.py, and agents reading db.lookup() (CLAUDE.md:17, db-maintenance.md:14). Writers: extract_objects.py, extract_abstractions.py, sync_max_bundle.py. Removing it is a data migration, not dead-code removal.
- **PD-11, permanent guard:** tests/test_dead_code_removed.py stays (35 cases). It scans `git ls-files` so removed names can't come back.
- **PD-2, verified-objects.json: DELETED.** It had no reader. The dated audit report that mentions it is left as written.
- **PD-3, dsp_sim wave fallbacks: DELETED.** The runner's try/except became a plain function-local import (kept local to avoid an import cycle), and topologies now imports the single `runner.TopologyError`. test_runner.py's docstring was rewritten.
- **PD-4, audit ImportError swallow: DELETED** the whole block. `src.maxpat.audit` no longer imports its CLI. `python3 -m src.maxpat.audit.cli --help` still works.
- **PD-5, Layer 4 `_check_genexpr_io_syntax` / `_check_genexpr_delay_usage`: DELETED (user decision (b)), in a 4th commit, 71a19149.**
  - The plan had missed that `tests/test_validation.py::TestLayer4GenExprChecks` asserts their errors, so Task 3 first restored them.
  - The user then chose option (b). The two checks, their call sites, the RESEARCH R1 docstring note and the 3 asserting tests are gone. The test names are `test_genexpr_spaced_io_triggers_error`, `test_genexpr_spaced_out_triggers_error` and `test_genexpr_delay_call_triggers_error`.
  - The class stays, with its 2 no-error tests and the gen~ param-message tests.
  - The guard now pins the removal.
- **PD-6, is_complex_patch / suggest_subpatchers: DELETED**, along with the shared-capabilities.md:109 bullet.
- **PD-7, add_node_script: DELETED.** The skill now documents `Patcher.add_box("node.script", ["myscript.js"], x=0.0, y=0.0)` plus `write_js(code, path)`, and the TECHNICAL.md row is gone.
- **PD-8, `_uncovered_empty_io`: DELETED.** It was a surgical text edit: JSON-equal to the base minus the key, numstat `0 15`, no trailing newline (as before). Its refresh code in extract_pkg_io.py is gone. The tool was never run.
- **PD-9, MS_* constants: DELETED.** The sizing.py comment now points at `Patcher.add_labeled_param_bank` (24 px per bar).
- **PD-10:** tests of deleted code were deleted, not retargeted.

## Behaviour changes

- validate_patch on a hand-built top-level newobj `codebox` now returns only the Layer 4b error, `'codebox' is restricted to ['gen', 'rnbo']`. The two redundant Layer 4 regex errors are gone. `has_blocking_errors` is still True (probed after the commit), so the save gate is unchanged. No tracked patch contains such a box, and the snapshot stayed byte-identical.
- `src.maxpat` no longer exports `is_complex_patch`, and Patcher has no `add_node_script`.
- `import src.maxpat.audit` no longer loads its CLI and has no `run_audit`.
- tools/extract_pkg_io.py no longer rewrites overrides.json when nothing merges.
- A broken dsp_sim topologies import now raises ImportError instead of TopologyError.

## Confirm in MAX

None needed. No patch output changes. The behaviour snapshot shows validate_patch output is identical for every committed patch file. `add_box("node.script", ...)` produces the DB's 1-inlet/2-outlet newobj shape, which `test_node_script_box_from_add_box` pins.

## Deviations from Plan

### 1. PD-5 restored in Task 3, then deleted by user decision
- **Found during:** Task 3, at Gate G. It showed 3 new failures in tests.test_validation.TestLayer4GenExprChecks.
- **Task 3:** validation.py was restored, so commit 7964d318 does not touch it.
- **Then:** the user chose option (b), so a 4th `(Q32)` commit, 71a19149, deleted the checks and the 3 tests.
  - The guard was red first: Q/red-t4.txt has 3 failures.
  - Gate G was rerun with 57 expected removals and passed. The snapshot was byte-identical.
- **Out-of-plan file:** tests/test_validation.py is outside the plan's files_modified list. The user's decision authorized it.

### 2. Step 0 snapshot scope
- The plan prototype said 95 files and 215 findings. `git ls-tree <base> -- patches`, filtered to the 4 suffixes, gives **71 tracked files and 211 rows**. The prototype most likely counted files on disk, including untracked ones. I followed the plan's specification (tracked files at base). The snapshot is deterministic (cmp passed).

### 3. Red evidence for Task 2
- I made Task 2's source edits before appending the guard class, so the working-tree red run showed only 1 failure. To fix this I ran the guard against the committed HEAD (c535c705) in a temporary detached worktree, then removed the worktree. Q/red-t2.txt holds both runs: 7 failures at HEAD, 1 in the working tree.

## Evidence

- **Baseline (7821c020):** 2 failed, 5317 passed, 5 xfailed, 1 xpassed (5325 junit ids).
- **Final (after 71a19149):** 2 failed, 5295 passed, 5 xfailed, 1 xpassed (5303 ids). The 2 failures are the unchanged q29-check pair.
- **Removed/added per task:**
  - T1: 29 removed, 9 added;
  - T2: 52 removed, 17 added;
  - T3: 54 removed, 33 added;
  - PD-5 commit: 57 removed (the 54 plus the 3 TestLayer4GenExprChecks tests), 35 added.

  No pass changed to non-pass, and every added id passes.
- **Snapshot**, identical after every task:
  - db_names 3091;
  - db_lookup_sha256 `80951c730234af2c…`;
  - aliases_sha256 `30d4817fa771bb2e…`;
  - 211 validate rows over 71 files.
- **Imports:** no new unused import in any task.
- **audit_db `ui_maxclasses_gap`:** 1 (`gen~`, from gen_codebox.maxpat) before, 0 after. DEF-knq-01 is closed.
- **Hygiene:**
  - `patches/` untouched, and the stash list is unchanged (empty).
  - The first 3 commits stay within files_modified; the PD-5 commit adds tests/test_validation.py, as the user authorized.

## Doc impact

- **TECHNICAL.md:**
  - line 3 no longer says "and memory system";
  - the Memory System TOC entry, the "No memory agent" note, the Memory System section, the `.max-memory/` tree lines and the "Memory store operations" bullet are gone;
  - the add_node_script table row is gone.
- **README.md:199:** "memory system, " removed. The patch table is untouched.
- **shared-capabilities.md:** the is_complex_patch bullet is removed.
- **max-patch-agent SKILL.md:** the node.script bullet now shows the add_box form.
- **CLAUDE.md:** not edited.
- TECHNICAL.md's stale Test Suite counts are left alone.

## Known Stubs

None.

## Follow-ups

- The 2 q29-check baseline failures, which come from the user's patches/q29-check project.
- Optional: a task that strips the DB `maxclass` field together with its 3 writers and 3 test readers (the PD-1 alternative).
- STATE.md's deferred DEF-knq-01 can be marked closed.

## Commits

- c535c705: memory library, relayout_patch.py, validate_db.py, merge_sources.py, gen_codebox fixture, verified-objects.json (Q32)
- 1b29cd9d: examples catalog, contrast_text_color, is_complex_patch, suggest_subpatchers, layout opt-out (Q32)
- 7964d318: add_node_script, MS_* constants, `_uncovered_empty_io`, dsp_sim fallbacks, audit ImportError swallow (Q32)
- 71a19149: the two Layer 4 GenExpr regex checks and their 3 tests (Q32, PD-5 option b)

## Self-Check: PASSED

- tests/test_dead_code_removed.py exists. All 7 deleted paths are absent.
- Commits c535c705, 1b29cd9d, 7964d318 and 71a19149 are present in `git log`.
