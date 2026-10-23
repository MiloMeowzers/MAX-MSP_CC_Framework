---
phase: quick-261022-mis
plan: 01
subsystem: object-db / validation / bundle sync
status: complete
tags: [Q38, bundle-mining, idioms, aliases, min_version, version_io, target_version]
requires: [Q9 help-io oracle (tools/help_io.py), Q30 objectfile report + --apply aliases]
provides:
  - .claude/max-objects/idioms.json (10,122 shipped cord keys)
  - .claude/max-objects/version_io.json (8 names)
  - 232 objectfile aliases in aliases.json (244 total)
  - string min_version across the DB
  - validate_patch(..., target_version=...)
affects: [validation Layer 3, Patcher.replace_box_safe, ObjectDatabase load, tools/sync_max_bundle.py CLI]
tech-stack:
  added: []
  patterns: [single-path DB writer with canonical bytes (mirrors groups.json), shared outlet_signal_class for miner and query]
key-files:
  created:
    - .claude/max-objects/idioms.json
    - .claude/max-objects/version_io.json
    - tests/test_idioms.py
    - tests/test_objectfile_aliases.py
    - tests/test_version_io.py
  modified:
    - tools/help_io.py
    - tools/sync_max_bundle.py
    - src/maxpat/db_lookup.py
    - src/maxpat/validation.py
    - src/maxpat/patcher.py
    - .claude/max-objects/aliases.json
    - .claude/max-objects/overrides.json
    - 35 x .claude/max-objects/**/objects.json (min_version only)
    - .claude/scripts/extract_objects.py
    - .claude/scripts/extract_abstractions.py
    - tests/test_db_tooling.py
    - tests/test_domain_scope.py
    - tests/test_version_tags.py
    - tests/fixtures/help_io_baseline.json
    - CLAUDE.md
    - .claude/skills/references/db-maintenance.md
    - .claude/skills/references/severity-contract.md
    - TECHNICAL.md
decisions:
  - "Shipped-idiom exemption covers Layer 3 type/role checks only; bounds, missing-box and malformed cords stay errors, and Layer 4 value/topology rules are untouched"
  - "Only the 13 mc_wrapper mc.* objectfile names are aliased; the 11 file-basis mc.* names (mono externals, no help I/O evidence) stay unaliased"
  - "version_io.json is regenerated wholesale (mined evidence, not curation); the dry-run +/-/~ counts are the review step"
  - "The target_version layer runs in max scopes only and emits warnings only (never part of the save gate)"
  - "vst~ 4->8 / retune~ 3->5 are NOT recorded in version_io.json: every bundle help box of each shows one I/O (Q11 already fixed those DB gaps); needs user confirmation"
metrics:
  duration: "~27 min"
  completed: 2026-10-22
estimate:
  tokens: 175000
  tasks: 3
actuals:
  tokens: 297972   # chars/4 over the full diff; 34,957 excluding .claude/max-objects data and the help-io fixture
  tasks: 3
  commits: 5
plan_head_before: 3da1f6e02064a34fd53e7284be07ac827103c08a
plan_head_after: 549400aad40947847217c94f6f91a5537f43cf18
---

# Phase quick-261022-mis Plan 01: Q38 bundle mining Summary

Validation no longer flags cords that Max's own help patches use. A new file, idioms.json, lists 10,122 such cords mined from the bundle's help files, and Layer 3 and `replace_box_safe` skip type/role checks for them; bounds are still checked. 232 `max objectfile` shortcut names now resolve: mc.*~ shortcuts, hslider, list.* -> zl.*, jit.op shortcuts and Vizzie short names. Every `min_version` in the DB is now a string. A second new file, version_io.json, records per-version I/O changes for 8 objects, and `validate_patch(..., target_version="9.0")` uses it to warn about patches that will break on older Max builds (warnings only).

## Commits

