# Severity Contract

> What a validator or critic finding means, what to do with it, and which findings stop a save. Every behavioral claim was checked against `src/maxpat/validation.py`, `src/maxpat/critics/` and `src/maxpat/hooks.py`. Section 7 (live findings) was checked against `tools/max_verify_live.py`.
> Path: `.claude/skills/references/severity-contract.md`. Console errors MAX prints at load time are in `troubleshooting.md`; proven MAX forms are in `proven-forms.md`.

## 1. Two systems

| | Validator | Critics |
|---|---|---|
| Entry point | `validate_patch(patch, db=None, allowed_packages=None, *, scope=None, target_version=None, patch_path=None, original=None)` | `review_patch(patch_dict, code_context=None, ext_code=None, ext_archetype="message", *, db=None, is_new=False)` |
| Result type | `ValidationResult` with `layer`, `level`, `message`, `proposed_removal`, `path`, and the structured identity `rule`, `box_ids`, `port` (plus the legacy `auto_fixed` flag) | `CriticResult` with `severity`, `finding`, `suggestion` (plus `rule`, `box_ids`, `port`, `path` and an optional quick-fix `fix`) |
| Question it answers | Is the patch mechanically valid? (JSON shape, objects exist, cords in range, domain rules, embedded GenExpr) | Is it well designed? (gain staging, fan-out, layout, contrast, device rules) |
| Levels | `error`, `warning`, `info` | `blocker`, `warning`, `note` |

`validate_patch` runs Layer 1 (json), Layer 2 (objects, plus maxclass usage, package gating and community extraction), Layer 3 (connections), Layer 4 (domain rules), Layer 4c (vocabulary checks), Layer 4b (domain restrictions) and Layer 5 (GenExpr inside the codeboxes of every gen patcher embedded in a scope). It runs these layers on the top level and then on every embedded patcher (`p`, embedded bpatcher / poly~, gen~ / mc.gen~ `data.patcher`, rnbo~ ...), each with its own scope; a nested result carries `path` (the box-id chain, `obj-1/obj-2`) and a `[p synth > gen~] ` message prefix. A gen scope skips Layers 4 and 4c. A Layer 1 error stops that scope and every scope under it: nothing after it runs there.

Every result carries a non-empty `rule` (for example `unknown_object`, `outlet_out_of_bounds`, `line_tilde_comma`, `expr_clip`, `bpatcher_numeric_args`), `box_ids` (`(src, dst)` for a cord, the box for a box finding, `()` for a scope finding) and `port` (an int or None). The save gate keys on these (section 5).

**`patch_path=`** (the file the patch is loaded from or saved to) makes an unknown object an `objects` **error**, unless `NAME.maxpat` / `.js` / `.gendsp` sits beside the patch or anywhere in its `patches/<project>/` tree (case-insensitive): then there is no finding. Without it, an unknown object stays a warning. The save gate and `validate_file` always pass it.

**`original=`** (the patch as loaded, when *patch* is an edit of it) gives each Layer 5 codebox its loaded code, so `validate_genexpr(original=...)` reports tab lines already in a loaded codebox as one warning and only new tab lines as an error. Without it, every codebox is generated code and every tab is an error. The save gate passes the baseline.

Layer 3 skips type/role checks (the `Unverified outlet types` warning, role-tier warnings, `Signal outlet to control-only inlet`) for a known companion pair (`relationships.json`) and for a cord listed in `idioms.json` -- a cord the bundle's own help patches ship, keyed by both names, both ports and the source outlet's signal class. Bounds, missing-box and malformed-cord errors are never skipped. A cord whose port is non-int, bool or negative, or whose box id is unusable, is a `Malformed patchline` error with a proposed removal. Both MC signal flavours (`signal`, `multichannelsignal`) count as signal; an `inlet` box source is never type-checked; the destination inlet is resolved from the box's args (`record~ buf N`), and any inlet a shipped help cord feeds with a signal accepts a signal from every source.

`target_version="9.0"` (opt-in, Q38) adds a `version` layer in max scopes only (nested max-scope patchers included): a `warning` for a box whose `min_version` is newer than the target, and for a cord on a port the target build lacks according to `version_io.json`. It never emits an error, so it never blocks `has_blocking_errors` or a save. When the target is at or before the last build known to lack the port, the warning reads "is lost on Max X"; when it falls between that build and the first build known to have it, "may be missing on Max X ... (changed between A and B)". An unparsable target raises ValueError.

