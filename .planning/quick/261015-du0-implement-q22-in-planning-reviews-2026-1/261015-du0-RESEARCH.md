# Quick 261015-du0 (Q22): GenExpr parser, codebox lint, js ES5 lint - Research

**Researched:** 2026-10-15
**Domain:** In-repo Python validators (`src/maxpat/code_validation.py`, `codegen.py`, `rnbo.py`, `hooks.py`)
**Confidence:** HIGH (every claim comes from code read this session or a scan run this session)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
**js engine detection (ES5 lint scope)**
- Add an engine parameter to `validate_js` (e.g. `engine: str | None`). ES6 syntax (const, let, `=>`, template literals, class, default parameters) is an error only when engine is `js`/`jsui`; never for `v8`/`v8ui`.
- For standalone `.js` file validation (hooks.py path), scan `.maxpat` patches in the same project directory for a `js`/`jsui`/`v8`/`v8ui` box whose text names the file. ES5 errors only when a js/jsui box references it. Unreferenced or v8-only files: no ES5 errors (a note at most).
- Patch-level validation (where the referencing box is known) passes the box's engine directly.

**tanh feedback-path detection**
- Flag `tanh(...)/tanh(` (normalize-by-tanh-of-drive) as an **error** when the codebox declares any `History` or `Delay` (feedback state exists); otherwise a **warning**. No dataflow analysis.

**Committed patches that trip new checks**
- Follow fix-plan rule 3: fix false positives in the checker; allowlist true positives with a written reason (tape-wobble obj-3 `pi`/`twopi` assignment must be reported, then allowlisted) and list every allowlist entry in SUMMARY.md. New checks ship at the severities in the spec table.

### Claude's Discretion
- Parser module location/name and API shape.
- Allowlist mechanism (reuse an existing allowlist if one exists in the critics/validation code).
- How the de-hoist warning ("local alias in a Param-only expression without `History one(1)`") is detected heuristically.

