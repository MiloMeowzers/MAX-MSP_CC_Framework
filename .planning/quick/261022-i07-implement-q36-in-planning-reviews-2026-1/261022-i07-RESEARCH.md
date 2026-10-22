# Quick 261022-i07: Q36 edit_patch session API + semantic patch diff - Research

**Researched:** 2026-10-22
**Domain:** in-repo Python (`src/maxpat`): save path, change tracking, diff
**Confidence:** HIGH (every claim below comes from reading code or running a probe this session)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Gate / stale refusal on exit:** raise and write nothing. `PatchValidationError` / `StaleFileError` propagate out of the with-block; the file is untouched and nothing is committed. The edited Patcher stays inspectable through the session/context object.
- An exception raised inside the with-block body also writes nothing (discard).
- **Exit scope:** route touched cords only (added/moved boxes, using the existing `_box_added_or_moved` / midpoint logic in hooks.py) and run `repair_text_contrast(patcher)`. No global auto-layout, no full finalize.
- Then reuse the `save_patch_roundtrip(..., original_text)` primitives (stale check, `_run_save_gate`, `format_patch_text`, atomic write, path-scoped auto-commit). Do not duplicate them.
- **Diff identity:** match boxes by box id. "moved" = any patching_rect x/y change (delta > 0). A size change is reported separately. `presentation` flag and `presentation_rect` changes are reported as presentation changes.
- **Recursion:** the diff recurses into embedded subpatchers / bpatcher embeds, path-prefixed (e.g. `p foo/obj-12 ...`), with the same id matching at each level.
- A no-op `edit_patch` session must be byte-identical, with no write and no commit (the Q29 guarantee).
- `force=True` is passed through only when the user confirms (CLAUDE.md Rule #7).

### Claude's Discretion
- The return value / session object shape (e.g. expose the commit hash, diff and orphaned cords after exit).
- The diff data structure and text renderer format (keep it compact).

### Deferred Ideas (OUT OF SCOPE)
- None listed. From the fix plan: Q39 (`/max-iterate --fix`, critic fix payloads) builds on this task and is NOT part of it.
</user_constraints>

## Summary

All four gate checks Q36 lists already exist inside `save_patch_roundtrip` → `_run_save_gate`. `edit_patch` is a thin session around `read_patch` + touched-cord routing + one `save_patch_roundtrip(new_dict, path, original_text, force=force)` call, with a no-op short-circuit in front of it. `save_patch_roundtrip` would still write (and then warn "no changes to commit") on a no-op, so the short-circuit is required. Only one Q36 property is missing today: **the write is not atomic.** `_write_and_sync` does `open(path, "w")`, while `src/maxpat/atomic_io.py` already provides `atomic_write_bytes`.

**Blocking conflict between two CONTEXT decisions. The planner must resolve it before tasks are written.** I ran `repair_text_contrast` on in-memory copies of all 63 committed `.maxpat` files (HEAD). It changes **33 of them: 268 boxes get a missing `textcolor` filled and 42 explicit ones change.** Running it on every exit therefore breaks the "no-op session is byte-identical / no write / no commit" decision. It also contradicts locked aesthetic decision D-4 ("deliberately NOT wired into any automatic path", `aesthetics.py:660-664`) and the user's feedback memory ("don't run `repair_text_contrast` … on an existing, user-approved patch"). **Recommended:** run contrast on exit **only for boxes the session touched** (added, moved, or presentation changed), never on the whole patcher (see Pattern 3).

`populate_assistance_comments()` (part of `finalize_patch(is_new=False)`) also changes 9 of the 63 committed patches on a no-op. Do not call it on exit; CONTEXT already excludes "full finalize". Touched-only midpoint routing changed 0 of 63 on a no-op, so it is safe to run unconditionally.

**Primary recommendation:** create a new module `src/maxpat/edit_session.py` (class `EditSession`; `edit_patch(path, *, force=False)` returns one) and a new pure-dict diff module `src/maxpat/patch_diff.py` (`diff_patch_dicts(old, new) -> PatchDiff`), with `Patcher.diff(other)` as a lazy-import wrapper. Make `_write_and_sync` atomic via `atomic_write_bytes`.

## Architectural Responsibility Map

| Capability | Owner | Rationale |
|---|---|---|
| Session lifecycle (read, yield, exit) | new `src/maxpat/edit_session.py` | Composes hooks/layout/aesthetics/patch_diff; keeps hooks.py (1409 lines) focused on saving |
| Stale, gate, format, write, commit | `hooks.save_patch_roundtrip` (unchanged API) | CONTEXT: reuse, do not duplicate |
| Atomic write | `hooks._write_and_sync` → `atomic_io.atomic_write_bytes` | Single choke point for all three writers |
| Touched-cord routing | `hooks._finalize_midpoints_recursive(p, layout._generate_midpoints)` | Already touched-only and recursive |
| Semantic diff | new `src/maxpat/patch_diff.py` (pure dict functions) | Works on `git show` text without building a Patcher; `Patcher.diff` wraps it |

## Existing primitives (verified by Read this session)

| Primitive | Location | What edit_patch uses it for |
|---|---|---|
| `read_patch(path) -> (Patcher, original_text)` | `hooks.py:393-425` | Enter: load. Uses `path.read_text()` and `SCOPE_BY_SUFFIX` domain context |
| `save_patch_roundtrip(patch_dict, path, original_text=None, *, force=False) -> str \| None` | `hooks.py:305-390` | Exit: the stale check runs first (`368-378`: `if path.read_text() != original_text: raise StaleFileError(path)`), then `_run_save_gate` (`381`), `format_patch_text` (`384`), mkdir + `_write_and_sync` (`386-387`), and `_auto_commit_saved_file` (`390`) |
| `_run_save_gate(patch_dict, path, original_text, *, force)` | `hooks.py:816-908` | Called by save_patch_roundtrip. New blockers by multiset key (`_gate_report`, `778-789`); removed cords → one `SaveGateWarning` (`863-881`, a warning whatever `force` is); port x-rank changes (`799-811`) → `PatchValidationError` (`903-908`). **All four Q36 checks are covered: stale, new-blocker, cord-removal, x-rank.** |
| `format_patch_text(patch_dict, original_text=None)` | `hooks.py:265-302` | No-op detection: `format_patch_text(p.to_dict(), original_text) == original_text` |
| `_write_and_sync(path, content)` | `hooks.py:137-142` | Non-atomic `open(path, "w")` + fsync. Needs to change (see Pitfall 4) |
| `_auto_commit_saved_file(path) -> str \| None` | `hooks.py:62-134` | Path-scoped commit under `patches/<project>/`; never raises; warns on every None |
| `_box_added_or_moved(box)` | `hooks.py:192-207` | `box._raw is None` → added; `_loaded_rect is None` → added; x or y differs from `_loaded_rect` → moved. A resize is not a move |
| `_finalize_midpoints_recursive(patcher, generate_fn)` | `hooks.py:210-241` | Eligible cord = `line._raw is None` or touches a touched box; `_generate_midpoints` skips cords that already have midpoints; recurses into `box._inner_patcher` |
| `_generate_midpoints(patcher, *, eligible=None)` | `layout.py:1519` | Pass as `generate_fn` |
| `StaleFileError(path)` / `PatchValidationError(message, *, path, findings, port_changes)` / `SaveGateWarning` | `hooks.py:463-480`, `432-460`, `519-524` | Propagate unchanged |
| `atomic_write_bytes(path, payload: bytes)` | `atomic_io.py:73-85` | Temp file in the target's dir, fsync, keeps mode, `os.replace`; cleans up on failure. Stdlib-only module, so no import cycle |
| `_apply_text_contrast(patcher) -> int` | `aesthetics.py:572-613` | Iterates **top-level `patcher.boxes` only** (no recursion); writes via `_set_textcolor` |
| `repair_text_contrast(patcher) -> int` | `aesthetics.py:657-676` | = `_apply_text_contrast(patcher)`; docstring locks D-4 "Opt-in only" |

### How change tracking works today (`patcher.py`)
- `Patcher.from_dict` deep-copies its input (`1991-1993`), and `_from_owned_dict` (`1995-2156`) builds each Box via `Box.__new__`. Fields: `id`, `maxclass`, `text`, `numinlets`, `numoutlets`, `outlettype`, `patching_rect`, `fontname`, `fontsize` (`2059-2067`). It derives `name`/`args` from `text` for `newobj` only; UI boxes get `args = []` (`2070-2079`). It also sets `presentation` (bool) and `presentation_rect` (list or None) (`2082-2084`), plus `extra_attrs` = every key not in `_BOX_HANDLED_KEYS` (`2104-2106`).
- `_BOX_HANDLED_KEYS` (`patcher.py:42-47`): `"id", "maxclass", "text", "numinlets", "numoutlets", "outlettype", "patching_rect", "fontname", "fontsize", "presentation", "presentation_rect", "patcher", "saved_object_attributes"`.
- Snapshots: `box._loaded = {"fontname", "fontsize", "extra_attrs" (deepcopy)}` (`2109-2113`), `box._raw = dict(box_data)` with `raw["patcher"] = None` as a key-order sentinel (`2117-2120`), and `box._loaded_rect = tuple(box.patching_rect)` (`2123`). Lines: `Patchline._raw = dict(line_data)` plus a `_loaded` snapshot of `order/hidden/midpoints/color/extra_attrs` (`122-134`).
- **There is no presentation snapshot** on Box, so "presentation changed" has to come from the diff against the baseline dict (see Pattern 3).
- An embedded patcher is `box._inner_patcher` (`2093-2101`), serialized back under `"patcher"` (`Box.to_dict` `508-513`).
- **bpatchers:** all 42 bpatchers in committed patches are external (`"name": "<file>.maxpat"`, no `"patcher"` key), and there are 0 embedded ones (probe over `git ls-files 'patches/**/*.maxpat'`). Recurse only when the box dict has a `"patcher"` dict. An external bpatcher's `name`/`args` show up as attribute changes. gen~ / rnbo~ / `p` boxes all carry `"patcher"`, so a codebox edit appears as the attribute `code` changing on the inner codebox.

## Patterns

### Pattern 1: `EditSession` (class-based context manager, not `@contextmanager`)
A class gives an object that survives the with-block: inspectable after a refusal, and it carries `commit_hash`, `diff` and `saved`. `__enter__` returns the **Patcher**, so `with edit_patch(path) as p:` matches the Q36 spec literally.

```python
# src/maxpat/edit_session.py  (sketch; names are recommendations)
class EditSession:
    def __init__(self, path, *, force=False):
        self.path = Path(path); self.force = force
        self.patcher = None; self.original_text = None
        self.saved = False; self.commit_hash = None; self.diff = None
    def __enter__(self):
        self.patcher, self.original_text = read_patch(self.path)   # re-read on every enter
        return self.patcher
    def current_diff(self):            # callable mid-block (Q39 preview)
        return diff_patch_dicts(json.loads(self.original_text), self.patcher.to_dict())
    def __exit__(self, exc_type, exc, tb):
        if exc_type is not None:
            return False               # discard: no route, no write, no commit; exception propagates
        p = self.patcher
        _finalize_midpoints_recursive(p, layout._generate_midpoints)   # touched cords only
        _contrast_touched(p, baseline_dict)                            # Pattern 3 (pending decision)
        new_dict = p.to_dict()
        self.diff = diff_patch_dicts(baseline_dict, new_dict)          # before save: survives a refusal
        if format_patch_text(new_dict, self.original_text) == self.original_text:
            return False               # no-op: no stale check, no gate, no write, no commit
        self.commit_hash = save_patch_roundtrip(new_dict, self.path, self.original_text, force=self.force)
        self.saved = True
        return False

def edit_patch(path, *, force=False) -> EditSession:
    return EditSession(path, force=force)
```
Usage: `s = edit_patch(path)`, then `with s as p: ...`, then read `s.commit_hash` / `print(s.diff.render())`. The one-liner `with edit_patch(path) as p:` also works when the result isn't needed.

### Pattern 2: `patch_diff.py`: a pure dict diff, keyed by id per level
- `diff_patch_dicts(old: dict, new: dict) -> PatchDiff` takes full `{"patcher": {...}}` dicts. `Patcher.diff(self, other)` = `diff_patch_dicts(self.to_dict(), other.to_dict())` (**`a.diff(b)` = the changes from a to b**, as in `git diff A B`). Put the import inside the method body, because patcher.py must not import the new module at top level (cycle-safe).
- Walk levels with your own recursion keyed by a **tuple of box ids only**. Do NOT reuse `hooks._iter_patchers` (`657-677`): its path element is `(id, text)`, so renaming `p foo` → `p bar` would make every inner box show as removed and re-added. Use the box text only for the rendered label (`p foo/obj-12`). Disambiguate with the id only when two siblings share a text.
- Per box id at each level: added / removed; `moved` (x or y differs); `resized` (w or h differs); `text` (old → new; `args` is derived from text, so don't report it separately); `attrs` (a sorted list of changed keys outside the handled set, plus fontname/fontsize, so `textcolor` from contrast repair shows up); `presentation` (flag and/or rect). Recurse when both sides have a `"patcher"` dict. When only one side has one, report "subpatcher added/removed (N boxes)".
- Cords: a set of `(src_id, outlet, dst_id, inlet)` per level → added / removed. Optionally a `rerouted` count (midpoints differ) to show the touched-cord routing at work.
- `PatchDiff`: a dataclass of lists plus `__bool__` (any change) and `render(max_lines=40) -> str`. Suggested compact lines: `+ obj-31 [*~ 0.5] @120,340`, `- obj-7 [cycle~ 440]`, `~ obj-12 moved 40,200 -> 40,260`, `~ obj-12 text "a" -> "b"`, `~ obj-12 attrs textcolor`, `~ obj-15 presentation off -> on [10,10,60,22]`, `+ cord obj-31:0 -> obj-4:0`, with nested lines prefixed `p voice/` and a final summary line of counts.

### Pattern 3: touched-only contrast (recommended resolution of the conflict)
- Touched set at the top level = boxes the diff reports as added, moved, or presentation-changed. `_apply_text_contrast` is top-level only, so compute the diff (or at least its top-level box section) before contrast, then contrast, then compute the final diff.
- Implementation: add a private keyword to `_apply_text_contrast(patcher, *, only_ids=None)` that skips boxes whose id is not in `only_ids`. The public `ensure_text_contrast` / `repair_text_contrast` signatures stay unchanged, so `test_doc_signatures` is unaffected. Alternative: snapshot `textcolor` of untouched boxes, call `repair_text_contrast`, then restore. Uglier, but it touches no shared code.
- With the touched set empty on a no-op, the no-op guarantee holds.

### Anti-patterns
- Calling `finalize_patch(p, is_new=False)` on exit: `populate_assistance_comments` dirties 9 of 63 committed patches on a no-op.
- Calling `save_patch_roundtrip` on a no-op: it writes identical bytes (mtime changes, MAX may see a change) and warns "no changes to commit".
- Running `apply_layout` / `ensure_text_contrast` / whole-patch `repair_text_contrast` on exit.
- Mutating the dict passed to the gate: the gate already deep-copies (`hooks.py:613-614`); keep the session's `new_dict` read-only after the no-op check.

## Don't Hand-Roll

| Problem | Use instead |
|---|---|
| Stale check / gate / layout-preserving text / commit | `save_patch_roundtrip(new_dict, path, original_text, force=force)` |
| Atomic temp + replace + mode preservation | `atomic_io.atomic_write_bytes` |
| Cord routing for touched boxes | `_finalize_midpoints_recursive` + `layout._generate_midpoints` |
| Port x-rank / removed-cord detection | Already in `_gate_report`; don't re-implement it in the diff (the diff reports cords removed for display only) |
| Throwaway git repo for tests | Copy the `_repo(tmp_path)` helper from `tests/test_save_safety.py:59-70` (init, user config, `commit.gpgsign false`, empty `core.hooksPath`) |

## Common Pitfalls

1. **No-op guarantee (Q29).** Compare `format_patch_text(p.to_dict(), original_text) == original_text` *before* calling save. Probe: 63/63 committed patches round-trip byte-identically, and touched-only midpoints change 0/63. Whole-patch contrast (33/63) and assistance comments (9/63) do change them. Test: parametrize over every committed `.maxpat` copied to `tmp_path`, run an empty session, then assert the bytes are unchanged, `_write_and_sync` was never called, and `s.saved is False`.
2. **Exceptions in the body.** `__exit__` must return `False` before any routing or writing when `exc_type` is set. That covers `KeyboardInterrupt` too (it is a `BaseException`, but `exc_type` is still set).
3. **StaleFileError / PatchValidationError on exit** come from inside `save_patch_roundtrip`, before any write (`368-381`). Set `self.diff` before calling save so the caller can still inspect `s.patcher` and `s.diff` after the raise. Don't catch these errors.
4. **Atomic write is a cross-writer change.** Changing `_write_and_sync`'s body to `atomic_write_bytes(path, content.encode("utf-8"))` makes `write_gendsp` / `write_js` atomic too, which needs a line in SUMMARY.md. Existing tests survive: `tests/test_hooks.py:320-328` patches `src.maxpat.hooks.os.fsync`, which is the global `os.fsync` that `atomic_io._write_temp` calls once; the `_write_and_sync` mock tests (`330-363`) are unaffected. `os.replace` gives the file a new inode and drops macOS xattrs. That is harmless for MAX and git. There are no symlinks under `patches/` (checked with `find patches -type l`), but resolve the path first anyway so a future symlink isn't replaced by a regular file.
5. **Re-entrancy.** Two overlapping sessions on one file: the second exit raises `StaleFileError`, which is the desired behaviour. Re-entering the same `EditSession` object must re-read in `__enter__` (CLAUDE.md Rule #7: re-read after every save). Also guard against nested entry of the same object (`RuntimeError` if `_active`).
6. **The diff keyed by `(id, text)`** breaks on a subpatcher rename. Key by id only (Pattern 2).
7. **The cord-removal warning is not a refusal.** `SaveGateWarning` is emitted even when the save succeeds. Let it propagate; the session diff also lists the removed cords.
8. **`/max-iterate` version bump order.** `bump_version` writes `versions.json` immediately (step 16). If the gate then refuses on exit, versions.json is already bumped. Keep the existing step 19 explicit `auto_commit_patch(..., files=[path, versions.json])`; the `.maxpat` itself is already committed by the session. Flag this in the doc text; don't change bump_version.
9. **Python 3.10.** The local interpreter is 3.14.2. Avoid 3.11+ features (`typing.Self`, `ExceptionGroup`, `tomllib`); keep `from __future__ import annotations`.

## Exports and naming
- No collisions: `grep` found no `edit_patch`, `EditSession`, `PatchDiff`, `patch_diff` or `def diff` in `src/` (only `tools/help_io.py:577 diff_baselines`, which is unrelated).
- Add `from src.maxpat.edit_session import edit_patch, EditSession` and `from src.maxpat.patch_diff import PatchDiff, diff_patch_dicts` to `src/maxpat/__init__.py` (hooks import at `31-45`) and to `__all__` (`84-150`, "File I/O" group).
- `tests/test_doc_signatures.py` binds every doc call form against `inspect.signature` over the names in `src.maxpat` (`_INDEX_MODULES` `56-65`) and Patcher methods (receivers `p`, `patcher`, …). New doc snippets (`edit_patch(path)`, `p.diff(other)`, `s.diff.render()`) must match the real signatures. `s` is not a known receiver, so `s.*` calls are skipped.

## Docs to update (Q36 scope only)
- `.claude/commands/max-iterate.md`: step 5 (`49-54` read_patch), step 18 (`115-118` save_patch_roundtrip), step 19 (`120-126`, which stays but is now only for versions.json), the Python Modules block (`134-140`). Recipe: `s = edit_patch(path)`, then `with s as patcher:` steps 6-17, then show `s.diff.render()` to the user. Note that step 16's bump happens inside the block.
- `.claude/skills/references/shared-capabilities.md`: "Editing Functions" (`229-240`), "Edit Workflow" (`242-249`), "Output Protocol (Edited Patches)" (`251-258`), and the Patch Safety paragraph (`271`). Replace the read/finalize/save sequence with the session form. Keep `finalize_patch(is_new=False)` documented as the manual path.
- Other docs mention `read_patch`/`save_patch_roundtrip` (CLAUDE.md Rule #5, TECHNICAL.md, max-patch-agent, max-dsp-agent, max-rnbo-agent, max-critic, severity-contract, max-onboard, max-build). Fix-plan rule 8: don't edit them, just list them in SUMMARY.md.

## Validation Architecture

| Property | Value |
|---|---|
| Framework | pytest (existing; `tests/conftest.py`) |
| Quick run | `python3 -m pytest -q tests/test_edit_session.py tests/test_patch_diff.py tests/test_hooks.py tests/test_save_gate.py tests/test_save_safety.py tests/test_edit_fidelity.py tests/test_doc_signatures.py` (the related files run in ~17 s; baseline 295 passed) |
| Full suite | `python3 -m pytest -q` (must be fully green; fix-plan rule 4, post-Q3) |

| Behaviour | Test | File |
|---|---|---|
| No-op session over every committed `.maxpat` copy: bytes same, no write, `saved False`, `commit_hash None` | unit, parametrized, tmp_path (no repo) | ❌ new `tests/test_edit_session.py` |
| No-op in a tmp git repo: HEAD unchanged, no "no changes to commit" warning | integration, `_repo(tmp_path)` | ❌ same |
| Edit (add box + cord) commits only that path; a pre-staged other file stays staged | integration | ❌ same |
| Exception in body → file bytes unchanged, no commit | unit | ❌ same |
| File modified between enter and exit → `StaleFileError`, bytes = the externally modified ones, `s.diff` set | unit | ❌ same |
| New blocker (e.g. reconverging fan-out, reuse `_fan()` from test_save_gate) → `PatchValidationError`, nothing written | integration | ❌ same |
| Port x-rank change in a subpatcher → `PatchValidationError` | unit | ❌ same |
| Removed cord → `SaveGateWarning` and the save succeeds | unit | ❌ same |
| Only touched cords get midpoints; existing midpoints untouched | unit | ❌ same |
| Contrast applied only to added/moved/presented boxes; untouched `textcolor`-less comments stay without one | unit (use ji-harmonizer HEAD copy: 83 boxes would change under whole-patch repair) | ❌ same |
| Atomic write: a failure in `os.replace` leaves the original bytes and no `.atomic-*.tmp` | unit (monkeypatch `os.replace`) | ❌ `tests/test_hooks.py` addition |
| Diff: added/removed/moved/resized/text/attrs/presentation/cords; nested path prefix; a renamed `p` still matches inner ids; external bpatcher not recursed; `a.diff(a)` is empty and falsy | unit on in-memory copies (`json.loads(git show HEAD:...)` or `read_text`) | ❌ new `tests/test_patch_diff.py` |
| Doc call forms bind | existing | ✅ `tests/test_doc_signatures.py` |

Test isolation: copy the autouse `_isolate_git_env` fixture (`test_save_safety.py:37-41`) and the `_repo` helper. For tmp_path saves outside a repo, add `pytestmark = pytest.mark.filterwarnings("ignore:.*not auto-committed:UserWarning")` (as `test_edit_fidelity.py:40-43` does). Never write a committed patch, not even with identical bytes (fix-plan rule 3).

## Package Legitimacy Audit
No external packages are installed in this task (stdlib + in-repo modules only).

## Security Domain
Local file I/O only; nothing is exposed to the network or other users. Relevant controls: atomic replace (integrity), the stale check (lost-update / TOCTOU, narrowed but not eliminated: MAX can still save between the stale read and `os.replace`), path-scoped commit (no `git add -A`). No ASVS auth/session/crypto categories apply.

## Assumptions Log

| # | Claim | Risk if wrong |
|---|---|---|
| A1 | Touched-only contrast is the intended reading of "run `repair_text_contrast(patcher)` on exit" (CONTEXT vs the no-op decision, D-4 and user feedback) | If the user really wants whole-patch repair, 33/63 user-confirmed patches get restyled on their first session and the no-op guarantee is void |
| A2 | Making `_write_and_sync` atomic for all three writers is acceptable (Q36 says "writes atomically"; the only route through `save_patch_roundtrip` is this helper) | If not, add a private `_atomic=True` path used only by the session |
| A3 | `os.replace` (new inode) does not upset an open MAX window more than an in-place rewrite does | Low; MAX does not hold .maxpat files open. Confirm when the user next edits a patch that is open in MAX |

## Open Questions
1. **Contrast scope on exit** (blocking, multiple choice for the user): (a) touched boxes only [recommended]; (b) none, with docs telling agents to call `repair_text_contrast` explicitly per Rule #9; (c) whole patch as CONTEXT literally says (breaks the no-op guarantee on 33/63 patches).
2. **Atomic write scope:** (a) all writers via `_write_and_sync` [recommended]; (b) session only.

## Sources
- Read this session: `src/maxpat/hooks.py:1-910`, `src/maxpat/patcher.py:42-52, 90-135, 241-360, 454-571, 1865-2180`, `src/maxpat/atomic_io.py:1-135`, `src/maxpat/aesthetics.py:572-676`, `src/maxpat/__init__.py:28-150`, `tests/test_hooks.py:300-365`, `tests/test_save_safety.py:1-120`, `tests/test_edit_fidelity.py:1-110`, `tests/test_doc_signatures.py:1-140`, `.claude/commands/max-iterate.md:40-141`, `.claude/skills/references/shared-capabilities.md:225-286`, fix plan Q36/Q39, review §5.3/§5.4.
- Probes (scratchpad scripts over `git show HEAD:` of all 63 tracked `.maxpat`): no-op round-trip 63/63 identical; touched-only midpoints 0/63 changed; assistance comments 9/63 changed; `repair_text_contrast` 33/63 changed (268 filled, 42 explicit changed); 42 external bpatchers, 0 embedded; gate `_gate_report` on ji-harmonizer 0.05 s.
- Memory: `feedback_contrast_critic_default_text.md` (do not recolor default-text comments on approved patches).
