#!/usr/bin/env python3
"""Drive a running MAX 9.2 from Python through a resident bridge patch (Q34 spike).

SPIKE STATUS: nothing here is confirmed in MAX yet. The manual checklist at
patches/max-bridge/test-results/v0.1.0-bridge-checklist.md is how the user
confirms (or refutes) each mechanism; patches/max-bridge/open-questions.md
lists what only MAX can answer. There is no /max-verify integration until
the user confirms the bridge works.

Protocol. The bridge patch (patches/max-bridge/generated/max-bridge.maxpat)
is a dumb UDP pass-through; this client owns all the sequencing:

    Python -> MAX  (OSC over UDP to 127.0.0.1:7400)
      /ping                 -> /pong reply (the ordering barrier)
      /open <abs path>      -> prepend load -> pcontrol
      /openfile <abs path>  -> ; max openfile maxbridge $1   (variant B)
      /closefile            -> ; max closefile maxbridge
      /sf <msg...>          -> sfrecord~ 2 (samptype, open, record, 0)
      /console <msg...>     -> console (write <file>, showonlyerrors 0|1)
      /listen 1|0           -> error on/off and the console gates
      /dsp 1|0              -> ; dsp start / ; dsp stop
      /close                -> ; __maxbridge_close bang  (the copy closes itself)

    MAX -> Python  (OSC over UDP to 127.0.0.1:7401)
      /err error <words...>     from error
      /con/obj, /con/msg, /con/type   from console outlets 0, 1, 2

The bridge's deferlow keeps commands in order, so the /pong after an /open
means "the load returned".

Subcommands:
    python3 tools/max_bridge.py ping
    python3 tools/max_bridge.py check PATCH.maxpat [--settle S] [--record N]
        [--shot [PNG]] [--open-mode pcontrol|openfile] [--console-all]
        [--leave-dsp-on] [--load-timeout S] [--dry-run]
    python3 tools/max_bridge.py analyze OUT.wav [--channels L,R]

Exit codes (house convention, tools/audit_db.py): 0 clean, 1 findings
(errors, analysis flags, unsupported outputs, shot failure, feedback cap),
2 bridge failure (MAX not answering, timeout, bad input).

LAN CAVEAT: udpreceive has no bind-host option, so the bridge patch listens
on UDP 7400 on ALL network interfaces. Any host on the network can send it
/open, and a patch with js or node.script is code execution. Close the
bridge patch when not in use and deny incoming connections if macOS asks.
This client binds 127.0.0.1 only.

Stdlib only plus the declared numpy and scipy; subprocesses use argv lists,
never a shell.
"""

from __future__ import annotations

import argparse
import socket
import struct
import sys
import time
from pathlib import Path

# Project root: this file is at tools/max_bridge.py
REPO_ROOT = Path(__file__).resolve().parent.parent

# Allow `from src.maxpat...` when run as a script
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

BRIDGE_PORT = 7400
REPLY_PORT = 7401
HOST = "127.0.0.1"
# route arguments of the bridge patch, in outlet order (TestBridgePatch pins it)
ROUTE_ADDRESSES = (
    "/ping", "/open", "/sf", "/console", "/dsp", "/listen",
    "/close", "/openfile", "/closefile",
)
TAP_L = "__maxbridge_L"
TAP_R = "__maxbridge_R"
CLOSE_RECEIVE = "__maxbridge_close"
COPY_PREFIX = "__maxbridge_"
BRIDGE_PATCH = REPO_ROOT / "patches" / "max-bridge" / "generated" / "max-bridge.maxpat"

DEFAULT_TIMEOUT = 2.0
MAX_EVENTS = 1000
_RCVBUF = 1 << 20


# ---------------------------------------------------------------------------
# OSC codec (stdlib)
# ---------------------------------------------------------------------------

def _osc_string(s: str) -> bytes:
    """NUL-terminated UTF-8, padded to a multiple of 4 bytes."""
    b = s.encode("utf-8")
    return b + b"\0" * (4 - len(b) % 4)


def osc_encode(address: str, *args) -> bytes:
    """One OSC message: address, type tags, arguments.

    int -> ``i`` (big-endian int32), float -> ``f`` (float32), str -> ``s``.
    """
    tags = ","
    payload = b""
    for a in args:
        if isinstance(a, bool):
            a = int(a)
        if isinstance(a, int):
            tags += "i"
            payload += struct.pack(">i", a)
        elif isinstance(a, float):
            tags += "f"
            payload += struct.pack(">f", a)
        elif isinstance(a, str):
            tags += "s"
            payload += _osc_string(a)
        else:
            raise TypeError(f"OSC argument {a!r}: only int, float and str are encoded")
    return _osc_string(address) + _osc_string(tags) + payload


