---
phase: quick-261013-q58
verified: 2026-10-13T00:00:00Z
status: human_needed
score: 7/7 must-haves verified
covered_files:
  - .planning/quick/261013-q58-implement-q13-in-planning-reviews-2026-1/261013-q58-PLAN.md
  - .planning/quick/261013-q58-implement-q13-in-planning-reviews-2026-1/261013-q58-SUMMARY.md
  - src/maxpat/builders.py
  - src/maxpat/maxclass_map.py
  - src/maxpat/patcher.py
  - src/maxpat/sizing.py
  - src/maxpat/validation.py
  - tests/test_analysis.py
  - tests/test_maxclass_map.py
  - tests/test_sizing.py
  - tests/test_sync_max_bundle.py
  - tools/sync_max_bundle.py
covered_digest: "v2:sha256:fc4f3f8cbf43e7aa34c5ab432b03f8ed3d871ed72367a55cac738d163ea5b58b"
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Open .planning/quick/261013-q58-implement-q13-in-planning-reviews-2026-1/confirm-live-thisdevice.maxpat in MAX 9.2"
    expected: "live.thisdevice and print thisdevice create as object boxes (alongside midiin -> midiout). No 'No such object' or maxclass error in the Max window."
    why_human: "Whether MAX loads the generated box can only be observed in MAX. This is the fix-plan's required user confirmation."
  - test: "Optional: open confirm-ui-maxclasses.maxpat in the same directory"
    expected: "Each of the 16 buildable added widgets appears as its widget, with no maxclass or parameter_enable error."
    why_human: "Widget rendering in MAX is not observable from the repo."
---

# Quick Task q58 (Q13): UI maxclass set - Verification Report

**Goal:** Implement Q13 (C4, C5): remove non-UI live.* and `patcher` from the UI set, make `add_box("p"|"patcher")` raise, add the 18 bundle-verified UI maxclasses, add a sync report section, add the bundled-help test, and ask the user to confirm `live.thisdevice` in MAX.
**Status:** human_needed (all automated checks pass; the MAX load check is a human item by design)
**Re-verification:** No, initial verification.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | The 14 non-UI live.* and `patcher` are absent from UI_MAXCLASSES and UI_SIZES. `add_box("live.thisdevice")` serializes as newobj with text and DB I/O. | VERIFIED | Ran the code: none of the 15 names are in either structure. `to_dict()` gives `{maxclass: newobj, text: live.thisdevice, numinlets: 1, numoutlets: 3, patching_rect w=121 h=22}`. |
| 2 | `_validate_maxclass_usage` flags an own-maxclass box of a removed name or `patcher` (without an embedded patcher) as a blocking "Wrong maxclass" error. The save gate refuses it. | VERIFIED | A hand-built dict with maxclass `live.thisdevice` and maxclass `patcher` gave 2 objects-layer "Wrong maxclass" errors, and `has_blocking_errors` was True. `_MAXCLASS_USAGE_SKIP = {inlet, outlet, bpatcher}` is in validation.py, and `_STRUCTURAL_MAXCLASSES` is unchanged. TestSaveGateEndToEnd passes. |
| 3 | `add_box` refuses `p`/`patcher` (pointing to `add_subpatcher`) and DB-less UI names (markup, progress), before an id is consumed. `replace_box`, `replace_box_safe` and `insert_into_connection` refuse without mutating. | VERIFIED | Ran all four: ValueError, `_next_id` 1 and `boxes` empty on a fresh patcher. On a populated patcher the three edit paths raised, and `_next_id`, boxes, lines and the old box were all unchanged. `_require_buildable` is called in `add_box` and in `replace_box` before `_require_domain_scope`. |
| 4 | 18 UI maxclasses are added (75 -> 93) and sizes (66 -> 84). markup is None. | VERIFIED | `len(UI_MAXCLASSES)=93`, `len(UI_SIZES)=84`. All 18 names are in both structures. The size values match the plan. The TestBundleEvidence tests (requires_max, run here) confirm each name has boxes in the bundle and 0 newobj tokens. |
| 5 | `validate_patch` raises zero "Wrong maxclass" errors on the top level of the bundled help patches. | VERIFIED | `test_no_wrong_maxclass_in_bundled_help` is real: it asserts `checked >= 2000` and `found == []`. It ran (Max.app is present, 185 passed, 0 skipped) and handles the G8 crash files via `_validate_maxclass_usage`. |
| 6 | The report-only `ui_maxclasses` sync section exists, is last in SECTION_KEYS, and reports the planned figures. Other summary lines are unchanged. | VERIFIED | The dry run prints `116 in bundle survey (3139 files); 27 missing ...; 1 UI entries MAX writes only as newobj: colorpicker; 3 unobserved`. The other 9 lines match the plan's evidence. Git status was clean after the run (nothing written). |
| 7 | Committed-patch behavior is unchanged, scope is respected, and the suite is green. | VERIFIED | `git diff --stat b0842779..HEAD` touches exactly the 10 allowed files, with nothing under `patches/`, CLAUDE.md, TECHNICAL.md, README.md or `.claude`. Full suite: **3171 passed, 1 xfailed, 1 xpassed, 29 warnings** (re-run by the verifier). The six changed `.py` files parse with `feature_version=(3,10)`. I did not independently re-run the 69-patch triage; I relied on SUMMARY (the triage JSON files are in the task dir) and on the green integration tests. |

