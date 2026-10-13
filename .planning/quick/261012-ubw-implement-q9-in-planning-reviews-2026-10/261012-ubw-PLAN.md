---
phase: quick-261012-ubw
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - tools/help_io.py
  - tools/audit_db.py
  - tests/test_help_io.py
  - tests/fixtures/help_io_mini_baseline.json
  - tests/fixtures/help_io_baseline.json
autonomous: true
requirements: [Q9, S6]

estimate:
  tokens: 110000
  raw_tokens: 110000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "`python3 tools/audit_db.py --help-io` scans every `.maxhelp` under `<max-app>/Contents/Resources/C74` and under the `help`/`Help` directory of each package in `--packages-dir` (default `~/Documents/Max 9/Packages`). It never descends into gen~/mc.gen~/mcs.gen~/gen/jit.gen/jit.pix/jit.gl.pix/rnbo~ patchers, or into any inner patcher whose classnamespace is dsp.gen, jit.gen or rnbo. It prints a summary (installed Max version, help-file appversions, sources, box counts, mismatching names), and `--json PATH` writes the full report. The default audit (no `--help-io`) is unchanged."
    - "Each compared box's saved numinlets/numoutlets is compared with `ObjectDatabase.compute_io_counts(name, positional_args)`. When the counts agree and the saved outlettype is a list of length numoutlets, the saved signal class of each outlet is compared with the signal class of `get_outlet_types(name, positional_args)`. Content-defined boxes, unresolved names, malformed boxes and gen~/rnbo~/jit.gen internals are counted but never compared. OQ1-A adds non-newobj boxes, keyed by maxclass with no args."
    - "`--write-baseline PATH` writes a canonical baseline: schema 1, sorted keys, indent 1, trailing newline, no timestamp, no absolute path, only names with at least one mismatch. Two runs give identical bytes. The target is screened by guard_output_path. An unavailable bundle gives exit 1 and writes nothing. `--write-baseline` without `--help-io` gives exit 2."
    - "`diff_baselines(baseline, live)` reports a regression exactly when a (source, name) has more count_mismatches or more type_mismatches live than in the baseline, for sources present in both at the same version. Stale-version, new and missing sources and all decreases are reported but are never regressions. A schema other than 1 raises ValueError. This is unit-tested on the committed tiny fixture `tests/fixtures/help_io_mini_baseline.json`, with no Max needed."
    - "`tests/fixtures/help_io_baseline.json` is committed. It was generated from the installed Max 9.2.0 bundle plus this Mac's packages, at the post-Task-2 HEAD with the DB unchanged. It is canonical and under 400 KB, and it records the review's evidence: sel, r, unpack, pack, route and coll count mismatches, sfrecord~ and pitchshift~ signal-role mismatches, and (OQ1-A) spectroscope~ (2,1) vs DB (2,0)."
    - "The requires_max live test passes on this Mac. It skips with `requires the Max application bundle` under MAXPAT_TEST_MAX_APP=/nonexistent/Max.app, and skips (does not fail) when the installed Max version differs from the baseline's. Decrementing one baseline count is detected as exactly one regression."
    - "No file under `.claude/max-objects/`, `src/`, `patches/`, CLAUDE.md, TECHNICAL.md, README.md or `.claude/skills/` changes. The full suite stays green (2691 passed at base, plus only the new tests; 1 xfailed, 1 xpassed). Every changed `.py` file parses under Python 3.10, and the new tests pass under uv Python 3.10."
  artifacts:
    - path: "tools/help_io.py"
      provides: "Help-box I/O oracle: source discovery, box walk with gen~/rnbo~/jit.gen skip, count and signal-class comparison, full report, canonical baseline, baseline diff, text summary"
      contains: "def diff_baselines"
      min_lines: 250
    - path: "tools/audit_db.py"
      provides: "CLI mode --help-io (with --packages-dir, --write-baseline) and run_help_io() envelope builder"
      contains: "--help-io"
    - path: "tests/test_help_io.py"
      provides: "Hermetic scanner/CLI/diff tests on fake bundles and the tiny fixture, committed-baseline hygiene tests, and the requires_max live regression test"
      contains: "requires_max"
      min_lines: 250
    - path: "tests/fixtures/help_io_mini_baseline.json"
      provides: "Tiny hand-written baseline for the diff unit tests"
      contains: "package:Demo"
    - path: "tests/fixtures/help_io_baseline.json"
      provides: "Committed Max 9.2.0 help-box I/O baseline (mismatching names per source)"
      contains: "\"schema\": 1"
  key_links:
    - from: "tools/audit_db.py"
      to: "tools/help_io.py"
      via: "`from tools import help_io` after the src imports; run_help_io() calls help_io.scan_help_io(); main() writes help_io.dump_baseline(help_io.build_baseline(section))"
      pattern: "help_io\\."
    - from: "tools/help_io.py"
      to: "src/maxpat/db_lookup.py"
      via: "db.lookup / db.compute_io_counts / db.get_outlet_types per compared box"
      pattern: "compute_io_counts"
    - from: "tools/help_io.py"
      to: "src/maxpat/patcher.py"
      via: "the content-defined exclusion is CONTENT_DEFINED_NAMES (patcher.py) united with _CONTAINER_NAMES (validation.py), imported rather than copied"
      pattern: "CONTENT_DEFINED_NAMES"
    - from: "tests/test_help_io.py"
      to: "tests/fixtures/help_io_baseline.json"
      via: "TestLiveOracle diffs a fresh live scan against the committed baseline and asserts no regressions"
      pattern: "help_io_baseline.json"
    - from: "tests/test_help_io.py"
      to: "tests/conftest.py"
      via: "@pytest.mark.requires_max plus `from tests.conftest import MAX_APP_PATH` (the MAXPAT_TEST_MAX_APP seam)"
      pattern: "MAX_APP_PATH"
---

<objective>
Implement Q9 of `.planning/reviews/2026-10-11-fix-plan.md`: a help-box I/O oracle. This is the §5.5 bundle-mining foundation that Q10 (variable-I/O rules, C1) and Q11 (overrides, C2, C9) consume. It also delivers the "help-box oracle test" half of S6.

- **New command:** `python3 tools/audit_db.py --help-io`. It scans every `.maxhelp` in the installed Max bundle and in the installed packages' help dirs, skipping gen~, rnbo~ and jit.gen internals.
- **Comparison:** each box's saved `numinlets`/`numoutlets`/`outlettype` against `ObjectDatabase.compute_io_counts(name, args)` and the DB port types.
- **Output:** JSON plus a summary (mismatching names, box counts, Max versions).
- **Baseline:** `tests/fixtures/help_io_baseline.json` is committed.
- **Test:** fails when mismatches increase compared with the baseline. It skips without Max.app, and its diff logic is unit-tested on a tiny committed fixture.
- **Do not fix DB entries.** This task measures the DB; it changes nothing under `.claude/max-objects/` or `src/`.

Output: three commits, one per task, each with `(Q9)` in the message. Nothing is pushed.
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
- Q1-Q8 have landed, so the suite must stay **fully green**. Expected baseline at HEAD `cd5a885`: **2691 passed, 1 xfailed, 1 xpassed, 29 warnings** (measured at planning in 51 s). The executor re-measures it in Step 0.
- Execution is sequential on the main working tree (no worktree), on branch `main`. All three tasks edit `tests/test_help_io.py` and `tools/help_io.py`, so they run in order.
- **This task never edits** `.claude/max-objects/**`, `src/**`, `patches/**`, CLAUDE.md, TECHNICAL.md, README.md or `.claude/skills/**`. The Q9 spec forbids DB fixes, and rule 8 covers the docs. If an oracle finding tempts a fix, record it in SUMMARY.md as Q10/Q11 input instead.
- **No outward action.** Never `git push`.
- Leave these alone and never stage them:
  - `.planning/tci-phase2/` (untracked);
  - the untracked `base-sha.txt` / `baseline-pytest.txt` / `stash-list-before.txt` / `local-state.sha256` files in the c5i, di7, egf, m87, pkh, qsr and sam quick dirs;
  - this task dir's own Step 0 files.
