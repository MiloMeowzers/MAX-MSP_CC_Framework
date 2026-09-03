# ChopChop scratch verification patchers

Regenerate: `python ../tools/build_test_patchers.py`. Open each in **Max 9
standalone** (not the device), DSP on. Step 1 is always "click ezdac", then the
numbered comments left→right. If an object box is red (failed to create),
report that first — don't judge behaviour off a broken patch.

## Why only three tests here

The first two batches over-reached. Lesson applied:

- **No karma~ in a scratch patcher.** doc 02 and `chopchop-max-testing`: a
  from-scratch karma~ harness has failed this project every time ("patchcord
  out of range", "can't load now"). Every karma~ question is deferred to a
  prototype inside a **duplicated copy of the real device**, where karma~ is
  already wired correctly.
- Questions answerable from documentation + the fact that **the device already
  does it** are not worth a Max session (see "Answered without a test" below).

## The three that need your ears/eyes

| File | Question | Decision it feeds |
|---|---|---|
| `voice.maxpat` | (support) `play~` one-shot voice: bang → play 1000–1250 ms of `tbuf` once, free the poly~ slot on `line~` done. | the voice-subpatcher shape for the `poly~` slice layer (D1 L2). |
| `t2_poly_attack.maxpat` | Fire a pre-instantiated `poly~`/`play~` voice repeatedly against a running metronome. Is the trigger→sound edge tight — no perceptible lag, clean attack on the `scope~`? | whether `poly~` one-shots can carry live pad triggering (D1 L2) instead of `karma~` jumps. |
| `t3_poly_steal.maxpat` | Machine-gun 6 notes into a 4-voice `poly~` → only 4 sound (stealing). `target 2, 1` then a note → `VOICE` print reads `2`. | the voice-management mechanism: home-voice-per-pad + choke default + spill (D2/D3). |
| `t5_detonate_rhythm.maxpat` | Tap a rhythm on 4 pads (each tap clicks + records to `detonate`). `start` replays against the same 4n metronome — do the replayed clicks land where you tapped? Then `write t5.mid` / `read` / `start`. | `detonate` vs `coll` for the MIDI-at-core sequencer store (D1 L3 / D8). |

## Answered without a test (state if you disagree)

- **T1 — `groove~`/`play~` reading a `buffer~` while `record~` writes it.**
  Standard Max; every live-looper and granular patch does it. The only artifact
  is reading the exact sample under the record head. The slice layer reads
  *committed* regions (behind the head), so no contention. → **fine.**
- **T4 — defining a shorter loop from a running karma~ capture (bare `window`
  vs `stop→position→window→play`), and the `ramp`/`snramp` seam.** Genuinely
  unresolved (karma-coordinate-conventions §3) — but this is a **karma~**
  question, so it goes to a device-copy prototype in Phase 3–5, not here.
- **T6 — `phasor~ @frequency 1n @lock 1 → delta~ → <~ -0.5 → edge~ → onebang`
  bar-edge detection.** Already proven: the device's own `p RollingB` and
  `p Record_And_Quantize` both use this exact chain and the device runs. Reuse
  verbatim for the Phase-4 handoff trigger.
