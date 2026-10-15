---
phase: quick-261015-bt8
verified: 2026-10-15T00:00:00Z
status: passed
score: 8/8 must-haves verified
covered_files:
  - .planning/quick/261015-bt8-implement-q21-in-planning-reviews-2026-1/261015-bt8-PLAN.md
  - .planning/quick/261015-bt8-implement-q21-in-planning-reviews-2026-1/261015-bt8-SUMMARY.md
  - src/maxpat/critics/__init__.py
  - src/maxpat/critics/structure_critic.py
  - tests/test_ordering_checks.py
covered_digest: "v2:sha256:d154cfb176cc5d78591f8b9aa783e93edda7d28398cda27dc625d5f4b7e78dae"
behavior_unverified: 0
overrides_applied: 1
overrides:
  - must_have: "2e40f06 probe: pre-fix caught, fixed passes (fix-plan Q21 spec)"
    reason: "Spec cannot hold for this probe (planner decision 2): pre-fix t s b already obeys R4, the fix t b s inverts it, and groove~ inlet 1 (Loop Min) is DB-hot. Probe pinned as 'neither form fires'."
    accepted_by: "user (Task 2 reply: idiom-exempt, keep 2e40f06)"
    accepted_at: "2026-10-15"
re_verification: false
---

# Quick 261015-bt8 (Q21): Verification Report

**Goal:** Implement Q21 from the fix plan: trigger type, `$N` arity and trigger order checks in `structure_critic`.
**Status:** passed
**Re-verification:** No, initial verification.

I did not trust SUMMARY.md. I read the merged code, rebuilt the probe shapes from `<reference_data>` in my own scratch script, and ran the tests myself. I changed no source and no patches.

## Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Trigger-type blocker: exact text for `t a`, nested path prefix, no finding for b/i/f/l/s, numbers, multi-character symbols, `#N`, upper case or bare `t`. The save gate refuses `t a`. | VERIFIED | My probe: `t a`, `trigger a b`, `t a a` (one finding) and `t p` all flag, with text identical to the spec: `Invalid trigger type: 't a' (obj-1) argument 'a' is not a trigger type (b, i, f, l, s) -- it outputs the literal symbol 'a'`. `t b i f l s`, `t 0 1. set foo`, `t #1 b`, `t`, `t B` and `t b @x a` give nothing. `test_save_gate_refuses_t_a` asserts `PatchValidationError` and that the file does not exist; it passes. |
| 2 | 503f92f pre-fix gives exactly one `Message $N arity:` blocker on obj-107. The fixed form gives none. The set-of-feeders rule (bang plus list is the resend idiom) holds. | VERIFIED | Probe output: `Message $N arity: 'addchord [ $1 [ $2 $3 $4 ] ]' (obj-107) uses $4 but its feeders supply at most 1 atom(s): 't l f f' (obj-124) outlet 2 -- $ arguments above 1 keep their stored value (0 until set)`. The fixed form is clean. `t b`→`$1` and `t f`→`$1 $2` flag. `t f`→`$1`, `t l`→`$1 $2 $3` and `\$1` do not. Argument-less `t`→`$1 $2` flags. A button beside `t l` into `$1 $2` gives nothing. The code (`_check_dollar_arity`) judges the whole set of inlet-0 feeders and skips when inlet 1 is fed. |
| 3 | 14f2221 pre-fix gives exactly one `Trigger order:` blocker, at top level and nested in `p slicer` (path `obj-24`). The fixed form is clean. One hop counts and two hops do not. Excluded targets are never checked. | VERIFIED | Probe: top level has one blocker with the exact spec text. Nested shows `[p slicer] Trigger order: ...` with path `obj-24`. The fixed form gives nothing, both ways. `t l b` → `zl.reg` → `pack 0 0` flags; with two `zl.reg` hops it does not. `gate` is skipped. The code has `_ORDER_EXCLUDED_NAMES` (gate, switch, ggate, gswitch, gswitch2, pak, funnel, `_ALL_HOT_NAMES`) and `_inlet_is_cold`, which reads DB `hot is False` and has the variable_io fallback. A control `t l b` into `pack 0 0` and `t b b` into `pack` via hops both flag. |
| 4 | 2e40f06 shapes (`t s b` pre-fix, `t b s` fixed): no Q21 finding in either form. The test docstring documents the spec deviation. | VERIFIED (override) | My probe shows `[]` for both forms. `TestProbe2e40f06` exists (tests lines 576-623), and its docstring cites planner decision 2. The deviation is user-approved and recorded in the frontmatter `overrides`. |
| 5 | The previous-value idiom follows `idiom-exempt`. Exempt: `t f f`→`- 0.`, `t i b`→`i`, `t f b`→`f 0.`, `t f f`→`> 0.`, `t l l b`→`vexpr $f1-$f2`, fibonacci `t b b`→`int` via a hop, and `t b l`→`waveform~`. The hop-fed 14f2221 shape still blocks. | VERIFIED | All seven idiom shapes return `[]` in my probe, and 14f2221 still blocks. `_DECISION = "idiom-exempt"` is in the tests. `decision.txt` contains `idiom-exempt`. `_is_order_idiom` covers storage targets, waveform~ and same-value direct feeds. `TestPreviousValueIdiom` exists, and the executor reports 7 tests that fail when the exemption is disabled. |
| 6 | `review_patch` passes its single DB to `review_structure`. Without `db`, `review_structure` builds its own. The checks are read-only. | VERIFIED | `critics/__init__.py` now has `review_structure(patch_dict, graph=graph, db=db)`. In my spy run, `review_patch` made 1 DB build and `review_structure(d, db=…)` made 0. A deep-copy compare after `review_patch` on a patch holding all three shapes plus `t a` gave `pure True`. A junk patch (None, list and int text, a missing source id, a non-int outlet) raises nothing. |
| 7 | Triage, calibration and the full suite are clean. No file under `patches/` changes. Exactly 2 `(Q21)` commits. Python 3.10 parse. | VERIFIED | `triage.py --selftest` passes 5/5. `--check` gives `files=69 mismatch=0 q21=0` (run fresh by me). `git diff 658432f0 HEAD` touches exactly 3 files: structure_critic.py, critics/__init__.py and test_ordering_checks.py, with none under `patches/`. `git log --grep="(Q21)"` shows exactly cb0a97b0 and da476d33. The stash list is empty. `ast.parse(feature_version=(3,10))` passes on all three files. The full suite ran by me: **3982 passed, 1 xfailed, 1 xpassed** (baseline 3909 plus 73 new tests). The targeted run was 527 passed, including `test_calibration_zero_blockers`. |
| 8 | Bundle report: Q/bundle-q21.json lists the findings over 3139 files. SUMMARY lists each hit with a verdict. The expected counts under `idiom-exempt` are 0/0/0. | VERIFIED | `bundle-q21.json` has `files: 3139`, `counts: {}` and `hits: []`, which matches the planning measurement for `idiom-exempt`. SUMMARY lists the 23 literal-rule hits that the exemption covers, each with a verdict. I did not re-run the bundle sweep, but the requires_max sweep in the full suite was green. |

