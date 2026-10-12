---
phase: quick-261012-bii
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/maxpat/validation.py
  - src/maxpat/__init__.py
  - src/maxpat/db_lookup.py
  - tests/test_validation_nondestructive.py
  - tests/test_validation.py
  - tests/test_integration_patches.py
  - tests/test_round_trip.py
  - .claude/skills/max-patch-agent/SKILL.md
  - .claude/skills/max-dsp-agent/SKILL.md
autonomous: true
requirements: [A2, A1, A8]

estimate:
  tokens: 75000
  raw_tokens: 75000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "validate_patch never mutates its input: a dict is deep-equal to its pre-validation copy afterwards, a Patcher keeps every line, and dict and Patcher input produce identical (layer, level, message, proposed_removal) lists."
    - "Every cord the validator would drop is reported as an error whose proposed_removal is (src_id, outlet, dst_id, inlet); nothing is removed unless the caller explicitly calls apply_fixes(patch, results)."
    - "has_blocking_errors(results) is True whenever a proposed removal exists (is_new=True is the default); has_blocking_errors(results, is_new=False) reports but does not block on proposed removals."
    - "cycle~ into p / patcher / bpatcher / poly~ / mc.poly~ / pfft~ / rnbo~ / any box with an embedded patcher keeps its cord with no connection finding, and container outlets carry no signal_role; out-of-range indices on a container are still proposed for removal."
    - "A signal_role mismatch is a warning with no proposed removal; tapin~ into tapout~ (and every pair in relationships.json) produces no connection finding, while an out-of-range index on a known pair is still proposed for removal."
    - "The 3 known strips (mixer-strip obj-15->obj-37, terrain-voice obj-16->obj-60, scala-synth-voice obj-1->obj-3) keep their cords with 0 proposed removals, none allowlisted and none xfailed; test_validate_patch_no_errors fails on any proposed removal in a committed patch."
    - "The mixer-strip review xfail is strict=True and its reason names the blocker that actually fires today."
    - "The max-patch-agent and max-dsp-agent new-patch protocols validate a copy.deepcopy and treat proposed removals as inspect, don't save."
    - "The pytest failing set equals the pre-task baseline (only the 3 allowed test_review_patch_no_blockers cases) and no file under patches/ changed."
  artifacts:
    - path: "src/maxpat/validation.py"
      provides: "ValidationResult.proposed_removal, non-mutating Layer 3, container detection, warning-only role tier, known-pair skip, apply_fixes, has_blocking_errors(results, is_new=True)"
      contains: "def apply_fixes"
    - path: "src/maxpat/db_lookup.py"
      provides: "ObjectDatabase.is_known_pair loaded from relationships.json"
      contains: "def is_known_pair"
    - path: "src/maxpat/__init__.py"
      provides: "apply_fixes exported beside validate_patch / has_blocking_errors"
      contains: "apply_fixes"
    - path: "tests/test_validation_nondestructive.py"
      provides: "Q1 regression tests: purity, dict/Patcher identity, proposed removals, apply_fixes, blocking semantics, containers, role warnings, known pairs, the 3 committed strips"
      min_lines: 180
    - path: "tests/test_integration_patches.py"
      provides: "test_validate_patch_no_errors counts proposed removals; strict mixer-strip xfail with an accurate reason"
      contains: "proposed_removal"
  key_links:
    - from: "tests/test_integration_patches.py"
      to: "src/maxpat/validation.py"
      via: "every result with proposed_removal set (or level error) fails the committed-patch test"
      pattern: "proposed_removal"
    - from: "src/maxpat/validation.py"
      to: "src/maxpat/db_lookup.py"
      via: "_validate_connections asks db.is_known_pair(src_name, dst_name) after the bounds checks"
      pattern: "is_known_pair"
    - from: "src/maxpat/db_lookup.py"
      to: ".claude/max-objects/relationships.json"
      via: "_load reads the pairs list into an unordered, alias-canonical pair set"
      pattern: "relationships.json"
    - from: ".claude/skills/max-patch-agent/SKILL.md"
      to: "src/maxpat/validation.py"
      via: "new-patch protocol validates copy.deepcopy(patch_dict) and gates the save on has_blocking_errors / proposed_removal"
      pattern: "deepcopy"
---

<objective>
Implement Q1 of `.planning/reviews/2026-10-11-fix-plan.md`: make `validate_patch` non-destructive.

Today Layer 3 (`_validate_connections`) pops "invalid" cords out of a dict input in place and marks them `auto_fixed`, which `has_blocking_errors` ignores. A Patcher input reports the same removal but removes nothing. The skills validate `patch_dict` and then save that same dict, so valid cords are silently deleted (review A1/A2). The integration test skips auto-fixed results, so CI never sees it (A8).

After this plan:
- validation is pure;
- removals are data (`proposed_removal`), applied only through an explicit `apply_fixes`;
- containers accept any cord;
- role mismatches warn;
- `relationships.json` pairs are never flagged;
- a proposed removal blocks new patches;
- the integration test fails on any proposed removal in a committed patch.

Output: three atomic commits (one per task), one new test file, and the two skill protocol blocks updated.

Requirements (quick-task scoped, from the review report):
- **A2**: pure validation, `apply_fixes()`, skills validate a deepcopy.
- **A1 (API part only)**: containers accept anything, role mismatches never strip, `relationships.json` pairs never removed. The data part (signal:false overrides, `_build_inlet_array`, guard test, biquad~, `in`/`peek~`, trailing outlets) is Q2 and is OUT of scope.
- **A8**: count proposed removals as failures in the integration test, and make the mixer-strip xfail strict.
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

Execution-environment additions (from the orchestrator):
- Execution is sequential on the main working tree (no worktree).
- Another Claude instance is committing to `patches/barnett-dbap/` concurrently (HEAD moved to `0f96a6f` during planning). Commit only this plan's `files_modified` paths. Leave `patches/.active-project.json` (modified) and `.planning/tci-phase2/` (untracked) alone.
- The local interpreter is Python 3.14 and no 3.10 is installed. Avoid 3.11+ syntax and APIs (`typing.Self`, `except*`, PEP 695 generics, `itertools.batched`). Every task's verify runs an `ast.parse(..., feature_version=(3, 10))` syntax gate.
</rules>

