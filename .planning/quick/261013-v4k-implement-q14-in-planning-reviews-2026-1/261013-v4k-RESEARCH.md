# Quick 261013-v4k: Q14 Inherited group messages and attributes (C8) - Research

**Researched:** 2026-10-13
**Domain:** Object DB sync (`tools/sync_max_bundle.py`) + `ObjectDatabase` accessors
**Confidence:** HIGH (every number below comes from a probe run this session against `/Applications/Max.app` 9.2.0 and the repo DB)

## Summary

Every object refpage already says which group names it inherits, as **names-only lists**. MC wrappers carry `<mcwrapper><mcwrappermethod name=…/><mcwrapperattr name=…/></mcwrapper>`. Jitter objects carry `<jittermethodlist><jittermethod/>` and `<jitterattributelist><jitterattribute/>`. So membership comes from the per-object refpage, never from a name prefix. The group pages only add **attribute types**. `parse_standard_xml` reads only `<methodlist>` / `<attributelist>`, so these lists were never extracted. That is why the deltas section reports 0 pending while C8 is real. There are 51 `mc.*` refpages with no `<mcwrapper>` (mc.pack~, mc.mixdown~, mc.gain~ …), which are native objects, not wrappers.

The fix plan's thispatcher source is wrong. `docs/userguide/content/controlling_max_with_messages.json` only has sections for `messages-to-max`, `midi-configuration-messages`, `messages-to-midi`, `messages-to-dsp` and `messages-to-jitter`. Its `wclose` is the **dsp** window message, and the file never mentions thispatcher. The user guide's `scripting_overview.json` says: "The help file for thispatcher provides an overview of its capabilities." The help patch is Max-serialized evidence, and per CLAUDE.md a help box beats documentation. Use `help/max/thispatcher.maxhelp`.

**Primary recommendation:** Add an `--apply groups` mode that writes one new file, `.claude/max-objects/groups.json`. It holds the group attribute definitions once, deduplicated name-list "profiles", and a member→profile map. Add read-only `ObjectDatabase.messages(name)` / `attributes(name)` / `selectors(name)` that merge at call time. **Do not mutate `lookup()` results.** Domain `objects.json` files and `overrides.json` stay byte-identical.

## Project Constraints (from CLAUDE.md)

- Rule #1: the DB is the single source of truth. This task is what makes `applyvalues` / `setvalue` legal for every mc.* wrapper.
- A help-patch box wins over a refpage. Refpage types are never allowed to overwrite expert overrides. The sync tool is additive and idempotent, cannot write `overrides.json`, and never changes existing I/O.
- After a sync: `audit_db.py`, then the dry-run, then the apply, then `--refresh-log`.
- Rule #5: a JSON data tool is fine; never regenerate `.maxpat`.
- Rule #7: no `git stash`. Commit with explicit paths, never `git add -A`.
- The refpage `name` attribute is authoritative, except for define-mapped aliases. Reuse `classify_refs` / `locate_base_entry`, which already handle this; the probe found 0 unresolved members.

## Current mechanics (verified)

