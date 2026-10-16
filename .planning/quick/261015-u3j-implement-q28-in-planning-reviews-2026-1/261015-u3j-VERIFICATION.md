---
phase: quick-261015-u3j
verified: 2026-10-15T00:00:00Z
status: human_needed
score: 9/9 must-haves verified
covered_files:
  - CLAUDE.md
  - src/maxpat/aesthetics.py
  - src/maxpat/builders.py
  - src/maxpat/hooks.py
  - src/maxpat/patcher.py
  - tests/test_change_tracking.py
  - tests/test_claude_md.py
  - tests/test_round_trip.py
covered_digest: "v2:sha256:f2a6d10ca7854e4035c1132f864bbcca09aaa37fa7b54783f4e39479964aa9d6"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: human_needed
  previous_score: 9/9
  gaps_closed:
    - "CR-01: replace_box_safe dropped parent_orphaned on auto-rewire"
    - "WR-01: remove_box put parent cords in orphaned"
    - "CR-02: middle-port removal orphaned the wrong parent cord"
    - "WR-02: left port add did not shift parent cords"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "In MAX, open a patch saved after adding an inlet and an outlet inside a loaded `p` subpatcher via the API (e.g. bassoon `p articulation`), and cord to/from the new ports."
    expected: "The parent box shows 3 inlets / 3 outlets and the cords work. The new outlet is saved with outlettype \"\"; MAX is assumed to recompute it on load."
    why_human: "Real MAX load behaviour of the synthesized port counts and outlettype cannot be checked from Python."
  - test: "In a loaded `p` with 2 inlets, both cabled, delete the left inlet through the API, save with force=True, reopen in MAX."
    expected: "The remaining cord lands on the single inlet, and the cord to the deleted inlet is gone."
    why_human: "Confirms the renumbering matches what MAX does on load (x-rank). Python cannot observe MAX."
  - test: "Save a loaded patch after a bgcolor, fontsize and cord `hidden` edit, then reopen it in MAX."
    expected: "Each edit renders as expected."
    why_human: "Visual rendering in MAX."
---

# Quick 261015-u3j (Q28): change tracking for loaded patches, re-verification report

**Goal:** Q28 (B5, B6, B7, S4). Edits to loaded boxes and cords reach disk. `from_dict` deep-copies its input. Port edits inside a subpatcher resync the parent. All 69 patch files still round-trip. CLAUDE.md Rule #5 is simplified.
**Status:** human_needed. Every automated check passed, including the four review fixes. Only the MAX confirmations remain.
**Re-verification:** Yes, after review fixes (0a2391e4, d618f39f, 8c040b0a). The must-haves are adjusted for the post-review decisions in CONTEXT.md: renumber like MAX on removal and on add, `orphaned` holds only this patcher's cords, and the save gate is unchanged.

## Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | B5 boxes: bgcolor, fontsize and fontname, extra_attrs and in-place edits reach `to_dict` | VERIFIED | No regression. The change-tracking tests pass in the full run, and `patcher.py` still has the `_loaded` snapshot diff (checked in the prior pass; commits since touch only the port sync code). |
| 2 | B5 cords: order, hidden, midpoints and extra_attrs reach `to_dict`; reverting removes the key | VERIFIED | No regression (same tests green). |
| 3 | S4 semantics (deep-copy snapshot, deleted/added keys, unchanged representation, raw write wins when unchanged) | VERIFIED | Own probe: 69 repo files give `from_dict -> to_dict` equal to the original by dict equality AND `json.dumps` identity, and the input is unchanged (69 files, 0 bad). |
| 4 | B6: `from_dict` shares nothing with the caller's dict | VERIFIED | Same 69-file probe leaves the input equal to its pristine deepcopy. TestB6 passes. |
| 5 | Round-trip guard over all repo patch files | VERIFIED | 69 files, 0 bad. The guard test is in the suite and passes. |
| 6 | B7: adding or removing a port box resyncs the parent; replace_box of a port with a same-kind port leaves the parent unchanged | VERIFIED | Own probe on bassoon `p articulation` (obj-85). Right-side inlet and outlet add: counts 3/3, `add_connection(obj-86, 0, art, 2)` succeeds, `to_dict` shows numinlets 3. Removing the right inlet obj-2: numinlets 2, `parent_orphaned` is exactly obj-69:0 -> obj-85:1. `replace_box_safe(obj-1, "inlet")` leaves `parent_orphaned == []`, numinlets 2 and all 4 parent cords unchanged. Top-level and non-port removal give empty `parent_orphaned`. |
| 7 | Middle-port removal (post-review: renumber like MAX); the save gate still reports the x-rank change | VERIFIED | See the four review-fix probes below. `hooks._gate_report` after removing obj-1 reports `['p articulation (obj-85): inlet obj-2 rank 1 -> 0']`, so an unforced save of the existing file is still refused. The gate was not changed. |
| 8 | Retired raw-dict copies; args/position raw syncs kept | VERIFIED | No change since the prior pass. TestRawCopiesRetired passes. |
| 9 | CLAUDE.md Rule #5, anchor, size, scope and suite | VERIFIED | The anchor appears once in CLAUDE.md, size 26916 bytes (under 30000). The review commits touch only `patcher.py`, `builders.py` (2 lines) and `tests/test_change_tracking.py`. No diff under `patches/` since 5fdc098e. `git stash list` is empty. No tracked file is modified in the working tree. Full suite, run once: **5060 passed, 5 xfailed, 1 xpassed** (baseline 4937, plus 112 from the first pass, plus 11 from the review fixes). |

**Score:** 9/9 truths verified, 0 behavior-unverified.

## Review-fix probes (independent, in memory, bassoon obj-85)

Parent cords before: obj-86:0 -> 85:0, obj-69:0 -> 85:1, 85:0 -> obj-4:0, 85:1 -> obj-73:1. Inner inlets obj-1 (x=30, rank 0) and obj-2 (x=480, rank 1); inner outlets obj-3 (rank 0) and obj-4 (rank 1).

| Finding | Probe | Result | Status |
|---------|-------|--------|--------|
| CR-01 | Replace inner outlet obj-4 with `print` via `replace_box_safe` (auto-rewire path; I/O counts match) | `orphaned` is this patcher's cord (obj-11 -> obj-4) only. `parent_orphaned` is `85:1 -> obj-73:1`, not dropped. The parent cord is gone and `numoutlets` is 1. `replace_box` returns the same `parent_orphaned`. | VERIFIED |
| WR-01 | Remove inner inlet obj-2, and remove a non-port inner box | `orphaned` is the inner cord obj-2 -> obj-10, every id inner-only. `parent_orphaned` is obj-69 -> 85:1. A non-port removal gives its own cords in `orphaned` and `parent_orphaned == []`. | VERIFIED |
| CR-02 (inlet) | Remove the leftmost inlet obj-1 | numinlets 1. `parent_orphaned` is `obj-86 -> 85:0` (the cord to the removed port). The obj-69 cord moves 1 -> 0. `to_dict` agrees (numinlets 1, cord on 0). | VERIFIED |
| CR-02 (outlet) | Set outlettype `['signal','float']`, remove the leftmost outlet obj-3 | outlettype becomes `['float']` in memory and in `to_dict`. `parent_orphaned` is `85:0 -> obj-4:0`. The `85:1 -> obj-73` cord moves to 0. Types and cords stay aligned. | VERIFIED |
| CR-02 (3 ports) | Add a middle inlet, then remove the first; also add-then-remove the same inlet | Remove-first of 3: numin 2, orphans the port-0 cord, cords renumbered. Add-then-remove restores the original 2 inlets and all 4 cords exactly, with no orphans. | VERIFIED |
| WR-02 (inlet) | Add an inlet at x=10 (left of both) | rank 0, numin 3. Cords to inlets 0/1 move to 1/2, in memory and in `to_dict`. | VERIFIED |
| WR-02 (outlet) | Add an outlet at x=10 | numout 3, outlettype `['','signal','float']` (`""` inserted at rank 0). Outlet cords 0/1 move to 1/2. | VERIFIED |
| WR-02 (middle add) | Add an inlet at x=250 | rank 1. The cord on inlet 1 moves to 2, the cord on 0 stays. | VERIFIED |
| WR-02 (embedded bpatcher) | `add_bpatcher(embedded=True, numinlets=2, ...)` with 2 cabled inlets; add two inner inlets | Parent counts stay 2 and cords stay on 0/1. A third inner inlet at x=0 grows the count to 3 and shifts the cords to 1/2. The declared ports are filled, not shifted. | VERIFIED |
| WR-02 (API subpatcher) | `add_subpatcher(inlets=2)`, cord both, add an inlet at x=-50 | numin 3, cords 0/1 shift to 1/2, `to_dict` agrees. | VERIFIED |

