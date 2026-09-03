# ChopChop — Project Knowledge Reference (v2)

This supersedes the previous knowledge reference. Several claims in the earlier version were
found to be **stale or wrong** during this session — corrected below, with the discrepancy
noted where it matters, since the pattern of the doc being wrong recurred enough times to be
worth flagging as a lesson in itself: **verify against the actual file, every time, even when
a prior doc sounds confident.**

See `00_ChopChop_Changelog_and_Timeline.md` for chronological detail and
`01b_ChopChop_Device_Architecture_SKILL.md` for the full technical wiring map.

## What this project is

A Max for Live device pair (Brain + Instance bpatcher). Instance file deliverable:
`ChopChop.amxd` / working file `ChopChop_v1_DEV.amxd`. Brain: `ChopChop_Brain.amxd`, largely
untouched. A 16-slice loop chopper built on **karma~** (third-party looper/sampler external,
not a Cycling '74 object — see the reference-sources file for where to find real docs on it).

## Core architecture, corrected

The original knowledge reference described `---playbackSpeed` as controlling karma~'s
continuous playback speed directly. **This is wrong.** Traced this session:

- `r ---playbackSpeed`'s only consumer is `p glitching` (inside `p Playback`), which feeds a
  `gen~` processing chain that constructs `jump`/`position`/`window` messages sent back to
  karma~. This is a real, audible mechanism — not a dead channel — but it is **not** karma~'s
  native speed control.
- Karma~'s actual speed inlet is **inlet 2** (its rightmost inlet, of 3), confirmed
  signal-preferential — matching documented `groove~`-like behavior: it needs a live input or
  speed defaults to zero. The real chain feeding it:
  `sig~ 1 → *~1. (obj-63) → *~1. (obj-21, modulated by p MessagesToKarma) → *~1. (obj-7,
  modulated by p transport) → karma~ inlet 2`.
- `p MessagesToKarma` is therefore the more likely correct integration point for genuine
  continuous-speed control, but this has **not yet been traced in depth** — flagged as the
  natural next step if `reverse_mode`'s mystery (below) needs a fresh angle.

**Named channel table**: mostly unchanged from the original reference, with the correction
above. See the architecture skill file for the full, current map of every traced connection.

## Reverse / back-forth / punch — current state

- **Punch-in-reverse**: ✅ built, confirmed working reliably throughout this session. Momentary
  press/release (`live.button`, `transition` attribute 0/1), XORed with `reverse_mode`'s
  persistent state via a shared combiner.
- **`reverse_mode` "no audible effect" mystery: RESOLVED — was a UI label/object identity
  mix-up, not a signal-chain bug.** The `live.button` whose UI label read "Pingpong" was
  actually wired to the real `reverse_mode` logic, and the button labeled "Reverse" was
  actually wired to `back_forth_mode` (ping-pong). Every test throughout this project's history
  had therefore been exercising the *other* feature from the one being reported on — pressing
  "Reverse" produced ping-pong's audible effect (genuinely working), while the actual
  `reverse_mode` toggle (mislabeled "Pingpong") was never being meaningfully tested as
  "reverse" at all. This fully explains the exhaustive, dead-end diagnostic chain in Phase 7
  below: the computational chain really was proven correct at every stage, because it was
  never actually broken — the label swap made the test results misleading, not the logic.
  **Still open**: only one of the two buttons was reportedly producing an audible effect after
  this was caught, not both — the label-swap explanation accounts for the *false* test results,
  not for why two theoretically-independent, now-correctly-identified controls wouldn't both
  simply work. Worth a fresh, clean test with correct labels before assuming this needs further
  signal-chain investigation. (Also worth remembering: `p glitching`/`---playbackSpeed`
  disconnection was raised and ruled out as an explanation earlier in this investigation —
  no need to re-litigate that specific hypothesis if this resurfaces.)
- **Ping-pong, unsequenced (`back_forth_mode`, karma~ direct loop)**: ✅ confirmed working,
  "crisp and clean," after a real self-found bug (see below) was fixed. Built on real position
  data — karma~'s own reported playback position (0–1, broadcast every ~20ms via the
  pre-existing `report 20` mechanism), watched for a jump > 0.5 as the wrap signal. No timer,
  no period calculation, no synthetic clock — this was an explicit architectural correction
  from the user, who correctly identified the original timer-based design as unnecessary
  complexity.
