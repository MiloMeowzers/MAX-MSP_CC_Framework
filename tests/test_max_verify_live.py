"""quick-261021-olv: hermetic tests for tools/max_verify_live.py (/max-verify --live).

Nothing here reaches MAX or the real bridge port: every run passes an explicit
--port (a FakeBridge's, or a free port nobody listens on) and --reply-port 0,
``_max_running`` and ``bridge.cg_windows`` are faked, and the bridge's run
dirs go under tmp_path.
"""

from __future__ import annotations

import ast
import json
import sys
import time
from pathlib import Path

import pytest

import tools.max_bridge as bridge
import tools.max_verify_live as live
from src.maxpat.db_lookup import ObjectDatabase
from src.maxpat.patcher import Patcher
from tests.test_max_bridge import FakeBridge, _free_port, _tone_patch

LIVE_PY = Path(live.__file__)


@pytest.fixture(scope="module")
def db():
    return ObjectDatabase()


@pytest.fixture(autouse=True)
def _no_real_max(monkeypatch):
    monkeypatch.setattr(live, "_max_running", lambda: True)
    monkeypatch.setattr(bridge, "cg_windows", lambda: [])


@pytest.fixture(autouse=True)
def _run_dirs(tmp_path, monkeypatch):
    counter = {"n": 0}

    def make():
        counter["n"] += 1
        d = tmp_path / "runs" / f"run{counter['n']}"
        d.mkdir(parents=True)
        return d

    monkeypatch.setattr(bridge, "_make_run_dir", make)


def _run(port, *paths, extra=(), capsys):
    argv = [*map(str, paths), "--port", str(port), "--reply-port", "0", "--timeout", "1.0",
            "--settle", "0.1", "--load-timeout", "1.5", "--no-shot", "--json"]
    if "--record" not in extra:
        argv += ["--record", "0.2"]
    argv += list(extra)
    rc = live.main(argv)
    out = capsys.readouterr().out
    return rc, json.loads(out)


def _opts(*argv):
    return live.build_parser().parse_args(list(argv))


# ---------------------------------------------------------------------------
# Patch builders
# ---------------------------------------------------------------------------

def _write(p: Patcher, path: Path) -> Path:
    from src.maxpat.hooks import format_patch_text
    path.write_text(format_patch_text(p.to_dict()))
    return path


def _tone_with(path: Path, db, extra: str) -> Path:
    p = Patcher(db=db)
    osc = p.add_box("cycle~", ["440"], x=20, y=20)
    g = p.add_box("*~", ["0.2"], x=20, y=60)
    out = p.add_box("dac~", [], x=20, y=100)
    p.add_connection(osc, 0, g, 0)
    p.add_connection(g, 0, out, 0)
    p.add_connection(g, 0, out, 1)
    if extra == "notein":
        p.add_box("notein", [], x=200, y=20)
    elif extra == "kslider":
        p.add_box("kslider", [], x=200, y=20)
    return _write(p, path)


def _adc_patch(path: Path, db) -> Path:
    p = Patcher(db=db)
    adc = p.add_box("adc~", [], x=20, y=20)
    g = p.add_box("*~", ["0.2"], x=20, y=60)
    out = p.add_box("dac~", [], x=20, y=100)
    p.add_connection(adc, 0, g, 0)
    p.add_connection(g, 0, out, 0)
    p.add_connection(g, 0, out, 1)
    return _write(p, path)


def _nodac_patch(path: Path, db) -> Path:
    p = Patcher(db=db)
    osc = p.add_box("cycle~", ["440"], x=20, y=20)
    mute = p.add_box("*~", ["0."], x=20, y=60)
    p.add_connection(osc, 0, mute, 0)
    return _write(p, path)


def _raw_patch(boxes: list[dict]) -> dict:
    return {"patcher": {"fileversion": 1, "rect": [0, 0, 400, 300], "boxes":
                        [{"box": b} for b in boxes], "lines": []}}


