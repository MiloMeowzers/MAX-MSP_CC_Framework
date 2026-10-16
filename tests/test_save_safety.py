"""Save-path safety regression tests (quick 261012-m87, fix-plan Q5).

Covers review findings:
- A5: auto-commit committed the whole git index (no pathspec), ignored git
  return codes, swallowed every failure, and returned nothing.
- A6: save_patch_roundtrip never re-read the file, so a MAX save made between
  read_patch and the agent's save was silently overwritten (lost update).

Every git operation here runs inside a throwaway repo under pytest's
``tmp_path``, never in the MAX repo. The code under test finds the repo from
the saved file's own directory, and an autouse fixture strips GIT_DIR,
GIT_WORK_TREE and GIT_INDEX_FILE from the environment as a guard.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import warnings
from pathlib import Path

import pytest

from src.maxpat.patcher import Patcher

pytestmark = pytest.mark.skipif(
    shutil.which("git") is None, reason="git is not installed"
)


# ---------------------------------------------------------------------------
# Fixtures and helpers
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
    _git(root, "config", "user.name", "Save Safety Test")
    _git(root, "config", "commit.gpgsign", "false")
    _git(root, "config", "core.hooksPath", str(hooks))
    return root.resolve()


def _staged(root: Path) -> list[str]:
    return [l for l in _git(root, "diff", "--cached", "--name-only").splitlines() if l]


def _head_files(root: Path) -> list[str]:
    return [l for l in _git(root, "show", "--name-only", "--format=", "HEAD").splitlines() if l]


def _head(root: Path) -> str:
    return _git(root, "rev-parse", "HEAD").strip()


def _has_head(root: Path) -> bool:
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "-q", "HEAD"],
        cwd=str(root),
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def _prestage(root: Path, name: str = "other.txt", text: str = "someone else's work\n") -> None:
    """Write and stage an unrelated file, as another instance would."""
    (root / name).write_text(text)
    _git(root, "add", "--", name)


def _minimal_patch(extra: bool = False) -> dict:
    p = Patcher()
    p.add_box("cycle~", ["440"])
    if extra:
        p.add_box("*~", ["0.5"])
    return p.to_dict()


def _patch_path(root: Path) -> Path:
    return root / "patches" / "demo" / "generated" / "demo.maxpat"


REL_P = "patches/demo/generated/demo.maxpat"


# ---------------------------------------------------------------------------
# Task 1 (A5): path-scoped auto-commit
# ---------------------------------------------------------------------------


class TestPathScopedCommit:
    """save_patch_roundtrip -> _auto_commit_saved_file -> auto_commit_patch."""

    def test_prestaged_file_not_swept_into_first_commit(self, tmp_path):
        from src.maxpat.hooks import save_patch_roundtrip

        root = _repo(tmp_path)
        _prestage(root)
        P = _patch_path(root)

        with warnings.catch_warnings():
            warnings.simplefilter("error")
            result = save_patch_roundtrip(_minimal_patch(), P)

        assert result == _head(root)
        assert len(result) == 40
        assert _head_files(root) == [REL_P]
        assert _staged(root) == ["other.txt"]

    def test_prestaged_file_not_swept_into_second_commit(self, tmp_path):
        from src.maxpat.hooks import save_patch_roundtrip

        root = _repo(tmp_path)
        P = _patch_path(root)
        first = save_patch_roundtrip(_minimal_patch(), P)
        assert first == _head(root)

        _prestage(root)
        second = save_patch_roundtrip(_minimal_patch(extra=True), P)

        assert second == _head(root)
        assert second != first
        assert _head_files(root) == [REL_P]
        assert _staged(root) == ["other.txt"]

    def test_noop_save_makes_no_commit_and_keeps_other_staged(self, tmp_path):
        """The review's repro: a no-op save committed only someone's wip file."""
        from src.maxpat.hooks import save_patch_roundtrip

        root = _repo(tmp_path)
        P = _patch_path(root)
        d = _minimal_patch()
        save_patch_roundtrip(d, P)
        head_before = _head(root)

        _prestage(root, "wip.txt")
        with pytest.warns(UserWarning, match="no changes to commit"):
            result = save_patch_roundtrip(d, P)

        assert result is None
        assert _head(root) == head_before
        assert _staged(root) == ["wip.txt"]


class TestAutoCommitDirect:
    """auto_commit_patch called directly."""

    def test_returns_full_hash_and_commits_only_listed_path(self, tmp_path):
        from src.maxpat.project import auto_commit_patch

        root = _repo(tmp_path)
        _prestage(root)
        P = _patch_path(root)
        P.parent.mkdir(parents=True)
        P.write_text("{}\n")

        result = auto_commit_patch(
            root / "patches" / "demo", root, "save demo.maxpat", files=[str(P)]
        )

        assert result == _head(root)
        assert len(result) == 40
        assert _head_files(root) == [REL_P]
        assert _staged(root) == ["other.txt"]
        msg = _git(root, "log", "-1", "--format=%s").strip()
        assert msg == "patch(demo): save demo.maxpat"

    def test_relative_file_resolves_against_base_dir(self, tmp_path):
        """Pytest's cwd is the MAX repo; a relative entry must resolve against base_dir."""
        from src.maxpat.project import auto_commit_patch

        root = _repo(tmp_path)
        P = _patch_path(root)
        P.parent.mkdir(parents=True)
        P.write_text("{}\n")

        result = auto_commit_patch(root / "patches" / "demo", root, "rel", files=[REL_P])

        assert result == _head(root)
        assert _head_files(root) == [REL_P]

    def test_files_none_commits_project_dir_only(self, tmp_path):
        from src.maxpat.project import auto_commit_patch

        root = _repo(tmp_path)
        a = root / "patches" / "demo" / "a.maxpat"
        b = root / "patches" / "other" / "b.maxpat"
        a.parent.mkdir(parents=True)
        b.parent.mkdir(parents=True)
        a.write_text("{}\n")
        b.write_text("{}\n")

        result = auto_commit_patch(root / "patches" / "demo", root)

        assert result == _head(root)
        assert _head_files(root) == ["patches/demo/a.maxpat"]
        assert _git(root, "log", "-1", "--format=%s").strip() == "patch(demo): auto-save"
        untracked = _git(root, "ls-files", "--others", "--exclude-standard").splitlines()
        assert "patches/other/b.maxpat" in untracked

    def test_glob_characters_are_literal(self, tmp_path):
        """`a[1].maxpat` as a glob would also match `a1.maxpat`."""
        from src.maxpat.project import auto_commit_patch

        root = _repo(tmp_path)
        demo = root / "patches" / "demo"
        demo.mkdir(parents=True)
        a1 = demo / "a1.maxpat"
        a1.write_text("{}\n")
        _git(root, "add", "--", "patches/demo/a1.maxpat")
        _git(root, "commit", "-q", "-m", "seed")
        a1.write_text('{"changed": 1}\n')
        _git(root, "add", "--", "patches/demo/a1.maxpat")

        bracket = demo / "a[1].maxpat"
        bracket.write_text("{}\n")
        result = auto_commit_patch(demo, root, "save a[1].maxpat", files=[str(bracket)])

        assert result == _head(root)
        assert _head_files(root) == ["patches/demo/a[1].maxpat"]
        assert _staged(root) == ["patches/demo/a1.maxpat"]

    def test_git_add_failure_raises(self, tmp_path):
        from src.maxpat.project import auto_commit_patch

        root = _repo(tmp_path)
        (root / ".gitignore").write_text("ignored/\n")
        f = root / "patches" / "demo" / "ignored" / "x.js"
        f.parent.mkdir(parents=True)
        f.write_text("inlets = 1;\n")

        with pytest.raises(RuntimeError, match="git add failed"):
            auto_commit_patch(root / "patches" / "demo", root, "x", files=[str(f)])
        assert not _has_head(root)

    def test_not_a_repo_raises(self, tmp_path):
        from src.maxpat.project import auto_commit_patch

        plain = tmp_path / "plain"
        (plain / "patches" / "demo").mkdir(parents=True)
        f = plain / "patches" / "demo" / "x.maxpat"
        f.write_text("{}\n")

        with pytest.raises(RuntimeError, match="rev-parse"):
            auto_commit_patch(plain / "patches" / "demo", plain, "x", files=[str(f)])


