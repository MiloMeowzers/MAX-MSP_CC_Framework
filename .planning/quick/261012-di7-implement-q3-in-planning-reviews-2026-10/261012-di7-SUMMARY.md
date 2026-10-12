---
phase: quick-261012-di7
plan: 01
status: complete
subsystem: critics
tags: [critics, fan-out, bach, dsp, validation, allowlist, calibration, q3]
requires: [quick-261012-bii (Q1), quick-261012-c5i (Q2)]
provides:
  - fan-out critic with display-sink/preset filters, outlettype signal test, trigger outlets checked, reconvergence-only blockers
  - Bach-llll command-source exemption at note severity
  - control-rate-to-signal-rate check removed
  - comment #N set-fed skip
  - pruned, hygiene-tested review-blocker allowlist
  - calibration test (zero blockers on 12 user-confirmed projects)
affects: [max-critic loop, tests/test_integration_patches.py]
tech-stack:
  added: []
  patterns: [BFS reconvergence over control-cord adjacency, allowlist hygiene test]
key-files:
  created:
    - tests/test_critic_precision.py
  modified:
    - src/maxpat/critics/structure_critic.py
    - src/maxpat/critics/package_critic.py
    - src/maxpat/critics/dsp_critic.py
    - src/maxpat/validation.py
    - tests/test_critics.py
    - tests/test_integration_patches.py
    - tests/test_signal_role_migration.py
    - tests/review_blocker_allowlist.json
decisions:
  - "OQ1 = A (user-chosen): fan-out blocks only when two branches reach one non-all-hot box at different inlets"
  - "OQ2 = A (user-chosen): control-rate-to-signal-rate check deleted"
  - "slot.maxpat buffer~ obj-1 outlet 1 is a true positive, allowlisted with a reason (rule 3)"
metrics:
  duration: 9m
  completed: 2026-10-12
actuals:
  tokens: 23280
  tasks: 3
  commits: 3
plan_head_before: 1138d30de8f2366f3a771c8a7732561709f47409
plan_head_after: 3008d2226351361291145650e9969aa7b70fee13
---

# Quick 261012-di7: Q3 Critic Precision Summary

Fan-out critic now ignores display sinks and preset membership cords, reads signal-ness from outlettype, checks trigger outlets, and blocks only on hazard-shaped reconvergence. Bach-llll exempts command sources at note severity, the control-to-signal check is gone, comment `#N` skips set-fed comments, and the allowlist is pruned 120 -> 1 behind a hygiene test and a zero-blocker calibration gate. The full suite is green.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 5a2363c | fan-out precision (E1), slot true positive allowlisted, mixer-strip xfail removed |
| 2 | 39033ce | Bach-llll note + command sources (E4), control-to-signal removed (E2), comment #N set-fed skip |
| 3 | 3008d22 | allowlist pruned to live reasoned entries, hygiene and calibration tests |

## Open questions

- OQ1: **A** (user-chosen 2026-10-12). Hazard-shaped reconvergence (different inlets, all-hot/container set exempt).
- OQ2: **A** (user-chosen 2026-10-12). `_check_audio_rate_consistency` deleted.

## Test totals

- Baseline (HEAD 1138d30): 3 failed, 2390 passed, 2 xfailed, 1 xpassed. The failures were exactly the 3 allowed cases (minitaur, physics-composition, timestretch).
- After Task 1: 1 failed (physics-composition, baseline), 2413 passed, 1 xfailed, 1 xpassed.
- After Task 2: 2445 passed, 1 xfailed, 1 xpassed (0 failed).
- Final (after Task 3): **2475 passed, 1 xfailed, 1 xpassed, 0 failed.**

RED counts recorded before each GREEN step:
- Task 1 (`test_critic_precision.py`, fan-out classes): 17 failed, 2 passed. The 2 that passed are intended regression anchors: the missing-outlettype `~` fallback, and the two-hop `i`/`button` -> `+` reconvergence, which was already a blocker.
- Task 2 (Bach/control/comment classes added): 28 failed, 22 passed. The 22 are the 19 Task 1 tests plus 3 anchors: `set Label` with no `#N` still warns, the unfed comment still warns, and the barnett-dbap obj-27 prose still warns.
- Task 3: `test_review_allowlist_entries_are_live` failed with 234 problems (1 missing file, 119 stale, 114 reasonless). `test_review_allowlist_excludes_calibration_projects` failed on 9 calibration keys. The coverage test and the 27 calibration cases passed, because the critic fixes had already landed.

## Corpus before/after (55 top-level committed patches)

| Measure | Before | After |
|---|---|---|
| Review blockers | 76 | 1 (slot.maxpat, allowlisted) |
| Fan-out blockers / warnings | 73 / 0 | 1 / 37 |
| Bach-llll findings | 3 blockers | 0 |
| Control-rate to signal-rate | 399 | 0 |
| Comment `#N` warnings (all `patches/**`) | 5 | 2 |
| Calibration blockers (27 files, 12 projects) | 36 (from observed_facts, not re-run) | 0 |

