---
phase: quick-261022-pqu
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  # Task 1 (tracer): golden pre-refactor commit, .amxd codec + export, param resolution, add_m4l_device skeleton
  - tests/fixtures/expected/m4l_gen_synth_golden.json
  - tests/test_m4l_gen_synth_golden.py
  - tests/fixtures/kicksynth-m4l.amxd
  - src/maxpat/m4l_constants.py
  - src/maxpat/m4l_device.py
  - src/maxpat/builders.py
  - tests/test_m4l_device.py
  # Task 2: init chain, Push banks, add_m4l_gen_synth refactored onto add_m4l_device
  - src/maxpat/m4l_polish.py
  # Task 3: critic checks, docs, combined Live check device, final gate
  - src/maxpat/critics/m4l_critic.py
  - CLAUDE.md
  - tests/test_doc_signatures.py
  - .planning/quick/261022-pqu-implement-q40-in-planning-reviews-2026-1/q40-live-check.maxpat
  - .planning/quick/261022-pqu-implement-q40-in-planning-reviews-2026-1/q40-live-check.amxd
autonomous: true
requirements: [Q40]

estimate:
  # estimate-calibration: factor 1 (sample_count 0, confidence low), so tokens == raw_tokens.
  # chars/4 over what the executor touches: plan + execute-plan workflow + summary template ~40k;
  # Task 1 ~95k (reads ~25k of builders/constants/polish/critic/maxjson/hooks/tests, writes ~35k of
  # m4l_device.py + builder + tests, baseline + iterations ~35k);
  # Task 2 ~55k (reads ~10k, writes ~20k, iterations ~25k);
  # Task 3 ~65k (critic ~12k, tests ~12k, CLAUDE.md ~3k, check device build/save/export ~10k,
  # two full-suite runs ~10k, SUMMARY ~8k, iterations ~10k).
  # Over the 100k smart zone (advisory). Quick mode keeps one plan; every task ends on a commit
  # boundary, so a fresh continuation can resume at Task 2 or Task 3.
  tokens: 255000
  raw_tokens: 255000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "The add_m4l_gen_synth golden test (tests/test_m4l_gen_synth_golden.py + tests/fixtures/expected/m4l_gen_synth_golden.json, 4 cases: default 2 params, gen_varname='osc', custom gen_code, 10 mixed params incl. int tuples and a spaced name) is committed in its own commit that touches no src/ file, BEFORE the commit that adds src/maxpat/m4l_device.py, and compares key-order-sensitive JSON text. It passes on the pre-refactor code and, unchanged, after Task 2's refactor (CONTEXT: Builder API, golden before refactor)."
    - "parse_amxd reads the .amxd chunk-wise ([4-byte tag][uint32 LE length][payload]) and build_amxd(f.code, f.payload, f.meta) reproduces the input byte-for-byte for the vendored kicksynth-m4l.amxd (always), Max.app fourin_fourout.amxd (requires_max) and the three Live 12 template devices (skipped when Live is absent). parse_amxd raises ValueError, naming the reason, for a ciph chunk or an mx@c payload (frozen/encrypted), a truncated chunk, trailing bytes, a missing ampf or ptch chunk, an unknown kind code (natt/nagg) and invalid UTF-8; it never evaluates the payload (CONTEXT: .amxd export)."
    - "export_amxd(patcher_or_path, out_path=None, kind=None) writes `ampf`(4, kind code) `meta`(4, uint32 0) `ptch`(N, dumps_max JSON + b'\\n\\x00'). The first 32 bytes equal struct.pack(AMXD_HEADER_FORMAT, ...) with N + 32 == file size, and bytes [0:28] equal the matching Live 12 template's. decode_payload(parse_amxd(written).payload) equals the source dict. kind=None uses detect_m4l_device_type; a project.amxdtype that disagrees with the kind, an out_path whose suffix is not .amxd, or a dict with no device markers and no kind raise ValueError and write nothing. A path argument leaves the .maxpat bytes untouched and writes the .amxd next to it; under patches/<project>/ the .amxd alone is auto-committed (CONTEXT: separate export_amxd, .maxpat stays the source of truth)."
    - "Patcher.add_m4l_device(kind, params=None, *, audio_source=None, midi_source=None, midi_in=True, init_chain=True, banks=True, presentation=True, modmode=ModMode.NONE) returns an M4LDevice. Wiring matches Live's templates verbatim: audio_effect plugin~:0 -> plugout~:0 and plugin~:1 -> plugout~:1; midi_effect midiin:0 -> midiout:0; instrument a midiin plus an unwired plugout~. An audio_source (Box, outlet) replaces the pass-through and feeds plugout~ inlets 0 AND 1 (the Q15 stereo form); a ((Box, o), (Box, o)) pair feeds L -> 0 and R -> 1. plugin~ and plugout~ are always bare (no channel argument). review_patch reports zero blockers on each kind's output (Q40: stereo plugin~/plugout~ wiring)."
    - "Each param dict {name, min, max, default, unit?, type?, steps?, short_name?, varname?, param_connect?, modmode?} becomes one live.dial with parameter_enable 1 and a valueof block in the legacy key order (parameter_initial [default], parameter_initial_enable 1, parameter_longname, parameter_shortname, parameter_mmin, parameter_mmax, parameter_modmode, parameter_type, parameter_unitstyle, then parameter_steps only when steps is given). Explicit keys always win. Inference matches whole name tokens, never substrings: ms -> Time, hz -> Hertz, db -> deciBel; a non-integer range inside [0, 1] -> Float; time/attack/decay/release/delay/length -> Time; freq/frequency/cutoff -> Hertz; gain/volume/level with min < 0 -> deciBel; pan -> Pan; semi/semitone(s)/transpose -> Semitones; an all-int (min, max, default) spec -> Int unit; type Int iff all-int and span <= 255, else Float (so an int span > 255 is Float type + Int unit, per parameters.maxref). 'harmonics' is not Time and a 0-1 'gain' stays Float (CONTEXT: Param spec)."
    - "Auto short names are m4l_polish._abbreviate_shortname(name, 8) made unique within 8 characters by trimming and appending 2, 3, ... ('Filter Envelope Amount' and 'Pitch Envelope Amount' give 'Amount' and 'Amount2'); an explicit short_name is never altered and never reused by an auto name. Duplicate names, unknown keys, missing required keys, bool bounds, min >= max, default outside [min, max], steps < 2, an Enum/Blob type and a Custom unit raise ValueError (Q40: unique short names)."
    - "With init_chain=True the builder adds live.thisdevice after the dials. Zero controls without param_connect: thisdevice alone. One: thisdevice:0 -> that dial:0. k >= 2: thisdevice:0 -> `t` with k `b` arguments, outlet j -> the j-th unbound dial inlet 0. gen~-bound dials never get an init cord. detect_m4l_device_type returns the requested kind for all three kinds, so export_amxd(kind=None) writes the right code (Q40: live.thisdevice init chain)."
    - "With banks=True and at least one param, patcher.parameters.parameterbanks equals m4l_polish.plan_push_banks(longnames), the pure function organize_push_banks now calls (its output is unchanged: tests/test_m4l_polish.py stays green). Exactly one newobj live.banks exists. Existing user-defined banks (any slot other than '-') are kept with a UserWarning. polish_m4l_device over the builder output keeps the banks, the short names and the single live.banks (Q40: Push parameterbanks)."
    - "With presentation=True and at least one dial, every dial is in presentation at [8 + 52*col, 8 + 56*row, 44, 48] (bundle live.dial size 44x48) with ncols = min(n, 8) for n <= 24, else ceil(n / 3). Every presentation bottom is <= 169 (Live's device height), and the patcher gets openinpresentation 1, devicewidth 8 + 52*ncols, openrect [0, 0, 0, 169] and latency 0 (Rule #9; Live template keys)."
    - "add_m4l_gen_synth builds its spec dicts with every key explicit (short_name = name, varname = name, type Float, unit Float, modmode Absolute, default = midpoint, param_connect built as the f-string f\"{gen_varname}::{name}\") and calls self.add_m4l_device('instrument', ..., audio_source=(gen_obj, 0), midi_in=False, init_chain=False, banks=False, presentation=False). Its return value and serialized output are unchanged: the golden test, tests/test_m4l_gen_synth.py (24 tests) and TestM4LBuilderClean pass unedited (CONTEXT: refactor onto the generic skeleton)."
    - "review_m4l adds 8 non-blocking rules: stereo_out, midi_passthrough (midi_effect only), shortname_length (note), int_param_range, param_range (per scope, tagged like the existing per-scope checks) and shortname_unique, bank_refs, device_height (device level). Each has a positive and a negative test; each per-scope rule gives the same finding nested in `p synth` with a `[p synth] ` prefix and path obj-1. None fires on add_m4l_device output. test_nested_junk_never_raises and the requires_max bundle sweep stay green (Q40: critic checks)."
    - "One Live check device covers Q15 and Q40: .planning/quick/261022-pqu-implement-q40-in-planning-reviews-2026-1/q40-live-check.maxpat is built with add_m4l_device (instrument; gen~ synth; freq and amp bound by param_connect; Out Gain dB, Octave Int and Attack ms unbound and banged by the init chain; two dials whose short names de-duplicate). It is polished, saved through the save_patch_roundtrip gate with zero blockers, and exported to q40-live-check.amxd (header iiii, meta 0). Both files are committed with explicit paths, and SUMMARY carries the combined checklist (Q15 items 1-4 + Q40 items) (CONTEXT: Q15 gate)."
    - "Everything Q40 adds is marked EXPERIMENTAL (not yet confirmed in Live) in the m4l_device module docstring, the add_m4l_device and export_amxd docstrings, the new critic rules' docstring, the CLAUDE.md M4L section and SUMMARY. CLAUDE.md stays <= 30,000 bytes and keeps every RULE_ANCHORS entry. tests/test_doc_signatures.py indexes src.maxpat.m4l_device and binds every documented call form (Q40: mark experimental)."
    - "Regression gate: the full pytest run in Task 3 has rc <= the Step 0 baseline status. junit_diff.py exits 0, with new test ids only from tests.test_m4l_device and tests.test_m4l_gen_synth_golden and no removals. `git status --porcelain patches patterns` and `git stash list` match their Step 0 snapshots. No commit touches patches/ or patterns/, and every commit stages explicit paths."
  artifacts:
    - path: "src/maxpat/m4l_device.py"
      provides: "AmxdFile, parse_amxd, build_amxd, encode_payload, decode_payload, export_amxd, name_tokens, infer_type_unit, unique_shortnames, resolve_param_specs, M4LDevice, build_m4l_device"
      contains: "def export_amxd"
    - path: "src/maxpat/builders.py"
      provides: "BuildersMixin.add_m4l_device; add_m4l_gen_synth delegating to it"
      contains: "def add_m4l_device"
    - path: "src/maxpat/m4l_constants.py"
      provides: "corrected AMXD chunk comment, AMXD_CHUNK_HEADER, AMXD_PAYLOAD_TERMINATOR"
      contains: "AMXD_PAYLOAD_TERMINATOR"
    - path: "src/maxpat/m4l_polish.py"
      provides: "pure plan_push_banks(longnames) used by organize_push_banks and the builder"
      contains: "def plan_push_banks"
    - path: "src/maxpat/critics/m4l_critic.py"
      provides: "8 Q40 rules wired into review_m4l"
      contains: "_check_stereo_out"
    - path: "tests/test_m4l_gen_synth_golden.py"
      provides: "pre-refactor golden of add_m4l_gen_synth"
      contains: "m4l_gen_synth_golden.json"
    - path: "tests/fixtures/kicksynth-m4l.amxd"
      provides: "real .amxd (git show 494c2e64), 103996 bytes, for the byte round-trip"
    - path: "tests/test_m4l_device.py"
      provides: "codec, export, inference, short names, wiring, init chain, banks, presentation, critic rule and parity tests"
      contains: "def test_kicksynth_byte_roundtrip"
    - path: ".planning/quick/261022-pqu-implement-q40-in-planning-reviews-2026-1/q40-live-check.amxd"
      provides: "the one device the user drags into Live for the combined Q15 + Q40 check"
  key_links:
    - from: "src/maxpat/builders.py"
      to: "src/maxpat/m4l_device.py"
      via: "add_m4l_device imports build_m4l_device lazily (import-cycle safety) and delegates"
      pattern: "build_m4l_device"
    - from: "src/maxpat/builders.py"
      to: "src/maxpat/builders.py"
      via: "add_m4l_gen_synth calls self.add_m4l_device with fully explicit specs"
      pattern: "self\\.add_m4l_device\\("
    - from: "src/maxpat/m4l_device.py"
      to: "src/maxpat/m4l_constants.py"
      via: "build_amxd / parse_amxd use AMXD_* tags, AMXD_CHUNK_HEADER and AMXD_PAYLOAD_TERMINATOR"
      pattern: "AMXD_CHUNK_HEADER|AMXD_PAYLOAD_TERMINATOR"
    - from: "src/maxpat/m4l_device.py"
      to: "src/maxpat/m4l_polish.py"
      via: "_abbreviate_shortname for short names, plan_push_banks for parameterbanks"
      pattern: "plan_push_banks|_abbreviate_shortname"
    - from: "src/maxpat/m4l_device.py"
      to: "src/maxpat/hooks.py"
      via: "export_amxd writes with atomic_write_bytes and commits via _auto_commit_saved_file"
      pattern: "_auto_commit_saved_file"
    - from: "src/maxpat/critics/m4l_critic.py"
      to: "review_m4l"
      via: "new device-level and per-scope checks appended in the existing top-level / nested blocks"
      pattern: "_check_stereo_out|_check_bank_refs|_check_device_height"
