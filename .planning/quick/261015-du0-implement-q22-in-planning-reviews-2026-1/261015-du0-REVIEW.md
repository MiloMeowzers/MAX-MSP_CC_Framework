---
phase: 261015-du0-implement-q22
reviewed: 2026-10-15T00:00:00Z
depth: quick
files_reviewed: 10
files_reviewed_list:
  - src/maxpat/code_validation.py
  - src/maxpat/codegen.py
  - src/maxpat/genexpr_parse.py
  - src/maxpat/hooks.py
  - src/maxpat/rnbo.py
  - tests/test_genexpr_lint.py
  - tests/test_genexpr_parse.py
  - tests/test_integration_patches.py
  - tests/test_js_lint.py
  - tests/validate_error_allowlist.json
findings:
  critical: 2
  warning: 5
  info: 4
  total: 11
status: issues_found
---

# Phase 261015-du0 (Q22): Code Review Report

**Reviewed:** 2026-10-15
**Depth:** quick (pattern scan over diff 83e38341..a9bf5a16, plus targeted probes of the new lint/parse paths)
**Files Reviewed:** 10
**Status:** issues_found

## Summary

The pattern scan found no hardcoded secrets, no dangerous calls (eval/exec/subprocess), and no debug artifacts. The only broad excepts are the documented "never raises" guards. The 237 new tests pass. Running small probe inputs through `validate_genexpr`, `validate_js` and `reorder_genexpr_declarations` turned up two correctness defects that matter:

1. The new js comment/string mask has no regex-literal state. Checks 1-4 now run on the mask, so one regex containing a quote or backtick blanks the rest of the file. The result is false "Missing outlets" errors and a missed `outlet()` out-of-bounds error. Before Q22, those checks ran on raw code, so this is a regression.
2. Check 15 reports an **error** for any `tanh(..)/tanh(..)` when the codebox declares any History. That includes `History one(1)`, the de-hoist idiom CLAUDE.md requires. Layer 5 feeds codebox errors into the save gate, so a legitimate non-feedback waveshaper is refused at save.

## Critical Issues

### CR-01: js mask treats regex literals as strings, so outlet/inlet checks silently break (regression)

**File:** `src/maxpat/code_validation.py:668-735` (`_js_mask`), used by Checks 1-5 from line ~808
**Issue:** `_js_mask` only knows the states normal, `//`, `/* */`, `'`, `"` and backtick. A regex literal is scanned as normal code. Its quote or backtick then opens a string or template state that runs until the next matching quote, or to EOF. Probe results:
- `var s = x.replace(/"/g, "");\noutlets = 1;\nfunction bang() { outlet(3, 1); }` with `engine="js"` reports "Missing 'outlets' declaration" (false) and "No handler functions found" (false). It also **misses** the real `outlet() index 3 out of bounds` error.
- `` var r = /`/; `` reports a false "ES6 syntax template literal" error for js/jsui and masks every line after it.
- `/\/\//` gives a false `//` comment start, which blanks the rest of the line.

Before Q22, Checks 1-4 ran on the raw code and did not have these failures. Agents are told to "read the returned list and fix it" (severity-contract §86), so they will act on the false errors, for example by adding a duplicate `outlets` line, and will not see the real out-of-bounds error.
**Fix:** Add a regex-literal state. Treat `/` as a regex start when the previous significant token is not an identifier, number, `)` or `]`, and handle `[...]` classes and backslash escapes until the closing `/`:
```python
# in state "" before the quote handling:
if c == "/" and _regex_allowed(prev_sig):   # prev_sig = last non-space char in `out`
    state = "re"; i += 1; continue
...
if state == "re":
    if c == "\\" and i + 1 < n: out[i] = out[i+1] = " "; i += 2; continue
    if c == "[": in_class = True
    elif c == "]": in_class = False
    elif c == "/" and not in_class: state = ""; i += 1; continue
    elif c == "\n": state = ""          # unterminated: recover at EOL
    if c not in "\r\n": out[i] = " "
    i += 1; continue
```
Add tests to `tests/test_js_lint.py` with `/"/g`, `` /`/ `` and `/\/\//` followed by an out-of-bounds `outlet()`.

