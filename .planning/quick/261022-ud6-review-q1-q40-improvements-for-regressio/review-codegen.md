---
area: codegen + device builders
reviewed: 2026-10-22
range: 0f96a6f1..HEAD (8ddcdc49)
files_reviewed_list:
  - src/maxpat/m4l_device.py
  - src/maxpat/m4l_polish.py
  - src/maxpat/rnbo.py
  - src/maxpat/codegen.py
  - src/maxpat/code_validation.py
  - src/maxpat/genexpr_parse.py
  - src/maxpat/diagnose.py
  - src/maxpat/testing.py
  - src/maxpat/externals.py
  - src/maxpat/ext_templates.py
  - src/maxpat/hooks.py (write_gendsp, _edit_gendsp_in_place, write_js, validate_code_file)
  - src/maxpat/builders.py (add_gen, add_m4l_device, add_m4l_gen_synth)
  - src/maxpat/critics/m4l_critic.py (Q40 checks, as they apply to builder output)
findings:
  blocker: 1
  warning: 5
  info: 6
status: issues_found
---

# Code generation + device builders: Q1–Q40 regression review

Every finding below was reproduced by running code. Scratch scripts are in `/private/tmp/claude-501/rv/`. No source, test or patch file was modified.

## What was run

- **Validator sweep.** I ran `validate_genexpr` on every codebox in `patches/**/*.maxpat|.gendsp|.maxhelp` and `patterns/**`, at any depth. I ran `validate_code_file` on every committed `.js`.
  - Result: 3 errors and 36 warnings. The 3 errors are tape-wobble `pi`/`twopi` (allowlisted under Q22) and the deliberate `max-bridge/fixtures/fx-genfail` fixture.
  - None of the warnings is a new false positive from Q22. Two kinds are pre-existing:
    - Check 2 on bassoon lines 507/518. The base commit flags 7 lines there and HEAD flags 2, so this is better than before.
    - The Check 14 de-hoist warnings on FDNverb, kicksynth, stereo-feedback-delay and tape-wobble. These match the CLAUDE.md "no local aliases" rule.
  - JS: no ES5 errors. The only results are 4 warnings: "no handler" and "unknown type".
- **M4L.** I built all three kinds with `add_m4l_device`, plus `add_m4l_gen_synth`, and ran `validate_patch`, `review_patch` and `export_amxd` → `parse_amxd` → `decode_payload` on each.
  - All round-trips are lossless. `q40-live-check.amxd` matches its .maxpat byte for byte.
  - Kind detection is correct, and `meta` is 0. The `ampf`/`meta`/`ptch` layout matches Live 12's three "Max Devices" templates.
- **Writers and generators.** I exercised `write_gendsp` in place (grow from 1 to 3 inputs, then shrink to 0). I ran `generate_js_script` and `generate_n4m_script` through their own validators, and `diagnose_console` on 23 typical console lines. `parse_proven_forms` and `append_proven_form` ran on a copy of the file. All of these behave as documented apart from the findings below.
- Targeted pytest: `test_m4l_device`, `test_code_validation`, `test_genexpr_lint`, `test_codegen` and `test_diagnose` give 386 passed.

---

## BLOCKER

### BL-01: `add_m4l_device` on a patcher that already has device I/O adds a second pass-through, doubling the audio

**File:** `src/maxpat/m4l_device.py:770-800, 818-820, 848-851`

**Defect:** An existing `plugin~` / `midiin` is reused only when `audio_source` / `midi_source` is given (the WR-01 fix). `plugout~`, `midiout` and `live.thisdevice` are never looked up; they are always added. Without a source, an `audio_effect` adds a fresh `plugin~ → plugout~` 0→0 / 1→1 pair beside the existing one.

**Why this is a supported scenario:** the builder already handles patchers that hold device content. It keeps existing presentation UI (WR-03) and banks every parameter already in the patcher (WR-04). Calling it on a patch built from Live's audio-effect template, or calling it a second time to add more parameters, is therefore expected use.

**Failure scenario:** the device ends up with two parallel dry paths into Live, so the signal is +6 dB (doubled). The patcher also gets two `live.thisdevice` boxes and an extra `midiin` (instrument).
- Neither `review_m4l` nor `validate_patch` reports any of this.
- `review_patch` reports only overlapping-box warnings.

