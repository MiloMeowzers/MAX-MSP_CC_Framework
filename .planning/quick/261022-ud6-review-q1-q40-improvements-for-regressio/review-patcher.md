---
area: patch model + save path
range: 0f96a6f1..8ddcdc49
reviewed: 2026-10-22
files_reviewed_list:
  - src/maxpat/patcher.py
  - src/maxpat/builders.py
  - src/maxpat/layout.py
  - src/maxpat/sizing.py
  - src/maxpat/aesthetics.py
  - src/maxpat/edit_session.py
  - src/maxpat/maxjson.py
  - src/maxpat/atomic_io.py
  - src/maxpat/hooks.py
  - src/maxpat/patch_diff.py
  - src/maxpat/project.py
  - src/maxpat/defaults.py
  - src/maxpat/analysis.py
  - scripts/ (build_release.sh, audit_signal_role.py; relayout_patch.py and memory.py removal)
findings:
  blocker: 1
  warning: 9
  info: 6
status: issues_found
---

# Q1–Q40 regression review: patch model + save path

## Method

Every finding was reproduced by running code. Writes went only to scratch copies: `/private/tmp/claude-501/rt/repo` is a scratch git repo holding copies of all 98 committed `patches/**` files, and `/private/tmp/claude-501/rt/m8` holds copies of external user patches. Nothing under `patches/` was written. The main repo is unchanged (`git status` is clean apart from the pre-existing `.planning` untracked files).

### Invariants that hold (verified)

| Invariant | Evidence |
|---|---|
| Lossless `from_dict`→`to_dict` | 77/77 committed patch files: dict-equal, input not mutated. 446/448 external files (2 exceptions, see IN-01). |
| Byte-identical no-op save | 77/77 through the real `save_patch_roundtrip` into the scratch repo, and 77/77 through a no-op `edit_patch` session: no write, no commit, no warning. Also every MAX ≥ 9.1 file in `~/Projects`, `~/Documents/UBC` and `~/Dev/scuffed` (177 files). |
| Change tracking reaches disk | Cord order, hidden, color and midpoint clear; box fontsize; extra_attrs delete and add; presentation off. |
| Save gate | 63/63 edit sessions that move one box saved with no false refusal. Adding an inlet at the right of a loaded `p` saves, and parent `numinlets` grows 4→5. An inlet x-swap is refused. |
| Port ranks under layout | `finalize_patch(is_new=True, force_layout=True)` over every committed patch: no crash, 0 port x-rank changes. |
| `auto_commit_patch` path scoping | `git commit -- <abs paths>` with `--literal-pathspecs`; return codes are checked. |
| Python 3.10 | All modules import under 3.10.19, and the round trip passes there, including under `LC_ALL=C`. |
| Dead code (Q32) | Nothing outside `.planning` and `tests/test_dead_code_removed.py` references `relayout_patch`, `src.maxpat.memory`, `build_examples_catalog`, `add_node_script`, `MS_*` and the rest. `scripts/audit_signal_role.py` still runs. |

## Narrative findings

### BLOCKER

#### CR-01: `replace_box` / `replace_box_safe` silently throw away an embedded patcher (gen~ code, `p` contents)
- **Where:** `src/maxpat/patcher.py:1203-1258`. Line 1246 rebuilds the box with plain `add_box`, and `_carry_box_identity` (1262-1344) copies no `_inner_patcher`. `_require_buildable` (`builders.py:126`) refuses only `p`/`patcher`.
- **Repro:** run `read_patch("patches/amplitude-follower/generated/amplitude-follower.maxpat")`, then `p.replace_box_safe(<gen~ obj-8>, "gen~")`.
  - The new box has no `patcher` key, so the embedded 3-box gen patcher and its GenExpr code are gone.
  - I/O resets to the DB default (1/1 → 2/1).
  - `orphaned == []`, and no exception is raised.
  - The save gate only emits a cord-removal `SaveGateWarning` and then writes. It does the same for `gen~`→`mc.gen~`, which is a conversion CLAUDE.md suggests.
