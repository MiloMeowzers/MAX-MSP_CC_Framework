"""Patch graphs: the shared dict-level graph and the Patcher traversal mixin.

:class:`PatchGraph` is the one shared graph of a .maxpat dict (S1, Q20). It
is built in a single :func:`src.maxpat.walk.iter_patchers` pass and holds
every scope (top level, ``p`` / embedded bpatcher / poly~ / gen~ / mc.gen~
``data.patcher`` / rnbo~ patchers) with its boxes and parsed cords.
``review_patch`` builds it once per call and passes it to every critic, so
no critic re-parses lines or rebuilds adjacency. The graph is read-only: it
never mutates the patch dict, and malformed boxes, lines, ids and ports are
skipped rather than raising.

:class:`PatchGraph` traversal (G9, Q20) -- ``downstream`` / ``upstream``:

* **Port-exact crossing.** A cord into a ``p`` / embedded bpatcher (inner
  context max or bpatcher) at inlet *i* enters only the inner ``inlet`` box
  of x-rank *i* (rank by ``(patching_rect x, array index)``, as MAX numbers
  ports); an inner ``outlet`` of rank *k* leaves only through the
  container's outlet *k*. Upstream mirrors this. Gen, rnbo and poly
  containers, and containers without an embedded patcher, are opaque: they
  are expanded like ordinary boxes and never entered.
* **Bridging.** ``send``/``s`` -> ``receive``/``r`` and ``send~``/``s~`` ->
  ``receive~``/``r~`` are linked by channel name (first argument) across
  every scope.
* **Signal test.** With ``signal_only`` a cord is followed when the source
  outlet's ``outlettype`` is signal / multichannelsignal (:func:`outlet_is_signal`)
  and the destination accepts signal at that inlet (a container, or the
  DB says so); never by the ``~`` name. Port boxes and crossing containers
  are transparent.
* **Adjacency once.** Scope adjacency is built once per graph; no traversal
  rebuilds it per node.

:meth:`PatchGraph.control_walk` (Q24 / R8) is a separate, additive
generator over **control** cords for the uninitialized-state check: a cord
whose ``Edge.signal`` is True is never followed, ``p`` / embedded bpatcher
containers and their port boxes are crossed port-exactly and never yielded,
and named bridges link ``send``/``s`` -> ``receive``/``r``, ``value``/``v``,
``pv`` (same, ancestor or descendant scope) and ``;`` remote-message
segments (a message box -> ``receive``/``r`` and ``value``/``v`` of each
target) in non-gen, non-rnbo scopes. BFS with a visited set; each cord or
bridge hop adds one to the depth and a node at ``max_depth`` is yielded but
not expanded. The bridge map is built lazily once per graph.

:class:`GraphMixin` provides the traversal methods mixed into Patcher
(downstream/upstream queries, signal path tracing, connected components);
downstream / upstream / signal_path run on one PatchGraph per call.
"""

from __future__ import annotations

