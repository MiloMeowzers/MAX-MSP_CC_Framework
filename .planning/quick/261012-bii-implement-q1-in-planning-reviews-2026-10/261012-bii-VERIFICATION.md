---
phase: quick-261012-bii
verified: 2026-10-12T15:43:20Z
status: passed
score: 9/9 must-haves verified
covered_files:
  - ".claude/skills/max-dsp-agent/SKILL.md"
  - ".claude/skills/max-patch-agent/SKILL.md"
  - ".planning/quick/261012-bii-implement-q1-in-planning-reviews-2026-10/261012-bii-PLAN.md"
  - ".planning/quick/261012-bii-implement-q1-in-planning-reviews-2026-10/261012-bii-SUMMARY.md"
  - "src/maxpat/__init__.py"
  - "src/maxpat/db_lookup.py"
  - "src/maxpat/validation.py"
  - "tests/test_integration_patches.py"
  - "tests/test_round_trip.py"
  - "tests/test_validation.py"
  - "tests/test_validation_nondestructive.py"
covered_digest: "v2:sha256:62c4d628ff9ee0b21a4e2bcf500396e3e99743ac808fc5214b3006186f09469f"
behavior_unverified: 0
overrides_applied: 0
---

# Quick 261012-bii (Q1: non-destructive validate_patch) Verification Report

**Goal:** Implement Q1 of `.planning/reviews/2026-10-11-fix-plan.md`: make `validate_patch` non-destructive.
**Status:** passed
**Re-verification:** No, initial verification.

## Goal Achievement

I verified this against the code and by running things myself. I did not rely on SUMMARY.md.

| # | Truth (Q1 spec / plan must_haves) | Status | Evidence |
|---|---|---|---|
| 1 | `validate_patch` never mutates its input; dict and Patcher give identical results | VERIFIED | The old `lines.pop` loop is gone from `_validate_connections` (diff). My own script ran `validate_patch` on all 56 committed `.maxpat` files: 0 mutated. It also compared dict and `Patcher.from_dict` input on each: 0 differences. |
| 2 | Removals are data: `proposed_removal=(src,outlet,dst,inlet)`. Only `apply_fixes` removes anything. | VERIFIED | `ValidationResult.proposed_removal` slot exists. `_line_key` builds the key. `apply_fixes` (validation.py) handles dict and Patcher. It is exported from `src/maxpat/__init__.py`. Tests: `TestApplyFixes`, `TestProposedRemoval`. |
| 3 | `has_blocking_errors` blocks a proposed removal for new patches. `is_new=False` reports but does not block. | VERIFIED | Code read. `is_new=True` is the default. The only `src/` caller, `hooks.py`, uses the default. `TestHasBlockingErrorsQ1` passes. |
| 4 | Containers (`p`, `patcher`, `bpatcher`, `poly~`, `mc.poly~`, `pfft~`, `rnbo~`, any embedded patcher) accept any cord and carry no outlet role. Bounds are still enforced. | VERIFIED | `_CONTAINER_NAMES` and `_is_container_box` match the spec list plus the embedded-patcher rule. Bounds checks run first and `continue`. The destination-container skip comes after. The role dispatch is skipped for a container source. `TestContainers` passes, including the inlet-3 bounds case. |
| 5 | A role mismatch warns and never removes. `relationships.json` pairs are never flagged, but bounds still apply. | VERIFIED | All six `_ROLE_TIER_TABLE` rows are `("warning", ...)`. `ObjectDatabase.is_known_pair` loads the pairs unordered and alias-canonical. The skip sits after the bounds checks. `TestKnownPairs` and `TestRoleMismatchWarns` pass. |
| 6 | The 3 known strips keep their cords with 0 proposed removals, with no allowlist or xfail. | VERIFIED | I checked directly. mixer-strip obj-15->obj-37: cord kept, 0 connection findings. terrain-voice obj-16->obj-60: cord kept, 0 findings. scala-synth-voice obj-1->obj-3: cord kept, 0 proposed, one warning `status outlet -> signal inlet ... -- connection kept`. That warning is a Q2 hand-off (DB data) and not an error. `test_validate_patch_no_errors` has no xfail and no allowlist. |
| 7 | `test_validate_patch_no_errors` fails on any proposed removal. The mixer-strip review xfail is `strict=True` with an accurate reason. | VERIFIED | The diff filters `r.level == "error" or r.proposed_removal is not None`. `_make_review_params` uses `strict=True`. The reason names the fan-out blocker. Test run shows XFAIL for mixer-strip (not XPASS). `_ALLOWLIST` is unchanged. |
| 8 | The max-patch-agent and max-dsp-agent protocols validate `copy.deepcopy` and treat proposed removals as "inspect, don't save". | VERIFIED | The diffs touch only the named Output Protocol (New Patches) steps. Both use `validate_patch(copy.deepcopy(patch_dict), db=patcher.db)`, state the inspect-don't-save rule, and gate the save on `has_blocking_errors(results, is_new=True)`. |
| 9 | The failing set equals the baseline and no `patches/` file changed. | VERIFIED | See below. |

