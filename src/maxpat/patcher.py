"""Patcher, Box, and Patchline data model with .maxpat JSON serialization.

This module provides the core types for building MAX patches programmatically.
Patcher holds boxes and connections; Box represents a single MAX object;
Patchline represents a connection between two boxes.

All JSON output follows the .maxpat format verified in 02-RESEARCH.md.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

from src.maxpat.defaults import (
    AESTHETIC_PALETTE,
    BUBBLE_TOP,
    DEFAULT_PATCHER_PROPS,
    FONT_NAME,
    FONT_SIZE,
    FONTFACE_BOLD,
    FONTFACE_ITALIC,
    GEN_PATCHER_BGCOLOR,
    SUBPATCHER_RECT,
    V_SPACING,
)

# Collision detection padding (px) around boxes for readability
COLLISION_PAD = 5.0

# Objects whose I/O comes from their content (embedded patcher, script,
# loaded file), not from their arguments. modify_box(args=...) keeps their
# I/O counts and cords instead of recomputing from the DB (Q6 / B2).
CONTENT_DEFINED_NAMES = frozenset({
    "p", "patcher", "bpatcher", "gen~", "mc.gen~", "jit.gen", "poly~",
    "mc.poly~", "js", "jsui", "v8", "v8ui", "node.script",
})

# Box keys from_dict maps onto model fields (everything else is extra_attrs).
# The round-trip extra_attrs diff skips them: their own overlays write them.
_BOX_HANDLED_KEYS = frozenset({
    "id", "maxclass", "text", "numinlets", "numoutlets",
    "outlettype", "patching_rect", "fontname", "fontsize",
    "presentation", "presentation_rect", "patcher",
    "saved_object_attributes",
})

# Patchline keys from_dict maps onto model fields.
_LINE_HANDLED_KEYS = frozenset({
    "source", "destination", "order", "hidden", "midpoints", "color",
})


def _apply_extra_attrs_diff(
    d: dict, current: dict, old: dict, handled: frozenset
) -> None:
    """Write extra_attrs changes since load into a round-trip dict (Q28 / B5).

    ``old`` is the deep-copied load snapshot. A key in ``old`` missing from
    ``current`` is popped from ``d``. A key of ``current`` not in
    ``handled`` that is new, or whose value differs from the snapshot
    (in-place edits included), is written with ``d[key] = value``: an
    existing key keeps its position, a new key appends. Unchanged values
    keep their file representation (12 vs 12.0) because they are compared
    with the snapshot, never written.
    """
    for k in old:
        if k not in current:
            d.pop(k, None)
    for k, v in current.items():
        if k in handled:
            continue
        if k not in old or old[k] != v:
            d[k] = v


from src.maxpat.maxclass_map import resolve_maxclass, is_ui_object, UI_MAXCLASSES
from src.maxpat.graph import GraphMixin
from src.maxpat.analysis import AnalysisMixin, SECTION_SIGNATURES, _SECTION_NAME_PRIORITY
from src.maxpat.sizing import calculate_box_size, is_max_saved, rendered_rect
from src.maxpat.db_lookup import (
    DOMAIN_SCOPES,
    ObjectDatabase,
    detect_patcher_scope,
    inner_patcher_scope,
)


class Patchline:
    """A connection between two boxes in a MAX patcher.

    Serializes to: {"patchline": {"source": [id, outlet], "destination": [id, inlet], ...}}

    Supports optional midpoints for segmented cable routing. Midpoints is a
    flat list of [x1, y1, x2, y2, ...] coordinates that the cable routes
    through, creating right-angle bends instead of diagonal lines.
    """

    def __init__(
        self,
        source_id: str,
        source_outlet: int,
        dest_id: str,
        dest_inlet: int,
        order: int = 0,
        hidden: bool = False,
        midpoints: list[float] | None = None,
        color: list | None = None,
        extra_attrs: dict | None = None,
        _raw: dict | None = None,
    ) -> None:
        self.source_id = source_id
        self.source_outlet = source_outlet
        self.dest_id = dest_id
        self.dest_inlet = dest_inlet
        self.order = order
        self.hidden = hidden
        self.midpoints = midpoints
        self.color = color
        self.extra_attrs = extra_attrs if extra_attrs is not None else {}
        self._raw = _raw
        # Load snapshot (Q28 / B5): taken whenever the line comes from a
        # file dict. to_dict writes back only the fields that differ from it.
        if _raw is not None:
            self._loaded: dict | None = {
                "order": order,
                "hidden": bool(hidden),
                "midpoints": copy.deepcopy(midpoints),
                "color": copy.deepcopy(color),
                "extra_attrs": copy.deepcopy(self.extra_attrs),
            }
        else:
            self._loaded = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to .maxpat patchline JSON structure.

        Uses dual-path serialization:
        - Round-trip path (self._raw exists): start from the original dict
          (unknown keys and key order kept), overlay source/destination,
          then write back every field that changed since load (Q28 / B5):
          order (0 included), hidden (True -> ``1``, False -> key removed),
          midpoints and color (empty/None -> key removed) and extra_attrs
          (added, changed and deleted keys). Unchanged fields come from
          ``_raw``, so a direct ``_raw`` key write still lands.
        - Creation path (no _raw): build dict from scratch for new connections.
        """
        if self._raw is not None:
            # Round-trip path: preserve original dict structure
            d = dict(self._raw)
            d["source"] = [self.source_id, self.source_outlet]
            d["destination"] = [self.dest_id, self.dest_inlet]
            snap = getattr(self, "_loaded", None)
            if snap is not None:
                _apply_extra_attrs_diff(
                    d, self.extra_attrs, snap["extra_attrs"], _LINE_HANDLED_KEYS
                )
                if self.order != snap["order"]:
                    d["order"] = self.order
                if bool(self.hidden) != snap["hidden"]:
                    if self.hidden:
                        d["hidden"] = 1
                    else:
                        d.pop("hidden", None)
                if self.midpoints != snap["midpoints"]:
                    if self.midpoints:
                        d["midpoints"] = list(self.midpoints)
                    else:
                        d.pop("midpoints", None)
                if self.color != snap["color"]:
                    if self.color is not None:
                        d["color"] = self.color
                    else:
                        d.pop("color", None)
                return {"patchline": d}
            # Update color if changed from what was in _raw
            if self.color is not None:
                d["color"] = self.color
            elif "color" in d and self.color is None:
                del d["color"]
            # Sync midpoints: add/update/remove as needed
            if self.midpoints:
                d["midpoints"] = list(self.midpoints)
            elif "midpoints" in d:
                del d["midpoints"]
            return {"patchline": d}
        else:
            # Creation path: build from scratch
            d: dict[str, Any] = {
                "source": [self.source_id, self.source_outlet],
                "destination": [self.dest_id, self.dest_inlet],
            }
            # Only include "order" if non-zero (MAX omits order=0)
            if self.order != 0:
                d["order"] = self.order
            if self.hidden:
                d["hidden"] = 1
            if self.midpoints:
                d["midpoints"] = list(self.midpoints)
            if self.color is not None:
                d["color"] = self.color
            d.update(self.extra_attrs)
            return {"patchline": d}


@dataclass
class EditResult:
    """Result of an edit operation with orphaned connection tracking.

    Returned by modify_box(), replace_box() and remove_box() to provide the
    caller with the edited/created/removed box and any connections that were
    orphaned during the operation (e.g., due to I/O count shrink or object
    replacement).

    ``parent_orphaned`` lists cords removed in the PARENT patcher when a
    port (inlet/outlet) box change inside a subpatcher shrank the parent
    box's port count (Q28 / B7). ``orphaned`` is always cords of THIS
    patcher (replace_box_safe rewires them by id); parent-patcher cords
    appear only in ``parent_orphaned``.
    """
    box: Box
    orphaned: list[dict] = field(default_factory=list)
    # Each orphaned entry: {"source_id", "source_outlet", "dest_id", "dest_inlet"}
    parent_orphaned: list[dict] = field(default_factory=list)


class BoxMovedWarning(UserWarning):
    """add_box moved a box off its requested position to clear a real overlap (Q29 / B10)."""


# Box attributes replace_box carries to the new box whatever its class (Q29 /
# B4): varname plus MAX's common box attributes (jbox.maxref.xml).
_IDENTITY_ALWAYS = (
    "varname", "color", "textcolor", "background", "hidden", "ignoreclick",
    "hint", "annotation",
)
_PARAMETER_KEYS = ("parameter_enable", "parameter_mappable")


