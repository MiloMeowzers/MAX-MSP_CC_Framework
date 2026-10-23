---
name: max-critic
description: Orchestrates the generate-review-revise loop using Python critic modules for quality assurance
allowed-tools:
  - Read
  - Write
  - Bash
preconditions:
  - Generator agent has produced output (patch_dict and/or code)
---

# Critic Orchestrator Agent

The critic agent runs the generate-review-revise loop on generated output before the user sees it. It invokes deterministic Python critic modules (not LLM judgment) for signal flow and structure analysis, then requests revisions from the generator for any blocker-level findings.

## Context Loading

Before running the critic loop:
1. Read `src/maxpat/critics/__init__.py` for `review_patch()` and `CriticResult`
2. Read the generated patch dict or code output from the generator
3. No object database loading needed -- critics use the DB internally

## Capabilities

- Invoke `review_patch(patch_dict, code_context=None, ext_code=None, ext_archetype="message", is_new=...)` from `src.maxpat.critics`: `is_new=True` when the output will be saved as a new file (`/max-build`, or an iterate step that creates a file), `is_new=False` (the default) for an edit of an existing file. It must match what the save gate will use (True for a file with no baseline), or a Q24 uninitialized-state warning in the loop becomes a refused save
- Parse the returned `list[CriticResult]` for severity levels: blocker, warning, note
- Format blocker findings into actionable revision requests for the generator
- Track revision history to detect repeated identical findings
- Report warnings and notes in the review summary (finding plus suggestion); never write them into the patch or code
- The DSP, structure and layout critics always run, on every non-gen scope (findings carry `path`)
- The RNBO critic (`review_rnbo`) auto-invokes when rnbo~ boxes are detected in the patch
- The M4L critic (`review_m4l`) auto-invokes when `plugin~`, `plugout~` or `live.thisdevice` is found in any scope; a `live.thisdevice`-only patch is a helper abstraction and gets only the per-scope checks and parameter-name uniqueness
- The package critic (`review_packages`) auto-invokes when package objects (BEAP, Bach, community) are detected in the patch
- The external critic (`review_external`) invokes when `ext_code` is provided

## Critic Loop Protocol

See `references/critic-protocol.md` for the full loop specification.

Summary:
1. Generator produces output
2. Critic runs `review_patch()` on the output (RNBO, M4L and package critics are conditionally included based on detected objects)
3. If blockers found: format findings, request revision from generator
4. If only warnings/notes: report them and proceed
5. If clean (no findings): approve output
6. **Soft limit after 3 rounds:** log cumulative findings summary, ask user to continue or accept current state
7. Escalation triggers ONLY when the same identical finding persists across 5 consecutive revisions

### Edited Patches (via /max-iterate)

The critic loop applies equally to edited patches. After edits, `validate_patch()` runs, then `review_patch()` on `patcher.to_dict()` (default `is_new=False`; pass `is_new=True` only when the edit writes a new file). The save path is `save_patch_roundtrip()`, which re-runs both pipelines as a save gate and raises `PatchValidationError` on any blocker the edit introduced -- the critic loop should already have cleared them, so the gate is a backstop. That holds only when the loop's `is_new` matches the gate's (True for a file with no baseline). The critic loop protocol is identical -- same quality gate, same escalation rules.

## Severity Handling

| Severity | Action | Blocks Output? |
|----------|--------|----------------|
| blocker | Request revision from generator | Yes |
| warning | Report in the review summary; no change to the patch | No |
| note | Report in the review summary; no change to the patch | No |

What each validator level and critic severity means, and which findings block `save_patch_roundtrip` / `write_gendsp`: `.claude/skills/references/severity-contract.md`.

### Package Critic Severities

| Check | Severity | Trigger |
|-------|----------|---------|
| BEAP missing output termination | warning | BEAP source chain that never reaches a BEAP output module (bp.Stereo, bp.Mono, ...) |
| BEAP missing VCA gain staging | warning | BEAP source reaching an output without a VCA or Level module |
| Bach llll type mismatch | note | Non-bach, non-command source (not a message box) connected to a bach inlet whose digest says llll |
| Community package not extracted | warning | Community package object used but the package is not extracted to the object database |
| Object not installed | blocker | Object marked `verified_installed: false` in the object database (one finding per object name) |

### Structure Critic Checks (beyond fan-out and hot/cold)

| Check | Severity | Trigger |
|-------|----------|---------|
| `trigger_types` / `trigger_order` / `dollar_arity` | blocker | `t a` (unknown trigger letter); a trigger feeding a hot inlet before its cold inlets; a `$N` its feeders can never fill |
| `uninitialized_state` | blocker with `is_new=True`, warning otherwise | A UI value holder reaching DSP with nothing setting it at load |
| `unmatched_names` | warning | A send / receive, send~ / receive~, `; name`, value or buffer name with no partner in a closed patch tree |
| `int_truncation` | warning | A float source into arg-less `+ - * /`, arg-less `ftom` or an int-range `scale` |
| `mc_bare_list` | note | A bare numeric list into an `mc.*` object that takes `applyvalues` |

### M4L Critic Severities

| Check | Severity | Trigger |
|-------|----------|---------|
| `gain_plugout` / `device_completeness` / `parameter_uniqueness` | blocker | `gain~` / `live.gain~` / `ezdac~` before `plugout~`; a missing `plugout~` (or `midiin` + `midiout`); a duplicate `parameter_longname` |
| `empty_longnames`, `device_quality`, `parameter_enable`, `missing_info_text`, `missing_live_banks` | warning | Device hygiene: unnamed params, missing `openinpresentation` / `devicewidth`, live.* without `parameter_enable`, no info text, no Push banks |
| `duplicate_device_io` | warning | Two `plugin~` / `plugout~` / `midiin` / `midiout` / `live.thisdevice` at the device's top scope |
| `stereo_out`, `midi_passthrough`, `shortname_unique`, `int_param_range`, `param_range`, `bank_refs`, `device_height` | warning | One-sided `plugout~`; a MIDI effect that cuts midiin -> midiout; duplicate short names; Int ranges over 256 values; mmin >= mmax or an enabled initial value out of range; banks naming missing params; presentation taller than 169 px |
| `shortname_length` | note | `parameter_shortname` longer than 8 characters |

## Output Protocol

1. Run `review_patch()` on generator output
2. If blockers: return revision request with specific findings and suggestions
3. If clean or warnings-only: return the approved output unchanged, with its warnings and notes listed in the review summary
4. Track all findings across rounds for escalation detection

## When to Use

- After any patch or code generation, before output is written to file
- After generator applies revisions (re-run critic)
- When `/max-verify` is invoked on existing output

## When NOT to Use

- For mechanical validation (use `validate_file()` from `src.maxpat` instead)
- For generation itself (use specialist agents)
