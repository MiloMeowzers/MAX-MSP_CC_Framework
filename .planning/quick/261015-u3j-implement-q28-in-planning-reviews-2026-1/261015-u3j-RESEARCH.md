# Quick 261015-u3j: Q28 Edit fidelity I (change tracking) - Research

**Researched:** 2026-10-15
**Domain:** `src/maxpat/patcher.py` round-trip serialization (Box/Patchline/Patcher)
**Confidence:** HIGH. Every claim comes from code read this session or a probe run this session.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
**Tracking mechanism**
- **Load snapshot + diff.** At `from_dict`, snapshot (deep copy) each tracked field: Box `fontname`, `fontsize`, `extra_attrs` (whole dict); Patchline `order`, `hidden`, `midpoints`, `color`, `extra_attrs`.
- At `to_dict`, write back any field whose current value differs from its snapshot; extra_attrs keys deleted since load are removed from the output; added keys are written.
- Unchanged fields come straight from `_raw`, so a no-op round-trip stays lossless (key order preserved; new keys append at the end).
- Must catch in-place mutation of lists/dicts (e.g. `box.extra_attrs["bgcolor"][3] = 0.5`) — hence deep-copied snapshot, not setters.

**Direct `_raw` writes**
- Keep working: a direct `_raw[k]` write still reaches disk when the corresponding tracked field is unchanged since load. A changed tracked field wins over `_raw`.
- Retire the manual `_raw` sync copies in `modify_box` (patcher.py ~627-739), `set_assistance_comment` (~1234-1252) and `aesthetics.py:414` where tracking now covers them (keep any that cover non-tracked fields such as text/numinlets/patching_rect if still needed — `patching_rect`/`text`/num* are already overlaid in to_dict).
- Simplify the CLAUDE.md Rule #5 "On round-tripped (pre-existing) boxes, `extra_attrs` mutations are silently dropped" paragraph to reflect that edits now reach disk.

