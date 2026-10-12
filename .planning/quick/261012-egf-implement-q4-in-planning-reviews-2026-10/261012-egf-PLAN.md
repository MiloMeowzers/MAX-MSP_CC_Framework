---
phase: quick-261012-egf
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/maxpat/critics/dsp_critic.py
  - src/maxpat/critics/rnbo_critic.py
  - src/maxpat/critics/m4l_critic.py
  - src/maxpat/critics/__init__.py
  - tests/test_critic_revival.py
autonomous: true
requirements: [E3, D4]

estimate:
  tokens: 80000
  raw_tokens: 80000
  tasks: 2
  confidence: low

must_haves:
  truths:
    - "A newobj `gen~ ...` or `mc.gen~ ...` box (the shape MAX and add_gen write) whose embedded codebox uses more in/out than the box has inlets/outlets gets the existing `gen~ I/O input mismatch` / `gen~ I/O output mismatch` blocker. mc.gen~ code is read from `data.patcher` (MAX's mc wrapper) as well as `patcher`. The old maxclass-gen~ fixtures still fire."
    - "(OQ1-A) A codebox with no patchline inside its gen patcher is not used for the comparison (MAX's own gen~.maxhelp demo codebox gives no finding); when no wired codebox has code, the `code_context` fallback works as before."
    - "review_patch runs the RNBO critic for newobj `rnbo~ ...` boxes (the shape MAX writes), and review_rnbo reviews them. Builder-shaped maxclass rnbo~ fixtures behave exactly as before."
    - "review_patch calls review_m4l when the top level contains plugin~, plugout~ or live.thisdevice. Device type is inferred: plugin~ -> audio_effect, plugout~ -> instrument, otherwise midi_effect. A patch with none of the three gets no M4L finding."
    - "Instruments no longer require midiin/midiout. (OQ2-A) No device type requires live.thisdevice. audio_effect and instrument require plugout~; midi_effect requires midiin and midiout."
    - "Every gain~ or live.gain~ upstream of a plugout~ over signal cords (direct or indirect) is exactly one blocker per (stage, plugout~) pair. Control cords don't count as a path. (OQ3-A) Any top-level ezdac~ in a detected M4L device is a blocker."
    - "review_patch on add_m4l_gen_synth output runs the M4L critic (at least one `M4L device` warning) and has zero blockers."
    - "Running review_patch on all 57 committed patch files gives the same findings before and after (any difference is classified in SUMMARY.md). The full suite is green, no committed patch file changed, and every changed .py file passes the Python 3.10 syntax gate."
  artifacts:
    - path: "tests/test_critic_revival.py"
      provides: "Q4 regression tests: gen~/mc.gen~/rnbo~ detection by name (hand-built and real-file repros), M4L dispatch, required objects, gain path, builder-clean"
      contains: "TestGenIOByName"
      min_lines: 200
    - path: "src/maxpat/critics/dsp_critic.py"
      provides: "_check_gen_io_match gated by box name; _gen_inner_patcher reads patcher or data.patcher; wired-codebox selection"
      contains: "_GEN_BOX_NAMES"
    - path: "src/maxpat/critics/rnbo_critic.py"
      provides: "shared is_rnbo_box(box) name predicate used by review_rnbo"
      contains: "def is_rnbo_box"
    - path: "src/maxpat/critics/m4l_critic.py"
      provides: "detect_m4l_device_type, reduced required-object sets, path-based gain-stage check, ezdac~ check"
      contains: "_M4L_GAIN_STAGE_NAMES"
    - path: "src/maxpat/critics/__init__.py"
      provides: "review_patch dispatches the M4L critic; _has_rnbo_boxes by name"
      contains: "detect_m4l_device_type"
  key_links:
    - from: "src/maxpat/critics/__init__.py"
      to: "src/maxpat/critics/m4l_critic.py"
      via: "review_patch -> detect_m4l_device_type(patch_dict) -> review_m4l(patch_dict, device_type=...)"
      pattern: "review_m4l\\(patch_dict, device_type="
    - from: "src/maxpat/critics/__init__.py"
      to: "src/maxpat/critics/rnbo_critic.py"
      via: "_has_rnbo_boxes and review_rnbo share is_rnbo_box, so dispatch and review agree on what counts as rnbo~"
      pattern: "is_rnbo_box"
    - from: "src/maxpat/critics/dsp_critic.py"
      to: "src/maxpat/codegen.py"
      via: "_check_gen_io_match -> _extract_codebox_code -> _gen_inner_patcher -> parse_genexpr_io"
      pattern: "_gen_inner_patcher"
    - from: "src/maxpat/critics/m4l_critic.py"
      to: "src/maxpat/critics/structure_critic.py"
      via: "the gain-path BFS uses Q3's _outlet_is_signal(box, outlet) to decide which cords carry audio"
      pattern: "_outlet_is_signal"
---

<objective>
Implement Q4 of `.planning/reviews/2026-10-11-fix-plan.md`: revive the dead critic detectors and wire in the M4L critic (review findings E3 and D4).

Today three detectors never fire on real patches because they gate on `maxclass`, while MAX writes these boxes as `newobj`:
- the gen~ code-vs-box I/O blocker;
- RNBO dispatch (`_has_rnbo_boxes`), plus a second gate inside `review_rnbo`;
- and `review_m4l` is never called by `review_patch` at all.

Called directly, review_m4l fails the framework's own `add_m4l_gen_synth` output (missing midiin, midiout and live.thisdevice). It also misses `live.gain~ -> plugout~` and anything that isn't a direct cord.

After this plan:
- **gen~ / mc.gen~ (E3)** are matched by box name, and mc.gen~'s `data.patcher` is read.
- **rnbo~ (E3)** is matched by name in both dispatch and review.
- **review_patch calls review_m4l (D4)** for devices it detects. The required objects are reduced, gain stages are flagged on any signal path to plugout~, and the builder's skeleton reviews with zero blockers.
- **Triage:** every committed patch is re-reviewed and any new finding is classified.

Output: two atomic commits (one per task) and one new test file. No committed patch file, builder, or doc is edited.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<rules>
Copied verbatim from `.planning/reviews/2026-10-11-fix-plan.md` ("Rules for every task"). They bind every task below.

1. Read the referenced finding IDs in the review report first; they contain the evidence and the expected fix.
2. Write each regression test **first**. It should reproduce the finding (red) before you fix it (green).
3. **Never edit committed patch files** (`patches/**/*.maxpat|.gendsp|.maxhelp|.js`). They are user-confirmed baselines, and the integration tests depend on them. If one produces a new finding:
   - false positive: fix the checker;
   - true positive in a committed patch: allowlist it with a written reason and list it in SUMMARY.md.
4. Run `python3 -m pytest -q` before and after.
   - Allowed baseline failures until Q3 lands: the 3 `test_review_patch_no_blockers` cases (minitaur, physics-composition, timestretch).
   - From Q3 onward the suite must be fully green.
