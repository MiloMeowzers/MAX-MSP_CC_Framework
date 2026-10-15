---
phase: quick-261015-f1o
plan: 01
status: complete
subsystem: code-validation
tags: [genexpr, js, validator, save-gate, Q22-fix]
requires: [Q22 (58eda034)]
provides:
  - "Check 15 feedback state = an assigned History or any Delay"
  - "_js_mask regex-literal state (_JS_REGEX_PREFIX_KEYWORDS heuristic)"
affects: [validate_genexpr, validate_patch Layer 5, save gate, validate_js, validate_code_file]
tech-stack:
  added: []
  patterns: ["standard JS regex-vs-division heuristic in a single linear mask pass"]
key-files:
  created: []
  modified:
    - src/maxpat/code_validation.py
    - tests/test_genexpr_lint.py
    - tests/test_js_lint.py
decisions:
  - "CR-02 (D-03): tanh/tanh is an error only when a History is assigned somewhere or any Delay is declared; a read-only History (History one(1)) gives the warning"
  - "CR-01 (D-02): a lone / starts a regex unless the previous significant token ends a value (identifier, number, ), ], closing quote/backtick/regex /) or is a prefix keyword"
  - "} is not a value end; an unterminated regex ends at its line end; delimiters and flags stay in the mask"
metrics:
  duration: "~35 min"
  completed: 2026-10-15
requirements: [CR-01, CR-02]
actuals:
  tokens: 5200
  tasks: 2
  commits: 2
plan_head_before: 58eda0347617c036476c18100adec218df189a9f
plan_head_after: ed476e8b
---

# Quick 261015-f1o: Fix Q22 review CR-01 and CR-02 Summary

`History one(1)` is no longer save-blocking for tanh/tanh (feedback state = an assigned History or any Delay), and `_js_mask` now reads regex literals, so quotes, backticks and `\/` inside a regex no longer blank the rest of a js file.

## Commits

| Task | Commit | Message |
|------|--------|---------|
| 1 (tracer) | 182c3e74 | fix(code-validation): tanh/tanh is an error only with an assigned History or a Delay (Q22-fix) |
| 2 | ed476e8b | fix(code-validation): js mask recognises regex literals (Q22-fix) |

Both commits touch only `src/maxpat/code_validation.py` plus their own test file. `git diff --name-only 58eda034 HEAD` lists exactly the three `files_modified`; patches/, patterns/ and `tests/validate_error_allowlist.json` are unchanged.

## Task 1: CR-02 (Check 15 feedback state)

- `_lint_genexpr` now collects `history_names` and `has_delay`, and sets `has_feedback_state = has_delay or bool(history_names & set(assigned))`, reusing the existing `assigned_names(code)` result (genexpr_parse.py untouched). Both Check 15 messages and severities are byte-identical.
- The Check 15 comment and the validate_genexpr docstring entry 15 now state D-03.
- New `TestCheck15FeedbackState` (8 tests): REVIEW repro (warning, no error), never-assigned History (warning), assigned History via `=`, `+=` and inside an `if` block (error, `_TANH_ERR`), `one(1)` beside an assigned `z` (error), `one(1)` + `Delay` (error), and a `validate_patch` end-to-end check (repro: no tanh error; `h = y;` variant: exactly one).
- **Fixture edits (the one allowed exception):** `TestCheck15Tanh.test_error_with_history` and the `_FAMILIES` tanh error row each gained one `h = y;` line after the tanh line (tanh stays on line 3). Their assertions are byte-identical.
- **Red evidence (`red-t1.txt`):** exactly the three expected tests failed for the specific defect: the repro and the never-assigned test with `assert 'error' == 'warning'`, and the e2e test with the `gen~ 'obj-1' codebox: Line 4: tanh(...)/tanh(...) ... History/Delay state` error. The 5 guards and the 2 updated fixtures passed (3 failed, 22 passed).

## Task 2: CR-01 (js mask regex literals)

