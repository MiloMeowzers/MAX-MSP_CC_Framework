"""cctrace -- follow a signal/message path across a ChopChop .amxd.

Builds one directed graph over the whole device, with edges for:
  * patchlines (within a scope)
  * named send -> receive  (`s`/`send` -> `r`/`receive`, and `s~`/`r~`), cross-scope
  * subpatcher boundaries: parent inlet N  <->  Nth `inlet` box inside (ordered by
    patching_rect x, per the Max convention), likewise outlets.

Usage:
  python cctrace.py FILE --channel ---recordOn
        list every sender and receiver of a named channel, with 1-hop context

  python cctrace.py FILE --box "/:record_arm_toggle" --down [--depth 6]
  python cctrace.py FILE --box "/Playback/RollingB:go" --up
        walk downstream / upstream from a box (id or varname), crossing sends
        and subpatcher walls

Box refs are "SCOPEPATH:idOrVarname"; SCOPEPATH matches the tail segment
(e.g. "RollingB") or the full "/Playback/RollingB/" path.
"""
from __future__ import annotations

import sys

from ccamxd import load, iter_scopes


SEND = {"s", "send", "s~", "send~"}
RECV = {"r", "receive", "r~", "receive~"}


def _first_word(text):
    return (text or "").strip().split()[0] if (text or "").strip() else ""


def _chan(text):
    parts = (text or "").split()
    return parts[1] if len(parts) > 1 and parts[0] in (SEND | RECV) else None


class Graph:
    def __init__(self, amx):
        self.scopes = list(iter_scopes(amx.patcher))
        self.by_path = {sc.path: sc for sc in self.scopes}
        # node = (scope_path, box_id).  adjacency stores (node, label)
        self.fwd: dict = {}
        self.bwd: dict = {}
        self.sc_of = {}
        for sc in self.scopes:
            for bid in sc.boxes:
                self.sc_of[(sc.path, bid)] = sc
        self._build()

    def _edge(self, a, b, label):
        self.fwd.setdefault(a, []).append((b, label))
        self.bwd.setdefault(b, []).append((a, label))

    def _ordered_io(self, sc, kind):
        boxes = [b for _, b in sc.iter_boxes() if b.get("maxclass") == kind]
        boxes.sort(key=lambda b: (b.get("patching_rect") or [0])[0])
        return boxes

    def _build(self):
        # patchlines
        for sc in self.scopes:
            for s, so, d, di in sc.lines():
                self._edge((sc.path, s), (sc.path, d), f"[{so}>{di}]")

        # named send/receive
        senders = {}
        receivers = {}
        for sc in self.scopes:
            for bid, b in sc.iter_boxes():
                c = _chan(b.get("text"))
                if not c:
                    continue
                w = _first_word(b.get("text"))
                if w in SEND:
                    senders.setdefault(c, []).append((sc.path, bid))
                elif w in RECV:
                    receivers.setdefault(c, []).append((sc.path, bid))
        self.senders, self.receivers = senders, receivers
        for c, ss in senders.items():
            for s in ss:
                for r in receivers.get(c, []):
                    self._edge(s, r, f"~{c}~")

        # subpatcher boundaries
        for sc in self.scopes:
            for bid, b in sc.iter_boxes():
                sub = b.get("patcher")
                if sub is None:
                    continue
                child = self.by_path.get(
                    sc.path + (b.get("text") or "?").replace("p ", "").strip()[:28] + "/"
                )
                if not child:
                    continue
                ins = self._ordered_io(child, "inlet")
                outs = self._ordered_io(child, "outlet")
                for n, ib in enumerate(ins):
                    self._edge((sc.path, bid), (child.path, ib["id"]), f"in{n}")
                for n, ob in enumerate(outs):
                    self._edge((child.path, ob["id"]), (sc.path, bid), f"out{n}")

    # -- lookups --------------------------------------------------------------
    def resolve(self, ref):
        scope_q, _, box_q = ref.rpartition(":")
        hits = []
        for sc in self.scopes:
            seg = sc.path.rstrip("/").rsplit("/", 1)[-1]
            if scope_q and scope_q not in (sc.path, seg, sc.path.rstrip("/")):
                continue
            for bid, b in sc.iter_boxes():
                if box_q == bid or box_q == b.get("varname"):
                    hits.append((sc.path, bid))
        return hits

    def label(self, node):
        sc = self.sc_of.get(node)
        if not sc:
            return f"{node}"
        b = sc.boxes.get(node[1], {})
        return f"{node[0]}{node[1]}  {b.get('text') or b.get('maxclass')}"

    def walk(self, start, direction="down", depth=6):
        adj = self.fwd if direction == "down" else self.bwd
        seen = {start}
        frontier = [(start, 0, "")]
        out = []
        while frontier:
            node, d, via = frontier.pop(0)
            out.append((d, via, node))
            if d >= depth:
                continue
            for nxt, lab in adj.get(node, []):
                if nxt not in seen:
                    seen.add(nxt)
                    frontier.append((nxt, d + 1, lab))
        return out


def _cli(argv):
    if not argv:
        print(__doc__)
        return 2
    g = Graph(load(argv[0]))
    rest = argv[1:]

    if "--channel" in rest:
        c = rest[rest.index("--channel") + 1]
        print(f"channel {c}")
        print(" senders:")
        for sp, bid in g.senders.get(c, []):
            print(f"   {g.label((sp, bid))}")
            for nxt, lab in g.bwd.get((sp, bid), []):
                if not lab.startswith("~"):
                    print(f"       <- {lab} {g.label(nxt)}")
        print(" receivers:")
        for sp, bid in g.receivers.get(c, []):
            print(f"   {g.label((sp, bid))}")
            for nxt, lab in g.fwd.get((sp, bid), []):
                if not lab.startswith("~"):
                    print(f"       -> {lab} {g.label(nxt)}")
        if not g.senders.get(c):
            print("   (no senders -- orphaned receiver)")
        if not g.receivers.get(c):
            print("   (no receivers -- orphaned sender)")
        return 0

    if "--box" in rest:
        ref = rest[rest.index("--box") + 1]
        hits = g.resolve(ref)
        if not hits:
            print("no box matches", ref)
            return 1
        direction = "up" if "--up" in rest else "down"
        depth = int(rest[rest.index("--depth") + 1]) if "--depth" in rest else 6
        for h in hits:
            print(f"=== {direction}stream from {g.label(h)}")
            for d, via, node in g.walk(h, direction, depth):
                arrow = "  " * d + (via + " " if via else "")
                print(f"  {arrow}{g.label(node)}")
        return 0

    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(_cli(sys.argv[1:]))
