# ChopChop — Architecture Reference and Functionality Audit

**Base:** `ChopChop_v6_174.amxd`
**Supersedes:** `02_ChopChop_Project_Knowledge_Reference.md`, `12_ChopChop_Architecture_and_Requirements.md`, `13_ChopChop_Divergence_Audit.md` for anything covered below.

Everything here was read from the `.amxd` JSON of v6_174 or reproduced on the running device. Where a statement rests on observation rather than inspection it says so.

---

## 1. Build metrics

| | |
|---|---|
| Scopes / boxes / lines | 30 / 1413 / 1594 |
| Validator problems | 0 |
| Duplicate patchcords | 0 |
| Message cycles | **27** |
| File size | 1,705,180 bytes, preserved on every edit |

The cycle figure is **per-scope, patchline-only**: no send/receive edges, no subpatcher crossings. Any broader definition produces tens of thousands of cycles and is useless as a tripwire. Anything above 27 in a sweep is new and must be accounted for.

### Scope tree

```
/                                                    613 / 656
  p TempoTranslate                                    63 /  73
  p Audio Routing                                     22 /  26
  p (obj-147)                                         26 /  30
  p Playback                                         109 / 120
    p RollingB                                        23 /  28
    p TriggerPoisition                                38 /  47
      p Sequence_Recorder                             46 /  51
        p Seq_Messages                                38 /  43
      p detect_edge                                    5 /   4
      p speedtranslations                             38 /  62
      p reverseCompensation                           10 /  10
    p Recording                                       22 /  21
      p Record_And_Quantize                           12 /  15
        p detect_edge                                  5 /   4
      p RecordArming                                  18 /  14
      gen~                                            13 /  14
    p BufferSwitching                                  6 /   2
    p MessagesToKarma                                 41 /  49
    p INIT                                             7 /  10
    p glitching                                       45 /  52
      gen~                                            29 /  35
    p pitchMod                                         5 /   5
    p transport                                       11 /  11
  p SpeedControl                                      48 /  66
    p release_and_rounding                            17 /  21
  p GlitchControl                                     48 /  61
    p release_and_rounding                            22 /  28
  p soloAndMuting                                      9 /   8
    gen~                                              24 /  28
```

---

## 2. The scaling rule

This is the single most consequential piece of the device and it was undocumented. It has two stages and **no bar quantisation anywhere**.

**Stage 1 — requested length.** `LoopLength` (`obj-89 live.menu`) → `obj-88 + 1` gives bars. `p TempoTranslate` converts that to milliseconds against the tempo. The result is latched by `obj-2503 f`, banged by `r ---sliceEdge`, through `obj-2505 change` → `s ---size`.

**Consequence:** a length change never takes effect at the moment the menu is used. It waits for the next slice boundary. At one bar that is a quarter of a bar; at four bars it is a whole beat.

**Stage 2 — window.** At root:

```
w_fsize  f            ← ---size (hot), ---capturedMs and ---reloop (t b f), ---regrid
w_div    / 1.         size ÷ capturedMs
w_clip   split 0. 1.
w_mul    * 1.         × ---reloop  (w_frel f 1, default 1)
         → s ---windowVal → prepend window → s ---karmaMsg
```

So:

```
windowVal = clip(---size / ---capturedMs, 0, 1) × ---reloop
```

Three consequences follow directly, and between them they explain most of the historical confusion:

- **Whole bars are incidental.** Nothing enforces them. 3/4 gives 0.75 only because the menu offers whole bars and `---capturedMs` happens to be a whole number of bars. A capture that isn't lands on a fraction with no clean slice boundary.
- **`split 0. 1.` clips upward scaling.** Requesting more than the capture pins the ratio at 1, which is why lengthening past the captured length does nothing.
- **The region start is never set.** Only `window` is ever sent to karma~ — no `position`, no `jump` on the length-change path. karma~ therefore places the region itself, at the start of the capture. **The loop is always the first `n` slices**, where `n = windowVal × 16`.

### The bar 1–2 commit rule

Because the region is fixed at 1…n, committing a shortening while the playhead is past slice `n` leaves it outside the new region and karma~ pulls it back to the start — an audible break.

