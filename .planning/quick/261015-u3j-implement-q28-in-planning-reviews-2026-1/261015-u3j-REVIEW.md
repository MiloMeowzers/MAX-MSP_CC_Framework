---
phase: quick-261015-u3j
reviewed: 2026-10-15T00:00:00Z
depth: quick
files_reviewed: 8
files_reviewed_list:
  - CLAUDE.md
  - src/maxpat/aesthetics.py
  - src/maxpat/builders.py
  - src/maxpat/hooks.py
  - src/maxpat/patcher.py
  - tests/test_change_tracking.py
  - tests/test_claude_md.py
  - tests/test_round_trip.py
findings:
  critical: 2
  warning: 2
  info: 3
  total: 7
status: issues_found
fix_status: critical and warning findings fixed (0a2391e4, d618f39f, 8c040b0a); info open
---

# Phase quick-261015-u3j: Code Review Report

**Reviewed:** 2026-10-15
**Depth:** quick (pattern scan of the added lines, plus a targeted read of the 5fdc098e..d4b80ee9 diff for the focus areas)
**Files Reviewed:** 8
**Status:** issues_found

## Summary

The pattern scan of the added lines found nothing: no eval/exec, no secrets, no debug artifacts, no bare excepts.

The change-tracking part (Box/Patchline `_loaded` snapshot, `_apply_extra_attrs_diff`, the `from_dict` deep copy) holds up for the focus cases:
- **Aliasing:** `_raw` and `extra_attrs` share value objects, and the snapshot is a separate deep copy, so in-place edits are caught.
- **Direct `_raw` writes:** these still land while the field is unchanged.
- **Every `_raw`-bearing box has a snapshot:** `from_dict` is the only place that sets `_raw`, and it also sets `_loaded`.
- **Edit path styling:** auto-styling runs only on `is_new`, so loaded boxes are not repainted.

The port-sync part has two correctness defects:
1. `replace_box_safe` drops `parent_orphaned`.
2. Removing a non-rightmost port orphans the wrong parent cord. The test enshrines this.

## Critical Issues

### CR-01: replace_box_safe silently discards parent_orphaned on the auto-rewire path

**Status:** fixed (0a2391e4)
**File:** `src/maxpat/patcher.py:1157-1174`
**Issue:** `replace_box` now reports parent-patcher cords that the port resync removed, but only in `parent_orphaned`. `replace_box_safe(rewire="auto")` rewires `result.orphaned` and then returns a new `EditResult(box=result.box, orphaned=[])`, which throws `parent_orphaned` away.

The auto branch runs whenever the I/O counts match. Replacing an `outlet` (1 in / 0 out) with `print`, or with `s foo` (also 1 in / 0 out), takes that branch. The parent `p`/bpatcher cords from that outlet are then deleted from the parent patcher and reported nowhere. CLAUDE.md Rule #8 tells agents to prefer `replace_box_safe`, so this is the common path.
**Fix:**
```python
            return EditResult(
                box=result.box,
                orphaned=[],
                parent_orphaned=result.parent_orphaned,
            )
```
Add a test: replace an inner outlet with `print` via `replace_box_safe` and assert that `parent_orphaned` is non-empty.

### CR-02: Removing a non-rightmost port orphans the wrong parent cord and keeps the cord to the deleted port

**Status:** fixed (8c040b0a)
**File:** `src/maxpat/patcher.py:765-805` (`_sync_parent_ports_after_remove`); test `tests/test_change_tracking.py:440-448`
**Issue:** The function only drops parent cords whose index is now out of range (`>= numinlets` / `>= numoutlets`). Take inner inlets A(0), B(1), C(2) and remove A:
- The cord to inlet 0 (A, the port that was deleted) survives and now addresses B.
- The legitimate cord to inlet 2 (C) is the one orphaned.

`test_middle_removal_orphans_out_of_range_only_and_gate_refuses` asserts exactly this. It expects `obj-86 -> obj-85:0` (the cord to the removed inlet `obj-1`) to survive and `obj-69 -> obj-85:1` to be orphaned.

