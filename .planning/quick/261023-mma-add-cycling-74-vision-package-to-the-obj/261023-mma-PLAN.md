---
phase: quick-261023-mma
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .claude/max-objects/packages/Vision/objects.json
  - .claude/max-objects/package_info.json
  - .claude/max-objects/extraction-log.json
  - tests/test_db_lookup.py
  - tests/fixtures/help_io_baseline.json
  - CLAUDE.md
  - .claude/skills/references/db-maintenance.md
  - .claude/max-objects/PACKAGES.md
autonomous: true
requirements: [VIS-01, VIS-02, VIS-03, VIS-04, VIS-05, VIS-06, VIS-07]

estimate:
  tokens: 90000
  raw_tokens: 90000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "All 12 refpage objects resolve through ObjectDatabase().lookup() with non-empty I/O: jit.vis.hands/body/face/facemesh/holistic/text/objectdetect/posemap 1 in / 3 out, jit.vis.gesture 1/4, jit.vis.segment/depth/bgsubtract 1/2. Each has package Vision, domain Packages, min_version \"9.2\", verified false and rnbo_compatible false"
    - "The 10 helpers (jit.vis.hands.parts, .left, .right, body.parts, face.parts, facemesh.parts, holistic.parts, debugdraw, grab, tondc) resolve as their own entries, never as v8, with the I/O MAX saves in the Vision help boxes"
    - "Patcher.add_box accepts jit.vis.hands and jit.vis.hands.parts. A jit.grab -> jit.vis.hands -> jit.vis.hands.parts patch validates with zero errors, so Rule #1 and bounds both hold"
    - "A message box sending getskeleton, outputmatrix or bang into jit.vis.hands raises no message_selector warning"
    - "The help-io oracle reports no unresolved and no mismatching jit.vis.* name for source package:Vision"
    - "get_effective_restrictions() is [] for every Vision name, and audit_empty_io() / audit_half_empty_io() list no jit.vis.* name"
    - "The full pytest suite passes at baseline plus the new Vision tests, with no new failures, and CLAUDE.md stays within its 30000-byte budget"
  artifacts:
    - path: ".claude/max-objects/packages/Vision/objects.json"
      provides: "22 Vision entries (12 refpage objects + 10 helpers)"
      contains: "jit.vis.hands.parts"
    - path: ".claude/max-objects/package_info.json"
      provides: "Vision registry entry (tier community, extracted true, installed true, object_count 22)"
      contains: "\"Vision\""
    - path: "tests/test_db_lookup.py"
      provides: "Vision lookup / I/O / define-name tests"
      contains: "def test_vision_"
    - path: "CLAUDE.md"
      provides: "Version Compatibility line for Vision (Max 9.2, unverified)"
      contains: "jit.vis."
  key_links:
    - from: ".claude/max-objects/packages/Vision/objects.json"
      to: "src/maxpat/db_lookup.py ObjectDatabase packages/ loader"
      via: "per-package directory scan (DOMAIN_LOAD_ORDER 'packages')"
      pattern: "packages/Vision"
    - from: ".claude/max-objects/package_info.json Vision entry"
      to: "src/maxpat/validation.py package_not_extracted check"
      via: "tier community + extracted true suppresses the not-extracted warning"
      pattern: "\"extracted\": true"
    - from: "Vision entries' own messages/attributes"
      to: "src/maxpat/validation.py _check_message_selectors"
      via: "db.selectors(name) includes the refpage jittermethodlist / jitterattributelist names"
      pattern: "outputmatrix"
---

<objective>
Add the Cycling '74 Vision package (v1.0.2, Max 9.2+, installed at the external path ~/Documents/Max 9/Packages/Vision) to the object DB, so its jit.vis.* objects pass Rule #1 and validation in generated patches.

Requirement IDs map to the task_spec items:
- VIS-01: the 12 refpage objects
- VIS-02: the helpers
- VIS-03: an aliases/groups decision for jit.vision / jit.vision.track and the define names
- VIS-04: idioms
- VIS-05: verification
- VIS-06: tests
- VIS-07: the CLAUDE.md line

