---
quick_id: 261022-ud6
status: complete
date: 2026-10-23
---

# 261022-ud6: Q1–Q40 review, fix everything, prepare v6.0.0

## Review
7 parallel reviewers over `0f96a6f1..8ddcdc49` → 11 blockers + Python 3.10 `math.exp2` break, ~35 warnings, info items, Q23 never executed. Consolidated in `261022-ud6-REVIEW.md`; detail in `review-*.md`.

## Fixes (all merged to main)
| WP | Area | Summary file |
|----|------|--------------|
| WP1 | validation + object DB (signal inlets, merger, malformed ports, structured rule ids) | wp1-SUMMARY.md |
| WP2 | patcher/save (replace_box keeps embedded patcher + id, byte-identical no-op saves all Max versions, gate structured keys, B11 contrast) | wp2-SUMMARY.md |
| WP3 | critics (gain-stage, hot/cold reconvergence, gen~ I/O, is_new in build loop) | wp3-SUMMARY.md |
| WP4 | codegen/M4L/RNBO (no doubled pass-through, diagnose causes, gen order, constants, rnbo~ shape, tabs rule) | wp4-SUMMARY.md |
| WP5 | dsp_sim (graph-inferred audio/control outputs, pitch detector, exp2, exit codes) | wp5-SUMMARY.md |
| WP6 | tools + release (bridge → tools/max_bridge, OIDC trusted publishing, publish-before-release, vermin 3.10 floor) | wp6-SUMMARY.md |
| WP7a | cross-WP handoffs | wp7a-SUMMARY.md |
| WP7b | Q23 vocabulary checks | wp7b-Q23-SUMMARY.md |
| WP8 | docs, CHANGELOG v6.0.0, release body wiring, STATE | wp8-SUMMARY.md |

Locked decisions: see `261022-ud6-PLAN.md`.

## Verification
- Full suite 7504 passed / 1 skipped / 4 xfailed / 0 xpassed (Python 3.14); identical on Python 3.10.19 (the one earlier 3.10 failure was disk-full ENOSPC, cleared).
- vermin: minimum 3.10. Release tarball builds; contains `tools/max_bridge/max-bridge.maxpat` and CHANGELOG; `release_notes.sh v6.0.0` extracts the section.
- No committed `patches/**` file content changed (bridge patch moved with git mv, 100% similarity).

## Pending user actions
- npmjs.com → create-max-framework → Trusted Publisher: owner `taylorbrook`, repo `MAX-MSP_CC_Framework`, workflow `release.yml`, environment blank. Then the `NPM_TOKEN` secret can be deleted.
- Push main + tag `v6.0.0`.

## Needs confirmation in MAX / Live
- Legacy (Max 8 / 9.0.x) patch edited via the legacy writer loads and re-saves normally.
- `gen~` → `mc.gen~` via replace_box_safe compiles with multichannel outlet; textbutton relabel keeps size.
- Theme fills: number/flonum 0.125, textbutton 0.262; reson~ inlet 1 is input gain; 0-input codebox with 1 inlet compiles.
- Gen: functions-before-declarations order compiles, function after a statement fails; stutter limiter `hoist_alias` shape compiles on current build.
- `rnbo~` box shape + positional `param` load; event-only rnbo~ (MIDI out, no out~) exports.
- M4L: two-call `add_m4l_device` → one pass-through, info text shown (plus the open Q15/Q40 Live check).
- bach `@out` with fewer letters than outlets repeats last letter; `@out m`/`x` readable by plain Max.
- DB inlet changes: `cycle~` → `live.remote~` 0, audio → `jit.vcr` 1, signal → `pitchshift~ 2` factor inlet, argless `sfrecord~` has 1 inlet.
- `line~`: `0, 1 500` jumps then ramps; `1 10, 0 500` plays only the last ramp.
