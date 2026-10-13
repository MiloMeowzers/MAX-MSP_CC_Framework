---
phase: quick-261012-sam
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .gitattributes
  - scripts/build_release.sh
  - tests/conftest.py
  - tests/test_extraction.py
  - tests/test_release.py
  - .gitignore
  - src/maxpat/project.py
  - tests/test_project.py
  - install.sh
  - installer/bin/create-max-framework.js
  - patches/.active-project.json
  - .claude/projects/-Users-taylorbrook-Dev-MAX/memory/feedback_multiple_choice.md
  - .github/workflows/test.yml
  - .github/workflows/release.yml
  - .release-ignore
  - requirements-dev.txt
autonomous: true
requirements: [A4, I1, I2, I3, B11]

estimate:
  tokens: 100000
  raw_tokens: 100000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "`bash scripts/build_release.sh OUT [TREEISH]` writes OUT with `git archive --format=tar.gz --prefix=MAX-MSP_CC_Framework/` from TREEISH (default HEAD), run from the repo top level whatever the caller's cwd. Any git or tar failure exits non-zero (set -euo pipefail, no exit-code masking), and nothing but OUT is written. release.yml runs it with OUT = $RUNNER_TEMP/framework.tar.gz and publishes that file."
    - "The HEAD archive ships `.claude/scripts/extract_objects.py`, `CLAUDE.md`, `src/`, `tools/`, the object DB and (OQ1-A) `.claude/max-objects/audit/width-overrides.json`. It contains nothing under `tests/`, `patches/`, `.planning/`, `.github/`, `scripts/`, `installer/` or `.claude/projects/`, no `.gitattributes`, and no nested archive. Every export-ignore pattern in `.gitattributes` starts with `/`."
    - "Every `src` module imports from the extracted archive (each module file resolves inside it), the shipped ObjectDatabase resolves `cycle~`, and (OQ1-A/B) the shipped width-override table is non-empty. `get_active_project` there returns None on the fresh layout (no `patches/`, and an empty `patches/`)."
    - "get_active_project returns None, and never raises, for a pointer file that is missing, unreadable, invalid JSON, not a JSON object, the legacy installer form with active_project null, nameless, a non-string name, an empty name, `.`/`..`, or a multi-component name. It still returns the dict for an existing project, including an uppercase name like FDNVerb."
    - "Neither installer writes an active-project pointer file. `create-max-framework --version` and `-v` print `create-max-framework v<installer/package.json version>`."
    - "`patches/.active-project.json` and `.claude/projects/` are untracked and gitignored in one commit that sweeps no other staged work. Both files stay on disk, byte-identical to their Step 0 checksums."
    - "`.github/workflows/test.yml` runs on ubuntu-latest for Python '3.10' and '3.12' on push to branches, pull_request and workflow_call. It installs requirements-dev.txt (numpy, scipy, pytest) and runs `python -m pytest -q`. release.yml's release job `needs` a test job that calls test.yml. `.release-ignore` is deleted."
    - "Tests that read /Applications/Max.app carry `requires_max` and skip cleanly without it (simulated through MAXPAT_TEST_MAX_APP). A fresh shallow clone passes the full suite on Python 3.10 and 3.12 with no global git identity and no Max.app. The main-tree suite stays fully green. Nothing is pushed, tagged or released."
  artifacts:
    - path: "tests/test_release.py"
      provides: "Q8 regression tests: release-archive smoke test (slow), .gitattributes anchoring, build-script failure propagation, CI workflow and dev-requirements checks"
      contains: "class TestReleaseArchive"
      min_lines: 150
    - path: "scripts/build_release.sh"
      provides: "Single source of truth for the release archive: git archive with the MAX-MSP_CC_Framework/ prefix, set -euo pipefail, tar integrity listing"
      contains: "git archive"
    - path: ".gitattributes"
      provides: "Anchored export-ignore rules that replace .release-ignore"
      contains: "/.claude/projects export-ignore"
    - path: ".github/workflows/test.yml"
      provides: "CI pytest job (push to branches, pull_request, workflow_call; Python 3.10 and 3.12)"
      contains: "python -m pytest -q"
    - path: "requirements-dev.txt"
      provides: "CI/test dependencies: numpy, scipy, pytest"
      contains: "numpy"
    - path: "src/maxpat/project.py"
      provides: "get_active_project tolerant of missing, malformed and legacy pointer files"
      contains: "data.get(\"name\")"
  key_links:
    - from: ".github/workflows/release.yml"
      to: "scripts/build_release.sh"
      via: "the release job's build step runs `bash scripts/build_release.sh \"$RUNNER_TEMP/framework.tar.gz\"`, and action-gh-release uploads `${{ runner.temp }}/framework.tar.gz`"
      pattern: "scripts/build_release.sh"
    - from: ".github/workflows/release.yml"
      to: ".github/workflows/test.yml"
      via: "jobs.test.uses ./.github/workflows/test.yml (on: workflow_call); jobs.release.needs test"
      pattern: "uses: ./.github/workflows/test.yml"
    - from: "tests/test_release.py"
      to: "scripts/build_release.sh"
      via: "the module-scoped fixture runs `bash scripts/build_release.sh <tmp>/framework.tar.gz`, which is exactly what release.yml runs, then extracts and imports the archive in a subprocess"
      pattern: "build_release.sh"
    - from: "scripts/build_release.sh"
      to: ".gitattributes"
      via: "git archive honors export-ignore from the archived tree's .gitattributes"
      pattern: "export-ignore"
    - from: "tests/conftest.py"
      to: "tests/test_extraction.py"
      via: "the requires_max marker is registered in pytest_configure, and pytest_runtest_setup skips it when MAX_APP_PATH is not a directory"
      pattern: "requires_max"
---

<objective>
Implement Q8 of `.planning/reviews/2026-10-11-fix-plan.md`: CI, the release archive and the installers (review findings A4, I1, I2, I3, B11).

- **A4:** the only workflow, `release.yml`, publishes tags without running pytest. There is no CI test job.
- **I1:** both installers write a legacy pointer file with `active_project: null`, but `get_active_project` reads `data["name"]`. A fresh install crashes in `/max-status` and `/max-build`.
- **I2:** the release tarball is built with `tar` + `.release-ignore`, and that build is wrong:
  - the unanchored `scripts` pattern strips `.claude/scripts/`;
  - the tarball is written inside the tree it archives, so it nests a truncated copy of itself;
  - it ships the tracked maintainer memory file;
  - tar's exit code is masked.
- **I3 (version part):** `create-max-framework --version` prints a hard-coded 1.0.0, while `installer/package.json` says 2.3.1.
- **B11 (tracking part):** `patches/.active-project.json` is tracked and shared through git. Untrack and gitignore it.

After this plan:
- the release is a `git archive` of HEAD with anchored `.gitattributes` export-ignore rules, built by one script that both release.yml and a smoke test run;
- fresh installs and legacy, malformed or missing pointer files give "no active project" instead of a crash;
- the installer reports its real version;
- local state is untracked;
- CI runs the suite on Python 3.10 and 3.12 for every push and PR;
- a tag runs the tests before anything is published.

Output: three commits, one per task, tagged `(Q8 `. Nothing is pushed, tagged or released; those outward steps are written up in SUMMARY.md for the user.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

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

Execution-environment additions:
- Q1-Q7 have landed, so the suite must stay **fully green**. Expected baseline at HEAD `1aee9bc`: **2661 passed, 1 xfailed, 1 xpassed, 29 warnings** (the Q7 final count). The executor re-measures it in Step 0.
- Execution is sequential on the main working tree (no worktree), on branch `main`. Tasks 1 and 3 both edit `tests/test_release.py`, and Task 3 edits `.github/workflows/release.yml`, so the tasks run in order.
- **No outward action.** Never `git push`, never create or push a tag, never run `gh release` or `npm publish`. Workflows are written and checked locally only. The manual steps go in SUMMARY.md.
- Leave these alone and never stage them:
  - `.planning/tci-phase2/` (untracked);
  - the untracked `base-sha.txt` / `baseline-pytest.txt` / `stash-list-before.txt` files in the c5i, di7, egf, m87, pkh and qsr quick dirs;
  - this task dir's own `base-sha.txt`, `stash-list-before.txt`, and the `baseline-pytest.txt` / `local-state.sha256` files Step 0 creates.

  Until Task 2 untracks it, `patches/.active-project.json` shows as modified. Never stage its content: Task 2 removes it from the index only.
- Another instance may commit concurrently. Commit only each task's `<files>`:
  - Tasks 1 and 3: `git add -- <paths>` then `git commit -m ... -- <paths>`.
  - Task 2 must use the temp-index commit in its action. A path-scoped commit re-adds a file that `git rm --cached` removed, because `--only` takes the path's working-tree content (probed at planning).
