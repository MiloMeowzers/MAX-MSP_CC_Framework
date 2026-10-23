"""Q38 part 3 (quick 261022-mis): version-aware I/O and validate_patch(target_version=...).

Bundle help boxes record the I/O of the Max build that saved them
(``patcher.appversion``). Where builds disagree for the same name and
arguments, and the disagreement is a strict version-ordered partition,
``help_io.scan_version_io`` records the change; ``--apply version-io`` writes
``.claude/max-objects/version_io.json``. ``validate_patch(..., target_version=)``
then warns (layer ``version``, never an error) about boxes that need a newer
Max and cords on ports an older build lacks.

Hermetic tests use a fake bundle / fake DB under ``tmp_path``; the real DB is
only read. Tests that read the installed Max bundle carry ``requires_max``.
"""

from __future__ import annotations

import copy
import json
import warnings
from pathlib import Path

import pytest

import tools.help_io as help_io
import tools.sync_max_bundle as sync
from src.maxpat.db_lookup import ObjectDatabase, parse_version
from src.maxpat.validation import validate_patch
from tests.conftest import MAX_APP_PATH
from tests.test_sync_max_bundle import _make_bundle, _make_db

REPO_ROOT = Path(__file__).resolve().parents[1]
REAL_DB = REPO_ROOT / ".claude" / "max-objects"


# ── parse_version ─────────────────────────────────────────────────


@pytest.mark.parametrize("text,expected", [
    ("9", (9, 0, 0)),
    ("9.0", (9, 0, 0)),
    ("9.0.3", (9, 0, 3)),
    ("8.1", (8, 1, 0)),
    ("9.10", (9, 10, 0)),
])
def test_parse_version(text, expected) -> None:
    assert parse_version(text) == expected


@pytest.mark.parametrize("bad", ["nine", "9.x", "", "9.0.0.1", " 9", 9, 9.0, None, True])
def test_parse_version_rejects(bad) -> None:
    with pytest.raises(ValueError):
        parse_version(bad)


# ── Mining on a fake bundle ───────────────────────────────────────


def _help(app: Path, rel: str, version: tuple[int, int, int], boxes: list[dict]) -> None:
    path = app / "Contents" / "Resources" / "C74" / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    major, minor, revision = version
    path.write_text(json.dumps({"patcher": {
        "appversion": {"major": major, "minor": minor, "revision": revision},
        "boxes": [{"box": dict(b, id=f"obj-{i}")} for i, b in enumerate(boxes, 1)],
        "lines": [],
    }}))


def _old(text: str, ni: int, no: int) -> dict:
    return {"maxclass": "newobj", "text": text, "numinlets": ni, "numoutlets": no}


@pytest.fixture
def fake(tmp_path: Path) -> dict:
    app = _make_bundle(tmp_path)
    root = _make_db(tmp_path)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        db = ObjectDatabase(root)
    return {"app": app, "db_root": root, "db": db,
            "argv": ["--max-app", str(app), "--db-root", str(root),
                     "--repo-root", str(tmp_path / "repo")]}


