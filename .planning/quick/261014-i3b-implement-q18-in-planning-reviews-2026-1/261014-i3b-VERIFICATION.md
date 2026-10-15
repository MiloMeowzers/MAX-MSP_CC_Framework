---
phase: quick-261014-i3b
verified: 2026-10-15T03:40:09Z
status: passed
score: 7/7 must-haves verified
covered_files:
  - CLAUDE.md
  - src/maxpat/builders.py
  - tests/test_agent_skills.py
  - tests/test_claude_md.py
  - .planning/quick/261014-i3b-implement-q18-in-planning-reviews-2026-1/261014-i3b-PLAN.md
  - .planning/quick/261014-i3b-implement-q18-in-planning-reviews-2026-1/261014-i3b-SUMMARY.md
covered_digest: "v2:sha256:d0eec7c287e407cb3abf49390c4ac2c313216fc73061363f4dd2149a8be3cf9d"
behavior_unverified: 0
overrides_applied: 0
---

# Quick 261014-i3b (Q18: slim CLAUDE.md) Verification Report

**Goal:** Shrink CLAUDE.md from about 45 KB to about 27 KB without losing any rule. Move the detail to its new homes and dedupe the skills. Update tests only for moved text. Report sizes.
**Commits:** b22fd90a, 9aaee361, d30c199b (base 725f568f)
**Re-verification:** No, initial verification.

## Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | CLAUDE.md is at most 30,000 bytes (target about 27 KB) | VERIFIED | `wc -c CLAUDE.md` gives 26,782. Base was 49,752. |
| 2 | No rule is lost. Each rule is a one-liner that names its new home. | VERIFIED | See "Rule preservation" below. |
| 3 | Tests changed only for moved text | VERIFIED | `git diff --numstat 725f568f HEAD -- tests/` gives +86/-0 and +269/-0, so additions only and no existing assertion edited or removed. The additions are `RULE_ANCHORS`, `BASE_HEADINGS`, a size ratchet, `MOVED_DETAIL` and the dedupe/pointer tests. |
| 4 | `builders.py` changed only in docstrings | VERIFIED | AST comparison of the base and HEAD files with docstrings blanked gives identical trees (`AST equal modulo docstrings: True`). The diff is +53/-4, all inside the `add_overlay_readout` and `add_labeled_param_bank` docstrings. |
| 5 | No `patches/` files touched | VERIFIED | `git diff --name-only 725f568f HEAD` lists no path under `patches/`. |
| 6 | The Builder API block and the 6x Output Protocol (Edited Patches) block are single-sourced in shared-capabilities.md | VERIFIED | The marker "Make surgical edits or section rebuild" appears once, in shared-capabilities.md, and 0 times in any SKILL.md. patch-agent and ui-agent carry a pointer stub (tests `test_dedupe_*`). Every non-blank line of the base Builder API block (patch-agent lines 80-182) and of each base Output Protocol section exists in shared-capabilities.md. The only exceptions are the rnbo Export Target and ext Archetype subsections, which intentionally stay in place. The one exception in the Builder API block is a cosmetic "Replaces the 5-step manual recipe in CLAUDE.md" line. |
| 7 | Suite is green. `1 xfailed, 1 xpassed` are pre-existing and unrelated to pending-q18 markers. | VERIFIED | See "xfail/xpass" below. |

**Score:** 7/7

## Rule preservation

- **Headings:** all 30 base headings survive verbatim (`BASE_HEADINGS` test passes).
- **Moved detail:** I diffed every backticked token and bold label of base CLAUDE.md against the new file and the corpus (all skills plus builders.py). 566 tokens were extracted, 169 are absent from CLAUDE.md, and 22 are absent everywhere. Of those 22, 12 are regex artifacts or fragments (for example `') reject with ...'`, `buffer~ slot-1`, `old_box`). The others are rationale and example detail, not rules:
  - `stash && merge && pop`. The rule (never stash, check `git stash list`) survives. Only the short-circuit explanation is gone.
  - `git show HEAD:path`. This is the save-gate baseline detail.
  - `git commit -m msg -- <paths>` and `UserWarning`. The path-scoped commit and warn-and-return-None behavior survive.
  - Individual `function bang()` and `maxAPI.addHandler/getDict/setDict` snippets. These are present in `max-js-agent/SKILL.md` in other forms.
  - `Examples/javascript/v8-network`. The `Examples/javascript` path is in `max-9.2-changes.md`.
