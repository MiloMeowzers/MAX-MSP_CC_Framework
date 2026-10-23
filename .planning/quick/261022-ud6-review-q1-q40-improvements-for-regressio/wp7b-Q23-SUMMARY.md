---
quick_id: 261022-ud6
work_package: WP7b
task: fix-plan Q23 (vocabulary checks and cheap wins; review §4.4 R7 / R10; review-docs-completion CR-01)
status: complete
branch: worktree-agent-aaf26a623d6d1867b
plan_head_before: 2f0aa05b
commits: 4
tags: [validation, critics, save-gate, builders, db]
key-files:
  created:
    - tests/test_vocabulary_checks.py
    - tests/test_vocabulary_critics.py
  modified:
    - src/maxpat/walk.py
    - src/maxpat/validation.py
    - src/maxpat/hooks.py
    - src/maxpat/db_lookup.py
    - src/maxpat/builders.py
    - src/maxpat/critics/structure_critic.py
    - tests/test_validation.py        # named edit: line~ test now asserts the error
    - tests/test_patcher.py           # named edit: add_bpatcher args now [1, 2]
---

# WP7b Summary: fix-plan Q23 vocabulary checks

Q23 had a plan (261015-fm1) but was never run. That plan was still accurate, so this WP executes it on top of WP1–WP6. Parts already on `main` were reused, not rebuilt: WP1's `patch_path` lookup and Q39's bach `@out` check.

Every row of the Q23 table now has a check, firing tests and guard tests. No check adds a blocker or an error to any committed patch. The full suite is green on Python 3.10.19 and 3.14.2.

## Spec rows: status, how, commit

