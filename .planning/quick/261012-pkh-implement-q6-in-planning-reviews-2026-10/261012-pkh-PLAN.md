---
phase: quick-261012-pkh
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/maxpat/hooks.py
  - src/maxpat/layout.py
  - src/maxpat/patcher.py
  - tests/test_edit_keeps_user_work.py
  - .claude/skills/max-patch-agent/SKILL.md
  - .claude/skills/max-dsp-agent/SKILL.md
  - .claude/skills/max-ui-agent/SKILL.md
  - .claude/skills/max-js-agent/SKILL.md
  - .claude/skills/max-rnbo-agent/SKILL.md
  - .claude/skills/max-ext-agent/SKILL.md
autonomous: true
requirements: [B1, B2, B3]

estimate:
  tokens: 80000
  raw_tokens: 80000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "A deepcopy of patches/ji-harmonizer/generated/ji-harmonizer.maxpat run through finalize_patch(is_new=False) keeps all 367 existing midpoint lists identical. Its 23 straight cords stay straight, and the serialized `lines` array of every patcher (top level and nested) equals the file's."
    - "On the edit path a cord gets midpoints only if it has none AND it is new or touches a box that was added or moved in this edit. A moved box's already-routed cords keep their midpoints. The is_new=True / apply_layout path is unchanged."
    - "populate_assistance_comments writes each inferred comment to `_raw[\"comment\"]` as well as extra_attrs, so it reaches disk on loaded subpatchers. All 15 empty inlet/outlet comments in ji-harmonizer serialize with text, and non-empty comments are untouched."
    - "modify_box(args=...) keeps the existing I/O counts, outlettype and every cord for content-defined boxes. That means an embedded patcher, bpatcher, p/patcher, gen~, mc.gen~, jit.gen, poly~, mc.poly~, js, jsui, v8, v8ui, node.script, any name not in the DB, and any DB object not marked variable_io. FDNVerb's top-level `gen~ FDNverb` keeps 2/2 I/O and all 41 cords with the same args and with changed args."
    - "For variable_io objects, modify_box recomputes I/O from the DB, keeps every cord whose indices stay in range, and returns the out-of-range ones in EditResult.orphaned. When the resulting text is identical to the current text, nothing else changes: no I/O recompute, resize or cord change."
    - "modify_box(args=...) on a message or comment box sets text to the space-joined args with no maxclass prefix, leaves I/O unchanged, and the text reaches disk through `_raw`."
    - "Step 3 of all six 'Output Protocol (Edited Patches)' blocks describes the routing-preserving finalize_patch. The full suite is green, no file under patches/ changed, the stash list is unchanged, and every changed .py file passes the Python 3.10 syntax gate."
  artifacts:
    - path: "tests/test_edit_keeps_user_work.py"
      provides: "Q6 regression tests: finalize keeps routing on ji-harmonizer, new/moved-cord routing, assistance comments on disk, modify_box I/O for content-defined vs variable_io boxes (FDNVerb), message/comment text"
      contains: "TestFinalizeKeepsRouting"
      min_lines: 220
    - path: "src/maxpat/hooks.py"
      provides: "finalize_patch(is_new=False) without the clearing loop; _box_added_or_moved predicate; per-patcher eligibility passed to _generate_midpoints"
      contains: "_box_added_or_moved"
    - path: "src/maxpat/layout.py"
      provides: "_generate_midpoints(patcher, eligible=None): optional per-line filter, default unchanged"
      contains: "eligible"
    - path: "src/maxpat/patcher.py"
      provides: "Box._loaded_rect snapshot set in from_dict; CONTENT_DEFINED_NAMES + Patcher._io_is_content_defined; modify_box keep/recompute/message rules; populate_assistance_comments writes _raw comment"
      contains: "_io_is_content_defined"
    - path: ".claude/skills/max-patch-agent/SKILL.md"
      provides: "Edited-patches step 3 describes the routing-preserving finalize (same line in the dsp, ui, js, rnbo and ext agent skills)"
      contains: "never clears existing midpoints"
  key_links:
    - from: "src/maxpat/hooks.py"
      to: "src/maxpat/layout.py"
      via: "finalize_patch(is_new=False) -> _finalize_midpoints_recursive -> _generate_midpoints(patcher, eligible=<line has _raw None or touches an added/moved box id>) for each patcher, recursively"
      pattern: "eligible="
    - from: "src/maxpat/patcher.py"
      to: "src/maxpat/hooks.py"
      via: "Patcher.from_dict records box._loaded_rect (tuple copy of patching_rect); _box_added_or_moved compares x/y with it (_raw None or no snapshot means added)"
      pattern: "_loaded_rect"
    - from: "src/maxpat/patcher.py"
      to: "src/maxpat/db_lookup.py"
      via: "modify_box -> _io_is_content_defined(box) -> db.lookup(name).get('variable_io'); recompute via compute_io_counts/get_outlet_types only when False is returned"
      pattern: "_io_is_content_defined\\("
    - from: "src/maxpat/patcher.py"
      to: ".maxpat on disk"
      via: "_populate_comments_recursive sets box._raw['comment'] for loaded inlet/outlet boxes, which Box.to_dict's round-trip path serializes"
      pattern: "_raw\\[\"comment\"\\]"
---

<objective>
Implement Q6 of `.planning/reviews/2026-10-11-fix-plan.md`: make the edit path keep user work (review findings B1, B2 and B3).

**B1: finalize_patch(is_new=False) erases routing.** `_finalize_midpoints_recursive` (`src/maxpat/hooks.py:149-167`) clears every cord's midpoints recursively and regenerates them. Six skills mandate this call on every edit. Measured on ji-harmonizer: 0 of 367 routed cords keep their midpoints, and 9 straight cords get routed.

**B2: modify_box(args=...) drops cords on content-defined boxes.** It recomputes I/O from the DB for boxes whose I/O comes from their content (`patcher.py:596-601`), even when the args are unchanged. FDNVerb `gen~ FDNverb` with the same args goes 2/2 -> 2/1 and 41 -> 40 cords. Names not in the DB go to 0/0 and lose every cord.

**B3: message/comment prefix.** `modify_box(args=...)` writes `message read drums.wav` / `comment New label`.

**Plus:** `populate_assistance_comments` sets only `extra_attrs`, so on loaded patches its comments never reach disk.

After this plan:
- the edit-path finalize never clears midpoints. It routes only cords that have none and are new or touch an added or moved box;
- modify_box keeps I/O and cords for content-defined boxes and recomputes only for variable_io objects;
- message/comment text is the joined args;
- assistance comments persist;
- step 3 of the six Output Protocol blocks says so.

