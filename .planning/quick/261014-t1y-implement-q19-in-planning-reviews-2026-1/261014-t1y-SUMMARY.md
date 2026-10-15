---
phase: quick-261014-t1y
plan: 01
subsystem: validation
status: complete
tags: [validation, walker, save-gate, recursion, Q19, A7, S1, S2, G8]
requires: [Q1 non-destructive validation, Q7 save gate, Q10 split_box_text, Q12 domain scopes]
provides:
  - src/maxpat/walk.py (iter_patchers + quote-aware box helpers)
  - per-scope recursive validate_patch with ValidationResult.path
  - path-aware apply_fixes and save-gate finding key
affects: [Q20 critics/analysis/graph recursion, Q22 GenExpr lint, Q23 beside-patch abstractions, Q36 edit-session API]
tech-stack:
  added: []
  patterns: [iterative pre-order walker with id() cycle guard, wrap nested patcher as {"patcher": inner} to reuse layer functions]
key-files:
  created:
    - src/maxpat/walk.py
    - tests/test_walk.py
    - tests/test_validation_recursive.py
  modified:
    - src/maxpat/validation.py
    - src/maxpat/rnbo_validation.py
    - src/maxpat/hooks.py
    - tests/test_validation.py
    - tests/test_save_gate.py
decisions:
  - "Nested findings: ValidationResult.path = box-id chain (obj-1/obj-2), message prefix [label > label]; top level unchanged"
  - "Gen scopes (top level included) skip Layer 4; Layer 4b and 5 still run"
  - "Nested rnbo~ scopes: alias-resolved rnbo_compatible:false is a warning (no UI skip); Layer 3 bounds-only"
  - "Layer 5 reports every codebox once, at the scope holding its gen container; top-level .gendsp codeboxes stay unchecked"
  - "hooks._finding_key appends the path; apply_fixes returns 5-tuples for nested cords, proposed_removal stays a 4-tuple"
  - "box_label uses name + first positional arg (stops at the first @attr), so `mc.gen~ @chans 32` labels as `mc.gen~`"
metrics:
  duration: ~12 min
  completed: 2026-10-14
  tasks: 3
  files: 8
actuals:
  tokens: 26645
  tasks: 3
  commits: 3
plan_head_before: f1d4ee3788fe2ca89ec707b42b7eb650dfa747d3
plan_head_after: 7eaa71fa7ab4c7b90fca831bf0419e678827541a
---

# Quick 261014-t1y: Q19 Shared walker and recursive validation Summary

Validation now walks every embedded patcher (p, embedded bpatcher/poly~, gen~, mc.gen~ `data.patcher`, jit.gen, rnbo~). Each one is checked with its own scope, and nested findings are tagged with a box-id `path` and a `[p synth > gen~] ` prefix. This runs on one new iterative walker (`src/maxpat/walk.py`) and one quote-aware name extractor. `apply_fixes` and the save gate now use the path too.

## Figures

| | Passed | xfailed | xpassed |
|---|---|---|---|
| Base (f1d4ee37, Q/baseline-pytest.txt) | 3677 | 1 | 1 |
| Final (Q/final-pytest.txt) | **3813** | 1 | 1 |

There are 136 new tests:

| File | New tests |
|---|---|
| tests/test_walk.py (new) | 55 |
| tests/test_validation_recursive.py (new) | 79, including the requires_max bundle sweep, which ran on this Mac |
| tests/test_save_gate.py | +2 (`test_path_distinguishes_keys`, `TestNestedGateKey::test_moved_nested_blocker_is_new`) |
| tests/test_validation.py | 0 net (one test renamed and inverted) |

Red runs before each task's implementation are in Q/red-t1.txt, Q/red-t2.txt and Q/red-t3.txt. The red-t3 bundle sweep reproduced exactly 4 IndexErrors, for example `help/jitter/jit.freeframe.maxhelp`.

Triage (Q/triage-t1.json, triage-t2.json and triage-final.json) shows **top_mismatch=0 and nested_bad=0** on all 69 files every time. Every changed .py passes `ast.parse(feature_version=(3, 10))`.

