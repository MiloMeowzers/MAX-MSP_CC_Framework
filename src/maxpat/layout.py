"""Row-based layout engine with component grouping and midpoint generation.

Positions MAX objects in a patcher for readable top-to-bottom signal flow:
1. Connected component detection to separate independent signal chains
2. Kahn's algorithm (topological sort by levels) to assign boxes to rows
3. Row-based layout: levels flow top-to-bottom, objects spread horizontally
4. Within-row ordering by parent position to minimize cable crossings
5. UI control objects grouped in a band above their target, left to right
   by inlet with gutters; each row box reserves a footprint for its band
   (Q27 / F2)
6. Disconnected objects (bpatchers, presentation-only) placed to the right,
   or in a new band below once the ~1600 px width cap is reached; rows and
   components wrap at the same cap (Q27 / F5)
7. Midpoint generation for all cable types:
   a. Horizontal offset cables get L-shaped routing at the vertical midpoint
   b. Upward-flowing cables (init sections) get right-edge bus routing
   c. Parallel bus cables are spaced apart to avoid visual overlap
8. Auto-sizing patcher rect to fit all content including bus routes
9. Presentation mode grid layout for UI objects (running x offset, rows
   advance by their tallest box; Q27 / F5)

Widths and heights come from ``sizing.rendered_rect`` (the geometry the
overlap critic and add_box share). apply_layout refuses MAX-saved or
>120-box patchers unless forced (LayoutRefusedError), never re-lays out an
embedded bpatcher face, and gives a status outlet no overlay companion
(Q27 / F1, F4, F5).

Implements PAT-06 (top-to-bottom signal flow) and PAT-07 (readable spacing).
"""

from __future__ import annotations

import math
from collections import defaultdict, deque
from typing import TYPE_CHECKING

from src.maxpat.defaults import (
    V_SPACING,
    H_GUTTER,
    HORIZONTAL_THRESHOLD,
    UPWARD_BUS_THRESHOLD,
    BUS_MARGIN,
    BUS_SPACING,
    PATCHER_PADDING,
    LAYOUT_MAX_BOXES,
    LayoutOptions,
)
from src.maxpat.sizing import is_max_saved, rendered_rect

if TYPE_CHECKING:
    from src.maxpat.patcher import Box, Patcher

# UI control object names that should be positioned above their targets
_UI_CONTROL_NAMES = frozenset({
    "toggle", "slider", "dial", "number", "flonum",
    "rslider", "button", "multislider", "kslider",
    "nslider", "led", "radiogroup", "umenu",
    "live.dial", "live.slider", "live.numbox",
    "live.toggle", "live.button",
})

# Companion objects placed beside their parent (monitoring/display sinks)
_COMPANION_NAMES = frozenset({
    "meter~", "levelmeter~", "scope~", "number~", "spectroscope~",
})

# Role-driven companion mapping (Phase 31 LAYOUT-03, D-14).
# Consulted FIRST in `_identify_companions`; falls through to
# `_COMPANION_NAMES` when `db.get_signal_role(name, outlet)` returns None
# (unaudited outlet, Phase 28 D-02). Augments -- does NOT replace --
# `_COMPANION_NAMES` (D-13). Six keys verbatim per D-14.
_ROLE_COMPANION_MAP: dict[str, dict[str, str | None]] = {
    "audio":   {"companion": "meter~", "placement": "right"},
    # Q27 / F1: no status overlay -- copying the source rect onto a flonum
    # hid the source; add_overlay_readout is the explicit overlay path.
    "status":  {"companion": None,     "placement": None},
    "trigger": {"companion": None,     "placement": None},
    "float":   {"companion": None,     "placement": None},
    "data":    {"companion": None,     "placement": None},
    "list":    {"companion": None,     "placement": None},
}

# Gap between a parent and its companion object placed beside it
_COMPANION_GAP = 5.0

# Starting position for the first row and first object
_START_X = 30.0
_START_Y = 30.0

# Gap between independent components laid out side by side
_COMPONENT_GAP = 40.0

# Margin from box edge to first/last inlet/outlet center
_IO_MARGIN = 7.0


class LayoutRefusedError(ValueError):
    """apply_layout refused to lay out a MAX-saved or large patcher (Q27 / F5).

    Global auto-layout on a user-arranged patch makes it unusably wide
    (ji-harmonizer 1,968 -> 10,203 px). Raised before any box moves; pass
    ``force=True`` to lay it out anyway.
    """


def _refusal_reason(patcher: Patcher) -> str | None:
    """Why *patcher* (its own boxes only) must not be auto-laid out, or None."""
    if is_max_saved(patcher.props):
        app = patcher.props.get("appversion") or {}
        return "the patch was saved by MAX %s.%s.%s" % (
            app.get("major"), app.get("minor"), app.get("revision"))
    n = len(patcher.boxes)
    if n > LAYOUT_MAX_BOXES:
        return "the patch has %d boxes (limit %d)" % (n, LAYOUT_MAX_BOXES)
    return None


def _layout_children(patcher: Patcher) -> list[Patcher]:
    """Inner patchers apply_layout recurses into: not embedded bpatcher
    faces (Q27 / F4), not empty ones."""
    out = []
    for box in patcher.boxes:
        inner = box._inner_patcher
        if inner is None or not inner.boxes:
            continue
        if box.maxclass == "bpatcher" or box.name == "bpatcher":
            continue
        out.append(inner)
    return out


def _check_layout_allowed(patcher: Patcher) -> None:
    """Raise LayoutRefusedError if *patcher* or any inner patcher the
    recursion would visit is MAX-saved or too large. Mutates nothing."""
    reason = _refusal_reason(patcher)
    if reason is not None:
        raise LayoutRefusedError(
            f"apply_layout refused: {reason}. Global auto-layout makes "
            "MAX-saved or large patches unusably wide; make local fixes "
            "(finalize_patch(patcher, is_new=False)) or pass force=True."
        )
    for inner in _layout_children(patcher):
        _check_layout_allowed(inner)


def _ceil_grid(v: float, grid: float | None) -> float:
    """Round *v* up to the grid (no-op when grid is None or <= 0)."""
    if not grid or grid <= 0:
        return v
    return math.ceil(v / grid - 1e-9) * grid


def _floor_grid(v: float, grid: float | None) -> float:
    """Round *v* down to the grid (no-op when grid is None or <= 0)."""
    if not grid or grid <= 0:
        return v
    return math.floor(v / grid + 1e-9) * grid


def _rdims(box: Box) -> tuple[float, float]:
    """Rendered (width, height) of a box, falling back to its stored rect."""
    r = rendered_rect(box)
    if r is None:
        return (box.patching_rect[2], box.patching_rect[3])
    return (r[2], r[3])


def _block_bbox(boxes: list[Box]) -> tuple[float, float, float, float]:
    """(left, top, right, bottom) over the rendered rects of *boxes*."""
    left = top = math.inf
    right = bottom = -math.inf
    for b in boxes:
        w, h = _rdims(b)
        x, y = b.patching_rect[0], b.patching_rect[1]
        left = min(left, x)
        top = min(top, y)
        right = max(right, x + w)
        bottom = max(bottom, y + h)
    return left, top, right, bottom


def _translate(boxes: list[Box], dx: float, dy: float) -> None:
    for b in boxes:
        b.patching_rect[0] += dx
        b.patching_rect[1] += dy


# ---------------------------------------------------------------------------
# Decorations: panels, headers and labels move with their boxes (Q27 / F3)
# ---------------------------------------------------------------------------

# Largest rendered-rect gap at which a label/header/step marker belongs to a
# content box (rider) rather than floating free.
_ANCHOR_GAP = 40.0


def _rrect(box: Box) -> list[float] | None:
    """Rendered rect of a Box (layout passes max_saved=False: it only runs on
    generator-written patches unless forced)."""
    return rendered_rect(box)


def _rect_center_in(rect: list[float], outer: list[float]) -> bool:
    cx = rect[0] + rect[2] * 0.5
    cy = rect[1] + rect[3] * 0.5
    return (outer[0] <= cx <= outer[0] + outer[2]
            and outer[1] <= cy <= outer[1] + outer[3])


