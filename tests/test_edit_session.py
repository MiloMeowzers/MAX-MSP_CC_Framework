"""edit_patch session tests (quick 261022-i07, fix-plan Q36).

Every git operation here runs inside a throwaway repo under pytest's
``tmp_path``, never in the MAX repo; an autouse fixture strips GIT_DIR,
GIT_WORK_TREE and GIT_INDEX_FILE from the environment as a guard. Committed
patches under ``patches/`` are only read (``git show HEAD:``) and copied to
tmp_path, never written.
"""

from __future__ import annotations

import ast
import functools
import json
import shutil
import subprocess
import warnings
from pathlib import Path

import pytest

from src.maxpat.patcher import Patcher
from src.maxpat.hooks import (
    PatchValidationError,
    SaveGateWarning,
    StaleFileError,
    save_patch_roundtrip,
)
from src.maxpat.edit_session import edit_patch

pytestmark = [
    pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed"),
    # Saves to tmp_path outside a repository: the auto-commit warns.
    pytest.mark.filterwarnings("ignore:.*not auto-committed:UserWarning"),
]

REPO_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Fixtures and helpers (copied from tests/test_save_gate.py, not imported)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolate_git_env(monkeypatch):
    """Make sure no inherited git env var can redirect git to another repo."""
    for var in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        monkeypatch.delenv(var, raising=False)


def _git(root: Path, *args: str) -> str:
    """Run git in *root* (check=True) and return stdout."""
    result = subprocess.run(
        ["git", *args],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def _repo(tmp_path: Path) -> Path:
    """Create a throwaway git repo at tmp_path/repo and return its resolved root."""
    root = tmp_path / "repo"
    root.mkdir()
    hooks = tmp_path / "empty-hooks"
    hooks.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Edit Session Test")
    _git(root, "config", "commit.gpgsign", "false")
    _git(root, "config", "core.hooksPath", str(hooks))
    return root.resolve()


def _staged(root: Path) -> list[str]:
    return [l for l in _git(root, "diff", "--cached", "--name-only").splitlines() if l]


def _head_files(root: Path) -> list[str]:
    return [l for l in _git(root, "show", "--name-only", "--format=", "HEAD").splitlines() if l]


def _head(root: Path) -> str:
    return _git(root, "rev-parse", "HEAD").strip()


def _patch_path(root: Path) -> Path:
    return root / "patches" / "demo" / "generated" / "demo.maxpat"


REL_P = "patches/demo/generated/demo.maxpat"


def _fan() -> dict:
    """FAN: number -> + 0 inlet 0, + -> print (clean). Ids obj-1..obj-3."""
    p = Patcher()
    n = p.add_box("number")
    a = p.add_box("+", ["0"])
    pr = p.add_box("print")
    p.add_connection(n, 0, a, 0)
    p.add_connection(a, 0, pr, 0)
    return p.to_dict()


def _seed(root: Path, P: Path, d: dict) -> str:
    """Write d directly to P and commit it (bypasses the gate). Returns the text."""
    text = json.dumps(d, indent=4)
    P.parent.mkdir(parents=True, exist_ok=True)
    P.write_text(text)
    rel = P.relative_to(root).as_posix()
    _git(root, "add", "--", rel)
    _git(root, "commit", "-q", "-m", "seed", "--", rel)
    return text


def _box_by_id(p: Patcher, box_id: str):
    for b in p.boxes:
        if b.id == box_id:
            return b
    raise KeyError(box_id)


def _sub() -> dict:
    """SUB: top-level p ctl (obj-1; inner inlets obj-1 x50, obj-2 x130,
    outlet obj-3, inner cord obj-1:0 -> obj-3:0), number (obj-2) -> p ctl
    inlet 0, p ctl outlet 0 -> print (obj-3)."""
    p = Patcher()
    box, inner = p.add_subpatcher("ctl", inlets=2, outlets=1)
    inner.add_connection(inner.get_inlets()[0], 0, inner.get_outlets()[0], 0)
    n = p.add_box("number")
    pr = p.add_box("print")
    p.add_connection(n, 0, box, 0)
    p.add_connection(box, 0, pr, 0)
    return p.to_dict()


def _ctl_box(d: dict) -> dict:
    for entry in d["patcher"]["boxes"]:
        if entry["box"].get("text") == "p ctl":
            return entry["box"]
    raise KeyError("p ctl")


def _inner_box(patcher: dict, box_id: str) -> dict:
    for entry in patcher["boxes"]:
        if entry["box"]["id"] == box_id:
            return entry["box"]
    raise KeyError(box_id)


def _gate_warnings(record) -> list:
    return [w for w in record if issubclass(w.category, SaveGateWarning)]


# Committed patches: read through git show HEAD:, copied to tmp_path ----------


def _tracked() -> list:
    try:
        out = subprocess.run(
            ["git", "ls-files", "-z", "--", "patches/*.maxpat"],
            cwd=str(REPO_ROOT), capture_output=True, check=True,
        ).stdout
        return sorted(p for p in out.decode("utf-8").split("\0") if p)
    except Exception:
        return []


TRACKED = _tracked()
JI = "patches/ji-harmonizer/generated/ji-harmonizer.maxpat"


@functools.lru_cache(maxsize=None)
def _head_bytes(rel: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"HEAD:{rel}"],
        cwd=str(REPO_ROOT), capture_output=True, check=True,
    ).stdout


