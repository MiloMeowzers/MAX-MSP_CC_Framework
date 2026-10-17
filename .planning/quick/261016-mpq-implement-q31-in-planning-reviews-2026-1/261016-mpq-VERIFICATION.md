---
phase: quick-261016-mpq
verified: 2026-10-16T23:39:37Z
status: human_needed
score: 7/7 must-haves verified
covered_files:
  - .claude/skills/max-ext-agent/BOUNDARIES.md
  - .claude/skills/max-ext-agent/SKILL.md
  - .planning/quick/261016-mpq-implement-q31-in-planning-reviews-2026-1/261016-mpq-PLAN.md
  - .planning/quick/261016-mpq-implement-q31-in-planning-reviews-2026-1/261016-mpq-SUMMARY.md
  - src/maxpat/code_validation.py
  - src/maxpat/codegen.py
  - src/maxpat/critics/ext_critic.py
  - src/maxpat/ext_templates.py
  - src/maxpat/externals.py
  - src/maxpat/hooks.py
  - tests/fixtures/min_api_stub/c74_min.h
  - tests/test_codegen_external_fixes.py
  - tests/test_externals.py
covered_digest: "v2:sha256:db42af9c6508dbdb49bde748335472d85834f0cef421739b5816bf2dc523f730"
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Scaffold a `foo~` DSP external (0 inputs and 2 inputs), run setup_min_devkit then build_external, load foo~.mxo in MAX 9"
    expected: "Builds against real min-api; the object loads as `foo~` and passes audio"
    why_human: "Needs network, Xcode tools and MAX. The tests use a min-api stand-in header, not min-api itself."
  - test: "Run a generated N4M script with dict name `my-dict` in node.script"
    expected: "getDict_my_dict() reads the dict"
    why_human: "Needs a running MAX; `node --check` only proves the syntax."
  - test: "Run a generated js `anything()` handler in a js box and send `foo 1 2`"
    expected: "The selector and the list arrive via messagename / arrayfromargs"
    why_human: "Needs a running MAX. Node with emulated globals gave [\"foo\",\"x\",2]."
---

# Quick Task 261016-mpq (Q31) Verification Report

**Goal:** Implement Q31 from `.planning/reviews/2026-10-11-fix-plan.md`: codegen and Min-DevKit template fixes (G5, G6, G7, G8 rest, G3 rest).
**Status:** human_needed. All automated checks pass. Real min-devkit and MAX confirmation remain.
**Re-verification:** No, initial verification.

## Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `foo~` scaffolds as `foo_tilde/source/foo_tilde.cpp` with class `foo_tilde`, help `foo~.maxhelp`; plain names unchanged | VERIFIED | Own probe: `scaffold_external(d, "foo~", "dsp", ...)` returned root `foo_tilde`, source `foo_tilde/source/foo_tilde.cpp`, help `foo_tilde/help/foo~.maxhelp`. The `cmake_folder_name` diff matches the plan. |
| 2 | DSP template compiles for 0-3 inputs and 1-2 outputs; ValueError on bad counts | VERIFIED | Own probe rendered (0,1), (1,1), (2,1), (1,2), (2,2), (0,2), (3,2) and (4,4) for `foo~` and ran one `clang++ -std=c++17 -fsyntax-only` against the stub: rc 0. The stub-fidelity tests are green and reject the f1f39215 shapes. |
| 3 | ext_critic: no blocker on any template; invalid identifier is reported; comments ignored; helper class no longer causes a mismatch | VERIFIED | `ext_critic.py` diff shows the `mask()` use, `_VALID_IDENT_RE` and `_OBJECT_CLASS_RE`. My probe's critic result on `foo~` DSP was `['note']` only. The TestG5ExtCritic* tests pass. |
| 4 | setup_min_devkit clones into `ext_dir/min-devkit` (cwd = ext_dir), gitignored first, no submodule add; docs and CMake hint follow | VERIFIED | Diff: `_ensure_gitignored` runs before any clone, then `git clone --recursive`. The fallback runs `git submodule update` only inside `min-devkit`. The word "submodule add" is gone. SKILL.md (3 places) and BOUNDARIES.md (1) are updated. Tests mock `subprocess.run`, with a `git init` only inside tmp_path. |
| 5 | N4M dict helpers get valid, unique identifiers with JSON-escaped literals | VERIFIED | Own probe with `my-dict`, `1st.dict`, `a b`, `say"hi`, `my_dict`: `node --check` rc 0. Helpers `getDict_my_dict`, `_1st_dict`, `_a_b`, `_say_hi`, `_my_dict_2`. |
| 6 | js `anything()` takes no parameters and reads `messagename` / `arrayfromargs` | VERIFIED | Generated `function anything() {` with `var args = arrayfromargs(arguments);` first. In node with emulated globals, `anything("x", 2)` sent `[0,["foo","x",2]]`. |
| 7 | validate_code_file checks every .gendsp codebox; detect_js_type ignores comments and strings; validate_js (Q22) untouched; suite not regressed | VERIFIED | `hooks.py` uses `walk.iter_patchers(data, scope="gen")` and keeps the single-top-level output unchanged. `detect_js_type` uses `_js_mask`. `code_validation.py` only changed in `detect_js_type`. Full suite: 2 failed, 5317 passed, 5 xfailed, 1 xpassed (baseline 5228 passed). The 2 failures are the known q29-check baseline ones. |