def _axis_gaps(a: list[float], b: list[float]) -> tuple[float, float]:
    """(horizontal gap, vertical gap) between two rects, 0 when overlapping."""
    hg = max(0.0, b[0] - (a[0] + a[2]), a[0] - (b[0] + b[2]))
    vg = max(0.0, b[1] - (a[1] + a[3]), a[1] - (b[1] + b[3]))
    return hg, vg


class _Decorations:
    """Pre-layout anchors of a patcher's decorations (Q27 / F3).

    Decorations are cordless panels, untargeted comments (labels, headers)
    and other ``background: 1`` boxes (step markers). Each non-panel
    decoration rides the nearest content box within ``_ANCHOR_GAP`` px
    (``box_riders``), else the smallest membered panel its center lies in
    (``panel_riders``); a panel with members is refit around them plus its
    box riders, keeping its original pads. Everything else stays an
    unanchored decoration for the disconnected placement.
    """

    def __init__(self) -> None:
        self.box_riders: dict[str, list[tuple[Box, float, float]]] = {}
        self.panel_riders: dict[str, list[tuple[Box, float, float]]] = {}
        # (panel, member ids, tracked boxes, pads (left, top, right, bottom))
        self.panels: list[tuple[Box, set[str], list[Box], tuple[float, float, float, float]]] = []
        self.anchored: set[str] = set()

    def riders_of(self, box_id: str) -> list[tuple[Box, float, float]]:
        return self.box_riders.get(box_id, [])


def _capture_decorations(patcher: Patcher) -> _Decorations:
    """Record every decoration's anchor and offset before layout moves boxes."""
    deco = _Decorations()
    boxes = patcher.boxes
    ids = {b.id for b in boxes}
    corded: set[str] = set()
    for line in patcher.lines:
        if line.source_id in ids and line.dest_id in ids:
            corded.add(line.source_id)
            corded.add(line.dest_id)

    def is_decoration(b: Box) -> bool:
        if b.id in corded:
            return False
        if b.maxclass == "panel":
            return True
        if b.maxclass == "comment" and not getattr(b, "target_id", None):
            return True
        return b.extra_attrs.get("background") == 1

    decos = [b for b in boxes if is_decoration(b)]
    deco_ids = {b.id for b in decos}
    content = []
    for b in boxes:
        if b.id in deco_ids or b.maxclass == "comment":
            continue
        r = _rrect(b)
        if r is not None:
            content.append((b, r))

    # Panel members: content boxes whose rendered center lies inside.
    panels = []
    for b in decos:
        if b.maxclass != "panel":
            continue
        rect = b.patching_rect
        if _rrect(b) is None:
            continue
        members = [c for c, r in content if _rect_center_in(r, rect)]
        if members:
            panels.append((b, members))

    # Box anchors, else panel anchors, for non-panel decorations.
    for d in decos:
        if d.maxclass == "panel":
            continue
        dr = _rrect(d)
        if dr is None:
            continue
        best = None
        best_key = None
        for idx, (c, cr) in enumerate(content):
            hg, vg = _axis_gaps(dr, cr)
            key = (max(hg, vg), min(hg, vg), idx)
            if best_key is None or key < best_key:
                best, best_key = c, key
        if best is not None and best_key[0] <= _ANCHOR_GAP:
            deco.box_riders.setdefault(best.id, []).append(
                (d, d.patching_rect[0] - best.patching_rect[0],
                 d.patching_rect[1] - best.patching_rect[1]))
            deco.anchored.add(d.id)
            continue
        holders = [p for p, _ in panels if _rect_center_in(dr, p.patching_rect)]
        if holders:
            p = min(holders, key=lambda q: q.patching_rect[2] * q.patching_rect[3])
            deco.panel_riders.setdefault(p.id, []).append(
                (d, d.patching_rect[0] - p.patching_rect[0],
                 d.patching_rect[1] - p.patching_rect[1]))
            deco.anchored.add(d.id)

    # Membered panels: tracked set = members + their box riders.
    for p, members in panels:
        tracked = list(members)
        for m in members:
            tracked.extend(r for r, _, _ in deco.riders_of(m.id))
        left, top, right, bottom = _block_bbox(tracked)
        px, py, pw, ph = p.patching_rect[:4]
        pads = (max(0.0, left - px), max(0.0, top - py),
                max(0.0, px + pw - right), max(0.0, py + ph - bottom))
        deco.panels.append((p, {m.id for m in members}, tracked, pads))
        deco.anchored.add(p.id)
    return deco


def _place_decorations(
    deco: _Decorations,
    box_map: dict[str, Box],
    within: set[str] | None = None,
) -> list[Box]:
    """Place riders at anchor + offset and refit panels around their
    tracked set + pads. Idempotent; never grid-snapped.

    *within* limits the pass to riders whose anchor is in it and panels
    whose members all are (the provisional per-component pass). Returns the
    decorations placed.
    """
    placed: list[Box] = []
    for anchor_id, riders in deco.box_riders.items():
        if within is not None and anchor_id not in within:
            continue
        anchor = box_map.get(anchor_id)
        if anchor is None:
            continue
        for rider, dx, dy in riders:
            rider.patching_rect[0] = anchor.patching_rect[0] + dx
            rider.patching_rect[1] = anchor.patching_rect[1] + dy
            placed.append(rider)
    for panel, member_ids, tracked, pads in deco.panels:
        if within is not None and not member_ids <= within:
            continue
        left, top, right, bottom = _block_bbox(tracked)
        pl, pt, pr, pb = pads
        panel.patching_rect[0] = left - pl
        panel.patching_rect[1] = top - pt
        panel.patching_rect[2] = (right - left) + pl + pr
        panel.patching_rect[3] = (bottom - top) + pt + pb
        placed.append(panel)
        for rider, dx, dy in deco.panel_riders.get(panel.id, []):
            rider.patching_rect[0] = panel.patching_rect[0] + dx
            rider.patching_rect[1] = panel.patching_rect[1] + dy
            placed.append(rider)
    return placed


def _clear_negative_coords(patcher: Patcher, grid: float | None) -> None:
    """Safety net: translate every box (and existing midpoint) right/down so
    no box starts at a negative coordinate."""
    if not patcher.boxes:
        return
    min_x = min(b.patching_rect[0] for b in patcher.boxes)
    min_y = min(b.patching_rect[1] for b in patcher.boxes)
    dx = _ceil_grid(-min_x, grid) if min_x < 0 else 0.0
    dy = _ceil_grid(-min_y, grid) if min_y < 0 else 0.0
    if not dx and not dy:
        return
    _translate(patcher.boxes, dx, dy)
    for line in patcher.lines:
        mids = getattr(line, "midpoints", None)
        if mids:
            line.midpoints = [
                v + (dx if i % 2 == 0 else dy) for i, v in enumerate(mids)
            ]


