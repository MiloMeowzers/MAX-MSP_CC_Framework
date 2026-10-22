---
phase: quick-261022-cmr
plan: 01
subsystem: dsp_sim (GenExpr interpreter + codebox smoke test)
status: complete
tags: [dsp_sim, genexpr, smoke, code-review-fixes, q35]
requires: [quick-261021-urs (Q35 interpreter and smoke)]
provides:
  - definite-assignment check (CR-01)
  - zero-output unsupported + output_typo WARN (CR-02)
  - per-corner unsupported findings and verdict rules (WR-01)
  - branch_state INFO advisory (WR-02)
  - tab_char WARN (WR-03)
  - Param default/override clamp (WR-04)
  - excited-input silence gate (WR-05)
  - unused_input WARN (WR-06)
affects: [max-dsp-agent pre-flight smoke verdicts]
tech-stack:
  added: []
  patterns: [parse-time AST walks, build-time lint/advisory tuples on Codebox, per-corner error findings]
key-files:
  created: []
  modified:
    - src/maxpat/dsp_sim/genexpr_interp.py
    - src/maxpat/dsp_sim/smoke.py
    - src/maxpat/dsp_sim/README.md
    - tests/dsp_sim/test_genexpr_interp.py
    - tests/dsp_sim/test_smoke.py
decisions:
  - "CR-01: if/else and for branches are checked on copies and never merged back (block-local names), departing from the review's `defined |= t & e` snippet, which would still PASS the review's own if/else probe"
  - "WR-02 (user, 2026-10-22): taken-branch if/else kept; every branch-stateful codebox gets one verdict-neutral branch_state INFO; docs call it the simulator's choice, unconfirmed in MAX"
  - "WR-03: tab is a WARN, not Unsupported (26 of 54 Max 9.2 Examples/gen codeboxes contain tabs)"
  - "WR-01: severity 'unsupported' is a third finding severity; fail beats unsupported beats pass; identical all-corner errors collapse to one 'all corners' finding with the legacy reason"
metrics:
  duration: "~35 min (resume session; baseline done by the previous executor)"
  completed: 2026-10-22
estimate:
  tokens: 185000
  tasks: 3
actuals:
  tokens: 9932
  tasks: 3
  commits: 3
plan_head_before: 574bf18c63a9e751ac7850192e01522c28f6d07b
plan_head_after: fa5bccf20a6e95c9537a8b2c1c3bef2df4207aab
---

# Quick 261022-cmr: Q35 review fixes (CR-01, CR-02, WR-01..WR-06) Summary

The smoke test no longer passes codeboxes that MAX would reject or that it can't check, and it no longer drops or invents FAILs. Locals read before they are assigned on every path, and codeboxes with no `outN`, are now `unsupported`. Corner errors are recorded per corner. Params are clamped to their range, silence is only judged while an input is still changing, and tab characters, output typos and unused `--input` keys each give a WARN. A `branch_state` INFO marks every stateful call inside an if/else body. The INFO never changes the verdict.

## Findings fixed

