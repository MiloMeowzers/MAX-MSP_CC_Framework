# Quick 261016-uy1: Q34 MAX bridge spike - Research

**Researched:** 2026-10-16
**Domain:** Driving a running MAX 9.2 from Python (UDP/OSC, pcontrol, error/console, sfrecord~, screencapture)
**Confidence:** MEDIUM. Every message form below was read from the installed 9.2.0 bundle. Whether the mechanisms behave as needed at runtime can only be confirmed by the user in MAX, which is the point of the spike.

<user_constraints>
## User Constraints (from the task text; there is no CONTEXT.md)

- This is a spike only. No `/max-verify` integration until the user confirms it works.
- Deliverables:
  - a resident bridge patch, built with the Patcher API under `patches/max-bridge/` and following all CLAUDE.md patch rules;
  - a Python client, `tools/max_bridge.py`;
  - a manual test checklist;
  - a list of open questions.
- **Open:** open a given `.maxpat` in the running MAX 9. Verify the mechanism (pcontrol `load`, ...) against refpages and help files.
- **Console:** test whether `error` and `console` see "No such object", "bad arguments" and gen~ "failed to compile" errors raised during load.
- **Record:** record N s to a temp wav with sfrecord~ (or instrument a temp copy that taps the dac~ inputs), then analyze it with the dsp_sim measures (peak, RMS, DC, NaN, pitch).
- **Screenshot:** capture the patch window with `screencapture`.
</user_constraints>

## Project Constraints (from CLAUDE.md, the ones that bind this task)

- **Rule #1:** use only DB objects, and check `domain`. Every object proposed below was looked up (I/O table below).
- **Rule #2 / severity contract:** a new file refuses every blocker at save, so the sfrecord~ DB gap described below must be fixed first.
- **Rules #3 and #4:** use `trigger` for fan-out of control messages, top-to-bottom flow, and comments on non-obvious cords.
- **Rule #5:** build patches with the Patcher API only; no generator scripts.
- **Rule #7:** saves auto-commit, scoped to their paths. Never `git add .` and never `git stash`.
- **Rule #9:** the bridge patch does not use presentation mode, so no presentation-parity work is needed.
- **`receive~` / `send~`:** these are used for cross-patch audio. `inlet~` / `outlet~` must not be used.
- **Message boxes:** `;\r<name> <msg>` cordless messages are a proven form (wormhole v1.4.x, from memory).

## Summary

The bridge should be a dumb UDP pass-through: `udpreceive 7400` → `deferlow` → `route` → MAX objects, and `error` / `console` → `prepend /addr` → `udpsend 127.0.0.1 7401`. Python owns all the sequencing. It uses a stdlib OSC codec (about 60 lines, `socket` + `struct`; python-osc is installed but is not a declared dependency).

Opening uses `pcontrol load <abs path>`. Python follows each command with `/ping`, and the `/pong` reply is the "load returned" barrier, because `deferlow` keeps commands in order.

The patch under test is never opened directly. A sibling temp copy, `__maxbridge_<stem>.maxpat`, is opened instead, with three additions:
- each `dac~` / `ezdac~` input source fans out to `send~ __maxbridge_L/R`;
- a cordless close hook: `receive __maxbridge_close` → `clean, wclose` → `thispatcher`;
- a unique window title, which the screenshot needs.

The bridge records `receive~ __maxbridge_L/R` → `sfrecord~ 2` in float32, so NaN survives. Python reads the file with `scipy.io.wavfile` and runs `measure_peak`, `measure_rms`, `measure_ac_rms` and `measure_fundamental`. DC is `np.mean`, and NaN/inf are counted separately.

The screenshot does not touch the bridge. It ports MUSC320's proven `tools/patch_shot.py` approach: a JXA `CGWindowListCopyWindowInfo` call to find the window id, then `screencapture -x -o -l <id>`. pyobjc/Quartz is not installed.

**Primary recommendation:** build it in this order:
1. Fix the `sfrecord~` inlet-1 override.
2. Build the bridge patch.
3. Write `tools/max_bridge.py` (OSC codec, `instrument()`, `analyze()`, `shoot()`, `check` CLI), with hermetic tests.
4. Build the fixture patches and the user checklist.