| Thing | Where | Fact |
|---|---|---|
| Apply modes | `tools/sync_max_bundle.py:142` | `APPLY_MODES = ("new", "define", "deltas", "inherited")` [VERIFIED] |
| Refpage index | `_scan_refpage_file` :248-286 | Stores `"inherited_attributes"` from `element.findall("jitterattributelist/jitterattribute")`. It does **not** read `jittermethodlist` or `mcwrapper` [VERIFIED] |
| Group detection | `group_attribute_definitions` :1151-1176 | A "group page" is a refpage whose name contains whitespace. A name that two pages define differently is `ambiguous` and is dropped [VERIFIED] |
| Inherited report | `compute_inherited` :1179-1233 | Report-only. `_pending` feeds `apply_inherited` :1793-1820, which copies **named** attrs into domain files. `alpha_mode` landed this way [VERIFIED] |
| Write guard | `allowed_db_target` :1295-1319 | Allow-list: core `objects.json`, `packages/NAME/objects.json`, `package_info.json`. Everything else raises `WriteRefused` [VERIFIED] |
| Additive check | `check_additive` :1343-1390 | `messages` may grow (old list kept as prefix). `attributes` may gain keys. Nothing else may change [VERIFIED] |
| Writer | `write_db_file` :1393-1428 | `detect_style` on the **existing** bytes, so it cannot create a new file. Writes atomically and returns False when the bytes are identical [VERIFIED] |
| Extractor | `.claude/scripts/extract_objects.py:416-435` | messages = `methodlist/method` names. attributes = `{"type", "get", "set"}` from `attributelist/attribute` [VERIFIED] |
| `ObjectDatabase` | `src/maxpat/db_lookup.py` | No `messages()` / `attributes()` method exists. `lookup()` (:601-643) returns the shared mutable `_objects` dict. Supplementary files are each guarded by `exists()` [VERIFIED] |
| Override merge | `_apply_object_overrides` :386-431 | A non-port field replaces the base value whole. Keys are canonicalised through aliases. An unknown key raises `ValueError` [VERIFIED] |
| Consumers of `messages`/`attributes` | grep of src/tools | **Only** the sync tool itself. No critic or validator reads them yet; Q23's selector check will be the first [VERIFIED: grep] |

Current dry-run (`python3 tools/sync_max_bundle.py`, 2 s):
```
deltas          : 0 objects -- 0 messages on 0, 0 attributes on 0
inherited attrs : 53 group-page attributes unrecorded on 186 objects (report-only; --apply inherited --attributes NAME)
```
The repo DB was read via `json.load` this session:
- `mc/objects.json` `mc.cycle~` messages = `['float', '(mouse)', 'reset', 'set', 'setall', 'signal']`
- `jit.gl.mesh`: 11 attrs, including `alpha_mode` = `{'type': 'symbol', 'get': True, 'set': True}`
- `max/objects.json` `thispatcher` messages = `['anything', 'end', 'savewindow', 'setactivetab', 'showparameterwindow']`, attrs `{}`
- `overrides.json` sets `messages` on `mc.sig~` (whole replacement, already contains `applyvalues`). No override sets `attributes`.

## Bundle facts (Max 9.2.0)

**Group pages.** All are doc pages that never become DB objects; the current report lists them in `doc_pages`.

| File | `name` attr | Methods | Attributes (typed) |
|---|---|---|---|
| `docs/refpages/msp-ref/mcwrapper-group.maxref.xml` | `MC Wrapper Features` | 23 (ease.* collapsed to `ease.linear`) | 10: chans, initialvalues, values, replicate, target, usebusymap, zero, busymapname, op, voiceprob |
| `docs/refpages/jit-ref/jit.group-gl.maxref.xml` | `Jitter GL Object (OB3D) Messages` | 14 | 65 (float 30 / int 23 / symbol 12) |
| `docs/refpages/jit-ref/jit.group-mop.maxref.xml` | `Jitter Matrix Operators` | 9 | 7, including pattern names `[in/out]_dim`, `[in/out]_name`, … |
| `packages/Jitter Geometry/docs/jit.geom-group.maxref.xml` | `Jitter Geometry Features` | 4 | 4 |
| `docs/refpages/msp-ref/snapshot-group.maxref.xml` | `Snapshot Messages` | 9 | 1. No per-object names list references it, so it is **out of scope** |

`array.group`, `dict.group`, `zl.group`, `radiogroup` and `jit.ui.group` are real objects, not groups (their names have no whitespace).

None of the group pages has placeholder types or `TEXT_HERE` in its methods. `name` is ambiguous between gl and geom, and the existing logic already drops it.

