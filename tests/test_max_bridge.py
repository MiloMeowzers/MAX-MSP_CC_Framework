"""quick-261016-uy1 (Q34): hermetic tests for tools/max_bridge.py.

The bridge spike drives a running MAX 9.2 over UDP/OSC. Nothing here needs
MAX: the OSC codec, the temp-copy instrumentation, the wav analysis, the
screenshot helpers (subprocess faked) and the full check sequence run
against an in-process FakeBridge on 127.0.0.1. House convention
(tests/test_sync_max_bundle.py): import the tool as a module and call its
functions directly.
"""

from __future__ import annotations

import json
import socket
import struct
import threading
import time
from pathlib import Path

import pytest

import tools.max_bridge as bridge
from src.maxpat.db_lookup import ObjectDatabase
from src.maxpat.patcher import Patcher
from src.maxpat.validation import validate_patch


@pytest.fixture(scope="module")
def db():
    return ObjectDatabase()


def _free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


# ---------------------------------------------------------------------------
# FakeBridge: an in-process stand-in for the MAX bridge patch
# ---------------------------------------------------------------------------

class FakeBridge:
    """A UDP thread on 127.0.0.1:0 that decodes packets, records them and
    answers the way the bridge patch is expected to.

    - ``/ping`` -> ``/pong`` to the sender (the client's reply port);
    - ``/open`` or ``/openfile`` -> ``/err error osc~: No such object`` when
      ``errors`` is set (and the same line into the fake console), or a flood
      of ``flood`` /err packets;
    - ``/console write <p>`` writes the fake console lines to p;
    - ``/sf open <p>`` remembers p; ``/sf 0`` writes a 0.2-amplitude 440 Hz
      float32 stereo wav there.
    - ``mute_after_open``: stop answering anything once /open arrives.
    """

    def __init__(self, errors: bool = False, flood: int = 0,
                 mute_after_open: bool = False) -> None:
        self.errors = errors
        self.flood = flood
        self.mute_after_open = mute_after_open
        self.received: list[tuple[str, list]] = []
        self.console = ["Max 9.2.0 (fake) started"]
        self.sf_path: str | None = None
        self.muted = False
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", 0))
        self.sock.settimeout(0.05)
        self.port = self.sock.getsockname()[1]
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def __enter__(self) -> "FakeBridge":
        self._thread.start()
        return self

    def __exit__(self, *exc) -> None:
        self._stop.set()
        self._thread.join(2.0)
        self.sock.close()

    @property
    def addresses(self) -> list[str]:
        return [a for a, _ in self.received]

    def _reply(self, addr, address, *args) -> None:
        self.sock.sendto(bridge.osc_encode(address, *args), addr)

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                data, addr = self.sock.recvfrom(65536)
            except socket.timeout:
                continue
            except OSError:
                return
            msg = bridge.osc_decode(data)
            if msg is None:
                continue
            address, args = msg
            self.received.append((address, list(args)))
            if self.muted:
                continue
            self._handle(addr, address, list(args))

    def _handle(self, addr, address, args) -> None:
        if address == "/ping":
            self._reply(addr, "/pong")
        elif address in ("/open", "/openfile"):
            if self.mute_after_open:
                self.muted = True
                return
            if self.errors:
                self.console.append("osc~: No such object")
                self._reply(addr, "/err", "error", "osc~:", "No", "such", "object")
            for i in range(self.flood):
                self._reply(addr, "/err", "error", "udpsend:", "flood", i)
        elif address == "/console" and args and args[0] == "write":
            Path(args[1]).write_text("\n".join(self.console) + "\n")
        elif address == "/sf" and args and args[0] == "open":
            self.sf_path = args[1]
        elif address == "/sf" and args == [0] and self.sf_path:
            _write_sine(Path(self.sf_path), 440.0, 0.2, seconds=1.0)


def _write_sine(path: Path, freq: float, amp: float, seconds: float = 1.0,
                sr: int = 44100, stereo: bool = True) -> None:
    import numpy as np
    from scipy.io import wavfile

    t = np.arange(int(sr * seconds)) / sr
    x = (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32)
    data = np.stack([x, x], axis=1) if stereo else x
    wavfile.write(str(path), sr, data)