| Task | Commit | Message |
|------|--------|---------|
| 1 (tracer) | 5ed4d5b3 | feat(db): shipped-idiom allowlist mined from bundle help cords; Layer 3 never type/role-checks a cord MAX ships |
| 2A | 431929f7 | feat(sync): --apply aliases --shadowed for RNBO-shadowed objectfile names; aliases never retarget an override |
| 2G | 1f87d519 | feat(db): 232 objectfile aliases ...; min_version stored as a string everywhere |
| 3 | 2fb31736 | feat(validation): version_io.json mined from help boxes; validate_patch(target_version=...) warns collaborators on older builds |
| 3 docs | 549400aa | docs: Q38 idioms, objectfile aliases, string min_version, version_io and target_version |

## Regression gate

- **Baseline** (Step 0, HEAD 3da1f6e0, before any edit): 6008 passed, 5 xfailed, 1 xpassed, rc 0. This matches the planning-time figure.
- **Final** (Task 3 verify, run as written): 6064 passed, 5 xfailed, 1 xpassed, rc 0. `baseline_rc 0 final_rc 0`.
- **junit_diff.py:** `base=6014 new=6070 added=86 offenders=0`, exit 0.
  - Removed: exactly the 30 allowed `tests.test_domain_scope.TestRealDbRestrictions::test_exempt[list.*]` ids.
  - Added (86), all passing: test_idioms 33, test_version_io 45, test_objectfile_aliases 3, test_db_tooling 4 (TestI6ApplyAliases), test_version_tags 1.
- `git status --porcelain patches patterns` and `git stash list` match their Step 0 snapshots (both empty). No commit touches patches/ or patterns/, and every commit staged explicit paths.
- **Red counts (tests run before the code existed):**
  - Task 1: test_idioms.py failed at collection (ImportError on `outlet_signal_class`). After the miner and writer were in, 5 tests were still red until the exemption and the idioms.json write landed.
  - Task 2A: 4 of the new TestI6ApplyAliases tests failed.
  - Task 3: test_version_io.py failed at collection (ImportError on `parse_version`).
- **Task verifies:** VERIFY1-OK, VERIFY2-OK and VERIFY3-OK, each run as written in the plan. Task 2 also ran a full-suite check before its data commit: 6019 passed, 5 xfailed, 1 xpassed.

## Part 1: shipped idioms

- `--apply idioms` mined **10,122 pairs** (planning estimate: ~10,030).
  - They come from **49,457** recorded cords. A further 11,750 cords were excluded (ineligible endpoints) and 0 were unclassified.
  - Running the dry-run again prints `+0 pending`.
- The live test `test_bundle_help_cords_are_never_flagged` validates every eligible bundle help cord alone against the real DB.
  - It checks more than 40,000 cords.
  - None gets a type/role finding.
- At HEAD these cords had produced 29 removal-proposing errors and 1218 warnings (planning-time figures).
- I/O snapshot unchanged versus Step 0 after Task 1 (3,091 names).

## Part 2: objectfile aliases and string min_version

**Alias groups (232; aliases.json now holds 244):**

| Group | Count | Examples |
|-------|-------|----------|
| mc_wrapper mc.*~ shortcuts | 13 | mc.times~ -> mc.*~, mc.plus~ -> mc.+~, mc.audiounit~ -> mc.vst~ |
| hslider | 1 | hslider -> slider |
| list.* -> zl.* | 31 | the 30 RNBO-shadowed names + list.iter |
| jit.op shortcuts | 97 | jit.+ -> jit.op |
| Vizzie short names | 90 | 4mixr -> vz.4mixr (smoothr and world have no candidate) |

- **overrides.json:**
  - The 30 `list.*` Q12 exemption entries are deleted. `list.ease` is kept.
  - cycle~'s `min_version` is now `"4"`.
  - A semantic check against HEAD confirms nothing else changed.
- **min_version:** 3,445 values in 35 objects.json files were converted to strings.
  - Values: "8" ×3050, "8.1" ×215, "9" ×167, "9.2" ×12, "4" ×1.
  - A per-file semantic check confirms nothing else changed.
  - The extractors now write `"8"`.
- **I/O vs Step 0:** only the 30 list.* names changed, as allowed.
- **Dry-run objectfile line:** `719 lines, 716 names, 109 unresolved ..., 0 RNBO/Gen-shadowed`.
- **RNBO compatibility:** RNBODatabase still reports every list.* name as rnbo-compatible with its RNBO entry.
- **Help-io baseline:** regenerated with 0 regressions and 19 improvements, all `count_mismatches` dropping to 0:
  - bundle: list.delace, list.indexmap, list.join, list.lace, list.len, list.lookup (3->0), list.median, list.queue, list.reg (2->0), list.rev, list.rot, list.stack, list.sum, list.swap, list.thin, list.union, list.unique;
  - package:FluidCorpusManipulation list.reg;
  - package:RNBO list.lookup (2->0).

