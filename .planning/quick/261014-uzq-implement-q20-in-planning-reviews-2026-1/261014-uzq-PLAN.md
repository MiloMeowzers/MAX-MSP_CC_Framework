---
phase: quick-261014-uzq
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/maxpat/graph.py
  - src/maxpat/critics/base.py
  - src/maxpat/critics/__init__.py
  - src/maxpat/critics/structure_critic.py
  - src/maxpat/critics/dsp_critic.py
  - src/maxpat/critics/package_critic.py
  - src/maxpat/critics/rnbo_critic.py
  - src/maxpat/critics/m4l_critic.py
  - src/maxpat/critics/layout_critic.py
  - src/maxpat/analysis.py
  - src/maxpat/testing.py
  - src/maxpat/hooks.py
  - src/maxpat/walk.py
  - tests/test_critics_recursive.py
  - tests/test_integration_patches.py
  - tests/test_graph.py
  - tests/test_analysis.py
  - tests/test_testing.py
autonomous: true
requirements: [A7, G9, G10, S1]

estimate:
  tokens: 190000
  raw_tokens: 190000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "A fan-out whose branches reconverge at different inlets inside `p synth` (obj-1) is reported by `review_patch` as a blocker whose `CriticResult.path` is `obj-1` and whose finding starts with `[p synth] Fan-out without trigger: `. `save_patch_roundtrip` refuses a new .maxpat containing it (PatchValidationError, the file is not written). The same blocker moved from `p voice` obj-1 to `p voice` obj-2 is a new blocker for the gate."
    - "Every critic reviews every scope that `walk.iter_patchers` yields and tags nested findings with the path: structure, dsp, package, rnbo, m4l, and layout including contrast. A nested finding has `CriticResult.path` set to the box-id chain (`obj-1/obj-2`), and its finding is prefixed with the label chain (`[p synth > gen~] `). Top-level findings keep `path == \"\"` and byte-identical text. On all 69 committed files, Q/triage.py shows top-level `review_patch` results equal to the base snapshot. The only exception is planner decision 4: 5 structure hot/cold warnings on top-level .gendsp files are dropped."
    - "`review_patch` builds exactly one `PatchGraph` per call (`PatchGraph.build` from `walk.iter_patchers`) and at most one ObjectDatabase, and passes that graph to every critic. A critic given `graph=` never rebuilds it. A critic called directly without a graph builds its own, so direct calls recurse too."
    - "The calibration test (`tests/test_integration_patches.py::test_calibration_zero_blockers`) stays green, and committed patches gain 0 nested blockers. Two false positives that only show up in subpatchers are fixed: (1) gen scopes skip the message-ordering checks; (2) a Jitter attribute/method message (for example `exprfill 0 snorm[0]` into jit.matrix, `dim $1 $1` into jit.noise, `scale $1 $1 $1` into jit.bfg) ends a reconvergence path. The 4 terrain-synth fan-out blockers become warnings. The review allowlist key includes the path, so a nested blocker can never be exempted by a top-level entry with the same id."
    - "graph.py (G9): traversal crosses into a `p`/embedded bpatcher only through the inner inlet whose x-rank equals the cord's inlet index, and leaves only through the matching parent outlet. `send`/`receive` and `send~`/`receive~` are bridged by channel name across every scope. `signal_only` follows a cord when the source outlet's `outlettype` is signal/multichannelsignal and the destination inlet accepts signal; it never decides by the `~` suffix. Adjacency is built once per traversal: `signal_path(cycle~)` through `p fx` now reaches the `dac~` beyond it instead of returning `[cycle~]`."
    - "`Patcher.analyze()` recurses into subpatchers. Its inventory counts every scope. Sections, Signal Flow, Control Flow and Parameters each append a `### [p synth]` block per nested scope, after the unchanged top-level content."
    - "`testing.generate_test_checklist` recurses through every non-gen scope and counts object boxes only. Comment and message boxes are ignored, and empty or whitespace text never raises. The G10 repro (`dac~` inside `p synth` plus the comment `metro speed and gen~ notes`) gives the Audio Output test and the audio-on setup step, with no Metro Timing and no gen~ test."
    - "`review_patch`, `generate_test_checklist` and `PatchGraph` (build plus one traversal per file) never raise on any .maxpat or .maxhelp in the installed Max 9 bundle. This is a requires_max test; the checklist raises IndexError on 1 bundle file at base."
    - "No file under patches/ changes. The full suite is green: base 3813 passed / 1 xfailed / 1 xpassed, plus the new tests. Every changed .py parses as Python 3.10. There are exactly 3 `(Q20)` commits."
  artifacts:
    - path: "src/maxpat/graph.py"
      provides: "Dict-level shared graph (PatchGraph, Scope, Edge, outlet_is_signal, resolve_patcher) built from walk.iter_patchers, with port-exact / s-r-bridged / outlettype-signal traversal; GraphMixin downstream/upstream/signal_path/_build_adj delegate to it"
      contains: "class PatchGraph"
    - path: "src/maxpat/critics/base.py"
      provides: "CriticResult.path slot and tag_results path/prefix helper"
      contains: "path"
    - path: "src/maxpat/critics/__init__.py"
      provides: "review_patch: one PatchGraph and one ObjectDatabase per call, graph passed to every critic, scope-wide dispatch detection"
      contains: "PatchGraph.build"
    - path: "src/maxpat/critics/structure_critic.py"
      provides: "Per-scope fan-out / hot-cold / duplicate checks on the shared graph, gen-scope ordering skip, Jitter setter path end"
      contains: "graph"
    - path: "src/maxpat/critics/layout_critic.py"
      provides: "Per-scope layout checks including contrast against each scope's own patcher background"
      contains: "graph"
    - path: "src/maxpat/analysis.py"
      provides: "Recursive analyze() over walk.iter_patchers scopes resolved to inner Patchers"
      contains: "iter_patchers"
    - path: "src/maxpat/testing.py"
      provides: "Recursive, object-box-only checklist"
      contains: "iter_patchers"
    - path: "tests/test_critics_recursive.py"
      provides: "A7/S1 critic recursion, parity, shared-graph, gen-skip, Jitter-setter, gate, purity, robustness tests and the requires_max bundle sweep"
      contains: "requires_max"
    - path: "tests/test_graph.py"
      provides: "G9 port-exact crossing, s/r bridging, outlettype signal test, adjacency-once tests; inverted every-inlet test"
      contains: "send~"
  key_links:
    - from: "src/maxpat/graph.py"
      to: "src/maxpat/walk.py"
      via: "PatchGraph.build -> walk.iter_patchers (the single dict walker); labels/paths via walk.path_ids / walk.path_prefix; names via walk.box_name / walk.box_args"
      pattern: "iter_patchers"
    - from: "src/maxpat/critics/__init__.py"
      to: "src/maxpat/graph.py"
      via: "review_patch builds PatchGraph once and passes graph= to every critic"
      pattern: "PatchGraph.build"
    - from: "src/maxpat/critics/base.py"
      to: "src/maxpat/walk.py"
      via: "tag_results sets CriticResult.path = walk.path_ids(path) and prefixes walk.path_prefix(path)"
      pattern: "path_prefix"
    - from: "src/maxpat/hooks.py"
      to: "src/maxpat/critics/base.py"
      via: "_finding_key reads CriticResult.path through getattr, keeping identically labelled nested critic blockers apart"
      pattern: "getattr\\(result, \"path\""
    - from: "tests/test_integration_patches.py"
      to: "src/maxpat/critics/base.py"
      via: "allowlist signature key includes CriticResult.path (entry `path`, default \"\")"
      pattern: "path"
    - from: "src/maxpat/graph.py"
      to: "src/maxpat/validation.py"
      via: "signal_only destination acceptance -> validation._is_container_box / validation._inlet_accepts_signal (lazy import)"
      pattern: "_inlet_accepts_signal"
    - from: "src/maxpat/analysis.py"
      to: "src/maxpat/graph.py"
      via: "analyze() enumerates walk.iter_patchers(self.to_dict()) scopes and resolves each to its inner Patcher via graph.resolve_patcher"
      pattern: "resolve_patcher"
    - from: "src/maxpat/testing.py"
      to: "src/maxpat/walk.py"
      via: "checklist names from walk.object_name over walk.iter_patchers scopes"
      pattern: "object_name"
---

<objective>
Implement Q20 of `.planning/reviews/2026-10-11-fix-plan.md`: review A7 (continued), G9 and G10, with S1 (shared walker plus shared graph). Run after Q19.

Q19 made `validate_patch` recurse. The critics, `analyze()`, the /max-test checklist and the graph traversal still look only at the top level, even though 41% of committed boxes are nested. Q20 adds:
- **Recursive critics (A7).** structure, dsp, package, rnbo, m4l, and layout including contrast each review every scope from `walk.iter_patchers` (the Q19 walker; no second dict walker). Nested findings are tagged the same way Q19 tags ValidationResult: a `CriticResult.path` slot holding the box-id chain, and a `[label > label] ` prefix on the finding. Top-level findings stay byte-identical, so save-gate keys and existing tests are stable.
- **Shared graph (S1).** A dict-level `PatchGraph` in `src/maxpat/graph.py` holds every scope's boxes and parsed cords. `review_patch` builds it once per call and passes it to every critic. It replaces the per-check adjacency rebuilds.
- **graph.py (G9).** Port-exact subpatcher crossing, bridging across send/receive and send~/receive~, a signal test by outlettype instead of the `~` name, and adjacency built once. `Patcher.downstream`, `upstream` and `signal_path` run on it.
- **`analyze()`** recurses into subpatchers.
- **Checklist (G10).** It recurses and counts object boxes only.
- **Calibration.** It stays green. The critic false positives that only show up in subpatchers are fixed: gen-scope ordering, and Jitter attribute-setter paths.

Purpose: the critics, the save gate, the analysis and the test checklist see the whole patch, not just its top level.

Output: three commits, one per task, each with `(Q20)` in its message, and Q/261014-uzq-SUMMARY.md. Nothing is pushed.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@CLAUDE.md
@.planning/quick/261014-t1y-implement-q19-in-planning-reviews-2026-1/261014-t1y-SUMMARY.md

Spec: `.planning/reviews/2026-10-11-fix-plan.md`. Read "## Rules for every task" and "### Q20: Recursive critics, analysis, checklist and graph".

Evidence: `.planning/reviews/2026-10-11-repo-review.md`. Read rows A7, G9 and G10 (grep `| A7 |`, `| G9 |`, `| G10 |`) and row S1 in "## 2" (grep `| S1 |`).

Q19 prior art for the process and for the walker contract: `src/maxpat/walk.py`, and `tests/test_validation_recursive.py` (helper style, the gate test, the bundle sweep).

