---
phase: quick-261022-cmr
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/maxpat/dsp_sim/genexpr_interp.py
  - src/maxpat/dsp_sim/smoke.py
  - tests/dsp_sim/test_genexpr_interp.py
  - tests/dsp_sim/test_smoke.py
  - src/maxpat/dsp_sim/README.md
autonomous: true
requirements: [CR-01, CR-02, WR-01, WR-02, WR-03, WR-04, WR-05, WR-06]

estimate:
  # estimate-calibration: factor 1, sample_count 0, confidence low -> tokens == raw_tokens.
  # Task 1 ~55k (baseline, definite assignment, zero-output, lint plumbing),
  # Task 2 ~55k (per-corner errors, clamp, silence gate, unused input),
  # Task 3 ~75k (WR-02 branch_state advisory + tests, docs, 1 s sweep, full-suite junit gate).
  tokens: 185000
  raw_tokens: 185000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "CR-01: a codebox that reads a local before it is assigned on every path is `unsupported` (exit 3), never PASS. The review probes `if (in1 > 0) { y = 1; } else { y = 0.5; } out1 = y * in1;` and `out1 = y; y = in1;` both give unsupported naming 'y' and its line. Names first assigned inside an if/else or for block do not leak out of it (gen variables are local-to-scope), compound assignment reads its target, and loop-carried locals assigned before the loop (the MAX-confirmed terrain-cheby form) still run."
    - "CR-02: a codebox with no outN (`ou1 = in1;`, `Data d(10); poke(d, in1, 0, 0);`) is `unsupported` with reason 'codebox has no outN outputs: nothing to check' (exit 3). A local that looks like a misspelled output (`ou2`, `Out1`) gives an `output_typo` WARN."
    - "WR-01: an interpreter error in one corner no longer discards FAILs from other corners. The review probe (`Param g(1, min=0, max=200000) ... pow(10,400) ... for (i = 0; i < g; ...)`) gives verdict fail (exit 1) with the nonfinite FAIL at `default` and an `unsupported` finding at `g=max (200000)`. An error that hits every corner with the same message collapses to one `all corners` finding and keeps the legacy reason text."
    - "WR-02 (user decision 2026-10-22, taken-branch + advisory note): if/else keeps taken-branch-only execution, with no behaviour change. Every codebox with a stateful call or write inside an if/else body (noise, phasor, cycle, latch, dcblock, poke, any `<name>.write()`) gets exactly one `branch_state` finding of severity `info` at corner `build`. Its detail names each construct and its line. It never changes the verdict, the exit code or the summary's warning count. The review probe `History c; if (c > 1e9) { out1 = noise(); } out1 = in1;` is pass, CLI exit 0, with the INFO line. buffer-recorder, random-walk and sample-and-hold still pass, each with its advisory. The interpreter docstring and the README state the taken-branch semantics as the simulator's choice, cite the evidence briefly and say it is unconfirmed in MAX; they never claim equivalence with gen~ as fact. CLAUDE.md and genexpr-rules.md are not edited; the rule conflict is a deferred follow-up in the SUMMARY."
    - "WR-03: a tab character anywhere in the codebox gives a `tab_char` WARN naming its first line. It is a WARN, not unsupported: 26 of the 54 codeboxes in Max 9.2's own Examples/gen contain tabs. WR-04: Param defaults and `params=` overrides are clamped to the declared [min, max], so `Param p(min=0.5, max=1); out1 = in1 / p;` runs at p = 0.5 and passes with 2 corners and no `silent` WARN."
    - "WR-05: the permanent-silence check runs only when some inlet still changes over the tail of the driven window (np.ptp > ACTIVITY_FLOOR), so 0-inlet decays, const-driven DC blockers and one-shot buffer playback no longer FAIL. A codebox that goes silent while the default noise is still active still FAILs. WR-06: an `--input K=SPEC` with K above a codebox's inlet count gives an `unused_input` WARN on that codebox."
    - "Acceptance/regression: all 19 patterns/gen files still PASS at the 1 s default (phasor:2 on swing-generator and subdivider), and exactly buffer-recorder, random-walk and sample-and-hold carry a branch_state INFO. The tanh(x*g)/tanh(g) Delay and History fixtures still FAIL self_sustain, and the `/ drive` twin still passes. Bassoon genrun parity holds at 1e-12. genrun.py, test_bassoon-model.py and test_cli.py are byte-identical to base-sha. The full pytest run exits <= 1 with a clean junit diff, patches/ and patterns/ are untouched, and the stash list is unchanged."
  artifacts:
    - path: "src/maxpat/dsp_sim/genexpr_interp.py"
      provides: "definite-assignment check in parse_codebox, Codebox.lint (tab_char, output_typo), Codebox.advisories (branch_state), Param default/override clamp, corrected semantics table"
      contains: "def _branch_state_advisory("
    - path: "src/maxpat/dsp_sim/smoke.py"
      provides: "zero-output unsupported, per-corner error findings + verdict rules, excited-input silence gate, unused_input WARN, lint findings, branch_state INFO findings"
      contains: "cb.advisories"
    - path: "tests/dsp_sim/test_genexpr_interp.py"
      provides: "regression tests for CR-01, WR-02 semantics + branch_state detection, WR-03 lint, WR-04 clamp"
      contains: "def test_local_read_before_assignment_is_unsupported"
    - path: "tests/dsp_sim/test_smoke.py"
      provides: "review-probe regression tests for CR-01, CR-02, WR-01..WR-06, including the WR-02 advisory on the probe and the 3 branch-stateful patterns"
      contains: "branch_state"
    - path: "src/maxpat/dsp_sim/README.md"
      provides: "checks table with the new findings, the clamp, definite assignment, the verdict rules and the if/else semantics stated as the simulator's choice, unconfirmed in MAX"
      contains: "unconfirmed in MAX"
  key_links:
    - from: "src/maxpat/dsp_sim/genexpr_interp.py parse_codebox"
      to: "src/maxpat/dsp_sim/smoke.py smoke_codebox"
      via: "Unsupported raised at parse (CR-01) -> unsupported verdict; Codebox.lint entries -> WARN findings at corner 'build'"
      pattern: "cb.lint"
    - from: "src/maxpat/dsp_sim/smoke.py corner loop"
      to: "CodeboxResult verdict"
      via: "per-corner try/except records severity 'unsupported' findings; fail beats unsupported beats pass"
      pattern: "\"unsupported\""
    - from: "src/maxpat/dsp_sim/smoke.py smoke_codebox"
      to: "_driven_checks silence check"
      via: "excited flag computed once from the inlet signals' tail ptp"
      pattern: "excited"
    - from: "src/maxpat/dsp_sim/genexpr_interp.py parse_codebox (_branch_state_advisory)"
      to: "src/maxpat/dsp_sim/smoke.py smoke_codebox findings"
      via: "Codebox.advisories entries -> Finding(check, 'info', 'build', 0, detail); verdict, _exit_code and the summary warning count ignore severity info"
      pattern: "cb.advisories"
---

<objective>
Fix the Q35 code-review findings CR-01, CR-02 and WR-01..WR-06 from .planning/quick/261021-urs-implement-q35-in-planning-reviews-2026-1/261021-urs-REVIEW.md. Each fix gets a regression test that reproduces the review's probe. The smoke contract this restores: broken or uncheckable codeboxes never PASS, correct codeboxes never FAIL, and a FAIL is never downgraded.

Out of scope, and to be listed as deferred in the SUMMARY: WR-07 (tests pinned to live terrain-synth/bassoon files), IN-01 (declaration type order), IN-02 (README title) and IN-03 (bad `buffers=` becomes unsupported).

Q35 locked decisions that still bind (numbered as in 261021-urs-PLAN.md):
- D-01: tree-walking AST interpreter compiled to closures; no eval/exec/compile/__import__.
- D-03: impulse+noise default stimulus with `--input` overrides.
- D-04: unsupported never passes.
- D-05: self-sustain check stays as is.
- D-06: DC is WARN only.
- D-07: genrun.py and tests/dsp_sim/test_bassoon-model.py stay untouched; no save gating.
- The CONTEXT "Specific Ideas" line on if/else ("interpreter may evaluate normally but must not rely on short-circuit side effects") permits taken-branch evaluation. `&&`, `||` and `?:` keep evaluating every operand.

