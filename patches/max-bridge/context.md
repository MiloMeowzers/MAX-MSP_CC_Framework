# max-bridge

**Spike (Q34, quick 261016-uy1).** There is no `/max-verify` integration until the user confirms the bridge works in MAX (see `test-results/v0.1.0-bridge-checklist.md`).

## Purpose

"Pending test in MAX" is the bottleneck in most projects. The bridge lets Python drive a running MAX 9.2:
- open a patch;
- capture the console errors raised while it loads;
- record N seconds of its output for dsp_sim analysis;
- screenshot its window.

The spike's job is to find out which of these mechanisms actually work.

Design source: `.planning/quick/261016-uy1-implement-q34-in-planning-reviews-2026-1/261016-uy1-RESEARCH.md`. That file is not committed; the summary below is the durable copy.

## Pieces

- `generated/max-bridge.maxpat`: the resident bridge patch. Open it in MAX and leave it open while `tools/max_bridge.py` runs.
- `tools/max_bridge.py` (repo root): the client, with the `ping`, `check` and `analyze` subcommands.
- `tests/test_max_bridge.py`: hermetic tests that run against an in-process fake bridge. No MAX is needed.

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

MAX -> Python (UDP 7401):
- `/err error <words...>`, from `error`;
- `/con/obj`, `/con/msg`, `/con/type`, from console outlets 0, 1 and 2, each through its gate.

`udpreceive` -> `deferlow` puts loads on the low-priority queue and keeps `/open` then `/ping` in order.

Audio: `receive~ __maxbridge_L` / `__maxbridge_R` -> `sfrecord~ 2` -> `snapshot~ 100` -> number box (elapsed ms).

## Temp-copy policy

`check` never opens the patch under test. Instead, `instrument()` writes a sibling copy, `__maxbridge_<stem>.maxpat`, built with the Patcher API, and adds to it:
- `send~ __maxbridge_L/R` taps on every `dac~`/`ezdac~` input source (the existing cords are kept);
- a cordless close hook: `receive __maxbridge_close` -> `clean, wclose` -> `thispatcher`.

The copy is written with `format_patch_text` + `atomic_write_bytes`, not `save_patch_roundtrip`: it is ephemeral, so it is neither committed nor gated (research A6). It is deleted in a `finally`, and `__maxbridge_*` is in `.gitignore` so a leftover copy can never be swept into a project auto-commit. Placing it as a sibling keeps relative lookups working (`.gendsp`, js, abstractions, audio files).

The original file is never written.

## Fixture-writer policy

Fixtures live in `fixtures/`, never in `generated/`: `tests/test_integration_patches.py` fails on blockers in `generated/`. There are two writers:
- **Writer A** (`save_patch_roundtrip`, auto-commits, save gate): for fixtures that are valid patches.
- **Writer B** (`format_patch_text` -> `atomic_write_bytes` -> `auto_commit_patch(files=[...])`): for deliberate-error fixtures, which the gate exists to refuse.

No allowlist entries are added for either.

## LAN caveat

`udpreceive` has no bind-host option, so the bridge listens on UDP 7400 on **all** network interfaces. Any host on the network can send `/open`, and a patch containing js or node.script amounts to code execution.
- Close the bridge patch when it is not in use.
- Deny incoming connections if macOS asks.

The Python client binds 127.0.0.1 only. A host filter or kill switch is an open question (`open-questions.md`).

## Presentation mode

None. The bridge is a utility patch with no user-facing controls, so Rule #9 does not apply.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | clean |
| 1 | findings: error lines, analysis flags, unsupported outputs, shot failure, feedback cap |
| 2 | bridge failure: no `/pong`, timeout, bind failure, a wav that never settles, refused input |
