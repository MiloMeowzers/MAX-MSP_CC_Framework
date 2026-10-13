"""Release-archive and CI regression tests (quick 261012-sam, fix-plan Q8).

Covers review findings:
- I2 / S10: the release tarball was built with ``tar`` + an unanchored
  ``.release-ignore``. It stripped ``.claude/scripts/``, nested a truncated copy
  of itself, shipped the tracked maintainer memory file, and masked tar's exit
  code. The release is now ``git archive`` of HEAD with anchored
  ``.gitattributes`` export-ignore rules, built by ``scripts/build_release.sh``
  -- the same script release.yml runs.

The only git command these tests run against the checkout is the read-only
``git archive`` inside ``scripts/build_release.sh``, writing into pytest's
``tmp_path``. The archive is built from HEAD, so archive assertions reflect
committed state, not the working tree.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PREFIX = "MAX-MSP_CC_Framework"
SCRIPT = REPO_ROOT / "scripts" / "build_release.sh"
GITATTRIBUTES = REPO_ROOT / ".gitattributes"

# Trees that must never ship (S2), relative to the archive prefix.
EXCLUDED_TREES = (
    "tests",
    "patches",
    ".planning",
    ".github",
    "scripts",
    "installer",
    ".claude/projects",
)
# Anchored export-ignore patterns .gitattributes must carry (S2).
EXPORT_IGNORE_PATTERNS = tuple("/" + t for t in EXCLUDED_TREES) + ("/.gitattributes",)
AUDIT_DIR = ".claude/max-objects/audit"
WIDTH_TABLE = AUDIT_DIR + "/width-overrides.json"  # OQ1-A: the only audit file shipped
RUNTIME_FILES = (
    ".claude/scripts/extract_objects.py",
    "CLAUDE.md",
    "src/maxpat/__init__.py",
    ".claude/max-objects/max/objects.json",
    "tools/sync_max_bundle.py",
    WIDTH_TABLE,
)
ARCHIVE_SUFFIXES = (".tar.gz", ".tgz", ".tar", ".zip")


def _git_worktree_ok() -> bool:
    if shutil.which("git") is None or shutil.which("bash") is None:
        return False
    r = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        env=_clean_env(),
    )
    return r.returncode == 0 and r.stdout.strip() == "true"


def _clean_env() -> dict[str, str]:
    """Environment without git redirection variables or PYTHONPATH."""
    env = dict(os.environ)
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "PYTHONPATH"):
        env.pop(key, None)
    return env


requires_git = pytest.mark.skipif(
    not _git_worktree_ok(),
    reason="git and bash with a git checkout are required",
)


def _run_script(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        env=_clean_env(),
        timeout=300,
    )


def _run_in_archive(root: Path, code: str) -> dict:
    """Run ``code`` in a fresh interpreter rooted at the extracted archive.

    ``code`` must print one JSON object on its last stdout line.
    """
    r = subprocess.run(
        [sys.executable, "-c", code, str(root)],
        cwd=str(root),
        capture_output=True,
        text=True,
        env=_clean_env(),
        timeout=300,
    )
    assert r.returncode == 0, f"subprocess failed:\n{r.stdout}\n{r.stderr}"
    lines = [ln for ln in r.stdout.splitlines() if ln.strip()]
    assert lines, f"no output:\n{r.stderr}"
    return json.loads(lines[-1])


@pytest.fixture(scope="module")
def release_archive(tmp_path_factory):
    """Build the release exactly as release.yml does, validate and extract it."""
    if not _git_worktree_ok():
        pytest.skip("git and bash with a git checkout are required")
    tmp = tmp_path_factory.mktemp("release")
    out = tmp / "framework.tar.gz"
    r = _run_script(str(out))
    if r.returncode != 0:
        pytest.fail(f"build_release.sh failed ({r.returncode}):\n{r.stderr}")
    dest = tmp / "extract"
    dest.mkdir()
    rels: set[str] = set()
    with tarfile.open(out, "r:gz") as tf:
        members = tf.getmembers()
        for m in members:
            name = m.name.rstrip("/")
            assert name == PREFIX or name.startswith(PREFIX + "/"), m.name
            assert not name.startswith("/"), m.name
            assert ".." not in Path(name).parts, m.name
            assert m.isfile() or m.isdir(), f"{m.name}: not a regular file or dir"
            if name != PREFIX:
                rels.add(name[len(PREFIX) + 1:])
        if hasattr(tarfile, "data_filter"):
            tf.extractall(dest, filter="data")
        else:  # pragma: no cover - Python without extraction filters
            tf.extractall(dest)
    root = dest / PREFIX
    assert root.is_dir()
    yield rels, root, out


@pytest.mark.slow
class TestReleaseArchive:
    """I2: the archive built by scripts/build_release.sh has the right contents."""

    def test_runtime_files_ship(self, release_archive):
        rels, root, _ = release_archive
        missing = [f for f in RUNTIME_FILES if f not in rels]
        assert not missing, f"runtime files missing from the release: {missing}"
        for f in RUNTIME_FILES:
            assert (root / f).is_file(), f

    def test_maintainer_trees_excluded(self, release_archive):
        rels, _, _ = release_archive
        leaked = sorted(
            r for r in rels for x in EXCLUDED_TREES if r == x or r.startswith(x + "/")
        )
        assert not leaked, f"maintainer trees shipped: {leaked[:20]}"
        assert ".gitattributes" not in rels
        audit_extra = sorted(
            r
            for r in rels
            if r.startswith(AUDIT_DIR + "/") and r != WIDTH_TABLE
        )
        assert not audit_extra, f"audit reports shipped: {audit_extra}"

    def test_no_nested_archive(self, release_archive):
        rels, _, _ = release_archive
        nested = sorted(r for r in rels if r.endswith(ARCHIVE_SUFFIXES))
        assert not nested, f"nested archives: {nested}"

    def test_every_src_module_imports_from_archive(self, release_archive):
        rels, root, _ = release_archive
        code = r"""