WR-02 user decision (recorded 2026-10-22, binding): "taken-branch + advisory note".
- Keep taken-branch-only if/else execution; no behaviour change.
- Smoke emits an info-level advisory finding, `branch_state`, whenever a stateful call or write sits inside an if/else body. It names the construct and its line, is attached to that codebox's result, and never changes the verdict (a pass stays a pass) or the exit code.
- The interpreter docstring and the dsp_sim README state the taken-branch semantics as the simulator's choice, cite the evidence briefly and say it is unconfirmed in MAX. They never claim equivalence with gen~ as fact.
- CLAUDE.md and .claude/skills/references/genexpr-rules.md are NOT edited. The SUMMARY records the rule conflict as a deferred follow-up: it needs a MAX test before the rule is reworded.
- Regression tests: the advisory fires on a branch-stateful codebox whose verdict stays pass, and buffer-recorder, random-walk and sample-and-hold still pass with the advisory present.

Planning-time evidence (live probes at HEAD 574bf18c; origin/main e942ee81 already contains the Q35 code commit 0accfea9):
- Every review probe reproduces at HEAD with the reviewed verdict (pass, pass, pass, pass, unsupported-with-no-findings, pass, pass, pass+silent, fail).
- Across all 98 codeboxes in patterns/gen and patches/** that parse today, including bassoon.gendsp:
  - none reads a local before definite assignment under the strict no-leak rule below;
  - none has zero outputs, a tab, a Param default outside [min, max], or a local within edit distance 1 of `out`.
- So CR-01, CR-02, WR-03 and WR-04 change no existing verdict. WR-05 only removes FAIL sources. The bassoon parity overrides are all inside their declared ranges, so the WR-04 override clamp cannot move parity.
- WR-02 evidence:
  - The Max 9.2 GenExpr user guide (Resources/C74/docs/userguide/content/gen/gen_genexpr.json, "Branching and Looping") says "different blocks of code will be executed depending on different conditions".
  - RNBO's GenExpr compiler (packages/RNBO/server/node_modules/@rnbo/genexpr_js/genexpr.pegjs, selection_statement) emits a plain ESTree IfStatement.
  - 8 shipped examples put poke/noise/Delay.write inside if blocks and rely on conditional execution: gen~.chopper_repeat, gen~.urn, gen~.data-urn, gen~.buffer.sort, gen~.haar.wavelet, gen~.interpreter-calculator, gen~.ola.granular and gen~.ola.pulsar. chopper_repeat, for example, pokes a segment offset only on a completed zero crossing.
  - In this repo, 3 patterns (buffer-recorder poke at line 14, random-walk noise at line 18, sample-and-hold noise at line 14) and 13 user codeboxes, including the MAX-confirmed terrain-cheby, use stateful calls inside if blocks. A revision-time probe (if/else bodies only, any depth; the if condition excluded) re-confirmed exactly these 16 of 98 parsed codeboxes, so these are the codeboxes the branch_state advisory fires on. The constructs found are poke and noise only. gong-engine has more than 300 poke sites, so the advisory detail must aggregate per construct, not list every site.
- WR-03 evidence: 26 of the 54 codeboxes in /Applications/Max.app/Contents/Resources/Examples/gen/*.maxpat contain tab characters.
- WR-04 evidence:
  - The gen `param` refpage (Gen/docs/refpages/common/gen_common_param.maxref.xml) says "Incoming values out of range will be clamped".
  - RNBO genexpr_js genbo.js (around lines 815-824) inserts `if (p < min) p = min; if (p > max) p = max` after a Param's initial value.

Purpose: the smoke test is the max-dsp-agent's advisory pre-flight. A vacuous or false verdict sends the agent the wrong way.
Output: fixes in two modules, regression tests in two test files, README updates, and a SUMMARY with the 1 s sweep table and the follow-ups.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@CLAUDE.md
@.planning/quick/261021-urs-implement-q35-in-planning-reviews-2026-1/261021-urs-REVIEW.md
@.planning/quick/261021-urs-implement-q35-in-planning-reviews-2026-1/261021-urs-CONTEXT.md
@.planning/quick/261021-urs-implement-q35-in-planning-reviews-2026-1/261021-urs-SUMMARY.md
@.claude/skills/references/genexpr-rules.md

QDIR below means .planning/quick/261022-cmr-fix-q35-review-findings-cr-01-cr-02-wr-0.

Interfaces (verified at planning time; line numbers at HEAD 574bf18c):
- src/maxpat/dsp_sim/genexpr_interp.py (1974 lines):
  - module docstring semantics table: lines 35-121. The rows to change are `locals` (44), `Param` (49-52) and `if / else` (65-67).
  - `class Unsupported(construct, line)`: line 153. Its str is `unsupported: <construct> (line N)`.
  - AST dataclasses: lines 313-406, each with `.off`. The relevant node types are Num, Str, Name(name), Unary(a), Bin(a, b), Tern(c, a, b), Call(name, args), Method(obj: str, method, args), Decl, Assign(name, op, expr), ExprStmt(expr), If(cond, then, els or None) and For(init: Assign, cond, step: Assign, body).
  - `_walk_stmts`: line 710. `_stmt_exprs`: line 724. `_IN_NAME`/`_OUT_NAME`: lines 734-735.
  - `@dataclass class Codebox`: line 744, fields code, n_in, n_out, params, warnings, decls, body, _locals, _ignored. `build()`: line 757.
  - `parse_codebox`: lines 774-868.
    - Params are resolved at 811-822: `p["default"]` becomes 0.0 when it is None and there are no args.
    - Locals are collected at 824-855. The `_ignored` ids are assignments to GEN_CONSTANTS names.
  - `_Builder.__init__`: line 1302. pvals are built at 1308-1313, where an unknown override raises ValueError.
  - `_Builder.stmt` If branch: lines 1646-1671 (taken branch only).
  - `Program.run`: line 1931. It returns `[]` when n_out == 0.
- src/maxpat/dsp_sim/smoke.py (781 lines):
  - `Finding(check, severity, corner, output, detail)`: line 82. The severity docstring reads fail | warn.
  - `_driven_checks(run, samplerate, full=True)`: line 351. The silence check is at 386-396.
  - `smoke_codebox`: lines 469-552. The docstring at 483-484 says keys beyond n_in are ignored. Parse try/except: 493-500. specs/any_default/all_default/driven/ring: 502-510. The corner loop sits inside one try at 516-542. The verdict is at 544-552.
  - `_exit_code` (verdict-based): line 691. `_format_text`: line 700, printing `  {SEVERITY} {check} [{corner}] {out|codebox}: {detail}`. `_report_dict`: line 724.
- tests/dsp_sim/test_genexpr_interp.py:
  - helpers `run(code, inputs=None, n=8, **build)` and `unsupported(code, match, n=1, **build)`: lines 34-48;
  - `test_locals_reset_every_sample` (`x = x + 1; out1 = x;`): line 117. It is exactly the read-before-assign form CR-01 rejects;
  - the parity test `test_bassoon_parity_with_genrun`: line 429.
- tests/dsp_sim/test_smoke.py:
  - `_gendsp(tmp_path, name, code, extra_boxes=())`: line 24;
  - `test_buffer_option_resizes_buffer`: line 354. Lines 365-372 assert a `silence` FAIL at `loop=min (0)` for buffer-player (0 inlets) with a 1000-frame buffer. That is the WR-05 false-FAIL class: a one-shot player that has finished playing is correct;
  - the fixture tests `test_history_latch_fails_self_sustain`, `test_tanh_over_tanh_delay_fixture_fails_self_sustain` and `test_stable_twin_passes`: lines 153-176;
  - `test_pattern_passes` (0.25 s): line 227.
- Pattern inlet counts: buffer-player, noise-generator, random-walk and master-clock have 0 inlets; simple-reverb has 2; every other pattern has 1. Every pattern has at least 1 output.
- Baseline: `python3 -m pytest tests/dsp_sim -q -p no:cacheprovider` gives 476 passed, 4 xfailed (17 s). src/, tests/, patches/ and patterns/ are clean, and the stash list is empty. The last full run took about 161 s.
- .planning/quick/261021-urs-implement-q35-in-planning-reviews-2026-1/junit_diff.py exists in the main checkout but is untracked, so an agent worktree will not have it.
</context>

<tasks>

<task type="tracer" tdd="true">
  <name>Task 1 (tracer): CR-01 + CR-02 end to end: uninitialized locals and zero-output codeboxes are unsupported through parse_codebox -> smoke_codebox -> CLI exit 3, with the lint plumbing (output_typo, tab_char per WR-03)</name>
  <files>src/maxpat/dsp_sim/genexpr_interp.py, src/maxpat/dsp_sim/smoke.py, tests/dsp_sim/test_genexpr_interp.py, tests/dsp_sim/test_smoke.py</files>
  <precondition>`git merge-base --is-ancestor 0accfea9 HEAD` succeeds (the Q35 code is in the tree), and `git status --porcelain src tests patches patterns` is empty.</precondition>
  <read_first>
    - src/maxpat/dsp_sim/genexpr_interp.py: lines 35-70 (semantics table), 696-868 (walk helpers, Codebox, parse_codebox)
    - src/maxpat/dsp_sim/smoke.py: lines 469-552 (smoke_codebox)
    - tests/dsp_sim/test_genexpr_interp.py: lines 34-48 and 110-125; tests/dsp_sim/test_smoke.py: lines 24-84
    - .planning/quick/261021-urs-implement-q35-in-planning-reviews-2026-1/261021-urs-REVIEW.md: CR-01, CR-02, WR-03
  </read_first>
  <behavior>
    - CR-01 (interpreter, via `unsupported(...)` matching "local 'y'" or the named local):
      - The review probe `if (in1 > 0) {\n y = 1;\n} else {\n y = 0.5;\n}\nout1 = y * in1;` raises Unsupported naming 'y', with line 6.
      - `out1 = y;\ny = in1;` raises, line 1.
      - `if (in1 > 0) { y = 1; } out1 = y;` raises.
      - `y += in1; out1 = y;` raises (a compound assignment reads its target).
      - `for (i = 0; i < 4; i += 1) { acc += 1; } out1 = acc;` raises for 'acc'.
      - `for (i = 0; i < 4; i += 1) { t = i; } out1 = i;` raises for 'i' (the counter does not leak).
    - CR-01 forms that still run:
      - `y = 0; if (in1 > 0) { y = 1; } else { y = 0.5; } out1 = y * in1;` with in1 = [1, -1] gives out1 = [1.0, -0.5].
      - The block-local `if (in1 > 0) { t = in1 * 2; out1 = t; }` runs.
      - The loop-carried form `x = in1; t0 = 1; t1 = x; acc = t0 + t1; for (i = 2; i < 6; i += 1) { t2 = 2 * x * t1 - t0; t0 = t1; t1 = t2; acc += t2; } out1 = acc;` runs.
      - `e = 5; out1 = e;` still runs with its constant warning.
    - `test_locals_reset_every_sample` is replaced by `test_local_read_before_assignment_is_unsupported`, holding the read-before-assign cases above. Its old codebox `x = x + 1; out1 = x;` is now Unsupported.
    - CR-01 (smoke): `main(["smoke", <gendsp of the review if/else probe>, "--seconds", "0.1"])` returns 3. The output contains UNSUPPORTED and 'y'.
    - CR-02 (smoke):
      - `smoke_codebox("ou1 = in1;", seconds=0.1)` and `smoke_codebox("Data d(10);\npoke(d, in1, 0, 0);", seconds=0.1)` give verdict unsupported, reason containing "no outN outputs" and corners 0. The CLI on the typo gendsp returns 3.
      - `out1 = in1; ou2 = in1 * 2;` gives pass with exactly one `output_typo` WARN (corner `build`) whose detail names 'ou2'.
      - `Out1 = in1; out1 = in1;` gives an output_typo WARN naming 'Out1'.
      - `t1 = in1; out1 = t1;` gives no output_typo.
    - WR-03:
      - `parse_codebox("out1 =\tin1 * 0.5;").lint` is `[("tab_char", <detail containing "line 1">)]`.
      - A tab first appearing on line 2 is reported as line 2.
      - `smoke_codebox("out1 =\tin1 * 0.5;", seconds=0.1)` gives verdict pass with a `tab_char` WARN, and the CLI prints `WARN tab_char`.
  </behavior>
  <action>
**Step 0. Baseline, before any edit.**
- Create QDIR. Write `git rev-parse HEAD` to QDIR/base-sha.txt and `git stash list` to QDIR/stash-list-before.txt.
- Create QDIR/junit_diff.py.
  - Copy .planning/quick/261021-urs-implement-q35-in-planning-reviews-2026-1/junit_diff.py when it exists in the checkout. In an agent worktree it is absent (it is untracked), so recreate it from this contract instead:
    - it loads both junit files and keys each testcase as `classname::name`;
    - status is passed, failed (a failure or error child), xfailed or skipped;
    - exit 1, listing offenders, on REMOVED (in the base, missing from the new run), REGRESS (passed, then not passed), FOREIGN (a new key outside the allowed prefixes) or ADDFAIL (a new key that does not pass);
    - it prints `base= new= added= offenders=`;
    - exit 2 on a bad argument count.
  - The allowed new-key prefixes are `tests.dsp_sim.test_smoke` and `tests.dsp_sim.test_genexpr_interp`.
  - Add one allowed removal: `ALLOWED_REMOVED = {"tests.dsp_sim.test_genexpr_interp::test_locals_reset_every_sample"}`. It is exempt from REMOVED, and the docstring says why: CR-01 replaces it.
- Run `python3 -m pytest -q -p no:cacheprovider --junitxml=QDIR/baseline-junit.xml` and write its exit code to QDIR/baseline-rc.txt.
  - Exit 0 or 1 is allowed, because the gate is the diff.
  - Exit 2 or more means the baseline is broken: stop and report before any edit.

**RED.** Write every `<behavior>` test first: interpreter cases in tests/dsp_sim/test_genexpr_interp.py, smoke and CLI cases in tests/dsp_sim/test_smoke.py, with fixtures through `_gendsp` in tmp_path. Delete `test_locals_reset_every_sample` and add `test_local_read_before_assignment_is_unsupported`. Run both files and confirm the new tests fail.

**GREEN, src/maxpat/dsp_sim/genexpr_interp.py.**
- **`_check_definite_assignment(stmts, defined, local_names, code)`**, a new module function called from parse_codebox after the locals collection, as `_check_definite_assignment(body, set(), set(locals_), code)`. Per CR-01, it walks the statements in order with a set of definitely-assigned local names.
  - Add a helper `_names_read(expr)` that yields Name nodes, recursing through Unary, Bin, Tern, and Call/Method args. Call names and Method objects are strings, not Name nodes, so they are never yielded.
  - **Assign:** check the names its expr reads. When op is not `=`, the target itself is also read. Then add the target to `defined`, unless the assignment is in the parse's ignored-constant set, whose target is a constant and not a local.
  - **ExprStmt:** check its expr.
  - **If:** check cond. Then check `then` with a copy of `defined`, and `els` with another copy. Do NOT merge the branches back afterward: a name first assigned inside a block is local to it. This follows the Max 9.2 user guide ("Gen variables are also local-to-scope") and genexpr-rules.md:14 ("must be initialized before the block"). It deliberately departs from the review's `defined |= t & e` snippet, which would still PASS the review's own if/else probe.
  - **For:** `inner = set(defined)`, then process init (which adds the counter), check cond against inner, check the body sequentially with inner, and check the step with inner. `defined` is unchanged after the loop, so neither the counter nor the body names leak.
  - **What is flagged:** only names in local_names. inN, outN, History, Param, constants, samplerate and Data/Buffer/Delay names are never flagged, and outN keeps its existing build-time handling.
  - **The error:** raise `Unsupported(f"local '{n}' is read before it is assigned on every path (gen~ 'not defined'); assign it before the first read, outside any if/else or for block that sets it", _line_of(code, name_node.off))`.
- **Codebox:** add the field `lint: list = field(default_factory=list)` after `_ignored`. It holds (check, detail) tuples for build-time WARNs. `warnings` (constant-assign strings) stays unchanged, because test_assignment_to_constant_is_ignored_with_warning reads it.
- **output_typo (CR-02):** in parse_codebox, for each local whose name matches `^([A-Za-z]+)(\d+)$`, is not a lowercase `out<digits>`, and whose letter part, lowercased, is within Levenshtein distance 1 of `out`: append `("output_typo", f"line {L}: local '{name}' looks like a misspelled output (outputs are out1..outN); it never reaches an outlet")`. L is the line of its first assignment. Write a small stdlib edit-distance helper, `_edit_distance(a, b)`. `t0` and `t1` are distance 2, so they are not flagged.
- **tab_char (WR-03):** if `"\t" in code`, append `("tab_char", f"line {L}: tab character in the codebox; the codebox safe-construct rules say spaces only (genexpr-rules.md)")`, where L is the line of the first tab. Use a WARN, not Unsupported: Max 9.2's own Examples/gen contain tabs in 26 of 54 codeboxes, so a tab is a project convention, not a confirmed compile error.
- **Docstring:** update the `locals` row: "must be assigned on every path before being read (checked at parse time; gen's 'not defined'); names first assigned inside an if/else or for block are local to it". Add a short line on `lint` (tab_char, output_typo).

**GREEN, src/maxpat/dsp_sim/smoke.py.**
- In smoke_codebox, right after a successful parse: if `cb.n_out == 0`, return `CodeboxResult(label, "unsupported", "codebox has no outN outputs: nothing to check", 0, [])` (CR-02).
- Next to the constant_assign findings, add one `Finding(check, "warn", "build", 0, detail)` per `cb.lint` entry.
- Extend the `Finding.check` docstring list with output_typo and tab_char.

Run `python3 -m pytest tests/dsp_sim/test_genexpr_interp.py tests/dsp_sim/test_smoke.py -q -p no:cacheprovider`. Every test passes, including the bassoon parity test and all 19 patterns at 0.25 s. If a pattern or the bassoon now comes back unsupported, stop and prove the rule against the codebox text before changing anything. The planning probe found zero hits. Never edit patterns/.

Commit only the four task files with explicit `git add <paths>`; never `git add .` or `git stash`. Message: `fix(dsp_sim): uninitialized locals and zero-output codeboxes are unsupported; tab/output-typo lint (quick 261022-cmr CR-01 CR-02 WR-03)`.
  </action>
  <verify>
    <automated>python3 -m pytest tests/dsp_sim/test_genexpr_interp.py tests/dsp_sim/test_smoke.py -q -p no:cacheprovider && python3 -c "from src.maxpat.dsp_sim.smoke import smoke_codebox as s; r=[s(c, seconds=0.1) for c in ('if (in1 > 0) {\n y = 1;\n} else {\n y = 0.5;\n}\nout1 = y * in1;', 'out1 = y;\ny = in1;', 'ou1 = in1;', 'Data d(10);\npoke(d, in1, 0, 0);')]; assert all(x.verdict == 'unsupported' for x in r), [(x.verdict, x.reason) for x in r]; t=s('out1 =\tin1 * 0.5;', seconds=0.1); assert t.verdict == 'pass' and any(f.check == 'tab_char' and f.severity == 'warn' for f in t.findings), t.findings" && test -s .planning/quick/261022-cmr-fix-q35-review-findings-cr-01-cr-02-wr-0/baseline-junit.xml && test -s .planning/quick/261022-cmr-fix-q35-review-findings-cr-01-cr-02-wr-0/junit_diff.py && test "$(cat .planning/quick/261022-cmr-fix-q35-review-findings-cr-01-cr-02-wr-0/baseline-rc.txt)" -le 1</automated>
  </verify>
  <done>
- The two CR-01 probes and the two CR-02 probes are unsupported through smoke_codebox, and the CLI exits 3.
- The output_typo and tab_char WARNs appear as specified, and correct forms (pre-initialised, block-local, loop-carried) still run.
- All 19 patterns pass at 0.25 s, and bassoon parity is green.
- The Step 0 baseline files exist with rc <= 1. One commit holds the four task files.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Verdict and stimulus integrity: per-corner errors keep FAILs (WR-01), Param clamp (WR-04), silence only while an input still changes (WR-05), unused --input warns (WR-06)</name>
  <files>src/maxpat/dsp_sim/smoke.py, src/maxpat/dsp_sim/genexpr_interp.py, tests/dsp_sim/test_smoke.py, tests/dsp_sim/test_genexpr_interp.py</files>
  <read_first>
    - src/maxpat/dsp_sim/smoke.py: lines 81-116 (records), 351-403 (_driven_checks), 469-552 (smoke_codebox, as committed in Task 1), 691-722 (_exit_code, _format_text)
    - src/maxpat/dsp_sim/genexpr_interp.py: lines 811-822 (Param resolution), 1302-1313 (_Builder pvals)
    - tests/dsp_sim/test_smoke.py: lines 180-200 (ring-out tests), 354-373 (test_buffer_option_resizes_buffer)
    - 261021-urs-REVIEW.md: WR-01, WR-04, WR-05, WR-06
  </read_first>
  <behavior>
    - WR-01:
      - The review probe `Param g(1, min=0, max=200000); out1 = in1/0*0 + pow(10,400); for (i = 0; i < g; i += 1) { out1 += 0; }` at 0.1 s gives verdict fail.
      - Its findings include a nonfinite FAIL at `default`, and one finding with check `unsupported` and severity `unsupported` at corner `g=max (200000)` whose detail contains "100000 iterations".
      - corners == 2 (the completed corners). The CLI on its gendsp returns 1 and prints `UNSUPPORTED [g=max (200000)]`.
    - WR-01, partial error and no FAIL: `Param g(1, min=0, max=200000); out1 = in1 * 0.5; for (i = 0; i < g; i += 1) { out1 += 0; }` gives verdict unsupported, a reason containing "1 of 3 corners", and corners == 2.
    - WR-01, collapse: `Param a(1, min=0, max=2); out1 = frobnicate(in1) * a;` gives verdict unsupported and exactly one `unsupported` finding, at corner `all corners`. Its reason equals the legacy text `unsupported: unknown function: frobnicate (line 1)`, and corners == 0. test_unknown_function_is_unsupported stays green unedited.
    - WR-04 (interpreter):
      - `parse_codebox("Param p(5, min=0, max=1); out1 = p;").params[0]["default"] == 1.0`, and the run gives 1.0;
      - `build(params={"p": 9})` gives 1.0, and `{"p": -3}` gives 0.0;
      - `Param p(min=0.5, max=1);` defaults to 0.5;
      - a Param with no min/max is unchanged.
    - WR-04 (smoke): the review probe `Param p(min=0.5, max=1); out1 = in1 / p;` at 0.1 s gives verdict pass, no `silent` finding, and corners == 2 (`default` and `p=max (1)`).
    - WR-05:
      - The review probe `History h(1); out1 = h; h = h * 0.99;` gives pass with no silence finding, and the CLI exits 0.
      - The one-pole DC blocker `History x1(0); History y1(0); y = in1 - x1 + 0.99 * y1; x1 = in1; y1 = y; out1 = y;` with `inputs={1: "const:1"}` at 0.1 s gives pass with no silence finding. At HEAD it FAILs silence.
      - Positive control: `History n(0); n = n + 1; out1 = in1 * (n < 2000);` at 0.25 s on the default stimulus still FAILs silence at `default`.
    - WR-05 test correction: test_buffer_option_resizes_buffer keeps its name and its `dim/channels` assertions. The buffer-player part now asserts that with `buffers={"bufname": (1000, 2)}` the verdict is pass with no silence finding, and that the CLI with `--buffer bufname=1000:2` returns 0. The old assertion encoded the WR-05 bug: a one-shot player that finishes is correct, and the player has no inlets.
    - WR-06:
      - `smoke_codebox("out1 = in1;", seconds=0.1, inputs={5: "const:1"})` gives pass plus exactly one `unused_input` WARN (corner `build`) whose detail contains "--input 5=const:1" and "1 inlet".
      - `inputs={1: "const:1"}` gives no unused_input.
      - `main(["smoke", <gendsp>, "--seconds", "0.1", "--input", "5=const:1"])` returns 0 and prints `WARN unused_input`.
  </behavior>
  <action>
**RED.** Add every `<behavior>` test: smoke cases in tests/dsp_sim/test_smoke.py, clamp cases in tests/dsp_sim/test_genexpr_interp.py. Apply the test_buffer_option_resizes_buffer correction. Run both files and confirm the new tests fail.

**GREEN, src/maxpat/dsp_sim/smoke.py.**
- **WR-01: per-corner errors.**
  - Move the try/except inside the corner loop. It wraps both the nominal and the self-sustain runs of one corner.
  - On `Unsupported` or any other `Exception`, record `Finding("unsupported", "unsupported", corner, 0, detail)` and continue with the next corner. Findings already appended for that corner, such as the nominal run's checks before a small-run error, are kept.
  - detail is `str(exc)` with its leading "unsupported: " removed for an Unsupported, and `interpreter error: <Type>: <msg>` otherwise. Keep each error's full legacy text (`str(exc)` or the interpreter-error string) for the reason.
  - corners is the number of corners that completed without error.
  - When every corner errored with the same detail, replace those findings with one finding at corner `all corners`.
  - Verdict:
    - any `severity == "fail"` gives `fail`, with reason `<n> failing check(s)`, plus `; unsupported at <k> corner(s)` when there are errors;
    - else any error gives `unsupported`, with reason equal to the first error's full legacy text, plus ` (<k> of <M> corners)` when k < M;
    - else `pass`.
  - Severity `unsupported` is a third value next to fail and warn. Update the Finding docstring.
  - In `_format_text`, print a finding of that severity as `  UNSUPPORTED [<corner>] codebox: <detail>`, without the redundant check token. The other lines are unchanged.
  - `_exit_code` stays verdict-based and unchanged.
- **WR-05: the silence gate.**
  - After the signals are built, compute once: `excited = cb.n_in >= 1 and any(np.ptp(sig[d1 - tail_n:d1]) > ACTIVITY_FLOOR for sig in signals)`. (d0, d1) is the driven window, and `tail_n = max(1, int((d1 - d0) * TAIL_FRACTION))` is the tail the silence check already uses.
  - Pass `excited` into `_driven_checks` as a new keyword argument (default True) and run the silence check only when it is true.
  - Change the silence detail's ending to "while an input is still changing".
  - Default stimulus (noise on the tail), phasor and sine inputs stay excited. 0 inlets, const, dc and zero are not.
- **WR-06:** after parse, for each override key k (sorted) with `k > cb.n_in`, add `Finding("unused_input", "warn", "build", 0, f"--input {k}={raw spec} not applied: this codebox has {cb.n_in} inlet(s)")`. Update the smoke_codebox docstring line about ignored keys.

**GREEN, src/maxpat/dsp_sim/genexpr_interp.py (WR-04).**
- In parse_codebox, after the default is resolved, clamp it the RNBO way: below min becomes min, then above max becomes max.
- In `_Builder.__init__`, clamp each `params=` override with the same rule, using that Param's declared min/max. Unknown names still raise ValueError.
- Docstring Param row: "default and overrides clamped to [min, max] (gen param refpage: 'Incoming values out of range will be clamped'; initial-value clamp [ASSUMED for gen~, RNBO genexpr_js clamps it])".

Run `python3 -m pytest tests/dsp_sim -q -p no:cacheprovider`. Everything passes, including test_cli.py, test_bassoon-model.py, parity, the ring-out tests and the 19-pattern test. A clamp can only matter where a default or override is out of range, and the planning probe found none in the repo.

Commit only the four task files. Message: `fix(dsp_sim): per-corner unsupported keeps FAILs, Param clamp, silence only while an input changes, unused --input warns (quick 261022-cmr WR-01 WR-04 WR-05 WR-06)`.
  </action>
  <verify>
    <automated>python3 -m pytest tests/dsp_sim -q -p no:cacheprovider && python3 -c "from src.maxpat.dsp_sim.smoke import smoke_codebox as s; r=s('Param g(1, min=0, max=200000); out1 = in1/0*0 + pow(10,400); for (i = 0; i < g; i += 1) { out1 += 0; }', seconds=0.1); assert r.verdict == 'fail' and any(f.check == 'nonfinite' and f.corner == 'default' for f in r.findings) and any(f.severity == 'unsupported' and f.corner.startswith('g=max') for f in r.findings), (r.verdict, r.findings); p=s('Param p(min=0.5, max=1); out1 = in1 / p;', seconds=0.1); assert p.verdict == 'pass' and p.corners == 2 and not any(f.check == 'silent' for f in p.findings), p; d=s('History h(1); out1 = h; h = h * 0.99;', seconds=0.1); assert d.verdict == 'pass', d.findings; u=s('out1 = in1;', seconds=0.1, inputs={5: 'const:1'}); assert u.verdict == 'pass' and [f.check for f in u.findings if f.check == 'unused_input'] == ['unused_input'], u.findings"</automated>
  </verify>
  <done>
- The WR-01 probe is fail (exit 1) with the nonfinite FAIL and the g=max unsupported finding both kept. A partial error without FAIL is unsupported with a corner count, and an all-corner identical error collapses to the legacy shape.
- The Param clamp holds for defaults and overrides.
- The 0-inlet decay, the const-driven DC blocker and the finished one-shot player pass, while the positive control still FAILs silence.
- unused_input WARNs.
- tests/dsp_sim is fully green. One commit holds the four task files.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: WR-02 per the user decision (taken-branch kept, branch_state INFO advisory, docs say "simulator's choice, unconfirmed in MAX"), docs for every fix, 1 s acceptance sweep and full-suite gate</name>
  <files>src/maxpat/dsp_sim/genexpr_interp.py, src/maxpat/dsp_sim/smoke.py, tests/dsp_sim/test_genexpr_interp.py, tests/dsp_sim/test_smoke.py, src/maxpat/dsp_sim/README.md</files>
  <read_first>
    - src/maxpat/dsp_sim/genexpr_interp.py: lines 35-121 (docstring, as edited by Tasks 1-2), the AST node classes Call/Method/If/For (around 355-406), `_walk_stmts`/`_stmt_exprs` (around 710-731), the Codebox dataclass and parse_codebox as edited by Task 1 (the `lint` field and its population), `_STATEFUL_CALLS` (around line 1898)
    - src/maxpat/dsp_sim/smoke.py: the Finding dataclass, the lint-findings block Task 1 added in smoke_codebox, `_format_text` (the summary warning count)
    - src/maxpat/dsp_sim/README.md: lines 104-226 (the smoke section)
    - 261021-urs-REVIEW.md: WR-02; 261021-urs-SUMMARY.md: the "1 s pattern sweep" table (the comparison baseline)
  </read_first>
  <behavior>
    - Taken-branch semantics, pinned (no behaviour change):
      - The WR-02 review probe `History c; if (c > 1e9) { out1 = noise(); } out1 = in1;` at 0.1 s gives verdict pass with no FAIL finding.
      - An untaken noise() does not advance the stream. For `if (in1 > 0) { y = noise(); out2 = y; } out1 = noise();` with seed 7 and n = 4:
        - with in1 all zeros, out1 equals the first 4 draws of `random.Random(7)` mapped through `-1 + 2 * r`;
        - with in1 all ones, out2 equals draws[0::2] and out1 equals draws[1::2] of the first 8 draws.
      - A conditional poke writes only when taken: `Data d(4); if (in1 > 0) { poke(d, 1, 0, 0); } out1 = peek(d, 0, 0);` with in1 = [0, 0, 1, 0] gives [0, 0, 1, 1].
    - branch_state detection (interpreter, `parse_codebox(code).advisories`), per the WR-02 user decision:
      - The review probe gives exactly `[("branch_state", detail)]`, where detail contains "noise() (line 1)" and "unconfirmed in MAX".
      - Each flagged construct fires on its own, parametrized over: `noise()`, `phasor(1)`, `cycle(1)`, `latch(in1, 1)`, `dcblock(in1)`, `poke(d, 1, 0, 0)` (with `Data d(4);`) and `dl.write(in1)` (with `Delay dl(10);`). Each is placed inside an `if (in1 > 0) { ... }` then-body, and the detail names it (`write()` appears as `dl.write()`).
      - It also fires from an else body, from a nested if body, and from a for body inside an if body.
      - Aggregation: `Data d(4);\nif (in1 > 0) {\n poke(d, 1, 0, 0);\n poke(d, 2, 1, 0);\n out1 = noise();\n}` gives one advisory, whose detail contains "poke() x2 (first at line 3)" and "noise() (line 5)", in first-occurrence order.
      - Not flagged, so `advisories == []`:
        - `out1 = noise();` (no if);
        - `if (noise() > 0) { out1 = 1; }` (a top-level if condition runs every sample);
        - `out1 = in1 > 0 ? noise() : 0;` (`?:` evaluates every operand);
        - `History h; if (in1 > 0) { h = in1; } out1 = h;`. A History assignment is not flagged, because conditional assignment is what `if` expresses. Under either reading of the gen rule (taken-branch, or both branches evaluated with condition-selected assignments as the review's alternative describes), the assignment lands only when the condition holds, so there is no divergence to report;
        - `Data d(4); if (in1 > 0) { out1 = peek(d, 0, 0) + dim(d) + channels(d) + selector(1, in1, 0); }` (pure reads).
    - branch_state in smoke (`tests/dsp_sim/test_smoke.py`):
      - `smoke_codebox(<review probe>, seconds=0.1)` gives verdict pass. Exactly one finding has check `branch_state`, with severity `info`, corner `build`, output 0 and a detail containing "noise()".
      - Verdict invariance: the verdict and the set of non-info findings equal those of the same call on a twin with the advisory stripped. Compare `[f for f in r.findings if f.severity != "info"]` against the same code where `noise()` is replaced by `0`.
      - A FAILing codebox stays fail with the advisory present: `History c; if (c > 1e9) { out1 = noise(); } out1 = in1/0*0 + pow(10,400);` gives verdict fail plus the branch_state INFO.
      - CLI: `main(["smoke", <gendsp of the review probe>, "--seconds", "0.1"])` returns 0. Its stdout contains `INFO branch_state [build] codebox:`, and that line comes after the codebox's `<label>: PASS` header. The summary's `N warning(s)` count equals the number of severity-`warn` findings, so the INFO is not counted.
      - `--json` on the same gendsp has exit_code 0, and the codebox's findings include `{"check": "branch_state", "severity": "info", ...}`.
      - Patterns: smoke_file at 0.25 s on patterns/gen/buffer/buffer-recorder.gendsp, patterns/gen/random/random-walk.gendsp and patterns/gen/random/sample-and-hold.gendsp each gives verdict pass with exactly one branch_state INFO. The details contain "poke() (line 14)", "noise() (line 18)" and "noise() (line 14)" respectively.
  </behavior>
  <action>
**WR-02 decision (user, 2026-10-22, binding: "taken-branch + advisory note").**
- Keep the interpreter's taken-branch-only `if`. `_Builder.stmt` and Program semantics do not change.
- Make the divergence risk visible: a `branch_state` INFO advisory on every codebox with a stateful call or write inside an if/else body. It never changes the verdict, the exit code or the warning count.
- The docs present taken-branch as the simulator's choice, with brief evidence, and say it is unconfirmed in MAX. They must not claim equivalence with gen~ as fact.
- Do NOT edit CLAUDE.md or .claude/skills/references/genexpr-rules.md. The SUMMARY records the conflict with genexpr-rules.md:13 and the CLAUDE.md Gen~ bullet ("both branches always execute") as a deferred follow-up: it needs a MAX test before the rule is reworded.
- The alternatives the review offered stay rejected: unsupported would regress buffer-recorder, random-walk, sample-and-hold and 13 user codeboxes, and running both branches would make buffer-recorder record unconditionally.

**RED.** Write every `<behavior>` test first.
- In tests/dsp_sim/test_genexpr_interp.py: the two pinned-semantics cases, then the branch_state detection cases. The flagged-construct cases are one parametrized test; the not-flagged cases are another.
- In tests/dsp_sim/test_smoke.py: the review-probe smoke, invariance, FAIL-stays-fail, CLI text, CLI JSON and three-pattern cases. Build gendsp fixtures with `_gendsp` in tmp_path.
- Run both files. The pinned-semantics and plain-verdict assertions pass already, because a planning probe confirmed them at HEAD. If one of those fails, stop and investigate before changing any semantics. The advisory assertions must fail.

**GREEN, src/maxpat/dsp_sim/genexpr_interp.py.**
- **Codebox:** add the field `advisories: list = field(default_factory=list)` after the `lint` field Task 1 added. It holds (check, detail) tuples for build-time INFO findings. Keep it separate from `lint`, so `lint` stays WARN-only and Task 1's `lint == [("tab_char", ...)]` assertions hold.
- **`_BRANCH_STATEFUL_CALLS`:** add the module constant `frozenset({"noise", "phasor", "cycle", "latch", "dcblock", "poke"})`. It is the subset of `_STATEFUL_CALLS` whose call site keeps state or writes. `peek`, `dim`, `channels`, `selector`, `mc_channel` and `mc_channelcount` are pure reads and are excluded. Any Method whose method is `write` is also flagged, named `<obj>.write()`.
- **`_branch_state_advisory(body, code)`:** a new module function called from parse_codebox right after the lint population. When it finds anything, its result is appended to `advisories`.
  - It walks the statements with a flag `inside`, False at the top level.
  - For an If, its cond is scanned only when `inside` is True; a top-level condition runs every sample. Its then and els bodies are walked with `inside=True`.
  - For a For, init.expr, cond and step.expr are scanned when `inside` is True, and its body is walked with the current `inside`.
  - For an Assign or ExprStmt, the expr is scanned when `inside` is True.
  - Scanning recurses through Unary, Bin, Tern, Call args and Method args, and records (construct, line). construct is `<name>()` for a Call in `_BRANCH_STATEFUL_CALLS`, or `<obj>.write()` for a write Method. line is `_line_of(code, node.off)`.
  - A History assignment is not flagged. Conditional assignment is what `if` expresses, and both readings of the gen rule agree on it.
  - Aggregate by construct, in order of first occurrence. Each entry is `<construct> (line L)` for one site, or `<construct> x<k> (first at line L)` for k > 1. Entries are joined by ", ". gong-engine has more than 300 poke sites, so the detail must not list them all.
  - Return at most one `("branch_state", f"{entries} inside an if/else branch: the simulator runs only the taken branch, so a stateful call there advances or writes only when its branch runs (simulator's choice, unconfirmed in MAX; genexpr-rules.md says both branches execute)")`.
- No change to `_Builder`, Program or any run-time path. The detection is a parse-time AST walk, per D-01: no eval, exec or compile.

**GREEN, src/maxpat/dsp_sim/smoke.py.**
- In smoke_codebox, right after the lint WARN findings Task 1 added, add one `Finding(check, "info", "build", 0, detail)` per `cb.advisories` entry.
- Extend the Finding docstring: check gains `branch_state`, and severity reads fail | warn | unsupported | info.
- The verdict computation, `_exit_code` and the `_format_text` warning count (`severity == "warn"`) stay unchanged, so an INFO never moves the verdict, the exit code or the warning count. `_format_text` already prints the INFO line as `  INFO branch_state [build] codebox: <detail>` under the codebox's label header, and `_report_dict` emits it with `"severity": "info"`. Do not change either function.

Run `python3 -m pytest tests/dsp_sim/test_genexpr_interp.py tests/dsp_sim/test_smoke.py -q -p no:cacheprovider`. Everything passes, including the 19-pattern test at 0.25 s. That test asserts verdicts only, so the three advisories do not affect it.

**Docs.**
- **genexpr_interp.py docstring:**
  - Replace the `if / else` row with: "only the taken branch's statements run. This is the simulator's choice and is unconfirmed in MAX. The Max 9.2 GenExpr guide ('Branching and Looping'), RNBO genexpr_js (it emits an IfStatement) and shipped Examples/gen such as gen~.chopper_repeat point to conditional execution, while genexpr-rules.md says both branches always execute. A stateful call (noise, phasor, cycle, latch, dcblock, poke, Delay write) inside a branch therefore advances or writes only when that branch runs. smoke reports each such codebox with an INFO `branch_state` finding".
  - Next to the `lint` line Task 1 added, add a line on `advisories` (branch_state, INFO).
- **src/maxpat/dsp_sim/README.md**, in the smoke section only (the title and Scope stay unchanged: IN-02 is out of scope):
  - Checks table:
    - `silence`: the check runs only when some inlet still changes over the tail of the driven window (ptp > `ACTIVITY_FLOOR`). It is skipped for 0-inlet codeboxes and all-const/zero inputs. Detail ends "while an input is still changing".
    - New rows: `unsupported` (per corner, severity UNSUPPORTED; identical all-corner errors collapse to `all corners`), `tab_char` WARN, `output_typo` WARN, `unused_input` WARN, and `branch_state` INFO. The branch_state row lists the flagged constructs (noise, phasor, cycle, latch, dcblock, poke, `<delay>.write()`), says that if conditions, `?:` operands, History assignments and pure reads are not flagged, and says it never changes the verdict or the exit code.
  - A verdict-rules paragraph: fail beats unsupported beats pass; the reason gives `<k> of <M> corners`; `corners` counts the completed corners; the severity values are fail, warn, unsupported and info (also in the JSON); info never changes the verdict, the exit code or the summary's warning count.
  - Corners paragraph: Param defaults and overrides are clamped to [min, max], with the refpage and RNBO evidence.
  - Interpreter paragraph:
    - definite assignment (gen 'not defined'; block-local names; for-loop names do not leak);
    - a codebox with no outN is unsupported;
    - the `[ASSUMED]` list gains the initial-value clamp.
  - Limits:
    - Replace the if bullet with: "`if` runs only the taken branch. This is the simulator's choice and is unconfirmed in MAX. The Max 9.2 GenExpr guide, RNBO genexpr_js and shipped Examples/gen (e.g. gen~.chopper_repeat) point to conditional execution, while genexpr-rules.md says both branches always execute. So a stateful call in a branch advances or writes only when that branch runs, and smoke flags each such codebox with an INFO `branch_state` finding. A MAX test is pending." The bullet must not state that the simulator matches gen~.
    - Add: a constant-driven generator that dies (all inlets const) is not caught by silence.
    - Add: `--input` keys above a codebox's inlet count warn `unused_input`.
  - The `--input` flag row mentions the unused_input WARN. The SPEC tables are unchanged.
- **smoke.py module docstring "Checks" bullet:** add that tab_char, output_typo and unused_input are WARN, that a codebox with no outputs is unsupported, and that a stateful call inside an if/else branch is an INFO advisory (branch_state) that never changes the verdict.

**Acceptance and final gate.** These are the `<automated>` commands.
- **19-pattern sweep.** Run all 19 patterns at the 1 s default through smoke_file, with `{1: "phasor:2"}` for swing-generator and subdivider. Every verdict must be pass, and the set of patterns carrying a branch_state INFO must be exactly buffer-recorder, random-walk and sample-and-hold.
  - Then print a per-pattern table (verdict, corners, warnings by check and corner, advisories) and compare it with the 261021-urs SUMMARY table.
  - Planning analysis expects identical WARNs: no new WARN fires on any pattern, the silence gate only removes FAIL sources, and no pattern default is out of range. The only new findings are the three branch_state INFOs.
  - Record any difference and explain it. A pattern that stops passing is a blocker: prove the interpreter right first, never edit patterns/.
- **Fixture tests:** test_history_latch_fails_self_sustain, test_tanh_over_tanh_delay_fixture_fails_self_sustain (1 s), test_stable_twin_passes and test_bassoon_parity_with_genrun all run inside the first `tests/dsp_sim` command of `<verify>`. They are not re-run separately.
- **Bassoon:** the .maxpat JSON check from the Q35 gate.
- **Full suite.**
  - `rm -f QDIR/final-junit.xml` first, then `python3 -m pytest -q -p no:cacheprovider --junitxml=QDIR/final-junit.xml`. Its exit code must be <= 1; 2 or more fails the gate whatever the diff says.
  - Then `python3 QDIR/junit_diff.py QDIR/baseline-junit.xml QDIR/final-junit.xml` must exit 0. The only allowed removal is test_locals_reset_every_sample.
- `git status --porcelain patches patterns` is empty, and `git stash list` equals QDIR/stash-list-before.txt.
- `git diff --quiet $(cat QDIR/base-sha.txt) -- patches/bassoon-model/tools/genrun.py tests/dsp_sim/test_bassoon-model.py tests/dsp_sim/test_cli.py` succeeds.

Commit only the task files changed in this task, with explicit `git add <paths>`. Message: `feat+docs(dsp_sim): branch_state INFO advisory for stateful calls in if/else (taken-branch kept, unconfirmed in MAX); document Q35 review fixes (quick 261022-cmr WR-02)`.
  </action>
  <verify>
    <automated>python3 -m pytest tests/dsp_sim tests/test_doc_signatures.py tests/test_agent_skills.py -q -p no:cacheprovider && grep -q "unconfirmed in MAX" src/maxpat/dsp_sim/README.md && grep -q "branch_state" src/maxpat/dsp_sim/README.md && python3 -c "import src.maxpat.dsp_sim.genexpr_interp as g; assert 'unconfirmed in MAX' in g.__doc__ and 'branch_state' in g.__doc__" && python3 -c "import glob; from src.maxpat.dsp_sim.smoke import smoke_file; ov={'swing-generator': {1: 'phasor:2'}, 'subdivider': {1: 'phasor:2'}}; fs=sorted(glob.glob('patterns/gen/**/*.gendsp', recursive=True)); assert len(fs) == 19, fs; res=[(f.rsplit('/', 1)[1][:-7], r) for f in fs for r in smoke_file(f, inputs=ov.get(f.rsplit('/', 1)[1][:-7], {}))]; bad=[(n, r.label, r.verdict, r.reason, r.findings) for n, r in res if r.verdict != 'pass']; assert not bad, bad; bs=sorted(n for n, r in res if any(x.check == 'branch_state' and x.severity == 'info' for x in r.findings)); assert bs == ['buffer-recorder', 'random-walk', 'sample-and-hold'], bs" && python3 -m src.maxpat.dsp_sim smoke patches/bassoon-model/generated/bassoon-model.maxpat --corners default --seconds 0.1 --input 1=const:220 --input 2=const:0.6 --json | python3 -c "import sys, json; r=json.load(sys.stdin); assert len(r['codeboxes']) == 1 and r['codeboxes'][0]['verdict'] != 'unsupported' and 'bassoon.gendsp' in r['codeboxes'][0]['label'], r" && rm -f .planning/quick/261022-cmr-fix-q35-review-findings-cr-01-cr-02-wr-0/final-junit.xml && { python3 -m pytest -q -p no:cacheprovider --junitxml=.planning/quick/261022-cmr-fix-q35-review-findings-cr-01-cr-02-wr-0/final-junit.xml >/dev/null; rc=$?; echo "full-suite pytest rc=$rc"; test "$rc" -le 1; } && python3 .planning/quick/261022-cmr-fix-q35-review-findings-cr-01-cr-02-wr-0/junit_diff.py .planning/quick/261022-cmr-fix-q35-review-findings-cr-01-cr-02-wr-0/baseline-junit.xml .planning/quick/261022-cmr-fix-q35-review-findings-cr-01-cr-02-wr-0/final-junit.xml && test -z "$(git status --porcelain patches patterns)" && diff <(git stash list) .planning/quick/261022-cmr-fix-q35-review-findings-cr-01-cr-02-wr-0/stash-list-before.txt && git diff --quiet "$(cat .planning/quick/261022-cmr-fix-q35-review-findings-cr-01-cr-02-wr-0/base-sha.txt)" -- patches/bassoon-model/tools/genrun.py tests/dsp_sim/test_bassoon-model.py tests/dsp_sim/test_cli.py CLAUDE.md .claude/skills/references/genexpr-rules.md</automated>
  </verify>
  <done>