Planning findings that drive the approach (verified while planning; do not re-derive them):
- The sync tool scans only the app bundle: `tools/sync_max_bundle.py` reads `Contents/Resources/C74` and `C74/packages/*`. That covers `parse_define_mappings`, `parse_objectfile_mappings`, `package_docs_dirs`, `build_help_index` and, through `tools/help_io.scan_help_idioms`, the idioms scan. It never reads ~/Documents/Max 9/Packages, so none of its `--apply new|define|aliases|groups|idioms` steps can reach Vision.
- The sanctioned user-package path is `python3 .claude/scripts/extract_objects.py --package Vision`. A scratch-output probe while planning confirmed what it does:
  - It finds the package automatically and parses all 12 refpages, writing `packages/Vision/objects.json` (sorted keys, indent 2, ensure_ascii False, trailing newline, the same style as the sibling package files).
  - It appends a Vision block to `package_info.json` with that file's style intact (only the new block changes).
  - It merges `extraction-log.json`.
  - On a re-run, existing entries win, so curation survives.
  - Its output needs curation: it writes min_version "8", verified true and prefix "jit.", and it takes dumpout types from the refpage.
- Existing define-mapped helpers are entries in their own package file, not overrides and not aliases. Precedents: `jit.gl.tex2mat` (`max define jit.gl.tex2mat v8 ...`) in packages/Jitter Tools/objects.json, and `jit.gl.web` in jitter/objects.json. Vizzie bpatcher modules carry `maxclass: bpatcher`, `abstraction_file`, `bpatcher_dimensions`.
- Help-box evidence (outlettype as MAX saved it):
  - Trackers (hands, body, face, facemesh, holistic, objectdetect, text): 1/3 `["jit_matrix","",""]`
  - gesture: 1/4 `["jit_matrix","","",""]`
  - posemap: 1/3 `["","",""]`
  - segment, depth, bgsubtract: 1/2 `["jit_matrix",""]`
  - Parts helpers (all outlets ""): hands.parts 1/7, hands.parts.left 1/7, body.parts 1/7, face.parts 1/6, facemesh.parts 1/9, holistic.parts 1/5
  - debugdraw: 1/1
  - jit.vis.grab: saved as a bpatcher of `jit-vis-grab-ui.maxpat`, 1/1 `["jit_matrix"]`, rect 250x55
  - jit.vis.tondc: an abstraction in the package's patchers/ folder, 1/1 `["jit_matrix"]`, used by 8 help boxes
- Today the live help-io scan lists 19 jit.vis.* names as unresolved under source package:Vision, jit.vis.tondc among them. The only non-Vision unresolved name there is gswitch2.
- groups.json is written only by `--apply groups`, which scans the bundle. Its `check_groups_additive` would abort a later sync that drops hand-added members. So the inherited Jitter names a Vision refpage lists go into each entry's own `messages` / `attributes`, not into groups.json. The refpage lists are `<jittermethodlist>` (bang, clear, exportattrs, exportsummary, getattributes, getstate, importattrs, jit_matrix, outputmatrix, summary) and `<jitterattributelist>` (outputmode, adapt, out_name).
- CLAUDE.md is 29523 bytes against `CLAUDE_BUDGET_BYTES = 30_000` in tests/test_claude_md.py: only about 470 bytes are free.

Purpose: Rule #1 currently blocks every jit.vis.* object. `Patcher().add_box('jit.vis.hands')` raises "Unknown object", so no generated patch can use the package.
Output: packages/Vision/objects.json (22 entries), the Vision package_info.json entry, Vision tests, and doc lines in CLAUDE.md, db-maintenance.md and PACKAGES.md.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@CLAUDE.md
@.claude/skills/references/db-maintenance.md

External, read-only inputs (third-party data: read as JSON/XML only, never execute):
- Vision package: ~/Documents/Max 9/Packages/Vision
  - `docs/*.maxref.xml` (12 refpages)
  - `help/*.maxhelp` (17 help patches)
  - `init/vision-object-mappings.txt` (the define/objectfile lines)
  - `code/jit.vis.parts.js` (inlets = 1; outlets = parts + 1; attributes row/detected/planecount; methods jit_matrix/getparts/getjoints)
  - `code/jit.vis.skeleton.js` (part names per tracker)
  - `code/jit.vis.draw.js` (v8 default 1/1; attributes layer/enable/point_size/line_width/pointcolor/linecolor, plus drawto via `implicit.context.js` `register_drawto`)
  - `patchers/jit-vis-grab-ui.maxpat` (inlet "0/1 to toggle, messages to jit.grab"; outlet "jit.grab output")
  - `patchers/jit.vis.tondc.maxpat` (`jit.unpack` -> `jit.pack`; 1 inlet, 1 outlet)
