"""Semantic patch diff (fix-plan Q36, review §5.4).

``diff_patch_dicts(old, new)`` compares two ``.maxpat`` file dicts
(``{"patcher": {...}}``) and returns a :class:`PatchDiff`: a flat list of
frozen :class:`DiffEntry` records describing the changes FROM ``old`` TO
``new`` (``Patcher.diff``: ``a.diff(b)`` is the change from a to b, as in
``git diff A B``). ``PatchDiff.render()`` gives a compact text view with a
summary line, for showing the user what an edit changed.

The diff is pure: it does no I/O and never mutates its inputs.

Boxes are matched by box id. The walk is iterative (an explicit stack), so
deep patcher nesting cannot hit the recursion limit.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Iterator

from src.maxpat.walk import box_label, box_maxclass

#: Every entry kind, in render / summary order.
DIFF_KINDS: tuple = (
    "box_added",
    "box_removed",
    "moved",
    "resized",
    "text",
    "attrs",
    "presentation",
    "subpatcher_added",
    "subpatcher_removed",
    "cord_added",
    "cord_removed",
    "cord_rerouted",
    "props",
    "zorder",
)

_LABEL_MAX = 40


@dataclass(frozen=True)
class DiffEntry:
    """One change. Values are hashable (tuples, str, int, float, bool, None).

    kind: one of DIFF_KINDS.
    path: ancestor box ids, ``()`` at the top level.
    where: rendered path prefix (``"p params/"``), ``""`` at the top level.
    box_id: the box id, None for cords and level-wide entries.
    label: display label (box text, truncated) or ``src:o -> dst:i`` for cords.
    old / new: kind-specific before / after values.
    """

    kind: str
    path: tuple
    where: str
    box_id: str | None
    label: str
    old: Any = None
    new: Any = None


@dataclass
class PatchDiff:
    """The changes from one patch dict to another (a list of DiffEntry)."""

    entries: list = field(default_factory=list)

    def __bool__(self) -> bool:
        return bool(self.entries)

    def __len__(self) -> int:
        return len(self.entries)

    def __iter__(self) -> Iterator[DiffEntry]:
        return iter(self.entries)

    def of(self, *kinds: str) -> list:
        """Entries whose kind is one of *kinds*."""
        wanted = set(kinds)
        return [e for e in self.entries if e.kind in wanted]

    def counts(self) -> dict:
        """Non-zero entry counts per kind, in DIFF_KINDS order."""
        c = Counter(e.kind for e in self.entries)
        return {k: c[k] for k in DIFF_KINDS if c.get(k)}

    def render(self, max_lines: int = 40) -> str:
        """Compact text: one line per entry (at most *max_lines*), then a
        ``... N more`` line when truncated, then a summary line.
        ``"no changes"`` for an empty diff."""
        if not self.entries:
            return "no changes"
        lines = [_render_entry(e) for e in self.entries[:max_lines]]
        rest = len(self.entries) - len(lines)
        if rest > 0:
            lines.append(f"... {rest} more")
        summary = ", ".join(f"{n} {k}" for k, n in self.counts().items())
        lines.append(f"{len(self.entries)} change(s): {summary}")
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.render()


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _g(value) -> str:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return format(value, "g")
    return str(value)


def _render_entry(e: DiffEntry) -> str:
    w = e.where
    if e.kind == "box_added":
        at = ""
        if isinstance(e.new, tuple) and len(e.new) == 2:
            at = f" @{_g(e.new[0])},{_g(e.new[1])}"
        return f"+ {w}{e.box_id} [{e.label}]{at}"
    if e.kind == "box_removed":
        return f"- {w}{e.box_id} [{e.label}]"
    if e.kind == "cord_added":
        return f"+ cord {w}{e.label}"
    if e.kind == "cord_removed":
        return f"- cord {w}{e.label}"
    return f"~ {w}{e.box_id or ''} {e.kind}"


# ---------------------------------------------------------------------------
# Diff
# ---------------------------------------------------------------------------


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def _display(box: dict) -> str:
    """Untruncated display label: newobj text, ``maxclass text`` for other
    text-bearing boxes, else walk.box_label."""
    text = box.get("text")
    maxclass = box_maxclass(box)
    if isinstance(text, str):
        if maxclass == "newobj":
            return text
        return f"{maxclass} {text}" if maxclass else text
    return box_label(box)


def _boxes(patcher: dict) -> list:
    """``[(id, box)]`` for every well-formed box, in file order."""
    out = []
    boxes = patcher.get("boxes")
    if not isinstance(boxes, list):
        return out
    seen = set()
    for entry in boxes:
        if not isinstance(entry, dict):
            continue
        box = entry.get("box")
        if not isinstance(box, dict):
            continue
        box_id = box.get("id")
        if not isinstance(box_id, str) or box_id in seen:
            continue
        seen.add(box_id)
        out.append((box_id, box))
    return out


def _cords(patcher: dict) -> list:
    """``[(key, patchline)]`` for every well-formed line; key is
    ``(src_id, outlet, dst_id, inlet)``."""
    out = []
    lines = patcher.get("lines")
    if not isinstance(lines, list):
        return out
    for entry in lines:
        if not isinstance(entry, dict):
            continue
        pl = entry.get("patchline")
        if not isinstance(pl, dict):
            continue
        src, dst = pl.get("source"), pl.get("destination")
        if not (isinstance(src, list) and isinstance(dst, list)):
            continue
        if len(src) < 2 or len(dst) < 2:
            continue
        if not (isinstance(src[0], str) and isinstance(dst[0], str)):
            continue
        if not all(isinstance(v, int) and not isinstance(v, bool) for v in (src[1], dst[1])):
            continue
        out.append(((src[0], src[1], dst[0], dst[1]), pl))
    return out


def _xy(box: dict):
    rect = box.get("patching_rect")
    if isinstance(rect, list) and len(rect) >= 4:
        return (rect[0], rect[1])
    return None


def _cord_label(key: tuple) -> str:
    return f"{key[0]}:{key[1]} -> {key[2]}:{key[3]}"


def _patcher_of(file_dict, side: str) -> dict:
    inner = file_dict.get("patcher") if isinstance(file_dict, dict) else None
    if not isinstance(inner, dict):
        raise ValueError(f"diff_patch_dicts: {side} has no 'patcher' dict")
    return inner


def diff_patch_dicts(old: dict, new: dict) -> PatchDiff:
    """The changes from *old* to *new* (both ``{"patcher": {...}}`` dicts).

    Raises:
        ValueError: when a side lacks a ``"patcher"`` dict.
    """
    old_p = _patcher_of(old, "old")
    new_p = _patcher_of(new, "new")
    entries: list = []
    path: tuple = ()
    where = ""

    old_boxes = _boxes(old_p)
    new_boxes = _boxes(new_p)
    old_map = dict(old_boxes)
    new_ids = {box_id for box_id, _ in new_boxes}

    for box_id, box in new_boxes:
        if box_id not in old_map:
            entries.append(DiffEntry(
                "box_added", path, where, box_id,
                _truncate(_display(box), _LABEL_MAX), None, _xy(box),
            ))
    for box_id, box in old_boxes:
        if box_id not in new_ids:
            entries.append(DiffEntry(
                "box_removed", path, where, box_id,
                _truncate(_display(box), _LABEL_MAX), None, None,
            ))

    old_cords = _cords(old_p)
    new_cords = _cords(new_p)
    added = Counter(k for k, _ in new_cords) - Counter(k for k, _ in old_cords)
    removed = Counter(k for k, _ in old_cords) - Counter(k for k, _ in new_cords)
    for key, _ in new_cords:
        if added.get(key):
            added[key] -= 1
            entries.append(DiffEntry("cord_added", path, where, None, _cord_label(key), None, key))
    for key, _ in old_cords:
        if removed.get(key):
            removed[key] -= 1
            entries.append(DiffEntry("cord_removed", path, where, None, _cord_label(key), key, None))

    return PatchDiff(entries)