def _newobj(i: int, text: str) -> dict:
    return {"id": f"obj-{i}", "maxclass": "newobj", "text": text, "numinlets": 1,
            "numoutlets": 1, "patching_rect": [20.0, 20.0 + 40 * i, 80.0, 22.0]}


def _no_copies(root: Path) -> bool:
    return not list(root.rglob(f"{bridge.COPY_PREFIX}*"))


# ---------------------------------------------------------------------------
# Module identity and constants
# ---------------------------------------------------------------------------

def test_import_identity():
    assert live.bridge is sys.modules["tools.max_bridge"]


def test_input_boxes_in_db(db):
    for name in live.INPUT_BOXES:
        entry = db.lookup(name)
        assert entry is not None, name
        assert entry["domain"].lower() not in ("rnbo", "gen"), name


def test_every_wording_has_a_suggestion():
    assert set(live.WORDING_SUGGESTIONS) == set(bridge.ERROR_WORDINGS)


# ---------------------------------------------------------------------------
# Option rules (D-01 / D-02)
# ---------------------------------------------------------------------------

def _argv_for(path, *opt_argv):
    opts = _opts(*opt_argv)
    scan = live.scan_patch(path)
    argv, mode, reasons = live.check_argv(path, scan, opts)
    parsed = bridge.build_parser().parse_args(argv)
    return argv, mode, reasons, parsed


class TestOptionRules:

    def test_notein_records_with_note(self, tmp_path, db):
        argv, mode, _r, parsed = _argv_for(_tone_with(tmp_path / "t.maxpat", db, "notein"))
        assert mode == "record"
        i = argv.index("--record")
        assert argv[i + 1] == "3.0"
        j = argv.index("--note")
        assert argv[j + 1:j + 3] == ["60", "100"]
        assert "--dsp-on-load" not in argv and parsed.dsp_on_load is False
        assert parsed.note == [60, 100] and parsed.record == 3.0

    def test_kslider_gets_note(self, tmp_path, db):
        argv, mode, _r, _p = _argv_for(_tone_with(tmp_path / "t.maxpat", db, "kslider"))
        assert mode == "record" and "--note" in argv

    def test_tone_only_no_note(self, tmp_path, db):
        argv, mode, _r, _p = _argv_for(_tone_patch(tmp_path / "t.maxpat", db))
        assert mode == "record" and "--note" not in argv

    def test_adc_load_only_no_dsp(self, tmp_path, db):
        argv, mode, reasons, parsed = _argv_for(_adc_patch(tmp_path / "a.maxpat", db))
        assert mode == "load-only"
        assert "--record" not in argv and "--dsp-on-load" not in argv
        assert parsed.dsp_on_load is False and parsed.record is None
        assert any("audio-input" in r for r in reasons)

    def test_adc_live_inputs_records(self, tmp_path, db):
        argv, mode, _r, parsed = _argv_for(_adc_patch(tmp_path / "a.maxpat", db), "--live-inputs")
        assert mode == "record" and parsed.record == 3.0
        assert "--dsp-on-load" not in argv

    def test_nodac_load_only_dsp_on(self, tmp_path, db):
        argv, mode, reasons, parsed = _argv_for(_nodac_patch(tmp_path / "n.maxpat", db))
        assert mode == "load-only" and parsed.dsp_on_load is True
        assert any("output not tapped" in r for r in reasons)

    def test_record_zero(self, tmp_path, db):
        argv, mode, reasons, parsed = _argv_for(_tone_patch(tmp_path / "t.maxpat", db),
                                                "--record", "0")
        assert mode == "load-only" and parsed.dsp_on_load is True and parsed.record is None
        assert "record disabled (--record 0)" in reasons

    def test_custom_note(self, tmp_path, db):
        argv, _m, _r, parsed = _argv_for(_tone_with(tmp_path / "t.maxpat", db, "notein"),
                                         "--note", "64", "90")
        j = argv.index("--note")
        assert argv[j + 1:j + 3] == ["64", "90"]

    def test_shot_rules(self, tmp_path, db, monkeypatch):
        path = _tone_patch(tmp_path / "t.maxpat", db)
        argv, *_ = _argv_for(path, "--no-shot")
        assert "--shot" not in argv
        monkeypatch.setattr(live.sys, "platform", "darwin")
        argv, _m, _r, parsed = _argv_for(path)
        assert "--shot" in argv and parsed.shot == ""
        monkeypatch.setattr(live.sys, "platform", "linux")
        argv, *_ = _argv_for(path)
        assert "--shot" not in argv

    def test_net_flags_only_when_given(self, tmp_path, db):
        path = _tone_patch(tmp_path / "t.maxpat", db)
        argv, _m, _r, parsed = _argv_for(path)
        assert "--port" not in argv and "--settle" not in argv
        assert parsed.port == bridge.BRIDGE_PORT and parsed.settle == 3.0
        argv, _m, _r, parsed = _argv_for(path, "--port", "7409", "--settle", "0.5")
        assert parsed.port == 7409 and parsed.settle == 0.5