# ---------------------------------------------------------------------------
# Task 1: DB fix, OSC codec, bridge patch, ping
# ---------------------------------------------------------------------------

class TestSfrecordOverride:

    def test_inlet_1_is_signal(self, db):
        inlets = db.lookup("sfrecord~")["inlets"]
        assert inlets[1]["type"] == "signal"
        assert inlets[1]["signal"] is True

    def test_receive_to_sfrecord_inlet_1_validates(self, db):
        p = Patcher(db=db)
        r = p.add_box("receive~", ["x"], x=20, y=20)
        rec = p.add_box("sfrecord~", ["2"], x=20, y=80)
        assert rec.numinlets == 2
        p.add_connection(r, 0, rec, 1)
        msgs = [r.message for r in validate_patch(p.to_dict(), db=db)]
        assert not [m for m in msgs if "control-only inlet" in m]

    def test_audit_source_kept_and_cites_q34(self):
        ov = json.loads(Path(".claude/max-objects/overrides.json").read_text())
        src = ov["objects"]["sfrecord~"]["_audit"]["source"]
        assert src.startswith("Q11 / C9 (261013-e43)")
        assert "Q34 (261016-uy1)" in src
        assert "Each inlet of sfrecord~ accepts a signal" in src


class TestOsc:

    def test_roundtrip_i_f_s(self):
        pkt = bridge.osc_encode("/x", 7, 0.5, "hello")
        assert len(pkt) % 4 == 0
        assert bridge.osc_decode(pkt) == ("/x", [7, 0.5, "hello"])

    @pytest.mark.parametrize("address,size", [("/ab", 4), ("/abc", 8), ("/abcd", 8)])
    def test_address_padding(self, address, size):
        pkt = bridge.osc_encode(address)
        # address block + ",\0\0\0"
        assert len(pkt) == size + 4
        assert pkt[:size].rstrip(b"\0") == address.encode()
        assert pkt[len(address)] == 0

    def test_int_is_big_endian_int32(self):
        pkt = bridge.osc_encode("/i", -2)
        assert pkt.endswith(struct.pack(">i", -2))

    def test_decode_extra_tags(self):
        body = (
            b"/t\0\0" + b",dhSTFN\0"
            + struct.pack(">d", 1.25) + struct.pack(">q", 2 ** 40)
            + b"sym\0"
        )
        assert bridge.osc_decode(body) == ("/t", [1.25, 2 ** 40, "sym", True, False, None])

    def test_bundle_is_none(self):
        assert bridge.osc_decode(b"#bundle\0" + b"\0" * 8) is None

    def test_truncated_raises(self):
        pkt = bridge.osc_encode("/x", 7)
        with pytest.raises(ValueError):
            bridge.osc_decode(pkt[:-2])
        with pytest.raises(ValueError):
            bridge.osc_decode(b"/abc")

    def test_unknown_tag_raises(self):
        with pytest.raises(ValueError):
            bridge.osc_decode(b"/x\0\0,q\0\0")


def _box_name(box) -> str:
    if box.maxclass == "newobj":
        return box.text.split()[0] if box.text else ""
    return box.maxclass


def _args(box) -> list[str]:
    return box.text.split()[1:]


