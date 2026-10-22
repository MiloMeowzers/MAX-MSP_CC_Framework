---
phase: quick-261021-olv
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - tools/max_bridge.py
  - tests/test_max_bridge.py
  - tools/max_verify_live.py
  - tests/test_max_verify_live.py
  - patches/max-bridge/context.md
  - patches/max-bridge/status.md
  - patches/max-bridge/versions.json
  - .claude/commands/max-verify.md
  - .claude/skills/references/severity-contract.md
  - patches/max-bridge/test-results/v0.3.0-verify-live-checklist.md
autonomous: true
requirements: [Q34]

estimate:
  tokens: 170000
  raw_tokens: 170000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "D-01: an audio-input patch (adc~, ezadc~, mc.adc~ or mc.ezadc~ anywhere in its JSON tree, or in a sibling .maxpat it references) is load-only by default. `--live-inputs` opts it into recording (and into the D-02 DSP-on-load)."
    - "D-02: every load-only patch gets `check --dsp-on-load`. That flag sends /dsp 1 just before the /open, so DSP-time errors (gen~ `failed to compile`) post during the load settle. The bridge's existing restore rule then puts DSP back the way it found it: /dsp 0 when it was off or unknown, nothing when it was already on, and the BridgeError cleanup switches it off too. Exception: an audio-input patch never gets --dsp-on-load unless --live-inputs is passed. Without the flag, the bridge's message plan is exactly what it is today."
    - "D-03: `/max-verify --live` leaves the static Summary line's counts untouched. Live counts sit beside it: `(live: b blockers, w warnings, n notes)` or `(live check skipped: <hint>)` / `(live check aborted: <hint>)`."
    - "D-04: nothing in tools/max_verify_live.py toggles the kill switch or opens the bridge patch. An AST test pins this: no `.send` call; no `open`, `osascript`, `/dsp` or `/listen` string constants. MAX is reached only through bridge.run_check and a read-only Bridge.ping pre-flight."
    - "Skip path: when there is no bridge patch in the install, MAX is not running, or the ping times out (bridge closed, or toggle OFF), the result is status `skipped` with a hint, exit 2, and no `__maxbridge_*` copy is ever written."
    - "Severity comes from map_findings, never from the bridge's exit_code or verdict. A console error with an ERROR_WORDINGS key is a blocker, other console errors are warnings, nonfinite/runaway is a blocker, clipping/dc_offset/silent are warnings. sr_changed_during_run/short_recording demote every record flag to a note. Unsupported outputs and shot failures are notes. closed False and feedback_suspected are warnings. severity-contract.md §7 states the same table."
    - "Top-level selection: from the project's generated/*.maxpat it drops `__maxbridge_*` and every file a sibling references (a bpatcher `name`, a newobj first token, or the poly~/mc.poly~/pfft~ argument; comments never count, and a file never excludes itself). terrain-synth resolves to [terrain-synth.maxpat]."
    - "Batch safety: patches run strictly one after another. The first bridge_failed after a good pre-flight aborts the run (status `aborted`, exit 2, later patches `not checked`). A patch whose original is open in MAX is skipped with a note. An exception in one patch becomes a warning and the loop goes on."
    - "Regression: all 124 pre-existing tests in tests/test_max_bridge.py pass unedited. The full-suite junit diff against the Step 0 baseline is clean. The stash list is unchanged and no `__maxbridge_*` file is left anywhere under patches/."
  artifacts:
    - path: "tools/max_verify_live.py"
      provides: "the /max-verify --live orchestrator: patch resolution, top-level selection, pre-flight, per-patch option rules (D-01/D-02), sequential bridge.run_check loop, map_findings, human/JSON report, exit codes 0/1/2"
      contains: "def map_findings("
    - path: "tools/max_bridge.py"
      provides: "opt-in `check --dsp-on-load` (one plan_messages insertion before the opener) plus docstring status text"
      contains: "--dsp-on-load"
    - path: "tests/test_max_verify_live.py"
      provides: "hermetic coverage on FakeBridge: option rules, mapping table, skip/abort/crash/open-original paths, top-level selection, D-04 AST guard, doc guards"
      contains: "from tests.test_max_bridge import FakeBridge"
    - path: ".claude/skills/references/severity-contract.md"
      provides: "§7 Live findings: the mapping table, report-only status, exit codes, the beside-not-merged Summary rule"
      contains: "## 7. Live findings"
    - path: ".claude/commands/max-verify.md"
      provides: "--live flags, step 7, safety notes, live output block, the Summary suffix"
      contains: "tools/max_verify_live.py"
    - path: "patches/max-bridge/test-results/v0.3.0-verify-live-checklist.md"
      provides: "the manual MAX confirmation for v0.3.0"
      contains: "fx-genfail"
  key_links:
    - from: "tools/max_verify_live.py check_argv (load-only, not audio-input-locked)"
      to: "tools/max_bridge.py plan_messages ('/dsp', (1,)) before the opener"
      via: "the --dsp-on-load flag parsed by bridge.build_parser()"
      pattern: "dsp_on_load"
    - from: "tools/max_verify_live.py"
      to: "tools.max_bridge (one module object)"
      via: "`from tools import max_bridge as bridge` after REPO_ROOT is put on sys.path; test asserts live.bridge is tools.max_bridge"
      pattern: "from tools import max_bridge as bridge"
    - from: "scan_patch tapped/note_kind"
      to: "bridge._instrument_patcher / bridge._inject_note"
      via: "run on a throwaway in-memory Patcher, so the option choice uses the bridge's own tap rule"
      pattern: "_instrument_patcher("
    - from: "map_findings rows"
      to: "severity-contract.md §7 table"
      via: "doc guard test: every ERROR_WORDINGS entry and every record flag name appears in §7"
      pattern: "## 7. Live findings"
---

<objective>
Add an opt-in `/max-verify --live` mode. After the static validation and critic review, it loads each top-level patch of the active project in the running MAX through the confirmed max-bridge (v0.1.0/v0.2.0, commit dc0cde91), and reports MAX's own console errors, recording flags and screenshots as live findings. Those findings are report-only and are mapped to blocker/warning/note per a new severity-contract.md §7.

Locked user decisions (numbered here from the planning brief):
- D-01: audio-input patches (adc~/ezadc~) are load-only by default; `--live-inputs` opts them into recording.
- D-02: load-only patches get DSP turned ON briefly during the load settle, to catch DSP-time gen~ compile errors, and DSP is then restored to its prior state. Exception (feedback safety): audio-input patches do NOT get DSP on unless `--live-inputs` is passed.
- D-03: live counts sit BESIDE the static Summary line, never merged into it.
- D-04: the kill switch is never toggled programmatically, and the bridge patch is never opened programmatically.

Design source: .planning/quick/261021-olv-max-verify-live-mode-via-max-bridge/261021-olv-RESEARCH.md. That research deferred DSP-on-load (its Open Question 1); D-02 now requires it. This plan adds it as the single, opt-in logic change to tools/max_bridge.py.

Purpose: "pending test in MAX" is the bottleneck. /max-verify --live closes the gap between the validator's prediction ("will not load") and MAX's ground truth, without ever making static verification depend on MAX.

