# Quick 261021-olv: /max-verify --live via max-bridge - Research

**Researched:** 2026-10-21
**Domain:** in-repo integration (Python tool + Markdown command doc). No new packages.
**Confidence:** HIGH for the code facts (all read this session), MEDIUM for the severity mapping and per-patch defaults (design calls, flagged in the Assumptions Log)

<user_constraints>
## User Constraints

There is no CONTEXT.md (quick task). The constraints come from the task brief and the confirmed bridge record:
- `--live` is **opt-in**. It runs **after** static validation and the critics, and it must **never fail static verification**: when the bridge is unusable, the report says `live check skipped: <hint>`.
- **The kill switch stays user-controlled.** Never toggle it, and never open the bridge patch programmatically (user decision N1, `patches/max-bridge/open-questions.md`).
- Use only the confirmed bridge (v0.1.0 and v0.2.0 checklists, both all-pass 2026-10-21, commit dc0cde91).
- The project rules apply: Rule #7 (no `git add .`, commit only in-project paths), no generator scripts, and the frustration directive "never modify working functionality". `tools/max_bridge.py` is confirmed in MAX, so treat it as frozen apart from docstring text.
</user_constraints>

## Summary

`/max-verify` has no Python entry point. `.claude/commands/max-verify.md` is a prose recipe the agent follows (`validate_file`, `validate_code_file`, `review_patch`, `update_status`). The bridge already exposes everything `--live` needs in-process: `run_check(args) -> dict` returns the full JSON report and never prints [VERIFIED: tools/max_bridge.py:1242-1339]. The work is therefore a **thin orchestrator CLI, `tools/max_verify_live.py`**. It does five things:
1. resolves the patches;
2. pre-flights the bridge once;
3. picks the record, note and shot options for each patch;
4. calls `bridge.run_check` sequentially;
5. maps each report to blocker, warning or note.

The command doc then gains a `--live` step that runs the CLI and appends its JSON to the report.

Three facts drive the design:
- **The bridge's own `exit_code` and `verdict` are unusable as the severity.** `findings` counts `unsupported` outputs (poly~, bpatcher, mc.dac~), `no_output_tap` and shot failures as findings [VERIFIED: tools/max_bridge.py:1331-1339]. A clean poly~ synth would therefore come back "findings". The wrapper must map fields itself.
- **`run_check` writes the sibling temp copy before it contacts the bridge** (`copy, inst = instrument(src, note=bool(note))` at :1260, before `Bridge(...)`). With the bridge down, each patch costs a copy write and delete plus a 2 s timeout. So run **one pre-flight `Bridge.ping()`** and skip everything if it fails.
- **Patch selection needs a sibling-reference scan.** I surveyed all 33 projects' `generated/` folders this session. Abstractions and bpatcher children (e.g. `terrain-voice`, `slot`, `wormhole`, `mixer-strip`, `slice-voice`) are exactly the `.maxpat` files that another sibling references as a bpatcher `name`, as a `newobj` first token, or as a `poly~`/`mc.poly~`/`pfft~` argument. Only `newobj` boxes may count, never comments: comment text like "FDNVerb v0.2.0" otherwise self-matches. Self-references are excluded.

**Primary recommendation:** add `tools/max_verify_live.py`, which imports `tools.max_bridge` in-process, makes no edits to `max_bridge.py` logic, has exit codes 0/1/2, and outputs JSON. Write the mapping table into `severity-contract.md` as a new §7. Test it in `tests/test_max_verify_live.py`, reusing `FakeBridge` and `_tone_patch` by importing them from `tests.test_max_bridge` (the house convention).

## Architectural Responsibility Map

| Capability | Owner | Notes |
|---|---|---|
| Static validation and critics | `src.maxpat` (`validate_file`, `review_patch`) | unchanged |
| Patch selection, pre-flight, option choice, severity mapping | **new `tools/max_verify_live.py`** | the tools tier, beside the bridge; `src/` never imports `tools/` today (grep), so keep it that way |
| Load, record, shot, close of one patch | `tools/max_bridge.run_check` | frozen and confirmed |
| Report composition (static + live) | `.claude/commands/max-verify.md` (agent) | a live section is appended, and the static summary is never altered |
| Severity semantics | `.claude/skills/references/severity-contract.md` §7 (new) | the single home, per CLAUDE.md |

## Standard Stack

