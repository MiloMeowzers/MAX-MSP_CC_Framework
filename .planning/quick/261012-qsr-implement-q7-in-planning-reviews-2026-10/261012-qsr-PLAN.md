---
phase: quick-261012-qsr
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/maxpat/hooks.py
  - src/maxpat/critics/__init__.py
  - src/maxpat/__init__.py
  - tests/test_save_gate.py
  - tests/test_hooks.py
  - README.md
  - TECHNICAL.md
autonomous: true
requirements: [A3, R1]

estimate:
  tokens: 95000
  raw_tokens: 95000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "save_patch_roundtrip and write_gendsp run validate_patch on a deepcopy and review_patch, both using one cached ObjectDatabase (review_patch gains a keyword-only db), AFTER the Q5 stale check and BEFORE any mkdir, write or commit. A refused save leaves the file, HEAD, the staged set and the caller's dict unchanged."
    - "New file (no original_text, no HEAD version and, under OQ1-A, nothing on disk): any blocking validation error (has_blocking_errors is_new=True semantics, so proposed removals count) or critic blocker raises PatchValidationError."
    - "Existing file: only blocking findings absent from the baseline raise. Baseline = original_text, else `git show HEAD:<path>`, else (OQ1-A) the file on disk. Findings are matched as a multiset of keys = origin + level/severity + rule template (box ids, quoted spans and numbers normalized out) + sorted box ids + proposed_removal; finding text is never compared."
    - "An unchanged Patcher round-trip of every committed patches/*/generated/*.maxpat and *.gendsp (67 files at planning time) reports zero new blockers, zero removed cords and zero port-rank changes."
    - "Cords present in HEAD (and in original_text when given) but absent from the new dict, walked recursively with path-qualified keys, produce exactly one SaveGateWarning naming them. A save that removes no cord emits no gate warning at all: the test_save_safety simplefilter('error') tests pass unedited."
    - "A changed x-rank of any inlet/outlet box present in both versions (top level or any embedded subpatcher, matched by a path of (box id, box text) plus the port box id), compared with HEAD and with original_text when given, raises PatchValidationError. A port appended rightmost does not."
    - "force=True bypasses the gate with a SaveGateWarning (a UserWarning subclass) listing what was bypassed. PatchValidationError carries path, findings and port_changes, and still constructs from a bare message."
    - "The hooks.py module docstring, the README validation paragraph and the TECHNICAL.md Write Hooks section describe the gate as built. The full suite is green, nothing under patches/ changed, and every changed .py file passes the Python 3.10 syntax gate."
  artifacts:
    - path: "tests/test_save_gate.py"
      provides: "Q7 regression tests: new-file and new-blocker refusal, pre-existing blockers save, multiset key matching, force bypass, cached DB, cord-removal warning, port x-rank block, write_gendsp gate, round-trip no-false-block sweep over committed patches"
      contains: "TestNewBlockerGate"
      min_lines: 300
    - path: "src/maxpat/hooks.py"
      provides: "Save gate section: SaveGateWarning, PatchValidationError attributes, _gate_db, _finding_key, _blocking_findings, _iter_patchers, _cord_set, _port_ranks, _gate_report, _head_text, _run_save_gate; wired into save_patch_roundtrip and write_gendsp(force=)"
      contains: "_run_save_gate"
    - path: "src/maxpat/critics/__init__.py"
      provides: "review_patch(..., *, db=None) threading the DB into _has_package_boxes and review_packages"
      contains: "db=db"
  key_links:
    - from: "src/maxpat/hooks.py"
      to: "src/maxpat/validation.py + src/maxpat/critics/__init__.py"
      via: "_run_save_gate -> _gate_report -> _blocking_findings -> validate_patch(copy.deepcopy(d), db=_gate_db()) and review_patch(copy.deepcopy(d), db=_gate_db()), inside warnings.catch_warnings + simplefilter('ignore')"
      pattern: "db=_gate_db\\(\\)"
    - from: "src/maxpat/hooks.py"
      to: "src/maxpat/project.py"
      via: "_head_text -> _run_git(root, ['show', 'HEAD:' + rel], ok_codes=(0, 128)); stdout when exit 0, else None; never raises"
      pattern: "HEAD:"
    - from: "src/maxpat/hooks.py save_patch_roundtrip / write_gendsp"
      to: "_run_save_gate"
      via: "called after the stale check and before indent detection, mkdir, _write_and_sync and _auto_commit_saved_file"
      pattern: "_run_save_gate\\("
---

<objective>
Implement Q7 of `.planning/reviews/2026-10-11-fix-plan.md`: an automatic save gate (review finding A3, §4.4 R1).

**A3:** saves never run validation or the critics. `PatchValidationError` is never raised in `src/`. Unallowlisted blockers came in through auto-commits (minitaur 0->3, physics 0->1->2, timestretch 0->1). The hooks.py docstring, README and TECHNICAL.md claim saves are validated.

**R1:** in `save_patch_roundtrip` / `write_gendsp`:
- run `validate_patch(deepcopy)` and `review_patch`;
- refuse only blockers not present in the original file (`force=True` overrides);
- diff the cord set against `git show HEAD:path` and report removed cords;
- check the subpatcher port x-rank.

The stale-file check is already done (Q5). The CI job / PostToolUse hook is Q8.

After this plan:
- a save refuses blockers it introduces (and every blocker in a new file);
- a save warns about removed cords;
- a save refuses a subpatcher port reorder;
- `force=True` bypasses with a warning;
- the docs say so.

Output: three atomic commits (one per task) and one new test file. Also a one-fixture fix in `tests/test_hooks.py`, a keyword-only `db` on `review_patch`, one new export, and doc edits in README.md and TECHNICAL.md. No committed patch file, CLAUDE.md or skill is edited.
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
- Q1-Q6 have landed, so the suite must stay **fully green**. The baseline recorded in this task dir at HEAD `676674a` is **2559 passed, 1 xfailed, 1 xpassed, 29 warnings**. The executor re-measures it in Step 0.
- Execution is sequential on the main working tree (no worktree), on branch `main`. All three tasks edit `src/maxpat/hooks.py`, and Tasks 1-2 both edit `tests/test_save_gate.py`, so the tasks run in order.
- Leave these alone and never stage them:
  - `patches/.active-project.json` (modified);
  - `.planning/tci-phase2/` (untracked);
  - the untracked `base-sha.txt` / `baseline-pytest.txt` / `stash-list-before.txt` files in the c5i, di7, egf, m87 and pkh quick dirs;
  - this task dir's own copies of those three files.

  Another instance may commit concurrently. Commit only each task's `<files>`, with `git commit -m ... -- <paths>`.
- **Every git operation in tests runs in a throwaway repo under pytest's `tmp_path`**, never in the MAX repo. Copy the helper pattern from `tests/test_save_safety.py` lines 26-117 into the new file (`_isolate_git_env` autouse fixture, `_git`, `_repo`, `_head`, `_has_head`, `_head_files`, `_staged`, the `skipif` on missing git). Copy them rather than importing a test module. Real committed patches are read with `json.load` and deep-copied, never written. Each verify asserts that the MAX repo's HEAD and staged set are unchanged by the test run, and that `git status --porcelain -- patches/` shows only the pre-existing `.active-project.json`.
- The local interpreter is Python 3.14 and no 3.10 is installed. Avoid 3.11+ syntax and APIs (no `match`, no `ExceptionGroup`, no `Self`, no PEP 695 generics, no `typing.override`). Every task's verify runs an `ast.parse(..., feature_version=(3, 10))` gate.
- The interactive shell is zsh. Multi-statement gates are wrapped in `bash -c '...'`.
- Throwaway scripts and outputs go in a scratch directory **outside the repo**: your session scratchpad, else `mktemp -d`.
</rules>

