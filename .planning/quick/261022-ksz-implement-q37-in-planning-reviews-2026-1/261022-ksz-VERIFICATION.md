---
phase: quick-261022-ksz
verified: 2026-10-22T00:00:00Z
status: human_needed
score: 7/7 must-haves verified
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Copy a real error line from the Max 9.2 Console window and paste it into /max-diagnose"
    expected: "Line matches its troubleshooting.md entry in the exact tier and locates the box. Check whether the copied text includes the object column and how it is separated (tab vs `obj: msg`)."
    why_human: "The Console paste format is not recorded anywhere. A tab-separated object column without a colon would only match in the no-prefix tier. Executor flagged this itself."
  - test: "M4L overlay"
    expected: "Stays experimental until a device is confirmed in Live."
    why_human: "Needs Ableton Live."
---

# Quick 261022-ksz (Q37) Verification Report

**Goal:** Implement Q37: /max-diagnose, confirmation lifecycle, router domains.
**Status:** human_needed. All automated must-haves pass; the only open items are the two MAX/Live checks below, which cannot be verified from the repo.

## Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `diagnose_console` / CLI map console lines to ranked troubleshooting.md entries, tables parsed live, tiers, best tier only | VERIFIED | `src/maxpat/diagnose.py` (696 lines). My own CLI run on a 5-line paste: 4 matched `[exact]`, 1 unmatched. The 6 same-wording `No such object` rows are all returned. Entries carry section, cause, fix and source. The unmatched line says "never invent console wording". |
| 2 | Read-only box location with skip rules, gen-section codebox hits with line numbers, fallbacks, malformed files listed | VERIFIED | CLI output: `box: fixtures/fx-genfail.maxpat [gen~] obj-2 [codebox] (code; lines 1, 2, 3)`, and gen containers for the compile line. Scanned 6 files (no `test-results/` or `__maxbridge_*` copies). The comment boxes in the fixtures were not reported as hits. |
| 3 | max-bridge fixtures: `osc~` -> fx-nosuchobj obj-3 with Pure Data fact (cycle~); `can't assign to parameter g` -> fx-genfail obj-2; `gen~: failed to compile patcher` matches the genpatcher row; patches/max-bridge bytes unchanged | VERIFIED | All three reproduced. `fact: osc~: Pure Data name, not MAX; MAX equivalent cycle~` was printed as `cycle~`. `shasum` of every file under patches/max-bridge before and after the run: identical. |
| 4 | /max-diagnose never edits; diagnose.py has no write/rename/subprocess/hooks/atomic_io; paste via file/stdin; fixes via /max-iterate | VERIFIED | The imports are argparse, json, os, re, sys, dataclasses, pathlib and walk only. The AST gate test passes. `.claude/commands/max-diagnose.md` requires a temp file, forbids interpolation and routes every fix through `/max-iterate` with a multiple-choice approval. `cat paste \| ... -` (stdin) also works. |
| 5 | `record_confirmation` writes `v<ver>-<slug>-confirmed.md`, never overwrites, rejects private/outside paths, path-scoped commit | VERIFIED | Spot-check in a temp git repo. File 1 was `v0.1.0-feature-x-confirmed.md`, file 2 was `...-confirmed-2.md`. Each produced its own commit touching only that one path. An untracked `other.txt` stayed untouched. `/Users/` evidence and a `../../` file were both rejected with ValueError. |
| 6 | `append_proven_form` atomic validated insert at end of section; tier validation; refuses duplicates/unknown sections; other lines unchanged; docs describe the flow | VERIFIED | On a copy of the real proven-forms.md, the diff showed only 7 added lines, placed at the end of the MC section before `## FluCoMa`. Duplicate title, unknown section, `[confirmed]` without a date and an unknown tier were all refused. `/max-test` steps 5-8 and the max-lifecycle SKILL.md "Confirmation Lifecycle" document the record -> offer (multiple choice) -> explicit-path commit flow. |
| 7 | dispatch-rules.md `## Domain Overlays` (Jitter, M4L experimental, poly~) with detect, DB-resolving objects, lead, reading, checks; router SKILL.md lists them | VERIFIED | All 54 backticked object references across the 3 overlays do a non-None `ObjectDatabase.lookup()` with `get_effective_restrictions == []`. The SKILL.md table was added, with a pointer to "Domain Overlays". No new agents were created. |
| 8 | Regression gate: full suite rc 0, junit_diff 0, patches/patterns unchanged, no stash | VERIFIED | `final-rc.txt`=0, `baseline-rc.txt`=0. `final-pytest.txt` has 6008 passed, 5 xfailed, 1 xpassed. `junit_diff.py baseline-junit.xml final-junit.xml` printed `base=5887 new=6014 added=127 offenders=0` (rc 0). `git diff --name-only 3a60d201..HEAD -- patches patterns` is empty. `git status --porcelain patches patterns` is empty. `git stash list` is empty. |

