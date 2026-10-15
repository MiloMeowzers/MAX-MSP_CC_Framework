"""Patch graphs: the shared dict-level graph and the Patcher traversal mixin.

:class:`PatchGraph` is the one shared graph of a .maxpat dict (S1, Q20). It
is built in a single :func:`src.maxpat.walk.iter_patchers` pass and holds
every scope (top level, ``p`` / embedded bpatcher / poly~ / gen~ / mc.gen~
``data.patcher`` / rnbo~ patchers) with its boxes and parsed cords.
``review_patch`` builds it once per call and passes it to every critic, so
no critic re-parses lines or rebuilds adjacency. The graph is read-only: it
never mutates the patch dict, and malformed boxes, lines, ids and ports are
skipped rather than raising.

:class:`GraphMixin` provides the BFS traversal methods mixed into Patcher
(downstream/upstream queries, signal path tracing, connected components).
"""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING, NamedTuple

from src.maxpat import walk

if TYPE_CHECKING:
    from src.maxpat.patcher import Box, Patchline


# ---------------------------------------------------------------------------
# Shared dict-level graph (S1, Q20)
# ---------------------------------------------------------------------------

# Outlet types that carry audio.
SIGNAL_OUTLET_TYPES = frozenset({"signal", "multichannelsignal"})


def outlet_is_signal(box, outlet) -> bool:
    """True when *box* outlet *outlet* carries audio (Q3 / E1).

    Decided by the box's ``outlettype`` entry at that index (``signal`` or
    ``multichannelsignal``). Only when the box has no entry there
    (hand-built dicts) does it fall back to the ``~``-name test. A missing
    or non-dict box is never signal.
    """
    if not isinstance(box, dict):
        return False
    outlettype = box.get("outlettype")
    if (
        isinstance(outlettype, list)
        and isinstance(outlet, int)
        and 0 <= outlet < len(outlettype)
    ):
        entry = outlettype[outlet]
        return isinstance(entry, str) and entry in SIGNAL_OUTLET_TYPES
    return walk.box_name(box).endswith("~")


class Edge(NamedTuple):
    """One well-formed cord of a scope: ``src`` outlet -> ``dst`` inlet.

    ``signal`` is :func:`outlet_is_signal` of the source box at ``outlet``;
    ``line`` is the raw patchline dict.
    """

    src: object
    outlet: int
    dst: object
    inlet: int
    signal: bool
    line: dict


def _valid_id(value) -> bool:
    return (
        isinstance(value, (str, int))
        and not isinstance(value, bool)
        and bool(value)
    )


