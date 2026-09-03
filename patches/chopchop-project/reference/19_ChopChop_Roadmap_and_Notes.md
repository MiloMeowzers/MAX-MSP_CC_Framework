# ChopChop — Roadmap, Architectural, Process and Design Notes

**Companion to** `18_ChopChop_v6_174_Architecture_and_Audit.md`. That document says what the device is; this one says what to do next and how to avoid the failures that produced it.

---

## Part A — Roadmap

Ordered. Reordering is allowed; doing it silently is not.

### A1. Multi-voice audio path

The largest gap and the smallest amount of new work relative to its value, because most of it is already built (§6 of the audit).

1. Connect `karmaB` and `karmaKeys` outputs into the mix stage. This is the actual blocker — everything upstream already runs.
2. Land `---abMix`. The dial exists and sends; nothing receives.
3. Give `---enableA` / `---enableB` / `---enableKeys` senders so the per-voice gates can close. Until then all three instances receive every message.
4. Resize `---bufB` and `---bufFreeze` from 20,000 ms. Anything over 20 s currently wraps. **Buffer declarations are order-sensitive in the `boxes` array** — deliver this as its own file.
5. Decide whether `karmaKeys` takes the device input or a tap off A. It currently receives no audio at all.
6. Attach `p RollingB`: `---bRealign` needs a sender, `---bAudible` needs a receiver.

**Deliver as separate sequential files.** Step 1 alone is testable: B becomes audible.

### A2. Sequencer usability

Blocked on characterisation. The mechanism is built and the length maths is in place; what is unusable in practice has not been established. Two things are visible from the file and worth doing regardless:

- `---SequenceStatus` is sent and never received. There is no feedback for empty / armed / recording / playing.
- Three unconnected objects in `p Sequence_Recorder`: a bare `toggle`, `r ---PatternRecordOn`, `revsel_split t i i`.

Storing the sequence as MIDI events rather than internal messages is a prerequisite for A4, not a parallel task.

### A3. Region overlay under reverse

The window is always drawn ahead of the playhead. Under reverse the loop lies behind it, so a persistent offset appears once direction changes. Fix is a `gate 2` on `---effectiveReverse` selecting `i − s` or `s − i` into the modulo — two objects, touches nothing else.

### A4. Ableton clip and MIDI integration

Core requirement, not a stretch goal, and absent from the working set for several sessions. Pad hits as real MIDI notes on a standard Ableton track; audio as clips via `ClipSlot.create_audio_clip` with shared markers for 16 clips from one master file. Depends on the sequencer storing MIDI events (A2).

### A5. Speed and stutter

Entirely unwired and the largest functional gap in the visible UI. `p SpeedControl` and `p GlitchControl` expect **relative encoder deltas, not absolute dial values**, which is why the dials are deliberately disconnected. Either adapt the subpatchers to absolute input or bind the dials to an encoder source.

### A6. Momentary reverse and Reloop as a momentary layer

Structure is correct; both need a momentary MIDI source. The settled design is Reloop as a momentary layer over Scaled. `record_arm_toggle` must be returned to its reserved purpose (preroll) if it is still standing in.

### A7. Upward scaling, bounce, freeze

Not a defect and no small fix. `window` cannot exceed 1, the buffer is not the constraint, `append` needs a live record pass, and `overdub` does not grow the loop. It is a consequence of the bounce and multi-voice work, and follows A1.

### A8. Two open display items

- Slice rescaling on resize: below captured length the 16 pads loop over a subset rather than spanning the shorter loop. Related to, but not the same as, the region layer.
- Probes `K_1`–`K_7` in the reserved presentation strip at x 1130 must be removed before shipping.

---

## Part B — Architectural notes

### B1. Never feed a value derived from karma~'s report back into playback

The report is live at the `report 20` rate. Anything that reads it and causes a playback change closes a loop: commit changes the window, window changes the report, report causes the commit. v6_170 did exactly this and produced a stack overflow on the device, with the cycle sweep rising 27→30 beforehand as the warning.

