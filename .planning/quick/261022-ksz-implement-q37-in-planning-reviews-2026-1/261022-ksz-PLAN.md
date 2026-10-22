---
phase: quick-261022-ksz
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  # Task 1 (4 files)
  - src/maxpat/diagnose.py
  - tests/test_diagnose.py
  - .claude/skills/references/troubleshooting.md
  - tests/test_doc_signatures.py
  # Task 2 (4 files)
  - src/maxpat/testing.py
  - tests/test_testing.py
  - .claude/commands/max-test.md
  - .claude/skills/max-lifecycle/SKILL.md
  # Task 3 (5 files)
  - .claude/commands/max-diagnose.md
  - tests/test_commands.py
  - .claude/skills/max-router/SKILL.md
  - .claude/skills/max-router/references/dispatch-rules.md
  - tests/test_agent_skills.py
autonomous: true
requirements: [Q37]

estimate:
  # estimate-calibration: factor 1 (sample_count 0, confidence low), so tokens == raw_tokens.
  # chars/4 over what the executor touches (revision 1, after the budget trim):
  # shared plan + execute-plan workflow + summary template ~29k;
  # Task 1 ~35k (reads ~9k, writes ~11k, test iterations ~15k);
  # Task 2 ~33k (reads ~12k, writes ~9k, iterations ~12k);
  # Task 3 ~20k (reads ~7k, writes ~5k, gate + iterations ~8k); SUMMARY ~4k.
  # Over the 100k smart zone (advisory). Quick mode keeps one plan, so each task is a
  # commit boundary the executor may hand to a fresh continuation (see <objective>).
  tokens: 121000
  raw_tokens: 121000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "`python3 -m src.maxpat.diagnose --project <name> <file|->` and `diagnose_console(text, project_dir, db=...)` map each pasted MAX console line to ranked troubleshooting.md entries (section, cause, fix, source). The tables are parsed live. A console pattern is a code span in a row's first cell at parenthesis depth 0, with parentheses counted only outside code spans. `<...>` matches one non-space token and `...` matches any text. A quoted identifier also matches any identifier, in a lower tier. In the lowest tier a template's leading `token: ` is optional. Only matches in the best tier are kept. Lines are normalized (double quotes dropped, whitespace collapsed, a doubled `X: X: ` prefix collapsed) and deduplicated with counts."
    - "The report locates offending boxes read-only in every .maxpat, .maxhelp and .gendsp under patches/<project>/. It skips `test-results/` and `__maxbridge_*` copies, and lists malformed files instead of raising. Lines outside the gen~ compile section give object hits (walk.object_name equal to the captured `<objectname>`, else the line's leading token), falling back to newobj argument tokens. Lines in the gen~ compile section give codebox hits (code containing a captured or quoted identifier, with 1-based line numbers), falling back to gen~ containers and codeboxes. Every matched line carries one `/max-iterate <project> ...` proposal naming the file, the subpatcher path, the box id and the entry's fix."
    - "On the committed max-bridge fixtures, read-only: `osc~: osc~: No such object` locates fixtures/fx-nosuchobj.maxpat obj-3, with a fact that osc~ is a Pure Data name (MAX equivalent cycle~). `codebox: can't assign to parameter g` locates the `[gen~]` codebox obj-2 in fixtures/fx-genfail.maxpat. `gen~: failed to compile patcher` matches the genpatcher row. The CLI leaves every byte under patches/max-bridge unchanged."
    - "/max-diagnose never edits anything. diagnose.py has no write, rename, subprocess, hooks or atomic_io use (AST-gated). The command doc requires the paste to go through a file or stdin (never interpolated into Python or shell source), and routes every fix through a user-approved /max-iterate."
    - "`record_confirmation(project_dir, feature, evidence, ...)` writes patches/<project>/test-results/v<version>-<slug>-confirmed.md (or <date>-<slug>-confirmed.md when the project is unversioned). It never overwrites (adds -2, -3), rejects private paths and files outside the project, and commits only that path through hooks._auto_commit_saved_file."
    - "`append_proven_form(section, title, rule, form, why, evidence)` atomically inserts a validated Rule/Form/Why/Evidence entry at the end of the named proven-forms.md section. The evidence needs a known tier, and `[confirmed]` needs a version and a date. It refuses duplicates, unknown sections (unless create_section=True) and private paths, and every other line stays unchanged. /max-test and the max-lifecycle SKILL.md document the flow: record the confirmation, offer the lesson (multiple choice), then commit proven-forms.md by explicit path."
    - "dispatch-rules.md has a `## Domain Overlays` section with Jitter, Max for Live (M4L, experimental) and poly~ subsections. Each subsection gives detect keywords, object references that all resolve in ObjectDatabase with no context restriction, a lead agent, required reading and checks. The router SKILL.md quick reference lists the three overlays."
    - "Regression gate: the full pytest run executed inside Task 3's verify has rc <= the baseline status derived from the Step 0 baseline-junit.xml (0 when it holds no failure or error), and junit_diff.py exits 0. `git status --porcelain patches patterns` and `git stash list` match their Step 0 snapshots. No commit touches patches/ or patterns/, and every commit names explicit paths."
  artifacts:
    - path: "src/maxpat/diagnose.py"
      provides: "TroubleEntry, EntryMatch, BoxHit, Diagnosis, DiagnoseReport, load_troubleshooting, normalize_console_line, match_line, locate_boxes, diagnose_console, main"
      contains: "def diagnose_console("
    - path: "tests/test_diagnose.py"
      provides: "parse oracle, self-match, matcher cases, locator on a synthetic project, max-bridge CLI end-to-end (read-only), AST read-only gate, input caps"
      contains: "def test_cli_max_bridge_read_only"
    - path: ".claude/commands/max-diagnose.md"
      provides: "/max-diagnose command: paste -> temp file -> CLI -> per-root-cause cause/fix/boxes -> /max-iterate proposal"
      contains: "python3 -m src.maxpat.diagnose"
    - path: "src/maxpat/testing.py"
      provides: "record_confirmation, PROVEN_TIERS, PROVEN_FORMS_PATH, ProvenForm, parse_proven_forms, format_proven_form, append_proven_form"
      contains: "def record_confirmation("
    - path: ".claude/skills/max-router/references/dispatch-rules.md"
      provides: "Domain Overlays: Jitter, Max for Live (M4L), poly~"
      contains: "## Domain Overlays"
  key_links:
    - from: "src/maxpat/diagnose.py load_troubleshooting"
      to: ".claude/skills/references/troubleshooting.md"
      via: "TROUBLESHOOTING_PATH default (repo root from Path(__file__).resolve().parents[2]), read at call time, never at import"
      pattern: "TROUBLESHOOTING_PATH"
    - from: "src/maxpat/diagnose.py locate_boxes"
      to: "src/maxpat/walk.py iter_patchers / object_name / box_args / path_prefix / is_gen_container"
      via: "module import of src.maxpat.walk"
      pattern: "walk.iter_patchers("
    - from: ".claude/commands/max-diagnose.md"
      to: "src/maxpat/diagnose.py main"
      via: "CLI run on a temp file holding the paste"
      pattern: "python3 -m src.maxpat.diagnose"
    - from: "src/maxpat/testing.py record_confirmation"
      to: "src/maxpat/hooks.py _auto_commit_saved_file"
      via: "lazy import inside the function; path-scoped commit, warns and never raises"
      pattern: "_auto_commit_saved_file("
    - from: "src/maxpat/testing.py append_proven_form / record_confirmation"
      to: "src/maxpat/atomic_io.py atomic_write_bytes"
      via: "atomic write of the UTF-8 payload"
      pattern: "atomic_write_bytes("
    - from: ".claude/commands/max-test.md"
      to: "src/maxpat/testing.py record_confirmation + append_proven_form"
      via: "documented confirmation steps"
      pattern: "record_confirmation("
    - from: ".claude/skills/max-router/SKILL.md"
      to: ".claude/skills/max-router/references/dispatch-rules.md Domain Overlays"
      via: "quick-reference overlay table pointing to the section"
      pattern: "Domain Overlays"
---

<objective>
Implement Q37 from .planning/reviews/2026-10-11-fix-plan.md (review §5.7 / §5 item 8, §3.11, §3.12, §5 item 13):
- **`/max-diagnose`**: the user pastes MAX console output. Each line maps to a cause and fix through `.claude/skills/references/troubleshooting.md`, the offending box is found in the active project's patches, and a `/max-iterate` fix is proposed.
- **Confirmation lifecycle** (max-lifecycle skill and the `/max-test` results flow): when the user confirms a feature works in MAX, the confirmation is written to `patches/<project>/test-results/`, and the user is offered a general lesson for `.claude/skills/references/proven-forms.md` with an evidence tier.
- **Router**: Jitter, M4L and poly~ domains in the dispatch rules.

Prerequisite check: Q17 (quick 261014-gf2, 3e3742e6) landed. troubleshooting.md (4 tables, 32 rows) and proven-forms.md (15 entries) exist at HEAD 3a60d201.

