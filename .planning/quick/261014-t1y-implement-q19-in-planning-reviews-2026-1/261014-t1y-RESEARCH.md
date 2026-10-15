# Quick 261014-t1y: Q19 Shared walker + recursive validation - Research

**Researched:** 2026-10-14
**Domain:** `src/maxpat/validation.py` pipeline, .maxpat embedded-patcher storage, save gate
**Confidence:** HIGH (all claims are from source read this session or prototypes run this session)

## Summary

Every Layer 2–5 function in `validation.py` reads `patch_dict["patcher"]["boxes"/"lines"]` and nothing else. So no layer needs a new signature: run the same functions on `{"patcher": inner}` with the inner scope, then tag the results. A quote-aware tokenizer already exists (`io_resolvers.split_box_text`, Q10). On every one of the 4,816 newobj/message texts in committed patches it returns exactly what `str.split()` returns, so swapping it in changes nothing on the baseline. Scope derivation also exists (`db_lookup.inner_patcher_scope`, Q12). `walk.py` should wrap these two rather than reimplement them.

I ran a prototype twice: once as a scratch pytest plugin that monkeypatches `validate_patch` to recurse, and once directly over all committed patches. **Committed patches gain zero nested errors and zero nested proposed removals**, so `test_validate_patch_no_errors` stays green and no allowlist is needed. They do gain 23 new warnings: 11 unsafe-gain `*~ 2.` style, 7 unknown abstractions (`terrain-lfo`, `terrain-osc`, `terrain-osc-b`), 4 unterminated, and 1 comment `#N`. They also gain about 83 info lines, almost all of them missing assistance comments. With the plugin, the full suite gives **1 failed / 3676 passed**. The single failure is `tests/test_validation.py::TestDomainGuard::test_floor_tilde_in_gen_subpatcher_silent`, which asserts the old D-07 "no recursion" rule that Q19 retires. That test must be inverted, because `floor~` inside gen~ is a true positive.

**Primary recommendation:**
- Split `validate_patch` into a per-scope runner, `_validate_scope(wrapped, db, allowed_packages, scope, ...)`, driven by `walk.iter_patchers`.
- Leave the top-level results list unchanged and append the nested results after it, in pre-order.
- Gen scope skips Layer 4 (`_validate_domain_rules`) entirely.
- Layer 5 checks codeboxes inside **any** gen container (`GEN_CONTAINER_NAMES`, with the inner patcher taken from `box["patcher"]` **or** `box["data"]["patcher"]`) in **every** scope.
- Make the rnbo_compatible check warning-level (see Open Question 1).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
### Path tagging
- Add a `path` slot to `ValidationResult` (`""` at top level).
- Nested findings ALSO get a message prefix, e.g. `[p synth > gen~] ...`. Top-level messages stay byte-identical so save-gate keys and existing tests are stable.

### Nested auto-fixes
- `proposed_removal` for nested cords is path-aware; `apply_fixes` walks to that scope's patcher and removes the cord there (both dict and Patcher inputs). Top-level behaviour unchanged.

### External abstractions
- Walk embedded patcher dicts only. Bpatchers/poly~/abstractions that reference an external file are not loaded.

### Gen/RNBO scope rules
- Reuse existing scope machinery (Q12 `detect_patcher_scope`, `DOMAIN_SCOPES`): each scope runs Layers 2–5 with its scope; gen scope skips MSP-only domain rules (dac~ termination, gain staging, etc.); rnbo scope applies rnbo_compatible logic. No new rule families.

### Claude's Discretion
- Exact path segment naming (box text vs varname), walker context detection for poly/bpatcher, internal refactor shape.

### Deferred Ideas (OUT OF SCOPE)
- Critics/analyze/checklist/graph recursion is Q20 — out of scope.
</user_constraints>