| Q23 row | Severity | Status | How | Commit |
|---|---|---|---|---|
| `clip(` in expr / vexpr / if | error | **done** | `_check_expr_clip` (Layer 4c, max scope only). Word-bounded `\bclip\s*\(`, so `fclip(`, gen~ codeboxes and rnbo scopes are never flagged. Rule `expr_clip`. | 3ad2b72e |
| Unknown object on the load/edit path | error | **done** (validator by WP1 b42a6966; plumbing here) | WP1 had already built `validate_patch(patch_path=)` and `_project_abstractions`. This WP wires the path through `_blocking_findings`, `_gate_report` (both sides, so a pre-existing unknown keys the same) and `_run_save_gate` (`patch_path=path`), and through `validate_file`. A new file with an unresolved unknown is refused and nothing is written. It saves when `NAME.maxpat` sits beside it. An edit that keeps an existing unknown saves; an edit that adds a second unknown is refused. | 3ad2b72e |
| Comma-separated `line~` segments | error | **done** (warning → error, per planner decision D2) | `_check_line_tilde_comma_messages` was rewritten in place to read `walk.message_segments`. It gives one **error** per (message, line~) cord when a ramp segment (2+ tokens) is followed by another segment: bassoon aac68ed `0., 0.9 15, 0.9 60, 0. 80`, `1 10, 0 500`. The jump-then-ramp idiom (`0, 1 500`, `100, 500 1000`, `0, $1 $1`, `stop, 0 100`) gives **no** finding; the old warning fired on it. The check applies in nested scopes. Rule `line_tilde_comma` is kept, and `box_ids` is now `(msg, line~)`. | 3ad2b72e |
| Numeric bpatcher args stored as strings | error | **done** | `_check_bpatcher_numeric_args` raises one error per bpatcher whose `args` holds `^[+-]?(\d+\.?\d*|\.\d+)$` strings (D11). Rule `bpatcher_numeric_args`. `add_bpatcher` now builds a new list and stores those strings as int / float. `1e3` stays a symbol. The caller's list is untouched. | 3ad2b72e |
| Message selector not in the destination's DB | warning | **done** | `_check_message_selectors` uses the D4 guards: message outlet 0 → inlet 0 only, max scope only. It skips numbers, `$ # @ "` tokens and `set`, plus containers, scripts and gen hosts, embedded patchers, unknown names, empty message lists, and lists containing `anything`. Accepted: `db.selectors` + the 21 jbox common attributes + `get<attr>`. **Addition:** bach / cage / dada / ears destinations are skipped (see Deviations). Rule `message_selector`. | 3ad2b72e, ad54023f |
| Unmatched send/receive across the patch tree | warning | **done** | `_check_unmatched_names(graph, dbh)` runs once per review in the structure critic, over closed trees only (D6). It covers s/r, send~/receive~ (plus mc.send~/mc.receive~), `; name` remote targets, value/v/pv, and buffer users (play~, groove~, index~, peek~, wave~, record~, poke~, cycle~ arg 2, …) against buffer~ / polybuffer~ (`pb.N`) / jit.buffer~. `#N` names are ignored, as the spec requires. Rule `unmatched_names`. | 620fa6be |
| Missing patcher-level `bgcolor` | warning | **done** | `_check_patcher_bgcolor` fires when `editing_bgcolor` or `locked_bgcolor` is set but `bgcolor` is not (D5), in every non-gen scope. A patcher with none of the three keys is fine (theme default). `set_canvas_background` never fires it. Rule `patcher_bgcolor`. | 3ad2b72e |
| Int truncation | warning | **done** | `_check_int_truncation` (D7). Float sources: flonum; dial/slider with `floatoutput 1`; live.dial/numbox/slider unless `parameter_type` is 1 or 2; `t f`; `f`; float-arg math; saved `float` outlettype on a newobj; DB float outlet. Destinations: arg-less `+ - * /` (any inlet), arg-less `ftom` (inlet 0), int-range `scale` (inlet 0). Max scopes only. Rule `int_truncation`. | 620fa6be |
| bach.* → non-bach without `@out t` | warning | **already done by Q39** | `package_critic._check_bach_out_mode` (rule `bach_out_mode`, text `Bach native llll output: `). This WP only adds the physics-composition f4f096b0~1 probe as a regression guard: obj-6, obj-7 and obj-16 are flagged and the `@out t` form is clean. | 620fa6be (test only) |
| mc.* fed a bare list | note | **done** | `_check_mc_bare_list` (D9). Destination is an `mc.*` newobj with `applyvalues` in `db.messages`, except mc.line~ / mc.curve~. Source is a message with a 2+ token numeric / `$N` segment, or a `pack` / `pak` with a numeric or missing first argument. Rule `mc_bare_list`. | 620fa6be |
| `db.selectors` crash (D10) | — | **done** | Dict message entries contribute their `name`. `db.selectors('bach.roll')` no longer raises TypeError, and `messages()` is unchanged. | 3ad2b72e |

Shared helpers: `walk.message_segments(box)` and `walk.message_remote_targets(box)` parse message text with quote and escape awareness, built on `split_box_text` (3ad2b72e). Existing private copies in graph.py, dsp_critic.py and m4l_polish.py were not touched (no refactor of shared code).

## Tests

- `tests/test_vocabulary_checks.py` (109): walk parts and junk input, clip, line~ (including the invariant `test_line_tilde_jump_then_ramp_idiom_not_flagged`), bpatcher args, add_bpatcher coercion and round-trip, db.selectors, the selector guards (bach family included), bgcolor, purity and junk input, and the save gate end to end (new-file refusal, abstraction beside, second unknown refused, clip / line~ / bpatcher refusals, validate_file).
- `tests/test_vocabulary_critics.py` (48): unmatched names (including the invariant `test_unmatched_names_skipped_on_open_tree`, the no-DB-built spy, and `#N` / `$` / `---` / numeric names), int truncation (TCI probe, dial `floatoutput`, live.dial `parameter_type`, rnbo skip, nested tag), MC bare list (ji-harmonizer probe), the bach Q39 probe, purity, never-blocker, and junk input.
- Named edits to existing tests: `test_validation.py::test_line_tilde_comma_message_warning` → `..._error` (`1 10, 0 500`, exactly one error), and `test_patcher.py::TestBpatcher::test_bpatcher_args` → `[1, 2]`.
- Red runs were recorded before each green: 58 failures for the validator half, 20 for the critic half, and 5 for the bach-skip refinement.
- **Full suite:** `7415 passed, 1 skipped, 5 xfailed` on **Python 3.14.2** and on **Python 3.10.19** (uv venv). The baseline at 2f0aa05b was 7258 passed, 1 skipped, 5 xfailed.

