---
phase: quick-261021-olv
plan: 01
status: complete
subsystem: tools/max-bridge, /max-verify
tags: [q34, max-bridge, max-verify, live-check, severity-contract]
requires: [max-bridge v0.2.0 (dc0cde91, confirmed in MAX 9.2)]
provides:
  - tools/max_verify_live.py (/max-verify --live orchestrator)
  - tools/max_bridge.py check --dsp-on-load
  - severity-contract.md section 7 (live findings)
  - max-bridge v0.3.0 records + manual checklist
affects: [.claude/commands/max-verify.md, .claude/skills/references/severity-contract.md, patches/max-bridge]
tech-stack:
  added: []
  patterns:
    - "wrapper reuses bridge._instrument_patcher/_inject_note on an in-memory Patcher for option choice"
    - "severity from map_findings, never from bridge exit_code/verdict"
    - "sibling-reference top-level selection (bpatcher name, newobj abstraction, poly~/mc.poly~/pfft~ arg)"
key-files:
  created:
    - tools/max_verify_live.py
    - tests/test_max_verify_live.py
    - patches/max-bridge/test-results/v0.3.0-verify-live-checklist.md
  modified:
    - tools/max_bridge.py
    - tests/test_max_bridge.py
    - .claude/commands/max-verify.md
    - .claude/skills/references/severity-contract.md
    - patches/max-bridge/context.md
    - patches/max-bridge/status.md
    - patches/max-bridge/versions.json
decisions:
  - "D-01..D-04 implemented as locked; --dsp-on-load is the only bridge logic change (opt-in, /dsp 1 at index(opener)-1)"
  - "Checklist step 5 uses amplitude-follower for the D-01 load-only case and gen-eq-test for the --live-inputs record case (amplitude-follower's output is not tapped, so it can never record)"
  - "An aborting patch gets status failed; later patches stay 'not checked'"
metrics:
  duration: ~16 min
  completed: 2026-10-21
estimate:
  tokens: 170000
  tasks: 3
actuals:
  tokens: 25700
  tasks: 3
  commits: 4
plan_head_before: 183b2add4936dc70368b393d3249e0dfa6a41a1a
plan_head_after: 6ca62463edf39eb3dfd7a5d2c7de1479458d5f7a
---

# Phase quick-261021-olv Plan 01: /max-verify --live via max-bridge Summary

`/max-verify --live` now loads each top-level patch of the active project in the running MAX 9.2 through the max-bridge and reports MAX's console errors, record flags and screenshots as report-only live findings (severity-contract §7). The bridge gains a single opt-in change, `check --dsp-on-load`, which turns DSP on just before `/open` so that gen~ compile errors post while the patch loads.

## Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (tracer) | max_verify_live tracer + check --dsp-on-load | 9adeb6de | tools/max_bridge.py, tests/test_max_bridge.py, tools/max_verify_live.py, tests/test_max_verify_live.py |
| 2 (RED) | project mode / selection / open-original / report tests | 1c709c2c | tests/test_max_verify_live.py |
| 2 (GREEN) | project mode, top-level selection, report; max-bridge v0.3.0 | b9097072 | tools/max_verify_live.py, tests/test_max_verify_live.py, patches/max-bridge/{context,status}.md, versions.json |
| 3 | max-verify.md --live, severity-contract §7, v0.3.0 checklist, doc guards | 6ca62463 | .claude/commands/max-verify.md, .claude/skills/references/severity-contract.md, patches/max-bridge/test-results/v0.3.0-verify-live-checklist.md, tests/test_max_verify_live.py |

## What was built

- **Bridge (D-02):**
  - `--dsp-on-load` appends `("/dsp", (1,))` after `/listen 1` and immediately before the opener, in both pcontrol and openfile modes. It is never placed between the opener and its load `/ping`.
  - The restore slot and the BridgeError cleanup are unchanged and already cover this DSP switch.
  - Without the flag, the plan is byte-for-byte what it was.
  - The docstring status text and usage line are updated.
- **Wrapper (`tools/max_verify_live.py`):**
  - `scan_patch` takes its tap and note decision from the bridge's own logic. Its audio-input scan is wider: any depth, plus referenced siblings followed transitively.
  - `check_argv` applies the D-01/D-02 rules.
  - `preflight` is read-only: a bridge-patch-present check, `pgrep -x Max`, and `Bridge.ping`.
  - `map_findings` implements the §7 table.
  - `run_live` runs strictly sequentially and handles every outcome: skip, abort on the first bridge_failed, crash (becomes a warning), refused, and open-original (skipped).
  - `find_top_level_patches`, project resolution, `format_report` and the JSON or human CLI are all in place.
