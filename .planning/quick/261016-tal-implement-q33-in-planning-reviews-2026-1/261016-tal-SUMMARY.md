---
phase: quick-261016-tal
plan: 01
subsystem: maxpat-core
tags: [refactor, box-factory, critics, gain-staging, layout, consolidation]
status: complete
requires:
  - phase: quick-261016-pz8
    provides: Q32 dead-code removal (base 7a80ff86)
provides:
  - Box.structural, the one factory for boxes built without a DB lookup
  - src/maxpat/gain_staging.py (shared missing-gain traversal and oscillator vocabulary)
  - sizing.outlet_x / inlet_x / IO_MARGIN (shared port geometry)
  - maxclass_map.ui_control_names(db) plus the three pinned purpose sets
  - CriticResult rule / box_ids / port, with critics.base.finding_ids
  - tests/test_consolidation.py permanent guard
affects: [builders, rnbo, externals, validation, critics, layout, analysis, review allowlist]
actuals:
  tokens: 29100
  tasks: 3
  commits: 3
plan_head_before: 7a80ff86b30f5af715cf877937b8141c928c67e1
plan_head_after: 2e85ff34fe0f9f9219921f7280f624a97f6af104
tech-stack:
  added: []
  patterns:
    - "Structural boxes: Box.structural(maxclass, text, nin, nout, outlettype, rect, /, *, box_id, ...)"
    - "Critic findings carry rule / box_ids / port; tests key on those, never on finding text"
key-files:
  created:
    - src/maxpat/gain_staging.py
    - tests/test_consolidation.py
  modified:
    - src/maxpat/patcher.py
    - src/maxpat/builders.py
    - src/maxpat/rnbo.py
    - src/maxpat/externals.py
    - src/maxpat/hooks.py
    - src/maxpat/validation.py
    - src/maxpat/sizing.py
    - src/maxpat/layout.py
    - src/maxpat/aesthetics.py
    - src/maxpat/maxclass_map.py
    - src/maxpat/analysis.py
    - src/maxpat/critics/base.py
    - src/maxpat/critics/dsp_critic.py
    - src/maxpat/critics/ext_critic.py
    - src/maxpat/critics/layout_critic.py
    - src/maxpat/critics/m4l_critic.py
    - src/maxpat/critics/package_critic.py
    - src/maxpat/critics/rnbo_critic.py
    - src/maxpat/critics/structure_critic.py
    - tests/test_integration_patches.py
    - tests/review_blocker_allowlist.json
    - tests/test_uninitialized_state.py
    - tests/test_critic_precision.py
key-decisions:
  - "PD-6: UI purpose sets kept split and pinned beside a DB-derived ui_control_names(db); unification left as a user decision"
  - "PD-7: CriticResult gains keyword-only port as well as rule / box_ids"
  - "Coordinator decision C: _FANOUT_RE moved verbatim into tests/test_critic_precision.py, its only remaining user"
requirements-completed: [S3, S7, S12]
duration: 34min
completed: 2026-10-16
---

# Quick 261016-tal Plan 01: Q33 consolidation Summary

**This was a pure refactor with no output change.** All 17 hand-built boxes now go through `Box.structural`. Validation and the DSP critic share one gain-staging traversal, and layout and its critic share one port-geometry helper. The UI-control purpose sets now live beside a DB-derived control set. Critic findings carry structured `rule` / `box_ids` / `port` fields, and the allowlist keys on those instead of parsing finding text.

## Decisions to confirm

- **PD-6 (unifying the UI-control sets).** Which way should the three UI-control sets go?
  - (a) Keep the split purpose sets. This is the current state: LAYOUT_BAND_CONTROLS, PRESENTATION_CONTROLS and PARAMETER_LIST_CONTROLS are pinned subsets of ui_control_names(db).
  - (b) Unify all three on ui_control_names. Measured impact: about 14 more presentation-coverage warnings in 12 files (13 gain~, 1 button), analyze() changes in 14 files, and 29 more control kinds banded in new layouts.
  - (c) Unify, but with DB-derived per-purpose filters (for example, presentation leaves out the "MSP U/I" category).
  - (b) and (c) change behaviour, so either one becomes its own quick task.
