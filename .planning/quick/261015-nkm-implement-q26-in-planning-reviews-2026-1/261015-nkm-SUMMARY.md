---
phase: quick-261015-nkm
plan: 01
subsystem: critics
status: complete
tags: [critics, hot-cold, gain-safety, contrast, rnbo, Q26, E5, E6, E7, E8]
requires: [Q21 trigger-order check, Q24 base 65b4a894]
provides:
  - shared-ancestor hot/cold check (E5)
  - bounds-propagating unsafe-gain trace on both *~ inlets (E6)
  - src/maxpat/dsp_roles.py DB-driven gain-stage / terminal sets (E6)
  - theme-aware text contrast in critic and generator (E7)
  - RNBO positional param names and missing in~ as a note (E8)
affects: [review_patch, validate_patch Layer 4, ensure_text_contrast, repair_text_contrast, save gate]
tech-stack:
  added: []
  patterns: [module-qualified DB-driven role sets, z-ordered panel layers, keep-passing color choice]
key-files:
  created:
    - src/maxpat/dsp_roles.py
    - tests/test_critic_fixes_e5_e8.py
  modified:
    - src/maxpat/critics/rnbo_critic.py
    - src/maxpat/critics/structure_critic.py
    - src/maxpat/critics/dsp_critic.py
    - src/maxpat/critics/__init__.py
    - src/maxpat/validation.py
    - src/maxpat/defaults.py
    - src/maxpat/aesthetics.py
    - src/maxpat/critics/layout_critic.py
    - .claude/skills/references/ui-presets.md
    - tests/test_critics.py
    - tests/test_critics_recursive.py
    - tests/test_aesthetics.py
    - tests/test_integration_patches.py
    - tests/review_blocker_allowlist.json
decisions:
  - "Hot/cold (E5) warns only when one upstream event reaches hot inlet 0 and a DB-cold inlet with the cold update at or after the last hot firing; Q21 owns targets a trigger reaches at both"
  - "Gain stages and output/chain terminals are derived from the object DB in src/maxpat/dsp_roles.py, shared by validation.py and dsp_critic.py"
  - "Unsafe-gain trace stops at unknown boxes (dbtoa, pack, +): no finding rather than a guessed range"
  - "Contrast: missing textcolor = theme text 0.85, no canvas key = 0.235, untinted newobj/message/umenu = 0.172; topmost visible containing panel wins; passing explicit colors are kept"
  - "slot.maxpat dial obj-54 -> *~ obj-9 inlet 1 (range 0 to 1.21) is a true positive, allowlisted under rule 3"
metrics:
  duration: 25m
  completed: 2026-10-15
estimate:
  tokens: 170000
  tasks: 3
actuals:
  tokens: 35440
  tasks: 3
  commits: 4
plan_head_before: 65b4a8943379d56cecc5d67069ffd24eb8019397
plan_head_after: a841a2e1e06cb1305c14bcd02a6cc53fe482dd16
---

# Phase quick-261015-nkm Plan 01: Q26 critic precision (E5-E8) Summary

This plan rewrites four critic checks:
- **E5, hot/cold:** a warning now needs one shared upstream event that delivers to the cold inlet too late.
- **E6, gain safety:** the trace reads value bounds and checks both `*~` inlets, and gain stages and terminals come from the object DB.
- **E7, contrast:** the critic and the generator now use Max 9 theme colors and only the topmost visible panel.
- **E8, RNBO:** positional param names are read, and a missing in~ is now a note.

Most of the noise is gone: committed hot/cold warnings fell from 143 to 0 and Low contrast warnings from 1090 to 56. The real defects the review named are now reported.

## Before/after finding counts, committed corpus (69 files)

From `Q/triage.py --check Q/triage-base.json Q/triage-final.json`. Mismatch was 0 after every commit (1a, 1b, 2, 3): no non-Q26 record changed in any file.