- Scratch directory for throwaway scripts and reports (external, session-only; referred to below as SCRATCH): /private/tmp/claude-501/-Users-taylorbrook-Dev-MAX/3e7bc973-ea45-4855-b55d-42be382c3118/scratchpad

Repo sources to consult (read once, grep for detail):
- .claude/scripts/extract_objects.py: `--package` mode, `update_package_registry`
- tools/sync_max_bundle.py: `_scan_refpage_file`, `outlet_from_help`, `parse_define_mappings`
- src/maxpat/atomic_io.py: `json_style`, `atomic_write_bytes`
- .claude/max-objects/packages/Jitter Tools/objects.json: the `jit.gl.tex2mat` entry is the template for a v8-define helper
- .claude/max-objects/packages/Vizzie/objects.json: `vz.4mixr` is the template for a bpatcher helper
- .claude/max-objects/groups.json: `attribute_definitions` types outputmode and adapt as int (jit.group-mop)
- tests/test_db_lookup.py: module-level test style
- tests/test_claude_md.py: byte budget and private-path checks
</context>

<tasks>

<task type="tracer">
  <name>Task 1: Tracer — extract Vision with the package extractor, curate the 12 refpage entries, prove jit.grab -> jit.vis.hands validates</name>
  <files>.claude/max-objects/packages/Vision/objects.json, .claude/max-objects/package_info.json, .claude/max-objects/extraction-log.json</files>
  <read_first>
    - .claude/skills/references/db-maintenance.md: "Refpage placeholders: counts vs types" (when the help box and the refpage disagree on a type, the help box wins) and "min_version is always a string"
    - .claude/scripts/extract_objects.py lines 1227-1345 (registry update) and 1416-1460 (--package flow)
    - ~/Documents/Max 9/Packages/Vision/init/vision-object-mappings.txt
  </read_first>
  <action>
Pre-flight (before any edit; keep every output in SCRATCH, never in the quick dir):
1. Record `git rev-parse HEAD` and `git stash list`.
2. Capture the baseline test summary: run `python3 -m pytest -q` in the background with a 600000 ms timeout and keep its last 3 lines as SCRATCH/baseline-pytest.txt. The last recorded figure was 7504 passed, 1 skipped, 4 xfailed.
3. Save a before-snapshot of the DB audits to SCRATCH/io-audit-before.json: dump `ObjectDatabase().audit_empty_io()` and `audit_half_empty_io()` as sorted JSON from a `python3 -c` one-liner, with warnings silenced.
4. Run the sync dry-run, `python3 tools/sync_max_bundle.py --json SCRATCH/sync-dryrun.json`, and confirm "jit.vis" occurs nowhere in that JSON. This is the recorded proof for VIS-03/VIS-04 that the sync tool's define, objectfile, aliases, groups and idioms scans never see the user package.

Extraction (the sanctioned user-package path, run from the repo root so the default `--output .claude/max-objects` applies):
5. Run `python3 .claude/scripts/extract_objects.py --package Vision --dry-run`, then the same command without `--dry-run`. Expect "Wrote 12 objects", "Added package_info.json entry: Vision (count=12)" and a merged extraction log.
6. Check `git diff --stat .claude/max-objects/package_info.json`: it must show only an added block of about 10 lines. If any other package's lines changed, restore the file from HEAD and add the Vision block by hand (step 9 rules).

Curation of packages/Vision/objects.json:
- Use one throwaway Python script saved in SCRATCH and run with cwd at the repo root. Never cd into the package directory. It loads the JSON, mutates it and writes it back.
- Do not route this through `sync_max_bundle.write_db_file`: its additive check refuses changed fields, and this file is new in this task.

7. For every one of the 12 entries:
   - Set min_version to the string "9.2" (the extractor writes "8"). Set verified false and rnbo_compatible false, per the task spec.
   - Keep maxclass newobj, module jit, domain Packages, category "Jitter Vision", package Vision, variable_io false and arguments [] exactly as the extractor wrote them.
   - Outlet types follow the help boxes, which win over the refpage:
     - Outlet 0 stays "matrix" wherever the help box saves jit_matrix, which is all except posemap. posemap outlet 0 stays "control" (help saves "").
     - Every dumpout outlet becomes type "control" with digest "dumpout": trackers id 2, gesture id 3, segment/depth/bgsubtract id 1. The help box saves "" there, which overrides the refpage's matrix, dictionary or dumpout.
     - Dictionary outlets keep the refpage's "dict", and gesture outlet 2 keeps "symbol". Help "" is control class, so these refine the help type rather than contradict it.
   - Leave inlets as extracted: one "matrix" inlet, hot true.
