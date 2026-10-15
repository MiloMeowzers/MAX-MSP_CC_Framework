---
phase: quick-261014-i3b
plan: 01
status: complete
subsystem: docs
tags: [claude-md, skills, references, docstrings, review-S11, Q18]
requires: [Q16, Q17]
provides:
  - slimmed CLAUDE.md (one-line imperatives with pointers)
  - .claude/skills/references/db-maintenance.md
  - .claude/skills/references/genexpr-rules.md
  - ui-presets.md "Text Contrast Resolution"
  - single-sourced Builder API and Output Protocol (Edited Patches) in shared-capabilities.md
  - CLAUDE.md slim guard tests
affects: [every agent session (CLAUDE.md), max-dsp-agent, max-ui-agent, max-js-agent, max-patch-agent, max-rnbo-agent, max-ext-agent, max-router]
tech-stack:
  added: []
  patterns: ["rule-anchor guard test: every imperative keeps a verbatim literal", "strict-xfail pending markers so every intermediate commit is green"]
key-files:
  created:
    - .claude/skills/references/db-maintenance.md
    - .claude/skills/references/genexpr-rules.md
  modified:
    - CLAUDE.md
    - .claude/skills/references/shared-capabilities.md
    - .claude/skills/references/ui-presets.md
    - src/maxpat/builders.py
    - .claude/skills/max-dsp-agent/SKILL.md
    - .claude/skills/max-ui-agent/SKILL.md
    - .claude/skills/max-js-agent/SKILL.md
    - .claude/skills/max-patch-agent/SKILL.md
    - .claude/skills/max-rnbo-agent/SKILL.md
    - .claude/skills/max-ext-agent/SKILL.md
    - .claude/skills/max-router/SKILL.md
    - tests/test_claude_md.py
    - tests/test_agent_skills.py
decisions:
  - "CLAUDE.md slimmed 49,752 -> 26,782 bytes (-46.2%) with all 238 rule anchors and 30 base headings kept; budget ratchet CLAUDE_BUDGET_BYTES = 30_000"
  - "Waveguide derivation ships in genexpr-rules.md; CLAUDE.md no longer cites a .planning/ archive"
  - "Builder API and Output Protocol (Edited Patches) live once, in shared-capabilities.md; patch/ui carry an identical pointer stub, all six specialists point to the shared protocol"
metrics:
  duration: "~20 min"
  completed: 2026-10-14
estimate:
  tokens: 200000
  tasks: 3
actuals:
  tokens: 38900
  tasks: 3
  commits: 3
plan_head_before: 725f568f02f18725082f6a458d3f6e8e843b2f0c
plan_head_after: d30c199be80badcf871a1541d33e1a06eb578249
---

# Phase quick-261014-i3b Plan 01: Slim CLAUDE.md (Q18) Summary

CLAUDE.md cut from 49,752 to 26,782 bytes (-46.2%) with every rule kept as a one-line imperative and a pointer. Moved detail sits verbatim in db-maintenance.md, genexpr-rules.md (including the waveguide derivation, now shipped), ui-presets.md "Text Contrast Resolution", the builder docstrings and max-js-agent. The Builder API and edited-patch Output Protocol blocks are single-sourced in shared-capabilities.md.

## Commits

| Task | Commit | Message |
|------|--------|---------|
| 1 | b22fd90a | test+docs: CLAUDE.md slim guards; DB internals moved to references/db-maintenance.md (Q18) |
| 2 | 9aaee361 | docs: slim CLAUDE.md — gen~ rules to genexpr-rules.md, contrast to ui-presets, recipes to builder docstrings, js/N4M to max-js-agent (Q18) |
| 3 | d30c199b | docs(skills): Builder API and edited-patch Output Protocol single-sourced in shared-capabilities (Q18) |

## Sizes (bytes, `wc -c`)

| File | Before (725f568f) | After | Delta |
|------|------:|------:|------:|
| CLAUDE.md | 49,752 | 26,782 | -22,970 (-46.2%) |
| max-patch-agent SKILL.md | 20,891 | 15,116 | -5,775 |
| max-ui-agent SKILL.md | 14,257 | 8,703 | -5,554 |
| max-dsp-agent SKILL.md | 24,532 | 24,288 | -244 |
| max-js-agent SKILL.md | 8,668 | 9,014 | +346 |
| max-rnbo-agent SKILL.md | 6,551 | 6,098 | -453 |
| max-ext-agent SKILL.md | 4,833 | 4,380 | -453 |
| max-router SKILL.md | 5,639 | 5,782 | +143 |
| references/shared-capabilities.md | 11,449 | 18,265 | +6,816 |
| references/ui-presets.md | 4,492 | 6,592 | +2,100 |
| references/db-maintenance.md (new) | - | 6,820 | +6,820 |
| references/genexpr-rules.md (new) | - | 13,607 | +13,607 |