**Repro:**
```python
p = Patcher()
p.add_m4l_device("audio_effect", [{"name": "Mix", "min": 0., "max": 1., "default": .5, "varname": "mix_a"}])
p.add_m4l_device("audio_effect", [{"name": "Wet", "min": 0., "max": 1., "default": .5}])
# boxes: plugin~ obj-1, plugout~ obj-2, ..., plugin~ obj-6, plugout~ obj-7, live.thisdevice obj-4 AND obj-9
# cords: obj-1->obj-2 (0,1) and obj-6->obj-7 (0,1)
```

**Fix:** before creating any box, look up the existing `plugin~` / `plugout~` / `midiin` / `midiout` / `live.thisdevice` by name, the same way `existing_in` and `live.banks` already are.
- Reuse each one that exists.
- Add the pass-through cords only when a box was newly created.
- Skip `live.thisdevice` (and its `t b …`) when one exists, and wire the new unbound dials from its outlet 0.

Add a critic check: more than one `plugout~` / `plugin~` / `live.thisdevice` in the top scope is a warning.

---

## WARNING

### WR-01: `add_m4l_device` does not reject a longname already used by a parameter in the patcher

**File:** `src/maxpat/m4l_device.py:757-764` (validation); `_existing_param_longnames` at `:691` is only used for banks (`:873`)

**Defect:** `resolve_param_specs` rejects duplicate names only within the call. `check_varname_collisions` covers varnames (WR-02) but not `parameter_longname`.

**Failure scenario:** the patcher has a dial with longname `Mix` (varname `mix_a`), and the caller adds a spec `{"name": "Mix", "varname": "mix_b"}`.
- The builder accepts it silently.
- `review_patch` then raises a **blocker** (`parameter_uniqueness`: Duplicate parameter_longname 'Mix') plus a `shortname_unique` warning.
- So a new device refuses to save through the gate.
- Push banks list `Mix` only once.

**Repro:** the two calls above with both `name: "Mix"`, followed by `review_patch(p.to_dict())`.

**Fix:** in `build_m4l_device`, before the first box, raise `ValueError` when any `spec["name"]` is in `_existing_param_longnames(patcher)`. Do the same for explicit short names against existing short names. This matches the WR-02 varname check.

### WR-02: `/max-diagnose` proposals pick the first tied row, so `No such object` always gets the RNBO/Gen fix

**File:** `src/maxpat/diagnose.py:377-379` (tie sort by `entry.row`), `:602-611` (proposal uses `matches[0]`)

**Defect:** All six `<objectname>: No such object` rows tie on score. The table order puts "RNBO- or Gen-only name" first, so the proposal is always "Check `lookup(name)["domain"]` …". This happens even when `_facts` has already worked out the real cause.

**Failure scenario** (`diagnose_console(..., db=ObjectDatabase())`):
- `newobj: osc~: No such object`: the fact line says "Pure Data name, MAX equivalent cycle~", but the proposal tells you to check the domain.
- `inlet~: No such object`: the proposal suggests the domain check instead of "use `inlet`".
- `bach.llll2list: No such object`: the proposal suggests the domain check instead of `bach.nth`.

The proposal is the actionable line that `/max-iterate` is fed.

**Fix:** when `db` is present, rank tied entries using the facts. Each check below picks one entry:

| Condition | Entry to rank first |
|---|---|
| `is_pd_object` | the PD entry |
| name in `{inlet~, outlet~}` | the inlet/outlet entry |
| name starts with `bach.` | the bach entry |
| non-empty `get_effective_restrictions` | the RNBO/Gen entry |
| otherwise | the package/abstraction entries |

Alternatively, emit no single-fix proposal when the top tier is ambiguous and the facts don't resolve it.

### WR-03: Check 5 rejects a function defined above a Param, which Cycling '74's own help patch does, and that error now blocks saves (Q7)

**File:** `src/maxpat/code_validation.py:210-235` (Check 5, line-based); `src/maxpat/codegen.py:128-138` (`reorder_genexpr_declarations`); `src/maxpat/hooks.py:602-631` (every Layer 5 error is a gate blocker)

**Defect:** Check 5 treats any line with `=` as the first "expression", including lines inside a function body. Code with a function definition before its `Param` / `Buffer` declarations therefore gets an error.
- This is exactly the shipped `C74/help/.../gen.maxhelp` codebox (`calcSample(position, maximum) { sum = 0; ... }` then `Param harmonic(1); Buffer waveform(...)`).
- On that codebox Check 5 errors "declaration 'Param harmonic' appears after expression on line 4".