A cold inlet is **not** protection. The loop does not need the reading object to re-fire; it only needs the chain to close.

**Test:** if the cycle sweep exceeds 27, stop. That is what it is for.

### B2. Never defer `---size`

`---size` feeds the playhead display chain as well as the window calculation. Gating `r ---sliceEdge → obj-2503` in `p TempoTranslate` to defer a commit desynchronises the playhead overlay and makes it stick (v6_171/172).

Between B1 and B2, both routes to removing the bar 1–2 commit constraint are closed. Treat the constraint as designed behaviour.

### B3. Prefer values the device owns over values read back

Every quantity the region layer eventually needed already existed: the slice index at `ov_1005`, the window at `---windowVal`, the jump target on the Reloop path. Five separate derivations of a "region start" from karma~ were built and all five were wrong. The correct answer was that karma~ places the region itself and the device never needed the value.

Before deriving a quantity, check whether the device already emits it, and whether it needs to exist at all.

### B4. Additive layers over shared mechanisms

The region overlay works because it has its own 32 panels and its own trigger and adds no cords to the playhead chain. The first attempt shared `ov_1005`'s trigger and the playhead's panels, and a fault in the new code reached the old — including muted audio and unresponsive pads from a purely additive display build.

When adding a display layer: own panels, own trigger, assert that no cord touches the existing chain.

### B5. Z-order is one insertion point

`padtint_*` 54–69, `overlay_slice_*` 70–85, `waveform~` and `pad_trigger_*` far later. Inserting at index 86 puts a new bank behind both playhead banks and in front of the waveform and buttons, for both displays at once. Earlier index draws in front.

### B6. Trigger ordering must be structural, not incidental

Where two values must arrive in a fixed order, put them on outlets of one `trigger` rather than on two receives of the same send. `ovr_nt t b i i` stores `n`, sets the gate, then fires — deterministic. Two separate `r ---windowVal` objects would not be.

Corollary: a send that fires more than once around one event will re-trigger anything hanging on it. `---windowVal` is emitted several times around a single resize because `w_fsize` is banged from four sources.

---

## Part C — Process notes

These are not general advice. Each one exists because ignoring it cost at least one build this session.

### C1. The reference documents outrank the skill files

The skill files and the project reference disagree in at least three places, and each disagreement cost a build:

| Question | Skill file | Project reference | Reality |
|---|---|---|---|
| Report element 0 coordinate | region-relative, starts at 0 | position 0.–1. | subtraction of `---regionStart` is load-bearing; removing it caused drift |
| Report element 3 | unidentified, reads 0.00 | start-position (ms) | reads 0.00 in practice; not usable |
| Does karma~ report the region start | no | element 3 | it places the region itself; the question was moot |

Also: the `0.875 → 0.4375` measurement in `karma-loop-semantics` does not describe `pos × window`. Building on it produced a uniform 8–10 slice error.

**Read the project reference documents first.** Whichever document is read first determines the design, and the skill files are the less reliable of the two.

### C2. Revert after two bad builds; do not attempt a third

Applied twice this session and correct both times. 162 and 163 both made things worse and the revert to 160 was the right call; 171 and 172 likewise, reverting to 169.

Every time this was violated, the next build was layered on a broken one and the symptom moved rather than resolved.

### C3. One variable per file; sequential files for multi-part work

v6_166 changed the chase branch and the region freeze together. It regressed, and the audio lag it introduced could not be attributed to either half.

### C4. Do not ship superseded builds

If build N+1 contains build N and supersedes it, ship only N+1. Shipping both wastes the reviewer's time and invites testing the wrong file.

### C5. Do not re-post a file the user already has

Reverting to a previous build means saying so. It does not mean re-delivering the file or writing a summary of the revert.

### C6. Symptom arithmetic is evidence, and it can mislead

