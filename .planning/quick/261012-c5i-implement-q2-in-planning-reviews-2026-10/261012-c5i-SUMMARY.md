---
phase: quick-261012-c5i
plan: 01
subsystem: object-db
tags: [db, overrides, validation, signal-ports, trailing-outlets, review-q2]
status: complete
requires: [quick-261012-bii]
provides:
  - "overrides.json: 63 audit-downgraded signal inlets restored (36 objects)"
  - "OverrideGenerator._build_inlet_array(count, obj_name) copies signal/type from the current DB entry by index"
  - "tests/test_db_signal_ports.py guard: no signal->control inlet flip outside _SIGNAL_DOWNGRADE_ALLOWLIST (adc~ 0, peek~ 0/1/2)"
  - "biquad~ inlet 0 = signal/list; `in` outlet has no role; peek~ inlets control"
  - "_classify_role_mismatch: a dst inlet type token equal to the src role accepts it"
  - "second_arg+1 / second_arg+2 formulas; trailing_outlets rules for play~, matrix~, mc.matrix~"
affects: [validation Layer 3, audit generator, Patcher box counts for matrix~/play~/mc.matrix~, Q10, Q11]
tech-stack:
  added: []
  patterns: ["guard test rebuilds pre-override base entries in DOMAIN_LOAD_ORDER and diffs override inlets against them"]
key-files:
  created:
    - tests/test_db_signal_ports.py
  modified:
    - .claude/max-objects/overrides.json
    - src/maxpat/audit/overrides.py
    - src/maxpat/validation.py
    - src/maxpat/db_lookup.py
    - tests/test_db_lookup.py
decisions:
  - "OQ1-A (user answer, 2026-10-12): the guard covers inlets only; the 40 outlet flips go to Q11"
  - "OQ2-A (user answer, 2026-10-12): mc.matrix~ N M = M audio + 2 control outlets (second_arg+2, trailing 2, default 4), following MAX-saved help boxes"
  - "OQ3-A (user answer, 2026-10-12): the 11 audit-written control inlets beyond the base arrays are left alone and handed to Q10"
  - "Override signal repair changes only `signal`/`type`; digests stay as written (Q11's per-port merge restores them)"
  - "Reviewed signal->control inlet exceptions live in _SIGNAL_DOWNGRADE_ALLOWLIST with written reasons; a hygiene test fails on stale or reasonless entries"
metrics:
  duration: "~25 min"
  completed: 2026-10-12
actuals:
  tokens: 11912
  tasks: 3
  commits: 3
plan_head_before: ee723d2806181efacce488ae8d2435b8f40dfcc1
plan_head_after: d0885b813efa72f2389276cfec99213dbb514075
---

# Quick 261012-c5i: Q2 - DB data that made the validator flag valid cords (A1 data part) Summary

The audit tool's blind `signal: false` inlets on 36 objects are repaired. The generator now copies signal/type from the DB, so a future audit regen can't reintroduce them, and a guard test forbids new downgrades outside a reviewed allowlist. biquad~, `in` and peek~ now match their refpages, and matrix~, mc.matrix~ and play~ outlet counts and roles match MAX-saved help boxes through `trailing_outlets`.

## Commits

| Task | Commit | Files |
|------|--------|-------|
| 1. Signal-inlet repair, generator, guard | 7909d49 | tests/test_db_signal_ports.py, .claude/max-objects/overrides.json, src/maxpat/audit/overrides.py |
| 2. biquad~ / in / peek~, role-token acceptance | eae0896 | .claude/max-objects/overrides.json, src/maxpat/validation.py, tests/test_db_signal_ports.py |
| 3. Trailing outlets + formulas | d0885b8 | src/maxpat/db_lookup.py, .claude/max-objects/overrides.json, tests/test_db_lookup.py, tests/test_db_signal_ports.py |

None of the commits touches `patches/`. The stash list was empty before and after the run. `patches/.active-project.json` and `.planning/tci-phase2/` were left untouched.

## Test totals