- The WR-02 probe passes (CLI exit 0) with exactly one `branch_state` INFO naming noise(). The untaken-branch noise and conditional-poke semantics are pinned by tests.
- The advisory fires for every flagged construct and position, aggregates per construct, and stays silent for if conditions, `?:`, History assignments and pure reads. It never changes a verdict: pass stays pass, fail stays fail, and the warning count is unchanged.
- buffer-recorder, random-walk and sample-and-hold pass with their advisory, at 0.25 s in the tests and at 1 s in the sweep. No other pattern gets one.
- The docstring and README state taken-branch as the simulator's choice, cite the evidence and say it is unconfirmed in MAX. CLAUDE.md and genexpr-rules.md match base-sha.
- The README documents every new finding, the verdict rules, the clamp, definite assignment and the silence gate.
- All 19 patterns pass at 1 s. The tanh/tanh(g) fixtures still FAIL self_sustain and the twin passes. Bassoon parity holds.
- The full pytest run gives rc <= 1 with a clean junit diff. patches/patterns are untouched, the stash list is unchanged, and genrun.py, test_bassoon-model.py and test_cli.py match base-sha.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| .maxpat/.gendsp codebox text -> parse_codebox | Untrusted text is parsed offline; the new static walks run on its AST. |
| smoke verdict -> max-dsp-agent / user | A false PASS or false FAIL misleads the agent's pre-flight. |
| this task -> repo | It must not touch patches/, patterns/, genrun.py or the legacy CLI. |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-cmr-01 | Repudiation (false pass) | parse_codebox / smoke_codebox verdict | high | mitigate | CR-01 definite assignment and CR-02 zero-output make these codeboxes unsupported. WR-01 keeps FAILs across corner errors and never collapses a FAIL into unsupported. Every review probe is a regression test. |
| T-cmr-02 | Repudiation (false fail) | silence check | medium | mitigate | WR-05 requires an inlet that still changes over the tail. A positive-control test keeps the true-silence FAIL alive. |
| T-cmr-03 | Tampering (regression) | patterns, bassoon parity, legacy CLI, wider suite | high | mitigate | The planning probe found zero affected repo codeboxes. Task 3 runs the 1 s 19-pattern sweep, the fixture tests, the 1e-12 parity and the full-suite junit diff against the Step 0 baseline (one allowlisted removal), and checks base-sha byte-identity of genrun.py, test_bassoon-model.py and test_cli.py. |
| T-cmr-04 | Elevation of privilege | genexpr_interp.py / smoke.py | high | mitigate | The fixes are pure AST walks and stdlib helpers. The existing AST guard test (no eval/exec/compile/__import__, no importlib) and the no-save-gate import test stay green in every task's run. |
| T-cmr-05 | Denial of service | new static walks | low | accept | They are linear in AST size. Statement nesting is already bounded by the parser (a RecursionError becomes Unsupported), and the edit distance runs only on short local names. |
| T-cmr-06 | Repudiation (silent unfaithful pass) | taken-branch if/else with stateful calls in a branch | medium | mitigate | Per the WR-02 user decision, `_branch_state_advisory` attaches a `branch_state` INFO to every such codebox, naming each construct and its line. The docs call taken-branch the simulator's choice, unconfirmed in MAX. The SUMMARY defers a MAX test before genexpr-rules.md:13 is reworded. Tests pin that the advisory fires, that it never moves the verdict, and that the three affected patterns still pass. |
| T-cmr-SC | Tampering | npm/pip/cargo installs | high | mitigate | Nothing is installed; the work uses stdlib plus the existing numpy. |
</threat_model>