<open_questions>
This is a decision the report doesn't make (rule 7). The orchestrator must put it to the user before execution and record the answer on the `Answer:` line. If execution starts with no recorded answer, the executor uses the **Recommended** option and lists it in SUMMARY.md as "resolved by default". The tasks are written for the recommended option, and the alternative's delta is stated.

**OQ1. What is the baseline for an existing file that has no `original_text` and no HEAD version?**

The spec says "compare against the original (`original_text`, else `git show HEAD:path`)" and "New files: refuse any blocker". It doesn't cover a file that exists on disk but is untracked, or that sits outside any git repo, and is saved without `original_text`. Examples: the MUSC319/MUSC320 course folders have no git, and a patch can be saved before its first commit.

Options:
- A) **(Recommended) The on-disk file is the original.**
  - Blockers are diffed against the file currently on disk.
  - Cords and ports use it as the only reference.
  - "New file" means: no `original_text`, no HEAD version, and no file at the path.
  - This matches the spec's intent ("refuse only blockers the save introduces").
- B) **Spec-literal: no `original_text` and no HEAD means a new file.**
  - Every pre-existing blocker refuses until the caller passes `force=True`, even when the save changes nothing.
  - Delta: drop the disk fallback in `_run_save_gate`. The OQ1 test (the non-git seed saved without `original_text`) asserts `PatchValidationError` instead of a successful save.

Answer: A — compare against the file on disk (user-chosen 2026-10-12)
</open_questions>

<assumption_delta_decision>
The assumption-delta and ai-integration detectors were not run. This quick task has no ROADMAP phase, so the phase-section probe has no input (`skipped`, not `detected:false`). Read manually, there is no singular-to-plural or derived-to-chosen shift:
- the gate derives everything from the patch, `original_text`, HEAD and disk;
- the one new piece of state is a process-wide cached `ObjectDatabase`, which is derived, not chosen.

No external service, ORM or schema is involved, so no coverage matrix or schema gate applies.
</assumption_delta_decision>

<context>
CLAUDE.md is already loaded as project instructions. Don't re-read it, and don't edit it in this task.

Read only these ranges:
- `.planning/reviews/2026-10-11-repo-review.md`: line 56 (A3), lines 259-260 (§4.1 classes 9 and 10: lost connections, port x-order) and lines 319-324 (R1). This satisfies rule 1.
- `.planning/reviews/2026-10-11-fix-plan.md`: lines 17-31 (rules) and 139-153 (Q7).
- `src/maxpat/hooks.py`:
  - 1-37 (module docstring, imports);
  - 39-111 (`_auto_commit_saved_file`, the repo-root pattern to mirror);
  - 205-299 (`detect_indent`, `save_patch_roundtrip`);
  - 333-358 (the exception classes);
  - 381-418 (`write_gendsp`).
- `src/maxpat/validation.py`: 103-141 (`ValidationResult`) and 144-246 (`validate_patch`, `has_blocking_errors`).
- `src/maxpat/critics/__init__.py`: 43-118 (`_has_package_boxes`, `review_patch`).
- `src/maxpat/critics/base.py` (the whole file, 26 lines).
- `src/maxpat/project.py`: 304-342 (`_run_git`).
- `src/maxpat/builders.py`: 602-670 (`add_subpatcher`, for Task 2 fixtures).
- Existing contracts that must stay green:
  - `tests/test_save_safety.py` (all, especially the `simplefilter("error")` saves at 121-135 and 381-392);
  - `tests/test_hooks.py` lines 50-70, 140-160 and 332-352;
  - `tests/test_round_trip.py` lines 1080-1142;
  - `tests/test_integration_patches.py` lines 1-120 (the allowlist matcher; leave it alone).
</context>

<observed_facts>
The planner verified these on 2026-10-12 at HEAD `676674a`. If a live value differs at execution time, the live value wins; record the difference in SUMMARY.md.

**Code shape:**
- `save_patch_roundtrip` is at `hooks.py:226-299`. Its stale check is lines 274-284. Indent detection, `json.dumps`, mkdir, `_write_and_sync` and the auto-commit follow.
- `write_gendsp` is at `hooks.py:381-418`. It takes `(code, path, num_inputs=None, num_outputs=None)`, has no `force` and no stale check, and writes `json.dumps(..., indent=2)`.
- `PatchValidationError` (`hooks.py:337`) is a bare `Exception` subclass. It is never raised in `src/` and only imported in `src/maxpat/__init__.py`, `tests/test_hooks.py:27` and the max-dsp-agent skill example, which constructs it with one message string.
- `CriticResult` has only `severity`, `finding` and `suggestion`. `ValidationResult` has `layer`, `level`, `message`, `auto_fixed` and `proposed_removal`. Neither carries a rule id or box ids, so the gate derives its key.
- `ObjectDatabase()` is constructed per call in `critics/__init__.py:46` (`_has_package_boxes`) and in `review_packages` when `db` is None. `review_packages(patch_dict, db=None)` already takes a db. No other critic uses the DB. `validate_patch(..., db=)` already takes one.
- `_run_git(root, args, ok_codes=(0,), timeout=10)` prepends `--literal-pathspecs`. `_run_git('.', ['show', 'HEAD:<rel>'], ok_codes=(0, 128))` returns exit 0 plus the content for a tracked file, and exit 128 ("does not exist in 'HEAD'") for a missing one. A fresh repo with no commits also exits 128.
- Timing: `validate_patch` + `review_patch` on terrain-synth (835 boxes) take about 0.1 s. `ObjectDatabase()` takes about 0.02 s.

**Caller audit** (a probe wrapped `save_patch_roundtrip` and `write_gendsp` and ran 8 test files; 490 passed):
- There were 35 gated calls:
  - `test_save_safety` 16 saves + 2 gendsp;
  - `test_hooks` 3 + 1;
  - `test_round_trip` 2;
  - `test_generation` 2;
  - `test_aesthetics` 1;
  - `test_code_validation` 1 gendsp;
  - `test_codegen` 7 gendsp.
- Exactly one has a blocking finding: `tests/test_hooks.py::TestWriteAndSync::test_save_patch_roundtrip_uses_sync` saves `{"patcher": {"boxes": []}}`, which hits Layer 1 "Missing or invalid 'lines' array". Its fixture gets `"lines": []`; the test is about fsync, not validation.
- No other src or tools code calls either function. `src/maxpat/__init__.py` re-exports them, and `test_agent_skills` / `test_commands` only grep the docs.
- `tests/test_save_safety.py:129` and `:388` wrap saves in `warnings.simplefilter("error")`. So the gate must emit no warning on a clean save, and it must swallow incidental DB/critic warnings.

**Round-trip stability of the designed key** (scratch probe, in memory):
- For all 67 committed `patches/*/generated/*.maxpat` and `*.gendsp`, `Patcher.from_dict(deepcopy).to_dict()` against the file dict gives 0 new blocking keys, 0 removed cords and 0 port-rank changes.
- The files hold 430 inlet/outlet boxes: 129 subpatcher port groups plus 32 top-level groups (abstractions), and no two ports share an x.
- The only baseline blocker is `patches/rhythmic-sampler/generated/slot.maxpat` (the allowlisted fan-out).

**Fixtures confirmed** (Patcher API; boxes are numbered `obj-1`... in creation order):
- `number` -> `+ 0` inlet 0 and inlet 1, plus `+` -> `print`: review blocker "Fan-out without trigger: 'number' (obj-1) outlet 0 connected to 2 destinations ... paths reconverge on '+' (obj-2) at different inlets ...". No validation error.
- `cycle~ 440` -> `dac~`: blocker "Missing gain staging: 'cycle~' (obj-1) connected to 'dac~' (obj-2) ...". One blocker per offending cord.
- Appending the raw patchline `obj-1:0 -> obj-2:7` to that dict gives a connections error with `proposed_removal == ('obj-1', 0, 'obj-2', 7)`. The message names only obj-2. A Patcher round-trip keeps the line.
- `add_subpatcher("ctl", inlets=2, outlets=1)`: inner inlets obj-1 (x 50) and obj-2 (x 130), and inner outlet obj-3. **Inner ids collide with outer ids**, so cord and port keys must be path-qualified.

