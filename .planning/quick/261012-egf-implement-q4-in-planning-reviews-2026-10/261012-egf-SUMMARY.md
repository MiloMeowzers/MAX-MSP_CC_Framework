---
phase: quick-261012-egf
plan: 01
subsystem: critics
status: complete
tags: [critics, gen~, mc.gen~, rnbo~, m4l, review_patch, Q4, E3, D4]
requires: [Q3 _outlet_is_signal (structure_critic)]
provides:
  - "_GEN_BOX_NAMES / _gen_inner_patcher / wired-codebox selection in dsp_critic"
  - "is_rnbo_box shared by review_rnbo and _has_rnbo_boxes"
  - "detect_m4l_device_type + review_m4l dispatched from review_patch"
  - "path-based gain-stage check (gain~/live.gain~ -> plugout~) and ezdac~ blocker"
affects: [max-critic loop, Q7 save gate, Q15, Q26, Q19/Q20]
tech-stack:
  added: []
  patterns: ["detect boxes by get_box_name, never maxclass", "reverse-BFS over signal cords via _outlet_is_signal"]
key-files:
  created:
    - tests/test_critic_revival.py
  modified:
    - src/maxpat/critics/dsp_critic.py
    - src/maxpat/critics/rnbo_critic.py
    - src/maxpat/critics/m4l_critic.py
    - src/maxpat/critics/__init__.py
decisions:
  - "OQ1-A (user): gen~ I/O check compares only the first codebox that appears in a patchline of its gen patcher; code_context fallback kept"
  - "OQ2-A (user): live.thisdevice not required for any M4L device type; instruments need only plugout~"
  - "OQ3-A (user): any top-level ezdac~ in a detected M4L device is a blocker"
metrics:
  duration: "~6 min"
  completed: 2026-10-12
  tasks: 2
  files: 5
actuals:
  tokens: 10200
  tasks: 2
  commits: 2
plan_head_before: 635883bc38943795556119581189bf6f297a6c6f
plan_head_after: d423bf48aeb5a6543632e3f26166d718cbc36772
---

# Phase quick-261012-egf Plan 01: Revive dead critic detectors and wire in the M4L critic (Q4) Summary

The gen~ I/O blocker and the RNBO critic now match boxes by name, so they fire on the `newobj` boxes MAX actually writes. mc.gen~ code is also read from `data.patcher`. `review_patch` now calls `review_m4l` whenever it finds plugin~, plugout~ or live.thisdevice. Required objects are reduced, gain~/live.gain~ is flagged on any signal path to plugout~, ezdac~ is flagged, and the `add_m4l_gen_synth` skeleton reviews with zero blockers.

## Commits

| Task | Commit | Message |
|------|--------|---------|
| 1 | 2cb8bf5 | fix(critics): detect gen~/mc.gen~/rnbo~ by box name and read mc.gen~ data.patcher, reviving the gen~ I/O and RNBO detectors (Q4 E3) |
| 2 | d423bf4 | fix(critics): wire review_m4l into review_patch; drop instrument midi and live.thisdevice requirements; flag gain~/live.gain~ on any signal path to plugout~ and ezdac~ in devices (Q4 D4) |

## Test totals

| Point | Result |
|-------|--------|
| Baseline (HEAD 635883b = base-sha.txt, stash empty) | 2475 passed, 1 xfailed, 1 xpassed |
| Task 1 RED (`tests/test_critic_revival.py`, 25 cases) | 13 failed, 12 passed. All 13 failed for the stated reasons: newobj/mc.gen~/add_gen/real-file mismatches gave `[]`, the unwired maxclass codebox was checked, and newobj rnbo~ was skipped by both gates |
| After Task 1 | 2500 passed, 1 xfailed, 1 xpassed |
| Task 2 RED (20 M4L cases) | 16 failed, 4 passed. The 4 passes are the planned anchors: None detection, plain-patch no-M4L, side branch, control cord. The module failed to import without `detect_m4l_device_type`, so the per-case counts come from a runtime stub injected from the scratch dir, with no repo change |
| After Task 2 (final) | 2520 passed, 1 xfailed, 1 xpassed. Fully green, passes up by exactly the 45 new tests |

Python 3.10 syntax gate (`ast.parse(..., feature_version=(3, 10))`) passed on all 5 changed .py files.

## Open questions

All three were answered by the user (2026-10-12) as option A. None was resolved by default.
- OQ1-A: compare only the first wired codebox, and fall back to `code_context` when there is none.
- OQ2-A: live.thisdevice is not required for any device type.
- OQ3-A: a top-level ezdac~ in a detected device is a blocker.

## Line references vs the spec (verified at base 635883b)