"Off by 4 at n=12, off by 8 at n=8" fitted `16 − n` exactly and produced a confident, wrong diagnosis on two data points. The third case did not fit and was rationalised away. Two points fitting a rule is not a rule.

When a mechanism is proposed, state what the fix should change and by how much, so the next test falsifies it rather than just failing.

### C7. Say when static analysis has run out

Several failures in this session were presented as diagnoses when they were hypotheses. "This needs a measurement" is cheaper than a confident wrong answer, and a single observation from the running device settled questions that five builds could not.

---

## Part D — Delivery checklist

Run before every `.amxd` edit is delivered.

- [ ] Every patchline source and destination id exists in that subpatcher's boxes, recursively
- [ ] No duplicate varnames or ids introduced
- [ ] Duplicate-patchcord sweep across every scope → 0
- [ ] Message-cycle sweep, per-scope patchline-only → **27**, not zero
- [ ] Any comparison to a reference file was scope-aware
- [ ] Every object property used — name, inlet semantics, outlet indices, message arguments, coordinate system — is confirmed in the audit, a reference file, or a working instance in this same patcher
- [ ] File size exactly 1,705,180
- [ ] Added visible elements: correct array index for z-order, presentation rects checked against their twins, patching rects overlap-asserted against every existing box and every other new box
- [ ] The build script asserts the existing chain is untouched where it should be — `old_cords ⊆ new_cords`, and the set of new cords touching named existing objects is exactly what was intended
- [ ] Anything speculative is flagged as such, with the exact cords to remove
- [ ] One variable, or delivered as separate sequential files

**Revert note.** The base already contains a box with id `ovr_amt_read` (`r ---overdubToggle`). "Delete every box whose id starts with `ovr_`" would take it too. The region layer is the ids added after v6_155.

---

## Part E — Design notes

### E1. Palette

| Role | Value | Alpha |
|---|---|---|
| Device background | `0.198 0.188 0.202` | |
| Module panels | `0.078 0.075 0.075` | 0.84–0.9 |
| Waveform strip panel | `0.239 0.255 0.278` | |
| Waveform trace | `0.627 0.631 0.231` olive | |
| Grid | `0.306 0.475 0.612` slate | 0.15 |
| Reflection | `0.32 0.70 0.537` green | 0.29 |
| Selection | `0.447 0.051 0.518` violet | 0.11 |
| **Playhead** | `0.35 0.82 0.78` aqua | 0.70 |
| **Region, waveform** | `0.62 0.3 0.85` violet | 0.45 |
| **Region, pads** | `0.62 0.3 0.85` violet | 0.60 |

The scheme is cool throughout — slate, green, violet — against a warm olive trace. A warm accent competes with the signal and desaturates to brown at low alpha over near-black. Overlay hues should be complementary to the trace, not adjacent to it.

Pads sit on plain near-black with nothing beneath, so they need higher alpha than the waveform for the same legibility. A tint at 0.45 that reads clearly over the waveform reads as dull grey over a black button.

Do not pick a region hue that matches a background already in use: a slate region was tried and vanished into `obj-85`'s own slate background.

### E2. Placement

- Presentation additions go in a reserved strip beyond the content extent, never squeezed into apparent gaps
- Patching position adjacent to what the object probes, where free space allows; assert overlap rather than eyeballing it
- `flonum` not `number` for normalised values; `parameter_enable: 0` on diagnostics
- Probes must be in **presentation mode** to be read against device behaviour — the Max patcher window is not a substitute for panel overlays and tints
- Probe boxes must be wide enough: a 62 px box truncated `119999.98` to `11999.98` and nearly produced a wrong conclusion

### E3. What the display should tell the performer

The region overlay is not decoration. It carries the one piece of state the performer cannot otherwise see: whether committing a length change now will be seamless or will jump. If the playhead marker is outside the lit region, the change will pull back to the start.

Design new indicators against that standard — state the performer needs and cannot infer — rather than adding restatements of what the audio already conveys.