This is **documented behaviour, not a defect.** The safe window is "you are already inside the new length": 4→3 only breaks from bar 4, 4→1 breaks from anywhere past bar 1. The region overlay already displays this — if the playhead marker sits outside the lit region, committing will jump.

Two attempts to remove the constraint were built and reverted, both instructive:

- **Jump to the current slice on commit** (v6_170). Reading the playhead and feeding it back into playback closes a loop through karma~'s report — commit changes the window, window changes the report, report causes the commit. Cycle count rose 27→30 and it produced a stack overflow on the device.
- **Defer the commit until the playhead is back in bounds** (v6_171/172). Gating `r ---sliceEdge → obj-2503` defers `---size`, which the playhead display chain depends on, so the overlay desynchronised and stuck.

Both routes are closed. Any future attempt must leave `---size` and the report loop untouched.

---

## 3. Playhead overlay

The one consistently solid display mechanism in the device.

```
p Playback outlet 2  (= unpack outlet 0, report element 0)
  → obj-2603 gate 2 1               control = ---reloopMode + 1
      outlet 1 (Reloop)  ─────────────────────────────┐
      outlet 0 (Scaled) → obj-2604 − 0.               │  ← ---regionStart (cold)
                        → obj-2606 split 0. 1.        │  out of range → obj-2607 + 1.
                        → obj-2608 / 1.               │  ← ---windowVal via obj-4301 f,
                                                      │    refreshed on ---sliceEdge
  → ov_1000 * 16. → ov_1001 int → ov_1002 minimum 15
  → ov_1003 maximum 0 → ov_1004 change → ov_1005 t i b
       outlet 1 (fires first) → ov_hideall → all 32 panels
       outlet 0 → ov_1007 route 0…15 → ov_show_i → overlay_slice_i and padtint_i
```

`ov_show_*` drives the waveform overlay panels **and** the pad tints from the same message, so the two displays are one mechanism.

**Do not remove the `− ---regionStart` subtraction.** It was removed in v6_149 on the strength of the coordinate skill file and produced progressive drift, a stuck chase and unresponsive clicks. Whatever the report's exact coordinate space, that subtraction is doing real work.

`minimum 15` / `maximum 0` clamp the index to 0–15. **An index pinned at 15 means the input left its range**, not that the display is stuck — historically the single most misdiagnosed symptom in this device.

---

## 4. Region overlay

Added this session. Independent of the playhead chain by construction: it has its own panels and its own trigger, and it adds **no cords at all** to `ov_1000`–`ov_1007`, `ov_show_*` or `ov_hideall`.

### Panels

32 new `panel` objects, presentation rects copied byte-for-byte from their playhead twins, inserted at array index 86:

```
padtint_* 54–69 | overlay_slice_* 70–85 | ovr_*reg_* 86–117 | waveform~ 169,200 | pad_trigger_* 208+
```

Earlier index draws in front, so one insertion point puts the region behind both playhead banks and in front of the waveform and the buttons. `ov_hideall` never reaches them.

### Extent

```
s = 0                                    in Scaled  (ovr_szero, gated off in Reloop)
s = struck pad index                     in Reloop  (ovr_phg ← ---padHitRaw)
n = clamp(int(---windowVal × 16 + 0.999), 1, 16)
lit when ((i − s + 16) % 16) < n
```

`n` is driven by `ovr_wv r ---windowVal` through `* 16. → + 0.999 → int → maximum 1 → minimum 16 → ovr_nchg change → ovr_nt t b i i`.

### Trigger and firing order

`ovr_fire3 t b b b`, right to left:

| Outlet | Action |
|---|---|
| 2 | `ovr_clear` → all 32 region panels to alpha 0 |
| 1 | `ovr_zg` gate (closed in Reloop via `ovr_zinv !- 1`) → `ovr_szero` → `s = 0` |
| 0 | `ovr_uzi uzi 16 1` → the per-slice test |

Recompute sources: `ovr_nt[0]` (length change), `ovr_rlmt[0]` (mode change), `ovr_phg` (Reloop strike). Nothing else — the region does not repaint per slice edge.

Per-slice test: `uzi 16 1` index off **outlet 2** → `− 1` → `t i i` → `(i − s + 16) % 16` → `< n` → `pack 0 0` → `route 0…15` → `sel 1` → pad message direct, waveform message via `ovr_wgate_i` gated on `---reloopMode`.

