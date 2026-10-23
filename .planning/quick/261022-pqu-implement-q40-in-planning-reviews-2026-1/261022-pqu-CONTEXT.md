# Quick Task 261022-pqu: Implement Q40 in .planning/reviews/2026-10-11-fix-plan.md — M4L device builder and .amxd export - Context

**Gathered:** 2026-10-22
**Status:** Ready for planning

<domain>
## Task Boundary

Implement Q40 in .planning/reviews/2026-10-11-fix-plan.md — M4L device builder and .amxd export.

Spec (fix plan, "Q40: M4L device pipeline (§5.9)"):
- `add_m4l_device(kind="instrument"|"audio_effect"|"midi_effect")` builds: stereo plugin~/plugout~ wiring; the live.thisdevice init chain; parameters with type and unit inferred from range and name (stepped integer → Int, ms → Time, Hertz, deciBel, 0–1 → Float); unique short names; Push `parameterbanks`; `.amxd` export using the header constants in `m4l_constants.py`, with the format verified against a bundled `.amxd`.
- Critic checks for the result.
- Mark it experimental until the user confirms it loads in Live.

</domain>

<decisions>
## Implementation Decisions

### Q15 gate
- The fix plan gates Q40 on Q15 being confirmed in Live. Q15 (261014-d13) is still `human_needed`: continuous dials, stereo out and Push banks are unconfirmed.
- The user chose to PROCEED anyway. Build on Q15's forms (ParamType/ModMode enums, bare plugout~ with gen~ outlet 0 → inlets 0 and 1, `patcher.parameters.parameterbanks` shape, newobj live.banks, LIVE_PARAMETER_OBJECTS).
- Everything Q40 adds is EXPERIMENTAL: say so in docstrings, the CLAUDE.md M4L section and the summary. Produce ONE Live check device/patch with a checklist that covers both the pending Q15 items and the Q40 items, so one Live session confirms both.

### .amxd export
- Add a separate `export_amxd(patcher_or_path, out_path, kind)`. The `.maxpat` stays the editable source of truth (validate/diff/roundtrip keep working); the `.amxd` is a derived binary written next to it.
- Use the AMXD_* constants in `src/maxpat/m4l_constants.py`. Verify the byte layout against a real .amxd: the kicksynth-m4l.amxd that the constants were reverse-engineered from, and/or a .amxd shipped in the Max/Live bundle. Add a round-trip test (parse a real file → re-export → byte-compare or structural compare).

### Builder API
- `add_m4l_device` is the generic skeleton: plugin~/plugout~ per kind, live.thisdevice init chain, params, unique short names, banks.
- Refactor `add_m4l_gen_synth` to call it internally. Its serialized output must stay unchanged; add a regression test comparing before/after dicts for representative inputs (Frustration directive: never regress working functionality).

### Param spec
- A list of dicts `[{name, min, max, default, unit?, type?, steps?, short_name?}]`. Infer type/unit from range and name (stepped int range → Int; ms/time → Time; freq/Hz → Hertz; gain/dB → deciBel; 0–1 → Float). Explicit keys always win. Short names are auto-made unique (Live's short-name length limit).

### Claude's Discretion
- MIDI-effect wiring details (midiin/midiout vs. plugin~ pass-through), the exact live.thisdevice init chain, the critic check list, and the module placement (builders.py vs. a new m4l_device.py) are left to the researcher and planner. All of it must be grounded in the object DB, refpages and bundle files (Rule #1).

</decisions>

<specifics>
## Specific Ideas

- The Q15 human checks to fold into the combined Live checklist are in `.planning/quick/261014-d13-implement-q15-in-planning-reviews-2026-1/261014-d13-VERIFICATION.md` (human_verification).
- The M4L rules in CLAUDE.md still apply: no gain~/live.gain~/ezdac~ before plugout~; bind live.dial to gen~ Params via param_connect.

</specifics>

<canonical_refs>
## Canonical References

- .planning/reviews/2026-10-11-fix-plan.md (Q15, Q40)
- src/maxpat/m4l_constants.py (AMXD_* header constants, enums)
- src/maxpat/builders.py add_m4l_gen_synth; src/maxpat/m4l_polish*; src/maxpat/critics/m4l_critic.py
- .planning/quick/261014-d13-implement-q15-in-planning-reviews-2026-1/ (Q15 summary + verification)

</canonical_refs>