**The 109 objectfile names left unaliased** (outside the five groups, no candidate, or help disagrees; left for a follow-up):
- Outside the five groups:
  - GSwitch, GSwitch2, array.shuffle, array.sub, audiounit~, dsp_delay, jit.gl.grab, jit.gl.movie~, jit.gl.text2d, jit.gl.text3d;
  - jit.mo.line, jit.mo.perlin, jit.mo.saw, jit.mo.tri, jit.time.delta, jit.time.line, jit.time.tri;
  - mc.input, mc.jit.catch~, mc.jit.movie~, mc.jit.release~, mc.levelmeter~, mc.meter~, mc.multigain~, mc.plugin~, mc.plugout~, mc.plugphasor~, mc.scope~, mc.spectroscope~, mcp.sfplay~, mcs.audiounit~;
  - multiSlider, omsinfo, string.at, string.chars, string.fromchars, string.passcmp, string.sub, ubumenu, uslider, xbendin2, xbendout2.
- No candidate:
  - liveui.map, liveui.multimap, mc.div~, mc.rdiv~, mc.live.adsr~, node.debug, smoothr, world;
  - the 59 mc.abl.dsp.*~ names: alternate, basicshapes, bitgrunge, bubble, chip, chorus, compander, crackle, darkhall, dfm, distortion, doubler, dualbasicshapes, ensemble, envfollower, euclid, expshaper, extratone, filterednoise, filther, flanger, fmbass, foldfm, fuzz, harmonicfm, meldfilter, meldosc, modalresonator, modulator, noiseloop, noisyshapes, overdrive, phaser, pitchestimator, pitchshifter, prism, pulsate, quartz, rain, ramp, ringmod, saturator, shepard, shimmer, simplefm, squarefifth, squaresync, stereolfo, subosc, swarm, tarp, tides, transform, transientdesign, velvetnoise, vibrato, vowel, wander, waveshaper.

The full list with bases and candidates is in QDIR/unaliased-109.json.

## Part 3: per-version I/O and target_version

**version_io.json: 8 names, the same set predicted at planning time.** The dry-run reports 6 ambiguous arg groups (plan estimate: 7: comment, gain~, jit.avc, live.comment, live.gain~, plot~) and 0 conflicting names.

| Name | Change (after -> by) | Delta | Newer than installed 9.2.0 |
|------|---------------------|-------|-----|
| live.meter~ | 7.0.3 -> 9.0.0 | +1 outlet | no |
| metro | 9.0.0 -> 9.3.0 | +2 outlets | yes |
| midiformat | 7.0.3 -> 8.1.4 | +1 outlet | no |
| midiparse | 7.0.3 -> 8.1.4 | +1 outlet | no |
| mousestate | 9.0.0 -> 9.0.5 | +5 outlets | no |
| poke~ | 7.0.0 -> 9.0.0 | +1 outlet | no |
| preset | 8.2.0 -> 9.0.0 | +1 outlet | no |
| twist~ | 9.0.0 -> 9.3.0 | +1 inlet | yes |

- For every change up to 9.2.0, the DB's current layout equals the post-change layout, so the port check compares against the right counts.
- metro and twist~ come from help files saved by a 9.3 build. Validation ignores them until the installed Max reaches 9.3.

