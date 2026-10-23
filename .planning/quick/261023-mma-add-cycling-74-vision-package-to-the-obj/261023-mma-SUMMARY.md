---
phase: quick-261023-mma
plan: 01
status: complete
subsystem: object-db
tags: [object-db, packages, jitter, vision, max-9.2]
requires: []
provides:
  - "packages/Vision/objects.json: 22 jit.vis.* entries (12 refpage objects + 10 helpers)"
  - "package_info.json Vision entry (community, prefix jit.vis., installed, object_count 22)"
affects:
  - "Rule #1 gate (Patcher.add_box) and validate_patch now accept jit.vis.* objects"
tech-stack:
  added: []
  patterns:
    - "User-installed package path: extract_objects.py --package NAME, then scratch-script curation (help boxes win on outlet types)"
    - "max define / objectfile names are their own package entries (jit.gl.tex2mat precedent), never aliases"
key-files:
  created:
    - .claude/max-objects/packages/Vision/objects.json
  modified:
    - .claude/max-objects/package_info.json
    - .claude/max-objects/extraction-log.json
    - tests/test_db_lookup.py
    - CLAUDE.md
    - .claude/skills/references/db-maintenance.md
    - .claude/max-objects/PACKAGES.md
decisions:
  - "VIS-03: no aliases.json / groups.json entries; inherited Jitter method/attribute names inlined per entry; jit.vision and jit.vision.track kept out of the DB"
  - "VIS-04: idioms.json untouched -- --apply idioms mines bundle help only; impact low (every Vision port is control class)"
  - "Help-io baseline restored, not regenerated: regeneration also picked up unrelated FluCoMa 1.0.9 -> 1.0.10 drift"
  - "Every Vision entry is verified false until jit.vis.* objects are confirmed in MAX 9.2"
metrics:
  duration: "~12 min"
  completed: 2026-10-23
estimate:
  tokens: 90000
  tasks: 3
actuals:
  tokens: 16800
  tasks: 3
  commits: 4
plan_head_before: 78cdd6d282bee3ee77ca6c1a3d8f17ce196add8c
plan_head_after: cfcbc40d5337d40bd439b32cb0c3622e99e4f94c
---

# Phase quick-261023-mma Plan 01: Vision package in the object DB Summary

Cycling '74 Vision 1.0.2 (Max 9.2+) is now in the object DB: 22 `jit.vis.*` entries (12 refpage trackers/processors plus 10 v8-define, bpatcher and abstraction helpers) with help-box-verified I/O. Rule #1 and `validate_patch` now accept a `jit.grab -> jit.vis.hands -> jit.vis.hands.parts` chain with zero errors.

## What was built

**Task 1 (tracer, commit 18539243):** `python3 .claude/scripts/extract_objects.py --package Vision` wrote the 12 refpage entries, the Vision `package_info.json` block and the merged extraction log. Curation by scratch script:
- min_version "8" -> "9.2"; verified true -> false; rnbo_compatible false.
- Last (dumpout) outlet -> type `control`, digest `dumpout` (the help boxes save `""`; the refpage said matrix/dictionary/dumpout). Outlet 0 stays `matrix`, except posemap's `control`. The dict outlets and gesture's symbol outlet keep their refpage types.
- Refpage `<jittermethodlist>` names were appended to each entry's `messages`. The `<jitterattributelist>` names were added to `attributes`: outputmode/adapt int, out_name symbol.
- package_info.json: prefix `jit.` -> `jit.vis.`, `"installed": true`. The diff touches only the Vision block.
- Tracer check passed: jit.grab plus getskeleton/outputmatrix/bang message boxes into jit.vis.hands gave zero validation findings. A bogus `foobarbaz` message is still flagged, so the selector check is live.

**Task 2 (TDD, RED 42bbe8c3, GREEN 8bcbecb9):** 10 helper entries, purely additive (the patience diff is +851/-0; the 12 Task 1 entries are byte-unchanged):

| Entry | I/O | Basis |
|---|---|---|
| jit.vis.hands.parts / .left (@row 0) / .right (@row 1) | 1/7 | `v8 jit.vis.parts.js hands`: wrist, thumb, index, middle, ring, little + dump |
| jit.vis.body.parts | 1/7 | head, torso, left_arm, right_arm, left_leg, right_leg + dump |
| jit.vis.face.parts | 1/6 | left_eye, right_eye, nose, lips, contour + dump |
| jit.vis.facemesh.parts | 1/9 | lips, left_eye, left_eyebrow, right_eye, right_eyebrow, face_oval, left_iris, right_iris + dump |
| jit.vis.holistic.parts | 1/5 | body, face, left_hand, right_hand + dump |
| jit.vis.debugdraw | 1/1 | `v8 jit.vis.draw.js`; attrs drawto, layer, enable, point_size, line_width, pointcolor, linecolor |
| jit.vis.grab | 1/1 | bpatcher `jit-vis-grab-ui.maxpat`, 250x55 |
| jit.vis.tondc | 1/1 | abstraction `patchers/jit.vis.tondc.maxpat` (unpack -> jit.gen -> pack, to NDC) |