class TestMining:
    def test_strict_partition_is_a_change(self, fake: dict) -> None:
        _help(fake["app"], "help/max/a.maxhelp", (8, 6, 5), [_old("old", 1, 1), _old("old", 1, 1)])
        _help(fake["app"], "help/max/b.maxhelp", (9, 0, 0), [_old("old", 1, 2)])
        scan = help_io.scan_version_io(fake["app"], fake["db"], installed="9.2.0")
        entry = scan["objects"]["old"]
        assert entry["changes"] == [{
            "after": "8.6.5", "by": "9.0.0", "inlets": 0, "outlets": 1,
            "newer_than_installed": False,
        }]
        assert entry["evidence"] == [{
            "args": [],
            "segments": [
                {"inlets": 1, "outlets": 1, "first": "8.6.5", "last": "8.6.5", "boxes": 2},
                {"inlets": 1, "outlets": 2, "first": "9.0.0", "last": "9.0.0", "boxes": 1},
            ],
            "example": "help/max/a.maxhelp",
        }]
        assert scan["conflicting"] == [] and scan["ambiguous_names"] == []

    def test_change_newer_than_installed_is_flagged(self, fake: dict) -> None:
        _help(fake["app"], "help/max/a.maxhelp", (9, 0, 0), [_old("old", 1, 1)])
        _help(fake["app"], "help/max/b.maxhelp", (9, 3, 0), [_old("old", 1, 2)])
        scan = help_io.scan_version_io(fake["app"], fake["db"], installed="9.2.0")
        assert scan["objects"]["old"]["changes"][0]["newer_than_installed"] is True

    def test_interleaved_versions_are_ambiguous(self, fake: dict) -> None:
        _help(fake["app"], "help/max/a.maxhelp", (8, 6, 5), [_old("old", 1, 1)])
        _help(fake["app"], "help/max/b.maxhelp", (9, 0, 0), [_old("old", 1, 2)])
        _help(fake["app"], "help/max/c.maxhelp", (9, 1, 0), [_old("old", 1, 1)])
        scan = help_io.scan_version_io(fake["app"], fake["db"])
        assert scan["objects"] == {}
        assert scan["ambiguous_groups"] == 1
        assert scan["ambiguous_names"] == ["old"]

    def test_arg_groups_with_different_deltas_conflict(self, fake: dict) -> None:
        _help(fake["app"], "help/max/a.maxhelp", (8, 6, 5), [_old("old 1", 1, 1), _old("old 2", 1, 1)])
        _help(fake["app"], "help/max/b.maxhelp", (9, 0, 0), [_old("old 1", 1, 2), _old("old 2", 2, 1)])
        scan = help_io.scan_version_io(fake["app"], fake["db"])
        assert "old" not in scan["objects"]
        assert scan["conflicting"] == ["old"]

    def test_arg_groups_with_equal_deltas_narrow_the_interval(self, fake: dict) -> None:
        _help(fake["app"], "help/max/a.maxhelp", (8, 0, 0), [_old("old 1", 1, 1)])
        _help(fake["app"], "help/max/b.maxhelp", (8, 6, 5), [_old("old 2", 1, 1)])
        _help(fake["app"], "help/max/c.maxhelp", (9, 0, 0), [_old("old 2", 1, 2)])
        _help(fake["app"], "help/max/d.maxhelp", (9, 1, 0), [_old("old 1", 1, 2)])
        changes = help_io.scan_version_io(fake["app"], fake["db"])["objects"]["old"]["changes"]
        assert [(c["after"], c["by"]) for c in changes] == [("8.6.5", "9.0.0")]

    def test_one_io_records_nothing(self, fake: dict) -> None:
        _help(fake["app"], "help/max/a.maxhelp", (8, 6, 5), [_old("old", 1, 1)])
        _help(fake["app"], "help/max/b.maxhelp", (9, 0, 0), [_old("old", 1, 1)])
        scan = help_io.scan_version_io(fake["app"], fake["db"])
        assert scan["objects"] == {} and scan["conflicting"] == [] and scan["ambiguous_groups"] == 0

    def test_unresolved_unknown_version_and_bad_files(self, fake: dict) -> None:
        _help(fake["app"], "help/max/a.maxhelp", (8, 6, 5), [_old("ghost.obj", 1, 1)])
        _help(fake["app"], "help/max/b.maxhelp", (9, 0, 0), [_old("ghost.obj", 1, 2)])
        unknown = fake["app"] / "Contents" / "Resources" / "C74" / "help" / "max" / "c.maxhelp"
        unknown.write_text(json.dumps({"patcher": {"boxes": [{"box": dict(_old("old", 1, 5), id="x")}]}}))
        (unknown.parent / "d.maxhelp").write_text("{nope")
        scan = help_io.scan_version_io(fake["app"], fake["db"])
        assert scan["objects"] == {}
        assert [b["file"] for b in scan["bad_files"]] == ["help/max/d.maxhelp"]

    def test_no_bundle_is_unavailable(self, tmp_path: Path, fake: dict) -> None:
        assert help_io.scan_version_io(tmp_path / "Nope.app", fake["db"])["available"] is False


# ── Writer and section ────────────────────────────────────────────


