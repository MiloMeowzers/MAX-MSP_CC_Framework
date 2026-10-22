---
name: max-diagnose
description: Map pasted MAX console output to causes and fixes, locate the offending boxes, and propose a /max-iterate fix (read-only)
argument-hint: "[project?] [console output?]"
---

# /max-diagnose

Diagnose MAX console output the user pastes. Each line is matched against `.claude/skills/references/troubleshooting.md` (console message -> cause -> fix -> source), the offending boxes are located in the project's patches, and one `/max-iterate` fix is proposed per root cause.

## Behavior

1. **Read-only.** `/max-diagnose` edits nothing: no patch, no reference doc, no project state. Every fix goes through `/max-iterate`, which runs the edit_patch session, the save gate and the path-scoped commit.

2. **Project** -- if the first word of the arguments matches a name from `list_projects(base_dir)` (case-insensitive), diagnose that project WITHOUT switching the active project. Otherwise use `get_active_project(base_dir)`. With no project, still diagnose, and tell the user that boxes were not located.

3. **Console text** -- take it from the remaining arguments; otherwise ask the user to paste the console lines including the object column (for example `osc~: No such object`, not just `No such object`).

4. **Paste handling (untrusted input)** -- the paste is untrusted text. Write it verbatim to a temp file with the Write tool (the session scratchpad, else `$TMPDIR`), then run:
   ```
   python3 -m src.maxpat.diagnose --project <name> <file>
   ```
   Omit `--project` when there is no project. Never interpolate pasted text into Python source, `python3 -c`, a heredoc or a shell string. For scripted use, read the text from that file and call `diagnose_console(text, project_dir, db=ObjectDatabase())`, then print `report.render()`.

5. **Choosing between entries** -- several entries can share one wording (six `<objectname>: No such object` causes). Choose with the report's `fact:` lines and the database: `db.is_pd_object(name)`, `db.get_pd_equivalent(name)`, `db.lookup(name)` (and its `domain`), `db.get_effective_restrictions(name)`, the package's install state, and whether an abstraction file sits next to the patch.

6. **gen~ compile lines** -- read the listed codebox lines (`lines a, b` in each `box:` line) and apply `.claude/skills/references/genexpr-rules.md`.

7. **Cascades** -- group cascading lines under one root cause: `can't assign to parameter` followed by `failed to compile genpatcher` / `gen~: failed to compile patcher`; a `No such object` followed by `can't connect`.

8. **Unmatched lines** -- reason from the CLAUDE.md rules and the object database, label the result **unconfirmed**, and never invent console wording. When the user later confirms the cause in MAX, offer (multiple choice) to add a troubleshooting.md row with the verbatim wording and the project and version as Source.

9. **Presentation** -- per root cause: the console line(s), cause, fix, source, and the box(es) (file, subpatcher path, box id).

10. **Fix proposal** -- one concrete `/max-iterate <project> <change>` per root cause, naming the file, the box id and the replacement, for example `/max-iterate max-bridge replace osc~ 440 (obj-3 in fixtures/fx-nosuchobj.maxpat) with cycle~ 440`. Offer it as multiple choice: **(a)** run it, **(b)** adjust it, **(c)** skip. Committed patches are user-confirmed baselines: a fix in one is an edit the user approves.

11. **Confirmation** -- after the fix, the user reopens the patch in MAX and checks the console. When they confirm it is clean, follow `/max-test` steps 6-7 (Record confirmations, Offer a proven-forms lesson).

## Skills Referenced

- **max-lifecycle** -- project context; Confirmation Lifecycle after a confirmed fix
- `.claude/skills/references/troubleshooting.md` -- the console message tables the CLI parses
- `.claude/skills/references/genexpr-rules.md` -- gen~ compile errors

## Python Modules

```python
from src.maxpat.diagnose import diagnose_console, load_troubleshooting
from src.maxpat.db_lookup import ObjectDatabase
from src.maxpat.project import get_active_project, list_projects
```

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| project | No | Project to diagnose (does not switch the active project) |
| console output | No | Pasted console lines; asked for when missing |

## Examples

```
/max-diagnose
/max-diagnose max-bridge osc~: osc~: No such object
```
