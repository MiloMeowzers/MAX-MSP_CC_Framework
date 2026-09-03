---
name: max-msp-karma-technical
description: Verified Max/MSP and karma~ object facts (inlet/outlet conventions, object behaviors, common gotchas), each confirmed against real documentation or reproduced evidence rather than assumed. Use before wiring any new Max object whose exact behavior isn't already confirmed here, especially inlet/outlet semantics, type coercion, and object argument counts — several entries exist specifically because a plausible-looking assumption caused a real, hard-to-diagnose bug.
---

# Max/MSP & karma~ — Verified Technical Reference

Every fact below was **verified against real documentation or reproduced evidence** during
this session — not assumed. Several corrected a wrong assumption that had already caused a
real bug. Where a fact was learned *because* of a mistake, the mistake is noted, since knowing
the wrong-but-plausible version is as useful as knowing the right one.

## The core discipline this file exists to reinforce

**Never assume an object's inlet/outlet semantics from how it looks or from a similar
object.** This session found four separate, self-introduced bugs from exactly this kind of
assumption (see `gate`, below, found four times before being fixed once — the same wrong
assumption was reused across multiple builds before it was ever checked). The fix each time
was the same: stop, search for the object's real reference documentation, verify the specific
claim, then proceed. Do this *before* wiring, not after something doesn't work.

## `gate` — control/data inlet convention (found backwards 4× this session)

**Left inlet = control** (an int selecting which outlet opens; `0` closes it).
**Right inlet = data** (whatever should pass through to the selected outlet).

> "Messages received in the right inlet are passed out the outlet specified by the number in
> the left inlet. If the number in the left inlet is 0... all messages are ignored."
> — Cycling '74, `gate` reference

For a single-outlet `gate 1`: left inlet `0`=closed, `1`=open; right inlet carries the data.
A number arriving at the **left/control** inlet never itself produces output — only what
arrives at the right/data inlet, while control is open, does. Sending data to the *left*
inlet by mistake means it's silently ignored (misread as a control value); sending the control
signal to the *right* inlet by mistake means the gate never actually opens/closes as intended.
**This exact mistake was made four separate times in one session** before being caught — always
double-check new `gate` wiring against this convention explicitly, don't pattern-match to
"whichever inlet felt like data before."

## `live.menu` — float outlet gives normalized position, not the item's value

The third (float) outlet does **not** give "the actual numeric value of the selected item"
(a plausible-sounding assumption that was wrong and caused a real, previously-undiagnosed
bug). It gives a **normalized 0–1 value based on list position**: for an *n*-item menu,
selecting index *i* gives `i / (n-1)`. For a 5-item menu (`0.5, 1, 2, 3, 4`), clicking `0.5`
(index 0) sends `0.0`; clicking `4` (index 4) sends `1.0` — completely disconnected from the
item's displayed/semantic value.

**To get the actual selected value**: use the **left (index) outlet** (a genuine integer
0..n-1) and route it through an explicit lookup (a `route` matching each index, feeding
message boxes with the real values) — the same pattern already used elsewhere for discrete
value tables. Do not trust "3rd outlet = real value" as a rule for `live.menu` — verify per
instance, since this exact wrong rule was documented as fact in an earlier project doc and
propagated a live bug for an unknown length of time before being caught.

## `live.toggle` — inlet behavior

A plain number sent to the inlet **does** fire the outlet (updates + broadcasts). Only the
`set` message (`set <value>`) updates the displayed/stored state **without** firing the
outlet — useful for silent initialization, dangerous if used where a live update was intended.
`live.toggle` also has a mouse-down/mouse-up "transition"-style output-timing attribute
(default: output on mouse-down) — not fully characterized this session, but worth checking if
a toggle's timing ever seems off relative to when it's clicked.

## `live.button` — press/release detection

The `transition` attribute controls when the object bangs: `0` = on press only (the default),
`1` = on release only, `2` = both (bangs on both edges, but the raw outlet value alone won't
tell you which edge fired — for genuine press-vs-release logic, use two separate `live.button`
instances, both mapped to the same physical control, one at `transition 0` and one at
`transition 1`). This attribute was found to need setting as a **top-level box property** in
the saved JSON (consistent with how other non-parameter attributes serialize on this object
type), not nested under `saved_attribute_attributes` — **not independently reference-confirmed**,
flagged as worth double-checking in the Inspector if a release-detecting button ever seems to
misbehave.

## Message boxes — the right/cold-inlet "probe" behavior

Sending a value to a message box's non-left inlet does **not** require the box to contain a
`$1` placeholder to have an effect. Confirmed directly from Cycling '74's own tutorial:

> "When you make a connection to the right inlet of a message box, you replace the message —
> but it doesn't output anything! ... the message box will only display the last message that
> it received."

This is a legitimate, sanctioned technique for a passive value "probe" (watch a live value's
current content without wiring anything to consume it) — and it means a message box that
appears to have a hardcoded literal with only an inbound *right*-inlet connection is not
necessarily inert; check whether it's live-updating (a "probe") versus genuinely
disconnected/frozen (check for a **left**-inlet connection or outgoing connection to determine
which). A box with only a right-inlet connection and no outgoing connection is functionally
inert for the signal path, but not "broken" — it's a working, if perhaps forgotten, debug view.

