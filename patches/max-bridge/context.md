# max-bridge

**Spike (Q34, quick 261016-uy1; v0.2.0 follow-ups, quick 261021-l26; v0.3.0, quick 261021-olv).** v0.1.0 and v0.2.0 are confirmed in MAX 9.2 (`test-results/v0.1.0-bridge-checklist.md` and `test-results/v0.2.0-bridge-checklist.md`, 2026-10-21, commit dc0cde91). v0.3.0 adds `check --dsp-on-load` and `tools/max_verify_live.py` (`/max-verify --live`), confirmed in MAX 9.2 (`test-results/v0.3.0-verify-live-checklist.md`, 2026-10-21; four fixes from the run: 9e849d87, b333b135, 869b5885, a4e17423). Known limit: a kill-switch abort leaves the copy window open and DSP as it was mid-run (the close and restore cannot pass the closed gate); the abort hint says so.

## Purpose

"Pending test in MAX" is the bottleneck in most projects. The bridge lets Python drive a running MAX 9.2:
- open a patch;
- capture the console errors raised while it loads;
- record N seconds of its output for dsp_sim analysis;
- screenshot its window.

The spike's job is to find out which of these mechanisms actually work.

Design source: `.planning/quick/261016-uy1-implement-q34-in-planning-reviews-2026-1/261016-uy1-RESEARCH.md`. That file is not committed; the summary below is the durable copy.

## Pieces

- `tools/max_bridge/max-bridge.maxpat` (repo root): the resident bridge patch. Open it in MAX and leave it open while `tools/max_bridge.py` runs. It lived at `generated/max-bridge.maxpat` until quick 261022-ud6 (WR-01) moved it, content unchanged, so releases ship it (`/patches` is export-ignored); the checklists in `test-results/` keep the old path as a historical record.
- `tools/max_bridge.py` (repo root): the client, with the `ping`, `check` and `analyze` subcommands.
- `tests/test_max_bridge.py`: hermetic tests that run against an in-process fake bridge. No MAX is needed.
- `tools/max_verify_live.py` (v0.3.0): the `/max-verify --live` wrapper. It picks the project's top-level patches, chooses the `check` options per patch, runs them one after another and maps each report to live findings.
- `tests/test_max_verify_live.py` (v0.3.0): hermetic tests of the wrapper on the same fake bridge.

## Protocol (the bridge is a dumb pass-through; Python sequences everything)

