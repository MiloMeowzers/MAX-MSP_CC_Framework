---
phase: quick-261016-mpq
plan: 01
status: complete
subsystem: codegen / externals / code validation
tags: [Q31, G3, G5, G6, G7, G8, min-devkit, n4m, js, gendsp]
requires: []
provides:
  - "ext_templates.cpp_identifier / cmake_folder_name"
  - "DSP template valid for 0/1/2+ inputs (sample vs samples<N>)"
  - "ext_critic identifier blocker + comment-masked checks"
  - "setup_min_devkit: clone into the external's gitignored min-devkit/"
  - "N4M dict identifiers sanitized; js anything() reads messagename/arrayfromargs"
  - "validate_code_file walks every .gendsp codebox; detect_js_type masks comments"
affects: [max-ext-agent, max-js-agent, max-dsp-agent]
tech-stack:
  added: []
  patterns:
    - "clang++ -fsyntax-only against a min-api stand-in header (tests/fixtures/min_api_stub)"
    - "node --check / vm driver over generated JS"
key-files:
  created:
    - tests/fixtures/min_api_stub/c74_min.h
    - tests/test_codegen_external_fixes.py
  modified:
    - src/maxpat/ext_templates.py
    - src/maxpat/externals.py
    - src/maxpat/critics/ext_critic.py
    - src/maxpat/codegen.py
    - src/maxpat/code_validation.py
    - src/maxpat/hooks.py
    - tests/test_externals.py
    - .claude/skills/max-ext-agent/SKILL.md
    - .claude/skills/max-ext-agent/BOUNDARIES.md
decisions:
  - "PD-1: foo~ -> class foo_tilde (cpp_identifier), folder/source foo_tilde (cmake_folder_name), help foo~.maxhelp"
  - "PD-2: DSP operator() takes input1..N; returns sample (1 out) or samples<N>; 0 inputs get one control inlet; num_outputs < 1 raises"
  - "PD-4: ext_critic masks comments/strings; invalid-identifier blocker replaces the misleading Missing MIN_EXTERNAL"
  - "PD-5: setup_min_devkit clones into ext_dir/min-devkit, gitignored there first; never a submodule add"
  - "PD-8: N4M dict helpers use sanitized, de-duplicated suffixes; all literals json.dumps-escaped"
  - "PD-11: validate_code_file checks every .gendsp codebox; single top-level codebox output unchanged"
metrics:
  duration: "~40 min"
  completed: 2026-10-16
actuals:
  tokens: 19300
  tasks: 3
  commits: 3
plan_head_before: f1f39215bf6b3636e76ecc266003b5272dc982be
plan_head_after: a04b94a46a92699fe77ea0aca8986712aa5f83bc
---

# Phase quick-261016-mpq Plan 01: Q31 codegen and Min-DevKit template fixes Summary

`foo~` externals now scaffold as `foo_tilde/` with class `foo_tilde`. The DSP template type-checks for 0-3 inputs and 1-2 outputs against a min-api stand-in. ext_critic reports invalid identifiers and ignores commented-out code. setup_min_devkit clones into the external's own gitignored `min-devkit/` and never adds a submodule. Generated N4M dict helpers and js `anything()` handlers now run in Node/MAX. validate_code_file checks every .gendsp codebox and detects js outside comments.

## Commits

| Task | Commit | Files |
|------|--------|-------|
| 1: DSP template, `~` names, CMake hint (G5, PD-6) | 8bb5ea43 | ext_templates.py, externals.py, c74_min.h stub, test_codegen_external_fixes.py, test_externals.py |
| 2: ext_critic identifiers + masking; setup_min_devkit clone; ext-agent docs (G5, G7) | d6b824a6 | ext_critic.py, externals.py, SKILL.md, BOUNDARIES.md, test_codegen_external_fixes.py, test_externals.py |
| 3: N4M dict identifiers, js anything(), every-codebox validation, comment-aware detect_js_type (G6, G8, G3) | a04b94a4 | codegen.py, code_validation.py, hooks.py, test_codegen_external_fixes.py |

## Test evidence