- gen~ maxclass gate: `dsp_critic.py:112`. The spec says 110.
- `_has_rnbo_boxes`: `critics/__init__.py:27-35`. The spec says 28-36.
- There was an extra, second gate at `rnbo_critic.py:57` (the review_rnbo loop). It is now `is_rnbo_box` too. Without that change, reviving `_has_rnbo_boxes` alone would have done nothing.

All observed_facts matched the live values. HEAD did not move during execution.

## Triage (rule 3): review_patch over every committed patch

| Metric | Before | After |
|--------|--------|-------|
| Files (`git ls-files patches`, .maxpat + .maxhelp) | 57 | 57 |
| Findings | 1350 | 1350 |
| Blockers | 1 (slot.maxpat, allowlisted) | 1 (same) |
| New / gone finding pairs | — | 0 / 0 |
| Top-level gen~/mc.gen~ boxes examined by the I/O check | 0 of 46 | 35 of 46 (11 reference external .gendsp / named gen and are skipped) |

No new findings, so nothing needed classifying. No committed patch (0 of 57) contains plugin~, plugout~, live.thisdevice or rnbo~, so neither the M4L nor the RNBO dispatch changes any corpus result. All 35 embedded gen~ codeboxes match their box I/O.

Extra check: MAX's bundled `help/msp/gen~.maxhelp` produces no gen~ I/O finding at any depth. The obj-29 unwired demonstration codebox is suppressed per OQ1-A.

## Historical evidence (kicksynth-m4l, via `git show` into scratch)

- **408cdf8:** detected as `instrument`. One blocker: `gain~ (obj-8) is on the signal path to plugout~ (obj-9)`. The old per-cord check gave 2 duplicates; now it is one finding per (stage, plugout~) pair.
- **494c2e6:** detected as `instrument`. 0 blockers. The only M4L finding is the live.banks warning.

## Deviations from Plan

None. The plan was executed as written.

Execution note: the commits landed on `main`, as the orchestrator directed (sequential execution on the main working tree, no worktree).

## Residuals (out of scope)

- A codebox fed by `param`/`history` inside the gen patcher is still compared against the gen~ box's inlets.
- Only one codebox (the first wired one) is compared per gen~.
- Code in external .gendsp files is not checked.
- send~/receive~ pairs are not followed when looking for paths to plugout~.
- mc.gain~ / mc.live.gain~ are not in `_M4L_GAIN_STAGE_NAMES`, and mc.plugout~/mc.plugin~ are not in the DB or the marker set.
- All critics still check the top level only.
- MAX-authored generator rnbo~ boxes now hit the E8 missing-in~ blocker that builder-made rnbo~ boxes already got (Q26).

## Hand-offs

- **Q15:** stereo plugout~ wiring in `add_m4l_gen_synth` (it still wires inlet 0 only), `_LIVE_NO_PARAM` / D5, ParamType/ModMode enums. `_LIVE_NO_PARAM` is unchanged and still importable by m4l_polish.
- **Q26:** E6 (plugout~ as a dsp_critic terminal, live.gain~ as a gain stage) and E8 (RNBO missing-in~ severity, positional `param` names, builder shape).
- **Q19/Q20:** recursion into subpatchers.
- **Q7:** the save gate will now see M4L and RNBO blockers.

## Doc impact (S7, not edited per rule 8)

- `TECHNICAL.md:504`: the gen~ I/O row now covers newobj gen~/mc.gen~, read from `patcher` or `data.patcher`, comparing the wired codebox.
- `TECHNICAL.md:554`: says "six" critics and that m4l_critic is not called. It is now called from review_patch.
- TECHNICAL.md has no M4L critic subsection.
- `.claude/skills/max-critic/SKILL.md:30-33`: add an M4L auto-invoke line (plugin~/plugout~/live.thisdevice).
- `.claude/skills/max-critic/references/critic-protocol.md:19`: same addition.

## Confirm in MAX / Live (rule 9)

Nothing to confirm, because no patch or builder changed. FYI:
- Any M4L device the critic reviews will now show polish warnings: openinpresentation, devicewidth, info text, live.banks.
- gain~/live.gain~ before plugout~, and any ezdac~ in a device, now block.

## Threat Flags

None. The changes are critic logic and tests only, with no new endpoints, file writes or trust-boundary surface.

## Self-Check: PASSED

- FOUND: tests/test_critic_revival.py, src/maxpat/critics/{dsp_critic,rnbo_critic,m4l_critic,__init__}.py
- FOUND commits: 2cb8bf5, d423bf4
- Final gate: GATES-OK-2-Q4-COMMITS-NO-PATCH-EDITS-STASH-UNCHANGED
