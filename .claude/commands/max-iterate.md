---
name: max-iterate
description: Modify existing patches or code in the active project
argument-hint: "[--full|--discuss|--research|--plan|--fix] [changes]"
---

# /max-iterate

Apply modifications to existing .maxpat patches using the analyze-first protocol. Reads the patch, shows a structural analysis, then makes surgical or section-level edits while preserving all existing objects and user positioning.

## Behavior

1. **Parse arguments for inline project switch** -- before loading the active project, check if the first word of the argument string matches an existing project:
   ```python
   from src.maxpat.project import get_active_project, set_active_project, list_projects, update_status, bump_version

   projects = list_projects(base_dir)
   args = user_input.strip()
   first_word = args.split()[0] if args else ""

   # Case-insensitive match against known project directories
   matched_project = None
   for p in projects:
       if p.lower() == first_word.lower():
           matched_project = p
           break

   if matched_project:
       set_active_project(matched_project, base_dir)
       change_description = " ".join(args.split()[1:])  # remaining text
   else:
       change_description = args  # entire string is the description
   ```

2. **Parse flags** -- extract workflow flags from the argument string before interpreting the change description:
   - Scan `change_description` (the text remaining after inline project switch parsing) for `--full`, `--discuss`, `--research`, `--plan` and `--fix`
   - `--full` expands to all three: discuss + research + plan
   - `--discuss`, `--research`, `--plan` can be used individually or combined
   - `--fix` switches to Quick-fix mode (see "Quick-fix mode (`--fix`)" below) instead of steps 6-18
   - Strip all recognized flags from `change_description` so downstream steps see only the modification text
   - Store flags as booleans: `do_discuss`, `do_research`, `do_plan`, `do_fix`

3. **Load active project** -- read `patches/.active-project.json` for the current project (which may have just been set by the step above). If no active project, prompt the user.

4. **Auto-detect target .maxpat** -- determine which patch file to edit:
   - Single .maxpat in `generated/`: use it automatically
   - Multiple .maxpat files: infer from the user's change description (match keywords to filenames)
   - Ambiguous: ask the user which file to edit

5. **Load patch for analysis** -- load the target file using read_patch:
   ```python
   patcher, original_text = read_patch(path)
   ```
   This read is for analysis and discussion only. The edit itself happens later in one `edit_patch(path)` session (step 14), which re-reads the file on entry, so a MAX save in between is picked up rather than overwritten.

6. **Analyze patch** (mandatory before any edits) -- run structural analysis and display it to the user:
   ```python
   summary = patcher.analyze()
   ```
   The analysis shows: complexity metrics, object inventory by domain, functional sections, signal chain trees, control flow origins, subpatcher hierarchy, and parameters. This gives agent and user shared context before discussing changes.

7. **Discuss phase** (only if `do_discuss` is true) -- engage in a structured discussion about the requested changes, following the same protocol as `/max-discuss`:
   - Present the patch analysis alongside the change request
   - Ask clarifying questions about implementation approach: which objects to use, signal flow strategy, how the change integrates with existing patch structure
   - Capture decisions and rationale
   - Append decisions to the project's `context.md` under a "Decisions" section
   - This phase is interactive -- wait for user responses before proceeding

8. **Research phase** (only if `do_research` is true) -- investigate MAX-specific approaches for the requested changes, following the same protocol as `/max-research`:
   - Read relevant object database domains from `.claude/max-objects/`
   - Check `relationships.json` for common object pairings relevant to the change
   - Identify candidate objects, signal flow patterns, and alternative approaches
   - Present findings with tradeoffs
   - Append research results to the project's `context.md` under a "Research" section

9. **Plan phase** (only if `do_plan` is true) -- create an explicit plan for the modifications before executing:
   - Based on the analysis, discussion decisions, and research findings, outline the specific edit steps
   - List which objects will be added, modified, or removed
   - Specify the edit strategy (surgical vs section rebuild) with rationale
   - Identify connection changes and signal flow impacts
   - Present the plan to the user and wait for approval before proceeding to execution

After all flagged phases complete, proceed to the standard edit flow (steps 10+). The edit flow now benefits from decisions captured in context.md and any research/plan context.

10. **Parse change request** -- interpret the user's desired modifications against the analysis context. Identify which objects, sections, or signal chains are affected.

