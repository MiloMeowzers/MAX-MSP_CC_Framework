---
phase: quick-261013-cyg
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/maxpat/io_resolvers.py
  - src/maxpat/db_lookup.py
  - tools/help_io.py
  - .claude/max-objects/overrides.json
  - tests/test_io_resolvers.py
  - tests/test_db_lookup.py
  - tests/test_patcher.py
  - tests/fixtures/help_io_baseline.json
autonomous: true
requirements: [C1, S6]

estimate:
  tokens: 75000
  raw_tokens: 75000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "Box text is tokenized with double quotes and backslash escapes respected, and positional args stop at the first @attribute token: `t \"LCD Text / Icon (Inactive)\"` = (1,1) and `combine sound 74 @triggers 1` = (2,2). compute_io_counts re-tokenizes whatever args list it is given, so pre-split and quote-joined args give the same answer."
    - "`r`/`receive` with a name = (0,1); bare `receive` = (1,1)."
    - "`select`/`sel`/`route`/`routepass` with N args = (N+1, N+1). Bare = (2,2): MAX-saved for sel, refpage-derived for route/routepass."
    - "`expr`/`vexpr`/`if` inlets = the highest $iN/$fN/$sN index (1 when there is none). `if … out2` has 2 outlets. `sprintf` inlets = number of format specifiers (min 1). `pipe` with N >= 2 args = (N, N-1); `pipe` with fewer args = (2,1). notein/ctlin drop the outlets their args fix."
    - "Bare pack/pak = (2,1), unpack = (1,2), trigger/t = (1,2), combine = (1,2), and combine N = (N,2). Bare switch = (3,1); b/bangbang bare = (1,2) and `b N` = (1,N); gate~ N = (2,N); bucket N = (1,N) with bare (1,1); buddy N = (N,N); unjoin N = (1,N+1) with bare (1,3); groove~ buf N = (3,N+1); tapout~ = one inlet/outlet per tap; record~ buf N = (N+2,1); jit.pack N = (N,2); jit.unpack N = (1,N+1); mc.route N = (2,N). matrix~, mc.matrix~ and play~ keep the counts Q2 gave them."
    - "Non-formula rules are Python resolver callables in src/maxpat/io_resolvers.py (S6). SUPPORTED_IO_FORMULAS is unchanged, an object never has both a resolver and a variable_io_rules entry (ValueError at load), and every object with a resolver or rule reports variable_io True in memory. The domain JSON files are untouched."
    - "Live help-io oracle: every Q10 target has 0 count mismatches in the bundle. The regenerated committed baseline's only per-name increases over the Q9 baseline are type mismatches unmasked on a Q10 target whose count is now correct (planning observed only bundle/mc.route, 11 boxes), and those are handed to Q11."
    - "validate_patch + review_patch findings over all committed patches/ files are identical before and after. No file under patches/ changes. The full suite is green, and every changed .py file parses under Python 3.10."
  artifacts:
    - path: "src/maxpat/io_resolvers.py"
      provides: "split_box_text, box_args, normalize_args, the per-object resolver callables and IO_RESOLVERS (canonical name -> resolver)"
      contains: "IO_RESOLVERS"
      min_lines: 120
    - path: "src/maxpat/db_lookup.py"
      provides: "compute_io_counts normalizes args, dispatches resolvers before formula rules, has a resolver/rule conflict check, and derives the variable_io flag in memory"
      contains: "IO_RESOLVERS"
    - path: ".claude/max-objects/overrides.json"
      provides: "variable_io_rules: corrected rules for pack/pak/unpack/trigger/combine/switch/unjoin and new rules for gate~/bucket/buddy/bangbang/groove~/tapout~/record~/jit.pack/jit.unpack/mc.route. The select/route/routepass/expr/vexpr rules are removed (now resolvers)."
      contains: "\"tapout~\""
    - path: "tests/test_io_resolvers.py"
      provides: "Tokenizer tests, resolver invariants, one MAX-saved-count assertion per fixed object with a cited source file, and a requires_max live check that every Q10 target is clean in the bundle"
      contains: "Q10_TARGETS"
      min_lines: 200
    - path: "tests/fixtures/help_io_baseline.json"
      provides: "Regenerated Max 9.2.0 help-io baseline with the Q10 mismatches removed"
      contains: "\"schema\": 1"
  key_links:
    - from: "src/maxpat/db_lookup.py"
      to: "src/maxpat/io_resolvers.py"
      via: "compute_io_counts -> normalize_args, then IO_RESOLVERS.get(canonical), before the variable_io/formula path"
      pattern: "normalize_args"
    - from: "tools/help_io.py"
      to: "src/maxpat/io_resolvers.py"
      via: "help_io.box_args delegates to io_resolvers.box_args (Q9 hand-off: quote-aware tokenizer)"
      pattern: "io_resolvers"
    - from: ".claude/max-objects/overrides.json"
      to: "src/maxpat/db_lookup.py"
      via: "variable_io_rules (existing formula vocabulary only) -> _apply_io_formula; trailing_outlets -> _resolve_outlet for unjoin/groove~/jit.unpack"
      pattern: "trailing_outlets"
    - from: "tests/test_io_resolvers.py"
      to: "tools/audit_db.py"
      via: "requires_max TestOracleTargets runs audit_db.run_help_io and asserts 0 bundle count mismatches for Q10_TARGETS"
      pattern: "run_help_io"
---

<objective>
Implement Q10 of `.planning/reviews/2026-10-11-fix-plan.md`: correct argument-dependent I/O counts (review finding C1), using the Q9 help-box oracle as evidence and per-object resolver callables (review §2 S6) wherever the formula mini-language can't express MAX's rule.

Three things change:
- **Tokenizer.** It respects quotes and stops at `@attributes`.
- **Resolvers.** A resolver registry handles receive, the select/route family, expr/vexpr/if, sprintf, pipe, notein and ctlin.
- **Formula rules.** Rules in `overrides.json` `variable_io_rules` are corrected or added, using only formula names that already exist.

Each fix gets a test asserting MAX's saved counts. The committed help-io baseline shrinks, and committed patches are triaged.

Purpose: generated boxes get the inlets and outlets MAX actually creates. Today the following are all wrong: `sel 0` gets 1 inlet, `r foo` gets 1 inlet, bare `unpack` gets 0 outlets, `expr $i1 + $i2 + $i3` gets 5 inlets, and `t "a b"` gets 2 outlets. Wrong counts like these either block valid cords or allow cords to ports that don't exist.

Output: three commits, one per task, each with `(Q10)` in the message. Nothing is pushed.
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

Additions for this execution environment:
- **Suite must stay green.** Q1–Q9 have landed. Expected baseline at HEAD `5587b1c`: **2727 passed, 1 xfailed, 1 xpassed, 29 warnings** (Q9 SUMMARY). The executor re-measures it in Step 0.
- **Worktree precondition (hard).** The executor runs in an isolated git worktree. Its base must contain the Q9 commits (`917fd14`), i.e. `tools/help_io.py` and `tests/fixtures/help_io_baseline.json` must exist. At planning, `origin/main` was `cd5a885`, which lacks Q9, while local `main` was `5587b1c`. If the precondition fails, HALT and report: "worktree base lacks Q9 — push local main (`git push origin main`) or base the worktree on 5587b1c". Don't recreate Q9.
- **Edit scope (observed live at planning).** Only the eight `files_modified` paths may change. In `.claude/max-objects/overrides.json`, only the `variable_io_rules` section may change. **Never edit:**
  - `patches/**`, CLAUDE.md, TECHNICAL.md, README.md, `.claude/skills/**`;
  - any domain `objects.json`, `aliases.json`;
  - the `objects` / `version_map` / `_comment` / `_uncovered_empty_io` sections of overrides.json (those are Q11 territory);
  - `SUPPORTED_IO_FORMULAS`, `_apply_io_formula`.
- **Stale line numbers.** The fix-plan's `db_lookup.py:618-646, 802-806` refs are stale. Live locations at planning:
  - `_validate_variable_io_rules` 211-253;
  - `_load` 108-205;
  - `_resolve_outlet` 653-681;
  - `compute_io_counts` 765-808;
  - `_apply_io_formula` 810-880;
  - `get_outlet_types` 882-943.