class Box:
    """A single MAX object box in a patcher.

    Handles maxclass resolution, content-aware sizing, and .maxpat JSON
    serialization. Supports both UI objects (maxclass = own name) and non-UI
    objects (maxclass = "newobj" with text field).
    """

    def __init__(
        self,
        name: str,
        args: list[str] | None = None,
        box_id: str = "obj-0",
        db: ObjectDatabase | None = None,
        x: float = 0.0,
        y: float = 0.0,
        allowed_packages: list[str] | None = None,
    ) -> None:
        """Create a Box.

        Args:
            name: MAX object name (e.g., "cycle~", "toggle", "pack").
            args: Object arguments (e.g., ["440"] for cycle~ 440).
            box_id: Unique box identifier (e.g., "obj-1").
            db: ObjectDatabase instance for lookup. Required for non-UI
                objects to verify existence and get I/O counts.
            x: Horizontal position.
            y: Vertical position.
            allowed_packages: Package filter. None=allow all (default),
                []=core only, ["BEAP"]=core+BEAP objects.

        Raises:
            ValueError: If name is not found in database and not a known
                       UI maxclass (Rule #1: Never Guess Objects).
        """
        if args is None:
            args = []

        self.name = name
        self.args = args
        self.id = box_id

        # Resolve the canonical name (handle aliases like t -> trigger)
        canonical = name
        if db:
            canonical = db._aliases.get(name, name)

        # Resolve maxclass
        self.maxclass = resolve_maxclass(canonical)

        # Build text field (name + args)
        parts = [name] + args
        self.text = " ".join(parts).strip()

        # Look up object in database for I/O counts and outlet types
        obj_data = None
        if db:
            obj_data = db.lookup(name, allowed_packages=allowed_packages)

        if obj_data is None and not is_ui_object(canonical):
            # Object not in database and not a known UI type -- Rule #1 violation
            raise ValueError(
                f"Unknown object: '{name}' -- not in database, verify manually. "
                f"(Rule #1: Never Guess Objects)"
            )

        # Compute I/O counts
        if db and obj_data:
            self.numinlets, self.numoutlets = db.compute_io_counts(name, args)
            self.outlettype = db.get_outlet_types(name, args)
        elif obj_data:
            self.numinlets = len(obj_data.get("inlets", []))
            self.numoutlets = len(obj_data.get("outlets", []))
            self.outlettype = self._derive_outlet_types(obj_data)
        else:
            # UI object not in database -- use defaults
            self.numinlets = 1
            self.numoutlets = 1
            self.outlettype = [""]

        # Compute box size
        w, h = calculate_box_size(self.text, self.maxclass)
        self.patching_rect = [x, y, w, h]

        # Font (for non-UI and text-based UI objects)
        self.fontname = FONT_NAME
        self.fontsize = FONT_SIZE

        # Presentation mode
        self.presentation = False
        self.presentation_rect: list[float] | None = None

        # Extra attributes (for custom box properties)
        self.extra_attrs: dict[str, Any] = {}

        # Comment association: layout-time only, not serialized to .maxpat
        self.target_id: str | None = None

        # Requested (x, y) when add_box moved the box off a real overlap
        # (Q29 / B10); None when it was placed where asked. Not serialized.
        # Builder boxes come from Box.__new__: read with getattr(..., None).
        self.nudged_from: tuple[float, float] | None = None

        # Internal: track if this is a subpatcher/bpatcher with embedded patcher
        self._inner_patcher: Patcher | None = None
        self._saved_object_attributes: dict[str, Any] | None = None
        self._bpatcher_attrs: dict[str, Any] | None = None

        # Raw dict for lossless round-trip (None for newly created boxes)
        self._raw: dict | None = None

        # Copy of patching_rect taken at load (from_dict); None for new boxes.
        # The edit-path finalize compares x/y with it to detect moved boxes.
        self._loaded_rect: tuple | None = None

        # Load snapshot of the tracked fields (fontname, fontsize, a deep
        # copy of extra_attrs), set by from_dict; None for new boxes (Q28).
        self._loaded: dict | None = None

    @property
    def right_edge(self) -> float:
        """X coordinate of the box's right edge (x + width)."""
        return self.patching_rect[0] + self.patching_rect[2]

    @property
    def bottom_edge(self) -> float:
        """Y coordinate of the box's bottom edge (y + height)."""
        return self.patching_rect[1] + self.patching_rect[3]

    @staticmethod
    def _derive_outlet_types(obj_data: dict) -> list[str]:
        """Derive outlettype array from object database outlets."""
        result = []
        for outlet in obj_data.get("outlets", []):
            if outlet.get("signal"):
                otype = outlet.get("type", "")
                if "multichannel" in otype.lower():
                    result.append("multichannelsignal")
                else:
                    result.append("signal")
            else:
                result.append("")
        return result

    def to_dict(self) -> dict[str, Any]:
        """Serialize to .maxpat box JSON structure.

        Uses dual-path serialization:
        - Round-trip path (self._raw exists): start from the original dict
          (unknown keys and key order kept). First write back every tracked
          field that changed since load (Q28 / B5): extra_attrs keys added,
          changed (in-place edits included) or deleted, and fontname /
          fontsize. Then overlay the structural fields (rect, I/O, text,
          outlettype, presentation, inner patcher, saved_object_attributes),
          which always win. Unchanged fields come from ``_raw``, so a direct
          ``_raw`` key write still lands while its field is unchanged.
        - Creation path (no _raw): build dict from scratch for new boxes.

        Returns:
            {"box": {...}} dict matching the .maxpat format.
        """
        if self._raw is not None:
            # === ROUND-TRIP PATH ===
            # Start from original dict, overlay any mutations
            d = dict(self._raw)

            # Tracked fields changed since load (Q28), before the overlays
            snap = getattr(self, "_loaded", None)
            if snap is not None:
                _apply_extra_attrs_diff(
                    d, self.extra_attrs, snap["extra_attrs"], _BOX_HANDLED_KEYS
                )
                for fld in ("fontname", "fontsize"):
                    cur = getattr(self, fld, None)
                    if cur != snap[fld]:
                        if cur is None:
                            d.pop(fld, None)
                        else:
                            d[fld] = cur

            # Overlay mutable fields that Python code may have changed
            d["patching_rect"] = self.patching_rect
            d["numinlets"] = self.numinlets
            d["numoutlets"] = self.numoutlets
            if self.text is not None:
                d["text"] = self.text
            if "outlettype" in self._raw:
                d["outlettype"] = self.outlettype

            # Presentation mode
            if self.presentation:
                d["presentation"] = 1
                if self.presentation_rect is not None:
                    d["presentation_rect"] = self.presentation_rect
            elif "presentation" in d:
                del d["presentation"]
                d.pop("presentation_rect", None)

            # Inner patcher (subpatcher/bpatcher embed)
            if self._inner_patcher is not None:
                d["patcher"] = self._inner_patcher.to_dict()["patcher"]
            elif "patcher" in self._raw:
                # Inner patcher was removed -- don't emit stale copy
                d.pop("patcher", None)

            # saved_object_attributes
            if self._saved_object_attributes is not None:
                d["saved_object_attributes"] = self._saved_object_attributes
            elif "saved_object_attributes" not in self._raw:
                d.pop("saved_object_attributes", None)

            return {"box": d}
        else:
            # === CREATION PATH (existing logic) ===
            d: dict[str, Any] = {
                "maxclass": self.maxclass,
                "id": self.id,
                "numinlets": self.numinlets,
                "numoutlets": self.numoutlets,
                "outlettype": self.outlettype,
                "patching_rect": self.patching_rect,
            }

            # Non-UI objects: include text and font
            if self.maxclass == "newobj":
                d["text"] = self.text
                d["fontname"] = self.fontname
                d["fontsize"] = self.fontsize
            elif self.maxclass in ("comment", "message"):
                # Text-based UI objects
                d["text"] = self.text
                d["fontname"] = self.fontname
                d["fontsize"] = self.fontsize
            elif self.maxclass == "bpatcher":
                # bpatcher may or may not have text
                pass
            else:
                # Fixed-size UI objects get parameter_enable
                d["parameter_enable"] = 0

            # bpatcher-specific attributes
            if self._bpatcher_attrs:
                d.update(self._bpatcher_attrs)

            # Embedded patcher (subpatcher or embedded bpatcher)
            if self._inner_patcher is not None:
                d["patcher"] = self._inner_patcher.to_dict()["patcher"]

            # Saved object attributes (for subpatchers)
            if self._saved_object_attributes is not None:
                d["saved_object_attributes"] = self._saved_object_attributes

            # Presentation mode
            if self.presentation:
                d["presentation"] = 1
                if self.presentation_rect is not None:
                    d["presentation_rect"] = self.presentation_rect

            # Extra attributes
            d.update(self.extra_attrs)

            return {"box": d}


from src.maxpat.builders import BuildersMixin


