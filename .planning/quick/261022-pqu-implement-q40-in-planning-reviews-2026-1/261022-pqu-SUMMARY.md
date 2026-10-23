---
phase: quick-261022-pqu
plan: 01
subsystem: m4l / builders / critics
tags: [Q40, m4l, amxd, live, builders, critics, experimental]
status: complete
requires: [Q15 M4L enums + stereo plugout~ + parameterbanks shape (261014-d13, still human_needed)]
provides:
  - src/maxpat/m4l_device.py (AmxdFile, parse_amxd, build_amxd, encode_payload, decode_payload, export_amxd, name_tokens, infer_type_unit, unique_shortnames, resolve_param_specs, M4LDevice, build_m4l_device)
  - Patcher.add_m4l_device
  - m4l_polish.plan_push_banks
  - 8 Q40 M4L critic rules
  - combined Q15 + Q40 Live check device
affects: [src/maxpat/builders.py add_m4l_gen_synth, src/maxpat/m4l_constants.py, src/maxpat/m4l_polish.py, src/maxpat/critics/m4l_critic.py, CLAUDE.md M4L section]
tech-stack:
  added: []
  patterns: [chunk-wise binary parser with bounds checks, golden characterization test committed before refactor, thin builder delegate with lazy import, shared pure planner]
key-files:
  created:
    - src/maxpat/m4l_device.py
    - tests/test_m4l_device.py
    - tests/test_m4l_gen_synth_golden.py
    - tests/fixtures/expected/m4l_gen_synth_golden.json
    - tests/fixtures/kicksynth-m4l.amxd
    - .planning/quick/261022-pqu-implement-q40-in-planning-reviews-2026-1/q40-live-check.maxpat
    - .planning/quick/261022-pqu-implement-q40-in-planning-reviews-2026-1/q40-live-check.amxd
  modified:
    - src/maxpat/builders.py
    - src/maxpat/m4l_constants.py
    - src/maxpat/m4l_polish.py
    - src/maxpat/critics/m4l_critic.py
    - CLAUDE.md
    - tests/test_doc_signatures.py
decisions:
  - "Module placement: codec, export, inference, short names and the device builder live in new src/maxpat/m4l_device.py; BuildersMixin.add_m4l_device is a thin lazy-import delegate"
  - "ModMode default for add_m4l_device is NONE (0), as kicksynth-m4l used; add_m4l_gen_synth keeps ABSOLUTE (4); Live check item 5 decides"
  - "midi_effect skeleton is midiin -> midiout pass-through (Live 12 MIDI Effect template), no plugin~"
  - "Init chain: live.thisdevice:0 bangs only dials without param_connect -- direct cord for one, t b ... for two or more; gen~-bound dials get none"
  - "8 Q40 critic rules are all non-blocking (warning, shortname_length a note) because the feature is EXPERIMENTAL"
  - "Presentation grid [8 + 52*col, 8 + 56*row, 44, 48], ncols = min(n, 8) up to 24 params else ceil(n/3); devicewidth 8 + 52*ncols; openrect [0,0,0,169]; latency 0"
  - "add_m4l_gen_synth validates its specs before creating gen~, so a bad spec leaves the patcher untouched"
metrics:
  duration: ~16 min wall clock (incl. two full-suite runs)
  completed: 2026-10-22
estimate:
  tokens: 255000
actuals:
  tokens: 29341
  tasks: 3
  commits: 5
plan_head_before: ec987817af85f4e385f71b4b4e8ab27d8fee4774
plan_head_after: c0396f5f3abfc47d61932c21440d5697d277af8f
---

# Quick 261022-pqu (Q40): M4L device builder and .amxd export Summary

**`Patcher.add_m4l_device(kind, params)` builds an instrument, audio effect or MIDI effect with Live-template wiring, inferred parameter metadata, unique short names, a live.thisdevice init chain and Push banks, and `export_amxd` writes a byte-correct .amxd. The .amxd codec is verified against kicksynth, fourin_fourout and Live 12's own templates.**

> **EXPERIMENTAL: not yet confirmed in Live.** Everything Q40 adds is unverified in Live until the user runs the combined Q15 + Q40 check below. That covers add_m4l_device, export_amxd, the init chain, inferred units, short names, banks and the 8 critic rules. The module docstring, the add_m4l_device and export_amxd docstrings, the critic docstring and the CLAUDE.md M4L section all say so.

