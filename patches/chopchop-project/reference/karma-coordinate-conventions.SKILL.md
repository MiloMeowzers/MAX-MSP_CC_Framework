---
name: karma-coordinate-conventions
description: The units and coordinate system of every karma~ status-report element and control message, and — equally important — which of them are still unverified. Use before writing any arithmetic that combines two karma~ quantities, before building an overlay or display that tracks playback position, and before assuming that two values from karma~ share a denominator. Read section 0 first: three claims in the previous revision were wrong and each cost a build.
---

# karma~ — what "normalised" means, per quantity

Every karma~ quantity in the range 0 to 1 is normalised over something. **They are not
normalised over the same thing.** This file records which is which, what was measured, what
has been disproved, and what remains open.

---

## 0. Corrections to the previous revision — read first

Revision 1 of this file was written from a single probe session and treated its readings as
settled. Three of its claims are wrong or unusable, and building on each of them cost at least
one build in the v6_147–v6_174 session.

| Claim in revision 1 | Status |
|---|---|
| Report element 0 is region-relative and always starts at 0 | **Disproved as a basis for arithmetic.** See §1. |
| Element 3 is unidentified but the project reference calls it start-position (ms) | **Neither is usable.** It reads 0.00 in every state. See §2a. |
| karma~ does not tell you the region start | **The question is moot.** See §1a. |
| Region start on a `window` change: latch 0.875 → region near 0.4375 | **Does not describe `pos × window`.** See §3. |

The pattern behind all four: a reading taken in one narrow state was generalised into a rule.
A measurement is evidence about the state it was taken in. It becomes a rule only when the
states that would falsify it have also been tried.

---

## 1. Report element 0 — coordinate space NOT established

**What was measured.** With a fixed capture and the loop length changed, element 0 sweeps:

| window | reported range |
|---|---|
| 1.0 | 0 → 1.0 |
| 0.5 | 0 → 0.499 |
| 0.25 | 0 → 0.249 |

The span equals `window` and the sweep starts at 0.

**What was wrongly concluded from it.** That the value is region-relative, and therefore that
the `− ---regionStart` subtraction ChopChop's playhead chain performs on it is redundant.

**What happened.** Removing that subtraction (v6_149) produced progressive drift, a chase
stuck at the clamp, and an overlay that stopped following clicks and pad hits. Progressive
drift is the recorded signature of two quantities with different denominators, so the
subtraction is converting between two spaces and is load-bearing.

**Treat element 0's coordinate space as unknown.** Do not remove or reproduce that subtraction
on the strength of the table above. If a build depends on knowing, measure it in the state the
build will run in — with a region that does *not* start at 0 — because every reading in the
table was taken with the region at the capture start, where region-relative and absolute
coincide.

---

## 1a. karma~ places the region itself — usually there is nothing to derive

The region-start question that consumed five builds turned out not to need an answer.

ChopChop sends **only `window`** on the length-change path — no `position`, no `jump`. karma~
therefore places the region itself, at the start of the capture. The loop is always the first
`n` slices, and only the entry point varies with where the playhead was.

Verified by tracing four commits on a 4-bar capture at a 3-bar loop: from pad 9 it plays
9→12 then 1→8; from pad 5, 5→12 then 1→4; from pad 12, 1→12; from pad 7, 7→12 then 1→6. All
four play the same twelve slices.

**Before deriving a position from karma~, check whether the device sets it.** If the device
never sends `position` or `jump` on that path, karma~'s placement is a fixed default and no
derivation is needed. Five separate derivations of a region start were built before anyone
checked which messages were actually being sent.

---

## 2. The `jump` message is absolute over the capture

**Measured.** With a 4-bar capture and a 1-bar window, `jump 0.5625` (pad 9 of 16) lands on
beat 1 of bar 3 — 0.5625 of the capture, not of the window.

So `jump` and the status report use different denominators. Do not subtract one from the other
and do not use a latched report value as a base for a jump target.

This one has held up. It is also why reloop-mode region tracking works: the jump target is a
value the device chose and sent, not one read back.

---

## 2a. The full report layout

Read off a running device through presentation-mode probes on `unpack f i i f f f`.

| Element | Carries | Units | Confidence |
|---|---|---|---|
| 0 | playhead position | normalised — over **what** is open (§1) | low |
| 1 | play state | int | good |
| 2 | record state | int | good |
| 3 | reads 0.00 in every state tested | — | **unusable** |
| 4 | loop end | milliseconds | good |
| 5 | window / loop length | milliseconds | good |

**Element 3.** karma~'s own assist tooltip calls it `start-position (ms)`, and
`02_ChopChop_Project_Knowledge_Reference.md` records that as authoritative. It does not hold on
this device: element 3 sits at 0.00 on a fresh load, during recording, after a full INIT, after
a resize and after a reloop jump. A build that took the region start from it drew the region
from slice 1 every time, because the value was always 0. **Do not use element 3.**

