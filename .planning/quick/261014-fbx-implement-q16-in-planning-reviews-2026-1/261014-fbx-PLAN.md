---
phase: quick-261014-fbx
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - tests/test_doc_signatures.py
  - CLAUDE.md
  - TECHNICAL.md
  - README.md
  - patterns/gen/INDEX.md
  - patterns/gen/ramps/adsr-envelope.gendsp
  - patterns/gen/ramps/ar-envelope.gendsp
  - patterns/gen/ramps/smooth-ramp.gendsp
  - patterns/gen/dsp/noise-generator.gendsp
  - patterns/gen/dsp/compressor.gendsp
  - patterns/gen/dsp/multi-tap-delay.gendsp
  - patterns/gen/random/random-walk.gendsp
  - patterns/gen/smoothing/lag-processor.gendsp
  - patterns/gen/buffer/buffer-player.gendsp
  - patterns/gen/buffer/buffer-recorder.gendsp
  - .claude/commands/max-iterate.md
  - .claude/skills/references/shared-capabilities.md
  - .claude/skills/references/ui-presets.md
  - .claude/skills/max-patch-agent/SKILL.md
  - .claude/skills/max-patch-agent/BOUNDARIES.md
  - .claude/skills/max-dsp-agent/SKILL.md
  - .claude/skills/max-js-agent/SKILL.md
  - .claude/skills/max-ui-agent/SKILL.md
  - .claude/skills/max-rnbo-agent/SKILL.md
  - .claude/skills/max-router/SKILL.md
  - .claude/skills/max-lifecycle/SKILL.md
  - .claude/skills/max-lifecycle/references/project-structure.md
autonomous: true
requirements: [J1, J2, J3, J4, J6, J7, J8, J9, J10, J11, J12, J13]

estimate:
  tokens: 170000
  raw_tokens: 170000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "tests/test_doc_signatures.py scans CLAUDE.md, TECHNICAL.md, README.md, patterns/gen/INDEX.md, every .claude/skills/**/*.md and every .claude/commands/*.md. It checks at least 200 Python call snippets of public src.maxpat API names against inspect.signature (keyword names, positional arity, a positional name that belongs to another parameter, an obvious type mismatch such as a Box or Patcher passed where str or dict is annotated) and reports zero findings. Its self-tests show it flags each of the five J3 raising forms and accepts the corrected forms."
    - "Every corrected call form in the docs runs: add_box(name, args), insert_into_connection(src, dst, name, args), replace_box_safe(box, name, args=...), apply_layout(patcher, options=...) and save_patch_roundtrip(patcher.to_dict(), path, ...) execute without TypeError."
    - "No doc says replace_box keeps or remaps connections. shared-capabilities.md, max-iterate.md and TECHNICAL.md point to replace_box_safe (auto-rewire only on matching I/O, otherwise result.orphaned per Rule #8)."
    - "Every doc line that lists js handler functions documents anything() with messagename and arrayfromargs(arguments). No doc documents an anything handler with a named parameter (J1)."
    - "The 0.0-1.0 gain rule names the *~ multiplier only. gain~ is documented as taking int slider positions (0 to size-1, default 0-157), and float sources are normalized with scale 0. 127. 0. 1. (J2, J6)."
    - "Every object token in max-dsp-agent SKILL.md and max-patch-agent BOUNDARIES.md resolves in ObjectDatabase. The FluCoMa templates use the ~ names and fit / predict-family messages verified against the installed FluCoMa refpages. The BEAP templates use bp.LFO, bp.LPF or bp.MMF, and bp.Sequencer (J8)."
    - "The ui-presets dial chain fans out through a t f f trigger (J9)."
    - "No doc references a slash command that has no .claude/commands file. A missing config.json is documented as core-only (allowed_packages=[], never None) in the router, lifecycle, project-structure and the four specialist config steps (J10)."
    - "No doc mentions a per-object io_rule field. CLAUDE.md and TECHNICAL.md point to overrides.json variable_io_rules, src/maxpat/io_resolvers.py and db.compute_io_counts. TECHNICAL's formula table equals SUPPORTED_IO_FORMULAS (minus the empty string) plus fixed:N (J11)."
    - "Every patterns/gen codebox is spaces-only, has no else-if chain, no == or != inside an if condition, no local alias of samplerate, and every peek/poke carries an explicit channel. validate_genexpr reports nothing new, and each .gendsp diff is the single code line (J12)."
    - "README's patch table lists exactly the project directories under patches/ (31 at planning). No doc contains U+FFFD. README names the js Legacy Engine instead of calling js objects V8. README and TECHNICAL counts are recomputed live. TECHNICAL documents every critic module (seven, including M4L) with severities taken from the code, and its spacing table equals defaults.py and layout.py (J13)."
    - "J4 (spectroscope~ is 2 inlets / 1 outlet) and J7 (edit-path finalize guidance) were already fixed by Q11 and Q6. J4 is locked by a test and J7 is checked by grep; both are recorded in SUMMARY."
    - "The full suite is green: the Step-0 baseline plus only the new tests, with 1 xfailed / 1 xpassed unchanged. No patches/** or src/** file changes. tests/test_doc_signatures.py parses under Python 3.10."
  artifacts:
    - path: "tests/test_doc_signatures.py"
      provides: "Doc call-form checker with self-tests, plus the Q16 doc regression guards (J1, J2/J6, J3, J4, J8, J9, J10, J11, J12, J13)"
      contains: "def test_doc_call_forms_match_signatures"
    - path: ".claude/skills/references/shared-capabilities.md"
      provides: "Editing Functions and Layout Options with real signatures; replace_box_safe guidance"
      contains: "replace_box_safe"
    - path: "CLAUDE.md"
      provides: "js anything() pattern, gain rule scoped to *~ plus gain~ slider positions, Variable I/O section pointing to variable_io_rules"
      contains: "variable_io_rules"
    - path: ".claude/skills/max-router/SKILL.md"
      provides: "Missing config.json means core-only; no STOP"
      contains: "allowed_packages=[]"
    - path: "README.md"
      provides: "31-project patch table, fixed js wording, no garbled characters, live counts"
      contains: "**amplitude-follower**"
    - path: "TECHNICAL.md"
      provides: "Corrected API tables, critic tables including the M4L critic, spacing table, Variable I/O Rules"
      contains: "m4l_critic.py"
    - path: "patterns/gen/ramps/adsr-envelope.gendsp"
      provides: "ADSR codebox rewritten to the proven-safe construct set"
      contains: "samplerate"
  key_links:
    - from: "tests/test_doc_signatures.py"
      to: "src/maxpat (Patcher, ObjectDatabase, module functions)"
      via: "inspect.signature binding of every extracted doc call snippet"
      pattern: "inspect.signature"
    - from: "tests/test_doc_signatures.py"
      to: "src/maxpat/db_lookup.py"
      via: "TECHNICAL formula table compared with SUPPORTED_IO_FORMULAS; template tokens checked with ObjectDatabase.exists"
      pattern: "SUPPORTED_IO_FORMULAS"
    - from: "tests/test_doc_signatures.py"
      to: "src/maxpat/defaults.py and src/maxpat/layout.py"
      via: "TECHNICAL Spacing Constants table compared with V_SPACING, H_GUTTER, _COMPONENT_GAP, _START_X/_START_Y"
      pattern: "_COMPONENT_GAP"
    - from: ".claude/skills/max-router/SKILL.md"
      to: "src/maxpat/project.py load_project_config"
      via: "None (no config.json) is mapped to allowed_packages=[] before dispatch"
      pattern: "allowed_packages=\\[\\]"
    - from: "README.md patch table"
      to: "patches/ directory listing"
      via: "test_readme_patch_table_lists_every_project"
      pattern: "patches"
---

<objective>
Implement Q16 from `.planning/reviews/2026-10-11-fix-plan.md`: review findings J1-J4 and J6-J13, plus the new doc-signature test. After this, the docs that agents read no longer tell them to:
- write call forms that raise;
- strip connections with `replace_box`;
- write js `anything` handlers that never match;
- send 0-1 values into `gain~`;
- use objects and messages that do not exist;
- fan out without a trigger;
- stop on a missing config;
- look for an `io_rule` field that no object has.

The gen~ pattern library uses only the proven-safe construct set. README and TECHNICAL match the repo.

Purpose: J1-J13 are documentation errors that make the agent produce broken patches. A doc-signature test stops call-form drift from coming back.

Output:
- `tests/test_doc_signatures.py`, the call-form checker plus regression guards.
- Corrected CLAUDE.md, TECHNICAL.md, README.md, skills, commands and `patterns/gen/INDEX.md`.
- 10 rewritten `patterns/gen` codeboxes.
- SUMMARY.md listing the items that need confirmation in MAX.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@CLAUDE.md