## What was built

- **.amxd codec** in `src/maxpat/m4l_device.py`:
  - `parse_amxd` reads the file chunk by chunk (`[tag][uint32 LE len][payload]`) and bounds-checks every length. It refuses `ciph`, `mx@c` (frozen), truncated input, trailing bytes, a file that does not start with `ampf`, a missing `ptch`, and the `natt`/`nagg` kinds.
  - `build_amxd` rebuilds each of these byte for byte: the vendored kicksynth-m4l.amxd (103996 B), Max.app fourin_fourout.amxd and the three Live 12 templates.
  - `decode_payload` strips exactly one NUL and decodes strict UTF-8 with `json.loads`; nothing is ever evaluated.
- **`export_amxd(patcher_or_path, out_path=None, kind=None)`:**
  - Writes `ampf` (kind) + `meta` (0) + `ptch` (`dumps_max` + `\n\0`). The first 28 bytes equal Live's template of the same kind.
  - `kind=None` uses `detect_m4l_device_type`.
  - It raises, writing nothing, on a suffix other than `.amxd`, a `project.amxdtype` mismatch, or a kind it cannot detect.
  - It writes atomically. Under `patches/<project>/` it auto-commits only the .amxd (temp-repo test). The .maxpat is never touched.
- **m4l_constants.py:** the AMXD comment is rewritten as a chunk stream. `AMXD_VERSION` and `AMXD_META_VERSION` are documented as chunk lengths, and the header format as write-only. Added `AMXD_CHUNK_HEADER = "<4sI"` and `AMXD_PAYLOAD_TERMINATOR = b"\n\x00"`. All old names and values are kept.
- **Parameter resolution:**
  - Type and unit are inferred from whole name tokens and the range, never substrings: "harmonics" is not Time, and a 0-1 "gain" stays Float.
  - Int type only when every value is an int and the span is ≤ 255; a wider int span gets Float type with Int unit.
  - Explicit `type`/`unit`/`steps`/`short_name`/`varname`/`param_connect`/`modmode` always win.
  - Auto short names are at most 8 characters and de-duplicated ("Amount", "Amount2").
  - Validation covers duplicates, unknown or missing keys, bool bounds, ranges, steps, Enum/Blob and Custom.
- **Device skeleton** (`build_m4l_device` / `add_m4l_device`):
  - Per-kind wiring copied from the Live templates, with bare plugin~/plugout~.
  - A mono `audio_source` feeds plugout~ 0 and 1; a stereo pair feeds L→0 and R→1. `midi_source` feeds midiout.
  - live.dial params use the legacy extra_attrs/valueof key order.
  - live.thisdevice init chain, Push `parameterbanks` via the shared `plan_push_banks`, one newobj live.banks, and a 169 px presentation grid with device props.
- **add_m4l_gen_synth** now calls `self.add_m4l_device("instrument", ..., audio_source=(gen_obj, 0), midi_in=False, init_chain=False, banks=False, presentation=False)` with fully explicit specs. The golden test (4 cases, key-order-sensitive), test_m4l_gen_synth.py and TestM4LBuilderClean pass unedited.
- **Critic** (`m4l_critic.py`), 8 non-blocking rules:
  - per scope, with nested `[p synth]` parity: `stereo_out`, `midi_passthrough` (midi_effect only), `shortname_length` (note), `int_param_range`, `param_range`;
  - device level: `shortname_unique`, `bank_refs`, `device_height`.
  - None fires on add_m4l_device output, and every rule skips malformed values without raising.
- **CLAUDE.md** M4L section: the "Codified" blockquote now documents add_m4l_device and export_amxd as EXPERIMENTAL (618 B; CLAUDE.md is 28536 B, under the 30000 B limit). `tests/test_doc_signatures.py` indexes `src.maxpat.m4l_device`, and the 3 new call forms bind.

## Commits