**Fix-plan "Rules for every task" (copy into PLAN.md):** `.planning/reviews/2026-10-11-fix-plan.md:17-31`:
1. Read the finding IDs first.
2. Write each regression test first (red, then green).
3. Never edit committed patches. A false positive means fixing the checker; a true positive gets an allowlist entry with a reason, listed in SUMMARY.
4. Run `python3 -m pytest -q` before and after. The suite must be fully green.
5. No `git stash`, no `git add -A`/`.`.
6. Python 3.10.
7. Don't widen scope; ask with multiple-choice options.
8. Edit docs only where the task says to; list other doc impact in SUMMARY.
9. Flag anything that needs confirming in MAX.

## Project Constraints (from CLAUDE.md)
- Rule #5: the Patcher API is the only way to edit patches. Never edit `patches/**` (this matches fix-plan rule 3).
- Rule #7: never `git stash`; stage explicit paths only.
- Subpatcher Inlet/Outlet Access: inner inlets/outlets are maxclass `inlet`/`outlet`. Never identify them by `box.text`.
- `validate_patch` is non-destructive (memory `feedback_validate_mutates.md`, Q1). Only `apply_fixes` removes cords. This must hold for nested scopes too.

## 1. Layer map: what reads `patch_dict["patcher"]` directly

All line numbers are in `src/maxpat/validation.py`. The review's `:232`, `:965` and `:1381` predate the Q1–Q18 edits; the current locations are listed below.

| Layer | Function (lines) | Reads | Per-scope plan |
|---|---|---|---|
| 1 | `_validate_json_structure` (336-361) | `patch_dict["patcher"]`, `.get("boxes")`, `.get("lines")` | Run on every scope and add the dup-id check (§5) |
| 2 | `_validate_objects_exist(patch_dict, db, scope)` (397-452) | `["patcher"]["boxes"]` (411) | Pass the inner scope |
| 2b | `_validate_maxclass_usage` (455-508) | `["patcher"]["boxes"]` (476) | Unchanged |
| 2c | `_validate_package_gating` (515-550) | `["patcher"]["boxes"]` (538) | Unchanged |
| 2d | `_validate_community_extracted` (557-614) | `["patcher"]["boxes"]` (570); `warned_packages` is local (568) | Share one `warned_packages` set across scopes, or the same package warns once per scope |
| 3 | `_validate_connections` (654-819) | `["patcher"]["boxes"]` (673), `["patcher"]["lines"]` (679) | Unchanged; ids are scope-local, so proposals need the path |
| 4 | `_validate_domain_rules` (949-1063) | `["patcher"]["boxes"]`/`["lines"]` (956-957), then box_lookup-based `_check_*` helpers | **Skip in gen scope** (details below) |
| 4b | `_validate_domain_restrictions(..., scope)` (1070-1124) | `["patcher"]["boxes"]` (1092) | Pass the inner scope; update the D-07 docstring |
| 5 | `_validate_embedded_genexpr` (1131-1201) | `["patcher"]["boxes"]` (1164), then `box.get("patcher")` (1178) | Generalize (§2) |

**Run per scope by wrapping:** call `_validate_*({"patcher": inner}, ...)`. No layer signature changes. The `validate_patch(patch, db, allowed_packages, *, scope)` signature (152-158) stays the same.

