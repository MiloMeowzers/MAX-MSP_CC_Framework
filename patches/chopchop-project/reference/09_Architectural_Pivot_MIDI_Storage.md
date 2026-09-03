# Architectural Pivot: MIDI Sequencing, Ableton Storage, Karma~ Retained

**Trimmed.** The test-harness section (former §4) and its follow-up are removed: the `play~`-based two-voice crossfade harness was abandoned, and the process lesson it produced now lives in Part C of `19_ChopChop_Roadmap_and_Notes.md`. `10_TestHarness_Postmortem_and_Correction.md` is superseded by this trim. What remains below are the three architectural decisions, which are still live and feed roadmap item A4 in document 19.

These decisions supersede the `seq~`-based sequencing/collision-detection work described in `07_Sequencer_Investigation_Consolidated_Findings.md` and the changelog. That file is still worth keeping as the record of what has already been tried against `seq~`, but its conclusions are not the direction of travel.

## 1. Sequencing moves entirely to Ableton's MIDI/clip engine

**Decision**: Pad hits become genuine MIDI notes. Live recording of pad performance uses a standard Ableton MIDI track, arming and capturing the same note stream the device already receives. Played-back MIDI (from a recorded clip) is routed back into the device's existing input, indistinguishable from a live hit.

**Why**: The entire `seq~`/collision-detection/boundary-pruning saga (v10 through v27 in this session's build history) existed because `seq~` had to *decide* what belonged in a stored sequence — collision detection, threshold dials, hysteresis, all of it. Ableton's clip engine needs no such decision: whatever got played back is exactly what gets replayed. This is the Dobrian `table`-replace principle (§2.2 in `08_...md`) taken to its logical conclusion — there is no ChopChop-owned event store to accumulate in, so there's nothing to prune.

**Consequence**: All `seq~`-based recording/collision/pruning work from this session is obsolete, not fixed. It was never the right layer to solve the problem in.

**Consequence for `karma~`'s addressing**: earlier project knowledge established that `p glitching` is the *mandatory* translation layer for any position command, since it's the only place that knows current real-time window/speed state (`01b_ChopChop_Device_Architecture_SKILL.md`). This still applies — a MIDI-triggered jump, live or replayed, must route through this same translation layer, not bypass it. This principle was reaffirmed, not superseded, by the MIDI pivot.

## 2. Storage architecture: master file + 16 clips via shared markers

**Decision**: At capture, `karma~`'s buffer writes to a file on disk (standard `write` message). `ClipSlot.create_audio_clip(path)` is called **16 times against that same single file**, in a scene created via `create_scene`. Each of the 16 clips gets its own `start_marker`/`end_marker` (both confirmed get/set in the LOM) carving out its 1/16th region, and `looping = false`. Clips are named with a shared capture-id plus pad number (e.g., `[capture-id]_Pad[note]`).

**Why this shape, not alternatives considered**:
- **Rejected: Simpler auto-slicing on one uploaded file.** Would need to load the captured file into Simpler at all — confirmed not programmatically possible (see gap in `08_...md`).
- **Rejected: LooperDevice → `export_to_clip_slot`.** Works, but requires a second device duplicating capture functionality karma~ already does — assessed as solving a plumbing problem by adding more plumbing. `karma~` already writes files directly; no intermediary needed.
- **Rejected: 16 separately-exported audio files** (via scratch-buffer `duplicate`+`crop`+`write`, confirmed viable via the official `buffer~` reference). Works, but the shared-file-plus-markers approach needs only one file write instead of sixteen buffer operations, and boundaries live as editable clip properties rather than being baked into separate files.

**Open/unconfirmed**: getting a clip's audio into a Simpler or Drum Rack pad for idiomatic drum-rack-style playback remains genuinely unconfirmed via LOM (see gap in `08_...md`). If Drum Rack pads are wanted for their choke-group behavior, one manual per-capture drag may be an unavoidable, permanent part of the workflow — this is a real platform constraint, not a bug to eventually fix.

## 3. Karma~ retained as the central manipulation engine — explicitly reconsidered, not assumed

Early in this session's redesign discussion, a "dry = simple trigger, wet = karma~" split using `groove~`/`play~` for the dry path was proposed. **This was explicitly rejected**: `groove~`/`play~` don't perform as well for this instrument's actual purpose — continuous, expressive, real-time manipulation is exactly what karma~ is built for and what made this project worth building over just using a stock sampler. Karma~ remains the sole playback/manipulation engine for production use.

**Smoothing/declick**: `ramp`/`snramp` are karma~'s own built-in, automatic raised-cosine crossfade length controls (confirmed in `01c_Max_MSP_Karma_Technical_SKILL.md`). Current configured value is `ramp 16`/`snramp 16` (~0.36ms) against a documented-reasonable `ramp 441` (~10ms) — a concrete, low-risk, already-identified fix for "truncation is rough," never yet applied.

A two-voice crossfade harness was once built to compare against karma~'s own declick empirically. It was abandoned without ever producing the comparison, and the reference patchers it rested on are no longer in project knowledge. **The open question it existed to answer is still open and still cheap**: raise `ramp`/`snramp` from 16 (~0.36 ms) toward 441 (~10 ms) on the live device and listen. That is a one-message change, not a harness.

## Status

None of the above is built. Roadmap item A4 in `19_ChopChop_Roadmap_and_Notes.md` carries it,
and it depends on the sequencer storing MIDI events rather than internal messages.

Two prerequisites are already in place and worth knowing before starting: `---padHitRaw`
carries the pad index 0–15 and is fed by the pads, the UI grid and the waveform click path
alike, so it is the single hook for "a slice was triggered", whatever the source. And
`Max9-LOM-en.pdf` / `Max9-JS-API-en.pdf` remain in project knowledge specifically for this
work.