Output: tools/max_verify_live.py and tests/test_max_verify_live.py; `check --dsp-on-load` in tools/max_bridge.py with new tests; an updated max-verify.md command and severity-contract.md §7; max-bridge v0.3.0 records (versions.json, status.md, context.md) and a v0.3.0 manual checklist.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@CLAUDE.md
@.planning/quick/261021-olv-max-verify-live-mode-via-max-bridge/261021-olv-RESEARCH.md
@tools/max_bridge.py
@tests/test_max_bridge.py
@.claude/commands/max-verify.md
@.claude/skills/references/severity-contract.md
@patches/max-bridge/context.md

Facts the executor relies on (verified while planning, 2026-10-21):
- tools/max_bridge.py `plan_messages` (about line 876): the plan is [/ping, /query, /ping, /console write, (showonlyerrors), /listen 1, opener, /ping, (record block), RESTORE_DSP, ...]. `_execute` (about line 1103) waits on the load barrier only when `prev in openers` (load_timeout + settle). Sending any "/dsp" sets report["_dsp_on"]. The RESTORE_DSP slot sends /dsp 0 when dsp_before is 0, or when it is None and _dsp_on is set. The BridgeError cleanup sends /dsp 0 when _dsp_on is set and dsp_before != 1.
- The v0.2.0 checklist step 5 confirms that with DSP already on when fx-genfail loaded, MAX posted `failed to compile genpatcher` and `failed to compile patcher`. So /dsp 1 placed before the /open reproduces that confirmed condition.
- `run_check(args)` (about line 1242) never prints. It writes the sibling `__maxbridge_<stem>.maxpat` copy BEFORE contacting the bridge, deletes it in a finally block, and returns verdict "bridge_failed" with copy None when guard_input refuses. `main()`, not run_check, validates `--note` (it needs --record and a pitch/velocity range).
- `instrument()` computes taps with `_instrument_patcher(p, "top", report)` on `Patcher.from_dict(json.loads(text))`, using report keys taps{L,R}, tap_boxes, unsupported, warnings, note_target. `_inject_note(p, report)` sets note_target to {kind: notein|kslider} or appends `--note: no notein or kslider to drive`.
- tests/test_max_bridge.py exports FakeBridge (errors, flood, mute_after_open, dsp_on, answers_query, max_sr, ...), `_tone_patch(path, db, dac_args=None, both=True, dac="dac~")`, `_free_port()`, and the `run_dir` / `_check` helpers. tests/__init__.py exists; tools/ has no __init__.py (namespace package; `import tools.max_bridge` works from the repo root).
- The QDIR junit gate (.planning/quick/261016-uy1-implement-q34-in-planning-reviews-2026-1/junit_diff.py) flags any NEW test outside tests.test_max_bridge as FOREIGN. Step 0 therefore makes a local copy that also accepts tests.test_max_verify_live.
- The object DB has adc~ (MSP), ezadc~ (MSP), mc.adc~ (MC) and mc.ezadc~ (MC). ezadc~, ezdac~ and kslider are UI maxclasses.
- Sibling-reference prototype run while planning: terrain-synth's top level is only terrain-synth (children: terrain-voice, terrain-osc, terrain-osc-b, terrain-lfo, terrain-cheby); simple-fm's is simple-fm; barnett-dbap's are barnett-dbap and control-demo.
- tests/test_commands.py and tests/test_agent_skills.py require max-verify.md to keep `review_patch` and `from src.maxpat import`, and to NOT contain `from src.maxpat.validation` or `from src.maxpat.code_validation`. tests/test_claude_md.py requires severity-contract.md to keep StaleFileError, SaveGateWarning, x-rank, force=True and PatchValidationError.

QDIR = .planning/quick/261021-olv-max-verify-live-mode-via-max-bridge
</context>

<tasks>

<task type="tracer">
  <name>Task 1 (tracer): `max_verify_live.py PATCH` runs end to end through the bridge's new opt-in --dsp-on-load, with the D-01/D-02 option rules and the §7 mapping</name>
  <files>tools/max_bridge.py, tests/test_max_bridge.py, tools/max_verify_live.py, tests/test_max_verify_live.py</files>
  <read_first>
    - tools/max_bridge.py: lines 1-70 (docstring), 349-351 (OUTPUT_BOXES, UNSUPPORTED_OUTPUTS), 374-446 (_instrument_patcher, _walk_patchers), 463-576 (_inject_note, instrument), 822-862 (ERROR_WORDINGS, guard_input), 876-918 (plan_messages), 1103-1186 (_execute), 1242-1350 (run_check, _bridge_hint), 1364-1400 (build_parser), 1451-1468 (main)
    - tests/test_max_bridge.py: lines 45-160 (FakeBridge), 546-557 (_tone_patch), 1052-1180 (run_dir, _check, TestCheck DSP tests)
    - .planning/quick/261021-olv-max-verify-live-mode-via-max-bridge/261021-olv-RESEARCH.md (Severity mapping, Common Pitfalls)
  </read_first>
  <action>
**Step 0. Baseline, before any edit.**
- Write `git rev-parse HEAD` to QDIR/base-sha.txt and `git stash list` to QDIR/stash-list-before.txt.
- Copy the gitignored patches/.active-project.json to QDIR/active-project-before.json. Task 2's verify checks that nothing rewrote it.
- Copy .planning/quick/261016-uy1-implement-q34-in-planning-reviews-2026-1/junit_diff.py to QDIR/junit_diff.py. In the copy only, extend the `ours` test so that a key starting with `tests.test_max_verify_live` also counts as ours. Leave the original untouched.
- Run `python3 -m pytest -q -p no:cacheprovider --junitxml=QDIR/baseline-junit.xml` and record the pass/fail counts. Pre-existing failures are allowed: the gate is the diff.
- Run `python3 -m pytest tests/test_max_bridge.py -q -p no:cacheprovider` and record the count (expect 124 passed).

**Part A. The bridge hook (D-02).** This is the only logic change in tools/max_bridge.py. Keep it opt-in.
- `build_parser`, check subparser: add `--dsp-on-load` (store_true, default False). Help text: "switch DSP on just before the /open so DSP-time errors (gen~ compiles) post during the settle; the prior DSP state is restored as after --record".
- `plan_messages`: when `getattr(opts, "dsp_on_load", False)` is true, append `("/dsp", (1,))` right after `("/listen", (1,))` and immediately before the opener (`/open`, or `/openfile` in openfile mode). Use getattr because some callers pass plain namespaces.
  - Never put it between the opener and its /ping. `_execute` keys the load wait (load_timeout + settle) on `prev in openers`, so anything inserted there would shrink the load wait to the 2 s generic ping.
  - Placing it before the /open also reproduces the v0.2.0 step-5 condition (DSP already on at load).