class TestAutoCommitWarnings:
    """Every non-commit outcome warns with its reason (through save_patch_roundtrip)."""

    def test_outside_patches_warns(self, tmp_path):
        from src.maxpat.hooks import save_patch_roundtrip

        root = _repo(tmp_path)
        f = root / "notes" / "x.maxpat"
        with pytest.warns(UserWarning, match=r"outside patches/.*not auto-committed"):
            result = save_patch_roundtrip(_minimal_patch(), f)

        assert result is None
        assert not _has_head(root)
        assert f.exists()

    def test_not_a_repo_warns(self, tmp_path):
        from src.maxpat.hooks import save_patch_roundtrip

        f = tmp_path / "plain" / "x.maxpat"
        with pytest.warns(UserWarning, match="not inside a git repository"):
            result = save_patch_roundtrip(_minimal_patch(), f)

        assert result is None
        assert f.exists()

    def test_git_failure_warns(self, tmp_path):
        from src.maxpat.hooks import save_patch_roundtrip

        root = _repo(tmp_path)
        (root / ".gitignore").write_text("ignored/\n")
        f = root / "patches" / "demo" / "ignored" / "x.maxpat"
        with pytest.warns(UserWarning, match=r"auto-commit failed.*git add failed"):
            result = save_patch_roundtrip(_minimal_patch(), f)

        assert result is None
        assert not _has_head(root)
        assert f.exists()


# ---------------------------------------------------------------------------
# Task 2 (A6): stale-file check; write helpers expose the commit hash (OQ1-A)
# ---------------------------------------------------------------------------