def _read_string(packet: bytes, pos: int) -> tuple[str, int]:
    end = packet.find(b"\0", pos)
    if end < 0:
        raise ValueError("OSC string is not NUL-terminated (truncated packet)")
    nxt = (end + 4) & ~3
    if nxt > len(packet):
        raise ValueError("OSC string padding runs past the packet end")
    return packet[pos:end].decode("utf-8", errors="replace"), nxt


def _take(packet: bytes, pos: int, n: int) -> bytes:
    if pos + n > len(packet):
        raise ValueError("OSC argument runs past the packet end (truncated packet)")
    return packet[pos:pos + n]


def osc_decode(packet: bytes):
    """``(address, [args])`` for one OSC message, or None for a ``#bundle``.

    Accepts the tags ``i f d h s S T F N``. Raises ValueError on a truncated
    or malformed packet.
    """
    if packet.startswith(b"#bundle"):
        return None
    address, pos = _read_string(packet, 0)
    if not address.startswith("/"):
        raise ValueError(f"not an OSC address: {address!r}")
    if pos >= len(packet):
        return address, []
    tags, pos = _read_string(packet, pos)
    if not tags.startswith(","):
        raise ValueError(f"OSC type tag string must start with ',': {tags!r}")
    args: list = []
    for tag in tags[1:]:
        if tag == "i":
            args.append(struct.unpack(">i", _take(packet, pos, 4))[0])
            pos += 4
        elif tag == "f":
            args.append(struct.unpack(">f", _take(packet, pos, 4))[0])
            pos += 4
        elif tag == "d":
            args.append(struct.unpack(">d", _take(packet, pos, 8))[0])
            pos += 8
        elif tag == "h":
            args.append(struct.unpack(">q", _take(packet, pos, 8))[0])
            pos += 8
        elif tag in ("s", "S"):
            s, pos = _read_string(packet, pos)
            args.append(s)
        elif tag == "T":
            args.append(True)
        elif tag == "F":
            args.append(False)
        elif tag == "N":
            args.append(None)
        else:
            raise ValueError(f"unsupported OSC type tag {tag!r}")
    return address, args


# ---------------------------------------------------------------------------
# Bridge client
# ---------------------------------------------------------------------------

class BridgeError(RuntimeError):
    """The bridge cannot be reached or used (bind failure, socket error)."""


class BridgeTimeout(BridgeError):
    """No /pong arrived in time: MAX is not running or the bridge is closed."""


class Bridge:
    """UDP client of the bridge patch.

    Binds an unconnected socket on 127.0.0.1:reply_port (0 = ephemeral;
    ``self.reply_port`` is the bound port) and sends with sendto, so a closed
    bridge port times out instead of raising connection-refused. Every
    non-/pong packet received is appended to ``events`` as
    ``(t, address, args)`` (t in seconds since the Bridge was made) until
    MAX_EVENTS; then ``/listen 0`` is sent once, ``feedback_suspected`` is
    set and further events are dropped.
    """

    def __init__(self, host: str = HOST, port: int = BRIDGE_PORT,
                 reply_port: int = REPLY_PORT, timeout: float = DEFAULT_TIMEOUT,
                 max_events: int = MAX_EVENTS) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.max_events = max_events
        self.events: list[tuple[float, str, list]] = []
        self.sent: list[tuple[str, tuple]] = []
        self.feedback_suspected = False
        self.t0 = time.monotonic()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, _RCVBUF)
        except OSError:
            pass
        try:
            self.sock.bind(("127.0.0.1", reply_port))
        except OSError as exc:
            self.sock.close()
            raise BridgeError(f"cannot bind reply port 127.0.0.1:{reply_port}: {exc}") from None
        self.reply_port = self.sock.getsockname()[1]

    def __enter__(self) -> "Bridge":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def close(self) -> None:
        self.sock.close()

    def now(self) -> float:
        return time.monotonic() - self.t0

    def send(self, address: str, *args) -> None:
        """Send one OSC message. /open and /openfile only take a COPY_PREFIX file."""
        if address in ("/open", "/openfile"):
            if not args or not Path(str(args[0])).name.startswith(COPY_PREFIX):
                raise ValueError(
                    f"{address} refused: only {COPY_PREFIX}* temp copies are opened, got {args!r}"
                )
        try:
            self.sock.sendto(osc_encode(address, *args), (self.host, self.port))
        except OSError as exc:
            raise BridgeError(f"send to {self.host}:{self.port} failed: {exc}") from None
        self.sent.append((address, tuple(args)))

    def _recv(self, deadline: float):
        """One decoded message before *deadline*, or None at the deadline."""
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return None
            self.sock.settimeout(remaining)
            try:
                data, _addr = self.sock.recvfrom(65536)
            except socket.timeout:
                return None
            except ConnectionRefusedError:
                continue  # an ICMP port-unreachable on some platforms: keep waiting
            except OSError as exc:
                raise BridgeError(f"receive on 127.0.0.1:{self.reply_port} failed: {exc}") from None
            try:
                msg = osc_decode(data)
            except ValueError:
                continue
            if msg is not None:
                return msg

    def _record(self, address: str, args: list) -> None:
        if self.feedback_suspected:
            return
        if len(self.events) >= self.max_events:
            self.feedback_suspected = True
            try:
                self.send("/listen", 0)
            except BridgeError:
                pass
            return
        self.events.append((round(self.now(), 4), address, list(args)))

    def collect(self, seconds: float) -> None:
        """Receive (and record) events for *seconds*."""
        deadline = time.monotonic() + max(0.0, seconds)
        while True:
            msg = self._recv(deadline)
            if msg is None:
                return
            if msg[0] != "/pong":
                self._record(*msg)

    def ping(self, timeout: float | None = None) -> float:
        """Send /ping, wait for /pong; return the latency in seconds.

        Events arriving meanwhile are recorded. Raises BridgeTimeout.
        """
        timeout = self.timeout if timeout is None else timeout
        start = time.monotonic()
        self.send("/ping")
        deadline = start + timeout
        while True:
            msg = self._recv(deadline)
            if msg is None:
                raise BridgeTimeout(
                    f"no /pong from {self.host}:{self.port} within {timeout:g} s"
                )
            if msg[0] == "/pong":
                return time.monotonic() - start
            self._record(*msg)


