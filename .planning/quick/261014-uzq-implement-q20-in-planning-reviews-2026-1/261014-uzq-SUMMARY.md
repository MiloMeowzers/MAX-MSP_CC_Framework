---
phase: quick-261014-uzq
plan: 01
subsystem: critics, graph, analysis, testing
tags: [Q20, A7, G9, G10, S1, recursive-critics, shared-graph]
status: complete
requires: [Q19 walk.iter_patchers, Q19 path-aware save-gate key]
provides:
  - graph.PatchGraph / Scope / Edge / outlet_is_signal / resolve_patcher
  - CriticResult.path + critics.base.tag_results
  - every patch critic reviews every scope on one shared graph
  - port-exact, s/r-bridged, outlettype-signal traversal (GraphMixin on PatchGraph)
  - recursive analyze() and object-only recursive test checklist
affects: [save gate (hooks._finding_key), review allowlist key, /max-verify, /max-test, Patcher.analyze]
tech-stack:
  added: []
  patterns: [one read-only PatchGraph per review_patch call, per-scope checks + tag_results]
key-files:
  created:
    - tests/test_critics_recursive.py
  modified:
    - src/maxpat/graph.py
    - src/maxpat/critics/base.py
    - src/maxpat/critics/__init__.py
    - src/maxpat/critics/structure_critic.py
    - src/maxpat/critics/dsp_critic.py
    - src/maxpat/critics/package_critic.py
    - src/maxpat/critics/rnbo_critic.py
    - src/maxpat/critics/m4l_critic.py
    - src/maxpat/critics/layout_critic.py
    - src/maxpat/analysis.py
    - src/maxpat/testing.py
    - src/maxpat/hooks.py
    - src/maxpat/walk.py
    - tests/test_integration_patches.py
    - tests/test_graph.py
    - tests/test_analysis.py
    - tests/test_testing.py
decisions:
  - "Q20: CriticResult gains a path slot; nested critic findings are tagged like Q19 ValidationResult (path = box-id chain, [label > label] prefix); top-level findings byte-identical"
  - "Q20: review_patch builds one PatchGraph and at most one ObjectDatabase per call and passes graph= to every critic"
  - "Q20: gen scopes skip message-ordering rules (structure runs only duplicate patchlines; dsp/package/m4l per-scope skip gen); D1 drops 5 top-level .gendsp hot/cold warnings"
  - "Q20: a setter message box (every comma segment starts with a symbol selector) cabled into a jit.* object ends a fan-out reconvergence path"
  - "Q20: dsp critic keeps its own outlettype-only signal reads (not edge.signal) - the three read sites are pinned by tests/test_signal_role_migration.py"
  - "Q20: analyze() Signal Flow roots include signal-emitting p/bpatcher sources, so outlettype-based adjacency never loses a chain"
metrics:
  duration: ~28 min
  completed: 2026-10-15
actuals:
  tokens: 52000
  tasks: 3
  commits: 4
plan_head_before: ad3213e4e42df7ef96660aad4bbfb40fcd5dba19
plan_head_after: f3bfdce329d83e4a1405e304fdfa9dc6db32757e
---

# Quick 261014-uzq Plan 01: Recursive critics, shared PatchGraph, G9 traversal, recursive analyze/checklist (Q20) Summary

Every critic now reviews every subpatcher scope from one shared dict-level `PatchGraph`, with findings tagged by path. Graph traversal crosses `p` boxes port by port, bridges send/receive, and decides signal by outlettype. `analyze()` and the /max-test checklist now cover the whole patch. Nothing under `patches/` changed.

## Figures

- **Base suite** (Q/baseline-pytest.txt, at ad3213e4): 3813 passed, 1 xfailed, 1 xpassed.
- **Final suite** (Q/final-pytest.txt): 3909 passed, 1 xfailed, 1 xpassed. That is +96 new tests, all green.
- **New tests per file:**
  - tests/test_critics_recursive.py: 74 (new file)
  - tests/test_graph.py: +10 (18 to 28), plus 1 renamed and inverted
  - tests/test_analysis.py: +3
  - tests/test_testing.py: +8
  - tests/test_integration_patches.py: +1
