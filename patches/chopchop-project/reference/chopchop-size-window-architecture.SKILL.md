---
name: chopchop-size-window-architecture
description: The size, window, INIT and buffer-guard architecture of ChopChop, current to v6_174 — how ---size, ---capturedMs, ---reloop and the window calculation fit together, what the full/soft INIT chains do, how the reduction guard works, and which sends carry what. Use before touching loop length, tempo handling, the waveform display, the INIT buttons, or anything that sends messages to karma~ in this device.
---

# ChopChop — size, window and INIT architecture

**Revision 2, current to `ChopChop_v6_174.amxd`.** The core expression is unchanged from
v6_127 and was re-traced through `w_fsize → w_div → w_clip → w_mul → s ---windowVal`. What is
new is §1a, which records what the expression implies at the device level, and corrections in
§6 and §8. See `18_ChopChop_v6_174_Architecture_and_Audit.md` for the full picture.

Supersedes any earlier description of loop-length handling. The device no longer changes loop
length by re-recording; it captures once and windows down.

---

## 1. The one expression everything rests on

```
window = clip( ---size / ---capturedMs , 0..1 ) × ---reloop
```

| Send | Meaning | Source |
|---|---|---|
| `---size` | length you **want**, ms, after the reduction guard | TempoTranslate |
| `---capturedMs` | length you **captured**, ms | `---size` latched when `---hasContent` goes to 1 |
| `---reloop` | beat-repeat ratio, default 1 | reloop palette |
| `---karmaMsg` | every message bound for karma~ | root → `p Playback` |

Because `---capturedMs` is a latch of `---size`, **the window calculation depends on nothing
karma~ reports**. That remains the right design, though the original reason for it was wrong:
reporting is not unreliable, and the historical failures were probe faults (see
`karma-loop-semantics` §8). The good reason is stronger — a value the device owns cannot be
fed back into playback and close a loop, which is what stack-overflowed v6_170.

Behaviour that falls out of it:

- After a capture, `---size == ---capturedMs`, so window is 1
- Reduce loop length → ratio drops → playback shrinks live, no stop, no re-record
- Request more than was captured → ratio exceeds 1 → pinned to 1. Growing needs a new capture
  or `append`
- Before any capture, the divider's `1.` argument makes the ratio large, so it pins at 1. No
  divide-by-zero guard is needed

### What the expression implies, at the device

Only `window` is ever sent to karma~ on the length-change path — no `position`, no `jump`.
karma~ therefore places the region itself, **at the start of the capture**.

**The loop is always the first `n` slices**, `n = window × 16`. On a 4-bar capture: 3 bars
lights 1–12 and drops 13–16; 2 bars lights 1–8; 1 bar lights 1–4. Only the entry point moves
with where the playhead was. Traced live from four different commit slices; all four played the
same twelve slices at a 3-bar window.

Two consequences that are not obvious from the formula:

- **There is no region start to compute.** Five separate derivations of one were built and all
  five were wrong, because the quantity had no effect on where karma~ actually put the region.
- **A shortening committed while the playhead is past slice `n` will jump**, because the
  playhead is outside the new region and karma~ pulls it back to the start. The safe window is
  "already inside the new length": lengthening is always safe, 4→3 breaks only from bar 4,
  4→1 breaks from anywhere past bar 1. This is designed behaviour, surfaced in the UI by the
  region overlay — if the playhead marker sits outside the lit region, committing will jump.
  Both routes out of it are closed; see `karma-loop-semantics` §8a.

### The commit is never immediate

`obj-2503 f` in `p TempoTranslate` is banged by `r ---sliceEdge`, so `---size` — and therefore
`---windowVal` and the `window` message — only move on the next slice boundary. A quarter of a
bar at 1 bar, a whole beat at 4 bars. Nothing downstream can be made to happen at the gesture.

`---windowVal` is also emitted **more than once** around a single resize, because `w_fsize` is
banged from four sources. Anything hanging on it that must fire once needs a `change` guard.

### Whole bars are incidental

Nothing enforces them. The ratios are clean only because the menu offers whole bars and
`---capturedMs` happens to be a whole number of bars. A capture that isn't lands on a fraction
with no clean slice boundary.

---

## 2. `---size` and the reduction guard, in `p TempoTranslate`

```
---size = bars × multiplier × (GlobalLength / 4) × barMs
```

`bars` is LoopLength (menu index + 1, range 1–8). `multiplier` is `Trigger[18]`, range 1–8.
`barMs` is `240000 / tempo` — four beats of 4/4. So the multiplier is a **bar count
multiplier**, not a meter setting: 1×3 means three 4/4 bars, twelve beats. Total range is
64:1, from 1 bar to 64 bars.

### The `f 1` on the LoopLength path

The bars value passes through an `f 1` before the first `* 1.`. This exists because tempo
changes only ever *bang* that multiply, and TempoTranslate has its own `live.thisdevice`
driving the tempo observer, independent of the root trigger that bangs the LoopLength menu —
their order is undefined. Without the `f`, a tempo change could not recompute at all, and the
`f` holding 0 at load would give `---size` of zero. The argument makes the worst case one bar.