def apply_layout(
    patcher: Patcher,
    options: LayoutOptions | None = None,
    *,
    force: bool = False,
) -> None:
    """Position all boxes using row-based topological layout with component grouping.

    Signal flow is top-to-bottom: topological depth maps to y-position.
    Independent signal chains are placed side by side as vertical groups,
    wrapping into a new band below once a block would pass
    ``30 + options.max_width`` (~1600 px); rows wrap at the same cap.
    UI controls feeding one object sit in a band above it, ordered by inlet.
    Disconnected objects (bpatchers, presentation-only) go to the right, or
    into a new band when they would not fit under the cap.
    Backward-direction cables get midpoints for clean segmented routing.
    Inner patchers are laid out recursively, except embedded bpatcher faces
    (their inner layout IS the face).

    Refusal guard (Q27 / F5): unless *force* is True, raises
    :class:`LayoutRefusedError` (a ValueError) before moving any box when
    this patcher or an inner patcher the recursion would visit was saved by
    MAX (``sizing.is_max_saved``) or has more than ``LAYOUT_MAX_BOXES``
    (120) boxes. Global layout of a user-arranged patch destroys it; use
    ``finalize_patch(patcher, is_new=False)`` for edits.

    Args:
        patcher: A Patcher instance containing boxes and lines.
        options: Optional layout parameters. Uses LayoutOptions defaults if None.
        force: Lay out a MAX-saved or large patcher anyway.

    Raises:
        LayoutRefusedError: the guard refused (nothing was changed).
    """
    if options is None:
        options = LayoutOptions()

    if not force:
        _check_layout_allowed(patcher)

    if not patcher.boxes:
        return

    # MAX resolves a subpatcher's port indices from the x-order of the
    # inlet/outlet boxes inside it (get_inlets()/get_outlets() sort by x to
    # match). Capture the pre-layout x-rank of each port box so repositioning
    # cannot silently remap the parent patcher's connection indices; the rank
    # is restored after all positioning passes below.
    port_order: dict[str, list[Box]] = {}
    for port_class in ("inlet", "outlet"):
        ports = [b for b in patcher.boxes if b.maxclass == port_class]
        if len(ports) > 1:
            port_order[port_class] = sorted(
                ports, key=lambda b: b.patching_rect[0]
            )

    # Decorations (panels, headers, labels, step markers) keep their
    # pre-layout anchors and offsets (Q27 / F3).
    deco = _capture_decorations(patcher)
    box_map = {b.id: b for b in patcher.boxes}

    # Build adjacency graph from patcher.lines
    adj, in_degree, reverse_adj = _build_graph(patcher.boxes, patcher.lines)

    # Separate connected components from disconnected objects; anchored
    # decorations are placed with their anchors, not in the column.
    components, disconnected = _find_components(patcher.boxes, adj)
    disconnected = [b for b in disconnected if b.id not in deco.anchored]

    grid = options.grid_size if options.grid_snap else None
    cap_right = _START_X + options.max_width

    # Layout each component as a vertical group (top-to-bottom rows),
    # side by side in bands no wider than the cap (Q27 / F5).
    cursor_x = _START_X
    band_top = _START_Y
    band_bottom = _START_Y
    for component_boxes in components:
        # Filter graph to this component
        comp_ids = {b.id for b in component_boxes}
        comp_adj = {
            k: [v for v in vs if v in comp_ids]
            for k, vs in adj.items() if k in comp_ids
        }
        comp_in_degree = {k: v for k, v in in_degree.items() if k in comp_ids}

        # Topological sort into levels (rows)
        rows = _topological_levels(component_boxes, comp_adj, comp_in_degree)
        if not rows:
            continue

        # Identify and extract UI controls (placed in their target's band)
        ui_controls = _identify_ui_controls(component_boxes, patcher.lines, rows)
        for box_id in ui_controls:
            for row in rows:
                row[:] = [b for b in row if b.id != box_id]
        rows = [r for r in rows if r]
        if not rows:
            continue

        # Identify and extract companion objects (meter~, etc.)
        # Pass db so role-driven dispatch (Phase 31 LAYOUT-03, D-13) can
        # consult `_ROLE_COMPANION_MAP`. Recursive `apply_layout` calls
        # below pass `box._inner_patcher` whose `.db` was set in
        # `add_subpatcher`, so the recursion preserves db threading
        # automatically (Pitfall 3).
        companions = _identify_companions(
            component_boxes, patcher.lines, rows, db=patcher.db,
        )
        for box_id in companions:
            for row in rows:
                row[:] = [b for b in row if b.id != box_id]
        rows = [r for r in rows if r]
        if not rows:
            continue

        # Position this component (rows + control bands) at cursor_x
        start_x = _ceil_grid(cursor_x, grid)
        _position_component(
            rows, start_x, band_top, reverse_adj, patcher.boxes,
            patcher.lines, options, controls=ui_controls, deco=deco,
        )

        # Position companion objects beside their parents
        _place_companions(patcher, companions)

        # Provisional decorations: this component's riders and the panels
        # whose members all lie in it. The block includes them; shift it
        # right/down if they reach left of cursor_x or above the band top.
        block_decos = _place_decorations(deco, box_map, within=comp_ids)
        left, top, right, bottom = _block_bbox(component_boxes + block_decos)
        shift_x = _ceil_grid(cursor_x - left, grid) if left < cursor_x else 0.0
        shift_y = _ceil_grid(band_top - top, grid) if top < band_top else 0.0
        if shift_x or shift_y:
            _translate(component_boxes, shift_x, shift_y)
            block_decos = _place_decorations(deco, box_map, within=comp_ids)
            left, top, right, bottom = _block_bbox(component_boxes + block_decos)

        # Component banding: a block that passes the cap moves to a new
        # band below everything placed so far.
        if right > cap_right and cursor_x > _START_X:
            new_top = _ceil_grid(band_bottom + _COMPONENT_GAP, grid)
            _translate(component_boxes, -_floor_grid(left - _START_X, grid),
                       new_top - band_top)
            band_top = new_top
            block_decos = _place_decorations(deco, box_map, within=comp_ids)
            left, top, right, bottom = _block_bbox(component_boxes + block_decos)
        band_bottom = max(band_bottom, bottom)
        cursor_x = right + _COMPONENT_GAP

    # Place disconnected objects to the right of all components, or in a
    # new band when their widest box would pass the cap.
    if disconnected:
        widest = 0.0
        for b in disconnected:
            fp = _footprint(b, None, 0.0, deco)
            widest = max(widest, fp.right - fp.left)
        if cursor_x + widest <= cap_right:
            disc_x, disc_y = cursor_x, band_top
        else:
            disc_x, disc_y = _START_X, band_bottom + _COMPONENT_GAP
        _position_disconnected(disconnected, disc_x, disc_y,
                               cap_right=cap_right, deco=deco)

    # Place associated comments near their targets
    _place_associated_comments(patcher.boxes, options.comment_gap)

    # Grid snap as final pass (after all positioning, before midpoints)
    if options.grid_snap:
        _snap_to_grid(patcher.boxes, options.grid_size)

    # Restore pre-layout x-rank of inlet/outlet boxes: give the k-th port
    # (by original rank) the k-th smallest post-layout x, kept strictly
    # increasing so MAX's x-order stays unambiguous.
    for ports in port_order.values():
        xs = sorted(b.patching_rect[0] for b in ports)
        for i in range(1, len(xs)):
            if xs[i] <= xs[i - 1]:
                xs[i] = xs[i - 1] + options.grid_size
        for b, x in zip(ports, xs):
            b.patching_rect[0] = x

    # Final decoration pass against final positions (exact offsets, never
    # snapped), then make sure nothing starts at a negative coordinate.
    _place_decorations(deco, box_map)
    _clear_negative_coords(patcher, grid)

    # Generate midpoints for all cables needing segmented routing
    _generate_midpoints(patcher)

    # Auto-size patcher rect to fit content and bus routing
    if not patcher._is_subpatcher:
        _auto_size_patcher_rect(patcher, options)

    # Recursively layout inner patchers (subpatchers, gen~); embedded
    # bpatcher faces keep their arrangement (Q27 / F4).
    for inner in _layout_children(patcher):
        apply_layout(inner, options, force=force)

    # Apply presentation mode layout if any boxes have presentation=True
    _apply_presentation_layout(patcher.boxes)


# ---------------------------------------------------------------------------
# Graph building
# ---------------------------------------------------------------------------


def _build_graph(
    boxes: list[Box],
    lines: list,
) -> tuple[dict[str, list[str]], dict[str, int], dict[str, list[str]]]:
    """Build adjacency, in-degree, and reverse-adjacency dicts from lines.

    Returns:
        (adjacency, in_degree, reverse_adjacency) tuple.
    """
    all_ids = {b.id for b in boxes}
    adj: dict[str, list[str]] = defaultdict(list)
    reverse_adj: dict[str, list[str]] = defaultdict(list)
    in_degree: dict[str, int] = {b.id: 0 for b in boxes}

    for line in lines:
        src = line.source_id
        dst = line.dest_id
        if src in all_ids and dst in all_ids:
            # Avoid duplicate edges
            if dst not in adj[src]:
                adj[src].append(dst)
                in_degree[dst] = in_degree.get(dst, 0) + 1
                reverse_adj[dst].append(src)

    return dict(adj), in_degree, dict(reverse_adj)


# ---------------------------------------------------------------------------
# Connected components
# ---------------------------------------------------------------------------


