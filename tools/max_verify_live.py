#!/usr/bin/env python3
"""``/max-verify --live``: load patches in the running MAX 9.2 through the bridge.

After /max-verify's static validation and critic review, this tool loads each
patch through the confirmed max-bridge (tools/max_bridge.py ``check``) and
reports MAX's own console errors, recording flags and screenshots as LIVE
findings. Live findings are report-only: severity-contract.md section 7 maps
them to blocker / warning / note, and they never enter the save gate or the
critic revision loop.

Locked decisions (quick 261021-olv):
    D-01  An audio-input patch (adc~, ezadc~, mc.adc~, mc.ezadc~ anywhere in
          its JSON tree, or in a sibling .maxpat it references) is load-only
          by default; --live-inputs opts it into recording.
    D-02  Every load-only patch gets ``check --dsp-on-load``: DSP goes on just
          before the open so DSP-time errors (gen~ compiles) post during the
          load settle, and the bridge restores the prior DSP state afterwards.
          An audio-input patch never gets it unless --live-inputs is passed.
    D-03  Live counts sit BESIDE the static Summary line, never merged into it.
    D-04  This tool never switches the bridge's enable toggle and never opens
          the bridge patch: the user does both. MAX is reached only through
          bridge.run_check and a read-only Bridge.ping pre-flight.

Severity comes from map_findings, never from the bridge's exit_code/verdict.

Exit codes: 0 ran, notes only; 1 any live blocker or warning; 2 skipped
(no bridge, MAX not running, toggle OFF), aborted (MAX stopped answering
mid-run) or a usage error.

LAN caveat: the bridge listens on UDP 7400 on ALL network interfaces (see the
module docstring of tools/max_bridge.py). Turn its toggle OFF, or close it,
when done; every report ends with that reminder.

Ctrl-C mid-run skips the bridge's cleanup: DSP may stay on and a
``__maxbridge_`` window may stay open in MAX. Close that window WITHOUT saving.

Stdlib plus in-repo imports only; subprocesses use argv lists, never a shell.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Running the script puts tools/ on sys.path[0]: a bare `import max_bridge`
# would make a second module object that test monkeypatches miss (Pitfall 6).
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools import max_bridge as bridge  # noqa: E402

INPUT_BOXES = ("adc~", "ezadc~", "mc.adc~", "mc.ezadc~")
ABSTRACTION_HOSTS = ("poly~", "mc.poly~", "pfft~")
DEFAULT_RECORD_S = 3.0
DEFAULT_NOTE = (60, 100)
REMINDER = ("Turn the bridge's enable toggle OFF (or close the bridge patch) when done: "
            "it listens on UDP 7400 on all network interfaces.")

UNRELIABLE_FLAGS = ("sr_changed_during_run", "short_recording")
UNRELIABLE_SUFFIX = " (measures unreliable: the audio driver restarted or DSP stopped; rerun)"
GEN_SUGGESTION = "gen~ compile error: see genexpr-rules.md (Param/local name clash, declaration order)"
WORDING_SUGGESTIONS = {
    "no such object": ("use a name from the object DB (Rule #1; pd-blocklist.json for PD names); "
                       "see troubleshooting.md"),
    "bad argument": "check the argument form against the DB / refpage; see troubleshooting.md",
    "failed to compile": GEN_SUGGESTION,
    "can't assign": GEN_SUGGESTION,
}
OTHER_ERROR_SUGGESTION = ("runtime or environment error (missing file, port in use) or a post from "
                          "another open patch: close unrelated patches and rerun")
FLAG_SUGGESTIONS = {
    "nonfinite": ("blocker", "NaN/inf or runaway output: check feedback gains and filter stability "
                             "before it reaches speakers"),
    "runaway": ("blocker", "NaN/inf or runaway output: check feedback gains and filter stability "
                           "before it reaches speakers"),
    "clipping": ("warning", "reduce the output gain below 1.0"),
    "dc_offset": ("warning", "add a DC blocker before the dac~"),
    "silent": ("warning", "needs a stimulus (start toggle, file load, note)?"),
}


# ---------------------------------------------------------------------------
# Patch scanning
# ---------------------------------------------------------------------------

def _iter_boxes(node):
    """Every box dict at any depth of a patch JSON (p/patcher subpatchers and
    embedded bpatcher patchers included)."""
    patcher = node.get("patcher") if isinstance(node, dict) else None
    if not isinstance(patcher, dict):
        return
    for entry in patcher.get("boxes") or []:
        box = entry.get("box") if isinstance(entry, dict) else None
        if not isinstance(box, dict):
            continue
        yield box
        yield from _iter_boxes(box)


def _stem(token) -> str:
    name = Path(str(token)).name
    return name[: -len(".maxpat")] if name.endswith(".maxpat") else name


def _references(patch_json, sibling_stems) -> set[str]:
    """The sibling stems *patch_json* references, at any depth.

    Only newobj and bpatcher boxes count (comment and message text never
    does): a bpatcher's ``name``; a newobj whose first token is a sibling
    stem (an abstraction); the first argument of poly~, mc.poly~ or pfft~.
    """
    stems = set(sibling_stems)
    refs: set[str] = set()
    for box in _iter_boxes(patch_json):
        maxclass = box.get("maxclass")
        if maxclass == "bpatcher":
            name = box.get("name")
            if name:
                refs.add(_stem(name))
        elif maxclass == "newobj":
            tokens = str(box.get("text") or "").split()
            if not tokens:
                continue
            if _stem(tokens[0]) in stems:
                refs.add(_stem(tokens[0]))
            elif tokens[0] in ABSTRACTION_HOSTS and len(tokens) > 1 and not tokens[1].startswith("@"):
                refs.add(_stem(tokens[1]))
    return refs & stems


def _input_hits(patch_json, label: str) -> list[str]:
    hits = []
    for box in _iter_boxes(patch_json):
        maxclass = box.get("maxclass")
        tokens = str(box.get("text") or "").split() if maxclass == "newobj" else []
        if maxclass in INPUT_BOXES or (tokens and tokens[0] in INPUT_BOXES):
            hits.append(f"{label}:{box.get('id')}")
    return hits


def _input_scan(path: Path, patch_json) -> list[str]:
    """``file:box-id`` of every audio-input box in *path* and, transitively,
    in every sibling .maxpat it references (D-01, feedback safety)."""
    siblings = {q.stem: q for q in path.parent.glob("*.maxpat")
                if not q.name.startswith(bridge.COPY_PREFIX)}
    visited = {path.stem}
    queue = [(path, patch_json)]
    where: list[str] = []
    while queue:
        q, data = queue.pop(0)
        where += _input_hits(data, q.name)
        for stem in sorted(_references(data, siblings)):
            if stem in visited:
                continue
            visited.add(stem)
            try:
                child = json.loads(siblings[stem].read_text())
            except (OSError, ValueError):
                continue
            queue.append((siblings[stem], child))
    return where


def scan_patch(path) -> dict:
    """Option-rule inputs for one patch; nothing is written.

    tapped / unsupported / note_kind come from the bridge's own
    _instrument_patcher and _inject_note run on a throwaway in-memory
    Patcher, so the choice never disagrees with what ``check`` taps.
    inputs / input_where come from the wider raw-JSON audio-input scan.
    """
    from src.maxpat.patcher import Patcher

    path = Path(path)
    data = json.loads(path.read_text())
    p = Patcher.from_dict(data)
    scratch: dict = {"taps": {"L": 0, "R": 0}, "tap_boxes": [], "unsupported": [],
                     "warnings": [], "note_target": None}
    bridge._instrument_patcher(p, "top", scratch)
    bridge._inject_note(p, scratch)
    where = _input_scan(path, data)
    target = scratch["note_target"]
    return {
        "tapped": scratch["taps"]["L"] + scratch["taps"]["R"] > 0,
        "unsupported": sorted({u["name"] for u in scratch["unsupported"]}),
        "note_kind": target["kind"] if target else None,
        "inputs": bool(where),
        "input_where": where,
    }


def _audio_input_locked(scan: dict, opts) -> bool:
    return bool(scan["inputs"]) and not getattr(opts, "live_inputs", False)


def check_argv(path, scan: dict, opts) -> tuple[list[str], str, list[str]]:
    """``(argv for bridge.build_parser(), mode, reasons)`` for one patch (D-01/D-02)."""
    argv = ["check", str(path)]
    for flag, attr in (("--port", "port"), ("--reply-port", "reply_port"),
                       ("--timeout", "timeout"), ("--settle", "settle"),
                       ("--load-timeout", "load_timeout")):
        value = getattr(opts, attr, None)
        if value is not None:
            argv += [flag, str(value)]
    if not getattr(opts, "no_shot", False) and sys.platform == "darwin":
        argv.append("--shot")

    reasons: list[str] = []
    locked = _audio_input_locked(scan, opts)
    record = getattr(opts, "record", None)
    mode = "load-only"
    if record is not None and record == 0:
        reasons.append("record disabled (--record 0)")
    elif locked:
        reasons.append("record skipped: audio-input patch (feedback risk, no stimulus); "
                       "--live-inputs opts in")
    elif not scan["tapped"]:
        why = ", ".join(scan["unsupported"]) or \
            "no dac~/ezdac~ cord at the top level or in a p subpatcher"
        reasons.append(f"output not tapped ({why})")
    else:
        mode = "record"
        seconds = record or DEFAULT_RECORD_S
        argv += ["--record", str(seconds)]
        reasons.append(f"record {seconds:g} s")
        if scan["note_kind"]:
            pitch, vel = getattr(opts, "note", None) or DEFAULT_NOTE
            argv += ["--note", str(pitch), str(vel)]
            reasons.append(f"note {pitch} {vel} into the {scan['note_kind']}")

    if mode == "load-only" and not locked:
        argv.append("--dsp-on-load")
        reasons.append("DSP on during the load settle (restored afterwards)")
    elif locked:
        reasons.append("DSP not switched on: audio-input patch (feedback safety); "
                       "--live-inputs opts in")
    return argv, mode, reasons


# ---------------------------------------------------------------------------
# Pre-flight (read-only)
# ---------------------------------------------------------------------------

def _max_running() -> bool | None:
    """True/False from ``pgrep -x Max`` on macOS; None when it cannot tell."""
    if sys.platform != "darwin":
        return None
    try:
        proc = subprocess.run(["pgrep", "-x", "Max"], capture_output=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode == 0:
        return True
    if proc.returncode == 1:
        return False
    return None


def _net(opts) -> tuple[int, int, float]:
    port = getattr(opts, "port", None)
    reply = getattr(opts, "reply_port", None)
    timeout = getattr(opts, "timeout", None)
    return (bridge.BRIDGE_PORT if port is None else port,
            bridge.REPLY_PORT if reply is None else reply,
            bridge.DEFAULT_TIMEOUT if timeout is None else timeout)


def preflight(opts) -> str | None:
    """None when the bridge answers; else the skip hint. Writes nothing.

    The hint for a closed bridge (or the toggle OFF) is the bridge's own:
    it tells the user to turn the toggle ON. This tool never does (D-04).
    """
    if not bridge.BRIDGE_PATCH.is_file():
        return "bridge patch not available in this install (patches/ is not shipped in releases)"
    if _max_running() is False:
        return ("MAX is not running: start MAX 9.2, open "
                "patches/max-bridge/generated/max-bridge.maxpat and turn ON its enable toggle")
    port, reply, timeout = _net(opts)
    try:
        with bridge.Bridge(bridge.HOST, port, reply, timeout) as b:
            b.ping(timeout)
    except bridge.BridgeError as exc:
        return bridge._bridge_hint(bridge.HOST, port) + f" ({exc})"
    return None


# ---------------------------------------------------------------------------
# Severity mapping (severity-contract.md section 7)
# ---------------------------------------------------------------------------

def _row(severity: str, finding: str, suggestion: str = "") -> dict:
    return {"severity": severity, "finding": finding, "suggestion": suggestion, "source": "live"}


def map_findings(report: dict) -> list[dict]:
    """Live findings of one ``bridge.run_check`` report (section 7 table).

    Never derived from report["exit_code"] / report["verdict"]: the bridge
    counts unsupported outputs and shot failures as findings, here they are
    notes.
    """
    rows: list[dict] = []
    for d in report.get("errors_distinct") or []:
        key = str(d.get("key", ""))
        finding = f"MAX console: {key} (x{d.get('occurrences', 1)})"
        if bridge._is_error_text(key):
            low = key.lower()
            wording = next(w for w in bridge.ERROR_WORDINGS if w in low)
            rows.append(_row("blocker", finding,
                             WORDING_SUGGESTIONS.get(wording, "see troubleshooting.md")))
        else:
            rows.append(_row("warning", finding, OTHER_ERROR_SUGGESTION))

    record = report.get("record")
    flags: list[str] = []
    if record:
        flags = list(record.get("flags") or [])
        unreliable = bool(set(UNRELIABLE_FLAGS) & set(flags))
        for flag in flags:
            if unreliable:
                rows.append(_row("note", f"record flag {flag}{UNRELIABLE_SUFFIX}",
                                 "rerun with the audio driver steady and DSP left alone"))
                continue
            severity, suggestion = FLAG_SUGGESTIONS.get(flag, ("warning", ""))
            rows.append(_row(severity, f"record flag {flag}", suggestion))
        for w in record.get("warnings") or []:
            if str(w).split(":", 1)[0].strip() in flags:
                continue
            rows.append(_row("note", str(w)))
    for w in report.get("warnings") or []:
        rows.append(_row("note", str(w)))
    for u in report.get("unsupported") or []:
        rows.append(_row("note", f"not tapped: {u.get('name')} at {u.get('path')}",
                         "coverage gap, not a defect: the output is not recorded"))
    shot = report.get("shot")
    if shot and "error" in shot:
        rows.append(_row("note", f"screenshot failed: {shot['error']}",
                         "grant Screen Recording to the terminal app "
                         "(System Settings > Privacy & Security)"))
    if report.get("closed") is False:
        rows.append(_row("warning", "the temp copy's window may still be open in MAX",
                         "close it WITHOUT saving"))
    if report.get("feedback_suspected"):
        rows.append(_row("warning",
                         "event cap tripped (console flood): the error list may be incomplete",
                         "find the patch posting in a loop and rerun"))
    return rows


# ---------------------------------------------------------------------------
# The run
# ---------------------------------------------------------------------------

def _entry(path: Path) -> dict:
    return {"patch": str(path), "name": path.name, "status": "not checked", "mode": None,
            "argv": None, "reasons": [], "findings": [], "shot_png": None, "run_dir": None,
            "record": None, "dsp_before": None, "verdict": None}


def _finish(result: dict, status: str | None = None, hint: str | None = None) -> dict:
    if status is not None:
        result["status"] = status
    if hint is not None:
        result["hint"] = hint
    counts = {"blocker": 0, "warning": 0, "note": 0}
    for entry in result["patches"]:
        for f in entry["findings"]:
            counts[f["severity"]] = counts.get(f["severity"], 0) + 1
    result["counts"] = counts
    if result["status"] in ("skipped", "aborted"):
        result["exit_code"] = 2
    elif counts["blocker"] + counts["warning"] > 0:
        result["exit_code"] = 1
    else:
        result["exit_code"] = 0
    return result


def run_live(patches, opts, *, project=None, excluded=None) -> dict:
    """Check *patches* one after another in the running MAX; return the result.

    Strictly sequential (one reply port, one sfrecord~). A skip (no bridge,
    MAX down, no answer) returns before any run_check, so no
    ``__maxbridge_*`` copy is ever written. The first bridge_failed after a
    good pre-flight aborts the run; an exception in one patch becomes a
    warning and the loop goes on.
    """
    result: dict = {
        "status": "ran", "hint": None, "project": project, "patches": [],
        "excluded": list(excluded or []), "notes": [],
        "counts": {"blocker": 0, "warning": 0, "note": 0},
        "reminder": REMINDER, "exit_code": 0,
    }
    paths = [Path(p) for p in patches]
    if not paths:
        return _finish(result, "skipped", "no top-level .maxpat to check")
    hint = preflight(opts)
    if hint:
        return _finish(result, "skipped", hint)

    result["patches"] = [_entry(p) for p in paths]
    total = len(paths)
    for i, entry in enumerate(result["patches"]):
        path = Path(entry["patch"])
        try:
            scan = scan_patch(path)
            argv, mode, reasons = check_argv(path, scan, opts)
            entry.update(mode=mode, argv=argv, reasons=reasons)
            print(f"[{i + 1}/{total}] {entry['name']}: {mode} ({'; '.join(reasons)})",
                  file=sys.stderr)
            args = bridge.build_parser().parse_args(argv)
            report = bridge.run_check(args)
        except Exception as exc:  # one broken patch must not end the batch
            entry["status"] = "failed"
            entry["findings"].append(_row("warning", f"live check crashed: {exc!r}",
                                          "run tools/max_bridge.py check on it alone"))
            print(f"[{i + 1}/{total}] {entry['name']}: crashed ({exc!r})", file=sys.stderr)
            continue

        entry.update(run_dir=report.get("run_dir"), record=report.get("record"),
                     dsp_before=report.get("dsp_before"), verdict=report.get("verdict"))
        if report.get("verdict") == "bridge_failed":
            if report.get("copy") is None:
                entry["status"] = "refused"
                entry["findings"].append(_row("note", str(report.get("error"))))
                continue
            entry["status"] = "failed"
            return _finish(
                result, "aborted",
                f"MAX stopped answering during {entry['name']} ({report.get('error')}): "
                "a modal dialog, a crash, or the enable toggle switched OFF")

        entry["status"] = "checked"
        entry["findings"] = map_findings(report)
        if _audio_input_locked(scan, opts) and report.get("dsp_before") == 1:
            entry["findings"].append(_row(
                "note", "DSP was already on: the copy's audio input was live during the load",
                "switch DSP off before a live run, or pass --live-inputs deliberately"))
        shot = report.get("shot")
        if shot and "error" not in shot:
            entry["shot_png"] = shot.get("png")
    return _finish(result)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="max_verify_live.py",
        description="/max-verify --live: load patches in the running MAX 9.2 through the "
                    "max-bridge and report MAX's own errors (report-only, severity-contract §7).",
    )
    parser.add_argument("patches", nargs="*", metavar="PATCH",
                        help="explicit .maxpat files (default: the active project's top-level patches)")
    parser.add_argument("--record", type=float, default=None, metavar="S",
                        help=f"seconds to record a tapped patch (default {DEFAULT_RECORD_S:g}; "
                             "0 = never record)")
    parser.add_argument("--note", nargs=2, type=int, default=None, metavar=("P", "V"),
                        help=f"note played into notein (else the first kslider) while recording "
                             f"(default {DEFAULT_NOTE[0]} {DEFAULT_NOTE[1]})")
    parser.add_argument("--no-shot", action="store_true", help="no screenshot")
    parser.add_argument("--live-inputs", action="store_true",
                        help="record audio-input patches and allow DSP-on-load for them "
                             "(mute mics or use headphones)")
    parser.add_argument("--settle", type=float, default=None,
                        help="bridge check --settle (default: the bridge's)")
    parser.add_argument("--load-timeout", type=float, default=None,
                        help="bridge check --load-timeout (default: the bridge's)")
    parser.add_argument("--port", type=int, default=None,
                        help=f"bridge UDP port (default {bridge.BRIDGE_PORT})")
    parser.add_argument("--reply-port", type=int, default=None,
                        help=f"local reply port (default {bridge.REPLY_PORT}; 0 = ephemeral)")
    parser.add_argument("--timeout", type=float, default=None,
                        help=f"seconds to wait for a /pong (default {bridge.DEFAULT_TIMEOUT:g})")
    parser.add_argument("--json", action="store_true", help="print the JSON result")
    return parser


def _explicit(paths: list[str]) -> tuple[list[Path], list[dict]]:
    keep: list[Path] = []
    excluded: list[dict] = []
    for raw in paths:
        p = Path(raw)
        if p.name.startswith(bridge.COPY_PREFIX):
            excluded.append({"patch": raw, "reason": "bridge temp copy"})
        elif p.suffix != ".maxpat":
            excluded.append({"patch": raw, "reason": "not a .maxpat"})
        elif not p.is_file():
            excluded.append({"patch": raw, "reason": "does not exist"})
        else:
            keep.append(p.resolve())
    return keep, excluded


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    opts = parser.parse_args(argv)
    if opts.record is not None and opts.record < 0:
        parser.error("--record must be 0 (never record) or a positive number of seconds")
    if opts.note is not None:
        pitch, vel = opts.note
        if not 0 <= pitch <= 127:
            parser.error(f"--note pitch {pitch} is outside 0-127")
        if not 1 <= vel <= 127:
            parser.error(f"--note velocity {vel} is outside 1-127")

    if not opts.patches:
        print("no PATH given", file=sys.stderr)
        return 2
    patches, excluded = _explicit(opts.patches)
    result = run_live(patches, opts, excluded=excluded)
    print(json.dumps(result, indent=2, default=str))
    return result["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