- `_execute`, `run_check` and `RESTORE_DSP` stay unchanged. The existing restore and cleanup rules already cover a /dsp 1 that this run sent. Without the flag the plan is identical to today's.
- Module docstring, text only:
  - Replace the SPIKE STATUS paragraph (lines 3-9) with: v0.1.0 and v0.2.0 confirmed in MAX 9.2 through their checklists (2026-10-21, commit dc0cde91); v0.3.0 adds `check --dsp-on-load` and the `/max-verify --live` wrapper tools/max_verify_live.py, pending patches/max-bridge/test-results/v0.3.0-verify-live-checklist.md.
  - Add `[--dsp-on-load]` to the `check` usage line.
  - Add one sentence to the "DSP restore (v0.2.0)" paragraph: --dsp-on-load sends /dsp 1 before /open, and the same restore rule applies.
- New tests in tests/test_max_bridge.py, in a new class `TestDspOnLoad`. Do not edit or rename any existing test. Use the existing `run_dir` fixture and `_check` helper.
  - Plan placement: with --dsp-on-load, `("/dsp", (1,))` sits at index(opener) - 1, after the first /query, in both pcontrol and openfile modes. A flagless load-only plan contains no `("/dsp", (1,))`.
  - DSP off before: `FakeBridge(dsp_on=0)` with `_check(fb, src, "--dsp-on-load", capsys=capsys)` gives rc 0. `("/dsp", [1])` is received before the first "/open" and `("/dsp", [0])` after it. The report has dsp_before 0 and dsp_stop_sent True, and fb.dsp_on ends at 0.
  - DSP on before: `FakeBridge(dsp_on=1)` receives no `("/dsp", [0])`, dsp_stop_sent is False, and fb.dsp_on stays 1.
  - Query unanswered: `FakeBridge(answers_query=False)` receives `("/dsp", [0])`, and a warning starting with dsp_state_unknown is present.
  - Bridge stops answering: `FakeBridge(mute_after_open=True, dsp_on=0)` gives rc 2 and `("/dsp", [0])` in fb.received (the BridgeError cleanup), and no `__maxbridge_` copy is left.
  - Dry run: `--dsp-on-load --dry-run` prints "/dsp 1" on the line right before the "/open ..." line.

**Part B. tools/max_verify_live.py (new).** Stdlib plus in-repo imports only, `#!/usr/bin/env python3`, subprocess with argv lists and never a shell.
- Header: `REPO_ROOT = Path(__file__).resolve().parent.parent`; put REPO_ROOT on sys.path if it is absent; then `from tools import max_bridge as bridge`. Never use a bare `import max_bridge`: running the script puts tools/ on sys.path[0], so that import would make a second module object and test monkeypatches would miss (RESEARCH Pitfall 6).
- Module docstring:
  - purpose and D-01..D-04;
  - exit codes 0/1/2;
  - this tool never switches the bridge's enable toggle and never opens the bridge patch: the user does both;
  - a pointer to the LAN caveat in tools/max_bridge.py;
  - Ctrl-C skips the bridge's cleanup, so DSP may stay on and a temp window may stay open (close it without saving).
- Constants:
  - `INPUT_BOXES = ("adc~", "ezadc~", "mc.adc~", "mc.ezadc~")`
  - `DEFAULT_RECORD_S = 3.0`
  - `DEFAULT_NOTE = (60, 100)`
  - `REMINDER`: "Turn the bridge's enable toggle OFF (or close the bridge patch) when done: it listens on UDP 7400 on all network interfaces."
  - Reuse bridge.OUTPUT_BOXES, UNSUPPORTED_OUTPUTS, ERROR_WORDINGS and COPY_PREFIX by reference; never retype them.
- `_references(patch_json, sibling_stems) -> set[str]`, for Task 2's selection and for the input scan. Walk the raw JSON recursively through every nested "patcher". Only newobj and bpatcher boxes count; comment and message text never does. Collect:
  - a bpatcher's `name`, as its stem;
  - a newobj whose first text token equals a sibling stem;
  - the first argument of poly~, mc.poly~ or pfft~, as its stem (strip `.maxpat`).
  Return only stems that are in sibling_stems.
- `scan_patch(path) -> dict` with keys tapped, unsupported, note_kind, inputs, input_where:
  - Tap rule: build a throwaway in-memory `Patcher.from_dict(json.loads(text))` with a scratch report `{"taps": {"L": 0, "R": 0}, "tap_boxes": [], "unsupported": [], "warnings": [], "note_target": None}`. Run `bridge._instrument_patcher(p, "top", scratch)`, then `bridge._inject_note(p, scratch)`. Nothing is written. Because this is the bridge's own tap and note-target logic, the option choice can never disagree with what `check` will tap.
    - tapped = taps L + R > 0;
    - unsupported = the sorted distinct `name`s in scratch["unsupported"];
    - note_kind = scratch["note_target"]["kind"], or None.
  - Input scan (inputs / input_where), for feedback safety deliberately wider than the tap walk. A box counts at any depth of the raw JSON (p/patcher subpatchers and embedded bpatcher patchers included) when either:
    - its maxclass is in INPUT_BOXES;
    - it is a newobj whose first text token is in INPUT_BOXES.
    The scan follows every sibling .maxpat in the same directory that this patch references (via `_references`), transitively, with a visited set. input_where lists "file:box-id" hits.
- `check_argv(path, scan, opts) -> (argv, mode, reasons)`. argv is for `bridge.build_parser().parse_args`; mode is "record" or "load-only". Apply in order:
  - Base: ["check", str(path)], plus --port, --reply-port, --timeout, --settle and --load-timeout only when the user gave them. The wrapper's defaults are None, so the bridge parser keeps its own defaults.
  - Shot: "--shot" unless opts.no_shot is set or sys.platform != "darwin".
  - `audio_input_locked = scan["inputs"] and not opts.live_inputs`.
  - Record decision:
    - opts.record == 0 → load-only, reason "record disabled (--record 0)".
    - elif audio_input_locked → load-only, reason "record skipped: audio-input patch (feedback risk, no stimulus); --live-inputs opts in" (D-01).
    - elif not scan["tapped"] → load-only, reason "output not tapped (" + the unsupported names, or "no dac~/ezdac~ cord at the top level or in a p subpatcher", + ")".
    - else → mode record: "--record" with str(opts.record or DEFAULT_RECORD_S). When note_kind is set, add "--note" with P V from opts.note or DEFAULT_NOTE. `--note` only ever travels with `--record`.
  - D-02:
    - load-only and not audio_input_locked → append "--dsp-on-load", reason "DSP on during the load settle (restored afterwards)";
    - audio_input_locked → reason "DSP not switched on: audio-input patch (feedback safety); --live-inputs opts in";
    - record mode never gets --dsp-on-load, because recording already switches DSP on inside the listen window.
- `_max_running()`: True or False from `subprocess.run(["pgrep", "-x", "Max"], capture_output=True, timeout=5)` (return code 0 or 1), on darwin only. Return None when it cannot tell (another platform, pgrep missing, any error).
- `preflight(opts) -> str | None`. None means go. It never writes anything. Checks, in order:
  1. `not bridge.BRIDGE_PATCH.is_file()` → "bridge patch not available in this install (patches/ is not shipped in releases)".
  2. `_max_running() is False` → "MAX is not running: start MAX 9.2, open patches/max-bridge/generated/max-bridge.maxpat and turn ON its enable toggle". None does not skip.
  3. `with bridge.Bridge(bridge.HOST, port, reply_port, timeout) as b: b.ping(timeout)`, with each value taken from opts or else from bridge.BRIDGE_PORT / REPLY_PORT / DEFAULT_TIMEOUT. On bridge.BridgeError return `bridge._bridge_hint(bridge.HOST, port) + f" ({exc})"`. That hint already tells the user to turn the toggle ON; never do it for them (D-04).