class TestInputScan:

    def test_bpatcher_child_with_adc(self, tmp_path):
        child = _raw_patch([_newobj(1, "adc~ 1 2")])
        (tmp_path / "child.maxpat").write_text(json.dumps(child))
        parent = _raw_patch([{"id": "obj-1", "maxclass": "bpatcher", "name": "child.maxpat",
                              "numinlets": 0, "numoutlets": 0,
                              "patching_rect": [20.0, 20.0, 200.0, 100.0]}])
        (tmp_path / "parent.maxpat").write_text(json.dumps(parent))
        scan = live.scan_patch(tmp_path / "parent.maxpat")
        assert scan["inputs"] is True
        assert scan["input_where"] == ["child.maxpat:obj-1"]

    def test_comment_does_not_count(self, tmp_path):
        patch = _raw_patch([{"id": "obj-1", "maxclass": "comment", "text": "adc~",
                             "numinlets": 1, "numoutlets": 0,
                             "patching_rect": [20.0, 20.0, 80.0, 20.0]}])
        (tmp_path / "c.maxpat").write_text(json.dumps(patch))
        assert live.scan_patch(tmp_path / "c.maxpat")["inputs"] is False

    def test_ezadc_maxclass_and_nested(self, tmp_path):
        inner = {"id": "obj-9", "maxclass": "ezadc~", "numinlets": 1, "numoutlets": 2,
                 "patching_rect": [20.0, 20.0, 45.0, 45.0]}
        sub = _newobj(1, "p inputs")
        sub["patcher"] = _raw_patch([inner])["patcher"]
        (tmp_path / "e.maxpat").write_text(json.dumps(_raw_patch([sub])))
        scan = live.scan_patch(tmp_path / "e.maxpat")
        assert scan["inputs"] is True and scan["input_where"] == ["e.maxpat:obj-9"]


# ---------------------------------------------------------------------------
# map_findings (severity-contract.md section 7)
# ---------------------------------------------------------------------------

def _report(**kw) -> dict:
    rep = {
        "patch": "/x/t.maxpat", "copy": "/x/__maxbridge_t.maxpat", "run_dir": "/tmp/r",
        "taps": {"L": 1, "R": 1}, "tap_boxes": [], "unsupported": [], "warnings": [],
        "load": {"open_s": 0.1, "pong_s": 0.2}, "errors": [], "events_raw": [],
        "record": None, "shot": None, "closed": None, "feedback_suspected": False,
        "console_write": {"status": "ok", "new_lines": []}, "errors_distinct": [],
        "max_sr": 44100, "note": None, "note_target": None, "dsp_before": 0,
        "dsp_stop_sent": True, "verdict": "clean", "exit_code": 0,
    }
    rep.update(kw)
    return rep


def _distinct(key: str, n: int = 1) -> dict:
    return {"key": key, "sources": {"error": n, "console": 0, "console_write": 0},
            "occurrences": n, "first_t": 0.1}