| Finding | Fix | Regression test(s) | Commit |
|---------|-----|--------------------|--------|
| CR-01 | `_check_definite_assignment` in `parse_codebox`. It walks statements in order. If/else branches and for bodies are checked on copies that are never merged back. Compound assignment reads its target. Ignored constant targets are not added. | interp: `test_local_read_before_assignment_is_unsupported` (7 cases, line numbers asserted), `test_definitely_assigned_locals_still_run`; smoke: `test_cr01_uninitialized_local_is_unsupported[if-else,read-first]`, `test_cr01_cli_exits_3` | b08e5d24 |
| CR-02 | `smoke_codebox` returns `unsupported` / "codebox has no outN outputs: nothing to check" when `n_out == 0`. `Codebox.lint` gets an `output_typo` entry for a `<letters><digits>` local whose letters are within edit distance 1 of `out` and that is not a lowercase `outN`. | interp: `test_output_typo_lint[ou2,Out1]`, `test_output_typo_lint_ignores_ordinary_locals`; smoke: `test_cr02_zero_output_codebox_is_unsupported[typo,poke-only]`, `test_cr02_cli_exits_3`, `test_cr02_output_typo_warns`, `test_cr02_no_output_typo_for_ordinary_locals` | b08e5d24 |
| WR-01 | The try/except now sits inside the corner loop. Each error becomes `Finding("unsupported", "unsupported", corner, 0, detail)`, and earlier findings are kept. `corners` counts the corners that completed. An identical error at every corner collapses to one `all corners` finding with the legacy reason. `_format_text` prints `UNSUPPORTED [<corner>] codebox: <detail>`. | `test_wr01_corner_error_keeps_fail` (verdict fail, exit 1), `test_wr01_partial_error_without_fail_is_unsupported` ("1 of 3 corners"), `test_wr01_identical_errors_collapse_to_all_corners`; `test_unknown_function_is_unsupported` stays green unedited | 67b0ae2d |
| WR-02 | User decision applied: taken-branch kept, `_branch_state_advisory` -> `Codebox.advisories` -> one INFO finding per codebox | interp: `test_untaken_noise_does_not_advance_the_stream`, `test_conditional_poke_writes_only_when_taken`, `test_branch_state_advisory_on_review_probe`, `test_branch_state_flags_each_construct` (7), `test_branch_state_fires_from_every_branch_position` (3), `test_branch_state_aggregates_per_construct`, `test_branch_state_not_flagged` (5); smoke: `test_wr02_branch_state_is_info_and_verdict_neutral`, `test_wr02_fail_stays_fail_with_advisory`, `test_wr02_cli_text_and_json`, `test_wr02_branch_stateful_patterns_pass_with_advisory` (3 patterns) | fa5bccf2 |
| WR-03 | `tab_char` lint WARN naming the first line that contains a tab | `test_tab_char_lint`, `test_wr03_tab_char_warns` | b08e5d24 |
| WR-04 | `_clamp_param` (RNBO order: min first, then max) on parse defaults and `_Builder` `params=` overrides | `test_param_default_and_overrides_are_clamped`, `test_wr04_param_default_clamped_in_smoke` (pass, 2 corners, no `silent`) | 67b0ae2d |
| WR-05 | `excited = n_in >= 1 and any(ptp(sig[tail of driven window]) > ACTIVITY_FLOOR)`, computed once and passed to `_driven_checks`. The detail now ends "while an input is still changing". | `test_wr05_zero_inlet_decay_passes`, `test_wr05_const_driven_dc_blocker_passes`, `test_wr05_silence_still_fails_while_input_active` (positive control); `test_buffer_option_resizes_buffer` corrected | 67b0ae2d |
| WR-06 | `unused_input` WARN for each override key above `n_in` (detail `--input K=SPEC not applied: this codebox has N inlet(s)`) | `test_wr06_unused_input_warns` (API + CLI) | 67b0ae2d |

## WR-02: user decision and evidence

On 2026-10-22 the user chose "taken-branch + advisory note":

- The interpreter still runs only the taken branch; `_Builder` and `Program` are unchanged.
- Every codebox with a stateful call or write inside an if/else body gets exactly one `branch_state` finding with severity `info` at corner `build`.
- That finding never changes the verdict, the exit code or the summary's warning count.

The evidence points to conditional execution:

- The Max 9.2 GenExpr guide ("Branching and Looping") says different blocks run under different conditions.
- RNBO genexpr_js emits a plain `IfStatement`.
- 8 shipped Examples/gen patches rely on conditional poke, noise or Delay.write inside `if`, for example gen~.chopper_repeat.

The docstring and the README describe taken-branch as the simulator's choice and say it is unconfirmed in MAX.

**Codeboxes the advisory fires on** (probe over every codebox in `patterns/gen` and `patches/**`). It matches the planning probe exactly: 16 entries, poke and noise only.