The parts helpers have messages `jit_matrix`/`getparts`/`getjoints` and attributes row/detected/planecount. The package_info object_count is 22.

**Task 3 (commit cfcbc40d):**
- CLAUDE.md gained a Version Compatibility bullet; the file is now 29645 of 30000 bytes.
- db-maintenance.md gained a "User-installed packages" paragraph.
- PACKAGES.md lists Vision under Community.

## Verification

- Help-io oracle: no `jit.vis.*` name is unresolved or mismatching under `package:Vision`. 19 names were unresolved before this change; `gswitch2` is the only one left, and it was already unresolved.
- `audit_empty_io` / `audit_half_empty_io`: the before and after snapshots are identical, and neither contains a `jit.vis.*` name.
- The default `tools/audit_db.py` report lists no `jit.vis.*` name anywhere.
- Throwaway in-memory patch `qmetro 33 -> jit.grab -> jit.vis.hands -> jit.vis.hands.parts`: zero errors and zero findings. Nothing was saved to the repo.
- `tests/test_help_io.py` and `tests/test_package_schema.py`: 102 passed. `tests/test_claude_md.py`: 336 passed.
- **Full pytest:** the baseline was 7504 passed, 1 skipped, 4 xfailed. After the change it is 7529 passed, 1 skipped, 4 xfailed: the baseline plus exactly the 25 new `test_vision_*` tests, with no new failures.
- Sync dry-run (`tools/sync_max_bundle.py --json`): the string "jit.vis" does not occur in the output. This shows the sync tool never sees the user package (VIS-03/VIS-04 evidence).

## Deviations from Plan

None that change behaviour. Notes:
- The help-io baseline (`tests/fixtures/help_io_baseline.json`) was **restored, not regenerated**. Regenerating it also changed `package:FluidCorpusManipulation` (version 1.0.9 -> 1.0.10, +8 boxes) and the `comment` box count (+4). That is unrelated drift in installed packages. The Vision part alone would have raised `package:Vision` boxes_compared from 607 to 646.
- The plan's verify one-liner filters on `x.rule == 'message_selector'`, but validation results carry no `rule` field. The zero-findings result was cross-checked with a negative control instead (`foobarbaz` is flagged as a domain warning).
- The plan's commit ledger file under the git dir could not be written, because the sandbox blocks git-dir paths. The commit count was measured with `git rev-list --count 78cdd6d2..HEAD` = 4.

## Gaps and deliberate exclusions

- **Idioms gap (VIS-04):** `tools/sync_max_bundle.py` (and `tools/help_io.scan_help_idioms` under it) scans only the app bundle. So Vision help cords cannot enter `idioms.json` through the sanctioned path, and `idioms.json` is untouched. The impact is low: every Vision port is control class, so Layer 3 has no signal/control mismatch to excuse.
- **VIS-03 decision:** `aliases.json` and `groups.json` have no Vision entries. groups.json is written only by the bundle scan, and `check_groups_additive` would abort a later sync that drops hand-added members. Each define/objectfile `jit.vis.*` name is its own entry. `jit.vision` and `jit.vision.track` are deliberately absent: they have no refpage and no help box, and their I/O depends on the mode argument.
- **Not covered:**
  - `patchers/jit.vis.models.maxpat` (the model-manager UI, which has no help box)
  - `patchers/examples/*`
  - `jit.vis.web.track.js` (internal to an example)
- **jit.vis.gesture** has no `<jittermethodlist>` in its refpage, so its messages are only `calibrate`. A `jit_matrix` input arrives by cord, so validation is unaffected, but a message box sending e.g. `bang` to it would raise a selector warning.
- **Out-of-scope help-io mismatches** in the Vision help (non-Vision objects, saved by Max 9.3.0): `dict.unpack` with N args saves 1/N+1 vs DB 1/2, `jit.gl.environment` saves 1/2 vs DB 2/2, and `jit.glue @columns 6` saves 6/2 vs DB 4/2. Not fixed here.
- **Unverified in MAX:** every Vision entry is `verified: false` until the user confirms the jit.vis.* objects in MAX 9.2.

## Known Stubs

None.

## Threat Flags

None. Package files were read only as JSON/XML/text, with `python3 -I` for direct reads of package data. No package JS was executed, and overrides.json, groups.json, aliases.json and idioms.json were not written.

## Self-Check: PASSED

- FOUND: .claude/max-objects/packages/Vision/objects.json (22 entries)
- FOUND commits: 18539243, 42bbe8c3, 8bcbecb9, cfcbc40d
