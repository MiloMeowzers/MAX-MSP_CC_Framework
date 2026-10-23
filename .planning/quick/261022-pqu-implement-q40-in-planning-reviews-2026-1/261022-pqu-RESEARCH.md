# Quick Task 261022-pqu (Q40): M4L device builder + .amxd export - Research

**Researched:** 2026-10-22
**Domain:** Max for Live device patchers, the `.amxd` container, Live parameter metadata
**Confidence:** HIGH for the byte format and wiring (309 real files parsed). MEDIUM for parameter inference (bundle statistics plus the refpage). LOW for Push-bank behavior in Live (still Q15-pending).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Q15 gate:** The fix plan gates Q40 on Q15 being confirmed in Live. Q15 (261014-d13) is still `human_needed`: continuous dials, stereo out and Push banks are unconfirmed. The user chose to PROCEED anyway. Build on Q15's forms (ParamType/ModMode enums, bare plugout~ with gen~ outlet 0 → inlets 0 and 1, `patcher.parameters.parameterbanks` shape, newobj live.banks, LIVE_PARAMETER_OBJECTS). Everything Q40 adds is EXPERIMENTAL: say so in docstrings, the CLAUDE.md M4L section and the summary. Produce ONE Live check device/patch with a checklist that covers both the pending Q15 items and the Q40 items, so one Live session confirms both.
- **.amxd export:** Add a separate `export_amxd(patcher_or_path, out_path, kind)`. The `.maxpat` stays the editable source of truth (validate/diff/roundtrip keep working); the `.amxd` is a derived binary written next to it. Use the AMXD_* constants in `src/maxpat/m4l_constants.py`. Verify the byte layout against a real .amxd: the kicksynth-m4l.amxd that the constants were reverse-engineered from, and/or a .amxd shipped in the Max/Live bundle. Add a round-trip test (parse a real file → re-export → byte-compare or structural compare).
- **Builder API:** `add_m4l_device` is the generic skeleton: plugin~/plugout~ per kind, live.thisdevice init chain, params, unique short names, banks. Refactor `add_m4l_gen_synth` to call it internally. Its serialized output must stay unchanged; add a regression test comparing before/after dicts for representative inputs (Frustration directive: never regress working functionality).
- **Param spec:** A list of dicts `[{name, min, max, default, unit?, type?, steps?, short_name?}]`. Infer type/unit from range and name (stepped int range → Int; ms/time → Time; freq/Hz → Hertz; gain/dB → deciBel; 0–1 → Float). Explicit keys always win. Short names are auto-made unique (Live's short-name length limit).

### Claude's Discretion
- MIDI-effect wiring details (midiin/midiout vs. plugin~ pass-through), the exact live.thisdevice init chain, the critic check list, and the module placement (builders.py vs. a new m4l_device.py) are left to the researcher and planner. All of it must be grounded in the object DB, refpages and bundle files (Rule #1).

### Deferred Ideas (OUT OF SCOPE)
None listed.
</user_constraints>

## Project Constraints (from CLAUDE.md)
- Rule #1: use DB objects only, and check `domain`. Every object below was looked up (see Wiring).
- Rule #3/#4: use `trigger` for fan-out. Fire right-to-left.
- Rule #5: build with the Patcher API only. No generator scripts.
- Rule #7: every save must be committed. Writers auto-commit path-scoped under `patches/<project>/`. Never `git add .`.
- Rule #9: presentation parity. M4L devices live in presentation, so every control goes into presentation.
- M4L section: no `gain~`/`live.gain~`/`ezdac~` before `plugout~`. Bind gen~ Params with `param_connect` + `parameter_enable: 1` + `saved_attribute_attributes.valueof`.
- Mark everything EXPERIMENTAL until it is confirmed in Live.

## Summary

The `.amxd` file is a plain chunk stream: `[4-byte tag][uint32 LE length][payload]`, repeated. A normal (unfrozen) device holds three chunks: `ampf` (payload = the 4-byte kind code), `meta` (payload = uint32, 0 for every editable Max-written file) and `ptch` (payload = UTF-8 patcher JSON). The existing `AMXD_HEADER_FORMAT = "<4sI4s4sI4x4sI"` produces exactly the right 32 bytes for a writer. The comment labels are wrong, though: the "meta version 4" is the meta chunk *length* and the "4 zero bytes padding" is the meta *payload*. A parser built on that format would silently drop non-zero meta values.

Max writes the ptch JSON with a trailing `"\n\0"`, counted in the length; 26 of 26 Max-written JSON payloads have it. The framework's own Python-written `kicksynth-m4l.amxd` has no terminator, and Live 12.3.6 still loaded it: Live wrote a `.adv` preset that references it and lists its parameters. Write Max's form.

Live's factory templates show the per-kind wiring:
- **audio_effect:** `plugin~` 0→`plugout~` 0 and 1→1.
- **midi_effect:** `midiin`→`midiout`.
- **instrument:** a lone `midiin` and an unwired `plugout~`.

**Primary recommendation:** create `src/maxpat/m4l_device.py`, holding the amxd codec, `export_amxd`, param inference and the bank planner, with a thin `add_m4l_device` method on `BuildersMixin`. Refactor `add_m4l_gen_synth` onto shared helpers, called in the same box-creation order. Write a golden-dict test BEFORE the refactor.

## 1. .amxd binary format (verified against real files)

Survey: 309 `.amxd` files from the Live 12 and Live 11 bundles, Max.app, `~/Music/Ableton` and `~/Documents/Max 9/Packages`, parsed chunk-wise. Every `ampf` file ended exactly at its last chunk. `[VERIFIED: scratchpad survey.py/survey2.py over real files]`

| Chunk sequence | Count | ptch payload |
|---|---|---|
| `ampf meta ptch` | 263 | 27 plain JSON (`{`); the rest begin `mx@c` (frozen collective) |
| `ampf meta ciph ptch` | 41 | encrypted (Ableton built-ins such as DS HH and Envelope Follower) |
| `ampf ptch` (no meta) | 4 | e.g. Max Compressor.amxd (mx@c); Abl.Droner.amxd (JSON) |
| plain JSON without the `ampf` header | 1 | `~/Music/Ableton/User Library/Presets/mx4live/kicksynth-m4l.amxd` (not a real amxd) |

**meta payload vs. kind of file.** Plain JSON written by Max: `00000000` (all Live templates; Max 9.0.7 user saves). Three Max 8.5.8 user saves have `01000000`. Frozen `mx@c` files: `04000000` (57) or `07000000` (200). **Write 0.**

**Kind codes seen:** `aaaa` 229, `iiii` 51, `mmmm` 24. The Live 12 MIDI Tools codes `natt` and `nagg` (2 each) are out of scope.

**Exact bytes of Live 12's own templates** (`/Applications/Ableton Live 12 Suite.app/Contents/App-Resources/Misc/Max Devices/`):
```
Max Instrument.amxd   (3800 B): 616d7066 04000000 69696969 6d657461 04000000 00000000 70746368 b80e0000  | "{\n\t\"patcher\" : \t{..." ... "\n}\n\0"
Max Audio Effect.amxd (4478 B): 616d7066 04000000 61616161 6d657461 04000000 00000000 70746368 5e110000  | ... "\n\0"
Max MIDI Effect.amxd  (3350 B): 616d7066 04000000 6d6d6d6d 6d657461 04000000 00000000 70746368 f60c0000  | ... "\n\0"
kicksynth-m4l.amxd  (103996 B): 616d7066 04000000 69696969 6d657461 04000000 00000000 70746368 1c960100  | json.dumps(indent=4) text, ends "\n}" (NO \0)
```
For every file, `struct.unpack("<4sI4s4sI4x4sI", b[:32])` gives `(b'ampf', 4, kind, b'meta', 4, b'ptch', N)` with `N + 32 == file size`. The length N includes the trailing `\n\0`. `[VERIFIED: hexdump + struct check this session]`

**Constants check.** File read this session: `src/maxpat/m4l_constants.py:97-110`. Verbatim:
```
AMXD_MAGIC = b"ampf"
AMXD_VERSION = 4
AMXD_META_MARKER = b"meta"
AMXD_META_VERSION = 4
AMXD_PATCH_MARKER = b"ptch"
AMXD_TYPE_AUDIO_EFFECT = b"aaaa"
AMXD_TYPE_INSTRUMENT = b"iiii"
AMXD_TYPE_MIDI_EFFECT = b"mmmm"
AMXD_HEADER_FORMAT = "<4sI4s4sI4x4sI"
AMXD_HEADER_SIZE = 32
```
- **Bytes:** all CORRECT for writing.
- **Semantics:** wrong in the comment block at :86-95. `AMXD_VERSION` (4) is the `ampf` chunk length, `AMXD_META_VERSION` (4) is the `meta` chunk length, and the `4x` is the meta payload (uint32 flags, 0).
- **Fix:** fix the comment, keep the names (pinned by `tests/test_m4l_constants.py:124-140`), and add `AMXD_CHUNK_HEADER = "<4sI"` and `AMXD_PAYLOAD_TERMINATOR = b"\n\x00"`.

**Parser rule.** Parse chunk-wise. Never parse through `AMXD_HEADER_FORMAT`, because `4x` discards a non-zero meta and the format cannot handle a missing meta chunk. Raise a clear error for a `ciph` chunk or an `mx@c` payload: "frozen/encrypted device, cannot export or edit".

**`project.amxdtype` = big-endian int of the kind code.**
- `aaaa` = 1633771873, `iiii` = 1768515945, `mmmm` = 1835887981.
- Present in every Max-written JSON payload.
- Absent from kicksynth, which loaded anyway.

`[VERIFIED: Max Instrument/Audio Effect/MIDI Effect payloads; int.from_bytes(b'aaaa','big')]`

Recommendation: if the dict has `project.amxdtype` and it disagrees with `kind`, raise. Otherwise leave the payload alone and do not inject `project`. The kicksynth result shows Live does not need it.

**Payload encoding to write:** `dumps_max(patch_dict).encode("utf-8") + b"\n\x00"`.
- `dumps_max` (`src/maxpat/maxjson.py:117`) is the framework's Max 9 layout. Max 9.0.7 itself still writes amxd payloads in the legacy tab/`" : "` layout (sendNote.amxd).
- Both layouts are plain JSON and both load. Byte-matching Max's legacy layout is not possible (maxjson.py:24 says it is not reproduced) and not needed.

**Round-trip tests:**
1. **Byte-identical:** `parse_amxd(f) → build_amxd(kind, raw_payload, meta) == f`.
   - Run it on `/Applications/Max.app/Contents/Resources/Examples/resources/fourin_fourout.amxd` (4692 B, `aaaa`, meta 0, ends `\n}\n\0`; `requires_max` marker, `tests/conftest.py:42`).
   - Run it on kicksynth, vendored from `git show 494c2e64:patches/kicksynth/generated/kicksynth-m4l.amxd` (103996 B, our own file) into `tests/fixtures/`.
2. **Structural:** `json.loads(parse(export(dict)).payload.rstrip(b"\0")) == dict`.
3. **Optional, skipif-gated:** the three Live templates, gated on the Live 12 path.

## 2. Device patcher JSON keys (real files)

**Keys in Max-written payloads that `Patcher()` defaults lack.**
- From `Max Instrument.amxd` (appversion 8.1.2): `openrect: [0,0,0,169]`, `latency: 0` and the `project{...}` block.
- Max 9 saves (sendNote 9.0.7, Max MIDI Generator 9.0.0) add `is_mpe: 0`, `external_mpe_tuning_enabled: 0`, `minimum_live_version: ""`, `minimum_max_version: ""` and `platform_compatibility: 0`.
- **None of these is required.** kicksynth (loaded in Live) had only: `fileversion, appversion, classnamespace, rect, openinpresentation, devicewidth, boxes, lines, parameters, autosave`.

`[VERIFIED: keys.py dump this session]`

`Patcher()` defaults already hold `devicewidth: 0.0` and `openinpresentation: 0` (dumped this session). Recommend that `add_m4l_device` set:
- `openinpresentation = 1`;
- `devicewidth` = the computed presentation width;
- `openrect = [0.0, 0.0, 0.0, 169.0]`;
- `latency = 0`.

The m4l critic already warns when the first two are missing (`m4l_critic.py:384-401`).

**Device height.** All three templates carry `openrect [0,0,0,169]` and a hidden comment "Device vertical limit" at y=170. Presentation content must fit in 169 px. `[VERIFIED: template dumps]`

**`parameters` dict.** Max computes `patcher.parameters` on save: per-box `"obj-N": [longname, shortname, 0]`, `inherited_shortname: 1` and `parameterbanks`. Max 9.1.2 saves banks with an extra `"buttons": ["-" x8]` key (kicksynth). The builder only writes `parameterbanks` (the Q15 shape); Max rebuilds the rest. No bundle file has a non-placeholder bank, so the filled-bank form stays `[ASSUMED]` (Q15 human check).

## 3. Per-kind wiring (DB + templates)

DB lookups were run this session (`ObjectDatabase().lookup`). Every restriction set is `[]`.

| Object | Domain | Inlets | Outlets | Notes |
|---|---|---|---|---|
| `plugin~` | MSP | 2 sig | 2 sig | bare = stereo; `plugin~ 1 2 3 4` has 4/4 (fourin_fourout) but the DB has `variable_io False`, so **use bare forms only** |
| `plugout~` | MSP | 2 sig | 2 sig | Max saves `numoutlets 2, outlettype [signal, signal]` |
| `midiin` | Max | 1 | 1 | template `outlettype ["int"]` |
| `midiout` | Max | 1 | 0 | |
| `live.thisdevice` | M4L | 1 | 3 | newobj; the bundle saves `numinlets 1, numoutlets 3, outlettype [bang, int, int]` (107/107 boxes) |
| `live.dial` | M4L | 1 | 2 | maxclass `live.dial`; `bang` ∈ `db.selectors("live.dial")` = True |
| `live.banks` | M4L | 1 | 1 | newobj text form (Q15) |
| `trigger` | Max | 1 | var | `compute_io_counts("trigger", ["b","b"])` = (1, 2) |

**Template wiring** (Live 12 `Misc/Max Devices`, verbatim lines):
- **Audio Effect:** `['obj-1', 0] → ['obj-2', 0]` and `['obj-1', 1] → ['obj-2', 1]` (plugin~ → plugout~).
- **MIDI Effect:** `midiin` 0 → `midiout` 0.
- **Instrument:** `midiin` box and `plugout~` box, **no lines**.

Recommended skeleton per kind:
- **instrument:** `midiin` (as in Live's template), plus `plugout~`. When an `audio_source=(box, outlet)` is given, wire source → plugout~ 0 and 1 (the Q15 form). Without a source, leave plugout~ for the caller.
- **audio_effect:** `plugin~` → `plugout~`, 0→0 and 1→1, as pass-through. If `audio_source` is given, the caller's processing sits between them. Return both boxes.
- **midi_effect:** `midiin` → `midiout` pass-through. No plugin~. A MIDI effect that cuts this blocks the track's MIDI.

**live.thisdevice init chain.** Refpage `m4l-ref/live.thisdevice.maxref.xml`:
- Outlet 0 bangs "when the Max Device is opened and completely initialized … every time a new preset is loaded or the device is saved".
- Outlets 1 and 2 report enabled state and preview state, and are inactive in plain Max.

Bundle usage of outlet 0 (mined): `t 1 b` 18, `t 1 b b` 2, `path …` etc.

Recommend: `live.thisdevice` 0 → `t b b … b`, one `b` per control that has **no** `param_connect`, and each trigger outlet → that control's inlet 0. A `bang` makes live.dial re-emit its restored value to the caller's DSP. With one target, cord directly; with none (all gen~-bound), emit `live.thisdevice` alone (it also marks the patch for `detect_m4l_device_type`). Create these boxes **after** the dials, so ids for the legacy path don't shift. `[ASSUMED]`: that a banged live.dial re-outputs in Live.

## 4. Parameter inference

**Enums.** Read this session: `m4l_constants.py:23-68`. `ParamType`: `FLOAT = 0`, `INT = 1`, `ENUM = 2`, `BLOB = 3`. `UnitStyle`: `INT = 0`, `FLOAT = 1`, `TIME = 2`, `HERTZ = 3`, `DECIBEL = 4`, `PERCENT = 5`, `PAN = 6`, `SEMITONES = 7`, `MIDI = 8`, `CUSTOM = 9`. `ModMode`: `NONE = 0` … `ABSOLUTE = 4`.

**Refpage** `parameters.maxref.xml`:
- **Short Name:** "The maximum length varies according to letter width, but is generally in a range of 5 to 7 characters." `[CITED]`
- **Type:** "the native integer representation is limited to 256 values … When working with Live UI objects whose integer values will exceed this range, the Type attribute should be set to Float, and the Unit Style attribute should be set to Int." `[CITED]`
- **Saved keys:** `parameter_steps`, `parameter_exponent`, `parameter_units` (Custom).
- **Visibility key:** the saved key is `parameter_invisible`, not "visibility".

**Bundle evidence** (live.dial/numbox/slider, `(type, unitstyle)` → typical range):

| (type, unitstyle) | Unit | Count | Typical ranges |
|---|---|---|---|
| (0,2) | Time | 235 | 0–500…10000 ms |
| (0,3) | Hertz | 269 | 20–20000 |
| (0,4) | dB | 68 | -72–0 |
| (0,5) | % | 673 | 0–100 (549/673) |
| (0,6) | Pan | 19 | -50–50 |
| (1,0) | Int | 180 | 1–32, 0–127 |
| (0,1) | Float | 758 | ±1, 0–1 |

`[VERIFIED: ranges.py over Max.app C74 patches]`

**Inference order** (explicit `type`/`unit`/`steps`/`short_name` keys always win):
1. Tokenize the name on `_`, spaces and camelCase, and match whole tokens (never substrings: "ms" must not match "harmonics").
2. Tokens `ms|time|attack|decay|release|delay|length` → TIME.
3. Tokens `freq|frequency|hz|cutoff` → HERTZ.
4. Token `db`, or `gain|volume|level` **with min < 0** → DECIBEL. A linear 0–1 gain stays Float.
5. Tokens `pan` → PAN; `semi|semitones|transpose` → SEMITONES.
6. Integer min/max/default (Python `int`), or `steps` given:
   - span ≤ 255 → `parameter_type` INT, unitstyle INT;
   - span > 255 → type FLOAT, unitstyle INT (refpage rule).
7. Otherwise FLOAT/FLOAT. This covers 0–1.
8. `parameter_modmode`: keep the gen-synth's ABSOLUTE for the legacy path. For the new builder, NONE = 0 matches kicksynth; this is open in Q15's ModMode judgment, so make it a parameter.

**Short names.** Reuse `m4l_polish._abbreviate_shortname(longname, max_len=8)` (`m4l_polish.py:99`), then de-duplicate. Collisions are real: "Amp Decay" and "Filter Decay" both drop to "Decay". De-dupe by trimming and appending a digit within 8 characters. The bundle shows Max does not enforce a limit (saved shortnames run up to 29 characters), so 8 is a Push-display convention; keep it consistent with polish.

**Banks.** Reuse the grouping logic in `organize_push_banks` (`m4l_polish.py:599-682`: `_classify_parameter`, chunks of 8, `"-"` padding, `{"0": {"index":0,"name":…, "parameters":[…]}}`). It mutates a dict and appends a raw `obj-live-banks` box. Extract a pure `plan_push_banks(longnames) -> dict` and use it from both paths. The builder then sets `self.props["parameters"] = {"parameterbanks": …}` and `add_box("live.banks")`.

## 5. Integration points

- **`add_m4l_gen_synth`** is at `src/maxpat/builders.py:1039-1163`. Its box-creation order is fixed and determines ids:
  1. `add_gen` → obj-1, with `varname` set;
  2. `add_box("plugout~", x=200, y=400)` → obj-2;
  3. `add_connection(gen,0,plugout,0)`, then `(…,1)`;
  4. dials obj-3… at `x=50+60*i, y=100`, `skip_overlap_check=True`.
- Each dial's `extra_attrs` are inserted in this order: `varname`, `param_connect`, `parameter_enable`, `saved_attribute_attributes.valueof`. The valueof key order is `parameter_initial [mid]`, `parameter_initial_enable 1`, `parameter_longname name`, `parameter_shortname name` (NOT abbreviated), `parameter_mmin`, `parameter_mmax`, `parameter_modmode 4`, `parameter_type 0`, `parameter_unitstyle 1`.
- **Refactor recipe:** extract `_m4l_param_dial(spec, x, y, *, param_connect=None)` and `_m4l_stereo_out(source, plugout)`. Call `add_m4l_device(kind="instrument", params=[explicit dicts with short_name=name, type/unit/modmode explicit], audio_source=(gen_obj, 0), midi_in=False, init_chain=False, banks=False, presentation=False, layout="legacy")`. With every explicit key set, inference never runs.
- **Golden test first:** in task 1, before touching code, commit `tests/fixtures/expected/m4l_gen_synth_*.json` from `json.dumps(p.to_dict())` for at least these inputs: default 2 params; `gen_varname="osc"`; custom `gen_code`; 10 params. The test must pass on the old code and stay green after the refactor.
- **Tests to keep green:**
  - `tests/test_m4l_gen_synth.py` (24 tests);
  - `tests/test_m4l_polish.py`;
  - `tests/test_m4l_constants.py`;
  - `tests/test_critic_revival.py::TestM4LBuilderClean` (zero blockers, :570-579);
  - `tests/test_critics_recursive.py`: `_PARITY_CASES` nested-parity invariant (:705-723) and the review_m4l assertions (:888-928).
- **Critic structure** (`critics/m4l_critic.py:120-173`):
  - Device-level checks run once on the top level (completeness, quality, uniqueness, banks).
  - Per-scope checks run on every non-gen scope via `tag_results(found, scope.path)`.
  - Each `CriticResult(severity, finding, suggestion, rule="<fn name minus _check_>", box_ids=finding_ids(...))`.
  - There is no rule registry; the rule id is just the string.
  - `review_patch` auto-runs it via `detect_m4l_device_type` (`critics/__init__.py:138-141`).
- **Saving a non-.maxpat:** `hooks._auto_commit_saved_file(path)` (`hooks.py:64`) works for any file under `patches/<project>/`. It warns and returns None elsewhere, and never raises. Write with `atomic_io.atomic_write_bytes(path, payload)` (`atomic_io.py:73`). `.amxd` is not gitignored (`git check-ignore` rc=1). The `.maxpat` and `.amxd` get separate commits. `kicksynth-m4l.amxd` was once committed (494c2e64), then deleted (d46042af).
- **Module placement:** create `src/maxpat/m4l_device.py`, holding:
  - the codec (`parse_amxd`, `build_amxd`, `encode_payload`);
  - `export_amxd`;
  - `infer_param`;
  - `unique_shortnames`;
  - `plan_push_banks` (or import it from polish).

  Add `add_m4l_device` to `BuildersMixin`, delegating to it; builders.py is already 1204 lines. `export_amxd(patcher_or_path, out_path=None, kind=None)`: when `kind` is None, use `detect_m4l_device_type(dict)`. Default `out_path` = `.maxpat` path with an `.amxd` suffix.

## 6. Proposed new critic checks

All are warnings or notes, because the work is experimental; blockers would block saves. Make them per-scope where they read box attributes, so nested parity holds.

| Rule | Severity | Check | Grounding |
|---|---|---|---|
| `stereo_out` | warning | bare plugout~ has exactly one of inlets 0/1 fed → one-sided output | Q15 D3 |
| `midi_passthrough` | warning | midi_effect: midiin has no outgoing cord or midiout has no incoming cord | MIDI Effect template |
| `shortname_unique` | warning | duplicate `parameter_shortname` across the device | Push/automation labels |
| `shortname_length` | note | shortname > 8 characters | refpage 5–7 chars |
| `int_param_range` | warning | `parameter_type` 1 with mmax-mmin > 255 | refpage Type text |
| `param_range` | warning | mmin ≥ mmax, or `parameter_initial` outside the range | — |
| `bank_refs` | warning | a `parameterbanks` slot names a longname not in the device | Q15 shape |
| `device_height` | warning | openinpresentation and a presentation box bottom > 169 | template openrect/limit comment |

Keep `project.amxdtype` vs. kind mismatch as an `export_amxd` ValueError, not a critic finding.

## Common Pitfalls
1. **Parsing via `AMXD_HEADER_FORMAT`:** it silently zeroes meta and breaks on `ampf ptch` files. Parse chunk-wise.
2. **Frozen and encrypted devices** (`mx@c` 240/309, `ciph` 41/309): refuse them and say why.
3. **Byte-identical regression:** any new box created before the dials, or any reordered `extra_attrs`/valueof key, changes the legacy output. Rely on the golden test.
4. **Substring inference** ("ms" in "harmonics", "hz" in "hzfoo"): match tokens. A linear "gain" 0–1 is not dB.
5. **Int params with span > 255** quantize in Live: use Float + unitstyle Int.
6. **Short-name collisions after abbreviation:** de-dupe after truncating.
7. **`plugin~`/`plugout~` with channel arguments** change I/O, but the DB says not variable: emit bare forms only.
8. **Presentation height:** presentation content must fit in 169 px. Use the Rule #9 presentation parity for every control.
9. **Live-only behaviors, unverifiable offline:**
   - live.thisdevice outlets 1 and 2;
   - bang re-emit after preset load;
   - Push bank display;
   - continuous dials;
   - whether Live uses `project.amxdtype` or only the header code (kicksynth suggests the header code).
10. **Auto-commit:** the Live check files live in `.planning/quick/...`, outside `patches/`, so they are not committed (an expected warning). Never `git add -A`.

## Environment Availability
| Dependency | Available | Version |
|---|---|---|
| Max.app | yes | 9.2.0 (`requires_max` tests run) |
| Ableton Live 12 Suite | yes | 12.4.6 (templates at `Contents/App-Resources/Misc/Max Devices/`) |
| Python / pytest | yes | 3.14.2 / 9.0.2 |

No package installs, so no Package Legitimacy Audit is needed.

## Validation Architecture
- **Quick run:** `python3 -m pytest tests/test_m4l_device.py tests/test_m4l_gen_synth.py tests/test_m4l_constants.py -q`
- **Full suite:** `python3 -m pytest -q`. The baseline is recorded in the quick dir (`baseline-pytest.txt`).

New `tests/test_m4l_device.py` covers:
- the codec: byte round-trip on fourin_fourout (`requires_max`) and the vendored kicksynth fixture; structural round-trip;
- per-kind wiring (cords verbatim as in the templates);
- the init chain (`t b…` count = number of unbound controls);
- inference tables;
- short-name uniqueness;
- banks shape;
- `export_amxd` header bytes per kind;
- refusal of mx@c/ciph input;
- each new critic rule (positive and negative);
- nested parity entries for the per-scope rules.

The golden gen-synth fixtures land in Wave 0.

**Manual (Live):** one check device covering both phases. Build an instrument with `add_m4l_device`, export it to `.amxd`, and drag it into Live; no copy-paste is needed. The checklist covers:
- **Q15:** continuous dials; stereo L+R; Push banks; ModMode choice.
- **Q40:**
  - the `.amxd` loads as the right device kind;
  - inferred units display correctly (ms/Hz/dB);
  - short names appear de-duplicated;
  - live.thisdevice re-emits values on preset load.

## Security Domain
`security_enforcement` is absent from the config, so it is treated as enabled. The only relevant category is ASVS V5 input validation for `parse_amxd`:
- bounds-check every chunk length against the file size;
- reject truncated data;
- never `eval`;
- decode UTF-8 strictly;
- strip only a single trailing `\0`.

Writes are atomic and path-scoped. No new auth, crypto or network surface.

## Assumptions Log
| # | Claim | Risk if wrong |
|---|---|---|
| A1 | Live accepts `parameterbanks` written without per-box `parameters` entries or `buttons` | Banks are missing on Push (cosmetic). Already a Q15 human check. |
| A2 | `bang` → live.dial re-emits its restored value in Live | The init chain is a no-op; the DSP misses its initial values. Live check item. |
| A3 | Live keys the device kind on the header code; a missing `project.amxdtype` is harmless | Wrong device slot. kicksynth (no `project`) loaded as MxDeviceInstrument, so the risk is low. |
| A4 | The 8-character short-name cap is the right Push convention | Names are truncated more than needed (cosmetic). |
| A5 | meta = 0 is right for an unfrozen device | Load failure. Low: all 44 Live/Max templates use 0. |

## Open Questions
1. ModMode default for the new builder (NONE vs ABSOLUTE): make it a parameter and let the Live check decide.
2. Whether to also export audio_effect/midi_effect check devices: CONTEXT says one device. The header codes for the other kinds are verified from Live's templates, so the risk is low.

## Sources
**Primary (HIGH):**
- Real `.amxd` files parsed this session: Live 12 `Misc/Max Devices/*.amxd`, Max.app `Examples/resources/fourin_fourout.amxd`, `~/Music/Ableton/User Library/.../kicksynth-m4l.amxd` + `.adv` (Creator "Ableton Live 12.3.6", PatchSlot → amxd, MxDFloatParameter list).
- Refpages: `docs/refpages/m4l-ref/parameters.maxref.xml`, `live.thisdevice.maxref.xml`.
- The `ObjectDatabase` lookups above.
- Bundle patch mining (valueof keys, ranges, thisdevice cords).

**Code read:**
- `m4l_constants.py`;
- `builders.py:1039-1163`;
- `m4l_polish.py:95-140`, `:499-700`, `:811-833`;
- `critics/m4l_critic.py`;
- `hooks.py:64-130`;
- `project.py:364-430`;
- `maxjson.py`;
- `tests/conftest.py`.

**Research date:** 2026-10-22. Valid until the next Max or Live update (re-run survey.py).
