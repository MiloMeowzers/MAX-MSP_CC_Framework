# chopchop-project

Pick up the existing ChopChop Max for Live device and complete its implementation. The device
works today but a large amount of core functionality is unbuilt, and there is refinement work
on top of that.

## Kickoff (2026-09-03)

### What this is

A mature Max for Live device pair, developed outside this repo:

- **Instance / working base:** `F:\CC Working\MAX Framework\Chop Chop\Dev Base\ChopChop_v6_174_BASE.amxd`
- **Brain:** `F:\CC Working\MAX Framework\Chop Chop\Dev Base\ChopChop_Brain_.amxd` (largely untouched)
- A 16-slice loop chopper built on **`karma~`** (third-party looper/sampler external, not
  Cycling '74). Pad grid (4x4, pad 1 bottom-left, pad 16 top-right), waveform display with
  playhead + region overlays, loop-length scaling by windowing, Reloop mode, reverse /
  ping-pong / punch, overdub / freeze / solo-mute, record quantise.

### Reference documentation (authoritative, in `Chop Chop\Reference Sources\`)

- `18_ChopChop_v6_174_Architecture_and_Audit.md` — what the device is (supersedes 02, 12, 13)
- `19_ChopChop_Roadmap_and_Notes.md` — roadmap (Part A), architecture rules (B), process
  rules (C), delivery checklist (D), design/palette (E)
- `09_Architectural_Pivot_MIDI_Storage.md` — sequencing -> Ableton MIDI/clip engine; storage
  = master file + 16 clips via shared markers; karma~ retained as manipulation engine
- `chopchop-size-window-architecture.SKILL.md` — size / window / INIT / buffer-guard
- `ChopChop_Timing_and_Size_Lookup.md` — timing / size / window / slice lookup tables
- `02_ChopChop_Project_Knowledge_Reference.md` — older knowledge reference (v2)
- karma~ skill files: `karma-coordinate-conventions`, `karma-loop-semantics`,
  `max-msp-karma-technical`
- Rule (C1): **the project reference docs outrank the skill files** where they disagree.

### Roadmap (from doc 19, Part A) — ordered, reordering allowed but not silently

- **A1. Multi-voice audio path** — largest gap, smallest new work (most is built, §6 of audit).
  Connect `karmaB` / `karmaKeys` outputs into the mix; land `---abMix`; add
  `---enableA/B/Keys` senders; resize `---bufB` / `---bufFreeze` from 20,000 ms (buffer decls
  order-sensitive -> own file); decide `karmaKeys` source; attach `p RollingB`. Deliver as
  separate sequential files; step 1 alone is testable (B becomes audible).
- **A2. Sequencer usability** — blocked on characterisation. `---SequenceStatus` sent, never
  received (no empty/armed/recording/playing feedback). Three unconnected objects in
  `p Sequence_Recorder`. Storing sequence as MIDI events is a prerequisite for A4.
- **A3. Region overlay under reverse** — window always drawn ahead of playhead; under reverse
  the loop is behind. Fix: `gate 2` on `---effectiveReverse` selecting `i-s` or `s-i` into
  the modulo. Two objects.
- **A4. Ableton clip & MIDI integration** — core requirement. Pad hits as real MIDI notes on
  a standard Ableton track; audio as clips via `ClipSlot.create_audio_clip` with shared
  markers, 16 clips from one master file. Depends on A2 (MIDI-event storage).
- **A5. Speed & stutter** — entirely unwired, largest gap in the visible UI. `p SpeedControl`
  / `p GlitchControl` expect relative encoder deltas, not absolute dial values (dials
  deliberately disconnected). Adapt subpatchers to absolute input, or bind dials to an
  encoder source. `---ToggleValue` / `---toggleValue` (two channels, case difference) neither
  driven — stutter engine cannot engage.
- **A6. Momentary reverse & Reloop as a momentary layer** — structure correct; both need a
  momentary MIDI source. Settled design: Reloop as momentary layer over Scaled.
  `record_arm_toggle` returns to its reserved purpose (preroll) if still standing in.
- **A7. Upward scaling, bounce, freeze** — not a small fix. `window` cannot exceed 1; follows
  from the bounce + multi-voice work (after A1).
- **A8. Two display items** — slice rescaling on resize (below captured length, 16 pads loop
  over a subset rather than spanning the shorter loop; fix = `jump = n/16 x window` on the
  jump path in `p glitching`); remove probes `K_1`-`K_7` from presentation strip at x 1130
  before shipping.

### Other open items (doc 02)

Preroll / instant-play buffer (investigated, not built), progressive tape-style
erase-ahead-of-record-head (replacing the deliberate buffer-clear-on-record placeholder),
LED indicators on pad buttons, `p MessagesToKarma` internals never traced, sequenced
ping-pong still timer-based, quantize-grid behaviour under rapid/simultaneous hits untested.
Declick: raise karma~ `ramp` / `snramp` from 16 (~0.36 ms) toward 441 (~10 ms) — one-message
change, never applied.

### Hard constraints from the delivery checklist (doc 19, Part D)

- File size must stay exactly **1,705,180** bytes.
- Per-scope patchline-only message-cycle sweep must read **27**, not zero. Above 27 = new,
  must be accounted for.
- **One variable per file**, or deliver as separate sequential files.
- Never feed a value derived from karma~'s report back into playback (B1 — stack-overflowed
  v6_170). Cycle sweep > 27 => stop.