**Per-object lists.** These are authoritative, and they vary per object:
- **MC:** 164 refpages carry `<mcwrapper>`, all named `mc.*`. The union is 53 methods (all `ease.*` variants expanded) and 14 attr names. There are 5 distinct signatures:
  - 92 have the full 53 methods + 13 attrs.
  - 68 lack `replicate`.
  - `mc.vst~` and `mc.amxd~` add `displaychan`.
  - `mc.sash~` has 19 methods.
  - `mc.record~` has an **empty** `<mcwrapper>`, so it gets nothing.
  - 51 `mc.*` refpages have no `<mcwrapper>` (`mc.pack~`, `mc.unpack~`, `mc.mixdown~`, `mc.gain~`, `mc.dac~`, `mc.poly~`, `mc.route`, …) and are not wrappers.
- **Jitter:**
  - 259 refpages have `<jittermethodlist>` with a 25-name union across 33 distinct signatures. The most common (101 objects) is bang, clear, exportattrs, exportsummary, getattributes, getstate, importattrs, jit_matrix, outputmatrix, summary.
  - 262 refpages have `<jitterattributelist>` with a 90-name union.
  - `exportsummary`, `rebuild_geometry` and `register` appear in object lists but not on any group page. Messages need no definition, so include them.
- **Attr names no group page defines** (current `undefined` report): `dim`, `planecount`, `out_name`, `in2_*`, `gl_color`, `fog_color`, `fog_density`, `fog_range`, `two_sided`, `material`, `texanchor`, `texrotate`, `texzoom`, `bounds`, `boundcalc`, `drawbounds`, `out2..4_*`, plus the MC `bz`, `bzname`, `fun`, `displaychan`. There is no type to record for these.
- **`jit.gl.mesh`:** 61 `<jitterattribute>` names. 47 are pending with a group definition (anchor, anim, …, position, rotatexyz, scale, …, viewalign), `alpha_mode` is already landed, and the rest are undefined/ambiguous.
- **Probe through `classify_refs` + `locate_base_entry`** (scratchpad script):
  - 163 MC members, every one lacking its wrapper names (8605 message adds, 2051 attr-name adds if copied).
  - 256 Jitter members lacking methods (2606 adds).
  - Member files: `mc/objects.json` 164, `jitter/objects.json` 199, `packages/Jitter Tools/objects.json` 55, `packages/Jitter Geometry/objects.json` 1.
  - 0 unresolved.
  - Copying all of this into the domain files would roughly double `mc/objects.json` (18,928 lines), which is why the separate file is the right call.

**thispatcher.** I walked the selectors of message boxes and `prepend X` boxes upstream of every `thispatcher` box in `help/max/thispatcher.maxhelp`, up to 3 hops including subpatchers:
- Top-level selectors: `clean, dirty, dispose, front, fullscreen, loadbang, path, savewindow, script, setactivetab, title, wclose, window, write`. This covers the required `script`, `write` and `wclose`.
- `script` subcommands seen: background, bringtofront, class, connect, connectcolor, delete, disconnect, hide, ignoreclick, move, newdefault, newobject, nth, offset, offsetfrom, respondtoclick, send, sendbox, sendtoback, show, size.
- `window` flags seen: constrain, exec, flags, getflags, getsize, gettitle, notitle, size, title, zoom.
- `build_help_index(c74)` (:349) already locates `.maxhelp` files by stem, so reuse it.

## Recommended design

