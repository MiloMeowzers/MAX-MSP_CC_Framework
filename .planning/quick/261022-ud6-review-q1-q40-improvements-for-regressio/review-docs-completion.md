---
review: Q1-Q40 post-hoc — completion + doc accuracy
reviewed: 2026-10-22
range: 0f96a6f1..HEAD (8ddcdc49)
scope:
  - .planning/reviews/2026-10-11-fix-plan.md (Q1-Q40 spec bullets)
  - .planning/quick/2610*/ (PLAN/SUMMARY/VERIFICATION)
  - .planning/STATE.md "Quick Tasks Completed"
  - CLAUDE.md, TECHNICAL.md, README.md, .claude/skills/**/*.md, .claude/commands/*.md
scripts:
  - /private/tmp/claude-501/doccheck/check_docs.py   # backticked paths, Class.attr, src.* modules, `from src... import`, bare calls/identifiers, tool --flags
  - /private/tmp/claude-501/doccheck/sigcheck.py     # tests/test_doc_signatures.py scanner re-run with EVERY src.maxpat module indexed
findings:
  critical: 2
  warning: 6
  info: 12
  total: 20
status: issues_found
---

# Q1-Q40 review: completion and doc accuracy

## Method

- I compared each fix-plan Q section with its quick-task SUMMARY and VERIFICATION, then spot-checked about 15 spec bullets against the code (grep plus live probes).
- I ran `check_docs.py` over 69 doc files. It reported about 160 candidates. Most were false positives: JSON/attribute keys, JS/GenExpr built-ins, and example paths. Every finding below was re-verified by hand against the code or a runtime probe.
- `sigcheck.py` re-ran the Q16 signature scanner (443 snippets) with all `src.maxpat.*` modules indexed. It found one extra mismatch (WR-03). The stock `tests/test_doc_signatures.py`, `test_claude_md.py` and `test_agent_skills.py` pass (620 passed).
- Removed-code references (Q32: memory.py, relayout_patch.py, validate_db.py, merge_sources.py, add_node_script, contrast_text_color, is_complex_patch, suggest_subpatchers, verified-objects.json): no tracked file outside `.planning/` references them, except one dated audit report and the guard test. Clean.

## Completion table

Status = SUMMARY frontmatter / STATE.md status column. "Live/MAX pending" lists only items still awaiting the user. Where I found later evidence of a confirmation, it is noted.

| Q | Dir | Status | Deferred / open items (from SUMMARY) | MAX/Live confirm pending |
|---|---|---|---|---|
| Q1 | 261012-bii | complete / Verified | — | none |
| Q2 | 261012-c5i | complete / Verified | 40 outlet flips → Q11; 11 beyond-base ports → Q10 (both done later) | optional: `mc.matrix~ 3 2`=4 out, `play~ buf 2`=3 out |
| Q3 | 261012-di7 | complete / Verified | residual Comment-`#N` prose warnings (barnett-dbap obj-27, looper obj-6) | optional: slot.maxpat ordering |
| Q4 | 261012-egf | complete / Verified | only the first codebox per gen~ is compared; external .gendsp not checked; send~/receive~ not followed to plugout~; mc.gain~ / mc.live.gain~ not in the gain set | none |
| Q5 | 261012-m87 | complete / Verified | index.lock contention has no retry; paths outside `patches/<project>/` (Ambire, MUSC320, TCI, SCI) warn and are never auto-committed | optional StaleFileError check |
| Q6 | 261012-pkh | complete / Verified | stale midpoints on moved boxes (accepted, T-pkh-07); one-time assistance-comment diff on first edit | optional |
| Q7 | 261012-qsr | complete / Verified | DB cache per process; a validator crash propagates out of the save | none |
| Q8 | 261012-sam | complete / Verified | **manual step 2 (tag a release) not done: newest tag is v5.0.0**; B11 per-session pointer; Actions pinned by tag, not SHA | none |
| Q9 | 261012-ubw | complete / Verified | — | none |
| Q10 | 261013-cyg | complete / Verified | 23 arg-dependent bundle names still mismatch (mxj, dict.pack, live.gain~, plot~ …); port layouts not modelled | **recommended:** bare route/routepass (2,2), bare t (1,2), `notein 0` / `ctlin -1` |
| Q11 | 261013-e43 | complete / Verified | 73 package type-mismatch names; generator still writes placeholder digests | **MEDIUM-confidence values:** mxj~ (1,2), jit.polymovie (1,3), mira.motion (1,1), jweb~ out 2 control, live.adsr~ signal inlets |
| Q12 | 261013-mv6 | complete / Verified | no MAX-equivalent suggestions for floor~→trunc~, counter~→count~ | **div~ / rdiv~ / rdiv exemptions** (MEDIUM); optional clip() codebox |
| Q13 | 261013-q58 | complete / Verified, user-confirmed 2026-10-13 (e9852567) | 22 bundle "Wrong maxclass" (gswitch2, suckah, mira.frame …) | done |
| Q14 | 261013-v4k | complete / "—" (no VERIFICATION) | Snapshot group; thispatcher `script` subcommands; fix-plan deviation: thispatcher list taken from the .maxhelp | none |
| Q15 | 261014-d13 | complete / Needs Review | live.drop type 4; UnitStyle NATIVE | **PENDING in Live:** continuous dials, stereo out, Push banks, ModMode 4 vs 0 |
| Q16 | 261014-fbx | complete / Needs Review | dsp_critic suggestion text (IN-07); INDEX.md "reverb~" (IN-06); PACKAGES.md BEAP bp.LPF inlet | **PENDING:** 10 rewritten patterns/gen files compile; FluCoMa template roles |
| Q17 | 261014-gf2 | complete / "—" | critic-protocol critic list (IN-04); doc-reference guard test | experimental RNBO/M4L labels stay until confirmed; [observed] proven-forms entries |
| Q18 | 261014-i3b | complete / Verified | listed stale skill lines, all still unfixed (IN-01, IN-02, WR-06) | none |
| Q19 | 261014-t1y | complete / Verified | severity-contract / TECHNICAL scope wording, still unfixed (WR-01, WR-02) | none |
| Q20 | 261014-uzq | complete / Verified | cross-scope flow; poly~ `in N`/`out N` crossing; 917 bundle-only nested blockers | optional /max-verify output check |
| Q21 | 261015-bt8 | complete / Verified | DB marks pak/funnel inlet 1 cold (excluded by name only); RNBO trigger `s` | none |
| Q22 | 261015-du0 (+f1o) | complete / Verified | kicksynth tanh false negative; validate_patch never reads .js; f1o WR-01..05 and IN-01/02 left | **OPEN DECISION:** tab = error while 74/146 shipped C74 codeboxes contain tabs; RNBO single-bound Params |
| **Q23** | **261015-fm1** | **NOT IMPLEMENTED: PLAN.md only, dir untracked, no SUMMARY, no STATE row, no commits** | see CR-01 | n/a |
| Q24 | 261015-j0n | complete / Verified | — | none |
| Q25 | 261015-m9b | complete / Verified | 4 strict bassoon xfails (6-10 c drift), decision open | optional tuner check at 220 Hz |
| Q26 | 261015-nkm | complete / Verified | RNBO builder E8 half; gain~ slider-range input unchecked; sig~/line bridges; `_check_out_of_bounds` rect crash (fixed in Q27) | optional |
| Q27 | 261015-qm7 | complete / Needs Review | **PD-1/6/7/8 narrowings await acceptance.** PD-8: the overlap critic does not use the shared rendered_rect for comments, which narrows a spec bullet | **3 MAX checks** (empty-text comment readout, panel/header layout, message width) |
| Q28 | 261015-u3j | complete / Needs Review | PD-3, PD-4 decisions open; validation.py reads `_raw` before extra_attrs for mc.gen~ `data` | **2 MAX checks** (subpatcher port add; bgcolor/fontsize/hidden edits) |
| Q29 | 261016-d3y | complete / Verified, user-confirmed (981b7b80) | PD-2..6 decisions; legacy Max 8 layout | done |
| Q30 | 261016-jbx | complete / Verified | **PD-3..9 decisions (A-D) never answered**; chmod 0600 DB files | none |
| Q31 | 261016-mpq | complete / Needs Review | PD-13 list (fixed 1-in help patch, `<1,0>` sinks, build/ not ignored, C++ keywords) | **real min-devkit build; N4M hyphenated dict; js anything()** |
| Q32 | 261016-pz8 | complete / Verified | DB `maxclass` field kept (PD-1) | none |
| Q33 | 261016-tal | complete / Verified (spec item PARTIAL) | **"One UI-control set" not unified (PD-6 open)**; layout/analyze nondeterministic under hash randomization (49/61 files) | none |
| Q34 | 261016-uy1 (+l26, olv) | complete / "—" | open-questions.md | user-confirmed v0.1-v0.3 (f935e550); STATE does not reflect this |
| Q35 | 261021-urs (+cmr) | complete / Verified | WR-07 fixture pinning; IN-01..03; `else if` unsupported | **MAX test needed:** "both branches always execute" vs taken-branch simulator |
| Q36 | 261022-i07 | complete / Verified | — | **2 MAX checks** (atomic replace while open; touched-only contrast on default-text comments) |
| Q37 | 261022-ksz | complete / Needs Review | 9 doc impacts not edited (IN-03, IN-05) | console paste format |
| Q38 | 261022-mis | complete / Verified | 109 objectfile names unaliased | **vst~ 4→8 / retune~ 3→5 not recorded; needs user confirmation** |
| Q39 | 261022-o2q | complete / Needs Review | mc.gen~ @param, warning fan-outs, line~ rewrites, set_attr | **4 MAX checks** |
| Q40 | 261022-pqu | complete / Needs Review. The user overrode the "only after Q15 is confirmed in Live" gate (CONTEXT.md:21-24) | 5 doc follow-ups, all still open (WR-04) | **combined Q15+Q40 Live check** (.planning/quick/261022-pqu-…/q40-live-check.amxd) |

**STATE.md consistency:** 43 rows cover Q1-Q40 except Q23, plus f1o, l26, olv and cmr. Every commit hash resolves and matches its task. Discrepancies are in WR-07 and IN-08.

## Critical issues

### CR-01: Q23 (vocabulary checks) was silently dropped

**Files:** `.planning/quick/261015-fm1-implement-q23-in-planning-reviews-2026-1/` (untracked, PLAN.md only), `.planning/STATE.md:119-120`, `src/maxpat/validation.py`, `src/maxpat/builders.py` (`add_bpatcher`), `src/maxpat/critics/structure_critic.py`

**Issue:** The plan was written, but the task was never executed. There is no SUMMARY, no commit, and no STATE row, so the table jumps from 261015-f1o to 261015-j0n. Nothing marks Q23 as deferred: Q24-Q40 proceeded and Q17/Q14 still say "belongs to Q23". Code check of the 10 spec rows:
- Absent: `expr clip()` error; unknown object as an error on the load path (`validate_patch` has no `patch_path`; severity-contract.md:40 still says warning); message-selector warning; numeric-string bpatcher args error, plus coercion (`add_bpatcher('x.maxpat', args=['slot-1','0'])` still serializes `['slot-1', '0']`, the exact form CLAUDE.md "Bpatcher …" says fails with "bad arguments creating object"); unmatched send/receive; missing patcher `bgcolor`; int truncation; mc bare list.
- Partial: line~ comma segments. Only the pre-Q23 *warning* exists (`validation.py:1938`); the spec says error.
- Done elsewhere: bach `@out t`, by Q39 (`package_critic.py:8-12`).
- Tests: no `tests/test_vocabulary_*` files exist.

**Fix:** Run Q23 from its existing PLAN (rebase it: the bach row is done and Q36/Q38 touched the save gate), or record an explicit deferral in STATE.md and the fix plan. At minimum, ship the `add_bpatcher` numeric coercion and the bpatcher-args error, because CLAUDE.md documents that load failure as a known trap.

### CR-02: CLAUDE.md tells agents to run whole-patch `repair_text_contrast` on edited patches, which restyles half the confirmed corpus

**Files:** `CLAUDE.md:96`, `CLAUDE.md:137`, `.claude/skills/references/ui-presets.md:172`; contradicted by `src/maxpat/edit_session.py:18-24`

**Issue:** CLAUDE.md:96 says "on edited patches call `repair_text_contrast(patcher)`" and calls this mandatory. The Q36 edit session deliberately never runs it ("restyles 33 of the 63 committed patches on a no-op"). I measured this: `repair_text_contrast` changes 310 boxes in 33/63 committed patches. 300 of them are comments, and 268 had no `textcolor`, which is the default-text class the user's feedback memory says not to recolor. ui-presets.md:172 also says "Contrast is NOT recomputed on the edit path", which has been false for `edit_patch` sessions since Q36 (touched boxes get contrast). An agent that follows CLAUDE.md overwrites approved colours.

**Fix:** Change CLAUDE.md:96 to: "New patches: `finalize_patch(is_new=True)` runs `ensure_text_contrast`. Edits through `edit_patch` fix contrast on touched boxes only. Call `repair_text_contrast` only when the user asks for a whole-patch repair." Make the same change to ui-presets.md:172 and scope CLAUDE.md:137 to the promoted boxes.

## Warnings

### WR-01: severity-contract.md still describes top-level-only validation and critics

**File:** `.claude/skills/references/severity-contract.md:15, :46, :88`

**Issue:**
- Line 15 says Layer 5 covers "codeboxes of top-level `gen~` boxes". Line 46 says `proposed_removal` is "a top-level cord". Line 88 says "Blocking findings come from the top-level patcher".
- Since Q19/Q20, every scope is validated and reviewed. A probe of `p sub > gen~` with a `delay()` codebox gives `error … path='p1'`. `apply_fixes` returns 5-tuples for nested cords (validation.py:574-577). review_layout/m4l/package walk nested scopes.
- CLAUDE.md Rule #2 names this file as the contract for what blocks a save.

**Fix:** Rewrite the three passages: per-scope validation with `path`, 4-tuples at the top level and 5-tuples nested, and blockers from every non-gen scope.

### WR-02: TECHNICAL.md critic and validator sections are stale after Q19/Q20/Q40

**File:** `TECHNICAL.md:430, :541, :557, :562, :559-570`

**Issue:**
- :430 says "top-level `gen~`".
- :541 says the layout critic checks "Only the top-level patcher". `review_layout` returns "top level first, nested scopes in" pre-order.
- :557 and :562 describe M4L detection and ezdac~ as top-level only. `detect_m4l_device_type` scans every non-gen scope (m4l_critic.py:104).
- The M4L table omits the 8 Q40 rules: stereo_out, midi_passthrough, shortname_length, shortname_unique, int_param_range, param_range, bank_refs, device_height.

**Fix:** Update these lines and add the Q40 rows (all warning; shortname_length is a note).

### WR-03: dsp_sim docs give a raising call form and a removed topology

**Files:** `TECHNICAL.md:593`, `TECHNICAL.md:612`, `.claude/skills/max-dsp-agent/SKILL.md:348-349`

**Issue:**
- TECHNICAL:593 shows `run_simulation(patch_path, topology, params, sweep_param, sweep)`, but the signature is keyword-only (`(*, patch_path=…, topology=…, …)`). Called positionally, it raises TypeError.
- TECHNICAL:612 and SKILL:348 list `bore_only`. `get_topology('bore_only')` raises `TopologyError: unknown topology 'bore_only'. Known: reed_bore, reed_bore_post_radiation` (removed in Q25).
- TECHNICAL never mentions the Q35 `smoke` subcommand or `genexpr_interp`.

**Fix:** Use `run_simulation(*, patch_path=…, topology=…, params=…, sweep_param=…, sweep=…)`, drop `bore_only` from both lists, and add a `python -m src.maxpat.dsp_sim smoke <file>` paragraph.

### WR-04: The router and skills still say there is no .amxd writer and never mention the Q40 builder

**Files:** `.claude/skills/max-router/references/dispatch-rules.md:114, :120, :124`, `.claude/skills/references/shared-capabilities.md:175-226`, `max-patch-agent/SKILL.md:81`, `max-ui-agent/SKILL.md:87`, `max-critic/SKILL.md`

**Issue:**
- dispatch-rules.md:124 says "the framework writes .maxpat only (there is no .amxd writer)". `src.maxpat.m4l_device.export_amxd` exists.
- The router only offers `add_m4l_gen_synth`, and so do the builder lists.
- `add_m4l_device` and `export_amxd` are documented only at CLAUDE.md:211. Every one of these is a Q40 SUMMARY "doc follow-up" that was never done.

**Fix:** Add `add_m4l_device(kind, params, …)` and `export_amxd(maxpat_path)` (both experimental) to the shared Builder API and the agent builder lists. Fix dispatch-rules :114/:124, and add the Q40 rules to the max-critic M4L list.

### WR-05: proven-forms.md says `finalize_patch(is_new=False)` re-routes every cord

**File:** `.claude/skills/references/proven-forms.md:123`

**Issue:** The line says "on a large patch re-saved in MAX it re-routes every cord, so call only `populate_assistance_comments()` and route new cords by hand". Since Q6, `finalize_patch` "Never clears existing cable midpoints … routes only cords that have no midpoints AND are new or touch a box added or moved" (hooks.py:177-182). The line also contradicts shared-capabilities.md:267, which recommends that exact call as the manual path.

**Fix:** Change the Form line to say `finalize_patch(is_new=False)` / `edit_patch` route only new or touched cords, and keep the "no global apply_layout" rule.

### WR-06: db-maintenance.md says validation strips cords

**File:** `.claude/skills/references/db-maintenance.md:40`

**Issue:** The line says "gets stripped by validation". Since Q1, validation never removes anything (validation.py:22-26). The CLAUDE.md MSP bullet was already reworded to "flags" (Q18 noted the mismatch and left it).

**Fix:** Replace "gets stripped by validation" with "is flagged by validation (a proposed removal)".

### WR-07: STATE.md hides the missing Q23

**File:** `.planning/STATE.md:119-120`

**Issue:** No row, no "skipped" or "deferred" entry, and "Pending Todos: None" / "Blockers: None" (:62-66). Nothing in the tracked planning tree records that Q23 never ran.

**Fix:** Add a Q23 row marked "Not executed (PLAN only)", or add it under Pending Todos.

## Info

- **IN-01** `max-patch-agent/SKILL.md:22`: "follow all 5 rules". CLAUDE.md has Rules #1-#9. Change it to "all rules".
- **IN-02** `max-ext-agent/SKILL.md:34`: "Read `CLAUDE.md` externals section". CLAUDE.md has no such section, only the `.mxo` line at :254. Point the line at TECHNICAL's externals section or the skill's own BOUNDARIES.md.
- **IN-03** `max-lifecycle/references/test-protocol.md:70`: "saved to `test-results/test-NNN.md` with incrementing numbers". `save_test_results(project_dir, test_name, …)` writes `<test_name>.md` and overwrites it (testing.py:174).
- **IN-04** `max-critic/references/critic-protocol.md:19`: lists only the DSP, structure, RNBO and external critics. `review_patch` also always runs layout, and conditionally runs M4L and packages (critics/__init__.py:130-149).
- **IN-05** `README.md:136-148` Commands table:
  - It has no `/max-diagnose`, no `/max-iterate --fix`, and no `/max-verify --live`.
  - The `max-iterate.md:4` argument-hint omits `--plan`, although :36 parses it.
  - README and TECHNICAL never mention `edit_patch`, `Patcher.diff`, quick fixes, `max_bridge` / `max_verify_live`, `idioms.json` / `version_io.json`, or `walk.iter_patchers`.
- **IN-06** `patterns/gen/INDEX.md:73`: "Use Instead Of: External reverb~". `reverb~` is not in the DB (`db.exists('reverb~') == False`), so the cell names a nonexistent object. Q16 noted this and left it.
- **IN-07** `src/maxpat/critics/dsp_critic.py:452`: the unsafe-gain suggestion always says `scale 0 127 0. 1.`. CLAUDE.md requires `scale 0. 127. 0. 1.` for float sources. Q16 noted this; it is unfixed.
- **IN-08** STATE.md:
  - Q38-Q40 are dated 2026-10-23, but their commits and SUMMARYs are 2026-10-22 (local).
  - Q14, Q17, Q34, l26 and olv show status "—".
  - Q34's user confirmation (f935e550) is not reflected.
  - Q29, Q30 and Q33 read "Verified" while their PD decision lists are still unanswered (Q29's MAX checks were confirmed).
- **IN-09** No release tag since v5.0.0. Q8 SUMMARY manual step 2 ("tag the next version to ship the fixes") is outstanding.
- **IN-10** Untracked artifacts: the base-sha, baseline-pytest and stash-list files in the Q2-Q8 dirs, plus the whole Q23 dir (git status). Commit them or delete them, so the Q23 PLAN isn't lost.
- **IN-11** `tests/test_doc_signatures.py:57-68` `_INDEX_MODULES` leaves out `src.maxpat.dsp_sim`, `walk`, `quickfix`, `edit_session` and others, which is why WR-03 got through. Build the index with `pkgutil.walk_packages(src.maxpat.__path__)` (sigcheck.py does this and finds only WR-03).
- **IN-12** CLAUDE.md:
  - Rule #5 and Rule #7 never mention `edit_patch`, which is now the sanctioned edit path (max-iterate.md:98).
  - CLAUDE.md:61's "`validate_patch` errors on it at the top level" understates the behaviour: it errors in every max scope.
  - The genexpr-rules.md:13 / CLAUDE.md:163 "both branches always execute" rule conflicts with the Q35 interpreter. This is open per 261022-cmr and needs a MAX test before any rewording.

---
_Reviewer: Claude (gsd-code-reviewer), completion + doc-accuracy lane. Read-only: no source or doc edited._
