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
2. **Live pad layer** — a `poly~` voice pool reading the **shared captured buffer**, driven by
   **explicit `target N` routing** (one home voice per pad), NOT `midinote` auto-allocation
   (see R7a — the auto-allocate + steal lifecycle proved fragile). Voice lifecycle is an
   envelope/gate we own. Adds **per-pad pitch and play-direction** (new capability). Replaces
   the idea of a 3rd `karma~` for the sequencer voice.
3. **Sequencer** — records the pad-hit event stream off layer 2 as **`coll`** entries
   (time-keyed: `time -> pad velocity duration ...`), replays through the same `poly~`. `seq~`
   and `detonate` are both out (R7a). Event model is note-shaped so A4 (Ableton MIDI track +
   16-clip audio export) is a `coll`->SMF/clip conversion step, not a rearchitecture.

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

ideation -> discussion -> research -> build

---

## Build log

### v6_175 — Phase 1 file 1: karmaB audible (2026-09-03)

`tools/phase1_karmab_audible.py`. Inside `p Playback`: inserted `bmixL` / `bmixR`
(`+~`) so `karma A` (obj-20) and `karmaB` sum into the existing L/R outlets (obj-23 /
obj-25). 2 new boxes, 2 cords removed (`obj-20[0]->obj-23`, `obj-20[1]->obj-25`), 6 added.
No `---abMix` yet (file 2). karmaKeys still silent (file with its own routing later).

Checks: file size 1,705,180 (identical); cycle sweep 27 (unchanged); 0 structural problems;
byte-exact round-trip; `cctrace` confirms `karmaB[0/1] -> bmix -> obj-23/25 -> p soloAndMuting
-> plugout~`, and `karma A` path preserved through the same `+~`.

**Expected on test:** karmaB records/plays in lockstep with A (gB open, shared messages,
`bspeed sig~ 1`), so after a normal capture the loop should be ~+6 dB / doubled — that is the
wire proven. File 2 swaps the raw sum for the `---abMix` crossfade.

Base for next edit: `ChopChop_v6_175.amxd`.
**Live test (user): records fine, no phasing — A/B are sample-aligned. Wire confirmed.**

### v6_176 — Phase 1 file 2: ---abMix crossfade (2026-09-03)

`tools/phase1_file2_abmix.py`. Base v6_175. Replaces the raw `bmixL/bmixR` sum with a linear
A/B crossfade off the existing `AB_MIX` dial (0-100, initial 0 -> `s ---abMix`, previously
orphaned):

```
r ---abMix -> / 100. -> [$1 20( -> line~ --+-- (mix)   -> *~ on karmaB L/R  (B gain)
                                           \- !-~ 1. -> *~ on karma A L/R   (1-mix, A gain)
*~ outputs -> bmixL / bmixR (unchanged) -> obj-23 / obj-25
```

9 new boxes; 4 file-1 direct cords removed and re-routed through the `*~`. Linear xfade =
constant level for coherent A/B. Dial initial 0 and nothing forces `---abMix` on load, so
`line~` rests at 0 -> A full / B silent = v6_174 default. Safe.

Checks: size 1,705,180 (identical); cycles 27; 0 structural problems; byte-exact round-trip;
`cctrace` confirms `xf_l` feeds all four `*~` gains and A/B reach `bmixL/R` only through them.

**Expected on test:** `A/B Mix` at 0 = only A (as before); sweep up = crossfade to karmaB;
at 100 = only karmaB. Since B currently records the same content as A, the sweep should sound
like level staying put / a subtle doubling in the middle, not a dropout. karmaKeys still
silent.

Base for next edit: `ChopChop_v6_176.amxd`.
**Live test (user): full-A and full-B identical; 50/50 gives slight phasing + a small dip =
A/B playheads not sample-locked (separate speed signals). Test-only condition (real A/B use =
non-identical content). Accepted, noted for Phase 5 seam work.**

### v6_177 — Phase 1 file 3: A/B hard-mute toggles + region-overlay-under-reverse (2026-09-03)

`tools/phase1_file3_enables_reverse.py`. Base v6_176. **Two independent changes, bundled at
user request** (each revertible on its own — A is the `en_*`/`vA_*`/`vB_*`/`voiceOn*` ids, B is
the `ovr_rev*` ids + the `ovr_sub`->`ovr_add` reroute).

