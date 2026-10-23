---
phase: quick-261022-o2q
plan: 01
subsystem: critics / quickfix
tags: [Q39, critics, quick-fix, edit_patch, max-iterate]
status: complete
requires: [Q36 edit_patch session + patch_diff]
provides: [CriticResult.fix, src/maxpat/critics/fixes.py, src/maxpat/quickfix.py, /max-iterate --fix]
affects: [structure_critic, dsp_critic, package_critic, src.maxpat exports, .claude/commands/max-iterate.md]
tech-stack:
  added: []
  patterns: [frozen dataclass payloads, validate-all-then-mutate applier, re-review-by-key before apply]
key-files:
  created:
    - src/maxpat/critics/fixes.py
    - src/maxpat/quickfix.py
    - tests/test_quickfix.py
  modified:
    - src/maxpat/critics/base.py
    - src/maxpat/critics/structure_critic.py
    - src/maxpat/critics/dsp_critic.py
    - src/maxpat/critics/package_critic.py
    - src/maxpat/__init__.py
    - src/maxpat/critics/__init__.py
    - .claude/commands/max-iterate.md
decisions:
  - "gen~ @param: parity critic check in dsp_critic (same condition as validation Layer 4), validation.py untouched"
  - "Q23 bach row (bach -> non-bach without @out t, warning) carried out here; Q23 should skip it"
  - "Preview is a separate read; apply re-derives payloads from the edit_patch session's fresh read by finding key"
  - "scale bounds always in float form (scale 0. 127. 0. 1.); constant sources get clip 0. 1."
  - "bach_out_mode exempts bang outlets (DB digest) and forwarders (outlet, send, s, forward, p, patcher, bpatcher, poly~, mc.poly~, button)"
  - "UI bach boxes (bach.roll) read the saved 'out' attribute; they get the warning but no fix (no Q39 op sets an attribute)"
metrics:
  duration: ~80 min
  completed: 2026-10-22
estimate:
  tokens: 205000
actuals:
  tokens: 24300
  tasks: 3
  commits: 3
plan_head_before: 74ce497e7243ab78cc4c2517d7232b485533afcc
plan_head_after: a38c65db2c19e03609a17927721ce8d84fc1751e
---

# Phase quick-261022-o2q Plan 01: Q39 quick-fix payloads Summary

Critic findings now carry an optional frozen `Fix` payload (ordered `t ...` for reconverging fan-outs, `@param $1` -> `param $1`, `scale`/`clip` before unsafe gain, `@out t` on bach). `src/maxpat/quickfix.py` lists, previews and applies the fixes, and `/max-iterate --fix` applies them through one `edit_patch` session, so the stale check, save gate and path-scoped commit stay in force.

## Commits

| Task | Commit | Message |
|------|--------|---------|
| 1 | 4735a84b | feat(critics): CriticResult.fix payloads; reconverging fan-out gets an ordered trigger fix applied through edit_patch |
| 2 | 5a17bd36 | feat(critics): quick-fix payloads for gen~ @param, unsafe gain (scale/clip) and bach @out t |
| 3 | a38c65db | feat(iterate): /max-iterate --fix previews and applies critic quick fixes through edit_patch |

No commit touches `patches/` or `patterns/`. Every commit names explicit paths.

## Test counts

- **Baseline** (Step 0, HEAD 74ce497e): rc 0, **6064 passed, 5 xfailed, 1 xpassed**. This matches the planning-time figure.
  - Note: I made the Task 1 source edits after pytest finished collecting but before the run ended. The counts are identical to the planning-time expectation, and baseline-junit.xml has no `tests.test_quickfix` ids.
- **Final** (after Task 3): rc 0, **6127 passed, 5 xfailed, 1 xpassed**.
- **junit_diff.py**: `base=6070 new=6133 added=63 offenders=0`. All 63 added ids are from `tests.test_quickfix`; none were removed or regressed.
- **Red counts**:
  - Task 1: against the base tree the whole module fails at collection (ModuleNotFoundError `src.maxpat.critics.fixes`, 31 tests). With only the payload model and applier added, and the structure critic unchanged, 13/31 fail.
  - Task 2: 15 of the 28 new cases are red. The no-finding and no-fix cases pass already, because the fix defaults to None.
  - Task 3: 2 red (exports, doc). The corpus test was already green after Tasks 1-2.
