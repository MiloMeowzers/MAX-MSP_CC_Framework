---
phase: quick-261016-tal
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/maxpat/patcher.py
  - src/maxpat/builders.py
  - src/maxpat/rnbo.py
  - src/maxpat/externals.py
  - src/maxpat/hooks.py
  - tests/test_consolidation.py
  - src/maxpat/gain_staging.py
  - src/maxpat/validation.py
  - src/maxpat/critics/dsp_critic.py
  - src/maxpat/sizing.py
  - src/maxpat/layout.py
  - src/maxpat/critics/layout_critic.py
  - src/maxpat/aesthetics.py
  - src/maxpat/maxclass_map.py
  - src/maxpat/analysis.py
  - src/maxpat/critics/base.py
  - src/maxpat/critics/ext_critic.py
  - src/maxpat/critics/m4l_critic.py
  - src/maxpat/critics/package_critic.py
  - src/maxpat/critics/rnbo_critic.py
  - src/maxpat/critics/structure_critic.py
  - tests/test_integration_patches.py
  - tests/review_blocker_allowlist.json
  - tests/test_uninitialized_state.py
  - tests/test_critic_precision.py
autonomous: true
requirements: [S3, S7, S12]

estimate:
  tokens: 190000
  raw_tokens: 190000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "Operator building any structural box (panel, step marker, p subpatcher parent, bpatcher, gen~ parent with its in / codebox / out, js, rnbo~ parent with its in~ / out~ / param / inport / outport / user objects, custom external help box) gets it from Box.structural. builders.py, rnbo.py and externals.py contain no Box.__new__ call (AST guard), and every structural box carries the same attribute set as a Box.__init__ box."
    - "Operator serializing the 11-case builder battery gets output byte-identical to the base commit, both straight from the builders and after apply_layout. Per-box attribute rows (name, args, id, I/O, rects, fonts, extra_attrs, saved / bpatcher attrs, inner-patcher back-refs, the bpatcher args identity) are identical too (Q/q33_gate.py snapshot, cmp after every task)."
    - "Operator reading the gain-staging rule finds one implementation: src/maxpat/gain_staging.py (find_ungained_paths plus the oscillator vocabulary). validation.py Layer 4 (warning) and the DSP critic (blocker) both call it, and neither module defines its own oscillator set or BFS. validate_patch and review_patch output on every committed patch file and test fixture is identical to the base."
    - "Operator reading layout code finds one port-geometry helper (sizing.outlet_x / sizing.inlet_x, accepting a Box or a raw box dict), used by layout.py and layout_critic.py, and no _resolve_patcher_bg wrapper in aesthetics.py or layout_critic.py. Forced apply_layout output on every committed .maxpat / .maxhelp is identical to the base, with PYTHONHASHSEED pinned to 0."
    - "Operator asking what a UI control is gets maxclass_map.ui_control_names(db): UI maxclasses the DB lists with parameter_enable or parameter_mappable (47 names under the repo DB, a superset of all three old sets). layout.py, layout_critic.py and analysis.py take their purpose sets (LAYOUT_BAND_CONTROLS, PRESENTATION_CONTROLS, PARAMETER_LIST_CONTROLS) from maxclass_map. Each set is pinned as a subset of it and equal to its pre-Q33 members, so analyze(), the presentation-coverage critic and layout output are unchanged. ui_control_names has no src consumer yet: the three sets are co-located and pinned, not replaced. SUMMARY therefore marks the Q33 \"One UI-control set\" item PARTIAL in `## Q33 item status`, with the measured impact numbers, and lists PD-6 first in `## Decisions to confirm` as the unification decision. The SUMMARY verify checks both."
    - "Operator inspecting any CriticResult sees structured rule, box_ids, port and path fields. Every CriticResult( call in src/maxpat/critics names a rule (AST guard), and every committed-corpus result has a rule and box_ids consistent with the ids its text names. tests/test_integration_patches.py and tests/review_blocker_allowlist.json key on (rule, box_ids, port, path) with no finding-text regex, and test_uninitialized_state.py reads rule / box_ids instead of _ID_RE. For every committed review_patch result, the base and new allowlist decisions are identical (Q/q33_gate.py allowlist)."
    - "After every task, the per-test junit diff against the Step 0 baseline (expected 2 failed, 5296 passed, 5 xfailed, 1 xpassed; the 2 q29-check failures) shows no pass-to-non-pass change, no removed test, and only tests.test_consolidation ids added, all passing. No module gains an unused import. Three `(Q33)` commits touch only files_modified paths, patches/ is untouched, and the stash list is unchanged."
  artifacts:
    - path: "tests/test_consolidation.py"
      provides: "Q33 guard: Box.structural contract, no hand-built boxes, shared helpers, UI purpose-set pins, CriticResult field contract and corpus consistency"
      contains: "class TestBoxStructural"
    - path: "src/maxpat/patcher.py"
      provides: "the one structural Box factory"
      contains: "def structural("
    - path: "src/maxpat/gain_staging.py"
      provides: "shared missing-gain-staging traversal and oscillator vocabulary"
      contains: "def find_ungained_paths"
    - path: "src/maxpat/sizing.py"
      provides: "shared port geometry for Box and raw dict"
      contains: "def outlet_x"
    - path: "src/maxpat/maxclass_map.py"
      provides: "DB-derived UI control set plus the three purpose subsets"
      contains: "def ui_control_names"
    - path: "src/maxpat/critics/base.py"
      provides: "CriticResult with rule / box_ids / port / path"
      contains: "box_ids"
    - path: "tests/review_blocker_allowlist.json"
      provides: "allowlist entries keyed on structured CriticResult fields"
      contains: "box_ids"
  key_links:
    - from: "src/maxpat/builders.py, src/maxpat/rnbo.py, src/maxpat/externals.py"
      to: "Box.structural (src/maxpat/patcher.py)"
      via: "every structural box built through the factory; ids still from the same _gen_id() calls in the same order"
      pattern: "Box\\.structural\\("
    - from: "validation._check_gain_staging and dsp_critic._check_gain_staging"
      to: "gain_staging.find_ungained_paths"
      via: "callers pass their own adjacency, oscillator set and dsp_roles sets, then format their own level and text"
      pattern: "find_ungained_paths\\("
    - from: "layout.py and critics/layout_critic.py"
      to: "sizing.outlet_x / sizing.inlet_x"
      via: "import aliased to the old private names, so call sites and tests/test_layout.py are unchanged"
      pattern: "outlet_x as _outlet_x"
    - from: "layout.py, critics/layout_critic.py, analysis.py"
      to: "maxclass_map purpose sets"
      via: "import of LAYOUT_BAND_CONTROLS / PRESENTATION_CONTROLS / PARAMETER_LIST_CONTROLS"
      pattern: "PARAMETER_LIST_CONTROLS"
    - from: "tests/test_integration_patches.py (_result_key, _allow_key)"
      to: "CriticResult.rule / box_ids / port / path and the JSON entry fields"
      via: "tuple key compare, no regex"
      pattern: "result\\.rule"
---

<objective>
This plan implements fix-plan Q33 (review §2 S3, S7, S12) as a pure refactor: no behaviour change, and the suite stays green.

- **Box factory (S3):** add `Box.structural(maxclass, text, nin, nout, outlettype, rect, **attrs)` and port all 17 hand-built `Box.__new__` blocks to it: builders.py ×9 (panel, step marker, subpatcher parent, bpatcher, gen~ in / codebox / out / parent, js), rnbo.py ×7 and externals.py ×1.
- **Gain staging (S7):** one module, src/maxpat/gain_staging.py, holds the oscillator → output-terminal traversal and the oscillator vocabulary. validation.py and dsp_critic.py both call it.
- **Geometry helpers (S12):** one `outlet_x` / `inlet_x` in sizing.py replaces the two copies. The two `_resolve_patcher_bg` one-line wrappers go.
- **One UI-control set (S12):** a DB-derived `maxclass_map.ui_control_names(db)`. The three consumers' purpose subsets move beside it and are pinned as subsets of it. Their output is unchanged (PD-6).
- **CriticResult (S7):** structured `rule`, `box_ids` and `port` fields (`path` exists since Q20). They are set at all 49 construction sites and used by tests/test_integration_patches.py, tests/review_blocker_allowlist.json and the Q24 test helpers instead of regex-parsing finding text.

Purpose: one fix site per concept. The hand-built boxes have already drifted, the two gain-staging copies disagree, port-geometry fixes had to be applied twice, and the allowlist breaks whenever a finding's wording changes.

Output:
- the factory and its ports;
- three shared modules / helpers;
- the structured critic fields;
- tests/test_consolidation.py (new; red first per task);
- three `(Q33)` commits. Each passes Gate G (per-test junit diff, behaviour snapshot, unused-import check), then its `<verify>` runs as a post-commit audit.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@CLAUDE.md

Read only the named parts. Line numbers are as of 7a80ff86.
- `.planning/reviews/2026-10-11-fix-plan.md`: the Q33 section (lines 585-595) and "Rules for every task" (lines 17-33).
- `.planning/reviews/2026-10-11-repo-review.md`: rows S3 (line 194), S7 (line 198) and S12 (line 203).
- Each task's `<read_first>` lists its own source ranges.
</context>

<rules>
Fix-plan rules (they bind every task):
1. Read the referenced finding first.
2. Write each regression test first (red), then fix (green).
3. Never edit committed patch files (`patches/**`).
4. Run `python3 -m pytest -q` before and after.
5. Never `git stash`; never `git add -A` / `git add .`; stage explicit paths only.
6. Code must work on Python 3.10.
7. Don't widen scope. If a step needs a decision the report doesn't make, stop and ask with multiple-choice options.
8. Edit CLAUDE.md, skills or TECHNICAL.md only where the task says to. This task says nowhere, so all doc impact goes in SUMMARY.
9. Flag anything that needs the user to confirm in MAX or Live.