Ship the error stream from both `error` and `console`, plus a `console write` before/after diff. Which of the three captures load-time errors is the question the spike answers.

## Architectural Responsibility Map

| Capability | Primary tier | Secondary | Rationale |
|---|---|---|---|
| Sequencing, timeouts, temp copy, analysis, verdict | Python client `tools/max_bridge.py` | - | Keeps the patch dumb; message forms can change without re-saving the patch |
| Open / close the patch | MAX: `pcontrol` in the bridge, `thispatcher` in the temp copy | macOS `open -a Max` and the AX close button (proven fallback) | Opening must happen inside MAX so the load barrier is ordered |
| Error capture | MAX: `error`, `console` | `console write` file | The spike decides which is authoritative |
| Audio capture | MAX: `send~` in the copy → `receive~` + `sfrecord~` in the bridge | - | You cannot tap `dac~` output from outside the patch |
| Screenshot | macOS: JXA window list + `screencapture` | - | Proven in MUSC320 (`SHOT PASS` x5, `.planning` there) |

## Objects (DB-verified this session: `ObjectDatabase().lookup` / `compute_io_counts`)

All of these have domain Max/MSP, and `get_effective_restrictions` returns `[]` for each.

| Object (args) | I/O | Role | Evidence |
|---|---|---|---|
| `udpreceive 7400` | 1 / 1 | OSC in. Attributes: `active defer maxqueuesize outputformat port quiet usestring`. Default `outputformat message` decodes OSC, so the address becomes the selector. There is **no bind-host attribute**. | refpage `docs/refpages/max-ref/udpreceive.maxref.xml:97-172` (`defer` default 0 = "scheduler thread"; `port` default 7374) |
| `udpsend 127.0.0.1 7401` | 1 / 0 | OSC out: "Max messages ... are serialized and sent ... as OSC-compatible UDP packets" | `max-ref/udpsend.maxref.xml` |
| `deferlow` | 1 / 1 | Moves every incoming command to the low-priority queue, in order | DB |
| `route /ping /open /sf /console /dsp /listen /close /openfile /closefile` | 10 / 10 | Dispatch: 9 matches + unmatched | `compute_io_counts` → (10, 10) |
| `pcontrol` | 1 / 1 | `load <file> [#1..#9 args]` opens the file "if it can be found in Max's search path". Also: `loadunique`, `shroud`, `close` (closes connected subpatchers only, not loaded files), `open`, `help` | `max-ref/pcontrol.maxref.xml` methods; help `help/max/pcontrol.maxhelp` "load <filename>" |
| `error` | 1 / 1 | Off until an int arrives; `1` listens, `0` stops. Output: "Any Max error generated by any object in any patch while the error object is listening ... preceded by the symbol `error` ... as individual words" | `max-ref/error.maxref.xml` (misc Output) |
| `console @showonlyerrors 1` | 1 / 3 | Outlets: 0 Object Name, 1 Message, 2 Message Type (int). Messages: `clear` clears the whole Max console; `write <filepath>` writes the entire console "ignoring any filters". Attributes: `classfilter patcherfilter showonlyerrors textfilter` | `max-ref/console.maxref.xml` |
| `sfrecord~ 2` | 2 / 1 | Methods: `open [name] [aiff/wave/...]`, `record <ms>`, `samptype float32`, `int` (0 stops and closes), `start <file> [nchans]`, `stop`, `print`, `loop`. Attributes: `beginramp endramp bitdepth dither nchans quantization resample sortloop` | `msp-ref/sfrecord~.maxref.xml:68-327`; help `help/msp/sfrecord~.maxhelp` ("open filename.wav", "record 1000", "prepend samptype") |
| `receive~ __maxbridge_L` / `_R` | 1 / 1 | Sums every `send~` of that name across patchers | `msp-ref/receive~.maxref.xml`; `send~`: "When two or more send~ objects are aimed at the same receive~ object, the signals add together" |
| `send~ __maxbridge_L` / `_R` (temp copy) | 1 / 0 | Tap | `msp-ref/send~.maxref.xml` |
| `receive __maxbridge_close` (temp copy) | 0 / 1 | Cordless close hook | DB (`r name` → (0, 1)) |
| `thispatcher` (temp copy) | 1 / 2 | `clean` "resets the patch's dirty bit"; `wclose` closes the window (help subpatcher `p "wclose sweet angel"`); `dispose` is "*USE AT YOUR OWN RISK*" (help: `p "dispose is evil"`) | `max-ref/thispatcher.maxref.xml:160-177`; `help/max/thispatcher.maxhelp:572` |
| `trigger i i` (and similar) | 1 / N | `/listen` fan-out to `error` + gates | `compute_io_counts` |
| `gate` | 2 / 1 | Gates the console streams while not listening | DB |
| `sel 1 0` | 3 / 3 | `/dsp 1` and `/dsp 0` | DB (`select` with 2 args) |
| `prepend /err` and similar | 1 / 1 | OSC address for the outgoing streams | DB |
| `snapshot~` + number box (optional) | - | Elapsed-ms readout from the sfrecord~ outlet; it also terminates the signal chain, which silences the "Unterminated signal chain" warning | DB |

