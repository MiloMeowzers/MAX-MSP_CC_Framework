"""ccsim -- tiny message-graph simulator for a ChopChop .amxd.

Interprets the real wiring for the control-domain objects that decide what
reaches karma~: trigger, sel/select, route/routepass, gate, toggle/live.toggle,
button/live.button, int/float/i/f, message boxes ($1 + comma sequencing),
change, onebang, deferlow/defer, delay/pipe (timing dropped), pass-through UI
number boxes, and named send/receive + subpatcher inlet/outlet crossings.

Signal objects are NOT simulated. When a path reaches one (`*~`, `sig~`,
`phasor~`, `edge~`, `snapshot~`, `gen~`, ...) it is reported as a signal
boundary and propagation stops there. Inject the downstream edge by hand.

Every object class actually encountered that has no handler is listed under
UNMODELED -- if a result looks empty, check that list first (the simulator has
historically failed silently on an unhandled class).

CAVEAT: an unmodeled object emits its input on OUTLET 0. If the live path
leaves such an object on a different outlet, ccsim will miss it. `cctrace.py`
(pure reachability, no value logic) is the ground truth for "does X connect to
karma~"; ccsim only adds value-domain reasoning (which gate is open, does this
`sel` match) on top of a path cctrace already confirmed.

Usage:
  python ccsim.py FILE --inject "/Playback/RollingB:go@0=bang" [--target karma~]
  python ccsim.py FILE --inject "/:obj-18@0=1"            # record_trigger on
  python ccsim.py FILE --inject "/:w_fsize@0=8000" --target "s ---karmaMsg"

Inject spec: SCOPE:idOrVarname @ INLET = VALUE   (VALUE: bang | int | float | a b c)
"""
from __future__ import annotations

import sys

from ccamxd import load, iter_scopes

SEND = {"s", "send", "s~", "send~"}
RECV = {"r", "receive", "r~", "receive~"}
SIGNAL_HINT = ("~",)   # class endswith
STOP_CLASSES = {"gen~", "phasor~", "edge~", "delta~", "snapshot~", "sig~",
                "cycle~", "line~", "click~", "train~", "count~", "sah~"}

BANG = "bang"


def toks(text):
    return (text or "").strip().split()


def as_val(s):
    try:
        return int(s)
    except ValueError:
        try:
            return float(s)
        except ValueError:
            return s


