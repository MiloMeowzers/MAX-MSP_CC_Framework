---
phase: quick-261015-nkm
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/maxpat/critics/rnbo_critic.py
  - src/maxpat/critics/structure_critic.py
  - src/maxpat/dsp_roles.py
  - src/maxpat/critics/dsp_critic.py
  - src/maxpat/critics/__init__.py
  - src/maxpat/validation.py
  - src/maxpat/defaults.py
  - src/maxpat/aesthetics.py
  - src/maxpat/critics/layout_critic.py
  - .claude/skills/references/ui-presets.md
  - tests/test_critic_fixes_e5_e8.py
  - tests/test_critics.py
  - tests/test_critics_recursive.py
  - tests/test_aesthetics.py
  - tests/test_integration_patches.py
  - tests/review_blocker_allowlist.json
autonomous: true
requirements: [E5, E6, E7, E8]

estimate:
  tokens: 170000
  raw_tokens: 170000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "RNBO (E8): inside an rnbo~ that has in~ and out~, `param freq 440` + `param freq 220` gives exactly one `Duplicate RNBO param name 'freq'` blocker; `param @name gain` + `param gain 0.5` gives one; `param MyGain 0` gives the snake_case naming warning; `param @min 0` gives no naming or duplicate finding. An inner patcher with out~ and no in~ gives exactly one finding, severity note, starting `rnbo~ '<id>' inner patcher has no in~ object -- `; a missing out~ is still a blocker."
    - "Hot/cold (E5): `review_structure` emits `Hot/cold inlet ordering issue: ` only when the target's hot inlet 0 and a DB-cold inlet get values from one upstream event, and that event's last cold update fires at or after its last hot firing (right-to-left outlet order at the divergence box, PD-1). number -> `unpack 0 0` with outlet 1 -> `+` inlet 0 and outlet 0 -> `+` inlet 1 gives exactly one warning. These give none: the swapped cords; two independent number boxes; p, bpatcher and js targets; storage targets; route/select divergences; a path that enters a box at a cold inlet; Jitter setter hops. The RCC v0.0.7 shape (`t l b` -> ears.slice~) gives only the Q21 `Trigger order: ` blocker (PD-2). Committed hot/cold warnings drop from 143 to 0."
    - "Gain safety (E6): these give no `Unsafe gain source: `: `0, 0.8 2000` -> line~ -> `*~` inlet 1; `64` -> `* 0.01` -> `*~`; a flonum with minimum 0 / maximum 1; ctlin -> `scale 0 127 0. 1.`; ctlin -> scale -> `dbtoa` -> line~ (an unknown box stops the trace, PD-4). These give exactly one blocker each, naming the inlet and the range: ctlin -> `scale 0 127 0. 4.`; ctlin -> `*~` inlet 0 with audio on inlet 1; a default-range live.dial; a float dial of size 121 and mult 0.01 (1.21). The text says ` via line~` only when the path crosses a line~."
    - "DB-driven sets (E6, PD-5): `src/maxpat/dsp_roles.py` derives these from the object DB. Gain stages {*~, mc.*~, gain~, mc.gain~, live.gain~, mc.live.gain~}. Output terminals {dac~, mc.dac~, ezdac~, mc.ezdac~, plugout~}. Chain terminals: the output terminals plus {send~, mc.send~, out~, mc.out~}. validation.py and dsp_critic.py both call it, module-qualified. cycle~ -> live.gain~ -> dac~ gives no `Missing gain staging`; cycle~ -> mc.dac~ and cycle~ -> plugout~ give one each; the `add_m4l_gen_synth` output has no `Unterminated signal chain` warning."
    - "Contrast (E7, PD-6): the critic reads missing textcolor as the theme text color 0.85 and a patcher with no bg key as the theme canvas 0.235. The visible panel is the topmost one containing the box: foreground-layer panels before `background: 1` panels, in box order within each layer. Fills with alpha below 0.5 are skipped. A box's own visible fill is its background, and a newobj/message/umenu with no fill attribute reads against 0.172. The amplitude-follower obj-16/20/22/23 shape warns at 2.30:1 and the kicksynth obj-154 shape at 1.24:1. A plain comment with no textcolor on the 0.333 or 0.235 canvas gives none. `ensure_text_contrast` keeps an explicit textcolor that already passes (the section header keeps header_color), still fills a missing one, and falls back to black or white only when both dark and light fail (mid-gray 0.5 panel -> black). After it runs, review_layout reports no `Low contrast text` warning on the same patch."
    - "Corpus and suite: `Q/triage.py --check` reports mismatch 0 after every task, so no record outside the Q26 kinds changes. SUMMARY gives before/after counts per Q26 kind. Planning expects: hot/cold 143 -> 0, Low contrast warnings 1090 -> 56, trade-off notes 213 -> 209, Unsafe gain 0 -> 1 (slot.maxpat obj-54 -> obj-9 inlet 1, allowlisted under rule 3), RNBO 0 -> 0, Unterminated 7 -> 7. test_calibration_zero_blockers stays green with no allowlist change. The full suite is green against the baseline (4782 passed, 5 xfailed, 1 xpassed) plus the new tests. The only edits to existing tests are the 7 spec-mandated ones in PD-8. There are at least 4 `(Q26)` commits, and none touches patches/."
  artifacts:
    - path: "src/maxpat/dsp_roles.py"
      provides: "DB-driven gain-stage, output-terminal and chain-terminal name sets shared by validation.py and dsp_critic.py"
      contains: "def chain_terminal_names"
    - path: "src/maxpat/critics/structure_critic.py"
      provides: "shared-ancestor hot/cold check (E5) deferring to Q21 trigger-order inside its reach"
      contains: "_check_hot_cold_ordering"
    - path: "src/maxpat/critics/dsp_critic.py"
      provides: "bounds-propagating unsafe-gain trace on both *~ inlets and DB-driven gain staging (E6)"
      contains: "dsp_roles."
    - path: "src/maxpat/aesthetics.py"
      provides: "theme-aware background resolution, z-ordered panel layers, keep-passing text color choice (E7)"
      contains: "def build_panel_layers"
    - path: "src/maxpat/defaults.py"
      provides: "Max 9 theme constants and the visible-fill alpha threshold"
      contains: "MAX_THEME_CANVAS_BG"
    - path: "src/maxpat/critics/rnbo_critic.py"
      provides: "positional param names; missing in~ as a note (E8)"
      contains: "_extract_param_name"
    - path: "tests/test_critic_fixes_e5_e8.py"
      provides: "one test class per Q26 change, plus robustness and purity"
      contains: "class TestHotColdSharedAncestor"
    - path: "tests/review_blocker_allowlist.json"
      provides: "the slot.maxpat unsafe-gain true positive, with its reason"
      contains: "unsafe_gain"
    - path: ".claude/skills/references/ui-presets.md"
      provides: "Text Contrast Resolution matching the new algorithm"
      contains: "MIN_VISIBLE_FILL_ALPHA"
  key_links:
    - from: "src/maxpat/critics/__init__.py"
      to: "src/maxpat/critics/dsp_critic.py"
      via: "review_patch passes its one ObjectDatabase to review_dsp"
      pattern: "review_dsp\\(patch_dict, code_context=code_context, graph=graph, db=db\\)"
    - from: "src/maxpat/validation.py"
      to: "src/maxpat/dsp_roles.py"
      via: "Layer 4 unterminated and gain-staging rules take their sets from dsp_roles(db)"
      pattern: "dsp_roles\\.chain_terminal_names\\("
    - from: "src/maxpat/critics/dsp_critic.py"
      to: "src/maxpat/dsp_roles.py"
      via: "gain staging takes gain stages and output terminals from dsp_roles(db)"
      pattern: "dsp_roles\\.output_terminal_names\\("
    - from: "src/maxpat/critics/layout_critic.py"
      to: "src/maxpat/aesthetics.py"
      via: "critic and generator build panel layers and patcher background through one helper each"
      pattern: "build_panel_layers\\("
    - from: "tests/test_integration_patches.py"
      to: "tests/review_blocker_allowlist.json"
      via: "the unsafe_gain allowlist kind keys on (source_id, gain_id, inlet, path)"
      pattern: "unsafe_gain"
---

<objective>
This plan implements fix-plan Q26 (review findings E5 to E8), the four remaining critic-precision fixes:
- **E5:** hot/cold warns only when the hot and cold inputs share an upstream ancestor.
- **E6:** gain safety parses messages correctly, propagates value bounds, traces both `*~` inlets, and uses DB-driven gain-stage and terminal sets shared with validation.py.
- **E7:** text contrast follows the Max 9 default theme.
- **E8:** the RNBO critic parses positional param names, and a missing in~ becomes a note.

Purpose: the review measured these critics at about 90% noise (E5: 48/63 noise; E7: 247/296 false), while real defects went unreported (E7: amplitude-follower at 2.3:1 and kicksynth at 1.24:1; E6: a 4x `scale` gain). Noise trains the user and the generator loop to ignore findings.

Output:
- the four fixes, plus a new module `src/maxpat/dsp_roles.py`;
- `tests/test_critic_fixes_e5_e8.py`;
- the 7 spec-mandated test edits;
- one rule-3 allowlist entry;
- an updated ui-presets.md;
- Q/triage.py and its reports, which give the before/after finding counts for SUMMARY.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@CLAUDE.md
@.planning/reviews/2026-10-11-fix-plan.md
@.claude/skills/references/severity-contract.md
@src/maxpat/critics/rnbo_critic.py
@src/maxpat/critics/__init__.py

