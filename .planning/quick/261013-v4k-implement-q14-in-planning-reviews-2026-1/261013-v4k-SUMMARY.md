---
phase: quick-261013-v4k
plan: 01
status: complete
subsystem: object-db
tags: [db, sync, groups, mc, jitter, thispatcher, C8, Q14]
requires: [Q13 (c306849c)]
provides:
  - "tools/sync_max_bundle.py --apply groups -> .claude/max-objects/groups.json"
  - "ObjectDatabase.messages() / attributes() / selectors()"
affects: [Q23 selector check (use selectors())]
tech-stack:
  added: []
  patterns: ["call-time merge of a supplementary DB file; lookup() never mutated"]
key-files:
  created:
    - .claude/max-objects/groups.json
    - tests/test_db_groups.py
  modified:
    - tools/sync_max_bundle.py
    - src/maxpat/db_lookup.py
    - tests/test_sync_max_bundle.py
    - .claude/max-objects/extraction-log.json
    - CLAUDE.md
decisions:
  - "New --apply groups mode; bare --apply inherited keeps its exit-2 contract"
  - "thispatcher selectors come from help/max/thispatcher.maxhelp, not the user-guide JSON"
  - "Group membership skips only whitespace-named group pages, not every _is_doc_page ref (jit.graph / jit.plot are real objects)"
metrics:
  duration: "~10 min"
  completed: 2026-10-13
estimate:
  tokens: 120000
  tasks: 3
actuals:
  tokens: 37700
  tasks: 3
  commits: 3
plan_head_before: e98525674828ac13a5a6d800bf9df129b86309b7
plan_head_after: 102e6786434182c24bb9a3ed79013702427c9e8f
---

# Phase quick-261013-v4k Plan 01: Inherited group names (Q14 / C8) Summary

`--apply groups` writes `.claude/max-objects/groups.json` from refpage `<mcwrapper>` / `<jittermethodlist>` / `<jitterattributelist>` lists and the thispatcher help patch. `ObjectDatabase.messages/attributes/selectors` merge it at call time, so `applyvalues`/`setvalue` are DB-legal on every real mc.* wrapper. `lookup()` output is unchanged.

## Commits

| Task | Commit | Message |
|------|--------|---------|
| 1 (tracer) | b85ec3be | feat(sync): --apply groups lands MC wrapper messages in groups.json; ObjectDatabase.messages merges them (Q14) |
| 2 | 4b89b475 | feat(db): Jitter/OB3D + thispatcher group profiles; ObjectDatabase.attributes/selectors (Q14) |
| 3 | 102e6786 | data(db): groups.json -- MC wrapper / Jitter / OB3D / thispatcher group names from Max 9.2.0 (Q14) |

## Figures

**Pytest**
- Base: 3171 passed, 1 xfailed, 1 xpassed, 29 warnings (63.4 s).
- Final: 3202 passed, 1 xfailed, 1 xpassed, 29 warnings (63.4 s). That is +31 new tests: 12 in TestGroups and 19 in tests/test_db_groups.py. No existing test was edited.
- Python 3.10 (`uv run --python 3.10`, `MAXPAT_TEST_MAX_APP=/nonexistent/Max.app`) over test_db_groups.py + test_sync_max_bundle.py: 117 passed, 1 skipped (the `requires_max` test).
- The `ast.parse(feature_version=(3, 10))` gate passes on all four changed .py files.
- `git status --porcelain` was unchanged across every pytest run.

**Dry-run delta**

Before (Q/sync-before.txt):
```
  inherited attrs : 53 group-page attributes unrecorded on 186 objects (report-only; --apply inherited --attributes NAME)
  groups          : 419 members (mc 163 / jit 256 / thispatcher 1), 62 profiles, +15216 names pending (--apply groups)
```
After (Q/sync-after.txt):
```
  inherited attrs : 0 group-page attributes unrecorded on 0 objects (report-only; --apply inherited --attributes NAME)
  groups          : 419 members (mc 163 / jit 256 / thispatcher 1), 62 profiles, +0 names pending (--apply groups)
  io compare      : 3091 names unchanged
```

**groups.json**
- Members by family: mc 163, jit 256, thispatcher 1. That is 419 members holding 420 profile memberships, because `mc.jit.peek~` carries both an mc and a jit profile.
- 62 profiles: jit 57, mc 4, thispatcher 1.
- 64 attribute_definitions.
- Names added: 15,216.
- Size: 4,038 lines, 81,515 bytes. Canonical serialization; sha256 `5430ce1a…a676`.
- A second `--apply groups` printed `unchanged` and produced the same sha.

