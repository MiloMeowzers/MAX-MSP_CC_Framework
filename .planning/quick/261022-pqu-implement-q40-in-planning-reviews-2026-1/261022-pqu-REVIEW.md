---
phase: 261022-pqu
reviewed: 2026-10-22T00:00:00Z
depth: quick
files_reviewed: 9
files_reviewed_list:
  - CLAUDE.md
  - src/maxpat/builders.py
  - src/maxpat/critics/m4l_critic.py
  - src/maxpat/m4l_constants.py
  - src/maxpat/m4l_device.py
  - src/maxpat/m4l_polish.py
  - tests/test_doc_signatures.py
  - tests/test_m4l_device.py
  - tests/test_m4l_gen_synth_golden.py
findings:
  critical: 0
  warning: 4
  info: 4
  total: 8
status: issues_found
---

# Phase 261022-pqu: Code Review Report

**Reviewed:** 2026-10-22
**Depth:** quick (pattern scan of the full diff `4fb424e4^..c0396f5f`, plus targeted reads of the new codec, the builder and the Q40 critic checks; two findings were confirmed by running the builder)
**Files Reviewed:** 9
**Status:** issues_found

## Summary

The pattern scan of the added lines found nothing: no secrets, no eval/exec/shell, no debug prints, no bare or empty `except`. The `.amxd` codec (`parse_amxd`, `build_amxd`, `decode_payload`) checks every chunk length against the bytes that remain, refuses `ciph`/`mx@c` frozen payloads and never evaluates the payload, so the untrusted-binary surface looks sound.

The problems are in `build_m4l_device`. It does not account for the patcher it builds into: it reuses varnames, clobbers the presentation and device geometry, and leaves existing parameters out of the Push banks. With `midi_source`, its own output also trips the new `midi_passthrough` critic. Nothing is a blocker, because every path is EXPERIMENTAL and non-blocking until the Live check passes.

## Narrative Findings (AI reviewer)

## Warnings

### WR-01: `midi_effect` + `midi_source` leaves a dangling `midiin` that the new critic flags

**File:** `src/maxpat/m4l_device.py:721-732`
**Issue:** For a `midi_effect`, `midiin` is always created (line 721). When `midi_source` is given, only `source -> midiout` is wired (line 732). `_normalize_source` requires the source box to exist before the build, so the caller's chain cannot start from `dev.midiin`, and the `midiin` box has no outgoing cord. The builder's own output fails its own check, as confirmed by running it: `p.add_m4l_device("midi_effect", midi_source=(makenote, 0))` followed by `review_m4l(d, "midi_effect")` gives `midi_passthrough: midiin (obj-2) has no outgoing cord`. A caller who builds their own `midiin` for the source chain ends up with two `midiin` boxes. `audio_effect` + `audio_source` has the same shape with an unwired `plugin~` (no critic covers that one).
**Fix:** Pick one of these:
- Skip creating `midiin` (and `plugin~`) when a source is given.
- Document that the caller must wire `dev.midiin` / `dev.plugin` into their chain afterwards, and add a test that runs `review_m4l` on the `midi_source` output.
- Accept a callable or a deferred source so the chain can be built from `dev.midiin`.

```python
elif kind == "midi_effect" and midi is None or (kind == "instrument" and midi_in):
    dev.midiin = patcher.add_box("midiin", x=200.0, y=340.0)
```

### WR-02: Dial varnames are not checked against existing boxes in the patcher

**File:** `src/maxpat/m4l_device.py:500-505, 753`; `src/maxpat/builders.py:1224`
**Issue:** `resolve_param_specs` only rejects duplicate varnames within the new specs. It never checks varnames that are already in `patcher.boxes`. Confirmed by running it: with a gen~ carrying `varname "synth"`, the spec `{"name": "synth", ..., "param_connect": "synth::synth"}` produces two boxes with `varname "synth"`. `add_m4l_gen_synth` has the same hazard by construction (`"varname": name` with `gen_varname="synth"` as the default). `param_connect` resolves the gen~ by varname, so a duplicate scripting name makes the binding ambiguous, or Max may rename one of the boxes on load.
**Fix:** In `build_m4l_device`, collect `{b.extra_attrs.get("varname") for b in patcher.boxes}` before creating any box. Raise `ValueError` if any `spec["varname"]` is in that set, or auto-suffix derived (non-explicit) varnames. Do this check before line 715 so that "nothing is created" on error still holds.