No new dependencies. `tools/max_bridge.py` is stdlib plus numpy and scipy, which are already declared and present (numpy 2.4.0, scipy 1.17.0, Python 3.14.2, probed). The wrapper should be stdlib only. **Package Legitimacy Audit:** not applicable, because no packages are installed.

## Architecture Patterns

### Data flow
```
/max-verify --live
  -> static: validate_file / validate_code_file / review_patch   (report printed first, unchanged)
  -> python3 tools/max_verify_live.py [--project NAME] [opts] --json
       resolve: active project (src.maxpat.project.get_active_project(REPO_ROOT)) -> generated/*.maxpat
                -> drop __maxbridge_* and sibling-referenced children -> top-levels
       preflight (once): platform darwin? bridge.BRIDGE_PATCH exists? `pgrep -x Max`?
                -> Bridge(...).ping()   (BridgeTimeout => bridge closed OR kill switch OFF)
                -> any failure: {"status":"skipped","hint":...}, exit 2, NO copies written
       originals open? bridge.cg_windows() titles == stem / "stem (presentation)" -> skip that patch (note)
       for each top-level, SEQUENTIALLY:
           scan -> opts (record/note/shot) -> args = bridge.build_parser().parse_args(["check", path, ...])
           report = bridge.run_check(args)          (catch Exception per patch -> warning, continue)
           report["verdict"] == "bridge_failed" -> status "aborted", stop the loop (MAX stopped answering)
           map_findings(report) -> [{severity, finding, suggestion, source:"live"}]
       -> JSON {status, hint, patches:[{patch, options, findings, shot_png, run_dir, record_summary}], counts}
  -> agent appends a "Live check (MAX)" section and adds live counts to the Summary line
```

### Wrapper API (proposed names)
```python
# tools/max_verify_live.py
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path: sys.path.insert(0, str(REPO_ROOT))
from tools import max_bridge as bridge   # NOT `import max_bridge` (see Pitfall 6)

def find_top_level_patches(generated: Path) -> tuple[list[Path], list[dict]]   # (tops, [{patch, reason:"abstraction of X"}])
def scan_patch(path: Path) -> dict      # {outputs: bool, inputs: bool, note: "notein"|"kslider"|None, mc_or_plugin: [...]}
def check_argv(path, scan, opts) -> list[str]
def preflight(opts) -> str | None        # None = ok, else the skip hint
def map_findings(report: dict) -> list[dict]
def run_live(paths: list[Path], opts) -> dict
def main(argv=None) -> int               # 0 clean/notes-only, 1 live blocker|warning, 2 skipped|aborted|usage
```
- `scan_patch` must use the **same rules the bridge taps by**. Walk with `bridge._walk_patchers(p, "top")`, which goes through the top level and embedded `p`/`patcher` and skips bpatchers [VERIFIED: tools/max_bridge.py:437-446]. Output boxes are `OUTPUT_BOXES = ("dac~", "ezdac~")` and the unsupported ones `UNSUPPORTED_OUTPUTS = ("mc.dac~", "plugout~", "poly~", "pfft~")` [VERIFIED: tools/max_bridge.py:349-350]. Use these names as constants, never retyped.
- Build args with `bridge.build_parser().parse_args(["check", str(path), *flags])`, so every default (`--settle` 3.0, `--load-timeout` 30.0, `--shot` const `""`) stays with the bridge [VERIFIED: tools/max_bridge.py:1376-1390]. **`main()` validates `--note`, not `run_check`**, so the wrapper must itself pass `--note` only together with `--record` (the "--note needs --record" check lives in `main` only).

### Per-patch option rules (auto, all overridable)
| Condition (from `scan_patch`) | Options |
|---|---|
| a tapped `dac~`/`ezdac~` at the top level or in a `p` subpatcher, and no `adc~`/`ezadc~`/`mc.adc~` | `--record 3` (as in checklist steps 4 and 6) |
| …and a `notein` (else a `kslider`) anywhere in the walk | add `--note 60 100` (note-off at 75 % of the record by default; the checklist confirmed that simple-fm sounds and releases) |
| audio-input patch (`adc~`/`ezadc~`; **18 of the generated patches**, survey) | load-only by default; note "record skipped: audio-input patch (feedback risk, no stimulus)". `--live-inputs` opts in |
| only `mc.dac~`/`plugout~` output, or the output sits inside a bpatcher (e.g. `mixer.maxpat`, where the dac lives in `mixer-master` via bpatcher) | load-only; note "output not tapped" |
| every patch | `--shot`, unless `--no-shot` or not darwin |
`--record 0` disables recording everywhere, and `--note P V` overrides the pitch and velocity.