**A — hard mute for karma A and karma B.** Two `live.toggle` params (`enableA` / `enableB`,
enum off/on, initial 1) in the OVERDUB presentation panel (gap under the OVR AMT dial, pres
y118), sending `---voiceOnA` / `---voiceOnB`. In `p Playback` each drives `$1 12 -> line~ 1.`
into a new `*~` folded onto the file-2 gain signals: `A gain = (1-mix)*voiceOnA`,
`B gain = mix*voiceOnB`. Toggle off -> `line~` ramps to 0 in 12 ms = that voice silenced,
click-free. `---enableA/B` (the message-gate channel) left untouched. 6 root + 8 Playback boxes.

**B — region overlay under reverse (roadmap A3).** Per-slice test was `((i-s+16)%16) < n` —
right forward, wrong under reverse. Added `gate 2 1` on `---effectiveReverse` picking `ovr_sub`
(i-s, outlet 0) or `ovr_revneg` (`* -1` = s-i, outlet 1) into `ovr_add`; `change -> t b i` sets
the gate (`+1` -> 1|2) then re-fires `ovr_fire3` so the overlay repaints on a direction flip.
`gate 2 1` defaults forward so a load with no `---effectiveReverse` still lights the region.
6 root boxes; `ovr_sub->ovr_add` rerouted. `ovr_fire3` now has 4 recompute sources (added
`ovr_revt`). doc 19 said "two objects" — it needed six for correct load + repaint behaviour.

Checks: size 1,705,180; cycles 27; 0 problems; byte-exact round-trip. `cctrace` confirms both
gain paths route through the new `*~`, `ovr_add` fed only via the reverse gate, and both
`---voiceOn*` channels sender->receiver.

**Expected on test:**
- *En A / En B toggles* (OVERDUB panel): both on = as v6_176. Turn `En A` off -> only karmaB
  audible; `En B` off -> only karma A. Both off -> silence. No clicks on toggle.
- *Reverse overlay*: engage reverse with a shortened loop and a non-1 window — the lit region
  on the pads/waveform should now sit *behind* the playhead (trailing it) instead of ahead,
  and flip back when reverse releases.

Base for next edit: `ChopChop_v6_177.amxd`.
**Live test (user): mute toggles work perfectly. A3 overlay fix BROKE the overlay on Reloop
(normal + reverse) — relocates the whole region outside the playing area. Unusable. Also: B
"completely out of step with A and constantly drifts" — now obvious because the mute toggles
let you A/B cleanly.**

### v6_178 — revert A3 (2026-09-03)

`tools/phase1_file3b_revert_a3.py`. Rebuilt from v6_176 with ONLY the mute-toggle half of
v6_177 re-applied. `ovr_*` overlay is back to v6_176 (pre-A3): ~1 slice lag under reverse,
self-correcting on release — the accepted behaviour. Verified: no `ovr_rev*` boxes,
`ovr_sub -> ovr_add` restored, 1,705,180 / 27 / 0 / byte-exact. **A3 is shelved** — any future
attempt must not move the forward-mode region (v6_177 did, via the `gate 2 1` default path or
the `ovr_add` reroute).

### v6_179 — sample-lock karmaB to karma A (2026-09-03)

`tools/phase1_file4_syncB_speed.py`. Base v6_178. Root cause of the B drift (flagged since the
v6_176 log): karmaB's speed inlet was a private `bspeed sig~ 1`, independent of karma A's
speed chain. Fix: feed `karmaB[2]` from `obj-7` (chain end, already feeding `obj-20[2]` and
`karmaKeys[2]`); drop the orphaned `bspeed`. All three karma instances now share one speed
signal incl. every transport/glitch modulation -> B tracks A exactly. **Reversed again in
Phase 3-5** when karmaB becomes the independent transport-locked rolling voice.
Verified: `obj-7` fans to A/Keys/B; 1,705,180 / 27 / 0 / byte-exact.

**Expected on test:** overlay behaves as it did pre-v6_177. `A/B Mix` sweep and En A / En B
toggling should now hold together with no drift / phasing — B is locked to A.

Base for next edit: `ChopChop_v6_179.amxd`.
**Live test (user): 179 fixes drift + overlay. But observed spurious records/overdubs into B,
B at a different length than A (capturing A at 4 bars, testing reloop), and B following A into
reverse then snapping back to forward after ~1 bar while A stays reversed.**

