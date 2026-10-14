---
phase: quick-261014-fbx
plan: 01
subsystem: docs
tags: [docs, skills, doc-signature-test, gen-patterns, J1, J2, J3, J4, J6, J7, J8, J9, J10, J11, J12, J13]
status: complete
requires: [Q11 d6a4393a (J4), Q6 (J7), Q12 (J5)]
provides:
  - tests/test_doc_signatures.py (doc call-form checker + Q16 regression guards)
  - corrected CLAUDE.md / TECHNICAL.md / README.md / skills / commands / patterns/gen
affects: [agent output for every /max-build and /max-iterate run]
tech-stack:
  added: []
  patterns: [inspect.signature binding of doc snippets, doc guard tests over the union of doc files]
key-files:
  created:
    - tests/test_doc_signatures.py
  modified:
    - CLAUDE.md
    - TECHNICAL.md
    - README.md
    - patterns/gen/INDEX.md
    - patterns/gen/{ramps,dsp,random,smoothing,buffer}/*.gendsp (10 files)
    - .claude/commands/max-iterate.md
    - .claude/skills/references/{shared-capabilities,ui-presets}.md
    - .claude/skills/max-{patch,dsp,js,ui,rnbo}-agent/SKILL.md, max-patch-agent/BOUNDARIES.md
    - .claude/skills/max-{router,lifecycle}/SKILL.md, max-lifecycle/references/project-structure.md
decisions:
  - "J10: missing config.json means core-only (allowed_packages=[]); /max-config and /max-version references removed, no commands added"
  - "J12: whole patterns/gen library rewritten to the proven-safe construct set (10 files), pending MAX compile confirmation"
  - "J1: TECHNICAL generate_js_script bullet documents messagename/arrayfromargs; codegen.py stub left to Q31"
metrics:
  duration: ~13 min
  completed: 2026-10-14
actuals:
  tokens: 62000
  tasks: 3
  commits: 3
plan_head_before: fc1c4f9700a7eceb93fdbe52cb083f06403b477a
plan_head_after: f361aeaeb850e2d38983c2f3ff7f19bfe2404922
---

# Phase quick-261014-fbx Plan 01: Q16 doc bugs (J1-J4, J6-J13) and doc-signature test Summary

The docs agents read no longer show call forms that raise, `replace_box` connection claims, parameterized js `anything` handlers, 0-1 values into `gain~`, nonexistent FluCoMa/BEAP/effect objects, untriggered fan-out, a config STOP, or an `io_rule` field. A 407-snippet `inspect.signature` checker keeps the call forms honest.

## Figures

- **Base:** `fc1c4f97` (hard check passed: contains e9852567; soft check passed: contains Q14/Q15). README/TECHNICAL counts were computed on this full base, so no caveat.
- **Baseline pytest:** 3251 passed, 1 xfailed, 1 xpassed, 29 warnings (65.2 s).
- **Final pytest:** 3343 passed, 1 xfailed, 1 xpassed, 29 warnings (68.3 s). That is +92, all in `tests/test_doc_signatures.py`.
- **New tests per task:** Task 1: 57 (7 bad-form + 10 good-form self-tests, coverage floor, 38 per-doc tests, replace_box guard). Task 2: 11. Task 3: 24 (19 gen-pattern params + 5).
- **Doc scanner:** 407 call snippets checked across 38 doc files. The floor is 200; RED run had 396.
- **Q/counts.txt (planner decision 7):**
  - LOC: 22,236 physical lines in `src/maxpat/**/*.py`, written as ~22,200.
  - Tests: 3,345 collected (`pytest --collect-only -q`).
  - Test files: 77 (`tests/**/test_*.py`).
  - Objects: 3,445 (1,948 core + 1,497 package), 29 packages. Unchanged.
- `git status --porcelain` was unchanged across every pytest run. Stash list unchanged (empty). No diff under `patches/` or `src/`.

## Finding table

| ID | Status | Files | Guard test |
|----|--------|-------|-----------|
| J1 | Fixed | CLAUDE.md, max-js-agent SKILL.md, TECHNICAL.md | test_js_anything_handler_uses_messagename |
| J2 | Fixed | CLAUDE.md (Gain safety), TECHNICAL.md (DSP critic MIDI row) | test_gain_rule_scoped_to_multiply_tilde |
| J3 | Fixed | max-patch-agent SKILL.md, max-dsp-agent SKILL.md, patterns/gen/INDEX.md, shared-capabilities.md, max-iterate.md, TECHNICAL.md | test_doc_call_forms_match_signatures, test_checker_flags_bad_form, test_replace_box_docs_point_to_safe_variant |
| J4 | Already fixed (Q11 d6a4393a). CLAUDE.md says 2 inlets / 1 outlet, which matches `compute_io_counts("spectroscope~", [])` = (2, 1). Lock test was green from the start, as planned | none | test_spectroscope_claim_matches_db |
| J5 | Done in Q12 (out of scope) | — | — |
| J6 | Fixed (`scale 0. 127. 0. 1.` for float sources) | CLAUDE.md | test_gain_rule_scoped_to_multiply_tilde |
| J7 | Already fixed (Q6). All six "Output Protocol (Edited Patches)" blocks say "never clears existing midpoints" (grep count = 6) | none | Task 2 verify grep |
| J8 | Fixed | max-dsp-agent SKILL.md, max-patch-agent BOUNDARIES.md | test_dsp_templates_use_db_objects, test_flucoma_templates_use_fit_predict |
| J9 | Fixed (`t f f`, right outlet to the number box, left outlet to the gen~ message) | ui-presets.md | test_ui_presets_dial_chain_uses_trigger |
| J10 | Fixed (core-only) | max-router, max-lifecycle, project-structure.md, patch/dsp/ui/rnbo agent SKILL.md | test_no_references_to_missing_commands, test_missing_config_is_core_only |
| J11 | Fixed | CLAUDE.md, TECHNICAL.md | test_variable_io_docs_point_to_overrides, test_technical_io_formula_table_matches_code |
| J12 | Fixed (rewrites pending MAX confirmation) | 10 patterns/gen .gendsp | test_gen_patterns_use_safe_constructs |
| J13 | Fixed | README.md, TECHNICAL.md | test_readme_patch_table_lists_every_project, test_docs_have_no_replacement_characters, test_readme_js_engine_wording, test_technical_spacing_table_matches_code, test_technical_documents_every_critic_module |

## Extra raising forms found by the scanner (beyond the five J3 bullets)

All of these are the same class as J3 and were fixed in Task 1:
- TECHNICAL: `add_bpatcher(filename, args, x, y)`, `find_box` / `find_boxes` given positionals (their parameters are keyword-only), `analyze(patcher)` (the method takes no argument), and `insert_into_connection` given a patchline. `modify_box(box, **attrs)` did not raise, but it was rewritten to the real keyword-only form as the plan directs.
- max-patch-agent: `add_subpatcher(name, inlets, outlets, inlet_comments, outlet_comments)`, where the comments land on x/y. Also `add_node_script(...)` and `add_js(...)`, which put a positional after a keyword and so could not be parsed.
- The "Patch Construction" prose told agents to call the Box constructor or the `__new__` bypass. It now says `add_box` plus the structural builders.

**Checker refinement during RED (1 false positive):** `.claude/commands/max-build.md:43` wrote `files=[...all generated file paths...]`, a prose placeholder that cannot be parsed. The checker now reduces `...text...` placeholders to `...` before parsing. A good-form self-test was added, and max-build.md was not edited. There were no other false positives.

## Decisions taken (planner decisions 1-10)

1. **J10: no commands added.** A missing config.json means core-only. The router passes `allowed_packages=[]` and continues, telling the user once that package objects stay disabled. The patch, dsp, ui and rnbo config steps each say "None -> `allowed = []` (core-only), never None". Evidence: none of the 18 config-less projects uses a package object, so behaviour is unchanged. No code changed; `test_project.py` still pins the None return.
2. **J12: the whole library was rewritten to the proven-safe set**, not re-verified, because an executor can't verify in MAX. See the pending list below.
3. **J4 and J7 were already fixed.** Nothing was rewritten; J4 gets a lock test and J7 a grep check.
4. **J1, TECHNICAL wording:** the bullet now says handler bodies read `messagename` and `arrayfromargs(arguments)`. `codegen.py` was not edited, so it still emits a named `anything` parameter. Q31 owns that.
5. **Scanner scope** includes README.md and patterns/gen/INDEX.md. The extra raising forms listed above were fixed.
6. **Guard scope:** the guards scan every doc file. J8 alone is pinned to its two files.
7. **Counts** were computed live after all tests existed. See Figures.
8. **Critic tables come from the current code:**
   - Fan-out is a blocker when branches reconverge on one box at different inlets, otherwise a warning.
   - Bach llll typing is a note.
   - New `### M4L Critic (m4l_critic.py)` section; "six" became "seven" in TECHNICAL, the README feature bullet, the README "How It Works" paragraph and the TECHNICAL architecture diagram line.
   - **Extension:** the same derivation corrected the DSP critic table. Gain staging is a blocker in `dsp_critic.py`, not a warning. The "Audio rate consistency" row was dropped because Q3/E2 removed that check. The MIDI-range row (a J2 line) was not touched again.
   - The layout table also lists contrast and presentation coverage, because `review_layout` runs those checks.
   - The package table lists BEAP missing-output, missing-VCA and object-not-installed (a blocker).