There is no CONTEXT.md, so there are no locked D-XX decisions. These are Claude's-discretion choices; record them in the module docstrings and SUMMARY:
- `/max-diagnose` is read-only. A Python module `src/maxpat/diagnose.py` with a CLI (`python3 -m src.maxpat.diagnose`) does the deterministic part: parse, match, locate, propose. The command doc does the judgment: pick among same-wording causes, group cascades, phrase the fix. Fixes always go through `/max-iterate`.
- The troubleshooting.md tables are the single source. No second copy of the wordings exists in code. The parse contract, one sentence, goes into the troubleshooting.md header.
- Confirmation files are per confirmation and never overwritten. They are committed through the same path-scoped policy as patch saves (Rule #7). The proven-forms append is a separate, user-consented step committed by explicit path.
- Router domains become **overlays** on the existing agents, not new agents. An overlay fixes the lead, adds secondaries, required reading and checks. No Jitter, M4L or poly~ specialist agent is created.
- README.md, TECHNICAL.md, CLAUDE.md, shared-capabilities.md and max-verify.md are NOT edited (fix-plan rule 8). Their doc impact is listed in SUMMARY.
- The max-lifecycle reference docs test-protocol.md and project-structure.md are NOT edited either (trimmed for the per-plan budget). Q37's lifecycle item is carried by the max-lifecycle SKILL.md and the /max-test flow; the two reference docs' stale result-file claims go to SUMMARY as doc impact.

Task boundaries (budget control; quick mode keeps one plan):
- Each task ends in its own explicit-path commit(s). No task relies on in-context state from an earlier task: its inputs are committed files and the Step 0 snapshots in QDIR (= .planning/quick/261022-ksz-implement-q37-in-planning-reviews-2026-1), and its read_first names everything it needs.
- If the executor's context is heavy at a task boundary (after a task's commit), it returns the standard checkpoint state (completed tasks with commit hashes, next task) so a fresh continuation starts at the next task. It never stops mid-task.
- No doc written before Task 3 names `/max-diagnose`: the command file only exists from Task 3, and tests/test_doc_signatures.py `test_no_references_to_missing_commands` fails on a `/max-*` name without a command file.

Fix-plan rules copied verbatim (rules for every task):
1. Read the referenced finding IDs in the review report first; they contain the evidence and the expected fix.
2. Write each regression test **first**. It should reproduce the finding (red) before you fix it (green).
3. **Never edit committed patch files** (`patches/**/*.maxpat|.gendsp|.maxhelp|.js`). They are user-confirmed baselines, and the integration tests depend on them. If one produces a new finding: false positive → fix the checker; true positive in a committed patch → allowlist it with a written reason and list it in SUMMARY.md.
4. Run `python3 -m pytest -q` before and after. From Q3 onward the suite must be fully green.
5. Never `git stash`. Never `git add -A` or `git add .`. Stage explicit paths only.
6. Code must work on Python 3.10.
7. Don't widen scope. If the fix needs a decision the report doesn't make, stop and ask with multiple-choice options.
8. Edit CLAUDE.md, skills or TECHNICAL.md only where the task says to. List any other doc impact in SUMMARY.md.
9. In SUMMARY.md, flag anything that needs the user to confirm in MAX or Live.

Purpose: close the loop between "it broke in MAX" and the fix (diagnose), and between "it works in MAX" and shipped knowledge (confirmations, then proven-forms). Send Jitter, M4L and poly~ work to the right agents with the right reading.
Output: two Python modules (one new, one extended) with tests, one new command, two lifecycle docs and two router docs updated, and test registrations.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
Context loading is trimmed for the per-plan budget:
- CLAUDE.md is loaded by the harness; do not re-read it.
- The Q37 entry and the fix-plan rules are copied into `<objective>`. Open .planning/reviews/2026-10-11-fix-plan.md only at lines 645-655 (the Q37 entry) if needed, never whole.
- troubleshooting.md is read in Task 1 and proven-forms.md in Task 2 (their read_first), not up front.

Interfaces (verified at planning time, HEAD 3a60d201):
- src/maxpat/walk.py (pure, never raises):
  - `box_maxclass` (60), `box_text` (68), `box_tokens` (76), `box_name` (81);
  - `box_args(box)` (91) returns raw tokens after the name for a newobj, else [];
  - `object_name(box)` (99) returns None for inlet/outlet/patcher/bpatcher, a newobj's first token, otherwise the maxclass (so a comment is `comment`);
  - `inner_patcher` (120); `is_gen_container(box)` (136) covers gen~, mc.gen~, jit.gen, ...;
  - `box_label` (171); `path_prefix(path)` (201) gives `[p synth > gen~] ` or `""`;
  - `iter_patchers(patch)` (225) yields `(path, patcher_dict, context)`, where context is one of max, gen, rnbo, poly, bpatcher. A .gendsp top level yields context `gen`. External files are never loaded.
- src/maxpat/project.py:
  - `get_active_project(base_dir) -> dict | None` (113) validates the name as a single path component and the directory as existing;
  - `list_projects(base_dir)` (477);
  - `get_version(project_dir) -> str | None` (255) returns the last versions.json entry, or None without the file.
- src/maxpat/hooks.py `_auto_commit_saved_file(path) -> str | None` (64): never raises; commits exactly that path when it is under `patches/<project>/` of its repo; otherwise emits one UserWarning (not a repo / outside patches / git failure / no change).
- src/maxpat/atomic_io.py `atomic_write_bytes(path, payload: bytes)` (73), stdlib only.
- src/maxpat/testing.py today:
  - `generate_test_checklist`;
  - `save_test_results(project_dir, test_name, results_md) -> Path` writes `test-results/{test_name}.md` and OVERWRITES a same-named file. test-protocol.md wrongly claims incrementing `test-NNN.md`.
  - Imports only `src.maxpat.walk`.
- ObjectDatabase:
  - `lookup(name)` (725), `is_pd_object` (961), `get_pd_equivalent` (972);
  - `get_effective_restrictions(name)` (1172) returns [] for UNKNOWN names too, so check lookup first;
  - `ObjectDatabase()` loads in about 0.02 s.
- tools/max_bridge.py `_error_key` (1028) is the doubled-prefix collapse rule. Mirror it in src and do not import tools/ from src.
- Grounded MAX 9.2 console wordings (max-bridge v0.3.0, 2026-10-21; tests/test_max_bridge.py 958-1025; patches/max-bridge/open-questions.md):
  - `osc~: osc~: No such object`
  - `send: bad arguments creating object`
  - `codebox: can't assign to parameter g`
  - `gen_domain: dsp.gen: [string "-- main2.lua..."]:727: failed to compile genpatcher`
  - `gen~: failed to compile patcher`
  - Whether a copy from the Max Console window includes the object column is NOT recorded. It is a SUMMARY item for the user.
- Committed fixtures (read only):
  - patches/max-bridge/fixtures/fx-nosuchobj.maxpat: obj-3 newobj `osc~ 440`;
  - patches/max-bridge/fixtures/fx-badargs.maxpat: obj-3 `send 15`;
  - patches/max-bridge/fixtures/fx-genfail.maxpat: obj-4 `gen~`, whose inner `[gen~]` obj-2 is a codebox with code `Param g(0.5);\ng = in1;\nout1 = g;`;
  - comment boxes in these fixtures mention `osc~` and the console text, and must never be hits.
- troubleshooting.md tables:
  - Object creation 11 rows, Messages 7, gen~ compile 8, FluCoMa and files 6, so 32 rows; plus a non-table "Silent failures" list.
  - The depth-0 rule (prototyped at planning time) gives:
    - six rows `<objectname>: No such object`;
    - the already-in-use row → only `<objectname>: <name>: already in use`;
    - the 'sr' row → only `use of undeclared identifier 'sr'`;
    - the maxb row → only `use of undeclared identifier 'maxb_NN'`;
    - `Wrong Point Size` alone;
    - `Please provide a valid dictionary...` + `labelDict is null`;
    - `Could not open file for writing` + `... not found`;
    - the delay() row keeps `delay()` intact;
    - two gen~ compile rows with no pattern ("wording not recorded" and "No message").
- proven-forms.md:
  - 15 `###` entries in 7 sections: Control and data, MC, FluCoMa, poly~ voices, UI, Subpatchers and layout, Framework workflow;
  - the `## Evidence tiers` preamble has no `###`;
  - every entry has `- **Rule:**`, `- **Form:**` (nested list in "voice forms"), `- **Why:**` and `- Evidence:`, with tiers from {confirmed, bundle, code, observed};
  - neither reference doc contains /Users/, /home/, .planning/, ~/.claude or a memory-note filename (checked at planning time).
- Object names DB-checked for the overlays (all `lookup` non-None, restrictions []):
  - Jitter: jit.world, jit.gl.render, jit.gl.mesh, jit.gl.gridshape, jit.gl.videoplane, jit.gl.texture, jit.gl.pix, jit.gl.slab, jit.matrix, jit.pwindow, jit.window, jit.movie, jit.grab, jit.noise, jit.bfg, jit.op, jit.expr, jit.gen, jit.pix, jit.catch~, jit.release~, jit.buffer~, jit.poke~, jit.peek~, jit.xfade, jit.pack, jit.unpack, jit.matrixinfo, qmetro;
  - M4L: plugin~, plugout~, live.thisdevice, live.dial, live.slider, live.numbox, live.menu, live.text, live.toggle, live.tab, live.meter~, live.object, live.path, live.observer, live.remote~, midiin, midiout;
  - poly~: poly~, mc.poly~, thispoly~, in, in~, out, out~, adsr~.
  - `db.selectors("poly~")` includes midinote, note, target, steal, voices, mute, up, down.
  - `midinote` is a message, not an object.
