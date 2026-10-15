---
phase: quick-261015-bt8
plan: 01
subsystem: critics
tags: [structure-critic, trigger, ordering, message-box, save-gate, Q21, R4]
status: complete
requires: [Q20 shared PatchGraph (658432f0)]
provides:
  - "structure_critic: Invalid trigger type / Message $N arity / Trigger order blockers on every non-gen scope"
  - "review_structure(patch_dict, *, graph=None, db=None); review_patch shares its ObjectDatabase"
affects: [save gate (hooks._blocking_findings via review_patch), max-critic revision loop]
tech-stack:
  added: []
  patterns: ["lazy per-call ObjectDatabase handle (_LazyDB)", "one-hop reach map per trigger"]
key-files:
  created:
    - tests/test_ordering_checks.py
  modified:
    - src/maxpat/critics/structure_critic.py
    - src/maxpat/critics/__init__.py
decisions:
  - "Task 2 (user): idiom-exempt -- storage targets (i/int/f/float/zl.reg/zl reg), same-value direct feeds (all hot+cold feeds direct from i/f/l/s outlets) and waveform~ are not reported by the trigger-order check"
  - "Task 2 (user): keep the 2e40f06 probe and pin 'neither form fires'"
  - "$N arity is judged over the whole set of inlet-0 feeders (resend idiom is not flagged)"
  - "review_structure builds its own DB lazily, only when a check needs it (at most one per call)"
metrics:
  duration: "~35 min"
  completed: 2026-10-15
estimate:
  tokens: 120000
  tasks: 3
actuals:
  tokens: 12400
  tasks: 3
  commits: 2
plan_head_before: 658432f0710aa0c9060947b92e3f4eb5bcd4c0a0
plan_head_after: da476d33b76f1bd4f19bd6c9fd0e4f381f8c63b4
---

# Quick 261015-bt8 Plan 01: Q21 ordering and message-shape checks Summary

The structure critic now has three new blocker checks. They run on every non-gen scope and catch these patterns:
- `t a`-style invalid trigger types;
- message `$N` above what its feeders can supply;
- a trigger that fires a box's hot inlet before its cold inlet, directly or through one hop.

Max's previous-value/delta idioms are exempt from the order check (user decision `idiom-exempt`). The 14f2221 and 503f92f pre-fix shapes are caught and their fixed forms pass. There are 0 new findings on the 69 committed patches and on the 3139 Max bundle files.

## Commits

| Task | Commit | Files |
|------|--------|-------|
| 1: trigger-type + $N arity blockers, db plumbing | cb0a97b0 | structure_critic.py, critics/__init__.py, tests/test_ordering_checks.py |
| 2: decision checkpoint (answered by the user: `idiom-exempt`, keep 2e40f06) | n/a | Q/decision.txt |
| 3: trigger-order blocker | da476d33 | structure_critic.py, tests/test_ordering_checks.py |

There are exactly 2 `(Q21)` commits, and neither touches `patches/` (Q/q21-commit-files.txt).

## What was built

- **`_check_trigger_types(scope)`** (planner decision 8). It flags any single lower-case ASCII letter outside b/i/f/l/s in a `trigger`/`t` argument list, scanning up to the first `@`. Each distinct token per box gets one blocker. Upper case, `#`/`$` tokens and multi-character constants are skipped.
- **`_check_dollar_arity(scope, dbh)`** (planner decisions 6 and 7). It applies the regex `(?<!\\)\$([1-9])` to the message text. A box is flagged only when all of these hold:
  - nothing feeds inlet 1;
  - at least one cord feeds inlet 0;
  - every inlet-0 feeder has a known atom count;
  - the largest of those counts is below the highest N.

  Atom counts come from `_outlet_atoms`, which tries these sources in order: the trigger letter, then the DB outlet (non-variable_io), then the box's MAX-saved `outlettype`.
- **`_check_trigger_order(scope, dbh)`** (planner decisions 3, 4 and 5, plus the Task 2 decision).
  - For each trigger it builds a reach map of (target, inlet) → {(outlet, direct|hop)}.
  - One hop counts: a message box, `zl.reg`/`zl reg`, f/float, i/int or prepend, entered at inlet 0 and followed out of outlet 0.
  - A cold inlet is one the DB marks `hot is False`, with the variable_io fallback.
  - These targets are excluded: gate, switch, ggate, gswitch, gswitch2, pak, funnel, and every `_ALL_HOT_NAMES` name.
  - It flags when min(hot outlets) > min(cold outlets), unless the shape is an idiom (`_is_order_idiom`).
