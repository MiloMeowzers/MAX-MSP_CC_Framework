"""quick-261012-ubw (Q9): tests for the help-box I/O oracle.

``python3 tools/audit_db.py --help-io`` compares the numinlets/numoutlets and
outlettype MAX saved into every shipped ``.maxhelp`` box with what
``ObjectDatabase.compute_io_counts`` / ``get_outlet_types`` predict. It is the
bundle-mining foundation (review 2026-10-11 §5.5) that Q10 (C1, variable-I/O
rules) and Q11 (C2/C9, overrides and signal roles) consume, and the
"help-box oracle test" half of S6.

Test hygiene:

* Hermetic tests build a fake ``Max.app`` and a fake object DB under
  ``tmp_path`` and ALWAYS pass an explicit packages dir under ``tmp_path``,
  so they never read the real ``~/Documents/Max 9/Packages`` or the real DB
  values (Q10/Q11 DB fixes cannot break them).
* Only the ``requires_max`` class reads the real bundle, the real DB and the
  default packages dir.
* Tests never write to the repo; every output goes under ``tmp_path``.
"""

from __future__ import annotations

import copy
import json
import plistlib
import subprocess
import sys
import warnings
from pathlib import Path

import pytest

import tools.audit_db as audit_db
from src.maxpat.db_lookup import ObjectDatabase
from tests.conftest import MAX_APP_PATH
from tools import help_io

REPO_ROOT = Path(__file__).resolve().parent.parent


# ── Fixture builders ──────────────────────────────────────────────


def _make_fake_max(tmp_path: Path, version: str = "9.9.9") -> Path:
    """Build a minimal Max.app with an Info.plist and an empty help/max dir."""
    app = tmp_path / "Max.app"
    contents = app / "Contents"
    contents.mkdir(parents=True)
    with open(contents / "Info.plist", "wb") as fh:
        plistlib.dump(
            {
                "CFBundleShortVersionString": f"{version} (abc123)",
                "CFBundleVersion": version,
                "CFBundleName": "Max",
            },
            fh,
        )
    (contents / "Resources" / "C74" / "help" / "max").mkdir(parents=True)
    return app


def _c74(app: Path) -> Path:
    return app / "Contents" / "Resources" / "C74"


def _port(signal: bool = False) -> dict:
    return {"id": 0, "type": "signal" if signal else "bang", "signal": signal}


def _make_fake_db(tmp_path: Path) -> Path:
    """Write a tiny object DB under tmp_path (never the real DB values).

    * ``alpha``: 1 control inlet, 2 control outlets.
    * ``vfoo``: variable I/O, 1 inlet, one outlet per positional argument.
    * ``sigout~``: 1 control outlet; ``mcout~``: 1 signal outlet.
    * ``uiwidget``: (1,1), a non-newobj maxclass (OQ1-A).
    * ``js``: (1,1), present to prove the content-defined exclusion wins.
    * ``emptyio``: no ports at all (``lookup`` warns on it).
    """
    root = tmp_path / "db"
    (root / "max").mkdir(parents=True)
    objects = {
        "alpha": {"name": "alpha", "inlets": [_port()], "outlets": [_port(), _port()]},
        "vfoo": {
            "name": "vfoo", "variable_io": True,
            "inlets": [_port()], "outlets": [_port(), _port()],
        },
        "sigout~": {"name": "sigout~", "inlets": [_port()], "outlets": [_port(False)]},
        "mcout~": {"name": "mcout~", "inlets": [_port()], "outlets": [_port(True)]},
        "uiwidget": {"name": "uiwidget", "inlets": [_port()], "outlets": [_port()]},
        "js": {"name": "js", "inlets": [_port()], "outlets": [_port()]},
        "emptyio": {"name": "emptyio", "inlets": [], "outlets": []},
    }
    (root / "max" / "objects.json").write_text(json.dumps(objects))
    (root / "overrides.json").write_text(json.dumps({
        "objects": {},
        "variable_io_rules": {
            "vfoo": {"inlet_count": "fixed:1", "outlet_count": "arg_count"},
        },
    }))
    return root