### Mode split

| | Waveform | Pad grid |
|---|---|---|
| Reloop | region shown | region shown |
| Scaled | not shown | region shown |

This follows from the display-range rule in §5: in Reloop the whole capture is in view, so a highlight showing where the section sits is meaningful. In Scaled the waveform *is* the section, so only the pads carry it, as a reminder of where the section came from.

### Colours

| Element | Value | Alpha |
|---|---|---|
| Playhead, both banks | `0.35 0.82 0.78` aqua | 0.70 |
| Region, waveform | `0.62 0.3 0.85` violet | 0.45 |
| Region, pads | `0.62 0.3 0.85` violet | 0.60 |

The original orange `1. 0.6 0.2` @ 0.35 sat a few degrees from the olive waveform trace (`0.627 0.631 0.231`), so it competed with the signal, and at low alpha over near-black it desaturated to brown. Aqua is complementary to the trace; violet is distinct from both and from the slate grid (`0.306 0.475 0.612`). A slate region was tried and disappeared into `obj-85`'s own background, which is the same hue.

`padtint_*` have `shape: 1` — circles. `overlay_slice_*` are rectangles.

---

## 5. Waveform display range

```
obj-79 r ---size → obj-77 deferlow → obj-121 t b i → obj-126 f
obj-126 → obj-2009 gate 2 1              control = ---reloopMode + 1 (obj-2006/2007/2008)
    outlet 0 (Scaled) → obj-4501 t f f
    outlet 1 (Reloop) → wf_tb t b → wf_fcap f ← r ---capturedMs → obj-4501
obj-4501 → obj-4502 gate 2 1             control = ---hasContent + 1
    outlet 1 → obj-136 minimum 120000 ← r ---capturedMs
    outlet 0 → obj-92 * 0.5
obj-92 → obj-135 t f 0 f f → obj-67 and obj-85 waveform~ inlets 0 and 1
```

Two `waveform~` objects split the display, each showing half the span — hence the `* 0.5`.

**Rule:** Reloop shows what was captured (four bars captured, four bars in view). Scaled redraws to the looping section only.

Before v6_174 the Reloop branch substituted a literal `1000000`, which the clamp and halve turned into a fixed 60,000 ms span regardless of the capture. `obj-2010` is left in place, orphaned, so reverting is two cords.

---

## 6. Voice and buffer inventory

| Object | Buffer | Inlets fed | Outlets used |
|---|---|---|---|
| `obj-20` | `---thisBuffer` 120,000 ms | 0, 1, 2 | 0, 1, 2 |
| `karmaB` | `---bufB` 20,000 ms | 0, 1, 2 | **none** |
| `karmaKeys` | `---bufFreeze` 20,000 ms | 0, 2 | **none** |

Buffers: `---dummy` 200, `---thisBuffer` 120000, `---bufB` 20000, `---bufFreeze` 20000, all stereo.

Multi-voice is far more built than the roadmap implies:

- **Message fan-out exists.** `kmsg_gate` → `gA` / `gB` / `gK`, one gate per voice.
- **Per-voice enables have no senders.** `---enableA`, `---enableB`, `---enableKeys` are received but never sent. All three gates are `gate 1 1`, open by default, so every message reaches all three instances.
- **karmaB receives the stereo device input**; `karmaKeys` receives none, only the speed signal on its rightmost inlet.
- **Speed:** karmaB is hard-wired to its own `sig~ 1`; karmaKeys shares karma A's speed signal.
- **Neither B nor Keys has any output connection.** This is the actual blocker.
- **`---bufB` and `---bufFreeze` are 20,000 ms** against A's 120,000. Any capture over 20 s wraps.
- **`AB_MIX` live.dial → `s ---abMix` has no receiver.** The crossfade control is built and unattached.

`p RollingB` is a complete realign engine — `phasor~ @frequency 1n @lock 1` → `delta~`/`edge~` → `onebang` → record / overdub 0 / play, delay driven by `---size` — whose output reaches karmaB's message inlet. Its trigger `---bRealign` has no sender and the `---bAudible` it emits has no receiver. Built and orphaned at both ends.

---

## 7. Channel audit

73 send/receive channels. Orphans:

**Sent, never received** — dead ends, each one a feature that stops short of its consumer:

