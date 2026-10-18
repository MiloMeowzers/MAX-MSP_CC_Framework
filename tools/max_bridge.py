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


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.cmd == "ping":
        return _cmd_ping(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