| Codebox | Advisory constructs |
|---------|---------------------|
| patterns/gen/buffer/buffer-recorder.gendsp | poke() (line 14) |
| patterns/gen/random/random-walk.gendsp | noise() (line 18) |
| patterns/gen/random/sample-and-hold.gendsp | noise() (line 14) |
| patches/gong-model/generated/gong-engine.gendsp | poke() x291 (first at line 104), noise() x2 (first at line 568) |
| patches/gong-model/generated/gong-model.maxpat > gen~ gong-engine (same codebox as above) | same |
| patches/granularsynthtest/generated/granular-engine.gendsp | noise() x4 (first at line 67), poke() x5 (first at line 84) |
| patches/knock/generated/knock.maxpat | noise() x5 (first at line 101) |
| patches/looper/generated/looper.maxpat | poke() x2 (first at line 54) |
| patches/reverse-delay/generated/reverse-delay-mono.maxpat | noise() x6 (first at line 183), poke() x20 (first at line 288) |
| patches/reverse-delay/generated/reverse-delay.maxpat | noise() x6 (first at line 184), poke() x20 (first at line 296) |
| patches/sample-layers/generated/sample-layers-slot.maxpat | noise() x3 (first at line 62) |
| patches/scala-synth/generated/scala-synth-voice.maxpat | poke() x2 (first at line 29) |
| patches/stutter/generated/stutter-engine.gendsp | poke() x19 (first at line 39), noise() x3 (first at line 117) |
| patches/stutter/generated/stutter.maxpat > gen~ stutter-engine (same codebox as above) | same |
| patches/terrain-synth/generated/terrain-cheby.maxpat (MAX-confirmed) | poke() x2 (first at line 67) |
| patches/timestretch/generated/timestretch.maxpat > gen~ @source timestretch-source | poke() x9 (first at line 158), noise() (line 462) |

**Deferred follow-up (rule conflict):** `.claude/skills/references/genexpr-rules.md:13` and the CLAUDE.md Gen~ bullet ("Everything runs once per sample, and both branches always execute") conflict with the simulator's taken-branch choice and the evidence above. A MAX test is needed before the rule is reworded. Neither file was edited; both are byte-identical to base-sha (checked by the Task 3 gate).

## Other notes

- **WR-03 evidence:** 26 of the 54 codeboxes in Max 9.2's `/Applications/Max.app/Contents/Resources/Examples/gen/*.maxpat` contain tab characters, so a tab is flagged as a project-convention WARN rather than a confirmed compile error.
- **CR-01 departure from the review snippet:** the review suggested `defined |= (t & e)` after an if/else. That would mark `y` as defined after `if (...) { y = 1; } else { y = 0.5; }`, so the review's own probe would still PASS. Gen variables are local-to-scope (Max 9.2 guide), and genexpr-rules.md:14 says to initialize before the block, so branches are never merged back. For-loop counters and body names do not leak either. Loop-carried locals assigned before the loop (the terrain-cheby form) still run.
- **`test_locals_reset_every_sample` replaced:** its codebox `x = x + 1; out1 = x;` reads `x` before assignment, which is exactly what CR-01 rejects. It is now the `self-read` case of `test_local_read_before_assignment_is_unsupported`. It is the one allowlisted removal in junit_diff.py.
- **`test_buffer_option_resizes_buffer` corrected:** it asserted a `silence` FAIL at `loop=min (0)` for buffer-player (0 inlets) with a 1000-frame buffer. A one-shot player that finishes is correct, so the test now asserts pass, no silence finding, and CLI exit 0. The test name and its `dim/channels` part are unchanged.
- **Repo-wide parse check:** 99 discovered codebox entries. 98 parse as before; the 1 unsupported is the deliberate `patches/max-bridge/fixtures/fx-genfail.maxpat` ("assignment to Param 'g'", unsupported before this change too). No repo codebox hits CR-01, CR-02, tab_char, output_typo or an out-of-range Param default.

## 1 s pattern sweep (smoke_file defaults; phasor:2 on in1 for swing-generator and subdivider)