Rule 4 baseline: the suite is NOT fully green. At 71a19149 (Q32 final; 7a80ff86 adds only planning docs) it is **2 failed, 5296 passed, 5 xfailed, 1 xpassed** (~110 s). Both failures come from the user's `patches/q29-check` project:
- `tests/test_doc_signatures.py::test_readme_patch_table_lists_every_project`;
- `tests/test_uninitialized_state.py::TestCommittedCorpus::test_committed_q24_findings_match_allowlist[patches/q29-check/generated/q29-check.maxpat]`.

They are out of scope (rule 7). "Suite green" here means no failure outside that baseline set.

**Q** = `.planning/quick/261016-tal-implement-q33-in-planning-reviews-2026-1`. Everything this plan writes in Q stays untracked and is never staged; the orchestrator commits PLAN and SUMMARY. Files:
- base-sha.txt, stash-list-before.txt, q33_gate.py;
- baseline-junit.xml, baseline-pytest.txt, behaviour-before.json, behaviour-check.json, imports-before.json;
- red-t1.txt to red-t3.txt;
- pytest-t1 / pytest-t2 / final-pytest (.txt and .xml), behaviour-*.json, imports-*.json;
- legacy/ (Task 3) and q33-commit-files.txt.

**Hard preconditions (Task 1, fresh start only, Q/base-sha.txt absent):**
- `git merge-base --is-ancestor 7a80ff86 HEAD` succeeds;
- `git diff --quiet HEAD --` over every existing files_modified path succeeds;
- tests/test_consolidation.py and src/maxpat/gain_staging.py do not exist.

If any fails, HALT and report which. At planning: HEAD = 7a80ff86, the tracked tree was clean and the stash list was empty.

**Q/q33_gate.py** is written in Step 0. It uses the stdlib only, runs from the checkout root, inserts the repo root on sys.path and ignores warnings.

**Hash seed.** On start, if `os.environ.get("PYTHONHASHSEED") != "0"`, it re-execs itself (`os.execve` of sys.executable with the same argv) with PYTHONHASHSEED=0. At planning, apply_layout(force=True) and Patcher.analyze() output on 49 of 61 committed files differed between two unseeded runs: set iteration order follows the string-hash seed. With the seed at 0 both runs were byte-identical. This nondeterminism is pre-existing and out of scope; record it in SUMMARY follow-ups.

Five subcommands:
- `snapshot OUT`: writes JSON (`sort_keys=True`, `indent=1`, `default=str`) with these keys:
  - `builders`: one entry per battery case, holding:
    - `json`: `json.dumps(p.to_dict())`, no sort_keys, so key order counts;
    - `boxes`: one row per box, recursing through `_inner_patcher` in pre-order. A row is the list of `getattr(box, k, None)` for name, args, id, maxclass, text, numinlets, numoutlets, outlettype, patching_rect, fontname, fontsize, presentation, presentation_rect, extra_attrs, _saved_object_attributes, _bpatcher_attrs, _raw, target_id, nudged_from, _loaded_rect and _loaded. It then appends: `_inner_patcher is None`; for a box with an inner patcher, `getattr(inner, "_parent_box", None) is box`; and for maxclass bpatcher, `box.args is (box._bpatcher_attrs or {}).get("args")`;
    - `layout_json`: `json.dumps(p.to_dict())` after `apply_layout(p)` on that same Patcher.
  - **Battery** (each case on a fresh `Patcher(db=db)`; `db = ObjectDatabase()` once):
    - `panels`: add_panel(10, 20, 100, 50); add_panel(5, 5, 40, 40, gradient=False); add_step_marker(3, 5, 5).
    - `subpatcher`: add_subpatcher("synth", inlets=2, outlets=3, inlet_comments=["a"], outlet_comments=["x", "y"]).
    - `bpatchers`: add_bpatcher("face.maxpat", args=["a", 0]); add_bpatcher(embedded=True, width=120.0, height=60.0, numinlets=2, numoutlets=0); add_bpatcher(object_name="bp.Oscillator").
    - `gen`: add_gen("out1 = in1 * 0.5;"); add_gen("out1 = 0; out2 = 1;", num_inputs=0, num_outputs=2); add_gen("out1 = in1 + in2 + in3;").
    - `m4l`: add_m4l_gen_synth([("cutoff", 20.0, 2000.0), ("res", 0.0, 1.0)]).
    - `js`: add_js("x.js", num_inlets=2, num_outlets=3); add_js("y.js").
    - `rnbo`: `src.maxpat.rnbo.add_rnbo(p, objects=[{"name": "cycle~", "args": ["440"]}], params=[{"name": "gain", "default": 0.5, "min": 0.0, "max": 1.0}, {"name": "x", "min": None, "max": None, "default": None}], audio_ins=2, audio_outs=1)`.
    - `rnbo_wrapper`: `generate_rnbo_wrapper(params=[{"name": "g", "default": 0.1, "min": 0.0, "max": 1.0}])`; this case uses the returned Patcher.
    - `ext_message`, `ext_dsp`, `ext_scheduler`: `src.maxpat.externals.generate_help_patch("myext", "message")`, `("myext~", "dsp")` and `("myext", "scheduler")`.

    At planning all 11 cases built and laid out without error, deterministic across hash seeds 1-3.
  - `corpus`: the files `git ls-tree -r -z --name-only <base> -- patches tests/fixtures` lists, filtered to .maxpat, .maxhelp, .gendsp and .rnbopat, with `<base>` from Q/base-sha.txt. Content comes from `git show <base>:<path>`, never from disk; the code is the working tree. A file that does not json.loads records `["load-error", <exception type name>]`. Each per-file call below works on a fresh `copy.deepcopy`; an exception records `["error", <exception type name>]` in that slot.
  - `validate`: the sorted list of [path, layer, level, message, str(proposed_removal or None), result path] for every `validate_patch(d, db=db)` result.
  - `review`: per corpus path, the list of [severity, finding, suggestion, path] per `review_patch(d, db=db)` result, in emission order. The new CriticResult fields are deliberately NOT in the snapshot; they are additive.
  - `analyze`: per .maxpat / .maxhelp path, the full text of `Patcher.from_dict(d, db=db).analyze()`.
  - `layout`: per .maxpat / .maxhelp path, the sha256 of `json.dumps(p.to_dict())` after `p = Patcher.from_dict(d, db=db); apply_layout(p, force=True)`.

  Prototype at planning: 75 corpus files (71 under patches/ plus 4 fixtures), 61 laid out and analysed, 1767 review results, about 20 s. Deterministic only with the seed pinned.
- `imports OUT [--baseline B]`: Q32's checker, over IMPORT_FILES (existing files only). Per file, it lists the import bindings never used. A binding is the alias, or the first dotted segment, of every Import / ImportFrom anywhere in the module (function-level included), except `__future__` and `*`. It counts as used if some `ast.Name` has that id, or a module-level `__all__` string lists it. With --baseline, it exits 1 if any file lists a name absent from that file's baseline list (a file absent from the baseline compares against an empty list). IMPORT_FILES is every .py path in files_modified.
- `junit BASE FINAL [--allow-added P]...`: allow-added defaults to `tests.test_consolidation.`. The id is `classname::name`; the status is failure, error, skipped or pass. It exits 1 if any of these holds:
  - (a) an id is failure/error in FINAL but not in BASE;
  - (b) any BASE id is missing from FINAL (Q33 removes no test);
  - (c) a FINAL id not in BASE starts with no allow-added prefix, or is not pass;
  - (d) an id that is pass in BASE is not pass in FINAL.

  It prints one summary line: base total/pass, final total/pass and added; failure-to-pass changes are reported, not fatal.
- `allowlist` (used from Task 3 on): proves that the structured allowlist keys decide exactly what the base regex keys decided.
  1. Write `git show <base>:tests/test_integration_patches.py` to Q/legacy/legacy_integration.py. Write the base `tests/review_blocker_allowlist.json` and `tests/validate_error_allowlist.json` beside it (that module opens both from its own directory at import).
  2. Import that file with `importlib.util.spec_from_file_location` as `legacy`. Import the working tree's `tests.test_integration_patches` as `new`.
  3. For every base corpus path under `patches/*/generated/*.maxpat`, run `review_patch(d, db=db)` once (working-tree critics; d from `git show`). For EVERY result, `legacy._is_allowlisted(rel, r) == new._is_allowlisted(rel, r)` must hold.
  4. For every result whose finding, prefix-stripped, starts with `Uninitialized state: `, the base Q24 regex id (copy verbatim: `re.compile(r"Uninitialized state: '[^']*' \((obj-\d+)\)")` searched on the prefix-stripped finding, else None) must equal `r.box_ids[0] if r.box_ids else None`. A result has `rule == "uninitialized_state"` if and only if it has that prefix.
  5. It prints the result count, blocker count and exempted count, and exits 1 on any mismatch.

**Gate G** (pre-commit, run from the checkout root), with `<T>` per task:
`bash -c 'Q=.planning/quick/261016-tal-implement-q33-in-planning-reviews-2026-1; T="$1"; python3 -m pytest -q -p no:cacheprovider --junitxml="$Q/$T.xml" > "$Q/$T.txt" 2>&1; R=$?; tail -1 "$Q/$T.txt"; test $R -le 1 || exit 1; python3 "$Q/q33_gate.py" junit "$Q/baseline-junit.xml" "$Q/$T.xml" || exit 1; python3 "$Q/q33_gate.py" snapshot "$Q/behaviour-$T.json" || exit 1; cmp "$Q/behaviour-before.json" "$Q/behaviour-$T.json" || exit 1; python3 "$Q/q33_gate.py" imports "$Q/imports-$T.json" --baseline "$Q/imports-before.json"' gate <T>`
- Task 1: `pytest-t1`. Task 2: `pytest-t2`. Task 3: `final-pytest`, plus `python3 "$Q/q33_gate.py" allowlist`.
- Commit only after G exits 0. Never commit a red task.
- If the snapshot differs, HALT and report the differing keys. Never accept a behaviour diff or regenerate behaviour-before.json.