- **Impact:** data loss of user DSP code on an operation that Rule #8 and Q29 describe as "keeps the box's identity".
- **Fix:** in `replace_box`, raise `ValueError` before any change when `old_box._inner_patcher is not None`, unless the old and new names are both content-defined compatible (`gen~`/`mc.gen~`, `p`/`patcher`). In the compatible case, move `_inner_patcher` (and its `_parent_box` back-reference) to the new box and keep its I/O counts.

### WARNING

#### WR-01: The save gate's port x-rank check is bypassed when the subpatcher box text changes in the same save; renames also raise false "cord removed" warnings
- **Where:** `src/maxpat/hooks.py:686`. The path element is `(box id, box text)`, and `_port_ranks` (733) and `_cord_set` (697) key on that path.
- **Repro** (scratch copy of `barnett-dbap/generated/dbap-source.maxpat`): swap the x of inlets 0 and 1 inside `p scenespack` (obj-155).
  - The swap alone is REFUSED (`inlet obj-150 rank 0 -> 1`).
  - The same swap plus `modify_box(obj-155, args=[..., "x"])` SAVES.
- **Second symptom:** the rename alone emits a `SaveGateWarning` claiming "8 cord(s) removed … (endpoint box deleted)" for every inner cord. Nothing was removed.
- **Fix:** key patcher paths on box id (plus maxclass) only. If the "regenerated, different subpatcher" case matters, detect it by comparing inner port-box ids, not the parent text.

#### WR-02: `replace_box_safe` makes the gate refuse blockers that were already in the patch
- **Where:**
  - `patcher.py:1246`: the replacement gets a fresh `_gen_id()`.
  - `hooks.py:590-599`: `_finding_key` matches baseline findings by `obj-N` ids.
- **Repro** (scratch `rhythmic-sampler/generated/slot.maxpat`, which already has a fan-out blocker on `buffer~` obj-1):
  ```
  with edit_patch(f) as p:
      p.replace_box_safe(obj1, "buffer~", args=["#1"])
  ```
  The result is `PatchValidationError: Fan-out without trigger: 'buffer~' (obj-172) ...`. The edit introduced nothing, but the blocker now carries a new id. This contradicts CLAUDE.md Rule #7, "pre-existing blockers still save".
- **Fix:** let `replace_box` reuse `old_box.id` (the old box is already removed). This also keeps the cords and the `session.diff` stable. The alternative is to map old→new id in the gate.

#### WR-03: A no-op save or `edit_patch` rewrites every Max 8 and Max 9.0.x file
- **Where:**
  - `maxjson.py:24-26`: the legacy tab layout is "not reproduced".
  - `hooks.py:305-308`.
  - `edit_session.py:124`: "no-op" is decided by byte equality.
- **Repro:** every tab-indented file in the user's projects fails the byte round trip. That is 202 files: Max 5.1–8.6, and 39 saved by **Max 9.0.x**, e.g. SCI `brainSCI.maxpat` (9.0.4) and the TCI repo.
- **edit_patch case:** a copy of `brainSCI.maxpat` through an empty `edit_patch` block gives `saved=True` with `len(diff)==0` and 41,800 changed diff lines out of 21,972. Under `patches/` that whole-file rewrite would also be committed.
- **Contradicted claims:** CLAUDE.md Rule #5 ("a no-op save is byte-identical") and the edit_session docstring step 4.
- **Fix:**
  1. In `EditSession.__exit__`, treat `new_dict == self._baseline` as the no-op test.
  2. Add a legacy writer: tab indent, `"key" : value`, and the `}\n,` brace style. Select it when `original_text` uses that layout.
  3. Until then, document that layout normalisation happens.

#### WR-04: `finalize_patch(is_new=True)` changes the patch before `LayoutRefusedError`
- **Where:** `hooks.py:192-195`. `apply_auto_styling` runs before `apply_layout` does its refusal check.
- **Repro:** `finalize_patch(read_patch(ji-harmonizer)[0], is_new=True)` raises `LayoutRefusedError`. By then the patcher already has:
  - `locked_bgcolor` added;
  - loadbang obj-106 and obj-267 given `bgcolor [0.85,0.92,0.85]`.

  The docstrings say the refusal happens "before changing anything". A caller that catches the error and saves ships the restyle. Q27 introduced the refusal.