Severity semantics: `.claude/skills/references/severity-contract.md`. Read it; do not edit it (rule 8).

**Line numbers in the spec and review have drifted.** Find every edit location by function name.
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

Additions for this execution environment:
- **Q** = `.planning/quick/261014-uzq-implement-q20-in-planning-reviews-2026-1`. Step-0 files, red-run outputs, Q/triage.py and its JSON outputs, and the final pytest output all go in Q. They stay untracked and are never staged. The orchestrator commits PLAN and SUMMARY.
- **Execution** is sequential, on `main`, in the main checkout (no worktree). Local main (`ad3213e4`) is ahead of origin/main (`49fbfd4b`).
  - **Hard precondition:** `git merge-base --is-ancestor ad3213e4 HEAD` succeeds (Q19 landed).
  - **Hard precondition:** `git diff --quiet HEAD -- src/maxpat/graph.py src/maxpat/critics src/maxpat/analysis.py src/maxpat/testing.py src/maxpat/hooks.py src/maxpat/walk.py tests/test_integration_patches.py tests/test_graph.py tests/test_analysis.py tests/test_testing.py` succeeds, and `tests/test_critics_recursive.py` does not exist.
  - If either fails, HALT and report which.
- **Step 0 (before any edit):**
  - Record `git rev-parse HEAD` in Q/base-sha.txt.
  - Record `git stash list` in Q/stash-list-before.txt (empty at planning).
  - Run the full suite (`python3 -m pytest -q -p no:cacheprovider`) into Q/baseline-pytest.txt. Expected at ad3213e4: **3813 passed, 1 xfailed, 1 xpassed** (about 65 s). If the figure differs, record it; do not fix it.
  - Write Q/triage.py (spec in `<reference_data>`), then run `python3 Q/triage.py --base Q/triage-base.json`. This must happen **before any source edit**, because it snapshots base critic behaviour.
  - **Prove that the gate can fail (still before any source edit).** Record all three runs, with their exit codes, in Q/triage-step0.txt:
    1. `python3 Q/triage.py --selftest` must exit 0, with all 11 synthetic cases passing.
    2. `python3 Q/triage.py --check Q/triage-base.json Q/triage-step0-nodrop.json --no-gen-drop` must exit 0 with top_mismatch=0 and nested=0. This proves the live comparison matches unchanged code to its own snapshot.
    3. `python3 Q/triage.py --check Q/triage-base.json Q/triage-step0-drop.json` must exit **1**. Every top_mismatch key must end in `.gendsp`, and those files must hold exactly the 5 GEN_ORDER records. This proves that live data trips the gate when the D1 gen skip is not implemented yet.
  - If any of the three runs behaves otherwise, fix Q/triage.py and re-run all three. Do not start Task 1 until all three behave as stated.
- **Edit scope.** Only the 18 `files_modified` paths may change, each only in a task that lists it in `<files>`.
  - **Never edit:**
    - `patches/**`, CLAUDE.md, TECHNICAL.md, README.md, `.claude/**` (including severity-contract.md and the max-critic skill);
    - `src/maxpat/validation.py` (its helpers are reused read-only), `db_lookup.py`, `io_resolvers.py`, `patcher.py`, `utils.py`, `layout.py`, `aesthetics.py`, `m4l_polish.py`, `builders.py`, `rnbo_validation.py`, `tools/**`.
  - `hooks._iter_patchers` and `utils.get_box_name` keep their own code (planner decision 15).
- **Existing tests.**
  - The only existing test whose assertion changes is `tests/test_graph.py::TestSubpatcherCrossing::test_downstream_includes_inner_inlets`. It asserts that crossing enters every inner inlet, which is exactly the retired G9 behaviour, so it is renamed and inverted in Task 3.
  - If any other existing test fails, first treat it as a code bug and fix the code.
  - Only if it asserts the same retired behaviour may it be inverted the same way, and it must then be listed in SUMMARY. The retired behaviours are: critics or analysis or checklist not looking inside a subpatcher, crossing every inner inlet, and the `~`-name signal filter.
  - Anything else: HALT and ask with options (rule 7). Never weaken an assertion.