<context>
CLAUDE.md is already loaded as project instructions. Don't re-read it.

Read in this order, and only these ranges:
- `.planning/reviews/2026-10-11-repo-review.md` lines 50-61: the 1A table rows A1, A2, A8 (rule 1).
- `.planning/reviews/2026-10-11-fix-plan.md` lines 37-53: the Q1 section.
- `src/maxpat/validation.py`:
  - 1-200: module docstring, `_STRUCTURAL_MAXCLASSES`, `_ROLE_TIER_TABLE`, `ValidationResult`, `validate_patch`, `has_blocking_errors`;
  - 232-252: `_extract_object_name`;
  - 456-716: `_validate_connections`, `_inlet_accepts_signal`, `_classify_dst_inlet`, `_classify_role_mismatch`.
- `src/maxpat/db_lookup.py` lines 72-135: `__init__` / `_load`, where aliases load first.
- `tests/test_validation.py`:
  - 1-60: helpers `_make_patch_dict`, `_make_box`, `_make_line`, and the module-scoped `db` fixture;
  - 173-572: Layer 3 and role-aware classes;
  - 1165-1246: `TestLayer3OverrideGuard`.
- `tests/test_integration_patches.py`: the whole file (172 lines).
- `src/maxpat/patcher.py` lines 39-75 (`Patchline` fields `source_id`, `source_outlet`, `dest_id`, `dest_inlet`) and 1202-1215 (`Patcher.from_dict(data, db=None)`).

Do NOT open any `objects.json` or `overrides.json` with the Read tool. Probe the DB only through `ObjectDatabase` in short `python3 -c` calls.
</context>

<observed_facts>
The planner verified these on 2026-10-12 at HEAD `0f96a6f`. If a live value differs at execution time, the live value wins; record the difference in SUMMARY.md.

**Baseline.** `python3 -m pytest -q -p no:cacheprovider` gives 2309 passed, 3 failed, 2 xfailed, 1 xpassed, in about 34 s.
- The 3 failures are the allowed `test_review_patch_no_blockers` cases (minitaur, physics-composition, timestretch).
- XFAIL: the mixer-strip review case, and `test_round_trip.py::TestFileLevelRoundTrip::test_framework_file_byte_identical`.
- XPASS: `test_max_saved_file_byte_identical`. Both round-trip markers are unrelated to Q1; leave them.

**The only mutation** in `validation.py` is the reverse-order `lines.pop(idx)` loop at the end of `_validate_connections` (around lines 605-607). No other layer writes to the input. With Patcher input, `validate_patch` calls `patch.to_dict()` and mutates only that throwaway copy.

**Every cord the current code strips in a committed patch** (scan of all `patches/*/generated/*.maxpat`):

| Patch | Cord | Source box | Destination box | Why it's stripped today | Q1 path |
|---|---|---|---|---|---|
| mixer-strip | obj-15:0 -> obj-37:0 | `selector~ 2` (role audio, outlettype signal) | `p sends`, embedded patcher; DB `p` inlet 0 `signal:false` | legacy "Signal outlet to control-only inlet" | **Fixed in Q1 (container rule):** the cord is kept and gets no finding. No xfail. |
| terrain-voice | obj-16:0 -> obj-60:0 | `*~ 0.` (audio) | `p motion`, embedded patcher | same legacy branch | **Fixed in Q1 (container rule).** As a side effect, this also removes a false Layer-4 warning `Unterminated signal chain: '*~' (obj-16)`. Layer 4 now sees the unstripped graph. |
| scala-synth-voice | obj-1:0 -> obj-3:0 | `in 1`; DB outlet role `status` (wrong, owned by Q2) | `peek~ scala-tuning`; DB inlet 0 `signal:true` (wrong, owned by Q2) | role tier `status -> signal`: error plus removal | **Fixed in Q1 (role mismatch becomes a warning):** the cord is kept with 0 proposed removals. A role *warning* remains until Q2 corrects the `in` / `peek~` DB data. It is not an error and not a removal, so it is not allowlisted or xfailed. Hand it off to Q2 in SUMMARY.md. |

The planner simulated Layer 3 without mutation: none of these 3 patches gains a new error in any other layer.

**No production caller depends on stripping.**
- In `src/`, the only caller of `validate_patch` is `hooks.validate_file`, which validates a freshly loaded dict and discards it.
- No critic calls it.
- The planner instrumented `validate_patch` across the whole suite. Only two places produced auto-fixed results: `tests/test_validation.py` (deliberate Layer-3 fixtures) and the 3 integration cases above. `tests/test_generation.py::_run_pipeline`, `tests/test_hooks.py` and `tests/test_codegen.py` never see a removal, so making proposed removals block by default changes none of their outcomes.
- No code anywhere sets `auto_fixed=True` except Layer 3. `code_validation` passes it through, always False.

**Existing tests that encode the old destructive contract** (must be rewritten, and they go red against old code):
- `TestLayer3ConnectionBounds`: `test_outlet_out_of_bounds_auto_fixed`, `test_inlet_out_of_bounds_auto_fixed`, `test_auto_fixed_connections_removed`.
- `TestLayer3SignalTypes::test_signal_to_control_only_inlet_detected`.
- `TestRoleAwareValidation`: `test_status_to_signal_emits_use_snapshot`, `test_trigger_to_signal_emits_use_sig`, `test_data_list_to_signal_emits_role_mismatch`, `test_trigger_to_float_warning_preserves`, `test_list_to_float_warning_bach_hint`, `test_audio_to_control_legacy_branch_runs`, `test_severity_auto_fix_contract`, `test_sfplay_done_bang_into_signal_still_removed`.
- `TestLayer3OverrideGuard`: `test_overridden_msp_object_auto_removes`, `test_non_msp_object_unchanged`.
- `TestHasBlockingErrors` and `TestValidationResult` keep passing unchanged, because the legacy `auto_fixed` field and its semantics are retained (S4).
- `test_role_tier_table_excludes_audio_keys` reads only the table's keys; it stays valid.