| Source | Kind | Severity | Before (65b4a894) | After (a841a2e1) | Planning expectation |
|---|---|---|---|---|---|
| review | Hot/cold inlet ordering issue | warning | 143 | 0 | 143 -> 0 |
| review | Unsafe gain source | blocker | 0 | 1 | 0 -> 1 |
| review | Missing gain staging | blocker | 0 | 0 | 0 -> 0 |
| review | Low contrast text | warning | 1090 | 56 | 1090 -> 56 |
| review | Presentation/patching contrast trade-off | note | 213 | 209 | 213 -> 209 |
| review | RNBO kinds | any | 0 | 0 | 0 -> 0 |
| validate | Unterminated signal chain | warning | 7 | 7 | 7 -> 7 |
| validate | Missing gain staging | warning | 0 | 0 | 0 -> 0 |

Every count matches the planning expectation. The 56 Low contrast warnings match the `<reference_data>` list file by file, in count and in ratio:
- amplitude-follower: 2 at 2.03 and 4 at 2.30;
- gong-engine: 1 at 1.13;
- kicksynth: 2.26 and 1.24;
- mixer-strip `[p sends]`: 8 at 1.12;
- mixer: 2.26;
- physics-composition bach.roll: 2.81;
- scala-synth: 9 flonums at 1.19 and 9 comments at 1.90;
- stereo-feedback-delay: 5 at 1.40;
- subtractive-synth: 4 at 3.98;
- tape-wobble: 9 at 1.12;
- wormhole-test: 1.35.

## Bundle (Max 9.2, 3139 .maxpat/.maxhelp files, review_patch)

| Kind | Severity | Before | After |
|---|---|---|---|
| Hot/cold inlet ordering issue | warning | 8810 | 990 |
| Low contrast text | warning | 28636 | 6676 |
| Low contrast text | note | 8 | 73 |
| Presentation/patching contrast trade-off | note | 5214 | 5710 |
| Unsafe gain source | blocker | 165 | 78 |
| Missing gain staging | blocker | 159 | 3 |
| rnbo~ (missing in~ / out~) | blocker | 1219 | 564 (out~ only) |
| rnbo~ (missing in~) | note | 0 | 655 |
| RNBO param (naming) | warning | 0 | 3 |

- Hot/cold 8810 -> 990 matches the plan's estimate of about 990.
- The RNBO change matches the plan exactly: 655 in~ blockers became notes, and 564 out~ blockers are unchanged.
- Missing gain staging dropped from 159 to 3, and live.gain~ becoming a gain stage accounts for all of it. A scratch run with only `live.gain~` added to the old set gives 2. The remaining difference is 1 new mc.dac~ hit (mc.evolve~.maxhelp: cycle~ -> mc.dac~).
- The 3 RNBO naming warnings are positional params that the old `@name`-only regex could not read.

## Planner decisions as implemented

**PD-1 (E5): the hot/cold rule** is `_check_hot_cold_ordering(scope, dbh, q21_targets)` in structure_critic.py.
- **Targets.** A box qualifies when control cords enter inlet 0 and at least one DB-cold inlet.
- **Skipped targets:**
  - `_ORDER_EXCLUDED_NAMES`, which includes p, bpatcher, js, poly~ and the other `_ALL_HOT_NAMES`;
  - any box with an embedded patcher;
  - the Q21 storage and idiom targets.
- **Upstream walk.** It runs separately for the hot cords and the cold cords. It follows only cords that enter their box at a hot inlet, that are not Jitter setter hops, and that do not leave the target.
- **Divergence.** Shared ancestors are checked in sorted id order. A box is skipped when it is an exclusive router (new `_EXCLUSIVE_ROUTER_NAMES`) or opaque (all-hot, embedded patcher, or DB-unknown).
- **Classification and hazard.** Each control out-cord of the ancestor counts as H (reaches the hot side), C (cold side) or B (both). It is a hazard when C is non-empty, H or B is non-empty, and min(C) <= min(H ∪ B).
- **Report.** One warning per target, with the `<reference_data>` texts.
- **Measured.** Corpus 143 -> 0, bundle 8810 -> 990.

