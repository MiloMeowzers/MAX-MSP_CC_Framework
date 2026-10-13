---
phase: quick-261012-sam
verified: 2026-10-13T04:39:52Z
status: passed
score: 8/8 must-haves verified
covered_files:
  - ".gitattributes"
  - ".github/workflows/release.yml"
  - ".github/workflows/test.yml"
  - "requirements-dev.txt"
  - "scripts/build_release.sh"
  - "src/maxpat/project.py"
  - "tests/test_release.py"
  - ".planning/quick/261012-sam-implement-q8-in-planning-reviews-2026-10/261012-sam-PLAN.md"
  - ".planning/quick/261012-sam-implement-q8-in-planning-reviews-2026-10/261012-sam-SUMMARY.md"
covered_digest: "v2:sha256:1c0158240100cf9f0b3d43d65b13742ab4698b0fd7b877c9fc9d19e2018b9e38"
behavior_unverified: 0
overrides_applied: 0
---

# Quick 261012-sam (Q8): CI tests, release tarball, installer. Verification Report

**Goal:** Implement Q8 of the 2026-10-11 fix plan (findings A4, I1, I2, I3 version, B11 tracking).
**Status:** passed. **Re-verification:** No.

## Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `build_release.sh OUT [TREEISH]` runs `git archive --prefix=MAX-MSP_CC_Framework/`, cd's to top level, `set -euo pipefail`, no masking. release.yml runs it into `$RUNNER_TEMP` and publishes that file | VERIFIED | Script read in full. I ran it from the repo and it produced a 240-entry archive in the scratchpad. release.yml diff shows `bash scripts/build_release.sh "$RUNNER_TEMP/framework.tar.gz"` and `files: ${{ runner.temp }}/framework.tar.gz`. No `tar czf`, `--exclude-from` or `\|\| [[` remain. |
| 2 | Archive ships `.claude/scripts/*`, CLAUDE.md, src, tools, DB and `audit/width-overrides.json` (user decision A). Nothing under tests, patches, .planning, .github, scripts, installer, `.claude/projects`. No `.gitattributes`, no nested archive. All patterns anchored | VERIFIED | Independent extraction: the 4 `.claude/scripts/*.py` files are present. The only audit file is `width-overrides.json`. The exclusion grep returned nothing. No `.tar/.zip/.release-ignore`. Top level is `.claude .gitignore CLAUDE.md install.sh LICENSE patterns README.md requirements-dev.txt src TECHNICAL.md tools`. Every `.gitattributes` pattern starts with `/`. (`src/maxpat/audit/` ships, correctly: it is source, not the anchored data dir.) |
| 3 | Every src module imports from the archive. `cycle~` resolves. Width table non-empty. `get_active_project` is None on the fresh layout | VERIFIED | In the extracted archive with `python3 -I`, no PYTHONPATH: `len(_WIDTH_OVERRIDES)=513`, `lookup('cycle~')` found, `sizing.__file__` inside the extract, `get_active_project` is None. The full import walk is covered by the slow test, which passed in the suite. |
| 4 | `get_active_project` returns None and never raises for missing, bad, legacy, nameless, non-string, empty, `.`/`..` and multi-component names. FDNVerb still resolves | VERIFIED | `project.py` read: `is_file` guard, `except (OSError, ValueError)`, dict check, `data.get("name")` str check, component check, dir check. `_PROJECT_NAME_RE` is not used. The new tests cover every case and pass. |
| 5 | Neither installer writes a pointer. `--version` and `-v` print the package.json version | VERIFIED | d1bd3c1 diff removes the `echo` in install.sh and `fs.writeFileSync` in the JS. `node ... --version` and `-v` both print `create-max-framework v2.3.1`, matching package.json. |
| 6 | Pointer and `.claude/projects/` are untracked and gitignored in one commit that sweeps nothing else. Files stay on disk, byte-identical | VERIFIED | `git ls-files` returns 0 for both. `check-ignore` hits `.gitignore:19-20`. Both files are on disk. SHA-256 matches `local-state.sha256`. d1bd3c1 name-status is exactly the 7 expected paths. Staged set is empty. |
| 7 | test.yml: ubuntu-latest, Python '3.10' and '3.12', push to branches, pull_request, workflow_call, installs requirements-dev.txt, runs `python -m pytest -q`. release `needs` a test job that calls test.yml. `.release-ignore` deleted | VERIFIED | Files read and parsed with PyYAML. `permissions: contents: read`. The `test` job uses `./.github/workflows/test.yml` and `release` has `needs: test`. `.release-ignore` is absent. `requirements-dev.txt` holds numpy, scipy and pytest. |
| 8 | `requires_max` skips cleanly without Max.app. Full suite green. Nothing pushed, tagged or released | VERIFIED | With `MAXPAT_TEST_MAX_APP=/nonexistent/Max.app`, `TestIOCrossCheck` gives 1 SKIPPED with reason "requires the Max application bundle at ...". Full suite: `2691 passed, 1 xfailed, 1 xpassed, 29 warnings`. No remote/tag actions found. Python 3.10 AST gate passes on the changed `.py` files. |

**Score:** 8/8 truths verified.

## Key Links

| From | To | Status |
|------|----|--------|
| release.yml | scripts/build_release.sh | WIRED |
| release.yml | test.yml (`uses` + `needs`) | WIRED |
| tests/test_release.py | build_release.sh (fixture) | WIRED. Slow smoke test passed in the suite. |
| build_release.sh | .gitattributes (export-ignore honored) | WIRED. Confirmed by my own archive build. |
| conftest.py | test_extraction.py (`requires_max`) | WIRED |

## Anti-Patterns

No TBD/FIXME/XXX debt markers were introduced. The ERR trap in `build_release.sh` that removes a partial output is a benign addition beyond the plan. Repo state after verification is unchanged: nothing staged, no new tracked modifications.

## Human Verification

None required. Nothing here needs confirmation in MAX. The first GitHub Actions run of Tests on Python 3.10 and 3.12 is the only check not exercised in this verification. I did not run the 3.10/3.12 shallow-clone simulation myself. I relied on the Python 3.10 syntax gate and the SUMMARY's report of that simulation. The push and tag are deliberate manual steps and are not gaps.

## Gaps Summary

None. The residuals the SUMMARY lists (per-session pointer, release checksums and pinned `curl | bash`, Actions pinned by tag) are out of Q8 scope.

---
_Verified: 2026-10-12_
_Verifier: Claude (gsd-verifier)_