- `map_findings(report) -> list[dict]`. Each item is {"severity", "finding", "suggestion", "source": "live"}. Never derive severity from report["exit_code"] or report["verdict"]: the bridge counts unsupported outputs and shot failures as findings. Rows (Task 3 writes the same table into severity-contract.md §7):
  1. An errors_distinct entry whose key passes `bridge._is_error_text` → blocker, finding `MAX console: {key} (x{occurrences})`. Suggestion by wording:
     - no such object → "use a name from the object DB (Rule #1; pd-blocklist.json for PD names); see troubleshooting.md";
     - bad argument → "check the argument form against the DB / refpage; see troubleshooting.md";
     - failed to compile / can't assign → "gen~ compile error: see genexpr-rules.md (Param/local name clash, declaration order)".
  2. Any other errors_distinct entry → warning. Suggestion: "runtime or environment error (missing file, port in use) or a post from another open patch: close unrelated patches and rerun".
  3. Record flags, from report["record"]["flags"] when record is present:
     - if {"sr_changed_during_run", "short_recording"} intersects the flags, EVERY flag becomes a note, with "(measures unreliable: the audio driver restarted or DSP stopped; rerun)" appended;
     - otherwise nonfinite and runaway → blocker, suggestion "NaN/inf or runaway output: check feedback gains and filter stability before it reaches speakers";
     - clipping → warning, "reduce the output gain below 1.0";
     - dc_offset → warning, "add a DC blocker before the dac~";
     - silent → warning, "needs a stimulus (start toggle, file load, note)?";
     - any other flag → warning.
  4. Notes:
     - each record["warnings"] entry whose prefix before ":" is not already a flag;
     - each report["warnings"] entry (dsp_state_unknown, a channel > 2 left untapped, `--note: no notein or kslider to drive`).
  5. Each report["unsupported"] entry → note `not tapped: {name} at {path}`. It is a coverage gap, never a defect.
  6. A report["shot"] with "error" → note. Suggestion: "grant Screen Recording to the terminal app (System Settings > Privacy & Security)".
  7. report["closed"] is False → warning "the temp copy's window may still be open in MAX", suggestion "close it WITHOUT saving".
  8. report["feedback_suspected"] → warning "event cap tripped (console flood): the error list may be incomplete".
- `run_live(patches, opts, *, project=None, excluded=None) -> dict`.
  - Result keys: status ("ran", "skipped" or "aborted"), hint, project, patches, excluded, notes, counts {blocker, warning, note}, reminder (REMINDER), exit_code.
  - Per-patch keys: patch (absolute), name, status ("checked", "skipped", "refused", "failed" or "not checked"), mode, argv, reasons, findings, shot_png, run_dir, record, dsp_before, verdict.
  - No patches → skipped, "no top-level .maxpat to check".
  - Run preflight next. A hint → skipped, with patches [], returned BEFORE any run_check, so no `__maxbridge_*` copy is ever written.
  - Loop strictly sequentially (one reply port, one sfrecord~). Print progress to stderr: "[i/n] name: mode (reasons)". Inside a per-patch try/except Exception: scan_patch, check_argv, `args = bridge.build_parser().parse_args(argv)`, `report = bridge.run_check(args)`. An exception gives status "failed" and the warning "live check crashed: {exc!r}", then the loop continues. KeyboardInterrupt propagates.
  - verdict "bridge_failed":
    - copy is None (guard_input refused) → status "refused", note with report["error"];
    - otherwise → run status "aborted", hint "MAX stopped answering during {name} ({error}): a modal dialog, a crash, or the enable toggle switched OFF". Every later patch gets status "not checked". Break; never spend --load-timeout on each remaining patch.
  - Otherwise status "checked", findings = map_findings(report). If audio_input_locked and report["dsp_before"] == 1, add the note "DSP was already on: the copy's audio input was live during the load", suggestion "switch DSP off before a live run, or pass --live-inputs deliberately".
  - Copy over: shot_png = report["shot"]["png"] when the shot has no error, plus run_dir, record, dsp_before and verdict.
  - counts are summed over all patch findings. exit_code: 2 when skipped or aborted; else 1 when blockers + warnings > 0; else 0.
- `main(argv=None) -> int`, argparse prog "max_verify_live.py":
  - positional PATCH* (nargs "*");
  - --record S (float, default None = DEFAULT_RECORD_S, 0 = never record);
  - --note P V (int; parser.error when the pitch is outside 0-127 or the velocity outside 1-127);
  - --no-shot, --live-inputs;
  - --settle, --load-timeout, --port, --reply-port, --timeout (all default None);
  - --json.
  - Explicit PATHs: a name starting with bridge.COPY_PREFIX, a non-.maxpat path or a missing file goes to excluded with a reason, and is not run.
  - With no PATH: print "no PATH given" to stderr and return 2. Task 2 replaces this branch with project resolution.
  - Print `json.dumps(result, indent=2, default=str)` to stdout. Task 2 adds the human format. Return result["exit_code"].

**Part C. tests/test_max_verify_live.py (new, hermetic).** It must never reach the real port 7400 or the real MAX.
- Imports: `import tools.max_bridge as bridge`, `import tools.max_verify_live as live`, and `from tests.test_max_bridge import FakeBridge, _tone_patch, _free_port`.
- Fixtures:
  - a module-scope `db` fixture (ObjectDatabase());
  - an autouse fixture that monkeypatches `live._max_running` to return True and `bridge.cg_windows` to return [];
  - an autouse fixture that monkeypatches `bridge._make_run_dir` to return a fresh tmp subdirectory per call (counter).
- Helper `_run(port, *paths, extra=(), capsys)`: calls live.main with the paths plus `--port {port} --reply-port 0 --timeout 1.0 --settle 0.1 --load-timeout 1.5 --no-shot --json`, plus `--record 0.2` unless extra overrides it. Returns (rc, json.loads(stdout)).
  - Every test passes `--reply-port 0`, so no test binds the real reply port 7401.
  - Every test passes an explicit `--port` (fb.port or `_free_port()`), so no test can reach a real bridge on 7400.
- Patch builders use the Patcher API plus `format_patch_text`, as `_tone_patch` does:
  - tone;
  - tone plus an unconnected notein;
  - tone plus a kslider;
  - an adc~ patch (adc~ → `*~ 0.2` → dac~);
  - a no-dac patch (cycle~ → `*~ 0.`).
  The reference tests write raw JSON dicts.