5. Never `git stash`. Never `git add -A` or `git add .`. Stage explicit paths only.
6. Code must work on Python 3.10.
7. Don't widen scope. If the fix needs a decision the report doesn't make, stop and ask with multiple-choice options.
8. Edit CLAUDE.md, skills or TECHNICAL.md only where the task says to. List any other doc impact in SUMMARY.md.
9. In SUMMARY.md, flag anything that needs the user to confirm in MAX or Live.

Execution-environment additions:
- Q3 has landed, so the suite must stay **fully green** (baseline: 2475 passed, 1 xfailed, 1 xpassed; recorded in this task dir's `baseline-pytest.txt`).
- Execution is sequential on the main working tree (no worktree), branch `main`. Tasks 1 and 2 both edit `src/maxpat/critics/__init__.py` and `tests/test_critic_revival.py`, so they run in order.
- Leave these alone and never stage them:
  - `patches/.active-project.json` (modified);
  - `.planning/tci-phase2/` (untracked);
  - the untracked files in `.planning/quick/261012-c5i-...` and `.planning/quick/261012-di7-...`;
  - this task dir's `base-sha.txt`, `baseline-pytest.txt` and `stash-list-before.txt`. The orchestrator wrote these; don't overwrite them.

  Another instance may commit concurrently. Commit only each task's `<files>`.
- The local interpreter is Python 3.14 and no 3.10 is installed. Avoid 3.11+ syntax and APIs (no `match`, no `ExceptionGroup`, no `tomllib`, no PEP 695 generics). Every task's verify runs an `ast.parse(..., feature_version=(3, 10))` gate.
- Committed `.maxpat` / `.maxhelp` files are opened read-only (`json.load`). Critics always get a freshly loaded dict, or a `copy.deepcopy` before any mutation.
- Throwaway scripts and their outputs (the triage snapshots, historical `git show` copies) go in a scratch directory **outside the repo**: your session scratchpad, else `mktemp -d`. Never write them under the repo.
- Do not touch `src/maxpat/builders.py`, `m4l_constants.py` or `m4l_polish.py`. Q15 owns them (stereo plugout~ wiring, enums, prefixes, Push banks).
</rules>

<open_questions>
These are decisions the report does not make (rule 7). The orchestrator must put them to the user before execution and record each answer on its `Answer:` line. If execution starts with no recorded answer, the executor uses the **Recommended** option and lists it in SUMMARY.md as "resolved by default". Every task below is written for the recommended options, and each alternative's delta is stated.

**OQ1. Which codebox does the revived gen~ I/O check compare?** Today `_extract_codebox_code` takes the first codebox in the gen patcher and compares its in/out usage against the gen~ box's inlet/outlet counts. A codebox's `in1..inN` are its own inlets, and inside a gen patcher anything can feed them. The planner ran the name-based detector over the 1018 help/example files in the Max bundle; 3 gen~ boxes there embed a codebox. One is a false positive: `help/msp/gen~.maxhelp` obj-29 (inside a tab subpatcher) holds a demonstration codebox with **no cords at all**, using in1..in4/out1..out3, inside a gen~ with 1 inlet. The committed corpus is unaffected under either option: all 35 embedded codeboxes are add_gen-shaped (`in N` -> codebox -> `out N`) and match.
- A) **(Recommended) Use the first codebox that has code and appears in at least one patchline of its gen patcher.** Codeboxes with no cords (demonstration or dead code) are skipped. If no wired codebox has code, fall back to `code_context` as today. This suppresses the bundle false positive. The existing maxclass fixtures still fire through their `code_context`, because their codeboxes have no lines.
- B) **Literal.** Keep first-codebox selection, with no wiring filter.
  - Delta: the Task 1 "unwired codebox" fixtures flip to expecting a blocker.
  - Delta: gen~.maxhelp obj-29 is listed in SUMMARY.md as a known residual false positive.

Answer: A (user, 2026-10-12): first wired codebox.

**OQ2. live.thisdevice in the required-object sets.** The spec says to drop midiin/midiout for instruments and requires `add_m4l_gen_synth` output to pass with zero blockers. That skeleton (gen~, live.dial x N, `plugout~ 1`) has no live.thisdevice, so after the midi drop review_m4l still emits `M4L instrument missing required object: live.thisdevice` as a blocker. Evidence that it isn't required:
- the framework's own builder omits it;
- the kicksynth-m4l device at 494c2e6 (the gain~ fix later used as the D1 ground truth) has none;
- no CLAUDE.md or skill rule asks for it.

Options:
- A) **(Recommended) Not required.** Remove live.thisdevice from every required set and emit no finding for it. audio_effect = {plugout~}, instrument = {plugout~}, midi_effect = {midiin, midiout}.
- B) **Advisory note.** Same sets as A, plus one `note` when a detected device has no live.thisdevice.
  - Delta: TestM4LRequiredObjects asserts that note, and the builder-clean test still asserts zero blockers.
- C) **Builder adds it.** Keep live.thisdevice required and make `add_m4l_gen_synth` emit a live.thisdevice box.
  - Delta: edits `src/maxpat/builders.py`, which Q15 owns, and may break `tests/test_m4l_gen_synth.py` box-count assertions.
  - Delta: Task 2 `<files>` grows by those two paths.

Answer: A (user, 2026-10-12): live.thisdevice not required.

**OQ3. "ezdac~ on any path to plugout~" can't happen.** The DB gives ezdac~ 2 signal inlets and **0 outlets**, so it can never sit upstream of plugout~, and a path check never fires for it. CLAUDE.md's M4L rule still lists it ("No gain~ / live.gain~ / ezdac~ before plugout~").
- A) **(Recommended)** Any top-level ezdac~ in a detected M4L device is a **blocker** (same severity as the gain-stage check).
- B) **Literal.** Path check only. ezdac~ is never flagged; record in SUMMARY.md that it is structurally unreachable.
  - Delta: the ezdac~ fixture asserts no finding.
- C) Any top-level ezdac~ in a detected M4L device is a **warning**.
  - Delta: the ezdac~ fixture asserts a warning and no blocker.

Answer: A (user, 2026-10-12): ezdac~ anywhere in a detected M4L device is a blocker.
</open_questions>

<assumption_delta_decision>
Primary noun: the M4L required-object set per device type. Transition: required -> optional (midiin/midiout for instruments per the spec; live.thisdevice per OQ2). Decision: **no-change** to the model. There are still three device types with one required set each, and only the set contents shrink. Rationale: the type is inferred from boxes the patch already has, so no new chosen or plural concept is introduced.
</assumption_delta_decision>

<context>
CLAUDE.md is already loaded as project instructions. Don't re-read it.

