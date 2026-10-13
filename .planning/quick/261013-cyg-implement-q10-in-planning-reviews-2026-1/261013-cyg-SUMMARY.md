---
phase: quick-261013-cyg
plan: 01
subsystem: object-db / io-counts
status: complete
tags: [Q10, C1, S6, variable-io, help-io-oracle]
requires: [Q9 help-io oracle (917fd14)]
provides: [src/maxpat/io_resolvers.py, quote-aware tokenizer, IO_RESOLVERS, corrected variable_io_rules]
affects: [compute_io_counts, get_outlet_types, Patcher.add_box, Patcher.modify_box, tools/help_io.py, audit parser/analyzer]
tech-stack:
  added: []
  patterns: [per-object resolver callables keyed by canonical name; resolver/rule conflict check at load; derived in-memory variable_io flag]
key-files:
  created: [src/maxpat/io_resolvers.py, tests/test_io_resolvers.py]
  modified: [src/maxpat/db_lookup.py, tools/help_io.py, .claude/max-objects/overrides.json, tests/test_db_lookup.py, tests/test_patcher.py, tests/fixtures/help_io_baseline.json]
decisions:
  - "Non-formula I/O rules are Python resolvers in src/maxpat/io_resolvers.py; SUPPORTED_IO_FORMULAS unchanged; an object may not have both a resolver and a variable_io_rules entry (ValueError at load)"
  - "Every object with a resolver or a variable_io_rules entry reports variable_io True in memory (assumption delta: promote); domain JSON untouched"
  - "compute_io_counts re-tokenizes args (quotes, backslash escapes) and truncates at the first @attribute token"
metrics:
  duration: ~11 min
  completed: 2026-10-13
actuals:
  tokens: 25700
  tasks: 3
  commits: 3
plan_head_before: 5587b1c36bc41dc541b5ff70e2576772df63dd10
plan_head_after: f5ddcecef77f0d4d9cffd55db67971e05035b53f
---

# Phase quick-261013-cyg Plan 01: Q10 Variable-I/O Counts Summary

compute_io_counts now matches MAX-saved help boxes for every object Q10 names. This comes from three changes: a quote-aware tokenizer that stops at `@attributes`, 11 per-object resolver callables (S6), and 17 corrected or added `variable_io_rules`. The help-io baseline shrinks from 441 to 414 mismatching names and from 13,084 to 9,601 boxes.

## Commits

| Task | Commit | Message |
|---|---|---|
| 1 (tracer) | aa81809 | feat(io): quote-aware box tokenizer and per-object I/O resolvers; r/receive with a name has 0 inlets (Q10) |
| 2 | b3dc9ba | feat(io): resolvers for select/route/routepass (N+1 inlets), expr/vexpr/if ($-index, out2), sprintf, pipe, notein, ctlin; retire their formula rules (Q10) |
| 3 | f5ddcec | fix(db): variable_io_rules match MAX-saved help boxes ... help-io baseline shrinks (Q10) |

Worktree base: `5587b1c`, which contains `917fd14` (Q9). The precondition held.

## Test and oracle figures

**pytest (Python 3.14, full suite)**

| Point | Result |
|---|---|
| Base (Step 0) | 2727 passed, 1 xfailed, 1 xpassed, 29 warnings |
| After Task 1 | 2758 passed, 1 xfailed, 1 xpassed, 29 warnings |
| After Task 2 | 2802 passed, 1 xfailed, 1 xpassed, 29 warnings |
| After Task 3 (final) | **2843 passed, 1 xfailed, 1 xpassed, 29 warnings** |

- `git status --porcelain` was unchanged across every full run, so tests never wrote to the repo.
- Red counts before each GREEN step:
  - Task 1: 9 failed / 22 passed, with the new test file run against base `db_lookup.py` and `help_io.py`.
  - Task 2: 38 failed.
  - Task 3: 38 failed.
- Warnings were 29 before and 29 after.
- **Python 3.10.19** (uv venv in the scratchpad, `requirements-dev.txt`, `MAXPAT_TEST_MAX_APP=/nonexistent/Max.app`): test_io_resolvers, test_db_lookup, test_help_io and test_patcher gave **405 passed, 3 skipped** (the skips are requires_max).
- Every changed `.py` passes `ast.parse(feature_version=(3, 10))`.

**Help-io oracle (`tools/audit_db.py --help-io`)**

