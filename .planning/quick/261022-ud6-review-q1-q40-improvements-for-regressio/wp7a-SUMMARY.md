---
quick_id: 261022-ud6
work_package: WP7a (cross-package handoffs from WP1-WP6)
status: complete
branch: worktree-agent-ac9dd1125f846b9db
plan_head_before: 2f0aa05bf095471a5626e49d40bbca8df651ac73
plan_head_after: c396c53b
commits: 9
python: 3.10.19 (uv venv from requirements-dev.txt) and 3.14.2, full suite green on both
tests: "7342 passed, 1 skipped, 4 xfailed, 0 xpassed (both interpreters; base 2f0aa05b: 7258 passed, 1 skipped, 5 xfailed)"
---

# WP7a: cross-package handoffs

I checked every handoff in the WP1-WP6 summaries against merged main (2f0aa05b) before acting on it. Each one that was still needed has a regression test that failed first and passes now. No `patches/**` file was edited. The only library files edited are `patterns/gen/timing/*.gendsp`, and those edits went through `write_gendsp`.

## Handoff → result

| From | Handoff | Result | Commit |
|---|---|---|---|
| WP3 → DB | `bach.slice` outlet count | **Done.** New `overrides.json` entry with 2 outlets (left / right llll). Evidence: the bach refpage lists 2 outlets, and the help box `bach.slice 3 @out t` is saved as 1 in / 2 out. I regenerated the help-io baseline: improvements only (21 bach/dada mismatching boxes gone, 0 regressions). | d3aaddef |
| WP3 → DB | `zplane~` outlets 1-3 type float vs role list | **Done.** Outlets 1-3 are now `type: list`. The refpage digests are "List of ... Pairs/Gains", and both MAX-saved help boxes store `outlettype` as `list` ×4. The refpage `float` type was wrong. The `_evidence` key is added. | d3aaddef |
| WP3 → DB | `mc.range~` outlet 1 role | **Done.** `signal_role` changed from `float` to `list`, matching the refpage type `list` and the help boxes' `list`. | d3aaddef |
| WP3 → aesthetics | Theme fills for uncolored number / flonum / textbutton (Q26) | **Done.** New `aesthetics.THEME_FILLS`, with number/flonum at 0.125 and textbutton at 0.262. Evidence: the Max 9.2 refpage `bgcolor` `dynamiccolor_default` is the theme `bgcolor` for number and `live_control_bg` for textbutton, with values from `default.maxtheme`. `THEME_FILL_MAXCLASSES` is now derived from the table. Corpus effect: critic findings are unchanged except the bach.roll fix below. The opt-in `repair_text_contrast` now also fixes 9 transparent-bg flonums in scala-synth, which the critic already flagged. **Needs MAX confirmation** (see below). | cc8d9fad |
| WP2 → WP3 | layout_critic skips self-painted boxes | **Done.** `_check_text_contrast` skips any box `paints_unknown_background` matches, the same rule the repair pass uses. The physics-composition bach.roll obj-67 false positive is gone (264 → 263 findings over the corpus). | cc8d9fad |
| WP3 → m4l_device | Clear error when exporting a helper abstraction | **Done.** `export_amxd` on a `live.thisdevice`-only patch now raises "...is a helper abstraction, not a device ... pass kind=...". An explicit kind still exports. | f27f56dc |
| WP4 | `add_m4l_device` docstring | **Done.** It now covers BL-01 reuse, WR-01 refusal, the overlap shift and info text. `info_text=` is exposed (None follows `presentation`). | f27f56dc |
| WP4 → WP3 | Call the duplicate-device-I/O hook from `review_m4l` | **Done.** It runs at the top scope of device reviews (not helper abstractions). `duplicate_device_io` is added to the Q40 rule tuple in `test_m4l_device.py`, so builder output is checked to stay clean. | f27f56dc |
| WP4 → WP3 | Q40 IN-03 `parameter_initial_enable` | **Done.** `param_range` checks `parameter_initial` only when `parameter_initial_enable` is truthy. `test_param_range` was updated to the new contract. | f27f56dc |
| WP3 follow-up | LFO depth into a filter cutoff must not be judged a gain stage | **Done**, within the CR-01 oscillator gate. New `dsp_critic._PARAMETER_INLETS` lists the frequency, Q and delay inlets taken from DB digests: lores~ 1-2, svf~ 1-2, onepole~ 1, reson~ 2-3, cross~ 1, comb~/allpass~ 1, filtercoeff~ 0 and 2, plus the mc. forms. reson~ inlet 1 (input gain) and every filter's audio inlet 0 are still judged as gain stages. | 88080d60 |
| WP4 → WP1/WP2 | Tabs decision: `original=` through Layer 5, hooks and the save gate | **Done.** `validate_patch(original=)` forwards each codebox's loaded code to `validate_genexpr(original=)`, keyed by scope box-id path + container id + codebox id. The save gate validates both sides with `original=baseline`, so a new tab line in a codebox that already had tabs is now a new blocker. Before, both sides gave one error with the same key, so it saved. `validate_file` and `validate_code_file` treat the file on disk as loaded; `validate_code_file(loaded=False)` opts out. | c0ff0a0b |
| WP4 | `write_gendsp` should pass `original=` | **Not needed.** `write_gendsp` runs no GenExpr check on its own codebox. The gate's Layer 5 skips the top-level codebox of a `.gendsp`, as documented in severity-contract.md. Nothing there can take `original=`. | — |
| WP4 → WP2 | `_edit_gendsp_in_place` codebox inlet count (IN-02) | **Done, adjusted to evidence.** Two MAX-resaved, user-confirmed files (granular-engine, q29-grow) keep `numinlets: 0`, so forcing `max(1, n_in)` would break the byte-identical no-op save (WR-08 test). The fix: never *write* 0, keep an existing 0 or 1 when there are no inputs, and stop treating a codebox's placeholder 1 inlet as a port. Before this, editing a 0-input `.gendsp` added a spurious `in 1` (reproduced). | c0ff0a0b |
| WP1 → WP2 | `hooks._finding_key` uses the structured key | **Confirmed already done** on main (WP2): `(origin, rule, box_ids + removal ids, port, removal, path)`. I restored the quickfix docstring claim. | c0ff0a0b |
| WP1 → WP2 | Pass `patch_path` through the save gate and `validate_file` | **Done.** It now goes through `_blocking_findings`, `_gate_report` (both sides) and `_run_save_gate`, and `validate_file` passes the file's path. Q23 D3 is now effective on the save path: an unknown name that no project abstraction resolves is an error, so a new file with one is refused. Nothing in the suite or the committed corpus changed. | c0ff0a0b |
| WP6 → WP2 | `test_framework_file_byte_identical` can never pass | **Done.** The non-strict xfail is removed. The test is parametrized over the two framework-written 2-space golden fixtures (`tests/fixtures/expected/simple_synth.maxpat`, `subpatcher_example.maxpat`) and asserts the 2-space expanded layout. I mutation-checked it: it fails when `format_patch_text` ignores the original layout. | e6914516 |
| WP5 | conftest `slow` marker description | **Done:** "release archive build, full repo smoke sweep". | e6914516 |
| — | Non-strict xfails that xpass | **None remain.** The base run had 0 xpassed. The only non-strict xfail left was the round-trip one above, and it is removed. The other xfails are strict (4 bassoon, integration allowlist) or a runtime `pytest.xfail` (round_trip:1481). | e6914516 |
| WP4 → WP5 | Remaining upper-case constants in the interpreter | **Done.** `GEN_CONSTANTS` now covers `genexpr_parse.BUILTIN_CONSTANTS`: every lower-case name, phi, and each upper-case alias with the same float. The `CONSTANTS` assert is unchanged. | 93bc52e2 |
| WP5 | `// smoke:` comments on swing-generator / subdivider, flip the pinned verdict | **Done.** `// smoke: in1=phasor:2 control out1` was added as the first codebox line through `write_gendsp`; the diff is one line per file. In `repo_smoke_verdicts.json`, swing-generator `all_corners_0.25s` goes from fail to pass, and the `_comment` is updated. A new test smokes both files at every corner. | e8c17584 |
| WP6 | Malformed patch in a `/max-verify --live` batch | **Done.** `scan_patch` now parses through `max_bridge._load_patch`, so any non-patch input raises ValueError. `run_live` reports OSError/ValueError from it as status `refused` with `cannot read <path>: ...`, and the batch continues. | c396c53b |