- **Ping-pong, sequenced (pattern/`seq~` mode)**: ⚠️ still on the older, timer-based design
  (self-rescheduling `delay` matching a computed period). Not yet rebuilt on a real signal, and
  not re-verified since the gate-inlet fix below (which does apply to it).

### The gate-inlet bug (important, generalizable lesson)

Max's `gate` object has **left inlet = control** (which outlet opens), **right inlet = data**
(what passes through) — confirmed against official Cycling '74 docs and community consensus.
Every `gate` object built fresh this session had this backwards, discovered only when directly
verifying the convention while investigating the reverse_mode mystery. This silently broke the
rebuilt ping-pong wrap-detector and both A/B-toggle gates for pad-hit recording. All four were
found (by systematically checking every self-built `gate` against the verified convention) and
fixed. **Lesson**: never assume a Max object's inlet semantics from pattern-matching to a
similar-looking object — verify per-object, every time, the same way the project already
insists on verifying object *names*.

## Pattern recording — pad-hit fidelity

Original architecture gap, found this session: pad identity (which of the 16 slices was
pressed) **never reached** `Sequence_Recorder`/`seq~` — it only received generic
record/overdub/stop control messages. This meant recorded "patterns" never actually captured
*which pads* were pressed, only *when recording was active* — explaining reported vagueness in
what got recorded.

**Fix built**: pad presses are tagged as `padhit N` (a list, not a bare number — required by
`seq~`'s own documentation to avoid corruption under non-forward playback, which now applies
given reverse exists), recorded into `seq~` alongside the existing control messages, and
routed back on playback through the *exact same* `reverseCompensation` entry point a live pad
press uses — meaning recorded hits re-adapt live to whatever reverse/quantize state is active
at playback time, per explicit user direction (not frozen at record time).

**Correct raw-pad-value tap point**: `TriggerPoisition` inlet 1 (`obj-10`), **not** inlet 0
(which carries a signal, `*~ 1.`, unrelated to pad identity — a real mistake made and corrected
this session; verify the parent-scope wiring before assuming which inlet carries what).

**A/B toggle**: the `user_1` placeholder button (top of the punch-button cluster) now toggles
between the original engine and the new pad-hit-faithful one, via two `gate` objects (fixed
alongside the ping-pong ones). **Not yet tested end-to-end with actual recording engaged** —
diagnostics confirmed the raw tap point is correct in isolation (bare pad presses, no
recording), but the full record→playback loop with the new engine has not been verified live.

## UI — pad grid layout (fixed)

**Explicit specification** (previously given, previously not implemented — corrected this
session): 4×4 grid, pad 1 bottom-left, pad 16 top-right, reading:
- Top row: 13, 14, 15, 16
- Row 2: 9, 10, 11, 12
- Row 3: 5, 6, 7, 8
- Bottom row: 1, 2, 3, 4

Verified via `presentation_rect` coordinates before and after the fix; matches spec exactly.
**Internal button-to-value wiring was always correct** (`pad_trigger_N` → value `N-1` for all
16, confirmed by individually tracing every button) — the bug was purely the *visual position*
of buttons relative to their internal values, not the logic. If pad presses still seem
scrambled after this fix, check the MIDI mapping in Ableton (it was recorded against the old,
wrong layout and will need re-recording against the corrected one).

## Quantize / grid mechanism (partially traced, real gaps remain)