| Source | Names before -> after | Boxes before -> after |
|---|---|---|
| bundle (9.2.0) | 164 -> 137 | 6867 -> 4963 |
| CNMAT Externals | 61 -> 52 | 524 -> 454 |
| FlowSwing | 18 -> 10 | 101 -> 81 |
| FluidCorpusManipulation | 67 -> 56 | 1391 -> 984 |
| RNBO | 13 -> 8 | 110 -> 36 |
| Rhythm and Time Toolkit | 15 -> 12 | 236 -> 217 |
| abclib | 15 -> 8 | 452 -> 241 |
| bach | 73 -> 65 | 1694 -> 1142 |
| cv.jit | 14 -> 4 | 178 -> 113 |
| dada | 39 -> 33 | 278 -> 257 |
| ears | 110 -> 105 | 722 -> 709 |
| ease | 6 -> 3 | 24 -> 17 |
| grainflow | 35 -> 26 | 292 -> 229 |
| ml.star | 11 -> 6 | 138 -> 92 |
| nn_tilde | 11 -> 8 | 77 -> 66 |
| **Total** | **441 -> 414** (count names 363 -> 335) | **13,084 -> 9,601** |

These figures match the planning prototype exactly.

**Fully fixed (source, name) pairs: 119.** In the bundle, 27 names went to zero mismatches: b, bucket, buddy, combine, ctlin, expr, gate~, groove~, if, jit.pack, jit.unpack, notein, pack, pak, pipe, r, receive, route, routepass, sel, select, sprintf, switch, t, unjoin, unpack, vexpr. The other 92 pairs are in the 14 package sources. After the change, no Q10 target has a count mismatch in any source.

**Baseline diffs against the Q9 baseline (`diff_baselines`)**
- Task 1: 15 improvements and 0 regressions.
- Task 3 (final): **120 improvements.**
- The **only regression** is `bundle/mc.route type_mismatches 0 -> 11`, and it is allowed under the plan's rule: Q10 target, count_mismatches now 0.
  - Cause: overrides.json `objects["mc.route"].outlets[*].signal_role = "audio"` on outlets MAX saves as control (int).
  - The count error used to hide it. Now that `mc.route 4` = (2,4) is right, the type comparison runs and exposes it.
  - **Hand off to Q11 (C9).** Not fixed here.

TestOracleTargets (requires_max) passes on this Mac with all 35 Q10_TARGETS. Advisory 1: `t` passed in Task 1, so it stayed in Task 1's targets.

## Behavior changes for the regression-averse user

- **Derived `variable_io` flag.** These 16 objects are now `variable_io` in memory: receive, if, sprintf, pipe, notein, ctlin, gate~, bucket, buddy, bangbang, groove~, tapout~, record~, jit.pack, jit.unpack, mc.route.
  - `Patcher.modify_box(args=...)` on them now recomputes I/O and orphans only out-of-range cords. Before, their I/O was kept as content-defined.
  - A test pins this: a loaded `gate~ 3` edited to `[2]` keeps outlets 0 and 1 and orphans exactly the outlet-2 cord.
  - `pan` and `pan~` also flip to True. This has no numeric effect, because their rules are `fixed:2`.
- **Args after `@` no longer count toward I/O** in `compute_io_counts`. For example, `combine sound 74 @triggers 1` has 2 inlets, not 4.
- **Quoted words are one argument** whether the caller passes them pre-split or joined. compute_io_counts re-tokenizes the args.
- **`audit_empty_io()["variable_io_ok"]`** drops select, route, routepass, expr and vexpr (now resolvers). It gains the 10 new rule names.
- **The audit parser and analyzer** (`audit/parser.py:176`, `audit/analyzer.py:244`) treat the newly variable objects as variable.
- **New boxes get MAX's counts:**
  - `sel 0` = (2,2) and `route a b` = (3,3);
  - bare `unpack` = (1,2), bare `pack` = (2,1), bare `t` = (1,2);
  - `r foo` = (0,1);
  - `expr $i1 + $i2 + $i3` = (3,1);
  - `t "a b"` = (1,1).
  Cords to the new route/select inlets (which set the match values) are now possible, and cords to ports that don't exist are now blocked.
- **The six rewritten tests** each now cite the MAX evidence:
  - `test_compute_io_counts_route_no_args_post_fn03` was renamed `..._matches_refpage`; (1,1) -> (2,2), from the route refpage.
  - `test_compute_io_counts_routepass_uses_loaded_formula` was renamed `..._routepass_resolver`; (1,3)/(1,4) -> (3,3)/(4,4), from `routepass 0 1` in jit.displays.maxhelp. It also asserts routepass is a resolver with no rule.
  - `test_compute_io_counts_routepass_normalized_default_outlets`: (1,3) -> (3,3), plus bare (2,2).
  - `TestVariableIO.test_route_two_args`: numinlets 1 -> 3 (`route time transport` = (3,3), jit.avc.maxhelp).
  - `test_compute_io_counts_honors_overrides_rules_for_lifted_objects`: combine (3,1) -> (3,2) and bare (0,1) -> (1,2), from combine.maxhelp and dada.machines.maxhelp. The cycle and router assertions are unchanged.
  - `test_compute_io_counts_trigger_no_args_post_fn03` was renamed `..._matches_refpage`; (1,0) -> (1,2), from the trigger refpage.
  - MAX evidence overturns FN-03 of REVIEW 260420-j15 for combine, trigger and route.

