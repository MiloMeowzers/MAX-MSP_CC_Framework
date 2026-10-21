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


# ---------------------------------------------------------------------------
# Task 2: instrument, analyze, shoot, check
# ---------------------------------------------------------------------------

def _tone_patch(path: Path, db, dac_args=None, both=True, dac="dac~") -> Path:
    from src.maxpat.hooks import format_patch_text
    p = Patcher(db=db)
    osc = p.add_box("cycle~", ["440"], x=20, y=20)
    g = p.add_box("*~", ["0.2"], x=20, y=60)
    out = p.add_box(dac, dac_args or [], x=20, y=100)
    p.add_connection(osc, 0, g, 0)
    p.add_connection(g, 0, out, 0)
    if both and out.numinlets > 1:
        p.add_connection(g, 0, out, 1)
    path.write_text(format_patch_text(p.to_dict()))
    return path


def _load(path: Path) -> Patcher:
    return Patcher.from_dict(json.loads(path.read_text()))


def _texts(p: Patcher) -> list[str]:
    return [b.text for b in p.boxes]


def _cords(p: Patcher) -> set:
    return {(l.source_id, l.source_outlet, l.dest_id, l.dest_inlet) for l in p.lines}


class TestInstrument:

    def test_taps_both_channels(self, tmp_path, db):
        src = _tone_patch(tmp_path / "tone.maxpat", db)
        before = src.read_bytes()
        copy, report = bridge.instrument(src)
        assert copy == tmp_path / "__maxbridge_tone.maxpat"
        assert src.read_bytes() == before
        assert report["taps"] == {"L": 1, "R": 1}
        assert report["no_output_tap"] is False and report["close_hook"] is True
        orig, inst = _load(src), _load(copy)
        assert _cords(orig) <= _cords(inst)
        dac_cords = lambda p: sorted(c for c in _cords(p) if c[2] == next(
            b.id for b in p.boxes if b.text == "dac~"))
        assert dac_cords(orig) == dac_cords(inst)
        by_id = {b.id: b for b in inst.boxes}
        gain = next(b for b in inst.boxes if b.text == "*~ 0.2")
        for tap in (bridge.TAP_L, bridge.TAP_R):
            (send,) = [b for b in inst.boxes if b.text == f"send~ {tap}"]
            assert [(by_id[l.source_id], l.source_outlet) for l in inst.lines
                    if l.dest_id == send.id] == [(gain, 0)]
        (rcv,) = [b for b in inst.boxes if b.text == f"receive {bridge.CLOSE_RECEIVE}"]
        (msg,) = [b for b in inst.boxes if b.maxclass == "message" and b.text == "clean, wclose"]
        (tp,) = [b for b in inst.boxes if b.text == "thispatcher"]
        succ = {(l.source_id, l.dest_id) for l in inst.lines}
        assert (rcv.id, msg.id) in succ and (msg.id, tp.id) in succ
        copy.unlink()

    def test_copy_validates_clean(self, tmp_path, db):
        copy, _ = bridge.instrument(_tone_patch(tmp_path / "v.maxpat", db))
        errors = [r for r in validate_patch(json.loads(copy.read_text()), db=db)
                  if r.level == "error"]
        copy.unlink()
        assert errors == []

    def test_channels_3_4_warn(self, tmp_path, db):
        copy, report = bridge.instrument(_tone_patch(tmp_path / "q.maxpat", db, ["3", "4"]))
        copy.unlink()
        assert report["taps"] == {"L": 0, "R": 0}
        assert len(report["warnings"]) == 2
        assert report["no_output_tap"] is True

    def test_dac_2_is_right(self, tmp_path, db):
        copy, report = bridge.instrument(_tone_patch(tmp_path / "r.maxpat", db, ["2"]))
        copy.unlink()
        assert report["taps"] == {"L": 0, "R": 1}

    def test_ezdac(self, tmp_path, db):
        copy, report = bridge.instrument(_tone_patch(tmp_path / "e.maxpat", db, dac="ezdac~"))
        copy.unlink()
        assert report["taps"] == {"L": 1, "R": 1}

    def test_dac_in_subpatcher(self, tmp_path, db):
        from src.maxpat.hooks import format_patch_text
        p = Patcher(db=db)
        _box, inner = p.add_subpatcher("out", inlets=0, outlets=0, x=20, y=20)
        osc = inner.add_box("cycle~", ["220"], x=20, y=20)
        g = inner.add_box("*~", ["0.1"], x=20, y=60)
        dac = inner.add_box("dac~", [], x=20, y=100)
        inner.add_connection(osc, 0, g, 0)
        inner.add_connection(g, 0, dac, 0)
        src = tmp_path / "sub.maxpat"
        src.write_text(format_patch_text(p.to_dict()))
        copy, report = bridge.instrument(src)
        inst = _load(copy)
        copy.unlink()
        assert report["taps"] == {"L": 1, "R": 0}
        sub = next(b for b in inst.boxes if b._inner_patcher is not None)
        assert f"send~ {bridge.TAP_L}" in _texts(sub._inner_patcher)
        assert f"send~ {bridge.TAP_L}" not in _texts(inst)

    @pytest.mark.parametrize("name,args", [
        ("mc.dac~", []), ("plugout~", []), ("poly~", ["voice", "4"]), ("pfft~", ["fx", "1024"]),
    ])
    def test_unsupported(self, tmp_path, db, name, args):
        from src.maxpat.hooks import format_patch_text
        p = Patcher(db=db)
        p.add_box(name, args, x=20, y=20)
        src = tmp_path / "u.maxpat"
        src.write_text(format_patch_text(p.to_dict()))
        copy, report = bridge.instrument(src)
        copy.unlink()
        assert [u["name"] for u in report["unsupported"]] == [name]
        assert "not tapped" in report["unsupported"][0]["reason"]

    def test_bpatcher_unsupported(self, tmp_path):
        d = {"patcher": {"fileversion": 1, "rect": [0, 0, 400, 300], "boxes": [
            {"box": {"id": "obj-1", "maxclass": "bpatcher", "name": "x.maxpat",
                     "numinlets": 0, "numoutlets": 0, "patching_rect": [10, 10, 100, 60]}}],
            "lines": []}}
        src = tmp_path / "b.maxpat"
        src.write_text(json.dumps(d))
        copy, report = bridge.instrument(src)
        copy.unlink()
        assert [u["name"] for u in report["unsupported"]] == ["bpatcher"]

    def test_no_dac(self, tmp_path, db):
        from src.maxpat.hooks import format_patch_text
        p = Patcher(db=db)
        p.add_box("loadbang", x=20, y=20)
        src = tmp_path / "n.maxpat"
        src.write_text(format_patch_text(p.to_dict()))
        copy, report = bridge.instrument(src)
        copy.unlink()
        assert report["no_output_tap"] is True

    def test_copies_are_gitignored(self):
        import subprocess
        r = subprocess.run(
            ["git", "check-ignore", "-q", "patches/simple-fm/generated/__maxbridge_x.maxpat"],
            cwd=bridge.REPO_ROOT)
        assert r.returncode == 0