**Score:** 7/7 plan truths plus the regression gate verified. 0 behavior-unverified.

## Tests I ran

`python3 -m pytest -q tests/test_diagnose.py tests/test_testing.py tests/test_commands.py tests/test_agent_skills.py tests/test_doc_signatures.py` -> **495 passed**.

## Artifacts

| Artifact | Status |
|----------|--------|
| `src/maxpat/diagnose.py` (`def diagnose_console(`) | exists, substantive, wired (CLI, tests, registered in `test_doc_signatures._INDEX_MODULES`) |
| `tests/test_diagnose.py` (`test_cli_max_bridge_read_only`) | exists, 504 lines |
| `.claude/commands/max-diagnose.md` | exists, contains `python3 -m src.maxpat.diagnose`, registered in `test_commands.ALL_COMMANDS` |
| `src/maxpat/testing.py` (`record_confirmation` etc.) | exists, 406 lines added, uses `atomic_write_bytes` and a lazy `_auto_commit_saved_file` |
| `dispatch-rules.md` (`## Domain Overlays`) | exists |

## Key links

- `diagnose.py` -> `troubleshooting.md`: parsed at call time. The CLI output matches the file's wording.
- `diagnose.py` -> `walk`: `import walk`. Box hits come from it.
- `testing.py` -> `hooks._auto_commit_saved_file`: the commit behaviour was observed.
- `testing.py` -> `atomic_io.atomic_write_bytes`: present in both write paths, with a rollback on failure in `append_proven_form`.
- `max-test.md` -> `record_confirmation`: documented.
- Router SKILL.md -> Domain Overlays: present.

## Anti-patterns / scope

- No patches/ or patterns/ changes. The 4 commits touch 13 files, all within the plan's `files_modified`.
- No TBD/FIXME/XXX debt markers were checked in the changed files beyond the test suite. None surfaced in my reads.
- Only the minor documented additions went beyond the plan: accepting a leading `v` on `version`, rejecting multi-line `lesson`/`max_version`, and the `Skipped: ... (outside the project)` listing.
- Doc impact (README, TECHNICAL, CLAUDE.md, shared-capabilities, max-verify, test-protocol.md, project-structure.md) is listed in SUMMARY and was deliberately not edited, per fix-plan rule 8.

## Notes (non-blocking)

- For `osc~: No such object`, the six same-wording entries tie. The command doc's judgment step (step 5, using the `fact:` line) chooses between them. The Pure Data row is not ranked first by the code. This is by design, as the SUMMARY documents.
- For `send: bad arguments creating object`, the locator also lists legitimate `send __maxbridge_*` boxes in generated/max-bridge.maxpat. This is a known, documented ambiguity left to judgment.

## Human verification required

1. **Max Console paste format.** Paste a real Max 9.2 Console line and check whether the object column is included and how it is separated (tab or `obj: msg`). A tab-separated object column without a colon would only match in the no-prefix tier and would locate boxes only through the fallback.
2. **M4L overlay.** Experimental until a device is confirmed in Live.

---
_Verified: 2026-10-22_
_Verifier: Claude (gsd-verifier)_