import re
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
    """A non-negative int port index (bools excluded; WR-01: a negative
    index used to pass and read ports from the end)."""
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


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

    __slots__ = ("scopes", "_by_ids", "_child_index", "_ranks", "_channels",
                 "_control_bridges")

    def __init__(self, scopes: list):
        self.scopes = scopes
        self._by_ids = {}
        self._child_index = {}
        for scope in scopes:
            self._by_ids.setdefault(scope._ids, scope)
            if scope.parent is not None:
                self._child_index.setdefault((id(scope.parent), scope.container), scope)
        self._ranks: dict = {}
        self._channels = None
        self._control_bridges = None

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
        return self._child_index.get((id(scope), str(box_id)))

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



    # -- traversal (G9, Q20) -------------------------------------------------

    def _port_ranks(self, scope: Scope) -> dict:
        """``{"inlet": {rank: id}, "outlet": {rank: id}, "rank": {id: rank}}``
        for *scope*'s port boxes, ranked by ``(patching_rect x, array index)``."""
        cached = self._ranks.get(id(scope))
        if cached is not None:
            return cached
        out: dict = {"inlet": {}, "outlet": {}, "rank": {}}
        for kind in ("inlet", "outlet"):
            ports = []
            for index, box in enumerate(scope.box_list):
                if walk.box_maxclass(box) != kind:
                    continue
                rect = box.get("patching_rect")
                try:
                    x = float(rect[0])
                except (TypeError, ValueError, IndexError, KeyError):
                    x = 0.0
                ports.append((x, index, box.get("id")))
            ports.sort(key=lambda p: (p[0], p[1]))
            for rank, (_x, _i, box_id) in enumerate(ports):
                out[kind].setdefault(rank, box_id)
                out["rank"].setdefault(box_id, rank)
        self._ranks[id(scope)] = out
        return out

    def _crossing_child(self, scope: Scope, box_id) -> "Scope | None":
        """The inner scope of a port-crossing container (max / bpatcher), or None."""
        inner = self.child(scope, box_id)
        if inner is not None and inner.context in _CROSSING_CONTEXTS:
            return inner
        return None

    def _channel_maps(self) -> dict:
        """``{(role, kind, channel): [(scope, id), ...]}`` over every scope."""
        if self._channels is not None:
            return self._channels
        maps: dict = {}
        for scope in self.scopes:
            for box_id, box in scope.boxes.items():
                name = walk.box_name(box)
                role_kind = _BRIDGE_NAMES.get(name)
                if role_kind is None:
                    continue
                args = walk.box_args(box)
                if not args:
                    continue
                maps.setdefault(role_kind + (args[0],), []).append((scope, box_id))
        self._channels = maps
        return maps

    def _bridged(self, scope: Scope, box_id, role: str, signal_only: bool) -> list:
        """Partners of a sender (role ``send``) / receiver (role ``receive``)."""
        box = scope.boxes.get(box_id)
        role_kind = _BRIDGE_NAMES.get(walk.box_name(box)) if box is not None else None
        if role_kind is None or role_kind[0] != role:
            return []
        kind = role_kind[1]
        if signal_only and kind != "signal":
            return []
        args = walk.box_args(box)
        if not args:
            return []
        other = "receive" if role == "send" else "send"
        return self._channel_maps().get((other, kind, args[0]), [])

    def _transparent(self, scope: Scope, box_id) -> bool:
        box = scope.boxes.get(box_id)
        if walk.box_maxclass(box) in ("inlet", "outlet"):
            return True
        return self._crossing_child(scope, box_id) is not None

    def downstream(self, scope: Scope, box_id, *, signal_only: bool = False, db=None) -> list:
        """``(scope, box_id)`` pairs reachable downstream of *box_id* in *scope*.

        BFS discovery order, the start excluded. Neighbours of each node are
        its out-edges stable-sorted by outlet. Crossing is port-exact,
        send/receive pairs are bridged, and ``signal_only`` follows a cord
        only when the source outlet is signal and the destination accepts
        signal (permissive when *db* is None). See the module docstring.
        """
        return self._traverse(scope, box_id, downstream=True, signal_only=signal_only, db=db)

    def upstream(self, scope: Scope, box_id, *, signal_only: bool = False, db=None) -> list:
        """``(scope, box_id)`` pairs reachable upstream of *box_id* (mirror of
        :meth:`downstream`: neighbours by in-edges stable-sorted by inlet)."""
        return self._traverse(scope, box_id, downstream=False, signal_only=signal_only, db=db)

    def _traverse(self, start_scope: Scope, start_id, *, downstream: bool,
                  signal_only: bool, db) -> list:
        result: list = []
        visited = {(id(start_scope), start_id)}
        crossed: set = set()
        queue: deque = deque([(start_scope, start_id)])

        def mark(scope, box_id) -> bool:
            key = (id(scope), box_id)
            if key in visited:
                return False
            visited.add(key)
            result.append((scope, box_id))
            return True

        def reach(scope, box_id, port) -> None:
            """Reach *box_id* through a cord at *port* (inlet downstream,
            outlet upstream)."""
            if box_id not in scope.boxes:
                return
            inner = self._crossing_child(scope, box_id)
            if inner is None:
                if mark(scope, box_id):
                    queue.append((scope, box_id))
                return
            mark(scope, box_id)
            key = (id(scope), box_id, downstream, port)
            if key in crossed:
                return
            crossed.add(key)
            port_id = self._port_ranks(inner)["inlet" if downstream else "outlet"].get(port)
            if port_id is not None and port_id in inner.boxes:
                if mark(inner, port_id):
                    queue.append((inner, port_id))

        while queue:
            scope, box_id = queue.popleft()
            box = scope.boxes.get(box_id)

            # Leaving a crossing scope through a port box
            exit_kind = "outlet" if downstream else "inlet"
            if (
                walk.box_maxclass(box) == exit_kind
                and scope.parent is not None
                and scope.context in _CROSSING_CONTEXTS
            ):
                parent = scope.parent
                container = self._container_id(parent, scope.container)
                rank = self._port_ranks(scope)["rank"].get(box_id)
                if container is not None and rank is not None:
                    key = (id(parent), container, not downstream, rank)
                    if key not in crossed:
                        crossed.add(key)
                        if downstream:
                            edges = [e for e in parent.out_edges.get(container, ()) if e.outlet == rank]
                            for e in edges:
                                reach(parent, e.dst, e.inlet)
                        else:
                            edges = [e for e in parent.in_edges.get(container, ()) if e.inlet == rank]
                            for e in edges:
                                reach(parent, e.src, e.outlet)

            if downstream:
                edges = sorted(scope.out_edges.get(box_id, ()), key=lambda e: e.outlet)
            else:
                edges = sorted(scope.in_edges.get(box_id, ()), key=lambda e: e.inlet)
            for e in edges:
                if signal_only:
                    src_id = e.src
                    if not self._transparent(scope, src_id):
                        if not e.signal or not _accepts_signal(scope.boxes.get(e.dst), e.inlet, db):
                            continue
                if downstream:
                    reach(scope, e.dst, e.inlet)
                else:
                    reach(scope, e.src, e.outlet)

            for partner_scope, partner_id in self._bridged(
                scope, box_id, "send" if downstream else "receive", signal_only
            ):
                if mark(partner_scope, partner_id):
                    queue.append((partner_scope, partner_id))

        return result

    @staticmethod
    def _container_id(parent: Scope, container_key):
        """The raw box id in *parent* whose str is *container_key*."""
        if container_key in parent.boxes:
            return container_key
        for box_id in parent.boxes:
            if str(box_id) == container_key:
                return box_id
        return None

    # -- control walk (Q24 / R8) ---------------------------------------------

    def control_walk(self, scope: Scope, box_id, *, downstream: bool, max_depth: int = 64):
        """Yield ``(scope, box_id)`` pairs reachable over control cords (Q24).

        BFS order; the start is never yielded and each pair at most once.
        Downstream follows ``scope.out_edges`` stable-sorted by outlet,
        upstream ``scope.in_edges`` stable-sorted by inlet; a cord whose
        ``Edge.signal`` is True is never followed. A cord into a ``p`` /
        embedded bpatcher (``_crossing_child``) continues at the inner port
        box of that x-rank, and reaching an inner exit port continues along
        the parent container's cords at that rank (signal cords still
        skipped); containers and port boxes are traversed, never yielded.
        Bridges (non-gen, non-rnbo scopes, channel = literal first
        argument): ``send``/``s`` -> ``receive``/``r``; ``value``/``v`` ->
        every other ``value``/``v``; ``pv`` -> every other ``pv`` in the
        same, an ancestor or a descendant scope; a message box -> every
        ``receive``/``r`` and ``value``/``v`` of each ``;`` segment target.
        Upstream mirrors them. Each cord or bridge hop adds 1 to the depth
        (a port crossing rides on its cord); a node at *max_depth* is
        yielded but not expanded. Read-only; malformed input never raises.
        """
        visited = {(id(scope), box_id)}
        crossed: set = set()
        queue: deque = deque([(scope, box_id, 0)])
        while queue:
            cur_scope, cur_id, depth = queue.popleft()
            if depth >= max_depth:
                continue
            for nxt_scope, nxt_id in self._control_neighbours(cur_scope, cur_id, downstream, crossed):
                key = (id(nxt_scope), nxt_id)
                if key in visited:
                    continue
                visited.add(key)
                yield nxt_scope, nxt_id
                queue.append((nxt_scope, nxt_id, depth + 1))

    def _control_neighbours(self, scope: Scope, box_id, downstream: bool, crossed: set) -> list:
        """Real (non-transparent) control neighbours of one node, in order."""
        out: list = []
        if downstream:
            for e in sorted(scope.out_edges.get(box_id, ()), key=lambda e: e.outlet):
                if not e.signal:
                    self._control_land(scope, e.dst, e.inlet, True, crossed, out)
        else:
            for e in sorted(scope.in_edges.get(box_id, ()), key=lambda e: e.inlet):
                if not e.signal:
                    self._control_land(scope, e.src, e.outlet, False, crossed, out)
        out.extend(self._control_bridged(scope, box_id, downstream))
        return out

    def _control_land(self, scope: Scope, box_id, port, downstream: bool,
                      crossed: set, out: list) -> None:
        """Resolve a cord landing on *box_id* at *port* through crossing
        containers and port boxes; append the real boxes reached to *out*."""
        pending: deque = deque([(scope, box_id, port)])
        while pending:
            s, b, p = pending.popleft()
            box = s.boxes.get(b)
            if box is None:
                continue
            inner = self._crossing_child(s, b)
            if inner is not None:
                key = (id(s), b, downstream, p)
                if key in crossed:
                    continue
                crossed.add(key)
                port_id = self._port_ranks(inner)["inlet" if downstream else "outlet"].get(p)
                if port_id is not None and port_id in inner.boxes:
                    pending.append((inner, port_id, None))
                continue
            maxclass = walk.box_maxclass(box)
            if maxclass not in ("inlet", "outlet"):
                out.append((s, b))
                continue
            key = (id(s), b, downstream)
            if key in crossed:
                continue
            crossed.add(key)
            if maxclass == ("inlet" if downstream else "outlet"):
                # Entered from the container: continue inside this scope.
                if downstream:
                    for e in sorted(s.out_edges.get(b, ()), key=lambda e: e.outlet):
                        if not e.signal:
                            pending.append((s, e.dst, e.inlet))
                else:
                    for e in sorted(s.in_edges.get(b, ()), key=lambda e: e.inlet):
                        if not e.signal:
                            pending.append((s, e.src, e.outlet))
                continue
            # Leaving a crossing scope through its port box.
            parent = s.parent
            if parent is None or s.context not in _CROSSING_CONTEXTS:
                continue
            container = self._container_id(parent, s.container)
            rank = self._port_ranks(s)["rank"].get(b)
            if container is None or rank is None:
                continue
            if downstream:
                for e in sorted(parent.out_edges.get(container, ()), key=lambda e: e.outlet):
                    if e.outlet == rank and not e.signal:
                        pending.append((parent, e.dst, e.inlet))
            else:
                for e in sorted(parent.in_edges.get(container, ()), key=lambda e: e.inlet):
                    if e.inlet == rank and not e.signal:
                        pending.append((parent, e.src, e.outlet))

    def _control_bridge_map(self) -> dict:
        """Lazily built, cached bridge index of the control walk."""
        if self._control_bridges is not None:
            return self._control_bridges
        maps: dict = {"send": {}, "receive": {}, "value": {}, "pv": {},
                      "msg_by_target": {}, "msg_targets": {}}
        for scope in self.scopes:
            if scope.scope in ("gen", "rnbo"):
                continue
            for box_id, box in scope.boxes.items():
                if walk.box_maxclass(box) == "message":
                    targets = _message_remote_targets(box)
                    if targets:
                        maps["msg_targets"][(id(scope), box_id)] = targets
                        for target in targets:
                            maps["msg_by_target"].setdefault(target, []).append((scope, box_id))
                    continue
                kind = _CONTROL_BRIDGE_KINDS.get(walk.box_name(box))
                if kind is None:
                    continue
                args = walk.box_args(box)
                if not args:
                    continue
                maps[kind].setdefault(args[0], []).append((scope, box_id))
        self._control_bridges = maps
        return maps

    @staticmethod
    def _scopes_related(a: Scope, b: Scope) -> bool:
        """True when *a* and *b* are the same scope or one contains the other."""
        for x, y in ((a, b), (b, a)):
            node = x
            while node is not None:
                if node is y:
                    return True
                node = node.parent
        return False

    def _control_bridged(self, scope: Scope, box_id, downstream: bool) -> list:
        """Bridge partners of one node (see :meth:`control_walk`)."""
        if scope.scope in ("gen", "rnbo"):
            return []
        box = scope.boxes.get(box_id)
        if box is None:
            return []
        maps = self._control_bridge_map()
        out: list = []
        if walk.box_maxclass(box) == "message":
            if downstream:
                for target in maps["msg_targets"].get((id(scope), box_id), ()):
                    out.extend(maps["receive"].get(target, ()))
                    out.extend(maps["value"].get(target, ()))
            return out
        kind = _CONTROL_BRIDGE_KINDS.get(walk.box_name(box))
        if kind is None:
            return out
        args = walk.box_args(box)
        if not args:
            return out
        channel = args[0]
        if kind == "send":
            if downstream:
                out.extend(maps["receive"].get(channel, ()))
        elif kind == "receive":
            if not downstream:
                out.extend(maps["send"].get(channel, ()))
                out.extend(maps["msg_by_target"].get(channel, ()))
        elif kind == "value":
            out.extend(
                (s, b) for s, b in maps["value"].get(channel, ())
                if not (s is scope and b == box_id)
            )
            if not downstream:
                out.extend(maps["msg_by_target"].get(channel, ()))
        elif kind == "pv":
            out.extend(
                (s, b) for s, b in maps["pv"].get(channel, ())
                if not (s is scope and b == box_id) and self._scopes_related(s, scope)
            )
        return out


