---
phase: 261021-urs-implement-q35-in-planning-reviews-2026-1
reviewed: 2026-10-22T15:43:48Z
depth: quick
files_reviewed: 7
files_reviewed_list:
  - .claude/skills/max-dsp-agent/SKILL.md
  - src/maxpat/dsp_sim/README.md
  - src/maxpat/dsp_sim/cli.py
  - src/maxpat/dsp_sim/genexpr_interp.py
  - src/maxpat/dsp_sim/smoke.py
  - tests/dsp_sim/test_genexpr_interp.py
  - tests/dsp_sim/test_smoke.py
findings:
  critical: 2
  warning: 7
  info: 3
  total: 12
status: issues_found
---

# Quick 261021-urs: Code Review Report

**Reviewed:** 2026-10-22T15:43:48Z
**Depth:** quick (pattern scan, plus targeted reads of the verdict logic and interpreter semantics as the focus asked; every claim below was checked with a probe run)
**Files Reviewed:** 7
**Status:** issues_found

## Summary

The quick-mode pattern scan is clean. There are no secrets, no eval/exec/compile/`__import__`, and no debug artifacts. The only broad excepts are the two deliberate `except Exception` -> unsupported guards in `smoke.py`. The CLI change is a lazy-imported `argv[0] == "smoke"` dispatch ahead of the legacy parser. It does not regress the legacy command: the legacy parser has no positionals, and `argv=None` still resolves to `sys.argv[1:]`.

Operator precedence matches C: `||` < `&&` < `== !=` < relational < additive < multiplicative < unary. The ternary is right-associative. `/` and `%` give 0 on a zero divisor. `min`/`max` NaN handling matches genlib's `y<x?y:x`. The Delay ring indexing never reads the current head for t in [1, N]. `peek` and `poke` ignore out-of-range and non-finite indices.

The problems are in the verdict contract. "Unsupported never passes" holds for constructs the interpreter refuses. It does not hold for codeboxes that MAX itself rejects, or that give the checks nothing to check:

- **Uninitialized locals pass.** A local assigned only inside if/else (a documented gen~ compile error) and a codebox with no `outN` both come back as PASS.
- **A FAIL can be downgraded.** An interpreter error in a later corner wipes out a FAIL already found in an earlier corner.
- **Silent wrong semantics.** The taken-branch-only `if`, unclamped Param defaults and accepted tab characters all produce PASS with no finding.
- **False FAILs.** The "permanent silence" check fails correct codeboxes when no inlet carries the default stimulus.

Probe results for every finding are reproducible with `smoke_codebox(code, seconds=0.1)`.

## Narrative Findings (AI reviewer)

## Critical Issues

### CR-01: Locals read before assignment, or assigned only inside if/else, PASS, but gen~ refuses to compile them

**File:** `src/maxpat/dsp_sim/genexpr_interp.py:826-855` (local collection), `:44` (docstring "locals ... reset to 0.0 every sample"), `:1946-1957` (per-sample zero reset)
**Issue:** `parse_codebox` registers any assigned name as a local, and `Program.run` zero-fills every local each sample. Nothing checks that a local is defined on every path before it is read. `.claude/skills/references/genexpr-rules.md:14` (and CLAUDE.md "Gen~") says: "Variables used inside if/else blocks must be initialized before the block, otherwise GenExpr errors with 'not defined'". The probes:

- `if (in1 > 0) {\n y = 1;\n} else {\n y = 0.5;\n}\nout1 = y * in1;` -> verdict `pass`, no findings.
- `out1 = y;\ny = in1;` (read before any assignment) -> verdict `pass` (only a `silent` WARN).

These codeboxes fail at load in MAX, yet `smoke` exits 0. That breaks the stated contract that broken or unsupported code never passes.

**Fix:** Run a definite-assignment pass in `parse_codebox`. Walk the body in order with a set of names that are definitely assigned. For an `If`, add only the names assigned in both branches when an else exists, and none when it does not. A `For` body counts as not definitely executed. Raise `Unsupported(f"local '{n}' read before it is assigned on every path (gen~: 'not defined')", line)` on any read outside that set. In-loop reads of names assigned earlier in the same body are fine.

```python
def _check_defined(stmts, defined: set, code):
    for s in stmts:
        for e in _stmt_exprs(s):
            for n in _names_read(e):          # Name nodes only, not calls/methods
                if n in local_names and n not in defined:
                    raise Unsupported(f"local '{n}' used before it is assigned "
                                      "(gen~ 'not defined')", _line_of(code, s.off))
        if isinstance(s, Assign):
            defined.add(s.name)
        elif isinstance(s, If):
            t = set(defined); _check_defined(s.then, t, code)
            e = set(defined); _check_defined(s.els or (), e, code)
            defined |= (t & e) if s.els else set()
        elif isinstance(s, For):
            ...
```