**Layer 4 helpers in gen scope.** All of these are MSP or Max-UI rules, so the whole of `_validate_domain_rules` should be skipped in gen scope:
- `_check_unterminated_chains` (1252, name ends `~`, `_TERMINAL_NAMES`)
- `_check_gain_staging` (1293, `_OSCILLATOR_NAMES` / `dac~`)
- `_check_unsafe_gain_values` (1350, `*~`)
- `_check_feedback_loops` (1387, outlettype `"signal"`; gen feedback via History is legal)
- `_check_gen_param_message_syntax` and `_check_line_tilde_comma_messages` (message boxes, which don't exist in gen)
- `_check_comment_hash_substitution`, `_check_multislider_fetchindex`, `_check_umenu_items_format`, `_check_assistance_comments`, `_check_compound_argument_substitution`
- `_check_genexpr_io_syntax` / `_check_genexpr_delay_usage` match only `maxclass=="newobj"` with text `codebox...`. Gen scopes store `maxclass "codebox"`, so Layer 5 owns those.

In the prototype, gen scopes (56 committed, plus all gen scopes in the bundle) gave **0** Layer 2/3/4b errors, so the other layers are safe to keep in gen scope.

**RNBO scope:** run Layers 2–5 with `scope="rnbo"`. Layer 2 already allows rnbo-only names there (implied restrictions, 420-432). The "rnbo_compatible logic" is `rnbo_validation._validate_rnbo_objects` (`rnbo_validation.py:120-145`, error level, via `RNBODatabase.is_rnbo_compatible`, `rnbo.py:68-80`, which is `name in self._compat_objects` with **no alias resolution**). See Open Question 1 before making it an error. No committed patch contains `rnbo~`, so triage impact is zero.

## 2. Existing walkers, extractors and codebox discovery

**Name extractors to replace in Q19:**
- `validation._extract_object_name` (368-388): `text.split()[0]` crashes on `"   "` (verified: IndexError at 384). It returns None for `_STRUCTURAL_MAXCLASSES = frozenset({"inlet", "outlet", "patcher", "bpatcher"})` (41).
- `validation._get_box_name` (1204-1212): same body as `utils.get_box_name`.
- Inline splits inside validation.py:
  - `_is_container_box` (649, `str(box.get("text",""))` turns None into the token `"None"`)
  - src_args (768)
  - `*~` parts (1366)
  - umenu (1638)
  - `text.startswith("gen~")` (1174)
  - `text.startswith("codebox")` (1469, 1494)
- `rnbo_validation._extract_object_name` (`rnbo_validation.py:101-118`): duplicate of the above with `_RNBO_STRUCTURAL_MAXCLASSES`.

**Reuse, don't write a new tokenizer.** `io_resolvers.split_box_text` (`io_resolvers.py:45-92`):
- quote-aware, with quotes kept in the token: `t "a b" c` gives `['t', '"a b"', 'c']`
- a backslash escapes the next character and is kept
- an unbalanced quote runs to the end of the text
- None gives `[]`, and it never raises

`io_resolvers.box_args(text)` (105-114) returns `(name, positional args up to the first @)`. **Caution:** validation.py:768 passes `split()[1:]`, **including** `@attrs`, to `db.get_signal_role(..., args=)`. Keep raw tokens there so the baseline doesn't change. io_resolvers imports nothing from `src.maxpat`, so `walk.py` → io_resolvers/db_lookup → no cycle. validation imports walk.

**Codebox discovery today (Layer 5, 1164-1200):** top-level boxes only, matched by `maxclass == "gen~"` or a newobj whose text starts with `gen~`, using `box.get("patcher")` only. It misses:
- **mc.gen~**: MAX's mc wrapper stores the inner patcher at `box["data"]["patcher"]` (committed: `ji-harmonizer.maxpat` obj-88, `'mc.gen~'`, keys `data`, `wrapper_uniquekey`). The Max bundle has 5 more. `dsp_critic._gen_inner_patcher` (`critics/dsp_critic.py:171-183`) already handles both locations; move that logic into `walk.inner_patcher(box)`.
- **jit.gen / jit.pix / jit.gl.pix / gen / mcs.gen~**: none are matched by name.
- **gen~ inside a `p`**: 15 committed instances in minitaur and 5 in terrain-synth/terrain-voice, all clean today.

Message format today: `f"gen~ '{gen_id}' codebox: {r.message}"` (1198). Tests match the substring `"gen~ 'g1' codebox:"` (`tests/test_validation.py:890,938`, and others).

**Recommended Layer 5 (per scope):**
- For every box in the scope where `walk.box_name(box) in GEN_CONTAINER_NAMES or maxclass == "gen~"` and `walk.inner_patcher(box)` is a dict, validate that inner patcher's `maxclass == "codebox"` boxes. Emit `f"{name} '{id}' codebox: ..."` at the **container's own (parent) path**. For gen~ this is byte-identical to today at the top level.
- The walker still visits the gen inner patcher, but that scope does **not** re-check its own codeboxes, so nothing is reported twice.
- Exception: a gen-scope patcher entered through a **non**-gen-container box (a `p` inside gen~) validates its own codeboxes as `codebox '{id}': ...`.
- Recommend **not** checking a top-level gen-scope file's own codeboxes (`.gendsp` via `validate_file`/`write_gendsp`). `validate_code_file` covers them, and `severity-contract.md:103` documents that `write_gendsp` doesn't gate on GenExpr checks.

A preview over the committed tree finds no nested or mc/jit codebox errors. The only findings are Param min/max warnings: 7 for each terrain-synth jit.gen obj-92 (2 copies). ji-harmonizer's mc.gen~ gains a top-level `info` "Detected I/O" line, which is a new top-level result but not a changed message.

**Scope constants** (verbatim, `src/maxpat/db_lookup.py`, read this session):
- `DOMAIN_SCOPES = ("max", "gen", "rnbo")` (75)
- `SCOPE_BY_CLASSNAMESPACE = {"dsp.gen": "gen", "jit.gen": "gen", "rnbo": "rnbo"}` (87)
- `GEN_CONTAINER_NAMES = frozenset({"gen~", "mc.gen~", "mcs.gen~", "gen", "jit.gen", "jit.pix", "jit.gl.pix",})` (93-95)
- `RNBO_CONTAINER_NAMES = frozenset({"rnbo~", "mc.rnbo~"})` (96)
- `inner_patcher_scope(box_dict, parent_scope)` (127-148): gen/rnbo by container name, else the embedded patcher's classnamespace/codebox, else the parent's scope. It reads `box_dict.get("patcher")` for the fallback, so pass `{**box, "patcher": inner}` for data.patcher boxes, or have walk resolve the scope itself.
- `validation._CONTAINER_NAMES = frozenset({"p", "patcher", "bpatcher", "poly~", "mc.poly~", "pfft~", "rnbo~",})` (89-91).

**Other walkers (Q20 consumers, list only, do not touch in Q19):**

| Location | What it walks |
|---|---|
| `hooks._iter_patchers` (`hooks.py:586-605`) | Save-gate walker; path element is `(box id, box text or maxclass)`; used by `_cord_set`/`_box_ids`/`_port_ranks`/`_path_label` (612-683) |
| `m4l_polish.py:159, 253-256` | |
| `critics/m4l_critic.py:278, 403` | |
| `critics/rnbo_critic.py:75, 97` | Name extractor |
| `critics/dsp_critic.py:171` (`_gen_inner_patcher`), `:343` | |
| `audit/parser.py:40, 118, 143` (`traverse_patcher`) | |
| `analysis.py:310, 519` | Patcher-based |
| `layout.py:213`, `graph.py:156, 212`, `aesthetics.py:523`, `hooks.py:220` (`_finalize_midpoints_recursive`) | |
| `testing.py:159-185` (`_extract_object_names`) | |
| `tests/test_domain_scope.py:503-514` (`_walk_max_scope_boxes`) | |

Other extractors: `utils.get_box_name` (`utils.py:6-18`, imported by 6 critics and m4l_polish), `package_critic._get_object_name:41`, `layout_critic:131`, `patcher.py:1391-1392`, `sizing.py:206`, `m4l_polish.py:261,536`.

## 3. Embedded-patcher storage (verified on committed patches plus the Max 9 bundle, 3,139 files and 12,119 scopes)

| Container | Storage | classnamespace seen | Committed count |
|---|---|---|---|
| `p` / `patcher` newobj | `box["patcher"]` | `"box"` or absent; `"rnbo"` when inside rnbo~ | 110 (`p`) |
| bpatcher, embedded | maxclass `bpatcher`, `"embed": 1`, `box["patcher"]` | absent / `"box"` | 0 (bundle: 1,007) |
| bpatcher, external | maxclass `bpatcher`, `"name": "X.maxpat"`, no `patcher` | n/a | 43 (not loaded, per the locked decision) |
| poly~ / pfft~ | external file only (`poly~ slice-voice 8 @steal 1`); never embedded in committed patches or the bundle | n/a | 3 external |
| gen~ | `box["patcher"]` | `"dsp.gen"` (MAX-saved) or `"box"` (generator-written, 20) | 53 |
| mc.gen~ | **`box["data"]["patcher"]`** | `"dsp.gen"` | 1 (ji-harmonizer obj-88) |
| jit.gen / jit.pix / jit.gl.pix / `gen` | `box["patcher"]` | `"jit.gen"` | 2 jit.gen (terrain-synth) |
| rnbo~ | `box["patcher"]` | `"rnbo"` | 0 (bundle: 663) |

**Context derivation (recommended):**
- `scope = inner_patcher_scope(...)`.
- `context = scope` if scope is gen or rnbo.
- Otherwise `"bpatcher"` if maxclass is `bpatcher`, `"poly"` if name is in `{"poly~", "mc.poly~"}`, else `"max"`.
- Validate scope = `context if context in ("gen", "rnbo") else "max"`.
- A `p` inside gen~ or rnbo~ inherits gen or rnbo, which matches `Patcher.from_dict` (`patcher.py:1413-1418`) and `test_rnbo_container_and_nested_p` (`tests/test_domain_scope.py:692`).
- The top-level context is the scope `validate_patch` already resolves (189-209).

**Path:** have `iter_patchers` yield path as a tuple of `(box_id, label)` pairs, mirroring `hooks._iter_patchers` so Q20 can replace it.
- `ValidationResult.path` is the id chain `"/".join(ids)`, for example `"obj-3/obj-9"`, and `""` at top. Ids are unique per scope, while labels are not (minitaur has 5 `p voice-N` with identical inner ids).
- The message prefix uses the labels: `f"[{' > '.join(labels)}] "`.
- Label = name + first positional arg: `p synth`, `gen~`, `poly~ voice`. For a bpatcher, use `bpatcher` plus its `name` when present.
- Walk iteratively (an explicit stack, in pre-order) so deep nesting can't hit the recursion limit.

## 4. Tokenizer facts
- No committed newobj or message text contains `"` or leading whitespace (survey of 4,816 texts). 90 `expr` and 16 `exprfill` texts use the `\,` escape. `split_box_text` gives the same result as `.split()` on all 4,816.
- MAX writes quoted symbols as `"a b"`, escapes as `\"`, `\,`, `\;`. Message boxes keep bare `,`/`;` ([ASSUMED] from MAX format knowledge; consistent with `split_box_text`'s docstring).
- Proposed `walk.py` helpers:
  - `box_text(box) -> str`: text if it's a str, else `""`. Use this everywhere validation.py does `box.get("text", "")`, because None or a number crashes (§5).
  - `box_tokens(box) -> list[str]`: `split_box_text`.
  - `box_name(box) -> str`: newobj gives token 0 or `""`; any other maxclass gives the maxclass or `""`. Same contract as `utils.get_box_name`.
  - `box_args(box) -> list[str]`: raw tokens after the name, including `@attrs`, as a drop-in for `split()[1:]`.
  - `inner_patcher(box)`.
- Keep `_extract_object_name`'s None-for-structural semantics as a thin wrapper over `box_name`, because Layers 2/3 rely on it.

## 5. Empty-text crash and duplicate ids (reproduced, Python 3.14.2)

| Input (newobj unless noted) | Result |
|---|---|
| `text: ""` | IndexError, `validation.py:1638` `_check_umenu_items_format` (the review's `:1381`). The bundle prototype hit this same crash 4 times (`loadbang.maxhelp`, `jit.freeframe.maxhelp`, BEAP Sync Osc, Vizzie) |
| `text: None` | AttributeError at 1469 `_check_genexpr_io_syntax` (`.startswith`); 1174 and 1494 have the same pattern |
| `text: "   "` | IndexError at 384 `_extract_object_name` |
| message/comment `text: None` | TypeError in `re.search` (1520/1557/1567/1588/1617 pattern) |
| message/comment `text: 5` | TypeError at 1237 (`"#" not in 5`) |
| Duplicate ids (two `obj-1`) | Today: only a confusing `Outlet index 0 out of bounds on 'obj-1' (has 0 outlet(s))` proposed removal |

**Fixes:**
- Route every text read through `walk.box_text`.
- Add the dup-id check inside `_validate_json_structure` after the boxes-is-list check: `("json", "error", "Duplicate box id 'obj-1' (2 boxes)")`.
- A top-level Layer-1 error still returns early (219-220).
- A nested Layer-1 error is reported with its path. Its scope's Layers 2–5 are skipped and the walker doesn't descend into it, because paths would be ambiguous.
- Survey: **0** duplicate ids, and 0 scopes with a non-list boxes/lines, in all 69 committed files and all 12,119 bundle scopes. Nothing new fires on the baseline.

## 6. Consumers of ValidationResult, and keeping top level identical

- `ValidationResult.__slots__ = ("layer", "level", "message", "auto_fixed", "proposed_removal")` (126). Add `"path"` as a keyword with default `""`. All 29 external `ValidationResult(` constructions (code_validation, rnbo_validation, hooks) are positional or keyword for the first 5 fields, so they are unaffected. Leave `__repr__` (144-145) alone; the prefix is in the message.
- **Save gate** (`hooks.py:491-520` `_finding_key`, `:528-547` `_blocking_findings`, `:687-735` `_gate_report`):
  - Keys come from the message template with `obj-N`, quotes and numbers normalized, plus the `proposed_removal` ids.
  - Baseline and new findings are both computed with the new code, so top-level keys are unchanged and pre-existing nested blockers are exempt by the multiset diff.
  - Recommend appending `getattr(result, "path", "")` to the key tuple. Without it, `[p voice-1]` and `[p voice-2]` normalize to the same template, and their inner `obj-68` ids collide.
  - `tests/test_save_gate.py:377-412` assert with `==`/`!=`/`in key` between keys, so appending an element keeps them green.
  - New files: any nested error now refuses the save. This is intended.
- `has_blocking_errors` (249-277): no change; nested proposals block new patches the same way.
- **apply_fixes** (280-329): group keys by `r.path`. `""` keeps today's exact code path and return values.
  - For a nested path, walk the ids. In a dict, `box["patcher"]` or `box["data"]["patcher"]`, then slice-assign `lines[:]`.
  - In a **Patcher**, nested scopes are `Box._inner_patcher` (a Patcher, set in `from_dict` at `patcher.py:1413-1418`), so filter `.lines[:]` there (Patchline fields `source_id/source_outlet/dest_id/dest_inlet`, `patcher.py:62-78`).
  - **mc.gen~ data.patcher is not parsed into `_inner_patcher`.** It lives in `box._raw["data"]` (shallow copy; `to_dict` round-trip uses `dict(self._raw)`, 289-291). Switch to dict mode and slice-assign `box._raw["data"]["patcher"]["lines"]` in place.
  - Return nested matches as `(path, src, outlet, dst, inlet)` so they're distinguishable from top-level 4-tuples. Keep `proposed_removal` itself as a 4-tuple (`test_validation_result_default_and_coercion` and the gate tests depend on it).
- **Integration tests:**
  - `test_validate_patch_no_errors` (`tests/test_integration_patches.py:134-156`) fails on any error or proposal. The prototype shows 0 nested ones, so no validation allowlist is needed. That file only has a *review* allowlist (`review_blocker_allowlist.json`).
  - `test_validation_nondestructive.py` dict and Patcher parity tests (92-115) must keep passing with nested findings. Patcher input goes through `to_dict()` (204), so parity holds automatically.

## 7. Triage preview (prototype run this session; scratchpad `proto.py`, `plug/q19proto.py`)

- Committed tree: 55 `patches/*/generated/*.maxpat` (57 with maxhelp), with 166 nested scopes (110 max, 56 gen).
  - The survey found 5,085 top-level boxes and 3,443 nested boxes, and 3,935 top-level lines and 2,943 nested lines (the review says 41% of boxes are nested).
  - New nested findings: 0 errors, 0 proposals, 23 warnings.

| Count | Warning | Where |
|---|---|---|
| 11 | `Unsafe gain multiplier` | minitaur `p filter` (`*~ 2.`/`5.`), `p mixer`, `p oscillators` (`*~ 24.`), and `p voice-1..5` (`*~ 1.5`–`4.`) |
| 7 | `Unknown object` | terrain-synth abstractions `terrain-lfo`/`terrain-osc`/`terrain-osc-b`; Q23 handles beside-patch abstractions |
| 4 | Unterminated `*~` | terrain-view-a/b |
| 1 | Comment `#N` | `p about` |
| 1 | Trigger-to-signal role warning | `p sequencer` |

- About 83 info lines: inlet/outlet missing assistance, plus 19 "Detected I/O".
- Warnings don't fail any test. List them in SUMMARY as "true-positive or intentional, user-confirmed patches, no action". The unsafe-gain ones are deliberate drive stages in user-confirmed minitaur.
- Full suite with recursion: **1 failed / 3676 passed / 1 xfailed / 1 xpassed**. The only failure is `test_floor_tilde_in_gen_subpatcher_silent` (`tests/test_validation.py:713-753`). Rewrite it to assert the error **with** `path == "gen-1"` and the `[gen~]` prefix, and update the `TestDomainGuard` docstring (684-689).
- Bundle robustness: no crashes except the 4 empty-text ones. Runtime: 1.9 s for 12,119 scopes, and 0.03 s top-level for 55 committed files. **Performance is a non-issue.**

## 8. Pitfalls

1. **Top-level list must stay a prefix.** Run the existing top-level sequence (Layers 1–5) first, unchanged, then append nested results. Don't interleave nested results per layer.
2. **Double-reporting codeboxes.** Layer 5 reports from the container's parent scope; the visited gen scope must not re-check them (§2).
3. **Python 3.10.** The local interpreter is 3.14.2 and no 3.10 is installed, though `uv 0.9.18` is available. Check syntax with `python3 -c "import ast,sys;[ast.parse(open(f).read(),feature_version=(3,10)) for f in sys.argv[1:]]" src/maxpat/walk.py src/maxpat/validation.py`. Avoid 3.11+ stdlib (`typing.Self`, `itertools.batched`, `except*`). `from __future__ import annotations` is already used, so `X | None` annotations are fine. Optionally run `uv run --python 3.10 python -m pytest tests/test_walk.py -q` if a network fetch is OK.
4. **Gate key collisions** across identically labeled subpatchers: add the path to `_finding_key` (§6).
5. **RNBO data gaps** (Open Question 1): a bundle preview of rnbo scopes shows the Max DB doesn't model RNBO well:
   - 98 `Signal outlet to control-only inlet` proposals
   - 20 `codebox~` wrong-maxclass errors
   - `setparam`/`bool`/`buffer`/`constant`/`ln`/`min` flagged "exists only in gen" inside rnbo
   - `is_rnbo_compatible` is False for `*~` (88), `flonum` (1,179), `panel` (655), `buffer~`, `+`, `*`, `-` and `t` (no alias resolution)

   Nested rnbo errors would be false blockers on future new RNBO patches.
6. **Module and doc text now stale:**
   - Module docstring (1-22) and Layer 4b/5 docstrings ("top-level only", D-07).
   - `severity-contract.md:15,42,84,103` ("top-level `gen~`", "top-level cord", "Scope of the walk").
   - Per rule 8, list these in SUMMARY. The docstrings in src are fine to edit.
7. Don't touch `hooks._iter_patchers` or `utils.get_box_name` in Q19 (Q20). Their output shapes are load-bearing for the gate's port-change labels.

## Open Questions

1. **RNBO-scope rnbo_compatible severity.** What we know: the locked decision says rnbo scope "applies rnbo_compatible logic". The data marks `*~`, `flonum`, `panel` and operators as incompatible.
   - A) warning, alias-resolved, skipping UI maxclasses (recommended)
   - B) error, as `validate_rnbo_patch` does
   - C) info only

   Separately: should rnbo scope also skip Layer 3 signal/role type checks (keeping bounds) and add `codebox~` to the 2b skip? Recommendation: **yes to skipping Layer 3 type checks in nested rnbo scopes only**, and leave 2b alone because the `codebox~` UI_MAXCLASSES gap is a separate DB issue. If the planner judges this a widening, ask the user per rule 7.