def _find_components(
    boxes: list[Box],
    adj: dict[str, list[str]],
) -> tuple[list[list[Box]], list[Box]]:
    """Find connected components and disconnected objects.

    Uses undirected BFS to group connected boxes. Objects with no
    connections at all are returned separately as disconnected.

    Returns:
        (components, disconnected) where components is a list of Box lists
        sorted largest-first, and disconnected is isolated Box objects.
    """
    # Build undirected adjacency
    undirected: dict[str, set[str]] = defaultdict(set)
    for src, dsts in adj.items():
        for dst in dsts:
            undirected[src].add(dst)
            undirected[dst].add(src)

    box_map = {b.id: b for b in boxes}
    visited: set[str] = set()
    components: list[list[Box]] = []
    disconnected: list[Box] = []

    for box in boxes:
        if box.id in visited:
            continue
        if box.id not in undirected:
            disconnected.append(box)
            visited.add(box.id)
            continue

        # BFS from this box
        component_ids: list[str] = []
        queue = deque([box.id])
        while queue:
            node = queue.popleft()
            if node in visited:
                continue
            visited.add(node)
            component_ids.append(node)
            for neighbor in undirected.get(node, set()):
                if neighbor not in visited:
                    queue.append(neighbor)

        comp_boxes = [box_map[bid] for bid in component_ids if bid in box_map]
        if comp_boxes:
            components.append(comp_boxes)

    # Largest component first for primary placement
    components.sort(key=len, reverse=True)

    return components, disconnected


# ---------------------------------------------------------------------------
# Topological sort
# ---------------------------------------------------------------------------


def _topological_levels(
    boxes: list[Box],
    adj: dict[str, list[str]],
    in_degree: dict[str, int],
) -> list[list[Box]]:
    """Assign boxes to levels using Kahn's algorithm (BFS by depth).

    Each level becomes a row in the layout. Source nodes (in-degree 0)
    are in level 0 (top row).
    """
    box_map = {b.id: b for b in boxes}
    comp_ids = {b.id for b in boxes}

    queue = deque()
    for box in boxes:
        if in_degree.get(box.id, 0) == 0:
            queue.append(box.id)

    levels: list[list[Box]] = []
    visited: set[str] = set()
    work_in_degree = dict(in_degree)

    while queue:
        level: list[Box] = []
        next_queue: deque[str] = deque()

        while queue:
            node_id = queue.popleft()
            if node_id in visited:
                continue
            visited.add(node_id)
            if node_id in box_map:
                level.append(box_map[node_id])

            for neighbor_id in adj.get(node_id, []):
                if neighbor_id not in comp_ids:
                    continue
                work_in_degree[neighbor_id] = work_in_degree.get(neighbor_id, 0) - 1
                if work_in_degree[neighbor_id] == 0 and neighbor_id not in visited:
                    next_queue.append(neighbor_id)

        if level:
            levels.append(level)
        queue = next_queue

    # Handle any remaining (cycle participants)
    remaining = [b for b in boxes if b.id not in visited]
    if remaining:
        levels.append(remaining)

    return levels


# ---------------------------------------------------------------------------
# Component positioning (row-based, top-to-bottom)
# ---------------------------------------------------------------------------


class _Footprint:
    """Space a row box reserves, as offsets from its top-left (Q27 / F2).

    ``left`` <= 0 and ``right`` >= the box's rendered width bound it
    horizontally; ``above`` is the band height reserved over it (its
    control group), ``bottom`` its extent below its top edge.
    """

    __slots__ = ("left", "right", "above", "bottom")

    def __init__(self, left: float, right: float, above: float, bottom: float):
        self.left = left
        self.right = right
        self.above = above
        self.bottom = bottom


def _control_groups(
    controls: dict[str, tuple[Box, int]] | None,
    all_boxes: list[Box],
    options: LayoutOptions,
    deco: "_Decorations | None" = None,
) -> dict[str, list[tuple[Box, float, _Footprint]]]:
    """Group extracted UI controls by target: target id -> [(control, dx, fp)].

    Controls are ordered by destination inlet, then box-array order, and
    sit left to right from the target's x, each footprint starting at least
    ``h_gutter`` after the previous one's right edge (rounded up to the grid
    when grid_snap is on, so the final snap keeps gutters). A control's
    footprint is its rendered rect plus its riders (a label beside a dial
    widens the group; Q27 / F3).
    """
    if not controls:
        return {}
    grid = options.grid_size if options.grid_snap else None
    order = {b.id: i for i, b in enumerate(all_boxes)}
    box_map = {b.id: b for b in all_boxes}
    by_target: dict[str, list[tuple[int, int, Box]]] = {}
    for ctrl_id, (target, inlet) in controls.items():
        ctrl = box_map.get(ctrl_id)
        if ctrl is None:
            continue
        by_target.setdefault(target.id, []).append(
            (inlet, order.get(ctrl_id, 0), ctrl))
    groups: dict[str, list[tuple[Box, float, _Footprint]]] = {}
    for target_id, entries in by_target.items():
        entries.sort(key=lambda e: (e[0], e[1]))
        placed: list[tuple[Box, float, _Footprint]] = []
        next_left = 0.0
        for _, _, ctrl in entries:
            fp = _footprint(ctrl, None, 0.0, deco)
            dx = _ceil_grid(next_left - fp.left, grid)
            placed.append((ctrl, dx, fp))
            next_left = dx + fp.right + options.h_gutter
        groups[target_id] = placed
    return groups


def _footprint(
    box: Box,
    group: list[tuple[Box, float, _Footprint]] | None,
    gap: float,
    deco: "_Decorations | None" = None,
) -> _Footprint:
    """The footprint of a row box: its rendered rect, widened and raised by
    its control group (W = group width, band = tallest control + gap) and
    extended by its riders' offset rects (labels, headers; Q27 / F3)."""
    w, h = _rdims(box)
    fp = _Footprint(0.0, w, 0.0, h)
    if group:
        fp.right = max(fp.right, max(dx + cfp.right for _, dx, cfp in group))
        tallest = max(cfp.above + cfp.bottom for _, _, cfp in group)
        fp.above = max(fp.above, tallest + gap)
    if deco is not None:
        for rider, dx, dy in deco.riders_of(box.id):
            rw, rh = _rdims(rider)
            fp.left = min(fp.left, dx)
            fp.right = max(fp.right, dx + rw)
            fp.above = max(fp.above, -dy)
            fp.bottom = max(fp.bottom, dy + rh)
    return fp