| # | Hash | Message |
|---|------|---------|
| 1 | 4fb424e4 | test(m4l): golden of add_m4l_gen_synth before the Q40 refactor (no src/ path) |
| 2 | 4c19488d | feat(m4l): add_m4l_device skeleton for three kinds and .amxd codec/export verified against real devices |
| 3 | beb0c488 | feat(m4l): live.thisdevice init chain, shared Push bank planner, add_m4l_gen_synth built on add_m4l_device |
| 4 | 7291277e | chore(quick-261022-pqu): combined Q15 + Q40 Live check device (.maxpat + .amxd) |
| 5 | c0396f5f | feat(critics): M4L device checks ...; CLAUDE.md M4L builder + export |

The golden commit (4fb424e4) precedes the commit that adds m4l_device.py (4c19488d), and `git diff base..golden -- src` is empty (verified).

## TDD red counts

| Task | Red before fix | Green after |
|------|----------------|-------------|
| 1 (golden) | characterization: green on the old code by design (9 tests) | 9 |
| 1 (device) | collection error: all 99 Task-1 cases red (module missing) | 99 |
| 2 | 15 of 120 red | 120 |
| 3 | 14 of 145 red | 145 |

## Regression gate

- Baseline (Step 0, HEAD ec987817): rc 0, **6127 passed, 5 xfailed, 1 xpassed**.
- Final (HEAD c0396f5f): rc 0, **6281 passed, 5 xfailed, 1 xpassed**.
- `junit_diff.py`: `base=6133 new=6287 added=154 offenders=0`. The 154 new ids are all `tests.test_m4l_device` (145) or `tests.test_m4l_gen_synth_golden` (9). No test was removed or regressed.
- `git status --porcelain patches patterns` and `git stash list` match their Step 0 snapshots (both empty). No commit touches patches/ or patterns/, and every commit staged explicit paths.
- No existing test was edited. The one permitted edit, adding `src.maxpat.m4l_device` to `_INDEX_MODULES`, was made.

## Deviations from Plan

### Auto-fixed Issues

**1. [CLAUDE.md gen~ rule] Live check GenExpr de-hoisted**
- **Found during:** Task 3 Part D.
- **Issue:** the plan's literal `out1 = cycle(freq * pow(2, octave)) * amp * gain;` is a Param-only expression. CLAUDE.md says hoisted Param-only temps can be emitted out of order and must be de-hoisted.
- **Fix:** `History one(1);` then `k_freq = freq * one;`, `k_oct = octave * one;`, `k_amp = amp * one;` and `k_gain = gain * one;`, with `out1 = cycle(k_freq * pow(2, k_oct)) * k_amp * k_gain;`. The Params, defaults and behavior are as planned.
- **Files:** q40-live-check.maxpat. **Commit:** 7291277e.

**2. [Rule 2 - Correctness] add_m4l_gen_synth validates before creating gen~**
- **Found during:** Task 2 Part D.
- **Issue:** the plan builds the specs after `add_gen`, so a spec that add_m4l_device rejects would leave a half-built patcher (a gen~ with no plugout~).
- **Fix:** the specs are built first and checked with the pure `resolve_param_specs` before `add_gen`. Output is unchanged (golden green), and the test asserts the patcher stays empty on a ValueError.
- **Files:** src/maxpat/builders.py. **Commit:** beb0c488.

### Intended behavior change (recorded per plan)

- `add_m4l_gen_synth` now raises `ValueError` for duplicate names, `min >= max` or non-numeric bounds, through add_m4l_device's spec validation. Such inputs used to produce a device the critic blocks (duplicate longname) or a nonsensical range.

### Notes

- Live check build warnings: the two "outside patches/<project>/ -- not auto-committed" UserWarnings (save + export) were expected. Both files were committed with explicit paths.
- History: the earlier `m4l_export.write_amxd` (b9710c35, deleted in cb889d9b) was not resurrected. It wrote tab-indented JSON with no `\n\0`.

## Doc follow-ups (not edited; plan rule 8)

1. `.claude/skills/max-router/references/dispatch-rules.md:115, :120, :124`: "there is no .amxd writer" is now false.
2. `.claude/skills/references/shared-capabilities.md` "Builder API" (:175-226): add add_m4l_device and export_amxd.
3. The builder lists in `max-patch-agent/SKILL.md:81` and `max-ui-agent/SKILL.md:87`.
4. The max-critic skill's M4L check list: add the 8 Q40 rules.
5. TECHNICAL.md's M4L section.

## Assumptions carried (RESEARCH A1-A5)