- **D-04:** an AST guard pins that the wrapper contains no `.send` call and none of the `open` / `osascript` / `/dsp` / `/listen` constants.
- **Docs:**
  - max-verify.md gets step 7, a safety list, the flags and examples, and a live output block with the beside-not-merged Summary suffix.
  - severity-contract.md gets §7.
  - context.md gets a `/max-verify --live` section and the new exit codes.
  - max-bridge is now at 0.3.0.

## Verification

- `tests/test_max_bridge.py`: 133 passed. That is the 124 pre-existing tests, unedited (the diff is +82/-0), plus 9 new TestDspOnLoad tests.
- `tests/test_max_verify_live.py`: 81 passed, all hermetic. Every run uses an explicit `--port` (a FakeBridge port or a free port) and `--reply-port 0`.
- Full suite: 2 failed, 5547 passed, 5 xfailed, 1 xpassed. The baseline was 2 failed, 5457 passed, and the same 2 failures are pre-existing (`test_readme_patch_table_lists_every_project`, `test_committed_q24_findings_match_allowlist[q29-check]`).
- `junit_diff.py baseline final`: base=5465 new=5555 added=90 offenders=0, exit 0.
- The dry run with `--dsp-on-load` shows `/dsp 1` on the line right before `/open`, and the flagless dry run has no `/dsp 1`.
- `max_verify_live.py --project simple-fm --port 7409` reports "Live check skipped" with exit 2.
- terrain-synth resolves to `[terrain-synth.maxpat]`, with its 5 children excluded.
- No `__maxbridge_*` file is left under patches/. The stash list is unchanged (empty). `patches/.active-project.json` is unchanged. `max-bridge.maxpat` is unchanged. simple-fm and terrain-synth are untouched.
- Nothing contacted 127.0.0.1:7400. The only real-socket probes went to 7409 or to a free port.

## Deviations from Plan

**1. [Rule 1 - Bug in plan text] Checklist step 5's `--live-inputs` record case uses gen-eq-test, not amplitude-follower**
- **Found during:** Task 3
- **Issue:** amplitude-follower has `adc~` (inputs True, obj-2) but no tapped `dac~` cord. With `--live-inputs` it would be load-only with DSP-on-load, never "recorded" as the plan expected.
- **Fix:** step 5 still names amplitude-follower for the D-01 load-only / DSP-untouched check. It uses `patches/gen-eq/generated/gen-eq-test.maxpat`, which has `adc~` and a tapped output, for the `--live-inputs` → record check.
- **Commit:** 6ca62463

**2. [Rule 3 - Blocking] junit_diff.py source copied from the main checkout**
- The plan's Step 0 source `.planning/quick/261016-uy1-.../junit_diff.py` is untracked, so it was absent from the worktree. It was copied read-only from /Users/taylorbrook/Dev/MAX, and only the local copy was extended (the `tests.test_max_verify_live` prefix counts as ours).

**3. Additions beyond the plan's test list (hermetic):**
- an unknown MAX state (`_max_running` None) still pings;
- refused input;
- several parents plus an unreadable sibling;
- missing project dir;
- the active-project pointer path;
- a reference cycle ("every file referenced");
- the window-list ShotError note;
- `WORDING_SUGGESTIONS` covers every `ERROR_WORDINGS` entry.

## Known Stubs

None.

## Threat Flags

None. No new network address or command was added. The wrapper reaches MAX only through `run_check` and a `/ping`.

## Untracked artifacts left (not committed, per instructions)

- QDIR: 261021-olv-PLAN.md, 261021-olv-SUMMARY.md, base-sha.txt, stash-list-before.txt, active-project-before.json, junit_diff.py, baseline-junit.xml, final-junit.xml
- patches/.active-project.json (a gitignored copy from the main checkout, used by Step 0/Task 2 verify)

## Self-Check: PASSED

- FOUND: tools/max_verify_live.py, tests/test_max_verify_live.py, patches/max-bridge/test-results/v0.3.0-verify-live-checklist.md
- FOUND commits: 9adeb6de, 1c709c2c, b9097072, 6ca62463
