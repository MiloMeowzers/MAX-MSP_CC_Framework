# Quick Task 261015-du0: Implement Q22 in .planning/reviews/2026-10-11-fix-plan.md — GenExpr parser, codebox lint, js ES5 lint - Context

**Gathered:** 2026-10-15
**Status:** Ready for planning

<domain>
## Task Boundary

Implement Q22 from `.planning/reviews/2026-10-11-fix-plan.md` (lines 402-427): one GenExpr tokenizer/statement parser (S5) used by `parse_genexpr_io`, `reorder_genexpr_declarations`, `parse_genexpr_params` and `validate_genexpr` (fixes G1, G2, G4); new `validate_genexpr` lint checks (R6); `validate_js` ES5 lint for js/jsui only plus comment-aware inlets/outlets parsing. One test per check. The fix plan's "Rules for every task" (lines 19-31) apply and must be copied into PLAN.md.

</domain>

<decisions>
## Implementation Decisions

### js engine detection (ES5 lint scope)
- Add an engine parameter to `validate_js` (e.g. `engine: str | None`). ES6 syntax (const, let, `=>`, template literals, class, default parameters) is an error only when engine is `js`/`jsui`; never for `v8`/`v8ui`.
- For standalone `.js` file validation (hooks.py path), scan `.maxpat` patches in the same project directory for a `js`/`jsui`/`v8`/`v8ui` box whose text names the file. ES5 errors only when a js/jsui box references it. Unreferenced or v8-only files: no ES5 errors (a note at most).
- Patch-level validation (where the referencing box is known) passes the box's engine directly.

### tanh feedback-path detection
- Flag `tanh(...)/tanh(` (normalize-by-tanh-of-drive) as an **error** when the codebox declares any `History` or `Delay` (feedback state exists); otherwise a **warning**. No dataflow analysis.

### Committed patches that trip new checks
- Follow fix-plan rule 3: fix false positives in the checker; allowlist true positives with a written reason (tape-wobble obj-3 `pi`/`twopi` assignment must be reported, then allowlisted) and list every allowlist entry in SUMMARY.md. New checks ship at the severities in the spec table.

### Claude's Discretion
- Parser module location/name and API shape.
- Allowlist mechanism (reuse an existing allowlist if one exists in the critics/validation code).
- How the de-hoist warning ("local alias in a Param-only expression without `History one(1)`") is detected heuristically.

</decisions>

<specifics>
## Specific Ideas

- G4 repros: `Param freq(440, min=20);` → max must not be 1.0 < min (missing bounds → None); `Param g(0.5) ;` must parse; `samplerate*0.25` default must not raise.
- G2 repro: `"// mix in4 and out3"` must not yield (4,3) ports.
- G1: reordering must not resurrect `/* */`-commented declarations nor split multi-line `Param …(\n…);`.

</specifics>

<canonical_refs>
## Canonical References

- `.planning/reviews/2026-10-11-fix-plan.md` Q22 (lines 402-427) and rules (lines 19-31)
- `.planning/reviews/2026-10-11-repo-review.md` G1/G2/G4 (lines 137-140), S5 (line 196), R6 (line 338), line 304
- CLAUDE.md "Gen~ (GenExpr DSP Code)" section and `.claude/skills/references/genexpr-rules.md`

</canonical_refs>
