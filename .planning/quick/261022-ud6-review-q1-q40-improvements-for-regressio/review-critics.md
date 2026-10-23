---
area: critics (src/maxpat/critics/*, src/maxpat/dsp_roles.py)
range: 0f96a6f1..8ddcdc49
reviewed: 2026-10-22
depth: deep
files_reviewed_list:
  - src/maxpat/critics/__init__.py
  - src/maxpat/critics/base.py
  - src/maxpat/critics/fixes.py
  - src/maxpat/critics/dsp_critic.py
  - src/maxpat/critics/structure_critic.py
  - src/maxpat/critics/layout_critic.py
  - src/maxpat/critics/m4l_critic.py
  - src/maxpat/critics/rnbo_critic.py
  - src/maxpat/critics/package_critic.py
  - src/maxpat/critics/ext_critic.py
  - src/maxpat/dsp_roles.py
findings:
  blocker: 4
  warning: 4
  info: 5
  total: 13
status: issues_found
---

# Critics regression review (Q1-Q40)

## How this was checked

- `review_patch` run over all 63 committed `.maxpat` / `.maxhelp` files under `patches/` (HEAD), plus every `.gendsp`. The same files were also run through the base critics (`git archive 0f96a6f1` extracted to a scratch dir).
  - At HEAD there are 2 blockers, both allowlisted in `slot.maxpat`. The base had 79 blockers.
  - No calibration project has a blocker. There are no crashes on committed files.
- The committed Q40 check device (`.planning/quick/261022-pqu-.../q40-live-check.maxpat`) and `add_m4l_device` (all 3 kinds) / `add_m4l_gen_synth` reviewed with `is_new=True`: zero blockers.
- Critic test files: 675 passed.
- I ran 26 malformed-input cases (empty / None / str patchers, missing ids, bad rects, non-str text, bad ports, odd bpatcher / mc.gen~ / rnbo~ / M4L / panel shapes) with `is_new` False and True. Only IN-01 crashes.
- Both allowlists were audited. `review_blocker_allowlist.json` has 2 entries; both reasons are sound true positives (an order dependence by box position, and deliberate +1.66 dB headroom). In `uninitialized_state_allowlist.json` every entry is a warning with a category reason, which matches the Q24 decisions.
- Every finding below was reproduced by running the code. The repro shapes are inline, as raw box/line dicts through `review_patch(..., db=ObjectDatabase())`.

## BLOCKER

### CR-01: Unsafe-gain trace blocks frequency/pitch scaling into `*~` (Q26)
**File:** `src/maxpat/critics/dsp_critic.py:679-697` (inlet-0 seeding and the `*~ k` base op), `:740` (threshold)

**Defect:** Q26 extended the trace to inlet 0 of every `*~` / `mc.*~`, and folds the `*~ k` argument in as a multiply. The critic never asks whether that `*~` is a gain stage on the audio path. A control ramp scaled into Hz is therefore reported as an unsafe gain.

**Repro:** `[0, 1 1000(` -> `line~` -> `*~ 440.` -> `+~ 220.` -> `cycle~` -> `*~ 0.2` -> `dac~` gives:
`[blocker] Unsafe gain source: message '0, 1 1000' (obj-1) reaches '*~' (obj-3) inlet 0 via line~ with values up to 440`.
`save_patch_roundtrip` of that new file raises `PatchValidationError` and writes nothing (checked on a scratch path). `[220 500(` -> `line~` -> `*~ 2.` gives the same blocker.

**Failure scenario:** any new or edited patch with a pitch sweep, a ramp scaled to Hz, or an FM ratio done with `*~ k` is refused at save.

**Fix:** only judge a `*~` as a gain when its other operand is audio, i.e. a signal cord into the other inlet from a non-ramp source. If neither inlet carries audio, skip the box. Also skip it when its output reaches the frequency/phase inlet 0 of an oscillator (`cycle~`, `saw~`, `phasor~`, `rect~`, `tri~` and the `mc.` forms). A `*~ k` with k > 1 and an unfed inlet 1 is arithmetic, not a gain: do not seed it.

### CR-02: Fan-out "reconvergence" ignores hot/cold, so orders that cannot matter become blockers (Q3, Q39)
**File:** `src/maxpat/critics/structure_critic.py:254-288` (`_branch_hits`), `:291-303` (`_meeting_boxes`, line 301)

**Defect:** the check reports a meeting whenever two branches reach one box at *different* inlets. It never checks that a hot inlet is involved. It also keeps expanding past a box that a branch entered at a DB-cold inlet, which emits nothing.

**Repro 1 (both cold):** flonum -> `pack 0. 0. 0.` inlet 1, and flonum -> `* 2.` -> `pack` inlet 2. Result: `[blocker] ... paths reconverge on 'pack' (obj-3) at different inlets`. Nothing outputs either way. The Q39 `insert_trigger` fix is still attached, and its order is arbitrary because there is no hot branch.

**Repro 2 (through a cold inlet):** flonum -> `+ 0.` inlet 1 (cold), and flonum -> `* 2.` -> `pack 0. 0.` inlet 1. `+` -> `pack` inlet 0, and `+` is driven elsewhere (`metro` -> `f` -> `+` inlet 0). Result: a blocker on `pack`, although branch 1 never reaches it.

**Failure scenario:** these blockers refuse saves for new files, and for edits that introduce the shape.

**Fix:** pass `dbh` into `_check_fan_out_without_trigger`. In `_branch_hits`, record the hit but do not expand a node entered only at inlets where `_inlet_is_cold` is True. In `_meeting_boxes`, require one branch to hit inlet 0 and a different branch to hit a cold inlet (> 0). Otherwise the result is a warning.

### CR-03: The revived gen~ I/O check compares codebox ports with gen~ box ports (Q4)
**File:** `src/maxpat/critics/dsp_critic.py:186-212` with `_extract_codebox_code` at `:221-261`

**Defect:** a codebox's `in1..inN` / `out1..outN` are its own ports. The gen~ box's ports are the `in N` / `out N` operators in the gen patcher. The detector was dead before Q4. Q4 revived it with these semantics, which hold only for the `add_gen` single-codebox layout.

**Repro A:** gen~ (1 inlet). `in 1` -> codebox A (out1, out2) -> codebox B (`out1 = in1 * in2;`) -> `out 1`. B comes first in `boxes`. Result: `[blocker] gen~ I/O input mismatch: GenExpr code uses 2 inputs ... has only 1 inlet(s)`.

**Repro B:** gen~ (1 inlet). `in 1` -> codebox in1, and `param depth 0.5` -> codebox in2. Same blocker.

**Failure scenario:** MAX-authored or hand-edited gen~ patchers that feed a codebox from params, history or another codebox cannot be saved.

**Fix:** count the gen patcher's `in N` / `out N` operators (max N) and compare those with `numinlets` / `numoutlets`. Use codebox parsing only when the patcher has no in/out operators and the code comes from `code_context`. Or keep codebox parsing only when every codebox `inK` is wired from `in K`.

### CR-04: Q24's new-file blocker is invisible to the generation critic loop
**Files:** `.claude/commands/max-build.md:33`, `.claude/skills/max-critic/SKILL.md:25,49`, `.claude/skills/max-critic/references/critic-protocol.md:16` (all call `review_patch(...)` without `is_new`), `src/maxpat/hooks.py:624` (the gate passes `is_new=True` for a file with no baseline)

**Defect:** in `/max-build`'s critic loop an uninitialized control is a warning, which is "approve unchanged". `save_patch_roundtrip` on the new file then treats the same finding as a blocker and raises `PatchValidationError`. `max-critic` SKILL.md:49 says "the critic loop should already have cleared them, so the gate is a backstop". For Q24 that is false.

**Failure scenario:** a dial cabled to gen~ with no loadmess or parameter initial is a common shape: stereo-feedback-delay has 8 and tape-wobble has 11, each a warning at HEAD. Such a build passes review and is then refused at step 6.

**Fix:** pass `is_new=True` in the build loop (`/max-build`, and any skill flow that writes a new file). Document it in the max-critic protocol. `/max-iterate` on an existing file keeps the default.

## WARNING

### WR-01: `$N` arity trusts the DB's `signal_role` / type over the MAX-saved `outlettype` (Q21)
**File:** `src/maxpat/critics/structure_critic.py:806-815` (`_outlet_atoms` step b)

**Defect:** `role == "float"` counts as 1 atom even when the DB `type` is `list`. The DB also wins over the box's own saved `outlettype`.

**Repro:**
- `zplane~` outlet 1 -> `[zeros $1 $2(` gives `[blocker] Message $N arity ... supply at most 1 atom(s)`. The refpage digest for that outlet is "List of Zero Coordinate Pairs".
- `mc.range~` outlet 1 -> `[$1 $2(` gives the same blocker. The refpage says `type="list"`, but the DB says `('list', role 'float')`.
- `seq~` outlet 2 (symbol) is counted as 0 atoms, because `role == "trigger"` is checked first.

**Fix:** check the saved `outlettype` first. Use the DB only when that is missing, and only its `type` (`bang` = 0; `int` / `float` / `symbol` = 1). Ignore `signal_role`, which is a validator concept, not an atom count.

### WR-02: A `live.thisdevice` abstraction is reviewed as a MIDI effect missing midiin/midiout (Q4)
**File:** `src/maxpat/critics/m4l_critic.py:99-118`, `:55-59`, `:296-303`

**Repro:** a helper `.maxpat` with `inlet`, `live.thisdevice` -> `t b` -> `outlet`, and no plugin~ / plugout~ gives:
- `[blocker] M4L midi_effect missing required object: midiin`
- the same blocker for `midiout`
- two `device_quality` warnings

**Failure scenario:** M4L helper abstractions and bpatcher faces commonly use `live.thisdevice` for init. Saving a new one is refused.

**Fix:** infer `midi_effect` only when `midiin` or `midiout` is present. With only `live.thisdevice`, return a new `"m4l_abstraction"` type. That type runs only the per-scope checks (gain_plugout, parameter_*, Q40 per-scope); skip completeness and device quality.

### WR-03: severity-contract.md no longer matches what blocks a save (Q20, Q24)
**File:** `.claude/skills/references/severity-contract.md:10`, `:88` (§5.9), §4

**Defect:**
- §5.9 says blocking findings come from the top-level patcher, plus Layer 5 and the M4L duplicate-param check. Since Q19/Q20, every critic and the validator review every nested scope, and nested blockers refuse saves. Checked: a `t b i` -> `pack` trigger-order blocker inside `[p sub]`, and an `osc~` inside `[p sub]`, are both reported.
- The §1 signature omits `is_new`.
- Nothing documents Q24's warning-on-edit / blocker-on-new rule, which is the only critic whose severity depends on the call.

**Fix:** update §1, §4 (add an `is_new` row) and §5.9 (nested scopes block, tagged by `path`). Fold in CR-04's loop rule.

### WR-04: Modulation-depth `*~` fed from a bounded UI source is still a gain blocker (pre-existing, kept by Q26)
**File:** `src/maxpat/critics/dsp_critic.py:521-524`, `:688-690`

**Repro:** `cycle~ 5` -> `*~ 100.` inlet 0, flonum (min 0, max 500) -> inlet 1, then `+~ 440.` -> `cycle~` -> `*~ 0.2` -> `dac~`. Result: `[blocker] Unsafe gain source: 'flonum' ... up to 500`. Classic FM/vibrato depth in Hz cannot be saved without `sig~` (simple-fm only escapes because it uses `sig~`).

**Fix:** the same gate as CR-01: the `*~` output must not feed an oscillator's frequency/phase inlet.

## INFO

### IN-01: Layout midpoint check crashes on a malformed `patching_rect`
**File:** `src/maxpat/critics/layout_critic.py:241-249`

`patching_rect: 5` raises `TypeError: object of type 'int' has no len()`. `["a","b","c","d"]` raises a `TypeError` in `sizing._port_x`. The code is pre-existing, but since Q20 it runs in every nested scope, and the save gate gets an exception instead of findings.

**Fix:** use `_stored_rect()` (already in the file) for both ends.

### IN-02: One defect is reported twice
**File:** `structure_critic.py:478-492` vs `:672-696`

`number` -> `+ 1` inlets 0 and 1 gives a fan-out blocker and a hot/cold warning ("fans out to both in undefined order") for the same cords.

**Fix:** skip the `c == h` hot/cold case when one source outlet feeds the target directly (the fan-out check owns it).

### IN-03: Dead code left by Q26 and Q33
- `dsp_critic.py`: `_MIDI_RANGE_SOURCES` (68-72), `_parse_line_tilde_targets` (374-391) and `_NORMALIZER_NAMES` / `_is_normalizer` (75, 351-371). `_is_normalizer` is used only by `tests/test_critics.py`; the trace treats every expr/vexpr as unknown (806-807), so those tests pin behaviour nothing uses.
- `structure_critic.py`: `_is_trigger_object` and `_is_signal_object` (175-184). Zero references.

### IN-04: The `@out` check ignores which outlet a mode letter covers
**File:** `package_critic.py:474-476`

`bach.slice 2 @out tn` with outlet 0 (text) -> `print` gives a `bach_out_mode` warning. The attached fix rewrites it to `@out tt`.

**Fix:** map `@out` characters to llll outlets, and flag only an outlet whose character is not `t`.

### IN-05: Design note: Q24 flags state that already agrees at load
A transport toggle -> `metro` -> `[1 5 0 200(` -> `line~` is a blocker when `is_new` ("toggle drives DSP at line~"), although the toggle and the metro are both off at load. This follows the user-locked D-01 (toggles count), so it is not a bug. It is noted because, with CR-04 fixed, every new patch with a play toggle will need a redundant `loadmess 0`. Consider stopping the reach walk at a clock (`metro`, `tempo`, `qmetro`) when the holder is a toggle.

## Spec gaps

| Q | Gap |
|---|---|
| Q3 | "Blocker only when downstream paths reconverge on one box" is implemented as "different inlets", without hot/cold or cold-entry semantics (CR-02). |
| Q4 | "Flag gain~/live.gain~ on any path to plugout~" is scope-local: a gain~ inside `[p chain]` before an outlet into plugout~ is not flagged. This is a deliberate Q20 decision, documented in `_check_gain_plugout`, but narrower than the spec text. The revived gen~ I/O detector has the wrong semantics (CR-03). |
| Q24 | "Blocker on new patches" is enforced only by the save gate, not by the critic loop (CR-04). The contract is undocumented (WR-03). |
| Q26 | Gain-safety "trace both `*~` inlets" was implemented without restricting it to gain usage (CR-01). Known unresolved follow-ups from the Q26 plan, still open: theme fills for uncolored number/flonum/textbutton (`aesthetics.THEME_FILL_MAXCLASSES` is newobj/message/umenu only, unverified); `out~` severity on event-only rnbo~ (a MIDI-only RNBO patch still gets the no-`out~` blocker). |
| Q33 | "Replace the three UI-control sets with one DB-derived set": `ui_control_names()` exists, but "no consumer uses it directly yet". The three purpose sets stay, by recorded user decision PD-6. This is an approved deviation, not a defect. |
| Q32/Q26 | Dead back-compat helpers remain in the critics (IN-03). |
| Q20, Q21, Q39, Q40 | Done as specified. Recursive tagging, the trigger-type / `$N` / trigger-order probes, the four fix kinds with a contract checker, and the non-blocking Q40 device checks (stereo out, MIDI pass-through, short names, ranges, bank refs, device height) all verified by running them. |
