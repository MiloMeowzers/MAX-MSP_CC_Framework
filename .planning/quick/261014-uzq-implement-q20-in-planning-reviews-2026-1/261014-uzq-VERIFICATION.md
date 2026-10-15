---
phase: quick-261014-uzq
verified: 2026-10-14T00:00:00Z
status: passed
score: 9/9 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Quick 261014-uzq (Q20): Verification Report

**Goal:** Recursive critics, `analyze()`, test checklist and graph traversal (review A7, G9, G10, S1).
**Commits:** 5922ecd9, b2b96823, d77b9b93, f3bfdce3 (ad3213e4..HEAD)
**Status:** passed
**Re-verification:** No

## Evidence gathered independently

- Full suite, run by me: **3909 passed, 1 xfailed, 1 xpassed**. Base was 3813/1/1. `git status --porcelain` was unchanged across the run.
- Calibration (`test_calibration_zero_blockers`), allowlist, `test_review_patch_no_blockers`, gate, graph and signal-role-migration tests: 199 passed in a targeted run.
- Max 9 bundle sweep (`TestBundleSweep`, requires_max): 1 passed (Max is installed here). It covers `review_patch`, `generate_test_checklist`, `PatchGraph.build` and both traversals on all bundle files.
- **Triage re-run against an independent base.**
  - I rebuilt the base critic snapshot myself from `git archive ad3213e4` (unmodified code). It is identical to the executor's `triage-base.json` (`snapshots equal: True`; 69 files, 1164 warning / 216 note / 1 blocker).
  - `triage.py --selftest` gave 11/11.
  - `triage.py --check` on HEAD gave `files=69 top_mismatch=0 gen_dropped=5 nested_bad=0 nested=1514`, exit 0.
- Scope: `git diff --stat` shows exactly the 18 planned files. Nothing under `patches/` changed, `tests/review_blocker_allowlist.json` is untouched, and the stash list is empty.
- Every changed .py parses with `feature_version=(3, 10)`.
- No module in `src/maxpat/critics/` imports `utils` any more.
- Direct probes on HEAD:
  - A button fan-out reconverging at pack inlets 0 and 1 inside `p synth` gives a blocker with `path == "obj-1"` and a `[p ...] ` prefix.
  - `signal_path(cycle~)` through a `p` now returns `cycle~, p, inlet, *~, outlet, dac~`.
  - The G10 repro (`dac~` in `p synth` plus a comment) produces the Audio Output test and the audio-on setup step. It does not produce Metro Timing or gen~ tests.

## Observable truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A nested fan-out blocker has a path and prefix, and the save gate refuses it. A moved nested blocker is new. | VERIFIED | Probe above; TestSaveGateNestedCritic passes; `hooks._finding_key` reads `path`. |
| 2 | All critics review every scope with path tagging. Top-level output is byte-identical apart from the 5 enumerated gen hot/cold warnings. | VERIFIED | `top_mismatch=0`, `gen_dropped=5` against my independently rebuilt base. Parity tests pass. `tag_results` in `base.py`. |
| 3 | One `PatchGraph` and at most one ObjectDatabase per `review_patch` call, shared by all critics. | VERIFIED | `__init__.py:113` builds once and passes `graph=graph` to dsp, structure, layout, rnbo, m4l and package. Spy tests pass. |
| 4 | Calibration stays green. 0 nested blockers on committed patches. The Jitter-setter and gen-scope false positives are fixed. The allowlist key includes the path. | VERIFIED | `nested_bad=0` over 69 files. Calibration test green. `test_allowlist_key_includes_path` passes. |
| 5 | G9: traversal is port-exact, s/r-bridged, decides signal by outlettype, and builds adjacency once. | VERIFIED | Crossing, bridging, outlettype and adjacency-once tests pass. `signal_path` probe passes through `p`. |
| 6 | `analyze()` recurses. Inventory, Sections, Signal Flow, Control Flow and Parameters get nested blocks after the top-level content. | VERIFIED (see note) | Recursive-analyze tests pass. Across 56 committed .maxpat files, Sections and Control Flow top-level text is unchanged. Signal Flow top-level text changed; see Advisory 2. |
| 7 | The checklist recurses and counts object boxes only. Whitespace text never raises. | VERIFIED | G10 repro probe; TestRecursiveChecklist passes. |
| 8 | No crashes on the Max 9 bundle. | VERIFIED | Sweep ran and passed here. |
| 9 | No `patches/` change. Full suite green. Python 3.10. Exactly 3 `(Q20)` commits. | VERIFIED with deviation | Everything holds except the commit count: there are 4 (see Advisory 1). |

## Advisory findings (not blockers)

1. **Commit count 4, not 3 (documented deviation).**
   - The extra commit d77b9b93 touches only `src/maxpat/critics/dsp_critic.py`.
   - It restores outlettype-only signal reads that `tests/test_signal_role_migration.py` pins. That test failed only in the full suite, because Task 2's verify subset omitted it.
   - The plan's own rules allow extra `(Q20)` commits with a reported deviation. History was not rewritten.
   - The by-hand checks were done: stash unchanged, no `patches/` path in any Q20 commit.
   - Effect: dsp uses its own outlettype read instead of `edge.signal`, as the existing test required. It is identical on committed patches.
2. **`analyze()` Signal Flow output changed at the top level.**
   - Planner decision 12 (outlettype-based `_build_adj`) makes this inevitable. It conflicts with the loose "unchanged top-level content" wording in the truth.
   - I compared base against HEAD on 56 patches (fixed hash seed). Sections and Control Flow are unchanged.
   - Signal Flow differs in a large share of files. Spot checks (gen-eq-test, control-demo) show chains now reach through `bpatcher`, `p` and `outlet` boxes instead of being cut off. I found no lost chains. The executor also added a root rule so no tree is lost.
   - This is disclosed in SUMMARY. Treat it as an intended behaviour change. Visually sanity-check `/max-verify` and `/max-test` output.
3. **Test-first deviation for Task 2.** The tests were written after the code. SUMMARY discloses it and `red-t2.txt` shows the red run against the Task 1 commit.
4. **Doc impact not edited, as the plan required:** severity-contract.md §9, TECHNICAL.md:561, the README validation paragraph, the max-critic skill and critic-protocol, and the allowlist `_doc`. About 794 nested low-contrast warnings are Q26 and were never recoloured.

## Human verification

None required. Optionally, read `/max-verify` and `/max-test` output on a patch with subpatchers.

## Gaps

None.

---

_Verified: 2026-10-14_
_Verifier: Claude (gsd-verifier)_