def _copy_committed(rel: str, tmp_path: Path) -> Path:
    dest = tmp_path / Path(rel).name
    dest.write_bytes(_head_bytes(rel))
    return dest


def _no_save(monkeypatch) -> None:
    def _boom(*a, **k):
        raise AssertionError("must not save or write")

    monkeypatch.setattr("src.maxpat.hooks.save_patch_roundtrip", _boom)
    monkeypatch.setattr("src.maxpat.hooks._write_and_sync", _boom)


def _top_boxes(d: dict) -> dict:
    return {e["box"]["id"]: e["box"] for e in d["patcher"]["boxes"]}


def _cord_map(d: dict) -> dict:
    out = {}
    for e in d["patcher"]["lines"]:
        pl = e["patchline"]
        key = (pl["source"][0], pl["source"][1], pl["destination"][0], pl["destination"][1])
        out.setdefault(key, pl)
    return out


# ---------------------------------------------------------------------------
# Tracer: commit scope, no-op, discard
# ---------------------------------------------------------------------------


def test_edit_commits_only_that_path(tmp_path):
    root = _repo(tmp_path)
    P = _patch_path(root)
    save_patch_roundtrip(_fan(), P)
    notes = root / "patches" / "demo" / "notes.txt"
    notes.write_text("unrelated\n")
    _git(root, "add", "--", "patches/demo/notes.txt")

    s = edit_patch(P)
    with s as p:
        num = p.add_box("number", x=300, y=40)
        pr = p.add_box("print", x=300, y=120)
        p.add_connection(num, 0, pr, 0)

    assert s.saved is True
    assert s.commit_hash == _head(root)
    assert _head_files(root) == [REL_P]
    assert _staged(root) == ["patches/demo/notes.txt"]
    assert len(s.diff.of("box_added")) == 2
    assert len(s.diff.of("cord_added")) == 1
    assert "+ cord" in s.diff.render()


def test_noop_session_in_repo(tmp_path):
    root = _repo(tmp_path)
    P = _patch_path(root)
    _seed(root, P, _fan())
    before = P.read_bytes()
    mtime = P.stat().st_mtime_ns
    head = _head(root)

    s = edit_patch(P)
    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")
        with s as p:
            pass

    assert P.read_bytes() == before
    assert P.stat().st_mtime_ns == mtime
    assert _head(root) == head
    assert [str(w.message) for w in record] == []
    assert s.saved is False
    assert s.commit_hash is None
    assert not s.diff
    assert s.diff.render() == "no changes"


def test_exception_in_body_discards(tmp_path, monkeypatch):
    P = tmp_path / "demo.maxpat"
    save_patch_roundtrip(_fan(), P)
    before = P.read_bytes()

    def _boom(*a, **k):
        raise AssertionError("must not save")

    monkeypatch.setattr("src.maxpat.hooks.save_patch_roundtrip", _boom)
    monkeypatch.setattr("src.maxpat.hooks._write_and_sync", _boom)

    s = edit_patch(P)
    with pytest.raises(ValueError):
        with s as p:
            p.add_box("print")
            raise ValueError("abort edit")

    assert P.read_bytes() == before
    assert s.saved is False


# ---------------------------------------------------------------------------
# No-op over every committed patch (D-04)
# ---------------------------------------------------------------------------


def test_committed_list_not_empty():
    assert len(TRACKED) >= 60


