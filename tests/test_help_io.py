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
from pathlib import Path

import pytest

from src.maxpat.db_lookup import ObjectDatabase
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
    """Write a tiny object DB: `alpha` is 1 control inlet, 2 control outlets."""
    root = tmp_path / "db"
    (root / "max").mkdir(parents=True)
    objects = {
        "alpha": {"name": "alpha", "inlets": [_port()], "outlets": [_port(), _port()]},
    }
    (root / "max" / "objects.json").write_text(json.dumps(objects))
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