Read only these ranges:
- `.planning/reviews/2026-10-11-repo-review.md`: lines 95-104 (§1D, D4), 106-116 (§1E, E3), 264 (§4.1 class 14), 281-303 (§4.2 missed list: `gain~/live.gain~ -> plugout~`, gen~ I/O dead detector). This satisfies rule 1.
- `.planning/reviews/2026-10-11-fix-plan.md`: lines 17-33 (rules) and 90-102 (Q4). Lines 285-300 (Q15) only to see what NOT to touch.
- `src/maxpat/critics/__init__.py` (all 114 lines).
- `src/maxpat/critics/dsp_critic.py` lines 1-172 (module docstring, constants, `review_dsp`, `_check_gen_io_match`, `_extract_codebox_code`).
- `src/maxpat/critics/rnbo_critic.py` lines 1-90.
- `src/maxpat/critics/m4l_critic.py` lines 1-155. The rest (parameter uniqueness, quality, info text, banks) is unchanged.
- `src/maxpat/critics/structure_critic.py` lines 100-116 (`_outlet_is_signal`).
- `src/maxpat/utils.py` (`get_box_name`, 18 lines).
- `src/maxpat/builders.py` lines 971-1060 (`add_m4l_gen_synth`). Read only.
- Tests:
  - `tests/test_critics.py` lines 9-31 (imports, `_make_patch`), 33-110 (maxclass gen~ fixtures), 268-290, 750-1000 (maxclass rnbo~ fixtures) and 1030-1135;
  - `tests/test_critic_precision.py` lines 1-50 (module-docstring, import and `_load` pattern to copy).
</context>

<observed_facts>
The planner verified these on 2026-10-12 at HEAD `635883b` (= `base-sha.txt`). If a live value differs at execution time, the live value wins; record the difference in SUMMARY.md.

