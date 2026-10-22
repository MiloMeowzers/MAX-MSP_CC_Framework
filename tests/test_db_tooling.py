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


# ══ I6 part 2: objectfile aliases (sync report, --apply aliases, audit_db) ══


def _add_entries(db_root: Path, rel: str, entries: dict) -> None:
    """Add fake-DB entries to one domain file (created when absent), test setup only."""
    path = db_root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    data.update(entries)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _objectfile_world(world: dict) -> dict:
    """One alias per candidate basis, plus resolved and RNBO-shadowed names."""
    from tests.test_sync_max_bundle import _entry

    c74, root = world["c74"], world["db_root"]
    (c74 / "init" / "q30-mappings.txt").write_text(
        "max objectfile *~ times~;\n"
        "max objectfile mc.times~ mc.wrapper~ times~;\n"
        "max objectfile 4mixr vz.4mixr.maxpat;\n"
        "max objectfile list.iter zl zl.iter;\n"
        "max objectfile list.len zl zl.len;\n"
        "max objectfile hslider slider;\n"
        "max objectfile jit.plus jit.old;\n"
        "max objectfile ghost.obj nowhere;\n"
        "max objectfile old old.impl;\n"
    )
    help_max = c74 / "help" / "max"
    help_max.mkdir(parents=True, exist_ok=True)
    (help_max / "hslider.maxhelp").write_text(_help_patch([_newobj("hslider", 1, 1, [""])]))
    _add_entries(root, "msp/objects.json", {"*~": _entry("*~", "MSP", "msp")})
    _add_entries(root, "mc/objects.json", {"mc.*~": _entry("mc.*~", "MC", "mc")})
    _add_entries(
        root,
        "max/objects.json",
        {
            "vz.4mixr": _entry("vz.4mixr", "Max", "max"),
            "zl.iter": _entry("zl.iter", "Max", "max"),
            "zl.len": _entry("zl.len", "Max", "max"),
            "slider": _entry("slider", "Max", "max"),
        },
    )
    _add_entries(root, "rnbo/objects.json", {"list.len": _entry("list.len", "RNBO", "rnbo")})
    return world


class TestI6ObjectfileParse:
    def test_every_init_file_and_line_shape_is_read(self, tmp_path: Path) -> None:
        c74 = tmp_path / "C74"
        (c74 / "init").mkdir(parents=True)
        (c74 / "packages" / "P" / "init").mkdir(parents=True)
        core = c74 / "init" / "a-objectmappings.txt"
        core.write_text(
            "max objectfile  dbl.space   target.obj;\n"
            "max objectfile mc.cls~ mc.wrapper~ cls~ @extra 1;\n"
            "max objectfile nosemi file.obj\n"
            "max objectfile dbl.space other.obj;\n"
            "max define not.objectfile target;\n"
        )
        pkg = c74 / "packages" / "P" / "init" / "p-mc.txt"
        pkg.write_text("max objectfile p.alias p.file;\n")

        parsed = sync.parse_objectfile_mappings(c74)
        records = parsed["records"]
        assert set(records) == {"dbl.space", "mc.cls~", "nosemi", "p.alias"}
        dbl, cls = records["dbl.space"], records["mc.cls~"]
        assert (dbl["file"], dbl["class"], dbl["args"]) == ("target.obj", None, "")
        assert (cls["file"], cls["class"], cls["args"]) == ("mc.wrapper~", "cls~", "@extra 1")
        assert records["nosemi"]["file"] == "file.obj"
        assert records["p.alias"]["package"] == "P"
        assert dbl["package"] is None
        assert parsed["lines"] == 5
        assert parsed["duplicates"] == ["dbl.space"]
        assert set(parsed["files"]) == {str(core), str(pkg)}


class TestI6ObjectfileReport:
    def test_section_slot(self) -> None:
        keys = sync.SECTION_KEYS
        assert keys[keys.index("define_missing") + 1] == "objectfile_aliases"
        assert keys[-1] == "ui_maxclasses"

    def test_candidates_bases_and_evidence(self, world: dict) -> None:
        _objectfile_world(world)
        before = _tree_bytes(world["db_root"])
        report = sync.run_report(world["db_root"], world["app"])
        assert _tree_bytes(world["db_root"]) == before
        section = report["sections"]["objectfile_aliases"]
        entries = {e["name"]: e for e in section["entries"]}

        def pick(name):
            return entries[name]["candidate"], entries[name]["basis"]

        assert pick("mc.times~") == ("mc.*~", "mc_wrapper")
        assert pick("4mixr") == ("vz.4mixr", "abstraction")
        assert pick("list.iter") == ("zl.iter", "class")
        assert pick("hslider") == ("slider", "file")
        assert pick("ghost.obj") == (None, None)
        # Resolved names are not entries; the RNBO-resolving one is listed apart.
        assert "old" not in entries and "*~" not in entries and "list.len" not in entries
        shadowed = {e["name"]: e for e in section["domain_shadowed"]}
        assert shadowed["list.len"]["candidate"] == "zl.len"
        # Help evidence.
        assert entries["jit.gl.fresh"]["help_io_agrees"] is False
        assert entries["list.iter"]["help_io_agrees"] is None
        assert entries["hslider"]["help_io_agrees"] is True
        assert entries["hslider"]["help_io"] == [[1, 1]]
        for entry in entries.values():
            for key in (
                "file", "class", "args", "package", "mapping_file", "line",
                "candidate_domain", "candidate_io", "help_stem",
            ):
                assert key in entry
        assert section["unresolved_count"] == len(section["names_unresolved"]) == len(entries)
        assert section["names_unresolved"] == sorted(section["names_unresolved"])
        assert section["by_basis"]["mc_wrapper"] == 1

        summary = sync.format_summary(report)
        assert any(line.strip().startswith("objectfile") for line in summary.splitlines())