## Committed corpus (76 files) and allowlists

The triage compared validate (with and without `patch_path`) and review records against a `git archive` of 2f0aa05b. The non-Q23 record streams are identical. The old line~ warning never fired on a committed file. Q23 records found:

- **18 `Patcher bgcolor:` warnings** (true positives; warnings never fail the integration tests):
  - 15 top-level: amplitude-follower, intelligent-corpus-remixer/slice-voice, kicksynth, knock, reverse-delay/reverse-delay-mono, reverse-delay/reverse-delay, sample-layers/sample-layers-slot, sample-layers/sample-layers, simple-fm, spectraldetector, stereo-feedback-delay, stutter, subtractive-synth, tape-wobble, wormhole/wormhole-test.
  - 3 nested: mixer-strip `[p sends]` obj-37, and rhythmic-sampler slot `[p init]` obj-p-init and `[p clock]` obj-p-clock.
- **1 `Unmatched send:` warning:** spectraldetector `send detector-state` (obj-22). It is a documented broadcast to other patches, so it is true to the spec and only a warning.
- **0** errors or blockers from any Q23 check. **0** unknown-object errors with `patch_path`.

**Allowlists: none added.** No calibration, integration or allowlist file changed.

One false positive was fixed in the checker, not allowlisted: max-bridge fixture `fx-badargs.maxpat` `send 15`. A deliberately bad-args box is not a name, so numeric names are now ignored.

## Max bundle triage (4715 files: Max.app C74 + bach + dada; 0 exceptions)

| Check | Planning | Now | Verdict |
|---|---|---|---|
| expr clip / line~ / bpatcher errors | 0 / 0 / 0 | 0 / 0 / 0 | ok |
| Message selector (max) | 25 | 25 | Same list as planning, all DB gaps; see the DB follow-ups below |
| Message selector (bach / dada) | not measured | 810 / 47 → **0** | All lllls or data symbols. Fixed by skipping bach-family destinations (ad54023f) |
| Patcher bgcolor | 8 | 8 | ok |
| Int truncation | 54 | 56 (+1 bach) | Real int-mode shapes: BEAP / M4L quantizers such as `scale 0 200 0 200` fed by `snapshot~`, and `*` fed by `live.numbox`. Warning only |
| Unmatched names | ~21 | 73 max, 18 bach / dada | 64 of the max hits come from one file. Pulse Width Example's 32 embedded BEAP channel bpatchers each have a dead `r slide` / `r sample_interval`: true positives, duplicated per instance. The M4L `---` device names (42 hits in FilterTaps/bdband2) were removed by ignoring `---` names |
| MC bare list | 0 | 0 | ok |

## Deviations from the 261015-fm1 plan

1. **[Rule 4 / spec reading, recorded for user veto] D2, line~.** The brief said "spec says error, follow the spec". The check is now an error. Following D2, it fires only on a ramp segment followed by another segment, and the jump-then-ramp idiom gets no finding at all. The old warning advised removing the comma, which breaks `0, 1 500`.
2. **[Rule 1] Selector check skips `bach.` / `cage.` / `dada.` / `ears.` destinations**, and treats a dict message entry named `anything` like a str one (bundle evidence above). D4 had not measured the bach and dada packages.
3. **[Rule 1] Unmatched-names refinements beyond the D6 text:**
   - `---` (M4L device-scoped) and numeric names are ignored.
   - mc.send~ / mc.receive~ share the send~ / receive~ namespace.
   - `pattrforward` opens the tree, like `forward`.
   - A `; name` target is also satisfied by a buffer~ / polybuffer~ / value of that name, since MAX binds those to their names.
