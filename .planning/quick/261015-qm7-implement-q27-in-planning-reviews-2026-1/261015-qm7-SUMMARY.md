---
phase: quick-261015-qm7
plan: 01
status: complete
subsystem: layout / sizing / layout critic / aesthetics
tags: [layout, rendered-rect, overlap-critic, contrast, panels, bpatcher, presentation, Q27]
requires: [Q26 (6912e583)]
provides:
  - "sizing.rendered_rect / is_max_saved: one rendered-geometry model shared by layout, add_box and the overlap critic"
  - "layout.LayoutRefusedError + apply_layout(force=) guard; finalize_patch(force_layout=)"
  - "control bands, 1600 px cap, decoration anchors, bpatcher-face skip, running presentation grid"
affects: [src/maxpat/layout.py, src/maxpat/critics/layout_critic.py, src/maxpat/hooks.py, src/maxpat/aesthetics.py, src/maxpat/builders.py, src/maxpat/patcher.py]
tech-stack:
  added: []
  patterns: ["footprint-based row packing", "pre-layout decoration capture + idempotent placement"]
key-files:
  created: [tests/test_layout_fixes_f1_f7.py]
  modified: [src/maxpat/sizing.py, src/maxpat/defaults.py, src/maxpat/patcher.py, src/maxpat/builders.py, src/maxpat/critics/layout_critic.py, src/maxpat/layout.py, src/maxpat/aesthetics.py, src/maxpat/hooks.py, tests/test_companion_role_layout.py]
decisions:
  - "PD-1: the status overlay is removed (not limited to UI pairs)"
  - "PD-7: MAX-saved message boxes keep their stored width in rendered_rect"
  - "PD-8: comments and panels stay out of the overlap critic"
  - "Control-feeding-control exclusion is order-independent: any candidate whose target is a candidate stays a row box"
metrics:
  duration: "~60 min"
  completed: 2026-10-15
actuals:
  tokens: 29000
  tasks: 3
  commits: 3
commits: 3
plan_head_before: 6912e583472d17244facbe39f205017b701e6aa0
plan_head_after: 40428815ffd00139d08dbe7b7fd8d6c903c64e6a
---

# Phase quick-261015-qm7 Plan 01: Q27 layout findings F1-F7 Summary

**One shared `rendered_rect()` (message `len*8+25`, comment 5.6 px/char + 1.6x wrap) behind add_box, the overlap critic and layout. Layout now refuses MAX-saved or >120-box patches unless forced, wraps at 1600 px, puts controls in an inlet-ordered band above their target, never re-lays out bpatcher faces, moves panels, headers and labels with their boxes, and picks text colours after layout. List-wrapped fills parse.**

## Commits

| Task | Commit | Message |
|------|--------|---------|
| 1 | 0db9d53a | fix(sizing): one shared rendered_rect for the add_box overlap check and the overlap critic (Q27) |
| 2 | 57d026a7 | fix(layout): control bands, no status overlay, bpatcher faces untouched, refusal guard, 1600 px cap and presentation grid; overlay readout presentation copy (Q27) |
| 3 | 40428815 | fix(layout): contrast after layout; panels, headers and labels move with their boxes; list-wrapped fills (Q27) |

Each commit touches only its own task's files. None touches `patches/`, docs or skills (Q/q27-commit-files.txt). The stash list is unchanged (empty before and after).

## What changed per finding

- **F1:** `_ROLE_COMPANION_MAP["status"]` is now `{companion: None, placement: None}` (the map still has six keys), and the overlay branch of `_place_companions` is deleted. A `dspstate~` -> `flonum` pair now lays the flonum out below its source, with no ignoreclick and no z-order change.
- **F2:** `_position_component` now packs per-box footprints:
  - each box's footprint is its rendered rect, plus its control band (W = group width, band = tallest control + v_spacing/2), plus its riders;
  - controls sit left to right from the target's x, ordered by inlet and then box order, with `h_gutter` gaps, rounded up to the grid;
  - a control feeding another control stays a row box.