@pytest.mark.parametrize("rel", TRACKED)
def test_noop_session_committed_copy(rel, tmp_path, monkeypatch):
    P = _copy_committed(rel, tmp_path)
    before = P.read_bytes()
    mtime = P.stat().st_mtime_ns
    _no_save(monkeypatch)

    s = edit_patch(P)
    with s:
        pass

    assert P.read_bytes() == before
    assert P.stat().st_mtime_ns == mtime
    assert s.saved is False
    assert s.commit_hash is None
    assert not s.diff, s.diff.render()


# ---------------------------------------------------------------------------
# Refusals (D-01) and force (D-08)
# ---------------------------------------------------------------------------


def test_stale_refused(tmp_path):
    P = tmp_path / "demo.maxpat"
    save_patch_roundtrip(_fan(), P)

    s = edit_patch(P)
    with pytest.raises(StaleFileError):
        with s as p:
            data = json.loads(P.read_text())
            data["patcher"]["boxes"][0]["box"]["patching_rect"][0] += 15
            external = json.dumps(data, indent=4)
            P.write_text(external)  # a MAX save between enter and exit
            p.add_box("print", x=300, y=200)

    assert P.read_text() == external
    assert s.saved is False
    assert len(s.diff.of("box_added")) == 1
    assert s.patcher is p


def test_new_blocker_refused(tmp_path):
    root = _repo(tmp_path)
    P = _patch_path(root)
    _seed(root, P, _fan())
    before = P.read_bytes()
    head = _head(root)

    s = edit_patch(P)
    with pytest.raises(PatchValidationError):
        with s as p:
            p.add_connection(_box_by_id(p, "obj-1"), 0, _box_by_id(p, "obj-2"), 1)

    assert P.read_bytes() == before
    assert _head(root) == head
    assert s.saved is False
    assert len(s.diff.of("cord_added")) == 1


def test_force_passthrough(tmp_path):
    root = _repo(tmp_path)
    P = _patch_path(root)
    _seed(root, P, _fan())

    s = edit_patch(P, force=True)
    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")
        with s as p:
            p.add_connection(_box_by_id(p, "obj-1"), 0, _box_by_id(p, "obj-2"), 1)

    assert s.saved is True
    assert s.commit_hash == _head(root)
    assert _gate_warnings(record)


def test_port_xrank_refused(tmp_path):
    root = _repo(tmp_path)
    P = _patch_path(root)
    _seed(root, P, _sub())
    before = P.read_bytes()
    head = _head(root)
    ctl_id = _ctl_box(json.loads(before))["id"]

    s = edit_patch(P)
    with pytest.raises(PatchValidationError) as excinfo:
        with s as p:
            inner = _box_by_id(p, ctl_id)._inner_patcher
            a, b = inner.get_inlets()[:2]
            a.patching_rect[0], b.patching_rect[0] = b.patching_rect[0], a.patching_rect[0]

    assert excinfo.value.port_changes
    assert P.read_bytes() == before
    assert _head(root) == head
    moved = s.diff.of("moved")
    assert {e.path for e in moved} == {(ctl_id,)}


def test_removed_cord_warns_and_saves(tmp_path):
    root = _repo(tmp_path)
    P = _patch_path(root)
    _seed(root, P, _fan())

    s = edit_patch(P)
    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")
        with s as p:
            p.remove_connection(_box_by_id(p, "obj-1"), 0, _box_by_id(p, "obj-2"), 0)

    assert s.saved is True
    assert s.commit_hash == _head(root)
    assert len(_gate_warnings(record)) == 1
    assert len(s.diff.of("cord_removed")) == 1


# ---------------------------------------------------------------------------
# Exit scope (D-03): touched cords, touched contrast, no whole-patch passes
# ---------------------------------------------------------------------------


@pytest.mark.filterwarnings("ignore:add_box moved")
def test_touched_cords_only(tmp_path):
    P = _copy_committed(JI, tmp_path)
    base = json.loads(P.read_text())
    base_cords = _cord_map(base)
    routed = {k for k, pl in base_cords.items() if pl.get("midpoints")}

    s = edit_patch(P)
    with s as p:
        a = next(
            b for b in p.boxes
            if b.maxclass == "newobj" and b.outlettype
            and b.outlettype[0] not in ("signal", "multichannelsignal")
        )
        endpoints = {k[0] for k in routed} | {k[2] for k in routed}
        b = next(x for x in p.boxes if x.id in endpoints and x.id != a.id)
        pr = p.add_box("print", x=a.patching_rect[0] + 300, y=a.patching_rect[1] + 100)
        p.add_connection(a, 0, pr, 0)
        p.modify_box(b, position=[b.patching_rect[0] + 20, b.patching_rect[1]])
        a_id, b_id, pr_id = a.id, b.id, pr.id

    assert s.saved is True
    saved = _cord_map(json.loads(P.read_text()))
    for key in routed:
        assert saved[key]["midpoints"] == base_cords[key]["midpoints"], key
    for key, pl in base_cords.items():
        if key in routed or b_id in (key[0], key[2]):
            continue
        assert not saved[key].get("midpoints"), key
    assert saved[(a_id, 0, pr_id, 0)].get("midpoints")
    for e in s.diff.of("cord_rerouted"):
        src, dst = e.label.split(" -> ")
        assert b_id in (src.rsplit(":", 1)[0], dst.rsplit(":", 1)[0]), e.label


