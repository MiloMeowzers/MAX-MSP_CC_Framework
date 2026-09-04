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
**Live test (user): no audio output on fresh load (A still captures correctly).**

### v6_181 — default the A/B mute gains to unity on load (2026-09-03)

`tools/phase1_file6_mute_loadinit.py`. Base v6_180. The p Playback audio path is
byte-identical from v6_177 through v6_180 (diffs confirm — the only changes were karmaB's
speed inlet and one karmaB message cord), and v6_177's mute toggles worked **because they
were clicked**. On a clean load nothing drives `vA_l` / `vB_l`: `line~ 1.` did not present
1.0 at instantiation here, and a `parameter_enable` `live.toggle` does not bang its outlet on
device load (Live restores param values *after* loadbang — the reason this device has INIT
chains). So `vA_x = xf_a * vA_l = 1 * 0 = 0` -> karma A silent, nothing to correct it.

Fix: `loadbang -> [1 15( -> vA_l / vB_l` in p Playback. Both mute `line~` ramp to unity at
load; a moved toggle still drives its own `line~`. Verified: `vA_l`/`vB_l` inlet 0 now fed by
both the toggle chain and `vmute_lbm`; 1,705,180 / 27 / 0 / byte-exact.

**Lesson:** any param-driven *signal* chain added to this device needs an explicit load-init
(`loadbang` or `live.thisdevice`); never assume the `live.*` control fires on load.

**Expected on test:** audio present on a fresh load with nothing touched; En A / En B still
mute their voice; `A/B Mix` still crossfades.

Base for next edit: `ChopChop_v6_181.amxd`.
**Live test (user): A audio OK now. B nothing at all; mute + A/B Mix have no audible effect.**

### R10. karmaB was never mirroring karma A (root cause of the whole B saga)

Traced in v6_181: **`obj-20` (karma A) inlet 0 is fed DIRECTLY by ~11 sources** —
`obj-13[2]` (p MessagesToKarma: record/play/overdub/jump), `obj-18[1]` (`t l l` <- p
Recording: record/play), `obj-28` (p INIT), `obj-31/38/43` (Reloop window palette), `obj-45`
(`r ---karmaMsg`: window calc + main stream), `obj-46`/`reinit_*` (report/ramp config).
**The `gB` gate only carries `kmsg_gate`'s side-stream** (`p glitching` / `p transport` /
`r ---directJump`) — NOT record/play/stop/window. So karmaB never got a `record`. `p RollingB`
was the *only* thing that made karmaB capture; v6_180 removed it -> karmaB silent, nothing for
the mix/mutes to act on. The audit's "message fan-out exists, `kmsg_gate -> gA/gB/gK`" was
describing the wrong stream. **`gA`/`gB`/`gK` + `---enableA/B/Keys` gate only the glitch
side-stream, not the transport messages** — worth remembering for any per-voice message work.

### v6_182 — mirror karma A's real message stream to karmaB (2026-09-03)

`tools/phase1_file7_mirror_karmaB.py`. Base v6_181. For every `obj-20` inlet-0 feeder karmaB
lacked, add the same cord to `karmaB[0]` — 11 cords, no new objects. Script asserts each
source really feeds `obj-20[0]` first. karmaB now records / windows / INITs / reloops exactly
when karma A does; `obj-34` (audio L) and the `gA`/`gB` side-stream were already parallel.
Verified: `karmaB[0]` feeders == `obj-20[0]` feeders (minus `gA`, which has `gB`);
1,705,180 / 27 / 0 / byte-exact.

**Expected on test:** fresh load -> A audible. Record a loop -> **B captures the same loop**.
`A/B Mix` now audibly crossfades A<->B (both on the same content -> roughly level-constant,
minimal phasing since B is speed-locked to A). `En A` / `En B` drop their voice (audible once
`A/B Mix` > 0).

Base for next edit: `ChopChop_v6_182.amxd`.
**Live test (user): all working. Phase 1 (A1 steps 1-3) COMPLETE at v6_182 —
karmaB audible, `---abMix` crossfade, A/B hard-mute toggles, karmaB truly mirrors karma A,
B speed-locked to A.**

### v6_183 — Phase 2: resize `---bufB` / `---bufFreeze` to 120,000 ms (2026-09-03)

`tools/phase2_resize_buffers.py`. Base v6_182. Both were hardcoded at 20000 ms in
`p BufferSwitching` with no reduction guard (only `---thisBuffer` has one). Edited the size
arg in the two existing `buffer~` declarations to `120000` — no boxes added/reordered, so the
order-sensitivity rule doesn't apply. ~42 MB/buffer stereo; ~127 MB across the four; applied
on next device load. Prereq for Phase 3 (rolling capture wants a generous ring on `---bufB`).
Verified: both decls updated, box order unchanged, 1,705,180 / 27 / 0 / byte-exact.

**Expected on test:** no audible change now; captures over 20 s into B/Keys no longer wrap
(not reachable until Phase 3/karmaKeys input exist — this is groundwork).

Base for next edit: `ChopChop_v6_183.amxd`.

### Preroll design (agreed 2026-09-03) + prototype

Scope narrowed by the user: preroll is **only** for the very first capture from a clean state
(`---hasContent == 0`); once running, normal functionality already works. Aim = remove the
wait on the first `record`. Preroll buffer length = selected LoopLength; LoopLength menu
change -> resize/restart preroll; add an LED beside the arm toggle for "preroll full".

