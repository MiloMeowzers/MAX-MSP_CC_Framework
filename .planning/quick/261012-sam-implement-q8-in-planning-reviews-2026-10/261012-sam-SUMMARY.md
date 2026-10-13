---
phase: quick-261012-sam
plan: 01
status: complete
subsystem: release, ci, installer, project
tags: [ci, release, git-archive, installer, active-project, Q8]
requires: [Q1-Q7 landed (HEAD 1aee9bc)]
provides:
  - scripts/build_release.sh (single definition of the release archive)
  - .gitattributes anchored export-ignore rules
  - .github/workflows/test.yml (pytest on 3.10 and 3.12, push/PR/workflow_call)
  - release.yml gated on tests
  - requires_max / slow pytest markers, MAXPAT_TEST_MAX_APP test seam
  - get_active_project tolerant of missing/malformed/legacy pointers
affects: [release.yml, install.sh, installer/bin/create-max-framework.js, src/maxpat/project.py, .gitignore]
tech-stack:
  added: [GitHub Actions actions/setup-python@v6, requirements-dev.txt]
  patterns: [git archive + export-ignore, reusable workflow via workflow_call, temp-index plumbing commit for untracking]
key-files:
  created:
    - scripts/build_release.sh
    - .gitattributes
    - tests/test_release.py
    - .github/workflows/test.yml
    - requirements-dev.txt
  modified:
    - tests/conftest.py
    - tests/test_extraction.py
    - tests/test_project.py
    - src/maxpat/project.py
    - install.sh
    - installer/bin/create-max-framework.js
    - .gitignore
    - .github/workflows/release.yml
  deleted:
    - .release-ignore
    - patches/.active-project.json (untracked only, kept on disk)
    - .claude/projects/-Users-taylorbrook-Dev-MAX/memory/feedback_multiple_choice.md (untracked only, kept on disk)
decisions:
  - "OQ1 = A (user answer): the release ships only .claude/max-objects/audit/width-overrides.json from the audit directory"
  - "Untracking confirmed by user: patches/.active-project.json and .claude/projects/ untracked, gitignored, kept on disk"
  - "get_active_project validates a single path component but not _PROJECT_NAME_RE (FDNVerb exists)"
  - "test.yml push trigger is branches ['**'] so tag pushes run the tests only through release.yml"
metrics:
  duration: ~40 min
  completed: 2026-10-12
actuals:
  tokens: 8000
  tasks: 3
  commits: 3
plan_head_before: 1aee9bc259b2b47992233ffe7e8df8397e1189c0
plan_head_after: 18b6f3bcd82f426de7f169bb1c985f0207426566
---

# Quick 261012-sam: Q8 CI, release archive and installers Summary

The release is now `git archive` of HEAD with anchored `.gitattributes` export-ignore rules, built by `scripts/build_release.sh`, which both release.yml and a smoke test run. CI runs pytest on Python 3.10 and 3.12 for every push and PR, and a tag runs those tests before anything is published. Fresh, legacy and malformed active-project pointers now give "no active project" instead of crashing. The installer reports its real version. Local state is untracked.

## User decisions (locked)

- **OQ1: option A, the user's answer** (not resolved by default). Only `.claude/max-objects/audit/width-overrides.json` ships from the audit directory, via `/.claude/max-objects/audit/** export-ignore` plus `/.claude/max-objects/audit/width-overrides.json -export-ignore`. The other audit reports don't ship. Inside the archive, `len(src.maxpat.sizing._WIDTH_OVERRIDES) > 0` is asserted.
- **Untracking: confirmed by the user.** `patches/.active-project.json` and `.claude/projects/` are untracked and gitignored, and the local files stay on disk.

## Commits

| Task | Commit | Subject |
|---|---|---|
| 1 | 202e5d4 | fix(release): build the release with git archive and anchored .gitattributes export-ignore; release smoke test; requires_max and slow markers (Q8 I2) |
| 2 | d1bd3c1 | fix(install): fresh installs have no active project ... untrack patches/.active-project.json and .claude/projects/ (Q8 I1 I3 B11) |
| 3 | 18b6f3b | ci: pytest workflow on push and PR for Python 3.10 and 3.12; release runs the tests first ... drop .release-ignore (Q8 A4) |

No fix-forward commits were needed. Nothing was pushed, tagged, released or published.

## Test results