The function already has `rank`, so the correct remap is fully determined. Instead, `parent_orphaned` hands the caller the wrong cord, and the patcher holds a cord into a port that no longer exists. The save gate refuses the save, but a confirmed `force=True` (which CLAUDE.md allows) writes the misrouted wiring to disk. The outlet path has the same flaw, and there the `outlettype` entry *is* deleted at `rank`, so types and cords end up misaligned.
**Fix:** Orphan cords at exactly `rank` and shift the higher ones down:
```python
        for pl in outer.lines:
            if kind == "inlet" and pl.dest_id == parent.id and rank is not None:
                if pl.dest_inlet == rank:
                    orphaned.append(_orphan_dict(pl)); continue
                if pl.dest_inlet > rank:
                    pl.dest_inlet -= 1
            elif kind == "outlet" and pl.source_id == parent.id and rank is not None:
                if pl.source_outlet == rank:
                    orphaned.append(_orphan_dict(pl)); continue
                if pl.source_outlet > rank:
                    pl.source_outlet -= 1
            # keep the existing out-of-range sweep as a fallback (rank None)
            surviving.append(pl)
```
Update the test so the cord to the removed port is the one in `parent_orphaned`, and so the shifted cord survives on its new index. The gate's x-rank refusal can stay as a second line of defence.

## Warnings

### WR-01: remove_box puts parent-patcher cords in `orphaned`, unlike modify_box/replace_box

**Status:** fixed (d618f39f)
**File:** `src/maxpat/patcher.py:689-697`
**Issue:**
- **Mixed semantics:** `remove_box` returns the parent-patcher orphans in both `orphaned` and `parent_orphaned`. Everywhere else (`modify_box`, `replace_box`, and the `replace_box_safe` rewire loop), `orphaned` means cords of *this* patcher. A caller that applies the usual "iterate `result.orphaned` and `self.add_connection`" pattern (CLAUDE.md Rule #8) will look up parent-patcher ids in the inner patcher, and either `KeyError` or wire the wrong boxes.
- **Own cords missing:** the cords `remove_box` drops from its own patcher are not reported at all.
**Fix:** Return the cords removed from this patcher in `orphaned`. Keep the parent cords only in `parent_orphaned`, which is the same contract `replace_box` already documents.

### WR-02: Adding a port left of existing ports shifts outlettype but not the parent cords

**Status:** fixed (8c040b0a)
**File:** `src/maxpat/patcher.py:739-763` (`_sync_parent_ports_after_add`)
**Issue:** For an outlet, the function inserts `""` into `parent.outlettype` at the new port's x-rank. That renumbers the types the way MAX renumbers the ports. Parent cords from outlet `>= rank` are not shifted, so in memory each one now addresses the neighbouring port and reads the wrong type entry. Inlets have the same problem minus the type list.

Ports that already exist on disk get caught by the save gate. But on a new file, or for ports added earlier in the same session, no baseline rank exists, so nothing flags the misnumbering.
**Fix:** After growing the count, bump `dest_inlet` (inlet) or `source_outlet` (outlet) by 1 on parent cords at index `>= rank`. That mirrors the CR-02 remap.

## Info

### IN-01: The all-files round-trip guard globs the working tree, not committed files

**File:** `tests/test_round_trip.py:88-92, 386-388`
**Issue:** `PATCHES_DIR.rglob` runs at import time and picks up untracked or in-progress patches written by other instances (multi-instance work is a documented workflow). The suite result then depends on workspace state, which contradicts the "every committed patch file" comment. The `>= 69` guard is also a magic number.
**Fix:** Build the list from `git ls-files patches/`, falling back to rglob outside git. Or keep rglob and drop the "committed" wording.

### IN-02: Strong parent back-refs make copy.deepcopy of an inner Patcher/Box copy the whole parent graph

**File:** `src/maxpat/patcher.py:539-544`, `src/maxpat/builders.py:838-841`, `src/maxpat/patcher.py:1742-1743`
**Issue:** `deepcopy(box)` of a `p` box, or `deepcopy(inner)`, now follows `_parent_patcher` and copies the outer patcher too. The clone's inner then syncs against a phantom outer copy: parent cords get "orphaned" there, not in the real patcher. No call site in `src/` does this today. Ad-hoc agent or test code that clones a subpatcher section would hit it.
**Fix:** Add a `__deepcopy__` on Patcher that resets `_parent_box` / `_parent_patcher` to None unless they are already in the memo. Or document that cloned inner patchers must be re-parented.

### IN-03: Same-kind port replacement at a tied x can change rank without any sync

**File:** `src/maxpat/patcher.py:1067-1093`
**Issue:** `get_inlets()` / `get_outlets()` sort by x only, a stable sort over list order. `replace_box` appends the new port at the end of `boxes`. If another port shares the same x, the new port's rank can change while the `old_kind == new_kind` branch skips any resync. The new box also has a new id, so the gate's id-based rank comparison may not flag it.
**Fix:** In the same-kind branch, compare `old_rank` with `self._port_rank(new_box)` and fall through to the resync, or warn, when they differ. Alternatively, insert the new box at the old box's list index.

---

_Reviewed: 2026-10-15_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: quick_
