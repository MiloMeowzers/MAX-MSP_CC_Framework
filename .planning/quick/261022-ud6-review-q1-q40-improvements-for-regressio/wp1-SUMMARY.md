---
quick_id: 261022-ud6
work_package: WP1
subsystem: validation core + object DB
status: complete
branch: worktree-agent-a3c9d088caa4ce58e
plan_head_before: 8ddcdc496ab59093bbd9b28f74ed6e0d99e50cb9
commits: 10
tags: [validation, db, overrides, audit, save-gate]
key-files:
  modified:
    - .claude/max-objects/overrides.json
    - src/maxpat/validation.py
    - src/maxpat/db_lookup.py
    - src/maxpat/graph.py
    - src/maxpat/quickfix.py
    - src/maxpat/audit/merger.py
    - src/maxpat/audit/overrides.py
    - src/maxpat/audit/cli.py
    - tools/help_io.py            # out of ownership, see Deviations
    - tests/fixtures/help_io_baseline.json
  created:
    - tests/test_signal_inlet_evidence.py
    - tests/test_validation_malformed_ports.py
    - tests/test_validation_rule_ids.py
    - tests/test_validation_abstractions.py
    - tests/test_zero_gain_terminator.py
---

# WP1 Summary: validation core + object DB fixes (review-validation.md, tools WR-06)

Every finding in `review-validation.md` is fixed and has a regression test that failed first (red→green). The spec gaps for Q2, Q10, Q30 and Q38 are closed. Tools-review WR-06 is fixed too.

Q7/Q33 is split. The structured finding key now exists on `ValidationResult`. Switching the save gate to use it is WP2's job.

## Findings → fix → commit

