---
phase: quick-261013-mv6
plan: 01
status: complete
subsystem: object-db / validation / patcher / genexpr
tags: [Q12, C3, G3, C11, J5, domain-scope, rnbo, gen, genexpr]
requires: [Q11 (0ef102ea)]
provides:
  - implied RNBO/Gen domain restrictions (367 names) with evidence-backed exemptions (35)
  - validate_patch scope kwarg + scope-aware Layer 2 / Layer 4b
  - Patcher.domain_context; add_box / replace_box / insert_into_connection refuse out-of-scope names
  - suffix-scoped save gate / validate_file / read_patch (.gendsp/.genjit -> gen, .rnbopat -> rnbo)
  - gen-domain-only GenExpr Check 6; Check 8 (clip() rejection) retired
affects: [src/maxpat/db_lookup.py, src/maxpat/validation.py, src/maxpat/patcher.py, src/maxpat/builders.py, src/maxpat/rnbo.py, src/maxpat/hooks.py, src/maxpat/code_validation.py, .claude/max-objects/overrides.json, .claude/max-objects/pd-blocklist.json, CLAUDE.md]
tech-stack:
  added: []
  patterns: [derived restriction from DB source sets; explicit key (even []) pre-empts derivation; scope threaded through validation, builders and save gate]
key-files:
  created: [tests/test_domain_scope.py]
  modified: [src/maxpat/db_lookup.py, src/maxpat/validation.py, src/maxpat/patcher.py, src/maxpat/builders.py, src/maxpat/rnbo.py, src/maxpat/hooks.py, src/maxpat/code_validation.py, .claude/max-objects/overrides.json, .claude/max-objects/pd-blocklist.json, CLAUDE.md, tests/test_code_validation.py, tests/test_validation.py]
decisions:
  - "Q12: a DB name whose only sources are rnbo/ and/or gen/ is implicitly restricted to them; an explicit domain_restricted key (even []) wins; get_domain_restrictions and Layer 4b stay explicit-only (D-05)"
  - "Q12: 35 RNBO-domain entries that are real Max objects (30 list.*, rnbo~, rnbo.remote, div~, rdiv~, rdiv) carry domain_restricted [] with a _domain_scope evidence note; codebox carries [gen, rnbo]"
  - "Q12: scope is a first-class input -- validate_patch(scope=), Patcher.domain_context (never serialized), file suffix for .gendsp/.genjit/.rnbopat"
  - "Q12: GenExpr Check 6 resolves called names against gen/objects.json only (raw names, no aliases); clip() accepted; Check 8 retired"
metrics:
  duration: ~75min
  completed: 2026-10-14
actuals:
  tokens: 29300
  tasks: 3
  commits: 3
plan_head_before: 0ef102ead3bb770e1fdc9c55c20994855dbe8c53
plan_head_after: 778cec00980cf753418b9d14f933207ed128f8d7
---

# Phase quick-261013-mv6 Plan 01: Q12 domain scope Summary

RNBO/Gen-only DB names (`expr~`, `wrap~`, `counter~`, `history`, 367 in total) are now restricted to their domains. The restriction is derived from DB source sets and enforced in validation Layer 2, `Patcher.add_box` and the save gate, and every scope (max/gen/rnbo) flows from the classnamespace, the container or the file suffix. Gen codebox calls are checked against the gen domain only, so `clip()` passes and `metro()` fails.

## Commits

| Task | Commit | Files |
|------|--------|-------|
| 1 (tracer) DB implied restrictions, exemptions, scope-aware Layer 2/4b, pd-blocklist | a62a6be1 | overrides.json, pd-blocklist.json, db_lookup.py, validation.py, tests/test_domain_scope.py |
| 2 Builder contexts, from_dict/read_patch/save gate scope, refuse-before-mutate | 903cce2e | patcher.py, builders.py, rnbo.py, hooks.py, tests/test_domain_scope.py |
| 3 GenExpr gen-domain Check 6, Check 8 retired, CLAUDE.md J5 | 778cec00 | code_validation.py, validation.py, tests/test_code_validation.py, tests/test_validation.py, CLAUDE.md |