11. **Choose edit strategy** (transparent to user) -- the agent selects an approach and explains it before executing:
    - **Surgical edit** -- for small, targeted changes: use `find_box()` to locate targets, then `modify_box()` or `replace_box_safe()` to make changes in place. Positions are preserved; `replace_box_safe()` keeps the box id and rewires every cord whose outlet/inlet index still exists on the new box -- rewire whatever comes back in `result.orphaned` (Rule #8).
    - **Section rebuild** -- for larger structural changes: use `connected_components()` to identify the affected group, `remove_box()` each object in the group, then rebuild with new objects and connections. Reconnect to the rest of the patch.

12. **Preserve existing objects** -- unconditionally preserve all objects the user did not ask to change. If the requested edit would affect objects the user added manually in MAX (e.g., removing an object that user-added objects connect to), warn before proceeding.

13. **Route through max-router** -- invoke the max-router skill for specialist dispatch with:
    - The modification description
    - The analysis summary as context
    - Project context

14. **Execute edits inside one edit_patch session** -- the specialist agent applies changes via Patcher API methods inside a single `with` block; steps 15-17 run inside the same block, and leaving it is the save (step 18):
    ```python
    from src.maxpat import edit_patch, validate_patch
    from src.maxpat.critics import review_patch
    from src.maxpat.project import bump_version, update_version_comment

    session = edit_patch(path)
    with session as patcher:
        box = patcher.find_box(name="cycle~")        # find / modify / replace / insert / remove
        patcher.modify_box(box, args=["220"])
        results = validate_patch(patcher)            # step 15
        review = review_patch(patcher.to_dict())     # step 15 (blockers: raise here to discard)
        new_version = bump_version(project_dir, "patch", description, files_changed=[path.name])  # step 16
        update_version_comment(patcher, new_version)  # step 17
    print(session.diff.render())                     # step 18: show the user what changed
    ```
    Run the whole block in ONE Python script: a `with` block cannot span separate tool calls. API inside the block:
    - `find_box()` / `find_boxes()` for locating targets
    - `modify_box()` for in-place attribute changes: `args` sets the text of a newobj, message, comment or text UI box (textbutton, live.text, live.comment, textedit) and raises on any other UI box -- set a dial's range, a toggle's colour etc. with `extra_attrs`; structural `extra_attrs` keys (`id`, `maxclass`, `numinlets`, `numoutlets`, `outlettype`, `patcher`) raise
    - `replace_box_safe()` for swapping object types (keeps the box id; rewires every cord whose index is still in range on the new box and returns the rest in `result.orphaned`, Rule #8; replacing a box with an embedded patcher works only for the same name or `gen~` <-> `mc.gen~`, anything else raises `ValueError`)
    - `insert_into_connection(src, dst, name, args)` for inserting objects into existing signal chains
    - `remove_box()` for removing objects (with automatic patchline cleanup)
    - `add_box()` / `add_connection()` for adding new objects

15. **Critic loop** -- validate and review the modified patch:
    - Run `validate_patch(patcher)` for structural validation
    - Run `review_patch(patcher.to_dict())` via the max-critic skill (the default `is_new=False` is right for an edit; pass `is_new=True` when the iteration creates a new file, e.g. a new abstraction, because the gate reviews a file with no baseline that way)
    - Same quality gate as `/max-build` -- blockers require revision; warnings and notes are listed in the summary, never written into the patch or code
    - On blockers, raise inside the `with` block to discard the edit (nothing is routed, written or committed), then fix and re-run the session

16. **Bump version** -- call `bump_version(project_dir, "patch", description, files_changed=[path.name])` where `description` is a short summary of the change. Use `"minor"` for significant reworks, `"major"` for breaking changes. Store the returned version string for the next step.

17. **Embed version comment** -- call `update_version_comment(patcher, new_version)` to add or update the version comment box in the patch. This MUST happen after bump (to get the new string) and before save (so the comment is in the saved file). The version comment is a visible `v0.1.0`-style comment placed in the top-right of the patch. Agents MUST NOT skip this step.

18. **Save = leaving the with-block** -- a clean exit from `with session as patcher:` saves:
    - routes touched cords only (new cords, and cords of boxes added or moved, that have no midpoints; existing midpoints are never cleared);
    - sets text contrast only on boxes the session added that carry an explicit textcolor (moved, presentation-changed and replaced boxes keep their colour, a comment without a textcolor is never given one, and there is no whole-patch restyle);
    - runs the save gate, including the stale check, and writes atomically through `save_patch_roundtrip` in the file's own JSON layout (indentation, key ordering and untracked metadata preserved);
    - commits only that path (`session.commit_hash`). A no-op session writes and commits nothing (`session.saved` is False).

    Show `session.diff.render()` to the user as "what changed".
    - `StaleFileError`: MAX saved the file in the meantime -- re-run the session (it re-reads the file).
    - `PatchValidationError`: fix the findings and re-run. `versions.json` was already bumped in step 16, so reuse the stored `new_version` and do not bump twice.
    - `edit_patch(path, force=True)` bypasses the gate -- only with user confirmation (CLAUDE.md Rule #7).

19. **Commit to git** -- the session already committed the .maxpat; also explicitly commit the version bump (`versions.json`) and any other changed files:
    ```python
    from src.maxpat.project import auto_commit_patch
    auto_commit_patch(project_dir, base_dir, description=f"v{new_version}: {change_description}", files=[str(path), str(project_dir / "versions.json")])
    ```
    Called directly, `auto_commit_patch()` raises `RuntimeError` on any git failure (not a repository, ignored path, index.lock): report it to the user; the files are saved but not committed.

20. **Update progress** -- increment progress via `update_status()`.

## Quick-fix mode (`--fix`)

Some critic findings carry a machine-applicable fix (`CriticResult.fix`, fix-plan Q39): a correctly ordered `t ...` for a reconverging fan-out, `@param $1` -> `param $1` for a gen~ message, a `scale <lo> <hi> 0. 1.` / `clip 0. 1.` before an unsafe gain input, and `@out t` on a bach object feeding plain MAX objects. With `--fix`, run steps 1 and 3-5; any remaining text only picks the target patch. Then:

a. **List** the fixable findings:
   ```python
   from src.maxpat import read_patch, fixable_findings

   patcher, original_text = read_patch(path)
   candidates = fixable_findings(patcher)
   for i, r in enumerate(candidates, 1):
       print(f"{i}. [{r.severity}] {r.finding}\n   fix: {r.fix.description}")
   ```
   If there are none, say so and stop; other findings go through a normal `/max-iterate`.

b. **Ask** the user to choose, in multiple-choice form: (A) all, (B) blockers only, (C) pick numbers, (D) cancel. `selected` is the chosen CriticResults (or their `finding_key(r)` tuples).

c. **Preview** the semantic diff (a separate read; nothing is written or committed), then ask: (A) apply, (B) cancel:
   ```python
   from src.maxpat import preview_quick_fixes

   print(preview_quick_fixes(path, selected).render())
   ```

d. **Apply** in ONE Python script and ONE `edit_patch` session, fixes first, then the version bump and comment:
   ```python
   from src.maxpat import edit_patch, apply_quick_fixes
   from src.maxpat.project import bump_version, update_version_comment

   session = edit_patch(path)
   with session as patcher:
       applied = apply_quick_fixes(patcher, selected)
       new_version = bump_version(project_dir, "patch", description, files_changed=[path.name])
       update_version_comment(patcher, new_version)
   print(session.diff.render())
   ```
   `apply_quick_fixes` re-reviews the session's fresh read before each selected finding and applies the payload found there.

e. **`FixError`** means the patch changed since the preview (a MAX save) or a payload no longer fits. Nothing was written: re-run `/max-iterate --fix`.

f. **Expect a `SaveGateWarning`** naming each cord a fix rerouted through the inserted box (removed cords are reported by the save gate). `StaleFileError` and `PatchValidationError` are handled as in step 18. The save gate is never bypassed in this mode: never pass `force` to `edit_patch` here.

g. Continue with steps 19-20.

## Skills Referenced

- **max-router** -- domain detection and agent dispatch
- **max-critic** -- post-modification quality review
- **max-lifecycle** -- project context and status updates

## Python Modules

```python
from src.maxpat import edit_patch, read_patch, save_patch_roundtrip, validate_patch, Patcher
from src.maxpat.project import get_active_project, set_active_project, list_projects, update_status, bump_version, update_version_comment, auto_commit_patch
from src.maxpat.critics import review_patch, CriticResult
from src.maxpat import fixable_findings, preview_quick_fixes, apply_quick_fixes, finding_key, FixError
```

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| changes | Yes | Optional project name prefix followed by description of modifications (e.g., "stutter add LFO to filter cutoff") |

## Flags

| Flag | Description |
|------|-------------|
| --full | Run full pipeline: discuss -> research -> plan -> build (requires interactive mode) |
| --discuss | Run discuss phase only before build (requires interactive mode) |
| --research | Run research phase only before build |
| --plan | Run plan phase only before build (requires interactive mode) |
| --fix | Quick-fix mode: list the critic findings that carry a fix, preview the semantic diff, apply the selected fixes through one `edit_patch` session (requires interactive mode) |

Flags are composable: `--discuss --research` runs both phases. `--full` is shorthand for `--discuss --research --plan`.

Flags are stripped from the change description before processing.

**Note:** `--full`, `--discuss`, and `--plan` require interactive mode because the discuss and plan phases wait for user input. `--research` can run non-interactively.

## Examples

```
/max-iterate add LFO to filter cutoff
/max-iterate change metro rate to 200ms
/max-iterate replace cycle~ with saw~ for the main oscillator
/max-iterate add preset save/recall to the UI

# Inline project switching (first word matches a project name):
/max-iterate stutter add LFO to filter cutoff     # switches to stutter, then iterates
/max-iterate FDNVerb increase diffusion            # switches to FDNVerb, then iterates

# Full pipeline (requires interactive mode -- discuss and plan wait for user input):
/max-iterate --full add granular synthesis engine
/max-iterate stutter --full redesign the delay feedback path

# Individual flags:
/max-iterate --discuss add LFO to filter cutoff
/max-iterate --research replace cycle~ with wavetable oscillator
/max-iterate --discuss --research add sidechain compression

# Quick-fix mode (preview, then apply the selected critic fixes):
/max-iterate --fix
/max-iterate stutter --fix
```