### CR-02: A codebox with zero outputs, or a misspelled output name, passes with no checks

**File:** `src/maxpat/dsp_sim/smoke.py:544-552`, `src/maxpat/dsp_sim/genexpr_interp.py:1971-1972`
**Issue:** When `io_counts` finds no `outN`, `Program.run` returns `[]`. `_driven_checks` and `_ringout_checks` then loop over nothing, so `failed` is False and the verdict is `pass`. The probes:

- `ou1 = in1;` (typo, becomes a local) -> `pass`, 0 findings.
- `Data d(10);\npoke(d, in1, 0, 0);` -> `pass`, 0 findings.

A PASS with zero outputs examined is vacuous. The typo case is exactly the kind of broken codebox the smoke test exists to catch.

**Fix:** In `smoke_codebox`, return a non-pass when nothing can be checked:

```python
if cb.n_out == 0:
    return CodeboxResult(label, "unsupported",
                         "codebox has no outN outputs: nothing to check", 0, [])
```

Also consider a `warn` finding for any local whose name matches `^o?u?t?\d+$` but is not `outN`.

## Warnings

### WR-01: An exception in a later corner discards FAIL findings from earlier corners

**File:** `src/maxpat/dsp_sim/smoke.py:516-542`
**Issue:** The `try` wraps the whole corner loop. When any corner raises (for example a Param max that drives a `for` bound past `LOOP_CAP`), the handler returns `CodeboxResult(label, "unsupported", ..., 0, [])`, which throws away every finding collected so far. Probe: `Param g(1, min=0, max=200000); out1 = in1/0*0 + pow(10,400); for (i = 0; i < g; i += 1) { out1 += 0; }`. The default corner produces a `nonfinite` FAIL, but the result is `unsupported` with no findings, so the exit code is 3 instead of 1. Callers that treat 3 as "not checked" rather than "broken" will miss a real failure, and the NaN evidence is lost.
**Fix:** Move the try/except inside the per-corner loop. Record the error as a per-corner `Finding("unsupported", "fail", corner, 0, msg)`. Then compute the verdict as `fail` if any fail finding is not of the unsupported kind, else `unsupported` if any corner errored, else `pass`.

### WR-02: if/else runs only the taken branch, and stateful calls inside a branch give no finding

**File:** `src/maxpat/dsp_sim/genexpr_interp.py:1646-1671` (docstring `:65-67`, README `:217-218`)
**Issue:** The locked CONTEXT says "both branches of if/else always execute in gen (interpreter ... must not rely on short-circuit side effects)". The interpreter runs only the taken branch. So `phasor`, `cycle`, `noise`, `latch`, `dcblock`, `Delay.write` and `poke` in an untaken branch neither advance nor write, which differs from gen. Probe: `History c; if (c > 1e9) { out1 = noise(); } out1 = in1;` -> `pass`. The divergence is documented, but a codebox that hits it gets a plain PASS with no signal that the simulation was not faithful.
**Fix:** At build time, detect any `_STATEFUL_CALLS` entry (other than the pure-constant `dim`/`channels`/`mc_*`), `Delay.write` or `poke` inside an `If` body. Add a `cb.warnings` entry, surfaced as a `warn` finding (e.g. check `branch_state`). Alternatively, evaluate stateful call sites in both branches and select only the assignments.

### WR-03: Tab characters are accepted, although they are the documented suspect for gen compile failure

**File:** `src/maxpat/dsp_sim/genexpr_interp.py:244` (`(?P<ws>\s+)`)
**Issue:** `genexpr-rules.md:105` and CLAUDE.md ("Codebox safe-construct rules: spaces only, NEVER tab characters") flag tabs as the prime suspect for a generic codebox compile failure. The lexer treats `\t` as whitespace. Probe: `out1 =\tin1 * 0.5;` -> `pass`. `else if` and nested `for` from the same rule set are rejected, so the safe-construct coverage is inconsistent.
**Fix:** In `parse_codebox`, add a build warning (WARN finding) when `"\t" in code`, pointing at the first line that contains one. Or make it `Unsupported` to match the `else if` treatment.

### WR-04: Param defaults are not clamped to the declared [min, max]