`TriggerPoisition` contains a dedicated quantize-grid subsystem: a `phasor~` locked to
note-value frequencies (`16n`/`32n`/`64n`, selected via `ButtonQuantize`) plus an edge
detector (`p detect_edge`), `switch`, and `onebang` objects. **Confirmed via diagnostic**: for
deliberately spaced-out pad presses, the raw pad value and `switch`'s output are always
identical — no filtering observed. **Not yet tested**: rapid or simultaneous presses, where
the mechanism's actual "collapse to grid" behavior (if any) remains unverified. This matters
directly for pad-hit recording fidelity and is a good next diagnostic target.

## Buffer-clear-on-record (deliberate, not a bug)

`---recordOn` triggers an unconditional `clear` to `---thisBuffer` on every record start. This
is a **known, deliberate placeholder**, per explicit user confirmation: "a clear buffer is
essential for a clean capture... we know it should be rolling but haven't figured the best
mechanism yet... if a session goes out of control, it ensures there is a way to reinitialise."
Do not remove or "fix" this without discussing first — the target design (progressive,
tape-style erase just ahead of the record head) is understood but not yet built.

## Not yet built / open items

1. **`reverse_mode`'s audible-effect mystery** — highest priority open item, genuinely unsolved.
2. **Sequenced ping-pong rebuild** — still timer-based; unsequenced was rebuilt on real signal
   data per user direction, sequenced should likely follow the same pattern once a real
   sequenced-position signal source is identified (may not exist as cleanly as karma~'s own
   position report — needs investigation).
3. **Pad-hit recording, full live test** — reconnected to the correct source, untested
   end-to-end with recording engaged.
4. **Quantize-grid collapsing behavior under rapid/simultaneous hits** — untested.
5. **LED indicators on pad buttons** — requested, not yet scoped or started. Needs a
   conversation about what state(s) should be reflected (currently-armed slice? last-triggered?
   record state?) before building.
6. **Reset live.button visual indicators on release** — requested, not yet scoped. Needs
   clarification on which buttons are affected and whether they're currently stuck-lit or just
   momentarily wrong.
7. **`p MessagesToKarma` internals** — never traced in depth; likely relevant to resolving the
   reverse_mode mystery, since it's a confirmed real modulation point in karma~'s actual speed
   chain.

## Known cosmetic / harmless items (deliberately left alone)

- Two orphaned objects in `oneShotCalculation` (a dead literal message box acting as a
  passive "probe" of the slice-duration calc, and one fully disconnected message box) —
  confirmed harmless, present since before this session, left in place at user's request
  ("who knows when we might need it... already proved useful").
- A second, fully disconnected sender to `---recordOn` (`obj-50`) — dead code, harmless,
  not touched.
- Old `DEBUG_*` print objects — noisy but harmless, unchanged from project's prior state.

## Hardware controller — EMP16

Full protocol reference: `05_EMP16_Controller_Reference.md`. Summary: channel 10, Note type
pads with aftertouch, confirmed note ranges via real MIDI-OX capture (20–35 independently
confirmed as Bank D; 36–51/52–67/68–83 confirmed to be pad data but letter assignment is
inference). **Hardware LED feedback: resolved, not achievable.** Thoroughly tested this
session (full 16-color × 16-pad sweep, both Note On/Off, on-device LIGHTS menu variations,
MIDI Device Inquiry SysEx — no reply, verified by direct log inspection) — no working method
found, no documented protocol, no community firmware project for this specific device. Do not
re-attempt without new information; see `05_EMP16_Controller_Reference.md` for the full record.

## Newly-built features, this session (second half)

- **Waveform position overlay**: ✅ confirmed working. 16 translucent pale-orange rectangular
  panels, one per slice, positioned exactly over the waveform display's own boxes (**not** the
  pad-trigger buttons — their coordinates differ; see architecture file), showing which slice is
  currently playing. Built on karma~'s real live position report (same signal ping-pong uses).
  Confirmed tracking correctly during mouse clicks on the grid, reverse, and punch-in. Took an
  extended debugging chain to get working — see changelog Phase 10 and the architecture file's
  `route` int/float writeup for the real root cause.