All live values matched the planner's observed_facts.

## Allowlist prune (120 -> 1)

Removed per patch: gen-eq 14, gong-model 6, intelligent-corpus-remixer 3, kicksynth 8, looper 1, minitaur 36, mixer-bus 1, comp-band 5, physics-composition 3, reverse-delay-mono 1, reverse-delay 1, rhythmic-sampler 2, slot 9 (1 kept), scala-synth-voice 2, scala-synth 16, simple-fm 1, stereo-feedback-delay 1, stutter 8, wormhole-test 1, and terrain-osc-test.maxpat 1 (the file no longer exists; its key was dropped). `_doc` was rewritten to say most former entries were critic false positives.

## Rule 3 true positives (allowlisted)

- `patches/rhythmic-sampler/generated/slot.maxpat`, fan-out, `buffer~ #1` obj-1 outlet 1. Reason: outlet 1 sends a bang after read. It feeds `setbuffer #1` obj-27, which reaches waveform~ obj-4 inlets 2/3 via js slot-engine.js -> `t f f` -> expr -> `trigger f f`. It also feeds `set #1` obj-28, which reaches waveform~ inlet 0. This works in MAX because fan-out fires right-to-left by box position (setbuffer at x=300 fires before set at x=110). The patch is frozen. The `~` name hid this before Q3.

## Deviations from Plan

**1. [Rule 3 - Blocking] Lowered the dsp_critic consumer-site floor in `tests/test_signal_role_migration.py` (4 -> 3)**
- **Found during:** Task 2 (full-suite run).
- **Issue:** `TestBackCompatConsumerAnchors::test_dsp_critic_outlet_signal_read_pattern_unchanged` counts `outlettype ... _SIGNAL_OUTLET_TYPES` reads in dsp_critic.py. The deleted `_check_audio_rate_consistency` was one of the four sites. The planner's simulated break list did not include this test.
- **Fix:** Set the floor to 3, with a comment citing Q3 / E2. The three remaining consumers (gain staging and the two unsafe-gain reads) are still anchored.
- **Files:** tests/test_signal_role_migration.py (an extra file in commit 39033ce, outside Task 2's `<files>`).

**2. [Cosmetic] dsp_critic section header "Check 4: Unsafe gain sources" renumbered to "Check 3"** after the old Check 3 was deleted. The `review_dsp` Checks list now names unsafe gain sources as item 3.

Otherwise the plan was executed as written.

## Residual noise (out of scope)

- Comment `#N` prose hits still warn: `patches/barnett-dbap/generated/barnett-dbap.maxpat` obj-27 and `patches/looper/generated/looper-demo.maxpat` obj-6. These are documentation comments that mention `#2` / `#1` and are fed by nothing.

## Hand-offs

- **Q23 (R10):** bach -> non-bach without `@out t` (the real Bach trap) is not detected.
- **Q26 (E5):** hot/cold noise. `_check_hot_cold_ordering` still uses the `~` name and still skips trigger-fed boxes. `_is_trigger_object` and `_is_signal_object` are kept for it.
- **Q19/Q20:** the critics still review the top level only (no subpatcher recursion).

## Doc impact (not edited, rule 8)

- `TECHNICAL.md:494`: the fan-out severity row says warning. It is now a blocker on reconvergence, otherwise a warning.
- `TECHNICAL.md:506`: the audio-rate consistency row is obsolete (the check is removed).
- `.claude/skills/max-critic/SKILL.md:65`: Bach llll is now a note, and command sources are exempt.
- `.claude/skills/references/shared-capabilities.md:51-81`: the critic now flags trigger outlets too and blocks only reconvergent fan-out. The generation rule "always use trigger" is unchanged.
- `.claude/skills/max-patch-agent/SKILL.md:71`: same fan-out severity note.
- CLAUDE.md Rule #4 (use trigger for fan-out) is still correct as a generation rule.

## Confirm in MAX (rule 9)

Nothing is required: no patch file changed. Optional: glance at rhythmic-sampler `slot.maxpat` (buffer~ -> setbuffer/set ordering). It now carries the only allowlisted blocker.

## Threat model

- T-di7-01: blocker anchors are kept in the tests: `number -> +` inlets 0/1, the two-hop `i`/`button` -> `+` case, a reconvergent `t b b` outlet, and the real slot.maxpat case.
- T-di7-03: the hygiene test is in place.
- T-di7-04 and T-di7-05: the final gate passed (no `patches/` paths in the commits or the working tree apart from the pre-existing `.active-project.json`, stash list unchanged, exactly 3 commits).

## Self-Check: PASSED

- tests/test_critic_precision.py exists (TestFanOutPrecision, TestFanOutCommittedPatches, TestBachCommandSources, TestControlToSignalRemoved, TestCommentHashSetFed).
- Commits 5a2363c, 39033ce and 3008d22 are present on main.
- The Python 3.10 `ast.parse` gate passed on every changed .py file.