- **overrides.json serialization.** It is exactly `json.dumps(data, indent=2, ensure_ascii=True)` with **no trailing newline**; planning verified that this round-trips the current file byte-for-byte. Edit it with a scratch Python script outside the repo: load, mutate only `variable_io_rules`, then write it back in that exact form. Every task that touches it runs the overrides guard in its verify.
- **Leave alone and never stage:**
  - `.planning/tci-phase2/`;
  - the untracked Step-0 files in the other quick dirs (c5i, di7, egf, m87, pkh, qsr, sam, ubw);
  - this task dir's own Step-0 and triage files.
- **Commits.** Another instance may commit concurrently. Commit only each task's `<files>`: `git add -- <paths>`, then `git commit -m "..." -- <paths>`. Never `git push`.
- **Tests never write to the repo.** Each verify compares `git status --porcelain` before and after the pytest run. The only command that writes `tests/fixtures/help_io_baseline.json` is the explicit `python3 tools/audit_db.py --help-io --write-baseline tests/fixtures/help_io_baseline.json`.
- **Python 3.10.** The local interpreter is 3.14. Avoid 3.11+ APIs: `Path.walk`, `tomllib`, `typing.Self`, `itertools.batched`, `except*`, `match`. Every changed `.py` passes `ast.parse(..., feature_version=(3, 10))`. CI (`.github/workflows/test.yml`) runs 3.10 and 3.12 without Max, so every new test that isn't `requires_max` must pass with only the repo DB.
- **Shell.** The shell is zsh. Multi-step gates are wrapped in `bash -c '...'`. Throwaway scripts go in the session scratchpad (else `mktemp -d`), never in the repo. A scratch helper that edits overrides.json or triages patches is not a Rule #5 generator script, because it never writes `.maxpat` files.
</rules>

<assumption_delta_decision>
**Delta:** "fixed counts" become "argument-derived counts" for 16 objects that the DB marks `variable_io: false`: receive, if, sprintf, pipe, notein, ctlin, gate~, bucket, buddy, bangbang, groove~, tapout~, record~, jit.pack, jit.unpack and mc.route. `compute_io_counts` used to return their array lengths regardless of args.

**Decision: promote.** Argument-derived counts replace the fixed ones. MAX-saved help boxes prove the fixed counts wrong (see `<evidence>`). The flag is derived in memory: every canonical name with a resolver or a `variable_io_rules` entry reports `variable_io: True`, so all consumers see one answer. The consumers are Box construction, `Patcher.modify_box`, `_io_is_content_defined` (B2: variable objects recompute their I/O on an args edit), and the audit parser/analyzer. The on-disk domain JSON flags are untouched.

**Consequence to record in SUMMARY:** `modify_box(args=...)` on these 16 objects now recomputes I/O and orphans only out-of-range cords. Before, it kept their I/O as content-defined. `pan`/`pan~` also flip to True in memory, which has no numeric effect because their rules are `fixed:2`.

**Other gates — not applicable:** API coverage (no external API) and schema-push (no ORM/schema files).
</assumption_delta_decision>

<observed_facts>
All of these were measured live at planning on this Mac (Max 9.2.0, build e9c80e453de, 14 packages), HEAD `5587b1c`.

**Oracle before Q10.** `python3 tools/audit_db.py --help-io` gives:
- all sources: 441 mismatching names (439 alias-resolved) and 13,084 mismatching boxes;
- bundle: 164 names.
It runs in ~2.3 s.

**Planning prototype.** A scratch monkeypatch implementing exactly this plan's tokenizer, resolvers and rules; nothing was committed or written to the repo.
- **Oracle:** 414 names and 9,601 boxes; bundle 137 names. 119 (source, name) pairs went to zero.
- **Names fixed in every source:** b, bucket, buddy, combine, ctlin, expr, gate~, groove~, if, jit.pack, jit.unpack, notein, pack, pak, pipe, r, receive, route, routepass, sel, select, sprintf, switch, t, unjoin, unpack, vexpr.
- **Only per-name increase:** bundle/mc.route `type_mismatches` 0 -> 11. Its count is now right, which unmasks a pre-existing override error: overrides.json `objects["mc.route"].outlets[*].signal_role = "audio"` on int outlets. MAX saves them as control. That is Q11's (C9) job and is not fixed here.
- **Full suite under the prototype:** 7 failed, 2720 passed. Six of the failures are existing tests that encode the wrong counts (listed in the tasks); the seventh is TestLiveOracle, the mc.route unmasking, which clears when the baseline is regenerated.
- **Committed-patch triage:** `validate_patch` (on a deepcopy) + `review_patch` over 57 `patches/**/*.maxpat|*.maxhelp` files gave **0 differences** with the prototype. Validation bounds use the box's saved `numinlets`/`numoutlets`, so loaded patches are not re-counted.

**Why many targets currently compute fixed counts.** These objects have `variable_io: false` in the DB, so `compute_io_counts` ignores args: gate~, bucket, buddy, bangbang, groove~, tapout~, record~, jit.pack, jit.unpack, mc.route, receive, notein, ctlin, if, sprintf, pipe.

**DB arrays already hold MAX's bare defaults** for pack (2,1), unpack (1,2), combine (1,2), switch (3,1), select (2,2), route (2,2) and unjoin (1,3). It is the rules that override them wrongly.
</observed_facts>

<evidence>
These are MAX-saved boxes (newobj, from the installed bundle or packages) that the tests cite. Format: object args => (numinlets, numoutlets) — file (help appversion).

**Task 1 objects**
- `r todrive` => (0,1) — C74/help/jitter/jit.anim.drive.maxhelp (9.0.0)
- `receive bem` => (0,1) — C74/help/max/forward.maxhelp (9.0.0)
- `receive` => (1,1) — C74/help/max/receive.maxhelp (9.0.0)
- `t "LCD Text / Icon (Inactive)"` => (1,1) — C74/help/m4l/live.routing.maxhelp (9.0.0)

**Task 2 objects**
- select family:
  - `sel` => (2,2) — C74/help/jitter/jit.playlist.maxhelp (9.0.0)
  - `sel 0 1` => (3,3) — C74/extras/JitterTester.maxpat (9.0.0)
  - `select 1 2 3 4 5 6 7` => (8,8) — C74/packages/Vizzie/help/vz.1easemappr.maxhelp (9.0.3)
- route / routepass:
  - `route point` => (2,2) — C74/help/jitter/jit.anim.path.maxhelp
  - `route time transport` => (3,3) — C74/help/jitter/jit.avc.maxhelp
  - `route "Control Border" "Text / Icon" "Slider Range Value"` => (4,4) — C74/help/m4l/live.colors.maxhelp
  - `routepass 0 1` => (3,3) — C74/help/jitter/jit.displays.maxhelp
  - Bare `route` / `routepass` have no MAX-saved box. The route.maxref.xml / routepass.maxref.xml refpages say: "If there is no argument, there is one other outlet, which is assigned the number 0". So bare = (2,2), refpage-derived, and SUMMARY flags it for MAX confirmation.
- expr / vexpr:
  - `expr $i3 * $i1 + $i2` => (3,1) — C74/help/max/expr.maxhelp (9.1.0)
  - `expr $i2 + 11` => (2,1) — FluidCorpusManipulation/help/fluid.bufnmf~.maxhelp
  - `expr sin (2. * 3.141593 * $f1)` => (1,1) (bundle)
  - `vexpr $f1*($f3-$f2)+$f2 @scalarmode 1` => (3,1) — C74/packages/BEAP/Examples/Synthesis Examples/Resynthesis.maxpat
  - `vexpr int($f1 * 255)` => (1,1) — C74/help/m4l/live.colors.maxhelp
- if:
  - `if $i1 < 8 then bang else out2 bang` => (1,2) — C74/help/jitter/jit.avc.maxhelp
  - `if $i3 == 1 then $f1 $f2 else out2 bang` => (3,2) — C74/help/max/nodes.maxhelp
  - `if $i2 == 1 then $i1` => (2,1) — C74/help/jitter/jit.displays.maxhelp
