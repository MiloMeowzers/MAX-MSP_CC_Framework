---
phase: quick-261016-d3y
plan: 01
subsystem: src/maxpat (hooks, patcher, builders, new maxjson)
tags: [Q29, B4, B8, B9, B10, edit-fidelity, json-layout, gendsp, replace_box, add_box]
status: complete
requires: [Q28 change tracking, EditResult.parent_orphaned, port sync]
provides:
  - maxjson.dumps_max / has_expanded_arrays (MAX 9 JSON layout)
  - hooks.format_patch_text (per-file layout choice; used by save_patch_roundtrip and write_gendsp)
  - write_gendsp in-place round-trip of an existing .gendsp (GendspWriteResult.orphaned)
  - replace_box identity carry (_carry_box_identity) and replace_box_safe in-range rewire with type gate
  - add_box overlap-only nudge (_nudge_off_overlap, Box.nudged_from, BoxMovedWarning)
affects: [every save_patch_roundtrip / write_gendsp caller, every replace_box(_safe) and add_box caller]
tech-stack:
  added: []
  patterns: [layout-preserving serialization, identity whitelist on replace, type-gated rewire]
key-files:
  created:
    - src/maxpat/maxjson.py
    - tests/test_edit_fidelity.py
  modified:
    - src/maxpat/hooks.py
    - src/maxpat/__init__.py
    - src/maxpat/patcher.py
    - src/maxpat/builders.py
    - tests/test_save_gate.py
    - tests/test_save_safety.py
    - tests/test_patcher.py
    - tests/test_claude_md.py
    - CLAUDE.md
    - TECHNICAL.md
    - .claude/skills/references/shared-capabilities.md
    - .claude/skills/max-dsp-agent/SKILL.md
    - .claude/skills/max-patch-agent/SKILL.md
decisions:
  - "Q29 PD-2: new files are written in MAX 9 layout; files keep their own layout (expanded or MAX) on save"
  - "Q29 PD-3: write_gendsp raises ValueError on a .gendsp that is not single-codebox (no regenerate flag); surplus port boxes feeding the user's graph are kept"
  - "Q29 PD-4: replace_box carries varname + jbox common attrs, valid colours and parameter blocks; fonts not carried"
  - "Q29 PD-5: replace_box_safe rewires every in-range cord except signal-into-control-only (validation mirror); rewired cords appended to lines"
  - "Q29 PD-6: add_box moves only on a real overlap; BoxMovedWarning only for explicit (non-origin) positions; _auto_position still snaps"
metrics:
  duration: ~40 min
  completed: 2026-10-16
actuals:
  tokens: 23103
  tasks: 3
  commits: 3
plan_head_before: 6438377ffcb4703b67b35ae7c1de77ac4b288aa7
plan_head_after: a5787ae888157b8151dad22fc205b0d464945b1e
---

# Phase quick-261016-d3y Plan 01: Edit fidelity II (Q29) Summary

Saves now keep each file's own JSON layout, so a no-op save is byte-identical whether MAX or the framework wrote the file last. MAX-saved files use the new `maxjson.dumps_max` writer. write_gendsp edits an existing .gendsp in place. replace_box keeps the box's identity, and replace_box_safe rewires every cord whose index still exists. add_box moves a box only when it really overlaps another, and reports the move.

## What changed

- **B9 (Task 1, b22df699).**
  - New `src/maxpat/maxjson.py`:
    - `dumps_max(obj, indent)` writes MAX 9's layout: scalar arrays inline, and the closing pad of an empty dict inside the braces.
    - `has_expanded_arrays(text)` detects the json.dumps layout.
  - New `hooks.format_patch_text(patch_dict, original_text=None)`. It takes the indent from the original text, uses json.dumps only when the original was in expanded layout (dumps_max otherwise), and adds a trailing newline only when the original had one.
  - `save_patch_roundtrip` and write_gendsp's new-file path write through format_patch_text, which is also exported from `src.maxpat`.
  - Checks:
    - every bundled Max help patch except 3 (973/976 `.maxhelp`) reproduces byte for byte;
    - all repo patch files (69 or more) have byte-identical no-op text;
    - both MAX-saved reference files are byte-identical in memory and as tmp copies.
- **B8 (Task 1).** write_gendsp on an existing path no longer regenerates the file:
  - It loads the file with read_patch and requires exactly one top-level codebox (otherwise ValueError, and nothing is written).
  - It sets the codebox `code`, numinlets, numoutlets and outlettype.
  - It adds missing `in N`/`out N` boxes, wired to the codebox.
  - It removes surplus port boxes, but only those whose only cords go to the codebox.
  - It removes cords on codebox ports that no longer exist.
  - It saves through save_patch_roundtrip, so the stale check, save gate, layout and auto-commit all apply.
  - Removed cords are in `GendspWriteResult.orphaned` (`[]` for a new file).
  - A no-op write of gong-engine.gendsp is byte-identical, and its `v1.12.1` comment survives.