class Sim:
    def __init__(self, amx, target="karma~", max_steps=20000):
        self.scopes = list(iter_scopes(amx.patcher))
        self.by_path = {sc.path: sc for sc in self.scopes}
        self.target = target
        self.max_steps = max_steps
        self.reached = []          # (scope, id, inlet, value)
        self.unmodeled = set()
        self.signal_stops = set()
        self.state = {}            # (scope,id) -> per-box state dict
        self._index_io()
        self._index_sr()

    # -- indexing ----------------------------------------------------------
    def _index_io(self):
        self.child_of = {}   # (scope,id) -> child Scope
        self.inl = {}        # child.path -> [ids ordered]
        self.outl = {}
        for sc in self.scopes:
            for bid, b in sc.iter_boxes():
                if b.get("patcher") is None:
                    continue
                cp = sc.path + (b.get("text") or "?").replace("p ", "").strip()[:28] + "/"
                child = self.by_path.get(cp)
                if not child:
                    continue
                self.child_of[(sc.path, bid)] = child
                io = {"inlet": [], "outlet": []}
                for _, cb in child.iter_boxes():
                    if cb.get("maxclass") in io:
                        io[cb["maxclass"]].append(cb)
                self.inl[cp] = [x["id"] for x in sorted(io["inlet"], key=lambda z: (z.get("patching_rect") or [0])[0])]
                self.outl[cp] = [x["id"] for x in sorted(io["outlet"], key=lambda z: (z.get("patching_rect") or [0])[0])]

    def _index_sr(self):
        self.recv_of = {}    # channel -> [(scope,id)]
        for sc in self.scopes:
            for bid, b in sc.iter_boxes():
                t = toks(b.get("text"))
                if len(t) >= 2 and t[0] in RECV:
                    self.recv_of.setdefault(t[1], []).append((sc.path, bid))

    def scope(self, path):
        return self.by_path[path]

    # -- propagation -----------------------------------------------------------
    def run(self, inject, verbose=False):
        self.q = [inject]                       # (scope, id, inlet, value)
        steps = 0
        loopguard = {}
        while self.q and steps < self.max_steps:
            steps += 1
            scope, bid, inlet, val = self.q.pop(0)
            sc = self.scope(scope)
            b = sc.boxes.get(bid)
            if b is None:
                if verbose:
                    print(f"  [{steps}] MISSING {scope}:{bid}")
                continue
            cls = b.get("maxclass") or ""
            if verbose:
                print(f"  [{steps}] {scope}{bid} in{inlet} <= {val!r}  "
                      f"({b.get('text') or cls})")
            text = b.get("text") or ""
            word = toks(text)[0] if toks(text) else cls

            key = (scope, bid, inlet, repr(val))
            loopguard[key] = loopguard.get(key, 0) + 1
            if loopguard[key] > 6:
                continue

            if word == self.target or text == self.target or cls == self.target \
               or (self.target.startswith("s ") and word in SEND and toks(text)[1:2] == self.target.split()[1:2]):
                self.reached.append((scope, bid, inlet, val))
                # keep propagating for sends; stop at object targets
                if not (self.target.startswith("s ") or self.target in SEND):
                    continue

            # named send: a send emits nothing on an outlet, so its cross-scope
            # hop must be dispatched here rather than from fanout()
            if word in SEND and len(toks(text)) >= 2:
                for (rp, rid) in self.recv_of.get(toks(text)[1], []):
                    self.q.append((rp, rid, 0, val))

            emits = self.handle(scope, bid, b, cls, word, text, inlet, val)
            for outlet, ov in emits:
                self.fanout(scope, bid, outlet, ov)
        self.steps = steps

    def fanout(self, scope, bid, outlet, val):
        sc = self.scope(scope)
        # subpatcher: emitting from a subpatcher box outlet is handled via child outlet objects;
        # here handle emitting INTO a child (box has patcher) is done in handle(); this is normal lines
        for s, so, d, di in sc.lines():
            if s == bid and so == outlet:
                dbox = sc.boxes.get(d)
                if dbox is not None and dbox.get("patcher") is not None:
                    # into subpatcher inlet di
                    child = self.child_of.get((scope, d))
                    if child and di < len(self.inl[child.path]):
                        self.q.append((child.path, self.inl[child.path][di], 0, val))
                    continue
                self.q.append((scope, d, di, val))
        # named send
        t = toks(sc.boxes[bid].get("text"))
        if len(t) >= 2 and t[0] in SEND:
            for (rp, rid) in self.recv_of.get(t[1], []):
                self.q.append((rp, rid, 0, val))
        # child outlet object -> parent box outlet
        if sc.boxes[bid].get("maxclass") == "outlet":
            # find parent
            for (psp, pbid), child in self.child_of.items():
                if child.path == scope:
                    order = self.outl[scope]
                    if bid in order:
                        n = order.index(bid)
                        self.q.append((psp, pbid, "_from_child_outlet", (n, val)))

    # -- object handlers -----------------------------------------------------
    def st(self, scope, bid):
        return self.state.setdefault((scope, bid), {})

    def handle(self, scope, bid, b, cls, word, text, inlet, val):
        t = toks(text)

        # special: a value arriving 'from child outlet' -> re-emit on that outlet
        if inlet == "_from_child_outlet":
            n, v = val
            return [(n, v)]

        # subpatcher box receiving on an inlet -> push to child inlet
        if b.get("patcher") is not None:
            child = self.child_of.get((scope, bid))
            if child and inlet < len(self.inl[child.path]):
                self.q.append((child.path, self.inl[child.path][inlet], 0, val))
            return []

        if cls in ("inlet", "outlet"):
            return [(0, val)]

        if word in ("t", "trigger"):
            args = t[1:] or ["b", "b"]
            out = []
            for i, a in enumerate(args):
                if a == "b":
                    out.append((i, BANG))
                elif a in ("i", "f", "l", "s", "a"):
                    out.append((i, val if val != BANG else 0))
                else:
                    out.append((i, as_val(a)))
            return list(reversed(out))       # right-to-left

        if word in ("sel", "select"):
            args = [as_val(x) for x in t[1:]]
            if inlet == 0:
                for i, a in enumerate(args):
                    if val == a:
                        return [(i, BANG)]
                return [(len(args), val)]
            return []

        if word in ("route", "routepass"):
            args = [as_val(x) for x in t[1:]]
            msg = val if isinstance(val, list) else [val]
            head = msg[0]
            for i, a in enumerate(args):
                if head == a:
                    rest = msg if word == "routepass" else (msg[1:] or [BANG])
                    return [(i, rest[0] if len(rest) == 1 else rest)]
            return [(len(args), val)]

        if word == "gate" or word == "gate~":
            n = int(t[1]) if len(t) > 1 and t[1].isdigit() else 1
            s = self.st(scope, bid)
            if inlet == 0:
                s["ctrl"] = int(val) if isinstance(val, (int, float)) else s.get("ctrl", 0)
                return []
            c = s.get("ctrl", 0)
            if 1 <= c <= n:
                return [(c - 1, val)]
            return []

        if cls in ("toggle", "live.toggle"):
            if isinstance(val, str) and val.startswith("set"):
                return []
            if val == BANG:
                return [(0, self.st(scope, bid).get("v", 0))]
            v = 1 if (isinstance(val, (int, float)) and val != 0) else 0
            self.st(scope, bid)["v"] = v
            return [(0, v)]

        if cls in ("button", "live.button"):
            return [(0, BANG)]

        if word in ("i", "int", "f", "float") or cls in ("number", "flonum", "live.numbox", "number~"):
            s = self.st(scope, bid)
            if inlet == 1:
                s["v"] = val
                return []
            if val == BANG:
                return [(0, s.get("v", 0))]
            s["v"] = val
            return [(0, val)]

        if word == "split":
            lo, hi = (as_val(t[1]), as_val(t[2])) if len(t) > 2 else (0, 1)
            x = val if isinstance(val, (int, float)) else 0
            return [(0, x)] if lo <= x <= hi else [(1, x)]

        if word in (">", "<", ">=", "<=", "==", "!=", "<~", ">~"):
            rhs = as_val(t[1]) if len(t) > 1 else 0
            x = val if isinstance(val, (int, float)) else 0
            w = word.rstrip("~")
            r = {">": x > rhs, "<": x < rhs, ">=": x >= rhs, "<=": x <= rhs,
                 "==": x == rhs, "!=": x != rhs}[w]
            return [(0, 1 if r else 0)]

        if word in ("clip", "clip~"):
            lo, hi = (as_val(t[1]), as_val(t[2])) if len(t) > 2 else (0, 1)
            x = val if isinstance(val, (int, float)) else 0
            return [(0, max(lo, min(hi, x)))]

        if word in ("minimum", "maximum"):
            rhs = as_val(t[1]) if len(t) > 1 else 0
            x = val if isinstance(val, (int, float)) else 0
            return [(0, min(x, rhs) if word == "minimum" else max(x, rhs))]

        if word == "change":
            s = self.st(scope, bid)
            if val != s.get("v"):
                s["v"] = val
                return [(0, val)]
            return []

        if word == "onebang":
            s = self.st(scope, bid)
            if inlet == 1:
                s["armed"] = True
                return []
            if s.get("armed"):
                s["armed"] = False
                return [(0, BANG)]
            return []

        if word in ("deferlow", "defer", "pipe", "delay", "del"):
            if isinstance(val, str) and val == "stop":
                return []
            return [(0, BANG if val == BANG or word in ("delay", "del") else val)]

        if cls == "message" or cls == "messbox":
            if inlet != 0:
                return []
            segs = [s.strip() for s in text.split(",")]
            out = []
            for seg in segs:
                parts = seg.split()
                sub = []
                for p in parts:
                    if p in ("$1", "$i1", "$f1"):
                        sub.append(val if val != BANG else 0)
                    else:
                        sub.append(as_val(p))
                if not sub:
                    sub = [val]
                out.append((0, sub[0] if len(sub) == 1 else sub))
            return out

        if word in ("s", "send", "s~", "send~"):
            return []            # cross-scope hop handled in fanout()

        if word in ("r", "receive", "r~", "receive~"):
            return [(0, val)]    # re-emit whatever the paired send delivered

        if word in ("+", "-", "*", "/") and len(t) > 1:
            try:
                rhs = as_val(t[1])
                if inlet == 1:
                    self.st(scope, bid)["rhs"] = rhs
                    return []
                rhs = self.st(scope, bid).get("rhs", rhs)
                x = val if isinstance(val, (int, float)) else 0
                r = {"+": x + rhs, "-": x - rhs, "*": x * rhs,
                     "/": (x / rhs if rhs else 0)}[word]
                return [(0, r)]
            except Exception:
                return [(0, val)]

        if word in ("prepend", "append"):
            extra = [as_val(x) for x in t[1:]]
            msg = val if isinstance(val, list) else [val]
            return [(0, (extra + msg) if word == "prepend" else (msg + extra))]

        # signal boundary
        if cls in STOP_CLASSES or word in STOP_CLASSES or (cls.endswith("~") and cls not in ("gate~",)):
            self.signal_stops.add((scope, bid, cls or word))
            return []

        # passthrough fallback
        self.unmodeled.add(word if cls == "newobj" else (cls or word))
        return [(0, val)]


