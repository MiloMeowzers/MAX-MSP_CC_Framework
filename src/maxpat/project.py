"""Project lifecycle management -- creation, tracking, status.

Each MAX project lives in its own directory under patches/ with independent
context, state, and generated files. This module handles:

- Project creation with full directory structure
- Active project tracking via .active-project.json
- Status read/write (stage, progress, created date)
- Project listing
"""

from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.maxpat.patcher import Box, Patcher

# Valid project name: lowercase alphanumeric + hyphens, no leading/trailing hyphen
_PROJECT_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

# Matches version comment text like "v0.1.0", "v1.2.3"
_VERSION_COMMENT_RE = re.compile(r"^v\d+\.\d+\.\d+$")


def create_project(name: str, base_dir: Path) -> Path:
    """Create a new project with full directory structure.

    Creates patches/{name}/ with:
    - context.md (empty template)
    - status.md (stage: ideation, progress: empty, created: ISO date)
    - generated/ (empty directory)
    - test-results/ (empty directory)

    Args:
        name: Project name (lowercase alphanumeric + hyphens only).
        base_dir: Root directory containing the patches/ folder.

    Returns:
        Path to the created project directory.

    Raises:
        ValueError: If name is invalid or project already exists.
    """
    if not _PROJECT_NAME_RE.match(name):
        raise ValueError(
            f"Invalid project name '{name}'. "
            "Must be lowercase alphanumeric with hyphens (e.g., 'my-synth')."
        )

    project_dir = base_dir / "patches" / name
    if project_dir.exists():
        raise ValueError(f"Project '{name}' already exists at {project_dir}")

    # Create directory tree
    project_dir.mkdir(parents=True)
    (project_dir / "generated").mkdir()
    (project_dir / "test-results").mkdir()

    # Initialize context.md
    (project_dir / "context.md").write_text(
        f"# {name}\n\nProject context and notes.\n"
    )

    # Initialize status.md
    now = datetime.now(timezone.utc).isoformat()
    status_content = (
        f"stage: ideation\n"
        f"progress: \n"
        f"created: {now}\n"
    )
    (project_dir / "status.md").write_text(status_content)

    # Create empty .maxpat so the user can open the project in MAX immediately
    from src.maxpat.patcher import Patcher as _Patcher
    from src.maxpat.aesthetics import set_canvas_background as _set_canvas_bg
    import json as _json

    empty_patcher = _Patcher()
    _set_canvas_bg(empty_patcher)
    patch_dict = empty_patcher.to_dict()
    maxpat_path = project_dir / "generated" / f"{name}.maxpat"
    maxpat_path.write_text(_json.dumps(patch_dict, indent=2) + "\n")

    # Initialize version tracking at 0.0.0
    init_versions(project_dir)

    return project_dir


def set_active_project(name: str, base_dir: Path) -> None:
    """Set the active project by writing .active-project.json.

    Args:
        name: Project name to activate.
        base_dir: Root directory containing the patches/ folder.
    """
    patches_dir = base_dir / "patches"
    patches_dir.mkdir(parents=True, exist_ok=True)

    active_file = patches_dir / ".active-project.json"
    data = {
        "name": name,
        "activated": datetime.now(timezone.utc).isoformat(),
    }
    active_file.write_text(json.dumps(data, indent=2) + "\n")


def get_active_project(base_dir: Path) -> dict | None:
    """Get the currently active project.

    Returns None if:
    - No .active-project.json exists
    - The referenced project directory doesn't exist (desync detection)

    Args:
        base_dir: Root directory containing the patches/ folder.

    Returns:
        Dict with 'name' and 'activated' keys, or None.
    """
    active_file = base_dir / "patches" / ".active-project.json"
    if not active_file.is_file():
        return None

    data = json.loads(active_file.read_text())
    project_dir = base_dir / "patches" / data["name"]
    if not project_dir.is_dir():
        return None

    return data


def read_status(project_dir: Path) -> dict:
    """Parse status.md and return dict with stage, progress, created fields.

    Args:
        project_dir: Path to the project directory.

    Returns:
        Dict with 'stage', 'progress', 'created' keys.
    """
    status_file = project_dir / "status.md"
    content = status_file.read_text()

    result = {}
    for line in content.strip().splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            result[key.strip()] = value.strip()

    return result