### v6_180 — disconnect the half-built p RollingB from karmaB (2026-09-03)

`tools/phase1_file5_disconnect_rollingB.py`. Base v6_179. Diagnosis (confirmed by the user's
symptoms): `p RollingB` fires once per load (onebang armed only by `loadbang`; `r ---bRealign`
has no sender), sending karmaB `overdub 0 / record / [delay] / play / record` with **no `stop`
first**. That leaves karmaB mid-overdub recording device input unbidden, at a loop length set
by that stray pass rather than the user's capture. Then:
- karmaB mirrors A's `window` via `gB`, but `window` scales as a fraction of the *captured*
  length -> different absolute region on B (the length mismatch).
- v6_179 shares A's speed, so B follows A into reverse; `p RollingB`'s `delay` (fallback
  **2000 ms ~= 1 bar @ 120**) then fires `play`/`record` into B, snapping it back — the
  "reverse on B for one bar" symptom.

Fix: remove the single cord `rollingB[0] -> karmaB[0]`. karmaB now sees only A's real
record/play/stop/window via `gB` (+ `bk_ramp`/`bk_snramp` declick at load, + the audio input)
= a true mirror of A. `p RollingB` left intact, outlet dangling, for **Phase 3** to rebuild
(needs `stop` before `record` + a real `---bRealign` trigger).
Verified: karmaB msg feeders now `gB` / `bk_ramp` / `bk_snramp` / `obj-34` only;
1,705,180 / 27 / 0 / byte-exact.

**Expected on test:** no records into B you didn't ask for; B captures with A, same length;
B follows A's length changes / reloop / reverse exactly, no 1-bar snap-back.

Base for next edit: `ChopChop_v6_180.amxd`.

---

## Research (2026-09-03)

Object facts verified against `.claude/max-objects/` (the framework DB). Device topology read
directly from `ChopChop_v6_174_BASE.amxd` JSON (scratchpad extractor
`amxd_extract.py` / `amxd_scope.py`).

### R1. Current device audio topology (read from the file)

```
plugin~ (device in) --+-- ingain_L/R (*~ ---inputGain) --> p Playback in 0,1   [karma A rec input; karmaB input]
                      +-- p Audio Routing in 0,1                                [DRY: raw input, state-gated]

p Playback out 0,1 (karma A audio L/R) --> p soloAndMuting --> plugout~         [WET]
p Audio Routing out 0,1 -------------------------------------> plugout~         [DRY, summed at plugout~]
```

- **`karmaB` (`karma~ ---bufB 2`) and `karmaKeys` (`karma~ ---bufFreeze 2`) have no output
  cords.** That is the A1 blocker, confirmed.
- `p Playback` external outlets: 0,1 = karma A audio; 2 = position report (elem 0); 3,4 =
  other report/status. Adding karmaB audio is best done **inside `p Playback`** (mix A+B before
  `p soloAndMuting`) to keep the external outlet count stable — fewer new root cords for the
  checklist.
- `AB_MIX` `live.dial` -> `s ---abMix` (sender exists, **no receiver**). The crossfade belongs
  in the in-`p Playback` mix.
- `p Audio Routing` is a small **state-gated** signal path (2 in / 2 out, `gate~ 2` + `*~`
  crossfade-to-silence on `---armed`/`---playing`/`---recording`/`---overdub`), not the master
  mix. Leave it for the DRY monitor path.

### R2. `p RollingB` — what it actually is (read from the file)

`phasor~ @frequency 1n @lock 1 -> delta~ -> <~ -0.5 -> edge~ -> onebang`, then `t b b b`
firing `overdub 0` + `record`, a `delay` whose time is `r ---size`, then `t b b b` -> `play` +
`1 -> s ---bAudible`; the whole cycle gated by `gate 1 1` behind `r ---recordOn` (`sel 1`).

- It is a **bar-edge-locked periodic re-record of karmaB, one loop-length per pass, self-
  retriggering while `---recordOn`** — not yet a continuous ring, but the right skeleton.
- **Orphaned both ends:** `r ---bRealign` has no sender; `s ---bAudible` has no receiver;
  karmaB output unwired.
