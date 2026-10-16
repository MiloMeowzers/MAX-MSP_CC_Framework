# Quick Task 261015-u3j: Implement Q28 in .planning/reviews/2026-10-11-fix-plan.md — change tracking for loaded patches - Context

**Gathered:** 2026-10-15
**Status:** Ready for planning

<domain>
## Task Boundary

Q28 of `.planning/reviews/2026-10-11-fix-plan.md` (findings B5, B6, B7, S4 in `.planning/reviews/2026-10-11-repo-review.md`):
- Change tracking: on loaded boxes and lines, every edited field reaches disk without manual `_raw` mutation (extra_attrs, fontsize/fontname, cord order/hidden/midpoints, colours). Then simplify the "mutate `box._raw`" paragraph in CLAUDE.md Rule #5.
- `from_dict` deep-copies its input (B6).
- Port sync: adding/removing inlet/outlet boxes inside a loaded subpatcher resyncs the parent's port counts (B7).
- All repo patch files still round-trip losslessly (keep that test).
- One test per finding, written red-first.

</domain>

<decisions>
## Implementation Decisions

### Tracking mechanism
- **Load snapshot + diff.** At `from_dict`, snapshot (deep copy) each tracked field: Box `fontname`, `fontsize`, `extra_attrs` (whole dict); Patchline `order`, `hidden`, `midpoints`, `color`, `extra_attrs`.
- At `to_dict`, write back any field whose current value differs from its snapshot; extra_attrs keys deleted since load are removed from the output; added keys are written.
- Unchanged fields come straight from `_raw`, so a no-op round-trip stays lossless (key order preserved; new keys append at the end).
- Must catch in-place mutation of lists/dicts (e.g. `box.extra_attrs["bgcolor"][3] = 0.5`) — hence deep-copied snapshot, not setters.

### Direct `_raw` writes
- Keep working: a direct `_raw[k]` write still reaches disk when the corresponding tracked field is unchanged since load. A changed tracked field wins over `_raw`.
- Retire the manual `_raw` sync copies in `modify_box` (patcher.py ~627-739), `set_assistance_comment` (~1234-1252) and `aesthetics.py:414` where tracking now covers them (keep any that cover non-tracked fields such as text/numinlets/patching_rect if still needed — `patching_rect`/`text`/num* are already overlaid in to_dict).
- Simplify the CLAUDE.md Rule #5 "On round-tripped (pre-existing) boxes, `extra_attrs` mutations are silently dropped" paragraph to reflect that edits now reach disk.

### Port removal in loaded subpatchers
- Adding/removing an inlet/outlet box in a subpatcher (loaded or new) resyncs the parent box's `numinlets`/`numoutlets`/`outlettype` (via a `sync_port_counts()`-style helper invoked from add/remove of inlet/outlet boxes; the inner patcher needs a back-reference to its parent box/patcher).
- Parent cords whose port index is now out of range are removed and returned as orphans (like `replace_box`'s `EditResult.orphaned`); the save gate's removed-cord warning still fires.
- Port index is by x-rank of inlet/outlet boxes (MAX convention; see memory "Subpatcher port x-order").

### Claude's Discretion
- Exact helper names and where the snapshot lives (`_loaded` dict attr on Box/Patchline).
- Whether `from_dict` deep-copies once at the top level or per box/line (must not share any nested object with the caller's dict).

</decisions>

<specifics>
## Specific Ideas

Repro cases from the review (B5/B6/B7):
- bgcolor set via `set_object_bgcolor` never reaches disk; fontsize 20 saves as 12; assistance comment in memory but `None` on disk; cord order/hidden edits dropped.
- `modify_box(position=…)` changed the input dict's rect (shared nested list).
- bassoon `p articulation` went to 3 inner inlets, parent still 2, `add_connection` to inlet 2 raises.

</specifics>

<canonical_refs>
## Canonical References

- `.planning/reviews/2026-10-11-fix-plan.md` §Q28 and "Rules for every task" (copy into PLAN.md)
- `.planning/reviews/2026-10-11-repo-review.md` rows B5, B6, B7, S4
- `CLAUDE.md` Rule #5, Rule #7 (save gate), Rule #8

</canonical_refs>

<post_review_decisions>
## Post-review decisions (2026-10-15, after REVIEW.md)

User decisions on REVIEW.md findings (these SUPERSEDE the "out-of-range cords only" port-removal rule above):
- **CR-01:** fix — `replace_box_safe` passes `parent_orphaned` through on its auto-rewire path.
- **WR-01:** fix — `remove_box` returns its own patcher's removed cords in `orphaned` and the parent's cords in `parent_orphaned` (never parent cords in `orphaned`).
- **CR-02 / PD-5:** renumber like MAX — removing an inlet/outlet box at x-rank k orphans the parent cords on port k (returned in `parent_orphaned`) and shifts parent cords on ports > k down by one.
- **WR-02:** shift up — adding an inlet/outlet box at x-rank k shifts parent cords on ports >= k up by one. Grow-only count behaviour stays for embedded bpatchers.
- The save gate is NOT changed in this task.
</post_review_decisions>