class TestI6ApplyAliases:
    def _seed_aliases(self, world: dict) -> Path:
        path = world["db_root"] / "aliases.json"
        path.write_text(
            json.dumps({"_comment": "curated", "aliases": {"zz": "old", "aa": "corething"}}, indent=2)
            + "\n"
        )
        os.chmod(path, 0o640)
        return path

    def test_names_are_mandatory(self, world: dict) -> None:
        _objectfile_world(world)
        before = _tree_bytes(world["db_root"])
        assert _run(world, "--apply", "aliases") == 2
        assert _tree_bytes(world["db_root"]) == before

    def test_a_file_basis_alias_lands_additively(self, world: dict) -> None:
        from src.maxpat.atomic_io import json_style
        from src.maxpat.db_lookup import ObjectDatabase

        _objectfile_world(world)
        path = self._seed_aliases(world)
        overrides = world["db_root"] / "overrides.json"
        overrides_sha = hashlib.sha256(overrides.read_bytes()).hexdigest()
        style_before = json_style(path.read_bytes(), json.loads(path.read_bytes()))
        assert _run(world, "--apply", "aliases", "--names", "jit.plus") == 0
        raw = path.read_bytes()
        data = json.loads(raw)
        assert list(data) == ["_comment", "aliases"]
        assert list(data["aliases"].items()) == [
            ("zz", "old"), ("aa", "corething"), ("jit.plus", "jit.old"),
        ]
        assert json_style(raw, data) == style_before
        assert _mode(path) == 0o640
        assert ObjectDatabase(world["db_root"]).lookup("jit.plus")["name"] == "jit.old"
        assert hashlib.sha256(overrides.read_bytes()).hexdigest() == overrides_sha

    def test_resolved_shadowed_unknown_and_disagreeing_names_never_land(self, world: dict) -> None:
        _objectfile_world(world)
        path = self._seed_aliases(world)
        before = path.read_bytes()
        out = world["repo"].parent / "aliases-report.json"
        code = _run(
            world, "--apply", "aliases", "--names", "old", "list.len", "nope.obj", "jit.gl.fresh",
            "--json", str(out),
        )
        assert code == 1
        assert path.read_bytes() == before
        results = {r["name"]: r for r in json.loads(out.read_text())["applied"]["aliases"]}
        assert results["old"]["status"] == "skipped"
        assert results["list.len"]["status"] == "skipped"
        assert results["nope.obj"]["status"] == "aborted"
        assert results["jit.gl.fresh"]["status"] == "aborted"

    def test_shadowed_flag_aliases_an_rnbo_shadowed_name(self, world: dict) -> None:
        from src.maxpat.db_lookup import ObjectDatabase

        _objectfile_world(world)
        path = self._seed_aliases(world)
        assert ObjectDatabase(world["db_root"]).lookup("list.len")["domain"] == "RNBO"
        assert _run(world, "--apply", "aliases", "--shadowed", "--names", "list.len") == 0
        assert json.loads(path.read_text())["aliases"]["list.len"] == "zl.len"
        assert ObjectDatabase(world["db_root"]).lookup("list.len")["name"] == "zl.len"

    def test_shadowed_flag_still_skips_a_max_resolution(self, world: dict) -> None:
        _objectfile_world(world)
        path = self._seed_aliases(world)
        before = path.read_bytes()
        out = world["repo"].parent / "aliases-report.json"
        code = _run(
            world, "--apply", "aliases", "--shadowed", "--names", "old", "--json", str(out),
        )
        assert code == 0
        assert path.read_bytes() == before
        results = {r["name"]: r for r in json.loads(out.read_text())["applied"]["aliases"]}
        assert results["old"]["status"] == "skipped"

    def test_an_override_keyed_name_is_aborted(self, world: dict) -> None:
        # An alias would silently retarget this override onto the candidate.
        # The override needs a base entry to load, so the realistic shape is
        # an RNBO-shadowed name (the list.* family before Q38).
        _objectfile_world(world)
        path = self._seed_aliases(world)
        overrides = world["db_root"] / "overrides.json"
        data = json.loads(overrides.read_text())
        data["objects"]["list.len"] = {"digest": "expert note"}
        overrides.write_text(json.dumps(data, indent=2, ensure_ascii=True))
        before = path.read_bytes()
        out = world["repo"].parent / "aliases-report.json"
        code = _run(
            world, "--apply", "aliases", "--shadowed", "--names", "list.len", "--json", str(out),
        )
        assert code == 1
        assert path.read_bytes() == before
        result = json.loads(out.read_text())["applied"]["aliases"][0]
        assert result["status"] == "aborted"
        assert "overrides.json" in result["reason"]
        assert "list.len" in result["reason"] and "zl.len" in result["reason"]

    def test_shadowed_requires_apply_aliases(self, world: dict) -> None:
        _objectfile_world(world)
        before = _tree_bytes(world["db_root"])
        assert _run(world, "--shadowed") == 2
        assert _run(world, "--apply", "groups", "--shadowed") == 2
        assert _tree_bytes(world["db_root"]) == before

    def test_a_failed_reload_restores_the_file(
        self, world: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _objectfile_world(world)
        path = self._seed_aliases(world)
        before = path.read_bytes()
        real_load = sync.load_db
        calls = {"n": 0}

        def failing_after_first(db_root):
            calls["n"] += 1
            if calls["n"] > 1:
                raise RuntimeError("injected reload failure")
            return real_load(db_root)

        monkeypatch.setattr(sync, "load_db", failing_after_first)
        assert _run(world, "--apply", "aliases", "--names", "jit.plus") == 2
        assert path.read_bytes() == before
        assert _mode(path) == 0o640


class TestI6AuditObjectfile:
    def test_objectfile_names_are_mapped_not_absent(self, tmp_path: Path) -> None:
        import tools.audit_db as audit_db
        from tests.test_audit_db import _add_packages, _fake_db, _make_fake_bundle

        app = _make_fake_bundle(tmp_path)
        c74 = _add_packages(app)
        (c74 / "init").mkdir(parents=True, exist_ok=True)
        (c74 / "init" / "q30-objectmappings.txt").write_text(
            "max objectfile of.alias bitand;\n"
            "max objectfile un.alias &;\n"
        )
        db_root = _fake_db(tmp_path, ["of.alias", "bare.alias", "ghost", "&"])
        report = audit_db.run_audit(repo_root=db_root.parent.parent, db_root=db_root, max_app=app)
        absent = report["sections"]["absent_from_bundle"]
        assert absent["names"] == ["ghost"]
        assert absent["count"] == 1
        assert absent["objectfile_mapped"] == [{"name": "of.alias", "file": "bitand", "class": None}]
        assert absent["objectfile_mapped_count"] == 1
        lines = audit_db.format_summary(report).splitlines()
        line = next(ln for ln in lines if "absent from Max" in ln)
        assert "+1 objectfile-mapped" in line and "+1 define-mapped" in line
        missing = report["sections"]["missing_from_db"]
        assert "un.alias" in missing["objectfile_aliases"]["unresolved"]
        assert missing["objectfile_aliases"]["lines"] == 2
        missing_line = next(ln for ln in lines if "missing from DB" in ln)
        assert "objectfile aliases unresolved" in missing_line
        assert "objectfiles" not in report["refpage_index"]
        assert len(report["sections"]) == 7


@pytest.mark.requires_max
class TestI6ObjectfileRealBundle:
    """Read-only reports of the real bundle against the real DB."""

    @pytest.fixture(scope="class")
    def section(self) -> dict:
        return sync.run_report(REAL_DB, MAX_APP_PATH)["sections"]["objectfile_aliases"]

    def test_q38_candidates(self, section: dict) -> None:
        entries = {e["name"]: e for e in section["entries"]}
        expected = {
            "mc.times~": ("mc.*~", "mc_wrapper"),
            "hslider": ("slider", "file"),
            "list.iter": ("zl.iter", "class"),
            "4mixr": ("vz.4mixr", "abstraction"),
        }
        for name, (candidate, basis) in expected.items():
            assert (entries[name]["candidate"], entries[name]["basis"]) == (candidate, basis), name

    def test_non_objectmappings_init_files_and_shadowed_names(self, section: dict) -> None:
        assert "mc.abl.dsp.chorus~" in section["names_unresolved"]
        shadowed = {e["name"]: e for e in section["domain_shadowed"]}
        assert shadowed["list.len"]["candidate"] == "zl.len"
        assert section["unresolved_count"] >= 251

    def test_audit_db_maps_objectfile_names(self) -> None:
        import tools.audit_db as audit_db

        report = audit_db.run_audit(repo_root=REPO_ROOT, db_root=REAL_DB, max_app=MAX_APP_PATH)
        absent = report["sections"]["absent_from_bundle"]
        mapped = {m["name"] for m in absent["objectfile_mapped"]}
        for name in ("jit.*", "mc.send~", "array.at"):
            assert name in mapped, name
            assert name not in absent["names"], name


# ══ I4: extract_objects.py refuses core overwrites, merges the log, skips doc pages ══


def _extract(monkeypatch: pytest.MonkeyPatch, *argv: str) -> int:
    """Run the extractor's main() through sys.argv; works with HEAD's main() too."""
    import sys

    module = _load_by_path("_q30_extract_objects", EXTRACTOR_PATH)
    monkeypatch.setattr(sys, "argv", ["extract_objects.py", *argv])
    try:
        code = module.main()
    except SystemExit as exc:
        code = exc.code
    return 0 if code is None else code


def _fake_c74(tmp_path: Path) -> Path:
    c74 = tmp_path / "C74"
    max_ref = c74 / "docs" / "refpages" / "max-ref"
    msp_ref = c74 / "docs" / "refpages" / "msp-ref"
    max_ref.mkdir(parents=True)
    msp_ref.mkdir(parents=True)
    (max_ref / "q30.obj.maxref.xml").write_text(
        _refpage(
            "q30.obj", module="max", inlets=[("int", "in")], outlets=[("int", "out")], methods=["bang"]
        )
    )
    (max_ref / "Doc Page.maxref.xml").write_text(
        _refpage("Doc Page", module="max", inlets=[], outlets=[], methods=["bang"])
    )
    (max_ref / "q30.bare.maxref.xml").write_text(_refpage("q30.bare", module="max"))
    (msp_ref / "q30.sig~.maxref.xml").write_text(
        _refpage(
            "q30.sig~", module="msp", inlets=[("signal", "in")], outlets=[("signal", "out")],
            methods=["signal"],
        )
    )
    return c74


_SEED_LOG = {
    "total_files_found": 2,
    "total_objects": 2,
    "domain_counts": {"max": 1, "msp": 1},
    "extraction_timestamp": "2026-01-01T00:00:00+00:00",
    "max_version": "9.2.0",
    "max_build": "abc",
    "sync": {"tool": "tools/sync_max_bundle.py --refresh-log"},
    "history": [{"total_objects": 1}],
}


def _seed_output(tmp_path: Path) -> Path:
    out = tmp_path / "out"
    (out / "max").mkdir(parents=True)
    (out / "msp").mkdir(parents=True)
    (out / "max" / "objects.json").write_text(
        json.dumps({"curated": {"name": "curated"}}, indent=2) + "\n"
    )
    (out / "msp" / "objects.json").write_text(
        json.dumps({"curated~": {"name": "curated~"}}, indent=2) + "\n"
    )
    (out / "extraction-log.json").write_text(json.dumps(_SEED_LOG, indent=2) + "\n")
    return out


class TestI4ExtractRefusesCore:
    def test_refuses_without_force_and_writes_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        c74, out = _fake_c74(tmp_path), _seed_output(tmp_path)
        before = _tree_bytes(out)
        code = _extract(monkeypatch, "--max-path", str(c74), "--output", str(out))
        err = capsys.readouterr().err
        assert code == 2
        assert "tools/sync_max_bundle.py" in err and "--force" in err
        assert _tree_bytes(out) == before

    def test_force_rebuilds_and_merges_the_log(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        c74, out = _fake_c74(tmp_path), _seed_output(tmp_path)
        assert _extract(monkeypatch, "--max-path", str(c74), "--output", str(out), "--force") == 0
        rebuilt = json.loads((out / "max" / "objects.json").read_text())
        assert "q30.obj" in rebuilt and "Doc Page" not in rebuilt
        log = json.loads((out / "extraction-log.json").read_text())
        assert set(_SEED_LOG) <= set(log)
        assert log["sync"] == _SEED_LOG["sync"]
        assert len(log["history"]) == len(_SEED_LOG["history"]) + 1
        assert log["last_extraction"]["mode"] == "full"

    def test_a_single_domain_run_is_refused_too(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        c74, out = _fake_c74(tmp_path), _seed_output(tmp_path)
        before = _tree_bytes(out)
        code = _extract(monkeypatch, "--max-path", str(c74), "--output", str(out), "--domain", "msp")
        assert code == 2
        assert _tree_bytes(out) == before


class TestI4ExtractLogMerge:
    def test_package_run_merges_the_real_log_shape(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        out = tmp_path / "out"
        (out / "packages").mkdir(parents=True)
        old = json.loads((REAL_DB / "extraction-log.json").read_text())
        (out / "extraction-log.json").write_text(json.dumps(old, indent=2) + "\n")
        (out / "package_info.json").write_text(json.dumps({}, indent=2) + "\n")
        pkg = tmp_path / "FakePackage"
        (pkg / "docs").mkdir(parents=True)
        (pkg / "docs" / "x.maxref.xml").write_text(
            _refpage("fake.x", inlets=[("int", "in")], outlets=[("int", "out")], methods=["bang"])
        )
        code = _extract(monkeypatch, "--package", "Fake", "--path", str(pkg), "--output", str(out))
        assert code == 0

        log = json.loads((out / "extraction-log.json").read_text())
        for key in old:
            assert key in log, key
        for key in ("sync", "max_version", "max_build"):
            assert log[key] == old[key], key
        superseded = {k: old[k] for k in sync._LOG_HISTORY_FIELDS if k in old}
        assert log["history"] == list(old.get("history") or []) + [superseded]
        assert log["last_extraction"]["package"] == "Fake"
        live = len(json.loads((out / "packages" / "Fake" / "objects.json").read_text()))
        assert log["total_objects"] == live == 1


class TestI4DocPageFilter:
    def test_whitespace_named_pages_are_not_extracted(self, tmp_path: Path) -> None:
        module = _load_by_path("_q30_extract_objects_doc", EXTRACTOR_PATH)
        result = module.extract_all(_fake_c74(tmp_path))
        names = {n for bucket in result["domains"].values() for n in bucket}
        assert "Doc Page" not in names
        assert "Doc Page" in result["log"]["documentation_pages"]
        assert "q30.bare" in names  # no I/O lists, no methods: still an object to the extractor

    def test_sync_doc_page_rule_is_unchanged(self) -> None:
        """Green guard (the whitespace and no-I/O shapes) plus the shared name rule."""
        assert sync._is_doc_page({"name": "Doc Page", "inlets": [{}], "outlets": [{}], "methods": ["x"]})
        assert sync._is_doc_page({"name": "q30.bare", "inlets": [], "outlets": [], "methods": []})
        assert not sync._is_doc_page({"name": "q30.obj", "inlets": [{}], "outlets": [], "methods": []})
        assert sync.is_doc_page_name("MC Wrapper Features")
        assert not sync.is_doc_page_name("jit.gl.pbr")

    @pytest.mark.requires_max
    def test_real_bundle_in_memory(self) -> None:
        module = _load_by_path("_q30_extract_objects_real", EXTRACTOR_PATH)
        result = module.extract_all(MAX_APP_PATH / "Contents" / "Resources" / "C74")
        names = {n for bucket in result["domains"].values() for n in bucket}
        for doc in (
            "MC Wrapper Features", "Snapshot Messages", "Jitter GL Object (OB3D) Messages",
            "Jitter Matrix Operators", "Parameter Properties", "Jitter Geometry Features",
        ):
            assert doc not in names, doc
        for name in (
            "jbox", "onecopy", "project", "jit.graph", "jit.plot", "jit.mo.fieldmask",
            "jit.mo.join", "mira.motion", "mira.multitouch",
        ):
            assert name in names, name


@pytest.mark.requires_max
class TestI4RealDbCopyRefused:
    def test_scratch_copy_of_the_real_db_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        copy_root = scratch_copy_of_real_db(tmp_path / "db-copy")
        before = _tree_bytes(copy_root)
        code = _extract(
            monkeypatch, "--max-path", str(MAX_APP_PATH / "Contents" / "Resources" / "C74"),
            "--output", str(copy_root),
        )
        assert code == 2
        assert _tree_bytes(copy_root) == before


# ══ I5: audit merger, confidence and variable_io proposals ══


def _audit_entry(**fields) -> dict:
    entry = dict(fields)
    entry["_audit"] = {"confidence": "HIGH", "instances": 5, "agreement": 1.0, "source": "io_count_finding"}
    return entry


def _port(idx: int) -> dict:
    return {"id": idx, "type": "", "signal": False, "digest": ""}


def _write_json(path: Path, data: dict, *, ensure_ascii: bool = False, newline: bool = True) -> Path:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=ensure_ascii) + ("\n" if newline else ""))
    return path


def _proposal(tmp_path: Path, objects: dict | None = None, conflicts: dict | None = None) -> Path:
    return _write_json(
        tmp_path / "proposed-overrides.json",
        {"_comment": "proposed", "objects": objects or {}, "conflicts": conflicts or {}},
    )


def _overrides(tmp_path: Path, objects: dict | None = None, **style) -> Path:
    return _write_json(
        tmp_path / "overrides.json",
        {
            "_comment": "Expert corrections.",
            "objects": objects or {},
            "version_map": {},
            "variable_io_rules": {"pack": {"inlet_count": "arg_count"}},
        },
        **style,
    )


@pytest.fixture(scope="module")
def real_db():
    from src.maxpat.db_lookup import ObjectDatabase

    return ObjectDatabase()


_MANUAL_COLL = {"inlets": [_port(0), _port(1)], "_note": "expert entry"}


class TestI5MergeTimeConflicts:
    def test_a_manual_entry_added_after_the_audit_survives(self, tmp_path: Path, real_db) -> None:
        from src.maxpat.audit.merger import OverrideMerger

        proposed = _proposal(tmp_path, objects={"coll": _audit_entry(inlets=[_port(0)])})
        overrides = _overrides(tmp_path, objects={"coll": _MANUAL_COLL})
        merger = OverrideMerger(proposed, overrides, real_db)
        merged = merger.merge()
        assert merged["objects"]["coll"] == _MANUAL_COLL
        conflicts = merger.detect_conflicts()
        assert conflicts["coll"]["reason"] == "CONFLICT_WITH_MANUAL"
        assert conflicts["coll"]["existing_manual"] == _MANUAL_COLL

    def test_adopt_fields_resolve_a_merge_time_conflict(self, tmp_path: Path, real_db) -> None:
        from src.maxpat.audit.merger import OverrideMerger

        proposed = _proposal(tmp_path, objects={"coll": _audit_entry(inlets=[_port(0)])})
        overrides = _overrides(tmp_path, objects={"coll": _MANUAL_COLL})
        merged = OverrideMerger(proposed, overrides, real_db).merge({"coll": {"adopt_fields": ["inlets"]}})
        coll = merged["objects"]["coll"]
        assert coll["inlets"] == [_port(0)]
        assert coll["_note"] == "expert entry"
        assert coll["_manual_original"] == _MANUAL_COLL

    def test_a_conflict_whose_manual_entry_was_removed_lands(self, tmp_path: Path, real_db) -> None:
        from src.maxpat.audit.merger import OverrideMerger

        audit = _audit_entry(inlets=[_port(0), _port(1)])
        proposed = _proposal(
            tmp_path,
            conflicts={
                "line~": {"audit_proposed": audit, "existing_manual": {"x": 1}, "reason": "CONFLICT_WITH_MANUAL"}
            },
        )
        overrides = _overrides(tmp_path)
        merger = OverrideMerger(proposed, overrides, real_db)
        merged = merger.merge()
        assert merged["objects"]["line~"] == audit
        assert merger.detect_conflicts() == {}

    def test_merge_rereads_the_live_file(self, tmp_path: Path, real_db) -> None:
        from src.maxpat.audit.merger import OverrideMerger

        proposed = _proposal(tmp_path, objects={"coll": _audit_entry(inlets=[_port(0)])})
        overrides = _overrides(tmp_path)
        merger = OverrideMerger(proposed, overrides, real_db)
        _overrides(tmp_path, objects={"coll": _MANUAL_COLL})  # manual edit after construction
        assert merger.merge()["objects"]["coll"] == _MANUAL_COLL


class TestI5MergerWrite:
    def test_a_no_op_merge_of_the_real_file_is_byte_identical(self, tmp_path: Path, real_db) -> None:
        from src.maxpat.audit.merger import OverrideMerger

        copy_path = tmp_path / "overrides.json"
        copy_path.write_bytes((REAL_DB / "overrides.json").read_bytes())
        before = copy_path.read_bytes()
        merger = OverrideMerger(_proposal(tmp_path), copy_path, real_db)
        assert merger.write(merger.merge()) is False
        assert copy_path.read_bytes() == before

    def test_new_proposal_appends_to_its_group_and_only_adds_lines(self, tmp_path: Path, real_db) -> None:
        import difflib

        from src.maxpat.audit.merger import OverrideMerger

        objects = {
            "_domain_max": "--- Max Objects ---",
            "zl": {"_note": "café"},
            "counter": {"_note": "unsorted on purpose"},
            "_domain_msp": "--- MSP Objects ---",
            "adsr~": {"_note": "msp"},
        }
        overrides = _overrides(tmp_path, objects=objects, ensure_ascii=True, newline=False)
        old_text = overrides.read_text()
        proposed = _proposal(tmp_path, objects={"coll": _audit_entry(inlets=[_port(0)])})
        merger = OverrideMerger(proposed, overrides, real_db)
        merged = merger.merge()
        assert list(merged["objects"]) == ["_domain_max", "zl", "counter", "coll", "_domain_msp", "adsr~"]
        assert merger.write(merged) is True
        new_text = overrides.read_text()
        assert not new_text.endswith("\n")
        assert new_text.isascii()
        removed = [
            line for line in difflib.unified_diff(old_text.splitlines(), new_text.splitlines(), lineterm="")
            if line.startswith("-") and not line.startswith("---")
        ]
        assert removed == []

    def test_write_keeps_mode_through_atomic_write_bytes(
        self, tmp_path: Path, real_db, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import src.maxpat.audit.merger as merger_mod

        overrides = _overrides(tmp_path)
        os.chmod(overrides, 0o640)
        calls = []
        real_writer = merger_mod.atomic_write_bytes if hasattr(merger_mod, "atomic_write_bytes") else None

        def spy(path, payload):
            calls.append(Path(path))
            return real_writer(path, payload)

        monkeypatch.setattr(merger_mod, "atomic_write_bytes", spy, raising=False)
        merger = merger_mod.OverrideMerger(
            _proposal(tmp_path, objects={"adsr~": _audit_entry(inlets=[_port(0)])}), overrides, real_db
        )
        assert merger.write(merger.merge()) is True
        assert calls == [overrides]
        assert _mode(overrides) == 0o640

    def test_stale_guard_refuses_to_clobber_a_newer_edit(self, tmp_path: Path, real_db) -> None:
        import src.maxpat.audit.merger as merger_mod

        overrides = _overrides(tmp_path)
        merger = merger_mod.OverrideMerger(
            _proposal(tmp_path, objects={"adsr~": _audit_entry(inlets=[_port(0)])}), overrides, real_db
        )
        merged = merger.merge()
        _overrides(tmp_path, objects={"coll": _MANUAL_COLL})  # someone edits the file
        edited = overrides.read_bytes()
        with pytest.raises(merger_mod.OverridesChangedError):
            merger.write(merged)
        assert overrides.read_bytes() == edited

    def test_a_new_domain_group_lands_in_domain_order(self, tmp_path: Path, real_db) -> None:
        """Green guard: msp goes between the max and jitter groups."""
        from src.maxpat.audit.merger import OverrideMerger

        objects = {
            "_domain_max": "--- Max Objects ---",
            "zl": {"_note": "max"},
            "_domain_jitter": "--- Jitter Objects ---",
            "jit.matrix": {"_note": "jit"},
        }
        overrides = _overrides(tmp_path, objects=objects)
        proposed = _proposal(tmp_path, objects={"adsr~": _audit_entry(inlets=[_port(0)])})
        merged = OverrideMerger(proposed, overrides, real_db).merge()
        headers = [k for k in merged["objects"] if k.startswith("_domain_")]
        assert headers == ["_domain_max", "_domain_msp", "_domain_jitter"]


def _box(name: str, text: str, numinlets: int, numoutlets: int, box_id: str = "obj-1"):
    from src.maxpat.audit import BoxInstance

    return BoxInstance(
        name=name,
        text=text,
        numinlets=numinlets,
        numoutlets=numoutlets,
        outlettype=[""] * numoutlets,
        patching_rect=[0.0, 0.0, 50.0, 22.0],
        box_id=box_id,
        depth=0,
        is_connected=True,
        connections=[],
        source_file=f"{name}.maxhelp",
    )


def _mock_db(defaults=(1, 1), outlet_types=None):
    from unittest.mock import MagicMock

    db = MagicMock()
    db.compute_io_counts.return_value = defaults
    db.get_outlet_types.return_value = outlet_types if outlet_types is not None else [""]
    db.lookup.return_value = {"inlets": [{"id": 0}], "outlets": [{"id": 0}], "variable_io": False}
    db._aliases = {}
    return db


class TestI5ConfidenceThreshold:
    def test_high_needs_three_instances(self) -> None:
        from src.maxpat.audit import analyzer

        assert analyzer.MIN_HIGH_INSTANCES == 3
        assert analyzer.compute_confidence([1], lambda x: x)[0] == "MEDIUM"
        assert analyzer.compute_confidence([1, 1], lambda x: x)[0] == "MEDIUM"
        assert analyzer.compute_confidence([1, 1, 1], lambda x: x)[0] == "HIGH"

    def test_one_mismatching_instance_is_medium(self) -> None:
        from src.maxpat.audit.analyzer import AuditAnalyzer

        db = _mock_db(outlet_types=["signal"])
        finding = AuditAnalyzer(db).analyze_outlet_types("thing~", [_box("thing~", "thing~", 1, 1)])
        assert finding is not None
        assert finding["confidence"] == "MEDIUM"


class TestI5VariableIoProposal:
    def _bucket(self):
        return [
            _box("bucket", "bucket", 1, 1, "obj-1"),
            _box("bucket", "bucket 4", 1, 4, "obj-2"),
            _box("bucket", "bucket 4", 1, 4, "obj-3"),
            _box("bucket", "bucket 4", 1, 4, "obj-4"),
        ]

    def test_argument_dependent_counts_become_a_rule(self) -> None:
        from src.maxpat.audit.analyzer import AuditAnalyzer

        finding = AuditAnalyzer(_mock_db()).analyze_io_counts("bucket", self._bucket())
        assert finding["counts_follow_arguments"] is True
        assert finding["help_outlets"] is None
        assert finding["help_inlets"] is None
        assert finding["proposed_variable_io"] == {
            "inlet_count": "fixed:1",
            "outlet_count": "first_arg",
            "default_inlets": 1,
            "default_outlets": 1,
        }

    def test_generator_proposes_a_rule_never_a_default_count(self, tmp_path: Path) -> None:
        from src.maxpat.audit.analyzer import AuditAnalyzer, ObjectFindings
        from src.maxpat.audit.overrides import OverrideGenerator

        db = _mock_db()
        finding = AuditAnalyzer(db).analyze_io_counts("bucket", self._bucket())
        overrides = _overrides(tmp_path)
        proposed = OverrideGenerator(db, overrides_path=overrides).generate_proposed_overrides(
            {"bucket": ObjectFindings("bucket", 4, io_count_finding=finding)}
        )
        assert len(proposed["objects"].get("bucket", {}).get("outlets", [])) != 4
        rule = proposed["variable_io_rules"]["bucket"]
        assert (rule["inlet_count"], rule["outlet_count"]) == ("fixed:1", "first_arg")
        assert rule["_audit"]["instances"] == 4
        assert rule["_audit"]["distinct_arguments"] == 2
        assert rule["_audit"]["source"] == "io_count_finding"
        assert rule["existing_rule"] is None

    def test_second_arg_plus_one(self) -> None:
        from src.maxpat.audit.analyzer import AuditAnalyzer

        instances = [_box("x", "x 2 3", 2, 4, "obj-1"), _box("x", "x 2 5", 2, 6, "obj-2")]
        finding = AuditAnalyzer(_mock_db()).analyze_io_counts("x", instances)
        assert finding["counts_follow_arguments"] is True
        assert finding["proposed_variable_io"]["outlet_count"] == "second_arg+1"
        assert finding["proposed_variable_io"]["inlet_count"] == "fixed:2"

    def test_one_args_key_with_two_count_pairs_is_todays_finding(self) -> None:
        """Green guard."""
        from src.maxpat.audit.analyzer import AuditAnalyzer

        instances = [_box("y", "y 3", 1, 2, "obj-1"), _box("y", "y 3", 1, 3, "obj-2")]
        finding = AuditAnalyzer(_mock_db()).analyze_io_counts("y", instances)
        assert finding.get("counts_follow_arguments", False) is False
        assert finding.get("proposed_variable_io") is None
        assert finding["help_outlets"] in (2, 3)

    def test_all_equal_counts_are_todays_finding(self) -> None:
        """Green guard."""
        from src.maxpat.audit.analyzer import AuditAnalyzer

        instances = [_box("z", "z", 1, 2, "obj-1"), _box("z", "z 4", 1, 2, "obj-2")]
        finding = AuditAnalyzer(_mock_db()).analyze_io_counts("z", instances)
        assert finding.get("counts_follow_arguments", False) is False
        assert finding["help_outlets"] == 2


_FORMULAS = (
    "fixed:3", "first_arg", "first_arg+1", "second_arg", "second_arg+1", "second_arg+2",
    "arg_count", "arg_count+1", "arg_count_or_default",
)


class TestI5FormulaParity:
    @pytest.mark.parametrize("formula", _FORMULAS)
    @pytest.mark.parametrize("args", [[], ["3"], ["3", "5"], ["1", "2", "4"]])
    def test_matches_object_database(self, real_db, formula: str, args: list) -> None:
        from src.maxpat.audit.analyzer import _formula_count

        assert _formula_count(formula, args, 2) == real_db._apply_io_formula(formula, args, 2)

    def test_non_integer_arguments_give_none(self) -> None:
        from src.maxpat.audit.analyzer import _formula_count

        assert _formula_count("first_arg", ["x"], 2) is None
        assert _formula_count("second_arg+1", ["1", "y"], 2) is None
        assert _formula_count("arg_count", ["x"], 2) == 1


class TestI5CliOverridesPath:
    def _setup(self, tmp_path: Path) -> tuple[Path, Path]:
        out = tmp_path / "audit"
        out.mkdir()
        _proposal(out, objects={
            "coll": _audit_entry(inlets=[_port(0)]),
            "adsr~": _audit_entry(inlets=[_port(0)]),
        })
        copy_path = _overrides(tmp_path, objects={"coll": _MANUAL_COLL})
        return out, copy_path

    def test_merge_writes_only_the_named_copy(self, tmp_path: Path) -> None:
        from src.maxpat.audit.cli import main

        real = REAL_DB / "overrides.json"
        real_sha = hashlib.sha256(real.read_bytes()).hexdigest()
        out, copy_path = self._setup(tmp_path)
        assert main(["--merge", "--output-dir", str(out), "--overrides", str(copy_path)]) == 0
        merged = json.loads(copy_path.read_text())["objects"]
        assert merged["coll"] == _MANUAL_COLL
        assert "adsr~" in merged
        assert hashlib.sha256(real.read_bytes()).hexdigest() == real_sha

    def test_dry_run_leaves_the_copy_alone(self, tmp_path: Path) -> None:
        from src.maxpat.audit.cli import main

        out, copy_path = self._setup(tmp_path)
        before = copy_path.read_bytes()
        assert main(["--merge", "--output-dir", str(out), "--overrides", str(copy_path), "--dry-run"]) == 0
        assert copy_path.read_bytes() == before
