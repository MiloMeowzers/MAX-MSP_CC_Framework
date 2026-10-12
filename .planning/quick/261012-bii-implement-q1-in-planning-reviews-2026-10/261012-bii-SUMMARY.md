---
phase: quick-261012-bii
plan: 01
subsystem: validation
tags: [validation, layer3, non-destructive, review-q1]
status: complete
requires: []
provides:
  - "pure validate_patch (dict and Patcher identical, input never mutated)"
  - "ValidationResult.proposed_removal + apply_fixes(patch, results)"
  - "has_blocking_errors(results, is_new=True)"
  - "ObjectDatabase.is_known_pair (relationships.json)"
affects: [hooks.validate_file, max-patch-agent, max-dsp-agent, Q2, Q3, Q7]
tech-stack:
  added: []
  patterns: ["removals as data, applied only by explicit apply_fixes"]
key-files:
  created:
    - tests/test_validation_nondestructive.py
  modified:
    - src/maxpat/validation.py
    - src/maxpat/__init__.py
    - src/maxpat/db_lookup.py
    - tests/test_validation.py
    - tests/test_integration_patches.py
    - tests/test_round_trip.py
    - .claude/skills/max-patch-agent/SKILL.md
    - .claude/skills/max-dsp-agent/SKILL.md
decisions:
  - "Layer 3 is pure: invalid cords are errors carrying proposed_removal=(src_id, outlet, dst_id, inlet); only apply_fixes removes them"
  - "has_blocking_errors defaults to is_new=True so un-updated callers block on proposed removals; is_new=False reports without blocking (Q7 adds the HEAD diff)"
  - "Container boxes (p/patcher/bpatcher/poly~/mc.poly~/pfft~/rnbo~/any embedded patcher) accept any cord; their outlets carry no signal_role; bounds still enforced"
  - "All _ROLE_TIER_TABLE rows are warnings; a role mismatch never removes a cord"
  - "relationships.json pairs are unordered, alias-canonical, and exempt from type/role checks only (never bounds)"
metrics:
  duration: "~25 min"
  completed: 2026-10-12
actuals:
  tokens: 17669
  tasks: 3
  commits: 3
plan_head_before: 0f96a6f1806693601d6835f8bbc79f313e7ab67e
plan_head_after: 294f90c44189da131a4c189ea4ce586ef1bcff08
---

# Quick 261012-bii: Non-destructive validate_patch (Q1) Summary

`validate_patch` no longer deletes cords. Layer 3 now reports each cord it would drop as an error carrying a `proposed_removal` 4-tuple. Only an explicit `apply_fixes()` call removes anything, and proposed removals block new patches. Containers and `relationships.json` pairs are exempt from type/role checks, and role mismatches are warnings. All 3 committed patches that used to lose a working cord now keep it.

## Commits

| Task | Commit | Files |
|---|---|---|
| 1. Pure Layer 3, proposed removals, `apply_fixes`, blocking, containers, warning roles, integration gate | a3ab4aa | validation.py, `__init__.py`, test_validation_nondestructive.py (new), test_validation.py, test_integration_patches.py |
| 2. `relationships.json` known pairs (tapin~ -> tapout~) | 879a46b | db_lookup.py, validation.py, test_validation_nondestructive.py |
| 3. Skill protocols validate a deepcopy; round-trip comment | 294f90c | max-patch-agent/SKILL.md, max-dsp-agent/SKILL.md, test_round_trip.py |

## Pytest

| Point | Result |
|---|---|
| Baseline (HEAD 0f96a6f) | 3 failed, 2309 passed, 2 xfailed, 1 xpassed |
| Task 1 RED | new file: ImportError at collection (`apply_fixes`); test_validation.py 15 failed / 94 passed; integration `-k validate_no_errors or mixer-strip` 34 failed (AttributeError `proposed_removal`) |
| After Task 1 | 3 failed, 2341 passed, 2 xfailed, 1 xpassed (+32 new tests) |
| Task 2 RED | TestKnownPairs: 3 failed, 1 passed (the bounds test already passed, as expected) |
| Final | 3 failed, 2345 passed, 2 xfailed, 1 xpassed |