- sprintf:
  - `sprintf %d - %d x %d\, %d bit\, %dHz %s` => (6,1) — C74/help/jitter/jit.displays.maxhelp (the saved text contains a literal backslash before each comma)
  - `sprintf symout %s%s` => (2,1), `sprintf %ld 34 %ld 555` => (2,1), `sprintf %c%c%c%c` => (4,1) — all C74/help/max/sprintf.maxhelp
- pipe:
  - `pipe 0 0 1000` => (3,2), `pipe 0. 0. 0. 2000` => (4,3), `pipe 500` => (2,1) — C74/help/max/pipe.maxhelp
  - `pipe 0 0 0 0 0 0 0 0 0 0 0 0 500` => (13,12) (bundle)
- notein:
  - `notein` => (1,3) — C74/extras/MIDItester.maxpat (8.1.2)
  - `notein a` => (1,3), `notein 17` => (1,2), `notein b 6` => (1,2) — C74/help/max/bendin.maxhelp
- ctlin:
  - `ctlin` => (1,3) — C74/extras/MIDItester.maxpat
  - `ctlin 7` => (1,2) — C74/help/max/linedrive.maxhelp
  - `ctlin 33 1` => (1,1), `ctlin -1 4` => (1,2), `ctlin a 1` => (1,2) — C74/help/max/ctlin.maxhelp

**Task 3 objects**
- pack / pak / unpack:
  - `pack` => (2,1) — C74/extras/KeyMidi.maxpat (9.0.5)
  - `pak` => (2,1) — C74/help/m4l/live.push.maxhelp (9.1.3)
  - `pak 0 0 0` => (3,1) — C74/help/max/jit.cellblock.maxhelp
  - `unpack` => (1,2) — C74/extras/GlobalTransport.maxpat (8.6.0)
- trigger: bare `trigger`/`t` has no MAX-saved newobj box. trigger.maxref.xml says "If there are no arguments, there are two outlets", so bare = (1,2), refpage-derived.
- combine:
  - `combine sound 74 @triggers 1` => (2,2) — C74/help/max/combine.maxhelp
  - `combine` => (1,2) — dada/help/dada.machines.maxhelp (7.3.4)
  - `combine e i` => (2,2) (abclib)
- switch:
  - `switch` => (3,1) — C74/help/max/switch.maxhelp
  - `switch 3` => (4,1) — C74/help/jitter/jit.keyscreen.maxhelp
- unjoin:
  - `unjoin` => (1,3) — C74/help/jitter/jit.playlist.maxhelp
  - `unjoin 4` => (1,5) — C74/help/msp/plot~.maxhelp
- gate~:
  - `gate~ 3 @ramptime 100` => (2,3) — C74/help/msp/gate~.maxhelp
  - `gate~ 5 2` => (2,5) — C74/help/max/crosspatch.maxhelp
  - `gate~` => (2,1) — C74/help/msp/freqshift~.maxhelp
- bucket / buddy:
  - `bucket` => (1,1) — C74/help/max/anal.maxhelp
  - `bucket 4 1` => (1,4) — C74/help/max/bucket.maxhelp
  - `buddy 4` => (4,4) and `buddy` => (2,2) — C74/help/max/buddy.maxhelp
- b / bangbang:
  - `b` => (1,2) — C74/extras/GlobalTransport.maxpat
  - `b 1` => (1,1) — C74/help/max/cpuclock.maxhelp
  - `bangbang` => (1,2) — C74/packages/Node for Max/patchers/debug-monitor/n4m.monitor.maxpat
  - `b 17` => (1,17) (bundle)
- groove~:
  - `groove~ audio 2` => (3,3) — C74/help/m4l/chucker~.maxhelp
  - `groove~ helpgroove02 4 @loop 1` => (3,5) — C74/help/msp/groove~.maxhelp
- tapout~:
  - `tapout~ 0 0` => (2,2) — C74/patchers/m4l/Lessons resources/M4L.dl.vdelay~.maxpat
  - `tapout~ 100` => (1,1) — C74/help/msp/plugin~.maxhelp
- record~:
  - `record~ this 2` => (4,1) — C74/media/legacy-tutorials/msp-tut/mypvoc2~.maxpat (7.0.0)
  - `record~ foo` => (3,1) — C74/help/msp/plugphasor~.maxhelp
- jit.pack / jit.unpack:
  - `jit.pack 2` => (2,2) and `jit.unpack 2` => (1,3) — C74/help/jitter/jit.fft.maxhelp
  - `jit.pack 3 float32` => (3,2) and `jit.unpack 5 float32` => (1,6) — C74/help/jitter/jit.p.shiva.maxhelp
- mc.route: `mc.route 4` => (2,4) — C74/help/msp/mc.pack~.maxhelp

**Refpage corroboration:** bucket ("no argument: one outlet"), buddy ("no argument: two inlets and two outlets"), unjoin ("in addition to the rightmost outlet, which is always present"), pipe (final arg is the delay time), ctlin ("negative number recognizes all controller numbers"), notein ("a number alone can be used in place of a letter" = channel) and sprintf ("number of inlets is determined by the number of changeable arguments").
</evidence>

<io_spec>
This is the exact behavior to implement. Resolvers are keyed by **canonical** name; the aliases `r`, `sel`, `b` and `t` resolve through aliases.json.

**Arg normalization** (every `compute_io_counts` call):
1. Join the given args with single spaces (`str()` each element).
2. Re-tokenize with `split_box_text`.
3. Truncate at the first token starting with `@`.

`split_box_text(text)` splits on whitespace outside double quotes. A double quote toggles the quoted state and stays in the token. A backslash makes the next character literal and stays in the token, so neither `\"` nor `\ ` (escaped space) toggles or splits. Empty input returns []. An unbalanced quote runs to the end of the text as one token. The function never raises.

`box_args(text)` returns `(token 0, positional args up to the first @-token)`, or `("", [])` for empty text.

**Resolvers** take `(args, (default_inlets, default_outlets))`, where the defaults are the DB array lengths, and return `(inlets, outlets)`:
- `receive`: (0,1) when there is at least one arg; else the defaults (1,1).
- `select`, `route`, `routepass`: n = max(len(args), 1); return (n+1, n+1).
- `expr`, `vexpr`:
  - inlets = the largest integer N among all matches of `\$[ifs](\d+)` in the joined args, or 1 when there is no match;
  - outlets = 1.
- `if`:
  - inlets as for expr;
  - outlets = 2 when any arg token equals `out2`, else 1.
- `sprintf`:
  - remove every literal `%%` from the joined args;
  - count matches of: a percent sign, flags `[-+ #0]*`, optional width digits, optional precision (`.` plus digits), optional length `hh|h|ll|l|L|q|j|z|t`, and a conversion char in `[diouxXeEfFgGaAcs]`;
  - inlets = max(count, 1); outlets = 1.
  - The `symout` keyword has no specifier, so it needs no special case.
- `pipe`: k = max(len(args) - 1, 1); return (k+1, k).
- `notein`: inlets 1; outlets 2 when any arg parses with `int()`, else 3.
- `ctlin`:
  - inlets 1;
  - ints = args that parse with `int()`, in order;
  - outlets = 3, minus 1 when ints is non-empty and ints[0] >= 0 (a specific controller), minus 1 more when len(ints) >= 2 (a channel).

**Formula rules** live in overrides.json `variable_io_rules` and use existing formula names only:

| object | inlet_count | outlet_count | defaults | trailing_outlets | change |
|---|---|---|---|---|---|
| pack | arg_count_or_default | fixed:1 | default_inlets 2 | – | formula arg_count -> arg_count_or_default |
| pak | arg_count_or_default | fixed:1 | default_inlets 2 | – | same |
| unpack | fixed:1 | arg_count_or_default | default_outlets 2 | – | same |
| trigger | fixed:1 | arg_count_or_default | default_outlets 2 | – | same |
| combine | arg_count_or_default | fixed:2 | default_inlets 1, default_outlets 2 | – | outlets fixed:1 -> fixed:2; bare inlets 1 |
| switch | first_arg+1 | fixed:1 | default_inlets 3 | – | default_inlets 2 -> 3 |
| unjoin | fixed:1 | first_arg+1 | default_outlets 3 | 1 | first_arg -> first_arg+1, default 3, trailing 1 |
| gate~ | fixed:2 | first_arg | default_outlets 1 | – | new |
| bucket | fixed:1 | first_arg | default_outlets 1 | – | new |
| buddy | first_arg | first_arg | default_inlets 2, default_outlets 2 | – | new |
| bangbang | fixed:1 | first_arg | default_outlets 2 | – | new |
| groove~ | fixed:3 | second_arg+1 | default_outlets 2 | 1 | new |
| tapout~ | arg_count_or_default | arg_count_or_default | default_inlets 1, default_outlets 1 | – | new |
| record~ | second_arg+2 | fixed:1 | default_inlets 3 | – | new |
| jit.pack | first_arg | fixed:2 | default_inlets 4 | – | new |
| jit.unpack | fixed:1 | first_arg+1 | default_outlets 5 | 1 | new |
| mc.route | fixed:2 | first_arg | default_outlets 2 | – | new |

Every rule carries a `description` and an `_audit` `{source: "Q10 / C1 (261013-cyg): <MAX-saved evidence from <evidence>>", confidence: "HIGH"}`. trigger and combine get `confidence: "MEDIUM"` for the refpage-derived bare case.

**Removed from variable_io_rules** in Task 2: `select`, `route`, `routepass`, `expr`, `vexpr`. These become resolvers, and each removed rule's `description`/`_audit` meaning moves into its resolver's docstring (e.g. vexpr "refpage-verified 2026-09-27").

**Unchanged:** expr~ (RNBO-only; Q12), matrix~, mc.matrix~, play~, sfplay~ and every other existing rule.
</io_spec>

<source_audit>
| Source | Item | Covered by |
|---|---|---|
| GOAL (Q10) | Default counts: bare pack/pak/unpack/trigger/t/combine use the defaults | Task 3 |
| GOAL | Extra inlets: route/routepass/select/sel get arg_count+1 inlets | Task 2 |
| GOAL | expr/vexpr/if count from the highest $ index; `if … out2` has 2 outlets | Task 2 |
| GOAL | Tokenizing: quotes respected (`t "a b"` is 1 argument) | Task 1 |
| GOAL | One port per argument: gate~ N, bucket N, buddy N | Task 3 |
| GOAL | Trailing outlets: unjoin N (+1) | Task 3 |
| GOAL | Trailing outlets: matrix~/mc.matrix~ N M (+dump), play~ buf N (+bang) | Already shipped by Q2 (d0885b8). Task 3 keeps them in Q10_TARGETS so they stay at 0 mismatches |
| GOAL | groove~, tapout~, record~, jit.pack/jit.unpack, mc.route | Task 3 |
| GOAL | notein/ctlin, sprintf, pipe | Task 2 |
| GOAL | Fixed counts: r/receive with a name = 0 inlets | Task 1 |
| GOAL | Fixed counts: switch 3 inlets; b 2 outlets | Task 3 |
| GOAL | Implementation: per-object resolver callables (S6) over extending the formula language | Task 1 (mechanism), Task 2 (resolvers); SUPPORTED_IO_FORMULAS frozen (test) |
| GOAL | Tests: each fix asserts MAX's saved counts; shrink the baseline | Tasks 1-3 (cited evidence rows); baseline regenerated in Tasks 1 and 3 |
| GOAL | Triage: committed-patch connections may validate differently (rule 3) | Step 0 + Task 3 triage diff |
| Q9 hand-off | Replace `help_io.box_args` with the quote-aware tokenizer | Task 1 |
| REQ | C1 | Tasks 1-3 |
| REQ | S6 (resolver callables + help-box oracle test) | Tasks 1-2 + TestOracleTargets |
| RESEARCH / CONTEXT | None for quick tasks; the fix-plan rules are copied into `<rules>` | — |