- **Bundle sweep** (`TestBundleSweep::test_bundle_sweep_never_raises`, requires_max): it ran on this Mac (Max 9.2.0) and passed in about 5 s. `review_patch`, `generate_test_checklist`, `PatchGraph.build`, and downstream (both modes) and upstream never raise on any bundle .maxpat/.maxhelp. At base the checklist raised IndexError on `liveui.map.maxpat`.
- **Triage** (Q/triage-final.json): files=69, top_mismatch=0, gen_dropped=5, nested_bad=0, nested=1514. The same figures appear in Q/triage-t1.json and triage-t2.json (t1 nested=101, structure only).
- **Step-0 gate proof** (Q/triage-step0.txt):
  - `--selftest` passed 11/11 (exit 0).
  - `--no-gen-drop` gave top_mismatch=0 nested=0 (exit 0).
  - The default check exited 1 with exactly the 5 .gendsp files, holding 1 GEN_ORDER record each.
- **Red runs:** Q/red-t1.txt, Q/red-t2.txt (31 failed), Q/red-t3.txt (19 failed).

## PatchGraph API (src/maxpat/graph.py)

- `SIGNAL_OUTLET_TYPES` = {signal, multichannelsignal}.
- `outlet_is_signal(box, outlet)`: the outlettype entry at that index decides, and a non-str entry is never signal. With no entry it falls back to the `~` name. None or non-dict boxes are False. `structure_critic._outlet_is_signal` stays as an alias.
- `Edge(src, outlet, dst, inlet, signal, line)`: one per well-formed cord. Ids must be str/int; ports must be int, not bool.
- `Scope` fields:
  - `path`, `key` (`obj-1/obj-2`), `prefix` (`[p a > p b] `), `context`, `scope`, `patcher` (the raw dict);
  - `boxes` (a duplicate id keeps its first position and its last box), `box_list` (every box with a valid id, duplicates kept);
  - `edges` (line order), `out_edges` / `in_edges`;
  - `parent`, `container`.
- `PatchGraph.build(patch, scope=None)`: one `walk.iter_patchers` pass, read-only. There is always a top scope; for degenerate input it is an empty max scope.
- `scopes` (pre-order, top first); `top`; `children(scope)`; `child(scope, box_id)`; `subtree(scope, box_id)` (the inner scope plus its descendants, pre-order).
- `downstream(scope, box_id, *, signal_only=False, db=None)` / `upstream(...)`: return `(scope, box_id)` pairs in BFS discovery order, start excluded.
  - Crossing is port-exact for max/bpatcher inner scopes. Gen, rnbo and poly containers are opaque.
  - s/r and s~/r~ are bridged by channel across scopes.
  - `signal_only` uses outlettype plus destination acceptance (`validation._is_container_box` / `_inlet_accepts_signal`, lazy import; permissive without db). Port boxes and crossing containers are transparent.
  - There are two visited sets: (scope, box) and (container, port) crossings.
- `resolve_patcher(patcher, path)`: follows `_inner_patcher` by box id; None when a step has none (mc.gen~ `data.patcher`).

## Triage (rule 3): nested findings on committed patches

**0 nested blockers. No allowlist entry was needed** (`tests/review_blocker_allowlist.json` untouched). The calibration test is green after every task.