**Report detail**
- undefined_attributes (39, selector-only): boundcalc, bounds, bz, bzname, dim, displaychan, drawbounds, fog_color, fog_density, fog_range, fun, gl_color, in2_/in3_ {dim, name, planecount, type}, material, out2_/out3_/out4_ {dim, name, planecount, type}, out_name, planecount, texanchor, texrotate, texzoom, two_sided.
- ambiguous_attributes: `name`.
- unresolved: none (0).
- help_read_errors: none.

**Other checks**
- Hashes of all 41 protected DB files (domain/package objects.json, overrides, aliases, relationships, package_info, pd-blocklist) match before and after.
- `git diff --stat base..HEAD -- .claude/max-objects` lists only groups.json and extraction-log.json.
- The shadowed-by-override report is still 5 objects.
- `--refresh-log` recorded `group_members: 419` and `pending_group_names: 0`.

## thispatcher

The measured set is 14 selectors and matches the planning prototype exactly: clean, dirty, dispose, front, fullscreen, loadbang, path, savewindow, script, setactivetab, title, wclose, window, write. `messages("thispatcher")` = the 5 own names followed by these.

## Deviations from Plan / Fix Plan

1. **[Fix-plan deviation] New `--apply groups` mode, not the bare `--apply inherited`.** `test_apply_needs_an_explicit_attribute_list` pins `--apply inherited` without `--attributes` to exit 2. The new mode shares the inherited path's scan and its group-page definitions.
2. **[Fix-plan deviation] thispatcher source is `help/max/thispatcher.maxhelp`, not `docs/userguide/content/controlling_max_with_messages.json`.** That JSON has no thispatcher section: it covers max/dsp/midi/jitter app messages, and its `wclose` is the DSP-window message. The user guide's scripting overview defers to the thispatcher help file. The source is recorded in the profile (`source: help/max/thispatcher.maxhelp`).
3. **[Rule 1 - Bug] Group membership no longer skips every `_is_doc_page` ref.** Found during Task 2 by comparing the dry run to the research probe: it gave jit 254 against the expected 256.
   - **Issue:** jit.graph and jit.plot are real Jitter DB objects (1 inlet / 2 outlets). Their refpages carry no inlet, outlet or method lists but do list 16 group names. Plan decision 3's `_is_doc_page` skip silently dropped them, so Q23 would later false-warn on their OB3D attributes.
   - **Fix:** skip only whitespace-named group pages. `locate_base_entry` still decides membership, and unresolved stayed 0.
   - **Test:** `test_doc_shaped_refpage_of_a_real_object_is_a_member` (RED before the fix).
   - **Files:** tools/sync_max_bundle.py, tests/test_sync_max_bundle.py. **Commit:** 4b89b475.
   - `compute_inherited` keeps its existing `_is_doc_page` skip (unchanged behaviour).
4. **RED-first note.** Four Task 2 writer and shrink tests (member removal, name loss, other paths, bundle shrink) already passed when first run, because Task 1 had implemented `write_groups_file` / `check_groups_additive` as planned. Every other new test failed first.
5. **Additions (Rule 2).** The groups report carries a `help_read_errors` key. `messages()` keeps the own list verbatim as a prefix and appends inherited names not already present, which is the "deduplicated in order" rule applied without touching own data.

## Out of scope / Deferred

- The Snapshot Messages group (`snapshot-group.maxref.xml`): no per-object list references it.
- thispatcher `script` subcommands and `window` flags (research open question 1): not stored.
- `define missing: jit.gl.grab, jit.gl.movie~`: pre-existing, unchanged.
- Message-name enforcement belongs to Q23, which should use `db.selectors()`.

## Doc impact (not edited, rule 8)

- `.claude/skills/references/max-9.2-changes.md` and `.claude/skills/references/shared-capabilities.md` mention `tools/sync_max_bundle.py`. They may want a line about `--apply groups` / `db.selectors()`.
- TECHNICAL.md and README.md have no sync-tool mention.

## MAX confirmation needed

None. This is data and tooling only: no patch was generated or edited.

## Known Stubs

None.

## Threat Flags

None. The new DB-tree writer is limited to `<db_root>/groups.json` and covered by T-v4k-01/02.

## Self-Check: PASSED

- FOUND: .claude/max-objects/groups.json, tests/test_db_groups.py, tools/sync_max_bundle.py, src/maxpat/db_lookup.py
- FOUND commits: b85ec3be, 4b89b475, 102e6786
- Stash list is empty both before and after (Q/stash-list-before.txt).