**Score:** 7/7 truths verified (0 behavior-unverified).

### Required Artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| `src/maxpat/maxclass_map.py` | VERIFIED | Removals and additions are present, with provenance comments and a docstring. |
| `src/maxpat/sizing.py` | VERIFIED | The 15 entries are removed and 18 are added. |
| `src/maxpat/validation.py` | VERIFIED | `_MAXCLASS_USAGE_SKIP` is defined and used. |
| `src/maxpat/builders.py` | VERIFIED | `_require_buildable` is called first in `add_box`. |
| `src/maxpat/patcher.py` | VERIFIED | `replace_box` calls `_require_buildable` before any mutation. |
| `tools/sync_max_bundle.py` | VERIFIED | `survey_maxclasses` and `section_ui_maxclasses` are wired into `run_report` and `format_summary`. |
| Tests | VERIFIED | `tests/test_maxclass_map.py` (+442 lines) has requires_max tests. `test_sync_max_bundle.py` has hermetic survey tests. |

### Key Links

| From | To | Status |
|------|----|--------|
| Box -> `resolve_maxclass` | maxclass_map | WIRED (live.thisdevice serializes as newobj) |
| `add_box` -> `_require_buildable` | `is_ui_object` + `db.exists` | WIRED |
| validation -> `_MAXCLASS_USAGE_SKIP` | validator behavior | WIRED (a maxclass patcher box is flagged) |
| save gate -> validate_patch | refusal of a bad file | WIRED (tested by TestSaveGateEndToEnd) |
| sync tool -> UI_MAXCLASSES | report diff | WIRED |

### Requirements Coverage

| Requirement | Status |
|-------------|--------|
| C4 | SATISFIED |
| C5 | SATISFIED |

### Anti-Patterns

No debt markers or stubs were found in the changed code. The diff was read in full.

### Residuals (SUMMARY-disclosed, outside Q13 scope)

These are not gaps in Q13. They are owned by later tasks or need a user decision:
- `m4l_polish.organize_push_banks` writes maxclass `live.banks`, which is now a true-positive "Wrong maxclass" save-gate blocker (Q15/D5).
- `markup` and `progress` are refused by `add_box` until they have DB entries (Q38).
- The G8 crash (Q19).
- Open decisions: `colorpicker` stays in the UI set although MAX writes it only as newobj; package-gated UI names build with guessed I/O; the 27 other bundle maxclasses.

### Human Verification Required

1. **live.thisdevice loads in MAX** (required by the fix-plan).
   - Test: open `confirm-live-thisdevice.maxpat` from the task dir in MAX 9.2.
   - Expected: `live.thisdevice` and `print thisdevice` create as object boxes, with no "No such object" or maxclass error.
   - Why human: MAX load behavior is not observable from the repo. The patch on disk has the correct shape (newobj `live.thisdevice` with 1 in / 3 out, newobj print, midiin, midiout).
2. **Optional:** open `confirm-ui-maxclasses.maxpat`. Expect the 16 widgets to render as widgets with no errors.

## Gaps Summary

No gaps. The implementation matches the plan and the fix-plan Q13 bullets. The remaining item is the MAX load confirmation, which was designed as a human step.

---
_Verified: 2026-10-13_
_Verifier: Claude (gsd-verifier)_
