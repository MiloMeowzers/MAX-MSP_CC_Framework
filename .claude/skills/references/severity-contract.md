# Severity Contract

> What a validator or critic finding means, what to do with it, and which findings stop a save. Every behavioral claim was checked against `src/maxpat/validation.py`, `src/maxpat/critics/` and `src/maxpat/hooks.py`.
> Path: `.claude/skills/references/severity-contract.md`. Console errors MAX prints at load time are in `troubleshooting.md`; proven MAX forms are in `proven-forms.md`.

## 1. Two systems

| | Validator | Critics |
|---|---|---|
| Entry point | `validate_patch(patch, db=None, allowed_packages=None, *, scope=None)` | `review_patch(patch_dict, code_context=None, ext_code=None, ext_archetype="message", *, db=None)` |
| Result type | `ValidationResult` with `layer`, `level`, `message`, `proposed_removal` (plus the legacy `auto_fixed` flag) | `CriticResult` with `severity`, `finding`, `suggestion` |
| Question it answers | Is the patch mechanically valid? (JSON shape, objects exist, cords in range, domain rules, embedded GenExpr) | Is it well designed? (gain staging, fan-out, layout, contrast, device rules) |
| Levels | `error`, `warning`, `info` | `blocker`, `warning`, `note` |

`validate_patch` runs Layer 1 (json), Layer 2 (objects, plus maxclass usage, package gating and community extraction), Layer 3 (connections), Layer 4 (domain rules), Layer 4b (domain restrictions) and Layer 5 (GenExpr inside codeboxes of top-level `gen~` boxes). A Layer 1 error stops the pipeline: nothing after it runs.

`review_patch` always runs the DSP, structure and layout critics. It adds the RNBO critic when an `rnbo~` box is present, the M4L critic when `plugin~`, `plugout~` or `live.thisdevice` is present, the package critic when package objects are present, and the external critic when `ext_code` is passed.

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
- `warning`: `Unknown object: 'zzfoo~' -- not in database`
- `info`: `gen~ 'obj-1' codebox: Detected I/O: 1 input(s), 1 output(s)`

**An unknown object is only a warning and does not block** `has_blocking_errors` or the save gate. Rule #1 still forbids it. Treat `Unknown object` as must-fix before saving: replace the name with one the database knows, or flag it with `// UNKNOWN OBJECT: [name] -- not in database, verify manually` and tell the user. A Pure Data name, an RNBO- or Gen-only name at Max scope, and a `domain_restricted` violation are all errors.

The `ValidationResult` docstring also lists a level `"fixed"`. Nothing emits it. `auto_fixed` is a legacy flag that `validate_patch` never sets. `has_blocking_errors` still ignores a legacy `auto_fixed` error that has no proposal.

## 3. Proposed removals

- `proposed_removal` is the 4-tuple `(src_id, src_outlet, dst_id, dst_inlet)` of a top-level cord the validator considers invalid.
- `validate_patch` never mutates its input, and a dict and a Patcher give the same results. A proposal is data. No cord has been removed.
- Inspect, don't save. A proposed removal is one of two things:
  - a real defect: fix the patch (wrong index, wrong object, a missing `snapshot~` or `sig~`);
  - a validator false positive: fix the checker or the database (`overrides.json`), never the committed patch.
- `apply_fixes(patch, results)` is the only code path that removes cords. It removes the proposed cords in place and returns the keys it matched. Run `validate_patch` again afterwards, because removing a cord can change other findings.
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

Warnings and notes are never written into the output: no `comment` boxes in the patch, no comments in GenExpr or JavaScript. Committed user patches would collect dozens of comment boxes that need deleting by hand, and none of the user-confirmed patches carry them. The summary is where the user reads them and decides.

The soft-limit "accept" option in the critic loop is the user's explicit confirmation to keep the remaining blockers. They are listed in the report. A new file that still holds a blocker then needs `force=True` to save (Rule #7: force only with the user's confirmation).

## 5. What blocks a save

