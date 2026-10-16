---
phase: quick-261015-u3j
plan: 01
subsystem: src/maxpat round-trip serialization
tags: [Q28, B5, B6, B7, S4, change-tracking, round-trip, port-sync]
status: complete
requires: []
provides:
  - load snapshot + diff serialization for loaded Box and Patchline
  - deep-copying Patcher.from_dict (private _from_owned_dict recursion)
  - parent port sync for inlet/outlet boxes inside p/patcher subpatchers and bpatchers
  - remove_box returns EditResult; EditResult.parent_orphaned
affects: [src/maxpat/patcher.py, src/maxpat/builders.py, src/maxpat/aesthetics.py, src/maxpat/hooks.py, CLAUDE.md]
tech-stack:
  added: []
  patterns: ["deep-copied load snapshot (_loaded) diffed before structural overlays in to_dict"]
key-files:
  created: [tests/test_change_tracking.py]
  modified: [src/maxpat/patcher.py, src/maxpat/builders.py, src/maxpat/aesthetics.py, src/maxpat/hooks.py, CLAUDE.md, tests/test_round_trip.py, tests/test_claude_md.py]
decisions:
  - "PD-3: modify_box(extra_attrs=) still writes _BOX_HANDLED_KEYS keys into _raw and syncs fontname/fontsize onto box fields"
  - "PD-4: port add is grow-only; remove_box returns EditResult; new EditResult.parent_orphaned; replace_box reports parent cords only in parent_orphaned"
  - "PD-5: middle-port removal orphans only out-of-range cords; the save gate refuses the x-rank change"
metrics:
  completed: 2026-10-15
  tasks: 3
estimate:
  tokens: 125000
actuals:
  tokens: 13950
  tasks: 3
  commits: 3
plan_head_before: 5fdc098e00f844603c9800dc943f72c065deae56
plan_head_after: d4b80ee9e57c07a0be41b7ed9c2b1d5d324df990
---

# Quick 261015-u3j: Q28 edit fidelity I (change tracking) Summary

Edits to loaded patches now reach disk. Each loaded box and cord gets a deep-copied load snapshot, and `to_dict` writes back every field that differs from it. `from_dict` deep-copies its input. Adding or removing an inlet/outlet inside a subpatcher resyncs the parent box's ports and returns any parent cords it had to drop.

## Commits

| Task | Commit | Message |
|------|--------|---------|
| 1 | 68d15902 | fix(patcher): change tracking for loaded boxes and cords; from_dict deep-copies its input (Q28) |
| 2 | 9b3c4abc | fix(patcher): adding or removing a subpatcher inlet/outlet resyncs the parent's ports (Q28) |
| 3 | d4b80ee9 | docs(claude-md): Rule #5 -- edits to loaded patches reach disk (Q28) |

## Suite evidence

| Run | Last line |
|-----|-----------|
| baseline-pytest.txt | 4937 passed, 5 xfailed, 1 xpassed, 29 warnings in 87.06s |
| pytest-t1.txt | 5038 passed, 5 xfailed, 1 xpassed, 30 warnings in 92.44s |
| pytest-t2.txt | 5049 passed, 5 xfailed, 1 xpassed, 30 warnings in 102.48s |
| final-pytest.txt | 5049 passed, 5 xfailed, 1 xpassed, 30 warnings in 98.06s |

Final = baseline + 112 new tests: 42 in test_change_tracking.py, plus 69 parametrized all-files round-trip cases and 1 file-count guard. The one extra warning is the expected "not inside a git repository -- not auto-committed" from the tracer's tmp_path save.

**Red evidence:**
- red-t1.txt: 21 failed, 10 passed. The 10 that passed are the green guards the plan names: modify_box(color), modify_box extra_attrs on disk, midpoints rebound/None, color None, in-place bgcolor, direct raw writes x3, structural raw key.
- red-t2.txt: 9 failed, 2 passed. The two passes were grow-only bpatcher and removing an added outlet, which already pass at HEAD.
- red-t3.txt: 1 failed (`test_rule_anchor_present` for the new anchor).

**Existing-test edits:** only two.
- The added `test_round_trip_identity_all_repo_files` method in tests/test_round_trip.py, plus its `_ALL_REPO_PATCH_FILES` list and a `test_repo_file_list_is_complete` count guard (>= 69).
- The single RULE_ANCHORS entry in tests/test_claude_md.py.

No other existing test changed, and all of them pass.

## What changed