- **MIDI-trigger-disc tinting**: ✅ confirmed working. 16 translucent pale-orange **circular**
  panels (matching the pads' actual round shape — an earlier square version was a visual
  mismatch, caught and fixed), positioned over the `pad_trigger_N` buttons, wired directly off
  the same proven show/hide messages as the waveform overlay (no separate logic). Lets the
  existing blue "struck via MIDI" state show through underneath. Considered, but deliberately
  did not implement via `live.button`'s own `activebgcolor`/`activebgoncolor` attributes
  directly — the risk of not being able to safely restore the button's true default color was
  the deciding factor at the time. **That risk is now resolved**: the actual default values were
  confirmed via the Inspector — `bgcolor`/`activebgcolor` (off states) are both plain black,
  `activebgoncolor` (the one visible during normal struck-pad use) is blue, `bgoncolor` is grey
  and not currently in play. A future session could switch to direct button recoloring using
  these now-known-safe values, if avoiding the manual bring-to-front step becomes worth it —
  not necessary given the current panel-based approach already works.
- **`RowSelect`/`ColorScheme` UI elements removed**, freeing presentation-view space. Their
  entire backend (a substantial, complete, but currently-dead Push-specific per-slice LED
  pipeline — see architecture file) is fully preserved, untouched, and still traceable if
  needed later.

## `p glitching`'s `gen~` engine — now partially decoded

Contains a genuine, direction-aware per-slice position generator, with `floor(position × 16)`
as one of its three outputs (i.e. it independently computes the current slice index, separate
from anything built this session). Full detail in the architecture file. Not fully decoded —
the `counter`/`history`/`sah` stages remain unclear — but confirmed structurally relevant to
the `reverse_mode` mystery (see below), since it demonstrates the glitch engine's output
genuinely depends on direction.

## `reverse_mode` "no audible effect" mystery — resolved

Was never a signal-chain bug: the `live.button` labeled "Pingpong" in the UI was actually wired
to the real `reverse_mode` logic, and the button labeled "Reverse" was actually wired to
`back_forth_mode` (ping-pong). Every historical test had been exercising the wrong feature from
the one being reported on. Full detail and the still-open follow-up (only one button confirmed
audible post-relabel, not both) is in the changelog's Phase 10 and the "Reverse / back-forth /
punch" section above.

## Instant-play preroll buffer — investigated, not built (pick up in a future session)

**The idea**: currently, hitting record waits for the full loop-length buffer (1–4 bars) to
fill before playback/looping begins — capture only starts on record-press, loop start = the
button press moment. Proposed fix: a continuously-running preroll capture while armed, so the
full buffer already exists the instant record is pressed, with an instant handoff to the "real"
loop rather than a fill-wait. Confirmed this is a real architectural bottleneck, not a
red herring (not quantize-to-transport or unrelated latency).

**What was ruled out or de-risked this session**:
- karma~'s default "record until buffer full, then auto-switch to playback" behavior is the
  object's own native behavior (confirmed via Rodrigo Constanzo's own forum posts), not a
  ChopChop inefficiency.
- Dynamic buffer repointing via `set <bufferName>` was flagged as a real M4L-specific risk from
  older web-sourced bug reports (buffer~ read errors specific to Live, not standalone Max) —
  but this is now substantially de-risked: `ChopChop_v1_DEV.amxd` already uses `set
  ---thisBuffer` successfully, confirmed working in the actual current environment (Max 9,
  Live 12), via `p INIT`'s loop-size-change handler (`r ---size` → stop → re-`set` the same
  buffer name, to force karma~ to re-sync its understanding of a resized buffer — not a
  two-buffer swap, but proof the message itself works reliably here).