**PD-2 (Q21 boundary).** `_trigger_reach(scope, t_id)` was factored out of `_check_trigger_order`, with Q21 behavior unchanged; its tests pass as before. `_q21_targets` builds the skip set.
- `review_structure` runs trigger order first and keeps the result order unchanged.
- **RCC check.** At d407da7b (v0.0.7, pre-fix), ears.slice~ obj-18 in `[p slicer]` gets only the Q21 `Trigger order: ` blocker and no hot/cold finding. At 3c9452a5 it gets neither.
- **Verdict on a difference.** Both historical RCC revisions also carry one same-outlet hot/cold warning in `[p sequencer]`. There, an `inlet` outlet fans out to `uzi` and to `zl.group` inlet 1, and `zl.group` inlet 0 is fed through `uzi` -> `- 1`. This is the PD-3 shape (fan-out in undefined order), so it is correct by the literal rule. The current committed RCC does not have it: the corpus count is 0.

**PD-3.** A same-outlet fan-out stays a hot/cold warning. `test_top_level_first_then_preorder` passes unchanged.

**PD-4 (E6): the gain trace** is `_check_unsafe_gain_sources` / `_trace_gain_inlet` in dsp_critic.py.
- **Seeds.** For each `*~` / `mc.*~` box and each inlet 0 and 1:
  - every control cord into that inlet;
  - every control cord into inlet 0 of a line~ that feeds it (these set into_line and crossed).
- **Inlet 0 with an argument.** When nothing enters inlet 1, `*~ k` starts the op chain with multiply-by-k.
- **Rules, in order:**
  1. message comma segments up to the first unescaped `;`, with only even positions read when the message feeds line~ directly;
  2. bounded sources: slider/dial, number/flonum, live.dial/slider/numbox, kslider/ctlin/notein;
  3. `* k`, `/ k`, `scale`/`zmap a b c d` (zmap clamps) and `clip lo hi`;
  4. expr/vexpr stops;
  5. trigger value outlets (i/f/l) pass the value on, a numeric argument is a constant, and other letters stop; f/float/i/int continue to the feeders of inlets 0 and 1;
  6. anything else stops.
- **Limits.** A visited set, a 64-hop limit and a 4096-state cap per (gain box, inlet).
- **Report.** One blocker per (source, gain box, inlet), with the source ranges merged.
- **Kept for back-compat:** `_is_normalizer`, `_parse_line_tilde_targets`, `_MIDI_RANGE_SOURCES` and `_NORMALIZER_NAMES`.
- **Splitter.** Q23 has not landed, so there is no `walk.message_segments`. A private `_message_segments` was added.
- **signal_role_migration floor.** dsp_critic.py still has 3 lines that contain both `outlettype` and `_SIGNAL_OUTLET_TYPES`.
- **Measured.** Corpus 0 -> 1 (the slot.maxpat true positive below). Bundle 165 -> 78.

**PD-5 (E6): `src/maxpat/dsp_roles.py`.**
- **Contents.** It defines the base vocabularies GAIN_STAGE_BASES, OUTPUT_TERMINAL_BASES and ROUTE_TERMINAL_BASES. A name, or its mc. counterpart, is kept only when:
  - the DB has an entry for it;
  - at least one of its inlets carries a signal;
  - its effective restrictions are not a subset of {rnbo, gen}.

  With `db=None` it uses one `lru_cache(maxsize=1)` default DB.
- **Resulting sets** under the repo DB are exactly the three in must_haves. `mc.plugout~` is absent from the DB, so it drops out.
- **validation.py.**
  - `_TERMINAL_NAMES` / `_GAIN_NAMES` are removed (nothing imported them).
  - `_check_unterminated_chains` now takes `dsp_roles.chain_terminal_names(db)`.
  - `_check_gain_staging` now takes `dsp_roles.gain_stage_names(db)` and `dsp_roles.output_terminal_names(db)`.
- **dsp_critic.py.**
  - `review_dsp(..., *, graph=None, db=None)`.
  - `_GAIN_NAMES` / `_TERMINAL_NAMES` stay as literal back-compat exports, pinned equal to the dsp_roles sets by a test.
  - The plugout~ suggestion names only `*~`.