2. **Top-level gen-scope files' own codeboxes** (`.gendsp` via `validate_patch`): recommend leaving them unchecked (§2). This is discretion; it keeps the `write_gendsp` gate behaviour documented in `severity-contract.md:103`.

## Validation Architecture

| Property | Value |
|---|---|
| Framework | pytest (repo suite; `conftest.py` in tests/) |
| Quick run | `python3 -m pytest -q tests/test_walk.py tests/test_validation.py tests/test_validation_nondestructive.py tests/test_save_gate.py tests/test_domain_scope.py` |
| Full suite | `python3 -m pytest -q`. Baseline this session: **3677 passed, 1 xfailed, 1 xpassed, 29 warnings in 67.6 s** |

| Behavior | Test (new, Wave 0) |
|---|---|
| `osc~` inside `p synth` is a Layer-2 error, `path == "<p id>"`, message starts `"[p synth] "` | `tests/test_validation_recursive.py` |
| Out-of-range cord in a subpatcher gives a proposal with the path; `apply_fixes` removes it from the inner lines (dict **and** Patcher); top-level lines untouched | same |
| `p` → gen~ → codebox `delay()` gives a `gen~ '<id>' codebox: delay()` error tagged with the p path | same |
| mc.gen~ `data.patcher` codebox and jit.gen codebox are checked | same |
| Gen scope skips Layer 4 (e.g. `cycle~`-less unterminated rules don't fire); `floor~` in gen~ gives a 4b error (inverted D-07 test) | `test_validation.py` edit |
| Empty / None / whitespace / non-str text: no crash (newobj, message, comment) | `tests/test_walk.py` + validation |
| Duplicate box ids gives a Layer-1 error (top level returns early; nested scope skipped) | same |
| Tokenizer: quoted args, `\,` escape, `@attrs` kept in `box_args`, data.patcher in `inner_patcher`, iter_patchers path/context for p / bpatcher(embed) / gen~ / mc.gen~ / jit.gen / rnbo~ / p-in-rnbo~ | `tests/test_walk.py` |
| Top-level byte-identity: messages, levels and proposals of every committed patch are unchanged as a prefix | Snapshot a list before the change, or assert `results[:n_top]` equals the pre-change output |

## Security Domain
This is a pure in-process validator over local JSON, with no auth, crypto or network involved. The only concern that applies is ASVS V5 input robustness. Malformed or untrusted `.maxpat` input must never crash: non-dict boxes, non-str text, non-list boxes/lines, cyclic or deep nesting. Use an iterative walker and `isinstance` guards everywhere.

## Sources (all HIGH; read or run this session)
- `src/maxpat/validation.py` (full), `db_lookup.py:60-148`, `io_resolvers.py:1-132`, `rnbo_validation.py:80-145`, `rnbo.py:68-80`, `patcher.py:52-82, 230-370, 1310-1440`, `hooks.py:440-735, 890-925`, `critics/dsp_critic.py:171-183`, `utils.py`
- `tests/test_integration_patches.py`, `test_validation.py:680-1000`, `test_validation_nondestructive.py:155-200`, `test_save_gate.py:370-412`, `test_domain_scope.py:495-720`
- Prototypes in `/private/tmp/claude-501/-Users-taylorbrook-Dev-MAX/2e6096dd-5a74-4be3-9ce3-70676e7f6ad2/scratchpad/` (`shapes.py`, `proto.py`, `bundle.py`, `plug/q19proto.py`)
- Max 9 bundle at `/Applications/Max.app/Contents/Resources/C74` (3,139 patchers)

**Valid until:** next edit to `validation.py`/`hooks.py` (fast-moving review queue; Q20–Q23 touch the same files).