**Decision for the user: vst~ 4→8 and retune~ 3→5 were intentionally not recorded.**
- Every bundle help box of each object (all saved by 9.0.0) shows one I/O.
- Neither name is in version_io.json, in `conflicting` or in `ambiguous_names`. `test_vst_and_retune_have_one_io_in_the_bundle` locks this.
- The review's "vst~ 4→8, retune~ 3→5" were DB-vs-help gaps, which Q11 already corrected (the DB now has vst~ 2/8 and retune~ 3/5).
- No shipped help box disagrees across versions, so nothing was invented (Rule #1).
- Confirm or supply other evidence (for example a help patch from an older build) if a version delta is still wanted.

**`validate_patch(patch, target_version="9.0")`:**
- It adds layer `version` warnings in max scopes only. Nested max-scope patchers are included and tagged with their path; gen and rnbo scopes are skipped.
- It warns for a box whose min_version is newer than the target (e.g. `jit.message` needs 9.2).
- It warns for a cord on a port the target build lacks (e.g. mousestate outlet 7 at 9.0 or 9.0.3).
- With `target_version=None` the results are identical to before; the test checks three committed patches.
- An unparsable target raises ValueError.
- It never emits an error, so the save gate is unchanged.

## Deviations from Plan

**1. [Rule 3 - Blocking] Help-io baseline regenerated against the committed package set**
- **Found during:** Task 2 Part F.
- **Issue:** the user's packages dir now contains `Vision` (v1.0.2), installed after the committed baseline. Regenerating as written added a new `package:Vision` source with 5 new mismatching names, so the check that the new file "only lowers or drops per-name counts" failed. The source is outside Q38.
- **Fix:** I regenerated with `--packages-dir` pointing at a scratchpad dir of symlinks to every installed package except Vision. That keeps the baseline's committed source set. Result: 0 regressions, 19 improvements, no new names. The live `test_help_io` class treats Vision as a new source, which is never a regression.
- **Commit:** 1f87d519.

**2. [Rule 1 - Test design] The overrides-guard test uses `list.len`, not `hslider`**
- **Found during:** Task 2 Part A.
- **Issue:** ObjectDatabase raises at load for an overrides key with no base domain entry. An `hslider` override in the fake world would therefore break the DB load rather than exercise the guard. A name that has a base entry resolves and is skipped first.
- **Fix:** the realistic case is an RNBO-shadowed name with an override (the pre-Q38 list.* shape). The test adds a `list.len` override and runs `--shadowed`; the name is aborted with the overrides.json reason and aliases.json stays byte-identical. The guard runs for every name that would otherwise proceed.
- **Commit:** 431929f7.

**3. [Rule 2] `scan_version_io` takes an optional `installed=` keyword**
- **Issue:** the plan's signature is `scan_version_io(max_app, db)`, but each change also needs `newer_than_installed`, which depends on the installed version.
- **Fix:** an optional keyword. The sync tool passes the install's short_version; without it the flag is False.
- **Commit:** 2fb31736.

**4. The ambiguous-group count is 6, not the planning estimate of 7**
- This is the observed result. It is reported as found and nothing was edited by hand.

Otherwise the plan was executed as written.

## Executor-noted design choices

- **Bounds and Layer 4 are not exempt.** The idiom exemption skips only the Layer 3 type/role checks: the `Unverified outlet types` warning, the role-tier warnings and `Signal outlet to control-only inlet`. Bounds, missing-box and malformed cords are always errors. Layer 4 value/topology rules (gain safety, feedback, unterminated chains) are not pair-validity checks and are untouched.
- **File-basis mc.* names are not aliased.** Only the 13 `mc_wrapper` lines are aliased, because they instantiate the same class as the target. The 11 file-basis mc.* names (mc.meter~, mc.plugout~, ...) are mono externals that read their own name, and no help box shows their I/O.
- **version_io.json is regenerated wholesale.** It is mined evidence, not curation; the dry-run's +/-/~ counts are the review step.
- **The version layer is max-scope only and warning-only.** gen and rnbo scopes share names with Max objects whose versions and I/O differ.
- **One shared signal-class function.** `outlet_signal_class` lives in db_lookup and is used by the miner, Layer 3 and the replace_box_safe check, so a mined key and a queried key always agree.

## Known Stubs

None.

## Threat Flags

None. The new writers, both mining scans and the alias guard are all covered by the plan's threat register (T-mis-01..05).

## Self-Check: PASSED

- FOUND: .claude/max-objects/idioms.json, .claude/max-objects/version_io.json, tests/test_idioms.py, tests/test_objectfile_aliases.py, tests/test_version_io.py
- FOUND commits: 5ed4d5b3, 431929f7, 1f87d519, 2fb31736, 549400aa