def _position_component(
    rows: list[list[Box]],
    start_x: float,
    start_y: float,
    reverse_adj: dict[str, list[str]],
    all_boxes: list[Box],
    lines: list,
    options: LayoutOptions,
    controls: dict[str, tuple[Box, int]] | None = None,
    deco: "_Decorations | None" = None,
) -> float:
    """Position boxes in a component as top-to-bottom rows.

    Each topological level is a row. Within each row (except the first),
    objects are sorted by the average x-position of their parents to
    minimize cable crossings.

    When options.inlet_align is True, child objects are positioned so their
    destination inlet X aligns under the parent's source outlet X (straighter
    cables). Otherwise, child center-x is aligned under parent center-x.

    Every row box reserves a footprint (Q27 / F2): its rendered rect plus
    the band of UI controls feeding it (*controls*: control id -> (target,
    inlet)), which sit above it left to right by inlet, and the offset
    rects of its riders (*deco*: labels and headers anchored to it). Slots keep
    ``h_gutter`` apart; a slot that would end past ``start_x +
    options.max_width`` opens a new line packed from start_x (a slot wider
    than the cap sits alone on its line). Each line's boxes share one y
    below the line's tallest band.

    Returns the total width of the component.
    """
    if not rows:
        return 0.0

    box_map = {b.id: b for b in all_boxes}
    grid = options.grid_size if options.grid_snap else None
    gap = options.v_spacing * 0.5
    cap = start_x + options.max_width
    groups = _control_groups(controls, all_boxes, options, deco)

    cursor_y = start_y
    for row_idx, row in enumerate(rows):
        if row_idx > 0 and len(row) > 1:
            # Sort by parent x to reduce crossings
            _sort_row_by_parent_x(row, reverse_adj, box_map)

        # Ideal x per box (row 0 packs left to right). Computed before any
        # box of this row moves, as the per-box pass did.
        ideals: list[float | None] = []
        for box in row:
            if row_idx == 0:
                ideals.append(None)
            elif options.inlet_align:
                # Inlet-under-outlet alignment for straighter cables
                ideals.append(_target_x_for_inlet_align(
                    box, reverse_adj, box_map, lines,
                ))
            else:
                # Legacy center-under-center
                target_x = _parent_center_x(box, reverse_adj, box_map)
                ideals.append(target_x - _rdims(box)[0] * 0.5)

        # Pack slots into lines, wrapping at the cap.
        row_lines: list[list[tuple[Box, _Footprint, float]]] = []
        current: list[tuple[Box, _Footprint, float]] = []
        prev_right: float | None = None
        packing = False
        for box, ideal in zip(row, ideals):
            fp = _footprint(box, groups.get(box.id), gap, deco)
            if ideal is None or packing:
                slot_left = start_x if prev_right is None else prev_right + options.h_gutter
            else:
                slot_left = max(ideal + fp.left, start_x)
                if prev_right is not None:
                    slot_left = max(slot_left, prev_right + options.h_gutter)
            x = _ceil_grid(slot_left - fp.left, grid)
            if x + fp.right > cap:
                if current:
                    row_lines.append(current)
                    current = []
                    packing = True
                    x = _ceil_grid(start_x - fp.left, grid)
                else:
                    # Alone on its line: pull it back under the cap when
                    # it fits, else it starts at start_x.
                    x = max(_ceil_grid(start_x - fp.left, grid),
                            _floor_grid(cap - fp.right, grid))
            current.append((box, fp, x))
            prev_right = x + fp.right
        if current:
            row_lines.append(current)

        for line in row_lines:
            band = max(fp.above for _, fp, _ in line)
            y = cursor_y + band
            if band > 0:
                y = _ceil_grid(y, grid)
            height = max(fp.bottom for _, fp, _ in line)
            for box, _, x in line:
                box.patching_rect[0] = x
                box.patching_rect[1] = y
            # Adaptive gap: add proportional spacing for tall elements (bpatchers)
            next_gap = options.v_spacing
            if height > 100:
                next_gap += (height - 100) * 0.1
            cursor_y = y + height + next_gap

    # Controls sit in their target's band, footprint bottoms gap px above it.
    for target_id, group in groups.items():
        target = box_map.get(target_id)
        if target is None:
            continue
        tx, ty = target.patching_rect[0], target.patching_rect[1]
        for ctrl, dx, cfp in group:
            ctrl.patching_rect[0] = tx + dx
            ctrl.patching_rect[1] = ty - gap - cfp.bottom

    placed = [b for row in rows for b in row]
    placed.extend(c for group in groups.values() for c, _, _ in group)
    _, _, right, _ = _block_bbox(placed)
    return right - start_x


def _target_x_for_inlet_align(
    child: Box,
    reverse_adj: dict[str, list[str]],
    box_map: dict[str, Box],
    lines: list,
) -> float:
    """Compute ideal x for child so its inlet aligns under parent's outlet.

    For each parent connection, finds the specific outlet X and inlet X,
    then computes what child.x should be for alignment. When multiple
    parents exist, averages the target positions.
    """
    targets: list[float] = []
    for line in lines:
        if line.dest_id == child.id:
            parent = box_map.get(line.source_id)
            if parent and parent.patching_rect[1] < child.patching_rect[1]:
                outlet_x_pos = _outlet_x(parent, line.source_outlet)
                inlet_x_pos = _inlet_x(child, line.dest_inlet)
                inlet_offset = inlet_x_pos - child.patching_rect[0]
                ideal_child_x = outlet_x_pos - inlet_offset
                targets.append(ideal_child_x)

    if targets:
        return sum(targets) / len(targets)

    # Fallback to center-under-parent-center
    return _parent_center_x(child, reverse_adj, box_map) - child.patching_rect[2] * 0.5


def _parent_center_x(
    box: Box,
    reverse_adj: dict[str, list[str]],
    box_map: dict[str, Box],
) -> float:
    """Compute the average center-x of a box's parents."""
    parents = reverse_adj.get(box.id, [])
    if not parents:
        return box.patching_rect[0] + box.patching_rect[2] * 0.5
    cxs = []
    for pid in parents:
        parent = box_map.get(pid)
        if parent:
            cxs.append(parent.patching_rect[0] + parent.patching_rect[2] * 0.5)
    return sum(cxs) / len(cxs) if cxs else 0.0


def _sort_row_by_parent_x(
    row: list[Box],
    reverse_adj: dict[str, list[str]],
    box_map: dict[str, Box],
) -> None:
    """Sort objects in a row by the average x-position of their parents.

    Parents in previous rows are already positioned, so their patching_rect
    x values are valid. This reduces cable crossings.
    """
    def parent_avg_x(box: Box) -> float:
        parents = reverse_adj.get(box.id, [])
        if not parents:
            return 0.0
        xs = []
        for pid in parents:
            parent = box_map.get(pid)
            if parent:
                xs.append(parent.patching_rect[0])
        return sum(xs) / len(xs) if xs else 0.0

    row.sort(key=parent_avg_x)


# ---------------------------------------------------------------------------
# UI control identification and positioning
# ---------------------------------------------------------------------------


def _identify_ui_controls(
    boxes: list[Box],
    lines: list,
    rows: list[list[Box]],
) -> dict[str, tuple[Box, int]]:
    """Identify UI control objects that should be placed above their targets.

    A UI control qualifies if:
    1. Its name is in _UI_CONTROL_NAMES
    2. It connects to a target (first connection target used)
    3. The target is in the same or the next row
    4. The target is not itself a qualifying control (Q27 / F2): a control
       feeding a control stays a row box, so bands never stack.

    Returns:
        control id -> (target box, destination inlet of the first cord).
    """
    row_index: dict[str, int] = {}
    for r_idx, row in enumerate(rows):
        for b in row:
            row_index[b.id] = r_idx

    box_map = {b.id: b for b in boxes}

    ui_connections: dict[str, tuple[str, int]] = {}
    for line in lines:
        src = line.source_id
        if src not in ui_connections and src in box_map:
            src_box = box_map[src]
            if src_box.name in _UI_CONTROL_NAMES:
                ui_connections[src] = (line.dest_id, line.dest_inlet)

    result: dict[str, tuple[Box, int]] = {}
    for ui_id, (target_id, inlet) in ui_connections.items():
        if ui_id in row_index and target_id in row_index:
            ui_row = row_index[ui_id]
            target_row = row_index[target_id]
            if target_row == ui_row or target_row == ui_row + 1:
                if target_id in box_map:
                    result[ui_id] = (box_map[target_id], inlet)

    # A candidate whose target is a candidate stays in its row. Removal is
    # judged against the candidate set as it stood at the start of each
    # pass (order-independent); repeat until no candidate is removed.
    while True:
        drop = [ui_id for ui_id, (target, _) in result.items() if target.id in result]
        if not drop:
            break
        for ui_id in drop:
            del result[ui_id]

    return result


# ---------------------------------------------------------------------------
# Companion object identification and positioning (meter~, scope~, etc.)
# ---------------------------------------------------------------------------