def _newobj(box_id, text, numinlets, numoutlets, outlettype=None, patcher=None) -> dict:
    box = {
        "maxclass": "newobj",
        "id": box_id,
        "text": text,
        "numinlets": numinlets,
        "numoutlets": numoutlets,
    }
    if outlettype is not None:
        box["outlettype"] = outlettype
    if patcher is not None:
        box["patcher"] = patcher
    return {"box": box}


def _help(boxes, appversion=(9, 1, 0), classnamespace="box") -> dict:
    patcher: dict = {"boxes": boxes, "lines": []}
    if appversion is not None:
        patcher["appversion"] = {
            "major": appversion[0],
            "minor": appversion[1],
            "revision": appversion[2],
        }
    if classnamespace is not None:
        patcher["classnamespace"] = classnamespace
    return {"patcher": patcher}


def _write(path: Path, data) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))
    return path


def _cli(*args) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "tools/audit_db.py", *[str(a) for a in args]],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )


def _tracer_tree(tmp_path: Path) -> tuple[Path, Path]:
    app = _make_fake_max(tmp_path)
    db = _make_fake_db(tmp_path)
    _write(
        _c74(app) / "help" / "max" / "alpha.maxhelp",
        _help([
            _newobj("obj-1", "alpha", 1, 2),
            _newobj("obj-2", "alpha 5", 1, 3),
        ]),
    )
    return app, db


# ── Task 1: tracer ────────────────────────────────────────────────


class TestTracer:
    def test_cli_end_to_end(self, tmp_path: Path) -> None:
        app, db = _tracer_tree(tmp_path)
        j = tmp_path / "out" / "h.json"
        bl = tmp_path / "out" / "bl.json"
        result = _cli(
            "--help-io", "--max-app", app, "--db-root", db,
            "--packages-dir", tmp_path / "no-packages",
            "--json", j, "--write-baseline", bl,
        )
        assert result.returncode == 0, result.stderr
        assert "MAX help-box I/O oracle" in result.stdout
        assert "Max 9.9.9" in result.stdout

        report = json.loads(j.read_text())
        assert report["mode"] == "help-io"
        section = report["help_io"]
        assert section["available"] is True
        alpha = section["mismatches"]["bundle"]["alpha"]
        assert alpha["boxes"] == 2
        assert alpha["count_mismatches"] == 1
        sig = alpha["signatures"]["count args=1 max=1,3 db=1,2"]
        assert sig["count"] == 1
        assert sig["examples"][0] == {
            "file": "help/max/alpha.maxhelp", "box": "obj-2", "text": "alpha 5",
        }

        text = bl.read_text()
        baseline = json.loads(text)
        assert baseline["schema"] == 1
        assert baseline["sources"]["bundle"]["version"] == "9.9.9"
        assert baseline["names"]["bundle"]["alpha"]["count_mismatches"] == 1
        assert text == help_io.dump_baseline(json.loads(text))

    def test_diff_flags_an_increase_and_an_improvement(self, tmp_path: Path) -> None:
        app, db = _tracer_tree(tmp_path)
        section = help_io.scan_help_io(
            app, tmp_path / "no-packages", ObjectDatabase(db_root=db), "9.9.9"
        )
        bl = help_io.build_baseline(section)

        same = help_io.diff_baselines(bl, bl)
        assert same["regressions"] == []
        assert same["improvements"] == []
        assert same["compared_sources"] == ["bundle"]

        older = copy.deepcopy(bl)
        older["names"]["bundle"]["alpha"]["count_mismatches"] = 0
        diff = help_io.diff_baselines(older, bl)
        assert diff["regressions"] == [{
            "source": "bundle", "name": "alpha", "field": "count_mismatches",
            "baseline": 0, "live": 1,
        }]
        assert diff["improvements"] == []

        swapped = help_io.diff_baselines(bl, older)
        assert swapped["regressions"] == []
        assert len(swapped["improvements"]) == 1


# ── Task 2: full scan semantics ───────────────────────────────────


def _ui(box_id, maxclass, numinlets, numoutlets) -> dict:
    return {"box": {"maxclass": maxclass, "id": box_id,
                    "numinlets": numinlets, "numoutlets": numoutlets}}