**Step 0 (Task 1, before any edit; skipped on resume when Q/base-sha.txt and Q/baseline-junit.xml exist):**
1. Check the hard preconditions. Then write `git rev-parse HEAD` to Q/base-sha.txt and `git stash list` to Q/stash-list-before.txt.
2. Write Q/q33_gate.py.
3. Run `python3 -m pytest -q -p no:cacheprovider --junitxml=Q/baseline-junit.xml > Q/baseline-pytest.txt 2>&1`. Expected: the Rule 4 figures. If they differ, record it, do not fix it.
4. Run `snapshot Q/behaviour-before.json`, then `snapshot Q/behaviour-check.json`. `cmp` must succeed (determinism); if it fails, HALT.
5. Run `imports Q/imports-before.json`.

**Commits.** One per task, each message ending `(Q33)`.
- Stage with `git add -- <paths>`, then `git commit -m "..." -- <all task paths>`.
- Order in every task: Gate G, then commit, then `<verify>`. `<verify>` is the post-commit audit: it reruns G from the committed tree and adds the task checks. If it fails, HALT and report; do not amend, rewrite history or start the next task.
- Never `git push`.

**Edit scope.**
- Only files_modified paths change, each only in a task whose `<files>` lists it. Never edit `patches/**`, CLAUDE.md, TECHNICAL.md, README.md, `.claude/**`, or any other src / tests / tools file.
- Existing-test edits are limited to those Task 3 names (tests/test_integration_patches.py and tests/test_uninitialized_state.py helpers). Any other existing test that fails is a code bug: fix the code, never the test.
- No serialized output may change. If an edit cannot be made byte-identical, HALT and ask (rule 7); never accept the diff.

**Context budget.** About 190k in total (low confidence; calibration factor 1, 0 samples): Task 1 ~55k, Task 2 ~50k, Task 3 ~75k, SUMMARY ~10k.
- Tasks 2 and 3 touch more than 5 paths each, but every edit is mechanical (move, import or keyword addition), so the split follows context cost. Read only each task's `<read_first>`.
- **Each task is an independent checkpoint.** It ends with its own Gate G, its own `(Q33)` commit and its own post-commit `<verify>`. After that verify the tree is committed and clean for the task's paths, and nothing from a later task has started, so execution can stop between any two tasks without losing work.
- **Stop rule:** after a task's `<verify>` passes, if context is past ~50%, stop. Write nothing else and report:
  - the last committed task (number and commit hash);
  - the next task to run;
  - that the Q/ artifacts are in place (base-sha.txt, baseline-junit.xml, behaviour-before.json, imports-before.json, q33_gate.py).

  Never stop between a task's Gate G and its commit. If context runs short mid-task, before Gate G, stop with the edits uncommitted and report the task as in progress.
- **SUMMARY** is written only after Task 3's `<verify>` passes. A stopped run writes no SUMMARY.

**Resume.** A fresh executor resumes this way:
1. **Detect done tasks** from the commits since Q/base-sha.txt: `git log --format=%s --fixed-strings --grep="(Q33)" "$(cat Q/base-sha.txt)"..HEAD`. Each task's subject prefix identifies it:
   - `refactor(patcher):` = Task 1;
   - `refactor(shared):` = Task 2;
   - `refactor(critics):` = Task 3.

   The done set must be a prefix of 1, 2, 3 (one commit each). Any other pattern, or a duplicate, means HALT and report.
2. **Skip Step 0.** It is skipped when Q/base-sha.txt and Q/baseline-junit.xml exist. Never regenerate behaviour-before.json, baseline-junit.xml or imports-before.json on resume: they are the Step 0 baseline every later gate compares against.
3. **Re-check.** Rerun the last done task's `<verify>` from the committed tree. If it fails, HALT.
4. **Pick up.** Start at the first task with no commit; its `<precondition>` (the exact count of `(Q33)` commits) must hold.
   - Uncommitted edits in that task's `<files>` belong to it: continue them, then run its Gate G.
   - Uncommitted edits outside its `<files>` mean HALT and report.
   - Rerun its red step only if its Q/red-tN.txt is missing.
5. **All three done:** if all three commits exist and Task 3's `<verify>` passes, only SUMMARY remains.
</rules>

<planner_decisions>
Everything below was checked live at 7a80ff86: grep over src, tests, tools, .claude and the docs, AST scans of src/maxpat/critics, and prototypes of the snapshot, builder battery and UI-set impact. SUMMARY lists PD-1 to PD-13 for the user to confirm.

- **PD-1, Box.structural signature.**
  - It is a classmethod on Box (src/maxpat/patcher.py). The six spec positionals (maxclass, text, nin, nout, outlettype, rect) are **positional-only** (`/`).
  - Keyword-only: box_id (required), name, args, font, inner, saved_attrs, bpatcher_attrs.
  - `**attrs` becomes extra_attrs, in call order.
  - Positional-only matters because the step marker's extra attribute is literally named `text`, and the codebox's extra attributes are `fontname` / `fontsize`; none of the keyword-only names is an extra attribute at any ported site.
  - Defaults:
    - `name` = the first whitespace token of text, else maxclass;
    - `args` = [];
    - `font` = (FONT_NAME, FONT_SIZE).
  - Stored as given, never copied: rect, outlettype, args (the bpatcher shares one args list with its bpatcher_attrs).
  - It sets exactly the attributes Box.__init__ sets (presentation False; presentation_rect, target_id, nudged_from, _raw, _loaded_rect and _loaded None) and does no DB lookup.
- **PD-2, ported sites.**
  - builders ×9, rnbo ×7 and externals._create_external_box ×1, which follows the same pattern; one factory means all of them.
  - Not ported: the Patcher.from_dict loader (patcher.py ~1989; a loader that restores _raw / _loaded, not a builder) and tests' Box.__new__ fixtures.
  - S3's other two places (the 9 builder blocks and layout's 3) now all live in builders.py (moved by quick 260703-h75); add_node_script went in Q32.
- **PD-3, newly complete attributes.** rnbo and externals boxes lacked target_id; every builder box lacked nudged_from / _loaded_rect / _loaded. All now exist as None. Every reader uses getattr(..., None) (hooks.py:202, layout.py:256, patcher.py:408) or reads target_id only on comments (layout.py:1319), so nothing observable changes; the battery snapshot proves it.
  - Preserved drift, not fixed (behaviour changes, so follow-ups): the embedded bpatcher still has no `embed: 1`; the rnbo~ parent keeps maxclass `rnbo~` (MAX writes newobj; not in UI_MAXCLASSES).
- **PD-4, gain staging module.** src/maxpat/gain_staging.py holds:
  - OSCILLATOR_NAMES (cycle~, saw~, rect~, tri~, noise~, pink~);
  - MC_OSCILLATOR_NAMES (mc.cycle~, mc.saw~, mc.rect~, mc.tri~);
  - `find_ungained_paths(box_lookup, signal_adj, oscillator_names, gain_names, terminal_names)`, which returns (osc_id, osc_name, terminal_id, terminal_name) tuples in emission order. The two prior copies are the same BFS: osc ids in box_lookup order, deque, visited (id, has_gain) on pop, a missing neighbour skipped, terminals reported when ungained and never traversed past.

  Kept per caller, because unifying any of them changes findings:
  - the signal-cord test: validation uses outlettype == "signal", the critic uses SIGNAL_OUTLET_TYPES (adds multichannelsignal);
  - the oscillator set: validation uses base only, the critic base plus mc;
  - level and wording: warning vs blocker plus suggestion;
  - the dsp_roles sets, still passed module-qualified so test monkeypatching keeps working.

  Unification options go to SUMMARY. The unsafe-gain checks are not duplicates (validation flags a literal `*~ k > 1`, the critic propagates source bounds) and stay as they are.
- **PD-5, geometry.**
  - `outlet_x` / `inlet_x` and `IO_MARGIN = 7.0` live in sizing.py, beside rendered_rect, the existing shared Box-or-dict geometry model.
  - A dict input keeps the critic's defaults (patching_rect [0, 0, 60, 22], count 1, no {"box": ...} unwrapping). A Box input reads patching_rect and numoutlets / numinlets directly.
  - layout.py and layout_critic.py import them as `_outlet_x` / `_inlet_x`, so call sites and tests/test_layout.py:634 stay unchanged.
  - Both `_resolve_patcher_bg` functions were one-line delegates to aesthetics.resolve_patcher_background; they are deleted and their single call sites call it directly.
- **PD-6, UI-control set: one DB-derived set, behaviour kept.**
  - `ui_control_names(db=None)` = the UI_MAXCLASSES members whose DB entry has `parameter_enable` or `parameter_mappable` in `db.attributes(name)`. That is 47 names under the repo DB, and a superset of all three old sets (verified at planning).
  - True unification changes output. Measured at planning on the committed .maxpat / .maxhelp files:
    - **presentation coverage**: about 14 more warnings in 12 files (13 gain~, which the critic excludes on purpose as a slaved fader, and 1 button);
    - **analyze()'s parameter list**: changes in 14 files (textedit 13, live.text 5, function 2, attrui 2, playlist~ 2, pictslider 2; nodes, jsui, filtergraph~ and led 1 each);
    - **apply_layout**: 29 more control kinds would be banded above their targets in new patches.

    Q33's done-when is "no behaviour change", so this plan keeps each consumer's members: LAYOUT_BAND_CONTROLS (18, matched by box name), PRESENTATION_CONTROLS (23, by maxclass) and PARAMETER_LIST_CONTROLS (22, by maxclass) move into maxclass_map.py beside it, each pinned as a subset and equal to its old members.
  - They are static, not intersected at runtime: review_layout has no db, and a runtime intersection would make layout depend on test stub DBs.
  - **Options for the user (SUMMARY):**
    - (a) keep this split (default);
    - (b) unify all three on ui_control_names;
    - (c) unify with DB-derived per-purpose filters, e.g. presentation excluding the "MSP U/I" category.

    (b) and (c) are behaviour changes and become their own quick task.