def parse_inject(g, spec):
    left, _, rhs = spec.partition("=")
    ref, _, inl = left.partition("@")
    inl = int(inl) if inl else 0
    rv = rhs.strip().split()
    if rv == ["bang"] or rv == []:
        v = BANG
    elif len(rv) == 1:
        v = as_val(rv[0])
    else:
        v = [as_val(x) for x in rv]
    scope_q, _, box_q = ref.rpartition(":")
    for sc in g:
        seg = sc.path.rstrip("/").rsplit("/", 1)[-1]
        if scope_q and scope_q not in (sc.path, seg, sc.path.rstrip("/")):
            continue
        for bid, b in sc.iter_boxes():
            if box_q == bid or box_q == b.get("varname"):
                return (sc.path, bid, inl, v)
    raise SystemExit(f"inject ref not found: {ref}")


def _cli(argv):
    if not argv or "--inject" not in argv:
        print(__doc__)
        return 2
    amx = load(argv[0])
    target = argv[argv.index("--target") + 1] if "--target" in argv else "karma~"
    sim = Sim(amx, target)
    inj = parse_inject(list(iter_scopes(amx.patcher)), argv[argv.index("--inject") + 1])
    print(f"inject {inj}   target='{target}'")
    sim.run(inj, verbose="--verbose" in argv)
    print(f"steps: {sim.steps}")
    if sim.reached:
        print(f"REACHED {target} ({len(sim.reached)}):")
        seen = set()
        for scope, bid, inlet, val in sim.reached:
            k = (scope, bid, inlet, repr(val))
            if k in seen:
                continue
            seen.add(k)
            b = sim.scope(scope).boxes[bid]
            print(f"  {scope}{bid}  inlet {inlet}  <= {val!r}   ({b.get('text') or b.get('maxclass')})")
    else:
        print(f"NOTHING reached {target}")
    if sim.signal_stops:
        print("signal boundaries hit (propagation stopped):")
        for scope, bid, c in sorted(sim.signal_stops):
            print(f"  {scope}{bid}  {c}")
    if sim.unmodeled:
        print("UNMODELED classes (treated as passthrough):", ", ".join(sorted(sim.unmodeled)))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli(sys.argv[1:]))
