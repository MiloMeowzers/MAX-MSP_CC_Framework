---
phase: quick-261015-du0
plan: 01
subsystem: code-validation
status: complete
tags: [genexpr, parser, lint, js, es5, validation, Q22]
requirements: [R6, S5, G1, G2, G4]
requires: []
provides:
  - "src/maxpat/genexpr_parse.py: single GenExpr mask tokenizer + statement parser"
  - "validate_genexpr Checks 10-16"
  - "validate_js(code, *, engine=None) ES5 lint; validate_code_file / write_js engine="
  - "tests/validate_error_allowlist.json"
affects: [add_gen, generate_gendsp, add_rnbo, validate_patch Layer 5, hooks.validate_code_file, hooks.write_js]
tech-stack:
  added: []
  patterns: ["offset-preserving comment/string mask; regexes run on the mask, original text sliced by spans"]
key-files:
  created:
    - src/maxpat/genexpr_parse.py
    - tests/test_genexpr_parse.py
    - tests/test_genexpr_lint.py
    - tests/test_js_lint.py
    - tests/validate_error_allowlist.json
  modified:
    - src/maxpat/codegen.py
    - src/maxpat/rnbo.py
    - src/maxpat/code_validation.py
    - src/maxpat/hooks.py
    - tests/test_integration_patches.py
decisions:
  - "Parser lives in src/maxpat/genexpr_parse.py, stdlib only, no src.maxpat imports"
  - "Validate errors in frozen patches get their own allowlist file (validate_error_allowlist.json), keyed (kind, box_id, name, path)"
  - "Spec 'note' severity maps to validator level info (D-06)"
  - "Checks 2/5 skip multi-line paren continuation lines"
  - "js engine scan: recursive inside patches/<project>, else non-recursive path.parent"
metrics:
  duration: "~75 min"
  completed: 2026-10-15
actuals:
  tokens: 31500
  tasks: 3
  commits: 3
plan_head_before: 83e38341d73cc3f93ea94f82493a694dac8a9986
plan_head_after: a9bf5a1651eb3bda1ba18b75d48dca7963c3e10f
---

# Quick 261015-du0 (Q22): GenExpr parser, codebox lint, js ES5 lint Summary

One offset-preserving GenExpr mask/statement parser now drives I/O detection, declaration reorder, Param parsing and validate_genexpr. On top of it sit the new codebox lint Checks 10-16 and an engine-scoped js ES5 lint.

## Commits

| Task | Commit | Message |
|---|---|---|
| 1 | b366a8a5 | feat(genexpr): one GenExpr tokenizer/statement parser for io, reorder, Param parsing and validation (Q22) |
| 2 | 31c617af | feat(code-validation): GenExpr lint checks 10-16 and validate-error allowlist (Q22) |
| 3 | a9bf5a16 | feat(code-validation): js ES5 lint by engine and comment-aware inlets/outlets (Q22) |

None of them touches `patches/` or `patterns/` (Q/q22-commit-files.txt). The stash list is unchanged.

## Test counts

- Baseline at 83e38341: **3982 passed, 1 xfailed, 1 xpassed** (Q/baseline-pytest.txt).
- Final: **4222 passed, 1 xfailed, 1 xpassed** (Q/final-pytest.txt). That is +240 new tests, nothing skipped, and the requires_max bundle sweeps ran.
- Red runs before each fix:
  - Q/red-t1.txt: 60 failed;
  - Q/red-t2.txt: 33 failed, including both allowlist entries reported stale;
  - Q/red-t3.txt: 83 failed.

## What changed

- **Parser (S5).** `src/maxpat/genexpr_parse.py` provides:
  - `mask` and `Stmt`/`statements`;
  - `declarations`, `split_args`, `parse_params`, `assigned_names`;
  - `io_counts`, `line_paren_depths`, plus `line_comment_starts`.

  It uses only the standard library, never raises, and preserves offsets.