---

<objective>
Implement Q40 from .planning/reviews/2026-10-11-fix-plan.md:682 ("M4L device pipeline", review §5.9, .planning/reviews/2026-10-11-repo-review.md:407).

Spec (fix plan):
- `add_m4l_device(kind="instrument"|"audio_effect"|"midi_effect")` builds:
  - stereo plugin~/plugout~ wiring;
  - the live.thisdevice init chain;
  - parameters with type and unit inferred from range and name (stepped integer → Int, ms → Time, Hertz, deciBel, 0–1 → Float);
  - unique short names;
  - Push `parameterbanks`;
  - `.amxd` export using the header constants in `m4l_constants.py`, with the format verified against a bundled `.amxd`.
- Critic checks for the result.
- Mark it experimental until the user confirms it loads in Live.

Locked by the user (CONTEXT.md):
- **Q15 gate:** proceed although Q15 (261014-d13) is still `human_needed`. Build on Q15's forms. Everything Q40 adds is EXPERIMENTAL. ONE Live check device plus checklist covers the pending Q15 items and Q40.
- **Export:** a separate `export_amxd(patcher_or_path, out_path, kind)`; the .maxpat stays the source of truth. Verify against kicksynth-m4l.amxd and a bundled .amxd, with a round-trip test.
- **Builder:** `add_m4l_device` is the generic skeleton. `add_m4l_gen_synth` is refactored to call it, and its output is proven unchanged by golden tests committed BEFORE the refactor.
- **Param spec:** dicts `{name, min, max, default, unit?, type?, steps?, short_name?}`, inference with explicit override, unique short names.

Claude's discretion (resolved here, grounded in DB lookups, refpages and bundle files at planning time):
- Module placement: new `src/maxpat/m4l_device.py` holds the codec, export, inference, short names and the device builder. `BuildersMixin.add_m4l_device` is a thin delegate, because builders.py is already 1204 lines.
- MIDI effect: `midiin` → `midiout` pass-through, as in Live's "Max MIDI Effect.amxd". It has no plugin~.
- Init chain: `live.thisdevice` outlet 0 → `t b …` → each control without `param_connect` (bundle idiom `t … b`; refpage: outlet 0 bangs when the device is initialized, on preset load and on save).
- Critic list: the 8 rules in Task 3, all warning or note.
- New-builder ModMode default: NONE (0), which kicksynth-m4l used and Live loaded. Legacy keeps ABSOLUTE. The checklist asks the user to decide (Q15 item 4).
- The spec dict also accepts `varname`, `param_connect` and `modmode`. The legacy path needs them to stay byte-identical, and gen~ binding needs param_connect.