import importlib, json, pkgutil, sys
root = sys.argv[1]
sys.path.insert(0, root)
errors, files = {}, {}
import src
def onerror(name):
    errors[name] = repr(sys.exc_info()[1])
names = [m.name for m in pkgutil.walk_packages(src.__path__, "src.", onerror=onerror)]
for name in names:
    try:
        mod = importlib.import_module(name)
        files[name] = getattr(mod, "__file__", None)
    except BaseException as exc:
        errors[name] = repr(exc)
cycle = None
widths = None
try:
    from src.maxpat.db_lookup import ObjectDatabase
    cycle = ObjectDatabase().lookup("cycle~") is not None
    import src.maxpat.sizing as sizing
    widths = len(sizing._WIDTH_OVERRIDES)
except BaseException as exc:
    errors["<checks>"] = repr(exc)
print(json.dumps({"names": names, "errors": errors, "files": files,
                  "cycle": cycle, "widths": widths}))
"""
        res = _run_in_archive(root, code)
        assert not res["errors"], res["errors"]
        root_res = root.resolve()
        for name, f in res["files"].items():
            assert f, f"{name} has no __file__"
            assert Path(f).resolve().is_relative_to(root_res), f"{name}: {f}"

        expected = set()
        for r in rels:
            if not (r.startswith("src/") and r.endswith(".py")):
                continue
            parts = r[: -len(".py")].split("/")
            if parts[-1] == "__init__":
                parts = parts[:-1]
            name = ".".join(parts)
            if name != "src":
                expected.add(name)
        assert set(res["names"]) == expected
        assert res["cycle"] is True, "ObjectDatabase in the archive cannot resolve cycle~"
        assert res["widths"] and res["widths"] > 0, "width-override table empty in the archive"

    def test_fresh_layout_has_no_active_project(self, release_archive):
        _, root, _ = release_archive
        code = r"""
import json, sys
from pathlib import Path
root = Path(sys.argv[1])
sys.path.insert(0, str(root))
from src.maxpat.project import get_active_project
first = get_active_project(root)
(root / "patches").mkdir(exist_ok=True)
second = get_active_project(root)
print(json.dumps({"first": first, "second": second}))
"""
        patches = root / "patches"
        assert not patches.exists(), "patches/ shipped in the release"
        res = _run_in_archive(root, code)
        assert res == {"first": None, "second": None}


class TestGitattributes:
    """I2: export-ignore patterns are anchored and cover the S2 exclusions."""

    def _rules(self) -> list[tuple[str, list[str]]]:
        assert GITATTRIBUTES.is_file(), ".gitattributes is missing"
        rules = []
        for line in GITATTRIBUTES.read_text().splitlines():
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            pattern, *attrs = s.split()
            rules.append((pattern, attrs))
        return rules

    def test_export_ignore_patterns_anchored(self):
        bad = [
            p
            for p, attrs in self._rules()
            if any(a in ("export-ignore", "-export-ignore") for a in attrs)
            and not p.startswith("/")
        ]
        assert not bad, f"unanchored export-ignore patterns: {bad}"

    def test_required_exclusions_present(self):
        ignored = {p for p, attrs in self._rules() if "export-ignore" in attrs}
        missing = [p for p in EXPORT_IGNORE_PATTERNS if p not in ignored]
        assert not missing, f"missing export-ignore patterns: {missing}"

    def test_claude_scripts_never_named(self):
        named = [p for p, _ in self._rules() if p.rstrip("/*").startswith("/.claude/scripts")]
        assert not named, named


@requires_git
class TestBuildScript:
    """I2: the build script fails loudly (no exit-code masking)."""

    def test_no_arguments_fails(self):
        assert SCRIPT.is_file(), "scripts/build_release.sh is missing"
        assert _run_script().returncode != 0

    def test_bad_treeish_fails(self, tmp_path):
        assert SCRIPT.is_file(), "scripts/build_release.sh is missing"
        r = _run_script(str(tmp_path / "out.tar.gz"), "no-such-ref-q8")
        assert r.returncode != 0, r.stdout
