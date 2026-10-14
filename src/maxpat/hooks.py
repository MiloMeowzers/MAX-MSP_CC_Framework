"""File write hooks for .maxpat, .gendsp, and .js output.

Save gate (fix-plan Q7, review A3 / R1): save_patch_roundtrip and
write_gendsp run validate_patch on a deepcopy plus review_patch, with one
cached ObjectDatabase, before anything is written or committed. Blocking
findings are compared with a baseline -- original_text, else the HEAD
version of the path, else the file on disk -- and matched by rule template
plus box ids (never by finding text), so only blockers the save introduces
raise PatchValidationError; with no baseline the file is new and every
blocker refuses. Cords removed compared with HEAD (and original_text) emit
one SaveGateWarning. A changed x-rank of a subpatcher or abstraction
inlet/outlet raises PatchValidationError. ``force=True`` saves anyway with a
SaveGateWarning listing what was bypassed. write_js validation stays
report-only; validate_file runs on demand. The gate validates .gendsp /
.genjit files in gen scope and .rnbopat files in rnbo scope
(SCOPE_BY_SUFFIX; Q12 / C3), so RNBO/Gen-only names are legal there.

Provides:
- finalize_patch: Single-call layout cleanup hook for new and edited patches.
- write_gendsp: Generate and write a .gendsp file to disk.
- write_js: Write JavaScript code and run code validation.
- validate_file: Load and validate an existing .maxpat file from disk.
- validate_code_file: Validate .gendsp or .js code files from disk.
- PatchGenerationError: Raised when unfixable errors prevent generation.
- PatchValidationError: Raised when the save gate blocks a file write.
- SaveGateWarning: Warning for removed cords and force=True bypasses.
- StaleFileError: Raised when a file changed on disk since it was read.

Save safety (Q5): save_patch_roundtrip, write_gendsp and write_js auto-commit
only the saved path (``git commit -m msg -- <path>`` from the repo root), so
anything else already staged stays staged and out of the commit. They commit
only under ``patches/<project>/`` of a git repository, and return the commit
hash (write_gendsp/write_js as a ``commit_hash`` attribute on their usual
return value) or None with a UserWarning giving the reason. save_patch_roundtrip
raises StaleFileError when original_text no longer matches the file on disk;
``force=True`` overwrites with a warning.
"""

from __future__ import annotations

import copy
import functools
import json
import os
import re
import warnings
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

from src.maxpat.validation import validate_patch, has_blocking_errors, ValidationResult
from src.maxpat.db_lookup import SCOPE_BY_SUFFIX

if TYPE_CHECKING:
    from src.maxpat.patcher import Patcher


def _auto_commit_saved_file(path: Path) -> str | None:
    """Auto-commit a saved file to git to prevent work loss (fix-plan Q5, A5).

    Finds the repository from the file's own directory with
    ``git rev-parse --show-toplevel``. When the file sits under
    ``patches/<project>/`` (measured from the repo root), commits exactly this
    one path via :func:`auto_commit_patch` -- anything else already staged
    stays staged and out of the commit.

    Never raises: a commit failure must not block the save, which has already
    happened. Every outcome other than a commit emits one ``UserWarning``
    naming the path and the reason:

    - not inside a git repository;
    - outside ``patches/<project>/`` (commit it yourself with an explicit path);
    - auto-commit failed (git error text: ignored path, index.lock, ...);
    - no changes to commit (the file matches the last commit).

    Returns:
        The full commit hash, or None (with a warning) when nothing was
        committed.
    """
    from src.maxpat.project import auto_commit_patch, _run_git

    abs_path = Path(path).resolve()

    try:
        root_out = _run_git(abs_path.parent, ["rev-parse", "--show-toplevel"]).stdout.strip()
        root = Path(root_out).resolve()
        rel = abs_path.relative_to(root)
    except (RuntimeError, ValueError):
        warnings.warn(
            f"{path}: not inside a git repository -- not auto-committed",
            UserWarning,
            stacklevel=3,
        )
        return None

    dir_parts = rel.parts[:-1]
    if "patches" not in dir_parts or dir_parts.index("patches") + 1 >= len(dir_parts):
        warnings.warn(
            f"{path}: outside patches/<project>/ in repo {root} -- not auto-committed; "
            f"commit it yourself with an explicit path",
            UserWarning,
            stacklevel=3,
        )
        return None
    i = dir_parts.index("patches")
    project_dir = root.joinpath(*rel.parts[: i + 2])

    try:
        commit_hash = auto_commit_patch(
            project_dir,
            root,
            description=f"save {abs_path.name}",
            files=[str(abs_path)],
        )
    except Exception as exc:  # never let a commit failure block the save
        warnings.warn(
            f"{path}: auto-commit failed -- {exc}; the file was saved but is not committed",
            UserWarning,
            stacklevel=3,
        )
        return None

    if commit_hash is None:
        warnings.warn(
            f"{path}: no changes to commit -- the file matches the last commit",
            UserWarning,
            stacklevel=3,
        )
        return None
    return commit_hash