**Elements 4 and 5** are absolute durations, not fractions. Anything dividing them by a
normalised value, or comparing them against element 0, is mixing units. A four-bar capture at
70 bpm requested 13714 ms and reported 13712.31 on both — karma~'s committed loop runs about
1.7 ms short of the request, consistently. Do not treat `---size` and the real loop length as
identical.

**Naming trap.** In ChopChop, `---sliceLengthMs` is fed from `karma_window_cache`, which is
element 5. It is the window in milliseconds, **not** a slice length. Anyone looking for a slice
count finds that name first and gets the wrong quantity.

---

## 2b. On a fresh load, elements 4 and 5 read the whole allocation

On a fresh load and after a full INIT with no content, elements 4 and 5 read ~119999.98 ms
against a 120000 ms buffer.

**Measured:** the readings above.
**Inferred, and never tested:** that `stop` on a karma~ with no defined loop is what commits
the allocation, and that it should therefore be gated behind a has-content flag.

Builds were prepared to gate the three `stop` sites in ChopChop (`p INIT`'s unconditional
loadbang stop, full INIT outlet 9, and the `hc_gate` cluster on the arm path) and were never
tested, because the change addressed no reported symptom. The reading stands; the causal story
does not, and the gating remains an open proposal rather than a fix.

---

## 2c. The report is readable — historical failures were probe faults

This project believed for a long time that karma~'s report produced nothing. It does not; it
drives every slice overlay in the device and always has. Three recorded causes of "the report
gives nothing":

- **A scratch patcher declaring `karma~` with the wrong outlet count** — 5 instead of 3. It
  reported nothing and the silence was read as a fact about karma~.
- **Probing in the patcher window.** Device-panel overlays and tints are not usefully
  observable there. Put probes in presentation mode.
- **A 62 px `flonum`** truncating 119999.98 to 11999.98, a factor of ten, nearly producing a
  wrong conclusion about buffer size. Widen the box.

---

## 3. What has not been established

- **Whether `position` uses the report's coordinate or `jump`'s.** Never measured. Two builds
  were designed around each answer in turn; neither was ever run.
- **Where karma~ places the region when `window` changes while playing.** A measurement
  recorded a latch of 0.875 against a region near 0.4375 with a window of 0.5, which reads as
  `pos × window`. **Building on that reading is disproved**: scaling the anchor by the window
  produced a uniform 8–10 slice error across every transition, worse than not scaling at all.
  Whatever that measurement captured, it was not the placement rule.
- **Whether a `jump` landing inside the current region leaves the region in place or moves it.**
  Out-of-region relocates it; the in-region case is untested.

---

## 4. Never feed a report-derived value back into playback

The report is live at the `report 20` rate. Anything that reads it and causes a playback change
closes a loop: the change alters the window, the window alters the report, the report causes
the change.

ChopChop v6_170 latched the playhead index from the display chain and sent it as a jump on
commit. The cycle sweep rose from 27 to 30 and the build produced a stack overflow in Ableton.

**A cold inlet is not protection.** The loop does not need the reading object to re-fire; it
only needs the chain to close.

**A cycle sweep catches this before the device does.** Run one against a recorded baseline on
every build.

---

## 5. Symptoms that mean a coordinate mismatch

- **A value that drifts further apart the longer it plays.** Two quantities advancing at
  different rates. In ChopChop this was a gen~ phasor normalised over `---size` subtracted from
  a karma~ report normalised over something else: at quarter length the phasor completed four
  cycles for the report's one.
- **An index pinned at its clamp.** A `minimum`/`maximum` pair holding at the top or bottom
  while a `change` freezes it there means the input has left its range, not that the display is
  stuck. This is the single most misdiagnosed symptom in this device.
- **Audio correct while the display is wrong.** karma~ bounds playback by its own internal
  region regardless of what the device believes, so a coordinate error shows in the display
  long before it is audible.

---

## 6. The rules this file exists to enforce

**Measure in the state the build will run in.** Every reading in §1 was taken with the region
at the capture start, where region-relative and absolute are the same number. That is why the
table looked conclusive and was not.

**Check what the device sends before deriving what it should receive.** §1a.

**Two data points fitting a rule is not a rule.** An error of 4 at n=12 and 8 at n=8 fitted
`16 − n` exactly and produced a confident wrong diagnosis; the third case did not fit and was
rationalised away. State what a proposed fix should change and by how much, so the next test
falsifies it rather than merely failing.

**Prefer a value the device owns to one read back.** Everything the region overlay eventually
needed already existed in the patch: the slice index at the end of the playhead chain, the
window at `---windowVal`, the jump target on the reloop path.