- **F3:** finalize_patch(is_new=True) now runs `apply_auto_styling(contrast=False)`, then `apply_layout(force=force_layout)`, then `ensure_text_contrast` once, then assistance comments. apply_layout captures decorations before layout:
  - labels, headers and step markers ride the nearest content box within 40 px, else the smallest membered panel they sit in;
  - a membered panel is refit around its members and their riders, keeping its original pads.

  Decorations are placed provisionally in each component pass and then finally after snap and port restore, with exact offsets and no snapping. A safety translate clears any negative coordinate. Panels and `background: 1` boxes no longer count as routing obstacles.
- **F4:** the recursion skips `bpatcher` boxes. `p` subpatchers are still laid out, and `_skip_auto_layout` is still honoured.
- **F5:**
  - **Guard:** `LayoutRefusedError(ValueError)` is raised before any mutation, checking the whole recursion tree, with the reference text.
  - **Cap:** rows, component bands and the disconnected column all wrap at `30 + LayoutOptions.max_width` (1600).
  - **Presentation:** the presentation grid uses a running x offset and the tallest-row y.
  - **Shared geometry:** add_box measures both the new box and the existing boxes by `rendered_rect`.
  - **Overlap critic:** it uses rendered rects, plus the deliberate-overlay exemption (an ignoreclick box inside the other's stored rect, within 2 px).
- **F6:** `resolve_fill_color` unwraps `[{...}]` under bgfillcolor, grad1 and bgcolor, reads `color1` then `color`, and returns only valid colours.
- **F7:** `add_overlay_readout` copies the target's presentation_rect plus the offsets when the target is in presentation. Comment readouts serialize `"text": ""`.

## Suite results (last lines)

- Baseline (6912e583): `4872 passed, 5 xfailed, 1 xpassed, 29 warnings in 82.68s`
- Q/pytest-t1.txt: `4899 passed, 5 xfailed, 1 xpassed, 29 warnings in 84.43s (0:01:24)`
- Q/pytest-t2.txt: `4923 passed, 5 xfailed, 1 xpassed, 29 warnings in 84.55s (0:01:24)`
- Q/final-pytest.txt: `4937 passed, 5 xfailed, 1 xpassed, 29 warnings in 84.79s (0:01:24)`

The final total is the baseline plus the 65 new tests in tests/test_layout_fixes_f1_f7.py. The red runs were recorded before each fix: Q/red-t1.txt (24 failed), Q/red-t2.txt (21 failed), Q/red-t3.txt (12 failed).

## Corpus before/after (Q/triage.py, 69 files, review_patch all scopes)

| Kind | Base | After T1 | After T2 | Final |
|------|------|----------|----------|-------|
| Overlapping boxes (all scopes) | 436 | 405 | 405 | 405 |
| top level | 359 | 328 | 328 | 328 |
| nested | 77 | 77 | 77 | 77 |
| `--check` mismatch (all non-overlap review + every validate record) | 0 | 0 | 0 | 0 |

The PD-8 per-file deltas were verified exactly:

- **Removed (overlay exemption):**
  - gen-eq-mc -13;
  - gen-eq -13;
  - dbap-source -8;
  - disintegrate -1.
- **Added (rendered message width, 9.0.0 files):**
  - slice-voice obj-4/obj-6;
  - mixer-bus obj-23/obj-24;
  - bounce-outlet2-test obj-7/obj-8;
  - wormhole-remote-test obj-11/obj-12.

These are warnings, so no allowlist was needed and no patch file was touched.

## Bundle (Max 9.2, 3139 files, Q/bundle-*.json)

| Kind | Base | After T1 | Final |
|------|------|----------|-------|
| Overlapping boxes (warning) | 16302 | 18132 | 18132 |
| Low contrast text (warning) | 6676 | 6676 | 6703 |
| Low contrast text (note) | 73 | 73 | 73 |
| Presentation/patching contrast trade-off (note) | 5710 | 5710 | 5684 |
| RAISED | 0 | 0 | 0 |
| list-wrapped fill boxes (PD-10) | 20 | 20 | 20 |

- **Overlaps +1830.** 1070 of Cycling '74's own bundle files carry appversion 9.0.0, so `is_max_saved` reads them as generator-written and applies `len*8+25` to their messages. This only affects warnings. It is a limit of the PD-5 appversion heuristic, which the plan measured only on the corpus. The same files would also not be refused by the layout guard.
- **Contrast +27 warnings / -26 trade-off notes.** These come from the 20 list-wrapped panels now being recognized as surfaces (PD-10). The plan expected 22 list-wrapped fills; my counter counts boxes, not keys.

## PD-13 test edits (the only existing-test edits)

1. `tests/test_companion_role_layout.py::TestRoleDrivenCompanions::test_role_map_status_overlay` now asserts companion None and placement None.
2. `test_status_role_overlays_source` is renamed `test_status_role_no_overlay`. It still uses the monkeypatched status role, and asserts:
   - the readout does not intersect the source;
   - the readout has no ignoreclick;
   - the readout's y is greater than the source's;
   - `p.boxes[0]` is not the readout.
3. The module docstring's D-14 line now reads "status -> no companion (Q27 / F1 ...)".

`test_status_role_overlay_rect_not_aliased` passes unchanged.

## Deviations from Q27

- **PD-1.**
  - *Q27:* "remove the status-role readout overlay, or limit it to UI→readout pairs".
  - *Shipped:* removed, not limited.
  - *Evidence:* there are 115 status-role outlets on 56 objects. The only UI owners (waveform~, live.adsrui, mc.live.gain~, playlist~, spectroscope~) are displays that a 22 px flonum would hide. No status outlet forms a UI-control-plus-readout pair.
  - *Follow-up:* none; `add_overlay_readout` is the explicit path.
- **PD-6.**
  - *Q27:* "about 1600 px".
  - *Shipped:* the cap holds, except that a single box wider than the cap sits alone on its line and passes it.
  - *Evidence:* `TestF5WidthCap::test_oversize_box_terminates_alone_past_cap` (2000 px box; T-qm7-02). It terminates, and the oversize box is the only one past 1630.
  - *Follow-up:* none unless very wide single boxes become common.
- **PD-7.**
  - *Q27:* "Message boxes: len*8+25".
  - *Shipped:* the rule applies to generated (9.0.0) patches, add_box and layout. MAX-saved patches keep their stored message width.
  - *Evidence:* the 653 font-12 message boxes in the Max 9.2 help are 97.7% narrower than len*8+25 (median -35 px). The literal rule adds 77 corpus warnings, against 4 with the MAX-saved exception. The bundle shows the limit of this heuristic too: 1070 MAX-shipped files saved at 9.0.0 still read as generated (+1830 bundle overlap warnings).
  - *Follow-up:* the MAX check below. A stronger "generator-written" marker than appversion would also help.
- **PD-8.**
  - *Q27:* one shared rect for the overlap critic, with "Comments: ~5.6 px per character, plus the 1.6x wrap rule".
  - *Shipped:* rendered_rect implements the comment rule for layout and add_box, but the overlap critic still excludes comments and panels, so the rule never reaches it.
  - *Evidence:* including comments adds 1448 corpus warnings at the 5 px pad (166 with no pad), and `test_comment_and_panel_excluded_from_overlap` pins the exclusion.
  - *Follow-up:* a comment-overlap critic (PD-12).

Please accept each narrowing (PD-1, PD-6, PD-7, PD-8) or reopen it.

## Deviations from Plan (executor log)

**1. [Rule 2 - Robustness] The out-of-bounds check skips non-numeric rects.** Found during Task 1. The new purity/robustness test showed `review_layout` raising TypeError on a `["a","b","c","d"]` rect in `_check_out_of_bounds`. It now reads the rect through the same `_stored_rect` guard as the overlap check. Corpus output is unchanged (mismatch 0). File: src/maxpat/critics/layout_critic.py (commit 0db9d53a).

**2. [Rule 1 - Bug, own test] Section header expectation.** A filled comment covers *at least* its stored rect, so a 16 pt header is 24.67 px tall rendered against 24 px stored. The test now asserts `>=`, not equality.

**3. [Design detail] Control-feeding-control exclusion is order-independent.** Each pass removes every candidate whose target is a candidate (judged against the start-of-pass set), repeating until stable. A dial -> flonum -> print chain therefore stays as rows. Covered by `test_control_feeding_control_stays_in_rows`.

**4. [Design detail] Grid-preserving translations.** Component shifts and band moves, plus the negative-coordinate safety translate, are rounded to the grid. This keeps the "round x up, so the final snap leaves gutters" guarantee. A control's y aligns its footprint bottom, which is the control's height when it has no riders, so this matches the plan's `target y - gap - h`.

**5. [Observation] A box-anchored header joins its panel's tracked set.** On the evidence patch, the header sat 30 px above the panel. After layout the refit panel's top pad clamps to 0 at the header's top, so the header now sits on the panel's top edge. Offsets are exact (header (-18, -48) from cycle~) and contrast passes. This is how PD-3's pad rule works, but it changes how such a header looks: see the MAX checks.

**6. Extra tests beyond the behaviour list:**
- inner-patcher guard;
- control -> control chain;
- an 18-loadbang disconnected-band variant;
- a new message measured by its rendered width in add_box;
- rider-width reservation;
- panel-routing equality.

The test module binds `sizing.rendered_rect` / `is_max_saved` late, so the red runs show per-test failures instead of a single ImportError.

## Follow-ups (PD-12 and observed)

- Inlet alignment still uses the pre-layout child y (`_target_x_for_inlet_align` is unchanged).
- Companions (meter~ to the right) still reserve no footprint width.
- A comment-overlap critic (PD-8).
- Type-aware fill dicts (read `color` for type "color", `color1` for gradients).
- A stronger generator-written marker than appversion 9.0.0 (bundle evidence above).
- Docs (below).

## Doc impact (not edited, rule 8)

- **`.claude/skills/references/shared-capabilities.md`:**
  - the companion table still says status -> flonum overlay;
  - add_overlay_readout's presentation copy and empty comment text;
  - `finalize_patch(..., force_layout=)` and `apply_layout(force=)` / `LayoutRefusedError`.
- **`proven-forms.md`:** "no global apply_layout" is now enforced in code (the guard).
- **`ui-presets.md`:** the fill encodings now include list-wrapped dicts.
- **CLAUDE.md Rule #4:** the message width rule `len*8+25`, with the MAX-saved nuance (stored width kept).
- **TECHNICAL.md:** the layout-critic overlap rows (rendered rects, overlay exemption).

## MAX confirmation needed (rule 9)

1. An empty-text comment overlay readout (`add_overlay_readout(type='comment')`) loads, and displays the text it receives via `set ...`.
2. A `finalize_patch(is_new=True)` build with a panel, a header and labels looks right: the panel sits behind its chain, labels sit next to their boxes, and text is readable. Check especially a header that originally sat just above a panel (see executor deviation 5).
3. Optional: whether generated (9.0.0) message boxes really render at about len*8+25 px.

## Known Stubs

None.

## Threat Flags

None. There is no new network, auth or file surface. Every threat-register mitigation is covered by a test (robustness, termination, guard, purity) or by triage.

## Self-Check: PASSED

- The created and modified files exist: tests/test_layout_fixes_f1_f7.py, plus every src file listed above.
- The commits exist: 0db9d53a, 57d026a7, 40428815, all touching only src/maxpat and tests.
- Q/red-t1/t2/t3, pytest-t1/t2 and final-pytest are recorded. Triage `--check` was 0 after every task. The triage selftest passes.
- STATE.md / ROADMAP.md are not touched, per the quick-task orchestrator contract.