def _rec(flags, warnings=()) -> dict:
    return {"wav": "/tmp/r/out.wav", "seconds": 3.0, "sample_rate": 44100,
            "header_sample_rate": 44100, "channels": {}, "flags": list(flags),
            "warnings": list(warnings)}


def _sev(rows):
    return [r["severity"] for r in rows]


class TestMapFindings:

    @pytest.mark.parametrize("wording", bridge.ERROR_WORDINGS)
    def test_wordings_are_blockers(self, wording):
        rows = live.map_findings(_report(errors_distinct=[_distinct(f"obj: {wording} x", 2)],
                                         verdict="findings", exit_code=1))
        assert _sev(rows) == ["blocker"]
        assert rows[0]["finding"] == f"MAX console: obj: {wording} x (x2)"
        assert rows[0]["suggestion"]

    def test_wording_suggestions(self):
        rows = live.map_findings(_report(errors_distinct=[
            _distinct("osc~: No such object"), _distinct("gen~: failed to compile patcher")]))
        assert "Rule #1" in rows[0]["suggestion"]
        assert "genexpr-rules.md" in rows[1]["suggestion"]

    def test_other_error_is_warning(self):
        rows = live.map_findings(_report(errors_distinct=[_distinct("sfplay~: can't open file")]))
        assert _sev(rows) == ["warning"]

    @pytest.mark.parametrize("flag,sev", [
        ("nonfinite", "blocker"), ("runaway", "blocker"), ("clipping", "warning"),
        ("dc_offset", "warning"), ("silent", "warning"), ("something_new", "warning"),
    ])
    def test_record_flags(self, flag, sev):
        rows = live.map_findings(_report(record=_rec([flag])))
        assert _sev(rows) == [sev]

    @pytest.mark.parametrize("trigger", live.UNRELIABLE_FLAGS)
    def test_unreliable_demotes_every_flag(self, trigger):
        rows = live.map_findings(_report(record=_rec(
            ["nonfinite", "clipping", trigger], [f"{trigger}: measures unreliable"])))
        assert _sev(rows) == ["note", "note", "note"]
        assert all("measures unreliable" in r["finding"] for r in rows)

    def test_record_and_report_warnings_are_notes(self):
        rows = live.map_findings(_report(
            record=_rec([], ["sr_header_mismatch: header 48000, MAX 44100"]),
            warnings=[bridge.DSP_UNKNOWN_WARNING, "--note: no notein or kslider to drive"]))
        assert _sev(rows) == ["note", "note", "note"]

    def test_unsupported_is_note_despite_exit_code(self):
        rows = live.map_findings(_report(
            unsupported=[{"box_id": "obj-3", "path": "top", "name": "mc.dac~", "reason": "x"}],
            verdict="findings", exit_code=1))
        assert _sev(rows) == ["note"]
        assert rows[0]["finding"] == "not tapped: mc.dac~ at top"

    def test_shot_error_is_note(self):
        rows = live.map_findings(_report(shot={"error": "no window", "png": "/tmp/s.png"},
                                         verdict="findings", exit_code=1))
        assert _sev(rows) == ["note"] and "Screen Recording" in rows[0]["suggestion"]

    def test_closed_false_is_warning(self):
        rows = live.map_findings(_report(closed=False))
        assert _sev(rows) == ["warning"] and "WITHOUT saving" in rows[0]["suggestion"]

    def test_feedback_is_warning(self):
        rows = live.map_findings(_report(feedback_suspected=True))
        assert _sev(rows) == ["warning"]

    def test_clean_report_is_empty(self):
        assert live.map_findings(_report(record=_rec([]), closed=True,
                                         shot={"png": "/tmp/s.png", "window_id": 1})) == []

    def test_every_row_is_live(self):
        rows = live.map_findings(_report(
            errors_distinct=[_distinct("osc~: No such object"), _distinct("other")],
            record=_rec(["clipping"], ["sr_header_mismatch: x"]), warnings=["w"],
            unsupported=[{"name": "plugout~", "path": "top"}], shot={"error": "e"},
            closed=False, feedback_suspected=True))
        assert len(rows) == 9
        assert all(r["source"] == "live" for r in rows)


