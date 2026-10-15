# Quick Task 261014-t1y: Implement Q19 in .planning/reviews/2026-10-11-fix-plan.md — shared walker and recursive validation - Context

**Gathered:** 2026-10-14
**Status:** Ready for planning

<domain>
## Task Boundary

Implement Q19 of `.planning/reviews/2026-10-11-fix-plan.md` (findings A7, S1/S2, G8 partial): new `src/maxpat/walk.py` (`iter_patchers`, quote-aware `box_name`/`box_args`), `validate_patch` Layers 2–5 per scope with path-tagged findings, codeboxes checked in every scope, empty-text crash fix, duplicate box ids as a Layer-1 error, dedupe the name extractors, regression tests, triage of new findings on committed patches. Critics/analyze/checklist/graph recursion is Q20 — out of scope.

</domain>

<decisions>
## Implementation Decisions

### Path tagging
- Add a `path` slot to `ValidationResult` (`""` at top level).
- Nested findings ALSO get a message prefix, e.g. `[p synth > gen~] ...`. Top-level messages stay byte-identical so save-gate keys and existing tests are stable.

### Nested auto-fixes
- `proposed_removal` for nested cords is path-aware; `apply_fixes` walks to that scope's patcher and removes the cord there (both dict and Patcher inputs). Top-level behaviour unchanged.

### External abstractions
- Walk embedded patcher dicts only. Bpatchers/poly~/abstractions that reference an external file are not loaded.

### Gen/RNBO scope rules
- Reuse existing scope machinery (Q12 `detect_patcher_scope`, `DOMAIN_SCOPES`): each scope runs Layers 2–5 with its scope; gen scope skips MSP-only domain rules (dac~ termination, gain staging, etc.); rnbo scope applies rnbo_compatible logic. No new rule families.

### RNBO compatibility severity (decided after research)
- In nested rnbo~ scopes, `rnbo_compatible: false` is reported at WARNING level (never a save blocker), with alias resolution before the lookup; signal/role type checks are skipped in nested RNBO scopes. Fixing the rnbo_compatible data itself is out of scope.

### Top-level .gendsp codeboxes
- `validate_patch` keeps NOT checking a top-level gen file's own codeboxes (validate_code_file covers them; preserves write_gendsp gate behaviour).

### Claude's Discretion
- Exact path segment naming (box text vs varname), walker context detection for poly/bpatcher, internal refactor shape.

</decisions>

<specifics>
## Specific Ideas

Required regression tests (each flagged with its path): `osc~` inside a `p`; out-of-range cord in a subpatcher; codebox `delay()` inside p → gen~. Plus empty-text newobj no longer crashes, duplicate box ids → Layer-1 error.

</specifics>

<canonical_refs>
## Canonical References

- `.planning/reviews/2026-10-11-fix-plan.md` — Q19 section + "Rules for every task" (copy into PLAN.md)
- `.planning/reviews/2026-10-11-repo-review.md` — A7, G8, S1, S2

</canonical_refs>