def _identify_companions(
    boxes: list[Box],
    lines: list,
    rows: list[list[Box]],
    db=None,
) -> dict[str, tuple[Box, str]]:
    """Identify companion objects + their placement strategy.

    Returns a dict mapping each companion's id to a `(parent_box, placement)`
    tuple. `placement` is "right" (place the companion to the right of
    the parent); the role map's former "overlay" entry for status outlets
    was removed in Q27 / F1.

    Dispatch order (D-13 augment-don't-replace):
      Pass A -- role-driven via `_ROLE_COMPANION_MAP` consulting
        `db.get_signal_role(src.name, outlet)`. Outlets with curated roles
        whose downstream box matches the role's companion name are claimed
        as companions of the upstream source. Single-parent guard applies
        (matches Pass B's invariant) per WR-02 (Plan 31-07).
      Pass B -- legacy `_COMPANION_NAMES` heuristic for any companion-name
        boxes the role pass did not already claim. This catches both the
        unaudited-outlet case (db.get_signal_role returns None) and the
        no-db case (db=None for back-compat). Always emits placement="right".

    A legacy companion qualifies if:
    1. Its name is in `_COMPANION_NAMES` (e.g., meter~, scope~)
    2. It has exactly one incoming connection (a single parent)
    3. It is a display/monitoring sink

    Args:
        boxes: All boxes in the current patcher (or subpatcher).
        lines: All connection lines.
        rows: Row groupings produced by topological sort (unused; kept for
            signature stability with sibling identification helpers).
        db: ObjectDatabase; pass `patcher.db` to enable role-driven
            dispatch. When None, only the legacy heuristic runs.
    """
    box_map = {b.id: b for b in boxes}
    comp_ids = {b.id for b in boxes}

    # Count incoming connections per box (used by both passes)
    incoming: dict[str, list[str]] = {}
    for line in lines:
        if line.source_id in comp_ids and line.dest_id in comp_ids:
            incoming.setdefault(line.dest_id, []).append(line.source_id)

    result: dict[str, tuple[Box, str]] = {}

    # Pass A: role-driven dispatch (D-13 fires first).
    if db is not None:
        for line in lines:
            src = box_map.get(line.source_id)
            dst = box_map.get(line.dest_id)
            if src is None or dst is None:
                continue
            # Single-parent guard (WR-02 fix, Plan 31-07): a companion with
            # multiple incoming edges is genuinely shared and should NOT be
            # claimed as a single source's display. Matches Pass B's existing
            # invariant. Also avoids a wasted DB query.
            if len(incoming.get(dst.id, [])) != 1:
                continue
            try:
                role = db.get_signal_role(src.name, line.source_outlet)
            except Exception:
                role = None
            if role is None:
                continue
            spec = _ROLE_COMPANION_MAP.get(role) or {}
            companion_name = spec.get("companion")
            placement = spec.get("placement")
            if companion_name and dst.name == companion_name and placement:
                # dst is a companion of src per the role map.
                result[dst.id] = (src, placement)

    # Pass B: legacy `_COMPANION_NAMES` heuristic (UNCHANGED behavior --
    # placement is always "right" to preserve back-compat).
    for box in boxes:
        if box.name not in _COMPANION_NAMES:
            continue
        if box.id in result:    # role pass already claimed this companion
            continue
        parents = incoming.get(box.id, [])
        if len(parents) != 1:
            continue
        parent = box_map.get(parents[0])
        if parent is not None:
            result[box.id] = (parent, "right")

    return result


def _place_companions(
    patcher: "Patcher",
    companions: dict[str, tuple[Box, str]],
) -> None:
    """Position companion objects beside their parent.

    Every companion sits at parent.x + parent.w + _COMPANION_GAP, same y,
    stacking left to right when several share a parent. The placement
    string carried in the companions dict (from `_identify_companions`) is
    "right"; any other value falls back to "right". The former "overlay"
    placement (status -> flonum on top of its source) was removed in
    Q27 / F1 because it hid the source; `Patcher.add_overlay_readout` is the
    explicit overlay path.

    Args:
        patcher: The Patcher instance whose boxes are being placed.
        companions: Map from companion box id to (parent_box, placement).
    """
    all_boxes = patcher.boxes
    box_map = {b.id: b for b in all_boxes}

    # Group companions by parent for stacking.
    right_groups: dict[str, list[str]] = {}
    for comp_id, (parent_box, _placement) in companions.items():
        right_groups.setdefault(parent_box.id, []).append(comp_id)

    for parent_id, comp_ids in right_groups.items():
        parent = box_map.get(parent_id)
        if parent is None:
            continue

        # Place companions to the right of parent, stacking if multiple
        cursor_x = parent.patching_rect[0] + parent.patching_rect[2] + _COMPANION_GAP
        for comp_id in comp_ids:
            comp_box = box_map.get(comp_id)
            if comp_box is None:
                continue
            comp_box.patching_rect[0] = cursor_x
            comp_box.patching_rect[1] = parent.patching_rect[1]
            cursor_x += comp_box.patching_rect[2] + _COMPANION_GAP


# ---------------------------------------------------------------------------
# Disconnected object positioning
# ---------------------------------------------------------------------------


def _position_disconnected(
    boxes: list[Box],
    start_x: float,
    start_y: float,
    cap_right: float | None = None,
    deco: "_Decorations | None" = None,
) -> None:
    """Place disconnected objects in a compact grid to the right of components.

    Groups subpatchers first, then other objects. Uses multi-column layout
    with wrapping to avoid excessively tall columns. Each box occupies its
    footprint: rendered rect (``sizing.rendered_rect``) plus the offset
    rects of its riders (*deco*; Q27 / F3). When a new column would end
    past *cap_right*, it instead starts a new column band at start_x, below
    the tallest column so far (Q27 / F5).
    """
    if not boxes:
        return

    # Separate subpatchers from other disconnected objects
    subpatchers = [b for b in boxes if b.name in ("patcher", "p")]
    others = [b for b in boxes if b.name not in ("patcher", "p")]

    # Compact vertical spacing for disconnected items
    disc_v_gap = 30.0
    disc_h_gap = H_GUTTER
    max_col_height = 400.0  # Wrap to next column after this height

    state = {
        "x": start_x, "y": start_y, "top": start_y,
        "col_w": 0.0, "lowest": start_y,
    }

    def new_column(next_w: float) -> None:
        next_x = state["x"] + state["col_w"] + disc_h_gap
        if cap_right is not None and next_x + next_w > cap_right and next_x > start_x:
            # New column band below the tallest column so far
            state["x"] = start_x
            state["top"] = state["lowest"] + disc_v_gap
        else:
            state["x"] = next_x
        state["y"] = state["top"]
        state["col_w"] = 0.0

    def dims(box: Box) -> _Footprint:
        return _footprint(box, None, 0.0, deco)

    def place(box: Box) -> None:
        fp = dims(box)
        w = fp.right - fp.left
        h = fp.above + fp.bottom
        if state["y"] + h > state["top"] + max_col_height and state["y"] > state["top"]:
            new_column(w)
        box.patching_rect[0] = state["x"] - fp.left
        box.patching_rect[1] = state["y"] + fp.above
        state["y"] += h + disc_v_gap
        state["lowest"] = max(state["lowest"], state["y"] - disc_v_gap)
        state["col_w"] = max(state["col_w"], w)

    # Place subpatchers first (in a column, they're reference modules)
    for box in subpatchers:
        place(box)

    # Start new column for non-subpatcher objects if subpatchers were placed
    if subpatchers and others:
        new_column(max(dims(b).right - dims(b).left for b in others))

    # Place other disconnected objects (comments, etc.)
    for box in others:
        place(box)


# ---------------------------------------------------------------------------
# Grid snap and comment placement
# ---------------------------------------------------------------------------


def _snap_to_grid(boxes: list[Box], grid_size: float) -> None:
    """Round all box positions to nearest grid multiple.

    Applied as a single pass after ALL positioning is complete
    (including companion and UI control placement).
    """
    for box in boxes:
        box.patching_rect[0] = round(box.patching_rect[0] / grid_size) * grid_size
        box.patching_rect[1] = round(box.patching_rect[1] / grid_size) * grid_size


def _place_associated_comments(boxes: list[Box], comment_gap: float) -> None:
    """Position comments with target_id next to their target objects.

    Places the comment to the right of the target at the same Y position,
    separated by comment_gap pixels.
    """
    box_map = {b.id: b for b in boxes}
    for box in boxes:
        if box.maxclass == "comment" and box.target_id:
            target = box_map.get(box.target_id)
            if target:
                box.patching_rect[0] = target.patching_rect[0] + target.patching_rect[2] + comment_gap
                box.patching_rect[1] = target.patching_rect[1]


# ---------------------------------------------------------------------------
# Midpoint generation for all cable types
# ---------------------------------------------------------------------------


def _outlet_x(box: Box, outlet_idx: int) -> float:
    """Approximate x position of an outlet on a box."""
    x = box.patching_rect[0]
    w = box.patching_rect[2]
    n = box.numoutlets
    if n <= 1:
        return x + _IO_MARGIN  # MAX draws a lone port at the left edge, not centered
    usable = w - 2 * _IO_MARGIN
    spacing = usable / (n - 1)
    return x + _IO_MARGIN + outlet_idx * spacing


def _inlet_x(box: Box, inlet_idx: int) -> float:
    """Approximate x position of an inlet on a box."""
    x = box.patching_rect[0]
    w = box.patching_rect[2]
    n = box.numinlets
    if n <= 1:
        return x + _IO_MARGIN  # MAX draws a lone port at the left edge, not centered
    usable = w - 2 * _IO_MARGIN
    spacing = usable / (n - 1)
    return x + _IO_MARGIN + inlet_idx * spacing