- Never defer `---size` (B2 — desyncs the playhead overlay).
- Prefer values the device already owns over values read back (B3).
- Additive display layers: own panels, own trigger, assert no cord touches the existing chain
  (B4). Z-order is one insertion point (B5).
- Revert after two bad builds; do not attempt a third (C2).

### Kickoff decisions (2026-09-03)

1. **Scope.** Primary target is **A1 (multi-voice audio path)**, but not in isolation:
   - **Working preroll / instant-start** is in scope alongside A1 (the "instant-play preroll
     buffer" item from doc 02 — continuously-running capture while armed so the buffer is
     already full the instant Record is pressed).
   - **A2 as the user actually means it** = overall **quantisation** and **faithful record /
     playback of pad hits** (timing, lag), not just the sequencer-status plumbing. The user
     considers A1, preroll and A2 **codependent and hard to separate**.
   - The user has explicitly asked for an **overall architecture + implementation strategy**
     covering these three together before piecemeal builds begin. That is the main job of
     `/max-discuss` + `/max-research` here.
2. **Workflow.** Hand-edit the `.amxd` JSON via the proven ChopChop extract / validate /
   re-inject route (the `anthropic-skills:chopchop-*` skills), honouring doc 19 Part D:
   file size exactly **1,705,180**, per-scope patchline-only cycle sweep **27**, **one
   variable per file / sequential files**. The user reports this route has been highly
   reliable. The `src.maxpat` Patcher API is **not** used for this project.
3. **Working copy.** Edit the device **in place** at
   `F:\CC Working\MAX Framework\Chop Chop\Dev Base\` (versioned there as v6_175, v6_176, ...),
   **and** keep a stable working copy tracked in this repo. Copied in on kickoff:
   - `patches/chopchop-project/generated/ChopChop_v6_174_BASE.amxd` (byte-identical to Dev
     Base, sha256 `19e3ed9a…`, 1,705,180 bytes — the stable base for this project)
   - `patches/chopchop-project/generated/ChopChop_Brain.amxd` (sha256 `4e39533a…`)
   - `patches/chopchop-project/reference/*.md` — full copy of the authoritative reference set
   - The auto-created empty `generated/chopchop-project.maxpat` is a scaffold artefact and
     unused; the real deliverable is the `.amxd`.
4. **Testing.** Direct on a duplicated `.amxd` in Max 9 / Live 12 (per doc 02 and the
   `anthropic-skills:chopchop-max-testing` skill). No from-scratch test harness — test against
   a copy of the real device.

### Still to resolve in /max-discuss

- The unified architecture for A1 + preroll + quantise/faithful-record, including the ordering
  of codependent pieces and what ships as which sequential file.
- Whether preroll's continuous-capture design can coexist with karma~'s "record until buffer
  full then auto-play" native behaviour, or needs the bootstrap-append approach / a second
  buffer (`---dummy` history to be investigated).
- Where quantisation lives (the `TriggerPoisition` quantize-grid subsystem: `phasor~` locked
  to `16n`/`32n`/`64n`, `p detect_edge`, `switch`, `onebang`) and how much of the reported
  lag is that vs. the commit-on-slice-edge latency vs. karma~ ramp/snramp (currently 16).

### Stage

ideation -> discussion
