---
phase: quick-261021-urs
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/maxpat/dsp_sim/genexpr_interp.py
  - src/maxpat/dsp_sim/smoke.py
  - src/maxpat/dsp_sim/cli.py
  - tests/dsp_sim/test_smoke.py
  - tests/dsp_sim/test_genexpr_interp.py
  - src/maxpat/dsp_sim/README.md
  - .claude/skills/max-dsp-agent/SKILL.md
autonomous: true
requirements: [Q35]

estimate:
  # estimate-calibration: factor 1 (sample_count 0), so tokens == raw_tokens.
  # Per task (rebalanced so no task is the bulk): Task 1 ~80k (baseline, interpreter
  # core, driven-window smoke, CLI), Task 2 ~80k (state constructs, self-sustain,
  # genrun parity), Task 3 ~70k (speed pass, .maxpat discovery, flags, acceptance,
  # docs, gate). Each fits one executor pass with room for debugging.
  tokens: 230000
  raw_tokens: 230000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "`python3 -m src.maxpat.dsp_sim smoke <file.gendsp|file.maxpat>` runs every gen~ codebox for 1 s at 44100 Hz by default (D-01). Each codebox runs once with every Param at its default, then once per Param at its declared min and at its declared max, with the other Params at default (D-02). Every inlet gets a 0.25 impulse plus seeded ±0.1 noise for the first half of the run, then zeros (D-03, D-06). The report names the codebox, the corner (e.g. `drive=max (10)`), the output and the check that failed."
    - "Verdicts: NaN/inf, peak > 4.0, permanent silence after excitation and self-sustain are FAIL. DC offset is WARN only (D-06). Self-sustain is a rerun at 0.01× stimulus: a tail that does not scale with it is a FAIL (D-05). Exit codes: 0 = everything passed (warnings allowed), 1 = any FAIL, 2 = usage or read error, 3 = any unsupported (with no FAIL) or nothing to smoke."
    - "Unsupported never passes (D-04). An unsupported GenExpr construct, an unknown identifier, a non-codebox operator in a gen patcher, a missing external .gendsp or an interpreter error gives verdict `unsupported` with the construct and line."
    - "All 19 `patterns/gen/**/*.gendsp` files pass, at 0.25 s in pytest and at the 1 s default in the final gate. swing-generator and subdivider get `--input 1=phasor:2` (D-06); no pattern is allowlisted or xfailed. The `tanh(tap * drive) / tanh(drive)` Delay-feedback codebox FAILs self-sustain at `default`, at `drive=max` and at `feedback=max`. Its `/ drive` twin passes (D-05). The bassoon codebox runs, from bassoon.gendsp and from bassoon-model.maxpat through the sibling `gen~ bassoon` lookup, with `--input 1=const:220 --input 2=const:0.6`. It is not unsupported and gives no NaN."
    - "The interpreter is a tree-walking AST evaluator compiled into nested Python closures (D-01). It never builds source text and never calls eval, exec, compile or __import__; an AST test pins this. On the shipped bassoon codebox it matches patches/bassoon-model/tools/genrun.py sample for sample within 1e-12 (0.1 s, seed 1, two cases)."
    - "Regression and scope (D-07): genrun.py and tests/dsp_sim/test_bassoon-model.py are byte-identical to the Step 0 base. tests/dsp_sim/test_cli.py passes unedited, and legacy `python3 -m src.maxpat.dsp_sim --help` still lists --topology. No module under src/maxpat outside dsp_sim imports smoke or genexpr_interp, so no save gates on it. The final full pytest run exits 0 or 1 (no collection, internal or usage error), its junit diff against the Step 0 baseline is clean, patches/ and patterns/ are untouched, and the stash list is unchanged."
  artifacts:
    - path: "src/maxpat/dsp_sim/genexpr_interp.py"
      provides: "the lexer, Pratt/recursive-descent parser, resolver and closure compiler; Unsupported; parse_codebox -> Codebox.build -> Program.run"
      contains: "class Unsupported"
    - path: "src/maxpat/dsp_sim/smoke.py"
      provides: "codebox discovery (.gendsp, .maxpat, sibling gen~ files), stimulus, corners, the five checks, report, smoke_file/smoke_codebox/smoke_main"
      contains: "def smoke_main("
    - path: "src/maxpat/dsp_sim/cli.py"
      provides: "the early `smoke` dispatch ahead of the legacy parser"
      contains: "== \"smoke\""
    - path: "tests/dsp_sim/test_genexpr_interp.py"
      provides: "interpreter unit tests plus the genrun parity test"
      contains: "def test_bassoon_parity_with_genrun"
    - path: "tests/dsp_sim/test_smoke.py"
      provides: "acceptance: patterns pass, unstable fixture fails, stable twin passes, bassoon runs, unsupported/skipped discovery, CLI/exit codes, AST no-eval guard, no-save-gate guard"
      contains: "tanh(tap * drive) / tanh(drive)"
    - path: "src/maxpat/dsp_sim/README.md"
      provides: "the smoke command: usage, stimulus, corners, the checks and thresholds table, overrides, Buffer/Data backing, semantics assumptions, exit codes, limits, advisory status"
      contains: "dsp_sim smoke"
  key_links:
    - from: "src/maxpat/dsp_sim/cli.py main()"
      to: "src/maxpat/dsp_sim/smoke.py smoke_main"
      via: "early dispatch on argv[0] == 'smoke' before build_parser(); lazy import"
      pattern: "smoke_main("
    - from: "src/maxpat/dsp_sim/smoke.py"
      to: "src/maxpat/dsp_sim/genexpr_interp.py"
      via: "parse_codebox(code) once per codebox, Codebox.build(params=corner) per run"
      pattern: "parse_codebox("
    - from: "src/maxpat/dsp_sim/genexpr_interp.py"
      to: "src/maxpat/genexpr_parse.py"
      via: "mask() before tokenizing; parse_params() as the single source of Param default/min/max"
      pattern: "from src.maxpat.genexpr_parse import"
    - from: "tests/dsp_sim/test_genexpr_interp.py"
      to: "patches/bassoon-model/tools/genrun.py render()"
      via: "module-scoped isolated-import fixture (same pattern as tests/dsp_sim/test_bassoon-model.py genrun fixture)"
      pattern: "genrun.render("
---

<objective>
Implement Q35 from .planning/reviews/2026-10-11-fix-plan.md (§4.4 R9, §5.2). The work has two parts:
- a GenExpr interpreter, src/maxpat/dsp_sim/genexpr_interp.py;
- a `smoke` subcommand for `python -m src.maxpat.dsp_sim`. It runs every gen~ codebox in a .gendsp or .maxpat at the Param corners and reports NaN/inf, peak > 4, DC offset, permanent silence and self-sustain, with an `unsupported` verdict that never passes.

Locked user decisions (from 261021-urs-CONTEXT.md, numbered here for traceability):
- D-01: Tree-walking interpreter. Parse into an AST and compile each node once into a nested Python closure that reads and writes a flat slot list. Generating source text, eval/exec and numba are all out. Keep the per-sample path lean. Add a `--seconds` override (default 1.0); the CLI default stays 1 s at 44.1 kHz.
- D-02: Corners are the default run plus one run per Param at min and one at max, with the other Params at default (1 + 2N). A Param with no declared min or max contributes nothing on that side. The report names the Param and corner that failed.
- D-03: Every inN gets impulse plus noise by default. A per-inlet `--input K=SPEC` override is documented in `--help`. Noise is seeded. The bassoon test uses overrides (in1 is frequency in raw Hz).
- D-04: Codeboxes only. A gen patcher with non-codebox operators (anything beyond in/out/codebox plumbing) is `unsupported`, as is any construct the interpreter does not support. Neither ever passes.
- D-05: Self-sustain/latch check. Rerun each corner at 0.01× stimulus and compare the post-excitation tails (inputs at zero). A tail ratio near 1 is a FAIL. The fixture stays the real `tanh(x*g)/tanh(g)` bug class, not a contrived peak > 4 design.
- D-06: DC offset is a WARN, not a FAIL. Default stimulus: 0.25 impulse plus seeded ±0.1 noise for the first half, then zeros. Pattern tests use `--input` overrides where a pattern needs a control-like input (phasor for swing-generator and subdivider). No per-pattern verdict allowlist.
- D-07: Keep patches/bassoon-model/tools/genrun.py and its test working unchanged. Do not gate saves on smoke (deferred).