- **Baseline** (HEAD ee723d2): 3 failed, 2345 passed, 2 xfailed, 1 xpassed. The 3 failures are the allowed `test_review_patch_no_blockers` cases (minitaur, physics-composition, timestretch).
- **Final** (HEAD d0885b8): 3 failed, 2390 passed, 2 xfailed, 1 xpassed. The failing set is identical to the baseline. The 45 extra passes are this plan's new tests: 32 in `test_db_signal_ports.py` and 13 in `test_db_lookup.py`.
- **Red counts before each GREEN step:**
  - **Task 1:** 9 failed / 11 passed.
    - The guard listed exactly 63 ports.
    - 2 generator tests failed on `signal is True`, and 1 failed with a TypeError from the old 1-arg signature.
    - 5 repros (sfrecord~ 2, vst~, pitchshift~, fffb~ 4, mc.snapshot~) failed with `Signal outlet to control-only inlet ... proposed removal`.
  - **Task 2:** 8 failed / 20 passed.
    - The peek~ allowlist entries were not yet live flips.
    - filtergraph~ -> biquad~ gave a `list outlet → signal inlet` warning.
    - in 1 -> peek~ and scala-synth-voice each gave a `status outlet → signal inlet` warning.
    - The 3 DB-fact tests failed.
    - cycle~ -> peek~ was accepted.
  - **Task 3:** 16 failed / 78 passed across `test_db_lookup.py` and `test_db_signal_ports.py`.
    - 12 DB tests failed, including the rewritten `test_compute_io_counts_mc_matrix`.
    - The matrix~ 2 4 -> dac~ and play~ buf 2 -> dac~ repros gave role warnings.
    - The 2 trailing-outlet anchors failed because the dump/bang outlet resolved beyond the DB array, so there was no role and no warning.
- The Python 3.10 `ast.parse` gate passes on every changed .py file. The Task 1 overrides diff contains only `"type"`/`"signal"` lines (ONLY-TYPE-SIGNAL-LINES).

## Repaired ports (Task 1): 63 ports on 36 objects, same as observed_facts

- **The 19 the spec names (29 ports):**
  - sfrecord~ 0, vst~ 0-1, pitchshift~ 0-1, fffb~ 0;
  - poly~ 0, pfft~ 0, 2d.wave~ 0-3, sfizz~ 0-1, thispoly~ 0, mcs.poly~ 0, mcs.tapout~ 0;
  - mc.snapshot~ 0-1, mc.groove~ 0-2, mc.play~ 0, mc.tapout~ 0, mc.line~ 0-1, mc.selector~ 0-1, mc.train~ 0-2, mc.vst~ 0-1.
- **17 others found (34 ports):**
  - MSP/MC: curve~ 0-2, line~ 0-1, mc.adsr~ 0-4, mc.amxd~ 0-2, mc.edge~ 0, mc.fffb~ 0, mc.peakamp~ 0, mc.poly~ 0, mc.spike~ 0;
  - Gen: concat 0, hsl2rgb 0, phasor 0, poke 0-3, rgb2hsl 0, swiz 0, train 0-1, vec 0.
- Restored types come from the base entries: `signal`, `signal/float`, `signal/int`, `signal/message`, `mc_signal`, `mc_signal/message`.
- adc~ 0 stays control. It is on the allowlist, with the reason taken from its existing `_audit.source`.
- No live value differed from observed_facts: 63/36 repaired, 40 outlet flips on 38 objects, MSP role-coverage `gap_count` 1 -> 2.

## Open questions: all user answers (none resolved by default)

- **OQ1-A (user answer, 2026-10-12): inlets only.** The guard checks inlets only. The 40 outlet flips go to Q11 (see below).
- **OQ2-A (user answer, 2026-10-12): M + 2, following MAX.**
  - The mc.matrix~ rule is now `second_arg+2`, `trailing_outlets 2`, `default_outlets 4`.
  - A 4th control outlet (no role) was appended to the mc.matrix~ override.
  - `mc.matrix~ 3 2` = (3, 4), with roles (audio, audio, list, None).
- **OQ3-A (user answer, 2026-10-12): leave for Q10.** The 11 beyond-base ports are unchanged (see below).

## Hand-offs