def test_contrast_touched_only(tmp_path):
    from src.maxpat.aesthetics import repair_text_contrast

    P = _copy_committed(JI, tmp_path)
    base = json.loads(P.read_text())
    assert repair_text_contrast(Patcher.from_dict(base)) > 3
    base_boxes = _top_boxes(base)
    assert "textcolor" not in base_boxes["obj-85"]
    assert "textcolor" not in base_boxes["obj-92"]

    s = edit_patch(P)
    with s as p:
        c = p.add_comment("touched", 2000, 2000)
        b92 = _box_by_id(p, "obj-92")
        p.modify_box(b92, position=[b92.patching_rect[0] + 10, b92.patching_rect[1]])
        p.add_to_presentation(_box_by_id(p, "obj-85"), [10, 10, 120, 20])
        new_id = c.id

    assert s.saved is True
    after = _top_boxes(json.loads(P.read_text()))
    touched = {new_id, "obj-92", "obj-85"}
    for box_id in touched:
        assert "textcolor" in after[box_id], box_id
    for box_id, box in base_boxes.items():
        if box_id in touched:
            continue
        assert ("textcolor" in after[box_id]) == ("textcolor" in box), box_id
        assert after[box_id].get("textcolor") == box.get("textcolor"), box_id


def test_apply_text_contrast_only_ids():
    from src.maxpat.aesthetics import _apply_text_contrast, repair_text_contrast

    d = json.loads(_head_bytes(JI))
    p = Patcher.from_dict(d)
    assert _apply_text_contrast(p, only_ids=set()) == 0
    assert not Patcher.from_dict(d).diff(p)

    assert _apply_text_contrast(p, only_ids={"obj-85"}) == 1
    diff = Patcher.from_dict(d).diff(p)
    assert [(e.kind, e.box_id) for e in diff] == [("attrs", "obj-85")]

    assert _apply_text_contrast(Patcher.from_dict(d)) == repair_text_contrast(Patcher.from_dict(d))


def test_session_exit_avoids_whole_patch_passes():
    forbidden = {
        "ensure_text_contrast", "repair_text_contrast", "finalize_patch",
        "apply_layout", "populate_assistance_comments",
    }
    src = (REPO_ROOT / "src" / "maxpat" / "edit_session.py").read_text()
    called = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Call):
            fn = node.func
            if isinstance(fn, ast.Name):
                called.add(fn.id)
            elif isinstance(fn, ast.Attribute):
                called.add(fn.attr)
    assert "_apply_text_contrast" in called
    assert not (called & forbidden), called & forbidden


# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------


def test_nested_entry_guard(tmp_path):
    P = tmp_path / "demo.maxpat"
    save_patch_roundtrip(_fan(), P)
    before = P.read_bytes()

    s = edit_patch(P)
    with pytest.raises(RuntimeError, match="already active"):
        with s:
            with s:
                pass
    assert P.read_bytes() == before
    assert s.saved is False


def test_reentry_rereads(tmp_path):
    P = tmp_path / "demo.maxpat"
    save_patch_roundtrip(_fan(), P)

    s = edit_patch(P)
    with s as p1:
        p1.add_box("print", x=300, y=200)
    assert s.saved is True

    with s as p2:
        pass
    assert p2 is not p1
    assert s.original_text == P.read_text()
    assert s.saved is False
    assert s.commit_hash is None


def test_current_diff_preview(tmp_path):
    P = tmp_path / "demo.maxpat"
    save_patch_roundtrip(_fan(), P)

    s = edit_patch(P)
    with pytest.raises(RuntimeError):
        s.current_diff()
    with s as p:
        p.add_box("print", x=300, y=200)
        assert len(s.current_diff().of("box_added")) == 1
    assert len(s.current_diff().of("box_added")) == 1


def test_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        with edit_patch(tmp_path / "nope.maxpat"):
            pass