| ID | Fixed | How | Commit |
|----|-------|-----|--------|
| **CR-01** | yes | **Data, from evidence.** The Max 9.2.0 bundle supplied the evidence: idioms.json, refpages, MAX-saved help/tutorial boxes and C74 abstraction sources. `overrides.json` now marks these inlets as signal-accepting: `mc.sum~` 0, `mc.selector~` 2, `mc.tapout~`/`mcs.tapout~` 1-2, `phasor~` 1, `sig~` 0, `live.remote~` 0, `mc.bands~` 0, `mcp.record~` 0, `windowed-fft~` 0, `jit.vcr` 0-1, `jit.cellblock` 0 and `pitchshift~` 2. `jit.cellblock` gets type `anything/signal` but keeps `signal:false`, so role checks still classify it as control. Every other placeholder inlet on a `~` object was filled in as control, with evidence: `live.adsr~` 5-10, `live.remote~` 1, `mc.bands~` 1-4, `mcp.record~` 1-2, `windowed-fft~` 1, `mc.receive~` 0, and `mcs.sfizz~` 0-1, which mirrors `sfizz~`. Each corrected entry carries an `_evidence` comment key.<br>**Code.**<br>• New `variable_io_rules.trailing_inlets` (non-negative int, validated at load).<br>• New `ObjectDatabase.resolve_inlet(name, inlet, args, *, count=)`. `record~ buf N` resolves to N signal inlets plus start/end. Validation resolves the destination inlet from the box's args and its saved `numinlets`. This is the Q10 gap.<br>• New `ObjectDatabase.is_shipped_signal_inlet(dst, inlet)`. Any shipped signal cord into an inlet exempts that inlet for every source, so `click~ → phasor~ 1` now passes.<br>• MC outlet flavour: every MC-family signal outlet in `overrides.json` is typed as MAX saves it (249 ports retyped). It is `multichannelsignal`, except `signal` for `mc.sum~`, `mc.unpack~`, `mc.channelcount~` 1, `mc.midiplayer~` 0, `mc.op~` 0, `mc.playlist~` 1, `mc.record~` 0, `mcs.groove~` 1 and `mcs.selector~` 0. The new `db_lookup.saved_outlet_type()` emits it, and `get_outlet_types` uses that.<br>• Layer 3's legacy check and Layer 4 (adjacency and unterminated chain) treat both flavours as signal, so MAX-saved and built MC boxes are checked the same way. An `inlet` box source is never type-checked: BEAP help ships a signal-typed inlet → `routepass`.<br>**Guards.**<br>• No shipped signal idiom may land on a control-only DB inlet. This was 25 cases; it is now 0.<br>• No unreviewed placeholder inlet may remain on a `~` object. The only reviewed exception is `pfft~` 1, a container. | 7cf7d729 |
| **CR-02** | yes | `OverrideMerger.merge()` skips proposals with no base domain entry and reports them in `merger.skipped` as `NO_BASE_ENTRY`; it no longer writes an inactive `_note`. New keys are keyed by canonical name. When an alias and its canonical name are both proposed, the canonical spelling wins and the other is reported as `DUPLICATE_OF <canonical>`. `write()` rehearses an `ObjectDatabase` load of the merged dict against a scratch root, using symlinks to the real files. If the load fails it raises `OverridesLoadError` and writes nothing. `--merge` prints the skipped proposals and returns 1 on a rejected write. `ObjectDatabase.db_root` was added. | 82bbc747 |
| WR-01 | yes | Layer 3 now treats any of these on a patchline as the existing "Malformed patchline" proposed-removal error: a port that is non-int, bool or negative, or an unusable box id. Layer 4's line loops skip these cords. A non-int saved count or a non-list `outlettype` no longer crashes. `_line_key` stays hashable. `graph._valid_port` rejects negative ports. The save gate now raises `PatchValidationError` instead of a raw `TypeError`. | 51e6fd5a |
| WR-02 | yes | `_build_count_outlet_array` seeds the io-count and empty-I/O outlet proposals by index from the DB. These paths no longer build `[""] * n` over base signal outlets. Help-saved outlettype evidence still goes through `_build_outlet_array`. | 697473db |
| WR-03 | yes | New `variable_io_rules` for `sfrecord~` (`first_arg`, default 1, all inlets signal) and `jit.catch~` (`first_arg`, default 1, 2 outlets). `sfrecord~ 4` now builds 4 inlets. | 7cf7d729 |
| WR-04 | yes | `*~` / `mc.*~` whose first argument is 0 and whose gain inlet receives no cord counts as a mute sink. This removes the 4 terrain-synth `[p terrain-view-a/b]` warnings. A driven gain inlet, a non-zero gain or `#N` still warns. The rule lives in validation.py, so there was no handoff. | ce127651 |
| IN-01 | yes | The quickfix docstring no longer claims the save gate uses `(rule, box_ids, port, path)`. `finding_key` now accepts a `ValidationResult`. The gate switch itself is WP2's (see Handoffs). | c4643d8b |
| IN-02 | yes | Implemented as fix-plan Q23 D3 to the spec's wording: `validate_patch(..., patch_path=p)` and `_project_abstractions(p)`. NAME.maxpat/.js/.gendsp found beside the patch, or anywhere in its `patches/<project>/` tree (casefolded), produces no finding. An unresolved name is an `objects` error that carries the box id. Without `patch_path` the warning is byte-identical. Every committed patch resolves all of its unknown names (0 errors). | b42a6966 |
| IN-03 | yes | A comment of 5 or more words that contains sentence punctuation is prose and is skipped. This clears 4 committed false positives. Short labels such as "Bus #1" or "Freq: #1 Hz", and punctuation-free 5-word labels, still warn. | b080a837, 202571e9 |
| IN-04 | yes | The version layer now distinguishes two cases. A target at or before `after` gets "is lost on Max X". A target inside (after, by) gets "may be missing on Max X ... (changed between A and B)". | c4643d8b |
| tools WR-06 | yes | `inlet` is now 0 inlets / 1 outlet and `outlet` is 1 inlet / 0 outlets. `Patcher.add_box` and `add_subpatcher` pick these up, with no patcher.py change needed. The save gate does not newly block anything, because Layer 3 bounds use each box's saved counts. The help-io baseline was regenerated: improvements only, no regressions. | 7cf7d729 |