class Patcher(GraphMixin, AnalysisMixin, BuildersMixin):
    """A MAX patcher containing boxes and patchlines.

    The top-level container for a .maxpat file. Serializes to the complete
    .maxpat JSON structure with patcher wrapper, boxes array, and lines array.

    Inherits graph traversal (GraphMixin) and analysis (AnalysisMixin) methods
    via mixin classes for maintainability.
    """

    def __init__(
        self,
        db: ObjectDatabase | None = None,
        is_subpatcher: bool = False,
        allowed_packages: list[str] | None = None,
        *,
        domain_context: str = "max",
    ) -> None:
        """Create a new Patcher.

        Args:
            db: ObjectDatabase instance. Created automatically if None.
            is_subpatcher: If True, uses SUBPATCHER_RECT for window size.
            allowed_packages: Package filter passed to Box creation.
                None=allow all (default), []=core only,
                ["BEAP"]=core+BEAP objects.
            domain_context: Keyword-only. The scope this patcher lives in:
                "max" (default), "gen" (gen~ / .gendsp) or "rnbo" (rnbo~ /
                .rnbopat). ``add_box`` refuses names whose effective domain
                restriction excludes it (Q12 / C3). Never serialized.

        Raises:
            ValueError: domain_context is not in DOMAIN_SCOPES.
        """
        if domain_context not in DOMAIN_SCOPES:
            raise ValueError(
                f"domain_context must be one of {DOMAIN_SCOPES}, got {domain_context!r}"
            )
        if db is None:
            db = ObjectDatabase()

        self.db = db
        self.domain_context = domain_context
        self.allowed_packages = allowed_packages
        self.boxes: list[Box] = []
        self.lines: list[Patchline] = []
        self.props = copy.deepcopy(DEFAULT_PATCHER_PROPS)
        self._next_id = 1
        self._is_subpatcher = is_subpatcher
        # Parent box / patcher of an embedded inner patcher (set by
        # add_subpatcher, embedded add_bpatcher and from_dict). Port boxes
        # added or removed here resync the parent's ports (Q28 / B7).
        self._parent_box: Box | None = None
        self._parent_patcher: Patcher | None = None
        self._port_sync_suspended = False

        if is_subpatcher:
            self.props["rect"] = list(SUBPATCHER_RECT)

    def _gen_id(self) -> str:
        """Generate the next unique box ID."""
        box_id = f"obj-{self._next_id}"
        self._next_id += 1
        return box_id

    def add_to_presentation(self, box: Box, rect: list[float] | None = None) -> Box:
        """Put a box into presentation mode at ``rect``.

        Sets ``presentation=1`` and ``presentation_rect`` on the box. Works
        on both new and round-tripped boxes (presentation is a model field,
        overlaid onto ``_raw`` at serialize).

        When ``rect`` is omitted, the box is placed at x=15 just below the
        current presentation extent, sized from its patching_rect. Prefer an
        explicit rect placed within the relevant presentation section's grid;
        the auto-placement is a fallback so a new control is at least visible
        rather than silently absent.

        Args:
            box: Box to add to the presentation layout.
            rect: [x, y, width, height] in presentation coordinates.

        Returns:
            The same Box, for chaining.
        """
        if rect is None:
            bottoms = [
                b.presentation_rect for b in self.boxes
                if b.presentation and b.presentation_rect
            ]
            y = max((r[1] + r[3] for r in bottoms), default=0.0) + 10.0
            rect = [15.0, y, box.patching_rect[2], box.patching_rect[3]]
        box.presentation = True
        box.presentation_rect = [float(v) for v in rect]
        return box

    def bring_to_front(self, box: Box) -> None:
        """Move box to index 0 in boxes array (renders on top of all other objects).

        In .maxpat files, z-order is implicit: objects EARLIER in the boxes
        array render on top of later ones. This moves the box to index 0.

        Args:
            box: Box to bring to front.

        Raises:
            ValueError: If box is not in this patcher.
        """
        try:
            self.boxes.remove(box)
        except ValueError:
            raise ValueError(f"Box {box.id!r} not in this patcher")
        self.boxes.insert(0, box)

    def send_to_back(self, box: Box) -> None:
        """Move box to end of boxes array (renders behind all other objects).

        In .maxpat files, z-order is implicit: objects LATER in the boxes
        array render behind earlier ones. This moves the box to the last
        position.

        Args:
            box: Box to send to back.

        Raises:
            ValueError: If box is not in this patcher.
        """
        try:
            self.boxes.remove(box)
        except ValueError:
            raise ValueError(f"Box {box.id!r} not in this patcher")
        self.boxes.append(box)

    def set_z_index(self, box: Box, index: int) -> None:
        """Move box to a specific position in the boxes array for z-order control.

        Index 0 = on top of everything (same as bring_to_front).
        Index -1 or len(boxes) = behind everything (same as send_to_back).
        Out-of-range indices are clamped to valid range.

        Args:
            box: Box to reposition.
            index: Target index in boxes array.

        Raises:
            ValueError: If box is not in this patcher.
        """
        try:
            self.boxes.remove(box)
        except ValueError:
            raise ValueError(f"Box {box.id!r} not in this patcher")
        # Clamp index to valid range after removal
        max_idx = len(self.boxes)
        if index < 0:
            index = max(0, max_idx + 1 + index)
        index = min(index, max_idx)
        self.boxes.insert(index, box)

    # ------------------------------------------------------------------
    # Mutation / removal
    # ------------------------------------------------------------------

    def remove_box(self, box: Box) -> EditResult:
        """Remove a box and all patchlines connected to it.

        Removing an inlet/outlet box inside a ``p``/``patcher`` subpatcher
        or a bpatcher resyncs the parent box (Q28 / B7): its numinlets /
        numoutlets become the exact inner port count, a removed outlet's
        outlettype entry is deleted, and parent cords on the removed port
        (or left out of range) are removed from the PARENT patcher and
        returned in ``parent_orphaned``.

        Ports are indexed by x-rank and renumber like MAX: removing the
        port at rank k orphans the parent cords on port k and shifts the
        parent cords on ports > k down by one. The save gate still
        reports the surviving ports' x-rank change and refuses an
        unforced save of an existing file.

        Args:
            box: The box to remove.

        Returns:
            EditResult with the removed box. ``orphaned`` holds the cords
            removed from THIS patcher (every cord to or from the box);
            ``parent_orphaned`` holds the parent-patcher cords removed by
            the port resync (empty for any other box). Parent cords never
            appear in ``orphaned``.

        Raises:
            ValueError: If the box is not in this patcher.
        """
        if box not in self.boxes:
            raise ValueError(
                f"Box {box.id} not found in this patcher"
            )
        kind = box.maxclass if box.maxclass in ("inlet", "outlet") else None
        rank = self._port_rank(box) if kind is not None else None
        # Filter out all patchlines referencing this box (build new list),
        # reporting the removed ones as this patcher's orphans.
        orphaned: list[dict] = []
        surviving = []
        for pl in self.lines:
            if pl.source_id == box.id or pl.dest_id == box.id:
                orphaned.append(self._orphan_dict(pl))
            else:
                surviving.append(pl)
        self.lines = surviving
        self.boxes.remove(box)
        parent_orphaned: list[dict] = []
        if kind is not None:
            parent_orphaned = self._sync_parent_ports_after_remove(kind, rank)
        return EditResult(
            box=box,
            orphaned=orphaned,
            parent_orphaned=parent_orphaned,
        )

    # ------------------------------------------------------------------
    # Parent port sync (Q28 / B7)
    # ------------------------------------------------------------------

    def _port_rank(self, box: Box) -> int | None:
        """x-rank of a port box among this patcher's inlets or outlets."""
        ports = self.get_inlets() if box.maxclass == "inlet" else self.get_outlets()
        for i, b in enumerate(ports):
            if b is box:
                return i
        return None

    def _port_sync_parent(self) -> Box | None:
        """The parent box whose ports mirror this patcher's port boxes.

        None (no sync) when sync is suspended, this patcher has no parent
        back-ref, the parent box is no longer in its patcher, or the parent
        is neither a bpatcher nor a ``p``/``patcher`` newobj (gen~, rnbo~,
        poly~ and friends define their ports differently).
        """
        if getattr(self, "_port_sync_suspended", False):
            return None
        parent = getattr(self, "_parent_box", None)
        outer = getattr(self, "_parent_patcher", None)
        if parent is None or outer is None:
            return None
        if getattr(parent, "_inner_patcher", None) is not self:
            return None
        if not any(b is parent for b in outer.boxes):
            return None
        if parent.maxclass == "bpatcher":
            return parent
        if parent.maxclass == "newobj":
            first = (parent.text or "").split()[:1]
            if first and first[0] in ("p", "patcher"):
                return parent
        return None

    @staticmethod
    def _orphan_dict(pl: Patchline) -> dict:
        return {
            "source_id": pl.source_id,
            "source_outlet": pl.source_outlet,
            "dest_id": pl.dest_id,
            "dest_inlet": pl.dest_inlet,
        }

    def _sync_parent_ports_after_add(self, box: Box) -> list[dict]:
        """Grow the parent's ports after a port box was added.

        Grow only: the parent changes only when the inner port count now
        exceeds the parent's count. Then the new port is inserted at its
        x-rank k the way MAX renumbers on load: an inlet raises numinlets
        and shifts parent cords into inlets >= k up by one; an outlet
        inserts ``""`` into outlettype at k, raises numoutlets and shifts
        parent cords from outlets >= k up by one.

        When the parent already declares at least as many ports as the
        inner patcher now has (an embedded bpatcher declares its counts
        before its inner ports exist), the new box fills a declared port
        rather than inserting one, so nothing changes and no cord moves.
        Returns [] (nothing is ever orphaned).
        """
        if box.maxclass not in ("inlet", "outlet"):
            return []
        parent = self._port_sync_parent()
        if parent is None:
            return []
        outer = self._parent_patcher
        rank = self._port_rank(box)
        if box.maxclass == "inlet":
            n = len(self.get_inlets())
            if n <= parent.numinlets:
                return []
            parent.numinlets = n
            if rank is not None:
                for pl in outer.lines:
                    if pl.dest_id == parent.id and pl.dest_inlet >= rank:
                        pl.dest_inlet += 1
        else:
            n = len(self.get_outlets())
            if n <= parent.numoutlets:
                return []
            types = list(parent.outlettype or [])
            pos = len(types) if rank is None else min(rank, len(types))
            types.insert(pos, "")
            parent.outlettype = (types + [""] * n)[:n]
            parent.numoutlets = n
            if rank is not None:
                for pl in outer.lines:
                    if pl.source_id == parent.id and pl.source_outlet >= rank:
                        pl.source_outlet += 1
        return []

    def _sync_parent_ports_after_remove(
        self, kind: str, rank: int | None
    ) -> list[dict]:
        """Resync the parent's ports exactly after a port box was removed.

        ``rank`` is the removed box's x-rank k, computed before removal.
        Ports renumber the way MAX renumbers on load: when k was one of
        the parent's counted ports, parent cords on port k are orphaned
        and cords on ports > k shift down by one; an outlet also deletes
        outlettype[k]. The count then becomes the exact inner port count
        (outlettype padded/truncated to match), and any parent cord still
        out of range is orphaned too. Orphans are removed from the PARENT
        patcher and returned as orphan dicts carrying their pre-removal
        indices.
        """
        parent = self._port_sync_parent()
        if parent is None:
            return []
        outer = self._parent_patcher
        if kind == "inlet":
            counted = rank is not None and rank < parent.numinlets
            n = len(self.get_inlets())
            parent.numinlets = n
        else:
            counted = rank is not None and rank < parent.numoutlets
            n = len(self.get_outlets())
            types = list(parent.outlettype or [])
            if counted and rank < len(types):
                del types[rank]
            parent.outlettype = (types + [""] * n)[:n]
            parent.numoutlets = n
        orphaned: list[dict] = []
        surviving = []
        for pl in outer.lines:
            if kind == "inlet" and pl.dest_id == parent.id:
                idx = pl.dest_inlet
            elif kind == "outlet" and pl.source_id == parent.id:
                idx = pl.source_outlet
            else:
                surviving.append(pl)
                continue
            new_idx = idx
            if counted:
                if idx == rank:
                    orphaned.append(self._orphan_dict(pl))
                    continue
                if idx > rank:
                    new_idx = idx - 1
            if new_idx >= n:
                orphaned.append(self._orphan_dict(pl))
                continue
            if kind == "inlet":
                pl.dest_inlet = new_idx
            else:
                pl.source_outlet = new_idx
            surviving.append(pl)
        outer.lines = surviving
        return orphaned

    def remove_connection(
        self,
        src_box: Box,
        src_outlet: int,
        dst_box: Box,
        dst_inlet: int,
    ) -> None:
        """Remove a specific connection between two boxes.

        Args:
            src_box: Source box.
            src_outlet: Source outlet index.
            dst_box: Destination box.
            dst_inlet: Destination inlet index.

        Raises:
            ValueError: If no matching connection exists.
        """
        for i, pl in enumerate(self.lines):
            if (pl.source_id == src_box.id
                    and pl.source_outlet == src_outlet
                    and pl.dest_id == dst_box.id
                    and pl.dest_inlet == dst_inlet):
                self.lines.pop(i)
                return
        raise ValueError(
            f"Connection not found: {src_box.id}[{src_outlet}] -> "
            f"{dst_box.id}[{dst_inlet}]"
        )

    def _io_is_content_defined(self, box: Box) -> bool:
        """True when a box's I/O comes from its content, not its args.

        modify_box(args=...) keeps the I/O counts and cords of such boxes
        (Q6 / B2). True for: an embedded patcher, a bpatcher (the DB marks
        it variable_io with an uncomputable rule), no DB, a name in
        ``CONTENT_DEFINED_NAMES`` (alias-resolved), a name not in the DB
        (abstraction or unknown), or a DB object not marked ``variable_io``.
        False only for a DB ``variable_io`` object that hits none of these.
        """
        if box._inner_patcher is not None:
            return True
        if box.maxclass == "bpatcher":
            return True
        if not self.db:
            return True
        canonical = self.db._aliases.get(box.name, box.name)
        if canonical in CONTENT_DEFINED_NAMES:
            return True
        entry = self.db.lookup(box.name)
        if entry is None:
            return True
        return not entry.get("variable_io")

    def modify_box(
        self,
        box: Box,
        *,
        args: list[str] | None = None,
        position: list[float] | None = None,
        color: list[float] | None = None,
        extra_attrs: dict | None = None,
    ) -> EditResult:
        """Modify a box's attributes in-place.

        Changes args, position, color, or extra_attrs.

        ``args`` rules (Q6 / B2 / B3):

        - message/comment boxes: text becomes ``" ".join(args)`` with no
          maxclass prefix; I/O is unchanged.
        - content-defined boxes (see ``_io_is_content_defined``: embedded
          patchers, bpatchers, ``CONTENT_DEFINED_NAMES``, names not in the
          DB, and DB objects not marked ``variable_io``): text becomes
          ``name + args``; I/O counts, outlettype and every cord are kept.
        - DB ``variable_io`` objects: I/O is recomputed from the DB. Cords
          whose indices stay in range are kept; out-of-range cords are
          removed and returned in ``EditResult.orphaned`` (the only way
          this method orphans).
        - If the resulting text equals the current text, nothing else
          changes: no I/O recompute, no resize, no cord change.

        Loaded boxes have text, I/O, outlettype and patching_rect synced to
        ``_raw``. ``color`` and ``extra_attrs`` reach disk through change
        tracking (Q28); only keys model fields own (``_BOX_HANDLED_KEYS``,
        e.g. fontsize, presentation) are still copied into ``_raw``, and
        ``fontname`` / ``fontsize`` / ``presentation`` /
        ``presentation_rect`` are synced onto the box fields.

        Args:
            box: The box to modify (must be in this patcher).
            args: New arguments (rules above).
            position: New [x, y] position.
            color: New box color [r, g, b, a] -- sets extra_attrs["bgcolor"].
            extra_attrs: Dict of additional attributes to set/update.

        Returns:
            EditResult with the modified box and any orphaned connections.

        Raises:
            ValueError: If box is not in this patcher.
        """
        if box not in self.boxes:
            raise ValueError(
                f"Box {box.id} not found in this patcher"
            )

        orphaned: list[dict] = []

        if args is not None:
            new_args = list(args)
            if box.maxclass in ("message", "comment"):
                new_text = " ".join(new_args).strip()
                recompute = False
            else:
                new_text = " ".join([box.name] + new_args).strip()
                recompute = not self._io_is_content_defined(box)

            box.args = new_args

            # Identical text: nothing else changes (Q6 / B2).
            if new_text != box.text:
                box.text = new_text

                # Recompute I/O counts via database (variable_io only)
                if recompute:
                    box.numinlets, box.numoutlets = self.db.compute_io_counts(
                        box.name, new_args
                    )
                    box.outlettype = self.db.get_outlet_types(
                        box.name, new_args
                    )

                # Recalculate box size
                w, h = calculate_box_size(box.text, box.maxclass)
                box.patching_rect[2] = w
                box.patching_rect[3] = h

                # Orphan connections to removed outlets/inlets
                surviving = []
                for pl in self.lines:
                    orphan = False
                    if pl.source_id == box.id and pl.source_outlet >= box.numoutlets:
                        orphan = True
                    if pl.dest_id == box.id and pl.dest_inlet >= box.numinlets:
                        orphan = True
                    if orphan:
                        orphaned.append({
                            "source_id": pl.source_id,
                            "source_outlet": pl.source_outlet,
                            "dest_id": pl.dest_id,
                            "dest_inlet": pl.dest_inlet,
                        })
                    else:
                        surviving.append(pl)
                self.lines = surviving

                # Sync _raw dict
                if box._raw is not None:
                    box._raw["text"] = box.text
                    box._raw["numinlets"] = box.numinlets
                    box._raw["numoutlets"] = box.numoutlets
                    if "outlettype" in box._raw:
                        box._raw["outlettype"] = box.outlettype
                    box._raw["patching_rect"] = box.patching_rect

        if position is not None:
            box.patching_rect[0] = position[0]
            box.patching_rect[1] = position[1]
            if box._raw is not None:
                box._raw["patching_rect"] = box.patching_rect

        if color is not None:
            # Change tracking carries it to disk on loaded boxes (Q28).
            box.extra_attrs["bgcolor"] = color

        if extra_attrs is not None:
            # Sync model-field attrs to the Python fields the to_dict()
            # round-trip path reads (box.presentation / presentation_rect,
            # and the tracked fontname / fontsize).
            if "presentation" in extra_attrs:
                box.presentation = bool(extra_attrs["presentation"])
            if "presentation_rect" in extra_attrs:
                box.presentation_rect = list(extra_attrs["presentation_rect"])
            if "fontname" in extra_attrs:
                box.fontname = extra_attrs["fontname"]
            if "fontsize" in extra_attrs:
                box.fontsize = extra_attrs["fontsize"]
            box.extra_attrs.update(extra_attrs)
            if box._raw is not None:
                # The extra_attrs diff skips model-field keys; keep their
                # pre-Q28 raw write. Every other key reaches disk through
                # change tracking.
                for k, v in extra_attrs.items():
                    if k in _BOX_HANDLED_KEYS:
                        box._raw[k] = v

        return EditResult(box=box, orphaned=orphaned)

    def replace_box(
        self,
        old_box: Box,
        new_name: str,
        *,
        args: list[str] | None = None,
    ) -> EditResult:
        """Replace a box with a new object of a different type.

        Creates a new box at the old box's position, removes the old box,
        and returns ALL old connections as orphaned (no auto-remap per
        CONTEXT.md locked decision). The caller handles rewiring
        (``replace_box_safe`` rewires the in-range ones).

        The new box keeps the old box's identity (Q29 / B4;
        ``_carry_box_identity``): its index in the boxes list (z-order),
        presentation flag and presentation_rect, ``varname`` and MAX's
        common box attributes (color, textcolor, background, hidden,
        ignoreclick, hint, annotation), colour attributes valid on the new
        object, and the parameter blocks (parameter_enable /
        parameter_mappable, ``saved_attribute_attributes.valueof``) when the
        new object is parameter-capable. Fonts, size, arguments, I/O and
        other class settings are not carried.

        Inside a ``p``/``patcher`` subpatcher or bpatcher, replacing a port
        box with a port of the same kind leaves the parent box's ports and
        cords unchanged. Replacing it with a non-port or the other kind
        applies the remove_box resync for the old kind, then the add_box
        growth for the new one (Q28 / B7); parent cords that resync removes
        are returned ONLY in ``parent_orphaned`` (``orphaned`` stays this
        patcher's cords).

        Args:
            old_box: The box to replace (must be in this patcher).
            new_name: Name of the replacement object (e.g., "saw~").
            args: Optional arguments for the new object.

        Returns:
            EditResult with the new box (at the old box's list index) and
            all old connections as orphaned.

        Raises:
            ValueError: If old_box is not in this patcher; if new_name is
                ``p``/``patcher`` (use add_subpatcher) or a UI maxclass with
                no DB entry (Rule #1; review C4/C5, Q13); or if new_name's
                domain restriction excludes this patcher's domain_context
                (Q12 / C3). All are raised before anything changes.
        """
        if old_box not in self.boxes:
            raise ValueError(
                f"Box {old_box.id} not found in this patcher"
            )

        # Buildability and domain checks before orphan capture and
        # remove_box: a refused replacement must leave the patch untouched
        # (Q12 / C3, Q13).
        self._require_buildable(new_name)
        self._require_domain_scope(new_name)

        # Capture ALL connections to/from old box as orphaned dicts
        orphaned: list[dict] = []
        for pl in self.lines:
            if pl.source_id == old_box.id or pl.dest_id == old_box.id:
                orphaned.append({
                    "source_id": pl.source_id,
                    "source_outlet": pl.source_outlet,
                    "dest_id": pl.dest_id,
                    "dest_inlet": pl.dest_inlet,
                })

        # Record old position
        old_x = old_box.patching_rect[0]
        old_y = old_box.patching_rect[1]

        # Identity snapshot (Q29 / B4), taken before remove_box
        old_index = self.boxes.index(old_box)
        old_maxclass = old_box.maxclass
        identity = {
            "extra_attrs": copy.deepcopy(old_box.extra_attrs),
            "presentation": bool(old_box.presentation),
            "presentation_rect": (
                list(old_box.presentation_rect)
                if old_box.presentation_rect is not None else None
            ),
        }

        old_kind = old_box.maxclass if old_box.maxclass in ("inlet", "outlet") else None
        old_rank = self._port_rank(old_box) if old_kind is not None else None

        # Suspend the parent port sync so a port-for-port replacement is
        # not seen as a remove (which would drop the top port's parent
        # cords) followed by an add (Q28 / B7).
        prev_suspended = getattr(self, "_port_sync_suspended", False)
        self._port_sync_suspended = True
        try:
            # Remove old box and its patchlines
            self.remove_box(old_box)

            # Create replacement box at old position (skip overlap -- intentional placement)
            new_box = self.add_box(new_name, args=args, x=old_x, y=old_y, skip_overlap_check=True)
        finally:
            self._port_sync_suspended = prev_suspended

        new_kind = new_box.maxclass if new_box.maxclass in ("inlet", "outlet") else None
        parent_orphaned: list[dict] = []
        if old_kind != new_kind:
            if old_kind is not None:
                parent_orphaned = self._sync_parent_ports_after_remove(old_kind, old_rank)
            if new_kind is not None:
                self._sync_parent_ports_after_add(new_box)

        self._carry_box_identity(old_box, new_box, old_index, old_maxclass, identity)

        return EditResult(box=new_box, orphaned=orphaned, parent_orphaned=parent_orphaned)

    def _carry_box_identity(
        self,
        old_box: Box,
        new_box: Box,
        old_index: int,
        old_maxclass: str,
        identity: dict | None = None,
    ) -> None:
        """Give a replacement box the old box's identity (Q29 / B4).

        ``identity`` is the snapshot replace_box took before removing the old
        box (deep-copied extra_attrs, presentation, presentation_rect); when
        None it is read from ``old_box``. Carried:

        - z-order: the new box moves to ``old_index`` in the boxes list;
        - presentation: flag and a copy of presentation_rect, verbatim;
        - always: ``varname`` and MAX's common box attributes
          (``_IDENTITY_ALWAYS``);
        - colour keys (name contains "color", or a non-``valueof`` key of the
          old ``saved_attribute_attributes``) when the key is a DB attribute
          of the new object, the maxclass is unchanged, or the new box is a
          newobj and the key is ``bgcolor``;
        - parameter_enable / parameter_mappable when the new object is
          parameter-capable (its DB attributes include either);
        - ``saved_attribute_attributes``: entries of carried keys, plus
          ``valueof`` when the new object is parameter-capable; set only
          when non-empty.

        Values are deep copies. Fonts, size, args/text and I/O are not
        carried. Writes only model fields (``extra_attrs``, presentation),
        never a raw dict.
        """
        if identity is None:
            identity = {
                "extra_attrs": copy.deepcopy(old_box.extra_attrs),
                "presentation": bool(old_box.presentation),
                "presentation_rect": (
                    list(old_box.presentation_rect)
                    if old_box.presentation_rect is not None else None
                ),
            }

        self.set_z_index(new_box, old_index)

        if identity["presentation"]:
            new_box.presentation = True
            rect = identity["presentation_rect"]
            new_box.presentation_rect = list(rect) if rect is not None else None

        old_attrs = identity["extra_attrs"]
        attrs: set = set()
        if self.db is not None:
            attrs = set((self.db.attributes(new_box.name) or {}).keys())
        capable = any(k in attrs for k in _PARAMETER_KEYS)
        old_saa = old_attrs.get("saved_attribute_attributes")
        saa_keys = (
            {k for k in old_saa if k != "valueof"}
            if isinstance(old_saa, dict) else set()
        )
        same_class = new_box.maxclass == old_maxclass

        carried: dict = {}
        for key, value in old_attrs.items():
            if key == "saved_attribute_attributes":
                continue
            if key in _IDENTITY_ALWAYS:
                carried[key] = copy.deepcopy(value)
            elif "color" in key.lower() or key in saa_keys:
                if (key in attrs or same_class
                        or (new_box.maxclass == "newobj" and key == "bgcolor")):
                    carried[key] = copy.deepcopy(value)
            elif key in _PARAMETER_KEYS and capable:
                carried[key] = copy.deepcopy(value)

        if isinstance(old_saa, dict):
            saa = {
                k: copy.deepcopy(v) for k, v in old_saa.items()
                if k in carried or (k == "valueof" and capable)
            }
            if saa:
                carried["saved_attribute_attributes"] = saa

        new_box.extra_attrs.update(carried)

    def replace_box_safe(
        self,
        old_box: Box,
        new_name: str,
        *,
        args: list[str] | None = None,
        rewire: str = "auto",
    ) -> EditResult:
        """Replace a box, keep its identity and rewire every in-range cord.

        Safer default alternative to ``replace_box``. Delegates to
        ``replace_box`` (so the new box keeps the old box's identity: list
        index / z-order, presentation rect, varname, colours, parameter
        blocks; Q29 / B4), then in ``"auto"`` mode rewires every orphan
        whose outlet and inlet indices exist on the new box, whatever the
        I/O counts: ``pack 0 0`` -> ``pack 0 0 0`` keeps all its cords.
        Rewired cords keep their midpoints, order, colour, hidden flag and
        extra attributes (they are appended to ``lines``).

        Returned in ``orphaned`` (the caller rewires them by hand):

        - cords whose outlet/inlet index the new box lacks;
        - signal cords that would land on a control-only inlet -- the
          cords validation flags as "Signal outlet to control-only inlet"
          (a signal outlet of a source that is not an unverified,
          non-overridden MSP object, into an inlet that does not accept
          signal), so a rewire never creates a cord the save gate refuses.

        Use ``rewire="manual"`` to opt back into the explicit-orphan
        workflow of ``replace_box``.

        Mirrors P1-1 in 260427-hox FINDINGS. Use this in preference to
        ``replace_box`` for new code; ``replace_box`` is preserved for
        explicit orphan handling.

        Args:
            old_box: The box to replace (must be in this patcher).
            new_name: Name of the replacement object (e.g., "saw~").
            args: Optional arguments for the new object.
            rewire: ``"auto"`` (default) rewires every in-range orphan that
                passes the signal type check. ``"manual"`` always returns
                orphans without rewiring (same shape as ``replace_box``).

        Returns:
            EditResult with the new box. ``orphaned`` holds only the cords
            not rewired (all of them in manual mode). ``parent_orphaned``
            (parent-patcher cords removed by a port resync) is always passed
            through from replace_box.

        Raises:
            ValueError: If ``old_box`` is not in this patcher (raised by
                the underlying ``replace_box``), or if ``rewire`` is not
                ``"auto"`` or ``"manual"``.
        """
        if rewire not in ("auto", "manual"):
            raise ValueError(
                f"rewire must be 'auto' or 'manual', got {rewire!r}"
            )

        old_id = old_box.id
        # The old cords, keyed like the orphan dicts, so a rewire keeps
        # their attributes (replace_box removes them).
        old_lines = {
            (pl.source_id, pl.source_outlet, pl.dest_id, pl.dest_inlet): pl
            for pl in self.lines
            if pl.source_id == old_id or pl.dest_id == old_id
        }

        # Delegate -- handles validation, orphan capture, removal, identity
        # and creating the new box at the old position.
        result = self.replace_box(old_box, new_name, args=args)

        if rewire == "manual":
            return result

        from src.maxpat import walk
        from src.maxpat.validation import _inlet_accepts_signal

        new_box = result.box
        box_by_id = {b.id: b for b in self.boxes}
        remaining: list[dict] = []
        for o in result.orphaned:
            src_id, so = o["source_id"], o["source_outlet"]
            dst_id, di = o["dest_id"], o["dest_inlet"]
            # The new box stands in for the old id on either side (self-loops too).
            src = new_box if src_id == old_id else box_by_id.get(src_id)
            dst = new_box if dst_id == old_id else box_by_id.get(dst_id)
            if (src is None or dst is None
                    or not 0 <= so < src.numoutlets
                    or not 0 <= di < dst.numinlets):
                remaining.append(o)
                continue
            if self._rewire_type_gated(src, so, dst, di, walk, _inlet_accepts_signal):
                remaining.append(o)
                continue
            old = old_lines.get((src_id, so, dst_id, di))
            if old is None:
                self.add_connection(src, so, dst, di)
                continue
            pl = self.add_connection(
                src, so, dst, di,
                order=old.order,
                hidden=bool(old.hidden),
                midpoints=copy.deepcopy(old.midpoints),
            )
            pl.color = copy.deepcopy(old.color)
            pl.extra_attrs = copy.deepcopy(old.extra_attrs)

        # Parent-patcher cords dropped by the port resync are not rewired
        # here (they live in the parent): pass them through.
        return EditResult(
            box=new_box,
            orphaned=remaining,
            parent_orphaned=result.parent_orphaned,
        )

    def _rewire_type_gated(self, src: Box, so: int, dst: Box, di: int,
                           walk, inlet_accepts_signal) -> bool:
        """True when validation would flag src:so -> dst:di as signal into control-only.

        Mirrors validation's "Signal outlet to control-only inlet" removal
        proposal (Q29 / B4): a signal outlet, from a source that is not a
        lenient (non-overridden ``~``) MSP object, into an inlet that does
        not accept signal.
        """
        types = src.outlettype or []
        if so >= len(types) or types[so] != "signal":
            return False
        if self.db is None:
            return False
        name = walk.object_name({"maxclass": src.maxclass, "text": src.text})
        if name and name.endswith("~") and not self.db.is_overridden(name):
            return False
        return not inlet_accepts_signal(
            {"maxclass": dst.maxclass, "text": dst.text}, di, self.db
        )

    def insert_into_connection(
        self,
        source: Box,
        dest: Box,
        name: str,
        args: list[str] | None = None,
    ) -> EditResult:
        """Insert a new box into all connections between source and dest.

        Splices a new object into existing connections: removes old
        source->dest connections and creates source->new and new->dest
        connections for each. One shared inserted object handles all
        matching connections.

        When the inserted object has fewer inlets/outlets than connections
        found, wires what fits and returns the rest as orphaned in
        EditResult (no hard failure for I/O mismatch).

        Args:
            source: Source box of the connection(s) to splice into.
            dest: Destination box of the connection(s) to splice into.
            name: Object name for the inserted box (e.g., "*~").
            args: Optional arguments for the inserted box.

        Returns:
            EditResult with the new box and any orphaned connections.

        Raises:
            ValueError: If no connections exist between source and dest,
                or source/dest not in patcher. add_box refusals (Rule #1,
                p/patcher, domain scope) propagate before any cord changes.
        """
        if source not in self.boxes:
            raise ValueError(f"Box {source.id} not found in this patcher")
        if dest not in self.boxes:
            raise ValueError(f"Box {dest.id} not found in this patcher")

        # Find ALL patchlines between source and dest
        matching = [
            pl for pl in self.lines
            if pl.source_id == source.id and pl.dest_id == dest.id
        ]
        if not matching:
            raise ValueError(
                f"No connection found between {source.id} and {dest.id}"
            )

        # Create the new box (skip overlap -- _auto_position handles positioning)
        new_box = self.add_box(name, args=args, skip_overlap_check=True)

        # Auto-position below source
        self._auto_position(new_box, near_box=source)

        # Determine I/O capacity
        capacity = min(new_box.numinlets, new_box.numoutlets)

        orphaned: list[dict] = []

        for i, pl in enumerate(matching):
            # Remove old connection
            self.lines = [ln for ln in self.lines if ln is not pl]

            if i < capacity:
                # Wire through the new box: source->new and new->dest
                self.add_connection(source, pl.source_outlet, new_box, i)
                self.add_connection(new_box, i, dest, pl.dest_inlet)
            else:
                # I/O capacity exceeded -- orphan this connection
                orphaned.append({
                    "source_id": pl.source_id,
                    "source_outlet": pl.source_outlet,
                    "dest_id": pl.dest_id,
                    "dest_inlet": pl.dest_inlet,
                })

        return EditResult(box=new_box, orphaned=orphaned)

    # ------------------------------------------------------------------
    # Auto-positioning
    # ------------------------------------------------------------------

    def _find_clear_position(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        exclude_box: Box | None = None,
    ) -> tuple[float, float]:
        """Find a non-overlapping position starting from (x, y), snapped to 15px grid.

        Nudges down by 15px on collision to preserve horizontal signal flow.
        Wraps to the next column (x += 15, y resets) when y > 2400.
        Existing boxes are measured by ``sizing.rendered_rect`` (a message
        box covers ``len*8+25`` px unless this patcher was MAX-saved; Q27 /
        F5), falling back to the stored rect when it is invalid.

        Args:
            x: Starting x position.
            y: Starting y position.
            w: Width of the box to place.
            h: Height of the box to place.
            exclude_box: Optional box to exclude from collision checks (self-reposition).

        Returns:
            (x, y) tuple snapped to 15px grid with no overlap.
        """
        # Snap to 15px grid
        x = round(x / 15.0) * 15.0
        y = round(y / 15.0) * 15.0
        start_y = y

        max_saved = is_max_saved(self.props)
        rects = []
        for box in self.boxes:
            if box is exclude_box:
                continue
            r = rendered_rect(box, max_saved=max_saved)
            rects.append(r if r is not None else box.patching_rect)

        for _ in range(200):
            collision = False
            for rect in rects:
                bx, by, bw, bh = rect[:4]
                # Check overlap with COLLISION_PAD on both rects
                if not (
                    x + w + COLLISION_PAD <= bx - COLLISION_PAD
                    or x - COLLISION_PAD >= bx + bw + COLLISION_PAD
                    or y + h + COLLISION_PAD <= by - COLLISION_PAD
                    or y - COLLISION_PAD >= by + bh + COLLISION_PAD
                ):
                    collision = True
                    break
            if not collision:
                return (x, y)
            # Nudge down first (preserves horizontal signal flow)
            y += 15.0
            if y > 2400:
                y = start_y
                x += 15.0
        return (x, y)

    def _nudge_off_overlap(
        self, x: float, y: float, w: float, h: float
    ) -> tuple[float, float, Box | None]:
        """Move a requested rect off a real overlap (Q29 / B10).

        Existing boxes are measured like ``_find_clear_position``
        (``sizing.rendered_rect``, falling back to patching_rect). When no
        existing rect truly overlaps the candidate (a positive-area
        intersection; touching or nearby edges do not count), the requested
        position is returned unchanged -- no grid snap. Otherwise the
        candidate steps down 15px from the requested y (after y > 2400, y
        resets and x steps 15px right) until no rect is within
        COLLISION_PAD of it on any side, for at most 400 steps.

        Returns:
            (x, y, overlapped) -- overlapped is the first box the requested
            rect overlapped, or None when the position was kept.
        """
        max_saved = is_max_saved(self.props)
        rects: list[tuple[Box, list]] = []
        for box in self.boxes:
            r = rendered_rect(box, max_saved=max_saved)
            rects.append((box, r if r is not None else box.patching_rect))

        overlapped = None
        for box, rect in rects:
            bx, by, bw, bh = rect[:4]
            if x < bx + bw and bx < x + w and y < by + bh and by < y + h:
                overlapped = box
                break
        if overlapped is None:
            return (x, y, None)

        start_y = y
        cx, cy = x, y
        for _ in range(400):
            cy += 15.0
            if cy > 2400:
                cy = start_y
                cx += 15.0
            clear = True
            for _box, rect in rects:
                bx, by, bw, bh = rect[:4]
                if not (
                    cx + w + COLLISION_PAD <= bx
                    or bx + bw + COLLISION_PAD <= cx
                    or cy + h + COLLISION_PAD <= by
                    or by + bh + COLLISION_PAD <= cy
                ):
                    clear = False
                    break
            if clear:
                break
        return (cx, cy, overlapped)

    def _auto_position(self, box: Box, near_box: Box | None = None) -> None:
        """Position a box automatically, avoiding collisions.

        If near_box is provided, places below it with V_SPACING gap.
        Otherwise, places at the center of the patcher visible rect.

        Args:
            box: The box to position.
            near_box: Optional reference box to position relative to.
        """
        if near_box is not None:
            ideal_x = near_box.patching_rect[0]
            ideal_y = (
                near_box.patching_rect[1]
                + near_box.patching_rect[3]
                + V_SPACING
            )
        else:
            ideal_x = self.props["rect"][2] / 2.0
            ideal_y = self.props["rect"][3] / 2.0

        r = rendered_rect(box, max_saved=is_max_saved(self.props))
        w, h = (r[2], r[3]) if r is not None else (box.patching_rect[2], box.patching_rect[3])
        new_x, new_y = self._find_clear_position(ideal_x, ideal_y, w, h)
        box.patching_rect[0] = new_x
        box.patching_rect[1] = new_y

        # Sync _raw if present (round-trip fidelity)
        if box._raw is not None:
            box._raw["patching_rect"] = box.patching_rect

    # ------------------------------------------------------------------
    # Search / query
    # ------------------------------------------------------------------

    def find_boxes(
        self,
        *,
        id: str | None = None,
        name: str | None = None,
        maxclass: str | None = None,
        text: str | None = None,
        recursive: bool = False,
    ) -> list[Box]:
        """Return all boxes matching the given criteria (AND combination).

        Args:
            id: Exact match against ``box.id``.
            name: Match against ``box.name`` with bidirectional alias
                resolution when a DB is available.
            maxclass: Exact match against ``box.maxclass``.
            text: Substring match against ``box.text``.
            recursive: If True, also search boxes inside subpatchers.

        Returns:
            List of matching Box objects (may be empty).
        """
        # Resolve the search name to its canonical form for alias matching
        canonical_search: str | None = None
        if name is not None:
            aliases = getattr(self.db, "_aliases", None) if self.db else None
            if aliases:
                canonical_search = aliases.get(name, name)
            else:
                canonical_search = name

        results: list[Box] = []
        for box in self.boxes:
            if not self._box_matches(box, id, name, maxclass, text, canonical_search):
                continue
            results.append(box)
        if recursive:
            for box in self.boxes:
                if box._inner_patcher is not None:
                    results.extend(
                        box._inner_patcher.find_boxes(
                            id=id, name=name, maxclass=maxclass,
                            text=text, recursive=True,
                        )
                    )
        return results

    def find_box(
        self,
        *,
        id: str | None = None,
        name: str | None = None,
        maxclass: str | None = None,
        text: str | None = None,
        recursive: bool = False,
    ) -> Box | None:
        """Return the first box matching the given criteria, or None.

        Same criteria as :meth:`find_boxes` but short-circuits on first
        match.  When *recursive* is True, parent boxes are checked before
        inner-patcher boxes (depth-first).

        Args:
            id: Exact match against ``box.id``.
            name: Match against ``box.name`` with bidirectional alias
                resolution when a DB is available.
            maxclass: Exact match against ``box.maxclass``.
            text: Substring match against ``box.text``.
            recursive: If True, also search boxes inside subpatchers.

        Returns:
            First matching Box, or None.
        """
        # Resolve the search name to its canonical form for alias matching
        canonical_search: str | None = None
        if name is not None:
            aliases = getattr(self.db, "_aliases", None) if self.db else None
            if aliases:
                canonical_search = aliases.get(name, name)
            else:
                canonical_search = name

        for box in self.boxes:
            if self._box_matches(box, id, name, maxclass, text, canonical_search):
                return box
        if recursive:
            for box in self.boxes:
                if box._inner_patcher is not None:
                    found = box._inner_patcher.find_box(
                        id=id, name=name, maxclass=maxclass,
                        text=text, recursive=True,
                    )
                    if found is not None:
                        return found
        return None

    def _box_matches(
        self,
        box: Box,
        id: str | None,
        name: str | None,
        maxclass: str | None,
        text: str | None,
        canonical_search: str | None,
    ) -> bool:
        """Return True if *box* satisfies all non-None criteria."""
        if id is not None and box.id != id:
            return False
        if name is not None:
            aliases = getattr(self.db, "_aliases", None) if self.db else None
            if aliases:
                canonical_box = aliases.get(box.name, box.name)
                if canonical_box != canonical_search:
                    return False
            else:
                if box.name != name:
                    return False
        if maxclass is not None and box.maxclass != maxclass:
            return False
        if text is not None and text not in (box.text or ""):
            return False
        return True

    def get_inlets(self) -> list[Box]:
        """Return all inlet objects in this patcher, sorted left-to-right.

        Used to find inlet objects inside subpatchers for connecting to them.
        All inlet objects have identical text="inlet", so they cannot be
        distinguished by text -- use list index instead.

        Returns:
            List of inlet Box objects sorted by x-position (leftmost first).
        """
        inlets = [b for b in self.boxes if b.maxclass == "inlet"]
        inlets.sort(key=lambda b: b.patching_rect[0])
        return inlets

    def get_outlets(self) -> list[Box]:
        """Return all outlet objects in this patcher, sorted left-to-right.

        Used to find outlet objects inside subpatchers for connecting from them.
        All outlet objects have identical text="outlet", so they cannot be
        distinguished by text -- use list index instead.

        Returns:
            List of outlet Box objects sorted by x-position (leftmost first).
        """
        outlets = [b for b in self.boxes if b.maxclass == "outlet"]
        outlets.sort(key=lambda b: b.patching_rect[0])
        return outlets

    def populate_assistance_comments(self) -> "Patcher":
        """Auto-populate empty assistance comments on inlet/outlet objects.

        Walks all boxes in this patcher looking for subpatchers (boxes with
        _inner_patcher set). For each inner patcher, finds inlet/outlet objects
        with empty comment attributes and infers descriptive text from their
        connections:

        - For inlets: looks at what the inlet connects to downstream and
          generates a comment like "signal to cycle~ 440".
        - For outlets: looks at what connects upstream to the outlet and
          generates a comment like "signal from *~ 0.5".
        - If no connections found, uses positional fallback: "inlet 1",
          "outlet 2", etc.
        - Skips inlet/outlet objects that already have non-empty comments.
        - Recurses into nested subpatchers.

        On loaded boxes the comment reaches disk through change tracking
        (Q6, Q28).

        Returns:
            self for method chaining.
        """
        self._populate_comments_recursive(self)
        return self

    @staticmethod
    def _set_assistance_comment(box: Box, text: str) -> None:
        """Set an inferred assistance comment.

        Writes extra_attrs only: the creation path serializes it directly
        and, on loaded boxes, change tracking writes it back (Q28).
        """
        box.extra_attrs["comment"] = text

    @staticmethod
    def _populate_comments_recursive(patcher: "Patcher") -> None:
        """Recursively populate assistance comments in a patcher and its subpatchers."""
        for box in patcher.boxes:
            if box._inner_patcher is not None:
                inner = box._inner_patcher
                # Build a lookup from box id to box object for the inner patcher
                id_to_box: dict[str, Box] = {b.id: b for b in inner.boxes}

                # Find inlet and outlet boxes, track their position index
                inlet_boxes: list[Box] = []
                outlet_boxes: list[Box] = []
                for b in inner.boxes:
                    if b.maxclass == "inlet":
                        inlet_boxes.append(b)
                    elif b.maxclass == "outlet":
                        outlet_boxes.append(b)

                # Sort by x position to get correct index ordering
                inlet_boxes.sort(key=lambda b: b.patching_rect[0])
                outlet_boxes.sort(key=lambda b: b.patching_rect[0])

                # Process inlets: find downstream connections
                for idx, inlet_box in enumerate(inlet_boxes):
                    if inlet_box.extra_attrs.get("comment", "") != "":
                        continue  # Skip non-empty comments
                    # Find patchlines where this inlet is the source
                    downstream = None
                    for line in inner.lines:
                        if line.source_id == inlet_box.id:
                            dest_box = id_to_box.get(line.dest_id)
                            if dest_box is not None:
                                downstream = dest_box
                                break
                    if downstream is not None:
                        prefix = "signal" if inlet_box.name.endswith("~") else "signal" if downstream.name.endswith("~") else "data"
                        desc = downstream.text[:40] if downstream.text else downstream.name
                        Patcher._set_assistance_comment(inlet_box, f"{prefix} to {desc}")
                    else:
                        Patcher._set_assistance_comment(inlet_box, f"inlet {idx + 1}")

                # Process outlets: find upstream connections
                for idx, outlet_box in enumerate(outlet_boxes):
                    if outlet_box.extra_attrs.get("comment", "") != "":
                        continue  # Skip non-empty comments
                    # Find patchlines where this outlet is the destination
                    upstream = None
                    for line in inner.lines:
                        if line.dest_id == outlet_box.id:
                            src_box = id_to_box.get(line.source_id)
                            if src_box is not None:
                                upstream = src_box
                                break
                    if upstream is not None:
                        prefix = "signal" if outlet_box.name.endswith("~") else "signal" if upstream.name.endswith("~") else "data"
                        desc = upstream.text[:40] if upstream.text else upstream.name
                        Patcher._set_assistance_comment(outlet_box, f"{prefix} from {desc}")
                    else:
                        Patcher._set_assistance_comment(outlet_box, f"outlet {idx + 1}")

                # Recurse into the inner patcher
                Patcher._populate_comments_recursive(inner)

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        db: "ObjectDatabase | None" = None,
        *,
        domain_context: str | None = None,
    ) -> "Patcher":
        """Reconstruct a Patcher from a raw .maxpat JSON dict.

        Takes the full {"patcher": {...}} structure and rebuilds a Patcher
        with boxes and lines populated from the JSON. Boxes are created via
        Box.__new__(Box) to bypass DB validation (we are loading, not creating).
        The input is deep-copied first, so the Patcher never shares a nested
        object with the caller's dict (Q28 / B6).

        Args:
            data: A raw .maxpat dict with top-level "patcher" key.
            db: Optional ObjectDatabase instance.
            domain_context: Keyword-only scope of the top level ("max",
                "gen", "rnbo"). None derives it with detect_patcher_scope
                (classnamespace, else a top-level codebox, else max). Inner
                patchers get inner_patcher_scope: gen~/jit.gen... -> gen,
                rnbo~ -> rnbo, anything else inherits (Q12 / C3).

        Returns:
            Reconstructed Patcher instance.
        """
        return cls._from_owned_dict(
            copy.deepcopy(data), db, domain_context=domain_context
        )

    @classmethod
    def _from_owned_dict(
        cls,
        data: dict[str, Any],
        db: "ObjectDatabase | None" = None,
        *,
        domain_context: str | None = None,
    ) -> "Patcher":
        """from_dict body for a dict this Patcher may own (already copied).

        Model fields, extra_attrs and ``_raw`` alias ``data``'s nested
        objects (so in-place edits reach both); each box and line also gets
        a separate deep-copied load snapshot (``_loaded``) that to_dict
        diffs against (Q28). Inner patchers recurse here, not through
        from_dict, so nested dicts are copied once.
        """
        # Fail fast on structural errors (per CONTEXT.md locked decision)
        if "patcher" not in data and "boxes" not in data:
            raise ValueError(
                "Invalid .maxpat structure: dict must contain a 'patcher' key "
                "(or be a patcher dict itself with 'boxes')"
            )
        patcher_data = data.get("patcher", data)
        boxes_raw = patcher_data.get("boxes", [])
        if not isinstance(boxes_raw, list):
            raise TypeError(
                f"Invalid .maxpat structure: 'boxes' must be a list, "
                f"got {type(boxes_raw).__name__}"
            )

        if domain_context is None:
            domain_context = detect_patcher_scope(patcher_data)
        elif domain_context not in DOMAIN_SCOPES:
            raise ValueError(
                f"domain_context must be one of {DOMAIN_SCOPES}, got {domain_context!r}"
            )

        p = cls.__new__(cls)
        p.db = db if db is not None else ObjectDatabase()
        p.domain_context = domain_context
        p.allowed_packages = None
        p.boxes = []
        p.lines = []
        p._is_subpatcher = False
        p._parent_box = None
        p._parent_patcher = None
        p._port_sync_suspended = False

        # Rebuild props preserving key order (include boxes/lines placeholders)
        p.props = {}
        for key, val in patcher_data.items():
            if key == "boxes":
                p.props["boxes"] = None  # placeholder -- actual data in p.boxes
            elif key == "lines":
                p.props["lines"] = None  # placeholder -- actual data in p.lines
            else:
                p.props[key] = copy.deepcopy(val)

        # Rebuild boxes
        max_id_num = 0
        for box_entry in boxes_raw:
            box_data = box_entry.get("box", {})

            box = Box.__new__(Box)
            box.id = box_data.get("id", "obj-0")
            box.maxclass = box_data.get("maxclass", "newobj")
            box.text = box_data.get("text")
            box.numinlets = box_data.get("numinlets", 1)
            box.numoutlets = box_data.get("numoutlets", 0)
            box.outlettype = box_data.get("outlettype", [])
            box.patching_rect = box_data.get("patching_rect", [0.0, 0.0, 60.0, 22.0])
            box.fontname = box_data.get("fontname", FONT_NAME)
            box.fontsize = box_data.get("fontsize", FONT_SIZE)

            # Derive name from text field or maxclass
            if box.text and box.maxclass == "newobj":
                box.name = box.text.split()[0] if box.text else ""
                parts = box.text.split()
                box.args = parts[1:] if len(parts) > 1 else []
            elif box.maxclass in ("comment", "message"):
                box.name = box.maxclass
                box.args = []
            else:
                box.name = box.maxclass
                box.args = []

            # Presentation
            box.presentation = bool(box_data.get("presentation", 0))
            pres_rect = box_data.get("presentation_rect")
            box.presentation_rect = list(pres_rect) if pres_rect else None

            # Internal fields
            box.target_id = None
            box._inner_patcher = None
            box._saved_object_attributes = box_data.get("saved_object_attributes")
            box._bpatcher_attrs = None

            # Reconstruct inner patcher if present
            if "patcher" in box_data:
                box._inner_patcher = Patcher._from_owned_dict(
                    {"patcher": box_data["patcher"]},
                    db=p.db,
                    domain_context=inner_patcher_scope(box_data, p.domain_context),
                )
                # Back-refs for the parent port sync (Q28 / B7)
                box._inner_patcher._parent_box = box
                box._inner_patcher._parent_patcher = p

            # Extra attrs: everything not already handled
            box.extra_attrs = {
                k: v for k, v in box_data.items() if k not in _BOX_HANDLED_KEYS
            }
            # Load snapshot for change tracking (Q28): a separate deep copy,
            # so in-place edits of extra_attrs values show up as changes.
            box._loaded = {
                "fontname": box.fontname,
                "fontsize": box.fontsize,
                "extra_attrs": copy.deepcopy(box.extra_attrs),
            }

            # Preserve raw box dict for lossless round-trip
            # Exclude nested patcher -- handled separately via _inner_patcher
            raw = dict(box_data)
            if "patcher" in raw:
                raw["patcher"] = None  # sentinel preserves key position in ordered dict
            box._raw = raw
            # Load-time position snapshot (a copy: patching_rect is shared
            # with _raw and mutated in place by modify_box(position=...)).
            box._loaded_rect = tuple(box.patching_rect)

            p.boxes.append(box)

            # Track max ID number
            try:
                id_num = int(box.id.split("-")[-1])
                if id_num > max_id_num:
                    max_id_num = id_num
            except (ValueError, IndexError):
                pass

        # Rebuild lines with color, extra attrs, and raw dict preservation
        for line_entry in patcher_data.get("lines", []):
            line_data = line_entry.get("patchline", {})
            src = line_data.get("source", ["", 0])
            dst = line_data.get("destination", ["", 0])
            pl_extra = {k: v for k, v in line_data.items() if k not in _LINE_HANDLED_KEYS}
            pl = Patchline(
                source_id=src[0],
                source_outlet=src[1],
                dest_id=dst[0],
                dest_inlet=dst[1],
                order=line_data.get("order", 0),
                hidden=bool(line_data.get("hidden", 0)),
                midpoints=line_data.get("midpoints"),
                color=line_data.get("color"),
                extra_attrs=pl_extra,
                _raw=dict(line_data),
            )
            p.lines.append(pl)

        p._next_id = max_id_num + 1
        return p

    def to_dict(self) -> dict[str, Any]:
        """Serialize to complete .maxpat JSON structure.

        Preserves key ordering from the original file when round-tripping.
        boxes/lines placeholders in props mark their original position.

        Returns:
            {"patcher": {...}} dict matching the .maxpat format.
        """
        result: dict[str, Any] = {}
        for key, val in self.props.items():
            if key == "boxes":
                result["boxes"] = [box.to_dict() for box in self.boxes]
            elif key == "lines":
                result["lines"] = [line.to_dict() for line in self.lines]
            else:
                result[key] = copy.deepcopy(val)
        # If boxes/lines were not in props (new patcher), append them
        if "boxes" not in result:
            result["boxes"] = [box.to_dict() for box in self.boxes]
        if "lines" not in result:
            result["lines"] = [line.to_dict() for line in self.lines]
        return {"patcher": result}
