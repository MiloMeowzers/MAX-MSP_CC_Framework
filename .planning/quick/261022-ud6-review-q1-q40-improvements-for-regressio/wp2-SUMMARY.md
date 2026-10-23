---
quick_id: 261022-ud6
package: WP2
area: patch model + save path
status: complete
branch: worktree-agent-a7b33c50b7b55040f
plan_head_before: 8ddcdc496ab59093bbd9b28f74ed6e0d99e50cb9
commits: 8
tests_added: tests/test_ud6_wp2_patcher.py (80 tests) + 2 legacy-layout fixtures
---

# WP2 (patch model + save path): fixes for review-patcher.md

All 16 findings in review-patcher.md are fixed: CR-01, WR-01..WR-09 and IN-01..IN-06. IN-04, IN-05 and part of WR-09 needed edits to docs outside WP2's ownership, so they are handed to WP8. The spec gaps for Q6, Q7/Q33, Q27, Q29 and Q36 are closed. Every fix was written test-first and failed before the change, except the IN-03 diff kind and the new maxjson writer functions, where the tests were written after the code.

## Finding → fix

| ID | Fixed | How | Commit |
|----|-------|-----|--------|
| CR-01 | yes | `replace_box` / `replace_box_safe` check the embedded patcher before changing anything. If the old and new names are the same, or the swap is `gen~` <-> `mc.gen~`, the inner patcher moves to the new box: `_parent_box` is repointed and `saved_object_attributes`, I/O and outlettype go with it, with `signal` <-> `multichannelsignal` following the mc.* side. Any other replacement raises `ValueError` and the patch is untouched. | 8cb5ae1d |
| WR-01 | yes | Gate path elements are now `(box id, maxclass)`, never the box text. Display labels come from a new `_path_labels(d)`. Swapping inlets and renaming the subpatcher in the same edit is refused. A rename on its own produces no cord-removed warning. Verified on a scratch copy of `dbap-source.maxpat` obj-155. | 53a03a3f |
| WR-02 | yes | The replacement box reuses `old_box.id`. A pre-existing blocker in `slot.maxpat` (buffer~ obj-1) saves after `replace_box_safe` (scratch copy). | 8cb5ae1d |
| WR-03 | yes | `format_patch_text` returns the original text when `json_identical(parsed, new)`. New writers: `maxjson.dumps_legacy` (Max 5–9.0.x tab layout) and `dumps_expanded`. `RawSpellings` keeps the file's own number and string spellings per key context, e.g. `11.595186999999999` and `";"`. `save_patch_roundtrip` keeps CRLF and never rewrites a file whose content is unchanged. `edit_patch` decides no-op on content. See the measurements under Verification. | 215780c2 |
| WR-04 | yes | `finalize_patch(is_new=True)` calls `layout._check_layout_allowed` first unless `force_layout`, so a refused patch is never restyled. | ee8b4bd2 |
| WR-05 | yes | `modify_box(args=)` on textbutton, live.text, live.comment or textedit (`TEXT_UI_MAXCLASSES`) sets the text with no prefix and keeps the size. Any other non-newobj UI class raises `ValueError` before any change and points to `extra_attrs`. | 1d46166a |
| WR-06 | yes | `extra_attrs` keys `patching_rect`, `text` and `saved_object_attributes` now set the model fields. `id`, `maxclass`, `numinlets`, `numoutlets`, `outlettype` and `patcher` raise before any change. `text` on a newobj raises and points to `args=`. | 1d46166a |
| WR-07 | yes | Edit sessions recolour only boxes the session added (id not in the file) that carry an explicit textcolor (locked decision B11). `paints_unknown_background()` skips bach.roll, jit.cellblock, an unfilled textbutton and similar boxes in every contrast pass. `gradient_stops()` scores text against both stops (bgfillcolor `type: gradient`, or `mode: 1` grad1/grad2) and keeps an explicit colour when no candidate reads on both. | e2378a24 |
| WR-08 | yes | Auto-detected port counts never fall below the codebox's existing count. Surplus `in N` / `out N` boxes are removed only when the count is given explicitly. Codebox fields are written only when they change. Writing back each file's own code leaves all 13 committed single-codebox `.gendsp` files byte-identical, including granular-sched and granular-engine. | aaa48f59 |
| WR-09 | partly | `max-patch-agent/SKILL.md` and `/max-build` (`.claude/commands/max-build.md`) now document `LayoutRefusedError`, `force_layout=True` for large new builds, and `is_new=False` / `edit_patch` for anything loaded from disk. `max-dsp-agent` and `max-ui-agent` still need the same note (WP8). | ee8b4bd2 |
| IN-01 | yes | A loaded box with no `patching_rect` is still written without one until its rect changes. | ca1c4cdb |
| IN-02 | yes | `replace_box` keeps the size for a same-maxclass fixed-size UI class (live.dial obj-33 stays 50×48) and for unchanged text. | 8cb5ae1d |
| IN-03 | yes | New diff kind `cord_attrs` (order, hidden, color, ...) renders as `~ cord a:0 -> b:0 attrs color,hidden,order`. | ca1c4cdb |
| IN-04 | handoff | The code already documents `Raises: RuntimeError`. The doc notes belong in `max-iterate.md` and `max-test.md` (WP8). | — |
| IN-05 | handoff | Stale docs, all owned by WP8. | — |
| IN-06 | yes | Port boxes that `write_gendsp` adds step right along the port row until they clear every box. | aaa48f59 |