**File:** `src/maxpat/dsp_sim/genexpr_interp.py:817-822`, `:1308-1312`; `src/maxpat/dsp_sim/smoke.py:332-343`
**Issue:** `Param p(min=0.5, max=1);` gets default `0.0`, and `Param p(5, min=0, max=1);` keeps default `5.0`; neither is clamped. The "default" corner (and every other Param's min/max corner, which holds this Param at its default) therefore runs at a value gen~ never produces, since gen~ clamps a Param to its range. Probe: `Param p(min=0.5, max=1); out1 = in1 / p;` runs with p = 0 (safediv -> 0), giving a `silent` WARN. That value can both hide a real failure at 0.5 and invent one at an out-of-range value.
**Fix:** In `parse_codebox`, after resolving the default, clamp it: `if p["min"] is not None: d = max(d, p["min"])`, and likewise for max. Apply the same clamp to any `params=` override in `_Builder.__init__`. If MAX's clamp-on-init behaviour is unconfirmed, tag the clamp `[ASSUMED]` in the docstring table.

### WR-05: "Permanent silence" FAILs correct codeboxes when no inlet carries the default stimulus

**File:** `src/maxpat/dsp_sim/smoke.py:508`, `:385-396`
**Issue:** When no inlet uses `impulse+noise` (0-inlet codeboxes, or every inlet overridden), `driven = (0, n)`. The silence check then fails any output that is active early and decays later, and its message claims "while the inputs are still active". Probes:

- 0-inlet decay `History h(1); out1 = h; h = h * 0.99;` -> `fail` (silence).
- A correct one-pole DC blocker with `--input 1=const:1` -> `fail` (silence).

Neither codebox is broken.
**Fix:** Only run the silence check when the driven window really has active input. Require `any_default`, or require that at least one inlet signal's absolute value over the tail is above `ACTIVITY_FLOOR` and changing (`np.ptp(sig[tail]) > ACTIVITY_FLOOR`). Skip it for `n_in == 0`. Fix the message to match.

### WR-06: `--input K=SPEC` for an inlet the codebox doesn't have is silently ignored

**File:** `src/maxpat/dsp_sim/smoke.py:491-502` (docstring `:483-484`)
**Issue:** `specs` only reads keys `1..cb.n_in`, so `--input 5=const:1` on a 1-inlet codebox is dropped without notice. In a multi-codebox file this can be intended. For a single codebox, a typo silently leaves the default stimulus in place. That also changes whether the ring-out and self-sustain checks run (`all_default`), so the user believes a configuration was tested when it was not.
**Fix:** In `smoke_file`, track which keys were consumed by at least one codebox. Print a stderr warning, or emit a `warn` finding, for keys no codebox used. Alternatively emit a per-codebox `warn` when `max(parsed_inputs) > cb.n_in`.

### WR-07: Tests are pinned to live user project files with hardcoded counts

**File:** `tests/dsp_sim/test_smoke.py:216-218`, `:243-262`, `:320-329`
**Issue:** `test_terrain_synth_discovery` asserts exactly 4 ok, 2 skipped and 6 entries in `patches/terrain-synth/generated/terrain-synth.maxpat`. The bassoon tests depend on `patches/bassoon-model/generated/*`. Both projects are actively edited by the user (MEMORY: terrain-synth v0.17.0 pending, bassoon drift xfails), so an unrelated patch edit will break the dsp_sim suite, or force a test edit. This is a test-reliability hazard, not a coverage gain.
**Fix:** Copy minimal fixtures (one embedded gen~, one sibling `.gendsp`, one jit.gen box) into `tests/dsp_sim/fixtures/` and assert discovery against those. Keep at most one smoke-only "real project parses without unsupported" test, without exact counts.

## Info

### IN-01: Declaration type order is not checked

**File:** `src/maxpat/dsp_sim/genexpr_interp.py:478-487`
**Issue:** Only "declarations before statements" is enforced. `genexpr-rules.md:19` prescribes Param, then Delay, then History, then Buffer/Data. `History h; Param p(1); ...` passes. This is low risk, since the hard compile requirement is the one already enforced.
**Fix:** Optionally add a `warn` when declaration types are out of the recommended order.

### IN-02: README title and scope still describe a bassoon-only harness

**File:** `src/maxpat/dsp_sim/README.md:1-5`
**Issue:** The README is titled "Bassoon Waveguide Pre-Flight Stability Harness" and says it is bassoon-specific. It now also documents the generic codebox smoke test (`:104`), which `max-dsp-agent/SKILL.md` points every gen~ edit at.
**Fix:** Retitle to "`dsp_sim` — waveguide stability harness and GenExpr codebox smoke test" and add one scope line for `smoke`.

### IN-03: `smoke_codebox` turns a bad `buffers=` argument into "unsupported" instead of raising ValueError

**File:** `src/maxpat/dsp_sim/genexpr_interp.py:1423-1428`; `src/maxpat/dsp_sim/smoke.py:484`, `:539-542`
**Issue:** The docstring says `smoke_codebox` "Raises ValueError on bad arguments". A malformed `buffers={"x": (0, 1)}` from an API caller instead raises inside `cb.build`. There the broad `except Exception` turns it into `unsupported: interpreter error: ValueError ...`. The CLI validates first, so only API callers are affected.
**Fix:** Validate `buffers` in `smoke_codebox` before the try block, the same way `inputs` is validated, or re-raise `ValueError` ahead of the generic handler.

---

_Reviewed: 2026-10-22T15:43:48Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: quick_
