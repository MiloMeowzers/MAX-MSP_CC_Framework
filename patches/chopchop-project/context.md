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

## Decisions (discussion, 2026-09-03)

The framing shifted during discussion: the problem is not "wire up karmaB", it is that one
`karma~` currently does capture + continuous-loop playback + live slice triggering + sequenced
playback through a single playhead and a single `seq~` event queue. That model has no
polyphony, no collision policy, and a sequencer timebase (`phasor~ 0.3`, free-running ~3.3 s)
locked to nothing musical — hence saturation under dense play and sync drift.

### D1. Three separated layers, distinct audio paths

1. **Scrub layer** — `karma A` (with `karma B` alternating, see D5): the continuous
   transport-locked playthrough. A layer in its own right, manipulable *at all times*. All
   existing manipulation stays here: reverse, ping-pong, glitch, `window`, Reloop. Independent
   of whether pads are being struck.
2. **Live pad layer** — a `poly~` voice pool reading the **shared captured buffer**,
   MIDI-note driven. Adds **per-pad pitch and play-direction** (new capability). Replaces the
   idea of a 3rd `karma~` for the sequencer voice — `poly~` is polyphonic and voice-steals,
   so it does not saturate the way a 3rd monophonic playhead would.
3. **Sequencer** — records the **MIDI note stream** off layer 2 (velocity, note-off, grid
   quantise), replays through the same `poly~`. `seq~` is removed. Built MIDI-at-core so A4
   (Ableton MIDI track + 16-clip audio export) is a mirror step, not a rearchitecture.

### D2. `poly~` over 16-fixed voices

16-fixed was seriously considered (deterministic, trivial per-pad state, no allocator). What
it costs: **same-pad overlap** — a pad always chokes its own previous sound, so no overlapping
release tails, rolls/ratchets that stack, or two copies of a pitched slice ringing together.
Since per-pad pitch + direction is wanted, that overlap matters. Export is **not** a
differentiator — the 16 clips derive from the 16 slice *regions* of the master capture
regardless of the voice engine.
Decision: `poly~`, structured with **per-pad choke groups on by default** (behaves exactly
like 16-fixed for rhythm), lifted per-pad for pitched/atmospheric use. A `@voices 16` pool
with a home-voice per pad (for 16-fixed-like determinism + per-pad state) is the likely
shape — exact mechanism is a research item.

### D3. Collision policy — switchable

Per-pad choke (default; rhythm/drums) <-> poly (atmospheric/pitched layering). Implemented as
`poly~` choke groups. Note: mapping slices directly, a single pad array is mono anyway; the
poly aspect earns its keep once per-pad direction + pitch are enabled.

### D4. Pad mode control

Each pad press is routed by a mode switch: **affect scrub playhead / affect live voices /
affect both**. Reloop and similar are scrub-layer modes — the mode switch decides whether a
press *also* fires live voices.

### D5. Preroll / instant-start — `karma A`/`B` alternate roles

Two `karma~` instances; whichever is not the current tape is the transport-locked rolling
capture. On Record press the roles swap at a transport edge — audio already exists, so start
is instant. Handoff trigger comes from the **transport phasor** (a value the device owns),
never from `karma~`'s position report (rule B1 — that stack-overflowed v6_170).
**A/B-mix** = current-loop vs. previous-loop crossfade (`---abMix` finally gets a receiver).

### D6. Loop length unification (subsumes A7)

The rolling capture runs continuously at a generous **max length** — buffer sized like A
(~120,000 ms), not the 20,000 ms `---bufB` has now — transport-locked. The committed loop is
a **movable window into that rolling buffer**. So `---capturedMs` becomes the rolling-buffer
length, not the last committed size, and the window scales **up** as freely as **down**, into
audio that was actually rolling, with **no re-record**. Genuinely new material beyond the ring
still needs a fresh capture. Preroll, loop-lengthening and A/B "previous loop" are then one
mechanism.
Watch: this must not reintroduce the report-feedback loop (B1) or defer `---size` (B2). The
window still comes from device-owned quantities.

### D7. Quantise — selectable grid

Bar / beat / 16th / off. Applied to MIDI note-on input into the recorder *and* to loop-bound
snapping on capture. Reuse the `ButtonQuantize` index-lookup pattern (`live.menu` left/index
outlet -> `route` -> value messages; the float outlet gives normalised position, not the
value).

### D8. A4 — architecture-supporting now, full build later

Not implementing full Ableton clip/MIDI integration in this project, but every decision above
must keep it a straight-line continuation: sequencer is MIDI notes from the start; the 16
slice regions are the export unit; pad hits are already note events.

### D9. Unchanged constraints

JSON-edit workflow; doc 19 Part D delivery checklist — file size **1,705,180**, per-scope
patchline-only cycle sweep **27**, **one variable per file / sequential files**; test on a
duplicated `.amxd` in Max 9 / Live 12; revert after two bad builds (C2).

## Revised phase plan (each phase = one or more sequential single-variable files)

1. `karmaB` / `karmaKeys` outputs -> mix stage; `---abMix` receiver; `---enableA/B/Keys`
   senders. Plumbing, no behavioural change to A. Step 1 alone testable (B audible). [A1 1-3]
2. Resize `---bufB` / `---bufFreeze` to ~120,000 ms. Own file (buffer decls order-sensitive). [A1 4]
3. Transport-locked rolling capture on `karma B` — revive `p RollingB`
   (`phasor~ @frequency 1n @lock 1` -> `delta~`/`edge~` -> `onebang`). `---bRealign` sender
   (arm state), `---bAudible` receiver.
4. Window-into-rolling-buffer loop model — `---capturedMs` = rolling length; window scales up
   and down; loop lengthening lands. [A7]
5. A/B alternate-role handoff + instant start; `---abMix` = current vs. previous loop. [preroll]
6. `poly~` live pad voice layer reading the shared buffer; MIDI-note driven; per-pad choke
   default.
7. Pad mode control (scrub / live / both).
8. Per-pad pitch + play-direction.
9. MIDI-note sequencer replacing `seq~`; grid quantise; replay through `poly~`. [A2 / A4 core]
10. Selectable collision policy (choke <-> poly).
11. *(follow-on project)* A4 — Ableton MIDI track + `create_audio_clip` x16 with shared markers.

Reordering allowed but not silently (roadmap rule). Phases 1-2 are safe plumbing, shippable
and testable immediately. Phases 3-5 are the architectural risk and the focus of research.

## Open items for /max-research

- `poly~` / `groove~` voice reading a `buffer~` that `karma B` is simultaneously recording
  into — read/write contention. Test on a duplicated device.
- Note-on latency of a pre-instantiated `poly~` voice vs. `karma~` `jump` + ramp (expected
  tighter; measure).
- Shared-buffer-offsets vs. 16 `duplicate`d slice buffers for the `poly~` layer.
- `poly~` voice-management mechanism for home-voice-per-pad + choke groups + spill.
- How much of `reverseCompensation` / `* 0.0625` / the quantize-grid math transfers to
  computing `poly~` voice start offsets.
- `p RollingB`'s current internals and original intent; `---dummy` (200 ms stereo, orphaned)
  history — was it the start of this?
- `record_arm_toggle` current state (doc 19 A6: reserved for preroll, may be standing in).
- Transport-edge detection for the handoff that satisfies B1/B2 (no report feedback, no
  `---size` deferral).
- Whether the rolling window model needs `append` at all, or is pure `window`/bounds.
- `karma~` `ramp` / `snramp` 16 -> toward 441 for the handoff seam (one-message change,
  never tried).

### Stage

ideation -> discussion -> (next) research