## Triage result

`validate_patch` (on a deepcopy) and `review_patch` ran over all 57 committed `patches/**/*.maxpat|*.maxhelp` files, giving 1417 findings at base and after each task. The result was **identical at base, after Task 1, after Task 2 and after Task 3**. No patch file changed, and nothing needed an allowlist.

## Deviations from Plan

- **Plan said:** compare base-sha files through `git show` inside the Python one-liners.
- **What happened:** The worktree sandbox refused those (it can't verify git calls made from a subprocess stay inside the worktree).
- **Workaround:** Base-sha copies of `help_io_baseline.json` and `overrides.json` were extracted with plain `git show` into the session scratchpad. An equivalent gate script (`scratchpad/gate.py`) applied the same assertions: Py3.10 syntax, overrides format/non-rule/changed-key guard, baseline regression allow-rule, triage equality.
- **Effect:** none on the outcome. Tooling only, nothing committed.

The rest of the plan executed as written.

## Residuals and follow-ups (not fixed, rule 7)

- **Arg-dependent bundle names still mismatching** (live run, bundle, names with more than one MAX count signature):
  - the 19 from planning: mxj (201 boxes), dict.pack (47), print (16), dict.unpack (14), jit.gl.multiple (13), mtr (8), matrix (6), mc.transpose~ (4), mcs.sig~ (4), array.routepass (3), jit.cycle (3), mc.separate~ (3), string.sprintf (3), grab (2), jit.catch~ (2), jit.gl.textmult (2), mpeformat (2), polyin (2), string.withpass (2);
  - also live.gain~ (162), plot~ (35), gen (8) and jit.avc (5), which vary by help-box shape, not clearly by args.
- **expr~** still uses `arg_count` (RNBO-only, Q12).
- **Inlet/outlet layouts are not modelled** for resolver objects or `record~ buf N` (S6/Q33).
  - `record~ buf 2` inlet 1 is the channel-2 signal, but DB index 1 is the start point.
  - ctlin/notein outlet digests are plain-indexed.
- **`Patcher.from_dict`** still splits `box.args` on whitespace. This doesn't affect counts, because compute_io_counts re-tokenizes.
- **mc.route outlet signal roles** are listed above (Q11 / C9).
- **sprintf specifiers:** the regex allows the space flag, so a literal `% d` in a format would count as a specifier. This follows the spec; no MAX-saved counter-example was seen.

## Doc impact (not edited, rule 8)

- **TECHNICAL.md:**
  - formula table (~lines 127-160): the `arg_count+1` route example now describes nothing, because route is a resolver;
  - API table: mention `src/maxpat/io_resolvers.py`, `IO_RESOLVERS`, `split_box_text`/`normalize_args`.
- **CLAUDE.md "Variable I/O Objects":**
  - `route foo bar baz` has 4 inlets as well as 4 outlets, and `select` is the same;
  - args are quote-aware, and `@attributes` don't count.
- **CLAUDE.md "After a Max update" procedure:** the Q9 note is still pending.

## Confirm in MAX (rule 9)

- These counts come from refpages, not MAX-saved boxes. A 30-second check in MAX is recommended:
  - bare `route` = (2,2) and bare `routepass` = (2,2);
  - bare `trigger` / `t` = (1,2).
- notein/ctlin with unusual args follow the refpage reading. Examples: `notein 0` -> 2 outlets; `ctlin -1` -> 3 outlets.
- No patch file changed, so there are no patch-level MAX checks.

## Threat Flags

None. No new network, auth or file-access surface. The overrides.json rewrite was guarded: only `variable_io_rules` changed, in exactly the 22 expected keys, and the byte format round-trips.

## Self-Check: PASSED

- FOUND: src/maxpat/io_resolvers.py, tests/test_io_resolvers.py, tests/fixtures/help_io_baseline.json
- FOUND commits: aa81809, b3dc9ba, f5ddcec (3 `(Q10)` commits since 5587b1c)
- Stash list unchanged (empty before and after). Protected trees (patches/, CLAUDE.md, TECHNICAL.md, README.md, .claude/skills, aliases.json, domain objects.json files) are unchanged in HEAD and in the working tree. Nothing pushed.