- M4L critic: `review_patch` runs `review_m4l` only when `detect_m4l_device_type` (src/maxpat/critics/m4l_critic.py 87) finds plugin~, plugout~ or live.thisdevice in a non-gen scope: plugin~ gives audio_effect, else plugout~ gives instrument, else midi_effect. No .amxd writer exists in src/maxpat.
- Doc tests:
  - tests/test_commands.py: `ALL_COMMANDS` (18-29) and cross-reference tests.
  - tests/test_doc_signatures.py: `_INDEX_MODULES` (59-68). Every skills and commands .md is in DOC_FILES automatically, so a new doc adds a parametrized id. `test_no_references_to_missing_commands` (597) requires every `/max-*` a doc names to exist.
  - tests/test_agent_skills.py: router tests (198-230), `test_dispatch_rules_no_stub_labels` (474).
- tests/test_dead_code_removed.py bans the removed memory-module names and phrases in src/, tests/ and .claude/. Do not use any phrase from its regex list in new text.
- tests/test_release.py imports every src module from the release archive, which excludes patches/ and tests/. diagnose.py must therefore do no I/O at import and use the stdlib plus src only.
- Git helpers to copy, not import, from tests/test_save_gate.py: the skipif `pytestmark` (28), the `_isolate_git_env` autouse fixture (40-44), `_git` (47), `_repo` (59), `_staged` (73), `_head_files` (77), `_head` (81). `_repo` has no initial commit, so seed one before staging an unrelated file.
- Baseline: the last full run (Q36 final) had rc 0, with 5881 passed, 5 xfailed and 1 xpassed.
</context>

<tasks>

<task type="tracer" tdd="true">
  <name>Task 1 (tracer): paste a console line into the CLI, get a ranked troubleshooting entry, the offending box and a /max-iterate proposal (`python3 -m src.maxpat.diagnose`)</name>
  <files>src/maxpat/diagnose.py, tests/test_diagnose.py, .claude/skills/references/troubleshooting.md, tests/test_doc_signatures.py</files>
  <read_first>
    - .claude/skills/references/troubleshooting.md (whole file: the four tables are the parse input)
    - src/maxpat/walk.py: 1-60 (contract), 60-260 (helpers, iter_patchers)
    - src/maxpat/project.py: 95-160 (get_active_project), 477-500 (list_projects)
    - tools/max_bridge.py: 1028-1056 (_error_key)
    - tests/test_max_bridge.py: 950-1040 (grounded console wordings)
    - tests/test_doc_signatures.py: 55-70 (`_INDEX_MODULES`)
    - The max-bridge fixture boxes are summarized in context. Open a fixture (read only) only if a CLI assertion fails.
  </read_first>
  <behavior>
    - Parse: `load_troubleshooting()` returns 32 or more TroubleEntry rows in the four sections, in file order (Object creation, Messages, gen~ compile, FluCoMa and files).
      - Six rows have patterns `("<objectname>: No such object",)`.
      - The depth-0 oracle rows parse exactly as listed in context (already-in-use, 'sr', maxb, Wrong Point Size, FluCoMa dictionary and file rows, delay() intact).
      - After this task's edit the genpatcher row has `("dsp.gen: ... failed to compile genpatcher", "gen~: failed to compile patcher")`.
      - Exactly two gen~ compile rows have no pattern.
      - A tmp file with a 3-cell row skips that row. A missing path raises FileNotFoundError.
    - Self-match: every pattern of every row, with placeholders replaced by w1, w2, … and `...` by `zz`, is matched by `match_line` with that row among the kept matches.
    - Normalize: `osc~: osc~: No such object` becomes `osc~: No such object`. Tabs and runs of spaces collapse to one space, and double quotes are dropped.
    - Match (kept best-tier matches, best first):
      - `osc~: osc~: No such object` and `newobj: osc~: No such object` give the six No-such-object rows, capturing objectname osc~.
      - Bare `No such object` gives the same six rows, without a capture.
      - `send: bad arguments creating object` gives the bad-arguments row.
      - `codebox: can't assign to parameter g` and bare `can't assign to parameter g` give the can't-assign row, capturing name g.
      - The gen_domain genpatcher line and `gen~: failed to compile patcher` give the genpatcher row.
      - `use of undeclared identifier 'sr'` gives only the 'sr' row.
      - `use of undeclared identifier 'k_drive'` gives the 'sr' and maxb rows, with identifier k_drive.
      - `function clip not found` gives the clip row first.
      - `umenu: doesn't understand a` gives the umenu row first, and no fluid.dataset~ row.
      - `print: hello` gives no match.
    - Locate (synthetic tmp project `demo`):
      - The osc~ line hits generated/demo.maxpat obj-1 at top level and obj-1 under `[p synth] `. It never hits the comment that mentions osc~, test-results/, a `__maxbridge_*` copy, or the malformed file, which appears in report.skipped.
      - `base: bad number` hits the `uzi 2 base 0` box with reason argument.
      - The can't-assign line hits the `[gen~] ` codebox with code_lines (1, 2, 3).
      - An undeclared-identifier line hits a .gendsp codebox.
      - A genpatcher line with no identifier falls back to gen containers and codeboxes.
    - Facts (with db): osc~ gives a Pure Data / cycle~ fact; expr~ gives a restriction fact; `frobnicate~` gives a not-in-database fact. With db=None there are no facts.
    - Proposal: `/max-iterate demo fix "…" at generated/demo.maxpat obj-1 [osc~ 440]: <first sentence of the fix>`.
    - CLI end to end on committed max-bridge with the five grounded lines:
      - rc 0;
      - the output names fixtures/fx-nosuchobj.maxpat obj-3, fixtures/fx-genfail.maxpat, cycle~ and `/max-iterate max-bridge`;
      - every file under patches/max-bridge has the same sha256 before and after;
      - stdin `-` works;
      - `--project ../x` and `--project nope` give rc 2.
    - Read-only AST gate:
      - diagnose.py imports none of src.maxpat.hooks, src.maxpat.atomic_io, subprocess or shutil;
      - it calls none of write_text, write_bytes, unlink, rename, replace, mkdir, rmdir, touch;
      - it has no `open()` with a mode containing w, a, x or +.
    - Caps: 2500 input lines give `report.truncated` True, with at most 2000 lines processed. A 5000-character line completes without error.
  </behavior>
  <action>
QDIR below means .planning/quick/261022-ksz-implement-q37-in-planning-reviews-2026-1.

**Step 0. Baseline, before any edit.**
- Write `git rev-parse HEAD` to QDIR/base-sha.txt, `git stash list` to QDIR/stash-list-before.txt, and `git status --porcelain patches patterns` to QDIR/patches-status-before.txt.
- Copy .planning/quick/261022-i07-implement-q36-in-planning-reviews-2026-1/junit_diff.py to QDIR/junit_diff.py. Change only the copy:
  - `ALLOWED_REMOVED` stays an empty set;
  - the `ours` predicate accepts new keys starting with `tests.test_diagnose`, `tests.test_testing`, `tests.test_commands`, `tests.test_agent_skills` or `tests.test_doc_signatures`. The last three only gain new parametrized ids and new tests;
  - the docstring says it is the Q37 gate (quick 261022-ksz).
- Run `python3 -m pytest -q -p no:cacheprovider --junitxml=QDIR/baseline-junit.xml > QDIR/baseline-pytest.txt 2>&1` and write its exit code to QDIR/baseline-rc.txt (SUMMARY reports it; no verify trusts it, the verifies derive the baseline status from baseline-junit.xml).
  - Exit 2 or more means a broken baseline: stop and report it before any edit.
  - Exit 1: list the failing ids in SUMMARY as pre-existing.
- These QDIR files stay uncommitted. This task's verify rejects a baseline taken after Part A (it would hold tests.test_diagnose cases).

The `/max-diagnose` command doc that wraps this CLI, and its ALL_COMMANDS registration, are Task 3 (budget split). The CLI on the committed max-bridge fixtures is the end-to-end path this tracer proves: console text → troubleshooting.md parse → match → patch walk → box + proposal.

**Part A. Tests first: tests/test_diagnose.py.**
- Write every `<behavior>` case. They stay red until Part C exists.
- Use a module-scoped `ObjectDatabase()` fixture.
- Build the synthetic project under tmp_path/patches/demo with plain JSON dicts, `{"patcher": {"boxes": [{"box": {...}}], "lines": []}}`. Embed the `p synth` and `gen~` inner patchers under `box["patcher"]`. The .gendsp top level has `"classnamespace": "dsp.gen"`.
- The CLI test copies nothing. It runs `[sys.executable, "-m", "src.maxpat.diagnose", "--project", "max-bridge", "--base-dir", str(REPO_ROOT), str(tmp_file)]` with cwd=REPO_ROOT, and hashes every file under patches/max-bridge with hashlib before and after.
- The AST gate parses src/maxpat/diagnose.py with `ast`.
- Name the tests so the artifact check finds `def test_cli_max_bridge_read_only`.

**Part B. troubleshooting.md: two edits only.** Rule 8 is satisfied because this file is the task's named source.
- (1) Append one sentence to the "How to read this table" paragraph. It says that `src/maxpat/diagnose.py` reads these four-column tables (do not name the slash command here: it does not exist until Task 3): every code span in the first cell outside parentheses is a console pattern, `<...>` matches one word and `...` any text. Keep four columns, and put example or companion wordings that are not patterns inside parentheses.
- (2) In the `dsp.gen: ... failed to compile genpatcher` row:
  - add `/ \`gen~: failed to compile patcher\`` right after the first code span, at depth 0;
  - append `; max-bridge v0.3.0 (2026-10-21) for \`gen~: failed to compile patcher\`` to its Source cell.
  - This wording is recorded verbatim in tests/test_max_bridge.py and in the max-bridge v0.3.0 checklist. Add no other rows and invent no wording.

**Part C. src/maxpat/diagnose.py**, stdlib + src.maxpat only, `from __future__ import annotations`, Python 3.10.