- **PD-7:** CriticResult got a keyword-only `port` field on top of `rule` / `box_ids`. Without it, the fan-out and unsafe-gain allowlist keys would be weaker than the old regex keys. The alternative is to drop `port` and accept weaker keys.
- **PD-1:** `Box.structural` is a classmethod. Its six spec arguments are positional-only. `box_id` (required), `name`, `args`, `font`, `inner`, `saved_attrs` and `bpatcher_attrs` are keyword-only, and `**attrs` becomes `extra_attrs`. Nothing passed in is copied.
- **PD-2:** Ported: builders x9, rnbo x7, externals x1. Not ported: the `from_dict` loader and the test fixtures.
- **PD-3:** Structural boxes now carry the full `Box.__init__` attribute set: `target_id`, `nudged_from`, `_loaded_rect` and `_loaded`, all None. Two existing drifts are kept as they are: the embedded bpatcher still has no `embed: 1`, and the rnbo~ parent keeps maxclass `rnbo~`.
- **PD-4:** gain_staging.py holds OSCILLATOR_NAMES, MC_OSCILLATOR_NAMES and find_ungained_paths. Some things stay per caller: which cords count as signal, which oscillator set is used, the severity and wording, and the dsp_roles sets.
- **PD-5:** `outlet_x` / `inlet_x` / `IO_MARGIN` live in sizing.py. layout.py and layout_critic.py import them under their old private names. Both `_resolve_patcher_bg` wrappers are deleted.
- **PD-8:** `rule` is the check function's name without `_check_`, plus per-finding `ext_*` ids and `rnbo_missing_inner_patcher`. `box_ids` are the ids the text names, in the order it names them, and never a "?" placeholder. text_contrast and param_naming also include the subject box. Nested refs such as `obj-1/obj-5` are split into their ids. `port` is set only for fan-out (source outlet), unsafe gain (gain inlet) and bach llll (destination inlet). This needed a small helper, `critics.base.finding_ids`.
- **PD-9:** The 2 allowlist entries are now {severity, rule, box_ids, port, path, source, reason}, and `_doc` names the new key. The fan-out key is stricter than before: it also lists the destination and reconvergence ids.
- **PD-10:** The Q24 helpers in test_uninitialized_state.py read `rule` / `box_ids`. `_ID_RE`, `_strip_prefix` and `import re` are gone, and its own allowlist JSON is unchanged.
- **PD-11:** Not changed: the save-gate text key (`hooks._finding_key`), the regex in the validate-error allowlist, and the max-critic skill's repeat detection.
- **PD-12:** S12's `_route_clear_path` nearby-box limit is outside Q33's list and is now a follow-up.
- **PD-13:** tests/test_consolidation.py stays as a permanent guard (23 tests).
- **Coordinator decision C (made mid-run):** `tests/test_critic_precision.py` imported `_FANOUT_RE` from test_integration_patches, which the plan did not anticipate. The regex was moved verbatim into test_critic_precision.py (pattern identity checked against the base), so that test's meaning is unchanged. The coordinator added the file to files_modified and to Task 3's `<files>` and verify. It was also added to q33_gate.py's IMPORT_FILES; it has no unused imports, before or after.

## Q33 item status

- **Box factory:** COMPLETE. `Box.structural`; builders.py, rnbo.py and externals.py contain no `Box.__new__` call (AST guard).
- **Gain staging:** COMPLETE. There is one traversal and one oscillator vocabulary, in src/maxpat/gain_staging.py. validation Layer 4 (warning) and dsp_critic (blocker) both call it.
- **Geometry helpers:** COMPLETE. `sizing.outlet_x` / `inlet_x` take a Box or a raw dict. Both `_resolve_patcher_bg` wrappers are deleted.
- **One UI-control set:** PARTIAL (explicit deferral). `ui_control_names(db)` was added (47 names), and the three purpose sets were co-located in maxclass_map.py and pinned, not replaced. Measured unification impact: ~14 presentation-coverage warnings in 12 files, analyze() changes in 14 files, 29 more banded control kinds in new layouts (see PD-6).
- **CriticResult:** COMPLETE. All 49 sites name a rule, and the corpus `box_ids` agree with the ids the finding text names. The integration test, the review allowlist and the Q24 helpers key on structured fields.

## Behaviour changes

None observable. The behaviour snapshot was byte-identical to Step 0 after the tracer and after every task. It covers builder JSON, laid-out JSON, per-box attribute rows, and validate / review / analyze / layout output over the whole committed corpus.

