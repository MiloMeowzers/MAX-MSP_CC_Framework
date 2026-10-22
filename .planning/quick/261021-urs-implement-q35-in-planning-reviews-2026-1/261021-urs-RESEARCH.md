# Quick 261021-urs: Q35 GenExpr interpreter + codebox smoke test - Research

**Researched:** 2026-10-21
**Domain:** Python tree-walking GenExpr interpreter, numpy stability metrics, `dsp_sim` CLI
**Confidence:** HIGH for integration points and construct inventory (read and scanned in the repo); MEDIUM for thresholds (prototyped in a scratch numpy sim this session); MEDIUM-LOW for the exact gen~ runtime semantics (marked)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Tree-walking interpreter** (user choice): parse codebox GenExpr into an AST and evaluate it node by node per sample. Do NOT transpile to Python source and `exec` it (genrun.py's approach is being replaced, not generalized in form). No numba.
- Consequence to manage: speed. Keep the per-sample evaluator lean (e.g. pre-resolve variable slots, precompute node dispatch once at parse time) — but it must stay an AST evaluator. Provide a `--seconds` override (default 1.0) so tests can run shorter where needed; the CLI default stays 1 s at 44.1 kHz.
- **Default + one-at-a-time:** one run with all Params at default, then each Param at its min and at its max with the others at default (1 + 2N runs). Params without a declared min/max only contribute the default run on that side. The report names which Param/corner failed.
- **Impulse + noise on every inN by default**, with a CLI override per inlet, e.g. `--input 1=const:220`, `--input 2=dc:1` (exact syntax at planner's discretion, must be documented in `--help`). The bassoon test uses overrides (in1 is raw-Hz frequency).
- Noise must be seeded (deterministic runs).
- Smoke covers codeboxes only. A gen~ / .gendsp whose patcher contains non-codebox gen operators (beyond in/out/codebox plumbing) gets an **"unsupported"** verdict — never a pass. Same for any GenExpr construct the interpreter does not support.

### Claude's Discretion
- Exact thresholds for DC offset and the "permanent silence after excitation" window (document them).
- Exit codes (suggest: 0 all pass, nonzero on any fail; unsupported treated as not-pass).
- How `Buffer` (external buffer~ refs) is backed in the sim (e.g. zero-filled or sized default) — document.
- Report format (text table; optional `--json`).
- Whether `patches/bassoon-model/tools/genrun.py` is left in place (it is used by the bassoon project's sim tooling — do not break it).

### Deferred Ideas (OUT OF SCOPE)
- Save gating ("Don't gate saves on it yet").
</user_constraints>

## Summary

The Q22 parser gives everything except expressions. `mask()` blanks comments, `parse_params()` gives the corners, and `statements()` gives statement spans. There is no expression AST, no block tree and no for-header parse. The interpreter needs its own tokenizer plus a recursive-descent parser. It should run them over `mask(code)` rather than rebuild blocks from `Stmt` records. Compile the AST once into a tree of Python closures that read and write a flat slot list. That is still an AST evaluator: no source text is generated and nothing calls `eval`/`exec`/`compile`. It ran at about 38 ns per node in a Python 3.14.2 micro-benchmark. At that rate the bassoon codebox (about 1,400 nodes) takes roughly 2-3 s per simulated second.

**The main planning risk is that the four listed checks cannot make the required unstable fixture fail.** A `tanh(x*g)/tanh(g)` loop is bounded by tanh. In the prototype it latched into a steady limit cycle with peak 0.85, not a peak above 4. It produced no NaN, no DC (the AC tail was 0.59) and no silence. The fixture fails only with a **self-sustain** check: after the inputs go to zero, rerun at 0.01× the stimulus. A stable system's tail scales down by about 0.01. A latched loop's tail does not scale (measured ratio 1.000 against 0.010 for the linear patterns). Two default-stimulus details also matter. With a 1.0 impulse, `compressor.gendsp` at `makeup=24` peaks at 5.0, so use a 0.25 impulse plus ±0.1 noise. Bipolar noise makes `swing-generator.gendsp` at `swing=0` output -5, so the timing patterns need a phasor input override.

**Primary recommendation:** Build `genexpr_interp.py` as lexer → Pratt/recursive-descent parser → resolver (slots) → closure compiler. Build `smoke.py` with the stimulus timeline below. FAIL on NaN/inf, peak > 4, permanent silence and self-sustain; only WARN on DC. Dispatch `smoke` in `cli.main()` before the legacy parser so existing behaviour is unchanged. Keep `genrun.py` and add an interpreter-vs-genrun parity test on the bassoon codebox.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary | Rationale |
|---|---|---|---|
| Tokenize/parse/compile GenExpr | `src/maxpat/dsp_sim/genexpr_interp.py` (new) | `genexpr_parse.mask/parse_params` | Q22 owns comment masking and Param parsing; the expression grammar is new |
| Codebox discovery, stimulus, corners, verdicts, report | `src/maxpat/dsp_sim/smoke.py` (new) | `measure.py` (`measure_peak`, `measure_ac_rms`) | Keeps cli.py thin |
| `smoke` subcommand | `cli.py:main()` early dispatch | `__main__.py` unchanged | Legacy CLI has no subparsers and requires `--patch` |
| Bassoon project sim | `patches/bassoon-model/tools/genrun.py` (KEEP) | — | Imported by `tests/dsp_sim/test_bassoon-model.py` |

## Integration Points (verified this session)

- **`genexpr_parse.py`** `[VERIFIED: src/maxpat/genexpr_parse.py:33-38]`: `DECL_TYPES = ("Param", "History", "Delay", "Buffer", "Data")`; `CONSTANTS = frozenset({"e", "pi", "twopi", "halfpi", "invpi", "ln2", "ln10", "log10e", "log2e", "sqrt2", "sqrt1_2", "degtorad", "radtodeg"})`. `parse_params(code)` returns "One dict per Param name with exactly the keys name, default, min, max" (min/max are None when absent or non-literal) `[VERIFIED: :360-367]`. Use it as the single source for corners. `mask()` preserves offsets, so a token offset maps to a line through `code.count("\n", 0, off)+1`. Not provided: an expression AST, a block/else tree, for-header parts (`_for_parts` is private), or Delay/Data/History argument values (`declarations()` returns names only).
  - Q22 `CONSTANTS` lacks the uppercase forms used in shipped, MAX-confirmed codeboxes: `TWOPI` (41 uses), `PI` (7) and `HALFPI` (3), for example in bassoon.gendsp. It also lacks `phi`, which the installed Gen refpage list includes `[VERIFIED: /Applications/Max.app/.../packages/Gen/docs/refpages/common/ listing]`. The interpreter must accept all of these.
- **`cli.py`** has no subcommands: `main(argv)` builds one argparse parser with `--patch` and the mutually exclusive `--topology`/`--mirror` both required. Exit codes `[VERIFIED: src/maxpat/dsp_sim/cli.py:56-62]`: `PASS: 0, PHASE_DRIFT: 1, MODE_COMPETITION: 2, NO_OSCILLATION: 3, RUNAWAY: 4`. `tests/dsp_sim/test_cli.py` calls `main([...])` with legacy flags. **Add `if argv and argv[0] == "smoke": return smoke_main(argv[1:])`** (with `argv = sys.argv[1:]` when None) before `build_parser()`, and mention `smoke` in the legacy description. The cli docstring threat model (T-01) promises no eval/exec; the new modules must keep that promise, and a grep test should cover them.
- **`genrun.py`** is bassoon-specific: it returns `out1, cone_hp` and builds the tick with `exec('\n'.join(fn),env)` `[VERIFIED: patches/bassoon-model/tools/genrun.py:44-62]`. Its semantics: History is sequential (the read is the previous sample's value until assigned, and later statements see the new value); `peek=lambda d,i,c:d[int(i)]`; `noise=lambda:random.uniform(-1,1)` after the global `random.seed(seed)`; `clamp=min(max())`; ternary via regex. Importers: `tests/dsp_sim/test_bassoon-model.py` (the `genrun` fixture plus the parity test vs `ReedBorePostRadiation`), `topologies/reed_bore_post_radiation.py` (docstring), and `patches/bassoon-model/context.md`. **Leave it in place.**
- **`measure.py`**: `measure_peak` returns NaN on any non-finite sample; `measure_ac_rms` removes the mean. Reuse both. Add a `measure_detrended_rms` (linear fit removed) for the self-sustain check.
- **Test naming:** `tests/dsp_sim/test_<patch_stem>.py` acts as a patch gate (D-07). Name the new files `test_genexpr_interp.py` / `test_smoke.py`, which no patch stem uses.

## Codebox Discovery

Scanned 88 codeboxes in 59 files (patches/ plus patterns/) this session:
- Codeboxes are boxes with `maxclass == "codebox"` whose text is in the `"code"` key. They sit inside a box's `"patcher"`, or at the top level of a `.gendsp`.
- `classnamespace` is inconsistent (`"dsp.gen"` 33×, `"box"` 21×), so **detect gen context from the container box text** (`gen~…` / `mc.gen~…`) or from a `.gendsp` top level.
- Skip `jit.gen` codeboxes (2 in terrain-synth.maxpat; they use `sample()`/`concat`/`norm`): report them as "skipped: not gen~". Recurse through `p`/bpatcher patchers.
- `gen~ bassoon` (bassoon-model.maxpat) has **no embedded patcher**. Resolve the sibling `bassoon.gendsp`; if it is not found, report "unsupported: external gendsp not found".
- Non-codebox operator detection: any box in a gen patcher other than `in N`/`out N` newobj, `codebox`, `comment` or `panel` makes the verdict "unsupported" for that gen patcher. The repo has **0** such gen patchers, so the test needs a synthetic fixture (e.g. a `.gendsp` with an `in 1 → * 0.5 → out 1` box).
- I/O counts come from `genexpr_parse.io_counts(code)`. Smoke each codebox standalone and ignore patcher wiring.

## Construct Inventory → Interpreter Scope

**Required for the three tests** (the patterns/gen 19 files plus bassoon.gendsp):
- Declarations:
  - `Param n(d, min=…, max=…)`;
  - `History n(v)`;
  - `Delay n(N)` with `.read(t)` (single argument) and `.write(x)`;
  - `Data n(N)`;
  - `Buffer n("name")`.
- Statements: `if/else` with braces (nested `else { if … }`), and continuation lines.
- Operators: `= + - * / < > <= >= && ?:` and unary `-`.
- Literals: `1.`, `.5` and `1e-1` forms.
- Built-ins: `abs min max clamp wrap exp log10 pow tanh sin cos atan sqrt floor noise phasor dim peek(buf,i,ch) poke(buf,v,i,ch)`, `samplerate`, `TWOPI HALFPI`.

**Cheap to add (used elsewhere in the repo):** `+= -= *= /=` (43), `for` with constant bounds (32 sites; max bound 600), `%` (2), `||` (2), `== !=`, `mix tan log log2 sign fixnan fixdenorm latch dcblock channels cycle triangle selector mstosamps`, `mc_channel` (simulate as 1), and the lowercase constants plus `pi twopi halfpi sqrt2 PI`.

**Not present anywhere, so mark them unsupported:**
- syntax: brace-less `if`/`else`, `else if` (forbidden by CLAUDE.md), `while`, `return`, user functions, `!`, bitwise ops, `a, b = …` multi-assign;
- calls: `peek` with >3 args, `poke` with >4, `.read` with >1 arg or `@`/kwarg attributes;
- unimplemented names: any other Gen operator name from the installed refpage list (e.g. `sah`, `accum`, `delta`, `elapsed`, `interp`, `wave`, `fft*`).

An unknown identifier also gives "unsupported", never a pass.

## Architecture Patterns

**Pipeline:** `mask(code)` → tokens (with offsets) → recursive-descent statements plus a Pratt expression parser (C precedence: `?:` < `||` < `&&` < `== !=` < `< > <= >=` < `+ -` < `* / %` < unary) → resolver (classify each name as constant / Param / History / local / inN / outN / Delay / Data / Buffer / builtin, and assign slot indices) → closure compiler → `Program.run(inputs, params, n_samples) -> list[np.ndarray]`.

**Closure compilation is the "precomputed dispatch" the decision asks for.** Each AST node compiles once into a Python callable that captures its children and slot indices, e.g. `lambda env: a(env) * b(env)`. Measured on Python 3.14.2: 38 ns/node for closures vs 63 ns/node for an `isinstance`-dispatch walker vs ~30 ns/line for genrun's exec'd code (bassoon: 6 µs/sample). No source string is ever built.

Speed techniques that keep it an AST evaluator:
1. Specialize leaf shapes: `Bin(op, Slot, Const)`, `Bin(op, Slot, Slot)`, `Assign(slot, Bin(...))`. These remove 2-3 calls per node.
2. Fold constants at compile time, including `samplerate` and constant names. **Compile once per corner with Params bound as constants**, so Param-only subexpressions fold the way gen hoists them. Compile cost is negligible; a large win for the patterns.
3. Use a flat Python `list` for slots. Back Data/Buffer with Python lists of floats, one list per channel. Avoid numpy scalars in the hot loop (an `np.float64` op is several times slower).
4. Keep statements as a tuple. Use one `for n in range(N)` loop that writes inputs into slots, runs the statements and appends the outputs; convert to numpy at the end.

Estimated run times:
- patterns/gen at 1 s: under 1 s per corner;
- bassoon: about 2-3 s per corner, so ~100 s for all 41 corners. Tests use `--seconds 0.1` plus a `--corners default` option;
- cap any `for` loop at e.g. 100k iterations per sample, else "unsupported: loop bound".

**Per-call-site state** for stateful built-ins (`phasor`, `latch`, `dcblock`, `cycle`): create a state cell per call node at compile time. `noise()`: per-program `random.Random(seed)`, `-1 + 2*rng.random()`. That is the same stream as genrun's `random.uniform(-1,1)` after `random.seed(seed)`, which enables bit-exact parity.

## GenExpr Semantics to Implement

| Construct | Behavior | Source |
|---|---|---|
| History | Slot that persists across samples, initialized from the decl. A read before assignment gets the previous sample's value; reads after assignment get the new value (sequential) | genrun + MAX-confirmed bassoon numbers `[CITED: patches/bassoon-model/context.md:420]`; exact gen equivalence `[ASSUMED]` |
| `peek(buf,i,ch)` | No interpolation; `boundmode` default **ignore** (out of range → 0); channelmode ignore; index in samples | `[VERIFIED: Gen refpage gen_dsp_peek.maxref.xml:92-100,131-139,181-189,216-224 — default values 'ignore','ignore','samples','none']` Fractional index → `floor` `[ASSUMED]` |
| `poke(buf,v,i,ch)` | Out-of-range index → no write; channel out of range → no write | `[CITED: gen_dsp_poke.maxref.xml description "If the index is out of range, no value is written"]` |
| `Delay d(N)` | Default interp **linear**; with `@feedback` on (default 1) the minimum delay is 1 sample. Clamp t to [1, N]; allocate ≥ N+2 (simple-reverb reads exactly `comb1.read(1687)` on `Delay comb1(1687)`). Write at the head, advance the head at end of sample | `[CITED: gen_dsp_delay.maxref.xml: interp default 'linear', feedback default 1]`; ring-buffer details `[ASSUMED]` |
| `/` | Return 0 when the denominator is 0 (genlib `safediv`) | `[ASSUMED]` — prevents false NaN fails |
| `%` | `math.fmod` (C sign semantics), 0 on a zero divisor | `[ASSUMED]` |
| `wrap/fold(x,lo,hi)` | When `hi == lo` return `lo` (buffer-player at the `start=1` / `end=0` corners hits range 0) | `[ASSUMED]` |
| `noise()` | Uniform in [-1, 1) | `[ASSUMED]` (refpage says only "A random number generator") |
| comparisons, `&&`, `\|\|` | Return 1.0/0.0, both sides evaluated | `[ASSUMED]` |
| `if/else` | Execute the taken branch only for assignments. Ternary: evaluate both arms (gen `switch`). Stateful calls inside untaken branches diverge from gen; document it | CLAUDE.md "both branches always execute" |
| constants | Assigning to a constant name is a no-op, so the constant wins; report it as a warning | CLAUDE.md / genexpr-rules.md:100 |
| floats | Everything is float64. `math.floor` returns int, so wrap it in `float()`. `math.sqrt/log/pow` raise on domain errors: catch `ValueError` → `nan` and `OverflowError` → `inf` (never let Python raise); `pow(neg, frac)` → `nan`, and never use `**` (it returns complex) | Python semantics |

## Stimulus and Verdicts (prototyped)

**Default stimulus per inlet:**
- impulse **0.25** at n=0;
- seeded uniform noise **±0.1** over [0, 50% of run);
- **zeros** over [50%, 100%) (the ring-out half);
- an independent seed per inlet.

**Overrides:** `--input K=const:V | dc:V | phasor:HZ | sine:HZ | impulse+noise | zero`. Any override turns the ring-out checks off for that run.

**Buffer backing:** 48000 frames × 1 channel of a 220 Hz sine at 0.25, deterministic and deliberately not equal to the 44100-sample run. Override with `--buffer name=frames[:chans]`. `Data` is zero-filled.

| Check | Definition (default) | Verdict |
|---|---|---|
| NaN/inf | any non-finite sample; report the first index | FAIL |
| Peak | `max|y| > 4.0` | FAIL |
| Permanent silence | output had `|y| > 1e-6` earlier, then `max|y| < 1e-9` over the last 10% of the driven window (inputs still active). Generators (0 inlets): the same test on the last 10% of the run. A codebox silent throughout is reported as WARN `silent` | FAIL |
| Self-sustain (needed for the fixture) | only for codeboxes with ≥1 inlet and all inlets at the default stimulus. Detrended RMS of the last 10% of ring-out > 0.01 in a rerun at 0.01× stimulus, **and** small/nominal tail ratio > 0.5 | FAIL |
| DC | `|mean|` over the driven window > 0.1, or `|mean|` of the last 10% of ring-out > 0.05 ("DC latch") | WARN only — phasor, random-walk, S&H, envelopes and exp-curve are unipolar by design |

Prototype numbers from a scratch hand-port (not the real interpreter):

| Case | Result |
|---|---|
| compressor `makeup=24` | peak 2.80 at 0.25/±0.1; 3.96 at 0.25/±0.25; 5.02 at 1.0/±0.5 |
| multi-tap `feedback=.95` | small/nominal 0.0100 |
| reverb `decay=.99` | small/nominal 0.0100 |
| fixture `tanh(tap*drive)/tanh(drive)` (10 ms Delay, `drive=4`, `feedback=.6`) | tail AC 0.59, small/nominal **0.9999** → FAIL |
| same at `drive=1` | 0.0116 |
| `/drive` twin | 0.015-0.13 → PASS |

The real stereo-feedback-delay v0.1.0 codebox (500 ms delay, git `9b1db66d`) does **not** discriminate within 1 s, because its tail holds only the first echo. Use the short-delay fixture.

## Common Pitfalls

1. **The swing-generator min corner fails on bipolar input**: `ph/sw*0.5` with `sw=0.01` turns -0.1 into -5. Give `timing/swing-generator` and `timing/subdivider` `--input 1=phasor:2` in the test parametrization, and document why (they are phasor-domain patterns).
2. **noise-generator `type=2`** (brown ×3.5) peaked at 2.2-3.6 across seeds 1-7. The seed is fixed, but the margin is thin; pin the codebox RNG seed in tests.
3. **`wrap(x, 0, 0)`** in buffer-player corners divides by zero unless guarded.
4. **Overrides keep inlets non-zero.** Never run ring-out/self-sustain on overridden runs (bassoon with `const` freq/breath sustains by design).
5. **Generators with inputs** (an LFO whose inlet is a reset) will trip self-sustain. Name the finding "sustains with zero input (self-oscillation or a generator)" and offer `--no-ringout`.
6. **The bassoon `reed_aper=-1` corner** may legitimately go silent. The bassoon test asserts "runs" (no exception, not `unsupported`, no NaN), not "pass".
7. **Do not edit genrun.py.** The parity test against the topology depends on it.
8. **Python `%` vs C fmod, `**` complex results, `math.floor` returning int**: all three silently change numbers.

## Don't Hand-Roll

| Problem | Use instead |
|---|---|
| Comment/string masking, Param min/max parsing | `genexpr_parse.mask`, `parse_params` (Q22 contract: never raises) |
| Peak/AC-RMS/NaN handling | `measure.measure_peak`, `measure.measure_ac_rms` |
| Gen operator name list for "known but unsupported" | Embed the list read from the installed refpages (`packages/Gen/docs/refpages/{common,dsp}`) as a frozenset constant. Do not read the Max bundle at runtime |

## Code Examples

```python
# cli.py — early dispatch keeps the legacy surface byte-identical
def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "smoke":
        from src.maxpat.dsp_sim.smoke import smoke_main
        return smoke_main(argv[1:])
    parser = build_parser()
    ...
```

```python
# closure compile (sketch) — no source text, no eval/exec
def compile_bin(op, a, b):
    if a.kind == "slot" and b.kind == "const":
        i, c = a.slot, b.value
        if op == "*": return lambda env: env[i] * c
    fa, fb = compile_expr(a), compile_expr(b)
    if op == "/": return lambda env: _safediv(fa(env), fb(env))
    ...
```

Fixtures (`tests/dsp_sim/fixtures/`, as `.gendsp` or written to `tmp_path`):
```
// unstable: must FAIL (self-sustain)            // stable twin: must PASS
Param drive(4, min=1, max=10);                   (identical, but)
Param feedback(0.6, min=0, max=0.95);            sat = tanh(tap * drive) / drive;
Delay d(4410);
tap = d.read(441);
sat = tanh(tap * drive) / tanh(drive);
d.write(in1 + feedback * sat);
out1 = tap;
```

## Assumptions Log

| # | Claim | Risk if wrong |
|---|---|---|
| A1 | A **self-sustain** check may be added beyond the four listed checks (otherwise the required fixture cannot fail without a contrived peak>4 design) | Needs user OK. The alternative is a contrived fixture that proves nothing about the real bug class |
| A2 | DC is WARN-only | If DC must fail, 8+ pattern files (phasor, random-walk, S&H, envelopes, exp-curve, subdivider, buffer-recorder) fail |
| A3 | Default stimulus 0.25 impulse / ±0.1 noise, ring-out second half | At a 1.0 impulse the compressor `makeup=24` corner fails peak>4 |
| A4 | gen `/` is safediv, `%` is fmod, `noise()` is in [-1,1), `wrap(lo==hi)` → lo, peek fractional index → floor, Delay clamp [1,N] | Small numeric divergence from MAX; false NaN fails if `/` is not safe |
| A5 | Sequential History semantics equal gen~ | Same assumption genrun already makes; MAX-confirmed indirectly via bassoon |
| A6 | Timing patterns may be tested with a phasor input override | Otherwise swing-generator fails at `swing=0` |

## Open Questions

1. **Self-sustain check (A1).** Recommendation: adopt it and confirm with the user at plan time. It is the only detector that catches the real `tanh/tanh(g)` failure (MAX symptom: repeats never die).
2. **External `.gendsp` resolution beyond the sibling directory** (Max search path): out of scope; report it as unsupported.

## Environment Availability

| Dependency | Available | Version |
|---|---|---|
| Python | ✓ | 3.14.2 |
| numpy / scipy | ✓ | 2.4.0 / 1.17.0 |
| pytest | ✓ | 9.0.2 |
| Max 9 Gen refpages (reference only) | ✓ | /Applications/Max.app/Contents/Resources/C74/packages/Gen/docs/refpages |

No new packages (the Package Legitimacy Audit does not apply).

## Validation Architecture

| Property | Value |
|---|---|
| Framework | pytest 9.0.2 (no pytest.ini; run from the repo root) |
| Quick run | `python3 -m pytest tests/dsp_sim/test_genexpr_interp.py tests/dsp_sim/test_smoke.py -q` |
| Full suite | `python3 -m pytest -q` |

| Behavior | Test |
|---|---|
| Operators, precedence, ternary, `+=`, for, constants (incl. uppercase), safediv, fmod, wrap zero-range, peek/poke bounds, Delay read N, History sequential, unknown name → Unsupported | `test_genexpr_interp.py` (unit, short programs) |
| Interpreter == genrun on the bassoon codebox (0.1 s, same seed) within 1e-12 | `test_genexpr_interp.py::test_bassoon_parity_with_genrun` (reuse the `genrun` fixture pattern from test_bassoon-model.py) |
| Every `patterns/gen/**/*.gendsp` passes (`--seconds 0.25`; phasor override for swing/subdivider) | `test_smoke.py` parametrized |
| Unstable fixture FAILs naming the corner; stable twin passes | `test_smoke.py` |
| Bassoon codebox runs (overrides `1=const:220 2=const:0.6`, `--corners default`, short seconds) | `test_smoke.py` |
| Non-codebox gen graph → unsupported; jit.gen skipped; exit codes; legacy CLI unchanged; no `eval(`/`exec(`/`compile(` in new modules | `test_smoke.py` |

Wave 0: create the fixtures (unstable, stable twin, non-codebox `.gendsp`).

## Security Domain

Offline file reader only. V5 input validation: treat `.maxpat` JSON and codebox text as untrusted. Never `eval`/`exec`/`compile`/`importlib` on it; loop-iteration cap (DoS); Data/Delay allocation cap (e.g. ≤ 50M samples total → unsupported) since `Data ring(1344000, 2)` exists.

## Sources

**Primary:**
- In-repo files read this session: genexpr_parse.py, dsp_sim/cli.py, measure.py, genrun.py, test_bassoon-model.py, patterns/gen/*.gendsp, bassoon.gendsp, and stereo-feedback-delay at `9b1db66d`.
- Installed Gen refpages: gen_dsp_peek/poke/delay/history/phasor/latch/dcblock and gen_common_* (Max 9.1.5 bundle).

**Secondary:** scratch numpy prototypes (scratchpad `proto.py`/`proto2.py`, not committed) for threshold calibration; a Python 3.14.2 closure micro-benchmark.

**Research date:** 2026-10-21. Valid ~30 days.