- **PD-7, CriticResult fields.**
  - Keyword-only after path: `rule: str = ""`, `box_ids: tuple = ()` (stored as tuple) and `port: int | None = None`.
  - `port` goes beyond the spec's names. Two of today's allowlist keys include a port index (fan-out source outlet, unsafe-gain inlet); without it the structured key would be weaker than the regex key. Alternative: drop port and accept weaker keys.
  - repr, tag_results and the save gate key (hooks._finding_key) are unchanged.
- **PD-8, field values.**
  - `rule` = the emitting check function's name without `_check_`, from the table in Task 3. review_external gets per-finding ids `ext_*`; review_rnbo's inline check is `rnbo_missing_inner_patcher`; `_trace_gain_inlet` emits `unsafe_gain_sources`.
  - `box_ids` = the real box ids the finding is about, deduplicated: every id the text names, in first-occurrence order. A subject box the text names only by label (text_contrast) may be included. Never a placeholder such as "?".
  - `port` is set only for fan_out_without_trigger (source outlet), unsafe_gain_sources (gain inlet) and bach_llll_types (destination inlet); None elsewhere.
- **PD-9, allowlist JSON.**
  - The 2 entries become {severity, rule, box_ids, port, path, source (label), reason}; kind / source_id / outlet / gain_id / inlet / destinations go, and `_doc` names the new key.
  - The fan-out entry's key is now stricter: it lists the destination and reconvergence ids, which the regex key ignored.
  - A future Bach entry keys on the destination id, not its name (no Bach entries exist).
  - Q/q33_gate.py allowlist proves identical decisions on every committed result.
- **PD-10, Q24 helpers.** test_uninitialized_state.py's `_q24` / `_q24_ids` / `_corpus_q24` switch from the prefix test and `_ID_RE` to rule / box_ids. Its allowlist is the other CriticResult allowlist and already keys on box_id, so its JSON is unchanged. Alternative: leave its regex.
- **PD-11, not changed (follow-ups):**
  - the save gate's text-template key (hooks._finding_key): switching it changes gate identity, and ValidationResult has no rule;
  - the validate-error allowlist's ValidationResult regex (not a CriticResult);
  - the max-critic skill loop's "same finding repeated" escalation (skill edit, rule 8).
- **PD-12, out of Q33's list:** S12's `_route_clear_path` nearby-box limit (a performance change). The fix-plan's Q33 omits it; it is a follow-up.
- **PD-13, permanent guard tests/test_consolidation.py.** It holds the red-first evidence per task and the AST / pin guards that keep the consolidation from regressing. Alternative: delete it after verification.

Doc impact (rule 8, SUMMARY only, not edited):
- .claude/skills/max-dsp-agent/SKILL.md:42 teaches "Codebox via `Box.__new__()` pattern"; it should point to Box.structural / add_gen;
- .claude/skills/references/severity-contract.md:11 lists CriticResult as severity / finding / suggestion; it now also has path, rule, box_ids and port;
- .claude/skills/max-critic/SKILL.md could key repeat detection on rule + box_ids.

Ordering: the Box factory leads as the tracer. It crosses builder, serializer and layout and is proven by the byte-identical battery after its first ported site.
</planner_decisions>

