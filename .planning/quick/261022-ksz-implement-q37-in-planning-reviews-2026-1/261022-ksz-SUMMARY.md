---
phase: quick-261022-ksz
plan: 01
status: complete
subsystem: maxpat diagnosis, lifecycle, router
tags: [Q37, diagnose, console, troubleshooting, confirmations, proven-forms, router, jitter, m4l, poly]
requires: [Q17 troubleshooting.md + proven-forms.md, walk.iter_patchers, hooks._auto_commit_saved_file, atomic_io.atomic_write_bytes]
provides:
  - src/maxpat/diagnose.py (diagnose_console, load_troubleshooting, match_line, locate_boxes, CLI)
  - /max-diagnose command
  - testing.record_confirmation, parse_proven_forms, format_proven_form, append_proven_form
  - router Domain Overlays (Jitter, M4L, poly~)
affects: [/max-test, max-lifecycle skill, max-router skill, troubleshooting.md]
tech-stack:
  added: []
  patterns: [read-only CLI over a live-parsed markdown table, AST read-only gate, non-overwriting path-scoped confirmation commits]
key-files:
  created:
    - src/maxpat/diagnose.py
    - tests/test_diagnose.py
    - .claude/commands/max-diagnose.md
  modified:
    - src/maxpat/testing.py
    - tests/test_testing.py
    - .claude/skills/references/troubleshooting.md
    - .claude/commands/max-test.md
    - .claude/skills/max-lifecycle/SKILL.md
    - .claude/skills/max-router/SKILL.md
    - .claude/skills/max-router/references/dispatch-rules.md
    - tests/test_commands.py
    - tests/test_agent_skills.py
    - tests/test_doc_signatures.py
decisions:
  - "/max-diagnose is read-only: src/maxpat/diagnose.py + CLI does parse/match/locate/propose; the command doc does the judgment; fixes only via /max-iterate"
  - "troubleshooting.md tables are the single source of console wordings, parsed live (depth-0 code spans of the first cell)"
  - "Match tiers exact > any-identifier > no-prefix; only the best tier is kept"
  - "Confirmations are per-confirmation files in test-results/, never overwritten, committed path-scoped (Rule #7); proven-forms appends are a separate consented explicit-path commit"
  - "Router domains are overlays on existing agents, not new agents"
metrics:
  duration: ~45 min
  completed: 2026-10-22
actuals:
  tokens: 27900
  tasks: 3
  commits: 4
plan_head_before: 3a60d2017dff5d2ed766dbeffb37a5841475f9c2
plan_head_after: cee6c3ac3f6acbfd77afbde8e95f3900fa3f3eca
---

# Phase quick-261022-ksz Plan 01: Q37 console diagnosis, confirmation lifecycle, router overlays Summary

`/max-diagnose` maps each pasted MAX console line to ranked troubleshooting.md entries (parsed live), locates the offending boxes read-only in `patches/<project>/` and drafts a `/max-iterate` fix. A user confirmation becomes a non-overwriting, path-scoped-committed `test-results/v<version>-<slug>-confirmed.md`, with an optional consented, tier-validated proven-forms.md lesson. The router gains Jitter, M4L and poly~ overlays.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | d2631fcf | feat(maxpat): console diagnosis module + CLI |
| 2 | 7b20e6ac | feat(maxpat): confirmation lifecycle (record_confirmation + proven-forms appender) |
| 3 | 13f47acc | feat(commands): /max-diagnose read-only console diagnosis |
| 3 | cee6c3ac | docs(router): Jitter, M4L and poly~ domain overlays |

No task boundary was handed to a fresh continuation; all three tasks ran in one executor.

## Regression gate

