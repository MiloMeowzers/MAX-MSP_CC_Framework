---
phase: quick-261016-d3y
verified: 2026-10-16T18:44:48Z
status: human_needed
score: 7/7 must-haves verified
covered_files:
  - .planning/quick/261016-d3y-implement-q29-in-planning-reviews-2026-1/261016-d3y-PLAN.md
  - .planning/quick/261016-d3y-implement-q29-in-planning-reviews-2026-1/261016-d3y-SUMMARY.md
  - CLAUDE.md
  - src/maxpat/__init__.py
  - src/maxpat/builders.py
  - src/maxpat/hooks.py
  - src/maxpat/maxjson.py
  - src/maxpat/patcher.py
  - tests/test_edit_fidelity.py
covered_digest: "v2:sha256:6e0309a0ea35768ce5c32c03174a72a95b85a3e2801718990b6c867c74f01748"
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Open a framework-saved new patch in MAX, re-save without edits, check git diff"
    expected: "Empty diff, or only MAX's own normalizations"
    why_human: "Needs MAX itself; the in-repo proof is MAX-layout parity on 1015/1018 bundle help patches plus the two MAX-saved reference files"
  - test: "Open a .gendsp that write_gendsp grew by one output, in MAX's gen editor"
    expected: "Codebox compiles and the new outlet appears"
    why_human: "gen compile happens only inside MAX"
  - test: "replace_box_safe a parameter-enabled dial or live.dial, then open in MAX"
    expected: "pattr / parameter binding (varname, valueof) still works"
    why_human: "Binding behavior is runtime MAX"
  - test: "Place a meter~ 5 px right of a gain~ and open in MAX"
    expected: "They render side by side"
    why_human: "Rendered widths are visual"
---

# Quick Task 261016-d3y (Q29) Verification Report

**Goal:** Q29 edit fidelity II: replace_box identity, gendsp round-trip, MAX-style JSON writer, add_box nudge-only-on-overlap with reporting. One test per finding B4, B8, B9, B10.
**Status:** human_needed. Everything automatable passed; only MAX-side checks remain.
**Re-verification:** No, initial verification.

## Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | B9 in-memory and tmp-copy no-op save is byte-identical for FDNVerb.maxhelp and sample-layers.maxpat; the reference files are never written | VERIFIED | My own probe (not the executor's tests): `read_patch` -> `save_patch_roundtrip` on tmp copies gives disk-identical True for both, in-memory `format_patch_text` equality True, and the sha256 of the originals is unchanged. `git diff --quiet 6438377f -- <both files>` is clean. |
| 2 | B9 corpus: all committed patches/** .maxpat/.maxhelp/.gendsp files have a byte-identical no-op save text | VERIFIED | Probe: 69 files, bad = []. `git diff HEAD -- patches` is clean. |
| 3 | B8: write_gendsp edits an existing .gendsp in place | VERIFIED | Probe on a gong-engine.gendsp copy. A no-op write is byte-identical with orphaned == []. Code using out3 adds an `out 3` box and one cord, the `v1.12.1` comment survives, and orphaned is empty. Code using only out1 removes `out 2` and returns the cord `obj-2:1 -> obj-4:0` in orphaned. The ValueError cases (two codeboxes, none) are covered by the passing TestB8GendspRoundTrip. |
| 4 | B4 identity: replace_box and replace_box_safe keep list index, presentation rect, varname, colours and parameter blocks | VERIFIED | `_carry_box_identity` is defined at patcher.py:1192 and called at 1188 from replace_box. TestB4ReplaceIdentity passes, including the dial -> live.dial and dial -> cycle~ negative cases. Red-first evidence is in red-t2 (15 failed). |
| 5 | B4 rewire: `pack 0 0` -> `pack 0 0 0` returns orphaned == []; a type gate keeps signal-into-control cords orphaned; plain replace_box still orphans every cord | VERIFIED | Probe: orphaned [] and 3 lines. `_rewire_type_gated` is at patcher.py:1392. TestB4Rewire passes. |
| 6 | B10: add_box keeps the requested position unless it truly overlaps; a move records nudged_from and warns BoxMovedWarning | VERIFIED | Probe: meter~ requested 5 px right of gain~ lands at [127.0, 100.0] with no BoxMovedWarning (warnings promoted to errors) and nudged_from None. A print on top of gain~ moves to (100, 250); nudged_from is (100.0, 100.0) and the warning names both box ids. |
| 7 | Docs, suite and scope | VERIFIED | The 10 DOCLINE lines match their named lines; numstat is exactly 1/1 per DOCLINE (CLAUDE.md 2/2, TECHNICAL.md 4/4, others 1/1). CLAUDE.md is 27406 bytes (<= 30000). Full suite, my own run: 5110 passed, 5 xfailed, 1 xpassed (baseline 5060 plus 50 new). Three `(Q29)` commits touch only files_modified paths, none under patches/. The stash list is unchanged and base-sha is 6438377f. The only existing-test edits are the 4 PD-7 tests and the 3 RULE_ANCHORS entries. Red evidence: red-t1 28 failed, red-t2 15 failed, red-t3 3 failed. |

**Score:** 7/7 truths verified, 0 behavior-unverified (every behavior-dependent truth has a passing test or probe).

## Required Artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| src/maxpat/maxjson.py | VERIFIED | Defines `dumps_max` and `has_expanded_arrays`; used by `format_patch_text`. |
| src/maxpat/hooks.py | VERIFIED | `format_patch_text` is wired into `save_patch_roundtrip` and `write_gendsp`; `read_patch` is used by the in-place gendsp path. |
| src/maxpat/patcher.py | VERIFIED | `BoxMovedWarning`, `_carry_box_identity`, `_rewire_type_gated` and `_nudge_off_overlap` are present and used. |
| src/maxpat/builders.py | VERIFIED | add_box calls `_nudge_off_overlap` (line 101) and sets `nudged_from`. |
| tests/test_edit_fidelity.py | VERIFIED | Six classes: TestB9TracerNoOpSave, TestB9MaxJsonWriter, TestB8GendspRoundTrip, TestB4ReplaceIdentity, TestB4Rewire, TestB10AddBoxPlacement. It passes together with test_change_tracking.py (100 passed). |
| `BoxMovedWarning` / `format_patch_text` exports | VERIFIED | Both import from `src.maxpat`. |

## Key Links

| From | To | Status |
|------|----|--------|
| save_patch_roundtrip -> format_patch_text -> dumps_max | WIRED (the disk-identical probe exercises the path) |
| write_gendsp -> read_patch / save_patch_roundtrip | WIRED (the gendsp probe) |
| replace_box_safe -> replace_box -> _carry_box_identity | WIRED |
| add_box -> _nudge_off_overlap | WIRED |

## Anti-Patterns

No TBD/FIXME/XXX/TODO/NotImplemented in the added lines of src or the new test file. Python 3.10 syntax check (`ast.parse(feature_version=(3, 10))`) passes on all six code files.

## Behavioral Spot-Checks

All run in my own process against tmp copies (scratchpad script). The working tree stayed clean afterwards (only untracked .planning files), and the reference files are unchanged against base 6438377f.

## Requirements Coverage

B4, B8, B9 and B10 each have a regression class. Tracked-tree changes are limited to the plan's 15 files. No orphaned requirements.

## Human Verification Required

1. **MAX no-op re-save.** Re-save a framework-saved new patch in MAX without edits. Expected: an empty `git diff`, or only MAX's own normalizations.
2. **gendsp grown by one output.** Open it in MAX's gen editor. Expected: the codebox compiles and the new outlet appears.
3. **Parameter binding after replace_box_safe.** Run it on a dial or live.dial. Expected: pattr / valueof binding still works.
4. **Companion layout.** A meter~ 5 px right of a gain~ renders side by side.

The SUMMARY also lists planner decisions PD-2 to PD-6 for the user to accept or reopen. They are decisions, not defects.

## Gaps Summary

None. All automated checks passed independently of the SUMMARY. Remaining items need MAX itself.

---

_Verified: 2026-10-16_
_Verifier: Claude (gsd-verifier)_
