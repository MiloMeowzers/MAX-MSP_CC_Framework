---
phase: quick-261015-j0n
plan: 01
status: complete
subsystem: critics
tags: [critics, structure-critic, graph, save-gate, Q24, R8]
requires: [Q20 shared PatchGraph, Q21 structure_critic _LazyDB, Q7 save gate]
provides:
  - PatchGraph.control_walk (control-cord BFS with port crossing and s/r, value, pv, ; bridges)
  - structure_critic._check_uninitialized_state (check 7)
  - review_structure / review_patch keyword-only is_new
  - save gate reviews a no-baseline file with is_new=True
affects: [src/maxpat/graph.py, src/maxpat/critics/structure_critic.py, src/maxpat/critics/__init__.py, src/maxpat/hooks.py]
tech-stack:
  added: []
  patterns: [additive graph traversal, lazily computed per-call context, caller-chosen severity via is_new]
key-files:
  created:
    - tests/test_uninitialized_state.py
    - tests/uninitialized_state_allowlist.json
  modified:
    - src/maxpat/graph.py
    - src/maxpat/critics/structure_critic.py
    - src/maxpat/critics/__init__.py
    - src/maxpat/hooks.py
decisions:
  - "Q24 check lives in structure_critic (check 7) over a new additive PatchGraph.control_walk; no second graph build"
  - "Severity is caller-chosen: review_structure/review_patch(is_new=False) default warning; the save gate passes is_new=True only for a file with no baseline"
  - "Init routes: parameter initial value, pattr cord/@bindto, autopattr+pattrstorage, autopattr restore dict (unless @autorestore 0), slaved gain~ (DB outlet flag), upstream load source, follower"
  - "dac~/ezdac~/mc.dac~/ezadc~ are never DSP targets; adc~ is"
  - "mixer-strip's 16 host-restored controls are reported per literal D-02 and allowlisted (user decision flagged)"
metrics:
  duration: 14m
  completed: 2026-10-15
estimate:
  tokens: 130000
  tasks: 3
actuals:
  tokens: 30400
  tasks: 3
  commits: 3
plan_head_before: 4b2890b89ceaf18e008df0202e9c700801f8aee8
plan_head_after: 4e8fdb3501f0d2c893d6daa8ddea942bd86993dc
---

# Quick 261015-j0n Plan 01: Q24 uninitialized UI -> DSP state check Summary

The structure critic now reports any UI value holder whose control output reaches DSP when nothing sets it at load. On an edit this is a warning. For a new file it is a blocker, so the save gate refuses the save. All 78 committed findings are pinned in an allowlist, each with a reason.

## What was built

- **`PatchGraph.control_walk(scope, box_id, *, downstream, max_depth=64)`** (graph.py, additive): a breadth-first walk over control cords only. Cords where `Edge.signal` is set are never followed. It crosses `p` and embedded bpatcher containers at the exact port, and the containers and port boxes are traversed but never yielded. It bridges `send`/`s` to `receive`/`r`, `value`/`v`, `pv` (same, ancestor or descendant scope) and `;` remote-message segments. Each cord or bridge hop adds 1 to the depth, and a node at `max_depth` is yielded but not expanded. A visited set makes it cycle-safe. The bridge map is built lazily into a new `__slots__` entry, `_control_bridges`. The private `_message_remote_targets` parses `;` targets. `_traverse`, `downstream`, `upstream`, `_channel_maps` and `_bridged` are untouched.
- **`_check_uninitialized_state`** (structure_critic.py, check 7): runs on every non-gen, non-rnbo scope, after `_check_trigger_order`.
  - gain~ and live.gain~ always reach DSP and get the gain-stage text.
  - The other D-01 holders are reported only when the downstream walk reaches a DSP box. The finding names the first DSP box reached.
  - Init routes are checked cheapest first: parameter initial value, then D-02 pattr binding (a pattr cord, `@bindto`, or autopattr in the same patcher plus a pattrstorage anywhere), then the autopattr `restore` dict, then a slaved gain~, then one upstream walk that accepts a load source or a follower.
  - `_InitContext` computes whole-graph facts lazily, once per call: whether a pattrstorage exists, the `@bindto` names, and the autopattr boxes per scope.
- **`is_new` plumbing**:
  - `review_structure(..., *, is_new=False)` and `review_patch(..., *, db=None, is_new=False)`.
  - `hooks._blocking_findings(..., *, is_new=False)`.
  - `_gate_report` reviews the new dict with `is_new=baseline_dict is None` and the baseline with the default.

## Locked decisions (as implemented)