### WR-03: `presentation=True` overwrites existing device geometry and overlaps existing presentation boxes

**File:** `src/maxpat/m4l_device.py:810-824`
**Issue:** The dial grid always starts at `(8, 8)`, and `devicewidth`, `openrect`, `openinpresentation` and `latency` are always overwritten. If the patcher already holds presentation UI (for example, adding a device skeleton to a partly built device), the new dials land on top of existing controls and `devicewidth` can shrink below the existing content. This breaks the "never modify working functionality" contract, and the overlap is not reported.
**Fix:** If any existing box has `presentation: 1`, either raise or warn and skip the grid (as the banks branch does). Otherwise, offset the grid to the right of the existing presentation extent, and set `devicewidth = max(existing, computed)` instead of overwriting it.

### WR-04: Planned Push banks contain only the new specs, dropping parameters already in the patcher

**File:** `src/maxpat/m4l_device.py:795`
**Issue:** `plan_push_banks([s["name"] for s in specs])` plans banks from the dials this call creates. Any `live.*` parameters already in the patcher are left out whenever the existing banks are absent or all-placeholder. Once written, the banks are no longer placeholders, so `m4l_polish.organize_push_banks` (`_banks_replaceable`) will not fix them later. Pre-existing parameters stay invisible on Push.
**Fix:** Plan from every parameter longname in the patcher, not just the new specs. Reuse `m4l_polish._collect_live_controls` (or the critic's `_collect_parameter_longnames`) plus the new specs, in box order:

```python
existing = [lv for lv in _existing_longnames(patcher) if lv not in new_names]
parameters["parameterbanks"] = plan_push_banks(existing + new_names)
```

## Info

### IN-01: `export_amxd` never checks an explicit `kind` against the patch contents

**File:** `src/maxpat/m4l_device.py:313-332`
**Issue:** When `kind` is given, the only cross-check is `project.amxdtype`, and only if a `project` block exists. Exporting a patch that contains `plugin~` with `kind="instrument"` (or a `plugout~` device as `"midi_effect"`) writes a mismatched `ampf` code without a warning.
**Fix:** When `kind` is explicit, also run `detect_m4l_device_type(patch)`. If the detected kind is non-None and differs from `kind`, raise or warn.

### IN-02: Explicit `type`/`short_name` are not checked for consistency

**File:** `src/maxpat/m4l_device.py:444, 551-554`
**Issue:** An explicit `type: "int"` with float bounds or a span over 255 is accepted. Explicit short names are never checked for length or for duplicates against each other (`taken` treats them as authoritative). All of these are only reported after the fact by the `int_param_range`, `shortname_length` and `shortname_unique` critics.
**Fix:** In `resolve_param_specs`, raise or warn when two explicit short names are equal, and when an explicit INT type has non-int bounds or a span over `_INT_TYPE_MAX_SPAN`.

### IN-03: `param_range` ignores `parameter_initial_enable`

**File:** `src/maxpat/critics/m4l_critic.py:693-696`
**Issue:** An out-of-range `parameter_initial` is flagged even when `parameter_initial_enable` is 0, where Live never applies the initial value. This is a false-positive warning.
**Fix:** Skip the initial-value test unless `valueof.get("parameter_initial_enable")` is truthy.

### IN-04: The delegation test asserts on source text

**File:** `tests/test_m4l_device.py:874-879`
**Issue:** `inspect.getsource(Patcher.add_m4l_gen_synth)` with substring asserts breaks on harmless refactors, such as reformatting the f-string or calling through a helper. It also says nothing about behaviour that the golden test does not already cover. Separately, `build_amxd` passes `meta` straight to `struct.pack("<I", ...)`, so a negative or 2^32+ value raises `struct.error` instead of the `ValueError` its docstring family uses.
**Fix:** Replace the source-text test with a `unittest.mock.patch.object(Patcher, "add_m4l_device", wraps=...)` call assertion. Validate `0 <= meta < 2**32` in `build_amxd`.

---

_Reviewed: 2026-10-22_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: quick_