### Spec gaps
- **Q2:** inlets repaired (CR-01). The outlet-downgrade cause is fixed (WR-02). The new guard covers indices past the base array.
- **Q10:** `record~ buf N` inlet layout, `sfrecord~ N` and `jit.catch~ N` are all done.
- **Q30:** the merger is load-safe (CR-02).
- **Q38:** the 25 mined idiom cords are fed back into `overrides.json`, the exemption is keyed by destination inlet, and a guard test was added.
- **Q7/Q33:** see the next section.

## Structured identity for WP2 (Q7/Q33)

`ValidationResult` now has keyword-only `rule: str`, `box_ids: tuple` and `port: int | None`, mirroring `CriticResult`. Every result that `validate_patch` emits has a non-empty `rule`. `_tag` keeps these fields on nested results, and `path` is unchanged.

Key on `(rule, box_ids, port, path)`, plus `proposed_removal` for cords.

Rule ids:

- **json:** `json_missing_patcher`, `json_missing_boxes`, `json_missing_lines`, `json_malformed_box`, `json_malformed_line`, `json_duplicate_box_id`
- **objects and packages:** `scope_restricted_object`, `pd_object`, `unknown_object`, `wrong_maxclass`, `package_not_allowed`, `package_not_extracted`, `rnbo_incompatible_object`
- **connections:** `malformed_patchline`, `missing_box`, `outlet_out_of_bounds`, `inlet_out_of_bounds`, `role_mismatch`, `unverified_outlet_types`, `signal_to_control_inlet`
- **domain:** `domain_restricted`, `genexpr_codebox`, `compound_arg_substitution`, `unterminated_chain`, `missing_gain_staging`, `unsafe_gain_value`, `feedback_without_delay`, `gen_param_at_syntax`, `comment_hash_substitution`, `line_tilde_comma`, `multislider_fetchindex`, `umenu_items_format`, `missing_assistance`
- **version:** `version_min_version`, `version_io_port` (port = the lost inlet or outlet index)

`box_ids` is `(src, dst)` for a cord, the box for a box finding, the cycle for a feedback loop, and `()` for scope-level findings.

## Tests added
- `tests/test_signal_inlet_evidence.py` (72): the CR-01 MC mixdown, both validation and the save gate; 17 valid cords; the record~ layout; anchors that must still flag; the destination-keyed idiom exemption; the two DB guards; MC flavour; the inlet-box source; WR-03 counts; WR-06 counts and bounds.
- `tests/test_validation_malformed_ports.py` (21): WR-01.
- `tests/test_validation_rule_ids.py` (~70): every result carries a rule and in-scope ids, checked across all committed .maxpat files.
- `tests/test_validation_abstractions.py` (12): IN-02 / Q23 D3.
- `tests/test_zero_gain_terminator.py` (11): WR-04.
- Additions to `test_merger.py` (+6, CR-02), `test_db_signal_ports.py` (+4, WR-02), `test_version_io.py` (+3, IN-04) and `test_critic_precision.py` (IN-03).

**Final suite:** `python3 -m pytest -q` → **6490 passed, 5 xfailed, 1 xpassed**. The baseline was 6287 passed, 5 xfailed, 1 xpassed. Run locally on Python 3.14; every changed file parses with `ast.parse(feature_version=(3,10))`.

**Sweeps:**
- `validate_patch` on all 77 committed patch files: no change versus baseline, apart from the intended IN-02, IN-03 and WR-04 removals.
- Max 9.2.0 bundle (2146 .maxhelp plus media .maxpat): Layer 3 errors went from 15 to 0, with the MC-flavour legacy check active.
- The user's external patches (~/Projects/Ambire, MUSC courses, scuffed; 257 files) and the main-tree `patches/` folder: 0 connection errors.