## `delay` — cancellation and rescheduling

Confirmed from Cycling '74 reference: sending `stop` to the **left** inlet cancels a pending
delay before it fires. Sending a **new** value to schedule another delay while one is already
pending automatically cancels the first and schedules the new one — you don't need to
explicitly `stop` before rescheduling, only when you want to cancel without immediately
starting a new one.

## `seq~` — real message-recording semantics

- Confirmed: "Any message can be sequenced except for commands to the `seq~` object itself."
  It genuinely will record arbitrary lists, not just single floats/ints.
- **Explicit, documented warning, directly relevant to any device with reversible/non-linear
  playback**: "seq~ can be used to sequence MIDI data if the MIDI input stream is converted
  into lists of MIDI events. This conversion is necessary to avoid outputting a corrupted...
  stream which would occur if... the seq~ object were not doing a simple forward linear
  playback." **Practical rule**: tag recorded events as lists (e.g. `padhit N` rather than
  bare `N`) any time the device supports reverse or non-linear playback of the recorded
  content — this isn't a style preference, it's the documented way to avoid corruption.
- `seq~` is driven by a signal input at its left inlet (optimized for a continuous ramp,
  typically `phasor~`, but works with any signal range) — the phasor's *value* at the moment
  an event arrives is its timestamp; all recorded events replay according to the signal's
  current value during playback, not real elapsed time. This means changing the driving
  phasor's frequency *after* recording legitimately stretches/compresses playback timing —
  that's by design, not a bug, provided the phasor's frequency-vs-real-time relationship is
  understood.
- `seq~`'s `clear`/`erase` message requires a sequence-name argument per docs
  ("the word clear, followed by the name of a sequence..."). A bare `erase`/`clear` with no
  argument doesn't match documented syntax — treat any such message found in an existing
  patch with suspicion, not as obviously-correct legacy code.

## `phasor~` — negative frequency

Community-corroborated (Cycling '74 forum, not the official reference page explicitly): "a
negative frequency simply results in a phasor that rotates in the opposite direction."
Mechanically this falls directly out of how a phasor is implemented (a simple per-sample
accumulator, `phase += frequency/samplerate`, wrapped to 0–1) — flipping the frequency's sign
just makes the accumulator subtract instead of add, continuing from whatever phase it's
currently at. This means reversing direction via a sign-flip is a genuine "U-turn from current
position," not a jump to a different point — true for both `phasor~` itself and for any
tape-style engine (like karma~) that treats speed and direction as the same signed parameter.

## `karma~` — third-party external, not Cycling '74 documented

`karma~` (by Raja/Rodrigo Constanzo) is **not** an official Max/MSP object — there is no
`docs.cycling74.com` reference page for it. Real sources: the author's own site
(rodrigoconstanzo.com/2015/05/karma), the GitHub repo (github.com/rconstanzo/karma), and
Cycling '74's own community forum threads (which discuss it as a third-party tool, not house
documentation). See the reference-sources file for direct links.

Confirmed from the author's own description (Cycling '74 tools listing): **karma~ needs a
live input on its right (speed) inlet, similar to `groove~` — with nothing connected, it
records/plays at speed zero.** This is a strong signal that the inlet is **signal-preferential**
(a standard Max convention: if a signal is connected to a signal-capable inlet, float messages
to that same inlet are typically ignored in favor of the live signal) — worth checking directly
against the specific `.amxd` before assuming a float message alone will reach it, if it's also
signal-connected elsewhere.

**Not yet verified this session**: the precise behavior of negative values on karma~'s
*continuous* speed inlet specifically (as opposed to speed set via whatever discrete/message
mechanism a given patch might use). Do not assume it behaves identically to the discrete case
without confirming.

## Reusable Max patching techniques (used repeatedly this session, all working)

**On-demand read of a live value** (needed because `r`/receive objects have **zero inlets** —
they cannot be "polled" or banged for their current value, they only push when their paired
`s`/send fires): maintain a local `f` (float) object continuously fed by the `r` object on its
hot/left inlet (auto-stores and outputs on every change). To read the *current* value on
demand later, bang that same hot inlet — it re-emits the last stored value without needing a
new value to arrive.