- **G2.** `parse_genexpr_io` uses `io_counts`, so `// mix in4 and out3` gives (1, 1).
- **G1.** `reorder_genexpr_declarations` moves whole depth-0 declaration statements by their original span:
  - commented-out declarations stay in their comment;
  - a multi-line Param moves verbatim;
  - `//` lines directly above a declaration move with it, and so does a trailing comment;
  - declarations inside function bodies are never moved;
  - the input comes back byte-identical when nothing needs to move.
- **G4.** `parse_genexpr_params` uses `parse_params`:
  - absent or non-literal values give None;
  - kwargs and whitespace are tolerated;
  - every name in a comma list is returned.

  `add_rnbo` now omits `@min`, `@max` or `@initial` when the value is None. Dicts without those keys keep the old defaults.
- **validate_genexpr Checks 1-9** run on the mask. Checks 2 and 5 use the paren-continuation rule. `_strip_line_comments` and `_strip_block_comments` were deleted, and every existing message format is unchanged.
- **Checks 10-16 (R6)** use the spec severities and the exact message text:
  - errors: tab (10), built-in constant assignment (11), Param assigned as a local (12);
  - warnings: nested or non-literal-bound `for` (13), de-hoist fixpoint (14);
  - tanh normalization (15): error when the codebox has History/Delay, otherwise warning (D-04);
  - info: `else if` and 2-argument `peek` (16).
- **js.** The new signature is `validate_js(code, *, engine=None)`:
  - ES6 syntax is an error for js/jsui, gives nothing for v8/v8ui, and gives exactly one info when the engine is unknown;
  - the inlets/outlets, handler and `outlet(` checks run on a JS comment/string mask (G8 js).
- **hooks.**
  - `_js_engine_for(path)` resolves the engine from the project's .maxpat boxes (D-02);
  - `validate_code_file(path, *, engine=None)` and `write_js(code, path, *, engine=None)` accept an explicit override (D-03).

## Allowlist entries (D-05)

`tests/validate_error_allowlist.json` is used only by `test_validate_patch_no_errors`. Its keys are (kind, box_id, name, path).

| Patch | Kind | box_id | name | path | Reason |
|---|---|---|---|---|---|
| patches/tape-wobble/generated/tape-wobble.maxpat | genexpr_const_assign | obj-3 | pi | "" | True positive surfaced by Q22. The gen~ obj-3 codebox assigns `pi = 3.14159265358979;` (line 42). The built-in wins silently and the value equals it, so behaviour is unchanged. The patch is frozen. |
| patches/tape-wobble/generated/tape-wobble.maxpat | genexpr_const_assign | obj-3 | twopi | "" | True positive surfaced by Q22. The same codebox assigns `twopi = 2.0 * pi;` (line 43). The built-in wins silently and the value equals it. The patch is frozen. |

The allowlist has three hygiene tests:
- liveness: each entry exists, has a reason, and still fires;
- calibration exclusion;
- key scoping: a different name, box id, path or patch is not exempted; a proposed removal is never exempted; warnings are never consulted.

## Committed-corpus triage (Q/triage.py, 87 codeboxes + 21 js files)

The final check (Q/triage-final.txt) passed with no unexpected changes: `err_added=2 (allowed pair) err_removed=0 unexpected=0 reorder_changed=0 io_changed=0 key_changed=0`. The reorder is the identity and the I/O counts are unchanged on all 87 codeboxes. The 21 js files show no change at all.

**Task 1 deltas (warnings removed, all false positives of the old line-based Check 2):**
- **Trailing comments.** These lines ended in `// ...` and were flagged as missing a semicolon:
  - bassoon.gendsp obj-3: lines 226, 229, 306, 330, 504;
  - gong-engine.gendsp obj-2: line 575;
  - comp-engine.gendsp obj-code: lines 4-8, 10, 11;
  - crossover-4band.gendsp obj-code: line 74.
- **Paren continuation.** Lines inside a multi-line paren group: tape-wobble obj-3/obj-3, lines 85-88 and 91-94 (`flutter_mod_L/R = ... (` spanning lines).