8. Inherited Jitter names (VIS-03 decision): for each entry, re-read its own refpage with ElementTree.
   - Append the `<jittermethodlist>` names to `messages` after the existing methodlist names, de-duplicated, in refpage order.
   - Add each `<jitterattributelist>` name to `attributes` without touching existing keys:
     - outputmode and adapt as `{"type": "int", "get": true, "set": true}` (the groups.json attribute_definitions types)
     - out_name as `{"type": "symbol", "get": true, "set": true}`
   - Do not edit groups.json or aliases.json. jit.vision and jit.vision.track get no entry and no alias:
     - no help box uses them
     - they have no refpage
     - their I/O depends on a mode argument
     - every jit.vis.* define or objectfile name is an entry in its own right, as with jit.gl.web and jit.gl.tex2mat
9. Write the file sorted by key, indent 2, ensure_ascii False, with a trailing newline. Assert `json_style(raw, data) == (False, True)` and sorted keys after the write.
10. Fix the package_info.json Vision entry:
    - Set prefix to "jit.vis." (the extractor inferred "jit.").
    - Add "installed": true after "extracted", matching the key order of other entries.
    - Set object_count to the entry count of packages/Vision/objects.json (12 for now).
    - Edit only the Vision dict. Reload the file with json (insertion order kept) and dump with indent 2, ensure_ascii False and a trailing newline. `git diff` must show only the Vision block.

