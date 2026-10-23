---
quick_id: 261022-ud6
work_package: WP3 (critics)
status: complete
branch: worktree-agent-a36c656cb6a5c3ccf
plan_head_before: 8ddcdc49
commits: 5
python: 3.10.19 (uv venv) and 3.14.2 -- full suite green on both
---

# WP3: critics regression fixes

Every finding in `review-critics.md` is fixed or, where locked, documented.
On the committed corpus, the review result changes in one place only: the
`slot.maxpat` fan-out false positive. No new blocker appears.

## Findings

| ID | Status | How | Commit |
|---|---|---|---|
| CR-01 | fixed | A `*~` / `mc.*~` is judged only as a gain stage. The other inlet must carry audio: a ramp (line~, curve~, sig~, adsr~, number~), a constant `*~ k` with inlet 1 unfed, or a control cord does not count. An unwired inlet 0 counts as audio. The box's signal output must also not reach an oscillator inlet (cycle~, saw~, rect~, tri~, phasor~ and mc. forms), directly or through signal arithmetic / mtof~. A scaled ramp is still traced: `line~ -> *~ 0.5 -> *~` is judged at the real gain as the product (`_ramp_seeds`). | d05b0316 |
| WR-04 | fixed | Same oscillator-target gate: an FM / vibrato depth in Hz on `*~` inlet 1 passes. | d05b0316 |
| CR-02 | fixed | `_branch_hits` no longer expands a box that a branch enters only at a DB-cold inlet. `_meeting_boxes` now needs one branch at inlet 0 and another at a cold inlet. The insert_trigger constraints use the same cold test, and `trigger_fix` still maps first-fired to the highest outlet. `_check_fan_out_without_trigger` takes `dbh`. `_paths_reconverge` was removed. | 40ba779d |
| CR-03 | fixed | The gen~ box is compared with the highest `in N` / `out N` operator. A wired codebox counts only through `inK` / `outK` ports it uses but nothing wires (the add_gen layout with `num_inputs` too low). `code_context` is a fallback used only when no wired codebox has code. Codeboxes in series pass, and so do param-fed ones. | d05b0316 |
| CR-04 | fixed | `/max-build` (`.claude/commands/max-build.md`; the skill file the brief named does not exist) and max-critic `SKILL.md` + `references/critic-protocol.md` now call `review_patch(..., is_new=True)` for new files. The default stays `False` (the edit-safe choice; see Decisions). The `review_patch` docstring is updated. | e3f1a648 |
| WR-01 | fixed | `_outlet_atoms` reads the saved `outlettype` first. The DB `type` is used only when that entry is missing or `""`. A DB `signal_role == "list"` vetoes to unknown, and `signal_role` is never an atom count (zplane~, mc.range~, seq~ symbol outlet). | 40ba779d |
| WR-02 | fixed | `live.thisdevice` without plugin~ / plugout~ / midiin / midiout is detected as `M4L_ABSTRACTION` (`"m4l_abstraction"`). It runs the per-scope checks and parameter uniqueness only. `export_amxd` refuses it with ValueError, because `_code_for` rejects an unknown kind. | 3aec392d |
| WR-03 | fixed | severity-contract.md: the §1 signature gains `is_new`, a new `is_new` paragraph explains the Q24 new-file blocker, and the helper-abstraction dispatch and nested `path` tagging are covered. §4 gets an uninitialized-state row. §5.3 notes that the baseline sets is_new. §5.4 adds `path` to the gate key. §5.9 now says nested scopes block. The summary table gets a new row. | e3f1a648 |
| IN-01 | fixed | The midpoint check uses `_stored_rect` and sanitised port counts (`_port_geometry`). | 3aec392d |
| IN-02 | fixed | The hot/cold check skips the equal-outlet case when the fan-out check reports that outlet (`_fan_out_owns`, sharing `_fan_out_branches`). | 40ba779d |
| IN-03 | fixed | Removed `_MIDI_RANGE_SOURCES`, `_NORMALIZER_NAMES`, `_is_normalizer` and `_parse_line_tilde_targets` (dsp), plus `_is_trigger_object` and `_is_signal_object` (structure). The 4 `_is_normalizer` tests are replaced by one behaviour test: expr / vexpr stops the trace. | d05b0316, 40ba779d |
| IN-04 | fixed | Each `@out` character maps to the cord's llll outlet, ranked among the DB outlets that are not bangs. `t`, `m` and `x` are readable. An outlet index past the string length takes the last character. | 3aec392d |
| IN-05 | documented | Locked D-01, behaviour unchanged. A design-note comment in `_check_uninitialized_state` proposes the clock-stop refinement. | 40ba779d |
| Q4 gap (gain~ before plugout~ inside `[p chain]`) | note only | Deliberately scope-local (Q20). This is already documented in `_check_gain_plugout`, and the code is unchanged. | -- |
| Q24 gap (new-file blocker outside the gate) | fixed | Covered by CR-04 + WR-03: `review_patch(is_new=True)` is the documented loop call. | e3f1a648 |
| Q26 follow-up: event-only RNBO | fixed | An rnbo~ with midiout / noteout / ctlout / bendout / pgmout / touchout / outport / out and no out~ now gets a note. With no output at all, it is still a blocker. | 3aec392d |
| Q26 follow-up: number/flonum theme fills | handoff | `THEME_FILL_MAXCLASSES` lives in `src/maxpat/aesthetics.py`, outside WP3 ownership. See Handoffs. | -- |