| Python -> MAX (UDP 7400) | Bridge wiring |
|---|---|
| `/ping` | route -> msg `/pong` -> udpsend (the ordering barrier) |
| `/open <abs path>` | route -> `prepend load` -> `pcontrol` |
| `/openfile <abs path>`, `/closefile` | `;\rmax openfile maxbridge $1` / `;\rmax closefile maxbridge` (variant B) |
| `/sf <msg...>` | route -> `sfrecord~ 2` inlet 0 (`samptype float32`, `open <wav>`, `record <ms>`, `0`) |
| `/console <msg...>` | route -> `console @showonlyerrors 1` (`write <file>`, `showonlyerrors 0/1`) |
| `/listen 1/0` | route -> `t i i i i` -> `error` and the three console `gate`s (`loadmess 0` closes them at load) |
| `/dsp 1/0` | route -> `select 1 0` -> `;\rdsp start` / `;\rdsp stop` |
| `/close` | route -> `;\r__maxbridge_close bang` (the temp copy closes itself) |
| `/query` (v0.2.0) | route -> `t b b b` -> `dspstate~`, `adstatus sr`, `adstatus switch` (any args become bangs, so a query never reaches adstatus's int "change a setting" method) |
| `/note <pitch> <vel> <ch>` (v0.2.0) | route -> `send __maxbridge_note` (only the temp copy has the matching receive) |
| kill switch (v0.2.0) | `toggle` (OFF at every load: `loadbang` -> `0` -> toggle) -> `t i i`: outlet 1 -> `gate 1 0` inlet 0; outlet 0 -> `select 0` -> msg `/listen 0` -> route inlet 0 -> the listen fan-out |

Route addresses are appended, never inserted, so the outlet indices of the v0.1.0 addresses (0-8) and their cords never move.

MAX -> Python (UDP 7401):
- `/err error <words...>`, from `error`;
- `/con/obj`, `/con/msg`, `/con/type`, from console outlets 0, 1 and 2, each through its gate;
- `/state/dsp 0|1` (adstatus switch, right outlet), `/state/adsr <sr>` (adstatus sr, right outlet), `/state/sr <sr>` (dspstate~ outlet 1): the `/query` replies, via `prepend /state/*` -> `send __maxbridge_reply` -> `receive __maxbridge_reply` -> udpsend (Rule #4: a named pair instead of a 1500 px cord). adstatus also reports at bridge load (its loadbang method) and dspstate~ whenever DSP starts or stops; these are harmless localhost packets that the client ignores outside a run.

`udpreceive` -> `gate 1 0` (inlet 1, data) -> `deferlow` -> `route`. The gate drops every command while the kill switch is OFF, before anything is queued. `deferlow` puts loads on the low-priority queue and keeps `/open` then `/ping` in order.

### Kill switch (v0.2.0, N1)

The enable toggle at the top left is OFF whenever the bridge patch opens, so every incoming command, `/ping` included, is dropped. Turn it ON to let `tools/max_bridge.py` in. A gated bridge looks exactly like a closed one: `ping` and `check` time out (exit 2) with a hint naming both causes (open the patch, turn the toggle ON). Turning it OFF also closes listening (`error` off, console gates closed), the same path the client's `/listen 0` takes. The toggle is a plain toggle (no parameter mode, no presentation); `loadbang` -> `0` sets it OFF explicitly, which the save gate's uninitialized-state check requires.

### DSP state (v0.2.0, N4)

`check` sends `/query` (then a `/ping` barrier) before `/open`, so a patch that starts DSP at load cannot hide the prior state. `dsp_before` is the first `/state/dsp`, else 1 when a `/state/sr` arrived (dspstate~ is silent while DSP is off), else unknown (None). After the record block, `/dsp 0` is sent only when DSP was off before, or when the state is unknown and this run switched it on (then the warning `dsp_state_unknown`; an older bridge patch ignores `/query`). DSP that was on stays on. `--leave-dsp-on` never sends `/dsp 0`. `--dsp-on-load` (v0.3.0) sends `/dsp 1` just before `/open` (never between `/open` and its load `/ping`), and the same restore rule applies. The report carries `dsp_before` and `dsp_stop_sent`.

### Sample rate (v0.2.0)

A second `/query` right after `/sf record` (DSP is surely on) makes dspstate~ report the rate the oscillators actually run at. `max_sr` is the last `/state/sr`, else the last `/state/adsr`. When it differs from the wav header by 1 Hz or more, the recording is analyzed at `max_sr`, the record carries `header_sample_rate`, and `record.warnings` gets `sr_header_mismatch: ...`. It is a warning, not a flag: the exit code does not change. `analyze OUT.wav --sr N` reruns it by hand. (v0.1.0 measured a 440 Hz tone as 478.9 Hz: 48000/44100 x 440.)

### Errors (v0.2.0)

`errors` stays the raw list (one entry per channel per posting). `errors_distinct` groups it by a canonical key: console entries become `"{obj}: {msg}"`, whitespace is collapsed, a doubled leading `"X: X: "` becomes `"X: "`, and a key equal to another minus one leading `"word: "` merges into the longer one. Each entry has `sources` (error, console, console_write counts), `occurrences` (the max over channels: every channel sees every posting) and `first_t`. The stderr summary reads `N distinct error(s) (M occurrence(s))`.

Audio: `receive~ __maxbridge_L` / `__maxbridge_R` -> `sfrecord~ 2` -> `snapshot~ 100` -> number box (elapsed ms).

## Temp-copy policy

`check` never opens the patch under test. Instead, `instrument()` writes a sibling copy, `__maxbridge_<stem>.maxpat`, built with the Patcher API, and adds to it:
- `send~ __maxbridge_L/R` taps on every `dac~`/`ezdac~` input source (the existing cords are kept). Since v0.2.0 each output box gets its own pair directly below it: L at the dac's x, 20 px under its bottom; R 15 px right of L (or at the dac's x when there is no L); moved down only on a real overlap; presentation 0. Several `send~` with one name sum, so the recording is unchanged. The report lists them in `tap_boxes`;
- with `check --note PITCH VEL [--note-ms MS]` (v0.2.0, needs `--record`): `receive __maxbridge_note` -> `unpack 0 0 0` in every patcher that holds a `notein`, mirroring each notein cord (outlet k -> the same destination). unpack fires right to left like notein, so cold-before-hot holds. Only when no notein exists anywhere does it drive the first `kslider` (velocity into the cold inlet 1, then pitch into the hot inlet 0; kslider has no list method). Never both: that would be a double note-on. Neither present: the warning `--note: no notein or kslider to drive`. The client sends `/note P V 1` after `/sf record` and `/note P 0 1` after MS ms (default 75% of the record). The report carries `note` and `note_target`;
- a cordless close hook: `receive __maxbridge_close` -> `clean, wclose` -> `thispatcher`.

The copy is written with `format_patch_text` + `atomic_write_bytes`, not `save_patch_roundtrip`: it is ephemeral, so it is neither committed nor gated (research A6). It is deleted in a `finally`, and `__maxbridge_*` is in `.gitignore` so a leftover copy can never be swept into a project auto-commit. Placing it as a sibling keeps relative lookups working (`.gendsp`, js, abstractions, audio files).

The original file is never written.

## Fixture-writer policy

Fixtures live in `fixtures/`, never in `generated/`: `tests/test_integration_patches.py` fails on blockers in `generated/`. There are two writers:
- **Writer A** (`save_patch_roundtrip`, auto-commits, save gate): for fixtures that are valid patches.
- **Writer B** (`format_patch_text` -> `atomic_write_bytes` -> `auto_commit_patch(files=[...])`): for deliberate-error fixtures, which the gate exists to refuse.

No allowlist entries are added for either.

| Fixture | Content | Expected | Writer |
|---|---|---|---|
| `fx-clean` | `cycle~ 440` -> `*~ 0.2` -> `dac~` (both inlets) | no errors; peak ~0.2, pitch ~440 Hz, dc ~0 | A |
| `fx-dc` | `sig~ 0.5` -> `*~ 1.` -> `dac~` (both inlets) | dc ~0.5; `dc_offset` + `silent`; pitch 0 | A |
| `fx-badargs` | a lone `send 15` | `send: bad argument creating object`; `no_output_tap` | A (the gate accepted it) |
| `fx-nosuchobj` | `cycle~ 440` renamed to `osc~ 440` after finalize (the sanctioned rename pattern) | `osc~: No such object`; `no_output_tap` | B (the gate refuses the Pure Data name) |
| `fx-genfail` | `cycle~ 220` -> gen~ codebox `Param g(0.5); g = in1; out1 = g;` -> `*~ 0.2` -> `dac~` | `codebox: can't assign to parameter g` + `failed to compile genpatcher` | B (validate_genexpr blocks the Param assignment) |

`fx-nosuchobj` breaks Rule #1 on purpose, for the console-capture test only.

## LAN caveat

`udpreceive` has no bind-host option, so the bridge listens on UDP 7400 on **all** network interfaces. Any host on the network can send `/open`, and a patch containing js or node.script amounts to code execution.
- Close the bridge patch when it is not in use.
- Deny incoming connections if macOS asks.

The Python client binds 127.0.0.1 only. The kill switch (v0.2.0, above) is implemented and OFF at every load, so nothing gets through until you turn it ON; still close the bridge patch when it is not in use. Any open patch can address `__maxbridge_reply` (its only sink is udpsend to 127.0.0.1:7401, which any patch could create anyway) and `__maxbridge_note` (which exists only in gitignored temp copies). There is no generic `/send`: `/note` reaches one fixed name.

## /max-verify --live (v0.3.0)

`tools/max_verify_live.py` runs after `/max-verify`'s static report and never changes it. Live findings are report-only: they are never part of the save gate or the critic revision loop.

- **Top-level selection.** From the project's `generated/*.maxpat` (non-recursive) it drops `__maxbridge_*` and every file a sibling references: a bpatcher `name`, a newobj whose first token is a sibling stem, or the poly~/mc.poly~/pfft~ argument. Comments never count, and a file never excludes itself. terrain-synth resolves to `terrain-synth.maxpat` only. Explicit PATHs skip the selection (the fixtures in `fixtures/`, playable abstractions). `--project NAME` overrides the active project without writing `.active-project.json`.
- **Option rules.** The tap and note-target decision reuses the bridge's own `_instrument_patcher` / `_inject_note` on an in-memory copy, so it never disagrees with what `check` taps. A tapped patch records (`--record 3` by default, `0` = never) with `--note 60 100` when it has a notein or kslider. D-01: an audio-input patch (`adc~`, `ezadc~`, `mc.adc~`, `mc.ezadc~` at any depth, or in a sibling it references) is load-only unless `--live-inputs`. D-02: every other load-only patch gets `check --dsp-on-load`, which switches DSP on just before `/open` so gen~ compile errors post during the settle; the usual restore rule puts DSP back. A locked audio-input patch never gets DSP switched on; if DSP was already on, a note says its input was live.
- **Severities.** `.claude/skills/references/severity-contract.md` section 7 holds the table; `map_findings` implements it. The bridge's own exit_code/verdict is never the severity.
- **Batch safety.** Patches run strictly one after another (one reply port, one sfrecord~). The first `bridge_failed` after a good pre-flight aborts the run, and the rest are "not checked". A per-patch exception becomes a warning and the loop goes on.
- **Open originals.** When a patch's own window is open in MAX (title `<stem>`, `<stem>*`, `<stem> (presentation)` or `<stem>.maxpat`), it is skipped with a note. The user's window is never closed.
- **The toggle and the bridge patch stay the user's (D-04).** The wrapper never sends a command itself: it reaches MAX only through `run_check` and a read-only `/ping` pre-flight. A closed bridge or the toggle OFF gives "live check skipped" with the toggle hint. Every report ends with the reminder to turn the toggle OFF.
- **Exit codes.** 0 ran with notes only; 1 any live blocker or warning; 2 skipped, aborted or a usage error.

## Presentation mode

None. The bridge is a utility patch whose one user control is the enable toggle (top left, patching mode); it has no presentation, so Rule #9 does not apply.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | clean |
| 1 | findings: error lines, analysis flags, unsupported outputs, shot failure, feedback cap |
| 2 | bridge failure: no `/pong`, timeout, bind failure, a wav that never settles, refused input |

`tools/max_verify_live.py` (v0.3.0) uses its own codes, computed from the live findings rather than the bridge's:

| Code | Meaning |
|---|---|
| 0 | ran; notes only |
| 1 | any live blocker or warning |
| 2 | skipped (no bridge patch in the install, MAX not running, no answer), aborted (MAX stopped answering mid-run) or a usage error |