# ---------------------------------------------------------------------------
# Temp-copy instrumentation
# ---------------------------------------------------------------------------

OUTPUT_BOXES = ("dac~", "ezdac~")
UNSUPPORTED_OUTPUTS = ("mc.dac~", "plugout~", "poly~", "pfft~")
_UNSUPPORTED_REASON = "external or multichannel output is not tapped in the spike"


def copy_path_for(src: Path) -> Path:
    """The sibling temp copy ``__maxbridge_<stem>.maxpat`` of *src*."""
    return src.parent / f"{COPY_PREFIX}{src.stem}.maxpat"


def _dac_channel(box, inlet: int) -> int | None:
    """The output channel a cord into *box* inlet *inlet* plays on."""
    if box.name == "ezdac~":
        return inlet + 1 if inlet in (0, 1) else None
    args = [a for a in box.text.split()[1:] if not a.startswith("@")]
    if not args:
        return inlet + 1
    if inlet >= len(args):
        return None
    try:
        return int(float(args[inlet]))
    except ValueError:
        return None


def _instrument_patcher(p, path: str, report: dict) -> None:
    by_id = {b.id: b for b in p.boxes}
    for box in list(p.boxes):
        if box.name in UNSUPPORTED_OUTPUTS or box.maxclass == "bpatcher":
            report["unsupported"].append({
                "box_id": box.id, "path": path,
                "name": "bpatcher" if box.maxclass == "bpatcher" else box.name,
                "reason": _UNSUPPORTED_REASON,
            })
        elif box.name in ("p", "patcher") and box._inner_patcher is not None:
            _instrument_patcher(box._inner_patcher, f"{path}/{box.id}", report)

    if not p.boxes:
        return
    right = max(b.right_edge for b in p.boxes) + 30.0
    top = min(b.patching_rect[1] for b in p.boxes)
    sends: dict[str, object] = {}
    warned: set = set()
    for line in list(p.lines):
        dst = by_id.get(line.dest_id)
        src = by_id.get(line.source_id)
        if dst is None or src is None or dst.name not in OUTPUT_BOXES:
            continue
        ch = _dac_channel(dst, line.dest_inlet)
        side = {1: "L", 2: "R"}.get(ch)
        if side is None:
            if (dst.id, ch) not in warned:
                warned.add((dst.id, ch))
                report["warnings"].append(
                    f"{path}/{dst.id} {dst.text!r} inlet {line.dest_inlet} plays channel "
                    f"{ch}: only channels 1 and 2 are recorded, not tapped")
            continue
        if side not in sends:
            tap = TAP_L if side == "L" else TAP_R
            sends[side] = p.add_box("send~", [tap], x=right,
                                    y=top + (0 if side == "L" else 30),
                                    skip_overlap_check=True)
        p.add_connection(src, line.source_outlet, sends[side], 0)
        report["taps"][side] += 1