The failing set is identical to the baseline: only the 3 allowed `test_review_patch_no_blockers` cases (minitaur, physics-composition, timestretch). The Python 3.10 syntax gate passes on every changed `.py` file.

## The 3 known strips

None of them is allowlisted or xfailed. The S13 fallback was not needed.

| Patch | Cord | Path | Final findings on that cord |
|---|---|---|---|
| mixer-strip | obj-15:0 -> obj-37:0 (`selector~` -> `p sends`) | container rule | 0. Patch total: 0 errors, 0 proposed. |
| terrain-voice | obj-16:0 -> obj-60:0 (`*~` -> `p motion`) | container rule | 0. Patch total: 0 errors, 0 proposed. The false Layer-4 `Unterminated signal chain: '*~' (obj-16)` warning is also gone. |
| scala-synth-voice | obj-1:0 -> obj-3:0 (`in 1` -> `peek~`) | warning-only role | 1 warning: `status outlet → signal inlet: use snapshot~ ('obj-1' outlet 0 -> 'obj-3' inlet 0) -- connection kept`. Patch total: 0 errors, 0 proposed. |

## Mixer-strip review xfail

I re-ran `review_patch`. The only blocker is `Fan-out without trigger: '+' (obj-14) outlet 0 -> selector~ obj-15/obj-16`. The `_REVIEW_XFAILS` reason now names that blocker and Q3, and the mark is `strict=True`. It reports XFAIL. Q3 must delete the entry once the fan-out false positive is fixed.

## Hand-offs

- **Q2:** scala-synth-voice obj-1 -> obj-3 still emits a role **warning** until Q2 fixes the DB:
  - `in` outlet role should be None (currently `status`);
  - `peek~` inlets should be control (currently inlet 0 `signal:true`).

  The `poly~` / `pfft~` / `mc.poly~` / `p` inlet-0 overrides are still `signal:false`. That no longer affects Layer 3 (the container rule), but Q2 should repair them.
- **Q7:** `has_blocking_errors(results, is_new=False)` does not block on proposed removals. Q7's HEAD diff supplies that gate for edits.

## Deviations from Plan

None. The plan was executed as written.

Live values that differed from observed_facts:
- `relationships.json` has **43** `pairs` entries, not 44. The 3-object pfft~ group is present as described.

Behaviour worth knowing, within spec:
- The known-pair skip covers every `relationships.json` pair, not just tapin~/tapout~. For example `line~ -> *~`, `snapshot~ -> number` and `loadbang -> trigger` now skip type/role checks too. Bounds are still enforced.
- Malformed patchlines with a non-list `source` or `destination` are now treated as malformed instead of raising, following S1.

## Doc impact (rule 8; not edited)

- TECHNICAL.md:52/404/428 still says auto-fix removes cords and that auto-fixed errors don't block.
- CLAUDE.md:197 still says "gets stripped by validation".
- `max-patch-agent/SKILL.md:46`: the capability list doesn't mention `apply_fixes`.
- These are still correct for Patcher input but don't mention proposed removals:
  - `max-critic/SKILL.md:49`
  - `references/shared-capabilities.md:135`
  - `.claude/commands/max-iterate.md:106`
  - `.claude/commands/max-build.md:30/58`
- The user memory entry `feedback_validate_mutates.md` is now **obsolete**, since validation is pure. Retiring it is your call; I did not touch memory files.

## Confirm in MAX (rule 9)

None. No patch file or generated output changed. This only stops the validator from deleting cords. The `patches/` diff for this plan's range is empty, the stash count is unchanged (0), and `patches/.active-project.json` and `.planning/tci-phase2/` were left untouched.

## Known Stubs

None.

## Threat Flags

None. No new network, auth or file-access surface.

## Self-Check: PASSED

- FOUND: tests/test_validation_nondestructive.py, src/maxpat/validation.py (`def apply_fixes`), src/maxpat/db_lookup.py (`def is_known_pair`)
- FOUND commits: a3ab4aa, 879a46b, 294f90c
