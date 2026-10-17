---
phase: quick-261016-tal
verified: 2026-10-16T00:00:00Z
status: passed
score: 7/7 must-haves verified (UI-control-set item is a deliberate, documented PARTIAL)
behavior_unverified: 0
covered_files:
  - src/maxpat/builders.py
  - src/maxpat/critics/base.py
  - src/maxpat/critics/dsp_critic.py
  - src/maxpat/critics/layout_critic.py
  - src/maxpat/externals.py
  - src/maxpat/gain_staging.py
  - src/maxpat/layout.py
  - src/maxpat/maxclass_map.py
  - src/maxpat/patcher.py
  - src/maxpat/rnbo.py
  - src/maxpat/sizing.py
  - src/maxpat/validation.py
  - tests/test_consolidation.py
  - tests/test_integration_patches.py
covered_digest: "v2:sha256:07a098962873c095bab24118baca093415018f6354535dd45b6627864b316a69"
---

# Quick 261016-tal (Q33) Verification Report

**Goal:** Box factory and shared helpers refactor: pure refactor, no behaviour change, suite green.
**Status:** passed
**Re-verification:** No

## Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Structural boxes come from `Box.structural`; no `Box.__new__` in builders / rnbo / externals | VERIFIED | `grep Box.__new__ src` finds only `patcher.py:1975` (docstring) and `patcher.py:2058` (the `from_dict` loader, explicitly out of scope per PD-2). `Box.structural` is defined at `patcher.py:387` and sets the full `Box.__init__` attribute set. `tests/test_consolidation.py` carries the AST guard and it passes. |
| 2 | Builder battery and laid-out output byte-identical to base | VERIFIED | I re-ran `q33_gate.py snapshot` from the working tree. `cmp` against `behaviour-before.json` is identical (11 builder cases, 75 corpus files, 61 laid out, 214 validate rows, 1769 review results). |
| 3 | One gain-staging implementation shared by validation and DSP critic | VERIFIED | `src/maxpat/gain_staging.py` exists. `validation.py:1615` and `dsp_critic.py:305` both call `gain_staging.find_ungained_paths`. Neither module defines its own oscillator set (greps find only docstring and comment mentions). The snapshot covers validate and review output over the whole corpus. |
| 4 | One port-geometry helper; no `_resolve_patcher_bg` wrappers | VERIFIED | `sizing.outlet_x` / `inlet_x` are defined once (`sizing.py:286,295`). `layout.py` and `layout_critic.py` import them as `_outlet_x` / `_inlet_x`, and no `def _outlet_x`, `def _inlet_x` or `def _resolve_patcher_bg` remains in src. The only mention of `_resolve_patcher_bg` is the guard in `test_consolidation.py`. Forced layout is covered by the snapshot's `layout` hashes (identical). |
| 5 | UI-control set: `ui_control_names(db)` added; purpose sets co-located and pinned | PARTIAL (accepted) | `maxclass_map.ui_control_names` (line 134) and the three sets (lines 160, 173, 183) exist. `layout.py`, `layout_critic.py` and `analysis.py` import their sets from `maxclass_map`. `ui_control_names` has no src consumer, so this is not a unification. SUMMARY marks the item PARTIAL with measured impact numbers and puts PD-6 first under "Decisions to confirm". The task brief says this is expected. |
| 6 | `CriticResult` has `rule` / `box_ids` / `port`; tests and allowlist key on them, with no finding-text regex | VERIFIED | `critics/base.py` defines `rule`, `box_ids`, `port` (keyword-only, in `__slots__`). An AST scan of `src/maxpat` finds 49 `CriticResult(` calls and 0 without `rule=`. `test_integration_patches._result_key` and `_allow_key` build `(rule, box_ids, port, path)` tuples. The allowlist JSON entries have `rule`, `box_ids`, `port` and `path`. `test_uninitialized_state.py` uses `r.rule` and `r.box_ids`, and `_ID_RE` is gone. The remaining `_CONST_ASSIGN_RE` in test_integration_patches belongs to the separate `ValidationResult` genexpr allowlist, which is out of scope (PD-11). `_FANOUT_RE` now lives only in `test_critic_precision.py` (coordinator option C). `q33_gate.py allowlist` re-run: 1721 results, 2 blockers, 2 exempted, 0 mismatches. |
| 7 | No test regressions; scope respected | VERIFIED | Full suite: `2 failed, 5318 passed, 5 xfailed, 1 xpassed` (110 s). The 2 failures are the known q29-check baseline ones (`test_readme_patch_table_lists_every_project` and `test_committed_q24_findings_match_allowlist[q29-check.maxpat]`). Per SUMMARY, the baseline was 5295 passed and the 23 added tests are all in `test_consolidation`. The imports gate reports no new unused import. `git diff 7a80ff86..HEAD` touches 25 files, all under `src/maxpat` or `tests`, with 0 changes under `patches/`. The stash list is empty. |

**Score:** 7/7 truths verified, with truth 5 accepted as the documented PARTIAL.

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Targeted tests | `pytest tests/test_consolidation.py tests/test_integration_patches.py tests/test_critic_precision.py tests/test_uninitialized_state.py` | 395 passed, 1 failed (the q29-check baseline case) | PASS |
| Behaviour snapshot vs Step 0 | `q33_gate.py snapshot` then `cmp` | identical | PASS |
| Allowlist structured vs legacy-regex equivalence | `q33_gate.py allowlist` | 0 mismatches | PASS |
| Unused-import gate | `q33_gate.py imports --baseline` | exit 0 | PASS |
| Full suite | `pytest -q` | only the 2 baseline failures | PASS |

## Anti-Patterns

No debt markers were introduced that need action. No stubs: the new modules are substantive and wired.

## Notes (informational, not gaps)

- PD-6 (UI-control-set unification) is the one open user decision. It is correctly deferred, since (b) and (c) would change behaviour.
- The gate snapshot pins `PYTHONHASHSEED=0`. Layout and `analyze()` output are hash-seed nondeterministic in the base too, and SUMMARY records this as a follow-up.
- Doc impact (`max-dsp-agent` SKILL mention of `Box.__new__`, severity-contract fields) is listed in SUMMARY and not applied, which is correct under the plan's rule 8.
- No MAX or Live confirmation is needed, because serialized output is byte-identical.

_Verified: 2026-10-16_
_Verifier: Claude (gsd-verifier)_