The MAX side needs these messages:
- `;\rdsp start` / `;\rdsp stop`: the user guide documents `; dsp start` "Turns the audio on" (`docs/userguide/content/controlling_max_with_messages.json`).
- `; max openfile <ref> <path>` and `; max closefile <ref>`: a documented open/close pair (`max-ref/max.maxref.xml`, "intended for batch collective building"). This is variant B for open/close.

**Blocking DB gap (fix first):** `overrides.json` → `objects.sfrecord~.inlets[1]` is `{"type": "", "signal": false}`. A prototype run this session of `validate_patch` on `receive~ → sfrecord~ 2` inlet 1 returned an error-level finding: `Signal outlet to control-only inlet: ... -> 'obj-4' inlet 1`. The refpage says "Each inlet of sfrecord~ accepts a signal", and `sfrecord~ 2` = (2, 1) in help. Set inlet 1 to `{"id": 1, "type": "signal", "signal": true}` with an `_audit` note. A variable-io rule (`first_arg` inlets, refpage default 1) is optional; leave it out of scope unless the test suite asks for it.

## Architecture

```
python tools/max_bridge.py check P.maxpat --settle 3 --record 5 --shot out.png
  │ 1 instrument(P) ─► P.dir/__maxbridge_<stem>.maxpat   (send~ taps + close hook)
  │ 2 bind 127.0.0.1:7401; /ping ─────────────► udpreceive 7400 ─► deferlow ─► route
  │ 3 /console write <tmp>/before.txt                      │
  │ 4 /listen 1 ─────────────────────────────────── t i i ─► error 1 ; gates open
  │ 5 /open <abs copy> ; /ping ── prepend load ─► pcontrol (synchronous load)
  │        ◄── /err error … , /con/msg …   (error, console ─► prepend ─► udpsend 7401)
  │        ◄── /pong  (= load returned; then wait --settle for gen~ compile)
  │ 6 /dsp 1 ; /sf samptype float32 ; /sf open <tmp>/out.wav ; /sf record 5000
  │        copy: dac~ sources ─► send~ __maxbridge_L/R ─► receive~ ─► sfrecord~ 2
  │ 7 wait 5 s + margin ; /sf 0 ; /ping   ◄── /pong
  │ 8 JXA window list → screencapture -x -o -l <id> out.png   (no bridge)
  │ 9 /console write <tmp>/after.txt ; /listen 0 ; /close ─► ;__maxbridge_close bang
  │ 10 delete the copy; analyze(out.wav); diff the console files; print JSON + exit code
```

Exit codes follow the house convention (`tools/audit_db.py`, MUSC320 tools): 0 = clean, 1 = errors or analysis failures found, 2 = the bridge failed (MAX not running, no `/pong`, timeout).

### Protocol: the bridge is pass-through, Python sequences