Choices made under Claude's Discretion (record them in the README):
- Thresholds: SILENCE_FLOOR 1e-9, ACTIVITY_FLOOR 1e-6, DC_DRIVEN_LIMIT 0.1, DC_TAIL_LIMIT 0.05, SUSTAIN_ABS 0.01, SUSTAIN_RATIO 0.5, TAIL_FRACTION 0.1.
- Exit codes: 0/1/2/3 as in the truths.
- Buffer backing: 48000 frames × 1 channel holding a 220 Hz sine at 0.25, resizable with `--buffer`. Data is zero-filled.
- Report: a text report, plus `--json`.
- genrun.py stays in place, and a parity test proves the interpreter reproduces it.

Purpose: catch unstable or broken gen~ codeboxes offline, before MAX opens them. The motivating example is the stereo-feedback-delay v0.1.0 `tanh/tanh(g)` runaway.
Output: two new modules, a CLI subcommand, two test files, README and SKILL docs.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/quick/261021-urs-implement-q35-in-planning-reviews-2026-1/261021-urs-CONTEXT.md
@.planning/quick/261021-urs-implement-q35-in-planning-reviews-2026-1/261021-urs-RESEARCH.md
@CLAUDE.md
@.claude/skills/references/genexpr-rules.md

Interfaces (verified at planning time):
- src/maxpat/genexpr_parse.py (stdlib only, never raises):
  - `mask(code) -> str` is the same length as `code`; comments and string contents are blanked, and quotes and newlines are kept.
  - `parse_params(code) -> list[dict]` returns keys name/default/min/max. Each value is a float, or None when absent or non-literal.
  - `io_counts(code) -> (max_in, max_out)`.
  - `CONSTANTS` is the 13 lowercase names. It has no uppercase forms and no `phi`.
- src/maxpat/dsp_sim/cli.py:
  - `main(argv=None)` at line 311 calls `build_parser()` (line 73) and has no subcommands.
  - Legacy exit codes are at line 56. The T-01 threat note in the docstring says there is no string evaluation.
  - tests/dsp_sim/test_cli.py calls `main([...])` with the legacy flags.
- src/maxpat/dsp_sim/measure.py: `measure_peak(buf)` (line 98) and `measure_ac_rms(buf)` (line 111) return NaN on non-finite input.
- `from src.maxpat import generate_gendsp; generate_gendsp(code, num_inputs, num_outputs) -> dict`. It returns a top-level patcher with boxes [`in 1` newobj, codebox (`code` key), `out 1` newobj]. `Patcher().add_gen(code, num_inputs, num_outputs)` gives a `gen~` newobj box with an embedded patcher holding a codebox.
- patches/bassoon-model/tools/genrun.py:
  - `render(code, freq, breath_fn, dur=1.0, seed=1, **over) -> (out1, cone_hp)`. It needs its tools dir on sys.path (`from core import analyze, SR`, SR = 44100.0).
  - Isolated-import fixture: tests/dsp_sim/test_bassoon-model.py lines 123-147.
  - Shipped Param dicts: same file, lines 66-89 (SHIPPED, _OFF, _NOT_CODEBOX_PARAMS).
- The bassoon codebox: patches/bassoon-model/generated/bassoon.gendsp, 537 lines, 22 Params, 2 inlets.
  - Constructs: `Data bore(8192)`, `peek(bore, ri, 0)`, `poke(bore, v, wi, 0)`, four `noise()` calls (none inside a ternary arm), ternaries, `&&`, TWOPI/HALFPI.
  - bassoon-model.maxpat holds `gen~ bassoon` with no embedded patcher; the sibling file is `generated/bassoon.gendsp`.
- patches/terrain-synth/generated/terrain-synth.maxpat holds 4 embedded gen~ codeboxes and 2 jit.gen codeboxes.
- External gen~ forms seen in patches/:
  - `gen~ NAME`
  - `gen~ @gen NAME.gendsp`
  - `mc.gen~ NAME @chans 32`
  - Only `newobj` boxes count. Comment boxes often start with "gen~ ...".
- Baseline at planning time: `python3 -m pytest tests/dsp_sim -q` gives 377 passed, 4 xfailed (12 s). patches/, patterns/, src/ and tests/ are clean. The stash list is empty.
</context>

<tasks>

<task type="tracer">
  <name>Task 1 (tracer): `smoke patterns/gen/gain/safe-gain.gendsp` runs end to end: interpreter core, driven-window smoke checks, CLI dispatch</name>
  <files>src/maxpat/dsp_sim/genexpr_interp.py, src/maxpat/dsp_sim/smoke.py, src/maxpat/dsp_sim/cli.py, tests/dsp_sim/test_smoke.py</files>
  <read_first>
    - src/maxpat/genexpr_parse.py: lines 1-60 (contracts, DECL_TYPES, CONSTANTS), 112-127 (mask), 350-394 (_literal, parse_params), 502-507 (io_counts)
    - src/maxpat/dsp_sim/cli.py: lines 1-70 (docstring, T-01, _EXIT_CODE), 73-100 (build_parser description), 311-350 (main)
    - src/maxpat/dsp_sim/measure.py: lines 98-131
    - patterns/gen/gain/safe-gain.gendsp, patterns/gen/dsp/compressor.gendsp (codebox text)
    - 261021-urs-RESEARCH.md: "Architecture Patterns", "GenExpr Semantics to Implement", "Stimulus and Verdicts", "Common Pitfalls"
    - .claude/skills/references/genexpr-rules.md: "Basics", "In-loop saturation", "Built-in constant names", "Codebox safe-construct rules"
  </read_first>
  <action>
QDIR below means .planning/quick/261021-urs-implement-q35-in-planning-reviews-2026-1.

**Step 0. Baseline, before any edit.**
- Write `git rev-parse HEAD` to QDIR/base-sha.txt and `git stash list` to QDIR/stash-list-before.txt.
- Copy .planning/quick/261021-olv-max-verify-live-mode-via-max-bridge/junit_diff.py to QDIR/junit_diff.py. The source is untracked, so in an agent worktree read it from /Users/taylorbrook/Dev/MAX/.planning/quick/261021-olv-max-verify-live-mode-via-max-bridge/junit_diff.py. In the copy only, change the `ours` predicate so that the only new tests counted as ours are keys starting with `tests.dsp_sim.test_smoke` or `tests.dsp_sim.test_genexpr_interp`. Update its docstring to match, and leave the original untouched.
- Run `python3 -m pytest -q -p no:cacheprovider --junitxml=QDIR/baseline-junit.xml`, write its exit code to QDIR/baseline-rc.txt, and record the counts. Exit 1 (pre-existing failures) is allowed, because the gate is the diff. Exit 2 or more means the baseline itself is broken (collection, internal or usage error): stop and report it before any edit.

**Part A: src/maxpat/dsp_sim/genexpr_interp.py, the interpreter core (D-01).** Write a module docstring stating:
- the pipeline;
- that this is an AST evaluator: closures, no generated source text, no string evaluation;
- the semantics table, with [ASSUMED] tags carried over from RESEARCH.

Keep it stdlib plus numpy. Import `mask`, `parse_params`, `io_counts` and `CONSTANTS` from src.maxpat.genexpr_parse.
- **Errors:**
  - `class Unsupported(Exception)` has attributes `construct: str` and `line: int | None`. Its str is `unsupported: <construct> (line N)`.
  - Every syntax error or construct outside the subset raises Unsupported, never another exception type.
  - A RecursionError during parsing becomes Unsupported("expression nesting too deep").
- **Constants:**
  - `GEN_CONSTANTS: dict[str, float]` holds Q22's 13 lowercase names, plus `phi` (golden ratio), plus the uppercase `PI`, `TWOPI` and `HALFPI`. The uppercase forms are MAX-confirmed in shipped codeboxes. No other uppercase names.
  - Caps: `LOOP_CAP = 100_000` iterations per for-loop per sample, and `STATE_CAP = 50_000_000` total Delay+Data+Buffer samples.
