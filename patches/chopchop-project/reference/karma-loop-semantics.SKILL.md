---
name: karma-loop-semantics
description: Verified karma~ loop-definition, transport-state, window/position and buffer-resize semantics, taken from the karma~ help file and from reproduced behaviour in the ChopChop device. Revision 2 corrects two sections that were wrong: a bare `window` change places the region at the capture start rather than following the playhead (section 3), and the status report is readable — the historical failures were probe faults (section 8). Use before wiring or debugging anything that creates, resizes, resets or reports a karma~ loop — including record/play/stop sequencing, dynamic loop resizing, buffer clearing, and any design that depends on karma~'s status outlet. Several entries exist because a plausible assumption caused hours of misdiagnosis.
---

# karma~ — loop, transport, window and buffer semantics

Everything here is either quoted behaviour from the `karma~.maxhelp` reference patch, or
behaviour reproduced directly in a running device. Where an entry corrects an earlier wrong
assumption, the wrong version is recorded too — the plausible-but-wrong version is what
you'll reach for again otherwise.

---

## 1. The transport state machine determines what `record` does

This is the single most consequential fact about karma~ and the one most likely to be
misdiagnosed as "the loop length parameter is broken".

From the help documentation:

> If the object is in a **stopped** state, a 'record' message will begin recording a **new
> loop**. If the object is in a **playing** state, a 'record' message will begin
> **overdubbing**. If the object is in an **overdubbing** state, a 'record' message will put
> the object in a **playing** state.

So:

| From state | `record` does |
|---|---|
| stopped | creates a new loop, at whatever length the pass runs for |
| playing | overdubs into the **existing** loop bounds |
| overdubbing | returns to playing |

**Loop length is only ever established when a loop is created.** A device that ends every
capture with `play` leaves karma~ playing, so every subsequent capture is an overdub and the
loop length never changes, no matter what the size parameter says.

### Symptoms this produces

- Changing loop length from 1 to 4 bars: the pass runs past the existing loop end and laps,
  giving jumps and missed beats
- Changing from 4 back to 1: the pass ends before covering the established loop, leaving the
  remainder untouched — **silent bars**
- Only the very first capture after load has clean, on-beat slices
- Results appear "variable from the same source", because they depend on capture history

### The fix

Send `stop` before `record` on any path that is meant to create a *new* loop. Leave the
playing-state `record` alone for overdub. In UI terms this maps cleanly: a Record control
means replace and must stop first; an Overdub control means layer and must not.

---

## 2. All three of `stop`, `play` and `record` close an initial loop

> Stops playback or recording immediately. If the creation of an initial loop is ended with a
> 'stop' message, it will also define the beginning and end points for the loop.

And:

> Hit RECORD to begin recording a new loop. If you end the loop by hitting RECORD, the loop
> will begin playing in OVERDUB mode. If you end the loop by hitting PLAY, the loop will begin
> playing. If you end the loop by hitting STOP, you define the loop length and stop playback.

| Ends the pass with | Loop defined | Resulting state |
|---|---|---|
| `record` | yes | overdubbing |
| `play` | yes | playing |
| `stop` | yes | stopped |

**Corrected assumption:** it is *not* true that only `play` commits a loop and `stop`
discards it. That wrong belief invalidated a whole round of buffer testing — a
record-then-stop sequence was declared invalid when it was in fact the correct way to define
a loop and leave karma~ ready to create the next one.

---

## 3. `window` and `position` resize the playing loop live, without stopping

> Once the initial loop is defined, it is possible to loop a smaller section of it. This is
> defined by the position and window controls. Both are set with a range between 0. to 1.

> The playhead will always remain within the position/window boundaries (unless jumped outside
> of), **even when the position/window parameters are moved dynamically**.

This is the only way to change effective loop length without interrupting audio. It shrinks
only — a window can never exceed the captured loop.

### Reproduced behaviour, 4-bar capture, 16 slices