Allowlist: `tests/review_blocker_allowlist.json` loses the slot.maxpat `fan_out_without_trigger` entry. It was a false positive: the setbuffer -> js path enters `expr` obj-150 only at its cold inlets 1 and 2, so the bang never reaches waveform~ obj-4 inlets 2 and 3. That fan-out is now a warning. `test_allowlist_key_includes_path` now uses the remaining unsafe-gain entry.

## Decisions

- **`is_new` default kept `False`.** The save gate always passes it explicitly. The other callers (`/max-iterate`, `/max-verify`, calibration and integration tests) review existing files, and with `True` every committed patch would show its pre-existing uninitialized controls as blockers (79 on the corpus). The build loop passes `True` explicitly instead.
- **An unwired `*~` inlet 0 counts as audio.** It is the not-yet-wired audio input of a gain whose control inlet is fed. This keeps the legacy ctlin -> `*~ 1.` inlet 1 fixtures blocking.
- **Filter-cutoff modulation is not covered by CR-01.** The oscillator gate follows the reviewer's fix. An LFO `*~ depth` -> `+~` -> `lores~` inlet 1 with a Hz-range flonum is still judged as a gain. This is a possible follow-up that needs a per-object table of frequency inlets.

## Tests

- New: `tests/test_ud6_critics_dsp.py` (12), `tests/test_ud6_critics_structure.py` (10), `tests/test_ud6_critics_devices.py` (21), `tests/test_ud6_critics_docs.py` (4). Each was red before its fix. The CR-02 fix-order case was checked against the old semantics, which gave a cyclic constraint and no fix.
- Updated to the corrected behaviour, each with a comment citing the finding:
  - `test_critics.py`: `line~ -> *~ 1.` with no audio operand; the normalizer tests.
  - `test_critic_fixes_e5_e8.py`: the `*~ 1.` unit-arg case; the same-outlet fan-out is no longer duplicated.
  - `test_critics_recursive.py`: preorder paths.
  - `test_critic_precision.py`: the slot fan-out is a warning.
  - `test_critic_revival.py`: the thisdevice-only patch is an abstraction.
  - `test_quickfix.py`: `@out nt` replaces `@out tn`.
  - `test_integration_patches.py`: the allowlist key test.
- Full suite: **6332 passed, 5 xfailed, 1 xpassed** on Python 3.10.19 and on 3.14.2.
- Corpus (`review_patch` over all 78 committed `.maxpat` / `.maxhelp` / `.gendsp` files plus the Q40 check device, `is_new` False and True):
  - The only diff from the base is the slot.maxpat fan-out, which went from blocker to warning.
  - Blockers: is_new=False 2 -> 1 (the allowlisted slot unsafe-gain entry). is_new=True 81 -> 80 (79 uninitialized_state + that 1).
  - No crashes, and the calibration projects have zero blockers.

## Handoffs

- **WP1 (validation):** review-validation WR-04. `_check_unterminated_chains` in `validation.py` should exempt a `*~` whose first argument is 0 and whose inlet 1 is unfed. I did not touch `dsp_roles.chain_terminal_names`, because the rule depends on arguments and the check lives in validation.py.
- **WP1 (DB):** the `bach.slice` DB entry lists 1 outlet, but the refpage has 2 (left and right llll). The `zplane~` outlets 1-3 have `type: float` but `signal_role: list`, and the refpage says "List of Zero Coordinate Pairs". `mc.range~` outlet 1 has the same type/role disagreement.
- **Owner of `aesthetics.py` (WP2 / WP8):** the Q26 follow-up on theme fills for uncolored `number` / `flonum` / `textbutton`. `THEME_FILL_MAXCLASSES` is still `{newobj, message, umenu}`, and adding classes changes contrast results, so it needs MAX confirmation first.
- **Owner of `m4l_device.py`:** `export_amxd` on a helper abstraction raises the generic "unknown device kind 'm4l_abstraction'". A clearer message would help ("a live.thisdevice-only patch is a helper abstraction; pass kind=").

## Doc impacts for WP8

- CLAUDE.md "What validator and critic findings mean" only points to the severity contract, so no change is needed there. The M4L section could mention that a `live.thisdevice`-only helper abstraction is not a device (`detect_m4l_device_type` -> `m4l_abstraction`).
- `.claude/commands/max-iterate.md` steps 15 and 124 call `review_patch(patcher.to_dict())`. That is correct for edits, but any iterate flow that creates a new file (a new abstraction) should pass `is_new=True`. Consider one line there; it is not in my file set.
- `.claude/commands/max-verify.md` keeps the default (`is_new=False`). Optionally note that `/max-verify` on a never-saved patch should pass `is_new=True`.
- `proven-forms.md` / `genexpr-rules.md`: no change.

## MAX confirmation items

1. bach `@out` with fewer characters than llll outlets: the critic assumes the last character repeats. The refpage says only "one character for each llll outlet". Check in MAX with `bach.slice 2 @out t` -> outlet 1 -> `print`.
2. bach `@out m` and `x` are treated as readable by plain MAX objects. `m` is documented as Max-format and `x` as no output.
3. An event-only rnbo~ (MIDI out, no out~) loads and exports without an audio outlet. This is the reason it is now a note rather than a blocker.

## Self-Check: PASSED

- Files exist: `src/maxpat/critics/{dsp,structure,m4l,layout,package,rnbo}_critic.py`, `tests/test_ud6_critics_{dsp,structure,devices,docs}.py` and `.claude/skills/references/severity-contract.md`.
- Commits d05b0316, 40ba779d, 3aec392d and e3f1a648 are on `worktree-agent-a36c656cb6a5c3ccf`, plus this SUMMARY commit.