def _write_and_sync(path: Path, content: str) -> None:
    """Write content to file and fsync to ensure Finder/MAX see changes."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())


def finalize_patch(patcher: "Patcher", is_new: bool = True) -> None:
    """Single-call layout cleanup hook for new and edited patches.

    For new patches (is_new=True):
        Applies auto-styling, full topological layout, assistance comments,
        and midpoint generation for all patchers and subpatchers.

    For edited patches (is_new=False):
        Never clears existing cable midpoints (Q6 / B1). It routes only
        cords that have no midpoints AND are new or touch a box added or
        moved in this edit, recursively through subpatchers, and fills
        empty inlet/outlet assistance comments (written to ``_raw`` so they
        reach disk). Existing objects are never repositioned. A moved box's
        already-routed cords keep their midpoints.

    Args:
        patcher: The Patcher instance to finalize.
        is_new: True for newly created patches, False for loaded/edited patches.
    """
    from src.maxpat.aesthetics import apply_auto_styling
    from src.maxpat.layout import apply_layout, _generate_midpoints

    if is_new:
        apply_auto_styling(patcher)
        apply_layout(patcher)
        patcher.populate_assistance_comments()
    else:
        patcher.populate_assistance_comments()
        _finalize_midpoints_recursive(patcher, _generate_midpoints)


def _box_added_or_moved(box) -> bool:
    """True when a box was added or moved since the patch was loaded.

    Added: the box has no ``_raw`` (created in this session) or no load-time
    snapshot (``_loaded_rect``; builder boxes made via ``Box.__new__`` lack
    the attribute). Moved: its x or y differs from the snapshot. A resize
    alone (width/height change, e.g. from a text edit) is not a move.
    """
    if box._raw is None:
        return True
    snap = getattr(box, "_loaded_rect", None)
    if snap is None:
        return True
    return (
        box.patching_rect[0] != snap[0] or box.patching_rect[1] != snap[1]
    )


def _finalize_midpoints_recursive(
    patcher: "Patcher",
    generate_fn: "callable",
) -> None:
    """Route eligible unrouted cords on a patcher and all nested subpatchers.

    Never clears existing midpoints (Q6 / B1). A cord is eligible when it is
    new (``line._raw is None``) or its source or destination box was added
    or moved in this edit; ``generate_fn`` itself still skips any cord that
    already has midpoints. Net rule: a cord is routed only if it has no
    midpoints and is new or touches an added or moved box.

    Args:
        patcher: The Patcher instance to process.
        generate_fn: The _generate_midpoints function from layout module
            (called with the keyword-only ``eligible`` filter).
    """
    touched = {b.id for b in patcher.boxes if _box_added_or_moved(b)}

    def _eligible(line) -> bool:
        return (
            line._raw is None
            or line.source_id in touched
            or line.dest_id in touched
        )

    generate_fn(patcher, eligible=_eligible)

    # Recurse into subpatchers
    for box in patcher.boxes:
        if box._inner_patcher is not None and box._inner_patcher.boxes:
            _finalize_midpoints_recursive(box._inner_patcher, generate_fn)


def detect_indent(file_text: str) -> str:
    """Detect the indentation style used in a JSON file.

    Reads the first indented line and returns the whitespace prefix.
    Returns 4 spaces (MAX default) if no indented line is found.

    Args:
        file_text: Raw file content as a string.

    Returns:
        The indentation string (e.g., "    ", "  ", "\\t").
    """
    for line in file_text.split("\n"):
        stripped = line.lstrip()
        if stripped and line != stripped:
            # Found an indented line -- extract the leading whitespace
            indent_chars = line[: len(line) - len(stripped)]
            return indent_chars
    return "    "  # Default: 4 spaces (MAX 9.1.2 format per user decision)


def save_patch_roundtrip(
    patch_dict: dict,
    path: "str | Path",
    original_text: str | None = None,
    *,
    force: bool = False,
) -> str | None:
    """Save a .maxpat dict preserving the original file's indentation.

    For round-trip saves (load -> edit -> save), pass the original file text
    so indentation is preserved. For new files, omit original_text to use
    MAX's default 4-space indentation.

    Stale-file check (fix-plan Q5, review finding A6): when original_text is
    given and the file already exists, the file on disk must still equal
    original_text exactly. If it does not (typically the user saved it in MAX
    after read_patch), StaleFileError is raised BEFORE anything is written or
    committed, so the MAX-side work is not silently lost. A target that does
    not exist yet is never stale. Re-read after every save before saving the
    same file again.

    Save gate (fix-plan Q7, review A3 / R1): after the stale check and
    before anything is written, validate_patch (on a deepcopy) and
    review_patch run on the new dict with one cached ObjectDatabase. Their
    blocking findings are compared with the baseline -- original_text, else
    the HEAD version of the path, else the file on disk -- by rule template
    plus box ids, never by finding text. Only findings the save introduces
    raise PatchValidationError; pre-existing ones save. A new file (no
    baseline) refuses every blocker. The caller's dict is never modified.

    Args:
        patch_dict: The .maxpat dict (output of Patcher.to_dict()).
        path: Destination file path.
        original_text: Original file content, as returned by read_patch().
            Used for indent detection and as the stale-check baseline. If
            None, uses 4-space indent (MAX 9.1.2 default) and skips the
            stale check.
        force: Keyword-only. Overwrite a stale file anyway, with a
            UserWarning, and bypass the save gate, with a SaveGateWarning
            listing what was bypassed. Use only when the user confirms the
            on-disk changes can be discarded or the findings are accepted.

    Returns:
        The full git commit hash of the path-scoped auto-commit (fix-plan
        Q5, A5), or None when nothing was committed. Every None comes with
        a UserWarning naming the reason: not inside a git repository,
        outside ``patches/<project>/``, git failed, or no changes to commit.
        Only this one path is committed; other staged files stay staged.

    Raises:
        StaleFileError: original_text no longer matches the file on disk and
            force is False. The file is untouched and nothing is committed.
        PatchValidationError: the save gate found blocking findings the save
            would introduce and force is False. Raised before anything is
            written or committed; ``findings`` and ``port_changes`` say why.
    """
    path = Path(path)

    # Stale-file check first: before mkdir, write or commit (Q5, A6).
    if original_text is not None and path.exists():
        if path.read_text() != original_text:
            if not force:
                raise StaleFileError(path)
            warnings.warn(
                f"{path}: file changed on disk since it was read; "
                f"overwriting because force=True",
                UserWarning,
                stacklevel=2,
            )

    # Save gate (Q7, A3 / R1): after the stale check, before mkdir/write/commit.
    _run_save_gate(patch_dict, path, original_text, force=force)

    if original_text is not None:
        indent = detect_indent(original_text)
    else:
        indent = "    "  # MAX default: 4 spaces

    # json.dumps indent parameter accepts str for custom indentation
    output = json.dumps(patch_dict, indent=indent, ensure_ascii=False)

    # Preserve trailing newline status of original file
    if original_text is not None and original_text.endswith("\n"):
        output += "\n"

    path.parent.mkdir(parents=True, exist_ok=True)
    _write_and_sync(path, output)

    # Auto-commit to git to prevent work loss (path-scoped; warns on None)
    return _auto_commit_saved_file(path)


def read_patch(path: "str | Path") -> tuple["Patcher", str]:
    """Load a .maxpat file into a Patcher ready for querying and editing.

    Returns (patcher, original_text) tuple. Pass original_text back to
    save_patch_roundtrip() for indent-preserving saves; it is also the
    baseline for the stale-file check (StaleFileError if the file changed on
    disk in between). Re-read after each save before saving the same file
    again -- the old original_text no longer matches the file.

    The Patcher's ``domain_context`` comes from the file suffix (.gendsp /
    .genjit -> gen, .rnbopat -> rnbo; SCOPE_BY_SUFFIX), else from the
    patcher's classnamespace / top-level codebox (Q12 / C3).

    Args:
        path: Path to the .maxpat file (str or pathlib.Path).

    Returns:
        (patcher, original_text) tuple.

    Raises:
        FileNotFoundError: If the file does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
        ValueError: If the JSON structure is not a valid .maxpat
            (missing 'patcher' key).
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    original_text = path.read_text()
    data = json.loads(original_text)
    from src.maxpat.patcher import Patcher
    patcher = Patcher.from_dict(data, domain_context=SCOPE_BY_SUFFIX.get(path.suffix))
    return (patcher, original_text)