| `window` | Plays | Pads |
|---|---|---|
| 1 | 4 bars | 1–16 across the whole loop |
| 0.5 | 2 bars | half the loop |
| 0.25 | 1 bar | pads 1–4 = bar 1, 5–8 = bar 2, 9–12 = bar 3, 13–16 = bar 4 |
| 0.125 | 2 beats | |
| 0.0625 | 1 beat | a single slice, i.e. beat repeat |

**Jump positions are not rescaled by the window.** A pad still jumps to its absolute position
across the *captured* loop, and the window follows the pad. Nothing falls outside the window;
playback wraps within it. Confirmed by direct test.

This has a design consequence worth being explicit about:

- **Reloop / beat-repeat mapping** — absolute pad positions, window follows the pad. This is
  what karma~ does natively, with no extra work.
- **Resize mapping** — if you want 16 pads spanning the *new shorter* length rather than a
  quarter of them, jump positions must be scaled: `jump = n/16 × window`. That scaling is
  yours to add; karma~ will not do it.

### CORRECTION — a `window` change on its own does not follow the playhead

"The window follows the pad" holds for a **jump**. It does **not** hold for a bare `window`
message. If `window` arrives with no accompanying `position` or `jump`, karma~ places the region
at the **start of the capture**, wherever the playhead happens to be.

Verified on a 4-bar capture at a 3-bar window, four commits from different slices: from pad 9
it plays 9→12 then 1→8; from pad 5, 5→12 then 1→4; from pad 12, 1→12; from pad 7, 7→12 then
1→6. All four play the same twelve slices — the first `n`. Only the entry point moves.

Two consequences, both of which cost builds before they were understood:

- **The region start is not something to derive from the playhead.** Five separate derivations
  were built in ChopChop and all five were wrong, because the quantity they were computing had
  no effect on where karma~ actually put the region. Check which messages the device sends
  before deriving what it should receive.
- **A shortening committed while the playhead is past slice `n` will jump.** The playhead is
  outside the new region, so karma~ pulls it back to the start — audible. The safe window is
  "already inside the new length": lengthening is always safe, 4→3 breaks only from bar 4,
  4→1 breaks from anywhere past bar 1. Treat this as designed behaviour and surface it in the
  UI rather than trying to remove it — both routes out of it are closed (see §8a).

---

## 4. `append` extends only

> Sending a message of 'append' will put karma back in its "initial loop creation" state,
> allowing for new definitions of the loop in/out points. … Hitting record will then begin
> recording **where the loop previously ended**.

Append grows a loop from its end point. There is no documented way to pull the out-point in,
so append cannot shrink. Shrinking is `window`'s job. Append also requires a record pass, so
it is a deliberate act rather than a parameter change.

---

## 5. Buffer operations while a karma~ is attached

| Message | Works with karma~ attached? |
|---|---|
| `clear` | **Yes** — reproduced; zeroes the audio, playback goes silent |
| `crop` | **No** — fails with "can't resize" |
| `size` | **No** in Max for Live — fails with "can't resize now" |
| `sizeinsamps` | Works in the help patch, **but see below** |

The help patch resizes with `loadbang → sizeinsamps 8192 → buffer~` while a karma~ is
attached, and it works. That patch's own instructions say "turn on audio" as a *later* step,
so it loads with the audio engine off.

**A Max for Live device always has DSP running.** There is no point in a M4L device's load
sequence when the audio engine is off, so runtime buffer resizing is effectively unavailable
there. Declare the buffer at the size you need and use `window` to work within it.

**Also important:** `clear` zeroes the audio but does **not** reset karma~'s loop bounds. A
cleared buffer with a defined loop still has that loop. Clearing is not a way to get back to
the "stopped, no loop" state — only `stop` puts karma~ where `record` will create a new loop.

---

## 6. A karma~ pointed at a buffer it did not record reads the whole allocation

Measured: a `set <buffer>` to a buffer recorded by a *different* karma~ gives an end point of
19999.98 ms on a 20000 ms buffer, and a window of 0.0625 gives 1249.999 ms. It treats the
entire allocation as the loop.