- Tests:
  - import identity: `live.bridge is sys.modules["tools.max_bridge"]`.
  - INPUT_BOXES: each name has a DB entry whose domain is not RNBO or Gen.
  - Option rules, via scan_patch plus check_argv with opts from live's parser:
    - tone + notein → record 3.0 s by default, with "--note", "60", "100", and no --dsp-on-load;
    - kslider → --note;
    - tone only → no --note;
    - adc~ → load-only, no --record, no --dsp-on-load, and a reason mentioning audio-input;
    - adc~ with --live-inputs → record;
    - no-dac → load-only with --dsp-on-load;
    - tone with --record 0 → load-only with --dsp-on-load;
    - --note 64 90 → "64", "90";
    - --no-shot → no --shot; with live.sys.platform monkeypatched, "darwin" gives --shot and "linux" does not;
    - every argv parses with bridge.build_parser(), and `.dsp_on_load` matches the expectation.
  - Input scan:
    - a parent whose bpatcher `name` is "child.maxpat", with child holding adc~ → inputs True;
    - a comment box whose text reads adc~ → inputs False.
  - map_findings: one test per table row, using synthetic report dicts built by a helper that has every key run_check sets.
    - Each bridge.ERROR_WORDINGS wording → blocker; a non-wording error → warning.
    - nonfinite and runaway → blocker; clipping, dc_offset and silent → warning.
    - short_recording present → every flag a note.
    - unsupported with exit_code 1 and verdict "findings" → notes only.
    - shot error → note; closed False → warning; feedback_suspected → warning.
    - Every row has source "live".
  - Skip:
    - nothing listening on a `_free_port()` port with --timeout 0.3 → rc 2, status skipped, a hint containing "toggle", a monkeypatched spy on bridge.run_check never called, and no `__maxbridge_*` file under tmp_path;
    - `_max_running` returning False → a hint starting "MAX is not running", and a started FakeBridge receives nothing;
    - bridge.BRIDGE_PATCH monkeypatched to a missing path → "not available in this install".
  - Run:
    - FakeBridge(errors=True) + tone → rc 1, one blocker containing "No such object", the original's bytes unchanged, no copy left;
    - FakeBridge() + tone → rc 0, mode record, record present.
  - D-02 end to end:
    - FakeBridge(dsp_on=0) + no-dac → `("/dsp", [1])` before "/open" and `("/dsp", [0])` after, fb.dsp_on 0;
    - FakeBridge(dsp_on=1) + no-dac → no `("/dsp", [0])`, fb.dsp_on 1;
    - FakeBridge(dsp_on=0) + adc~ → `("/dsp", [1])` never received and no "/sf";
    - FakeBridge(dsp_on=1) + adc~ → the "DSP was already on" note.
  - Abort: FakeBridge(mute_after_open=True) with two tone patches → rc 2, status aborted, the second patch "not checked", and `fb.addresses.count("/open") == 1`.
  - Crash: bridge.run_check monkeypatched to raise RuntimeError on the first call and delegate to the real one afterwards → the first patch is "failed" with a warning, the second is "checked".
  - D-04 AST guard: `ast.parse` tools/max_verify_live.py. Assert:
    - no Call whose func is an Attribute named `send`;
    - no str Constant exactly equal to "open", "osascript", "/dsp" or "/listen".
    Comments are invisible to ast, and docstrings never equal those exact strings.

Commit only these four paths with `git add <paths>`, never `git add .` and never `git stash`. Message: `feat(tools): max_verify_live tracer + max_bridge check --dsp-on-load (quick 261021-olv)`.
  </action>
  <verify>
    <automated>python3 -m pytest tests/test_max_bridge.py tests/test_max_verify_live.py -q -p no:cacheprovider && python3 tools/max_bridge.py check patches/max-bridge/fixtures/fx-clean.maxpat --dsp-on-load --dry-run | python3 -c "import sys; L=[l.strip() for l in sys.stdin]; i=next(k for k,l in enumerate(L) if l.startswith('/open ')); assert L[i-1]=='/dsp 1', L" && test -z "$(python3 tools/max_bridge.py check patches/max-bridge/fixtures/fx-clean.maxpat --dry-run | grep -x '/dsp 1')" && python3 tools/max_verify_live.py patches/max-bridge/fixtures/fx-clean.maxpat --port 7409 --reply-port 0 --timeout 0.5 --json | python3 -c "import sys,json; r=json.load(sys.stdin); assert r['status']=='skipped' and r['exit_code']==2 and r['patches']==[], r" && test -z "$(find patches -name '__maxbridge_*')" && git diff --quiet HEAD -- patches/max-bridge/generated/max-bridge.maxpat</automated>
  </verify>
  <done>
- `check --dsp-on-load` places /dsp 1 immediately before the opener, and the existing restore rule handles it (FakeBridge tests for DSP off, DSP on, unknown and a muted bridge).
- The flagless plan is unchanged, and all 124 pre-existing bridge tests pass unedited.
- `max_verify_live.py PATCH --json` checks a patch end to end on FakeBridge with the D-01/D-02 option rules and the §7 mapping, and skips with exit 2 and no temp copy when the bridge does not answer.
- The D-04 AST guard passes. Four paths are committed.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: The project-level CLI (active project, top-level selection, open-original skip, human report) and the max-bridge v0.3.0 records</name>
  <files>tools/max_verify_live.py, tests/test_max_verify_live.py, patches/max-bridge/context.md, patches/max-bridge/status.md, patches/max-bridge/versions.json</files>
  <read_first>
    - tools/max_verify_live.py and tests/test_max_verify_live.py (as Task 1 left them)
    - src/maxpat/project.py lines 95-200 (get_active_project, update_status) and 272-322 (bump_version)
    - tools/max_bridge.py lines 705-760 (ShotError, cg_windows, _find_window)
    - patches/max-bridge/context.md (the whole file; its sections: Purpose, Pieces, Protocol, Kill switch, DSP state, Temp-copy policy, LAN caveat, Exit codes)
  </read_first>
  <behavior>
    - Selection:
      - find_top_level_patches drops a bpatcher child, a poly~ child, an mc.poly~ child, a pfft~ child, a newobj abstraction and `__maxbridge_x.maxpat`;
      - a comment whose text names a sibling does not exclude it, and a file referencing its own stem stays a top-level;
      - excluded reasons read "abstraction of <parent, ...>";
      - for the real repo, read-only: find_top_level_patches(patches/terrain-synth/generated) → [terrain-synth.maxpat].
    - Resolution:
      - no PATH, no --project and get_active_project → None gives rc 2 and a hint containing "no active project";
      - --project "../x" gives rc 2;
      - --project together with a PATH gives SystemExit 2;
      - with --project demo against a tmp REPO_ROOT (patches/demo/generated holding parent.maxpat with a bpatcher of child.maxpat), only parent is opened on FakeBridge (`fb.addresses.count("/open") == 1`, and the opened path ends `__maxbridge_parent.maxpat`), and result["excluded"] lists child.
    - Open original (live.sys.platform monkeypatched to "darwin"):
      - cg_windows returning a row titled "tone" (also "tone (presentation)", "tone*" and "tone.maxpat") gives status skipped with the note "original is open in MAX", and no "/open" is sent;
      - cg_windows raising bridge.ShotError gives a run-level note, and the patch still runs.
    - format_report:
      - a ran result shows "Live check (MAX 9.2)", the per-patch "LIVE BLOCKER:" / "LIVE WARNING:" / "LIVE NOTE:" lines, "Live: b blockers, w warnings, n notes" and REMINDER;
      - a skipped result shows "Live check skipped: <hint>";
      - main without --json prints format_report.
  </behavior>
  <action>