| Python → MAX (port 7400) | Bridge wiring | Reply |
|---|---|---|
| `/ping` | route → msg `/pong` → udpsend | `/pong` |
| `/open <path>` | route → `prepend load` → `pcontrol` | (none; follow it with `/ping`) |
| `/sf <msg...>` | route → `sfrecord~` inlet 0 (`samptype float32`, `open /x.wav`, `record 5000`, `0`) | - |
| `/console <msg...>` | route → `console` (`write /x.txt`, `clear`) | - |
| `/listen 1\|0` | route → `t i i` → `error` and the three console `gate`s | - |
| `/dsp 1\|0` | route → `sel 1 0` → `;\rdsp start` / `;\rdsp stop` | - |
| `/close` | route → msg `;\r__maxbridge_close bang` | - |
| `/openfile <path>`, `/closefile` | msgs `;\rmax openfile maxbridge $1` / `;\rmax closefile maxbridge` (variant B) | - |

| MAX → Python (port 7401) | Source |
|---|---|
| `/err error <words...>` | `error` → `prepend /err` |
| `/con/obj`, `/con/msg`, `/con/type` | `console` outlets 0, 1, 2 → `gate` → `prepend` |

Use separate addresses because the console's outlet firing order is unknown (see Open Questions).

**OSC codec (stdlib).** Encoding: the address, then the type tags (`,` + one tag per argument), then the arguments. Strings are NUL-terminated and padded to 4 bytes; `i` is a big-endian int32; `f` is a float32. The decoder should accept the tags `i f d h s S T F N` and skip bundles (`#bundle`). Python sends paths as single `s` atoms, so spaces survive, but write temp files to paths without spaces anyway.

### Temp-copy instrumentation (`instrument(src) -> Path`)

1. `text = src.read_text()`, then `p = Patcher.from_dict(json.loads(text))`.
2. Walk the top patcher and every embedded `p` subpatcher (inner `Patcher`s). In each patcher:
   - for every cord whose destination is a `dac~` or `ezdac~` box, map the inlet index to a channel. `dac~` uses its args (none means `1 2`); `ezdac~` uses inlets 0 and 1.
   - channel 1 → `send~ __maxbridge_L`, channel 2 → `send~ __maxbridge_R`.
   - add one `send~` per patcher per channel, and `add_connection(src_box, src_outlet, send_box, 0)`.
   - the existing dac~ cords stay untouched, so the patch stays audible.
   - signal fan-out is fine. Rule #4's trigger rule is about control messages.
3. Add `receive __maxbridge_close` → message `clean, wclose` → `thispatcher` at the top level.
4. Write the copy as a **sibling** (`src.parent / f"__maxbridge_{src.stem}.maxpat"`) with `format_patch_text(p.to_dict(), text)` + `atomic_write_bytes`. Do **not** use `save_patch_roundtrip`: it auto-commits and runs the save gate. A sibling keeps relative lookups working (`.gendsp`, js, abstractions and audio files next to the patch).
5. Delete the copy in a `finally`. Add `__maxbridge_*` to `.gitignore`: `auto_commit_patch` runs `git add -- <project_dir>` (`src/maxpat/project.py:416`), so a leftover copy would otherwise land in the next project commit.

Unsupported in the spike: report these as `"unsupported"`, never as a pass.
- `mc.dac~` (MC 1 / 0).
- `plugout~`: M4L only, and it cannot run outside Live.
- `dac~` inside `poly~`, `bpatcher` or abstraction files, which live in external files.
- channels above 2.
- a patch with no `dac~`: record nothing and report `no_output_tap`.

### Analysis (`analyze(wav) -> dict`)

