"""Semantic patch diff (fix-plan Q36, review §5.4).

``diff_patch_dicts(old, new)`` compares two ``.maxpat`` file dicts
(``{"patcher": {...}}``) and returns a :class:`PatchDiff`: a flat list of
frozen :class:`DiffEntry` records describing the changes FROM ``old`` TO
``new`` (``Patcher.diff``: ``a.diff(b)`` is the change from a to b, as in
``git diff A B``). ``PatchDiff.render()`` gives a compact text view with a
summary line, for showing the user what an edit changed.

The diff is pure: it does no I/O and never mutates its inputs.

Identity and kinds (D-06): boxes are matched by box id at each patcher
level. Per common box: ``moved`` (patching_rect x/y), ``resized`` (w/h,
reported separately), ``text`` (the display label: text or maxclass),
``attrs`` (sorted keys whose presence or value differs -- fontname,
fontsize, textcolor, saved_object_attributes and every other
non-structural key), ``presentation`` (the flag and presentation_rect),
``subpatcher_added`` / ``subpatcher_removed`` (only one side embeds a
patcher). Per level: ``box_added`` / ``box_removed``, ``cord_added`` /
``cord_removed`` (``(src, outlet, dst, inlet)`` multiset),
``cord_rerouted`` (midpoints differ), ``props`` (patcher-level keys) and
``zorder`` (the common boxes' order changed).

Recursion (D-07): the diff descends into every box that embeds a patcher on
both sides (``box["patcher"]``, or ``box["data"]["patcher"]`` for mc.gen~,
via ``walk.inner_patcher``), with the same id matching. ``DiffEntry.path``
holds ancestor box ids only, so renaming a ``p`` does not re-add its
contents; ``where`` is the rendered prefix built from ``walk.box_label``
(``p params/``; ``p x (obj-2)/`` when siblings share a label). Added and
removed boxes are not descended into, and external bpatchers (no embedded
patcher) are never loaded: their ``name`` / ``args`` show as attrs.

The walk is iterative (an explicit stack), so deep patcher nesting cannot
hit the recursion limit. Malformed boxes and lines are skipped, never
raised on.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Iterator

from src.maxpat.walk import box_label, box_maxclass, inner_patcher

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
_TEXT_MAX = 60

# Box keys never reported as attrs: identity, structure, and the fields
# with their own entry kinds.
_STRUCTURAL_KEYS = frozenset({
    "id", "maxclass", "text", "numinlets", "numoutlets", "outlettype",
    "patching_rect", "presentation", "presentation_rect", "patcher",
})


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


def _pres(value) -> str:
    if not (isinstance(value, tuple) and len(value) == 2) or not value[0]:
        return "off"
    rect = value[1]
    if isinstance(rect, tuple):
        return "on [" + ",".join(_g(v) for v in rect) + "]"
    return "on"


def _pair(value, sep: str) -> str:
    if isinstance(value, tuple) and len(value) == 2:
        return f"{_g(value[0])}{sep}{_g(value[1])}"
    return str(value)


def _zorder_moved(old, new) -> int:
    """Boxes that changed place in the stacking order: len - LIS."""
    import bisect

    if not (isinstance(old, tuple) and isinstance(new, tuple)):
        return 0
    index = {box_id: i for i, box_id in enumerate(old)}
    tails: list = []
    for box_id in new:
        i = index.get(box_id)
        if i is None:
            continue
        pos = bisect.bisect_left(tails, i)
        if pos == len(tails):
            tails.append(i)
        else:
            tails[pos] = i
    return len(new) - len(tails)


def _render_entry(e: DiffEntry) -> str:
    w = e.where
    head = f"{w}{e.box_id} [{e.label}]"
    kind = e.kind
    if kind == "box_added":
        at = ""
        if isinstance(e.new, tuple) and len(e.new) == 2:
            at = f" @{_pair(e.new, ',')}"
        return f"+ {head}{at}"
    if kind == "box_removed":
        return f"- {head}"
    if kind == "moved":
        return f"~ {head} moved {_pair(e.old, ',')} -> {_pair(e.new, ',')}"
    if kind == "resized":
        return f"~ {head} resized {_pair(e.old, 'x')} -> {_pair(e.new, 'x')}"
    if kind == "text":
        return (
            f'~ {w}{e.box_id} text "{_truncate(str(e.old), _TEXT_MAX)}"'
            f' -> "{_truncate(str(e.new), _TEXT_MAX)}"'
        )
    if kind == "attrs":
        return f"~ {head} attrs {','.join(e.new or ())}"
    if kind == "presentation":
        return f"~ {head} presentation {_pres(e.old)} -> {_pres(e.new)}"
    if kind == "subpatcher_added":
        return f"+ {head} subpatcher ({e.new} boxes)"
    if kind == "subpatcher_removed":
        return f"- {head} subpatcher ({e.old} boxes)"
    if kind == "cord_added":
        return f"+ cord {w}{e.label}"
    if kind == "cord_removed":
        return f"- cord {w}{e.label}"
    if kind == "cord_rerouted":
        return f"~ cord {w}{e.label} rerouted"
    if kind == "props":
        return f"~ {w}patcher props {','.join(e.new or ())}"
    if kind == "zorder":
        return f"~ {w}z-order changed ({_zorder_moved(e.old, e.new)} boxes)"
    return f"~ {head} {kind}"


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


def _rect(box: dict):
    rect = box.get("patching_rect")
    if isinstance(rect, list) and len(rect) >= 4:
        return rect
    return None


def _presentation(box: dict) -> tuple:
    flag = bool(box.get("presentation"))
    rect = box.get("presentation_rect") if flag else None
    return (flag, tuple(rect) if isinstance(rect, list) else None)


def _attr_value(box: dict, key: str, strip_data_patcher: bool):
    value = box[key]
    if strip_data_patcher and key == "data" and isinstance(value, dict):
        return {k: v for k, v in value.items() if k != "patcher"}
    return value


def _changed_keys(old: dict, new: dict, skip: frozenset, strip_data_patcher: bool = False) -> tuple:
    keys = []
    for key in set(old) | set(new):
        if key in skip:
            continue
        if (key in old) != (key in new):
            keys.append(key)
        elif _attr_value(old, key, strip_data_patcher) != _attr_value(new, key, strip_data_patcher):
            keys.append(key)
    return tuple(sorted(keys))


def _data_patcher(box: dict) -> bool:
    """True when the box's embedded patcher lives under data.patcher (mc.gen~)."""
    return not isinstance(box.get("patcher"), dict) and inner_patcher(box) is not None