class PatchGenerationError(Exception):
    """Raised when unfixable structural errors prevent patch generation."""


class PatchValidationError(Exception):
    """Raised when the save gate refuses a write (fix-plan Q7, A3 / R1).

    save_patch_roundtrip() and write_gendsp() raise it BEFORE anything is
    written or committed when the save would introduce a blocking validation
    error or critic blocker (any blocker, for a new file), or would change
    the x-rank of a subpatcher/abstraction inlet or outlet. Fix the findings,
    or pass force=True to save anyway (with a SaveGateWarning).

    Still constructible from a bare message: ``PatchValidationError("msg")``.

    Attributes:
        path: The file that was not written, or None.
        findings: The new blocking ValidationResult / CriticResult objects.
        port_changes: Human-readable port x-rank changes (list of str).
    """

    def __init__(
        self,
        message: str,
        *,
        path: "str | Path | None" = None,
        findings=(),
        port_changes=(),
    ) -> None:
        self.path = path
        self.findings = list(findings)
        self.port_changes = list(port_changes)
        super().__init__(message)


class StaleFileError(Exception):
    """Raised when a file changed on disk since it was read (fix-plan Q5, A6).

    save_patch_roundtrip() raises this before writing when original_text no
    longer matches the file on disk -- usually because the user saved it in
    MAX after read_patch(). Re-read and re-apply the edit, or pass
    force=True to overwrite.

    Attributes:
        path: The file that changed.
    """

    def __init__(self, path: "str | Path") -> None:
        self.path = path
        super().__init__(
            f"{path}: file changed in MAX since it was read; re-read and "
            f"re-apply (read_patch), or pass force=True to overwrite"
        )