# ---------------------------------------------------------------------------
# Skip paths: no copy is ever written
# ---------------------------------------------------------------------------

class TestSkip:

    def test_nothing_listening(self, tmp_path, db, monkeypatch, capsys):
        calls = []
        monkeypatch.setattr(bridge, "run_check", lambda a: calls.append(a))
        src = _tone_patch(tmp_path / "tone.maxpat", db)
        rc = live.main([str(src), "--port", str(_free_port()), "--reply-port", "0",
                        "--timeout", "0.3", "--json"])
        res = json.loads(capsys.readouterr().out)
        assert rc == 2 and res["status"] == "skipped" and res["exit_code"] == 2
        assert "toggle" in res["hint"] and res["patches"] == []
        assert calls == [] and _no_copies(tmp_path)

    def test_max_not_running(self, tmp_path, db, monkeypatch, capsys):
        monkeypatch.setattr(live, "_max_running", lambda: False)
        src = _tone_patch(tmp_path / "tone.maxpat", db)
        with FakeBridge() as fb:
            rc, res = _run(fb.port, src, capsys=capsys)
            time.sleep(0.1)
        assert rc == 2 and res["hint"].startswith("MAX is not running")
        assert fb.received == [] and _no_copies(tmp_path)

    def test_no_bridge_patch(self, tmp_path, db, monkeypatch, capsys):
        monkeypatch.setattr(bridge, "BRIDGE_PATCH", tmp_path / "missing.maxpat")
        src = _tone_patch(tmp_path / "tone.maxpat", db)
        rc, res = _run(_free_port(), src, capsys=capsys)
        assert rc == 2 and "not available in this install" in res["hint"]

    def test_unknown_max_state_still_pings(self, tmp_path, db, monkeypatch, capsys):
        monkeypatch.setattr(live, "_max_running", lambda: None)
        src = _tone_patch(tmp_path / "tone.maxpat", db)
        with FakeBridge() as fb:
            rc, res = _run(fb.port, src, capsys=capsys)
        assert rc == 0 and res["status"] == "ran", res

    def test_no_patches(self, tmp_path, capsys):
        rc, res = _run(_free_port(), tmp_path / "__maxbridge_x.maxpat", tmp_path / "y.txt",
                       capsys=capsys)
        assert rc == 2 and res["status"] == "skipped"
        assert {e["reason"] for e in res["excluded"]} == {"bridge temp copy", "not a .maxpat"}


# ---------------------------------------------------------------------------
# Runs on FakeBridge
# ---------------------------------------------------------------------------

class TestRun:

    def test_error_run_blocker(self, tmp_path, db, capsys):
        src = _tone_patch(tmp_path / "tone.maxpat", db)
        before = src.read_bytes()
        with FakeBridge(errors=True) as fb:
            rc, res = _run(fb.port, src, capsys=capsys)
        assert rc == 1 and res["status"] == "ran", res
        (entry,) = res["patches"]
        blockers = [f for f in entry["findings"] if f["severity"] == "blocker"]
        assert len(blockers) == 1 and "No such object" in blockers[0]["finding"]
        assert res["counts"]["blocker"] == 1
        assert src.read_bytes() == before and _no_copies(tmp_path)

    def test_clean_run(self, tmp_path, db, capsys):
        src = _tone_patch(tmp_path / "tone.maxpat", db)
        with FakeBridge() as fb:
            rc, res = _run(fb.port, src, capsys=capsys)
        assert rc == 0, res
        (entry,) = res["patches"]
        assert entry["status"] == "checked" and entry["mode"] == "record"
        assert entry["record"] is not None and entry["verdict"] == "clean"
        assert res["reminder"] == live.REMINDER and _no_copies(tmp_path)

    def test_refused(self, tmp_path, db, monkeypatch, capsys):
        src = _tone_patch(tmp_path / "tone.maxpat", db)
        monkeypatch.setattr(bridge, "_allowed_roots", lambda: [tmp_path / "elsewhere"])
        with FakeBridge() as fb:
            rc, res = _run(fb.port, src, capsys=capsys)
        assert res["patches"][0]["status"] == "refused"
        assert "/open" not in fb.addresses and rc == 0