### CR-02: Check 15 makes `tanh/tanh` a blocking error whenever any History exists, including `History one(1)`

**File:** `src/maxpat/code_validation.py:508-512` (where `has_feedback_state` is set), `614-635` (Check 15)
**Issue:** `has_feedback_state` becomes True for **any** History or Delay declaration. It does not check whether the History is ever written. CLAUDE.md requires `History one(1);` plus `k_x = x * one;` to de-hoist Param-only setup chains, so most codeboxes that follow project rules declare a History that is read-only. Probe:
```
Param drive(2);
History one(1);
d = drive * one;
out1 = tanh(in1 * d) / tanh(d);
```
This yields `error: Line 4: tanh(...)/tanh(...) normalization in a codebox with History/Delay state (a feedback path)`. That is wrong: there is no feedback path, and output-stage `tanh(x*d)/tanh(d)` is a legitimate unity-peak waveshaper. `_validate_embedded_genexpr` (Layer 5) forwards codebox errors to `validate_patch`, and the save gate refuses newly introduced errors. A new patch with this codebox therefore cannot be saved without `force=True`.
**Fix:** Count a History as feedback state only if it is assigned in the body, not just declared. Delay can stay unconditional, since a Delay that is written is a buffer. Or keep Check 15 at warning level. For example:
```python
history_names = {n for d, ns, _ in decls if d == "History" for n in ns}
has_delay = any(d == "Delay" for d, _, _ in decls)
has_feedback_state = has_delay or bool(history_names & set(assigned))
```
Add a regression test with `History one(1)` plus `tanh/tanh` that expects no error.

## Warnings

### WR-01: The paren-continuation rule hides every missing semicolon after an unclosed paren, and nothing checks paren balance

**File:** `src/maxpat/code_validation.py:154-157` (Check 2), `217-220` (Check 5)
**Issue:** Check 2 skips any line whose start or end depth is above 0. One unclosed `(` therefore makes every later line a "continuation", and Check 1 only counts braces. Probe:
```
Param g(1, min=0, max=1);
a = max(in1, 0;
b = a * g
c = b * 2
out1 = c;
```
This returns only the `Detected I/O` info: no error for the unclosed paren and no missing-semicolon warnings. Before Q22, lines 3 and 4 were flagged. The gen~ compile will fail in MAX with no validator signal.
**Fix:** Add a paren-balance check on `masked` next to Check 1, reported as an error: `masked.count("(") != masked.count(")")`, or the final depth from `line_paren_depths(code)[-1][1] != 0`. When the parens are unbalanced, skip the continuation rule.

### WR-02: The ES5 lint misses destructuring, async/await and other ES6+ forms that CLAUDE.md names

**File:** `src/maxpat/code_validation.py:738-745` (`_JS_ES6_PATTERNS`)
**Issue:** CLAUDE.md's js rule lists "no const/let, arrow functions, template literals, classes, **destructuring**, default parameters or **async/await**". The lint covers only the first six forms. Probe: `async function f() { var {a, b} = o; await g(); for (var x of y) {} var z = [...q]; }` with `engine="js"` produces no ES6 error. The Legacy Engine rejects all of these, and write-time validation now gives a false sense of coverage.
**Fix:** Add patterns, all run on the mask: `\basync\s+function\b`, `\bawait\s+[\w$(]`, `\b(?:var|let|const)\s*[\[{]` (destructuring), `\bfor\s*\(\s*(?:var|let|const)?\s*[\w$]+\s+of\b`, `\.\.\.[\w$\[({]` (spread/rest) and `\*\*`.

### WR-03: `write_js` defaults to `engine=None`, so the default js workflow never receives ES5 errors

**File:** `src/maxpat/hooks.py:1112-1151`, `1093-1096`
**Issue:** When `write_js(code, path)` runs, no `.maxpat` references the new file yet, so `_js_engine_for` returns None and every ES6 form shrinks to one `info`. The docstring admits this ("pass the engine to get ES5 errors"). However, `.claude/skills/max-js-agent/SKILL.md` (lines 52, 108-111) and `severity-contract.md` still document `write_js(code, path)` and `validate_js(code)` without `engine`. In the documented default flow (`js` is the default object), the new lint therefore stays at info level and agents will not act on it.
**Fix:** Update the max-js-agent SKILL.md and BOUNDARIES.md calls to `write_js(code, path, engine="js")` / `validate_js(code, engine="js")`, or make `write_js` fall back to `"js"` when the scan returns None, since js is the project default.