class TestWriter:
    def test_refuses_any_other_path(self, tmp_path: Path) -> None:
        root = tmp_path / "db"
        root.mkdir()
        for bad in (root / "idioms.json", root / "max" / "version_io.json", tmp_path / "version_io.json"):
            with pytest.raises(sync.WriteRefused):
                sync.write_version_io_file(bad, {"objects": {}}, root)
        assert not any(root.iterdir())

    def test_canonical_and_idempotent(self, tmp_path: Path) -> None:
        root = tmp_path / "db"
        root.mkdir()
        data = {"_comment": "c", "objects": {"zz": {"changes": []}, "aa": {"changes": []}}}
        assert sync.write_version_io_file(root / "version_io.json", data, root) is True
        raw = (root / "version_io.json").read_bytes()
        assert raw == sync.canonical_version_io_bytes(data)
        assert raw.decode().index('"aa"') < raw.decode().index('"zz"')
        assert raw.endswith(b"\n")
        assert sync.write_version_io_file(root / "version_io.json", data, root) is False
        assert (root / "version_io.json").read_bytes() == raw

    def test_section_counts_and_apply(self, fake: dict, capsys) -> None:
        _help(fake["app"], "help/max/a.maxhelp", (8, 6, 5), [_old("old", 1, 1)])
        _help(fake["app"], "help/max/b.maxhelp", (9, 0, 0), [_old("old", 1, 2)])
        root = fake["db_root"]
        section = sync.run_report(root, fake["app"])["sections"]["version_io"]
        assert (section["names"], section["added"], section["removed"], section["changed"]) == (1, 1, 0, 0)

        stale = {"objects": {"gone": {"changes": []}, "old": {"changes": [], "evidence": []}}}
        (root / "version_io.json").write_bytes(sync.canonical_version_io_bytes(stale))
        section = sync.section_version_io(sync.build_bundle_index(fake["app"]), root)
        assert (section["added"], section["removed"], section["changed"]) == (0, 1, 1)

        assert sync.main([*fake["argv"], "--apply", "version-io"]) == 0
        written = json.loads((root / "version_io.json").read_text())
        assert set(written["objects"]) == {"old"}
        assert written["generator"] == "tools/sync_max_bundle.py --apply version-io"
        capsys.readouterr()
        assert sync.main(fake["argv"]) == 0
        out = capsys.readouterr().out
        assert "  version io      : 1 names with per-version I/O changes (0 ambiguous arg groups, " \
               "0 conflicting); +0 -0 ~0 vs version_io.json (--apply version-io)" in out

    def test_section_keys(self) -> None:
        keys = sync.SECTION_KEYS
        assert keys[keys.index("idioms") + 1] == "version_io"
        assert "version-io" in sync.APPLY_MODES


# ── DB accessors ──────────────────────────────────────────────────


def _vio_db(tmp_path: Path, doc: dict | None) -> ObjectDatabase:
    root = _make_db(tmp_path)
    (root / "aliases.json").write_text(json.dumps({"aliases": {"o": "old"}}, indent=2) + "\n")
    if doc is not None:
        (root / "version_io.json").write_text(json.dumps(doc, indent=2) + "\n")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return ObjectDatabase(root)


_CHANGE = {"after": "9.0.0", "by": "9.0.5", "inlets": 0, "outlets": 2}


class TestDbAccessors:
    def test_io_changes_alias_canonical_and_copied(self, tmp_path: Path) -> None:
        db = _vio_db(tmp_path, {"max_version": "9.2.0", "objects": {
            "o": {"changes": [dict(_CHANGE, by="9.1.0", after="9.0.5"), _CHANGE]},
        }})
        changes = db.io_changes("old")
        assert [c["by"] for c in changes] == ["9.0.5", "9.1.0"]
        assert db.io_changes("o") == changes
        changes[0]["outlets"] = 99
        assert db.io_changes("old")[0]["outlets"] == 2
        assert db.io_changes("nothing") == []
        assert db.version_io_max_version == "9.2.0"

    def test_absent_file(self, tmp_path: Path) -> None:
        db = _vio_db(tmp_path, None)
        assert db.io_changes("old") == []
        assert db.version_io_max_version is None

    @pytest.mark.parametrize("change", [
        dict(_CHANGE, after="9.0.5"),
        dict(_CHANGE, by="later"),
        dict(_CHANGE, inlets="0"),
        {"after": "9.0.0", "by": "9.0.5"},
    ])
    def test_malformed_file_fails_fast(self, tmp_path: Path, change: dict) -> None:
        with pytest.raises(ValueError, match="version_io.json"):
            _vio_db(tmp_path, {"objects": {"old": {"changes": [change]}}})

    def test_min_version(self, tmp_path: Path) -> None:
        db = _vio_db(tmp_path, None)
        assert db.min_version("old") == "8"  # the fake DB stores the number 8
        assert db.min_version("o") == "8"
        assert db.min_version("nothing") is None