`review_patch` always runs the DSP, structure and layout critics. It adds the RNBO critic when an `rnbo~` box is present, the M4L critic when `plugin~`, `plugout~` or `live.thisdevice` is present, the package critic when package objects are present, and the external critic when `ext_code` is passed. A patch whose only M4L marker is `live.thisdevice` (no `plugin~`, `plugout~`, `midiin` or `midiout`) is a helper abstraction: the M4L critic runs its per-scope checks and parameter-name uniqueness on it, never the device completeness or device quality checks. Every critic reviews every scope (top level, `p`, bpatcher, poly~, gen~, rnbo~ patchers); a nested finding carries `path` (the box-id chain, `obj-1/obj-2`) and a `[p synth] ` prefix on its `finding`.

**`is_new`** changes exactly one critic result: the structure critic's uninitialized-state finding (Q24: a UI value holder that reaches DSP with nothing setting it at load -- no parameter initial value, loadmess / loadbang path, pattr restore or slaved gain~ input) is a `blocker` with `is_new=True` and a `warning` with `is_new=False` (the default). Pass `is_new=True` whenever the reviewed patch will be saved as a new file -- `/max-build`'s critic loop, and any flow that creates a file -- because the save gate reviews a file with no baseline with `is_new=True` (section 5). Reviewing a new file with the default would approve a warning that the gate then refuses. Keep the default for edits of an existing file (`/max-iterate`, `/max-verify`): a pre-existing uninitialized control then stays a warning, and the gate only refuses one the edit introduces.

Layer 4c (Q23) checks vocabulary in non-gen scopes:

- **errors**: `expr` / `vexpr` / `if` calling `clip()` (`expr_clip`, max scope); a bpatcher whose `args` hold numeric strings (`bpatcher_numeric_args`);
- **warnings**: a message selector the destination does not list (`message_selector`, max scope; containers, scripts, gen hosts and `bach.` / `cage.` / `dada.` / `ears.` destinations are never judged); a patcher that sets `editing_bgcolor` / `locked_bgcolor` but no `bgcolor` (`patcher_bgcolor`).

Layer 4 also errors on a message into `line~` where a ramp segment (2+ tokens) is followed by another comma segment (`line_tilde_comma`, every scope): only the last ramp plays. A leading jump (`0, 1 500`, `stop, 0 100`) gets no finding. A `*~ 0` / `mc.*~ 0` whose gain inlet is unfed counts as a mute terminator for unterminated chains. A `Comment` `#N` warning skips prose (5+ words with sentence punctuation).

## 2. Validator levels

| Level | Meaning | Blocks `has_blocking_errors(results, is_new=True)` | Blocks with `is_new=False` | Blocks a save |
|---|---|---|---|---|
| `error` | Will not load or will misbehave in MAX | Yes | Yes, unless it carries a `proposed_removal` | Yes, when the save introduces it (section 5) |
| `error` with `proposed_removal` | An invalid cord (malformed, missing endpoint box, out-of-range index, signal outlet into a control-only inlet) | Yes | No, it is reported only | Yes, when the save introduces it |
| `warning` | Suspect but loadable | No | No | No |
| `info` | Diagnostic (detected I/O, handlers found) | No | No | No |

Examples, as the validator reports them:

- `error`: `'osc~' is a Pure Data object, not MAX. Use cycle~ instead.`
- `error`: `'expr~' exists only in ['rnbo'] -- No such object in a max patcher. Use it inside an rnbo~ patcher.`
- `error` with a proposal: `Outlet index 5 out of bounds on 'obj-1' (has 1 outlet(s)) -- proposed removal (not applied; see apply_fixes)`
- `warning`: `Unknown object: 'zzfoo~' -- not in database` (an `error` when `patch_path` is passed and no abstraction resolves it)
- `info`: `gen~ 'obj-1' codebox: Detected I/O: 1 input(s), 1 output(s)`

**Without `patch_path`, an unknown object is only a warning and does not block** `has_blocking_errors`. The save gate and `validate_file` pass the path, so there an unresolved unknown object is an error: a new file holding one is refused, and an edit that adds one is refused (a pre-existing one still saves). Save an abstraction before the patch that uses it. Rule #1 still forbids it. Treat `Unknown object` as must-fix before saving: replace the name with one the database knows, or flag it with `// UNKNOWN OBJECT: [name] -- not in database, verify manually` and tell the user. A Pure Data name, an RNBO- or Gen-only name at Max scope, and a `domain_restricted` violation are all errors.

The `ValidationResult` docstring also lists a level `"fixed"`. Nothing emits it. `auto_fixed` is a legacy flag that `validate_patch` never sets. `has_blocking_errors` still ignores a legacy `auto_fixed` error that has no proposal.