- **DB plumbing.** `review_structure(..., db=None)` takes a keyword-only `db`. `review_patch` passes its DB, so there is still at most one DB per call. Called without one, `review_structure` builds it lazily through `_LazyDB` from `src.maxpat.db_lookup` at call time, so test spies still intercept it.
- **Finding and suggestion text** match `<reference_data>` exactly. Each finding carries `obj-N` ids and quoted names, so `hooks._finding_key` can key it.
- **Existing checks are untouched.** `_check_hot_cold_ordering` still warns on hop-fed hot inlets.

## Probe results

| Probe | Pre-fix | Fixed |
|-------|---------|-------|
| 503f92f (`t l f f` → `addchord [ $1 [ $2 $3 $4 ] ]`) | exactly one `Message $N arity:` blocker on obj-107 | no Q21 finding |
| 14f2221 (`t l b` → zl.reg → ears.slice~) | exactly one `Trigger order:` blocker, at top level and nested in `[p slicer]` (path obj-24) | no Q21 finding and no blocker |
| 2e40f06 (`t s b` / `t b s` → groove~) | no finding | no finding |

## Deviations from Plan

### Spec deviation (planned, user-acknowledged): 2e40f06

The spec says "pre-fix caught, fixed passes", but that cannot hold for 2e40f06 (planner decision 2):
- The pre-fix `t s b` already sent the hot `set $1` from outlet 0, which fires last.
- The fix `t b s` inverted R4.
- groove~ inlet 1 (Loop Min) is DB-hot, and v0.0.5 replaced the cord anyway.

The user chose to keep the probe and pin "neither form fires". `TestProbe2e40f06`'s docstring records the evidence.

### Discretion (planner decisions 6-8)

- **6, atom-count precedence.** The order is the trigger letter, then the DB outlet, then the box's saved `outlettype` as a fallback. The fallback is needed because the DB types button/loadbang/metro outlets as plain `control`.
- **7, `$N` multi-feeder rule (assumption delta).** All inlet-0 feeders are judged together. `test_resend_idiom_bang_beside_list_feeder_not_flagged` pins this invariant.
- **8, trigger-type scope.** Only single lower-case letters outside b/i/f/l/s are flagged.

### Minor executor choices

- **Feeder labels in `$N` findings.** The `{feeders}` label is the box **text** when the box has text, otherwise the box name. The `<behavior>` example (`'t l f f' (obj-104) outlet 2`) needs this; `<reference_data>` says `{src_name}`, which would give `'t'`.
- **Lazy DB.** `review_structure` without `db` builds its DB lazily, only when a Q21 check needs a lookup. That is still at most one per call, and it avoids roughly 30 ms per call across the many existing `review_structure(d)` tests.
- **Arguments read up to the first `@`.** `_trigger_letters` and `_check_trigger_types` read trigger arguments only up to the first `@` token.

Otherwise the plan was executed as written. No auto-fixes were needed.

## Bundle triage (Q/bundle-q21.json)

`--bundle` over 3139 files gives `counts={}`: **0 trigger-type, 0 `$N` arity and 0 order findings.** This matches the planning measurement for `idiom-exempt`.

As a cross-check, a scratch run with `_is_order_idiom` forced to False (the literal rule) gave **23** order hits, exactly the planning count. Each one would be a false blocker that `idiom-exempt` exempts on purpose. Verdicts:

| File (bundle-relative) | Shape | Verdict |
|---|---|---|
| extras/Audiotester.maxpat | `t i b` → `i` | idiom (previous value), correctly exempt |
| help/jitter/jit.gl.text.maxhelp `[p matrixoutput > p PULSE]` | `t f f` → `>` | idiom (delta compare), correctly exempt |
| help/jitter/jit.lcd.maxhelp `[p mousing > p mousedrawing]` | `t i b` → `int` | idiom, correctly exempt |
| help/jitter/jit.lcd.maxhelp `[p basic > p mousedrawing]` | `t i b` → `int` | idiom, correctly exempt |
| help/max/cpuclock.maxhelp `[p "uzi test"]` | `t f f` → `-` | idiom (delta), correctly exempt |
| help/max/cpuclock.maxhelp `[p "scheduling test"]` | `t f f` → `-` | idiom (delta), correctly exempt |
| help/max/multislider.maxhelp `[p basic > p EKG]` obj-6 | `t f b` → `f` | idiom, correctly exempt |
| help/max/multislider.maxhelp `[p basic > p EKG]` obj-14 | `t f b` → `f` | idiom, correctly exempt |
| help/max/nodes.maxhelp `[p fun > p directionFromMouse]` obj-36 | `t f f` → `-` | idiom (delta), correctly exempt |
| help/max/nodes.maxhelp `[p fun > p directionFromMouse]` obj-33 | `t f f` → `-` | idiom (delta), correctly exempt |
| help/max/trigger.maxhelp `[p examples]` | `t f f` → `- 0.` | Cycling '74's own delta example, correctly exempt |
| BEAP Phase Vocoder Example `[bpatcher]` | `t b l` → `waveform~` | waveform~ UI idiom, correctly exempt |
| BEAP Spectral Image Filter example `[... p log2lin-freq]` | `t i i b` → `-` | idiom (same-value direct), correctly exempt |
| BEAP bp.Noise.maxhelp `[... p log2lin-freq]` | `t i i b` → `-` | same, correctly exempt |
| BEAP bp.Spectral Filter.maxhelp | `t i i b` → `-` | same, correctly exempt |
| BEAP bp.Spectral Image Filter.maxhelp | `t i i b` → `-` | same, correctly exempt |
| BEAP clippings bp.Spectral Filter.maxpat | `t i i b` → `-` | same, correctly exempt |
| BEAP clippings bp.Spectral Image Filter.maxpat | `t i i b` → `-` | same, correctly exempt |
| BEAP clippings bp.Classroom Samplr.maxpat | `t f b` → `waveform~` | waveform~ idiom, correctly exempt |
| Jitter Tools tf.sculpt.maxpat `[p generate_gestures]` | `t l l b` → `vexpr` | idiom (same-value direct), correctly exempt |
| RNBO rnbo_trigger.maxhelp `[rnbo~]` | `t f f` → `-` | delta idiom, correctly exempt |
| Vizzie vz.scribblr.maxpat `[p mouse-drawing]` | `t i b b` → `int` | storage idiom, correctly exempt |
| max-mxj fibonacci.maxhelp `[p maxonacci]` | `t b b` → `int` (one hop via `int`) | storage idiom, correctly exempt |

## Committed-patch triage

- `Q/triage.py --check` reports `files=69 mismatch=0 q21=0`, both after Task 1 (triage-t1.json) and after Task 3 (triage-final.json).
- `--selftest` passes 5/5, and Step 0 self-check exited 0 (Q/triage-step0.txt).
- There are no allowlist changes, and no file under `patches/` changed.

## Test results

- Baseline at 658432f0: 3909 passed, 1 xfailed, 1 xpassed (Q/baseline-pytest.txt).
- Final: **3982 passed, 1 xfailed, 1 xpassed** (Q/final-pytest.txt). That is +73 new tests in `tests/test_ordering_checks.py`. `test_calibration_zero_blockers` and the requires_max bundle sweep are green.
- Red runs: Q/red-t1.txt (32 failed), Q/red-t3.txt (15 failed).
- I also forced `_is_order_idiom` to False as a check: all 7 idiom tests then fail. So the idiom tests really exercise the exemption.
- Every changed .py file parses as Python 3.10.

## Follow-ups (not done, out of scope)

- **DB hot-flag defect, an `overrides.json` follow-up.** `pak` and `funnel` are all-hot in Max, but the DB marks inlet 1 `hot: false`. The trigger-order check excludes both by name. Other DB consumers still see the wrong flag.
- **`gswitch2` is not in the object DB.** It is excluded by name only.
- **RNBO trigger lacks `s`** (rnbo_trigger.maxref.xml). Inside an rnbo~ scope, `t s` is not flagged by the trigger-type check. This is out of scope.

## Doc impact (no docs edited)

- The max-critic `SKILL.md` has no structure-critic severity table, so there is nothing to update there. If one is added later, the three Q21 blockers belong in it.
- The `severity-contract.md` blocker semantics now cover the three new structure-critic blockers.
- The proven-forms.md "trigger types" rule (no `t a`) is now enforced by the critic.
- CLAUDE.md Rule #3 (hot/cold ordering) is now enforced for same-trigger feeds, with the idiom exemption. The rule text could mention that previous-value/delta idioms are intentional.

## MAX confirmation

There is nothing to confirm in MAX. The checks are static, and their semantics come from the refpages (trigger.maxref.xml, message.maxref.xml, groove~.maxref.xml).

## Known Stubs

None.

## Threat Flags

None. The change adds no new surface: it is read-only critic code. The junk-robustness tests and the purity test cover T-bt8-01 and T-bt8-05.

## Self-Check: PASSED

- FOUND: src/maxpat/critics/structure_critic.py, src/maxpat/critics/__init__.py, tests/test_ordering_checks.py
- FOUND: commits cb0a97b0 and da476d33 (`git log` shows both `(Q21)` commits from base 658432f0)
- FOUND: Q/decision.txt (`idiom-exempt`), Q/bundle-q21.json, Q/triage-final.json, Q/final-pytest.txt
- The stash list is unchanged (empty before and after).
