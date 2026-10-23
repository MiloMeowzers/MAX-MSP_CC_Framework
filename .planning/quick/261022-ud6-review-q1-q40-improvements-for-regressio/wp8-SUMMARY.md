---
quick_id: 261022-ud6
work_package: WP8 (docs sweep, CHANGELOG, STATE)
status: complete
branch: worktree-agent-a9c67b051068e01ab
plan_head_before: 2a2c24a5
commits: 16
claude_md: "255 lines / 28,536 bytes -> 255 lines / 29,523 bytes (+987 bytes; budget 30,000)"
tests: "python3 -m pytest -q: 7504 passed, 1 skipped, 4 xfailed (Python 3.14; 7509 collected). Doc tests (test_claude_md, test_doc_signatures, test_agent_skills, test_ud6_critics_docs): 628 passed"
---

# WP8 Summary: docs match the merged 261022-ud6 code; v6.0.0 CHANGELOG

Every doc finding in review-docs-completion.md and every "doc impacts" item in wp1-wp7b was applied, or is recorded below as already done or not applicable. CLAUDE.md keeps its one-line style and grew by 987 bytes. Most of the detail went into the reference docs. Nothing under `patches/**` was edited. Nothing was pushed or tagged.

## Doc items → result

| Source | Item | Result | File(s) |
|---|---|---|---|
| docs CR-02 / B11 | CLAUDE.md:96 told agents to run whole-patch `repair_text_contrast` on edits | done: edits recolour only added boxes that carry an explicit textcolor, never a default-text comment; whole-patch repair runs only on request | CLAUDE.md, ui-presets.md "Text Contrast Resolution" (new B11 path list), shared-capabilities.md |
| docs CR-02 | CLAUDE.md:137 Rule #9 contrast parity | done: scoped to the promoted boxes, no `ensure_text_contrast` on edits | CLAUDE.md |
| docs WR-01 | severity-contract "top-level only" (Layer 5, proposed_removal, blockers) | done: per-scope layers and `path`; 4-tuple / 5-tuple `apply_fixes`; Layer 5 covers every gen patcher (WP3 had already fixed §5.9) | severity-contract.md |
| docs WR-02 | TECHNICAL top-level claims and M4L table | done: layout and M4L critics walk every scope; M4L table has the 8 Q40 rules + `duplicate_device_io`, `ezdac~` in every scope, helper abstraction | TECHNICAL.md |
| docs WR-03 / WP6 IN-01 | `run_simulation` positional form, `bore_only`, no smoke section | done: keyword-only signature, two topologies, `smoke` section (port kinds, directives, lints, exit codes) | TECHNICAL.md, max-dsp-agent SKILL.md |
| docs WR-04 / WP4 | "no .amxd writer"; `add_m4l_device` / `export_amxd` missing from skills and router | done | dispatch-rules.md, shared-capabilities.md Builder API, max-patch/ui/dsp-agent SKILL.md, max-critic SKILL.md |
| docs WR-05 / WP2 #7 | proven-forms.md:123 and shared-capabilities finalize_patch claims | done: `is_new=False` routes only new or touched cords and never clears midpoints | proven-forms.md, shared-capabilities.md |
| docs WR-06 | db-maintenance "gets stripped by validation" | done: "is flagged (a proposed removal)" | db-maintenance.md |
| docs WR-07 | STATE.md hides Q23 | done: Q23 row and 261022-ud6 row | .planning/STATE.md |
| docs IN-01 | "follow all 5 rules" | done: Rules #1-#9 | max-patch-agent SKILL.md |
| docs IN-02 | "CLAUDE.md externals section" | done: points at BOUNDARIES.md and TECHNICAL "External Critic" | max-ext-agent SKILL.md |
| docs IN-03 | test-results `test-NNN.md` | done: `<test_name>.md`, overwritten | test-protocol.md, TECHNICAL.md |
| docs IN-04 | critic-protocol critic list | done: layout always; M4L and package conditional | critic-protocol.md, max-critic SKILL.md |
| docs IN-05 | README commands; `--plan` hint; edit_patch / diff / quickfix / bridge / idioms / version_io / walk unmentioned | done | README.md, max-iterate.md, TECHNICAL.md |
| docs IN-06 | INDEX.md "External reverb~" (not in DB) | done | patterns/gen/INDEX.md |
| docs IN-07 | unsafe-gain suggestion lacks the float `scale` form | done: code string plus its pinned test (red, then green) | dsp_critic.py, test_critic_fixes_e5_e8.py |
| docs IN-08 | STATE inconsistencies (dates, "—" statuses, Q34) | not done: out of the WP8 brief (rows only) | — |
| docs IN-09 | no tag since v5.0.0 | open: tagging is the user's call; recorded as a STATE pending todo | .planning/STATE.md |
| docs IN-10 | untracked artifacts in the main checkout | n/a in this worktree: those files are not in git | — |
| docs IN-11 | doc-signature index missed modules | done: `pkgutil.walk_packages` index, plus a `run_simulation` positional bad-form pin | tests/test_doc_signatures.py |
| docs IN-12 | Rule #5/#7 `edit_patch`; Rule #1 "top level"; "both branches" | done for the first two. "Both branches always execute" is left as is (open, needs a MAX test per 261022-cmr) | CLAUDE.md |
| WP1 | db-maintenance items | done: `trailing_inlets`, `resolve_inlet`, `is_shipped_signal_inlet`, `saved_outlet_type`, MC flavour, `_evidence`, merger semantics + `OverridesLoadError` + `--merge` rc, inlet/outlet I/O | db-maintenance.md |
| WP1 | severity / TECHNICAL items | done: rule ids, `patch_path`, legacy signal check, malformed ports, `*~ 0` mute sink, comment prose, version-layer wording | severity-contract.md, TECHNICAL.md |
| WP2 #1 | Rule #8: replace_box id / size / embedded patcher | done; max-iterate also says "rewires any in-range cord" | CLAUDE.md, shared-capabilities.md, max-iterate.md, TECHNICAL.md |
| WP2 #2 | Rule #5: no-op save byte-identical for every layout; maxjson exports | done (max-9.2-changes.md has no save section, so n/a there) | CLAUDE.md, TECHNICAL.md, severity-contract.md §5 |
| WP2 #4 | structured gate key; path keys on box id + maxclass | done | severity-contract.md §5.4, TECHNICAL.md |
| WP2 #5 / WR-09 | `LayoutRefusedError` in dsp and ui agents | done; also one line in CLAUDE.md Rule #5 | max-dsp-agent, max-ui-agent SKILL.md |
| WP2 #6 | `auto_commit_patch` raises RuntimeError | done | max-iterate.md, max-test.md, shared-capabilities.md, TECHNICAL.md |
| WP2 #8 | `modify_box` args / extra_attrs | done | shared-capabilities.md, max-iterate.md, TECHNICAL.md |
| WP2 #9 | `write_gendsp` explicit port removal | done | CLAUDE.md Rule #5, genexpr-rules.md, TECHNICAL.md |
| WP2 #10 | diff kind `cord_attrs` | done | TECHNICAL.md |
| WP3 | M4L helper abstraction; iterate / verify `is_new` | done | CLAUDE.md M4L, max-iterate.md, max-verify.md, TECHNICAL.md |
| WP4 | constants (`phi`, upper-case), functions-first order, tabs error/warn, M4L reuse and refusal, RNBO positional param + box shape, new GenExpr severities | done | CLAUDE.md Gen~/M4L, genexpr-rules.md, severity-contract.md §6, TECHNICAL.md (critic + new RNBO codegen section) |
| WP5 | smoke port kinds, `// smoke:`, silence WARN, exit 64 | done; fix-plan Q35/Q25 text left (only the Q23 note was requested) | max-dsp-agent SKILL.md, genexpr-rules.md, TECHNICAL.md, CHANGELOG.md |
| WP6 | README:168 bridge, `--check-deps`, trusted publishing, "v6.0" wording | done | README.md, TECHNICAL.md (new Release section), dsp_sim/README.md, TECHNICAL:138 |
| WP7a | theme fills, critic skips self-painted boxes, `duplicate_device_io`, `param_range` enable, filter-inlet gain exemption, gate `patch_path` / `original`, `validate_code_file(loaded=)`, `.gendsp` numinlets, dsp_sim constants, `--live` refused | done | ui-presets.md, severity-contract.md, TECHNICAL.md, genexpr-rules.md, dsp_sim/README.md, max-verify.md |
| WP7b | unknown object = error with path; Layer 4c errors and warnings; critic rules; line~ wording; bpatcher coercion; troubleshooting rows | done (`critics/__init__.py` docstring not edited: it is code and out of scope) | severity-contract.md, CLAUDE.md Rule #1 / MSP / Bpatcher, troubleshooting.md, TECHNICAL.md, max-critic SKILL.md |
| brief | test counts and LOC | done: 7,509 tests / 134 files; ~40,800 LOC | README.md, TECHNICAL.md |
| brief | CHANGELOG v6.0.0 | done: Breaking / Added / Fixed / Migration notes | CHANGELOG.md (new; no earlier release-notes convention existed) |
| brief | release.yml body | done: `scripts/release_notes.sh` extracts the tag's section before any publish step; `body_path` on the GitHub release step; 4 tests | .github/workflows/release.yml, scripts/release_notes.sh, tests/test_release.py |
| brief | STATE rows + fix-plan Q23 note | done | .planning/STATE.md, .planning/reviews/2026-10-11-fix-plan.md |

## Release wiring note

`Extract release notes` runs right after the archive build. A tag with no `## [X.Y.Z]` section fails at that step, before npm publish, so a mismatch can never leave npm published without a GitHub release. `softprops/action-gh-release@v3` takes `body_path`. `scripts/` is export-ignored, which is fine because the workflow runs from the checkout.

## Deviations

- **[Rule 1] IN-07 was a code string.** A test pinned the suggestion text, so I updated that test first (red), then the string (green).
- **[Rule 1] Doc-signature parse failures.** My first db-maintenance and genexpr-rules call forms (`count=`, `original=`) did not parse. Commit 43c6df60 landed with 2 failing doc tests; 9df5a1ff fixed them.
- **CLAUDE.md M4L blockquote.** I dropped "the combined Q15/Q40 Live check is pending" and "Q40;" to fit the byte budget. The pending Live check is still recorded in shared-capabilities.md and STATE.

## Needs confirmation

None new. Every unconfirmed behaviour is carried over from the WP SUMMARYs. The CHANGELOG migration notes and the STATE pending todos list them.

## Self-Check: PASSED

- All 16 WP8 commits are in `git log 2a2c24a5..HEAD`.
- CHANGELOG.md, scripts/release_notes.sh and this file exist.
- The full suite is green.