| # | Assumption | Risk if wrong |
|---|-----------|---------------|
| A1 | Live accepts `parameterbanks` without per-box `parameters` entries or `buttons` | Banks missing on Push (cosmetic). Live check item 4. |
| A2 | A banged live.dial re-outputs its restored value in Live | The init chain is a no-op and the DSP misses initial values. Live check item 8. |
| A3 | Live keys the device kind on the header code; a missing `project.amxdtype` is harmless | Wrong device slot (low risk: kicksynth had no `project`). Live check item 1. |
| A4 | 8 characters is the right short-name cap | Over-truncation (cosmetic). |
| A5 | meta = 0 is right for an unfrozen device | Load failure (low risk: all 44 Live/Max templates use 0). |

## Live check (Q15 + Q40), one session

Device: `/Users/taylorbrook/Dev/MAX/.planning/quick/261022-pqu-implement-q40-in-planning-reviews-2026-1/q40-live-check.amxd`. Its source is `q40-live-check.maxpat`, and the build record is `live-check-save.txt` in the same folder (not committed).

Build record:
- 21727 B; header `616d7066 04000000 69696969 6d657461 04000000 00000000 70746368 bf540000` (iiii, meta 0).
- devicewidth 372, openrect [0,0,0,169].
- Banks:
  - "Filter": freq, Filter Envelope Amount;
  - "Amp": amp, Out Gain;
  - "Pitch": Octave, Pitch Envelope Amount;
  - "Envelope": Attack.

  freq lands in Filter because the existing `_classify_parameter` lists "freq" under Filter.
- Dials:

  | Dial | Type / unit | ModMode | Initial | Binding |
  |------|-------------|---------|---------|---------|
  | freq | Float / Hertz | Absolute | 220 | bound `synth::freq` |
  | amp | Float / Float | None | 0.5 | bound `synth::amp` |
  | Out Gain | Float / deciBel | None | -12 | unbound |
  | Octave | Int / Int | None | 0 | unbound |
  | Attack | Float / Time | None | 10 | unbound |
  | Filter Envelope Amount (short "Amount") | Float / Float | None | 0 | unbound |
  | Pitch Envelope Amount (short "Amount2") | Float / Float | None | 0 | unbound |

- Init chain: live.thisdevice:0 → `t b b b b b`, whose outlets 0-4 go to Out Gain, Octave, Attack and the two Envelope Amount dials.
- Out Gain → `dbtoa` → `prepend gain` → gen~. Octave → `prepend octave` → gen~. gen~'s `gain` Param defaults to 0, so **the device is silent unless the init chain delivers Out Gain**.

Lower the track volume first, then drag `q40-live-check.amxd` onto an empty MIDI track.

1. (Q40) It loads as an Instrument in the instrument slot.
2. (Q15) freq and amp move smoothly (continuous, not 0/1 steps).
3. (Q15) Audio shows on both L and R of the track meter.
4. (Q15) The Parameter Banks window (double-click live.banks) or Push shows the four banks above.
5. (Q15) ModMode: freq is Absolute, the others None. In a clip envelope, decide which default you want for new devices (add_m4l_device default None vs add_m4l_gen_synth Absolute).
6. (Q40) freq shows Hz, Attack shows ms, Out Gain shows dB, and Octave shows integers -2..2 in steps.
7. (Q40) The two Envelope Amount dials show distinct short names ("Amount", "Amount2").
8. (Q40) The tone (220 Hz sine) is audible right after loading without touching Out Gain. Move Out Gain and Octave, save a Live preset, reload it: the level and octave match the stored values. Silence means the init chain does not fire.
9. (Q40) Nothing is clipped at the bottom (169 px).

Confirming 2-5 also closes Q15's human_verification (261014-d13).

## Known Stubs

None. The Attack and Envelope Amount dials in the check device are deliberately unwired: they exist to test units, short names and the init chain.

## Self-Check: PASSED

- FOUND: src/maxpat/m4l_device.py, tests/test_m4l_device.py, tests/test_m4l_gen_synth_golden.py, tests/fixtures/expected/m4l_gen_synth_golden.json, tests/fixtures/kicksynth-m4l.amxd, q40-live-check.maxpat, q40-live-check.amxd
- FOUND commits: 4fb424e4, 4c19488d, beb0c488, 7291277e, c0396f5f