**Always-loaded reduction:** CLAUDE.md -46.2% (above the S11 ~40% target; under the 28,000-byte working target, so no section needs justifying).

**Per-agent effect of shared-capabilities gaining the Builder API (planner decision 12)** -- SKILL.md + shared-capabilities.md, the pair each specialist loads:

| Agent | Before | After | Delta | Note |
|-------|------:|------:|------:|------|
| patch | 32,340 | 33,381 | +1,041 | loses its Builder API copy, gains the shared one plus the shared protocol/reference bullets |
| ui | 25,706 | 26,968 | +1,262 | same as patch |
| dsp | 35,981 | 42,553 | +6,572 | now loads the 5.7 KB Builder API; also reads genexpr-rules.md (13,607) before GenExpr work |
| js | 20,117 | 27,279 | +7,162 | now loads the Builder API |
| rnbo | 18,000 | 24,363 | +6,363 | now loads the Builder API |
| ext | 16,282 | 22,645 | +6,363 | now loads the Builder API |

Net per session: CLAUDE.md saves 22,970 bytes for every session; a specialist session nets -21,929 (patch) to -15,808 (js). The dsp/js/rnbo/ext growth is the cost of the spec placing the Builder API in shared-capabilities.md.

## Rule inventory

- Q/rule-inventory.md: **193 units** (awk counter at base = 193): **182 RULE / 11 INFO**.
- Anchors: **238** in `RULE_ANCHORS` = 177 seed + 61 inventory additions. Every RULE row has at least one anchor; 13 moved-detail rows are covered by the seed anchor that their pointer one-liner keeps (`add_labeled_param_bank`, `add_overlay_readout`, `max-api`, `Legacy Engine`).
- All 238 anchors and all 30 base headings are present in the slimmed CLAUDE.md, re-checked after every section edit.

| Base section | Slim form | Detail home |
|---|---|---|
| Object Database / Supplementary Files / How to Use | file-tree block -> one line; one line per supplementary file; ObjectDatabase code block kept; 5 "DB rules" one-liners with their bold labels | `.claude/skills/references/db-maintenance.md` |
| Rule #1 | kept, lightly compressed | stays |
| Rule #2, #3, #4 | bullets compressed, every imperative kept | stays |
| Text Contrast | 2 paragraphs: WCAG 4.5:1 / precedence / encodings; ensure vs repair + pointer | ui-presets.md "Text Contrast Resolution" |
| Multislider | Codified line (recipe in docstring), one manual-bank line, full "Reading values by index" | `add_labeled_param_bank` docstring |
| Rule #5 | 2 paragraphs, all imperatives | stays (history dropped) |
| Rule #6 | Codified line + one paragraph + pointer | `add_overlay_readout` docstring; shared-capabilities "Z-Order Manipulation" |
| Rule #7 | one paragraph + 4 bullets | severity-contract.md section 5 |
| Rule #8, #9 | compressed, J3 kept | stays |
| MSP | one line per bullet; buffer~ 9.2 one line; mis-marked outlet one-liner | max-9.2-changes.md; db-maintenance.md |
| Gen~ | pointer line + 15 bold-labelled one-liners | `.claude/skills/references/genexpr-rules.md` |
| Subpatcher I/O | code block -> one sentence | stays |
| RNBO | Experimental line + 3 bullets | stays |
| N4M | 2 bullets | `.claude/skills/max-js-agent/SKILL.md` |
| js / v8 | 4 bullets | max-js-agent SKILL.md; max-9.2-changes.md |
| M4L | Experimental line + Codified + 4 bullets | `add_m4l_gen_synth` docstring (valueof keys) |
| bach, PD, Version, Bpatcher, Variable I/O, File Conventions | compressed; fences -> inline examples | max-9.2-changes.md (9.2 object list) |