- `p Playback > p BufferSwitching` contains a **second, currently unused** buffer allocation
  (`buffer~ ---dummy 200 2`, mono... actually stereo, 200ms) — zero connections anywhere in the
  file. This looks like the start of a genuine two-buffer switching mechanism that was never
  finished/wired up. Worth investigating its history/intent before building something new from
  scratch — check whether the changelog or a much older version of the file sheds light on
  what it was originally for.
- karma~'s inlet/outlet layout, from the object's own assist tooltips: inlets = 0/1 signal
  recording input (L/R), 2 signal speed; outlets = 0/1 signal output (L/R), 2 status list —
  `position (0.–1.), play-state (int), record-state (int), start-position (ms),
  end-position (ms), window-size (ms)`.

  **CORRECTED — the tooltip description of element 3 does not hold in this device.** Read live
  on the running device, element 3 sits at `0.00` in every state tested, including after a
  resize and after a Reloop jump. It does not carry a usable region start. A build was made on
  the strength of this line and the region always drew from slice 1 because `s` was always 0.

  The question is moot in any case: the device never sends `position` or `jump` on the
  length-change path, only `window`, so karma~ places the region itself at the start of the
  capture. The loop is always the first `n` slices. See §2 of
  `18_ChopChop_v6_174_Architecture_and_Audit.md`.

  Element 0's coordinate space is also **not settled**. The `karma-coordinate-conventions`
  skill file calls it region-relative starting at 0; removing the `− ---regionStart`
  subtraction that the playhead chain performs on it (v6_149) produced progressive drift, a
  stuck chase and unresponsive clicks. Whatever it is, that subtraction is load-bearing.

  Elements 4 and 5 are reliable: a four-bar capture requested at 13714 ms read 13712.31 on
  both. karma~'s loop comes out about 1.7 ms short of the request — consistent, small, and
  worth knowing before treating `---size` and the real loop length as identical.

  Note that `---sliceLengthMs` is **misnamed**: it is fed from `karma_window_cache`, which is
  element 5, the window in milliseconds. It is not a slice length.
- karma~'s `append` message (documented, real): extends an *already-created* initial loop,
  not useful for eliminating the wait before the first loop exists. But noted as potentially
  useful for a bootstrap approach — create the smallest possible initial loop (near-zero wait),
  start playing it immediately, then `append`+`record` to grow it to the real desired length
  while already audibly looping. Unverified whether this is glitch-free in practice.
- A `rezer~` external exists (by "raja", via Cycling '74 forums) — purpose-built for separate
  record/play heads, closer to the ideal shape of this problem than repurposing karma~. Not
  recommended to switch engines given how much of ChopChop's existing architecture (reverse,
  ping-pong, punch, the glitch engine) is built specifically around karma~'s behavior — noted
  as a fallback reference only if karma~-based approaches hit a wall.
- **A from-scratch isolated test harness (separate .amxd, not touching ChopChop) was attempted
  to empirically determine what happens when initial recording runs past the buffer's
  allocated size without an explicit stop — this was not resolved.** The harness repeatedly
  threw "patchcord inlet/outlet out of range" errors that did NOT go away even after
  stripping the connections down to bare minimum (just message controls + report reading, no
  audio in/out, no speed signal). Given karma~'s real inlet/outlet layout is now confirmed
  correct (see above) and matches what the harness assumed, **the actual cause of those errors
  was never found** — worth debugging properly in a future session, or abandoning the
  from-scratch harness entirely in favor of testing directly against a duplicated copy of the
  real, working `ChopChop_v1_DEV.amxd` (agreed as the better path going forward regardless).

**Recommended next steps for a future session**: (1) test the buffer-boundary question
directly on a duplicated ChopChop device rather than a from-scratch harness; (2) investigate
`---dummy`'s history/original intent; (3) if pursuing the buffer-swap design, prototype it
against the now-confirmed-working `set` mechanism already proven in this file, rather than
external, possibly-stale forum reports.
