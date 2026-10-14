---
phase: quick-261014-gf2
plan: 01
status: complete
subsystem: docs
tags: [docs, severity, troubleshooting, proven-forms, theme, experimental-labels, Q17]
requires: [Q16 merged (49fbfd4b)]
provides:
  - .claude/skills/references/severity-contract.md
  - .claude/skills/references/troubleshooting.md
  - .claude/skills/references/proven-forms.md
affects: [CLAUDE.md Rule #2, max-critic, critic-protocol, max-build, max-iterate, TECHNICAL, README, ui-presets, shared-capabilities, max-rnbo/patch/ui/dsp-agent skills, dsp_sim comments]
tech-stack:
  added: []
  patterns: [evidence-tiered reference docs, report-not-annotate critic findings]
key-files:
  created:
    - .claude/skills/references/severity-contract.md
    - .claude/skills/references/troubleshooting.md
    - .claude/skills/references/proven-forms.md
  modified:
    - CLAUDE.md
    - TECHNICAL.md
    - README.md
    - .claude/skills/max-critic/SKILL.md
    - .claude/skills/max-critic/references/critic-protocol.md
    - .claude/commands/max-build.md
    - .claude/commands/max-iterate.md
    - .claude/skills/references/shared-capabilities.md
    - .claude/skills/references/ui-presets.md
    - .claude/skills/max-rnbo-agent/SKILL.md
    - .claude/skills/max-patch-agent/SKILL.md
    - .claude/skills/max-ui-agent/SKILL.md
    - .claude/skills/max-dsp-agent/SKILL.md
    - src/maxpat/builders.py
    - src/maxpat/dsp_sim/classifier.py
    - src/maxpat/dsp_sim/runner.py
    - src/maxpat/dsp_sim/topologies/reed_bore.py
    - src/maxpat/dsp_sim/topologies/reed_bore_post_radiation.py
    - tests/dsp_sim/README.md
    - tests/dsp_sim/fixtures/bassoon_v041_mirror.py
    - tests/dsp_sim/test_bassoon_v040_regression.py
decisions:
  - "Critic warnings/notes are reported in the review summary, never written into patches or code (max-critic, critic-protocol, max-build, max-iterate, TECHNICAL)"
  - "Shipped files point dead memory citations to CLAUDE.md rules; maintainer-only tests/ files point to the archived-memories file"
  - "Unknown object documented as a non-blocking validator warning that Rule #1 still forbids (Q23 makes it an error)"
metrics:
  duration: "~11 min wall clock after Step 0 (plus a ~67 s baseline run)"
  completed: 2026-10-14
estimate:
  tokens: 150000
  tasks: 3
actuals:
  tokens: 18100    # chars/4 over the realized diff 49fbfd4b..3e3742e6 (72,449 chars)
  tasks: 3
  commits: 3
plan_head_before: 49fbfd4b40caa858ba6f69de0ca114dd75824660
plan_head_after: 3e3742e6f467003d524bc75b0c8770f30c8cce39
---

# Phase quick-261014-gf2 Plan 01: Q17 Missing Documentation Summary

Three new shipped reference docs: a code-verified severity contract (validator levels, proposed removals, critic severities, save gate), a MAX console-error troubleshooting table, and evidence-tiered proven forms promoted from private memory. Also: the critic stops writing findings into patches, README states macOS-only and its dependencies, the Max 9 theme defaults are documented, RNBO/M4L builders are labeled experimental, and the two dead memory citations are repointed.

## Figures

| Run | Result |
|---|---|
| Baseline (`49fbfd4b`, Q/baseline-pytest.txt) | 3343 passed, 1 xfailed, 1 xpassed, 29 warnings (66.8 s) |
| Final (`3e3742e6`, Q/final-pytest.txt) | 3346 passed, 1 xfailed, 1 xpassed, 29 warnings (65.7 s) |
| `pytest --collect-only` | 3345 -> 3348 |

The +3 delta is exactly one `test_doc_call_forms_match_signatures` case per new reference doc (DOC_FILES rglobs `.claude/skills/**/*.md`). `git status --porcelain` was identical before and after every pytest run. No test file was edited and nothing under `patches/` changed.

## Item table

| Item | Files | Evidence | Commit |
|---|---|---|---|
| REV3-1 severity contract | severity-contract.md (new), CLAUDE.md Rule #2 (one line), max-critic SKILL.md, critic-protocol.md, max-build.md, max-iterate.md, TECHNICAL.md | Q/severity-probe.txt; validation.py, critics/, hooks.py, code_validation.py, rnbo_validation.py, package_critic.py | d80d5352 |
| REV3-2 troubleshooting | troubleshooting.md (new) | CLAUDE.md sections; Max user guide `C74/docs/userguide/content/error_messages.json`; MEM by topic (name traps, gen Param clash, FluCoMa notes, expr~, TCI notes) | 45923e19 |
| REV3-5 theme defaults | ui-presets.md "Max 9 Theme Defaults"; max-ui-agent pointer | `default.maxtheme` `styledefaults` (Max 9.2.0) | 45923e19 / 3e3742e6 |
| REV3-6 proven forms | proven-forms.md (new); shared-capabilities.md "Reference Docs" | 12 review §3.6 items; bundle refpages (trigger, plus, scale, conformpath, jit.bfg, mcwrapper-group, waveform~.maxhelp, adsr-synth.maxpat); FluCoMa package refpages; code; MEM by topic; Q/objects-check.txt | 45923e19 |
| REV3-3 macOS + deps | README Prerequisites | requirements-dev.txt; ext_validation.py (`file`, `lipo`), externals.py (cmake, Unix Makefiles), project.py (git), README install Option A (npx) | 3e3742e6 |
| REV3-7 experimental labels | README (2 bullets), TECHNICAL (2 rows), max-rnbo-agent, max-patch-agent, max-ui-agent | no `.amxd` / `rnbo~` under patches/ | 3e3742e6 |
| REV3-8 dead citations | max-dsp-agent, max-patch-agent, max-ui-agent SKILL.md; builders.py; dsp_sim classifier/runner/2 topologies; tests/dsp_sim README, fixture, regression test | ARCHIVE section "Resonant filters belong OUT of a waveguide loop"; CLAUDE.md Gen~ "Waveguide loop filters", Rule #4 "Reading values by index" | 3e3742e6 |

## Severity probe highlights (Q/severity-probe.txt)

- **Unknown object (`zzfoo~`) is a validator `warning`**: `has_blocking_errors` False for both `is_new` values, and a new file containing it saves through the gate (case f2). Q23 is what will make it an error; the contract says Rule #1 still forbids it.
- `osc~` (PD) and `expr~` at Max scope are `error`s that block in both modes.
- An out-of-range cord is an `error` with `proposed_removal=('obj-1', 5, 'obj-2', 0)`: blocks with `is_new=True`, not with `is_new=False`; the input dict is unchanged; `apply_fixes` on a copy removed exactly that cord and re-validation left no proposals.
- **The level `"fixed"` is never emitted** and `auto_fixed` is never set (grep over src/ and the probe).
- Critic blocker (cycle~ -> dac~ without gain): the new-file save raises `PatchValidationError` and writes nothing; `force=True` writes and emits `SaveGateWarning`. Edit with only a pre-existing blocker saves; an edit adding an out-of-range cord is refused even on the edit path (the gate uses the `is_new=True` blocking set and diffs against the baseline); removing a cord saves with a `SaveGateWarning`; a stale `original_text` raises `StaleFileError`.
- `write_js` with an `outlet()` index error writes the file and returns the `error`.
- **Gap found:** `write_gendsp("out1 = delay(in1, 100);")` is written without refusal. The gate's `validate_patch` does not apply GenExpr checks to a `.gendsp`'s own top-level codebox (Layer 5 only walks codeboxes inside top-level `gen~` boxes). The same code inside a `.maxpat` gen~ codebox is refused (case j). The contract and TECHNICAL "Code Validation" say exactly this; the code is not changed (no code changes in Q17). Candidate for Q19/Q23.

## Decisions taken (planner decisions 1-14)

1. `references/` = `.claude/skills/references/`.
2. **Release-safe repointing:** shipped files (src/, .claude/skills/) point to the CLAUDE.md rules "Waveguide loop filters" and Rule #4 "Reading values by index"; maintainer-only tests/dsp_sim files point to the ARCHIVE path and section plus the CLAUDE.md rule. No shipped file gained a `.planning/` reference.
3. .py edits are comment/docstring-only: Q/noncode-check.py reports all 7 changed .py files OK (AST-identical modulo docstrings).
4. No new test file; the 3 new docs are covered by test_doc_signatures (call forms, J1/J3/J10/U+FFFD).
5. **The annotate removal was extended beyond max-critic SKILL.md** to critic-protocol.md (Step 5, soft-limit "accept", worked example), max-build.md step 5, max-iterate.md step 15 and TECHNICAL "Severity Levels". "accept" now means the user accepts the remaining blockers, they are listed in the report, and a new-file save then needs `force=True` (Rule #7). max-verify.md unchanged.
6. Stale severity text fixed in TECHNICAL: "Blocking Behavior" rewritten to `has_blocking_errors` semantics; "Code Validation" lead sentence made exact (standalone report-only; `write_gendsp` does not check its codebox; Layer 5 errors in a `.maxpat` block). Also, under the same decision, TECHNICAL Layer 2 "Severity" (unknown object = warning) and Layer 3 "Severity" (proposed removal, not in-place auto-fix) were corrected, since both contradicted the contract. max-critic package table re-derived from package_critic.py (Bach llll = note; "Object not installed" blocker added).
7. Proven-forms scope = the 12 review §3.6 items only (15 entries: FluCoMa split into 4).
8. Evidence tiers [confirmed] / [bundle] / [code] / [observed]; no tier upgraded beyond the MEM note's wording.
9. Troubleshooting strings verbatim only where a source quotes them; "wording not recorded" otherwise. Sources are CLAUDE.md sections, bundle files, or project + version.
10. shared-capabilities.md "## Reference Docs" after "## Max 9.2"; max-ui-agent "Visual Design Patterns" theme pointer; CLAUDE.md only the Rule #2 line.
11. Experimental labels with the exact texts, placed as specified; the patch-agent and ui-agent Builder API sections stayed byte-identical (test_agent_skills green).
12. README dependencies mirror requirements-dev.txt; system tools listed only where code invokes them (git, cmake + make via the Unix Makefiles generator, `file`, `lipo`, Node/npx for install Option A).
13. Unknown object documented as a non-blocking warning.
14. Theme note from `default.maxtheme` `styledefaults`; states that the contrast critic and aesthetics.py assume legacy defaults until Q26. CLAUDE.md contrast rules untouched.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - correctness] TECHNICAL Layer 2 and Layer 3 "Severity" lines** — Found during Task 1. Both contradicted the contract (Layer 2 said "error" for everything; Layer 3 said invalid cords are removed in place). Corrected under planner decision 6. Commit d80d5352.

**2. [Rule 1 - verify gate] `/Users/` in path examples** — Found during Task 2 verify. The HFS path example (`Macintosh HD:/Users/...`) tripped the private-path negative grep; replaced with `Macintosh HD:/<path>/...`. Commit 45923e19.

**3. [Rule 3 - verify gate] "defer_low" wording** — proven-forms used the refpage's "deferlow"; the verify requires "defer_low". The heading and why-line now use `defer_low` and quote the refpage's "deferlow". Commit 45923e19.

No other deviations.

## Handoffs to Q18

- When CLAUDE.md content moves (genexpr-rules.md, builder docstrings), repoint the shipped pointers to CLAUDE.md "Waveguide loop filters" (max-dsp-agent "Verdict & Fix Reference", dsp_sim classifier/runner/topologies) and Rule #4 "Reading values by index" (patch/ui-agent Builder API, `add_labeled_param_bank` docstring in builders.py).
- CLAUDE.md's own `.planning/` archive citation (review §3.8 bullet 3) is unchanged.
- Optionally add one-line CLAUDE.md pointers to troubleshooting.md and proven-forms.md (only the Rule #2 pointer to severity-contract.md was added).
- Carry the experimental labels into CLAUDE.md's RNBO and M4L sections.

## Out of scope / doc impact, not edited (rule 8)

- max-9.2-changes.md cites the unshipped tests/test_round_trip.py (§3.8 bullet 4).
- Z-order evidence for overlapping panels next to Rule #6 (§3.5).
- README's "no in-framework audio preview or simulation"-style wording versus dsp_sim (not touched).
- Theme-aware contrast code (Q26) and unknown object -> error (Q23).
- `write_gendsp`'s gate does not run GenExpr checks on its own codebox (probe case h); candidate for Q19/Q23.
- critic-protocol.md Step 2 lists only DSP/structure/RNBO/external critics (layout, M4L and package missing); max-critic SKILL.md Critic Loop step 2 omits M4L. Not severity text, so not edited.
- General MEM notes not promoted (planner decision 7), by topic: linked stereo gain~; mc/lcd/bpatcher forms; Jitter GL beyond numdecimalplaces; gen~ loops/Data; live.dial face; textedit/.scl; plain-dial parameter mode; comment wrap; dada.bounce; vector-edge retrigger traps; the contrast false positive.
- Follow-up candidate: a dedicated doc-reference guard test (no shipped file cites a memory-note filename or `.planning/` path).

## Pending user confirmation (rule 9, non-blocking)

- proven-forms entries tagged only [observed] (user could confirm in MAX): trigger types and shared namespace (Ambire v0.5.0), arg-less math (TCI) and int-arg `scale` (minitaur v0.1.9), FluCoMa read/dump chaining (Traces), the `t b` route guard (TCI), kmeans `fitpredict` (intelligent-corpus-remixer v0.2.1), port x-order (ji-harmonizer v0.0.1; code-backed), no global auto-layout, jit.bfg basis (terrain-synth v0.2.x; bundle-backed).
- The experimental RNBO/M4L labels stay until an `rnbo~` patch is opened in MAX and an `.amxd` built by `add_m4l_gen_synth` / `polish_m4l_device` is opened in Live.

## Known Stubs

None.

## Checks

- Stash list unchanged (empty before and after).
- **MEM hash check: unchanged** (45 files, Q/mem.sha256 matches). Nothing was written to MEM.
- Q/objects-check.txt: every object/message named in the new docs resolves in ObjectDatabase or the FluCoMa refpages, except the names the docs say do not exist or must not be used (PD names, `inlet~`/`outlet~`, RNBO/Gen-only names at Max scope, stale bach converters). `fluid.plotter` messages are not in its refpage, so proven-forms prescribes none.
- STATE.md / ROADMAP.md not updated by this executor (quick task; orchestrator handles the docs commit).

## Self-Check: PASSED

- FOUND: .claude/skills/references/severity-contract.md, troubleshooting.md, proven-forms.md
- FOUND commits: d80d5352, 45923e19, 3e3742e6