`sr, x = scipy.io.wavfile.read(path)`. It supports `IEEE_FLOAT` and `EXTENSIBLE` (checked this session in the scipy 1.17.0 source). Per channel:
- `nan`/`inf` counts via `np.isnan` / `np.isinf`. `measure_peak` and `measure_rms` return NaN when *any* sample is non-finite, so count separately and measure the finite remainder.
- skip `ClassifierThresholds().settle_ms` = 100 ms.
- `peak = measure_peak`, `rms = measure_rms`, `ac_rms = measure_ac_rms`, `dc = float(np.mean(tail))`. **dsp_sim has no DC function**: `src/maxpat/dsp_sim/measure.py:85-238` defines `measure_rms`, `measure_peak`, `measure_ac_rms`, `measure_fundamental(buf, sample_rate)` and `cents_offset`.
- `pitch = measure_fundamental(tail, sr)`. It returns 0.0 when there is no clear period; its window is 40 Hz to 4 kHz.

Flags:
- `nonfinite`: any NaN or inf.
- `runaway`: peak > `runaway_amplitude` 10.0; also flag peak > 1.0 as `clipping`.
- `silent`: ac_rms < `amplitude_floor` 1e-4.
- `dc_offset`: |dc| > 0.01. This threshold is `[ASSUMED]`.

The thresholds come from `measure.py:71-77`.

Do not use stdlib `wave` (PCM only). Do not use int24/int16 either: NaN cannot survive integer quantization, so float32 is required.

### Screenshot (`shoot(stem, png)`)

Port these from `~/Documents/UBC/Courses/MUSC320/tools/patch_shot.py` (commit 1009e5c; a different repo, so copy them with a comment rather than import):
- `_CG_WINDOWS_JXA`: `ObjC.import("CoreGraphics")`, `CGWindowListCopyWindowInfo(0, 0)`, filter `kCGWindowOwnerName === "Max" && kCGWindowLayer === 0`;
- `_wait_window` (poll, then wait for the title to hold still);
- `_capture`: `screencapture -x -o -l <id>`, and fail on a missing or empty file.

The window title starts with `__maxbridge_<stem>`, so it is unique. A presentation-mode patch is titled `<stem> (presentation)`; the spike captures it as shown and reports the title, without sending the Cmd-Opt-E keystroke. Screen Recording permission is needed for the terminal: window names come back empty and images come back black without it.

## Common Pitfalls

1. **Thread and order.** `udpreceive` outputs on the scheduler thread (`defer` 0). Put one `deferlow` right after it: file loads belong on the low-priority queue, and a single queue keeps `/open` → `/ping` ordered, which is what the barrier relies on.
2. **Feedback loop.** If `udpsend` itself posts an error, `error` forwards it, and that can loop. Keep `error` off and the gates closed except between `/listen 1` and `/listen 0`. **Never** `print` inside the bridge.
3. **Absolute paths.** The refpage only says "found in Max's search path". An absolute POSIX path in `pcontrol load`, `sfrecord~ open` and `console write` is `[ASSUMED]` to work. The fallbacks are `open -a Max <path>` (proven by patch_shot) and variant B, `max openfile`.
4. **gen~ compiles late.** The compile error may post after `pcontrol load` returns. `--settle` (default 3 s) keeps listening after the `/pong`.
5. **sfrecord~ needs DSP on.** `open`/`record` while DSP is off records nothing; `start` would wait for DSP instead. Send `/dsp 1` first. After `/sf 0`, poll until the file size is stable before reading, because the header is written on close.
6. **sfrecord~ ramps.** `beginramp` and `endramp` exist, but their defaults are undocumented. A fade would bias peak and DC at the edges; the 100 ms settle trim covers the start, so also trim the last 50 ms.
7. **Save gate.** `save_patch_roundtrip` on a new bridge file refuses every blocker. Fix the sfrecord~ override first, or saving the bridge raises `PatchValidationError`.
8. **Error fixtures cannot go under `generated/`.** `tests/test_integration_patches.py:23` globs `patches/*/generated/*.maxpat` and fails on blockers. Put deliberate-error fixtures in `patches/max-bridge/fixtures/`. Write them with `format_patch_text`, so `tests/test_edit_fidelity.py` (rglob over `patches/`) still round-trips them, and commit them with `auto_commit_patch(files=[...])`.
9. **LAN exposure.** `udpreceive` has no bind-host attribute. Any host on the network could send `/open <path>`, and a patch with js or node.script is code execution. Keep the bridge closed when it is not in use. macOS may show a "accept incoming connections" firewall prompt for MAX; deny external connections.
10. **`console clear` wipes the user's Max window.** Use the `write` before/after diff instead, and never clear by default.

