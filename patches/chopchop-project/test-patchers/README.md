# ChopChop scratch verification patchers

Regenerate: `python ../tools/build_test_patchers.py`. Max 9 standalone, DSP on.
All 5 files must stay in **one folder** (t2/t3 load `voice.maxpat` by name).

Third rewrite. Everything is now a **synthesised blip** (`cycle~ * line~`
envelope) — no `buffer~`, no `poke~`, no `play~`, no file loading. So the only
thing t2/t3 test is: *does `poly~` route a trigger to a voice that makes
sound?*

## Run in this order

1. **`t0_sanity.maxpat`** — no `poly~` at all. Click `ezdac~`, then `blip`.
   - **Hear a 330 Hz tone each click** → audio path is fine, go on.
   - **Silent** → it's DSP/audio setup (audio not enabled, wrong output device,
     sample rate) — *not* the patch. Fix that first; nothing else will sound.

2. **`t2_poly_attack.maxpat`** — `poly~ voice.maxpat 4`. Click `ezdac~`, then
   `fire` (sends `midinote 60 110`).
   - **Blip fires, tight, no lag vs the metro click** → `poly~` slice layer is
     viable; report how the attack looks on the `scope~`.
   - **`poly~` object is red** → it can't find `voice.maxpat` (keep the folder
     together).
   - **`poly~` loads but silent** → click the **`bang`** box next to `fire`
     instead, and tell me which of the two produces sound. That isolates whether
     `midinote` voice-routing is the problem vs the voice patch itself.

3. **`t3_poly_steal.maxpat`** — machine-gun the six `midinote` boxes → at most
   4 blips overlap (older cut). `target 2, 1` then a note → `VOICE` prints `2`.

4. **`t5_detonate_rhythm.maxpat`** — no `poly~`. `transport 1`, metro toggle on.
   `record`, tap a rhythm on the 4 pads, `start` replays — do the replayed
   clicks land where you tapped, against the same metro? Then `write t5.mid`,
   `read`, `start` again.

## Not tested here (answered from docs / the device itself)

- **`groove~`/`play~` reading a `buffer~` while `record~` writes it** — standard
  Max; the slice layer reads committed regions behind the record head. Fine.
- **karma~ loop-definition from a running capture, `ramp`/`snramp` seam** — a
  karma~ question, so it's prototyped inside a **duplicated copy of the real
  device** in Phase 3–5, never a from-scratch patcher (doc 02: that has failed
  every time).
- **`phasor~ @1n @lock 1 → delta~ → <~ -0.5 → edge~ → onebang` bar-edge** — the
  device's `p RollingB` and `p Record_And_Quantize` already use this exact chain
  and run. Reuse verbatim.
