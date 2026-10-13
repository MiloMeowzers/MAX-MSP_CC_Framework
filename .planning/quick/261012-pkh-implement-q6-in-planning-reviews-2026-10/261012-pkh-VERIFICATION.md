---
phase: quick-261012-pkh
verified: 2026-10-12T00:00:00Z
status: passed
score: 7/7 must-haves verified
covered_files:
  - src/maxpat/hooks.py
  - src/maxpat/layout.py
  - src/maxpat/patcher.py
  - tests/test_edit_keeps_user_work.py
covered_digest: "v2:sha256:5f24018311b0d5c05b9291feb3a1c88efd5751ddec1e942f71f83e8c2b289ad1"
behavior_unverified: 0
overrides_applied: 0
---

# Quick 261012-pkh (Q6): Edit path keeps cord routing and cords. Verification Report

**Goal:** Implement Q6 of `.planning/reviews/2026-10-11-fix-plan.md`: the edit path keeps routing and cords (B1, B2, B3, plus assistance comments).
**Status:** passed
**Re-verification:** No, initial verification.

## Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | ji-harmonizer deepcopy through `finalize_patch(is_new=False)` keeps all 367 midpoint lists, keeps straight cords straight, and serialized `lines` equal the file's in every patcher | VERIFIED | Independent in-memory script: kept 367, changed 0, straight cords routed 0, `lines equal True` across all nested patchers. `_finalize_midpoints_recursive` no longer has the clearing loop (git diff). |
| 2 | Edit-path cord gets midpoints only if it has none AND is new or touches an added/moved box; `is_new=True` path unchanged | VERIFIED | `hooks.py` `_box_added_or_moved` (`_raw is None`, no `_loaded_rect`, or x/y differs from the snapshot) and `_eligible` (`line._raw is None` or touches a touched id). `layout._generate_midpoints(..., *, eligible=None)` default is unchanged. `is_new=True` branch is untouched. Moved-box, unmoved-control and resize-only tests pass. |
| 3 | `populate_assistance_comments` writes `_raw["comment"]` so comments reach disk on loaded subpatchers | VERIFIED | `_set_assistance_comment` writes both `extra_attrs` and `_raw`. All four former assignments use it. Skip rule for non-empty comments is unchanged. Synthetic and ji-harmonizer (15 ports) tests pass. |
| 4 | `modify_box(args=...)` keeps I/O and cords for content-defined boxes (embedded patcher, bpatcher, p/gen~/js/etc., names not in the DB, non-variable_io) | VERIFIED | `_io_is_content_defined` and `CONTENT_DEFINED_NAMES` match the spec. Independent FDNVerb check: top-level `gen~ FDNverb` stays 2/2 with 41 lines and `orphaned == []`. Test file covers `p`, `js` and an unknown abstraction. |
| 5 | variable_io objects recompute and keep in-range cords, orphans are returned; identical text is a no-op | VERIFIED | Recompute branch only when `not _io_is_content_defined`. The orphan sweep is retained. `new_text != box.text` guard gives the no-op. pack/trigger/expr tests pass. Existing `test_patcher.py` / `test_round_trip.py` modify_box contracts are unedited and green. |
| 6 | message/comment `modify_box(args)` text is the joined args with no maxclass prefix, I/O unchanged, reaches `_raw` | VERIFIED | `new_text = " ".join(new_args)` for `message`/`comment`; `_raw["text"]` synced. TestModifyBoxText passes. |
| 7 | Step 3 of all six Output Protocol blocks updated; suite green; no `patches/` change; stash unchanged; Python 3.10 syntax clean | VERIFIED | Six skills each have 1 "never clears existing midpoints" line and 0 old "regenerates cable midpoints" lines. The skill diff is exactly 6 one-line replacements. Full suite: 2559 passed, 1 xfailed, 1 xpassed, 29 warnings. `git diff --stat bc1ab66 HEAD -- patches` is empty. `git status -- patches/` shows only the pre-existing `.active-project.json`. `git stash list` is empty and matches `stash-list-before.txt`. `ast.parse(feature_version=(3,10))` passes on all four `.py` files. |

**Score:** 7/7 truths verified, 0 behavior-unverified. Every behavior-dependent truth has an exercising test (19 tests in `tests/test_edit_keeps_user_work.py`, all passing) plus my own independent repro on the real patches.

## Required Artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| `tests/test_edit_keeps_user_work.py` | VERIFIED | Exists, about 500 lines, 19 passing tests. Contains `TestFinalizeKeepsRouting`. |
| `src/maxpat/hooks.py` | VERIFIED | Contains `_box_added_or_moved`; clearing loop removed. |
| `src/maxpat/layout.py` | VERIFIED | Keyword-only `eligible` on `_generate_midpoints`; default behavior byte-identical. |
| `src/maxpat/patcher.py` | VERIFIED | `_loaded_rect` (init and `from_dict`), `CONTENT_DEFINED_NAMES`, `_io_is_content_defined`, modify_box rules, `_raw["comment"]`. |
| Six `SKILL.md` | VERIFIED | Step 3 line replaced with the S5 text. |

## Key Links

| From | To | Status |
|------|----|--------|
| `hooks._finalize_midpoints_recursive` | `layout._generate_midpoints(eligible=...)` | WIRED. Called per patcher and recursed into subpatchers. |
| `patcher.from_dict` | `hooks._box_added_or_moved` via `_loaded_rect` | WIRED. Snapshot is a tuple copy taken at load. |
| `modify_box` | `_io_is_content_defined` / `db.compute_io_counts` | WIRED. |
| `_populate_comments_recursive` | on-disk `comment` via `_raw` | WIRED. Verified through `to_dict()` serialization. |

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| ji-harmonizer routing kept | in-memory script (scratchpad, no writes) | 367/367 kept, 0 straight routed, lines equal | PASS |
| FDNVerb `gen~ FDNverb` same args | same script | 2/2, 41 lines, no orphans | PASS |
| New test file | `pytest tests/test_edit_keeps_user_work.py` | 19 passed | PASS |
| Full suite | `pytest -q -p no:cacheprovider` | 2559 passed, 1 xfailed, 1 xpassed | PASS |

## Anti-Patterns

No TBD/FIXME/XXX markers were introduced in the changed source. No stubs. Commits touch only the plan's listed files: 12b3c92 (4 files), 9c724c9 (2 files), 9c4885f (6 files).

## Requirements Coverage

| Requirement | Status |
|-------------|--------|
| B1 | SATISFIED |
| B2 | SATISFIED |
| B3 | SATISFIED |

## Human Verification

None required. No patch file changed. The optional MAX checks listed in SUMMARY.md (reopen an edited patch, confirm routing intact and tooltips) are advisory only.

## Residuals (declared in SUMMARY, accepted by the plan, not gaps)

- A moved box's already-routed cords keep their old midpoints (spec rule, T-pkh-07).
- expr/vexpr changed-expression I/O miscount goes to Q10 (OQ1-A, user-selected).
- modify_box(args) on UI widgets other than message/comment still writes a text field.
- Doc files (`shared-capabilities.md`, `TECHNICAL.md`, `README.md`, `max-iterate.md`) are intentionally unedited and listed in SUMMARY.

## Gaps Summary

None. The SUMMARY's claims (test totals, repro numbers, commit scope, skill edits) were independently reproduced against the codebase.

---

_Verified: 2026-10-12_
_Verifier: Claude (gsd-verifier)_
