# Quick Task 261015-j0n: Implement Q24 in .planning/reviews/2026-10-11-fix-plan.md — uninitialized UI→DSP state check - Context

**Gathered:** 2026-10-15
**Status:** Ready for planning

<domain>
## Task Boundary

Implement Q24 (§4.4 R8) from `.planning/reviews/2026-10-11-fix-plan.md`: new check `_check_uninitialized_state` — a UI control whose output reaches DSP params or `*~`/gain~ must have one of: `parameter_enable` with an initial value; a loadmess/loadbang path; a pattr/pattrstorage restore; a slaved gain~ input. Warning on edits, blocker on new patches. Latent cases reported as warnings: FDNVerb.maxhelp obj-29, disintegrate-helper obj-10, granularsynthtest obj-26, spectraldetector obj-8 (all four are top-level plain `gain~` with `parameter_enable: 0`).

</domain>

<decisions>
## Implementation Decisions

### Which UI classes count (state-holding controls)
- "Value holders": gain~, live.gain~, slider, dial, number, flonum, live.dial, live.slider, live.numbox, toggle, live.toggle, umenu, live.menu, tab, live.tab, radiogroup.
- Excluded: button, kslider, multislider, textedit, nodes, matrixctrl (and any other UI class not listed).

### pattr-managed controls
- Per-control binding, not whole-patch exemption. A control counts as initialized if:
  - it is bound to a `pattr` (cord into/out of a pattr bound to it, or `pattr @bindto <varname>`), or
  - it has a `varname` in a patcher containing `autopattr` AND a `pattrstorage` exists somewhere in the patch tree.
- Unbound controls in the same patch are still checked.

### "Reaches DSP" tracing
- Full control graph: follow control cords through any objects, subpatcher inlet/outlet ports, and named send/receive (s/r, send/receive, value/v/pv as applicable), until reaching a gen~/mc.gen~/rnbo~/poly~ inlet, `*~`/`mc.*~`, gain~, or any object with signal I/O.
- Bounded depth and cycle-safe (visited set).

### Claude's Discretion
- Exact module placement (structure_critic vs validation) and how "new patch vs edit" severity is plumbed — follow existing conventions (e.g. how other Q-tasks distinguished is_new / finalize_patch(is_new=True) and the severity contract).
- What counts as a "loadmess/loadbang path" (e.g. loadbang/loadmess → … → control, or loadmess/loadbang → message → control's inlet, including through `t`, and `;name msg` sends to a receive feeding the control) and "slaved gain~ input" (another gain~'s outlet cord into this gain~'s left inlet — see memory feedback_gain_linked_stereo).
- What qualifies as "parameter_enable with an initial value" (parameter_enable 1 plus parameter_initial_enable 1 / parameter_initial in saved_attribute_attributes.valueof, or live.* defaults — verify against existing committed patches and proven forms).

</decisions>

<specifics>
## Specific Ideas

- Latent cases must surface as warnings (committed patches are never edited — rule 3 of the fix plan); if any other committed patch produces a new finding, either fix the checker (false positive) or allowlist with a reason and list it in SUMMARY.md.
- Regression tests first (red→green), one per initialization route plus the uninitialized case and the new-vs-edit severity split.
- Calibration test must stay green; full suite green.

</specifics>

<canonical_refs>
## Canonical References

- `.planning/reviews/2026-10-11-fix-plan.md` — "Rules for every task" + Q24 section
- `.planning/reviews/2026-10-11-repo-review.md` — §4.4 R8 and the "Load-time init" row (line ~254) with commit evidence (44afda9, 23d6f01, 9ea409f, 447ac9a, 0e019d0, 2b48909, 0d0f1cf, 49747a0, da8fc2b)
- `.claude/skills/references/severity-contract.md` — warning vs blocker semantics, save gate

</canonical_refs>