**Docs at planning time:**
- `hooks.py:3` says "Implements FRM-05: auto hook on file write triggers validation."
- `TECHNICAL.md` "### Write Hooks" is at lines 460-470 (spec: 462):
  - an intro line claiming hooks "automatically trigger validation";
  - a 3-row table with "Blocks on Error = No";
  - a closing sentence (line 470) saying validation runs on demand, not on save.
- `README.md:178` (the "Validation Pipeline" paragraph) claims every patch passes validation and that blockers trigger revision before output is written.
- `force=True` appears 0 times in README.md and TECHNICAL.md, and `PatchValidationError` 0 times in either.

**Docs that become stale or newly true** (rule 8: not edited here, listed in SUMMARY.md):
- CLAUDE.md Rule #7: the save now raises PatchValidationError / warns SaveGateWarning.
- `.claude/skills/references/shared-capabilities.md:147`.
- `.claude/skills/max-lifecycle/references/project-structure.md:80`: "hooks which trigger validation on write" is now true for .maxpat/.gendsp.
- `.claude/skills/max-patch-agent/SKILL.md:314-321`: the Output Protocol steps 3-7 that R1 calls "SKILL.md:317-320". They stay correct, and the gate is a backstop.
- `.claude/skills/max-critic/SKILL.md:49`.
- No skill line becomes wrong, and the Q7 spec doesn't list skills, so none is edited.
</observed_facts>

<settled_decisions>
These were resolved at planning from the Q7 spec, review A3/R1/§4.1 classes 9-10 and the Q1/Q5 hand-offs. Don't re-litigate them; if something live contradicts one, stop and ask (rule 7).

- **S1: Where the gate lives.**
  - It is a clearly headed "Save gate (Q7, review A3 / R1)" section in `src/maxpat/hooks.py`.
  - `validate_patch` is already imported there. Import `review_patch` lazily from `src.maxpat.critics` **inside** `_blocking_findings` at call time, so tests can monkeypatch `src.maxpat.critics.review_patch`.
  - Use `copy` and `functools`/`re` from the standard library only.
- **S2: Public surface.**
  - New `class SaveGateWarning(UserWarning)`. Every warning the gate emits uses it. Export it from `src/maxpat/__init__.py` (the import list and `__all__`, next to `StaleFileError`).
  - `PatchValidationError.__init__(self, message, *, path=None, findings=(), port_changes=())` stores `path`, `findings` (a list of the new blocking ValidationResult/CriticResult objects) and `port_changes` (a list of str), and passes `message` to `Exception`. A bare `PatchValidationError("msg")` keeps working.
  - `save_patch_roundtrip` keeps its signature: the existing keyword-only `force` now also bypasses the gate.
  - `write_gendsp` gains keyword-only `force: bool = False`, and keeps its positional args and its `GendspWriteResult` return.
- **S3: One cached DB.**
  - `_gate_db()` is decorated with `functools.lru_cache(maxsize=1)` and returns `ObjectDatabase()`. Edits to the DB files during a running process are not seen; say so in its docstring.
  - `review_patch(patch_dict, code_context=None, ext_code=None, ext_archetype="message", *, db=None)` passes `db` to `_has_package_boxes(patch_dict, db=None)` (which constructs one only when None) and to `review_packages(patch_dict, db=db)`. With `db=None`, behavior is unchanged.
- **S4: Blocking findings and the key.**
  - `_blocking_findings(patch_dict)` runs `validate_patch(copy.deepcopy(patch_dict), db=_gate_db())` and `review_patch(copy.deepcopy(patch_dict), db=_gate_db())` inside `warnings.catch_warnings()` with `warnings.simplefilter("ignore")`. It never calls `apply_fixes`. It returns:
    - every ValidationResult with `level == "error"`, except a legacy `auto_fixed` one without `proposed_removal`. That mirrors `has_blocking_errors(..., is_new=True)`: per the Q1 hand-off, a **new** proposed removal blocks on edits too, and only pre-existing ones are exempt;
    - every CriticResult with `severity == "blocker"`.
  - `_finding_key(result)` returns a hashable tuple:
    - origin: `("validate", layer, level)` or `("review", severity)`;
    - rule template: the message/finding with box-id tokens (regex `\bobj-\d+\b`) replaced by `<id>` FIRST, then single- or double-quoted spans replaced by `<q>`, then numbers (`\d+(\.\d+)?`) replaced by `<n>`, then whitespace collapsed;
    - `tuple(sorted(ids))`: the extracted ids, plus the source and destination ids of `proposed_removal` when set;
    - `proposed_removal` (or None).

    Keys are compared as `collections.Counter` multisets. A finding is new when its key's count in the new patch exceeds the baseline count. Rationale: the spec says match by "rule + box ids rather than finding text". The 67-file probe shows the key is stable across a round-trip.
- **S5: Baselines and references** (OQ1-A shown; under B, drop "disk").
  - `_head_text(path)` resolves the path and walks up to its nearest existing ancestor directory.
    - It runs `_run_git(anc, ["rev-parse", "--show-toplevel"])` and computes `rel` from the resolved root (resolve both sides: tmp dirs on macOS live under the `/private` symlink).
    - It returns the stdout of `_run_git(root, ["show", "HEAD:" + rel.as_posix()], ok_codes=(0, 128))` when the exit code is 0, else None.
    - Any RuntimeError/ValueError returns None. It never warns or raises.
  - **Blocker baseline** = `original_text`, else the HEAD text, else the on-disk text when the path exists. None means new file: every blocking finding refuses.
  - **Cord/port references** = the HEAD text and `original_text`, each when available. If neither exists, the on-disk text. Comparing against `original_text` too means a change already on disk before this save is never attributed to the save: the stale check guarantees `original_text` equals disk unless `force=True`. Typical case: the user deleted a cord or reordered ports in MAX after the last auto-commit.
    - A cord is **removed** when it is in every reference and absent from the new dict.
    - A port is **changed** when it exists in the new dict and in every reference, and its new rank differs from its rank in every reference.
    - No references means both checks are skipped.
  - A text that fails `json.loads`, or lacks a `patcher` dict, is dropped from its role. A dropped blocker baseline means new-file semantics.