Read only the named parts of these:
- `.planning/reviews/2026-10-11-repo-review.md`: rows E5 to E8 (lines ~116-119) and §1J item 5 (line ~213).
- `src/maxpat/critics/structure_critic.py`:
  - 1-160: module docstring, constants, review_structure, `_LazyDB`;
  - `_is_jitter_setter_hop` (~229);
  - `_check_hot_cold_ordering` (~405-496);
  - `_box_label` (~507);
  - the Q21 block (~700-857: `_ORDER_*` sets, `_is_order_hop`, `_inlet_is_cold`, `_is_order_idiom`, `_check_trigger_order`).
- `src/maxpat/critics/dsp_critic.py`: 1-115 and 230-505.
- `src/maxpat/validation.py`: 55-70 (constants), `_validate_domain_rules` (~1279-1365), `_check_unterminated_chains` and `_check_gain_staging` (~1569-1665).
- `src/maxpat/aesthetics.py`: 1-120 and 222-505.
- `src/maxpat/critics/layout_critic.py`: 1-70 and 323-443.
- `src/maxpat/defaults.py`: 115-170.
- `.claude/skills/references/ui-presets.md`: 139-168 ("Max 9 Theme Defaults" and "Text Contrast Resolution").
- Tests:
  - `tests/test_critics.py`: `_hot_cold_ordering_issue_patch` (~449), `test_hot_cold_ordering_detected` (~649), class TestDSPCriticGainSafety (~1356-1742).
  - `tests/test_critics_recursive.py`: helpers 40-135 (`_box`, `_line`, `_container`, `_inner`, `_patch`, `_hot_cold_content`); the parity table and test (~669-718); TestRnboNested (~820-845); TestBundleSweep (~1049).
  - `tests/test_aesthetics.py`: TestEnsureTextContrast (~736-861), TestContrastPrimitives and TestBoxOwnBackground (~1004-1160).
  - `tests/test_integration_patches.py`: 30-120 (allowlist keys) and 230-343.
  - `tests/review_blocker_allowlist.json`.
  - `tests/test_signal_role_migration.py`: 115-140 (`_DSP_CRITIC_MIN_CONSUMER_SITES = 3`).
</context>

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

Additions for this execution environment:
- **Q** = `.planning/quick/261015-nkm-implement-q26-in-planning-reviews-2026-1` (create it with `mkdir -p` if a worktree lacks it). These files go in Q and stay untracked, never staged:
  - the Step-0 files;
  - Q/red-t1.txt, Q/red-t1b.txt, Q/red-t2.txt, Q/red-t3.txt;
  - Q/triage.py and its JSON;
  - Q/final-pytest.txt and Q/q26-commit-files.txt.

  The orchestrator commits PLAN and SUMMARY. Never name a scratch script after a stdlib module.
- **Base.** At planning, local main HEAD = `65b4a894` (Q24 and Q25 landed), and origin/main = `4b2890b8`, 9 commits behind. Q23 (plan 261015-fm1) is planned but NOT executed.
  - **Hard precondition:** `git merge-base --is-ancestor 65b4a894 HEAD` succeeds. If it fails in an agent worktree, the worktree was based on a stale origin/main. HALT and report "push main to origin, then rerun".
  - **Hard precondition:** these hold:
    - `git diff --quiet HEAD --` succeeds over every existing `files_modified` path;
    - `src/maxpat/dsp_roles.py` and `tests/test_critic_fixes_e5_e8.py` do not exist.

    If either fails, HALT and report which.
  - If `(Q23)` commits exist (`git log --oneline --fixed-strings --grep="(Q23)" 65b4a894..HEAD`), record them in SUMMARY. Line numbers in `<context>` will have shifted, and the Step-0 snapshot absorbs Q23's findings. If `walk.message_segments` then exists, use it for comma/semicolon splitting in Task 2 instead of the private splitter.
- **Step 0 (Task 1, before any source edit):**
  - Write `git rev-parse HEAD` to Q/base-sha.txt and `git stash list` to Q/stash-list-before.txt.
  - Run `python3 -m pytest -q -p no:cacheprovider` into Q/baseline-pytest.txt. Expected at 65b4a894: **4782 passed, 5 xfailed, 1 xpassed** (about 90 s). If it differs, record it; do not fix it.
  - Write Q/triage.py to the spec in `<reference_data>`, then run:
    - `python3 Q/triage.py --selftest` (must exit 0);
    - `--base Q/triage-base.json`;
    - `--check Q/triage-base.json Q/triage-step0.json` (must exit 0);
    - `--bundle Q/bundle-base.json`, when /Applications/Max.app exists.

    Record the exit codes and the printed tables in Q/triage-step0.txt.
- **Edit scope.**
  - Only the 16 `files_modified` paths may change, each only in a task whose `<files>` lists it.
  - Never edit `patches/**`, CLAUDE.md, TECHNICAL.md, README.md, any `.claude/**` file other than ui-presets.md, any other `src/` file, or `tools/**`.
  - The only edits allowed to existing tests are the PD-8 list. Any other existing test that fails is a code bug: fix the code, never the test.
- **Commits.** Four commits, each message ending `(Q26)`: Task 1 two (1a RNBO, then 1b hot/cold), Task 2 one (gain safety), Task 3 one (contrast).
- **Context budget (checker scope_sanity).** Each task carries one sizeable feature: Task 1 the hot/cold rewrite (the RNBO fix ahead of it is a ~15-line tracer slice), Task 2 gain safety, Task 3 contrast. Read only a task's own `<read_first>` list; never load another task's source files.
  - Stage with `git add -- <commit files>` and commit with `git commit -m "..." -- <commit files>`.
  - Never `git push` and never rewrite history.
  - A follow-up fix that lands as its own `(Q26)` commit, touching only this plan's files, is kept and explained in SUMMARY.
</rules>

<planner_decisions>
Every decision below is within Claude's discretion: the fix plan leaves it open, no CONTEXT.md exists, and none needs a user decision. Each one was measured at planning with scratch prototypes. The corpus is the 69 committed .maxpat/.maxhelp/.gendsp files; the bundle is the 3139 .maxpat/.maxhelp files of the installed Max 9.2. A temp-worktree run of the full suite with all four prototypes is the source of PD-8.

**PD-1. Hot/cold rule (E5).** Per non-gen scope, control cords only (`Edge.signal` False).
- **Targets.** A box with control cords into inlet 0 and into at least one inlet that `_inlet_is_cold` (DB `hot: false`) marks cold. Check this cheap shape first, before any DB lookup. Skipped targets ("skip p, bpatcher and js targets"):
  - `_ORDER_EXCLUDED_NAMES` (gate/switch family, pak, funnel, and `_ALL_HOT_NAMES`, which holds p, patcher, bpatcher, js, jsui, v8*, node.*, poly~, pfft~, rnbo~, gen~);
  - any box with an embedded patcher (`walk.inner_patcher`);
  - the Q21 storage/idiom targets (`_ORDER_STORAGE_NAMES`, zl reg, `_ORDER_IDIOM_TARGETS`).

  An abstraction or other DB-unknown object has no cold inlet, so it is never a target. The old `~`-name skip is gone: the control inlets of an MSP object (ears.slice~ inlet 1) are checked, and signal cords never count.
- **Upstream sets.** For the hot cords and the cold cords separately, walk upstream from the cord sources (included) over control in-cords. Follow a cord only when:
  - it enters its box at a hot inlet (not `_inlet_is_cold`);
  - it is not a Jitter setter hop (`_is_jitter_setter_hop(src, dst)`);
  - its source is not the target itself.

  Use a visited set. An event that enters a box at a cold inlet does not propagate; without this, notein -> poly inlet 1 makes notein a false shared ancestor (scala-synth).
- **Independent.** No box is in both sets: no finding.
- **Divergence.** For each shared ancestor A, in sorted id order:
  - Skip A when it routes each event to one outlet: route, routepass, select, sel, gate, ggate, gswitch2, split, spray, if (the terrain-source `route backup restore` false positives).
  - Skip A when its outlet order is opaque: `_ALL_HOT_NAMES`, an embedded patcher, or a DB-unknown name (the `p clock` / `p init` false positives in slot.maxpat).
  - Otherwise classify A's control out-cords. A cord reaches a side when it is one of the target's cords on that side, or when it enters, at a hot inlet and not as a Jitter setter hop, a box in that side's upstream set (the target excluded). H = reaches hot only, C = cold only, B = both.
  - **Hazard** when C is non-empty, H or B is non-empty, and min(C outlets) <= min(H ∪ B outlets). Outlets fire right to left, so the lowest outlet fires last. A cold update at a lower outlet than the last hot firing arrives too late. An equal outlet is a fan-out with undefined order.
  - B-only and H-after-B shapes are not hazards: each B wave sets its own cold inlets before firing hot. This keeps simple-fm's init `t b b b b b` clean.
- **Report.** The first hazardous ancestor gives exactly one warning per target.
- **Measured.** Corpus 143 -> 0. The 143 split into:
  - excluded targets: 56;
  - storage/idiom targets: 10;
  - DB-unknown targets: 10;
  - no DB-cold inlet fed: 2;
  - independent, or ordered right to left: 65.

  Bundle 8810 -> 990: 947 same-outlet fan-outs and 43 reversed orders. Bundle cost: 1.8 s.

**PD-2. Q21 boundary (no double report).** Factor Q21's reach loop into `_trigger_reach(scope, t_id)` as a pure refactor (`_check_trigger_order`'s behavior and its tests unchanged).
- Hot/cold skips any target that a trigger in the same scope reaches, directly or through one Q21 hop, at inlet 0 and at a DB-cold inlet. Q21 owns those: it either reports a `Trigger order: ` blocker or exempts the previous-value idiom (`t f f` -> `- 0.`).
- **Measured.** RCC v0.0.7 pre-fix (`git show d407da7b:patches/rhythmic-corpus-chopper/generated/rhythmic-corpus-chopper.maxpat`) gives exactly the Q21 blocker on `[p slicer]` ears.slice~ obj-18 and no hot/cold finding there. Post-fix (3c9452a5) gives neither.
- To compute the skip set, `review_structure` runs `_check_trigger_order` once before hot/cold, keeping the result order unchanged: fan-out, hot/cold, trigger types, `$N` arity, trigger order, uninitialized state.

