---
phase: quick-261016-jbx
plan: 01
subsystem: db-tooling
status: complete
tags: [object-db, sync, audit, extractor, atomic-io, Q30, I4, I5, I6]
requires: []
provides:
  - src/maxpat/atomic_io.py (atomic_write_bytes, atomic_write_many, json_style)
  - sync objectfile_aliases report section + --apply aliases (Q38 input)
  - extractor --force guard + merged extraction log
  - merge-time conflict detection + style-preserving overrides writer
affects: [tools/sync_max_bundle.py, tools/audit_db.py, .claude/scripts/extract_objects.py, .claude/scripts/validate_db.py, src/maxpat/audit/*]
tech-stack:
  added: []
  patterns: [temp-file + fsync + chmod + os.replace, prepare-all-then-replace-all transaction with rollback, json_style reproduction]
key-files:
  created: [src/maxpat/atomic_io.py, tests/test_db_tooling.py]
  modified: [tools/sync_max_bundle.py, tools/audit_db.py, .claude/scripts/extract_objects.py, .claude/scripts/validate_db.py, src/maxpat/audit/merger.py, src/maxpat/audit/analyzer.py, src/maxpat/audit/overrides.py, src/maxpat/audit/cli.py, tests/test_sync_max_bundle.py, tests/test_version_tags.py]
decisions:
  - "PD-3: min_version written as strings; DB checks accept number or string until Q38"
  - "PD-5: one all-or-nothing write covers object files plus package_info.json"
  - "PD-6: every init/*.txt read (719 lines); basis rules mc_wrapper/abstraction/class/file; RNBO-shadowed list.* report-only"
  - "PD-7: extractor applies only the whitespace doc-page rule; log merged in every mode"
  - "PD-8: removed-manual conflicts land; new keys at end of domain group; stale guard"
  - "PD-9: 1-2 unanimous instances are MEDIUM; variable_io rules are proposals only"
metrics:
  duration: "~65 min"
  completed: 2026-10-16
actuals:
  tokens: 39750
  tasks: 3
  commits: 3
plan_head_before: 981b7b807d68c69b0a62ff3b3c8b81e92d3115d3
plan_head_after: 5dbee5cb
---

# Phase quick-261016-jbx Plan 01: Q30 safe DB tooling Summary

The object-DB tools can no longer silently damage the curated DB. Sync writes are atomic, keep file modes and are all-or-nothing. The extractor refuses to overwrite core files and merges the log. The audit merger never clobbers a manual override and keeps overrides.json byte-stable. The DB can now see the 311 `max objectfile` names Max instantiates (I4, I5, I6).

## Commits

| Task | Commit | Subject |
|------|--------|---------|
| 1 | 39265cc0 | fix(sync): mode-preserving atomic writes, transactional multi-file applies, string versions, define regex drops the trailing ';' (Q30) |
| 2 | 9389d383 | feat(db-tools): objectfile alias report and --apply aliases; audit_db reads objectfile lines; extract_objects refuses core overwrites, merges the log, skips doc pages (Q30) |
| 3 | 5dbee5cb | fix(audit): merge-time conflicts and an atomic, style-preserving overrides writer; HIGH needs 3 instances; variable_io rule proposals (Q30) |

The 3 commits touch exactly the 12 files_modified paths (Q/q30-commit-files.txt). Nothing under `patches/` or `.claude/max-objects/` changed.

## Test gates

| File | Last line |
|------|-----------|
| baseline-pytest.txt | 2 failed, 5115 passed, 5 xfailed, 1 xpassed, 39 warnings in 106.09s |
| pytest-t1.txt | 2 failed, 5154 passed, 5 xfailed, 1 xpassed, 39 warnings in 97.16s |
| pytest-t2.txt | 2 failed, 5173 passed, 5 xfailed, 1 xpassed, 39 warnings in 107.68s |
| final-pytest.txt | 2 failed, 5228 passed, 5 xfailed, 1 xpassed, 33 warnings in 103.54s |

Every gate failed only on the 2 pre-existing baseline failures, both out of scope (follow-up for the user):
- `tests/test_doc_signatures.py::test_readme_patch_table_lists_every_project`: the README patch table lacks q29-check.
- `tests/test_uninitialized_state.py::TestCommittedCorpus::test_committed_q24_findings_match_allowlist[patches/q29-check/generated/q29-check.maxpat]`: obj-32 is not allowlisted.

DB state: `Q/db-state-now.txt` matches `Q/db-state-before.txt` (51 files, sha256 and mode) after every task. `git diff --stat -- .claude/max-objects/` is empty and the stash list is unchanged. Python 3.10 compatibility was checked with `ast.parse(feature_version=(3, 10))`; only 3.14 is installed locally.

## Red evidence

- **red-t1.txt:** 33 failed, 110 passed.
  - Failing: every TestI6Tracer / AtomicMode / TransactionalApply / DefineRegex / StringVersions / VersionTuple case, plus the 5 PD-10-edited sync tests.
  - Green guards that passed at HEAD by design: `test_package_object_and_its_count_land_in_one_run` and the real-bundle define check `test_real_bundle_defines_have_no_semicolon_in_alias_or_target`. tests/test_version_tags.py was widened, so it passed both before and after.
- **red-t2.txt:** 17 failed, 2 errors. The errors are the real-bundle section fixture, a KeyError on the missing section. Nothing passed at HEAD: `test_sync_doc_page_rule_is_unchanged` also needs the new `is_doc_page_name`, but its `_is_doc_page` assertions keep HEAD's behavior.
- **red-t3.txt:** 52 failed, 3 passed. The green guards were:
  - `test_a_new_domain_group_lands_in_domain_order`;
  - `test_one_args_key_with_two_count_pairs_is_todays_finding`;
  - `test_all_equal_counts_are_todays_finding`.
  - Note: the plan listed `test_merge_rereads_the_live_file` as a green guard, but it is red at HEAD, because HEAD never re-reads.

## Existing-test edits (PD-10 only)

- tests/test_sync_max_bundle.py:
  - lines 519, 1025 and 1160 now expect `"9.7"`;
  - line 1120 now expects `"8"`;
  - the float test was renamed `test_min_version_flag_keeps_a_point_release_as_a_string` and asserts "9.1", "9" and "9.10".
- tests/test_version_tags.py: the five tests go through a local `_version_tuple` and accept a number or a version string. array./string. require major 9 with no minor or minor 0, abl. requires major 9, mc requires any valid version.

No other existing test was edited.

## Measured on the real bundle (Max 9.2.0, read-only)

- **objectfile:** 719 lines in 12 files, 716 names, 3 duplicates (`!=~`, `mcs.sfizz~`, `mc.sfizz~`), 405 resolved, 311 unresolved.
  - By basis: abstraction 90, class 6, file 134, mc_wrapper 14, none 67.
  - 30 names are RNBO-shadowed (list.* -> zl.*).
  - Help evidence exists for 9 candidates: 8 disagree, all file basis (jit.mo.line/perlin/saw/tri -> jit.mo.func, jit.time.line -> jit.mo.time, mc.input -> mc.target, xbendin2 -> xbendin, xbendout2 -> xbendout); 1 agrees (list.iter -> zl.iter).
- **audit_db:**
  - `absent from Max : 2 DB names with no refpage (+4 define-mapped aliases, +14 objectfile-mapped aliases, ...)`. The 2 are M4L.api.ObserveTransport and M4L.api.ToggleTransport (was 16).
  - `missing from DB : 8 ... ; 311 objectfile aliases unresolved`.

## Behavior changes

- `extract_objects.py` needs `--force` to replace an existing core domain file (max, msp, jitter, mc, gen, m4l, rnbo). Without it, it exits 2, writes nothing and points to `tools/sync_max_bundle.py`. `main(argv)` returns exit codes (0 / 1 / 2).
- Every extractor run (`--package`, `--domain`, `--force`) merges `extraction-log.json`: the old keys and history are kept, the superseded state is appended, and the run is recorded under `last_extraction`.
- Whitespace-named documentation pages are never extracted. The 9 no-I/O objects (jbox, onecopy, ...) still are.
- Sync `--apply` writes keep file modes; a new file gets the umask default. new / define / deltas / inherited are all-or-nothing, and a failed replace is rolled back.
- New `min_version` values are strings ("9.2", "9.10"). The installed version string is now kept correctly (9.10 stays "9.10", not 9.1), and `--min-version` returns strings.
- Argument-less `max define A B;` lines parse to target `B`.
- The sync report has an `objectfile_aliases` section and an `objectfile` summary line. audit_db adds `objectfile_mapped` to absent_from_bundle and `objectfile_aliases` to missing_from_db, still with 7 sections.
- `--apply aliases --names ...` exists. It writes only `aliases.json`, additively and in the file's own style and mode, then checks that the DB reloads (rolled back with exit 2 if not). It exits 1 if a name was aborted.
- The audit merger:
  - recomputes conflicts at merge time;
  - keeps the file's key order and style;
  - places new names at the end of their domain group;
  - `write()` returns False on a no-op;
  - raises `OverridesChangedError` if the file changed since `merge()`.
- `--merge --overrides PATH` targets a copy.
- Audit confidence: HIGH needs 3 or more instances. I/O findings carry `counts_follow_arguments` and `proposed_variable_io`. Argument-dependent counts become `proposed["variable_io_rules"]` entries, never default counts.

## Deviations from Plan

### Auto-fixed / executor choices

1. **[Rule 2 - Correctness] Extractor refuses an unreadable extraction log.** `ExtractionLogUnreadable` makes the extractor exit 2 before writing anything if the existing extraction-log.json is not a JSON object. Merging into it would otherwise wipe its history. (9389d383)
2. **help_inlets / help_outlets are computed per side.** When counts follow the arguments, each side takes the argument-less count only where that side differs from the DB default. A whole-pair rule would propose an unchanged side. (5dbee5cb)
3. **`OverrideMerger.pending_variable_io_rules()`** was added so the CLI does not read the private `_proposed`. (5dbee5cb)
4. **`objectfile_aliases.names` is a count** (716), matching `lines`. The unresolved names are in `names_unresolved`.

No architectural change, no package install, no auth gate.

## Decisions to confirm

- **PD-3 (string versions):** new `min_version` values are written as strings, and validate_db / test_version_tags accept a number or a version string until Q38 migrates the DB. Alternative: keep writing numbers until Q38.
- **PD-5 (transaction scope):** one all-or-nothing write covers the object files and the package_info.json count update.
- **PD-6 (objectfile scope):**
  - every `init/*.txt` and `packages/*/init/*.txt` file is read: 719 lines, not the review's 647 (60 extra MC wrapper lines come from other init files);
  - the candidate basis rules are mc_wrapper -> abstraction -> class -> file;
  - the 30 RNBO-shadowed list.* names are report-only and never aliased by Q30.
- **PD-7 (extractor):** the extractor applies only the sync tool's whitespace doc-page rule, because the no-I/O rule would drop 9 real objects. The log is merged in every mode, `--force` included.
- **PD-8 (merger):**
  - a proposal-file conflict whose manual entry was removed after the audit now lands as an ordinary proposal;
  - new keys go at the end of their domain group;
  - the stale guard refuses a write when the file changed since `merge()`.
- **PD-9 (confidence and rules):** 1-2 unanimous instances are MEDIUM, which is still eligible for a proposal. variable_io rules are proposals only and are never merged.

Please accept each one or reopen it:
- A) Accept all six.
- B) Accept all except PD-3: keep numeric min_version until Q38 migrates the DB.
- C) Accept all except PD-9: make 1-2 instance findings LOW, so they are not proposed.
- D) Reopen a specific PD (name it).

## Follow-ups (PD-11, out of scope)

- **chmod the real DB files left at 0600 by earlier syncs.** They are in the main checkout, not this worktree. The list comes from `find .claude/max-objects -maxdepth 3 -name "*.json" -perm 600 -not -path "*/_pkg-source/*"`:
  `chmod 644 .claude/max-objects/package_info.json .claude/max-objects/{max,msp,jitter,mc,m4l}/objects.json ".claude/max-objects/packages/ableton-dsp/objects.json" ".claude/max-objects/packages/Jitter Geometry/objects.json" ".claude/max-objects/packages/jit.mo/objects.json" ".claude/max-objects/packages/Jitter Tools/objects.json"`
- **Q38 inputs:**
  - Each `objectfile_aliases.entries[]` carries name, file, class, args, package, mapping_file, line, candidate, basis, candidate_domain, candidate_io, help_stem, help_io and help_io_agrees. `domain_shadowed[]` adds `domain`.
  - The 30 `domain_shadowed` list.* names need a lookup-context decision: they resolve only to RNBO entries today, so `--apply aliases` skips them.
  - The 8 help-disagreeing file-basis candidates are listed above.
- **Q38's DB-wide min_version migration.** The DB holds 3,050 int 8, 215 float 8.1, 167 int 9, 12 float 9.2 and 1 int 4.
- The 2 q29-check baseline failures (README patch table; Q24 allowlist for obj-32).
- tools/extract_pkg_io.py fallbacks, and reading `max define` lines outside objectmappings files: not touched.

## Doc impact (not edited, rule 8)

- `.claude/skills/references/db-maintenance.md` "After a Max update" should cover:
  - `--apply aliases` and the objectfile_aliases section;
  - the extractor's `--force` and log merge;
  - string min_version.
- max-9.2-changes.md line 184 and shared-capabilities.md line 13.
- TECHNICAL.md lines 122 and 133 show min_version as an int.

## MAX confirmation (rule 9)

None needed. This task changes DB tooling only: it writes no patch and changes no DB data.

## Known Stubs

None.

## Threat Flags

None. No surface beyond the plan's threat model: the new aliases.json writer is T-jbx-06, which is mitigated and tested.

## Self-Check: PASSED

- FOUND: src/maxpat/atomic_io.py, tests/test_db_tooling.py
- FOUND commits: 39265cc0, 9389d383, 5dbee5cb
- Q30 commit files are within files_modified (12/12); DB state unchanged; stash list unchanged.