# ── validate_patch(target_version=...) on the real DB ─────────────


@pytest.fixture(scope="module")
def real_db() -> ObjectDatabase:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return ObjectDatabase()


def _mousestate_scope(outlet: int = 7) -> dict:
    return {
        "boxes": [
            {"box": {"id": "obj-1", "maxclass": "newobj", "text": "mousestate",
                     "numinlets": 1, "numoutlets": 10, "outlettype": [""] * 10,
                     "patching_rect": [10, 10, 80, 22]}},
            {"box": {"id": "obj-2", "maxclass": "newobj", "text": "print",
                     "numinlets": 1, "numoutlets": 0, "patching_rect": [10, 60, 40, 22]}},
        ],
        "lines": [{"patchline": {"source": ["obj-1", outlet], "destination": ["obj-2", 0]}}],
    }


def _patch(scope: dict) -> dict:
    return {"patcher": dict(scope, fileversion=1, rect=[0, 0, 600, 400])}


def _version(results) -> list:
    return [r for r in results if r.layer == "version"]


@pytest.mark.requires_max
class TestCommittedFile:
    def test_mousestate_change_is_recorded(self, real_db: ObjectDatabase) -> None:
        changes = real_db.io_changes("mousestate")
        assert changes and changes[0]["after"] == "9.0.0" and changes[0]["by"] == "9.0.5"