## Spec gaps closed

- **Q29 (B9):** a no-op save is byte-identical for any layout: MAX 9.1+, Max 5–9.0.x tabs, CRLF and the expanded layout. This was a locked decision.
- **Q29 (B4):** `replace_box` keeps the box id and the embedded patcher.
- **Q29 (B8):** `write_gendsp` with unchanged code is a true no-op and never shrinks ports.
- **Q6:** the no-prefix text rule now covers text-bearing UI boxes.
- **Q7 / Q33 (validation IN-01):** `_finding_key` uses `(origin, rule, sorted box_ids + removal ids, port, removal, path)` whenever a result has a non-empty `rule` and `box_ids`. ValidationResult fields are read with getattr, so the key works with or without WP1's new fields. It falls back to the text template only when those fields are missing.
- **Q27:** layout refusal is atomic.
- **Q36:** the contrast pass follows B11.

## Verification

All writes went to scratch copies under the session scratchpad. Nothing was written under `patches/`.

- **No-op saves on committed patches:** all 77 committed patch files passed through `save_patch_roundtrip` and an empty `edit_patch` unchanged, with no write and no save. This used a scratch git repo copy of `patches/`.
- **Contrast on moved boxes:** moving every top-level box 1 px in an `edit_patch` session flipped 0 textcolors. The review measured 42 flips across 9 patches before this fix.
- **Legacy writer on user files:** `dumps_legacy` + `RawSpellings` reproduces all 262 MAX-saved tab-layout files in ~/Dev, ~/Projects and ~/Documents byte for byte (Max 5.1–9.0.7, CRLF normalised).
- **Legacy writer on package files:** 2892 of 3279 package files match. The other 387 are script-written help files (RNBO stray blank lines, bach space indents). A no-op save still leaves these untouched.
- **No-op saves on legacy copies:** 151 of 151 sampled legacy files, `brainSCI.maxpat` included, came through `save_patch_roundtrip` and `edit_patch` byte-identical.
- **Legacy edit diff:** a one-box move changes exactly one line, and CRLF is kept.
- **Full suite:** see "Test results" below.

## Contract changes (tests updated on purpose)

- `test_patcher.py::test_replace_removes_old_box` now checks that the replacement keeps the old id.
- `test_round_trip.py::test_modify_preserves_other_boxes` now passes args to a newobj. A panel refuses args.
- `test_edit_session.py::test_contrast_touched_only` follows the B11 contract: moved, presentation and default-text comments are not recoloured, and an added explicit colour is fixed.
- `test_edit_fidelity.py` port-removal tests pass explicit `num_inputs` / `num_outputs`.
- `test_patch_diff.py::test_diff_kinds_complete` includes `cord_attrs`.

## Handoffs

- **WP3 (critics):**
  - `layout_critic` text-contrast check: use `aesthetics.paints_unknown_background(maxclass, box)` to skip self-painted boxes. Today bach.roll's black-on-white text is scored against the canvas, a false positive.
  - Optionally build its layers with `build_panel_layers(..., gradients=True)` so gradient panels are scored on both stops. Its default call is unchanged.