- **Latent bug when revived:** it sends `record` from a playing state = overdub
  (karma-loop-semantics S1). A true re-capture needs **`stop` before `record`**. Add it.
- The `phasor~ @lock 1 -> delta~ -> <~ -0.5 -> edge~ -> onebang` chain is the **in-file,
  proven, transport-derived bar-edge-once detector**. Reuse it verbatim for the handoff
  trigger — it satisfies B1 (no karma~ report in the loop).

### R3. `p Record_And_Quantize` — the quantise-grid primitive already exists

`inlet -> sel 0 1 2 3 4 -> t 1n / t 2n / t 4n / t 8n / t 16n -> phasor~ @frequency 1n @lock 1
-> p detect_edge -> onebang -> outlet`.

Selectable transport-locked grid (whole/half/quarter/8th/16th), proven in-file. **This is D7.**
Extend with an "off" bypass (route around `onebang`) and reuse the same shape for MIDI note-on
quantise. `ButtonQuantize` (`live.menu`) already offers 16n/32n/64n for pad-trigger quantise
via the `TriggerPoisition` subsystem — same pattern.

### R4. MIDI infrastructure — there is none

**No `notein` / `noteout` / `midiin` / `midiout` / `midiparse` / `makenote` / `kslider`
anywhere in the device.** Pad input is Live-parameter-mapped `live.button`s
(`pad_trigger_1..16`) producing message-domain indices 0-15. Consequences:

- "MIDI-at-core" (D1 L3 / D8) means the **event model** is note-shaped
  `(time, pitch/pad, velocity, duration)` — not routing through `notein`/`noteout`.
- **`live.button` carries no velocity.** Sequencer velocity is synthetic (fixed, or from a
  `live.dial` / aftertouch source added later).
- A4's "pad hits as real MIDI notes on an Ableton track" needs the **LOM clip-write path**
  (doc 09) — a genuine new subsystem, correctly deferred. The internal store must be
  A4-shaped now.

### R5. Object choices (DB-verified)

| Need | Object | Notes |
|---|---|---|
| Per-voice slice player | **`groove~ ---thisBuffer 2`** (in=3 out=2, RNBO-ok) | inlet 0 = signal rate/increment (**negative = true reverse from current pos**, per phasor accumulator semantics); inlets 1,2 = loop min/max in **ms** (the slice region); `startloop`/`stop`; `set`. One object gives per-pad **pitch + direction**. |
| Alt one-shot player | `wave~` (in=3 out=1, RNBO-ok) / `play~` (ms-position, needs external ramp) | `wave~` = 0-1 phase across a start/end ms window, strictly non-looping; `play~` has a done-bang but no built-in varispeed. |
| Voice pool | **`poly~ <voice>.maxpat 16`** | I/O = the voice subpatcher's `in`/`out`/`in~`/`out~` count. `midinote`/`note` = auto voice-alloc + steal; `target N` = explicit home-voice-per-pad; `thispoly~` inside for `mute` / busy / `@steal`. |
| Alt voice pool | `mc.groove~` N-chan | lighter, no subpatcher plumbing, **but** no built-in alloc/steal/choke — hand-rolled. `poly~` preferred. |
| Transport lock | **`phasor~ @frequency 1n @lock 1`** | already 3x in-file, proven. `plugphasor~` (beat-synced 0-1 ramp) is an alt. |
| Absolute bar/beat (if handoff needs counts) | `plugsync~` (9 outlets: state, bar, beat, ticks, timesig, tempo, ppq-ticks, samplecount, flags) | device currently reads tempo via `live.observer` instead; `plugin~`/`plugout~` already present so the plugin transport family is available. |
| Bar-edge-once | `phasor~ @lock 1 -> delta~ -> <~ -0.5 -> edge~ -> onebang` | in-file (`p RollingB`); or `phasor~ @lock 1 -> p detect_edge -> onebang` (`p Record_And_Quantize`). |
| Sequencer event store | **`detonate`** (8 params/event incl. delta-time, pitch, velocity, duration, chan; reads/writes SMF) | MIDI-at-core fit; A4 -> "write SMF / point at clip". Alt: `coll` (time-indexed lists, disk I/O, scriptable) if timing is quantised anyway; `mtr` (ms-accurate multitrack, `writejson`); `live.step` (M4L step-grid UI, 5 outlets) if a step UI is wanted over free recording. |
| Per-voice env / declick | `line~` / `curve~` (done-bang) | single space-delimited list for multi-segment `line~` (MSP rule); karma~ seam: `ramp`/`snramp` 16 -> ~200-441. |