4. **Placement, to limit merge conflicts with WP7a:**
   - The validator checks live in a self-contained Layer 4c `_validate_vocabulary` block at the end of validation.py, called with one line after Layer 4. `_validate_domain_rules` keeps its signature.
   - The critic checks are appended at the end of structure_critic.py.
   - The `_LazyDB` class is unchanged; module-level guarded `_db_exists` / `_db_messages` are used instead.
5. **Bach row:** not reimplemented. Q39's `bach_out_mode` reports one finding per bach box, not one per cord as in D8. The probe test pins the three boxes.
6. **Commits:** 3 code commits plus this SUMMARY (the plan had 3 per-task commits). The validator half landed in one commit with its bach-skip refinement as a follow-up fix commit.

## Merge hotspots with WP7a

- `src/maxpat/hooks.py`: the `_blocking_findings` signature and validate call; the `_gate_report` signature and both `_blocking_findings` calls; the `_run_save_gate` `_gate_report(...)` call (`patch_path=path`); `validate_file`.
- `src/maxpat/validation.py`: `_validate_scope_layers` gains 3 lines after the Layer 4 call. The rest of the file is an appended block plus the in-place `_check_line_tilde_comma_messages` rewrite.

## Doc impacts (no docs edited)

- `.claude/skills/references/severity-contract.md`:
  - §1/§2 say "An unknown object is only a warning". It is now an error with the patch path (the save gate and `validate_file`).
  - Add the new errors (`expr_clip`, `line_tilde_comma`, `bpatcher_numeric_args`) and warnings (`message_selector`, `patcher_bgcolor`) to the §5 table.
  - The critic list should gain `unmatched_names`, `int_truncation` and `mc_bare_list`.
- `CLAUDE.md`:
  - MSP `line~` bullet: say that a leading single-number jump (`0, 1 500`) is fine and only ramp-then-segment is an error.
  - Rule #1: unknown objects block a save unless an abstraction resolves beside the patch or in its project. Save abstractions before the patch that uses them.
  - "Bpatcher and Abstraction Arguments": `add_bpatcher` now coerces numeric strings, and the validator errors on them.
- `.claude/skills/references/troubleshooting.md`: rows for "function clip not found", "doesn't understand X" and "bad arguments" should point at the new checks.
- `TECHNICAL.md`: the validator check list (Layer 4c) and the structure-critic check list.
- `.claude/skills/max-critic/SKILL.md`: the check list.
- `src/maxpat/critics/__init__.py`: the review_patch docstring (left alone to avoid a conflict with WP7a).
- `.planning/STATE.md` and the fix plan: add a Q23 row pointing here; CR-01 is resolved.

## DB follow-ups (overrides.json, not edited)

The selector warnings show DB message gaps in the Max bundle:
- pcontrol `enable`
- jit.movie `bang`
- jit.qt.movie `stop` / `frame` / `bang` / `start`
- detonate `dump`
- jit.gl.meshwarp `blend`
- jit.gl.texture `clear`
- jit.playlist `vol` / `unique`
- flonum `razzledazzle`

## Needs MAX confirmation

- D2 relies on 63 Cycling '74 shapes. Optionally confirm that `0, 1 500` into `line~` jumps to 0 and then ramps to 1, and that `1 10, 0 500` plays only the last ramp.
- Nothing else: every check is static.

## Self-Check: PASSED

- All created and modified files exist.
- Commits 3ad2b72e, ad54023f and 620fa6be are on `worktree-agent-aaf26a623d6d1867b`.
- No commit touches `patches/`, `.claude/`, CLAUDE.md or TECHNICAL.md.
- `git stash` was not used.