- Another instance may commit concurrently. Commit only each task's `<files>`: `git add -- <paths>`, then `git commit -m "..." -- <paths>`.
- Tests never write to the repo. They write only under pytest's `tmp_path`. Every hermetic test passes an explicit `--packages-dir` / `packages_dir` under `tmp_path` and never reads the real `~/Documents/Max 9/Packages`; only the requires_max class may. Each verify asserts `git status --porcelain` is identical before and after the test run.
- The only command that writes `tests/fixtures/help_io_baseline.json` is the explicit `--write-baseline` run in Task 3.
- The local interpreter is Python 3.14. Avoid 3.11+ APIs: `Path.walk`, `rglob(case_sensitive=...)`, `tomllib`, `typing.Self`, `itertools.batched`, `except*`, `match`. Each task runs the `ast.parse(..., feature_version=(3, 10))` gate on its `.py` files, and Task 3 runs the new tests under uv Python 3.10.
- The interactive shell is zsh. Multi-statement gates are wrapped in `bash -c '...'`. Throwaway files go outside the repo: your session scratchpad, else `mktemp -d`.
</rules>

<open_questions>
This is a decision the report doesn't make (rule 7). The orchestrator must put it to the user before execution and record the answer on the `Answer:` line. If execution starts with no recorded answer, the executor uses the **Recommended** option and lists it in SUMMARY.md as "resolved by default". The tasks are written for the recommended option, and each alternative's delta is stated.

**OQ1. Which boxes does the oracle compare?**

The conflict:
- The Q9 spec says "each **newobj** box".
- Its consumer Q11 says "using the oracle for the values" for spectroscope~, live.scope~, gridmeter~, playlist~, live.adsrui and dict.view. MAX saves all six as UI maxclasses, never as newobj, so a newobj-only oracle has no values for them.
- The review's C2 evidence ("spectroscope~ DB (2,0) vs MAX (2,1) in 24/24 boxes") was evidently measured on UI boxes.

Planning probe, bundle only: 107 non-newobj maxclasses resolve in the DB, and 25 of them mismatch. Examples:

| maxclass | MAX saved | DB | boxes |
|---|---|---|---|
| spectroscope~ | (2,1) | (2,0) | 57/57 |
| live.scope~ | (2,1) | (2,0) | 111/111 |
| dict.view | (1,0) | (1,1) | 70/70 |
| playlist~ | (1,5) | (1,3) | 25/25 |
| live.adsrui | (10,10) | (1,1) | 23/23 |
| gridmeter~ | (1,1) | (1,0) | 6/6 |
| inlet | (0,1) | (1,1) | 1845/1845 |
| outlet | (1,0) | (2,0) | 1629/1629 |

Options:
- A) **(Recommended) newobj boxes, plus non-newobj boxes whose maxclass resolves in the DB.**
  - Non-newobj boxes are keyed by maxclass and compared with no args.
  - They get the same content-defined exclusion (S4), which drops bpatcher, jsui, v8ui and every `*codebox*` maxclass.
  - Full-report entries carry `kinds` (`newobj` / `box`), and the summary splits mismatching names into newobj and other.
  - This gives Q11 its values.
- B) **newobj only**, the literal spec wording.
  - Delta: one guard in the walk (`maxclass != "newobj"` is skipped and not counted as unresolved).
  - Drop the `uiwidget` / `missingui` scan tests and the spectroscope~ evidence check.
  - Q11 must gather UI-object evidence separately.