Output: three atomic commits (one per task), one new test file, and a one-line change in each of the six skills. No committed patch file, CLAUDE.md, command or TECHNICAL.md is edited.
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
- Q3, Q4 and Q5 have landed, so the suite must stay **fully green**. The planner measured the baseline at HEAD `bc1ab66` on 2026-10-12: **2540 passed, 1 xfailed, 1 xpassed, 29 warnings**. The executor re-measures it in Step 0.
- Execution is sequential on the main working tree (no worktree), branch `main`. Tasks 1 and 2 both edit `src/maxpat/patcher.py` and `tests/test_edit_keeps_user_work.py`, so the tasks run in order.
- Leave these alone and never stage them:
  - `patches/.active-project.json` (modified);
  - `.planning/tci-phase2/` (untracked);
  - the untracked `base-sha.txt` / `baseline-pytest.txt` / `stash-list-before.txt` files in the c5i, di7, egf and m87 quick dirs;
  - this task dir's own copies of those three files.

  Another instance may commit concurrently. Commit only each task's `<files>`, with `git commit -m ... -- <paths>`.
- **The tests never write anywhere.** Real patches (ji-harmonizer, FDNVerb) are loaded with `json.load`, wrapped in `copy.deepcopy`, built with `Patcher.from_dict`, and inspected in memory only. No test calls `save_patch_roundtrip`, `write_gendsp`, `write_js` or git. Each verify asserts that `git status --porcelain -- patches/` shows nothing except the pre-existing `.active-project.json`.
- The local interpreter is Python 3.14 and no 3.10 is installed. Avoid 3.11+ syntax and APIs (no `match`, no `ExceptionGroup`, no `Self`, no PEP 695 generics). Every task's verify runs an `ast.parse(..., feature_version=(3, 10))` gate.
- The interactive shell is zsh. Multi-statement gates are wrapped in `bash -c '...'`. The Q5 SUMMARY recorded a gate that broke under zsh word-splitting.
- Throwaway scripts and outputs go in a scratch directory **outside the repo**: your session scratchpad, else `mktemp -d`.
</rules>

<open_questions>
This is a decision the report doesn't make (rule 7). The orchestrator must put it to the user before execution and record the answer on the `Answer:` line. If execution starts with no recorded answer, the executor uses the **Recommended** option and lists it in SUMMARY.md as "resolved by default". Task 2 is written for the recommended option, and the alternative's delta is stated.

**OQ1. How does modify_box treat `expr` / `vexpr`?**
- Review B2 lists "some `expr`" among content-defined boxes. The Q6 spec instead defines content-defined by the DB flag, and `expr`/`vexpr` are `variable_io: true` with an `arg_count` rule.
- That rule counts whitespace tokens, not `$i/$f/$s` variables:
  - `compute_io_counts("expr", ["$f1", "+", "$f2"])` returns 3 inlets (MAX makes 2);
  - `expr $f1+$f2` gives 1 inlet, so its inlet-1 cord would be orphaned.
- Fixing the rule is C1, which belongs to Q10.

Options:
- A) **(Recommended) Spec-literal plus the unchanged-text short-circuit (S3).**
  - expr/vexpr recompute through the DB rule when their text changes, and every cord still in range survives.
  - Re-applying identical args changes nothing, which covers B2's "even when the args are unchanged".
  - The miscount on a *changed* expression is listed as a residual for Q10.
- B) **Treat expr/vexpr as content-defined until Q10.**
  - Add both names to `CONTENT_DEFINED_NAMES`, so changing an expression never changes I/O.
  - Downside: changing `expr $f1` to `expr $f1 + $f2` leaves 1 inlet, so the new inlet can't be connected.
  - Delta: Task 2 adds a changed-args expr test that asserts the counts are kept, and SUMMARY lists Q10 as the owner of removing the two names.

Answer: A (Recommended) — follow the spec literally; user-selected 2026-10-12.
</open_questions>

<assumption_delta_decision>
The assumption-delta and ai-integration detectors were not run. This quick task has no ROADMAP phase, so the phase-section probe has no input (`skipped`, not `detected:false`). Read manually, there is no singular-to-plural or derived-to-chosen shift. The only new piece of state is a load-time rect snapshot per box (`_loaded_rect`), which is derived, not chosen. No external service, ORM or schema is involved, so no coverage matrix or schema gate applies.
</assumption_delta_decision>

<context>
CLAUDE.md is already loaded as project instructions. Don't re-read it, and don't edit it in this task.

Read only these ranges:
- `.planning/reviews/2026-10-11-repo-review.md`: lines 63-69 (the 1B table header, B1, B2, B3) and line 178 (J7). This satisfies rule 1.
- `.planning/reviews/2026-10-11-fix-plan.md`: lines 17-31 (rules) and 124-137 (Q6).
- `src/maxpat/hooks.py`: lines 110-168 (`finalize_patch`, `_finalize_midpoints_recursive`).
- `src/maxpat/layout.py`: lines 195-210 (the `apply_layout` call site) and 1086-1176 (`_generate_midpoints`).
- `src/maxpat/patcher.py`:
  - 116-127 (`EditResult`);
  - 137-234 (`Box.__init__`);
  - 555-659 (`modify_box`);
  - 1115-1199 (`populate_assistance_comments` / `_populate_comments_recursive`);
  - 1201-1340 (`from_dict`).
- `src/maxpat/builders.py`: lines 40-60 (`add_box` signature), 81-110 (`add_comment`), 510-532 (`add_message`) and 602-670 (`add_subpatcher`). Useful for building synthetic patches that are then reloaded via `Patcher.from_dict(p.to_dict())`.
- Existing contracts that must stay green:
  - `tests/test_hooks.py` lines 235-283;
  - `tests/test_patcher.py` lines 1166-1330;
  - `tests/test_round_trip.py` lines 1315-1375;
  - `tests/test_layout.py` lines 315-345;
  - `tests/test_aesthetics.py` lines 1188-1195.
</context>

<observed_facts>
The planner verified these on 2026-10-12 at HEAD `bc1ab66`. If a live value differs at execution time, the live value wins; record the difference in SUMMARY.md.

