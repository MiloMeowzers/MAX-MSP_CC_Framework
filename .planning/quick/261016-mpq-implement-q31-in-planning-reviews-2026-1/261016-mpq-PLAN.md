---
phase: quick-261016-mpq
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/maxpat/ext_templates.py
  - src/maxpat/externals.py
  - src/maxpat/critics/ext_critic.py
  - src/maxpat/codegen.py
  - src/maxpat/code_validation.py
  - src/maxpat/hooks.py
  - tests/fixtures/min_api_stub/c74_min.h
  - tests/test_codegen_external_fixes.py
  - tests/test_externals.py
  - .claude/skills/max-ext-agent/SKILL.md
  - .claude/skills/max-ext-agent/BOUNDARIES.md
autonomous: true
requirements: [G5, G6, G7, G8, G3]

estimate:
  tokens: 180000
  raw_tokens: 180000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "Operator scaffolding a DSP external named `foo~` gets `<project>/foo_tilde/source/foo_tilde.cpp` declaring `class foo_tilde : public object<foo_tilde>` and `MIN_EXTERNAL(foo_tilde);`, plus `<project>/foo_tilde/help/foo~.maxhelp`, whose external box text is `foo~`. min-api's CMake (max-sdk-base max-pretarget) turns the `foo_tilde` folder back into `foo~.mxo`. Names without `~` keep today's paths and code."
    - "Operator generating the DSP template for 0, 1, 2 or 3 signal inputs with 1 or 2 outputs gets C++ that passes `clang++ -std=c++17 -fsyntax-only` against the min-api stub (tests/fixtures/min_api_stub/c74_min.h, which models min-api's sample_operator performer). One output returns `sample`; 2 or more return `samples<N>`. Output k returns `input{k+1}`, or `0.0` once the inputs run out. A 0-input external declares one control inlet, as min.phasor~ does. At f1f39215 the 1:1, 2:1, 2:2 and 0:1 cases and every `foo~` render fail that compile. num_outputs < 1 or num_inputs < 0 raises ValueError."
    - "Operator running ext_critic on any generated template (names foo~, my.ext~, plain; all three archetypes) gets no blocker. On f1f39215's `foo~` code the critic now reports one blocker, \"'foo~' is not a valid C++ identifier (class declaration and MIN_EXTERNAL)\", instead of \"Missing MIN_EXTERNAL()\". A MIN_EXTERNAL, #include or class that appears only in a comment no longer counts. A helper class declared before the object class no longer causes a false name-mismatch blocker."
    - "Operator calling setup_min_devkit(ext_dir) gets min-devkit cloned with `git clone --recursive` into `ext_dir/min-devkit` (cwd = ext_dir), and `min-devkit/` listed once in `ext_dir/.gitignore`, with existing lines kept. In a git repo enclosing ext_dir, `git status` shows ext_dir/.gitignore but nothing under min-devkit/. No git command runs outside ext_dir, and no submodule is added to any repo. A re-run is idempotent, and a half-present checkout is repaired inside min-devkit itself. The CMake FATAL_ERROR hint and the max-ext-agent SKILL.md / BOUNDARIES.md describe the same thing. Tests never touch the network or the framework repo."
    - "Operator generating an N4M script with dict_access names like `my-dict`, `1st.dict`, `a b`, `say\"hi` and both `my-dict` and `my_dict` gets a script that passes `node --check`. Helpers are named getDict_my_dict / setDict_my_dict, a collision gets a `_2` suffix, and every dict-name string is JSON-escaped. At f1f39215, `getDict_my-dict` is a SyntaxError. Plain names keep their function names."
    - "Operator generating a js script with an anything handler gets `function anything() {`, with `var args = arrayfromargs(arguments);` as the first body line. Run in node with MAX's globals emulated (messagename = \"foo\"), `anything(\"x\", 2)` sends outlet 0 the list [\"foo\", \"x\", 2]. validate_js(engine=\"js\") reports no error; the code is ES5. At f1f39215, `anything(msg)` binds the first argument to msg and leaves args undefined."
    - "Operator running validate_code_file on a .gendsp gets findings from every codebox: all top-level codeboxes and those in gen subpatchers. When the file holds more than one codebox, or a nested one, each finding is prefixed `[path] codebox '<id>': ` and carries `path`; at f1f39215 only the first codebox is checked. A file with exactly one top-level codebox gives exactly validate_genexpr's output (the 13 committed .gendsp files are unchanged). A .js file whose only `require('max-api')` or `inlets =` text sits in a comment or string is classified by its real code. validate_js's own comment handling (Q22, a9bf5a16) is untouched, and tests/test_js_lint.py stays green."
    - "After every task, the full suite shows no failure outside the 2 baseline q29-check failures, and more passed tests than the baseline (5228 passed, 5 xfailed, 1 xpassed, 2 failed at f1f39215). At least 3 `(Q31)` commits touch only files_modified paths; nothing under patches/ changes; the stash list is unchanged."
  artifacts:
    - path: "src/maxpat/ext_templates.py"
      provides: "cpp_identifier / cmake_folder_name; DSP template valid for 0/1/2+ inputs; every template's class is cpp_identifier(name); CMake hint points at setup_min_devkit"
      contains: "def cpp_identifier"
    - path: "src/maxpat/externals.py"
      provides: "scaffold_external folder/source naming via cmake_folder_name; setup_min_devkit clone + per-external .gitignore"
      contains: "MIN_DEVKIT_URL"
    - path: "src/maxpat/critics/ext_critic.py"
      provides: "comment-masked structural checks, identifier check, MIN_EXTERNAL found with any argument"
      contains: "_VALID_IDENT_RE"
    - path: "src/maxpat/codegen.py"
      provides: "N4M dict identifiers sanitized and de-duplicated; JSON-escaped dict literals; js anything() reads messagename/arrayfromargs"
      contains: "arrayfromargs(arguments)"
    - path: "src/maxpat/hooks.py"
      provides: "validate_code_file walks every .gendsp codebox"
      contains: "iter_patchers"
    - path: "tests/fixtures/min_api_stub/c74_min.h"
      provides: "syntax-check stand-in for min-api: the template surface plus the sample_operator performer specializations"
      contains: "sample_operator"
    - path: "tests/test_codegen_external_fixes.py"
      provides: "red-first regression tests for G5, G6, G7 and the G3/G8 rest"
      contains: "class TestG5TracerTildeDspExternal"
  key_links:
    - from: "src/maxpat/externals.py (scaffold_external)"
      to: "src/maxpat/ext_templates.py (cmake_folder_name, cpp_identifier)"
      via: "folder and source file get the CMake-safe form; the class gets the C++ identifier"
      pattern: "cmake_folder_name\\("
    - from: "src/maxpat/critics/ext_critic.py"
      to: "src/maxpat/ext_templates.py (cpp_identifier)"
      via: "the invalid-identifier blocker suggests the same mapping the templates use"
      pattern: "cpp_identifier\\("
    - from: "src/maxpat/critics/ext_critic.py"
      to: "src/maxpat/genexpr_parse.py (mask)"
      via: "one C-style comment/string mask for the structural checks"
      pattern: "mask\\("
    - from: "src/maxpat/hooks.py (validate_code_file)"
      to: "src/maxpat/walk.py (iter_patchers, path_prefix, path_ids)"
      via: "every patcher of the .gendsp is walked; nested findings carry their path"
      pattern: "iter_patchers\\("
    - from: "src/maxpat/code_validation.py (detect_js_type)"
      to: "src/maxpat/code_validation.py (_js_mask)"
      via: "type detection reads code outside comments and strings"
      pattern: "_js_mask\\("
---

<objective>
This plan implements fix-plan Q31 (review findings G5, G6, G7, the rest of G8, and the validate_code_file part of G3): codegen and Min-DevKit template fixes.
- **G5, externals.**
  - The DSP template compiles for 0, 1 and 2+ inputs (`input1…`, or zeros per output).
  - A MAX name `foo~` becomes the C++ class `foo_tilde`, in the folder/file form min-api's CMake expects.
  - ext_critic checks that the class name is a valid identifier and stops misreporting `MIN_EXTERNAL`.
- **G7.** setup_min_devkit clones min-devkit into the external's own gitignored directory instead of running a submodule add in the framework repo.
- **G6.**
  - generate_n4m_script sanitizes dict names into valid JS identifiers.
  - generate_js_script's `anything()` uses `messagename` / `arrayfromargs`.
- **G8 rest.** `validate_js` ignores comments when parsing inlets/outlets; Q22 did that (a9bf5a16), and this plan confirms it. The remaining raw-text parse is `detect_js_type`, which validate_code_file uses to pick the js validator, and this plan fixes it.
- **G3 rest.** validate_code_file checks every codebox in a .gendsp.
- **Tests.** One regression class per finding, written red first.

Purpose: each item makes the agent emit code that fails in MAX, Node or the compiler (an undeclared `input`, `class foo~`, `getDict_my-dict`, an anything() that never sees its selector), mutates the framework repo, or silently skips validation.