Answer: A (resolved by default: the user resumed with "continue" and didn't pick an option; record it in SUMMARY.md as resolved by default)
</open_questions>

<observed_facts>
The planner verified these on 2026-10-12 at HEAD `cd5a885`. If a live value differs at execution time, the live value wins; record the difference in SUMMARY.md.

**Repo state:**
- Branch `main`. The staged set is empty and `git stash list` is empty. This task dir was empty at planning (no `base-sha.txt` yet).
- The full suite gives `2691 passed, 1 xfailed, 1 xpassed, 29 warnings in 51.16s` and leaves `git status --porcelain` unchanged.
- `tools/` has no `__init__.py`. Tests import `tools.audit_db` as a namespace package.
- `tools/sync_max_bundle.py:90` imports from `tools.audit_db` at load, so `tools/help_io.py` must never import `tools.audit_db`; a cycle would break the sync tool.
- `audit_db.guard_output_path` refuses only `patches/` and `.claude/max-objects/`, so `tests/fixtures/` is writable through it.
- `audit_db.MAX_PATCHER_DEPTH = 32`.
- `tests/conftest.py` defines `MAX_APP_PATH` (the `MAXPAT_TEST_MAX_APP` seam), registers `requires_max` and `slow`, and skips requires_max items with the reason `requires the Max application bundle at <path> (not found)`. A probe confirmed that `from tests.conftest import MAX_APP_PATH` inside a test returns the same module object pytest loaded.

**Install:**
- Max 9.2.0 (build e9c80e453de) at `/Applications/Max.app`.
- `Contents/Resources/C74` holds 2114 `.maxhelp`, all under `help/` or `packages/*/help|Help/`:
  - `help/`: 976 (max 472, msp 266, jitter 205, m4l 32, resources 1);
  - packages: RNBO 563, BEAP 172 (its dir is `Help`, capital H), Vizzie 114, Jitter Tools 102, ableton-dsp 77, max-mxj 62, Jitter Geometry 26, jit.mo 13, maxforlive-elements 3, mira 3, Node for Max 2, VIDDLL 1.
- Every file parses as JSON, and none is a symlink.
- `~/Documents/Max 9/Packages` holds 17 package dirs. 14 have `.maxhelp` under an immediate `help` child, 1316 files in all:
  - abclib 67, bach 240, CNMAT Externals 58, cv.jit 70, dada 31, ears 103, ease 6, FlowSwing 7, FluidCorpusManipulation 78, grainflow 45, ml.star 17, nn_tilde 4, Rhythm and Time Toolkit 27, RNBO 563.
  - The user RNBO is 1.4.3 and the bundled one 1.4.5; their help files differ.
  - catart-mubu keeps its 18 `.maxhelp` under `patchers/`, and nn_tilde has 4 more there. These are outside help dirs, so they are not scanned (spec).
  - ABL Effect Modules and Max Tutorials have none.
  - Every scanned package has a `package-info.json` with a string `version`.
  - `~/Documents/Max 8/Packages` also exists; Max 9 doesn't load it, so it is not scanned.

**Box shapes:**
- Inner-patcher classnamespace counts: `box` 5060, absent 825, `rnbo` 705, `dsp.gen` 55, `jit.gen` 26.
- 37 gen~ inner patchers carry no classnamespace (old format), so the skip must also match container names (S3).
- newobj boxes, including internals: 59,710. All have int numinlets/numoutlets, 12,332 have no `outlettype`, and 4 have non-string text.
- Help appversions (files): 9.0.0 ×1012, 8.6.5 ×459, 9.0.3 ×122, 9.1.0 ×109, 7.0.3 ×73, 9.0.6 ×60, ... 9.3.0 ×6; 7 files have none.

**Prototype of S2-S6** (newobj only, scratch script, not committed):
- Bundle:
  - 31,685 newobj boxes outside gen/rnbo internals: ~24,000 compared, ~7,350 content-defined, 268 unresolved;
  - 762 internal patchers skipped;
  - **133 literal names (131 alias-resolved) with count mismatches**, 143 literal names with any mismatch, ~2,650 count-mismatching boxes;
  - 13 names with signal-role mismatches: bp.arc.accum-2, bp.arc.knob, gen, mc.adsr~, mc.selector~, mc.stash~, mcs.poly~, mcs.tapout~, pitchshift~, sfrecord~, stash~, stretch~, plus pfft~, which drops out once `_CONTAINER_NAMES` is excluded.
- All sources: 3,430 files, ~39,400 compared boxes. Bundle + 14 packages give a baseline-shaped JSON of ~104 KB at indent 1.
- Scan plus DB load takes ~1.1 s.
- The review's "~119" does not reproduce exactly. Variants gave 98 (core `help/` only) and 111 (boxes with `@attrs` excluded). The figure depends on definition, so no test asserts it.
- The C1 examples reproduce at HEAD:
  - `compute_io_counts` gives `sel 0`→(1,2), `r foo`→(1,1), `unpack`→(1,0), `pack`→(0,1), `route a b`→(1,3), `expr $f1*$f2`→(1,1), `gate~ 3`→(2,1), `unjoin 3`→(1,3), `coll`→(2,4).
  - Help-box signatures (canonical): select args=1 max (2,2) vs db (1,2) ×236; receive args=1 (0,1) vs (1,1) ×481; unpack args=0 (1,2) vs (1,0) ×59; pack args=0 (2,1) vs (0,1) ×27; coll (1,4) vs (2,4) 113/113.
- Help boxes use the aliases heavily: `t` 967 vs `trigger` 17; `r` 476 vs `receive` 14; `sel` 334 vs `select` 200; `b` 40.
- Unresolved non-newobj maxclasses in the bundle: markup 55, gswitch2 12, progress 5, pianoroll 1.

**Code anchors:**
- `Patcher.from_dict` derives args with `box.text.split()[1:]`, keeping `@attr` tokens (`patcher.py:1342-1344`).
- `CONTENT_DEFINED_NAMES` (`patcher.py:35-38`) is p, patcher, bpatcher, gen~, mc.gen~, jit.gen, poly~, mc.poly~, js, jsui, v8, v8ui, node.script. `validation._CONTAINER_NAMES` (`validation.py:81-83`) adds pfft~ and rnbo~.
- `get_outlet_types` returns `signal`, `multichannelsignal` or `""`.
- `lookup()` warns once per name on empty I/O and on `verified_installed:false`.
- `estimate-calibration`: factor 1, 0 samples, confidence low.
</observed_facts>

<settled_decisions>
These were resolved at planning from the Q9 spec, C1/C2/C9, S6, §5.5 and the observed facts. Don't re-litigate them; if something live contradicts one, stop and ask (rule 7).

- **S1: Module layout.**
  - `tools/help_io.py` holds all oracle logic. It imports only the standard library and `src.maxpat` (db_lookup, patcher, validation), never `tools.audit_db`.
  - `tools/audit_db.py` owns the CLI mode, the Info.plist read (`audit_install`), the DB load and the output-path guard.
  - Public API of help_io:
    - `SCHEMA_VERSION = 1`, `MAX_PATCHER_DEPTH = 32`, `DEFAULT_PACKAGES_DIR = Path.home() / "Documents" / "Max 9" / "Packages"`;
    - `GEN_RNBO_CONTAINERS`, `SKIPPED_NAMESPACES`, `CONTENT_DEFINED`;
    - `box_args(text) -> (name, args)`, `signal_class(outlettype) -> "signal" | "control"`;
    - `discover_sources(max_app, packages_dir, bundle_version)`;
    - `scan_help_io(max_app, packages_dir, db, bundle_version) -> dict`;
    - `build_baseline(section) -> dict`, `dump_baseline(baseline) -> str`, `diff_baselines(baseline, live) -> dict`;
    - `format_help_io_summary(envelope, json_path=None, baseline_path=None) -> str`.
- **S2: Sources.**
  - `bundle`: every `*.maxhelp` under `<max-app>/Contents/Resources/C74` (rglob). Its version is the Info.plist short version.
  - `package:<dir name>`: for each immediate subdirectory of `packages_dir`, the `*.maxhelp` under its immediate children whose lowercased name is `help`. Its version is `package-info.json`'s `version` when that is a str, else None.
  - Packages with no help files produce no source.
  - Files are sorted by POSIX path relative to the source root, and that relative path is what reports carry.
  - A missing or unreadable `packages_dir` gives zero package sources plus a reason; it is not an error.
- **S3: Internals skip.** Never descend into a box's inner patcher when the box's name is in `GEN_RNBO_CONTAINERS` = {gen~, mc.gen~, mcs.gen~, gen, jit.gen, jit.pix, jit.gl.pix, rnbo~, mc.rnbo~, mcs.rnbo~}, or when the inner patcher's `classnamespace` is in `SKIPPED_NAMESPACES` = {dsp.gen, jit.gen, rnbo}. Count each skip in `internal_patchers_skipped`. Every other inner patcher (p, bpatcher embeds, classnamespace box or absent) is walked, up to depth 32 (`depth_capped` counter).
- **S4: Content-defined exclusion.** A box is content-defined, counted and not compared, when any of these holds:
  - it has an embedded `patcher` dict;
  - its alias-resolved name is in `CONTENT_DEFINED = CONTENT_DEFINED_NAMES | _CONTAINER_NAMES` (imported from `src.maxpat.patcher` and `src.maxpat.validation`, never copied);
  - its name contains `codebox`.

  Gaps this reveals (pfft~ is excluded only via `_CONTAINER_NAMES`; mxj and mcs.poly~ are compared) are reported in SUMMARY for Q33. Neither set is edited.
- **S5: Args and keys.**
  - newobj: `text.split()`; the name is token 0, and the args are the following tokens up to (not including) the first token starting with `@`.
  - Non-newobj (OQ1-A): the name is the maxclass, and the args are `[]`.
  - This mirrors from_dict's whitespace split except that attributes are not arguments. Q10's quote-aware tokenizer replaces `box_args`; that is a SUMMARY hand-off.
  - Report and baseline keys are the **literal** name (`sel`, `select`, `r`, `t` stay separate), so they don't move when aliases.json changes. The full report adds `canonical`.
- **S6: Comparison.**
  - Count mismatch: saved `(numinlets, numoutlets)` differs from `compute_io_counts`. Signature: `count args=<n> max=<i>,<o> db=<i>,<o>`.
  - Otherwise, when the saved `outlettype` is a list with length equal to numoutlets and numoutlets > 0, compare per-outlet signal class: `signal` and `multichannelsignal` are signal, everything else is control. Signature: `type max=<a/b/..> db=<a/b/..>`.
  - The signal vs multichannelsignal flavour is not compared; this matches C9's signal-vs-control definition.
  - Malformed (non-int or bool counts, non-string or empty newobj text): counted, skipped.
  - Unresolved (`db.lookup(name) is None`): counted per name.
  - Any exception from the DB calls is caught per box and recorded in `compare_errors` (capped at 50). It is never fixed here.
  - DB warnings are suppressed during the scan with `warnings.catch_warnings()` + `simplefilter("ignore")`.
- **S7: Full report** (`--json`, not committed). The envelope is:
  - `mode` (`"help-io"`), `generated_at`, `repo_root`, `max_app`, `packages_dir`;
  - `install`: `audit_install()`;
  - `help_io`: the section.

  The section holds:
  - `available` and `reason`;
  - `sources[sid]`: `kind`, `root`, `version`, `files`, `bad_files` (`file`, `reason`) and `appversions` (`M.m.r` or `unknown` → file count), plus `stats`:
    - `newobj_boxes`, `other_boxes`, `compared`, `content_defined`, `unresolved`, `malformed`;
    - `internal_patchers_skipped`, `depth_capped`, `compare_errors`;
    - `names_compared`, `mismatching_boxes`, `mismatching_names`, `count_mismatch_names`, `type_mismatch_names`;
  - `mismatches[sid][name]` (only names with at least one mismatch): `canonical`, `kinds`, `boxes`, `count_mismatches`, `type_mismatches`, and `signatures[sig]` with `count`, sorted `appversions`, and `examples` (the first 3 in scan order, each `file`/`box`/`text`);
  - `unresolved[sid][name]`, `compare_errors`;
  - `summary`: totals across sources, with literal and alias-resolved mismatching-name counts and the appversion histogram.
- **S8: Baseline** (`build_baseline`). Keys:
  - `schema`: 1;
  - `generator`: `python3 tools/audit_db.py --help-io --write-baseline tests/fixtures/help_io_baseline.json`;
  - `max_version`;
  - `sources[sid]`: `version`, `files`, `boxes_compared`, `mismatching_boxes`, `mismatching_names`;
  - `names[sid][name]`: `boxes`, `count_mismatches`, `type_mismatches`, `signatures` (sig → count);
  - `totals`: `files`, `boxes_compared`, `mismatching_boxes`, `mismatching_names`, `count_mismatch_names`, `type_mismatch_names`.

  It carries no roots, files, examples, appversions, canonical names or timestamps. `dump_baseline` is `json.dumps(b, sort_keys=True, indent=1) + "\n"`.
- **S9: Diff and stale policy.** `diff_baselines` returns:
  - `regressions` / `improvements`: lists of `{source, name, field, baseline, live}`, sorted by (source, name, field), where field is `count_mismatches` or `type_mismatches` and a missing value counts as 0;
  - `compared_sources`, `stale_sources` (`sid → {baseline, live}` versions), `new_sources`, `missing_sources`.

  Rules:
  - Only sources present in both at an equal version are compared.
  - The live test skips (doesn't fail) when `bundle` is stale, with a re-baseline instruction. A Max update is not a framework regression, and the skip is visible in `-rs`.
  - Stale packages are reported and excluded.
- **S10: CLI.** New flags: `--help-io` (store_true), `--packages-dir` (default `DEFAULT_PACKAGES_DIR`) and `--write-baseline PATH`.
  - `--write-baseline` without `--help-io` is a parser error (exit 2).
  - Both output paths are screened by `guard_output_path` before any work (exit 2 on refusal, nothing written).
  - `--json` in help-io mode writes the help-io envelope.
  - An unavailable section plus `--write-baseline` gives exit 1, with an error on stderr and nothing written.
  - Otherwise the exit is 0, including a missing bundle (reported as unavailable, like the default audit).
  - Without `--help-io`, behavior is byte-for-byte unchanged.
- **S11: Tests** live in `tests/test_help_io.py`.
  - Hermetic tests build a fake Max.app (Info.plist via plistlib, as `tests/test_audit_db.py::_make_fake_bundle` does) and a fake DB in `tmp_path`: `max/objects.json`, plus `overrides.json` with `variable_io_rules` where needed. They never touch the real DB values, so Q10/Q11 DB fixes can't break them.
  - The live class is `@pytest.mark.requires_max` and uses `from tests.conftest import MAX_APP_PATH` with the default packages dir.
- **S12: Docs.** Only the `tools/audit_db.py` module docstring changes:
  - the read-only contract names both outputs;
  - a help-io mode note;
  - usage lines.

  The CLAUDE.md:59 re-sync procedure, TECHNICAL.md and `.claude/skills/references/shared-capabilities.md` are listed as doc impact in SUMMARY, not edited (rule 8).
</settled_decisions>

<source_audit>
| Source item (Q9 spec) | Covered by |
|---|---|
| New command `python3 tools/audit_db.py --help-io` | Task 1 (tracer), Task 2 |
| Scan every `.maxhelp` in the bundle and the installed packages' help dirs | Task 1 (bundle), Task 2 (packages, S2) |
| Skip gen~, rnbo~ and jit.gen internals | Task 2 (S3) |
| Compare saved numinlets/numoutlets/outlettype against `compute_io_counts(name, args)` and the DB port types | Task 1 (counts), Task 2 (signal class, args, OQ1) |
| Output: JSON plus a summary (mismatching names, box counts, Max versions) | Task 1 (skeleton), Task 2 (full S7 report, appversions) |
| Baseline `tests/fixtures/help_io_baseline.json` committed | Task 3 |
| Test fails when mismatches increase; skips without Max.app | Task 3 (TestLiveOracle, requires_max) |
| Diff logic unit-tested on a tiny fixture | Task 1 (basic), Task 3 (mini fixture, S9) |
| Expect ~119 mismatching names | Task 3: actual figures recorded, definition explained (observed facts) |
| Do not fix DB entries | Rules addition + Task 3 diff gate on `.claude/max-objects/` and `src/` |
| Orchestrator notes: deterministic, reasonably sized baseline; live scan run by the executor | S8, Task 3 (determinism and size tests, explicit write run) |
</source_audit>

<context>
CLAUDE.md is already loaded as project instructions. Don't re-read it, and don't edit it.

Read only these ranges:
- `.planning/reviews/2026-10-11-repo-review.md`: lines 83-84 (C1, C2), 91 (C9), 197 (S6) and 395-399 (§5.5 bundle mining). This satisfies rule 1.
- `.planning/reviews/2026-10-11-fix-plan.md`: lines 17-31 (rules), 180-189 (Q9), 191-233 (Q10/Q11, the consumers: what evidence they need) and 657-670 (Q38: per-version I/O).
- `tools/audit_db.py`:
  - 1-100: docstring, imports, constants, SECTION_KEYS;
  - 103-141: guard_output_path;
  - 210-271: `_split_short_version`, `audit_install`;
  - 624-652: `_git`, `_walk_boxes`, for the depth-cap idiom;
  - 836-901: `_unavailable`, `run_audit`;
  - 904-975: `_headline`, `format_summary`;
  - 983-1053: `build_parser`, `main`.
- `src/maxpat/db_lookup.py`: 342-384 (`lookup`), 765-880 (`compute_io_counts`, `_apply_io_formula`), 882-943 (`get_outlet_types`).
- `src/maxpat/patcher.py`: 32-38 (`CONTENT_DEFINED_NAMES`) and 1340-1350 (from_dict arg split). `src/maxpat/validation.py`: 81-83 (`_CONTAINER_NAMES`).
- `tests/conftest.py` (all, ~120 lines). `tests/test_audit_db.py`: 1-150 (fixture builders, minimal fake DB) and 656-700 (TestCLI subprocess pattern).
</context>

<tasks>

<task type="tracer" tdd="true">
  <name>Task 1: Help-box oracle end to end on one path. A fake-bundle .maxhelp goes through the compute_io_counts count comparison, the --help-io summary and JSON, --write-baseline, and a diff_baselines regression; the real 9.2.0 bundle runs through the same command</name>
  <files>tools/help_io.py, tools/audit_db.py, tests/test_help_io.py</files>
  <read_first>.planning/reviews/2026-10-11-repo-review.md (lines 83-84, 91, 197, 395-399), .planning/reviews/2026-10-11-fix-plan.md (lines 17-31, 180-233), tools/audit_db.py (ranges in context), src/maxpat/db_lookup.py (765-943), tests/conftest.py, tests/test_audit_db.py (1-150, 656-700)</read_first>
  <behavior>
    Module helpers in `tests/test_help_io.py`. Tasks 2 and 3 reuse and extend them.
    - `REPO_ROOT`.
    - `_make_fake_max(tmp_path, version="9.9.9")` writes `Max.app/Contents/Info.plist` with `CFBundleShortVersionString` `"<version> (abc123)"` and `CFBundleVersion`, and creates `Contents/Resources/C74/help/max/`. It returns the app path.
    - `_make_fake_db(tmp_path)` writes `db/max/objects.json` with `alpha` (1 control inlet, 2 control outlets) and returns the db root.
    - `_newobj(box_id, text, numinlets, numoutlets, outlettype=None, patcher=None)` and `_help(boxes, appversion=(9, 1, 0), classnamespace="box")` build the dicts.
    - `_write(path, data)` writes JSON after mkdir.
    - `_cli(*args)` runs `[sys.executable, "tools/audit_db.py", *args]` with `cwd=REPO_ROOT`, `capture_output=True`, `text=True`, `check=False`.

    TestTracer:
    - `test_cli_end_to_end`:
      - Setup: `help/max/alpha.maxhelp` holds `alpha` saved (1,2) and `alpha 5` saved (1,3).
      - Run `_cli("--help-io", "--max-app", app, "--db-root", db, "--packages-dir", tmp/"no-packages", "--json", J, "--write-baseline", BL)`, with J and BL under tmp_path.
      - It exits 0. stdout contains `MAX help-box I/O oracle` and `Max 9.9.9`.
      - J: `mode == "help-io"`, `help_io.available` is True, and `help_io.mismatches.bundle.alpha` has `boxes == 2` and `count_mismatches == 1`, with signature key `count args=1 max=1,3 db=1,2` (count 1, example file `help/max/alpha.maxhelp`, box id and text).
      - BL: `schema == 1`, `sources.bundle.version == "9.9.9"`, `names.bundle.alpha.count_mismatches == 1`, and BL's text equals `help_io.dump_baseline(json.loads(text))`.
    - `test_diff_flags_an_increase_and_an_improvement`:
      - `diff_baselines(BL, BL)` has no regressions or improvements, and `compared_sources == ["bundle"]`.
      - With a deepcopy whose alpha `count_mismatches` is 0 as the baseline, the diff against BL is exactly one regression `{"source": "bundle", "name": "alpha", "field": "count_mismatches", "baseline": 0, "live": 1}`.
      - With the arguments swapped, it is exactly one improvement.

    RED: `tools/help_io.py` doesn't exist and `--help-io` is an unknown argument.
  </behavior>
  <action>
    Implements the Q9 "New command", "Compare" (counts), "Output" and "Baseline" bullets as a thin, production-quality slice, per S1, S5, S6 (counts only here), S8, S9 (compared sources only here) and S10.

    Step 0, baseline (rule 4). Set `Q=.planning/quick/261012-ubw-implement-q9-in-planning-reviews-2026-10`.
    - If `$Q/base-sha.txt` is absent, write `git rev-parse HEAD` into it. If `$Q/stash-list-before.txt` is absent, write `git stash list` into it (expected empty). If HEAD moved from `cd5a885`, record that in SUMMARY.md and continue.
    - Run `python3 -m pytest -q -p no:cacheprovider`. Write its final summary line to `$Q/baseline-pytest.txt` (expected `2691 passed, 1 xfailed, 1 xpassed, 29 warnings`).
    - Record `git diff --cached --name-only` (expected empty) in the SUMMARY notes.
    - None of these files is ever staged.

    RED:
    1. Create `tests/test_help_io.py` with the helpers and TestTracer from `<behavior>`. Its module docstring cites quick 261012-ubw, Q9, C1/C2/C9, S6 and §5.5, and states:
       - hermetic tests use fake bundles and a fake DB under `tmp_path` and always pass an explicit packages dir;
       - only the requires_max class (Task 3) reads the real bundle;
       - tests never write to the repo.
    2. Run `python3 -m pytest -q -p no:cacheprovider tests/test_help_io.py` and record the red counts.

    GREEN:
    3. Create `tools/help_io.py`. The module docstring covers: purpose (help-box I/O oracle; Q10/Q11/Q38 consume it); read-only (it reads JSON only, never executes Max or package code, and writes nothing itself); and the S5/S6 comparison definition.
       - Add `from __future__ import annotations`, the S1 constants and the `ROOT` sys.path insert mirroring audit_db.
       - `box_args` per S5.
       - `discover_sources`: the bundle source only for now. Package discovery lands in Task 2, but keep the `packages_dir` parameter.
       - `scan_help_io`:
         - per file: `read_bytes` + `json.loads`, catching `(OSError, ValueError)` into `bad_files`; a non-dict top level is a bad file;
         - a recursive walk of `patcher.boxes` with a depth guard of `MAX_PATCHER_DEPTH`;
         - newobj boxes: content-defined if they have an embedded `patcher`, else unresolved when `db.lookup` is None, else compared by counts;
         - aggregation into the S7 section shape (fields Task 2 will fill may start at 0).
       - `build_baseline`, `dump_baseline` and `diff_baselines` per S8/S9.
       - `format_help_io_summary`: a header line `MAX help-box I/O oracle  (<generated_at>)`, then `install` (`Max <short_version> (build <id>)`), `sources`, `boxes`, `mismatching` and per-source lines; or `help-box I/O : unavailable (<reason>)`.
    4. Edit `tools/audit_db.py`:
       - import help_io with `from tools import help_io  # noqa: E402` after the src imports;
       - add `run_help_io(repo_root=None, db_root=None, max_app=None, packages_dir=None)`. It builds the S7 envelope, calls `audit_install`, loads `ObjectDatabase(db_root=...)` (a load failure gives an unavailable section, never a raise) and an unavailable section when `install.available` is False;
       - add the S10 flags and the `main()` dispatch;
       - update the module docstring per S12.

       The default path (no `--help-io`) must stay untouched.
    5. Run the verify. Then commit: `git add -- tools/help_io.py tools/audit_db.py tests/test_help_io.py`, then `git commit -m "feat(audit): audit_db.py --help-io compares MAX help-box I/O with compute_io_counts; JSON report, summary, canonical baseline and baseline diff (Q9)" -- tools/help_io.py tools/audit_db.py tests/test_help_io.py`.
  </action>
  <verify>
    <automated>bash -c 'B=$(git status --porcelain); python3 -m pytest -q -p no:cacheprovider tests/test_help_io.py tests/test_audit_db.py tests/test_sync_max_bundle.py || exit 1; [ "$B" = "$(git status --porcelain)" ] || { echo TREE-CHANGED-BY-TESTS; exit 1; }; SCR=$(mktemp -d); python3 tools/audit_db.py --help-io --json "$SCR/h.json" > "$SCR/out.txt" || exit 1; grep -q "MAX help-box I/O oracle" "$SCR/out.txt" || exit 1; python3 -c "import json,sys; s=json.load(open(sys.argv[1]))[\"help_io\"]; assert s[\"available\"], s; b=s[\"sources\"][\"bundle\"]; assert b[\"files\"] > 2000, b[\"files\"]; print(\"REAL-BUNDLE\", b[\"version\"], b[\"files\"], \"files\", len(s[\"mismatches\"][\"bundle\"]), \"mismatching names\")" "$SCR/h.json" || exit 1; rm -rf "$SCR"; echo TRACER-GREEN'</automated>
    <automated>python3 -c "import ast,sys; [ast.parse(open(f).read(), filename=f, feature_version=(3, 10)) for f in sys.argv[1:]]; print('PY310-SYNTAX-OK')" tools/help_io.py tools/audit_db.py tests/test_help_io.py</automated>
  </verify>
  <done>Both TestTracer tests are green, after a recorded red. test_audit_db.py and test_sync_max_bundle.py are unchanged and green. The real bundle run reports Max 9.2.0 and over 2000 files. The tests leave `git status` unchanged. There is one commit with `(Q9)` touching exactly the three files.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Full scan semantics. Installed packages' help dirs; gen~/rnbo~/jit.gen internals skipped; content-defined, unresolved and malformed boxes counted; positional args before @; signal-role comparison; OQ1 non-newobj boxes; signatures with appversions and examples; complete S7 report and summary</name>
  <files>tools/help_io.py, tools/audit_db.py, tests/test_help_io.py</files>
  <read_first>tools/help_io.py (as committed by Task 1), src/maxpat/patcher.py (32-38, 1340-1350), src/maxpat/validation.py (81-83), src/maxpat/db_lookup.py (882-943), .planning/reviews/2026-10-11-repo-review.md (line 91, C9)</read_first>
  <behavior>
    Extend `_make_fake_db` with these objects, all in `max/objects.json` and keeping `alpha`:
    - `vfoo`: `variable_io: true`, 1 inlet, 2 outlets. `overrides.json` gives it `variable_io_rules` `{"vfoo": {"inlet_count": "fixed:1", "outlet_count": "arg_count"}}`.
    - `sigout~`: 1 outlet, control (`signal: false`).
    - `mcout~`: 1 outlet, `signal: true`.
    - `uiwidget`: (1,1).
    - `js`: (1,1), present in the DB to prove the exclusion beats the lookup.
    - `emptyio`: inlets `[]`, outlets `[]` (would warn on lookup).

    TestScan, calling `help_io.scan_help_io(app, pkgs, ObjectDatabase(db_root=db), "9.9.9")` directly. Bundle file `help/max/scan.maxhelp` (appversion 9.1.0) holds:
    1. `alpha` saved (1,2): compared, no mismatch.
    2. `alpha 5` saved (1,3): count mismatch, signature `count args=1 max=1,3 db=1,2`.
    3. `vfoo a b @attr 1` saved (1,2): compared, no mismatch. This proves args stop at the first `@`; with the attr tokens it would predict 4.
    4. `sigout~` saved (1,1), outlettype `["signal"]`: type mismatch, signature `type max=signal db=control`.
    5. `mcout~` saved (1,1), outlettype `["multichannelsignal"]`: no mismatch (mc collapses to signal).
    6. `sigout~` saved (1,1) with no outlettype: compared, no type check.
    7. `nosuch 1`: `unresolved.bundle.nosuch == 1`, not compared.
    8. `js foo.js` saved (1,3): content-defined.
    9. `p sub` with an embedded patcher (classnamespace `box`) holding `alpha 7` saved (1,9): the p box is content-defined, and the inner box is compared and mismatches.
    10. `gen~` with an inner patcher (classnamespace `dsp.gen`) holding `alpha 9` saved (1,9): not walked.
    11. `gen~` with an inner patcher with no classnamespace, holding `alpha 9`: not walked (name rule).
    12. `rnbo~` with classnamespace `rnbo`, holding `alpha 9`: not walked.

        For 10-12, `internal_patchers_skipped == 3` and no `alpha 9` signature exists.
    13. A newobj with `numinlets: "x"`, and another with `numoutlets: true` (bool is not an int count): both malformed.
    14. A newobj with empty text `""`, and another whose `text` is the int `5`: both malformed.
    15. OQ1-A boxes: a box with maxclass `uiwidget`, saved (1,2), is compared and mismatches under key `uiwidget` with `kinds == ["box"]`. Maxclass `missingui` is unresolved. Maxclass `v8.codebox` is content-defined.
    16. `emptyio` saved (0,0): compared, and the scan records no warnings.

    Check the counters: `compared`, `content_defined`, `unresolved`, `malformed`, `internal_patchers_skipped`, `newobj_boxes`, `other_boxes`. Then check:
    - `mismatches.bundle.alpha`: `count_mismatches == 2` (boxes 2 and 9), `canonical == "alpha"`, `kinds == ["newobj"]`. The signature's `appversions` is `["9.1.0"]`, and its examples are at most 3, carrying `file` `help/max/scan.maxhelp`.
    - `warnings.catch_warnings(record=True)` around the scan records nothing.

    More TestScan cases:
    - Second bundle file `packages/BPkg/help/b.maxhelp`, plus an invalid-JSON file `help/max/broken.maxhelp` and a top-level JSON list `help/max/list.maxhelp`.
      - b.maxhelp is counted in `bundle`.
      - The two bad files land in `sources.bundle.bad_files` with their relative paths, and the scan continues.
      - `sources.bundle.appversions` counts `9.1.0` and `unknown` (a file with no appversion).
    - Packages dir under tmp_path:
      - `UserPkg/package-info.json` (`{"version": "1.2.3"}`) and `UserPkg/help/u.maxhelp` with `alpha 5` saved (1,3) give source `package:UserPkg`, version `1.2.3`, with that mismatch.
      - `UserPkg/patchers/x.maxhelp` is not scanned.
      - `CapPkg/Help/c.maxhelp` (no package-info) gives `package:CapPkg`, version None.
      - `EmptyPkg/` with no help dir gives no source.
      - A nonexistent packages dir gives zero package sources and still a valid section.
    - Depth cap: 40 nested `p` patchers, the deepest holding `alpha 5` saved (1,3), give no exception and `depth_capped >= 1`.
    - Determinism: two scans of the same tree give equal `dump_baseline(build_baseline(section))` bytes.

    TestCliModes:
    - A missing bundle (`--max-app tmp/absent.app`) exits 0, and stdout says `unavailable`.
    - The summary of the TestScan tree lists `package:UserPkg`, a `help versions` line containing `9.1.0`, and a `mismatching` line.

    RED: Task 1's scanner has no packages, skip rules, type comparison, @-stripping, OQ1 boxes or counters.

    OQ1-B delta: drop case 15. Non-newobj boxes are not counted anywhere.
  </behavior>
  <action>
    Implements the Q9 "Scan" bullet (packages, the internals skip) and the rest of the "Compare" and "Output" bullets, per S2-S7 and OQ1 (Recommended A if unanswered). It builds out from the Task 1 slice without changing its public signatures.

    RED:
    1. Add the TestScan and TestCliModes cases from `<behavior>` to `tests/test_help_io.py`, then run `python3 -m pytest -q -p no:cacheprovider tests/test_help_io.py` and record the red counts.

    GREEN:
    2. In `tools/help_io.py`:
       - `discover_sources` gains package discovery per S2. Catch `PermissionError`/`OSError` on `iterdir` and record a `packages_reason`.
       - Constants: `GEN_RNBO_CONTAINERS`, `SKIPPED_NAMESPACES`, and `CONTENT_DEFINED` imported per S4.
       - The walk applies the order: malformed check, content-defined check, unresolved check, compare. It recurses per S3.
       - `signal_class` and the S6 type comparison, run only when counts match.
       - Wrap the whole scan in `warnings.catch_warnings()` with `simplefilter("ignore")`, and catch per-box exceptions into `compare_errors` (cap 50; the counter keeps counting).
       - Fill every S7 stats field, the signature `appversions` / `examples` (first 3, deterministic scan order), `unresolved`, and the cross-source `summary`:
         - literal and alias-resolved (`db._aliases.get(name, name)`, as `patcher.py` does) mismatching-name counts;
         - count- and type-mismatch name counts;
         - the appversion histogram.
       - Extend `format_help_io_summary`:
         - an `install` line;
         - a `sources` line (bundle files; N packages and files; the packages dir or its reason);
         - a `boxes` line (compared, content-defined, unresolved, malformed, internal patchers skipped, bad files);
         - a `mismatching` line (names; alias-resolved; count; signal-role; newobj vs other per OQ1; boxes);
         - a `help versions` line (top 5 appversions by file count, then `(+N more)`);
         - one line per source (sid, version or `-`, files, compared, mismatching names, mismatching boxes);
         - a `top names` line (the 10 literal names with the most mismatching boxes, as `name mismatching/boxes`).
    3. `tools/audit_db.py` needs only what `run_help_io` must pass through (the packages dir default and the reason). Keep the default audit path untouched.
    4. Run the verify. Then commit: `git commit -m "feat(audit): help-io scans installed packages' help dirs, skips gen~/rnbo~/jit.gen internals and content-defined boxes, compares signal roles, records signatures, examples and help appversions (Q9)" -- tools/help_io.py tools/audit_db.py tests/test_help_io.py`, after `git add --` of the same paths.
  </action>
  <verify>
    <automated>bash -c 'B=$(git status --porcelain); python3 -m pytest -q -p no:cacheprovider tests/test_help_io.py tests/test_audit_db.py tests/test_sync_max_bundle.py || exit 1; [ "$B" = "$(git status --porcelain)" ] || { echo TREE-CHANGED-BY-TESTS; exit 1; }; SCR=$(mktemp -d); python3 tools/audit_db.py --help-io --json "$SCR/h.json" > "$SCR/out.txt" || exit 1; cat "$SCR/out.txt"; python3 -c "import json,sys; s=json.load(open(sys.argv[1]))[\"help_io\"]; b=s[\"sources\"][\"bundle\"][\"stats\"]; assert b[\"internal_patchers_skipped\"] > 0 and b[\"content_defined\"] > 0 and b[\"unresolved\"] > 0, b; pk=[k for k in s[\"sources\"] if k.startswith(\"package:\")]; assert pk, \"no package sources\"; print(\"SOURCES\", len(s[\"sources\"]), \"MISMATCHING\", s[\"summary\"][\"mismatching_names\"], \"COUNT-NAMES\", s[\"summary\"][\"count_mismatch_names\"])" "$SCR/h.json" || exit 1; rm -rf "$SCR"; echo SCAN-GREEN'</automated>
    <automated>python3 -c "import ast,sys; [ast.parse(open(f).read(), filename=f, feature_version=(3, 10)) for f in sys.argv[1:]]; print('PY310-SYNTAX-OK')" tools/help_io.py tools/audit_db.py tests/test_help_io.py</automated>
  </verify>
  <done>
    - Every TestScan and TestCliModes case is green, after a recorded red.
    - The real run lists the bundle plus package sources (planning saw 14). It shows non-zero internal-skip, content-defined and unresolved counters, and figures in the planning range: ~24k compared bundle boxes, ~130-145 bundle mismatching names.
    - The tests leave `git status` unchanged.
    - There is one `(Q9)` commit touching only the three files.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Committed baseline and regression test. Diff semantics are unit-tested on the tiny committed fixture; --write-baseline is hardened; the live scan writes tests/fixtures/help_io_baseline.json; a requires_max test fails when mismatches increase and skips without Max.app</name>
  <files>tools/help_io.py, tools/audit_db.py, tests/test_help_io.py, tests/fixtures/help_io_mini_baseline.json, tests/fixtures/help_io_baseline.json</files>
  <read_first>tools/help_io.py and tests/test_help_io.py (as committed by Task 2), tools/audit_db.py (main, guard_output_path), tests/conftest.py</read_first>
  <behavior>
    `tests/fixtures/help_io_mini_baseline.json`, hand-written in canonical form:
    - `schema` 1, `max_version` `9.9.9`;
    - `sources.bundle` version `9.9.9` and `sources["package:Demo"]` version `1.0.0`, each with plausible `files` / `boxes_compared` / `mismatching_*`;
    - `names.bundle.alpha`: boxes 4, count 2, type 0, signatures `{"count args=0 max=1,2 db=1,0": 2}`;
    - `names.bundle["beta~"]`: boxes 3, count 0, type 1, `{"type max=signal db=control": 1}`;
    - `names["package:Demo"]["demo.obj"]`: boxes 2, count 1, type 0, `{"count args=1 max=2,1 db=1,1": 1}`;
    - a `generator` naming it a test fixture, and `totals`.

    TestDiff (no Max), all on deepcopies of the loaded mini fixture:
    1. Identical: no regressions or improvements; `compared_sources == ["bundle", "package:Demo"]`.
    2. alpha count 2→3: exactly one regression, field `count_mismatches`, 2→3.
    3. beta~ type 1→2: one regression, field `type_mismatches`.
    4. New name `gamma` in bundle with count 1: one regression, baseline 0.
    5. alpha removed from live: one improvement, no regression.
    6. Live `package:Demo` version `1.0.1` with demo.obj count 1→5: no regression; `stale_sources == {"package:Demo": {"baseline": "1.0.0", "live": "1.0.1"}}`.
    7. Live adds `package:New` with mismatches: `new_sources == ["package:New"]`, no regression.
    8. Live lacks `package:Demo`: `missing_sources == ["package:Demo"]`.
    9. A `boxes` change alone is not a regression.
    10. Several regressions come back sorted by (source, name, field).
    11. `schema` 2 on either side raises ValueError.
    12. The mini fixture's text equals `dump_baseline(json.loads(text))`.

    TestBaselineOutput (fake trees from Task 2's helpers):
    - The dump contains no `str(tmp_path)`, no `str(Path.home())`, and no `generated_at` / `root` / `examples` / `appversions` key.
    - Only names with at least one mismatch appear, and each name's signature counts sum to count + type mismatches.
    - CLI:
      - `--write-baseline` twice gives identical bytes.
      - `--write-baseline <tmp repo>/patches/x.json` (with `--repo-root` at a tmp fake repo, per test_audit_db's `_make_fake_repo`) exits 2, writes nothing, and stderr says `refusing to write`.
      - `--write-baseline` without `--help-io` exits 2.
      - `--help-io --write-baseline` with a missing bundle exits 1 and writes nothing.

    TestCommittedBaseline (no Max; runs in CI), on `tests/fixtures/help_io_baseline.json`:
    - it exists, `schema == 1`, and `max_version` is a str;
    - its text equals `dump_baseline(json.loads(text))`;
    - it is under 400_000 bytes;
    - it contains no `/Users/`, `/Applications/`, `/home/` or `generated_at`;
    - every `names` source key is in `sources`;
    - every entry has `count_mismatches + type_mismatches > 0`, and its signature counts sum to that.

    TestLiveOracle (`@pytest.mark.requires_max`). A class-scoped fixture runs `audit_db.run_help_io(max_app=MAX_APP_PATH)` (default DB and packages dir) once and builds the live baseline.
    - `test_mismatches_do_not_increase`:
      - load the committed baseline and diff;
      - if `bundle` is in `stale_sources`, `pytest.skip` with `help-io baseline recorded against Max <b>, installed <l>: re-run python3 tools/audit_db.py --help-io --write-baseline tests/fixtures/help_io_baseline.json`;
      - otherwise assert no regressions. The failure message lists up to 20 as `source/name field baseline->live`, plus the inspect command `python3 tools/audit_db.py --help-io --json <path>`.
    - `test_a_regression_is_detected_on_live_data`: same stale skip. Take a deepcopy of the committed baseline, decrement the first (sorted) bundle name's larger nonzero field by 1, and assert the diff against live is exactly one regression for that name and field. Skip if bundle has no names.

    RED:
    - The mini fixture and both baseline files are missing.
    - Task 1/2's diff lacks the stale/new/missing classification and the schema check.
    - The `--write-baseline` guard, ordering and unavailable cases are untested or failing.
  </behavior>
  <action>
    Implements the Q9 "Baseline" and "Test" bullets and the tiny-fixture diff tests, per S8-S11.

    RED:
    1. Write `tests/fixtures/help_io_mini_baseline.json` from `<behavior>`, with sorted keys, indent 1 and a trailing newline.
    2. Add TestDiff, TestBaselineOutput, TestCommittedBaseline and TestLiveOracle to `tests/test_help_io.py`. Import `MAX_APP_PATH` via `from tests.conftest import MAX_APP_PATH`, and set `BASELINE = REPO_ROOT / "tests" / "fixtures" / "help_io_baseline.json"`.
    3. Run `python3 -m pytest -q -p no:cacheprovider -rs tests/test_help_io.py` and record the red counts.

    GREEN:
    4. Complete `diff_baselines` per S9: the schema check, stale/new/missing classification, sorted output and missing-equals-0. Finish the S10 write path in `tools/audit_db.py`:
       - screen both paths before work;
       - an unavailable section gives exit 1 and nothing written;
       - `parser.error` when `--write-baseline` comes without `--help-io`;
       - the summary echoes `baseline : <path>` and `json : <path>`.
    5. Produce the committed baseline from the real install. The DB is unchanged since base:
       - `python3 tools/audit_db.py --help-io --json "$SCR/help-io.json" --write-baseline tests/fixtures/help_io_baseline.json`;
       - then `--write-baseline "$SCR/again.json"`, which must `cmp` equal.

       Spot-check the evidence with a scratch Python one-liner; it is not a committed test, so Q10/Q11 can shrink the baseline freely. `names.bundle` must contain:
       - `sel` with `count args=1 max=2,2 db=1,2`;
       - `r` with `count args=1 max=0,1 db=1,1`;
       - `unpack` with `count args=0 max=1,2 db=1,0`;
       - `pack` with `count args=0 max=2,1 db=0,1`;
       - `route` and `coll` with count mismatches;
       - `sfrecord~` and `pitchshift~` with type mismatches;
       - (OQ1-A) `spectroscope~` with `count args=0 max=2,1 db=2,0`.

       If any is absent, stop and investigate before committing; never edit the baseline by hand. Keep the full JSON report in the scratchpad for SUMMARY figures.
    6. Run the full verify. Then commit: `git add -- tools/help_io.py tools/audit_db.py tests/test_help_io.py tests/fixtures/help_io_mini_baseline.json tests/fixtures/help_io_baseline.json`, then `git commit -m "test(audit): committed Max 9.2.0 help-box I/O baseline and a requires_max regression test that fails when mismatches increase; diff logic unit-tested on a tiny fixture (Q9)" -- <same five paths>`.
  </action>
  <verify>
    <automated>bash -c 'B=$(git status --porcelain); SCR=$(mktemp -d); python3 -m pytest -q -p no:cacheprovider -rs tests/test_help_io.py > "$SCR/all.txt" 2>&1 || { tail -40 "$SCR/all.txt"; exit 1; }; python3 -m pytest -q -p no:cacheprovider -rs "tests/test_help_io.py::TestLiveOracle" > "$SCR/live.txt" 2>&1 || { tail -40 "$SCR/live.txt"; exit 1; }; tail -1 "$SCR/live.txt" | grep -q "2 passed" || { tail -5 "$SCR/live.txt"; echo LIVE-ORACLE-NOT-2-PASSED; exit 1; }; tail -1 "$SCR/live.txt" | grep -q "skipped" && { echo LIVE-ORACLE-SKIPPED-ON-THIS-MAC; exit 1; }; MAXPAT_TEST_MAX_APP=/nonexistent/Max.app python3 -m pytest -q -p no:cacheprovider -rs tests/test_help_io.py > "$SCR/nomax.txt" 2>&1 || { tail -40 "$SCR/nomax.txt"; exit 1; }; grep -q "requires the Max application bundle" "$SCR/nomax.txt" || { echo NO-REQUIRES-MAX-SKIP; exit 1; }; [ "$B" = "$(git status --porcelain)" ] || { echo TREE-CHANGED-BY-TESTS; exit 1; }; python3 tools/audit_db.py --help-io --write-baseline "$SCR/again.json" > /dev/null || exit 1; cmp -s "$SCR/again.json" tests/fixtures/help_io_baseline.json || { echo BASELINE-NOT-REPRODUCIBLE; exit 1; }; echo "help_io: $(tail -1 "$SCR/all.txt") | no-max: $(tail -1 "$SCR/nomax.txt")"; rm -rf "$SCR"; echo BASELINE-GREEN'</automated>
    <automated>bash -c 'B=$(git status --porcelain); SCR=$(mktemp -d); python3 -m pytest -q -p no:cacheprovider > "$SCR/full.txt" 2>&1; RC=$?; tail -1 "$SCR/full.txt"; [ "$RC" -eq 0 ] || { tail -40 "$SCR/full.txt"; echo FULL-SUITE-RED; exit 1; }; [ "$B" = "$(git status --porcelain)" ] || { echo TREE-CHANGED-BY-SUITE; exit 1; }; rm -rf "$SCR"; echo FULL-SUITE-GREEN'</automated>
    <automated>bash -c 'Q=.planning/quick/261012-ubw-implement-q9-in-planning-reviews-2026-10; BASE=$(cat $Q/base-sha.txt); git diff --quiet "$BASE" HEAD -- .claude/max-objects src patches CLAUDE.md TECHNICAL.md README.md .claude/skills && git diff --quiet -- .claude/max-objects src patches CLAUDE.md TECHNICAL.md README.md .claude/skills || { echo PROTECTED-TREE-CHANGED; exit 1; }; L=$(git log --oneline "$BASE"..HEAD) || { echo GIT-LOG-FAILED; exit 1; }; N=$(printf "%s\n" "$L" | grep -c "(Q9)"); [ "$N" -ge 3 ] || { echo "ONLY $N Q9 COMMITS"; exit 1; }; [ "$(git stash list)" = "$(cat $Q/stash-list-before.txt)" ] || { echo STASH-LIST-CHANGED; exit 1; }; python3 -c "import ast,sys; [ast.parse(open(f).read(), filename=f, feature_version=(3, 10)) for f in sys.argv[1:]]; print(\"PY310-SYNTAX-OK\")" tools/help_io.py tools/audit_db.py tests/test_help_io.py || exit 1; SCR=$(mktemp -d); if command -v uv >/dev/null && uv venv -q --python 3.10 "$SCR/v" && uv pip install -q --python "$SCR/v/bin/python" -r requirements-dev.txt; then mkdir -p "$SCR/home"; HOME="$SCR/home" MAXPAT_TEST_MAX_APP=/nonexistent/Max.app "$SCR/v/bin/python" -m pytest -q -p no:cacheprovider -rs tests/test_help_io.py tests/test_audit_db.py > "$SCR/out.txt" 2>&1 || { tail -40 "$SCR/out.txt"; exit 1; }; grep -q "requires the Max application bundle" "$SCR/out.txt" || { echo NO-REQUIRES-MAX-SKIP-310; exit 1; }; echo "PY310: $(tail -1 "$SCR/out.txt")"; else echo UV-PY310-UNAVAILABLE; fi; rm -rf "$SCR"; echo GATES-GREEN'</automated>
  </verify>
  <done>
    - All TestDiff, TestBaselineOutput and TestCommittedBaseline cases are green after a recorded red.
    - TestLiveOracle passes on this Mac and is not skipped. Under `MAXPAT_TEST_MAX_APP=/nonexistent/Max.app` it skips with the requires_max reason.
    - `tests/fixtures/help_io_baseline.json` reproduces byte-for-byte from a fresh run, is under 400 KB, and holds the spot-checked evidence.
    - The full suite is green: 2691 base plus the new tests, 1 xfailed, 1 xpassed, and the warning count recorded.
    - The protected trees are unchanged since base, there are at least 3 `(Q9)` commits, and the stash list is unchanged.
    - The 3.10 run is green, or `UV-PY310-UNAVAILABLE` is recorded in SUMMARY.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Max bundle and third-party packages -> scanner | `.maxhelp` JSON from Cycling '74 and from user-installed third-party packages is parsed. |
| CLI arguments -> filesystem writes | `--json` and `--write-baseline` paths become file writes. |
| Local machine -> committed fixture | The baseline is generated from this Mac and committed to a shared repo. |
| Baseline -> regression gate | The committed baseline decides what counts as a regression. |
| Test run -> repo working tree | Tests run next to user-confirmed patches and the DB. |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-ubw-01 | Denial of Service | `help_io.scan_help_io` on malformed or deeply nested package help files | low | mitigate | Per-file `(OSError, ValueError)` handling into `bad_files`; non-dict tops tallied; depth cap 32 (`depth_capped`); per-box DB exceptions caught into a capped `compare_errors`. Tests cover broken JSON, a JSON list and 40-deep nesting. |
| T-ubw-02 | Tampering | `--write-baseline` / `--json` writing into `patches/` or `.claude/max-objects/` | medium | mitigate | Both paths are screened by `guard_output_path` before any work: exit 2, nothing written (CLI test). |
| T-ubw-03 | Information Disclosure | Committed baseline leaking the home dir, username or absolute paths | low | mitigate | Baseline carries only source ids, package dir names and counts (S8). TestCommittedBaseline and TestBaselineOutput assert no `/Users/`, `/Applications/`, `/home/`, home path, tmp path, roots, examples or timestamps. |
| T-ubw-04 | Elevation of Privilege | Executing code from the Max bundle or third-party packages | low | mitigate | `json.loads` only. The Max binary is never run (Info.plist via plistlib); no subprocess is added; no package code is imported. |
| T-ubw-05 | Repudiation | A re-baseline silently absorbing a regression | medium | mitigate | The baseline is written only by the explicit `--write-baseline` run, never by a test. It is committed in Task 3 with its figures in SUMMARY, and its canonical sorted form makes every delta visible in `git diff`. |
| T-ubw-06 | Tampering | Tests or the scan modifying the DB, src or committed patches (spec: no DB fixes) | high | mitigate | Hermetic tests write only under `tmp_path` with an explicit packages dir. Every verify compares `git status --porcelain` before and after, and Task 3 asserts `git diff --quiet BASE HEAD` (and the working tree) over `.claude/max-objects`, `src`, `patches` and the docs. |
| T-ubw-07 | Denial of Service | The live test false-failing after a Max or package update | low | mitigate | Stale-version sources are excluded (S9). A stale `bundle` skips with the re-baseline command, so it never fails the suite. |
| T-ubw-SC | Tampering | Package installs | low | accept | No new dependency: standard library + pytest only. The 3.10 gate installs the existing `requirements-dev.txt` (numpy, scipy, pytest; [VERIFIED] in Q8) into a throwaway uv venv. |
</threat_model>

<verification>
- `python3 -m pytest -q -p no:cacheprovider` is fully green before (expected 2691 passed, 1 xfailed, 1 xpassed, 29 warnings) and after each task.
  - Passes rise only by the new tests, and xfailed/xpassed stay at 1/1.
  - Record the warning count before and after.
- After every test run, `git status --porcelain` is unchanged.
- No file under `.claude/max-objects/`, `src/`, `patches/`, CLAUDE.md, TECHNICAL.md, README.md or `.claude/skills/` differs from `base-sha.txt`, in HEAD or in the working tree.
- There are at least 3 `(Q9)` commits since `base-sha.txt`, each touching only its task's paths. The stash list is unchanged. Nothing is pushed.
- The Python 3.10 syntax gate passes on every changed `.py` file, and the new tests pass under uv Python 3.10 with Max simulated absent (or the fallback is recorded).
- `python3 tools/audit_db.py --help-io` prints the summary on this Mac, and the committed baseline reproduces byte-for-byte.
</verification>

<success_criteria>
- `python3 tools/audit_db.py --help-io` exists:
  - it scans the bundle and the installed packages' help dirs and skips gen~/rnbo~/jit.gen internals;
  - it compares saved I/O counts and signal roles against `compute_io_counts` / `get_outlet_types`;
  - it emits a JSON report and a summary with mismatching names, box counts, the installed Max version and help-file appversions.
- `tests/fixtures/help_io_baseline.json` is committed, deterministic, under 400 KB, and holds the C1/C2/C9 evidence that Q10 and Q11 will consume.
- A requires_max test fails when mismatches increase, skips without Max.app and on a Max version change, and its diff logic is unit-tested on a tiny committed fixture that runs in CI.
- No DB entry, src module, patch or doc changed. The suite is green on 3.14 and, for the new tests, on 3.10.
</success_criteria>

<output>
Create `.planning/quick/261012-ubw-implement-q9-in-planning-reviews-2026-10/261012-ubw-SUMMARY.md` when done. It must include:
- baseline and final pytest totals, the red counts recorded before each GREEN step, and the warning count before and after;
- how OQ1 was resolved: user answer, or "resolved by default" with option A;
- **the oracle figures from the real run:**
  - per-source table: files, compared, content-defined, unresolved, internal patchers skipped, mismatching names, mismatching boxes;
  - totals;
  - literal and alias-resolved mismatching-name counts (bundle and all sources), count vs signal-role split, and (OQ1-A) newobj vs other boxes;
  - the top 15 names by mismatching boxes;
  - the help appversion histogram;
  - the installed Max version and build;
  - baseline size in bytes and the HEAD it was generated at;
- **the "~119" reconciliation:** the bundle figure under this plan's definition, compared with the review's ~119, and why they differ (definition: recursion into subpatchers, packages, attrs, literal vs canonical; the planning-time variants were 98, 111 and 131-143);
- the spot-checked evidence lines (sel, r, unpack, pack, route, coll, sfrecord~, pitchshift~, spectroscope~);
- **hand-offs:**
  - **Q10:**
    - regenerate with `python3 tools/audit_db.py --help-io --write-baseline tests/fixtures/help_io_baseline.json` after each fix so the baseline shrinks;
    - replace `help_io.box_args` with the quote-aware tokenizer when it lands;
    - the baseline is keyed by literal names (`sel`/`select`, `r`/`receive`, `t`/`trigger` are separate).
  - **Q11:** use `--json` signatures and examples for the override values, including the OQ1 UI boxes (spectroscope~, live.scope~, gridmeter~, playlist~, live.adsrui, dict.view, inlet/outlet).
  - **Q38:** signature `appversions` give the per-version deltas.
  - **Q33:** the content-defined gaps seen (pfft~ only in `_CONTAINER_NAMES`; mxj, mcs.poly~ compared) and any `compare_errors`.
- doc impact, not edited (rule 8): the CLAUDE.md:59 "After a Max update, re-sync" procedure should gain the help-io re-baseline step; TECHNICAL.md tools/test-suite notes; `.claude/skills/references/shared-capabilities.md` (audit_db mention);
- residuals:
  - the live test reads this Mac's `~/Documents/Max 9/Packages`, so other machines see those sources as new or missing (informational);
  - a Max update makes the live test skip until re-baselined;
- rule 9, "Confirm in MAX": no patch file changed, so nothing is required.
</output>
