---
phase: quick-261015-f1o
verified: 2026-10-15T00:00:00Z
status: passed
score: 5/5 must-haves verified
covered_files: [src/maxpat/code_validation.py, tests/test_genexpr_lint.py, tests/test_js_lint.py]
covered_digest: "v2:sha256:354e808b0b978ea62cafd85be4fb33126031a2b33ed47adf9adada7d1b6d7755"
behavior_unverified: 0
overrides_applied: 0
---

# Quick 261015-f1o: Fix Q22 CR-01 / CR-02 Verification Report

**Goal:** Fix Q22 review findings CR-01 (js `_js_mask` regex literals) and CR-02 (tanh check false error with `History one(1)`).
**Status:** passed. **Re-verification:** No.

## Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | CR-02 repro (`History one(1)`, tanh/tanh) gives exactly one tanh result at warning, no error; `validate_patch` does not refuse it | VERIFIED | Re-ran repro: one `warning`, message byte-identical to spec. `test_validate_patch_history_one_not_blocked` passes (asserts both the no-error case and that the `h = y;` variant still yields one error). |
| 2 | tanh/tanh stays an error (message unchanged) with an assigned History or any Delay; never-assigned History gives warning | VERIFIED | Ran: assigned `h = y;` -> error; Delay -> error; chained `h = out1 = y` -> error; never-assigned -> warning. |
| 3 | CR-01 repro 1 (`/"/g`): no false Missing 'outlets' / No handler; `Handler functions found: bang` and exactly one OOB error | VERIFIED | Re-ran: results are Missing 'inlets' (correct, repro has no inlets line), `Handler functions found: bang`, `outlet() index 3 out of bounds (declared outlets = 1 ...)`. |
| 4 | Backtick-in-regex gives no ES6 template error (js and jsui) and later lines are still checked; `/\/\//` does not open a comment | VERIFIED | Re-ran repros 2 (js and jsui) and 3: only the handler info plus the OOB error. |
| 5 | Heuristic and invariants (mask length and line breaks kept, never raises, line-end recovery) | VERIFIED | Mask of `x = /[\/"]/g;\r\ny=1;\r\n` keeps length and `\r\n`. Ran adversarial inputs (`/`, `x = /`, `x = /[/`, trailing backslash, `}/`, `/"\n`) for engines None/js/v8 with no exception. 72 `TestRegexLiterals` tests pass. |
| 6 | Closing gates (D-04) | VERIFIED | See below. |

Score: 5/5 plan truths plus closing gates verified; 0 behavior-unverified (the behavior-dependent truths are exercised by passing tests).

## Closing Gates

| Gate | Result |
|------|--------|
| Targeted tests (`test_genexpr_lint`, `test_js_lint`, `test_code_validation`, `test_integration_patches`), run by me | 422 passed |
| Full suite (`final-pytest.txt`) | 4302 passed, 1 xfailed, 1 xpassed (baseline 4222 plus new tests) |
| Triage (`triage-final.txt`) | `codeboxes=87 js=21 err_added=0 err_removed=0 unexpected=0 reorder_changed=0 io_changed=0 key_changed=0` |
| `tests/validate_error_allowlist.json` | unchanged since 58eda034, 2 entries |
| patches/ and patterns/ | no diff vs 58eda034 |
| `git diff --name-only 58eda034 HEAD` | exactly the 3 `files_modified` |
| `(Q22-fix)` commits | 2 (182c3e74, ed476e8b) |
| Stash list | empty, matches before-state |
| Red evidence | `red-t1.txt`, `red-t2.txt` present; SUMMARY reports 3 and 18 failures before the fix |

## Anti-Patterns / Notes

No blockers. Documented heuristic limits, none in scope and none occurring in the 21 committed .js files:
- `a++ / 2` (and a division after `}`) reads as a regex. I confirmed `a++ / 2; var q = "/"; outlet(3,1);` hides the OOB error.
- A `)` closing an `if`/`while` header before a regex literal reads as division. I confirmed `if (x) /"/.test(y); outlet(3,1);` misses the OOB error.
- Chained-assignment inner targets (IN-01) are out of scope, as noted in SUMMARY.

These are warnings about heuristic edge cases the plan explicitly accepted (D-02, "Known limit"), not gaps against the must-haves.

## Human Verification

None. Validator-only change; nothing to confirm in MAX.

_Verified: 2026-10-15_
_Verifier: Claude (gsd-verifier)_