- **B4 (Task 2, aae2c21c).**
  - `replace_box` takes an identity snapshot before removal, then `_carry_box_identity` restores:
    - the list index (z-order);
    - presentation and presentation_rect;
    - varname and the jbox common attributes;
    - colour keys that are valid on the new object (in the DB, same maxclass, or `bgcolor` on a newobj);
    - parameter_enable/mappable and `saved_attribute_attributes` (filtered; `valueof` only when the new object is parameter-capable).
  - `replace_box_safe(rewire="auto")` rewires every orphan whose indices are in range, keeping midpoints, order, colour, hidden and extra_attrs.
  - `_rewire_type_gated` mirrors validation's "Signal outlet to control-only inlet" rule, including the lenient branch for non-overridden `~` objects.
  - Plain replace_box still orphans every cord (Rule #8). parent_orphaned is still passed through.
- **B10 (Task 2).**
  - `add_box` passes float x/y and calls `_nudge_off_overlap`:
    - no move unless the box truly overlaps another (positive-area intersection);
    - on a real overlap it steps 15 px down until it has 5 px clearance (wrapping to the next column after y 2400).
  - `Box.nudged_from` records the requested position.
  - A `BoxMovedWarning` (exported) fires for every non-origin move.
  - `_find_clear_position` and `_auto_position` are unchanged.
- **Docs (Task 3, a5787ae8).** Exactly the 10 DOCLINE replacements:
  - CLAUDE.md lines 106 and 129;
  - test_claude_md.py line 166 (3 anchors);
  - shared-capabilities.md line 238;
  - max-dsp-agent SKILL.md line 36;
  - max-patch-agent SKILL.md line 39;
  - TECHNICAL.md lines 306, 335, 357 and 469.

  numstat shows 1/1 per DOCLINE. CLAUDE.md is 27406 bytes.

## Test evidence

| Run | Last line |
|---|---|
| Q/baseline-pytest.txt | 5060 passed, 5 xfailed, 1 xpassed, 30 warnings in 93.14s |
| Q/pytest-t1.txt | 5089 passed, 5 xfailed, 1 xpassed, 30 warnings in 93.81s |
| Q/pytest-t2.txt | 5107 passed, 5 xfailed, 1 xpassed, 39 warnings in 94.23s |
| Q/final-pytest.txt | 5110 passed, 5 xfailed, 1 xpassed, 39 warnings in 91.32s |

The xfail/xpass split is unchanged. There are 47 new tests in tests/test_edit_fidelity.py, and the 3 anchor cases bring the total to 50 (5060 + 50 = 5110).

**Red evidence:**
- **red-t1: 28 failed, 1 passed.** That run had maxjson.py held out of the tree so it was a true red. The one pass is the green guard `test_expanded_file_stays_expanded`, which matches HEAD behavior.
- **red-t2: 15 failed, 226 passed** (test_edit_fidelity + test_patcher). Green guards that passed at HEAD by design:
  - `test_plain_replace_box_still_orphans_every_cord`;
  - `test_manual_returns_every_cord`;
  - `test_equal_count_unchanged`;
  - `test_unverified_msp_source_stays_rewired` (ears.split~);
  - `test_skip_overlap_check_never_moves`;
  - every existing TestB9/B8 test.
- **red-t3: 3 failed** (the 3 new `test_rule_anchor_present` cases), with only the anchors line applied.

**Existing-test edits (and nothing else):**
- PD-7.1: `tests/test_patcher.py::TestReplaceBoxSafe::test_auto_mismatched_io_falls_back_to_orphans` became `test_auto_mismatched_io_rewires_in_range_cords`.
- PD-7.2: `tests/test_patcher.py::TestAddBoxOverlapDetection::test_add_box_snaps_to_grid` became `test_add_box_keeps_requested_position`.
- PD-7.3: `tests/test_save_gate.py::TestNewBlockerGate::test_force_bypasses_with_warning` now computes the expected text as `format_patch_text(new_dict, T)`, and its import line adds `format_patch_text`.
- PD-7.4: `tests/test_save_safety.py::TestStaleFile::test_force_overwrites_with_warning` gets the same change.
- The 3 RULE_ANCHORS added on tests/test_claude_md.py line 166.

The two reference files (FDNVerb.maxhelp, sample-layers.maxpat) still match HEAD. No `patches/**` file changed, and the stash list is unchanged.

## Decisions to confirm

- **PD-2:** New .maxpat/.gendsp files are now written in MAX 9 layout (inline scalar arrays). Existing files keep their own layout. The 3 legacy Max 8 tab-indented layouts (none in the repo) are reformatted to MAX 9 layout on their first save. Alternative (B): keep the expanded json.dumps layout for new files.
- **PD-3:** write_gendsp raises ValueError on an existing .gendsp that does not have exactly one top-level codebox. There is no regenerate flag; delete the file to regenerate it. A surplus `in N`/`out N` box that also feeds the user's own gen graph is kept, and only its codebox cords are removed.
- **PD-4:** replace_box's identity whitelist includes the jbox common extras (hint, annotation, hidden, ignoreclick, background) besides varname and color/textcolor. Fonts are not carried, and neither is an inlet's `comment`.
- **PD-5:** replace_box_safe's type gate leaves signal-into-control-only cords orphaned instead of rewiring them, mirroring validation. Rewired cords are appended to `lines`, so they do not keep their old index.
- **PD-6:** BoxMovedWarning fires only for explicit (non-origin) positions; moves from the default (0, 0) are silent but still record `nudged_from`. `_auto_position` / `_find_clear_position` still snap to the 15 px grid.

Please answer for each of PD-2 to PD-6:
- (a) accept as built;
- (b) reopen with the alternative named above;
- (c) reopen with a different change (describe it).

## Behavior changes

- New .maxpat and .gendsp files are written in MAX 9 layout. New .gendsp files used to be 2-space json.dumps; they are now 4-space MAX layout.
- An existing .gendsp passed to write_gendsp is edited, not replaced.
- add_box no longer snaps explicit positions to the 15 px grid, and no longer treats a gap under 10 px as a collision.
- replace_box_safe now rewires cords when the I/O counts differ, and replace_box(_safe) keeps the box's list index and identity attributes.

## Deviations from Plan

**1. [Rule 1 - Test bug] Non-str key test collided True with 1**
- **Found during:** Task 1 green.
- **Issue:** The planned `dumps_max({True: 1, None: 2, 1: 3, 1.5: 4})` collapses `True` and `1` into one dict key.
- **Fix:** One dict per key (True, False, None, 1, 1.5). The test is in the new file only.
- **Commit:** b22df699

**2. [Rule 2 - Test strength] Two B8 tests would have passed at HEAD**
- **Found during:** Task 1 red.
- **Issue:** `test_added_input_grows_ports` and `test_explicit_counts_override_detection` also pass under regeneration.
- **Fix:** Both now also assert that the `v1.12.1` comment survives, so they are red at HEAD. The test is in the new file only.
- **Commit:** b22df699

**3. [Execution note] Red run for Task 1 held maxjson.py out of the tree**
- maxjson.py was written before the red run (out of TDD order). It was moved to the scratchpad for the red run and restored afterwards, so red-t1 reflects HEAD behavior.

## Doc impact not edited (PD-8)

- The stale json.dumps comments at tests/test_round_trip.py lines 44-60 and in TestSubpatcherByteIdentity.
- The non-strict xfails in TestFileLevelRoundTrip.
- src/maxpat/project.py:88 and src/maxpat/externals.py:271 still write new files with json.dumps (expanded layout). Their next framework save keeps that layout.

## Follow-ups (PD-10)

- Legacy Max 8 layout (tab indent, `"key" : value`).
- Keeping rewired cords at their old index in `lines`.
- Carrying fonts, or an inlet's `comment`, on replace.
- Switching the project.py / externals.py new-file writers to format_patch_text.
- A CLAUDE.md Rule #4 note about BoxMovedWarning.

## MAX confirmation needed (rule 9)

1. Open a new patch saved by the framework, re-save it in MAX without edits, and check that `git diff` is empty or shows only MAX's own normalizations.
2. Open a .gendsp that write_gendsp grew by one output in MAX's gen editor. Check that the codebox compiles and the new outlet appears.
3. Use replace_box_safe on a parameter-enabled dial or live.dial. Check that its pattr / parameter binding (varname, valueof) still works.
4. Check that a meter~ placed 5 px right of a gain~ renders side by side.

## Python 3.10

Not runnable locally (3.14 only). Compatibility was checked with `ast.parse(feature_version=(3, 10))` on all 9 changed Python files.

## Known Stubs

None.

## Threat Flags

None. No new network, auth or file-access surface; edits stay within the plan's threat register.

## Self-Check: PASSED

- FOUND: src/maxpat/maxjson.py, tests/test_edit_fidelity.py
- FOUND commits: b22df699, aae2c21c, a5787ae8 (all `(Q29)`; files limited to files_modified, none under patches/; Q/q29-commit-files.txt)
- Task 3 verify block: VERIFY_RC=0 (doclines 10, bad [], count [])