Module docstring:
- the Q37 purpose;
- the read-only guarantee;
- the parse contract;
- the match tiers;
- the locate rules;
- that it does no I/O at import;
- that tools/max_bridge._error_key is the origin of the doubled-prefix rule.

Constants:
- `TROUBLESHOOTING_PATH = Path(__file__).resolve().parents[2] / ".claude" / "skills" / "references" / "troubleshooting.md"`;
- `GEN_SECTION = "gen~ compile"`;
- `MAX_LINES = 2000`, `MAX_LINE_CHARS = 2000`, `MAX_HITS = 10`;
- `PATCH_SUFFIXES = (".maxpat", ".maxhelp", ".gendsp")`;
- `SKIP_DIRS = {"test-results", ".git", "node_modules", "__pycache__"}`.

Dataclasses:
- frozen `TroubleEntry(section, message, patterns: tuple[str, ...], cause, fix, source, row: int)`;
- frozen `EntryMatch(entry, pattern, tier, score: int, captures: tuple[tuple[str, str], ...])`;
- frozen `BoxHit(file, where, box_id, label, reason, code_lines: tuple[int, ...] = ())`. Here `file` is the posix path relative to project_dir, and `reason` is one of object, argument, code, gen container;
- `Diagnosis(line, count, matches, objects, identifiers, hits, hits_omitted, facts, proposal)`;
- `DiagnoseReport(project, files, skipped, diagnoses, truncated)` with `render() -> str`.

`load_troubleshooting(path=None) -> list[TroubleEntry]`:
- Read the file (FileNotFoundError propagates).
- Track the current `## ` heading.
- Take table rows that start with `|`, skipping the header row (first cell `Console message`) and the `|---` separator.
- Split on ` | ` after stripping the outer pipes. Skip a row that does not have exactly four cells.
- Patterns are code spans of cell 0 at parenthesis depth 0. Scan character by character: a backtick starts a code span that runs to the next backtick, and parentheses count only outside code spans.

`normalize_console_line(line) -> str`:
- drop `"`;
- collapse whitespace (tabs included) and strip;
- collapse a leading `X: X: ` to `X: `, repeatedly.

`match_line(line, entries) -> list[EntryMatch]`:
- Normalize first.
- For each entry and pattern, try three variants:
  - **exact**, bonus 3000: `<...>` becomes `(\S+)` (capture named by the placeholder text), `...` becomes `.*?`, and everything else is literal, `re.escape`d;
  - **any-identifier**, bonus 2000: as exact, but each quoted literal becomes `'([^']+)'` captured as `identifier`. A quoted literal is a single quote not preceded by a word character, then non-space non-quote characters, then a quote not followed by a word character. This keeps the apostrophe in doesn't / can't literal. Only built when the template has a quoted literal;
  - **no-prefix**, bonus 1000: the exact template with a leading `<placeholder>: ` or `word: ` removed (word = no spaces, colons or angle brackets). Only built when such a prefix exists.
- Use `re.search` with IGNORECASE.
- Score = bonus + count of literal characters in the variant. An entry keeps its best-scoring pattern and variant.
- Return only the matches in the best tier (bonus class), sorted by score descending, then by row.

`locate_boxes(project_dir, *, objects=(), identifiers=(), gen_fallback=False, cache=None) -> tuple[list[BoxHit], list[str]]`:
- Walk project_dir with `os.walk(followlinks=False)`, sorted. Skip SKIP_DIRS and file names starting with `__maxbridge_`, and keep PATCH_SUFFIXES.
- Each file whose resolved path is not inside project_dir is skipped. A JSON or decode error appends `"<rel> (<reason>)"` to the skipped list. `cache` is a dict reused across lines, so each file is read once per report.
- Walk each file with `walk.iter_patchers`. `where` = `walk.path_prefix(path)`, and the label is the newobj text (else `walk.box_label`), truncated to 40 characters with `...`.
- Order:
  1. object hits: `walk.object_name(box)` is in `objects`;
  2. if there are none, argument hits: a newobj whose `walk.box_args` contains a token from `objects`;
  3. code hits: a box with a str `code` in gen context whose code matches `\b<identifier>\b`, with the 1-based matching line numbers;
  4. if `gen_fallback` and there are no code hits: gen container boxes (`walk.is_gen_container`) and boxes with a str `code`.
- Never raise on malformed boxes.

`diagnose_console(text, project_dir=None, *, db=None, entries=None) -> DiagnoseReport`:
- Split lines, cap at MAX_LINES (setting truncated), and truncate each to MAX_LINE_CHARS. Normalize, drop empties, and dedupe with counts in first-seen order.
- Mode:
  - If the top match's section is GEN_SECTION, use gen mode. identifiers = name/identifier captures ∪ quoted tokens in the line; `gen_fallback=True`.
  - Otherwise use object mode. objects = all objectname captures, else the line's leading `token:` (also for unmatched lines).
- Facts are added only when db is given and in object mode, each call wrapped in try/except:
  - lookup None and is_pd_object → `"<n>: Pure Data name, not MAX; MAX equivalent <eq>"`;
  - lookup None otherwise → `"<n>: not in the object database"`;
  - non-empty `get_effective_restrictions` → `"<n>: only valid inside <list> (domain <domain>)"`.
- Proposal (only when there are matches):
  - `/max-iterate <project> fix "<line>" at <file> <where><box_id> [<label>]: <first sentence of the top entry's fix>`;
  - with no hits, drop the `at …` part; with no project, drop `<project> `.
- `project` is `project_dir.name` or None.

`render()` format (tests assert on these fragments):
- Header lines:
  - `Console diagnosis: N distinct line(s), M matched, K unmatched`;
  - `Project: <name> (F patch file(s) scanned)` or `Project: none -- boxes not located (pass --project NAME)`;
  - one `Skipped: …` line per skipped file;
  - `Input truncated to 2000 lines.` when truncated.
- Then per diagnosis:
  - `[i] <line>` plus `  (xN)` when the count is above 1;
  - per match: `  entry: <section> -- \`<pattern>\` [<tier>]`, then `    cause: `, `    fix: ` and `    source: ` lines;
  - when there is no match: `  no troubleshooting entry: diagnose from the CLAUDE.md rules and the object database; never invent console wording`;
  - `  fact: …` lines;
  - `  box: <file> <where><box_id> [<label>] (<reason>[; lines a, b])` lines, then `  ... and N more box(es)`;
  - `  propose: <proposal>`.
- An empty input renders `no console lines`.