RNBO-compat (only matters if A4 ever tempts an RNBO export — this device is a Max audio-effect
M4L, so it does not): OK = `groove~`, `wave~`, `record~`, `phasor~`, `edge~`, `delta~`,
`train~`, `makenote`, `midiformat`. Not OK = `poly~`, `play~`, `2d.wave~`, `index~`,
`plugsync~`, `coll`, `mtr`, `detonate`, `seq~`, `karma~`.

`karma~` is **not** in the framework DB (third-party). Verified I/O comes from the
`karma-*` reference skills: stereo `karma~ <buf> 2` = 3 in / 3 out; inlet 0 = L audio + **all
messages**; inlet 2 = **speed signal** (needs a live signal or it sits at 0); outlet 2 =
status (`unpack f i i f f f`: pos0-1, play, rec, [elem3 unusable], endMs, windowMs).

### R6. Signal-flow decisions for the build

- **Voice layer reads the shared `---thisBuffer`.** Slice region per note = `sliceIndex *
  (windowMs/16)` .. `+ windowMs/16` into `groove~`'s loop min/max. The existing
  `reverseCompensation` / `* 0.0625` / quantize-grid math ports to computing these ms offsets.
- **karmaB rolling:** revive `p RollingB` + `stop`-before-`record`; `---bRealign` <- arm/
  handoff; `---bAudible` -> mix.
- **Handoff:** `record_trigger` arms a `phasor~ @lock 1` bar-edge-once; on the edge, define
  karmaB's loop from the ring (`stop` -> bounds/`window` -> `play`), swap `---abMix` /
  routing so karmaB is the tape, re-arm karma A as roller. Transport-edge trigger only (B1);
  never gate `---size` (B2).
- **Loop length (D6):** point the `---capturedMs` receiver at the rolling-buffer length
  (buffer resized ~120000 in phase 2), so `window = requestedMs / rollingMs` can exceed the
  last committed size -> lengthening lands, still from device-owned values.
- **Mix:** karmaB L/R crossfaded against karma A **inside `p Playback`**, `---abMix` receiver
  drives it, sum -> `p soloAndMuting` -> `plugout~`. External outlet count unchanged.
- **Slice audio storage:** shared-buffer-offsets for the engine (low memory, auto-tracks
  re-capture); derive the 16 export clips at export time. `duplicate` works while karma~ is
  attached but `crop` does not (karma-loop-semantics S5) — a pre-sized scratch dup buffer
  avoids needing `crop`.

### R7. Verification plan — REVISED after two bad scratch-patcher batches

**Rule re-learned:** no `karma~` in a from-scratch patcher (doc 02 / `chopchop-max-testing` —
it has failed this project every time: "patchcord out of range", "can't load now"). karma~
questions go to a **duplicated copy of the real device**. And questions the docs + "the device
already does it" settle are not worth a Max session.

| # | Question | Where it's answered |
|---|---|---|
| T1 | `groove~`/`play~` read while `record~` writes the same buffer | **docs**: standard; slice layer reads committed regions behind the head -> fine |
| T2 | pre-instantiated `poly~`/`play~` voice: attack tight enough to replace `karma~` jump? | **scratch** `t2_poly_attack.maxpat` (poly~ only, metronome reference) |
| T3 | `poly~` `midinote`/`target` stealing + choke, 4-voice | **scratch** `t3_poly_steal.maxpat` |
| T4 | define shorter loop from running capture: bare `window` vs `stop->position->window->play`; `ramp`/`snramp` seam | **device-copy prototype**, Phase 3-5 (karma~) |
| T5 | `detonate` rhythm round-trip vs a metronome; SMF write/read | **scratch** `t5_detonate_rhythm.maxpat` |
| T6 | `phasor~ @1n @lock 1 -> delta~ -> <~ -0.5 -> edge~ -> onebang` bar-edge | **device already proves it** (`p RollingB`, `p Record_And_Quantize`) — reuse verbatim |

### R7a. Scratch-patcher approach ABANDONED (2026-09-03)

