---
phase: quick-261016-jbx
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/maxpat/atomic_io.py
  - tools/sync_max_bundle.py
  - tools/audit_db.py
  - .claude/scripts/extract_objects.py
  - .claude/scripts/validate_db.py
  - src/maxpat/audit/merger.py
  - src/maxpat/audit/analyzer.py
  - src/maxpat/audit/overrides.py
  - src/maxpat/audit/cli.py
  - tests/test_db_tooling.py
  - tests/test_sync_max_bundle.py
  - tests/test_version_tags.py
autonomous: true
requirements: [I4, I5, I6]

estimate:
  tokens: 195000
  raw_tokens: 195000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "Operator sees DB file permissions kept: after a sync `--apply` (tracer: `--apply new --names newthing` on the hermetic fake bundle), a `max/objects.json` that was 0o644 is still 0o644 (HEAD leaves 0o600), and a log or groups file the tool creates gets the umask default. The new entry's min_version reads \"9.7\", a string (HEAD: float 9.7). Evidence: every sync writer goes through atomic_io.atomic_write_bytes."
    - "Operator sees a failed sync apply leave the DB untouched: if any file in a multi-file `--apply` fails a check, the run exits 2 and no file changes (HEAD writes max/objects.json first, then fails); if a replace fails midway, the files already replaced are restored, bytes and mode. `--min-version 9.10` lands \"9.10\" (HEAD stores 9.1), and an argument-less `max define bare.def corething;` line maps bare.def to corething, not \"corething;\" (the 104 real-bundle defines parse unchanged)."
    - "Operator sees, in the sync dry-run report, every `max objectfile` alias Max knows but the DB cannot resolve, each with a proposed target, how it was derived and help-box evidence: on Max 9.2.0, 719 lines and 311 unresolved names (the review counted 647 / 251 in the objectmappings files; the other 60 are MC wrappers in other init files), e.g. mc.times~ -> mc.*~, hslider -> slider, list.iter -> zl.iter, 4mixr -> vz.4mixr; the 30 list.* names that resolve only to RNBO entries are listed apart with zl.* targets. `--apply aliases --names X` adds X to aliases.json only when X is unresolved, its target resolves and any help boxes agree; aliases.json keeps its order, style and mode, and if the DB then fails to load the change is rolled back (exit 2)."
    - "Operator running tools/audit_db.py no longer sees objectfile aliases counted as absent from Max: on 9.2 the 'absent from Max' line drops from 16 to 2 names (M4L.api.ObserveTransport, M4L.api.ToggleTransport) and shows the objectfile-mapped count separately; the 'missing from DB' line adds how many objectfile aliases are unresolved. The JSON still has exactly 7 sections."
    - "Operator running extract_objects.py over an existing DB without --force gets an error naming tools/sync_max_bundle.py, exit 2, and no change (a scratch copy of the real DB run against the 9.2 bundle stays byte-identical; HEAD drops 25 curated entries and adds 6 documentation pages). After any extractor run (--package, --domain packages, --force), extraction-log.json still holds its sync record, Max version and history, with the previous state appended and the run under last_extraction (HEAD: --package wipes it to total_objects 1). The 6 whitespace-named documentation pages are never extracted; the 9 objects whose refpages lack I/O lists (jbox, onecopy, project, jit.graph, jit.plot, jit.mo.fieldmask, jit.mo.join, mira.motion, mira.multitouch) still are."
    - "Operator merging an audit never loses an expert override: a manual entry added to overrides.json after the audit ran survives --merge and is reported as a conflict (HEAD overwrites it); an edit made between merge and write makes the write refuse (OverridesChangedError) rather than clobber it. A merge that changes nothing leaves overrides.json byte-identical (HEAD: 782 keys moved, a 28,966-line diff); a merge that only adds proposals only adds lines (new names at the end of their domain group); every write keeps the file mode. `--merge --overrides PATH` targets a copy."
    - "Operator reading proposed-overrides.json no longer sees overstated or argument-specific proposals: a finding backed by 1-2 help instances is MEDIUM, never HIGH (HIGH needs 3 or more); when help-box counts change with the arguments (bucket 4 -> 4 outlets) the proposal is a variable_io rule under variable_io_rules (e.g. outlet_count first_arg), never a default I/O override with the argument-specific count, and the merger never applies those rules."
    - "Nothing under .claude/max-objects/ changes: git diff and git status are empty, every tracked DB file's sha256 and mode match Q/db-state-before.txt, and no --apply runs against the real bundle or DB. After every task the full suite shows no failure beyond the 2 pre-existing q29-check failures and more passing tests than the baseline (5115 passed, 5 xfailed, 1 xpassed, 2 failed at 981b7b80). At least 3 `(Q30)` commits touch only files_modified paths; the stash list is unchanged."
  artifacts:
    - path: "src/maxpat/atomic_io.py"
      provides: "atomic_write_bytes (mode-preserving), atomic_write_many (all-or-nothing), json_style (reproduce ensure_ascii / trailing newline)"
      contains: "def atomic_write_many"
    - path: "tools/sync_max_bundle.py"
      provides: "write_db_files transaction; string versions; fixed define regex; parse_objectfile_mappings; objectfile_aliases section; --apply aliases; is_doc_page_name; restate_extraction_log"
      contains: "def parse_objectfile_mappings"
    - path: "tools/audit_db.py"
      provides: "objectfile-mapped names in absent_from_bundle; unresolved objectfile aliases in missing_from_db"
      contains: "objectfile_mapped"
    - path: ".claude/scripts/extract_objects.py"
      provides: "--force guard, merged extraction log, doc-page filter, main(argv)"
      contains: "class CoreOverwriteRefused"
    - path: "src/maxpat/audit/merger.py"
      provides: "merge-time conflicts, order-preserving merge, atomic style-preserving write, stale guard"
      contains: "class OverridesChangedError"
    - path: "src/maxpat/audit/analyzer.py"
      provides: "MIN_HIGH_INSTANCES; counts_follow_arguments + proposed_variable_io"
      contains: "MIN_HIGH_INSTANCES"
    - path: "tests/test_db_tooling.py"
      provides: "red-first regression tests for I4, I5 and I6, all on tmp_path scratch data"
      contains: "class TestI6TracerApplyKeepsModeAndStringVersion"
  key_links:
    - from: "tools/sync_max_bundle.py (apply_objects / apply_deltas / apply_inherited)"
      to: "src/maxpat/atomic_io.py (atomic_write_many)"
      via: "write_db_files prepares every payload first, then replaces all files or none"
      pattern: "atomic_write_many\\("
    - from: "src/maxpat/audit/merger.py (write)"
      to: "src/maxpat/atomic_io.py (atomic_write_bytes, json_style)"
      via: "the file's own style is reproduced and the replace keeps its mode"
      pattern: "json_style\\("
    - from: ".claude/scripts/extract_objects.py (extract_all / write_output)"
      to: "tools/sync_max_bundle.py (is_doc_page_name, restate_extraction_log, write_extraction_log)"
      via: "lazy _sync_tool() import; one doc-page rule and one log writer for both tools"
      pattern: "restate_extraction_log\\("
    - from: "tools/audit_db.py (build_refpage_index)"
      to: "tools/sync_max_bundle.py (parse_objectfile_mappings)"
      via: "both tools read the same objectfile lines"
      pattern: "parse_objectfile_mappings\\("
    - from: "src/maxpat/audit/overrides.py (OverrideGenerator)"
      to: "src/maxpat/audit/analyzer.py (analyze_io_counts)"
      via: "proposed_variable_io becomes a variable_io_rules proposal, never a default count"
      pattern: "proposed_variable_io"
---

<objective>
This plan implements fix-plan Q30 (review findings I4, I5 and I6): safe DB tooling.
- **I4, `.claude/scripts/extract_objects.py`.** Refuse to overwrite core domain files without `--force` and point to `tools/sync_max_bundle.py`; merge every run into `extraction-log.json` (history appended) instead of wiping it; skip documentation pages with the sync tool's doc-page rule.
- **I5, audit merger and analyzer.** Recompute conflicts at merge time; write overrides.json atomically in its own formatting (no key re-sort, no trailing-newline churn); HIGH confidence needs 3 or more instances; propose `variable_io` rules when counts follow the arguments.
- **I6, `tools/sync_max_bundle.py` and `tools/audit_db.py`.** The define regex strips the trailing `;`; versions are strings; atomic writes keep the file mode; multi-file applies are transactional; both tools read the bundle's `objectfile` alias lines and report unresolved aliases; `--apply aliases --names …` lands named aliases. The report is the input Q38 consumes.
- **Tests.** One regression class per finding, written red first, all on scratch copies.

Purpose: each of these tools can silently damage the curated object DB today (wiped log, 25 dropped entries, clobbered overrides, 0600 files, half-written applies), and 311 names Max instantiates are invisible to it.

Output:
- src/maxpat/atomic_io.py (new) and tests/test_db_tooling.py (new);
- the fixes in the sync tool, audit_db, the extractor, validate_db and the audit package;
- the PD-10 existing-test edits;
- three `(Q30)` commits, each behind its own full-suite gate.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@CLAUDE.md
@.planning/reviews/2026-10-11-fix-plan.md
@.claude/skills/references/db-maintenance.md