Two things make this worse:
- **Ordering conflict:** `add_gen` auto-runs `reorder_genexpr_declarations`, which hoists the Params above the function. The Max 9 user guide (`docs/userguide/content/gen/gen_genexpr.json`, "Defining GenExpr Functions") says "functions must be declared **before** all statements". The rewrite therefore produces the opposite of the documented order. This is not verified in MAX.
- **Pre-existing, but now gating:** both checks also misbehave at 0f96a6f1. Since Q7 the Check 5 error is a save-gate blocker for any new gen~ codebox written in this idiom.

**Repro:** `gen~` whose codebox is `"calc(x) {\n    y = x * 2;\n    return y;\n}\n\nParam g(0.5, min=0, max=1);\nout1 = calc(in1) * g;\n"`. `_blocking_findings(p.to_dict(), is_new=True)` then returns that Check 5 error.

**Fix:**
- Run Check 5 over `genexpr_parse.statements()`. Ignore statements whose `parents` contain `"func"`, and treat a depth-0 function header as neither declaration nor expression.
- In `reorder_genexpr_declarations`, do not move declarations above a leading block of function definitions.
- Confirm the accepted order once in MAX and record it in `genexpr-rules.md`.

### WR-04: Check 11 misses `phi` and the upper-case constant aliases

**File:** `src/maxpat/genexpr_parse.py:35-38` (`CONSTANTS`); used by `code_validation.py:537-544`

**Defect:** The Max 9 Gen operator guide (`docs/userguide/content/gen/gen_common_operators.json`) lists the constants with upper-case aliases: `PI`, `TWOPI`, `HALFPI`, `INVPI`, `E`, `LN2`, `LN10`, `LOG10E`, `LOG2E`, `SQRT2`, `SQRT1_2`, `DEGTORAD`, `RADTODEG`. It also lists `phi` / `PHI`.

Neither `phi` nor any upper-case form is in `CONSTANTS`. `phi` is a very common phase-variable name, and CLAUDE.md says "the constant wins silently".

**Repro:** `validate_genexpr("phi = 0.;\nout1 = in1 + phi;")` and `validate_genexpr("TWOPI = 6.0;\nout1 = in1*TWOPI;")` give no error. `pi = …` errors. (No committed codebox assigns any of these today.)

**Fix:**
- Add `phi`, `PHI` and the upper-case aliases to `CONSTANTS`. That also widens Check 14's `base_names`.
- Add `phi` to the CLAUDE.md "Never use GenExpr built-in constant names" list (a Q16/Q18 doc change) and to `genexpr-rules.md`.
- Sanity-check against the DB: `db.lookup("PI")` and `db.lookup("phi")` both return None today.

### WR-05: The RNBO builder still emits the box shape review E8 flagged; Q26 fixed only the critic half

**File:** `src/maxpat/rnbo.py:232-249, 294-302`

**Defect:** `generate_rnbo_wrapper()` and `add_rnbo` still write the parent box with `maxclass: "rnbo~"` and no `text` (`to_dict` drops it). The other E8 builder points also remain:
- `audio_ins + 1` inlets;
- `param @name … @initial …`.

All 663 MAX-authored rnbo~ boxes are `newobj` + `text "rnbo~"`. CLAUDE.md says a non-UI maxclass gives "invalid attribute maxclass" at load.
- `validate_patch` reports nothing on this shape. Only two "Unterminated signal chain" warnings appear inside.
- This is pre-existing. E8's builder half ("generate MAX's shape; golden fixture") was never scheduled: Q26 took only the critic part.

**Fix:** a follow-up task. Build the parent with `Box.structural("newobj", "rnbo~", …)`, copy the inlet/outlet counts and `classnamespace "rnbo"` from a MAX-saved rnbo~ golden fixture, and use the positional `param <name> <initial> @min @max` form. Until then, keep RNBO marked experimental.

---

## INFO