Exclusions (not gaps):
- mc.route outlet signal roles (C9) → Q11.
- expr~ → Q12.
- The 19 other arg-dependent bundle names left mismatching after the prototype (e.g. dict.pack, print, mtr, matrix, polyin, jit.cycle) are not in Q10's object list; rule 7 applies, and they are listed in SUMMARY as follow-ups.
- Inlet-layout modelling (record~ N inlet 1 is the channel-2 signal, not the DB's start point) is S6/Q33 scope.
</source_audit>

<context>
@.planning/reviews/2026-10-11-fix-plan.md
@.planning/reviews/2026-10-11-repo-review.md
@.planning/quick/261012-ubw-implement-q9-in-planning-reviews-2026-10/261012-ubw-SUMMARY.md
@src/maxpat/db_lookup.py
@tools/help_io.py
@tests/test_help_io.py
@tests/test_db_lookup.py
@.claude/max-objects/overrides.json
</context>

<tasks>

<task type="tracer" tdd="true">
  <name>Task 1 (tracer): quote-aware tokenizer + resolver dispatch, end-to-end on one path (r/receive) through compute_io_counts, Patcher.add_box, the help-io oracle and its committed baseline</name>
  <files>src/maxpat/io_resolvers.py, src/maxpat/db_lookup.py, tools/help_io.py, tests/test_io_resolvers.py, tests/fixtures/help_io_baseline.json</files>
  <read_first>
    - .planning/reviews/2026-10-11-repo-review.md rows C1 (line ~83) and S6 (line ~197) — rule 1
    - src/maxpat/db_lookup.py lines 1-75, 100-255 and 650-945 (constants, _load, _validate_variable_io_rules, _resolve_outlet, compute_io_counts, _apply_io_formula, get_outlet_types)
    - tools/help_io.py lines 125-145 (box_args) and 281-356 (_SourceScan._box)
    - tests/test_help_io.py lines 1-60 and 609-692 (imports, BASELINE, TestCommittedBaseline, TestLiveOracle pattern)
    - src/maxpat/patcher.py lines 567-589 (_io_is_content_defined) and 640-665 (modify_box recompute)
  </read_first>
  <behavior>
    - split_box_text: `t "a b" c` -> [t, "a b", c] (quotes kept); `x\ y z` -> [x\ y, z]; `expr store(tab3[-1]\,$i1\,$i2)` -> 2 tokens; `"unclosed a b` -> one token; empty or whitespace -> []; tabs/newlines split.
    - box_args: `gate~ 3 @ramptime 100` -> (gate~, [3]); `route "A B" c` -> (route, ["A B" token, c]); empty -> ("", []).
    - normalize_args: pre-split [`"LCD`, `Text`, `/`, `Icon`, `(Inactive)"`] and the single quoted token both give a 1-element list. Args after an @-token are dropped. Non-str elements are accepted via str(). None -> [].
    - help_io.box_args delegates to io_resolvers.box_args (same quote-aware results).
    - compute_io_counts with the evidence rows for Task 1: r [todrive] (0,1), receive [bem] (0,1), receive [] (1,1), t with the LCD quoted text (1,1) in both pre-split and quoted forms.
    - Patcher.add_box("r", ["foo"]) has numinlets 0 and numoutlets 1. `db.lookup("receive")["variable_io"]` is True (derived), so `_io_is_content_defined` on an `r foo` box is False.
    - Invariants: SUPPORTED_IO_FORMULAS equals the 10 base strings (`""`, arg_count, arg_count+1, arg_count_or_default, first_arg, first_arg+1, second_arg, second_arg+1, second_arg+2, inherited_from_subpatch). Every IO_RESOLVERS key is a canonical DB name (not an alias key), resolves via lookup, and has no variable_io_rules entry. A tmp_path DB whose overrides.json has a variable_io_rules entry for `receive` raises ValueError at ObjectDatabase construction, naming `receive`.
    - requires_max TestOracleTargets: the live oracle's bundle mismatches show count_mismatches == 0 for every name in Q10_TARGETS (Task 1 value: r, receive, t). It skips when the installed bundle version differs from the committed baseline's max_version.
  </behavior>
  <precondition>The worktree HEAD contains commit 917fd14 (Q9): `git merge-base --is-ancestor 917fd14 HEAD` succeeds and both tools/help_io.py and tests/fixtures/help_io_baseline.json exist.</precondition>
  <action>
**Step 0** (Q = `.planning/quick/261013-cyg-implement-q10-in-planning-reviews-2026-1`; the files written here are untracked and never staged):
1. Assert the precondition. If it fails, HALT with the message in `<rules>`.
2. Write `git rev-parse HEAD` to Q/base-sha.txt, and `git stash list` to Q/stash-list-before.txt.
3. Run `python3 -m pytest -q -p no:cacheprovider` and write its last line to Q/baseline-pytest.txt. Expect 2727 passed, 1 xfailed, 1 xpassed, 29 warnings. If anything fails at base, stop and report.
4. Write `python3 tools/audit_db.py --help-io --json Q/help-io-before.json`.
5. Write a scratch triage script in the session scratchpad. For every `patches/**/*.maxpat` and `patches/**/*.maxhelp` (sorted), it:
   - parses the JSON, skipping unparseable files;
   - runs `validate_patch(copy.deepcopy(d), db=db)` and `review_patch(copy.deepcopy(d), db=db)` with a single `ObjectDatabase()` and warnings ignored;
   - stores, per file, the sorted list of `V|layer|level|message` and `C|severity|finding` strings.
   Run it into Q/triage-base.json. Planning saw 57 files.

**Implementation**
1. Create `src/maxpat/io_resolvers.py`.
   - Module docstring: explain S6/C1, that the module never imports db_lookup (to avoid a cycle), and that resolvers are keyed by canonical name and win over `variable_io_rules`.
   - Implement `split_box_text`, `box_args`, `normalize_args` exactly as in `<io_spec>`.
   - Add the `_receive` resolver, an `IoResolver` type alias (`Callable[[list[str], tuple[int, int]], tuple[int, int]]`) and `IO_RESOLVERS = {"receive": _receive}`.
   - Each resolver's docstring cites its MAX-saved evidence.
   - Python 3.10: `from __future__ import annotations`, `typing.Callable`.
2. In `src/maxpat/db_lookup.py`, import `IO_RESOLVERS` and `normalize_args` from `src.maxpat.io_resolvers`.
   - (a) In `_validate_variable_io_rules`, raise ValueError when any canonical name is both in IO_RESOLVERS and in the loaded rules. The message names the object and says to delete the rule.
   - (b) At the end of `_load`, after the overrides merge, the schema validation and the signal_role writethrough, set `variable_io = True` in memory on every `self._objects` entry whose name is in the rules or in IO_RESOLVERS. This is the assumption-delta decision. Skip names not in `_objects`, because tmp_path DBs are tiny.
   - (c) `compute_io_counts`:
     - normalize args first;
     - unknown object -> (0,0) as before;
     - compute defaults from the DB arrays;
     - when the canonical name is in IO_RESOLVERS, return the resolver result;
     - otherwise keep the existing variable_io/rule/formula path unchanged, now fed the normalized args.
     Update the docstring, mentioning resolvers, normalization and @-truncation. Don't touch `SUPPORTED_IO_FORMULAS`, `_apply_io_formula`, `_resolve_outlet` or `get_outlet_types`; the latter two already route through compute_io_counts.
3. In `tools/help_io.py`, make `box_args` delegate to `io_resolvers.box_args`. This is the Q9 hand-off. Keep the public name and signature, and update the module docstring line "token 0 of text.split()" to "quote-aware tokens". It still never imports tools.audit_db.
4. **Tests first.** Create `tests/test_io_resolvers.py` with:
   - a module constant `Q10_TARGETS = ("r", "receive", "t")` (grown by Tasks 2-3);
   - the tokenizer/normalize/box_args tests;
   - a parametrized `MAX_SAVED` table of (name, args, expected, citation). Each row's citation string is the `<evidence>` file plus box text, and the test asserts `ObjectDatabase().compute_io_counts(name, args) == expected`;
   - the invariant tests and the add_box/derived-flag tests;
   - the tmp_path conflict test (minimal db layout as in tests/test_help_io.py `_make_fake_db`: `max/objects.json` containing `receive`, and overrides.json with that rule);
   - `@pytest.mark.requires_max class TestOracleTargets`, with a module-scoped fixture calling `audit_db.run_help_io(max_app=MAX_APP_PATH)` and the version-skip pattern from TestLiveOracle._diff_or_skip.
   Imports follow tests/test_help_io.py: `import tools.audit_db as audit_db`, `from tests.conftest import MAX_APP_PATH`, `from tools import help_io`.
   Run the new file and record the red count before implementing; then make it pass.
5. Regenerate the baseline with `python3 tools/audit_db.py --help-io --write-baseline tests/fixtures/help_io_baseline.json`. Gate it against the Q9 baseline at base-sha: zero regressions are allowed in this task. Expected improvements: r and receive in every source, t in the bundle.
6. Run the triage script again into Q/triage-t1.json and diff it against triage-base.json. Expect identical. If it differs, classify per rule 3; never edit patches.
7. Commit the five files: `feat(io): quote-aware box tokenizer and per-object I/O resolvers; r/receive with a name has 0 inlets (Q10)`.
  </action>
  <verify>
    <automated>python3 -c "import ast,sys; [ast.parse(open(f).read(), filename=f, feature_version=(3, 10)) for f in sys.argv[1:]]; print('PY310-SYNTAX-OK')" src/maxpat/io_resolvers.py src/maxpat/db_lookup.py tools/help_io.py tests/test_io_resolvers.py && python3 -c "import json,subprocess,sys; sys.path.insert(0,'.'); from tools import help_io; q='.planning/quick/261013-cyg-implement-q10-in-planning-reviews-2026-1/'; sha=open(q+'base-sha.txt').read().strip(); old=json.loads(subprocess.check_output(['git','show',sha+':tests/fixtures/help_io_baseline.json'])); new=json.load(open('tests/fixtures/help_io_baseline.json')); d=help_io.diff_baselines(old,new); print(len(d['improvements']),'improvements', d['regressions']); a=json.load(open(q+'triage-base.json')); b=json.load(open(q+'triage-t1.json')); print('TRIAGE-SAME' if a==b else 'TRIAGE-DIFF'); sys.exit(1 if (d['regressions'] or not a==b) else 0)" && bash -c 'S=$(mktemp); git status --porcelain > "$S"; python3 -m pytest -q -p no:cacheprovider; R=$?; S2=$(mktemp); git status --porcelain > "$S2" || { echo GIT-STATUS-FAILED; exit 1; }; diff -q "$S" "$S2" >/dev/null || { echo TESTS-CHANGED-TREE; exit 1; }; exit $R'</automated>
  </verify>
  <done>
    - io_resolvers.py exists with the tokenizer and the receive resolver, and compute_io_counts dispatches through it.
    - `r foo` = (0,1), `t "LCD Text / Icon (Inactive)"` = (1,1), and help_io.box_args is quote-aware.
    - The baseline is regenerated with 0 regressions, and the triage is identical.
    - The full suite is green: base passes plus the new tests, 1 xfailed, 1 xpassed. TestOracleTargets passes on this Mac.
    - One `(Q10)` commit touches exactly the five files.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: resolvers for select/sel, route, routepass, expr, vexpr, if, sprintf, pipe, notein, ctlin; retire their formula rules</name>
  <files>src/maxpat/io_resolvers.py, .claude/max-objects/overrides.json, tests/test_io_resolvers.py, tests/test_db_lookup.py, tests/test_patcher.py</files>
  <read_first>
    - src/maxpat/io_resolvers.py (from Task 1)
    - tests/test_db_lookup.py lines 595-735 (the route/routepass tests rewritten here)
    - tests/test_patcher.py lines 296-335 (TestVariableIO)
    - .claude/max-objects/overrides.json `variable_io_rules` entries for select, route, routepass, expr, vexpr (starting near line 16463)
  </read_first>
  <behavior>
    - Every Task 2 `<evidence>` row holds via compute_io_counts, including `sel` bare (2,2), `route` with the three quoted args (4,4), the sprintf row with `\,` escapes (6,1), the 13-arg pipe (13,12), and every notein/ctlin row.
    - Refpage-derived rows (citation says "refpage"): `route` [] (2,2) and `routepass` [] (2,2).
    - Edge rows: `expr` with no `$` and a quoted body (1,1); `sprintf` [] (1,1); `sprintf` with only `%%` (1,1); `pipe` [] (2,1); `if` without out2 (N,1); `ctlin none` (1,3); `notein "Sensel Morph"` as one quoted token (1,3).
    - Outlet types: get_outlet_types for `sel 0 1` is 3 control entries and for `if … out2 …` is 2 control entries (expansion inherits the last DB outlet).
    - The overrides guard passes: only variable_io_rules changed, exactly the keys expr, route, routepass, select and vexpr (all removed), and the byte format is unchanged.
    - Q10_TARGETS grows by sel, select, route, routepass, expr, vexpr, if, sprintf, pipe, notein, ctlin, and TestOracleTargets passes.
  </behavior>
  <action>
1. **Tests first.** In `tests/test_io_resolvers.py`, add the Task 2 `MAX_SAVED` rows (evidence, refpage and edge rows from `<behavior>`) and extend Q10_TARGETS.
2. **Rewrite the existing tests that encode counts MAX contradicts.** Rule 3 doesn't apply here: these are not patch files. In each rewritten docstring, cite Q10/C1 and the evidence file:
   - tests/test_db_lookup.py `test_compute_io_counts_route_no_args_post_fn03`: expected (1,1) becomes (2,2). Rename it to `test_compute_io_counts_route_no_args_matches_refpage`.
   - `test_compute_io_counts_routepass_uses_loaded_formula`: (1,3)/(1,4) become (3,3)/(4,4), and it additionally asserts that `"routepass" in IO_RESOLVERS` and `"routepass" not in db._variable_io_rules`. Rename it to `test_compute_io_counts_routepass_resolver`.
   - `test_compute_io_counts_routepass_normalized_default_outlets`: it anchored a rule shape that no longer exists, so it now asserts `routepass ["a","b"] == (3,3)` and `routepass [] == (2,2)`.
   - tests/test_patcher.py `TestVariableIO.test_route_two_args`: numinlets 1 becomes 3 (MAX `route time transport` = (3,3)).
   Record the red count.
3. **Implement the resolvers** in `src/maxpat/io_resolvers.py` exactly per `<io_spec>`:
   - one shared selector-family function registered under select, route and routepass;
   - one shared dollar-index function for expr and vexpr;
   - separate functions for `if`, `sprintf`, `pipe`, `notein` and `ctlin`;
   - compile the regexes at module level.
   Each docstring cites the evidence. The route/routepass docstring states that the bare case is refpage-derived. The vexpr docstring keeps the removed rule's "refpage-verified 2026-09-27" note.
4. **Edit overrides.json with a scratch script.** Delete exactly the `variable_io_rules` keys select, route, routepass, expr and vexpr, then write back with `json.dumps(data, indent=2, ensure_ascii=True)` and no trailing newline. Task 1's load-time check would raise if any of them stayed.
5. Run the triage script into Q/triage-t2.json and diff it against triage-base.json; expect it identical.
6. **Baseline.** Don't regenerate the baseline unless TestLiveOracle fails. It should pass because every change is an improvement. If it fails only through a type mismatch unmasked on a Task 2 target whose count is now 0, regenerate the baseline, add it to this commit, and record it.
7. Commit the five files: `feat(io): resolvers for select/route/routepass (N+1 inlets), expr/vexpr/if ($-index, out2), sprintf, pipe, notein, ctlin; retire their formula rules (Q10)`.
  </action>
  <verify>
    <automated>python3 -c "import ast,sys; [ast.parse(open(f).read(), filename=f, feature_version=(3, 10)) for f in sys.argv[1:]]; print('PY310-SYNTAX-OK')" src/maxpat/io_resolvers.py tests/test_io_resolvers.py tests/test_db_lookup.py tests/test_patcher.py && python3 -c "import json,subprocess; q='.planning/quick/261013-cyg-implement-q10-in-planning-reviews-2026-1/'; sha=open(q+'base-sha.txt').read().strip(); t=open('.claude/max-objects/overrides.json').read(); assert json.dumps(json.loads(t),indent=2,ensure_ascii=True)==t, 'FORMAT'; b=json.loads(subprocess.check_output(['git','show',sha+':.claude/max-objects/overrides.json'])); n=json.loads(t); assert all(b.get(k)==n.get(k) for k in set(b)|set(n) if not k=='variable_io_rules'), 'NON-RULE-CHANGE'; br=b['variable_io_rules']; nr=n['variable_io_rules']; ch=sorted(k for k in set(br)|set(nr) if not br.get(k)==nr.get(k)); assert ch==sorted('expr route routepass select vexpr'.split()), ch; assert not set(nr)&set('expr route routepass select vexpr'.split()); a=json.load(open(q+'triage-base.json')); c=json.load(open(q+'triage-t2.json')); assert a==c, 'TRIAGE-DIFF'; print('OVERRIDES-GUARD-OK TRIAGE-SAME')" && bash -c 'S=$(mktemp); git status --porcelain > "$S"; python3 -m pytest -q -p no:cacheprovider; R=$?; S2=$(mktemp); git status --porcelain > "$S2" || { echo GIT-STATUS-FAILED; exit 1; }; diff -q "$S" "$S2" >/dev/null || { echo TESTS-CHANGED-TREE; exit 1; }; exit $R'</automated>
  </verify>
  <done>
    - All ten resolvers are registered, and every Task 2 evidence row passes.
    - The five formula rules are removed with no other change to overrides.json.
    - The four rewritten tests pass with MAX values.
    - The triage is identical, and the full suite is green, including TestLiveOracle and TestOracleTargets.
    - One `(Q10)` commit touches exactly the task's files.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: formula-rule fixes in variable_io_rules (pack/pak/unpack/trigger/combine/switch/unjoin, new gate~/bucket/buddy/bangbang/groove~/tapout~/record~/jit.pack/jit.unpack/mc.route), baseline regenerated, final triage and 3.10 run</name>
  <files>.claude/max-objects/overrides.json, tests/test_io_resolvers.py, tests/test_db_lookup.py, tests/fixtures/help_io_baseline.json</files>
  <read_first>
    - `<io_spec>` formula table and `<evidence>` Task 3 objects
    - tests/test_db_lookup.py lines 595-660 (combine and trigger assertions rewritten here) and 880-930 (matrix~/play~/mc.matrix~ trailing tests, which must stay green)
    - src/maxpat/db_lookup.py _resolve_outlet (trailing_outlets guard `0 < trailing < len(db_outlets)`)
  </read_first>
  <behavior>
    - Every Task 3 `<evidence>` row holds via compute_io_counts. The refpage row for trigger [] is (1,2), and for t [] it is (1,2).
    - Layout via trailing_outlets:
      - `groove~ a 4`: get_outlet_types gives 5 entries, all `signal`, and get_signal_role on outlet 4 equals the DB's sync outlet role.
      - `unjoin 4`: 5 outlets, all control.
      - `jit.unpack 2`: 3 entries, all control.
      - `gate~ 3`: 3 entries, all signal.
      - `tapout~ 0 0`: 2 entries, both signal.
    - The modify_box consequence of the assumption delta: a loaded `gate~ 3` box with cords on outlets 0-2, edited to args [2], ends with numoutlets 2 and orphans exactly the outlet-2 cord.
    - Q10_TARGETS grows by pack, pak, unpack, trigger, combine, switch, unjoin, gate~, bucket, buddy, b, bangbang, groove~, tapout~, record~, jit.pack, jit.unpack, mc.route, matrix~, mc.matrix~, play~, and TestOracleTargets passes.
    - The overrides guard passes over exactly the 22 changed keys (5 removed in Task 2, 7 modified, 10 added).
    - The baseline diff against the Q9 baseline has no regression except type mismatches on Q10 targets whose count_mismatches are 0 (planning expects only bundle/mc.route type_mismatches 0 -> 11).
  </behavior>
  <action>
1. **Tests first.** In `tests/test_io_resolvers.py`, add the Task 3 `MAX_SAVED` rows, the layout/type tests and the gate~ modify_box test. For the modify_box test, build the loaded box the same way tests/test_edit_keeps_user_work.py `_port_harness` does, or construct it through `Patcher.from_dict` with a saved `gate~ 3` box plus three print boxes. Extend Q10_TARGETS.
2. **Rewrite** tests/test_db_lookup.py `test_compute_io_counts_honors_overrides_rules_for_lifted_objects`:
   - combine [a,b,c]: (3,1) becomes (3,2);
   - combine []: (0,1) becomes (1,2), citing combine.maxhelp and dada.machines.maxhelp;
   - the cycle and router assertions stay unchanged.
   Rewrite `test_compute_io_counts_trigger_no_args_post_fn03` to expect (1,2), cite the trigger refpage, and rename it `test_compute_io_counts_trigger_no_args_matches_refpage`. Both docstrings note that MAX evidence overturns FN-03 of REVIEW 260420-j15.
   Record the red count.
3. **Edit overrides.json `variable_io_rules`** with a scratch script, per the `<io_spec>` table:
   - modify pack, pak, unpack, trigger, combine, switch and unjoin, keeping their existing `_audit`/`description` keys but updating the text;
   - add gate~, bucket, buddy, bangbang, groove~, tapout~, record~, jit.pack, jit.unpack and mc.route, each with `description` and `_audit`;
   - write back in the exact serialization; leave no other section changed.
   The `trailing_outlets` values must satisfy the existing positive-int validator and `_resolve_outlet`'s `trailing < len(db_outlets)` guard: unjoin has 3 DB outlets, groove~ 2, jit.unpack 5.
4. **Regenerate the baseline** with `python3 tools/audit_db.py --help-io --write-baseline tests/fixtures/help_io_baseline.json` and run the allow-rule gate (verify).
   - The allow rule is mechanical: a regression is allowed only when the field is `type_mismatches`, the name is a Q10 target, and its count_mismatches is now 0.
   - Any other regression is a bug in this task; fix it, don't allowlist it.
   - Expect bundle/mc.route type_mismatches 0 -> 11. That is the override `signal_role: audio` on int outlets, which goes to Q11 and is not fixed here.
5. **Final triage.** Write Q/triage-after.json and diff it against triage-base.json; expect it identical. Write `python3 tools/audit_db.py --help-io --json Q/help-io-after.json` for the SUMMARY figures.
6. **Python 3.10 run.** If `uv` is available:
   - create a throwaway 3.10 venv in a mktemp dir;
   - `uv pip install -r requirements-dev.txt`;
   - run `MAXPAT_TEST_MAX_APP=/nonexistent/Max.app <venv>/bin/python -m pytest -q -p no:cacheprovider -rs tests/test_io_resolvers.py tests/test_db_lookup.py tests/test_help_io.py`;
   - expect green, with requires_max tests skipped.
   Otherwise record UV-PY310-UNAVAILABLE in SUMMARY. Don't redirect HOME; the worktree sandbox refused it in Q9.
7. Commit the four files: `fix(db): variable_io_rules match MAX-saved help boxes — bare pack/pak/unpack/trigger/combine defaults, switch/b defaults, gate~/bucket/buddy/unjoin/groove~/tapout~/record~/jit.pack/jit.unpack/mc.route arg rules; help-io baseline shrinks (Q10)`.
8. **Final checks:**
   - `git stash list` equals Q/stash-list-before.txt;
   - at least 3 `(Q10)` commits since base-sha;
   - nothing under patches/, CLAUDE.md, TECHNICAL.md, README.md, `.claude/skills` or the domain objects.json files differs from base-sha, in HEAD or in the working tree.
  </action>
  <verify>
    <automated>python3 -c "import ast,sys; [ast.parse(open(f).read(), filename=f, feature_version=(3, 10)) for f in sys.argv[1:]]; print('PY310-SYNTAX-OK')" tests/test_io_resolvers.py tests/test_db_lookup.py && python3 -c "import json,subprocess,sys; sys.path.insert(0,'.'); from tools import help_io; q='.planning/quick/261013-cyg-implement-q10-in-planning-reviews-2026-1/'; sha=open(q+'base-sha.txt').read().strip(); t=open('.claude/max-objects/overrides.json').read(); assert json.dumps(json.loads(t),indent=2,ensure_ascii=True)==t, 'FORMAT'; b=json.loads(subprocess.check_output(['git','show',sha+':.claude/max-objects/overrides.json'])); n=json.loads(t); assert all(b.get(k)==n.get(k) for k in set(b)|set(n) if not k=='variable_io_rules'), 'NON-RULE-CHANGE'; br=b['variable_io_rules']; nr=n['variable_io_rules']; ch=sorted(k for k in set(br)|set(nr) if not br.get(k)==nr.get(k)); exp=sorted('expr route routepass select vexpr pack pak unpack trigger combine switch unjoin gate~ bucket buddy bangbang groove~ tapout~ record~ jit.pack jit.unpack mc.route'.split()); assert ch==exp, ch; old=json.loads(subprocess.check_output(['git','show',sha+':tests/fixtures/help_io_baseline.json'])); new=json.load(open('tests/fixtures/help_io_baseline.json')); d=help_io.diff_baselines(old,new); T=set('r receive t sel select route routepass expr vexpr if sprintf pipe notein ctlin pack pak unpack trigger combine switch unjoin gate~ bucket buddy b bangbang groove~ tapout~ record~ jit.pack jit.unpack mc.route matrix~ mc.matrix~ play~'.split()); bad=[r for r in d['regressions'] if not (r['field']=='type_mismatches' and r['name'] in T and new['names'][r['source']].get(r['name'],{}).get('count_mismatches',0)==0)]; print(len(d['improvements']),'improvements; regressions:',[(r['source'],r['name'],r['field'],r['baseline'],r['live']) for r in d['regressions']]); a=json.load(open(q+'triage-base.json')); c=json.load(open(q+'triage-after.json')); print('TRIAGE-SAME' if a==c else 'TRIAGE-DIFF'); sys.exit(1 if (bad or not a==c) else 0)" && bash -c 'Q=.planning/quick/261013-cyg-implement-q10-in-planning-reviews-2026-1; BASE=$(cat $Q/base-sha.txt); git diff --quiet "$BASE" HEAD -- patches CLAUDE.md TECHNICAL.md README.md .claude/skills .claude/max-objects/aliases.json .claude/max-objects/max .claude/max-objects/msp .claude/max-objects/mc .claude/max-objects/jitter .claude/max-objects/gen .claude/max-objects/m4l .claude/max-objects/rnbo .claude/max-objects/packages && git diff --quiet -- patches CLAUDE.md TECHNICAL.md README.md .claude/skills || { echo PROTECTED-TREE-CHANGED; exit 1; }; L=$(git log --oneline "$BASE"..HEAD) || { echo GIT-LOG-FAILED; exit 1; }; N=$(printf "%s\n" "$L" | grep -c "(Q10)"); [ "$N" -ge 3 ] || { echo "ONLY $N Q10 COMMITS"; exit 1; }; [ "$(git stash list)" = "$(cat $Q/stash-list-before.txt)" ] || { echo STASH-LIST-CHANGED; exit 1; }; S=$(mktemp); git status --porcelain > "$S"; python3 -m pytest -q -p no:cacheprovider; R=$?; S2=$(mktemp); git status --porcelain > "$S2" || { echo GIT-STATUS-FAILED; exit 1; }; diff -q "$S" "$S2" >/dev/null || { echo TESTS-CHANGED-TREE; exit 1; }; exit $R'</automated>
  </verify>
  <done>
    - Every Task 3 evidence row passes, and the rules use only existing formula names.
    - The overrides guard passes over exactly 22 rule keys.
    - The regenerated baseline's only regressions are allowed unmaskings (expected: bundle/mc.route type only).
    - The triage is identical over all committed patches.
    - The full suite is green: base 2727 passed plus the new tests, 1 xfailed, 1 xpassed. The 3.10 run is green or recorded unavailable.
    - At least 3 `(Q10)` commits; the stash list is unchanged; no protected tree changed; nothing is pushed.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Scratch edit script -> overrides.json | A hand-run script rewrites the expert-curated overrides file |
| DB rules/resolvers -> generated patches | Computed counts become `numinlets`/`numoutlets` of every newly built box |
| Local machine -> committed baseline | Baseline regenerated from this Mac's bundle + packages and committed |
| Baseline -> regression gate | The committed baseline decides what TestLiveOracle treats as a regression |
| Test run -> repo working tree | Tests run next to user-confirmed patches and the DB |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-cyg-01 | Tampering | `.claude/max-objects/overrides.json` rewrite (Tasks 2-3) | high | mitigate | Exact serialization (`indent=2, ensure_ascii=True`, no trailing newline; byte-identical round trip verified at planning). The verify guard asserts that every top-level key other than `variable_io_rules` deep-equals base-sha, that the changed rule keys equal the expected set exactly, and that the format round-trips. |
| T-cyg-02 | Tampering | Committed patches / save path | high | mitigate | No `patches/**` edit (protected-tree `git diff --quiet` vs base-sha in HEAD and working tree). validate_patch + review_patch triage over all committed patches must be identical before and after (Step 0 vs Tasks 1/2/3). Loaded boxes keep their saved counts (from_dict does not recompute). |
| T-cyg-03 | Repudiation | Baseline regeneration absorbing a real regression | medium | mitigate | Each regeneration is gated against the Q9 baseline at base-sha. Task 1 allows zero regressions. Task 3 allows only type mismatches on Q10 targets whose count is now 0. SUMMARY lists every allowed row and every improvement. |
| T-cyg-04 | Tampering | Resolver/rule ambiguity silently changing counts | medium | mitigate | ValueError at DB load when an object has both a resolver and a variable_io_rules entry (tmp_path test). SUPPORTED_IO_FORMULAS is frozen by a test, and every resolver key must be a canonical DB name. |
| T-cyg-05 | Denial of Service | `split_box_text` on malformed text (unbalanced quotes, trailing backslash, huge strings) | low | mitigate | Single linear pass that never raises; tests cover unbalanced quote, trailing backslash, empty and whitespace-only input. |
| T-cyg-06 | Tampering | Derived `variable_io` flag changing modify_box behavior for 16 objects | medium | mitigate | The assumption delta is recorded. The gate~ modify_box test pins the new orphan behavior, and the derived flag lives in memory only (domain JSON untouched). |
| T-cyg-07 | Information Disclosure | Regenerated baseline leaking machine paths | low | mitigate | build_baseline emits only ids, versions and counts. The existing TestCommittedBaseline (no `/Users/`, `/Applications/`, timestamps) runs in every verify. |
| T-cyg-SC | Tampering | Package installs | low | accept | No new dependency: standard library + pytest. The optional 3.10 venv installs the existing requirements-dev.txt (numpy, scipy, pytest), verified in Q8. |
</threat_model>

<verification>
- **Suite.** `python3 -m pytest -q -p no:cacheprovider` is green before (expected 2727 passed, 1 xfailed, 1 xpassed, 29 warnings) and after each task. Passes rise only by new tests; xfailed/xpassed stay 1/1. Record the warning count before and after. `git status --porcelain` is unchanged across each run.
- **Rewritten tests.** The six existing tests that encoded wrong counts are rewritten with MAX citations, and none is deleted:
  - test_db_lookup: combine/cycle/router lifted, trigger no-args, route no-args, routepass resolver, routepass defaults;
  - test_patcher: route two args.
  No other existing test changed.
- **Oracle.** The live help-io oracle shows 0 count mismatches for every Q10 target in the bundle (TestOracleTargets). The regenerated baseline's only regressions against the Q9 baseline are allowed unmaskings.
- **Triage.** Committed-patch triage is identical (57 files at planning).
- **Protected trees and commits.** patches/, docs, skills, aliases and the domain objects.json files are unchanged. overrides.json changes only in `variable_io_rules`, and only in the 22 listed keys. There are at least 3 `(Q10)` commits, the stash list is unchanged, and nothing is pushed.
- **Python 3.10.** The syntax gate passes on every changed .py, and the 3.10 test run is green or recorded unavailable.
</verification>

<success_criteria>
- `compute_io_counts` matches MAX-saved help boxes for every object Q10 names:
  - pack/pak/unpack/trigger/t/combine defaults;
  - route/routepass/select/sel N+1 inlets;
  - expr/vexpr/if $-index and out2;
  - quote-aware tokenizing;
  - gate~/bucket/buddy one port per arg;
  - unjoin +1;
  - groove~, tapout~, record~, notein/ctlin, jit.pack/jit.unpack, mc.route, sprintf, pipe;
  - r/receive 0 inlets, switch 3 inlets, b 2 outlets.
  matrix~/mc.matrix~/play~ stay correct.
- The non-formula rules are per-object resolver callables (S6). The formula vocabulary is unchanged.
- Each fix has a test citing the MAX-saved box, and the committed baseline shrinks (planning prototype: 13,084 -> about 9,601 mismatching boxes; 441 -> about 414 names).
- No committed patch changed or validates differently, and the suite is green.
</success_criteria>

<output>
Create `.planning/quick/261013-cyg-implement-q10-in-planning-reviews-2026-1/261013-cyg-SUMMARY.md` when done. It must include:

**Test and oracle figures**
- Base and final pytest totals, the red counts before each GREEN step, and the warning count before and after.
- Oracle before/after (from Q/help-io-before.json and Q/help-io-after.json):
  - per-source mismatching names and boxes;
  - totals;
  - the (source, name) pairs fully fixed;
  - the `diff_baselines` improvements count;
  - every allowed regression row, with its cause.
  Expected: bundle/mc.route type 0 -> 11, from overrides.json `objects["mc.route"].outlets[*].signal_role = "audio"` on int outlets. **Hand off to Q11 (C9).**

**Behavior changes for the regression-averse user**
- Derived `variable_io` flag: modify_box now recomputes I/O for the 16 newly variable objects, and pan/pan~ flip with no numeric effect.
- Args after `@` no longer count toward I/O.
- `audit_empty_io()["variable_io_ok"]` drops select/route/routepass/expr/vexpr, which are now resolvers.
- The audit parser's degenerate-box check treats the newly variable objects as variable.
- The six rewritten tests and why each value changed.

**Triage result** (expected identical; any finding classified per rule 3).

**Residuals and follow-ups (not fixed, rule 7)**
- The 19 remaining arg-dependent bundle names from the planning prototype (mxj, dict.pack, print, dict.unpack, jit.gl.multiple, mtr, matrix, mc.transpose~, mcs.sig~, array.routepass, jit.cycle, mc.separate~, string.sprintf, grab, jit.catch~, jit.gl.textmult, mpeformat, polyin, string.withpass), refreshed from the real run.
- expr~ still uses `arg_count` (RNBO-only, Q12).
- Inlet/outlet layouts are not modelled for resolver objects or record~ N (S6/Q33): `record~ buf 2` inlet 1 is signal channel 2, but the DB index 1 is the start point; ctlin/notein outlet digests are plain-indexed.
- `Patcher.from_dict` still splits `box.args` on whitespace. This doesn't affect counts, because compute_io_counts re-tokenizes.

**Doc impact (not edited, rule 8)**
- TECHNICAL.md formula table (~lines 127-160: the `arg_count+1` route example now describes outlets only) and the API table: mention resolvers / io_resolvers.py.
- CLAUDE.md "Variable I/O Objects": route/select also gain inlets; quote-aware args.
- The CLAUDE.md "After a Max update" procedure (Q9 note still pending).

**Confirm in MAX (rule 9)**
- Bare `route` / `routepass` = (2,2) and bare `trigger` / `t` = (1,2) are refpage-derived, not MAX-saved; a 30-second check in MAX is recommended.
- notein/ctlin with unusual args (e.g. `notein 0`) follow the refpage reading.
- No patch file changed.

**Worktree base used.** Confirm that it contained 917fd14.
</output>