- **New test ids** (tests/test_quickfix.py):
  - Task 1:
    - test_critic_result_fix_defaults_to_none, test_critic_result_fix_is_keyword_only, test_fix_model_frozen_and_hashable, test_fix_model_rejects_unknown, test_contract_accepts_builder_and_rejects_breaches
    - test_fan_blocker_carries_trigger_fix, test_three_branch_order, test_trigger_letter_from_outlettype[bang-b|int-i|float-f|list-l|-l], test_trigger_letter_unknown_type_no_fix, test_conflicting_order_no_fix, test_warning_fan_out_no_fix, test_duplicate_branch_cords_no_fix
    - test_apply_fix_on_fan_in_memory, test_guard_add_box_outside_allowlist, test_guard_gain_normalizer_with_metro, test_guard_absent_cord, test_guard_set_text_mismatch, test_guard_unknown_scope_path, test_guard_no_fix, test_nested_fix_edits_only_inner
    - test_finding_key_and_tuple_passthrough, test_fixable_findings_does_not_mutate_dict, test_apply_quick_fixes_missing_key_in_memory, test_preview_writes_nothing, test_edit_patch_applies_trigger_fix, test_edit_patch_missing_key_writes_nothing, test_quickfix_module_never_saves
  - Task 2:
    - test_gen_param_warning_and_fix, test_gen_param_multi_segment, test_gen_param_not_cabled_to_gen_no_finding, test_gen_param_parity_with_validation[5 params], test_gen_param_apply_clears_both
    - test_gain_slider_scale_fix, test_gain_live_dial_bounds, test_gain_via_line_tilde, test_gain_constant_clip, test_gain_no_fix_message_into_line, test_gain_no_fix_two_path_cords, test_gain_no_fix_ops_push_past_one
    - test_bach_out_warning_and_fix, test_bach_out_replaces_existing_value[2 params], test_bach_out_t_no_finding, test_bach_out_one_finding_per_box, test_bach_out_exempt_consumers[bach.flat|outlet|send|p], test_bach_roll_bang_outlet_exempt, test_bach_ui_out_attribute_read, test_bach_out_apply_keeps_io_and_cords, test_bach_out_guard_rejects_non_bach_box
  - Task 3: test_exports, test_max_iterate_documents_fix, test_corpus_fixes_apply_cleanly
- **Snapshots**: `git status --porcelain patches patterns` and `git stash list` match their Step 0 snapshots (both empty).

## Corpus outcome (63 tracked patches, HEAD bytes)

| Kind | Findings | Fix offered | Detail |
|------|----------|-------------|--------|
| insert_trigger | 1 blocker | 1 | rhythmic-sampler slot.maxpat, buffer~ obj-1 outlet 1. The fix is `t b b` with outlet 1 -> obj-27 (`setbuffer #1`, reaches waveform~ obj-4 at inlets 2/3) and outlet 0 -> obj-28 (`set #1`, reaches obj-4 at inlet 0). This is the planning-time expectation. |
| insert_gain_normalizer | 1 blocker | 1 | slot.maxpat dial obj-54 (size 121, mult 0.01, floatoutput, range 0-1.21) -> `t f f` obj-166 -> `$1 10` -> line~ -> `*~` obj-9 inlet 1. The fix is `scale 0. 1.21 0. 1.` on the dial -> `t f f` cord. It is offered because exactly one traced cord leaves the dial, and the `$1 10` message continues to `$1` (it is not a line~ constant). Caveats: the dial deliberately allows a slight boost (this blocker is allowlisted as intentional), and `t f f` outlet 1 also feeds a flonum display, which would then show the normalized value. Accepting this fix is the user's call. |
| rewrite_gen_param | 0 | 0 | |
| set_bach_out | 0 | 0 | The physics-composition bach -> non-bach cords already use `@out t`. bach.roll obj-67 (`out: nnnnnnn`) produces no finding. |

Every offered fix applies cleanly in memory. Afterwards its own key is gone, no new blocker key appears, and the validate_patch error count does not rise (`test_corpus_fixes_apply_cleanly`). No allowlist entries were added.

## Decisions

- **Parity critic check instead of moving the validation rule.** `dsp_critic._check_gen_param_message_syntax` uses validation.py's condition: a message box matching `@\w+\s+\$`, a control cord into a box named `gen~`, and one finding per message box. That way the payload lives on a CriticResult. validation.py is not edited. Parity is pinned by a 5-case parametrized test.
- **Q23 bach row carried out here.** `bach_out_mode` is a warning. **Q23 should skip this row.**
- **Preview is a separate read.** A with-block cannot span the user's confirmation. `apply_quick_fixes` re-reviews the session's fresh read before each key, so a MAX save between preview and apply is caught as FixError (key gone or payload changed) or as the session's StaleFileError.
- **Scale bounds are always in float form** (`max_float`: `127.` / `-12.` / `1.21`). This avoids the int-argument truncation trap in `scale`. Constant sources get `clip 0. 1.`. A message feeding line~ directly gets no fix.
- **Trigger order.** At each meeting box, a branch that reaches an inlet > 0 fires before a different branch that reaches inlet 0. The sort is a stable topological sort, with ties kept in cord order. Conflicting constraints (a cycle), a duplicate branch cord, or an outlettype other than bang/int/float/list/"" give no fix.
- **bach exemptions.**
  - Outlets whose DB digest contains "bang" are exempt (bach.roll outlet 7).
  - Forwarders are exempt (outlet, send, s, forward, p, patcher, bpatcher, poly~, mc.poly~, button).
  - UI bach boxes read the saved `out` attribute. They get the warning with no fix, because no Q39 op sets an attribute.