def instrument(src: Path) -> tuple[Path, dict]:
    """Write the instrumented sibling copy of *src*; return (copy_path, report).

    The copy adds ``send~ __maxbridge_L/R`` taps fed from every dac~/ezdac~
    input source (channel 1 -> L, 2 -> R; existing cords untouched), in the
    top patcher and every embedded ``p`` subpatcher, plus a cordless close
    hook (``receive __maxbridge_close`` -> ``clean, wclose`` ->
    ``thispatcher``) at the top level. It is built with the Patcher API and
    written with format_patch_text + atomic_write_bytes, never
    save_patch_roundtrip: the copy is ephemeral, gitignored and deleted by
    the caller (research A6). The source file is only read.

    Report keys: taps {L, R} (cords tapped), unsupported (mc.dac~, plugout~,
    poly~, pfft~, bpatcher boxes), warnings (channels above 2),
    no_output_tap, close_hook.
    """
    import json

    from src.maxpat.atomic_io import atomic_write_bytes
    from src.maxpat.hooks import format_patch_text
    from src.maxpat.patcher import Patcher

    src = Path(src)
    text = src.read_text()
    p = Patcher.from_dict(json.loads(text))
    report: dict = {"taps": {"L": 0, "R": 0}, "unsupported": [], "warnings": [],
                    "no_output_tap": False, "close_hook": False}
    _instrument_patcher(p, "top", report)

    right = (max(b.right_edge for b in p.boxes) if p.boxes else 0.0) + 30.0
    top = min((b.patching_rect[1] for b in p.boxes), default=20.0) + 70.0
    rcv = p.add_box("receive", [CLOSE_RECEIVE], x=right, y=top, skip_overlap_check=True)
    msg = p.add_message("clean, wclose", x=right, y=top + 40)
    tp = p.add_box("thispatcher", x=right, y=top + 80, skip_overlap_check=True)
    p.add_connection(rcv, 0, msg, 0)
    p.add_connection(msg, 0, tp, 0)
    report["close_hook"] = True
    report["no_output_tap"] = report["taps"]["L"] + report["taps"]["R"] == 0

    copy = copy_path_for(src)
    atomic_write_bytes(copy, format_patch_text(p.to_dict(), text).encode("utf-8"))
    return copy, report


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

DC_OFFSET_LIMIT = 0.01  # [ASSUMED] research A5: tune after real runs
END_TRIM_MS = 50  # sfrecord~ endramp default is undocumented (research pitfall 6)


def analyze(wav: Path, channels: list[str] | None = None) -> dict:
    """dsp_sim measures of a recorded wav, per channel (index 0 = L, 1 = R).

    NaN and inf are counted on the whole channel; the metrics come from the
    finite samples left after trimming ClassifierThresholds().settle_ms from
    the start and END_TRIM_MS from the end. Flags: nonfinite, runaway
    (peak > runaway_amplitude), clipping (peak > 1.0), silent (ac_rms <
    amplitude_floor), dc_offset (|dc| > DC_OFFSET_LIMIT).
    """
    import numpy as np
    from scipy.io import wavfile

    from src.maxpat.dsp_sim.measure import (
        ClassifierThresholds, measure_ac_rms, measure_fundamental, measure_peak, measure_rms,
    )

    th = ClassifierThresholds()
    sr, x = wavfile.read(str(wav))
    x = np.asarray(x)
    if x.ndim == 1:
        x = x[:, None]
    warnings_out: list[str] = []
    if x.dtype.kind == "u":
        half = float(2 ** (8 * x.dtype.itemsize - 1))
        x = (x.astype(np.float64) - half) / half
        warnings_out.append(f"integer wav ({x.dtype}): scaled to float; NaN is undetectable")
    elif x.dtype.kind == "i":
        scale = float(2 ** (8 * x.dtype.itemsize - 1))
        warnings_out.append(f"integer wav ({x.dtype}): scaled to float; NaN is undetectable")
        x = x.astype(np.float64) / scale
    else:
        x = x.astype(np.float64)

    names = ["L", "R"] + [f"ch{i + 1}" for i in range(2, x.shape[1])]
    names = names[:x.shape[1]]
    wanted = names if channels is None else [c for c in names if c in channels]
    n = x.shape[0]
    start = int(sr * th.settle_ms / 1000)
    end = max(start, n - int(sr * END_TRIM_MS / 1000))
    out: dict = {}
    for i, name in enumerate(names):
        if name not in wanted:
            continue
        col = x[:, i]
        nan = int(np.isnan(col).sum())
        inf = int(np.isinf(col).sum())
        seg = col[start:end]
        seg = seg[np.isfinite(seg)]
        m = {
            "nan": nan,
            "inf": inf,
            "peak": measure_peak(seg),
            "rms": measure_rms(seg),
            "ac_rms": measure_ac_rms(seg),
            "dc": float(np.mean(seg)) if seg.size else 0.0,
            "pitch_hz": measure_fundamental(seg, sr),
        }
        flags = []
        if nan or inf:
            flags.append("nonfinite")
        if m["peak"] > th.runaway_amplitude:
            flags.append("runaway")
        if m["peak"] > 1.0:
            flags.append("clipping")
        if m["ac_rms"] < th.amplitude_floor:
            flags.append("silent")
        if abs(m["dc"]) > DC_OFFSET_LIMIT:
            flags.append("dc_offset")
        m["flags"] = flags
        out[name] = m
    return {
        "wav": str(wav),
        "sample_rate": int(sr),
        "seconds": round(n / float(sr), 4) if sr else 0.0,
        "channels": out,
        "flags": sorted({f for m in out.values() for f in m["flags"]}),
        "warnings": warnings_out,
    }