- **B5 / S4 (patcher.py):**
  - Module constants `_BOX_HANDLED_KEYS` and `_LINE_HANDLED_KEYS`, and a shared helper `_apply_extra_attrs_diff`.
  - `Box._loaded` (fontname, fontsize, deep-copied extra_attrs) is set in from_dict.
  - `Patchline._loaded` is set in `__init__` whenever `_raw` is given.
  - `Box.to_dict` applies the diff before the structural overlays.
  - `Patchline.to_dict` uses change-gated rules for order, hidden, midpoints and color. Lines with no snapshot keep the old code path.
- **B6:** the public `from_dict` is now `_from_owned_dict(copy.deepcopy(data))`. Nested patchers recurse through `_from_owned_dict`, so they are copied once.
- **S4 retired copies:**
  - modify_box(color=) and modify_box(extra_attrs=) for non-structural keys;
  - `_set_assistance_comment`;
  - `aesthetics._set_textcolor`.

  Docstrings are updated, including hooks.finalize_patch. The modify_box args/position `_raw` syncs are kept.
- **B7 (patcher.py, builders.py):**
  - New `_parent_box` / `_parent_patcher` / `_port_sync_suspended` attributes.
  - New `_port_rank`, `_port_sync_parent`, `_sync_parent_ports_after_add` and `_sync_parent_ports_after_remove`.
  - add_box calls the add sync.
  - add_subpatcher and the embedded add_bpatcher set the back-refs after their inner ports exist.
  - remove_box returns an `EditResult`.
  - replace_box suspends the sync around its remove + add, then applies the net rule.
- **CLAUDE.md:** the line-108 Rule #5 paragraph is replaced with the exact reference_data text. The file is now 26916 bytes, under the 30000 limit.

## Deviations from Plan

None. The plan was executed as written. One small addition: `_port_sync_parent` also requires `parent._inner_patcher is self`. This guards against a stale back-ref after an inner patcher is reassigned, and it does not change any planned behaviour.

## Decisions to confirm

- **PD-3:** modify_box(extra_attrs=) still writes structural keys (those in `_BOX_HANDLED_KEYS`, e.g. fontsize, presentation) into `box._raw`. It also now syncs `fontname` / `fontsize` onto the box fields, so the font diff writes them. Every other key reaches disk only through change tracking.
- **PD-4:**
  - Adding a port is grow-only, because embedded bpatchers declare their counts before their inner ports exist.
  - remove_box now returns an `EditResult` instead of None.
  - There is a new `EditResult.parent_orphaned` field.
  - replace_box reports parent cords only in `parent_orphaned`, and `orphaned` stays this patcher's cords, because replace_box_safe rewires those by id.
- **PD-5: RESOLVED by the user (2026-10-15): renumber like MAX** (option B). Implemented in 8c040b0a (see "Review fixes"). Removing the port at x-rank k orphans the parent cords on port k and shifts the cords above it down by one; adding a port that grows the count shifts cords at or above its rank up by one. The save gate is unchanged.

Accept or reopen each:
- PD-3: (A) accept / (B) stop writing structural keys to `_raw` too
- PD-4: (A) accept / (B) exact resync on add, with orphan return from add_box / (C) put replace_box parent cords in `orphaned` as well
- PD-5: resolved (B, renumber like MAX)

## Behavior change

`set_object_bgcolor` and `apply_auto_styling` (the dac~/loadbang highlights) now persist on a **loaded** patch. Before, they were silently dropped. `finalize_patch(is_new=False)` calls neither, so the default edit flow is unchanged. Calling them by hand on a loaded patch will now change the file.

## Follow-ups (PD-8, out of scope)

- validation.py:609 still reads `box._raw` before `extra_attrs` for the mc.gen~ `data` key, so an edited `data` via extra_attrs is not seen by that check.
- `to_dict` output still aliases model lists.
- ~~MAX-style port renumbering on middle-port removal (PD-5 option B).~~ Done in 8c040b0a.
- All Q29 items (replace_box identity, gendsp round-trip, MAX-style JSON writer, add_box nudge) and Q36.

## Doc impact (not edited, rule 8)

- CLAUDE.md:238: `box.extra_attrs["args"]` now also works for the bpatcher numeric-arg fix. The `_raw` advice there is still valid.
- The CLAUDE.md "Subpatcher Inlet/Outlet Access" section could mention the parent port sync.
- shared-capabilities.md:239: remove_box now returns an EditResult and runs the port sync.
- TECHNICAL.md:342.
- Stale test docstrings at test_edit_keeps_user_work.py:13 and test_aesthetics.py:958. Both describe the old `_raw` rule; the tests themselves still pass.

## MAX confirmation (rule 9)