<verification>
- The review probes, each now a test:
  - CR-01 x2 and CR-02 x2 are unsupported (exit 3);
  - WR-01 is fail (exit 1) with both findings kept;
  - WR-02 passes with pinned taken-branch semantics and one `branch_state` INFO (exit 0);
  - WR-03 passes with a tab_char WARN;
  - WR-04 passes at p = 0.5 with 2 corners;
  - WR-05 decay and DC blocker pass, and the positive control still FAILs;
  - WR-06 gives an unused_input WARN.
- `python3 -m pytest tests/dsp_sim -q -p no:cacheprovider` is green, including parity, test_cli.py and test_bassoon-model.py.
- All 19 patterns pass at 1 s with the phasor overrides, with branch_state INFOs on exactly buffer-recorder, random-walk and sample-and-hold. The tanh/tanh(g) fixtures still FAIL self_sustain.
- CLAUDE.md and .claude/skills/references/genexpr-rules.md are byte-identical to base-sha.
- The full suite gives rc <= 1 with a clean junit diff. patches/ and patterns/ are untouched, and the stash list is unchanged.
</verification>

<success_criteria>
- CR-01, CR-02 and WR-01..WR-06 are fixed exactly, each with a regression test that reproduces the review's probe.
- WR-02 is resolved per the user decision of 2026-10-22. The taken-branch semantics are kept and pinned, and every branch-stateful codebox gets a verdict-neutral `branch_state` INFO. The docs call it the simulator's choice, unconfirmed in MAX. The rule conflict is deferred to a MAX test, with CLAUDE.md and genexpr-rules.md untouched. WR-03 is a WARN, backed by the Max examples evidence.
- No pattern, fixture, parity or legacy-CLI regression.
- D-01, D-04, D-05, D-06 and D-07 still hold.
</success_criteria>