_COLLISION_PAD = 5.0  # Padding around obstacle bounding boxes


def _boxes_between(
    patcher: Patcher,
    src_box: Box,
    dst_box: Box,
    src_ox: float,
    dst_ix: float,
) -> list[Box]:
    """Find boxes whose bounding box overlaps the cord's corridor.

    A box is an obstacle if:
    - Its vertical span overlaps the cord's vertical range (src_oy to dst_iy)
    - Its horizontal span overlaps the cord's horizontal corridor
    - It is not the source or destination box
    - It is not a background element (a panel or a ``background: 1`` box):
      cords run over panels, which sit behind their chains (Q27 / F3)
    """
    src_oy = src_box.patching_rect[1] + src_box.patching_rect[3]
    dst_iy = dst_box.patching_rect[1]

    # Vertical range of the cord (top to bottom)
    cord_top = min(src_oy, dst_iy)
    cord_bottom = max(src_oy, dst_iy)

    # Horizontal corridor of the cord
    cord_left = min(src_ox, dst_ix) - _COLLISION_PAD
    cord_right = max(src_ox, dst_ix) + _COLLISION_PAD

    obstacles: list[Box] = []
    for box in patcher.boxes:
        if box.id == src_box.id or box.id == dst_box.id:
            continue
        if _is_background(box):
            continue
        bx, by, bw, bh = box.patching_rect
        # Expand box by collision pad
        box_left = bx - _COLLISION_PAD
        box_right = bx + bw + _COLLISION_PAD
        box_top = by - _COLLISION_PAD
        box_bottom = by + bh + _COLLISION_PAD

        # Check overlap in both dimensions
        h_overlap = box_left < cord_right and box_right > cord_left
        v_overlap = box_top < cord_bottom and box_bottom > cord_top

        if h_overlap and v_overlap:
            obstacles.append(box)

    return obstacles


_ROUTE_CLEAR = 4.0  # Gap kept between a routed cord and any box edge


def _is_background(box: Box) -> bool:
    """Panels and ``background: 1`` boxes render behind cords."""
    return box.maxclass == "panel" or box.extra_attrs.get("background") == 1


def _segment_hits(
    x1: float, y1: float, x2: float, y2: float,
    rects: list[tuple[float, float, float, float]],
) -> bool:
    """True if the axis-aligned segment crosses any (left, top, right, bottom) rect."""
    lo_x, hi_x = min(x1, x2), max(x1, x2)
    lo_y, hi_y = min(y1, y2), max(y1, y2)
    for left, top, right, bottom in rects:
        if lo_x < right and hi_x > left and lo_y < bottom and hi_y > top:
            return True
    return False


def _path_clear(
    points: list[tuple[float, float]],
    rects: list[tuple[float, float, float, float]],
) -> bool:
    """True if every segment of an orthogonal polyline avoids every rect."""
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        if _segment_hits(x1, y1, x2, y2, rects):
            return False
    return True


def _path_cost(points: list[tuple[float, float]]) -> float:
    """Manhattan length plus a fixed penalty per bend."""
    length = sum(
        abs(x2 - x1) + abs(y2 - y1)
        for (x1, y1), (x2, y2) in zip(points, points[1:])
    )
    return length + 20.0 * max(0, len(points) - 2)


def _route_clear_path(
    patcher: Patcher,
    src_box: Box,
    dst_box: Box,
    src_ox: float,
    src_oy: float,
    dst_ix: float,
    dst_iy: float,
) -> list[float] | None:
    """Find a short orthogonal route that crosses no box, or None.

    Two shapes are tried, cheapest clear route wins:

    - **Z**: down from the outlet, one horizontal run at a free height, down
      into the inlet (2 midpoints).
    - **Lane**: a short drop below the outlet, across to a clear vertical
      lane beside the boxes in the way, down the lane, across above the
      inlet, then into it (4 midpoints).

    Every segment is checked against every other box (padded by
    ``_ROUTE_CLEAR``), so a route never doubles back over itself and never
    passes through an object. Returns None when no clear route exists; the
    caller then keeps a plain L-shape rather than zig-zagging.
    """
    pad = _ROUTE_CLEAR
    rects: list[tuple[float, float, float, float]] = []
    for box in patcher.boxes:
        if box.id in (src_box.id, dst_box.id):
            continue
        if _is_background(box):
            continue  # panels / background boxes are never obstacles (Q27 / F3)
        bx, by, bw, bh = box.patching_rect
        rects.append((bx - pad, by - pad, bx + bw + pad, by + bh + pad))

    # The cord leaves the outlet downward and enters the inlet from above.
    start = (src_ox, src_oy)
    end = (dst_ix, dst_iy)

    # Candidate heights for horizontal runs: just outside every box edge,
    # plus the points right below the source and right above the destination.
    levels = {src_oy + 8.0, dst_iy - 8.0, (src_oy + dst_iy) * 0.5}
    for left, top, right, bottom in rects:
        levels.add(top - 2.0)
        levels.add(bottom + 2.0)

    best: list[tuple[float, float]] | None = None
    best_cost = float("inf")

    def consider(points: list[tuple[float, float]]) -> None:
        nonlocal best, best_cost
        cost = _path_cost(points)
        if cost < best_cost and _path_clear(points, rects):
            best, best_cost = points, cost

    # Z routes need a level between the outlet and the inlet.
    if dst_iy > src_oy + 4.0:
        for y in sorted(levels):
            if src_oy + 3.0 <= y <= dst_iy - 3.0:
                consider([start, (src_ox, y), (dst_ix, y), end])

    # Lane routes: the first run sits just below the source, the last just
    # above the destination; the lane runs beside some box edge.
    near_src = sorted(
        (y for y in levels if y >= src_oy + 3.0),
        key=lambda y: y - src_oy,
    )[:4]
    near_dst = sorted(
        (y for y in levels if y <= dst_iy - 3.0),
        key=lambda y: dst_iy - y,
    )[:4]
    lanes = {src_ox, dst_ix}
    for left, top, right, bottom in rects:
        lanes.add(left - 2.0)
        lanes.add(right + 2.0)
    mid_x = (src_ox + dst_ix) * 0.5
    for lane in sorted(lanes, key=lambda x: abs(x - mid_x)):
        for y1 in near_src:
            for y2 in near_dst:
                consider([start, (src_ox, y1), (lane, y1), (lane, y2),
                          (dst_ix, y2), end])

    if best is None:
        return None

    # Drop collinear points so the stored route has only real bends.
    pts = [best[0]]
    for p_mid, p_next in zip(best[1:], best[2:]):
        p_prev = pts[-1]
        if (p_prev[0] == p_mid[0] == p_next[0]) or (p_prev[1] == p_mid[1] == p_next[1]):
            continue
        pts.append(p_mid)
    pts.append(best[-1])
    inner = pts[1:-1]
    if not inner:
        return None
    flat: list[float] = []
    for x, y in inner:
        flat.extend([x, y])
    return flat


