"""Q38 part 1 (quick 261022-mis): the shipped-idiom allowlist.

Every cord a Cycling '74 help patch ships is a cord MAX itself created and
saved, so validation Layer 3 must never type/role-flag it (or propose to
strip it), and ``replace_box_safe`` must never orphan it. The pipeline is
bundle help cords -> ``help_io.scan_help_idioms`` -> ``--apply idioms`` ->
``.claude/max-objects/idioms.json`` -> ``ObjectDatabase.is_shipped_idiom`` ->
Layer 3 / ``_rewire_type_gated``.

Hermetic tests use a fake bundle and fake DB under ``tmp_path`` or a scratch
copy of the real DB; the real DB is only read. Tests that read the installed
Max bundle carry ``requires_max``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

import tools.help_io as help_io
import tools.sync_max_bundle as sync
from src.maxpat.db_lookup import ObjectDatabase, outlet_signal_class
from src.maxpat.patcher import Patcher
from src.maxpat.validation import _validate_connections, validate_patch
from tests.conftest import MAX_APP_PATH
from tests.test_db_tooling import scratch_copy_of_real_db
from tests.test_sync_max_bundle import _make_bundle, _make_db, _tree_bytes

REPO_ROOT = Path(__file__).resolve().parents[1]
REAL_DB = REPO_ROOT / ".claude" / "max-objects"


# ── Fake help files ───────────────────────────────────────────────


def _box(bid: str, maxclass: str = "newobj", text: str | None = None, *,
         ni: int = 1, no: int = 1, outlettype: list[str] | None = None, **extra) -> dict:
    box = {"id": bid, "maxclass": maxclass, "numinlets": ni, "numoutlets": no}
    if text is not None:
        box["text"] = text
    if outlettype is not None:
        box["outlettype"] = outlettype
    box.update(extra)
    return box


def _cord(src: str, outlet: int, dst: str, inlet: int) -> dict:
    return {"patchline": {"source": [src, outlet], "destination": [dst, inlet]}}


def _patcher(boxes: list[dict], lines: list[dict], **extra) -> dict:
    patcher = {"boxes": [{"box": b} for b in boxes], "lines": lines}
    patcher.update(extra)
    return patcher


def _write_help(app: Path, rel: str, boxes: list[dict], lines: list[dict],
                appversion: tuple[int, int, int] = (9, 0, 0)) -> Path:
    path = app / "Contents" / "Resources" / "C74" / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    patcher = _patcher(boxes, lines)
    major, minor, revision = appversion
    patcher["appversion"] = {"major": major, "minor": minor, "revision": revision,
                             "architecture": "x64", "modernui": 1}
    path.write_text(json.dumps({"patcher": patcher}))
    return path


def _cycle_times(app: Path, rel: str = "help/msp/cords.maxhelp") -> Path:
    return _write_help(
        app, rel,
        [_box("obj-1", text="cycle~ 440", ni=2, no=1, outlettype=["signal"]),
         _box("obj-2", text="*~ 0.5", ni=2, no=1, outlettype=["signal"])],
        [_cord("obj-1", 0, "obj-2", 0)],
    )


@pytest.fixture
def app(tmp_path: Path) -> Path:
    return _make_bundle(tmp_path)


# ── Mining ────────────────────────────────────────────────────────


class TestMining:
    def test_records_a_signal_cord(self, app: Path) -> None:
        _cycle_times(app)
        scan = help_io.scan_help_idioms(app)
        assert scan["available"] is True
        assert "0 signal *~ 0" in scan["pairs"]["cycle~"]
        assert scan["recorded_cords"] == 1

    def test_outlet_signal_class_is_shared(self) -> None:
        assert outlet_signal_class(["signal", "bang"], 0) == "signal"
        assert outlet_signal_class(["multichannelsignal"], 0) == "signal"
        assert outlet_signal_class(["signal", "bang"], 1) == "control"
        assert outlet_signal_class(["signal", ""], 1) == "control"
        assert outlet_signal_class(["signal"], 1) is None
        assert outlet_signal_class(None, 0) is None
        assert outlet_signal_class(["signal"], "0") is None
        assert outlet_signal_class(["signal"], -1) is None

    def test_pairs_are_sorted_by_outlet_class_dst_inlet(self, app: Path) -> None:
        _write_help(
            app, "help/max/many.maxhelp",
            [_box("a", text="unpack 0 0 0 0 0 0 0 0 0 0 0", ni=1, no=11, outlettype=[""] * 11),
             _box("b", text="pack 0 0 0 0 0 0 0 0 0 0 0", ni=11, no=1, outlettype=[""])],
            [_cord("a", 10, "b", 2), _cord("a", 2, "b", 10), _cord("a", 2, "b", 1)],
        )
        pairs = help_io.scan_help_idioms(app)["pairs"]["unpack"]
        assert pairs == ["2 control pack 1", "2 control pack 10", "10 control pack 2"]

    def test_ineligible_endpoints_are_excluded(self, app: Path) -> None:
        sig = _box("sig", text="cycle~", ni=2, no=1, outlettype=["signal"])
        targets = [
            _box("in", "inlet", ni=0, no=1, outlettype=[""]),
            _box("out", "outlet", ni=1, no=0),
            _box("p", text="p inner", ni=1, no=1, outlettype=[""],
                 patcher=_patcher([], [])),
            _box("bp", "bpatcher", ni=1, no=1, outlettype=[""]),
            _box("js", text="js thing.js", ni=1, no=1, outlettype=[""]),
            _box("cb", "codebox", ni=1, no=1, outlettype=[""]),
            _box("emb", text="thing", ni=1, no=1, outlettype=[""],
                 patcher=_patcher([], [])),
        ]
        lines = [_cord("sig", 0, "out", 0), _cord("in", 0, "sig", 0)]
        lines += [_cord("sig", 0, t["id"], 0) for t in targets[2:]]
        _write_help(app, "help/max/excluded.maxhelp", [sig, *targets], lines)
        scan = help_io.scan_help_idioms(app)
        assert scan["excluded_cords"] == 7
        assert scan["recorded_cords"] == 0
        assert scan["pairs"] == {}

    def test_idiom_endpoint(self) -> None:
        assert help_io.idiom_endpoint(_box("a", text="cycle~ 440")) == "cycle~"
        assert help_io.idiom_endpoint(_box("a", "toggle")) == "toggle"
        assert help_io.idiom_endpoint(_box("a", "inlet")) is None
        assert help_io.idiom_endpoint(_box("a", text="poly~ voice 4")) is None
        assert help_io.idiom_endpoint(_box("a", text="gen.codebox~")) is None
        assert help_io.idiom_endpoint(_box("a", text="", ni=0, no=0)) is None

    def test_unclassified_source_is_counted(self, app: Path) -> None:
        _write_help(
            app, "help/max/unclassified.maxhelp",
            [_box("a", text="metro 100", ni=2, no=1),
             _box("b", text="print", ni=1, no=0)],
            [_cord("a", 0, "b", 0)],
        )
        scan = help_io.scan_help_idioms(app)
        assert scan["unclassified_cords"] == 1
        assert scan["recorded_cords"] == 0

    def test_malformed_cords_are_counted(self, app: Path) -> None:
        _write_help(
            app, "help/max/malformed.maxhelp",
            [_box("a", text="metro 100", ni=2, no=1, outlettype=["bang"]),
             _box("b", text="print", ni=1, no=0)],
            [{"patchline": {"source": ["a"], "destination": ["b", 0]}},
             {"patchline": {"source": ["a", "0"], "destination": ["b", 0]}},
             {"patchline": {"source": ["a", 0], "destination": ["missing", 0]}},
             "junk"],
        )
        scan = help_io.scan_help_idioms(app)
        assert scan["malformed_cords"] == 4
        assert scan["recorded_cords"] == 0


class TestWalkLimits:
    def test_gen_and_rnbo_internals_are_never_walked(self, app: Path) -> None:
        inner = _patcher(
            [_box("x", text="cycle~", ni=2, no=1, outlettype=["signal"]),
             _box("y", text="*~", ni=2, no=1, outlettype=["signal"])],
            [_cord("x", 0, "y", 0)],
        )
        boxes = [
            _box("g", text="gen~", ni=1, no=1, outlettype=["signal"], patcher=dict(inner)),
            _box("d", text="p dsp", ni=1, no=1, outlettype=[""],
                 patcher=dict(inner, classnamespace="dsp.gen")),
            _box("r", text="p rn", ni=1, no=1, outlettype=[""],
                 patcher=dict(inner, classnamespace="rnbo")),
        ]
        _write_help(app, "help/msp/internals.maxhelp", boxes, [])
        scan = help_io.scan_help_idioms(app)
        assert scan["internal_patchers_skipped"] == 3
        assert scan["pairs"] == {}

    def test_ordinary_subpatchers_are_walked(self, app: Path) -> None:
        inner = _patcher(
            [_box("x", text="cycle~", ni=2, no=1, outlettype=["signal"]),
             _box("y", text="*~", ni=2, no=1, outlettype=["signal"])],
            [_cord("x", 0, "y", 0)],
        )
        _write_help(app, "help/msp/sub.maxhelp",
                    [_box("p", text="p sub", ni=0, no=0, patcher=inner)], [])
        assert help_io.scan_help_idioms(app)["pairs"] == {"cycle~": ["0 signal *~ 0"]}

    def test_depth_is_capped(self, app: Path) -> None:
        deepest = _patcher(
            [_box("x", text="cycle~", ni=2, no=1, outlettype=["signal"]),
             _box("y", text="*~", ni=2, no=1, outlettype=["signal"])],
            [_cord("x", 0, "y", 0)],
        )
        patcher = deepest
        for level in range(help_io.MAX_PATCHER_DEPTH + 2):
            patcher = _patcher([_box(f"p{level}", text="p deep", ni=0, no=0, patcher=patcher)], [])
        path = app / "Contents" / "Resources" / "C74" / "help" / "max" / "deep.maxhelp"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"patcher": patcher}))
        scan = help_io.scan_help_idioms(app)
        assert scan["depth_capped"] == 1
        assert scan["pairs"] == {}

    def test_bad_files_are_recorded_not_raised(self, app: Path) -> None:
        path = app / "Contents" / "Resources" / "C74" / "help" / "max" / "broken.maxhelp"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{not json")
        (path.parent / "list.maxhelp").write_text("[1, 2]")
        _cycle_times(app)
        scan = help_io.scan_help_idioms(app)
        assert sorted(b["file"] for b in scan["bad_files"]) == [
            "help/max/broken.maxhelp", "help/max/list.maxhelp",
        ]
        assert scan["pairs"] == {"cycle~": ["0 signal *~ 0"]}

    def test_no_bundle_is_unavailable(self, tmp_path: Path) -> None:
        scan = help_io.scan_help_idioms(tmp_path / "Nope.app")
        assert scan["available"] is False
        assert "C74" in scan["reason"]


# ── Writer ────────────────────────────────────────────────────────


def _doc(pairs: dict) -> dict:
    return {"_comment": "c", "generator": "g", "max_version": "9.2.0",
            "source": "s", "pairs": pairs}


class TestWriter:
    def test_refuses_any_other_path(self, tmp_path: Path) -> None:
        root = tmp_path / "db"
        root.mkdir()
        for bad in (root / "groups.json", root / "max" / "idioms.json", tmp_path / "idioms.json"):
            with pytest.raises(sync.WriteRefused):
                sync.write_idioms_file(bad, _doc({}), root)
        assert not any(root.iterdir())

    def test_canonical_and_idempotent(self, tmp_path: Path) -> None:
        root = tmp_path / "db"
        root.mkdir()
        data = _doc({"zeta": ["0 control b 0"], "alpha": ["1 signal a 0", "0 signal a 1"]})
        assert sync.write_idioms_file(root / "idioms.json", data, root) is True
        raw = (root / "idioms.json").read_bytes()
        assert raw == sync.canonical_idioms_bytes(data)
        text = raw.decode("utf-8")
        assert text.endswith("\n")
        assert text.index('"alpha"') < text.index('"zeta"')
        assert json.loads(text)["pairs"]["alpha"] == ["0 signal a 1", "1 signal a 0"]
        mtime = (root / "idioms.json").stat().st_mtime_ns
        assert sync.write_idioms_file(root / "idioms.json", data, root) is False
        assert (root / "idioms.json").read_bytes() == raw
        assert (root / "idioms.json").stat().st_mtime_ns == mtime

    def test_additive(self, tmp_path: Path) -> None:
        root = tmp_path / "db"
        root.mkdir()
        old = _doc({"cycle~": ["0 signal *~ 0"], "gone": ["0 control print 0"]})
        sync.write_idioms_file(root / "idioms.json", old, root)
        mined = {"available": True, "pairs": {"cycle~": ["0 signal dac~ 0"]}}
        target = sync.build_idioms_target(mined, sync.load_idioms(root), {"short_version": "9.2.0"})
        assert target["pairs"] == {
            "cycle~": ["0 signal *~ 0", "0 signal dac~ 0"],
            "gone": ["0 control print 0"],
        }
        with pytest.raises(sync.AdditiveViolation):
            sync.check_idioms_additive(old, _doc({"cycle~": ["0 signal *~ 0"]}))
        with pytest.raises(sync.AdditiveViolation):
            sync.write_idioms_file(root / "idioms.json", _doc({"cycle~": ["0 signal *~ 0"]}), root)

    def test_file_without_pairs_is_unreproducible(self, tmp_path: Path) -> None:
        root = tmp_path / "db"
        root.mkdir()
        (root / "idioms.json").write_text(json.dumps({"_comment": "x"}) + "\n")
        with pytest.raises(sync.StyleUnreproducible):
            sync.load_idioms(root)

    def test_absent_file_loads_as_none(self, tmp_path: Path) -> None:
        assert sync.load_idioms(tmp_path) is None


# ── CLI on the fake world ─────────────────────────────────────────


@pytest.fixture
def world(tmp_path: Path) -> dict:
    app = _make_bundle(tmp_path)
    db_root = _make_db(tmp_path)
    _cycle_times(app)
    return {
        "app": app,
        "db_root": db_root,
        "argv": ["--max-app", str(app), "--db-root", str(db_root),
                 "--repo-root", str(tmp_path / "repo")],
    }


_SUMMARY_RE = re.compile(
    r"^  idioms +: (\d+) pairs from (\d+) help cords \((\d+) excluded, (\d+) unclassified\), "
    r"\+(\d+) pending \(--apply idioms\)$",
    re.M,
)


class TestCli:
    def test_section_keys_place_idioms_after_groups(self) -> None:
        keys = sync.SECTION_KEYS
        assert keys[keys.index("groups") + 1] == "idioms"
        assert "idioms" in sync.APPLY_MODES

    def test_apply_writes_only_idioms_json(self, world: dict, capsys) -> None:
        root = world["db_root"]
        before = sync.run_report(root, world["app"])["sections"]["idioms"]
        assert before["available"] is True
        assert before["pending"] > 0
        assert before["committed"] == 0
        assert not (root / "idioms.json").exists()
        tree = _tree_bytes(root)

        assert sync.main([*world["argv"], "--apply", "idioms"]) == 0
        out = capsys.readouterr().out
        assert "applied idioms" in out
        after_tree = _tree_bytes(root)
        assert set(after_tree) - set(tree) == {"idioms.json"}
        assert {k: v for k, v in after_tree.items() if k != "idioms.json"} == tree
        assert json.loads((root / "idioms.json").read_text())["pairs"] == {
            "cycle~": ["0 signal *~ 0"],
        }

        after = sync.run_report(root, world["app"])["sections"]["idioms"]
        assert after["pending"] == 0
        assert after["committed"] == after["pairs"] == 1

        raw = (root / "idioms.json").read_bytes()
        assert sync.main([*world["argv"], "--apply", "idioms"]) == 0
        assert (root / "idioms.json").read_bytes() == raw

        assert sync.main(world["argv"]) == 0
        match = _SUMMARY_RE.search(capsys.readouterr().out)
        assert match is not None
        assert match.group(1) == "1" and match.group(5) == "0"

    def test_dry_run_summary_reports_pending(self, world: dict, capsys) -> None:
        assert sync.main(world["argv"]) == 0
        match = _SUMMARY_RE.search(capsys.readouterr().out)
        assert match is not None
        assert int(match.group(5)) > 0
        assert not (world["db_root"] / "idioms.json").exists()


# ── ObjectDatabase lookup ─────────────────────────────────────────


def _lookup_db(tmp_path: Path, pairs: dict | None) -> ObjectDatabase:
    root = _make_db(tmp_path)
    (root / "aliases.json").write_text(json.dumps({"aliases": {"sel": "select"}}, indent=2) + "\n")
    if pairs is not None:
        (root / "idioms.json").write_text(json.dumps(_doc(pairs), indent=2) + "\n")
    return ObjectDatabase(root)


class TestLookup:
    def test_absent_file_never_matches(self, tmp_path: Path) -> None:
        db = _lookup_db(tmp_path, None)
        assert db.is_shipped_idiom("cycle~", 0, "signal", "*~", 0) is False

    def test_alias_canonical_both_ways(self, tmp_path: Path) -> None:
        db = _lookup_db(tmp_path, {"sel": ["0 control print 0"],
                                   "metro": ["0 control sel 0"]})
        assert db.is_shipped_idiom("select", 0, "control", "print", 0) is True
        assert db.is_shipped_idiom("sel", 0, "control", "print", 0) is True
        assert db.is_shipped_idiom("metro", 0, "control", "select", 0) is True
        assert db.is_shipped_idiom("metro", 0, "control", "sel", 0) is True

    def test_class_and_ports_must_match(self, tmp_path: Path) -> None:
        db = _lookup_db(tmp_path, {"sel": ["0 control print 0"]})
        assert db.is_shipped_idiom("sel", 0, "signal", "print", 0) is False
        assert db.is_shipped_idiom("sel", 0, None, "print", 0) is False
        assert db.is_shipped_idiom("sel", 1, "control", "print", 0) is False
        assert db.is_shipped_idiom("sel", 0, "control", "print", 1) is False

    def test_malformed_item_fails_fast(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="idioms.json"):
            _lookup_db(tmp_path, {"sel": ["0 control print"]})
        with pytest.raises(ValueError, match="idioms.json"):
            _lookup_db(tmp_path / "b", {"sel": ["x control print 0"]})


# ── Layer 3 exemption and replace_box_safe mirror (scratch real DB) ──


@pytest.fixture(scope="module")
def scratch_dbs(tmp_path_factory) -> dict:
    """Two scratch copies of the real DB: no pair listed, and two listed."""
    out = {}
    for label, pairs in (
        ("unlisted", {}),
        ("listed", {"cycle~": ["0 signal print 0"], "edge~": ["0 control *~ 0"]}),
    ):
        root = scratch_copy_of_real_db(tmp_path_factory.mktemp(label))
        (root / "idioms.json").write_text(json.dumps(_doc(pairs), indent=2) + "\n")
        out[label] = ObjectDatabase(root)
    return out


def _one_cord(src: dict, dst: dict, outlet: int, inlet: int) -> dict:
    return {"patcher": {"boxes": [{"box": src}, {"box": dst}],
                        "lines": [_cord(src["id"], outlet, dst["id"], inlet)]}}


def _cycle_print(outlet: int = 0) -> dict:
    return _one_cord(
        _box("obj-1", text="cycle~ 440", ni=2, no=1, outlettype=["signal"]),
        _box("obj-2", text="print", ni=1, no=0),
        outlet, 0,
    )


def _edge_times(outlettype: list[str]) -> dict:
    return _one_cord(
        _box("obj-1", text="edge~", ni=1, no=2, outlettype=outlettype),
        _box("obj-2", text="*~ 0.5", ni=2, no=1, outlettype=["signal"]),
        0, 0,
    )


class TestExemption:
    def test_unlisted_signal_to_control_is_flagged(self, scratch_dbs: dict) -> None:
        results = _validate_connections(_cycle_print(), scratch_dbs["unlisted"])
        assert len(results) == 1
        assert "Signal outlet to control-only inlet" in results[0].message
        assert results[0].proposed_removal == ("obj-1", 0, "obj-2", 0)

    def test_listed_cord_is_not_flagged(self, scratch_dbs: dict) -> None:
        assert _validate_connections(_cycle_print(), scratch_dbs["listed"]) == []
        conn = [r for r in validate_patch(_cycle_print(), db=scratch_dbs["listed"])
                if r.layer == "connections"]
        assert conn == []

    def test_listed_names_still_get_bounds_errors(self, scratch_dbs: dict) -> None:
        results = _validate_connections(_cycle_print(outlet=3), scratch_dbs["listed"])
        assert len(results) == 1
        assert "Outlet index 3 out of bounds" in results[0].message
        assert results[0].proposed_removal is not None

    def test_role_tier_warning_is_exempt_when_listed(self, scratch_dbs: dict) -> None:
        unlisted = scratch_dbs["unlisted"]
        assert unlisted.get_signal_role("edge~", 0) not in (None, "audio")
        warned = _validate_connections(_edge_times(["bang", "bang"]), unlisted)
        assert [r.level for r in warned] == ["warning"]
        assert "connection kept" in warned[0].message
        assert _validate_connections(_edge_times(["bang", "bang"]), scratch_dbs["listed"]) == []

    def test_other_class_is_still_checked(self, scratch_dbs: dict) -> None:
        listed = scratch_dbs["listed"]
        still = _validate_connections(_edge_times(["signal", "bang"]), listed)
        assert [r.level for r in still] == ["warning"]


class TestReplaceBoxSafeMirror:
    def _orphans(self, db: ObjectDatabase) -> list[dict]:
        p = Patcher(db=db)
        osc = p.add_box("cycle~", args=["440"])
        out = p.add_box("print")
        p.add_connection(osc, 0, out, 0)
        result = p.replace_box_safe(osc, "cycle~", args=["220"])
        self.lines = [(pl.source_id, pl.source_outlet, pl.dest_id, pl.dest_inlet) for pl in p.lines]
        self.ids = (result.box.id, out.id)
        return result.orphaned

    def test_unlisted_cord_is_orphaned(self, scratch_dbs: dict) -> None:
        orphaned = self._orphans(scratch_dbs["unlisted"])
        assert len(orphaned) == 1
        assert self.lines == []

    def test_listed_cord_is_rewired(self, scratch_dbs: dict) -> None:
        assert self._orphans(scratch_dbs["listed"]) == []
        assert self.lines == [(self.ids[0], 0, self.ids[1], 0)]


# ── Live bundle ───────────────────────────────────────────────────


def _walk_scopes(patcher, depth: int = 0):
    """Yield every patcher the miner walks (same internals skipped)."""
    if not isinstance(patcher, dict) or depth > help_io.MAX_PATCHER_DEPTH:
        return
    yield patcher
    for entry in patcher.get("boxes") or []:
        box = entry.get("box") if isinstance(entry, dict) else None
        if not isinstance(box, dict):
            continue
        inner = box.get("patcher")
        if not isinstance(inner, dict):
            continue
        name = help_io.box_args(box["text"])[0] if isinstance(box.get("text"), str) \
            and box.get("maxclass") == "newobj" and box["text"].split() else box.get("maxclass")
        if name in help_io.GEN_RNBO_CONTAINERS or \
                inner.get("classnamespace") in help_io.SKIPPED_NAMESPACES:
            continue
        yield from _walk_scopes(inner, depth + 1)


_ALLOWED = ("Outlet index", "Inlet index", "Connection references missing box", "Malformed")


@pytest.mark.requires_max
def test_bundle_help_cords_are_never_flagged() -> None:
    db = ObjectDatabase()
    c74 = MAX_APP_PATH / "Contents" / "Resources" / "C74"
    checked = 0
    keys: set[tuple] = set()
    offenders: list[str] = []
    for path in sorted(c74.rglob("*.maxhelp")):
        try:
            top = json.loads(path.read_bytes())
        except (OSError, ValueError):
            continue
        if not isinstance(top, dict):
            continue
        for scope in _walk_scopes(top.get("patcher")):
            boxes = {}
            for entry in scope.get("boxes") or []:
                box = entry.get("box") if isinstance(entry, dict) else None
                if isinstance(box, dict) and box.get("id"):
                    boxes[box["id"]] = box
            for line in scope.get("lines") or []:
                pl = line.get("patchline") if isinstance(line, dict) else None
                if not isinstance(pl, dict):
                    continue
                s, d = pl.get("source"), pl.get("destination")
                if not (isinstance(s, list) and isinstance(d, list) and len(s) >= 2 and len(d) >= 2):
                    continue
                if not (isinstance(s[1], int) and isinstance(d[1], int)):
                    continue
                src, dst = boxes.get(s[0]), boxes.get(d[0])
                if src is None or dst is None:
                    continue
                sname, dname = help_io.idiom_endpoint(src), help_io.idiom_endpoint(dst)
                cls = outlet_signal_class(src.get("outlettype"), s[1])
                if sname is None or dname is None or cls is None:
                    continue
                one = [{"box": src}] if src is dst else [{"box": src}, {"box": dst}]
                patch = {"patcher": {"boxes": one, "lines": [line]}}
                checked += 1
                keys.add((sname, s[1], cls, dname, d[1]))
                for r in _validate_connections(patch, db):
                    if not r.message.startswith(_ALLOWED) and len(offenders) < 20:
                        offenders.append(f"{path.relative_to(c74)}: {r.message}")
    assert offenders == []
    assert checked > 40000, checked
    assert len(keys) > 5000, len(keys)


@pytest.mark.requires_max
def test_committed_idioms_are_current() -> None:
    assert sync.run_report(REAL_DB, MAX_APP_PATH)["sections"]["idioms"]["pending"] == 0