Not taken, because they were optional and outside this list: WP2's `Box._derive_outlet_types` → `saved_outlet_type()`, and `layout_critic` using `build_panel_layers(gradients=True)`.

## Contract changes (tests updated on purpose)

- `tests/test_ud6_wp2_patcher.py::test_paints_unknown_background`: an untinted textbutton is a known theme fill now, and textedit stays unknown.
- `tests/test_m4l_device.py::test_param_range`: the cases that check the initial value pass `parameter_initial_enable=1`. `Q40_RULES` now includes `duplicate_device_io`.
- `tests/test_round_trip.py::test_framework_file_byte_identical`: repointed, as above.

## New tests

`tests/test_ud6_wp7a_{db,contrast,m4l,dsp,tabs,live}.py` and `tests/dsp_sim/test_ud6_wp7a_{constants,timing_patterns}.py`. All of them were red before their fix.

## Doc impacts for WP8

- **db-maintenance.md:** no new mechanism. The zplane~ / mc.range~ / bach.slice entries carry `_evidence` keys.
- **CLAUDE.md "Text Contrast" + ui-presets.md "Text Contrast Resolution":**
  - Untinted number/flonum resolve to their 0.125 theme fill and textbutton to 0.262 (`aesthetics.THEME_FILLS`).
  - The layout critic now skips self-painted unknown-colour boxes, as the repair pass already did.
