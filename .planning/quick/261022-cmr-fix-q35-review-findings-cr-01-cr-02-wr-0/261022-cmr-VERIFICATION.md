---
phase: quick-261022-cmr
verified: 2026-10-22T00:00:00Z
status: passed
score: 8/8 must-haves verified
covered_files:
  - src/maxpat/dsp_sim/README.md
  - src/maxpat/dsp_sim/genexpr_interp.py
  - src/maxpat/dsp_sim/smoke.py
  - tests/dsp_sim/test_genexpr_interp.py
  - tests/dsp_sim/test_smoke.py
covered_digest: "v2:sha256:601c454daf2fa607d31e23f281d9d53307d3693c7601f50319d320e58aa36caf"
behavior_unverified: 0
overrides_applied: 0
re_verification: none (initial verification)
---

# Quick 261022-cmr: Q35 review fixes (CR-01, CR-02, WR-01..WR-06) Verification

**Goal:** Fix Q35 review findings CR-01, CR-02, WR-01..WR-06 from 261021-urs-REVIEW.md.
**Status:** passed
**Commits verified:** b08e5d24, 67b0ae2d, fa5bccf2 (base 574bf18c)

I did not take SUMMARY.md on trust. I re-ran every review probe through `smoke_codebox` and the CLI, re-ran the suites, and diffed the files that must not change.

## Observable Truths

| # | Truth | Status | Evidence (own runs) |
|---|-------|--------|---------------------|
| CR-01 | A local read before assignment on every path is unsupported (exit 3). The review if/else probe and `out1 = y; y = in1;` name 'y' and a line. Block-local names do not leak. Compound assignment reads its target. Loop-carried locals still run. | VERIFIED | `smoke_codebox` gives unsupported for the if/else probe ("local 'y' is read before it is assigned ... (line 6)"), for `out1 = y; y = in1;`, for `y += in1; out1 = y;` and for `for(...){t=i;} out1=i;`. The CLI on the if/else probe exits 3. These pass: `y = 0; if ... else ...` pre-initialised, the terrain-cheby loop-carried form, block-local `t`, nested for/if, History and Param reads, and a ternary on a local. |
| CR-02 | A codebox with no outN is unsupported with "codebox has no outN outputs: nothing to check". A misspelled-output local gives an `output_typo` WARN. | VERIFIED | `ou1 = in1;` and the poke-only codebox both give unsupported with that reason, and the CLI exits 3. `out1 = in1; ou2 = in1*2;` gives pass plus one `output_typo` warn at `build`. |
| WR-01 | A corner error no longer discards FAILs. | VERIFIED | The review probe gives verdict fail, CLI exit 1, with the nonfinite FAIL at `default` and `UNSUPPORTED [g=max (200000)]` kept. A partial error with no FAIL gives unsupported with "(1 of 3 corners)" and corners = 2. An identical error at every corner collapses to one `all corners` finding with the legacy text `unsupported: unknown function: frobnicate (line 1)`. |
| WR-02 | If/else stays taken-branch. Each branch-stateful codebox gets exactly one `branch_state` INFO. The INFO never changes the verdict, the exit code or the warning count. The docs say "simulator's choice, unconfirmed in MAX". CLAUDE.md and genexpr-rules.md are unchanged. | VERIFIED | The probe gives pass, CLI exit 0, one `INFO branch_state [build] codebox: noise() (line 1) ...` line, `0 warning(s)`, and JSON severity `info`. A twin that FAILs on nonfinite stays fail with the INFO present. At 1 s, `branch_state` appears on exactly buffer-recorder, random-walk and sample-and-hold. `git diff --quiet 574bf18c HEAD -- CLAUDE.md .claude/skills/references/genexpr-rules.md` is clean. The docstring (genexpr_interp.py:74) and README lines 239-244 say "simulator's choice ... unconfirmed in MAX" and cite the evidence. Neither asserts equivalence with gen~. |
| WR-03 | A tab gives a `tab_char` WARN, not unsupported. | VERIFIED | Verdict pass plus a `tab_char` warn naming line 1. The CLI prints `WARN tab_char`, exit 0. |
| WR-04 | Param defaults and overrides are clamped to [min, max]. | VERIFIED | `Param p(min=0.5, max=1); out1 = in1/p;` gives pass, 2 corners and no `silent` finding. The clamp tests are green. |
| WR-05 | Silence is checked only while an input still changes. | VERIFIED | The 0-inlet decay gives pass, exit 0. The const:1 DC blocker gives pass. The positive control (`n < 2000` gate) still FAILs `silence` at `default`. |
| WR-06 | An `--input K` above the inlet count gives an `unused_input` WARN. | VERIFIED | API and CLI (`--input 5=const:1`) both give pass plus `WARN unused_input [build]`, exit 0. |
| Regression | The 19 patterns still pass. Fixtures, parity and untouched files hold. | VERIFIED | See below. |

## Regression and acceptance checks

- `python3 -m pytest tests/dsp_sim -q -p no:cacheprovider`: 531 passed, 4 xfailed. This includes `test_bassoon_parity_with_genrun`, the tanh/tanh(g) Delay and History self_sustain FAIL fixtures and the `/ drive` twin.
- Full `python3 -m pytest -q`: 5711 passed, 5 xfailed, 1 xpassed (156 s). `junit_diff.py baseline-junit.xml <my run>` prints `base=5662 new=5717 added=56 offenders=0` and exits 0. The only removal is the allowlisted `test_locals_reset_every_sample`.
- 1 s sweep of the 19 `patterns/gen` files, with `phasor:2` on swing-generator and subdivider: all pass. The only INFO carriers are buffer-recorder, random-walk and sample-and-hold. WARN sets match the SUMMARY table.
- Bassoon `.maxpat`: one codebox, pass, no findings, exit 0.
- `git status --porcelain src tests patches patterns CLAUDE.md .claude` is clean after my runs. The stash list is empty.
- `git diff 574bf18c HEAD` shows no change to `patches/`, `patterns/`, CLAUDE.md, genexpr-rules.md, genrun.py, test_bassoon-model.py or test_cli.py. Only 5 files changed: README.md, genexpr_interp.py, smoke.py and the two test files.
- No `eval(`, `exec(`, `compile(` or `__import__` call exists in the two modules. The only hits are regex names and a docstring line saying there are none.
- README documents the new findings (tab_char, output_typo, unused_input, branch_state), the silence gate, the clamp with its `[ASSUMED]` tag, and the if limit.

## Requirements coverage

All eight IDs (CR-01, CR-02, WR-01 to WR-06) are satisfied. WR-07, IN-01, IN-02 and IN-03 are out of scope. SUMMARY.md lists them as deferred, along with the genexpr-rules.md/CLAUDE.md "both branches execute" conflict, which needs a MAX test.

## Anti-patterns

No TBD/FIXME/XXX debt markers or stubs found in the diffed code that block the goal.

## Gaps

None.

## Human verification

None required for this task. One item is a known, user-accepted open question: whether MAX executes both if/else branches (WR-02). It is recorded in SUMMARY.md and the README as unconfirmed in MAX, and needs a MAX test before the rule text is reworded. It does not gate this task.

---

_Verified: 2026-10-22_
_Verifier: Claude (gsd-verifier)_
