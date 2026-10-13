---
phase: quick-261012-pkh
plan: 01
subsystem: maxpat-edit-path
tags: [edit-path, finalize_patch, modify_box, midpoints, assistance-comments, Q6]
status: complete
requires: []
provides:
  - "finalize_patch(is_new=False) that never clears midpoints (routes only new/added/moved-box cords)"
  - "modify_box(args=...) keep/recompute I/O rule + unchanged-text no-op + message/comment text"
  - "assistance comments written to _raw (reach disk)"
affects: [max-iterate, six agent skills' Output Protocol (Edited Patches)]
tech-stack:
  added: []
  patterns: ["load-time rect snapshot (Box._loaded_rect) for moved-box detection", "eligible-filter callable on _generate_midpoints"]
key-files:
  created:
    - tests/test_edit_keeps_user_work.py
  modified:
    - src/maxpat/hooks.py
    - src/maxpat/layout.py
    - src/maxpat/patcher.py
    - .claude/skills/max-patch-agent/SKILL.md
    - .claude/skills/max-dsp-agent/SKILL.md
    - .claude/skills/max-ui-agent/SKILL.md
    - .claude/skills/max-js-agent/SKILL.md
    - .claude/skills/max-rnbo-agent/SKILL.md
    - .claude/skills/max-ext-agent/SKILL.md
decisions:
  - "Q6 OQ1 answered A by the user: expr/vexpr follow the DB variable_io rule; the unchanged-text short-circuit protects re-applied args; changed-expression miscounts go to Q10 (C1)"
  - "Edit-path finalize never clears midpoints; a cord is routed only if it has none and is new or touches an added/moved box (moved = x/y differs from the load-time snapshot; resize alone is not a move)"
  - "modify_box keeps I/O and cords for content-defined boxes (embedded patcher, bpatcher, CONTENT_DEFINED_NAMES, unknown names, non-variable_io); recomputes only for DB variable_io objects"
metrics:
  duration: 6min
  completed: 2026-10-12
estimate:
  tokens: 80000
  tasks: 3
actuals:
  tokens: 10400
  tasks: 3
  commits: 3
plan_head_before: bc1ab6648afb43cf3bb788d95634fbb10b4ffac6
plan_head_after: 9c4885f37bde8eb34749abd4360fe726588a3e5b
---

# Quick 261012-pkh: Q6, the edit path keeps user work (B1, B2, B3)

The edit-path `finalize_patch` no longer erases hand routing. `modify_box(args=...)` no longer drops cords on content-defined boxes and no longer writes a `message `/`comment ` prefix. Inferred assistance comments now reach disk.

## Commits

| Task | Commit | Files |
|------|--------|-------|
| 1 (B1 + comments) | 12b3c92 | src/maxpat/hooks.py, src/maxpat/layout.py, src/maxpat/patcher.py, tests/test_edit_keeps_user_work.py |
| 2 (B2, B3) | 9c724c9 | src/maxpat/patcher.py, tests/test_edit_keeps_user_work.py |
| 3 (skills) | 9c4885f | the six agent SKILL.md files (step-3 line only) |

HEAD at dispatch was `bc1ab66` and stayed there: no other instance committed during the run. `git rev-list --count bc1ab66..HEAD` = 3.

## Test totals

- Baseline (HEAD bc1ab66): **2540 passed, 1 xfailed, 1 xpassed, 29 warnings**. Matches the planner's figure.
- After Task 1: 2547 passed, 1 xfailed, 1 xpassed, 29 warnings.
- After Task 2 and Task 3 (final): **2559 passed, 1 xfailed, 1 xpassed, 29 warnings**. The +19 passes are the new file. Warning count is unchanged.
- RED before Task 1 GREEN: 7 of 7 failed, each for the stated reason:
  - ji-harmonizer kept 0/367 midpoints;
  - the pre-existing line `('top', 0)` changed;
  - the moved-box B->C cord was rerouted to `[307, 146, 37, 146]`;
  - unmoved/resized straight cords were routed;
  - comments were `""` on disk (synthetic subpatcher and `p init/obj-26`).
- RED before Task 2 GREEN: 10 failed and 9 passed. The 9 passes were the 7 Task 1 tests plus the pack/trigger guards.
  - FDNVerb was 2/1 with both the same and changed args;
  - `p` and `js` went to 1/1, the abstraction to 0/0;
  - `_io_is_content_defined` was missing;
  - expr re-apply dropped to 1 inlet;
  - text was `message read drums.wav` / `comment New label`.

## Repro numbers, before -> after

- ji-harmonizer through `finalize_patch(is_new=False)`:
  - midpoints kept: 0/367 -> **367/367**;
  - straight cords routed: 9 -> **0**;
  - the serialized `lines` equal the file's in every patcher;
  - 15 empty port comments now serialize with text (`p init` 2, `p wtctl` 1, `p ratioset` 12).
- FDNVerb `gen~ FDNverb`, `modify_box(args=["FDNverb"])`: 2/1 and 40 cords -> **2/2 and 41 cords**. The same holds with changed args (`FDNverb2`). With the same args, patching_rect is unchanged.

## OQ1 resolution

**User answer: A** (recorded 2026-10-12). It is not a default resolution. `expr`/`vexpr` recompute through the DB rule only when their text changes. Re-applying identical args is a no-op, and there is a test for it.

## Live line references vs the spec

- `finalize_patch` is at `hooks.py:122` and `_finalize_midpoints_recursive` at `hooks.py:149-167` (spec 85-103).
- `modify_box` is at `patcher.py:555-659` (spec 590-625).

These matched the planner's observed facts at execution time.

## Implementation notes

- I added a small helper, `Patcher._set_assistance_comment(box, text)`, which writes both `extra_attrs` and `_raw`. It replaces the four inline assignments in `_populate_comments_recursive`. The behavior is exactly S2; it just avoids repeating the same two lines four times.
- In the synthetic assistance test, the inner chain is `inlet -> t b -> outlet` instead of `inlet -> print x -> outlet`. `print` has no outlet, so the plan's chain couldn't feed the outlet.
- I added one test beyond the plan, `test_resize_alone_is_not_a_move`. It pins down the S1 rule that a width change alone is not a move.

## Deviations from Plan

None functionally. The plan executed as written apart from the two test-construction notes above.

## Residuals (out of scope)

- A moved box's already-routed cords keep their old midpoints, which may now look stale. This is the spec's rule and was accepted as T-pkh-07.
- New cords that get bus-routed are spaced only against other new cords, not against existing bus cords.
- `expr`/`vexpr` miscount I/O on a *changed* expression because the arg_count rule counts tokens, not `$i/$f`. That belongs to Q10 (C1). `o.route` has no io rule.
- `modify_box(args)` on UI widgets other than message/comment still writes a text field.
- These belong to Q28/Q29:
  - replace_box loses identity and wiring (B4);
  - extra_attrs/fontsize changes are dropped on round-tripped boxes (B5);
  - shared `patching_rect`/`_raw` lists (B6);
  - port resync (B7).

## Doc impact (not edited, rule 8)

- `.claude/skills/references/shared-capabilities.md:25` still says the edit path "regenerates midpoints", and `:122` is related.
- `TECHNICAL.md:317` still says modify_box works "with I/O recomputation".
- The capability lines at `max-patch-agent/SKILL.md:44`, `max-dsp-agent/SKILL.md:75` and `max-ui-agent/SKILL.md:38` ("midpoints + comments (edit)") are loose but not wrong.
- `README.md:115`: the "preserving ... manual changes you've made in MAX" promise now holds for routing and cords. B4/B5 are still open.
- `.claude/commands/max-iterate.md:87` ("Preserves all positions and connections") is now true for modify_box. replace_box is still governed by Rule #8.
- J7 is moot. The interim advice to call only `populate_assistance_comments()` is no longer needed.

## Hand-offs

- **Q10**: fix the expr/vexpr io rule (C1). Under OQ1-A nothing needs removing from `CONTENT_DEFINED_NAMES`.
- **Q28**: change tracking. `Box._loaded_rect` can feed its moved/changed set.
- **Q29**: replace_box should keep midpoints and identity.

## Confirm in MAX (rule 9)

No patch file changed, so nothing is required. Optional checks:
- Open a patch with hand-routed cords and run `/max-iterate` to add one object. Reopen it in MAX and confirm the existing routing is intact and only the new cord bends.
- Hover over a subpatcher inlet the edit touched and confirm the assistance tooltip appears.

**Note:** the first edit-path save of each existing patch will also write inferred assistance comments for every inlet/outlet that had none. This is a one-time diff, for example 15 ports in ji-harmonizer.

## Threat surface

No new network, auth, file-access or schema surface was introduced.

## Known Stubs

None.

## Self-Check: PASSED

- tests/test_edit_keeps_user_work.py: FOUND
- commits 12b3c92, 9c724c9, 9c4885f: FOUND (3 `(Q6 ` commits since base-sha, each touching only plan files)
- stash list unchanged; `git status --porcelain -- patches/` shows only the pre-existing `.active-project.json`
- Python 3.10 syntax gate: PASSED on all changed .py files