Live state at planning time (HEAD ec987817, after Q39; Q39 final run: 6127 passed, 5 xfailed, 1 xpassed):
- No .amxd writer exists in src/. An earlier `src/maxpat/m4l_export.py::write_amxd` (b9710c35) was deleted in cb889d9b, a commit unrelated to it. It wrote tab-indented JSON with no `\n\0` terminator. Do not resurrect it.
- There are no M4L patches among the 63 tracked patches/*.maxpat, so the new critic rules cannot change corpus findings.
- `.claude/skills/max-router/references/dispatch-rules.md:124` says "there is no .amxd writer". That becomes false, but fix-plan rule 8 limits doc edits to CLAUDE.md here (CONTEXT names only the CLAUDE.md M4L section). SUMMARY lists it as the first doc follow-up.

Purpose: an agent can build a Live device of any of the three kinds with correct wiring, parameter metadata and Push banks, and hand the user an .amxd they can drag into Live. One Live session then confirms both Q15 and Q40.
Output: m4l_device.py, add_m4l_device, refactored add_m4l_gen_synth, plan_push_banks, 8 critic rules, tests, CLAUDE.md M4L section, one Live check device (.maxpat + .amxd) and a checklist.

Out of scope:
- Live 12 MIDI Tool kinds (`natt`/`nagg`);
- frozen-device (mx@c) or encrypted (ciph) export or editing;
- Enum/Blob parameters and the Custom unit style;
- check devices for audio_effect/midi_effect (CONTEXT says one device);
- doc edits outside the CLAUDE.md M4L section (listed in SUMMARY instead).
</objective>

<assumption_delta_decision>
primary_noun: M4L device builder
transition: one specific builder (add_m4l_gen_synth, instrument + gen~ only) -> a generic skeleton for three device kinds (add_m4l_device)
decision: promote
rationale: add_m4l_device becomes the primary representation (wiring, params, init, banks, presentation). add_m4l_gen_synth becomes a variant that calls it with fully explicit specs and all new features switched off.
invariant_test: tests/test_m4l_gen_synth_golden.py. The legacy serialized output is key-order-identical before and after the promotion. It is committed before the refactor.
</assumption_delta_decision>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@./CLAUDE.md
@.planning/quick/261022-pqu-implement-q40-in-planning-reviews-2026-1/261022-pqu-CONTEXT.md
@.planning/quick/261022-pqu-implement-q40-in-planning-reviews-2026-1/261022-pqu-RESEARCH.md
@.planning/quick/261014-d13-implement-q15-in-planning-reviews-2026-1/261014-d13-VERIFICATION.md

QDIR below means .planning/quick/261022-pqu-implement-q40-in-planning-reviews-2026-1. QDIR files stay uncommitted (snapshots, junit, scripts, notes). The exceptions are this PLAN and the SUMMARY (committed by the orchestrator) and the two Live check device files (committed explicitly in Task 3, Rule #7).

Rules for every task (fix-plan "Rules for every task", copied):
1. Read the referenced evidence first: review §5.9 item 9 (.planning/reviews/2026-10-11-repo-review.md:407), the Q15 VERIFICATION human items, and RESEARCH.md §1-§6.
2. Write each regression test first; it must be red before the fix and green after. The golden test is a characterization test and is green on the old code by design. Record red counts per task for SUMMARY.
3. Never edit committed patch files (`patches/**/*.maxpat|.gendsp|.maxhelp|.js`) or `patterns/`. A false positive on a committed patch means fixing the checker. A true positive gets an allowlist entry with a reason, listed in SUMMARY.
4. Run `python3 -m pytest -q` before (Step 0) and after (Task 3). The suite must stay fully green relative to the baseline.
5. Never `git stash`. Never `git add .` or `git add -A`. Stage explicit paths only (`git add -- <path>...`). Another instance may be active, so never stage outside this plan's files_modified (plus QDIR PLAN/SUMMARY at the end).
6. Python 3.10 compatible. Keep `from __future__ import annotations`. No `enum.StrEnum`, `typing.Self` or other 3.11+ features. Edited .py files pass `ast.parse(..., feature_version=(3, 10))`.
7. Don't widen scope. If a decision is not made by the report, CONTEXT or this plan, stop and ask with multiple-choice options.
8. Edit docs only where the task says (here only the CLAUDE.md M4L section). List other doc impact in SUMMARY.
9. In SUMMARY, flag everything that needs confirming in Live (the combined checklist in Task 3).
10. No existing test may change. All new tests go in tests/test_m4l_device.py or tests/test_m4l_gen_synth_golden.py. The one permitted edit to an existing test file is adding "src.maxpat.m4l_device" to `_INDEX_MODULES` in tests/test_doc_signatures.py (Task 3). If an existing test breaks because it pins a finding list that now gains a Q40 finding, the rule is too broad: narrow it.
11. Rule #1: use only objects verified in the DB at planning time (table below). Any other object needs an `ObjectDatabase().lookup()` with non-empty I/O and a `domain` check first.

<interfaces>
Verified at planning time (HEAD ec987817):
- DB (`ObjectDatabase().lookup`, restrictions all `[]`):
  - plugin~: MSP, 2 in / 2 out signal, variable_io False;
  - plugout~: MSP, 2/2 signal;
  - midiin: Max, 1/1;
  - midiout: Max, 1/0;
  - live.thisdevice: M4L, 1/3 (newobj);
  - live.dial: M4L, 1/2 (maxclass live.dial);
  - live.banks: M4L, 1/1 (newobj, not in UI_MAXCLASSES);
  - trigger: `compute_io_counts("trigger", ["b","b"]) == (1, 2)`;
  - dbtoa: Max 1/1; prepend: Max 1/1;
  - `"bang" in db.selectors("live.dial")`.
- `Patcher().add_box(name, args=None, x=0.0, y=0.0, skip_overlap_check=False) -> Box` (builders.py:42). Default sizes: live.dial 44x66, live.thisdevice 121x22, `t b b` 51x22, live.banks 86x22, plugin~ 65x22, plugout~ 90x22.
- `add_connection(src, outlet, dst, inlet)`; `add_to_presentation(box, rect)` sets `box.presentation` / `box.presentation_rect` (patcher.py:643). `Patcher.props` is an ordered dict that defaults to `devicewidth: 0.0` and `openinpresentation: 0`, with no `parameters` key. `to_dict()` emits props in insertion order.
- `add_m4l_gen_synth` (builders.py:1039-1163). Order:
  1. `add_gen(code, num_inputs=0, num_outputs=1, x=200.0, y=200.0)` gives obj-1, plus `varname`;
  2. `add_box("plugout~", x=200.0, y=400.0)` gives obj-2;
  3. connect gen:0 → plugout:0, then gen:0 → plugout:1;
  4. dials at `x=50.0 + 60.0*i, y=100.0, skip_overlap_check=True`. Each dial's extra_attrs are inserted in the order varname, param_connect, parameter_enable, saved_attribute_attributes. The valueof keys are listed in must_haves.
  It raises `ValueError("params must not be empty")` before building. Its output is deterministic (same sha256 across runs).
- m4l_constants.py:97-110: AMXD_MAGIC b"ampf", AMXD_VERSION 4, AMXD_META_MARKER b"meta", AMXD_META_VERSION 4, AMXD_PATCH_MARKER b"ptch", AMXD_TYPE_* aaaa/iiii/mmmm, AMXD_HEADER_FORMAT "<4sI4s4sI4x4sI", AMXD_HEADER_SIZE 32. tests/test_m4l_constants.py:124-140 pins these names and values. The comment block at :86-95 mislabels "version" (actually the ampf chunk length), "meta version" (the meta chunk length) and "padding" (the meta payload).
- `maxjson.dumps_max(obj, indent="    ") -> str` has no trailing newline. `atomic_io.atomic_write_bytes(path, payload)`. `hooks._auto_commit_saved_file(path) -> str | None` never raises. It warns "not inside a git repository" or "outside patches/<project>/ … not auto-committed".
- m4l_polish:
  - `_abbreviate_shortname(longname, max_len=8)` (:99);
  - `_classify_parameter` (:567);
  - `organize_push_banks(patch_dict)` (:592) builds `{str(i): {"index": i, "name": …, "parameters": [8 slots, "-" padded]}}` in group-first-appearance order;
  - `_banks_replaceable(existing)`;
  - `polish_m4l_device(patch_dict)` runs: enable, prefixes, names, banks, info text.
- critics/m4l_critic.py:
  - `review_m4l(patch_dict, device_type=None, *, graph=None)` (:120). Top-level block at :151-162; nested loop at :164-171 with `tag_results(found, scope.path)`.
  - Helpers: `_scope_boxes(scope)`, `_device_scopes(graph)`, `_collect_parameter_longnames(graph)`, `_box_longname(box)`, `LIVE_PARAMETER_OBJECTS`, `detect_m4l_device_type(patch_dict, *, graph=None)`.
  - `graph.Edge(src, outlet, dst, inlet, signal, line)`; `scope.edges`, `scope.boxes` (id → box), `scope.box_list`, `scope.path`, `scope.key`, `graph.top.patcher`.
  - `CriticResult(severity, finding, suggestion, path="", *, rule="", box_ids=(), port=None, fix=None)`; `finding_ids(*ids)`.
- Parity helpers to copy (not import): tests/test_critics_recursive.py `_box` (:41), `_line` (:56), `_inner` (:60), `_container` (:66), `_patch` (:72), `_plugout` (:561), `_dial` (:873). tests/test_critics_recursive.py:1031-1040 `test_nested_junk_never_raises` runs review_m4l on a junk scope that has a string inlet ("0"). TestBundleSweep (:1056, requires_max) runs review_patch over every bundle patch.
- Real files:
  - `/Applications/Max.app/Contents/Resources/Examples/resources/fourin_fourout.amxd`: 4692 B, aaaa, meta 0, ends `\n}\n\0`;
  - `/Applications/Ableton Live 12 Suite.app/Contents/App-Resources/Misc/Max Devices/` holds `Max Instrument.amxd` (iiii, 3800 B), `Max Audio Effect.amxd` (aaaa, 4478 B) and `Max MIDI Effect.amxd` (mmmm, 3350 B);
  - `git show 494c2e64:patches/kicksynth/generated/kicksynth-m4l.amxd`: iiii, meta 0, 103996 B, ends `\n}` with no terminator.
  - `.amxd` is not gitignored.
- tests/test_doc_signatures.py:58 `_INDEX_MODULES`. Index names are first-wins (`setdefault`). `Patcher.` receivers bind against Patcher methods.
- tests/test_claude_md.py: `CLAUDE_BUDGET_BYTES = 30_000` (CLAUDE.md is 28067 B now). RULE_ANCHORS include "plugout~", "param_connect", "parameter_enable: 1", "saved_attribute_attributes.valueof", "add_m4l_gen_synth" and the heading "### Max for Live (M4L / .amxd)".
</interfaces>
</context>

<tasks>

<task type="tracer" tdd="true">
  <name>Task 1 (tracer): golden pre-refactor commit, then instrument/audio/MIDI device → add_m4l_device → .maxpat dict → export_amxd → parse_amxd round trip</name>
  <files>tests/fixtures/expected/m4l_gen_synth_golden.json, tests/test_m4l_gen_synth_golden.py, tests/fixtures/kicksynth-m4l.amxd, src/maxpat/m4l_constants.py, src/maxpat/m4l_device.py, src/maxpat/builders.py, tests/test_m4l_device.py</files>
  <precondition>`git status --porcelain src tests .claude CLAUDE.md TECHNICAL.md` is empty and ec987817 (Q39) is an ancestor of HEAD.</precondition>
  <read_first>
    - .planning/quick/261022-pqu-implement-q40-in-planning-reviews-2026-1/261022-pqu-RESEARCH.md §1, §2, §3, §4
    - src/maxpat/m4l_constants.py (whole file)
    - src/maxpat/builders.py lines 1-120 and 1039-1163
    - src/maxpat/m4l_polish.py lines 95-140
    - src/maxpat/maxjson.py lines 1-40 and 117-130; src/maxpat/atomic_io.py lines 73-87; src/maxpat/hooks.py lines 64-138
    - src/maxpat/critics/m4l_critic.py lines 85-120
    - tests/test_m4l_gen_synth.py lines 1-30; tests/test_edit_session.py lines 25-85 (git temp-repo helpers)
  </read_first>
  <behavior>
    tests/test_m4l_gen_synth_golden.py (Part A, before any src edit):
    - The fixture holds 4 cases, each the `Patcher().to_dict()` after add_m4l_gen_synth (warnings suppressed):
      - "default": [("freq", 20.0, 2000.0), ("amp", 0.0, 1.0)];
      - "varname_osc": [("freq", 100.0, 1000.0)], gen_varname="osc";
      - "custom_code": [("cutoff", 20.0, 20000.0), ("res", 0.0, 1.0)] with an explicit gen_code;
      - "ten_params": freq, amp, attack_ms 1.0–500.0, cutoffHz, gain_db -70.0–0.0, octave -2–2 (ints), steps 1–16 (ints), pan -1.0–1.0, "Filter Envelope Amount", mix.
    - The test rebuilds each case and asserts `json.dumps(actual, indent=2) == json.dumps(expected_case, indent=2)`. This text comparison is key-order-sensitive, because json.load keeps order. It also asserts the returned (gen, dials, plugout) ids are obj-1, obj-3…, obj-2.

    tests/test_m4l_device.py (Task 1 cases):
    - Codec:
      - `test_kicksynth_byte_roundtrip`: tests/fixtures/kicksynth-m4l.amxd gives code b"iiii", meta 0, and `build_amxd(f.code, f.payload, f.meta) == data`. `decode_payload` returns a dict with patcher.boxes.
      - fourin_fourout (`@pytest.mark.requires_max`): aaaa, meta 0, payload ends b"\n\x00", identical rebuild.
      - The 3 Live templates (skipif the Live dir is missing): codes iiii/aaaa/mmmm, meta 0, identical rebuild.
      - A synthetic `ampf ptch` file (no meta) parses with meta None and rebuilds identically.
      - Each refusal raises ValueError: ciph chunk, mx@c payload (message contains "frozen"), chunk length past the end, trailing bytes, first tag not ampf, no ptch, kind code b"natt", invalid UTF-8 in decode_payload.
    - Export:
      - For each kind, `export_amxd(d, tmp/x.amxd, kind)` gives bytes[:32] == `struct.pack(AMXD_HEADER_FORMAT, AMXD_MAGIC, AMXD_VERSION, code, AMXD_META_MARKER, AMXD_META_VERSION, AMXD_PATCH_MARKER, N)`, `len == 32 + N`, a payload ending b"\n\x00", and `decode_payload(parse_amxd(...).payload) == d`.
      - Against the Live template of the same kind (skipif): bytes[0:28] are equal.
      - Path form: a .maxpat in tmp_path exports to the same stem with .amxd; the .maxpat bytes are unchanged.
      - out_path "x.maxpat" raises ValueError and writes nothing. project.amxdtype 1633771873 (aaaa) with kind "instrument" raises ValueError. A dict with no device markers and kind None raises ValueError.
      - Temp git repo with patches/demo/dev.maxpat committed: export_amxd(path) makes a HEAD commit whose name-only list is exactly patches/demo/dev.amxd.
      - Module setup copies tests/test_edit_session.py's pytestmark (skip without git; ignore the "not auto-committed" UserWarning).
    - Inference table (resolve_param_specs on single-param lists; (type, unit) as ints). Each line is spec → expected:
      - freq 20.0–2000.0 → (0, 3); "Filter Cutoff" 20.0–20000.0 → (0, 3); cutoffHz 0.0–1.0 → (0, 3);
      - cutoff 0.0–1.0 → (0, 1); attack 1.0–500.0 → (0, 2); delay_ms 0.0–1.0 → (0, 2);
      - harmonics 1.0–16.0 → (0, 1); gain 0.0–1.0 → (0, 1); "Out Gain" -70.0–0.0 → (0, 4);
      - gain_dB 0.0–6.0 → (0, 4); volume 0.0–2.0 → (0, 1); pan -50.0–50.0 → (0, 6);
      - transpose -24–24 ints → (1, 7); Octave -2–2 ints → (1, 0); steps 1–16 ints → (1, 0);
      - "Delay Time" 0–5000 ints → (0, 2); notes 0–1000 ints → (0, 0);
      - an explicit {"type": "int", "unit": "ms"} on freq → (1, 2);
      - steps=5 on a float range → parameter_steps 5, type unchanged.
    - Short names:
      - "Filter Envelope Amount" + "Pitch Envelope Amount" → ["Amount", "Amount2"];
      - an explicit short_name "Amount" first → the auto ones become "Amount2", "Amount3";
      - explicit long names are kept verbatim;
      - every auto name is ≤ 8 characters.
    - Validation: each case in must_haves truth 6 raises ValueError.
    - Builder wiring (cords as (src, outlet, dst, inlet) on box names):
      - audio_effect: exactly {(plugin~, 0, plugout~, 0), (plugin~, 1, plugout~, 1)};
      - midi_effect: exactly {(midiin, 0, midiout, 0)};
      - instrument: a midiin, a plugout~ and no I/O cords; `midi_in=False` has no midiin;
      - instrument with audio_source=(cycle box, 0): (cycle~, 0, plugout~, 0) and (cycle~, 0, plugout~, 1);
      - a stereo pair source gives L→0 and R→1;
      - audio_effect with audio_source: no plugin~→plugout~ cord;
      - midi_effect with midi_source: no midiin→midiout cord, source→midiout:0;
      - audio_source on midi_effect raises ValueError;
      - plugin~/plugout~ text is bare and args are empty.
    - Dials: the extra_attrs key order and valueof key order equal the legacy order (must_haves). Values come from resolve_param_specs. min/max/default are written exactly as given, with no coercion.
    - Presentation:
      - for n in (1, 8, 9, 24, 25, 40), every dial has presentation 1 with the grid rect and bottom ≤ 169;
      - props: openinpresentation 1, devicewidth 8 + 52*ncols, openrect [0.0, 0.0, 0.0, 169.0], latency 0;
      - `presentation=False` leaves the props untouched;
      - no BoxMovedWarning is recorded.
    - Tracer E2E: for each kind, `review_patch(p.to_dict())` has zero blockers. The instrument with a cycle~ source goes to_dict → export_amxd → parse_amxd → code iiii and an equal decoded dict.
  </behavior>
  <action>
**Step 0. Baseline, before any edit** (Q39 pattern):
- Write `git rev-parse HEAD` to QDIR/base-sha.txt, `git stash list` to QDIR/stash-list-before.txt, and `git status --porcelain patches patterns` to QDIR/patches-status-before.txt.
- Copy .planning/quick/261022-o2q-implement-q39-in-planning-reviews-2026-1/junit_diff.py to QDIR/junit_diff.py. Change only the copy:
  - its docstring says it is the Q40 gate (quick 261022-pqu);
  - the `ours` predicate accepts keys starting with `tests.test_m4l_device` or `tests.test_m4l_gen_synth_golden`;
  - ALLOWED_REMOVED stays empty, with its length asserted to be 0.
- Run `python3 -m pytest -q -p no:cacheprovider --junitxml=QDIR/baseline-junit.xml > QDIR/baseline-pytest.txt 2>&1` and write the exit code to QDIR/baseline-rc.txt.
  - Exit 2 or more: stop and report.
  - Exit 1: record the failing ids in SUMMARY as pre-existing.
  - Expected: 6127 passed, 5 xfailed, 1 xpassed.

**Part A. Golden test, committed before any src change** (CONTEXT: Builder API, golden before refactor):
- Generate tests/fixtures/expected/m4l_gen_synth_golden.json from the CURRENT add_m4l_gen_synth for the 4 cases in `<behavior>`. Use a one-off `python3 -c` that runs to_dict and `json.dump(..., indent=2)`; do not commit a generator script (Rule #5).
- Write tests/test_m4l_gen_synth_golden.py and run it (green).
- `git add -- tests/fixtures/expected/m4l_gen_synth_golden.json tests/test_m4l_gen_synth_golden.py` and commit `test(m4l): golden of add_m4l_gen_synth before the Q40 refactor (quick 261022-pqu, Q40)`. This commit must touch no src/ path.

**Part B. Tests first.**
- Vendor the real file: `git show 494c2e64:patches/kicksynth/generated/kicksynth-m4l.amxd > tests/fixtures/kicksynth-m4l.amxd`. Check that it is 103996 bytes and starts with `ampf`.
- Write the Task 1 cases of tests/test_m4l_device.py. Run them and record the red count.

**Part C. m4l_constants.py.**
- Rewrite the AMXD comment block as a chunk stream: `[tag][uint32 LE length][payload]` repeated.
  - `ampf`: length 4, payload = the kind code.
  - `meta`: length 4, payload = uint32 flags, 0 for every editable Max-written device; 1/4/7 seen in Max 8 saves and frozen files.
  - `ptch`: length N, payload = UTF-8 patcher JSON that Max ends with `\n\0`.
  - Say that AMXD_VERSION and AMXD_META_VERSION are the chunk lengths, and that AMXD_HEADER_FORMAT is for writing only (its `4x` drops the meta payload; parse chunk-wise). Cite the RESEARCH survey (309 files, Live 12 templates, fourin_fourout, kicksynth).
- Add `AMXD_CHUNK_HEADER = "<4sI"` and `AMXD_PAYLOAD_TERMINATOR = b"\n\x00"`.
- Keep every existing name and value.

**Part D. src/maxpat/m4l_device.py (new).**
- Module docstring: EXPERIMENTAL, not yet confirmed in Live (Q15/Q40 Live check pending), plus the evidence summary.
- Module-level imports: stdlib, m4l_constants, maxjson and atomic_io only. Import m4l_polish, critics.m4l_critic and hooks inside the functions that use them; builders.py, patcher.py and the critics must not form an import cycle.
- Codec:
  - `KIND_CODES = {"audio_effect": AMXD_TYPE_AUDIO_EFFECT, "instrument": AMXD_TYPE_INSTRUMENT, "midi_effect": AMXD_TYPE_MIDI_EFFECT}` plus the reverse map.
  - `@dataclass(frozen=True) AmxdFile(code: bytes, meta: int | None, payload: bytes)` with a `kind` property.
  - `build_amxd(kind_or_code, payload, meta=0) -> bytes`: emit the ampf chunk, the meta chunk only when meta is not None, then the ptch chunk.
  - `parse_amxd(data) -> AmxdFile`: a chunk loop with `struct.unpack_from(AMXD_CHUNK_HEADER)`.
    - Bounds-check every length against the remaining bytes.
    - The first chunk must be ampf with length 4 and a known code.
    - meta is optional (length 4).
    - A `ciph` chunk or a ptch payload starting with b"mx@c" raises ValueError("frozen/encrypted device ... cannot export or edit").
    - Any other tag, a missing ptch, or bytes after the last chunk raise ValueError.
    - Never parse through AMXD_HEADER_FORMAT.
  - `encode_payload(patch_dict) -> bytes` returns `dumps_max(patch_dict).encode("utf-8") + AMXD_PAYLOAD_TERMINATOR`. It requires a dict with a "patcher" dict.
  - `decode_payload(payload) -> dict` strips exactly one trailing b"\x00", then decodes strict UTF-8 and runs json.loads. It never evaluates anything.
- `export_amxd(patcher_or_path, out_path=None, kind=None) -> Path` (EXPERIMENTAL in the docstring):
  - Accept a Patcher (to_dict), a dict, or a str/Path to a .maxpat (json.loads of the file text).
  - `out_path` defaults to the path argument with an .amxd suffix. It is required for a Patcher or dict. A suffix other than .amxd raises ValueError.
  - `kind=None` uses `detect_m4l_device_type`; None raises ValueError. An unknown kind name raises ValueError.
  - When `patcher.project.amxdtype` exists and differs from `int.from_bytes(code, "big")`, raise ValueError. Never inject a `project` block.
  - Write with `atomic_write_bytes`, then `hooks._auto_commit_saved_file(out)`. Return the out Path.
  - The docstring says: save the .maxpat through save_patch_roundtrip first; the .maxpat is the source of truth.
- Param resolution:
  - `name_tokens(name)`: split on non-alphanumerics. A piece whose lowercase is ms/hz/db is one token; otherwise camelCase/digit-split it (`cutoffHz` → cutoff, hz; `freq1` → freq, 1). Lowercase everything.
  - `infer_type_unit(name, mn, mx, default) -> (type, unit)` follows the rule order in must_haves truth 5.
  - `unique_shortnames(longnames, explicit) -> list[str]` follows truth 6.
  - `resolve_param_specs(params, *, modmode=ModMode.NONE) -> list[dict]`. Required keys: name, min, max, default. Allowed optional keys: unit, type, steps, short_name, varname, param_connect, modmode.
    - `type` accepts a ParamType, an int, or "float"/"int"; Enum/Blob raise.
    - `unit` accepts a UnitStyle 0-8, an int, a member name, or ms/hz/db/%; Custom raises.
    - `modmode` accepts a ModMode, an int or a member name.
    - varname = name when it is a valid identifier, else the lowercased `\W+` → `_` form. Duplicate names or varnames raise.
    - Return dicts with resolved ints.
- `@dataclass M4LDevice(kind, plugin, plugout, midiin, midiout, thisdevice, init_trigger, dials, banks)`. Unused fields are None, and dials is a list.
- `build_m4l_device(patcher, kind, params=None, *, audio_source=None, midi_source=None, midi_in=True, presentation=True, modmode=ModMode.NONE) -> M4LDevice` (Task 2 adds init_chain and banks). Box creation order is fixed so the legacy ids hold:
  1. plugin~ (audio_effect), or midiin (midi_effect, or instrument with midi_in) at (200, 340);
  2. plugout~ (instrument/audio_effect) or midiout (midi_effect) at (200, 400);
  3. I/O cords: inlet 0 before inlet 1;
  4. dials, created by `add_box("live.dial", x=50 + 60*i, y=100, skip_overlap_check=True)`. extra_attrs are set in the order varname, param_connect (only when given), parameter_enable 1, saved_attribute_attributes.valueof (keys as in must_haves). Values are written with `int()` for enums and as given for min/max/default.
  - When presentation is on and there is at least one dial: `add_to_presentation` with the grid rect, then the four props (truth 9).
  - Validate audio_source / midi_source shape and kind before creating anything. Raise ValueError for an unknown kind.

**Part E. builders.py.** Add `BuildersMixin.add_m4l_device(self, kind, params=None, *, ...)`. It lazily imports `build_m4l_device` and returns its result. The docstring covers the kinds, the wiring per kind (Live template evidence), the param-spec keys and the inference summary. Mark it EXPERIMENTAL, not yet confirmed in Live. Do not touch add_m4l_gen_synth in this task.

**Part F. Commit.** Run the verify pytest list and the ast 3.10 gate until green. Then `git add -- tests/fixtures/kicksynth-m4l.amxd src/maxpat/m4l_constants.py src/maxpat/m4l_device.py src/maxpat/builders.py tests/test_m4l_device.py` and commit `feat(m4l): add_m4l_device skeleton for three kinds and .amxd codec/export verified against real devices (quick 261022-pqu, Q40)`. Then run the full verify command.
  </action>
  <verify>
    <automated>python3 -m pytest -q -p no:cacheprovider tests/test_m4l_device.py tests/test_m4l_gen_synth_golden.py tests/test_m4l_gen_synth.py tests/test_m4l_constants.py tests/test_m4l_polish.py tests/test_critic_revival.py && python3 -c "import ast, sys; [ast.parse(open(f).read(), feature_version=(3, 10)) for f in sys.argv[1:]]" src/maxpat/m4l_device.py src/maxpat/builders.py src/maxpat/m4l_constants.py tests/test_m4l_device.py tests/test_m4l_gen_synth_golden.py && test -s .planning/quick/261022-pqu-implement-q40-in-planning-reviews-2026-1/base-sha.txt && test -s .planning/quick/261022-pqu-implement-q40-in-planning-reviews-2026-1/baseline-junit.xml && python3 -c "import sys, xml.etree.ElementTree as E; t = list(E.parse(sys.argv[1]).getroot().iter('testcase')); assert len(t) >= 6000, len(t); assert not [c for c in t if c.get('classname', '').startswith(('tests.test_m4l_device', 'tests.test_m4l_gen_synth_golden'))], 'baseline taken after new tests'" .planning/quick/261022-pqu-implement-q40-in-planning-reviews-2026-1/baseline-junit.xml && G=$(git log -1 --format=%H --diff-filter=A -- tests/fixtures/expected/m4l_gen_synth_golden.json) && test -n "$G" && git diff --quiet "$(cat .planning/quick/261022-pqu-implement-q40-in-planning-reviews-2026-1/base-sha.txt)" "$G" -- src && M=$(git log -1 --format=%H --diff-filter=A -- src/maxpat/m4l_device.py) && test -n "$M" && test "$G" != "$M" && git merge-base --is-ancestor "$G" "$M" && test "$(git cat-file -s HEAD:tests/fixtures/kicksynth-m4l.amxd)" = "103996" && test -z "$(git status --porcelain src tests)"</automated>
  </verify>
  <done>The golden test exists in a commit that precedes every src change. The .amxd codec rebuilds kicksynth, fourin_fourout and the Live templates byte-for-byte and refuses frozen, encrypted and malformed input. export_amxd writes Max's header and payload form and auto-commits path-scoped. add_m4l_device builds all three kinds with template wiring, inferred parameter metadata, unique short names and a 169 px presentation grid, with zero review blockers. Task 1 is committed.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: live.thisdevice init chain, Push parameterbanks via plan_push_banks, add_m4l_gen_synth refactored onto add_m4l_device</name>
  <files>src/maxpat/m4l_device.py, src/maxpat/builders.py, src/maxpat/m4l_polish.py, tests/test_m4l_device.py</files>
  <precondition>Task 1's commits are in HEAD, and tests/test_m4l_gen_synth_golden.py passes at HEAD.</precondition>
  <read_first>
    - src/maxpat/m4l_polish.py lines 555-700 (_BANK_KEYWORDS, _classify_parameter, organize_push_banks, _banks_replaceable) and 811-833 (polish_m4l_device)
    - src/maxpat/builders.py lines 1039-1163 (add_m4l_gen_synth)
    - src/maxpat/m4l_device.py (Task 1 output)
    - tests/test_m4l_polish.py lines 330-560 (TestPushBanks)
    - src/maxpat/critics/structure_critic.py lines 1160-1180 (_LOAD_SOURCES includes live.thisdevice)
  </read_first>
  <behavior>
    Added to tests/test_m4l_device.py:
    - Init chain:
      - all params bound (param_connect): live.thisdevice exists, there is no trigger, and no cord leaves thisdevice;
      - one unbound: thisdevice:0 → dial:0;
      - three unbound plus one bound: thisdevice:0 → `t b b b` (text exactly "t b b b", numoutlets 3), with outlet j → unbound dial j inlet 0 (j = 0, 1, 2) and no cord into the bound dial;
      - the thisdevice/t ids sort after every dial id (created later);
      - `init_chain=False` gives no live.thisdevice.
    - Detection: `detect_m4l_device_type(p.to_dict())` equals the kind for all three kinds (defaults), and export_amxd(kind=None) writes the matching code.
    - Banks:
      - `plan_push_banks(["freq", "amp", "Attack", "Octave"])` equals the parameterbanks that organize_push_banks writes for a patch with those 4 parameter dials (cross-check through the real function);
      - the builder sets `props["parameters"]["parameterbanks"] == plan_push_banks(longnames)` and adds exactly one newobj live.banks;
      - a patcher whose props already hold user-defined banks (a slot other than "-") keeps them and emits a UserWarning;
      - an existing live.banks box is reused;
      - `banks=False` or no params gives no parameters key and no live.banks.
    - Polish compatibility: `polish_m4l_device(p.to_dict())` keeps parameterbanks, every parameter_shortname, exactly one live.banks and every presentation rect, and adds annotations.
    - review_patch on each kind with defaults and mixed bound/unbound params has zero blockers. It has no fan_out_without_trigger finding and no uninitialized-state finding for the unbound dials.
    - Legacy delegation:
      - `inspect.getsource(Patcher.add_m4l_gen_synth)` contains "self.add_m4l_device(" and the literal f"{gen_varname}::{name}" f-string;
      - add_m4l_gen_synth with a duplicate name now raises ValueError (record as an intended deviation);
      - tests/test_m4l_gen_synth_golden.py and tests/test_m4l_gen_synth.py pass unedited.
  </behavior>
  <action>
**Part A. Tests first.** Write the Task 2 cases. Run them and record the red count.

**Part B. plan_push_banks (m4l_polish.py).**
- Extract the grouping and chunking body of organize_push_banks into a pure, public `plan_push_banks(longnames: list[str]) -> dict`. It classifies each name with `_classify_parameter`, groups in first-appearance order, chunks by 8, pads with "-", and names banks "Group", "Group 2"…
- It returns `{str(i): {"index": i, "name": …, "parameters": […]}}`, or {} for no names.
- organize_push_banks collects longnames exactly as before and calls it. Its behavior, the live.banks handling and `_banks_replaceable` are unchanged; tests/test_m4l_polish.py must pass unedited.
- Docstring: the builder and polish share it.

**Part C. Init chain and banks in build_m4l_device** (Q40: live.thisdevice init chain, Push parameterbanks). Add keyword args `init_chain=True` and `banks=True` to build_m4l_device and to `BuildersMixin.add_m4l_device`. Creation order after the dials:
1. When init_chain is on: `add_box("live.thisdevice", x=50, y=20, skip_overlap_check=True)`.
   - Unbound dials (those with no param_connect): k = 1 → cord thisdevice:0 → dial:0.
   - k ≥ 2 → `add_box("t", ["b"] * k, x=50, y=60, skip_overlap_check=True)`, cord thisdevice:0 → t:0, then t:j → unbound[j]:0 for j in order.
   - The docstring explains: refpage live.thisdevice outlet 0 bangs when the device is initialized, on preset load and on save. A banged live.dial re-outputs its value. Mark this [ASSUMED] for Live and part of the Live check. gen~-bound dials are served by param_connect.
2. When banks is on and there are params: `parameters = patcher.props.setdefault("parameters", {})`.
   - When `_banks_replaceable(parameters.get("parameterbanks"))`, set it to `plan_push_banks(longnames)`. Otherwise keep it and `warnings.warn(..., UserWarning)`.
   - Reuse any box named live.banks, else `add_box("live.banks", x=350, y=400, skip_overlap_check=True)`.
- Fill M4LDevice.thisdevice, init_trigger and banks.

**Part D. Refactor add_m4l_gen_synth onto add_m4l_device** (CONTEXT: refactor; the output must stay byte-identical).
- Keep the empty-params ValueError, the default gen_code construction, the add_gen call and the gen varname exactly as they are.
- Then build one spec dict per tuple with every key explicit:
  - name, min, max;
  - default = (mn + mx) / 2.0, varname = name, short_name = name;
  - type ParamType.FLOAT, unit UnitStyle.FLOAT, modmode ModMode.ABSOLUTE;
  - param_connect = f"{gen_varname}::{name}" (keep this exact f-string literal: T-31-04).
- Call `self.add_m4l_device("instrument", specs, audio_source=(gen_obj, 0), midi_in=False, init_chain=False, banks=False, presentation=False)` and return `(gen_obj, dev.dials, dev.plugout)`.
- Update the docstring: it is built on add_m4l_device and EXPERIMENTAL. ValueError is now also raised for duplicate names, min ≥ max, and a default outside the range.
- If the golden test fails, the fix goes in build_m4l_device (order or keys), never in the fixture.

**Part E. Commit.** Run the verify pytest list and the ast gate until green. Then `git add -- src/maxpat/m4l_device.py src/maxpat/builders.py src/maxpat/m4l_polish.py tests/test_m4l_device.py` and commit `feat(m4l): live.thisdevice init chain, shared Push bank planner, add_m4l_gen_synth built on add_m4l_device (quick 261022-pqu, Q40)`.
  </action>
  <verify>
    <automated>python3 -m pytest -q -p no:cacheprovider tests/test_m4l_device.py tests/test_m4l_gen_synth_golden.py tests/test_m4l_gen_synth.py tests/test_m4l_polish.py tests/test_m4l_constants.py tests/test_critic_revival.py tests/test_critics_recursive.py tests/test_uninitialized_state.py && python3 -c "import ast, sys; [ast.parse(open(f).read(), feature_version=(3, 10)) for f in sys.argv[1:]]" src/maxpat/m4l_device.py src/maxpat/builders.py src/maxpat/m4l_polish.py tests/test_m4l_device.py && G=$(git log -1 --format=%H --diff-filter=A -- tests/fixtures/expected/m4l_gen_synth_golden.json) && test -n "$G" && git diff --quiet "$G" HEAD -- tests/fixtures/expected/m4l_gen_synth_golden.json tests/test_m4l_gen_synth_golden.py tests/test_m4l_gen_synth.py tests/test_m4l_polish.py && grep -q "self.add_m4l_device(" src/maxpat/builders.py && grep -q "def plan_push_banks" src/maxpat/m4l_polish.py && test -z "$(git status --porcelain src tests)"</automated>
  </verify>
  <done>Devices of every kind carry a live.thisdevice init chain that bangs exactly the unbound controls. They get Push parameterbanks from the shared planner and a single live.banks, and they survive polish unchanged. add_m4l_gen_synth delegates to add_m4l_device, and the golden, gen-synth and polish tests pass unedited. Task 2 is committed.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: 8 M4L critic rules, CLAUDE.md M4L section, combined Q15+Q40 Live check device, final regression gate</name>
  <files>src/maxpat/critics/m4l_critic.py, tests/test_m4l_device.py, CLAUDE.md, tests/test_doc_signatures.py, .planning/quick/261022-pqu-implement-q40-in-planning-reviews-2026-1/q40-live-check.maxpat, .planning/quick/261022-pqu-implement-q40-in-planning-reviews-2026-1/q40-live-check.amxd</files>
  <precondition>Task 2's commit is in HEAD.</precondition>
  <read_first>
    - src/maxpat/critics/m4l_critic.py (whole file)
    - src/maxpat/critics/base.py lines 1-110
    - tests/test_critics_recursive.py lines 35-80, 555-570, 690-725, 870-930 and 1025-1100
    - CLAUDE.md lines 205-216 (the M4L section)
    - tests/test_doc_signatures.py lines 55-125
    - .planning/quick/261014-d13-implement-q15-in-planning-reviews-2026-1/261014-d13-VERIFICATION.md (human_verification)
  </read_first>
  <behavior>
    Added to tests/test_m4l_device.py (fixtures are hand-built dicts with explicit outlettype, or builder output):
    - stereo_out (warning, per scope):
      - a bare plugout~ fed by a signal cord on inlet 0 only gives one finding starting "plugout~ (" and naming inlet 0; inlet 1 only is the same;
      - both inlets, or no signal cord at all (Live's instrument template), gives none;
      - `plugout~ 1` with args is not checked.
    - midi_passthrough (warning, per scope, device_type midi_effect only):
      - a lone midiin with no outgoing cord gives a finding; a midiout with no incoming cord gives a finding;
      - the pass-through gives none;
      - device_type instrument with a lone midiin (the Live template) gives none.
    - shortname_length (note, per scope): shortname "Frequency" (9) gives one; 8 or fewer, or a missing shortname, gives none.
    - int_param_range (warning, per scope): parameter_type 1 with 0..1000 gives one; type 1 with 0..255 gives none; type 0 with 0..1000 gives none.
    - param_range (warning, per scope):
      - mmin 10 / mmax 10 gives one; parameter_initial [500] outside 0..100 gives one;
      - a valid range gives none;
      - string/absent mmin and a non-list initial are skipped without raising.
    - shortname_unique (warning, device level): two dials with shortname "Amount", one top and one nested, give one finding naming both refs ("obj-3" and "obj-1/obj-3").
    - bank_refs (warning, device level): parameterbanks naming "Ghost" (absent) gives one finding naming Ghost; "-" slots and present longnames give none; non-dict banks are skipped without raising.
    - device_height (warning, device level): openinpresentation 1 and a presentation box at y 150 with h 48 gives one; bottom ≤ 169, or openinpresentation 0, gives none.
    - Nested parity: for each per-scope rule, the content wrapped in `p synth` (helpers copied from tests/test_critics_recursive.py) gives findings equal to the top-level ones with a "[p synth] " prefix and path "obj-1".
    - Builder cleanliness: none of the 8 rule ids appear in review_m4l for add_m4l_device output of each kind (defaults, 9 mixed params), nor for add_m4l_gen_synth output with names ≤ 8 characters.
    - Junk safety: review_m4l on a scope with string inlets, non-dict valueof and non-list bank parameters does not raise.
  </behavior>
  <action>
**Part A. Tests first.** Write the Task 3 cases. Run them and record the red count.

**Part B. Critic rules (critics/m4l_critic.py)** (Q40: critic checks for the result).
- Add the 8 rules (RESEARCH §6). rule = the function name minus `_check_`, and box_ids via finding_ids. All are non-blocking because the work is EXPERIMENTAL; say so in the module docstring with a Q40 paragraph.
  - Per scope, run in the top-level block (when top_is_device) and in the nested loop with tag_results:
    - `_check_stereo_out(scope)`: signal edges into a bare `plugout~` (text exactly "plugout~"). fed == {0} or {1} gives a warning "plugout~ (<id>) receives signal on inlet <i> only -- the other channel is silent", suggesting both inlets (a mono source feeds 0 and 1; Q15 D3).
    - `_check_midi_passthrough(scope, device_type)`: only when device_type is midi_effect. A midiin with no outgoing edge, or a midiout with no incoming edge, gives one warning per box (Live's MIDI Effect template wires midiin → midiout; a cut path blocks the track's MIDI).
    - `_check_shortname_length(boxes)`: a note for a LIVE_PARAMETER_OBJECTS box whose str shortname is longer than 8 (parameters.maxref: about 5-7 characters shown).
    - `_check_int_param_range(boxes)`: a warning when parameter_type == 1 and numeric mmax − mmin > 255 (parameters.maxref Type text; suggest Float type with Int unit style).
    - `_check_param_range(boxes)`: a warning when numeric mmin ≥ mmax, or when the first element of a list parameter_initial is a number outside [mmin, mmax].
  - Device level, run once, top-level results:
    - `_check_shortname_unique(graph)`: mirror _collect_parameter_longnames / _check_parameter_uniqueness for parameter_shortname, as a warning.
    - `_check_bank_refs(top_patcher, longnames)`: for each bank in a dict `parameters.parameterbanks`, collect the str slots that are not "-" and not a device longname. Give one warning listing them.
    - `_check_device_height(top_patcher, top_boxes)`: when openinpresentation is truthy, give one warning listing ids of presentation boxes whose numeric presentation_rect bottom > 169.
- Every check tolerates malformed values (non-dict valueof or parameters, non-numeric bounds, string inlets, non-list slots) by skipping. It never raises. Existing checks, their order and their findings are unchanged.

**Part C. Docs** (rule 8: only these two edits).
- CLAUDE.md "### Max for Live (M4L / .amxd)": keep the heading, the `**Experimental:**` line and every bullet. Replace the "> Codified (synth skeleton): …" line with one blockquote of at most 700 bytes that says:
  - `Patcher.add_m4l_device(kind, params)` (Q40; kind instrument / audio_effect / midi_effect) builds the skeleton: Live-template wiring, the live.thisdevice init chain, live.dial params with unit/type inferred from range and name (explicit keys win), unique short names and Push parameterbanks;
  - `Patcher.add_m4l_gen_synth(params)` (Phase 31) is built on it;
  - save the .maxpat (the source of truth), then `export_amxd(maxpat_path)` from `src.maxpat.m4l_device` writes the .amxd next to it;
  - both are unconfirmed in Live (the combined Q15/Q40 Live check is pending);
  - the rules below still apply.
  The file stays ≤ 30,000 bytes.
- tests/test_doc_signatures.py: append "src.maxpat.m4l_device" to `_INDEX_MODULES` (nothing else).

**Part D. One combined Live check device** (CONTEXT: Q15 gate). Build it in memory with a one-off `python3 -` invocation (not a committed script, Rule #5) and record its output in QDIR/live-check-save.txt.
- `p = Patcher()`. `add_gen` at (200, 200) with num_inputs=0, num_outputs=1 and this GenExpr, one statement per line, spaces only:
  - `Param freq(220, min=20, max=2000);`
  - `Param amp(0.5, min=0, max=1);`
  - `Param gain(0, min=0, max=1);`
  - `Param octave(0, min=-2, max=2);`
  - `out1 = cycle(freq * pow(2, octave)) * amp * gain;`
  Set the gen varname to "synth".
- `dev = p.add_m4l_device("instrument", params, audio_source=(gen, 0))` with these params:
  - freq 20.0–2000.0 default 220.0, param_connect "synth::freq", modmode "absolute";
  - amp 0.0–1.0 default 0.5, param_connect "synth::amp";
  - "Out Gain" -70.0–0.0 default -12.0;
  - "Octave" -2–2 default 0;
  - "Attack" 1.0–500.0 default 10.0;
  - "Filter Envelope Amount" 0.0–1.0 default 0.0;
  - "Pitch Envelope Amount" 0.0–1.0 default 0.0.
- Out Gain dial:0 → `dbtoa` → `prepend gain` → gen~:0. Octave dial:0 → `prepend octave` → gen~:0. Place these 3 boxes without overlap, below the dial row and right of gen~. Gen~'s Param gain defaults to 0, so the device is silent unless the init chain delivers Out Gain: that makes the init chain observable.
- `d = p.to_dict()`; `polish_m4l_device(d)`; `save_patch_roundtrip(d, QDIR/q40-live-check.maxpat)`. A new file refuses every blocker. If the gate refuses, stop and report the findings; never pass force.
- Then `export_amxd(QDIR/q40-live-check.maxpat)` gives QDIR/q40-live-check.amxd. Both writers warn "not auto-committed" (outside patches/), which is expected.
- In live-check-save.txt record:
  - the save result;
  - the parameterbanks;
  - per dial (longname, shortname, type, unitstyle, modmode, initial, bound or unbound);
  - the init-chain cords;
  - the .amxd first 32 bytes in hex and its size.
- `git add -- QDIR/q40-live-check.maxpat QDIR/q40-live-check.amxd` and commit `chore(quick-261022-pqu): combined Q15 + Q40 Live check device (.maxpat + .amxd)`.

**Part E. Code commit and final gate.**
- `git add -- src/maxpat/critics/m4l_critic.py tests/test_m4l_device.py CLAUDE.md tests/test_doc_signatures.py` and commit `feat(critics): M4L device checks for stereo out, MIDI pass-through, short names, ranges, bank refs and device height; CLAUDE.md M4L builder + export (quick 261022-pqu, Q40)`.
- Then run the full verify command. It runs the full suite with junit into QDIR/final-junit.xml and QDIR/final-pytest.txt (rc in QDIR/final-rc.txt) and runs junit_diff.

**Part F. SUMMARY content** (for the summary writer):
- EXPERIMENTAL status, stated plainly.
- Red counts per task. Baseline and final counts, plus the junit_diff output.
- Decisions: module placement; ModMode default NONE for the new builder (legacy ABSOLUTE); the MIDI-effect pass-through; the init-chain shape; the 8 rules and their severities; the presentation grid.
- Deviation: add_m4l_gen_synth now raises ValueError for duplicate names, min ≥ max, or a default outside the range. Such inputs used to produce a device the critic blocks.
- History note: write_amxd (b9710c35) was deleted in cb889d9b. It is not resurrected.
- Doc follow-ups, not edited per rule 8:
  - .claude/skills/max-router/references/dispatch-rules.md:115, :120 and :124 ("there is no .amxd writer" is now false);
  - .claude/skills/references/shared-capabilities.md "Builder API" (:175-226);
  - the builder lists in max-patch-agent/SKILL.md:81 and max-ui-agent/SKILL.md:87;
  - the max-critic skill's M4L check list;
  - TECHNICAL.md's M4L section.
- Assumptions A1-A5 from RESEARCH.
- **Live check (Q15 + Q40), one session.** Lower the track volume first. Drag QDIR/q40-live-check.amxd onto an empty MIDI track.
  1. (Q40) It loads as an Instrument in the instrument slot.
  2. (Q15) freq and amp move smoothly (continuous, not 0/1 steps).
  3. (Q15) Audio shows on both L and R of the track meter.
  4. (Q15) The Parameter Banks window or Push shows the banks recorded in live-check-save.txt.
  5. (Q15) ModMode: freq is Absolute, the others None. In a clip envelope, decide which default you want for new devices.
  6. (Q40) freq shows Hz, Attack shows ms, Out Gain shows dB, and Octave shows integers -2..2 in steps.
  7. (Q40) The two Envelope Amount dials show distinct short names ("Amount", "Amount2").
  8. (Q40) The tone is audible right after loading without touching Out Gain. Move Out Gain and Octave, save a Live preset, reload it: the level and octave match the stored values. Silence means the init chain does not fire.
  9. (Q40) Nothing is clipped at the bottom (169 px).
  Confirming 2-5 also closes Q15's human_verification (261014-d13).
  </action>
  <verify>
    <automated>python3 -m pytest -q -p no:cacheprovider tests/test_m4l_device.py tests/test_doc_signatures.py tests/test_claude_md.py tests/test_critics_recursive.py tests/test_critic_revival.py tests/test_m4l_polish.py tests/test_m4l_gen_synth_golden.py && python3 -c "import ast, sys; [ast.parse(open(f).read(), feature_version=(3, 10)) for f in sys.argv[1:]]" src/maxpat/critics/m4l_critic.py tests/test_m4l_device.py && python3 -W ignore -c "import sys, json; from pathlib import Path; from src.maxpat.m4l_device import parse_amxd, decode_payload; from src.maxpat.critics import review_patch; f = parse_amxd(Path(sys.argv[1]).read_bytes()); assert f.code == b'iiii' and f.meta == 0, f; d = decode_payload(f.payload); assert d == json.loads(Path(sys.argv[2]).read_text()); assert not [r for r in review_patch(d) if r.severity == 'blocker']" .planning/quick/261022-pqu-implement-q40-in-planning-reviews-2026-1/q40-live-check.amxd .planning/quick/261022-pqu-implement-q40-in-planning-reviews-2026-1/q40-live-check.maxpat && git cat-file -e HEAD:.planning/quick/261022-pqu-implement-q40-in-planning-reviews-2026-1/q40-live-check.amxd && git cat-file -e HEAD:.planning/quick/261022-pqu-implement-q40-in-planning-reviews-2026-1/q40-live-check.maxpat && { python3 -m pytest -q -p no:cacheprovider --junitxml=.planning/quick/261022-pqu-implement-q40-in-planning-reviews-2026-1/final-junit.xml > .planning/quick/261022-pqu-implement-q40-in-planning-reviews-2026-1/final-pytest.txt 2>&1; echo $? > .planning/quick/261022-pqu-implement-q40-in-planning-reviews-2026-1/final-rc.txt; } && python3 -c "import sys, xml.etree.ElementTree as E; base = int(any(x.tag in ('failure', 'error') for c in E.parse(sys.argv[1]).getroot().iter('testcase') for x in c)); fin = int(open(sys.argv[2]).read().strip()); print('baseline_rc', base, 'final_rc', fin); sys.exit(0 if base >= fin else 1)" .planning/quick/261022-pqu-implement-q40-in-planning-reviews-2026-1/baseline-junit.xml .planning/quick/261022-pqu-implement-q40-in-planning-reviews-2026-1/final-rc.txt && python3 .planning/quick/261022-pqu-implement-q40-in-planning-reviews-2026-1/junit_diff.py .planning/quick/261022-pqu-implement-q40-in-planning-reviews-2026-1/baseline-junit.xml .planning/quick/261022-pqu-implement-q40-in-planning-reviews-2026-1/final-junit.xml && test "$(git status --porcelain patches patterns)" = "$(cat .planning/quick/261022-pqu-implement-q40-in-planning-reviews-2026-1/patches-status-before.txt)" && test "$(git stash list)" = "$(cat .planning/quick/261022-pqu-implement-q40-in-planning-reviews-2026-1/stash-list-before.txt)" && git merge-base --is-ancestor "$(cat .planning/quick/261022-pqu-implement-q40-in-planning-reviews-2026-1/base-sha.txt)" HEAD && test -z "$(git log --name-only --format= "$(cat .planning/quick/261022-pqu-implement-q40-in-planning-reviews-2026-1/base-sha.txt)"..HEAD -- patches patterns)" && test "$(wc -c < CLAUDE.md)" -le 30000 && test -z "$(git status --porcelain src tests .claude CLAUDE.md TECHNICAL.md)"</automated>
  </verify>
  <done>The M4L critic reports the 8 Q40 rules as warnings or notes, with nested parity and junk safety, and it is silent on builder output. CLAUDE.md documents add_m4l_device and export_amxd as experimental. One committed .maxpat + .amxd Live check device passes the save gate. The full suite is no worse than baseline, junit_diff passes, and patches/, patterns/ and the stash list are untouched. SUMMARY carries the decisions, the doc follow-ups and the combined Q15 + Q40 Live checklist.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| .amxd file → parse_amxd | Bytes from any device file (Live packs, downloads, frozen devices) are untrusted input |
| patch dict / .maxpat → export_amxd → disk + git | export writes a binary next to the user's source of truth and commits it |
| param spec dicts → builder → Live parameter metadata | caller data becomes Live parameter names, ranges and binding strings |
| add_m4l_gen_synth callers → refactored builder | existing user-facing builder output must not drift |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-pqu-01 | Tampering / DoS | m4l_device.parse_amxd, decode_payload | medium | mitigate | chunk-wise loop that bounds-checks every uint32 length against the remaining bytes; rejects truncation, trailing bytes, unknown tags and kinds, ciph and mx@c; strict UTF-8; strips exactly one trailing NUL; json.loads only (no eval); refusal tests per case (ASVS V5) |
| T-pqu-02 | Tampering | export_amxd output path | medium | mitigate | out_path must end in .amxd (ValueError before any write), so a .maxpat source is never overwritten; atomic_write_bytes leaves the old file intact on error; tests assert the .maxpat bytes are unchanged |
| T-pqu-03 | Tampering | device kind header vs patch content | low | mitigate | an existing project.amxdtype that disagrees with the kind raises ValueError; kind=None uses detect_m4l_device_type and raises on None; header bytes compared against Live's own templates |
| T-pqu-04 | Repudiation | git history of exports | low | mitigate | _auto_commit_saved_file commits only the .amxd path under patches/<project>/ (temp-repo test asserts HEAD names exactly that path); the check device is committed with explicit paths; never `git add -A` |
| T-pqu-05 | Tampering (regression) | add_m4l_gen_synth refactor | medium | mitigate | key-order-sensitive golden fixture committed before any src change (verify checks commit ancestry and an empty src diff); the fixture and the gen-synth/polish tests are unchanged since (verify diff) |
| T-pqu-06 | Spoofing | param_connect binding strings | low | mitigate | legacy keeps the T-31-04 f-string literal (source-inspect test); duplicate names and varnames raise; the critic's duplicate longname and new duplicate shortname checks |
| T-pqu-07 | Information disclosure | exported payload | low | accept | the payload is exactly the patch dict the user saved; no env, paths or project block injected |
| T-pqu-SC | Tampering | npm/pip/cargo installs | high | accept | no package is installed by this plan (stdlib and existing src.maxpat only; RESEARCH: no Package Legitimacy Audit needed); the gate has nothing to check |
</threat_model>

<verification>
- Task 1 verify: the codec, export, inference, short-name and builder tests are green, including the real-file byte round trips; the golden commit precedes the m4l_device commit and touches no src; the baseline exists and predates the new tests.
- Task 2 verify: the init-chain, banks, polish-compatibility and delegation tests are green; the golden, gen-synth and polish tests are unchanged since the golden commit and still pass; src/ and tests/ are clean after the commit.
- Task 3 verify:
  - the 8 critic rules with parity and junk safety pass;
  - the doc and CLAUDE.md tests pass and CLAUDE.md is ≤ 30,000 bytes;
  - the committed check device parses as iiii/meta 0, round-trips to its .maxpat and has zero blockers;
  - the full suite is no worse than baseline and junit_diff passes;
  - patches/, patterns/ and the stash list are unchanged.
- Source audit (all COVERED):

| SOURCE | ID | Item | Plan | Status | Notes |
|---|---|---|---|---|---|
| GOAL | Q40 | M4L device builder and .amxd export | Tasks 1-3 | COVERED | |
| REQ | Q40-1a | stereo plugin~/plugout~ wiring | Task 1 | COVERED | template wiring per kind; mono source feeds both inlets (Q15 form) |
| REQ | Q40-1b | live.thisdevice init chain | Task 2 | COVERED | bangs unbound controls only |
| REQ | Q40-1c | type/unit inferred from range and name (Int, Time, Hertz, deciBel, 0–1 Float) | Task 1 | COVERED | token rules plus refpage's Int-span rule |
| REQ | Q40-1d | unique short names | Task 1 | COVERED | ≤ 8 chars, digit suffix |
| REQ | Q40-1e | Push parameterbanks | Task 2 | COVERED | shared plan_push_banks |
| REQ | Q40-1f | .amxd export with m4l_constants, verified against a bundled .amxd | Task 1 | COVERED | byte round trips: kicksynth, fourin_fourout, 3 Live templates |
| REQ | Q40-2 | critic checks for the result | Task 3 | COVERED | 8 rules |
| REQ | Q40-3 | mark experimental until confirmed in Live | Tasks 1-3 | COVERED | docstrings, CLAUDE.md, SUMMARY |
| CONTEXT | Q15 gate | proceed, build on Q15 forms, everything EXPERIMENTAL, ONE combined Live check + checklist | Tasks 1-3 | COVERED | q40-live-check.amxd + SUMMARY checklist (Q15 items 1-4 + Q40) |
| CONTEXT | export | separate export_amxd; .maxpat stays source of truth; round-trip test | Task 1 | COVERED | |
| CONTEXT | builder | add_m4l_device generic; add_m4l_gen_synth refactored; golden committed before refactor | Tasks 1-2 | COVERED | golden commit in Task 1 Part A, refactor in Task 2 |
| CONTEXT | param spec | dicts, inference, explicit keys win, unique short names | Task 1 | COVERED | extra optional keys varname/param_connect/modmode |
| CONTEXT | discretion | MIDI wiring, init chain, critic list, module placement | Tasks 1-3 | COVERED | grounded in templates, refpage, DB |
| RESEARCH | §1 | constants comment fix, chunk parser, `\n\0` terminator, refuse ciph/mx@c, amxdtype check | Task 1 | COVERED | |
| RESEARCH | §2 | device props (openinpresentation, devicewidth, openrect, latency), 169 px | Tasks 1, 3 | COVERED | builder + device_height rule |
| RESEARCH | §3 | bare plugin~/plugout~ only | Task 1 | COVERED | |
| RESEARCH | §4 | ModMode as a parameter | Task 1 | COVERED | default NONE; legacy ABSOLUTE; Live check item 5 |
| RESEARCH | §5 | refactor recipe, golden first, plan_push_banks extraction | Tasks 1-2 | COVERED | |
| RESEARCH | — | Live 12 MIDI Tool kinds natt/nagg | — | EXCLUDED | out of scope per RESEARCH |
| RESEARCH | OQ2 | check devices for audio_effect / midi_effect | — | EXCLUDED | CONTEXT locks one device; header codes verified against templates |
</verification>

<success_criteria>
- `p.add_m4l_device(kind, params)` builds an instrument, audio effect or MIDI effect. Each has Live-template wiring, inferred and overridable parameter metadata, unique short names, a live.thisdevice init chain, Push banks and a 169 px presentation, and each reviews with zero blockers.
- `export_amxd` writes an .amxd whose bytes follow Max's own form, verified against real devices, while the .maxpat stays the editable source.
- add_m4l_gen_synth produces exactly the bytes it did before (golden), now through the generic builder.
- The M4L critic warns on one-sided stereo, cut MIDI pass-through, short-name problems, bad ranges, dangling bank refs and over-tall devices.
- One committed check device plus a checklist lets one Live session confirm Q15 and Q40. Everything is marked EXPERIMENTAL until then.
- No committed patch changed, and the full suite is no worse than baseline.
</success_criteria>

<output>
Create `.planning/quick/261022-pqu-implement-q40-in-planning-reviews-2026-1/261022-pqu-SUMMARY.md` when done.
</output>