Worktree base: `0ef102ead3bb770e1fdc9c55c20994855dbe8c53`, which contains Q11 (precondition passed: merge-base ancestor, `tests/test_override_merge.py` present, `merge_override_ports` defined). Nothing was pushed.

## Figures

- **pytest:**
  - base: `2921 passed, 1 xfailed, 1 xpassed, 29 warnings`;
  - after T1: 3041 passed;
  - after T2: 3070 passed;
  - final: **3081 passed, 1 xfailed, 1 xpassed, 29 warnings**. The warning count is unchanged at 29.
  - `git status --porcelain` was identical before and after every run.
- **Red counts before each GREEN step:**
  - T1: collection ImportError (the whole new file was red);
  - T2: 23 failed (2 already passed: the gen-inner validate test via codebox detection, and the .maxpat gate refusal from T1);
  - T3: 11 failed (block comments already passed, because the old check accepted metro/coll as DB objects).
- **`audit_domain_scope()`:**
  - implied **367**: 224 `['rnbo']`, 54 `['gen']`, 89 `['gen','rnbo']`;
  - explicit **2**: `codebox`, `floor~`;
  - exempt **35**.
- **Derivation:** 405 rnbo/gen-only names − alias key `f` − 35 exemptions − 2 explicit (`floor~`, `codebox`) = 367. Before the overrides edit the live count was 403 (405 − f − floor~).
- **Bundle GenExpr oracle** (Max 9.2.0, outside packages/RNBO and rnbo~ subtrees):
  - 66 codeboxes, 12 of which call `clip(`;
  - the old check errored on **48** of them; the new check reports **0** "Unknown GenExpr operator" errors;
  - 31 require-derived warning names, all in `easetile.genjit`.
- **Bundle Max-scope oracle:** 3,139 .maxpat/.maxhelp files, 1,411 distinct Max-scope newobj names, 0 with an implied restriction. Every exemption has evidence: an objectmappings line, an `.mxo`, or a Max-scope box.
- **Triage:**
  - committed-patch triage over 69 files / 1,448 findings is **identical** at base and after T1, T2 and T3 (run without a scope kwarg, so auto-detection is what keeps it identical);
  - codebox triage over 67 committed codeboxes is **identical** at base and after T3.
- **help-io oracle:** unchanged. `help-io-before.json` and `help-io-after.json` differ only in `generated_at`, and T1's `--write-baseline` names equal `tests/fixtures/help_io_baseline.json`.
- **validate_db.py --full:** `pd_blocklist_entries` is now 18 (was 19; threshold 15). Its other 2 failures are pre-existing and unrelated: `objects_json_valid` and `each_domain_nonempty` expect a monolithic `packages/objects.json`, which is not tracked at base either (packages live in per-package dirs).
- **Python 3.10:** a uv 3.10.19 venv with requirements-dev.txt and `MAXPAT_TEST_MAX_APP=/nonexistent/Max.app` gave 464 passed and 3 skipped (the requires_max oracles) across test_domain_scope, test_code_validation, test_validation, test_save_gate and test_codegen. The `ast.parse(feature_version=(3,10))` gate passed on every changed .py.

## Behavior changes (for the regression-averse user)

- **New boxes:**
  - `Patcher.add_box` raises ValueError for the 367 implied names, and for `floor~`/`codebox`, outside their domains. The message names the restriction, the context and Rule #1, plus `MAX equivalent: pong~ 1 0. 1.` for `wrap~`.
  - `floor~` via add_box at Max scope was previously silent. Its validation is unchanged (exactly one Layer 4b error, same text).
  - An `m4l` restriction is allowed in a Max patcher.
- **Inner patchers:**
  - `add_rnbo` inner -> rnbo, `add_gen` inner -> gen;
  - subpatchers and embedded bpatchers inherit their parent's context;
  - `from_dict` derives contexts from container names and classnamespace;
  - `read_patch` uses the file suffix.