Tracer check, end-to-end through every layer (extractor output -> DB loader -> Rule #1 gate in Patcher.add_box -> validate_patch, including the selector check): build an in-memory Patcher with these connections, all into inlet 0 of jit.vis.hands, then run validate_patch on it:
- jit.grab outlet 0 -> jit.vis.hands
- message box getskeleton -> jit.vis.hands
- message box outputmatrix -> jit.vis.hands
- message box bang -> jit.vis.hands

Commit with explicit paths only: `git add` the three files listed in files, then `git commit -m "feat(quick-261023-mma): extract Vision package refpage objects into the object DB"`. No `git add -A`, no `git stash`.
  </action>
  <verify>
    <automated>python3 -c "import warnings; warnings.simplefilter('ignore'); from src.maxpat.db_lookup import ObjectDatabase as D; d=D(); E={'hands':(1,3),'body':(1,3),'face':(1,3),'facemesh':(1,3),'holistic':(1,3),'text':(1,3),'objectdetect':(1,3),'posemap':(1,3),'gesture':(1,4),'segment':(1,2),'depth':(1,2),'bgsubtract':(1,2)}; bad=[k for k,v in E.items() if (lambda o,n: o is None or d.compute_io_counts(n,[])!=v or o['package']!='Vision' or o['min_version']!='9.2' or o['verified'] is not False or o['rnbo_compatible'] is not False or d.get_effective_restrictions(n)!=[] or o['outlets'][-1]['type']!='control')(d.lookup('jit.vis.'+k),'jit.vis.'+k)]; print('bad', bad); assert not bad"</automated>
    <automated>python3 -c "import warnings; warnings.simplefilter('ignore'); from src.maxpat import Patcher; from src.maxpat.validation import validate_patch; p=Patcher(); g=p.add_box('jit.grab'); h=p.add_box('jit.vis.hands'); p.add_connection(g,0,h,0); [p.add_connection(p.add_message(t),0,h,0) for t in ('getskeleton','outputmatrix','bang')]; r=validate_patch(p); bad=[(x.level,x.message) for x in r if x.level=='error' or getattr(x,'rule',None)=='message_selector']; print(bad); assert not bad"</automated>
    <automated>python3 -c "import json; from src.maxpat.atomic_io import json_style; p='.claude/max-objects/packages/Vision/objects.json'; raw=open(p,'rb').read(); d=json.loads(raw); assert json_style(raw,d)==(False,True) and list(d)==sorted(d); i=json.load(open('.claude/max-objects/package_info.json'))['Vision']; assert i['tier']=='community' and i['prefix']=='jit.vis.' and i['extracted'] is True and i['installed'] is True and i['object_count']==len(d), i; print('style+registry ok', len(d))"</automated>
  </verify>
  <done>
- `Patcher.add_box('jit.vis.hands')` no longer raises. The 12 refpage names resolve with the expected I/O, min_version "9.2", verified false and restrictions [].
- The jit.grab -> jit.vis.hands patch with getskeleton/outputmatrix/bang messages validates with zero errors and zero message_selector warnings.
- The package_info.json diff touches only the Vision block.
- The baseline and the before-snapshots are saved in SCRATCH, and the commit holds only the three listed files.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Add the 10 helper entries test-first, then run the help-io, audit and throwaway-patch verification</name>
  <files>tests/test_db_lookup.py, .claude/max-objects/packages/Vision/objects.json, .claude/max-objects/package_info.json, tests/fixtures/help_io_baseline.json</files>
  <read_first>
    - tests/test_db_lookup.py (top imports and one module-level test, for style)
    - ~/Documents/Max 9/Packages/Vision/code/jit.vis.parts.js lines 1-60 and 200-250
    - ~/Documents/Max 9/Packages/Vision/code/jit.vis.skeleton.js (parts arrays)
    - ~/Documents/Max 9/Packages/Vision/code/jit.vis.draw.js lines 1-30 and 160-205
    - the jit.gl.tex2mat entry in .claude/max-objects/packages/Jitter Tools/objects.json and the vz.4mixr entry in .claude/max-objects/packages/Vizzie/objects.json
  </read_first>
  <behavior>
    - test_vision_refpage_objects_resolve, parametrized over the 12 refpage names with the counts from Task 1's verify:
      - lookup is not None; package Vision; domain Packages; min_version "9.2"; verified False; rnbo_compatible False
      - compute_io_counts(name, []) equals the expected pair; get_effective_restrictions(name) == []
      - outlet 0 type is "matrix", except posemap's "control"; the last outlet type is "control"
    - test_vision_helpers_resolve, parametrized:
      - expected counts: jit.vis.hands.parts (1,7), jit.vis.hands.parts.left (1,7), jit.vis.hands.parts.right (1,7), jit.vis.body.parts (1,7), jit.vis.face.parts (1,6), jit.vis.facemesh.parts (1,9), jit.vis.holistic.parts (1,5), jit.vis.debugdraw (1,1), jit.vis.grab (1,1), jit.vis.tondc (1,1)
      - lookup(name)["name"] == name, not "v8"; package Vision; inlets and outlets non-empty
    - test_vision_define_names_are_own_entries:
      - jit.vis.hands (a `max define` of jit.vision.track handpose) and jit.vis.hands.parts.left (a `max define` of v8 jit.vis.parts.js hands @row 0) resolve to their own Vision entries
      - the .left entry's outlet count (7) differs from lookup("v8")
      - db.exists("jit.vision.track") is False (deliberately absent, see the VIS-03 decision)
    - test_vision_selectors_include_inherited_jitter_names: db.selectors("jit.vis.hands") contains getskeleton, outputmatrix, bang and adapt
    - test_vision_package_info_count: get_package_info("Vision") has tier community and extracted True; its object_count equals len(get_package_objects("Vision")) and equals 22
  </behavior>
  <action>
RED:
1. Append the five behaviours above to tests/test_db_lookup.py as module-level tests. Every function name starts with `test_vision_`. Use one module-scoped ObjectDatabase fixture, or the file's existing pattern if it has one, and keep the file's import style.
2. Run `python3 -m pytest tests/test_db_lookup.py -q -k vision`. The helper, define-name and package-count tests must fail; the Task 1 refpage and selector tests should already pass.
3. Commit the tests alone with explicit paths: `test(quick-261023-mma): add failing Vision helper tests`.

GREEN (VIS-02): add the 10 helper entries to packages/Vision/objects.json.
- Placement: the package file, the same home as the jit.gl.tex2mat v8 define helper. Never overrides.json, never an alias to v8.
- Use the same scratch-script method and write rules as Task 1 steps 7-9: sorted keys, `json_style == (False, True)`, existing 12 entries byte-unchanged.
- Each entry follows the key order of the extracted tracker entries:
  - maxclass newobj (grab: bpatcher), module jit, domain Packages, category "Jitter Vision", package Vision
  - min_version "9.2", verified false, rnbo_compatible false, variable_io false, arguments []
  - tags ["Jitter", "Vision"], and seealso naming the parent tracker
  - inlet 0 `{"id": 0, "type": "matrix", "signal": false, "digest": ..., "hot": true}`
  - digest/description: say what the helper does, and put the defining mapping line in the description (for example `max define jit.vis.hands.parts v8 jit.vis.parts.js hands;`), as the jit.gl.web digest does
- Parts helpers (`v8 jit.vis.parts.js <kind>`):
  - one "matrix" outlet per part, digest "<part> (jit_matrix)" from jit.vis.skeleton.js, then a last "control" outlet with digest "dump: getparts, getjoints"
  - messages ["jit_matrix", "getparts", "getjoints"]
  - attributes row, detected and planecount, each `{"type": "int", "get": true, "set": true}`
  - The help boxes save "" for every v8 outlet. That is control class, so "matrix" refines it with the code's setoutletassist evidence instead of contradicting it.
  - Part lists:
    - hands (also .left = `@row 0` and .right = `@row 1`): wrist, thumb, index, middle, ring, little
    - body: head, torso, left_arm, right_arm, left_leg, right_leg
    - face: left_eye, right_eye, nose, lips, contour
    - facemesh: lips, left_eye, left_eyebrow, right_eye, right_eyebrow, face_oval, left_iris, right_iris
    - holistic: body, face, left_hand, right_hand
- jit.vis.debugdraw (`v8 jit.vis.draw.js`):
  - inlet: the pose matrix
  - one "control" outlet: the unused v8 default outlet, which the help saves as ""
  - messages ["jit_matrix"]
  - attributes:
    - drawto symbol
    - layer int, enable int
    - point_size, line_width, pointcolor and linecolor float32
- jit.vis.grab (`bpatcher @name jit-vis-grab-ui.maxpat`), following the vz.4mixr template:
  - maxclass "bpatcher"
  - inlet 0 type "control", hot true, digest "0/1 to toggle, messages to jit.grab"
  - outlet 0 "matrix", digest "jit.grab output"
  - messages ["int", "anything"] (the inlet forwards to jit.grab)
  - attributes {}
  - after the shared keys: "abstraction_file": "patchers/jit-vis-grab-ui.maxpat" and "bpatcher_dimensions": [250.0, 55.0]
- jit.vis.tondc (an abstraction in the package's patchers/ folder, used by 8 help boxes; covered because the goal is every jit.vis.* object a generated patch would use):
  - newobj, matrix inlet, matrix outlet
  - read patchers/jit.vis.tondc.maxpat to describe the conversion in the digest
  - messages ["jit_matrix"], attributes {}
  - "abstraction_file": "patchers/jit.vis.tondc.maxpat"
- Out of scope, list them in the SUMMARY: patchers/jit.vis.models.maxpat (the package launcher's model-manager UI, no help box), the patchers/examples/*, and jit.vis.web.track.js (internal to an example).
- Raise package_info.json Vision object_count to 22 with the Task 1 step 10 rules.
- Run the -k vision tests again: all green.

VERIFY (VIS-04/VIS-05):
1. Run the help-io check from the verify block below. No jit.vis.* name may remain unresolved or mismatching under package:Vision; gswitch2 staying unresolved is pre-existing.
2. Regenerate the help-io baseline: `python3 tools/audit_db.py --help-io --write-baseline tests/fixtures/help_io_baseline.json`, then inspect `git diff tests/fixtures/help_io_baseline.json`.
   - Keep it only if the changes are confined to the package:Vision source stats and the totals (boxes_compared and friends).
   - If any other source or name changed (unrelated drift in installed packages), restore it with `git checkout -- tests/fixtures/help_io_baseline.json` and record the drift in the SUMMARY.
3. Run the after-snapshot of audit_empty_io / audit_half_empty_io and diff it against SCRATCH/io-audit-before.json. No jit.vis.* name may appear, and nothing new may be critical.
4. Run `python3 tools/audit_db.py --json SCRATCH/audit-after.json` and confirm no jit.vis.* name sits in any missing, unresolved or empty-io list.
5. Throwaway patch (spec item 5): save a script in SCRATCH that builds an in-memory Patcher, `qmetro 33` -> jit.grab -> jit.vis.hands outlet 0 -> jit.vis.hands.parts inlet 0, and runs validate_patch. It must report zero errors. Do not save a .maxpat into the repo.

Idioms gap (VIS-04): `--apply idioms` mines bundle help only, so Vision help cords cannot enter idioms.json through the existing path. Leave idioms.json untouched and record the gap in the SUMMARY. Its impact is low: every Vision port is control class, so Layer 3 has no signal/control mismatch to excuse.

Commit with explicit paths: objects.json, package_info.json, tests/test_db_lookup.py, plus the baseline if kept. Message: `feat(quick-261023-mma): add Vision helper objects (parts, debugdraw, grab, tondc)`.
  </action>
  <verify>
    <automated>python3 -m pytest tests/test_db_lookup.py -q -k vision</automated>
    <automated>python3 -c "import warnings; warnings.simplefilter('ignore'); from tools import audit_db; s=audit_db.run_help_io(max_app=audit_db.DEFAULT_MAX_APP)['help_io']; u=[n for n in s['unresolved'].get('package:Vision',{}) if n.startswith('jit.vis')]; m=[n for n in s['mismatches'].get('package:Vision',{}) if n.startswith('jit.vis')]; print('unresolved',u,'mismatch',m); assert not u and not m"</automated>
    <automated>python3 -c "import warnings; warnings.simplefilter('ignore'); from src.maxpat import Patcher; from src.maxpat.validation import validate_patch; p=Patcher(); q=p.add_box('qmetro',['33']); g=p.add_box('jit.grab'); h=p.add_box('jit.vis.hands'); s=p.add_box('jit.vis.hands.parts'); p.add_connection(q,0,g,0); p.add_connection(g,0,h,0); p.add_connection(h,0,s,0); r=validate_patch(p); e=[x.message for x in r if x.level=='error']; print(e); assert not e"</automated>
    <automated>python3 -m pytest tests/test_help_io.py tests/test_package_schema.py -q</automated>
  </verify>
  <done>
- All `test_vision_*` tests pass after a recorded red run.
- packages/Vision/objects.json holds 22 entries, and the 12 Task 1 entries are unchanged.
- package_info.json reports object_count 22.
- The help-io scan shows no unresolved and no mismatching jit.vis.* name.
- The throwaway jit.grab -> jit.vis.hands -> jit.vis.hands.parts patch validates with zero errors.
- The audit before/after diff and the audit_db report show no jit.vis.* entries.
- The idioms gap and the uncovered patchers are noted for the SUMMARY.
  </done>
</task>

<task type="auto">
  <name>Task 3: Document Vision (CLAUDE.md line, db-maintenance note, PACKAGES.md), run the full suite against baseline, commit</name>
  <files>CLAUDE.md, .claude/skills/references/db-maintenance.md, .claude/max-objects/PACKAGES.md</files>
  <read_first>
    - CLAUDE.md "## Version Compatibility" section (lines ~227-233)
    - tests/test_claude_md.py lines 110-120 and 255-280 (CLAUDE_BUDGET_BYTES = 30_000; no `.planning/` or `/Users/` text; every cited .md must exist)
    - .claude/max-objects/PACKAGES.md "## Scope"
  </read_first>
  <action>
1. CLAUDE.md (VIS-07): add one bullet at the end of the Version Compatibility list, after the `validate_patch(patch, target_version="9.0")` bullet. Wording: Vision package objects (`jit.vis.*`, Cycling '74 Vision 1.0.2) need Max 9.2+ and are unverified until confirmed in MAX.
   - Keep it under about 160 bytes. CLAUDE.md is 29523 of 30000 bytes, so check `wc -c CLAUDE.md` afterwards.
   - No other CLAUDE.md edits.
2. .claude/skills/references/db-maintenance.md: add a short paragraph, at most 6 lines, at the end of "## After a Max update", titled as a bold lead-in on user-installed packages. It must state:
   - The sync tool, idioms and groups scans read only the app bundle. User packages under ~/Documents/Max 9/Packages are extracted with `python3 .claude/scripts/extract_objects.py --package NAME` and then curated: help boxes win on outlet types, min_version is the package's Max floor as a string, verified false.
   - For Vision, the `max define` / `max objectfile` jit.vis.* names are entries in their own right (no aliases.json entry), and jit.vision / jit.vision.track stay out of the DB.
   - The refpage `<jittermethodlist>` / `<jitterattributelist>` names are recorded in the entries' own messages/attributes, because groups.json is bundle-only.
   - Vision help cords are not in idioms.json.
   - Check with `python3 tools/audit_db.py --help-io`.
   - No `/Users/` or `.planning/` text: tests/test_claude_md.py checks this file too.
3. .claude/max-objects/PACKAGES.md: add "Vision" to the Community list in "## Scope", alphabetically between Rhythmic Time Toolkit and the end, with "(Cycling '74, Max 9.2+)". No other edits.
4. Run `python3 -m pytest tests/test_claude_md.py -q`, then the full `python3 -m pytest -q` in the background with a 600000 ms timeout.
   - Compare against SCRATCH/baseline-pytest.txt: passed must equal the baseline plus the new `test_vision_*` count, with no new failures or errors.
   - Any failure that also fails on the baseline commit is pre-existing. Prove it with `git show <base-sha>:path` or a temp worktree, never stash.
5. Commit with explicit paths: CLAUDE.md, db-maintenance.md, PACKAGES.md. Message: `docs(quick-261023-mma): document Vision package support and user-package DB maintenance`.
6. Confirm `git stash list` matches the pre-flight record and `git status --short` shows no stray modified tracked files from this task.

In the SUMMARY, record:
- the 22 entries
- the VIS-03 decision (no aliases or groups entries; inherited names inlined)
- the idioms gap
- jit.vis.models, the examples and jit.vis.web.track.js left out
- whether the help-io baseline was regenerated or restored
- the pytest baseline vs after figures
- that every Vision entry is verified false until the user confirms jit.vis.* objects in MAX 9.2
  </action>
  <verify>
    <automated>python3 -m pytest tests/test_claude_md.py -q</automated>
    <automated>python3 -m pytest -q</automated>
  </verify>
  <done>
- The CLAUDE.md Version Compatibility section carries the Vision line, and test_claude_md passes (budget and private-path checks included).
- db-maintenance.md documents the user-package path and the Vision decisions.
- PACKAGES.md lists Vision.
- The full suite equals the baseline plus the new Vision tests, with no new failures.
- Three task commits contain only the files each task touched. The stash list is unchanged.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| third-party package files -> repo tools | Vision refpages (XML), help patches (JSON) and JS code are untrusted data read by the extractor and the scratch scripts |
| scratch curation script -> object DB | hand-curated JSON is written into .claude/max-objects/, which every generated-patch validation reads |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-mma-01 | Tampering | reading ~/Documents/Max 9/Packages/Vision | low | mitigate | Package files are parsed only with ElementTree / json (via extract_objects.py and SCRATCH scripts). Package JS is read as text, never executed (no node, no v8). Scripts live in SCRATCH with cwd at the repo root and never run from inside the package directory. |
| T-mma-02 | Tampering | .claude/max-objects/packages/Vision/objects.json, package_info.json | medium | mitigate | json_style (False, True) and sorted-key asserts after every write. The `git diff` on package_info.json must touch only the Vision block. The 12 Task 1 entries stay byte-unchanged in Task 2. ObjectDatabase load + test_package_schema + full pytest gate each commit. overrides.json, groups.json, aliases.json and idioms.json are not written. |
| T-mma-03 | Repudiation | git history | low | mitigate | Per-task commits stage explicit paths only (no `git add -A`, no `git stash`). The stash list is compared with the pre-flight record at the end. |
| T-mma-04 | Information disclosure | CLAUDE.md / db-maintenance.md | low | mitigate | test_claude_md private-path checks (no `/Users/`, no `.planning/`) run in Task 3. The docs reference only `~/Documents/Max 9/Packages` and repo-relative paths. |
| T-mma-SC | Tampering | npm/pip/cargo installs | low | accept | This plan installs no packages. Vision is already installed by the user through Max's Package Manager and is only read. |
</threat_model>

<verification>
- Every name in the Task 1 and Task 2 verify lists resolves with non-empty I/O and restrictions [].
- validate_patch on jit.grab -> jit.vis.hands -> jit.vis.hands.parts: zero errors. Selector messages into jit.vis.hands: zero message_selector warnings.
- The help-io oracle shows no jit.vis.* name unresolved or mismatching under package:Vision.
- The audit_empty_io / audit_half_empty_io before/after diff shows no jit.vis.* name. The audit_db.py default report lists no jit.vis.* gap.
- The full pytest equals the baseline plus the new Vision tests.
</verification>

<success_criteria>
- packages/Vision/objects.json: 22 entries (12 refpage objects + 10 helpers), all min_version "9.2", verified false, rnbo_compatible false, in the sibling files' JSON style.
- package_info.json Vision entry: tier community, prefix jit.vis., version 1.0.2, extracted true, installed true, object_count 22.
- No changes to overrides.json, aliases.json, groups.json or idioms.json. The decision and the gaps are documented in db-maintenance.md and the SUMMARY.
- The CLAUDE.md Version Compatibility line is present and within the 30000-byte budget.
- Tests: the new `test_vision_*` tests pass, and the full suite shows no regression against baseline.
</success_criteria>

<output>
Create `.planning/quick/261023-mma-add-cycling-74-vision-package-to-the-obj/261023-mma-SUMMARY.md` when done
</output>