**Correct sequencing of "set the other input, then trigger recompute"**: Max's `t` (trigger)
object fires its outlets **right to left**. To ensure a cold/right inlet is set *before* a
hot/left inlet is triggered (a very common requirement — e.g., "update the divisor, then
retrigger the divide"), route the value that sets the cold inlet through the trigger's
*rightmost* outlet, and the bang that triggers the hot inlet through the *leftmost* outlet.
Getting this backwards (right and left outlets in the wrong order for the desired sequence) is
an easy, quiet mistake — always trace which outlet fires first when building a new `t`-based
sequence, don't assume left-to-right.

**Combining multiple boolean sources into one (XOR-style)**: sum the sources, then take
modulo 2. `(a + b) % 2` gives 0 when both agree, 1 when they differ — exactly XOR for 0/1
inputs, and generalizes cleanly to more sources by chaining sums before the final mod. Each
source needs its own local `f`-store (per the "on-demand read" pattern above) so that a
change in *any* source can force a fresh re-emit of *all* sources into the sum, not just the
one that changed.

**Position/wrap detection without a timer**: if a real, live position signal already exists
(as karma~'s status report provides), compute the delta between consecutive readings and treat
any delta larger than a sane threshold (e.g. `> 0.5` for a 0–1 normalized position) as a wrap
event. This is more robust than a synthetic timer matching a *calculated* period, since it
reacts to what's actually happening rather than an assumption about what should be happening —
and it was an explicit, correct architectural correction requested mid-session after the
timer-based approach proved unreliable.

## `route` — silently fails to match a force-converted float against integer arguments

**Found via an extended, multi-session debugging chase** (the waveform position overlay's
"show the correct slice" mechanism worked perfectly on manual trigger but never fired during
real automatic operation, despite provably correct wiring end-to-end). Root cause: the value
feeding `route 0 1 2 3...` had been force-converted to float via a `t f b` (trigger, float
outlet) immediately upstream. `route`'s numeric-argument outlets did not match against this
force-converted float, even though the numeric value was correct and even though `route`
generally documents itself as matching numbers regardless of int/float distinction. Changing
the upstream trigger to `t i b` (integer outlet, preserving the value's native int type instead
of force-converting it) fixed the match immediately and completely.

**Practical implication**: do not assume `route`'s numeric matching is float/int-agnostic in
all cases. If a `route` object's outlets aren't firing despite the incoming value visibly being
correct (confirmed via a `print` immediately upstream) and the wiring is confirmed correct via
scope-aware inspection, check the *type* of the value arriving — specifically whether it was
force-converted via `t f ...` — before assuming a wiring or logic bug. Prefer feeding `route`
values that retain their natural type (use `t i ...` rather than `t f ...` when the value is
conceptually an integer index) rather than force-converting to float upstream.

**How this was actually diagnosed** (useful pattern for future silent-mismatch bugs): a
`print` was added immediately before and after the suspect object. The upstream print fired
reliably with correct values; the downstream print never fired during real operation. A manual
click directly on the object downstream of `route` (in a locked, running patcher) fired
correctly and produced the expected visible result — proving every part of the chain *except*
`route`'s own matching was sound. This isolated the bug to `route` specifically, rather than to
rendering, scripting, or wiring, which several earlier (incorrect) hypotheses had assumed.

---

## `uzi` — the index is on outlet 2, not outlet 1

`uzi` has three outlets and its `outlettype` is `['bang', 'bang', 'int']`:

| Outlet | Carries |
|---|---|
| 0 | bang, once per iteration |
| 1 | bang, the carry — fires once when the run completes |
| 2 | **int, the current iteration number** |

Taking the index from outlet 1 gets a single bang at the end of the run, so a per-iteration
chain receives nothing at all and the whole mechanism is silently inert. That is exactly what
happened in ChopChop v6_151: a 69-box region-overlay build produced no visible output and the
fault was invisible to the validator, the cycle sweep and the duplicate-cord sweep, because
every cord was legal.

Arguments are `uzi <count> <start>`; default start is 1, so `uzi 16` yields 1–16 and needs a
`- 1` for a zero-based index.

**The general lesson is not about `uzi`.** A working instance of the same object already
existed in the same patcher — `uzi 64 1` in `p TempoTranslate`, driving from outlet 2. Before
wiring an object whose outlet layout you have not confirmed, grep the patcher for an existing
instance and copy its wiring. The reference is usually already in the file.

Related: when duplicating an object that has a non-obvious inlet or outlet count, copy the
`numinlets` / `numoutlets` from the working instance rather than reasoning about them.
`route 0 1 … 15` in this device carries `numinlets: 17`, which is not what the object reference
would lead you to expect.

---

## `minimum` / `maximum` as a clamp — a pinned index means bad input

`minimum 15` then `maximum 0` clamps to 0–15. When the display holds at 15 and a downstream
`change` freezes it there, **the input has left its range** — the clamp is working. This reads
as a stuck display and has been misdiagnosed as one repeatedly in this project, prompting fixes
aimed at the display end that regressed the device.

Check what is feeding the clamp before touching anything after it.

---

## `f` — a cold inlet stores, but it does not break a feedback loop

`f`'s right inlet stores without outputting, which is often described as making it safe to tap
a live value. It is not, if the tapped value is later fed back into whatever produces it.

The loop does not need the `f` to re-fire. It only needs the chain to close: ChopChop v6_170
stored a live playhead index in a cold inlet, banged it on commit, and sent the result back
into playback. The commit changed the window, the window changed the report, the report changed
the index — stack overflow in Ableton, with the message-cycle sweep rising from 27 to 30
beforehand as the only warning.

**Run a cycle sweep against a recorded baseline on every build.** A structural cycle that
cannot iterate is still worth knowing about; one that can will not announce itself until it is
running in the host.

