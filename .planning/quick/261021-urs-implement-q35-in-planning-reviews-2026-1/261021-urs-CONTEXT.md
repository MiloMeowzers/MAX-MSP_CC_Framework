# Quick Task 261021-urs: Implement Q35 in .planning/reviews/2026-10-11-fix-plan.md — GenExpr interpreter and codebox smoke test - Context

**Gathered:** 2026-10-21
**Status:** Ready for planning

<domain>
## Task Boundary

Implement Q35 from `.planning/reviews/2026-10-11-fix-plan.md` (§4.4 R9, §5.2):

- **Interpreter:** generalize `patches/bassoon-model/tools/genrun.py` into `src/maxpat/dsp_sim/genexpr_interp.py`, using the Q22 parser (`src/maxpat/genexpr_parse.py`). Cover the proven-safe subset: Param, History, Delay read/write; Data/Buffer peek/poke with channel; if/else; constant-bound for; built-in math and constants; `in1..inN` / `out1..outN`.
- **New command:** `python -m src.maxpat.dsp_sim smoke <patch.maxpat|.gendsp>`. Runs every codebox for 1 s at 44.1 kHz with impulse plus noise inputs, at the Param default/min/max corners. Reports NaN/inf, peak > 4, DC offset, and permanent silence after excitation. Unsupported constructs give an "unsupported" verdict, never pass.
- **Tests:** the `patterns/gen` files pass; a deliberately unstable `tanh(x*g)/tanh(g)` feedback codebox fails; the bassoon codebox runs.
- Don't gate saves on it yet.

</domain>

<decisions>
## Implementation Decisions

### Execution engine
- **Tree-walking interpreter** (user choice): parse codebox GenExpr into an AST and evaluate it node by node per sample. Do NOT transpile to Python source and `exec` it (genrun.py's approach is being replaced, not generalized in form). No numba.
- Consequence to manage: speed. Keep the per-sample evaluator lean (e.g. pre-resolve variable slots, precompute node dispatch once at parse time) — but it must stay an AST evaluator. Provide a `--seconds` override (default 1.0) so tests can run shorter where needed; the CLI default stays 1 s at 44.1 kHz.

### Param corners
- **Default + one-at-a-time:** one run with all Params at default, then each Param at its min and at its max with the others at default (1 + 2N runs). Params without a declared min/max only contribute the default run on that side. The report names which Param/corner failed.

### Input stimulus
- **Impulse + noise on every inN by default**, with a CLI override per inlet, e.g. `--input 1=const:220`, `--input 2=dc:1` (exact syntax at planner's discretion, must be documented in `--help`). The bassoon test uses overrides (in1 is raw-Hz frequency).
- Noise must be seeded (deterministic runs).

### Non-codebox gen~ graphs
- Smoke covers codeboxes only. A gen~ / .gendsp whose patcher contains non-codebox gen operators (beyond in/out/codebox plumbing) gets an **"unsupported"** verdict — never a pass. Same for any GenExpr construct the interpreter does not support.

### Self-sustain check (post-research decision)
- Add a **self-sustain / latch check**: re-run each corner at 0.01× stimulus and compare post-excitation tails (inputs zeroed). A stable/linear design's tail scales ~0.01; a latched loop's tail ratio stays ~1 → **fail**. This is how the `tanh(x*g)/tanh(g)` fixture fails (it is tanh-bounded, peak ~0.85, so peak/NaN/DC/silence alone cannot fail it). Do NOT replace the fixture with a contrived peak>4 one.

### DC + stimulus level (post-research decision)
- **DC offset is a warning, not a fail** (phasor, envelopes, random walk, S&H etc. sit off zero by design).
- Default stimulus: 0.25 impulse + seeded ±0.1 noise for the first half of the run, then zeros (excitation-then-tail).
- Pattern tests use `--input` overrides (e.g. a phasor ramp for swing-generator / timing patterns) where a pattern needs a control-like input; no per-pattern verdict allowlist.

### Claude's Discretion
- Exact thresholds for DC offset and the "permanent silence after excitation" window (document them).
- Exit codes (suggest: 0 all pass, nonzero on any fail; unsupported treated as not-pass).
- How `Buffer` (external buffer~ refs) is backed in the sim (e.g. zero-filled or sized default) — document.
- Report format (text table; optional `--json`).
- Whether `patches/bassoon-model/tools/genrun.py` is left in place (it is used by the bassoon project's sim tooling — do not break it).

</decisions>

<specifics>
## Specific Ideas

- GenExpr rules to respect (CLAUDE.md "Gen~"): both branches of if/else always execute in gen (interpreter may evaluate normally but must not rely on short-circuit side effects); declarations precede expressions; built-in constant names (`e`, `pi`, `twopi`, ...) win over locals; `peek(buf, idx, chan)` / `poke(buf, val, idx, chan)`; Delay via `.write()` / `.read()`; History is a one-sample delay with sequential-assignment semantics as genrun.py models.
- The unstable fixture is `tanh(x*g)/tanh(g)` normalization inside a feedback loop (the CLAUDE.md rule says normalize by `/g`); the smoke must flag it.

</specifics>

<canonical_refs>
## Canonical References

- `.planning/reviews/2026-10-11-fix-plan.md` — Q35 entry (and §4.4 R9, §5.2 in the parent review)
- `src/maxpat/genexpr_parse.py` — Q22 parser (statement splitter, declarations, parse_params, io_counts)
- `patches/bassoon-model/tools/genrun.py` — existing minimal runner being generalized
- `src/maxpat/dsp_sim/` — existing sim package (cli.py, runner.py, measure.py) the `smoke` subcommand joins
- `.claude/skills/references/genexpr-rules.md` — full gen~ rules
- `patterns/gen/` — pattern files that must pass

</canonical_refs>