def _valid_port(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _entry_box(entry):
    """The box of a boxes-array entry: ``entry["box"]``, or a bare box dict."""
    if not isinstance(entry, dict):
        return None
    box = entry.get("box")
    if isinstance(box, dict):
        return box
    if "id" in entry:
        return entry
    return None


def _parse_endpoint(value):
    if not isinstance(value, (list, tuple)) or len(value) < 2:
        return None
    box_id, port = value[0], value[1]
    if not isinstance(box_id, (str, int)) or isinstance(box_id, bool):
        return None
    if not _valid_port(port):
        return None
    return box_id, port


class Scope:
    """One patcher of a :class:`PatchGraph`.

    Attributes:
        path: the ``walk.iter_patchers`` path tuple (``()`` at the top).
        key: ``walk.path_ids(path)`` (``obj-1/obj-2``; ``""`` at the top).
        prefix: ``walk.path_prefix(path)`` (``[p synth > gen~] ``).
        context: max / gen / rnbo / poly / bpatcher.
        scope: ``walk.scope_of(context)`` (max / gen / rnbo).
        patcher: the raw patcher dict (never mutated).
        boxes: id -> box, in first-seen order; a duplicate id keeps its
            first position and its last box.
        box_list: every box with a valid id, in array order (duplicates kept).
        edges: one :class:`Edge` per well-formed cord, in line order.
        out_edges / in_edges: id -> edges leaving / entering it, line order.
        parent: the enclosing Scope (None at the top).
        container: the id of the box holding this patcher (None at the top).
    """

    __slots__ = (
        "path", "key", "prefix", "context", "scope", "patcher", "boxes",
        "box_list", "edges", "out_edges", "in_edges", "parent", "container",
        "_ids",
    )

    def __init__(self, path: tuple, patcher, context: str, parent=None):
        self.path = path
        self.key = walk.path_ids(path)
        self.prefix = walk.path_prefix(path)
        self.context = context
        self.scope = walk.scope_of(context)
        self.patcher = patcher if isinstance(patcher, dict) else {}
        self.parent = parent
        self.container = path[-1][0] if path else None
        self._ids = tuple(box_id for box_id, _ in path)

        boxes: dict = {}
        box_list: list = []
        raw_boxes = self.patcher.get("boxes")
        for entry in raw_boxes if isinstance(raw_boxes, list) else ():
            box = _entry_box(entry)
            if box is None:
                continue
            box_id = box.get("id")
            if not _valid_id(box_id):
                continue
            boxes[box_id] = box
            box_list.append(box)
        self.boxes = boxes
        self.box_list = box_list

        edges: list = []
        out_edges: dict = {}
        in_edges: dict = {}
        raw_lines = self.patcher.get("lines")
        for entry in raw_lines if isinstance(raw_lines, list) else ():
            if not isinstance(entry, dict):
                continue
            line = entry.get("patchline", entry)
            if not isinstance(line, dict):
                continue
            src = _parse_endpoint(line.get("source"))
            dst = _parse_endpoint(line.get("destination"))
            if src is None or dst is None:
                continue
            edge = Edge(
                src[0], src[1], dst[0], dst[1],
                outlet_is_signal(boxes.get(src[0]), src[1]), line,
            )
            edges.append(edge)
            out_edges.setdefault(edge.src, []).append(edge)
            in_edges.setdefault(edge.dst, []).append(edge)
        self.edges = edges
        self.out_edges = out_edges
        self.in_edges = in_edges

    def __repr__(self) -> str:
        return f"Scope({self.key or '<top>'!r}, {self.context})"


class PatchGraph:
    """Every scope of one patch dict, built once and shared (S1, Q20).

    ``scopes`` is in ``walk.iter_patchers`` pre-order, top first. There is
    always a top scope: when the walker yields nothing (no usable patcher)
    the top is an empty max scope with patcher ``{}``.
    """

    __slots__ = ("scopes", "_by_ids")

    def __init__(self, scopes: list):
        self.scopes = scopes
        self._by_ids = {}
        for scope in scopes:
            self._by_ids.setdefault(scope._ids, scope)

    @classmethod
    def build(cls, patch, scope: "str | None" = None) -> "PatchGraph":
        """One ``walk.iter_patchers(patch, scope=scope)`` pass; read-only."""
        scopes: list = []
        by_ids: dict = {}
        for path, patcher, context in walk.iter_patchers(patch, scope=scope):
            ids = tuple(box_id for box_id, _ in path)
            parent = by_ids.get(ids[:-1]) if ids else None
            node = Scope(path, patcher, context, parent=parent)
            by_ids.setdefault(ids, node)
            scopes.append(node)
        if not scopes:
            scopes.append(Scope((), {}, "max"))
        return cls(scopes)

    @property
    def top(self) -> Scope:
        return self.scopes[0]

    def children(self, scope: Scope) -> list:
        """Scopes directly inside *scope*, in pre-order."""
        return [s for s in self.scopes if s.parent is scope]

    def child(self, scope: Scope, box_id) -> "Scope | None":
        """The scope embedded in *scope*'s box *box_id*, or None."""
        for s in self.scopes:
            if s.parent is scope and s.container == str(box_id):
                return s
        return None

    def subtree(self, scope: Scope, box_id) -> list:
        """The inner scope of container *box_id* in *scope* plus everything
        below it, in pre-order (``[]`` when the box holds no patcher)."""
        root = self.child(scope, box_id)
        if root is None:
            return []
        out = []
        for s in self.scopes:
            node = s
            while node is not None and node is not root:
                node = node.parent
            if node is root:
                out.append(s)
        return out


class GraphMixin:
    """Graph traversal methods mixed into Patcher.

    Expects ``self.boxes``, ``self.lines``, and ``self.db`` to be provided
    by the host class (Patcher).
    """

    def _build_adj(
        self, signal_only: bool = False
    ) -> tuple[dict[str, list[tuple[str, int]]], dict[str, list[tuple[str, int]]], "dict[str, Box]"]:
        """Build forward and reverse adjacency dicts from self.lines.

        Args:
            signal_only: If True, skip connections where either source or
                destination box name does not end with ``~``.

        Returns:
            (forward, reverse, box_map) where:
            - forward[source_id] = sorted list of (dest_id, source_outlet) tuples
            - reverse[dest_id] = sorted list of (source_id, dest_inlet) tuples
            - box_map maps id -> Box for fast lookups
        """
        box_map: dict[str, Box] = {b.id: b for b in self.boxes}
        forward: dict[str, list[tuple[str, int]]] = {}
        reverse: dict[str, list[tuple[str, int]]] = {}

        for line in self.lines:
            src_id = line.source_id
            dst_id = line.dest_id
            if src_id not in box_map or dst_id not in box_map:
                continue
            if signal_only:
                src_box = box_map[src_id]
                dst_box = box_map[dst_id]
                if not src_box.name.endswith("~") or not dst_box.name.endswith("~"):
                    continue
            forward.setdefault(src_id, []).append((dst_id, line.source_outlet))
            reverse.setdefault(dst_id, []).append((src_id, line.dest_inlet))

        # Sort by outlet/inlet index for left-to-right ordering
        for v in forward.values():
            v.sort(key=lambda t: t[1])
        for v in reverse.values():
            v.sort(key=lambda t: t[1])

        return forward, reverse, box_map

    def downstream(self, box: "Box", *, signal_only: bool = False) -> "list[Box]":
        """Return all boxes reachable downstream from *box* (BFS, full chain).

        Results are ordered by outlet index (left to right) for natural
        signal-flow reading. The starting box is NOT included.

        Traversal crosses subpatcher boundaries: when a downstream neighbor
        has ``_inner_patcher``, the traversal follows through inlet objects
        inside the subpatcher and continues out through outlet objects.

        Args:
            box: Starting box.
            signal_only: If True, only follow connections where both source
                and destination box names end with ``~``.

        Returns:
            List of downstream Box objects.

        Raises:
            ValueError: If *box* is not in this patcher.
        """
        if box not in self.boxes:
            raise ValueError(
                f"Box '{box.id}' ({box.name}) is not in this patcher"
            )
        return self._traverse(box, direction="downstream", signal_only=signal_only)

    def upstream(self, box: "Box", *, signal_only: bool = False) -> "list[Box]":
        """Return all boxes reachable upstream from *box* (BFS, full chain).

        Results are ordered by inlet index (left to right). The starting
        box is NOT included.

        Traversal crosses subpatcher boundaries by following outlet objects
        inside subpatchers back to their sources.

        Args:
            box: Starting box.
            signal_only: If True, only follow connections where both source
                and destination box names end with ``~``.

        Returns:
            List of upstream Box objects.

        Raises:
            ValueError: If *box* is not in this patcher.
        """
        if box not in self.boxes:
            raise ValueError(
                f"Box '{box.id}' ({box.name}) is not in this patcher"
            )
        return self._traverse(box, direction="upstream", signal_only=signal_only)

    def _traverse(
        self,
        start: "Box",
        *,
        direction: str,
        signal_only: bool = False,
    ) -> "list[Box]":
        """BFS traversal in given direction, crossing subpatcher boundaries.

        Args:
            start: The starting box.
            direction: ``"downstream"`` or ``"upstream"``.
            signal_only: Filter to signal-only connections.

        Returns:
            Ordered list of reachable Box objects (starting box excluded).
        """
        result: list[Box] = []
        # visited tracks (id(patcher), box_id) to handle cross-patcher traversal
        visited: set[tuple[int, str]] = set()
        visited.add((id(self), start.id))

        # Queue items: (patcher, box_id) -- the patcher that owns the box
        queue: deque[tuple[GraphMixin, str]] = deque()

        # Seed the queue with immediate neighbors in this patcher
        self._enqueue_neighbors(
            queue, visited, result, self, start, direction, signal_only
        )

        while queue:
            patcher, box_id = queue.popleft()
            box_map = {b.id: b for b in patcher.boxes}
            current_box = box_map.get(box_id)
            if current_box is None:
                continue

            # If this box has an inner patcher, cross the boundary
            if current_box._inner_patcher is not None:
                self._cross_subpatcher(
                    queue, visited, result, patcher, current_box,
                    direction, signal_only
                )

            # Enqueue neighbors of current_box within its own patcher
            self._enqueue_neighbors(
                queue, visited, result, patcher, current_box, direction, signal_only
            )

        return result

    def _enqueue_neighbors(
        self,
        queue: "deque[tuple[GraphMixin, str]]",
        visited: set[tuple[int, str]],
        result: "list[Box]",
        patcher: "GraphMixin",
        box: "Box",
        direction: str,
        signal_only: bool,
    ) -> None:
        """Add unvisited neighbors of *box* to the BFS queue and result."""
        forward, reverse, box_map = patcher._build_adj(signal_only=signal_only)

        if direction == "downstream":
            neighbors = forward.get(box.id, [])
        else:
            neighbors = reverse.get(box.id, [])

        for neighbor_id, _index in neighbors:
            key = (id(patcher), neighbor_id)
            if key in visited:
                continue
            visited.add(key)
            neighbor_box = box_map.get(neighbor_id)
            if neighbor_box is not None:
                result.append(neighbor_box)
                queue.append((patcher, neighbor_id))

    def _cross_subpatcher(
        self,
        queue: "deque[tuple[GraphMixin, str]]",
        visited: set[tuple[int, str]],
        result: "list[Box]",
        parent_patcher: "GraphMixin",
        sub_box: "Box",
        direction: str,
        signal_only: bool,
    ) -> None:
        """Cross into a subpatcher boundary during traversal.

        For downstream: find inlet/inlet~ objects inside and continue from them.
        For upstream: find outlet/outlet~ objects inside and trace back from them.
        """
        inner = sub_box._inner_patcher
        if inner is None:
            return

        if direction == "downstream":
            # Find connections entering sub_box in parent, map to inner inlet objects
            # Then find outlet/outlet~ objects in inner, map back to parent connections
            # Step 1: find inlet objects inside
            for inner_box in inner.boxes:
                if inner_box.name in ("inlet", "inlet~"):
                    key = (id(inner), inner_box.id)
                    if key not in visited:
                        visited.add(key)
                        result.append(inner_box)
                        queue.append((inner, inner_box.id))

            # Step 2: find outlet objects that lead back to parent
            for inner_box in inner.boxes:
                if inner_box.name in ("outlet", "outlet~"):
                    key = (id(inner), inner_box.id)
                    if key not in visited:
                        visited.add(key)
                        result.append(inner_box)
                        # Outlet objects map back to parent's sub_box outlets
                        # Enqueue sub_box's downstream in parent (already handled
                        # by normal traversal since sub_box is in the result path)
        else:
            # upstream: find outlet objects inside and trace backwards
            for inner_box in inner.boxes:
                if inner_box.name in ("outlet", "outlet~"):
                    key = (id(inner), inner_box.id)
                    if key not in visited:
                        visited.add(key)
                        result.append(inner_box)
                        queue.append((inner, inner_box.id))

            # Also expose inlet objects (they connect back to parent upstream)
            for inner_box in inner.boxes:
                if inner_box.name in ("inlet", "inlet~"):
                    key = (id(inner), inner_box.id)
                    if key not in visited:
                        visited.add(key)
                        result.append(inner_box)

    def signal_path(self, box: "Box") -> "list[Box]":
        """Return the full signal chain passing through *box* (~ objects only).

        Combines upstream signal sources (reversed) + box + downstream signal
        sinks. Only includes boxes whose name ends with ``~``.

        Args:
            box: The box to trace the signal path through.

        Returns:
            Ordered list of ~ boxes from source to sink.

        Raises:
            ValueError: If *box* is not in this patcher.
        """
        if box not in self.boxes:
            raise ValueError(
                f"Box '{box.id}' ({box.name}) is not in this patcher"
            )
        upstream_signal = self.upstream(box, signal_only=True)
        downstream_signal = self.downstream(box, signal_only=True)
        # Reverse upstream so sources come first
        upstream_signal = list(reversed(upstream_signal))
        is_signal = box.name.endswith("~")
        if is_signal:
            return upstream_signal + [box] + downstream_signal
        else:
            return upstream_signal + downstream_signal

    def connected_components(self) -> "list[list[Box]]":
        """Return groups of interconnected boxes.

        Uses undirected BFS. Disconnected objects (no connections) are
        returned as single-element groups. Components are sorted by size
        (largest first).

        Returns:
            List of Box lists, each list is a connected component.
        """
        if not self.boxes:
            return []

        # Build undirected adjacency from lines
        undirected: dict[str, set[str]] = {}
        box_map: dict[str, Box] = {b.id: b for b in self.boxes}

        for line in self.lines:
            src = line.source_id
            dst = line.dest_id
            if src in box_map and dst in box_map:
                undirected.setdefault(src, set()).add(dst)
                undirected.setdefault(dst, set()).add(src)

        visited: set[str] = set()
        components: list[list[Box]] = []

        for box in self.boxes:
            if box.id in visited:
                continue
            visited.add(box.id)

            if box.id not in undirected:
                # Disconnected box -> single-element group
                components.append([box])
                continue

            # BFS to find connected component
            component: list[Box] = [box]
            queue: deque[str] = deque()
            for neighbor in undirected.get(box.id, set()):
                if neighbor not in visited:
                    queue.append(neighbor)

            while queue:
                node_id = queue.popleft()
                if node_id in visited:
                    continue
                visited.add(node_id)
                node_box = box_map.get(node_id)
                if node_box is not None:
                    component.append(node_box)
                for neighbor in undirected.get(node_id, set()):
                    if neighbor not in visited:
                        queue.append(neighbor)

            components.append(component)

        # Sort largest first
        components.sort(key=lambda c: len(c), reverse=True)
        return components