<output>
Create `.planning/quick/261022-cmr-fix-q35-review-findings-cr-01-cr-02-wr-0/261022-cmr-SUMMARY.md` when done. Include:
- one row per finding: the fix, the test name(s) and the commit;
- the WR-02 user decision (2026-10-22, "taken-branch + advisory note") with its evidence. List the codeboxes the branch_state advisory fires on: the 3 patterns plus the 13 user codeboxes from the planning probe, or any difference found. Record the deferred follow-up: genexpr-rules.md:13 and the CLAUDE.md Gen~ "both branches always execute" rule conflict with the simulator's taken-branch choice and its evidence; the conflict needs a MAX test before the rule is reworded, and neither file was edited;
- the WR-03 evidence (26/54 shipped example codeboxes contain tabs);
- the CR-01 departure from the review snippet (no branch merge) and why;
- the test_locals_reset_every_sample replacement and the test_buffer_option_resizes_buffer correction;
- the 1 s per-pattern verdict/warning table and its diff against 261021-urs;
- the baseline and final pytest exit codes and the junit_diff output;
- deferred items: WR-07, IN-01, IN-02, IN-03, plus the note that `else if` is valid GenExpr per the Max 9.2 guide but stays Unsupported here (out of scope).
</output>

<source_audit>
| SOURCE | ID | Item | Task | Status |
|--------|----|------|------|--------|
| GOAL | - | Fix Q35 review findings CR-01, CR-02, WR-01..WR-06 | 1-3 | COVERED |
| REQ | CR-01 | locals read before assignment / assigned only in if/else are unsupported | 1 | COVERED |
| REQ | CR-02 | zero-output codebox is not a pass; misspelled-output warn | 1 | COVERED |
| REQ | WR-01 | per-corner error keeps earlier FAILs | 2 | COVERED |
| REQ | WR-02 | stateful calls in untaken branches: faithful-to-gen or flagged | 3 (user decision 2026-10-22: taken-branch kept + branch_state INFO advisory; docs say simulator's choice, unconfirmed in MAX; rule conflict deferred to a MAX test) | COVERED |
| REQ | WR-03 | tab characters flagged | 1 (WARN) | COVERED |
| REQ | WR-04 | Param defaults/overrides clamped to [min, max] | 2 | COVERED |
| REQ | WR-05 | silence check only with active (changing) input | 2 | COVERED |
| REQ | WR-06 | unused `--input` key surfaced | 2 | COVERED |
| CONTEXT | D-01 | AST closures, no eval | 1-3 (no new eval; AST guard test stays green) | COVERED |
| CONTEXT | D-04 | unsupported never passes | 1, 2 | COVERED |
| CONTEXT | D-05 | self-sustain unchanged; tanh/tanh(g) fixture still FAILs | 3 gate | COVERED |
| CONTEXT | D-06 | DC stays WARN | 2 (verdict rules unchanged for dc) | COVERED |
| CONTEXT | D-07 | genrun.py + test untouched; no save gate | 3 gate | COVERED |
| CONTEXT | specifics | if/else "interpreter may evaluate normally"; && / || / ?: evaluate all operands | 3 (taken-branch kept; the advisory surfaces the unconfirmed divergence from the "both branches" line) | COVERED |
| USER | WR-02 decision | taken-branch + INFO advisory; docs unconfirmed-in-MAX; no CLAUDE.md / genexpr-rules.md edit; regression tests on the probe + 3 patterns | 3 | COVERED |
| PROMPT | acceptance | 19-pattern 1 s sweep with phasor overrides; tanh fixture; bassoon parity 1e-12 | 3 | COVERED |
| PROMPT | out of scope | WR-07, IN-01, IN-02, IN-03 | - | DEFERRED (listed in SUMMARY) |
</source_audit>