- **Applier safety.**
  - Every op is validated before any mutation: contract, add_box allowlist {t, trigger, scale, clip}, boxes, cords, port ranges (new-box I/O from the DB), set_text `old_text`, a message box for rewrite_gen_param, and for set_bach_out a Bach newobj with unchanged I/O.
  - A failure during mutation restores the scope's boxes and lines lists.
  - quickfix.py never references a save or commit function and never passes `force`; an AST test checks this.
- **Gain trace bookkeeping.** The consumer cords are read from `via` after the BFS completes, not at visit time: a state reached through two cords is visited only once. A truncated walk (hop limit or state cap) offers no fix. The blocker text, suggestion, key and the set of reported sources are unchanged.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Gain fix path-cord bookkeeping read at visit time**
- **Found during:** Task 2 (`test_gain_no_fix_two_path_cords`)
- **Issue:** The trace dedupes states with `seen`. A slider with two path cords therefore recorded only the first consumer and got a fix it should not have.
- **Fix:** `note()` records states; cords are gathered from `via` after the walk. A truncated walk gives no fix.
- **Commit:** 5a17bd36

**2. [Rule 1 - Bug] UI bach boxes (bach.roll) were invisible to the detector**
- **Found during:** Task 2 (`test_bach_roll_bang_outlet_exempt`)
- **Issue:** bach.roll is a UI maxclass with no `text`, so `@out` cannot be read from arguments.
- **Fix:** Read the saved `out` attribute (evidence: physics-composition obj-67 `"out": "nnnnnnn"`). Emit the warning without a fix. I adjusted the new test to assert `fix is None` for the UI box and added `test_bach_ui_out_attribute_read`. No existing test changed.
- **Commit:** 5a17bd36

**3. [Rule 3 - Blocking] Invalid escape in the dsp_critic module docstring**
- I rewrote the regex mention as prose (`@name $N`) so the module compiles under `-W error`. This was done in Task 2.

Builder placement: the Task 2 builders were drafted with Task 1 but held back and landed in the Task 2 commit, so the commit boundaries match the plan.

## Known Stubs

None.

## Doc impact (not edited, fix-plan rule 8)

- `.claude/skills/max-critic/SKILL.md`: mention `CriticResult.fix` and the four kinds, plus the new `gen_param_message_syntax` and `bach_out_mode` warnings.
- `.claude/skills/references/severity-contract.md`: list the two new warning rules, and state that a fix payload never changes severity or the finding key.
- `.claude/skills/references/shared-capabilities.md`, edit protocol: point to `/max-iterate --fix` for critic-fixable findings.
- `TECHNICAL.md`: add `src/maxpat/quickfix.py` and `src/maxpat/critics/fixes.py` to the module map, with the preview/apply flow.
- `/max-diagnose`: suggest `--fix` when a mapped finding carries a payload.
- CLAUDE.md bach section: could mention that the critic now flags a missing `@out t`.

## Follow-ups

- mc.gen~ `@param` (validation's parity condition is gen~ only).
- Fixes for warning-level (non-reconverging) fan-outs.
- Message -> line~ gain rewrites (normalizing only the target atoms).
- A `set_attr` op so UI bach boxes (bach.roll `out`) can be fixed.

## Confirm in MAX

1. `t l l` passes anything-messages (e.g. `set foo`) unchanged, and the chosen firing order is right on a real reconverging fan-out. Use slot.maxpat's buffer~ obj-1 outlet 1 -> `t b b` (outlet 1 `setbuffer #1` first, outlet 0 `set #1` last) on a scratch copy.
2. `scale 0. 127. 0. 1.` (and `scale -12. 12. 0. 1.`, `scale 0. 1.21 0. 1.`) outputs floats in 0.-1.
3. `@out t` on a bach object box (`bach.nth 1 @out t` -> `expr`) gives plain MAX lists with no "wrong message or type".
4. Run `/max-iterate --fix` end to end on a scratch copy: list, choose, preview render, apply in one edit_patch session, `session.diff.render()`, the SaveGateWarning naming the rerouted cords, and a path-scoped commit.

## Self-Check: PASSED

- FOUND: src/maxpat/critics/fixes.py, src/maxpat/quickfix.py, tests/test_quickfix.py
- FOUND commits: 4735a84b, 5a17bd36, a38c65db
- Task 3 full verify command: VERIFY_PASS
