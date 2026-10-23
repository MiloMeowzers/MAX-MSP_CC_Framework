# Q1–Q40 Post-hoc Review (2026-10-22)

Range: `0f96a6f1..8ddcdc49` (249 commits). Suite: 6287 passed, 5 xfailed, 1 xpassed (non-strict xfail `test_max_saved_file_byte_identical` now passes).
Detail per area: `review-{validation,patcher,critics,codegen,dspsim,tools-release,docs-completion}.md`.

## Blockers (11 unique)

| ID | Area | Defect | Origin |
|----|------|--------|--------|
| B1 | completion | Q23 (vocabulary checks) never executed: PLAN only, no commits/SUMMARY/STATE row; 8/10 checks missing incl. `add_bpatcher` numeric args saved as `'0'` | Q23 |
| B2 | validation | Signal-accepting inlets marked control (`mc.sum~` 0, `mc.selector~` 2, `mc.tapout~`/`mcs.tapout~` 1-2, `phasor~` 1, `sig~` 0, `record~` 1) → save gate refuses valid new patches (`mc.cycle~→mc.*~→mc.sum~→dac~`) | Q1/Q7 exposed Q2/Q11 gaps |
| B3 | validation | `audit/merger.py:177-187` writes unknown-object + alias-key overrides that the Q11 loader rejects → one `--merge` breaks every DB load | Q30 vs Q11 |
| B4 | patcher | `replace_box`/`replace_box_safe` on gen~ (any embedded patcher) silently deletes the embedded patcher/code | Q29 |
| B5 | critics | Unsafe-gain trace treats every `*~` inlet 0 as gain → blocks `line~→*~ 440.→cycle~` | Q26 |
| B6 | critics | Fan-out "reconvergence" ignores hot/cold → blocks branches landing on cold inlets | Q3 |
| B7 | critics | Revived gen~ I/O check counts wrong ports → false mismatch for codeboxes in series / `param`-fed | Q4 |
| B8 | critics | `/max-build` + max-critic call `review_patch` without `is_new` → loop approves what the save gate refuses | Q24 |
| B9 | codegen | `add_m4l_device` on a patch already holding `plugin~`/`plugout~` adds a second pass-through (+6 dB) | Q40 |
| B10 | dsp_sim | Smoke `peak > 4` / silence / self-sustain checks FAIL 11 user-confirmed codeboxes (control outputs in Hz/ms, gates, triggers) | Q35 |
| B11 | docs | CLAUDE.md:96 mandates `repair_text_contrast` on edits → recolours 310 boxes in 33 committed patches (mostly default-text comments) | Q36/docs |

Plus: `math.exp2` (3.11+) in `genexpr_interp.py:1119` breaks `exp2()` on the 3.10 target (tools BL-01 / dspsim WR-04).

## Notable warnings
- patcher: `write_gendsp` with unchanged code drops an `in 1` box (granular-sched/engine); no-op save rewrites every Max 8/9.0.x file (202 tab-indented files); edit-session contrast recolours wrongly (bach.roll); `LayoutRefusedError` undocumented; `p` rename disables port-order gate.
- validation: string/float port index → raw TypeError; override generator still downgrades signal outlets; `sfrecord~ N`/`jit.catch~ N` I/O; `*~ 0.` flagged as unterminated.
- critics: `$N` atom count from DB over saved `outlettype`; helper abstraction with only `live.thisdevice` treated as MIDI effect.
- codegen: decl-order check rejects function-above-Param (C74's own gen.maxhelp); constant check misses `phi`/`PI`/…; `/max-diagnose` always suggests RNBO/Gen cause; RNBO builder `maxclass "rnbo~"` (E8 never scheduled).
- dsp_sim: `mc.gen~` codeboxes never smoked; pitch detector octave errors on narrow pulses; exit code 2 ambiguous.
- tools/release: `--live` bridge patch lives in `patches/` (excluded from release); DSP pre-flight uses bare `pytest`; `audit_db.py --json` writes; **NPM_TOKEN likely expired (90-day cap)**.
- docs: severity-contract/TECHNICAL top-level-only claims, `run_simulation` signature, `bore_only`, no `.amxd` writer claim, `finalize_patch` re-route claim, db-maintenance "strips cords".

## Release
Recommended **v6.0.0** (breaking: non-destructive `validate_patch`, save gate raises, removed `memory.py`, `is_complex_patch`, `suggest_subpatchers`, `add_node_script`, `contrast_text_color`, `bore_only`). Checklist in `review-tools-release.md`.