- **Lexer:** run it over `mask(code)`.
  - Token kinds:
    - NUMBER: `1`, `1.`, `.5`, `1e-1`, `1.5E+3`;
    - IDENT;
    - STRING: content sliced from the ORIGINAL code at the same offsets, because mask blanks string contents;
    - punctuation and operators: `( ) { } , ; . ? : = += -= *= /= == != < > <= >= && || + - * / %`.
  - Any other character, including `!` (alone), `++`, `--`, `[`, `]`, bitwise operators and `@`, is Unsupported with the offending text.
  - Each token carries an offset. Line = `code.count("\n", 0, off) + 1`.
- **Parser:** recursive descent for statements, Pratt for expressions. Parse the full grammar here, including the constructs Task 2 executes.
  - Statements:
    - declarations: `Param|History|Delay|Buffer|Data` NAME [ `(` args `)` ] { `,` NAME [ `(` args `)` ] } `;`, where args may hold `key=value` kwargs;
    - `if (expr) { ... } [else { ... }]`. Nest freely. `else if` and a brace-less if/else body are Unsupported;
    - `for (init; cond; step) { ... }`. A for nested inside a for is Unsupported("nested for loop");
    - assignment `NAME (=|+=|-=|*=|/=) expr ;`;
    - expression statement `expr ;`;
    - an empty `;`.
  - Unsupported statements: `while`, `return`, `break`, `continue`, a user function definition, `a, b = ...` multi-assign, chained `a = b = c`, and a missing `;`.
  - Expression precedence, low to high: ternary `?:` (right-associative), `||`, `&&`, `== !=`, `< > <= >=`, `+ -`, `* / %`, unary `- +`, then postfix call `f(args)` and member call `name.method(args)`.
  - The AST is small frozen dataclasses or tuples holding the source offset.
- **Resolver and build:**
  - `parse_codebox(code) -> Codebox`. Codebox has `n_in`, `n_out` (from io_counts), `params` (from parse_params, the single source for corners), `warnings: list[str]`, and the AST.
  - `Codebox.build(*, params=None, samplerate=44100.0, seed=1, buffers=None) -> Program`. It does the following:
    - classifies every name as constant, Param, History, local (any name assigned anywhere), inN, outN, `samplerate`, or built-in function;
    - binds Params as constants for this corner, so Param-only subexpressions fold. A `params` key that is not a declared Param raises ValueError;
    - folds constant subtrees bottom-up without reassociating, so results stay bit-identical;
    - allocates one flat Python list of float slots.
  - Name errors:
    - A name read but never assigned and not otherwise known is Unsupported("unknown identifier: X").
    - Assigning to a Param or an inN is Unsupported.
    - Assigning to a GEN_CONSTANTS name is ignored (the constant wins, as in MAX) and appends a warning.
  - `Param p;` with no args defaults to 0.0. A present but non-literal default is Unsupported.
- **Runtime semantics:** `Program.run(inputs, n_samples) -> list[np.ndarray]` returns out1..outN as float64 arrays.
  - Convert the inputs with `.tolist()` once.
  - Per sample: slice-assign the input row into the input slots, reset the output and local slots to 0.0 with one slice assignment, run the statement closures in order, and append the output slots.
  - History slots persist and are sequential: a read before the assignment sees the previous sample, and a read after it sees the new value.
  - `/` returns 0.0 when the divisor is 0 (safediv). `%` is `math.fmod`, with 0.0 for a zero divisor.
  - Comparisons, `&&` and `||` evaluate both sides and return 1.0/0.0. The ternary evaluates both arms (gen switch semantics).
  - `if` runs only the taken branch's statements. Document that stateful calls inside an untaken branch differ from gen's both-branches execution.
  - Use math.* on Python floats only; never `**` (it can return complex). Wrap `math.floor`/`ceil`/`trunc` in `float()`.
  - Domain errors: a ValueError becomes nan, except log/log10/log2 of 0, which give -inf. An OverflowError becomes ±inf. Never let a numeric Python exception escape `run`.
- **Pure built-ins in this task:**
  - `abs min max clamp clip exp exp2 log log10 log2 pow sqrt tanh sinh cosh sin cos tan asin acos atan atan2 floor ceil trunc fract sign mix wrap fold fixnan fixdenorm mstosamps sampstoms`;
  - `wrap`/`fold` take 1 arg (range 0..1) or 3 args. When hi == lo they return lo. `mix(a, b, t) = a + (b - a) * t`;
  - a wrong arity is Unsupported.
- **What Task 2 adds:** for loops, Delay/Data/Buffer and their methods, peek/poke/dim/channels, noise/phasor/latch/dcblock/cycle/triangle/selector/mc_channel, and GEN_OPERATOR_NAMES. In this task, build() raises Unsupported naming each of them. That is the correct never-pass behaviour.
- **Speed (D-01):** a closure per node. Specialise slot∘const, const∘slot and slot∘slot binary operators and Assign(slot, expr). Keep statements as a tuple. No numpy scalars in the hot loop.

**Part B: src/maxpat/dsp_sim/smoke.py, the smoke core (D-02, D-03, D-04, D-06).** This task builds the driven-window checks; Task 2 adds the two ring-out checks (dc latch, self_sustain per D-05).
- **Constants** (define the whole block here, including the ones Task 2 consumes):
  - stimulus: IMPULSE = 0.25, NOISE_AMP = 0.1, DRIVE_FRACTION = 0.5, SUSTAIN_SCALE = 0.01;
  - checks: PEAK_LIMIT = 4.0, SILENCE_FLOOR = 1e-9, ACTIVITY_FLOOR = 1e-6, DC_DRIVEN_LIMIT = 0.1, DC_TAIL_LIMIT = 0.05, SUSTAIN_ABS = 0.01, SUSTAIN_RATIO = 0.5, TAIL_FRACTION = 0.1;
  - run limits: MAX_SECONDS = 60.0, samplerate in [1000, 384000].
- **Dataclasses:**
  - `Finding(check, severity, corner, output, detail)`. check is one of nonfinite, peak, silence, silent, dc, self_sustain, constant_assign. severity is fail or warn. output is 1-based.
  - `CodeboxEntry(label, code, status, reason)`. status is ok, unsupported or skipped.
  - `CodeboxResult(label, verdict, reason, corners, findings)`. verdict is pass, fail, unsupported or skipped. corners is an int, the number of corners run.
- **Discovery:** `discover_codeboxes(path) -> list[CodeboxEntry]`. In this task it handles `.gendsp`:
  - Read the JSON. Collect the top-level `codebox` boxes (`code` key). The labels are `<file name> > codebox K`.
  - Any box that is not an `in N`/`out N` newobj, a codebox, a comment or a panel turns the whole gen patcher into one unsupported entry, with the reason "non-codebox gen operators: <first 5 box texts>" (D-04).
  - A gen patcher with no codebox is unsupported ("no codebox").
  - An unreadable file or a wrong suffix raises ValueError. smoke_main maps it to exit 2. Task 3 adds `.maxpat`.
- **Stimulus:**
  - `parse_input_spec(spec)` accepts:
    - `impulse+noise` (the default);
    - `zero`;
    - `const:V`, and `dc:V` as its alias;
    - `phasor:HZ`, a 0..1 ramp;
    - `sine:HZ`, amplitude 0.25.
  - Anything else raises ValueError (exit 2).
  - The default signal is IMPULSE at n = 0 plus a uniform ±NOISE_AMP drawn from `np.random.default_rng((seed, k))` over [0, N·DRIVE_FRACTION), then zeros. Inlet k gets its own stream.
  - An overridden inlet holds its signal for the whole run. Explicit `impulse+noise` counts as default.
- **Corners (D-02):** `default` first. Then, per Param in declaration order:
  - `NAME=min (V)` when min is declared and differs from the default, and `NAME=max (V)` likewise (V formatted with `:g`);
  - with `corners="default"`, only the default run.