| Severity | Class | Count | Files (count) | Disposition |
|---|---|---|---|---|
| warning | Low contrast text | 794 | terrain-synth 117, minitaur 48, performance-patch-template 38, reverse-delay 25, wormhole 25, reverse-delay-mono 24, physics-composition 23, subtractive-synth 23, barnett-dbap 21, ji-harmonizer 21, scala-synth 21, gong-model 20, looper 20, stutter 20, bassoon-model 19, intelligent-corpus-remixer 19, sample-layers 19, granularsynthtest 18, simple-fm 18, spectraldetector 18, stereo-feedback-delay 18, timestretch 18, FDNVerb 17, gen-eq-mc 17, gen-eq 17, mixer 17, rhythmic-sampler 17, tape-wobble 17, kicksynth 16, amplitude-follower 14, disintegrate 14, knock 14, mixer-strip 14, rhythmic-corpus-chopper 14, terrain-voice 10, sample-layers-slot 2, dbap-source 1 | **Q26** theme-default false positive (review E7). Never recoloured; no action. |
| warning | Missing midpoints | 539 | terrain-synth 225, physics-composition 132, slot 31, intelligent-corpus-remixer 25, minitaur 24, tape-wobble 16, reverse-delay 14, reverse-delay-mono 13, dbap-source 12, terrain-voice 11, sample-layers-slot 10, wormhole 5, timestretch 4, amplitude-follower 3, ji-harmonizer 3, terrain-cheby 3, slice-voice 2, looper 2, knock 1, scala-synth-voice 1, spectraldetector 1, stereo-feedback-delay 1 | True positive or intentional; user-confirmed patches; no action. |
| warning | Hot/cold inlet ordering | 79 | terrain-synth 30, physics-composition 11, rhythmic-corpus-chopper 8, performance-patch-template 7, intelligent-corpus-remixer 3, minitaur 3, reverse-delay-mono 3, reverse-delay 3, slot 3, dbap-source 2, looper 2, sample-layers-slot 2, subtractive-synth 1, terrain-voice 1 | True positive or intentional; user-confirmed; no action. The 36 gen-scope hot/cold findings are removed by D1. Q21 owns trigger checks. |
| warning | Overlapping boxes | 77 | tape-wobble 21, terrain-synth 14, ji-harmonizer 11, mixer-strip 8, gong-model 6, physics-composition 6, intelligent-corpus-remixer 5, rhythmic-corpus-chopper 3, reverse-delay-mono 1, reverse-delay 1, slot 1 | Intentional; user-confirmed; no action. |
| warning | Fan-out without trigger | 22 | terrain-synth 9, mixer-strip 8, slot 2, gong-model 1, reverse-delay-mono 1, reverse-delay 1 | True positive or intentional (execution order undefined, no reconvergence); no action. |
| note | Bach llll type mismatch | 3 | physics-composition `[p dispatch]` obj-96: `t` obj-7 into bach.keys obj-8/10/12 | Intentional; user-confirmed; no action. |

**Fan-out warnings, with path:**

- **terrain-synth:**
  - `[p terrain-source]` obj-44: inlet obj-1, inlet obj-2, message obj-100.
  - `[p terrain-source-b]` obj-303: the same three.
  - `[p terrain-view-a]` obj-418: loadbang obj-10.
  - `[p terrain-view-b]` obj-419: loadbang obj-10.
  - `[p animate]` obj-635: `t` obj-14 outlet 2.
- **mixer-strip** `[p sends]` obj-37: `+` obj-15/26/37/48/59/70/81/92 into selector~ plus a second destination.
- **rhythmic-sampler slot** `[p clock]` obj-p-clock: expr obj-104, trigger obj-124 outlet 1.
- **gong-model** `[p settings]` obj-21: inlet obj-16.
- **reverse-delay** and **reverse-delay-mono** `[p sync]` obj-141: transport obj-13 outlet 4.

The 4 terrain-synth reconvergence blockers found at planning are now warnings, through the decision-5 setter rule: `[p terrain-source]` / `-b` inlet obj-2, and `[p terrain-view-a]` / `-b` loadbang obj-10.

**gen_dropped (D1), 5 top-level .gendsp hot/cold warnings on `'codebox'`:** FDNVerb/FDNverb.gendsp, bassoon-model/bassoon.gendsp, granularsynthtest/granular-voice.gendsp, stutter/brickwall-limiter.gendsp, stutter/stutter-engine.gendsp (1 each).

## Decisions taken (planner decisions 1-16)

1. **Path tagging.** `CriticResult(severity, finding, suggestion, path="")` with a `path` slot; `__repr__` is unchanged. `tag_results` prefixes the finding only (never the suggestion), and does nothing for `()`.
2. **Shared graph.** `PatchGraph` as specified. It is read-only (deep-equal purity tests) and tolerant: bare boxes and patchlines are accepted, and malformed cords are skipped.
3. **Scope-local checks.** Every check runs per scope; there is no cross-scope critic flow.
4. **Gen scopes.** structure runs duplicates only; dsp, package and m4l per-scope checks skip gen; layout and rnbo run everywhere. **Measured D1 = 5.**
5. **Jitter setter path end** (`_is_jitter_setter_hop`, including the first hop). **Measured: 4 demotions.** No other top-level structure result changed.
6. **package.** `collect_packages_used` runs across non-gen scopes, with per-call `warned_packages` / `flagged` dedup. The BEAP adjacency uses `edge.signal` and keeps the bpatcher special case. A bpatcher's `name` is used only when it is a str, otherwise `""` (the base behaviour).
7. **dsp.** Checks run per non-gen scope, and `code_context` applies to the top scope only.
   - **Deviation:** the signal test is the critic's own outlettype-only read, not `edge.signal`. See Deviations 1.