- **severity-contract.md:**
  - New M4L warning `duplicate_device_io`.
  - `param_range` honours `parameter_initial_enable`.
  - Gain safety: a `*~` that feeds a filter's cutoff/Q/delay inlet is not a gain stage.
  - Save gate (§5): `patch_path` is passed, so an unresolved unknown object refuses a new file or a save that adds one.
  - Tabs: loaded tab lines warn and new tab lines block, now also in the gate (`original=` on both sides).
  - `validate_file` / `validate_code_file` treat disk files as loaded. Note `validate_code_file(path, loaded=False)` for code just generated.
- **TECHNICAL.md:** `validate_patch(original=)`; `validate_code_file(loaded=)`; `add_m4l_device(info_text=)`; the `export_amxd` helper-abstraction error.
- **CLAUDE.md M4L section:** `export_amxd` refuses a live.thisdevice-only helper abstraction unless `kind=` is given.
- **CLAUDE.md Gen~ / genexpr-rules.md:** a `.gendsp` edit never writes codebox `numinlets: 0`, and 0-input codeboxes no longer gain an `in 1`. Also mention the `// smoke:` directive on pattern files (WP5's doc item).
- **dsp_sim README:** the interpreter knows every upper-case constant alias.
- **max-verify.md:** a malformed patch in a `--live` batch is listed as refused (`cannot read`).

## Needs confirmation in MAX

1. **Theme fills:** an untinted `number` / `flonum` really renders on 0.125 and an untinted `textbutton` (off state) on 0.262 in the Max 9 default theme. These values come from the refpage `dynamiccolor_default` + `default.maxtheme`, not from a screenshot. Check: screenshot a new patch with one of each.
2. **reson~ inlet 1 is an input gain** (kept as a gain stage) and lores~/svf~ inlet 2 is resonance (exempt). Both come from DB digests. Low risk.
3. **A 0-input codebox with `numinlets: 1`** written by `write_gendsp` loads and compiles. MAX's own help patches use this shape, so it is expected to work.

## Self-Check: PASSED

- All 9 commits are present in `git log 2f0aa05b..HEAD`: d3aaddef, cc8d9fad, f27f56dc, 88080d60, c0ff0a0b, e6914516, 93bc52e2, e8c17584, c396c53b.
- All 8 new test files exist.
- Full suite on Python 3.10.19 and on 3.14.2: 7342 passed, 1 skipped, 4 xfailed, 0 xpassed.