- **D-01:** `_VALUE_HOLDERS` (14 classes) plus `_GAIN_STAGES` (gain~, live.gain~), matched by maxclass. button, kslider, multislider, textedit, nodes, matrixctrl, mc.live.gain~ and comment are tested as never reported.
- **D-02:** binding is checked per control. The test `test_unbound_control_in_pattr_patch_still_reported` confirms an unbound control in a pattr patch is still reported. Autopattr counts only in the control's own scope and only with a pattrstorage somewhere in the tree.
- **D-03:** reach uses the full control graph: cords, port-exact crossing, s/r, value, pv and `;` segments. It is bounded at depth 64 (a chain of 63 `t i` is found, 64 is not) and is cycle-safe (tested with a `t i` / `+ 0` loop, with and without gen~).
- **Severity:** a warning by default and a blocker with `is_new=True`. The four latent cases are warnings on the committed files.

## Planner decisions (as implemented)

1. **Placement:** structure_critic plus a public `PatchGraph.control_walk`. The critic uses the shared graph, and `TestReviewPatchSharedGraph` stays green.
2. **is_new:** keyword-only, default False. Only the save gate sets it, for a file with no baseline. `test_severity_split_is_only_is_new` holds.
3. **Init routes:**
   - Parameter initial value: `parameter_enable == 1` and `valueof.parameter_initial_enable == 1` with a `parameter_initial` key.
   - Load sources: loadbang, loadmess and live.thisdevice.
   - Autopattr `restore` dict, unless the box text carries `@autorestore 0`.
   - Slaved gain~: decided by the DB outlet `signal` flag, so a master saved with outlettype `["signal","signal"]` still counts (tested).
   - Follower: an upstream value holder that is not in the control's own downstream set (tested both ways, including a mutual pair, which gives 2 findings).
4. **Reach:** signal cords are never followed. gain~ and live.gain~ always count as DSP. dac~, ezdac~, mc.dac~ and ezadc~ are never targets; adc~ is. The DSP test is, in order: DSP name, then a signal outlettype, then a DB signal inlet or outlet.
5. **mixer-strip is reported** (16 HOST entries). This needs your decision; see below.
6. **Depth 64.** The bundle sweep (`requires_max`) ran inside the full suite and passed. The full suite took 84.6 s, against 84.1 s at baseline.
7. **Finding text** matches `<reference_data>` exactly (tested) and always starts with `Uninitialized state: `.

## Committed corpus (78 warnings, 25 files, all at path "")

The live run matched the planning expectation exactly: no missing, extra, maxclass or severity differences. There were therefore no verdicts to record and no checker fixes in Task 3.

| File | Entries | Category |
|---|---|---|
| barnett-dbap/barnett-dbap.maxpat | obj-13 number | PARAM |
| barnett-dbap/control-demo.maxpat | obj-39 slider, obj-41 flonum | PARAM |
| barnett-dbap/dbap-source.maxpat | obj-13, obj-15 toggle; obj-20 number | TOGGLE; PARAM |
| disintegrate/disintegrate-helper.maxpat | obj-8 flonum; **obj-10 gain~** | PARAM; LATENT |
| FDNVerb/FDNVerb.maxhelp | obj-8 toggle; **obj-29 gain~** | TOGGLE; LATENT |
| gen-eq/gen-eq-mc-test.maxpat | obj-8 toggle | TOGGLE |
| gen-eq/gen-eq-test.maxpat | obj-8 toggle | TOGGLE |
| gong-model/gong-model.maxpat | obj-407 flonum (cold inlet of `f 0.8`) | PARAM |
| granularsynthtest/granularsynthtest.maxpat | **obj-26 gain~** | LATENT |
| intelligent-corpus-remixer/intelligent-corpus-remixer.maxpat | obj-11, obj-13, obj-50 toggle; obj-17 number; obj-20 live.gain~ | TOGGLE; PARAM; LIVEGAIN |
| looper/looper-demo.maxpat | obj-7 toggle | TOGGLE |
| mixer/mixer-strip.maxpat | obj-57, 58, 80, 85, 90, 95, 100, 105 dial; obj-72, 76, 81, 86, 91, 96, 101, 106 umenu | HOST |
| physics-composition/physics-composition.maxpat | obj-22 toggle | TOGGLE |
| reverse-delay/reverse-delay-mono.maxpat | obj-138 toggle; obj-140 flonum | TOGGLE; PARAM |
| reverse-delay/reverse-delay.maxpat | obj-138 toggle; obj-140 flonum | TOGGLE; PARAM |
| rhythmic-corpus-chopper/rhythmic-corpus-chopper.maxpat | obj-8, obj-10 toggle | TOGGLE |
| rhythmic-sampler/slot.maxpat | obj-48, obj-138 dial | PARAM |
| sample-layers/sample-layers.maxpat | obj-8 toggle | TOGGLE |
| simple-fm/simple-fm.maxpat | obj-76 umenu | PARAM |
| spectraldetector/spectraldetector.maxpat | obj-3 umenu; **obj-8 gain~** | PARAM; LATENT |
| stereo-feedback-delay/stereo-feedback-delay.maxpat | obj-8, 13, 18, 23, 28, 33, 38, 43 dial | PRESET |
| stutter/stutter.maxpat | obj-21, obj-28, obj-42 toggle; obj-44, obj-47 dial | TOGGLE; PARAM |
| tape-wobble/tape-wobble.maxpat | obj-10, 12, 15, 17, 20, 22, 25, 27, 29, 32, 34 dial | PARAM |
| terrain-synth/terrain-synth.maxpat | obj-759, obj-784, obj-835 toggle | TOGGLE |
| timestretch/timestretch.maxpat | obj-48, obj-49 toggle | TOGGLE |