- `review_patch` passes its db to `review_dsp`.
- **Measured.** The corpus is unchanged. The `add_m4l_gen_synth` output no longer gets an Unterminated warning.

**PD-6 (E7): theme-aware contrast.**
- **defaults.py:** MAX_THEME_TEXT, MAX_THEME_CANVAS_BG, MAX_THEME_BOX_FILL and MIN_VISIBLE_FILL_ALPHA.
- **New in aesthetics.py:**
  - `fill_is_visible`, `is_valid_color`, `THEME_FILL_MAXCLASSES`;
  - `resolve_patcher_background` (`_resolve_patcher_bg` delegates to it);
  - `build_panel_layers`;
  - `FALLBACK_TEXT_CANDIDATES` and `choose_text_color`.
- **Changed in aesthetics.py:**
  - `_bg_under_rect` now returns the FIRST containing layer.
  - `resolve_effective_background(..., *, maxclass=None)` applies the own-fill rules.
  - `_apply_text_contrast` writes and counts only the colors that change.
- **layout_critic.py.** A missing or invalid textcolor is read as MAX_THEME_TEXT. It uses the shared helpers for the panel layers and the patcher background.
- **Measured.** Corpus 1090 -> 56 warnings and 213 -> 209 trade-off notes, both exact.

**PD-7 (E8): RNBO.**
- `_extract_param_name`: the `@name` value wins. Otherwise it takes the first argument after `param`, unless that starts with `@` or is a number. The quote-aware `split_box_text` does the tokenizing; numbers are matched by regex, so a param named `inf` or `nan` is still read as a name.
- A missing in~ is now a note, with the `<reference_data>` text and suggestion. A missing out~ is still a blocker.

**PD-8: the existing-test edits, exactly these 7.**
1. `tests/test_critics.py::_hot_cold_ordering_issue_patch` now uses the unpack shape, and `test_hot_cold_ordering_detected` asserts exactly one `Hot/cold inlet ordering issue: '+' (obj-4)` warning.
2. `tests/test_critics_recursive.py::_hot_cold_content` now uses the unpack shape. The parity test passes, and `test_gen_scope_skips_ordering` passes unchanged.
3. `TestRnboNested::test_rnbo_in_p_without_in` now expects `("note", "obj-1")` and the new in~ text.
4. `test_line_tilde_to_signal_inlet_no_flag` is renamed `test_line_tilde_to_inlet_0_is_traced` and asserts one blocker naming inlet 0 via line~.
5. `test_section_header_on_dark_canvas` asserts that header_color is kept and that its ratio is at least MIN_CONTRAST_RATIO.
6. `test_section_header_on_light_panel`: the same assertion.
7. `tests/test_integration_patches.py` adds the `unsafe_gain` kind (`_UNSAFE_GAIN_RE`, `_blocker_match_key`, `_entry_key`). The change is additive.

## True positive allowlisted (fix-plan rule 3)

`patches/rhythmic-sampler/generated/slot.maxpat`:
- **Finding.** `Unsafe gain source: 'dial' (obj-54) reaches '*~' (obj-9) inlet 1 via line~ with values up to 1.21 (range 0 to 1.21)`.
- **Path.** The vol dial obj-54 (floatoutput 1, size 121, mult 0.01) -> `t f f` obj-166 -> `$1 10` obj-155 -> line~ obj-156 -> `*~` obj-9 inlet 1. The path was checked against the file.
- **Entry.** Appended to `tests/review_blocker_allowlist.json`: kind `unsafe_gain`, source_id obj-54, gain_id obj-9, inlet 1, path "". The key was built from the live finding, and the reason is the `<reference_data>` text.
- **Meaning.** The 1.21 peak is +1.66 dB of headroom on the slot volume.
- rhythmic-sampler is not a calibration project. `test_calibration_zero_blockers` stays green with no allowlist change.

## Deviations from Plan

