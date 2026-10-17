"""Q32 removal guard: removed files and names stay removed, no tracked file
references them, kept paths keep their behaviour."""

import ast
import importlib
import importlib.util
import json
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


class TestRemovedPublicApi:
    @pytest.mark.parametrize(
        "module, name",
        [
            ("src.maxpat.project", "build_examples_catalog"),
            ("src.maxpat.project", "_read_project_description"),
            ("src.maxpat.aesthetics", "contrast_text_color"),
            ("src.maxpat.aesthetics", "is_complex_patch"),
            ("src.maxpat", "is_complex_patch"),
            ("src.maxpat.layout", "suggest_subpatchers"),
        ],
    )
    def test_removed_name_is_gone(self, module, name):
        assert not _has_attr(module, name)

    def test_package_all_names_exist(self):
        pkg = importlib.import_module("src.maxpat")
        missing = [n for n in pkg.__all__ if not hasattr(pkg, n)]
        assert missing == []

    def test_no_reference_names_removed_api(self):
        assert _references([
            r"\bbuild_examples_catalog\b",
            r"\b_read_project_description\b",
            r"\bcontrast_text_color\b",
            r"\bis_complex_patch\b",
            r"\bsuggest_subpatchers\b",
            r"\b_skip_auto_layout\b",
        ]) == []


def _try_nodes(tree) -> list:
    kinds = (ast.Try,) + ((ast.TryStar,) if hasattr(ast, "TryStar") else ())
    return [n for n in ast.walk(tree) if isinstance(n, kinds)]


class TestRemovedInternals:
    @pytest.mark.parametrize(
        "module, name",
        [
            ("src.maxpat.validation", "_check_genexpr_io_syntax"),
            ("src.maxpat.validation", "_check_genexpr_delay_usage"),
            ("src.maxpat.patcher", "Patcher.add_node_script"),
            ("src.maxpat.defaults", "MS_BAR_HEIGHT"),
            ("src.maxpat.defaults", "MS_LABEL_FONTSIZE"),
            ("src.maxpat.defaults", "MS_LABEL_HEIGHT"),
            ("src.maxpat.defaults", "MS_LABEL_WIDTH"),
            ("src.maxpat.defaults", "MS_GAP"),
            ("src.maxpat.audit", "run_audit"),
        ],
    )
    def test_removed_name_is_gone(self, module, name):
        assert not _has_attr(module, name)

    def test_overrides_drops_uncovered_empty_io(self):
        path = REPO_ROOT / ".claude" / "max-objects" / "overrides.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "_uncovered_empty_io" not in data

    @pytest.mark.parametrize(
        "rel, func",
        [
            ("src/maxpat/audit/__init__.py", None),
            ("src/maxpat/dsp_sim/topologies/__init__.py", None),
            ("src/maxpat/dsp_sim/runner.py", "_resolve_stepper_factory"),
        ],
    )
    def test_no_import_fallback(self, rel, func):
        tree = ast.parse((REPO_ROOT / rel).read_text(encoding="utf-8"))
        if func is not None:
            matches = [
                n for n in ast.walk(tree)
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                and n.name == func
            ]
            assert len(matches) == 1
            tree = matches[0]
        assert _try_nodes(tree) == []

    def test_no_reference_names_removed_internals(self):
        assert _references([
            r"\b_check_genexpr_io_syntax\b",
            r"\b_check_genexpr_delay_usage\b",
            r"\b_uncovered_empty_io\b",
            r"\brefresh_uncovered_only\b",
            r"\b32-02\b",
            r"\badd_node_script\b",
            r"\bMS_(BAR_HEIGHT|LABEL_FONTSIZE|LABEL_HEIGHT|LABEL_WIDTH|GAP)\b",
        ]) == []

    # Behaviour pins: green before and after the removals.

    def test_top_level_codebox_still_blocks(self):
        from src.maxpat.validation import has_blocking_errors, validate_patch

        patch = {"patcher": {"boxes": [{"box": {
            "id": "c1",
            "maxclass": "newobj",
            "text": "codebox",
            "numinlets": 1,
            "numoutlets": 1,
            "patching_rect": [0, 0, 100, 50],
            "code": "out1 = delay(in1, 10);",
        }}], "lines": []}}
        results = validate_patch(patch)
        assert has_blocking_errors(results)
        assert any("restricted to" in r.message for r in results)

    def test_node_script_box_from_add_box(self):
        from src.maxpat.patcher import Patcher

        box = Patcher().add_box("node.script", ["x.js"])
        assert box.maxclass == "newobj"
        assert box.text == "node.script x.js"
        assert box.numinlets == 1
        assert box.numoutlets == 2

    def test_topology_error_is_one_class(self):
        from src.maxpat.dsp_sim import runner, topologies

        assert topologies.TopologyError is runner.TopologyError
        with pytest.raises(runner.TopologyError):
            topologies.get_topology("nope")

    def test_audit_cli_imports(self):
        assert callable(importlib.import_module("src.maxpat.audit.cli").main)