9. **J8 verification sources:**
   - Object names come from ObjectDatabase. All template port indices are within the DB I/O counts.
   - FluCoMa methods and attributes come from the installed `docs/*.maxref.xml`. Connection shapes come from `help/*.maxhelp`, e.g. `fluid.list2buf` -> `knearest $2` / `predictpoint $2`, `route fit predictpoint`, and `button` -> `fluid.buf*~` -> `button`.
   - BEAP port roles come from the module patchers' presentation labels plus the BEAP help patches. Examples: Sequencer outlet 0 = CV feeds `bp.FM`; outlet 1 = Gate. The LFO's sine, ramp and square outputs are ×5 / ×10 → ±5 V.
   - Unverified claims were removed, including default numbers such as numbands 40, `@components 2-10`, mlpclassifier defaults, "ASYNC", and LFO "0-5V".
   - `fluid.stats @numderivs` was wrong (it belongs to `fluid.bufstats~`) and was replaced by `@history`. "reset" became `clear`.
10. **Extra edit locations** were made as planned: Patch Construction prose, the four config lines, and the Community DSP FluCoMa names.
    - **Deviation:** the plan said no PACKAGES.md exists, but `.claude/max-objects/PACKAGES.md` does exist, is tracked, and has the canonical BEAP templates. So the BEAP template sentence now points to `.claude/max-objects/PACKAGES.md` (full path) *and* to the BEAP section of max-patch-agent SKILL.md, instead of dropping the PACKAGES.md reference.

