---
phase: quick-261022-pqu
verified: 2026-10-22T00:00:00Z
status: human_needed
score: 13/13 must-haves verified in the codebase; Live behavior unconfirmed
behavior_unverified: 0
gaps: []
human_verification:
  - test: "Drag q40-live-check.amxd onto an empty MIDI track (lower track volume first)"
    expected: "Loads as an Instrument in the instrument slot, no load error"
    why_human: "Only Live can show whether it loads (assumption A3 kind code, A5 meta=0)"
  - test: "Move freq and amp"
    expected: "Continuous dials, not 0/1 steps (Q15 item)"
    why_human: "Dial behavior in Live"
  - test: "Watch the track meter"
    expected: "Audio on both L and R (gen~ outlet 0 into plugout~ 0 and 1)"
    why_human: "Live audio routing"
  - test: "Open the Parameter Banks window (double-click live.banks) or Push"
    expected: "Four banks: Filter (freq, Filter Envelope Amount), Amp (amp, Out Gain), Pitch (Octave, Pitch Envelope Amount), Envelope (Attack)"
    why_human: "Push banks without per-box parameters/buttons entries (assumption A1)"
  - test: "Check ModMode in a clip envelope"
    expected: "freq Absolute, others None; user decides the default for add_m4l_device (None) vs add_m4l_gen_synth (Absolute)"
    why_human: "User decision, Live behavior"
  - test: "Read the dial units"
    expected: "freq in Hz, Attack in ms, Out Gain in dB, Octave integer -2..2 in steps"
    why_human: "Unit rendering in Live"
  - test: "Read the two Envelope Amount dials"
    expected: "Short names Amount and Amount2"
    why_human: "Live display"
  - test: "Load the device untouched, then change Out Gain/Octave, save a Live preset and reload it"
    expected: "220 Hz tone audible on load without touching Out Gain; reload restores level and octave. Silence means the live.thisdevice init chain does not fire or a banged dial does not re-output (assumption A2)"
    why_human: "Live init and preset-restore sequencing"
  - test: "Look at the device in presentation"
    expected: "Nothing clipped at the 169 px height"
    why_human: "Visual"
---

# Quick 261022-pqu (Q40): M4L device builder and .amxd export Verification Report

**Goal:** `add_m4l_device(kind=...)` with stereo wiring, live.thisdevice init chain, inferred param types/units, unique short names, Push parameterbanks, `.amxd` export verified against a bundled .amxd, critic checks, and EXPERIMENTAL marking until the user confirms it in Live.
**Status:** human_needed. Every code-level truth holds. Whether Live loads and behaves as expected cannot be checked here. Q15 (261014-d13) is still unconfirmed, and the user chose to proceed.

## Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Golden test committed before the refactor, in its own commit with no src/ file | VERIFIED | 4fb424e4 touches only the test and fixture; it is the parent of 4c19488d (which adds m4l_device.py). I ran the golden test in a temporary worktree at 4fb424e4: 9 passed. The golden files are unchanged from 4fb424e4 to HEAD, and the test passes at HEAD, so the refactored add_m4l_gen_synth is key-order-identical. |
| 2 | parse_amxd/build_amxd chunk codec, byte round trip, refuses frozen/invalid input | VERIFIED | I round-tripped kicksynth-m4l.amxd (103996 B), Max.app's fourin_fourout.amxd and q40-live-check.amxd byte-for-byte. Parser source reviewed (ciph, mx@c, truncated, trailing bytes, unknown kind, bounds checks); tests pass. No Live app templates were found on this machine, so that comparison was not independently re-run. |
| 3 | export_amxd writes ampf + meta 0 + ptch (dumps_max + `\n\0`) | VERIFIED | Code reviewed. The committed q40-live-check.amxd has header `616d7066 04000000 69696969 6d657461 04000000 00000000 70746368 bf540000` and its decoded payload equals q40-live-check.maxpat JSON. Mismatch/suffix/kind errors raise before the write. |
| 4 | add_m4l_device wiring for three kinds | VERIFIED | Built all three. instrument: midiin + unwired plugout~. audio_effect: plugin~ 0->plugout~ 0 and 1->1. midi_effect: midiin->midiout. detect_m4l_device_type returns the right kind each time. audio_source feeds plugout~ 0 and 1 (live-check device: obj-1:0 -> obj-3:0 and 1). |
| 5 | Param spec to live.dial, type/unit inference with explicit override | VERIFIED | Probe: Cutoff = Float/Hertz, Mix = Float/Float, Steps (1..8) = Int/Int, "Attack ms" = Float/Time. Source reviewed: whole-token matching, Int span <= 255. |
| 6 | Unique short names | VERIFIED | Live-check device has "Amount" and "Amount2" for the two Envelope Amount dials. Probe: "Attack ms" -> "Atk ms". |
| 7 | live.thisdevice init chain | VERIFIED (structure) | Probe: thisdevice:0 -> `t b b b b` -> each dial. Live-check device: `t b b b b b` to the 5 unbound dials; gen~-bound freq/amp get no init cord. Runtime behavior is a human item. |
| 8 | Push parameterbanks plus a single live.banks | VERIFIED (structure) | Probe output shows banks and one live.banks. Pure `plan_push_banks` is used by the builder and organize_push_banks (test_m4l_polish green). |
| 9 | Presentation grid and device props | VERIFIED | Dials at [8+52c, 8, 44, 48]; device height rule implemented. |
| 10 | add_m4l_gen_synth delegates to add_m4l_device, output unchanged | VERIFIED | Golden passes; test_m4l_gen_synth.py passes unedited. |
| 11 | 8 non-blocking critic rules | VERIFIED | Source has all 8 rule functions. Probes: stereo_out fires on a mono plugout~; bank_refs fires on a stale bank ref; shortname_length fires as a note. None of the 8 fires on add_m4l_device output or on q40-live-check.maxpat. (My first probe passed no device_type and returned [], my error.) |
| 12 | Live check device covers Q15 + Q40, built with the builder, polished, committed | VERIFIED | q40-live-check.maxpat/.amxd committed in 7291277e. validate_patch shows only an info line. The critic returns no findings. |
| 13 | EXPERIMENTAL marking and doc limits | VERIFIED | Module docstring, export_amxd docstring, critic docstring and CLAUDE.md M4L section all say EXPERIMENTAL. CLAUDE.md is 28536 B (<= 30000). test_doc_signatures green. |
| 14 | Regression gate | VERIFIED | I re-ran the full suite: 6281 passed, 5 xfailed, 1 xpassed, rc 0. This matches the SUMMARY and exceeds baseline 6127 by the 154 new tests. No tracked-file changes remain (`git status` shows untracked files only), no stash, no worktree left. |

## Anti-patterns

No TBD/FIXME/XXX/TODO/HACK in m4l_device.py, m4l_critic.py, m4l_polish.py or tests/test_m4l_device.py.

## Observations (not gaps)

- On add_m4l_device output the existing (pre-Q40) rule "live.dial missing info text" warns. That is expected and unrelated to the 8 new rules.
- An instrument built with add_m4l_device and no audio_source has an unwired plugout~ (silent), as Live's own template does. This is by design.
- Stale docs remain, as SUMMARY lists: dispatch-rules.md ("there is no .amxd writer"), shared-capabilities.md, the max-patch-agent/max-ui-agent/max-critic skills, TECHNICAL.md. This is a deferred doc follow-up, not a Q40 gap (plan rule 8).
- Assumptions A1-A5 (parameterbanks without per-box entries, banged live.dial re-outputs, kind-code only, 8-char short names, meta = 0) are unconfirmed until the Live session.

## Human verification required

The 9 items in the frontmatter, one Live session with `q40-live-check.amxd`. Confirming items 2-5 also closes Q15's open human_verification (261014-d13). Until then Q40 stays EXPERIMENTAL.

---
_Verified: 2026-10-22_
_Verifier: Claude (gsd-verifier)_