## Required Artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| `src/maxpat/patcher.py` | VERIFIED | `_from_owned_dict`, `_loaded`, `EditResult.parent_orphaned`, `_port_rank`, `_orphan_dict` and both `_sync_parent_ports_after_*` methods are present and exercised by the probes. |
| `src/maxpat/builders.py` | VERIFIED | `add_box` calls the add sync, and the back-refs are set after the inner ports exist. |
| `src/maxpat/aesthetics.py` | VERIFIED | Unchanged since the prior pass. |
| `tests/test_change_tracking.py` | VERIFIED | The renumber, embedded-declared, same-kind-replace and add-then-remove tests are present and pass. |
| `tests/test_round_trip.py` | VERIFIED | The all-files guard passes. |
| `CLAUDE.md` | VERIFIED | Rule #5 anchor present once. |

## Key Links

| From | To | Status |
|------|----|--------|
| `from_dict` snapshot | `Box.to_dict` / `Patchline.to_dict` diff | WIRED |
| `builders.add_box` | `_sync_parent_ports_after_add` | WIRED (probe grows and shifts the parent) |
| `remove_box` | `_sync_parent_ports_after_remove` | WIRED (probe orphans and renumbers) |
| `replace_box` / `replace_box_safe` | `parent_orphaned` | WIRED (CR-01 probe) |
| `RULE_ANCHORS` | CLAUDE.md Rule #5 | WIRED |

## Anti-Patterns

No unreferenced TBD, FIXME or XXX markers in the review-fix diffs. No change under `patches/`.

## Open items (non-blocking)

- **IN-01 to IN-03** from REVIEW.md are open by decision (out of scope). Of these, IN-03 can matter in one edge case: a same-kind port replacement at a tied x can change rank without a parent resync. It was not probed here and is not part of a must-have.
- **Gate vs renumber:** an unforced save of an existing file after removing a non-rightmost port is still refused, because the gate reports the surviving port's x-rank change. This is intended, because the gate was deliberately not changed in this task. A `force=True` save writes the renumbered cords, which the probes show are consistent.
- PD-3 and PD-4 remain for the user to accept or reopen (see SUMMARY.md). PD-5 was resolved by the user.
- Behavior change: `set_object_bgcolor` and `apply_auto_styling` now persist on loaded patches.
- Python 3.10 compatibility was checked only by `ast.parse(feature_version=(3, 10))`.

## Human Verification Required

1. **New ports in MAX.** Add an inlet and an outlet to a loaded `p` subpatcher through the API and save. Reopen in MAX and cord to the new ports. Expected: the parent shows the new ports and the cords work. Why human: MAX load behaviour, including the assumed outlettype recomputation (A1).
2. **Renumbered cords in MAX.** In a loaded `p` with 2 inlets, both cabled, delete the left inlet through the API, save with `force=True`, reopen. Expected: the remaining cord lands on the single inlet. Why human: confirms the in-memory renumbering equals MAX's x-rank behaviour on load.
3. **Edit rendering.** Make a bgcolor, fontsize and cord `hidden` edit on a loaded patch, save, and reopen in MAX. Expected: each edit renders as expected. Why human: visual rendering.

## Gaps Summary

None. CR-01, WR-01, CR-02 and WR-02 are each fixed and independently confirmed. The post-review contract holds: `orphaned` is this patcher's cords only, `parent_orphaned` is the parent's, and ports renumber like MAX on add and on remove, with embedded bpatchers' declared ports not shifted. The full suite is green at 5060 passed.

---

_Verified: 2026-10-15_
_Verifier: Claude (gsd-verifier)_