- **Step 0:** HEAD was `1aee9bc` (= base-sha.txt, unchanged). The staged set was empty. Baseline: `2661 passed, 1 xfailed, 1 xpassed, 29 warnings`, matching the plan.
- **RED counts before each GREEN step:**
  - Task 1, step 4 (no script, no `.gitattributes`): `5 failed, 5 errors`.
  - Task 1, step 6 (script present, `.gitattributes` not yet in HEAD): `5 failed, 5 passed`. The failures were `test_maintainer_trees_excluded` (`.claude/projects/...feedback_multiple_choice.md`, `.github`, `.planning`, ... shipped; this reproduces I2's memory-file leak), `test_fresh_layout_has_no_active_project` (`patches/` shipped) and the 3 TestGitattributes tests.
  - Task 2: `13 failed, 59 passed`. Each failure had its stated cause: the legacy content raised KeyError, `{not json` and the empty file raised JSONDecodeError, a list and the null/int names raised TypeError, and `""`, `../outside` and `a/b` returned the dict. Both installer files contained the pointer, and `--version` / `-v` printed v1.0.0 vs 2.3.1. The FDNVerb guard was green.
  - Task 3: `6 failed, 10 passed` (no test.yml, release.yml not gated and still using tar, `.release-ignore` present, no requirements-dev.txt).
- **Full suite after each task:** 2671, then 2685, then **2691 passed, 1 xfailed, 1 xpassed, 29 warnings** (final). The warning count is unchanged at 29, and the registered markers add no PytestUnknownMarkWarning.
- **Final pytest line (main tree):** `2691 passed, 1 xfailed, 1 xpassed, 29 warnings in 55.72s`

## Release archive facts (HEAD build)

- After Task 1: 240 entries (167 regular files), 953,267 bytes. After Task 3, built from the shallow clone: 240 entries, 953,863 bytes (`.release-ignore` gone, `requirements-dev.txt` added).
- Top level: `.claude .gitignore CLAUDE.md install.sh LICENSE patterns README.md src TECHNICAL.md tools` (plus `requirements-dev.txt` after Task 3).
- `.claude/scripts/` ships all 4 files: `extract_abstractions.py`, `extract_objects.py`, `merge_sources.py`, `validate_db.py`.
- The only file shipped from `.claude/max-objects/audit/` is `width-overrides.json`.
- Nothing ships under `tests/`, `patches/`, `.planning/`, `.github/`, `scripts/`, `installer/` or `.claude/projects/`. There is no `.gitattributes` and no nested archive.
- All 52 `src` modules import from the extracted archive, each `__file__` inside it. `ObjectDatabase().lookup("cycle~")` resolves, the width table is non-empty, and `get_active_project` returns None with no `patches/` and with an empty one.

## CI simulation (shallow `file://` clone, Max.app absent, no global git identity)

Run with `GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1 MAXPAT_TEST_MAX_APP=/nonexistent/Max.app`. No fallback was needed.

| Python | numpy / scipy / pytest | Result |
|---|---|---|
| 3.10.19 (uv) | 2.2.6 / 1.15.3 / 9.1.1 | 2690 passed, 1 skipped, 1 xfailed, 1 xpassed, 43 warnings |
| 3.12.12 (uv) | 2.5.4 / 1.18.1 / 9.1.1 | 2690 passed, 1 skipped, 1 xfailed, 1 xpassed, 43 warnings |

- The skip line was: `SKIPPED [1] tests/conftest.py:43: requires the Max application bundle at /nonexistent/Max.app (not found)`.
- `bash scripts/build_release.sh` succeeds from the clone.
- The warning count is higher in the clone (43 vs 29). The likely cause is the different numpy/scipy/Python versions; no tests fail.

## Untrack commit (Task 2)

- **Why a temp index:** after `git rm --cached X`, a path-scoped `git commit -- X ...` re-adds X from the working tree (the `--only` trap probed at planning). The commit was built with plumbing instead:
  1. `GIT_INDEX_FILE=<tmp> git read-tree HEAD`;
  2. `rm --cached` / `add` the explicit paths;
  3. `write-tree`;
  4. `commit-tree -p OLD`;
  5. `update-ref HEAD NEW OLD`;
  6. `git reset -q -- <paths>`.
- **HEAD name-status (d1bd3c1)**, exactly the 7 expected lines:
  ```
  D  .claude/projects/-Users-taylorbrook-Dev-MAX/memory/feedback_multiple_choice.md
  M  .gitignore
  M  install.sh
  M  installer/bin/create-max-framework.js
  D  patches/.active-project.json
  M  src/maxpat/project.py
  M  tests/test_project.py
  ```
- **Local-file checksums.** Both files are identical before (Step 0) and after, still on disk and now ignored:
  - `8259ef50...00b49ac  patches/.active-project.json` (points at rhythmic-corpus-chopper);
  - `c487c98e...461f697  .claude/projects/.../feedback_multiple_choice.md`.

  No `/max-switch` exception occurred.
- The staged set was empty before and after every commit. `git status --porcelain -- patches/` is now empty, and the stash list is unchanged.

## Settled decisions worth knowing

- `get_active_project` does **not** use `_PROJECT_NAME_RE`, because `patches/FDNVerb` exists and is uppercase. It only requires a non-empty single path component: not `.` or `..`, and no `/`, `\` or NUL. `set_active_project` is unchanged.
- test.yml's `push: branches: ['**']` keeps tag pushes from running it twice. On a tag, the tests run once, through release.yml's `test` job (`workflow_call`).
- The Python versions are quoted (`'3.10'`, `'3.12'`), because unquoted 3.10 is the YAML float 3.1.
- `MAXPAT_TEST_MAX_APP` is the test seam: set it to a nonexistent path to simulate a machine without Max. Only `TestIOCrossCheck` is marked `requires_max`, and its inner BEAP skip stays.
- `scripts/build_release.sh` also has an `ERR` trap that removes a partial output file on failure. This is a small addition beyond the plan, consistent with "nothing but OUT is written".

## Deviations from Plan

- **The release_archive fixture yields 3 values** `(rels, root, out)` instead of 2. The extra path is harmless and unused by the assertions.
- **The fresh-layout test also asserts that `patches/` is absent** from the extracted archive before calling `get_active_project`. Without that check, the test's "no `patches/`" case would be meaningless. This check is why the test was red before `.gitattributes` landed.
- **ERR trap in build_release.sh** (see above).

Otherwise the plan was executed as written.

## Manual steps for the user (not done by the executor)

1. Phase 1 of the fix plan (Q1-Q8) is complete. Per its "Push main after each phase", run `git push origin main`, then watch the first **Tests** run in the GitHub Actions tab for both Python versions.
2. To ship the fixes (I3 "release after the fixes"), tag the next version (for example `git tag v5.1.0 && git push origin v5.1.0`). release.yml then runs the tests, builds the archive, creates the GitHub Release and runs `npm publish` (needs the NPM_TOKEN secret).
3. Optional: confirm that the published tarball lists `MAX-MSP_CC_Framework/.claude/scripts/extract_objects.py` and `.claude/max-objects/audit/width-overrides.json`.

## Side effects to know

- When another clone (another machine) pulls the untrack commit, git **deletes** that clone's local `patches/.active-project.json` and the stray memory copy. Re-run `/max-switch` there.
- GitHub's auto-generated "Source code" archives also honor export-ignore now, so they exclude tests, patches, .planning and the rest.

## Residuals (out of scope)

- **Per-session pointer (B11):** instances that share one working tree still share `patches/.active-project.json`.
- **I3 remainder:** release checksums, and a pinned version for `curl | bash`.
- **Actions are pinned by major tag** (`@v6`, `@v3`), not by SHA.

## Doc impact (not edited, rule 8)

- **README:** Option C (git clone) and a contributor note about `pip install -r requirements-dev.txt`.
- **TECHNICAL "Test Suite":** the test count is stale; document CI, the `requires_max` / `slow` markers and `MAXPAT_TEST_MAX_APP`.
- **TECHNICAL "Active Project Tracking":** the pointer is per-checkout and untracked. A missing, malformed or legacy pointer means no active project.

## Hand-offs

- **Q9:** its help-io test should use `@pytest.mark.requires_max`.
- **Future release-content changes** go through `.gitattributes` and `tests/test_release.py`.

## Confirm in MAX (rule 9)

No patch file changed, so nothing is required.

## Threat Flags

None beyond the plan's threat model. T-sam-01 to 11 are mitigated as planned; T-sam-12 and SHA pinning are accepted residuals.

## Self-Check: PASSED

- All files exist: scripts/build_release.sh, .gitattributes, tests/test_release.py, .github/workflows/test.yml, requirements-dev.txt.
- `.release-ignore` is absent.
- Commits 202e5d4, d1bd3c1 and 18b6f3b are present in `git log`.