`r ---regrid` also bangs this `f`, which is how Re-Grid forces a recompute.

### The reduction guard

64 bars at 120 bpm is 128 seconds. Recording past the buffer end wraps and corrupts rather
than failing, so the length must be reduced *before* the pass starts.

```
B = ---size / barMs                          requested bars
C = (---bufferMs × 0.98) / barMs             capacity in bars, 2% margin for ramp/snramp
d = largest divisor of B that is ≤ C
---size = d × barMs
```

Implemented as `uzi 64 1` walking every candidate, with `%` → `== 0` testing divisibility and
`<=` testing fit. Both produce 0/1 and are combined by **multiplication**, so no `&&` object
and no `expr` escaping is involved. `zl group 64 → zl sort → zl slice 63` takes the largest
survivor.

Divisor rather than floor: 64 into 40 gives **32**, not 40. A shorter loop that divides the
intended phrase stays in time; an arbitrary shorter loop drifts against it forever.

**A cycle bug to remember:** the object holding B fed both `uzi` and the modulo, and the
per-iteration trigger banged it — so every one of the 64 steps restarted the whole walk.
Stack overflow, outlets disabled. The fix was a second `i` object holding a loop-local copy of
B, leaving `uzi` with exactly one trigger source outside the iteration. Sweep every scope for
message cycles after any build that adds a `uzi`.

---

## 3. Buffer allocation

`buffer~ ---thisBuffer 120000 2` in `p Playback/p BufferSwitching`, about 42 MB stereo, with
`loadmess 120000 → s ---bufferMs` at root feeding the guard.

Fixed, not selectable. `size` and `sizeinsamps` both fail with "can't resize now" while a
karma~ is attached, and a M4L device always has DSP running, so there is no window in the load
sequence where a resize would be accepted. A BufferSize `live.menu` was built and removed for
this reason.

120 s covers everything except 8×8 below roughly 128 bpm, which the guard handles. Changing it
is a one-word edit in `BufferSwitching`, plus the matching `loadmess`.

`---bufB` and `---bufFreeze` remain at 20000. Neither karma~ has an output connected.

---

## 4. Messages to karma~

Every message reaches `karma~ ---thisBuffer 2` through **one** route:

```
root:  s ---karmaMsg  →  p Playback:  r ---karmaMsg  →  karma~ leftmost inlet
```

Both the INIT chains and the window calculation use it. `p INIT` and `p MessagesToKarma`
remain separate legacy routes into the same inlet.

`loadmess report 150` also sits in `p Playback` feeding that inlet. It is the only
configuration under which reporting ever produced a value, and reporting is not relied upon.

---

## 5. INIT chains

**Full INIT** — `t b b b b b b b b b b b`, fired by the full_INIT button and by
`r RE_INIT → deferlow`. `RE_INIT` hangs off outlet 1 of the root `live.thisdevice` trigger,
which is the correct load anchor: `loadbang` fires before Live restores parameters, which is
why the device used to need "wake-up clicks" before Record and Reverse responded. The
`deferlow` pushes the chain behind the rest of the load fan-out, including the waveform's
buffer binding on outlet 0.

Outlets fire right to left:

| Outlet | Sends |
|---|---|
| 10 | `report 20` → `---karmaMsg` |
| 9 | `stop` → `---karmaMsg` |
| 8 | `window 1` → `---karmaMsg` |
| 7 | `position 0` → `---karmaMsg` |
| 6–3 | `0` into Pattern Rec, Overdub, Back-Forth, Reverse |
| 2 | `1` into Trigger |
| 1 | `0` into LoopLength |
| 0 | bangs the soft INIT trigger |

**Soft INIT** — `t b b b b`, fired by the Reset button and by full INIT outlet 0:

| Outlet | Sends |
|---|---|
| 3 | `s ---bufClear` → `[clear(` → `buffer~ ---thisBuffer` |
| 2 | `s ---eraseSeqButton` → `[clear all(` → `seq~` |
| 1 | `0` → `s ---hasContent` |
| 0 | `s ---regrid` |

Regrid last, so the display redraws against the reset state.

**Explicit values, not bangs.** Every toggle gets a literal `0` rather than a bang, because a
number into a `live.toggle` sets *and* outputs, which drives the engine as well as the UI. The
device's own `rec_reset_msg` uses `set 0` specifically to update a toggle *without* output,
which is the evidence that a bare `0` does output.

**A failure mode worth remembering:** full INIT outlet 0 originally fed an empty message box
into a `live.button`, which lights the button and stops. The soft INIT trigger's only input
was that button's *outlet*. Every send had a receiver and every message box had text, so all
existence checks passed — but the chain terminated in the wrong object. **Trace chains to
their terminus, not to their first destination.**

---

## 6. Waveform display

`r ---size → deferlow → t b i → obj-126 f → obj-2009 gate 2 1 → obj-4501 → obj-4502 gate 2 1 →`
`minimum 120000` or `* 0.5` → `obj-135 t f 0 f f` → both `waveform~` objects. The `* 0.5` is
because the display is two rows of 8 slices, each showing half the loop.