Output:
- tests/test_codegen_external_fixes.py and tests/fixtures/min_api_stub/c74_min.h (new);
- the fixes in ext_templates, externals, ext_critic, codegen, code_validation and hooks;
- the max-ext-agent doc lines;
- the PD-12 existing-test edits;
- three `(Q31)` commits, each behind a pre-commit full-suite gate and followed by its task's `<verify>` as a post-commit audit.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@CLAUDE.md
@.planning/reviews/2026-10-11-fix-plan.md

Read only the named parts. Line numbers are as of f1f39215.
- `.planning/reviews/2026-10-11-repo-review.md`: rows G3 and G5-G8 (lines 139-144) and J1 (line 172).
- `.planning/reviews/2026-10-11-fix-plan.md`: the Q31 section (lines 549-559) and Q19 / Q22 (lines 358-433) for what already landed.
- Each task's `<read_first>` lists its own source ranges.
</context>

<rules>
Copied verbatim from `.planning/reviews/2026-10-11-fix-plan.md` ("Rules for every task"). They bind every task below.

1. Read the referenced finding IDs in the review report first; they contain the evidence and the expected fix.
2. Write each regression test **first**. It should reproduce the finding (red) before you fix it (green).
3. **Never edit committed patch files** (`patches/**/*.maxpat|.gendsp|.maxhelp|.js`). They are user-confirmed baselines, and the integration tests depend on them. If one produces a new finding:
   - false positive: fix the checker;
   - true positive in a committed patch: allowlist it with a written reason and list it in SUMMARY.md.
4. Run `python3 -m pytest -q` before and after.
   - Allowed baseline failures until Q3 lands: the 3 `test_review_patch_no_blockers` cases (minitaur, physics-composition, timestretch).
   - From Q3 onward the suite must be fully green.
5. Never `git stash`. Never `git add -A` or `git add .`. Stage explicit paths only.
6. Code must work on Python 3.10.
7. Don't widen scope. If the fix needs a decision the report doesn't make, stop and ask with multiple-choice options.
8. Edit CLAUDE.md, skills or TECHNICAL.md only where the task says to. List any other doc impact in SUMMARY.md.
9. In SUMMARY.md, flag anything that needs the user to confirm in MAX or Live.

Rule 4 at f1f39215: the suite is NOT fully green before this task. Measured at planning: **2 failed, 5228 passed, 5 xfailed, 1 xpassed** (~102 s). Both failures come from the user's `patches/q29-check` project, not from codegen or externals:
- `tests/test_doc_signatures.py::test_readme_patch_table_lists_every_project`;
- `tests/test_uninitialized_state.py::TestCommittedCorpus::test_committed_q24_findings_match_allowlist[patches/q29-check/generated/q29-check.maxpat]`.

They are out of scope (rule 7): do not fix them. The gate for this plan is "no failure outside the baseline set, and more passed tests than the baseline". SUMMARY lists both as a follow-up (unchanged from Q30).

Rule 8: the orchestrator's task statement for Q31 says to update skill docs that still describe the old setup_min_devkit behavior or the `anything(msg)` pattern. The anything() docs were fixed in Q16 (a821f604) and are guarded by `tests/test_doc_signatures.py::test_js_anything_handler_uses_messagename`, so none needs an edit. The setup_min_devkit lines in `.claude/skills/max-ext-agent/SKILL.md` (3 lines) and `BOUNDARIES.md` (1 line) still describe the old behavior; Task 2 updates them (PD-7). No CLAUDE.md or TECHNICAL.md edit. TECHNICAL.md's External Critic table (lines 520-530) gains no row for the identifier check; SUMMARY lists that as doc impact. Module and function docstrings of the edited code are updated.

Additions for this execution environment:
- **Q** = `.planning/quick/261016-mpq-implement-q31-in-planning-reviews-2026-1`. These files go in Q and stay untracked, never staged: base-sha.txt, stash-list-before.txt, baseline-pytest.txt, red-t1.txt, red-t2.txt, red-t3.txt, pytest-t1.txt, pytest-t2.txt, final-pytest.txt, q31-commit-files.txt. The orchestrator commits PLAN and SUMMARY. Never name a scratch script after a stdlib module.
- **Execution.** The executor runs sequentially on the main working tree; every path here is repo-root-relative and every command assumes cwd at the checkout root. At planning, HEAD = `f1f39215` (local main is ahead of origin/main 981b7b80) and the tracked tree is clean.
  - **Hard precondition:** `git merge-base --is-ancestor f1f39215 HEAD` succeeds. If it fails, HALT and report it.
  - **Hard precondition (fresh start only, Q/base-sha.txt absent):**
    - `git diff --quiet HEAD -- src/maxpat/ext_templates.py src/maxpat/externals.py src/maxpat/critics/ext_critic.py src/maxpat/codegen.py src/maxpat/code_validation.py src/maxpat/hooks.py tests/test_externals.py .claude/skills/max-ext-agent` succeeds;
    - neither `tests/test_codegen_external_fixes.py` nor `tests/fixtures/min_api_stub/` exists.

    If either fails, HALT and report which.
- **Step 0 (Task 1, before any source edit):**
  - Write `git rev-parse HEAD` to Q/base-sha.txt and `git stash list` to Q/stash-list-before.txt.
  - Run `python3 -m pytest -q -p no:cacheprovider` into Q/baseline-pytest.txt. Expected: the Rule 4 figures above. If it differs, record it; do not fix it.
- **Toolchain.** At planning, `clang++` (Apple clang 17) and `node` (v24) are on PATH. Tests that need them skip through `shutil.which` when absent. On this machine they must run, not skip: the task's red/green evidence depends on them, so a skip here counts as a failed gate.
- **Network and repo safety (hard).**
  - No test and no executor command may clone, fetch or contact GitHub. setup_min_devkit is exercised only with a monkeypatched `subprocess.run` (in `src.maxpat.externals`).
  - The one real-git test runs `git init` inside tmp_path only.
  - Never run setup_min_devkit or build_external against a real directory.
- **Edit scope.**
  - Only the 11 files_modified paths may change, each only in a task whose `<files>` lists it.
  - Never edit `patches/**`, README.md, TECHNICAL.md, CLAUDE.md, or any other `.claude/`, `src/` or `tests/` file.
  - The only edits allowed to existing test files are those in PD-12. Any other existing test that fails is a code bug: fix the code, never the test. If such a test pins an old behavior Q31 explicitly replaces, stop and report it (rule 7).
- **Generated js stays ES5** (CLAUDE.md js rules): the js generator emits only `var` / `function` forms. N4M output is Node (modern syntax allowed, unchanged).
- **Commits.** One commit per task, at least 3 in total, each message ending `(Q31)`.
  - **Order in every task: pre-commit gate, then commit, then `<verify>`.**
  - **Pre-commit gate:** run this from the checkout root, replacing the trailing `<F>` with `pytest-t1` (Task 1), `pytest-t2` (Task 2) or `final-pytest` (Task 3): `bash -c 'Q=.planning/quick/261016-mpq-implement-q31-in-planning-reviews-2026-1; F="$Q/$1.txt"; python3 -m pytest -q -p no:cacheprovider > "$F" 2>&1; R=$?; tail -1 "$F"; test $R -le 1 || exit 1; python3 -c "import re,sys; b,a=[open(p).read() for p in sys.argv[1:3]]; f=lambda t:{l.split(\" - \")[0].strip() for l in t.splitlines() if l.startswith((\"FAILED \",\"ERROR \"))}; n=lambda t:int((re.findall(r\"(\d+) passed\",t) or [0])[-1]); new=sorted(f(a)-f(b)); print(\"new failures:\",new,\"passed:\",n(b),\"->\",n(a)); sys.exit(1 if new or n(a)<=n(b) else 0)" "$Q/baseline-pytest.txt" "$F"' gate <F>`.
    - It exits 0 only if Q/<F>.txt has no FAILED/ERROR line outside Q/baseline-pytest.txt's set and more passed tests than the baseline.
    - Commit only after it exits 0. Never commit a red task.
  - **`<verify>` is the post-commit audit.** It runs after the task's commit, because it needs that commit to exist (`test $# -ge N`). It re-runs the full suite, which regenerates Q/<F>.txt from the committed tree, and then rechecks the red evidence, the greps, `patches/` and Python 3.10 syntax.
    - If it fails, HALT and report. Do not amend the commit, rewrite history or start the next task.
  - Stage with `git add -- <task files>` and commit with `git commit -m "..." -- <task files>`. Never `git push`; never rewrite history.
- **Context budget.** About 180k in total (low confidence; calibration factor 1, 0 samples).
  - **Per task:** Task 1 ~55k, Task 2 ~60k, Task 3 ~55k, plus SUMMARY ~10k. No task is above ~60k, about 30% of a 200k window, which is the low end of context-budget.md's heavy per-task band.
  - **Rebalanced at revision:** the ext_critic work (PD-4, TestG5ExtCriticIdentifiers, ext_critic and test_critics reads) moved from Task 1 to Task 2. The one-line CMake hint (PD-6, TestG7CmakeHint) moved from Task 2 to Task 1, so ext_templates.py stays in a single task. Each task touches at most 6 files.
  - Each task is a complete unit with its own red file, gate file and `(Q31)` commit; read only its `<read_first>` list.
  - **Stop rule:** after a task's `<verify>` passes, if the executor's context is past ~50%, it stops and reports the last committed task.
