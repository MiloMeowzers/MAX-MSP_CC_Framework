---
quick_id: 261022-ud6
work_package: WP4 (codegen + device builders)
status: complete
branch: worktree-agent-ac6c591065892e1d6
plan_head_before: 8ddcdc49
commits: 8
actuals:
  tokens: 34000   # chars/4 over the realized diff (135 kB)
  commits: 8
tests: "6407 passed, 5 xfailed, 1 xpassed (python3 -m pytest -q; baseline 6287 passed). Run on Python 3.14 -- no 3.10 interpreter on this machine; code avoids 3.11+ syntax"
---

# WP4 Summary: codegen + device builders (review-codegen.md, Q40 IN-01..04)

All findings in review-codegen.md are fixed or handed off with an exact patch. Every fix was written test-first: the new tests failed on 8ddcdc49 and pass now. No `patches/**` file was edited.

## Finding -> fix

| ID | Status | How | Commit |
|---|---|---|---|
| BL-01 | fixed | `build_m4l_device` looks up the top-scope `plugin~`/`plugout~`/`midiin`/`midiout`/`live.thisdevice` and reuses each one it finds. Two of one name raise `ValueError` before any box is built. The pass-through only feeds output inlets that nothing feeds yet, so a `plugin~ -> fx -> plugout~` chain never gets a dry path. A source into an inlet another source already feeds raises; the same cord again is a no-op. A reused `live.thisdevice` never fans out: it extends an all-bang `t` through `replace_box_safe`, or moves its existing cords onto a new `t b ...`. New critic hook: `m4l_device.find_duplicate_device_io` / `duplicate_device_io_results` (rule `duplicate_device_io`, warning). | d5dfaa1c |
| WR-01 | fixed | `resolve_param_specs(existing_longnames=, existing_shortnames=)`: a name equal to an existing `parameter_longname` raises. So does an explicit short name equal to an existing one, or two equal explicit short names. Auto short names avoid the existing ones (`Amount2`). | d5dfaa1c |
| WR-02 | fixed | `diagnose._rank_no_such`: with a db, the six tied "No such object" rows are ranked by facts. PD name -> PD row; `inlet~`/`outlet~` -> port row; stale bach names -> bach row; an effective restriction -> RNBO/Gen row; a package object -> package row; an unknown name -> abstraction row. A core object with no restriction gets no single-fix proposal. `.claude/commands/max-diagnose.md` step 5 says this. | a77f4f0b |
| WR-03 | fixed | Check 5 now runs on statements and skips function bodies, so the gen.maxhelp form no longer errors and no longer blocks a save. A function after a statement is an **error** (Max user guide: "functions must be declared before all statements"). A function after a declaration only is a **warning**. `reorder_genexpr_declarations` (used by `add_gen`) emits functions, then declarations, then statements. It never hoists a Param above a function, and it leaves the C74 form byte-identical. Every shipped Gen codebox that has functions (C74 bundle + installed packages) is F+D+S+. | 5f6e2690 |
| WR-04 | fixed | New `genexpr_parse.BUILTIN_CONSTANTS` = Q22's 13 names + `phi` + every upper-case alias (PI, TWOPI, ..., PHI, E), used by Checks 11/14. `CONSTANTS` stays the 13 lower-case names because `dsp_sim.genexpr_interp` asserts it. | 5f6e2690, 2f6fc373 |
| WR-05 (E8 builder half) | fixed, EXPERIMENTAL | `add_rnbo` builds a newobj `rnbo~` with `max(1, #in~)` inlets and `#out~ + 1` outlets (the last one `list`). It also writes `inletInfo`/`outletInfo`, sets inner `classnamespace "rnbo"`, and writes params as `param <name> <initial> @min @max`. Golden fixture `tests/fixtures/expected/rnbo_box_shapes.json` holds 7 MAX-saved shapes from the Max 9.2 RNBO help patches; the rule holds for 616 of 620 port-only bundle boxes. | 77698dd8 |
| IN-01 | fixed | Check 2 uses statements. It warns on an unterminated statement, or inside a statement where a complete-looking line (paren depth 0, no trailing operator) is followed by a line that starts a new statement. Operator continuations (bassoon 507/518), Allman headers and brace-less two-line `if` are no longer flagged. Check 4 uses `param_items`, so `Param g(max(1,2), min=0, max=10)` keeps its range and every name of a comma list is checked. | 5f6e2690 |
| IN-02 | fixed (codegen) / handoff (hooks) | `generate_gendsp` writes codebox `numinlets: max(1, n_in)`. `hooks._edit_gendsp_in_place` -> WP2 (below). `add_gen`'s codebox is unchanged: the gen-synth golden fixes its bytes. | 9f03f4e9 |
| IN-03 | fixed | `validate_js` / `detect_js_type` match `inlets`/`outlets` only bare or as `this.inlets`, never `numinlets`, and never `inlets ==`. | 9f03f4e9 |
| IN-04 | fixed | `generate_n4m_script` passes the `addHandler` selector through `json.dumps` (`node --check` test). | 9f03f4e9 |
| IN-05 | fixed | A message's `set <name>` is rewritable only when the box cords into a declarer, a buffer user or a waveform~, in the same patcher. Otherwise it counts as a reference (report-only). | 28f5a1f6 |
| IN-06 | fixed | New dials get `annotation` / `annotation_name`. `info_text` defaults to `presentation`, so the gen-synth golden is unchanged. When a new box overlaps a pre-existing one, all new boxes shift right together. | d5dfaa1c |
| Q22 tabs (locked) | fixed (API) | `validate_genexpr(code, db, *, original=None)`. Tab lines found verbatim in `original` give one **warning**; new tab lines stay an **error**. `original=None` means generated code, where every tab is an error. Callers must pass `original` (handoff below). | 5f6e2690 |
| Q22 spec gap | fixed | Checks 2, 4 and 5 use the parser. Checks 6 and 9 were checked against functions, Allman headers and comments: no false positive found, so they stay as they are. | 5f6e2690 |
| Q40 dup-I/O spec gap | fixed (check) / handoff (critic wiring) | See BL-01. | d5dfaa1c |
| Q40 IN-01 | fixed | `export_amxd` warns (UserWarning) when an explicit kind disagrees with `detect_m4l_device_type`; an unknown kind still raises first. | d5dfaa1c |
| Q40 IN-02 | fixed | Duplicate explicit short names raise. An explicit Int type with non-integral bounds or a span over 255 **warns**: explicit keys still win, and an existing test pins that. | d5dfaa1c |
| Q40 IN-03 | handoff -> WP3 | `m4l_critic.py` is not WP4's file. Patch is below. | -- |
| Q40 IN-04 | fixed | The delegation test spies on `add_m4l_device` (`mock.patch.object(..., autospec=True, side_effect=...)`). `build_amxd` raises `ValueError` unless `meta` is None or an int in `[0, 2**32)`; bools are rejected. | d5dfaa1c |