Write the behavior tests first (RED), then implement (GREEN). Commit both steps.

- `find_top_level_patches(generated: Path) -> (tops, excluded)`:
  - Take `sorted(generated.glob("*.maxpat"))`, non-recursive.
  - A name starting with bridge.COPY_PREFIX → excluded "bridge temp copy".
  - Parse each remaining sibling's JSON. An unreadable file stays a top-level candidate; its per-patch run then reports the failure as a warning.
  - refs = `_references(json, stems)` minus the file's own stem. A stem referenced by any other sibling is a child, excluded as {"patch": filename, "reason": "abstraction of " + sorted parent stems joined by ", "}.
- Patch resolution in main, replacing Task 1's no-PATH branch:
  - Explicit PATHs work as in Task 1, with no sibling filtering.
  - --project NAME: it must be a single path component with no "/" or "\\", not "." or "..". REPO_ROOT/patches/NAME/generated must exist; otherwise return 2 with a hint. It never writes patches/.active-project.json.
  - Otherwise use `get_active_project(REPO_ROOT)["name"]`. Import get_active_project into the module namespace, and read the module-level REPO_ROOT at call time, so tests can monkeypatch both. None → return 2 with "no active project: run /max-switch, or pass --project NAME or PATH".
  - Passing --project and PATHs together → parser.error.
  - If tops is empty but candidates exist → skipped "every .maxpat in {dir} is referenced by a sibling: pass explicit PATHs".
  - Pass project and excluded through to run_live.
- Open originals (RESEARCH Pitfall 1). After a good preflight, and only on darwin, call `bridge.cg_windows()` once.
  - On bridge.ShotError, OSError or subprocess.SubprocessError: add the run-level note "could not list MAX windows ({exc}): close any open original by hand" and continue.
  - Normalise each title by stripping whitespace, then a trailing "*", then a trailing " (presentation)".
  - A patch whose stem equals a normalised title, or whose `stem + ".maxpat"` does, is not run:
    - status "skipped";
    - note "original is open in MAX (shared send/receive/buffer~ names and udpreceive ports would collide)";
    - suggestion "close it (save first if it has edits) and rerun".
  - Never close or touch the user's window.
- `format_report(result) -> str`, the text the command doc shows:
  - Line 1: "Live check (MAX 9.2): {project or f'{n} patch(es)'}", then an "=" underline.
  - skipped → "Live check skipped: {hint}"; aborted → "Live check aborted: {hint}", plus the not-checked names.
  - Per patch, a header "{name}  [{status}; {mode}: {reasons joined by '; '}]", then:
    - "  LIVE BLOCKER: {finding} -- Fix: {suggestion}"
    - "  LIVE WARNING: {finding} -- {suggestion}"
    - "  LIVE NOTE: {finding}"
    - "  shot: {png}" and "  run dir: {run_dir}" when present.
  - Then "Excluded: {name} ({reason})" lines and the run-level notes.
  - Then "Live: {b} blockers, {w} warnings, {n} notes ({checked} checked, {not_run} not run)".
  - Last line: REMINDER.
  - main prints format_report unless --json is given.
- Bridge project records (no patch file changes):
  - Run `bump_version(Path("patches/max-bridge"), "minor", "v0.3.0: /max-verify --live (tools/max_verify_live.py) and check --dsp-on-load")`; the new last version must be 0.3.0.
  - Run `update_status(Path("patches/max-bridge"), progress="v0.3.0 built (/max-verify --live, check --dsp-on-load), pending manual test; v0.1.0 and v0.2.0 confirmed 2026-10-21")`.
  - patches/max-bridge/context.md:
    - replace the line-3 status paragraph with: v0.1.0 and v0.2.0 confirmed in MAX 9.2 (2026-10-21, dc0cde91); v0.3.0 adds `check --dsp-on-load` and tools/max_verify_live.py (`/max-verify --live`), pending test-results/v0.3.0-verify-live-checklist.md; quick 261021-olv;
    - add tools/max_verify_live.py and tests/test_max_verify_live.py to "Pieces";
    - add a "## /max-verify --live (v0.3.0)" section covering: the top-level selection rule; the option rules (D-01 audio-input load-only, D-02 DSP on during the load settle except locked audio-input patches); the pointer to severity-contract.md §7 for severities; sequential runs and abort on the first bridge_failed; the open-original skip; the toggle and the bridge patch stay the user's (D-04); the 0/1/2 exit codes. Also add those exit codes to the "Exit codes" section.

Commit only these five paths. Message: `feat(tools): max_verify_live project mode, top-level selection, report; max-bridge v0.3.0 (quick 261021-olv)`.
  </action>
  <verify>
    <automated>python3 -m pytest tests/test_max_verify_live.py tests/test_max_bridge.py -q -p no:cacheprovider && python3 -c "from pathlib import Path; from tools.max_verify_live import find_top_level_patches as f; t,e=f(Path('patches/terrain-synth/generated')); assert [p.name for p in t]==['terrain-synth.maxpat'], t; assert {x['patch'] for x in e}=={'terrain-voice.maxpat','terrain-osc.maxpat','terrain-osc-b.maxpat','terrain-lfo.maxpat','terrain-cheby.maxpat'}, e" && python3 tools/max_verify_live.py --project simple-fm --port 7409 --reply-port 0 --timeout 0.5 | grep -q "Live check skipped" && python3 -c "import json;assert json.load(open('patches/max-bridge/versions.json'))['versions'][-1]['version']=='0.3.0'" && grep -q "## /max-verify --live" patches/max-bridge/context.md && test -z "$(find patches -name '__maxbridge_*')" && test -z "$(git status --porcelain patches/simple-fm patches/terrain-synth)" && cmp -s patches/.active-project.json .planning/quick/261021-olv-max-verify-live-mode-via-max-bridge/active-project-before.json</automated>
  </verify>
  <done>
- The project mode resolves the active project (or --project) to its top-level patches only.
- Open originals are skipped, never closed.
- The human report matches the shape in the command doc.
- max-bridge is at v0.3.0 in versions.json, status.md and context.md.
- Five paths are committed, and every test in both files passes.
  </done>
</task>

<task type="auto">
  <name>Task 3: /max-verify --live in the command doc, severity-contract §7, the v0.3.0 manual checklist, doc guards and the full-suite gate</name>
  <files>.claude/commands/max-verify.md, .claude/skills/references/severity-contract.md, patches/max-bridge/test-results/v0.3.0-verify-live-checklist.md, tests/test_max_verify_live.py</files>
  <read_first>
    - .claude/commands/max-verify.md and .claude/skills/references/severity-contract.md (both whole)
    - patches/max-bridge/test-results/v0.2.0-bridge-checklist.md (the format: numbered steps with [ ] status, Expect and Result lines, V-questions citing steps)
    - tools/max_verify_live.py (map_findings, format_report, the CLI flags) as Tasks 1-2 left it
  </read_first>
  <action>
**.claude/commands/max-verify.md.** Keep steps 1-6, the three existing import lines, "review_patch" and the existing Output Format block verbatim.