### 1. `groups.json`: each group once, deduplicated profiles
```json
{
  "_comment": "Inherited group messages/attributes (review C8 / Q14). Written only by tools/sync_max_bundle.py --apply groups. Merged at call time by ObjectDatabase.messages/attributes/selectors; never copied into domain files.",
  "max_version": "9.2.0",
  "attribute_definitions": {
    "position": {"definition": {"type": "float", "get": true, "set": true}, "source": "jit-ref/jit.group-gl.maxref.xml"}
  },
  "profiles": {
    "mc-3f2a9c1e": {"messages": ["applymessages", "..."], "attributes": ["busymapname", "..."], "source": "mcwrapper"},
    "jit-7b01d2aa": {"messages": ["bang", "..."], "attributes": ["anchor", "..."], "source": "jitter"},
    "thispatcher-help": {"messages": ["clean", "...", "write"], "attributes": [], "source": "help/max/thispatcher.maxhelp"}
  },
  "members": {"mc.cycle~": ["mc-3f2a9c1e"], "jit.gl.mesh": ["jit-7b01d2aa"], "thispatcher": ["thispatcher-help"]}
}
```
- Store `attribute_definitions` once. Reuse `group_attribute_definitions()`, which already handles ambiguity, and record the source relative to `C74/`.
- Profile id = family + first 8 hex of the sha256 of the sorted name lists. It is deterministic, so a re-run is byte-identical.
- Members are keyed by the **DB key** returned by `locate_base_entry`, never the refpage filename.
- Serialize with `json.dumps(indent=2, sort_keys=True, ensure_ascii=False) + "\n"`.

### 2. Sync tool: new apply mode `groups` (the extension of the inherited path)
Keep `--apply inherited` as it is. `test_apply_needs_an_explicit_attribute_list` asserts that `--apply inherited` without `--attributes` exits 2, so reusing the bare form would regress it.

Changes in `tools/sync_max_bundle.py`:
- `_scan_refpage_file`: add `"inherited_messages"` (`jittermethodlist/jittermethod` + `mcwrapper/mcwrappermethod`) and `"mcwrapper_attributes"` (`mcwrapper/mcwrapperattr`).
- `compute_groups(index, classified, db, raw_db, existing_groups)` builds the target `groups.json` dict. It also returns a delta report (`members_added`, `names_added_per_family`, `unchanged`) and `undefined` attribute names.
- `thispatcher_help_selectors(c74, help_index)` does the help walk described above, with a depth bound like `MAX_PATCHER_DEPTH`.
- New dry-run section `"groups"`: add it to `SECTION_KEYS`, and add one `format_summary` line, e.g. `groups : N members (mc X / jit Y / thispatcher 1), +M names pending`. Put this line in SUMMARY.md, per Q14's "dry-run first" rule.
- `write_groups_file(path, data, db_root)` is a separate writer, because `write_db_file` cannot create a file. It may only target `<db_root>/groups.json`, and it must use `check_groups_additive(old, new)`:
  - no member is removed;
  - each member's effective name set (the union of its profiles' messages and attribute names) never shrinks;
  - an existing `attribute_definitions` entry never changes.

  It writes atomically and returns False on identical bytes. Add `groups.json` to the allow-list only through this function, and update the module docstring's write-path paragraph.
- `compute_inherited` must treat attribute names recorded in `groups.json` as recorded. Otherwise "53 attrs on 186 objects" stays in the report forever after the apply.
- `--refresh-log`: add `"group_members"` and `"pending_group_names"` to the `sync` block. Existing refresh-log tests assert `domain_counts`/`history`, not the exact `sync` keys.

### 3. `ObjectDatabase`: read-only merge (`src/maxpat/db_lookup.py`)
- In `_load`, after `_apply_object_overrides`, load `groups.json` only `if exists()`. The minimal-db-root tests rely on that guard.
  - Canonicalize member keys through `self._aliases`.
  - An unknown member raises `ValueError`, matching the overrides policy (C7).
  - A missing profile id raises.
- `messages(name) -> list[str] | None`: `lookup(name)["messages"]` (base, or the override list as for `mc.sig~`) + inherited profile messages, order-preserving dedupe. Returns None for an unknown object.
- `attributes(name) -> dict | None`: own attrs, plus inherited names that have an `attribute_definitions` entry. **Own definitions win.** Already-landed `alpha_mode` stays as is.
- `selectors(name) -> set[str] | None`: messages ∪ own attr names ∪ **all** inherited attr names, including undefined-type ones like `fun`, `bz`, `dim`. This is the set Q23's selector check should use, since Max accepts any attribute name as a message.
- **Never write inherited data into `_objects`.** `compute_deltas` detects override shadowing with `resolved_messages != raw_messages` (:1118-1123), so mutating `lookup()` would flag every group member as "shadowed by override".