- **Gen~ rules:** every rule is a bold-labelled one-liner in CLAUDE.md. The derivations and per-version evidence are present in `genexpr-rules.md`: phase-delay formula, `PB_re`, mode-competition, `maxb_NN`, `gmax_raw`, `srs = samplerate * one`, spectraldetector, ji-harmonizer v0.1.2, stereo-feedback-delay, and others. max-dsp-agent line 23 loads `genexpr-rules.md`.
- **Other homes:** DB internals are in `db-maintenance.md`, the contrast algorithm in `ui-presets.md` ("Text Contrast Resolution"), and the multislider and z-order recipes in the builder docstrings. The `Reading values by index` and `fetch $1` rule stays in CLAUDE.md.
- **External citations:** code and docs cite the bold labels "Waveguide loop filters" and `Gen~ (GenExpr DSP Code)`, and both still resolve in CLAUDE.md.
- **Tests:** `tests/test_claude_md.py` and `tests/test_agent_skills.py` give 515 passed.

## xfail/xpass

- A full-suite run just now gives `3677 passed, 1 xfailed, 1 xpassed`.
- The xfail is `tests/test_round_trip.py::TestFileLevelRoundTrip::test_framework_file_byte_identical`. Its reason is that rhythmic-sampler.maxpat was re-saved by MAX with different indentation.
- The xpass is `test_max_saved_file_byte_identical`. Its reason is that comp-band.maxpat was re-saved by MAX with different array formatting.
- Both come from a pre-existing `xfail` in `test_round_trip.py`. The task's `baseline-pytest.txt` (before the change) also reads `3346 passed, 1 xfailed, 1 xpassed`.
- `grep` for `xfail`/`xpass` in `tests/test_claude_md.py` and `tests/test_agent_skills.py` finds nothing, and `pending-q18` appears nowhere in `tests/`, `src/` or `.claude/`. The `XFAIL` entries in `pending-markers.txt` were a temporary red-first stage that was removed.
- The patches/ round-trip tests that xfail/xpass are unrelated to Q18.

## Sizes (bytes, before to after)

| File | Before | After |
|------|--------|-------|
| CLAUDE.md | 49,752 | 26,782 |
| max-patch-agent | 20,891 | 15,116 |
| max-ui-agent | 14,257 | 8,703 |
| max-dsp-agent | 24,532 | 24,288 |
| max-js-agent | 8,668 | 9,014 |
| max-rnbo-agent | 6,551 | 6,098 |
| max-ext-agent | 4,833 | 4,380 |
| max-router | 5,639 | 5,782 |
| shared-capabilities | 11,449 | 18,265 |

## Anti-Patterns / Findings (non-blocking)

| Severity | Item |
|----------|------|
| Info | CLAUDE.md gained `**Experimental:**` lines under the RNBO and M4L headings. Q17 labelled these only in README, TECHNICAL and the skills. The addition was a planned decision (the plan lines 184-185 and SUMMARY handoff 4) and it is disclosed. The tests lock the exact text. |
| Info | shared-capabilities.md still says the builder "Replaces the 5-step manual recipe in CLAUDE.md §Rule #6". The recipe now lives in the docstring. The wording is slightly stale and affects no behavior. |
| Info | The explanatory rationale for the stash-chain short-circuit and the `git show HEAD:path` save-gate baseline was dropped. The rules themselves remain. |
| Info | `max-js-agent` grew by about 350 bytes and `max-router` by about 140. Both are expected, because the js/N4M pointers landed in max-js-agent and the router's loading table gained a row. |

No TBD/FIXME/XXX debt markers were introduced. There is nothing for the user to confirm in MAX or Live, since this is a documentation and docstring change.

## Gaps Summary

None. The goal is achieved: CLAUDE.md is 26.8 KB, all 30 headings and the rule imperatives are retained with pointers to their homes, and the duplicated skill blocks are single-sourced. Only tests, docs and docstrings changed, and the suite is green.

---

_Verified: 2026-10-14_
_Verifier: Claude (gsd-verifier)_