Totals: LATENT 4, LIVEGAIN 1, TOGGLE 23, PRESET 8, HOST 16, PARAM 26. The four spec latent cases (in bold) are warnings, and `test_spec_latent_cases_are_warnings` pins them. Task 2's pattr routes cleared bassoon-model's live.gain~ obj-9 (autopattr plus pattrstorage), as the plan expected. Triage after every task showed `mismatch=0 q24_blockers=0`, so every non-Q24 review record is unchanged from the Step-0 snapshot.

## For a user decision: mixer-strip (planner decision 5)

Under the literal D-02 rule, an abstraction whose state its host's pattrstorage restores is reported. mixer-strip's 16 named controls sit under `autopattr @autorestore 0` with no pattrstorage in the file. The host, mixer.maxpat, recalls them through its `mixstate` pattrstorage, but a per-file review cannot see that. The committed file only gets warnings. However, a NEW abstraction file with this shape is refused by the save gate. Options:

- **A. Keep it (literal D-02, current behaviour).** New host-restored abstractions need an explicit init route, or a forced save once confirmed.
- **B. Exempt it.** Treat varnamed controls under autopattr as initialized in a file whose top level has inlet/outlet boxes (an abstraction), even when there is no pattrstorage.

## Known false negatives

- `loadmess set N` counts as initialized: the path exists even though `set` does not output.
- A umenu filled by a loadbang `append` chain counts as initialized.
- `pattrforward` and a js `loadbang()` are not recognized as load sources.
- pv bridging is approximated by scope ancestry (same, ancestor or descendant patcher).

## Doc impact (no docs edited, rule 8)

- `.claude/skills/references/severity-contract.md` §1: the `review_patch` signature lacks `is_new`. §5: a Q24 finding blocks only a new file.
- max-critic SKILL.md: the /max-build loop should call `review_patch(..., is_new=True)` so the generator sees Q24 before the save gate does (threat T-j0n-04).
- CLAUDE.md MSP section: gain~ init (and UI init in general) is now enforced for new patches.
- The Q23 plan's `walk.message_remote_targets` could later replace graph.py's private `_message_remote_targets`.
- TECHNICAL.md has no new critic module; `test_technical_documents_every_critic_module` stays green.

## Nothing to confirm in MAX

The check is static. The autopattr autorestore semantics come from autopattr.maxref.xml (autorestore defaults to 1 and outputs the last-saved values at load).

## Deviations from Plan

- **Task 2 did not modify graph.py.** Task 1 implemented the whole `control_walk` contract (all bridges, the `;` parser and depth semantics), so there was nothing left for Task 2 to add. The Task 2 commit carries only structure_critic.py and the test file. The `TestControlWalkDownstream` tests were already green at the Task 2 red run, which still showed 36 failures elsewhere.
- **Downstream walk tests are in a new class, `TestControlWalkDownstream`,** next to `TestControlWalkUpstream`, rather than in that one class.
- **Separate shell commands for the plan's `<automated>` verify one-liners.** This worktree's sandbox refuses compound commands that mix git with computed variables, so each verify was run as separate equivalent commands. Every check passed: the test files, the git status comparison, the red-file grep, triage `--selftest` and `--check`, the greps, the 3.10 AST parse, an unchanged stash list, 3 `(Q24)` commits, and no `patches/` path in the commit file list.

No other deviations; no auth gates.

## Verification

- `tests/test_uninitialized_state.py`: 176 passed.
- Full suite (Q/final-pytest.txt): **4478 passed, 1 xfailed, 1 xpassed, 29 warnings in 84.57s**. The baseline was 4302 passed, 1 xfailed, 1 xpassed; the difference is the 176 new tests. test_calibration_zero_blockers and the bundle sweep are green with no allowlist change.
- Triage: `files=69 mismatch=0 q24=78 q24_blockers=0` (Q/triage-final.json).

## Commits

- 117fab92 feat(critics): uninitialized-state check for gain stages with new-vs-edit severity through the save gate (Q24)
- 99494a02 feat(critics): uninitialized-state check covers every value holder and init route (Q24)
- 4e8fdb35 test(critics): pin uninitialized-state warnings on committed patches (Q24)

## Self-Check: PASSED

- FOUND: src/maxpat/graph.py (def control_walk), src/maxpat/critics/structure_critic.py (_check_uninitialized_state), src/maxpat/critics/__init__.py (is_new=is_new), src/maxpat/hooks.py (is_new=baseline_dict is None), tests/test_uninitialized_state.py, tests/uninitialized_state_allowlist.json
- FOUND commits: 117fab92, 99494a02, 4e8fdb35