- Tests never write to the MAX repo. The only git command a test runs against the checkout is the read-only `git archive` inside `scripts/build_release.sh`, with output under pytest's `tmp_path`. Each verify asserts the following are unchanged by the test run:
  - HEAD;
  - the staged set;
  - `git status --porcelain -- patches/` (shows only `.active-project.json` before Task 2, nothing after).
- The local interpreter is Python 3.14. The `ast.parse(..., feature_version=(3, 10))` gate runs on every changed `.py` file. Task 3's final gate also runs the real suite under uv-managed Python 3.10 and 3.12 (both already installed in uv at planning: `cpython-3.10.19`, `cpython-3.12.12`).
- The interactive shell is zsh. Multi-statement gates are wrapped in `bash -c '...'`.
- Throwaway files go outside the repo: your session scratchpad, else `mktemp -d`.
</rules>

<open_questions>
This is a decision the report doesn't make (rule 7). The orchestrator must put it to the user before execution and record the answer on the `Answer:` line. If execution starts with no recorded answer, the executor uses the **Recommended** option and lists it in SUMMARY.md as "resolved by default". The tasks are written for the recommended option, and each alternative's delta is stated.

**OQ1. What should the release ship from `.claude/max-objects/audit/`?**

Background:
- `.release-ignore` excludes the whole directory today.
- The Q8 spec's exclusion list doesn't mention it.
- `src/maxpat/sizing.py:21-30` loads `.claude/max-objects/audit/width-overrides.json` at import time: 513 object-width overrides, used at `sizing.py:205`. Without the file, `_WIDTH_OVERRIDES` silently becomes `{}`. So every install from the v5.0.0 tarball has run without the width table. This is the same class of bug as the stripped `.claude/scripts/`.
- The other 5 files are maintainer audit reports (`audit-report.json` alone is 3.5 MB) that the audit CLI regenerates.

Options:
- A) **(Recommended) Ship only `width-overrides.json`.**
  - `.gitattributes` gets `/.claude/max-objects/audit/** export-ignore`, followed by `/.claude/max-objects/audit/width-overrides.json -export-ignore`. A planning-time probe of `git archive` confirmed the exception works.
  - The smoke test asserts that the file ships, that the other five don't, and that `len(src.maxpat.sizing._WIDTH_OVERRIDES) > 0` inside the archive.
- B) **Ship the whole directory** (+3.7 MB uncompressed, simplest rules).
  - Delta: drop both audit lines from `.gitattributes`.
  - The smoke test asserts the directory ships, plus the same non-empty check.
- C) **Keep excluding the whole directory**, exactly as `.release-ignore` does. Installs keep the silent width-table gap.
  - Delta: one line, `/.claude/max-objects/audit export-ignore`.
  - The smoke test asserts the directory is absent and skips the non-empty check.

Answer:
</open_questions>

<assumption_delta_decision>
The assumption-delta and ai-integration detectors were not run. This quick task has no ROADMAP phase, so the phase-section probe has no input (`skipped`, not `detected:false`). Read manually:
- the plan replaces the release mechanism (tar + `.release-ignore` becomes git archive + `.gitattributes`), which is the S10 simplification the review chose;
- it introduces no ORM, schema or AI component;
- the only external services are GitHub Actions and the existing npm publish, which are unchanged apart from the ordering gate.

No coverage matrix or schema gate applies.
</assumption_delta_decision>

<package_legitimacy>
No new package is introduced. CI installs the three third-party packages the code already imports. A planning-time AST scan of every `.py` under `src/`, `tests/`, `tools/`, `scripts/` and `.claude/scripts/` found exactly these three outside the standard library and first-party code:

| Package | Status | Evidence |
|---|---|---|
| numpy | [VERIFIED] | Imported by `src/maxpat/dsp_sim/*`. Installed locally (2.4.0, Python 3.14). Installed from PyPI into a uv Python 3.10 venv at planning (2.2.6). |
| scipy | [VERIFIED] | Imported by `src/maxpat/dsp_sim/measure.py`. Local 1.17.0; 3.10 venv 1.15.3. |
| pytest | [VERIFIED] | Imported by `tests/`. Local 9.0.2; 3.10 venv 9.1.1. |

The GitHub Actions used are:
- `actions/checkout@v6` (already used by release.yml);
- `actions/setup-python@v6` (official; the `v6` tag was confirmed through `gh api` at planning);
- `softprops/action-gh-release@v3` and `actions/setup-node@v6` (unchanged).

No [ASSUMED] or [SUS] entry exists, so no legitimacy checkpoint is needed.
</package_legitimacy>

<context>
CLAUDE.md is already loaded as project instructions. Don't re-read it, and don't edit it in this task.