- **S6: Cords and ports** (pure dict walkers, no Patcher).
  - `_iter_patchers(patcher_dict, path=())` yields `(path, patcher_dict)` for the top level and recursively for every box whose `patcher` value is a dict. A path element is `(box id, box text or maxclass)`, so a regenerated patch whose `obj-5` is now a different subpatcher isn't compared port-for-port.
  - `_cord_set(d)` is the set of `(path, src_id, src_outlet, dst_id, dst_inlet)` over all patchers, skipping malformed patchlines.
  - `_port_ranks(d)` maps `(path, "inlet"|"outlet", port box id)` to a rank: the index among that patcher's boxes of that maxclass, sorted by `(patching_rect[0], array index)`. Only maxclass `inlet`/`outlet` count; gen `in N`/`out N` are numbered by argument and excluded.
  - "x-rank changed" means the rank of a port present in both versions changed (review §4.1 #10: "x-rank unchanged vs HEAD"). So a swap, a mid-insert and a mid-delete all block, and a port appended rightmost does not. The memory rule is "new abstraction inlets go rightmost".
- **S7: `_gate_report(new_dict, baseline_dict, ref_dicts)`** is pure (no I/O). It returns a `NamedTuple GateReport(new_blockers, removed_cords, port_changes)`:
  - `new_blockers` is a list of result objects in their original order;
  - `removed_cords` is a sorted list of cord keys;
  - `port_changes` is a list of strings like `"top: inlet obj-2 rank 1 -> 0"` / `"p ctl (obj-1): inlet obj-1 rank 0 -> 1"`.

  Task 1 returns empty `removed_cords`/`port_changes`; Task 2 fills them.
- **S8: `_run_save_gate(patch_dict, path, original_text, *, force)`** gathers the texts (S5), parses them, calls `_gate_report`, then:
  1. If cords were removed, emit ONE `SaveGateWarning`, whatever `force` is: `"<path>: N cord(s) removed compared with HEAD"` (or `"with original_text"` / `"with the file on disk"` when that was the only reference). List the first 10 as `<path>/<src>:<outlet> -> <dst>:<inlet>`, mark `(endpoint box deleted)` when an endpoint id no longer exists in that patcher, and end with `... and K more` when there are more than 10.
  2. If `new_blockers` or `port_changes` is non-empty, build one message:
     - the path;
     - the baseline label: `original_text`, `HEAD`, `the file on disk`, or `new file: every blocker refuses`;
     - each new finding's `repr`;
     - each port change, with the note that parent cords address ports by x-rank;
     - the remedy: "fix them, or pass force=True to save anyway".
     - With force: warn `SaveGateWarning` with `"force=True: saving despite "` + the message.
     - Without force: raise `PatchValidationError(message, path=path, findings=..., port_changes=...)`.
  3. Return None. Nothing is written, created or committed before it returns.

  Call sites:
  - `save_patch_roundtrip`: right after the stale-check block, before indent detection.
  - `write_gendsp`: right after `generate_gendsp`, before mkdir, with `original_text=None`.
</settled_decisions>

<tasks>

<task type="tracer" tdd="true">
  <name>Task 1: Save gate end-to-end on save_patch_roundtrip: a save that introduces a blocker raises PatchValidationError before anything is written or committed. Pre-existing blockers in the original still save, force=True bypasses with a warning, and one cached DB serves validate_patch and review_patch</name>
  <files>tests/test_save_gate.py, src/maxpat/hooks.py, src/maxpat/critics/__init__.py, src/maxpat/__init__.py, tests/test_hooks.py</files>
  <read_first>.planning/reviews/2026-10-11-repo-review.md (lines 56, 259-260, 319-324), .planning/reviews/2026-10-11-fix-plan.md (lines 17-31, 139-153), src/maxpat/hooks.py (lines 1-111, 205-299, 333-358), src/maxpat/validation.py (lines 103-141, 144-246), src/maxpat/critics/__init__.py (lines 43-118), src/maxpat/critics/base.py, src/maxpat/project.py (lines 304-342), tests/test_save_safety.py (lines 1-135, 315-410), tests/test_hooks.py (lines 332-352)</read_first>
  <behavior>
    All git work is in a `_repo(tmp_path)` repo. The target is `P = root/patches/demo/generated/demo.maxpat` (rel `REL_P`). "Seed directly" means writing `json.dumps(d, indent=4)` to P, then `git add -- REL_P` and `git commit -m seed -- REL_P` via `_git`, which bypasses the gate. FAN = number -> `+ 0` inlet 0, plus `+` -> `print` (clean). GAIN = `cycle~ 440` -> `dac~` (a critic blocker). OOR = the raw patchline `obj-1:0 -> obj-2:7` appended to a dict (a validation error with a proposed removal).

    TestNewBlockerGate:
    - New file, GAIN (fresh repo, nothing at P):
      - `save_patch_roundtrip(d, P)` raises PatchValidationError;
      - `exc.findings` has exactly 1 CriticResult containing "Missing gain staging", and `exc.path` is P;
      - "force=True" is in `str(exc)`;
      - P doesn't exist, `_has_head(root)` is False, and `d` equals its pre-call deepcopy.
      - RED: the save succeeds.
    - New file, a clean patch plus OOR: raises, and `exc.findings` is one ValidationResult with `proposed_removal == ("obj-1", 0, "obj-2", 7)`. RED.
    - New reconverging fan-out on an existing file:
      - save FAN through `save_patch_roundtrip` (clean, committed);
      - `read_patch(P)`, then add the cord number -> `+` inlet 1 (by box id, through the Patcher API);
      - `save_patch_roundtrip(p.to_dict(), P, T)` raises, with one finding containing "reconverge";
      - `P.read_text() == T`, and HEAD and the staged set are unchanged.
      - The same edit with no `original_text` (HEAD baseline) also raises. RED for both.
    - New proposed-removal cord on an existing file (the Q1 hand-off): commit clean FAN, then save its dict plus OOR with T. It raises. RED.
    - Pre-existing blockers save. Seed GAIN + OOR directly, then:
      - (a) `read_patch` and an unchanged save with T: no PatchValidationError (a "no changes to commit" UserWarning is fine);
      - (b) add an unconnected `print other` box and save with T: returns `_head(root)`, which is a new commit;
      - (c) the same edit with no `original_text` (HEAD baseline) saves.
      - (b) and (c) are RED-free guards. They must stay green after GREEN.
    - Multiset: seed one GAIN directly. The edit adds a second `cycle~ 440` -> the same `dac~` (new ids) and saves with T. It raises with exactly 1 finding, and that finding names the new cycle~ id. RED.
    - OQ1 (non-git): seed GAIN + OOR at `tmp_path/plain/x.maxpat` with no git. Edit (add `print other`) and save with no `original_text`:
      - OQ1-A: saves (the existing "not inside a git repository" UserWarning is fine);
      - OQ1-B: raises.
    - force=True: the reconverging-fan-out edit with `force=True` saves, warns `SaveGateWarning` matching "force=True", returns `_head(root)`, and disk equals the new dict's JSON. RED: no gate, no warning.

    TestFindingKey (pure, no git):
    - Two CriticResults with the same blocker template that differ only in a quoted name and a number give equal `_finding_key`s.
    - Two that differ only in one `obj-N` give different keys.
    - A ValidationResult whose message names only obj-2 but whose `proposed_removal` is `("obj-1", 0, "obj-2", 7)` has a key whose id tuple is `("obj-1", "obj-2")`.

    TestGateDb:
    - `_gate_db() is _gate_db()`.
    - `review_patch(d, db=_gate_db())` is accepted and returns the same severities as `review_patch(d)` for GAIN.
    - Build the clean patch dict FIRST (`Patcher()` constructs its own DB). Then warm `_gate_db()` and monkeypatch `src.maxpat.db_lookup.ObjectDatabase.__init__` with a counting wrapper that delegates to the original. One clean `save_patch_roundtrip` into a tmp repo constructs 0 new databases. RED: `_has_package_boxes` builds one per review.

    TestRoundTripNoFalseBlocks (in memory, parametrized over `patches/*/generated/*.maxpat` and `*.gendsp`, ids = repo-relative paths):
    - For each file, `_gate_report(Patcher.from_dict(deepcopy(d), db=_gate_db()).to_dict(), d, [d])` has empty `new_blockers`. Skip files without a `patcher` dict.

    Existing contracts, green with no edits except the one fixture:
    - `test_save_safety.py` passes unedited, including both `simplefilter("error")` saves;
    - `tests/test_hooks.py::TestWriteAndSync::test_save_patch_roundtrip_uses_sync`'s data becomes `{"patcher": {"boxes": [], "lines": []}}`.
  </behavior>
  <action>
    Implement the Q7 "Checks", "Existing files" and "New files" bullets for `save_patch_roundtrip`, plus the `force` bypass, per S1-S5, S7 (blocker part) and S8.

    Step 0, baseline (rule 4). Set `Q=.planning/quick/261012-qsr-implement-q7-in-planning-reviews-2026-10`.
    - The three baseline files already exist there. Never overwrite them and never stage them.
    - If HEAD moved from `676674a` because another instance committed, record that in SUMMARY.md and continue.
    - Run `python3 -m pytest -q -p no:cacheprovider` and confirm it is fully green. Expected: 2559 passed, 1 xfailed, 1 xpassed, 29 warnings. Record the totals and the warning count.

    RED:
    1. Create `tests/test_save_gate.py`. The module docstring cites quick 261012-qsr, Q7, A3 and R1, and says all git runs in tmp repos and committed patches are only read. Add the copied tmp-repo helpers, then TestNewBlockerGate, TestFindingKey, TestGateDb and TestRoundTripNoFalseBlocks covering every `<behavior>` bullet.
       - Import `_finding_key`, `_gate_db`, `_gate_report` and `SaveGateWarning` from `src.maxpat.hooks` inside the tests, so collection doesn't fail before GREEN.
    2. Run the file and confirm it is red for the stated reasons. Record the red/green counts for SUMMARY.md.

    GREEN:
    3. `src/maxpat/critics/__init__.py`: add the keyword-only `db` to `review_patch` and the optional `db` to `_has_package_boxes`, per S3, and document `db` in the docstring. No other critic changes.
    4. `src/maxpat/hooks.py`:
       - add the save-gate section: `SaveGateWarning`, `_gate_db`, `_finding_key`, `_blocking_findings`, `_head_text`, the `GateReport` NamedTuple, `_gate_report` (Task 1 fills only `new_blockers`) and `_run_save_gate` (S8, with the cord-warning step a no-op until Task 2);
       - give `PatchValidationError` the S2 `__init__` and docstring;
       - call `_run_save_gate(patch_dict, path, original_text, force=force)` in `save_patch_roundtrip` right after the stale-check block;
       - extend the `save_patch_roundtrip` docstring: it gains a "Save gate (Q7)" paragraph, a `force` that now also bypasses the gate, and Raises: PatchValidationError.
       - Leave the module docstring to Task 3.
    5. `src/maxpat/__init__.py`: import and export `SaveGateWarning`.
    6. `tests/test_hooks.py`: change only the `data` literal in `test_save_patch_roundtrip_uses_sync` to include `"lines": []`. Record it in SUMMARY.md as the one existing caller that needed a change, and why.
    7. Re-run until green. Then run the caller-audit set (`tests/test_save_safety.py`, `tests/test_hooks.py`, `tests/test_round_trip.py`, `tests/test_generation.py`, `tests/test_aesthetics.py`, `tests/test_code_validation.py`, `tests/test_codegen.py`, `tests/test_agent_skills.py`, `tests/test_commands.py`, `tests/test_integration_patches.py`), then the full suite. It must be fully green with xfailed/xpassed unchanged (1/1).

    Commit with explicit paths only: `git add tests/test_save_gate.py src/maxpat/hooks.py src/maxpat/critics/__init__.py src/maxpat/__init__.py tests/test_hooks.py`, then `git commit -m "fix(save): save_patch_roundtrip refuses new validation errors and critic blockers vs original_text/HEAD, force=True bypasses; one cached DB (Q7 A3)" -- tests/test_save_gate.py src/maxpat/hooks.py src/maxpat/critics/__init__.py src/maxpat/__init__.py tests/test_hooks.py`.
  </action>
  <verify>
    <automated>bash -c 'H0=$(git rev-parse HEAD) || exit 1; S0=$(git diff --cached --name-only) || exit 1; python3 -m pytest -q -p no:cacheprovider tests/test_save_gate.py tests/test_hooks.py tests/test_save_safety.py tests/test_round_trip.py tests/test_generation.py tests/test_aesthetics.py tests/test_code_validation.py tests/test_codegen.py tests/test_integration_patches.py || exit 1; [ "$(git rev-parse HEAD)" = "$H0" ] || { echo MAX-REPO-HEAD-MOVED; exit 1; }; [ "$(git diff --cached --name-only)" = "$S0" ] || { echo MAX-REPO-STAGED-CHANGED; exit 1; }; GS=$(git status --porcelain -- patches/) || { echo GIT-STATUS-FAILED; exit 1; }; W=$(printf "%s\n" "$GS" | grep . | grep -v " patches/.active-project.json$"); [ -z "$W" ] || { echo "PATCH-WORKTREE: $W"; exit 1; }; echo GATE-TESTS-GREEN-MAX-REPO-UNTOUCHED'</automated>
    <automated>bash -c 'grep -v "^[[:space:]]*#" src/maxpat/hooks.py | grep -q "raise PatchValidationError(" || { echo "NO-RAISE-IN-SRC"; exit 1; }; grep -q "db=_gate_db()" src/maxpat/hooks.py || { echo NO-CACHED-DB; exit 1; }; grep -q "review_packages(patch_dict, db=db)" src/maxpat/critics/__init__.py || { echo DB-NOT-THREADED; exit 1; }; python3 -c "from src.maxpat import SaveGateWarning, PatchValidationError; assert issubclass(SaveGateWarning, UserWarning); e = PatchValidationError(\"m\"); assert e.findings == [] and e.port_changes == [] and str(e) == \"m\"; print(\"SURFACE-OK\")"'</automated>
    <automated>python3 -c "import ast,sys; [ast.parse(open(f).read(), filename=f, feature_version=(3, 10)) for f in sys.argv[1:]]; print('PY310-SYNTAX-OK')" src/maxpat/hooks.py src/maxpat/critics/__init__.py src/maxpat/__init__.py tests/test_save_gate.py tests/test_hooks.py</automated>
    <automated>python3 -m pytest -q -p no:cacheprovider && echo SUITE-GREEN</automated>
  </verify>
  <done>
    - Every Task 1 test passes, and each RED case was recorded red first.
    - A save that introduces a validation error or critic blocker raises PatchValidationError with structured findings, before any write or commit. The caller's dict is unmodified.
    - Pre-existing blockers (from `original_text`, HEAD, or disk under OQ1-A) save.
    - `force=True` saves with a SaveGateWarning.
    - One cached DB serves both pipelines.
    - All 67 committed files round-trip with no new blocker.
    - The full suite is green, the MAX repo and `patches/` are untouched by tests, and there is one commit containing exactly the 5 listed paths.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Cord-removal warning, port x-rank block and the write_gendsp gate: removed cords produce one SaveGateWarning; a reordered or shifted subpatcher/abstraction port refuses the save; write_gendsp runs the same gate with force=</name>
  <files>src/maxpat/hooks.py, tests/test_save_gate.py</files>
  <read_first>src/maxpat/hooks.py (the Task 1 save-gate section, and write_gendsp at about lines 381-418 before Task 1's growth), src/maxpat/builders.py (lines 602-670), tests/test_save_gate.py (as left by Task 1), tests/test_codegen.py (the write_gendsp tests, found with grep -n write_gendsp), tests/test_save_safety.py (lines 415-440)</read_first>
  <behavior>
    These use the same tmp-repo conventions as Task 1. SUB = a top-level `p ctl` built with `add_subpatcher("ctl", inlets=2, outlets=1)`, with:
    - an inner cord from inner inlet 0 to inner outlet 0 (`inner.add_connection(inner.get_inlets()[0], 0, inner.get_outlets()[0], 0)`);
    - a top-level `number` feeding its inlet 0;
    - a top-level `print` fed by its outlet 0.

    The planner probed the inner ids: inlets obj-1 (x 50) and obj-2 (x 130), outlet obj-3. ABS = `_, inner = Patcher().add_subpatcher("abs", inlets=1, outlets=2)`, saved as `inner.to_dict()`, whose top level holds inlet obj-1 and outlets obj-2 (x 50) and obj-3 (x 130). "Disk-edit" means writing `json.dumps(modified, indent=4)` to P without committing, to simulate a MAX save after the last auto-commit, then calling `read_patch(P)`. New inlet boxes in dict edits are `{"box": {"id": "obj-90", "maxclass": "inlet", "numinlets": 0, "numoutlets": 1, "outlettype": [""], "patching_rect": [X, 30.0, 30.0, 30.0]}}`, and the parent `p ctl` box's `numinlets` is bumped to 3 in the same edit.

    TestCordRemoval:
    - Commit FAN; read; delete the `+` -> `print` patchline from `p.to_dict()`; save with T.
      - It warns exactly one `SaveGateWarning` matching "1 cord(s) removed compared with HEAD" that names `obj-2:0 -> obj-3:0`;
      - the save commits (it returns `_head(root)`).
      - RED: no warning.
    - Delete the `print` box itself via the Patcher API and save. The warning marks `(endpoint box deleted)`. RED.
    - Commit SUB; delete the inner inlet -> outlet cord from the `p ctl` inner patcher's `lines` in the dict; save with T. The single warning names the `p ctl` path and `obj-1:0 -> obj-3:0`. RED.
    - The cord was removed before this save. Commit FAN, disk-edit a copy with the `+` -> `print` line removed, read it, add an unconnected `print other` box, and save with that T under `warnings.simplefilter("error")`. It saves with no warning (exempt per S5). Guard.
    - A clean edit (add an unconnected box) under `simplefilter("error")` saves with no warning. Guard.

    TestPortOrder:
    - Commit SUB; read; in `p.to_dict()`, swap the inner inlets' `patching_rect` x values; save with T.
      - It raises PatchValidationError, and `exc.port_changes` names inner inlets obj-1 and obj-2;
      - `P.read_text() == T`, and HEAD is unchanged.
      - RED: saves.
    - The same swap with `force=True` saves and warns a SaveGateWarning matching "force=True". RED.
    - Top-level abstraction: commit ABS, swap the x of top-level outlets obj-2 and obj-3, and save with T. It raises, and `port_changes` contains "top". RED.
    - Mid-insert: in SUB, add a third inner inlet at X = 90 (between the two). It raises (obj-2's rank shifts 1 -> 2). RED.
    - Append rightmost: add a third inner inlet at X = 210. It saves, with no PatchValidationError and no SaveGateWarning (record warnings and assert none is a SaveGateWarning). Guard.
    - The port order changed before this save. Commit SUB, disk-edit with the inner inlets swapped, read it, add an unconnected top-level box, and save with that T. It saves (exempt per S5). Guard.

    TestWriteGendspGate:
    - A clean `write_gendsp("out1 = in1 * 0.5;", root/patches/demo/generated/x.gendsp, num_inputs=1, num_outputs=1)` under `simplefilter("error")` returns a GendspWriteResult whose `commit_hash == _head(root)`. Guard.
    - Monkeypatch `src.maxpat.critics.review_patch` to return one `CriticResult("blocker", "injected (obj-1)", "s")`:
      - `write_gendsp` to a new path raises PatchValidationError and the file doesn't exist. RED.
      - `force=True` writes it and warns a SaveGateWarning. RED: `force` is not a parameter.
    - Writing the same code again over a committed x.gendsp (HEAD baseline, no blockers) succeeds with no PatchValidationError. Guard.

    TestRoundTripNoFalseBlocks (extend Task 1's parametrized test): also assert `removed_cords == []` and `port_changes == []` for all 67 files.
  </behavior>
  <action>
    Implement the Q7 "Removed cords" and "Port order" bullets, and wire `write_gendsp` into the gate, per S5-S8.

    RED: add TestCordRemoval, TestPortOrder and TestWriteGendspGate to `tests/test_save_gate.py`, and extend TestRoundTripNoFalseBlocks, covering every `<behavior>` bullet. Run the file and confirm it is red for the stated reasons; the guard cases may already pass. Record the counts.

    GREEN, in `src/maxpat/hooks.py`:
    1. Add `_iter_patchers`, `_cord_set` and `_port_ranks` (S6).
    2. Complete `_gate_report`: `removed_cords` is the intersection of the reference cord sets minus the new set, sorted, and `port_changes` follows S5/S7. Empty references give empty lists.
    3. Complete `_run_save_gate`'s cord warning (S8 step 1), and include port changes in the refusal and force messages (S8 step 2).
    4. `write_gendsp`:
       - add the keyword-only `force: bool = False`;
       - call `_run_save_gate(gendsp_dict, path, None, force=force)` after `generate_gendsp` and before mkdir;
       - update its docstring: the gate, `force`, and Raises: PatchValidationError. Keep "there is no stale-file check here".
    5. Re-run until green. Then run `tests/test_codegen.py`, `tests/test_code_validation.py`, `tests/test_save_safety.py`, `tests/test_hooks.py` and `tests/test_integration_patches.py`, then the full suite. It must be fully green with xfailed/xpassed unchanged (1/1).

    Commit with explicit paths: `git add src/maxpat/hooks.py tests/test_save_gate.py`, then `git commit -m "fix(save): save gate warns on removed cords, refuses subpatcher port x-rank changes, gates write_gendsp with force= (Q7 R1)" -- src/maxpat/hooks.py tests/test_save_gate.py`.
  </action>
  <verify>
    <automated>bash -c 'H0=$(git rev-parse HEAD) || exit 1; S0=$(git diff --cached --name-only) || exit 1; python3 -m pytest -q -p no:cacheprovider tests/test_save_gate.py tests/test_codegen.py tests/test_code_validation.py tests/test_save_safety.py tests/test_hooks.py tests/test_integration_patches.py || exit 1; [ "$(git rev-parse HEAD)" = "$H0" ] || { echo MAX-REPO-HEAD-MOVED; exit 1; }; [ "$(git diff --cached --name-only)" = "$S0" ] || { echo MAX-REPO-STAGED-CHANGED; exit 1; }; GS=$(git status --porcelain -- patches/) || { echo GIT-STATUS-FAILED; exit 1; }; W=$(printf "%s\n" "$GS" | grep . | grep -v " patches/.active-project.json$"); [ -z "$W" ] || { echo "PATCH-WORKTREE: $W"; exit 1; }; echo GATE-TESTS-GREEN-MAX-REPO-UNTOUCHED'</automated>
    <automated>python3 -c "import inspect; from src.maxpat.hooks import write_gendsp, _cord_set, _port_ranks, _iter_patchers; p = inspect.signature(write_gendsp).parameters['force']; assert p.kind is p.KEYWORD_ONLY and p.default is False; print('GENDSP-FORCE-OK')"</automated>
    <automated>python3 -c "import ast,sys; [ast.parse(open(f).read(), filename=f, feature_version=(3, 10)) for f in sys.argv[1:]]; print('PY310-SYNTAX-OK')" src/maxpat/hooks.py tests/test_save_gate.py</automated>
    <automated>python3 -m pytest -q -p no:cacheprovider && echo SUITE-GREEN</automated>
  </verify>
  <done>
    - Every Task 2 test passes, and each RED case was recorded red first.
    - Removed cords (recursive, path-qualified) produce one SaveGateWarning, and changes that predate the save are exempt.
    - A port rank change in any subpatcher or abstraction top level refuses the save, while a rightmost append does not.
    - `write_gendsp` runs the same gate with `force=`.
    - All 67 committed files round-trip with no removed cord or port change.
    - The full suite is green, the MAX repo and `patches/` are untouched by tests, and there is one commit containing exactly the 2 listed paths.
  </done>
</task>

<task type="auto">
  <name>Task 3: Make the hooks.py module docstring, README and TECHNICAL.md Write Hooks section describe the gate as built, run the final gates, write SUMMARY</name>
  <files>src/maxpat/hooks.py, README.md, TECHNICAL.md</files>
  <read_first>.planning/reviews/2026-10-11-fix-plan.md (line 153), src/maxpat/hooks.py (lines 1-23), README.md (line 178), TECHNICAL.md (lines 460-470)</read_first>
  <action>
    Implement the Q7 "Docs" bullet (rule 8: only these three places).

    1. `src/maxpat/hooks.py` module docstring:
       - Replace the line-3 FRM-05 sentence with an accurate summary of the save gate. It runs in `save_patch_roundtrip` and `write_gendsp`:
         - validate_patch on a deepcopy, plus review_patch, with one cached DB;
         - new-file vs existing-file rules, and the baseline order (`original_text`, HEAD, disk per OQ1);
         - key matching by rule + box ids;
         - the removed-cord SaveGateWarning;
         - the port x-rank refusal;
         - `force=True`.
       - `write_js` validation stays report-only, and `validate_file` is on demand.
       - Add `SaveGateWarning` to the Provides list, and keep the Q5 paragraph.
       - No code changes.
    2. `README.md` line 178: keep the paragraph and append one or two sentences. As a backstop, `save_patch_roundtrip` and `write_gendsp` re-run validation and the critics before writing:
       - they refuse any blocker the save would introduce (pre-existing ones in the file being edited are allowed);
       - they refuse a changed subpatcher port order;
       - they warn about removed cords;
       - `force=True` overrides.

       The sentence must contain the literal `force=True`. Touch no other README line (README:172 is Q5 doc impact, listed in SUMMARY).
    3. `TECHNICAL.md` "### Write Hooks" (lines 460-470):
       - Fix the intro line.
       - Update the table rows:
         - `save_patch_roundtrip(patch_dict, path, original_text=None, *, force=False)`: validate_patch + review_patch gate, cord-removal warning and port x-rank check; Blocks on Error = "New blockers / port reorder (force=True overrides)";
         - `write_gendsp(code, path, ..., *, force=False)`: the same gate;
         - `write_js`: unchanged, report-only.
       - Replace the closing on-demand-validation sentence (line 470) with a short paragraph:
         - the baseline order and new-file rule;
         - matching by rule + box ids (not message text);
         - removed cords vs HEAD warn (SaveGateWarning);
         - port x-rank changes block;
         - findings on the edit path that existed before the save never block, which is why third-party objects in user patches don't reject load-edit-save cycles;
         - `PatchValidationError` attributes (`findings`, `port_changes`, `path`).
       - Touch nothing else in TECHNICAL.md.
    4. Run the final gates (see `<verify>`). Then commit with explicit paths: `git add src/maxpat/hooks.py README.md TECHNICAL.md`, then `git commit -m "docs(save): hooks docstring, README and TECHNICAL describe the automatic save gate (Q7 docs)" -- src/maxpat/hooks.py README.md TECHNICAL.md`.
    5. Write SUMMARY.md (see `<output>`).
  </action>
  <verify>
    <!-- planner-discipline-allow: rather than automatically on every save -->
    <automated>bash -c 'O=$(grep -c "rather than automatically on every save" TECHNICAL.md); [ "$O" = 0 ] || { echo OLD-TECHNICAL-CLAIM-LEFT; exit 1; }; grep -q "PatchValidationError" TECHNICAL.md || { echo TECHNICAL-NO-ERROR; exit 1; }; grep -q "force=True" README.md || { echo README-NO-FORCE; exit 1; }; H=$(sed -n "1,40p" src/maxpat/hooks.py); printf "%s\n" "$H" | grep -q "SaveGateWarning" || { echo DOCSTRING-NO-WARNING; exit 1; }; printf "%s\n" "$H" | grep -q -i "save gate" || { echo DOCSTRING-NO-GATE; exit 1; }; echo DOCS-OK'</automated>
    <automated>bash -c 'python3 -m pytest -q -p no:cacheprovider || exit 1; GS=$(git status --porcelain -- patches/) || { echo GIT-STATUS-FAILED; exit 1; }; W=$(printf "%s\n" "$GS" | grep . | grep -v " patches/.active-project.json$"); [ -z "$W" ] || { echo "PATCH-WORKTREE: $W"; exit 1; }; python3 -c "import ast,sys; [ast.parse(open(f).read(), filename=f, feature_version=(3, 10)) for f in sys.argv[1:]]" src/maxpat/hooks.py src/maxpat/critics/__init__.py src/maxpat/__init__.py tests/test_save_gate.py tests/test_hooks.py || exit 1; echo SUITE-GREEN-PATCHES-UNTOUCHED-PY310'</automated>
    <automated>bash -c 'Q=.planning/quick/261012-qsr-implement-q7-in-planning-reviews-2026-10; B=$(cat "$Q/base-sha.txt") || exit 1; N=$(git rev-list --count --grep="(Q7 " "$B"..HEAD) || exit 1; [ "$N" = 3 ] || { echo "Q7-COMMITS=$N"; exit 1; }; H=$(git log --format=%H --grep="(Q7 " "$B"..HEAD) || { echo GIT-LOG-FAILED; exit 1; }; for h in $H; do F=$(git show --name-only --format= "$h") || exit 1; X=$(printf "%s\n" "$F" | grep . | grep -v -E "^(src/maxpat/(hooks|__init__)[.]py|src/maxpat/critics/__init__[.]py|tests/test_save_gate[.]py|tests/test_hooks[.]py|README[.]md|TECHNICAL[.]md)$"); [ -z "$X" ] || { echo "EXTRA-FILES in $h: $X"; exit 1; }; done; S=$(git stash list) || { echo GIT-STASH-LIST-FAILED; exit 1; }; [ "$S" = "$(cat "$Q/stash-list-before.txt")" ] || { echo STASH-CHANGED; exit 1; }; git log --format="%h %s" --grep="(Q7 " "$B"..HEAD; echo GATES-OK-3-Q7-COMMITS-STASH-UNCHANGED'</automated>
  </verify>
  <done>
    - The hooks.py module docstring, README:178 and the TECHNICAL.md Write Hooks section describe the gate as built, and the old on-demand claim is gone.
    - The full suite is green, nothing under `patches/` changed, and the Python 3.10 gate passes.
    - Exactly 3 `(Q7 ` commits since `base-sha.txt`, each touching only plan files.
    - The stash list is unchanged.
    - SUMMARY.md is written.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Agent output -> user's patch on disk | A generated or edited patch becomes the user's file and is auto-committed; the save is the last point to stop a broken patch. |
| Validator/critic verdicts -> save decision | Checker false positives on user-confirmed patches must not block or alter their saves. |
| Saved path -> git subprocess | Paths reach `git rev-parse` / `git show HEAD:<rel>` as argv. |
| Test suite -> MAX repo and committed patches | Tests must never commit to the MAX repo or write committed patches. |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-qsr-01 | Tampering | `save_patch_roundtrip` / `write_gendsp` write and auto-commit patches with new blockers (A3) | high | mitigate | `_run_save_gate` runs validate_patch(deepcopy) + review_patch before any write. New files refuse every blocker; existing files refuse blockers absent from the baseline. Tests: new file, new fan-out, new proposed-removal cord, multiset second instance. |
| T-qsr-02 | Denial of Service | The gate blocks saves of user-confirmed patches on pre-existing or checker-noise findings | high | mitigate | Baseline diff by rule + box-id key (not text). A round-trip sweep over all 67 committed patches asserts zero new blockers, removed cords and port changes. Pre-existing-blocker save tests cover original_text, HEAD and disk (OQ1). `force=True` escape with a listed warning. |
| T-qsr-03 | Tampering | Cords silently lost between saves (§4.1 class 9) | medium | mitigate | Recursive path-qualified cord diff vs HEAD (and original_text) gives one SaveGateWarning naming each removed cord, with deleted endpoints marked. Tests at top level and nested. |
| T-qsr-04 | Tampering | A subpatcher/abstraction port reorder makes parent cords hit the wrong port (§4.1 class 10) | high | mitigate | The rank of every port present in both versions must be unchanged, or PatchValidationError. Tests: swap, mid-insert, top-level abstraction; rightmost append allowed. |
| T-qsr-05 | Tampering | The gate mutates the caller's dict (A2 regression) or removes cords | medium | mitigate | Only deepcopies reach validate_patch/review_patch, and apply_fixes is never called. A test asserts the dict equals its pre-call deepcopy after a refused save. |
| T-qsr-06 | Repudiation | `force=True` hides what was bypassed | low | mitigate | The SaveGateWarning includes the full refusal message (findings, port changes). |
| T-qsr-07 | Elevation of Privilege | A crafted path is injected into git commands | low | mitigate | `_run_git` passes argv with no shell plus `--literal-pathspecs`. `rel` is computed from resolved paths under the repo root, so a path outside the root raises ValueError, which gives None. |
| T-qsr-08 | Tampering | Gate tests commit to the MAX repo or touch committed patches | high | mitigate | All git runs in tmp repos with git env vars stripped. Committed patches are read and deep-copied only. Each verify asserts the MAX repo HEAD and staged set are unchanged and `patches/` is clean. |
| T-qsr-09 | Denial of Service | Incidental DB/critic warnings escalate under `simplefilter("error")` callers | low | mitigate | Both pipelines run inside catch_warnings + simplefilter("ignore"). The existing `test_save_safety` error-filter saves pass unedited. |
| T-qsr-SC | Tampering | npm/pip/cargo installs | high | mitigate | No package-manager install. Only the standard library and in-repo code are used, so no Package Legitimacy Audit is required. |
</threat_model>

<source_audit>
Sources:
- the fix-plan Q7 section and its rules;
- review finding A3, §4.1 classes 9 and 10, and §4.4 R1;
- the Q1 hand-off (proposed removals on edits are Q7's) and the Q5 hand-off (reuse `force`; Q7 owns the docstring and TECHNICAL claims);
- the orchestrator's notes: sequential main tree, explicit staging, no stash, the caller audit, and matching by rule + box ids.

This quick task has no ROADMAP phase, CONTEXT.md or RESEARCH.md.

| Source item | Covered by | Status |
|---|---|---|
| GOAL: an automatic save gate | Tasks 1-2 | COVERED |
| Checks: save_patch_roundtrip and write_gendsp run validate_patch (deepcopy) + review_patch with one cached DB | Task 1 (S3, S4, S8); Task 2 (write_gendsp) | COVERED |
| Existing files: compare against original_text, else HEAD; raise only for new blockers/errors | Task 1 (S4, S5) | COVERED (plus disk per OQ1) |
| Match by rule + box ids, not finding text | Task 1 (S4 `_finding_key`, TestFindingKey, 67-file sweep) | COVERED |
| force=True bypasses with a warning | Task 1; Task 2 (port force) | COVERED |
| Removed cords: warn vs HEAD | Task 2 (S5-S8, TestCordRemoval) | COVERED (recursive, also exempting changes already in original_text) |
| Port order: block on an x-rank change vs HEAD | Task 2 (S6, TestPortOrder) | COVERED (rank of common ports, subpatchers plus abstraction top level) |
| New files: refuse any blocker | Task 1 | COVERED |
| Test: a new reconverging fan-out raises | Task 1 | COVERED |
| Test: an unchanged patch with pre-existing blockers saves | Task 1 | COVERED (original_text, HEAD, disk) |
| Test: the cord-removal warning fires | Task 2 | COVERED |
| Test: an x-rank swap blocks | Task 2 | COVERED |
| Test: force=True works | Tasks 1-2 | COVERED |
| Docs: hooks.py module docstring, README, TECHNICAL:462 | Task 3 | COVERED (TECHNICAL lines 460-470 live) |
| Audit existing callers of save_patch_roundtrip/write_gendsp (orchestrator) | observed_facts probe; Task 1 step 6-7; SUMMARY | COVERED (1 fixture fix) |
| Q1 hand-off: new proposed removals block on edits | Task 1 (S4) | COVERED |
| R1: stale-file check | Q5 (landed) | EXCLUDED (done) |
| R1: CI pytest job / PostToolUse hook | Q8 | EXCLUDED (other task) |
| R1: fix SKILL.md:317-320; CLAUDE.md Rule #7; shared-capabilities | SUMMARY doc-impact list | EXCLUDED from edits (rule 8; not in the Q7 doc list) |
| Recursive validation/critics inside subpatchers | Q19/Q20 | EXCLUDED (the gate inherits their reach) |
</source_audit>

<verification>
- `python3 -m pytest -q -p no:cacheprovider` is fully green before (expected 2559 passed, 1 xfailed, 1 xpassed, 29 warnings) and after each task. Passes rise only by the new tests, and xfailed/xpassed stay at 1/1. Record the warning count before and after; the gate adds no warning to existing tests.
- After every test run, the MAX repo HEAD and staged set are unchanged by the tests, and `git status --porcelain -- patches/` shows only the pre-existing `.active-project.json`.
- Exactly 3 `(Q7 ` commits since `base-sha.txt`, each touching only plan files. The stash list is unchanged.
- The Python 3.10 syntax gate passes on every changed `.py` file.
</verification>

<success_criteria>
- A3 is fixed: saves validate and review, and refuse blockers they introduce (all blockers for new files).
- R1 is delivered:
  - non-mutating gate;
  - pre-existing findings allowed by rule + box-id key;
  - removed-cord warning vs HEAD;
  - port x-rank refusal;
  - `force=True`;
  - one cached DB.
- No false block on any of the 67 committed patches' round-trips.
- The docs describe the gate. The suite is green, no patch file is touched, and the code is Python 3.10 clean.
</success_criteria>

<output>
Create `.planning/quick/261012-qsr-implement-q7-in-planning-reviews-2026-10/261012-qsr-SUMMARY.md` when done. It must include:
- baseline and final pytest totals, the red counts recorded before each GREEN step, and the pytest warning count before and after;
- how OQ1 was resolved: user answer, or "resolved by default" with the recommended option;
- live line references vs the spec: TECHNICAL Write Hooks 460-470 (spec 462); `save_patch_roundtrip` and `write_gendsp` line ranges before and after;
- the caller audit:
  - 35 gated calls in 8 test files;
  - the one fixture change in `tests/test_hooks.py` and why;
  - confirmation that no src/tools caller exists;
- the 67-file round-trip result (0/0/0), plus the gate's measured cost on terrain-synth (two pipelines on baseline and new, plus two git calls);
- settled decisions worth knowing:
  - new proposed removals block edits (Q1 hand-off);
  - "x-rank" means the rank of common ports, so a mid-insert or mid-delete blocks;
  - changes already in `original_text` are exempt from the cord/port checks;
  - path elements include the box text;
- residuals, all out of scope:
  - validation and critics are top level only, so findings inside subpatchers are not gated until Q19/Q20;
  - a regenerated patch with renumbered ids produces cord-removal warnings;
  - the DB cache is per process;
  - `write_js` stays report-only;
  - the CI job / PostToolUse hook (R1) is Q8;
- doc impact, not edited (rule 8):
  - CLAUDE.md Rule #7 (PatchValidationError / SaveGateWarning / `force` now apply to the gate);
  - `.claude/skills/references/shared-capabilities.md:147`;
  - `.claude/skills/max-lifecycle/references/project-structure.md:80` (now true);
  - `.claude/skills/max-patch-agent/SKILL.md:314-321` (R1's "SKILL.md:317-320": still correct, and the gate is a backstop);
  - `.claude/skills/max-critic/SKILL.md:49`;
  - `README.md:172` (Q5's auto-commit scope);
  - the max-dsp-agent skill's `PatchValidationError(...)` example still works (bare message);
- hand-offs:
  - Q8 (CI runs `tests/test_save_gate.py`; its tmp repos need git);
  - Q19/Q20 (once validation recurses, the gate's key needs a patcher path, because inner ids collide with outer ids);
  - Q36 (`edit_patch` sessions should call `_run_save_gate` through `save_patch_roundtrip`);
  - Q39 (quick-fix payloads can attach to `PatchValidationError.findings`);
- rule 9, "Confirm in MAX": no patch file changed, so nothing is required. Note for the user:
  - a save that would introduce a blocker, or reorder a subpatcher's ports, now raises PatchValidationError; Claude must fix it or ask before using `force=True`;
  - removed cords now print a SaveGateWarning.
</output>
