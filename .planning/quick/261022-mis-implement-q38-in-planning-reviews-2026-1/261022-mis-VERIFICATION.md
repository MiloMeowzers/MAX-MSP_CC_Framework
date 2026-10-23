---
phase: quick-261022-mis
verified: 2026-10-22T00:00:00Z
status: passed
score: 7/7 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Quick 261022-mis (Q38): Verification Report

**Goal:** Implement Q38: idiom allowlist, objectfile aliases, version-aware I/O.
**Status:** passed
**Re-verification:** No, initial verification

## Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `--apply idioms` writes idioms.json from bundle help cords; additive, idempotent | VERIFIED | idioms.json holds 1237 sources and 10,122 pairs. The live dry-run prints `idioms: 10122 pairs from 49457 help cords (11750 excluded, 0 unclassified), +0 pending`. |
| 2 | Layer 3 never type/role-flags a listed cord; bounds still enforced; `replace_box_safe` rewires it | VERIFIED | `validation.py:1202-1208` runs the idiom check after the bounds check (out-of-bounds is flagged earlier, `:1165-1176`). `patcher.py:1479` mirrors it in `_rewire_type_gated`. `test_bundle_help_cords_are_never_flagged` and `test_listed_names_still_get_bounds_errors` pass. |
| 3 | 232 objectfile aliases added; 12 hand aliases kept; list.* overrides deleted; RNBO unaffected | VERIFIED | aliases.json has 244 entries. By target: jit.op 97, vz.* 90, zl.* 31, mc.* 13 (the shortcuts), plus hslider. Spot-checked in the live DB: `mc.times~` -> `mc.*~` (2 in, 1 out), `list.len` -> `zl.len`, `hslider` -> `slider`, `jit.+` -> `jit.op`, `4mixr` -> `vz.4mixr`. The only override starting with `list.` is `list.ease`. `test_objectfile_aliases`, `test_domain_scope` and `test_db_tooling` pass. |
| 4 | Every `min_version` is a string; extractors write "8"; nothing else changed | VERIFIED | Across 36 objects.json files the counts are "8" 3050, "8.1" 215, "9" 167, "9.2" 12, "4" 1, all `str`, none numeric. The cycle~ override is `"4"`. Both extractors write `"min_version": "8"`. `test_version_tags` passes. |
| 5 | `--apply version-io` writes version_io.json with the 8 predicted names; vst~/retune~ not fabricated | VERIFIED | version_io.json holds objects with evidence segments; the dry-run reports `8 names ... +0 -0 ~0`. mousestate, metro and live.meter~ were inspected. vst~ and retune~ are absent, as the plan allows. |
| 6 | `validate_patch(target_version=...)` adds warning-only `version` layer; None is a no-op; bad target raises ValueError | VERIFIED | Live check: target 9.0 and 9.0.3 warn that `jit.message` needs 9.2, and 9.2 is clean. mousestate outlet 9 warns at 9.0 and is clean at 9.0.5 and 9.2. All results are warnings. `"abc"` raises `ValueError: not a Max version string`. `validate_patch(p) == validate_patch(p, target_version=None)`. |
| 7 | Regression gate | VERIFIED | `final-pytest.txt` shows 6064 passed, 5 xfailed, 1 xpassed, rc 0 (baseline 6008 passed). I re-ran test_idioms, test_version_io, test_objectfile_aliases, test_version_tags and test_domain_scope: 206 passed. I re-ran test_db_tooling, test_sync_max_bundle and test_help_io: 245 passed. `git diff 3da1f6e0 549400aa -- patches patterns` is empty. `git stash list` is empty. No tracked files are dirty. |

## Key Links

| From | To | Status |
|------|----|--------|
| `sync_max_bundle` | `help_io.scan_*` | WIRED (dry-run output exercises both scans) |
| `db_lookup._load` | idioms.json / version_io.json | WIRED (`is_shipped_idiom`, `io_changes` and `min_version` return real data) |
| `validation` | `db.is_shipped_idiom` / `io_changes` / `min_version` | WIRED (live behavior confirmed above) |
| `patcher._rewire_type_gated` | `db.is_shipped_idiom` | WIRED (`patcher.py:1479`) |
| aliases / overrides guard | overrides `objects` | VERIFIED (guard test passes) |

## Anti-Patterns

No TBD, FIXME or XXX markers were added in tools/, src/, tests/ or .claude/scripts. No stubs were found: the miners and queries return real mined data.

## Notes for the user (not gaps)

- vst~ 4->8 and retune~ 3->5 are not in version_io.json. No bundle help box shows a version disagreement, and the DB already has the post-change I/O (vst~ 2/8, retune~ 3/5). This matches the must-have and Rule #1. The user can supply older-build evidence if a delta is wanted.
- metro and twist~ changes (9.3.0) are recorded but flagged `newer_than_installed`. They are inert until the installed Max reaches 9.3.
- 109 objectfile names remain unaliased by design (out of scope). The list is in `unaliased-109.json`.
- The help-io baseline was regenerated against the committed package set, excluding the newly installed Vision package. This is a documented deviation and is acceptable.

## Human Verification

None required. The plan changes no `.maxpat` files.

---
_Verified: 2026-10-22_
_Verifier: Claude (gsd-verifier)_