## Fixture patches for the checklist (`patches/max-bridge/fixtures/`)

| Fixture | Content | Expected |
|---|---|---|
| `fx-clean` | `cycle~ 440` → `*~ 0.2` → `dac~` (both inlets) | no errors; peak ≈ 0.2; pitch ≈ 440 Hz; dc ≈ 0 |
| `fx-nosuchobj` | `osc~ 440` (a PD name, deliberately invalid) | `osc~: No such object` (troubleshooting.md:13) |
| `fx-badargs` | `send 15` | `send: bad argument creating object` (user guide `error_messages.json`: "One send object with the argument 15 ... indicating an error") |
| `fx-genfail` | gen~ codebox `Param g(0.5); g = in1; out1 = g;` | `codebox: can't assign to parameter g` + `failed to compile genpatcher` (troubleshooting.md:41, Ambire v0.8.0) |
| `fx-dc` | `sig~ 0.5` → `dac~` | dc ≈ 0.5, `dc_offset` flagged, pitch 0 |

## Manual Test Checklist (seed; the plan writes the final one into `patches/max-bridge/test-results/`)

1. Open `patches/max-bridge/generated/max-bridge.maxpat` in MAX 9.2. Check that the console is clean and note whether a firewall prompt appears.
2. `python3 tools/max_bridge.py ping` → `PONG` within 1 s.
3. `check fx-clean --record 3 --shot`:
   - the window opens titled `__maxbridge_fx-clean`;
   - the tone is audible;
   - the JSON shows peak ≈ 0.2 and pitch ≈ 440;
   - the PNG shows only that window;
   - the window closes with no save sheet;
   - the copy is deleted.
4. `check fx-nosuchobj`. Record which of `error` / `console` / the console-write diff saw the error.
5. `check fx-badargs`: same.
6. `check fx-genfail`: same, and note the delay after `/pong` before the gen~ error arrived.
7. `check fx-dc`: dc ≈ 0.5 flagged. Also check the wav header: format tag 3 (float), 32-bit.
8. Variant B: `check fx-clean --open-mode openfile`. Does a window appear, and does `closefile` close it?
9. Run against one real project patch (e.g. `patches/simple-fm`), and confirm the original file is byte-identical afterwards (`git status` clean).

## Open Questions (answerable only in MAX)

1. Does `error` see load-time errors ("No such object" posted at instantiation) and gen~ compile errors from another top-level patcher? The refpage says "any object in any patch".
2. What do `console`'s outlets fire, and in what order? What do the Message Type ints mean (not documented in the refpage or help)? Is "No such object" an error type, so that it passes `@showonlyerrors 1`?
3. What is the `console write` file format (plain lines? the object-name column?), and does it accept an absolute POSIX path?
4. Do `pcontrol load` and `sfrecord~ open` accept absolute POSIX paths?
5. Must `samptype float32` come before `open`? (The help shows them as separate boxes with no order.) Does a float32 wav keep NaN?
6. Does `record <ms>` close the file when it finishes, or is `0` still required? Does `0` after an auto-stop post an error?
7. Does `clean, wclose` free a top-level patcher loaded by pcontrol (DSP chain gone, `send~` gone)?
8. Does `max openfile` show the window (variant B)?
9. How long after load does gen~ compile? This sets the `--settle` default.
10. Out of spike scope, but needed for `--live`: how should a patch that needs stimulus (MIDI or note messages) be driven? A possible `/send <name> <msg>` via `forward` (DB 1 / 0; `send <name>` selector) is deferred.

## Assumptions Log