class TestDspOnLoadEndToEnd:

    def test_nodac_dsp_off(self, tmp_path, db, capsys):
        src = _nodac_patch(tmp_path / "n.maxpat", db)
        with FakeBridge(dsp_on=0) as fb:
            rc, res = _run(fb.port, src, capsys=capsys)
        assert rc == 0, res
        assert res["patches"][0]["mode"] == "load-only"
        i_open = fb.addresses.index("/open")
        assert fb.received.index(("/dsp", [1])) < i_open < fb.received.index(("/dsp", [0]))
        assert fb.dsp_on == 0

    def test_nodac_dsp_on(self, tmp_path, db, capsys):
        src = _nodac_patch(tmp_path / "n.maxpat", db)
        with FakeBridge(dsp_on=1) as fb:
            rc, res = _run(fb.port, src, capsys=capsys)
        assert rc == 0, res
        assert ("/dsp", [0]) not in fb.received and fb.dsp_on == 1

    def test_adc_dsp_off_never_on(self, tmp_path, db, capsys):
        src = _adc_patch(tmp_path / "a.maxpat", db)
        with FakeBridge(dsp_on=0) as fb:
            rc, res = _run(fb.port, src, capsys=capsys)
        assert rc == 0, res
        assert ("/dsp", [1]) not in fb.received and "/sf" not in fb.addresses
        assert fb.dsp_on == 0

    def test_adc_dsp_already_on_note(self, tmp_path, db, capsys):
        src = _adc_patch(tmp_path / "a.maxpat", db)
        with FakeBridge(dsp_on=1) as fb:
            rc, res = _run(fb.port, src, capsys=capsys)
        notes = [f["finding"] for f in res["patches"][0]["findings"] if f["severity"] == "note"]
        assert any(n.startswith("DSP was already on") for n in notes), res
        assert rc == 0 and ("/dsp", [1]) not in fb.received


class TestBatch:

    def test_abort_on_first_bridge_failed(self, tmp_path, db, capsys):
        a = _tone_patch(tmp_path / "a.maxpat", db)
        b = _tone_patch(tmp_path / "b.maxpat", db)
        with FakeBridge(mute_after_open=True) as fb:
            rc, res = _run(fb.port, a, b, capsys=capsys)
        assert rc == 2 and res["status"] == "aborted"
        assert "MAX stopped answering during a.maxpat" in res["hint"]
        assert res["patches"][1]["status"] == "not checked"
        assert fb.addresses.count("/open") == 1
        assert _no_copies(tmp_path)

    def test_crash_is_a_warning(self, tmp_path, db, monkeypatch, capsys):
        a = _tone_patch(tmp_path / "a.maxpat", db)
        b = _tone_patch(tmp_path / "b.maxpat", db)
        real = bridge.run_check
        calls = {"n": 0}

        def flaky(args):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("boom")
            return real(args)

        monkeypatch.setattr(bridge, "run_check", flaky)
        with FakeBridge() as fb:
            rc, res = _run(fb.port, a, b, capsys=capsys)
        first, second = res["patches"]
        assert first["status"] == "failed"
        assert first["findings"][0]["severity"] == "warning"
        assert "live check crashed" in first["findings"][0]["finding"]
        assert second["status"] == "checked" and rc == 1


# ---------------------------------------------------------------------------
# D-04: the wrapper never toggles the kill switch or opens the bridge patch
# ---------------------------------------------------------------------------

def test_d04_ast_guard():
    tree = ast.parse(LIVE_PY.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            assert node.func.attr != "send", ast.dump(node)
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            assert node.value not in ("open", "osascript", "/dsp", "/listen"), node.value