Spec: `.planning/reviews/2026-10-11-fix-plan.md`. Read the "### Q16" section and "Rules for every task". Evidence: `.planning/reviews/2026-10-11-repo-review.md`, section "### 1J", rows J1-J13. J5 is NOT in scope; it was done in Q12.

**Line numbers in the spec and the review (e.g. CLAUDE.md:273) have drifted since 2026-10-11. Find every edit location by its content (the heading or quoted text named in each task), never by line number.**
</context>

<rules>
These are copied from the fix plan's "Rules for every task" and bind every task.

1. Read the referenced finding IDs in the review report first. They contain the evidence and the expected fix.
2. Write each regression test **first**. It must reproduce the finding (red) before the fix makes it green. J4 is the exception: it was already fixed by Q11, so its lock test is green from the start. Record that in SUMMARY.
3. **Never edit committed patch files** (`patches/**/*.maxpat|.gendsp|.maxhelp|.js`). They are user-confirmed baselines, and the integration tests depend on them. If one produces a new finding:
   - false positive: fix the checker;
   - true positive in a committed patch: allowlist it with a written reason and list it in SUMMARY.md.
4. Run `python3 -m pytest -q -p no:cacheprovider` before and after. The suite must be fully green.
5. Never `git stash`. Never `git add -A` or `git add .`. Stage explicit paths only.
6. Code must work on Python 3.10.
7. Don't widen scope. If the fix needs a decision that neither the report nor `<planner_decisions>` below makes, stop and ask with multiple-choice options.
8. Edit CLAUDE.md, skills or TECHNICAL.md only where this plan says to (Q16 is the task that says to). List any other doc impact in SUMMARY.md.
9. In SUMMARY.md, flag anything that needs the user to confirm in MAX.

Additions for this execution environment:
- **Q** means `.planning/quick/261014-fbx-implement-q16-in-planning-reviews-2026-1`. Create it in the worktree if it is absent. Step-0 files, RED captures and final captures go in Q. They stay untracked and are never staged.
- **Worktree base.** At planning, local main = `fc1c4f97` (contains Q14 and Q15) and origin/main = `e9852567` (Q13). Between them, the only file this plan edits that differs is CLAUDE.md. Its hunks are Q14's DB-section lines, which do not overlap any Q16 edit. Either base works for the doc edits.
  - **Hard precondition:** `git merge-base --is-ancestor e9852567 HEAD` succeeds. If it fails, HALT and report "worktree base older than Q13".
  - **Soft check:** if `git merge-base --is-ancestor fc1c4f97 HEAD` fails, proceed, but state in SUMMARY that the README/TECHNICAL test counts were computed on a base without the Q14/Q15 tests, and give the recompute commands from Task 3 so they can be refreshed after merge.
- **Step 0:**
  - Record `git rev-parse HEAD` in Q/base-sha.txt.
  - Record `git stash list` in Q/stash-list-before.txt.
  - Run the full suite into Q/baseline-pytest.txt. Expected: **3251 passed, 1 xfailed, 1 xpassed, 29 warnings** at `fc1c4f97` (about 65 s), or **3171 passed** with the same 1/1/29 at `e9852567`. Record a different figure; do not fix it.