<source_audit>
| Source | Item | Covered by |
|--------|------|-----------|
| GOAL (Q33) | Add Box.structural(maxclass, text, nin, nout, outlettype, rect, **attrs) | Task 1 (PD-1) |
| GOAL | Port every hand-built Box.__new__ block in builders, rnbo and layout | Task 1: builders ×9 (layout's 3 moved there), rnbo ×7, plus externals ×1 (PD-2) |
| GOAL | Gain staging: merge the duplicated rules in validation.py and dsp_critic.py into one module | Task 2 (gain_staging.py, PD-4) |
| GOAL | Merge the duplicated `_outlet_x` / `_inlet_x` and `_resolve_patcher_bg` | Task 2 (sizing.py helpers, wrappers deleted; PD-5) |
| GOAL | Replace the three disagreeing UI sets (layout.py, layout_critic.py, analysis.py) with one DB-derived set | PARTIAL (explicit deferral). Task 2 adds ui_control_names(db) plus the three purpose subsets, co-located and pinned, with behaviour kept; no src consumer uses the DB set yet. Replacing the sets is a behaviour change, so it goes to the user as PD-6 (first in SUMMARY Decisions, with the measured impact), and SUMMARY's `## Q33 item status` marks the item PARTIAL (checked by the SUMMARY verify) |
| GOAL | CriticResult rule / box_ids / path, used in test_integration_patches.py and the allowlist instead of regex-parsing | Task 3 (PD-7 to PD-10; path already existed) |
| GOAL | Done when pure refactor and suite green | Gate G (junit diff, behaviour snapshot incl. builder bytes, validate / review / analyze / layout over the corpus, imports) every task; allowlist equivalence in Task 3 |
| REQ | S3 | Task 1 |
| REQ | S7 | Task 2 (gain staging), Task 3 (CriticResult) |
| REQ | S12 | Task 2 (geometry, UI set); `_route_clear_path` limit not in Q33's list (PD-12, follow-up) |
| CONTEXT | Behaviour snapshot before, diff after, flag unavoidable differences | Step 0 snapshot plus cmp per task; PD-6 unification options in SUMMARY |
| CONTEXT | Builder output byte-identical across the port | snapshot `builders` (json, layout_json, attribute rows) |
| CONTEXT | Sequential on main, no stash, explicit paths | Rules: Commits, Edit scope; Task 3 verify audits commit files and the stash list |
| RESEARCH | none (no research phase) | — |
</source_audit>

<tasks>

<task type="tracer" tdd="true">
  <name>Task 1: Step 0 and gate tooling; tracer: Box.structural end to end through add_panel (factory, builder, serializer, layout) behind a red-first guard and the byte-identical battery, then the other 16 hand-built boxes in builders, rnbo and externals</name>
  <files>src/maxpat/patcher.py, src/maxpat/builders.py, src/maxpat/rnbo.py, src/maxpat/externals.py, src/maxpat/hooks.py, tests/test_consolidation.py</files>
  <precondition>`git merge-base --is-ancestor 7a80ff86 HEAD` succeeds (on a fresh start the rules' hard preconditions also hold).</precondition>
  <read_first>
    - .planning/reviews/2026-10-11-repo-review.md row S3 (line 194)
    - src/maxpat/patcher.py 1-30 (imports: FONT_NAME, FONT_SIZE), 241-360 (Box.__init__: the attribute set the factory must reproduce; comment at 339-342), 385-500 (to_dict creation path, read-only)
    - src/maxpat/builders.py 307-430 (add_panel, add_step_marker), 806-865 (add_subpatcher parent), 930-990 (add_bpatcher), 1030-1152 (add_gen in / codebox / out / parent), 1288-1337 (add_js)
    - src/maxpat/rnbo.py 1-12 (module docstring), 150-158, 173-180 (lazy imports), 203-395 (7 blocks)
    - src/maxpat/externals.py 1-40 (imports), 138-176
    - src/maxpat/hooks.py 192-205
    - planner_decisions PD-1, PD-2, PD-3, PD-13
  </read_first>
  <behavior>
    Module setup for tests/test_consolidation.py:
    - docstring: "Q33 consolidation guard: one Box factory, shared helpers, structured critic fields";
    - `REPO_ROOT = Path(__file__).resolve().parents[1]`;
    - a module-scoped `db` fixture (`ObjectDatabase()`);
    - `_calls(path, attr, owner)`: AST helper returning the Call nodes in path whose func is `Attribute(value=Name(id=owner), attr=attr)`.

    **TestBoxStructural** (red at HEAD):
    - `test_attribute_set_matches_init`: `set(vars(Box.structural("panel", "", 1, 0, [], [0.0, 0.0, 10.0, 10.0], box_id="obj-1")))` equals `set(vars(Box("toggle", box_id="obj-2", db=db)))`.
    - `test_fields_and_defaults`:
      - the six positionals land on maxclass, text, numinlets, numoutlets, outlettype and patching_rect (rect and outlettype by identity);
      - id from box_id;
      - name "in" for text "in 1", maxclass for text "", explicit name wins;
      - args [] by default, explicit args by identity;
      - default fontname / fontsize are FONT_NAME / FONT_SIZE, and font=("Arial", 11.0) sets both;
      - inner / saved_attrs / bpatcher_attrs land on _inner_patcher / _saved_object_attributes / _bpatcher_attrs;
      - presentation False; presentation_rect, target_id, nudged_from, _raw, _loaded_rect and _loaded None.
    - `test_extra_attrs_may_reuse_positional_names`: `Box.structural("textbutton", "", 1, 3, ["", "", "int"], [0, 0, 24, 24], box_id="m", text="3", fontname="Arial")` gives extra_attrs == {"text": "3", "fontname": "Arial"} and box.text == "".
    - `test_to_dict_matches_hand_built`: a structural codebox and a Box made with `Box.__new__(Box)` plus the same fields set by hand give equal `json.dumps(to_dict())`.
    - `test_builders_use_the_factory`, parametrized over src/maxpat/builders.py, src/maxpat/rnbo.py and src/maxpat/externals.py: `_calls(path, "__new__", "Box") == []` and `_calls(path, "structural", "Box")` is non-empty.
  </behavior>
  <action>
**Step 0.** Do the rules' Step 0 in order: preconditions, base-sha, stash list, Q/q33_gate.py (all five subcommands, with the hash-seed re-exec), the baseline junit run, the two snapshots plus cmp, and the imports baseline.

**Red.** Create tests/test_consolidation.py with the `<behavior>` setup and TestBoxStructural. Run `python3 -m pytest -q -p no:cacheprovider tests/test_consolidation.py > Q/red-t1.txt 2>&1`; it must show failures.

**Green, tracer first (factory + add_panel):**
1. In src/maxpat/patcher.py, add the `Box.structural` classmethod per PD-1, after `_derive_outlet_types`.
   - It creates the box via `cls.__new__(cls)` and assigns every attribute Box.__init__ assigns, with the PD-1 defaults. `extra_attrs` is the `**attrs` dict.
   - Its docstring states:
     - it is the one factory for boxes that bypass the DB (structural containers, gen / rnbo internals, custom externals);
     - the six positionals are positional-only so extra attributes may be named text / maxclass / fontname;
     - nothing passed in is copied.
   - Reword the comment at patcher.py:339-342 so it no longer says builder boxes come from Box.__new__. The getattr advice stays for boxes made without __init__ (from_dict, tests).
2. Port add_panel to it: `self._gen_id()` is evaluated as the box_id argument, then the extra attributes are background, ignoreclick, border, rounded and mode in that order. The bgfillcolor / bgcolor branch after it is unchanged.
3. Run `python3 Q/q33_gate.py snapshot Q/behaviour-tracer.json && cmp Q/behaviour-before.json Q/behaviour-tracer.json` and `python3 -m pytest -q -p no:cacheprovider tests/test_consolidation.py -k "not builders_use"`. Both must pass before expanding.

**Green, expansion.** Port the other 16 blocks. At every site:
- Keep every `_gen_id()` / `inner._gen_id()` call in its current order relative to the others: id order is serialized.
- Pass `name=` explicitly wherever the PD-1 default would differ from today's value: the subpatcher parent ("patcher", text "p {name}"), the rnbo user objects (obj_name) and the external box (name).
- Pass `args=` wherever today's args are non-empty.
- Keep extra-attribute keys in today's order.

Per site:
- **add_step_marker:** pass font=(FONT_NAME, 11.0) and the eight extra attributes, keeping the best_text_color import and computation before the call.
- **add_subpatcher:** pass inner=inner and saved_attrs with the four keys. Set the back-refs after, as now.
- **add_bpatcher:** build bpatcher_attrs (with the optional name) before the call and pass bpatcher_attrs plus `args=args`, so `box.args is bpatcher_attrs["args"]` still holds. The embedded branch still assigns `_inner_patcher` and the back-refs after.
- **add_gen:** the in / out loops, the codebox and the parent. The codebox passes `code=code, fontname=FONT_NAME, fontsize=FONT_SIZE` as extra attributes; the parent keeps `max(1, num_inputs)` inlets and inner=inner.
- **add_js:** the box. Reword its docstring "Uses Box.__new__ to bypass DB lookup" to name Box.structural.
- **rnbo.py:** the in~ / out~ loops, params, inport, outport, user objects (move the rnbo_db lookup and outlettype derivation before the call) and the parent (maxclass "rnbo~", inner=inner, unchanged).
  - Drop the lazy FONT_NAME / FONT_SIZE import if it is now unused.
  - Reword the three docstring / comment mentions of the Box.__new__ pattern (lines 6, 154, 371) to name Box.structural.
- **externals._create_external_box:** port it, rewording its docstring the same way; drop imports that become unused.
- **src/maxpat/hooks.py:196-197:** reword the docstring clause so it says boxes built without Box.__init__ may lack `_loaded_rect`, instead of naming builder boxes. Comment-only.

Re-run the guard file; it must pass.

**Gate, commit, audit:**
1. Run Gate G with `pytest-t1`. It must exit 0.
2. Commit the 6 task paths: `refactor(patcher): add Box.structural and build every structural box in builders, rnbo and externals through it; serialized builder output byte-identical (Q33)`.
3. Run `<verify>`. If it fails, HALT and report.
  </action>
  <verify>
    <automated>bash -c 'Q=.planning/quick/261016-tal-implement-q33-in-planning-reviews-2026-1; T=pytest-t1; python3 -m pytest -q -p no:cacheprovider --junitxml="$Q/$T.xml" > "$Q/$T.txt" 2>&1; R=$?; tail -1 "$Q/$T.txt"; test $R -le 1 || exit 1; python3 "$Q/q33_gate.py" junit "$Q/baseline-junit.xml" "$Q/$T.xml" || exit 1; python3 "$Q/q33_gate.py" snapshot "$Q/behaviour-$T.json" || exit 1; cmp "$Q/behaviour-before.json" "$Q/behaviour-$T.json" || exit 1; python3 "$Q/q33_gate.py" imports "$Q/imports-$T.json" --baseline "$Q/imports-before.json" || exit 1; grep -iq -e failed -e error "$Q/red-t1.txt" || exit 1; grep -q "class TestBoxStructural" tests/test_consolidation.py || exit 1; ST=$(git status --porcelain -- patches) || exit 1; test -z "$ST" || exit 1; C=$(git log --format=%H --fixed-strings --grep="(Q33)" "$(cat "$Q/base-sha.txt")"..HEAD) && set -- $C && test $# -ge 1 || exit 1; python3 -c "import ast,sys;[ast.parse(open(f).read(),feature_version=(3,10)) for f in sys.argv[1:]]" src/maxpat/patcher.py src/maxpat/builders.py src/maxpat/rnbo.py src/maxpat/externals.py src/maxpat/hooks.py tests/test_consolidation.py'</automated>
  </verify>
  <done>The Step 0 artifacts exist, and the baseline matched the plan figures (or the difference is recorded). Q/red-t1.txt shows the guard red. The tracer snapshot matched before expansion. Gate G passed, then `<verify>` passed:
- no test removed, only guard ids added (all passing), no status changed;
- the behaviour snapshot, including every builder battery byte, layout output and box attribute row, is identical to Step 0, and no import was orphaned;
- builders.py, rnbo.py and externals.py contain no Box.__new__ call;
- one `(Q33)` commit touches only the 6 Task 1 paths.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: shared helpers: one gain-staging traversal (gain_staging.py) for validation and the DSP critic, one port-geometry helper in sizing.py, the two patcher-background wrappers gone, and the DB-derived UI control set with the three purpose subsets in maxclass_map.py</name>
  <files>src/maxpat/gain_staging.py, src/maxpat/validation.py, src/maxpat/critics/dsp_critic.py, src/maxpat/sizing.py, src/maxpat/layout.py, src/maxpat/critics/layout_critic.py, src/maxpat/aesthetics.py, src/maxpat/maxclass_map.py, src/maxpat/analysis.py, tests/test_consolidation.py</files>
  <precondition>Exactly one `(Q33)` commit exists since Q/base-sha.txt, and Task 1's `<verify>` passes.</precondition>
  <read_first>
    - .planning/reviews/2026-10-11-repo-review.md rows S7 (line 198) and S12 (line 203)
    - src/maxpat/validation.py 40-66 (the oscillator set and its comments), 1340-1366 (call site), 1602-1662 (_check_gain_staging)
    - src/maxpat/critics/dsp_critic.py 1-60 (docstring incl. the NOTE at 28-29, the oscillator set at 46-50; _GAIN_NAMES / _TERMINAL_NAMES stay), 114-128 (call site), 250-356 (_outlettype, _check_gain_staging)
    - src/maxpat/dsp_roles.py 28-55 (the cached default-DB pattern)
    - src/maxpat/sizing.py 256-280
    - src/maxpat/layout.py 30-95 (imports, _UI_CONTROL_NAMES at 54-60, _IO_MARGIN at 94), 1025-1056 (_identify_ui_controls), 1325-1353 (_outlet_x / _inlet_x)
    - src/maxpat/critics/layout_critic.py 18-40, 110-136, 326-345 (_INTERACTIVE_MAXCLASSES and its comment), 375-425 (_resolve_patcher_bg and its call site)
    - src/maxpat/aesthetics.py 385-407, 580-590
    - src/maxpat/maxclass_map.py (all, ~120 lines; it has no imports, so keep any DB import lazy)
    - src/maxpat/analysis.py 18-24, 678-694 (_parameter_lines)
    - planner_decisions PD-4, PD-5, PD-6
  </read_first>
  <behavior>
    **TestSharedHelpers** (red at HEAD), appended to tests/test_consolidation.py.

    Gain staging:
    - `test_gain_staging_vocabulary`: OSCILLATOR_NAMES == {cycle~, saw~, rect~, tri~, noise~, pink~} and MC_OSCILLATOR_NAMES == {mc.cycle~, mc.saw~, mc.rect~, mc.tri~}.
    - `test_find_ungained_paths`, over tiny box_lookup / adjacency dicts (boxes as `{"maxclass": "newobj", "text": ...}`):
      - cycle~ -> dac~ gives [(o, "cycle~", d, "dac~")];
      - cycle~ -> *~ -> dac~ gives [];
      - mc.cycle~ -> dac~ gives [] with OSCILLATOR_NAMES and one hit with OSCILLATOR_NAMES | MC_OSCILLATOR_NAMES;
      - a neighbour id missing from box_lookup is skipped.
    - `test_both_layers_delegate`: `inspect.getsource` of validation._check_gain_staging and of dsp_critic._check_gain_staging each contain "find_ungained_paths", and neither module assigns a module-level `_OSCILLATOR_NAMES` (AST).

    Geometry:
    - `test_port_geometry`:
      - `sizing.outlet_x({"patching_rect": [10, 0, 100, 22], "numoutlets": 3}, 2) == 103.0`;
      - a lone port gives x + 7.0;
      - a dict missing both keys gives 7.0;
      - a Box with the same rect and counts gives the same values for outlet_x and inlet_x.
    - `test_one_geometry_site`:
      - `layout._outlet_x is sizing.outlet_x`, the same for `_inlet_x` and for layout_critic;
      - AST: no FunctionDef `_outlet_x` / `_inlet_x` and no `_IO_MARGIN` assignment in layout.py or critics/layout_critic.py;
      - no FunctionDef `_resolve_patcher_bg` in aesthetics.py or critics/layout_critic.py.

    UI controls:
    - `test_ui_control_names_is_db_derived`: `ui_control_names(db) <= UI_MAXCLASSES`; it contains toggle, flonum, number, live.dial, gain~, textedit and button; it excludes comment, panel, message and meter~.
    - `test_purpose_sets`, parametrized over the three sets:
      - each is `<= ui_control_names(db)`;
      - each equals its pinned pre-Q33 literal: the 18 layout names, the 23 presentation names and the 22 analysis names, copied verbatim from layout.py:54-60, layout_critic.py:334-340 and analysis.py:681-688 at 7a80ff86.
    - `test_consumers_import_the_sets`: AST shows no `_UI_CONTROL_NAMES` assignment in layout.py and no `_INTERACTIVE_MAXCLASSES` in layout_critic.py; `inspect.getsource(Patcher._parameter_lines)` contains "PARAMETER_LIST_CONTROLS".
  </behavior>
  <action>
**Red.** Append TestSharedHelpers. Run `python3 -m pytest -q -p no:cacheprovider tests/test_consolidation.py > Q/red-t2.txt 2>&1`. It must show failures, with TestBoxStructural still green.

**Green, gain staging (PD-4):**
- **New src/maxpat/gain_staging.py:**
  - a module docstring: the missing-gain-staging rule shared by validation.py Layer 4 (warning, base oscillators, "signal" cords) and the DSP critic (blocker, base and mc oscillators, SIGNAL_OUTLET_TYPES cords). Each caller builds its own adjacency and passes dsp_roles' sets, so the two keep today's findings (fix-plan Q33 / review S7);
  - the two frozensets;
  - find_ungained_paths, moved verbatim from the existing BFS, with hits returned instead of appended.
- **validation.py:**
  - delete the oscillator comment and set;
  - extend the dsp_roles comment to say the oscillator vocabulary and traversal come from src.maxpat.gain_staging;
  - `_check_gain_staging` keeps its signature and loops over `gain_staging.find_ungained_paths(box_lookup, signal_adj, gain_staging.OSCILLATOR_NAMES, gain_names, terminal_names)`, appending the same ValidationResult text.
- **dsp_critic.py:**
  - delete the oscillator set;
  - `_check_gain_staging` keeps its signature, defaults and adjacency build, then loops over `find_ungained_paths(..., gain_staging.OSCILLATOR_NAMES | gain_staging.MC_OSCILLATOR_NAMES, ...)` with the same plugout~ / other suggestion and blocker text;
  - in the module docstring, reword the gain-staging bullet and the NOTE: gain staging is reported by both layers from one shared implementation; unterminated chains and feedback loops stay validation-only.
  - Keep `_GAIN_NAMES` / `_TERMINAL_NAMES` (tests import them).
- Drop any import (e.g. a deque) that becomes unused; the imports gate checks.

**Green, geometry (PD-5):**
- **sizing.py:** add `IO_MARGIN = 7.0`, a private `_port_x(box, idx, count_key)` and public `outlet_x(box, outlet_idx)` / `inlet_x(box, inlet_idx)` with the PD-5 dict / Box semantics and today's formula, including the lone-port comment.
- **layout.py and critics/layout_critic.py:** delete `_IO_MARGIN` and both functions, and import `inlet_x as _inlet_x` and `outlet_x as _outlet_x` from src.maxpat.sizing (extend the existing sizing import line).
- **aesthetics.py:** delete `_resolve_patcher_bg`; its call site calls `resolve_patcher_background(patcher.props)`.
- **critics/layout_critic.py:** delete its `_resolve_patcher_bg`. `_check_text_contrast` adds `resolve_patcher_background` to its existing local aesthetics import and calls it with patcher_props.

**Green, UI controls (PD-6):**
- **maxclass_map.py:**
  - after is_ui_object, add a lazily cached default-DB helper (the dsp_roles._default_db pattern with a function-local ObjectDatabase import);
  - add `ui_control_names(db=None) -> frozenset[str]`, whose docstring states the PD-6 derivation and that it is the DB authority the purpose subsets are pinned against (fix-plan Q33 / review S12);
  - add the three frozensets with their members copied verbatim, each with a comment giving its purpose and match key:
    - LAYOUT_BAND_CONTROLS: placed in a band above the object they feed; matched by box name;
    - PRESENTATION_CONTROLS: interactive param-entry widgets that belong in presentation; gain~, meters and comments are excluded on purpose; matched by maxclass; move layout_critic's comment here;
    - PARAMETER_LIST_CONTROLS: analyze()'s parameter list; it includes gain~ / live.gain~; matched by maxclass;
  - add one comment above them: the sets differ on purpose, and unifying them is a recorded user decision (Q33 SUMMARY), not a refactor.
- **layout.py:** delete `_UI_CONTROL_NAMES`; import LAYOUT_BAND_CONTROLS and use it in `_identify_ui_controls`; its docstring names it.
- **critics/layout_critic.py:** delete `_INTERACTIVE_MAXCLASSES` and its comment; import and use PRESENTATION_CONTROLS.
- **analysis.py:** `_parameter_lines` uses PARAMETER_LIST_CONTROLS, imported beside UI_MAXCLASSES.

Re-run the guard file; it must pass.

**Gate, commit, audit:**
1. Run Gate G with `pytest-t2`. It must exit 0.
2. Commit the 10 task paths: `refactor(shared): one gain-staging traversal for validation and the DSP critic, one port-geometry helper, no patcher-background wrappers, UI-control purpose sets beside a DB-derived control set (Q33)`.
3. Run `<verify>`. If it fails, HALT and report.
  </action>
  <verify>
    <automated>bash -c 'Q=.planning/quick/261016-tal-implement-q33-in-planning-reviews-2026-1; T=pytest-t2; python3 -m pytest -q -p no:cacheprovider --junitxml="$Q/$T.xml" > "$Q/$T.txt" 2>&1; R=$?; tail -1 "$Q/$T.txt"; test $R -le 1 || exit 1; python3 "$Q/q33_gate.py" junit "$Q/baseline-junit.xml" "$Q/$T.xml" || exit 1; python3 "$Q/q33_gate.py" snapshot "$Q/behaviour-$T.json" || exit 1; cmp "$Q/behaviour-before.json" "$Q/behaviour-$T.json" || exit 1; python3 "$Q/q33_gate.py" imports "$Q/imports-$T.json" --baseline "$Q/imports-before.json" || exit 1; grep -iq -e failed -e error "$Q/red-t2.txt" || exit 1; grep -q "class TestSharedHelpers" tests/test_consolidation.py || exit 1; python3 -c "import src.maxpat.gain_staging as g, src.maxpat.maxclass_map as m; assert callable(g.find_ungained_paths) and callable(m.ui_control_names)" || exit 1; ST=$(git status --porcelain -- patches) || exit 1; test -z "$ST" || exit 1; C=$(git log --format=%H --fixed-strings --grep="(Q33)" "$(cat "$Q/base-sha.txt")"..HEAD) && set -- $C && test $# -ge 2 || exit 1; python3 -c "import ast,sys;[ast.parse(open(f).read(),feature_version=(3,10)) for f in sys.argv[1:]]" src/maxpat/gain_staging.py src/maxpat/validation.py src/maxpat/critics/dsp_critic.py src/maxpat/sizing.py src/maxpat/layout.py src/maxpat/critics/layout_critic.py src/maxpat/aesthetics.py src/maxpat/maxclass_map.py src/maxpat/analysis.py tests/test_consolidation.py'</automated>
  </verify>
  <done>Q/red-t2.txt shows TestSharedHelpers red. Gate G passed, then `<verify>` passed:
- validate / review / analyze / layout output on the whole corpus and every builder byte are identical to Step 0;
- no import was orphaned, and no test status changed;
- one gain-staging traversal, one port-geometry helper, no background wrapper, and the UI purpose sets pinned against ui_control_names;
- the second `(Q33)` commit touches only the 10 Task 2 paths.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: CriticResult gets rule / box_ids / port at all 49 construction sites; test_integration_patches.py, review_blocker_allowlist.json and the Q24 test helpers key on them instead of parsing finding text; legacy-equivalence audit and final audit</name>
  <files>src/maxpat/critics/base.py, src/maxpat/critics/dsp_critic.py, src/maxpat/critics/ext_critic.py, src/maxpat/critics/layout_critic.py, src/maxpat/critics/m4l_critic.py, src/maxpat/critics/package_critic.py, src/maxpat/critics/rnbo_critic.py, src/maxpat/critics/structure_critic.py, tests/test_integration_patches.py, tests/review_blocker_allowlist.json, tests/test_uninitialized_state.py, tests/test_consolidation.py, tests/test_critic_precision.py</files>
  <precondition>Exactly two `(Q33)` commits exist since Q/base-sha.txt, and Task 2's `<verify>` passes.</precondition>
  <read_first>
    - src/maxpat/critics/base.py (all, 54 lines)
    - the construction sites, by enclosing function (line numbers at 7a80ff86; dsp_critic and layout_critic moved in Task 2, so grep `CriticResult(`):
      - dsp_critic: _check_gen_io_match (179, 190), _check_gain_staging (~343), _trace_gain_inlet (768);
      - ext_critic: review_external (72, 82, 91, 109, 118, 129, 139, 150, 163);
      - layout_critic: _check_overlapping_boxes (220), _check_missing_midpoints (279, 288), _check_out_of_bounds (316), _check_presentation_coverage (363), _check_text_contrast (462, 474, 489);
      - m4l_critic 220-490;
      - package_critic 235-520;
      - rnbo_critic 100-315;
      - structure_critic 380-410 (fan-out finding and outlet variable), 590-602 (hot/cold), 750-760, 810-825, 975-1020, 1320-1342
    - tests/test_integration_patches.py 1-190 and 276-376 (regex keys, _result_key / _allow_key / _is_allowlisted, hygiene test, test_allowlist_key_includes_path)
    - tests/review_blocker_allowlist.json (all; 2 entries plus _doc)
    - tests/test_uninitialized_state.py 1-100 (_Q24, _strip_prefix, _q24, _ID_RE, _q24_ids) and 1120-1140 (_corpus_q24)
    - planner_decisions PD-7, PD-8, PD-9, PD-10, PD-11
  </read_first>
  <behavior>
    **TestCriticResultFields** (red at HEAD), appended to tests/test_consolidation.py:
    - `test_defaults_and_keyword_only`: CriticResult("note", "f", "s") has rule "", box_ids (), port None and path ""; a 5th positional argument raises TypeError; box_ids=["a"] is stored as ("a",).
    - `test_every_site_names_a_rule`: AST over every src/maxpat/critics/*.py; each Call whose func is Name `CriticResult` has a `rule` keyword whose value is a str Constant matching `^[a-z][a-z0-9_]*$`. There are 49 such calls at planning; assert at least 49.
    - `test_corpus_results_are_structured`: for every `patches/*/generated/*.maxpat` (sorted glob from REPO_ROOT), each review_patch result satisfies:
      - rule is non-empty;
      - box_ids is a tuple of str, each a box id somewhere in the file (all scopes, via walk.iter_patchers);
      - the ids the finding names: the file's ids matched as standalone tokens (`(?<![\w.-])ID(?![\w-])`), deduplicated, in first-occurrence order, equal `[i for i in r.box_ids if i in named]`;
      - port is None or an int.
    - `test_allowlist_rules_carry_ports`: every committed blocker with rule fan_out_without_trigger or unsafe_gain_sources has an int port. A minimal Bach llll mismatch patch, the same shape an existing tests/ case uses (grep "Bach llll type mismatch" in tests/), yields rule bach_llll_types, box_ids (source id, destination id) and port equal to the destination inlet.
    - `test_allowlist_is_structured`:
      - every review_blocker_allowlist.json entry has rule, box_ids (list of str), port (int or null), path, severity and a non-empty reason, and none of kind / source_id / outlet / gain_id / inlet / destinations;
      - test_integration_patches defines none of _FANOUT_RE / _BACH_RE / _UNSAFE_GAIN_RE / _DST_NAME_RE / _blocker_match_key / _entry_key (AST);
      - its `_result_key(CriticResult("blocker", "x", "s", path="p", rule="r", box_ids=("a",), port=1)) == ("r", ("a",), 1, "p")`.
    - `test_q24_helpers_are_structured`: tests/test_uninitialized_state.py assigns no `_ID_RE` (AST), and `inspect.getsource` of its `_q24` contains "rule".
  </behavior>
  <action>
**Red.** Append TestCriticResultFields. Run `python3 -m pytest -q -p no:cacheprovider tests/test_consolidation.py > Q/red-t3.txt 2>&1`. It must show failures, with Tasks 1-2's classes still green.

**Green, fields (PD-7):** in critics/base.py:
- extend `__slots__`;
- add keyword-only `rule=""`, `box_ids=()` (stored via tuple()) and `port=None` after path;
- document the three fields in the class docstring, naming PD-8's definitions;
- leave `__repr__` and tag_results unchanged.

**Green, sites (PD-8).** Add `rule=`, `box_ids=` and, where listed, `port=` to every CriticResult call. Never change severity, finding or suggestion text.

Rules by enclosing function (49 calls):
- **dsp_critic:** gen_io_match (2), gain_staging, unsafe_gain_sources (in _trace_gain_inlet; port = the gain inlet).
- **ext_critic review_external, in source order:** ext_missing_include, ext_missing_min_external, ext_min_external_no_class, ext_invalid_identifier, ext_class_mismatch, ext_missing_inlet, ext_missing_dsp_operator, ext_missing_timer, ext_todo. box_ids is () for all.
- **layout_critic:** overlapping_boxes, missing_midpoints (2), out_of_bounds, presentation_coverage, text_contrast (3; box_ids is the text box's own id when it has a real one).
- **m4l_critic:** gain_plugout (2), device_completeness, empty_longnames, parameter_uniqueness, device_quality (2), parameter_enable, missing_info_text, missing_live_banks.
- **package_critic:** beap_output_termination, beap_vca_staging, bach_llll_types (port = the destination inlet), community_extracted, install_state.
- **rnbo_critic:** rnbo_missing_inner_patcher (review_rnbo's inline check), io_completeness (2), param_naming, duplicate_params, target_fitness.
- **structure_critic:** fan_out_without_trigger (port = the source outlet), hot_cold_ordering, trigger_types, dollar_arity, trigger_order, redundant_connections, uninitialized_state.

box_ids come from the local id variables the finding text is built from, deduplicated in the order the text names them. Never include a placeholder such as "?" (a box without an id).

**Green, tests (PD-9, PD-10):**
- **tests/review_blocker_allowlist.json:**
  - rewrite the 2 entries in the PD-9 shape. Take rule / box_ids / port from the live blocker each entry matches today, found by running review_patch on rhythmic-sampler/generated/slot.maxpat; keep severity, a `source` label and the reason text unchanged;
  - rewrite `_doc`'s "Matching keys" sentence to: matching key = CriticResult rule + box_ids + port + path (Q33).
  - Edit the file with the Write tool (it is small); keep 2-space indentation and the existing key order of untouched values.
- **tests/test_integration_patches.py:**
  - `_result_key(result)` returns `(result.rule, tuple(result.box_ids), result.port, result.path)`;
  - `_allow_key(entry)` returns `(entry.get("rule"), tuple(entry.get("box_ids", ())), entry.get("port"), entry.get("path", ""))`;
  - delete the finding-format comment block, the four regexes, `_blocker_match_key` and `_entry_key`;
  - update the allowlist comment's key description;
  - in test_allowlist_key_includes_path, build both CriticResults with the slot fan-out entry's rule, box_ids and port (nested: path "obj-9"). Its assertions are unchanged;
  - keep `re`, which the validate allowlist still uses.
- **tests/test_uninitialized_state.py:**
  - `_q24` keeps results with `r.rule == "uninitialized_state"`;
  - `_q24_ids` and `_corpus_q24` read `r.box_ids[0] if r.box_ids else None`;
  - delete `_ID_RE`; remove `import re` and `_strip_prefix` only if nothing else uses them.

Re-run the guard file and both edited test files; they must pass, except the q29-check baseline case.

**Gate, commit, audit:**
1. Run Gate G with `final-pytest`, then `python3 Q/q33_gate.py allowlist`. Both must exit 0.
2. Commit the 12 task paths: `refactor(critics): CriticResult carries rule, box_ids and port; the integration test and review allowlist key on them instead of parsing finding text (Q33)`.
3. Run `<verify>`, the final audit: it also writes Q/q33-commit-files.txt and checks the stash list. If it fails, HALT and report.
  </action>
  <verify>
    <automated>bash -c 'Q=.planning/quick/261016-tal-implement-q33-in-planning-reviews-2026-1; T=final-pytest; python3 -m pytest -q -p no:cacheprovider --junitxml="$Q/$T.xml" > "$Q/$T.txt" 2>&1; R=$?; tail -1 "$Q/$T.txt"; test $R -le 1 || exit 1; python3 "$Q/q33_gate.py" junit "$Q/baseline-junit.xml" "$Q/$T.xml" || exit 1; python3 "$Q/q33_gate.py" snapshot "$Q/behaviour-$T.json" || exit 1; cmp "$Q/behaviour-before.json" "$Q/behaviour-$T.json" || exit 1; python3 "$Q/q33_gate.py" imports "$Q/imports-$T.json" --baseline "$Q/imports-before.json" || exit 1; python3 "$Q/q33_gate.py" allowlist || exit 1; grep -iq -e failed -e error "$Q/red-t3.txt" || exit 1; grep -q "class TestCriticResultFields" tests/test_consolidation.py || exit 1; python3 -c "import json; d=json.load(open(\"tests/review_blocker_allowlist.json\")); assert all(\"box_ids\" in e and \"rule\" in e for es in d[\"patches\"].values() for e in es)" || exit 1; ST=$(git status --porcelain -- patches) || exit 1; test -z "$ST" || exit 1; S=$(git stash list) && test "$S" = "$(cat "$Q/stash-list-before.txt")" || exit 1; B=$(cat "$Q/base-sha.txt"); C=$(git log --format=%H --fixed-strings --grep="(Q33)" "$B"..HEAD) && set -- $C && test $# -ge 3 || exit 1; for c in $C; do git show --name-only --format= "$c" || exit 1; done > "$Q/q33-commit-files.txt" && test -s "$Q/q33-commit-files.txt" || exit 1; python3 -c "import sys; fm=open(sys.argv[2]).read().split(\"---\")[1]; blk=fm.split(\"files_modified:\")[1].split(\"autonomous:\")[0]; ok={l.strip()[2:].strip() for l in blk.splitlines() if l.strip().startswith(\"- \")}; bad=sorted({l.strip() for l in open(sys.argv[1]) if l.strip() and l.strip() not in ok}); print(\"committed files outside files_modified:\", bad); sys.exit(1 if bad else 0)" "$Q/q33-commit-files.txt" "$Q/261016-tal-PLAN.md" || exit 1; python3 -c "import ast,sys;[ast.parse(open(f).read(),feature_version=(3,10)) for f in sys.argv[1:]]" src/maxpat/critics/base.py src/maxpat/critics/dsp_critic.py src/maxpat/critics/ext_critic.py src/maxpat/critics/layout_critic.py src/maxpat/critics/m4l_critic.py src/maxpat/critics/package_critic.py src/maxpat/critics/rnbo_critic.py src/maxpat/critics/structure_critic.py tests/test_integration_patches.py tests/test_uninitialized_state.py tests/test_consolidation.py tests/test_critic_precision.py'</automated>
  </verify>
  <done>Q/red-t3.txt shows TestCriticResultFields red. Gate G and the allowlist audit passed, then the final `<verify>` passed:
- every CriticResult call names a rule, and every committed result carries consistent box_ids;
- the integration test and allowlist key on (rule, box_ids, port, path) with no finding regex, and the Q24 helpers read rule / box_ids;
- base and new allowlist decisions are identical for every committed result;
- the behaviour snapshot is identical to Step 0, no test status changed, and the 2 q29-check failures are unchanged;
- three `(Q33)` commits touch only files_modified paths, patches/ is untouched, and the stash list is unchanged.</done>
</task>

</tasks>

<threat_model>
Security config: enforcement on (absent = enabled), ASVS level 1, block on high. This is a local refactor: there is no network, auth, crypto, user input or package install. What matters:
- not changing the patches agents generate (users open them in MAX);
- not weakening the test safety net (the allowlists);
- git hygiene in a repo shared by concurrent Claude instances.

## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Builders -> .maxpat on disk -> MAX | A silently changed box dict (key order, id order, missing attribute) is a broken or different patch for the user |
| Critics / validation -> save gate and integration tests | Changed findings or allowlist keys can block valid saves or hide real blockers |
| Concurrent Claude instances -> git | Broad staging or stash can sweep in or strand another instance's work |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-tal-01 | Tampering | Box.structural port changes serialized builder output (key order, _gen_id order, shared args list) | high | mitigate | The snapshot `builders` key compares exact json.dumps bytes (unsorted), layout output and per-box attribute rows, including the bpatcher args identity and inner back-refs, against Step 0 after the tracer and after every task. |
| T-tal-02 | Tampering | Shared helpers or UI-set move silently change validation / critic / layout / analyze output | high | mitigate | The snapshot covers validate_patch, review_patch, analyze() and forced apply_layout over every committed patch file and fixture at the base commit, with PYTHONHASHSEED pinned to 0 (otherwise layout / analyze are nondeterministic). Purpose sets are pinned to their old members; the unification is surfaced to the user, not applied (PD-6). |
| T-tal-03 | Elevation of Privilege | Structured allowlist keys exempt a blocker the regex keys did not (a weakened safety net) | medium | mitigate | `q33_gate.py allowlist` imports the base test module with the base JSON and requires identical decisions for every committed result. The Q24 id extraction is cross-checked against the base regex. The new fan-out key is strictly narrower (PD-9). |
| T-tal-04 | Repudiation | Broad git staging or stash during the task | medium | mitigate | `git add --` / `git commit -- <paths>` only; the final verify audits every `(Q33)` commit's files against files_modified and checks the stash list. |
| T-tal-05 | Denial of Service | Import cycle from maxclass_map / gain_staging / sizing imports breaks `import src.maxpat` | low | mitigate | maxclass_map imports ObjectDatabase lazily; gain_staging imports only walk; the full suite and the Task 2 import probe run before each commit. |
| T-tal-SC | Tampering | npm/pip/cargo installs | high | mitigate | No package-manager install in this plan; only the existing python3, pytest and git are used. Any install the executor finds itself needing is a stop-and-ask (rule 7). |
</threat_model>

<verification>
- Every task's `<verify>` passes. Q/red-t1.txt to red-t3.txt each show guard failures recorded before the change.
- Q/pytest-t1, pytest-t2 and final-pytest (.txt/.xml) each pass `q33_gate.py junit` against Q/baseline-junit.xml: no test removed, only tests.test_consolidation ids added (all passing), and no status change for any test that passed. The expected final summary is 2 failed, 5296 + guard-count passed, 5 xfailed, 1 xpassed.
- The Q/behaviour-*.json files (and Q/behaviour-tracer.json) are byte-identical to Q/behaviour-before.json. Q/imports-*.json add no unused import over Q/imports-before.json. `q33_gate.py allowlist` exits 0.
- `git status --porcelain -- patches` is empty, `git stash list` is unchanged, and the `(Q33)` commits touch only files_modified paths.
- After SUMMARY.md is written, check it:
  - its decisions section names every planner call, with PD-6 the first one named;
  - its `## Q33 item status` section marks the "One UI-control set" item PARTIAL with the measured impact numbers, and the other four items COMPLETE;
  - the remaining required sections exist.

  <automated>bash -c 'S=.planning/quick/261016-tal-implement-q33-in-planning-reviews-2026-1/261016-tal-SUMMARY.md && D=$(awk "/^## Decisions to confirm/{f=1;next} /^## /{f=0} f" "$S") && test -n "$D" && for k in PD-1 PD-2 PD-3 PD-4 PD-5 PD-6 PD-7 PD-8 PD-9 PD-10 PD-11 PD-12 PD-13; do printf "%s\n" "$D" | grep -q -- "$k" || exit 1; done && F=$(printf "%s\n" "$D" | grep -o "PD-[0-9][0-9]*" | head -1) && test "$F" = "PD-6" && I=$(awk "/^## Q33 item status/{f=1;next} /^## /{f=0} f" "$S") && test -n "$I" && U=$(printf "%s\n" "$I" | grep -F "One UI-control set") && printf "%s\n" "$U" | grep -qF PARTIAL && for n in "12 files" "14 files" "29"; do printf "%s\n" "$U" | grep -qF -- "$n" || exit 1; done && for it in "Box factory" "Gain staging" "Geometry helpers" "CriticResult"; do printf "%s\n" "$I" | grep -F -- "$it" | grep -qF COMPLETE || exit 1; done && grep -q "^## Behaviour changes" "$S" && grep -q "^## Confirm in MAX" "$S" && grep -q "^## Follow-ups" "$S"'</automated>
</verification>

<success_criteria>
- Box.structural exists, and all 17 hand-built boxes in builders, rnbo and externals use it, with builder output byte-identical.
- One gain-staging traversal in gain_staging.py serves validation and the DSP critic; one port-geometry helper in sizing.py; no patcher-background wrappers.
- ui_control_names(db) is the DB-derived UI-control authority. The three purpose sets live beside it, pinned, with output unchanged. This Q33 item is PARTIAL by explicit deferral: SUMMARY's `## Q33 item status` says so with the measured impact, and PD-6, the unification decision, is first in `## Decisions to confirm`. The SUMMARY verify checks both.
- CriticResult carries rule / box_ids / port / path. The integration test, the review allowlist and the Q24 helpers use them instead of parsing finding text, with allowlist decisions identical.
- No behaviour change, proven per task by the junit diff, the corpus-wide snapshot and the imports check. The full suite has no failure outside the 2 q29-check baseline failures.
- No doc edits; doc impact is listed in SUMMARY (rule 8).
</success_criteria>

<output>
Create `.planning/quick/261016-tal-implement-q33-in-planning-reviews-2026-1/261016-tal-SUMMARY.md` when done. It must include:
- `## Decisions to confirm`: PD-1 to PD-13, one line each with the choice made. PD-6 comes first, as a multiple-choice question:
  - (a) keep the split purpose sets [current];
  - (b) unify on ui_control_names, with the measured impact: ~14 presentation-coverage warnings in 12 files, analyze() changes in 14 files, 29 more banded control kinds in new layouts;
  - (c) unify with DB-derived per-purpose filters.

  PD-7 (the added `port` field) comes second. The PD-6 line must be the first line in this section that names any PD id.
- `## Q33 item status`: one line per fix-plan Q33 item, using the item's exact name.
  - `Box factory`, `Gain staging`, `Geometry helpers` and `CriticResult`: each marked COMPLETE.
  - `One UI-control set`: marked PARTIAL. The line states that ui_control_names(db) was added and the three purpose sets were co-located and pinned, not replaced, and gives the measured unification impact: "~14 presentation-coverage warnings in 12 files, analyze() changes in 14 files, 29 more banded control kinds in new layouts (see PD-6)".
- `## Behaviour changes`: none observable; say so explicitly. Note that structural boxes now carry the full Box.__init__ attribute set (PD-3), and that `src.maxpat.sizing` gains the public outlet_x / inlet_x / IO_MARGIN, `maxclass_map` gains ui_control_names and the three sets, and CriticResult gains keyword-only fields.
- `## Confirm in MAX` (rule 9): none needed. Builder output is byte-identical and no finding changed. Say so explicitly.
- `## Follow-ups`:
  - PD-6 (b)/(c) if chosen;
  - unifying the gain-staging cord test / oscillator set / severity (PD-4);
  - the embedded-bpatcher `embed: 1` and rnbo~ maxclass drift (PD-3);
  - the save gate key on rule / box_ids (PD-11);
  - the max-critic loop repeat detection;
  - S12's `_route_clear_path` limit (PD-12);
  - layout / analyze nondeterminism under hash randomization (49 of 61 committed files differ between unseeded runs);
  - the 2 q29-check baseline failures.
- Doc impact: max-dsp-agent SKILL.md:42, severity-contract.md:11, max-critic SKILL.md (listed, not edited).
- Evidence:
  - the baseline and final pytest summary lines and the added guard count;
  - the snapshot facts (corpus file count, review result count, builder case count);
  - the allowlist audit line (results / blockers / exempted).
- Commits: the three `(Q33)` hashes.
</output>