## 3. Proposed removals

- `proposed_removal` is the 4-tuple `(src_id, src_outlet, dst_id, dst_inlet)` of a cord the validator considers invalid, in the scope named by the result's `path` (`""` at the top level).
- `validate_patch` never mutates its input, and a dict and a Patcher give the same results. A proposal is data. No cord has been removed.
- Inspect, don't save. A proposed removal is one of two things:
  - a real defect: fix the patch (wrong index, wrong object, a missing `snapshot~` or `sig~`);
  - a validator false positive: fix the checker or the database (`overrides.json`), never the committed patch.
- `apply_fixes(patch, results)` is the only code path that removes cords. It removes each proposed cord from the lines of the scope its `path` names (never from another scope holding the same 4-tuple) and returns what it matched: the 4-tuple for a top-level cord, the 5-tuple `(path, src_id, src_outlet, dst_id, dst_inlet)` for a nested one. Run `validate_patch` again afterwards, because removing a cord can change other findings.
- Validate a `copy.deepcopy` of the dict anyway, as the skills say. It costs nothing and protects you from any future checker that does mutate.

```python
import copy
from src.maxpat.validation import validate_patch, has_blocking_errors, apply_fixes

results = validate_patch(copy.deepcopy(patch_dict))
proposals = [r.proposed_removal for r in results if r.proposed_removal]
if has_blocking_errors(results, is_new=True):
    ...  # fix the patch; call apply_fixes(patch_dict, results) only for a confirmed defect
```

## 4. Critic severities

| Severity | Generation loop action | Patch or code change |
|---|---|---|
| `blocker` | Revision request to the generator, with `finding` and `suggestion` | The generator fixes it |
| `warning` | Reported to the user in the review summary (finding plus suggestion) | None |
| `note` | Reported to the user in the review summary (finding plus suggestion) | None |
| uninitialized-state (`rule == "uninitialized_state"`) | A `blocker` (revision request) with `is_new=True`, a `warning` (report only) with `is_new=False` | The generator initializes the control at load when it is a blocker |

Critic findings added in v6.0.0 (all report-only): the structure critic's `unmatched_names` warning (a send / receive, send~ / receive~, `; name` target, value or buffer name with no partner, checked once per review over closed patch trees; `#N`, `---` and numeric names are ignored), `int_truncation` warning (a float source into arg-less `+ - * /`, arg-less `ftom` or an int-range `scale`) and `mc_bare_list` note (a bare numeric list into an `mc.*` object that takes `applyvalues`); the M4L critic's `duplicate_device_io` warning (two `plugin~` / `plugout~` / `midiin` / `midiout` / `live.thisdevice` at the device top scope) and the Q40 device rules `stereo_out`, `midi_passthrough`, `shortname_unique`, `int_param_range`, `param_range` (which checks `parameter_initial` only when `parameter_initial_enable` is set), `bank_refs` and `device_height` (warnings) plus `shortname_length` (note). In the DSP critic's gain-safety check, a `*~` is judged as a gain stage only when its other inlet carries audio and its output does not reach an oscillator inlet or a filter's cutoff / Q / delay inlet (`lores~`, `svf~`, `onepole~`, `reson~` 2-3, `comb~`, `allpass~`, ...), so FM depth and LFO-to-cutoff modulation pass.

Warnings and notes are never written into the output: no `comment` boxes in the patch, no comments in GenExpr or JavaScript. Committed user patches would collect dozens of comment boxes that need deleting by hand, and none of the user-confirmed patches carry them. The summary is where the user reads them and decides.

The soft-limit "accept" option in the critic loop is the user's explicit confirmation to keep the remaining blockers. They are listed in the report. A new file that still holds a blocker then needs `force=True` to save (Rule #7: force only with the user's confirmation).

## 5. What blocks a save

`save_patch_roundtrip(patch_dict, path, original_text=None, *, force=False)` and `write_gendsp(code, path, num_inputs=None, num_outputs=None, *, force=False)` run the same save gate before anything is created, written or committed.