def _inner(boxes, classnamespace="box") -> dict:
    patcher: dict = {"boxes": boxes, "lines": []}
    if classnamespace is not None:
        patcher["classnamespace"] = classnamespace
    return patcher


def _scan_boxes() -> list:
    return [
        _newobj("obj-1", "alpha", 1, 2),
        _newobj("obj-2", "alpha 5", 1, 3),
        _newobj("obj-3", "vfoo a b @attr 1", 1, 2),
        _newobj("obj-4", "sigout~", 1, 1, outlettype=["signal"]),
        _newobj("obj-5", "mcout~", 1, 1, outlettype=["multichannelsignal"]),
        _newobj("obj-6", "sigout~", 1, 1),
        _newobj("obj-7", "nosuch 1", 1, 1),
        _newobj("obj-8", "js foo.js", 1, 3),
        _newobj("obj-9", "p sub", 1, 1,
                patcher=_inner([_newobj("obj-9a", "alpha 7", 1, 9)])),
        _newobj("obj-10", "gen~", 1, 1,
                patcher=_inner([_newobj("g-1", "alpha 9", 1, 9)], "dsp.gen")),
        _newobj("obj-11", "gen~", 1, 1,
                patcher=_inner([_newobj("g-2", "alpha 9", 1, 9)], None)),
        _newobj("obj-12", "rnbo~", 1, 1,
                patcher=_inner([_newobj("r-1", "alpha 9", 1, 9)], "rnbo")),
        _newobj("obj-13a", "alpha", "x", 2),
        _newobj("obj-13b", "alpha", 1, True),
        _newobj("obj-14a", "", 1, 1),
        _newobj("obj-14b", 5, 1, 1),
        _ui("obj-15a", "uiwidget", 1, 2),
        _ui("obj-15b", "missingui", 1, 1),
        _ui("obj-15c", "v8.codebox", 1, 1),
        _newobj("obj-16", "emptyio", 0, 0),
    ]


