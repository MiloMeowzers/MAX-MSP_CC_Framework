"""Q32 removal guard: removed files and names stay removed, no tracked file
references them, kept paths keep their behaviour."""

import importlib
import importlib.util
import re
import subprocess
from functools import lru_cache
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

SCAN_ROOTS = (
    "src",
    "tests",
    "tools",
    "scripts",
    ".claude/scripts",
    ".claude/skills",
    ".claude/commands",
    "patterns",
    "installer",
    ".github",
    "CLAUDE.md",
    "README.md",
    "TECHNICAL.md",
    "install.sh",
)

_THIS_FILE = Path(__file__).resolve()


@lru_cache(maxsize=1)
def _tracked_text_files() -> tuple[Path, ...]:
    try:
        out = subprocess.run(
            ["git", "ls-files", "-z", "--", *SCAN_ROOTS],
            cwd=REPO_ROOT,
            capture_output=True,
            check=True,
        ).stdout.decode("utf-8")
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("git is unavailable")
    files = []
    for rel in out.split("\0"):
        if not rel:
            continue
        parts = Path(rel).parts
        if "node_modules" in parts or "__pycache__" in parts:
            continue
        path = REPO_ROOT / rel
        if path.resolve() == _THIS_FILE or not path.is_file():
            continue
        files.append(path)
    return tuple(files)


def _references(patterns: list[str]) -> list[str]:
    regexes = [re.compile(p) for p in patterns]
    hits = []
    for path in _tracked_text_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        for lineno, line in enumerate(text.splitlines(), 1):
            for rx in regexes:
                for m in rx.finditer(line):
                    rel = path.relative_to(REPO_ROOT).as_posix()
                    hits.append(f"{rel}:{lineno}: {m.group(0)}")
    return sorted(hits)


def _has_attr(module: str, dotted: str) -> bool:
    obj = importlib.import_module(module)
    for part in dotted.split("."):
        if not hasattr(obj, part):
            return False
        obj = getattr(obj, part)
    return True


REMOVED_PATHS = (
    "src/maxpat/memory.py",
    "tests/test_memory.py",
    "scripts/relayout_patch.py",
    ".claude/scripts/validate_db.py",
    ".claude/scripts/merge_sources.py",
    "tests/fixtures/expected/gen_codebox.maxpat",
    ".claude/max-objects/verified-objects.json",
)


class TestRemovedFilesAndModules:
    @pytest.mark.parametrize("rel", REMOVED_PATHS)
    def test_removed_path_is_gone(self, rel):
        assert not (REPO_ROOT / rel).exists()

    def test_memory_module_is_gone(self):
        assert importlib.util.find_spec("src.maxpat.memory") is None

    def test_no_reference_names_a_removed_file(self):
        assert _references([
            r"\bMemoryStore\b",
            r"\bMemoryEntry\b",
            r"max-memory",
            r"maxpat[./]memory\b",
            r"(?i)\bmemory (system|store|agent)\b",
            r"\brelayout_patch\b",
            r"\bvalidate_db\b",
            r"\bmerge_sources\b",
            r"gen_codebox\.maxpat",
            r"verified-objects\.json",
        ]) == []