class GendspWriteResult(dict):
    """write_gendsp() return value: the .gendsp dict plus ``commit_hash``.

    A plain dict subclass with identical content; ``commit_hash`` is the
    auto-commit hash (str) or None when nothing was committed (Q5, OQ1-A).
    """

    commit_hash: "str | None" = None


class JsWriteResult(list):
    """write_js() return value: the ValidationResult list plus ``commit_hash``.

    A plain list subclass with identical content; ``commit_hash`` is the
    auto-commit hash (str) or None when nothing was committed (Q5, OQ1-A).
    """

    commit_hash: "str | None" = None


# ===========================================================================
# Save gate (Q7, review A3 / R1)
# ===========================================================================
#
# save_patch_roundtrip() and write_gendsp() call _run_save_gate() before any
# mkdir, write or commit. The gate never mutates the caller's dict: only
# deepcopies reach validate_patch/review_patch, and apply_fixes is never
# called.


class SaveGateWarning(UserWarning):
    """Warning emitted by the save gate (fix-plan Q7).

    Raised as a warning (never an error) for removed cords, and when
    ``force=True`` bypasses a refusal; the message lists what was bypassed.
    """


class GateReport(NamedTuple):
    """Result of comparing a patch dict with its baseline (pure, no I/O)."""

    new_blockers: list
    removed_cords: list
    port_changes: list


@functools.lru_cache(maxsize=1)
def _gate_db():
    """One process-wide ObjectDatabase for the save gate.

    Cached for the life of the process, so edits to the DB files made while
    the process runs are not seen by the gate until it restarts.
    """
    from src.maxpat.db_lookup import ObjectDatabase

    return ObjectDatabase()


_GATE_ID_RE = re.compile(r"\bobj-\d+\b")
_GATE_QUOTED_RE = re.compile(r"'[^']*'|\"[^\"]*\"")
_GATE_NUM_RE = re.compile(r"\d+(\.\d+)?")
_GATE_WS_RE = re.compile(r"\s+")