Additive API changes:
- Structural boxes carry the full `Box.__init__` attribute set (PD-3).
- `src.maxpat.sizing` gains public `outlet_x`, `inlet_x` and `IO_MARGIN`.
- `maxclass_map` gains `ui_control_names` and the three sets.
- `CriticResult` gains keyword-only `rule`, `box_ids` and `port`; `critics.base` gains `finding_ids`.

## Confirm in MAX

None needed. Builder output is byte-identical and no finding changed (text, severity or order).

## Deviations from Plan

1. **[Rule 3 - Blocking] `_FANOUT_RE` importer outside scope.** The plan's audit missed that `tests/test_critic_precision.py` imports it, and `test_ordering_checks` and `test_uninitialized_state` import that module. I stopped at a decision checkpoint, and the coordinator chose option C (see Decisions). Commit 2e85ff34.
2. **Baseline count.** Step 0 measured 2 failed, **5295** passed, 5 xfailed, 1 xpassed; the plan said 5296. The cause is Q32's final commit 71a19149, which removed 3 Layer 4 tests and added 2 dead-code guards. The junit statuses are otherwise identical to the Q32 final run. Recorded, not fixed.
3. **TestSharedHelpers red evidence.** I wrote Task 2's green code before its tests. To keep the red evidence honest, the new tests were run against the Task 1 commit (a56d88a4) in a temporary detached worktree, which was then removed: 10 failed, 7 passed (`red-t2.txt`). The Task 1 and Task 3 reds were run in the main tree before their changes.
4. **The baseline pytest ran while my first edits were being made.** It was started in the background and collected before any edit. Its statuses match the Q32 final junit exactly, apart from the Q32 delta in item 2.
5. **Added helper `critics.base.finding_ids`.** It deduplicates ids and drops None / "?" so that no site emits a placeholder (PD-8).

## Follow-ups

- PD-6 (b) or (c), if chosen: unify the UI-control sets.
- Unify the gain-staging cord test, oscillator set and severity across the two layers (PD-4).
- The embedded bpatcher's missing `embed: 1`, and the rnbo~ parent's maxclass `rnbo~` instead of newobj (PD-3).
- Key the save gate on rule / box_ids instead of the text template (PD-11).
- Key the max-critic loop's repeat detection on rule + box_ids.
- S12's `_route_clear_path` nearby-box limit (PD-12).
- Layout and analyze() are nondeterministic under hash randomization: 49 of 61 committed files differ between unseeded runs. The gate pins PYTHONHASHSEED=0.
- The 2 q29-check baseline failures (README patch table; the Q24 corpus allowlist case for q29-check.maxpat).

## Doc impact (listed, not edited; rule 8)

- `.claude/skills/max-dsp-agent/SKILL.md:42` teaches "Codebox via `Box.__new__()` pattern"; it should point to `Box.structural` / `add_gen`.
- `.claude/skills/references/severity-contract.md:11` lists CriticResult as severity / finding / suggestion; it now also has path, rule, box_ids and port.
- `.claude/skills/max-critic/SKILL.md` could key its repeat detection on rule + box_ids.

## Evidence

- Baseline: `2 failed, 5295 passed, 5 xfailed, 1 xpassed` (114.68 s).
- Final: `2 failed, 5318 passed, 5 xfailed, 1 xpassed` (111.36 s), with 23 guard tests added, all passing.
- junit diff (base -> final): 5303 -> 5326 tests. Only `tests.test_consolidation` ids were added, none were removed, and no status changed.
- Snapshot: 11 builder cases, 75 corpus files (61 laid out and analysed), 214 validate rows and 1769 review results. Byte-identical after the tracer, Task 1, Task 2 and Task 3.
- Allowlist audit: 1721 results, 2 blockers, 2 exempted, 0 mismatches. The Q24 rule and ids match the old regex.
- Imports gate: no new unused import in any files_modified .py file.
- No committed file is outside files_modified, `patches/` is untouched, and the stash list is unchanged (empty).

## Commits

- a56d88a4 refactor(patcher): Box.structural; every structural box goes through it (Task 1)
- b915b430 refactor(shared): shared gain staging, port geometry and UI purpose sets (Task 2)
- 2e85ff34 refactor(critics): CriticResult rule / box_ids / port; allowlist keys on them (Task 3)

## Self-Check: PASSED