8. **rnbo.** rnbo~ boxes are found in every scope and reported at the scope that holds them. Params are collected over the rnbo~ subtree; refs below the top inner patcher read `obj-11/obj-10`.
9. **m4l.** Detection runs across non-gen scopes.
   - Device-level checks run once at `""`: completeness, openinpresentation/devicewidth, longname uniqueness (nested refs read `<scope key>/<id>`), and live.banks.
   - Per-scope checks are tagged: gain to plugout~, ezdac~, parameter_enable, empty longname, and info text.
   - Every `saved_attribute_attributes` / `valueof` read is isinstance-guarded.
10. **layout.** Checks run per scope, with gen included. Contrast resolves against each scope's own patcher dict. `_box_label` uses the first token, then the maxclass, then `unknown`. maxclass reads go through `walk.box_maxclass`, so a list maxclass never raises.
11. **Allowlist key.** It includes the path (`_result_key` / `_allow_key`). `test_allowlist_key_includes_path` covers it.
12. **G9 traversal and GraphMixin.** Implemented as specified. `downstream`, `upstream` and `signal_path` build one PatchGraph per call. `_enqueue_neighbors` and `_cross_subpatcher` are deleted. `connected_components` is unchanged.
13. **Recursive analyze().** Implemented, with one added root rule (Deviations 2).
14. **Checklist.** Non-gen scopes, object boxes only, `walk.object_name`.
15. **Decision-15 walkers.** They keep their own code: `hooks._iter_patchers`, `utils.get_box_name`, and the walkers in layout.py, aesthetics.py and m4l_polish.py.
16. **Bundle-only nested findings.** Not triaged; the sweep is a no-crash test only.

**Effects confirmed with Q/triage.py:** 0 top-level changes in any critic, except D1 = 5.

**Effects confirmed by comparing analyze() and checklist output on all 57 committed .maxpat/.maxhelp files** (base vs final, fixed hash seed):

- **Unchanged:** Overview, Sections, Control Flow, Parameters and Subpatchers, top-level part.
- **Signal Flow changed in 35 files.** This is decision 12: `_build_adj(signal_only=True)` now follows outlettype. As a result, p and bpatcher containers and inner `outlet` boxes appear in the trees, and control cords out of `~` objects (for example `gain~` right outlet) are dropped.
- **Checklist:** 23 files gain steps from nested objects (Audio Output, MIDI Input, gen~ Processing, Metro Timing). None lose a step.

## Existing tests changed

- `tests/test_graph.py::TestSubpatcherCrossing::test_downstream_includes_inner_inlets` was renamed to `test_downstream_enters_only_the_wired_inlet` and inverted, as the plan specified. It asserted the retired every-inner-inlet crossing.
- No other existing test was changed or inverted.

## Deviations from Plan

### Auto-fixed issues

**1. [Rule 1 - existing test] dsp critic keeps its own outlettype signal reads**
- **Found during:** the Task 3 full suite.
- **Issue:** `tests/test_signal_role_migration.py::TestBackCompatConsumerAnchors::test_dsp_critic_outlet_signal_read_pattern_unchanged` failed after Task 2.
  - That test pins at least 3 `outlettype` / `_SIGNAL_OUTLET_TYPES` read sites in dsp_critic.py.
  - Decision 7's `edge.signal` had removed them. Task 2's verify subset does not include that file.
- **Fix:**
  - Following the existing-tests rule (fix the code first), gain staging and the two unsafe-gain adjacency passes decide signal-ness from the source box's outlettype only, as at base, now over `Edge` tuples.
  - A `_outlettype` helper returns str entries only, so a list entry never raises.
  - This matches base exactly on hand-built dicts too (no `~` fallback), and is identical on committed patches.
- **Files modified:** src/maxpat/critics/dsp_critic.py
- **Commit:** d77b9b93, a 4th `(Q20)` commit (see "Commit count" below).

**2. [Rule 1 - regression] analyze() Signal Flow lost whole chains**
- **Found during:** the Task 3 base/final analyze() comparison.
- **Issue:** with outlettype-based `_build_adj`, a p or bpatcher feeding a `~` chain now counts as a signal input. Five committed patches therefore printed `(no signal objects detected)` where base had trees: physics-composition, sample-layers, subtractive-synth, comp-band and control-demo.
- **Fix:** `_signal_body` roots now also include non-`~` boxes that emit a signal cord and have no signal input. 0 files now lose their tree.
- **Files modified:** src/maxpat/analysis.py (in the Task 3 commit).