def _saved_and_read(root: Path):
    """Save P once (committed), read it back, and add one box to the patcher."""
    from src.maxpat.hooks import read_patch, save_patch_roundtrip

    P = _patch_path(root)
    save_patch_roundtrip(_minimal_patch(), P)
    patcher, T = read_patch(P)
    patcher.add_box("*~", ["0.5"])
    return P, patcher, T


def _simulate_max_save(P: Path, T: str) -> str:
    """Write T2 = T with one box's patching_rect x moved, as a MAX save would."""
    data = json.loads(T)
    rect = data["patcher"]["boxes"][0]["box"]["patching_rect"]
    rect[0] = rect[0] + 37.0
    T2 = json.dumps(data, indent=4, ensure_ascii=False)
    assert T2 != T
    P.write_text(T2)
    return T2


class TestStaleFile:
    def test_stale_file_raises_without_writing(self, tmp_path):
        from src.maxpat.hooks import save_patch_roundtrip, StaleFileError

        root = _repo(tmp_path)
        P, patcher, T = _saved_and_read(root)
        head_before = _head(root)
        T2 = _simulate_max_save(P, T)

        with pytest.raises(StaleFileError) as excinfo:
            save_patch_roundtrip(patcher.to_dict(), P, T)

        msg = str(excinfo.value)
        assert "changed in MAX since it was read" in msg
        assert "re-read" in msg
        assert "force=True" in msg
        assert excinfo.value.path == P
        assert P.read_text() == T2
        assert _head(root) == head_before

    def test_force_overwrites_with_warning(self, tmp_path):
        from src.maxpat.hooks import format_patch_text, save_patch_roundtrip

        root = _repo(tmp_path)
        P, patcher, T = _saved_and_read(root)
        _simulate_max_save(P, T)
        _prestage(root)
        new_dict = patcher.to_dict()

        with pytest.warns(UserWarning, match="force=True"):
            result = save_patch_roundtrip(new_dict, P, T, force=True)

        expected = format_patch_text(new_dict, T)
        assert P.read_text() == expected
        assert result == _head(root)
        assert _head_files(root) == [REL_P]
        assert _staged(root) == ["other.txt"]

    def test_unchanged_file_saves_normally(self, tmp_path):
        from src.maxpat.hooks import save_patch_roundtrip

        root = _repo(tmp_path)
        P, patcher, T = _saved_and_read(root)

        with warnings.catch_warnings():
            warnings.simplefilter("error")
            result = save_patch_roundtrip(patcher.to_dict(), P, T)

        assert result == _head(root)
        assert _head_files(root) == [REL_P]

    def test_missing_target_is_never_stale(self, tmp_path):
        from src.maxpat.hooks import save_patch_roundtrip

        root = _repo(tmp_path)
        P, patcher, T = _saved_and_read(root)
        new_path = P.parent / "copy.maxpat"
        assert not new_path.exists()

        result = save_patch_roundtrip(patcher.to_dict(), new_path, T)

        assert new_path.exists()
        assert result == _head(root)
        assert _head_files(root) == ["patches/demo/generated/copy.maxpat"]

    def test_stale_file_error_exported(self):
        from src.maxpat import StaleFileError
        from src.maxpat.hooks import StaleFileError as HooksStaleFileError

        assert StaleFileError is HooksStaleFileError
        assert issubclass(StaleFileError, Exception)


class TestWriteHelpersCommit:
    """OQ1-A: write_gendsp/write_js keep their return values and add commit_hash."""

    def test_write_gendsp_commit_hash(self, tmp_path):
        from src.maxpat.hooks import write_gendsp

        root = _repo(tmp_path)
        _prestage(root)
        x = root / "patches" / "demo" / "generated" / "x.gendsp"

        result = write_gendsp("out1 = in1 * 0.5;", x, num_inputs=1, num_outputs=1)

        assert isinstance(result, dict)
        assert "patcher" in result
        assert json.loads(x.read_text()) == dict(result)
        assert result.commit_hash == _head(root)
        assert _head_files(root) == ["patches/demo/generated/x.gendsp"]
        assert _staged(root) == ["other.txt"]

    def test_write_js_commit_hash(self, tmp_path):
        from src.maxpat.hooks import write_js
        from src.maxpat.validation import ValidationResult

        root = _repo(tmp_path)
        x = root / "patches" / "demo" / "generated" / "x.js"
        code = 'inlets = 1;\noutlets = 1;\nfunction bang() { outlet(0, "bang"); }\n'

        result = write_js(code, x)

        assert isinstance(result, list)
        assert all(isinstance(r, ValidationResult) for r in result)
        assert result.commit_hash == _head(root)
        assert _head_files(root) == ["patches/demo/generated/x.js"]

    def test_write_gendsp_outside_repo_warns(self, tmp_path):
        from src.maxpat.hooks import write_gendsp

        y = tmp_path / "plain" / "y.gendsp"
        with pytest.warns(UserWarning, match="not inside a git repository"):
            result = write_gendsp("out1 = in1 * 0.5;", y, num_inputs=1, num_outputs=1)

        assert result.commit_hash is None
        assert y.exists()