## Commits

| Task | Commit | Message |
|---|---|---|
| 1 | 97d715a2 | feat(validation): shared patcher walker and per-scope recursive validation with path-tagged findings (Q19) |
| 2 | e6bef1ee | feat(validation): codeboxes in every gen scope, nested RNBO rules, path-aware save-gate keys (Q19) |
| 3 | 7eaa71fa | fix(validation): empty-text and malformed-entry robustness, duplicate box ids as Layer-1 errors, one quote-aware name extractor (Q19) |

No file under `patches/` was touched (Q/q19-commit-files.txt). The stash list is unchanged and nothing was pushed.

## walk.py API

| Name | Contract |
|---|---|
| `CONTEXTS` | `("max", "gen", "rnbo", "poly", "bpatcher")` |
| `STRUCTURAL_MAXCLASSES` | inlet / outlet / patcher / bpatcher; `object_name` returns None for these |
| `box_maxclass(box)` | maxclass if it is a str, else `""` |
| `box_text(box)` | text if it is a str, else `""` (None, numbers and lists never raise) |
| `box_tokens(box)` | `split_box_text(box_text(box))` (quote-aware; `\,` and quotes kept) |
| `box_name(box)` | newobj: first token or `""`; otherwise the maxclass |
| `box_args(box)` | newobj: raw tokens after the name, `@attrs` included (drop-in for `split()[1:]`); otherwise `[]` |
| `object_name(box)` | None for structural / non-str maxclass / an empty newobj; newobj gives its first token; otherwise the maxclass |
| `inner_patcher(box)` | dict `box["patcher"]`, else dict `box["data"]["patcher"]`, else None |
| `is_gen_container(box)` | name in `GEN_CONTAINER_NAMES` or maxclass `gen~` |
| `inner_scope(box, parent_scope)` | `inner_patcher_scope` on a sanitized view (never raises) |
| `box_label(box)` | `p synth`, `poly~ voice`, `gen~`; `bpatcher [name]`; otherwise the maxclass; `?` as fallback |
| `path_ids(path)` / `path_prefix(path)` | `obj-1/obj-2` / `[p synth > gen~] `; both are `""` at the top |
| `scope_of(context)` | gen and rnbo map to themselves; everything else maps to max |
| `iter_patchers(patch, scope=None)` | yields `(path, patcher, context)`, top level first, then pre-order. It uses an explicit stack and an id() cycle guard, walks embedded dicts only, and skips malformed entries |

## Triage (rule 3), from Q/triage-final.json

**Nested errors: 0. Nested proposals: 0. No allowlist entry was needed.** Committed patches gain 38 nested warnings and 104 nested infos (83 missing-assistance, 21 `Detected I/O`).

| Count | Level | Template | File / path | Disposition |
|---|---|---|---|---|
| 6 | warning | `Unsafe gain multiplier` | minitaur: `p oscillators` obj-3 (`*~ 2.`, `*~ 24.`), `p mixer` obj-4 (`*~ 2.`), `p filter` obj-8 (`*~ 2.`, `*~ 5.` ×2) | True positive or intentional (deliberate drive stages); user-confirmed patch; no action |
| 5 | warning | `Unsafe gain multiplier` | physics-composition: `p voice-1..5` obj-62..66, inner obj-68 (`*~ 2.`/`3.`/`1.5`/`2.5`/`4.`) | True positive or intentional; user-confirmed patch; no action. Research attributed these to minitaur; they are in physics-composition |
| 7 | warning | `Unknown object` | terrain-synth `p terrain-view-a` obj-418 (terrain-osc ×2, terrain-lfo), `p terrain-view-b` obj-419 (terrain-osc-b ×2, terrain-lfo); terrain-voice `p motion` obj-60 (terrain-lfo) | Q23 (beside-patch abstractions) |
| 4 | warning | `Unterminated signal chain` `*~` | terrain-synth `p terrain-view-a` (obj-26, obj-45), `p terrain-view-b` (obj-26, obj-48) | True positive or intentional; user-confirmed patch; no action |
| 1 | warning | Comment `#N` | looper `p about` obj-57 (obj-18) | True positive or intentional; user-confirmed patch; no action |
| 1 | warning | `trigger outlet → signal inlet` | rhythmic-corpus-chopper `p sequencer` obj-25 (obj-45 → obj-46) | True positive or intentional; user-confirmed patch; no action |
| 14 | warning | jit.gen codebox `Param … missing min/max` | terrain-synth `p terrain-source` obj-44 and `p terrain-source-b` obj-303, jit.gen obj-92 (tension, damp, leak, ex_amp, ex_x, ex_y, ex_r) | True positive or intentional; user-confirmed patch; no action |
| 83 | info | inlet/outlet missing assistance comment | various `p` subpatchers | Info; no action |
| 21 | info | `<container> codebox: Detected I/O` | nested gen~ (19) and jit.gen (2) | Info; no action |