Read only these ranges:
- `.planning/reviews/2026-10-11-repo-review.md`: line 57 (A4), line 77 (B11), lines 161-163 (I1, I2, I3), line 201 (S10) and line 324 (R1's "CI pytest job (or a Claude Code PostToolUse hook)"). This satisfies rule 1.
- `.planning/reviews/2026-10-11-fix-plan.md`: lines 17-31 (rules) and 155-174 (Q8).
- `.github/workflows/release.yml` (all 40 lines), `.release-ignore` (13 lines), `.gitignore` (16 lines).
- `install.sh` lines 40-52; `installer/bin/create-max-framework.js` lines 1-36 and 49-70; `installer/package.json`.
- `src/maxpat/project.py` lines 20-30 (`_PROJECT_NAME_RE`) and 96-136 (`set_active_project`, `get_active_project`).
- `src/maxpat/sizing.py` lines 15-30 (OQ1).
- `tests/conftest.py` (all, 92 lines), `tests/test_extraction.py` lines 1-20 and 121-152, `tests/test_project.py` lines 1-20 and 87-121.
- `tests/test_save_safety.py` lines 1-30 (the module-level `skipif` on a missing git, to mirror).
</context>

<observed_facts>
The planner verified these on 2026-10-12 at HEAD `1aee9bc` (= `base-sha.txt`). If a live value differs at execution time, the live value wins; record the difference in SUMMARY.md.

**Release today:**
- `release.yml` runs `tar czf framework.tar.gz --exclude-from=.release-ignore --transform ... . || [[ $? -eq 1 ]]` in the checkout, then uploads `framework.tar.gz`, then sets the installer version from the tag and runs `npm publish` (NPM_TOKEN).
- `.release-ignore` holds 13 unanchored patterns: `.planning`, `.git`, `.github`, `.pytest_cache`, `tests`, `.claude/max-objects/audit`, `src/maxpat/__pycache__`, `patches`, `installer`, `scripts`, `.DS_Store`, `*.pyc`, `__pycache__`.
- There is no `.gitattributes`, no `requirements*.txt`, and no pytest ini/pyproject/setup.cfg. Markers are not registered anywhere.

**git archive probe** (a scratch shallow clone plus a candidate `.gitattributes`):
- Anchored `/scripts export-ignore` keeps `.claude/scripts/*` (4 files) and drops `scripts/`.
- `/.claude/max-objects/audit/**` + `/.claude/max-objects/audit/width-overrides.json -export-ignore` ships exactly that one audit file.
- The archive has 239 entries (~950 KB): regular files and dirs only, with no symlinks (tracked modes are only 100644 and 100755). Python's `tarfile` hides the pax global header.
- `git archive HEAD` works in a `--depth 1` clone.
- Run from a subdirectory, `git archive` archives only that subdirectory, so the script must cd to the top level.

**Git commit trap** (scratch-repo probe):
- After `git rm --cached X`, a path-scoped `git commit -m m -- X .gitignore` RE-ADDS X from the working tree. HEAD still contains it.
- The temp-index sequence keeps other staged files staged and leaves X on disk and ignored:
  1. `GIT_INDEX_FILE=tmp git read-tree HEAD`;
  2. `rm --cached` / `add` the explicit paths;
  3. `write-tree`;
  4. `commit-tree -p OLD`;
  5. `update-ref HEAD NEW OLD`;
  6. `git reset -q -- <paths>`.
- Separately: `git add -- deleted.txt new.txt`, then `git commit -m m -- deleted.txt new.txt`, records both a deletion and a new file and doesn't sweep another staged file.
- The repo has no active hooks (`.git/hooks` holds only samples), no commit signing, and an empty staged set at planning.

**Tracked local state:**
- `git ls-files` lists `patches/.active-project.json` (modified in the working tree, pointing at rhythmic-corpus-chopper) and `.claude/projects/-Users-taylorbrook-Dev-MAX/memory/feedback_multiple_choice.md`.
- No Python, test, skill or command reads `.claude/projects/`.
- No test reads `patches/.active-project.json`.
- `auto_commit_patch` only commits under `patches/<project>/`, and no skill or command `git add`s the pointer, so gitignoring it breaks no workflow.

**get_active_project** (`project.py:114-136`):
- Reproduced at planning:
  - the legacy installer content raises `KeyError: 'name'`;
  - `{not json` and an empty file raise JSONDecodeError;
  - a JSON list raises TypeError;
  - a null name raises TypeError;
  - name `../outside` with an existing `<base>/outside/` returns the dict.
- The project `patches/FDNVerb` exists and fails `_PROJECT_NAME_RE` (lowercase only), so that regex must NOT gate `get_active_project`.

**Installers:**
- `install.sh:47-49` creates `patches/` and writes the legacy pointer. `create-max-framework.js:55-63` does the same.
- `create-max-framework.js:10` hard-codes `VERSION = '1.0.0'`; `node installer/bin/create-max-framework.js --version` prints `create-max-framework v1.0.0`, while `installer/package.json` says 2.3.1.
- `npm pack --dry-run --json ./installer` lists `README.md`, `bin/create-max-framework.js` and `package.json`, so `require('../package.json')` resolves in the published package.
- release.yml runs `npm version <tag>` before publishing, so the published `--version` will equal the tag.

**Test-suite portability** (the CI simulation done at planning):
- In a `git clone --depth 1 file://...` of HEAD, under a uv Python 3.10.19 venv with numpy 2.2.6, scipy 1.15.3 and pytest 9.1.1, the suite gave **2661 passed, 1 xfailed, 1 xpassed** in three runs:
  - on the normal volume;
  - on a case-sensitive APFS volume;
  - with `GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1` (no global git identity).
- An audit-hook probe of every file open, listdir and scandir under `/Applications/Max` or `Documents/Max 9` during the full run found exactly one test: `tests/test_extraction.py::TestIOCrossCheck::test_beap_io_matches_help_patches`. It is the only collected test in that class, and it already calls `pytest.skip` when the BEAP Help dir is missing. The audit_db and sync_max_bundle tests use fake bundles under `tmp_path`.
- `src/` has 53 `.py` files. `pkgutil.walk_packages` over `src` yields 52 modules, including `src.maxpat.dsp_sim.__main__`, which imports without side effects, and all import cleanly. No shipped code imports `scripts`, `tests` or `patches`.
- `ObjectDatabase()` and `sizing` resolve their data relative to `__file__`, so imports from the extracted archive read the archive's DB.

**Tooling:**
- uv 0.9.18 has cpython 3.10.19 and 3.12.12 installed.
- PyYAML 6.0.3 is available locally only, not as a project dependency. It parses the bare `on:` key as boolean `True`.
- node v24.19.0; npm available.
- bsdtar 3.5.3 has no `--transform`, so the old release command can't even run on macOS.
- `act`, `actionlint` and `shellcheck` are not installed.
- `gh api` shows latest `actions/checkout` v7.0.1 and `actions/setup-python` v7.0.0, and the `v6` tags exist for both. Stay on v6 to match release.yml.
- Latest release: v5.0.0 (2026-05-01).
</observed_facts>

<settled_decisions>
These were resolved at planning from the Q8 spec, findings A4/I1/I2/I3/B11, S10 and the observed facts. Don't re-litigate them; if something live contradicts one, stop and ask (rule 7).

- **S1: One build script.**
  - `scripts/build_release.sh OUT [TREEISH]` is the only definition of the release archive. release.yml runs it and the smoke test runs it.
  - It lives in `scripts/`, which is export-ignored, so it never ships.
  - TREEISH defaults to HEAD. It exists so the smoke test can prove a failing git command propagates; the release always uses HEAD.
- **S2: The export-ignore set** ports every `.release-ignore` pattern that matches a tracked path, anchored:
  - `/.planning`, `/.github`, `/tests`, `/patches`, `/scripts`, `/installer`;
  - the OQ1 audit lines;
  - plus `/.claude/projects` and `/.gitattributes`.

  The untracked-only patterns (`.pytest_cache`, `__pycache__`, `*.pyc`, `.DS_Store`, `.git`) are moot under git archive. `install.sh`, `.gitignore`, `README.md`, `LICENSE`, `TECHNICAL.md`, `patterns/`, `tools/` and the new `requirements-dev.txt` keep shipping, matching today's tarball apart from the bug fixes. `installer/` stays excluded, as today, because npm publishes it separately.
- **S3: get_active_project.** It returns None, silently with no warning, when:
  - the file is missing or not a regular file;
  - reading or decoding fails (catch `OSError` and `ValueError`; JSONDecodeError and UnicodeDecodeError are ValueErrors);
  - the decoded value isn't a dict;
  - `name = data.get("name")` isn't a non-empty `str`;
  - the name is `.` or `..`, or contains `/`, `\` or NUL;
  - `patches/<name>/` isn't a directory.

  Otherwise it returns the dict unchanged. Rationale:
  - "malformed" in the spec plus B11's "the name isn't validated" justify the single-path-component check;
  - `_PROJECT_NAME_RE` is NOT used, because FDNVerb exists;
  - `set_active_project` is unchanged.
- **S4: Installers keep creating `patches/`.** The directory is harmless and keeps the layout identical. They only stop writing the pointer. The replacement comments say "no active-project pointer is written" without naming the file, so the installer tests (which skip comment lines) stay unambiguous.
- **S5: Version.** The JS reads `require('../package.json').version` once at the top, replacing the constant. The output format `create-max-framework v<version>` is unchanged.
- **S6: Markers live in `tests/conftest.py`.** No new ini file at the root.
  - `MAX_APP_PATH = Path(os.environ.get("MAXPAT_TEST_MAX_APP", "/Applications/Max.app"))` is a test seam for simulating a machine without Max.
  - `pytest_configure` registers `requires_max` and `slow`.
  - `pytest_runtest_setup` skips `requires_max` items when `MAX_APP_PATH` isn't a directory, with the reason `requires the Max application bundle at <path> (not found)`.
  - Only `TestIOCrossCheck` gets `requires_max` (the probe's only Max.app reader). Its inner `pytest.skip` stays, because the BEAP package can be missing even when Max is present.
- **S7: CI shape.**
  - `test.yml` triggers on `push` with `branches: ['**']` (so tag pushes don't double-run it), `pull_request` and `workflow_call`.
  - It sets `permissions: contents: read`, one job on `ubuntu-latest` with `timeout-minutes: 30` and `strategy.fail-fast: false`, and `matrix.python-version: ['3.10', '3.12']`. The versions are quoted: unquoted `3.10` is the YAML float 3.1.
  - Steps:
    1. `actions/checkout@v6` (default depth 1, which the smoke test tolerates);
    2. `actions/setup-python@v6` with `python-version`, `cache: pip` and `cache-dependency-path: requirements-dev.txt`;
    3. `python -m pip install -r requirements-dev.txt`;
    4. `python -m pytest -q`, which runs the slow smoke test too.
  - `release.yml` gains a `test` job (`uses: ./.github/workflows/test.yml`, `permissions: contents: read`). Its `release` job gets `needs: test`, keeps `permissions: contents: write`, and builds with S1. The Node/npm steps are unchanged.
- **S8: requirements-dev.txt** holds `numpy>=2.2`, `scipy>=1.15` and `pytest>=9.0`. These are the lowest versions verified at planning, and the last releases that support Python 3.10 resolve under them. A header comment says numpy and scipy are also runtime dependencies of `src/maxpat/dsp_sim`.
- **S9: B11 scope.** Untracking ends sharing the pointer through git. Instances sharing one working tree still share the file; a per-session pointer is not in the Q8 spec, so it is a SUMMARY residual. I3's checksums, the pinned `curl | bash` version and actually cutting a release are also residuals or manual steps.
</settled_decisions>

<tasks>

<task type="tracer" tdd="true">
  <name>Task 1: Release archive end-to-end: scripts/build_release.sh runs git archive of HEAD with anchored .gitattributes export-ignore rules. A slow smoke test builds, extracts and imports it (every src module from the archive, get_active_project None on the fresh layout). requires_max/slow markers registered, and the one Max.app test marked</name>
  <files>tests/conftest.py, tests/test_extraction.py, tests/test_release.py, scripts/build_release.sh, .gitattributes</files>
  <read_first>.planning/reviews/2026-10-11-repo-review.md (lines 57, 77, 161-163, 201), .planning/reviews/2026-10-11-fix-plan.md (lines 17-31, 155-174), .github/workflows/release.yml, .release-ignore, src/maxpat/sizing.py (lines 15-30), tests/conftest.py, tests/test_extraction.py (lines 1-20, 121-152), tests/test_save_safety.py (lines 1-30)</read_first>
  <behavior>
    `REPO_ROOT = Path(__file__).resolve().parent.parent`, `PREFIX = "MAX-MSP_CC_Framework"`, and `SCRIPT = REPO_ROOT / "scripts" / "build_release.sh"`. "rel" means a member name with `PREFIX + "/"` stripped.

    TestReleaseArchive (marked `slow`; skipped when git or bash is missing, or when `git rev-parse --is-inside-work-tree` fails in REPO_ROOT):
    - The module-scoped fixture:
      - runs `["bash", str(SCRIPT), str(out)]` with `cwd=REPO_ROOT`; a non-zero exit calls `pytest.fail` with stderr;
      - opens `out` with tarfile and validates every member: the name is PREFIX or starts with PREFIX + "/"; it is not absolute; it has no `..` component; it is a regular file or a dir;
      - extracts with `filter="data"` when `hasattr(tarfile, "data_filter")`;
      - yields (rel names set, extracted root).
    - `test_runtime_files_ship`: `.claude/scripts/extract_objects.py`, `CLAUDE.md`, `src/maxpat/__init__.py`, `.claude/max-objects/max/objects.json`, `tools/sync_max_bundle.py` and (OQ1-A) `.claude/max-objects/audit/width-overrides.json` are all present.
    - `test_maintainer_trees_excluded`: no rel equals, or starts with `<x>/`, any of `tests`, `patches`, `.planning`, `.github`, `scripts`, `installer` or `.claude/projects`. There is no rel `.gitattributes`. Under OQ1-A, no other `.claude/max-objects/audit/` file is present. RED until `.gitattributes` is in HEAD: `tests/`, `patches/` and `.claude/projects/` all ship from a plain archive of HEAD.
    - `test_no_nested_archive`: no rel ends in `.tar.gz`, `.tgz`, `.tar` or `.zip`.
    - `test_every_src_module_imports_from_archive`: one subprocess `[sys.executable, "-c", CODE, str(root)]` with `cwd=str(root)` and `PYTHONPATH` removed from the env.
      - CODE puts root first on `sys.path`, imports `src`, walks `pkgutil.walk_packages(src.__path__, "src.", onerror=...)`, and imports each name.
      - It records errors, module `__file__`s, `ObjectDatabase().lookup("cycle~") is not None`, and `len(src.maxpat.sizing._WIDTH_OVERRIDES)`.
      - It prints one JSON object on its last stdout line.
    - The test asserts:
      - no import errors;
      - every `__file__` resolves inside root;
      - the walked module set equals the set derived from the archive's `src/**/*.py` members (package `__init__` gives the package name; `src` itself is excluded);
      - `cycle~` resolves;
      - (OQ1-A/B) the width-override count is above 0.
    - `test_fresh_layout_has_no_active_project`: the same subprocess pattern calls `get_active_project(Path(root))`, first with no `patches/`, then again after creating an empty `patches/` (what the installers do). Both are None.

    TestGitattributes (fast, unmarked, reads the working-tree file):
    - Every non-blank, non-`#` line whose attributes include `export-ignore` (set or `-` unset) has a pattern starting with `/`.
    - Each S2 exclusion is present as `<pattern> export-ignore`.
    - No pattern names `/.claude/scripts`.
    - RED: the file doesn't exist.

    TestBuildScript (unmarked; same git/bash skip):
    - Running SCRIPT with no arguments exits non-zero.
    - Running it with `out` under `tmp_path` and TREEISH `no-such-ref-q8` exits non-zero (no exit-code masking).
    - RED: the script is missing.

    Markers (checked by the verify, not by unit tests):
    - `MAXPAT_TEST_MAX_APP=/nonexistent/Max.app` turns `TestIOCrossCheck` into one SKIPPED with the reason `requires the Max application bundle at ...`;
    - without it, the test still passes on this Mac;
    - `pytest --markers tests` lists both markers.
  </behavior>
  <action>
    Implement the Q8 "Release build" bullets and the smoke test (finding I2, simplification S10), plus the `requires_max` marker (A4's portability precondition), per S1, S2 and S6 and the OQ1 answer (Recommended A if unanswered).

    Step 0, baseline (rule 4). Set `Q=.planning/quick/261012-sam-implement-q8-in-planning-reviews-2026-10`.
    - `base-sha.txt` and `stash-list-before.txt` already exist there. Never overwrite or stage them.
    - If HEAD moved from `1aee9bc`, record that in SUMMARY.md and continue.
    - Run `python3 -m pytest -q -p no:cacheprovider` and write its final summary line to `$Q/baseline-pytest.txt`. Expected: 2661 passed, 1 xfailed, 1 xpassed, 29 warnings.
    - Write `shasum -a 256 patches/.active-project.json .claude/projects/-Users-taylorbrook-Dev-MAX/memory/feedback_multiple_choice.md` to `$Q/local-state.sha256`.
    - Record `git diff --cached --name-only` (expected empty) in SUMMARY notes.
    - None of these files is ever staged.

    Markers first (no behavior change):
    1. `tests/conftest.py`: add `import os`, the `MAX_APP_PATH` constant, `pytest_configure` (register `requires_max: test reads the installed Max application bundle; skipped when it is absent` and `slow: slow test (builds the release archive); deselect with -m "not slow"`) and `pytest_runtest_setup`, all per S6. Write a docstring line that names the env var.
    2. `tests/test_extraction.py`: decorate `class TestIOCrossCheck` with `@pytest.mark.requires_max`. Keep its inner BEAP skip.

    RED:
    3. Create `tests/test_release.py` with TestReleaseArchive, TestGitattributes and TestBuildScript covering every `<behavior>` bullet.
       - The module docstring cites quick 261012-sam, Q8, I2 and S10. It says the only git command run against the checkout is the read-only archive build into `tmp_path`, and that the archive is built from HEAD, so archive assertions reflect committed state.
       - Mirror the git skip from `tests/test_save_safety.py`, but apply `slow` to TestReleaseArchive only. Task 3 adds fast classes to this file.
       - Use only the standard library plus pytest.
    4. Run `python3 -m pytest -q -p no:cacheprovider tests/test_release.py`. It must be red (no script, no `.gitattributes`). Record the counts.
    5. Create `scripts/build_release.sh` and `chmod 755` it. It must:
       - start with a bash shebang, a header comment (purpose; "release.yml and tests/test_release.py both run this file"; usage `scripts/build_release.sh OUTPUT.tar.gz [TREEISH]`), and `set -euo pipefail`;
       - require 1 or 2 arguments, else print usage to stderr and exit 2;
       - `mkdir -p` the output's parent and turn OUTPUT into an absolute path BEFORE changing directory;
       - `cd` to the directory containing the script, then to `git rev-parse --show-toplevel` (git archive run from a subdirectory archives only that subdirectory);
       - run `git archive --format=tar.gz --prefix=MAX-MSP_CC_Framework/ -o "$OUT" "${TREEISH:-HEAD}"`;
       - run `tar -tzf "$OUT" > /dev/null` as an integrity check;
       - print the output path.

       Nothing may mask an exit code.
    6. Re-run the test file. TestBuildScript is now green. TestReleaseArchive is still red only on the exclusion and the OQ1 assertions, because HEAD has no `.gitattributes`. This reproduces I2's "ships the memory file" part. Record it.

    GREEN:
    7. Create `.gitattributes`:
       - a header comment: the release archive is `git archive` of HEAD, built by `scripts/build_release.sh`; every pattern is anchored with a leading `/`, because an unanchored `scripts` also matches `.claude/scripts/`, which `src/maxpat/validation.py`, the max-lifecycle skill and `tools/sync_max_bundle.py` need (review I2);
       - one `<pattern> export-ignore` line per S2 exclusion;
       - the OQ1 lines.
    8. Commit with explicit paths only:
       - `git add -- tests/conftest.py tests/test_extraction.py tests/test_release.py scripts/build_release.sh .gitattributes`;
       - `git commit -m "fix(release): build the release with git archive and anchored .gitattributes export-ignore; release smoke test; requires_max and slow markers (Q8 I2)" -- tests/conftest.py tests/test_extraction.py tests/test_release.py scripts/build_release.sh .gitattributes`.

       `.release-ignore` and `release.yml` are untouched until Task 3, so the old workflow stays self-consistent at this commit.
    9. Run the verify. The archive tests are green only now, because the archive is built from HEAD. If any fails, fix it and commit the fix forward as `fix(release): ... (Q8 I2)` with the same explicit-path form. Never amend or rewrite.
  </action>
  <verify>
    <automated>bash -c 'H0=$(git rev-parse HEAD) || exit 1; S0=$(git diff --cached --name-only) || exit 1; python3 -m pytest -q -p no:cacheprovider -rs tests/test_release.py tests/test_extraction.py || exit 1; [ "$(git rev-parse HEAD)" = "$H0" ] || { echo MAX-REPO-HEAD-MOVED; exit 1; }; [ "$(git diff --cached --name-only)" = "$S0" ] || { echo MAX-REPO-STAGED-CHANGED; exit 1; }; GS=$(git status --porcelain -- patches/) || exit 1; W=$(printf "%s\n" "$GS" | grep . | grep -v " patches/.active-project.json$"); [ -z "$W" ] || { echo "PATCH-WORKTREE: $W"; exit 1; }; echo RELEASE-TESTS-GREEN-MAX-REPO-UNTOUCHED'</automated>
    <automated>bash -c 'OUT=$(MAXPAT_TEST_MAX_APP=/nonexistent/Max.app python3 -m pytest -q -p no:cacheprovider -rs tests/test_extraction.py::TestIOCrossCheck 2>&1); printf "%s\n" "$OUT" | grep -q "requires the Max application bundle" || { printf "%s\n" "$OUT"; echo NO-REQUIRES-MAX-SKIP; exit 1; }; python3 -m pytest -q -p no:cacheprovider tests/test_extraction.py::TestIOCrossCheck | grep -q "1 passed" || { echo REAL-MAX-RUN-CHANGED; exit 1; }; M=$(python3 -m pytest -p no:cacheprovider --markers tests); printf "%s\n" "$M" | grep -q "@pytest.mark.requires_max" && printf "%s\n" "$M" | grep -q "@pytest.mark.slow" || { echo MARKERS-NOT-REGISTERED; exit 1; }; bash -n scripts/build_release.sh && test -x scripts/build_release.sh || { echo SCRIPT-SYNTAX-OR-MODE; exit 1; }; echo MARKERS-AND-SCRIPT-OK'</automated>
    <automated>python3 -c "import ast,sys; [ast.parse(open(f).read(), filename=f, feature_version=(3, 10)) for f in sys.argv[1:]]; print('PY310-SYNTAX-OK')" tests/conftest.py tests/test_extraction.py tests/test_release.py</automated>
    <automated>python3 -m pytest -q -p no:cacheprovider && echo SUITE-GREEN</automated>
  </verify>
  <done>
    - The `release` archive of HEAD (built by the same script release.yml will run in Task 3) ships `.claude/scripts/`, the DB and (OQ1-A) the width table.
    - It excludes tests, patches, .planning, .github, ./scripts, installer and .claude/projects, and contains no nested archive.
    - Every src module imports from it, and the fresh layout has no active project.
    - `requires_max` skips cleanly without Max.app.
    - Each RED case was recorded red first.
    - The full suite is green, with xfailed/xpassed unchanged (1/1).
    - The MAX repo, the staged set and `patches/` are untouched by the tests.
    - There is one `(Q8 ` commit (plus any fix-forward), containing exactly the 5 listed paths.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Fresh installs have no active project. get_active_project returns None for missing, malformed and legacy pointer files; both installers stop writing the pointer; --version reads package.json; patches/.active-project.json and .claude/projects/ are untracked and gitignored in one temp-index commit, and stay on disk</name>
  <files>.gitignore, src/maxpat/project.py, tests/test_project.py, install.sh, installer/bin/create-max-framework.js</files>
  <read_first>src/maxpat/project.py (lines 20-30, 96-136), tests/test_project.py (lines 1-20, 87-121), install.sh (lines 40-52), installer/bin/create-max-framework.js (lines 1-36, 49-70), installer/package.json, .gitignore</read_first>
  <behavior>
    These tests extend `tests/test_project.py`. A helper `_write_pointer(base, text)` creates `base/patches/` and writes `text` to the pointer file there.

    TestActiveProject additions (each returns None; RED today as observed):
    - The legacy installer content, i.e. a JSON object whose only key is the old snake_case key with value null: RED, KeyError.
    - `{not json`: RED, JSONDecodeError.
    - The empty string: RED, JSONDecodeError.
    - `["my-synth"]`: RED, TypeError.
    - `{"name": null}`: RED, TypeError.
    - `{"name": 5}`: RED, TypeError.
    - `{"name": ""}`: RED. `patches/` itself is a dir, so the current code returns the dict.
    - `{"name": "../outside"}` with `<base>/outside/` created: RED, returns the dict.
    - `{"name": "a/b"}` with `<base>/patches/a/b/` created: RED, returns the dict.
    - Guard: `{"name": "FDNVerb", "activated": "x"}` with `<base>/patches/FDNVerb/` created returns that dict. It must stay green.
    - The four existing tests pass unedited.

    TestInstallers (repo files read from REPO_ROOT):
    - `install.sh`, with lines whose stripped form starts with `#` removed, contains neither the pointer file name nor the legacy snake_case key. RED: line 49.
    - `installer/bin/create-max-framework.js`, with lines whose stripped form starts with `//`, `/*` or `*` removed, contains neither. RED: lines 61-62.
    - Skipped when `shutil.which("node")` is None: `[node, js, "--version"]` and `[node, js, "-v"]`, each with `cwd=tmp_path` and `timeout=30`, exit 0, and their stripped stdout equals `create-max-framework v` + `json.load(installer/package.json)["version"]`. RED: prints v1.0.0.

    Write the two forbidden literals in the test file as constants built from parts (for example `"." + "active-project.json"` and `"active" + "_project"`). That way the test source and this plan never contain a literal that a reader could mistake for a live write.
  </behavior>
  <action>
    Implement the Q8 "Untrack local files", "Installers", "get_active_project" and "Version" bullets (findings I1, I3 version part, B11 tracking part), per S3, S4, S5 and S9.

    RED:
    1. Add the `<behavior>` tests to `tests/test_project.py`: the TestActiveProject additions, and a new TestInstallers class with REPO_ROOT and the node skip. Run `python3 -m pytest -q -p no:cacheprovider tests/test_project.py`. Every RED case must fail for the stated reason and the guard must pass. Record the counts.

    GREEN:
    2. `src/maxpat/project.py`: rewrite `get_active_project` per S3, using `data.get("name")`.
       - Its docstring lists every None case, including "the legacy pointer that installers before Q8 wrote".
       - Leave `set_active_project` and `_PROJECT_NAME_RE` alone.
    3. `install.sh`:
       - delete the line that writes the pointer;
       - keep `mkdir -p "${PROJECT_NAME}/patches"`;
       - replace the comment above it with: `# Create the patches directory. No active-project pointer is written: a fresh install has no active project until /max-new or /max-switch sets one.`
    4. `installer/bin/create-max-framework.js`:
       - replace the hard-coded version constant with `const VERSION = require('../package.json').version;` plus a comment that the release workflow stamps package.json from the tag before publishing;
       - delete the `fs.writeFileSync(...)` call for the pointer;
       - keep the `patchesDir` mkdir;
       - change the comment above it to the same wording as step 3, with `//`.
    5. `.gitignore`: append a commented section ("Per-checkout local state -- never committed (review B11, I2)") with the anchored lines `/patches/.active-project.json` and `/.claude/projects/`.
    6. Re-run `tests/test_project.py` and `tests/test_release.py`, then `bash -n install.sh` and `node --check installer/bin/create-max-framework.js`. All green.

    COMMIT (temp index; never a path-scoped commit for this task, see `<rules>`):
    7. Run one `bash -c 'set -euo pipefail; ...'` block that does the following:
       - `OLD=$(git rev-parse HEAD)`; `IDX=$(mktemp -d)/index`;
       - `GIT_INDEX_FILE=$IDX git read-tree "$OLD"`;
       - `GIT_INDEX_FILE=$IDX git rm -q --cached -- patches/.active-project.json .claude/projects/-Users-taylorbrook-Dev-MAX/memory/feedback_multiple_choice.md`;
       - `GIT_INDEX_FILE=$IDX git add -- .gitignore src/maxpat/project.py tests/test_project.py install.sh installer/bin/create-max-framework.js`;
       - `TREE=$(GIT_INDEX_FILE=$IDX git write-tree)`;
       - `NEW=$(git commit-tree "$TREE" -p "$OLD" -m "fix(install): fresh installs have no active project - installers stop writing the pointer, get_active_project returns None for missing, malformed or legacy files, --version reads package.json; untrack patches/.active-project.json and .claude/projects/ (Q8 I1 I3 B11)")`;
       - `git update-ref -m "commit: Q8 Task 2" HEAD "$NEW" "$OLD"`;
       - `git reset -q -- .gitignore src/maxpat/project.py tests/test_project.py install.sh installer/bin/create-max-framework.js patches/.active-project.json .claude/projects/-Users-taylorbrook-Dev-MAX/memory/feedback_multiple_choice.md`;
       - remove the temp dir.

       Notes:
       - If `update-ref` fails because HEAD moved (another instance committed), rerun the whole block from the new HEAD.
       - The two local files are never written by this sequence and stay on disk. Their checksums must match `$Q/local-state.sha256`. The one legitimate exception: another instance ran `/max-switch` meanwhile; then record the new pointer content in SUMMARY.md instead.
    8. Run the verify.
  </action>
  <verify>
    <automated>bash -c 'H0=$(git rev-parse HEAD) || exit 1; S0=$(git diff --cached --name-only) || exit 1; python3 -m pytest -q -p no:cacheprovider -rs tests/test_project.py tests/test_release.py || exit 1; [ "$(git rev-parse HEAD)" = "$H0" ] || { echo MAX-REPO-HEAD-MOVED; exit 1; }; [ "$(git diff --cached --name-only)" = "$S0" ] || { echo MAX-REPO-STAGED-CHANGED; exit 1; }; GS=$(git status --porcelain -- patches/) || exit 1; [ -z "$GS" ] || { echo "PATCH-WORKTREE: $GS"; exit 1; }; echo PROJECT-INSTALLER-TESTS-GREEN-PATCHES-CLEAN'</automated>
    <automated>bash -c 'Q=.planning/quick/261012-sam-implement-q8-in-planning-reviews-2026-10; for p in patches/.active-project.json .claude/projects/-Users-taylorbrook-Dev-MAX/memory/feedback_multiple_choice.md; do if git ls-files --error-unmatch -- "$p" >/dev/null 2>&1; then echo "STILL-TRACKED $p"; exit 1; fi; if git cat-file -e "HEAD:$p" 2>/dev/null; then echo "STILL-IN-HEAD $p"; exit 1; fi; git check-ignore -q --no-index -- "$p" || { echo "NOT-IGNORED $p"; exit 1; }; [ -f "$p" ] || { echo "GONE-FROM-DISK $p"; exit 1; }; done; shasum -a 256 patches/.active-project.json .claude/projects/-Users-taylorbrook-Dev-MAX/memory/feedback_multiple_choice.md | diff - "$Q/local-state.sha256" || { echo LOCAL-FILES-CHANGED-CHECK-MAX-SWITCH; exit 1; }; SUBJ=$(git log -1 --format=%s) || exit 1; case "$SUBJ" in *"(Q8 I1"*) ;; *) echo HEAD-NOT-TASK2; exit 1;; esac; A=$(git diff-tree --no-commit-id --name-status -r HEAD) || exit 1; A=$(printf "%s\n" "$A" | sort); E=$(printf "D\t.claude/projects/-Users-taylorbrook-Dev-MAX/memory/feedback_multiple_choice.md\nM\t.gitignore\nM\tinstall.sh\nM\tinstaller/bin/create-max-framework.js\nD\tpatches/.active-project.json\nM\tsrc/maxpat/project.py\nM\ttests/test_project.py\n" | sort); [ "$A" = "$E" ] || { printf "%s\n---expected---\n%s\n" "$A" "$E"; exit 1; }; echo UNTRACKED-IGNORED-KEPT-COMMIT-SCOPED'</automated>
    <automated>bash -c 'bash -n install.sh && node --check installer/bin/create-max-framework.js || exit 1; V=$(node -e "console.log(require(\"./installer/package.json\").version)"); [ "$(node installer/bin/create-max-framework.js --version)" = "create-max-framework v$V" ] || { echo VERSION-MISMATCH; exit 1; }; npm pack --dry-run --json ./installer 2>/dev/null | python3 -c "import json,sys; f=[x[\"path\"] for x in json.load(sys.stdin)[0][\"files\"]]; assert \"package.json\" in f, f" || { echo PACKAGE-JSON-NOT-PUBLISHED; exit 1; }; echo INSTALLERS-OK'</automated>
    <automated>python3 -c "import ast,sys; [ast.parse(open(f).read(), filename=f, feature_version=(3, 10)) for f in sys.argv[1:]]; print('PY310-SYNTAX-OK')" src/maxpat/project.py tests/test_project.py</automated>
    <automated>python3 -m pytest -q -p no:cacheprovider && echo SUITE-GREEN</automated>
  </verify>
  <done>
    - A fresh install, a legacy installer pointer, a malformed pointer or a traversal name all give "no active project" instead of a crash. Valid pointers, including FDNVerb, still resolve.
    - Neither installer writes a pointer.
    - `--version` and `-v` print the package.json version.
    - Both local files are untracked, gitignored and still on disk, byte-identical.
    - HEAD's commit contains exactly the 7 expected name-status lines, and no other instance's staged work was swept.
    - Each RED case was recorded red first.
    - The full suite is green, and `git status --porcelain -- patches/` is now empty.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: CI on every push and PR (Python 3.10 and 3.12), and release gated on the same tests. test.yml (push to branches, pull_request, workflow_call) installs requirements-dev.txt and runs pytest; release.yml needs it and builds with scripts/build_release.sh into $RUNNER_TEMP; .release-ignore deleted; a shallow-clone CI simulation passes on 3.10 and 3.12 with no Max.app and no global git identity</name>
  <files>tests/test_release.py, .github/workflows/test.yml, .github/workflows/release.yml, requirements-dev.txt, .release-ignore</files>
  <read_first>.github/workflows/release.yml, tests/test_release.py (as left by Task 1), .planning/reviews/2026-10-11-repo-review.md (lines 57, 324)</read_first>
  <behavior>
    New fast, unmarked classes in `tests/test_release.py`. They read repo files with plain text and need no YAML library, so they also run in CI.

    TestCiConfig:
    - `.github/workflows/test.yml` exists, and its text contains `workflow_call`, `pull_request`, `branches:`, `ubuntu-latest`, `python -m pip install -r requirements-dev.txt`, `python -m pytest -q`, and the quoted versions `'3.10'` and `'3.12'`. RED: the file is missing.
    - `.github/workflows/release.yml` contains `uses: ./.github/workflows/test.yml`, matches the regex `needs:\s*\[?\s*test\b`, and contains `bash scripts/build_release.sh "$RUNNER_TEMP/framework.tar.gz"` and `${{ runner.temp }}/framework.tar.gz`. RED: none of these is there.
    - Write release.yml negative assertions as Python `not in` checks inside this test: no `--exclude-from`, no shell exit-code masking of the form `|| [[`, and no `tar czf`. RED: all three are present.
    - `(REPO_ROOT / ".release-ignore").exists()` is False. RED.

    TestDevRequirements:
    - `requirements-dev.txt` parses into names: strip `#` comments and blanks, then the name is the text before the first of `<>=!~[; ` (lowercased). Those names include numpy, scipy and pytest. RED: the file is missing.
    - AST-scan every `.py` under `src`, `tests`, `tools`, `scripts` and `.claude/scripts`, skipping `__pycache__`. Collect level-0 `import` / `from` top-level names. Remove `sys.stdlib_module_names` (Python 3.10+), the first-party names {src, tests, tools, scripts}, and any name that matches a scanned file stem or package dir. The rest must be a subset of the requirement names. Expected rest at planning: exactly {numpy, scipy, pytest}. RED: the file is missing.
  </behavior>
  <action>
    Implement the Q8 "CI" bullets (finding A4; R1's CI alternative, with the PostToolUse hook alternative not taken) and the release.yml half of "Release build", per S1, S7 and S8.

    RED:
    1. Add TestCiConfig and TestDevRequirements to `tests/test_release.py` per `<behavior>`, and extend its module docstring to cite A4. Run them; they must be red as stated. Record the counts.

    GREEN:
    2. Create `requirements-dev.txt` per S8.
    3. Create `.github/workflows/test.yml` per S7, with `name: Tests` and a job named `pytest (Python ${{ matrix.python-version }})`. Use two `run:` steps exactly as `python -m pip install -r requirements-dev.txt` and `python -m pytest -q`.
    4. Edit `.github/workflows/release.yml`:
       - add a `test` job before `release`: `uses: ./.github/workflows/test.yml` with `permissions: contents: read`;
       - add `needs: test` to the `release` job, and keep its `permissions: contents: write` and `actions/checkout@v6`;
       - replace the "Build tarball" step with a step named "Build release archive" whose run is exactly `bash scripts/build_release.sh "$RUNNER_TEMP/framework.tar.gz"`;
       - set the "Create GitHub Release" step's `files:` to `${{ runner.temp }}/framework.tar.gz`;
       - leave the setup-node, version and npm publish steps byte-identical;
       - add no comment that quotes the removed command.
    5. Delete `.release-ignore` from disk with `rm`, not `git rm`.
    6. Re-run `tests/test_release.py`; all green. Run the YAML structure check in the verify (local PyYAML).

    Commit with explicit paths only:
    - `git add -- tests/test_release.py .github/workflows/test.yml .github/workflows/release.yml requirements-dev.txt .release-ignore` (this stages the deletion);
    - `git commit -m "ci: pytest workflow on push and PR for Python 3.10 and 3.12; release runs the tests first and publishes the git-archive tarball from RUNNER_TEMP; requirements-dev.txt; drop .release-ignore (Q8 A4)" -- tests/test_release.py .github/workflows/test.yml .github/workflows/release.yml requirements-dev.txt .release-ignore`.

    CI simulation (after the commit, in the verify):
    - shallow-clone HEAD with `git clone -q --depth 1 "file://$(pwd)"` into a `mktemp -d` dir;
    - for each of Python 3.10 and 3.12:
      - `uv venv` it;
      - `uv pip install -r <clone>/requirements-dev.txt`;
      - in the clone, run `python -m pytest -q -p no:cacheprovider -rs` with `GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1 MAXPAT_TEST_MAX_APP=/nonexistent/Max.app`;
    - also run `bash scripts/build_release.sh` from the clone.

    Both runs must be green and must show the requires_max skip. If uv or the network is unavailable, the verify falls back to the local `python3`. Record that 3.10/3.12 were not exercised locally, and that the first GitHub run is then the only check.

    Then write SUMMARY.md (see `<output>`).
  </action>
  <verify>
    <automated>bash -c 'H0=$(git rev-parse HEAD) || exit 1; S0=$(git diff --cached --name-only) || exit 1; python3 -m pytest -q -p no:cacheprovider tests/test_release.py || exit 1; [ "$(git rev-parse HEAD)" = "$H0" ] || { echo MAX-REPO-HEAD-MOVED; exit 1; }; [ "$(git diff --cached --name-only)" = "$S0" ] || { echo MAX-REPO-STAGED-CHANGED; exit 1; }; GS=$(git status --porcelain -- patches/) || exit 1; [ -z "$GS" ] || { echo "PATCH-WORKTREE: $GS"; exit 1; }; [ ! -e .release-ignore ] || { echo RELEASE-IGNORE-STILL-ON-DISK; exit 1; }; echo CI-CONFIG-TESTS-GREEN'</automated>
    <automated>python3 -c "import yaml; t=yaml.safe_load(open('.github/workflows/test.yml')); r=yaml.safe_load(open('.github/workflows/release.yml')); on=t.get('on', t.get(True)); assert {'push','pull_request','workflow_call'} <= set(on), on; assert on['push'].get('branches') and not on['push'].get('tags'), on['push']; assert t['permissions']=={'contents':'read'}, t.get('permissions'); j=list(t['jobs'].values())[0]; assert j['runs-on']=='ubuntu-latest'; assert j['strategy']['matrix']['python-version']==['3.10','3.12'], j['strategy']; runs=[s.get('run','').strip() for s in j['steps']]; assert 'python -m pip install -r requirements-dev.txt' in runs and 'python -m pytest -q' in runs, runs; ro=r.get('on', r.get(True)); assert ro=={'push':{'tags':['v*']}}, ro; assert r['jobs']['test']['uses']=='./.github/workflows/test.yml', r['jobs']['test']; n=r['jobs']['release']['needs']; assert n in ('test',['test']), n; rs=r['jobs']['release']['steps']; assert any(s.get('run','').strip()=='bash scripts/build_release.sh \"\$RUNNER_TEMP/framework.tar.gz\"' for s in rs), rs; up=[s for s in rs if 'action-gh-release' in s.get('uses','')][0]; assert up['with']['files']=='\${{ runner.temp }}/framework.tar.gz', up; assert any('npm publish' in s.get('run','') for s in rs); print('WORKFLOWS-OK')"</automated>
    <automated>bash -c 'SCR=$(mktemp -d); git clone -q --depth 1 "file://$(pwd)" "$SCR/ci" || exit 1; PYS=""; if command -v uv >/dev/null; then for V in 3.10 3.12; do if uv venv -q --python "$V" "$SCR/v$V" && uv pip install -q --python "$SCR/v$V/bin/python" -r "$SCR/ci/requirements-dev.txt"; then PYS="$PYS $SCR/v$V/bin/python"; else echo "UV-PY$V-UNAVAILABLE"; fi; done; fi; [ -n "$PYS" ] || { echo CI-SIM-FALLBACK-PYTHON3; PYS=python3; }; for PY in $PYS; do (cd "$SCR/ci" && GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1 MAXPAT_TEST_MAX_APP=/nonexistent/Max.app "$PY" -m pytest -q -p no:cacheprovider -rs) > "$SCR/out.txt" 2>&1 || { tail -40 "$SCR/out.txt"; echo "CI-SIM-RED $PY"; exit 1; }; grep -q "requires the Max application bundle" "$SCR/out.txt" || { echo "NO-REQUIRES-MAX-SKIP $PY"; exit 1; }; echo "$("$PY" --version 2>&1): $(tail -1 "$SCR/out.txt")"; done; (cd "$SCR/ci" && bash scripts/build_release.sh "$SCR/fw.tar.gz") >/dev/null || { echo CLONE-RELEASE-BUILD-FAILED; exit 1; }; rm -rf "$SCR"; echo CI-SIM-GREEN'</automated>
    <automated>bash -c 'Q=.planning/quick/261012-sam-implement-q8-in-planning-reviews-2026-10; L=$(git log --format=%s "$(cat $Q/base-sha.txt)"..HEAD) || exit 1; N=$(printf "%s\n" "$L" | grep -c "(Q8 "); [ "$N" -ge 3 ] || { echo "Q8-COMMITS=$N"; exit 1; }; [ "$(git stash list)" = "$(cat $Q/stash-list-before.txt)" ] || { echo STASH-LIST-CHANGED; exit 1; }; python3 -m pytest -q -p no:cacheprovider && echo SUITE-GREEN-Q8-COMMITS-$N'</automated>
    <automated>python3 -c "import ast,sys; [ast.parse(open(f).read(), filename=f, feature_version=(3, 10)) for f in sys.argv[1:]]; print('PY310-SYNTAX-OK')" tests/test_release.py</automated>
  </verify>
  <done>
    - test.yml runs pytest on ubuntu for Python 3.10 and 3.12 on every branch push, PR and workflow_call.
    - release.yml can't publish unless that same job passes, and it uploads the git-archive tarball from `$RUNNER_TEMP`.
    - `.release-ignore` is gone, and requirements-dev.txt covers every third-party import.
    - A fresh shallow clone passes the full suite on 3.10 and 3.12 (or the recorded fallback), with Max.app simulated absent and no global git identity, and the clone builds the release archive.
    - Each RED case was recorded red first.
    - The main-tree suite is green.
    - There are at least 3 `(Q8 ` commits since base-sha, each touching only its task's paths, and the stash list is unchanged.
    - Nothing was pushed, tagged or published.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Repo HEAD -> public release tarball | Everything export-ignore lets through is published to every installer user. |
| Release tag -> GitHub Release + npm | A tag push publishes artifacts with `contents: write` and NPM_TOKEN. |
| Installer -> user's new project | The installers lay out the project the framework then reads (`get_active_project`). |
| Pointer file -> filesystem path | `name` from a JSON file becomes `patches/<name>`. |
| CI runner -> GITHUB_TOKEN | Test jobs run repo code with the token's permissions. |
| Executor -> shared git index | Other instances may have work staged in the same index. |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-sam-01 | Information Disclosure | Release tarball ships the maintainer memory file `.claude/projects/...` (I2) | high | mitigate | `/.claude/projects export-ignore` plus untrack and gitignore (Task 2). The smoke test asserts no `.claude/projects` member. |
| T-sam-02 | Tampering | Wrong release contents: `.claude/scripts/` stripped, nested truncated tarball, masked tar errors (I2) | high | mitigate | `git archive` of HEAD from the object DB (it can't capture its own output) into `$RUNNER_TEMP`. Anchored patterns, with a test that every export-ignore pattern starts with `/`. `set -euo pipefail` plus a `tar -tzf` integrity listing. The smoke test checks the runtime files, the exclusions, nested archives and that every src module imports. |
| T-sam-03 | Tampering | Release publishes untested code (A4) | high | mitigate | release.yml `release` `needs` the `test` job, which calls test.yml (full suite, including the archive smoke test, on 3.10 and 3.12). |
| T-sam-04 | Denial of Service | Fresh or legacy installs crash `/max-status` and `/max-build` on the pointer file (I1) | high | mitigate | Installers stop writing it. `get_active_project` returns None for missing, malformed, legacy or invalid names. Tests reproduce each crash first. |
| T-sam-05 | Elevation of Privilege | A pointer `name` with `..` or separators escapes `patches/` (B11) | medium | mitigate | Single-path-component check (S3). The traversal and multi-component tests return None. |
| T-sam-06 | Tampering | A shared tracked pointer lets one clone retarget another's project through git (B11) | medium | mitigate | Untracked and gitignored. Instances sharing one working tree still share it: residual S9, listed in SUMMARY. |
| T-sam-07 | Elevation of Privilege | Over-privileged GITHUB_TOKEN in test jobs | medium | mitigate | `permissions: contents: read` on test.yml and on release.yml's `test` caller job. Only the `release` job keeps `contents: write`. |
| T-sam-08 | Repudiation | Installer reports the wrong version (I3) | low | mitigate | `--version` reads package.json, which release.yml stamps from the tag. A node test compares it with package.json. |
| T-sam-09 | Tampering | The untrack commit sweeps other instances' staged work, or re-adds the removed files | high | mitigate | Temp-index plumbing commit with an `update-ref` old-value guard, then `git reset` of exactly the task's paths. The verify asserts HEAD's name-status list is exactly the 7 expected lines and that both files are still on disk and ignored. |
| T-sam-10 | Tampering | Tests write to the MAX repo or committed patches | high | mitigate | The only git command against the checkout is the read-only archive build into `tmp_path`. Each verify asserts HEAD, the staged set and `patches/` status are unchanged. |
| T-sam-11 | Tampering | Path traversal when the smoke test extracts the archive | low | mitigate | Every member is validated (under the prefix, not absolute, no `..`, file or dir only), and `filter="data"` is used when available. The archive is self-built from HEAD. |
| T-sam-12 | Tampering | `curl \| bash` pulls an unpinned `latest` with no checksum (I3 remainder) | medium | accept | Not in the Q8 spec. Listed as a SUMMARY residual for a follow-up task. |
| T-sam-SC | Tampering | pip installs in CI; third-party GitHub Actions | high | mitigate | No new package: numpy, scipy and pytest are pre-existing imports, [VERIFIED] by an AST scan and a planning-time PyPI install (see `<package_legitimacy>`). A test keeps requirements-dev.txt a superset of the imports. Actions use the official `actions/*@v6` plus the pre-existing `softprops/action-gh-release@v3`. SHA pinning is a residual. |
</threat_model>

<source_audit>
Sources:
- the fix-plan Q8 section and its rules;
- review findings A4, I1, I2, I3 and B11, simplification S10, and R1's CI clause;
- the Q5 and Q7 hand-offs: CI runs the tmp-repo git tests, and the runner needs git;
- the orchestrator's notes: sequential main tree, explicit staging, no stash, no push and no release, workflows validated locally.

This quick task has no ROADMAP phase, CONTEXT.md or RESEARCH.md.

| Source item | Covered by | Status |
|---|---|---|
| GOAL: CI tests, release tarball, installer | Tasks 1-3 | COVERED |
| CI: test.yml, push + pull_request, ubuntu, Python 3.10 and 3.12, requirements-dev.txt, `python -m pytest -q` | Task 3 (S7, S8) | COVERED (also workflow_call) |
| CI: Max.app tests skip cleanly; `requires_max` marker | Task 1 (S6) | COVERED (probe found 1 test; env-var simulation) |
| CI: release.yml runs the tests first | Task 3 | COVERED |
| Release: `git archive --prefix=MAX-MSP_CC_Framework/ HEAD` + `.gitattributes` export-ignore replacing `.release-ignore` | Task 1 (archive, attrs); Task 3 (delete `.release-ignore`, wire release.yml) | COVERED |
| Release: anchored patterns; `.claude/scripts/` ships; ./scripts, tests, patches, .planning, .github, .claude/projects excluded | Task 1 (S2, TestGitattributes, TestReleaseArchive) | COVERED (plus installer, `.gitattributes`, OQ1 audit) |
| Release: archive to `$RUNNER_TEMP`; stop masking tar's exit code | Task 1 (script); Task 3 (release.yml) | COVERED |
| Untrack `.claude/projects/` and `patches/.active-project.json`, gitignore both, files stay on disk | Task 2 (temp-index commit) | COVERED |
| Installers stop writing the legacy pointer | Task 2 | COVERED |
| `get_active_project`: None for missing, malformed or legacy files, using `data.get("name")` | Task 2 (S3) | COVERED (plus name-component check from B11) |
| Version: `--version` reads package.json | Task 2 (S5) | COVERED |
| Smoke test (slow): build + extract; `.claude/scripts/extract_objects.py` exists; no `.claude/projects`; no nested tarball; import every src module; fresh-layout `get_active_project` None | Task 1 | COVERED |
| Q5/Q7 hand-off: CI runs the tmp-repo git tests (git present, no global identity) | Task 3 CI simulation (`GIT_CONFIG_GLOBAL=/dev/null`) | COVERED |
| I3: cut a fresh release; publish checksums; pin the `curl \| bash` version | SUMMARY manual steps and residuals | EXCLUDED (outward-facing or not in the Q8 spec) |
| B11: per-session pointer / pass the project explicitly | SUMMARY residual | EXCLUDED (not in the Q8 spec) |
| R1: Claude Code PostToolUse hook alternative | — | EXCLUDED (R1 says "or"; CI job chosen by the spec) |
| Docs (README, TECHNICAL test-suite and active-project sections) | SUMMARY doc-impact list | EXCLUDED from edits (rule 8; the Q8 spec lists no docs) |
| OQ1: `.claude/max-objects/audit/` in the release | Task 1, per the answer (default A) | COVERED |
</source_audit>

<verification>
- `python3 -m pytest -q -p no:cacheprovider` is fully green before (expected 2661 passed, 1 xfailed, 1 xpassed, 29 warnings) and after each task.
  - Passes rise only by the new tests, and xfailed/xpassed stay at 1/1.
  - Record the warning count before and after. Registered markers add no PytestUnknownMarkWarning.
- After every test run, the MAX repo HEAD and staged set are unchanged by the tests. `git status --porcelain -- patches/` shows only the pre-existing `.active-project.json` before Task 2 and nothing after.
- There are at least 3 `(Q8 ` commits since `base-sha.txt` (more only for fix-forwards), each touching only its task's paths. The stash list is unchanged.
- The Python 3.10 syntax gate passes on every changed `.py` file. The shallow-clone CI simulation is green on Python 3.10 and 3.12 (or the fallback is recorded).
- Nothing was pushed, tagged, released or published.
</verification>

<success_criteria>
- A4 is fixed: a CI pytest job runs on push and PR for Python 3.10 and 3.12, and the release workflow is gated on it.
- I2 is fixed: the release is a `git archive` of HEAD with anchored export-ignore rules, built into `$RUNNER_TEMP` by one script with no masked errors. It ships `.claude/scripts/`, and neither the memory file nor a nested tarball. A smoke test proves all of this, plus that every src module imports.
- I1 is fixed: no installer writes the legacy pointer, and `get_active_project` tolerates missing, malformed and legacy files.
- I3 (version) is fixed: `--version` reads package.json.
- B11 (tracking) is fixed: the pointer and `.claude/projects/` are untracked and gitignored, and stay on disk.
- The suite is green on the main tree and in a clean shallow clone on 3.10 and 3.12. No patch file is touched.
</success_criteria>

<output>
Create `.planning/quick/261012-sam-implement-q8-in-planning-reviews-2026-10/261012-sam-SUMMARY.md` when done. It must include:
- baseline and final pytest totals, the red counts recorded before each GREEN step, and the pytest warning count before and after;
- how OQ1 was resolved: user answer, or "resolved by default" with option A;
- the archive facts: member count, size, and confirmation that `.claude/scripts/*` and (OQ1) the width table ship and the excluded trees don't;
- the CI-simulation results: Python versions, totals, the requires_max skip line, and any fallback;
- the untrack commit:
  - why it used a temp index (the path-scoped-commit re-add trap);
  - HEAD's name-status list;
  - the local-file checksums before and after (or the recorded `/max-switch` exception);
- settled decisions worth knowing:
  - `get_active_project` doesn't use `_PROJECT_NAME_RE` (FDNVerb);
  - test.yml's `branches: ['**']` keeps tag pushes from double-running it;
  - the Python versions are quoted;
  - `MAXPAT_TEST_MAX_APP` is the test seam;
- **manual steps for the user** (never done by the executor):
  1. Phase 1 of the fix plan (Q1-Q8) is complete. Per its "Push main after each phase", run `git push origin main` and watch the first Tests run in the GitHub Actions tab, for both Python versions.
  2. To ship the fixes (I3 "release after the fixes"), tag the next version (for example `v5.1.0`) and push the tag. release.yml then runs the tests, builds the archive, creates the GitHub Release and runs npm publish (needs the NPM_TOKEN secret).
  3. Optionally confirm the published tarball lists `MAX-MSP_CC_Framework/.claude/scripts/extract_objects.py`.
- side effects the user should know:
  - other clones (other machines) that pull the untrack commit have their local `patches/.active-project.json` and the stray memory copy deleted by git; they re-run `/max-switch` there;
  - GitHub's auto-generated "Source code" archives also honor export-ignore now;
- residuals, all out of scope:
  - per-session pointer (instances sharing one working tree still share it, B11);
  - release checksums and a pinned `curl | bash` version (I3);
  - Actions pinned by major tag rather than SHA;
- doc impact, not edited (rule 8):
  - README Option C (git clone) and a contributor note about `pip install -r requirements-dev.txt`;
  - TECHNICAL "Test Suite" (stale count; CI, markers, `MAXPAT_TEST_MAX_APP`);
  - TECHNICAL "Active Project Tracking" (the pointer is per-checkout and untracked, and missing/malformed/legacy means no active project);
- hand-offs:
  - Q9: its help-io test should use `@pytest.mark.requires_max`;
  - any future release-content change goes through `.gitattributes` and `tests/test_release.py`;
- rule 9, "Confirm in MAX": no patch file changed, so nothing is required.
</output>