**Task 2 deltas:**
- **Errors (+2, allowlisted):** tape-wobble obj-3 `pi` and `twopi`.
- **De-hoist warnings (Check 14):**
  - stereo-feedback-delay obj-1/obj-2: line 30 `inc` (alias `sr`, Param `mod_rate`) and line 43 `dcoef` (alias `sr`, Param `damp`). The plan expected `inc`; `dcoef` is the same `sr` pattern.
  - tape-wobble obj-3/obj-3: `f1_inc` (L77), `w0_bump` (L123), `w0_lp` (L142), each with aliases `sr` and `twopi`. These match the plan.
  - **Not predicted by the plan:**
    - FDNVerb.gendsp obj-3, line 158: `dc = frz ? 0 : min(damping, 0.98)` with `frz = freeze > 0.5`.
    - kicksynth obj-19/obj-2, line 55: `amp_coeff = exp(-1.0 / (amp_samples * amp_curve))` with `amp_samples = max(amp_decay * 0.001 * samplerate, 1)`.

    Both are exactly the "chain of dependent hoisted values" that genexpr-rules.md names as the risk, so they are true matches of the spec's fixpoint, not checker false positives. They are warnings only: no test or critic gate reads them, and kicksynth's calibration gate (review_patch blockers) is unaffected. Both patches work on the user's Max build; per genexpr-rules.md the risk is on other 9.x builds.
- **tanh warning (Check 15):** `patterns/gen/gain/soft-clipper.gendsp` obj-2, `tanh(in1 * drive) / tanh(drive)`, with no History. This was expected and is acceptable per the orchestrator.
- **2-argument peek info (Check 16):** scala-synth-voice obj-5/obj-2, line 26. Expected.

## Bundle report (Q/bundle-q22.json)

The report covers 66 inputs with 0 exceptions: 65 codeboxes from .maxpat/.maxhelp/.gendsp/.genjit files plus 1 `.genexpr`, with `/packages/RNBO/` skipped per the spec. Counts by codebox:

| Check | Count |
|---|---|
| tab (error) | 48 |
| else_if (info) | 23 |
| peek2 (info) | 3 |
| for_bound (warning) | 3 |
| nested_for (warning) | 1 |

The research total of 146 included the 80 RNBO `.genexpr` files. A side scan of those (0 exceptions) found 26 more tab errors, which makes **74 tabs**, matching the research. For loops also match the research: 3 + 3 = 6 non-literal bounds and 1 + 1 = 2 nested. The research's `else if` (100) and peek (192) numbers count occurrences, not codeboxes.

**Tab = error now flags Cycling '74 codeboxes that compile in MAX (74 of 146).** This severity is locked by the spec and CLAUDE.md. The bundle oracle only asserts no `Unknown GenExpr operator` error, so it stays green. This is recorded here for the user to weigh.

## Discretion choices

- **Parser API.** It lives in `src/maxpat/genexpr_parse.py` with the reference API. Task 2 could only edit code_validation.py, so Check 14 builds its assignment records from the parser's private helpers (`_find_assign`, `_for_parts`, `_split_top`, `_strip_prefixes`, `_paren_content`) instead of adding a regex copy.
- **Allowlist mechanism.** A new `tests/validate_error_allowlist.json` with the same hygiene as `review_blocker_allowlist.json`, which covers critic blockers only.
- **De-hoist.** The fixpoint from the plan's reference data.
- **Check 2 / Check 5 continuation rule.** Check 2 skips a line that starts or ends inside an open paren; Check 5 skips a line that starts inside one.
- **Project-dir scan rule.** Inside `patches/<project>/` the scan is recursive (rglob); anywhere else it is a non-recursive `path.parent` glob. js/jsui wins over v8/v8ui.
- **Severity mapping.** The spec's "note" maps to `info`.
- **Robustness.** `statements` and `line_paren_depths` reset paren depth at `{` and `}`, so an unbalanced `(` cannot swallow the rest of the codebox.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `m` mask variable shadowed in validate_genexpr**
- **Found during:** Task 2.
- **Issue:** Check 9's `m = assign_pattern.match(...)` rebinds `m`, so anything after Check 9 that used the mask got a Match object instead.
- **Fix:** Renamed the mask variable to `masked` throughout validate_genexpr.
- **Files modified:** src/maxpat/code_validation.py.
- **Commit:** 31c617af.