- **Edit scope.** Only the `files_modified` paths may change, and each only in a task that lists it. Doc edits use scoped `Edit` replacements, never whole-file `Write`. The only exception is the new test file.
- **Commits.** One commit per task, each message ending `(Q16)`: `git add -- <task files>`, then `git commit -m "..." -- <task files>`. Never `git push`.
- **Tests never write to the repo.** Each verify compares `git status --porcelain` before and after the pytest run.
- **Python 3.10.** Avoid 3.11+ APIs (`tomllib`, `typing.Self`, `except*`, `match`, `Path.walk`, `itertools.batched`). CI runs 3.10/3.12 without Max. The new tests must pass with only the repo (DB, docs, patches); none may read the Max bundle or the FluCoMa package.
- **Shell.** The shell is zsh, so wrap multi-step gates in `bash -c '...'`. Throwaway scripts go in `mktemp -d`, never in the repo (CLAUDE.md Rule #5).
- **Never quote a removed wrong form in the new doc text.** A sentence such as "not `<old form>`" would re-trip the guards. Describe what is wrong by concept instead.
</rules>

<planner_decisions>
These are decisions the fix plan does not spell out, recorded so the executor does not need to stop.

1. **J10: remove the references; a missing config.json means core-only.** The review offers "add the commands, or treat a missing config as core-only" and recommends neither. The quick-task constraint picks the smaller scope.
   - Evidence at planning: none of the 18 projects without config.json (FDNVerb, disintegrate, gen-eq, gong-model, granularsynthtest, kicksynth, minitaur, mixer, performancepatchtest, reverse-delay, rhythmic-sampler, scala-synth, stereo-feedback-delay, stutter, tape-wobble, terrain-synth, timestretch, wormhole) has a package object in its generated patches. Core-only therefore changes no existing project's behavior.
   - `Patcher(allowed_packages=None)` means allow everything (patcher.py `allowed_packages` docstring), and `load_project_config` / `get_allowed_packages` return None when the file is missing. "Core-only" therefore only holds if every reader maps None to `[]`. So the four specialist config steps (patch, dsp, ui and rnbo agent SKILL.md, each a single line naming `load_project_config()`) are edited too, as well as the router, lifecycle and project-structure.
   - No code changes: `test_project.py` pins the None return.
2. **J12 scope is the whole `patterns/gen` library, rewritten to the proven-safe construct set.** J12's fix ("re-verify in MAX or rewrite to the proven-safe construct set") targets the library. An executor cannot verify in MAX, so it rewrites, and SUMMARY flags the result for MAX confirmation. A scan at planning found these 10 files:
   - `else if`: adsr-envelope (×3), noise-generator;
   - `==` in an if condition: adsr-envelope;
   - a `sr = samplerate;` alias used only in Param-only expressions: adsr-envelope, ar-envelope, smooth-ramp, compressor, multi-tap-delay, random-walk, lag-processor. This is exactly the CLAUDE.md "No local aliases in Param-only expressions" compile failure;
   - peek/poke without an explicit channel: buffer-player, buffer-recorder.

   Each rewrite preserves the semantics. Every expression is a leaf, Param × samplerate, so writing `samplerate` directly follows the kicksynth pattern; no `History one(1)` de-hoist is needed.
3. **J4 and J7 are already fixed.** J4: Q11 commit d6a4393a corrected the CLAUDE.md spectroscope~ claim. It now says 2 inlets / 1 outlet, and `db.compute_io_counts("spectroscope~", [])` is (2, 1). J7: Q6 made `finalize_patch(is_new=False)` keep midpoints, and all six "Output Protocol (Edited Patches)" blocks already say "never clears existing midpoints". Task 2 adds a J4 lock test and a J7 grep check. Nothing is rewritten.
4. **J1, TECHNICAL wording.** The TECHNICAL `generate_js_script` bullet describes codegen, and `codegen.py` still emits a named `anything` parameter until Q31. The bullet therefore states how handler bodies must read the message (`messagename`, `arrayfromargs(arguments)`) without claiming the generated stub has changed. Do not edit `codegen.py`. SUMMARY notes that Q31 owns it.
5. **Doc-signature test scope.** The spec's file set (CLAUDE.md, skills, commands, TECHNICAL) is extended with README.md and `patterns/gen/INDEX.md`; INDEX.md is a J3 location. The scanner also flags call forms that raise beyond the five J3 bullets:
   - TECHNICAL's `find_box` / `find_boxes` (keyword-only parameters), `analyze(patcher)` (a method with no argument), `add_bpatcher(filename, args, x, y)` and `modify_box(box, **attrs)`;
   - patch-agent's `add_subpatcher` (comments landing on x/y), and `add_node_script` / `add_js` (positional after keyword, unparseable).

   These are the same J3 class, and the spec'd test must pass, so Task 1 fixes them.
6. **Guard tests are in one file and scan the union of docs where they can.** The J1, J2/J6, J3-wording, J4, J10 and J11 guards scan every doc file, not one fixed file. Q18 will then move text out of CLAUDE.md without breaking them. J8 is pinned to its two named files, because other docs deliberately name nonexistent objects, e.g. CLAUDE.md "No `inlet~` / `outlet~`" and the ABL names in max-9.2-changes.md.
7. **J13 counts are computed live, last, in Task 3,** after every new test exists. The methods:
   - LOC = physical lines of `src/maxpat/**/*.py` (excluding `__pycache__`), rounded to the nearest 100 and written with `~`. At planning: 22,236.
   - Tests = the `pytest --collect-only -q` total.
   - Test files = the count of `tests/**/test_*.py`.
   - Objects = the sum of the 7 domain `objects.json` files plus every `packages/*/objects.json`. At planning: 3,445, unchanged.
   - Critics = the number of critic modules `review_patch` invokes. At planning: 7. Q4 wired the M4L critic.
8. **J13 critic tables are derived from the code as it is now, not from the review.** Q3 changed severities after the review: fan-out is a blocker when branches reconverge on one box at different inlets and a warning otherwise, and Bach llll typing is a note. Q4 wired the M4L critic, so TECHNICAL gains an `### M4L Critic (`m4l_critic.py`)` section, and the "six critics" sentences become seven.
9. **J8 verification sources (Rule #1).**
   - Object names and I/O: `ObjectDatabase`.
   - FluCoMa message and attribute names: `<method name='...'>` and `<attribute name='...'>` in `$HOME/Documents/Max 9/Packages/FluidCorpusManipulation/docs/<object>.maxref.xml`. Connection shapes come from the matching `help/<object>.maxhelp`.
   - BEAP module port roles: `/Applications/Max.app/Contents/Resources/C74/packages/BEAP/Help/<module>.maxhelp` and the module patchers under `.../BEAP/clippings/BEAP/`. The DB has I/O counts but mostly empty port descriptions.
   - Any attribute, message or port role that cannot be confirmed from these sources is removed, or kept with "(role unverified — confirm in MAX)" and listed in SUMMARY. Never guess.
10. **Extra edit locations, beyond the spec's line list, needed for consistency (rule 8):**
    - max-patch-agent SKILL.md "Patch Construction" prose: it tells agents to construct `Box` directly, which contradicts the fixed call forms;
    - the four specialist config lines (decision 1);
    - the dsp SKILL.md "Community DSP Packages" FluCoMa names (same file as J8, caught by the J8 guard);
    - the dangling "PACKAGES.md" reference inside the BEAP template text being rewritten. No PACKAGES.md exists; point to the BEAP section of max-patch-agent SKILL.md.
11. **Security:** ASVS L1, block on high (config has no security keys; absent means enabled). See `<threat_model>`. No package installs.
</planner_decisions>

<observed_facts>
Measured at planning: HEAD `fc1c4f97`, Max 9.2.0 installed. Full suite: 3251 passed, 1 xfailed, 1 xpassed, 29 warnings (65.6 s).

**Real signatures** (`inspect.signature`; `self` omitted):
- `Patcher.add_box(name, args=None, x=0.0, y=0.0, skip_overlap_check=False) -> Box`
- `Box(name, args=None, box_id='obj-0', db=None, x=0.0, y=0.0, allowed_packages=None)`
- `Patcher.replace_box(old_box, new_name, *, args=None)`
- `Patcher.replace_box_safe(old_box, new_name, *, args=None, rewire='auto')`
- `Patcher.insert_into_connection(source, dest, name, args=None) -> EditResult`
- `Patcher.modify_box(box, *, args=None, position=None, color=None, extra_attrs=None)`
- `Patcher.find_box(*, id=None, name=None, maxclass=None, text=None, recursive=False)`; `find_boxes` has the same keywords.
- `Patcher.analyze() -> str`
- `Patcher.add_subpatcher(name, inlets=1, outlets=1, x=0.0, y=0.0, inlet_comments=None, outlet_comments=None)`
- `Patcher.add_bpatcher(filename=None, embedded=False, args=None, x=0.0, y=0.0, width=None, height=None, numinlets=1, numoutlets=1, object_name=None)`
- `Patcher.add_node_script(filename, code=None, num_outlets=2, x=0.0, y=0.0)`
- `Patcher.add_js(filename, code=None, num_inlets=1, num_outlets=1, x=0.0, y=0.0)`
- `apply_layout(patcher, options=None)`
- `save_patch_roundtrip(patch_dict, path, original_text=None, *, force=False)`
- `write_gendsp(code, path, num_inputs=None, num_outputs=None, *, force=False)`
- `finalize_patch(patcher, is_new=True)`; `MemoryEntry(pattern, domain, observed, context, rule)`

**Smoke run of the corrected forms** (passes with `python3 -W error`): `add_box("gen~", ["smooth-ramp"])`, `insert_into_connection(c, d, "*~", ["0.5"])`, `replace_box_safe(c, "phasor~", args=["220"])` (orphaned == []), and `apply_layout(p, options=LayoutOptions())`.

**A scanner prototype** (the design in Task 1) checked 386 call snippets and found 20 findings in 5 files:
- TECHNICAL.md (7), in the Patcher methods table and the Read/Write and Patch Analysis sections:
  - `add_bpatcher(filename, args, x, y)`;
  - `find_box(query, by, recursive)`, `find_boxes(...)`;
  - the `insert_into_connection` row taking a patchline;
  - the 3-positional `replace_box` row;
  - `save_patch_roundtrip` given a Patcher;
  - `analyze(patcher)`.
- patterns/gen/INDEX.md (2) and max-dsp-agent SKILL.md "Using External .gendsp Patterns" (2): the Box-constructed-then-added gen~ example.
- max-patch-agent SKILL.md "Key Functions" (6): the Box constructor bullet, the add-a-Box bullet, add_subpatcher, the apply_layout keyword, add_node_script and add_js.
- shared-capabilities.md (3): the "Layout Options" apply_layout keyword, plus the "Editing Functions" insert_into_connection and replace_box bullets.

It had zero false positives after three refinements:
- use `bind_partial`, so prose mentions such as `finalize_patch(is_new=True)` pass;
- in def-mode, drop bare `...` items, so `write_gendsp(code, path, ..., *, force=False)` passes;
- strip `#` comments, so the TECHNICAL MemoryEntry block parses.

**The replace_box wording** that claims connections survive: the shared-capabilities "Editing Functions" bullet, the TECHNICAL methods-table row, and max-iterate.md step 11 "Surgical edit" (plus step 14's bullet list).

**Unresolved object tokens** (`db.exists` False, PD objects and "Gen~" excluded):
- max-dsp-agent SKILL.md: bp.LFOscillator, bp.SVF, bp.Steppr, chorus~, flanger~, phaser~, reverb~, melbands~, fluid.bufmelbands, fluid.bufmfcc, fluid.bufnmf, fluid.bufstats, fluid.dataset, fluid.kdtree, fluid.loudness, fluid.mfcc, fluid.mlpclassifier, fluid.normalize, fluid.pitch;
- max-patch-agent BOUNDARIES.md: filter~.

**The DB has:**
- FluCoMa: fluid.melbands~/mfcc~/pitch~/loudness~ (1/2), fluid.stats (1/2, no ~), fluid.normalize~, fluid.dataset~, fluid.kdtree~, fluid.mlpclassifier~ (each 1/2), fluid.bufnmf~/bufstats~ (1/2), fluid.bufmelbands~/bufmfcc~ (1/1), fluid.list2buf (1/1), fluid.buf2list (1/1), fluid.labelset~ (1/2).
- BEAP: bp.LFO 0/5, bp.LPF 5/1, bp.MMF 5/1, bp.Sequencer 2/2, bp.FM 2/1, bp.ADSR 2/1, bp.VCA 2/1, bp.Keyboard 0/4, bp.Oscillator 6/2, bp.Stereo 2/0.
- Effects: cverb~ (MSP, 2/1) exists; reverb~, chorus~, flanger~, phaser~ and filter~ do not.
- FluCoMa refpage methods include fit, predict and predictpoint on fluid.mlpclassifier~. `grep "<method name='"` lists them.

**Slash-command references with no `.claude/commands` file:**
- `/max-config`: max-lifecycle SKILL.md (Package Configuration bullet and "When to Use" list), max-lifecycle/references/project-structure.md (config.json section), max-router SKILL.md (Domain Context Loading step 3);
- `/max-version`: max-lifecycle "When to Use".

The existing commands are max-build, max-discuss, max-iterate, max-new, max-onboard, max-research, max-status, max-switch, max-test and max-verify.

**Variable I/O:**
- overrides.json `variable_io_rules` has 45 entries. Do not hard-code that count in prose.
- `SUPPORTED_IO_FORMULAS` (db_lookup.py): "", arg_count, arg_count+1, arg_count_or_default, first_arg, first_arg+1, second_arg, second_arg+1, second_arg+2, inherited_from_subpatch. `fixed:N` is validated separately.
- `IO_RESOLVERS` (io_resolvers.py): ctlin, expr, if, notein, pipe, receive, route, routepass, select, sprintf, vexpr.
- `compute_io_counts`: trigger b i f gives (1,3); pack 0 0 0 0 gives (4,1); route foo bar baz gives (4,4); gate 3 gives (2,3); matrix~ 4 2 gives (4,3). TECHNICAL's current matrix~ example ("2 outlets") is wrong.
- No domain `objects.json` carries an `io_rule` key.

**gain~ refpage** (`msp-ref/gain~.maxref.xml`): int sets the slider value; a float is "Converted to int"; `size` defaults to 158, so values run 0 to size-1. The `scale` refpage: if all four arguments are ints the output is int, and integer arguments truncate. The user-confirmed memory (minitaur v0.1.9) says `scale 0 127 0. 1.` turns 63.5 into 63.

**DSP critic** (`dsp_critic.py`, MIDI-range check): it traces only the inlet 1 of `*~` / `mc.*~`, directly or through `line~`. It does not check gain~.

**TECHNICAL J13 targets:**
- The Spacing Constants table says 100/70/120 px. The code says `V_SPACING=20`, `H_GUTTER=15` (defaults.py), `_COMPONENT_GAP=40.0` and `_START_X=_START_Y=30.0` (layout.py).
- The Layout Critic table has a "Companion misalignment" row. The `layout_critic.py` docstring lists overlapping boxes, missing cable midpoints and out-of-bounds placement.
- The Critic Loop text says six critics and that m4l is not called; `critics/__init__.py` invokes seven.
- There is no M4L critic section.
- "2,309 tests across 55 test files" and "~18,600 LOC" are stale.

**README J13 targets:**
- The "Node for Max & js scripting" feature bullet calls js objects V8.
- The milestone table rows v2.2 and v2.4.0 contain runs of U+FFFD in the Phases/Plans cells. The text is garbled in every historical version, so it cannot be recovered; neighboring cells use "—".
- The "## Patches" table lists 18 of the 31 project directories. Missing: amplitude-follower, barnett-dbap, disintegrate, ji-harmonizer, knock, looper, reverse-delay, sample-layers, simple-fm, spectraldetector, stereo-feedback-delay, subtractive-synth, terrain-synth. Each has a context.md.
- "six domain-specific critics" appears twice. The tree block says "~18,600 LOC" and "2,309 tests".

**patterns/gen:** 19 .gendsp files, each with exactly one codebox. JSON is indented 2 spaces with no trailing newline. No test reads them. `validate_genexpr(code)` returns only an info line for adsr-envelope today.
</observed_facts>

<tasks>

<task type="tracer" tdd="true">
  <name>Task 1 (tracer): Doc call-form checker end to end, plus every raising call form and replace_box wording fixed (J3)</name>
  <precondition>`git merge-base --is-ancestor e9852567 HEAD` succeeds (the worktree base contains Q13).</precondition>
  <files>tests/test_doc_signatures.py, .claude/skills/max-patch-agent/SKILL.md, .claude/skills/max-dsp-agent/SKILL.md, .claude/skills/references/shared-capabilities.md, .claude/commands/max-iterate.md, TECHNICAL.md, patterns/gen/INDEX.md</files>
  <read_first>
    - .planning/reviews/2026-10-11-fix-plan.md, the "### Q16" section and "Rules for every task"; .planning/reviews/2026-10-11-repo-review.md, the "### 1J" table (J3 row)
    - CLAUDE.md "### Rule #8" (the replace_box / replace_box_safe contract)
    - src/maxpat/__init__.py (the export list)
    - .claude/skills/max-patch-agent/SKILL.md: "### Patch Construction" and "### Key Functions"
    - .claude/skills/max-dsp-agent/SKILL.md: "### Using External .gendsp Patterns"
    - .claude/skills/references/shared-capabilities.md: "## Layout Options", "## Editing Functions", "## Edit Workflow"
    - .claude/commands/max-iterate.md: steps 11 and 14
    - TECHNICAL.md: the Patcher methods table, the "Codified layout/UX builders" table, "### Read/Write Functions" and "### Patch Analysis"
    - patterns/gen/INDEX.md: "### In a .maxpat (via agent generation)"
    - tests/test_agent_skills.py lines 1-40 (house style) and tests/conftest.py (markers)
  </read_first>
  <behavior>
    Create tests/test_doc_signatures.py. All names below are module-level, so later tasks can reuse them.
    - `DOC_FILES`: repo-root-relative Paths, sorted. CLAUDE.md, TECHNICAL.md, README.md, patterns/gen/INDEX.md, every `.claude/skills/**/*.md` and every `.claude/commands/*.md`. Resolve the repo root with `Path(__file__).resolve().parents[1]`.
    - The API index, built once and cached:
      - public functions and classes defined in src.maxpat (`__module__` starts with "src.maxpat", name without a leading underscore) from the modules src.maxpat, src.maxpat.project, src.maxpat.critics, src.maxpat.hooks, src.maxpat.layout, src.maxpat.aesthetics, src.maxpat.memory, src.maxpat.testing and src.maxpat.m4l_polish;
      - the public methods of `Patcher` and of `ObjectDatabase`.
    - `_scan_text(text, label) -> (findings: list[str], checked: int)`:
      - **Extraction.** Take fenced blocks whose language tag is empty, python or py, plus inline backtick spans outside fences, keeping line numbers. Within each, find `<receiver>.<name>(` or a bare `<name>(` where name is in the index, but not when it is preceded by `def `. Take the balanced-parenthesis argument text and strip `#` comments from it.
      - **Receiver routing.**
        - db, self.db, patcher.db, ObjectDatabase, ObjectDatabase(), and any receiver ending in "db": ObjectDatabase methods.
        - patcher, Patcher, Patcher(), p, inner, sub, self, parent: Patcher methods.
        - No receiver: the module-level function or class, and the Patcher method of the same name. The snippet passes if any candidate passes.
        - Any other receiver: skipped.
      - **Call mode.** Applies when `ast.parse("f(" + args + ")", mode="eval")` succeeds and there is at least one argument.
        - (a) `signature.bind_partial` with dummy objects must succeed. When `*`/`**` expansion is present, check only that the explicit keyword names exist, unless the function takes `**kwargs`.
        - (b) A positional bare-name argument whose identifier is the name of a different parameter of the same signature is a finding (catches `db` landing on `box_id`).
        - (c) Type sentinel. Infer a type for a positional argument:
          - bare names: patcher, p, inner give Patcher; patch_dict gives dict; db gives ObjectDatabase; patchline gives Patchline; box, old_box, new_box, src, dst, src_box, dst_box give Box;
          - a call to Box, Patcher or Patchline gives that class.

          If the bound parameter's annotation string names one of str, dict, Box, Patcher, Patchline, ObjectDatabase, list, int, float or bool, and does not name the inferred type, that is a finding.
      - **Def mode.** If call mode fails to parse, drop bare `...` items and parse `def f(<args>): pass`. Every listed parameter name must exist in the signature, unless the signature takes `**kwargs`. This accepts listings such as `add_overlay_readout(target, *, format="%.2f")`.
      - If neither mode parses, the finding is "unparseable call form".
      - `checked` counts every snippet that resolved to at least one signature.
      - The finding format is `"<label>:<line>: <receiver.>name(<args>) -> <reasons>"`.
    - `test_checker_flags_bad_form`, parametrized over 7 inline-markdown cases. Each must give at least one finding:
      - add_box given a Box built with a trailing db argument;
      - a bare Box constructor whose third positional is db;
      - apply_layout with the keyword spelled layout_options;
      - insert_into_connection given (src, dst, new_box);
      - replace_box given three positionals;
      - save_patch_roundtrip given patcher as its first argument;
      - find_box given three positionals.
    - `test_checker_accepts_good_form`, parametrized. Each gives zero findings:
      - `patcher.add_box("gen~", ["smooth-ramp"])`
      - `apply_layout(patcher, options=LayoutOptions(v_spacing=20.0))`
      - `patcher.insert_into_connection(src, dst, "*~", ["0.5"])`
      - `patcher.replace_box_safe(box, "cycle~", args=["440"])`
      - `save_patch_roundtrip(patcher.to_dict(), path, original_text)`
      - `write_gendsp(code, path, ..., *, force=False)`
      - `finalize_patch(is_new=True)`
      - `patcher.add_overlay_readout(target, *, format="%.2f")`
      - a JS span `outlet(0, value)` (not an API name)
    - `test_scan_covers_enough_call_snippets`: the summed `checked` over DOC_FILES is at least 200 (386 at planning).
    - `test_doc_call_forms_match_signatures`, parametrized over DOC_FILES (ids = relative path): no findings. The assertion message joins the findings.
    - `test_replace_box_docs_point_to_safe_variant`:
      - (a) shared-capabilities.md, max-iterate.md and TECHNICAL.md each contain `replace_box_safe`;
      - (b) in DOC_FILES, a line is a finding when all of these hold:
        - it matches the regex `\breplace_box\(`;
        - it does not contain replace_box_safe;
        - its lowercase form does not contain "orphan";
        - it matches `remap` or `preserves all positions and connections` (case-insensitive).
    RED, captured into Q/red-task1.txt. Expect:
    - test_doc_call_forms_match_signatures to fail for TECHNICAL.md, patterns/gen/INDEX.md, max-dsp-agent SKILL.md, max-patch-agent SKILL.md and shared-capabilities.md, with at least the 20 findings in `<observed_facts>`;
    - the replace_box test to fail on the shared-capabilities, TECHNICAL and max-iterate wording;
    - every self-test to pass.

    Classify any finding beyond the 20. Either it is a real raising form (fix the doc in this task and list it in SUMMARY), or it is a checker false positive (fix the checker and add a good-form self-test case).
  </behavior>
  <action>
RED first: write tests/test_doc_signatures.py as specified in the behavior block and capture the failing run. Then fix the docs to the real signatures in `<observed_facts>`, per J3 and planner decisions 5 and 10, locating each place by content.
- **max-patch-agent SKILL.md "### Patch Construction":**
  - Standard objects are created with `patcher.add_box(name, args, x, y)`, which looks the name up in ObjectDatabase (Rule #1) and returns the Box.
  - Structural objects come from `add_subpatcher()`, `add_bpatcher()` and `add_gen()`.
  - Remove the guidance to call the Box constructor or its `__new__` bypass directly.
- **max-patch-agent SKILL.md "### Key Functions":**
  - Replace the Box-constructor bullet and the add-a-Box bullet with one `Patcher.add_box(name, args=None, x=0.0, y=0.0)` bullet.
  - Write `Patcher.add_subpatcher(name, inlets=1, outlets=1, x=0.0, y=0.0, inlet_comments=None, outlet_comments=None)`.
  - Write `apply_layout(patcher, options=None)`.
  - Write `Patcher.add_node_script(filename, code=None, num_outlets=2, x=0.0, y=0.0)` and `Patcher.add_js(filename, code=None, num_inlets=1, num_outlets=1, x=0.0, y=0.0)`, keeping their return notes.
- **max-dsp-agent SKILL.md and patterns/gen/INDEX.md, in the external-.gendsp example:** the creation line becomes `gen_box = patcher.add_box("gen~", ["smooth-ramp"])`. The numinlets/numoutlets/outlettype lines that follow stay.
- **shared-capabilities.md:**
  - "## Layout Options": `apply_layout(patcher, options=LayoutOptions(...))`.
  - "## Editing Functions": `patcher.insert_into_connection(src, dst, name, args)` inserts a new object between two connected boxes and returns an EditResult.
  - Also in "## Editing Functions": `patcher.replace_box_safe(box, new_name, args=[...])` swaps the object type. It auto-rewires by index only when the new object's inlet AND outlet counts match. Otherwise it returns `result.orphaned` to rewire (CLAUDE.md Rule #8).
  - Add one sentence: plain `replace_box(box, new_name, args=...)` orphans every connection.
- **max-iterate.md:**
  - Step 11 "Surgical edit": use `modify_box()` or `replace_box_safe()`. Positions are preserved, and connections survive only when `replace_box_safe()` finds a matching I/O layout. On a mismatch, rewire `result.orphaned` (Rule #8).
  - Step 14: the swap bullet names `replace_box_safe()` with the same caveat, and the insert bullet reads `insert_into_connection(src, dst, name, args)`.
- **TECHNICAL.md, Patcher methods table:**
  - `add_bpatcher(filename=None, embedded=False, args=None, x=0.0, y=0.0, ...)`;
  - `find_box(*, id=None, name=None, maxclass=None, text=None, recursive=False)` and `find_boxes(...)` with the same keywords;
  - `modify_box(box, *, args=None, position=None, color=None, extra_attrs=None)`;
  - `insert_into_connection(source, dest, name, args=None)`: insert a new object between two connected boxes;
  - `replace_box(old_box, new_name, *, args=None)`: every old connection comes back in `EditResult.orphaned` and must be rewired (Rule #8); prefer `replace_box_safe`.
- **TECHNICAL.md, other sections:** the "Read/Write Functions" row becomes `save_patch_roundtrip(patch_dict, path, original_text=None, *, force=False)`, with a note to pass `patcher.to_dict()`. "Patch Analysis" says `patcher.analyze()`.
- Edit only these call-form lines and the replace_box sentences. No other wording changes in this task.
Then run the verify: the test file is green, and the corrected forms execute.
Commit: `docs: doc call forms match real signatures, replace_box_safe guidance, doc-signature test (Q16)`, with the 7 task files.
  </action>
  <verify>
    <automated>bash -c 'B=$(git status --porcelain) && python3 -m pytest tests/test_doc_signatures.py -q -p no:cacheprovider && A=$(git status --porcelain) && test "$B" = "$A" && python3 -W error -c "from src.maxpat import Patcher, apply_layout, LayoutOptions; p = Patcher(); p.add_box(\"gen~\", [\"smooth-ramp\"]); c = p.add_box(\"cycle~\", [\"440\"]); d = p.add_box(\"dac~\"); p.add_connection(c, 0, d, 0); p.insert_into_connection(c, d, \"*~\", [\"0.5\"]); r = p.replace_box_safe(c, \"phasor~\", args=[\"220\"]); assert r.orphaned == []; apply_layout(p, options=LayoutOptions())" && python3 -c "import ast; ast.parse(open(\"tests/test_doc_signatures.py\").read(), feature_version=(3, 10))"'</automated>
  </verify>
  <done>
- The checker flags all 7 bad forms and accepts all good forms, and checks at least 200 snippets.
- Every DOC_FILES entry has zero call-form findings, and the replace_box wording guard passes.
- The corrected forms execute under `-W error`. Q/red-task1.txt holds the RED run.
- The commit holds exactly the 7 task files.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Agent rules and templates that cause broken output: js handler, gain rule, FluCoMa/BEAP templates, dial trigger, core-only config, variable I/O (J1, J2, J6, J8, J9, J10, J11; J4/J7 verified)</name>
  <precondition>`$HOME/Documents/Max 9/Packages/FluidCorpusManipulation/docs` and `/Applications/Max.app/Contents/Resources/C74/packages/BEAP/Help` exist. They are the J8 verification sources, read by the executor, never by tests.</precondition>
  <files>tests/test_doc_signatures.py, CLAUDE.md, TECHNICAL.md, .claude/skills/max-js-agent/SKILL.md, .claude/skills/max-dsp-agent/SKILL.md, .claude/skills/max-patch-agent/BOUNDARIES.md, .claude/skills/references/ui-presets.md, .claude/skills/max-router/SKILL.md, .claude/skills/max-lifecycle/SKILL.md, .claude/skills/max-lifecycle/references/project-structure.md, .claude/skills/max-patch-agent/SKILL.md, .claude/skills/max-ui-agent/SKILL.md, .claude/skills/max-rnbo-agent/SKILL.md</files>
  <read_first>
    - The review's "### 1J" rows J1, J2, J4, J6, J7, J8, J9, J10 and J11
    - CLAUDE.md: "### MSP (Audio/Signal)" (Gain safety bullet), "### js / v8 (JavaScript inside MAX)" (Handler functions bullet), "## Variable I/O Objects"
    - TECHNICAL.md: the DB schema example and "Key fields" (the trigger JSON), "### Variable I/O Rules", the DSP Critic table ("MIDI-range gain values" row), and "### js Object (`generate_js_script`)"
    - .claude/skills/max-js-agent/SKILL.md (Handler functions bullet)
    - .claude/skills/max-dsp-agent/SKILL.md: "### Signal Chain Construction", "### Community DSP Packages", "## Package Workflow Templates" (all five templates)
    - .claude/skills/max-patch-agent/BOUNDARIES.md (the MSP signal chains bullet); max-patch-agent SKILL.md BEAP bullets (for the PACKAGES.md pointer)
    - .claude/skills/references/ui-presets.md: "## Complete Dial Chain Example"
    - .claude/skills/max-router/SKILL.md "## Domain Context Loading"; max-lifecycle SKILL.md "### Package Configuration" and "## When to Use"; max-lifecycle/references/project-structure.md "### config.json"
    - The config step naming `load_project_config()` in the patch, dsp, ui and rnbo agent SKILL.md files
    - src/maxpat/db_lookup.py (SUPPORTED_IO_FORMULAS and its comment; `_validate_variable_io_rules`; `compute_io_counts` docstring); src/maxpat/io_resolvers.py (IO_RESOLVERS); src/maxpat/critics/dsp_critic.py (the `_GAIN_INLET_1_NAMES` block)
    - Read-only user memory, for proven FluCoMa gotchas to cite (optional): /Users/taylorbrook/.claude/projects/-Users-taylorbrook-Dev-MAX/memory/reference_flucoma_list2buf_autosize.md, reference_flucoma_read_defer_low.md, reference_flucoma_kmeans_plotter.md
  </read_first>
  <behavior>
    Append to tests/test_doc_signatures.py, reusing DOC_FILES and a module-scoped ObjectDatabase fixture.
    - `test_js_anything_handler_uses_messagename` (J1):
      - every DOC_FILES line containing `msg_int(` also contains `messagename` and `arrayfromargs(arguments)`;
      - no DOC_FILES line matches `anything\(\s*[A-Za-z_]`.
    - `test_gain_rule_scoped_to_multiply_tilde` (J2, J6):
      - no DOC_FILES line contains the phrase "feeding `*~` or `gain~`";
      - some DOC_FILES line contains "`scale 0. 127. 0. 1.`";
      - some DOC_FILES line contains "`gain~`" and "slider position".
    - `test_dsp_templates_use_db_objects` (J8), parametrized over max-dsp-agent/SKILL.md and max-patch-agent/BOUNDARIES.md. Every token matched by these patterns must satisfy `db.exists`:
      - the tilde-object regex `(?<![\w.~/$#-])((?:[a-z]\w*\.)*[A-Za-z]\w*~)(?![\w*])`;
      - the package regex `(?<![\w/-])((?:fluid|bp)\.[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)*~?)(?![\w*])`.

      Exempt "Gen~", `db.is_pd_object` names, and tokens ending in .maxpat or .gendsp.
    - `test_flucoma_templates_use_fit_predict` (J8): in max-dsp-agent SKILL.md, no match of `["`]train["`]`, at least one match of `["`]fit["`]`, and at least one of `["`]predict(point)?["`]`.
    - `test_ui_presets_dial_chain_uses_trigger` (J9): the text from "## Complete Dial Chain Example" to the next "## " heading or EOF contains a line matching `^\s*(t|trigger) f f\b`.
    - `test_no_references_to_missing_commands` (J10): every `(?<![\w./-])/(max-[a-z][a-z0-9-]*)` in DOC_FILES has a matching `.claude/commands/<name>.md`.
    - `test_missing_config_is_core_only` (J10):
      - max-router SKILL.md contains "`allowed_packages=[]`" and has no line containing both "config.json" and "STOP";
      - project-structure.md contains "core-only";
      - in each of the patch, dsp, ui and rnbo agent SKILL.md files, every line naming `load_project_config()` contains "core-only".
    - `test_variable_io_docs_point_to_overrides` (J11):
      - no DOC_FILES line matches `\bio_rule\b`;
      - CLAUDE.md contains `variable_io_rules` and `compute_io_counts`.
    - `test_technical_io_formula_table_matches_code` (J11): in TECHNICAL.md's "### Variable I/O Rules" subsection (up to the next heading), the set of first-column backticked tokens of the table rows equals `(SUPPORTED_IO_FORMULAS - {""}) | {"fixed:N"}`.
    - `test_spectroscope_claim_matches_db` (J4 lock; green from the start): every DOC_FILES match of `spectroscope~[^\n]*?(\d+) inlets? / (\d+) outlets?` equals `db.compute_io_counts("spectroscope~", [])`, and there is at least one match.

    RED, captured into Q/red-task2.txt: all of these fail except the J4 lock.
  </behavior>
  <action>
RED first: append the tests and capture the failing run. Then fix the docs, locating each place by content.
- **J1 (CLAUDE.md js section and the max-js-agent Handler functions bullet):**
  - The handler bullet names `bang()`, `msg_int(v)`, `msg_float(v)`, `list()` (read its values with `arrayfromargs(arguments)`) and `anything()`.
  - For `anything()`, MAX passes the selector in `messagename` and the arguments in `arguments`. Show the pattern inline: `function anything() { var a = arrayfromargs(arguments); if (messagename == "foo") { ... } }`. It must stay ES5.
  - TECHNICAL's `generate_js_script` bullet lists `anything` and states that handler bodies read the selector from `messagename` and the values via `arrayfromargs(arguments)` (planner decision 4).
  - Do not quote the old parameterized form anywhere.
- **J2 and J6 (the CLAUDE.md MSP "Gain safety" bullet):**
  - Values feeding the gain input of the `*~` multiplier (including `line~` ramps into it) MUST be in 0.0-1.0.
  - Normalize MIDI ints with `scale 0 127 0. 1.` or `/ 127.`.
  - Normalize float sources (flonum, float-output dial/slider/live.dial) with `scale 0. 127. 0. 1.`, because all-int input arguments make `scale` truncate float input.
  - `gain~` is different. Its left inlet takes int slider positions, 0 to size-1 (default size 158, so 0-157). Floats are converted to int, so a 0.-1. value leaves it at or near silence. Drive it with slider positions, never 0-1 gains.
  - Keep the sentence that validation and the DSP critic block violations, scoped to `*~` / `mc.*~`.
  - The TECHNICAL DSP Critic "MIDI-range gain values" row describes what the code checks: raw 0-127 control sources reaching inlet 1 of `*~` / `mc.*~`, directly or through `line~`, without a normalizer. Severity: blocker.
- **J8 (max-dsp-agent SKILL.md and patch BOUNDARIES), following planner decision 9 and Rule #1:**
  - "### Signal Chain Construction": replace the Effects bullet with objects that resolve in the DB, such as `cverb~` and `allpass~`, plus building effects in gen~ from `patterns/gen` (`simple-reverb`, `multi-tap-delay`) or `tapin~`/`tapout~` modulated by `cycle~`. Never name the nonexistent effect objects.
  - "### Community DSP Packages": use the `~` FluCoMa names.
  - The three FluCoMa templates:
    - use the DB names (`fluid.normalize~`, `fluid.dataset~`, `fluid.kdtree~`, `fluid.mlpclassifier~`, `fluid.bufnmf~`, `fluid.bufstats~`, `fluid.bufmelbands~`, `fluid.bufmfcc~`; `fluid.stats` keeps no `~`);
    - use the fit / predict / predictpoint messages, plus any other message, attribute or connection shape, only as the installed refpage and help patch show them;
    - where a buffer-based model object is fed from a real-time feature list, route it through `fluid.list2buf` and back through `fluid.buf2list`, as the help patches do. The proven list2buf gotcha, pre-size the buffer plus `@autosize 0`, may be cited;
    - remove any attribute the refpage lacks.
  - The two BEAP templates:
    - `bp.LFO` replaces bp.LFOscillator, `bp.LPF` or `bp.MMF` replaces bp.SVF, and `bp.Sequencer` replaces bp.Steppr;
    - every port index must be in range per the DB, and every port role verified from the BEAP help or module patchers. Mark unverifiable roles "(role unverified — confirm in MAX)";
    - point the opening sentence's dangling PACKAGES.md reference at the BEAP section of max-patch-agent SKILL.md.
  - Patch BOUNDARIES: the MSP signal chains example lists only DB objects, e.g. cycle~, biquad~, delay~.
- **J9 (ui-presets "## Complete Dial Chain Example"):** insert `t f f` below `scale 0 127 20. 20000.`. The number box hangs off its right outlet and the gen~ param message off its left outlet, and the diagram notes that right fires first (Rule #3).
- **J10 (planner decision 1):**
  - Router "## Domain Context Loading" step 3: when `load_project_config()` returns None, the project is core-only. Pass `allowed_packages=[]` to specialists and continue, with no stop. Tell the user once that package objects stay disabled until a config.json lists packages.
  - Lifecycle "### Package Configuration": packages are changed later by editing `patches/<project>/config.json` or calling `save_project_config()`; a project without config.json is core-only. Delete the two nonexistent commands from "## When to Use".
  - project-structure.md "### config.json": the file is created by `/max-new` and edited directly. A missing file means core-only, so builds proceed with package objects disabled.
  - The four specialist config steps each add: if `load_project_config()` returns None, use `allowed = []` (core-only), never None (None allows every package).
- **J11:**
  - CLAUDE.md "## Variable I/O Objects": argument-dependent counts come from `overrides.json` → `variable_io_rules` (one formula entry per object) and from the text-aware resolvers in `src/maxpat/io_resolvers.py` (`IO_RESOLVERS`: select, route, expr, …). The domain files carry only the `variable_io` flag. Always get counts from `db.compute_io_counts(name, args)`. Keep the three examples; they are correct.
  - TECHNICAL: remove the per-object rule block from the trigger schema example, and point the "Key fields" `variable_io` bullet to `compute_io_counts`.
  - TECHNICAL "### Variable I/O Rules": rewrite it to describe overrides.json `variable_io_rules` (keyed by object name, with `inlet_count`/`outlet_count`/`default_*` and a description) plus IO_RESOLVERS. Its formula table has exactly one row per formula in `(SUPPORTED_IO_FORMULAS - {""}) | {"fixed:N"}`. Each example is computed at execution time with `db.compute_io_counts` from an object whose rule uses that formula; use "—" when no object uses it. Do not state a rule count.
- **J4 / J7:** change nothing. Record the evidence (planner decision 3) for SUMMARY.
Run the existing doc tests too; test_agent_skills and test_commands must stay green. Commit: `docs: js anything() pattern, gain~ slider positions, DB-real FluCoMa/BEAP templates, dial trigger, core-only config, variable_io_rules (Q16)`, with the 13 task files.
  </action>
  <verify>
    <automated>bash -c 'B=$(git status --porcelain) && python3 -m pytest tests/test_doc_signatures.py tests/test_claude_md.py tests/test_agent_skills.py tests/test_commands.py tests/test_project.py -q -p no:cacheprovider && A=$(git status --porcelain) && test "$B" = "$A" && python3 -c "import glob; n = sum(\"never clears existing midpoints\" in open(f).read() for f in glob.glob(\".claude/skills/max-*/SKILL.md\")); assert n == 6, n"'</automated>
  </verify>
  <done>
- All Task 2 guards are green: J1, J2/J6, J8, J9, J10, J11 and the J4 lock. Task 1's tests are still green.
- The six edit-protocol blocks still carry the Q6 midpoint guarantee (J7).
- test_claude_md, test_agent_skills, test_commands and test_project are green.
- Q/red-task2.txt holds the RED run. The commit holds exactly the 13 task files.
- Every unverified BEAP or FluCoMa detail is listed for SUMMARY.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: gen~ pattern library on the proven-safe construct set (J12), and README/TECHNICAL brought in line with the repo (J13)</name>
  <files>tests/test_doc_signatures.py, README.md, TECHNICAL.md, patterns/gen/ramps/adsr-envelope.gendsp, patterns/gen/ramps/ar-envelope.gendsp, patterns/gen/ramps/smooth-ramp.gendsp, patterns/gen/dsp/noise-generator.gendsp, patterns/gen/dsp/compressor.gendsp, patterns/gen/dsp/multi-tap-delay.gendsp, patterns/gen/random/random-walk.gendsp, patterns/gen/smoothing/lag-processor.gendsp, patterns/gen/buffer/buffer-player.gendsp, patterns/gen/buffer/buffer-recorder.gendsp</files>
  <read_first>
    - The review's "### 1J" rows J12 and J13
    - CLAUDE.md "### Gen~ (GenExpr DSP Code)": the "No local aliases in Param-only expressions", "Codebox safe-construct rules" and declaration-ordering bullets
    - The codebox `code` of each of the 10 listed .gendsp files (extract it with a one-off `python3 -c`)
    - README.md: the feature bullets, the tree block, "## Patches" and the milestone table; each missing project's `patches/<name>/context.md` (first section only)
    - TECHNICAL.md: "## Critic System" through "### Critic Loop", the "### Spacing Constants" table, the src/maxpat LOC sentence, the object-count lines near the package-file description, and "## Test Suite"
    - The module docstrings and `CriticResult(` severities of src/maxpat/critics/{structure,dsp,rnbo,ext,layout,package,m4l}_critic.py, plus the `review_patch` docstring in src/maxpat/critics/__init__.py
    - src/maxpat/defaults.py (V_SPACING, H_GUTTER, PATCHER_PADDING) and src/maxpat/layout.py (_START_X, _START_Y, _COMPONENT_GAP)
  </read_first>
  <behavior>
    Append to tests/test_doc_signatures.py:
    - `test_gen_patterns_use_safe_constructs` (J12), parametrized over `sorted(patterns/gen/**/*.gendsp)` (19 files). For every codebox `code` in the file:
      - no tab character;
      - no `else\s+if`;
      - no `==` or `!=` inside the balanced parentheses of any `if\s*\(`;
      - no line matching `^\s*[A-Za-z_]\w*\s*=\s*samplerate\s*;`;
      - every `peek(` call has at least 3 top-level arguments and every `poke(` at least 4.
    - `test_readme_patch_table_lists_every_project` (J13): the set of `**name**` first cells in README's "## Patches" table, up to the next "## ", equals the set of non-hidden directories under `patches/`.
    - `test_docs_have_no_replacement_characters` (J13): no DOC_FILES file contains U+FFFD.
    - `test_readme_js_engine_wording` (J13): README does not contain "V8 `js`", and it contains "Legacy Engine".
    - `test_technical_spacing_table_matches_code` (J13): each row of TECHNICAL's "### Spacing Constants" table maps every backticked name in its first cell to its code value, and the number before "px" in the second cell must equal it. The map: V_SPACING and H_GUTTER from defaults; COMPONENT_GAP is layout._COMPONENT_GAP; START_X and START_Y are layout._START_X/_START_Y; PATCHER_PADDING from defaults. An unknown name fails. The rows V_SPACING, H_GUTTER and COMPONENT_GAP must be present.
    - `test_technical_documents_every_critic_module` (J13): for every `src/maxpat/critics/*_critic.py`, TECHNICAL has a line starting with "### " that contains "(`<filename>`)".

    RED, captured into Q/red-task3.txt. Expect:
    - the 10 listed .gendsp to fail and the other 9 to pass;
    - README to be missing 13 projects;
    - U+FFFD in README;
    - the V8 wording;
    - spacing 100/70/120;
    - no m4l_critic.py heading.
  </behavior>
  <action>
RED first: append the tests and capture the failing run.

**J12 (planner decision 2).** Rewrite each listed codebox to the proven-safe construct set without changing its behavior:
- Turn each else-if chain into nested `else { if (...) { ... } else { ... } }`.
- Turn each `x == N` on the integer state into the range test `x > N - 0.5 && x < N + 0.5`, with the numbers written out.
- Delete each `sr = samplerate;` alias and write `samplerate` directly at every use (e.g. `max(attack * samplerate * 0.001, 1)`).
- Give peek and poke an explicit channel 0, e.g. `peek(buf, read_pos, 0)` and `poke(buf, audio_in, pos, 0)`.
- Use 4-space indentation only. Keep all declarations first, in their existing order.

The edit method, per file, uses a one-off `python3 -c` (not a committed script; Rule #5) from the checkout root:
- read the raw text and `json.loads` it;
- take the single codebox code and build the new code;
- assert that `json.dumps(old_code)` occurs exactly once in the raw text (if it does not, try `ensure_ascii=False`);
- replace it with `json.dumps(new_code)` and write the text back with no trailing newline.

Then prove each file:
- `git diff --numstat -- <file>` shows 1 insertion and 1 deletion;
- the file still `json.load`s;
- `validate_genexpr(new_code)` has no error or warning that `validate_genexpr(old_code)` lacked.

Record the old/new pairs in Q/j12-rewrites.txt.

Do not touch INDEX.md here. Its leftover "External reverb~" wording is noted in SUMMARY (out of scope).

**J13, README:**
- The js bullet mirrors the max-js-agent skill: `js` objects (Legacy Engine, ES5), `v8` objects (Modern Engine) and Node for Max `node.script`.
- Replace each U+FFFD run in the milestone table with "—".
- The "## Patches" table gets one row per directory under `patches/`, sorted case-insensitively.
  - The 13 new rows each get a one-sentence description drawn only from the project's context.md. Invent no features.
  - Recompute the Files column for all 31 rows from the extensions present under `patches/<p>/generated/` (only .maxpat, .gendsp and .js are listed).
  - Existing descriptions stay unchanged.
- Change "six domain-specific critics" to seven, adding Max for Live device conventions to each list.

**J13, TECHNICAL (planner decision 8):**
- The Structure, Layout and Package Critic tables state each module's real checks and severities:
  - fan-out without trigger is a blocker when branches reconverge on one box at different inlets, otherwise a warning;
  - the layout checks are overlap, missing midpoints and out-of-bounds; drop the nonexistent companion row;
  - Bach llll typing is a note;
  - BEAP termination/VCA and community extraction follow the code.
- Add an `### M4L Critic (`m4l_critic.py`)` section from its docstring and severities. Say it runs when `detect_m4l_device_type` sees plugin~, plugout~ or live.thisdevice.
- "### Critic Loop" says seven critics, with RNBO/M4L/package/external conditional, and drops the not-called sentence. The test-area bullet lists seven.
- The Spacing Constants table: V_SPACING 20px, H_GUTTER 15px, COMPONENT_GAP 40px, START_X / START_Y 30px; adding PATCHER_PADDING 40px is optional.
- Do not edit the J3/J1/J2/J11 lines again.

**Counts (planner decision 7), computed last.** Run the full suite once so every new test exists, then run these into Q/counts.txt:
- `find src/maxpat -name "*.py" -not -path "*/__pycache__/*" -print0 | xargs -0 cat | wc -l`
- `python3 -m pytest --collect-only -q -p no:cacheprovider | tail -1`
- `find tests -name "test_*.py" -not -path "*/__pycache__/*" | wc -l`
- a one-off `python3 -c` summing the domain and package objects.json entry counts.

Write the LOC (rounded to the nearest 100, with ~) into the README tree block and TECHNICAL's src/maxpat sentence. Write the test count into the README tree block. Write the test count and test-file count into TECHNICAL "## Test Suite". Confirm, or update if changed, the 3,445 / 29-package figures. If the soft base check failed, add the SUMMARY caveat (rules).

Commit: `docs: gen~ patterns on proven-safe constructs; README/TECHNICAL tables and counts match the repo (Q16)`, with the 13 task files. Then run the full suite into Q/final-pytest.txt and record `git stash list` against Q/stash-list-before.txt.
  </action>
  <verify>
    <automated>bash -c 'B=$(git status --porcelain) && python3 -m pytest -q -p no:cacheprovider && A=$(git status --porcelain) && test "$B" = "$A" && BASE=$(cat .planning/quick/261014-fbx-implement-q16-in-planning-reviews-2026-1/base-sha.txt) && D=$(git diff --name-only "$BASE"..HEAD -- patches src) && test -z "$D" && python3 -c "import json, glob; [json.load(open(f)) for f in glob.glob(\"patterns/gen/**/*.gendsp\", recursive=True)]" && python3 -c "import ast; ast.parse(open(\"tests/test_doc_signatures.py\").read(), feature_version=(3, 10))"'</automated>
  </verify>
  <done>
- All 19 pattern files pass the safe-construct guard. Each of the 10 rewritten files differs only in its code line, and validate_genexpr reports nothing new.
- The README table lists all project directories (31 at planning), with no U+FFFD and with the Legacy Engine wording.
- TECHNICAL documents all seven critic modules with code-derived severities and has the correct spacing table. The counts are computed live and recorded in Q/counts.txt.
- The full suite is green: the baseline plus only the new tests, with 1 xfailed / 1 xpassed.
- There is no diff under patches/ or src/, and the stash list is unchanged. The commit holds exactly the 13 task files.
  </done>
</task>

</tasks>

<threat_model>
Security config: ASVS level 1, block on high. `security_enforcement` is absent from .planning/config.json, so it is enabled. This is documentation and a read-only test with no network, auth or user-input surface. The trust boundary that matters is docs → agent behavior → generated patches that the user runs in MAX with real audio hardware.

## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Docs → agent output | Agents follow CLAUDE.md, skills and TECHNICAL literally; wrong guidance becomes broken or unsafe patches |
| Generated patch → audio hardware | Gain guidance controls output level |
| Pattern library → user projects | .gendsp files are copied into projects as-is |
| Committed patches → tests | User-confirmed baselines that must never change |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-fbx-01 | Tampering | CLAUDE.md gain rule (J2/J6): rewording could let raw 0-127 reach `*~` and produce dangerously loud output | high | mitigate | The `*~` 0.0-1.0 MUST rule and the critic sentence stay, and the critic code is unchanged. test_gain_rule_scoped_to_multiply_tilde asserts the normalizers are documented. gain~ is documented as slider positions, so agents stop sending it values that silence it. |
| T-fbx-02 | Elevation of Privilege | Core-only config (J10): None reaching `Patcher(allowed_packages=None)` would allow every package, unvetted community objects included | medium | mitigate | Docs mandate `allowed_packages=[]`, never None, in the router and all four specialist steps. test_missing_config_is_core_only pins it. Planning showed no config-less project uses package objects. |
| T-fbx-03 | Tampering | Pattern rewrites (J12) changing DSP behavior or breaking compilation | medium | mitigate | Mechanical, semantics-preserving rules only; single-line JSON diff per file; the validate_genexpr non-regression check; MAX compile confirmation listed in SUMMARY as pending. |
| T-fbx-04 | Tampering | Template rewrites (J8) introducing guessed messages, attributes or port roles (Rule #1) | medium | mitigate | Every name is verified against the DB plus the FluCoMa and BEAP refpages and help files. Unverifiable details are removed or marked "(role unverified — confirm in MAX)" and listed in SUMMARY. test_dsp_templates_use_db_objects pins the object names. |
| T-fbx-05 | Repudiation | Doc checker false negatives or positives letting raising forms back in or blocking valid docs | low | mitigate | Self-tests for the 7 known bad forms and 9 good forms, plus a ≥200-snippet coverage floor. |
| T-fbx-06 | Tampering | Edits to committed `patches/**` baselines or `src/**` | medium | mitigate | Neither is in scope. The Task 3 verify asserts an empty `git diff --name-only <base>..HEAD -- patches src`. |
| T-fbx-SC | Tampering | Package installs | low | accept | No new dependency: standard library plus pytest. |
</threat_model>

<verification>
- **Suite.** The baseline comes from Step 0 (3251 or 3171 passed, with 1 xfailed / 1 xpassed / 29 warnings). The final run is the baseline plus only the new tests in tests/test_doc_signatures.py, with 1/1 unchanged. `git status --porcelain` is unchanged across every pytest run.
- **RED evidence.** Q/red-task1.txt, Q/red-task2.txt and Q/red-task3.txt each show the task's guards failing before the fix. The exception is the J4 lock, which is green by design.
- **Existing tests.** No existing test file is edited. test_claude_md, test_agent_skills, test_commands and test_project stay green.
- **Commits.** Three `(Q16)` commits, each within its task's files. The stash list equals Q/stash-list-before.txt. Nothing is pushed.
- **Scope.** `git diff --name-only <base>..HEAD` lists only `files_modified` paths. Nothing changes under `patches/` or `src/`.
- **Python 3.10.** `ast.parse(feature_version=(3, 10))` passes on tests/test_doc_signatures.py.
</verification>

<success_criteria>
- An agent following CLAUDE.md, the skills, the commands or TECHNICAL writes only Patcher API calls that bind. It never strips connections through `replace_box`, and it writes js `anything` handlers that match.
- Gain guidance is correct for both `*~` and `gain~`.
- Templates name only objects, messages and attributes that exist.
- A missing config.json no longer halts a build: the project is core-only.
- Variable-I/O guidance points at the real rule store.
- The gen~ pattern library uses only constructs proven to compile.
- README and TECHNICAL describe the repo as it is.
- A doc-signature test keeps call forms honest from now on.
</success_criteria>

<output>
Create `.planning/quick/261014-fbx-implement-q16-in-planning-reviews-2026-1/261014-fbx-SUMMARY.md`. It must include:

- **Figures.**
  - Base and final pytest totals and warnings.
  - The new-test count per task.
  - Snippets checked by the doc scanner.
  - The Q/counts.txt values, with the counting method (planner decision 7).
- **Finding table.** For each of J1, J2, J3, J4, J6, J7, J8, J9, J10, J11, J12 and J13: fixed or already fixed, the files touched, and the guarding test name. J4 and J7 cite Q11 d6a4393a and Q6. Note that J5 was done in Q12.
- **Extra raising forms the scanner found** beyond the five J3 bullets, and any checker refinement made during RED.
- **Decisions taken:** planner decisions 1-10, especially:
  - the J10 choice and its evidence;
  - the J12 library-wide scope;
  - that the TECHNICAL J1 wording leaves the codegen stub to Q31.
- **Pending user confirmation in MAX** (rule 9; human-verify, non-blocking):
  - **The 10 rewritten patterns/gen files compile.** Add `patterns/gen` to Max's File Preferences search path, or copy a file next to a scratch patch. Create `gen~ <name>`, confirm the Max console shows no compile error, and spot-check behavior: adsr-envelope gate on/off traces A/D/S/R; noise-generator `type 0/1/2` switches white/pink/brown; buffer-player and buffer-recorder read and write channel 1.
  - Every BEAP port role or FluCoMa connection marked unverified in the templates.
  - gain~ slider-position guidance: optional, already user-confirmed via memory.
- **Out of scope / doc impact, not edited (rule 8):**
  - `dsp_critic.py`'s suggestion text still says `scale 0 127 0. 1.`. That is fine for MIDI ints; float sources need `scale 0. 127. 0. 1.` (a code change for a later task).
  - `codegen.py` still emits a named `anything` parameter (Q31).
  - INDEX.md's "External reverb~" wording.
  - Unresolved ABL-style names in max-9.2-changes.md.
  - Q15's pending doc impacts: add_m4l_gen_synth feeds both plugout~ inlets, and the TECHNICAL builder row.
  - README describes `patches/` while the release archive export-ignores it.
- **Base caveat.** If the soft base check failed, the test-count caveat and the recompute commands.
</output>