- **Fix:** call `layout._check_layout_allowed(patcher)` (unless `force_layout`) as the first statement of the `is_new` branch.

#### WR-05: `modify_box(args=...)` on loaded UI boxes writes bogus text (the B3 fix covered only message/comment)
- **Where:** `patcher.py:1059-1064`, with the overlay at 495-496.
- **Repro** (ji-harmonizer):
  - textbutton "load .scl" + `args=["Go"]` → `"text": "textbutton Go"`, and the rect resets to 100×20.
  - toggle + `args=["1"]` → a new `"text": "toggle 1"` key in the JSON.
- **Fix:** use the message/comment rule (`" ".join(args)`) for every non-newobj maxclass that carries text (textbutton, live.text, umenu labels). Refuse `args` for other UI maxclasses (point to `extra_attrs`). Do not resize a box whose size is fixed or user-set.

#### WR-06: `modify_box(extra_attrs={"patching_rect"|"text"|...})` is silently lost on loaded boxes and diverges on new ones
- **Where:** `patcher.py:1124-1143`. The `_BOX_HANDLED_KEYS` entries go into `_raw`, but `to_dict` overlays the model fields.
- **Repro:**
  - Loaded box: `[30,30,58,22]` with extra_attrs `patching_rect=[10,10,300,22]` still serializes as `[30,30,58,22]`.
  - New box: serializes as `[10,10,300,22]`, while `box.patching_rect` stays `[0,0,102,22]`, which is what layout and the overlap check read.
- **History:** pre-existing, but Q6/Q28 reworked this block and left it in place.
- **Fix:** map `patching_rect`/`text` onto the fields (as `presentation`/`fontname` already are), and raise for `id`/`maxclass`/`numinlets`/`numoutlets`/`outlettype`/`patcher`.

#### WR-07: The edit-session contrast pass recolours user textcolors wrongly (bach.roll, gradient panels)
- **Where:**
  - `edit_session.py:115-119`;
  - `aesthetics.py:488-492`: any box with `textcolor` is a target;
  - `aesthetics.py:525-534`: only newobj/message/umenu get an implicit own fill;
  - `aesthetics.py:335-367`: a gradient panel resolves to `grad1` only.
- **Repro** (moving each box 1 px through the session path):
  - physics-composition `bach.roll` obj-67 goes black → `[0.8,0.8,0.82]`. That is light notation on bach.roll's own white background, which is unreadable.
  - amplitude-follower comments obj-7 and obj-10 go light → black over a mode-1 gradient panel. `grad2` (dark `0.27,0.31,0.43`) is ignored.
  - In total, 42 explicit colours across 9 committed patches would flip when touched.
- **Stale doc:** `ui-presets.md:172` still says "Contrast is NOT recomputed on the edit path".
- **Fix:**
  - Treat objects that paint their own background (bach.*, jit.cellblock, textedit, live.* displays, …; ideally DB-driven) as "own" surfaces, or skip them.
  - For `mode: 1` gradient panels, score against both `grad1` and `grad2`.
  - In edit sessions, keep an explicit colour unless the box was newly added.

#### WR-08: An identical-code `write_gendsp` is not a no-op: auto-detected inputs remove existing `in N` boxes and cords
- **Where:** `hooks.py:960-993`.
- **Repro** (scratch copies): `write_gendsp(<the file's own code>, path)` for every committed single-codebox .gendsp.
  - 11 files: byte-identical.
  - `granularsynthtest/granular-sched.gendsp`: removed `in 1`, set the codebox to `numinlets 0`, orphaned cord obj-1→obj-2, and committed the result.
  - `granular-engine.gendsp`: removed its `in 1`.
- **Impact:** with an `in 2` that the code doesn't read, the parent `gen~` loses inlet 1, and MAX drops the parent cord on load. The save gate cannot see this, because it is a cross-file change.
- **Fix:** on the in-place path with `num_inputs/num_outputs=None`, never go below the existing port count (`max(detected, existing)`). Remove ports only when they are passed explicitly.