### Environment

The plan says to execute on `main` in the main checkout. This run executed in the orchestrator's agent worktree (`worktree-agent-afe5bfe2b1ce062fe`) as instructed. All hard preconditions held at base 83e38341.

## Known limitations and deferred items

- **Known tanh false negative.** kicksynth's `tanh(drive*sig) / max(tanh_drive, 0.001)` is not matched. The pattern was deliberately not widened because kicksynth is a calibration project.
- **D-03 has no patch-level call site.** The `engine=` parameter on `validate_js`, `validate_code_file` and `write_js` is ready, but `validate_patch` does not read .js files (out of scope).
- **`write_js` timing.** Without an explicit `engine=`, a js file written before its referencing .maxpat exists gets one ES6 info, not an error. Pass `engine="js"` when the box type is known.
- **Deferred (rule 7):**
  - G3: validate every codebox in a .gendsp (hooks still checks only the first);
  - S9: delete the dead `_check_genexpr_io_syntax` / `_check_genexpr_delay_usage`;
  - add js reading to validate_patch.
- **Minor.** For CRLF code the reorder's separator line and the newline appended to a piece at EOF are `\n`, which mixes line endings. MAX accepts both.

## To confirm in MAX / Live (rule 9)

1. **Tab severity vs the bundle evidence.** 74 of 146 shipped Cycling '74 codeboxes contain tabs and compile, yet tabs are now an error, which refuses a .maxpat save that newly introduces them through Layer 5. Decide whether to keep `error` or downgrade it.
2. **RNBO params with one bound.** A GenExpr Param with only `min=` or `max=` now produces an RNBO `param` with only that bound, so RNBO's default applies to the missing one; previously it was hard-coded to 0.0/1.0. Confirm in MAX when an RNBO export is next used (RNBO is experimental).

The checks themselves are static and grounded in genexpr-rules.md, so nothing else needs confirming in MAX.

## Doc impact (no docs edited, rule 8)

- **TECHNICAL.md:436-449.** The validate_genexpr check list stops at Check 9, and the validate_js list lacks the ES5 lint and engine parameter.
- **severity-contract.md:103.** Still accurate (validate_js is report-only), but the new GenExpr errors (tab, constant, Param-as-local, tanh with state) now refuse a .maxpat save that introduces them through Layer 5.
- **max-js-agent SKILL.md:52.** Shows `validate_js(code)`; there is now an `engine=` keyword, and `write_js` has `engine=`.
- **max-rnbo-agent SKILL.md:65.** `parse_genexpr_params` may now return None bounds and defaults.
- **genexpr-rules.md.** The tab, `else if` and peek rules should be read against the bundle evidence above.
- **`patterns/gen/gain/soft-clipper.gendsp`.** It teaches `tanh(x*drive)/tanh(drive)` and now draws a Check 15 warning.
- **CLAUDE.md "Gen~" codebox rules.** Tabs, constant names, the Param/local clash, loops, de-hoist, tanh normalization and the js ES5 rule are now enforced by the validator.

## Threat surface

There is no new network, auth or schema surface. The engine scan reads .maxpat files near a .js path, bounded as described above, and it is read-only and never raises (T-du0-06 mitigated).

## Self-Check: PASSED

- Files exist:
  - src/maxpat/genexpr_parse.py;
  - tests/test_genexpr_parse.py, tests/test_genexpr_lint.py, tests/test_js_lint.py;
  - tests/validate_error_allowlist.json.
- Commits exist: b366a8a5, 31c617af and a9bf5a16 are all in `git log`.
- Closing state:
  - full suite green;
  - triage `--check` exited 0 after every task;
  - `--selftest` exited 0;
  - bundle report has 0 exceptions;
  - exactly 3 `(Q22)` commits, none touching patches/ or patterns/;
  - Python 3.10 `ast` parse passes on all 9 changed .py files;
  - stash list unchanged.