`main(argv=None) -> int` with argparse:
- arguments: `file` (optional, default `-` = stdin), `--project NAME`, `--base-dir DIR` (default cwd), `--no-db`;
- validate `--project` like get_active_project: non-empty, not `.`/`..`, no `/`, `\` or NUL, and `<base>/patches/<name>` is a directory. Otherwise print to stderr and return 2;
- without `--project`, use `get_active_project(base_dir)`. None means no locating;
- an unreadable file prints to stderr and returns 2;
- print `report.render()` and return 0;
- add `if __name__ == "__main__": raise SystemExit(main())`.

**Part D. Signature index registration.** In tests/test_doc_signatures.py, append `"src.maxpat.diagnose"` at the end of `_INDEX_MODULES`. This proves the module imports cleanly into the doc-signature index now, and binds the Task 3 command doc's call forms against the real signatures.
  </action>
  <verify>
    <automated>python3 -m pytest -q -p no:cacheprovider tests/test_diagnose.py tests/test_doc_signatures.py tests/test_dead_code_removed.py tests/test_release.py && printf 'osc~: osc~: No such object\n' | python3 -m src.maxpat.diagnose --project max-bridge - | grep -q 'fixtures/fx-nosuchobj.maxpat obj-3' && test -s .planning/quick/261022-ksz-implement-q37-in-planning-reviews-2026-1/base-sha.txt && git merge-base --is-ancestor "$(cat .planning/quick/261022-ksz-implement-q37-in-planning-reviews-2026-1/base-sha.txt)" HEAD && ! git cat-file -e "$(cat .planning/quick/261022-ksz-implement-q37-in-planning-reviews-2026-1/base-sha.txt):src/maxpat/diagnose.py" 2>/dev/null && python3 -c "import sys, xml.etree.ElementTree as E; t = list(E.parse(sys.argv[1]).getroot().iter('testcase')); assert len(t) >= 5000, len(t); assert not [c for c in t if c.get('classname', '').startswith('tests.test_diagnose')], 'baseline taken after Part A'" .planning/quick/261022-ksz-implement-q37-in-planning-reviews-2026-1/baseline-junit.xml && grep -q 'tests.test_diagnose' .planning/quick/261022-ksz-implement-q37-in-planning-reviews-2026-1/junit_diff.py && python3 .planning/quick/261022-ksz-implement-q37-in-planning-reviews-2026-1/junit_diff.py .planning/quick/261022-ksz-implement-q37-in-planning-reviews-2026-1/baseline-junit.xml .planning/quick/261022-ksz-implement-q37-in-planning-reviews-2026-1/baseline-junit.xml</automated>
    <fails_when>non-zero exit from any step: a failed or errored test in the four pytest files (summary line shows "failed" or "error"); grep finding no `fixtures/fx-nosuchobj.maxpat obj-3` box line in the live CLI output; base-sha.txt empty or not an ancestor of HEAD; src/maxpat/diagnose.py already present at base-sha (git cat-file succeeds); baseline-junit.xml missing, unparsable, under 5000 testcases, or holding tests.test_diagnose cases (AssertionError "baseline taken after Part A"); junit_diff.py lacking the tests.test_diagnose prefix, or its self-diff printing an offender line</fails_when>
  </verify>
  <done>
- The Step 0 snapshots exist, and baseline-junit.xml is a pre-edit full run (5000+ testcases, no tests.test_diagnose cases).
- All tests/test_diagnose.py cases pass, and src.maxpat.diagnose is in the doc-signature index.
- The CLI on the committed max-bridge fixtures locates fx-nosuchobj obj-3 and the fx-genfail codebox, and changes no byte under patches/max-bridge.
- troubleshooting.md carries the parse-contract sentence and the grounded `gen~: failed to compile patcher` companion, and nothing else changed in it.
- Commit with explicit paths only: `git add` the four task files by name, then `git commit -m "feat(maxpat): console diagnosis module + CLI (quick 261022-ksz, Q37)" -- <the same four paths>`. This commit is the first task boundary.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: confirmation lifecycle: a confirmed feature lands in test-results/ and, with consent, as a tiered proven-forms.md lesson</name>
  <files>src/maxpat/testing.py, tests/test_testing.py, .claude/commands/max-test.md, .claude/skills/max-lifecycle/SKILL.md</files>
  <read_first>
    - src/maxpat/testing.py (whole), tests/test_testing.py (whole)
    - src/maxpat/hooks.py: 60-135 (_auto_commit_saved_file)
    - src/maxpat/atomic_io.py: 1-90
    - src/maxpat/project.py: 225-272 (init_versions, get_version)
    - .claude/skills/references/proven-forms.md (whole: the entry format to reproduce)
    - tests/test_save_gate.py: 20-85 (git isolation helpers to copy)
    - tests/test_claude_md.py: 250-280 (the private-path rule to mirror)
    - .claude/commands/max-test.md, .claude/skills/max-lifecycle/SKILL.md (whole)
  </read_first>
  <behavior>
    - **record_confirmation, file content.** On a tmp project with versions.json at 0.2.1, it writes test-results/v0.2.1-lfo-sync-confirmed.md. The file contains:
      - `# Confirmed in MAX: LFO sync`;
      - `- Project: demo`, `- Version: v0.2.1`, `- Date: 2026-10-22` (when passed), `- MAX: 9.2.0` (else `not recorded`);
      - a `- Files:` line with backticked relative paths (else `none listed`);
      - `- Proven-forms lesson:` with the lesson or `none proposed`;
      - a `## Evidence` section holding the evidence text.
    - **Names and validation.**
      - No versions.json gives `2026-10-22-<slug>-confirmed.md` and `- Version: unversioned`.
      - A second identical call writes `...-confirmed-2.md` and leaves the first file's bytes unchanged.
      - The feature `../../etc passwd` gives a slug-only name inside test-results/.
      - A `files` entry outside the project or missing → ValueError, and nothing is written.
      - `/Users/` or a memory-note filename in the evidence → ValueError, and nothing is written.
      - A bad version or date format → ValueError.
      - An empty feature or evidence, or a newline in the feature → ValueError.
    - **Commit.**
      - `commit=False` writes and emits no warning.
      - `commit=True` outside a repo emits a UserWarning matching "not auto-committed".
      - In a throwaway repo (initial commit seeded, then an unrelated `patches/demo/notes.txt` staged), HEAD names only the confirmation file and notes.txt stays staged.
    - **parse_proven_forms on the committed file.**
      - 15 or more entries, none in "Evidence tiers".
      - Every entry has non-empty rule, form, why and evidence, and tiers that form a non-empty subset of PROVEN_TIERS.
      - The "voice forms" form keeps its nested items.
    - **Private paths.** The committed proven-forms.md and troubleshooting.md have no private-path findings.
    - **format_proven_form round trip.** Formatting, then parsing, gives back the same fields. A list form renders nested `  - ` items.
    - **append_proven_form, success.** Appending to a tmp copy under section "UI" gives:
      - the new entry is the last `###` before `## Subpatchers and layout`;
      - every original line is kept, in order: difflib shows only insertions;
      - the file still parses with all fields.
    - **append_proven_form, refusals.**
      - A duplicate title (case-insensitive, any section) → ValueError, bytes unchanged.
      - An unknown section → ValueError naming the existing sections.
      - With create_section=True, a new `## Jitter` section is appended at EOF with the entry.
      - The section "Evidence tiers" is refused.
      - Evidence without a tier, or with an unknown `[tag]` → ValueError.
      - `[confirmed]` without a vN.N version and a YYYY-MM-DD date in its clause → ValueError.
      - A newline, a leading `#` or `<!--` in title, rule, why or evidence → ValueError.
      - A private path in any field → ValueError.
    - **Docs.**
      - max-test.md contains `record_confirmation(` and `proven-forms.md`.
      - max-lifecycle SKILL.md contains `Confirmation Lifecycle`, `record_confirmation` and `append_proven_form`.
      - Both docs contain `-confirmed.md`. (Ordering, not a test: they must not name a command that does not exist yet; tests/test_doc_signatures.py `test_no_references_to_missing_commands` in this task's verify enforces it.)
  </behavior>
  <action>
**Part A. Tests first: tests/test_testing.py.**
- Add the classes `TestRecordConfirmation`, `TestProvenForms` and `TestLifecycleDocs` covering every `<behavior>` case.
- Copy (do not import) the git helpers and the `_isolate_git_env` fixture from tests/test_save_gate.py. Scope the skip-if-no-git to the repo test only.
- Pass `date="2026-10-22"` explicitly wherever a name or content is asserted.
- Use `pytest.warns(UserWarning, match="not auto-committed")` for the non-repo commit case.
- Use `warnings.catch_warnings(record=True)` + `simplefilter("always")` for the commit=False no-warning case.

**Part B. src/maxpat/testing.py.**
- Extend the module docstring: the test-results flow, confirmations (Q37), proven-forms entries and evidence tiers.
- Keep `generate_test_checklist` and `save_test_results` byte-for-byte in behavior.
- Imports stay stdlib + `src.maxpat.walk` + `src.maxpat.atomic_io`. Import `project.get_version` and `hooks._auto_commit_saved_file` lazily inside the function: no import cycle and no import-time I/O.

New names:
- `PROVEN_TIERS = ("confirmed", "bundle", "code", "observed")`.
- `PROVEN_FORMS_PATH = Path(__file__).resolve().parents[2] / ".claude" / "skills" / "references" / "proven-forms.md"`.
- `_private_path_findings(text) -> list[str]` flags `/Users/`, `/home/`, `.planning/`, `~/.claude` and memory-note filenames, `\b(feedback|project|reference)_[a-z0-9_]+\.md\b`. This is the tests/test_claude_md.py rule plus `/home/` and `~/.claude`.
- `_slug(text)`: lowercase; runs of characters outside [a-z0-9] become `-`; strip `-`; at most 48 characters; `feature` when empty.

`record_confirmation(project_dir, feature, evidence, *, version=None, max_version=None, files=None, lesson=None, date=None, commit=True) -> Path`:
- **Validate before any write:**
  - project_dir is an existing directory (FileNotFoundError);
  - feature is non-empty, single-line and at most 200 characters; evidence is non-empty;
  - version defaults to `get_version(project_dir)` and must match `^\d+\.\d+\.\d+$` when present;
  - date defaults to today's local ISO date and must match `^\d{4}-\d{2}-\d{2}$`;
  - each `files` entry resolves inside project_dir and exists; store it as a posix path relative to project_dir;
  - `_private_path_findings` over feature, evidence, lesson and max_version must be empty (ValueError listing the findings).
- **Name:** `v{version}-{slug}-confirmed.md`, or `{date}-{slug}-confirmed.md` when unversioned, in project_dir/test-results (mkdir). On collision append `-2`, `-3`, … before `.md`. Never overwrite.
- **Content:** exactly the `<behavior>` layout, UTF-8, trailing newline, written with `atomic_write_bytes`.
- **Commit:** if `commit`, call `_auto_commit_saved_file(path)`, which is path-scoped, warns on any non-commit and never raises.
- Return the path.

Proven-forms helpers:
- frozen dataclass `ProvenForm(section, title, rule, form, why, evidence, tiers: tuple[str, ...])`.
- `parse_proven_forms(text) -> list[ProvenForm]`:
  - track `## ` headings; each `### ` starts an entry;
  - take each field from its `- **Rule:**` / `- **Form:**` / `- **Why:**` / `- Evidence:` line, plus the following indented continuation lines, joined with newlines;
  - tiers = the `[word]` tags in the evidence that are in PROVEN_TIERS, in order and unique;
  - missing fields become `""`.
- `format_proven_form(title, rule, form, why, evidence) -> str`:
  - validates title, rule, why and evidence: single line, non-empty, not starting with `#`, no `<!--`, no private paths;
  - form is a str (same checks) or a list of such strs, rendered as `- **Form:**` followed by `  - item` lines;
  - the evidence must carry at least one tier, and every `[lowercase-word]` tag in it must be a tier;
  - every `[confirmed]` clause (text up to the next `;` or end) must contain `v\d+\.\d+` and `\d{4}-\d{2}-\d{2}`;
  - returns `### {title}\n\n- **Rule:** …\n- **Form:** …\n- **Why:** …\n- Evidence: …\n`.
- `append_proven_form(section, title, rule, form, why, evidence, *, path=None, create_section=False) -> Path`:
  - path defaults to PROVEN_FORMS_PATH. Read the text and format the block first, since the format validates;
  - refuse `Evidence tiers`, and a title equal to an existing one, case-insensitive (ValueError);
  - find the exact `## {section}` heading and insert the block at the end of that section (before the next `## ` or EOF), with exactly one blank line before it and the original spacing kept after it;
  - an unknown section → ValueError listing the sections, unless create_section, which appends `\n## {section}\n\n{block}` at EOF;
  - write with `atomic_write_bytes`, re-parse, and if the new entry is missing or incomplete, restore the original bytes and raise RuntimeError;
  - no commit: the caller commits the file by explicit path. Say so in the docstring.

**Part C. Docs.** Rule 8 is satisfied because the task names the max-lifecycle skill and the /max-test flow.

.claude/commands/max-test.md:
- In step 5, say that `save_test_results` overwrites a same-named file, so name it `v<version>-<slug>-checklist`.
- Commit the results file with `auto_commit_patch(project_dir, base_dir, description=..., files=[str(path)])`.
- Add step 6, **Record confirmations**:
  - trigger: the user confirms in MAX that a feature works (a passing checklist item, or in conversation, including after a /max-iterate fix). Do not name the diagnosis command here: it does not exist until Task 3, and its own doc links back to this step;
  - call `record_confirmation(project_dir, feature, evidence, version=..., max_version=..., files=[...])`, with the user's words as evidence;
  - this writes test-results/…-confirmed.md and commits only that path.
- Add step 7, **Offer a proven-forms lesson**:
  - only for general MAX knowledge valid beyond this project;
  - draft it with `format_proven_form(...)` and evidence `[confirmed] <project> v<version> (<date>)`;
  - show it verbatim and ask with multiple choice: append as drafted / edit first / skip;
  - on append, call `append_proven_form(section, title, rule, form, why, evidence)`, then commit by explicit path: `git add .claude/skills/references/proven-forms.md` and `git commit -m "docs(proven-forms): …" -- .claude/skills/references/proven-forms.md`;
  - never copy private paths or project-only facts.
- Renumber "Update status" to step 8. Its status note is `v<version> <feature> confirmed in MAX <date>`.
- Extend the Python Modules imports.

.claude/skills/max-lifecycle/SKILL.md:
- extend the Python Interface import with `record_confirmation, format_proven_form, append_proven_form`;
- add a `### Confirmation Lifecycle` capability: trigger, record (the file pattern `test-results/v<version>-<slug>-confirmed.md`, never overwritten), offer, evidence tiers (link `.claude/skills/references/proven-forms.md`), consent, explicit-path commit;
- add a "When to Use" bullet: whenever the user says a feature works in MAX.

Do not edit .claude/skills/max-lifecycle/references/test-protocol.md or project-structure.md (trimmed for the per-plan budget; their stale result-file lines go to SUMMARY).

Every call form in these docs must bind against the real signatures; tests/test_doc_signatures.py checks them.
  </action>
  <verify>
    <automated>python3 -m pytest -q -p no:cacheprovider tests/test_testing.py tests/test_doc_signatures.py tests/test_commands.py tests/test_agent_skills.py tests/test_claude_md.py tests/test_dead_code_removed.py tests/test_release.py && git diff --quiet HEAD -- .claude/skills/references/proven-forms.md && test -s .planning/quick/261022-ksz-implement-q37-in-planning-reviews-2026-1/base-sha.txt && test -z "$(git log --format=%H "$(cat .planning/quick/261022-ksz-implement-q37-in-planning-reviews-2026-1/base-sha.txt)"..HEAD -- .claude/skills/references/proven-forms.md)"</automated>
    <fails_when>non-zero exit: a failed or errored test in the seven pytest files (summary line shows "failed" or "error", e.g. an unbound doc call form or a `/max-*` name without a command file); `git diff --quiet` exiting 1 because the working-tree proven-forms.md differs from HEAD; base-sha.txt missing; or git log since base-sha listing a commit that touched proven-forms.md</fails_when>
  </verify>
  <done>
- record_confirmation writes non-overwriting, validated, path-scoped-committed confirmation files.
- The proven-forms helpers parse the committed file and append validated entries to tmp copies only. The committed proven-forms.md is unchanged.
- max-test.md and the max-lifecycle SKILL.md document the flow, and their call forms bind.
- Commit with explicit paths only: `git add` the four task files by name, then `git commit -m "feat(maxpat): confirmation lifecycle -- record_confirmation + proven-forms appender (quick 261022-ksz, Q37)" -- <the same four paths>`. This commit is the second task boundary.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: agent-facing wiring: the `/max-diagnose` command over the Task 1 CLI, router domain overlays for Jitter, M4L and poly~, plus the full-suite regression gate</name>
  <files>.claude/commands/max-diagnose.md, tests/test_commands.py, .claude/skills/max-router/references/dispatch-rules.md, .claude/skills/max-router/SKILL.md, tests/test_agent_skills.py</files>
  <read_first>
    - src/maxpat/diagnose.py: the module docstring and `main()` (committed in Task 1: the CLI this command wraps)
    - .claude/commands/max-iterate.md: 1-60 (inline project parsing, the house style for commands)
    - tests/test_commands.py: 1-60 (ALL_COMMANDS), 118-145 (cross-reference test style)
    - tests/test_doc_signatures.py: 120-140 (call-form binding), 597-606 (`test_no_references_to_missing_commands`)
    - .claude/skills/max-router/SKILL.md, .claude/skills/max-router/references/dispatch-rules.md (whole)
    - tests/test_agent_skills.py: 1-110, 195-230, 470-490
    - CLAUDE.md "Max for Live (M4L / .amxd)" and "Subpatcher Inlet/Outlet Access" sections (already in context from the harness; do not re-read)
    - .claude/skills/references/proven-forms.md "poly~ voices" and "enum values" entries
    - src/maxpat/critics/m4l_critic.py: 87-110 (detect_m4l_device_type)
  </read_first>
  <behavior>
    - **Command doc.** max-diagnose.md exists with frontmatter `name: max-diagnose` and a description, and "max-diagnose" is in ALL_COMMANDS, so the frontmatter and minimum-content tests cover it.
      - `test_diagnose_references_troubleshooting_and_iterate`: the doc contains `troubleshooting.md`, `/max-iterate` and `python3 -m src.maxpat.diagnose`, and (lowercased) both `read-only` and `untrusted`.
      - Every call form in it binds against the real signatures (tests/test_doc_signatures.py, with src.maxpat.diagnose indexed since Task 1), and every `/max-*` it names exists.
    - **Overlay sections.** dispatch-rules.md has `## Domain Overlays` with three subsections, `### Jitter (video, matrices, OpenGL)`, `### Max for Live (M4L)` and `### poly~ (polyphonic voices)`.
      - Each contains the labels `**Detect (keywords):**`, `**Object references:**`, `**Agents:**`, `**Pass to specialists:**` and `**Checks:**`.
      - Each `**Agents:**` line names `max-patch-agent` or `max-dsp-agent` as lead.
    - **Object references.** Every backticked name on the three `**Object references:**` lines has `ObjectDatabase().lookup(name)` not None and `get_effective_restrictions(name) == []`.
    - **M4L checks.** The M4L subsection contains `Experimental`, `detect_m4l_device_type`, `plugin~`, `plugout~` and `live.thisdevice`.
    - **Quick reference.** Router SKILL.md contains `Domain Overlays`, `Jitter`, `M4L` and `poly~`.
    - **Existing tests.** The existing router tests and `test_dispatch_rules_no_stub_labels` still pass.
  </behavior>
  <action>
**Part A. Tests first** (all red until Parts B-D).
- tests/test_commands.py:
  - add `"max-diagnose"` to ALL_COMMANDS and update the module docstring count to 11;
  - add `test_diagnose_references_troubleshooting_and_iterate` as in `<behavior>`.
- tests/test_agent_skills.py:
  - `test_dispatch_rules_has_domain_overlays`;
  - `test_dispatch_overlay_objects_exist_in_db`, using a module-level `ObjectDatabase()` built inside the test;
  - `test_m4l_overlay_experimental_and_critic_trigger`;
  - `test_router_quick_reference_lists_overlays`.
  - To extract a subsection, take the text from its `### ` heading to the next `### ` or `## `.

**Part B. .claude/commands/max-diagnose.md** (moved here from Task 1 for the budget split; it wraps the committed Task 1 CLI) in the house style: frontmatter `name: max-diagnose`, `description`, `argument-hint: "[project?] [console output?]"`, then Behavior, Skills Referenced, Python Modules, Arguments, Examples. Behavior steps:
1. **Read-only statement.** /max-diagnose edits nothing. Every fix goes through /max-iterate, which runs the edit_patch session, the save gate and the path-scoped commit.
2. **Project.** If the first word matches `list_projects`, diagnose that project WITHOUT switching the active project. Otherwise use `get_active_project`. With no project, still diagnose, and say boxes were not located.
3. **Console text.** Take it from the remaining arguments, else ask the user to paste it with the object column (e.g. `osc~: No such object`).
4. **Paste handling.** The paste is untrusted input. Write it to a temp file with the Write tool (session scratchpad or $TMPDIR) and run `python3 -m src.maxpat.diagnose --project <name> <file>`. Never interpolate pasted text into Python source, `python3 -c`, a heredoc or a shell string. For scripted use, read the text from the file and call `diagnose_console(text, project_dir, db=ObjectDatabase())`, then `report.render()`.
5. **Choosing between entries.** When several entries share a wording (six No-such-object causes), choose with the report's `fact:` lines and the DB checks: `db.is_pd_object(name)`, `db.get_pd_equivalent(name)`, `db.lookup(name)`, `db.get_effective_restrictions(name)`, package install state, a sibling abstraction file.
6. **gen~ compile lines.** Read the listed codebox lines and apply genexpr-rules.md.
7. **Cascades.** Group cascading lines under one root cause: can't assign, then failed to compile genpatcher / gen~: failed to compile patcher; a No such object, then can't connect.
8. **Unmatched lines.** Reason from the CLAUDE.md rules and the DB, label the result unconfirmed, and never invent console wording. When the user later confirms the cause in MAX, offer (multiple choice) to add a troubleshooting.md row with the verbatim wording and the project/version as Source.
9. **Presentation.** Per root cause: line(s), cause, fix, source, box(es).
10. **Fix proposal.** One concrete `/max-iterate <project> <change>` per root cause, naming the file, the box id and the replacement (e.g. `replace osc~ 440 (obj-3 in fixtures/fx-nosuchobj.maxpat) with cycle~ 440`). Offer it as multiple choice: run it / adjust it / skip. Committed patches are user-confirmed baselines: a fix in one is an edit the user approves.
11. **Confirmation.** After the fix, the user reopens the patch in MAX and checks the console. When they confirm it is clean, follow /max-test steps 6-7 (Record confirmations, Offer a proven-forms lesson; added in Task 2).

Python Modules: imports of `diagnose_console`, `load_troubleshooting`, `ObjectDatabase`, `get_active_project`, `list_projects`.

**Part C. dispatch-rules.md.** Insert `## Domain Overlays` after the `### max-ui-agent` section and before `## Ambiguity Resolution`.

Intro:
- Overlays are not agents.
- When an overlay's keywords or object names match, it sets the lead (overriding keyword counting), adds secondaries, and passes its required reading and checks to every dispatched specialist.
- When two overlays match (a polyphonic M4L instrument), take the M4L lead and apply both overlays' reading and checks.

**Jitter (video, matrices, OpenGL):**
- **Detect (keywords):** jitter, video, camera / webcam, texture, OpenGL / GL, shader, 3D render, mesh, particles, pixel processing, Vizzie, any `jit.*` name. "matrix" alone is NOT Jitter (mod matrix, routing matrix).
- **Object references:** the Jitter list from the context Interfaces, backticked.
- **Agents:**
  - lead max-patch-agent: matrix and render chains are newobj control flow (qmetro or jit.world drive, matrix routing);
  - plus max-dsp-agent for jit.gen / jit.pix / jit.gl.pix codeboxes (GenExpr, under the codebox safe-construct rules in genexpr-rules.md) and for audio-to-matrix bridges (jit.catch~, jit.release~, jit.buffer~, jit.poke~, jit.peek~);
  - plus max-ui-agent when jit.pwindow goes into presentation;
  - plus max-js-agent only when JS scripting is asked for.
- **Pass to specialists:** proven-forms.md "enum values" (check jit.* attribute values in the bundle maxref/help before use; jit.bfg @basis); look jit.* objects up in ObjectDatabase (domain Jitter).
- **Checks:** never route Jitter to max-rnbo-agent (no RNBO equivalent); jit.gen / jit.pix / jit.gl.pix inner patchers validate in gen scope.

**Max for Live (M4L):**
- Starts with: **Experimental:** not yet confirmed in MAX or Live.
- **Detect (keywords):** max for live, m4l, ableton, Live device, amxd, audio effect device, instrument device, MIDI effect device, Live parameter / automation, Push, plugin~ / plugout~ / live.thisdevice.
  - "live" alone (live input, live performance, live coding) is not M4L.
  - A live.dial face in a plain MAX patch is UI (max-ui-agent), not M4L.
- **Object references:** the M4L list from the context Interfaces.
- **Agents:**
  - audio effect or instrument: lead max-dsp-agent (the `add_m4l_gen_synth` builder, experimental);
  - MIDI effect: lead max-patch-agent;
  - plus max-ui-agent for live.* controls in presentation;
  - plus max-js-agent only for Live API scripting asked for in JS.
- **Pass to specialists:** CLAUDE.md "Max for Live (M4L / .amxd)" (no gain~ / live.gain~ / ezdac~ before plugout~; live.dial / live.slider bind through param_connect with parameter_enable); the add_m4l_gen_synth docstring; "Builder API" in shared-capabilities.md.
- **Checks:**
  - `review_patch` runs the M4L critic only when `detect_m4l_device_type` finds plugin~, plugout~ or live.thisdevice (plugin~ gives an audio effect, else plugout~ an instrument, else a MIDI effect), so every M4L build includes them;
  - the framework writes .maxpat only (no .amxd writer);
  - report the result as experimental.

**poly~ (polyphonic voices):**
- **Detect (keywords):** poly~, polyphony / polyphonic, N-voice synth, voice allocation, voice stealing, thispoly~. "voice" alone (vocal processing, harmonizer voices) is not poly~.
- **Object references:** the poly~ list from the context Interfaces.
- **Agents:**
  - lead max-dsp-agent (the voice abstraction);
  - plus max-patch-agent for the host: note to `midinote` / `note` / `target` messages, the voice file and the `poly~ <voice> N` arguments, thispoly~ busy/mute;
  - plus max-ui-agent for host controls.
- **Pass to specialists:** proven-forms.md "poly~ voices"; troubleshooting.md (No such object when the voice file is not next to the host).
- **Checks:**
  - the voice is a separate .maxpat next to the host, and the walker never loads it, so run validate_patch and review_patch on the voice file too;
  - inside the voice, use in / in~ / out / out~ (not inlet / outlet) for poly~ I/O;
  - new inlets on a shared voice abstraction go rightmost.

Also in dispatch-rules.md (Part C continued):
- Add Edge Cases rows:
  - "video mixer with crossfade" → Patch (Jitter), lead Patch;
  - "audio-reactive 3D visuals" → Patch (Jitter) + DSP, lead Patch;
  - "mod matrix for a synth" → DSP, lead DSP (not Jitter);
  - "M4L audio effect" → DSP (M4L) + UI, lead DSP;
  - "M4L MIDI effect" → Patch (M4L) + UI, lead Patch;
  - "8-voice poly synth" → DSP (poly~) + Patch, lead DSP;
  - "polyphonic M4L instrument" → DSP (M4L + poly~) + Patch + UI, lead DSP;
  - "live input looper" → DSP, lead DSP ("live" alone is not M4L).
- Add one line under Ambiguity Resolution: domain overlays are applied before the default lead hierarchy.
- Name only objects that resolve in the DB (Rule #1). Never add `-- STUB` markers.

**Part D. router SKILL.md.**
- After the quick-reference table, add a short `**Domain Overlays**` table with columns Overlay | Lead | Also | Detect, and three rows (Jitter, M4L (experimental), poly~), plus one sentence pointing to `references/dispatch-rules.md` "Domain Overlays".
- Add three "Common multi-domain patterns" examples.
- In Output Protocol step 3, pass the matched overlay's required reading and checks to the specialists.
- Under "When NOT to Use", add `/max-diagnose`: read-only diagnosis; its proposed fix runs through /max-iterate, which routes.

**Part E. Commits, then the final gate.** QDIR is .planning/quick/261022-ksz-implement-q37-in-planning-reviews-2026-1.
1. Commit the command with explicit paths: `git add .claude/commands/max-diagnose.md tests/test_commands.py`, then `git commit -m "feat(commands): /max-diagnose read-only console diagnosis (quick 261022-ksz, Q37)" -- .claude/commands/max-diagnose.md tests/test_commands.py`.
2. Commit the router docs: `git add` the three router paths by name, then `git commit -m "docs(router): Jitter, M4L and poly~ domain overlays (quick 261022-ksz, Q37)" -- <the same three paths>`.
3. Run the `<verify>` command verbatim. It runs the targeted doc tests, then the full suite itself (about 3 minutes), writing final-junit.xml, final-pytest.txt and final-rc.txt fresh inside the same command. It trusts no earlier QDIR output except the Step 0 snapshots, and it fails if any of them is missing.
4. Any regression: fix it in the owning task's files, commit the fix by explicit path, re-run the verify, and record it in SUMMARY.
  </action>
  <verify>
    <automated>python3 -m pytest -q -p no:cacheprovider tests/test_agent_skills.py tests/test_commands.py tests/test_doc_signatures.py && test -f .planning/quick/261022-ksz-implement-q37-in-planning-reviews-2026-1/stash-list-before.txt && test -f .planning/quick/261022-ksz-implement-q37-in-planning-reviews-2026-1/patches-status-before.txt && test -s .planning/quick/261022-ksz-implement-q37-in-planning-reviews-2026-1/base-sha.txt && test -s .planning/quick/261022-ksz-implement-q37-in-planning-reviews-2026-1/baseline-junit.xml && { python3 -m pytest -q -p no:cacheprovider --junitxml=.planning/quick/261022-ksz-implement-q37-in-planning-reviews-2026-1/final-junit.xml > .planning/quick/261022-ksz-implement-q37-in-planning-reviews-2026-1/final-pytest.txt 2>&1; echo $? > .planning/quick/261022-ksz-implement-q37-in-planning-reviews-2026-1/final-rc.txt; } && python3 -c "import sys, xml.etree.ElementTree as E; base = int(any(x.tag in ('failure', 'error') for c in E.parse(sys.argv[1]).getroot().iter('testcase') for x in c)); fin = int(open(sys.argv[2]).read().strip()); print('baseline_rc', base, 'final_rc', fin); sys.exit(0 if base >= fin else 1)" .planning/quick/261022-ksz-implement-q37-in-planning-reviews-2026-1/baseline-junit.xml .planning/quick/261022-ksz-implement-q37-in-planning-reviews-2026-1/final-rc.txt && python3 .planning/quick/261022-ksz-implement-q37-in-planning-reviews-2026-1/junit_diff.py .planning/quick/261022-ksz-implement-q37-in-planning-reviews-2026-1/baseline-junit.xml .planning/quick/261022-ksz-implement-q37-in-planning-reviews-2026-1/final-junit.xml && test "$(git status --porcelain patches patterns)" = "$(cat .planning/quick/261022-ksz-implement-q37-in-planning-reviews-2026-1/patches-status-before.txt)" && test "$(git stash list)" = "$(cat .planning/quick/261022-ksz-implement-q37-in-planning-reviews-2026-1/stash-list-before.txt)" && git merge-base --is-ancestor "$(cat .planning/quick/261022-ksz-implement-q37-in-planning-reviews-2026-1/base-sha.txt)" HEAD && test -z "$(git log --name-only --format= "$(cat .planning/quick/261022-ksz-implement-q37-in-planning-reviews-2026-1/base-sha.txt)"..HEAD -- patches patterns)"</automated>
    <fails_when>non-zero exit from any step: a failed or errored test in the three targeted files; a Step 0 snapshot (stash-list-before.txt, patches-status-before.txt, base-sha.txt, baseline-junit.xml) missing or empty; the full-suite run inside this command exiting above the baseline status (the python step prints "baseline_rc X final_rc Y" with Y greater than X and exits 1); junit_diff.py printing a REMOVED, REGRESS, FOREIGN or ADDFAIL line; the patches/patterns porcelain output or the stash list differing from Step 0; base-sha not an ancestor of HEAD; or git log since base-sha naming any file under patches/ or patterns/</fails_when>
  </verify>
  <done>
- max-diagnose.md is registered in ALL_COMMANDS, and its call forms bind against the real signatures.
- dispatch-rules.md and the router SKILL.md carry the three DB-verified overlays.
- The full-suite run inside the verify has rc <= the baseline status derived from baseline-junit.xml, and junit_diff exits 0.
- The patches/patterns porcelain output and the stash list match Step 0.
- No commit since base-sha touches patches/ or patterns/.
- Four feature commits exist (Task 1, Task 2, and Task 3's command and router commits), each with explicit paths.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| pasted console text → diagnose parser | untrusted, arbitrary text from the user's clipboard |
| CLI args (`--project`, file, `--base-dir`) → filesystem | names and paths choose what is read |
| user/agent text → test-results/ and proven-forms.md | proven-forms.md is read by future agents as guidance, so its content persists as instructions |
| confirmation writer → git repository | it commits; other work may be staged in the same index |
| diagnose → user-approved patches | committed patches are confirmed baselines; diagnosis must never change them |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-ksz-01 | Elevation (code injection) | /max-diagnose paste handling | high | mitigate | The command doc requires the paste to be written to a temp file with the Write tool and passed as a file or stdin. Interpolating it into `python3 -c`, a heredoc or a shell string is forbidden. A test asserts the doc carries the "untrusted" instruction and names the CLI form. |
| T-ksz-02 | Tampering (patch change) | diagnose.py / /max-diagnose | high | mitigate | The module is read-only, and an AST gate rejects hooks, atomic_io, subprocess, shutil, write/rename/unlink calls and writing `open()` modes. The CLI test hashes every file under patches/max-bridge before and after. Fixes go only through a user-approved /max-iterate (edit_patch save gate). |
| T-ksz-03 | Tampering (path traversal) | `--project`, `record_confirmation` slug and `files` | high | mitigate | `--project` is validated as a single path component naming an existing patches/ directory (rc 2 otherwise). The confirmation filename is a `[a-z0-9-]` slug inside test-results/. `files` entries must resolve inside project_dir. The locator skips files whose resolved path leaves project_dir and does not follow symlinked directories. Tests cover `../x` and `../../etc passwd`. |
| T-ksz-04 | Tampering / Elevation (persistent instruction injection) | append_proven_form → proven-forms.md | high | mitigate | Appending happens only after the user picks "append" in a multiple-choice prompt showing the verbatim entry. The fields are single-line, with no leading `#` and no `<!--`. Evidence needs known tiers, and `[confirmed]` needs a version and a date. Duplicates and the Evidence-tiers section are refused. The write is atomic, followed by a re-parse with rollback. The commit uses an explicit path, so it is reviewable in git. |
| T-ksz-05 | Information disclosure | test-results/ and proven-forms.md content | medium | mitigate | `_private_path_findings` (/Users/, /home/, .planning/, ~/.claude, memory-note filenames) rejects the write. A test pins the committed proven-forms.md and troubleshooting.md as clean. |
| T-ksz-06 | Tampering (commit scope) | record_confirmation commit | high | mitigate | The commit goes only through hooks._auto_commit_saved_file (path-scoped `git commit -- <path>`; it warns and never raises). The throwaway-repo test asserts that HEAD names only the confirmation file and that the pre-staged file stays staged. Docs commit proven-forms.md by explicit path. No `git add -A`. |
| T-ksz-07 | Denial of service | console matcher | medium | mitigate | Input is capped at 2000 lines of 2000 characters. Patterns use `\S+`, `.*?` and `[^']+` between literals. A test covers a 2500-line paste and a 5000-character line. Patch files are read once per report (cache). |
| T-ksz-08 | Tampering (test pollution) | tests/test_diagnose.py, tests/test_testing.py | high | mitigate | Committed patches are only read. Writes go to tmp_path, and git work happens in `_repo(tmp_path)` with env isolation. The final gate compares the patches/patterns porcelain output and the stash list with Step 0. |
| T-ksz-09 | Spoofing (misrouting) | router overlays | low | accept | Markdown dispatch guidance only. Every object named resolves in the DB (test), and M4L is labelled experimental. |
| T-ksz-SC | Tampering | npm/pip/cargo installs | high | mitigate | No packages are installed; stdlib and in-repo modules only. tests/test_release.py's third-party import check stays green. |
</threat_model>

<verification>
- `python3 -m pytest -q -p no:cacheprovider tests/test_diagnose.py tests/test_testing.py tests/test_commands.py tests/test_agent_skills.py tests/test_doc_signatures.py tests/test_claude_md.py tests/test_dead_code_removed.py tests/test_release.py` passes.
- `printf 'osc~: osc~: No such object\n' | python3 -m src.maxpat.diagnose --project max-bridge -` prints a box line for fixtures/fx-nosuchobj.maxpat obj-3 and a `/max-iterate max-bridge` proposal.
- The full-suite run executed inside Task 3's verify has rc <= the baseline status derived from QDIR/baseline-junit.xml, and QDIR/junit_diff.py exits 0. Task 1's verify proved that baseline is a pre-edit run.
- The patches/ and patterns/ porcelain output and the stash list match their Step 0 snapshots.
- `git log --name-only base-sha..HEAD` shows nothing under patches/ or patterns/. Apart from .planning/ docs, it names only files in files_modified.
</verification>

<success_criteria>
- Q37 is delivered:
  - `/max-diagnose` maps each pasted console line to cause and fix via troubleshooting.md, locates the offending box in the active project's patches, and proposes the `/max-iterate` fix, all read-only;
  - a user confirmation is written to `patches/<project>/test-results/` and committed, and a tiered general lesson can be appended to proven-forms.md with consent;
  - the router has Jitter, M4L and poly~ domains in its dispatch rules.
- Every `<behavior>` case is pinned by a test, and every threat with disposition mitigate has its test or doc guard.
</success_criteria>

<output>
Create `.planning/quick/261022-ksz-implement-q37-in-planning-reviews-2026-1/261022-ksz-SUMMARY.md` when done. Include:
- the baseline and final pytest rc and counts (final = the full-suite run inside Task 3's verify), the junit_diff result, and any pre-existing failures;
- whether any task boundary was handed to a fresh continuation (see Task boundaries in `<objective>`);
- the Claude's-discretion choices:
  - the diagnose module + CLI split;
  - the match tiers and the depth-0 parse contract;
  - the locator order;
  - the confirmation file naming and commit policy;
  - overlays instead of new agents;
- the troubleshooting.md edits (the parse-contract sentence, and the `gen~: failed to compile patcher` companion with its source);
- the doc impact NOT edited (fix-plan rule 8):
  - README.md Commands table (no `/max-diagnose` row);
  - TECHNICAL.md lifecycle/commands tables;
  - CLAUDE.md reference list;
  - shared-capabilities.md troubleshooting pointer (could name /max-diagnose);
  - max-verify.md `--live` findings (could point to /max-diagnose);
  - troubleshooting.md could name /max-diagnose in its header (Task 1 names only the module, because the command did not exist yet);
  - .claude/skills/max-lifecycle/references/test-protocol.md: its "Result Recording" claims incrementing `test-NNN.md` files (save_test_results writes `<test_name>.md` and overwrites), and it has no Confirmations section (trimmed from this plan for the per-plan budget);
  - .claude/skills/max-lifecycle/references/project-structure.md: its `test-001.md` tree line (could show `v<version>-<slug>-checklist.md` and `-confirmed.md`; trimmed for the same reason);
  - the follow-up that tools/max_verify_live.py could reuse src.maxpat.diagnose instead of its own wording table;
- items for the user to confirm in MAX (fix-plan rule 9):
  - the paste format of a Max 9.2 Console copy: whether the object column is included and how it is separated (tab vs `obj: msg`). The matcher handles `obj: msg`, a doubled prefix and a bare message; a tab-separated object column without a colon would only match in the no-prefix tier;
  - that the M4L overlay stays experimental until a device is confirmed in Live.
</output>