**Line references (the spec's numbers have drifted):**
- `finalize_patch` is at `hooks.py:122-146` (spec 85-103), and `_finalize_midpoints_recursive` at `hooks.py:149-167`. The clearing loop is lines 159-161.
- `modify_box` is at `patcher.py:555-659` (spec 590-625).
  - The args branch is lines 590-634: the text build at 593-594, the DB recompute at 596-601, resize at 603-606, the orphan sweep at 608-625 and the `_raw` sync at 627-634.
- `_populate_comments_recursive` is at `patcher.py:1138-1199`. The four `extra_attrs["comment"] = ...` assignments are at 1175, 1177, 1194 and 1196.
- `from_dict` is at `patcher.py:1201-1340`.
  - `box.patching_rect` is the *same list object* as `box_data["patching_rect"]`, and therefore as `_raw["patching_rect"]` (line 1259; finding B6, owned by Q28). `modify_box(position=...)` mutates it in place (lines 637-640).
  - So "moved" can't be detected by comparing with `_raw`. It needs a separate snapshot copied at load time (S1).
- `_generate_midpoints` is at `layout.py:1086`.
  - It already skips lines that have midpoints (lines 1117-1118), so the clearing loop is what defeats it.
  - `apply_layout` calls it at `layout.py:205` with no extra argument. `tests/test_layout.py:323` and `:341` call it directly the same way.
- `Box.__new__` is used in `builders.py` (panel, step marker, add_subpatcher, bpatcher, gen in/out/codebox, add_gen parent, node.script, js). All of those boxes set `_raw = None` and do **not** get a `_loaded_rect` attribute, so the predicate must use `getattr(box, "_loaded_rect", None)`.

**Repros on real patches (in memory, deepcopies):**
- ji-harmonizer, walked recursively:
  - 390 lines, 367 with midpoints;
  - after `finalize_patch(is_new=False)`: 0/367 midpoints kept, and 9 previously straight cords routed.
  - 15 inlet/outlet boxes have an empty comment: `p init` 2, `p wtctl` 1, `p ratioset` 12.
- FDNVerb: the target is top-level `obj-4`, `maxclass == "newobj"`, text exactly `gen~ FDNverb`.
  - It has no embedded patcher (it references `FDNverb.gendsp`).
  - The top-level patcher has 41 lines, and 16 of them touch obj-4.
  - `modify_box(obj4, args=["FDNverb"])` gives I/O 2/2 -> 2/1, 40 lines, 1 orphaned.
  - A nested **comment** inside `p about` also starts with "gen~ FDNverb:". Tests must select by maxclass, exact text and top level.
- For both patches, `Patcher.from_dict(deepcopy).to_dict()` gives `lines` arrays equal to the file's in every patcher (0 diffs). Neither file has an empty `midpoints` array.

**DB facts:**
- `variable_io: false`: gen~, mc.gen~, p, patcher, poly~, mc.poly~, js, jsui, v8, v8ui, node.script, node.codebox, v8.codebox, jit.gen, jit.pix, jit.gl.pix, rnbo~, pfft~, cycle~, coll, pattr, message, comment, toggle.
- `variable_io: true`: bpatcher (rule `inherited_from_subpatch`, which can't be computed from args), expr, vexpr, trigger/t, pack, unpack, route, sel, gate.
- 39 variable_io objects; only `o.route` has no rule.
- `compute_io_counts` returns **(0, 0) for a name not in the DB**. A loaded abstraction loses every cord on `modify_box(args=...)` today.

**Callers that must stay green:**
- `finalize_patch(is_new=False)`: `tests/test_hooks.py:253`, `:277`. Both build fresh Patchers, so every box is "added" and the behavior is unchanged.
- `modify_box(args=...)`:
  - `tests/test_patcher.py:1174`, `:1184`, `:1195`, `:1212`, `:1277`, `:1319` (new cycle~/trigger boxes; trigger shrink orphans 2);
  - `tests/test_round_trip.py:1332`, `:1375` (kicksynth `cycle~` and `boxes[0]`).
- `tests/test_aesthetics.py:1195` asserts that `repair_text_contrast` is not in `finalize_patch`'s source.
- No test asserts the text of the skills' step-3 lines. `tests/test_agent_skills.py` only checks that `modify_box`, `find_box` and `save_patch_roundtrip` appear.

**Docs that become stale or wrong** (rule 8: not edited here, listed in SUMMARY.md):
- `.claude/skills/references/shared-capabilities.md:25` ("regenerates midpoints" on the edit path) and `:122`;
- `TECHNICAL.md:317` (modify_box "with I/O recomputation");
- the capability lines `max-patch-agent/SKILL.md:44`, `max-dsp-agent/SKILL.md:75`, `max-ui-agent/SKILL.md:38` ("midpoints + comments (edit)": loose but not wrong);
- `README.md:115` (the "preserving ... manual changes you've made in MAX" promise now holds for routing and cords; B4/B5 are still open);
- `.claude/commands/max-iterate.md:87` ("Preserves all positions and connections": now true for modify_box; replace_box is still Rule #8).
</observed_facts>

<settled_decisions>
These were resolved at planning from the Q6 spec and the B1-B3 fix columns. Don't re-litigate them; if something live contradicts one, stop and ask (rule 7).

- **S1: Edit-path routing (B1).**
  - In `layout.py`, add a keyword-only parameter: `_generate_midpoints(patcher, *, eligible=None)`, where `eligible` is an optional callable taking a Patchline and returning bool.
    - In the first classification loop, right after the existing midpoints skip, skip any line for which `eligible` is not None and returns False.
    - With the default None, behavior is byte-identical, so `apply_layout` and the direct test calls are unchanged.
    - Document the parameter in the docstring.
  - In `patcher.py`:
    - `Box.__init__` sets `self._loaded_rect = None`;
    - `from_dict` sets `box._loaded_rect = tuple(box.patching_rect)`, a copy taken at load. Nested patchers get it through the existing recursive `from_dict`.
    - Don't touch the shared-list behavior; B6 is Q28's.
  - In `hooks.py`, add `_box_added_or_moved(box) -> bool`. It returns True when `box._raw is None` or `getattr(box, "_loaded_rect", None) is None` (added). Otherwise it returns True only when `box.patching_rect[0]` or `[1]` differs from the snapshot's x/y (moved).
    - A resize alone (a width change from a text edit) is not "moved".
  - Rewrite `_finalize_midpoints_recursive` so it never clears. For each patcher:
    1. compute `touched` = ids of added-or-moved boxes;
    2. call `generate_fn(patcher, eligible=...)`, where a line is eligible when `line._raw is None` (a new cord) or its source_id or dest_id is in `touched`;
    3. recurse exactly as today.

    `_generate_midpoints` itself still skips lines that already have midpoints. Net rule (spec): **a cord is routed only if it has no midpoints and is new or touches an added or moved box.** A moved box's already-routed cords keep their midpoints (residual, SUMMARY).
  - Update the `finalize_patch` docstring's edited-patches paragraph and the `_finalize_midpoints_recursive` docstring. Cite Q6 / B1.
  - Don't add `repair_text_contrast` or any other call to `finalize_patch`.
- **S2: Assistance comments reach disk.** In `_populate_comments_recursive`, wherever an inferred comment is assigned to `extra_attrs["comment"]`, also set `box._raw["comment"]` to the same string when `box._raw is not None`.
  - The skip rule ("already has a non-empty comment") and the inference text are unchanged.
  - Add one sentence to the `populate_assistance_comments` docstring: on loaded boxes the comment is written to `_raw` so it serializes.
- **S3: modify_box(args=...) (B2, B3).** Keep the signature and the EditResult shape. When `args` is given:
  1. `new_args = list(args)`.
     - For `box.maxclass in ("message", "comment")`, `new_text = " ".join(new_args).strip()` and the I/O mode is "keep" (B3).
     - Otherwise `new_text = " ".join([box.name] + new_args).strip()`, and the I/O mode is "keep" when `self._io_is_content_defined(box)`, else "recompute".
  2. Set `box.args = new_args`. **If `new_text == box.text`, stop:** no I/O recompute, no resize, no orphan sweep, no `_raw` change.
  3. Otherwise:
     - set `box.text = new_text`;
     - in "recompute" mode only, set numinlets/numoutlets from `self.db.compute_io_counts(box.name, new_args)` and outlettype from `self.db.get_outlet_types(box.name, new_args)`;
     - resize as today;
     - run the existing orphan sweep (it can only orphan in "recompute" mode);
     - sync `_raw` as today (text, numinlets, numoutlets, outlettype when present, patching_rect).
  - Add a module constant `CONTENT_DEFINED_NAMES = frozenset({"p", "patcher", "bpatcher", "gen~", "mc.gen~", "jit.gen", "poly~", "mc.poly~", "js", "jsui", "v8", "v8ui", "node.script"})`. This is the spec's list, plus review B2's `jit.gen`, plus the direct siblings `patcher`, `mc.poly~` and `v8ui`.
  - Add `Patcher._io_is_content_defined(box) -> bool`, which returns True when any of these hold:
    - `box._inner_patcher is not None`;
    - `box.maxclass == "bpatcher"`;
    - `self.db` is falsy;
    - the alias-resolved name (`self.db._aliases.get(box.name, box.name)`, the same access `Box.__init__` uses) is in `CONTENT_DEFINED_NAMES`;
    - `self.db.lookup(box.name)` is None (an abstraction or unknown name);
    - the entry's `variable_io` is falsy.

    It returns False only for a DB object marked variable_io that hits none of the above. bpatcher is listed because the DB marks it variable_io with an uncomputable rule.
  - Rewrite the modify_box docstring: the keep/recompute rule, the message/comment text rule, the unchanged-text short-circuit, and orphans only from a variable_io shrink. Cite Q6 / B2 / B3. Under OQ1-B, add `"expr"` and `"vexpr"` to the constant.
  - UI widgets other than message/comment keep today's text behavior (out of scope; SUMMARY residual).
- **S4: Tests.** Create the new file `tests/test_edit_keeps_user_work.py`.
  - The module docstring cites quick 261012-pkh, Q6, B1, B2 and B3, and says real patches are only read and deep-copied.
  - A module-scoped fixture holds one `ObjectDatabase()`, passed as `db=` to every `Patcher.from_dict` and `Patcher(...)`.
  - Helpers:
    - `_load(rel)` returns `Patcher.from_dict(copy.deepcopy(json.load(open(REPO / rel))), db=db)`, where `REPO = Path(__file__).resolve().parents[1]`;
    - `_walk(patcher, path="top")` yields `(path, patcher)` recursively through `_inner_patcher`;
    - `_reload(p)` returns `Patcher.from_dict(p.to_dict(), db=db)`, which turns API-built boxes into loaded boxes with `_raw`.
  - No test writes files or runs git. Don't modify any existing test file.
- **S5: Skills (spec: only where guidance becomes wrong).** Only the step-3 line of the six "Output Protocol (Edited Patches)" blocks becomes wrong: it describes a full midpoint regeneration. Replace that whole line with exactly the text below, and change nothing else in those files:

  `3. Finalize patch: ``finalize_patch(patcher, is_new=False)`` -- never clears existing midpoints: it routes only cords that have none and are new or touch a box you added or moved, and fills empty inlet/outlet assistance comments (saved to disk), without repositioning existing objects`

  The double backticks above stand for single backticks in the file, matching the current line's code span.
</settled_decisions>

<tasks>

<task type="tracer" tdd="true">
  <name>Task 1: Edit-path finalize keeps routing end-to-end (B1): load a real patch, add a box and a cord, run finalize_patch(is_new=False), serialize. Every existing midpoint and straight cord survives, only the new cord is routed, and assistance comments reach disk</name>
  <files>tests/test_edit_keeps_user_work.py, src/maxpat/layout.py, src/maxpat/hooks.py, src/maxpat/patcher.py</files>
  <read_first>.planning/reviews/2026-10-11-repo-review.md (lines 63-69, 178), .planning/reviews/2026-10-11-fix-plan.md (lines 17-31, 124-137), src/maxpat/hooks.py (lines 110-168), src/maxpat/layout.py (lines 195-210, 1086-1176), src/maxpat/patcher.py (lines 137-234, 1115-1340), tests/test_hooks.py (lines 235-283)</read_first>
  <behavior>
    "Snapshot" means a dict mapping `(path, index)` to the line's midpoints (a list copy, or None), built over `_walk`. JH = `patches/ji-harmonizer/generated/ji-harmonizer.maxpat`.

    TestFinalizeKeepsRouting:
    - JH unchanged through `finalize_patch(p, is_new=False)`:
      - all 367 lines that had midpoints have identical lists;
      - all 23 that had none still have none;
      - for every patcher (walk the serialized dict and the file's dict in parallel by box id), the serialized `lines` array equals the file's.
      - RED: 0/367 kept, 9 straight cords routed.
    - JH with work added:
      - setup: take a top-level loaded box S with `numoutlets >= 1`; add `print q6` with `add_box(..., x=S.x + 300, y=S.y + 200, skip_overlap_check=True)`; `add_connection(S, 0, new, 0)`; then finalize.
      - The new cord has non-empty midpoints, and the 367 + 23 pre-existing lines are exactly as in the snapshot.
      - RED: the pre-existing lines are rerouted.
    - Moved box (synthetic, built with the API then reloaded with `_reload`):
      - layout: A at (30, 30), B at (30, 100), C at (30, 170); cord A->B with no midpoints; cord B->C with midpoints `[40, 140, 40, 150]` set before reload.
      - `modify_box(B, position=[300, 100])`, then finalize.
      - A->B gets non-empty midpoints, and B->C keeps exactly `[40, 140, 40, 150]`.
      - RED: B->C is cleared and regenerated.
    - Unmoved control: A at (30, 30), B at (300, 100), a straight cord A->B, reloaded. After finalize the cord is still straight. RED: it gets routed.
    - Fresh-Patcher path unchanged: the two existing `test_hooks.py` edit-path tests stay green with no edits (all boxes count as added).

    TestAssistanceCommentsPersist:
    - Synthetic: `add_subpatcher("sub", inlets=1, outlets=1)` with the inner inlet -> `print x` -> outlet, plus a second subpatcher whose inlet has a non-empty comment "keep me". Reload, call `populate_assistance_comments()`, then `to_dict()`:
      - the first inner inlet and outlet dicts carry a non-empty "comment";
      - the "keep me" comment is unchanged.
      - RED: the key stays "" on disk.
    - JH after `finalize_patch(is_new=False)`: in the serialized dict, every inlet/outlet box in `p init`, `p wtctl` and `p ratioset` has a non-empty "comment" (15 previously empty). RED.
  </behavior>
  <action>
    Implement the Q6 `finalize_patch(is_new=False)` and `populate_assistance_comments` bullets per S1, S2 and S4.

    Step 0, baseline (rule 4). Set `Q=.planning/quick/261012-pkh-implement-q6-in-planning-reviews-2026-10`.
    - If `$Q/base-sha.txt`, `$Q/stash-list-before.txt` and `$Q/baseline-pytest.txt` don't exist, create them: `git rev-parse HEAD`, `git stash list`, and the last lines of the baseline pytest run. Never overwrite them if present, and never stage them.
    - If HEAD moved from `bc1ab66` because another instance committed, record that in SUMMARY.md and continue.
    - Run `python3 -m pytest -q -p no:cacheprovider` and confirm it is fully green. Expected: 2540 passed, 1 xfailed, 1 xpassed, 29 warnings. Record the totals and the warning count.

    RED:
    1. Create `tests/test_edit_keeps_user_work.py` with the module docstring, the db fixture and the helpers (S4), plus TestFinalizeKeepsRouting and TestAssistanceCommentsPersist covering every `<behavior>` bullet.
    2. Run it and confirm it is red for the stated reasons. Record the red/green counts for SUMMARY.md.

    GREEN:
    3. `src/maxpat/layout.py`: add the keyword-only `eligible` parameter to `_generate_midpoints` per S1 (one guard in the first loop, plus the docstring). Touch nothing else in layout.py.
    4. `src/maxpat/patcher.py`:
       - add the `_loaded_rect` default in `Box.__init__` and the snapshot in `from_dict` (S1);
       - add the `_raw["comment"]` write in `_populate_comments_recursive`, plus its docstring sentence (S2).
       - Nothing else in patcher.py changes in this task.
    5. `src/maxpat/hooks.py`: add `_box_added_or_moved`, rewrite `_finalize_midpoints_recursive` without the clearing loop, pass the per-patcher `eligible` callable, and update both docstrings (S1). `finalize_patch`'s `is_new=True` branch is unchanged.
    6. Re-run until green. Then run `tests/test_hooks.py`, `tests/test_layout.py`, `tests/test_aesthetics.py`, `tests/test_round_trip.py` and `tests/test_patcher.py`, then the full suite, which must be fully green with xfailed/xpassed unchanged (1/1).

    Commit with explicit paths only: `git add tests/test_edit_keeps_user_work.py src/maxpat/layout.py src/maxpat/hooks.py src/maxpat/patcher.py`, then `git commit -m "fix(edit): finalize_patch(is_new=False) keeps existing midpoints and routes only new or moved cords; assistance comments reach disk (Q6 B1)" -- tests/test_edit_keeps_user_work.py src/maxpat/layout.py src/maxpat/hooks.py src/maxpat/patcher.py`.
  </action>
  <verify>
    <automated>bash -c 'python3 -m pytest -q -p no:cacheprovider tests/test_edit_keeps_user_work.py tests/test_hooks.py tests/test_layout.py tests/test_aesthetics.py tests/test_round_trip.py || exit 1; GS=$(git status --porcelain -- patches/) || { echo GIT-STATUS-FAILED; exit 1; }; W=$(printf "%s\n" "$GS" | grep . | grep -v " patches/.active-project.json$"); [ -z "$W" ] || { echo "PATCH-WORKTREE: $W"; exit 1; }; echo PATCHES-UNTOUCHED'</automated>
    <automated>python3 -c "import ast,sys; [ast.parse(open(f).read(), filename=f, feature_version=(3, 10)) for f in sys.argv[1:]]; print('PY310-SYNTAX-OK')" src/maxpat/layout.py src/maxpat/hooks.py src/maxpat/patcher.py tests/test_edit_keeps_user_work.py</automated>
    <automated>python3 -m pytest -q -p no:cacheprovider && echo SUITE-GREEN</automated>
  </verify>
  <done>
    - Every TestFinalizeKeepsRouting and TestAssistanceCommentsPersist case passes, and each RED case was recorded red first.
    - ji-harmonizer keeps 367/367 midpoints and 23/23 straight cords through the edit-path finalize, and its serialized lines equal the file's.
    - Only new cords, or cords touching added or moved boxes, are routed.
    - Inferred assistance comments serialize on loaded subpatchers.
    - The full suite is green, and nothing under `patches/` changed.
    - One commit containing exactly the 4 listed paths.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: modify_box keeps user work (B2, B3): content-defined boxes keep their I/O and cords, variable_io objects recompute and keep in-range cords, identical text is a no-op, and message/comment text has no maxclass prefix</name>
  <files>src/maxpat/patcher.py, tests/test_edit_keeps_user_work.py</files>
  <read_first>.planning/reviews/2026-10-11-repo-review.md (lines 68-69), src/maxpat/patcher.py (lines 555-659, as left by Task 1), src/maxpat/builders.py (lines 81-110, 510-532, 602-670), tests/test_patcher.py (lines 1166-1330), tests/test_round_trip.py (lines 1315-1375)</read_first>
  <behavior>
    FD = `patches/FDNVerb/generated/FDNVerb.maxpat`. `box4` = the top-level box with `maxclass == "newobj"` and text exactly `gen~ FDNverb`. "Loaded" means built with the API and passed through `_reload`, or loaded from a literal dict, so the box has `_raw`.

    TestModifyBoxContentDefined:
    - FD, same args: `modify_box(box4, args=["FDNverb"])`:
      - box4 is 2/2;
      - top-level `len(lines) == 41`;
      - `orphaned == []`;
      - `box4.patching_rect` is unchanged (no resize);
      - the serialized top-level lines equal the file's.
      - RED: 2/1, 40.
    - FD, changed args: `modify_box(box4, args=["FDNverb2"])` gives text `gen~ FDNverb2`, still 2/2 and 41 lines, `orphaned == []`, and `_raw["numoutlets"] == 2`. RED.
    - Loaded `p articulation` with 2 inner inlets and 2 inner outlets (parent 2/2), with a cord into each inlet and out of each outlet: `modify_box(args=["phrasing"])` keeps 2/2 and all 4 cords, and the text becomes `p phrasing`. RED: DB 1/1 orphans 2.
    - Loaded `js engine.js` with numinlets 3 / numoutlets 2 and cords into inlets 0-2 and out of outlet 1 (literal dict): `args=["engine2.js"]` keeps 3/2 and all 4 cords. RED.
    - Loaded abstraction `q6-test-abstraction 1` (a name not in the DB) with 2/2 and cords on every port: `args=["2"]` keeps 2/2 and every cord. RED: 0/0, all orphaned.
    - `_io_is_content_defined` predicate:
      - True for: the loaded box4, a box with an embedded patcher, a loaded bpatcher box, `js`, `node.script`, an unknown name, and `cycle~` (not variable_io);
      - False for: `trigger`, `pack`, `expr` (the last under OQ1-A only).

    TestModifyBoxVariableIO (guards):
    - Loaded `pack 0 0 0` with cords into inlets 0, 1 and 2: `args=["0", "0"]` gives numinlets 2, exactly the inlet-2 cord in `result.orphaned`, and the other two kept.
    - Loaded `trigger b i f` with cords out of all 3 outlets: `args=["b", "b", "b", "b"]` gives 4 outlets and keeps all 3 cords.
    - Unchanged text, OQ1-A: loaded `expr $f1+$f2` with numinlets 2 and cords into inlets 0 and 1. `modify_box(args=["$f1+$f2"])` keeps 2 inlets, both cords, and an unchanged patching_rect. RED: recompute gives 1 inlet and orphans the inlet-1 cord.

    TestModifyBoxText (B3):
    - New `add_message("read a.wav")`, then `modify_box(args=["read", "drums.wav"])`: `box.text == "read drums.wav"` and I/O is unchanged. RED: `message read drums.wav`.
    - Loaded message box with a cord from its outlet to `print`: the same edit gives `_raw["text"] == "read drums.wav"`, the serialized box text matches, the cord is kept, and I/O is unchanged. RED.
    - New `add_comment("Old")`, then `args=["New", "label"]` gives `box.text == "New label"`. RED: `comment New label`.
    - Existing contract tests in `tests/test_patcher.py` and `tests/test_round_trip.py` stay green unedited: cycle~ text update, the trigger shrink that orphans 2, and the kicksynth modify round-trip.
  </behavior>
  <action>
    Implement the Q6 `modify_box(args=…)` and "message/comment" bullets per S3 and S4. Recommended: OQ1-A.

    RED: add TestModifyBoxContentDefined, TestModifyBoxVariableIO and TestModifyBoxText to `tests/test_edit_keeps_user_work.py`, covering every `<behavior>` bullet. Run the file and confirm it is red for the stated reasons; the guard tests may already pass. Record the counts.

    GREEN:
    1. `src/maxpat/patcher.py`:
       - add `CONTENT_DEFINED_NAMES` near the other module constants and `Patcher._io_is_content_defined` next to `modify_box`;
       - rewrite only the `if args is not None:` branch of `modify_box` per S3: message/comment text, keep vs recompute, unchanged-text short-circuit, sweep and `_raw` sync. The position, color and extra_attrs branches are unchanged;
       - rewrite the modify_box docstring (S3).
       - Under OQ1-B, add `expr`/`vexpr` to the constant and replace the unchanged-text expr test with the changed-args test from OQ1-B.
    2. Re-run until green. Then run `tests/test_patcher.py`, `tests/test_round_trip.py`, `tests/test_hooks.py` and `tests/test_agent_skills.py`, then the full suite, which must be fully green with xfailed/xpassed unchanged (1/1).

    Commit with explicit paths: `git add src/maxpat/patcher.py tests/test_edit_keeps_user_work.py`, then `git commit -m "fix(edit): modify_box keeps I/O and cords for content-defined boxes, recomputes only variable_io; message/comment text has no maxclass prefix (Q6 B2 B3)" -- src/maxpat/patcher.py tests/test_edit_keeps_user_work.py`.
  </action>
  <verify>
    <automated>bash -c 'python3 -m pytest -q -p no:cacheprovider tests/test_edit_keeps_user_work.py tests/test_patcher.py tests/test_round_trip.py tests/test_hooks.py || exit 1; GS=$(git status --porcelain -- patches/) || { echo GIT-STATUS-FAILED; exit 1; }; W=$(printf "%s\n" "$GS" | grep . | grep -v " patches/.active-project.json$"); [ -z "$W" ] || { echo "PATCH-WORKTREE: $W"; exit 1; }; echo PATCHES-UNTOUCHED'</automated>
    <automated>python3 -c "import ast,sys; [ast.parse(open(f).read(), filename=f, feature_version=(3, 10)) for f in sys.argv[1:]]; print('PY310-SYNTAX-OK')" src/maxpat/patcher.py tests/test_edit_keeps_user_work.py</automated>
    <automated>python3 -c "from src.maxpat.patcher import CONTENT_DEFINED_NAMES, Patcher; assert {'p','bpatcher','gen~','mc.gen~','poly~','js','jsui','v8','node.script'} <= CONTENT_DEFINED_NAMES; assert hasattr(Patcher, '_io_is_content_defined'); print('CONTENT-DEFINED-OK')"</automated>
    <automated>python3 -m pytest -q -p no:cacheprovider && echo SUITE-GREEN</automated>
  </verify>
  <done>
    - Every new modify_box case passes, and each RED case was recorded red first.
    - FDNVerb `gen~ FDNverb` keeps 2/2 and 41 cords with the same and with changed args.
    - `p`, `js` and unknown abstractions keep their I/O and cords.
    - variable_io objects recompute and orphan only out-of-range cords.
    - Identical text is a no-op.
    - Message/comment text has no maxclass prefix and reaches `_raw`.
    - The existing modify_box contract tests are green unedited, and the full suite is green.
    - One commit containing exactly the 2 listed paths.
  </done>
</task>

<task type="auto">
  <name>Task 3: Update step 3 of the six "Output Protocol (Edited Patches)" blocks, run the final gates, write SUMMARY</name>
  <files>.claude/skills/max-patch-agent/SKILL.md, .claude/skills/max-dsp-agent/SKILL.md, .claude/skills/max-ui-agent/SKILL.md, .claude/skills/max-js-agent/SKILL.md, .claude/skills/max-rnbo-agent/SKILL.md, .claude/skills/max-ext-agent/SKILL.md</files>
  <read_first>.planning/reviews/2026-10-11-fix-plan.md (line 137); in each skill, the "## Output Protocol (Edited Patches)" block: max-patch-agent line 323, max-dsp-agent line 279, max-ui-agent line 218, max-js-agent line 109, max-rnbo-agent line 95, max-ext-agent line 78 (step 3 is 4 lines below each heading)</read_first>
  <action>
    Implement the Q6 "Skills" bullet per S5 and rule 8.

    1. In each of the six skills, replace only the step-3 line of the "Output Protocol (Edited Patches)" block. That is the line starting `3. Finalize patch:` that names `finalize_patch(patcher, is_new=False)`. Replace it with the exact S5 line. Its old description, after the `--`, claims a full midpoint regeneration, which is no longer true.
       - Steps 1, 2 and 4-6 are unchanged, and nothing else in any skill changes. That includes the "midpoints + comments (edit)" capability lines, which stay loosely correct and are listed in SUMMARY.md.
       - Before editing, confirm with a grep that the old step-3 description appears only on those six step-3 lines.
    2. Run the final gates (see the `<verify>` commands). Then commit with explicit paths: `git add` the six SKILL.md paths, then `git commit -m "docs(skills): Output Protocol (Edited Patches) step 3 describes the routing-preserving finalize_patch (Q6 docs)" -- <the six SKILL.md paths>`.
    3. Write SUMMARY.md (see `<output>`).
  </action>
  <verify>
    <automated>bash -c 'for s in patch dsp ui js rnbo ext; do f=.claude/skills/max-$s-agent/SKILL.md; n=$(grep -c "never clears existing midpoints" "$f"); [ "$n" = 1 ] || { echo "NEW-LINE-COUNT=$n in $f"; exit 1; }; o=$(grep -v "^#" "$f" | grep -c "regenerates cable midpoints"); [ "$o" = 0 ] || { echo "OLD-LINE-LEFT in $f"; exit 1; }; grep -q "finalize_patch(patcher, is_new=False)" "$f" || { echo "CALL-MISSING in $f"; exit 1; }; done; echo SKILLS-OK'</automated>
    <automated>bash -c 'python3 -m pytest -q -p no:cacheprovider || exit 1; GS=$(git status --porcelain -- patches/) || { echo GIT-STATUS-FAILED; exit 1; }; W=$(printf "%s\n" "$GS" | grep . | grep -v " patches/.active-project.json$"); [ -z "$W" ] || { echo "PATCH-WORKTREE: $W"; exit 1; }; echo SUITE-GREEN-PATCHES-UNTOUCHED'</automated>
    <!-- planner-discipline-allow: patches/ -->
    <automated>bash -c 'Q=.planning/quick/261012-pkh-implement-q6-in-planning-reviews-2026-10; B=$(cat "$Q/base-sha.txt") || exit 1; N=$(git rev-list --count --grep="(Q6 " "$B"..HEAD) || exit 1; [ "$N" = 3 ] || { echo "Q6-COMMITS=$N"; exit 1; }; H=$(git log --format=%H --grep="(Q6 " "$B"..HEAD) || { echo GIT-LOG-FAILED; exit 1; }; for h in $H; do F=$(git show --name-only --format= "$h") || exit 1; X=$(printf "%s\n" "$F" | grep . | grep -v -E "^(src/maxpat/(hooks|layout|patcher)[.]py|tests/test_edit_keeps_user_work[.]py|[.]claude/skills/max-(patch|dsp|ui|js|rnbo|ext)-agent/SKILL[.]md)$"); [ -z "$X" ] || { echo "EXTRA-FILES in $h: $X"; exit 1; }; done; S=$(git stash list) || { echo GIT-STASH-LIST-FAILED; exit 1; }; [ "$S" = "$(cat "$Q/stash-list-before.txt")" ] || { echo STASH-CHANGED; exit 1; }; git log --format="%h %s" --grep="(Q6 " "$B"..HEAD; echo GATES-OK-3-Q6-COMMITS-STASH-UNCHANGED'</automated>
  </verify>
  <done>
    - All six step-3 lines carry the S5 text, and the old regeneration description is gone. No other skill line changed.
    - The full suite is green, and nothing under `patches/` changed.
    - Exactly 3 `(Q6 ` commits since `base-sha.txt`, each touching only plan files.
    - The stash list is unchanged.
    - SUMMARY.md is written.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Agent edit -> user's patch on disk | Hand-routed cords, cords and text in a user-confirmed patch must survive an agent edit; the edit path is the only writer. |
| Object DB -> loaded box I/O | DB defaults describe the no-argument case, not a box whose I/O comes from its content (an embedded patcher, a script, an abstraction file). |
| Test suite -> committed patches | Tests read user-confirmed baselines and must never write them. |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-pkh-01 | Tampering | `_finalize_midpoints_recursive` clears and regenerates every midpoint (B1) | high | mitigate | Clearing loop removed. `_generate_midpoints(eligible=...)` routes only cords with no midpoints that are new or touch an added/moved box. Test: ji-harmonizer 367/367 midpoints and 23/23 straight cords kept; serialized lines equal the file's. |
| T-pkh-02 | Tampering | `modify_box(args=...)` recomputes DB I/O for content-defined boxes and silently drops cords (B2) | high | mitigate | `_io_is_content_defined` keeps the counts for embedded patchers, `CONTENT_DEFINED_NAMES`, unknown names and non-variable_io objects. Identical text is a no-op. Tests: FDNVerb 2/2 and 41 cords; `p`, `js` and abstraction cords kept. |
| T-pkh-03 | Tampering | `modify_box` writes a maxclass prefix into message/comment text (B3) | medium | mitigate | Text = joined args for message/comment, synced to `_raw`. Tests on new and loaded boxes check the serialized text. |
| T-pkh-04 | Repudiation | `populate_assistance_comments` reports success but the comment never reaches disk on loaded patches | low | mitigate | `_raw["comment"]` is written alongside extra_attrs. Tests check the serialized dicts (synthetic, plus the 15 ji-harmonizer ports). |
| T-pkh-05 | Tampering | A variable_io rule miscount (expr C1) shrinks I/O and orphans a valid cord | medium | mitigate | The unchanged-text short-circuit protects re-applied args. Changed-expression miscounts are a residual owned by Q10 (OQ1). Orphans are always returned in `EditResult.orphaned`, never silently lost. |
| T-pkh-06 | Tampering | Tests write to or reformat committed patches | high | mitigate | Real patches are loaded with json.load + deepcopy and inspected in memory. No save or git call in tests. Each verify asserts `git status --porcelain -- patches/` is clean apart from the pre-existing `.active-project.json`. |
| T-pkh-07 | Tampering | A moved box's routed cords keep stale midpoints | low | accept | This is the spec's rule (never clear). MAX still draws through the old points. Listed as a residual in SUMMARY.md; the agent can clear specific cords on purpose. |
| T-pkh-SC | Tampering | npm/pip/cargo installs | high | mitigate | No package-manager install. Only the standard library and in-repo code are used, so no Package Legitimacy Audit is required. |
</threat_model>

<source_audit>
Sources:
- the fix-plan Q6 section and its rules;
- review findings B1, B2 and B3 (evidence and fix columns) and J7;
- the Q5 PLAN (plan shape, baseline-file and gate conventions);
- the orchestrator's notes: sequential main tree, path-scoped commits, no stash, real-patch tests on deepcopies only, a recorded baseline, and live line numbers.

This quick task has no ROADMAP phase, CONTEXT.md or RESEARCH.md.

| Source item | Covered by | Status |
|---|---|---|
| GOAL: the edit path keeps cord routing and cords | Tasks 1-2 | COVERED |
| `finalize_patch(is_new=False)`: stop clearing existing midpoints | Task 1 (S1) | COVERED |
| Only route cords that have no midpoints and are new or touch added/moved boxes | Task 1 (S1: `eligible`, `_box_added_or_moved`, `_loaded_rect`) | COVERED (moved = x/y change vs the load snapshot) |
| `modify_box(args=…)`: content-defined boxes keep their I/O counts and cords | Task 2 (S3) | COVERED (embedded patcher, the named set, unknown names, non-variable_io) |
| Recompute I/O only for variable_io; keep cords still in range | Task 2 (S3) | COVERED (plus the unchanged-text short-circuit; expr per OQ1) |
| message/comment text = joined args, no maxclass prefix | Task 2 (S3) | COVERED |
| `populate_assistance_comments` writes `_raw["comment"]` | Task 1 (S2) | COVERED |
| Test: ji-harmonizer deepcopy keeps 100% of its midpoints | Task 1 TestFinalizeKeepsRouting | COVERED (367/367, plus 23 straight cords and serialized-lines equality) |
| Test: FDNVerb `gen~ FDNverb`, same args, keeps 2/2 and 41 cords | Task 2 TestModifyBoxContentDefined | COVERED (also with changed args) |
| Test: message box text has no `message ` prefix | Task 2 TestModifyBoxText | COVERED |
| Skills: update the six Output Protocol blocks only where the guidance becomes wrong | Task 3 (S5) | COVERED (step 3 only) |
| Live line numbers vs the spec | observed_facts; SUMMARY | COVERED |
| Baseline pytest before changes | Task 1 Step 0 | COVERED |
| The 9 rules copied into the plan | `<rules>` | COVERED |
| replace_box identity and rewiring (B4); extra_attrs/fontsize drops (B5); shared lists (B6); port resync (B7) | Q28 / Q29 | EXCLUDED (other tasks); `_loaded_rect` is a copy, so B6 is untouched |
| The expr/vexpr rule fix (C1) | Q10 | EXCLUDED; OQ1 picks interim behavior |
| shared-capabilities, TECHNICAL, README, max-iterate command, capability lines | SUMMARY doc-impact list | EXCLUDED from edits (rule 8), reported |
</source_audit>

<verification>
- `python3 -m pytest -q -p no:cacheprovider` is fully green before (expected 2540 passed, 1 xfailed, 1 xpassed, 29 warnings) and after each task. Passes rise only by the new tests, and xfailed/xpassed stay at 1/1. Record the warning count; this task adds no new warning source.
- `git status --porcelain -- patches/` shows only the pre-existing `.active-project.json` after every test run.
- Exactly 3 `(Q6 ` commits since `base-sha.txt`, each touching only plan files. The stash list is unchanged.
- The Python 3.10 syntax gate passes on every changed `.py` file.
</verification>

<success_criteria>
- B1 is fixed: the edit-path finalize never erases routing, and only new cords, or cords touching added or moved boxes, get midpoints.
- B2 is fixed: modify_box keeps I/O and cords for content-defined boxes and recomputes only for variable_io objects, keeping in-range cords.
- B3 is fixed: message/comment text has no maxclass prefix.
- Assistance comments reach disk. The six skills' step 3 matches the new behavior.
- The suite is green, no patch file is touched, and the code is Python 3.10 clean.
</success_criteria>

<output>
Create `.planning/quick/261012-pkh-implement-q6-in-planning-reviews-2026-10/261012-pkh-SUMMARY.md` when done. It must include:
- baseline and final pytest totals, the red counts recorded before each GREEN step, and the pytest warning count before and after;
- how OQ1 was resolved: user answer, or "resolved by default" with the recommended option;
- live line references vs the spec: `hooks.py:122-167` (spec 85-103) and `patcher.py:555-659` (spec 590-625);
- the repro numbers before and after: ji-harmonizer 0/367 -> 367/367 midpoints kept and 9 -> 0 straight cords rerouted; FDNVerb 2/1 and 40 cords -> 2/2 and 41;
- residuals, all out of scope:
  - a moved box's already-routed cords keep their old midpoints;
  - bus-routed new cords are spaced only against other new cords;
  - expr/vexpr changed-expression miscounts (Q10, C1), and `o.route` has no rule;
  - modify_box(args) on UI widgets other than message/comment still writes a text field;
  - the replace_box identity and rewire losses (B4), extra_attrs/fontsize drops (B5), shared lists (B6) and port resync (B7) are Q28/Q29;
- doc impact, not edited (rule 8):
  - `.claude/skills/references/shared-capabilities.md:25` and `:122`;
  - `TECHNICAL.md:317`;
  - the capability lines at `max-patch-agent:44`, `max-dsp-agent:75` and `max-ui-agent:38`;
  - `README.md:115`;
  - `.claude/commands/max-iterate.md:87`;
  - J7 is now moot: the review's interim advice to call only `populate_assistance_comments()` is no longer needed;
- hand-offs: Q10 (the expr/vexpr rule, which lets OQ1-B's names come out if B was chosen), Q28 (change tracking; `_loaded_rect` can feed its moved/changed set), Q29 (replace_box keeps midpoints and identity);
- rule 9, "Confirm in MAX": no patch file changed, so nothing is required. Optional checks:
  - open a patch with hand-routed cords, run `/max-iterate` to add one object, reopen it in MAX, and confirm the existing routing is intact and only the new cord bends;
  - hover over a subpatcher inlet the edit touched and confirm the assistance tooltip appears.

  Note for the user: the first edit-path save of each existing patch will now also write inferred assistance comments for any inlet/outlet that had none, a one-time diff (e.g. 15 ports in ji-harmonizer).
</output>