Read only the named parts. Line numbers are as of 981b7b80.
- `.planning/reviews/2026-10-11-repo-review.md`: rows I4, I5 and I6 (lines 164-166); C2 (line 84) and C11 (line 93) for the analyzer and list.* background; §5.5 (lines 395-403) for what Q38 will do with the alias report.
- `.planning/reviews/2026-10-11-fix-plan.md`: the Q30 section (lines 532-549) and Q38 (lines 657-671).
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

Rule 4 at 981b7b80: the suite is NOT fully green before this task. Measured at planning: **2 failed, 5115 passed, 5 xfailed, 1 xpassed** (~102 s). Both failures come from the user's `patches/q29-check` project committed after Q29, not from DB tooling:
- `tests/test_doc_signatures.py::test_readme_patch_table_lists_every_project` (README patch table lacks q29-check);
- `tests/test_uninitialized_state.py::TestCommittedCorpus::test_committed_q24_findings_match_allowlist[patches/q29-check/generated/q29-check.maxpat]` (obj-32 not allowlisted).

They are out of scope (rule 7): do not fix them. The gate for this plan is "no failure outside the baseline set, and more passed tests than the baseline". SUMMARY lists both as a follow-up.

Q30 does not tell this plan to edit CLAUDE.md, skills or TECHNICAL.md, so none is edited (rule 8). Module docstrings of the edited code are updated.

Additions for this execution environment:
- **Q** = `.planning/quick/261016-jbx-implement-q30-in-planning-reviews-2026-1`. These files go in Q and stay untracked, never staged: base-sha.txt, stash-list-before.txt, baseline-pytest.txt, db-state-before.txt, db-state-now.txt, red-t1.txt, red-t2.txt, red-t3.txt, pytest-t1.txt, pytest-t2.txt, final-pytest.txt, q30-commit-files.txt. The orchestrator commits PLAN and SUMMARY. Never name a scratch script after a stdlib module.
- **Execution.** The plan may run in the main working tree or in an isolated git worktree; every path here is repo-root-relative and every command assumes cwd at the checkout root. At planning, HEAD = origin/main = `981b7b80` and the tracked tree is clean.
  - **Hard precondition:** `git merge-base --is-ancestor 981b7b80 HEAD` succeeds. If it fails, HALT and report it.
  - **Hard precondition (fresh start only, Q/base-sha.txt absent):** `git diff --quiet HEAD -- tools/sync_max_bundle.py tools/audit_db.py .claude/scripts/extract_objects.py .claude/scripts/validate_db.py src/maxpat/audit tests/test_sync_max_bundle.py tests/test_version_tags.py` succeeds, and neither `src/maxpat/atomic_io.py` nor `tests/test_db_tooling.py` exists. If either fails, HALT and report which.
- **Step 0 (Task 1, before any source edit):**
  - Write `git rev-parse HEAD` to Q/base-sha.txt and `git stash list` to Q/stash-list-before.txt.
  - Record the DB state: for every path in `git ls-files .claude/max-objects`, one line `<sha256> <oct mode> <path>`. Use the exact `python3 -c` db-state command from Task 1's verify, redirected to Q/db-state-before.txt instead of Q/db-state-now.txt (51 lines at planning).
  - Run `python3 -m pytest -q -p no:cacheprovider` into Q/baseline-pytest.txt. Expected: the Rule 4 figures above. If it differs, record it; do not fix it.
- **DB safety (hard).**
  - Never write, chmod, touch or create anything under `.claude/max-objects/`.
  - Never run the sync tool's `--apply` (any mode) or `--refresh-log` with the real bundle or the real DB; every apply test uses the hermetic fake bundle and a fake or scratch DB.
  - Never run `extract_objects.py` or the audit `--merge` with the real DB as output or target. Against the real bundle the extractor runs only in memory (`extract_all`) or into a scratch copy without `--force`, where it must refuse.
  - Read-only reports of the real bundle against the real DB (`run_report`, `run_audit`, `parse_*_mappings`) are allowed; they write nothing.
  - Tests write only under `tmp_path`. Real DB data is used only as a read-only source for scratch copies.
  - A scratch copy of the real DB copies exactly: the top-level `*.json` files of `.claude/max-objects/`, `<domain>/objects.json` for max, msp, jitter, mc, gen, m4l and rnbo, and `packages/*/objects.json`. Never copy or walk `.claude/max-objects/_pkg-source/` (7.7 GB, untracked) or `audit/`.
  - tests/test_db_tooling.py has a module-scoped autouse guard that snapshots sha256 and mode of those same real files (explicit list, no recursive walk) before the module and asserts them unchanged after it.
- **Edit scope.**
  - Only the 12 files_modified paths may change, each only in a task whose `<files>` lists it. Never edit `patches/**`, README.md, any other `tools/`, `.claude/` or `src/` file.
  - The only edits allowed to existing test files are those in PD-10. Any other existing test that fails is a code bug: fix the code, never the test. If such a test pins an old behavior Q30 explicitly replaces, stop and report it (rule 7).
- **Commits.** One commit per task, at least 3 in total, each message ending `(Q30)`.
  - **Gate:** commit a task only after a full-suite run recorded in Q/pytest-t1.txt, Q/pytest-t2.txt or Q/final-pytest.txt shows no FAILED/ERROR line outside Q/baseline-pytest.txt's set and more passed tests than the baseline. Never commit a red task.
  - Stage with `git add -- <task files>` and commit with `git commit -m "..." -- <task files>`. Never `git push`; never rewrite history.
  - A follow-up fix that lands as its own `(Q30)` commit touching only these paths is kept and explained in SUMMARY.
- **Context budget (one plan, three self-contained units).** The quick-task form allows a single plan, so the budget is enforced per task. ~195k in total (low confidence; calibration factor 1, 0 samples), per task: Task 1 ~60k, Task 2 ~75k, Task 3 ~50k plus SUMMARY ~10k.
  - Each task is a complete unit: its own red file, gate file and `(Q30)` commit, and its own `<read_first>` list. Read only that list; read the 2,686-line sync tool and the 1,327-line extractor by offset ranges, never whole.
  - **Stop rule:** after a task's commit, if the executor's own context is past ~50%, it stops there and reports the last committed task, so a fresh executor resumes at the next task (Resume points). Never start a task it cannot finish.
- **Resume points.** Every task boundary is a committed state behind its gate. A fresh executor counts the `(Q30)` commits since Q/base-sha.txt and starts at the first task without one; it skips Step 0 when Q/base-sha.txt, Q/db-state-before.txt and Q/baseline-pytest.txt exist; uncommitted edits in the resumed task's `<files>` belong to that task (rerun its red step only if its Q/red-tN.txt is missing). The merge-base precondition always applies.
</rules>

<planner_decisions>
The fix plan names the outcomes. These are the planner's resolutions of what it leaves open (Claude's discretion), each measured at 981b7b80 with real data read-only and `git diff -- .claude/max-objects` empty after every probe. SUMMARY lists PD-3, PD-5, PD-6, PD-7, PD-8 and PD-9 for the user to confirm.

