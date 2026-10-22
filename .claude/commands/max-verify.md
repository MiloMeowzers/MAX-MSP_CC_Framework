---
name: max-verify
description: Run validation and critic review on generated output
---

# /max-verify

Run the full validation pipeline and critic review on all generated files in the active project.

## Behavior

1. **Load active project** -- read `patches/.active-project.json` for the current project. If no active project, prompt the user.

2. **Find generated files** -- scan the project's `generated/` directory for all `.maxpat`, `.gendsp`, and `.js` files.

3. **Run mechanical validation** -- for each file:
   - `.maxpat` files: call `validate_file()` from `src.maxpat` to check JSON structure, object validity, connection bounds
   - `.js` / `.gendsp` files: call `validate_code_file()` from `src.maxpat` for code-level validation

4. **Run critic review** -- invoke the max-critic skill:
   - Call `review_patch(patch_dict, code_context)` from `src.maxpat.critics`
   - Collect all `CriticResult` findings across files

5. **Display results** grouped by severity:
   - **Blockers** -- must be fixed before the patch will work correctly. Suggest specific fixes.
   - **Warnings** -- potential issues that may cause unexpected behavior. Annotate with explanation.
   - **Notes** -- informational observations about style or best practices.

6. **Update status** -- record verification results in project status.

7. **Live check (opt-in, `--live`)** -- only with `--live`, and only after steps 3-5 have printed the static report:
   - Run `python3 tools/max_verify_live.py --json` plus the pass-through flags (`--record S`, `--note P V`, `--no-shot`, `--live-inputs`). Give no PATH: the tool reads the same active-project pointer and drops the abstractions and bpatcher children that a sibling references, so only top-level patches are loaded.
   - **Exit 0 or 1** -- append a "Live check (MAX 9.2):" section built from the JSON: per patch, the `LIVE BLOCKER` / `LIVE WARNING` / `LIVE NOTE` lines with their suggestions, the shot path and the run dir. Optionally Read each shot PNG to eyeball the layout, and flag visual issues.
   - **Exit 2** -- one line: `live check skipped: <hint>` (no bridge, MAX not running, toggle OFF), or `live check aborted: <hint>` plus the not-checked patches. The static report and its counts stay exactly as they were.
   - Live findings are report-only (`.claude/skills/references/severity-contract.md` section 7): never feed them into the critic revision loop, never change step 6's status record from them, and never auto-fix. Offer `/max-iterate` for the fixes.

## Live check safety

- Turn the volume down.
- Close the originals of the project's patches (the tool skips a patch whose original is open) and any unrelated patch: console posts from other open patches are attributed to the patch under test.
- The bridge patch (`patches/max-bridge/generated/max-bridge.maxpat`) must already be open in MAX with its enable toggle ON. That is the user's job: never toggle it or open the bridge patch for them (D-04). Afterwards, remind the user to turn the toggle OFF: the bridge listens on UDP 7400 on all network interfaces.
- Recorded patches switch DSP on only for the recording. Load-only patches get DSP on during the load settle so gen~ compile errors post, and the prior DSP state is restored afterwards (D-02).
- Audio-input patches (`adc~`, `ezadc~`, `mc.adc~`, `mc.ezadc~`) stay load-only with DSP untouched unless `--live-inputs` (D-01). If DSP is already on, their input is live during the load, so switch DSP off first.
- Ctrl-C mid-run skips the bridge's cleanup: DSP may stay on and a `__maxbridge_` window may stay open. Close that window WITHOUT saving.

## Skills Referenced

- **max-critic** -- critic review loop with `review_patch()` and `CriticResult`
- **max-lifecycle** -- project context and status updates

## Python Modules

```python
from src.maxpat import validate_file, validate_code_file
from src.maxpat.critics import review_patch, CriticResult
from src.maxpat.project import get_active_project, update_status
```

Live (CLI): python3 tools/max_verify_live.py [--json] [--record S] [--note P V] [--no-shot] [--live-inputs]

## Arguments

None required. Verifies all generated files in the active project.

Optional flags:
- `--live` -- after the static report, load each top-level patch in the running MAX through the max-bridge (step 7).
- `--record S` -- seconds to record a patch whose output is tapped (default 3; 0 = never record).
- `--note P V` -- the note played into `notein`, or else the first `kslider`, while recording (default 60 100).
- `--no-shot` -- no screenshots.
- `--live-inputs` -- record audio-input patches and allow DSP-on-load for them (mute mics or use headphones).

## Examples

```
/max-verify
/max-verify --live
/max-verify --live --record 0 --no-shot
/max-verify --live --live-inputs
```

## Output Format

```
Verification Results for: {project-name}
=========================================

{filename}:
  BLOCKER: {description} -- Fix: {suggestion}
  WARNING: {description}
  NOTE: {description}

Summary: {blockers} blockers, {warnings} warnings, {notes} notes
```

With `--live`, the live section follows the static report (the same lines `format_report` prints):

```
Live check (MAX 9.2): {project-name}
====================================

{filename}  [{status}; {mode}: {reasons}]
  LIVE BLOCKER: {finding} -- Fix: {suggestion}
  LIVE WARNING: {finding} -- {suggestion}
  LIVE NOTE: {finding}
  shot: {png}
  run dir: {run_dir}

Excluded: {child}.maxpat (abstraction of {parent})

Live: {lb} blockers, {lw} warnings, {ln} notes ({checked} checked, {not_run} not run)

Turn the bridge's enable toggle OFF (or close the bridge patch) when done: it listens on UDP 7400 on all network interfaces.

Summary: {blockers} blockers, {warnings} warnings, {notes} notes   (live: {lb} blockers, {lw} warnings, {ln} notes)
```

When the live check could not run, the Summary suffix is `(live check skipped: {hint})` or `(live check aborted: {hint})` instead. Live counts sit beside the static counts and are never added to them (D-03).