**Newly covered top-level codebox findings:** 1. It is ji-harmonizer obj-88: `mc.gen~ 'obj-88' codebox: Detected I/O: 3 input(s), 1 output(s)` (info).

## Decisions taken (planner decisions 1-13)

1. **Path and label.** Path elements are `(str(id) or "?", label)`. `ValidationResult.path` is the id chain, and the prefix is the label chain. `box_label` uses the name plus the first *positional* argument: it stops at the first `@attr` instead of skipping `@` tokens, so `mc.gen~ @chans 32` labels as `mc.gen~` rather than `mc.gen~ 32`. This matches the decision's stated examples.
2. **Context.** gen and rnbo come from `inner_scope`; otherwise bpatcher, then poly~/mc.poly~, then max. A `p` inside gen~ or rnbo~ inherits the parent's scope. The poly and bpatcher contexts run the max layers.
3. **Top level.** The top level runs first, unchanged, and nested results follow in pre-order. Triage confirms byte identity on all 69 files.
4. **Gen Layer-4 skip.** Every gen scope skips Layer 4, the top level included. This has no effect on the baseline: the 12 .gendsp files give 0 findings. Layers 4b and 5 still run.
5. **RNBO rules are nested-only.** The `rnbo-objects` check is a warning, alias-resolved, with **no UI skip**, so `flonum` and `panel` would warn. `RNBODatabase` is cached lazily, and Layer 3 checks bounds only in nested rnbo scopes (`type_checks=False`). A top-level `.rnbopat` is unchanged.
6. **Layer 5.** Codeboxes are reported from the scope that holds their gen container, as `<name or maxclass> '<id>' codebox: …`. Each is reported once, and top-level .gendsp codeboxes stay unchecked.
7. **Pruning.** A nested Layer-1 error skips that scope and its descendants, while siblings still run. A top-level Layer-1 error still returns early.
8. **Malformed entries are Layer-1 errors.** A non-dict box or line entry, and a non-dict `box` or `patchline` value, are errors. A dict entry without the key is tolerated.
9. **apply_fixes.** Proposals are grouped by path, and the `""` group runs the pre-Q19 code verbatim. Nested scopes are resolved by the full path string: `walk.iter_patchers` for dicts; `_inner_patcher` plus `data.patcher` from `_raw` or `extra_attrs` for a Patcher. A path that names no scope, or more than one, removes nothing. Nested matches return 5-tuples, and `proposed_removal` stays a 4-tuple.
10. **Gate key.** `_finding_key` appends `getattr(result, "path", "")`.
11. **Layer 2d.** One `warned_packages` set is shared per `validate_patch` call.
12. **One name extractor.** `validation._extract_object_name` / `_get_box_name` / `_STRUCTURAL_MAXCLASSES` and `rnbo_validation._extract_object_name` / `_RNBO_STRUCTURAL_MAXCLASSES` are deleted. Neither module contains `.split()` anymore. The `.split()` grep assertion did **not** need narrowing: the only remaining split in validation.py is `inlet_type.split("/")`, which the regex does not match.
13. **Bundle-only findings** are out of scope. The sweep is a no-crash test only (see follow-ups).

