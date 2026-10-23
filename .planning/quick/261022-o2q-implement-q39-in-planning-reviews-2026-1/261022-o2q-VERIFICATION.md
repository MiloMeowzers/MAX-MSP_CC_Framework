---
phase: quick-261022-o2q
verified: 2026-10-23T01:05:10Z
status: human_needed
score: 10/10 must-haves verified
covered_files:
  - .claude/commands/max-iterate.md
  - .planning/quick/261022-o2q-implement-q39-in-planning-reviews-2026-1/261022-o2q-PLAN.md
  - .planning/quick/261022-o2q-implement-q39-in-planning-reviews-2026-1/261022-o2q-SUMMARY.md
  - src/maxpat/__init__.py
  - src/maxpat/critics/__init__.py
  - src/maxpat/critics/base.py
  - src/maxpat/critics/dsp_critic.py
  - src/maxpat/critics/fixes.py
  - src/maxpat/critics/package_critic.py
  - src/maxpat/critics/structure_critic.py
  - src/maxpat/quickfix.py
  - tests/test_quickfix.py
covered_digest: "v2:sha256:4cb12bddf372dbbb14f79dcbdf4f93636b7481475f604ad7898387d4cfdf5c03"
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "In MAX, on a scratch copy of rhythmic-sampler slot.maxpat, apply the offered fix `t b b` on buffer~ obj-1 outlet 1 (outlet 1 -> setbuffer #1, outlet 0 -> set #1)"
    expected: "`t b b` passes the bang-outlet messages unchanged, and the firing order (setbuffer first, set last) works on waveform~ with no console errors"
    why_human: "Real MAX trigger semantics and firing order cannot be checked from Python"
  - test: "Load a patch with `scale 0. 127. 0. 1.`, `scale -12. 12. 0. 1.` and `scale 0. 1.21 0. 1.` inserted by the gain fix"
    expected: "The scale objects output floats in 0.-1. (or 0.-1. for the 1.21 range) and the patch opens with no errors"
    why_human: "scale argument handling needs MAX"
  - test: "Apply `bach.nth 1 @out t` (from the bach_out_mode fix) with a following `expr`"
    expected: "Plain MAX lists arrive at expr with no 'wrong message or type' console error"
    why_human: "Bach package runtime behavior"
  - test: "Run `/max-iterate --fix` end to end on a scratch copy of a project patch (list, choose, preview, apply, session.diff.render())"
    expected: "Fix applied in one edit_patch session, SaveGateWarning names the rerouted cords, a single path-scoped commit lands, and the saved file reopens in MAX"
    why_human: "Interactive command flow and MAX file load"
  - test: "Decide whether to accept the offered `scale 0. 1.21 0. 1.` fix on slot.maxpat dial obj-54"
    expected: "That blocker is allowlisted as an intentional slight boost, and `t f f` outlet 1 also feeds a flonum display, which would then show the normalized value. The user should choose to skip or accept it."
    why_human: "Design intent"
---

# Quick Task 261022-o2q (Q39) Verification Report

**Goal:** Critic quick-fix payloads and `/max-iterate --fix`.
**Status:** human_needed. Every automated check passes. The remaining items need MAX or a user decision.
**Re-verification:** No, initial verification.

## Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `CriticResult.fix` is keyword-only and defaults to None. `Fix` and `FixOp` are frozen, and the key is unchanged. | VERIFIED | base.py diff adds `"fix"` to `__slots__` and a keyword-only `fix=None`. `fixes.py` holds the frozen dataclasses and the FIX_KINDS/FIX_OPS contract. Existing critic suites pass. |
| 2 | A reconverging fan-out blocker carries an ordered `insert_trigger` fix. Warnings and conflicting orders get none. | VERIFIED | `_fan_out_trigger_fix` uses a cold-before-hot stable topological sort. It returns None for a cycle, a duplicate branch or an unknown outlettype, and is attached only on the blocker path. My probe on a FAN fixture produced `t l l` with inlet 1 on outlet 1 and inlet 0 on outlet 0. The re-review is clean of fan-out, trigger_order and hot_cold findings. |
| 3 | The `gen_param_message_syntax` warning matches validation's condition and carries a `set_text` fix. | VERIFIED | dsp_critic `_GEN_AT_PARAM_RE` and the gen~ cord check mirror validation. `validation.py` is not changed. The parity test and the apply-clears-both test pass. |
| 4 | `unsafe_gain_sources` gets a `scale`/`clip` fix only under the single-cord and ops-safe rules. | VERIFIED | `_gain_fix` requires exactly one path cord, ops that keep [0,1] within [-1,1], and no truncation. A message into line~ gets None. Float-form bounds come from `max_float`. All gain fix and no-fix tests pass. |
| 5 | `bach_out_mode` is a warning with a `set_bach_out` fix. | VERIFIED | `_check_bach_out_mode` implements the exemptions (bang digest, forwarders, Bach consumers) and emits one warning per box. The corpus has 0 findings. Tests pass. |
| 6 | The quickfix API works and fails closed. | VERIFIED | quickfix.py (296 lines) validates all ops before mutating, rolls back on failure, re-reviews by key, and raises FixError when a key is missing. The preview writes nothing. The AST test shows no save function and no `force`. |
| 7 | Applying through `edit_patch` saves through the Q36 session. | VERIFIED | `test_edit_patch_applies_trigger_fix` and `test_edit_patch_missing_key_writes_nothing` pass. |
| 8 | `/max-iterate --fix` is documented. | VERIFIED | max-iterate.md has the argument-hint, the flag scan, the Flags table, and a Quick-fix section covering list, choose, preview, apply in one session, and `session.diff.render()`. The doc-signature tests pass. |
| 9 | Corpus safety. | VERIFIED | I ran fixable_findings over the 63 tracked patches at HEAD. It offers exactly 2 fixes, both in slot.maxpat: `t b b` on obj-1 and `scale 0. 1.21 0. 1.` on obj-54. `test_corpus_fixes_apply_cleanly` passes. |
| 10 | Regression gate. | VERIFIED | The full suite gives 6127 passed, 5 xfailed, 1 xpassed. That is baseline 6064 plus 63 new tests, all from `tests.test_quickfix`. `git stash list` and `git status patches patterns` are empty. No commit touches patches/ or patterns/. |

## Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| New tests | `pytest tests/test_quickfix.py` | 63 passed | PASS |
| Critic, save-gate, validation, doc and integration suites | 15 test files | 1735 passed | PASS |
| Full suite | `pytest -q` | 6127 passed, 5 xfailed, 1 xpassed | PASS |
| Live FAN probe | `apply_quick_fixes` | `t l l` inserted, cold inlet fires first, re-review clean of fan-out findings | PASS |
| Corpus probe | `fixable_findings` over `git ls-files patches/*.maxpat` | 2 fixes, both in slot.maxpat | PASS |

## Anti-Patterns

None found in the changed source. The Known Stubs list is empty. `validation.py` is unmodified. The only file under tests/ that changed is the new `tests/test_quickfix.py`, so no existing test was edited.

## Notes

- A remaining `missing_midpoints` result after the FAN fix is a layout note, not a fan-out or ordering finding.
- The SUMMARY claim that Q23 should skip the bach row is consistent with the code, which implements that row in package_critic.

## Human Verification Required

See the frontmatter list. These are the MAX confirmations from the plan, plus the decision about the slot.maxpat `scale 0. 1.21 0. 1.` fix.

---

_Verified: 2026-10-22_
_Verifier: Claude (gsd-verifier)_