| Pattern | Verdict | Corners | Warnings | Advisories |
|---|---|---|---|---|
| buffer-player | pass | 6 | silent@start=max (1), silent@end=min (0) | - |
| buffer-recorder | pass | 3 | silent@default, dc@record=max (1) x2, silent@loop=max (1) | poke() (line 14) |
| compressor | pass | 10 | - | - |
| multi-tap-delay | pass | 7 | - | - |
| noise-generator | pass | 2 | - | - |
| simple-reverb | pass | 7 | - | - |
| safe-gain | pass | 3 | silent@gain=min (0) | - |
| soft-clipper | pass | 2 | - | - |
| adsr-envelope | pass | 9 | dc x2 at each of default, attack=min, decay=min, decay=max, sustain=min, sustain=max, release=max | - |
| ar-envelope | pass | 5 | dc@default, dc@attack=min (0.1), dc@release=max (10000) x2 | - |
| exp-curve | pass | 3 | dc@curve=min (-4), silent@curve=max (4) | - |
| smooth-ramp | pass | 3 | - | - |
| random-walk | pass | 8 | dc x8 (default + 7 corners) | noise() (line 18) |
| sample-and-hold | pass | 4 | silent x4 | noise() (line 14) |
| lag-processor | pass | 5 | dc@rise_ms=max (5000), dc@fall_ms=max (5000) | - |
| one-pole-smooth | pass | 3 | - | - |
| master-clock | pass | 5 | dc x5 | - |
| subdivider | pass | 3 | dc x3 | - |
| swing-generator | pass | 3 | dc x3 | - |

**Diff against the 261021-urs table:** every pattern has the same verdict, the same corner count and the same WARN counts by check. For example, buffer-recorder has dc x1 + dc latch x1 + silent x2, and adsr-envelope has dc x7 + dc latch x7. No new WARN fires. The only new findings are the three branch_state INFOs on buffer-recorder, random-walk and sample-and-hold. No pattern was edited.

## Gate results

- **Baseline** (base-sha 574bf18c): `pytest` rc 0, 5656 passed, 5 xfailed, 1 xpassed (baseline-junit.xml, from the previous executor's Step 0).
- **Final**: `pytest` rc 0, 5711 passed, 5 xfailed, 1 xpassed, 155 s (final-junit.xml).
- **junit_diff.py baseline-junit.xml final-junit.xml**: `base=5662 new=5717 added=56 offenders=0`, exit 0. The only removal is the allowlisted `test_locals_reset_every_sample`.
- `tests/dsp_sim` + `tests/test_doc_signatures.py` + `tests/test_agent_skills.py`: 810 passed, 4 xfailed. These include `test_bassoon_parity_with_genrun` (1e-12), the tanh/tanh(g) Delay and History fixtures (still FAIL self_sustain) and the `/ drive` twin (passes).
- 19-pattern 1 s sweep: all pass. branch_state appears on exactly buffer-recorder, random-walk and sample-and-hold.
- Bassoon `.maxpat` JSON check: 1 codebox (bassoon.gendsp), verdict pass, no findings.
- `git status --porcelain patches patterns` is empty, and the stash list is unchanged (still empty).
- genrun.py, test_bassoon-model.py, test_cli.py, CLAUDE.md and genexpr-rules.md are byte-identical to base-sha.

## Self-Check: PASSED

- All 5 modified files exist.
- Commits b08e5d24, 67b0ae2d and fa5bccf2 are present on main.
- `git rev-list --count 574bf18c..HEAD` = 3.

## Deviations from Plan

None. The plan was executed as written. One judgement call: the CR-01 compound-assignment error is reported at the assignment's line, because the target of `y += ...` is not a Name node.

## Deferred items (out of scope)

- **WR-07:** tests are pinned to live terrain-synth and bassoon project files with hardcoded counts. Move them to minimal fixtures in `tests/dsp_sim/fixtures/`.
- **IN-01:** declaration type order (Param, Delay, History, Buffer/Data) is not checked.
- **IN-02:** the README title and Scope still describe a bassoon-only harness.
- **IN-03:** a bad `buffers=` argument to `smoke_codebox` comes back as `unsupported` instead of raising ValueError.
- **WR-02 rule conflict:** genexpr-rules.md:13 and CLAUDE.md say "both branches always execute", but the simulator runs only the taken branch, and the evidence points to conditional execution. This needs a MAX test before the rule is reworded.
- **`else if`:** valid GenExpr per the Max 9.2 guide, but it stays Unsupported in the interpreter (out of scope).

## Threat Flags

None. The changes are parse-time AST walks and stdlib helpers, with no new I/O, network or eval surface. The AST guard test (`test_no_string_evaluation_in_smoke_modules`) and the no-save-gate import test stay green.