def _finding_key(result) -> tuple:
    """Hashable identity of a blocking finding: rule template + box ids.

    Finding text is never compared as-is. The key is
    ``(origin, template, ids, proposed_removal)``:

    - origin: ``("validate", layer, level)`` or ``("review", severity)``;
    - template: the text with box ids replaced by ``<id>`` first, then
      quoted spans by ``<q>``, then numbers by ``<n>``, whitespace collapsed;
    - ids: sorted unique ``obj-N`` ids from the text, plus the source and
      destination ids of ``proposed_removal`` when set;
    - proposed_removal: the cord tuple, or None.
    """
    if isinstance(result, ValidationResult):
        origin: tuple = ("validate", result.layer, result.level)
        text = result.message or ""
        removal = result.proposed_removal
    else:
        origin = ("review", getattr(result, "severity", None))
        text = getattr(result, "finding", "") or ""
        removal = None

    ids = set(_GATE_ID_RE.findall(text))
    if removal is not None and len(removal) >= 3:
        ids.add(str(removal[0]))
        ids.add(str(removal[2]))

    template = _GATE_ID_RE.sub("<id>", text)
    template = _GATE_QUOTED_RE.sub("<q>", template)
    template = _GATE_NUM_RE.sub("<n>", template)
    template = _GATE_WS_RE.sub(" ", template).strip()
    return (origin, template, tuple(sorted(ids)), removal)


def _blocking_findings(patch_dict: dict, scope: "str | None" = None) -> list:
    """Blocking validation errors and critic blockers of *patch_dict*.

    Runs validate_patch and review_patch on deepcopies with the cached gate
    DB, swallowing incidental warnings. Validation errors mirror
    ``has_blocking_errors(..., is_new=True)``: every error blocks, including
    proposed removals, except a legacy ``auto_fixed`` one without a
    proposal. Pre-existing findings are exempted by the baseline diff, not
    here. *scope* is passed to validate_patch (None auto-detects; Q12).
    """
    from src.maxpat.critics import review_patch

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        v_results = validate_patch(copy.deepcopy(patch_dict), db=_gate_db(), scope=scope)
        c_results = review_patch(copy.deepcopy(patch_dict), db=_gate_db())

    found = [
        r for r in v_results
        if r.level == "error" and not (r.auto_fixed and r.proposed_removal is None)
    ]
    found.extend(r for r in c_results if r.severity == "blocker")
    return found