- Baseline at f1f39215: 2 failed, 5228 passed, 5 xfailed, 1 xpassed. Both failures are the known q29-check ones.
- After Task 1: 5264 passed. After Task 2: 5298 passed. Final: **5317 passed**, the same 2 baseline failures, 5 xfailed, 1 xpassed.
- Red evidence: red-t1.txt (31 failed; TestG5StubFidelity already green), red-t2.txt (15 failed), red-t3.txt (11 failed).
- tests/test_codegen_external_fixes.py: 89 tests, none skipped (clang++, node and git all ran).
- `git status -- patches` is empty, the stash list is unchanged, and every `(Q31)` commit touches only files_modified paths.

## Decisions to confirm

- **PD-1:** a MAX name `foo~` maps to class `foo_tilde` (`cpp_identifier`: `~` becomes `_tilde`, other non-identifier characters become `_`, and `_` is prefixed when the name starts with a digit). Folder and source become `foo_tilde/source/foo_tilde.cpp` (`cmake_folder_name`: only `~` becomes `_tilde`, mirroring max-pretarget). Help stays `help/foo~.maxhelp`. Names without `~` keep their paths.
- **PD-2:** the DSP operator() takes `sample input1..N`. It returns `sample` for 1 output and `samples<N>` for 2 or more. Output k is `input{k+1}`, or `0.0` once the inputs run out. 0 inputs get one `(anything) messages` control inlet. `num_outputs < 1`, `num_inputs < 0`, and bool or non-int counts raise ValueError.
- **PD-4:** ext_critic runs its structural checks on a comment/string mask (genexpr_parse.mask). The include check only counts a `#include` that is not in a comment. An invalid identifier gives one blocker per token (`'foo~' is not a valid C++ identifier (class declaration and MIN_EXTERNAL)`) instead of "Missing MIN_EXTERNAL". `MIN_EXTERNAL()` with no argument gives "names no class". The object class is the one deriving from `object<...>`, so a helper class declared first no longer causes a false mismatch.
- **PD-5:** setup_min_devkit first writes `min-devkit/` to `ext_dir/.gitignore` (append-only, idempotent, existing bytes kept). It then runs `git clone --recursive MIN_DEVKIT_URL min-devkit` with cwd = ext_dir. A half-present checkout that has `.git` is repaired with `git submodule update --init --recursive` inside min-devkit itself. A non-git `min-devkit/` folder returns False and is left untouched. OSError and timeout return False.
- **PD-7:** the max-ext-agent SKILL.md (Capabilities bullet, Key Functions line, Output Protocol step 2) and the BOUNDARIES.md DOES bullet now describe the clone into the external's own gitignored `min-devkit/`. The Key Functions line also notes that `~` names scaffold as `<name>_tilde/`.
- **PD-8:** each N4M dict helper suffix is `re.sub(r"[^A-Za-z0-9_$]", "_", name)`. A collision gets `_2`, `_3` and so on, and exact duplicate names are emitted once. Every dict-name literal and error-message prefix is `json.dumps`-escaped, and each section gets a `// dict "<name>" -> getDict_x() / setDict_x(data)` comment.
- **PD-11:** validate_code_file walks every patcher via `walk.iter_patchers(data, scope="gen")`. With exactly one top-level codebox it returns validate_genexpr's output unchanged. Otherwise each finding is prefixed `[path] codebox '<id>': ` and carries `path`.

## Confirm in MAX

Rule 9: none of this has been confirmed in MAX or Live yet.
- **Real min-devkit build:** scaffold `foo~` DSP externals with 0 inputs and with 2 inputs, run `setup_min_devkit` then `build_external` (needs network and the Xcode command-line tools), and check that `foo~.mxo` loads in MAX 9 and passes audio. The stub compile is only a stand-in check, not min-api.
- **N4M script:** run a generated N4M script with a hyphenated dict name (`my-dict`) in node.script and check that `getDict_my_dict()` reads the dict.
- **js anything():** run a generated `anything()` handler in a js box and check that sending `foo 1 2` posts or outputs the selector and the list.