## Severity mapping (proposed severity-contract.md §7)

Live findings are **report-only**. They never enter the save gate (§5) or the critic loop (§4). They use the critic vocabulary so `/max-verify` can merge the counts.

| Live finding (report field) | Severity | Rationale (contract text) |
|---|---|---|
| `errors_distinct[].key` containing one of `ERROR_WORDINGS = ("no such object", "bad argument", "failed to compile", "can't assign")` [VERIFIED: tools/max_bridge.py:822] | **blocker** | §2: validator `error` = "Will not load or will misbehave in MAX". MAX's own console says exactly this; it is the ground truth that the static `error` only predicts. Suggest the fix from `troubleshooting.md`. |
| any other `errors_distinct` entry | warning | §2: `warning` = "Suspect but loadable". These are runtime or environment errors (missing sample file, `udpreceive` port in use, a post from another open patch). |
| `record.flags` `nonfinite` / `runaway` (peak > `runaway_amplitude: float = 10.0` [VERIFIED: src/maxpat/dsp_sim/measure.py:74]) | **blocker** | §4: blocker = "The generator fixes it". NaN/inf and runaway output are definite DSP defects, and dangerous at the speaker. |
| `record.flags` `clipping` / `dc_offset` / `silent` | warning | loadable but audibly wrong. For `silent`, suggest "needs a stimulus (start toggle, file load)?" |
| `record.flags` `sr_changed_during_run` / `short_recording` | note, **and demote that patch's other record flags to note** | environment, not the patch: "measures unreliable" (the flag text itself). Rerun. |
| `record.warnings` `sr_header_mismatch`, report `warnings` `dsp_state_unknown`, channel >2 / `--note: no notein or kslider` | note | informational; the analysis already corrected itself |
| `unsupported` (mc.dac~, plugout~, poly~, pfft~, bpatcher) | note ("not tapped") | coverage gap, not a defect. **This overrides the bridge's exit_code.** |
| `shot.error` | note (hint: Screen Recording permission) | evidence aid only |
| `shot.png` | listed (not a finding) | the agent may `Read` the PNG to eyeball the layout |
| `closed == False` | warning | the temp window is still open in MAX: close it **without saving** |
| `feedback_suspected` | warning | the 1000-event cap tripped (flood); the error list may be incomplete |
| `verdict == "bridge_failed"` after a good pre-flight | none: status `aborted` | MAX stopped answering (a modal dialog, a crash, or the user switched the toggle OFF); stop and report the unchecked patches |

**Exit codes** (house convention, matching `max_bridge`): 0 = ran, notes only; 1 = any live blocker or warning; 2 = skipped, aborted or usage error. `/max-verify` treats 2 as "live check skipped: <hint>" and leaves the static summary exactly as it was.

## Don't Hand-Roll

| Problem | Use instead |
|---|---|
| OSC, sequencing, DSP restore, SR guard, error dedupe | `bridge.run_check` (confirmed) |
| a reachability probe | `bridge.Bridge(...).ping()` + `bridge._bridge_hint(HOST, port)` (it already names the toggle) |
| window titles | `bridge.cg_windows()` (onscreen-only fix f00883c6) |
| argument defaults | `bridge.build_parser().parse_args(...)` |
| active project | `src.maxpat.project.get_active_project(REPO_ROOT)`, which returns None on a bad pointer and never raises; plus `--project NAME`, which overrides without writing `.active-project.json` |

## Common Pitfalls

