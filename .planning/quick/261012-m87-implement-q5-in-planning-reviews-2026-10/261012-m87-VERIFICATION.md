---
phase: quick-261012-m87
verified: 2026-10-12T00:00:00Z
status: passed
score: 6/6 must-haves verified
behavior_unverified: 0
overrides_applied: 0
gaps: []
human_verification: []
---

# Quick 261012-m87 (Q5): Save-path safety Verification Report

**Goal:** Path-scoped auto-commit and stale-file check (review findings A5, A6).
**Commits:** 540c335, d66b34a, 1fdcf8a (HEAD, base 1fa28a3)
**Status:** passed
**Re-verification:** No

## Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A pre-staged unrelated file is not in the patch commit and stays staged (roundtrip, write_gendsp, write_js, direct auto_commit_patch) | VERIFIED | Independent tmp-repo run: `other.txt` staged; commit contained only `patches/proj/a.maxpat`; staged set still `['other.txt']` after roundtrip, write_js and write_gendsp saves. Covered by TestPathScopedCommit, TestAutoCommitDirect and TestWriteHelpersCommit. |
| 2 | A no-op second save makes no commit and keeps the other file staged | VERIFIED | Independent run: second save returned None and warned "no changes to commit". Commit count stayed at 2 and `other.txt` stayed staged. |
| 3 | auto_commit_patch uses `rev-parse --show-toplevel`, absolute literal pathspecs after `--`, checked return codes, full hash returned, RuntimeError on git failure | VERIFIED | `src/maxpat/project.py` `_run_git` and `auto_commit_patch` read directly. `_run_git` prefixes `--literal-pathspecs` and raises RuntimeError naming the subcommand and stderr. add, `diff --cached --quiet -- paths`, `commit -q -m msg -- paths` and `log -1 --format=%H -- paths` all go through it. The returned hash is 40 characters and equals HEAD. Tests cover a glob-character name, a git add failure and a non-repo. |
| 4 | save_patch_roundtrip returns the hash. write_gendsp and write_js keep their return values plus a `commit_hash` attribute (OQ1 Option A). A None result warns with the reason | VERIFIED | `GendspWriteResult(dict)` and `JsWriteResult(list)` carry `commit_hash`; I confirmed `isinstance` dict and list. `_auto_commit_saved_file` warns for four reasons: not a repo, outside `patches/<project>/`, git failure, no changes. Independent run: a `write_js` outside `patches/` returned None and warned. |
| 5 | A stale original_text raises StaleFileError before any write or commit. force=True overwrites with a warning. A missing target is never stale | VERIFIED | Independent run: StaleFileError raised, file left as MAX wrote it, commit count unchanged. `force=True` saved and warned. The check sits before mkdir and write in `hooks.py`. StaleFileError is exported from `src.maxpat`. |
| 6 | CLAUDE.md Rule #7 paragraph and hooks docstrings. Suite green, no patch file changed, MAX repo HEAD and index untouched, Python 3.10 syntax | VERIFIED | `git diff --name-only 1fa28a3 HEAD` lists only CLAUDE.md, `__init__.py`, `hooks.py`, `project.py` and `tests/test_save_safety.py`. The CLAUDE.md paragraph (+2 lines) covers path-scoping, warnings, StaleFileError and force. Full suite: 2540 passed, 1 xfailed, 1 xpassed, 29 warnings. HEAD unchanged, index empty and stash list empty after the runs. `ast.parse(feature_version=(3,10))` passes on all four .py files. |

**Score:** 6/6 truths verified. No behavior-dependent truth lacks a behavioral test: the tmp-repo tests passed, and I reproduced them independently.

## Required Artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| `tests/test_save_safety.py` | VERIFIED | Contains TestPathScopedCommit (the line-count minimum is not re-checked). 20 tests across 5 classes, all using tmp_path repos. |
| `src/maxpat/project.py` | VERIFIED | Contains `--show-toplevel` and `--literal-pathspecs`. |
| `src/maxpat/hooks.py` | VERIFIED | `class StaleFileError`, `_auto_commit_saved_file` returning hash or warning, `force` keyword. |
| `src/maxpat/__init__.py` | VERIFIED | Exports StaleFileError. |
| `CLAUDE.md` | VERIFIED | Rule #7 paragraph present. |

## Key Links

| From | To | Status |
|------|----|--------|
| save_patch_roundtrip / write_gendsp / write_js | `_auto_commit_saved_file` | WIRED (hooks.py lines 264, 382, 524) |
| `_auto_commit_saved_file` | `auto_commit_patch` | WIRED. It is the only production caller; commit scope was shown by the independent run. |
| `auto_commit_patch` | git (`--literal-pathspecs`) | WIRED |
| read_patch `original_text` | stale check in save_patch_roundtrip | WIRED |

## Requirements Coverage

| Requirement | Status |
|-------------|--------|
| A5 (whole-index commit, unchecked return codes, silent failure) | SATISFIED |
| A6 (lost update) | SATISFIED |

## Anti-Patterns

No TBD, FIXME or XXX markers and no stubs in the changed files. The `except Exception` in `_auto_commit_saved_file` is deliberate: it warns with the reason and never swallows silently.

## Advisory Notes (not blocking)

- **TOCTOU window.** The file can change between the stale check and the write. The window is milliseconds and Q36 owns atomic writes. The SUMMARY records it as accepted.
- **Unchecked overwrites remain.** Saves with `original_text=None`, `write_gendsp` and `write_js` overwrite without a stale check. This is documented in the docstrings and is out of scope for Q5.
- **Stale baseline after a save.** `original_text` goes stale after any save, so a command that saves twice with the same `original_text` will now raise. `.claude/commands/max-iterate.md` step 18 does not yet mention StaleFileError. The SUMMARY lists this under "Doc impact", deferred.
- **More warnings in the suite.** Warnings rose from 9 to 29, all "not inside a git repository" from tmp_path saves in existing tests. No filters were added.
- **Gate script under zsh.** The plan's final gate script needs `bash -c`, because the unquoted `$H` word-splits under zsh.

## Human Verification

None required. The optional MAX-side check in the SUMMARY (save in MAX, then run /max-iterate and expect StaleFileError) is a nice-to-have, not a gate.

---
_Verified: 2026-10-12_
_Verifier: Claude (gsd-verifier)_