class TestTargetVersion:
    def test_target_version_warns_on_missing_port(self, real_db: ObjectDatabase) -> None:
        patch = _patch(_mousestate_scope())
        found = _version(validate_patch(patch, db=real_db, target_version="9.0"))
        assert len(found) == 1
        r = found[0]
        assert r.level == "warning"
        for part in ("obj-1", "mousestate", "outlet 7", "9.0", "version_io"):
            assert part in r.message, part
        assert len(_version(validate_patch(patch, db=real_db, target_version="9.0.3"))) == 1
        assert _version(validate_patch(patch, db=real_db, target_version="9.1")) == []
        assert _version(validate_patch(patch, db=real_db)) == []

    def test_low_outlets_never_warn(self, real_db: ObjectDatabase) -> None:
        patch = _patch(_mousestate_scope(outlet=0))
        assert _version(validate_patch(patch, db=real_db, target_version="9.0")) == []

    def test_min_version(self, real_db: ObjectDatabase) -> None:
        assert real_db.min_version("jit.message") == "9.2"
        patch = _patch({"boxes": [{"box": {
            "id": "obj-1", "maxclass": "newobj", "text": "jit.message",
            "numinlets": 1, "numoutlets": 2, "outlettype": ["", ""],
            "patching_rect": [10, 10, 80, 22]}}], "lines": []})
        found = _version(validate_patch(patch, db=real_db, target_version="9.0"))
        assert len(found) == 1
        assert "9.2" in found[0].message and "obj-1" in found[0].message
        assert "No such object" in found[0].message
        assert _version(validate_patch(patch, db=real_db, target_version="9.2")) == []

    def test_target_at_or_before_after_says_lost(self, real_db: ObjectDatabase) -> None:
        """IN-04: the evidence brackets a change (after, by]. A target at or
        before ``after`` certainly lacks the port."""
        patch = _patch(_mousestate_scope())
        [r] = _version(validate_patch(patch, db=real_db, target_version="9.0"))
        assert "is lost on Max 9.0" in r.message
        assert (r.rule, r.box_ids, r.port) == ("version_io_port", ("obj-1",), 7)

    def test_target_inside_interval_says_may_be_missing(self, real_db: ObjectDatabase) -> None:
        """IN-04: after < target < by -- the evidence cannot say which side
        of the change the target build is on."""
        patch = _patch(_mousestate_scope())
        [r] = _version(validate_patch(patch, db=real_db, target_version="9.0.3"))
        assert "is lost" not in r.message
        assert "may be missing on Max 9.0.3" in r.message
        assert "changed between 9.0.0 and 9.0.5" in r.message

    def test_live_meter_target_8_may_be_missing(self, real_db: ObjectDatabase) -> None:
        patch = _patch({
            "boxes": [
                {"box": {"id": "obj-1", "maxclass": "newobj", "text": "live.meter~",
                         "numinlets": 1, "numoutlets": 2, "outlettype": ["", ""],
                         "patching_rect": [10, 10, 80, 22]}},
                {"box": {"id": "obj-2", "maxclass": "newobj", "text": "print",
                         "numinlets": 1, "numoutlets": 0, "patching_rect": [10, 60, 40, 22]}},
            ],
            "lines": [{"patchline": {"source": ["obj-1", 1], "destination": ["obj-2", 0]}}],
        })
        def port_rows(target):
            return [r for r in _version(validate_patch(patch, db=real_db,
                                                       target_version=target))
                    if r.rule == "version_io_port"]

        [r] = port_rows("8.0")
        assert "may be missing on Max 8.0" in r.message
        assert "changed between 7.0.3 and 9.0.0" in r.message
        [r7] = port_rows("7.0")
        assert "is lost on Max 7.0" in r7.message

    def _wrapped(self, text: str, inner: dict) -> dict:
        return _patch({"boxes": [{"box": {
            "id": "obj-9", "maxclass": "newobj", "text": text,
            "numinlets": 1, "numoutlets": 1, "outlettype": [""],
            "patching_rect": [10, 10, 80, 22], "patcher": inner}}], "lines": []})

    def test_nested_max_subpatcher_carries_its_path(self, real_db: ObjectDatabase) -> None:
        inner = dict(_mousestate_scope(), rect=[0, 0, 400, 300])
        found = _version(validate_patch(self._wrapped("p sub", inner), db=real_db,
                                        target_version="9.0"))
        assert len(found) == 1
        assert found[0].path == "obj-9"
        assert "mousestate" in found[0].message

    @pytest.mark.parametrize("text,namespace", [("rnbo~", "rnbo"), ("gen~", "dsp.gen")])
    def test_rnbo_and_gen_scopes_are_skipped(self, real_db, text, namespace) -> None:
        inner = dict(_mousestate_scope(), rect=[0, 0, 400, 300], classnamespace=namespace)
        found = _version(validate_patch(self._wrapped(text, inner), db=real_db,
                                        target_version="9.0"))
        assert found == []

    def test_change_newer_than_installed_is_ignored(self, real_db: ObjectDatabase) -> None:
        patch = _patch({"boxes": [
            {"box": {"id": "obj-1", "maxclass": "newobj", "text": "metro 100",
                     "numinlets": 2, "numoutlets": 1, "outlettype": ["bang"],
                     "patching_rect": [10, 10, 80, 22]}},
            {"box": {"id": "obj-2", "maxclass": "newobj", "text": "print",
                     "numinlets": 1, "numoutlets": 0, "patching_rect": [10, 60, 40, 22]}},
        ], "lines": [
            {"patchline": {"source": ["obj-1", 0], "destination": ["obj-2", 0]}},
            {"patchline": {"source": ["obj-2", 0], "destination": ["obj-1", 1]}},
        ]})
        assert _version(validate_patch(patch, db=real_db, target_version="9.0")) == []

    def test_unparsable_target_raises(self, real_db: ObjectDatabase) -> None:
        with pytest.raises(ValueError):
            validate_patch(_patch(_mousestate_scope()), db=real_db, target_version="nine")

    def test_default_path_is_unchanged(self, real_db: ObjectDatabase) -> None:
        paths = sorted(REPO_ROOT.glob("patches/*/generated/*.maxpat"))[:3]
        assert len(paths) == 3

        def key(results):
            return [(r.layer, r.level, r.message, r.path, r.proposed_removal) for r in results]

        for path in paths:
            data = json.loads(path.read_text())
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                plain = key(validate_patch(copy.deepcopy(data), db=real_db))
                explicit = key(validate_patch(copy.deepcopy(data), db=real_db, target_version=None))
            assert plain == explicit, path


# ── Live bundle ───────────────────────────────────────────────────


@pytest.mark.requires_max
def test_committed_version_io_is_current() -> None:
    section = sync.run_report(REAL_DB, MAX_APP_PATH)["sections"]["version_io"]
    assert section["available"] is True
    assert (section["added"], section["removed"], section["changed"]) == (0, 0, 0)


@pytest.mark.requires_max
def test_vst_and_retune_have_one_io_in_the_bundle(real_db: ObjectDatabase) -> None:
    committed = json.loads((REAL_DB / "version_io.json").read_text())["objects"]
    scan = help_io.scan_version_io(MAX_APP_PATH, real_db)
    for name in ("vst~", "retune~"):
        assert name not in committed
        assert name not in scan["conflicting"]
        assert name not in scan["ambiguous_names"]