- **Ring-out window:** applies only when n_in ≥ 1, every inlet is on the default stimulus, and ringout is True. Then the driven window is [0, N/2) and ring-out is [N/2, N). Otherwise the driven window is [0, N). Compute both windows here and keep the ring-out window on the run record; Task 2's checks consume it.
- **Checks** in this task run per output, on the nominal run:
  - **nonfinite:** any non-finite sample. FAIL, reporting the first index and its time. Skip the other checks for that output.
  - **peak:** max|y| > PEAK_LIMIT. FAIL.
  - **silence:** the last TAIL_FRACTION of the driven window has max|y| < SILENCE_FLOOR while the earlier part of the driven window exceeded ACTIVITY_FLOOR. FAIL, "permanent silence after excitation".
  - **silent:** max|y| never exceeds ACTIVITY_FLOOR. WARN.
  - **dc:** |mean| over the driven window > DC_DRIVEN_LIMIT. WARN only (D-06). Task 2 adds the ring-out tail half of this check.
- **Verdicts:** unsupported if parse, build or run raised Unsupported, or any other Exception (reason "interpreter error: <type>: <msg>"; never pass). Otherwise fail if any finding is a FAIL, else pass. Warnings are kept on the result, and codebox warnings become constant_assign WARN findings.
- **Public API:**
  - `smoke_codebox(code, *, label="codebox", seconds=1.0, samplerate=44100.0, inputs=None, buffers=None, corners="all", seed=1, ringout=True) -> CodeboxResult`;
  - `smoke_file(path, **same) -> list[CodeboxResult]`. Skipped and unsupported discovery entries pass through as results;
  - `inputs` is a `dict[int, str]` of specs keyed by 1-based inlet. Keys beyond a codebox's n_in are ignored.
- **`smoke_main(argv) -> int`:** argparse with prog `python -m src.maxpat.dsp_sim smoke`.
  - Arguments: positional `path`, `--seconds` (default 1.0, (0, 60]), `--samplerate` (default 44100), `--seed` (default 1), `--corners {all,default}`, `--no-ringout`, and `--input K=SPEC` (repeatable; the help lists every SPEC form and the phasor example).
  - Report:
    - a header line with path, seconds, rate, seed and corners;
    - one line per codebox, `<label>: PASS|FAIL|UNSUPPORTED|SKIPPED (<n> corners)` plus the reason;
    - indented `FAIL|WARN <check> [<corner>] out<k>: <detail>` lines;
    - a final `summary:` line with counts.
  - Exit codes: 0 when everything passed; 1 on any FAIL; 2 on a usage or read error; 3 when there is an unsupported entry and no FAIL, or nothing to smoke.

**Part C: src/maxpat/dsp_sim/cli.py dispatch.**
- At the top of `main`, set `argv = sys.argv[1:] if argv is None else list(argv)`. If `argv` is non-empty and `argv[0] == "smoke"`, lazily import smoke_main and return `smoke_main(argv[1:])`. Otherwise run the legacy body unchanged.
- Append to the build_parser description: "Subcommand: `smoke PATH` runs the GenExpr codebox smoke test; see `smoke --help`."
- Extend the module docstring:
  - usage gains a smoke line;
  - T-01 gains: "genexpr_interp/smoke compile codebox text into closures and never evaluate strings; an AST test pins it".
- Leave the legacy flags, exit codes and behaviour byte-for-byte as they were.

**Part D: tests/dsp_sim/test_smoke.py, the tracer tests.** Add a helper `_gendsp(tmp_path, name, code, extra_boxes=())`: it calls `generate_gendsp(code)`, appends any extra newobj boxes, writes `<name>.gendsp` and returns the path. Tests:
- `main(["smoke", "patterns/gen/gain/safe-gain.gendsp", "--seconds", "0.25"]) == 0`, and the output contains PASS.
- The report names the failing corner (D-02). Code `Param gain(1, min=0, max=100); out1 = in1 * gain;` at `--seconds 0.25` gives exit 1, a `peak` FAIL whose corner is `gain=max (100)`, and no peak finding at `default` or `gain=min (0)`. The 0.25 impulse × 100 peaks near 25.
- DC is a WARN, not a FAIL (D-06). Code `out1 = in1 + 0.5;` at `--seconds 0.25` gives exit 0, verdict pass, and a `WARN dc` line. This stays true after Task 2: the tail is a constant, so its detrended RMS is 0 and self_sustain cannot fire.
- `out1 = frobnicate(in1);` gives exit 3, and the output names `frobnicate`.
- `--seconds 0` and `--input 1=bogus:3` each exit 2.
- `main(["--help"])` still prints `--topology` (the legacy surface).

Commit only these four source/test paths with `git add <paths>`. Never use `git add .` or `git stash`. Message: `feat(dsp_sim): GenExpr interpreter core + codebox smoke tracer (quick 261021-urs)`.
  </action>
  <verify>
    <automated>python3 -m pytest tests/dsp_sim/test_smoke.py tests/dsp_sim/test_cli.py -q -p no:cacheprovider && python3 -m src.maxpat.dsp_sim smoke patterns/gen/gain/safe-gain.gendsp --seconds 0.25 && python3 -m src.maxpat.dsp_sim smoke --help | grep -q -- "--input" && python3 -m src.maxpat.dsp_sim --help | grep -q -- "--topology" && test -s .planning/quick/261021-urs-implement-q35-in-planning-reviews-2026-1/baseline-junit.xml && test -s .planning/quick/261021-urs-implement-q35-in-planning-reviews-2026-1/junit_diff.py && test "$(cat .planning/quick/261021-urs-implement-q35-in-planning-reviews-2026-1/baseline-rc.txt)" -le 1</automated>
  </verify>
  <done>
