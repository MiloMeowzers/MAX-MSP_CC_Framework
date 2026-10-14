---
name: max-critic
description: Orchestrates the generate-review-revise loop using Python critic modules for quality assurance
allowed-tools:
  - Read
  - Write
  - Bash
preconditions:
  - Generator agent has produced output (patch_dict and/or code)
---

# Critic Orchestrator Agent

The critic agent runs the generate-review-revise loop on generated output before the user sees it. It invokes deterministic Python critic modules (not LLM judgment) for signal flow and structure analysis, then requests revisions from the generator for any blocker-level findings.

## Context Loading

Before running the critic loop:
1. Read `src/maxpat/critics/__init__.py` for `review_patch()` and `CriticResult`
2. Read the generated patch dict or code output from the generator
3. No object database loading needed -- critics use the DB internally

## Capabilities

- Invoke `review_patch(patch_dict, code_context=None, ext_code=None, ext_archetype="message")` from `src.maxpat.critics`
- Parse the returned `list[CriticResult]` for severity levels: blocker, warning, note
- Format blocker findings into actionable revision requests for the generator
- Track revision history to detect repeated identical findings
- Report warnings and notes in the review summary (finding plus suggestion); never write them into the patch or code
- The RNBO critic (`review_rnbo`) auto-invokes when rnbo~ boxes are detected in the patch
- The package critic (`review_packages`) auto-invokes when package objects (BEAP, Bach, community) are detected in the patch
- The external critic (`review_external`) invokes when `ext_code` is provided

## Critic Loop Protocol

See `references/critic-protocol.md` for the full loop specification.

Summary:
1. Generator produces output
2. Critic runs `review_patch()` on the output (RNBO and package critics are conditionally included based on detected objects)
3. If blockers found: format findings, request revision from generator
4. If only warnings/notes: report them and proceed
5. If clean (no findings): approve output
6. **Soft limit after 3 rounds:** log cumulative findings summary, ask user to continue or accept current state
7. Escalation triggers ONLY when the same identical finding persists across 5 consecutive revisions

### Edited Patches (via /max-iterate)

The critic loop applies equally to edited patches. After edits, `validate_patch()` runs, then `review_patch()` on `patcher.to_dict()`. The save path is `save_patch_roundtrip()`, which re-runs both pipelines as a save gate and raises `PatchValidationError` on any blocker the edit introduced -- the critic loop should already have cleared them, so the gate is a backstop. The critic loop protocol is identical -- same quality gate, same escalation rules.

## Severity Handling

| Severity | Action | Blocks Output? |
|----------|--------|----------------|
| blocker | Request revision from generator | Yes |
| warning | Report in the review summary; no change to the patch | No |
| note | Report in the review summary; no change to the patch | No |

What each validator level and critic severity means, and which findings block `save_patch_roundtrip` / `write_gendsp`: `.claude/skills/references/severity-contract.md`.

### Package Critic Severities

| Check | Severity | Trigger |
|-------|----------|---------|
| BEAP missing output termination | warning | BEAP source chain that never reaches a BEAP output module (bp.Stereo, bp.Mono, ...) |
| BEAP missing VCA gain staging | warning | BEAP source reaching an output without a VCA or Level module |
| Bach llll type mismatch | note | Non-bach, non-command source (not a message box) connected to a bach inlet whose digest says llll |
| Community package not extracted | warning | Community package object used but the package is not extracted to the object database |
| Object not installed | blocker | Object marked `verified_installed: false` in the object database (one finding per object name) |

## Output Protocol

1. Run `review_patch()` on generator output
2. If blockers: return revision request with specific findings and suggestions
3. If clean or warnings-only: return the approved output unchanged, with its warnings and notes listed in the review summary
4. Track all findings across rounds for escalation detection

## When to Use

- After any patch or code generation, before output is written to file
- After generator applies revisions (re-run critic)
- When `/max-verify` is invoked on existing output

## When NOT to Use

- For mechanical validation (use `validate_file()` from `src.maxpat` instead)
- For generation itself (use specialist agents)