### Deferred Ideas (OUT OF SCOPE)
None listed in CONTEXT.md. Per fix-plan rule 7 (don't widen scope), these stay out: G3's "walk all codeboxes in a .gendsp" (`hooks.py` still checks only the first codebox), deleting the dead `_check_genexpr_io_syntax` / `_check_genexpr_delay_usage` (S9), and adding js file reading to `validate_patch`.
</user_constraints>

## Fix-plan rules (copy into PLAN.md verbatim)
Source: `.planning/reviews/2026-10-11-fix-plan.md:19-31`, read this session.
1. Read the referenced finding IDs in the review report first; they contain the evidence and the expected fix.
2. Write each regression test **first**. It should reproduce the finding (red) before you fix it (green).
3. **Never edit committed patch files** (`patches/**/*.maxpat|.gendsp|.maxhelp|.js`). They are user-confirmed baselines, and the integration tests depend on them. If one produces a new finding:
   - false positive: fix the checker;
   - true positive in a committed patch: allowlist it with a written reason and list it in SUMMARY.md.
4. Run `python3 -m pytest -q` before and after.
   - Allowed baseline failures until Q3 lands: the 3 `test_review_patch_no_blockers` cases (minitaur, physics-composition, timestretch).
   - From Q3 onward the suite must be fully green.
5. Never `git stash`. Never `git add -A` or `git add .`. Stage explicit paths only.
6. Code must work on Python 3.10.
7. Don't widen scope. If the fix needs a decision the report doesn't make, stop and ask with multiple-choice options.
8. Edit CLAUDE.md, skills or TECHNICAL.md only where the task says to. List any other doc impact in SUMMARY.md.
9. In SUMMARY.md, flag anything that needs the user to confirm in MAX or Live.

## Summary

**Baseline (HEAD 83e38341, run this session):** `python3 -m pytest -q` gives **3982 passed, 1 xfailed, 1 xpassed** in 78 s, so the suite is fully green. The local interpreter is **Python 3.14.2** and no 3.10 is installed, so 3.10 compatibility has to be checked by reading the code (see Pitfall 8).

**All bugs reproduce red today** (run this session against the current code):
- G2: `parse_genexpr_io("// mix in4 and out3\nout1 = in1;")` returns `(4, 3)`.
- G1a: a `/*\nHistory h(0);\n*/` block gets hoisted out of the comment and becomes live.
- G1b: a multi-line `Param g(0.5,\n  min=0, max=1);` is split into a syntax error.
- G4: `Param freq(440, min=20);` gives `max: 1.0`. `Param g(0.5) ;` gives `[]`. `samplerate*0.25` raises `ValueError`.
- js: `validate_js("// inlets = 2\n// outlets = 1\nconst a = () => 1;\nfunction bang(){}")` returns only `info: Handler functions found`. The comment satisfied the inlets/outlets check and the ES6 passed.

**Committed-corpus impact is small.** The new **error**-level checks fire on exactly one committed codebox: **tape-wobble obj-3**, `pi`/`twopi` assignment (confirmed). Every other hit is a warning or info. Nothing fires on any committed `.js` file.

**Primary recommendation:** Build one offset-preserving "mask" tokenizer in a new `src/maxpat/genexpr_parse.py`. It blanks comments and string contents to spaces and keeps newlines, so offsets and line numbers map 1:1 onto the original text. A statement splitter that tracks paren and brace depth runs on top of the mask. Every caller does its regex work on the mask and slices the **original** text by the spans. To keep the tape-wobble error from turning `test_validate_patch_no_errors` red, add a new `tests/validate_error_allowlist.json` with the same hygiene as the review allowlist.

## Code map (read this session)

| Function | Location | Callers |
|---|---|---|
| `parse_genexpr_io` | `codegen.py:23-43`: bare `re.findall(r"\bin(\d+)\b", code)` on raw code | `builders.py:956` (add_gen), `codegen.py:190` (generate_gendsp), `critics/dsp_critic.py:155`, `__init__.py:48` export, tests `test_codegen.py:27-75,585` |
| `reorder_genexpr_declarations` | `codegen.py:94-166`: line-based, `startswith(_DECL_PREFIXES)` | `builders.py:952` only (auto-applied in `add_gen`). Tests `test_codegen.py:808-890`, including the exact-string assertion `result == code` when no reorder is needed |
| `parse_genexpr_params` | `rnbo.py:97-133`: pattern `r"Param\s+(\w+)\(([^)]+)\);"`, defaults `min_val = 0.0` / `max_val = 1.0`, `float(parts[0])` | No `src` caller. Exported (`__init__.py:64`) and documented in `.claude/skills/max-rnbo-agent/SKILL.md:50,65`. Tests `test_rnbo.py:190-220` (explicit min/max only, so returning None for missing bounds keeps them green) |
| `validate_genexpr` | `code_validation.py:79-379`: Checks 1-9. Check 6 already strips `//` and `/* */` with regexes; Checks 2/5/9 are line-based | `builders.py:963-967` (errors become `warnings.warn`), `validation.py:1458-1530` `_validate_embedded_genexpr` (Layer 5: every codebox in a gen-scope inner patcher, message prefix `"{container} '{box_id}' codebox: "`), `hooks.py:984` (.gendsp, first codebox only). Tests: `test_code_validation.py` (many), bundle oracle `:610-649` (only asserts no `"Unknown GenExpr operator"` errors) |
| `validate_js` | `code_validation.py:382-449`: `re.search(r"inlets\s*=\s*(\d+)", code)` on raw code | `hooks.py:991` only (via `validate_code_file`, reached by `write_js` at `hooks.py:1007-1041`). Tests `test_code_validation.py:366-420` |
| `detect_js_type` | `code_validation.py:510-525` | `hooks.py:987` |

- No patch-level js validation exists anywhere. `validation.py` and the critics never read `.js` files, and the only js-name list is `structure_critic.py:60`. So the "patch-level passes engine directly" decision currently has **no call site**. Add the parameter and the hooks path, and don't build a new patch-level js reader (scope).
- `add_js` (`builders.py:1277`) always emits `js <filename>` and does not validate. `write_js` is normally called **before** the `.maxpat` that references the file is saved, so at write time the reference scan finds no box and ES5 errors cannot fire. Optional mitigation that stays in scope: `validate_code_file(path, engine=None)`, where an explicit engine overrides the scan.
- Validator levels are `error|warning|info|fixed` (`validation.py:124`). There is **no `note` level** (that word belongs to the critics, `severity-contract.md:13`), so map the spec's "note" (`else if`, 2-arg `peek`) to **`info`**.

## Committed-corpus scan (throwaway script in the scratchpad, run this session)

The scan covered 68 codeboxes across `patches/**/*.maxpat|.gendsp|.maxhelp`, recursing into gen~, mc.gen~, `p` and `data.patcher`, plus 21 `patches/**/*.js` files.

| Check (spec severity) | Committed hits | Action |
|---|---|---|
| Tab (error) | **0** | none |
| Constant assignment (error) | **tape-wobble/generated/tape-wobble.maxpat, top-level gen~ `obj-3`, codebox `obj-3`: L42 `pi = 3.14159265358979;`, L43 `twopi = 2.0 * pi;`** (codebox also declares `Delay del_L(4096)`) | Allowlist (true positive). Reason: the constant wins silently and the literal equals the built-in, so the code is harmless; the patch is frozen. ValidationResult `path` = `""`, message prefix `gen~ 'obj-3' codebox:` |
| Param also an assigned local (error) | 0 | none |
| Nested / non-literal `for` (warning) | 0. All loops have literal bounds (gong-engine, terrain-cheby, timestretch, reverse-delay, spectraldetector, wormhole, granular*, scala-synth `i = i + 1`). The gong `for` loops at L442/453/473 are inside an `if`, not nested | none |
| De-hoist alias (warning) | stereo-feedback-delay obj-1/obj-2 (`sr = samplerate` → `inc = twopi * mod_rate / sr`); tape-wobble obj-3 ×3 (`f1_inc`, `w0_bump`, `w0_lp` via `sr`/`twopi`) | Warnings only, no test impact. Report in SUMMARY |
| `tanh(…)/tanh(` (error if History/Delay, else warning) | 0 in `patches/`. **`patterns/gen/gain/soft-clipper.gendsp` obj-2**: `out1 = tanh(in1 * drive) / tanh(drive)` with no History, so a warning. Known false negative: kicksynth obj-20 `tanh(drive*sig) / max(tanh_drive, 0.001)` (codebox has History) does not match the literal pattern. **Do not widen the pattern**: kicksynth is a calibration project and would go red | Report the pattern-library hit as doc impact in SUMMARY |
| `else if` (note→info) | 0 | none |
| 2-arg `peek` (note→info) | scala-synth-voice.maxpat gen~ obj-5 / codebox obj-2 L26 `phase = peek(phases, i);` (L29 also has a 2-arg `poke`, which is not in the spec) | info only |
| js ES6 in js/jsui-referenced file (error) | **0**. All 20 referenced files are `js` (no jsui/v8/v8ui boxes anywhere in `patches/`) and ES5-clean. `barnett-dbap/test-results/preflight_motion.js` is unreferenced | none |
| js commented `inlets`/`outlets` | 0 | none |

**Max 9.2 bundle oracle (146 Cycling '74 codeboxes plus `.genexpr` files, which compile in MAX):**
- tabs in **74**, `else if` in **100**, 2-arg `peek` **192**, non-literal `for` **6**, nested `for` **2**;
- `"strings"` in **21** (`Buffer wind("window")`, `require("lib")`, `interp="none"`, `boundmode="wrap"`);
- `/* */` in 8 (`\r\n` line endings in `bp.AD2`);
- comma multi-assign (`a, b = peek(...)`);
- multi-line call args;
- user function definitions (`stkr.waveshaping.genexpr`).

The tab=error severity therefore flags code that compiles in MAX. It is locked by spec and project CLAUDE.md, and the bundle tests only assert no crash plus no `Unknown GenExpr operator`, so nothing goes red. Note it in SUMMARY.

## Architecture

### Parser module: `src/maxpat/genexpr_parse.py` (new, stdlib only)
```python
# Shape (Claude's discretion). Pure functions, no DB import (avoids the
# code_validation <-> validation circular-import dance).
def mask(code: str) -> str:
    """Same length as code. // and /* */ comment chars -> ' ' (newlines kept);
    string-literal contents -> ' ' (quotes kept). Unterminated /* or " runs to EOF."""
@dataclass(frozen=True)
class Stmt:
    start: int; end: int      # span in ORIGINAL text, end includes ';' if present
    text: str                 # masked text of the statement (comment-free)
    depth: int                # brace depth at statement start (0 = top level)
    line: int                 # 1-based line of first non-space char
    kind: str                 # "decl" | "assign" | "expr" | "header" (if/for/else/func `{`)
def statements(code: str) -> list[Stmt]:
    """Split the mask on ';' at PAREN depth 0 (so for(;;) headers stay whole),
    and on '{' / '}' (headers end at '{'). A trailing statement without ';'
    ends at '}' or EOF (bundle: `require("moogLadderFilter")`)."""
def declarations(code) -> list[tuple[str, list[str], Stmt]]   # (Param|History|..., names, stmt)
def split_args(s: str) -> list[str]                            # top-level commas, paren-aware
def parse_param(stmt) -> list[dict]                            # name/default/min/max, None when absent/non-literal
def assigned_names(code) -> dict[str, list[int]]              # name -> lines (see Pitfall 4)
def io_counts(code) -> tuple[int, int]                         # on mask
```
- **`parse_genexpr_io`**: run `\bin(\d+)\b` / `\bout(\d+)\b` on `mask(code)`.
- **`reorder_genexpr_declarations`**:
  - Fast path: if no depth-0 `decl` stmt follows an `assign`/`expr` stmt, `return code` unchanged (test `test_no_reorder_needed` asserts exact equality).
  - Otherwise, cut each depth-0 `decl` stmt's **original span**, together with the run of whole `//` comment lines directly above it (keeps `test_preserves_comments` and comment association), out of the text.
  - Emit the cut pieces grouped Param → History → Delay → Buffer/Data (existing `_TYPE_ORDER`), then a blank line, then the remainder. A declaration inside `/* */` is masked, so it is never a stmt and stays put (fixes G1a). A multi-line Param is one span (fixes G1b).
- **`parse_genexpr_params`**:
  - Use the declarations from the parser.
  - `default`: `float(arg0)` if it parses, else `None`. Optionally keep the raw text as `default_expr`.
  - `min`/`max`: from kwargs `min\s*=` / `max\s*=` anywhere in args, `None` when absent or non-literal.
  - **Consumer fix needed:** `add_rnbo` (`rnbo.py:268-275`) does `param.get("min", 0.0)`. A present-but-None key returns `None` and would emit `@min None`. Have it skip `@min`/`@max`/`@initial` when the value is None. Without this, the G4 fix regresses a downstream path.
- **`validate_genexpr`**:
  - Compute `m = mask(code)` once.
  - Check 1 counts braces on `m` (fixes braces in comments).
  - Run Checks 2/5/9 on `m.split("\n")`. Their existing `startswith("//")` skips become harmless no-ops, and line numbers are unchanged.
  - Check 6: replace `_strip_line_comments` + `_strip_block_comments` with `m`.
  - Add new checks 10-16 using the parser.
  - **Before/after diff:** dump `validate_genexpr` output for all 68 committed codeboxes before the change and diff it after. Errors must be identical except the two tape-wobble constant errors; warning/info changes must each be explainable.

### New checks: detection rules (all calibrated against the corpus above)
| # | Check | Rule | Level |
|---|---|---|---|
| 10 | Tab | `"\t" in code` (raw; a tab inside a comment still breaks MAX per genexpr-rules.md:105). Report the first few line numbers | error |
| 11 | Constant assignment | Any name in `assigned_names` ∩ {e, pi, twopi, halfpi, invpi, ln2, ln10, log10e, log2e, sqrt2, sqrt1_2, degtorad, radtodeg}, case-sensitive (bundle/scala-synth `TWOPI` is legal). One result per name, message containing the name and line | error |
| 12 | Param assigned | Param names (all comma-listed) ∩ `assigned_names`, excluding the declaration stmt itself | error |
| 13 | Loop shape | `for` header: split its paren content on `;`; the condition's bound must match a numeric literal (`\d+(\.\d*)?`). A `for` whose `{` opens inside another `for` block is nested | warning |
| 14 | De-hoist alias | Fixpoint (this scan produced zero noise): a *derived local* is a name with exactly one assignment, not declared by History/Delay/Buffer/Data, whose RHS identifiers (excluding called names `name(`) ⊆ Params ∪ {samplerate, vectorsize} ∪ constants ∪ derived (literal-only RHS like `RING = 1344000;` counts). Flag a derived assignment whose RHS uses ≥1 derived local **and** ≥1 Param. A `History one(1)` de-hoist (`srs = samplerate * one`) is excluded naturally, because `one` is a History and not in the set | warning |
| 15 | tanh norm | On the mask: `tanh\s*\(` with a balanced paren, then `\s*/\s*tanh\s*\(`. Error if any `History`/`Delay` declaration exists, else warning | error/warning |
| 16 | Notes | `\belse\s+if\b` on the mask; `peek(` whose **positional** arg count (top-level commas, excluding `kw=` args) is 2 | info |

### js (`validate_js(code, engine=None)`)
- Build a JS mask (blank `//`, `/* */`, `'…'`, `"…"`, and template-literal bodies, while recording that a backtick was seen). Run inlets/outlets, handler and `outlet(` checks on the mask (fixes G8 / the R6 tail).
- ES6 patterns on the mask:
  - `\bconst\s+[A-Za-z_$]`
  - `\blet\s+[A-Za-z_$\[{]`
  - `=>`
  - a backtick (detected during masking)
  - `(?<![.\w$])class\s+[A-Za-z_$]`
  - default params: `\bfunction\b\s*[\w$]*\s*\(([^)]*)\)` where group 1 contains `=` not followed by `=`
- `engine in ("js", "jsui")` → error. `"v8"`/`"v8ui"` → nothing. `None` → one `info` ("ES6 syntax found; legal only in v8/v8ui").
- `hooks.validate_code_file`: when `js_type == "js"`, resolve the engine by scanning `*.maxpat` in `path.parent` (committed js files sit beside their patches in `generated/`) and recursing into subpatchers. Match on:
  - `newobj` text tokens[0] ∈ {js, jsui, v8, v8ui} with `Path(tokens[1]).stem == path.stem` (text may carry trailing args: `js foo.js 3`);
  - `maxclass` ∈ {jsui, v8ui} with a `filename` attr.
  - Any js/jsui reference → `"js"`; only v8 references → `"v8"`; none → `None`. Use `io_resolvers.split_box_text` for the text, which is the existing quote-aware tokenizer.

## Allowlist recommendation
- `tests/review_blocker_allowlist.json` is matched only against `review_patch` **critic blockers**. Its `_doc` says "for test_review_patch_no_blockers ONLY", and `review_patch` never calls `validate_genexpr`.
- The tape-wobble error surfaces in **`test_validate_patch_no_errors`** (`tests/test_integration_patches.py`), which has **no allowlist**.
- Add `tests/validate_error_allowlist.json` (`{"_doc":…, "patches": {"patches/tape-wobble/generated/tape-wobble.maxpat": [{"kind": "genexpr_const_assign", "path": "", "box_id": "obj-3", "name": "pi", "reason": "…"}, {…"twopi"…}]}}`).
- Key on (kind, ValidationResult.path, container box id, name), **never the line number**.
- Filter it in `test_validate_patch_no_errors`, and add a liveness test that mirrors `test_review_allowlist_entries_are_live` (file exists, reason non-empty, entry still fires) plus the calibration-project exclusion. tape-wobble is **not** in `_CALIBRATION_PROJECTS`.
- To make keying robust, give the constant-assignment message a fixed shape, e.g. `"Assignment to GenExpr built-in constant 'pi' (line 42) ..."`.
- The save gate is unaffected: `TestRoundTripNoFalseBlocks` compares against the file's own baseline, so the pre-existing error is not "new".

## Common Pitfalls
1. **Strings exist in GenExpr.** `Buffer b("name")`, `require("lib")`, `interp="none"`. A naive `//` stripper eats code after `"http://…"`. Mask strings before comments in a single left-to-right scan, never with sequential regexes. A `//` inside `/* */` and a `/*` inside `//` are both handled by that single scan.
2. **`;` inside `for(;;)` headers** must not split statements. Split only at paren depth 0.
3. **Missing final `;`, `\r\n`, unterminated comment or string.** The tokenizer must never raise. Two bundle sweeps (`test_validation_recursive.py:688`, `test_critics_recursive.py:1050`) assert that `validate_patch`/`review_patch` never raise on all 146 bundle codeboxes. Run them; they are `requires_max`, and Max.app is present.
4. **Assigned-name extraction** must cover:
   - `x =`, `+= -= *= /=`;
   - comma LHS `a, b = peek(...)`;
   - the for-header init `for (i = 0; …)`.

   It must exclude:
   - `== <= >= !=`;
   - kwargs at paren depth > 0 (`min=20`, `interp="none"`);
   - declaration statements.
5. **Reorder exactness:** keep `return code` byte-identical when nothing moves, and slice the original text, never the mask. Otherwise comments vanish from the output.
6. **Error-level noise in `add_gen`:** `builders.py:964-967` turns every error into a `UserWarning`. Tests that use `warnings.simplefilter("error")` (`test_save_gate.py:649,664,790`; `test_save_safety.py:129,388`) would explode if their fixture GenExpr used tabs, constants or `tanh/tanh`. Run the full suite.
7. **Calibration projects must stay clean.** Don't widen the tanh pattern to `/ max(tanh_…` (kicksynth). 2-arg peek in scala-synth stays `info`.
8. **Python 3.10:**
   - No atomic groups `(?>…)` or possessive quantifiers `*+` in `re` (3.11+).
   - No `typing.Self`, `tomllib`, `except*` or PEP 695 generics.
   - `@dataclass(slots=True)` is fine (3.10).
   - Keep `from __future__ import annotations` for `str | None` hints.
   - Python 3.10 cannot be run locally, so review by inspection.
9. **Circular import:** `code_validation` imports `validation.ValidationResult`. Keep `genexpr_parse` dependency-free so `codegen`, `rnbo` and `code_validation` can all import it at module top.

## Tests (one per check, written red-first)
- **`tests/test_genexpr_parse.py` (new):**
  - mask keeps length and newlines;
  - strings and `//` inside strings;
  - `for(;;)` stays one header;
  - multi-line Param is one stmt;
  - never raises on unterminated comment or string.
- **`test_codegen.py`:**
  - G2 repro: `(1, 1)`, not `(4, 3)`;
  - G1a: commented `History` stays in the comment;
  - G1b: multi-line Param moves whole and stays parseable;
  - the existing 6 reorder tests stay green.
- **`test_rnbo.py`:**
  - the three G4 repros (`max is None`, the whitespace-before-`;` case parses, a `samplerate*0.25` default gives `default is None` without raising);
  - `add_rnbo` with a None bound emits no `@min None`.
- **`test_code_validation.py`:**
  - checks 10, 11, 12, 13 (nested and non-literal as two cases), 14, 15 (error with History, warning without), 16 (`else if`, 2-arg peek, and 3-arg peek with kwargs not flagged);
  - de-hoisted `srs = samplerate * one` not flagged;
  - `TWOPI` not flagged.
- **`test_code_validation.py` (js):**
  - ES6 forms parametrized ×6 → error at `engine="js"`, nothing at `"v8"`, info at `None`;
  - `// inlets = 2` is not a declaration;
  - ES6 inside a string or comment not flagged.
- **hooks:**
  - a `tmp_path` project with `x.maxpat` (`js x.js`) and an ES6 `x.js` → error;
  - same with `v8 x.js` → no error;
  - unreferenced → info.
- **Integration:**
  - the tape-wobble allowlist filter;
  - allowlist liveness and reason test.

**Commands:** quick: `python3 -m pytest -q tests/test_genexpr_parse.py tests/test_code_validation.py tests/test_codegen.py tests/test_rnbo.py tests/test_integration_patches.py`. Full: `python3 -m pytest -q` (≈80 s, baseline 3982 passed / 1 xfailed / 1 xpassed).

## Open Questions (for SUMMARY, not blockers)
1. **Tab = error vs the bundle.** 74 of 146 shipped Cycling codeboxes contain tabs. The severity is locked by spec and project CLAUDE.md, so ship it as specified and note the evidence in SUMMARY.
2. **`patterns/gen/gain/soft-clipper.gendsp` teaches `tanh(x*drive)/tanh(drive)`.** It now gets a warning. `patterns/` is not under the rule-3 freeze, but editing it widens scope, so list it as doc impact.
3. **`write_js` timing.** ES5 errors never fire at write time when the patch doesn't exist yet. The optional `engine=` override on `validate_code_file` mitigates this; the planner decides.
4. **Doc impact.** TECHNICAL.md:436-449 lists the `validate_genexpr` / `validate_js` checks, and `severity-contract.md:103` says `validate_js` is report-only. Rule 8 says to edit them only if the task says so, so list them in SUMMARY.

## Sources
- Code read this session: `code_validation.py` (full), `codegen.py:1-180`, `rnbo.py:90-140,190-300`, `hooks.py:920-1041`, `validation.py:118-148,1458-1530`, `builders.py:935-975,1277-1330`, `tests/test_integration_patches.py:1-260`, `tests/review_blocker_allowlist.json`, `tests/test_codegen.py:805-900`, `tests/test_rnbo.py:190-225`, `tests/test_doc_signatures.py:665-725`, `.claude/skills/references/genexpr-rules.md:92-114`, `severity-contract.md:13-103`.
- Scans: scratchpad `scan.py`, `dehoist.py`/`dehoist2.py`, `jsscan.py`, `bundle.py` (against `patches/`, `patterns/gen`, and `/Applications/Max.app/Contents/Resources/C74`).
- Baseline: `python3 -m pytest -q` at 83e38341.

**Valid until:** the next commit that touches `code_validation.py`, `codegen.py`, `rnbo.py` or `patches/`.