- **Resume points.**
  - A fresh executor counts the `(Q31)` commits since Q/base-sha.txt and starts at the first task without one.
  - Before that task, it re-runs the previous task's `<verify>` (the post-commit audit). If the audit fails, it HALTs and reports.
  - It skips Step 0 when Q/base-sha.txt and Q/baseline-pytest.txt exist.
  - Uncommitted edits in the resumed task's `<files>` belong to that task; rerun its red step only if its Q/red-tN.txt is missing.
</rules>

<planner_decisions>
The fix plan names the outcomes. These are the planner's resolutions of what it leaves open (Claude's discretion), each checked at f1f39215. SUMMARY lists PD-1, PD-2, PD-4, PD-5, PD-7, PD-8 and PD-11 for the user to confirm.

**Evidence gathered at planning (read-only, via `gh api` on the Cycling74 repos and local probes):**
- **max-sdk-base `script/max-pretarget.cmake`:**
  - `string(REPLACE "~" "_tilde" THIS_FOLDER_NAME ...)`, then `project(${THIS_FOLDER_NAME})`;
  - `if ("${PROJECT_NAME}" MATCHES ".*_tilde")`, then `string(REGEX REPLACE "_tilde" "~" EXTERN_OUTPUT_NAME_DEFAULT ...)`.

  min-api `script/min-pretarget.cmake` includes it. So a folder named `foo_tilde` builds `foo~.mxo`, and our CMake template's `source/${PROJECT_NAME}.cpp` (evaluated after the include) is `source/foo_tilde.cpp`. min-devkit's own projects follow the same layout (`min.phasor_tilde/min.phasor_tilde.cpp`).
- **min-api `include/c74_min_operator_sample.h`:**
  - the `sample_operator<1, 1>` performer does `auto out = self->m_min_object(in); out_samps[i] = out;`, so a 1:1 operator() must return `sample`: `samples<1>` (a `std::array`) cannot be assigned to a double;
  - the generic performer does `auto out = ins.call();`, then, when numouts > 0, `perform_copy_output` with one overload for `samples<N>` (indexes `vals[chan]`) and one for `const sample val`;
  - `c74_min_api.h:59,68` defines `using sample = double;` and `using samples = std::array<sample, count>;`.
- **min-devkit examples:**
  - `min.phasor~` is `sample_operator<0, 1>` with `sample operator()()` and one control inlet `inlet<> in1 {this, "(number) frequency"}`;
  - `min.xfade~` is `<3, 1>` returning `sample`.
- **Stub compile prototype** (scratchpad, same design as PD-3):
  - at f1f39215, dsp 1:1 fails ("assigning to 'double' from incompatible type 'samples<1>'");
  - 2:2, 0:1 and 2:1 fail ("use of undeclared identifier 'input'");
  - `foo~` fails;
  - 1:2 and the message and scheduler templates compile.

  A prototype of the PD-2 rules compiled 0:1, 1:1, 2:1, 1:2, 2:2, 0:2, 3:2 and 4:4 with class `foo_tilde` in one `clang++ -std=c++17 -fsyntax-only` call (exit 0).
- **Node:** `node --check` on f1f39215's `generate_n4m_script(..., dict_access=["my-dict"])` output fails with "SyntaxError: Unexpected token '-'" at `getDict_my-dict`.
- **Corpus:**
  - the 13 committed .gendsp files each hold at most one codebox, all top-level;
  - the comment-aware detect_js_type prototype (PD-10) classifies all 21 committed .js files exactly as f1f39215 does (20 js, 1 None).
- **Already done (confirm, do not redo):**
  - Q19 (7eaa71fa): empty-text newobj no longer crashes validate_patch, and duplicate box ids are a Layer-1 error. Probe: `Duplicate box id 'obj-2' (2 boxes)`, no exception.
  - Q22 (a9bf5a16): validate_js runs on `_js_mask`, with tests `tests/test_js_lint.py:119` (`// inlets = 2`) and `:127` (`/* outlets = 3 */`).
  - Q16 (a821f604): the anything() docs.

**PD-1. Names (G5).** Two public helpers in src/maxpat/ext_templates.py:
- `cpp_identifier(name: str) -> str`: replace `~` with `_tilde`, then every character outside `[A-Za-z0-9_]` with `_`; prefix `_` when the result is empty or starts with a digit. Examples: `foo~` -> `foo_tilde`, `my.ext~` -> `my_ext_tilde`, `plain` -> `plain`, `2x` -> `_2x`.
- `cmake_folder_name(name: str) -> str`: replace `~` with `_tilde` only, which mirrors max-pretarget. Examples: `foo~` -> `foo_tilde`, `my.ext~` -> `my.ext_tilde` (min-api names that build `my.ext~.mxo`).

How they are used:
- Each of render_message_template, render_dsp_template and render_scheduler_template uses `cpp_identifier(name)` for `class X : public object<X>` and `MIN_EXTERNAL(X);`.
- render_test_template includes `"<cmake_folder_name(name)>.cpp"`; its TEST_CASE label keeps the MAX name.
- scaffold_external:
  - writes root = `project_dir / cmake_folder_name(name)` and `source/<folder>.cpp`;
  - keeps `help/<name>.maxhelp`, using the MAX name: MAX finds help by object name, and the help box text stays `foo~`;
  - keeps its return keys.

Names that are already valid identifiers produce byte-identical code and paths. Docstrings saying "valid C++ identifier" become "MAX object name (mapped through cpp_identifier)".

**PD-2. DSP template rules (G5).** In render_dsp_template:
- **Arguments:** `num_inputs` must be an int >= 0 and `num_outputs` an int >= 1 (bool rejected); otherwise raise ValueError naming both values and the supported range. At f1f39215 0 outputs never compiled (`samples<0>` initialized with one element). A min-api `<1, 0>` sink would need `void operator()`; SUMMARY lists it as a follow-up.
- **Signal inlets:** unchanged when num_inputs >= 1.
- **0 inputs:** exactly one `inlet<>  m_input  { this, "(anything) messages" };`, as min.phasor~ does.
- **Outlets:** unchanged.
- **operator() parameters:** `sample input1, ..., sample inputN` (none for 0 inputs). This also replaces the 1-input `sample input`.
- **Output values:** output k (0-based) is `input{k+1}` when k < num_inputs, else `0.0`.
- **One output:** `sample operator()(<params>) {` ... `return <v0>;`.
- **Two or more outputs:** `samples<N> operator()(<params>) {` ... `return { v0, v1, ... };`.
- **Body:** keep the `// TODO: implement DSP processing` comment; the function body closes with `}` and no trailing `;`.
- **Everything else unchanged:** MIN_DESCRIPTION/TAGS/AUTHOR, params, dspsetup and m_samplerate.

**PD-3. The min-api stub (tests/fixtures/min_api_stub/c74_min.h).** It is not min-api; it is the smallest stand-in that lets clang type-check the three templates the way min-api would. Its header comment cites the min-api lines above. It contains:
- `#pragma once`; `<array>`, `<cstddef>`, `<functional>`, `<initializer_list>`, `<type_traits>`, `<utility>`, `<vector>`.
- In `namespace c74 { namespace min {`:
  - **Samples and atoms:**
    - `using sample = double;`; `template <size_t N> using samples = std::array<sample, N>;`;
    - `struct atom` (constructible from double and from const char*, with `operator double() const`); `using atoms = std::vector<atom>;`.
  - **Objects:** `struct object_base {};`; `template <class T> struct object : object_base {};`; `using function = std::function<atoms(const atoms&, int)>;`.
  - **Ports and handlers:**
    - `template <class = void>` structs `inlet` (ctor `object_base*, const char*, const char* = ""`), `outlet` (same ctor plus a variadic `send`), `message` (ctors `object_base*, const char*, function` and `object_base*, const char*, const char*, function`) and `timer` (ctor `object_base*, function`; `delay(double)`; `stop()`);
    - `struct range` (ctor from `std::initializer_list<double>`);
    - `template <class T> struct attribute` (variadic ctor `object_base*, const char*, T, A&&...`; `operator T() const`).
  - **Operators:** `struct sample_operator_base {};` and `template <size_t I, size_t O> struct sample_operator : sample_operator_base` with static constexpr `input_count()` / `output_count()`.
  - **A `stub` namespace that mirrors min-api's performer selection exactly:**
    - when `std::is_base_of<sample_operator<1, 1>, T>`: call with one double and assign the result to a `double`;
    - else when `<1, 0>`: call with one double and ignore the result;
    - else: build `samples<T::input_count()>`, call through `std::make_index_sequence`, and copy the result through two overloads: a template that indexes `vals[c]` for `c < output_count()`, and one taking `const sample`;
    - `check(T&)` runs the performer only when T derives from sample_operator_base.