**1. [Rule 1 - Bug] Negative outlet index crashed DSP gain staging**
- **Found during:** Task 2 robustness test (a cord with outlet `-3`).
- **Issue:** `_check_gain_staging` indexed `src_outlettype[edge.outlet]` with a negative int that was out of range, which raised IndexError.
- **Fix:** the guard is now `0 <= edge.outlet < len(src_outlettype)`, still on the pinned one-line read shape.
- **Files:** src/maxpat/critics/dsp_critic.py. **Commit:** 9a80232d.

**2. [Test scope] Task 3 robustness test narrowed.** A non-numeric `patching_rect` crashes `_check_out_of_bounds`. That bug predates Q26 and is outside its scope, so it is logged in `deferred-items.md` and not fixed. The robustness test covers exactly the contrast junk the plan names.

**3. Hot/cold ancestor label.** The finding names the target by `walk.box_name` (`'pack'`) and the ancestor by `_box_label` (`'unpack 0 0'`), following `<reference_data>`.

Otherwise the plan was executed as written. There are 4 `(Q26)` commits; none touches `patches/`, and every file is under src/maxpat, tests or ui-presets.md.

## Verification

- **Baseline** (Q/baseline-pytest.txt): 4782 passed, 5 xfailed, 1 xpassed, as expected.
- **Final** (Q/final-pytest.txt): 4872 passed, 5 xfailed, 1 xpassed, including the requires_max bundle sweep. The 90 extra are the new tests; `tests/test_critic_fixes_e5_e8.py` holds 77 test functions, with parametrization.
- **Red runs** recorded: Q/red-t1.txt, red-t1b.txt, red-t2.txt, red-t3.txt.
- **Verify blocks.** Each task's `<verify>` block passed.
- **Stash list** unchanged (empty). Python 3.10 parse holds for every touched file.
- **Q23 status:** not landed. There are no `(Q23)` commits in 65b4a894..HEAD.

## Commits

| Task | Commit | Message |
|---|---|---|
| 1a | 33df9006 | fix(critics): RNBO critic parses positional param names; missing in~ is a note (Q26) |
| 1b | 4a226958 | fix(critics): hot/cold warns only when one upstream event updates a cold inlet after the hot one (Q26) |
| 2 | 9a80232d | fix(critics): gain safety propagates value bounds on both *~ inlets with DB-driven gain-stage and terminal sets (Q26) |
| 3 | a841a2e1 | fix(critics): theme-aware text contrast -- Max 9 defaults, topmost visible panel, keep passing colours (Q26) |

## Follow-ups (outside Q26)

- The RNBO builder half of E8: shape, classnamespace and a golden fixture.
- `gain~` input check: its slider-position range is still unchecked.
- `sig~` and control `line` as gain bridges: the trace stops at them today.
- out~ severity on event-only rnbo~ patchers: 564 bundle blockers.
- Uncolored number/flonum/textbutton theme fills (`bgcolor` style 0.125, unverified).
- `_check_out_of_bounds` non-numeric rect crash (see deferred-items.md).

## Doc impact (nothing edited, rule 8)

- **TECHNICAL.md tables now out of date:**
  - Structure hot/cold;
  - DSP gain staging, and "MIDI-range gain values";
  - RNBO "Missing I/O": in~ is now a note;
  - validation Layer 4 terminals: now DB-driven, with plugout~ and the mc.* variants;
  - Layout "Low contrast text": theme defaults, topmost panel.
- **ui-presets.md** was updated as the plan requires.
- **CLAUDE.md** was not edited; its precedence summary is still accurate.
- **Memory note** `feedback_contrast_critic_default_text`: now resolved. A comment with no textcolor on the 0.333 or 0.235 canvas is no longer flagged.

## MAX confirmation (rule 9)

Nothing needs checking in MAX. Optionally, glance at the labels now newly flagged as low contrast:
- amplitude-follower's presentation labels (2.30:1 on the 0.537/0.537/0.776 panel);
- scala-synth's presentation flonums obj-321..337 (white text on the light presentation panel, 1.19:1).

## Self-Check: PASSED

- FOUND: src/maxpat/dsp_roles.py, tests/test_critic_fixes_e5_e8.py
- FOUND commits: 33df9006, 4a226958, 9a80232d, a841a2e1