- **IN-01 (Q22 spec gap; FP):** `code_validation.py:151-184, 197-208`.
  - Check 2 (missing semicolon) and Check 4 (Param range) are still line/regex scans. Only the comment mask is shared, not the Q22 statement parser.
  - Check 2 warns on a multi-line expression continued without parentheses (bassoon.gendsp lines 507, 518). It also warns on an Allman-style function header (`f(x) // helper` then `{`, and the bundle's `calcSample(position, maximum)`).
  - Check 4 cuts `Param g(max(1,2), min=0, max=10)` at the first `)`, then warns "missing min/max".
  - Fix: drive both checks from `statements()` / `parse_params()`.
- **IN-02:** `codegen.py:293` (`generate_gendsp`) and `hooks.py:968` (`_edit_gendsp_in_place`) write a codebox with `numinlets: 0` when the code has no `inN`.
  - MAX-authored codeboxes with no inputs carry 1 inlet: `gen.maxhelp`, `gen~.maxhelp`, `jit.gl.material.maxhelp`, and the MAX-resaved `slice-voice` / `granular-sched`.
  - It is harmless in practice (granular-engine, user-confirmed, has 0), but it diverges from MAX's shape, and Q15 already fixed the same thing for the gen~ parent.
  - Fix: `max(1, n_in)` for the codebox's `numinlets`.
- **IN-03:** `code_validation.py:918, 926`. `inlets\s*=` / `outlets\s*=` have no word boundary, so `var numinlets = 2;` satisfies the "inlets declaration" check. Fix: `(?<![\w$.])inlets\s*=`.
- **IN-04:** `codegen.py:435`. `generate_n4m_script` interpolates the handler `name` raw into `addHandler("{name}", …)`, while Q31 now `json.dumps`-escapes dict names. A selector containing `"` or `\` breaks the script. Fix: `json.dumps(name)`.
- **IN-05:** `m4l_polish.py:281-286, 482-491`. `ensure_m4l_prefixes` rewrites the target of every max-scope `set <name>` message whose name is a rename candidate, whatever the message feeds.
  - Example: `set state, bang` became `set ---state, bang` beside a `pv state`.
  - A `set foo` that sets a message or umenu display then changes visibly.
  - This is per the Q15 spec, so it is only flagged. Fix: rewrite only when the message's cord goes to a declarer or buffer user.
- **IN-06:** `m4l_device.py:824-851`. Builder output trips its own critics.
  - Every dial gets "missing info text". The builder could call `populate_info_text`.
  - The fixed coordinates with `skip_overlap_check=True` (dials at y 100, `live.thisdevice` at (50, 20), `t b …` at (50, 60)) overlap a caller's chain that sits at default positions: overlap warnings in the `audio_source` / `midi_source` repros.

---

## Spec gaps

| Q-id | What's missing |
|---|---|
| Q22 | Only `parse_genexpr_io`, `reorder_genexpr_declarations` and `parse_genexpr_params` fully use the shared parser. `validate_genexpr` uses only its mask: Checks 2, 4, 5, 6 and 9 are still line/regex based (IN-01, WR-03). |
| Q22 (and CLAUDE.md/Q16) | The constant list omits `phi` and every upper-case alias (WR-04). |
| E8 (unscheduled) | Q26 implemented only the RNBO critic half. The builder-shape fix (newobj `rnbo~` with text, inlet counts, `classnamespace`, positional `param`, golden fixture) is in no Q task (WR-05). |
| Q40 "Critic checks for the result" | No check catches duplicated device I/O (two `plugout~` / `plugin~` / `live.thisdevice`) (BL-01). Builder input validation does not cover existing longnames (WR-01). |
| Q40 REVIEW IN-01..IN-04 | Still open; the fix round 8ddcdc49 covered WR-01..04 only. Not re-reported here: explicit kind not checked against contents, explicit type/short_name consistency, `param_range` ignoring `parameter_initial_enable`, `build_amxd` meta range. |
| Q40 "Mark experimental" | Done (module, builder and CLAUDE.md). The Live check (`q40-live-check.amxd`) is still pending; BL-01 and WR-01 are worth fixing before it is used as the baseline. |

Verified as done to spec:
- **Q12:** gen-domain operator check; `clip` accepted; `metro` rejected.
- **Q15:** enums; consistent `---` prefixing with report-only fallback; gen~ ≥1 inlet; stereo plugout~; banks in `parameters.parameterbanks`.
- **Q22:** comment-safe I/O and reorder; G4 Param parsing; lint checks 10–16; js ES5 lint by engine.
- **Q29:** `write_gendsp` in-place grow/shrink keeps user boxes and reports orphans.
- **Q31:** DSP template 0/1/2+ inputs and `foo_tilde`; N4M dict identifiers; `anything()` via `messagename` / `arrayfromargs`; min-devkit clone into a gitignored folder; per-codebox `.gendsp` validation.
- **Q33:** `Box.structural` in rnbo and externals; names derived correctly.
- **Q37:** `diagnose` read-only, all 32 troubleshooting patterns self-match; `record_confirmation` / proven-forms append on a copy.
- **Q40:** `.amxd` codec and export round-trip.