- **Macros:**
  - `MIN_DESCRIPTION` / `MIN_TAGS` / `MIN_AUTHOR` expand to `static constexpr const char* class_description` / `class_tags` / `class_author`;
  - `MIN_FUNCTION` expands to `[this](const c74::min::atoms& args, const int inlet) -> c74::min::atoms`;
  - `MIN_EXTERNAL(cls)` defines `void ext_main(void* p)` calling `c74::min::stub::check(*static_cast<cls*>(p))`.

The test file keeps the stub honest with a fidelity class:
- these must FAIL to compile:
  - a 1:1 class returning `samples<1>`;
  - a 2:2 class returning `{ input }` with parameters `input1, input2`;
  - `class foo~`;
- these must compile:
  - the min.phasor~ shape (`<0, 1>`, `sample operator()()`, one control inlet);
  - the min.xfade~ shape (`<3, 1>` returning `sample`).

Every compile is `clang++ -std=c++17 -fsyntax-only -I tests/fixtures/min_api_stub <files>`; the files are written to tmp_path, and several files go in one invocation where possible. SUMMARY states plainly that this is a stand-in check: a real build against min-devkit needs the user (rule 9).

**PD-4. ext_critic (G5; implemented in Task 2).** Task 1 needs no critic edit: the current regexes (`MIN_EXTERNAL\s*\(\s*(\w+)\s*\)`, `class\s+(\w+)\s*:`) already accept the `foo_tilde` code that Task 1's templates emit.
- **Mask:** `from src.maxpat.genexpr_parse import mask` (C-style `//` and `/* */` comments and double-quoted string contents blanked, same length). Known limit: a char literal containing a double quote (`'"'`), which no template emits.
- `_VALID_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")`.
- **Check 1:** search the include regex on the RAW code; it is satisfied only by a match whose first character (`#`) survives in the mask, so a commented-out include no longer counts.
- **Checks 2 and 3 run on the mask:**
  - MIN_EXTERNAL regex: `MIN_EXTERNAL\s*\(\s*([^)]*?)\s*\)`. No match gives the existing "Missing MIN_EXTERNAL()" blocker (text unchanged); an empty argument gives the blocker "MIN_EXTERNAL() names no class".
  - Object class: `\bclass\s+([^\s:{;<>,()]+)\s*:\s*public\s+object\s*<`, falling back to the legacy first `\bclass\s+([^\s:{;<>,()]+)\s*:`.
  - **Identifier check:** each distinct token among the class name and the MIN_EXTERNAL argument that fails `_VALID_IDENT_RE` gives one blocker, `'<tok>' is not a valid C++ identifier (<sites>)`, where sites is "class declaration", "MIN_EXTERNAL" or both joined by " and ". The suggestion is `Use '<cpp_identifier(tok)>' in both places -- a MAX name's '~' maps to '_tilde', and min-api's CMake builds the folder <cmake_folder_name form> as the '~' external`.
  - **Name mismatch:** checked only when both names were found and differ; the existing text is unchanged.
- **Checks 4-6** (inlet, sample/vector operator, timer) run on the mask.
- **Check 7** (TODO notes) runs on the raw code, unchanged.
- Module docstring: list the identifier check and the comment masking.

**PD-5. setup_min_devkit (G7).** In src/maxpat/externals.py:
- `MIN_DEVKIT_URL = "https://github.com/Cycling74/min-devkit.git"`.
- `setup_min_devkit(ext_dir) -> bool` keeps its signature. Steps:
  1. `ext_dir = Path(ext_dir)`; if it is not an existing directory, return False with no write and no call.
  2. `_ensure_gitignored(ext_dir)`:
     - if any stripped line of `ext_dir/.gitignore` is `min-devkit`, `min-devkit/`, `/min-devkit` or `/min-devkit/`, write nothing;
     - otherwise append a comment line `# Min-DevKit checkout (setup_min_devkit) -- never committed` and the line `min-devkit/`, adding a newline first when the file is non-empty and lacks one;
     - create the file when it is missing;
     - keep every existing byte; write only that file.

     This runs before any clone, so a partial clone is never stageable.
  3. If `ext_dir/min-devkit/source/min-api` exists, return True.
  4. If `ext_dir/min-devkit` exists:
     - with a `.git` entry (dir or file): run `git submodule update --init --recursive` with cwd = `ext_dir/min-devkit`. This is min-devkit's own nested min-api, never the framework repo;
     - without a `.git` entry: return False and never delete user files.
  5. Otherwise run `["git", "clone", "--recursive", MIN_DEVKIT_URL, "min-devkit"]` with cwd = str(ext_dir), capture_output, text, timeout=600.
  6. A non-zero return code returns False.
  7. Finally return whether the marker exists.

  `OSError` (git missing, unwritable .gitignore) and `subprocess.TimeoutExpired` return False.
- No other git command, never a submodule add, and never a cwd outside ext_dir.
- The module docstring line for setup_min_devkit changes accordingly.

**PD-6. CMake hint (G7; implemented in Task 1, with the other ext_templates.py edits).** The new text holds before Task 2 lands: setup_min_devkit already exists, and the manual clone works on its own. render_cmake_template's FATAL_ERROR text becomes `min-api not found. Run setup_min_devkit(ext_dir), or: git clone --recursive https://github.com/Cycling74/min-devkit.git min-devkit`. Nothing else in the template changes.

**PD-7. max-ext-agent docs (G7, orchestrator directive).** In `.claude/skills/max-ext-agent/SKILL.md`, rewrite the Capabilities bullet, the Key Functions line and Output Protocol step 2, and in `BOUNDARIES.md` the "DOES" bullet, to say: setup_min_devkit clones Min-DevKit (recursively, with min-api) into the external's own `min-devkit/` folder and lists it in that folder's `.gitignore`, outside the framework repo's index.
- The new wording does not use the word for the old mechanism.
- SKILL.md must keep `scaffold_external`, `build_external` and `### Archetype Reference`, and must not contain the words that `tests/test_agent_skills.py::test_ext_agent_not_stub` bans.
- One sentence also notes that a MAX name with `~` scaffolds as `<name>_tilde/` (PD-1).

**PD-8. N4M dict identifiers (G6).** In generate_n4m_script:
- Each dict name is `str(name)`; exact duplicates are emitted once (first occurrence).
- Suffix: `re.sub(r"[^A-Za-z0-9_$]", "_", name)`, or `_` when empty. When a suffix is already used, append `_2`, `_3`, ... until it is unused.
- Each dict section begins with the comment `// dict <json.dumps(name)> -> getDict_<s>() / setDict_<s>(data)`.
- Every JS string literal is `json.dumps(...)`: the getDict/setDict name arguments, and the whole post-message prefixes `json.dumps("Error getting dict " + name + ": ")` / `json.dumps("Error setting dict " + name + ": ")` followed by `+ e.message`.
- Plain names (`mydict`) keep their function names and message text.
- The docstring documents the mapping.

**PD-9. js anything() (G6, J1).** In generate_js_script:
- `_handler_args["anything"]` becomes `""`.
- For an `anything` handler, the emitted body starts with the 4-space-indented line `var args = arrayfromargs(arguments);`, followed by the caller's body.
- Every other handler type's output is unchanged.
- The docstring: MAX passes the selector in `messagename` and the arguments in `arguments`, never as named parameters; the body reads `messagename` and the generated `args` array; ES5 only.

**PD-10. detect_js_type ignores comments (G8, the inlets/outlets parse validate_code_file still did on raw text).**
- `n4m` iff a match of the existing require regex on the RAW code has its `require` token intact at the same offset in `_js_mask(code)[0]`.
- `js` iff `inlets\s*=` matches the mask.
- Order and return values are unchanged.
- validate_js itself is not touched (Q22).

**PD-11. validate_code_file walks every codebox (G3 rest).** For .gendsp:
- After the unchanged JSON-error path, collect every `(path, box)` where `box["maxclass"] == "codebox"` and `"code" in box`, over `walk.iter_patchers(data, scope="gen")` in walker order (non-dict entries skipped).
- None found: the existing warning, unchanged.
- One db: `_gate_db()`.
- **Exactly one codebox and it is top-level:** return `validate_genexpr(code, db=db)` unchanged.
- **Otherwise,** every finding of every codebox becomes `ValidationResult(r.layer, r.level, f"{walk.path_prefix(path)}codebox '{box.get('id', '<unknown>')}': {r.message}", auto_fixed=r.auto_fixed, path=walk.path_ids(path))`.
- The .js branch and the other suffixes are unchanged.
- The docstring describes the walk.

**PD-12. Existing-test edits allowed (old behavior Q31 replaces).**
1. tests/test_externals.py line 136: `assert "samples<1>" in code` becomes `assert "sample operator()(sample input1)" in code` (PD-2 evidence: the `<1, 1>` performer cannot take `samples<1>`).
2. tests/test_externals.py class TestSetupMinDevkit (lines 862-890): reword the class docstring, the `test_setup_min_devkit_not_present` docstring and its mock comment to the clone behavior. No assertion changes; both tests stay green unedited otherwise.

Keep every other line of that file.