**PD-3. Same-outlet fan-out stays a hot/cold warning.** The fix-plan rule is literal: the inputs share an ancestor. This also keeps `test_top_level_first_then_preorder`, which pins a fan-out blocker plus a hot/cold warning on `button -> pack 0 0` inlets 0 and 1. The fan-out check still reports it too.

**PD-4. Gain-safety trace (E6).** For each `*~` / `mc.*~` box G and each inlet i in {0, 1}:
- **Seeds.**
  - Every control cord into (G, i). A cord is signal when `src_outlettype[outlet] in _SIGNAL_OUTLET_TYPES`; keep that one-line read shape (see PD-8).
  - Every control cord into inlet 0 of a `line~` whose signal cord feeds (G, i). These seeds carry into_line=True and crossed_line=True.
  - For i == 0, when G has a numeric first argument k and no cord (signal or control) enters inlet 1, start the op chain with multiply-by-k, so `line~` -> `*~ 0.01` is judged as the product.
- **Walk.** Backward BFS. State = (box id, op chain, into_line, crossed_line). Use a visited set; a hop limit of 64 and a cap of 4096 states per (G, i) guarantee termination, even on cycles through `*` boxes. At box B, the first matching rule applies:
  1. **Message box.**
     - Split the text into comma segments. Comma tokens follow `_is_setter_message`'s rule: a `,` token, or a token ending in an unescaped `,`. Ignore everything from the first unescaped `;`, which starts a remote message.
     - A segment whose first atom is neither a number nor `$N` is a command (for example `set`, `stop`) and carries no value.
     - When into_line is set (B feeds line~ directly), only the even positions of each segment are targets; odd positions are ramp times. Otherwise every atom of a value segment counts.
     - Numbers form a constant interval. Each `$N` continues to B's inlet-0 control feeders with into_line=False.
  2. **Bounded source.**
     - slider / dial: value × mult + min. Value is in [0, size−1], or [0, size] with floatoutput 1. Defaults: size 128, mult 1, min 0.
     - number / flonum: [minimum, maximum]. A missing side is assumed 0 or 127, which keeps today's "raw 0-127" meaning; min 0 / max 1 is therefore safe.
     - live.dial / live.slider / live.numbox: `saved_attribute_attributes.valueof.parameter_mmin` / `parameter_mmax`, defaults 0 / 127.
     - kslider, ctlin, notein: [0, 127].

     Non-numeric or bool attribute values fall back to the defaults.
  3. **Op box.** Prepend the op and continue to the inlet-0 control feeders:
     - `* k` or `/ k`, with a numeric first argument (`/ 0` is unknown);
     - `scale a b c d` and `zmap a b c d`, with at least 4 numeric arguments. Linear map; zmap also clamps to [c, d]. A 5th exponent argument is ignored: the endpoints still map to c and d.
     - `clip lo hi`, with at least 2 numeric arguments: clamp.
  4. **expr / vexpr** that matches the existing `_is_normalizer` pattern: safe, stop.
  5. **Pass-through.**
     - trigger / t: only when the followed cord leaves an outlet whose argument is `i`, `f` or `l` (value); continue to inlet-0 feeders. A numeric argument is a constant source. Any other letter stops.
     - f / float / i / int: a numeric argument is a constant source; continue to the feeders of inlets 0 and 1.
  6. **Anything else** stops, with an unknown range and no finding. This includes control `line`, `+`, `pack`, `dbtoa`, arg-less `*`, js and containers.
- **Finding.** When an interval reaches G and max(|lo|, |hi|) > 1.0: one blocker per (source box, G, i), with the text from `<reference_data>`.
- **Measured.**
  - Passing unknown boxes through, as today, gives 5 corpus false positives: mixer-strip dial -> `scale 0 128 -20. 20.` -> dbtoa -> line~ -> `*~` obj-11 and obj-12, and three pack-fed ramp-time values into slot.maxpat `$1 $2 0. $3`. Stopping gives 0 false positives and 1 true positive.
  - The true positive: slot.maxpat dial obj-54 (floatoutput, size 121, mult 0.01, range 0 to 1.21) -> `t f f` obj-166 -> `$1 10` obj-155 -> line~ obj-156 -> `*~` obj-9 inlet 1. It is allowlisted under rule 3 (rhythmic-sampler is not a calibration project). The allowlist supports only fanout and bach_llll kinds today, so Task 2 adds an `unsafe_gain` kind.
  - `gain~`'s own inputs stay unchecked (out of Q26 scope; the review lists it separately).
- **Message splitting.** If Q23 has landed `walk.message_segments`, use it; otherwise add a private splitter.
- **Back-compat.** Keep `_is_normalizer` (tests call it).

**PD-5. DB-driven sets (E6).** The DB has no gain-stage or terminal field. plugout~ cannot be derived as "a sink with no audio outlet", because plugout~.maxref.xml documents two signal pass-thru outlets. So `src/maxpat/dsp_roles.py` holds a small documented base vocabulary and lets the DB decide the rest:
- **Base vocabulary.** GAIN_STAGE_BASES (`*~`, `gain~`, `live.gain~`); OUTPUT_TERMINAL_BASES (`dac~`, `ezdac~`, `plugout~`); ROUTE_TERMINAL_BASES (`send~`, `out~`).
- **Functions.** `gain_stage_names(db=None)`, `output_terminal_names(db=None)` and `chain_terminal_names(db=None)` (output ∪ route) return frozensets.
- **Membership.** Each base and its `mc.` counterpart is kept only when:
  - `db.lookup(name)` is a dict;
  - at least one of its inlets has `signal` True;
  - `db.get_effective_restrictions(name)` is not a non-empty subset of {rnbo, gen}.

  So DB re-syncs that add or drop mc.* variants change the sets with no code edit. `db=None` uses one process-wide cached `ObjectDatabase` (`functools.lru_cache(maxsize=1)`, the `hooks._gate_db` precedent).
- **Callers.** validation.py and dsp_critic.py call these module-qualified (`dsp_roles.<fn>(db)`), so tests can monkeypatch them.
  - validation.py drops its own `_GAIN_NAMES` / `_TERMINAL_NAMES` (no importers; grep at planning).
  - dsp_critic.py keeps `_GAIN_NAMES` / `_TERMINAL_NAMES` as back-compat exports (tests/test_critics.py imports `_GAIN_NAMES`), equal to the repo-DB values and pinned equal by a test. No check reads them.
- **review_dsp.** Gains keyword-only `db=None`; review_patch passes its db.
- **Missing-gain-staging suggestion.** Names only `*~` for plugout~, because the M4L critic forbids gain~ / live.gain~ before plugout~.
- **Measured.** No corpus change: 0 gain-staging findings, 7 Unterminated unchanged, and no plugout~ in committed files. The `add_m4l_gen_synth` output loses its false `Unterminated signal chain: 'plugout~' (obj-2)` warning.