**DB facts for containers** (from `ObjectDatabase().lookup`):
- `poly~`: inlet 0 `signal:false`.
- `mc.poly~`: inlet 0 `signal:false`, outlet 0 role `status`.
- `pfft~`: both inlets `signal:false`, outlet 0 role `status`.
- `rnbo~`: inlet 0 control.
- `p` / `patcher`: inlet 0 `signal:false`.
- `bpatcher`: maxclass `bpatcher`, and `_extract_object_name` returns None for it.

So today `cycle~ -> poly~/pfft~/p` is stripped, and so is `pfft~` or `mc.poly~` outlet 0 into a signal inlet (role `status`).

**`tapin~` / `tapout~`:** tapin~ outlet 0 has role `status`; tapout~ inlet 0 is `signal/float` with `signal:true`. So the cord hits the `(status, signal)` tier row.

**`relationships.json`:**
- It is `{"_comment", "pairs": [{"objects": [...], "relationship", "note"}]}`.
- It has 44 entries. One is a group of 3: `pfft~`, `fftin~`, `fftout~`.
- No field gives a direction.
- **Nothing in `src/` loads it today.**
- `aliases.json` maps `s` -> `send` and `r` -> `receive`.

**`ObjectDatabase(db_root=<empty dir>)`** constructs without error; `lookup` returns None.

**Fixture proven by the planner.** These boxes, built with the test helpers, round-trip `Patcher.from_dict(...).to_dict() == dict`, and `validate_patch` returns identical result reprs for dict and Patcher input:
- `line~` (2 in / 2 out, outlettype `["signal", ""]`) -> `print` (1 in / 0 out): legacy signal into a control-only inlet;
- `cycle~ 440` outlet 2 -> `*~ 0.5`: out-of-bounds outlet;
- `cycle~ 440` outlet 0 -> `*~ 0.5`: valid.
</observed_facts>

<settled_decisions>
Resolved at planning, from the Q1 spec and the A1/A2/A8 fix columns. Don't re-litigate them. If something live contradicts one, stop and ask (rule 7).

- **S1: Removal key.** `proposed_removal` is a 4-tuple `(src_id, src_outlet, dst_id, dst_inlet)`, built by one private helper `_line_key(patchline)`. The helper treats a non-list `source`/`destination` as empty and pads missing elements with None. A malformed line (`source == ["obj-1"]`) therefore keys as `("obj-1", None, "obj-2", 0)`, and `apply_fixes` matches dict lines with the same helper. Scope is the top-level patcher only, the same as Layer 3 today. Q19 adds paths later.
- **S2: Which findings carry a proposed removal.** Exactly the four existing Layer-3 error kinds, each at level `error`:
  - malformed patchline;
  - cord to or from a missing box;
  - outlet index out of bounds;
  - inlet index out of bounds;
  - plus the legacy "Signal outlet to control-only inlet" for a non-container, non-known-pair destination.
  Their message suffix becomes `-- proposed removal (not applied; see apply_fixes)`. Role-tier findings never carry one.
- **S3: Check order inside `_validate_connections`.** For each well-formed cord whose boxes both exist:
  - (a) bounds checks. These still apply to containers and known pairs.
  - (b) If both boxes resolve to names and `db.is_known_pair(src_name, dst_name)` is true, skip all type and role checks: no finding.
  - (c) If the destination is a container, skip all type and role checks: no finding.
  - (d) If the source is a container, skip the role dispatch only. The legacy outlettype check still runs, because the spec says only "no outlet signal_role".
  - (e) Role dispatch.
  - (f) The legacy signal / "Unverified outlet types" branch, unchanged apart from S2.
- **S4: `ValidationResult`.** Add slot and keyword `proposed_removal=None`, coercing a list to a tuple. Keep the `auto_fixed` slot and constructor keyword for back-compatibility (`code_validation`, tests and external callers construct it), but `validate_patch` never sets it True. `__repr__` is unchanged (`test_repr_format` pins it).
- **S5: `has_blocking_errors(results, is_new=True)`.** Only results at level `error` count:
  - an error with `proposed_removal` blocks when `is_new` is True, the default, so an existing caller can't silently pass;
  - with `is_new=False` (the edit path) it is reported but not blocking;
  - an error with `auto_fixed=True` and no `proposed_removal` stays non-blocking (legacy);
  - every other error blocks.
  The spec says "blocking for new patches". The default of True is the only reading under which un-updated callers stop passing silently. Q7 later adds the HEAD diff for edits.
- **S6: `apply_fixes(patch, results)`.**
  - It accepts a dict or a Patcher.
  - It collects the distinct `proposed_removal` keys from `results`, in order, and removes every top-level line whose key matches. For a dict it uses slice-assignment on `patch["patcher"]["lines"]`, so caller references stay valid. For a Patcher it filters `patch.lines` by `(source_id, source_outlet, dest_id, dest_inlet)`.
  - It returns the list of keys that actually matched at least one line, each once and in order.
  - It mutates only on this explicit call. It is a no-op returning `[]` when nothing is proposed, nothing matches, or the dict lacks `patcher.lines`.
  - Its docstring tells callers to re-run `validate_patch` afterwards.
  - It is exported from `src/maxpat/__init__.py`.
- **S7: Containers.** `_CONTAINER_NAMES = frozenset({"p", "patcher", "bpatcher", "poly~", "mc.poly~", "pfft~", "rnbo~"})`, exactly the spec list. `_is_container_box(box)` is True when any of these holds:
  - `isinstance(box.get("patcher"), dict)` (any embedded patcher: p, gen~, rnbo~, bpatcher with embed);
  - maxclass is `patcher` or `bpatcher`;
  - maxclass is `newobj` and the first token of `text` is in `_CONTAINER_NAMES`.
- **S8: Role tier.** All six `_ROLE_TIER_TABLE` rows become `("warning", suggestion)` 2-tuples, and the keys are unchanged (the audio-key invariant test stays valid). `_classify_role_mismatch` returns `(level, message) | None`. The caller appends `('<src_id>' outlet N -> '<dst_id>' inlet M) -- connection kept` to the message. The tier result stays final: skip the legacy branch for that cord, so the D-02 separation is preserved. Update the table's header comment (A1: role mismatches warn, never remove).
- **S9: Known pairs.**
  - `ObjectDatabase._load` reads `relationships.json` if it exists, after aliases load. Every 2-combination of distinct alias-canonical names in each `objects` list is stored as a `frozenset` in `self._known_pairs`, which is initialised in `__init__` before `_load`.
  - `is_known_pair(a, b) -> bool` canonicalises both names through aliases. It is unordered, because the file has no direction field, and it returns False for `a == b`.
  - The skip covers Layer 3 type/role checks only, never bounds.