# ---------------------------------------------------------------------------
# Screenshot
# ported from MUSC320 tools/patch_shot.py @ 1009e5c (_CG_WINDOWS_JXA, _osascript,
# cg_windows, _find_window, _wait_window, _wait_gone, _capture); the
# presentation keystroke and the AX close button are deliberately not ported.
# ---------------------------------------------------------------------------

APP = "Max"
SHOT_LOAD_SETTLE = 1.0
SHOT_POLL = 0.5
SHOT_TITLE_TIMEOUT = 10.0
OSA_TIMEOUT = 15

# CoreGraphics window list: every layer-0 (document) window owned by Max, with
# its window id and bounds. kCGWindowListOptionAll = 0, kCGNullWindowID = 0.
_CG_WINDOWS_JXA = '''
ObjC.import("CoreGraphics");
var arr = ObjC.castRefToObject($.CGWindowListCopyWindowInfo(0, 0));
var info = ObjC.deepUnwrap(arr) || [];
var out = [];
for (var i = 0; i < info.length; i++) {
  var w = info[i];
  if (w.kCGWindowOwnerName === "{app}" && w.kCGWindowLayer === 0) {
    var b = w.kCGWindowBounds;
    out.push([w.kCGWindowNumber, w.kCGWindowName || "", b.X, b.Y, b.Width, b.Height].join("\\t"));
  }
}
out.join("\\n");
'''


class ShotError(RuntimeError):
    """A screenshot step failed; the message says which."""


