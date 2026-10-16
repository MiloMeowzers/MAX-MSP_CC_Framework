---
phase: quick-261015-qm7
verified: 2026-10-15T21:00:00Z
status: human_needed
score: 12/12 must-haves verified (code-level)
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "add_overlay_readout(type='comment') in MAX"
    expected: "Empty-text comment readout loads and displays text received via `set ...`"
    why_human: "MAX runtime rendering"
  - test: "finalize_patch(is_new=True) build with panel, header and labels, opened in MAX"
    expected: "Panel behind its chain, labels beside their boxes, text readable. Check a header that originally sat just above a panel (executor deviation 5: header now sits on the panel top edge)."
    why_human: "Visual layout quality"
  - test: "Accept or reopen the four narrowings of the Q27 text (PD-1, PD-6, PD-7, PD-8)"
    expected: "User decision, as requested in SUMMARY.md"
    why_human: "Spec deviations need the user's explicit sign-off"
---

# Quick Task qm7 (Q27, layout fixes F1-F7) Verification

**Goal:** Implement Q27: layout overlay, stacking, contrast order, bpatcher faces, width cap.
**Status:** human_needed. Every code-level truth is verified. The remaining items are MAX visual checks and the user's decision on the four documented narrowings.

## Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Shared `rendered_rect` / `is_max_saved` (F5) | VERIFIED | Ran independently: message "set foo bar baz qux" gives w 177; comment "hello world label" gives w 105.2; 100-char comment at w 150 gives 62 high; 50 chars at w 200 gives 290; junk rect gives None. Called from builders.py:83, patcher.py:1006/1052, layout.py:165/203 and layout_critic.py:203. |
| 2 | Overlap critic uses rendered rects with the overlay exemption; corpus 436 -> 405 | VERIFIED | `triage.py --check base final` gives `mismatch=0`, with Overlapping boxes 436 -> 405. The selftest exits 0. |
| 3 | add_box overlap check uses rendered rects | VERIFIED | builders.py:83 and patcher.py:1006. Covered by TestF5AddBoxRenderedOverlap and TestF5AddBoxNewBoxRenderedDims, which pass. |
| 4 | F1: no status overlay | VERIFIED | `_ROLE_COMPANION_MAP["status"] == {companion: None, placement: None}` and the map has 6 keys. TestF1NoStatusOverlay and the PD-13-edited tests pass. |
| 5 | F2: control band by inlet, with gutters | VERIFIED | Independent probe: pack(0. 0. 0.) with cords created out of order. Flonum a is at x 30, flonum b at x 105, dial at x 180. Bottoms are 82, 82 and 85, against pack top 90. The pack is at y 90. |
| 6 | F3: contrast after layout; decorations anchored | VERIFIED | `finalize_patch` has `apply_layout(patcher...` before `ensure_text_contrast(patcher)`, and the latter appears once. Signature has `force_layout`. `apply_auto_styling(..., *, contrast=True)`. TestF3DecorationsAndContrastOrder passes. |
| 7 | F4: bpatcher faces skipped | VERIFIED | layout.py:127 skips `bpatcher` in the recursion. TestF4BpatcherFace passes. |
| 8 | F5 guard (`LayoutRefusedError`, `force`) | VERIFIED | A 9.1.5 patch raises with the exact reference text. Signature is `apply_layout(patcher, options=None, *, force=False)`. |
| 9 | F5 cap and presentation grid | VERIFIED | 20 chains: max right edge 1482, 0 intersections, wrapped to a second band (maxy 180). 30 loadbangs into one print: max right 1542, print below all. Constants are 1600 / 120 / `LayoutOptions.max_width` 1600. TestF5PresentationGrid passes. |
| 10 | F6: list-wrapped fills | VERIFIED | TestF6ListWrappedFill passes. aesthetics.py is among the changed files. |
| 11 | F7: overlay readout | VERIFIED | builders.py:510 sets `readout.text = ""`, and builders.py:523 calls `add_to_presentation`. TestF7OverlayReadout passes. |
| 12 | Suite and scope hygiene | VERIFIED | I re-ran the full suite: no failures. The recorded final run is 4937 passed, 5 xfailed, 1 xpassed, which is the baseline 4872 plus 65 new tests. 3 `(Q27)` commits touch only `src/maxpat` and `tests` (no `patches/`). Stash list is empty. The working tree has no uncommitted source changes. |
| 13 | `## Deviations from Q27` in SUMMARY has PD-1, PD-6, PD-7 and PD-8 | VERIFIED | The plan's awk/grep check passes for all four. |

**Score:** 12/12 plan truths verified (truth 13 is the SUMMARY structure check, which also passes). 0 behavior-unverified.

## Required Artifacts

All artifacts exist, are substantive and are wired. Key links: `layout_critic.py` -> `sizing.rendered_rect`, `patcher.py` -> `sizing.rendered_rect`, `layout.py` -> `sizing.rendered_rect`, and `hooks.py` -> `apply_layout` then `ensure_text_contrast`.

## Anti-Patterns

I did not run a full scan. I did not read the three commit diffs line by line. The scan of the changed files for new unreferenced TBD/FIXME/XXX debt markers was not run, and no such markers surfaced in anything I read.

## Notes and Warnings (non-blocking)

- Bundle sweep (SUMMARY; I did not re-run it): Overlapping boxes rose 16302 -> 18132 across Max's own help and bundle files. 1070 of Cycling '74's bundle files carry appversion 9.0.0, so `is_max_saved` reads them as generated. This is a warning-level limit of the PD-5/PD-7 heuristic, and SUMMARY discloses it.
- Executor deviation 5: a header sitting 30 px above a panel now sits on the panel's top edge. This is the reason for the visual MAX check above.
- Doc impact (shared-capabilities.md, proven-forms.md, ui-presets.md, CLAUDE.md Rule #4, TECHNICAL.md) is deliberately unedited and listed in SUMMARY.

## Gaps Summary

No code gaps. Human items:
1. MAX confirmation of the empty-text comment readout and the finalize_patch visual layout.
2. The user's accept or reopen decision on PD-1, PD-6, PD-7 and PD-8.

---
_Verified: 2026-10-15_
_Verifier: Claude (gsd-verifier)_