- **WP1 (validation):** `hooks._finding_key` reads `ValidationResult.rule` / `.box_ids` / `.port` with getattr. Once WP1 adds those slots, keys become structured automatically. Keep `rule` a non-empty str and `box_ids` an iterable of real ids.
- **WP8 (docs):** see "Doc impacts".

## Doc impacts (for WP8; WP2 did not edit CLAUDE.md, TECHNICAL.md or references)

1. **CLAUDE.md Rule #8 and `shared-capabilities.md`:**
   - `replace_box` / `replace_box_safe` keep the box id and the size (same fixed-size UI class or unchanged text).
   - They move an embedded patcher only for the same name or `gen~` <-> `mc.gen~`, and otherwise raise `ValueError`.
   - `max-iterate.md:113` should say they rewire any in-range cord (IN-05).
2. **CLAUDE.md Rule #5 and `max-9.2-changes.md` / `TECHNICAL.md` save sections:**
   - A no-op save is byte-identical for Max 8 / 9.0.x tab-layout and CRLF files too.
   - Edits keep the file's layout (legacy writer) and number/string spellings.
   - An unchanged file is not rewritten.
   - `maxjson` now exports `dumps_legacy`, `dumps_expanded`, `detect_layout`, `RawSpellings` and `json_identical`.
3. **CLAUDE.md "Text Contrast" (B11) and `ui-presets.md` "Text Contrast Resolution" (`ui-presets.md:172` is stale):**
   - `edit_patch` recolours only boxes the edit added that carry an explicit textcolor.
   - Comments without a textcolor are never given one.
   - Self-painted objects with no fill attribute (`paints_unknown_background`) are skipped.
   - Gradient panels are scored on both stops (`gradient_stops`), and an explicit colour is kept when nothing reads on both.
   - `repair_text_contrast` is still whole-patch and opt-in.
   - The CLAUDE.md line telling users to call `repair_text_contrast(patcher)` on edited patches contradicts B11.
4. **`severity-contract.md:83` and `TECHNICAL.md:468`:** gate matching is now structured `rule + box_ids + port + path`, with a text template only as the fallback. Gate patcher paths key on box id + maxclass, so a rename doesn't matter.
5. **`max-dsp-agent/SKILL.md:277` and `max-ui-agent`:** add the `LayoutRefusedError` / `force_layout=True` note (WR-09; copy the max-patch-agent wording).
6. **`max-iterate.md:145` and `max-test.md:33`:** `auto_commit_patch` raises `RuntimeError` on git failure (IN-04).
7. **`proven-forms.md:123` and `shared-capabilities.md:33`:** `finalize_patch(is_new=False)` routes only new or touched unrouted cords and never regenerates midpoints (IN-05).
8. **`modify_box` docs (`shared-capabilities.md`, `max-iterate.md`):**
   - `args` on textbutton / live.text / live.comment / textedit sets the text.
   - `args` on any other UI box raises; use `extra_attrs`.
   - `extra_attrs` `patching_rect` / `text` / `saved_object_attributes` set the model fields, and structural keys raise.
9. **`write_gendsp` docs:** auto-detected counts never shrink ports. Pass explicit `num_inputs` / `num_outputs` to remove ports.
10. **Patch diff docs:** new kind `cord_attrs`.

## MAX-confirmation items

- Open a Max 8 / 9.0.x patch edited through the legacy writer (e.g. a scratch copy of an SCI patch with one box moved) and confirm MAX loads it, then confirm MAX's own re-save diff is limited to MAX's normal re-save changes.
- `gen~` -> `mc.gen~` via `replace_box_safe`: confirm the moved embedded gen patcher compiles in mc.gen~ and the outlet shows as multichannel.
- A textbutton whose text was set via `modify_box(args=...)` shows the new label at its old size.

## Test results

Full `python3 -m pytest -q` at ca1c4cdb gave the same result on both interpreters: **6367 passed, 5 xfailed, 1 xpassed**. The baseline at 8ddcdc49 was 6287 passed, 5 xfailed, 1 xpassed; the 80 extra tests are the new `tests/test_ud6_wp2_patcher.py`.

| Interpreter | Time |
|---|---|
| Python 3.10.19 (uv venv) | 279 s |
| Python 3.14.2 | 207 s |

The 1 xpassed is the existing non-strict xfail `test_max_saved_file_byte_identical`.
