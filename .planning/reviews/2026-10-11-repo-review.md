# Full Repo Review — 2026-10-11

Scope: everything in the repo — `src/maxpat/**` (19.5k LOC), tests (31k LOC), tools/scripts/installer/CI, the object DB, CLAUDE.md/README/TECHNICAL, skills/commands, and the 31 patch projects.

Method: 8 parallel reviewers, one per area:
- core API
- validation and DB lookup
- layout and contrast
- critics and codegen
- tools, installer and dsp_sim
- docs and skills
- git-history failure mining (2,533 commits, 390 `versions.json` entries)
- object-DB integrity

Ground truth was the installed Max 9.2 bundle: refpages keyed by `<c74object name>`, plus 2,114 help patches that MAX itself saved (11,033 `newobj` boxes).

Legend:
- **✓** = re-verified by the lead reviewer in this session.
- **R** = reproduced by a sub-reviewer with a scratch script.
- **L** = from reading the code (file:line given).

Nothing in the repo was modified apart from this file.

## 0. Baseline and what is solid

- `pytest` on `main` (dbf0d6b): **2309 passed, 3 failed**, 2 xfailed, 1 xpassed.
  - The 3 failures are `test_review_patch_no_blockers` for minitaur, physics-composition and timestretch.
  - All three are critic false positives (§1E), committed after the 2026-09-21 allowlist update.
- Round-trip is solid. All 69 repo patch files (56 .maxpat, 12 .gendsp, 1 .maxhelp) round-trip `from_dict`→`to_dict` with zero structural differences, including after an add-box + add-connection edit. No id collisions. (R)
- `review_patch` is deterministic and does not mutate its input. (R)
- The DB loads in ~24 ms and ~14 MB. (R)
- Alias targets, relationship names and PD-equivalent names all resolve. (R)
- `package_info.json` counts match. (R)
- All 12 Max 9.2 objects are tagged `min_version 9.2`. (R)
- Per-domain counts in CLAUDE.md are accurate. (R)
- dsp_sim tests pass (73). (R)

**Core diagnosis:** the safety net fails in both directions.
- **Destructive false positives:** it silently deletes valid cords and blocks correct idioms.
- **Missed real defects:**
  - nothing runs at save time;
  - nothing looks inside subpatchers (41% of committed boxes are nested);
  - several detectors are dead;
  - most documented rules are prose-only.

---

## 1. Bugs

### 1A. Safety net: validation, save and CI

| ID | Sev | Where | Finding | Evidence | Fix |
|---|---|---|---|---|---|
| A1 | HIGH ✓ | `validation.py:548-644`, `audit/overrides.py:172,279-292`, `overrides.json` (`tapin~` :3222, `pfft~` :2738, `poly~` :2899, `in` :2317) | `validate_patch` **deletes valid cords** as "auto-fixed" errors, which don't count as blocking. | Stripped:<br>• `tapin~ 1000→tapout~ 500` ("status outlet → signal inlet")<br>• `filtergraph~→biquad~` in0 (the biquad~ refpage documents the 5-coefficient list there)<br>• `cycle~→poly~` / `pfft~` / `rnbo~`<br>• `cycle~→p` in real patches<br>• `matrix~ 2 4` outlet 2→`dac~`<br>• `play~ buf 2` outlet 1→`dac~`<br>• `cycle~`→`sfrecord~ 2` / `vst~` / `pitchshift~` / `fffb~ 4` / `mc.snapshot~` (the audit tool wrote `signal:false` inlets for ~26 MSP/MC objects)<br>• `in 1`→`peek~`<br>3 committed patches lose a working cord on validation:<br>• mixer-strip obj-15→obj-37<br>• terrain-voice obj-16→obj-60 (the cord lost in terrain v0.16.0)<br>• scala-synth-voice obj-1→obj-3 (v1.0.0 is user-confirmed working) | • Container boxes (`p`, `patcher`, `bpatcher`, `poly~`, `mc.poly~`, `pfft~`, `rnbo~`) accept anything.<br>• Role mismatches become warnings, never strips.<br>• Repair the `signal:false` overrides and forbid signal→control flips in a test.<br>• Never auto-remove a pair listed in `relationships.json`. |
| A2 | HIGH ✓ | `validation.py:142,605-607`; `max-patch-agent/SKILL.md:316-320`; `max-dsp-agent/SKILL.md:273,277` | Validation behaves differently for the two input types. **Patcher input:** reports "connection removed" but removes nothing and isn't blocking. **Dict input:** strips cords in place. The skills validate `patch_dict` and then save that same dict. | ✓ The Patcher still has 1 line after "-- connection removed", and `has_blocking_errors=False`. | Make validation pure: return proposed removals and add an explicit `apply_fixes()`. Skills should validate a `deepcopy`. |
| A3 | HIGH ✓ | `hooks.py:132-167` (`save_patch_roundtrip`), `hooks.py:206-240` (`write_gendsp`) | **Saves never run validation or the critics.** `PatchValidationError` / `PatchGenerationError` are never raised in `src/`. The hooks.py docstring ("FRM-05: auto hook on file write triggers validation"), README and TECHNICAL:462 say otherwise. | Unallowlisted blockers came in via auto-commits:<br>• `385d85a` minitaur (0→3)<br>• `5b09fe4` / `190ab52` physics (0→1→2)<br>• `de0162e` timestretch (0→1) | On save: `validate_patch(deepcopy)` + `review_patch`. Refuse blockers *not present in `original_text`*; offer `force=True`. |
| A4 | HIGH ✓ | `.github/workflows/release.yml` (the only workflow) | **No CI test job.** Tags publish without running pytest, and the suite is red today. | Read. | Add a pytest workflow on push/PR; gate release on it. |
| A5 | HIGH ✓ | `project.py:362` (`auto_commit_patch`), `hooks.py:40-51` | **Auto-commit commits the whole git index**: `git commit -m msg` with no pathspec. It also has these problems:<br>• `git add` return codes are unchecked;<br>• `except Exception: pass` hides failures;<br>• it only commits paths containing a `patches/` component (anything else silently never commits);<br>• it returns `None` either way. | R (throwaway repo): a staged `other.txt` landed in "patch(foo): save foo.maxpat"; a second no-op save committed only `wip.txt`. | `git commit -m msg -- <paths>`; repo root via `git rev-parse --show-toplevel`; check return codes; return the hash or raise. |
| A6 | HIGH | `hooks.py:149-164` | **Lost update:** `save_patch_roundtrip` never re-reads the file. A MAX save between `read_patch` and the agent's save is overwritten. MAX saves are never committed, so it is unrecoverable. | R: read → simulated MAX save → agent edit → save; the user's MAX edit survived = False, nothing raised. | Compare the disk file with `original_text` (or a hash) before writing; on mismatch raise, or merge per box id. |
| A7 | HIGH ✓ | All of validation Layers 2–5; all critics except layout; layout critic + contrast; `analyze()`; `testing.py` checklist | **Nothing recurses into subpatchers** (`p`, bpatcher, embedded poly~). 41% of committed boxes and 42% of non-gen cords are nested. | ✓ An `osc~` (PD object) plus an out-of-range cord inside a `p` → 0 findings (top-level `osc~` is caught). R: the same content gives 2 blockers at top level and `[]` inside `p synth`. | Shared `iter_patchers()` yielding (path, patcher, context ∈ {max, gen, rnbo, poly}); tag findings with the path. |
| A8 | MED | `tests/test_integration_patches.py:97-99` | The mixer-strip xfail reason no longer reproduces; the test now fails on an unallowlisted fan-out, which the non-strict xfail hides. Separately, `test_validate_patch_no_errors` skips auto-fixed results, so the A1 cord strips are invisible to CI. | R | `xfail(strict=True)`; count auto-fixed removals as failures in the integration test. |

### 1B. The edit path destroys user work