def _scan_tree(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Fake bundle + fake packages dir exercising every scan rule."""
    app = _make_fake_max(tmp_path)
    db = _make_fake_db(tmp_path)
    c74 = _c74(app)
    _write(c74 / "help" / "max" / "scan.maxhelp", _help(_scan_boxes()))
    _write(c74 / "packages" / "BPkg" / "help" / "b.maxhelp",
           _help([_newobj("obj-1", "alpha", 1, 2)], appversion=None))
    (c74 / "help" / "max" / "broken.maxhelp").write_text("{not json")
    _write(c74 / "help" / "max" / "list.maxhelp", [1, 2, 3])

    pkgs = tmp_path / "packages"
    _write(pkgs / "UserPkg" / "package-info.json", {"version": "1.2.3"})
    _write(pkgs / "UserPkg" / "help" / "u.maxhelp",
           _help([_newobj("obj-1", "alpha 5", 1, 3)]))
    _write(pkgs / "UserPkg" / "patchers" / "x.maxhelp",
           _help([_newobj("obj-1", "alpha 6", 1, 4)]))
    _write(pkgs / "CapPkg" / "Help" / "c.maxhelp",
           _help([_newobj("obj-1", "alpha", 1, 2)]))
    (pkgs / "EmptyPkg").mkdir(parents=True)
    return app, db, pkgs


def _scan(app: Path, db: Path, pkgs: Path) -> dict:
    return help_io.scan_help_io(app, pkgs, ObjectDatabase(db_root=db), "9.9.9")


class TestScan:
    def test_box_rules_and_counters(self, tmp_path: Path) -> None:
        app, db, pkgs = _scan_tree(tmp_path)
        database = ObjectDatabase(db_root=db)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            section = help_io.scan_help_io(app, pkgs, database, "9.9.9")
        assert [str(w.message) for w in caught] == []

        stats = section["sources"]["bundle"]["stats"]
        # scan.maxhelp: 17 top-level newobj + the p's inner box, 3 others;
        # b.maxhelp adds one compared newobj.
        assert stats["newobj_boxes"] == 19
        assert stats["other_boxes"] == 3
        assert stats["compared"] == 10
        assert stats["content_defined"] == 6
        assert stats["unresolved"] == 2
        assert stats["malformed"] == 4
        assert stats["internal_patchers_skipped"] == 3

        mism = section["mismatches"]["bundle"]
        alpha = mism["alpha"]
        assert alpha["count_mismatches"] == 2  # obj-2 and the p's inner box
        assert alpha["canonical"] == "alpha"
        assert alpha["kinds"] == ["newobj"]
        assert sorted(alpha["signatures"]) == [
            "count args=1 max=1,3 db=1,2",
            "count args=1 max=1,9 db=1,2",
        ]
        for sig in alpha["signatures"].values():
            assert sig["count"] == 1  # no gen~/rnbo~ internal was walked
            assert sig["appversions"] == ["9.1.0"]
            assert len(sig["examples"]) <= 3
            assert sig["examples"][0]["file"] == "help/max/scan.maxhelp"
        inner = alpha["signatures"]["count args=1 max=1,9 db=1,2"]
        assert inner["examples"][0]["box"] == "obj-9a"

        assert "vfoo" not in mism  # args stop at the first @
        assert mism["sigout~"]["type_mismatches"] == 1
        assert mism["sigout~"]["count_mismatches"] == 0
        assert list(mism["sigout~"]["signatures"]) == ["type max=signal db=control"]
        assert "mcout~" not in mism  # multichannelsignal is a signal class
        assert "js" not in mism and "emptyio" not in mism
        assert mism["uiwidget"]["kinds"] == ["box"]
        assert mism["uiwidget"]["count_mismatches"] == 1
        assert section["unresolved"]["bundle"] == {"missingui": 1, "nosuch": 1}

    def test_bad_files_appversions_and_bundle_packages(self, tmp_path: Path) -> None:
        section = _scan(*_scan_tree(tmp_path))
        bundle = section["sources"]["bundle"]
        assert bundle["files"] == 4
        bad = {b["file"] for b in bundle["bad_files"]}
        assert bad == {"help/max/broken.maxhelp", "help/max/list.maxhelp"}
        assert bundle["appversions"] == {"9.1.0": 1, "unknown": 1}

    def test_package_sources(self, tmp_path: Path) -> None:
        section = _scan(*_scan_tree(tmp_path))
        src = section["sources"]
        assert sorted(src) == ["bundle", "package:CapPkg", "package:UserPkg"]
        assert src["package:UserPkg"]["version"] == "1.2.3"
        assert src["package:UserPkg"]["files"] == 1  # patchers/ is not scanned
        assert src["package:CapPkg"]["version"] is None
        user = section["mismatches"]["package:UserPkg"]["alpha"]
        assert list(user["signatures"]) == ["count args=1 max=1,3 db=1,2"]
        assert section["mismatches"]["package:CapPkg"] == {}

    def test_missing_packages_dir(self, tmp_path: Path) -> None:
        app, db, _ = _scan_tree(tmp_path)
        section = _scan(app, db, tmp_path / "nowhere")
        assert section["available"] is True
        assert list(section["sources"]) == ["bundle"]
        assert section["packages_reason"]

    def test_depth_cap(self, tmp_path: Path) -> None:
        app = _make_fake_max(tmp_path)
        db = _make_fake_db(tmp_path)
        node: dict = _inner([_newobj("deep", "alpha 5", 1, 3)])
        for i in range(40):
            node = _inner([_newobj(f"p-{i}", "p nest", 1, 1, patcher=node)])
        _write(_c74(app) / "help" / "max" / "deep.maxhelp", {"patcher": node})
        section = _scan(app, db, tmp_path / "no-packages")
        assert section["sources"]["bundle"]["stats"]["depth_capped"] >= 1

    def test_deterministic_baseline(self, tmp_path: Path) -> None:
        app, db, pkgs = _scan_tree(tmp_path)
        first = help_io.dump_baseline(help_io.build_baseline(_scan(app, db, pkgs)))
        second = help_io.dump_baseline(help_io.build_baseline(_scan(app, db, pkgs)))
        assert first == second


class TestCliModes:
    def test_missing_bundle_exits_zero(self, tmp_path: Path) -> None:
        result = _cli(
            "--help-io", "--max-app", tmp_path / "absent.app",
            "--db-root", _make_fake_db(tmp_path),
            "--packages-dir", tmp_path / "no-packages",
        )
        assert result.returncode == 0, result.stderr
        assert "unavailable" in result.stdout

    def test_summary_lines(self, tmp_path: Path) -> None:
        app, db, pkgs = _scan_tree(tmp_path)
        result = _cli("--help-io", "--max-app", app, "--db-root", db,
                      "--packages-dir", pkgs)
        assert result.returncode == 0, result.stderr
        out = result.stdout
        assert "package:UserPkg" in out
        versions = [ln for ln in out.splitlines() if "help versions" in ln]
        assert versions and "9.1.0" in versions[0]
        assert any(ln.strip().startswith("mismatching") for ln in out.splitlines())


# ── Task 3: diff semantics, baseline output, committed baseline ───


MINI = REPO_ROOT / "tests" / "fixtures" / "help_io_mini_baseline.json"
BASELINE = REPO_ROOT / "tests" / "fixtures" / "help_io_baseline.json"


def _mini() -> dict:
    return json.loads(MINI.read_text())


def _keys(obj) -> set:
    """Every dict key anywhere in a JSON value."""
    found: set = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            found.add(k)
            found |= _keys(v)
    elif isinstance(obj, list):
        for v in obj:
            found |= _keys(v)
    return found


def _assert_signature_sums(baseline: dict) -> None:
    for sid, names in baseline["names"].items():
        assert sid in baseline["sources"], sid
        for name, e in names.items():
            total = e["count_mismatches"] + e["type_mismatches"]
            assert total > 0, (sid, name)
            assert sum(e["signatures"].values()) == total, (sid, name)


class TestDiff:
    def test_identical(self) -> None:
        d = help_io.diff_baselines(_mini(), _mini())
        assert d["regressions"] == [] and d["improvements"] == []
        assert d["compared_sources"] == ["bundle", "package:Demo"]
        assert d["stale_sources"] == {}
        assert d["new_sources"] == [] and d["missing_sources"] == []

    def test_count_increase(self) -> None:
        live = _mini()
        live["names"]["bundle"]["alpha"]["count_mismatches"] = 3
        d = help_io.diff_baselines(_mini(), live)
        assert d["regressions"] == [{
            "source": "bundle", "name": "alpha", "field": "count_mismatches",
            "baseline": 2, "live": 3,
        }]

    def test_type_increase(self) -> None:
        live = _mini()
        live["names"]["bundle"]["beta~"]["type_mismatches"] = 2
        d = help_io.diff_baselines(_mini(), live)
        assert [(r["name"], r["field"]) for r in d["regressions"]] == [
            ("beta~", "type_mismatches")
        ]

    def test_new_name_is_a_regression_from_zero(self) -> None:
        live = _mini()
        live["names"]["bundle"]["gamma"] = {
            "boxes": 1, "count_mismatches": 1, "type_mismatches": 0,
            "signatures": {"count args=0 max=1,1 db=1,0": 1},
        }
        d = help_io.diff_baselines(_mini(), live)
        assert d["regressions"] == [{
            "source": "bundle", "name": "gamma", "field": "count_mismatches",
            "baseline": 0, "live": 1,
        }]

    def test_removed_name_is_an_improvement(self) -> None:
        live = _mini()
        del live["names"]["bundle"]["alpha"]
        d = help_io.diff_baselines(_mini(), live)
        assert d["regressions"] == []
        assert d["improvements"] == [{
            "source": "bundle", "name": "alpha", "field": "count_mismatches",
            "baseline": 2, "live": 0,
        }]

    def test_stale_source_is_excluded(self) -> None:
        live = _mini()
        live["sources"]["package:Demo"]["version"] = "1.0.1"
        live["names"]["package:Demo"]["demo.obj"]["count_mismatches"] = 5
        d = help_io.diff_baselines(_mini(), live)
        assert d["regressions"] == []
        assert d["stale_sources"] == {
            "package:Demo": {"baseline": "1.0.0", "live": "1.0.1"}
        }
        assert d["compared_sources"] == ["bundle"]

    def test_new_source_is_not_compared(self) -> None:
        live = _mini()
        live["sources"]["package:New"] = {
            "version": "2.0.0", "files": 1, "boxes_compared": 1,
            "mismatching_boxes": 1, "mismatching_names": 1,
        }
        live["names"]["package:New"] = {"x": {
            "boxes": 1, "count_mismatches": 1, "type_mismatches": 0,
            "signatures": {"count args=0 max=1,1 db=0,0": 1},
        }}
        d = help_io.diff_baselines(_mini(), live)
        assert d["new_sources"] == ["package:New"]
        assert d["regressions"] == []

    def test_missing_source(self) -> None:
        live = _mini()
        del live["sources"]["package:Demo"]
        del live["names"]["package:Demo"]
        d = help_io.diff_baselines(_mini(), live)
        assert d["missing_sources"] == ["package:Demo"]
        assert d["regressions"] == []

    def test_boxes_change_alone_is_not_a_regression(self) -> None:
        live = _mini()
        live["names"]["bundle"]["alpha"]["boxes"] = 40
        d = help_io.diff_baselines(_mini(), live)
        assert d["regressions"] == [] and d["improvements"] == []

    def test_regressions_are_sorted(self) -> None:
        live = _mini()
        live["names"]["package:Demo"]["demo.obj"]["type_mismatches"] = 1
        live["names"]["bundle"]["beta~"]["type_mismatches"] = 4
        live["names"]["bundle"]["beta~"]["count_mismatches"] = 1
        live["names"]["bundle"]["alpha"]["type_mismatches"] = 1
        d = help_io.diff_baselines(_mini(), live)
        keys = [(r["source"], r["name"], r["field"]) for r in d["regressions"]]
        assert keys == [
            ("bundle", "alpha", "type_mismatches"),
            ("bundle", "beta~", "count_mismatches"),
            ("bundle", "beta~", "type_mismatches"),
            ("package:Demo", "demo.obj", "type_mismatches"),
        ]

    @pytest.mark.parametrize("side", ["baseline", "live"])
    def test_unknown_schema_raises(self, side: str) -> None:
        other = _mini()
        other["schema"] = 2
        args = (other, _mini()) if side == "baseline" else (_mini(), other)
        with pytest.raises(ValueError):
            help_io.diff_baselines(*args)

    def test_mini_fixture_is_canonical(self) -> None:
        text = MINI.read_text()
        assert text == help_io.dump_baseline(json.loads(text))


class TestBaselineOutput:
    def test_dump_is_machine_neutral(self, tmp_path: Path) -> None:
        app, db, pkgs = _scan_tree(tmp_path)
        baseline = help_io.build_baseline(_scan(app, db, pkgs))
        text = help_io.dump_baseline(baseline)
        assert str(tmp_path) not in text
        assert str(Path.home()) not in text
        assert not _keys(baseline) & {"generated_at", "root", "examples", "appversions"}

    def test_only_mismatching_names_and_signature_sums(self, tmp_path: Path) -> None:
        baseline = help_io.build_baseline(_scan(*_scan_tree(tmp_path)))
        assert sorted(baseline["names"]["bundle"]) == ["alpha", "sigout~", "uiwidget"]
        _assert_signature_sums(baseline)

    def test_cli_write_twice_identical(self, tmp_path: Path) -> None:
        app, db, pkgs = _scan_tree(tmp_path)
        outs = []
        for i in range(2):
            target = tmp_path / f"bl{i}.json"
            r = _cli("--help-io", "--max-app", app, "--db-root", db,
                     "--packages-dir", pkgs, "--write-baseline", target)
            assert r.returncode == 0, r.stderr
            assert f"baseline        : {target}" in r.stdout
            outs.append(target.read_bytes())
        assert outs[0] == outs[1]

    def test_cli_refuses_protected_target(self, tmp_path: Path) -> None:
        app, db, pkgs = _scan_tree(tmp_path)
        repo = tmp_path / "repo"
        (repo / "patches").mkdir(parents=True)
        target = repo / "patches" / "x.json"
        r = _cli("--help-io", "--repo-root", repo, "--max-app", app, "--db-root", db,
                 "--packages-dir", pkgs, "--write-baseline", target)
        assert r.returncode == 2
        assert not target.exists()
        assert "refusing to write" in r.stderr

    def test_cli_write_baseline_requires_help_io(self, tmp_path: Path) -> None:
        target = tmp_path / "bl.json"
        r = _cli("--write-baseline", target, "--max-app", tmp_path / "absent.app")
        assert r.returncode == 2
        assert not target.exists()

    def test_cli_unavailable_bundle_writes_nothing(self, tmp_path: Path) -> None:
        target = tmp_path / "bl.json"
        j = tmp_path / "h.json"
        r = _cli("--help-io", "--max-app", tmp_path / "absent.app",
                 "--db-root", _make_fake_db(tmp_path),
                 "--packages-dir", tmp_path / "no-packages",
                 "--json", j, "--write-baseline", target)
        assert r.returncode == 1
        assert "error" in r.stderr
        assert not target.exists() and not j.exists()


class TestCommittedBaseline:
    """Hygiene of the committed baseline; no Max needed (runs in CI)."""

    def test_exists_and_schema(self) -> None:
        baseline = json.loads(BASELINE.read_text())
        assert baseline["schema"] == 1
        assert isinstance(baseline["max_version"], str)

    def test_canonical(self) -> None:
        text = BASELINE.read_text()
        assert text == help_io.dump_baseline(json.loads(text))

    def test_size(self) -> None:
        assert BASELINE.stat().st_size < 400_000

    def test_no_machine_paths_or_timestamps(self) -> None:
        text = BASELINE.read_text()
        for needle in ("/Users/", "/Applications/", "/home/", "generated_at"):
            assert needle not in text, needle

    def test_entries_are_mismatches_with_matching_signature_sums(self) -> None:
        _assert_signature_sums(json.loads(BASELINE.read_text()))


@pytest.fixture(scope="module")
def live() -> dict:
    """One live scan (real bundle, real DB, default packages dir) per module."""
    envelope = audit_db.run_help_io(max_app=MAX_APP_PATH)
    section = envelope["help_io"]
    assert section["available"], section.get("reason")
    return help_io.build_baseline(section)


@pytest.mark.requires_max
class TestLiveOracle:
    """Fails when MAX-saved help boxes disagree with the DB more than recorded.

    Reads the real bundle, the real DB and the default packages dir. Skips
    without Max.app (conftest) and when the installed Max differs from the
    version the baseline was recorded against.
    """

    INSPECT = "python3 tools/audit_db.py --help-io --json <path>"

    @staticmethod
    def _diff_or_skip(baseline: dict, live: dict) -> dict:
        diff = help_io.diff_baselines(baseline, live)
        stale = diff["stale_sources"].get("bundle")
        if stale is not None:
            pytest.skip(
                f"help-io baseline recorded against Max {stale['baseline']}, "
                f"installed {stale['live']}: re-run python3 tools/audit_db.py "
                "--help-io --write-baseline tests/fixtures/help_io_baseline.json"
            )
        return diff

    def test_mismatches_do_not_increase(self, live: dict) -> None:
        diff = self._diff_or_skip(json.loads(BASELINE.read_text()), live)
        rows = [
            f"{r['source']}/{r['name']} {r['field']} {r['baseline']}->{r['live']}"
            for r in diff["regressions"][:20]
        ]
        assert not diff["regressions"], (
            f"{len(diff['regressions'])} help-box I/O regressions vs the committed "
            f"baseline (inspect with {self.INSPECT}):\n" + "\n".join(rows)
        )

    def test_a_regression_is_detected_on_live_data(self, live: dict) -> None:
        committed = json.loads(BASELINE.read_text())
        base_diff = self._diff_or_skip(committed, live)
        names = committed["names"].get("bundle", {})
        if not names:
            pytest.skip("committed baseline records no bundle mismatches")
        name = sorted(names)[0]
        entry = names[name]
        field = max(("count_mismatches", "type_mismatches"), key=lambda f: entry[f])
        doctored = copy.deepcopy(committed)
        doctored["names"]["bundle"][name][field] -= 1
        diff = help_io.diff_baselines(doctored, live)
        new = [r for r in diff["regressions"] if r not in base_diff["regressions"]]
        assert len(new) == 1
        assert (new[0]["source"], new[0]["name"], new[0]["field"]) == (
            "bundle", name, field
        )
