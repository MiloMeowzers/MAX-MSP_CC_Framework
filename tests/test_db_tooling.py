"""Q30 / I4 I5 I6: DB tooling regression tests; scratch copies only.

Every write in this module goes to ``tmp_path``: the hermetic fake bundle and
fake DB from ``tests/test_sync_max_bundle.py``, or a scratch copy of the real
DB made from an explicit file list. The real DB is only ever read, and a
module-scoped guard asserts that its files keep their sha256 and mode.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import stat
from pathlib import Path

import pytest

import tools.sync_max_bundle as sync
from tests.conftest import MAX_APP_PATH
from tests.test_sync_max_bundle import (
    _help_patch,
    _make_bundle,
    _make_db,
    _newobj,
    _refpage,
    _tree_bytes,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
REAL_DB = REPO_ROOT / ".claude" / "max-objects"
REAL_DOMAINS = ("max", "msp", "jitter", "mc", "gen", "m4l", "rnbo")
VALIDATE_DB_PATH = REPO_ROOT / ".claude" / "scripts" / "validate_db.py"
EXTRACTOR_PATH = REPO_ROOT / ".claude" / "scripts" / "extract_objects.py"


# ── Real-DB guard ─────────────────────────────────────────────────


def real_db_files() -> list[Path]:
    """The real DB files tests may read: an explicit list, never a recursive walk.

    Top-level ``*.json``, ``<domain>/objects.json`` for the 7 core domains and
    ``packages/*/objects.json``. ``_pkg-source/`` and ``audit/`` are never
    touched.
    """
    files = sorted(p for p in REAL_DB.glob("*.json") if p.is_file())
    files.extend(REAL_DB / d / "objects.json" for d in REAL_DOMAINS if (REAL_DB / d / "objects.json").is_file())
    files.extend(sorted(p for p in REAL_DB.glob("packages/*/objects.json") if p.is_file()))
    return files


def _state(paths: list[Path]) -> dict[str, tuple[str, int]]:
    return {
        str(p): (hashlib.sha256(p.read_bytes()).hexdigest(), stat.S_IMODE(p.stat().st_mode))
        for p in paths
    }


@pytest.fixture(autouse=True, scope="module")
def _real_db_guard():
    """The real DB keeps every file's sha256 and mode across this module."""
    before = _state(real_db_files())
    yield
    assert _state(real_db_files()) == before


def scratch_copy_of_real_db(dest: Path) -> Path:
    """Copy the real DB's explicit file list into `dest` (read-only source)."""
    for src in real_db_files():
        rel = src.relative_to(REAL_DB)
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(src.read_bytes())
    return dest


def _umask_default() -> int:
    mask = os.umask(0)
    os.umask(mask)
    return 0o666 & ~mask