**PD-1. Shared atomic I/O: `src/maxpat/atomic_io.py` (new, stdlib only, imports nothing from src.maxpat).** The merger (src) and the sync tool (tools) both need it, and src must not import tools.
- `atomic_write_bytes(path, payload: bytes) -> None`: a temp file in the target's own directory (`tempfile.mkstemp`), write, flush, `os.fsync`, then `os.chmod(tmp, mode)` where mode is `stat.S_IMODE` of the existing target, or `0o666 & ~umask` for a new file (umask read with an `os.umask` round-trip), then `os.replace`. On any exception the temp file is removed and the target is untouched.
- `atomic_write_many(items: Sequence[tuple[path, bytes]]) -> None`: all or nothing. Phase 1 writes every temp file (each with its own target's mode) before any replace. Phase 2 replaces in order, remembering each original's bytes and mode (or that it was absent). If any replace fails, every already-replaced target is restored (original bytes and mode, or unlinked if it was absent), the remaining temps are removed, and the exception re-raises.
- `json_style(raw: bytes, data) -> tuple[bool, bool] | None`: the (ensure_ascii, trailing_newline) pair for which `json.dumps(data, indent=2, ensure_ascii=…) + ("\n" if …)` encodes to exactly `raw`, trying ensure_ascii False first (UTF-8 preferred when both reproduce), else None.
- The sync tool's `detect_style` delegates to `json_style` and still raises StyleUnreproducible on None.

**PD-2. Define regex (I6).** `_DEFINE_RE` becomes `^\s*max\s+define\s+([^\s;]+)\s+([^\s;]+)\s*(.*?)\s*;?\s*$` (alias and target can no longer swallow `;`). Prototyped: the 104 real-bundle defines parse identically to HEAD (none is argument-less today), `max define bare.def target.obj;` gives ("bare.def", "target.obj", ""), and `max definesubstitution …` still does not match.

**PD-3. String versions (I6).**
- `_major_minor(short_version) -> str | None`: "9.2.0" -> "9.2", "9.10.0" -> "9.10" (each part through int(), so "09" -> "9"; ".0" minors are kept: "9.0.0" -> "9.0").
- `parse_min_version(text) -> str`: same accepted syntax (`\d+(\.\d+)?`) and range (4 <= major < 10, now tested on the major part); returns the canonical string ("8", "9.1", "9.10").
- `index["version"]`, every written `min_version` (build_refpage_entry C5, build_define_entry, `--min-version`) and the `min_version` notes are strings.
- Consequence handled here: the real DB stores numbers (3,050 int 8, 215 float 8.1, 167 int 9, 12 float 9.2, 1 int 4), and two checks require numbers. A future real `--apply new|define` would make them fail. So tests/test_version_tags.py (all five tests) and `.claude/scripts/validate_db.py` (check_min_version_range, check_max9_objects) accept a number OR a version string, compared through a `_version_tuple` helper (number -> its parts, e.g. 8.1 -> (8, 1), 9 -> (9,); "9.10" -> (9, 10); anything else, booleans included, -> None, which fails). No real DB value changes; Q38 migrates them to strings.

**PD-4. Mode-preserving atomic writes (I6).** write_db_file, write_groups_file, write_extraction_log and the new aliases writer replace their own mkstemp/os.replace blocks with `atomic_write_bytes`. The real DB already holds 10 files at 0600 from earlier syncs (max, msp, jitter, mc, m4l `objects.json`, 4 package files and package_info.json); this task never touches them, and SUMMARY gives the user the chmod.

**PD-5. Transactional apply (I6).**
- `prepare_db_file(path, new_data, db_root) -> bytes | None` holds every check of today's write_db_file (allow-list, style, additive, sorted-or-appended key order) and returns the payload, or None when it would be byte-identical. `write_db_file` = prepare + atomic_write_bytes, same signature and return value.
- `write_db_files(items: list[tuple[path, data]], db_root) -> list[str]`: prepares every item first (any WriteRefused / StyleUnreproducible / AdditiveViolation raises before anything is written), then one `atomic_write_many`; returns the DB-relative paths written.
- apply_objects stages every destination file and the package_info.json count update in one write_db_files call; the counts come from the staged data, not from re-reading disk (update_package_counts becomes a staging helper). apply_deltas and apply_inherited also write through one write_db_files call. main catches OSError from the apply block with the other write errors and exits 2.

**PD-6. objectfile aliases (I6).**
- `parse_objectfile_mappings(c74) -> dict` reads every `init/*.txt` and `packages/*/init/*.txt` (Max runs every init file; the define parser keeps its `*objectmappings*.txt` glob). Line regex `^\s*max\s+objectfile\s+([^\s;]+)\s+([^\s;]+)\s*(.*?)\s*;?\s*$`. Returns `{"records": {name: {name, file, class, args, package, mapping_file, line}}, "lines": int, "files": [paths], "duplicates": [names]}`; class is the first token after the file (or None), args the rest; package is the `packages/<P>` owner or None; the first line for a name wins, later ones go to duplicates.
- Candidate alias target, by line shape (the first rule for the shape that yields a name the DB resolves; `canonical(X)` = the DB name lookup() gives X, else the DB name of the first objectfile alias, in name order, whose file is X and which resolves):
  - file `mc.wrapper~` -> basis `mc_wrapper`: "mc." + canonical(class) (`mc.times~ mc.wrapper~ times~` -> `*~` via `max objectfile *~ times~;` -> `mc.*~`); no fallback to the mono class;
  - file ending `.maxpat` or `.js` -> basis `abstraction`: the file stem (`4mixr vz.4mixr.maxpat` -> `vz.4mixr`);
  - otherwise basis `class`: canonical(class) when it differs from the alias, else basis `file`: canonical(file);
  - else candidate None, basis None.
- Help evidence: `find_help_boxes(index, name, (candidate,))`; `help_io` = the boxes' (numinlets, numoutlets); `help_io_agrees` = every box equals `compute_io_counts(candidate, box args)` (True), any box differs (False), no box (None).
- Report section `objectfile_aliases`, inserted in SECTION_KEYS right after `define_missing` (ui_maxclasses stays last, inherited_attributes -> groups stays adjacent): available, files, lines, names, duplicates, resolved, unresolved_count, names_unresolved (sorted), by_basis, domain_shadowed (objectfile names whose lookup() entry has domain RNBO or Gen, with candidate and evidence), entries (one per unresolved name, in name order: name, file, class, args, package, mapping_file, line, candidate, basis, candidate_domain, candidate_io, help_stem, help_io, help_io_agrees). format_summary gains one `objectfile` line.
- `--apply aliases --names …` (APPLY_MODES gains "aliases"; --names is mandatory, exit 2 without it). Per name: lookup() resolves it (any domain, the 30 RNBO-shadowed list.* included) -> skipped; no objectfile line -> aborted; no candidate -> aborted; help_io_agrees False -> aborted; else written as `aliases[name] = candidate`. Written through `write_aliases_file(db_root, additions) -> bool`: only `<db_root>/aliases.json`; every existing top-level key and alias unchanged (AdditiveViolation otherwise); existing aliases keep their order, new ones are appended in name order; style via json_style; atomic and mode-preserving. Then ObjectDatabase(db_root) must load and lookup(name)["name"] must equal the candidate for each written alias; otherwise the original bytes are restored and the run exits 2. Exit 1 if any named alias aborted. write_db_file keeps refusing aliases.json (existing test).
- audit_db: build_refpage_index stores the parse under `objectfiles` (left out of the emitted refpage_index header, like defines). audit_absent_from_bundle lists DB names with no refpage that are objectfile aliases (and not define aliases) under `objectfile_mapped` [{name, file, class}] plus `objectfile_mapped_count`, excluded from count. audit_missing_from_db gains `objectfile_aliases` {lines, names, unresolved_count, unresolved}, not added to count. Summary lines: the absent line adds `+N objectfile-mapped aliases` (keeping `+N define-mapped`); the missing line adds `; N objectfile aliases unresolved`. No new audit section: tests/test_audit_db.py pins exactly 7.
- Measured at planning (9.2.0, real DB, read-only): 719 lines (647 in the 9 objectmappings files + live.guilib-init.txt 12, abl-dsp-mc.txt 59, mc-mappings.txt 1), 716 names, 3 duplicates (`!=~`, `mcs.sfizz~`, `mc.sfizz~`), 311 unresolved: mc_wrapper 14, abstraction 90, class 6, file 134, none 67. 30 list.* names resolve only to RNBO entries (candidates zl.* by class). Help evidence exists for 9 candidates: 8 disagree (all basis file, e.g. mc.input -> mc.target, jit.mo.line -> jit.mo.func), 1 agrees. 14 of audit_db's 16 "no refpage" names are objectfile names. Report cost: 0.06 s on top of the 2 s report.

**PD-7. Extractor (I4).**
- `main(argv=None) -> int`, `if __name__ == "__main__": sys.exit(main())`; package mode returns instead of calling sys.exit. A new `--force` flag.
- `write_output(result, output_root, domain_filter=None, force=False)`: before writing anything, if any core domain file the run would write (`<output>/<d>/objects.json` for d in max, msp, jitter, mc, gen, m4l, rnbo) already exists and force is False, it raises `CoreOverwriteRefused` (lists the files). main prints it with the pointer: run `python3 tools/sync_max_bundle.py` (dry-run), then `--apply new|define --names …`; `--force` only to rebuild the core files from refpages, which drops curated entries. It returns 2 with nothing written (no package file, no log). Per-package files (already merge-preserving) and the log are not core files: `--package` and `--domain packages` need no --force.
- Doc pages: extract_all skips any refpage whose name the sync tool's new `is_doc_page_name(name)` flags (the whitespace rule) and records the skipped names in the run's `documentation_pages`. The sync tool's `_is_doc_page(ref)` becomes `is_doc_page_name(ref["name"]) or <its no-I/O clause>`, behavior unchanged. The no-I/O clause is NOT applied by the extractor: measured on the 9.2 bundle, the full `_is_doc_page` flags 15 extractor refpages = the 6 whitespace-named documentation pages + 9 objects the DB holds (jbox, onecopy, project, jit.graph, jit.plot, jit.mo.fieldmask, jit.mo.join, mira.motion, mira.multitouch), whose refpages merely omit their I/O lists.
- Log: in every write mode, after the object files, `extraction-log.json` becomes `sync.restate_extraction_log(output_root, old, now, extra={"last_extraction": run})` written by `sync.write_extraction_log`. run = {tool, mode ("package" | "domain" | "full"), package, source, extraction_timestamp, total_files_found, total_objects, domain_counts, error_count, errors, documentation_pages} from the run's own stats.
- `restate_extraction_log(db_root, old, now, extra=None) -> dict` is factored out of build_extraction_log: `dict(old)` updated with the counts re-stated from disk, carried fields, the timestamp, then `extra`, then `history` (old history + the superseded state's `_LOG_HISTORY_FIELDS`). build_extraction_log = restate with extra = {max_version, max_build, sync}; its key order and values are identical to HEAD (TestRefreshLog stays green unedited).
- The extractor reaches the sync tool through a lazy `_sync_tool()` that puts the repo root (`Path(__file__).resolve().parents[2]`) on sys.path and imports `tools.sync_max_bundle`. Neither tool imports the other at module load, so there is no cycle; both ship in the release archive (tests/test_release.py RUNTIME_FILES).
- Measured: a full run against the 9.2 bundle (0.4 s in memory) drops 25 entries from the real core files (max: array.at, node.codebox, node.script; jitter: jit.*, jit.fx.rota, jit.gl.layer, jit.gl.movie, jit.gl.pbr, jit.gl.polymovie, jit.gl.web, jit.gl.web~, jit.time, jit.time.perlin, jit.time.saw, jit.time.sin; mc: mc.capture~, mc.receive~, mc.send~, mc.sum~, mcp.record~, mcs.loudness~, mcs.sfizz~; m4l: M4L.api.ObserveTransport, M4L.api.ToggleTransport, live.scope~) and adds the 6 documentation pages ('MC Wrapper Features', 'Snapshot Messages', 'Jitter GL Object (OB3D) Messages', 'Jitter Matrix Operators', 'Parameter Properties', 'Jitter Geometry Features').

**PD-8. Merger (I5).**
- `merge()` re-reads overrides.json (keeping the raw bytes) and recomputes conflicts against it: a proposal, from `objects` or `conflicts` of the proposal file, is a conflict iff the live file holds an entry for its name, compared through the DB's aliases (`getattr(db, "_aliases", None)` when it is a dict, the overrides.py precedent). reason CONFLICT_WITH_MANUAL; existing_manual = the live entry. `detect_conflicts()` returns this recomputed dict. A proposal-file conflict whose manual entry has since been removed lands like any proposal; a conflict lands only through conflict_resolutions (field-level adopt and `_manual_original`, unchanged).
- Order: top-level keys and every existing `objects` key keep their position; an adopted conflict is replaced in place. New names go at the end of their domain group (just before the next `_domain_*` key, or the end), in name order; a missing group is created with its `_domain_<d>` separator before the first existing separator that comes later in DOMAIN_ORDER (or at the end). Orphans still get their `_note`.
- `write(merged) -> bool`: indent 2 with the file's own ensure_ascii and trailing newline from `json_style` (fallback when unreproducible: ensure_ascii True, trailing newline iff the file ends with one); returns False and writes nothing on identical bytes; atomic and mode-preserving through atomic_write_bytes; raises `OverridesChangedError` (no write) when the file's bytes differ from those the last merge() read.
- CLI: `--overrides PATH` (default: the repo's overrides.json) for --merge. The merge summary prints the recomputed conflicts and how many `variable_io_rules` proposals await manual review (never merged).
- Measured: at HEAD a no-op merge+write of a scratch copy of the real overrides.json moves 782 of 792 keys and produces a 28,966-line diff (the file is ensure_ascii, no trailing newline; 4 of its 9 domain groups are not sorted).

**PD-9. Analyzer and generator (I5).**
- `MIN_HIGH_INSTANCES = 3`. compute_confidence: HIGH iff ratio >= 1.0 and len(instances) >= 3; unanimity over 1-2 instances falls to MEDIUM; the other tiers are unchanged (the 5 TestComputeConfidence cases stay green).
- analyze_io_counts, after finding mismatches: group instances by normalized positional args (`parse_object_text`, then `io_resolvers.normalize_args`). When the (inlets, outlets) pairs are not all equal and each args key maps to exactly one pair, the finding gets `counts_follow_arguments: True`; `help_inlets` / `help_outlets` come only from argument-less instances (their consensus) and only when it differs from the DB default, else None; and `proposed_variable_io` = {inlet_count, outlet_count, default_inlets, default_outlets}: per side, the first of `fixed:N`, first_arg, first_arg+1, second_arg, second_arg+1, second_arg+2, arg_count, arg_count+1, arg_count_or_default that reproduces every instance's count (default = the argument-less count when present, else the DB default), or None when a side has no fit. Otherwise `counts_follow_arguments: False`, `proposed_variable_io: None`, and the finding is as today.
- A pure `_formula_count(formula, args, default) -> int | None` evaluates the candidates. It mirrors `ObjectDatabase._apply_io_formula` on integer arguments (parity test) and returns None where that formula would need a non-integer argument.
- OverrideGenerator never proposes default inlets/outlets from a finding whose help counts are None; a non-None `proposed_variable_io` goes to `proposed["variable_io_rules"][name]` = rule + `"_audit": {confidence, instances, distinct_arguments, source: "io_count_finding"}` + `"existing_rule"` (the live rule or None). The key `variable_io_rules` is always present (sorted). Proposals only: the merger preserves the live variable_io_rules section unchanged (TestNonObjectSectionsPreserved).

**PD-10. Existing-test edits allowed (old behavior that Q30 replaces).**
1. tests/test_sync_max_bundle.py lines 519, 1025 and 1160: `entry["min_version"] == 9.7` becomes `== "9.7"`.
2. Line 1120: `entry["min_version"] == 8 and isinstance(entry["min_version"], int)` becomes `entry["min_version"] == "8"`.
3. Lines 1123-1125: rename to `test_min_version_flag_keeps_a_point_release_as_a_string`, asserting `parse_min_version("9.1") == "9.1"`, `parse_min_version("9") == "9"` and `parse_min_version("9.10") == "9.10"`.
4. tests/test_version_tags.py: the five tests accept a number or a version string through a local `_version_tuple` (PD-3); the array./string. tests require major 9 with no minor or minor 0 (`9`, `9.0`, `"9"`), the abl. test major 9, the mc test any valid version.

Keep every other line of these files.

**PD-11. Out of scope** (SUMMARY follow-ups): chmod of the 10 real 0600 files; migrating DB min_version values to strings and the RNBO-shadowed list.* aliases (Q38); applying any alias to the real DB (Q38); tools/extract_pkg_io.py fallbacks; reading `max define` lines outside objectmappings files; db-maintenance.md, max-9.2-changes.md and shared-capabilities.md doc updates; the 2 q29-check baseline failures.
</planner_decisions>

<reference_data>
**Real-file styles (json_style, measured).** overrides.json: ensure_ascii True, no trailing newline. aliases.json and extraction-log.json: reproducible both ways, trailing newline. Core domain files: max, gen (both), msp, mc, rnbo (UTF-8 + newline), jitter (ASCII, no newline), m4l (no newline, not sorted).

**Hermetic fixtures to reuse (import, never copy).** `tests.test_sync_max_bundle`: `_make_bundle`, `_make_db`, `_refpage`, `_help_patch`, `_newobj`, `_entry`, `_tree_bytes`, `_sha`; the fake bundle is version "9.7.3 (abc123)", its `init/fake-objectmappings.txt` already holds `max objectfile jit.gl.fresh jit.old;` (help boxes for jit.gl.fresh in jit.old.maxhelp are (1, 2); the fake jit.old is (1, 1), so its help evidence disagrees). `tests.test_audit_db`: `_make_fake_bundle`, `_add_packages`, `_fake_db`, `_make_fake_repo`. `tests.conftest`: `MAX_APP_PATH` and the `requires_max` marker (skips without /Applications/Max.app).

**Existing tests that pin behavior this plan must keep.** test_sync_max_bundle: SECTION_KEYS order (lines 471, 957-963, 1283, 1378), `write_db_file` refusing aliases.json (line 907), TestRefreshLog (750-829), TestWriteGuard (895-943). test_audit_db: 7 sections (441-452, 626-653), `"+1 define-mapped"` and `"1 DB names with no refpage"` in the summary (355-366), the `refpage_index` meta excluding objects/stems/defines (402). test_merger: all of it, including `--merge --dry-run` against the real overrides path, read-only (557-615). test_audit_analyzer: TestComputeConfidence (114-160). test_extraction: TestCommunityPackageExtraction (217-289).

**Q38 contract (the report must carry this).** Q38 applies, with explicit names: mc.*~ shortcuts (mc.times~, mc.plus~: basis mc_wrapper), hslider (file), list.* -> zl.* (list.iter: class; the other 30 are in domain_shadowed), jit.op shortcuts (jit.+ etc.: file), Vizzie short names (abstraction, 90 of the 92 lines). Every entry therefore carries name, candidate, basis, candidate_io and help evidence.
</reference_data>

<tasks>

<task type="tracer" tdd="true">
  <name>Task 1: Step 0; tracer apply -> mode kept + string min_version end to end, then atomic I/O, transactional applies, define regex and string versions (I6 part 1)</name>
  <files>src/maxpat/atomic_io.py, tools/sync_max_bundle.py, .claude/scripts/validate_db.py, tests/test_db_tooling.py, tests/test_sync_max_bundle.py, tests/test_version_tags.py</files>
  <precondition>`git merge-base --is-ancestor 981b7b80 HEAD` succeeds.</precondition>
  <read_first>
    - .planning/reviews/2026-10-11-repo-review.md row I6 (line 166)
    - tools/sync_max_bundle.py 1-81, 153-257, 581-600, 935-984, 1652-1862, 2084-2253, 2256-2367 and 2481-2600
    - .claude/scripts/validate_db.py 1-60 and 314-356; tests/test_version_tags.py (all)
    - tests/test_sync_max_bundle.py 1-130, 230-450, 509-540, 831-945, 997-1030 and 1100-1165
    - planner_decisions PD-1 to PD-5 and PD-10; reference_data
  </read_first>
  <behavior>
    - Module setup (tests/test_db_tooling.py): docstring "Q30 / I4 I5 I6: DB tooling regression tests; scratch copies only". The module-scoped autouse real-DB guard from the rules. A `world` fixture built from `_make_bundle` / `_make_db`. New functions and modules are imported inside the tests.
    - **TestI6TracerApplyKeepsModeAndStringVersion** (red at HEAD): chmod `max/objects.json` to 0o644; `sync.main([*argv, "--apply", "new", "--names", "newthing"]) == 0`; the mode is still 0o644; `entry["min_version"] == "9.7"` and is a str.
    - **TestI6AtomicMode** (red unless marked):
      - `write_db_file` on a 0o640 file keeps 0o640;
      - `--apply deltas` keeps 0o644 on every file it writes;
      - `write_extraction_log` over a 0o640 log keeps 0o640, and on a missing log creates it with `0o666 & ~umask`;
      - `write_groups_file` over a 0o640 canonical groups.json keeps 0o640;
      - unit: `atomic_write_bytes` on a new path in tmp_path leaves no temp file behind and gives `0o666 & ~umask`.
    - **TestI6TransactionalApply** (red):
      - rewrite `packages/FakePkg/objects.json` with indent=4 (unreproducible), then `--apply new --names newthing pkg.fresh` exits 2 and `_tree_bytes(db_root)` is unchanged (HEAD writes max/objects.json first);
      - `atomic_write_many` over three targets (the second absent beforehand) with `os.replace` monkeypatched in `src.maxpat.atomic_io` to fail on its third call: raises; targets 1 and 3 keep their original bytes and modes, target 2 is absent again, and no temp file remains in either directory;
      - `write_db_files` with one AdditiveViolation item writes none of the items;
      - green guard: `--apply new --names pkg.fresh` lands the entry and the package_info.json count in one run.
    - **TestI6DefineRegex** (red): a fake `init/q30-objectmappings.txt` line `max define bare.def corething;` parses to target "corething", args ""; `pkg.alias` still has target "corething" and args "alias.js"; a requires_max case: `parse_define_mappings` of the real C74 returns no target or alias ending in ";" (green guard).
    - **TestI6StringVersions** (red): `_major_minor` cases from PD-3 (None for unusable input); `parse_min_version` returns "8", "9.1", "9.10" and rejects "10", "3", "nine", "9.x", "-8"; `--apply define --names jit.gl.fresh --min-version 8` gives `min_version == "8"`.
    - **TestVersionTuple** (red): validate_db loaded by path; `_version_tuple` gives (9, 10) for "9.10", (8, 1) for 8.1, (9,) for 9, and None for True, None and "x".
  </behavior>
  <action>
**Step 0.** Do the rules' Execution and Step 0 items: the hard preconditions, base-sha, the stash list, Q/db-state-before.txt and the baseline suite.

**Red.**
- Create tests/test_db_tooling.py with the `<behavior>` classes.
- Apply the PD-10 edits to tests/test_sync_max_bundle.py and tests/test_version_tags.py.
- Run `python3 -m pytest -q -p no:cacheprovider tests/test_db_tooling.py tests/test_sync_max_bundle.py tests/test_version_tags.py` into Q/red-t1.txt. It must show failures.

**Green: tracer first.**
- Create src/maxpat/atomic_io.py with atomic_write_bytes, atomic_write_many and json_style (PD-1).
- In tools/sync_max_bundle.py: prepare_db_file, write_db_file on top of it, write_db_files (PD-5); apply_objects through write_db_files; `_major_minor` returning a string (PD-3).
- Run TestI6TracerApplyKeepsModeAndStringVersion alone until it passes. Then expand.

**Green: expansion.**
- detect_style delegates to json_style; write_groups_file and write_extraction_log use atomic_write_bytes (PD-4).
- apply_deltas and apply_inherited through write_db_files; the package count staging helper; main catches OSError in the apply block and exits 2 (PD-5).
- `_DEFINE_RE` (PD-2); parse_min_version and every min_version write as strings (PD-3).
- validate_db.py: `_version_tuple` and the two checks (PD-3). Change nothing else in that file.
- Update the sync module docstring (writers, transaction, string versions) and the docstrings of every changed function.

**Gate and commit:**
1. Run the full suite into Q/pytest-t1.txt; the verify gate must pass.
2. Commit the 6 task files: `fix(sync): mode-preserving atomic writes, transactional multi-file applies, string versions, define regex drops the trailing ';' (Q30)`.
  </action>
  <verify>
    <automated>bash -c 'Q=.planning/quick/261016-jbx-implement-q30-in-planning-reviews-2026-1 && touch "$Q/pytest-t1.txt" && python3 -m pytest -q -p no:cacheprovider > "$Q/pytest-t1.txt" 2>&1; R=$?; tail -1 "$Q/pytest-t1.txt"; test $R -le 1 || exit 1; python3 -c "import re,sys; b,a=[open(p).read() for p in sys.argv[1:3]]; f=lambda t:{l.split(\" - \")[0].strip() for l in t.splitlines() if l.startswith((\"FAILED \",\"ERROR \"))}; n=lambda t:int((re.findall(r\"(\d+) passed\",t) or [0])[-1]); new=sorted(f(a)-f(b)); print(\"new failures:\",new,\"passed:\",n(b),\"->\",n(a)); sys.exit(1 if new or n(a)<=n(b) else 0)" "$Q/baseline-pytest.txt" "$Q/pytest-t1.txt" || exit 1; git diff --quiet HEAD -- .claude/max-objects || exit 1; ST=$(git status --porcelain -- .claude/max-objects patches) || exit 1; test -z "$ST" || exit 1; python3 -c "import hashlib,os,subprocess,sys; ps=[p for p in subprocess.run([\"git\",\"ls-files\",\"-z\",\".claude/max-objects\"],check=True,capture_output=True).stdout.decode().split(chr(0)) if p]; [print(hashlib.sha256(open(p,\"rb\").read()).hexdigest(), oct(os.stat(p).st_mode & 0o7777), p) for p in ps]" > "$Q/db-state-now.txt" || exit 1; diff -q "$Q/db-state-now.txt" "$Q/db-state-before.txt" || exit 1; grep -iq -e failed -e error "$Q/red-t1.txt" && grep -q "def atomic_write_many" src/maxpat/atomic_io.py && grep -q "def json_style" src/maxpat/atomic_io.py && grep -q "def write_db_files" tools/sync_max_bundle.py && grep -q "def prepare_db_file" tools/sync_max_bundle.py && grep -q "def _version_tuple" .claude/scripts/validate_db.py && grep -q "class TestI6TracerApplyKeepsModeAndStringVersion" tests/test_db_tooling.py && grep -q "class TestI6TransactionalApply" tests/test_db_tooling.py && grep -q "def test_min_version_flag_keeps_a_point_release_as_a_string" tests/test_sync_max_bundle.py && C=$(git log --format=%H --fixed-strings --grep="(Q30)" "$(cat "$Q/base-sha.txt")"..HEAD) && set -- $C && test $# -ge 1 && python3 -c "import ast,sys;[ast.parse(open(f).read(),feature_version=(3,10)) for f in sys.argv[1:]]" src/maxpat/atomic_io.py tools/sync_max_bundle.py .claude/scripts/validate_db.py tests/test_db_tooling.py tests/test_sync_max_bundle.py tests/test_version_tags.py'</automated>
  </verify>
  <done>Red was recorded (Q/red-t1.txt), then the gate passed (Q/pytest-t1.txt).
- Every sync writer keeps an existing file's mode; new files get the umask default.
- A multi-file apply writes everything or nothing, and a failed replace is rolled back.
- Argument-less defines lose the `;`; versions are strings end to end; the DB type checks accept a number or a version string.
- The real DB is unchanged (sha256 and mode). One `(Q30)` commit touches only the 6 Task 1 files.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: objectfile alias report, --apply aliases and audit_db objectfile reading (I6 part 2); extractor refuses core overwrites, merges the log, skips documentation pages (I4)</name>
  <files>tools/sync_max_bundle.py, tools/audit_db.py, .claude/scripts/extract_objects.py, tests/test_db_tooling.py</files>
  <read_first>
    - .planning/reviews/2026-10-11-repo-review.md rows I4 and I6 (lines 164, 166), C11 (line 93) and §5.5 (lines 395-403); fix-plan Q38 (lines 657-671)
    - tools/sync_max_bundle.py 155-166, 185-257, 378-449, 581-640, 992-1081, 1594-1650, 2117-2181, 2256-2367 and 2408-2686 (after Task 1's edits, locate these by function name)
    - tools/audit_db.py 165-224, 387-588, 858-916 and 976-1043
    - .claude/scripts/extract_objects.py 1-30, 198-220, 886-1100 and 1214-1327
    - tests/test_audit_db.py 63-155, 240-367, 387-405 and 436-453; tests/test_extraction.py 1-25 and 217-289; tests/test_sync_max_bundle.py 233-316 and 750-830
    - planner_decisions PD-6 and PD-7; reference_data (fixtures, Q38 contract)
  </read_first>
  <behavior>
    - **TestI6ObjectfileParse** (red): a fake C74 with core `init/a-objectmappings.txt`, a package `packages/P/init/p-mc.txt` (not an objectmappings name) and lines covering a double space, a class plus extra args, a mapping with no `;`, and a duplicate name. `parse_objectfile_mappings` returns every record (class/args split, package "P" for the package file), lines counts every line, duplicates holds the repeated name, and files holds both files.
    - **TestI6ObjectfileReport** (hermetic world; the test adds a fixture init file and fake-DB entries, including an `rnbo/objects.json` entry with domain RNBO) (red):
      - SECTION_KEYS has `objectfile_aliases` right after `define_missing`; ui_maxclasses is still last;
      - one alias per basis: mc_wrapper through the file chain, abstraction, class, file, and none;
      - a resolved alias is not in entries; the RNBO-resolving name is in domain_shadowed with its candidate;
      - help_io_agrees is False for jit.gl.fresh, None with no help box, True for a matching fixture box;
      - format_summary has an `objectfile` line; the report run leaves `_tree_bytes(db_root)` unchanged.
    - **TestI6ApplyAliases** (red):
      - `--apply aliases` without --names exits 2 and the tree is unchanged;
      - a file-basis alias with no help box is written: exit 0, old aliases keep their order, the new one is appended, json_style and mode are preserved, `ObjectDatabase(db_root).lookup(alias)["name"]` equals the candidate, overrides.json sha is unchanged;
      - a resolved name and the RNBO-shadowed name are skipped; an unknown name and jit.gl.fresh (help disagrees) are aborted with exit 1, and aliases.json is byte-identical;
      - a forced verification failure (monkeypatched load_db raising) restores aliases.json and exits 2.
    - **TestI6AuditObjectfile** (tests.test_audit_db fixtures plus an `init` objectfile line) (red): absent_from_bundle has `objectfile_mapped == [{"name": ..., "file": ..., "class": ...}]`, the count excludes it, and the summary shows `+1 objectfile-mapped` with `+N define-mapped` still present; missing_from_db carries `objectfile_aliases` with the unresolved name; the refpage_index meta has no `objectfiles` key; 7 sections.
    - **TestI6ObjectfileRealBundle** (requires_max, read-only report of the real bundle against the real DB):
      - mc.times~ -> mc.*~ (mc_wrapper), hslider -> slider (file), list.iter -> zl.iter (class), 4mixr -> vz.4mixr (abstraction);
      - mc.abl.dsp.chorus~ is unresolved (non-objectmappings init files are read); list.len is in domain_shadowed with candidate zl.len; unresolved_count >= 251;
      - run_audit: jit.*, mc.send~ and array.at are in objectfile_mapped and not in absent names.
    - **TestI4ExtractRefusesCore**: the extractor loaded by path, run through a helper that sets sys.argv, calls `main()` and turns SystemExit into its code (so the test runs at HEAD too). The fake C74 holds `docs/refpages/max-ref` with one object refpage and one whitespace-named doc page; the scratch output holds `max/objects.json` and a seeded extraction-log.json.
      - Red: without --force the code is 2, stderr names `tools/sync_max_bundle.py` and `--force`, and every output byte is unchanged.
      - With --force: max/objects.json is rebuilt, the doc page is absent, and the log keeps its old keys with history + 1.
      - `--domain msp` with an existing msp file is refused too.
    - **TestI4ExtractLogMerge** (red): the scratch output is seeded with a copy of the real extraction-log.json (read-only source), a `packages/` dir and package_info.json. `--package Fake --path <tmp package with docs/x.maxref.xml>` exits 0; every old key is kept (sync, max_version, max_build), `history == old history + [superseded state]`, `last_extraction["package"] == "Fake"`, and `total_objects` equals the live count on disk.
    - **TestI4DocPageFilter** (red): `extract_all(fake c74)` has no whitespace-named object and lists it in `documentation_pages`; a refpage with no I/O lists and no methods is still extracted; `sync._is_doc_page` gives the same answers as at HEAD for both shapes (green guard); `sync.is_doc_page_name` exists. requires_max: `extract_all` of the real C74 (in memory) holds none of the 6 documentation pages and all 9 no-I/O names.
    - **TestI4RealDbCopyRefused** (requires_max) (red): a scratch copy of the real DB (rules' explicit file list), with the extractor run against the real bundle and `--output <copy>` without --force, gives code 2 and a byte-identical copy (HEAD drops the 25 entries).
  </behavior>
  <action>
**Red.** Append the `<behavior>` classes to tests/test_db_tooling.py. Run `python3 -m pytest -q -p no:cacheprovider tests/test_db_tooling.py -k "I6Objectfile or I6Apply or I6Audit or I4"` into Q/red-t2.txt. It must show failures.

**Green: sync tool.**
- parse_objectfile_mappings and the candidate / evidence helpers (PD-6); build_bundle_index stores the parse under `objectfiles`.
- The `objectfile_aliases` section, its SECTION_KEYS slot, its run_report wiring and the format_summary line.
- `aliases` in APPLY_MODES, apply_aliases, write_aliases_file, the reload verification with restore, the main wiring and result printing, and the exit codes (PD-6).
- is_doc_page_name, with _is_doc_page on top of it; restate_extraction_log, with build_extraction_log on top of it (PD-7). TestRefreshLog must stay green unedited.

**Green: audit_db.** The `objectfiles` index key (left out of the emitted header), objectfile_mapped, missing_from_db objectfile_aliases and the two summary lines (PD-6). Update the module docstring's section notes.

**Green: extractor (PD-7).**
- main(argv=None) returning codes, `--force`, CoreOverwriteRefused and the guard in write_output, run before any write.
- The lazy `_sync_tool()`; the doc-page skip in extract_all; the merged log in every write mode.
- Update the usage docstring: `--force`, the sync-tool pointer, and that the log is merged.
- Do not change parse_standard_xml, parse_gen_xml, parse_rnbo_xml, discover_xml_files or update_package_registry.

**Gate and commit:**
1. Run the full suite into Q/pytest-t2.txt; the verify gate must pass.
2. Commit the 4 task files: `feat(db-tools): objectfile alias report and --apply aliases; audit_db reads objectfile lines; extract_objects refuses core overwrites, merges the log, skips doc pages (Q30)`.
  </action>
  <verify>
    <automated>bash -c 'Q=.planning/quick/261016-jbx-implement-q30-in-planning-reviews-2026-1 && touch "$Q/pytest-t2.txt" && python3 -m pytest -q -p no:cacheprovider > "$Q/pytest-t2.txt" 2>&1; R=$?; tail -1 "$Q/pytest-t2.txt"; test $R -le 1 || exit 1; python3 -c "import re,sys; b,a=[open(p).read() for p in sys.argv[1:3]]; f=lambda t:{l.split(\" - \")[0].strip() for l in t.splitlines() if l.startswith((\"FAILED \",\"ERROR \"))}; n=lambda t:int((re.findall(r\"(\d+) passed\",t) or [0])[-1]); new=sorted(f(a)-f(b)); print(\"new failures:\",new,\"passed:\",n(b),\"->\",n(a)); sys.exit(1 if new or n(a)<=n(b) else 0)" "$Q/baseline-pytest.txt" "$Q/pytest-t2.txt" || exit 1; git diff --quiet HEAD -- .claude/max-objects || exit 1; ST=$(git status --porcelain -- .claude/max-objects patches) || exit 1; test -z "$ST" || exit 1; python3 -c "import hashlib,os,subprocess,sys; ps=[p for p in subprocess.run([\"git\",\"ls-files\",\"-z\",\".claude/max-objects\"],check=True,capture_output=True).stdout.decode().split(chr(0)) if p]; [print(hashlib.sha256(open(p,\"rb\").read()).hexdigest(), oct(os.stat(p).st_mode & 0o7777), p) for p in ps]" > "$Q/db-state-now.txt" || exit 1; diff -q "$Q/db-state-now.txt" "$Q/db-state-before.txt" || exit 1; grep -iq -e failed -e error "$Q/red-t2.txt" && grep -q "def parse_objectfile_mappings" tools/sync_max_bundle.py && grep -q "def apply_aliases" tools/sync_max_bundle.py && grep -q "def write_aliases_file" tools/sync_max_bundle.py && grep -q "def is_doc_page_name" tools/sync_max_bundle.py && grep -q "def restate_extraction_log" tools/sync_max_bundle.py && grep -q "objectfile_mapped" tools/audit_db.py && grep -q "parse_objectfile_mappings(" tools/audit_db.py && grep -q "class CoreOverwriteRefused" .claude/scripts/extract_objects.py && grep -q "restate_extraction_log(" .claude/scripts/extract_objects.py && grep -q "class TestI4ExtractRefusesCore" tests/test_db_tooling.py && grep -q "class TestI6ApplyAliases" tests/test_db_tooling.py && python3 -c "import sys; sys.path.insert(0, \".\"); import tools.sync_max_bundle as s; k=s.SECTION_KEYS; sys.exit(0 if k[k.index(\"define_missing\")+1]==\"objectfile_aliases\" and k[-1]==\"ui_maxclasses\" and \"aliases\" in s.APPLY_MODES else 1)" && C=$(git log --format=%H --fixed-strings --grep="(Q30)" "$(cat "$Q/base-sha.txt")"..HEAD) && set -- $C && test $# -ge 2 && python3 -c "import ast,sys;[ast.parse(open(f).read(),feature_version=(3,10)) for f in sys.argv[1:]]" tools/sync_max_bundle.py tools/audit_db.py .claude/scripts/extract_objects.py tests/test_db_tooling.py'</automated>
  </verify>
  <done>Red was recorded (Q/red-t2.txt), then the gate passed (Q/pytest-t2.txt).
- The sync report lists every objectfile alias the DB cannot resolve, with a candidate, basis and help evidence, plus the RNBO-shadowed list.* names.
- `--apply aliases --names` lands only named, verified aliases, additively and atomically.
- audit_db separates objectfile-mapped names from real absences and reports unresolved aliases.
- The extractor refuses core overwrites without --force, merges the log with history in every mode, and never extracts documentation pages.
- The real DB is unchanged. A second `(Q30)` commit touches only the 4 Task 2 files.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: merger recomputes conflicts at merge time and writes atomically in the file's own style; HIGH needs 3 instances; variable_io rule proposals (I5); final gate, commit audit and SUMMARY</name>
  <files>src/maxpat/audit/merger.py, src/maxpat/audit/analyzer.py, src/maxpat/audit/overrides.py, src/maxpat/audit/cli.py, tests/test_db_tooling.py</files>
  <read_first>
    - .planning/reviews/2026-10-11-repo-review.md rows I5 (line 165) and C2 (line 84)
    - src/maxpat/audit/merger.py (all, 242 lines); src/maxpat/audit/analyzer.py 42-80 and 225-284; src/maxpat/audit/overrides.py 60-245; src/maxpat/audit/cli.py 33-140 and 140-210
    - src/maxpat/db_lookup.py 25-42 and 1211-1335 (compute_io_counts, _apply_io_formula); src/maxpat/io_resolvers.py 117-133 (normalize_args); src/maxpat/audit/parser.py 18-70 (parse_object_text)
    - tests/test_merger.py 1-110, 194-225, 345-440 and 488-615; tests/test_audit_analyzer.py 1-75, 110-160 and 218-290
    - planner_decisions PD-8 and PD-9
  </read_first>
  <behavior>
    - **TestI5MergeTimeConflicts** (red):
      - the proposal file has `coll` under `objects` (no conflict at audit time); the live overrides.json then gains a manual `coll` entry. merge() keeps the manual entry unchanged; detect_conflicts() holds coll with reason CONFLICT_WITH_MANUAL and existing_manual == the live entry;
      - with `{"coll": {"adopt_fields": ["inlets"]}}` the inlets are adopted and `_manual_original` is set;
      - a proposal-file conflict whose manual entry has since been removed lands as an ordinary proposal;
      - green guard: a merger built before a manual edit sees the edit (merge() re-reads).
    - **TestI5MergerWrite** (red unless marked):
      - a scratch copy of the real overrides.json plus an empty proposal file: merge() then write() returns False, and the bytes are identical (HEAD: 782 keys moved);
      - a fixture overrides.json with an unsorted `_domain_max` group, ensure_ascii, no trailing newline: a new max-domain proposal goes at the end of the max group, every existing key keeps its relative order, the file still has no trailing newline, and a difflib diff of old to new text has only `+` lines;
      - a 0o640 file keeps its mode, and write() goes through `atomic_write_bytes` (spy via monkeypatch on the merger module);
      - stale guard: merge(), then an on-disk edit, then write() raises OverridesChangedError and the file keeps the edit;
      - green guard: a new domain group lands in DOMAIN_ORDER position.
    - **TestI5ConfidenceThreshold** (red): compute_confidence gives MEDIUM for 1 unanimous instance and for 2, HIGH for 3; MIN_HIGH_INSTANCES == 3; analyze_outlet_types with one mismatching instance reports MEDIUM.
    - **TestI5VariableIoProposal** (red unless marked), with a MagicMock DB whose default counts are (1, 1) and variable_io False:
      - instances `bucket` (1,1) and three `bucket 4` (1,4): counts_follow_arguments True, help_outlets None, proposed_variable_io == {"inlet_count": "fixed:1", "outlet_count": "first_arg", "default_inlets": 1, "default_outlets": 1};
      - OverrideGenerator: proposed["objects"] has no bucket entry with 4 outlets; proposed["variable_io_rules"]["bucket"] carries the rule, `_audit` (instances 4, distinct_arguments 2) and existing_rule None;
      - `x 2 3` (2,4) and `x 2 5` (2,6) give second_arg+1 on the outlet side;
      - green guards: one args key with two count pairs gives counts_follow_arguments False and today's finding; all-equal counts keep today's behavior.
    - **TestI5FormulaParity** (red): for every candidate formula and the integer argument lists [], ["3"], ["3", "5"] and ["1", "2", "4"] with default 2, `_formula_count` equals `ObjectDatabase()._apply_io_formula`; non-integer arguments read by the formula give None.
    - **TestI5CliOverridesPath** (red): `cli.main(["--merge", "--output-dir", d, "--overrides", copy])` writes only the copy (the manual entry kept, the new proposal landed) and returns 0; with `--dry-run` the copy is unchanged; the repo overrides.json sha256 is unchanged.
    - tests/test_merger.py, tests/test_audit_analyzer.py, tests/test_audit_reporter.py and tests/test_db_signal_ports.py stay green, unedited.
  </behavior>
  <action>
**Red.** Append the `<behavior>` classes to tests/test_db_tooling.py. Run `python3 -m pytest -q -p no:cacheprovider tests/test_db_tooling.py -k I5` into Q/red-t3.txt. It must show failures.

**Green.**
- merger.py (PD-8): OverridesChangedError; merge() re-reads the file and recomputes conflicts; detect_conflicts() recomputes too; the order-preserving assembly replaces the sorting `_group_by_domain` step (keep `_get_domain` and DOMAIN_ORDER); write() with json_style, atomic_write_bytes, the no-op return and the stale guard. Update the module and class docstrings: the class no longer claims to regroup or sort.
- analyzer.py (PD-9): MIN_HIGH_INSTANCES, compute_confidence, `_formula_count`, the arguments analysis in analyze_io_counts; document the two new finding keys on ObjectFindings.io_count_finding.
- overrides.py (PD-9): the default-count guard and the `variable_io_rules` proposals.
- cli.py (PD-8): `--overrides`, plus the conflict and pending-rules lines in the merge summary.

**Final gate:**
1. Run the full suite into Q/final-pytest.txt; the verify gate must pass.
2. Commit the 5 task files: `fix(audit): merge-time conflicts and an atomic, style-preserving overrides writer; HIGH needs 3 instances; variable_io rule proposals (Q30)`.
3. Write `git show --name-only` of every `(Q30)` commit to Q/q30-commit-files.txt.

Then write SUMMARY.md to the `<output>` spec.
  </action>
  <verify>
    <automated>bash -c 'Q=.planning/quick/261016-jbx-implement-q30-in-planning-reviews-2026-1 && touch "$Q/final-pytest.txt" && python3 -m pytest -q -p no:cacheprovider > "$Q/final-pytest.txt" 2>&1; R=$?; tail -1 "$Q/final-pytest.txt"; test $R -le 1 || exit 1; python3 -c "import re,sys; b,a=[open(p).read() for p in sys.argv[1:3]]; f=lambda t:{l.split(\" - \")[0].strip() for l in t.splitlines() if l.startswith((\"FAILED \",\"ERROR \"))}; n=lambda t:int((re.findall(r\"(\d+) passed\",t) or [0])[-1]); new=sorted(f(a)-f(b)); print(\"new failures:\",new,\"passed:\",n(b),\"->\",n(a)); sys.exit(1 if new or n(a)<=n(b) else 0)" "$Q/baseline-pytest.txt" "$Q/final-pytest.txt" || exit 1; git diff --quiet HEAD -- .claude/max-objects || exit 1; ST=$(git status --porcelain -- .claude/max-objects patches) || exit 1; test -z "$ST" || exit 1; DS=$(git diff --stat -- .claude/max-objects/) || exit 1; test -z "$DS" || exit 1; python3 -c "import hashlib,os,subprocess,sys; ps=[p for p in subprocess.run([\"git\",\"ls-files\",\"-z\",\".claude/max-objects\"],check=True,capture_output=True).stdout.decode().split(chr(0)) if p]; [print(hashlib.sha256(open(p,\"rb\").read()).hexdigest(), oct(os.stat(p).st_mode & 0o7777), p) for p in ps]" > "$Q/db-state-now.txt" || exit 1; diff -q "$Q/db-state-now.txt" "$Q/db-state-before.txt" || exit 1; grep -iq -e failed -e error "$Q/red-t3.txt" && grep -q "class OverridesChangedError" src/maxpat/audit/merger.py && grep -q "json_style(" src/maxpat/audit/merger.py && grep -q "MIN_HIGH_INSTANCES" src/maxpat/audit/analyzer.py && grep -q "proposed_variable_io" src/maxpat/audit/analyzer.py && grep -q "proposed_variable_io" src/maxpat/audit/overrides.py && grep -q -e "--overrides" src/maxpat/audit/cli.py && grep -q "class TestI5MergeTimeConflicts" tests/test_db_tooling.py && grep -q "class TestI5VariableIoProposal" tests/test_db_tooling.py && S=$(git stash list) && test "$S" = "$(cat "$Q/stash-list-before.txt")" && C=$(git log --format=%H --fixed-strings --grep="(Q30)" "$(cat "$Q/base-sha.txt")"..HEAD) && set -- $C && test $# -ge 3 && for c in $C; do git show --name-only --format= "$c" || exit 1; done > "$Q/q30-commit-files.txt" && test -s "$Q/q30-commit-files.txt" && python3 -c "import sys; ok=set(sys.argv[2:]); bad=sorted({l.strip() for l in open(sys.argv[1]) if l.strip() and l.strip() not in ok}); print(\"committed files outside files_modified:\", bad); sys.exit(1 if bad else 0)" "$Q/q30-commit-files.txt" src/maxpat/atomic_io.py tools/sync_max_bundle.py tools/audit_db.py .claude/scripts/extract_objects.py .claude/scripts/validate_db.py src/maxpat/audit/merger.py src/maxpat/audit/analyzer.py src/maxpat/audit/overrides.py src/maxpat/audit/cli.py tests/test_db_tooling.py tests/test_sync_max_bundle.py tests/test_version_tags.py && python3 -c "import ast,sys;[ast.parse(open(f).read(),feature_version=(3,10)) for f in sys.argv[1:]]" src/maxpat/audit/merger.py src/maxpat/audit/analyzer.py src/maxpat/audit/overrides.py src/maxpat/audit/cli.py tests/test_db_tooling.py'</automated>
  </verify>
  <done>Red was recorded (Q/red-t3.txt), then the final gate passed (Q/final-pytest.txt): no failure outside the 2 baseline failures, more passed tests than 5115.
- A manual override added after the audit survives a merge.
- overrides.json is written atomically in its own style, unchanged on a no-op merge, and never over a newer edit.
- HIGH needs 3 instances; argument-dependent counts become variable_io proposals, never defaults.
- `git diff --stat -- .claude/max-objects/` is empty and every tracked DB file keeps its sha256 and mode.
- At least 3 `(Q30)` commits, all within files_modified and none under patches/; the stash list is unchanged.</done>
</task>

</tasks>

<threat_model>
Security config: enforcement on, ASVS level 1, block on high. This is local tooling that reads the installed Max bundle and writes JSON data files, with no network, auth, crypto or package installs. What matters:
- integrity of the curated object DB (overrides, domain files, aliases, log history);
- no write to the real DB from tests or from this task;
- git hygiene.

## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Installed Max bundle (init/*.txt, refpages, help patches) -> sync / audit / extractor | Vendor text and JSON parsed into DB proposals; malformed or surprising lines must not corrupt the DB |
| Tool CLI arguments (--output, --names, --overrides, --force) -> DB files | An operator mistake or wrong path can overwrite curated data |
| Audit proposals -> overrides.json | Machine-derived corrections meet expert-curated entries |
| Test suite -> filesystem | Tests run next to the real DB and must only touch tmp_path |
| Concurrent Claude instances -> git | Broad staging or stash can sweep in or strand another instance's work |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-jbx-01 | Tampering | extract_objects.py full / domain run overwriting curated core files | high | mitigate | CoreOverwriteRefused before any write unless --force; the message points to the sync tool (PD-7). TestI4ExtractRefusesCore and TestI4RealDbCopyRefused (scratch copy of the real DB, byte-identical). |
| T-jbx-02 | Repudiation | extraction-log.json history and sync record wiped by a run | medium | mitigate | Every write mode merges through restate_extraction_log: old keys kept, superseded state appended to history, the run recorded under last_extraction (PD-7). TestI4ExtractLogMerge. |
| T-jbx-03 | Tampering | Audit merger overwriting manual overrides added after the audit, or racing a concurrent edit | high | mitigate | Conflicts recomputed against the live file at merge time; OverridesChangedError when the file changed since merge() read it (PD-8). TestI5MergeTimeConflicts and the stale-guard test. |
| T-jbx-04 | Tampering | Partial multi-file writes after a mid-apply failure | medium | mitigate | write_db_files prepares every payload first; atomic_write_many replaces all or restores all (PD-1, PD-5). TestI6TransactionalApply, including an injected os.replace failure. |
| T-jbx-05 | Denial of Service | Atomic writers leaving DB files at mode 0600 (unreadable to other users and tools) | low | mitigate | atomic_write_bytes copies the target's mode, or uses the umask default for new files (PD-1, PD-4). TestI6AtomicMode and the tracer. The 10 real files already at 0600 are listed for the user, not touched. |
| T-jbx-06 | Tampering | `--apply aliases` adding an alias that breaks ObjectDatabase loading or shadows a real entry | medium | mitigate | Only named, unresolved aliases whose candidate resolves and whose help boxes (if any) agree; additive check; reload verification with byte restore; resolved and RNBO-shadowed names are never aliased (PD-6). TestI6ApplyAliases. |
| T-jbx-07 | Tampering | Bundle text (objectfile / define lines) parsed into bad names or targets | low | mitigate | Anchored regexes exclude `;` from name and target; candidates must resolve in the DB; nothing from the report is written without --names (PD-2, PD-6). |
| T-jbx-08 | Tampering | Tests writing the real DB or committed patches | high | mitigate | Scratch copies from an explicit file list (never _pkg-source); the module-scoped real-DB guard; each verify checks git diff, git status, and sha256 + mode against Q/db-state-before.txt. |
| T-jbx-09 | Elevation of Privilege | Commits sweeping in other instances' files, or a stash stranding work | medium | mitigate | `git add -- <paths>` and path-limited commits; the commit-file allowlist check; the stash list compared with Step 0; hard preconditions HALT on a stale base or a dirty tree. |
| T-jbx-10 | Tampering | Analyzer proposals turning argument-specific help counts into default I/O overrides | medium | mitigate | HIGH needs 3 instances; argument-dependent counts become variable_io_rules proposals that are never merged automatically (PD-9). TestI5VariableIoProposal. |
| T-jbx-SC | Tampering | npm/pip/cargo installs | low | accept | This plan installs no packages. |
</threat_model>

<verification>
- Every task's `<verify>` passes. Q/red-t1.txt, red-t2.txt and red-t3.txt each show failures recorded before the fix.
- Q/pytest-t1.txt, pytest-t2.txt and final-pytest.txt each show no FAILED/ERROR line outside the 2 baseline failures, and more passed tests than the baseline's 5115; the 5 xfailed / 1 xpassed split is unchanged.
- `git diff --stat -- .claude/max-objects/` is empty, `git status --porcelain -- .claude/max-objects` is empty, and every tracked DB file's sha256 and mode match Q/db-state-before.txt.
- `git stash list` is unchanged. The `(Q30)` commits touch only files_modified paths. The only existing-test edits are those in PD-10.
- After SUMMARY.md is written, its decisions section names the planner calls:

  <automated>bash -c 'S=.planning/quick/261016-jbx-implement-q30-in-planning-reviews-2026-1/261016-jbx-SUMMARY.md && D=$(awk "/^## Decisions to confirm/{f=1;next} /^## /{f=0} f" "$S") && test -n "$D" && for k in PD-3 PD-5 PD-6 PD-7 PD-8 PD-9; do printf "%s\n" "$D" | grep -q -- "$k" || exit 1; done'</automated>
</verification>

<success_criteria>
- I4, I5 and I6 each have regression tests that were red at 981b7b80 and are green now, all on scratch data.
- The extractor cannot silently overwrite core DB files or wipe the extraction log, and it never extracts documentation pages.
- The merger never overwrites a newer manual override, never re-sorts or reformats overrides.json, and writes atomically; the analyzer no longer rates single instances HIGH or saves argument-specific counts as defaults.
- The sync tool's writes keep file modes and are all-or-nothing; versions are strings; argument-less defines parse correctly; both tools report objectfile aliases; `--apply aliases --names` exists for Q38.
- No file under .claude/max-objects/ changed. No CLAUDE.md, skill or TECHNICAL.md edit.
- SUMMARY lists the decisions to confirm, behavior changes, doc impact, follow-ups and Q38 inputs.
</success_criteria>

<output>
Create `.planning/quick/261016-jbx-implement-q30-in-planning-reviews-2026-1/261016-jbx-SUMMARY.md` when done. It must include:
- the last line of Q/baseline-pytest.txt, Q/pytest-t1.txt, Q/pytest-t2.txt and Q/final-pytest.txt, and the 2 pre-existing baseline failures by node id (q29-check: README patch table and the Q24 allowlist) as a follow-up for the user;
- the red evidence: failing test counts from Q/red-t1.txt, red-t2.txt and red-t3.txt, naming the green guards that passed at HEAD by design;
- the existing-test edits (PD-10), and nothing else;
- **`## Decisions to confirm`**: a section with exactly this heading, separate from the template's executor "Deviations from Plan" log. One entry per planner call, each naming its PD id:
  - **PD-3:** min_version written as strings now, with the DB type checks widened to accept both until Q38 migrates (alternative: keep numbers until Q38);
  - **PD-5:** transaction scope: object files plus package_info.json in one all-or-nothing write;
  - **PD-6:** all init/*.txt files read (719 lines, not the review's 647); the candidate basis rules; RNBO-shadowed list.* names report-only, never aliased by Q30;
  - **PD-7:** the extractor applies only the sync tool's whitespace rule (the no-I/O rule would drop 9 real objects); the log is merged in every mode, --force included;
  - **PD-8:** a proposal whose manual entry was removed after the audit now lands; new keys go at the end of their domain group; the stale guard;
  - **PD-9:** 1-2 unanimous instances are MEDIUM (still proposal-eligible); variable_io rules are proposals only, never merged.

  End the section by asking the user to accept each one or reopen it, with multiple-choice options.
- **behavior changes:**
  - extract_objects.py needs --force to replace a core domain file and returns exit codes;
  - every extractor run merges extraction-log.json;
  - sync `--apply` writes are all-or-nothing and keep file modes;
  - new min_version values are strings;
  - the sync report and audit_db summary have objectfile lines;
  - `--apply aliases` exists;
  - merger output keeps the file's order and style;
  - audit confidence and io findings changed as in PD-9;
- **follow-ups (PD-11):**
  - the exact chmod command for the real DB files at 0600 (list them with `find .claude/max-objects -maxdepth 3 -name "*.json" -perm 600 -not -path "*/_pkg-source/*"`);
  - the Q38 inputs: report fields, the 30 domain_shadowed list.* names needing a lookup-context decision, the 8 help-disagreeing file-basis candidates;
  - Q38's DB-wide min_version migration;
- **doc impact, not edited (rule 8):**
  - db-maintenance.md "After a Max update": `--apply aliases`, the objectfile section, the extractor's --force and log merge, string min_version;
  - max-9.2-changes.md line 184 and shared-capabilities.md line 13;
  - TECHNICAL.md lines 122 and 133 (min_version shown as an int);
- **MAX confirmation (rule 9):** none needed. This task changes DB tooling only, writes no patch and changes no DB data;
- **Python 3.10:** not runnable locally (3.14 only); compatibility checked with `ast.parse(feature_version=(3, 10))`.
</output>