- Add step 7, "Live check (opt-in, `--live`)". It runs only after steps 3-5 have printed the static report.
  - Command: `python3 tools/max_verify_live.py --json` plus the pass-through flags. Give no PATH: the tool reads the same active-project pointer and drops abstractions and bpatcher children that a sibling references.
  - Exit 0 or 1 → append a "Live check (MAX 9.2):" section built from the JSON:
    - per patch, the LIVE BLOCKER / LIVE WARNING / LIVE NOTE lines with their suggestions, the shot path and the run dir;
    - optionally Read each shot PNG to eyeball the layout, and flag visual issues.
  - Exit 2 → one line: "live check skipped: <hint>", or "live check aborted: <hint>" with the not-checked patches. The static report and its counts stay exactly as they were.
  - Live findings are report-only (severity-contract.md §7): never feed them into the critic revision loop, never change step 6's status record from them, and never auto-fix. Offer /max-iterate.
- Add a "Live check safety" list:
  - turn the volume down;
  - close the originals of the project's patches (the tool skips an open original) and any unrelated patch: console posts from other open patches are attributed to the patch under test;
  - the bridge patch must already be open with its enable toggle ON. That is the user's job: never toggle it or open the bridge patch for them (D-04). Afterwards, remind the user to turn the toggle OFF;
  - recorded patches switch DSP on only for the recording. Load-only patches get DSP on during the load settle so gen~ compile errors post, and the prior DSP state is restored (D-02);
  - audio-input patches stay load-only with DSP untouched unless --live-inputs (D-01). If DSP is already on, their input is live, so switch DSP off first;
  - Ctrl-C mid-run skips the bridge's cleanup: DSP may stay on and a `__maxbridge_` window may stay open. Close that window without saving.
- Arguments: keep "None required. Verifies all generated files in the active project." and add these flags:
  - `--live`;
  - `--record S` (default 3; 0 = never record);
  - `--note P V` (default 60 100; played into notein, or else the first kslider, while recording);
  - `--no-shot`;
  - `--live-inputs` (records audio-input patches and allows DSP-on-load for them: mute mics or use headphones).
- Python Modules: add a line "Live (CLI): python3 tools/max_verify_live.py [--json] [--record S] [--note P V] [--no-shot] [--live-inputs]".
- Examples: add `/max-verify --live`, `/max-verify --live --record 0 --no-shot` and `/max-verify --live --live-inputs`.
- Output Format: add a second block showing the live section, matching format_report's lines. Its Summary line is `Summary: {blockers} blockers, {warnings} warnings, {notes} notes   (live: {lb} blockers, {lw} warnings, {ln} notes)`, with the alternatives `(live check skipped: {hint})` and `(live check aborted: {hint})`. Add the sentence: live counts sit beside the static counts and are never added to them (D-03).

