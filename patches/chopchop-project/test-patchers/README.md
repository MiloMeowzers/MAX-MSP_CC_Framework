# ChopChop scratch verification patchers (T1–T6)

Throwaway diagnostics per `chopchop-max-testing`. Regenerate with
`python ../tools/build_test_patchers.py`. Open each in **Max 9 standalone**
(not the device), DSP on, click the numbered steps left→right, read the
result, report back. `karma~` resolves because the device already uses it.

Each answers one question from `context.md` Research R7 and unblocks a
build decision.

| File | Question | Feeds decision |
|---|---|---|
| `t1_buffer_contention.maxpat` | Does `groove~` glitch/zipper/drop while `record~` writes the **same** buffer? | Whether the `poly~` slice layer can read `---thisBuffer` while `karma B` rolls into it (Phase 3/6). If yes-glitch → slice layer reads a `duplicate`d copy instead. |
| `t2_voice.maxpat` | (support file) the `poly~` voice: `bang → groove~` one-shot of a fixed ms slice. | Confirms the voice subpatcher I/O shape (`in 1` / `out~ 1` / `out~ 2` + `thispoly~`). |
| `t2_poly_vs_karma.maxpat` | Is a pre-instantiated `poly~` voice's note-on attack as tight as / tighter than a `karma~ jump`? | `groove~`-in-`poly~` vs staying on `karma~` for slice triggering (D1 L2). Record a few seconds into `tbuf` first. |
| `t3_poly_steal_choke.maxpat` | Does `target N` give a stable home voice? Does `midinote` steal sanely past 16? Does a shared note / choke group cut group-mates? | The voice-management mechanism for home-voice-per-pad + per-pad choke default + spill (D2/D3). |
| `t4_karma_loopdef_ramp.maxpat` | Defining a shorter loop from a **running** rolling capture: bare `window 0.5` vs `stop → position → window → play`. Where does the region land, any click? Then sweep `ramp`/`snramp` 16→200 at the seam. | The Phase 4/5 handoff: how `karma B`'s loop is committed from the ring, and the declick value. |
| `t5_detonate_roundtrip.maxpat` | Record `(Δtime, pitch, velocity, duration)` into `detonate` against `transport`, replay; faithful under a tempo change? SMF write/read? | `detonate` vs `coll` for the sequencer store (D1 L3 / D8). |
| `t6_bar_edge_once.maxpat` | `phasor~ @frequency 1n @lock 1 → delta~ → <~ -0.5 → edge~ → onebang`, self-re-armed: exactly one bang per bar, transport-locked, no drift over minutes? | Reusing this in-file pattern as the Phase 4 handoff trigger (satisfies rule B1 — transport-derived, not `karma~`-report-derived). |

## Notes / known limitations

- **T2/T3 voices never free.** `t2_voice` marks `thispoly~` busy on note but has no
  done-detector, so `poly~` voices stay allocated. Enough to eyeball `target` /
  `midinote` routing and stealing; not a fidelity rig.
- **T2** needs real audio in `tbuf` first (drop a file on the `buffer~`, or wire an
  input) — silent slices give nothing to judge attack by.
- **T4/T6** need the transport **running** — `phasor~ @lock 1` produces nothing with
  the transport stopped.
- If a patcher shows nothing, check every object instantiated (red = missing) before
  concluding anything about behaviour (`chopchop-max-testing`: the historical
  failures were probe faults, not real).