def _wav(path: Path, data, sr: int = 44100) -> Path:
    from scipy.io import wavfile
    wavfile.write(str(path), sr, data)
    return path


class TestAnalyze:

    def test_sine(self, tmp_path):
        p = tmp_path / "s.wav"
        _write_sine(p, 440.0, 0.2)
        r = bridge.analyze(p)
        for ch in ("L", "R"):
            m = r["channels"][ch]
            assert abs(m["pitch_hz"] - 440.0) < 1.0
            assert abs(m["peak"] - 0.2) < 1e-3
            assert abs(m["dc"]) < 1e-3
            assert m["flags"] == []
        assert r["flags"] == []

    def test_dc(self, tmp_path):
        import numpy as np
        p = _wav(tmp_path / "d.wav", np.full((44100, 2), 0.5, dtype=np.float32))
        r = bridge.analyze(p)
        m = r["channels"]["L"]
        assert {"dc_offset", "silent"} <= set(m["flags"])
        assert m["pitch_hz"] == 0.0
        assert abs(m["dc"] - 0.5) < 1e-6

    def test_nan(self, tmp_path):
        import numpy as np
        t = np.arange(44100) / 44100
        x = (0.2 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        x[20000:20010] = np.nan
        p = _wav(tmp_path / "n.wav", np.stack([x, x], axis=1))
        m = bridge.analyze(p)["channels"]["L"]
        assert m["nan"] == 10
        assert "nonfinite" in m["flags"]
        assert abs(m["peak"] - 0.2) < 1e-3

    @pytest.mark.parametrize("amp,flag", [(1.5, "clipping"), (20.0, "runaway")])
    def test_loud(self, tmp_path, amp, flag):
        p = tmp_path / "l.wav"
        _write_sine(p, 220.0, amp)
        assert flag in bridge.analyze(p)["flags"]

    def test_int16_scaled(self, tmp_path):
        import numpy as np
        t = np.arange(44100) / 44100
        x = (0.5 * 32767 * np.sin(2 * np.pi * 440 * t)).astype(np.int16)
        r = bridge.analyze(_wav(tmp_path / "i.wav", x))
        assert abs(r["channels"]["L"]["peak"] - 0.5) < 1e-3
        assert any("NaN" in w for w in r["warnings"])

    def test_channels_l_only(self, tmp_path):
        p = tmp_path / "c.wav"
        _write_sine(p, 440.0, 0.2)
        assert list(bridge.analyze(p, channels=["L"])["channels"]) == ["L"]

    def test_cli(self, tmp_path, capsys):
        p = tmp_path / "c.wav"
        _write_sine(p, 440.0, 0.2)
        assert bridge.main(["analyze", str(p), "--channels", "L"]) == 0
        assert list(json.loads(capsys.readouterr().out)["channels"]) == ["L"]
        _write_sine(p, 440.0, 1.5)
        assert bridge.main(["analyze", str(p)]) == 1


class FakeRun:
    """Stands in for bridge._run: answers osascript with a window list (after
    ``appear_after`` empty answers) and writes a png for screencapture."""

    def __init__(self, rows, write_png=True, appear_after=0):
        self.rows = rows
        self.write_png = write_png
        self.appear_after = appear_after
        self.calls: list[list[str]] = []

    def __call__(self, cmd, timeout):
        import subprocess
        self.calls.append(list(cmd))
        out = ""
        if cmd[0] == "osascript":
            n = len([c for c in self.calls if c[0] == "osascript"])
            if n > self.appear_after:
                out = "\n".join("\t".join(str(v) for v in r) for r in self.rows)
        elif cmd[0] == "screencapture" and self.write_png:
            Path(cmd[-1]).write_bytes(b"\x89PNG fake")
        return subprocess.CompletedProcess(cmd, 0, out, "")


@pytest.fixture
def fast_shot(monkeypatch):
    monkeypatch.setattr(bridge, "SHOT_LOAD_SETTLE", 0.0)
    monkeypatch.setattr(bridge, "SHOT_POLL", 0.01)


class TestShoot:

    ROWS = [(11, "other", 0, 0, 100, 100), (42, "__maxbridge_tone", 10, 20, 640, 480)]

    def test_finds_window_and_captures(self, tmp_path, monkeypatch, fast_shot):
        fake = FakeRun(self.ROWS, appear_after=1)
        monkeypatch.setattr(bridge, "_run", fake)
        png = tmp_path / "s.png"
        r = bridge.shoot("__maxbridge_tone", png, timeout=2.0)
        assert r == {"window_id": 42, "title": "__maxbridge_tone", "width": 640, "height": 480}
        (cap,) = [c for c in fake.calls if c[0] == "screencapture"]
        assert cap == ["screencapture", "-x", "-o", "-l", "42", str(png)]
        jxa = next(c for c in fake.calls if c[0] == "osascript")
        assert jxa[:3] == ["osascript", "-l", "JavaScript"]
        assert '"Max"' in jxa[-1] and "kCGWindowLayer === 0" in jxa[-1] and "kCGWindowIsOnscreen" in jxa[-1]

    def test_empty_png(self, tmp_path, monkeypatch, fast_shot):
        monkeypatch.setattr(bridge, "_run", FakeRun(self.ROWS, write_png=False))
        with pytest.raises(bridge.ShotError):
            bridge.shoot("__maxbridge_tone", tmp_path / "s.png", timeout=1.0)

    def test_no_window(self, tmp_path, monkeypatch, fast_shot):
        monkeypatch.setattr(bridge, "_run", FakeRun([(11, "other", 0, 0, 1, 1)]))
        t0 = time.monotonic()
        with pytest.raises(bridge.ShotError):
            bridge.shoot("__maxbridge_tone", tmp_path / "s.png", timeout=0.3)
        assert time.monotonic() - t0 < 2.0

    def test_wait_gone(self, monkeypatch, fast_shot):
        monkeypatch.setattr(bridge, "_run", FakeRun(self.ROWS))
        assert bridge.wait_gone(99, timeout=0.1) is True
        assert bridge.wait_gone(42, timeout=0.1) is False


@pytest.fixture
def run_dir(tmp_path, monkeypatch):
    d = tmp_path / "run"
    d.mkdir()
    monkeypatch.setattr(bridge, "_make_run_dir", lambda: d)
    return d


def _check(fb, patch, *extra, capsys):
    argv = ["check", str(patch), "--port", str(fb.port), "--reply-port", "0",
            "--settle", "0.1", "--load-timeout", "1.5", "--timeout", "1.0", *extra]
    rc = bridge.main(argv)
    return rc, json.loads(capsys.readouterr().out)


class TestCheck:

    def test_error_run(self, tmp_path, db, run_dir, capsys):
        src = _tone_patch(tmp_path / "tone.maxpat", db)
        before = src.read_bytes()
        with FakeBridge(errors=True) as fb:
            rc, rep = _check(fb, src, "--record", "0.2", capsys=capsys)
        assert rc == 1 and rep["exit_code"] == 1 and rep["verdict"] == "findings"
        assert rep["errors"][0]["source"] == "error"
        assert "No such object" in rep["errors"][0]["text"]
        assert any(e["source"] == "console_write" for e in rep["errors"])
        assert rep["record"] is not None and rep["record"]["flags"] == []
        assert not (tmp_path / "__maxbridge_tone.maxpat").exists()
        assert src.read_bytes() == before

    def test_clean_run_and_order(self, tmp_path, db, run_dir, capsys):
        src = _tone_patch(tmp_path / "tone.maxpat", db)
        with FakeBridge() as fb:
            rc, rep = _check(fb, src, "--record", "0.2", capsys=capsys)
        assert rc == 0 and rep["verdict"] == "clean", rep
        assert rep["errors"] == [] and rep["closed"] is None
        copy = tmp_path / "__maxbridge_tone.maxpat"
        opts = bridge.build_parser().parse_args(["check", str(src), "--record", "0.2"])
        planned = [a for a, _ in bridge.plan_messages(copy, run_dir, opts)]
        assert fb.addresses == planned
        assert planned[:2] == ["/ping", "/console"]
        assert "/open" in planned and "/sf" in planned and planned[-1] == "/ping"
        assert ("/dsp", [0]) in fb.received

    def test_bridge_stops_answering(self, tmp_path, db, run_dir, capsys):
        src = _tone_patch(tmp_path / "tone.maxpat", db)
        with FakeBridge(mute_after_open=True) as fb:
            rc, rep = _check(fb, src, capsys=capsys)
        assert rc == 2 and rep["verdict"] == "bridge_failed"
        assert not (tmp_path / "__maxbridge_tone.maxpat").exists()

    def test_feedback_cap(self, tmp_path, db, run_dir, capsys, monkeypatch):
        monkeypatch.setattr(bridge, "MAX_EVENTS", 50)
        src = _tone_patch(tmp_path / "tone.maxpat", db)
        with FakeBridge(flood=80) as fb:
            rc, rep = _check(fb, src, capsys=capsys)
        assert rc == 1 and rep["feedback_suspected"] is True
        assert len(rep["events_raw"]) == 50
        assert fb.received.count(("/listen", [0])) >= 2

    def test_openfile_mode(self, tmp_path, db, run_dir, capsys):
        src = _tone_patch(tmp_path / "tone.maxpat", db)
        with FakeBridge() as fb:
            rc, _rep = _check(fb, src, "--open-mode", "openfile", capsys=capsys)
        assert rc == 0
        assert "/openfile" in fb.addresses and "/closefile" in fb.addresses
        assert "/open" not in fb.addresses and "/close" not in fb.addresses

    def test_dry_run(self, tmp_path, db, run_dir, capsys, monkeypatch):
        def no_socket(*a, **k):
            raise AssertionError("dry run opened a socket")
        monkeypatch.setattr(bridge.socket, "socket", no_socket)
        src = _tone_patch(tmp_path / "tone.maxpat", db)
        rc = bridge.main(["check", str(src), "--record", "1", "--dry-run"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "/open " in out and "/sf record 1000" in out
        assert not (tmp_path / "__maxbridge_tone.maxpat").exists()

    def test_refuses_outside_roots(self, tmp_path, db, monkeypatch, capsys):
        src = _tone_patch(tmp_path / "tone.maxpat", db)
        monkeypatch.setattr(bridge, "_allowed_roots", lambda: [tmp_path / "elsewhere"])
        assert bridge.main(["check", str(src), "--dry-run"]) == 2
        assert "refused" in capsys.readouterr().err
        assert not (tmp_path / "__maxbridge_tone.maxpat").exists()

    def test_refuses_non_maxpat(self, tmp_path):
        f = tmp_path / "x.txt"
        f.write_text("{}")
        assert bridge.main(["check", str(f), "--dry-run"]) == 2

    def test_open_requires_copy_prefix(self):
        with bridge.Bridge(port=_free_port(), reply_port=0) as b:
            with pytest.raises(ValueError):
                b.send("/open", "/tmp/tone.maxpat")
            with pytest.raises(ValueError):
                b.send("/openfile", "/tmp/tone.maxpat")

    def test_shot_and_closed(self, tmp_path, db, run_dir, capsys, monkeypatch):
        shots = []

        def fake_shoot(prefix, png, timeout=10.0):
            shots.append((prefix, Path(png)))
            return {"window_id": 7, "title": prefix, "width": 10, "height": 10}

        monkeypatch.setattr(bridge, "shoot", fake_shoot)
        monkeypatch.setattr(bridge, "wait_gone", lambda wid, timeout=5.0: True)
        src = _tone_patch(tmp_path / "tone.maxpat", db)
        with FakeBridge() as fb:
            rc, rep = _check(fb, src, "--shot", capsys=capsys)
        assert rc == 0, rep
        assert shots == [("__maxbridge_tone", run_dir / "shot.png")]
        assert rep["shot"]["window_id"] == 7 and rep["closed"] is True

    def test_check_defaults_are_documented(self):
        assert "--settle" in bridge.__doc__ and "--record" in bridge.__doc__

    def test_check_defaults(self):
        a = bridge.build_parser().parse_args(["check", "x.maxpat"])
        assert (a.settle, a.record, a.shot, a.open_mode, a.load_timeout) == (
            3.0, None, None, "pcontrol", 30.0)
        assert a.console_all is False and a.leave_dsp_on is False and a.dry_run is False


# ---------------------------------------------------------------------------
# Task 3: fixtures, checklist, open questions
# ---------------------------------------------------------------------------

PROJECT_DIR = bridge.REPO_ROOT / "patches" / "max-bridge"
FIXTURES = ("fx-clean", "fx-dc", "fx-badargs", "fx-nosuchobj", "fx-genfail")
CHECKLIST = PROJECT_DIR / "test-results" / "v0.1.0-bridge-checklist.md"
OPEN_QUESTIONS = PROJECT_DIR / "open-questions.md"


class TestFixtures:

    def test_fixtures_exist_outside_generated(self):
        for name in FIXTURES:
            assert (PROJECT_DIR / "fixtures" / f"{name}.maxpat").is_file(), name
        assert sorted(p.name for p in (PROJECT_DIR / "generated").iterdir()) == ["max-bridge.maxpat"]

    @pytest.mark.parametrize("name,tapped", [
        ("fx-clean", True), ("fx-dc", True), ("fx-genfail", True),
        ("fx-nosuchobj", False), ("fx-badargs", False),
    ])
    def test_instrument_fixture(self, name, tapped):
        src = PROJECT_DIR / "fixtures" / f"{name}.maxpat"
        before = src.read_bytes()
        copy, report = bridge.instrument(src)
        try:
            if tapped:
                assert report["taps"] == {"L": 1, "R": 1}
            else:
                assert report["no_output_tap"] is True
        finally:
            copy.unlink()
        assert src.read_bytes() == before
        assert not copy.exists()

    @pytest.mark.parametrize("name", FIXTURES)
    def test_fixture_round_trips(self, name):
        from src.maxpat.hooks import format_patch_text
        text = (PROJECT_DIR / "fixtures" / f"{name}.maxpat").read_text()
        d = json.loads(text)
        assert format_patch_text(Patcher.from_dict(d).to_dict(), text) == text

    def test_deliberate_errors_present(self):
        nso = (PROJECT_DIR / "fixtures" / "fx-nosuchobj.maxpat").read_text()
        assert '"osc~ 440"' in nso and "DELIBERATE ERROR FIXTURE" in nso
        gen = json.loads((PROJECT_DIR / "fixtures" / "fx-genfail.maxpat").read_text())
        codes = [ib["box"].get("code") for b in gen["patcher"]["boxes"] if "patcher" in b["box"]
                 for ib in b["box"]["patcher"]["boxes"] if ib["box"]["maxclass"] == "codebox"]
        assert codes == ["Param g(0.5);\ng = in1;\nout1 = g;"]

    def test_checklist_names_every_fixture(self):
        text = CHECKLIST.read_text()
        for name in FIXTURES:
            assert f"fixtures/{name}.maxpat" in text, name
        assert "find patches -name '__maxbridge_*'" in text
        assert "git status --porcelain patches/simple-fm" in text

    def test_every_question_cites_a_checklist_step(self):
        import re
        text = OPEN_QUESTIONS.read_text()
        steps = {int(n) for n in re.findall(r"^(\d+)\. \[[^]]*\]", CHECKLIST.read_text(), re.M)}
        entries = re.split(r"\n(?=(?:\d+|A\d|N\d)\. )", text)
        entries = [e for e in entries if re.match(r"(?:\d+|A\d|N\d)\. ", e)]
        assert len(entries) == 10 + 6 + 5
        for e in entries:
            m = re.search(r"Answered by: checklist step (\d+)", e)
            assert m, e[:60]
            assert int(m.group(1)) in steps, e[:60]
            assert "Answer:" in e
