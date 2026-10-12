---
phase: quick-261012-egf
verified: 2026-10-12T23:10:00Z
status: passed
score: 8/8 must-haves verified
covered_files:
  - ".planning/quick/261012-egf-implement-q4-in-planning-reviews-2026-10/261012-egf-PLAN.md"
  - ".planning/quick/261012-egf-implement-q4-in-planning-reviews-2026-10/261012-egf-SUMMARY.md"
  - "src/maxpat/critics/__init__.py"
  - "src/maxpat/critics/dsp_critic.py"
  - "src/maxpat/critics/m4l_critic.py"
  - "src/maxpat/critics/rnbo_critic.py"
  - "tests/test_critic_revival.py"
covered_digest: "v2:sha256:485ab18cec1cd8ded69add76c7c9f4fd974421cd514705d9d7438f8fc7f6b185"
behavior_unverified: 0
overrides_applied: 0
---

# Quick 261012-egf (Q4): Revive dead critic detectors and review_m4l - Verification Report

**Goal:** Implement Q4 of `.planning/reviews/2026-10-11-fix-plan.md`: revive the dead critic detectors (gen~/mc.gen~/rnbo~) and wire `review_m4l` into `review_patch`.
**Verified:** 2026-10-12
**Status:** passed
**Re-verification:** No, initial verification

I did not rely on SUMMARY.md. I read both commit diffs, ran the full suite, re-ran the corpus triage against a base export of 635883b, and ran behavioral probes. I also mutated a scratch copy of the code to check the new tests catch regressions.

## Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | newobj `gen~` / `mc.gen~` with mismatched codebox I/O get the existing `gen~ I/O` blockers. mc.gen~ is read from `data.patcher` as well as `patcher`. Old maxclass fixtures still fire. | VERIFIED | `dsp_critic.py` has `_GEN_BOX_NAMES` and gate `get_box_name(box) not in _GEN_BOX_NAMES`. `_gen_inner_patcher` returns `patcher` or `data.patcher`. Probe: ji-harmonizer obj-88 (mc.gen~, `data.patcher` only) gives no finding unmutated and an input blocker naming obj-88 with numinlets set to 2. The `TestGenIOByName` cases cover hand-built, add_gen, and wormhole obj-12. Mutating the gate back to maxclass makes 8 tests fail. |
| 2 | (OQ1-A) An unwired codebox is skipped; `code_context` fallback is preserved. | VERIFIED | `_extract_codebox_code` builds `wired_ids` from patchline source/destination and skips unwired codeboxes. Mutating the wiring filter out makes 2 tests fail. Bundle `gen~.maxhelp` gives no gen~ I/O finding (probe, Max installed). |
| 3 | `review_patch` runs the RNBO critic for newobj `rnbo~` boxes; `review_rnbo` reviews them. Maxclass fixtures unchanged. | VERIFIED | `is_rnbo_box` in `rnbo_critic.py` is used by both the `review_rnbo` loop gate and `_has_rnbo_boxes`. Mutating it back to maxclass makes 4 tests fail. `tests/test_critics.py` passes unchanged. |
| 4 | `review_patch` calls `review_m4l` when plugin~, plugout~ or live.thisdevice is present. Device type is inferred (plugin~ gives audio_effect, plugout~ gives instrument, else midi_effect). None when no marker is present. | VERIFIED | `detect_m4l_device_type` and the dispatch block in `critics/__init__.py` are present, and `review_m4l` is in `__all__`. Probe: kicksynth at 408cdf8 and 494c2e6 are both detected as `instrument`. The `TestM4LDispatch` cases cover the rest. |
| 5 | Instruments no longer require midiin/midiout. No type requires live.thisdevice. | VERIFIED | `_REQUIRED_OBJECTS` = audio_effect {plugout~}, instrument {plugout~}, midi_effect {midiin, midiout}. This matches OQ2-A. |
| 6 | One blocker per (gain~ or live.gain~ stage, plugout~) pair over signal cords, direct or indirect. Control cords don't count. (OQ3-A) Any top-level ezdac~ in a detected device is a blocker. | VERIFIED | `_check_gain_plugout` does a reverse BFS over cords filtered by `_outlet_is_signal` and collects a set of (plugout, stage) pairs. This gives one blocker per pair even with two cords, and the visited set makes cycles safe. It emits an ezdac~ blocker per top-level ezdac~. Probe: kicksynth 408cdf8 gives exactly one blocker (gain~ obj-8 to plugout~ obj-9), and 494c2e6 gives zero blockers. Mutating the signal filter out makes 1 test fail. |
| 7 | `review_patch` on `add_m4l_gen_synth` output runs the M4L critic (at least one `M4L device` warning) with zero blockers. | VERIFIED | Probe: 0 blockers, 3 `M4L device` warnings. |
| 8 | `review_patch` on all 57 committed patches gives the same findings before and after; full suite green; no patch file changed; Python 3.10 syntax gate passes. | VERIFIED | Independent triage against a `git archive 635883b` export (src and .claude): 57 files, 1350 findings, 1 blocker before and after, 0 new and 0 gone. A first run that lacked `.claude/` showed 3 spurious Bach notes; that was my harness missing the object DB, not a regression. Full suite: 2520 passed, 1 xfailed, 1 xpassed (baseline 2475, so +45 new tests). `git diff 635883b HEAD --name-only` lists only the 5 plan files, none under `patches/`. The stash list is empty. `ast.parse(feature_version=(3, 10))` passes on all 5 .py files. |