1. **The original is already open in MAX.** It shares `send`/`receive`/`buffer~`/`pattr`/`coll` names with the copy, and `udpreceive <port>` fails to bind a second time, which gives a spurious error. The checklists made "close the original" a manual step. Detect it with `cg_windows()` (titles are `<stem>` or `<stem> (presentation)`, as confirmed for the copy in N5) and **skip that patch with a note**. Never close the user's window: it may hold unsaved edits.
2. **Error attribution.** `error` and `console` see **every** open patch. Posts from other patches during the listen window get attributed to the patch under test. Docs: close unrelated patches. Blockers need the 4 wordings, so stray runtime noise lands as warnings.
3. **A modal dialog or crash mid-batch** stalls `deferlow`: `/pong` times out after `--load-timeout` 30 s. Abort the loop on the first `bridge_failed`; don't burn 30 s per remaining patch.
4. **Run time.** Measured: about 5 s per patch for a load-only run (settle 3 s + shot ~1.5 s) and about 9 s with `--record 3`. Runs are strictly sequential: one reply port (7401), one `sfrecord~`. Never parallelise. Print progress per patch.
5. **DSP and volume.** `--record` turns DSP on (restored afterwards). If DSP was already on, even a load-only copy plays immediately. Put "turn the volume down" in the doc. Audio-input patches stay load-only by default (feedback).
6. **Double import.** Running `python3 tools/max_verify_live.py` puts `tools/` on `sys.path[0]`, so `import max_bridge` would create a second module object, and test monkeypatches (`bridge._make_run_dir`, `bridge._run`) would silently miss. Always `from tools import max_bridge as bridge` after inserting REPO_ROOT. A test should assert `live.bridge is tools.max_bridge`.
7. **Release builds have no bridge.** `/patches export-ignore` [VERIFIED: .gitattributes:15], while `tools/` ships. In an installed release `BRIDGE_PATCH` is missing, so the pre-flight must say "bridge patch not available in this install", not the generic hint.
8. **Uncaught exceptions in `run_check`.** `instrument()` raises on bad JSON, and `analyze()` on a bad wav. Catch per patch and turn them into a warning. Ctrl-C bypasses `_execute`'s BridgeError cleanup (DSP may stay on, the window open); document it.
9. **Children that are also playable** (FDNVerb-style abstractions with no top-level) are excluded by the sibling rule only when a sibling references them. Explicit paths (`max_verify_live.py PATH…`) cover the rest, for example the fixtures in `patches/max-bridge/fixtures/`.
10. **Stale docs.** `tools/max_bridge.py:3-9` and `patches/max-bridge/context.md:3` still say "v0.2.0 pending" and "no /max-verify integration". Update the text only.

## Security Domain

| ASVS | Applies | Control |
|---|---|---|
| V5 Input validation | yes | `guard_input` (repo or temp only, `.maxpat` only, refuses `__maxbridge_*`) and the `Bridge.send` `/open` copy-prefix check; both already exist. The wrapper adds no new address. |
| V12 Files | yes | copies are siblings, gitignored (`__maxbridge_*`, .gitignore:23) and deleted in a `finally`; run dirs go in `$TMPDIR` |
| V14 Config | yes | **the kill switch is never touched.** It sits before `route` (the gate drops everything while OFF), so it cannot be remotely toggled anyway. The wrapper must not script UI clicks or `open -a Max` on the bridge patch. It ends every live report with the note "turn the bridge toggle OFF / close the bridge when done" (LAN caveat: `udpreceive` binds all interfaces). |
| V2/V3/V4/V6 | no | — |

## Validation Architecture

| Property | Value |
|---|---|
| Framework | pytest 9.0.2 (probed); `tests/test_max_bridge.py` baseline 124 passed in 18.7 s |
| Quick run | `python3 -m pytest tests/test_max_verify_live.py -q -x` |
| Full suite | `python3 -m pytest -q` |

Tests in the new `tests/test_max_verify_live.py`:
- **Imports:** `from tests.test_max_bridge import FakeBridge, _tone_patch` (house convention, as in `from tests.test_validation import _make_box`). Do not move FakeBridge (that would be regression churn). Redefine the 3-line `run_dir` fixture.
- **Top-level selection:** bpatcher child, poly~ child, comment self-reference not counted, `__maxbridge_*` dropped.
- **Option rules:** dac+notein gives record and note; adc gives load-only; mc.dac~ gives load-only; `--record 0`.
- **`map_findings`:** one row per table line, including the demotion under `short_recording`, and unsupported staying a note while the bridge exit_code is 1.
- **Skip paths:** FakeBridge not started (closed or kill switch) gives status `skipped`, exit 2, and **no `__maxbridge_*` file ever written**. A muted bridge after the pre-flight (`FakeBridge(mute_after_open=True)`) gives `aborted`, and the later patches are not attempted.
- **Run paths:** an error run (`FakeBridge(errors=True)`) gives a blocker "osc~: No such object". A clean tone run gives exit 0.
- **Open original:** monkeypatch `bridge.cg_windows` to return a row titled with the stem; the patch is skipped with a note.
- **Import identity:** `live.bridge is tools.max_bridge`.
- **Doc guards:** max-verify.md still contains `from src.maxpat import` and `review_patch` (`tests/test_agent_skills.py:459-471`, `tests/test_commands.py:142-147`), and now also mentions `--live` and `max_verify_live.py`.