def _run(cmd: list[str], timeout: float):
    """subprocess.run with an argv list (never a shell); tests replace it."""
    import subprocess

    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def _osascript(script: str, timeout: float = OSA_TIMEOUT, language: str | None = None) -> str:
    import subprocess

    cmd = ["osascript"]
    if language:
        cmd += ["-l", language]
    cmd += ["-e", script]
    try:
        proc = _run(cmd, timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ShotError(f"osascript did not run: {exc}") from None
    if proc.returncode != 0:
        tail = " | ".join((proc.stderr or "").strip().splitlines()[-3:])
        raise ShotError(f"osascript exited {proc.returncode}: {tail}")
    return (proc.stdout or "").strip()


def cg_windows() -> list[tuple]:
    """``[(window_id, name, x, y, w, h)]`` for every Max document window."""
    text = _osascript(_CG_WINDOWS_JXA.replace("{app}", APP), language="JavaScript")
    rows = []
    for line in text.splitlines():
        parts = line.split("\t")
        if len(parts) != 6:
            continue
        try:
            rows.append((int(parts[0]), parts[1], *(int(float(v)) for v in parts[2:])))
        except ValueError:
            continue
    return rows


def _find_window(prefix: str):
    for row in cg_windows():
        if row[1].startswith(prefix):
            return row
    return None


def _wait_window(prefix: str, timeout: float):
    """The window row once it exists and its title has held still."""
    deadline = time.monotonic() + timeout
    while True:
        row = _find_window(prefix)
        if row is not None:
            break
        if time.monotonic() >= deadline:
            raise ShotError(f"no Max window named {prefix!r} within {timeout:g} s "
                            "(Screen Recording permission missing?)")
        time.sleep(SHOT_POLL)
    time.sleep(SHOT_LOAD_SETTLE)
    stable_deadline = time.monotonic() + SHOT_TITLE_TIMEOUT
    last = None
    while time.monotonic() < stable_deadline:
        row = _find_window(prefix)
        if row is None:
            raise ShotError(f"window for {prefix!r} vanished while loading")
        if last is not None and row[1] == last[1]:
            return row
        last = row
        time.sleep(SHOT_POLL)
    raise ShotError(f"title of the {prefix!r} window kept changing")


def wait_gone(window_id: int, timeout: float = 5.0) -> bool:
    """True once *window_id* is no longer in the window list."""
    deadline = time.monotonic() + timeout
    while True:
        if all(row[0] != window_id for row in cg_windows()):
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(min(0.25, SHOT_POLL))


def _capture(window_id: int, png: Path) -> None:
    import subprocess

    cmd = ["screencapture", "-x", "-o", "-l", str(window_id), str(png)]
    try:
        proc = _run(cmd, OSA_TIMEOUT)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ShotError(f"screencapture did not run: {exc}") from None
    if proc.returncode != 0:
        raise ShotError(f"screencapture exited {proc.returncode}: {(proc.stderr or '').strip()}")
    if not png.is_file() or png.stat().st_size == 0:
        raise ShotError("screencapture wrote no image (Screen Recording permission missing?)")


def shoot(title_prefix: str, png: Path, timeout: float = 10.0) -> dict:
    """Capture the Max window whose title starts with *title_prefix* (by window id).

    A presentation-mode patch is captured as shown (title ``<stem>
    (presentation)``); no keystroke is sent. Raises ShotError.
    """
    png = Path(png)
    png.parent.mkdir(parents=True, exist_ok=True)
    window_id, title, _x, _y, w, h = _wait_window(title_prefix, timeout)
    _capture(window_id, png)
    return {"window_id": window_id, "title": title, "width": w, "height": h}


# ---------------------------------------------------------------------------
# check: the full sequence
# ---------------------------------------------------------------------------

ERROR_WORDINGS = ("no such object", "bad argument", "failed to compile", "can't assign")
WAV_STABLE_TIMEOUT = 5.0
CONSOLE_FILE_TIMEOUT = 2.0


class InputRefused(ValueError):
    """The check input failed the path guard."""


def _allowed_roots() -> list[Path]:
    import tempfile

    return [REPO_ROOT, Path(tempfile.gettempdir())]


def _make_run_dir() -> Path:
    import tempfile

    return Path(tempfile.mkdtemp(prefix="maxbridge-"))


def guard_input(path: Path) -> Path:
    """The resolved input; InputRefused unless it is an existing .maxpat
    under REPO_ROOT or the system temp dir (after realpath)."""
    import os

    p = Path(path)
    if p.suffix != ".maxpat":
        raise InputRefused(f"refused: {path} is not a .maxpat")
    if not p.is_file():
        raise InputRefused(f"refused: {path} does not exist")
    real = Path(os.path.realpath(p))
    for root in _allowed_roots():
        r = Path(os.path.realpath(root))
        if real == r or r in real.parents:
            break
    else:
        raise InputRefused(f"refused: {real} is outside the repo and the temp dir")
    if real.name.startswith(COPY_PREFIX):
        raise InputRefused(f"refused: {real.name} is itself a bridge temp copy")
    return real


def plan_messages(copy: Path, run_dir: Path, opts, tapped: bool = True) -> list[tuple]:
    """Every message check sends, in order (research Architecture)."""
    run_dir = Path(run_dir)
    openfile = getattr(opts, "open_mode", "pcontrol") == "openfile"
    plan: list[tuple] = [("/ping", ())]
    plan.append(("/console", ("write", str(run_dir / "before.txt"))))
    if opts.console_all:
        plan.append(("/console", ("showonlyerrors", 0)))
    plan.append(("/listen", (1,)))
    plan.append(("/openfile" if openfile else "/open", (str(copy),)))
    plan.append(("/ping", ()))
    if opts.record and tapped:
        plan += [
            ("/dsp", (1,)),
            ("/sf", ("samptype", "float32")),
            ("/sf", ("open", str(run_dir / "out.wav"))),
            ("/sf", ("record", int(round(opts.record * 1000)))),
            ("/sf", (0,)),
            ("/ping", ()),
        ]
        if not opts.leave_dsp_on:
            plan.append(("/dsp", (0,)))
    plan.append(("/console", ("write", str(run_dir / "after.txt"))))
    plan.append(("/listen", (0,)))
    if opts.console_all:
        plan.append(("/console", ("showonlyerrors", 1)))
    plan.append(("/closefile", ()) if openfile else ("/close", ()))
    plan.append(("/ping", ()))
    return plan


def _wait_file(path: Path, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while True:
        if path.is_file():
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.05)


def _wait_stable(path: Path, timeout: float = WAV_STABLE_TIMEOUT) -> bool:
    """True once *path* exists and its size holds for 3 reads 100 ms apart."""
    deadline = time.monotonic() + timeout
    sizes: list[int] = []
    while time.monotonic() < deadline:
        size = path.stat().st_size if path.is_file() else -1
        sizes = (sizes + [size])[-3:]
        if len(sizes) == 3 and size > 0 and len(set(sizes)) == 1:
            return True
        time.sleep(0.1)
    return False


def _is_error_text(text: str) -> bool:
    low = text.lower()
    return any(w in low for w in ERROR_WORDINGS)


def _error_lines(events: list, console_all: bool, console_new: list[str]) -> list[dict]:
    """Error lines from the /err stream, the console stream and the console-write diff."""
    errors: list[dict] = []
    for t, address, args in events:
        if address == "/err":
            words = [str(a) for a in args]
            if words and words[0] == "error":
                words = words[1:]
            errors.append({"source": "error", "text": " ".join(words), "t": t})
    for k, (t, address, args) in enumerate(events):
        if address != "/con/msg":
            continue
        text = " ".join(str(a) for a in args)
        if console_all and not _is_error_text(text):
            continue
        near = {}
        for j in range(max(0, k - 2), min(len(events), k + 3)):
            tj, aj, argsj = events[j]
            if aj in ("/con/obj", "/con/type") and abs(tj - t) <= 0.05 and aj not in near:
                near[aj] = argsj
        errors.append({"source": "console", "text": text, "t": t,
                       "obj": near.get("/con/obj"), "type": near.get("/con/type")})
    for line in console_new:
        if _is_error_text(line):
            errors.append({"source": "console_write", "text": line, "t": None})
    return errors


def _console_diff(run_dir: Path) -> tuple[str, list[str]]:
    from collections import Counter

    before, after = run_dir / "before.txt", run_dir / "after.txt"
    if not (_wait_file(before, CONSOLE_FILE_TIMEOUT) and _wait_file(after, CONSOLE_FILE_TIMEOUT)):
        return "unavailable", []
    seen = Counter(before.read_text(errors="replace").splitlines())
    new = []
    for line in after.read_text(errors="replace").splitlines():
        if seen[line] > 0:
            seen[line] -= 1
        elif line.strip():
            new.append(line)
    return "ok", new


def _execute(b: Bridge, plan: list[tuple], args, run_dir: Path, copy: Path, report: dict) -> None:
    """Send *plan* with the barrier waits; fill *report* in place."""
    openers = ("/open", "/openfile")
    closers = ("/close", "/closefile")
    window_id = None
    try:
        for i, (address, margs) in enumerate(plan):
            prev = plan[i - 1][0] if i else None
            if address == "/sf" and margs == (0,):
                b.collect(args.record + 0.5)
            if address in closers and args.shot is not None:
                png = Path(args.shot) if args.shot else run_dir / "shot.png"
                try:
                    report["shot"] = shoot(COPY_PREFIX + Path(args.patch).stem, png)
                    report["shot"]["png"] = str(png)
                    window_id = report["shot"]["window_id"]
                except ShotError as exc:
                    report["shot"] = {"error": str(exc), "png": str(png)}
            if address != "/ping":
                b.send(address, *margs)
                if address in openers:
                    report["load"]["open_s"] = round(b.now(), 4)
                elif address == "/dsp":
                    report["_dsp_on"] = margs == (1,)
                elif address in closers:
                    report["_closed_sent"] = True
                continue
            if prev in openers:
                b.ping(args.load_timeout)
                report["load"]["pong_s"] = round(b.now(), 4)
                b.collect(args.settle)
            elif prev == "/sf":
                b.ping(args.timeout)
                wav = run_dir / "out.wav"
                if not _wait_stable(wav):
                    raise BridgeError(f"{wav} never appeared or never stopped growing")
                report["_wav"] = wav
            else:
                b.ping(args.timeout)
                if prev in closers and args.shot is not None:
                    if window_id is not None:
                        report["closed"] = bool(wait_gone(window_id, 5.0))
                    else:
                        try:
                            report["closed"] = _find_window(COPY_PREFIX + Path(args.patch).stem) is None
                        except ShotError:
                            report["closed"] = False
    except BridgeError:
        # best effort: leave MAX as we found it, without waiting for answers
        cleanup: list[tuple] = [("/listen", (0,))]
        if report.get("_dsp_on") and not args.leave_dsp_on:
            cleanup.append(("/dsp", (0,)))
        if any(a in openers for a, _ in b.sent) and not report.get("_closed_sent"):
            cleanup.append(("/closefile", ()) if args.open_mode == "openfile" else ("/close", ()))
        for address, margs in cleanup:
            try:
                b.send(address, *margs)
            except BridgeError:
                pass
        raise


def run_check(args) -> dict:
    """Run one check; return the JSON report (``exit_code`` included)."""
    report: dict = {
        "patch": str(args.patch), "copy": None, "run_dir": None, "taps": None,
        "unsupported": [], "warnings": [], "load": {"open_s": None, "pong_s": None},
        "errors": [], "events_raw": [], "record": None, "shot": None, "closed": None,
        "feedback_suspected": False, "console_write": None,
        "verdict": "bridge_failed", "exit_code": 2,
    }
    try:
        src = guard_input(Path(args.patch))
    except InputRefused as exc:
        report["error"] = str(exc)
        return report
    report["patch"] = str(src)
    copy, inst = instrument(src)
    report.update(copy=str(copy), taps=inst["taps"], unsupported=inst["unsupported"],
                  warnings=inst["warnings"])
    try:
        run_dir = Path(_make_run_dir())
        report["run_dir"] = str(run_dir)
        plan = plan_messages(copy, run_dir, args, tapped=not inst["no_output_tap"])
        if args.dry_run:
            report["plan"] = [" ".join([a, *(str(x) for x in m)]) for a, m in plan]
            report["verdict"], report["exit_code"] = "dry_run", 0
            try:
                run_dir.rmdir()  # nothing was written there
            except OSError:
                pass
            return report
        try:
            with Bridge(HOST, args.port, args.reply_port, args.timeout,
                        max_events=MAX_EVENTS) as b:
                try:
                    _execute(b, plan, args, run_dir, copy, report)
                finally:
                    report["events_raw"] = [list(e) for e in b.events]
                    report["feedback_suspected"] = b.feedback_suspected
        except BridgeError as exc:
            report["error"] = str(exc)
            return report
    finally:
        copy.unlink(missing_ok=True)
        report.pop("_dsp_on", None)
        report.pop("_closed_sent", None)

    status, new_lines = _console_diff(run_dir)
    report["console_write"] = {"status": status, "new_lines": new_lines}
    report["errors"] = _error_lines(b.events, args.console_all, new_lines)
    wav = report.pop("_wav", None)
    if wav is not None:
        a = analyze(wav)
        report["record"] = {"wav": str(wav), "seconds": a["seconds"], "channels": a["channels"],
                            "flags": a["flags"], "warnings": a["warnings"]}
    findings = (
        bool(report["errors"])
        or bool(report["record"] and report["record"]["flags"])
        or bool(report["unsupported"])
        or bool(args.record and inst["no_output_tap"])
        or bool(report["shot"] and "error" in report["shot"])
        or report["feedback_suspected"]
    )
    report["verdict"], report["exit_code"] = ("findings", 1) if findings else ("clean", 0)
    return report


def _bridge_hint(host: str, port: int) -> str:
    rel = BRIDGE_PATCH.relative_to(REPO_ROOT)
    return (f"MAX bridge at {host}:{port} did not answer: open {rel} in MAX "
            f"(MAX 9.2 must be running)")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _add_net_args(sp: argparse.ArgumentParser) -> None:
    sp.add_argument("--port", type=int, default=BRIDGE_PORT,
                    help=f"bridge UDP port (default {BRIDGE_PORT})")
    sp.add_argument("--reply-port", type=int, default=REPLY_PORT,
                    help=f"local reply port on 127.0.0.1 (default {REPLY_PORT}; 0 = ephemeral, "
                         "only useful against a fake bridge)")
    sp.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT,
                    help=f"seconds to wait for a /pong (default {DEFAULT_TIMEOUT:g})")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="max_bridge.py",
        description="Drive a running MAX 9.2 through the resident bridge patch (Q34 spike).",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("ping", help="check that the bridge answers")
    _add_net_args(sp)

    sc = sub.add_parser("check", help="open a patch copy, collect errors, record, screenshot, close")
    sc.add_argument("patch", help="the .maxpat to check (under the repo or the temp dir)")
    sc.add_argument("--settle", type=float, default=3.0,
                    help="seconds to keep listening after the load /pong (gen~ compiles late)")
    sc.add_argument("--record", type=float, default=None, metavar="SECONDS",
                    help="record this many seconds of the dac~ taps and analyze them")
    sc.add_argument("--shot", nargs="?", const="", default=None, metavar="PNG",
                    help="screenshot the window (default <run_dir>/shot.png)")
    sc.add_argument("--open-mode", choices=("pcontrol", "openfile"), default="pcontrol",
                    help="pcontrol load (default) or ; max openfile (variant B)")
    sc.add_argument("--console-all", action="store_true",
                    help="console shows every line, not only errors, during the run")
    sc.add_argument("--leave-dsp-on", action="store_true",
                    help="do not switch DSP off after recording")
    sc.add_argument("--load-timeout", type=float, default=30.0,
                    help="seconds to wait for the /pong after the open (default 30)")
    sc.add_argument("--dry-run", action="store_true",
                    help="print the message sequence; open no socket")
    _add_net_args(sc)

    sa = sub.add_parser("analyze", help="dsp_sim measures of a recorded wav")
    sa.add_argument("wav")
    sa.add_argument("--channels", default=None, help="comma list, e.g. L or L,R")
    return parser