- `python3 -m src.maxpat.dsp_sim smoke patterns/gen/gain/safe-gain.gendsp` exits 0 with a PASS report.
- The gain codebox exits 1 with a peak FAIL named at `gain=max (100)` only (D-02).
- The `in1 + 0.5` codebox passes with a dc WARN (D-06).
- An unknown identifier exits 3 as unsupported.
- Bad arguments exit 2.
- The legacy CLI and tests/dsp_sim/test_cli.py are unchanged and green.
- The Step 0 baseline files exist in QDIR, and baseline-rc.txt holds 0 or 1. Four paths are committed.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Feedback state: Delay, Data/Buffer peek/poke, constant-bound for, stateful built-ins, the ring-out checks (self-sustain per D-05, dc latch) and genrun parity on the bassoon codebox</name>
  <files>src/maxpat/dsp_sim/genexpr_interp.py, tests/dsp_sim/test_genexpr_interp.py, src/maxpat/dsp_sim/smoke.py, tests/dsp_sim/test_smoke.py</files>
  <read_first>
    - src/maxpat/dsp_sim/genexpr_interp.py, src/maxpat/dsp_sim/smoke.py and tests/dsp_sim/test_smoke.py (as committed in Task 1)
    - patches/bassoon-model/tools/genrun.py (whole file, 71 lines; do NOT edit)
    - tests/dsp_sim/test_bassoon-model.py: lines 60-147 (paths, SHIPPED, _OFF, _NOT_CODEBOX_PARAMS, _shipped_codebox, genrun fixture), 156-210 (parity cases)
    - patterns/gen/dsp/multi-tap-delay.gendsp, patterns/gen/dsp/simple-reverb.gendsp, patterns/gen/buffer/buffer-player.gendsp, patterns/gen/buffer/buffer-recorder.gendsp, patterns/gen/dsp/noise-generator.gendsp, patterns/gen/timing/master-clock.gendsp (codebox text)
    - 261021-urs-RESEARCH.md: "Construct Inventory", "GenExpr Semantics to Implement" (peek/poke/Delay rows), "Architecture Patterns" (per-call-site state, noise stream), "Stimulus and Verdicts" (self-sustain), "Common Pitfalls" items 4-5
  </read_first>
  <behavior>
    - Precedence: `out1 = 1 + 2 * 3 - 4 / 2;` gives 5. `-2 * -3` gives 6. A nested ternary is right-associative. A comparison gives 1.0/0.0.
    - Division and modulo: `1 / 0` gives 0. `-7 % 3` gives -1.0 (fmod). `5 % 0` gives 0.
    - Compound assignment: `+= -= *= /=` apply to locals and History.
    - Constants: `pi`, `TWOPI`, `HALFPI` and `phi` read correctly. `e = 5; out1 = e;` gives 2.718281828…, with one warning.
    - History is sequential: with `History h(0); out1 = h; h = in1; out2 = h;`, out1 is in1 delayed one sample and out2 equals in1. Locals reset every sample: `x = x + 1; out1 = x;` gives 1 on every sample.
    - for: `acc = 0; for (i = 0; i < 32; i += 1) { acc += 1; } out1 = acc;` gives 32. A bound from a Param folds per corner. A bound that reads in1 is Unsupported("for loop bound is not constant"). A bound of 200000 is Unsupported (loop cap). A nested for is Unsupported.
    - Delay:
      - With `Delay d(10); out1 = d.read(3); d.write(in1);`, an impulse comes out at n = 3. read(0) clamps to 1 and read(100) clamps to 10.
      - read(2.5) gives a linear interpolation between taps 2 and 3. Write-then-read in the same sample still gives the previous samples.
      - Multiple taps on one Delay work.
    - Data/Buffer:
      - `peek(buf, i, ch)` floors the index. An index outside [0, frames) or a channel outside [0, channels) gives 0. A NaN or inf index gives 0.
      - `poke` outside the range writes nothing. `dim`/`channels` report the size.
      - A default Buffer has dim 48000 and channels 1, and holds 0.25·sin(2π·220·n/samplerate). `buffers={"name": (1000, 2)}` resizes it.
      - Data is zero-filled. A size above STATE_CAP is Unsupported.
    - Stateful built-ins (state per call site):
      - `noise()` with seed s matches `-1 + 2 * random.Random(s).random()` for each call in order, and the same seed gives identical output.
      - `phasor(441)` at 44100 Hz starts at 0 and has a period of 100 samples.
      - `latch(x, c)` holds when c == 0.
      - `dcblock` matches the refpage GenExpr (y = x - x1 + 0.9997·y1).
      - `cycle(f)` = sin(2π·phase) with an internal phase.
    - Unsupported:
      - with the name in the message: `sah(in1, in2, 0.5)` reports a known Gen operator that is not implemented; `while`; `else if`; a brace-less if; `x++`; `!x`;
      - the wrong arity: peek with 4 args, poke with 5 args, read with 2 args.
    - Math safety: `sqrt(-1)` gives nan, `log(0)` -inf, `pow(-2, 0.5)` nan and `exp(1000)` inf. Program.run raises nothing.
    - Parity: on the shipped bassoon codebox, interpreter out1 equals genrun.render out1 within 1e-12 over 0.1 s at seed 1, for (a) the codebox defaults (vibrato, noise and chiff on) and (b) parity case c-440Hz-extremes with _OFF. Both renders are non-silent (peak > 1e-3).
    - Self-sustain, History latch (tests/dsp_sim/test_smoke.py, `_gendsp` helper, `--seconds 0.25`). Code:
      - `Param drive(4, min=1, max=10);`
      - `Param feedback(0.6, min=0, max=0.95);`
      - `History y(0);`
      - `y = tanh((in1 - feedback * y) * drive) / tanh(drive);`
      - `out1 = y;`
      - Expected: exit 1, self_sustain findings at corners starting `default`, `drive=max` and `feedback=max`, and none at `drive=min` or `feedback=min`. The small-signal loop gain is -2.4, so it latches into a Nyquist limit cycle at about ±0.98.
    - Self-sustain, Delay fixture (test_smoke.py): the code below, at the default 1 s, gives verdict fail, with self_sustain findings whose corner starts with `default`, `drive=max` and `feedback=max`, and none at `drive=min` or `feedback=min`. `main(["smoke", path])` returns 1. The code:
      - `Param drive(4, min=1, max=10);`
      - `Param feedback(0.6, min=0, max=0.95);`
      - `Delay d(4410);`
      - `tap = d.read(441);`
      - `sat = tanh(tap * drive) / tanh(drive);`
      - `d.write(in1 + feedback * sat);`
      - `out1 = tap;`
    - Stable twin (test_smoke.py): the same code with `sat = tanh(tap * drive) / drive;` gives verdict pass and exit 0.
    - Ring-out limits (test_smoke.py): the Delay fixture with `--input 1=const:0.1`, or with `--no-ringout`, produces no self_sustain finding. This pins the documented limit: ring-out needs default stimulus.
    - DC latch (test_smoke.py): Task 1's `out1 = in1 + 0.5;` codebox now also reports a `dc` WARN whose detail says "dc latch", and still passes.
  </behavior>
  <action>
**RED.**
- Write tests/dsp_sim/test_genexpr_interp.py covering every interpreter `<behavior>` line, using short codeboxes through `parse_codebox(code).build(...).run(inputs, n)`.
- Add the self-sustain, stable-twin, ring-out-limit and dc-latch `<behavior>` tests to tests/dsp_sim/test_smoke.py, with fixtures built in tmp_path through the Task 1 `_gendsp` helper. Write no fixture files into the repo.
- Run both files and confirm the Task 2 constructs and the self_sustain/dc-latch assertions fail. Commit `test(dsp_sim): failing state-construct and self-sustain tests (quick 261021-urs)`.
- The parity test, `test_bassoon_parity_with_genrun`:
  - Copy the module-scoped isolated-import `genrun` fixture pattern from tests/dsp_sim/test_bassoon-model.py lines 123-147. Use importlib, put the tools dir on sys.path[0], and restore `core`/`genrun` in sys.modules afterwards. Do not import from the hyphenated test module.
  - Read the codebox from bassoon.gendsp the same way `_shipped_codebox` does.
  - Case a: `genrun.render(code, 220.0, lambda t: 0.6, dur=0.1, seed=1)` against `parse_codebox(code).build(seed=1).run([full(220.0), full(0.6)], N)[0]`.
  - Case b: use the c-440Hz-extremes overrides restricted to codebox Params, plus _OFF (a local copy of those dicts). Pass the same kwargs to both sides, with in1 = 440.0 and in2 = 0.45.

**GREEN.** Extend src/maxpat/dsp_sim/genexpr_interp.py.
- **for loops:**
  - The init is an assignment to a local, the cond is a comparison whose bound side folds to a constant at build time, and the step is an assignment or compound assignment.
  - Execute init, then loop while cond != 0: run the body, then the step.
  - Count iterations. Exceeding LOOP_CAP raises Unsupported("for loop exceeded 100000 iterations in one sample").
  - A non-constant bound raises Unsupported("for loop bound is not constant"). The counter is an ordinary local slot.
- **Delay** (`Delay d(N)`; N folds to a constant, ceil to int ≥ 1; any second arg other than 1 is Unsupported):
  - Use a ring list of N+2 floats and a head index.
  - `d.write(x)` stores at the head; the last write in a sample wins.
  - `d.read(t)` (exactly one argument) clamps t to [1, N]. Split t into an integer part i and a fraction f, and return `(1-f)·buf[head-i] + f·buf[head-i-1]`, with modular indices.
  - Every head advances once at the end of each sample, after the statements and before the output append.
  - Any other method, or keyword/@ arguments, are Unsupported.
- **Data** (`Data name(frames[, chans])`, zero-filled): one Python float list per channel.
- **Buffer** (`Buffer name("bufname")` or `Buffer name;`):
  - The buffer~ name is the string argument, else the declared name.
  - Back it with `buffers.get(bufname, (48000, 1))` frames × channels. Each channel holds 0.25·sin(2π·220·n/samplerate).
  - Document that MAX's buffer~ contents are not available offline.
- **State cap:** the sum of all Delay/Data/Buffer allocations above STATE_CAP is Unsupported.
- **peek/poke:**
  - `peek(buf, idx[, chan])` takes 2-3 args and `poke(buf, val, idx[, chan])` takes 3-4. buf must be a Data or Buffer name.
  - floor the index. Out of range on index or channel: peek gives 0.0 and poke writes nothing. A non-finite index counts as out of range.
  - `dim(buf)` and `channels(buf)` give the frame and channel counts.