**Manual MAX confirmation** (new `patches/max-bridge/test-results/v0.3.0-verify-live-checklist.md`):
- bridge closed gives "skipped" while the static report is intact;
- the toggle ON on simple-fm gives record + note + shot;
- the fixtures `fx-nosuchobj` (blocker) and `fx-dc` (warnings);
- the original open gives skip;
- the toggle switched OFF mid-batch gives "aborted".

## Docs to update

- `.claude/commands/max-verify.md`:
  - `## Arguments`: `--live`, `--record N` (0 = off), `--no-shot`, `--note P V`, `--live-inputs`;
  - Behavior step 7 "Live check (opt-in)" with the CLI call and the skip and exit semantics;
  - an Output Format block `Live check (MAX 9.2):` with per-patch `LIVE BLOCKER/WARNING/NOTE`, shot path and run dir;
  - Summary `(+ live: b/w/n | live check skipped: <hint>)`;
  - keep the existing import lines.
- `.claude/skills/references/severity-contract.md`: a new **§7 Live findings** with the table above, citing `tools/max_verify_live.py` in place of the header's "checked against src" claim.
- `patches/max-bridge/context.md`: replace line 3, and add a "## /max-verify --live" section covering selection, options, mapping pointer and the abort rule. Update `status.md` too (still "v0.2.0 built, pending manual test", although dc0cde91 confirmed it).
- `tools/max_bridge.py` module docstring (lines 3-9): text only.
- `.claude/skills/max-critic/SKILL.md` "When to Use": one line saying live findings are report-only and never revision requests (optional).
- **CLAUDE.md: no change needed.** No rule requires it: severity semantics live in `severity-contract.md`, which CLAUDE.md already points to.

## Environment Availability

| Dependency | Available | Notes |
|---|---|---|
| MAX process | yes (`pgrep -x Max` gives pid 15535) | `-x Max` is a reliable "MAX running" probe |
| Bridge reachable | **no** at research time: `ping` exit 2 with the toggle hint (closed or toggle OFF) | this is exactly the skip path: a good live fixture for the doc example |
| osascript / screencapture | `/usr/bin/osascript`, `/usr/sbin/screencapture` | macOS only; Screen Recording permission was granted (shots passed in the checklists) |
| numpy / scipy | 2.4.0 / 1.17.0 | — |

## Assumptions Log

| # | Claim | Risk if wrong |
|---|---|---|
| A1 | Audio-input patches default to load-only (feedback risk outweighs coverage) | effect patches get no audio check unless `--live-inputs` is given |
| A2 | Only the 4 `ERROR_WORDINGS` keys are blockers; other console errors are warnings | a real load failure with other wording is under-reported |
| A3 | `nonfinite`/`runaway` = blocker; `clipping`/`dc_offset`/`silent` = warning | severity noise |
| A4 | An original's MAX window title is exactly `<stem>` or `<stem> (presentation)` (confirmed for copies only; the unsaved `*` form is untested) | an open original goes undetected, giving duplicate names and spurious errors |
| A5 | Timing estimates of 5 s / 9 s per patch are derived from the defaults, not measured end to end | longer runs |

## Open Questions

1. **Should load-only runs also switch DSP on briefly?** Today gen~ DSP-time errors (`failed to compile genpatcher/patcher`) only appeared with DSP on (checklist step 5), so they are missed. That needs a bridge plan change, so defer it. Recommendation: accept it for now and mention it in the doc.
2. **Should live counts merge into the single Summary line, or sit beside it?** Recommendation: beside it, `(live: …)`, so static gating semantics stay visibly separate.

## Sources
- Read this session: `tools/max_bridge.py` (full), `tests/test_max_bridge.py` (FakeBridge, `_check`, `run_dir`), `.claude/commands/max-verify.md`, `.claude/skills/max-critic/SKILL.md`, `severity-contract.md`, `patches/max-bridge/{context.md, open-questions.md, test-results/v0.1.0*, v0.2.0*}`, `src/maxpat/project.py:95-193`, `src/maxpat/dsp_sim/measure.py:55-77`, `.gitattributes`, `tests/test_release.py`, `tests/test_commands.py`, `tests/test_agent_skills.py:459-471`.
- Probes: the generated/ survey script (33 projects), `max_bridge.py ping` (exit 2), `pgrep`, pytest baseline.

**Valid until:** the next change to `tools/max_bridge.py` or the bridge patch.