# Contexts whose containers are crossed port-exactly (G9).
_CROSSING_CONTEXTS = frozenset({"max", "bpatcher"})

# Bridged object names -> (role, kind)
_BRIDGE_NAMES = {
    "send": ("send", "control"), "s": ("send", "control"),
    "send~": ("send", "signal"), "s~": ("send", "signal"),
    "receive": ("receive", "control"), "r": ("receive", "control"),
    "receive~": ("receive", "signal"), "r~": ("receive", "signal"),
}


# Control-walk bridge names (Q24): object name -> bridge kind.
_CONTROL_BRIDGE_KINDS = {
    "send": "send", "s": "send",
    "receive": "receive", "r": "receive",
    "value": "value", "v": "value",
    "pv": "pv",
}

# A ``;`` not escaped with a backslash starts a remote-message segment.
_REMOTE_SPLIT_RE = re.compile(r"(?<!\\);")


def _message_remote_targets(box) -> list:
    """Receive names targeted by a message box's ``;`` segments (Q24).

    Only a ``message`` box with str text. The text is split on ``;`` not
    preceded by a backslash; for every segment after the first, the first
    whitespace token after stripping spaces, ``\\r`` and ``\\n`` is a target
    (``;\\rwhrt pitch 7`` targets ``whrt``). Unique, in order; never raises.
    """
    if walk.box_maxclass(box) != "message":
        return []
    text = walk.box_text(box)
    if ";" not in text:
        return []
    out: list = []
    for segment in _REMOTE_SPLIT_RE.split(text)[1:]:
        tokens = segment.strip(" \r\n").split()
        if tokens and tokens[0] not in out:
            out.append(tokens[0])
    return out