def update_status(project_dir: Path, **kwargs: str) -> None:
    """Update specific fields in status.md.

    Args:
        project_dir: Path to the project directory.
        **kwargs: Fields to update (e.g., stage="build", progress="50%").
    """
    current = read_status(project_dir)
    current.update(kwargs)

    lines = [f"{key}: {value}" for key, value in current.items()]
    (project_dir / "status.md").write_text("\n".join(lines) + "\n")


def load_project_config(project_dir: Path) -> dict | None:
    """Load config.json from project directory.

    Returns None if config.json does not exist (project not configured).
    """
    config_path = project_dir / "config.json"
    if not config_path.is_file():
        return None
    return json.loads(config_path.read_text())


def save_project_config(project_dir: Path, config: dict) -> None:
    """Write config.json to project directory."""
    config_path = project_dir / "config.json"
    config_path.write_text(json.dumps(config, indent=2) + "\n")


def get_allowed_packages(project_dir: Path) -> list[str] | None:
    """Get allowed packages from project config.

    Returns:
        List of package names if configured, None if no config exists.
        Empty list means core-only (explicitly configured with no packages).
    """
    config = load_project_config(project_dir)
    if config is None:
        return None
    return config.get("packages", [])


def init_versions(project_dir: Path) -> str:
    """Initialize versions.json with a 0.0.0 entry if it doesn't exist.

    Idempotent -- if versions.json already exists, returns the current version
    without modifying the file.

    Args:
        project_dir: Path to the project directory.

    Returns:
        Current version string (e.g., "0.0.0").
    """
    versions_file = project_dir / "versions.json"
    if versions_file.is_file():
        data = json.loads(versions_file.read_text())
        return data["versions"][-1]["version"]

    data = {
        "versions": [
            {
                "version": "0.0.0",
                "description": "Initial version",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ]
    }
    versions_file.write_text(json.dumps(data, indent=2) + "\n")
    return "0.0.0"


def get_version(project_dir: Path) -> str | None:
    """Get the current (latest) version string for a project.

    Args:
        project_dir: Path to the project directory.

    Returns:
        Version string (e.g., "0.1.0") or None if no versions.json exists.
    """
    versions_file = project_dir / "versions.json"
    if not versions_file.is_file():
        return None

    data = json.loads(versions_file.read_text())
    return data["versions"][-1]["version"]


def bump_version(
    project_dir: Path, bump: str = "patch", description: str = "",
    files_changed: list[str] | None = None,
) -> str:
    """Increment the project version and record the change.

    Args:
        project_dir: Path to the project directory.
        bump: One of "patch", "minor", or "major".
        description: Human-readable description of what changed.

    Returns:
        The new version string.

    Raises:
        ValueError: If bump is not "patch", "minor", or "major".
        FileNotFoundError: If versions.json does not exist (must init first).
    """
    if bump not in ("patch", "minor", "major"):
        raise ValueError(
            f"bump must be 'patch', 'minor', or 'major', got '{bump}'"
        )

    versions_file = project_dir / "versions.json"
    if not versions_file.is_file():
        raise FileNotFoundError(
            f"No versions.json in {project_dir}. Call init_versions() first."
        )

    data = json.loads(versions_file.read_text())
    current = data["versions"][-1]["version"]
    parts = [int(x) for x in current.split(".")]

    if bump == "major":
        parts = [parts[0] + 1, 0, 0]
    elif bump == "minor":
        parts = [parts[0], parts[1] + 1, 0]
    else:  # patch
        parts = [parts[0], parts[1], parts[2] + 1]

    new_version = ".".join(str(p) for p in parts)
    entry = {
        "version": new_version,
        "description": description,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if files_changed:
        entry["files_changed"] = files_changed
    data["versions"].append(entry)
    versions_file.write_text(json.dumps(data, indent=2) + "\n")
    return new_version


def _run_git(
    root: "Path | str",
    args: list[str],
    ok_codes: tuple[int, ...] = (0,),
    timeout: float = 10,
) -> "subprocess.CompletedProcess[str]":
    """Run ``git --literal-pathspecs <args>`` in *root* and check the exit code.

    No shell is involved: *args* are passed as argv elements, and callers put
    every pathspec after ``--``. ``--literal-pathspecs`` stops glob characters
    in a filename (``a[1].maxpat``) from matching sibling files.

    Returns:
        The CompletedProcess (stdout/stderr as text).

    Raises:
        RuntimeError: ``git <subcommand> failed (exit N): <stderr>`` when the
            exit code is not in *ok_codes*, or ``git <subcommand> could not
            run: <error>`` when git is missing, times out, or cannot start.
    """
    import subprocess

    try:
        result = subprocess.run(
            ["git", "--literal-pathspecs", *args],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
        raise RuntimeError(f"git {args[0]} could not run: {exc}") from exc
    if result.returncode not in ok_codes:
        raise RuntimeError(
            f"git {args[0]} failed (exit {result.returncode}): {result.stderr.strip()}"
        )
    return result


def auto_commit_patch(
    project_dir: Path,
    base_dir: Path,
    description: str = "",
    files: list[str] | None = None,
) -> str | None:
    """Auto-commit patch project files to git after a save operation.

    The commit is path-scoped (fix-plan Q5, review finding A5): it runs
    ``git commit -m <msg> -- <paths>`` from the repository root, so anything
    another instance already staged stays staged and out of this commit, and
    the "anything to commit?" check looks only at these paths.

    The repository root comes from ``git rev-parse --show-toplevel`` run in
    *base_dir*. Every path is made absolute (relative ``files`` entries
    resolve against *base_dir*, never the process cwd) and passed as a
    literal pathspec after ``--``. Every git return code is checked.

    Args:
        project_dir: Path to the project directory (e.g., patches/gen-eq/).
            Its name is used in the commit message; it is also the pathspec
            when ``files`` is empty.
        base_dir: A directory inside the repo (normally the repo root); git
            commands run from the root ``rev-parse`` finds from here.
        description: Human-readable description of the change.
        files: Optional explicit list of file paths to commit (absolute, or
            relative to base_dir). If empty/None, commits all changes under
            project_dir/.

    Returns:
        The full commit hash, or None when the given paths have nothing to
        commit (other staged files do not count).

    Raises:
        RuntimeError: When any git command fails or cannot run (not a git
            repository, ignored path, index.lock contention, missing git,
            timeout). The message names the git subcommand and its stderr.
    """
    base = Path(base_dir)
    root_out = _run_git(base, ["rev-parse", "--show-toplevel"]).stdout.strip()
    root = Path(root_out).resolve()

    def _abs(p: "str | Path") -> str:
        p = Path(p)
        if not p.is_absolute():
            p = base / p
        return str(p.resolve())

    if files:
        paths = [_abs(f) for f in files]
    else:
        paths = [_abs(project_dir)]

    _run_git(root, ["add", "--", *paths])

    staged = _run_git(root, ["diff", "--cached", "--quiet", "--", *paths], ok_codes=(0, 1))
    if staged.returncode == 0:
        return None  # Nothing to commit for these paths

    project_name = Path(project_dir).name
    msg = f"patch({project_name}): {description}" if description else f"patch({project_name}): auto-save"

    _run_git(root, ["commit", "-q", "-m", msg, "--", *paths], timeout=30)

    # Path-scoped log is race-safe against another instance committing other
    # paths between our commit and this lookup (rev-parse HEAD is not).
    return _run_git(root, ["log", "-1", "--format=%H", "--", *paths]).stdout.strip()


def list_versions(project_dir: Path) -> list[dict]:
    """List all version entries for a project, newest first.

    Args:
        project_dir: Path to the project directory.

    Returns:
        List of version entry dicts (version, description, timestamp),
        ordered newest first. Empty list if no versions.json.
    """
    versions_file = project_dir / "versions.json"
    if not versions_file.is_file():
        return []

    data = json.loads(versions_file.read_text())
    return list(reversed(data["versions"]))


def update_version_comment(patcher: Patcher, version: str) -> Box:
    """Add or update a version comment box in the top-right of the patch.

    Searches for an existing comment matching the ``vX.Y.Z`` pattern and
    updates its text in place.  If none exists, a new comment is created at
    position (550, 10).

    Args:
        patcher: The Patcher instance to modify.
        version: Version string *without* the ``v`` prefix (e.g., ``"0.1.0"``).

    Returns:
        The Box object for the version comment (created or updated).
    """
    version_text = f"v{version}"

    # Search for existing version comment
    for box in patcher.find_boxes(maxclass="comment"):
        if _VERSION_COMMENT_RE.match(box.text):
            box.text = version_text
            return box

    # No existing version comment -- create one
    return patcher.add_comment(version_text, x=550.0, y=10.0)


def list_projects(base_dir: Path) -> list[str]:
    """List all project names (directories under patches/ excluding hidden files).

    Args:
        base_dir: Root directory containing the patches/ folder.

    Returns:
        Sorted list of project directory names.
    """
    patches_dir = base_dir / "patches"
    if not patches_dir.is_dir():
        return []

    return sorted(
        d.name
        for d in patches_dir.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    )


# File extensions to include in examples/ copies
_EXAMPLE_EXTENSIONS = {".maxpat", ".gendsp", ".js"}


def _read_project_description(project_dir: Path) -> str:
    """Extract the first non-empty, non-heading line from context.md.

    Args:
        project_dir: Path to the project directory.

    Returns:
        Description string, or "No description" if none found.
    """
    context_file = project_dir / "context.md"
    if not context_file.is_file():
        return "No description"

    for line in context_file.read_text().splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return stripped

    return "No description"


def build_examples_catalog(base_dir: Path) -> Path:
    """Build an examples/ directory and PATCHES.md catalog from generated patches.

    For each project in patches/:
    1. Copies .maxpat, .gendsp, and .js files from generated/ to examples/{name}/
    2. Generates PATCHES.md with a summary table and per-project detail sections

    The function is idempotent -- it cleans and rebuilds examples/ on each call.

    Args:
        base_dir: Root directory containing the patches/ folder.

    Returns:
        Path to the generated PATCHES.md file.
    """
    examples_dir = base_dir / "examples"
    projects = list_projects(base_dir)

    # Collect project info
    project_data: list[dict] = []
    for name in projects:
        project_dir = base_dir / "patches" / name
        generated_dir = project_dir / "generated"

        if not generated_dir.is_dir():
            continue

        # Find eligible files
        files = sorted(
            f.name
            for f in generated_dir.iterdir()
            if f.is_file() and f.suffix in _EXAMPLE_EXTENSIONS
        )

        if not files:
            continue

        version = get_version(project_dir) or "unknown"
        description = _read_project_description(project_dir)

        project_data.append({
            "name": name,
            "version": version,
            "description": description,
            "files": files,
            "generated_dir": generated_dir,
        })

    # Copy files to examples/
    for proj in project_data:
        dest_dir = examples_dir / proj["name"]

        # Clean existing directory for idempotent rebuild
        if dest_dir.exists():
            shutil.rmtree(dest_dir)

        dest_dir.mkdir(parents=True)

        for fname in proj["files"]:
            shutil.copy2(proj["generated_dir"] / fname, dest_dir / fname)

    # Generate PATCHES.md
    lines: list[str] = []
    lines.append("# Patch Catalog")
    lines.append("")
    lines.append("Generated patch examples from the MAX project.")
    lines.append("")

    # Summary table
    lines.append("| Project | Version | Description |")
    lines.append("|---------|---------|-------------|")
    for proj in project_data:
        link = f"[{proj['name']}](examples/{proj['name']}/)"
        lines.append(f"| {link} | {proj['version']} | {proj['description']} |")
    lines.append("")

    # Per-project detail sections
    for proj in project_data:
        lines.append(f"## {proj['name']}")
        lines.append("")
        lines.append(f"**Version:** {proj['version']}")
        lines.append(f"**Description:** {proj['description']}")
        lines.append("")
        lines.append("Files:")
        for fname in proj["files"]:
            lines.append(f"- {fname}")
        lines.append("")
        lines.append("---")
        lines.append("")

    patches_md = base_dir / "PATCHES.md"
    patches_md.write_text("\n".join(lines))

    return patches_md