def _head_text(path: "str | Path") -> "str | None":
    """Text of *path* at HEAD in its own git repo, or None. Never raises."""
    from src.maxpat.project import _run_git

    try:
        abs_path = Path(path).resolve()
        anc = abs_path.parent
        while not anc.exists() and anc.parent != anc:
            anc = anc.parent
        root_out = _run_git(anc, ["rev-parse", "--show-toplevel"]).stdout.strip()
        root = Path(root_out).resolve()
        rel = abs_path.relative_to(root)
        result = _run_git(root, ["show", "HEAD:" + rel.as_posix()], ok_codes=(0, 128))
    except (RuntimeError, ValueError, OSError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout


def _parse_patch_text(text: "str | None") -> "dict | None":
    """json.loads *text*; None when absent, invalid, or without a patcher dict."""
    if text is None:
        return None
    try:
        data = json.loads(text)
    except ValueError:
        return None
    if not isinstance(data, dict) or not isinstance(data.get("patcher"), dict):
        return None
    return data


def _iter_patchers(patcher_dict: dict, path: tuple = ()):
    """Yield ``(path, patcher_dict)`` for a patcher and every embedded one.

    A path element is ``(box id, box text or maxclass)``, so a regenerated
    patch whose ``obj-5`` is now a different subpatcher is not compared
    port-for-port. Inner ids collide with outer ids, hence the path.
    """
    if not isinstance(patcher_dict, dict):
        return
    yield path, patcher_dict
    boxes = patcher_dict.get("boxes")
    if not isinstance(boxes, list):
        return
    for entry in boxes:
        box = entry.get("box") if isinstance(entry, dict) else None
        if not isinstance(box, dict):
            continue
        inner = box.get("patcher")
        if isinstance(inner, dict):
            elem = (str(box.get("id", "")), str(box.get("text") or box.get("maxclass") or ""))
            yield from _iter_patchers(inner, path + (elem,))


def _top_patcher(d: "dict | None") -> "dict | None":
    if not isinstance(d, dict):
        return None
    top = d.get("patcher")
    return top if isinstance(top, dict) else None


def _cord_set(d: "dict | None") -> set:
    """Set of ``(path, src_id, src_outlet, dst_id, dst_inlet)`` over all patchers.

    Malformed patchlines are skipped.
    """
    cords = set()
    for path, patcher in _iter_patchers(_top_patcher(d)):
        lines = patcher.get("lines")
        if not isinstance(lines, list):
            continue
        for entry in lines:
            line = entry.get("patchline") if isinstance(entry, dict) else None
            if not isinstance(line, dict):
                continue
            src = line.get("source")
            dst = line.get("destination")
            try:
                cords.add((path, str(src[0]), int(src[1]), str(dst[0]), int(dst[1])))
            except (TypeError, ValueError, IndexError, KeyError):
                continue
    return cords


def _box_ids(d: "dict | None") -> dict:
    """Map patcher path -> set of box ids in that patcher."""
    ids: dict = {}
    for path, patcher in _iter_patchers(_top_patcher(d)):
        found = set()
        for entry in patcher.get("boxes") or []:
            box = entry.get("box") if isinstance(entry, dict) else None
            if isinstance(box, dict) and "id" in box:
                found.add(str(box["id"]))
        ids[path] = found
    return ids


def _port_ranks(d: "dict | None") -> dict:
    """Map ``(path, "inlet"|"outlet", port box id)`` -> x-rank.

    The rank is the index among that patcher's boxes of that maxclass,
    sorted by ``(patching_rect x, array index)`` -- the order MAX uses to
    number subpatcher/abstraction ports. gen ``in N``/``out N`` boxes are
    numbered by argument and are not counted.
    """
    ranks: dict = {}
    for path, patcher in _iter_patchers(_top_patcher(d)):
        boxes = patcher.get("boxes")
        if not isinstance(boxes, list):
            continue
        for kind in ("inlet", "outlet"):
            ports = []
            for index, entry in enumerate(boxes):
                box = entry.get("box") if isinstance(entry, dict) else None
                if not isinstance(box, dict) or box.get("maxclass") != kind:
                    continue
                rect = box.get("patching_rect")
                try:
                    x = float(rect[0])
                except (TypeError, ValueError, IndexError, KeyError):
                    x = 0.0
                ports.append((x, index, str(box.get("id", ""))))
            ports.sort(key=lambda p: (p[0], p[1]))
            for rank, (_x, _i, box_id) in enumerate(ports):
                ranks[(path, kind, box_id)] = rank
    return ranks


def _path_label(path: tuple) -> str:
    """``top`` for the top level, else ``text (id) > text (id)``."""
    if not path:
        return "top"
    return " > ".join(f"{text} ({box_id})" for box_id, text in path)


def _gate_report(
    new_dict: dict,
    baseline_dict: "dict | None",
    ref_dicts: list,
    scope: "str | None" = None,
) -> GateReport:
    """Compare *new_dict* with its blocker baseline and cord/port references.

    Pure (no I/O). ``baseline_dict`` None means a new file: every blocking
    finding is new. Otherwise a finding is new when its key's count in the
    new patch exceeds its count in the baseline (multiset match).
    """
    new_findings = _blocking_findings(new_dict, scope=scope)
    if baseline_dict is None:
        new_blockers = list(new_findings)
    else:
        base_counts = Counter(_finding_key(r) for r in _blocking_findings(baseline_dict, scope=scope))
        seen: Counter = Counter()
        new_blockers = []
        for r in new_findings:
            key = _finding_key(r)
            seen[key] += 1
            if seen[key] > base_counts[key]:
                new_blockers.append(r)

    removed_cords: list = []
    port_changes: list = []
    if ref_dicts:
        # A cord is removed when every reference has it and the new dict
        # does not (a removal already present in original_text is exempt).
        ref_cords = set.intersection(*(_cord_set(r) for r in ref_dicts))
        removed_cords = sorted(ref_cords - _cord_set(new_dict))

        # A port changed when it exists in the new dict and every reference
        # and its new rank differs from its rank in every reference.
        new_ranks = _port_ranks(new_dict)
        ref_ranks = [_port_ranks(r) for r in ref_dicts]
        for key in sorted(new_ranks):
            if not all(key in rr for rr in ref_ranks):
                continue
            new_rank = new_ranks[key]
            if all(rr[key] != new_rank for rr in ref_ranks):
                path, kind, box_id = key
                port_changes.append(
                    f"{_path_label(path)}: {kind} {box_id} rank {ref_ranks[0][key]} -> {new_rank}"
                )

    return GateReport(new_blockers, removed_cords, port_changes)


def _run_save_gate(
    patch_dict: dict,
    path: "str | Path",
    original_text: "str | None",
    *,
    force: bool,
) -> None:
    """Refuse a save that introduces blockers (Q7). Writes nothing.

    Blocker baseline: original_text, else the HEAD version of *path*, else
    the file on disk (OQ1-A). No baseline means a new file, where every
    blocker refuses. Raises PatchValidationError, or with ``force=True``
    warns SaveGateWarning and returns.
    """
    path = Path(path)
    head_text = _head_text(path)
    disk_text = None
    if original_text is None and head_text is None and path.exists():
        try:
            disk_text = path.read_text()
        except (OSError, ValueError):
            disk_text = None

    if original_text is not None:
        base_label, baseline = "original_text", _parse_patch_text(original_text)
    elif head_text is not None:
        base_label, baseline = "HEAD", _parse_patch_text(head_text)
    else:
        base_label, baseline = "the file on disk", _parse_patch_text(disk_text)
    if baseline is None:
        base_label = "new file: every blocker refuses"

    refs: list = []
    for label, text in (("HEAD", head_text), ("original_text", original_text)):
        parsed = _parse_patch_text(text)
        if parsed is not None:
            refs.append((label, parsed))
    if not refs:
        parsed = _parse_patch_text(disk_text)
        if parsed is not None:
            refs.append(("the file on disk", parsed))

    report = _gate_report(
        patch_dict, baseline, [d for _, d in refs],
        scope=SCOPE_BY_SUFFIX.get(path.suffix),
    )

    # 1. Removed cords: one warning, whatever force is (review §4.1 class 9).
    if report.removed_cords:
        ref_labels = [label for label, _ in refs]
        if "HEAD" in ref_labels:
            against = "HEAD"
        else:
            against = ref_labels[0]
        new_ids = _box_ids(patch_dict)
        n = len(report.removed_cords)
        cord_lines = [f"{path}: {n} cord(s) removed compared with {against}:"]
        for cpath, src, outlet, dst, inlet in report.removed_cords[:10]:
            ids_here = new_ids.get(cpath, set())
            mark = ""
            if src not in ids_here or dst not in ids_here:
                mark = " (endpoint box deleted)"
            cord_lines.append(f"  {_path_label(cpath)}/{src}:{outlet} -> {dst}:{inlet}{mark}")
        if n > 10:
            cord_lines.append(f"  ... and {n - 10} more")
        warnings.warn("\n".join(cord_lines), SaveGateWarning, stacklevel=3)

    # 2. New blockers / port x-rank changes: refuse (or warn under force).
    if not report.new_blockers and not report.port_changes:
        return None

    lines = [f"save gate findings for {path} (baseline: {base_label}):"]
    if report.new_blockers:
        lines.append(f"{len(report.new_blockers)} new blocking finding(s):")
        lines.extend(f"  {r!r}" for r in report.new_blockers)
    if report.port_changes:
        lines.append(
            f"{len(report.port_changes)} subpatcher/abstraction port x-rank change(s) "
            f"(parent cords address ports by x-rank, so they would hit the wrong port):"
        )
        lines.extend(f"  {c}" for c in report.port_changes)
    lines.append("Fix them, or pass force=True to save anyway.")
    message = "\n".join(lines)

    if force:
        warnings.warn(f"force=True: saving despite {message}", SaveGateWarning, stacklevel=3)
        return None
    raise PatchValidationError(
        message,
        path=path,
        findings=report.new_blockers,
        port_changes=report.port_changes,
    )


def write_gendsp(
    code: str,
    path: str | Path,
    num_inputs: int | None = None,
    num_outputs: int | None = None,
    *,
    force: bool = False,
) -> dict:
    """Generate and write a .gendsp file to disk.

    Creates a standalone .gendsp file containing a Gen patcher with
    codebox, in/out objects, and patchlines.

    Save gate (fix-plan Q7): before anything is written, the generated dict
    goes through the same gate as save_patch_roundtrip -- validate_patch
    (on a deepcopy) and review_patch, compared with the HEAD version of the
    path, else the file on disk; with neither it is a new file and every
    blocker refuses. Removed cords warn (SaveGateWarning); new blockers and
    port x-rank changes raise PatchValidationError.

    Args:
        code: GenExpr source code for the codebox.
        path: Output file path for the .gendsp file.
        num_inputs: Number of inputs. Auto-detected from code if None.
        num_outputs: Number of outputs. Auto-detected from code if None.
        force: Keyword-only. Bypass the save gate, with a SaveGateWarning
            listing what was bypassed.

    Returns:
        The generated .gendsp dict, as a GendspWriteResult (a dict subclass)
        whose ``commit_hash`` attribute is the path-scoped auto-commit hash,
        or None with a UserWarning giving the reason (Q5). Overwrites
        unconditionally -- there is no stale-file check here.

    Raises:
        PatchValidationError: the save gate refused the write and force is
            False. Nothing is written, created or committed.
    """
    from src.maxpat.codegen import generate_gendsp

    path = Path(path)
    gendsp_dict = generate_gendsp(code, num_inputs, num_outputs)

    # Save gate (Q7): before mkdir, write or commit.
    _run_save_gate(gendsp_dict, path, None, force=force)

    # Create parent directories if needed
    path.parent.mkdir(parents=True, exist_ok=True)

    # Write JSON with readable formatting
    _write_and_sync(path, json.dumps(gendsp_dict, indent=2))

    # Auto-commit to git to prevent work loss (path-scoped; warns on None)
    result = GendspWriteResult(gendsp_dict)
    result.commit_hash = _auto_commit_saved_file(path)
    return result


def validate_file(path: str | Path) -> list[ValidationResult]:
    """Load and validate an existing .maxpat file from disk.

    .gendsp / .genjit files validate in gen scope and .rnbopat in rnbo
    scope (SCOPE_BY_SUFFIX); other suffixes auto-detect (Q12 / C3).

    Args:
        path: Path to the .maxpat file.

    Returns:
        List of ValidationResult from the validation pipeline.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    # Try to load JSON
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        return [ValidationResult(
            "json", "error",
            f"Invalid JSON: {e}",
        )]

    # Run the validation pipeline on the loaded dict
    return validate_patch(data, scope=SCOPE_BY_SUFFIX.get(path.suffix))


def validate_code_file(path: str | Path) -> list[ValidationResult]:
    """Validate a .gendsp or .js code file from disk.

    For .gendsp files: parses JSON, extracts codebox code attribute,
    and runs validate_genexpr on it.

    For .js files: reads content, uses detect_js_type to determine
    if N4M or js object, and runs the appropriate validator.

    Args:
        path: Path to the .gendsp or .js file.

    Returns:
        List of ValidationResult from the code validator.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    from src.maxpat.code_validation import (
        validate_genexpr,
        validate_js,
        validate_n4m,
        detect_js_type,
    )

    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    content = path.read_text()

    if path.suffix == ".gendsp":
        # Parse JSON and extract codebox code
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            return [ValidationResult(
                "json", "error",
                f"Invalid JSON in .gendsp file: {e}",
            )]

        # Find the codebox and extract code
        code = None
        for box_entry in data.get("patcher", {}).get("boxes", []):
            box = box_entry.get("box", {})
            if box.get("maxclass") == "codebox" and "code" in box:
                code = box["code"]
                break

        if code is None:
            return [ValidationResult(
                "code", "warning",
                "No codebox with 'code' attribute found in .gendsp file",
            )]

        return validate_genexpr(code)

    elif path.suffix == ".js":
        js_type = detect_js_type(content)
        if js_type == "n4m":
            return validate_n4m(content)
        elif js_type == "js":
            return validate_js(content)
        else:
            return [ValidationResult(
                "code", "warning",
                "Could not determine JavaScript type (N4M or js object) -- "
                "missing require('max-api') or inlets declaration",
            )]

    else:
        return [ValidationResult(
            "code", "warning",
            f"Unsupported file extension: {path.suffix} "
            f"(expected .gendsp or .js)",
        )]


def write_js(
    code: str,
    path: str | Path,
) -> list[ValidationResult]:
    """Write JavaScript code to disk and run code validation.

    Writes the code to the specified .js file path, then runs
    validate_code_file on the written file. Validation is report-only
    and never blocks the write.

    Args:
        code: JavaScript source code (N4M or js object).
        path: Output file path for the .js file.

    Returns:
        List of ValidationResult from code validation, as a JsWriteResult (a
        list subclass) whose ``commit_hash`` attribute is the path-scoped
        auto-commit hash, or None with a UserWarning giving the reason (Q5).
        Overwrites unconditionally -- there is no stale-file check here.
    """
    path = Path(path)

    # Create parent directories if needed
    path.parent.mkdir(parents=True, exist_ok=True)

    # Write the file first (never blocked by validation)
    _write_and_sync(path, code)

    # Auto-commit to git to prevent work loss (path-scoped; warns on None)
    commit_hash = _auto_commit_saved_file(path)

    # Run validation on the written file
    result = JsWriteResult(validate_code_file(path))
    result.commit_hash = commit_hash
    return result