def _accepts_signal(box, inlet: int, db) -> bool:
    """True when *box* accepts a signal cord at *inlet*.

    A container (``validation._is_container_box``) always does; otherwise
    ``validation._inlet_accepts_signal``. Permissive when *db* is None or
    the box is missing.
    """
    if db is None or not isinstance(box, dict):
        return True
    from src.maxpat import validation

    if validation._is_container_box(box):
        return True
    return validation._inlet_accepts_signal(box, inlet, db)


def resolve_patcher(patcher, path: tuple):
    """The Patcher at walk *path* below *patcher*, following ``_inner_patcher``
    by box id; None when a step has no embedded Patcher (e.g. mc.gen~
    ``data.patcher``)."""
    current = patcher
    for box_id, _label in path:
        nxt = None
        for box in getattr(current, "boxes", ()):
            if str(getattr(box, "id", "")) == box_id and getattr(box, "_inner_patcher", None) is not None:
                nxt = box._inner_patcher
                break
        if nxt is None:
            return None
        current = nxt
    return current


class GraphMixin:
    """Graph traversal methods mixed into Patcher.

    Expects ``self.boxes``, ``self.lines``, and ``self.db`` to be provided
    by the host class (Patcher). ``downstream`` / ``upstream`` /
    ``signal_path`` build one :class:`PatchGraph` from ``self.to_dict()``
    per call and run its port-exact, send/receive-bridged,
    outlettype-signal traversal (G9, Q20); results are mapped back to Box
    objects through :func:`resolve_patcher`.
    """

    def _build_adj(
        self, signal_only: bool = False
    ) -> tuple[dict[str, list[tuple[str, int]]], dict[str, list[tuple[str, int]]], "dict[str, Box]"]:
        """Build forward and reverse adjacency dicts from self.lines.

        Args:
            signal_only: If True, keep only cords whose source outlet carries
                audio (``outlettype`` signal / multichannelsignal, via
                :func:`outlet_is_signal`) and whose destination accepts
                signal at that inlet (a container, or the DB says so; G9).

        Returns:
            (forward, reverse, box_map) where:
            - forward[source_id] = sorted list of (dest_id, source_outlet) tuples
            - reverse[dest_id] = sorted list of (source_id, dest_inlet) tuples
            - box_map maps id -> Box for fast lookups
        """
        box_map: dict[str, Box] = {b.id: b for b in self.boxes}
        forward: dict[str, list[tuple[str, int]]] = {}
        reverse: dict[str, list[tuple[str, int]]] = {}
        dicts: dict = {}
        if signal_only:
            dicts = PatchGraph.build(self.to_dict()).top.boxes

        for line in self.lines:
            src_id = line.source_id
            dst_id = line.dest_id
            if src_id not in box_map or dst_id not in box_map:
                continue
            if signal_only:
                if not outlet_is_signal(dicts.get(src_id), line.source_outlet):
                    continue
                if not _accepts_signal(dicts.get(dst_id), line.dest_inlet, self.db):
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

        Results are in BFS discovery order, each node's neighbours ordered by
        outlet index (left to right). The starting box is NOT included.

        Traversal crosses subpatcher boundaries port-exactly: a cord into a
        ``p`` / embedded bpatcher at inlet *i* enters only the inner inlet of
        x-rank *i*, and an inner outlet of rank *k* continues only from the
        container's outlet *k*. gen~ / rnbo~ / poly~ containers are opaque.
        send/receive and send~/receive~ pairs are bridged by channel name.

        Args:
            box: Starting box.
            signal_only: If True, follow only cords whose source outlet
                carries audio (``outlettype``) into an inlet that accepts
                signal; port boxes and crossing containers are transparent.

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

        Results are in BFS discovery order, each node's neighbours ordered by
        inlet index (left to right). The starting box is NOT included.

        Mirrors :meth:`downstream`: a cord from a ``p`` outlet *k* enters only
        the inner outlet of x-rank *k*; an inner inlet of rank *i* continues
        only from the container's inlet *i*. Receivers bridge to senders.

        Args:
            box: Starting box.
            signal_only: Same rule as :meth:`downstream`.

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
        """One PatchGraph per call; ``(scope, id)`` pairs mapped back to Boxes.

        Pairs in scopes without a Patcher (mc.gen~ ``data.patcher``) are
        dropped.
        """
        graph = PatchGraph.build(self.to_dict())
        top = graph.top
        db = self.db if signal_only else None
        if direction == "downstream":
            pairs = graph.downstream(top, start.id, signal_only=signal_only, db=db)
        else:
            pairs = graph.upstream(top, start.id, signal_only=signal_only, db=db)

        maps: dict = {}
        result: list[Box] = []
        for scope, box_id in pairs:
            key = id(scope)
            if key not in maps:
                patcher = resolve_patcher(self, scope.path)
                maps[key] = {} if patcher is None else {b.id: b for b in patcher.boxes}
            found = maps[key].get(box_id)
            if found is not None:
                result.append(found)
        return result

    def signal_path(self, box: "Box") -> "list[Box]":
        """Return the full signal chain passing through *box*.

        Combines upstream signal sources (reversed) + box + downstream signal
        sinks, using the ``signal_only`` traversal (outlettype + destination
        acceptance, crossing ``p`` boxes port-exactly). *box* itself is
        included when its ``outlettype`` has a signal / multichannelsignal
        entry, or, with no ``outlettype`` list, when its name ends in ``~``.

        Args:
            box: The box to trace the signal path through.

        Returns:
            Ordered list of boxes from source to sink.

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
        outlettype = getattr(box, "outlettype", None)
        if isinstance(outlettype, list):
            is_signal = any(t in SIGNAL_OUTLET_TYPES for t in outlettype if isinstance(t, str))
        else:
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