- New `_JS_REGEX_PREFIX_KEYWORDS` (return, typeof, instanceof, in, of, new, delete, void, throw, case, do, else, yield, await) plus `"re"` state with `in_class`. The pass tracks `value_end`, `last_sig` and `ident_start` incrementally (no backward scans, so it stays linear; 20k-line probe in 0.08 s).
- `_js_mask` and `validate_js` docstrings updated. `_JS_ES6_PATTERNS`, Checks 1-5, the engine logic, `validate_n4m` and `detect_js_type` are untouched.
- New `TestRegexLiterals` (72 tests incl. parametrizations).
- **Red evidence (`red-t2.txt`):** 18 failed, 54 passed. The failures were exactly the 3 repros (4 tests: the false `Missing 'outlets'` and `No handler` results, the false `ES6 syntax template literal on line 3` for js and jsui, and the missed OOB), the 12 keyword/punctuation prefixes (missed OOB), the character class (missed OOB) and the line-end recovery (false `Missing 'inlets'`). All guards passed before the fix.

## Closing gates (D-04)

- **Triage:** `triage.py --check` against the Step-0 base gives the single line `codeboxes=87 js=21 err_added=0 err_removed=0 unexpected=0 reorder_changed=0 io_changed=0 key_changed=0` after Task 1 and after Task 2, with no warning/info delta lines either.
- **Allowlist:** byte-identical to base, still exactly 2 entries.
- **Full suite:** baseline 4222 passed, 1 xfailed, 1 xpassed; final **4302 passed, 1 xfailed, 1 xpassed** (+8 Task 1, +72 Task 2) (`final-pytest.txt`).
- **Python 3.10:** all three changed .py files parse with `ast` `feature_version=(3, 10)`.
- **Stash list:** empty before and after.

## Discretion choices (as decided in the plan)

- A closing `'`, `"`, backtick or regex `/` counts as a value end, so a following `/` is division.
- `}` is not a value end: `}` followed by `/` starts a regex.
- Prefix keywords are matched on the whole identifier ending at the previous significant character, so `returned / 2` is division.
- An unterminated regex ends at its line end (not EOF), resetting `in_class`.
- Regex delimiters and flags stay in the mask; only the body is blanked. A backtick inside a regex never reaches `template_lines`.

## Known limits

- **`)`-header:** a `)` closing an `if`/`while`/`for` header directly before a regex reads as division (`if (x) /"/.test(y)` is mis-masked). This is the standard heuristic's limit.
- **`}` misread:** a division after `}` (for example `x = {} / 2`) reads as a regex.
- **Postfix `++`/`--`:** `a++ / 2` reads as a regex, because `+` does not end a value.
- **The damage is not always confined to one line.** An unterminated misread regex ends at its line end. A misread regex that closes on the same line, for example on a `/` inside a later string, can leave an unmatched quote that runs to EOF. Probe: `x = a++ / 2; y = "/";`. None of these forms occurs in the 21 committed .js files (triage delta 0).
- **Related, out of scope (IN-01):** `assigned_names` drops inner targets of chained assignments, so `a = h = y` with `History h` would still read as a never-assigned History and give the warning instead of the error.

## Deviations from Plan

None. The plan was executed as written. One environment note: the worktree sandbox refused compound shell commands, so Step 0 and the two `<verify>` chains ran from small helper scripts in the session scratchpad. The commands were the same as the plan's.

## Out of scope (D-01): left untouched

WR-01 (paren continuation hides missing semicolons), WR-02 (ES5 lint misses destructuring and async), WR-03 (`write_js` default `engine=None`), WR-04 (reorder moves statements after a missing `;`), WR-05 (private helper imports and duplicated traversal), IN-01 (chained-assignment targets), IN-02 (reorder line endings and whitespace), IN-03 (engine scan by stem), IN-04 (silent catch-alls).

## Doc impact

None. CLAUDE.md:170 ("In-loop saturation: normalize by the drive gain") and `.claude/skills/references/genexpr-rules.md:88` describe the GenExpr rule, not the validator's History detection, and stay accurate. No doc mentions the js mask. No docs were edited (rule 8).

## Confirm in MAX (rule 9)

Nothing. Both changes are validator-only and change no patch, codebox or .js file.

## Threat Flags

None. No new surface: the in-process validators gained no network, file or auth paths.

## Self-Check: PASSED

- FOUND: src/maxpat/code_validation.py, tests/test_genexpr_lint.py, tests/test_js_lint.py
- FOUND commits: 182c3e74, ed476e8b
- FOUND evidence: base-sha.txt, stash-list-before.txt, baseline-pytest.txt, triage-step0.txt, triage-base.json, triage-t1.json, triage-final.json, triage-final.txt, red-t1.txt, red-t2.txt, final-pytest.txt