## Common Pitfalls
1. **Treating `mc.` as membership.** 51 mc.* objects are not wrappers, and `mc.record~` lists none. Use `<mcwrapper>` children only.
2. **Refpage filename vs name attribute, and define aliases.** Iterate `classified["authoritative"]` and resolve with `locate_base_entry`. The probe got 0 unresolved this way.
3. **Fabricating attribute types.** Undefined names (`dim`, `gl_color`, `fun`, …) get no definition. They go only in `selectors()`, consistent with the existing `undefined` handling.
4. **Ambiguous `name`.** It is defined differently by gl and geom. Keep it out of `attribute_definitions`. It is still a selector.
5. **Mutating `lookup()`.** This breaks shadow detection and shared state; see design §3.
6. **First write of a new file.** `write_db_file`/`detect_style` read the existing bytes, so they cannot create `groups.json`. Use a dedicated writer.
7. **Non-determinism.** Sort names inside each profile, and hash after sorting, so an idempotent re-run is byte-identical. Test this.
8. **The thispatcher source.** Do not parse `controlling_max_with_messages.json`: it is the max/dsp/midi/jitter app-message page, and its `wclose` is the DSP window. Record the help-patch provenance in the profile `source`, and note the fix-plan correction in SUMMARY.md.
9. **The `mc.sig~` override list.** Override `messages` replace the base list, so `messages()` must union the inherited profile on top of the resolved list.
10. **`--apply inherited` exit-2 contract and the `WriteRefused` parametrized list.** Leave both untouched. The new mode is additive to the CLI.

## Validation Architecture

| Property | Value |
|---|---|
| Framework | pytest (repo standard) |
| Quick run | `python3 -m pytest tests/test_sync_max_bundle.py tests/test_db_groups.py tests/test_db_lookup.py -q` |
| Full suite | `python3 -m pytest -q` |
| Baseline (this session) | Subset (sync, db_lookup, audit_db, override_merge, object_schema, domain_scope): **432 passed**. Full: **3171 passed, 1 xfailed, 1 xpassed, 29 warnings** (60 s) |

**Real-DB tests**, new file `tests/test_db_groups.py`. These read the committed `groups.json` and need no Max:
- `test_mc_cycle_messages_include_applyvalues_and_setvalue`
- `test_jit_gl_mesh_has_ob3d_attributes`. Assert, e.g., `{"position", "rotatexyz", "scale", "blend_enable", "depth_enable", "lighting_enable", "drawto", "enable"} <= db.attributes("jit.gl.mesh").keys()`, and that `position` is typed `float` from the group page.
- `test_thispatcher_has_script_write_wclose`
- `test_lookup_dict_is_not_mutated`: `lookup("mc.cycle~")["messages"]` is still the 6 base names.
- `test_override_message_list_still_gains_group_names` (`mc.sig~`)
- `test_native_mc_object_is_not_a_member`: `mc.pack~` messages do not include `applyvalues`.
- `test_undefined_inherited_attr_is_selector_not_attribute` (`fun` on `mc.cycle~`)

**Fixture tests**, using a tmp db_root:
- `test_missing_groups_file_is_fine`
- `test_unknown_member_key_raises`
- `test_alias_member_key_canonicalises`