**3. [Process] Task 2 tests written after the implementation**
- The Task 2 code was written before its tests (rule 2 asks for tests first).
- **Red evidence:** Q/red-t2.txt runs the full Task 2 test file against the Task 1 commit 5922ecd9, in a temporary detached worktree that was removed afterwards. It shows 31 failed and 42 passed (the Task 1 cases), which is the red state the plan expects.

**4. [Test fixture] `test_multichannel_cord_followed`**
- The DB derives `signal` (not `multichannelsignal`) for `mc.cycle~` outlet 0 on a newly built box.
- The test therefore sets `outlettype = ["multichannelsignal"]` (MAX's saved form) before asserting that the cord is followed.

**5. [Test expectation] two Task 1 cases corrected before green**
- The "bang still propagates" case needs `, bang` in both messages; with one, it correctly stays a warning.
- The pre-order case expects the hot/cold warning that the reconvergent `pack` also produces.

### Commit count: 4 instead of 3

- `5922ecd9` Task 1: 6 files.
- `b2b96823` Task 2: 7 files.
- `d77b9b93` an extra fix to a Task 2 file (src/maxpat/critics/dsp_critic.py only). Reason: Deviation 1.
- `f3bfdce3` Task 3: 9 files.

History was not rewritten. The automated Task 3 verify passed every check except `test $# -eq 3`.

The remaining checks were run by hand:

- Q/q20-commits.txt lists the 4 commits.
- Q/q20-commit-files.txt has the `git show --name-only` output for every commit, with no `patches/` path.
- Q/commit-check.txt: the stash list is unchanged (empty), no `patches/` paths, and the file is non-empty.

## Out of scope / doc impact, not edited (rule 8)

- `.claude/skills/references/severity-contract.md` §9 "Scope of the walk": blocking critic findings now come from every scope.
- TECHNICAL.md:561: M4L detection is no longer top-level only. The layout-critic description there also needs updating.
- README.md validation-pipeline paragraph: the critics are now recursive.
- The max-critic skill and `critic-protocol.md`, wherever they describe top-level-only review.
- `tests/review_blocker_allowlist.json` `_doc`: keys now include an optional `path` (default `""`).
- Decision-15 walkers left on their own code: `hooks._iter_patchers`, `utils.get_box_name` (now used only by m4l_polish and tests), and the layout.py, aesthetics.py and m4l_polish.py walkers.
- **Follow-ups:**
  - cross-scope critic flow, now possible on the G9 traversal (oscillator in `p` to a top-level dac~, gain~ in `p` to plugout~, BEAP across bpatchers);
  - analysis flow across subpatcher boundaries (review §4.4 item 12);
  - embedded poly~ port crossing (`in N` / `out N`);
  - Q26 theme-aware contrast (794 nested low-contrast warnings);
  - Q21 trigger and `$N` ordering checks;
  - RNBO data gaps;
  - the 917 bundle-only nested blockers.

## Known Stubs

None.

## Threat Flags

None. No new network, auth, file or schema surface; T-uzq-01 to T-uzq-09 are mitigated as planned:

- robustness, purity and bundle-sweep tests;
- triage nested_bad=0;
- the path-aware allowlist and gate keys;
- loop-terminating visited sets;
- no `patches/` edits, explicit-path staging and no stash.

## MAX/Live confirmation

None required: the work is critic, analysis and graph code only, and no patch changed. Optionally, check that `/max-verify` and `/max-test` output reads well on a patch with subpatchers, including the `[p ...]` prefixes and the `### [p ...]` analysis blocks.

## Self-Check: PASSED

- All 18 files exist.
- Commits 5922ecd9, b2b96823, d77b9b93 and f3bfdce3 are present in `git log`.
- Q artifacts are present: base-sha.txt, stash-list-before.txt, baseline-pytest.txt, triage.py, triage-base.json, triage-step0.txt, red-t1/t2/t3.txt, triage-t1/t2/final.json, t3-gate-b/c/d.txt, final-pytest.txt, q20-commits.txt, q20-commit-files.txt, commit-check.txt.