**Q11 (C9 outlet roles; OQ1-A).** There are 40 outlet signal->control flips on 38 objects. They are written by `_build_outlet_array(help_types)` from MAX-saved help-box outlettypes, and none of them is guarded:
- **30 Gen operators** (outlettype is always "" inside gen patchers): bool, buffer, channels, constant, dcblock, delta, dim, fixnan, fold, fract, history, hypot, isnan, latch, min, mix, mstosamps, noise, or, phasewrap, phasor, pi, radians, sah, samplerate, sampstoms, selector, train, triangle, trunc and wrap. All are outlet 0.
- **buffer~ 0-1** (manual entry).
- **pong 0.**
- **jit.peek~ 1, jit.poke~ 0, jit.release~ 1.**
- **amxd~ 2/3.**
- **live.modulate~ 0.**

C9's 16 outlet role contradictions also stay with Q11. Only C9's cause (`_build_inlet_array`) was fixed here.

**Q10 (argument-dependent ports; OQ3-A).** 11 audit-written control inlets sit beyond the base inlet arrays, so copy-by-index can't reach them:
- sfrecord~ 1, pitchshift~ 2, mc.selector~ 2;
- mc.tapout~ 1-2, mcs.tapout~ 1-2;
- concat 1, vec 1-2 (Gen);
- pfft~ 1 (a container, so harmless).

Two of these still give proposed removals, which block new patches:
- `cycle~ -> sfrecord~ 2` inlet 1;
- an MC signal into `mc.selector~ 2` inlet 2.

Q10 owns record~ N / tapout~ taps / one-port-per-argument layouts.

## Side effects

- **MSP role coverage.** `audit_signal_role_coverage()["msp"]["gap_count"]` goes from 1 to 2, because `in` no longer has a curated role. No test pins this count.
- **mc.chord~.** Its `signal/list` inlet 0 now also accepts list-role sources without a warning. A DB scan confirms the token rule affects only biquad~ 0 and mc.chord~ 0.
- **Patcher box counts.**
  - `matrix~ 2 4` is now built with 5 outlets (was 4).
  - `play~ buf 2` is now built with 3 outlets (was 2).
  - `mc.matrix~ N M` is built with M + 2 outlets (was M).
  - A bare `matrix~` now defaults to 2 outlets (1 audio + dump).
  - `play~ buf @loop 1` falls back to 2 outlets and gives a one-time non-integer warning (same semantics as `second_arg`).
- **scala-synth-voice.** Its only connection warning (`status outlet → signal inlet: use snapshot~`, obj-1 -> obj-3) is gone. mixer-strip, terrain-voice and scala-synth-voice all propose 0 removals.
- **Anchors.** Signals into `print` and `peek~` are still proposed for removal. A list into a plain `signal` inlet (`*~`) still warns. A trailing dump or bang cord into `dac~` still warns, with no proposed removal.

## Doc impact (not edited, rule 8 / S14)

- **`TECHNICAL.md:159`.** The `matrix~ 4 2` -> 2 outlets example is now 3. The formula table lacks `second_arg+1` / `second_arg+2`.
- **`CLAUDE.md:197`.** The MSP bullet "If a control connection ... gets stripped by validation" predates Q1. It should read "proposed for removal" and could mention the new inlet guard (`tests/test_db_signal_ports.py`).
- **Q11 / Q10 hand-offs** as listed above.
- **mc.matrix~ outlettype (pre-existing gap).** `get_outlet_types` returns `signal` for mc.matrix~, but MAX writes `multichannelsignal`. The override outlets are typed `signal`, not multichannel.

## Deviations from Plan

None. The plan was executed as written with the user's OQ1-A / OQ2-A / OQ3-A answers. Minor notes:
- **Alias handling in `_build_inlet_array`.** After alias canonicalisation, it also falls back to the raw name, which is harmless and type-guarded.
- **Task 3 anchors.** They were red because no role resolved, not because of a wrong warning. The end state is as specified.

## Confirm in MAX (rule 9)

Nothing is required: every count comes from MAX-saved help boxes, and no patch file changed. Optionally, open a generated `mc.matrix~ 3 2` (expect 4 outlets) and `play~ buf 2` (expect 3 outlets).

## Known Stubs

None.

## Self-Check: PASSED

- FOUND: tests/test_db_signal_ports.py, .claude/max-objects/overrides.json, src/maxpat/audit/overrides.py, src/maxpat/validation.py, src/maxpat/db_lookup.py, tests/test_db_lookup.py
- FOUND commits: 7909d49, eae0896, d0885b8 (`git rev-list --count ee723d2..HEAD` = 3)