### WR-04: `reorder_genexpr_declarations` moves executable statements when a declaration is missing its `;`

**File:** `src/maxpat/codegen.py:125-219`
**Issue:** The statement splitter ends statements only at `;` or `{`. In `x = in1;\nParam g(1)\nout1 = x*g;\n`, the decl statement therefore swallows `out1 = x*g;`, and the whole piece moves above `x = in1;`:
`'Param g(1)\nout1 = x*g;\n\nx = in1;\n'`. The old line-based reorder moved only the decl line. The rewrite changes statement order, and it moves the missing-semicolon site, so Check 2's line number and the user's mental map no longer match the source they wrote.
**Fix:** Before reordering, refuse to move (return `code` unchanged) any decl statement whose masked text contains a newline at paren depth 0 followed by a non-decl token. A cheaper rule: only move decl statements where `st.terminated` is True and the text after the closing `)` of the last item is only `;`.

### WR-05: `code_validation` imports five private helpers from `genexpr_parse` and duplicates its traversal

**File:** `src/maxpat/code_validation.py:19-32`, `459-490` (`_assignment_records`)
**Issue:** `_find_assign`, `_for_parts`, `_paren_content`, `_split_top` and `_strip_prefixes` are private names used across a module boundary. `_assignment_records` also re-implements the `assigned_names` walk; its docstring says it is "sourced exactly like" it. The module docstring says genexpr_parse exists to end the "three regex copies that disagreed". This adds a second copy of the assignment traversal that can drift from the first, so Check 11/12 and Check 14 would then see different assignment sets.
**Fix:** Have `genexpr_parse` expose one public `assignments(code) -> list[(names, op, rhs, line)]`, build `assigned_names` on top of it, and import only public names in `code_validation`.

## Info

### IN-01: `assigned_names` drops inner targets of chained assignments

**File:** `src/maxpat/genexpr_parse.py:419-500`
**Issue:** `c = d = 2;` records only `c`, so `x = pi = 3;` or `y = gain = 0;` (with `gain` a Param) escape Checks 11 and 12.
**Fix:** In `_lhs_names`, loop over the RHS while `_find_assign` keeps finding a depth-0 `=`.

### IN-02: The reorder output mixes line endings and leaves trailing whitespace

**File:** `src/maxpat/codegen.py:219`
**Issue:** The separator is a hard-coded `"\n"` even for CRLF input (`...Param g(1);\r\n\nx = in1;\r\n`). Removing a decl from the middle of a line leaves trailing spaces (`'x = in1;  \n'`).
**Fix:** Detect `\r\n` in the input and use it for the separator. When `kept` is non-blank, `rstrip(" \t")` it.

### IN-03: The engine scan matches by stem only and misses `js name.with.dots`

**File:** `src/maxpat/hooks.py:931-941` (`_js_names_file`)
**Issue:** Any `js foo` box in the project marks every `foo.js` anywhere under `patches/<project>/` as js, which is a cross-folder collision. Also, `js my.lib`, which MAX resolves to `my.lib.js`, gives `Path("my.lib").stem == "my"`, so it never matches. Separately, `engine` is not validated: a typo such as `"JS"` or `"V8"` silently drops to the unknown-engine info.
**Fix:** Compare `ref` (adding `.js` when the suffix is not `.js`) against `path.name`. Normalize `engine` with `.lower()` and reject unknown values.

### IN-04: Silent catch-alls can disable all lint and reorder with no signal

**File:** `src/maxpat/genexpr_parse.py:257`, `497`; `src/maxpat/hooks.py:1006`, `1014`; `src/maxpat/code_validation.py` (`_lint_genexpr` try)
**Issue:** If `_statements_from` ever raises, `statements()` returns `[]`. Checks 10-16, the reorder and the Param parse then all silently become no-ops, and `# pragma: no cover` hides this from coverage.
**Fix:** Emit a `warnings.warn` (or an `info` ValidationResult) from the guard so a parser fault is visible.

---

_Reviewed: 2026-10-15_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: quick_