#### WR-09: The skills don't know about the new `LayoutRefusedError`
- **Where:**
  - `layout.py:99-136`: the refusal at >120 boxes or MAX-saved, including any inner patcher.
  - The `finalize_patch(patcher, is_new=True)` recipes in `max-patch-agent/SKILL.md:215`, `max-dsp-agent/SKILL.md:277` and `max-ui-agent`.
- **Gap:** none of these mention `force_layout` or the exception (`git grep` finds no hits). A large `/max-build` (or one that embeds a >120-box subpatcher) now crashes at finalize, and per WR-04 the patch is already partially restyled when it does.
- **Fix:** document `force_layout=True` for big new builds in those recipes, together with WR-04.

### INFO

- **IN-01:** `patcher.py:2072`: a box without `patching_rect` gets a default `[0,0,60,22]` written on round trip. The only case found is two old files, `~/Projects/Set_performance Package_v5-Beta/Set*.maxpat`. Fix: track whether the key was absent.
- **IN-02:** `replace_box` resets `patching_rect` w/h even for a same-class replacement: the FDNVerb `live.dial` obj-33 goes from 50×48 to 44×66. This is documented, but it shows as a visible resize in an approved patch. Consider carrying the size when `same_class`.
- **IN-03:** `patch_diff.py:415-439` reports cord `order`/`hidden`/`color` changes nowhere; only midpoints show as `cord_rerouted`. A `/max-iterate` diff therefore hides those edits.
- **IN-04:** `auto_commit_patch` (`project.py:364-430`) now raises `RuntimeError` instead of returning None (a Q5 contract change). The `max-iterate.md:145` and `max-test.md:33` recipes call it directly with no handling. Note this in those docs.
- **IN-05:** Stale docs:
  - `max-iterate.md:113` says `replace_box_safe` "auto-rewires only on matching inlet/outlet counts". Since Q29 it rewires any in-range cord.
  - `proven-forms.md:123` says `finalize_patch(is_new=False)` "re-routes every cord". Since Q6 it routes only new or touched cords.
  - `shared-capabilities.md:33` says it "regenerates midpoints".
- **IN-06:** `hooks.py:1009`: `_edit_gendsp_in_place` adds missing port boxes with the overlap check skipped. They are placed 80 px right of the existing ports, which can sit on top of user boxes. This is cosmetic.

## Spec gaps

| Q | What's missing |
|---|---|
| Q29 (B9) | Byte-identical no-op saves are verified only for the MAX ≥9.1 layout (and only in-repo files). Max 9.0.x and Max 8 tab-layout files are fully rewritten (WR-03). The maxjson docstring says Max 9.0 help patches were measured, but user files saved by 9.0.x use the legacy layout. |
| Q29 (B4) | The identity carried by `replace_box` omits the box id (WR-02) and the embedded patcher (CR-01), and drops the size (IN-02). |
| Q29 (B8) | The in-place `write_gendsp` port "sync" shrinks ports on an unchanged-code rewrite (WR-08). |
| Q6 (B3) | The no-prefix text rule covers only message/comment; textbutton and other text-bearing UI still get `maxclass args` text (WR-05). |
| Q7 / R1 | The port x-rank check is keyed on box text, so a rename disables it (WR-01). Matching "by rule + box ids" breaks on any id change (WR-02). |
| Q27 (F5) | The refusal is not atomic within `finalize_patch` (WR-04), and the skill recipes were not updated (WR-09). |
| Q36 | Contrast on touched boxes is not safe for self-filled objects or gradient panels (WR-07). The no-op test is byte-based, not semantic (WR-03). The doc updates missed `ui-presets.md:172` and `max-iterate.md:113` (IN-05). |
| Q28 | Done as specified. Pre-existing `modify_box(extra_attrs=)` model-field loss remains (WR-06). |
| Q5, Q32, Q33 | Done as specified. No remaining references to the removed code, and no hand-built `Box.__new__` outside `patcher.py`. |

---
_Reviewer: Claude (gsd-code-reviewer), deep, verified by execution_