## Deviations from Plan

1. **[Rule 1 - Bug] PACKAGES.md pointer** (Task 2): the plan's premise was wrong. The pointer was made explicit rather than removed (see decision 10). Commit a821f604.
2. **[Rule 1 - Bug] TECHNICAL DSP critic table** (Task 3): the stale gain-staging severity and the removed audio-rate row were corrected from code (see decision 8). Commit f361aeae.
3. **[Rule 3] Scanner prose-ellipsis refinement** (Task 1), described above. Commit 6dafc9cf.
4. **Edit method:** doc edits used scoped exact-string replacements through a scratchpad helper that asserts each match occurs exactly once (not the Edit tool). The DSP template block was one bounded section replacement. No whole-file rewrites.

There were no allowlisted items: no committed patch produced a finding, and the new tests never read `patches/**` contents except for the directory listing.

## Pending user confirmation in MAX (human-verify, non-blocking)

1. **The 10 rewritten patterns/gen files compile.** Each diff is the single `code` line; old and new pairs are in `Q/j12-rewrites.txt`. `validate_genexpr` reports nothing new for any of them.
   - `patterns/gen/ramps/adsr-envelope.gendsp`: else-if chain nested; `phase == N` became range tests; `sr` alias removed.
   - `patterns/gen/ramps/ar-envelope.gendsp`: `sr` alias removed.
   - `patterns/gen/ramps/smooth-ramp.gendsp`: `sr` alias removed.
   - `patterns/gen/dsp/noise-generator.gendsp`: else-if nested.
   - `patterns/gen/dsp/compressor.gendsp`: `sr` alias removed.
   - `patterns/gen/dsp/multi-tap-delay.gendsp`: `sr` alias removed.
   - `patterns/gen/random/random-walk.gendsp`: `sr` alias removed.
   - `patterns/gen/smoothing/lag-processor.gendsp`: `sr` alias removed.
   - `patterns/gen/buffer/buffer-player.gendsp`: `peek(buf, read_pos, 0)`.
   - `patterns/gen/buffer/buffer-recorder.gendsp`: `poke(buf, audio_in, pos, 0)`.

   **How to check:** add `patterns/gen` to Max's File Preferences search path, or copy a file next to a scratch patch. Create `gen~ <name>` and confirm the console shows no compile error. Spot-check:
   - adsr-envelope: gate on/off traces A/D/S/R.
   - noise-generator: `type 0/1/2` switches white/pink/brown.
   - buffer-player and buffer-recorder: read and write channel 1.