Combined with `crop` being unavailable, this closes off copy-based handover between karma~
instances: `duplicate` works, `crop` does not, and without the crop the receiving instance
reads the whole buffer.

The same measurement appears if a loop is *never defined at all* — record without ending the
pass, leave it running, and the reported end eventually settles at the full allocation. If you
see a number near the buffer length, suspect "no loop was ever defined" before suspecting a
handover bug.

---

## 7. Object shape

- **Mono** `karma~ <buf>` — 2 inlets, 2 outlets
- **Stereo** `karma~ <buf> 2` — 3 inlets, 3 outlets

| Inlet | Takes |
|---|---|
| 0 (leftmost) | left audio **and every message** — `record`, `play`, `stop`, `report`, `window`, `position`, `jump`, `set`, `append` |
| 1 | right audio (stereo only) |
| last | speed, as a **signal** |

> Varispeed … is controlled by a signal going in to the right-most inlet of the external.
> There is no minimum/maximum value as interpolation is used.

**The status outlet is the last outlet** — outlet 1 on mono, outlet 2 on stereo. Not outlet 2
universally. A test patch built with the wrong outlet count silently reported nothing and cost
several hours.

---

## 8. Status reporting — CORRECTED, it is readable

The status list is `unpack f i i f f f`:

> current position (0. to 1.) · play state (int) · record state (int) · start position (ms) ·
> end position (ms) · window size (ms)

Reporting must be switched on with a `report <ms>` message. The help patch uses
**`loadmess report 150`** — an object that fires itself at instantiation, not a message box
triggered later.

This section previously said the report was unusable in M4L and that no feature should depend
on it. **That was wrong.** The report drives every slice overlay in ChopChop and always has.
The historical "it produces nothing" observations were probe faults, three of them recorded:

- a scratch patcher declaring `karma~` with 5 outlets instead of 3, which reported nothing;
- probes placed in the patcher window while behaviour was judged on the device panel — put
  probes in **presentation mode**;
- a 62 px `flonum` truncating 119999.98 to 11999.98, a factor of ten.

What survives from the original guidance, and is still right:

**Prefer a value you own to one you read back.** Latching your own requested size at capture
time cannot fail silently and is available immediately. More importantly, a value read from the
report and fed back into playback closes a loop — the change alters the window, the window
alters the report, the report causes the change. ChopChop v6_170 did exactly that and produced
a stack overflow in Ableton. A cold inlet is not protection.

**Which elements to trust:** 1, 2, 4 and 5 are reliable. Element 3 reads 0.00 in every state
tested despite the tooltip calling it start-position, and element 0's coordinate space is not
established. See the `karma-coordinate-conventions` skill, section 2a.

---

## 8a. Two closed routes for committing a resize out of bounds

Both were built against ChopChop and both were reverted. Recorded so they are not retried.

**Jump to the current slice on commit.** Reading the playhead and feeding it back into playback
closes the loop described in §8. Cycle count rose from 27 to 30 and the device stack-overflowed.

**Defer the commit until the playhead is back in bounds.** In ChopChop the length change is
latched on a slice edge, and that same latched value feeds the playhead display chain. Gating it
desynchronises the display and makes the chase stick.

The general shape: **a commit gate must not sit on a value that a display also consumes, and a
commit must not be triggered by anything downstream of it.**

---

## 9. Recording past the buffer end wraps, it does not stop

> While creating the initial loop you can wraparound the area recorded thus far by going below
> "zero" … When doing this you will **overdub (and hear) the audio that was previously
> written** to that part of the buffer.

So a record pass longer than the allocation silently corrupts rather than failing. Any device
that lets the user select a length exceeding the buffer needs a guard that reduces the length
*before* recording starts.

Reduce to a **divisor of the requested bar count** rather than simply flooring to what fits.
64 bars into a 40-bar capacity should become 32, not 40 — 32 repeats twice per intended phrase
and stays in time, whereas 40 drifts against it forever.