- In a loaded `p` subpatcher, add an inlet and an outlet through the API and save. Reopen in MAX: the new ports should appear on the parent box, and a cord to/from them should work. The new outlet gets `""` in outlettype, and MAX recomputes it on load (assumption A1).
- Make a bgcolor, fontsize and cord `hidden` edit on a loaded patch, save, and reopen in MAX. Each should render as expected.

## Python 3.10

Python 3.10 cannot be run locally (only 3.14 is installed). Compatibility was checked with `ast.parse(feature_version=(3, 10))` on every changed .py file. The new annotations rely on `from __future__ import annotations`, which patcher.py already has.

## Threat surface

No new network, auth or file surfaces. The new trust-boundary behaviour is that port edits inside a subpatcher now mutate the parent box and parent cords (threat T-u3j-02). The mitigations are: add is grow-only, remove returns every parent cord it drops, the save gate's warning still fires, and tests cover these cases.

## Self-Check: PASSED

- FOUND: tests/test_change_tracking.py; src/maxpat/patcher.py contains `def _from_owned_dict`, `_BOX_HANDLED_KEYS`, `_LINE_HANDLED_KEYS`, `def _sync_parent_ports_after_remove` and `parent_orphaned`. builders.py contains `_sync_parent_ports_after_add(` and `_parent_box`.
- FOUND commits: 68d15902, 9b3c4abc, d4b80ee9. Q/q28-commit-files.txt lists only files_modified paths and nothing under patches/.
- The stash list is unchanged, and `git status --porcelain` was unchanged by the final suite run.

## Review fixes

Fixes for 261015-u3j-REVIEW.md (CR-01, CR-02, WR-01, WR-02). IN-01..IN-03 were out of scope and not touched. Each fix had its regression test written red first in tests/test_change_tracking.py.

| Finding | Commit | Change |
|---------|--------|--------|
| CR-01 | 0a2391e4 | `replace_box_safe` passes `parent_orphaned` through on the auto-rewire path. Test: loaded outlet (2 in / 0 out) replaced by `dac~` via `replace_box_safe`. |
| WR-01 | d618f39f | `remove_box` returns the cords it removed from its own patcher in `orphaned`; parent cords only in `parent_orphaned`. EditResult docstring updated. Two tests updated (`test_remove_added_inlet_returns_parent_cord`, `test_remove_non_port_box_returns_empty_edit_result` -> `..._returns_own_cords`), one added. No src caller used the old shape. |
| CR-02 + WR-02 | 8c040b0a | Shared renumber in `_sync_parent_ports_after_remove` / `_sync_parent_ports_after_add` (new `_orphan_dict` helper). Remove at rank k: orphan parent cords on k, shift > k down, delete `outlettype[k]`, then the exact-count out-of-range sweep. Add at rank k: only when the add grows the parent count, insert `""` at k in outlettype and shift cords >= k up. |

CR-02 / WR-02 details:
- `test_middle_removal_orphans_out_of_range_only_and_gate_refuses` is replaced by `test_middle_removal_renumbers_like_max`. The cord to the removed inlet is the orphan, and the other cord moves 1 -> 0. The gate still reports `port_changes` (the surviving inlet's x-rank went 1 -> 0), so an unforced save of an existing file is still refused. This is the current gate behaviour, which was deliberately left unchanged.
- **Embedded bpatchers:** when the parent already declares at least as many ports as the inner patcher now has, an added port fills a declared port. The counts and cords are unchanged. Only an add that grows the count past the declared one is an insert and shifts cords (`test_embedded_bpatcher_declared_ports_not_shifted`).
- Same-kind port replacement (`replace_box` port -> port at the same x) still runs under the sync suspension, and no cords move (`test_replace_left_port_with_port_does_not_shift`, covering inlet and outlet).
- New tests also cover outlet types/cords alignment, middle-of-three removal, the replace_box different-kind path using the old rank, a middle insert, and add-then-remove being a no-op on the parent.

Suite: baseline at d4b80ee9 was 5049 passed, 5 xfailed, 1 xpassed. Final is **5060 passed, 5 xfailed, 1 xpassed, 30 warnings** (11 new tests net). Verification ran in the main checkout, with no worktree (`workflow.use_worktrees` was not used, per the orchestrator instruction). All repo patch files still round-trip (tests/test_round_trip.py is green). Python 3.10 syntax was checked with `ast.parse(feature_version=(3, 10))`.

MAX confirmation still to do: in a loaded `p` with 2 inlets, both cabled, delete the left inlet through the API, save with `force=True`, and reopen. The remaining cord should land on the single inlet.