- **S10: Docs scope (rule 8).**
  - Edit only these:
    - the Output Protocol (New Patches) block in `max-patch-agent/SKILL.md` (lines ~314-320);
    - steps 3 and 7 of the Output Protocol (New Patches) block in `max-dsp-agent/SKILL.md` (lines ~273 and ~277);
    - the `validation.py` module and function docstrings;
    - the stale "validate_patch mutates the dict" comment in `tests/test_round_trip.py` (around lines 341-342).
  - Don't edit; list in SUMMARY.md as doc impact instead:
    - TECHNICAL.md:52/404/428 (still says auto-fix removes and that auto-fixed errors don't block);
    - CLAUDE.md:197 ("gets stripped by validation");
    - `max-patch-agent/SKILL.md:46` (capability list lacks `apply_fixes`);
    - `max-critic/SKILL.md:49`, `references/shared-capabilities.md:135`, `.claude/commands/max-iterate.md:106` and `.claude/commands/max-build.md:30/58` (still correct for Patcher input, but they don't mention proposed removals);
    - the user memory entry `feedback_validate_mutates.md` (now obsolete). The user retires it; the executor must not touch memory files.
- **S11: Test placement.** New Q1 contract tests go in a new `tests/test_validation_nondestructive.py`, which reuses `_make_box` / `_make_line` / `_make_patch_dict` by `from tests.test_validation import ...`. If that import path fails under the repo's pytest config, copy the three helpers instead. It has a module-scoped `db` fixture. Old-contract tests are rewritten in place in `tests/test_validation.py`, renamed where the name states the old behaviour.
- **S12: Mixer-strip review xfail.**
  - `_make_review_params` applies `pytest.mark.xfail(reason=..., strict=True)`.
  - The `_REVIEW_XFAILS` reason is rewritten to the blocker that fires today: `Fan-out without trigger: '+' (obj-14) outlet 0 -> selector~ obj-15/obj-16`, a critic-precision false positive owned by Q3. Strict means Q3 must delete this entry when it passes.
  - Re-run `review_patch` on the mixer-strip first. If it no longer produces any blocker, delete the entry instead.
  - Do not allowlist it.
- **S13: Fallback for the 3 strips (expected unused).** If, after Task 1, any of the 3 still has a proposed removal and the cause is DB data that Q2 owns, mark only that `test_validate_patch_no_errors` case `xfail(strict=True, reason="Q2: <exact DB cause>")` through a `_VALIDATE_XFAILS` dict. Never allowlist it. Record it in SUMMARY.md.
</settled_decisions>

<tasks>

<task type="tracer" tdd="true">
  <name>Task 1: Pure Layer 3 end-to-end: proposed removals, apply_fixes, blocking for new patches, containers, warning-only roles, integration gate</name>
  <files>src/maxpat/validation.py, src/maxpat/__init__.py, tests/test_validation_nondestructive.py, tests/test_validation.py, tests/test_integration_patches.py</files>
  <read_first>.planning/reviews/2026-10-11-repo-review.md (lines 50-61), src/maxpat/validation.py (ranges in context), tests/test_validation.py (ranges in context), tests/test_integration_patches.py</read_first>
  <behavior>
    - Test 1 (purity, A2): validate the observed_facts fixture (line~->print, cycle~ outlet 2 -> *~, cycle~ -> *~). The dict deep-equals its deepcopy taken before; a Patcher built by `Patcher.from_dict(deepcopy, db=db)` still has 3 lines, and its `to_dict()` equals the pre-validation `to_dict()`.
    - Test 2 (identity, A2): dict input and Patcher input give identical lists of `(r.layer, r.level, r.message, r.proposed_removal)`.
    - Test 3: the out-of-bounds outlet result is level error with `proposed_removal == ("obj-3", 2, "obj-4", 0)` and the text `proposed removal` in its message. An out-of-bounds inlet (`cycle~` -> `*~` inlet 5) proposes `("obj-3", 0, "obj-4", 5)`. line~->print proposes `("obj-1", 0, "obj-2", 0)`. No result proposes the valid cycle~->*~ cord.
    - Test 4: a malformed line with source `["obj-1"]` yields an error proposing `("obj-1", None, "obj-2", 0)`, and `apply_fixes` removes that line from the dict.
    - Test 5: `ValidationResult("json", "error", "m").proposed_removal is None`, and a list argument is stored as a tuple.
    - Test 6 (`apply_fixes` dict): it returns exactly the 2 proposed keys, the dict keeps only the valid cord, a re-validation has no proposed removals, and a second `apply_fixes` with the same results returns `[]`.
    - Test 7 (`apply_fixes` Patcher): the same on a Patcher; `len(p.lines) == 1` afterwards. Results that carry only warnings give `[]` and leave the input unchanged.
    - Test 8 (`has_blocking_errors`):
      - fixture results: True with the default and with `is_new=True`; False with `is_new=False` when every error carries a proposed removal;
      - a plain `ValidationResult("objects", "error", "unknown")` blocks under both settings;
      - a legacy `auto_fixed=True` error without a proposal does not block.
    - Test 9 (containers, A1): parametrize over these `cycle~ 440` outlet 0 -> container inlet 0 cases:
      - `poly~ voice 4`, `mc.poly~ voice 4`, `pfft~ fx 1024`, `rnbo~`;
      - `p synth` with an embedded `{"boxes": [], "lines": []}` patcher;
      - `patcher synth` with an embedded patcher;
      - a maxclass `bpatcher` box;
      - a synthetic newobj `print` that carries an embedded patcher (this proves the embedded-patcher rule independently of the name list).
      Each case: no result with layer `connections`, the cord is present, and the dict is unchanged.
    - Test 10: container sources `pfft~ fx 1024` and `mc.poly~ voice 4` (outlettype `["signal"]`) outlet 0 -> `*~ 0.5` inlet 0 produce no `connections` result.
    - Test 11: `cycle~` -> `p synth` (numinlets 1) inlet 3 is still proposed for removal (bounds before exemptions).
    - Test 12 (role, A1): monkeypatch `db.get_signal_role` so it returns `status` for source `status_x`, then connect `status_x` -> `*~ 0.5` inlet 0.
      - Exactly one connections result: level warning, `proposed_removal is None`, and a message containing `use snapshot~`, `'obj-1'` and `'obj-2'`.
      - The cord is kept.
      - Every `_ROLE_TIER_TABLE` value has level `warning`.
    - Test 13 (committed strips, A1/A8): parametrize these over `json.load` of each file (read only):
      - `("patches/mixer/generated/mixer-strip.maxpat", "obj-15", 0, "obj-37", 0)`;
      - `("patches/terrain-synth/generated/terrain-voice.maxpat", "obj-16", 0, "obj-60", 0)`;
      - `("patches/scala-synth/generated/scala-synth-voice.maxpat", "obj-1", 0, "obj-3", 0)`.
      Each case: the dict is unchanged, no result has a `proposed_removal`, and the cord is present. For terrain-voice there is also no warning containing `Unterminated signal chain: '*~' (obj-16)`.
  </behavior>
  <action>
    Implement A2 and the A1 API part, per S1-S8, S11-S13.

    Step 0, baseline (rule 4). Before touching code, set `Q=.planning/quick/261012-bii-implement-q1-in-planning-reviews-2026-10` and run:
    - `git rev-parse HEAD > $Q/base-sha.txt`;
    - `git stash list | wc -l > $Q/stash-count-before.txt`;
    - `python3 -m pytest -q -p no:cacheprovider -rf 2>&1 | grep -E '^(FAILED|[0-9]+ (passed|failed))' | sed 's/ - .*//' > $Q/baseline-pytest.txt`.
    Confirm that the failing set is exactly the 3 allowed `test_review_patch_no_blockers` cases. If it isn't, record the extra failures in SUMMARY.md and treat them as baseline. Never stage these three files in a task commit.

    RED:
    1. Create `tests/test_validation_nondestructive.py` with Tests 1-13 from `<behavior>`, grouped in classes: TestPurity, TestProposedRemoval, TestApplyFixes, TestHasBlockingErrorsQ1, TestContainers, TestRoleMismatchWarns, TestCommittedStrips. Import `apply_fixes` from `src.maxpat.validation`, and also assert that `from src.maxpat import apply_fixes` works.
    2. Rewrite the old-contract tests in `tests/test_validation.py` listed in observed_facts:
       - Replace every `r.auto_fixed` filter for connection removals with `r.proposed_removal is not None`.
       - Replace every "lines removed" assertion with "lines unchanged (same length) plus the expected key proposed".
       - For the three tier-error tests (status / trigger / data-list into signal), assert level `warning`, `proposed_removal is None` and the cord kept.
       - In the two float-warning tests, swap `auto_fixed is False` for `proposed_removal is None`.
       - Rename `test_severity_auto_fix_contract` to `test_role_tier_contract_warns_never_removes`, asserting warning plus no proposal for both cases.
       - Rename `test_sfplay_done_bang_into_signal_still_removed` to `test_sfplay_done_bang_into_signal_still_flagged`: the cord is kept, a `trigger outlet` warning is present, and nothing is proposed.
       - Rename the `*_auto_fixed` and `*_auto_removes` / `*_connections_removed` tests to `*_proposed` / `*_proposes_removal` / `test_invalid_connection_kept_and_proposed`.
       - Update the TestRoleAwareValidation class docstring to the new tier contract.
    3. In `tests/test_integration_patches.py::test_validate_patch_no_errors`, fail on every result where `r.level == "error" or r.proposed_removal is not None`. Mention proposed removals in the assertion message. Per S12, make `_make_review_params` apply `strict=True` and rewrite the mixer-strip `_REVIEW_XFAILS` reason, after re-running `review_patch` on the mixer-strip to confirm the current blocker.
    4. Run the three test files and confirm they are red for the expected reasons (AttributeError / ImportError on the new API; lines removed; level error). Record the red counts for SUMMARY.md.

    GREEN, in `src/maxpat/validation.py`:
    - (a) S4 `ValidationResult` slot and keyword.
    - (b) Private `_line_key` (S1), plus `_CONTAINER_NAMES` and `_is_container_box` (S7).
    - (c) Rewrite `_validate_connections`. It keeps no removal index list and never writes to `patch_dict`. Each S2 error carries `proposed_removal=_line_key(...)` (or the explicit 4-tuple) and the new message suffix. Apply the S3 order. Leave step (b) of S3 for Task 2: Task 2 inserts the known-pair skip at that position.
    - (d) S8 role tier: table values, `_classify_role_mismatch` return shape, the message suffix with cord ids, and an updated header comment.
    - (e) Add `apply_fixes` per S6 next to `has_blocking_errors`.
    - (f) Implement S5 `has_blocking_errors(results, is_new=True)` with an updated docstring.
    - (g) Rewrite the module docstring and the `_validate_connections` docstring to describe the pure contract. Layer 3 reports and never removes; removals are applied only by `apply_fixes`; proposed removals block new patches.

    In `src/maxpat/__init__.py`, import `apply_fixes` with `validate_patch` / `has_blocking_errors` and add it to `__all__` under "# Patch validation".

    Don't change Layers 1, 2, 4 and 5. Don't change the "Unverified outlet types" warning path beyond S3 ordering. Don't touch DB data (that is Q2).

    Re-run until green. Then run the integration file. All `test_validate_patch_no_errors` cases must pass with no xfail (S13 is the fallback only). The mixer-strip review case must report XFAIL (strict). The 3 allowed review failures are unchanged.

    Commit with explicit paths only: `git add src/maxpat/validation.py src/maxpat/__init__.py tests/test_validation_nondestructive.py tests/test_validation.py tests/test_integration_patches.py`. Then run `git commit -m "fix(validation): non-destructive validate_patch -- proposed removals, apply_fixes, containers, warning-only roles (Q1 A2/A1/A8)" -- <same paths>`.
  </action>
  <verify>
    <automated>python3 -m pytest -q -p no:cacheprovider tests/test_validation_nondestructive.py tests/test_validation.py</automated>
    <automated>python3 -m pytest -q -p no:cacheprovider -rxX tests/test_integration_patches.py -k "test_validate_patch_no_errors or mixer-strip" 2>&1 | tail -4</automated>
    <automated>python3 -c "import ast,sys; [ast.parse(open(f).read(), filename=f, feature_version=(3, 10)) for f in sys.argv[1:]]; print('PY310-SYNTAX-OK')" src/maxpat/validation.py src/maxpat/__init__.py tests/test_validation_nondestructive.py tests/test_validation.py tests/test_integration_patches.py</automated>
    <automated>Q=.planning/quick/261012-bii-implement-q1-in-planning-reviews-2026-10; python3 -m pytest -q -p no:cacheprovider -rf 2>&1 | grep '^FAILED' | sed 's/ - .*//' | sort | diff <(grep '^FAILED' $Q/baseline-pytest.txt | sort) - && echo SUITE-AT-BASELINE</automated>
  </verify>
  <done>
    - The new test file and the rewritten `tests/test_validation.py` pass, and were recorded red first.
    - Every `test_validate_patch_no_errors` case passes, counting proposed removals as failures, with no xfail and no allowlist.
    - The mixer-strip review case reports XFAIL under `strict=True` with an accurate reason.
    - The failing set equals the baseline.
    - One commit containing exactly the 5 listed paths.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Never flag relationships.json pairs (tapin~ -> tapout~): ObjectDatabase.is_known_pair plus the Layer 3 skip</name>
  <files>src/maxpat/db_lookup.py, src/maxpat/validation.py, tests/test_validation_nondestructive.py</files>
  <read_first>src/maxpat/db_lookup.py (lines 72-135), .claude/max-objects/relationships.json (first 25 lines only), src/maxpat/validation.py (_validate_connections as rewritten in Task 1)</read_first>
  <behavior>
    - Test 14: in a dict with `tapin~ 1000` (numinlets 1, numoutlets 1, outlettype `["tapconnect"]`) -> `tapout~ 500` (numinlets 1, numoutlets 1, outlettype `["signal"]`) outlet 0 -> inlet 0, using the real DB with no monkeypatch, there is no result with layer `connections`, the cord is kept, and the dict is unchanged. This is red after Task 1, because the `(status, signal)` tier warning fires.
    - Test 15:
      - `db.is_known_pair("tapin~", "tapout~")` and `db.is_known_pair("tapout~", "tapin~")` are True;
      - `("pfft~", "fftin~")` and `("fftin~", "fftout~")` are True (the group of 3 expands to all pairs);
      - `("s", "r")` is True (alias-canonical send/receive);
      - `("cycle~", "dac~")` and `("tapin~", "tapin~")` are False.
    - Test 16: `tapin~ 1000` outlet 3 -> `tapout~ 500` inlet 0 is still an error with `proposed_removal == ("obj-1", 3, "obj-2", 0)` (bounds before the known-pair skip).
    - Test 17: `ObjectDatabase(db_root=tmp_path).is_known_pair("tapin~", "tapout~") is False` and does not raise when relationships.json is absent.
  </behavior>
  <action>
    Implement the Q1 "Known pairs" bullet per S9 and S3(b).

    RED: add Tests 14-17 to `tests/test_validation_nondestructive.py` as a TestKnownPairs class. Run them and confirm they are red: Test 14 by the tier warning, and Tests 15/17 by the missing method.

    GREEN:
    - In `src/maxpat/db_lookup.py`:
      - initialise `self._known_pairs: set[frozenset[str]] = set()` in `__init__` before `self._load(db_root)`;
      - in `_load`, after aliases are loaded, read `db_root / "relationships.json"` only if it exists, and for each entry of its `pairs` list add a `frozenset` for every `itertools.combinations` 2-subset of distinct alias-canonical names from `objects`;
      - add a public `is_known_pair(self, a: str, b: str) -> bool` with a docstring (unordered; the source is relationships.json; it exempts Layer 3 type/role checks only).
    - In `src/maxpat/validation.py::_validate_connections`, insert step S3(b) right after the bounds checks and before the container and role checks. When `_extract_object_name` gives non-None names for both boxes and `db.is_known_pair(src_name, dst_name)` is true, emit nothing and move to the next cord.
    - Add one line to the `_validate_connections` docstring describing the exemption.

    Don't edit `relationships.json`. Don't change bounds checks.

    Re-run until green. Commit with explicit paths: `git add src/maxpat/db_lookup.py src/maxpat/validation.py tests/test_validation_nondestructive.py`, then `git commit -m "fix(validation): never flag relationships.json pairs such as tapin~ -> tapout~ (Q1 A1)" -- <same paths>`.
  </action>
  <verify>
    <automated>python3 -m pytest -q -p no:cacheprovider tests/test_validation_nondestructive.py tests/test_validation.py tests/test_db_lookup.py</automated>
    <automated>python3 -c "import ast,sys; [ast.parse(open(f).read(), filename=f, feature_version=(3, 10)) for f in sys.argv[1:]]; print('PY310-SYNTAX-OK')" src/maxpat/db_lookup.py src/maxpat/validation.py tests/test_validation_nondestructive.py</automated>
    <automated>Q=.planning/quick/261012-bii-implement-q1-in-planning-reviews-2026-10; python3 -m pytest -q -p no:cacheprovider -rf 2>&1 | grep '^FAILED' | sed 's/ - .*//' | sort | diff <(grep '^FAILED' $Q/baseline-pytest.txt | sort) - && echo SUITE-AT-BASELINE</automated>
  </verify>
  <done>
    - Tests 14-17 pass, and were recorded red first.
    - tapin~ -> tapout~ produces no connection finding, while bounds on known pairs are still enforced.
    - The failing set equals the baseline.
    - One commit containing exactly the 3 listed paths.
  </done>
</task>

<task type="auto">
  <name>Task 3: Skill protocols validate a deepcopy and treat proposed removals as inspect, don't save; stale comment; final gates and SUMMARY inputs</name>
  <files>.claude/skills/max-patch-agent/SKILL.md, .claude/skills/max-dsp-agent/SKILL.md, tests/test_round_trip.py</files>
  <read_first>.claude/skills/max-patch-agent/SKILL.md (lines 312-330), .claude/skills/max-dsp-agent/SKILL.md (lines 268-290), tests/test_round_trip.py (lines 328-356)</read_first>
  <action>
    Implement the Q1 "Skill update" bullet per S10. Edit only the ranges named here (rule 8).

    1. In `.claude/skills/max-patch-agent/SKILL.md`, "Output Protocol (New Patches)", steps 3-6 (around lines 317-320):
       - Step 3 validates a copy: `patch_dict = patcher.to_dict()`, then `results = validate_patch(copy.deepcopy(patch_dict), db=patcher.db)`. Note that validation never mutates its input, so the deepcopy is defense in depth.
       - Add a step saying proposed removals mean inspect, don't save. If `has_blocking_errors(results, is_new=True)` is True, or any result has `proposed_removal` set, do NOT save. Inspect each `(src_id, outlet, dst_id, inlet)`:
         - a real wiring mistake: fix the build and re-validate;
         - a validator false positive: keep the cord and report the checker gap.
         Call `apply_fixes(patch_dict, results)` only when removal is explicitly wanted, then re-validate.
       - The save step runs only after that gate passes.
       - Renumber the steps; keep the rest of the block's wording.
    2. In `.claude/skills/max-dsp-agent/SKILL.md`, "Output Protocol (New Patches)":
       - Step 3 (around line 273) validates `copy.deepcopy(patch_dict)`, where `patch_dict = patcher.to_dict()`, with `db=patcher.db`. Add the same inspect-don't-save sentence for proposed removals.
       - Step 7 (around line 277) saves via `save_patch_roundtrip(patch_dict, path)` or `write_gendsp()` only when `has_blocking_errors(results, is_new=True)` is False.
    3. In `tests/test_round_trip.py`, `test_unknown_keys_survive_round_trip_and_validation` (around lines 341-342): reword the comment that claims validate_patch strips lines. It should say validation is pure and the deepcopy guards the pristine comparison. Keep every assertion. This is a comment-only change.
    4. Final gates:
       - Run the full suite and diff it against the baseline.
       - Run `python3 -m pytest -q -p no:cacheprovider -rxX tests/test_integration_patches.py` and capture the XFAIL line for the mixer-strip.
       - Confirm that `git diff --name-only $(cat .planning/quick/261012-bii-implement-q1-in-planning-reviews-2026-10/base-sha.txt)..HEAD -- patches/` is empty for this plan's commits. Any lines present must come only from the concurrent barnett-dbap instance; check with `git log --format='%h %s' <base>..HEAD -- patches/`.
       - Confirm that `git stash list | wc -l` equals the recorded `stash-count-before.txt`.
    5. Commit with explicit paths: `git add .claude/skills/max-patch-agent/SKILL.md .claude/skills/max-dsp-agent/SKILL.md tests/test_round_trip.py`, then `git commit -m "docs(skills): validate a deepcopy; proposed removals are inspect, don't save (Q1 A2)" -- <same paths>`.

    Write the SUMMARY.md inputs (see `<output>`).
  </action>
  <verify>
    <automated>grep -c "deepcopy" .claude/skills/max-patch-agent/SKILL.md .claude/skills/max-dsp-agent/SKILL.md</automated>
    <automated>grep -c "proposed_removal\|proposed removal" .claude/skills/max-patch-agent/SKILL.md .claude/skills/max-dsp-agent/SKILL.md</automated>
    <automated>python3 -m pytest -q -p no:cacheprovider tests/test_agent_skills.py tests/test_claude_md.py tests/test_round_trip.py</automated>
    <automated>Q=.planning/quick/261012-bii-implement-q1-in-planning-reviews-2026-10; python3 -m pytest -q -p no:cacheprovider -rf 2>&1 | grep '^FAILED' | sed 's/ - .*//' | sort | diff <(grep '^FAILED' $Q/baseline-pytest.txt | sort) - && echo SUITE-AT-BASELINE</automated>
  </verify>
  <done>
    - Both skill protocol blocks validate a `copy.deepcopy` and gate the save on proposed removals / `has_blocking_errors(results, is_new=True)`.
    - The round-trip comment is accurate.
    - The skill/CLAUDE.md/round-trip tests pass.
    - The full-suite failing set equals the baseline.
    - No `patches/` path appears in this plan's commits, and the stash count is unchanged.
    - One commit containing exactly the 3 listed paths.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| `.maxpat` JSON -> `validate_patch` | Patches come from MAX saves, collaborators, and generated code. They may be malformed. The validator must read them and never rewrite them. |
| Validation results -> save decision | Agents and skills decide whether to write to disk based on `has_blocking_errors` / `proposed_removal`. A silent pass ships a broken or stripped patch. |
| Executor -> git index on shared `main` | A concurrent instance commits `patches/barnett-dbap/`. Unrelated dirty files are present. |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-bii-01 | Tampering | `validate_patch` / `_validate_connections` on caller-owned data | high | mitigate | Layer 3 keeps no removal index and never writes the input (S1-S3). Task 1 Tests 1-2 assert deep equality for dict input and unchanged lines for Patcher input. Test 13 does the same on the 3 committed patches. |
| T-bii-02 | Tampering | `apply_fixes` | medium | mitigate | Removes only top-level lines whose 4-tuple key equals a result's `proposed_removal`. Returns the matched keys. Task 1 Tests 6-7 prove that valid cords survive, that a second call is a no-op, and that warning-only results change nothing. |
| T-bii-03 | Repudiation | `has_blocking_errors` silent pass | high | mitigate | A proposed removal blocks when `is_new=True` (the default, S5), so un-updated callers stop passing silently (Test 8). `test_validate_patch_no_errors` fails on any proposed removal in a committed patch (Task 1). |
| T-bii-04 | Elevation of Privilege | container and known-pair exemptions bypassing checks | medium | mitigate | Bounds checks run before both exemptions (S3). Test 11 (`p` inlet 3) and Test 16 (tapin~ outlet 3) assert that removals are still proposed. |
| T-bii-05 | Denial of Service | malformed patchlines | low | mitigate | `_line_key` treats a non-list source/destination as empty and pads with None (S1). Test 4 covers a 1-element source through validate and `apply_fixes`. |
| T-bii-06 | Repudiation | git staging next to a concurrent instance | medium | mitigate | Explicit-path `git add` and `git commit -- <paths>` per task; no stash, `-A` or `.` (rule 5). Task 3 checks that no `patches/` path is in this plan's commits and that the stash count is unchanged. |
| T-bii-SC | Tampering | npm/pip/cargo installs | high | mitigate | No package-manager install in this plan. Only the standard library (`copy`, `itertools`, `json`, `ast`) and in-repo imports are used, so no Package Legitimacy Audit is required. |
</threat_model>

<source_audit>
Sources: the fix-plan Q1 section, review findings A1/A2/A8, and the orchestrator's planning notes. This quick task has no ROADMAP phase, CONTEXT.md or RESEARCH.md.

| Source item | Covered by | Status |
|---|---|---|
| GOAL: non-destructive `validate_patch` | Tasks 1-3 | COVERED |
| No mutation; dict and Patcher behave identically | Task 1 (S1-S4, Tests 1-2) | COVERED |
| Proposed removals as data (`proposed_removal` tuple) | Task 1 (S1, S2, Tests 3-5) | COVERED |
| `apply_fixes(patch, results)` | Task 1 (S6, Tests 6-7) | COVERED |
| Containers: p, patcher, bpatcher, poly~, mc.poly~, pfft~, rnbo~, any embedded patcher; no outlet signal_role | Task 1 (S7, S3, Tests 9-11) | COVERED |
| Role mismatch becomes a warning, never a removal | Task 1 (S8, Test 12) | COVERED |
| Never flag a `relationships.json` pair (tapin~ -> tapout~) | Task 2 (S9, Tests 14-17) | COVERED |
| `has_blocking_errors` blocks proposed removals for new patches | Task 1 (S5, Test 8) | COVERED |
| Skills: validate a `copy.deepcopy`; proposed removals are inspect, don't save (max-patch-agent:316-320, max-dsp-agent:273,277) | Task 3 | COVERED |
| Integration test fails on any proposed removal in a committed patch (A8) | Task 1 step 3 | COVERED |
| 3 known strips fixed here or in Q2, never allowlisted | Task 1 Test 13: mixer-strip and terrain-voice via containers, scala-synth-voice via warning-only roles (observed_facts table); S13 fallback | COVERED, all in Q1 |
| Mixer-strip xfail `strict=True`, or removed if it no longer applies | Task 1 (S12) | COVERED |
| Tests: Patcher and dict identical, input unchanged; cycle~ -> poly~/pfft~/rnbo~/p keeps its cord; tapin~ -> tapout~ keeps its cord | Tests 1-2, 9, 14 | COVERED |
| Grep every caller so callers that want removals use `apply_fixes` | observed_facts: no `src/` caller depends on stripping; the suite instrumented | COVERED (no caller needs `apply_fixes`) |
| The 9 rules copied into the plan | `<rules>` | COVERED |
| A1 data part: signal:false overrides, `_build_inlet_array`, signal-flip guard test, biquad~, `in`/`peek~` roles, trailing outlets | Q2 | EXCLUDED (scoped to Q2 by the fix plan) |
| Docs outside the named skill lines (TECHNICAL, CLAUDE.md:197, other skills/commands, user memory) | SUMMARY.md doc-impact list (S10, rule 8) | EXCLUDED from edits, reported |
</source_audit>

<verification>
- `python3 -m pytest -q -p no:cacheprovider` before and after (rule 4). The failing set equals `baseline-pytest.txt`: only the 3 allowed `test_review_patch_no_blockers` cases. The pass count rose only by this plan's new tests.
- `test_validate_patch_no_errors` passes for every committed patch, with no xfail and no allowlist entry added.
- `python3 -m pytest -q -p no:cacheprovider -rxX tests/test_integration_patches.py` shows the mixer-strip review case as XFAIL with the new strict reason.
- `git log --format='%h %s' $(cat .planning/quick/261012-bii-implement-q1-in-planning-reviews-2026-10/base-sha.txt)..HEAD` lists exactly 3 commits from this plan, each touching only its task's `<files>`. Any `patches/` commits in that range belong to the concurrent instance.
- `git status --short` still shows `patches/.active-project.json` modified and `.planning/tci-phase2/` untracked, both untouched and unstaged. `git stash list` count is unchanged.
- The Python 3.10 syntax gate passes on every changed `.py` file.
</verification>

<success_criteria>
- A2: `validate_patch` is pure for dict and Patcher input, and the results are identical. `apply_fixes` is the only path that removes cords, and it is exported. Both skills validate a deepcopy and treat proposed removals as inspect, don't save.
- A1 (API): containers accept any cord and carry no outlet role; role mismatches warn; `relationships.json` pairs are never flagged; bounds are still enforced everywhere.
- A8: proposed removals fail the committed-patch integration test; the mixer-strip xfail is strict and accurate.
- The 3 known strips keep their cords with 0 proposed removals, none allowlisted or xfailed.
- No regression: failing set equals baseline, no patch file edited, Python 3.10 syntax clean.
</success_criteria>

<output>
Create `.planning/quick/261012-bii-implement-q1-in-planning-reviews-2026-10/261012-bii-SUMMARY.md` when done. It must include:
- baseline vs final pytest totals and the red counts recorded before each GREEN step;
- for each of the 3 known strips, the path it took (container rule / warning-only role) and its final finding count;
- the Q2 hand-off: scala-synth-voice obj-1 -> obj-3 still emits a role *warning* until Q2 corrects `in` (role -> None) and `peek~` (control inlets). `poly~`/`pfft~` inlet overrides are still `signal:false`; that no longer affects Layer 3, but Q2 repairs them;
- the Q7 hand-off: `has_blocking_errors(is_new=False)` does not block proposed removals; Q7's HEAD diff supplies that gate;
- the S10 doc-impact list (not edited, rule 8), including that the user memory entry `feedback_validate_mutates.md` is now obsolete and the user may retire it;
- any live value that differed from observed_facts;
- rule 9: "Confirm in MAX: none". No patch file or generated output changed; the change only stops the validator from deleting cords.
</output>