def _cmd_ping(args) -> int:
    try:
        with Bridge(HOST, args.port, args.reply_port, args.timeout) as b:
            latency = b.ping(args.timeout)
    except BridgeError as exc:
        print(f"{_bridge_hint(HOST, args.port)} ({exc})", file=sys.stderr)
        return 2
    print(f"PONG {latency * 1000:.1f} ms")
    return 0


def _cmd_check(args) -> int:
    import json

    report = run_check(args)
    if report.get("verdict") == "dry_run":
        for line in report["plan"]:
            print(line)
        return 0
    if "error" in report and report["copy"] is None:
        print(report["error"], file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, default=str))
    summary = (f"{report['verdict']}: {len(report['errors'])} error line(s), "
               f"record flags {report['record']['flags'] if report['record'] else None}, "
               f"unsupported {len(report['unsupported'])}, run dir {report['run_dir']}")
    if report["verdict"] == "bridge_failed":
        summary += f" -- {_bridge_hint(HOST, args.port)} ({report.get('error')})"
    print(summary, file=sys.stderr)
    return report["exit_code"]


def _cmd_analyze(args) -> int:
    import json

    channels = args.channels.split(",") if args.channels else None
    result = analyze(Path(args.wav), channels)
    print(json.dumps(result, indent=2))
    return 1 if result["flags"] else 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.cmd == "ping":
        return _cmd_ping(args)
    if args.cmd == "check":
        return _cmd_check(args)
    if args.cmd == "analyze":
        return _cmd_analyze(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