- **Stateful built-ins:** create a state cell per call node at build time.
  - `noise()`: one `random.Random(seed)` per Program; each call returns `-1 + 2 * rng.random()` (the same stream as genrun's `random.uniform(-1, 1)`).
  - `phasor(freq[, reset])`: returns the current phase, then advances by freq/samplerate, wrapped into [0, 1). A non-zero reset sets the phase to 0.
  - `latch(x, ctrl)`: initial held value 0.
  - `dcblock(x)`: x1, y1 state with 0.9997.
  - `cycle(freq)`: one argument, sine at the internal phase, then advance.
  - `triangle(phase, duty)`: pure; ramps up to the duty point and back down, wrapping phase into [0, 1).
  - `selector(i, a, b, ...)`: floor i; values ≤ 0 give 0.0 and indices above the count clamp to the last [ASSUMED].
  - `mc_channel` and `mc_channelcount`: 1.0, as a bare name or as a zero-arg call.
- **GEN_OPERATOR_NAMES:**
  - A sorted frozenset literal of the 162 `<c74object name='...'>` values from the installed Gen refpages under `/Applications/Max.app/Contents/Resources/C74/packages/Gen/docs/refpages/common` and `.../dsp` (Max 9.2.0).
  - Generate it once at implementation time and paste it in, with a comment citing the source and version. Never read the bundle at runtime.
  - A call to a name in that set that the interpreter does not implement is Unsupported("Gen operator not implemented: NAME"). A call to any other unknown name is Unsupported("unknown function: NAME").
- Update the module docstring's semantics table: Delay, peek/poke bounds, Buffer backing, stateful built-ins, the if-branch caveat, and the [ASSUMED] rows from RESEARCH A4/A5.

**GREEN, ring-out checks in src/maxpat/dsp_sim/smoke.py (D-05, D-06).** Both run only on ring-out runs, using the ring-out window Task 1 stores on the run record.
- **dc latch:** |mean| of the ring-out tail > DC_TAIL_LIMIT is a `dc` WARN with detail "dc latch". WARN only (D-06).
- **self_sustain (D-05):**
  - Build a fresh Program and rerun the corner with every inlet's default stimulus × SUSTAIN_SCALE, using the same seeds.
  - The tail is the last TAIL_FRACTION of the ring-out window.
  - small = detrended RMS of the small run's tail (remove a linear fit with np.polyfit degree 1). nom = the same for the nominal run.
  - small > SUSTAIN_ABS and small / max(nom, 1e-12) > SUSTAIN_RATIO is a FAIL. The detail reads "sustains with zero input (small X at 0.01x vs Y at 1x): self-oscillation, latched feedback or a generator with an inlet; --no-ringout skips this check".
  - Run the nonfinite and peak checks on the small run too.
- Leave the Task 1 driven-window checks, verdict rules, report format and exit codes unchanged.

Then run `python3 -m pytest tests/dsp_sim/test_genexpr_interp.py tests/dsp_sim/test_smoke.py -q`.
- If parity is not bit-exact, find the first differing sample and fix the interpreter's evaluation order or folding. Never loosen the 1e-12 tolerance, and never edit genrun.py.
- The speed measurement and any speed tuning belong to Task 3; do not tune here.

Commit `feat(dsp_sim): Delay/Data/Buffer, for loops, stateful built-ins, self-sustain check, genrun parity (quick 261021-urs)` with only the four task paths.
  </action>
  <verify>
    <automated>python3 -m pytest tests/dsp_sim/test_genexpr_interp.py tests/dsp_sim/test_smoke.py tests/dsp_sim/test_bassoon-model.py tests/dsp_sim/test_cli.py -q -p no:cacheprovider && python3 -m src.maxpat.dsp_sim smoke patterns/gen/dsp/multi-tap-delay.gendsp --seconds 0.25 && python3 -m src.maxpat.dsp_sim smoke patterns/gen/dsp/noise-generator.gendsp --seconds 0.25 && python3 -m src.maxpat.dsp_sim smoke patterns/gen/buffer/buffer-player.gendsp --seconds 0.25 && git diff --quiet "$(cat .planning/quick/261021-urs-implement-q35-in-planning-reviews-2026-1/base-sha.txt)" -- patches/bassoon-model/tools/genrun.py tests/dsp_sim/test_bassoon-model.py</automated>
  </verify>
  <done>
- Every `<behavior>` line is a passing test.
- The bassoon codebox matches genrun within 1e-12 in both cases.
- The History latch and the tanh/tanh(g) Delay fixture FAIL self_sustain at default, drive=max and feedback=max; the `/ drive` twin passes.
- multi-tap-delay, noise-generator and buffer-player smoke with exit 0, with self_sustain active.
- genrun.py and test_bassoon-model.py are unchanged from base-sha.
- RED and GREEN commits exist with only the four task paths.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Speed pass, .maxpat discovery, --buffer/--json, Q35 acceptance tests (patterns pass, bassoon runs, guards), docs, final gate</name>
  <files>src/maxpat/dsp_sim/smoke.py, tests/dsp_sim/test_smoke.py, src/maxpat/dsp_sim/README.md, .claude/skills/max-dsp-agent/SKILL.md, src/maxpat/dsp_sim/genexpr_interp.py</files>
  <read_first>
    - src/maxpat/dsp_sim/smoke.py, tests/dsp_sim/test_smoke.py and src/maxpat/dsp_sim/genexpr_interp.py (as committed in Task 2; open genexpr_interp.py only if the speed rule fires)
    - 261021-urs-RESEARCH.md: "Architecture Patterns" (closure timing, speed techniques)
    - patches/bassoon-model/generated/bassoon-model.maxpat (find the `gen~ bassoon` newobj box with a JSON load; do not read the whole file)
    - src/maxpat/dsp_sim/README.md: lines 1-20 (Scope), 51-120 (When & How to Run, CLI, Scope & Future Work)
    - .claude/skills/max-dsp-agent/SKILL.md: lines 287-345 ("DSP Pre-Flight Simulation")
    - 261021-urs-RESEARCH.md: "Codebox Discovery", "Stimulus and Verdicts", "Common Pitfalls", "Validation Architecture"
  </read_first>
  <behavior>
    - Patterns: every one of the 19 `patterns/gen/**/*.gendsp` files gives verdict pass with `seconds=0.25`. swing-generator and subdivider get `inputs={1: "phasor:2"}`, because they are phasor-domain patterns: bipolar noise at `swing=min` maps -0.1 to -5. Assert the glob finds exactly 19 files.
    - The unstable tanh/tanh(g) fixture, its `/ drive` twin and the ring-out-limit tests are already in test_smoke.py from Task 2; keep them unchanged.
    - Options: `--corners default` runs exactly 1 corner.
    - Bassoon:
      - `smoke_file("patches/bassoon-model/generated/bassoon.gendsp", seconds=0.1, corners="default", inputs={1: "const:220", 2: "const:0.6"})` gives one result whose verdict is not unsupported, with no nonfinite finding and corners == 1.
      - The same options on bassoon-model.maxpat give exactly one result, from the sibling bassoon.gendsp (the label contains `bassoon.gendsp`), whose verdict is not unsupported.
    - Discovery:
      - A .gendsp holding the safe-gain code plus an extra `* 0.5` newobj gives unsupported, with "non-codebox" and `* 0.5` in the reason; the CLI exits 3.
      - A .maxpat built with `Patcher().add_gen(safe-gain code, 1, 1)` and written to tmp_path is discovered, and passes.
      - A .maxpat holding a `gen~ no-such-engine` newobj with no sibling file gives unsupported, "external gendsp not found".
      - A gen~ name containing `/` or `..` gives unsupported.
      - `discover_codeboxes` on patches/terrain-synth/generated/terrain-synth.maxpat gives 4 ok gen~ entries and 2 skipped jit.gen entries, without running anything.
      - A .maxpat with no gen~ exits 3.
    - --json and --buffer:
      - `--json` prints one JSON object with keys path, seconds, samplerate, seed, corners, exit_code and codeboxes. Each codebox has label, verdict, reason, corners and findings; each finding has check, severity, corner, output and detail.
      - `--buffer bufname=1000:2` resizes buffer-player's Buffer, so dim reads 1000. A malformed `--buffer` exits 2.
    - Guards:
      - An AST scan of src/maxpat/dsp_sim/genexpr_interp.py, smoke.py and cli.py finds no Call whose func is a bare Name in {eval, exec, compile, __import__}, and no import of importlib in genexpr_interp.py or smoke.py. cli.py keeps its existing importlib mirror loader.
      - An AST scan of every src/maxpat/**/*.py outside src/maxpat/dsp_sim finds no import of src.maxpat.dsp_sim.smoke or src.maxpat.dsp_sim.genexpr_interp (D-07: no save gate).
  </behavior>
  <action>
**Speed (D-01), first.**
- Measure µs per sample on the bassoon codebox (bassoon.gendsp, 1.0 s, default corner, `--input 1=const:220 --input 2=const:0.6`) and on compressor.gendsp (1.0 s, default corner). Record both numbers for the README limits and the SUMMARY.
- If the bassoon takes more than about 3 s per simulated second, apply the RESEARCH speed techniques (leaf specialisation, folding) in src/maxpat/dsp_sim/genexpr_interp.py while staying an AST closure evaluator (D-01). Then rerun tests/dsp_sim/test_genexpr_interp.py: the 1e-12 genrun parity must still hold. Never loosen that tolerance and never edit genrun.py. Record the before and after numbers.
- If the rule does not fire, leave genexpr_interp.py untouched.

**RED.** Add every `<behavior>` test to tests/dsp_sim/test_smoke.py.
- Build the fixtures in tmp_path with the Task 1 `_gendsp` helper, `Patcher().add_gen(...)` + `to_dict()`, or a minimal top-level patcher dict for the external-gen~ and no-gen~ cases. Write no fixture files into the repo.
- The patterns test is parametrized over `sorted(glob("patterns/gen/**/*.gendsp", recursive=True))`, with readable ids (the stem). A failure message lists every finding.
- Run the file and confirm the new discovery, JSON and buffer tests fail. Commit `test(dsp_sim): Q35 smoke acceptance tests (quick 261021-urs)`.

**GREEN, in src/maxpat/dsp_sim/smoke.py.**
- **.maxpat discovery** in `discover_codeboxes`. Walk `patcher.boxes` recursively, to depth ≤ 32.
  - A newobj box whose first text token is `gen~` or `mc.gen~` and that has an embedded `patcher` is a gen patcher. Apply the Task 1 gen-patcher rule to it: codeboxes, plumbing, non-codebox, then unsupported. Labels are `<file> > <box text> > codebox K`.
  - A gen~/mc.gen~ newobj without an embedded patcher is external. The name is the value after `@gen`, else the first token after the object name that does not start with `@`.
    - No name gives unsupported "gen~ without embedded patcher or file name".
    - A name containing `/`, `\` or `..` gives unsupported "external gendsp name is not a plain file name".
    - Otherwise resolve `<containing file's dir>/<name>` and append `.gendsp` when missing. Only that directory is searched.
    - Not found gives unsupported "external gendsp not found: <file> (only the patch's own directory is searched)".
    - Found: discover inside that file as a gen patcher, with labels prefixed `<maxpat> > <box text> > <name>.gendsp`.
  - A box whose first token is `jit.gen`, `jit.pix` or `jit.gl.pix` and that has an embedded patcher gives one skipped entry, "not gen~ (<token>)". Do not recurse into it.
  - Any other box with an embedded `patcher` (p, bpatcher, poly~ with an embedded patcher) is recursed into.
  - Only `newobj` boxes are classified; comment boxes are ignored.
- **`--buffer NAME=FRAMES[:CHANS]`** (repeatable): FRAMES ≥ 1, CHANS default 1, and the total ≤ STATE_CAP. Pass it as `buffers={name: (frames, chans)}`; malformed input exits 2.
- **`--json`:** the report object as specified in `<behavior>`, printed with `json.dumps(indent=2)`. The exit code is the same as the text mode.
- **Calibration rule:** if a pattern does not pass, first prove the interpreter semantics with a focused unit test. Likely culprits are Delay indexing, wrap/fold edges, History ordering and safediv.
  - If the interpreter is right and the pattern genuinely trips a check, do not edit the pattern, allowlist it, xfail it, or move PEAK_LIMIT or the nonfinite rule.
  - You may retune only the discretionary DC, silence and self-sustain thresholds, and only if the unstable fixture still FAILs and the History latch test still FAILs. Record the measured numbers in the README and SUMMARY.
  - Otherwise stop and report the pattern and its finding as a blocker.

**Docs.**
- src/maxpat/dsp_sim/README.md:
  - In Scope, add one sentence: the `smoke` subcommand (Q35) is the general-purpose exception, a GenExpr codebox smoke test for any gen~ codebox.
  - Add a section `### \`python -m src.maxpat.dsp_sim smoke\`: GenExpr codebox smoke test`, after the CLI section. It covers:
    - usage, and every flag with its default;
    - discovery rules: .gendsp, embedded gen~/mc.gen~, sibling external .gendsp, jit.gen skipped, non-codebox operators unsupported;
    - the stimulus timeline and the SPEC forms;
    - the corners (D-02);
    - the checks table: check, definition, threshold constant and value, severity;
    - the self-sustain rationale, citing the genexpr-rules.md "In-loop saturation" rule;
    - Buffer/Data backing;
    - the interpreter semantics and [ASSUMED] list;
    - exit codes 0/1/2/3;
    - limits: codebox-only, untaken-branch stateful calls, overrides disable ring-out, external files only in the same directory, speed (µs/sample from the speed step above; a full 45-corner bassoon run takes about N s);
    - "Advisory: not a save gate (Q35, D-07)".
- .claude/skills/max-dsp-agent/SKILL.md: under "## DSP Pre-Flight Simulation", add a subsection `### Codebox smoke test (advisory)`. In 3-5 lines of prose plus one bash command line, say:
  - after writing or editing a gen~ codebox, run `python3 -m src.maxpat.dsp_sim smoke <file>`;
  - report FAIL/UNSUPPORTED findings to the user;
  - never block a save on it;
  - details are in src/maxpat/dsp_sim/README.md.
  - No Python code block (test_doc_signatures scans skill code blocks).

**Final gate.**
- Run the pattern sweep at the 1 s default through smoke_file (the second `<automated>` command) and record the per-pattern verdicts and warnings in the SUMMARY.
- Delete QDIR/final-junit.xml first, so a stale file from an earlier attempt can never satisfy the diff.
- Run `python3 -m pytest -q -p no:cacheprovider --junitxml=QDIR/final-junit.xml` and keep its exit code.
  - 0 or 1 is allowed. Exit 1 means test failures, and the junit diff judges those against the baseline's pre-existing failures.
  - 2 (interrupted, which includes collection errors), 3 (internal error), 4 (usage error) or 5 (no tests collected) fails the gate on its own, whatever the diff says.
- Then `python3 QDIR/junit_diff.py QDIR/baseline-junit.xml QDIR/final-junit.xml` must exit 0.
- In the SUMMARY, record the baseline and final pytest exit codes, and note how junit_diff.py classifies a collection error. pytest writes it as a testcase with an empty classname and an `<error>` child, so its `::<module>` key is FOREIGN; the aborted run also reports every baseline test as REMOVED; and a missing or unparsable junit file makes the script exit non-zero.
- `git status --porcelain patches patterns` must be empty, and `git stash list` must equal QDIR/stash-list-before.txt.

Commit only the task paths you changed (genexpr_interp.py only when the speed rule fired). Message: `feat(dsp_sim): smoke .maxpat discovery, --json/--buffer, speed pass, Q35 acceptance + docs (quick 261021-urs)`.
  </action>
  <verify>
    <automated>python3 -m pytest tests/dsp_sim tests/test_doc_signatures.py tests/test_agent_skills.py -q -p no:cacheprovider && python3 -c "import glob; from src.maxpat.dsp_sim.smoke import smoke_file; ov={'swing-generator': {1: 'phasor:2'}, 'subdivider': {1: 'phasor:2'}}; fs=sorted(glob.glob('patterns/gen/**/*.gendsp', recursive=True)); assert len(fs) == 19, fs; bad=[(f, r.label, r.verdict, r.reason, r.findings) for f in fs for r in smoke_file(f, inputs=ov.get(f.rsplit('/', 1)[1][:-7], {})) if r.verdict != 'pass']; assert not bad, bad" && python3 -m src.maxpat.dsp_sim smoke patches/bassoon-model/generated/bassoon-model.maxpat --corners default --seconds 0.1 --input 1=const:220 --input 2=const:0.6 --json | python3 -c "import sys, json; r=json.load(sys.stdin); assert len(r['codeboxes']) == 1 and r['codeboxes'][0]['verdict'] != 'unsupported' and 'bassoon.gendsp' in r['codeboxes'][0]['label'], r" && rm -f .planning/quick/261021-urs-implement-q35-in-planning-reviews-2026-1/final-junit.xml && { python3 -m pytest -q -p no:cacheprovider --junitxml=.planning/quick/261021-urs-implement-q35-in-planning-reviews-2026-1/final-junit.xml >/dev/null; rc=$?; echo "full-suite pytest rc=$rc"; test "$rc" -le 1; } && python3 .planning/quick/261021-urs-implement-q35-in-planning-reviews-2026-1/junit_diff.py .planning/quick/261021-urs-implement-q35-in-planning-reviews-2026-1/baseline-junit.xml .planning/quick/261021-urs-implement-q35-in-planning-reviews-2026-1/final-junit.xml && test -z "$(git status --porcelain patches patterns)" && diff <(git stash list) .planning/quick/261021-urs-implement-q35-in-planning-reviews-2026-1/stash-list-before.txt</automated>
  </verify>
  <done>
- Every Q35 acceptance test passes:
  - all 19 patterns at 0.25 s in pytest, and again at the 1 s default in the gate;
  - the Task 2 tanh/tanh(g) fixture still FAILs self-sustain at default, drive=max and feedback=max, and the `/ drive` twin still passes;
  - the bassoon runs from both the .gendsp and the .maxpat.
- µs/sample for bassoon and compressor is recorded, and parity still holds if the speed rule fired.
- Non-codebox gen patchers, missing external files and unknown names are unsupported, and jit.gen is skipped.
- The AST guards hold.
- The README and the SKILL pointer document the command as advisory.
- The final full pytest run exits 0 or 1, its junit diff is clean, patches/ and patterns/ are untouched, and the stash list is unchanged.
- Only the changed task paths are committed.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| .maxpat/.gendsp JSON → smoke | Patch files and codebox text are untrusted input, parsed offline. |
| codebox text → interpreter | GenExpr source becomes executable behaviour inside the Python process. |
| smoke → repo | smoke is a reader; it must never write patches, patterns or genrun.py. |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-urs-01 | Elevation of privilege | genexpr_interp.py codebox evaluation | high | mitigate | Codebox text is tokenized, parsed and compiled into closures over a fixed operator and built-in table. No source text is generated and nothing is evaluated as a string. The Task 3 AST guard forbids bare eval/exec/compile/__import__ calls and importlib in the new modules. |
| T-urs-02 | Denial of service | interpreter loops, allocations, parse depth, run length | medium | mitigate | LOOP_CAP of 100000 iterations per sample, STATE_CAP of 50M samples, RecursionError becomes Unsupported, nested for loops are Unsupported, `--seconds` ≤ 60, samplerate in [1000, 384000], discovery depth ≤ 32. |
| T-urs-03 | Tampering | patches/, patterns/, genrun.py, test_bassoon-model.py | high | mitigate | smoke only reads, and fixtures live in tmp_path. Task 2 verifies `git diff --quiet base-sha` on genrun.py and test_bassoon-model.py; Task 3 verifies `git status --porcelain patches patterns` is empty. Commits name explicit paths and never use git stash. |
| T-urs-04 | Information disclosure | external gen~ name resolution | low | mitigate | Only `<containing dir>/<name>.gendsp` is opened. A name with `/`, `\` or `..` is unsupported, and this is tested. |
| T-urs-05 | Repudiation (false pass) | smoke verdicts | high | mitigate | Unsupported constructs, unknown names, non-codebox operators, missing files and interpreter exceptions all give `unsupported` (exit 3), never pass. Nothing to smoke exits 3. Self-sustain catches the bounded tanh/tanh(g) runaway, which peak and NaN checks miss. |
| T-urs-06 | Tampering (regression) | legacy dsp_sim CLI and suite | medium | mitigate | Early dispatch only on argv[0] == "smoke". test_cli.py stays unedited. The final full pytest run must exit 0 or 1 (a stale final-junit.xml is deleted first), and its junit diff against the Step 0 baseline must be clean. The no-import guard keeps smoke out of every save path (D-07). |
| T-urs-SC | Tampering | npm/pip/cargo installs | high | mitigate | No packages are installed. The work uses stdlib plus numpy, which is already in requirements-dev.txt. |
</threat_model>

<verification>
- `python3 -m pytest tests/dsp_sim -q -p no:cacheprovider` passes, including test_genexpr_interp.py, test_smoke.py, the unedited test_cli.py and test_bassoon-model.py.
- `python3 -m src.maxpat.dsp_sim smoke patterns/gen/gain/safe-gain.gendsp` exits 0. The tanh/tanh(g) fixture exits 1 naming self_sustain at default.
- All 19 patterns pass at the 1 s default, with the phasor override on swing-generator and subdivider only.
- The bassoon codebox runs from bassoon-model.maxpat through the sibling .gendsp, and matches genrun within 1e-12.
- The final full pytest run exits 0 or 1, and QDIR/junit_diff.py baseline vs final exits 0. patches/ and patterns/ are clean. The stash list is unchanged.
</verification>

<success_criteria>
- Q35 is delivered:
  - genexpr_interp.py covers Param, History, Delay read/write, Data/Buffer peek/poke with channel, if/else, constant-bound for, built-in math and constants, and in1..inN/out1..outN;
  - `python -m src.maxpat.dsp_sim smoke` reports NaN/inf, peak > 4, DC (warn), permanent silence and self-sustain at the default and min/max corners, with an unsupported verdict that never passes;
  - the patterns pass, the unstable `tanh(x*g)/tanh(g)` feedback codebox fails, and the bassoon codebox runs;
  - saves are not gated.
- D-01 to D-07 are each implemented and pinned by tests. The discretionary thresholds and backing are documented in the README.
</success_criteria>

<output>
Create `.planning/quick/261021-urs-implement-q35-in-planning-reviews-2026-1/261021-urs-SUMMARY.md` when done. Include:
- µs/sample (bassoon and compressor);
- the 1 s per-pattern verdict and warning table;
- any threshold retune, with its measured numbers;
- the junit diff result, the baseline and final pytest exit codes, and how junit_diff.py classifies a collection error.
</output>

<source_audit>
| SOURCE | ID | Item | Task | Status |
|--------|----|------|------|--------|
| GOAL | Q35 | GenExpr interpreter + codebox smoke test | 1-3 | COVERED |
| REQ | Q35 | interpreter subset (Param/History/Delay/Data/Buffer peek-poke/if-else/const for/math+constants/in-out) | 1, 2 | COVERED |
| REQ | Q35 | `python -m src.maxpat.dsp_sim smoke <maxpat/gendsp>`, 1 s @ 44.1 kHz, impulse+noise, default/min/max corners | 1, 3 | COVERED |
| REQ | Q35 | reports NaN/inf, peak > 4, DC, permanent silence; unsupported never passes | 1, 2, 3 | COVERED |
| REQ | Q35 | tests: patterns pass, tanh/tanh(g) fails, bassoon runs | 2, 3 | COVERED |
| REQ | Q35 | don't gate saves | 3 (no-import guard, docs) | COVERED |
| CONTEXT | D-01 | AST closures, no exec/eval/numba, lean, --seconds | 1, 2, 3 | COVERED |
| CONTEXT | D-02 | default + one-at-a-time corners, report names the corner | 1 | COVERED |
| CONTEXT | D-03 | impulse+noise default, documented --input, seeded, bassoon overrides | 1, 3 | COVERED |
| CONTEXT | D-04 | codebox-only; non-codebox and unsupported constructs give unsupported | 1, 2, 3 | COVERED |
| CONTEXT | D-05 | self-sustain 0.01× rerun; real tanh/tanh(g) fixture | 2 | COVERED |
| CONTEXT | D-06 | DC warn-only, 0.25/±0.1 then zeros, phasor overrides, no allowlist | 1, 2, 3 | COVERED |
| CONTEXT | D-07 | genrun kept + parity; no save gate | 2, 3 | COVERED |
| RESEARCH | - | uppercase PI/TWOPI/HALFPI + phi; Gen operator name list; safediv/fmod/wrap lo==hi; peek/poke bounds; Delay clamp [1,N] linear; Buffer backing; caps; jit.gen skip; sibling .gendsp; AST no-eval test; detrended RMS | 1, 2, 3 | COVERED |
| RESEARCH | - | external .gendsp beyond the sibling directory | - | OUT OF SCOPE (research Open Q2; reported as unsupported) |
</source_audit>