Three rebuilds, none usable in the M4L editor. What the runs actually told us (keep — these
shape the design):

- **`detonate` is out.** In the M4L/standalone editor it produced clicks but **stored nothing**
  (`DET 0` on open, no accumulation). Whatever the cause, it is not a reliable store here.
  -> **Sequencer store = `coll`** (time-keyed event lists, disk read/write, scriptable), not
  `detonate`. SMF/A4 export becomes a `coll`->SMF conversion step (build-time Python tool or
  a small `js`), not a `detonate write`.
- **`poly~` + `midinote` auto-allocation is fragile.** Symptom: one note sounds, then silence
  until reload — a stuck `thispoly~` busy/free lifecycle (voice never freed -> no free voices
  -> subsequent notes dropped). Do **not** lean on `midinote`/`note` auto-allocation + steal.
- **`target N` works reliably.** -> the voice layer uses **explicit `target`-based routing**:
  one home voice per pad (`target <pad>` before each trigger), voice lifecycle driven by an
  explicit envelope/gate we own, not by `poly~`'s note bookkeeping. Choke = re-`target` the
  same voice (natural cut); overlap/poly = `target` a spillover voice deliberately.
- karma~ questions never belonged in a from-scratch patcher (doc 02). They move to a
  **duplicated-device prototype** during Phase 3-5.

Net: the voice engine is `poly~` with **manual `target` routing** (not `midinote`), and the
sequencer is **`coll`**. Both get validated for real inside a device copy, not in isolation.
Test patchers + builder left in `test-patchers/` as a record; not maintained.

### R8. Tooling — rebuilt (`patches/chopchop-project/tools/`)

`chopchop-max-testing` SKILL.md references `scripts/amxd.py` etc. — not shipped. Rebuilt this
session as a stdlib-only package under `tools/`, all verified against v6_174:

| Tool | Does | Verified |
|---|---|---|
| **`ccamxd.py`** | extract / inspect / **byte-preserving re-inject** of the main patcher blob. `--identity` `--scopes` `--dump SCOPE` `--find`. | no-op round-trip is **byte-exact**; `json.dumps(sep=(",",":"))` reproduces Max's bytes. Main blob slot 1,596,959; content 455,171; **headroom ~1.14 MB** of space padding for edits. Second small pretty patcher + embedded `.js` after the blob are never touched. |
| **`validate.py`** | per-scope: dangling cords, outlet/inlet index vs `num*`, dup cords / ids / varnames; **elementary message-cycle sweep** (Johnson, patchline-only). `--baseline` diffs and fails on new problems or a changed cycle total. | baseline = **27 cycles, 0 problems** — matches doc 18 §1 exactly. |
| **`cctrace.py`** | whole-device graph; crosses send/receive + subpatcher inlet/outlet walls. `--channel ---foo` (senders/receivers + orphan flag); `--box SCOPE:id --up/--down`. | reproduces audit orphan list (`---abMix`, `---bAudible`, `---enableA/B/Keys`, …). |
| **`ccsim.py`** | best-effort message-value simulator (trigger/sel/route/gate/toggle/button/f/message/change/onebang/split/comparators/prepend + send-receive + subpatcher). Signal objects = hard stop. **Caveat: unmodeled objects pass on outlet 0** — `cctrace` is ground truth for reachability, `ccsim` adds value logic on top. | `w_fsize 8000 -> karma~ <= ['window', 1.0]` traced across 3 scopes + 2 sends. |

The scratch prototypes `amxd_extract.py` / `amxd_scope.py` remain as thin wrappers.

### R9. `record_arm_toggle` is fully unwired (build-phase item resolved)

`cctrace --box "/:record_arm_toggle" --down` -> **no outgoing connections at all.** It is a
dead root `live.toggle`, not "standing in" for anything (doc 19 A6). **Free to claim as the
preroll arm control with zero rewiring.**

### Build-phase open items

- Decide `detonate` vs `coll` for the sequencer store after T5.
- Decide `groove~` vs `wave~` per voice after T1/T2.
- Confirm the `poly~` voice subpatcher I/O shape (audio out L/R + a done/free signal).
- `ccsim` unmodeled-and-non-outlet-0 objects seen so far: `pack`, `uzi`, `panel` (harmless),
  `split` now modeled. Extend handlers if a build's critical path runs through one.