**Score:** 8/8 truths verified (0 present but behavior-unverified)

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tests/test_critic_revival.py` | Q4 regression tests (min 200 lines, contains `TestGenIOByName`) | VERIFIED | 579 lines, 45 tests, all passing. Mutation checks show the tests are not vacuous. |
| `src/maxpat/critics/dsp_critic.py` | `_GEN_BOX_NAMES`, `_gen_inner_patcher`, wired-codebox selection | VERIFIED | All present and used by `_check_gen_io_match`. |
| `src/maxpat/critics/rnbo_critic.py` | `def is_rnbo_box` | VERIFIED | Present, imported by `critics/__init__.py`. |
| `src/maxpat/critics/m4l_critic.py` | `detect_m4l_device_type`, `_M4L_GAIN_STAGE_NAMES`, reduced sets, ezdac~ check | VERIFIED | All present. `_LIVE_NO_PARAM` is kept for `m4l_polish`. |
| `src/maxpat/critics/__init__.py` | Dispatches `review_m4l`; `_has_rnbo_boxes` by name | VERIFIED | Both present. |

## Key Link Verification

| From | To | Via | Status |
|------|----|-----|--------|
| `critics/__init__.py` | `m4l_critic.py` | `review_m4l(patch_dict, device_type=m4l_device_type)` | WIRED |
| `critics/__init__.py` | `rnbo_critic.py` | `is_rnbo_box` shared by dispatch and review | WIRED |
| `dsp_critic.py` | gen patcher | `_check_gen_io_match` to `_extract_codebox_code` to `_gen_inner_patcher` | WIRED |
| `m4l_critic.py` | `structure_critic.py` | `_outlet_is_signal` imported and used in the BFS | WIRED |

## Behavioral Spot-Checks and Probes

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full suite | `python3 -m pytest -q -p no:cacheprovider` | 2520 passed, 1 xfailed, 1 xpassed | PASS |
| Corpus triage | review_patch over 57 files, base vs HEAD | 1350/1350 findings, 0 new, 0 gone | PASS |
| Real-file repro (mc.gen~ via `data.patcher`) | mutate ji-harmonizer obj-88 numinlets | input blocker naming obj-88 | PASS |
| Historical kicksynth | review_patch on 408cdf8 and 494c2e6 | 1 blocker (gain~ obj-8 to plugout~ obj-9) and 0 blockers | PASS |
| Builder skeleton | `add_m4l_gen_synth` then review_patch | 0 blockers, 3 M4L warnings | PASS |
| Bundle gen~.maxhelp | review_patch | no gen~ I/O finding | PASS |
| Test sensitivity | scratch-copy mutations (gen gate, rnbo gate, signal filter, wiring filter) | 8, 4, 1 and 2 test failures | PASS |

There are no `probe-*.sh` scripts declared for this task.

## Requirements Coverage

| Requirement | Description | Status |
|-------------|-------------|--------|
| E3 | gen~/mc.gen~/rnbo~ detected by name; mc.gen~ `data.patcher` read | SATISFIED |
| D4 | review_m4l wired in; reduced required objects; gain stages on any signal path; builder clean | SATISFIED |

## Anti-Patterns Found

None. There are no TBD, FIXME or XXX markers in the changed files, no stubs, and no patch files touched. The working tree shows only the pre-existing `patches/.active-project.json` modification and untracked planning files.

## Human Verification Required

None. This is critic logic and test code only; no patch or builder changed, so there is nothing to confirm in MAX or Live.

## Notes (advisory, not gaps)

- **Residuals are all declared out of scope and match the plan:**
  - send~/receive~ paths aren't followed;
  - mc.gain~ is not in the gain set;
  - critics are top-level only;
  - only the first wired codebox is compared.
- **Hand-offs to later tasks:**
  - E8 missing-in~ now fires on MAX-authored rnbo~ boxes (Q26);
  - Q7's save gate will see M4L and RNBO blockers.
- **Docs not updated, as the plan directs:** `TECHNICAL.md:504` and `:554`, the max-critic SKILL, and critic-protocol.md. SUMMARY.md lists them.
- **SUMMARY accuracy:** its claims on test totals, triage, historical results and line references matched what I found.

---

_Verified: 2026-10-12_
_Verifier: Claude (gsd-verifier)_