2. **Template details marked "(role unverified -- confirm in MAX)":**
   - FluCoMa real-time chain rows 4-5: which `fluid.normalize~` reply should trigger `fluid.buf2list` after `transformpoint`. No help patch uses `transformpoint`.
   - FluCoMa offline pipeline: identifier bookkeeping for `addpoint`.
3. **Optional:** the `gain~` slider-position guidance is already user-confirmed via memory (gain~ linked stereo / minitaur notes).

## Out of scope / doc impact, not edited (rule 8)

- `dsp_critic.py` suggestion text still recommends `scale 0 127 0. 1.`. That is fine for MIDI ints, but float sources need `scale 0. 127. 0. 1.`. This is a code change for a later task.
- `codegen.py` still emits a named `anything` parameter (Q31).
- `patterns/gen/INDEX.md` still has its "External reverb~" wording.
- Unresolved ABL-style names in `max-9.2-changes.md`.
- Q15's pending doc impacts: add_m4l_gen_synth feeds both plugout~ inlets, and the TECHNICAL builder row.
- README describes `patches/` while the release archive export-ignores it.
- **New:** `.claude/max-objects/PACKAGES.md` BEAP templates wire `bp.LFO 0 -> bp.LPF 1 (CV2 cutoff)`. bp.LPF inlet 1 is CV1 (1v/oct) and CV2 is inlet 2; the BEAP help wires LFO -> LPF inlet 2. Not in this plan's files.
- **New:** TECHNICAL's validation-layer table (line ~414, "Missing gain staging ... warning") describes the validator, not the critic, and was left alone.

## Known Stubs

None.

## Threat Flags

None. These are docs and a read-only test. T-fbx-01 is mitigated: the `*~` 0-1 MUST rule and the critic sentence remain. T-fbx-02 is mitigated: `allowed_packages=[]` is pinned in the router and the four specialists.

## Commits

- 6dafc9cf docs: doc call forms match real signatures, replace_box_safe guidance, doc-signature test (Q16)
- a821f604 docs: js anything() pattern, gain~ slider positions, DB-real FluCoMa/BEAP templates, dial trigger, core-only config, variable_io_rules (Q16)
- f361aeae docs: gen~ patterns on proven-safe constructs; README/TECHNICAL tables and counts match the repo (Q16)

## Self-Check: PASSED

- tests/test_doc_signatures.py exists; 92 tests are green.
- Commits 6dafc9cf, a821f604 and f361aeae exist on main.
- Q/base-sha.txt, stash-list-before.txt, baseline-pytest.txt, red-task1/2/3.txt, j12-rewrites.txt, counts.txt and final-pytest.txt exist (untracked, not staged).