Also: 7c480d1b updates the `add_gen` comment (functions-first reorder).

## Tests added / changed

- New: `tests/test_m4l_device_reuse.py` (29), `tests/test_genexpr_wp4.py` (47), `tests/test_rnbo_shape.py` (13), `tests/test_codegen_wp4.py` (12), `tests/test_m4l_polish_wp4.py` (6), plus `TestNoSuchObjectRanking` in `tests/test_diagnose.py` (13).
- Updated tests whose old behaviour the findings superseded, each with a comment:
  - `test_m4l_device.py`: source-text test -> mock spy.
  - `test_genexpr_lint.py`: `TWOPI` is now flagged.
  - `test_genexpr_parse.py`: a function after a statement now moves to the top; the RNBO param text uses the positional form.
  - `test_rnbo.py`: newobj shape and MAX inlet counts.
  - `test_m4l_polish.py`: `_buffer_users_patch` now cords its `set` message into groove~.
- Validator sweep (`validate_genexpr` on every committed codebox at any depth in patches/** and patterns/**, `validate_code_file` on every committed .js):
  - Before: 43 findings, 3 errors. After: 41 findings, 3 errors (the same allowlisted tape-wobble pi/twopi errors and the fx-genfail fixture).
  - The only change is that the two bassoon semicolon false positives are gone. There are no new findings and the JS results are unchanged.
- Max 9.2 bundle sweep (Gen codeboxes outside rnbo~):
  - Removed: the gen.maxhelp and jit.gl.material Check 5 false errors, and 8 continuation-line semicolon false positives.
  - Added: Param range warnings on comma-list Params (true positives).
- `find_duplicate_device_io` over every committed .maxpat: 0 hits.

## Handoffs

- **WP3 (critics):**
  - (1) Call the duplicate-I/O hook from `review_m4l`'s top scope: `from src.maxpat.m4l_device import duplicate_device_io_results; results.extend(duplicate_device_io_results(patch_dict))` (rule `duplicate_device_io`, warning). Add it to `Q40_RULES` if that tuple is kept.
  - (2) Q40 IN-03 in `_check_param_range`: in the `else` branch, `continue` unless `valueof.get("parameter_initial_enable")` is truthy, before testing `parameter_initial`.
- **WP2 (patcher/save, hooks, builders.py):**
  - (1) IN-02 in `hooks._edit_gendsp_in_place`: write codebox `numinlets` as `max(1, n_in)`.
  - (2) Tabs decision wiring: `validate_code_file` on a file read from disk should pass `original=code`. `write_gendsp` should pass `original=<previous on-disk codebox code>`. The save gate (`_blocking_findings`, or Layer 5 via WP1) should pass each codebox's baseline code as `original`.
  - (3) Update the `Patcher.add_m4l_device` docstring for BL-01 reuse, WR-01 refusal, info text and the overlap shift. Optionally expose `info_text=` (now a `build_m4l_device` kwarg).
- **WP1 (validation):** Layer 5 (`validation.py` `_check_codeboxes`, or similar) should accept per-codebox originals and forward them to `validate_genexpr(original=...)`. Without that, loaded codeboxes with tabs still report an error.
- **WP5 (dsp_sim):** `GEN_CONSTANTS` has only PI/TWOPI/HALFPI as upper-case aliases. Consider the rest (INVPI, E, PHI, LN2, ...) from `genexpr_parse.BUILTIN_CONSTANTS`. Its `assert set(_LOWER_CONSTANTS) == set(CONSTANTS)` was the reason `CONSTANTS` was kept at 13.

## Doc impacts for WP8 (CLAUDE.md / TECHNICAL.md / references not edited here)

- CLAUDE.md "Never use GenExpr built-in constant names": add `phi` and "and their upper-case aliases (PI, TWOPI, PHI, E, ...)".
- CLAUDE.md Gen~ / genexpr-rules.md: codebox order is functions, then declarations, then statements. A function after a statement is a validator error; add_gen reorders to this form.
- CLAUDE.md / genexpr-rules.md tabs rule: an error in generated or edited code, a warning for tabs already in a loaded codebox (`validate_genexpr(original=...)`).
- CLAUDE.md M4L section and TECHNICAL.md:
  - `add_m4l_device` reuses existing device I/O and never adds a second pass-through.
  - It refuses taken param names and short names.
  - Dials get info text when `presentation=True`.
  - `export_amxd` warns on a kind mismatch.
  - New critic rule `duplicate_device_io` (once WP3 wires it).
- TECHNICAL.md line 514 (RNBO duplicate params "`@name`"): the builder now writes the positional `param <name> ...`, and the critic already parses both forms. CLAUDE.md RNBO section: builder shape per the golden fixture.
- severity-contract.md: new warnings (function after a declaration, loaded-codebox tabs) and a new error (function after a statement).
- troubleshooting.md: none. `/max-diagnose` behaviour is documented in `.claude/commands/max-diagnose.md` (edited).

## Needs confirmation in MAX / Live

1. **WR-03:** that the order functions -> Param -> statements compiles in MAX's gen~ (it is the bundle's own form), and that a function after a statement fails (the error is based on the user guide). Record the result in genexpr-rules.md.
2. **WR-05:** open `generate_rnbo_wrapper(params=[...])` output in MAX. Check: rnbo~ compiles, has 2 inlets and 3 outlets for 2x2, and `param g 0.5 @min 0 @max 1` sets its initial value. RNBO stays EXPERIMENTAL until then.
3. **BL-01 / IN-06:** part of the pending Q40 Live check. Build a device with two `add_m4l_device` calls and confirm in Live one pass-through (no +6 dB), one init chain, and that the dial info text shows.
4. **IN-05:** run polish on a device with a `set name` message that feeds a display, and confirm the display text is unchanged.

## Deviations

- WR-04: the review asked to add the aliases to `CONSTANTS`. A new `BUILTIN_CONSTANTS` holds them instead, because a WP5-owned assert pins `CONSTANTS` (Rule 3, blocking).
- Q40 IN-02: the Int-type consistency problems warn instead of raising, so the existing "explicit keys always win" contract and its test still hold.
- `add_gen`'s codebox `numinlets` is not changed: `tests/test_m4l_gen_synth_golden.py` forbids changing the fixture.

## Self-Check: PASSED

- Commits d5dfaa1c, a77f4f0b, 5f6e2690, 77698dd8, 9f03f4e9, 28f5a1f6, 7c480d1b, 2f6fc373 are on the branch.
- The new test files and `tests/fixtures/expected/rnbo_box_shapes.json` exist.
- The full suite is green.