| Channel | From | Note |
|---|---|---|
| `---abMix` | root | A/B crossfade dial, nowhere to go |
| `---bAudible` | p RollingB | realign engine's output flag |
| `---karmaPlaying` | p Playback | report element 1 |
| `---karmaRecording` | p Playback | report element 2 |
| `---loopEndMs` | p Playback | report element 4 |
| `---SequenceStatus` | p Sequence_Recorder | no sequencer state feedback anywhere |
| `---overdubAmount` | root | |
| `---reverseMode` | root | `---effectiveReverse` is the live one |
| `glitchDisplay` | p GlitchControl | |
| `pitchDisplay` | p Playback | |

**Received, never sent** — receivers waiting on a source that does not exist:

| Channel | In | Note |
|---|---|---|
| `---enableA` / `---enableB` / `---enableKeys` | p Playback | the multi-voice switch |
| `---directJump` | p Playback | |
| `---speedControls` | p TriggerPoisition | speed dial unwired |
| `---toggleValue` / `---ToggleValue` | p glitching, SpeedControl, GlitchControl | note the case difference — two distinct channels, neither driven |
| `---overdubCount` | p MessagesToKarma | |
| `---solosAndMutes` | p soloAndMuting | |
| `GlobalLength` / `GlobalOff` / `globalRecQuantize` | root | Push-era leftovers |

**Naming fault:** `---sliceLengthMs` is **not** a slice length. It is fed from `karma_window_cache`, which is report element 5 — karma~'s window in milliseconds. Anyone reaching for a slice count finds this name first and gets the wrong quantity.

---

## 8. Functionality audit

### Working

- Capture, playback, 16-slice pad triggering, mouse triggering on the waveform and the pad grid
- Loop length scaling by the rule in §2, within the bar 1–2 commit constraint
- Reloop mode: division palette `rl_0`–`rl_4`, jump-based region relocation, region overlay following the struck pad
- Playhead overlay on waveform and pads, both modes
- Region overlay on pads in both modes, on the waveform in Reloop
- Waveform display range switching correctly between capture and section
- Full and soft INIT, `---regrid`, `---hasContent` gating of the `capturedMs` display clamp
- Overdub, freeze toggle, solo/mute, input routing, record quantise

### Partial

- **Sequencer.** `seq~ overdub-enable-flag 1` records `---padHitRaw` prepended `padhit`, gated by `---seqFaithEngine`. Transport on `---PatternRecordDirect` / `---PatternRecordBang` through `gate 2`. `p Seq_Messages` does the length maths from `---size` with a reverse-compensation term. No state feedback (`---SequenceStatus` orphaned). Three objects in that scope are unconnected: a bare `toggle`, `r ---PatternRecordOn`, `revsel_split t i i`. Specific usability faults not yet characterised.
- **Reverse.** `---effectiveReverse` is live and drives `p Seq_Messages`. Momentary reverse needs a momentary MIDI source. The region overlay does **not** account for direction — the window is always drawn ahead of the playhead; under reverse it should extend behind, which is a `gate 2` on `---effectiveReverse` selecting `i − s` or `s − i` into the modulo.

### Absent

- Multi-voice audio output (§6)
- A/B mix
- Speed and stutter dials (`p SpeedControl` and `p GlitchControl` expect relative encoder deltas, not absolute dial values; deliberately unwired)
- Ableton clip and MIDI integration
- Upward scaling past the capture (§2, and see roadmap)
- Bounce and freeze as committed operations

---

## 9. Things that look like faults and are not

- **The bar 1–2 commit rule** (§2). Performance discipline, visible on screen.
- **An overlay index pinned at pad 16.** The clamp doing its job; the input has left range.
- **`gate 1 1`** — one outlet, open by default. All three voice gates are open, so messages already fan out to all three karma~ instances.
- **`uzi` index is on outlet 2.** Outlets are `['bang','bang','int']`. The working reference in `p TempoTranslate` (`uzi 64 1`) drives from outlet 2.
- **`live.button` always outputs a bang**, never a numeric. `sel 1` filters silently discard every press.
- **`route` will not match a force-converted float against integer arguments.** Use `t i b`, not `t f b`.
- **`change` cannot process symbols.** `---recordOn` sends a symbol.