class TestBridgePatch:

    @pytest.fixture(scope="class")
    def patch(self):
        from src.maxpat.hooks import read_patch
        p, text = read_patch(bridge.BRIDGE_PATCH)
        return p, json.loads(text)

    def _one(self, p, name):
        found = [b for b in p.boxes if _box_name(b) == name]
        assert len(found) == 1, (name, [b.text for b in found])
        return found[0]

    def _succ(self, p, box, outlet=None):
        by_id = {b.id: b for b in p.boxes}
        return [
            (by_id[l.dest_id], l.dest_inlet) for l in p.lines
            if l.source_id == box.id and (outlet is None or l.source_outlet == outlet)
        ]

    def _reaches(self, p, start, target, avoid=()) -> bool:
        seen, todo = set(), [start]
        while todo:
            b = todo.pop()
            if b.id in seen:
                continue
            seen.add(b.id)
            if b is target:
                return True
            for nxt, _ in self._succ(p, b):
                if _box_name(nxt) not in avoid:
                    todo.append(nxt)
        return False

    def test_exists_at_bridge_patch(self):
        assert bridge.BRIDGE_PATCH.is_file()
        assert bridge.BRIDGE_PATCH == bridge.REPO_ROOT / "patches/max-bridge/generated/max-bridge.maxpat"

    def test_validates_and_reviews_clean(self, patch, db):
        from src.maxpat.hooks import _blocking_findings
        _p, d = patch
        errors = [r for r in validate_patch(d, db=db) if r.level == "error"]
        assert errors == []
        assert _blocking_findings(d, is_new=True) == []

    def test_args_pinned_to_constants(self, patch):
        p, _ = patch
        assert _args(self._one(p, "udpreceive")) == [str(bridge.BRIDGE_PORT)]
        assert _args(self._one(p, "udpsend")) == [bridge.HOST, str(bridge.REPLY_PORT)]
        assert tuple(_args(self._one(p, "route"))) == bridge.ROUTE_ADDRESSES

    def test_route_order(self):
        assert bridge.ROUTE_ADDRESSES == (
            "/ping", "/open", "/sf", "/console", "/dsp", "/listen",
            "/close", "/openfile", "/closefile",
        )

    def test_udpreceive_deferlow_route(self, patch):
        p, _ = patch
        udp = self._one(p, "udpreceive")
        (dl, _i), = self._succ(p, udp)
        assert _box_name(dl) == "deferlow"
        (rt, _i), = self._succ(p, dl)
        assert _box_name(rt) == "route"

    def test_ping_reaches_pong_then_udpsend(self, patch):
        p, _ = patch
        route = self._one(p, "route")
        (msg, _i), = self._succ(p, route, 0)
        assert msg.maxclass == "message" and msg.text == "/pong"
        assert (self._one(p, "udpsend"), 0) in self._succ(p, msg)

    def test_open_close_messages(self, patch):
        p, _ = patch
        route = self._one(p, "route")
        idx = bridge.ROUTE_ADDRESSES.index
        (pre, _i), = self._succ(p, route, idx("/open"))
        assert pre.text == "prepend load"
        assert _box_name(self._succ(p, pre)[0][0]) == "pcontrol"
        (close, _i), = self._succ(p, route, idx("/close"))
        assert close.text == ";\r" + bridge.CLOSE_RECEIVE + " bang"
        (of, _i), = self._succ(p, route, idx("/openfile"))
        assert of.text == ";\rmax openfile maxbridge $1"
        (cf, _i), = self._succ(p, route, idx("/closefile"))
        assert cf.text == ";\rmax closefile maxbridge"

    def test_dsp_select(self, patch):
        p, _ = patch
        route = self._one(p, "route")
        (sel, _i), = self._succ(p, route, bridge.ROUTE_ADDRESSES.index("/dsp"))
        assert sel.text in ("select 1 0", "sel 1 0")
        assert self._succ(p, sel, 0)[0][0].text == ";\rdsp start"
        assert self._succ(p, sel, 1)[0][0].text == ";\rdsp stop"

    def test_taps_reach_sfrecord(self, patch):
        p, _ = patch
        rec = self._one(p, "sfrecord~")
        assert _args(rec) == ["2"]
        for tap, inlet in ((bridge.TAP_L, 0), (bridge.TAP_R, 1)):
            (r,) = [b for b in p.boxes if b.text == f"receive~ {tap}"]
            assert (rec, inlet) in self._succ(p, r)
        route = self._one(p, "route")
        assert (rec, 0) in self._succ(p, route, bridge.ROUTE_ADDRESSES.index("/sf"))

    def test_error_and_console_streams(self, patch):
        p, _ = patch
        udpsend = self._one(p, "udpsend")
        err = self._one(p, "error")
        (pre, _i), = self._succ(p, err)
        assert pre.text == "prepend /err"
        assert (udpsend, 0) in self._succ(p, pre)
        console = self._one(p, "console")
        assert "@showonlyerrors 1" in console.text
        for outlet, addr in enumerate(("/con/obj", "/con/msg", "/con/type")):
            (g, inlet), = self._succ(p, console, outlet)
            assert _box_name(g) == "gate" and inlet == 1
            (pre, _i), = self._succ(p, g)
            assert pre.text == f"prepend {addr}"
            assert (udpsend, 0) in self._succ(p, pre)
            # the console reaches udpsend only through its gate
            assert not self._reaches(p, console, udpsend, avoid=("gate",))

    def test_listen_fanout_closed_at_load(self, patch):
        p, _ = patch
        trig = self._one(p, "trigger") if any(_box_name(b) == "trigger" for b in p.boxes) \
            else self._one(p, "t")
        assert _args(trig) == ["i", "i", "i", "i"]
        loadmess = self._one(p, "loadmess")
        assert _args(loadmess) == ["0"]
        assert (trig, 0) in self._succ(p, loadmess)
        route = self._one(p, "route")
        assert (trig, 0) in self._succ(p, route, bridge.ROUTE_ADDRESSES.index("/listen"))
        assert _box_name(self._succ(p, trig, 0)[0][0]) == "error"
        for outlet in (1, 2, 3):
            (g, inlet), = self._succ(p, trig, outlet)
            assert _box_name(g) == "gate" and inlet == 0

    def test_no_print_no_presentation(self, patch):
        p, _ = patch
        assert not [b for b in p.boxes if _box_name(b) == "print"]
        assert not [b for b in p.boxes if b.presentation]

    def test_lan_warning_comment(self, patch):
        p, _ = patch
        texts = " ".join(b.text for b in p.boxes if b.maxclass == "comment")
        assert "ALL network interfaces" in texts
        assert "Never add print" in texts