## Deviations
1. **[Rule 3 – blocking] `tools/help_io.py` (WP6's area).** WR-06 gave `inlet` its real 0/1 I/O. That pushed 1845 bundle inlet boxes into the oracle's outlettype comparison, and an inlet's saved type mirrors its parent cord. I added `CONTEXT_TYPED = {"inlet"}` (12 lines) so their types are not compared, and regenerated `tests/fixtures/help_io_baseline.json`: improvements only. WP6 should keep this when merging.
2. **IN-03 reversed a pinned decision.** `test_committed_prose_comment_still_warns` asserted that the barnett-dbap prose warning should stay. The review asked for it to be removed, so the test now asserts no warning on 4 committed prose comments, plus new short-label anchors.
3. **`tests/test_db_lookup.py`:** `mc.matrix~ 3 2` now expects `multichannelsignal` ×2. MAX saves it that way in the bundle help.
4. **Layer 3/4 MC flavour extension.** The old check skipped `multichannelsignal` entirely. It was extended only after bundle, committed and external sweeps all showed 0 new errors.

## Handoffs
- **WP2 (hooks.py):** switch `hooks._finding_key` to `(rule, box_ids, port, path)` + `proposed_removal` (fields above), for both ValidationResult and CriticResult; then restore the quickfix docstring claim. Also wire `patch_path=path` through `_blocking_findings`, `_gate_report` (new dict and baseline) and `_run_save_gate`, and into `validate_file`. That makes Q23 D3 effective on the save path. If WP7 owns Q23, coordinate so this lands once.
- **WP2 (patcher.py, optional):** `Box._derive_outlet_types` is effectively unreachable, but it could call `db_lookup.saved_outlet_type()` for consistency.
- **WP6 (tools):** keep `help_io.CONTEXT_TYPED`. `extract_pkg_io.py` atomic-io (tools IN-05) is unchanged here.
- **WP7 (Q23):** D3 (unknown objects / `patch_path` / `_project_abstractions`) is implemented in validation.py to the spec's wording. Build the other Q23 checks on top of it, and do not re-implement it.

## Doc impacts (for WP8; no docs edited)
- **db-maintenance.md:**
  - Document `variable_io_rules.trailing_inlets` (non-negative; 0 = every inlet repeats DB inlet 0), `ObjectDatabase.resolve_inlet`, `is_shipped_signal_inlet` and `saved_outlet_type`.
  - Explain the MC outlet typing in `overrides.json`: `multichannelsignal` versus `signal`, taken from help evidence.
  - Document the `_evidence` comment key on override entries.
  - Document the merger's new behaviour: skipped proposals, canonical keys, the rehearsal load and `OverridesLoadError`, and the `--merge` return code.
  - Note `inlet`/`outlet` I/O (0/1, 1/0).
  - Replace "gets stripped by validation" (docs WR-06).
- **severity-contract.md / TECHNICAL.md:**
  - `ValidationResult.rule/box_ids/port` and the rule-id list.
  - `validate_patch(patch_path=)`: an unknown object is an error on that path.
  - Legacy signal check: both flavours count as signal, `inlet` sources are exempt, the inlet is resolved through args, and the destination-keyed idiom exemption applies.
  - Malformed-port handling (WR-01).
  - Unterminated chains: `*~ 0.` is a mute sink.
  - Comment #N: prose is skipped.
  - Version layer: "is lost" versus "may be missing".
- **CLAUDE.md:** the MSP bullet "Always terminate ... `*~ 0.`" is now honoured by the validator, so no change is needed. In the Object Database section, consider one line on `trailing_inlets` next to `variable_io_rules`. Rule #2 is now enforceable for `inlet`/`outlet` boxes.

## Needs confirmation in MAX
- `live.remote~` inlet 0 accepting `cycle~` directly: the help ships `cycle~`/`phasor~` → 0, so the risk is low.
- `jit.vcr` inlet 1 signal: the refpage says "MSP audio in 2" and help ships `p some-noises` → 1.
- `pitchshift~ 2` inlet 2 (factor) accepting a signal: refpage type Signal, but no shipped cord.
- `sfrecord~` with no argument having 1 inlet: refpage only, because no argless help box exists.

## Self-Check: PASSED
All 5 created test files and every modified file exist on the branch. All 9 code commits are present in `git log 8ddcdc49..HEAD`: 82bbc747, 697473db, 51e6fd5a, 7cf7d729, ce127651, c4643d8b, b42a6966, b080a837, 202571e9.
