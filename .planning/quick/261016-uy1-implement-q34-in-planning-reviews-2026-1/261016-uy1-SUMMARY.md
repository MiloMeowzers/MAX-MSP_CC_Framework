---
phase: quick-261016-uy1
plan: 01
subsystem: tools / max-bridge
tags: [Q34, max-bridge, osc, udp, sfrecord~, dsp_sim, screencapture, spike]
status: complete
requires: [src/maxpat/dsp_sim/measure.py, src/maxpat/hooks.py, src/maxpat/project.py]
provides: [tools/max_bridge.py, patches/max-bridge/generated/max-bridge.maxpat, patches/max-bridge/fixtures/*]
affects: [.claude/max-objects/overrides.json (sfrecord~ inlet 1), .gitignore, README.md]
tech-stack:
  added: []
  patterns: [stdlib OSC codec over UDP, in-process FakeBridge test double, ephemeral gitignored temp copy]
key-files:
  created:
    - tools/max_bridge.py
    - tests/test_max_bridge.py
    - patches/max-bridge/generated/max-bridge.maxpat
    - patches/max-bridge/fixtures/fx-clean.maxpat
    - patches/max-bridge/fixtures/fx-dc.maxpat
    - patches/max-bridge/fixtures/fx-badargs.maxpat
    - patches/max-bridge/fixtures/fx-nosuchobj.maxpat
    - patches/max-bridge/fixtures/fx-genfail.maxpat
    - patches/max-bridge/test-results/v0.1.0-bridge-checklist.md
    - patches/max-bridge/open-questions.md
    - patches/max-bridge/context.md
    - patches/max-bridge/status.md
    - patches/max-bridge/versions.json
  modified:
    - .claude/max-objects/overrides.json
    - .gitignore
    - README.md
decisions:
  - "Temp copies are written with format_patch_text + atomic_write_bytes, not save_patch_roundtrip (research A6): ephemeral, gitignored (__maxbridge_*), deleted in a finally; the original is only read"
  - "check starts with a /ping (research Architecture step 2), so a missing bridge fails in --timeout seconds instead of --load-timeout"
  - "Fixture writers: fx-clean, fx-dc, fx-badargs via Writer A (save gate accepted all three); fx-nosuchobj and fx-genfail via Writer B (deliberate blockers)"
  - "Bridge patch hand-laid-out after finalize_patch(is_new=True): apply_layout stacked comments on boxes; stepped cord midpoints so no two cords share a segment"
metrics:
  duration: "~244 min wall (includes a network interruption)"
  completed: 2026-10-17
actuals:
  tokens: 38400
  tasks: 3
  commits: 12
plan_head_before: 6d1183019e8ada22818a2d921e741dfd6e77a39a
plan_head_after: 415f3127ee9dbe4ef4bdd100080871f35be58d17
---

# Quick 261016-uy1 (Q34): MAX bridge spike Summary

This spike adds a resident UDP/OSC bridge patch and a stdlib Python client, `tools/max_bridge.py` (`ping`, `check`, `analyze`). `check` does the following, in order:
1. writes an instrumented sibling copy of the patch, with `send~` taps on the dac~ inputs and a cordless close hook;
2. opens the copy in MAX behind a `/ping` load barrier;
3. collects the `error` and `console` streams and a `console write` diff;
4. records the taps with `sfrecord~` in float32 and analyzes the wav with the dsp_sim measures;
5. screenshots the window by its id;
6. closes the window and deletes the copy.

It prints one JSON report and exits 0 clean / 1 findings / 2 bridge failure. Everything that does not need MAX is covered by hermetic tests that run against an in-process fake bridge. MAX behaviour itself is **untested until the user runs the checklist**.

## What was built

| Task | Commits | Result |
|---|---|---|
| 1 (tracer) | 37b8dc56, 9f1c9d26, 59c39298, ecc645a6, c614d740 | The `sfrecord~` inlet-1 override is now a signal inlet, with the `_audit` source extended to cite the Q34 refpage. The bridge patch is v0.1.0 with 0 validation errors and 0 review findings. The OSC codec, `Bridge` client and `ping` CLI are done, and the README row is added. |
| 2 | 92210031 | `instrument()`, `analyze()`, `shoot()` / `wait_gone()` (ported from MUSC320 `patch_shot.py` @ 1009e5c, without the keystroke or AX close), `plan_messages()` / `run_check()`, the `check`/`analyze` CLI, and `.gitignore` `__maxbridge_*`. |
| 3 | 74723eb6, d869e1fa, 339f438f, cadfae1d, 11d0202a, 415f3127 | The five fixtures, the checklist (setup plus 9 steps), `open-questions.md` (Q1-10, A1-A6, N1-N5, each tied to a checklist step), the context.md fixture table, and TestFixtures. |

Tracer gate: Task 1's `<verify>` was re-run end-to-end and passed (113 passed; `ping` against an empty port returned exit 2 with the port and the bridge path in the message) before Task 2 started.

## Test results vs baseline

- **Baseline** (6d118301): 2 failed, 5318 passed, 5 xfailed, 1 xpassed.
- **Final** (415f3127): 2 failed, 5415 passed, 5 xfailed, 1 xpassed.
  - The same 2 pre-existing failures: `test_readme_patch_table_lists_every_project` (the message is still exactly `missing: ['q29-check']; extra: []`) and the q29-check Q24 allowlist case.
- `junit_diff.py` exits 0: base=5326, new=5423, added=97, offenders=0. The additions are 82 tests in `tests.test_max_bridge`, plus corpus cases whose ids name `patches/max-bridge/`. All pass, none were removed, and nothing regressed.
- `git stash list` is unchanged.
- `.claude/commands` and `.claude/skills` are unchanged, so there is no `/max-verify` integration.
- No `__maxbridge_*` file is left on disk.
- Every changed path is in the plan's `files_modified`.

## Deviations from Plan

### Auto-fixed / adjusted

1. **[Rule 1 - layout] Bridge patch hand-laid-out.** `finalize_patch(is_new=True)` → `apply_layout` placed the header comments on top of the `/pong` row and the close/listen comments on top of `console`, `t` and `sfrecord~`. After finalize, the boxes were placed by hand:
   - the boxes follow the route outlet order;
   - the receive~ taps and `loadmess` sit beside their branch cords;
   - the streams converge on a single `udpsend`;
   - cords got stepped midpoints so no two run along the same segment.

   The result has 0 rendered overlaps (checked with `rendered_rect`), and validate/review are still clean. It is saved as the second commit, 59c39298. Its SaveGateWarning listing 25 "removed" cords only reflects the renumbered ids: the box and cord counts are identical (38/35).
2. **[Rule 2] `check` starts with `/ping`.** Without it, a closed bridge would wait the full `--load-timeout` (30 s). It matches research Architecture step 2, and `plan_messages()` includes it, so the order test holds.
3. **[Rule 2] Best-effort cleanup on a bridge failure.** On a failure mid-run, `check` sends `/listen 0`, `/dsp 0` (if it turned DSP on) and `/close`/`/closefile` (if it opened the copy) without waiting for replies, then exits 2.
4. **[Rule 2] `guard_input` also refuses an input that is itself a `__maxbridge_*` copy.**
5. **Minor:** `--dry-run` removes its empty run dir; the `check` subcommand also takes `--timeout` for the non-load `/ping`s.

### Decisions recorded

- **Research A6:** `instrument()` writes the sibling copy with `format_patch_text` + `atomic_write_bytes`, never `save_patch_roundtrip`. The copy is ephemeral, gitignored and deleted in a `finally`.
- **Fixture writer split:** Writer A (`save_patch_roundtrip`) handled `fx-clean`, `fx-dc` and `fx-badargs`; the save gate accepted all three, so none moved to Writer B. Writer B (`format_patch_text` → `atomic_write_bytes` → `auto_commit_patch`) handled `fx-nosuchobj` (the `osc~` Pure Data name) and `fx-genfail` (`validate_genexpr` blocks the Param assignment). No allowlist entries were added.

## Known Stubs

None. The open spike questions are tracked in `patches/max-bridge/open-questions.md`, not as code stubs.

## Threat Flags

None beyond the plan's threat model. The LAN exposure (T-uy1-01) is documented in the bridge header comment, context.md and checklist step 1, and N1 asks the user to decide on a host filter or kill switch.

## Next step (user)

Open `patches/max-bridge/generated/max-bridge.maxpat` in MAX 9.2 and work through `patches/max-bridge/test-results/v0.1.0-bridge-checklist.md`, filling the "Answer:" lines in `patches/max-bridge/open-questions.md`. Do not add any `/max-verify --live` integration until the user confirms the bridge works.

## Self-Check: PASSED

- FOUND: tools/max_bridge.py, tests/test_max_bridge.py, patches/max-bridge/generated/max-bridge.maxpat, the 5 fixtures, the checklist, open-questions.md
- FOUND commits: 37b8dc56 9f1c9d26 59c39298 ecc645a6 c614d740 92210031 74723eb6 d869e1fa 339f438f cadfae1d 11d0202a 415f3127 (12 = `git rev-list --count 6d118301..HEAD`)