def _inner_count(inner: dict) -> int:
    boxes = inner.get("boxes")
    return len(boxes) if isinstance(boxes, list) else 0


def _midpoints(pl: dict):
    mids = pl.get("midpoints")
    if isinstance(mids, list) and mids:
        return tuple(mids)
    return None


def _diff_level(path: tuple, where: str, old_p: dict, new_p: dict,
                entries: list, children: list) -> None:
    """Append one patcher level's entries; collect ``children`` to descend."""
    old_boxes = _boxes(old_p)
    new_boxes = _boxes(new_p)
    old_map = dict(old_boxes)
    new_ids = {box_id for box_id, _ in new_boxes}
    label_count = Counter(box_label(box) for _, box in new_boxes)

    def add(kind, box_id, label, old=None, new=None):
        entries.append(DiffEntry(kind, path, where, box_id, label, old, new))

    for box_id, nb in new_boxes:
        label = _truncate(_display(nb), _LABEL_MAX)
        ob = old_map.get(box_id)
        if ob is None:
            add("box_added", box_id, label, None, _xy(nb))
            continue
        orect, nrect = _rect(ob), _rect(nb)
        if orect is not None and nrect is not None:
            if (orect[0], orect[1]) != (nrect[0], nrect[1]):
                add("moved", box_id, label, (orect[0], orect[1]), (nrect[0], nrect[1]))
            if (orect[2], orect[3]) != (nrect[2], nrect[3]):
                add("resized", box_id, label, (orect[2], orect[3]), (nrect[2], nrect[3]))
        otext, ntext = _display(ob), _display(nb)
        if otext != ntext:
            add("text", box_id, label, otext, ntext)
        o_inner, n_inner = inner_patcher(ob), inner_patcher(nb)
        strip = (
            o_inner is not None and n_inner is not None
            and _data_patcher(ob) and _data_patcher(nb)
        )
        keys = _changed_keys(ob, nb, _STRUCTURAL_KEYS, strip)
        if keys:
            add("attrs", box_id, label, None, keys)
        opres, npres = _presentation(ob), _presentation(nb)
        if opres != npres:
            add("presentation", box_id, label, opres, npres)
        if o_inner is None and n_inner is not None:
            add("subpatcher_added", box_id, label, None, _inner_count(n_inner))
        elif o_inner is not None and n_inner is None:
            add("subpatcher_removed", box_id, label, _inner_count(o_inner), None)
        elif o_inner is not None and n_inner is not None:
            seg = box_label(nb)
            if label_count[seg] > 1:
                seg = f"{seg} ({box_id})"
            children.append((path + (box_id,), f"{where}{seg}/", o_inner, n_inner))

    for box_id, ob in old_boxes:
        if box_id not in new_ids:
            add("box_removed", box_id, _truncate(_display(ob), _LABEL_MAX))

    old_cords = _cords(old_p)
    new_cords = _cords(new_p)
    old_count = Counter(k for k, _ in old_cords)
    new_count = Counter(k for k, _ in new_cords)
    added = new_count - old_count
    removed = old_count - new_count
    for key, _ in new_cords:
        if added.get(key):
            added[key] -= 1
            add("cord_added", None, _cord_label(key), None, key)
    for key, _ in old_cords:
        if removed.get(key):
            removed[key] -= 1
            add("cord_removed", None, _cord_label(key), key, None)
    old_first: dict = {}
    for key, pl in old_cords:
        old_first.setdefault(key, pl)
    seen = set()
    for key, pl in new_cords:
        if key in seen or key not in old_first:
            continue
        seen.add(key)
        omid, nmid = _midpoints(old_first[key]), _midpoints(pl)
        if omid != nmid:
            add("cord_rerouted", None, _cord_label(key), omid, nmid)

    props = _changed_keys(old_p, new_p, frozenset({"boxes", "lines"}))
    if props:
        add("props", None, "patcher", None, props)

    old_order = tuple(box_id for box_id, _ in old_boxes if box_id in new_ids)
    new_order = tuple(box_id for box_id, _ in new_boxes if box_id in old_map)
    if old_order != new_order:
        add("zorder", None, "z-order", old_order, new_order)


def diff_patch_dicts(old: dict, new: dict) -> PatchDiff:
    """The changes from *old* to *new* (both ``{"patcher": {...}}`` dicts).

    Entries come level by level, depth first in new-side box order; within
    a level: boxes in new-side order (added and changed), removed boxes in
    old order, cords, props, z-order.

    Raises:
        ValueError: when a side lacks a ``"patcher"`` dict.
    """
    old_p = _patcher_of(old, "old")
    new_p = _patcher_of(new, "new")
    entries: list = []
    stack = [((), "", old_p, new_p)]
    while stack:
        path, where, o, n = stack.pop()
        children: list = []
        _diff_level(path, where, o, n, entries, children)
        stack.extend(reversed(children))
    return PatchDiff(entries)