def _mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def _load_by_path(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ── Hermetic world ────────────────────────────────────────────────


@pytest.fixture
def world(tmp_path: Path) -> dict:
    app = _make_bundle(tmp_path)
    db_root = _make_db(tmp_path)
    return {
        "app": app,
        "c74": app / "Contents" / "Resources" / "C74",
        "db_root": db_root,
        "repo": tmp_path / "repo",
        "argv": [
            "--max-app", str(app), "--db-root", str(db_root), "--repo-root", str(tmp_path / "repo"),
        ],
    }


def _run(world: dict, *extra: str) -> int:
    return sync.main([*world["argv"], *extra])


def _load(world: dict, rel: str) -> dict:
    return json.loads((world["db_root"] / rel).read_text(encoding="utf-8"))


# ══ I6 part 1: atomic writes, transactions, define regex, versions ══


class TestI6TracerApplyKeepsModeAndStringVersion:
    """Tracer: one real apply keeps the file mode and writes a string version."""

    def test_apply_new_keeps_mode_and_writes_a_string_min_version(self, world: dict) -> None:
        path = world["db_root"] / "max" / "objects.json"
        os.chmod(path, 0o644)
        assert _run(world, "--apply", "new", "--names", "newthing") == 0
        assert _mode(path) == 0o644
        entry = json.loads(path.read_text(encoding="utf-8"))["newthing"]
        assert entry["min_version"] == "9.7"
        assert isinstance(entry["min_version"], str)


class TestI6AtomicMode:
    def test_write_db_file_keeps_an_existing_mode(self, world: dict) -> None:
        path = world["db_root"] / "max" / "objects.json"
        os.chmod(path, 0o640)
        data = json.loads(path.read_text(encoding="utf-8"))
        data["old"]["messages"].append("grown")
        assert sync.write_db_file(path, data, world["db_root"]) is True
        assert _mode(path) == 0o640

    def test_apply_deltas_keeps_the_mode_of_every_file_it_writes(self, world: dict) -> None:
        root = world["db_root"]
        files = [p for p in root.rglob("*.json") if p.is_file()]
        for path in files:
            os.chmod(path, 0o644)
        before = _tree_bytes(root)
        assert _run(world, "--apply", "deltas") == 0
        after = _tree_bytes(root)
        changed = [rel for rel in after if after[rel] != before.get(rel)]
        assert changed, "the fixture must give --apply deltas something to write"
        for rel in changed:
            assert _mode(root / rel) == 0o644, rel

    def test_write_extraction_log_keeps_an_existing_mode(self, world: dict) -> None:
        log = world["db_root"] / "extraction-log.json"
        log.write_text(json.dumps({"total_objects": 1}, indent=2) + "\n")
        os.chmod(log, 0o640)
        sync.write_extraction_log(world["db_root"], {"total_objects": 2})
        assert _mode(log) == 0o640
        assert json.loads(log.read_text())["total_objects"] == 2

    def test_write_extraction_log_creates_a_new_log_with_the_umask_default(self, world: dict) -> None:
        log = world["db_root"] / "extraction-log.json"
        assert not log.exists()
        sync.write_extraction_log(world["db_root"], {"total_objects": 2})
        assert _mode(log) == _umask_default()

    def test_write_groups_file_keeps_an_existing_mode(self, world: dict) -> None:
        root = world["db_root"]
        path = root / sync.GROUPS_FILE
        old = {"attribute_definitions": {}, "members": {}, "profiles": {}}
        path.write_bytes(sync.canonical_groups_bytes(old))
        os.chmod(path, 0o640)
        new = dict(old, max_version="9.7")
        assert sync.write_groups_file(path, new, root) is True
        assert _mode(path) == 0o640

    def test_atomic_write_bytes_new_file_gets_umask_default_and_leaves_no_temp(
        self, tmp_path: Path
    ) -> None:
        from src.maxpat.atomic_io import atomic_write_bytes

        target = tmp_path / "fresh.json"
        atomic_write_bytes(target, b"{}\n")
        assert target.read_bytes() == b"{}\n"
        assert _mode(target) == _umask_default()
        assert sorted(p.name for p in tmp_path.iterdir()) == ["fresh.json"]


class TestI6TransactionalApply:
    def test_a_failing_file_in_a_multi_file_apply_writes_nothing(self, world: dict) -> None:
        root = world["db_root"]
        pkg = root / "packages" / "FakePkg" / "objects.json"
        pkg.write_text(json.dumps(json.loads(pkg.read_text()), indent=4) + "\n")  # unreproducible
        before = _tree_bytes(root)
        assert _run(world, "--apply", "new", "--names", "newthing", "pkg.fresh") == 2
        assert _tree_bytes(root) == before

    def test_atomic_write_many_restores_every_target_when_a_replace_fails(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import src.maxpat.atomic_io as atomic_io

        d1, d2 = tmp_path / "d1", tmp_path / "d2"
        d1.mkdir()
        d2.mkdir()
        first, second, third = d1 / "a.json", d1 / "b.json", d2 / "c.json"
        first.write_bytes(b"first\n")
        os.chmod(first, 0o640)
        third.write_bytes(b"third\n")
        os.chmod(third, 0o604)

        real_replace = os.replace
        calls = {"n": 0}

        def flaky_replace(src, dst):
            calls["n"] += 1
            if calls["n"] == 3:
                raise OSError("injected replace failure")
            return real_replace(src, dst)

        monkeypatch.setattr(atomic_io.os, "replace", flaky_replace)
        with pytest.raises(OSError, match="injected"):
            atomic_io.atomic_write_many(
                [(first, b"FIRST\n"), (second, b"SECOND\n"), (third, b"THIRD\n")]
            )
        monkeypatch.undo()

        assert first.read_bytes() == b"first\n" and _mode(first) == 0o640
        assert not second.exists()
        assert third.read_bytes() == b"third\n" and _mode(third) == 0o604
        assert sorted(p.name for p in d1.iterdir()) == ["a.json"]
        assert sorted(p.name for p in d2.iterdir()) == ["c.json"]

    def test_write_db_files_with_one_additive_violation_writes_nothing(self, world: dict) -> None:
        root = world["db_root"]
        max_path = root / "max" / "objects.json"
        msp_path = root / "msp" / "objects.json"
        grown = json.loads(max_path.read_text(encoding="utf-8"))
        grown["old"]["messages"].append("grown")
        shrunk = {}  # every msp entry removed
        before = _tree_bytes(root)
        with pytest.raises(sync.AdditiveViolation):
            sync.write_db_files([(max_path, grown), (msp_path, shrunk)], root)
        assert _tree_bytes(root) == before

    def test_package_object_and_its_count_land_in_one_run(self, world: dict) -> None:
        """Green guard: the package entry and package_info.json count together."""
        assert _run(world, "--apply", "new", "--names", "pkg.fresh") == 0
        assert "pkg.fresh" in _load(world, "packages/FakePkg/objects.json")
        assert _load(world, "package_info.json")["FakePkg"]["object_count"] == 2


class TestI6DefineRegex:
    def test_an_argument_less_define_drops_the_trailing_semicolon(self, world: dict) -> None:
        (world["c74"] / "init" / "q30-objectmappings.txt").write_text(
            "max define bare.def corething;\n"
        )
        defines = sync.parse_define_mappings(world["c74"])
        assert defines["bare.def"]["target"] == "corething"
        assert defines["bare.def"]["args"] == ""
        assert defines["pkg.alias"]["target"] == "corething"
        assert defines["pkg.alias"]["args"] == "alias.js"

    @pytest.mark.requires_max
    def test_real_bundle_defines_have_no_semicolon_in_alias_or_target(self) -> None:
        defines = sync.parse_define_mappings(MAX_APP_PATH / "Contents" / "Resources" / "C74")
        assert defines
        for alias, record in defines.items():
            assert not alias.endswith(";"), alias
            assert not record["target"].endswith(";"), (alias, record["target"])


class TestI6StringVersions:
    @pytest.mark.parametrize(
        "short, expected",
        [
            ("9.2.0", "9.2"),
            ("9.10.0", "9.10"),
            ("09.2.1", "9.2"),
            ("9.0.0", "9.0"),
            ("9.7.3 (abc123)", "9.7"),
            (None, None),
            ("", None),
            ("nine", None),
            ("9", None),
        ],
    )
    def test_major_minor_is_a_string(self, short, expected) -> None:
        assert sync._major_minor(short) == expected

    @pytest.mark.parametrize("text, expected", [("8", "8"), ("9.1", "9.1"), ("9.10", "9.10")])
    def test_parse_min_version_returns_the_canonical_string(self, text: str, expected: str) -> None:
        assert sync.parse_min_version(text) == expected

    @pytest.mark.parametrize("bad", ["10", "3", "nine", "9.x", "-8"])
    def test_parse_min_version_rejects(self, bad: str) -> None:
        import argparse

        with pytest.raises(argparse.ArgumentTypeError):
            sync.parse_min_version(bad)

    def test_explicit_min_version_lands_as_a_string(self, world: dict) -> None:
        assert _run(world, "--apply", "define", "--names", "jit.gl.fresh", "--min-version", "8") == 0
        assert _load(world, "jitter/objects.json")["jit.gl.fresh"]["min_version"] == "8"

    def test_bundle_index_version_is_a_string(self, world: dict) -> None:
        assert sync.build_bundle_index(world["app"])["version"] == "9.7"


class TestVersionTuple:
    @pytest.fixture(scope="class")
    def validate_db(self):
        return _load_by_path("_q30_validate_db", VALIDATE_DB_PATH)

    @pytest.mark.parametrize(
        "value, expected",
        [("9.10", (9, 10)), (8.1, (8, 1)), (9, (9,)), ("9", (9,)), (True, None), (None, None), ("x", None)],
    )
    def test_version_tuple(self, validate_db, value, expected) -> None:
        assert validate_db._version_tuple(value) == expected