**Dropped INFO** (full list in Q/rule-inventory.md "Final status"):
- Unit #61, the Rule #5 "This rule exists because ... deprecated in milestone 2.0" history. The reason survives as "(regeneration overwrites manual edits)".
- Sentences dropped from kept units, all rationale or anecdote with no instruction:
  - "silent bugs" (Rule #3, reworded);
  - "user-confirmed tight spacing" and "companion detection lives in defaults.py";
  - "Three orphaned stashes ... recovered" and the `stash && merge && pop` explanation;
  - the quoted replace_box docstring and "cost multi-version debugging cycles";
  - Rule #9's "This rule exists because ...";
  - gain~'s float-to-int rationale;
  - "(SIMD-friendly)";
  - js/v8 "All five are in the DB" and the bundled v8 example conventions (duplicated in max-js-agent).
- The DB file-tree object counts were dropped (statistics; `extraction-log.json` and `tools/audit_db.py` report them).
- Gen~ anecdotes and per-version evidence were moved verbatim to genexpr-rules.md, not dropped.

## Figures

- Baseline (725f568f): 3346 passed, 1 xfailed, 1 xpassed (matches the plan).
- Final: **3677 passed, 1 xfailed, 1 xpassed**, 29 warnings. The xfail/xpass are unchanged.
- Collected: 3348 -> 3679 (+331):

| Test function | New cases |
|---|---:|
| test_claude_md_size_budget | 1 |
| test_claude_md_headings_preserved | 1 |
| test_rule_anchor_present (a001-a238) | 238 |
| test_moved_detail_present (dbmaint 18, genexpr 20, uicontrast 7, jsagent 5, severity 5, max92 7) | 62 |
| test_claude_md_points_to_detail_home | 9 |
| test_claude_md_pointer_paths_exist | 1 |
| test_claude_md_no_private_paths | 1 |
| test_shipped_doc_has_no_private_paths | 2 |
| test_builder_docstrings_carry_recipes | 1 |
| test_dedupe_builder_api_in_shared | 1 |
| test_dedupe_skill_builder_api_is_pointer | 2 |
| test_dedupe_output_protocol_in_shared | 1 |
| test_dedupe_output_protocol_pointer | 6 |
| test_dedupe_rnbo_ext_subsections_kept | 1 |
| test_dsp_agent_loads_genexpr_rules | 1 |
| test_ui_agent_points_to_uicontrast_section | 1 |
| test_doc_call_forms_match_signatures (db-maintenance.md, genexpr-rules.md) | 2 |
| **Total** | **331** |

- **Test-first proof:** Q/red-run.txt (71 failed, 539 passed). Run before any doc edit or marker; every failure was in the planned red set.
- **Strict-xfail markers:**
  - After the DB slice, 48 cases were marked (Q/pending-markers.txt): `PENDING_T2` for 38 cases, `PENDING_T3` for 10 dedupe cases.
  - Task 2 removed every `PENDING_T2`; Task 3 removed every `PENDING_T3`.
  - No marker remains, and every commit's targeted run was green.
- **Tests:** test changes are additions only. `git diff 725f568f -- tests/` has no removed lines.
- **Safety checks:**
  - `git status --porcelain` was unchanged across every pytest run.
  - The stash list was unchanged (empty).
  - MEM hashes are unchanged (45 files, Q/mem.sha256).
  - No `(Q18)` commit touches `patches/`.
  - `noncode-check.py` confirms builders.py is AST-identical apart from docstrings.

## Decisions taken (planner decisions 1-14)

1. `references/` = `.claude/skills/references/`; the UI reference is ui-presets.md.
2. Budget ratchet 30,000. The final 26,782 is under the 28,000 target. No rule was dropped to hit a number.
3. All 30 base headings kept verbatim. The Subpatcher code block became one sentence.
4. Bold labels kept as citation anchors. These include `**Waveguide loop filters:**`, `**No local aliases in Param-only expressions.**`, `**Hoisted temps can be emitted out of order ...**` and `**Reading values by index:**`. Citations from dsp_sim, tests and skills therefore still resolve.
5. The ARCHIVE derivation ships in genexpr-rules.md under "## Waveguide loop filters" -> "### Derivation":
   - headings are demoted to `####`;
   - the front matter, the `=====` line and the session id are stripped;
   - project names only, no paths.
6. The "Reference docs" list sits under the intro and gives 8 full paths. The Experimental lines are the first line under the RNBO and M4L headings.
7. Sections outside the five targets were slimmed only by pointing at detail that lives elsewhere or by rewording:
   - severity-contract.md section 5;
   - max-9.2-changes.md;
   - the add_m4l_gen_synth docstring;
   - shared-capabilities "Z-Order Manipulation".

   The MSP mis-marked-outlet bullet moved verbatim to db-maintenance.md, and a one-liner stays.
8. Only INFO units or sentences were dropped (list above).
9. Skill dedupe covered exactly Builder API and Output Protocol (Edited Patches).
10. The Builder API stubs are byte-identical, so the four existing Builder API tests stay green without edits.
11. Placement:
    - Builder API goes after "## Layout Options".
    - Output Protocol goes after "## Edit Workflow".
    - The one overlay sentence was repointed to "Z-Order Manipulation" above and the docstring.
    - The Experimental label moved with the block.
12. The per-agent byte effect is reported above.
13. Pointers:
    - full paths in the Reference docs list;
    - bare basenames inline (`db-maintenance.md`, `genexpr-rules.md`, `severity-contract.md`, `shared-capabilities.md`, `max-9.2-changes.md`), each the basename of a file under `.claude/skills/`;
    - `context.md` is allowlisted.
14. builders.py docstrings only:
    - `add_labeled_param_bank` now holds the full recipe, the 14-param example, `p drift` / `p settings` and the full "Reading values by index" text;
    - `add_overlay_readout` now holds the 5-step manual equivalent and the `background=1` note;
    - patcher.py is untouched.

**Q17 handoffs:**
- **Handoff 1:** labels kept, so the dsp_sim, test and skill citations of CLAUDE.md "Waveguide loop filters" and "Reading values by index" still resolve and lead on to genexpr-rules.md and the docstring. Explicit new pointers were added only in the max-dsp-agent "Verdict & Fix Reference" column header and the `add_labeled_param_bank` docstring.
- **Handoff 2:** the derivation moved into genexpr-rules.md and CLAUDE.md's `.planning/` citation is gone. test_claude_md_no_private_paths guards this, which also closes review §3.8 bullet 3.
- **Handoff 3:** the Reference docs list includes troubleshooting.md and proven-forms.md.
- **Handoff 4:** the Experimental labels are now in CLAUDE.md's RNBO and M4L sections.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Section rewriter cut the Subpatcher section at a `#` comment inside a code fence**
- **Found during:** Task 2, Subpatcher section
- **Issue:** My temporary rewrite script treated the in-fence `# Connect to the third inlet` comment as a heading. It left an orphan fence opener that swallowed the following headings.
- **Detection:** test_claude_md_headings_preserved failed on that section, which is the per-section re-run working as designed.
- **Fix:** removed the leftover lines and made the rewriter fence-aware. The rest of the sections were then applied with all tests green.
- **Files modified:** CLAUDE.md (before commit)
- **Commit:** 9aaee361

**2. Small rule restorations while reviewing the slim text**
- Restored inline before commit:
  - the waveguide "source-side filters count as in-loop" clause;
  - "check inlet/outlet lengths, not just `exists()`";
  - the save gate's "pre-existing blockers still save; a new file refuses every blocker";
  - the bpatcher "post-round-trip `box.args` is empty" note.
- These are instructions, so they stay in the always-loaded file.

Otherwise the plan was executed as written.

## Out of scope / doc impact, not edited (rule 8)

- S11 also counts the fan-out rule (7×) and the `#N` rule (3×) across the skills. They are not in the Q18 spec, so they are a follow-up.
- max-patch-agent says "follow all 5 rules", which is stale: there are 9.
- max-ext-agent points to a CLAUDE.md externals section that does not exist.
- README's repo tree does not list `.claude/skills/references/`.
- src/maxpat/dsp_sim comments still cite the CLAUDE.md label "Waveguide loop filters". It still resolves.
- db-maintenance.md keeps the verbatim pre-Q1 wording that validation "strips" cords. CLAUDE.md's MSP one-liner now says "flags".
- Each specialist's "> **Shared Capabilities:**" blockquote lists shared section names. It does not yet name "Builder API" or "Output Protocol (Edited Patches)"; the stubs carry the pointer.
- The genexpr-rules.md 9.2 paragraph says "recorded here", now meaning genexpr-rules.md. It is verbatim, and the CLAUDE.md one-liner carries the rule.

## MAX/Live confirmation

**None needed.** This task changed docs and docstrings only, with no patch, codebox or runtime behavior change: builders.py is AST-identical apart from docstrings, and nothing under `patches/` changed.

## Known Stubs

None.

## Threat Flags

None. No new network, auth, file-access or schema surface.

## Self-Check: PASSED

- FOUND: .claude/skills/references/db-maintenance.md, .claude/skills/references/genexpr-rules.md, CLAUDE.md (26,782 bytes)
- FOUND commits: b22fd90a, 9aaee361, d30c199b
- Q artifacts (untracked, not staged):
  - base-sha.txt, stash-list-before.txt, mem.sha256;
  - sizes-before.txt, sizes-after.txt;
  - collect-before.txt, collect-after.txt;
  - baseline-pytest.txt, red-run.txt, t1-run.txt, pending-markers.txt;
  - rule-inventory.md, noncode-check.py, final-pytest.txt.