Mechanism (from web research — `record~` loop-mode circular buffer is the documented
primitive; karma-loop-semantics §3/§6 give the karma side):
- `record~ ---thisBuffer 2 @loop 1` writes the device input into a ring while armed +
  clean-state. karma A isn't playing then, so no read/write conflict; no separate buffer
  (M4L can't resize buffers at runtime, §5).
- "Full" = `delay LoopLength` after `record~` start -> LED. Menu change -> restart.
- On first Record with (arm + full + clean): stop `record~`, **skip the `clear
  ---thisBuffer`**, send karma A `set ---thisBuffer, position 0., window (LoopLength/120000),
  play`, set `---hasContent 1` and `---capturedMs = 120000` so the existing window math
  yields the right fraction, regrid. Loop is then a window into 120000 ms -> Phase 4
  (lengthening) falls out.

**Open question the prototype answers:** does `karma~ set + window + play` on a
`record~`-filled buffer (no karma record pass) give a clean bounded loop? Everything hinges
on it.

**`ChopChop_v6_183_PREROLL_TEST.amxd`** (`tools/build_preroll_prototype.py`) — v6_183 + a
throwaway root rig near x2600 y180: `record~ ---thisBuffer 2 @loop 1` fed from
`ingain_L/R`; buttons [1 fill start] / [2 fill stop] / [3 window .033] / [3b .5] / [3c 1.]
(the 3s send `set ---thisBuffer, position 0., window <f>, play` via `s ---karmaMsg`);
number boxes on `---karmaPos` / `---karmaRep4` (loop end ms) / `---karmaRep5` (window ms) /
`---karmaPlaying`. 1,705,180 / 27 / 0 / byte-exact. **Not a version bump** — discard after.

---

### Preroll prototype results (v6_183_PREROLL_TEST / TEST2)

- `set ---thisBuffer, window X, play` **does loop the window cleanly and indefinitely** (no
  clicks, any message ordering) — BUT on a `set` (never-recorded) buffer karma treats it as a
  one-shot of the full buffer length: it loops the window for ~120 s wall-clock then goes
  silent for the remainder before wrapping. A periodic `jump 0.` / re-`play` keep-alive removes
  that gap (or a handoff to a real record pass makes it moot).
- **Pads / slice-jump and Reverse / Reloop WORK on a `set`+`window` loop.** The slice path
  sends `jump` (absolute over capture), doesn't need karma's pos report.
- **karma's pos report is dead (stuck at 0) on a `set` buffer** -> the playhead overlay won't
  track from it. Fix: drive the overlay from the keep-alive clock's phase during a preroll loop.
- `loop` is **not** a karma message ("karma doesn't understand loop"). Use `jump` / `position`.
- "tail not head" = `record~ @loop 1` ring rotation; fixed by `reset`-ing the write head on arm.

Conclusion: preroll is viable. Build = ring+LED (file 1), capture handoff + keep-alive
(file 2), overlay source swap (file 3).

### v6_184 — Phase 3 file 1: preroll ring + FULL LED (2026-09-03)

`tools/phase3_file1_preroll_ring.py`. Base v6_183. Adds `p Preroll` (subpatcher at root):
`record~ ---thisBuffer 2 @loop 1` fed `ingain_L/R`, runs only while `---prerollArm == 1` AND
`---hasContent == 0`; `reset, 1` on start / `0` on stop; `r ---size` drives a `delay` -> after
one full ring pass `s ---prerollFull 1`. LoopLength change resets the ring + restarts the
delay + `---prerollFull 0`; `---hasContent -> 1` force-stops it. Root: `record_arm_toggle`
(obj-29, was dead) -> `s ---prerollArm` and promoted into the OVERDUB panel right edge with an
"ARM" label; a `led` (`r ---prerollFull`) + "FULL" label beside it. **No behaviour change to
normal operation** — the ring only writes `---thisBuffer` while `---hasContent == 0`, and the
capture handoff (file 2) isn't built, so a normal Record still clears + records as before.
Verified: 1,705,180 / 27 / 0 / byte-exact; `p Preroll` 23 boxes / 33 lines; channels connected.

**Expected on test:** (1) normal record/playback unchanged. (2) With the device in its
clean/no-content state, turn the ARM toggle on -> the FULL led lights after one LoopLength.
(3) Change LoopLength while armed -> led goes dark, relights after the new LoopLength.
ARM+LED placement (OVERDUB panel right edge) is a first guess — say if it should move.

Base for next edit: `ChopChop_v6_184.amxd`.
**Live test (user): basic preroll works — toggle / FULL LED / LoopLength response all as
expected; usable for instant capture while running and for 1->4 bar lengthening (glitch during
the pass-into-running, clean after — predicted). Issues raised:
(a) repeated full INIT -> failed captures (4 bars compressed to a few slices / wrong lengths /
fragments); (b) preroll fill is visible in the waveform display (suppress, or a distinct tint);
(c) Record still has a short delay + must wait a full loop length before all pads are usable,
and pads hit during that window can stall/halt/corrupt (no handoff yet -> normal record pass);
(d) waveform vanish/restart on capture is a misleading diag for a new user.**

### v6_185 — Phase 3: rewrite p Preroll state machine (2026-09-03)

`tools/phase3_file2_preroll_statemachine.py`. Base v6_184. Full replace of `p Preroll`'s
inner patcher (a v6_184-added box, not round-tripped -> clean). Fixes for (a):
- **Ring stops on `r ---recordOn` (record START)**, not on `---hasContent -> 1` (record end).
  v6_184 kept `record~` writing `---thisBuffer` all through a normal capture, fighting karma
  -> the fragments.
- **`want = arm AND (hasContent==0)`** recomputed via `t i b` / `t b i` ordering; `change`
  only de-dupes edges, and `want` genuinely goes 0 then 1 across capture->INIT so it never
  sticks (v6_184's `pr_run` change stuck at 1).
- **`delay 400` settle** before `reset, 1` -> `record~` when the ring becomes wanted, so
  INIT's `clear` / `regrid` / `stop` / `window 1` / `position 0` all land first; repeated
  INITs keep pushing the restart out.
- `pr_running` flag gates the LoopLength-change restart.
`p Preroll` 23->33 boxes. Verified 1,705,180 / 27 / 0 / byte-exact.

**Still to do:** (b)/(d) waveform display during fill = v6_186; (c) the capture handoff
(`set`+`window`+keep-alive on Record when preroll full) + pad-safety gating = v6_187 — that's
what actually removes the delay and the pad-unsafe window.

**Expected on test:** repeated full INIT -> clean captures, correct lengths, no fragments.
Basic preroll fill/LED unchanged.

Base for next edit: `ChopChop_v6_185.amxd`.
**Live test (user): 15 full INIT + capture at varied lengths -> NO failed captures (v6_185
reliability fix confirmed). But more hiss/crackle "during the transfer" than the first run,
worse near the loop start.** (Expected — v6_185 still runs the normal `clear` + karma
record-pass on Record; stopping the ring right at Record press stacks record~'s hard stop +
the buffer clear + karma record on one 120 MB buffer.)

### v6_186 — Phase 3: LoopLength-bounded ring + the capture handoff (2026-09-03)

`tools/phase3_file3_handoff.py`. Base v6_185. Two coupled changes:

1. **`p Preroll` ring wraps at LoopLength, not 120 s.** `record~ ---thisBuffer 2 @loop 1` now
   gets start 0 (inlet 2) and end `---size` (inlet 3), re-sent on ring start and LoopLength
   change. v6_184/185 wrapped at the 120 s buffer end, so 0..LoopLength wasn't a contiguous
   recent capture (the "tail" rotation, stale content in the window).
   **ASSUMPTION: `record~ <buf> 2` inlets are 0=L sig+ctrl / 1=R sig / 2=start ms / 3=end ms.**
   If wrong, the ring keeps wrapping at 120 s — user should check whether the captured loop is
   now the *head* (contiguous, correct) rather than a rotated tail.
2. **Capture handoff.** `gate 2` on `record_trigger -> recordon_send`, control `---prerollFull+1`:
   full -> `s ---prerollCapture`; not full -> `s ---recordOn` (unchanged). New `p PrerollCapture`
   on `r ---prerollCapture`: `s ---prerollLoop 1`; `s ---hasContent 1`; `s ---capturedMs 120000`
   (overrides the size latch, last wins); `s ---karmaMsg "set ---thisBuffer, position 0.,
   window <---size/120000>, play"`; `s ---regrid`. Keep-alive: `r ---sliceEdge -> counter 0 15
   -> carry -> gate(---prerollLoop) -> jump 0. -> s ---karmaMsg` (resets karma's phantom
   one-shot every LoopLength). `---prerollLoop` cleared by `---hasContent==0` (INIT) or
   `---recordOn` (normal record). **No `clear`, no record pass** -> the crackle phase is gone.
Verified: 1,705,180 / 27 / 0 / byte-exact; channels routed.

**Expected on test:** with preroll FULL, hitting Record gives an **instant** looped capture —
no `clear`, no wait, no crackle-during-transfer, pads/reverse/reloop usable immediately.
Overlay still frozen during a preroll loop (pos report dead — v6_187). If preroll is NOT full,
Record is exactly as before. Also check the captured loop is the *head* of your input now (ring
end-point assumption).

Base for next edit: `ChopChop_v6_186.amxd`.
**Live test (user): preroll fills + refills on LoopLength change, but Record -> no audio / no
playstate.**

### v6_187 — fix the handoff (2026-09-03)

`tools/phase3_file4_handoff_fixes.py`. Base v6_186. Causes of "no audio on Record":
1. **`rc_gate` was `gate 2` = closed by default** -> a Record click before `---prerollFull`
   ever fired routed nowhere (not `---recordOn`, not `---prerollCapture`). -> `gate 2 1` +
   `loadbang 1 -> rc_gate` control. Record now always routes: control 1 = normal (default),
   control 2 = handoff (when `---prerollFull`).
2. **`record~` start/end inlets 2/3 were an unverified assumption** and the extra cords may
   have disturbed the ring. Reverted: `pr_rec` back to 2 inlets, `pr_startpt`/`pr_endptf`
   removed. Ring wraps at 120 s again (rotated capture, functional) — proper LoopLength
   bounding waits until the `record~ <buf> 2` inlet layout is confirmed.
3. **`pc_fracf` had no default** -> a missing `---size` -> `window 0` -> silence. Now
   `f 0.0667` (~4 bar / 120 s).
Verified: 1,705,180 / 27 / 0 / byte-exact.

**Expected on test:** Record with preroll NOT full -> normal capture (as v6_185). Record with
preroll FULL -> instant windowed loop (audible, playstate set), no clear/record pass. Overlay
still frozen during a preroll loop. Ring capture is rotated (not head-aligned) until the
`record~` inlet layout is verified.

Base for next edit: `ChopChop_v6_187.amxd`.

## Phase status

- **Phase 1 — karmaB audible + mixable + mirror** — DONE (v6_175-182).
- **Phase 2 — resize `---bufB` / `---bufFreeze`** — DONE (v6_183).
- **Phase 3 — transport-locked rolling capture on karmaB** — next. Rebuild `p RollingB`:
  `stop` before `record`, a real `---bRealign` sender, `---bAudible` receiver, continuous
  ring rather than a one-shot. Prototype in a duplicated device first (karma~ timing).
- Phase 4 — window-into-rolling-buffer loop model (loop lengthening).
- Phase 5 — A/B alternate-role handoff + instant start.
- Phase 6+ — `poly~` slice layer (`target` routing), pad modes, per-pad pitch/direction,
  `coll` MIDI-note sequencer.

Deferred / smaller: A3 region overlay under reverse (shelved — user: 1-slice lag acceptable);
`karmaKeys` output + audio input (A1 step 5, needs a design call); `---enableA/B/Keys`
message-gate senders (separate channel from the mute toggles — gates only the glitch
side-stream, see R10).

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

---

### v6_199_USEREDIT — adopted as the permanent base (2026-09-04)

User re-laid the diagnostic strip (2-col grid, x942 / x1040) and cleared the DEBUG panel of
its display boxes (`diag_gain_disp`, `diag_ovr_disp`, `diagpr_*`, `obj-31/41/46` — some `r`
objects now orphaned, harmless). `ccamxd` handles the re-saved file (1,883,883 B; identity
MISMATCH = JSON reformat only; 639 root boxes / 32 scopes / 27 cycles / 0 problems; stable
across round-trips). **All future edits start here and are LOGIC-ONLY — the presentation
layout is not to be touched.**

Visible diagnostics in this base: PLY (`r ---karmaPlaying`), FRC (`r ---windowVal`, flonum),
HC, FUL, SIZ (`r ---size`) in col 1; CAP (`r ---capturedMs`, flonum), HND (`r ---dbgHandoff`),
SPD (`r ---dbgSpeed` — `snapshot~ 120` on `obj-7` out in `p Playback`, the shared karma speed
signal), RON (`r ---recordOn`) in col 2. MAN button (`mk_btn` → `set ---thisBuffer, window
0.05, jump 0., play` → `s ---karmaMsg`) at pres x803.

### DIAGNOSIS — the `set`+`window` handoff cannot sustain under a running transport

Clean-state test on v6_199_USEREDIT (4-bar, Arm → input → FULL LED → Record), strip readings:

| | armed, LED green | Record clicked | MAN, transport OFF |
|---|---|---|---|
| PLY | 0 | 0 | **1** |
| FRC | 1.0 | 1.0 | 1.0 |
| HC  | 0 | 0 | 0 |
| SPD | **1.0** | **1.0** | **0** |
| RON | 0 | 0 | 0 |
| HND | 0 | 1.0 | 1.0 |

- **`---recordOn` / quantise-record chain is NOT involved.** RON stays 0. With preroll FULL,
  `rc_gate` routes the Record click to `s ---prerollCapture` *only* — never `s ---recordOn` —
  so `p RecordArming` never arms `p Record_And_Quantize`. The "record button chain fighting"
  theory (quantise engine) is ruled out.
- **`p RollingB` is fully disconnected** in this base (no lines to/from it in `p Playback`).
  Not a factor.
- **The MAN button sends a byte-identical `set/window/jump/play` over the identical
  `---karmaMsg` route** (→ `obj-45` → `obj-20[0]` / `karmaB[0]`, bypassing all gates). It
  **fails identically to the handoff with transport running**, and **succeeds with transport
  stopped**. Starting the transport also kills an already-sustaining MAN loop ("waveform
  cleared, silence").
- The only variable that tracks success/failure is transport state == SPD (0 vs 1). SPD is
  `obj-7` out = `sig~ 1` × … × `is_playing` (`p transport` outlet 1). Transport running →
  karma speed signal = 1; stopped → 0.

**Conclusion:** `karma~ set ---thisBuffer, window X, play` on a `record~`-filled buffer with
**no karma record pass** only enters/holds a play state when the speed signal is 0. The
v6_183_PREROLL_TEST prototype ("preroll is viable") was validated with the transport stopped,
which is why it looked clean. Under normal M4L use (transport running) the mechanism does not
work. This invalidates the Phase-3 handoff design (v6_186/187, `p PrerollCapture`).

**Redesign required.** The handoff must end with karma establishing a **real bounded loop**
(a genuine record pass that adopts the preroll ring content, or an A/B alternate-role handoff
where the rolling karma is already in a real recorded state). Options for the user:
1. **Pull Phase 5 forward** — karma B rolls a real transport-locked record pass while armed
   (reuse the `p RollingB` / `phasor~ @lock 1 → delta~ → <~ → edge~ → onebang` bar-edge
   detector, R2); on Record, B already holds a real loop → swap B into the A role, no phantom.
2. **karma A short adopt-pass** — on Record: `stop` → very short real `record` (one scheduler
   tick, input muted) to force karma to write loop points, then immediately define the loop
   region over the pre-filled ring bytes and `play`. Needs karma loop-point message research
   (no `karma~` in the framework DB; `loop` is not valid — only `jump`/`position`/`window`).
3. Accept preroll as a **transport-stopped-only** instant-start (niche) and make the normal
   transport-running path as fast as possible instead.

Recommendation: **option 1** — it reuses proven in-file machinery, gives a real loop (real pos
report, real lengthening in Phase 4), and matches the agreed D-series architecture.

---

### karma~ research pass — source + help file + project skills (2026-09-04)

User supplied `karma~.maxhelp` + `karma1.0/` (with **full C source** `karma~.c`, 2148 lines).
Also read the project skills `karma-loop-semantics`, `max-msp-karma-technical`,
`chopchop-size-window-architecture` (in `Downloads/chopchop/Updated skills/`).

**Version is karma 1.0**, confirmed — `karma_dsp64` posts the literal string
`"64bit_v1.0stereo"` (the line seen in ChopChop's Max console). No newer external anywhere in
the supplied tree. So the 1.0 C source is authoritative for this device.

**Complete message vocabulary** (`class_addmethod` in `karma~.c`, matches the help file's
message boxes exactly): `position` `window` `jump` `stop` `play` `record` `append` `set`
`overdub` `report` `ramp` `snramp` `snrcurv` `interp`. Attributes: `report` `ramp` `snramp`
`snrcurv` `interp` only.

- **`loopstart` / `loopend` / `@phaseout` / `buffer` / `crop` / `resize` / `sync` / `speed`
  messages DO NOT EXIST.** The `Rolling Buffer, Pre Roll and Overdub Implementation.md` doc in
  the user's tree is AI-generated and its "Verified" message claims for those are wrong — do
  not build on that doc's specifics. Its *architecture* (always-rolling `record~` dual buffer
  + role swap, "Mode 2 Pre-Roll") is sound and matches Rodrigo's own live-looping approach.
- **`set <buf>` on a buffer karma did not record → loop = the whole allocation.** Confirmed in
  source (`karma_bufchange`: `x->loop = x->end = x->bframes-1`) and in `karma-loop-semantics`
  §6 (measured: 19999.98 ms end on a 20000 ms buffer). `window` is always a fraction of that.
- **`crop` fails ("can't resize"), `size`/`sizeinsamps` fail in M4L ("can't resize now")** —
  DSP is always running in a M4L device. `karma-loop-semantics` §5. So there is **no message
  that turns a `record~`-pre-filled buffer region into a real bounded karma loop.**
- **A real loop is only ever established by a karma record pass.** `stop` / `play` / `record`
  all *close* an initial loop and define its length (`karma-loop-semantics` §1–2). Canonical
  flow: `stop → record → (loop duration) → stop|play|record`. karma's `record` has **zero
  latency** — `karma_record` from a stopped state zeroes the buffer and starts writing in the
  same signal block. The "wait" in ChopChop is its own `p Record_And_Quantize` transport-
  `phasor~` downbeat gate, not karma.
- **`karma_record` from a stopped state ZEROES THE ENTIRE BUFFER** (`for i<frms: b[i]=0`) then
  records. From a *playing* state it overdubs, no wipe. This is why a "record" reaching karma
  mid-handoff wipes the waveform.
- **Speed inlet is signal-preferential and "nothing connected / value 0 → records/plays at
  speed 0"** (`max-msp-karma-technical` skill; source: at `speed==0`, `dir=0`, `sprale=0`,
  `dpos` frozen → no motion). ChopChop's `obj-7 = *~ 1.` multiplies the `sig~ 1` speed chain
  by `p transport` outlet 1 = Live's `is_playing`, so **transport stopped ⇒ karma speed 0**.
  This is a deliberate "looper only runs while Ableton plays" choice but it is entangled with
  the handoff failure.

**Unresolved by static analysis:** the observed inversion (MAN `set/window/play` plays with
SPD 0 / transport off, does NOT play with SPD 1 / transport on) is backwards from the 1.0
source, which says speed 0 = frozen. Needs an in-Max probe (below). What IS certain: the
normal real-record path (`record → delay(---size) → play`) works with transport running
(confirmed by every prior device test) — only the `set`+`window` phantom fails.

**Conclusion / recommendation unchanged and now well-supported:** drop `set`+`window` preroll.
Two real routes:
- **(A) minimal** — give `p Record_And_Quantize` an "off/bypass" (skill R3 already proposes
  this) so `record` fires the instant the button is hit from a clean state. Loop still needs
  one LoopLength to *complete* (real pass) but starts immediately; enable pads against the
  in-progress loop. No ring, no phantom, ~small edit.
- **(B) full (Phase 5 forward)** — karma B runs a continuous **real** record pass while armed
  (its speed must be kept nonzero regardless of arm state). On capture, `stop`/`play` karma B
  → real loop closed instantly → swap B into the output role, A starts a fresh record. Real
  pos reports, real `window`, Phase-4 lengthening all fall out. This is the rolling-buffer
  doc's Mode 2.

**Probe to run before building either:** on v6_199_USEREDIT, transport RUNNING, clean state,
do a NORMAL capture (Record with ARM off, so preroll does not intercept) at a 4-bar
LoopLength. Confirm it makes a clean on-beat 4-bar loop with working pads. If yes (expected),
the real-record path is the foundation and `set`+`window` is abandoned for good.

### v6_201 — Phase 3 file 18: preroll playback moves to groove~ (2026-09-04)

`tools/phase3_file18_groove_preroll_engine.py`. Base **v6_199_USEREDIT** (logic-only, no
presentation change). Implements option C from the karma research pass.

**p Playback (obj-118) — new groove~ engine:**
- `gv` = `groove~ ---thisBuffer 2`, fed by a private `gv_sig` (`sig~ 1.`) on inlet 0 — a
  clean forward rate that is **NOT** multiplied by `is_playing` (that gate is what made the
  karma phantom transport-dependent).
- `gv_r` (`r ---gvMsg`) → gv[0]; `gv_lsr` (`r ---gvLoopStart`) → gv[1]; `gv_ler`
  (`r ---gvLoopEnd`) → gv[2].
- `gv[0]/gv[1]` → `gvxL/gvxR` (`*~`), gain from `gv_gate` (`line~`) ← `gv_gm` (`$1 15`) ←
  `gv_gr` (`r ---prerollLoop`): 0 normally, ramps to 1 on capture.
- `gv_plr` (`r ---prerollLoop`) → `sel 0` → `stop` → gv[0]: any INIT stops groove~.
- `gvmixL/gvmixR` (`+~`) inserted between `bmixL/bmixR` and the p Playback audio outlets
  (`obj-23/obj-25`); groove~ sums in on `gvmix[1]`.

**p PrerollCapture — rewritten**, phantom removed (`pc_lm/pc_szdiv/pc_szclamp/pc_msg/
pc_kmsg/pc_t` dropped). `pc_trig` → `pc_seq` (`t b b b b b b`) fires, in order:
`s ---gvLoopEnd` = current `---size` · `s ---gvLoopStart` = 0 · `s ---gvMsg set ---thisBuffer`
· `s ---gvMsg loop 1` · `s ---gvMsg startloop` · `s ---prerollLoop 1` + `s ---dbgHandoff 1`.

**root:** `obj-123[0]` (soft INIT — also full INIT and load) → `ri_pl0 "0"` →
`s ---prerollLoop`, so a Full INIT now both stops groove~ and closes its gain.

**p Preroll:** ring bounded to `[0, ---size]` — `pr_settle` (ring-start bang) → `pr_sp0 "0"`
→ `pr_rec[2]` (start ms); `(r ---size)` + `pr_settle` → `pr_endf` (`f`) → `pr_rec[3]`
(end ms). `record~ ---thisBuffer 2` inlets 2/3 = start/end ms, DB- and sample-patch-verified.

New channels: `---gvMsg` `---gvLoopStart` `---gvLoopEnd` `---prerollLoop`.
Verified: 1,883,883 / **27** cycles / 0 problems, size preserved.

**Expected on test** (v6_199_USEREDIT layout, no edit needed):
- Clean state, transport running, 4-bar LoopLength. Arm → input → FUL LED lights.
- Hit Record → **groove~** plays `[0, 4 bars]` of the ring immediately, looping. Should be
  audible with **transport running** (the case the phantom failed). HND reads 1.
- **PLY (`---karmaPlaying`) will stay 0** during a groove~ preroll loop — groove~ is not
  karma. Judge by ear + HND, not PLY, for this build.
- Full INIT → groove~ stops, gain closes, ring left silent (per your requirement).
- Pads / slice / reverse / overlay do **not** act on the groove~ loop yet — that's file 19.
- Normal Record (ARM off, preroll does not intercept) unchanged.

Base for next edit: `ChopChop_v6_201.amxd`.

---

## Phase 5/6 design spec — rolling-buffer architecture (2026-09-04, agreed with user)

The device is rebuilt around a **rolling capture group** that is completely separate from the
loop the device plays. Settled over a long design conversation; this section is the reference.

### The three layers

```
  INPUT (dry + optional feedback)
        |
  [1] ROLLING CAPTURE GROUP  --------------------  the "tape" / history. Never heard directly.
        - continuous, fixed short cadence (1 bar), transport-locked
        - fills ring buffer(s) sized for the MAX master length
        |   COMMIT  = grab the last <LoopLength> off the ring, fast-render into the master
        v
  [2] MASTER LOOP  ---------------------------------  one committed karma~, read-only between commits
        - real, bounded, correct-length karma loop
        - the existing slice engine runs on it UNCHANGED: jump / window / reverse / overlay / reloop
        - OVERDUB layers onto it in real time, within bounds (karma-native)
        |   master bed  +  voice hits  (summed, additive)
        v
  [3] VOICES + DSP  -------------------------------  performance layer, output-only by default
        - poly~ voice pool, `target N` routing (NOT midinote), pitch/dir/env per pad
        - coll sequencer drives the VOICES, not the tape
        - DSP chain (soloAndMuting / glitch / pitchMod) post-master -> plugout~
        - optional FEEDBACK gain: main mix -> back into [1]'s record input
```

### Buffer / karma roles (roles rotate, instances are fixed)

| Instance | Reads | Job | Records? |
|---|---|---|---|
| `karmaMaster` | whichever buffer is currently frozen | committed loop; drives slices/overlay/output | never |
| `karmaRoll1/2` (or ring readers) | rolling-pool buffers | the churn | yes, continuous |
| `groove~` (v6_201 engine) | ring buffer | cold-start bridge + the READ side of every Commit render | no |
| `poly~` pool | slices of `bufFreeze` | pad hits + sequenced layers | never (transient voices) |

Buffers: a pool of ~4 (`buf1..buf4`) cycling through roles + `bufFreeze` for the voice
layer. Recommend 4 so one buffer is always "cooling" and a `record`'s buffer-zero never lands
on a swap edge. Existing device buffers: `---thisBuffer` / `---bufB` / `---bufFreeze` (all
120000 ms) — reuse + add.

### The four write / hold operations — keep the vocabulary separate

| Op | Writes | From | Trigger | Purpose |
|---|---|---|---|---|
| **Roll** | rolling ring(s) | live input mix (+ feedback) | automatic, continuous while armed | keeps a real, recent, on-beat loop always available |
| **Commit** | master slot | last `LoopLength` off the ring | **auto** on the first phrase boundary after arm; **manual** button after that (optional `follow` = every boundary) | put new material into the base loop — instant, because the audio already exists |
| **Snapshot** ("Freeze" button, existing) | `bufFreeze` | master output, **clean or wet** (toggle) | manual | stable source for the poly/sequencer voices, immune to later base-layer DSP / overdubs |
| **Overdub** (existing toggle) | master buffer | live input / voices, within loop bounds | manual hold | karma-native real-time layering onto the existing master, no length change |

Roll is the only fully automatic one. The first Commit is automatic (it *is* the implicit
first Record: establishes the master, sets `---hasContent`, fades in `karmaMaster`, hands the
slice engine over, ends the `groove~` bridge). Every Commit after is manual. `hold` locks the
current master against any Commit, manual or auto.

### Decoupled: roll cadence vs master length

The rolling chain runs at a **fixed short cadence (1 bar)**, always. **LoopLength governs
only the master** — how much Commit grabs and the master loop's bounds. Running the whole
chain at the master length (e.g. 8 bars) means up to 8 bars of dead time before a change can
reach the output; decoupling makes responsiveness sub-bar regardless of master length.

**Fast-render Commit:** on Commit, a `groove~` reads the last `LoopLength` off the ring at
high speed (e.g. 8x) into `karmaMaster` recording at the same speed. A 4-bar master renders
in ~1/2 bar wall-clock; 8 bars in ~1 bar. `karmaMaster` ends with a real, bounded karma loop
(full slice/jump/overlay), crossfaded in against the old master.

- Loop start = the commit point (bar-aligned, not snapped to the 4/8-bar phrase grid) — like
  a hardware looper punch-in. Add phrase-grid snapping later only if wanted.
- The render `groove~` source and `karmaMaster`'s record must be driven off the **same**
  high-speed ramp so they stay locked and close at the right `maxpos`.
- karma clamps record advance to `loop/1024` per sample (~375x for a 4-bar loop @ 48k) — 8x
  is well inside it; render speed is a tunable with a ceiling.
- Ring-wrap on the grab (`[writePos - LoopLength, writePos]` crossing the `@loop 1` boundary):
  size the ring >> LoopLength and clamp for now; proper fix is `poke~`/`count~` with a
  modular read (rolling-buffer doc "Alternative Approach").
- "Lengthen 1->4 bars" falls straight out — the ring always holds the max length, so set
  LoopLength to 4 and Commit.

### The two gains

- **Feedback gain** (main mix -> Roll input): 0 = Roll captures dry input only, every Commit
  is a clean new loop. >0 = Roll captures the processed/performed result, so a Commit reshapes
  what the loop *is* (not just layers on it like Overdub). Bounded: both gains <1 => decays.
- **Commit crossfade gain** (rendered loop -> master): unity = replace; below unity = blend
  into the existing master. N/A for the first (auto) Commit — nothing to fade against.

### Why infinite regress can't happen

1. Master buffer is **read-only between commits** — pads `jump`/`window`, never write. Slicing
   the master can't change the master.
2. Voice layer is **output-only by default** — `poly~` -> output bus, not to any record input.
   Layering pad hits doesn't accumulate. `coll` fires transient voices; nothing grows.
3. The one accumulating path (main mix -> Roll input) is a **single feedback gain, default 0**,
   and it's a mix not a multiply.

### Control surface

`Arm` · `Commit` (+ crossfade gain, + `follow`, + `hold`) · `Freeze/Snapshot` (+ clean/wet)
· `Overdub` · `Feedback gain`.

### Build order

- **v6_202** — the rolling substrate: continuous ring + fixed 1-bar transport-locked cadence
  + write-position tracking + repoint the v6_201 `groove~` to grab `[writePos - LoopLength,
  writePos]`. Monitor tap + diagnostics. No master/slice change yet.
- **v6_203** — fast-render Commit into `karmaMaster`; crossfade; auto-first / manual-after
  lifecycle; `---hasContent` handover.
- **v6_204** — Snapshot clean/wet split; feedback gain into the Roll input.
- **v6_205+** — `poly~` voice layer (`target N`), `coll` sequencer, per-pad pitch/direction.

### Open verification items (test in Max, do not assume)

- karma record fidelity at 8x (ipoke~ interpolation, the `loop/1024` clamp interaction).
- `groove~` behaviour when `loopstart > loopend` (wrapping grab) — assume it does NOT wrap;
  design around it.
- Exact sample offset between `phasor~ @lock 1` wrap and the audible bar in Live 12.
- Whether a per-bar `record` buffer-zero on the rolling karmas is a CPU problem at the device
  buffer size (argues for smaller dedicated roll buffers, or `poke~` ring instead of karma
  record passes for layer [1]).

### v6_202 — Phase 5 file 1: rolling substrate (2026-09-04)

`tools/phase3_file19_rolling_substrate.py`. Base v6_201. Logic-only; **no presentation
layout change**. First increment of the rolling-buffer architecture — the continuous ring +
fixed cadence that Commit/render (v6_203) will sit on.

- **`buffer~ ---rollBuf 120000 2`** added in `p Playback/p BufferSwitching`.
- **`p RollCapture`** (new root subpatcher, x2600 y560, 2 audio inlets ← `ingain_L/R`):
  `record~ ---rollBuf 2 @loop 1` runs continuously while `---prerollArm == 1` (`sel 1 0` →
  `1`+`reset` on arm, `0` on disarm). `phasor~ @frequency 1n @lock 1 → delta~ → <~ 0. →
  edge~` = 1-bar transport-locked cadence → `counter` → `s ---dbgBar`. `snapshot~` on the
  `record~` sync outlet, banged by the bar edge → `* 120000.` → `s ---rollWritePos` (ring
  write position in ms latched at each bar mark).
- **`p Preroll`**: `p_l/p_r → pr_rec` cut — the old bounded ring no longer writes
  `---thisBuffer` (karma A's buffer). `---prerollFull` / FUL-LED timer logic untouched.
- **`p PrerollCapture`**: groove~ now grabs from `---rollBuf`, region
  `[writePos − ---size, writePos]`. `pc_setb` → `set ---rollBuf`. `pc_wef` (`f`, cold-fed by
  `r ---rollWritePos`, latched by `pc_seq[4]`) → `s ---gvLoopEnd` and → `pc_ssub (−) ←
  pc_szf(---size)` → `pc_swrap (expr ($f1<0.)?($f1+120000.):$f1)` → `s ---gvLoopStart`. The
  fixed `0` loopstart (`pc_ls`) removed.
- **Diag repoint** (logic only, both fields obsolete under groove~): `dg_spd_r`
  `r ---dbgSpeed` → **`r ---dbgBar`** (SPD field = bar counter), `dg_frc_r` `r ---windowVal`
  → **`r ---rollWritePos`** (FRC field = ring write pos ms).

New channels: `---rollBuf` (buffer), `---dbgBar`, `---rollWritePos`.
Verified: 1,883,883 / **27** cycles / 0 problems, size preserved.

**Expected on test** (v6_199_USEREDIT layout, no edit):
- Arm, transport running. **SPD field** should now tick up once per bar, locked to Live's
  transport (it's the `phasor~ @lock 1` bar counter). **FRC field** shows the ring write
  position in ms, advancing ~one bar's worth each bar, wrapping near 120000.
- Let it roll a few bars, hit Record → groove~ plays the last `LoopLength` ending at the most
  recent bar mark, from `---rollBuf`. Do it again 2 bars later → a different, more recent
  slice. Responsiveness is one bar regardless of LoopLength.
- If the grabbed audio is stale / wrong length / glitches at the wrap: the `record~` sync
  outlet scaling assumption (0–1 × 120000 = ms) is wrong — first open item in the spec.
- Full INIT still stops groove~ and closes the gate (v6_201 behaviour).
- No master / slice / karma change — PLY stays 0 for a groove~ preroll, as in v6_201.

Base for next edit: `ChopChop_v6_202.amxd`.

---

### v6_202 test (user) — FAILED on beat alignment (2026-09-04)

- LoopLength 4, master 4. "No tempo / beat alignment in the preroll — everything off from the
  start." Loop plays **½ bar + 4 bars + ½ bar** before repeating (≈ 2 extra beats). SPD field
  (`---dbgBar`) "never stops increasing, reached 159" — a free-running counter, meaningless.
  FRC (`---rollWritePos`) climbs and wraps at 120000 (units were fine; the earlier "12000"
  was a typo).
- **Diagnosis:** `record~` sync-outlet units are OK, so the offset is *structural* — the
  committed grab region wasn't an exact integer-bar window. The bar-edge latch
  (`phasor~ @lock 1 → edge~ → snapshot~`) picked a position a couple of beats off a bar line,
  and the ring wrap at 120000 ms is not a bar boundary so straddling grabs hit `groove~` with
  `loopstart > loopend` (no wrap).
- **karma record-speed verified from `karma~.c` 1.0** (+ user bench test with a scratch patch):
  `record` advances `dpos` by `speed*srscale` per sample (clamped to `loop/1024` ≈ 375× for a
  4-bar loop); loop length = `maxpos` reached; ipoke~ **linear**-interpolates the gaps for
  speed>1. So an 8× record pass fed 8×-fast audio → a real bounded loop of the correct length
  at 1× pitch. Fast-render is viable. (Scratch rig:
  `test-patchers/fastrender_probe.maxpat` — note: karma status does NOT report in a bare
  editor patcher, so the probe measures loop period with `delta~→edge~→timer`, not karma's
  status outlet.)
- **Architecture decided with the user:** fast-render Commit **from the `record~` ring**
  (not the A/B real-loop swap). Ring stays the always-full bar-aligned stage; Commit
  transcribes the last LoopLength into `karma ---thisBuffer` at 8× (~½ bar, groove~-bridged),
  yielding a real karma master the existing slice engine runs on unchanged. Deferring
  fast-render to a later version was rejected as throwaway work.

### v6_203 — Phase 5 file 2: bar-locked substrate + fast-render Commit (2026-09-04)

`tools/phase3_file20_fastrender_commit.py`. Base v6_202. Logic-only; **no presentation
change**. Fixes the v6_202 beat-alignment failure and restores a real karma master
(v6_185-level function: slice / reverse / DSP / UI / overlay all live on it again).

- **`p TempoTranslate`**: `+ s ---barMs` (bar length ms, tapped off `r_barms`).
- **`p RollCapture` reworked** — position tracking no longer uses the `record~` sync outlet:
  - Ring bar-bounded: `r ---barMs → floor(120000/barMs) = ringBars → ringBars*barMs =
    ---ringUsedMs → record~ inlet 3` (inlet 2 = 0). `record~ ---rollBuf` now wraps on an
    exact integer-bar boundary.
  - Grab end: `edge~ → t b b`; a free counter (`s ---dbgBar` unchanged) → `(cnt − armRef)`
    → `% ringBars` = **fold** → `fold*barMs = s ---rollEndMs`. An exact integer-bar position —
    **no phasor snapshot, so no 2-beat offset.** `armRef` latched on the arm bar so fold
    restarts at 0.
  - **Bar-synced Arm:** `sel 1 0` on `---prerollArm`. Armed → `pendf=1`. `t b b[0]` (bar
    edge) → `pendf` (bang) → `sel 1` → `reset, 1` to `record~` **on the downbeat**, latch
    `armRef`, clear pending. Disarm → `0` to `record~`.
  - Drift realign: `fold == 0` (`sel 0`) → bare `reset` to `record~` (head snaps to bar 0
    exactly when it would wrap).
  - `+ s ---rollFold` (fold, 0..ringBars−1).
- **`p Preroll`**: fully retire `pr_rec` (`record~ ---thisBuffer`) — v6_202 cut its audio;
  now cut its reset/1/0 control too so it can't fight karma's fast-render pass on the same
  buffer. FUL-LED / `---prerollFull` timer chain untouched.
- **`p PrerollCapture` → the Commit orchestrator** (auto first, manual after):
  - Auto-first: `r ---prerollFull → sel 1 → gate` (open while `---hasContent == 0`) → arm
    `pc_fpf`; next `r ---dbgBar` tick → `s ---prerollCapture` (same trigger the manual Record
    path uses). Fires once, then `---hasContent 1` closes the gate.
  - On `---prerollCapture`: `t b b b b b b`. o6 latch `end/barMs/size/ringUsed`;
    `sizeMs = round(size/barMs)*barMs`; `start = end − sizeMs`; `wrap = start < 0`.
    o5..o2 the groove~ bridge (`set ---rollBuf`, loop points, `startloop`, `---prerollLoop 1`).
    o0: if not wrap → `s ---commitGo [start end sizeMs/8]`; if wrap → re-arm the next-bar
    retry (defer one bar; the wrapped two-segment `play~` read is a v6_204 item).
- **`p FastRender`** (NEW root subpatcher, on `r ---commitGo`): `unpack f f f` → build
  `line~` list `"start 0. end renderMs"` → `line~ → play~ ---rollBuf 2 → send~ ---renderL/R`.
  Sequence: `s ---renderActive 1` (→ speed 8, karma rec source → play~) → `stop` → `record`
  → `delay renderMs` → `s ---renderActive 0` (speed → 1) → `play` (closes the loop) →
  `s ---regrid` → `s ---hasContent 1` → `delay 25 → s ---prerollLoop 0` (fade the bridge).
- **`p Playback`**: `obj-7 → +~ (+ fr_boost line~) → obj-20[2]` — `fr_boost` jumps to 7 while
  `---renderActive` (karma-A speed = 1+7 = 8 during the pass, 1 otherwise); karmaB / keys /
  `sp_snap` keep the un-boosted `obj-7`. Karma-A **record source** (`obj-34/obj-29`) routed
  through `selector~ 2` per channel — input 1 = live, input 2 = `receive~ ---renderL/R`,
  control = `---renderActive + 1`. `loadmess 0 → s ---renderActive` inits to the live path.
- **Diag repoint** (logic only): SPD field `dg_spd_r` → `r ---rollFold` (bar-in-ring, wraps);
  FRC field `dg_frc_r` → `r ---rollEndMs` (grab end, ms).

New channels: `---barMs ---rollEndMs ---ringUsedMs ---rollFold ---renderActive ---renderL~
---renderR~ ---commitGo`. Dropped: `---rollWritePos`.
Verified: 1,883,883 / **29** cycles / 0 problems, size preserved. The **+2 cycles** vs the
27 baseline are two standard clear-after-fire latch loops (`rc_pendf↔rc_pchk↔rc_pclr` in
RollCapture; `pc_fpf↔pc_fchk↔pc_fclr` in PrerollCapture) — same idiom as `p Preroll`'s
`pr_want` chain; each terminates in one pass.

**Unverified — test in Max / Live 12:**
1. `record~ ---rollBuf 2` inlets 2/3 = loop start/end ms (v6_201 log says verified; relied on).
2. `play~` position-ramp at 8× into `karma record` at speed 8 → a clean real loop (karma
   source + user bench test say yes; confirm end-to-end in the device).
3. `phasor~ @frequency 1n @lock 1` bar edge vs the audible downbeat in Live 12 — a residual
   offset rotates the committed loop by that fixed amount (not the v6_202 "2 beats", which
   was the non-integer grab).
4. `selector~ 2` click on the speed signal during the record pass (instant `line~` steps).
5. `---abMix` default must route karma A audible — if the committed master is silent, check
   the A/B mix dial is toward A.

**Expected on test** (v6_199_USEREDIT layout, no edit):
- Arm with transport running → the roll starts on the next bar. **SPD** now shows the
  bar-in-ring counter (wraps 0..~59), **FRC** the grab end in ms.
- One LoopLength later the FUL LED lights and the **first Commit fires automatically** on the
  next bar: `---hasContent → 1`, a real karma loop appears in `---thisBuffer`, PLY goes 1,
  pads / reverse / reloop / window / overlay all work on it. Brief groove~ bridge covers the
  ~½-bar render.
- After that, the **Record button** Commits again from the current ring (manual), same path.
- Loop should be exactly LoopLength and start on a bar line — no extra beats.

Base for next edit: `ChopChop_v6_203.amxd`.

---

### v6_203 test (user) — auto-Commit rejected; handover incomplete (2026-09-04)

- SPD wraps at **34** (not ~59) — correct: `ringBars = floor(120000/barMs)` = 34 at the
  user's tempo (barMs ≈ 3530, ~68 BPM). Not a bug.
- **½-bar silence dropouts**, one ~1 LoopLength after FUL (the auto-Commit) and again
  "around 194 bars" where **all play stopped and did not restart**. The auto-Commit
  machinery (defer/retry latch re-arming; `p FastRender`'s render `delay` getting reset)
  is the cause.
- **No waveform / no chase overlay** after the Commit: a normal Record fires a `reinit`
  (`report 20` + `snramp 16` + `ramp 16` → karma, via `---recordOn` →
  `Playback/reinit_onlybang`). The fast-render path skipped it, so karma never streamed
  position → frozen display.
- **A/B mutes do nothing** — `---enableA/---enableB/---enableKeys` have **no senders in the
  base** (feed `gate 1 1`, default open). Pre-existing v6_199 issue, not a v6_203 regression.
- **User design ruling:** *no auto-first Commit.* It is just "arm = delayed record" + a
  pointless second press and undermines the preroll. **Record is the only Commit**; the
  device stays silent until the user presses it. The preroll value is: Record can be pressed
  a beat or two late and still Commit the last *bar-aligned* LoopLength instantly.

### v6_204 — Phase 5 file 3: Record-only Commit + karma handover fix (2026-09-04)

`tools/phase3_file21_no_autocommit_handover.py`. Base v6_203. Logic-only; no presentation
change. Only `p PrerollCapture` and `p FastRender` change.

- **Auto-first Commit removed entirely.** The whole arming cluster (`pc_full/pc_fsel/
  pc_hcr/pc_hcinv/pc_fgate/pc_fpend/pc_fpf/pc_fbarr/pc_fbang/pc_fchk/pc_fclr/pc_fcs`)
  is gone. `p PrerollCapture` now responds only to `r ---prerollCapture`, which
  `rc_gate` fires on a **Record press while `---prerollFull`** (unchanged root wiring).
  Device is silent until Record.
- **Defer/retry latch removed.** No `gate 2`, no `pc_fpend` re-arm. A grab that would cross
  the ring seam is **clamped**: `start = max(end − sizeMs, 0)`, `renderMs = (end − start)/8`
  — Commit `[0, end]` (shorter that once, contiguous, valid). The `/PrerollCapture/` message
  cycle is gone → **28 cycles** (was 29; the remaining +1 vs the 27 baseline is the
  `/RollCapture/` bar-synced-arm latch).
- **Handover fixed.** `p FastRender` close step now also fires `report 20` → `snramp 16` →
  `ramp 16` to `s ---karmaMsg` (→ obj-20) right after `play`, matching the `---recordOn`
  reinit — so the chase overlay and the position/window displays come back.
- Untouched: the bar-locked substrate (`p RollCapture`), the groove~ bridge, the karma-A
  speed boost + record-source `selector~`s (`p Playback`), the `p Preroll` `pr_rec`
  retirement.

**Not fixed here:** the orphaned `---enableA/B/Keys` (A/B mutes). Separate piece — likely
folded into the "A/B = master vs ring" rework.

Verified: 1,883,883 / **28** cycles / 0 problems, size preserved.

**Expected on test** (v6_199_USEREDIT layout, no edit):
- Arm, transport running → the roll starts on the next bar; **nothing is audible**.
- SPD counts 0..33 and wraps; FRC shows the grab end climbing per bar.
- FUL LED lights one LoopLength after the roll starts.
- **Press Record** (any time after FUL, on or slightly off the beat) → one Commit: a real
  karma loop in `---thisBuffer`, PLY 1, **chase overlay + waveform + window displays live**,
  pads / reverse / reloop all working. A brief groove~ bridge covers the ~½-bar render.
- No dropouts, no periodic stop (there is no auto machinery left to misfire).
- If the master is silent: check the A/B mix dial is toward A.

Base for next edit: `ChopChop_v6_204.amxd`.

### v6_204 test (user) — handover OK; the render pass is empty + full-length (2026-09-04)

Decisive diagnostic: karma A **plays**, chase overlay **tracks**, PLY 1, SPD/FRC track.
But the committed loop is the **whole 120000 ms buffer, empty** (slices "super slow", audio
dies instantly). So the handover works — the **render pass itself** is the whole problem:

1. It recorded **silence**. The render source was `play~ ---rollBuf` (position-driven) piped
   `send~`/`receive~` -> `selector~` -> karma. The user's bench test that proved 8x render
   used **`groove~` (rate-driven) straight into karma**. (Mistake: I switched to `play~`
   purely to make a future wrapped-grab two-segment read easy — an edge case ~10% of the
   time — and traded away the verified mechanism. Reverted.)
2. The loop closed at the **buffer end** (`frames-1`) not `sizeMs`. karma's record head
   advances at the **speed-inlet rate**; v6_204 fed `obj-7 + 7` (a `+~` boost on an unknown
   base) which can exceed 8x and race the buffer end before `play` lands.

### v6_205 — Phase 5 file 4: groove~ render source + exact 8x + diags (2026-09-04)

`tools/phase3_file22_groove_render.py`. Base v6_204. Logic-only. `p Playback` +
`p FastRender` + one `p PrerollCapture` expr + a diag repoint.

- **Render source is now `gv2` `groove~ ---rollBuf 2`** (the verified pattern): loop points
  via `---gv2Lo`/`---gv2Hi` -> `gv2` inlets 1/2, then `set ---rollBuf` + `loop 1`, then a
  **float position** (= lo) into `gv2` inlet 0 to play. `gv2` audio -> `fr_recL/recR`
  `selector~` input 2 -> `obj-20[0]/[1]` (**direct patchcords**, no `send~`/`receive~`).
  `play~` / `send~ ---renderL~R` / `receive~` all removed.
- **karma-A speed during the render is EXACTLY `sig~ 8.`** via `fr_spd` `selector~ 2`
  (`[1]` = `obj-7`, `[2]` = `sig~ 8.`, ctl = `---renderActive + 1`). `gv2` rate is a matching
  `selector~` (`sig~ 0.` idle / `sig~ 8.` render). The `+~` boost is gone. So karma advances
  exactly 8x -> `play` at `renderMs` closes the loop at `renderMs*8 = end - start ~= sizeMs`.
- **`play` via `deferlow`** so karma processes `record` first (kills a same-tick race).
  `renderMs` floored: `pc_spanx` -> `expr ($f2-$f1<480.)?60.:(($f2-$f1)/8.)`.
- **Reinit fires before `record`** (report 20 / snramp 16 / ramp 16 -> `s ---karmaMsg`).
- **Diag repoint** (logic only): SPD `dg_spd_r` -> `r ---karmaRep4` (**karma loop END ms**:
  ~sizeMs = the render finally worked; ~120000 = still broken). FRC `dg_frc_r` ->
  `r ---frRenderMs` (the `renderMs` FastRender used).

New channels: `---gv2Msg ---gv2Lo ---gv2Hi ---frRenderMs`. Removed: `---renderL~ ---renderR~`.
Verified: 1,883,883 / **28** cycles / 0 problems, size preserved.

**Expected on test:** Arm (silent), FUL LED, press Record -> a committed loop whose length
(SPD field = `---karmaRep4`) reads ~`sizeMs` (a few thousand ms), NOT ~120000; real audio in
it; slices at the right rate; overlay tracks. FRC field shows `renderMs` (a few hundred ms).
If SPD still shows ~120000 or the loop is empty, those two numbers say where it broke.

Base for next edit: `ChopChop_v6_205.amxd`.

### v6_205 test (user) + v6_206 fix — broken expr ternaries (2026-09-04)

v6_205: instant playback but "insanely quick", overlay whizzing.  Diag: FRC
(`---frRenderMs`) = **0**; SPD (`---karmaRep4` = karma loop END ms) = static
**85.33 ms** (== 4096 samples == karma's minimum-loop clamp); cap/ful = 13714
(the intended 4-bar length -- so `---size` is fine).

-> `renderMs` reached FastRender as 0 -> `delay 0` -> `play` the same tick as
`record` -> karma's initial-loop `maxpos` ~= 0 -> loop clamped to 4096.

Root cause: the **arithmetic-in-condition `expr` ternaries** added in v6_204 /
v6_205 emit NOTHING in Max's `expr`, so `pc_pk`'s renderMs inlet kept its
default `0.`.  (v6_204's `pc_startx` ternary broke identically -> `start` stuck
at 0 -> `renderMs = end/8` -> often huge -> that build's whole-buffer loop.
The v6_202 `pc_swrap` ternary worked because it was single-var, no arithmetic
in the condition.)

### v6_206 -- Phase 5 file 5: expr fix (2026-09-04)

`tools/phase3_file23_expr_fix.py`.  Base v6_205.  Logic-only, two `expr` text
edits in `p PrerollCapture`, nothing else:

  pc_startx : ($f1-$f2<0.)?0.:($f1-$f2)         -> `expr max($f1-$f2,0.)`
  pc_spanx  : ($f2-$f1<480.)?60.:(($f2-$f1)/8.) -> `expr max(($f2-$f1)/8.,60.)`

  start    = max(end - sizeMs, 0)         (clamp a seam-crossing grab)
  renderMs = max((end - start) / 8, 60)   (>= 60; <= sizeMs/8 by construction)

Verified: 1,883,883 / **28** cycles / 0 problems, size preserved.

**Expected on test:** press Record -> **SPD (`---karmaRep4`) should read ~13712**
(the loop END ms -- NOT 85, NOT 120000), **FRC (`---frRenderMs`) ~1714**, real
audio in the loop, slices at a sane rate, overlay tracks normally.  If Record is
pressed soon after arm (fold small) the loop is shorter (only that much was
captured) but still valid.

Base for next edit: `ChopChop_v6_206.amxd`.

### v6_206 test (user) + course correction (2026-09-04)

v6_206 still gave an 85 ms loop (SPD `---karmaRep4` static 85.333, `---size` 3428
= 1 bar this run).  User: "you had this transfer working in the earlier build...
build from **203** -- it had a working fast render; the issue was not wiring it
into everything else, and the timer-driven auto-commit that killed it."  Also
noted (correctly) that the user had originally suggested deferring fast-render
and was talked out of it.

**On-disk diff confirmed the user is right:**
- **v6_203** `pc_rmsx = expr $f1/8.` (plain) -> `renderMs = sizeMs/8`, always.
  Sound.  v6_203's render mechanism = `play~ ---rollBuf` + `line~` position ramp
  + `+~` speed boost (obj-7 + 7).
- **v6_204** replaced the start calc with an **arithmetic-in-condition `expr`
  ternary** (`($f1-$f2<0.)?0.:($f1-$f2)`) -> emits nothing in Max -> `start`
  stuck at 0 -> `renderMs = end/8` -> often huge -> that build's whole-buffer
  loop.  v6_205/206 then rewrote the render source (groove~/selector~) chasing
  the wrong cause, and v6_205 added a *second* broken ternary (`pc_spanx`).

### v6_207 -- Phase 5 file 6: back to v6_204, expr fix only (2026-09-04)

`tools/phase3_file24_v204_expr_only.py`.  **Base v6_204** (drop the v6_205/206
groove~/selector~ rewrite).  v6_204 already is "v6_203 minus the auto-commit,
plus the handover reinit".  ONLY the two clamp exprs change -- exactly 2 leaf
boxes, no line changes, nothing else:

  pc_startx : ($f1-$f2<0.)?0.:($f1-$f2)  ->  `expr max($f1-$f2,0.)`
  pc_spanx  : ($f2-$f1)/8.               ->  `expr max(($f2-$f1)/8.,60.)`

  start    = max(end - sizeMs, 0)        (a seam-crossing grab -> [0, end])
  renderMs = max((end - start) / 8, 60)

Render mechanism is v6_203's, untouched: `play~ ---rollBuf` + `line~` position
ramp, `+~` boost (obj-7 + 7) for karma speed, record-source `selector~`s, the
`report 20`/`snramp 16`/`ramp 16` reinit after `play`.  Record-only Commit (no
auto-commit, no defer/retry latch).

Verified: 1,883,883 / **28** cycles / 0 problems, size preserved.

**Expected on test:** Record -> SPD (`---karmaRep4`) ~= `---size` (the loop END
ms; NOT 85, NOT 120000), FRC (`---frRenderMs`) ~= `---size`/8, real audio, sane
slices, overlay tracks.

Base for next edit: `ChopChop_v6_207.amxd`.

### Correction — v6_203's render WORKS; rebuild minimally from it (2026-09-04)

User re-tested `generated/ChopChop_v6_203.amxd` (byte-identical to their
Downloads copy, MD5 3c4a58e1): **"it has the full loop playing"** -- the
fast-render transcription is sound.  The failures were (a) the timer-driven
auto-commit thrashing it, and (b) a slight tempo error (loop length =
`renderMs * (obj-7 + 7)`, exact only when `obj-7 == 1`).  v6_204's from-scratch
`p PrerollCapture` rebuild + the broken clamp ternary sent me down a 3-build
detour (v6_205/206 groove~/selector~ rewrite -- all discarded).

### v6_208 -- Phase 5 file 7: v6_203 minus auto-commit, plus reinit (2026-09-04)

`tools/phase3_file25_v203_minus_autocommit.py`.  **Base v6_203.**  The minimal
change: strip ONLY the 12-box auto-commit cluster from `p PrerollCapture`
(`pc_full/pc_fsel/pc_hcr/pc_hcinv/pc_fgate/pc_fpend/pc_fpf/pc_fbarr/pc_fbang/
pc_fchk/pc_fclr/pc_fcs`) and every line touching it (incl. `pc_gate[1] ->
pc_fpend`, the defer arm).  Add the `report 20`/`snramp 16`/`ramp 16` reinit to
`p FastRender` off `fr_cl[2]` (chase-overlay wiring, matches the normal
`---recordOn` reinit).

**Everything else is v6_203 verbatim** -- `play~ ---rollBuf` + `line~` position
ramp render, the `+~` speed boost (obj-7 + 7), `renderMs = pc_rmsx = sizeMs/8`,
the wrap router.  Diff: `/p_prcap/` 40->28 boxes, `/p_fastrender/` 28->32.
Record (on FUL) is the only Commit; a would-wrap grab routes to `pc_gate`
outlet 1 -> nowhere (press Record again next bar).

Verified: 1,883,883 / **28** cycles (v6_203 was 29 -- the removed `pc_fpf`
latch) / 0 problems, size preserved.

**Expected on test:** Arm (silent), FUL LED, press Record ONCE -> the full loop
plays and keeps playing (no auto-commit to wreck it), chase overlay tracks,
pads / reverse / reloop work.  Tempo may still be slightly off -> that is
v6_209, isolated (make karma's record speed exactly 8, not obj-7 + 7).

Base for next edit: `ChopChop_v6_208.amxd`.

---

## ▶ CONTINUATION STATE (2026-09-04) — read this first on resume

**Base file:** `generated/ChopChop_v6_208.amxd` (1,883,883 bytes). Every build is a
**logic-only** edit on the user-relaid v6_199 layout — **never touch presentation / openrect /
box positions**. Builds must be testable with no editing (the user is firm on this).

**Workflow:** hand-edit the `.amxd` JSON via `tools/` (`ccamxd.py` load/save, `validate.py`
sweep — baseline was 27; **v6_204 = 28** message cycles / 0 problems / byte-size preserved,
the +1 is the bar-synced-arm latch loop). One build script per version in
`tools/phase3_fileNN_*.py`, model on the latest. Commit every save with
`git -c user.email="sisericm@gmail.com" -c user.name="Claude"`. Send the `.amxd` with
SendUserFile. Update this file's build log every version.

**Design reference:** the "Phase 5/6 design spec" section above is the agreed architecture —
rolling capture group (churn) → read-only master loop (karma, slice engine unchanged) →
voices+DSP (additive). Four write ops kept as separate vocabulary: **Roll** (auto, continuous)
· **Commit** (auto first, manual after; grabs one LoopLength off the ring, fast-renders into
karmaMaster at ~8×) · **Snapshot** (existing Freeze btn, → bufFreeze, clean/wet) · **Overdub**
(existing, karma-native). Roll cadence is fixed 1-bar, decoupled from master LoopLength. Two
gains: feedback (main mix → roll input, default 0) and commit crossfade.

**Built & awaiting user test — v6_204 (Record-only Commit + handover fix).** Full detail in
the build-log entry above. In short: the grab window is an **exact integer-bar** region from a
transport bar counter (`fold*barMs`) — kills the v6_202 "2 beats off". Arm starts the roll on
the next bar; **nothing is audible until the user presses Record.** Record (any time after the
FUL LED, on or slightly off the beat) → one Commit: `p FastRender` does a `play~`-at-8× read
of the ring into `karma ---thisBuffer` recording at speed 8, `play` closes it, then
`report 20`/`snramp 16`/`ramp 16` wake karma → a real bounded karma loop with a live chase
overlay, driven by the existing slice engine unchanged. Seam-crossing grabs are clamped to
`[0,end]` (no defer). The auto-first Commit and its retry latch are **gone** (they caused the
v6_203 dropouts + eventual stop).

**Test focus:** device silent until Record; then does the committed loop come out the right
length + on the bar; do pads / reverse / reloop / window / **chase overlay + waveform** work;
no dropouts / no periodic stop. If the master is silent → A/B mix dial toward A.

**Next (v6_205):** the wrapped-grab two-segment `play~` read (so a seam grab is full length,
not clamped); the A/B-as-master-vs-ring rework incl. wiring `---enableA/B` (the mutes are
dead in the base); Snapshot clean/wet split; feedback gain into the roll input. Then v6_206+
the `poly~` voice layer.

**Verification notes:**
1. karma record fidelity at 8× — **confirmed** viable from `karma~.c` + user bench test.
2. `record~` sync-outlet units — **moot**, dropped since v6_203.
3. `groove~` `loopstart > loopend` — bridge never wraps (`[max(0,start), end]`); render
   `play~` is position-driven, seam grabs clamped for now (two-segment = v6_205).
4. `phasor~ @lock 1` wrap vs audible-bar offset in Live 12 — still open. A residual fixed
   offset rotates the committed loop by that amount; not the v6_202 "2 beats" (that was the
   non-integer grab).
5. per-bar buffer-zero — N/A, v6_203 keeps the cheap `record~` ring (no karma passes in
   layer 1).

**karma~ is v1.0** (posts `64bit_v1.0stereo`). Messages: position/window/jump/stop/play/
record/append/set/overdub/report/ramp/snramp/snrcurv/interp ONLY. No loopstart/loopend/crop/
resize/sync. `groove~` DOES have `@loopstart`/`@loopend` (ms) + inlets 1/2 = loop min/max.
karma `set` on a foreign buffer = whole allocation. karma `record` from stop zeroes the whole
buffer. Speed inlet signal-preferential, value 0 = frozen. Source: `C:\Users\Brown\Downloads\
chopchop\karma1.0\karma~(win64)\karma~.c` + `karma~.maxhelp` + user's `maxpat samples/`.