**PD-6. Contrast (E7).**
- **Theme constants** (defaults.py), from default.maxtheme styledefaults in Max 9.2.0: MAX_THEME_TEXT 0.85, MAX_THEME_CANVAS_BG 0.235, MAX_THEME_BOX_FILL 0.172 (all RGBA grays, alpha 1), MIN_VISIBLE_FILL_ALPHA 0.5.
- **"First non-background panel".** Interpreted as z-order, topmost first: panels with `background` != 1 (foreground layer) come before `background: 1` panels; within each layer, box-array order, where index 0 is topmost (CLAUDE.md Rule #6). The FIRST containing panel wins.

  Both E7 evidence cases sit on `background: 1` panels that the reviewer did use: amplitude-follower obj-21 (grad1 0.537/0.537/0.776) and kicksynth obj-10 (grad1 0.94). So "non-background" cannot mean "exclude `background: 1`".
- **Low-alpha fills.** A fill with alpha below 0.5 is skipped, for panels and for a box's own fill. An assumed (uncolored) panel keeps today's assumed handling.
- **Own fill.**
  - A visible own fill (bgfillcolor color1/color, grad1, bgcolor) is the background.
  - When the box has NO fill attribute at all and its maxclass is newobj, message or umenu, the background is MAX_THEME_BOX_FILL. Those are the classes whose refpages document `bgfillcolor`, the theme's box-fill key.
  - An explicitly transparent fill falls through to the surface beneath. 35 corpus flonums and 10 number boxes carry `[0, 0, 0, 0]`.
- **Critic.** A missing or invalid textcolor is MAX_THEME_TEXT; the patcher background fallback is MAX_THEME_CANVAS_BG.
- **Generator.**
  - Keep an explicit textcolor that already passes against every candidate background.
  - Otherwise fill or replace it: first `best_text_color` over today's dark/light candidates. Only when that still fails, try dark, light, black and white.
  - A missing textcolor is still filled. Existing tests require it, and an explicit color survives a user theme change.
- **One fix site.** One helper each serves the critic and the generator: `build_panel_layers` and `resolve_patcher_background`.
- **Measured.**
  - Corpus Low contrast warnings 1090 -> 56 (list in `<reference_data>`); trade-off notes 213 -> 209.
  - The E7 cases now warn: amplitude-follower obj-16/20/22/23 at 2.30:1 and kicksynth obj-154 at 1.24:1. The memory's default-text false positive is gone.
  - New true positives: scala-synth flonums obj-321..337 (white text, transparent fill, light presentation panel) at 1.19:1. They are warnings; no allowlist is needed.

**PD-7. RNBO (E8).**
- `_extract_param_name`: the `@name` value wins when present. Otherwise use the first argument after `param`, if it does not start with `@` and is not a number. Tokens come from `walk.split_box_text`.
- A missing in~ becomes a note with the text from `<reference_data>`. A missing out~ stays a blocker (fix-plan scope).
- **Measured** over the RNBO package, help and docs: 655 in~ blockers (MAX's own rnbo_triangle~.maxhelp among them) and 564 out~ blockers. Many are event-only rnbo~ patchers. List out~ as a follow-up in SUMMARY; do not change it here.
- The RNBO builder half of E8 (shape, classnamespace, golden fixture) is not in Q26's bullets; it is out of scope.

**PD-8. Spec-mandated edits to existing tests: exactly these.** The planning worktree run showed exactly the failures below and 4775 other passes.
1. `tests/test_critics.py::TestStructureCritic::test_hot_cold_ordering_detected`. Its fixture `_hot_cold_ordering_issue_patch` feeds `+` from two independent `random` boxes (E5 noise). Change the fixture to the shared-ancestor shape (number -> `unpack 0 0`, outlet 1 -> `+` inlet 0, outlet 0 -> `+` inlet 1) and assert exactly one `Hot/cold inlet ordering issue: '+' (obj-4)` warning.
2. `tests/test_critics_recursive.py::_hot_cold_content`, used by `test_nested_parity_with_top_level[structure_hot_cold]`, the same way: obj-2 number, obj-3 `unpack 0 0`, obj-4 `+`. `test_gen_scope_skips_ordering` keeps passing unchanged.
3. `tests/test_critics_recursive.py::TestRnboNested::test_rnbo_in_p_without_in`: severity `note` and the new in~ text.
4. `tests/test_critics.py::TestDSPCriticGainSafety::test_line_tilde_to_signal_inlet_no_flag`. Message `100 500` -> line~ -> `*~ 1.` inlet 0 (nothing in inlet 1) is now one blocker naming inlet 0 ("trace both `*~` inlets"). Rename it `test_line_tilde_to_inlet_0_is_traced`.
5. `tests/test_aesthetics.py::TestEnsureTextContrast::test_section_header_on_dark_canvas`: assert the header keeps `AESTHETIC_PALETTE["header_color"]` (8.04:1 on header_bgcolor) and the ratio is at least MIN_CONTRAST_RATIO.
6. `tests/test_aesthetics.py::TestEnsureTextContrast::test_section_header_on_light_panel`: the same assertion.
7. `tests/test_integration_patches.py`: add the `unsafe_gain` kind to `_blocker_match_key` and `_entry_key`. This is additive; no existing key changes.

Also keep at least 3 lines in dsp_critic.py that contain both `outlettype` and `_SIGNAL_OUTLET_TYPES`. tests/test_signal_role_migration.py counts them, and its floor is 3.
</planner_decisions>

<reference_data>
**Finding and suggestion text (exact).**

`{label}` is `structure_critic._box_label(box)`. For dsp, it is `walk.box_name(box)`, or `message '<text>'` for a message box.

- **Hot/cold, reversed.** `Hot/cold inlet ordering issue: '{name}' ({dst_id}) gets hot inlet 0 and cold inlet(s) {cold} from one event at '{anc}' ({anc_id}), but outlet {c} (cold) fires after outlet {h} (hot) -- '{name}' outputs with a stale cold value`
- **Hot/cold, same outlet.** `Hot/cold inlet ordering issue: '{name}' ({dst_id}) gets hot inlet 0 and cold inlet(s) {cold} from one event at '{anc}' ({anc_id}) outlet {o}, which fans out to both in undefined order -- '{name}' may output with a stale cold value`
- **Hot/cold suggestion.** `Feed both from one 'trigger' (t) with the hot inlet on its lowest outlet: trigger outlets fire right to left, so the cold inlets are set first.`
- **Unsafe gain.** `Unsafe gain source: {label} ({src_id}) reaches '{gain}' ({gid}) inlet {i}{via} with values up to {peak:g} (range {lo:g} to {hi:g}) -- gain inputs must stay within 0.0-1.0`. Here `{via}` is ` via line~` only when the path crossed a line~, and `{label}` is `'<name>'` or `message '<text>'`.
- **Unsafe gain suggestion.** `Normalize before the gain input, e.g. 'scale 0 127 0. 1.' or '/ 127.' for a 0-127 source, so the value stays within 0.0-1.0`
- **RNBO in~ note.** `rnbo~ '{rnbo_id}' inner patcher has no in~ object -- it takes no audio input, which is expected for a generator`. Suggestion: `If the patch should process audio input, add an 'in~ 1' object to the inner RNBO patcher`

**Q/triage.py** (scratch, untracked, run from the repo root with `sys.path` at cwd, warnings suppressed, one ObjectDatabase).
- `files()`: the sorted union of `patches/**/*.maxpat`, `*.maxhelp` and `*.gendsp` (69 at planning).
- `snapshot()`: for each file, two record lists:
  - `review_patch(d, db=db)` records `{severity, finding, suggestion, path}`;
  - `validate_patch(d, db)` records `{level, layer, message, path}`.
- **Q26 kinds.** A record is Q26 when its text, after an optional leading `[...] ` prefix, starts with one of these.
  - Critic: `Hot/cold inlet ordering issue: `, `Unsafe gain source: `, `Missing gain staging: `, `Low contrast text: `, `Presentation/patching contrast trade-off: `, `Duplicate RNBO param name `, `RNBO param `, `rnbo~ `.
  - Validate: `Unterminated signal chain: `, `Missing gain staging: `.

  The kind label is the prefix without its trailing `: `.
- `--base OUT`: write `snapshot()`.
- `--check BASE OUT`: write `snapshot()` to OUT.
  - Per file, mismatch means the non-Q26 records (in order) differ from BASE's.
  - Print `files=N mismatch=M`, then a table `source | kind | severity/level | before | after` covering every Q26 (kind, severity) present in either snapshot.
  - Exit 1 when M is above 0.
- `--bundle OUT`: when /Applications/Max.app exists, run `review_patch` on every .maxpat/.maxhelp under Contents/Resources/C74 (skipping unparseable files). Write the counts of the Q26 critic kinds by (kind, severity). Otherwise write `{"skipped": true}`.
- `--selftest` (synthetic records) exits 0 only when all of these hold:
  - identical snapshots pass;
  - a changed non-Q26 record is a mismatch;
  - `[p x] Hot/cold inlet ordering issue: ...` is classified as Q26;
  - a Q26 record that alone changes gives mismatch 0;
  - the count table counts by severity.

**Planning expectation, committed corpus (before at 65b4a894 -> after, from the prototypes).**

| Source | Kind | Severity | Before | After |
|---|---|---|---|---|
| review | Hot/cold inlet ordering issue | warning | 143 | 0 |
| review | Unsafe gain source | blocker | 0 | 1 |
| review | Missing gain staging | blocker | 0 | 0 |
| review | Low contrast text | warning | 1090 | 56 |
| review | Presentation/patching contrast trade-off | note | 213 | 209 |
| review | RNBO kinds | any | 0 | 0 |
| validate | Unterminated signal chain | warning | 7 | 7 |
| validate | Missing gain staging | warning | 0 | 0 |

The 56 after-state Low contrast warnings (file, scope key, box ids, ratio):
- amplitude-follower.maxpat "": obj-7, obj-10 (2.03); obj-16, obj-20, obj-22, obj-23 (2.30).
- gong-model/generated/gong-engine.gendsp "": obj-5 (1.13).
- kicksynth.maxpat "": obj-13 (2.26), obj-154 (1.24).
- mixer-strip.maxpat "obj-37" ([p sends]): obj-13, obj-24, obj-35, obj-46, obj-57, obj-68, obj-79, obj-90 (1.12).
- mixer.maxpat "": obj-15 (2.26).
- physics-composition.maxpat "": obj-67 bach.roll (2.81).
- scala-synth.maxpat "": flonums obj-321, obj-323, obj-325, obj-327, obj-329, obj-331, obj-333, obj-335, obj-337 (1.19); comments obj-1, obj-7, obj-9, obj-15, obj-16, obj-55, obj-61, obj-63, obj-217 (1.90).
- stereo-feedback-delay.maxpat "": obj-17, obj-22, obj-37, obj-42, obj-52 (1.40).
- subtractive-synth.maxpat "": obj-80, obj-85, obj-90, obj-95 (3.98).
- tape-wobble.maxpat "": obj-8, obj-13, obj-18, obj-23, obj-30, obj-36, obj-38, obj-40, obj-42 (1.12).
- wormhole-test.maxpat "": obj-1 (1.35).

**Bundle (supplementary).**
- Hot/cold: 8810 -> about 990.
- RNBO over the RNBO package, help and docs: 655 in~ blockers -> notes; 564 out~ blockers unchanged.

The `--bundle` run covers all of C74, so its RNBO counts may be higher; report them as measured.

**Allowlist entry** (tests/review_blocker_allowlist.json, under `patches/rhythmic-sampler/generated/slot.maxpat`, appended after the existing fanout entry):
- fields: severity "blocker", kind "unsafe_gain", source_id "obj-54", gain_id "obj-9", inlet 1, path "";
- reason: `True positive (fix-plan rule 3), surfaced by Q26 (E6) once dials and value bounds were read: vol dial obj-54 (floatoutput 1, size 121, mult 0.01, range 0 to 1.21) -> 't f f' obj-166 -> '$1 10' obj-155 -> line~ obj-156 -> '*~' obj-9 inlet 1, a deliberate +1.66 dB headroom on the slot volume. The patch is frozen (never edited to satisfy critics); listed in the Q26 SUMMARY.`

**Key regex** for `_blocker_match_key`: `Unsafe gain source: (?:message )?'[^']*' \(([^)]+)\) reaches '[^']*' \(([^)]+)\) inlet (\d+)`. It gives the key ("unsafe_gain", source_id, gain_id, int(inlet)). `_entry_key` maps kind "unsafe_gain" the same way.
</reference_data>

<source_audit>
| Source | Item | Covered by |
|---|---|---|
| GOAL (fix-plan Q26) | Hot/cold: warn only on a shared upstream ancestor; skip p, bpatcher, js targets | Task 1 (1b; PD-1..3) |
| GOAL | Gain: split on commas; target/time pairs only for messages feeding line~ directly | Task 2 (PD-4) |
| GOAL | Gain: bounds through `* k`, `/ k`, scale/clip args, box min/max incl. parameter_mmin/mmax | Task 2 (PD-4) |
| GOAL | Gain: trace both `*~` inlets | Task 2 (PD-4, PD-8 item 4) |
| GOAL | Gain: DB-driven gain-stage/terminal sets shared with validation.py; live.gain~ stage; mc.dac~, plugout~ terminals | Task 2 (PD-5) |
| GOAL | Contrast: theme text 0.85, canvas 0.235, box fill 0.172 | Task 3 (PD-6) |
| GOAL | Contrast: first non-background containing panel; skip low-alpha fills; own fill is the background | Task 3 (PD-6) |
| GOAL | Contrast: keep passing colours; black and white as candidates | Task 3 (PD-6) |
| GOAL | RNBO: positional param names; missing in~ -> note | Task 1 (1a; PD-7) |
| GOAL | Tests: one per change; calibration green | Tasks 1-3 (`tests/test_critic_fixes_e5_e8.py`), Task 3 full suite |
| GOAL | Report finding counts on committed patches before and after | Task 1 Step 0 (Q/triage-base.json), Tasks 1-3 `--check`, SUMMARY table |
| REQ | E5, E6, E7, E8 | Task 1 (1b), Task 2, Task 3, Task 1 (1a) |
| Orchestrator | ui-presets.md "Text Contrast Resolution" updated to match | Task 3 |
| Orchestrator | Memory false positive (default-text comments at 2.81:1) resolved | Task 3 test + SUMMARY |
| Excluded (not in Q26 bullets) | RNBO builder shape and golden fixture (E8 second half); `gain~` input check; `sig~` and control `line` as bridges; missing out~ severity | SUMMARY follow-ups |
| RESEARCH | none (no research phase) | n/a |
</source_audit>

<tasks>

<task type="tracer" tdd="true">
  <name>Task 1: Step 0 baseline and triage harness; RNBO tracer slice (1a); then hot/cold on a shared upstream event (1b)</name>
  <files>src/maxpat/critics/rnbo_critic.py, src/maxpat/critics/structure_critic.py, tests/test_critic_fixes_e5_e8.py, tests/test_critics.py, tests/test_critics_recursive.py</files>
  <precondition>Both hard preconditions in `<rules>` hold (HEAD contains 65b4a894; the task files are clean; dsp_roles.py and the new test file are absent).</precondition>
  <read_first>
    - 1a: src/maxpat/critics/rnbo_critic.py (whole); tests/test_critics_recursive.py lines 40-135 (helpers) and TestRnboNested (~820-845); src/maxpat/critics/__init__.py review_patch (~63-140)
    - 1b: src/maxpat/critics/structure_critic.py 1-160, `_is_jitter_setter_hop` (~229), `_check_hot_cold_ordering` (~405-496), `_box_label` (~507) and the Q21 block (~700-857); tests/test_critics.py `_hot_cold_ordering_issue_patch` (~449) and `test_hot_cold_ordering_detected` (~649); tests/test_critics_recursive.py `_hot_cold_content` (~120) and the parity test (~669-718)
    - `<rules>` (Step 0), `<reference_data>` (triage spec, RNBO note text, hot/cold texts), `<planner_decisions>` PD-1 to PD-3, PD-7 and PD-8 items 1-3
  </read_first>
  <behavior>
    **1a, RNBO (classes TestRnboParamNames, TestRnboMissingIn):**
    - Positional duplicate: an rnbo~ (inner classnamespace rnbo, holding `in~ 1` and `out~ 1`) with `param freq 440` and `param freq 220` gives exactly one blocker starting `Duplicate RNBO param name 'freq'`.
    - Mixed duplicate: `param @name gain` plus `param gain 0.5` gives one duplicate blocker.
    - Naming: `param MyGain 0` gives one naming warning suggesting `my_gain`; `param @min 0` and `param 5` give no naming and no duplicate finding.
    - in~ note: inner `out~ 1` only, no in~, gives exactly one finding, severity "note", with the exact text from `<reference_data>`; the same nested in `p synth` carries path obj-1 and the prefix `[p synth] `.
    - out~ unchanged: inner `in~ 1` only gives the existing out~ blocker.
    - review_patch: a top-level rnbo~ generator (out~ only) yields no RNBO blocker from `review_patch`.
    - Bundle (requires_max): review_rnbo on `Contents/Resources/C74/packages/RNBO/help/rnbo_triangle~.maxhelp` gives no blocker mentioning in~.

    **1b, hot/cold (class TestHotColdSharedAncestor):**
    - Reversed order: number -> `unpack 0 0`; outlet 1 -> `+` inlet 0; outlet 0 -> `+` inlet 1. Exactly one warning, with the reversed-order text.
    - Swapped cords: none.
    - Independent sources: two independent number boxes into `+` inlets 0 and 1: none.
    - Same-outlet fan-out: `button` outlet 0 -> `pack 0 0` inlets 0 and 1. One hot/cold warning with the same-outlet text, plus the existing fan-out blocker.
    - Skipped targets: the reversed shape into `p x`, an embedded bpatcher, `js foo.js`, `gate 2` and `pak 0 0`: none. Into `i` (storage): none.
    - Exclusive router: a `route a b` divergence (outlet 1 -> target hot, outlet 0 -> target cold): none.
    - Cold-inlet stop: notein outlets 0/1 -> `poly 4` inlets 0/1, and poly outlets feeding `int` inlets 0/1 in correct order: none.
    - Jitter setter stop: loadbang fan-out through two `exprfill ...` messages into jit.matrix boxes, both feeding `jit.pack` inlets 0/1: none.
    - Deep reversed order: `t i i`; outlet 1 -> `+ 1` -> `-` inlet 0; outlet 0 -> `-` inlet 1. One hot/cold warning (outside Q21's one-hop reach).
    - Q21 boundary: `t i b` with outlet 1 -> `+` inlet 0 and outlet 0 -> `+` inlet 1 gives only the `Trigger order: ` blocker and no hot/cold. `t f f` -> `- 0.` (Q21 idiom) gives neither.
    - MSP control inlets: the reversed `t l b` shape into `ears.slice~` is reported once in total, by Q21. With a two-hop path it is reported by hot/cold.
    - Nested: the reversed shape inside `p a` (obj-1) gives path obj-1 and the prefix `[p a] Hot/cold inlet ordering issue: `.
    - Robustness and purity: review_structure never raises on junk values (non-int ports, cords to missing ids, a target with no DB entry, non-str text), and the patch deep-equals its pre-review copy.
  </behavior>
  <action>
**Step 0 first** (see `<rules>`): Q/base-sha.txt, Q/stash-list-before.txt, Q/baseline-pytest.txt, then write Q/triage.py per `<reference_data>` and run --selftest, --base, --check and --bundle into Q/triage-step0.txt.

**1a. Red (tracer slice: proves test-first -> fix -> triage before/after -> commit end to end on the smallest change).**
- Create `tests/test_critic_fixes_e5_e8.py`. Its module docstring cites fix-plan Q26 and findings E5-E8 and says one class per change. It has a module-scoped ObjectDatabase fixture and imports `_box`, `_line`, `_container`, `_inner`, `_patch` from `tests.test_critics_recursive`. Add class TestRnboParamNames and class TestRnboMissingIn with the 1a `<behavior>` cases; the bundle case is marked `pytest.mark.requires_max` and builds its path from `tests.conftest.MAX_APP_PATH`.
- Apply PD-8 item 3 to `tests/test_critics_recursive.py::TestRnboNested::test_rnbo_in_p_without_in`: expect `[("note", "obj-1")]` and the new `[p synth] rnbo~ 'obj-2' inner patcher has no in~ object -- ...` text.
- Run both files into Q/red-t1.txt. It must show failures.

**1a. Green (rnbo_critic.py), per E8 / PD-7.**
- `_extract_param_name` returns the `@name` value when present. Otherwise it returns the first token after `param` (`walk.split_box_text`) that does not start with `@` and does not parse as a number; else None. Non-str text gives None.
- `_check_io_completeness` emits the missing-in~ finding as "note" with the `<reference_data>` text and suggestion; the out~ branch is unchanged.
- Update the module docstring and the review_rnbo docstring: positional names, in~ note, and the generator rationale (MAX's own rnbo_triangle~ help).
- Run `python3 Q/triage.py --check Q/triage-base.json Q/triage-t1.json`: mismatch 0 and no Q26 count change, since committed files hold no rnbo~.
- Commit `src/maxpat/critics/rnbo_critic.py`, `tests/test_critic_fixes_e5_e8.py` and `tests/test_critics_recursive.py` with `fix(critics): RNBO critic parses positional param names; missing in~ is a note (Q26)`.

**1b. Red.**
- Add TestHotColdSharedAncestor to `tests/test_critic_fixes_e5_e8.py`.
- Apply PD-8 items 1 and 2: rewrite the two independent-source fixtures to the unpack shape, and make `test_hot_cold_ordering_detected` assert exactly one `Hot/cold inlet ordering issue: '+' (obj-4)` warning.
- Run into Q/red-t1b.txt (must show failures).

**1b. Green (structure_critic.py), E5 / PD-1..PD-3.**
- Factor `_trigger_reach(scope, t_id)` out of `_check_trigger_order` with no behavior change.
- Rewrite `_check_hot_cold_ordering(scope, dbh, q21_targets)` per PD-1, using `_inlet_is_cold`, `_is_jitter_setter_hop`, `_ORDER_EXCLUDED_NAMES`, `_ORDER_STORAGE_NAMES`, `_is_zl_reg`, `_ORDER_IDIOM_TARGETS`, a new module frozenset for the exclusive-outlet routers, `_box_label` and the `<reference_data>` texts.
- In `review_structure`, compute the scope's trigger-order results first. Pass the PD-2 skip set, built from `_trigger_reach` over the scope's triggers, to hot/cold, then extend `found` in the original check order.
- Every read is type-guarded and read-only. Update the module docstring, the review_structure docstring (check 2) and the function docstring, citing E5 and PD-1..3.

**Then:**
- Run `python3 Q/triage.py --check Q/triage-base.json Q/triage-t1b.json`: mismatch 0 and hot/cold 143 -> 0 (investigate any other count and record the verdict).
- Commit `src/maxpat/critics/structure_critic.py`, `tests/test_critic_fixes_e5_e8.py`, `tests/test_critics.py` and `tests/test_critics_recursive.py` with `fix(critics): hot/cold warns only when one upstream event updates a cold inlet after the hot one (Q26)`.
  </action>
  <verify>
    <automated>bash -c 'Q=.planning/quick/261015-nkm-implement-q26-in-planning-reviews-2026-1 && B=$(git status --porcelain) && python3 -m pytest -q -p no:cacheprovider tests/test_critic_fixes_e5_e8.py tests/test_critics_recursive.py tests/test_critics.py tests/test_critic_precision.py tests/test_ordering_checks.py tests/test_uninitialized_state.py tests/test_integration_patches.py && A=$(git status --porcelain) && test "$B" = "$A" && grep -iq -e failed -e error "$Q/red-t1.txt" && grep -iq -e failed -e error "$Q/red-t1b.txt" && python3 "$Q/triage.py" --selftest && python3 "$Q/triage.py" --check "$Q/triage-base.json" "$Q/triage-t1b.json" && test -s "$Q/triage-step0.txt" && test -s "$Q/baseline-pytest.txt" && C=$(git log --format=%H --fixed-strings --grep="(Q26)" "$(cat "$Q/base-sha.txt")"..HEAD) && set -- $C && test $# -ge 2 && python3 -c "import ast,sys;[ast.parse(open(f).read(),feature_version=(3,10)) for f in sys.argv[1:]]" src/maxpat/critics/rnbo_critic.py src/maxpat/critics/structure_critic.py tests/test_critic_fixes_e5_e8.py'</automated>
  </verify>
  <done>
- Positional and `@name` params are both checked for duplicates and naming; a generator rnbo~ (no in~) gets a note, not a blocker; a missing out~ is still a blocker.
- Hot/cold fires only on a shared upstream event that updates a cold inlet at or after the hot firing, and defers to Q21 inside Q21's reach. Committed hot/cold warnings are 0.
- PD-8 items 1-3 are applied and nothing else in existing tests changed.
- Step 0 artifacts exist; triage gives mismatch 0 after each commit.
- Two `(Q26)` commits (1a, 1b) exist.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Bounds-propagating gain safety on both *~ inlets, with DB-driven gain-stage and terminal sets shared with validation</name>
  <files>src/maxpat/dsp_roles.py, src/maxpat/critics/dsp_critic.py, src/maxpat/critics/__init__.py, src/maxpat/validation.py, tests/test_critic_fixes_e5_e8.py, tests/test_critics.py, tests/test_integration_patches.py, tests/review_blocker_allowlist.json</files>
  <precondition>Task 1's two `(Q26)` commits exist and Q/triage-base.json exists.</precondition>
  <read_first>
    - src/maxpat/critics/dsp_critic.py 1-115 and 230-505; src/maxpat/validation.py 55-70, ~1279-1365, ~1569-1665; src/maxpat/critics/__init__.py review_patch (~63-140)
    - tests/test_critics.py TestDSPCriticGainSafety (~1356-1742); tests/test_integration_patches.py 30-120; tests/review_blocker_allowlist.json; tests/test_signal_role_migration.py 115-140
    - `<planner_decisions>` PD-4, PD-5 and PD-8 items 4 and 7; `<reference_data>` (gain finding texts, allowlist entry, key regex)
  </read_first>
  <behavior>
    **Gain (classes TestGainMessageParsing, TestGainBounds, TestGainBothInlets, TestDspRoles):**
    - Message parsing:
      - `0, 0.8 2000` -> line~ -> `*~` inlet 1: none.
      - `0.5, 100 500` -> line~: one, via line~.
      - `$1 20` -> line~ fed by ctlin: one, via line~.
      - `$1 $2 0. $3` -> line~ fed by `pack f f f` (from a dial): none.
      - `64` -> `* 0.01` -> `*~`: none.
      - `200` -> `* 0.01` -> `*~`: one, whose text lacks `via line~`.
      - `set 5` -> `*~`: none.
      - `; foo 100` remote part: ignored.
    - Bounds:
      - flonum minimum 0 / maximum 1: none.
      - flonum maximum 1 only: none.
      - number with no limits: one (0-127).
      - ctlin -> `scale 0 127 0. 1.`: none.
      - ctlin -> `scale 0 127 0. 4.`: one (range 0 to 4).
      - ctlin -> `zmap 0 127 0. 2.`: one.
      - ctlin -> `clip 0. 0.5`: none.
      - ctlin -> `/ 127.`: none.
      - live.dial with parameter_mmin 0 / mmax 1: none; with defaults: one.
      - dial floatoutput 1, size 121, mult 0.01: one (1.21).
      - ctlin -> `t b f` outlet 0 (b) -> `*~`: none.
      - ctlin -> `t f` -> `*~`: one.
      - ctlin -> `dbtoa` -> `*~`: none (unknown stops).
    - Both inlets:
      - ctlin -> `*~` inlet 0 with cycle~ on inlet 1: one naming inlet 0.
      - message `100 500` -> line~ -> `*~ 1.` inlet 0: one (PD-8 item 4).
      - line~ fed `100` -> `*~ 0.01` inlet 0, with inlet 1 empty: none.
      - mc.*~ the same as *~.
    - DB-driven sets:
      - `dsp_roles` returns exactly the three sets in must_haves under the repo DB.
      - A DB double whose lookup returns None for `mc.live.gain~` drops it.
      - dsp_critic `_GAIN_NAMES` / `_TERMINAL_NAMES` equal `gain_stage_names(db)` / `output_terminal_names(db)`.
      - cycle~ -> live.gain~ -> dac~: no `Missing gain staging`.
      - cycle~ -> mc.dac~: one; cycle~ -> plugout~: one, whose suggestion names `*~` and not `gain~`.
      - `validate_patch(Patcher().add_m4l_gen_synth(...)` output) has no `Unterminated signal chain` result.
      - Monkeypatching `src.maxpat.dsp_roles.chain_terminal_names` to add `adc~` removes an unconnected adc~'s Unterminated warning.
    - Robustness and purity: review_dsp never raises on junk values:
      - size "x" and saved_attribute_attributes 5;
      - valueof 3 and message text 7;
      - `scale` with 2 args and non-int ports;
      - cords to missing ids;
      - a `* 2` cycle feeding `*~`.

      The patch deep-equals its pre-review copy.
  </behavior>
  <action>
**Red.**
- Add the four gain/role classes to `tests/test_critic_fixes_e5_e8.py`.
- Apply PD-8 item 4 in `tests/test_critics.py` (rename to `test_line_tilde_to_inlet_0_is_traced`, assert one blocker naming inlet 0).
- Run into Q/red-t2.txt (must show failures).

**Green, E6 / PD-4 and PD-5.**
- **dsp_roles.py.** Create `src/maxpat/dsp_roles.py`: the module docstring states the PD-5 derivation and the plugout~ refpage evidence, then the three base tuples, the cached default-DB helper and the three functions.
- **validation.py.**
  - `_validate_domain_rules` passes `dsp_roles.chain_terminal_names(db)` to `_check_unterminated_chains`, and `dsp_roles.gain_stage_names(db)` plus `dsp_roles.output_terminal_names(db)` to `_check_gain_staging`. This replaces the literal dac~/ezdac~ test.
  - Remove the two validation-local constants they replace, and update the docstrings.
- **dsp_critic.py.**
  - `review_dsp(..., *, graph=None, db=None)`.
  - `_check_gain_staging` takes the gain-stage and output-terminal sets from dsp_roles; the plugout~ suggestion follows PD-5.
  - Rewrite `_check_unsafe_gain_sources` to the PD-4 trace with the `<reference_data>` texts. Keep the signal-ness read as `src_outlettype[...] in _SIGNAL_OUTLET_TYPES` at 2 sites or more, so dsp_critic.py keeps at least 3 such lines.
  - Keep `_is_normalizer`, and keep `_GAIN_NAMES` / `_TERMINAL_NAMES` as pinned back-compat exports.
  - Update the module and review_dsp docstrings, citing E6 / PD-4 / PD-5.
- **critics/__init__.py.** review_patch calls `review_dsp(patch_dict, code_context=code_context, graph=graph, db=db)` and documents it.
- **Rule-3 allowlist.** Apply PD-8 item 7: add the `unsafe_gain` regex and entry key to `tests/test_integration_patches.py`, and append the `<reference_data>` entry to `tests/review_blocker_allowlist.json`. Build the entry from the live finding, not by hand-copying.

**Then:**
- Run `python3 Q/triage.py --check Q/triage-base.json Q/triage-t2.json`: mismatch 0, and Unsafe gain 0 -> 1 with only the slot.maxpat finding. Any other new gain finding is either a checker bug (fix it here) or a true positive (allowlist it with a reason). Record each verdict for SUMMARY.
- Commit the 8 task files with `fix(critics): gain safety propagates value bounds on both *~ inlets with DB-driven gain-stage and terminal sets (Q26)`.
  </action>
  <verify>
    <automated>bash -c 'Q=.planning/quick/261015-nkm-implement-q26-in-planning-reviews-2026-1 && B=$(git status --porcelain) && python3 -m pytest -q -p no:cacheprovider tests/test_critic_fixes_e5_e8.py tests/test_critics.py tests/test_critics_recursive.py tests/test_integration_patches.py tests/test_signal_role_migration.py tests/test_validation.py tests/test_validation_recursive.py tests/test_validation_nondestructive.py tests/test_critic_revival.py tests/test_m4l_gen_synth.py tests/test_save_gate.py && A=$(git status --porcelain) && test "$B" = "$A" && grep -iq -e failed -e error "$Q/red-t2.txt" && python3 "$Q/triage.py" --check "$Q/triage-base.json" "$Q/triage-t2.json" && grep -q "review_dsp(patch_dict, code_context=code_context, graph=graph, db=db)" src/maxpat/critics/__init__.py && grep -q "dsp_roles.chain_terminal_names(" src/maxpat/validation.py && grep -q "dsp_roles.output_terminal_names(" src/maxpat/critics/dsp_critic.py && grep -q "unsafe_gain" tests/review_blocker_allowlist.json && C=$(git log --format=%H --fixed-strings --grep="(Q26)" "$(cat "$Q/base-sha.txt")"..HEAD) && set -- $C && test $# -ge 3 && python3 -c "import ast,sys;[ast.parse(open(f).read(),feature_version=(3,10)) for f in sys.argv[1:]]" src/maxpat/dsp_roles.py src/maxpat/critics/dsp_critic.py src/maxpat/critics/__init__.py src/maxpat/validation.py tests/test_critic_fixes_e5_e8.py tests/test_integration_patches.py'</automated>
  </verify>
  <done>
- Gain safety parses comma segments, reads target/time pairs only for direct line~ feeds, propagates bounds through `* k`, `/ k`, scale/zmap/clip and box min/max, traces both inlets, and stops at unknown boxes.
- validation.py and dsp_critic.py take their gain-stage and terminal sets from dsp_roles(db).
- The one new committed true positive is allowlisted with a reason.
- PD-8 items 4 and 7 are applied and nothing else in existing tests changed; triage gives mismatch 0.
- A third `(Q26)` commit exists.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Theme-aware contrast in the critic and generator, ui-presets.md, full suite, before/after report and SUMMARY</name>
  <files>src/maxpat/defaults.py, src/maxpat/aesthetics.py, src/maxpat/critics/layout_critic.py, .claude/skills/references/ui-presets.md, tests/test_critic_fixes_e5_e8.py, tests/test_aesthetics.py</files>
  <precondition>Task 2's `(Q26)` commit exists (three `(Q26)` commits in total) and Q/triage-t2.json exists.</precondition>
  <read_first>
    - src/maxpat/aesthetics.py 1-120 and 222-505; src/maxpat/critics/layout_critic.py 1-70 and 323-443; src/maxpat/defaults.py 115-170
    - tests/test_aesthetics.py TestEnsureTextContrast, TestContrastPrimitives, TestBoxOwnBackground, TestRepairTextContrast
    - .claude/skills/references/ui-presets.md 139-168, and the phrase pins in tests/test_claude_md.py (~226: "## Text Contrast Resolution", "bgfillcolor", "grad1", "maximizes the MINIMUM contrast", "Presentation coordinates", "Patcher background", "MIN_CONTRAST_RATIO")
    - `<planner_decisions>` PD-6 and PD-8 items 5-6; `<reference_data>` (the 56-warning after-list)
  </read_first>
  <behavior>
    **Critic (class TestThemeAwareContrast):**
    - Theme text default: a comment with no textcolor gives no Low contrast on a patcher with no bg keys, on editing_bgcolor 0.333, or on bgcolor 0.235.
    - Theme canvas fallback: a comment with textcolor 0.7 gray gives none with no bg keys (5.24:1) and a warning with editing_bgcolor 0.333 (3.54:1).
    - E7 evidence: a comment with no textcolor in presentation on a `background: 1` panel with grad1 [0.537, 0.537, 0.776, 1] warns at `2.30:1`. One with no textcolor on grad1 0.94 warns at `1.24:1`.
    - First containing panel: two overlapping `background: 1` panels, index 0 dark [0.1] and index 1 light [0.94], with a comment of textcolor [0.2, 0.2, 0.25] inside both, give a warning (judged against index 0). Swapping the array order gives none. A foreground panel (light, `background` 0) at index 1 beats a background-layer dark panel at index 0: none.
    - Low-alpha fills: a panel with bgcolor [0, 0, 0, 0] is skipped (no-textcolor comment on the 0.235 canvas: none). A dark-text comment with own bgcolor [0, 0, 0, 0] on a light panel is judged against the panel: none.
    - Own fill: a comment with an opaque light own bgcolor and dark text gives none on a dark panel. A message box with textcolor [0.2, 0.2, 0.25] and no fill attribute on a light panel warns against the theme box fill (1.12:1). The same message with a light bgfillcolor gives none.

    **Generator (class TestContrastGenerator):**
    - Keep passing: `add_section_header` + `ensure_text_contrast` keeps header_color; `repair_text_contrast` on a fresh header patch returns 0. A comment with explicit LIGHT text on the dark canvas is kept (repair returns 0).
    - Fallback candidates: a comment on a mid-gray [0.5] panel gets [0.0, 0.0, 0.0, 1.0] (dark 3.13, light 2.49, white 3.98, black 5.28) with ratio at least 4.5.
    - Missing color: a plain comment (no textcolor) still gets a textcolor written.
    - Agreement: after `ensure_text_contrast` on a patch with overlapping panels, a low-alpha panel and a header, `review_layout(p.to_dict())` gives no `Low contrast text` warning.

    **Robustness:** review_layout never raises when textcolor is "x", bgcolor is [1], background is "yes", or the panel rects are None or short. The patch deep-equals its pre-review copy.
  </behavior>
  <action>
**Red.**
- Add TestThemeAwareContrast and TestContrastGenerator to `tests/test_critic_fixes_e5_e8.py`.
- Apply PD-8 items 5 and 6 in `tests/test_aesthetics.py`.
- Run into Q/red-t3.txt (must show failures).

**Green, E7 / PD-6.**
- **defaults.py.** Add MAX_THEME_TEXT, MAX_THEME_CANVAS_BG, MAX_THEME_BOX_FILL (the PD-6 values) and MIN_VISIBLE_FILL_ALPHA 0.5, with a provenance comment: default.maxtheme styledefaults textcolor / editing_bgcolor and locked_bgcolor / bgfillcolor_color*, Max 9.2.0, review E7.
- **aesthetics.py.**
  - Add `fill_is_visible(color)`.
  - Add `resolve_patcher_background(props)`: bgcolor, editing_bgcolor, locked_bgcolor, then MAX_THEME_CANVAS_BG. `_resolve_patcher_bg` delegates to it.
  - Add THEME_FILL_MAXCLASSES = newobj, message, umenu.
  - Add `build_panel_layers(entries)`. Entries are (attrs, patching_rect, presentation, presentation_rect). It returns the z-ordered patching and presentation layers of PD-6, without panels whose found fill is invisible.
  - `_bg_under_rect` returns the FIRST containing layer.
  - `resolve_effective_background` gains keyword-only `maxclass=None` and the PD-6 own-fill rules.
  - Add FALLBACK_TEXT_CANDIDATES (black, white) and `choose_text_color(current, backgrounds)`, returning (color, kept) per PD-6. `best_text_color`, `contrast_text_color` and TEXT_COLOR_CANDIDATES stay unchanged.
  - `_apply_text_contrast` uses `build_panel_layers` and `choose_text_color`, writes only changed colors, and counts only changes.
  - Update the ensure_text_contrast and repair_text_contrast docstrings.
- **layout_critic.py.**
  - `_check_text_contrast` reads a missing or invalid textcolor as MAX_THEME_TEXT and builds layers with `build_panel_layers`.
  - It resolves the patcher background through `resolve_patcher_background` and passes `maxclass`.
  - Update the module docstring sentence on the fallback canvas.
- **ui-presets.md** (the orchestrator requires it to match the code).
  - In "Max 9 Theme Defaults", replace the last bullet. Say that `defaults.py` MAX_THEME_TEXT / MAX_THEME_CANVAS_BG / MAX_THEME_BOX_FILL encode these values, and that the critic and `ensure_text_contrast` use them.
  - In "Text Contrast Resolution", delete the opening sentence that says the contrast code still assumes the legacy defaults.
  - Rewrite the precedence list to PD-6:
    1. A visible own fill; transparent fills, alpha below `MIN_VISIBLE_FILL_ALPHA`, are ignored. A newobj/message/umenu box with no fill attribute reads against the 0.172 box fill.
    2. and 3. Presentation coordinates / Patching coordinates: the FIRST (topmost) containing panel. Foreground-layer panels come before `background: 1` panels, in box order within each layer (Rule #6). Low-alpha panels are skipped.
    4. Patcher background: bgcolor > editing_bgcolor > locked_bgcolor > the 0.235 theme canvas.
  - Add one sentence each on these points:
    - missing textcolor is read as 0.85;
    - the generator keeps a passing color;
    - black and white are used only when dark and light both fail.
  - Keep every phrase that tests/test_claude_md.py pins. Do not edit CLAUDE.md (rule 8; its precedence summary stays accurate).

**Then:**
- Run `python3 Q/triage.py --check Q/triage-base.json Q/triage-final.json`: mismatch 0. Compare the Low contrast after-list with the 56 entries in `<reference_data>`. A difference is either an implementation bug (fix it here) or a prototype error; record every verdict.
- Run `--bundle Q/bundle-final.json` when Max is installed.
- Run the full suite into Q/final-pytest.txt. It must be green against Q/baseline-pytest.txt plus the new tests, including the requires_max bundle sweep.
- Commit the 6 task files with `fix(critics): theme-aware text contrast -- Max 9 defaults, topmost visible panel, keep passing colours (Q26)`.
- Write Q/q26-commit-files.txt (the files of every `(Q26)` commit).

**SUMMARY must include:**
- the before/after table from Q/triage-base.json vs Q/triage-final.json per Q26 kind and severity (the fix-plan "report finding counts" item), plus the bundle table when present;
- PD-1 to PD-8 as implemented, with measurements and every verdict on a difference from the planning expectation;
- the slot.maxpat true positive and its allowlist entry;
- the 7 spec-mandated test edits;
- follow-ups outside Q26: the RNBO builder half of E8; `gain~` input check; `sig~` / control `line` as gain bridges; out~ severity on event-only rnbo~; uncolored number/flonum/textbutton theme fills (`bgcolor` style 0.125, unverified);
- doc impact, nothing edited (rule 8): TECHNICAL.md tables for Structure hot/cold, DSP gain staging and "MIDI-range gain values", RNBO "Missing I/O", validation Layer 4 terminals and Layout "Low contrast text"; the memory note feedback_contrast_critic_default_text is now resolved;
- the Q23 status (landed or not);
- MAX confirmation (rule 9): nothing required. Optionally, the user can glance at amplitude-follower's presentation labels and scala-synth's presentation flonums, which are newly flagged as low contrast.
  </action>
  <verify>
    <automated>bash -c 'Q=.planning/quick/261015-nkm-implement-q26-in-planning-reviews-2026-1 && touch "$Q/final-pytest.txt" && B=$(git status --porcelain) || exit 1; python3 -m pytest -q -p no:cacheprovider > "$Q/final-pytest.txt" 2>&1; R=$?; tail -1 "$Q/final-pytest.txt"; A=$(git status --porcelain) || exit 1; test $R -eq 0 && test "$B" = "$A" && grep -iq -e failed -e error "$Q/red-t3.txt" && python3 "$Q/triage.py" --selftest && python3 "$Q/triage.py" --check "$Q/triage-base.json" "$Q/triage-final.json" && grep -q "MAX_THEME_CANVAS_BG" src/maxpat/defaults.py && grep -q "build_panel_layers(" src/maxpat/critics/layout_critic.py && grep -q "MIN_VISIBLE_FILL_ALPHA" .claude/skills/references/ui-presets.md && ! grep -q "until Q26" .claude/skills/references/ui-presets.md && for p in "## Text Contrast Resolution" "bgfillcolor" "grad1" "maximizes the MINIMUM contrast" "Presentation coordinates" "Patcher background" "MIN_CONTRAST_RATIO"; do grep -qF "$p" .claude/skills/references/ui-presets.md || exit 1; done && python3 -c "import ast,sys;[ast.parse(open(f).read(),feature_version=(3,10)) for f in sys.argv[1:]]" src/maxpat/defaults.py src/maxpat/aesthetics.py src/maxpat/critics/layout_critic.py tests/test_critic_fixes_e5_e8.py tests/test_aesthetics.py && S=$(git stash list) && test "$S" = "$(cat "$Q/stash-list-before.txt")" && C=$(git log --format=%H --fixed-strings --grep="(Q26)" "$(cat "$Q/base-sha.txt")"..HEAD) && set -- $C && test $# -ge 4 && for c in $C; do git show --name-only --format= "$c" || exit 1; done > "$Q/q26-commit-files.txt" && test -s "$Q/q26-commit-files.txt" && ! grep -q "^patches/" "$Q/q26-commit-files.txt" && ! grep -qv -e "^src/maxpat/" -e "^tests/" -e "^\.claude/skills/references/ui-presets\.md$" "$Q/q26-commit-files.txt"'</automated>
  </verify>
  <done>
- Critic and generator are theme-aware and agree:
  - missing text 0.85, missing canvas 0.235, untinted object/message/umenu fill 0.172;
  - the topmost visible containing panel wins, and low-alpha fills are skipped;
  - passing colors are kept, and black/white are used only when dark and light both fail.
- ui-presets.md describes exactly this.
- Triage gives mismatch 0, and SUMMARY carries the before/after table.
- The full suite and calibration are green against the baseline plus new tests.
- At least 4 `(Q26)` commits exist, touching only src/maxpat, tests and ui-presets.md; the stash list is unchanged.
  </done>
</task>

</tasks>

<threat_model>
Security config: ASVS level 1, block on high. This is in-process critic, validator and styling code over local JSON, with no network, auth or crypto. What matters:
- ASVS V5 input robustness;
- no false blockers that make the generator loop "fix" correct patches;
- no edits to frozen user patches.

## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| .maxpat JSON -> critics / validator / aesthetics | Patch files (user, generated, MAX-saved, bundle) are untrusted structure: box attributes (size, mult, minimum, parameter_mmin, fills, alpha, background), message text and cords drive traversal and arithmetic |
| critic blocker -> save gate / generator revision loop | An Unsafe-gain blocker refuses a save that introduces it and drives a revision |
| Concurrent Claude instances -> git | Broad staging or stash can sweep in or strand another instance's work |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-nkm-01 | Denial of Service | Gain trace, hot/cold walk, panel layers or RNBO parsing raise on malformed input (non-numeric size/mult/minimum, non-dict valueof, short colour lists, non-str text, bad ports), aborting review_patch, validate_patch and every save | high | mitigate | Type guards on every read; the robustness tests in Tasks 1, 2 and 3; the existing `_junk_scope` sweep and the requires_max bundle sweep (3139 files) in the full suite. |
| T-nkm-02 | Denial of Service | Unbounded traversal: op chains growing around cycles through `*` boxes; upstream walks on large patches | medium | mitigate | Gain trace: visited set, 64-hop limit and a 4096-state cap per (gain box, inlet), with a cycle test. Hot/cold: visited set plus the cheap target prefilter; measured 1.8 s over the whole bundle. |
| T-nkm-03 | Tampering | False-positive blockers pushing the generator to rewrite correct shapes (dbtoa trims, ramp-time values, ordered multi-outlet sources) | high | mitigate | PD-1 and PD-4 measured on the corpus and bundle; unknown boxes stop the gain trace; hot/cold stays a warning; the triage `--check` mismatch gate after every task. |
| T-nkm-04 | Tampering | Committed user-confirmed patches edited to silence findings | high | mitigate | Rule 3 and the edit scope. The new true positive is allowlisted with a reason; the Task 3 verify fails if any `(Q26)` commit touches `patches/` or a file outside src/maxpat, tests and ui-presets.md. |
| T-nkm-05 | Tampering | Critic or generator mutating the patch dict or the Box | medium | mitigate | Purity deep-equal tests; `_apply_text_contrast` writes only changed text colours through `_set_textcolor`. |
| T-nkm-06 | Repudiation | Silent loss of real findings (hot/cold 143 -> 0, contrast 1090 -> 56) with no record | low | mitigate | The SUMMARY before/after table from Q/triage.py, the bundle table, and every verdict on a difference from the planning expectation. |
| T-nkm-07 | Elevation of Privilege | Commits sweeping in other instances' files, or a stash stranding work | medium | mitigate | `git add -- <paths>` plus path-limited commits; the stash list compared with Step 0; hard preconditions HALT on dirty task files or a stale base. |
| T-nkm-SC | Tampering | npm/pip/cargo installs | low | accept | This plan installs no packages. |
</threat_model>

<verification>
- `tests/test_critic_fixes_e5_e8.py` is green, with one class per Q26 change plus robustness and purity: RNBO names, RNBO in~, hot/cold, gain message parsing, gain bounds, both inlets, dsp_roles, theme contrast, contrast generator.
- Only the 7 PD-8 existing-test edits were made, and every other existing test passes unchanged, including tests/test_signal_role_migration.py.
- test_calibration_zero_blockers is green with no allowlist change. test_review_patch_no_blockers is green, with the one new `unsafe_gain` entry for slot.maxpat.
- Q/triage.py --check gives mismatch 0 after each commit (1a, 1b, 2, 3), and SUMMARY carries the before/after counts.
- The full suite is green against the baseline of 4782 passed, 5 xfailed, 1 xpassed plus the new tests; the requires_max bundle sweep passes.
- At least 4 `(Q26)` commits exist, none touching patches/. Python 3.10 parse holds, and the stash list is unchanged.
</verification>

<success_criteria>
- Hot/cold warns only on a shared upstream event with cold-after-hot order. It skips p, bpatcher and js targets and never duplicates Q21.
- Gain safety reads ramp times correctly, propagates value bounds, traces both `*~` inlets, and uses DB-driven gain-stage and terminal sets shared with validation.py: live.gain~ is a gain stage; mc.dac~ and plugout~ are terminals.
- Contrast follows the Max 9 default theme in both critic and generator, and ui-presets.md documents it.
- The RNBO critic parses positional param names, and a generator without in~ gets a note.
- Finding counts on committed patches are reported before and after. Every new committed finding is fixed in the checker or allowlisted with a reason, and no patch file is touched.
</success_criteria>

<output>
Create `.planning/quick/261015-nkm-implement-q26-in-planning-reviews-2026-1/261015-nkm-SUMMARY.md` when done.
</output>