## Deviations from Plan

- **Scratch tooling only:** Q/triage.py's first `--check` compared top-level records without `path` against base records that still had a `path` key. It reported a false `top_mismatch=31`, and the fix was to drop `path` on both sides. The helper is untracked, and no product code was affected.
- **Test import:** the bundle sweep imports `MAX_APP_PATH` from `tests.conftest`, as other tests do; the bare `conftest` import does not resolve.

Otherwise the plan was executed as written.

## Existing tests changed

- `tests/test_validation.py::TestDomainGuard::test_floor_tilde_in_gen_subpatcher_silent` was renamed to `test_floor_tilde_in_gen_subpatcher_flagged_with_path` and inverted. It now asserts exactly one `[gen~] 'floor~' is restricted to ['rnbo']; not allowed in a gen patcher.` error with `path == "gen-1"`.
- Two docstrings were rewritten: TestDomainGuard (Layer 4b runs in every scope; D-07 retired in Q19) and TestEmbeddedGenExpr (Layer 5 runs in every scope; the D-07 note is retired).
- No other existing test needed changes. The existing `TestFindingKey` tests stayed green unedited.

## Out of scope / doc impact, not edited (rule 8)

- `.claude/skills/references/severity-contract.md` still describes the top-level-only scope and a 4-tuple `apply_fixes` return (around lines 11, 15, 42, 47, 84 and 103). It should say: recursive scopes, `path`, and 5-tuples for nested cords.
- TECHNICAL.md: "Layer 5: Embedded GenExpr Codebox Walker" (now every gen container, reported at the parent scope) and the proposed-removal paragraph.
- `proven-forms.md`: "validate a deepcopy" (still correct, since validation is pure).
- Q20 consumers still on their own walkers and extractors: `hooks._iter_patchers`, `utils.get_box_name`, the critics, analysis, testing, graph, layout and m4l_polish.
- `db_lookup.inner_patcher_scope` still splits text itself.
- Bundle-only checker and DB gaps from planner decision 13, which the sweep only reaches:
  - max-scope "Wrong maxclass" errors on MAX-saved maxclasses (a Q13-class maxclass-map follow-up);
  - "Signal outlet to control-only inlet" proposals in max scopes;
  - rnbo-scope `codebox~` "Wrong maxclass" errors;
  - gen-only names flagged inside rnbo;
  - gen~ codebox init-before-if errors (Q22 GenExpr lint);
  - RNBO `rnbo_compatible` data gaps for `flonum`, `panel`, `*~` and the arithmetic operators. Nested rnbo scopes now *warn* on these.
- Robustness gaps not in the plan's never-raise list, left as they were: a non-hashable box `id`, or a non-list patchline `source` reaching Layer 4's `len(source)`, can still raise. None occur in committed patches or the bundle.

## Threat model

The register's mitigations are implemented and tested:
- T-01: same-4-tuple twin cords stay untouched for dict, Patcher and mc.gen~.
- T-02: deep, cyclic and malformed input, plus the bundle sweep.
- T-03: the moved-blocker gate test.
- T-04: triage shows 0 nested errors and 0 proposals, and RNBO is warning-only.
- T-05: no patches/ change.
- T-06: purity tests.
- T-07: triage top-level byte identity.
- T-08: explicit-path commits and an unchanged stash list.

No new threat surface.

## MAX/Live confirmation

None required: the work is validator-only and no patch changed. Optional: the nested RNBO rules are unconfirmed in MAX because no RNBO patch has been confirmed yet.

## Self-Check: PASSED

- FOUND: src/maxpat/walk.py, tests/test_walk.py, tests/test_validation_recursive.py
- FOUND commits: 97d715a2, e6bef1ee, 7eaa71fa (exactly 3 `(Q19)` commits since f1d4ee37)
- Full suite green (3813 passed / 1 xfailed / 1 xpassed), triage-final top_mismatch=0 and nested_bad=0, stash list unchanged, no patches/ in the commits