**Score:** 8/8 truths verified (one with a user-approved override). 0 behavior-unverified.

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/maxpat/critics/structure_critic.py` | `_check_trigger_types`, `_check_dollar_arity`, `_check_trigger_order`, `db` kwarg | VERIFIED | All three exist (862 lines). They are called in the non-gen branch, and gen scopes run only the duplicate-patchline check. |
| `src/maxpat/critics/__init__.py` | `review_patch` passes its DB | VERIFIED | The pattern `review_structure(patch_dict, graph=graph, db=db)` is present. |
| `tests/test_ordering_checks.py` | Probe, idiom, save-gate, one-DB, purity and junk tests | VERIFIED | 713 lines, with the classes TestTriggerTypes, TestDollarArity, TestProbe503f92f, TestAtomChecksEndToEnd, TestTriggerOrder, TestProbe14f2221, TestProbe2e40f06, TestPreviousValueIdiom and TestPurity. |

## Key Links

| From | To | Status |
|------|----|--------|
| `critics/__init__.py` | `structure_critic.review_structure` | WIRED (db passed; one build proven by spy) |
| `structure_critic` | `db_lookup` (`_LazyDB.lookup`, `hot` flags, outlet types) | WIRED (cold-inlet and atom-count decisions use the DB; imported inside the function so test spies intercept it) |
| `hooks` save gate | `review_patch` | WIRED (the `t a` refusal test passes) |

## Data-Flow, Anti-Patterns and Requirements

- Data flow: not applicable, because this is an in-process static critic. The checks consume real Scope edges and DB records, and I confirmed that with my own probes.
- Anti-patterns: I scanned the added source. It has no TBD, FIXME or XXX markers and no stubs. Every lookup path is guarded.
- Requirement R4 (review §4.4) is satisfied by truths 1-5.

## Findings

No blockers.

Informational, all disclosed in SUMMARY:
- The idiom-exempt rule means a real inversion into a storage object, or one that feeds the same value to both inlets, is not reported. The user accepted this trade-off.
- `pak` and `funnel` are excluded by name because their DB `hot` flags are wrong. That is an `overrides.json` follow-up.
- RNBO's trigger lacks `s`. That is out of scope.
- The feeder label in `$N` findings uses the box text (`'t l f f'`) rather than the bare name. This matches the plan's `<behavior>` example.

## Human Verification

None. The checks are static, with semantics taken from the refpages. There is nothing to confirm in MAX.

---

_Verified: 2026-10-15_
_Verifier: Claude (gsd-verifier)_