1. **Stale check first** (`save_patch_roundtrip` only). When `original_text` is given and the file on disk no longer equals it, `StaleFileError` is raised before the gate runs. Re-read with `read_patch(path)` and re-apply the edit.
2. **Blocking set.** `validate_patch` (with `patch_path=path` and, when there is a baseline, `original=baseline`) and `review_patch` run on deepcopies with one cached database. Blocking findings are every validator `error` (proposed removals included; a legacy `auto_fixed` error without a proposal excluded) plus every critic `blocker`. Warnings, info and notes never block. The `.gendsp` and `.genjit` suffixes validate in gen scope, `.rnbopat` in rnbo scope.
3. **Baseline.** `original_text`, else the file at `HEAD` in git, else the file on disk. With none, the file is new: `review_patch` runs with `is_new=True` (an uninitialized control reaching DSP is then a blocker -- section 1) and every blocking finding refuses. A file with a baseline is reviewed with `is_new=False`.
4. **Matching.** A finding with a non-empty `rule` and `box_ids` keys on its origin, `rule`, sorted box ids (plus the proposed-removal ids), `port`, `proposed_removal` and scope `path` (`""` at the top level), so a reworded message keeps its key. Otherwise the key falls back to the text template (box ids, quoted names and numbers masked) plus its box ids and `path`. Gate patcher paths key on box id + maxclass, never the box text, so renaming a subpatcher changes no key; `replace_box` keeps the box id, so a pre-existing blocker on a replaced box still matches. Keys are counted as a multiset: a finding blocks only when the new patch has more of that key than the baseline. Pre-existing findings save, so load-edit-save cycles on user patches that already hold third-party objects are not refused.
5. **Port x-rank.** A subpatcher or abstraction `inlet`/`outlet` that exists in both versions and changes x-rank refuses the save, because parent cords address ports by x-rank. A port appended rightmost is fine.
6. **Removed cords.** Cords in the reference (HEAD and `original_text`) that are missing from the new patch emit one `SaveGateWarning` listing them. It never refuses. Confirm the removal was intended.
7. **Refusal.** `PatchValidationError` with `.findings` (the new `ValidationResult` / `CriticResult` objects), `.port_changes` and `.path`. Nothing was written. Swapping inlets and renaming the same subpatcher in one edit is also refused. Separately, `finalize_patch(is_new=True)` (before any save) raises `LayoutRefusedError` (a `ValueError`) on a MAX-saved patcher or one over the box limit, before any box moves: pass `force_layout=True` for a large new build, `is_new=False` (or `edit_patch`) for anything read from disk.

   A no-op save writes nothing: when the new dict is identical to the file (`maxjson.json_identical`), `save_patch_roundtrip` keeps the original text byte for byte (any layout: MAX 9.1+ inline arrays, Max 5-9.0.x tabs, CRLF, the framework's expanded arrays), and an `edit_patch` session with no change skips the gate, the write and the commit.
8. **`force=True`.** Saves anyway and emits a `SaveGateWarning` listing what was bypassed. Use it only with the user's confirmation.
9. **Scope of the walk.** Blocking findings come from every scope, not just the top level: the validator runs its layers on every embedded patcher (Q19) and every critic reviews every scope (Q20), so a blocker inside `[p sub]`, a bpatcher, a poly~ or an rnbo~ patcher refuses a save that introduces it, exactly like a top-level one. A nested finding is tagged with its `path` (and a `[p sub] ` prefix), which is part of its gate key, so a nested blocker never matches a top-level baseline finding. The removed-cord and port x-rank checks also walk every embedded patcher.

`write_js(code, path)` has no gate. It writes and auto-commits first, then returns the code-validation results. An `error` there (for example `outlet() index 3 out of bounds`) is reported, never blocking. Read the returned list and fix it.

### Summary

| Finding | Generation loop | New file save | Edited file save |
|---|---|---|---|
| Validator `error` | Fix | Refused | Refused if the edit introduced it |
| Validator `error` with `proposed_removal` | Inspect: fix the patch or the checker | Refused | Refused if the edit introduced it |
| Validator `warning` (incl. `Unknown object` without `patch_path`) | Fix when it breaks a rule (Rule #1) | Saved | Saved |
| Unresolved unknown object (gate passes `patch_path`) | Replace it, or save the abstraction first | Refused | Refused if the edit introduced it |
| Validator `info` | None | Saved | Saved |
| Critic `blocker` | Revision request | Refused | Refused if the edit introduced it |
| Critic uninitialized-state | Revision request when reviewed with `is_new=True` (a new file), else report | Refused (blocker on a new file) | Saved (a warning on an edit) |
| Critic `warning` / `note` | Report in the summary | Saved | Saved |
| Port x-rank change | Restore the order | n/a | Refused |
| Removed cord | Confirm it was intended | n/a | Saved with `SaveGateWarning` |

## 6. Code and RNBO validators

`validate_genexpr`, `validate_js` and `validate_n4m` (`src/maxpat/code_validation.py`) emit `error`, `warning` and `info` at layer `code`. Standalone, through `validate_code_file(path)` or `write_js`, they are report-only and never block. `validate_code_file` treats a file on disk as loaded code (tab lines warn); pass `loaded=False` right after writing generated code (every tab is an error). GenExpr inside a codebox of any gen patcher embedded in a `.maxpat` (top level or nested) is different: Layer 5 feeds those findings into `validate_patch`, so a GenExpr `error` there (for example `delay()` in a codebox, a function after a statement, or a new tab line) refuses a save that introduces it. A function declared after a declaration only (no statement before it) is a warning; tabs already in a loaded codebox are one warning. `write_gendsp` does not run the GenExpr checks on its own codebox through the gate, so a `.gendsp` with `delay()` is written. Run `validate_code_file(path)` on it, or check the code with `validate_genexpr` before writing. `validate_rnbo_patch` (`src/maxpat/rnbo_validation.py`) emits `error` for objects not compatible with RNBO, for an unknown export target and for external file references, and `warning` for target limits (param count, buffers on embedded targets). It is not part of the save gate. Act on its errors before export.

## 7. Live findings (`/max-verify --live`)

Live findings come from `tools/max_verify_live.py`, which loads each top-level patch in the running MAX 9.2 through the max-bridge and maps every `tools/max_bridge.py check` report with `map_findings`. They are report-only: never part of the save gate (section 5) or the critic revision loop (section 4), never written into the patch, never auto-fixed. The bridge's own `exit_code` / `verdict` is not the severity: the bridge counts unsupported outputs and shot failures as findings, and here they are notes.

| Live finding (report field) | Severity | Notes |
|---|---|---|
| `errors_distinct[].key` containing one of the four `ERROR_WORDINGS`: `no such object`, `bad argument`, `failed to compile`, `can't assign` | blocker | MAX's own console confirms what a validator `error` only predicts. Suggestion by wording: the object DB and `troubleshooting.md`; the argument form; `genexpr-rules.md` for gen~ compile errors |
| any other `errors_distinct` entry | warning | runtime or environment error (missing file, port in use) or a post from another open patch |
| `record.flags` `nonfinite` / `runaway` | blocker | NaN/inf or runaway output: dangerous at the speaker |
| `record.flags` `clipping` / `dc_offset` / `silent` | warning | loadable but audibly wrong; `silent` usually needs a stimulus |
| `record.flags` `sr_changed_during_run` / `short_recording` | note, and every other record flag of that patch is demoted to note | the audio driver restarted or DSP stopped: measures unreliable, rerun |
| `record.warnings` (`sr_header_mismatch`) and report `warnings` (`dsp_state_unknown`, a channel above 2 left untapped, `--note: no notein or kslider to drive`) | note | informational; the analysis already corrected itself |
| `unsupported` (`mc.dac~`, `plugout~`, `poly~`, `pfft~`, `bpatcher`) | note (`not tapped: ...`) | a coverage gap, not a defect |
| `shot.error` | note | grant Screen Recording to the terminal app |
| `closed` is False | warning | the temp copy's window may still be open: close it WITHOUT saving |
| `feedback_suspected` | warning | the event cap tripped (console flood): the error list may be incomplete |
| DSP already on (`dsp_before` 1) for a locked audio-input patch | note | its input was live during the load |
| the patch's original is open in MAX | note; the patch is skipped | shared names and ports would collide; the user's window is never closed |
| an exception while checking one patch | warning (`live check crashed`) | the loop goes on with the next patch |
| `guard_input` refused the path | note; status `refused` | |
| the patch file is not a readable patch (truncated JSON, undecodable bytes, `{"patcher": 3}`) | note; status `refused` (`cannot read <path>: ...`) | the batch goes on with the next patch |
| `verdict` `bridge_failed` after a good pre-flight | none: the run is `aborted` | MAX stopped answering (a modal dialog, a crash, the toggle switched OFF); the remaining patches are "not checked" |

**Exit codes** of `tools/max_verify_live.py`: 0 ran with notes only; 1 any live blocker or warning; 2 skipped (no bridge patch in the install, MAX not running, the bridge did not answer), aborted, or a usage error.

**Summary rule.** `/max-verify --live` never changes the static Summary line's counts. The live counts sit beside it: `(live: b blockers, w warnings, n notes)`, or `(live check skipped: <hint>)` / `(live check aborted: <hint>)`.

A live blocker is MAX confirming what a validator error predicts. Fix it through `/max-iterate`, then rerun.