def _generate_midpoints(patcher: Patcher, *, eligible=None) -> None:
    """Add midpoints to patchlines for clean segmented cable routing.

    Handles four routing patterns:

    1. **Horizontal offset** (forward or backward): source and destination have
       significant horizontal distance. Creates a 2-midpoint horizontal segment
       at the vertical midpoint between source and dest, OR obstacle-avoiding
       dog-leg routing when intermediate objects block the path.

    2. **Upward bus routing**: source is far below destination (e.g., loadbang
       init cables). Routes cables along the right edge of the patcher in a
       vertical bus, then turns left to the target. Parallel bus cables are
       spaced apart to avoid visual overlap.

    3. **Near-vertical with obstacle**: vertical cables that pass through an
       intermediate object get a horizontal jog around the obstacle.

    4. **Near-vertical clean**: cables with minimal horizontal offset and no
       obstacles get no midpoints (clean straight lines).

    Only adds midpoints to lines that don't already have them.

    Args:
        patcher: The Patcher whose lines are routed (not recursive).
        eligible: Optional callable taking a Patchline and returning bool.
            When given, lines for which it returns False are skipped (left
            exactly as they are). The edit-path ``finalize_patch`` passes
            one that admits only new cords and cords touching an added or
            moved box (Q6 / B1). Default None routes every line that has no
            midpoints, which is the ``apply_layout`` behavior.
    """
    box_map = {b.id: b for b in patcher.boxes}

    # First pass: classify cables
    companion_lines: list = []  # Side-by-side objects (gain~ -> meter~)
    upward_lines: list = []
    normal_lines: list = []

    for line in patcher.lines:
        if line.midpoints:
            continue
        if eligible is not None and not eligible(line):
            continue

        src_box = box_map.get(line.source_id)
        dst_box = box_map.get(line.dest_id)
        if not src_box or not dst_box:
            continue

        src_ox = _outlet_x(src_box, line.source_outlet)
        src_oy = src_box.patching_rect[1] + src_box.patching_rect[3]
        dst_ix = _inlet_x(dst_box, line.dest_inlet)
        dst_iy = dst_box.patching_rect[1]

        hdist = abs(src_ox - dst_ix)
        vdist = src_oy - dst_iy  # positive = upward flow

        # Companion pattern: objects at the same y, close together horizontally
        same_y = src_box.patching_rect[1] == dst_box.patching_rect[1]
        close_x = abs(src_box.patching_rect[0] - dst_box.patching_rect[0]) < 80
        if same_y and close_x and vdist > 0:
            companion_lines.append(
                (line, src_box, dst_box, src_ox, src_oy, dst_ix, dst_iy),
            )
        elif hdist > HORIZONTAL_THRESHOLD and vdist > UPWARD_BUS_THRESHOLD:
            upward_lines.append((line, src_ox, src_oy, dst_ix, dst_iy))
        else:
            normal_lines.append(
                (line, src_box, dst_box, src_ox, src_oy, dst_ix, dst_iy),
            )

    # Route companion cables with tight local loop
    for line, src_box, dst_box, src_ox, src_oy, dst_ix, dst_iy in companion_lines:
        _route_companion_cable(line, src_box, dst_box, src_ox, src_oy, dst_ix, dst_iy)

    # Route upward cables via right-edge bus
    if upward_lines:
        _route_bus_cables(upward_lines, patcher.boxes)

    # Route normal cables with obstacle detection
    for line, src_box, dst_box, src_ox, src_oy, dst_ix, dst_iy in normal_lines:
        hdist = abs(src_ox - dst_ix)
        obstacles = _boxes_between(patcher, src_box, dst_box, src_ox, dst_ix)

        if obstacles:
            # Route around obstacles along a clear Z or lane path. If none
            # exists, fall back to the plain L-shape: crossing a box is less
            # confusing than a cord that doubles back over itself.
            routed = _route_clear_path(
                patcher, src_box, dst_box, src_ox, src_oy, dst_ix, dst_iy,
            )
            if routed is not None:
                line.midpoints = routed
            elif hdist > HORIZONTAL_THRESHOLD:
                mid_y = (src_oy + dst_iy) * 0.5
                line.midpoints = [src_ox, mid_y, dst_ix, mid_y]
        elif hdist > HORIZONTAL_THRESHOLD:
            # Simple L-shape at vertical midpoint (no obstacles)
            mid_y = (src_oy + dst_iy) * 0.5
            line.midpoints = [src_ox, mid_y, dst_ix, mid_y]


def _route_companion_cable(
    line: object,
    src_box: Box,
    dst_box: Box,
    src_ox: float,
    src_oy: float,
    dst_ix: float,
    dst_iy: float,
) -> None:
    """Route a cable between side-by-side companion objects with a tight local loop.

    The cable exits the source outlet (bottom), goes right past the rightmost
    object edge, up to above the destination inlet (top), then left to the inlet.
    This produces a compact U-shaped route hugging the right side of the pair.
    """
    # Find the rightmost edge of both objects
    src_right = src_box.patching_rect[0] + src_box.patching_rect[2]
    dst_right = dst_box.patching_rect[0] + dst_box.patching_rect[2]
    pair_right = max(src_right, dst_right)

    bus_x = pair_right + 7.0  # Tight margin past the pair's right edge
    line.midpoints = [
        bus_x, src_oy + 5,
        bus_x, dst_iy - 8,
        dst_ix, dst_iy - 8,
    ]


def _route_bus_cables(
    upward_lines: list[tuple],
    boxes: list[Box],
) -> None:
    """Route upward-flowing cables via a right-edge vertical bus.

    Cables run horizontally to a bus X position on the right side of the
    patcher, then vertically up, then horizontally left to the destination.
    Parallel cables are spaced apart by BUS_SPACING to avoid overlap.

    Args:
        upward_lines: List of (line, src_ox, src_oy, dst_ix, dst_iy) tuples.
        boxes: All boxes in the patcher (for computing rightmost edge).
    """
    # Find rightmost object edge
    max_right = 0.0
    for box in boxes:
        right = box.patching_rect[0] + box.patching_rect[2]
        if right > max_right:
            max_right = right

    bus_start_x = max_right + BUS_MARGIN

    # Sort by destination Y (topmost target gets innermost bus position)
    upward_lines.sort(key=lambda t: t[4])  # sort by dst_iy ascending

    for i, (line, src_ox, src_oy, dst_ix, dst_iy) in enumerate(upward_lines):
        bus_x = bus_start_x + i * BUS_SPACING
        # 3-midpoint route: right to bus, up along bus, left to target
        line.midpoints = [
            bus_x, src_oy + 5,
            bus_x, dst_iy - 8,
            dst_ix, dst_iy - 8,
        ]


# ---------------------------------------------------------------------------
# Patcher rect auto-sizing
# ---------------------------------------------------------------------------


def _auto_size_patcher_rect(patcher: Patcher, options: LayoutOptions) -> None:
    """Set patcher rect to fit all objects and bus routing with padding.

    Computes the bounding box of all objects (including midpoint bus routes)
    and sets the patcher window size accordingly.
    """
    if not patcher.boxes:
        return

    max_right = 0.0
    max_bottom = 0.0

    for box in patcher.boxes:
        right = box.patching_rect[0] + box.patching_rect[2]
        bottom = box.patching_rect[1] + box.patching_rect[3]
        if right > max_right:
            max_right = right
        if bottom > max_bottom:
            max_bottom = bottom

    # Account for bus routing midpoints extending past objects
    for line in patcher.lines:
        if line.midpoints:
            for j in range(0, len(line.midpoints), 2):
                mx = line.midpoints[j]
                if mx > max_right:
                    max_right = mx
            for j in range(1, len(line.midpoints), 2):
                my = line.midpoints[j]
                if my > max_bottom:
                    max_bottom = my

    new_w = max_right + options.patcher_padding
    new_h = max_bottom + options.patcher_padding

    # Enforce minimum size
    new_w = max(new_w, 400.0)
    new_h = max(new_h, 300.0)

    rect = patcher.props.get("rect", [85.0, 104.0, 640.0, 480.0])
    rect[2] = new_w
    rect[3] = new_h
    patcher.props["rect"] = rect


# ---------------------------------------------------------------------------
# Presentation mode layout
# ---------------------------------------------------------------------------


def _apply_presentation_layout(boxes: list[Box]) -> None:
    """Set presentation_rect on boxes with presentation=True.

    Arranges presentation objects in a grid layout (left-to-right, wrapping
    after 4 per row). Only boxes that don't already have a presentation_rect
    are placed, and only they count toward a row. x is a running offset
    advanced by each box's rendered width + 60, and each row starts below
    the previous row's tallest box + 40, so mixed widths never overlap
    (Q27 / F5). The rect keeps the box's stored width and height; uniform
    sizes reproduce the fixed-pitch grid.
    """
    auto = [b for b in boxes if b.presentation and b.presentation_rect is None]
    if not auto:
        return

    grid_x_start = 20.0
    grid_y_start = 20.0
    grid_h_spacing = 60.0
    grid_v_spacing = 40.0
    max_per_row = 4

    x = grid_x_start
    y = grid_y_start
    row_h = 0.0
    col = 0
    for box in auto:
        if col == max_per_row:
            x = grid_x_start
            y += row_h + grid_v_spacing
            row_h = 0.0
            col = 0
        rw, rh = _rdims(box)
        box.presentation_rect = [x, y, box.patching_rect[2], box.patching_rect[3]]
        x += rw + grid_h_spacing
        row_h = max(row_h, rh)
        col += 1