**Sync fixture tests**, a `TestGroups` class in `tests/test_sync_max_bundle.py`. Extend `_add_group_fixtures` with an mc wrapper refpage that has `<mcwrapper>`, a jit refpage with `<jittermethodlist>`, and a fake `thispatcher.maxhelp`.
- `test_dry_run_reports_groups_and_writes_nothing` (tree bytes identical)
- `test_apply_groups_writes_only_groups_json`: domain files and `overrides.json` sha are unchanged.
- `test_apply_groups_is_idempotent` (byte-identical second run)
- `test_groups_writer_refuses_member_removal` / `..._definition_change`
- `test_inherited_report_counts_groups_json_as_recorded`

**Wave 0:** none. pytest and the fixture builders (`_refpage`, `_make_bundle`, `world`) already exist.

**Execution order for the real apply:**
1. `python3 tools/audit_db.py`
2. `python3 tools/sync_max_bundle.py`: paste the groups line into SUMMARY.md.
3. `python3 tools/sync_max_bundle.py --apply groups`
4. Re-run the dry-run and confirm 0 pending.
5. `python3 tools/sync_max_bundle.py --refresh-log`
6. Run the full suite.
7. Commit with explicit paths: `groups.json`, `extraction-log.json`, the tool, `db_lookup.py`, and the tests.
8. Add one CLAUDE.md line under "How to Use the Database": use `db.messages()` / `db.attributes()` / `db.selectors()` for message/attribute questions, because `lookup()` excludes inherited group names.

## Suggested task split
1. **Sync tool:** scan additions, `compute_groups`, thispatcher help walk, `groups` section and apply mode, `write_groups_file` + additive check, inherited-report adjustment, log fields, and the `TestGroups` tests.
2. **ObjectDatabase:** `groups.json` load, `messages` / `attributes` / `selectors`, and the fixture tests.
3. **Real run:** dry-run delta into SUMMARY.md, apply, refresh-log, real-DB tests, CLAUDE.md note, and the full-suite gate.

## Assumptions Log
| # | Claim | Risk if wrong |
|---|---|---|
| A1 | Max accepts any settable attribute name as a message selector, which justifies `selectors()` including attr names | Q23 would under-warn; it would not cause false errors [ASSUMED] |
| A2 | The help-patch selectors (14) are the right curated thispatcher set. The help shows usage, but it is not an exhaustive spec | Q23 may warn on rare valid thispatcher messages. Low risk, since `thispatcher` lists `anything` [ASSUMED] |
| A3 | Profile-dedup storage satisfies "store each group once" better than per-member verbatim lists (~18k lines) | Only the file layout changes; behaviour is identical [ASSUMED: design judgment] |

## Open Questions
1. Should `groups.json` also record the `script` subcommands and `window` flags (useful for a later scripting validator)? Recommendation: store them as `profiles["thispatcher-help"]["script_subcommands"]`. It is cheap, it is not exposed through `messages()`, and it is optional.
2. Should Snapshot Messages (vst~/amxd~) be imported? No per-object list references them. Recommendation: out of scope, note it in SUMMARY.md.

## Sources
- Installed bundle: `/Applications/Max.app/Contents/Resources/C74/docs/refpages/{msp-ref,jit-ref}/…group….maxref.xml`, `msp-ref/mc.rate~.maxref.xml` (`<mcwrapper>` block), `jit-ref/jit.gl.mesh.maxref.xml`, `max-ref/thispatcher.maxref.xml`, `help/max/thispatcher.maxhelp`, `docs/userguide/content/{controlling_max_with_messages,scripting_overview}.json` [VERIFIED: parsed this session]
- Repo: `tools/sync_max_bundle.py`, `src/maxpat/db_lookup.py`, `.claude/scripts/extract_objects.py`, `tests/test_sync_max_bundle.py`, `.planning/reviews/2026-10-11-{fix-plan,repo-review}.md` [VERIFIED: read this session]
- No external packages are installed, so the package legitimacy audit is not applicable. Security: local JSON data tool, no network. The existing write guard (path allow-list, refusal of report paths under the DB/patches) extends to `groups.json`.

**Valid until:** next Max update (re-run the dry-run after any bundle change).