**Score:** 9/9 truths verified.

## Behavioral Spot-Checks and Test Runs

| Check | Result |
|---|---|
| `pytest tests/test_validation_nondestructive.py tests/test_validation.py tests/test_integration_patches.py` | 3 failed, 251 passed, 1 xfailed. The 3 failures are the allowed `test_review_patch_no_blockers` cases (minitaur, physics-composition, timestretch). |
| Full `python3 -m pytest -q` | 3 failed, 2345 passed, 2 xfailed, 1 xpassed. Failing set is exactly the 3 allowed cases. XFAIL is the mixer-strip case plus `test_framework_file_byte_identical`. XPASS is `test_max_saved_file_byte_identical`. Both round-trip markers pre-date Q1. |
| Purity and dict/Patcher identity over all 56 committed patches (own script) | 0 mutated, 0 differences, 0 proposed removals. |
| `git diff --name-only 0f96a6f..HEAD -- patches/` | Empty. The commits touch only the 9 planned files. |
| `git stash list` | 0 entries. |
| `git status` | Only `patches/.active-project.json` (M) and `.planning/tci-phase2/` (untracked) remain, as before. |

## Requirements Coverage

| Requirement | Status | Evidence |
|---|---|---|
| A2: pure validation, `apply_fixes`, skills validate a deepcopy | SATISFIED | Truths 1, 2, 8 |
| A1 (API part): containers, role warnings, known pairs | SATISFIED | Truths 4, 5 |
| A8: the integration test counts proposed removals; the xfail is strict | SATISFIED | Truth 7 |

## Anti-Patterns Found

None blocking. I found no new TODO, FIXME, XXX or TBD markers in the changed source. The tests were rewritten, not removed. Old-contract tests were renamed and now assert "cord kept plus proposal". The skip and xfail diff scan of `tests/test_validation.py` found nothing.

## Notes (informational, not gaps)

- The known-pair skip covers all 43 `relationships.json` pairs, not only `tapin~`/`tapout~`. Examples are `line~ -> *~` and `loadbang -> trigger`. This follows the spec ("never flag a pair listed in relationships.json"). Bounds are still enforced.
- The SUMMARY says `relationships.json` has 43 pairs, not the 44 the plan observed. This is a harmless discrepancy.
- Q2 hand-off: scala-synth-voice still emits a role warning until the `in`/`peek~` DB data is fixed.
- Q7 hand-off: the `is_new=False` edit path needs a HEAD diff gate to block proposed removals.
- Doc impact (not edited, per rule 8): TECHNICAL.md:52/404/428, CLAUDE.md:197, and the capability lists in several skills and commands. The memory entry `feedback_validate_mutates.md` is now obsolete.
- Human verification: none needed. No patch or generated output changed.

---

_Verified: 2026-10-12_
_Verifier: Claude (gsd-verifier)_