**.claude/skills/references/severity-contract.md.** Sections 1-6 stay unchanged.
- Line 3: append "Section 7 (live findings) was checked against `tools/max_verify_live.py`."
- Add "## 7. Live findings (`/max-verify --live`)", containing:
  - Opening: the findings come from `tools/max_verify_live.py`, which maps `tools/max_bridge.py check` reports. They are report-only and never part of the save gate (section 5) or the critic revision loop (section 4). The bridge's own exit_code/verdict is not the severity.
  - The table, row for row as map_findings, naming the actual keys and flags:
    - the four ERROR_WORDINGS (no such object, bad argument, failed to compile, can't assign) → blocker;
    - other console errors → warning;
    - nonfinite / runaway → blocker;
    - clipping / dc_offset / silent → warning;
    - sr_changed_during_run / short_recording → note, and every other record flag of that patch demoted to note;
    - record warnings and report warnings (sr_header_mismatch, dsp_state_unknown) → note;
    - unsupported (mc.dac~, plugout~, poly~, pfft~, bpatcher) → note;
    - shot error → note;
    - closed False → warning;
    - feedback_suspected → warning;
    - DSP already on for a locked audio-input patch → note;
    - original open → note (patch skipped);
    - crashed → warning;
    - refused → note;
    - bridge_failed after a good pre-flight → run aborted.
  - Exit codes 0/1/2.
  - The Summary rule (D-03).
  - A closing line: a live blocker is MAX confirming what a validator error predicts; fix it through /max-iterate, then rerun.

**patches/max-bridge/test-results/v0.3.0-verify-live-checklist.md (new).** Same format as the v0.2.0 checklist: each step has [ ] status, Expect and "Result: pending" lines, and every command runs from the repo root.
- Step 0, setup:
  - volume down;
  - close the originals of the patches under test and any unrelated patch;
  - open patches/max-bridge/generated/max-bridge.maxpat; the toggle starts OFF.
- Step 1, toggle OFF:
  - `/max-verify --live` on the active project → the static report is intact, then "live check skipped" with the toggle hint;
  - `python3 tools/max_verify_live.py --project simple-fm; echo $?` → 2.
- Step 2, toggle ON and DSP OFF: `python3 tools/max_verify_live.py --project simple-fm`
  - Expect: record 3 s with note 60 100, a shot path, DSP OFF afterwards, exit 0;
  - Read the shot.
- Step 3, blockers and warnings: `python3 tools/max_verify_live.py patches/max-bridge/fixtures/fx-nosuchobj.maxpat patches/max-bridge/fixtures/fx-dc.maxpat`
  - Expect: a LIVE BLOCKER for no such object, and a dc_offset LIVE WARNING for fx-dc.
- Step 4, D-02, with DSP OFF: `python3 tools/max_verify_live.py patches/max-bridge/fixtures/fx-genfail.maxpat --record 0`
  - Expect: load-only with DSP on during the load; LIVE BLOCKERs for can't assign and failed to compile; DSP OFF again afterwards;
  - Repeat with DSP ON beforehand → DSP stays ON.
- Step 5, D-01 with an audio-input project:
  - Pick it by running scan_patch over patches/amplitude-follower/generated/amplitude-follower.maxpat and confirm inputs True before naming it in the step. If it is False, pick another project from the planning survey list (barnett-dbap via dbap-source, gen-eq, disintegrate) and confirm the same way.
  - With DSP OFF, `python3 tools/max_verify_live.py --project <it>` → load-only, MAX's DSP indicator never turns on.
  - Then with mics muted or headphones on, `... --live-inputs` → recorded.
- Step 6, open original: open patches/simple-fm/generated/simple-fm.maxpat in MAX and rerun step 2 → skipped with the "original is open" note.
  - Then make an unsaved edit and rerun, to record the title form.
  - Close the original without saving.
- Step 7, abort: `python3 tools/max_verify_live.py patches/max-bridge/fixtures/fx-clean.maxpat patches/max-bridge/fixtures/fx-dc.maxpat patches/max-bridge/fixtures/fx-badargs.maxpat --record 5`. Switch the toggle OFF during the first recording.
  - Expect: aborted, later patches "not checked", exit 2;
  - then no `__maxbridge_` window open, DSP back as before, and `find patches -name '__maxbridge_*'` prints nothing.
- Step 8, cleanup: toggle OFF or close the bridge.
- V-questions, each citing its step:
  - W1: does DSP-on-load surface fx-genfail's failed to compile lines with DSP off beforehand? (step 4)
  - W2: the MAX window title form of an open original, saved and with unsaved edits (RESEARCH A4)? (step 6)
  - W3: the seconds per patch, load-only versus record (A5)? (steps 2-4)
  - W4: does a toggle-OFF mid-batch abort within one load-timeout? (step 7)

**Doc guards (append to tests/test_max_verify_live.py):**
- max-verify.md contains: `from src.maxpat import`, `review_patch`, `--live`, `tools/max_verify_live.py`, `--live-inputs`, `(live:`, `live check skipped`, `LIVE BLOCKER`.
- severity-contract.md contains "## 7. Live findings" and "max_verify_live". Its section-7 text (from that heading to the end of the file) contains every bridge.ERROR_WORDINGS entry and every flag name: nonfinite, runaway, clipping, dc_offset, silent, sr_changed_during_run, short_recording.
- The v0.3.0 checklist exists and mentions fx-genfail, --live-inputs and aborted.
- format_report's first line starts with "Live check (MAX 9.2)", the same title the doc uses.

**Final gate:**
- `python3 -m pytest -q -p no:cacheprovider --junitxml=QDIR/final-junit.xml`
- `python3 QDIR/junit_diff.py QDIR/baseline-junit.xml QDIR/final-junit.xml` must exit 0.
- `git stash list` must equal QDIR/stash-list-before.txt, and `find patches -name '__maxbridge_*'` must print nothing.

Commit only the four task paths. Message: `docs(max-verify): --live mode, severity-contract §7, max-bridge v0.3.0 checklist (quick 261021-olv)`.
  </action>
  <verify>
    <automated>python3 -m pytest tests/test_max_verify_live.py tests/test_commands.py tests/test_agent_skills.py tests/test_claude_md.py -q -p no:cacheprovider && grep -q "## 7. Live findings" .claude/skills/references/severity-contract.md && grep -q "tools/max_verify_live.py" .claude/commands/max-verify.md && test -f patches/max-bridge/test-results/v0.3.0-verify-live-checklist.md && { python3 -m pytest -q -p no:cacheprovider --junitxml=.planning/quick/261021-olv-max-verify-live-mode-via-max-bridge/final-junit.xml >/dev/null || true; } && python3 .planning/quick/261021-olv-max-verify-live-mode-via-max-bridge/junit_diff.py .planning/quick/261021-olv-max-verify-live-mode-via-max-bridge/baseline-junit.xml .planning/quick/261021-olv-max-verify-live-mode-via-max-bridge/final-junit.xml && diff <(git stash list) .planning/quick/261021-olv-max-verify-live-mode-via-max-bridge/stash-list-before.txt && test -z "$(find patches -name '__maxbridge_*')"</automated>
  </verify>
  <done>
- /max-verify documents --live with its flags, safety notes, output block and the beside-not-merged Summary suffix.
- severity-contract.md §7 states the same table map_findings implements, and the doc guards pin it.
- The v0.3.0 manual checklist exists.
- The full-suite junit diff against the Step 0 baseline is clean, the stash list is unchanged, and no temp copies are left. Four paths are committed.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Python -> MAX (UDP 7400) | Every command that reaches MAX goes through bridge.run_check or Bridge.ping. The bridge patch listens on all interfaces (LAN caveat, unchanged). |
| Repo patch -> temp copy | run_check writes `__maxbridge_<stem>.maxpat` beside the original and deletes it in a finally block. The user's original must never change. |
| Audio input -> speakers | A loaded copy with adc~ and DSP on can feed back. |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-olv-01 | Elevation of privilege | kill switch / bridge patch | high | mitigate | D-04: the wrapper never toggles the switch and never opens the bridge patch. The Task 1 AST guard forbids `.send` calls and the `open`/`osascript`/`/dsp`/`/listen` constants. The skip hint tells the user what to do. |
| T-olv-02 | Tampering | the user's original .maxpat | high | mitigate | Only run_check writes, and only the guarded `__maxbridge_` sibling. Tests assert the original's bytes are unchanged and no copy is left. An open original is skipped, never closed. Step 0 and the final gate check that `find patches -name '__maxbridge_*'` is empty. |
| T-olv-03 | Denial of service (physical: feedback / speaker damage) | adc~ patches, DSP | high | mitigate | D-01/D-02: an audio-input patch is load-only and gets no --dsp-on-load unless --live-inputs. The input scan follows referenced siblings and embedded bpatchers. There is a note when DSP was already on. nonfinite/runaway is a blocker. The doc warns to turn the volume down. |
| T-olv-04 | Information disclosure / Spoofing | UDP 7400 on all interfaces | medium | mitigate | No new address is added. Every report ends with REMINDER (toggle OFF / close the bridge). The client still binds 127.0.0.1 only. |
| T-olv-05 | Repudiation (false "clean") | static vs live results | medium | mitigate | A skip or abort exits 2 with a hint. The static Summary counts are never altered (D-03). Severity comes from map_findings, not the bridge verdict. |
| T-olv-06 | Denial of service | modal dialog / crash mid-batch | medium | mitigate | Abort on the first bridge_failed, without spending a load-timeout on each remaining patch. A per-patch exception becomes a warning. |
| T-olv-07 | Tampering (MAX state) | DSP left on by --dsp-on-load | medium | mitigate | The existing restore slot and BridgeError cleanup are reused unchanged, and FakeBridge tests cover off/on/unknown/muted. Ctrl-C is documented as skipping the cleanup (accepted). |
| T-olv-SC | Tampering | npm/pip/cargo installs | high | mitigate | No packages are installed. The wrapper is stdlib plus in-repo; numpy and scipy are already declared and are only used inside max_bridge. |
</threat_model>

<verification>
- `python3 -m pytest tests/test_max_bridge.py tests/test_max_verify_live.py -q -p no:cacheprovider` passes. The 124 pre-existing bridge tests are unedited.
- The dry-run plan with --dsp-on-load has "/dsp 1" right before "/open ..."; without the flag the plan has no "/dsp 1" line.
- `python3 tools/max_verify_live.py --project simple-fm --port 7409 --reply-port 0 --timeout 0.5` prints "Live check skipped" and writes no temp copy.
- find_top_level_patches on terrain-synth returns only terrain-synth.maxpat.
- `python3 QDIR/junit_diff.py QDIR/baseline-junit.xml QDIR/final-junit.xml` exits 0, the stash list is unchanged, and no `__maxbridge_*` files remain.
- MAX confirmation is the user's: patches/max-bridge/test-results/v0.3.0-verify-live-checklist.md.
</verification>

<success_criteria>
- `/max-verify --live` is documented and runnable: after the unchanged static report it appends a live section, or one "live check skipped/aborted: <hint>" line, with live counts beside the static Summary (D-03).
- D-01, D-02 and D-04 are implemented and pinned by hermetic tests. The only bridge logic change is the opt-in --dsp-on-load.
- severity-contract.md §7 and map_findings agree, pinned by doc guards.
- max-bridge is at v0.3.0 with a pending manual checklist. The full-suite junit gate is clean.
</success_criteria>

<output>
Create `.planning/quick/261021-olv-max-verify-live-mode-via-max-bridge/261021-olv-SUMMARY.md` when done.
</output>