- **Baseline** (Step 0, before any edit): rc 0, 5881 passed, 5 xfailed, 1 xpassed (5887 testcases). No pre-existing failures.
- **Final** (full suite inside Task 3's verify): rc 0, 6008 passed, 5 xfailed, 1 xpassed.
- `junit_diff.py`: `base=5887 new=6014 added=127 offenders=0` (exit 0).
- `git status --porcelain patches patterns` and `git stash list` match Step 0 (both empty). No commit since base-sha touches patches/ or patterns/; every commit used explicit paths.

## Claude's-discretion choices

- **Module + CLI split:** `src/maxpat/diagnose.py` (stdlib + src.maxpat, no I/O at import) does the deterministic part; `.claude/commands/max-diagnose.md` does the judgment (same-wording causes, cascades, phrasing) and routes fixes through `/max-iterate`.
- **Parse contract:** console patterns are code spans in a row's first cell at parenthesis depth 0 (parentheses counted only outside code spans). `<...>` matches one non-space token, `...` any text.
- **Match tiers:** exact (3000) > any-identifier (2000, a quoted literal matches any quoted identifier) > no-prefix (1000, leading `token: ` optional). Score = bonus + literal characters; only the best tier is kept. Lines are normalized (quotes dropped, whitespace collapsed, doubled `X: X: ` collapsed, mirroring `tools/max_bridge._error_key`) and deduplicated with counts. A leading placeholder is anchored at a token start and leading/trailing `...` are dropped from the regex, so matching stays linear on long lines.
- **Locator order:** object hits (`walk.object_name` equals a captured `<objectname>` or the leading token) -> newobj argument tokens if none. In gen mode: codebox hits (identifier as a word, 1-based line numbers) -> gen containers and codeboxes. Skips `test-results/`, `.git`, `node_modules`, `__pycache__` and `__maxbridge_*` copies, and does not follow symlinked directories. Malformed files are listed under `Skipped:`.
- **Confirmation naming/commit:** `v<version>-<slug>-confirmed.md` (`<date>-<slug>-confirmed.md` unversioned), `-2`, `-3` on collision. The commit goes through `hooks._auto_commit_saved_file`, which is path-scoped, warns and never raises.
- **Overlays instead of agents:** a matched overlay sets the lead, adds secondaries, and passes its required reading and checks. No Jitter, M4L or poly~ agent was created.

## troubleshooting.md edits

1. Added a parse-contract sentence to "How to read this table". It names `src/maxpat/diagnose.py`, not the command.
2. Genpatcher row: added the depth-0 companion `` `gen~: failed to compile patcher` ``. Its Source now cites `max-bridge v0.3.0 (2026-10-21)`. No other rows were changed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `_first_sentence` split inside `if ... }`**
- **Found during:** Task 1 (manual CLI run on max-bridge)
- **Issue:** the genpatcher fix was cut at the `...` in `` `else { if ... }` ``, which gave a truncated proposal.
- **Fix:** a sentence now ends only at `.!?` + whitespace + an uppercase letter or backtick, and never after `..`. Regression test `test_first_sentence_keeps_ellipsis`.
- **Commit:** d2631fcf

Other small additions beyond the plan:
- `record_confirmation` accepts a leading `v` on `version`.
- It rejects a multi-line `lesson` or `max_version`.
- `locate_boxes` lists a file that resolves outside the project as `Skipped: <rel> (outside the project)`.

## Doc impact NOT edited (fix-plan rule 8)

- README.md Commands table: no `/max-diagnose` row.
- TECHNICAL.md lifecycle/commands tables: no `/max-diagnose` or confirmation lifecycle.
- CLAUDE.md reference list: could name `/max-diagnose` beside troubleshooting.md.
- shared-capabilities.md troubleshooting pointer: could name `/max-diagnose`.
- max-verify.md `--live` findings: could point to `/max-diagnose`.
- troubleshooting.md header could now name `/max-diagnose`. Task 1 named only the module, because the command did not exist yet.
- `.claude/skills/max-lifecycle/references/test-protocol.md`: "Result Recording" claims incrementing `test-NNN.md` files, but `save_test_results` writes `<test_name>.md` and overwrites it. The file has no Confirmations section.
- `.claude/skills/max-lifecycle/references/project-structure.md`: its `test-001.md` tree line could show `v<version>-<slug>-checklist.md` and `-confirmed.md`.
- Follow-up: `tools/max_verify_live.py` could reuse `src.maxpat.diagnose` instead of its own wording table.

## For the user to confirm in MAX (fix-plan rule 9)

- **Paste format of a Max 9.2 Console copy:** check whether the copied text includes the object column, and how it is separated (tab vs `obj: msg`).
  - The matcher handles `obj: msg`, a doubled prefix and a bare message.
  - A tab-separated object column without a colon would only match in the no-prefix tier.
  - That also means the box would be located only through the fallback.
- **M4L overlay:** it stays experimental until a device is confirmed in Live.

## Notes

- For `osc~: No such object` the six same-wording rows tie, and the proposal uses the first row's fix (RNBO/Gen-only). The `fact:` line (Pure Data name, MAX equivalent cycle~) and the command doc's step 5 steer the choice. Ranking is deliberately not fact-driven in code.
- For `send: bad arguments creating object` on max-bridge, the locator also lists the legitimate `send __maxbridge_*` boxes in generated/max-bridge.maxpat, after the fixture. Telling them apart is left to the command's judgment step.

## Self-Check: PASSED

- FOUND: src/maxpat/diagnose.py, tests/test_diagnose.py, .claude/commands/max-diagnose.md
- FOUND commits: d2631fcf, 7b20e6ac, 13f47acc, cee6c3ac