**Port removal in loaded subpatchers**
- Adding/removing an inlet/outlet box in a subpatcher (loaded or new) resyncs the parent box's `numinlets`/`numoutlets`/`outlettype` (via a `sync_port_counts()`-style helper invoked from add/remove of inlet/outlet boxes; the inner patcher needs a back-reference to its parent box/patcher).
- Parent cords whose port index is now out of range are removed and returned as orphans (like `replace_box`'s `EditResult.orphaned`); the save gate's removed-cord warning still fires.
- Port index is by x-rank of inlet/outlet boxes (MAX convention; see memory "Subpatcher port x-order").

### Claude's Discretion
- Exact helper names and where the snapshot lives (`_loaded` dict attr on Box/Patchline).
- Whether `from_dict` deep-copies once at the top level or per box/line (must not share any nested object with the caller's dict).

### Deferred Ideas (OUT OF SCOPE)
None listed. Q29 (replace_box identity, MAX-style JSON writer, add_box nudge) and Q36 (`edit_patch`, `Patcher.diff`) are separate tasks. Do not pull them in.
</user_constraints>

## Rules for every task (copy into PLAN.md, from fix-plan.md:17-31)
1. Read the finding IDs in the review report first.
2. Write each regression test **first**: red before the fix, green after.
3. **Never edit committed patch files** (`patches/**/*.maxpat|.gendsp|.maxhelp|.js`).
4. Run `python3 -m pytest -q` before and after. Baseline this session: **4937 passed, 5 xfailed, 1 xpassed** (87 s). The suite must be fully green.
5. Never `git stash`. Never `git add -A` or `git add .`. Stage explicit paths only.
6. Code must work on Python 3.10.
7. Don't widen scope. If the fix needs a decision the report doesn't make, stop and ask with multiple-choice options.
8. Edit CLAUDE.md, skills or TECHNICAL.md only where the task says to. List any other doc impact in SUMMARY.md.
9. In SUMMARY.md, flag anything the user must confirm in MAX or Live.

## Summary

All three findings reproduce on the bassoon patch this session (the probe was run against an in-memory load; nothing was written):
- **B5:** `set_object_bgcolor` gives bgcolor `None` on output. `fontsize=20` saves as `12.0`. Cord `order=3` and `hidden=True` both come out `None`.
- **B6:** `modify_box(position=[999,999])` changed the caller's input dict to `[999, 999, 44.0, 22.0]`.
- **B7:** after adding a third inlet inside `p articulation`, the parent still has 2. `add_connection(..., art, 2)` raises `ValueError: Inlet index 2 out of range for box obj-85 (p articulation) which has 2 inlet(s)`.

**Root causes:**
- `Box.to_dict` round-trip path (patcher.py:288-324) starts from `dict(self._raw)` and overlays only rect, I/O, text, outlettype, presentation, the inner patcher and saved_object_attributes. It never writes `extra_attrs`, `fontname` or `fontsize`.
- `Patchline.to_dict` (patcher.py:94-109) overlays source, destination, color and midpoints, but not `order`, `hidden` or `extra_attrs`.
- `from_dict` builds `raw = dict(box_data)`, a shallow copy (patcher.py:1442). Box fields and extra_attrs values alias the caller's lists.
- Loaded inner patchers have no link to their parent box (patcher.py:1423-1427; `_is_subpatcher` is set `False` at :1370).

**Primary recommendation:**
- Public `from_dict` does one `copy.deepcopy(data)`, then recurses through a private owned-dict builder.
- Store `_loaded` snapshots on Box and Patchline, and apply the diff in `to_dict` *before* the structural overlays.
- Add `_parent_box` / `_parent_patcher` back-refs and a `_sync_parent_ports()` that runs from `add_box` and `remove_box` when the box's maxclass is `inlet` or `outlet`. `remove_box` returns the orphaned parent cords.

## Architectural Responsibility Map

| Capability | Owner | Notes |
|---|---|---|
| Snapshot at load | `Patcher.from_dict` (patcher.py:1318-1482) | Box via `Box.__new__`. Patchline via its constructor with `_raw=` |
| Diff write-back | `Box.to_dict` / `Patchline.to_dict` round-trip branches | Creation branch unchanged |
| Input isolation (B6) | `Patcher.from_dict` public entry | One deepcopy, not one per level |
| Parent port sync (B7) | `BuildersMixin.add_box` (builders.py:41-94), `Patcher.remove_box` (patcher.py:536-554) | Back-refs set in from_dict, add_subpatcher (builders.py:823), embedded add_bpatcher (builders.py:940) |
| Save-time safety net | `hooks._run_save_gate` (hooks.py:772-860) | Already reports removed cords and port x-rank changes; no change needed |

## Findings

### 1. `_raw` write inventory (src, skills, tests)

| Site | Writes | Tracked by Q28? | Action |
|---|---|---|---|
| patcher.py:709-716 `modify_box(args=)` | `_raw` text, numinlets, numoutlets, outlettype, patching_rect | No (already overlaid in to_dict:294-300) | **Keep.** Redundant for disk but pinned by tests: test_edit_keeps_user_work.py:339-340, 441, 491; test_patcher.py:1283 |
| patcher.py:721-722 `modify_box(position=)` | `_raw["patching_rect"]` | No (overlaid) | **Keep** (test_patcher.py:1315-1316 asserts it) |
| patcher.py:726-727 `modify_box(color=)` | `_raw["bgcolor"]` | Yes (extra_attrs) | **Retire** |
| patcher.py:738-739 `modify_box(extra_attrs=)` | `_raw.update(extra_attrs)` | Yes | **Retire.** The presentation sync at :733-736 stays |
| patcher.py:1059-1060 `_auto_position` | `_raw["patching_rect"]` | No (overlaid) | Keep (harmless) |
| patcher.py:1251-1252 `_set_assistance_comment` | `_raw["comment"]` | Yes | **Retire.** The helper reduces to the extra_attrs write; update its docstring and :1234-1235 |
| aesthetics.py:582-593 `_set_textcolor` (the review's ":414"; the line has moved) | `_raw["textcolor"]` | Yes | **Retire.** Rewrite the docstring at :584-589, which cites the old rule |
| builders.py, rnbo.py, externals.py `x._raw = None` (about 20 sites) | new boxes | n/a | Untouched (creation path) |
| validation.py:609 | *reads* `box._raw` before extra_attrs for the mc.gen~ `data` key | — | Optional: read `box.extra_attrs` so an edited `data` is seen. Same key on both paths |
| hooks.py:166 docstring | "written to `_raw`" | — | Update wording |

**Docs:**
- CLAUDE.md:108 is the Rule #5 paragraph: the task edits it.
- CLAUDE.md:238 (bpatcher args: "convert numeric strings in `box._raw["args"]`") stays valid, because direct `_raw` writes keep working. After Q28, `box.extra_attrs["args"]` also works. List this in SUMMARY.md as doc impact; do not edit it.
- TECHNICAL.md:342 and max-9.2-changes.md:137 stay accurate.
- No skill SKILL.md mentions `_raw`.

**Test guard (must update):** `tests/test_claude_md.py:196`. `RULE_ANCHORS` contains `"silently dropped at serialize"` (and `"box._raw"` at :163). Rewording Rule #5 drops the first anchor, so replace it in `RULE_ANCHORS` with a phrase from the new text. `"box._raw"` survives because CLAUDE.md:238 still contains it. Budget: CLAUDE.md is 26782 bytes, under `CLAUDE_BUDGET_BYTES = 30_000` (test_claude_md.py:115) [VERIFIED: wc -c, Read].

### 2. Readers and hidden behaviour changes

- **Tracked-field writers on loaded objects in src:**
  - extra_attrs: only `set_object_bgcolor` (aesthetics.py:200-203), `apply_auto_styling` through it (aesthetics.py:259-262), `_set_textcolor`, `modify_box`, `_set_assistance_comment`.
  - fontname/fontsize: none in src; builders set them on new boxes only.
  - Line `midpoints`: layout.py:382, 1646-1653, 1677, 1713 (already reach disk through the current overlay).
  - Line `order`/`hidden`/`color`: nothing in src writes them on loaded lines.
- **The behaviour change to watch:** `apply_auto_styling` on a *loaded* patch will now persist dac~/loadbang highlight bgcolors that were silently dropped before. `finalize_patch(is_new=False)` does not call it (hooks.py:183-185), so the default edit flow is unaffected. Calling it by hand on a loaded patch will now change files. Note this in SUMMARY.md.
- **Hidden aliasing today:** loaded `extra_attrs` values are *the same objects* as `_raw` values (patcher.py:1436-1445 builds both from `box_data`). In-place nested edits such as `extra_attrs["bgcolor"][3] = 0.5` on an existing key therefore already reach disk, and they also mutate the caller's dict. Only rebinding a key, or adding a new key, is dropped. Keep the aliasing between extra_attrs and `_raw` (both now owned after the deepcopy). The snapshot must be a separate deepcopy.
- **Other aliases (fine once the input is owned):**
  - `box.patching_rect is _raw["patching_rect"]`. `box.outlettype is _raw["outlettype"]`. `box._saved_object_attributes is box_data["saved_object_attributes"]`.
  - `pl.midpoints` and `pl.color` are the `_raw` lists.
  - `_loaded_rect` is already a tuple copy (patcher.py:1448) and is used by `hooks._box_added_or_moved` (hooks.py:188-203). Leave it as is.
- **`to_dict` output aliases the model** (`d["patching_rect"] = self.patching_rect`, and so on). This is not B6 and is out of scope; callers already deepcopy before validating (hooks.py:569-570).

### 3. B6 deep-copy point and cost

- Only one src caller of `from_dict` exists: `read_patch` (hooks.py:386). Tests call it heavily.
- Timings on the largest repo patch, `terrain-synth.maxpat` (2.19 MB, 1499 boxes including nested), mean of 5 runs:

| Operation | Time |
|---|---|
| `from_dict` | 3.5 ms |
| `copy.deepcopy(data)` | 7.0 ms |
| `json.loads(json.dumps(data))` | 5.2 ms |
| `to_dict` | 1.5 ms |
| deepcopy of all box extra_attrs plus line midpoints/extra_attrs (snapshot cost) | 1.8 ms |

  Memory: the snapshot roughly doubles extra_attrs and midpoints storage, which is a few MB at worst. Negligible.
- **Recommendation:** in the public `from_dict`, run `data = copy.deepcopy(data)` once, then call a private `_from_owned_dict(...)`. The inner-patcher recursion at patcher.py:1423 calls `_from_owned_dict` directly, so nested patchers are not re-copied at every depth.
  - Keep the public signature `from_dict(cls, data, db=None, *, domain_context=None)`.
  - The `copy.deepcopy(val)` for props at :1380 can become a plain assignment, though that is optional.
  - Use `copy.deepcopy`, not a JSON round-trip, so non-JSON test inputs (tuples) don't break.

### 4. B7 port sync

- **Repro confirmed:** `patches/bassoon-model/generated/bassoon-model.maxpat` box `obj-85` "p articulation": numinlets 2, numoutlets 2, outlettype `['', '']`, 2 inner inlets and 2 inner outlets.
- **Back-refs to add:** set `inner._parent_box = box` and `inner._parent_patcher = p`.
  - Where: from_dict (:1423); add_subpatcher (builders.py:823); embedded add_bpatcher (builders.py:940). gen (builders.py:1112) and rnbo (rnbo.py:389) are optional and harmless, because their ports are `in N` / `in~ N` newobj boxes, not maxclass `inlet`/`outlet`.
  - Default `None` in `Patcher.__init__` and in from_dict. Read via `getattr(..., None)`.
- **When to sync:** only when the box's maxclass is `"inlet"` or `"outlet"` and the parent box is a `p`/`patcher` newobj or a `bpatcher`.
- **Port order:** `get_inlets()` / `get_outlets()` (patcher.py:1189-1215) sort by `patching_rect[0]` (stable, so ties fall back to array order). This matches `hooks._port_ranks` `(x, array index)` (hooks.py:679-707).
- **Sync algorithm:**
  - Set `numinlets = len(inlets)` and `numoutlets = len(outlets)`.
  - Rebuild `outlettype`: delete the entry at the removed outlet's rank (computed *before* removal), and insert `""` at a new outlet's rank. Pad or truncate to `numoutlets`.
  - Then remove any parent-patcher cords with `dest_id == parent.id and dest_inlet >= numinlets`, or `source_id == parent.id and source_outlet >= numoutlets`, and return them as orphans.
- **Outlettype convention:** a survey of all 69 repo files found 110 `p` boxes, every one with counts matching its inner ports.
  - Parent outlettype usually copies the type of the inner source that feeds the outlet: 19 `signal`←signal, 6 bang, 3 int, 2 float, 2 multichannelsignal, 2 jit_gl_texture.
  - There are also 11 cases of `''` with a signal source, so `""` is also found in practice.
  - Q1 made container boxes accept any connection in validation (fix-plan.md:43). So `""` for a new outlet is safe; deriving the type is optional.
- **Return shape:**
  - `add_box` must keep returning `Box`. Adding a port never orphans anything (counts only grow).
  - `remove_box` currently returns `None` (patcher.py:536-554). Change it to return `EditResult(box=removed_box, orphaned=[...parent-patcher cords])`. This is backward compatible: no caller uses the return value (the only src caller is replace_box:798).
  - Document that these orphans are cords in the **parent** patcher.
  - `replace_box` of a port box goes through remove + add, so the sync runs twice. Correct, if redundant.
- **Save-gate interaction (no code change needed):**
  - Removed parent cords show up in `_gate_report.removed_cords` and warn `SaveGateWarning` (hooks.py:815-837).
  - Removing a *non-rightmost* port, or adding a port left of existing ones, changes the x-rank of existing port boxes. `port_changes` then makes the save **raise `PatchValidationError`** unless `force=True` (hooks.py:755-765, 839-865). Only rightmost add/remove saves cleanly.
  - The locked "out-of-range only" orphan rule means a middle-port removal leaves cords above it pointing one port too high in memory. The gate refuses that save, so nothing silently wrong reaches disk. Put this in the remove_box docstring.

### 5. Lossless round-trip test

- **What the "69" counts:** all files under `patches/**` with extensions `.maxpat` + `.maxhelp` (57) and `.gendsp` (12). This session's probe ran `from_dict(d).to_dict() == original` on all 69: **0 mismatches, 0 skipped, no input mutated.**
- **Existing coverage:**
  - `tests/test_round_trip.py:73-84,366-380` `TestRoundTripIdentity::test_round_trip_identity` uses only a **10-file** `_PROJECT_PATCHES` list and compares by **dict equality** (`result == original`), not bytes. The comment at :43-56 explains why bytes are out of reach: MAX's compact arrays, which is Q29's job.
  - `tests/test_save_gate.py:846-877` `TestRoundTripNoFalseBlocks` covers `patches/*/generated/*.maxpat|*.gendsp` (67 files) through the gate report, not equality.
- **Recommendation:** keep the existing test. Add a parametrized `test_round_trip_identity_all_repo_files` over `sorted(rglob)` of the three extensions (69 ids). It should also assert the input dict is unchanged after `from_dict(...)` plus a mutation, which doubles as B6 coverage.

### 6. Pitfalls

1. **Overlay order.** Apply the extra_attrs, font and line diffs **before** the structural overlays in `Box.to_dict`.
   - Why: `modify_box(extra_attrs={"presentation": ...})` puts handled keys into extra_attrs (patcher.py:733-737). With the overlays last, `box.presentation` / `presentation_rect` / `patching_rect` still win.
   - Also skip handled keys in the diff. Hoist `_handled_keys` (patcher.py:1430-1435, quoted verbatim: `"id", "maxclass", "text", "numinlets", "numoutlets", "outlettype", "patching_rect", "fontname", "fontsize", "presentation", "presentation_rect", "patcher", "saved_object_attributes"`) to a module constant shared by from_dict and to_dict. [VERIFIED: patcher.py:1430-1435]
2. **Key order.** Use `d[k] = v` on a key that already exists, which keeps its position, and `d.pop(k)` for deletions. Added keys then append. Don't rebuild `d`.
3. **12 vs 12.0, 1 vs True.** Six boxes in the repo have an int `fontsize`; all others are float. Lines carry `order` (515, 195 of them `0`) and `midpoints` (3862). No repo line has `hidden` or `color`.
   - Compare current values to the *snapshot*, never to `_raw`. Python's `12 == 12.0` and `[1,0] == [1.0,0.0]` then count as unchanged, so the original representation is kept (lossless).
   - Snapshot `hidden` as the bool the model holds (patcher.py:1473).
4. **Default-valued writes.**
   - `order` is written whenever it changed, including to `0` (MAX writes `order: 0`).
   - `hidden` changed to False: pop the key. Changed to True: write `1`, matching the creation path (patcher.py:119-120).
   - `midpoints` changed to empty or None: pop. Otherwise write `list(...)`.
   - `color` changed to None: pop. This keeps today's overlay semantics, now applied only on a change. Existing tests to keep green: test_round_trip.py:240-301.
5. **Missing snapshot.** Builder boxes come from `Box.__new__` with `_raw = None`. Read `getattr(self, "_loaded", None)`. If `_raw` is set but there is no snapshot, apply no diff (today's behaviour).
   - For Patchline: take the snapshot in `__init__` when `_raw is not None`, so any direct `Patchline(_raw=...)` construction is covered too. from_dict passes `_raw=` there (patcher.py:1467-1478).
6. **Nested patcher sentinel.** `_raw["patcher"] = None` (patcher.py:1443-1444) must stay. `"patcher"` is a handled key, so it never enters the extra_attrs snapshot.
7. **Bpatcher.** `_bpatcher_attrs` is `None` on load (patcher.py:1419) and only the creation path uses it (patcher.py:354-355). On loaded bpatchers those attrs live in `extra_attrs` (test_round_trip.py:485), so Q28 tracking covers them. Leave `_bpatcher_attrs` untracked. All 43 repo bpatchers are file-based (none embedded).
8. **Python 3.10.** Only Python 3.14.2 is installed locally; no `python3.10`. Avoid 3.11+ features (`typing.Self`, `except*`, `tomllib`). Plain dicts, `copy.deepcopy` and `dataclasses` are fine. This cannot be verified locally, so flag it in SUMMARY.md.
9. **deepcopy of a Patcher with back-refs.** `copy.deepcopy(patcher)` handles the Box↔Patcher cycle through its memo. Don't add `__eq__`/`__hash__`.
10. **`_is_subpatcher` is unreliable** for loaded inner patchers: it is set `False` at patcher.py:1370. Use the new back-ref, not this flag.

## Code Examples (sketch; names are Claude's discretion)

```python
# Box.to_dict round-trip branch, before the existing overlays
d = dict(self._raw)
snap = getattr(self, "_loaded", None)
if snap is not None:
    old = snap["extra_attrs"]
    for k in old:
        if k not in self.extra_attrs:
            d.pop(k, None)                      # deleted since load
    for k, v in self.extra_attrs.items():
        if k in _BOX_HANDLED_KEYS:
            continue
        if k not in old or old[k] != v:
            d[k] = v                            # changed (in place) or added (appends)
    for f in ("fontname", "fontsize"):
        if getattr(self, f) != snap[f]:
            d[f] = getattr(self, f)
d["patching_rect"] = self.patching_rect          # ...existing overlays unchanged below
```

## Validation Architecture

| Property | Value |
|---|---|
| Framework | pytest (repo standard). Full suite 4937 passed, 87 s |
| Quick run | `python3 -m pytest -q tests/test_change_tracking.py tests/test_round_trip.py tests/test_save_gate.py tests/test_claude_md.py` |
| Full suite | `python3 -m pytest -q` |

| Finding | Test (new file `tests/test_change_tracking.py`, red-first) | Red today? |
|---|---|---|
| B5 | Load bassoon in memory. `set_object_bgcolor`, `fontsize=20`, `populate_assistance_comments` on an inlet with empty comment, line `order`/`hidden` → all present in `to_dict()` | Yes (probe) |
| B6 | `modify_box(position=…)` and an in-place `extra_attrs` list edit leave a pristine `deepcopy` of the input equal to the input | Yes (probe) |
| B7 | `p articulation`: `inner.add_box("inlet", x=500)` → parent numinlets 3 and `add_connection(…, art, 2)` succeeds. Removing the rightmost inlet → numinlets 2 and the cord returned in `remove_box(...).orphaned` | Yes (probe) |
| S4 | In-place nested mutation of a *new* key reaches disk. A direct `_raw[k]` write on an unchanged field reaches disk. A changed extra_attr beats a conflicting `_raw` write. A deleted extra_attrs key is absent from output. New keys append after existing keys | Partly |
| Round-trip | Parametrize over all 69 `patches/**` files (dict equality) | Green today, keep green |

**Wave 0:** create `tests/test_change_tracking.py`. Update `RULE_ANCHORS` in `tests/test_claude_md.py` alongside the CLAUDE.md edit. Tests load committed patches read-only and never write them.

## Security Domain
Not applicable: a local library serialization change with no auth, network or crypto. Input-validation surface is unchanged (`from_dict` structural checks at patcher.py:1344-1355 stay).

## Assumptions Log

| # | Claim | Risk if wrong |
|---|---|---|
| A1 | `""` is an acceptable outlettype for a newly added parent outlet, since MAX recomputes it on load | Low: Q1 container rule already exempts `p` boxes in validation. The user can confirm in MAX that the new port appears and works |
| A2 | Code is 3.10-compatible (not runnable locally) | Low if the code avoids 3.11+ features |

## Open Questions
1. **Middle-port removal remapping.** The locked rule orphans only out-of-range cords. MAX itself renumbers, keeping each cord on its port object.
   - Recommendation: implement the locked rule and rely on the save gate's port x-rank refusal. Do not widen scope. If the planner wants a rank-aware remap, ask the user (A: locked out-of-range only; B: orphan the removed port's cords and shift the higher ones).

## Sources
- Read this session: `src/maxpat/patcher.py` 40-1506; `src/maxpat/hooks.py` 141-240, 640-860; `src/maxpat/builders.py` 41-100, 700-835, 925-946, 990-1120; `src/maxpat/aesthetics.py` 182-206, 248-262, 582-593; `src/maxpat/validation.py` 595-615; `tests/test_round_trip.py` 40-95, 360-390; `tests/test_save_gate.py` 835-877; `tests/test_claude_md.py` 150-300; `tests/test_aesthetics.py` 950-975.
- Probes run this session: B5/B6/B7 repro on the bassoon patch (in memory); a 69-file round-trip and input-mutation check; timings on terrain-synth; a survey of p-box outlettype and line keys.

**Valid until:** the next edit to patcher.py (internal code). Line numbers are as of HEAD 5fdc098e.