class TestPing:

    def test_pong(self, capsys):
        with FakeBridge() as fb:
            rc = bridge.main(["ping", "--port", str(fb.port), "--reply-port", "0",
                              "--timeout", "2"])
        assert rc == 0
        assert capsys.readouterr().out.startswith("PONG ")
        assert fb.addresses == ["/ping"]

    def test_no_listener_exit_2(self, capsys):
        port = _free_port()
        t0 = time.monotonic()
        rc = bridge.main(["ping", "--port", str(port), "--reply-port", "0",
                          "--timeout", "0.5"])
        assert rc == 2
        assert time.monotonic() - t0 < 1.5
        err = capsys.readouterr().err
        assert f"127.0.0.1:{port}" in err
        assert str(bridge.BRIDGE_PATCH.relative_to(bridge.REPO_ROOT)) in err

    def test_bind_failure_is_bridge_error(self):
        holder = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        holder.bind(("127.0.0.1", 0))
        try:
            with pytest.raises(bridge.BridgeError) as exc:
                bridge.Bridge(reply_port=holder.getsockname()[1])
            assert str(holder.getsockname()[1]) in str(exc.value)
        finally:
            holder.close()

    def test_events_collected_during_ping(self):
        with FakeBridge(errors=True) as fb:
            with bridge.Bridge(port=fb.port, reply_port=0) as b:
                b.send("/openfile", "/tmp/" + bridge.COPY_PREFIX + "x.maxpat")
                b.ping(2.0)
        assert [e[1] for e in b.events] == ["/err"]


class TestCli:

    def test_ping_defaults(self):
        args = bridge.build_parser().parse_args(["ping"])
        assert (args.port, args.reply_port, args.timeout) == (7400, 7401, 2.0)

    def test_constants(self):
        assert (bridge.BRIDGE_PORT, bridge.REPLY_PORT, bridge.HOST) == (7400, 7401, "127.0.0.1")
        assert (bridge.TAP_L, bridge.TAP_R) == ("__maxbridge_L", "__maxbridge_R")
        assert bridge.CLOSE_RECEIVE == "__maxbridge_close"
        assert bridge.COPY_PREFIX == "__maxbridge_"