**Score:** 7/7 truths verified. Nothing is behavior-unverified.

### Test Execution

| Check | Command | Result |
|-------|---------|--------|
| Q31 regression tests | `python3 -m pytest tests/test_codegen_external_fixes.py -rs` | 89 passed, none skipped (clang++, node and git all ran) |
| Full suite | `python3 -m pytest -q` | 2 failed (baseline q29-check: `test_readme_patch_table_lists_every_project`, `test_committed_q24_findings_match_allowlist[q29-check]`), 5317 passed |
| patches/ untouched | `git status --porcelain -- patches` and `git diff f1f39215 HEAD --name-only` | Empty. The diff touches only the 11 planned files. |
| Stash list | `git stash list` | Empty |

### Artifacts and Key Links

| Artifact / link | Status |
|-----------------|--------|
| `ext_templates.py` (`cpp_identifier`, `cmake_folder_name`, DSP rules, CMake hint) | VERIFIED, wired from `externals.py` and `ext_critic.py` |
| `externals.py` (scaffold naming, `MIN_DEVKIT_URL`, `setup_min_devkit`) | VERIFIED |
| `ext_critic.py` (mask, identifier blocker, imports `cpp_identifier`) | VERIFIED |
| `codegen.py` (N4M identifiers, js `anything`) | VERIFIED |
| `hooks.py` (`iter_patchers` walk) and `code_validation.py` (`_js_mask`) | VERIFIED |
| `tests/fixtures/min_api_stub/c74_min.h` | VERIFIED. Contains `sample_operator` and is a stand-in, not min-api. |

### Anti-Patterns

No TBD, FIXME or XXX markers were introduced (the suite's own debt checks stay green). No stubs found in the touched code.

### Requirements Coverage

G5, G6, G7, G8 and G3: SATISFIED, with a test class per finding.

### Human Verification Required

The compiler check uses a stand-in header, not real min-api. A true build and the MAX-side behavior need the user (items in the frontmatter).

1. **Real min-devkit build.** Scaffold a `foo~` DSP external (0 and 2 inputs), run `setup_min_devkit` then `build_external`, and load `foo~.mxo` in MAX 9. Expected: it builds, loads as `foo~` and passes audio.
2. **N4M dict helper.** Run an N4M script with a hyphenated dict name in node.script. Expected: `getDict_my_dict()` reads the dict.
3. **js anything().** Send `foo 1 2` to a js box with the generated handler. Expected: the selector and the arguments arrive.

### Follow-ups (not gaps; planned out of scope, PD-13)

- The DSP help patch still uses a fixed 1-in/1-out external box.
- `<1, 0>` sink externals.
- `build/` is not gitignored in the external.
- No C++ keyword check in ext_critic.
- No TECHNICAL.md critic-table row.
- The 2 pre-existing q29-check failures.

---

_Verified: 2026-10-16_
_Verifier: Claude (gsd-verifier)_
