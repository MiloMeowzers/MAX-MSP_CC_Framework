"""edit_patch session tests (quick 261022-i07, fix-plan Q36).

Every git operation here runs inside a throwaway repo under pytest's
``tmp_path``, never in the MAX repo; an autouse fixture strips GIT_DIR,
GIT_WORK_TREE and GIT_INDEX_FILE from the environment as a guard. Committed
patches under ``patches/`` are only read (``git show HEAD:``) and copied to
tmp_path, never written.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import warnings
from pathlib import Path

import pytest

from src.maxpat.patcher import Patcher
from src.maxpat.hooks import save_patch_roundtrip
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