**PD-13. Out of scope** (SUMMARY follow-ups):
- the DSP help patch's fixed 1-in/1-out external box: with 0 inputs it still feeds cycle~ into the control inlet;
- `<1, 0>` sink externals;
- ignoring `build/` in the external's .gitignore;
- C++ keyword checks in ext_critic;
- quoting `"` in MIN_DESCRIPTION text;
- N4M handler-name escaping;
- the TECHNICAL.md critic-table row;
- the 2 q29-check baseline failures;
- a real min-devkit build (rule 9).
</planner_decisions>

<tasks>

<task type="tracer" tdd="true">
  <name>Task 1: Step 0; tracer scaffold `foo~` DSP -> foo_tilde source -> no blocker from the current critic -> stub compile, then every input/output count, every template and the CMake hint (G5, PD-6)</name>
  <files>src/maxpat/ext_templates.py, src/maxpat/externals.py, tests/fixtures/min_api_stub/c74_min.h, tests/test_codegen_external_fixes.py, tests/test_externals.py</files>
  <precondition>`git merge-base --is-ancestor f1f39215 HEAD` succeeds, and `clang++` is on PATH.</precondition>
  <read_first>
    - .planning/reviews/2026-10-11-repo-review.md row G5 (line 141)
    - src/maxpat/ext_templates.py (all, 317 lines; render_cmake_template's FATAL_ERROR is line 275)
    - src/maxpat/critics/ext_critic.py 20-28 only (regexes: confirms foo_tilde already passes; no edit in this task)
    - src/maxpat/externals.py 1-90 and 209-279
    - tests/test_ext_templates.py (all, 96 lines); tests/test_externals.py 110-140, 280-295 and 386-480
    - planner_decisions: evidence, PD-1 to PD-3, PD-6, PD-12 item 1
  </read_first>
  <behavior>
    - Module setup (tests/test_codegen_external_fixes.py): docstring "Q31 / G5 G6 G7 G8 G3: codegen and Min-DevKit template regression tests; tmp_path only, no network". Helpers: `STUB_DIR = Path("tests/fixtures/min_api_stub")`, `needs_clang = pytest.mark.skipif(shutil.which("clang++") is None, ...)`, and `_syntax_check(tmp_path, sources: dict[str, str]) -> subprocess.CompletedProcess` (writes each source to tmp_path, then one clang++ `-std=c++17 -fsyntax-only -I <STUB_DIR>` call over all of them).
    - **TestG5TracerTildeDspExternal** (red at HEAD):
      - `scaffold_external(tmp_path, "foo~", "dsp", "d", num_inputs=2, num_outputs=2)` returns root `tmp_path/"foo_tilde"`, source `foo_tilde/source/foo_tilde.cpp` and help `foo_tilde/help/foo~.maxhelp`;
      - the source contains `class foo_tilde : public object<foo_tilde>, public sample_operator<2, 2>`, `samples<2> operator()(sample input1, sample input2)`, `return { input1, input2 };` and `MIN_EXTERNAL(foo_tilde);`;
      - `review_external(src, archetype="dsp")` has no blocker. This is the current critic: it reports "Missing MIN_EXTERNAL" at HEAD and passes once PD-1 is in. PD-4 lands in Task 2;
      - the help JSON has a box whose text is `foo~`;
      - (needs_clang) `_syntax_check` of the source returns 0.
    - **TestG5DspIoCounts** (red), parametrized over (0,1), (1,1), (2,1), (1,2), (2,2), (0,2), (3,2):
      - the operator() parameter list is exactly `sample input1..N`;
      - the return type is `sample` for one output and `samples<N>` otherwise;
      - the return values follow PD-2 (`0.0` once the inputs run out);
      - the sample_operator<N, M> args match;
      - for 0 inputs, exactly one `(anything) messages` inlet and no `(signal) audio input`;
      - review_external has no blocker.

      ValueError for num_outputs=0 and for num_inputs=-1.
    - **TestG5StubCompile** (needs_clang, red): one `_syntax_check` over the 7 DSP cases named `foo~` (with one param), plus message and scheduler templates named `foo~` and `my.ext~`, plus `plain` for all three: return code 0, with stderr shown on failure.
    - **TestG5StubFidelity** (needs_clang, green guard): the 3 must-fail shapes each fail (each in its own call) and the 2 must-compile shapes compile (PD-3).
    - **TestG5CppNames** (red):
      - cpp_identifier and cmake_folder_name follow the PD-1 examples;
      - each render_*_template with `foo~` declares `class foo_tilde` and `MIN_EXTERNAL(foo_tilde);`, and contains no `foo~` outside string literals;
      - render_test_template("foo~") includes `"foo_tilde.cpp"`;
      - a `plain` scaffold keeps `plain/source/plain.cpp` and `plain/help/plain.maxhelp` (green guard).
      - Define the template set that TestG5StubCompile compiles as a module-level helper, `_template_cases()`, returning (label, archetype, code) tuples, so Task 2's critic class can reuse it.
    - **TestG7CmakeHint** (red; PD-6): render_cmake_template("x") contains `setup_min_devkit` and `git clone --recursive`, and not the words `git submodule`.
  </behavior>
  <action>
**Step 0.** Do the rules' Execution and Step 0 items: the hard preconditions, base-sha, the stash list and the baseline suite.

**Red.**
- Create tests/fixtures/min_api_stub/c74_min.h (PD-3) and tests/test_codegen_external_fixes.py with the `<behavior>` classes.
- Apply PD-12 item 1 to tests/test_externals.py.
- Run `python3 -m pytest -q -p no:cacheprovider tests/test_codegen_external_fixes.py tests/test_externals.py tests/test_ext_templates.py` into Q/red-t1.txt. It must show failures, and TestG5StubFidelity must already pass: the stub has to catch the f1f39215 bugs before anything is fixed.

**Green: tracer first.**
- In src/maxpat/ext_templates.py, add cpp_identifier and cmake_folder_name (PD-1) and apply the PD-2 rules in render_dsp_template.
- In src/maxpat/externals.py, give scaffold_external the PD-1 folder and source naming; only names containing `~` change.
- Run TestG5TracerTildeDspExternal alone until it passes. Its critic assertion needs no ext_critic edit (PD-4 note), and this task never edits ext_critic. Then expand.

**Green: expansion.**
- Use cpp_identifier in render_message_template and render_scheduler_template, and cmake_folder_name in render_test_template (PD-1).
- In render_cmake_template, change only the FATAL_ERROR text (PD-6).
- Update the module docstrings of ext_templates and externals, and the docstrings of render_dsp_template, generate_external_code and scaffold_external.
- Leave setup_min_devkit and ext_critic for Task 2.

**Gate, commit, audit (the rules' order):**
1. Pre-commit gate: run the rules' gate command with `<F>` = `pytest-t1`. It must exit 0.
2. Commit the 5 task files: `fix(externals): DSP template compiles for 0, 1 and 2+ inputs; foo~ scaffolds as foo_tilde with class foo_tilde; CMake hint points at setup_min_devkit (Q31)`.
3. Post-commit audit: run `<verify>` now. It needs the commit from step 2 and regenerates Q/pytest-t1.txt. If it fails, HALT and report.
  </action>
  <verify>
    <automated>bash -c 'Q=.planning/quick/261016-mpq-implement-q31-in-planning-reviews-2026-1 && touch "$Q/pytest-t1.txt" && python3 -m pytest -q -p no:cacheprovider > "$Q/pytest-t1.txt" 2>&1; R=$?; tail -1 "$Q/pytest-t1.txt"; test $R -le 1 || exit 1; python3 -c "import re,sys; b,a=[open(p).read() for p in sys.argv[1:3]]; f=lambda t:{l.split(\" - \")[0].strip() for l in t.splitlines() if l.startswith((\"FAILED \",\"ERROR \"))}; n=lambda t:int((re.findall(r\"(\d+) passed\",t) or [0])[-1]); new=sorted(f(a)-f(b)); print(\"new failures:\",new,\"passed:\",n(b),\"->\",n(a)); sys.exit(1 if new or n(a)<=n(b) else 0)" "$Q/baseline-pytest.txt" "$Q/pytest-t1.txt" || exit 1; ST=$(git status --porcelain -- patches) || exit 1; test -z "$ST" || exit 1; grep -iq -e failed -e error "$Q/red-t1.txt" && python3 -m pytest -q -p no:cacheprovider -rs tests/test_codegen_external_fixes.py -k "G5" > /dev/null 2>&1 && ! python3 -m pytest -q -p no:cacheprovider -rs tests/test_codegen_external_fixes.py -k "G5" 2>&1 | grep -q SKIPPED && grep -q "def cpp_identifier" src/maxpat/ext_templates.py && grep -q "def cmake_folder_name" src/maxpat/ext_templates.py && grep -q "setup_min_devkit(ext_dir)" src/maxpat/ext_templates.py && grep -q "class TestG7CmakeHint" tests/test_codegen_external_fixes.py && grep -q "sample_operator" tests/fixtures/min_api_stub/c74_min.h && grep -q "class TestG5TracerTildeDspExternal" tests/test_codegen_external_fixes.py && grep -q "class TestG5StubFidelity" tests/test_codegen_external_fixes.py && C=$(git log --format=%H --fixed-strings --grep="(Q31)" "$(cat "$Q/base-sha.txt")"..HEAD) && set -- $C && test $# -ge 1 && python3 -c "import ast,sys;[ast.parse(open(f).read(),feature_version=(3,10)) for f in sys.argv[1:]]" src/maxpat/ext_templates.py src/maxpat/externals.py tests/test_codegen_external_fixes.py tests/test_externals.py'</automated>
  </verify>
  <done>Red was recorded (Q/red-t1.txt) with the stub fidelity class already green. The pre-commit gate passed, and then the post-commit `<verify>` passed and regenerated Q/pytest-t1.txt with no G5 test skipped.
- `foo~` scaffolds as foo_tilde/ with class foo_tilde, and its help file is foo~.maxhelp.
- The DSP template type-checks for 0-3 inputs and 1-2 outputs; every template reviews with no blocker from the current critic.
- The CMake hint names setup_min_devkit and the recursive clone.
- One `(Q31)` commit touches only the 5 Task 1 files.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: ext_critic checks identifiers and ignores commented-out code (G5, PD-4); setup_min_devkit clones into the external's own gitignored min-devkit/, never a submodule of the framework repo; max-ext-agent docs follow (G7)</name>
  <files>src/maxpat/critics/ext_critic.py, src/maxpat/externals.py, .claude/skills/max-ext-agent/SKILL.md, .claude/skills/max-ext-agent/BOUNDARIES.md, tests/test_codegen_external_fixes.py, tests/test_externals.py</files>
  <precondition>Task 1's `(Q31)` commit exists since Q/base-sha.txt, and Task 1's `<verify>` passes.</precondition>
  <read_first>
    - .planning/reviews/2026-10-11-repo-review.md rows G5 and G7 (lines 141 and 143)
    - src/maxpat/critics/ext_critic.py (all, 123 lines); src/maxpat/genexpr_parse.py 112-121 (mask)
    - src/maxpat/ext_templates.py: grep `def cpp_identifier` and `def cmake_folder_name`, signatures and docstrings only (added in Task 1)
    - tests/test_codegen_external_fixes.py: grep `def _template_cases` (Task 1's template set)
    - tests/test_critics.py 920-1000 and 1060-1110
    - src/maxpat/externals.py 1-35, plus `def setup_min_devkit` through the end of that function (Task 1 shifted the f1f39215 lines 281-334, so grep for it)
    - .claude/skills/max-ext-agent/SKILL.md (all); .claude/skills/max-ext-agent/BOUNDARIES.md 1-12
    - tests/test_externals.py 858-895; tests/test_agent_skills.py 160-195
    - planner_decisions PD-4, PD-5, PD-7 and PD-12 item 2
  </read_first>
  <behavior>
    - **TestG5ExtCriticIdentifiers** (red at Task 1's commit unless marked; Task 1 does not touch the critic):
      - f1f39215-shape `foo~` message code (class foo~, `object<foo~>`, `MIN_EXTERNAL(foo~);`) gives exactly one blocker containing "'foo~' is not a valid C++ identifier", naming both sites, with `foo_tilde` in the suggestion, and no "Missing MIN_EXTERNAL" finding;
      - a commented `// MIN_EXTERNAL(old_name);` above valid code gives no blocker;
      - MIN_EXTERNAL only inside a `/* */` comment gives the Missing blocker;
      - an include only in a comment gives the include blocker;
      - `class helper : public base_thing {};` declared before `class my_object : public object<my_object>` with `MIN_EXTERNAL(my_object);` gives no mismatch blocker;
      - `MIN_EXTERNAL()` gives "names no class";
      - green guard: `class a : public object<a>` with `MIN_EXTERNAL(b);` still gives the existing mismatch blocker text;
      - green guard: every template from `_template_cases()` reviews with no blocker.
    - A `fake_run` fixture monkeypatches `src.maxpat.externals.subprocess.run`. It records `(argv, cwd)`; for a `git clone` it creates `<cwd>/<last arg>/source/min-api`; for `git submodule update` it creates `<cwd>/source/min-api`; and it returns a CompletedProcess with returncode 0 (configurable per test).
    - **TestG7SetupMinDevkitClones** (red unless marked):
      - on an empty ext dir, the result is True after exactly one call, `["git", "clone", "--recursive", MIN_DEVKIT_URL, "min-devkit"]` with cwd == str(ext_dir);
      - no recorded argv contains "submodule" together with "add", and every cwd resolves inside ext_dir;
      - `.gitignore` holds the line `min-devkit/` exactly once;
      - a second call returns True with no new call and still one line (idempotent);
      - a pre-existing `.gitignore` of `build/\n*.o` (no trailing newline) keeps those two lines and gains the entry on its own line;
      - with `min-devkit/.git` present but no min-api: one `["git", "submodule", "update", "--init", "--recursive"]` call with cwd == str(ext_dir/"min-devkit"), and True;
      - `min-devkit/` present without `.git`: False, no call, and the folder's files are untouched;
      - the clone returns 1: False;
      - run raises FileNotFoundError: False;
      - a missing ext_dir: False, no call, nothing created;
      - green guard: marker already present gives True and no call.
    - **TestG7GitIgnoresCheckout** (red; real local git, tmp_path only):
      - `git init` a repo in tmp_path, with ext_dir = repo/"ext" holding a tracked-looking file;
      - inside a `monkeypatch.context()`, run setup_min_devkit with the fake clone, which also writes `min-devkit/README.md`;
      - after leaving the context, `git -C repo status --porcelain --untracked-files=all` lists `ext/.gitignore` and nothing under `ext/min-devkit/`.
    - **TestG7ExtAgentDocs** (red): `.claude/skills/max-ext-agent/SKILL.md` and `BOUNDARIES.md` contain no "submodule" (case-insensitive); SKILL.md mentions `min-devkit/` and `.gitignore`, and still names setup_min_devkit, scaffold_external and build_external.
  </behavior>
  <action>
**Red.**
- Add the `<behavior>` classes to tests/test_codegen_external_fixes.py.
- Apply PD-12 item 2 (docstrings and the comment only) to tests/test_externals.py.
- Run `python3 -m pytest -q -p no:cacheprovider tests/test_codegen_external_fixes.py tests/test_externals.py tests/test_critics.py tests/test_agent_skills.py` into Q/red-t2.txt. It must show failures.

**Green.**
- In src/maxpat/critics/ext_critic.py: PD-4. Import `mask` from genexpr_parse and cpp_identifier / cmake_folder_name from ext_templates, then add `_VALID_IDENT_RE` and the identifier blocker. Each of checks 1-7 reads raw code, the mask or both, exactly as PD-4 lists it. Update the module docstring. Run TestG5ExtCriticIdentifiers and tests/test_critics.py until green.
- In src/maxpat/externals.py: MIN_DEVKIT_URL, `_ensure_gitignored` and the PD-5 setup_min_devkit; rewrite its docstring and the module docstring line.
- Edit the 4 doc lines in SKILL.md and BOUNDARIES.md (PD-7). Change nothing else in those files.
- Run the tests above until green. tests/test_agent_skills.py and tests/test_doc_signatures.py must stay green, apart from the baseline failure.

**Gate, commit, audit (the rules' order):**
1. Pre-commit gate: run the rules' gate command with `<F>` = `pytest-t2`. It must exit 0.
2. Commit the 6 task files: `fix(externals): ext_critic checks C++ identifiers and ignores commented-out code; setup_min_devkit clones min-devkit into the external's own gitignored folder, no framework-repo submodule; max-ext-agent docs follow (Q31)`.
3. Post-commit audit: run `<verify>` now. It needs the commit from step 2 and regenerates Q/pytest-t2.txt. If it fails, HALT and report.
  </action>
  <verify>
    <automated>bash -c 'Q=.planning/quick/261016-mpq-implement-q31-in-planning-reviews-2026-1 && touch "$Q/pytest-t2.txt" && python3 -m pytest -q -p no:cacheprovider > "$Q/pytest-t2.txt" 2>&1; R=$?; tail -1 "$Q/pytest-t2.txt"; test $R -le 1 || exit 1; python3 -c "import re,sys; b,a=[open(p).read() for p in sys.argv[1:3]]; f=lambda t:{l.split(\" - \")[0].strip() for l in t.splitlines() if l.startswith((\"FAILED \",\"ERROR \"))}; n=lambda t:int((re.findall(r\"(\d+) passed\",t) or [0])[-1]); new=sorted(f(a)-f(b)); print(\"new failures:\",new,\"passed:\",n(b),\"->\",n(a)); sys.exit(1 if new or n(a)<=n(b) else 0)" "$Q/baseline-pytest.txt" "$Q/pytest-t2.txt" || exit 1; ST=$(git status --porcelain -- patches) || exit 1; test -z "$ST" || exit 1; grep -iq -e failed -e error "$Q/red-t2.txt" && grep -q "_VALID_IDENT_RE" src/maxpat/critics/ext_critic.py && grep -q "class TestG5ExtCriticIdentifiers" tests/test_codegen_external_fixes.py && grep -q "MIN_DEVKIT_URL" src/maxpat/externals.py && grep -q "def _ensure_gitignored" src/maxpat/externals.py && grep -q "class TestG7SetupMinDevkitClones" tests/test_codegen_external_fixes.py && grep -q "class TestG7GitIgnoresCheckout" tests/test_codegen_external_fixes.py && grep -q "setup_min_devkit" .claude/skills/max-ext-agent/SKILL.md && C=$(git log --format=%H --fixed-strings --grep="(Q31)" "$(cat "$Q/base-sha.txt")"..HEAD) && set -- $C && test $# -ge 2 && python3 -c "import ast,sys;[ast.parse(open(f).read(),feature_version=(3,10)) for f in sys.argv[1:]]" src/maxpat/externals.py src/maxpat/critics/ext_critic.py tests/test_codegen_external_fixes.py tests/test_externals.py'</automated>
  </verify>
  <done>Red was recorded (Q/red-t2.txt). The pre-commit gate passed, and then the post-commit `<verify>` passed and regenerated Q/pytest-t2.txt.
- The critic reports invalid identifiers instead of a missing MIN_EXTERNAL, ignores commented-out code and finds the object class past helper classes. Every Task 1 template still reviews with no blocker.
- setup_min_devkit clones into ext_dir/min-devkit and ignores it there: once, idempotently, keeping existing lines.
- It repairs a half-present checkout inside min-devkit only, refuses a non-git folder, and never runs a git command outside ext_dir.
- A real local repo does not see the checkout.
- The max-ext-agent docs describe the clone, as Task 1's CMake hint already does.
- No test touched the network. The second `(Q31)` commit touches only the 6 Task 2 files.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: N4M dict identifiers and js anything() (G6); validate_code_file checks every .gendsp codebox and detects js outside comments (G3/G8 rest); final gate, commit audit and SUMMARY</name>
  <files>src/maxpat/codegen.py, src/maxpat/code_validation.py, src/maxpat/hooks.py, tests/test_codegen_external_fixes.py</files>
  <precondition>Task 2's `(Q31)` commit exists since Q/base-sha.txt, Task 2's `<verify>` passes, and `node` is on PATH.</precondition>
  <read_first>
    - .planning/reviews/2026-10-11-repo-review.md rows G3, G6 and G8 (lines 139, 142 and 144) and J1 (line 172)
    - src/maxpat/codegen.py 1-14 and 342-471
    - src/maxpat/code_validation.py 674-720 (`_js_mask` contract) and 1046-1061 (detect_js_type)
    - src/maxpat/hooks.py 535-543 (`_gate_db`) and 1243-1333 (validate_code_file)
    - src/maxpat/walk.py 196-206 and 225-280; src/maxpat/validation.py 1479-1483 (who reports .gendsp top-level codeboxes)
    - tests/test_codegen.py 600-790; tests/test_code_validation.py 476-580; tests/test_js_lint.py 110-135
    - planner_decisions PD-8 to PD-11
  </read_first>
  <behavior>
    - `needs_node = pytest.mark.skipif(shutil.which("node") is None, ...)`.
    - **TestG6N4MDictIdentifiers** (red):
      - `generate_n4m_script([bang handler], dict_access=["my-dict", "my_dict", "1st.dict", "a b", 'say"hi', "my-dict"])` declares exactly the async functions getDict_my_dict, getDict_my_dict_2, getDict_1st_dict, getDict_a_b and getDict_say_hi (and the setDict_ twins), 5 each;
      - it contains `maxAPI.getDict("my-dict")` and `maxAPI.getDict("say\"hi")`;
      - (needs_node) `node --check` on the written file exits 0;
      - green guard: `dict_access=["mydict"]` still declares getDict_mydict / setDict_mydict, with the post text `Error getting dict mydict: `.
    - **TestG6JsAnythingHandler** (red):
      - `generate_js_script(1, 1, handlers=[{"type": "anything", "body": "outlet(0, [messagename].concat(args));"}])` contains `function anything() {` with `    var args = arrayfromargs(arguments);` as the next line, and no `anything(msg`;
      - `validate_js(code, engine="js")` has no error;
      - (needs_node) a driver script in tmp_path runs the code with Node's vm module, in a context with `messagename = "foo"`, `outlet` recording its arguments, `arrayfromargs` slicing its argument and `post` as a no-op; calls `anything("x", 2)`; prints JSON; the result is `[[0, ["foo", "x", 2]]]`;
      - green guard: default handlers are unchanged (`function msg_int(v)`, `function list()`).
    - **TestG8DetectJsTypeIgnoresComments** (red unless marked):
      - `"// require('max-api') is for node.script\ninlets = 1;\noutlets = 1;\nfunction bang() { outlet(0, 1); }"` is "js";
      - `"// inlets = 2\nfunction bang() {}"` is None;
      - `'post("inlets = 3");'` is None;
      - green guards: `const maxAPI = require("max-api");` is "n4m" and `"inlets = 2;\noutlets = 1;"` is "js";
      - validate_code_file on the first sample written as a .js file in tmp_path reports js findings (a "Handler functions found" info), not the N4M "No maxAPI" warning.
    - **TestG8ValidateJsCommentsConfirmed** (green guard): validate_js on `"// inlets = 2\n// outlets = 1\nfunction bang() {}"` reports both missing-declaration errors (Q22 behavior kept).
    - **TestG3ValidateCodeFileEveryCodebox** (red unless marked):
      - a .gendsp with two top-level codeboxes `obj-1` (`out1 = in1;`) and `obj-2` (`out1 = delay(in1, 100);`) gives an error containing `codebox 'obj-2': ` and "delay()";
      - a codebox inside a gen subpatcher box `obj-9` (a newobj with an embedded `patcher` holding codebox `obj-10` using delay()) gives an error with path `obj-9`, its message starting with `[` and containing `codebox 'obj-10': `;
      - green guard: a single top-level codebox gives messages equal to `[r.message for r in validate_genexpr(code)]`;
      - green guard: no codebox gives the existing warning.
  </behavior>
  <action>
**Red.**
- Add the `<behavior>` classes to tests/test_codegen_external_fixes.py.
- Run `python3 -m pytest -q -p no:cacheprovider tests/test_codegen_external_fixes.py tests/test_codegen.py tests/test_code_validation.py tests/test_js_lint.py` into Q/red-t3.txt. It must show failures.

**Green.**
- In src/maxpat/codegen.py: PD-8 in generate_n4m_script and PD-9 in generate_js_script (ES5 only); update the module and function docstrings.
- In src/maxpat/code_validation.py: PD-10 in detect_js_type only; validate_js is untouched. Update the docstring.
- In src/maxpat/hooks.py: PD-11 in validate_code_file, importing walk inside the function like the existing code_validation import; update the docstring and the module docstring line.
- Probe: run validate_code_file over every committed `patches/**/*.gendsp` and `patches/**/*.js`, before and after the change (the before run from `git show <base>:src/maxpat/hooks.py` in a temp module, or by recording the output at the red step). The outputs must be identical; list the counts in SUMMARY.

**Gate, commit, audit, SUMMARY (the rules' order):**
1. Pre-commit gate: run the rules' gate command with `<F>` = `final-pytest`. It must exit 0.
2. Commit the 4 task files: `fix(codegen): N4M dict helpers get valid JS identifiers, js anything() reads messagename/arrayfromargs; validate_code_file checks every .gendsp codebox and detects js outside comments (Q31)`.
3. Post-commit audit: run `<verify>` now. It needs all 3 `(Q31)` commits and regenerates Q/final-pytest.txt. It also writes the commit file audit to Q/q31-commit-files.txt and checks it against files_modified. If it fails, HALT and report.
4. Only after `<verify>` passes, write SUMMARY.md per `<output>`.
  </action>
  <verify>
    <automated>bash -c 'Q=.planning/quick/261016-mpq-implement-q31-in-planning-reviews-2026-1 && touch "$Q/final-pytest.txt" && python3 -m pytest -q -p no:cacheprovider > "$Q/final-pytest.txt" 2>&1; R=$?; tail -1 "$Q/final-pytest.txt"; test $R -le 1 || exit 1; python3 -c "import re,sys; b,a=[open(p).read() for p in sys.argv[1:3]]; f=lambda t:{l.split(\" - \")[0].strip() for l in t.splitlines() if l.startswith((\"FAILED \",\"ERROR \"))}; n=lambda t:int((re.findall(r\"(\d+) passed\",t) or [0])[-1]); new=sorted(f(a)-f(b)); print(\"new failures:\",new,\"passed:\",n(b),\"->\",n(a)); sys.exit(1 if new or n(a)<=n(b) else 0)" "$Q/baseline-pytest.txt" "$Q/final-pytest.txt" || exit 1; ST=$(git status --porcelain -- patches) || exit 1; test -z "$ST" || exit 1; grep -iq -e failed -e error "$Q/red-t3.txt" && ! python3 -m pytest -q -p no:cacheprovider -rs tests/test_codegen_external_fixes.py 2>&1 | grep -q SKIPPED && grep -q "arrayfromargs(arguments)" src/maxpat/codegen.py && grep -q "_js_mask(" src/maxpat/code_validation.py && grep -q "iter_patchers(" src/maxpat/hooks.py && grep -q "class TestG6N4MDictIdentifiers" tests/test_codegen_external_fixes.py && grep -q "class TestG3ValidateCodeFileEveryCodebox" tests/test_codegen_external_fixes.py && S=$(git stash list) && test "$S" = "$(cat "$Q/stash-list-before.txt")" && C=$(git log --format=%H --fixed-strings --grep="(Q31)" "$(cat "$Q/base-sha.txt")"..HEAD) && set -- $C && test $# -ge 3 && for c in $C; do git show --name-only --format= "$c" || exit 1; done > "$Q/q31-commit-files.txt" && test -s "$Q/q31-commit-files.txt" && python3 -c "import sys; ok=set(sys.argv[2:]); bad=sorted({l.strip() for l in open(sys.argv[1]) if l.strip() and l.strip() not in ok}); print(\"committed files outside files_modified:\", bad); sys.exit(1 if bad else 0)" "$Q/q31-commit-files.txt" src/maxpat/ext_templates.py src/maxpat/externals.py src/maxpat/critics/ext_critic.py src/maxpat/codegen.py src/maxpat/code_validation.py src/maxpat/hooks.py tests/fixtures/min_api_stub/c74_min.h tests/test_codegen_external_fixes.py tests/test_externals.py .claude/skills/max-ext-agent/SKILL.md .claude/skills/max-ext-agent/BOUNDARIES.md && python3 -c "import ast,sys;[ast.parse(open(f).read(),feature_version=(3,10)) for f in sys.argv[1:]]" src/maxpat/codegen.py src/maxpat/code_validation.py src/maxpat/hooks.py tests/test_codegen_external_fixes.py'</automated>
  </verify>
  <done>Red was recorded (Q/red-t3.txt). The pre-commit gate passed, and then the post-commit `<verify>` passed and regenerated Q/final-pytest.txt: no failure outside the 2 baseline failures, more passed tests than 5228, and nothing in the new test file skipped.
- N4M dict helpers are valid, unique JS identifiers with escaped literals, and node accepts the script.
- js anything() reads messagename and arrayfromargs(arguments) in ES5.
- validate_code_file checks every .gendsp codebox and classifies js outside comments; the committed corpus output is unchanged.
- At least 3 `(Q31)` commits, all within files_modified and none under patches/; the stash list is unchanged.</done>
</task>

</tasks>

<threat_model>
Security config: enforcement on (absent = enabled), ASVS level 1. This is local code generation and validation. The only network-capable code path is setup_min_devkit's clone of a fixed, official URL, which tests replace with a fake. There are no package installs, no auth and no crypto. What matters:
- generated code must not be injectable through user-supplied names;
- the framework repo must not be mutated by external scaffolding;
- tests must stay offline and in tmp_path;
- git hygiene.

## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Caller-supplied names (dict names, external names, handler bodies) -> generated JS / C++ source | Arbitrary strings pasted into code; must stay data, not code |
| setup_min_devkit -> git / GitHub | Fetches third-party source into the user's tree; must stay confined to the external's folder |
| Test suite -> filesystem, git, clang++, node | Tests run next to the real repo and must touch only tmp_path |
| Concurrent Claude instances -> git | Broad staging or stash can sweep in or strand another instance's work |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-mpq-01 | Tampering | generate_n4m_script string literals built from dict names | medium | mitigate | Every dict-name literal and post prefix is `json.dumps(...)`; identifiers are reduced to `[A-Za-z0-9_$]` (PD-8). TestG6N4MDictIdentifiers uses `say"hi` and `node --check`. |
| T-mpq-02 | Tampering | setup_min_devkit adding a submodule to, or staging into, the framework repo | high | mitigate | Clone into ext_dir/min-devkit only, gitignored there before the clone; the only other git command runs inside min-devkit (PD-5). TestG7SetupMinDevkitClones asserts every argv and cwd; TestG7GitIgnoresCheckout proves an enclosing repo does not see the checkout. |
| T-mpq-03 | Tampering | `.gitignore` write clobbering user content | low | mitigate | Append-only and idempotent; existing bytes kept; only that one file written (PD-5); tested with a no-trailing-newline file. |
| T-mpq-04 | Elevation of Privilege | Cloning third-party code (min-devkit) that later builds and runs | medium | accept | Same fixed official Cycling74 URL as at f1f39215, now a module constant; never caller-supplied; runs only when the agent sets up an external; tests never clone. |
| T-mpq-05 | Tampering | ext_critic / scaffold accepting `foo~` and emitting invalid C++ or CMake target names | low | mitigate | cpp_identifier / cmake_folder_name everywhere (PD-1); identifier blocker in the critic (PD-4). |
| T-mpq-06 | Denial of Service | validate_code_file walking a hostile .gendsp | low | accept | `walk.iter_patchers` is iterative and cycle-safe and never loads external files; the per-codebox cost is the existing validate_genexpr. |
| T-mpq-07 | Tampering | Tests invoking clang++ / node / git | low | mitigate | Every input file and repo lives in tmp_path; clang++ runs `-fsyntax-only` (no output files); node runs `--check` or a vm driver over generated text only; no network. |
| T-mpq-08 | Repudiation | Broad git staging during the task | medium | mitigate | `git add -- <files>` / `git commit -- <files>` only; the final verify audits every `(Q31)` commit's files against files_modified and checks the stash list. |
| T-mpq-SC | Tampering | npm/pip/cargo installs | high | mitigate | No package-manager install in this plan; clang++, node and git are pre-installed system tools used only on generated text in tmp_path. Any install the executor finds itself needing is a stop-and-ask (rule 7). |
</threat_model>

<verification>
- Every task's `<verify>` passes. Q/red-t1.txt, red-t2.txt and red-t3.txt each show failures recorded before the fix (Task 1's with TestG5StubFidelity already green).
- Q/pytest-t1.txt, pytest-t2.txt and final-pytest.txt each show no FAILED/ERROR line outside the 2 baseline failures, and more passed tests than the baseline's 5228; the 5 xfailed / 1 xpassed split is unchanged. On this machine no test in tests/test_codegen_external_fixes.py is skipped.
- `git status --porcelain -- patches` is empty; `git stash list` is unchanged; the `(Q31)` commits touch only files_modified paths; the only existing-test edits are those in PD-12.
- Confirmed, not redone: Q19's empty-text and duplicate-id fixes, Q22's comment-aware validate_js, and Q16's anything() docs.
- After SUMMARY.md is written, its decisions section names the planner calls:

  <automated>bash -c 'S=.planning/quick/261016-mpq-implement-q31-in-planning-reviews-2026-1/261016-mpq-SUMMARY.md && D=$(awk "/^## Decisions to confirm/{f=1;next} /^## /{f=0} f" "$S") && test -n "$D" && for k in PD-1 PD-2 PD-4 PD-5 PD-7 PD-8 PD-11; do printf "%s\n" "$D" | grep -q -- "$k" || exit 1; done && grep -q "^## Confirm in MAX" "$S"'</automated>
</verification>

<success_criteria>
- G5, G6, G7, and the G3/G8 rest each have regression tests that were red at f1f39215 and are green now, all in tmp_path and offline.
- The Min-DevKit templates type-check for every supported input/output count and for `~` names. The scaffold lays `~` externals out the way min-api's CMake builds them, and ext_critic reports what is actually wrong.
- setup_min_devkit never touches the framework repo's git state.
- Generated N4M and js code is valid in Node / ES5 and reads MAX's anything() contract correctly.
- validate_code_file covers every .gendsp codebox and picks the js validator from real code. Committed corpus output is unchanged.
- Only the max-ext-agent SKILL.md / BOUNDARIES.md lines describing setup_min_devkit changed among the docs.
- SUMMARY lists the decisions to confirm, the MAX/Live confirmations, behavior changes, doc impact and follow-ups.
</success_criteria>

<output>
Create `.planning/quick/261016-mpq-implement-q31-in-planning-reviews-2026-1/261016-mpq-SUMMARY.md` when done. It must include:
- `## Decisions to confirm`: PD-1, PD-2, PD-4, PD-5, PD-7, PD-8 and PD-11, one line each with the choice made.
- `## Confirm in MAX` (rule 9):
  - a real min-devkit build of a scaffolded `foo~` DSP external with 0 and 2 inputs (`setup_min_devkit` then `build_external`; needs network and the Xcode command-line tools), and that `foo~.mxo` loads in MAX 9 and passes audio;
  - a node.script running a generated N4M script with a hyphenated dict name;
  - a js box running a generated anything() handler (`foo 1 2` posts the selector and the list).
- Behavior changes:
  - `~` scaffold paths;
  - the 1-output `sample` return type;
  - the num_outputs >= 1 ValueError;
  - the new critic blocker text;
  - setup_min_devkit's writes and commands;
  - prefixed messages for multi-codebox .gendsp files;
  - js type detection.
- Probes: the corpus validate_code_file before/after counts, and the stub-compile case list.
- Doc impact: the TECHNICAL.md External Critic table row (not edited).
- Follow-ups: PD-13 and the 2 q29-check baseline failures.
- Commits: the three `(Q31)` hashes.
</output>