## Behavior changes

- **`~` scaffold paths:** `scaffold_external(..., "foo~", ...)` now writes `foo_tilde/` and `foo_tilde/source/foo_tilde.cpp` (it used to write `foo~/source/foo~.cpp`). The help file is still `foo~.maxhelp`, and the return keys are unchanged.
- **1-output DSP:** the return type is now `sample`, not `samples<1>`. The 1-input parameter is now `input1`, not `input`.
- **Output-count check:** `render_dsp_template` raises ValueError when num_outputs < 1 (0 outputs never compiled).
- **New critic text:** the identifier blocker and "MIN_EXTERNAL() names no class". A MIN_EXTERNAL, #include or class that appears only in a comment no longer counts.
- **setup_min_devkit:** writes `ext_dir/.gitignore` and runs `git clone --recursive` in ext_dir, or `git submodule update` inside `min-devkit/` for a half-present checkout. It never runs `git submodule add`. The timeout is 600 s, and a missing ext_dir returns False.
- **Multi-codebox .gendsp:** when a file holds more than one codebox, or a nested one, every codebox is validated and each message carries a prefix.
- **js type detection:** `require('max-api')` or `inlets =` inside a comment or string no longer decides the type.
- **N4M and js codegen:** dict helper names are sanitized. The js `anything()` handler now has no parameters and its body starts with `var args = arrayfromargs(arguments);`.

## Probes

- **Corpus validate_code_file:** ran over all 34 committed files (13 .gendsp, 21 .js) before the change (at d6b824a6, i.e. before Task 3) and after it. The JSON outputs are byte-identical: 42 findings (.gendsp: 13 info + 8 warning; .js: 17 info + 4 warning).
- **Stub-compile cases (one clang++ call):**
  - DSP `foo~` with 1 param for (0,1), (1,1), (2,1), (1,2), (2,2), (0,2) and (3,2);
  - DSP `my.ext~` and `plain` at 1:1;
  - message and scheduler templates for `foo~`, `my.ext~` and `plain`.
- **Stub fidelity:**
  - rejected: 1:1 returning `samples<1>`; 2:2 returning `{ input }`; `class foo~`;
  - accepted: the min.phasor~ shape (<0,1>) and the min.xfade~ shape (<3,1>).
- **Confirmed, not redone:** Q22's comment-aware validate_js (TestG8ValidateJsCommentsConfirmed; tests/test_js_lint.py green) and Q16's anything() docs (test_doc_signatures guard green).

## Deviations from Plan

None that change behavior. Minor notes:
- In Task 1 I also reworded the scaffold_external docstring line "Does NOT create min-devkit/ submodule" so it points at setup_min_devkit and build_external. Docstring only.
- Task 1's test module imports `cpp_identifier` / `cmake_folder_name` through the module (`ext_templates.cpp_identifier`), so the red run could show per-test failures and a green TestG5StubFidelity instead of a collection error.

## Doc impact

- The TECHNICAL.md External Critic table (around lines 520-530) has no row yet for the new identifier check or the comment masking. Not edited (rule 8).

## Known Stubs

None. (`tests/fixtures/min_api_stub/c74_min.h` is a deliberate test stand-in for min-api, not a code stub.)

## Follow-ups

These are the PD-13 items:
- The DSP help patch still uses a fixed 1-in/1-out external box, so with 0 inputs it feeds cycle~ into the control inlet.
- `<1, 0>` sink externals (they need `void operator()`).
- `build/` is not ignored in the external's .gitignore.
- ext_critic has no C++ keyword checks.
- `"` in MIN_DESCRIPTION text is not quoted.
- N4M handler names are not escaped.
- The TECHNICAL.md critic-table row.
- A real min-devkit build (rule 9).
- The 2 q29-check baseline failures, unchanged from Q30: `test_readme_patch_table_lists_every_project` and `test_committed_q24_findings_match_allowlist[patches/q29-check/...]`.

## Self-Check: PASSED

- All created and modified files exist.
- Commits 8bb5ea43, d6b824a6 and a04b94a4 are present in `git log`.