**Line references (the spec's numbers have shifted after Q1-Q3):**
- The gen~ maxclass gate is at `dsp_critic.py:112` (the spec says 110), inside `_check_gen_io_match` (lines 99-154). `_extract_codebox_code` is at lines 157-171 and reads only `box["patcher"]`.
- `_has_rnbo_boxes` is at `critics/__init__.py:27-35` (the spec says 28-36).
- There is a **second** maxclass gate at `rnbo_critic.py:57` (the review_rnbo loop). If only `_has_rnbo_boxes` changes, review_rnbo still skips every newobj rnbo~, so the revival is a no-op.
- `m4l_critic.py`:
  - `_REQUIRED_OBJECTS` is at lines 20-24;
  - `_check_gain_plugout` is at lines 69-115: one finding per direct cord, `gain~` name only, line 106;
  - `review_m4l(patch_dict, device_type=None)` returns `[]` when `device_type` is None.
- `review_patch` is at `critics/__init__.py:55-102`.

**Shapes MAX writes (bundle and corpus):**
- gen~: newobj with text `gen~ ...` and the gen patcher at `box["patcher"]`. Example: Max bundle `help/msp/gen~.maxhelp`.
- mc.gen~: newobj with text `mc.gen~ ...` and the gen patcher at **`box["data"]["patcher"]`** (mc wrapper, `wrapper_uniquekey`). Examples: bundle `gen~.maxhelp` and committed `patches/ji-harmonizer/generated/ji-harmonizer.maxpat` obj-88. CLAUDE.md's add_gen-plus-rename recipe writes `box["patcher"]` instead, so both locations occur.
- rnbo~: newobj with text like `rnbo~ @title basic`, and the inner patcher at `box["patcher"]` with `classnamespace: "rnbo"`. Example: RNBO package `help/rnbo_expm1~.maxhelp` obj-1.
- The framework's builder `add_rnbo` writes maxclass `rnbo~` with text `rnbo~`. `get_box_name` returns the maxclass for non-newobj boxes, so a name test covers both shapes. It also covers the maxclass-gen~ test fixtures.
- `add_gen(code, num_inputs=1, num_outputs=1)` with code using in1..in3/out1..out2 writes newobj `gen~` 1/1 with `in 1` -> codebox -> `out 1` wired. `review_dsp` on it returns `[]` today (the review's R).

**Corpus** (`git ls-files patches`: 56 .maxpat + 1 .maxhelp = 57 files, no .amxd):
- No plugin~, plugout~, live.thisdevice or rnbo~ at any depth.
- 46 top-level gen~/mc.gen~ boxes (43 gen~, 3 mc.gen~):
  - 35 embed a wired codebox (34 via `patcher`, plus ji-harmonizer obj-88 via `data.patcher`). All 35 match: code I/O <= box I/O. For example, ji-harmonizer obj-88 has code 3/1 and box 3/1, and wormhole obj-12 has code 4/2 and box 4/2.
  - The other 11 reference an external .gendsp or a named gen (no embedded code) and stay skipped.
- Today, review_patch over the 57 files gives 1350 findings, of which 1 is a blocker (slot.maxpat, allowlisted).

**Full-change simulation** (OQ1-A, OQ2-A, name-based RNBO in both gates, M4L dispatch), run by the planner on a `git archive HEAD` scratch copy:
- the corpus findings are identical (1350 / 1 blocker, 0 new, 0 gone);
- the full suite is 2475 passed, 1 xfailed, 1 xpassed, so **no existing test changes contract**;
- `gen~.maxhelp` obj-29 is suppressed under OQ1-A.

**add_m4l_gen_synth** (`[("freq", 20., 2000.), ("amp", 0., 1.)]`) emits: newobj `gen~`, newobj `plugout~ 1`, and 2 `live.dial`. It has no live.thisdevice, midiin or midiout.
- `review_patch` today: 0 findings.
- `review_m4l(d, "instrument")` today: 3 blockers (missing live.thisdevice, midiin, midiout) and 5 warnings (openinpresentation, devicewidth, 2 info-text, live.banks).

**History.** `patches/kicksynth/generated/kicksynth-m4l.maxpat` was deleted at d46042a.
- At 408cdf8 it has notein and live.thisdevice, and gain~ obj-8 -> plugout~ obj-9 at inlets 0 and 1. Today's per-cord check emits 2 duplicate findings for that one gain~.
- At 494c2e6 the gain~ is gone (and so is live.thisdevice), with gen~ obj-7 -> plugout~ obj-9 at both inlets.
- review_patch gives 0 blockers on both today.

**DB:**
- ezdac~: 2 signal inlets, 0 outlets.
- gain~: outlet 0 signal, outlet 1 control.
- live.gain~: outlets 0-1 signal, 2-4 control.
- plugout~ / plugin~: 2 signal inlets and 2 signal outlets.
- mc.plugout~ / mc.plugin~ are not in the DB.

**Tests:**
- No test references `review_m4l`, `m4l_critic`, or its finding text.
- `src/maxpat/m4l_polish.py:25` imports `_LIVE_NO_PARAM` from m4l_critic. Keep that name.
- `tests/test_critics.py` `_gen_io_mismatch_patch` / `_gen_output_mismatch_patch` use maxclass gen~, a codebox with `lines: []`, and pass `code_context`. The four `_rnbo_patch_*` fixtures use maxclass rnbo~.
</observed_facts>

<settled_decisions>
Resolved at planning from the Q4 spec and the E3/D4 fix columns. Don't re-litigate them; if something live contradicts one, stop and ask (rule 7).

- **S1: gen~ detection (E3).**
  - Add module-level `_GEN_BOX_NAMES = frozenset({"gen~", "mc.gen~"})` in `dsp_critic.py`. The gate in `_check_gen_io_match` becomes `get_box_name(box) in _GEN_BOX_NAMES`. That is first-token equality, the precise reading of "text starting with". It also keeps maxclass-gen~ fixtures, because `get_box_name` returns the maxclass for non-newobj boxes.
  - New helper `_gen_inner_patcher(box) -> dict | None` returns `box["patcher"]` when it is a dict, else `box["data"]["patcher"]` when both are dicts, else None. `_extract_codebox_code` uses it.
  - Under OQ1-A, `_extract_codebox_code` collects every box id that appears as a `source[0]` or `destination[0]` in the inner `lines` (accepting both `{"patchline": {...}}` and bare entries). It returns the code of the first codebox with non-empty `code` whose id is in that set, else None. Under OQ1-B there is no wiring filter.
  - Finding texts, suggestions and blocker severity are unchanged (prefixes `gen~ I/O input mismatch:` / `gen~ I/O output mismatch:`).
  - Update the module docstring, the `review_dsp` docstring and the check's docstring, citing Q4 / E3: detection is by name, and mc.gen~ is read from `data.patcher`.
- **S2: RNBO detection (E3).**
  - Add a public `is_rnbo_box(box: dict) -> bool` in `rnbo_critic.py`, returning `get_box_name(box) == "rnbo~"` (import `get_box_name` from `src.maxpat.utils`).
  - The review_rnbo loop gate uses it, and `_has_rnbo_boxes` in `critics/__init__.py` uses it (import from rnbo_critic).
  - The inner patcher stays at `box["patcher"]`, which is MAX's location.
  - E8 items stay as they are; Q26 owns them: the missing-in~ blocker, positional `param` names, and the builder shape. SUMMARY.md notes that MAX-authored generator rnbo~ boxes now get the same missing-in~ blocker builder-made ones already get.
- **S3: M4L dispatch (D4).**
  - Add a public `detect_m4l_device_type(patch_dict: dict) -> str | None` in `m4l_critic.py`. It reads top-level box names via `get_box_name`; this also catches a maxclass `live.thisdevice`.
  - It returns None unless the names include plugin~, plugout~ or live.thisdevice. Then plugin~ gives `"audio_effect"`, plugout~ gives `"instrument"`, and anything else gives `"midi_effect"`.
  - `review_patch` calls it right after the RNBO block; when the result isn't None it extends with `review_m4l(patch_dict, device_type=<type>)`.
  - Add `"review_m4l"` to `__all__`, and update the module and `review_patch` docstrings ("the M4L critic is only invoked when plugin~, plugout~ or live.thisdevice is present").
  - `review_m4l(..., device_type=None)` still returns `[]`.
- **S4: Required objects.** `_REQUIRED_OBJECTS` becomes audio_effect {"plugout~"}, instrument {"plugout~"}, midi_effect {"midiin", "midiout"} (OQ2-A). The finding text is unchanged (`M4L <type> missing required object: <name>`). Under OQ2-B, add the note per OQ2; under OQ2-C, see OQ2.
- **S5: Gain stages and ezdac~.** Rewrite `_check_gain_plugout(boxes, lines)` in place.
  - `_M4L_GAIN_STAGE_NAMES = frozenset({"gain~", "live.gain~"})`.
  - Build `rev: dict[str, list[str]]` (destination id to source ids) from cords where `_outlet_is_signal(src_box, src_outlet)` is true. Import `_outlet_is_signal` from `src.maxpat.critics.structure_critic`; it reads outlettype and falls back to the `~` name only when outlettype is missing.
  - For each plugout~ box in box order, breadth-first walk `rev` with a visited set, continuing through every box, gain stages included.
  - Record each reached box whose `get_box_name` is in the set. Emit one blocker per (stage id, plugout id), sorted by (plugout id, stage id):
    - finding `"<name> (<stage id>) is on the signal path to plugout~ (<plugout id>) -- Ableton's channel strip handles volume, so a gain stage before plugout~ is redundant and can silence the device"`;
    - suggestion `"Remove <name> and route the final processing stage directly to plugout~"`.
  - Under OQ3-A, also emit one blocker per top-level ezdac~:
    - finding `"ezdac~ (<id>) in an M4L device -- Live's channel strip handles output and volume; route the final processing stage to plugout~"`;
    - suggestion `"Remove ezdac~ and connect the final processing stage to plugout~"`.
  - Scope is top-level cords only, matching every other critic. send~/receive~ pairs aren't followed, and mc.gain~ / mc.live.gain~ aren't in the set (the spec names three objects). Both are listed in SUMMARY.md as residual.
  - Update the module docstring and the check's docstring, citing Q4 / D4.
- **S6: Test placement.**
  - New file `tests/test_critic_revival.py`. Its module docstring cites quick 261012-egf, Q4, E3 and D4, and says committed patches are read-only.
  - It imports `review_patch` and `_has_rnbo_boxes` from `src.maxpat.critics`, `review_dsp` / `review_rnbo` / `review_m4l` / `detect_m4l_device_type` from their modules, `Patcher` from `src.maxpat.patcher`, and from `tests.test_critics`: `_make_patch`, `_gen_io_mismatch_patch`, `_gen_output_mismatch_patch`, `_rnbo_patch_clean`, `_rnbo_patch_duplicate_params`.
  - It defines a `_load(rel)` helper (json.load from the repo root), and deep-copies before any mutation.
  - Wrap `add_gen` calls in `warnings.catch_warnings()` so GenExpr diagnostics don't leak.
  - Existing tests in `tests/test_critics.py` are not modified (the simulation showed no contract change).
- **S7: Docs (rule 8).** No CLAUDE.md, skill or TECHNICAL.md edits. SUMMARY.md lists:
  - `TECHNICAL.md:504` (the gen~ I/O row now covers newobj gen~/mc.gen~);
  - `TECHNICAL.md:554` (says "six" critics and that m4l_critic is not called; it is now called);
  - there is no M4L critic subsection in TECHNICAL.md;
  - `.claude/skills/max-critic/SKILL.md:30-33` (add an M4L auto-invoke line);
  - `.claude/skills/max-critic/references/critic-protocol.md:19`.
- **S8: Allowlist.** `tests/review_blocker_allowlist.json` is unchanged. `_blocker_match_key` only knows the fanout and bach_llll kinds. If triage finds a new **true-positive** blocker in a committed patch (none expected), stop and ask (rule 7): allowlisting it means adding a new kind, which is outside Q4. A new **false positive** is fixed in the checker (rule 3).
</settled_decisions>

<tasks>

<task type="tracer" tdd="true">
  <name>Task 1: Detect gen~/mc.gen~/rnbo~ by box name end-to-end (E3): dsp_critic, rnbo_critic, _has_rnbo_boxes, with newobj and real-file repros</name>
  <files>tests/test_critic_revival.py, src/maxpat/critics/dsp_critic.py, src/maxpat/critics/rnbo_critic.py, src/maxpat/critics/__init__.py</files>
  <read_first>.planning/reviews/2026-10-11-repo-review.md (lines 95-116), .planning/reviews/2026-10-11-fix-plan.md (lines 17-33, 90-102), src/maxpat/critics/__init__.py (all), src/maxpat/critics/dsp_critic.py (lines 1-172), src/maxpat/critics/rnbo_critic.py (lines 1-90), tests/test_critics.py (lines 9-110, 750-1000), tests/test_critic_precision.py (lines 1-50)</read_first>
  <behavior>
    TestGenIOByName ("gen finding" means a result whose finding starts with `gen~ I/O`). Every fixture is a hand-built dict built with `_make_patch` unless stated. "Wired" means inner lines `in N` -> codebox and codebox -> `out N`.
    - newobj `gen~`, numinlets 1 / numoutlets 1, inner patcher `in 1` -> codebox (code `out1 = in1 + in2 + in3; out2 = in1;`) -> `out 1`, wired. `review_dsp` gives exactly 2 gen blockers: an input mismatch naming 3 inputs and an output mismatch naming 2 outputs. RED: `[]`, the review's repro.
    - The same box with text `gen~ @title demo`: the same 2 blockers. RED.
    - newobj `mc.gen~` with the same mismatched inner patcher stored under `data.patcher` (MAX's mc wrapper shape, no `patcher` key): an input blocker. RED.
    - newobj `mc.gen~` with the inner patcher under `patcher` (the add_gen-plus-rename shape): an input blocker. RED.
    - Builder repro: `Patcher().add_gen("out1 = in1 + in2 + in3;\nout2 = in1;", num_inputs=1, num_outputs=1)`, then `to_dict()`, then `review_dsp`: input and output blockers. RED: `[]`.
    - Real files (deepcopy, then mutate):
      - ji-harmonizer obj-88 (`mc.gen~`, `data.patcher`, code 3/1) with numinlets set to 2 gives an input blocker naming `obj-88`. RED. Unmutated, it gives no gen finding;
      - wormhole obj-12 (`gen~`, code 4/2) with numoutlets set to 1 gives an output blocker naming `obj-12`. RED.
    - Anchors:
      - a matched newobj `gen~` 1/1 with code `out1 = in1 * 0.5;`, wired, gives no gen finding;
      - newobj `gen~ @gen foo.gendsp` with no inner patcher gives no gen finding;
      - the imported maxclass fixtures `_gen_io_mismatch_patch()` and `_gen_output_mismatch_patch()`, with their code_context, still give their blockers.
    - Unwired codebox (OQ1-A). A maxclass-`gen~` box 1/1 whose only codebox (code uses in1..in4, out1..out3) appears in no inner line:
      - with no code_context, no gen finding. RED: blocker, since today it is checked;
      - the same fixture as a newobj `gen~` also gives no gen finding;
      - the same unwired fixture **with** `code_context={"gen~_code": {<id>: <code>}}` gives an input blocker (the fallback is preserved).
      - Under OQ1-B, the first two expect a blocker instead.
    - End-to-end: `review_patch` on the first newobj fixture includes both gen blockers. RED.

    TestRNBOByName:
    - MAX-shaped newobj rnbo~: text `rnbo~ @title demo`, numinlets 1 / numoutlets 1, inner `patcher` with `classnamespace: "rnbo"`, `in~ 1`, `out~ 1`, and two boxes `param @name gain @min 0 @max 1`:
      - `review_rnbo` gives a blocker whose finding contains "duplicate" (case-insensitive). RED: `[]`;
      - `review_patch` gives the same duplicate blocker. RED.
    - The same shape with params `param @name GainLevel ...` and `param @name FilterCutoff ...`: `review_patch` gives naming warnings mentioning both. RED.
    - A clean MAX-shaped newobj rnbo~ (in~, out~, one `param @name gain_level ...`): `review_patch` gives no finding containing "rnbo~" or "param".
    - `_has_rnbo_boxes`:
      - True for the newobj fixture and for `_rnbo_patch_clean()` (maxclass rnbo~);
      - False for a patch whose only box is newobj `gen~`.
      - The newobj case is RED today.
    - The maxclass fixtures are unchanged through `review_patch`: `_rnbo_patch_duplicate_params()` still gives a duplicate blocker, and `_rnbo_patch_clean()` still gives no RNBO finding.
  </behavior>
  <action>
    Implement the Q4 "Detect by box name, not maxclass" bullets per S1, S2 and S6. Recommended: OQ1-A.

    Step 0, baseline (rule 4). Set `Q=.planning/quick/261012-egf-implement-q4-in-planning-reviews-2026-10`.
    - Confirm `git rev-parse HEAD` equals `$Q/base-sha.txt`, and `git stash list` equals `$Q/stash-list-before.txt` (both empty today). If HEAD moved because another instance committed, record that in SUMMARY.md and continue; the base stays the file's value. Don't overwrite either file.
    - Run `python3 -m pytest -q -p no:cacheprovider` and confirm it is fully green (2475 passed, 1 xfailed, 1 xpassed). Record the totals.
    - Triage "before" snapshot. In a scratch directory outside the repo, write a throwaway Python script that:
      - lists `git ls-files patches` paths ending in `.maxpat` or `.maxhelp`;
      - `json.load`s each one and runs `review_patch`;
      - saves `{path: sorted([severity, finding] pairs)}` as JSON in that scratch directory.

      Expected: 57 files, 1350 findings, 1 blocker. Keep the script; Task 2 reruns it.

    RED:
    1. Create `tests/test_critic_revival.py` with the module docstring, the imports and the `_load` helper (S6), and the classes TestGenIOByName and TestRNBOByName covering every `<behavior>` bullet.
    2. Run it and confirm it is red for the stated reasons. Record the red/green counts for SUMMARY.md.

    GREEN:
    3. `src/maxpat/critics/dsp_critic.py`, per S1 (OQ1-A wiring filter): add `_GEN_BOX_NAMES` and `_gen_inner_patcher`, change the gate in `_check_gen_io_match`, and rewrite `_extract_codebox_code`. Update the three docstrings. Leave `_check_gain_staging`, `_check_unsafe_gain_sources` and `_SIGNAL_OUTLET_TYPES` alone.
    4. `src/maxpat/critics/rnbo_critic.py`, per S2: add `is_rnbo_box`, use it at the loop gate, and add a one-line Q4 / E3 note to the module docstring. Leave `_check_io_completeness`, `_extract_param_name` and the other checks alone (E8 is Q26).
    5. `src/maxpat/critics/__init__.py`: `_has_rnbo_boxes` delegates to `is_rnbo_box`, with a docstring citing Q4 / E3. Make no M4L change yet (Task 2).
    6. Re-run until green. Then run the full suite: it must stay fully green.

    Commit with explicit paths only: `git add tests/test_critic_revival.py src/maxpat/critics/dsp_critic.py src/maxpat/critics/rnbo_critic.py src/maxpat/critics/__init__.py`, then `git commit -m "fix(critics): detect gen~/mc.gen~/rnbo~ by box name and read mc.gen~ data.patcher, reviving the gen~ I/O and RNBO detectors (Q4 E3)" -- <same paths>`.
  </action>
  <verify>
    <automated>python3 -m pytest -q -p no:cacheprovider tests/test_critic_revival.py tests/test_critics.py</automated>
    <automated>python3 -c "import ast,sys; [ast.parse(open(f).read(), filename=f, feature_version=(3, 10)) for f in sys.argv[1:]]; print('PY310-SYNTAX-OK')" src/maxpat/critics/dsp_critic.py src/maxpat/critics/rnbo_critic.py src/maxpat/critics/__init__.py tests/test_critic_revival.py</automated>
    <automated>python3 -m pytest -q -p no:cacheprovider && echo SUITE-GREEN</automated>
  </verify>
  <done>
    - Every TestGenIOByName and TestRNBOByName case passes, and each RED case was recorded red first.
    - The maxclass fixtures in `tests/test_critics.py` pass unchanged.
    - The full suite is green.
    - One commit containing exactly the 4 listed paths.
    - The triage "before" snapshot exists in scratch, outside the repo.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Wire review_m4l into review_patch (D4): device-type detection, reduced required objects, gain stages on any path to plugout~, builder skeleton clean; corpus triage and final gates</name>
  <files>src/maxpat/critics/m4l_critic.py, src/maxpat/critics/__init__.py, tests/test_critic_revival.py</files>
  <read_first>.planning/reviews/2026-10-11-repo-review.md (lines 103, 264, 281-303), src/maxpat/critics/m4l_critic.py (lines 1-155), src/maxpat/critics/structure_critic.py (lines 100-116), src/maxpat/builders.py (lines 971-1060, read only), src/maxpat/critics/__init__.py (as left by Task 1)</read_first>
  <behavior>
    Fixtures are hand-built with `_make_patch` and real outlettypes: `plugin~`/`plugout~` `["signal", "signal"]`, `gen~` `["signal"]`, `gain~` `["signal", ""]`, `live.gain~` `["signal", "signal", "", "", ""]`, `*~` `["signal"]`, `number` `["", "bang"]`. "Gain finding" means a result whose finding contains "is on the signal path to plugout~".

    TestM4LDispatch:
    - `detect_m4l_device_type`:
      - plugin~ -> plugout~ gives `"audio_effect"`;
      - `notein` + gen~ -> plugout~ gives `"instrument"`;
      - newobj `live.thisdevice` + `midiin` gives `"midi_effect"`;
      - a maxclass `live.thisdevice` box alone gives `"midi_effect"`;
      - cycle~ -> `*~ 0.5` -> dac~ gives `None`.
    - `review_patch` on the cycle~ -> `*~` -> dac~ patch gives no finding containing "M4L" or "plugout~".
    - `review_patch` on plugin~ -> plugout~ (both inlets) with no patcher props gives a warning starting with "M4L device missing openinpresentation". RED: not called.

    TestM4LRequiredObjects:
    - `review_m4l(notein + gen~ -> plugout~, "instrument")` gives no finding containing "missing required object". RED: midiin, midiout, live.thisdevice.
    - `review_m4l(plugin~ -> plugout~, "audio_effect")` gives no "missing required object" finding. RED: live.thisdevice.
    - `review_patch` on newobj `live.thisdevice` alone gives exactly two blockers: `M4L midi_effect missing required object: midiin` and `...: midiout`. RED: not called.
    - `review_patch` on plugin~ -> `*~ 0.5` (no plugout~) gives the blocker `M4L audio_effect missing required object: plugout~`. RED.
    - Under OQ2-B, also assert the live.thisdevice note.

    TestM4LGainPath (`review_patch`):
    - gen~ -> gain~ outlet 0 -> plugout~ inlets 0 and 1 gives **exactly one** gain finding: a blocker containing the gain~ id and the plugout~ id. RED: 0 through review_patch; 2 duplicates through review_m4l.
    - gen~ -> live.gain~ (outlets 0/1) -> plugout~ (inlets 0/1) gives one blocker naming live.gain~. RED.
    - Indirect: gen~ -> gain~ -> `*~ 0.5` -> plugout~ gives one blocker naming gain~. RED.
    - Chain: gen~ -> gain~ -> live.gain~ -> plugout~ gives two blockers, one each. RED.
    - Anchors:
      - side branch: plugin~ -> plugout~, and plugin~ -> gain~ -> `meter~`. gain~ is not upstream of plugout~, so no gain finding;
      - control only: gain~ outlet 1 -> `number` -> `*~` inlet 1, with plugin~ -> `*~` inlet 0 and `*~` -> plugout~. No gain finding, because a control cord is not a signal path.
    - ezdac~ (OQ3-A): plugin~ -> plugout~ and plugin~ -> ezdac~ give one blocker starting with "ezdac~ (" and containing "M4L device". RED. Under OQ3-B: no ezdac~ finding. Under OQ3-C: a warning.

    TestM4LBuilderClean:
    - `Patcher().add_m4l_gen_synth([("freq", 20.0, 2000.0), ("amp", 0.0, 1.0)])`, then `to_dict()`, then `review_patch`:
      - at least one finding starts with "M4L device" (the critic ran);
      - zero blockers.
      - RED: no M4L finding.
    - `review_m4l` on the same dict with `"instrument"` gives zero blockers. RED: 3.
  </behavior>
  <action>
    Implement the Q4 "Wire in the M4L critic" and "Triage" bullets per S3, S4, S5, S6 and S8. Recommended: OQ2-A, OQ3-A.

    RED: add the four classes to `tests/test_critic_revival.py` covering every `<behavior>` bullet. Run the file and confirm it is red for the stated reasons. Record the counts.

    GREEN:
    1. `src/maxpat/critics/m4l_critic.py`:
       - add `detect_m4l_device_type` (S3);
       - set `_REQUIRED_OBJECTS` per S4;
       - add `_M4L_GAIN_STAGE_NAMES` and rewrite `_check_gain_plugout` as the path-based check, plus the ezdac~ check (S5), importing `_outlet_is_signal` from `src.maxpat.critics.structure_critic`;
       - update the module docstring (first bullet: gain stages on any signal path to plugout~, plus ezdac~) and the check docstrings, citing Q4 / D4.

       Keep `_LIVE_NO_PARAM` and the parameter-uniqueness, device-quality, info-text and live.banks checks unchanged; D5 and `_LIVE_NO_PARAM` belong to Q15.
    2. `src/maxpat/critics/__init__.py`: import `review_m4l` and `detect_m4l_device_type`, dispatch per S3 after the RNBO block, add `"review_m4l"` to `__all__`, and update the module and `review_patch` docstrings.
    3. Re-run until green. Then run `tests/test_m4l_gen_synth.py`, `tests/test_critics.py` and `tests/test_integration_patches.py`, then the full suite: it must be fully green. Record the totals.
    4. Historical evidence (record in SUMMARY.md, not a test). Use `git show 408cdf8:patches/kicksynth/generated/kicksynth-m4l.maxpat` and `git show 494c2e6:patches/kicksynth/generated/kicksynth-m4l.maxpat`, each redirected into the scratch directory outside the repo. Run `review_patch` on both. Expected:
       - 408cdf8: exactly one blocker, the gain finding for gain~ obj-8 -> plugout~ obj-9;
       - 494c2e6: zero blockers.
    5. Triage (rule 3, the spec's "Triage" bullet). Re-run Task 1's throwaway script into an "after" JSON in scratch and diff it against "before" per file: new pairs and gone pairs. Expected: 0 new and 0 gone, because no committed patch contains plugin~/plugout~/live.thisdevice/rnbo~ and all 35 embedded gen~ codeboxes match.
       - Classify every difference in SUMMARY.md.
       - A false positive is fixed in the checker, then re-run.
       - A true-positive blocker means stop and ask (S8).
       - Also record how many top-level gen~/mc.gen~ boxes the detector now examines: expected 35 of 46 (it was 0), with 11 external .gendsp skipped.
    6. Final gates: see the last `<verify>` command.

    Commit with explicit paths: `git add src/maxpat/critics/m4l_critic.py src/maxpat/critics/__init__.py tests/test_critic_revival.py`, then `git commit -m "fix(critics): wire review_m4l into review_patch; drop instrument midi and live.thisdevice requirements; flag gain~/live.gain~ on any signal path to plugout~ and ezdac~ in devices (Q4 D4)" -- <same paths>`. Adjust the subject to match the recorded OQ2/OQ3 answers, keeping `(Q4 D4)`.

    Then write SUMMARY.md (see `<output>`).
  </action>
  <verify>
    <automated>python3 -m pytest -q -p no:cacheprovider tests/test_critic_revival.py tests/test_critics.py tests/test_m4l_gen_synth.py tests/test_integration_patches.py</automated>
    <automated>python3 -c "import ast,sys; [ast.parse(open(f).read(), filename=f, feature_version=(3, 10)) for f in sys.argv[1:]]; print('PY310-SYNTAX-OK')" src/maxpat/critics/m4l_critic.py src/maxpat/critics/__init__.py tests/test_critic_revival.py</automated>
    <automated>python3 -m pytest -q -p no:cacheprovider && echo SUITE-GREEN</automated>
    <!-- planner-discipline-allow: patches/ -->
    <automated>Q=.planning/quick/261012-egf-implement-q4-in-planning-reviews-2026-10; B=$(cat $Q/base-sha.txt) || exit 1; H=$(git log --format=%H --grep='(Q4 ' "$B"..HEAD) || { echo GIT-LOG-FAILED; exit 1; }; N=$(printf '%s\n' "$H" | grep -c .); [ "$N" = 2 ] || { echo "Q4-COMMITS=$N"; exit 1; }; for h in $H; do F=$(git show --name-only --format= "$h") || exit 1; X=$(printf '%s\n' "$F" | grep . | grep -v -E '^(src/maxpat/critics/(dsp_critic|rnbo_critic|m4l_critic|__init__)\.py|tests/test_critic_revival\.py)$'); [ -z "$X" ] || { echo "EXTRA-FILES in $h: $X"; exit 1; }; done; GS=$(git status --porcelain -- patches/) || { echo GIT-STATUS-FAILED; exit 1; }; W=$(printf '%s\n' "$GS" | grep . | grep -v ' patches/.active-project.json$'); [ -z "$W" ] || { echo "PATCH-WORKTREE: $W"; exit 1; }; S=$(git stash list) || { echo GIT-STASH-LIST-FAILED; exit 1; }; [ "$S" = "$(cat $Q/stash-list-before.txt)" ] || { echo STASH-CHANGED; exit 1; }; git log --format='%h %s' --grep='(Q4 ' "$B"..HEAD; echo GATES-OK-2-Q4-COMMITS-NO-PATCH-EDITS-STASH-UNCHANGED</automated>
  </verify>
  <done>
    - Every TestM4LDispatch, TestM4LRequiredObjects, TestM4LGainPath and TestM4LBuilderClean case passes, and each RED case was recorded red first.
    - `add_m4l_gen_synth` output reviews with zero blockers and visible M4L warnings.
    - The full suite is green.
    - Triage shows no unclassified new finding.
    - Exactly 2 `(Q4 ` commits since `base-sha.txt`, each touching only plan files, with none under `patches/`.
    - The stash list is unchanged.
    - SUMMARY.md is written.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Critic output -> max-critic revision loop (and, after Q7, the save gate) | Newly live detectors can block generation. Too loose lets silent M4L devices or broken gen~ wiring ship; too strict blocks correct devices. |
| Committed patches -> triage and tests | Frozen user-confirmed baselines are read for repros and must never be written. |
| Executor -> git index on shared `main` | A concurrent instance and dirty unrelated files are present. |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-egf-01 | Elevation of Privilege | OQ1-A unwired-codebox skip in `_extract_codebox_code` | low | mitigate | The skip applies only to codeboxes with zero cords. The `code_context` fallback is kept and tested. Wired-mismatch anchors (hand-built, add_gen, ji-harmonizer obj-88, wormhole obj-12) stay blockers. |
| T-egf-02 | Denial of Service | M4L and RNBO critics now live in `review_patch` (false blockers stall the loop) | medium | mitigate | The required sets are reduced to what a device needs. TestM4LBuilderClean pins zero blockers on the builder skeleton. Corpus triage shows 0 new findings. The 494c2e6 kicksynth-m4l device reviews at 0 blockers. The E8 missing-in~ false positive is handed to Q26 and noted in SUMMARY.md. |
| T-egf-03 | Tampering | Committed patches edited to satisfy critics | high | mitigate | Rule 3. Real-file repros deepcopy before mutating. The final gate fails on any `patches/` path in Q4 commits or in the working tree, except the pre-existing `.active-project.json`. |
| T-egf-04 | Repudiation | git staging next to a concurrent instance | medium | mitigate | Explicit-path `git add` / `git commit -- <paths>` only, with no stash, `-A` or `.` (rule 5). The gate checks each `(Q4 ` commit's file list against the plan's files and compares the stash list before and after. |
| T-egf-05 | Tampering | Historical `git show` copies and triage snapshots | low | mitigate | They are written only to a scratch directory outside the repo and are never staged. |
| T-egf-SC | Tampering | npm/pip/cargo installs | high | mitigate | No package-manager install. Only the standard library and in-repo code are used, so no Package Legitimacy Audit is required. |
</threat_model>

<source_audit>
Sources:
- the fix-plan Q4 section and its rules;
- review findings E3 and D4, plus §4.1 class 14 and §4.2 (missed `gain~/live.gain~ -> plugout~`, dead gen~ I/O detector);
- the Q3 PLAN and SUMMARY (plan shape, allowlist conventions, `_outlet_is_signal`);
- the orchestrator's constraints.

This quick task has no ROADMAP phase, CONTEXT.md or RESEARCH.md.

| Source item | Covered by | Status |
|---|---|---|
| GOAL: revive dead detectors and review_m4l | Tasks 1-2 | COVERED |
| gen~ code-vs-box I/O check matches by name (gen~, mc.gen~) | Task 1 (S1) | COVERED (mc.gen~ `data.patcher` read, so MAX-saved mc.gen~ is live; codebox choice per OQ1) |
| `_has_rnbo_boxes` matches by name (rnbo~) | Task 1 (S2) | COVERED (plus the second gate in review_rnbo, without which the revival is a no-op) |
| Add newobj fixtures; keep the old maxclass fixtures working | Task 1 behavior | COVERED |
| review_patch calls review_m4l on plugin~ / plugout~ / live.thisdevice | Task 2 (S3) | COVERED |
| Drop the midiin/midiout requirement for instruments | Task 2 (S4) | COVERED (live.thisdevice per OQ2) |
| Flag gain~ / live.gain~ / ezdac~ on any path to plugout~ | Task 2 (S5) | COVERED (ezdac~ is a sink; handled per OQ3) |
| add_m4l_gen_synth output passes with zero blockers | Task 2 TestM4LBuilderClean | COVERED |
| Triage: review_patch on every committed patch, classify NEW findings in SUMMARY | Task 1 step 0 plus Task 2 step 5 | COVERED |
| Verify the spec's line references against live code | observed_facts; SUMMARY.md | COVERED |
| The 9 rules copied into the plan | `<rules>` | COVERED |
| E8 RNBO critic and builder fixes (missing in~ severity, positional param, builder shape) | Q26 | EXCLUDED (other task); consequence noted in SUMMARY.md |
| D1/D2/D3/D5: enums, prefixes, add_gen inlets, stereo plugout~, Push banks, `_LIVE_NO_PARAM` | Q15 | EXCLUDED (other task) |
| E6: plugout~ as a terminal and live.gain~ as a gain stage in dsp_critic | Q26 | EXCLUDED (other task) |
| Recursion into subpatchers; send~/receive~ path following | Q19/Q20 | EXCLUDED; residual listed in SUMMARY.md |
| Doc and skill text (TECHNICAL.md, max-critic SKILL, critic-protocol) | SUMMARY.md doc-impact list (S7, rule 8) | EXCLUDED from edits, reported |
</source_audit>

<verification>
- `python3 -m pytest -q -p no:cacheprovider` is fully green before (2475 passed, 1 xfailed, 1 xpassed) and after each task. Passes rise only by the new tests.
- Corpus triage over the 57 committed files: findings before = after (expected 1350, 1 blocker, slot.maxpat, allowlisted). The gen~ I/O detector now examines 35 of 46 top-level gen~/mc.gen~ boxes (it was 0).
- Historical: kicksynth-m4l at 408cdf8 gives 1 gain blocker; at 494c2e6 it gives 0 blockers.
- Exactly 2 `(Q4 ` commits since `base-sha.txt`, each touching only its task's `<files>`. No `patches/` path in them or in the working-tree diff (apart from the pre-existing `.active-project.json`). The stash list is unchanged.
- The Python 3.10 syntax gate passes on every changed `.py` file.
</verification>

<success_criteria>
- E3 is fixed: gen~/mc.gen~/rnbo~ are detected by box name, the gen~ I/O blocker and the RNBO critic fire on MAX-shaped boxes, and the maxclass fixtures still work.
- D4 is fixed: review_patch runs review_m4l on detected devices, instruments don't need midiin/midiout, gain stages on any signal path to plugout~ block, and the builder skeleton reviews with zero blockers.
- Every committed patch is re-reviewed, with no unclassified new finding and no patch edits. The suite is green and the code is Python 3.10 clean.
</success_criteria>

<output>
Create `.planning/quick/261012-egf-implement-q4-in-planning-reviews-2026-10/261012-egf-SUMMARY.md` when done. It must include:
- baseline and final pytest totals, plus the red counts recorded before each GREEN step;
- how each open question was resolved: user answer, or "resolved by default" with the recommended option;
- live line references vs the spec: `dsp_critic.py:112` (spec 110), `critics/__init__.py:27-35` (spec 28-36), and the extra gate at `rnbo_critic.py:57`;
- the triage table: 57 files, findings and blockers before/after, new/gone counts, each NEW finding classified (expected none), and gen~ boxes examined 0 -> 35 of 46 (11 external .gendsp skipped). Also note that 0 committed patches contain plugin~/plugout~/live.thisdevice/rnbo~;
- the historical kicksynth-m4l results (408cdf8 and 494c2e6);
- residuals, all out of scope:
  - a codebox fed by `param`/`history` inside the gen patcher is still compared against gen~ box inlets;
  - only one codebox is compared per gen~;
  - external .gendsp code is not checked;
  - send~/receive~ are not followed to plugout~;
  - mc.gain~ / mc.live.gain~ are not in the gain set;
  - critics are top-level only;
  - MAX-authored generator rnbo~ boxes now hit the E8 missing-in~ blocker (Q26);
- hand-offs:
  - Q15: stereo plugout~ wiring in add_m4l_gen_synth, `_LIVE_NO_PARAM` / D5, enums;
  - Q26: E6 plugout~ terminal and live.gain~ gain stage, E8;
  - Q19/Q20: recursion;
  - Q7: the save gate will now see M4L and RNBO blockers;
- the S7 doc-impact list (not edited, rule 8);
- rule 9, "Confirm in MAX / Live": nothing is required, because no patch or builder changed. FYI: M4L devices reviewed by the critic now show polish warnings (openinpresentation, devicewidth, info text, live.banks), and gain~/live.gain~ before plugout~ now blocks.
</output>