| ID | Sev | Where | Finding | Evidence | Fix |
|---|---|---|---|---|---|
| B1 | HIGH ✓ | `hooks.py:100-103` (`_finalize_midpoints_recursive`) | `finalize_patch(is_new=False)` **clears every cord's midpoints recursively** and regenerates them. Six skills mandate it on every edit (patch:326, dsp:283, ui:222, js:113, rnbo:99, ext:82). The README promises /max-iterate preserves "manual changes you've made in MAX". | ✓ Code. R: ji-harmonizer 218/218, terrain-synth 328/328, dbap-source 109/109 cords rerouted; 2,467/2,489 across the repo. `_generate_midpoints` already skips routed cords; the clearing loop defeats it. | Drop the clearing loop, or clear only cords touching added or moved boxes. |
| B2 | HIGH ✓ | `patcher.py:596-625` | `modify_box(args=…)` recomputes I/O from the DB for **content-defined** boxes (`p`, `gen~`, `mc.gen~`, `js`, `poly~`, `jit.gen`, some `expr`) and drops cords **even when the args are unchanged**. | ✓ FDNVerb `gen~ FDNverb` with the same args: I/O 2/2→2/1, cords 41→40. R: `p articulation` 2/2→1/1 (21→19 cords); 114 boxes / 427 cords exposed repo-wide. | Take I/O from inner ports (embedded patcher), keep existing counts for js/node.script/poly~; recompute only for DB `variable_io` objects. |
| B3 | MED ✓ | `patcher.py:590-593` | `modify_box(args=…)` on message/comment boxes prefixes the maxclass into the text. | ✓ `'message read drums.wav'`, `'comment New label'`; git history has a fix for exactly this (28fb0df: 17 message boxes). | Text = `" ".join(args)` for message/comment; skip the I/O recompute. |
| B4 | MED | `patcher.py:661-711` | `replace_box` / `replace_box_safe` drop the box's identity: varname, presentation rect, z-order (new box goes to the end), colours, parameter blocks. This breaks Rule #9 and pattr/param_connect/getnamed bindings. `rewire="auto"` gives up whenever I/O counts differ (`pack 0 0`→`pack 0 0 0` orphans every cord). Rewired cords lose midpoints, order and colour. | R | Carry over a whitelist of attributes; keep the list index; rewire every orphan whose indices are still in range. |
| B5 | MED | `patcher.py:271-307, 81-96, 1162-1196` | On loaded boxes, **most edits are silently dropped at save**: `extra_attrs` (including public `set_object_bgcolor` and `populate_assistance_comments`), `fontsize`/`fontname`, and cord `order`/`hidden`. | R: bgcolor never reaches disk; fontsize 20 saves as 12; assistance comment in memory but `None` on disk. | Track changed fields and write them back (see §2 S4). |
| B6 | MED | `patcher.py:1259,1303` | `from_dict` shares nested lists with the caller's dict, so edits mutate the "original". | R: `modify_box(position=…)` changed the input dict's rect. | Deepcopy each box/line dict once on load. |
| B7 | MED | `patcher.py` (add/remove inlet in a loaded subpatcher) | The parent's `numinlets`/`numoutlets` aren't resynced, so the new port can't be connected. | R: bassoon `p articulation` went to 3 inner inlets, parent still 2, connect raises. | `sync_port_counts()` called from add/remove of inlet/outlet boxes. |
| B8 | MED | `hooks.py:206-240` | `write_gendsp` rebuilds the .gendsp from code each time; edits made in MAX's gen editor are lost (the Rule #5 "generator" problem for .gendsp). | L | If the file exists: load it, replace only the codebox `code`, sync ports, save via round-trip. |
| B9 | MED | `hooks.py:157` | The first framework save after a MAX save **reformats the whole file**: `json.dumps` puts one array element per line, while MAX writes short arrays inline. | R: a no-op save grows FDNVerb.maxhelp 946→1,762 lines and sample-layers 1,343→2,415. | A MAX-style JSON writer (short arrays inline) so diffs show only real changes. |
| B10 | MED | `builders.py:66-77`, `patcher.py:900-927` | `add_box` always snaps to the 15px grid and treats any gap under 10px as a collision. | R: `meter~` requested 5px right of `gain~` (the CLAUDE.md companion rule) lands 155px below; `cycle~` (37,52) lands at (30,45). | Nudge only on real overlap; companion-aware padding; report when a box was moved. |
| B11 | MED | `patches/.active-project.json`, `project.py:96-136` | The active-project pointer is **tracked in git and shared by all instances** (39 commits touch it; it's modified right now). `/max-switch` in one instance retargets another's `/max-iterate`. The name isn't validated, and malformed JSON crashes. | R/L | Untrack and gitignore it; use a per-session pointer or pass the project explicitly. |

### 1C. Object DB: wrong data that makes generated patches wrong

| ID | Sev | Where | Finding | Evidence | Fix |
|---|---|---|---|---|---|
| C1 | HIGH ✓ | `db_lookup.py:618-646, 802-806`; `overrides.json` `variable_io_rules` | **Argument-dependent I/O is wrong for everyday objects.** 119 names disagree with MAX-saved help boxes at least once; 62 arg-dependent objects are miscounted (45 with no rule, 17 with a wrong rule). | ✓ Bare `unpack`→(1,0) (MAX (1,2), 57 boxes); `pack`→(0,1) (MAX (2,1)); `sel 0`→(1,2) (MAX (2,2), 132 boxes); `route a b`→(1,3) (MAX (3,3)); `expr $f1*$f2`→1 inlet (MAX 2), and `expr $i1 + $i2 + $i3`→5 inlets (whitespace-token counting); `gate~ 3`→(2,1) (MAX (2,3)); `unjoin 3`→3 outlets (MAX 4); `r foo`→(1,1) (MAX (0,1), 473 boxes). Also wrong:<br>• bare `switch` (MAX 3 inlets), `b` (MAX 2 outlets)<br>• `matrix~ N M` (+dump outlet), `play~ buf N` (+bang outlet), `groove~ buf N`, `tapout~` taps, `record~ N`<br>• `bucket N`, `buddy N`, `notein/ctlin N`, `jit.unpack N`, `mc.route N`<br>• `if … out2`, `sprintf`, `pipe`<br>• quotes not respected: `t "LCD Text / Icon (Inactive)"`→5 outlets | Use `arg_count_or_default` for pack/unpack/t/pak/combine/expr; `arg_count+1` inlets for route/select/routepass; count the highest `$`-index for expr/vexpr/if; quote-aware tokenizer; add rules for the 45. Regression-test against help boxes (§5). |
| C2 | HIGH ✓ | `overrides.json` | **Overrides contradict both refpages and MAX's own saved files.** CLAUDE.md:57 asserts the wrong spectroscope~ value. Most of these came from commit 5b792f7 and the help-audit analyzer, which rates HIGH confidence from a single instance (`audit/analyzer.py:71,269,278`). | ✓ `coll` DB (2,4) vs MAX (1,4) in 48/48 boxes. ✓ `spectroscope~` DB (2,0) vs MAX (2,1) in 24/24 boxes. R: `index~` outlets cut 2→1 (MAX 2, 11/11); `poke~` cut 1→0 (MAX 1, 6/6); `vst~` 4 vs 8 outlets (12/12); `retune~` 3 vs 5; `thispoly~` 2 vs 3; `live.scope~` 0 vs 1 outlet; `playlist~` 3 vs 5; `gridmeter~` 0 vs 1; `bucket` 2 vs 1; `mousestate` 5 vs 10; `live.adsr~` (4,1) vs (11,3); `live.adsrui` (1,1) vs (10,10); `dict.view` (1,1) vs (1,0); `jit.polymovie`, `jit.line`, `mxj~`, `mira.motion` (bad fallback guesses in `tools/extract_pkg_io.py:69-166`, which never searches the app bundle's help dirs). | Correct the overrides and CLAUDE.md:57; require ≥3 instances for HIGH; re-audit against 9.2. |
| C3 | HIGH ✓ | `db_lookup.py:136-159` | **About 360 RNBO-only / Gen-only names pass existence checks at Max top level**; only `floor~` carries `domain_restricted`. You already hit this: "expr~: No such object" (2026-10-04, tremolo-am-ringmod). | ✓ `expr~`, `wrap~`, `counter~`, `dcblock~`, `phasor`, `history`, `latch`, `clamp`, `mstosamps` all add and validate with zero errors. R: none of the ~364 has a core refpage, object mapping, external, abstraction or help use. | Imply a restriction for any entry sourced only from `rnbo/` or `gen/`; error on a top-level box resolving there. |
| C4 | HIGH ✓ | `maxclass_map.py:39,53-61` | **Non-UI `live.*` objects and `patcher` are listed as UI maxclasses**, so they serialize with no `text` and MAX can't load them. Affected: live.thisdevice, live.path, live.object, live.observer, live.map, live.routing, live.push, live.miditool.in/out, live.remote~, live.param~, live.modulate~, live.banks, live.colors. This breaks any LOM device; the maxclass validator can't catch it because the names are whitelisted. | ✓ `add_box("live.thisdevice")` → `{"maxclass":"live.thisdevice","text":null}`; `add_box("p",["foo"])` → `{"maxclass":"patcher","text":null}`. R: across 3,160 bundled patches MAX always writes these as `newobj` (live.thisdevice 107–108×, live.path 112×, live.object 99×, `p` 6,764×). | Remove them from the UI set; make `add_box("p")` raise and point to `add_subpatcher`. |
| C5 | MED | `maxclass_map.py` | ~41–44 **real UI maxclasses are missing**, so `add_box` writes them as plain objects and the validator raises "Wrong maxclass" on MAX-saved patches (39 blocking errors on top-level help patches). | R: jit.fpsgui (139–177), jit.playlist (156), jit.pworld (129), plot~ (100–124), mc.ezdac~ (71), mc.live.gain~ (69), markup (55), v8ui (20–27), live.adsrui (24), mc.number~ (21), v8.codebox (15–17), itable (13), multirange, gridmeter~, node.codebox, text.codebox, zplane~, progress. | Generate the UI set from a bundle survey inside `sync_max_bundle.py`. |
| C6 | MED ✓ | `db_lookup.py:164-172` | **Overrides replace whole top-level keys, not a deep merge**, although the code comment and CLAUDE.md say deep-merge. | ✓ Code: `self._objects[name][key] = value`. R: 417 port descriptions on 171 objects become "Control output" (uzi loses "Done banging", `line~` loses "Ramp Time"); 192 `hot` flags dropped; 46 overrides shrink a port array. | Merge per port (keep base description/type unless set); this would also shrink the 364 KB overrides.json. |
| C7 | MED | `db_lookup.py:167` | Overrides keyed by an alias (`r`, `del`, `v`) are silently ignored, and their "No base domain entry" notes are false. The `r` override holds the correct 0-inlet fact. | R | Canonicalize override keys through aliases; fail fast on unknown keys. |
| C8 | HIGH (✓ for mc) | DB extraction | **Inherited group messages and attributes are never extracted.**<br>• 162/163 MC wrappers lack the 53 wrapper messages (`applyvalues`, `setvalue`, `replicatevalues`…).<br>• 198 Jitter objects lack the shared Jitter messages.<br>• 135 GL objects lack ~61 OB3D attributes (only `alpha_mode` landed).<br>• `thispatcher`'s scripting messages exist only in the user guide.<br>Rule #1 therefore forbids your user-confirmed `applyvalues` form (ji-harmonizer, barnett-dbap). | ✓ `mc.cycle~` has 6 messages, no `applyvalues`/`setvalue`. | Import the group pages (mcwrapper-group, jit group, OB3D) in the sync tool, or merge them on the fly in `messages(name)`. Don't enforce message names until this lands. |
| C9 | MED | DB signal roles | 16 objects' outlet signal-vs-control roles contradict what MAX writes. Root cause in the audit tool: `_build_inlet_array` hard-codes `signal: False`. | R: `mc.route` 0/1 and `mc.live.gain~` 1 are marked audio (MAX: control); `gen` 0 audio (MAX: float); `mc.adsr~` 0/1, `sfrecord~` 0 and `pitchshift~` 0/1 marked status (MAX: signal). | Copy `signal`/`type` from the base entry by index; never downgrade. |
| C10 | MED | `package_critic.py:478`; skills (patch:205-208, dsp:118, lifecycle:60-66) | The package gate checks `extracted`, not `installed`. Odot, IRCAM Spat, ml-lib, Cage and RTK are `installed=False, extracted=True` (119 objects), so `rtk.seq~` passes with only a warning → "No such object". `bach.llll2list` / `bach.list2llll` still pass existence checks (`verified_installed:false` only warns). | R | Gate on `installed`; make `exists()` respect `verified_installed:false`. |
| C11 | LOW | `pd-blocklist.json`; `list.*` entries | The PD blocklist lists `clip~` (a real MSP object) and says MAX has `wrap~` (it doesn't). Max's 31 `list.*` objects (which map to `zl.*`) resolve to RNBO I/O; e.g. `list.len` is (1,1) vs MAX (2,2). | R | Fix both entries; import aliases from `objectfile` lines (§5). |
| C12 | LOW | DB | `pan`/`pan~` rules are ignored (no `variable_io: true`); `o.route` has the flag but no rule. 354 objects carry OBJARG/TEXT_HERE placeholder arguments (336 copied from the refpage itself); 302 have an empty port type. | R | Curate; re-extraction would copy the placeholders again. |

### 1D. Max for Live (never opened in MAX: no `.amxd` in `patches/`)

| ID | Sev | Where | Finding | Evidence | Fix |
|---|---|---|---|---|---|
| D1 | HIGH ✓ | `m4l_constants.py:13-51`; `builders.py:1078-1080`; `m4l_polish.py:168` | **`ParamType` has INT and FLOAT swapped, and `ModMode` is off by one** (it has no "None"). As a result:<br>• `add_m4l_gen_synth` writes 0–1 dials as type 1 = Int (likely quantized to 0/1 in Live);<br>• it writes modmode 3, which MAX reads as Additive;<br>• the m4l_polish default "FLOAT" also writes Int.<br>The tests lock in the wrong values. | ✓ The `parameters.maxref.xml` order is Float, Int, Enum, Blob and None, Unipolar, Bipolar, Additive, Absolute. ✓ The kicksynth-m4l ground truth (408cdf8) stores float dials (0–1, 50–1000 Hz) as type 0. R: shipped live.gain~ is type 0 in 447/448; modmode 4 occurs 34× and the clip-mod range appears only with mode 4. | FLOAT=0, INT=1, ENUM=2, BLOB=3; NONE=0…ABSOLUTE=4; test against literal values from the bundle. |
| D2 | HIGH ✓ | `m4l_polish.py:178-211` | **`ensure_m4l_prefixes` breaks references.** It rewrites the second token of any text box (including comments and messages) and ignores `s`/`r` and all consumers of a renamed name. Two skills recommend `polish_m4l_device`. | ✓ `send level`→`send ---level` but `r level` is unchanged; `buffer~ grains`→`buffer~ ---grains` but `play~ grains 2` is unchanged; the comment "send the dry signal"→"send ---the dry signal". | Touch only `newobj` boxes and rename consistently across all references, or report the names instead of rewriting. |
| D3 | MED | `builders.py:953, 1040-1049` | `add_gen` with 0 inputs gives the gen~ 0 inlets (MAX always gives ≥1), so no `param $1` message can be wired, including on the `add_m4l_gen_synth` skeleton. That skeleton wires only `plugout~` inlet 0 (left channel only) and passes an obsolete channel argument `1`. | R: `ValueError … gen~ which has 0 inlet(s)`. | `max(1, num_inputs)` inlets; wire both plugout~ inlets; drop the `1`. |
| D4 | MED ✓ | `critics/__init__.py` | `review_m4l` is **never called** by `review_patch`. Called directly, it fails the framework's own builder (it demands midiin/midiout for an instrument) and misses `live.gain~→plugout~` (line 106 only matches `gain~`). | ✓ grep shows no call. R | Call it when plugin~/plugout~/live.thisdevice is present; flag gain~/live.gain~/ezdac~ on any path to plugout~. |
| D5 | MED | `m4l_polish.py:120-171, 359-378` | Push banks are written to `_parameter_banks` (MAX uses `patcher.parameters.parameterbanks`); `parameter_enable` is added to live.comment/live.line/live.meter~, which aren't parameters; `_LIVE_NO_PARAM` is incomplete. | R | Fix the key; DB-driven parameter-capable set. |

### 1E. Critics: noise drowns the signal, and some detectors are dead

Corpus run: `review_patch` on 55 committed patches produced 1,768 findings (1,230 from the layout critic). Of the other 538, **≈90% are noise.**

| ID | Sev | Where | Finding | Evidence | Fix |
|---|---|---|---|---|---|
| E1 | HIGH ✓ | `structure_critic.py:117-149` | **Fan-out blocker false positives cause all 3 red tests.** In total 37–38 of the 73 fan-out blockers are false positives. False negatives too: a trigger outlet feeding 2 destinations is skipped (line 126), and MSP objects' control outlets are skipped by `~`-name (line 130). | ✓ timestretch: `preset` outlet 2 is "Connect to Objects to Exclude From a Preset" (refpage), a membership cord where a trigger can't be inserted. ✓ minitaur: `expr`/`scale` → display `flonum` + `send`. physics: see E4. | Skip display-only sinks and preset membership outlets 0/2/4; use outlettype, not the name; **blocker only when downstream paths reconverge** (17 real cases), otherwise warn. |
| E2 | HIGH ✓ | `dsp_critic.py:261-321` | The **"Control-rate to signal-rate" warning is ~100% noise** (399 hits) and its advice is harmful. | ✓ Fires on the CLAUDE.md-mandated `cutoff $1`→gen~ inlet 0 and on `number→sig~` (the fix it suggests). R: a strict filter on DB inlet/message data removes 387/399; the rest are command messages. | Delete it, or restrict it to signal-only inlets with no numeric methods, at note severity. |
| E3 | HIGH ✓ | `dsp_critic.py:110`; `critics/__init__.py:28-36` | **Dead detectors:**<br>• The gen~ code-vs-box I/O blocker requires `maxclass == "gen~"` (MAX and `add_gen` write `newobj`); only test fixtures use maxclass gen~.<br>• `_has_rnbo_boxes` requires `maxclass == "rnbo~"`; all 663 MAX-authored rnbo~ boxes are `newobj`. | ✓ Code. R: a gen~ box with 1/1 I/O and code using in3/out2 → `[]`. | Detect by name (`gen~`, `mc.gen~`, `rnbo~`); add newobj fixtures. |
| E4 | MED | `package_critic.py:306-365` | The Bach-llll blocker fires on any non-bach source into an inlet described as llll, including command messages, attrui, loadmess, receive. | R: 3/3 FPs in physics-composition (`addchord [ $1 [ $2 $3 $4 ] ]`, `domain $1 $2`, `receive roll-clear`); 1,882 blockers on bach's own help patches. | Exempt command sources; note severity. The real trap runs the other way: bach → non-bach without `@out t`. |
| E5 | MED | `structure_critic.py:193-245` | 48/63 hot/cold warnings are noise: p/bpatcher/js targets, a multi-outlet source MAX already orders right-to-left, and independent event sources. Meanwhile the real RCC v0.0.7 shape (hot fed via trigger) is skipped. | R | Warn only when hot and cold inputs share an upstream ancestor. |
| E6 | MED | `dsp_critic.py:30-43, 339, 351-366, 444, 468-509`; `validation.py:36,40` | **Gain safety is judged by object name and mis-parses messages.**<br>• `0, 0.8 2000` → line~ → `*~` is a blocker: the ramp time is read as a target.<br>• `64` → `* 0.01` → `*~` reports "via line~" with no line~.<br>• flonum with min 0 / max 1 → blocker.<br>• `scale 0 127 0. 4.` (4× gain) is missed, and only `*~` inlet 1 is traced.<br>• `live.gain~` isn't a gain stage; `mc.dac~` and `plugout~` aren't terminals, so every M4L patch gets a false "Unterminated".<br>• `gain~` itself is never checked (and CLAUDE.md's rule for it is wrong, §1J). | R | Split on commas; parse pairs only for messages feeding line~; read box min/max and scale/clip args; trace both inlets; DB-driven gain/terminal sets. Longer term: value-range propagation (§6). |
| E7 | MED | `aesthetics.py:200-326`; `layout_critic.py:387-389` | **Contrast is not theme-aware.** The critic assumes black text when `textcolor` is missing (legacy maxcolors defaults). Max 9's default theme is text 0.85 on canvas 0.235 (box fill 0.172). For overlapping panels it uses the LAST containing panel (MAX shows the FIRST) and treats transparent `[0,0,0,0]` fills as opaque black. | R: 247/296 low-contrast warnings are false (the known false positive in `feedback_contrast_critic_default_text` is still present), while real problems are missed: amplitude-follower obj-16/20/22/23 at 2.3:1, kicksynth obj-154 at 1.24:1. | Model the theme defaults; use the first non-background containing panel; skip low-alpha fills; treat a box's own fill as its background. |
| E8 | MED | `rnbo_critic.py:23,113-127`; `rnbo.py:217,273-276,385-393` | **RNBO critic:**<br>• The positional `param freq 440` name isn't parsed (only `@name`), so duplicate checks never fire.<br>• A missing `in~` is a blocker, though generator patches legitimately have none (MAX's own rnbo_triangle~ help fails).<br>**RNBO builder** (never opened in MAX) differs from all 663 MAX-authored rnbo~ boxes:<br>• maxclass `rnbo~` with no text;<br>• `classnamespace "box"` (MAX: `"rnbo"`);<br>• `audio_ins+1` inlets;<br>• `@initial` isn't a param option. | R | Parse the positional name; missing `in~` → note; generate MAX's shape; add a golden fixture from a MAX-saved rnbo~ patch. |

### 1F. Layout for new patches

| ID | Sev | Where | Finding | Evidence | Fix |
|---|---|---|---|---|---|
| F1 | HIGH ✓ | `layout.py:61, 765-779` | The `status`-role readout is placed **exactly on top of its source** with `ignoreclick=1` at z-index 0, hiding the source object. 97 DB outlets carry the `status` role. | ✓ `dspstate~`→`flonum`: both at [30,30,79,22], flonum index 0. | Remove the status overlay, or only overlay UI→readout pairs. |
| F2 | HIGH | `layout.py:592-606` | UI controls feeding the same object are **stacked at identical coordinates**. | R: two flonums and a dial into `pack 0. 0. 0.` all land at (30,0). | Row above the target, ordered by inlet, with gutters. |
| F3 | HIGH | `hooks.py:82-83`; `layout.py:183-187` | `finalize_patch(is_new=True)` picks text colours **before** layout. Layout then moves panels, headers and untargeted labels into a "disconnected" column, so panels no longer sit behind their chains and labels land on the wrong surface. Matches memory's barnett-dbap "3000 px right" report. | R: panel (12,-8)→(150,30) while its chain stays at x=30; a label moved onto a light panel → 1.40:1. | Run contrast after layout; give decorations member ids so they move with their boxes. |
| F4 | HIGH | `layout.py:212-216` | Embedded bpatcher faces are re-laid out; the `_skip_auto_layout` opt-out is never set. | R: a dial inside a 120×80 face moves to (30,0); its label moves to (105,30), outside the view. | Skip bpatcher inner patchers by default. |
| F5 | MED | `layout.py:82-99, 1313-1323, 482, 748-761`; `layout_critic.py:22,139-179`; `sizing.py:207-219` | More layout problems:<br>• No size guard on `apply_layout` (ji-harmonizer 1,968→10,203 px wide).<br>• The presentation auto-grid offsets by each box's own width, so mixed widths overlap.<br>• Inlet alignment uses pre-layout y.<br>• Companions reserve no width.<br>• The overlap critic misses rendered-width overlaps (comments excluded; `len*8+25` ignored; 7 px/char vs MAX's ~5.6) and floods 169/359 noise warnings (64 from the framework's own overlay-readout recipe). | R | Width cap / refuse MAX-saved patches unless forced; one shared `rendered_rect()` for layout and critic. |
| F6 | LOW | `aesthetics.py:25-28, 266-268, 448-451` | With only 2 candidate colours, a mid-grey surface can't reach 4.5:1 (it picks 3.13:1 where black would give 5.28). Accent colours that already pass are flattened to grey. A list-wrapped fill dict (as in MAX's `generic_editor.maxpat`) crashes the critic. | R | Keep any colour that already passes; add black/white candidates; handle list-wrapped fills. |
| F7 | LOW | `builders.py:383-414` | `add_overlay_readout` ignores presentation (Rule #6/#9 gap), and a `comment` readout shows the literal text "comment". | R | Copy the target's presentation rect; empty text. |

### 1G. Code generation and code validators

| ID | Sev | Where | Finding | Evidence | Fix |
|---|---|---|---|---|---|
| G1 | MED | `codegen.py:94-166` (auto-applied by `add_gen`) | `reorder_genexpr_declarations` works line by line. It moves declarations out of `/* */` comments, so commented-out code becomes live, and it splits a multi-line `Param …(\n…);` into a syntax error. | R | Strip comments, split statements on `;`, move whole statements. |
| G2 | MED | `codegen.py:37-38` | `parse_genexpr_io` counts `inN`/`outN` inside comments. | R: `"// mix in4 and out3"` → (4,3) ports. | Strip comments first. |
| G3 | MED | `code_validation.py:203-232`; `validation.py:933-936` | The GenExpr validator uses the wrong namespace: it **rejects Gen's real `clip()`** (documented; BEAP codeboxes use it) and user-defined functions, but **accepts Max-only `metro(`/`coll(`/`route(`**. Layer 5 skips `mc.gen~`, nested gen~, `jit.gen`/`jit.pix`; `validate_code_file` checks only the first codebox in a .gendsp (`hooks.py:321`). | R: `out1 = clip(in1,-1,1);` → blocking. | Check against the gen domain only; support function definitions; walk all codeboxes. |
| G4 | MED | `rnbo.py:109-133` | `parse_genexpr_params` mis-parses Params. | R: `Param freq(440, min=20);` → max 1.0 < min; `Param g(0.5) ;` dropped; `samplerate*0.25` raises. | Regex `Param\s+(\w+)\s*\(([^)]*)\)\s*;`; missing bounds → None. |
| G5 | MED | `ext_templates.py:73, 139-166` | The Min-DevKit DSP template only compiles with exactly 1 input (`return { input };` vs `input1…`), and `foo~` is pasted in as a C++ class name. `ext_critic` misreports it. | R | `input1…` / zeros per output; class name `foo_tilde`. |
| G6 | LOW | `codegen.py:318-335, 396-402` | `generate_n4m_script` emits `getDict_my-dict` (a SyntaxError in node); `generate_js_script` emits `anything(msg)` (wrong, §1J). | R | Sanitize identifiers; use `messagename` + `arrayfromargs`. |
| G7 | LOW | `externals.py:304-314` | `setup_min_devkit` runs `git submodule add` inside the framework repo. | L | Clone into the external's dir; gitignore it. |
| G8 | LOW | `validation.py:1381, 468-473`; `code_validation` (`validate_js`) | Smaller validator defects. | R: a newobj with empty text crashes all of `validate_patch` (IndexError); duplicate box ids go undetected (only a confusing out-of-bounds auto-fix); the `validate_js` regex matches comments (`// inlets = 2`). | Quote-aware tokenizer; Layer-1 duplicate-id error. |
| G9 | MED | `graph.py:49-53, 180, 197-254` | Graph traversal is imprecise. Crossing into a subpatcher enqueues every inner inlet; `signal_only` filters by the `~` name suffix (`signal_path(cycle~)` through `p fx` → `[cycle~]`); `downstream()` stops at `send~` (no send/receive bridging); adjacency is rebuilt per node. | R | Port-exact crossing, s/r bridging, outlettype-based signal test, adjacency built once. |
| G10 | MED | `testing.py:159-185` | The /max-test checklist takes the first word of every box, including comments and messages, and never recurses. | R: `dac~` inside `p synth` plus the comment "metro speed and gen~ notes" → only a "Metro Timing" test. | Object boxes only; recurse. |

### 1H. DSP pre-flight (`dsp_sim`)

| ID | Sev | Where | Finding | Evidence | Fix |
|---|---|---|---|---|---|
| H1 | HIGH ✓ | `dsp_sim/measure.py:109-150` (`measure_fundamental`) | **The pitch detector fails in the bassoon's register and on harmonic-rich waveforms.** | ✓ Sines at 58.27 / 70 Hz → **4009.09 Hz**; saws at 220 / 440 Hz → **109.99 Hz** (octave errors). Low B♭1 = 58.27 Hz. | Normalised ACF or YIN; first peak >0.9·max after the first zero crossing; regression tests 50–1000 Hz on sine/saw/pulse. |
| H2 | HIGH | `dsp_sim/runner.py:264-268` | A startup transient trips the early runaway exit, and the gate then returns **PASS** having rendered only step 0. | R: a model that runs away ×40 for drive > 0.5 → "pass, all 1 steps within thresholds". | Runaway check on the post-settle slice; early exit → runaway/incomplete, never pass. |
| H3 | HIGH | `topologies/reed_bore_post_radiation.py:127,152`; `tests/dsp_sim/test_bassoon-model.py` | The "canonical passing" bassoon topology is **stale** versus the shipped `bassoon.gendsp`: no phase-delay compensation, old reed. The test sweeps only post-loop `bell_bright`, so the gate passes without testing the shipped loop. | R: sweeping in-loop `bore_damp` drifts −83→−10 cents (`mode_competition`). | Port the current loop; sweep `bore_damp` and 58–440 Hz. Long term: run the real codebox (§6 F2). |
| H4 | MED | `measure.py:158`; `classifier.py:104`; `runner.py:253` | More false PASS paths:<br>• No-pitch output is scored as in tune (a constant 0.3 passes).<br>• DC defeats the no-oscillation check.<br>• `bore_only` settles to DC and reads 4009 Hz at every setting.<br>• A misspelled sweep param (`bel_brigth`) does nothing → pass. | R | RMS after mean removal; pitch 0 → no_oscillation; topologies declare params and reject unknown ones. |

### 1I. Distribution and DB tooling

| ID | Sev | Where | Finding | Evidence | Fix |
|---|---|---|---|---|---|
| I1 | HIGH ✓ | `install.sh:49`; `installer/bin/create-max-framework.js:61-62`; `project.py:132` | **A fresh install crashes:** the installers write `{"active_project": null}`, but `get_active_project` reads `data["name"]`. `/max-status`/`/max-build` call it before any project exists. | ✓ Code; R: `KeyError: 'name'`. | Don't create the file (missing → None); use `data.get("name")`. |
| I2 | HIGH ✓ | `.release-ignore:10`; `.github/workflows/release.yml:17-18` | **The release tarball is wrong:**<br>• The unanchored `scripts` pattern also strips `.claude/scripts/`, which `validation.py:432-444`, max-lifecycle and `sync_max_bundle.py:100` require.<br>• The tarball is written inside the tree it archives, so it contains a truncated copy of itself.<br>• It ships the tracked maintainer memory file `.claude/projects/-Users-taylorbrook-Dev-MAX/memory/feedback_multiple_choice.md`.<br>• tar's exit 1 is masked. | ✓ The v5.0.0 tarball listing shows `framework.tar.gz` + the memory file, and no `.claude/scripts`. | `git archive --prefix=… HEAD` with `.gitattributes export-ignore`; untrack `.claude/projects/`. |
| I3 | MED | GitHub releases; `create-max-framework.js:10` | The latest release, v5.0.0 (2026-05-01), is 5 months stale (no 9.2 DB, no audit/sync tools). `npx create-max-framework --version` prints 1.0.0 vs package.json 2.3.1. `curl \| bash` pulls an unpinned `latest` with no checksum. | R | Release after the fixes; read the version from package.json; publish checksums. |
| I4 | MED | `.claude/scripts/extract_objects.py:1031-1045, 1095` | **Destructive and unguarded.**<br>• The documented `--package` mode wipes `extraction-log.json` (total_objects 3,445→1, history and sync section gone).<br>• A full run overwrites the core domain files: it drops 25 curated entries (node.script, node.codebox, mc.send~/receive~, M4L.api.*, live.scope~…) and adds 6 documentation pages as objects. | R (scratch copies) | Refuse to overwrite core files without `--force`; merge into the log; reuse the sync tool's doc-page filter. |
| I5 | MED | `audit/merger.py:105-163`; `audit/analyzer.py:71-278` | The merger overwrites manual overrides added after the audit ran (conflicts recomputed too early); writes are non-atomic; it re-sorts 756 keys (noisy diffs). The analyzer rates HIGH confidence from 1 instance and saves argument-specific counts as defaults (bucket, vst~, retune~, coll). | R | Recompute conflicts at merge time; atomic, style-preserving writer; ≥3 instances for HIGH; propose `variable_io` rules. |
| I6 | LOW | `tools/sync_max_bundle.py:191, 201, 1282, 1548, 1618, 1771`; `tools/audit_db.py:537-571` | Smaller tooling defects:<br>• The define regex keeps a trailing `;` on argument-less defines.<br>• Versions are stored as floats ("9.10"→9.1).<br>• Atomic writers leave files at mode 0600.<br>• Multi-file apply isn't transactional.<br>• Only the 104 `define` alias lines are read; the 647 `objectfile` lines are ignored (251 unresolved names, incl. 14 of the 16 "no refpage" names `audit_db` reports). | R | As listed. |

### 1J. Documentation that makes the agent produce broken output

| ID | Sev | Where | Finding | Evidence | Fix |
|---|---|---|---|---|---|
| J1 | HIGH ✓ | CLAUDE.md:273, max-js-agent:41, TECHNICAL:643; `codegen.py:401` | The js handler is documented as `anything(msg, args)`. In MAX the selector is `messagename` and the arguments are `arguments`, so `if (msg == "foo")` never matches. | ✓ CLAUDE.md:273 and codegen. R: the 9.2 user guide; all 9 repo js files use `messagename`. | `function anything() { var a = arrayfromargs(arguments); if (messagename == "foo") … }` |
| J2 | HIGH ✓ | CLAUDE.md:189, TECHNICAL:507 | "Values feeding `*~` **or `gain~`** must be 0.0–1.0". For gain~ this is wrong: the refpage says a float into the left inlet is "Converted to int. Sets the value of the slider" (0–157), so 0.–1. ≈ silence. Memory confirms sending 120. | ✓ gain~.maxref.xml | Restrict the rule to `*~`; document gain~ slider positions. |
| J3 | HIGH | max-patch-agent:39-40, :45; max-dsp-agent:53; patterns/gen/INDEX.md:13; shared-capabilities:107, 123-124; TECHNICAL:313-319, 355, 466; max-iterate.md:87 | **Call forms that raise errors:**<br>• `add_box(Box(name, args, db))`: the third positional arg is `box_id`, and `add_box(Box)` is a TypeError.<br>• `apply_layout(…, layout_options=)`: the kw is `options`.<br>• `insert_into_connection(src, dst, new_box)`: wrong signature.<br>• positional `replace_box(box, name, args)`: `args` is keyword-only.<br>• `save_patch_roundtrip(patcher, path)`: Patcher isn't JSON-serializable.<br>Three docs (shared-capabilities:124, max-iterate.md:87, TECHNICAL:319) say `replace_box` keeps or remaps connections, contradicting Rule #8. | R (`inspect.signature` + calls) | Fix the call forms; point to `replace_box_safe`; add a doc-signature test (§6). |
| J4 | MED ✓ | CLAUDE.md:57 | The spectroscope~ claim is wrong (C2). | ✓ | Fix. |
| J5 | MED ✓ | CLAUDE.md:53, 198 | `expr~` is presented as an MSP object, and the `clip()` rule is mis-scoped: GenExpr has `clip`; the ban applies to `expr`/`vexpr`/`if` only. | ✓ Memory 2026-10-04; refpage | Fix; add "check `lookup()['domain']`" to Rule #1. |
| J6 | MED | CLAUDE.md:189 | `scale 0 127 0. 1.` with integer input args truncates float input (memory minitaur v0.1.9; scale.maxref). Fine for MIDI ints, wrong for flonum/live.dial. | R | Recommend `scale 0. 127. 0. 1.` for float sources. |
| J7 | MED | 6 skills ("Output Protocol (Edited Patches)") | They mandate `finalize_patch(is_new=False)` on every edit (B1). | R | Use `populate_assistance_comments()` only, until B1 is fixed. |
| J8 | MED | dsp:83, 142-211, 218-263; patch BOUNDARIES:16 | Templates use objects and messages not in the DB:<br>• FluCoMa names without `~` (`fluid.dataset`, `fluid.kdtree`…) and a "train" message (help uses `fit`/`predict`);<br>• `reverb~`, `chorus~`, `flanger~`, `phaser~`, `filter~`;<br>• `bp.LFOscillator`, `bp.SVF`, `bp.Steppr` (real modules: `bp.LFO`, `bp.LPF`/`bp.MMF`, `bp.Sequencer`). | R (`lookup` → None) | Fix the templates. |
| J9 | MED | ui-presets.md:127-135 | The dial example fans `scale` out to two destinations without a trigger (critic blocker). | R | Add a `t f f`. |
| J10 | MED | router:24, lifecycle:56,116-117, project-structure:34 | `/max-config` and `/max-version` are referenced ("STOP … run /max-config") but don't exist. 18/31 projects have no config.json. | R | Add the commands, or treat a missing config as core-only. |
| J11 | MED | CLAUDE.md:347-350; TECHNICAL:125-159 | Documents a per-object `io_rule` field no object has; the rules live in overrides.json `variable_io_rules` (39 objects). | R | Fix the docs. |
| J12 | LOW ✓ | patterns/gen (created 2026-03-22, never revisited) | `adsr-envelope.gendsp` (3×) and `noise-generator.gendsp` use `else if` plus `==` in `if`. The library predates every codebox lesson and was never confirmed in MAX. INDEX.md uses the broken `Box(…, db)` form. | ✓ | Re-verify in MAX or rewrite to the proven-safe construct set. |
| J13 | LOW | README.md:21, :230, :233; README patch table; TECHNICAL:494, :540, :549, :669-672 | Stale or wrong:<br>• README says "V8 `js` objects".<br>• Garbled U+FFFD characters at README:230/:233.<br>• The README patch table lists 18 of 31 projects.<br>• TECHNICAL's tables are stale: fan-out/Bach "warning" (actually blocker), a "Companion misalignment" check that doesn't exist, spacing 100/70/120 (code: 20/15/40).<br>• LOC ~18.6k → 19.5k; tests 2,309 → 2,315 (3 failing). | R | Generate the stats in CI. |

---

## 2. Simplification

| # | Proposal | Payoff |
|---|---|---|
| S1 | **One recursive walker + graph:** `iter_patchers()` yields (path, patcher, context) for validation, critics, layout critic, contrast, `analyze()`, testing and audit. It replaces ≥4 walkers, 6 name extractors and ≥6 adjacency rebuilds (`dsp_critic.py` 188/391/418, `validation.py` 741/770, structure/package critics), and fixes the `== "signal"` checks that ignore `multichannelsignal`. | Fixes A7, G9, G10 by construction. |
| S2 | **One quote-aware box-text tokenizer**, replacing `validation.py:232, :965` and `rnbo_validation.py:101`. | Fixes the expr/t quoting bugs and the empty-text crash. |
| S3 | **One Box factory**, `Box.structural(maxclass, text, nin, nout, outlettype, rect, **attrs)`, replacing ~19 hand-built `Box.__new__` blocks (builders ×9, rnbo ×7, panel/step-marker/bpatcher ×3). | These copies have already drifted: that's where the missing `embed: 1` (bpatcher, ✓ `builders.py:774-798`) and the 0-inlet gen~ came from. |
| S4 | **Change tracking on loaded boxes** instead of the `_raw` overlay. | Fixes B5; retires the CLAUDE.md "mutate `box._raw`" rule and the manual `_raw` copies in `patcher.py:627-657` and `aesthetics.py:414`. |
| S5 | **One GenExpr tokenizer/parser** used for I/O detection, declaration reordering, Param extraction and lint, replacing 3 regex copies (codegen, rnbo, code_validation). | Fixes G1–G4; enables §4 lint. |
| S6 | **Per-object I/O resolver callables** plus a help-box oracle test, replacing the string-formula mini-language (`arg_count`, `trailing_outlets`, `_resolve_outlet`). | Fixes C1 and keeps it fixed. |
| S7 | **Merge duplicated rules:** gain staging lives in both validation.py (warning) and dsp_critic.py (blocker) with different name sets (`dsp_critic.py:9` claims otherwise). Give `CriticResult` structured `rule`/`box_ids`/`path` fields; today the integration test regex-parses finding text, and the critic loop's "same finding repeated" escalation can't fire on regenerated ids. | One severity model. |
| S8 | **Per-port override merge.** | Fixes C6/C7; shrinks overrides.json (364 KB). |
| S9 | **Delete dead or broken code:**<br>• `memory.py` (no command/skill uses it; TECHNICAL:288 says so)<br>• `project.py:449-567` `build_examples_catalog` / `_read_project_description` (would delete `examples/<name>`)<br>• `scripts/relayout_patch.py` (crashes on every patch; bypasses Rule #7; does a global relayout)<br>• `.claude/scripts/validate_db.py` (expects a single `packages/objects.json`, reports 1,948 objects)<br>• `.claude/scripts/merge_sources.py`<br>• `tests/fixtures/expected/gen_codebox.maxpat` (unreferenced; keeps `audit_db`'s UI-maxclass check permanently red)<br>• `validation.py:1220-1267` (`_check_genexpr_io_syntax` / `_check_genexpr_delay_usage` never match)<br>• `_skip_auto_layout`, `contrast_text_color`, `is_complex_patch` / `suggest_subpatchers`<br>• unused `MS_*` constants (`defaults.py:21-25`)<br>• the DB `maxclass` field and `verified-objects.json` (no readers); `_uncovered_empty_io`<br>• dsp_sim phase scaffolding<br>• `audit/__init__.py:56-60` ImportError swallow<br>• `add_node_script` (bypasses the DB) | Less surface. |
| S10 | **Release via `git archive`** with export-ignore. | Fixes I2. |
| S11 | **CLAUDE.md 45 KB → ~27 KB** (it's loaded every session):<br>• DB-maintenance internals (:51-59, ~4.5 KB) → `references/db-maintenance.md`<br>• Gen derivations and per-version anecdotes (:214-230, ~5.5 KB) → `references/genexpr-rules.md` (loaded by the DSP agent)<br>• contrast algorithm (~1.6 KB) → UI reference<br>• multislider/z-order recipes (~1.9 KB) → builder docstrings<br>• js/N4M (~3 KB, duplicated in max-js-agent)<br>Skills: the Builder API block is byte-identical in patch-agent:80-182 and ui-agent:83-185 (5.6 KB); the edit protocol appears in 6 skills; the fan-out rule 7×, the `#N` rule 3×. Move each to shared-capabilities once. | ~40% less always-loaded context; one place to fix J7. |
| S12 | **Shared geometry helpers:** `_outlet_x`/`_inlet_x` and `_resolve_patcher_bg` are duplicated (65d754f had to be applied twice), and three hard-coded "UI control" sets disagree (`layout.py:41`, `layout_critic.py:290`, `analysis.py:552`). Also limit `_route_clear_path` to nearby boxes (4.3 s on minitaur). | One fix site. |

---

## 3. Missing information

1. **Severity contract.** Nothing explains validator error/warning/info plus `auto_fixed` versus critic blocker/warning/note, or that **auto_fixed = a cord was deleted**. "Unknown object" (Rule #1) is only a validator warning (`validation.py:284-287`), so hallucinated objects pass the blocking gate. The max-critic skill says to annotate every warning as an in-patch comment (~32 per patch); no patch does, and it shouldn't.
2. **Troubleshooting table: MAX console error → cause → fix.** The strings are scattered across CLAUDE.md:53, :198, :219-224, :244, :333, and several exist only in personal memory: "can't assign to parameter", "already in use", "doesn't understand a", "Wrong Point Size", "failed to compile genpatcher".
3. **Dependencies and platform.** There's no requirements/pyproject: numpy and scipy (dsp_sim) and pytest (the DSP agent's gate) are undeclared. There's no statement that everything assumes macOS (`/Applications/Max.app`, Mach-O checks, `~/Documents/Max 9/Packages`).
4. **Save semantics.** `validate_patch` mutates dict input (A2); docs claim saves are validated (A3); auto-commit needs a `patches/<project>/` path (A5); `finalize_patch(is_new=False)` erases routing (B1); Rule #8 doesn't mention that `replace_box` also drops identity (B4).
5. **Max 9 theme defaults** (text 0.85, canvas 0.235, box fill 0.172 from `default.maxtheme`) aren't documented; the code and critic use the legacy maxcolors defaults (E7). Z-order evidence for overlapping panels (the FIRST containing panel is visible) belongs next to Rule #6.
6. **~40 KB of general MAX knowledge lives only in your personal memory** and never ships to framework users:
   - trigger types are b/i/f/l/s (`t a` outputs literal "a");
   - named objects share one namespace (coll/sflist~);
   - arg-less math and int-arg `scale` truncate floats;
   - bare lists to `mc.*` go to every channel (`applyvalues`/`setvalue`);
   - FluCoMa: read is defer_low (chain dump off the completion message), `conformpath` paths, `list2buf @autosize 0`, kmeans `fitpredict`;
   - poly~ proven forms;
   - `waveform~ setmode 1`;
   - `flonum numdecimalplaces 0` = auto;
   - subpatcher port x-order;
   - validate a deepcopy;
   - no global auto-layout;
   - DB enum values must be checked against maxref/help (e.g. `jit.bfg @basis`).
7. **RNBO and M4L builders have never been opened in MAX** (no `rnbo~` patch, no `.amxd` in `patches/`). Label them experimental until confirmed.
8. **Dangling references.**
   - `feedback_waveguide_loop_phase_comp.md` is cited in 8 files (the dsp_sim runner, classifier and topologies, `tests/dsp_sim/README`, max-dsp-agent) but no longer exists.
   - `feedback_multislider_fetch.md` is cited at patch:125 and ui:128.
   - CLAUDE.md cites a `.planning/` archive that releases exclude.
   - `max-9.2-changes.md` cites the unshipped `tests/test_round_trip.py`.
9. **dsp_sim limits** (only 220 Hz tested; unreliable <90 Hz and on saw-like waves until H1 is fixed).
10. **The after-Max-update procedure** omits that the sync never re-checks existing I/O (drift: vst~, retune~, coll), that package extraction clobbers the log (I4), and that `extract_pkg_io` fallbacks are guesses.
11. **Test evidence.** `test-results/` is empty in 12 of 14 projects; confirmations live only in status.md and memory.
12. **Router coverage.** There are no Jitter, M4L or poly~ domains in the router (dispatch-rules.md: zero hits), and `m4l_critic` is never invoked.
13. **The allowlist wording.** `review_blocker_allowlist.json` calls 120 exemptions "debt" although most are critic false positives. That invites future agents to insert pointless triggers, which would break preset exclusion in timestretch.
14. **Upgrade and uninstall.** There's no path that protects `patches/` and local `overrides.json` edits.
15. **Local permissions.** `.claude/settings.local.json` (local, untracked) auto-approves `cp /tmp/overrides_base.json .claude/max-objects/overrides.json`, which can overwrite the 364 KB overrides without a prompt. Prune stale entries.

---

## 4. Common MAX-patch issues: taxonomy, guard coverage, proposals

Built from 2,533 commits, 390 `versions.json` entries, context/status files and memory. Each "Fires?" verdict comes from an in-memory probe patch run through `validate_patch(deepcopy)`, `review_patch`, `validate_genexpr` and `validate_js` (63 probes).

### 4.1 Ranked classes (frequency × severity)

| # | Class | Fix commits / projects (examples) | MAX symptom | Guard today | Fires? | Proposed guard |
|---|---|---|---|---|---|---|
| 1 | DSP stability: runaway feedback, NaN, clipping, clicks | ≈20 / 12 (afa5ed3, 7076e3d, 80898ec, af145eb, faabbae, f2717af, 89fb84b, 32a7fba, 3dabe7f, 65e8650) | Blow-ups; permanent silence after NaN | dsp_critic gain checks (top level); bassoon-only sim; tanh rule is prose | No | Codebox smoke test at Param corners (§4.3 R9); lint `tanh(…)/tanh(` |
| 2 | Event ordering & message shape: trigger order, invalid trigger letter, `$N` beyond atoms, wrong outlet | ≈17 / 7 (14f2221 `t l b`→`t b l`, 2e40f06, 503f92f, 90671c2, 6efde43, 1dc55a3, 29ba9b4, cac6955, ae967f1, 32be1e3, 5a48451; sample-layers v0.5.1 `t a`) | Silence; values stuck at 0; "doesn't understand a" | Fan-out + hot/cold (top level; the hot/cold check skips trigger-fed boxes, which is exactly the RCC v0.0.7 shape) | 0/5 | R4 |
| 3 | Nonexistent or wrong-domain object, message, function, attribute | ≈15 / 8 (`bach.llll2list` + `expr clip()` physics v0.0.2, 28fb0df "message " prefix ×17, df0e74f `set`→`line~`, `expr~`) | "No such object", "doesn't understand" | `add_box` rejects unknown names; `floor~`; `verified_installed` | Partial: expr~, `expr clip(`, the "message " prefix (created by `modify_box`), unknown objects on load/edit, and messages the destination doesn't understand are all missed | R7 |
| 4 | Load-time init: gain~ at 0, unset params and mutes, no resync | ≈20 / 11 (44afda9, 23d6f01, 9ea409f, 447ac9a, 0e019d0, 2b48909, 0d0f1cf, 49747a0, da8fc2b; mixer v0.0.9–v0.2.0 five in a row) | Silent on open; UI and DSP disagree until touched | None (M4L prose only) | No | R8 |
| 5 | gen~ codebox compile and hoisting | ≈12 / 10 (35acbf3, d9377df, a935b2c, 21c15dc; de-hoists 5c56163, 0d0f1cf, 3b1b4fe, f177540, b74cf6d; 789e737 `e` as a variable) | "failed to compile genpatcher"; silent gen~ | Declaration order, `delay()`, `clip()`, read-before-init | 4/4 legacy checks fire; 0/7 newer constructs caught; codebox inside `p` invisible | R6 |
| 6 | Package & object semantic traps | ≈12 / 7 (dec5f8e bach `@out t`, ji v0.0.3 `applyvalues`, 36bb685 deferlow, FluCoMa ×3) | Silent no-ops, stalls | Only the noisy Control→signal warning | No | Package rule table (R10) |
| 7 | Instancing, `#N`, naming | ≈10 / 4 (mixer v0.0.1–v0.1.0, b677ee8, a639f11 js `maxclass === 'bpatcher'` never matched → 26 stacked duplicates, 40dd55d) | Duplicates on reload; "bad arguments"; "already in use" | Compound-`#N` and comment-`#N` warnings | Partial: comment-`#N` precision is 0% (6/6 hits benign); numeric bpatcher args, shared names, js checks missed | R7, R10 |
| 8 | Patching-layout overlap (most churn) | ≈18 / 9 (timestretch bd6cb84→e6324aa→cc23d01→20b62b4, 4 rounds in a row) | Unreadable patch | Stored-rect overlap | Misses rendered-width overlaps; 357 warnings already | Rendered rects (`len*8+25`, ~5.6 px/char comments) |
| 9 | Lost connections | 5 / 4 (9a7c295 replace_box orphans, f69c1b4, dbf0d6b, terrain v0.16.0, 4edc59f) | Missing channel or feature | `replace_box_safe` (opt-in); the validator itself causes it | No | Save-time cord diff vs HEAD (R1) |
| 10 | Subpatcher port x-order | 4 (5c23cc4, d76608b, bd8553e, terrain) | Messages hit the wrong object | Builder only | No | x-rank unchanged vs HEAD on save |
| 11 | Contrast & canvas bgcolor | ≈11 / 10 | Unreadable labels | Contrast warning | Fires, but noisy (E7); a missing patcher `bgcolor` alone isn't flagged | Theme-aware contrast; flag missing `bgcolor` |
| 12 | `line~` comma segments | 3 (rhythmic-sampler v0.1.1; bassoon aac68ed→df0e74f→0d0f1cf) | Envelope never opens | Validator warning (top level) | Didn't stop 2 commits | Promote to error; recurse |
| 13 | Silent int truncation (arg-less `+ - * /`, int-range `scale`, arg-less `ftom`) | 3 (0f1becf, 503f92f, TCI) | Values flatline | None | 0/3 | Flag float source → int-mode box |
| 14 | M4L `gain~` before `plugout~` | 2 (494c2e6, 8cc5d69) | Silent device | m4l_critic | Not via `review_patch` | Call it (D4) |
| 15 | Duplicate box ids | 1 (a0e2d00) | Label or cord on the wrong box | None | No | Layer-1 error |

### 4.2 Documented rules: caught or not (probed)

**11 of 29 caught** (one only as a non-blocking warning).

Caught:
- ctlin 0–127 → `*~`
- live.dial → line~ → `*~`
- `line~` commas (warning)
- `floor~` at top level
- `@param` → gen~
- umenu plain array
- `fetchindex`
- compound `#N`
- comment `#N`
- unterminated chain
- `inlet~`/`outlet~` (warning only)

Missed:
- a normalizer whose output exceeds 1
- slider → `*~` inlet 0
- `mc.cycle~ → mc.dac~` with no gain stage
- a bare list → `mc.*`
- gain~/live.gain~ → plugout~
- live.dial → gen~ without `param_connect`
- `clip(` in expr
- `expr~` at top level
- `t a`
- arg-less math in a float chain
- numeric bpatcher args as strings
- bach → non-bach without `@out t`
- `info` → buffer~
- unmatched send/receive names
- control-rate feedback loop
- `scale … 0 1` with integer output
- gen~ code I/O vs box I/O (dead detector, E3)
- codebox tabs / `else if` / nested loops / assigning to `e`

The js ES5 lint passes `const`, `let`, `=>`, template literals and `class` in `js` boxes.

### 4.3 Latent hits in committed patches

- **Cords the validator would strip** (all working): mixer-strip obj-15→obj-37, terrain-voice obj-16→obj-60, scala-synth-voice obj-1→obj-3.
- **The 3 failing tests are critic false positives:** timestretch obj-51 (preset exclusion cords), physics obj-107/109 (bach commands), minitaur obj-479/480/481 (display flonum + send).
- **gain~ with no init or recall** (silent until touched; UX only): FDNVerb.maxhelp obj-29, disintegrate-helper obj-10, granularsynthtest obj-26, spectraldetector obj-8.
- **GenExpr:**
  - tape-wobble obj-3 assigns `pi`/`twopi`. Harmless only because the values match the constants; the project is unconfirmed.
  - `sr = samplerate` aliases appear in 5 codeboxes. That's a risk only in Param-only expressions.
- **Rule calibration:** scala-synth-voice compiles with 2-arg `peek` / 3-arg `poke`, so the "explicit channel arg" rule is stricter than MAX requires. Make it a style note. Likewise, `else if` is documented as valid in the 9.2 GenExpr guide, so keep it as a precaution note, not an error.
- **Zero hits** for: ES6 in the 20 js/jsui files, trigger-order inversions, `t a`, `expr clip`, PD or RNBO-only objects, "message " prefixes, numeric-string bpatcher args, umenu format, duplicate ids.

### 4.4 Recommendations (ordered)

1. **R1: Automatic, non-mutating save gate.** In `save_patch_roundtrip` / `write_gendsp`:
   - run `validate_patch(deepcopy)` + `review_patch`;
   - refuse only blockers *not in the original file* (`force=True` to override);
   - diff the cord set against `git show HEAD:path` and report removed cords;
   - check the port x-rank;
   - check for a stale file.
   - Also add a CI pytest job (or a Claude Code PostToolUse hook) and fix SKILL.md:317-320.
2. **R2: Recurse everything** via `iter_patchers()` with gen/rnbo/poly context.
3. **R3: Critic precision**, with a **calibration test: 0 blockers on user-confirmed patches**. Expected result: ~76 → ~35 blockers, and the 3 red tests pass with no patch edits.
   - Fan-out: skip display sinks, preset 0/2/4 and independent branches.
   - Bach-llll: skip command sources.
   - Comment `#N`: skip comments fed by `set …#N`.
   - Control→signal: demote to a note.
   - Contrast: make it theme-aware.
4. **R4: Ordering and atom checks** in `structure_critic`, as blockers:
   - trigger args ∈ {b,i,f,l,s} or constants;
   - the highest `$N` ≤ the atoms the feeding outlet supplies (`b` = 0, `i`/`f`/`s` = 1, bang/done outlets = 0);
   - the hot inlet must be fed by a lower trigger outlet index than every cold feeder (direct, or through one hop via `zl.reg`/`f`/`i`/message/`prepend`; exclude gate/switch/poly~).
5. **R5: Per-port override merge** (C6) and help-box I/O regression (C1/C2).
6. **R6: GenExpr lint** (`validate_genexpr` checks 10–16), plus `validate_js` ES5 lint for `js`/`jsui` boxes only:
   - tab character → error;
   - assignment to a constant name (`e`, `pi`, `twopi`…) → error;
   - Param ∩ assigned locals → error ("can't assign to parameter");
   - nested or non-literal-bound `for` → warning;
   - local alias in a Param-only expression without `History one(1)` → warning;
   - `tanh(x*g)/tanh(g)` in a feedback path → error;
   - `else if` and 2-arg `peek` → notes.
7. **R7: Vocabulary and domain.**
   - A top-level box resolving only to rnbo/gen → error.
   - `clip(` in `expr`/`vexpr`/`if` → error.
   - A message selector must appear in the destination's DB messages (after C8 lands).
   - An unknown object on the load/edit path → error unless an abstraction file exists beside the patch.
   - Fix `modify_box` text (B3); `add_bpatcher` coerces numeric strings to numbers.
8. **R8: `_check_uninitialized_state`.** UI controls that reach DSP need `parameter_enable` + initial, a loadmess/loadbang path, a pattr restore, or a slaved gain~ input. Warn on edits; block on new patches.
9. **R9: Codebox smoke test.** Generalize `patches/bassoon-model/tools/genrun.py` into `dsp_sim`: run each codebox for 1 s with impulse + noise at Param min/max corners; NaN/inf/peak>4/DC/silence → blocker before save.
10. **R10: Cheap wins.**
    - Call `review_m4l`.
    - Duplicate ids → error.
    - Rendered message width in the overlap check.
    - `line~` commas → error.
    - Missing patcher `bgcolor`.
    - Int-truncation shapes.
    - Numeric bpatcher args.
    - Send/receive name pairing across the patch tree (`s`/`r`, `send~`/`receive~`, `pv`, `value`; excluding `#N`).
    - Package rule table (bach `@out t` → non-bach; `deferlow` before `jit.gl.*`; mc list → `applyvalues`).

---

## 5. New features and expansion

1. **MAX bridge for closed-loop verification (the biggest lever).** "Pending test in MAX" is the bottleneck in most project memories (Ambire, terrain-synth, MUSC319/320, TCI). The DB already has the pieces:
   - `error` ("Listens for and reports Max errors as message output");
   - `console` ("Mirror and filter messages to the Max window");
   - `pcontrol` (`load`/`open`/`close`);
   - `sfrecord~`;
   - `node.script` / `udpsend` / `udpreceive`.

   A resident bridge patch could:
   - open a patch;
   - collect console errors ("No such object", "bad arguments", gen~ compile failures);
   - record N seconds of output (or instrument a temp copy that taps the `dac~` inputs) for dsp_sim analysis (NaN/peak/DC/silence/pitch);
   - screenshot for contrast and wrap checks (promote MUSC320's `tools/patch_shot.py`).

   This would become `/max-verify --live`. Start with a spike: does `error` see load-time and gen~ compile errors?
2. **GenExpr → numpy interpreter** for the proven-safe codebox subset (Param, History, Delay, Data, peek/poke, if/else, constant-bound for). It pre-flights every gen~ by running the *real* code, which removes the hand-ported topology drift behind H3.
3. **Edit-session API**, `with edit_patch(path) as p:`:
   - stale check;
   - change tracking;
   - route only touched cords;
   - new-blocker gate;
   - MAX-style JSON writer (byte-stable diffs);
   - atomic write;
   - path-scoped commit.

   It replaces the 20-step recipes in the commands and skills.
4. **Semantic patch diff** (`Patcher.diff`: boxes added/removed/moved, args and cords changed) for /max-iterate review and git history.
5. **Bundle mining:**
   - a help-box I/O oracle and an idiom allowlist (any (src,outlet)→(dst,inlet) pair MAX ships is never stripped);
   - aliases from the 647 `objectfile` lines (`mc.*~` shortcuts, `hslider`, `list.*`, `jit.op` shortcuts, 92 Vizzie short names);
   - group-merged MC/Jitter/OB3D messages and attributes;
   - a version-aware DB (string `min_version`, per-version I/O such as vst~ 4→8) so patches validate for collaborators on older 9.x;
   - an I/O-drift section plus `--apply io` in `sync_max_bundle.py`;
   - a UI-maxclass list generated from the bundle.
6. **Context-aware lookup**, `lookup(name, context="msp"|"gen"|"rnbo"|"m4l")`, used when walking gen~/rnbo~ subpatchers.
7. **Quick-fix payloads on critic findings** (a correctly ordered `t …` for the 17 real reconverging fan-outs, `@param` → `param`, scale insertion for gain), so `/max-iterate --fix` can apply them.
8. **Shipped proven-forms reference** (`references/proven-forms.md` with evidence tiers), plus:
   - a lifecycle step that records user confirmations into it (and fills `test-results/`);
   - `/max-diagnose` (paste a console error → cause → fix).
9. **M4L device pipeline**, `add_m4l_device(kind)`:
   - stereo plugin~/plugout~;
   - live.thisdevice init;
   - correct enums;
   - Push `parameterbanks`;
   - Int/Float/unit-style inference from range and name;
   - `.amxd` export (header constants already in `m4l_constants`).
10. **Value-range propagation** (min/max through number boxes, scale/clip, `* k`, line~) for principled gain-safety and int-truncation checks.
11. **Layout:**
    - section-aware layout with attached decorations (panels and headers move with their members);
    - `relayout_local()`;
    - a width cap;
    - a presentation builder with its own critic;
    - project theme profiles.
12. **Recursive `analyze()`** (flow across `p`/bpatcher boundaries, a parameter and binding inventory, section names from send/receive) and analysis-driven test checklists.
13. **Router domains** for Jitter, M4L and poly~, and a golden RNBO fixture from a MAX-saved rnbo~ patch.
14. **Release hygiene:**
    - CI test job;
    - release smoke test (install the tarball into temp → `get_active_project` → import every module → build and validate a tiny patch);
    - `tools/db_doctor.py` pre-commit (audit + sync dry-run + I/O oracle);
    - stats generated in CI;
    - a doc-signature test that checks every call form in docs/skills against `inspect.signature`.

---

## 6. Suggested fix order

1. **Stop the bleeding.** These are small, contained changes.
   - A1: no destructive auto-fix; container boxes; repair `signal:false` overrides.
   - A2: pure validation; skills validate a deepcopy.
   - A3: new-blocker save gate + cord diff.
   - A5: pathspec commit.
   - A6: stale-file check.
   - B1: stop clearing midpoints.
   - B2/B3: `modify_box`.
   - E1–E3: critic precision + dead detectors, which turns the suite green with no patch edits.
   - A4: CI test job.
   - I1/I2: installer + tarball.
2. **Correct the knowledge.**
   - C1–C8: I/O rules + help-box oracle test, RNBO/Gen-only restriction, live.* maxclass, UI set, per-port merge, MC/Jitter group messages.
   - D1–D2: M4L enums + prefixes.
   - J1–J13: doc fixes.
   - S11: CLAUDE.md slimming.
3. **Widen coverage.**
   - A7/S1: recursion.
   - §4.4 R4/R6/R7/R8/R10: ordering, lint, vocabulary, init and cheap-win checks.
   - H1–H4: dsp_sim.
   - E4–E8: remaining critic fixes.
4. **Expand.**
   - MAX bridge spike.
   - GenExpr interpreter.
   - Edit-session API.
   - Bundle mining.
   - Proven-forms shipping.