**`obj-2009` switches the span on `---reloopMode`, and this is a rule, not an implementation
detail:**

- **Reloop shows what was captured.** Four bars captured, four bars in view; three captured,
  three in view. Slices stay fixed under the pads, so the same waveform is always in view.
- **Scaled shows only the looping section.** The pads subdivide that section into 16, so the
  slices under them get smaller as the loop shortens.

Until v6_174 the Reloop branch substituted a literal `1000000`, which the `minimum 120000`
clamp and the `* 0.5` turned into a fixed 60,000 ms span regardless of the capture. `obj-2010`
still holds that constant, orphaned.

This split is why the region overlay is drawn on the waveform in Reloop only: in Reloop the
capture is in view so a highlight showing where the section sits is meaningful, whereas in
Scaled the waveform already *is* the section and only the pads carry the reminder.

It was moved onto `r ---loopEndMs` in v6_118 and was blank from then until v6_124, because
that send never carried anything — karma~ reporting does not work here. Driving it from
`---size` is both correct and better: `---size` is the effective loop length after the guard,
so the display regrids on LoopLength, multiplier, tempo and Re-Grid with no reporting
dependency.

`s ---loopEndMs` and its `change 0` remain in `p Playback` as a diagnostic hook, sending to
nothing.

---

## 7. Diagnostics in place

Number boxes at root (x 2520, y 700): buffer allocation, LoopLength→bars, multiplier,
`---size` after guard, `---capturedMs`, window sent to karma~, `---reloop`.

In TempoTranslate (x 1050): barMs, requested bars B, capacity bars C, chosen divisor d.

Prints at root (x 2820): `CC-buffer`, `CC-bars`, `CC-mult`, `CC-size`. These fire once per
user action. The blanket "never add print objects" rule concerns per-tick and per-sample
paths; a handful of lines per parameter change is not a flood, and a print is the only way to
see a `buffer~` error that follows a message.

Sanity check: `size AFTER guard ÷ captured` should equal `window` whenever the ratio is under
1. And `d` should always divide `B` and never exceed `C`.

---

## 8. Known-outstanding

- **Slice rescaling on resize.** Window shrinks the playing region but jump positions are not
  scaled, so below the captured length you loop over a subset of the 16 pads rather than
  getting 16 across the shorter loop. Fixing it means `jump = n/16 × window` on the jump path
  in `p glitching`.
- **`stop` is only on the INIT chains.** A new-loop capture at a different length still needs
  an INIT first, because `record` from a playing state overdubs. A Record-path `stop` was
  considered and is **retired** — it would interrupt performance, and length changes no longer
  require re-recording. Note also that three sites send `stop` where no loop may exist
  (`p INIT`'s unconditional loadbang stop, full INIT outlet 9, and the `hc_gate` cluster on the
  arm path); gating them behind `---hasContent` is an open proposal, not a fix, and addresses
  no reported symptom.
- **Reloop palette is unattached.** `1 / 0.5 / 0.25 / 0.125 / 0.0625` message boxes feed
  `s ---reloop` but no UI control drives them yet. `reloop_toggle` drives `---reloopMode`, which
  is the mode switch, not the division.
- **Speed and stutter are unwired.** `playback_speed` and `stutter_rate` have zero patchcords;
  `p SpeedControl` and `p GlitchControl` have no inlet connections; `---glitchOn` and
  `---pitchOn` sit behind a gate driven by `---ToggleValue`, which has receivers and no sender
  anywhere. Note there are **two distinct channels differing only in case** — `---ToggleValue`
  and `---toggleValue` — and neither is driven. The stutter engine cannot engage. `p
  SpeedControl` and `p GlitchControl` also expect relative encoder deltas, not absolute dial
  values, which is why the dials are deliberately disconnected rather than simply unfinished.
- **Preroll remains blocked.** See the karma-loop-semantics skill, section 6.

---

## 9. Added since v6_127 — the region overlay

A second display layer marking which slices the current loop covers. It is deliberately
independent of the playhead chain: its own 32 panels inserted at array index 86 (behind both
playhead banks, in front of the `waveform~` and the pad buttons), its own trigger, and no cords
added to `ov_1000`–`ov_1007`, `ov_show_*` or `ov_hideall`.

```
s = 0                  in Scaled   (ovr_szero, gated off in Reloop by ovr_zinv !- 1)
s = struck pad index   in Reloop   (ovr_phg ← ---padHitRaw)
n = clamp(int(---windowVal × 16 + 0.999), 1, 16)
lit when ((i − s + 16) % 16) < n
```

Recomputed only on a length change, a mode change or a Reloop strike — never per slice edge.
`ovr_fire3 t b b b` fires right to left: clear all 32, set `s`, run the pass.

`---padHitRaw` carries the pad index 0–15 and is fed by the pads, the UI grid and the waveform
click path alike, so it is the single hook for "a slice was triggered" whatever the source.

Known gap: the window is always drawn ahead of the playhead, so under reverse it should extend
behind. A `gate 2` on `---effectiveReverse` selecting `i − s` or `s − i` into the modulo.