| # | Claim | Risk if wrong |
|---|---|---|
| A1 | Absolute POSIX paths work in `pcontrol load`, `sfrecord~ open` and `console write` | Fall back to `open -a Max`, or Max-style paths via `conformpath` (DB 1 / 2) |
| A2 | `udpsend` encodes Max floats as OSC `f` (32-bit) or `d` | The decoder handles both, so the risk is low |
| A3 | A `route` remainder of `open /x.wav` arrives at sfrecord~ as the `open` selector | `/sf` pass-through breaks; switch to per-command routes with `prepend` |
| A4 | Signal fan-out to `send~` in the copy adds no audible change | None expected (send~ adds no gain) |
| A5 | The `dc_offset` threshold is 0.01 | Tune it after real runs |
| A6 | Writing an ephemeral, gitignored sibling copy without `save_patch_roundtrip` is acceptable under Rules #5 and #7 (it is built with the Patcher API, never committed, and deleted after) | The user may prefer copies in `$TMPDIR`, at the cost of relative-file lookups |

## Environment Availability

| Dependency | Available | Version | Note |
|---|---|---|---|
| MAX | ✓ (running, pid 75824) | 9.2.0 (e9c80e453de) | `Info.plist` |
| python3 | ✓ | 3.14.2 | |
| numpy / scipy | ✓ | 2.4.0 / 1.17.0 | declared in `requirements-dev.txt` |
| python-osc, soundfile | installed | - | **not declared**, so do not use them; stdlib OSC + scipy wavfile instead |
| pyobjc / Quartz | ✗ | - | use JXA through `osascript -l JavaScript` (proven) |
| `screencapture`, `osascript` | ✓ | macOS 26.6.2 | Screen Recording permission is needed for the terminal |
| UDP 7400 / 7401 | free | - | `lsof` showed no listener |

No new packages, so no package legitimacy audit is needed.

## Validation Architecture

The framework is pytest (`requirements-dev.txt` pytest>=9.0). Quick run: `python3 -m pytest tests/test_max_bridge.py -q`. Full suite: `python3 -m pytest -q`.

Write `tests/test_max_bridge.py` as hermetic tests. House convention (`tests/test_sync_max_bundle.py` header) is `import tools.max_bridge as bridge` and calling the functions directly. No MAX is needed:
- OSC encode/decode round-trip (`i f s`, padding, and `d` decode);
- `instrument()` on a tmp fixture with `cycle~` → `dac~`: the send~ taps go to inlets L and R; the original cords are unchanged; the close hook is present; `dac~ 3 4` gets no tap plus a warning; `mc.dac~` is reported unsupported;
- `analyze()` on synthetic float32 wavs written with `scipy.io.wavfile.write`: 440 Hz sine → pitch within 1 Hz; DC 0.5 flagged; injected NaN counted;
- the client protocol against a fake bridge (a thread on 127.0.0.1 answering `/ping`), including a timeout with exit code 2;
- the overrides test: `sfrecord~` inlet 1 is signal; the bridge patch validates with 0 errors; the fixtures are not under `generated/`.

Manual-only: everything in the checklist, which needs MAX.

## Security Domain

- **Input validation:** Python refuses any path outside the repo and the temp dir, and only ever opens `__maxbridge_*` copies.
- **Network exposure:** Python binds `127.0.0.1` only. The MAX-side exposure (pitfall 9) is documented and left open for the user to accept or reject.
- **Subprocesses:** argv lists only, never a shell.

## Sources

- **Primary (HIGH):**
  - Max 9.2.0 bundle refpages: `pcontrol`, `error`, `console`, `udpreceive`, `udpsend`, `sfrecord~`, `send~`, `receive~`, `thispatcher`, `max`, `adstatus`;
  - help patches: `pcontrol`, `error`, `console`, `sfrecord~`, `thispatcher`;
  - user guide: `controlling_max_with_messages.json` and `error_messages.json`;
  - the `ObjectDatabase` lookups and the validator prototype run this session;
  - `src/maxpat/dsp_sim/measure.py`, `project.py:364-432`, `hooks.py:145,265,305`.
- **Secondary:** MUSC320 `tools/patch_shot.py` (proven `SHOT PASS` x5 on Max 9.2); `.claude/skills/references/troubleshooting.md` (error wordings).

**Valid until:** the next Max update (re-check the refpages after re-syncing the bundle).