- **Committed-patch triage (conditional, rule 3).** Planning measured 0 nested blockers after the planner-decision-4 and -5 fixes. If the executor observes any nested blocker on a committed patch:
  - a false positive: fix the critic within this task's files;
  - a true positive in a non-calibration project: add a path-scoped entry with a written `reason` to `tests/review_blocker_allowlist.json` (the single permitted exception to the edit scope; stage it with that task's commit) and list it in SUMMARY;
  - a true positive in a calibration project: HALT and ask (calibration patches may never be allowlisted).
  - New nested warnings and notes are expected. They are listed in SUMMARY, never allowlisted, and never fixed by editing patches.
- **Commits.** One commit per task, each message ending `(Q20)`: `git add -- <task files>`, then `git commit -m "..." -- <task files>`. Never `git push`.
  - Each task's code and tests reach green **before** its commit, so a task normally needs exactly one commit.
  - **If the Task 3 count check (`exactly 3`) fails:**
    - Never rewrite history: no reset, rebase, amend of an earlier task's commit, squash or stash.
    - Write `git log --oneline --fixed-strings --grep="(Q20)" "$(cat Q/base-sha.txt)"..HEAD` to Q/q20-commits.txt.
    - **Fewer than 3:** a task's commit is missing. Make it with that task's files, then re-run the verify.
    - **More than 3:** for example, a fix found after a task's commit, made as its own `(Q20)` commit with only that task's files. Keep the extra commits.
      - Run the remaining checks of the Task 3 verify by hand: the stash comparison, and `git show --name-only` over **every** listed commit into Q/q20-commit-files.txt with no `patches/` path. Record their results in Q/commit-check.txt.
      - Report each extra commit under SUMMARY "Deviations", with its hash, files and reason. The verifier judges it; the executor does not re-run the automated verify with a weakened count.
- **Tests never write to the repo.** Each verify compares `git status --porcelain` before and after its pytest run. Tests that save use `tmp_path` and copies of the `_isolate_git_env` autouse fixture and the `_git` / `_repo` helpers from `tests/test_validation_recursive.py` (copied, not imported).
- **Python 3.10.** The local interpreter is 3.14. Avoid 3.11+ APIs: `typing.Self`, `itertools.batched`, `except*`, `match`, `tomllib`. Every changed .py passes `ast.parse(..., feature_version=(3, 10))`. `from __future__ import annotations` is used, so `X | None` annotations are fine. CI runs 3.10 and 3.12 without Max, so every test that is not `requires_max` must pass with only the repo DB.
- **Imports.**
  - graph.py may import `walk` at module level. Patcher imports graph, and walk imports only db_lookup and io_resolvers, so there is no cycle.
  - graph.py imports `validation` only inside the function that needs it.
  - The critics import `PatchGraph` / `outlet_is_signal` from graph.
  - analysis.py and testing.py import walk. analysis.py also imports graph's `resolve_patcher`.
  - Nothing new imports `critics` from graph, walk, analysis or validation.
- **Shell.** The shell is zsh, so multi-step gates are wrapped in `bash -c '...'`. Python one-liners inside double quotes avoid `!=` and `$`.
</rules>

<planner_decisions>
The fix plan leaves these open, and no CONTEXT.md exists for Q20. They are recorded here so the executor does not need to stop. Each one follows a Q19 precedent or a live measurement (`<observed_facts>`).

1. **Path tagging (the Q19 convention, applied to critics).**
   - `CriticResult` gains the slot `path` and a fourth constructor parameter `path: str = ""`. Existing 3-argument constructions keep working, and `__repr__` is unchanged.
   - `critics/base.py` adds `tag_results(results, path)`. For a non-empty walk path tuple, it sets `r.path = walk.path_ids(path)` and `r.finding = walk.path_prefix(path) + r.finding`. For `()` it touches nothing. Suggestions are never prefixed.
   - Top-level findings keep `path == ""` and byte-identical text.
   - `hooks._finding_key` already appends `getattr(result, "path", "")`. Only its docstring changes (Task 3).
2. **The shared graph (S1): a dict-level `PatchGraph` in graph.py.**
   - `PatchGraph.build(patch, scope=None)` runs one `walk.iter_patchers(patch, scope=scope)` pass.
   - `graph.scopes` is in walker pre-order, top first. There is **always** a top scope. When the walker yields nothing (no usable patcher), the top is an empty max scope with patcher `{}`, so the top-level output of every critic on degenerate input is unchanged.
   - Each `Scope` carries:
     - `path` (the walk tuple), `key` (`walk.path_ids(path)`) and `prefix` (`walk.path_prefix(path)`);
     - `context` (max/gen/rnbo/poly/bpatcher) and `scope` (`walk.scope_of(context)`);
     - `patcher` (the raw dict);
     - `boxes`, built exactly like the critics' `box_lookup` today. Iterate the entries in order and skip falsy ids, so a duplicate id keeps its first position and its last box.
       - The box of an entry is `entry["box"]` when that is a dict. Otherwise it is the entry itself when the entry is a dict with an `id`; m4l_critic accepts bare boxes today.
     - `box_list`: every box with a truthy id, in array order, duplicates included. This is the layout critic's list.
     - `edges`: one `Edge(src, outlet, dst, inlet, signal, line)` per well-formed cord, **in line order**.
       - The patchline is `entry.get("patchline", entry)` (critics accept bare patchlines today).
       - `source` and `destination` must be lists or tuples of length ≥ 2, ids must be str or int, and ports must be int (not bool). Anything else is skipped and never raises.
       - `signal = outlet_is_signal(boxes.get(src), outlet)`.
     - `out_edges[id]` and `in_edges[id]`, both in line order;
     - its parent scope and container box id.
   - Scopes are identified internally by the tuple of path ids, never by splitting `key`. `graph.children(scope)` and `graph.subtree(scope, box_id)` (the container's inner scope plus everything below it, in pre-order) come from the same structure.
   - `outlet_is_signal(box, outlet)` is moved from `structure_critic._outlet_is_signal` without changing its semantics. The `outlettype` entry at that index decides (`signal` or `multichannelsignal`). Only when there is no entry does it fall back to `walk.box_name(box).endswith("~")`. `structure_critic._outlet_is_signal` stays as an alias.
   - Critics must iterate `scope.edges` / `scope.boxes` / `scope.box_list` in their stored order, never a sorted adjacency. That keeps finding order and destination lists byte-identical.
   - The graph is read-only: no critic or graph code mutates the patch dict.
3. **Critic checks stay scope-local.** Each check runs on one scope's own boxes and edges, exactly as it ran on the top level before.
   - Q20 adds no cross-scope critic traversal. For example, an oscillator in `p` reaching a top-level `dac~`, a gain~ in `p` reaching plugout~, and BEAP chains across bpatchers are not followed.
   - This keeps every top-level finding byte-identical, and therefore the save-gate keys and the calibration baseline.
   - Cross-scope critic flow, now possible on the G9 traversal, is a SUMMARY follow-up.
4. **Gen scopes skip the message-domain rules.** This applies to every gen scope, including a top-level .gendsp, following the Q19 decision-4 precedent. Gen is synchronous per-sample dataflow, so Rule #3 ordering does not apply.
   - **structure** runs only the duplicate-patchline check in a gen scope.
   - **dsp** and **package** skip gen scopes.
   - **m4l** per-scope checks skip gen scopes.
   - **layout** (including contrast) and **rnbo** run in every scope.
   - The poly, bpatcher and rnbo contexts run the max rules.
   - Allowed top-level delta (D1): the 5 base structure warnings `Hot/cold inlet ordering issue: 'codebox' ...` on top-level .gendsp files disappear. Q/triage.py accounts for them as `gen_dropped`.
5. **Jitter setter path end (the subpatcher-only false positive).** This is in structure_critic's reconvergence walk (`_paths_reconverge`), and it covers the first hop from the fan-out source as well.
   - **Setter message box:** a box with maxclass `message` where every comma-separated segment starts with a symbol selector. Segment boundaries are unescaped commas: a token that is `,` or ends in `,` but not `\,`.
   - A selector is a symbol when it is not a number, does not start with `$` or `;`, is not one of `bang`, `outputmatrix`, `jit_matrix` or `jit_gl_texture`, and does not start with `get`.
   - **The rule:** a cord from a setter message box into a box whose `walk.box_name` starts with `jit.` records the hit at that box but does not expand past it.
   - Jitter treats these messages as attribute or method calls that emit nothing. The evidence is the user-confirmed terrain-synth, where each such message needs a separate `bang` to output.
   - A message containing `bang` (for example `exprfill ..., bang`) still propagates.
   - Measured: this demotes exactly the 4 nested terrain-synth blockers to warnings, and changes 0 top-level findings.
6. **package critic.**
   - `packages_used` is collected once across all non-gen scopes, which decides the BEAP and Bach dispatch.
   - The checks then run per scope, in today's family order (BEAP, Bach, community, install-state).
   - One community `warned_packages` set and one install-state `flagged` set are shared across all scopes of a call. An unextracted package or a missing object therefore reports once per patch, at the first scope (pre-order) where it appears.
   - The BEAP signal adjacency uses `outlet_is_signal`, so `multichannelsignal` counts (S1). The "bpatcher source = signal" special case is kept.
   - `_has_package_boxes` looks across all non-gen scopes.
7. **dsp critic.**
   - The gen~/mc.gen~ I/O check, gain staging and unsafe gain sources run per non-gen scope.
   - `code_context["gen~_code"]` (keyed by top-level box id) applies to the top scope only, because inner ids collide with outer ones.
   - The signal test is `edge.signal`. It is identical on committed patches: 0 of 6,932 cords lack an outlettype entry.
   - Text reads go through `walk.box_text` / `walk.box_tokens`.
8. **rnbo critic.**
   - rnbo~ boxes (`walk.box_name == "rnbo~"`) are found in every scope. For each one, today's checks run on its inner patcher. The no-inner-patcher, I/O completeness, naming, duplicates and target checks are all reported at the path of the scope that holds the rnbo~ box, like the Q19 Layer-5 rule.
   - Params are collected across the rnbo~ box's whole subtree (`graph.subtree`, pre-order), for naming, duplicates and the target param count.
   - A param box below the rnbo~'s top inner patcher is referenced in a duplicate message by the id chain from that inner patcher (`obj-7/obj-3`). A box in the top inner patcher keeps its plain id, so today's messages are unchanged.
   - `_has_rnbo_boxes(patch_dict, graph=None)` looks across all scopes.
9. **m4l critic.**
   - `detect_m4l_device_type(patch_dict, *, graph=None)` collects marker names across all non-gen scopes.
   - **Device-level checks** run once and are reported at path `""`:
     - completeness (required names in any non-gen scope);
     - openinpresentation / devicewidth on the top patcher;
     - duplicate parameter_longname across all scopes (a nested box is referenced by `<scope key>/<id>`, a top-level box by its plain id);
     - live.banks presence against parameter controls in any scope.
   - **Per-scope checks** run on every non-gen scope and are tagged:
     - gain stage on a scope-local signal path to a plugout~;
     - ezdac~;
     - parameter_enable on parameter-capable live.* controls;
     - empty-longname warning;
     - missing info text.

     The two former ad-hoc `box["patcher"]` recursions are replaced by graph scopes.
   - Order within the top level is today's: gain/ezdac, completeness, uniqueness, quality, info text, live.banks. Nested per-scope results follow in pre-order.
10. **layout critic, including contrast.**
    - Every check runs per scope, gen included.
    - Contrast resolves against each scope's own patcher dict (`bgcolor` / `editing_bgcolor` / `locked_bgcolor`, else the palette canvas, as today).
    - `_box_label` uses the first `walk.box_tokens` token, else the maxclass, else `unknown`. Whitespace text no longer raises.
    - Presentation coverage is per scope: active when that scope has a presentation box.
    - The theme-default-text false positive is Q26 (review E7; `.claude/skills/references/ui-presets.md` "Max 9 Theme Defaults"). It is **not** fixed here. Nested low-contrast warnings are expected, are listed in SUMMARY as Q26, and are never recoloured.
    - The module docstring's "only checks the top-level patcher" note is replaced.
11. **Allowlist key (tests/test_integration_patches.py).**
    - The signature key gains the path: a result key is the finding-derived key plus `getattr(result, "path", "")`, and an entry key is the entry key plus `entry.get("path", "")`.
    - `_is_allowlisted` takes the CriticResult, and `test_review_allowlist_entries_are_live` builds its live keys the same way.
    - The existing slot.maxpat entry is top-level, so `tests/review_blocker_allowlist.json` needs no edit.
12. **G9 traversal (Task 3).**
    - `PatchGraph.downstream(scope, box_id, *, signal_only=False, db=None)` and `upstream(...)` return `(scope, box_id)` pairs in BFS discovery order, start excluded. At each node, neighbours are taken from `out_edges` / `in_edges`, stable-sorted by outlet (downstream) or inlet (upstream). Two visited sets apply: one over (scope, box), and one over (container, port) crossings.
    - **Port-exact crossing** applies only to containers whose inner scope context is max or bpatcher. Inner `inlet`/`outlet` boxes are ranked by `(patching_rect x, array index)`, as in `hooks._port_ranks` and `Patcher.get_inlets`.
      - **Downstream:** reaching container C at inlet i adds C to the result and enters only inner inlet rank i. C's own out-edges are not expanded. Reaching inner outlet rank k expands C's parent out-edges from outlet k only.
      - **Upstream:** this mirrors downstream, through outlet rank k in and inlet rank i out.
      - Gen, rnbo and poly containers, and containers without an embedded patcher, are **opaque**: they are expanded like ordinary boxes and never entered.
    - **Bridging.**
      - Senders are `send`/`s` (control) and `send~`/`s~` (signal). Receivers are `receive`/`r` and `receive~`/`r~`, the set `AnalysisMixin._resolve_send_receive_pairs` uses today.
      - The channel is the first `walk.box_args` token; a box with no args does not bridge.
      - Downstream at a sender enqueues every receiver of the same kind and channel in any scope; upstream at a receiver enqueues the senders.
      - `signal_only` bridges only the signal kind.
    - **signal_only edge rule.**
      - Port boxes (maxclass `inlet`/`outlet`) and crossing containers are transparent: they are only ever reached through a followed signal edge, so their out-edges are not type-tested.
      - Any other source's edge is followed iff `edge.signal` holds and the destination accepts signal at that inlet. A destination accepts signal if `validation._is_container_box(dst)` or `validation._inlet_accepts_signal(dst, inlet, db)`; it is permissive when `db` is None.
      - Measured DB facts behind this rule: print inlet 0 is control-only, snapshot~/`*~`/meter~/dac~ inlets accept signal, and `p` inlet 0 is listed as control, hence the container check.
    - **GraphMixin.**
      - `downstream` and `upstream` keep the `ValueError` for a foreign box. They build `PatchGraph.build(self.to_dict())` **once** per call and map `(scope, id)` pairs back to Box objects through `resolve_patcher(self, scope.path)`, which follows `_inner_patcher` by box id. Pairs in scopes without a Patcher, such as mc.gen~ `data.patcher`, are dropped.
      - `signal_only` passes `self.db`.
      - `signal_path` keeps its composition (upstream reversed + box + downstream). The box itself counts as signal when its `outlettype` has a signal or multichannelsignal entry, or, with no `outlettype` list, when its name ends in `~`.
      - `_build_adj(signal_only=True)` keeps its signature and return shape, but filters with `outlet_is_signal` plus destination acceptance instead of the name suffix. `_traverse` no longer rebuilds adjacency per node.
      - `connected_components` is unchanged.
13. **Recursive analyze() (Task 3).**
    - `analyze()` enumerates `walk.iter_patchers(self.to_dict())` (the single walker) and resolves each nested scope to its inner Patcher with `resolve_patcher`. Unresolvable scopes are skipped.
    - Overview and Subpatchers are unchanged, because they are already recursive.
    - **Inventory** is one table counting every scope: gen-context boxes count as `Gen`, rnbo-context boxes as `RNBO`, everything else `_classify_domain`. When nested scopes exist, it is followed by the line `Counts include N subpatcher scope(s).`
    - **Sections, Signal Flow and Control Flow** emit the top-level body exactly as today. Then, for each nested max/bpatcher/poly scope whose facet has content, they add a `### [p synth > ...]` heading (`walk.path_prefix(path).strip()`) followed by that inner Patcher's facet lines.
    - **Parameters** lists top-level controls as today, then nested controls as `- [p synth] label (maxclass)`. `(none detected)` appears only when no scope has any.
    - Flow across subpatcher boundaries in the analysis output (review §4.4 item 12) is a SUMMARY follow-up.
14. **Checklist (Task 3).**
    - Names come from every scope of `walk.iter_patchers(patch_dict)` except gen-context scopes, whose GenExpr operators are not Max objects.
    - For every box whose maxclass is not `comment` or `message`, the name is `walk.object_name(box)`. None, meaning structural or empty, is skipped.
    - Full-text entries (`metro 500`) are dropped: `has_metro` still matches the name `metro`.
    - The step texts are unchanged.
15. **Out of scope (rule 7), listed in SUMMARY:**
    - `hooks._iter_patchers` (save-gate cord/port walker; its path labels differ from walk's);
    - `utils.get_box_name` (only m4l_polish and tests use it once the critics stop);
    - `layout.py`, `aesthetics.py` and `m4l_polish.py` walkers;
    - theme-aware contrast (Q26);
    - cross-scope critic flow;
    - trigger and `$N` checks (Q21);
    - RNBO data gaps;
    - embedded poly~ port crossing (`in N`/`out N`; 0 in committed patches).
16. **Bundle-only nested findings are out of scope.** The sweep is a no-crash test only. 917 nested blockers in C74's own patches, mostly right-to-left fan-out, are not triaged.
</planner_decisions>

<assumption_delta_decision>
**Delta (singular to plural).**
- "The patch a critic reviews" meant its top-level patcher; now it means every embedded patcher, each with its own context. A critic finding's identity grows from `(severity, finding)` to include the **scope path**.
- "The graph" meant one Patcher's own lines; now it means every scope plus port and channel links.

**Decision: promote, matching Q19.**
- `CriticResult.path` is part of what a finding is. The save-gate key (already path-aware since Q19) and the review allowlist key use it.
- The top level is just the `""` path.
- Finding text keeps its human prefix for display. Structured `rule`/`box_ids` fields stay with Q33 (review S7).

**Invariant test (accepted):** `test_nested_parity_with_top_level`, parametrized over one fixture per per-scope critic check. Any content wrapped in `p synth` must produce exactly the top-level findings for that content, with the `[p synth] ` prefix and path `obj-1`. It goes red if a future change reintroduces the top-level-only assumption.

**Planner-contribution gates** (run at planning):
- **API coverage.** In-process critic, graph and analysis code over local JSON. No external API, so there is no checkpoint and no COVERAGE.md.
- **Assumption delta.** A quick task has no ROADMAP section, so the delta above is recorded by hand.
- **Schema push.** No ORM or schema files.
- **Package legitimacy.** No installs.
- **Security.** ASVS level 1, block on high; see `<threat_model>`.
</assumption_delta_decision>

<scope_acceptance>
**The scope is accepted, not split.** A quick task allows at most 3 tasks, and Q20 is one fix-plan item. Each task stays inside a reviewable, verifiable budget for these reasons.

- **Per-task budget** (raw, chars/4 over what each task reads, writes and verifies; the calibration factor is 1 with no history):

  | Task | Budget | Breakdown |
  |---|---|---|
  | 1 | about 70k | reads walk, graph, structure, `__init__`, hooks excerpts and the integration test (about 25k); writes PatchGraph and the structure rework (about 15k) and tests (about 15k); verify output (about 15k) |
  | 2 | about 65k | reads 5 critics (about 30k); writes them (about 15k) and tests (about 12k); verify output (about 8k) |
  | 3 | about 55k | reads graph, analysis, testing and tests (about 20k); writes traversal (about 10k), analysis/testing (about 8k) and tests (about 10k); full suite and SUMMARY (about 7k) |

  Each is well under half of the executor's context.
- **The file counts (6 / 7 / 9) exceed the 5-file heuristic on purpose.**
  - Task 2's critic edits all follow one pattern: a `graph=` keyword, a per-scope loop and `tag_results`.
  - In Task 3, `hooks.py` and `walk.py` are docstring-only, and 4 of the 9 paths are test files.
- **Blast radius is bounded.** Each task commits on its own, after a verify that re-runs the triage gate (now self-tested) and the calibration test.
- **Task 3 has internal sub-gates.** It is staged into three independent features, each with its own focused gate, run and passed before the next feature starts (see Task 3 Steps B-D). A failure in one feature is therefore localized before the full-suite verify.
- **Fallback if Task 3 still overruns.** If the executor's context nears its limit during Task 3, it stops after the last passed sub-gate without committing and reports a checkpoint naming the completed sub-steps. It never commits a partial Task 3 under the `(Q20)` tag.
</scope_acceptance>

<observed_facts>
All figures were measured live at planning on this Mac (Max 9.2.0), at HEAD `ad3213e4` (local main; origin/main `49fbfd4b`). Probes are in the planner scratchpad, not the repo.

**Suite:** 3813 passed, 1 xfailed, 1 xpassed, in 65 s. The working tree is clean apart from untracked `.planning/quick/**` files.

**Code today**
- `critics/__init__.py`:
  - `review_patch` calls dsp, structure and layout always; rnbo when `_has_rnbo_boxes` finds a top-level rnbo~; m4l when `detect_m4l_device_type` finds a top-level marker; ext when there is code; package when `_has_package_boxes` finds a top-level package object.
  - With `db=None`, `_has_package_boxes` constructs an ObjectDatabase on **every** call.
- Every critic reads only `patch_dict["patcher"]["boxes"/"lines"]` and rebuilds its own `box_lookup` and line parse per check:
  - structure: fan-out, hot/cold, duplicates;
  - dsp: gen I/O, `_check_gain_staging` signal_adj, `_check_unsafe_gain_sources` with three line passes;
  - package: `_build_signal_adjacency` twice, using `== "signal"`;
  - m4l: `_check_gain_plugout` rev graph;
  - layout: five checks.
- m4l `_collect_parameter_longnames` and `_check_missing_info_text` recurse through `box["patcher"]` only, without paths.
- `critics/base.py` `CriticResult.__slots__` is `("severity", "finding", "suggestion")`.
- Names come from `utils.get_box_name`, which crashes on whitespace text, and from `rnbo_critic._get_inner_object_name` and `layout_critic._box_label` (both use `text.split()[0]`). `m4l_critic` imports `structure_critic._outlet_is_signal`.
- `graph.py` (GraphMixin):
  - `_build_adj(signal_only)` filters both endpoint names by `~`;
  - `_enqueue_neighbors` calls `_build_adj` for every dequeued node;
  - `_cross_subpatcher` adds **every** inner inlet and outlet;
  - there is no send/receive handling.
- `analysis.py`:
  - recursive only in `_count_recursive` and `_hierarchy_lines`;
  - the inventory, sections, signal flow, control flow and parameters cover the top level only.
- `testing._extract_object_names` takes `text.split()[0]` of every box (comments and messages included) and adds the full text. It never recurses.
- `hooks._finding_key` returns `(origin, template, ids, removal, getattr(result, "path", ""))`. Its docstring says the path is `""` for critic findings.
- `tests/test_integration_patches.py`:
  - `_blocker_match_key` keys are `("fanout", source_id, outlet)` / `("bach_llll", ...)`, with no path;
  - the regexes use `.search`, so a prefixed nested finding would match a top-level entry by id.

**Committed patches** (69 files: 56 .maxpat, 1 .maxhelp, 12 .gendsp)
- Walk contexts: max 167 (57 top + 110 nested) and gen 68 (12 top + 56 nested). There are no rnbo, embedded poly or embedded bpatcher scopes.
- There are 0 M4L markers (plugin~/plugout~/live.thisdevice) in any scope. Package objects appear only nested in `rhythmic-corpus-chopper.maxpat`, and its top-level package review is `[]`.
- 0 of 6,932 cords lack an outlettype entry at their source outlet.
- Base top-level `review_patch` over the 69 files: 1164 warnings, 216 notes, and 1 blocker (the allowlisted `slot.maxpat` obj-1 outlet 1).
- Top-level .gendsp critic output includes 5 structure warnings `Hot/cold inlet ordering issue: 'codebox' ...`. These are dropped under decision 4.
- **Prototype recursion** (each nested scope wrapped as `{"patcher": inner}`, each critic called directly):
  - 0 crashes;
  - **4 nested blockers**, all structure fan-out in terrain-synth, a calibration project:
    - `[p terrain-source]` / `[p terrain-source-b]`: `inlet` obj-2 outlet 0 fans out to `dim $1 $1` → jit.noise and `expr` → `scale $1 $1 $1` → jit.bfg, "reconverging" on `jit.xfade` obj-64;
    - `[p terrain-view-a]` / `[p terrain-view-b]`: `loadbang` obj-10 fans out to `exprfill 0 snorm[0]` / `exprfill 0 snorm[1]` → jit.matrix → `jit.pack` obj-19 inlets 0 and 2.
  - With the decision-5 rule prototyped, exactly those 4 become warnings. No top-level structure result changes on any non-gen file.
  - Nested warnings and notes, for SUMMARY:
    - layout low contrast about 786 (max scopes; the theme-default false positive, Q26);
    - missing midpoints about 485 (max) + 54 (gen);
    - overlapping boxes 77;
    - hot/cold 79 (max) + 36 (gen, removed by decision 4);
    - fan-out warnings about 18 (+4 demoted);
    - 3 Bach llll notes.
- `Patcher.from_dict(d).analyze()` and `.to_dict()` run without error on all 57 committed .maxpat/.maxhelp files.

**Max 9 bundle** (`/Applications/Max.app/Contents/Resources/C74`): 3,139 patcher files, all parsed.
- Walk contexts: max 10,111, bpatcher 1,007, gen 292, rnbo 709 (8,980 nested).
- Prototype nested critics: 0 crashes, about 2.8 s.
- `generate_test_checklist` raises `IndexError` on 1 file: `packages/Max for Live/patchers/liveui.map.maxpat` (whitespace text).

**Graph tests vs the decision-12 rules:**
- `tests/test_graph.py::TestSubpatcherCrossing::test_downstream_includes_inner_inlets` (a 2-inlet `p`, cord into inlet 0, asserting both inner inlets are in the result) is the only existing assertion of retired behaviour.
- All `TestSignalOnly` and `TestSignalPath` cases in test_graph.py and test_patcher.py stay green under outlettype + destination acceptance (traced case by case). This includes `cycle~ -> print` being skipped, `snapshot~ -> print` being skipped, and `[cycle~, *~, dac~]` order.
- `test_patcher.py` subpatcher crossing tests wire inner inlet 0 → `*~` → outlet 0, so they stay green under port-exact crossing.
- `Patcher.get_inlets()` sorts by x; its order equals the `(x, index)` rank.
</observed_facts>

<reference_data>
**Q/triage.py.** The executor writes this once in Step 0. It is a scratch helper, untracked, and never writes under `patches/`.
- Run it from the repo root; insert the cwd at the front of `sys.path`.
- Imports: json, re, sys, glob, warnings, pathlib; `ObjectDatabase` from `src.maxpat.db_lookup`; `review_patch` from `src.maxpat.critics`.
- FILES is the sorted union of the globs `patches/**/*.maxpat`, `patches/**/*.maxhelp` and `patches/**/*.gendsp` (recursive). Print its length (69 at planning).
- For each file:
  - json-load it;
  - call `review_patch(d, db=db)` under `warnings.catch_warnings()` with `simplefilter("ignore")`, using one shared ObjectDatabase;
  - record one dict per result: `severity`, `finding`, `suggestion`, and `path` (`getattr(r, "path", "")`).
- `--base OUT` writes `{file: [records]}` to OUT and prints the file count and per-severity counts. Expected at base: 1164 warning / 216 note / 1 blocker.
- `--check BASE OUT`:
  - `GEN_ORDER = re.compile(r"^(Hot/cold inlet ordering issue|Fan-out without trigger): ")`.
  - For each file:
    - **top** is the records with `path == ""`, with the path key dropped.
    - **base_top** is BASE[file] with the path key dropped. For a `.gendsp` file, base records matching GEN_ORDER are removed from base_top and counted in `gen_dropped` (planner decision 4, D1).
    - top must equal base_top exactly (severity, finding, suggestion; order included). Otherwise `top_mismatch[file]` is the first differing index.
    - **nested** is the records with `path != ""`.
    - **bad** is the nested records with severity `blocker`.
  - It writes OUT as JSON with:
    - `files`, `top_mismatch` and `gen_dropped` (total and per file);
    - `nested_bad` (full records with file);
    - `nested_counts` keyed by `severity|template`, where template first strips a leading `^\[[^\]]*\] ` prefix, then replaces `obj-\d+` with `<id>`, `'[^']*'` with `<q>` and `\d+(\.\d+)?` with `<n>`;
    - `per_file_nested` (file → list of `severity`, `path`, `finding[:160]`).
  - It prints `files=N top_mismatch=M gen_dropped=G nested_bad=K nested=X`, and exits 1 if M or K is nonzero.
  - Expected after every task: G = 5 (measured at planning). G is enforced through the top-equality test: if the gen skip were missing at the top level, those 5 records would reappear in top and raise a mismatch.
- **Structure.** All of the comparison lives in one pure function, `compare(base_records, cur_records, is_gendsp, gen_drop=True) -> (mismatch_index_or_None, dropped, bad)`. `--check` and `--selftest` both call it, so the self-test exercises the exact code that gates each task.
- `--no-gen-drop` (with `--check`) disables the D1 filter (`gen_drop=False`). It exists only for the Step-0 live checks.
- **`--selftest`** runs `compare` on synthetic in-memory records and touches no patch file. It exits 0 only if every case below behaves as stated, and prints one line per case.
  1. Identical base and current: no mismatch, no bad.
  2. One top-level `finding` changed by one character: mismatch at that index.
  3. Two top-level records swapped: mismatch.
  4. A top-level record missing: mismatch.
  5. An extra top-level record: mismatch.
  6. A changed `severity` or `suggestion`: mismatch.
  7. A nested (`path != ""`) blocker in current: bad = 1. A nested warning: bad = 0.
  8. `is_gendsp=True`, where the base has a `Hot/cold inlet ordering issue: ` record that current lacks: no mismatch, dropped = 1.
  9. Case 8 with `gen_drop=False`: mismatch.
  10. `is_gendsp=True`, where the base has a non-GEN_ORDER record (for example `Missing midpoints: ...`) that current lacks: mismatch.
  11. `is_gendsp=False`, where the base has a GEN_ORDER record that current lacks: mismatch.
</reference_data>

<tasks>

<task type="tracer">
  <name>Task 1: Shared PatchGraph + path-tagged recursive structure critic, end to end through review_patch, the allowlist and the save gate</name>
  <files>src/maxpat/graph.py, src/maxpat/critics/base.py, src/maxpat/critics/__init__.py, src/maxpat/critics/structure_critic.py, tests/test_critics_recursive.py, tests/test_integration_patches.py</files>
  <precondition>Both hard preconditions in `<rules>` hold, and the Step-0 files Q/base-sha.txt, Q/stash-list-before.txt, Q/baseline-pytest.txt, Q/triage-base.json and Q/triage-step0.txt exist (triage-base taken before any source edit). Q/triage-step0.txt shows the three Step-0 triage runs behaving as required: selftest exit 0, `--no-gen-drop` exit 0, default check exit 1 on the .gendsp files only.</precondition>
  <read_first>
    - The review rows A7 and S1 (grep `| A7 |`, `| S1 |` in `.planning/reviews/2026-10-11-repo-review.md`)
    - src/maxpat/walk.py (whole file: iter_patchers, box helpers, path_ids/path_prefix/scope_of)
    - src/maxpat/graph.py (whole file)
    - src/maxpat/critics/__init__.py, src/maxpat/critics/base.py, src/maxpat/critics/structure_critic.py (whole files)
    - src/maxpat/hooks.py: `_finding_key`, `_blocking_findings`, `_gate_report` (find by name)
    - tests/test_integration_patches.py (whole file)
    - tests/test_validation_recursive.py, lines 1-110 (helpers, style) and 400-460 (the gate test and the git helpers to copy)
  </read_first>
  <behavior>
    tests/test_critics_recursive.py (new):
    - **TestPatchGraph:**
      - `PatchGraph.build` yields scopes in `walk.iter_patchers` pre-order with matching path, key, prefix and context, for p, gen~, mc.gen~ `data.patcher`, an embedded bpatcher and an rnbo~.
      - A `{}` dict and `{"patcher": {}}` give exactly one empty top scope.
      - Duplicate box ids keep their first position and their last box in `scope.boxes`, while `box_list` keeps both.
      - Bare box entries and bare patchline entries are accepted.
      - A cord whose source or destination is None, short, a string, has a list id, or has a str/float/bool port is skipped without raising.
      - `edge.signal` follows `outlet_is_signal`: an outlettype entry decides (multichannelsignal counts), and the `~` name is used only without an entry.
      - `children` and `subtree` return the container's inner scopes.
      - Building never mutates the input (deep-equal).
    - **TestStructureNested:**
      - Inside `p synth` (obj-1): a `button` (obj-2, outlettype `["bang"]`) outlet 0 feeds `pack 0 0` (obj-3) inlets 0 and 1. `review_structure` gives exactly one blocker, with path `obj-1` and finding starting `[p synth] Fan-out without trigger: 'button' (obj-2) outlet 0`.
      - `test_nested_parity_with_top_level`, parametrized over fan-out reconvergence, a non-reconvergent fan-out warning, a hot/cold warning and a duplicate patchline: the content wrapped in `p synth` gives the top-level findings, prefixed, with path `obj-1`, in the same order.
      - A two-level nest gives path `obj-1/obj-2` and prefix `[p a > p b] `.
      - Gen scopes:
        - the same reconvergence and a hot/cold shape inside gen~, and in a top-level `classnamespace: dsp.gen` dict, give no fan-out or hot/cold finding;
        - a duplicate patchline inside gen~ is still reported, with path.
      - Top-level results come first; nested follow in pre-order.
    - **TestJitterSetter:**
      - The terrain-view shape: a `loadbang` fans out to message `exprfill 0 snorm[0]` → `jit.matrix 1 float32 64 64` → `jit.pack 3` inlet 0, and to `exprfill 0 snorm[1]` → a second jit.matrix → `jit.pack` inlet 2. This gives a fan-out **warning** ("execution order is undefined") and no blocker, at the top level and inside a p.
      - The same shape with `exprfill 0 snorm[0], bang` is still a blocker.
      - A setter message that is itself the fan-out source feeding two jit.matrix boxes, whose outputs meet at different jit.pack inlets, is not a blocker.
      - `get`-prefixed, `$1`-first and numeric-first messages still propagate.
    - **TestReviewPatchSharedGraph:**
      - Spy on `PatchGraph.build`: one `review_patch` call builds exactly one graph, and `review_structure(..., graph=g)` builds none.
      - `review_patch` constructs at most one ObjectDatabase when `db=None` (spy on the class).
      - The input dict is deep-equal after `review_patch`.
    - **TestSaveGateNestedCritic** (git helpers copied):
      - A new .maxpat whose `p synth` holds the button → pack reconvergence is refused by `save_patch_roundtrip`: PatchValidationError, a CriticResult finding with path `obj-1` and the `[p synth] ` prefix, and the file not written.
      - `_gate_report(new, baseline, [])`, where the baseline has two `p voice` boxes (obj-1, obj-2) with identical inner ids and the reconvergence in obj-1, and the new dict has it moved to obj-2, reports exactly one new blocker, whose path is `obj-2`.

    tests/test_integration_patches.py:
    - `test_allowlist_key_includes_path`: a CriticResult blocker `Fan-out without trigger: 'buffer~' (obj-1) outlet 1 connected to 2 destinations (...) -- ...` with path `obj-9`, checked against `patches/rhythmic-sampler/generated/slot.maxpat`, is **not** allowlisted. The same finding with path `""` is.

    Q/triage.py --check: top_mismatch=0, gen_dropped=5, nested_bad=0.
  </behavior>
  <action>
**Step A: tests first (rule 2).**
- Write tests/test_critics_recursive.py with every Task 1 case in `<behavior>`.
  - Write local `_box` / `_line` / `_inner` / `_container` / `_patch` builders in the style of tests/test_validation_recursive.py. Do not import them.
  - Use a module-scoped `db` fixture.
  - Copy the `_isolate_git_env` autouse fixture and the `_git` / `_repo` helpers from tests/test_validation_recursive.py.
  - The gate test writes to `<_repo(tmp_path)>/patches/demo/generated/demo.maxpat`. Build its dict from `Patcher().to_dict()`, then append the `p synth` box.
- Add `test_allowlist_key_includes_path` to tests/test_integration_patches.py.
- Run `python3 -m pytest -q -p no:cacheprovider tests/test_critics_recursive.py tests/test_integration_patches.py::test_allowlist_key_includes_path` into Q/red-t1.txt. Expected: a collection error (no PatchGraph) and the key test failing.

**Step B: graph.py, the dict front end** (planner decision 2).
- Add `SIGNAL_OUTLET_TYPES`, `outlet_is_signal`, `Edge` (a NamedTuple), `Scope` and `PatchGraph` (`build`, `scopes`, `top`, `children`, `subtree`) to src/maxpat/graph.py, next to GraphMixin. GraphMixin stays untouched in this task.
- Extend the module docstring: one shared graph per patch (S1, Q20), built from `walk.iter_patchers`, read-only.

**Step C: critics/base.py** (planner decision 1).
- Add the `path` slot and the constructor parameter, then `tag_results(results, path)`.
- Document both in the class docstring.

**Step D: structure_critic.py.**
- Signature: `review_structure(patch_dict, *, graph=None)`. Build `PatchGraph.build(patch_dict)` when graph is None.
- For each scope in `graph.scopes`, run the three checks on that scope's `boxes` / `edges` and pass the results through `tag_results(..., scope.path)`.
  - In gen scopes, only `_check_redundant_connections` runs (planner decision 4).
  - The checks consume `Edge` tuples in line order instead of re-parsing lines, with semantics unchanged.
- Move `_outlet_is_signal` to `graph.outlet_is_signal` and keep the alias.
- Names come from `walk.box_name`. The module stops importing utils.
- Add the planner-decision-5 setter rule to `_paths_reconverge` (a small `_is_jitter_setter_hop(src_box, dst_box)` helper, with its docstring citing the terrain-synth evidence).
- Update the module docstring: per-scope review, gen skip, setter path end.

**Step E: critics/__init__.py.**
- In `review_patch`, construct `ObjectDatabase()` once when `db` is None and reuse it for package detection and the package critic. Build `graph = PatchGraph.build(patch_dict)` once, and pass `graph=graph` to `review_structure`. The other critics are wired in Task 2.
- Update the docstring.

**Step F: tests/test_integration_patches.py.**
- Make the allowlist key path-aware (planner decision 11) and update the allowlist comment block to say keys include the CriticResult path.

**Step G.**
- Run the Task 1 tests until green, then the verify command.
  - If Q/triage.py reports a top-level mismatch or a nested blocker, or test_calibration_zero_blockers fails, apply the conditional triage rule in `<rules>`.
  - If another existing test fails, apply the existing-tests rule.
- Commit with the message `feat(critics): shared PatchGraph and path-tagged recursive structure critic (Q20)`, staging exactly the six task files.
  </action>
  <verify>
    <automated>bash -c 'Q=.planning/quick/261014-uzq-implement-q20-in-planning-reviews-2026-1 && B=$(git status --porcelain) && python3 -m pytest -q -p no:cacheprovider tests/test_critics_recursive.py tests/test_critics.py tests/test_critic_precision.py tests/test_critic_revival.py tests/test_integration_patches.py tests/test_save_gate.py tests/test_graph.py tests/test_patcher.py tests/test_aesthetics.py tests/test_m4l_gen_synth.py && A=$(git status --porcelain) && test "$B" = "$A" && grep -iq -e failed -e error "$Q/red-t1.txt" && python3 "$Q/triage.py" --selftest && python3 "$Q/triage.py" --check "$Q/triage-base.json" "$Q/triage-t1.json" && python3 -c "import ast,sys;[ast.parse(open(f).read(),feature_version=(3,10)) for f in sys.argv[1:]]" src/maxpat/graph.py src/maxpat/critics/base.py src/maxpat/critics/__init__.py src/maxpat/critics/structure_critic.py tests/test_critics_recursive.py tests/test_integration_patches.py'</automated>
  </verify>
  <done>
    - PatchGraph exists, read-only and tolerant.
    - CriticResult carries a path.
    - The structure critic reviews every scope with path and prefix, skips ordering checks in gen scopes, and ends paths at Jitter setters.
    - review_patch builds one graph and one DB.
    - The gate refuses a new file with a nested structure blocker and treats a moved nested blocker as new.
    - The allowlist key is path-aware.
    - Q/red-t1.txt shows the red run. Q/triage-t1.json shows top_mismatch=0, gen_dropped=5, nested_bad=0.
    - The calibration test is green.
    - One `(Q20)` commit with six paths.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: dsp, package, rnbo, m4l and layout (including contrast) critics recursive on the shared graph, with scope-wide dispatch and per-call dedup</name>
  <files>src/maxpat/critics/dsp_critic.py, src/maxpat/critics/package_critic.py, src/maxpat/critics/rnbo_critic.py, src/maxpat/critics/m4l_critic.py, src/maxpat/critics/layout_critic.py, src/maxpat/critics/__init__.py, tests/test_critics_recursive.py</files>
  <read_first>
    - src/maxpat/critics/dsp_critic.py, package_critic.py, rnbo_critic.py, m4l_critic.py, layout_critic.py (whole files)
    - src/maxpat/critics/__init__.py and the Task 1 graph additions in src/maxpat/graph.py
    - tests/test_critic_revival.py, lines 300-500 (M4L and RNBO fixture shapes and what they assert)
    - tests/test_critics.py, lines 2440-2527 (effective-background contrast tests) and the package-critic tests (grep `review_packages`)
    - tests/test_aesthetics.py, the TestContrastCritic class (grep it)
  </read_first>
  <behavior>
    Appended to tests/test_critics_recursive.py:
    - `test_nested_parity_with_top_level` gains one parametrized fixture per per-scope check:
      - dsp: oscillator → dac~ with no gain (blocker); `slider` → `*~` inlet 1 (blocker); gen~ I/O mismatch (blocker);
      - package: Bach llll note (skip if bach is not in the repo DB);
      - m4l: ezdac~, and live.dial without parameter_enable (each run with a top-level plugout~ so the device is detected);
      - layout: overlap, missing midpoints, out-of-bounds, low contrast with the scope's own `bgcolor`, presentation coverage.

      Each gives identical findings prefixed with `[p synth] ` and path `obj-1`.
    - **DSP:**
      - A gen~ nested inside `p synth` with an I/O mismatch is a blocker with path `obj-1`.
      - `code_context["gen~_code"]` keyed `obj-2` applies to a top-level gen~ obj-2, and not to a nested gen~ obj-2.
      - No dsp finding comes from inside a gen scope.
    - **Package:**
      - An unextracted community package (monkeypatched the way existing package tests do) used at the top level and inside a p warns exactly once, at the top level.
      - Used only inside a p, it warns once, with path.
      - A `verified_installed: false` object (monkeypatched `get_install_state`) present in two scopes gives one blocker, at the first scope in pre-order.
      - `_has_package_boxes` is True when the package object is only nested.
      - A BEAP bpatcher chain inside a p is reviewed, with path.
    - **RNBO:**
      - An rnbo~ inside `p synth` with no in~ gives the I/O blocker with path `obj-1` and prefix `[p synth] `.
      - Duplicate params, one in the rnbo~ inner patcher and one inside a `p` within it, give one duplicate blocker naming `<inner id>` and `<p id>/<inner id>`.
      - A mis-cased param inside that inner `p` warns.
      - `_has_rnbo_boxes` is True for a nested rnbo~.
      - The existing test_critic_revival RNBO messages are unchanged.
    - **M4L:**
      - A plugout~ only inside a p makes `detect_m4l_device_type` return `instrument`, and gives no "missing required object: plugout~".
      - An ezdac~ inside a p is a blocker with path.
      - gain~ → plugout~ inside the same p is a blocker with path.
      - Duplicate parameter_longname between a top-level live.dial obj-3 and a nested live.dial obj-3 in p obj-1 is one blocker at path `""`, referencing `obj-3` and `obj-1/obj-3`.
      - Missing info text on a nested parameter control is tagged with path, not reported untagged at the top level.
      - A live.banks inside a p satisfies the banks check.
    - **Layout:**
      - A low-contrast comment inside a p whose own patcher `bgcolor` is light (dark text) warns with path. The same comment inside a p with no bgcolor uses the palette fallback, as at the top level.
      - Whitespace-only text on any box in any scope never raises.
    - **TestReviewPatchSharedGraph:** with every critic active (top-level plugout~, nested rnbo~, a nested package object), one `review_patch` call still builds exactly one PatchGraph, and every critic receives that same object (spy on each review function's `graph` keyword).
    - **Purity:** the nested dict used above is deep-equal after `review_patch`.
    - **Robustness:** for each critic, a nested scope holding a non-dict box, a non-dict line, None text, a list maxclass, a non-dict `saved_attribute_attributes` and a non-list `outlettype` returns a list without raising.

    Q/triage.py --check: top_mismatch=0, gen_dropped=5, nested_bad=0.
  </behavior>
  <action>
**Step A: tests first (rule 2).**
- Append the `<behavior>` cases.
- Run them into Q/red-t2.txt. Expected: the dsp, package, rnbo, m4l and layout nested cases and the shared-graph spy fail; the Task 1 cases stay green.

**Step B: dsp_critic.py** (planner decision 7).
- Signature: `review_dsp(patch_dict, code_context=None, *, graph=None)`.
- Run per non-gen scope; checks take the scope's boxes and edges.
- `code_context` applies only at `scope.path == ()`.
- `_gen_inner_patcher` becomes `walk.inner_patcher`.
- Text and names go through walk.

**Step C: package_critic.py** (planner decision 6).
- Signature: `review_packages(patch_dict, db=None, *, graph=None)`.
- Names: a bpatcher's `name` only when it is a str, otherwise `walk.box_name`.
- One shared dedup state per call.
- `_build_signal_adjacency` takes a scope and uses `edge.signal`.

**Step D: rnbo_critic.py** (planner decision 8).
- Signature: `review_rnbo(patch_dict, code_context=None, *, graph=None)`.
- `is_rnbo_box` uses `walk.box_name`. `_get_inner_object_name` is replaced by `walk.box_name`. Param text is read with `walk.box_text`.

**Step E: m4l_critic.py** (planner decision 9).
- Signatures: `detect_m4l_device_type(patch_dict, *, graph=None)` and `review_m4l(patch_dict, device_type=None, *, graph=None)`.
- Import `outlet_is_signal` from graph.
- Every dict read of `saved_attribute_attributes` / `valueof` is isinstance-guarded.
- Update the module docstring (the "Scope is the top level only" note goes away).

**Step F: layout_critic.py** (planner decision 10).
- Signature: `review_layout(patch_dict, *, graph=None)`.
- Per scope with that scope's `box_list`, `boxes`, `edges` and patcher dict.
- The `_box_label` change.
- Replace the module docstring note.

**Step G: critics/__init__.py.**
- Pass `graph=graph` to dsp, layout, rnbo, m4l (detect and review) and package.
- `_has_rnbo_boxes(patch_dict, graph=None)` and `_has_package_boxes(patch_dict, db=None, graph=None)` look across scopes, per decisions 6 and 8.
- No module in `src/maxpat/critics/` imports `utils` any more.
- Update the module and `review_patch` docstrings: every critic reviews every scope, findings are path-tagged, and one graph is built per call.

**Step H.**
- Run the verify command, applying the conditional triage rule and the existing-tests rule as needed.
- Commit with the message `feat(critics): dsp, package, rnbo, m4l and layout critics review every scope on the shared graph (Q20)`, staging exactly the seven task files (plus `tests/review_blocker_allowlist.json` only under the conditional rule).
  </action>
  <verify>
    <automated>bash -c 'Q=.planning/quick/261014-uzq-implement-q20-in-planning-reviews-2026-1 && B=$(git status --porcelain) && python3 -m pytest -q -p no:cacheprovider tests/test_critics_recursive.py tests/test_critics.py tests/test_critic_precision.py tests/test_critic_revival.py tests/test_integration_patches.py tests/test_save_gate.py tests/test_aesthetics.py tests/test_m4l_polish.py tests/test_m4l_gen_synth.py tests/test_layout.py tests/test_commands.py && A=$(git status --porcelain) && test "$B" = "$A" && grep -iq -e failed -e error "$Q/red-t2.txt" && python3 "$Q/triage.py" --selftest && python3 "$Q/triage.py" --check "$Q/triage-base.json" "$Q/triage-t2.json" && python3 -c "import ast,sys;[ast.parse(open(f).read(),feature_version=(3,10)) for f in sys.argv[1:]]" src/maxpat/critics/dsp_critic.py src/maxpat/critics/package_critic.py src/maxpat/critics/rnbo_critic.py src/maxpat/critics/m4l_critic.py src/maxpat/critics/layout_critic.py src/maxpat/critics/__init__.py tests/test_critics_recursive.py'</automated>
  </verify>
  <done>
    - All six patch critics review every scope with path and prefix, on the one shared graph.
    - Dispatch detects nested rnbo~, M4L markers and package objects.
    - Package and install-state findings dedup per patch. Device-level M4L findings report once.
    - Contrast resolves against each scope's own background.
    - Parity, purity and robustness tests are green.
    - Q/red-t2.txt shows the red run. Q/triage-t2.json shows top_mismatch=0, gen_dropped=5, nested_bad=0.
    - One `(Q20)` commit.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: graph.py G9 traversal, recursive analyze(), recursive object-only checklist, bundle sweep; full suite, triage, SUMMARY</name>
  <files>src/maxpat/graph.py, src/maxpat/analysis.py, src/maxpat/testing.py, src/maxpat/hooks.py, src/maxpat/walk.py, tests/test_graph.py, tests/test_analysis.py, tests/test_testing.py, tests/test_critics_recursive.py</files>
  <read_first>
    - The review rows G9 and G10 (grep `| G9 |`, `| G10 |`)
    - src/maxpat/graph.py (after Task 1) and src/maxpat/analysis.py, src/maxpat/testing.py (whole files)
    - src/maxpat/validation.py: `_is_container_box` and `_inlet_accepts_signal` (find by name; read-only)
    - src/maxpat/hooks.py: `_port_ranks` (the x-rank rule) and the `_finding_key` docstring
    - src/maxpat/patcher.py: `get_inlets` / `get_outlets`, `Box.to_dict`, `Patcher.to_dict` (find by name; read-only)
    - tests/test_graph.py (whole file), tests/test_patcher.py classes TestDownstream / TestUpstream / TestSignalPath (grep them), tests/test_analysis.py lines 15-58 (the `_quick_box` helper), tests/test_testing.py lines 1-30
  </read_first>
  <behavior>
    tests/test_graph.py, with GraphMixin exercised through Patcher (add_subpatcher, get_inlets/get_outlets):
    - **TestPortExactCrossing:**
      - `p fx` has 2 inlets and 2 outlets. cycle~ feeds p inlet 1. Inside, inlet rank 1 → `*~ 0.5` → outlet rank 0, and inlet rank 0 → `print`. Outside, p outlet 0 → dac~ and p outlet 1 → a top-level `print`.
      - `downstream(cycle~)` contains p, inner inlet rank 1, `*~`, inner outlet rank 0 and the dac~. It does not contain inner inlet rank 0, the inner print, or the top-level print.
      - `upstream(dac~)` contains p, outlet rank 0, `*~`, inlet rank 1 and the cycle~, and not the inner print.
    - **TestSendReceiveBridging:**
      - cycle~ → `send~ bus` at the top level; inside a p, `receive~ bus` → `*~` → outlet; p outlet 0 → dac~. `downstream(cycle~)` reaches receive~, `*~` and dac~, and `upstream(dac~)` reaches send~ and cycle~.
      - `metro` → `s tick`, and `r tick` → `print` in another p: downstream reaches print.
      - `signal_only=True` does not bridge `s`/`r`.
      - A `s a` → `r a` → `s a` loop terminates.
    - **TestOutlettypeSignal:**
      - The G9 repro: `signal_path(cycle~)` through `p fx` (inner inlet → `*~` → outlet) to dac~ contains p fx, `*~` and dac~, not just `[cycle~]`.
      - `snapshot~` → `number` is not followed with signal_only.
      - An `mc.cycle~` (outlettype multichannelsignal) → `mc.*~` cord is followed.
      - `_build_adj(signal_only=True)` keeps `cycle~ -> *~` and drops `cycle~ -> print`.
    - **TestAdjacencyOnce:** spy on `PatchGraph.build` and `GraphMixin._build_adj`. One `downstream()` over a 200-box chain builds the graph exactly once and calls `_build_adj` zero times.
    - **TestSubpatcherCrossing:** `test_downstream_includes_inner_inlets` is renamed `test_downstream_enters_only_the_wired_inlet` and inverted: inner inlet rank 0 is in the result, inlet rank 1 is not.

    tests/test_analysis.py, **TestRecursiveAnalyze:**
    - A Patcher with `p synth` (cycle~ → `*~` → outlet, loadbang → print, a slider with varname `cutoff`) and a top-level dac~. `analyze()` contains:
      - `### [p synth]` under `## Signal Flow`, with cycle~;
      - `### [p synth]` under `## Control Flow`, with loadbang;
      - `- [p synth] cutoff (slider)` under `## Parameters`;
      - an inventory whose MSP count includes the inner cycle~ and `*~`, followed by `Counts include 1 subpatcher scope(s).`
    - A gen~ with an embedded gen patcher counts its boxes as `Gen` in the inventory and adds no `###` block to Signal Flow.
    - A patch without subpatchers gives no `###` line and no "Counts include" line.

    tests/test_testing.py, **TestRecursiveChecklist:**
    - The G10 repro: `dac~` inside `p synth` plus a top-level comment `metro speed and gen~ notes` gives "Audio Output" and the audio-on setup step, with no "Metro Timing" and no "gen~ Processing".
    - A message box `metro 500` is not counted.
    - A UI `toggle` (maxclass toggle) inside a p is counted.
    - A gen~ patcher's inner `button`-named operator is ignored.
    - Text that is `""`, `"   "`, None or 5 never raises.

    tests/test_critics_recursive.py, **TestBundleSweep** (`@pytest.mark.requires_max`):
    - Every `*.maxpat` / `*.maxhelp` under `MAX_APP_PATH / "Contents/Resources/C74"` is loaded. Files that are not JSON, or whose JSON is not a dict with a dict `patcher`, are skipped.
    - For each file: `review_patch(d, db=db)`, `generate_test_checklist(d, name)` and `PatchGraph.build(d)`. Then, for the first top-scope box with an out-edge, `downstream` (both modes, with db) and `upstream`.
    - It collects `(relpath, step, exception repr)` for every raise, asserts the list is empty, and asserts that more than half of the files were checked. At base the checklist raises IndexError on 1 file.
  </behavior>
  <action>
**Step A: tests first (rule 2).**
- Add the `<behavior>` cases, including the rename and inversion in test_graph.py.
- Run `python3 -m pytest -q -p no:cacheprovider tests/test_graph.py tests/test_analysis.py tests/test_testing.py tests/test_critics_recursive.py::TestBundleSweep` into Q/red-t3.txt. Expected: the crossing, bridging, signal, adjacency, recursive analyze and checklist cases fail, and the sweep shows the checklist IndexError.

**Step B: graph.py G9** (planner decision 12).
- Add `PatchGraph.downstream` / `upstream`, the port-rank maps, the channel maps, the destination-acceptance helper (lazy validation import) and `resolve_patcher(patcher, path)`.
- Rewrite `GraphMixin._traverse` / `downstream` / `upstream` / `signal_path` / `_build_adj` on top of them. Delete `_enqueue_neighbors` and `_cross_subpatcher`; no test imports them.
- Update the module and method docstrings: port-exact crossing, transparent ports, opaque gen/rnbo/poly containers, bridging, the outlettype rule, adjacency built once.
- **Sub-gate B** (must pass before Step C): `python3 -m pytest -q -p no:cacheprovider tests/test_graph.py tests/test_patcher.py tests/test_analysis.py tests/test_critics_recursive.py -k "not TestBundleSweep and not TestRecursiveAnalyze" > Q/t3-gate-b.txt`.
  - test_analysis.py is included because its non-recursive cases call `_build_adj` / `connected_components`.

**Step C: analysis.py** (planner decision 13).
- Refactor each facet into a body-lines helper so the top-level output stays byte-identical, then add the nested blocks and the recursive inventory.
- Update the AnalysisMixin and `analyze` docstrings.
- **Sub-gate C** (must pass before Step D): `python3 -m pytest -q -p no:cacheprovider tests/test_analysis.py tests/test_patcher.py > Q/t3-gate-c.txt`.

**Step D: testing.py** (planner decision 14).
- Replace `_extract_object_names` with a walk-based extractor over all non-gen scopes.
- **Sub-gate D** (must pass before Step E): `python3 -m pytest -q -p no:cacheprovider tests/test_testing.py tests/test_critics_recursive.py::TestBundleSweep > Q/t3-gate-d.txt`.

**Step E: docstrings only.**
- In src/maxpat/hooks.py `_finding_key`, the path now comes from ValidationResult **and** CriticResult (Q20).
- In src/maxpat/walk.py, replace the "move onto this module in Q20" sentence. Say that the critics, the shared graph, analysis and testing now use this walker, and that `hooks._iter_patchers`, `utils.get_box_name`, `layout.py`, `aesthetics.py` and `m4l_polish.py` keep their own walkers (follow-up).

**Step F: full suite, triage, commit.**
- Before committing, run the full suite (`python3 -m pytest -q -p no:cacheprovider`), the triage selftest and check, and the ast parse. Fix until all are green, so no fix lands after the commit.
- Commit with the message `feat(graph): port-exact, send/receive-bridged, outlettype-signal traversal; recursive analyze() and test checklist (Q20)`, staging exactly the nine task files.
- Then run the verify command. It re-runs the suite into Q/final-pytest.txt, writes Q/triage-final.json, and checks the commits.
- If only the commit-count check fails, follow the count-failure handling in `<rules>` ("Commits").

**Step G: write SUMMARY.md** (see `<output>`).
  </action>
  <verify>
    <automated>bash -c 'Q=.planning/quick/261014-uzq-implement-q20-in-planning-reviews-2026-1 && touch "$Q/final-pytest.txt" && B=$(git status --porcelain) || exit 1; python3 -m pytest -q -p no:cacheprovider > "$Q/final-pytest.txt" 2>&1; R=$?; tail -1 "$Q/final-pytest.txt"; A=$(git status --porcelain) || exit 1; test $R -eq 0 && test "$B" = "$A" && grep -iq -e failed -e error "$Q/red-t3.txt" && python3 "$Q/triage.py" --selftest && python3 "$Q/triage.py" --check "$Q/triage-base.json" "$Q/triage-final.json" && python3 -c "import ast,sys;[ast.parse(open(f).read(),feature_version=(3,10)) for f in sys.argv[1:]]" src/maxpat/graph.py src/maxpat/analysis.py src/maxpat/testing.py src/maxpat/hooks.py src/maxpat/walk.py src/maxpat/critics/__init__.py src/maxpat/critics/base.py src/maxpat/critics/structure_critic.py src/maxpat/critics/dsp_critic.py src/maxpat/critics/package_critic.py src/maxpat/critics/rnbo_critic.py src/maxpat/critics/m4l_critic.py src/maxpat/critics/layout_critic.py tests/test_critics_recursive.py tests/test_graph.py tests/test_analysis.py tests/test_testing.py tests/test_integration_patches.py && S=$(git stash list) && test "$S" = "$(cat "$Q/stash-list-before.txt")" && C=$(git log --format=%H --fixed-strings --grep="(Q20)" "$(cat "$Q/base-sha.txt")"..HEAD) && set -- $C && test $# -eq 3 && for c in $C; do git show --name-only --format= "$c" || exit 1; done > "$Q/q20-commit-files.txt" && test -s "$Q/q20-commit-files.txt" && ! grep -q "^patches/" "$Q/q20-commit-files.txt"'</automated>
  </verify>
  <done>
    - Traversal is port-exact, bridges send/receive and send~/receive~ across scopes, decides signal by outlettype plus destination acceptance, and builds adjacency once per call.
    - `signal_path` passes through `p` boxes.
    - `analyze()` and the checklist recurse; the checklist counts object boxes only.
    - The bundle sweep is green where Max is installed.
    - The full suite is green. Q/triage-final.json shows top_mismatch=0, gen_dropped=5, nested_bad=0.
    - Three `(Q20)` commits, the stash list unchanged, no patches/ change.
    - SUMMARY.md is written.
  </done>
</task>

</tasks>

<threat_model>
Security config: ASVS level 1, block on high. `security_enforcement` is absent from .planning/config.json, so it is enabled. This is in-process critic, graph and analysis code over local JSON, with no network, auth or crypto. The surface that matters is ASVS V5 input robustness, plus the save gate's job: never write a broken patch, and never wrongly refuse a good one.

## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| .maxpat JSON → PatchGraph / critics / analysis / checklist | Patch files (user, generated or MAX-saved) are untrusted structure. Nested patchers were ignored by these consumers before, and are now parsed. |
| critic results → save gate | Blocking critic findings decide whether a file is written; `_finding_key` decides what counts as new |
| critic results → review allowlist | Signature keys decide which blockers in frozen patches are exempt |
| Concurrent Claude instances → git | Broad staging or stash can sweep in or strand another instance's work |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-uzq-01 | Denial of Service | review_patch (and so every save), PatchGraph, analyze and the checklist crashing on malformed, deep or cyclic nested input that recursion now reaches | high | mitigate | The walk is the Q19 iterative walker with its id() cycle guard. Scope parsing skips wrong-typed boxes, lines, ids and ports (decision 2), and text and names go through walk. Tested by the Task 1 TestPatchGraph and Task 2 robustness tests and the requires_max sweep of 3,139 bundle files (Task 3). |
| T-uzq-02 | Denial of Service | New nested false-positive critic blockers refusing saves of good patches (gen-scope ordering, Jitter setters) | high | mitigate | Decisions 4 and 5. test_calibration_zero_blockers and test_review_patch_no_blockers stay green. Q/triage.py requires nested_bad=0 on all 69 committed files after every task. Bundle-only findings are not promoted (decision 16). |
| T-uzq-03 | Tampering | The review allowlist exempting a nested blocker because its source id and outlet equal a top-level entry's | medium | mitigate | Decision 11: the key includes the CriticResult path. test_allowlist_key_includes_path. |
| T-uzq-04 | Repudiation | The save-gate multiset missing a new nested critic blocker in identically labelled subpatchers | medium | mitigate | `_finding_key` already reads `path`; CriticResult now carries it. Covered by TestSaveGateNestedCritic's moved-blocker case. |
| T-uzq-05 | Tampering | Critics, PatchGraph or analysis mutating the patch dict or Patcher while walking | medium | mitigate | The graph is read-only (decision 2). Deep-equal purity tests in Tasks 1 and 2; analyze works on `to_dict()` output and resolved Patchers, read-only. |
| T-uzq-06 | Tampering | Top-level critic findings silently changing (save-gate keys, the calibration baseline and existing tests depend on them) | medium | mitigate | Decisions 1 and 3. Q/triage.py compares every top-level result on 69 files with the base snapshot after each task. The only allowance is the enumerated gen_dropped D1, which must total 5. |
| T-uzq-07 | Denial of Service | Traversal looping forever on send/receive cycles or feedback across scopes | medium | mitigate | Visited sets over (scope, box) and over (container, port) crossings (decision 12). Covered by the `s a` → `r a` → `s a` loop test and the existing feedback-loop tests. |
| T-uzq-08 | Tampering | Committed user-confirmed patches edited to silence new findings | high | mitigate | Rule 3 and the edit scope forbid `patches/**`. The Task 3 verify fails if any `(Q20)` commit touches `patches/`. A calibration true positive HALTs. |
| T-uzq-09 | Elevation of Privilege | Commits sweeping in other instances' files, or a stash stranding work | medium | mitigate | `git add -- <paths>` plus a path-limited `git commit -- <paths>`, never `-A` or `.`. The stash list is compared with Step 0, and the hard preconditions HALT on uncommitted edits in task files. |
| T-uzq-SC | Tampering | npm/pip/cargo installs | low | accept | This plan installs no packages. |
</threat_model>

<verification>
- **Suite.**
  - Step 0 baseline is expected at 3813 passed, 1 xfailed, 1 xpassed.
  - The final run is green with the xfail/xpass unchanged, plus the new tests (the requires_max sweep runs on this Mac).
  - Every task commit is green on its verify set, and `git status --porcelain` is unchanged across every pytest run.
- **Test-first proof.** Q/red-t1.txt, Q/red-t2.txt and Q/red-t3.txt each show failures or errors from before that task's implementation.
- **Byte identity and triage.** Q/triage-t1.json, Q/triage-t2.json and Q/triage-final.json each show top_mismatch=0, gen_dropped=5 and nested_bad=0 against Q/triage-base.json.
  - The gate is proven able to fail: Q/triage-step0.txt records `--selftest` passing all 11 synthetic cases, the unchanged-code `--no-gen-drop` check exiting 0, and the default check exiting 1 on the .gendsp files only.
  - Every task verify re-runs `--selftest` before `--check`.
- **Calibration.** test_calibration_zero_blockers is green after every task.
- **Scope.** Only `files_modified` change (plus the conditional allowlist entry, if one was ever needed), with no change under patches/ and no edits to docs or `.claude/**`.
- **Python 3.10.** Every changed .py passes `ast.parse(feature_version=(3, 10))`.
- **Commits.** Three `(Q20)` commits. The stash list is unchanged and nothing is pushed.
</verification>

<success_criteria>
- A fan-out hazard, a missing gain stage, an M4L ezdac~, an rnbo~ without in~ or a low-contrast label inside any subpatcher is reported with a path that shows where it is. The save gate refuses new files that introduce such blockers.
- One graph per `review_patch` call feeds every critic.
- Graph traversal follows real ports and send/receive channels and decides signal by outlettype, so `signal_path` no longer stops at a `p`.
- `analyze()` and the /max-test checklist describe the whole patch. The checklist no longer reacts to words in comments or messages.
- Every committed patch still reviews with zero unallowlisted blockers, the calibration patches with zero blockers, and top-level findings are byte-identical apart from the 5 enumerated gen ordering warnings.
</success_criteria>

<output>
Create `.planning/quick/261014-uzq-implement-q20-in-planning-reviews-2026-1/261014-uzq-SUMMARY.md`. It must include:

- **Figures.**
  - Base and final pytest totals.
  - The new test count per file: test_critics_recursive.py, test_graph.py, test_analysis.py, test_testing.py, test_integration_patches.py.
  - Confirmation that the bundle sweep ran.
- **PatchGraph API.** One line per public name, with its contract: `outlet_is_signal`, `Edge`, `Scope` fields, `PatchGraph.build`, `scopes`, `top`, `children`, `subtree`, `downstream`, `upstream`, `resolve_patcher`.
- **Triage (rule 3), from Q/triage-final.json.**
  - Nested findings on committed patches, by template, severity and count, with file and path for every warning class.
  - The expected classes are layout contrast (mark as Q26 theme defaults, never recoloured), midpoints, overlaps, hot/cold, the 4 demoted terrain-synth fan-outs plus the other fan-out warnings, and the Bach notes.
  - Each is marked "true-positive or intentional; user-confirmed patch; no action" or with its follow-up ID.
  - The 5 gen_dropped warnings, by file.
  - Confirmation of 0 nested blockers and whether any allowlist entry was needed.
- **Decisions taken:** planner decisions 1-16, with measured effects: D1 = 5, the setter rule's 4 demotions, and 0 top-level changes otherwise.
- **Existing tests changed:** the test_graph.py inversion, plus any other inversion made under the existing-tests rule, with its reason.
- **Out of scope / doc impact, not edited (rule 8):**
  - `.claude/skills/references/severity-contract.md` §9 "Scope of the walk" (blocking findings now come from every scope);
  - TECHNICAL.md:561 (M4L detection is no longer top-level only) and the layout-critic description;
  - README.md validation-pipeline paragraph (critics are recursive);
  - the max-critic skill and `critic-protocol.md` if they describe top-level-only review;
  - `tests/review_blocker_allowlist.json` `_doc` (keys now include `path`);
  - the decision-15 walkers left on their own code;
  - the follow-ups: cross-scope critic flow, analysis flow across boundaries (review §4.4 item 12), embedded poly~ port crossing, Q26 theme-aware contrast, Q21 ordering checks, and the 917 bundle-only nested blockers.
- **MAX/Live confirmation:** none required. The work is critic, analysis and graph code only, and no patch changed. Optional: the user may sanity-check that `/max-verify` and `/max-test` output on a patch with subpatchers reads well.
</output>