- **Edits:** `replace_box`, `replace_box_safe` and `insert_into_connection` refuse before mutating anything (box, cords and `_next_id` unchanged).
- **Validation:**
  - `validate_patch(..., *, scope=None)` resolves its scope from the kwarg, then a Patcher's `domain_context`, then the classnamespace, then a top-level maxclass codebox, else max;
  - Layer 2 errors on implied names outside the scope;
  - Layer 4b skips explicit restrictions that include the scope, with a new message in gen/rnbo scope;
  - .gendsp/.genjit validate as Gen and .rnbopat as RNBO in the save gate, `validate_file` and `read_patch`.
- **GenExpr:**
  - `clip()` is accepted, and Max-only names (`metro`, `coll`, `route`) are errors (add_gen surfaces them as warnings, as before);
  - user-defined functions, comma-separated declarations, `.method(` calls and `/* */` comments are no longer misread;
  - in code that calls `require(...)`, unknown names are warnings.
- **pd-blocklist:** `clip~` is no longer listed as a PD object, and `wrap~` now suggests `pong~ 1 0. 1.`.

## Deviations from Plan

None. The plan was executed as written. Notes:
- I wrote the `rnbo.remote` `_domain_scope.finding` text myself, because the plan gave only its evidence and confidence. It reads "real Max object (an RNBO package external); its only DB entry is RNBO…".
- `test_checks_skip_comments` and `test_severity_contract` were left byte-identical, per "pass without edits". Only the class-level comment and docstring that described Check 8 were updated.

## Triage result

Identical, with no new findings in committed patches. No patch file changed and no allowlist entries were needed.

## Residuals and follow-ups (not fixed, rule 7)

- **Q19:** Layer 2/4b/5 recursion and gen/rnbo scope rules, including Max-only names inside gen~ and codeboxes in mc.gen~, jit.gen and nested gen~.
- **Q31:** `validate_code_file` checks only the first .gendsp codebox.
- **Q38:**
  - alias `list.*` to `zl.*` and fix the `list.*` I/O (e.g. `list.len` resolves to RNBO (1,1));
  - delete the 30 `list.*` exemption entries then, because an alias key plus its canonical key fails at load.
- **Q22:** the full GenExpr tokenizer. Only comment and declaration handling landed here.
- `generate_gendsp` writes classnamespace `box`, while MAX writes `dsp.gen`. The codebox rule in `detect_patcher_scope` covers this.
- No suggestion data exists for `floor~` -> `trunc~`, `counter~` -> `count~` and similar. Only `wrap~` has a MAX equivalent today.
- Pre-existing: validate_db.py expects a monolithic `packages/objects.json` (2 FAIL rows). Unrelated to Q12.

## Doc impact (not edited, rule 8)

- TECHNICAL.md:146: `domain_restricted` semantics changed. Absent now means implied, and `[]` means unrestricted.
- TECHNICAL.md:197-212: the pd-blocklist sample (clip~ removed, wrap~ -> pong~).
- TECHNICAL.md:221-237: the API table needs the new methods (`get_sources`, `get_implied_restrictions`, `get_effective_restrictions`, `is_gen_operator`, `suggest_max_equivalent`, `audit_domain_scope`, `detect_patcher_scope`, `inner_patcher_scope`).
- TECHNICAL.md:383-393: Layer 2 now covers the implied restriction and scope.
- TECHNICAL.md:420: Layer 4b is scope-aware.
- max-rnbo-agent SKILL: `add_box` inside the `add_rnbo` inner patcher now works, and RNBO-only names are accepted there.

## Confirm in MAX (rule 9)

- Type `div~`, `rdiv~` and `rdiv` into a Max patch. Each should create an object; they are exempted on the strength of their .mxo filenames and objectmappings (MEDIUM confidence). Drop the exemption for any that fails.
- Optional: check that a gen~ codebox with `out1 = clip(in1, -1, 1);` compiles. This is documented, and BEAP ships 12 such codeboxes.
- No patch file changed.

## Known Stubs

None.

## Self-Check: PASSED

- FOUND: tests/test_domain_scope.py, src/maxpat/db_lookup.py, src/maxpat/code_validation.py
- FOUND commits: a62a6be1, 903cce2e, 778cec00 (`git rev-list --count 0ef102ea..HEAD` = 3)
