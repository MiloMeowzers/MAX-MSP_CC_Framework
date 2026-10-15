---
phase: quick-261014-t1y
verified: 2026-10-14T00:00:00Z
status: passed
score: 9/9 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Quick 261014-t1y (Q19): Shared walker and recursive validation: Verification Report

**Goal:** Implement Q19: shared walker (`walk.py`) and recursive validation (A7, S1, S2, G8 part).
**Status:** passed
**Re-verification:** No, initial verification

## Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | walk.py `iter_patchers`: pre-order, explicit stack, tuple path, contexts, no external load, no raise, deep and cyclic safe, quote-aware helpers | VERIFIED | 280-line `src/maxpat/walk.py`. Probe: 1500-deep nest yields 1501 scopes, a self-cyclic dict yields 1, `box_tokens('foo "a b" c')` gives `['foo','"a b"','c']`, None text gives `''`. 55 tests in test_walk.py pass. |
| 2 | Layers 1-5 per scope, `path` set, `[label] ` prefix, top-level byte-identical | VERIFIED | Probe: nested findings carry `path='obj-1'` and prefix `[p synth] `. I re-ran `triage.py --check` against the base results: `top_mismatch=0 nested_bad=0` on 69 files, nested=142, newly_covered_top=1. This matches the SUMMARY. |
| 3 | `osc~` in `p` is an error with path and prefix; nested out-of-range cord is a 4-tuple proposal; `apply_fixes` removes it only in that scope and returns a 5-tuple | VERIFIED | Probe A: `error 'obj-1' [p synth] 'osc~' is a Pure Data object`. Probe B: `proposed_removal=('obj-1',5,'obj-2',0)`; `apply_fixes` returned `[('obj-1','obj-1',5,'obj-2',0)]` and the inner lines list was empty. Patcher-input, mc.gen~ and gate-refusal tests exist (`TestSaveGateNested`, mc.gen~ tests at lines 259-275, 495) and pass. |
| 4 | Scope rules: gen skips Layer 4; floor~ in gen~ is an error at path `gen-1`; nested rnbo~ warns and skips type checks | VERIFIED | Tests `test_gen_scope_skips_layer4`, `test_top_level_gen_skips_layer4`, `test_type_checks_skipped_in_rnbo`, `test_bounds_still_checked_in_rnbo` pass. The inverted D-07 test is in test_validation.py. |
| 5 | Layer 5 checks codeboxes in every gen container, once each, at the holder's scope; top-level .gendsp unchecked | VERIFIED | Probe C: `delay()` in p -> gen~ gives one error with path `obj-1` and prefix `[p x]`. mc.gen~ codebox test (line 495) passes. |
| 6 | Save-gate `_finding_key` includes path | VERIFIED | hooks.py `_finding_key` docstring and tuple include path. `test_path_distinguishes_keys` and `TestNestedGateKey::test_moved_nested_blocker_is_new` pass. |
| 7 | Never raises on empty, None or non-str text, or malformed entries, or on the Max bundle; duplicate ids are a Layer-1 error and nested scopes are pruned | VERIFIED | Probe D: no errors and no crash on `''`, None, `'  '` and int text. Probe E: top-level `Duplicate box id 'obj-1' (2 boxes)`. Probe F: nested duplicate gives the same error with path `obj-1` and prefix `[p a]`. `test_bundle_sweep_never_raises` ran and passed on this Mac. |
| 8 | One name extractor | VERIFIED | `grep` finds no `_get_box_name`, `_extract_object_name` or `_STRUCTURAL_MAXCLASSES` in `src/maxpat`. The only `.split()` in validation.py, rnbo_validation.py and walk.py is a docstring mention. |
| 9 | No `patches/` change; suite green; Python 3.10 parse | VERIFIED | `git diff --name-only f1d4ee37..HEAD` shows no `patches/` entries. Full suite: 3813 passed, 1 xfailed, 1 xpassed (matches SUMMARY; base was 3677 plus 136 new tests). `ast.parse(feature_version=(3,10))` passes for walk, validation, hooks and rnbo_validation. Exactly 3 commits: 97d715a2, e6bef1ee, 7eaa71fa. Stash list is empty. |

## Required Artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| `src/maxpat/walk.py` | VERIFIED | Substantive and wired. validation.py and rnbo_validation.py import it. |
| `src/maxpat/validation.py` | VERIFIED | Per-scope recursion, `ValidationResult.path`, path-aware `apply_fixes`. |
| `src/maxpat/hooks.py` | VERIFIED | Path in `_finding_key`. |
| `src/maxpat/rnbo_validation.py` | VERIFIED | Uses walk helpers. |
| `tests/test_walk.py`, `tests/test_validation_recursive.py`, `tests/test_save_gate.py` | VERIFIED | 348 tests pass across the four touched test files. |

## Anti-Patterns

None blocking. SUMMARY discloses known unhandled edge cases (non-hashable box `id`, non-list patchline `source` reaching Layer 4). These are outside the plan's never-raise list.

## Human Verification

None required. The work is validator-only and no patch changed.

## Notes (non-blocking)

- Doc follow-ups the SUMMARY lists as out of scope (severity-contract.md, TECHNICAL.md) still describe top-level-only validation.
- Q20 consumers still use their own walkers, as scoped.

---
_Verified: 2026-10-14_
_Verifier: Claude (gsd-verifier)_