`save_patch_roundtrip(patch_dict, path, original_text=None, *, force=False)` and `write_gendsp(code, path, num_inputs=None, num_outputs=None, *, force=False)` run the same save gate before anything is created, written or committed.

1. **Stale check first** (`save_patch_roundtrip` only). When `original_text` is given and the file on disk no longer equals it, `StaleFileError` is raised before the gate runs. Re-read with `read_patch(path)` and re-apply the edit.
2. **Blocking set.** `validate_patch` and `review_patch` run on deepcopies with one cached database. Blocking findings are every validator `error` (proposed removals included; a legacy `auto_fixed` error without a proposal excluded) plus every critic `blocker`. Warnings, info and notes never block. The `.gendsp` and `.genjit` suffixes validate in gen scope, `.rnbopat` in rnbo scope.
3. **Baseline.** `original_text`, else the file at `HEAD` in git, else the file on disk. With none, the file is new and every blocking finding refuses.
4. **Matching.** A finding's key is its rule template (box ids, quoted names and numbers masked) plus its box ids. Keys are counted as a multiset: a finding blocks only when the new patch has more of that key than the baseline. Pre-existing findings save, so load-edit-save cycles on user patches that already hold third-party objects are not refused.
5. **Port x-rank.** A subpatcher or abstraction `inlet`/`outlet` that exists in both versions and changes x-rank refuses the save, because parent cords address ports by x-rank. A port appended rightmost is fine.
6. **Removed cords.** Cords in the reference (HEAD and `original_text`) that are missing from the new patch emit one `SaveGateWarning` listing them. It never refuses. Confirm the removal was intended.
7. **Refusal.** `PatchValidationError` with `.findings` (the new `ValidationResult` / `CriticResult` objects), `.port_changes` and `.path`. Nothing was written.
8. **`force=True`.** Saves anyway and emits a `SaveGateWarning` listing what was bypassed. Use it only with the user's confirmation.
9. **Scope of the walk.** Blocking findings come from the top-level patcher (plus Layer 5's codeboxes in top-level `gen~` boxes, and the M4L critic's duplicate-parameter check, which walks subpatchers). The removed-cord and port x-rank checks walk every embedded patcher.

`write_js(code, path)` has no gate. It writes and auto-commits first, then returns the code-validation results. An `error` there (for example `outlet() index 3 out of bounds`) is reported, never blocking. Read the returned list and fix it.

### Summary

| Finding | Generation loop | New file save | Edited file save |
|---|---|---|---|
| Validator `error` | Fix | Refused | Refused if the edit introduced it |
| Validator `error` with `proposed_removal` | Inspect: fix the patch or the checker | Refused | Refused if the edit introduced it |
| Validator `warning` (incl. `Unknown object`) | Fix when it breaks a rule (Rule #1) | Saved | Saved |
| Validator `info` | None | Saved | Saved |
| Critic `blocker` | Revision request | Refused | Refused if the edit introduced it |
| Critic `warning` / `note` | Report in the summary | Saved | Saved |
| Port x-rank change | Restore the order | n/a | Refused |
| Removed cord | Confirm it was intended | n/a | Saved with `SaveGateWarning` |

## 6. Code and RNBO validators

`validate_genexpr`, `validate_js` and `validate_n4m` (`src/maxpat/code_validation.py`) emit `error`, `warning` and `info` at layer `code`. Standalone, through `validate_code_file(path)` or `write_js`, they are report-only and never block. GenExpr inside a codebox of a top-level `gen~` box in a `.maxpat` is different: Layer 5 feeds those findings into `validate_patch`, so a GenExpr `error` there (for example `delay()` in a codebox) refuses a save that introduces it. `write_gendsp` does not run the GenExpr checks on its own codebox through the gate, so a `.gendsp` with `delay()` is written. Run `validate_code_file(path)` on it, or check the code with `validate_genexpr` before writing. `validate_rnbo_patch` (`src/maxpat/rnbo_validation.py`) emits `error` for objects not compatible with RNBO, for an unknown export target and for external file references, and `warning` for target limits (param count, buffers on embedded targets). It is not part of the save gate. Act on its errors before export.
