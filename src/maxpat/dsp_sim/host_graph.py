"""Host-patch port inference for the codebox smoke test (261022-ud6 CR-01).

The smoke test used to judge every codebox output as audio driven by +-0.1
noise, so outlets that carry Hz, ms, sample indices or state flags (and
inlets that carry triggers) failed correct, MAX-confirmed code. This module
reads the patch that hosts a gen~ / mc.gen~ box and classifies each port.

Outlets (traced downstream through patch cords):

* ``audio``: some path reaches an audio sink -- dac~, ezdac~, plugout~, out~,
  gain~ / live.gain~, meter~ / levelmeter~ / live.meter~, sfrecord~,
  adoutput~ -- through signal consumers. A signal object passes the signal on
  from its left inlet (a ``*~`` gain stage, a filter's input, the left inlet
  of the next gen~); ``+~`` / ``-~`` / ``mc.pack~`` / ``mc.combine~`` /
  ``matrix~`` pass every inlet and ``selector~`` / ``gate~`` their right
  inlets. ``send~ X`` continues at every ``receive~ X`` in the same file;
  ``p`` / bpatcher / poly~ / abstraction boxes are entered and left through
  their inlet / outlet (in~ / out~) objects.
* ``control``: no path reaches an audio sink. Parameter inlets of signal
  objects (``*~`` right inlet, a filter's cutoff, a gen~ inlet other than
  the first), generators' rate inlets (cycle~, phasor~, play~, tapout~ ...),
  displays (snapshot~, number~, scope~) and control objects end a path, and
  an unconnected outlet is control.
* Unknown hosts are ``audio`` (the conservative full-check default): a
  ``send~`` with no ``receive~`` in the file, an abstraction outlet with no
  instance in a sibling .maxpat, or a search that runs out of budget.

Inlets (traced upstream from the gen~ inlet):

* ``trigger``: click~, train~, or a signal comparison (``>~`` ... ``!=~``).
* ``control``: sig~, line~, curve~, adsr~, number~ (control values turned
  into signals), or another gen~ outlet that is itself control.
* ``audio``: any other signal source (adc~, plugin~, oscillators, filters, an
  audio gen~ outlet), or an unresolvable host.
* ``zero``: no signal reaches the inlet (unconnected, or messages only):
  MAX feeds a gen~ signal inlet 0 then.
Math objects (``+~``, ``*~``, ``mtof~``, ``slide~`` ...) take the strongest
kind of their inputs (audio > trigger > control).

Only the host file's own directory is searched for abstractions and hosts
(the Max search path is not available offline), and every search is bounded
(``_BUDGET`` visited ports, ``_MAX_FILES`` files).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

__all__ = [
    "AUDIO",
    "CONTROL",
    "TRIGGER",
    "ZERO",
    "PortKinds",
    "HostGraph",
    "external_gendsp_name",
    "gen_port_map",
    "obj_name",
]

AUDIO = "audio"
CONTROL = "control"
TRIGGER = "trigger"
ZERO = "zero"

_RANK = {AUDIO: 3, TRIGGER: 2, CONTROL: 1}

_GEN_OBJECTS = ("gen~", "mc.gen~")
_SIGNAL_TYPES = ("signal", "multichannelsignal")

# Downstream: reaching one of these means the outlet is audio.
_AUDIO_SINKS = frozenset({
    "dac~", "ezdac~", "plugout~", "out~", "gain~", "live.gain~", "meter~",
    "levelmeter~", "live.meter~", "sfrecord~", "adoutput~",
})
# Downstream stops (control): displays and measurement objects.
_DISPLAY_STOPS = frozenset({
    "snapshot~", "number~", "scope~", "live.scope~", "spectroscope~",
    "peakamp~", "avg~", "edge~", "thresh~", "zerox~", "change~",
})
# Signal objects whose left inlet is a rate / position / time, not audio.
_PARAM_INLET0 = frozenset({
    "cycle~", "phasor~", "saw~", "rect~", "tri~", "train~", "rand~", "techno~",
    "line~", "curve~", "sig~", "click~", "play~", "groove~", "index~", "wave~",
    "peek~", "poke~", "count~", "tapout~", "adsr~",
})
# Signal objects that pass audio on every inlet.
_ALL_INLETS_AUDIO = frozenset({"+~", "-~", "!-~", "pack~", "combine~", "matrix~"})
# Signal objects whose inlet 0 is a control and inlets >= 1 carry audio.
_RIGHT_INLETS_AUDIO = frozenset({"selector~", "gate~"})

# Upstream classification.
_TRIGGER_SOURCES = frozenset({"click~", "train~", ">~", "<~", ">=~", "<=~", "==~", "!=~"})
_CONTROL_SOURCES = frozenset({"sig~", "line~", "curve~", "adsr~", "number~"})
_MATH_PASS = frozenset({
    "+~", "-~", "*~", "/~", "!-~", "!/~", "clip~", "scale~", "mtof~", "ftom~",
    "abs~", "pow~", "minimum~", "maximum~", "round~", "trunc~", "dbtoa~",
    "atodb~", "slide~", "rampsmooth~", "pack~", "combine~", "selector~",
    "gate~", "pass~", "dup~",
})

_BUDGET = 20000
_MAX_FILES = 64
MAX_SCOPE_DEPTH = 32        # embedded patchers nested deeper are not indexed


def external_gendsp_name(tokens: list):
    """The .gendsp name of an external gen~ box: the value after @gen, else
    the first token after the object name that does not start with '@'."""
    if "@gen" in tokens:
        i = tokens.index("@gen")
        return tokens[i + 1] if i + 1 < len(tokens) else None
    for tok in tokens[1:]:
        if tok.startswith("@"):
            return None
        return tok
    return None


@dataclass
class PortKinds:
    """Port kinds for one codebox, keyed by the codebox's 1-based inN / outN.

    ``notes`` maps "in1" / "out2" to a short evidence string (the sink or
    source that decided the kind). ``host`` names where the kinds came from.
    """

    inputs: dict = field(default_factory=dict)
    outputs: dict = field(default_factory=dict)
    notes: dict = field(default_factory=dict)
    host: str = ""


def _base(name: str) -> str:
    return name[3:] if name.startswith("mc.") else name


def obj_name(box: dict) -> str:
    """The object name of a box: the first text token of a newobj, else the
    maxclass (gain~, ezdac~, inlet, outlet, bpatcher, ...)."""
    if box.get("maxclass") == "newobj":
        toks = str(box.get("text", "") or "").split()
        return toks[0] if toks else ""
    return str(box.get("maxclass", "") or "")


def _tokens(box: dict) -> list:
    return str(box.get("text", "") or "").split()


def _xkey(box: dict):
    rect = box.get("patching_rect") or [0, 0]
    try:
        return (float(rect[0]), float(rect[1]))
    except (TypeError, ValueError, IndexError):
        return (0.0, 0.0)


def _port_number(box: dict):
    """N of ``in N`` / ``in~ N`` / ``out N`` / ``out~ N`` (poly~ ports)."""
    toks = _tokens(box)
    if len(toks) >= 2:
        try:
            return int(float(toks[1]))
        except ValueError:
            return None
    return None


class _Scope:
    """One patcher level of a file: boxes, cords and its inlet/outlet order."""

    def __init__(self, fidx, patcher: dict, parent, depth: int = 0):
        self.fidx = fidx
        self.parent = parent          # (scope, box id) or None at file top level
        self.depth = depth
        self.boxes: dict = {}
        for i, entry in enumerate(patcher.get("boxes", []) or []):
            box = entry.get("box", {}) if isinstance(entry, dict) else {}
            bid = box.get("id")
            # A box with no (or a duplicate) id cannot be wired; keep it under
            # a synthetic key so discovery still sees it.
            if bid is None or bid in self.boxes:
                bid = f"__box{i}"
            self.boxes[bid] = box
        self.out_links: dict = {}
        self.in_links: dict = {}
        for entry in patcher.get("lines", []) or []:
            pl = entry.get("patchline", {}) if isinstance(entry, dict) else {}
            src, dst = pl.get("source"), pl.get("destination")
            if not (isinstance(src, list) and isinstance(dst, list)
                    and len(src) >= 2 and len(dst) >= 2):
                continue
            s, d = (src[0], int(src[1])), (dst[0], int(dst[1]))
            if s[0] in self.boxes and d[0] in self.boxes:
                self.out_links.setdefault(s, []).append(d)
                self.in_links.setdefault(d, []).append(s)
        self.inlets = sorted(
            (b for b, x in self.boxes.items() if x.get("maxclass") == "inlet"),
            key=lambda b: _xkey(self.boxes[b]),
        )
        self.outlets = sorted(
            (b for b, x in self.boxes.items() if x.get("maxclass") == "outlet"),
            key=lambda b: _xkey(self.boxes[b]),
        )
        self.children: dict = {}
        for bid, box in self.boxes.items():
            inner = box.get("patcher")
            if (isinstance(inner, dict) and obj_name(box) not in _GEN_OBJECTS
                    and depth < MAX_SCOPE_DEPTH):
                child = _Scope(fidx, inner, (self, bid), depth + 1)
                self.children[bid] = child
                fidx.scopes.append(child)
        for bid, box in self.boxes.items():
            name = obj_name(box)
            toks = _tokens(box)
            if _base(name) in ("send~",) and len(toks) >= 2:
                fidx.sends.setdefault(toks[1], []).append((self, bid))
            elif _base(name) in ("receive~",) and len(toks) >= 2:
                fidx.receives.setdefault(toks[1], []).append((self, bid))


class _FileIndex:
    def __init__(self, path: Path, data: dict):
        self.path = path
        self.scopes: list = []
        self.sends: dict = {}
        self.receives: dict = {}
        self.root = _Scope(self, data["patcher"], None)
        self.scopes.insert(0, self.root)


def _read(path: Path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict) or not isinstance(data.get("patcher"), dict):
        return None
    return data


class HostGraph:
    """Port-kind inference over one directory of patches (cached per instance)."""

    def __init__(self):
        self._files: dict = {}
        self._instances: dict = {}
        self._routes: dict = {}

    # -- files ------------------------------------------------------------------

    def file(self, path) -> "_FileIndex | None":
        p = Path(path).resolve()
        if p not in self._files:
            if len(self._files) >= _MAX_FILES:
                return None
            data = _read(p) if p.suffix.lower() == ".maxpat" else None
            self._files[p] = _FileIndex(p, data) if data else None
        return self._files[p]

    def _abstraction(self, scope: _Scope, box: dict):
        """(file index, kind) for a box that loads a sibling .maxpat
        (newobj abstraction, poly~ NAME, bpatcher without embedded patcher)."""
        if isinstance(box.get("patcher"), dict):
            return None
        name = obj_name(box)
        if name == "poly~":
            toks = _tokens(box)
            stem, kind = (toks[1] if len(toks) >= 2 else ""), "poly"
        elif name == "bpatcher":
            stem, kind = str(box.get("name", "") or ""), "plain"
        elif box.get("maxclass") == "newobj" and name and not name.endswith("~"):
            stem, kind = name, "plain"
        else:
            return None
        if stem.endswith(".maxpat"):
            stem = stem[:-len(".maxpat")]
        if not stem or "/" in stem or "\\" in stem or ".." in stem:
            return None
        target = scope.fidx.path.parent / f"{stem}.maxpat"
        if not target.is_file():
            return None
        fidx = self.file(target)
        return (fidx, kind) if fidx is not None else None

    def instances(self, fidx: _FileIndex) -> list:
        """(scope, box id, kind) for every box in a sibling .maxpat that loads
        ``fidx`` as an abstraction."""
        key = fidx.path
        if key in self._instances:
            return self._instances[key]
        found: list = []
        self._instances[key] = found
        stem = fidx.path.stem
        for sib in sorted(fidx.path.parent.glob("*.maxpat")):
            if sib.resolve() == fidx.path:
                continue
            try:
                if stem not in sib.read_text(encoding="utf-8", errors="ignore"):
                    continue
            except OSError:
                continue
            other = self.file(sib)
            if other is None:
                continue
            for sc in other.scopes:
                for bid, box in sc.boxes.items():
                    ab = self._abstraction(sc, box)
                    if ab is not None and ab[0] is fidx:
                        found.append((sc, bid, ab[1]))
        return found

    def gen_hosts(self, gendsp: Path) -> list:
        """(scope, box id) for every gen~ / mc.gen~ box in a sibling .maxpat
        that loads ``gendsp`` by name."""
        out: list = []
        stem = gendsp.stem
        for sib in sorted(gendsp.parent.glob("*.maxpat")):
            try:
                if stem not in sib.read_text(encoding="utf-8", errors="ignore"):
                    continue
            except OSError:
                continue
            fidx = self.file(sib)
            if fidx is None:
                continue
            for sc in fidx.scopes:
                for bid, box in sc.boxes.items():
                    if box.get("maxclass") != "newobj" or obj_name(box) not in _GEN_OBJECTS:
                        continue
                    data = box.get("data")
                    if isinstance(box.get("patcher"), dict) or (
                        isinstance(data, dict) and isinstance(data.get("patcher"), dict)
                    ):
                        continue
                    name = external_gendsp_name(_tokens(box))
                    if name and (name == stem or name == f"{stem}.gendsp"):
                        out.append((sc, bid))
        return out

    # -- downstream ---------------------------------------------------------------

    def outlet_kind(self, scope: _Scope, bid, outlet: int) -> tuple:
        """(kind, evidence) for box outlet ``outlet``: AUDIO when a path
        reaches an audio sink, else CONTROL."""
        stops: list = []
        seen: set = set()
        queue = [(scope, d) for d in scope.out_links.get((bid, outlet), [])]
        if not queue:
            return CONTROL, "unconnected"
        budget = _BUDGET
        while queue:
            budget -= 1
            if budget < 0:
                return AUDIO, "search budget exhausted (host unknown)"
            sc, (dbid, din) = queue.pop()
            key = (id(sc), dbid, din)
            if key in seen:
                continue
            seen.add(key)
            verdict = self._down_step(sc, dbid, din, queue, stops)
            if verdict is not None:
                return AUDIO, verdict
        uniq = list(dict.fromkeys(stops))
        return CONTROL, "no audio sink (" + ", ".join(uniq[:3]) + (", ..." if len(uniq) > 3 else "") + ")"

    def _follow(self, sc: _Scope, bid, queue: list, outlets=None) -> None:
        box = sc.boxes[bid]
        types = box.get("outlettype")
        n = len(types) if isinstance(types, list) else None
        idxs = outlets if outlets is not None else range(n if n is not None else 8)
        for o in idxs:
            if isinstance(types, list) and o < len(types) and types[o] not in _SIGNAL_TYPES:
                continue
            for d in sc.out_links.get((bid, o), []):
                queue.append((sc, d))

    def _down_step(self, sc: _Scope, bid, inlet: int, queue: list, stops: list):
        """Expand one (box, inlet). Returns an evidence string on reaching an
        audio sink (or an unknown host), else None after queueing successors."""
        box = sc.boxes[bid]
        name = obj_name(box)
        base = _base(name)
        if name in _AUDIO_SINKS or base in _AUDIO_SINKS:
            return name
        toks = _tokens(box)
        if base == "send~":
            targets = sc.fidx.receives.get(toks[1] if len(toks) >= 2 else "", [])
            if not targets:
                return f"{name} {toks[1] if len(toks) >= 2 else ''} (no receive~ in this file)".strip()
            for rsc, rbid in targets:
                self._follow(rsc, rbid, queue)
            return None
        if name == "outlet" or (base == "out" and sc.parent is None):
            return self._leave(sc, bid, queue, stops)
        if bid in sc.children:
            child = sc.children[bid]
            if inlet < len(child.inlets):
                ibid = child.inlets[inlet]
                for d in child.out_links.get((ibid, 0), []):
                    queue.append((child, d))
            return None
        ab = self._abstraction(sc, box)
        if ab is not None:
            fidx, kind = ab
            for (asc, abid) in self._abstraction_inlets(fidx, kind, inlet):
                self._follow(asc, abid, queue)
            return None
        if name in _GEN_OBJECTS:
            route = self._gen_route(sc, bid, inlet)
            if route is None:           # codebox unavailable: inlet 0 passes
                route = None if inlet == 0 else []
                if inlet == 0:
                    self._follow(sc, bid, queue)
            if route:
                self._follow(sc, bid, queue, outlets=route)
            elif route is not None:
                stops.append(f"{name} inlet {inlet + 1}")
            return None
        if base in _DISPLAY_STOPS:
            stops.append(name)
            return None
        if base in _PARAM_INLET0:
            stops.append(f"{name} inlet {inlet + 1}")
            return None
        if base in _ALL_INLETS_AUDIO or (base in _RIGHT_INLETS_AUDIO and inlet >= 1):
            self._follow(sc, bid, queue)
            return None
        if base in _RIGHT_INLETS_AUDIO:
            stops.append(f"{name} inlet {inlet + 1}")
            return None
        if name.endswith("~"):
            if inlet == 0:
                self._follow(sc, bid, queue)
            else:
                stops.append(f"{name} inlet {inlet + 1}")
            return None
        stops.append(name or str(box.get("maxclass", "")))
        return None

    def _gen_patcher(self, sc: _Scope, box: dict):
        inner = box.get("patcher")
        if isinstance(inner, dict):
            return inner
        data = box.get("data")
        if isinstance(data, dict) and isinstance(data.get("patcher"), dict):
            return data["patcher"]
        name = external_gendsp_name(_tokens(box))
        if not name or "/" in name or "\\" in name or ".." in name:
            return None
        fname = name if name.endswith(".gendsp") else f"{name}.gendsp"
        data = _read(sc.fidx.path.parent / fname)
        return data["patcher"] if data else None

    def _gen_route(self, sc: _Scope, bid, inlet: int):
        """Box outlets a downstream gen~ passes inlet ``inlet``'s value to, or
        None when its codebox cannot be read or run.

        From the downstream codebox's value dataflow (value_dependencies):
        inlet 0 reaches every outlet whose value depends on it; a later inlet
        only the same-numbered outlet (a stereo pair). A frequency or index
        into a later inlet of a one-outlet filter or player therefore stops
        there."""
        key = (id(sc), bid, inlet)
        if key in self._routes:
            return self._routes[key]
        from src.maxpat.dsp_sim.genexpr_interp import parse_codebox, value_dependencies

        route = None
        patcher = self._gen_patcher(sc, sc.boxes[bid])
        if patcher is not None:
            try:
                found: set = set()
                any_codebox = False
                for entry in patcher.get("boxes", []) or []:
                    cbox = entry.get("box", {}) if isinstance(entry, dict) else {}
                    if cbox.get("maxclass") != "codebox":
                        continue
                    any_codebox = True
                    ins, outs = gen_port_map(patcher, cbox.get("id"))
                    deps = value_dependencies(parse_codebox(cbox.get("code", "") or ""))
                    for k_in, gin in ins.items():
                        if gin != inlet:
                            continue
                        for k_out, srcs in deps.items():
                            if k_in in srcs:
                                found.update(o for o in outs.get(k_out, [])
                                             if inlet == 0 or o == inlet)
                route = sorted(found) if any_codebox else None
            except Exception:   # unsupported or unparsable codebox: fall back
                route = None
        self._routes[key] = route
        return route

    def _leave(self, sc: _Scope, bid, queue: list, stops: list):
        """An outlet box: continue in the parent box, or at every instance of
        this file; an abstraction with no instance is an unknown host."""
        if sc.parent is not None:
            psc, pbid = sc.parent
            if bid in sc.outlets:
                self._follow(psc, pbid, queue, outlets=[sc.outlets.index(bid)])
            return None
        insts = self.instances(sc.fidx)
        if not insts:
            return "abstraction outlet, no host instance in this directory"
        for isc, ibid, kind in insts:
            j = self._top_outlet_index(sc, bid, kind)
            if j is not None:
                self._follow(isc, ibid, queue, outlets=[j])
        return None

    @staticmethod
    def _top_outlet_index(sc: _Scope, bid, kind: str):
        box = sc.boxes[bid]
        if kind == "poly":
            n = _port_number(box)
            return n - 1 if n and box.get("maxclass") != "outlet" else None
        return sc.outlets.index(bid) if bid in sc.outlets else None

    @staticmethod
    def _abstraction_inlets(fidx: _FileIndex, kind: str, inlet: int) -> list:
        root = fidx.root
        if kind == "poly":
            return [
                (root, b) for b, box in root.boxes.items()
                if _base(obj_name(box)) in ("in~", "in") and _port_number(box) == inlet + 1
            ]
        return [(root, root.inlets[inlet])] if inlet < len(root.inlets) else []

    # -- upstream -----------------------------------------------------------------

    def inlet_kind(self, scope: _Scope, bid, inlet: int) -> tuple:
        """(kind, evidence) of the signal arriving at box inlet ``inlet``."""
        sources = [(scope, s) for s in scope.in_links.get((bid, inlet), [])]
        kind, ev = self._combine(sources, set(), [_BUDGET])
        if kind is None:
            return ZERO, "no signal connected"
        return kind, ev

    def _combine(self, sources: list, seen: set, budget: list):
        best, ev = None, ""
        for sc, (sbid, sout) in sources:
            k, e = self._up(sc, sbid, sout, seen, budget)
            if k is not None and (best is None or _RANK[k] > _RANK[best]):
                best, ev = k, e
            if best == AUDIO:
                break
        return best, ev

    def _up(self, sc: _Scope, bid, outlet: int, seen: set, budget: list):
        budget[0] -= 1
        if budget[0] < 0:
            return AUDIO, "search budget exhausted (host unknown)"
        key = (id(sc), bid, outlet)
        if key in seen:
            return None, ""
        seen.add(key)
        box = sc.boxes[bid]
        name = obj_name(box)
        base = _base(name)
        toks = _tokens(box)
        if base in _TRIGGER_SOURCES:
            return TRIGGER, name
        if base in _CONTROL_SOURCES:
            return CONTROL, name
        if name == "inlet" or (base in ("in~", "in") and sc.parent is None):
            return self._enter_from_host(sc, bid, seen, budget)
        if base == "receive~":
            sends = sc.fidx.sends.get(toks[1] if len(toks) >= 2 else "", [])
            if not sends:
                return AUDIO, f"{name} with no send~ in this file"
            srcs = [(ssc, s) for ssc, sbid in sends for s in ssc.in_links.get((sbid, 0), [])]
            return self._combine(srcs, seen, budget)
        if bid in sc.children:
            child = sc.children[bid]
            if outlet < len(child.outlets):
                obid = child.outlets[outlet]
                return self._combine(
                    [(child, s) for s in child.in_links.get((obid, 0), [])], seen, budget
                )
            return None, ""
        ab = self._abstraction(sc, box)
        if ab is not None:
            fidx, kind = ab
            root = fidx.root
            if kind == "poly":
                obids = [b for b, x in root.boxes.items()
                         if _base(obj_name(x)) in ("out~", "out") and _port_number(x) == outlet + 1]
            else:
                obids = [root.outlets[outlet]] if outlet < len(root.outlets) else []
            return self._combine(
                [(root, s) for ob in obids for s in root.in_links.get((ob, 0), [])], seen, budget
            )
        if name in _GEN_OBJECTS:
            kind, ev = self.outlet_kind(sc, bid, outlet)
            return kind, f"{name} out{outlet + 1} ({kind})"
        if base in _MATH_PASS:
            n_in = int(box.get("numinlets", 2) or 2)
            srcs = [(sc, s) for i in range(max(n_in, 1)) for s in sc.in_links.get((bid, i), [])]
            return self._combine(srcs, seen, budget)
        types = box.get("outlettype")
        if isinstance(types, list) and outlet < len(types):
            if types[outlet] not in _SIGNAL_TYPES:
                return None, ""          # a message cord: no signal
        elif not name.endswith("~"):
            return None, ""
        return AUDIO, name or str(box.get("maxclass", ""))

    def _enter_from_host(self, sc: _Scope, bid, seen: set, budget: list):
        box = sc.boxes[bid]
        if sc.parent is not None:
            if bid not in sc.inlets:
                return None, ""
            psc, pbid = sc.parent
            j = sc.inlets.index(bid)
            return self._combine([(psc, s) for s in psc.in_links.get((pbid, j), [])], seen, budget)
        insts = self.instances(sc.fidx)
        if not insts:
            return AUDIO, "abstraction inlet, no host instance in this directory"
        srcs: list = []
        for isc, ibid, kind in insts:
            if kind == "poly":
                n = _port_number(box)
                j = n - 1 if n and box.get("maxclass") != "inlet" else None
            else:
                j = sc.inlets.index(bid) if bid in sc.inlets else None
            if j is not None:
                srcs.extend((isc, s) for s in isc.in_links.get((ibid, j), []))
        return self._combine(srcs, seen, budget)


def gen_port_map(gen_patcher: dict, code_box_id) -> tuple:
    """(inputs, outputs) for one codebox inside a gen patcher: codebox inlet
    k (1-based) -> gen~ box inlet index (0-based) via its ``in M`` box, and
    codebox outlet k -> gen~ box outlet index via ``out M``. A codebox port
    with no in / out cord is absent from the map."""
    boxes = {}
    for entry in gen_patcher.get("boxes", []) or []:
        box = entry.get("box", {}) if isinstance(entry, dict) else {}
        if box.get("id") is not None:
            boxes[box["id"]] = box
    ins: dict = {}
    outs: dict = {}
    for entry in gen_patcher.get("lines", []) or []:
        pl = entry.get("patchline", {}) if isinstance(entry, dict) else {}
        src, dst = pl.get("source"), pl.get("destination")
        if not (isinstance(src, list) and isinstance(dst, list)
                and len(src) >= 2 and len(dst) >= 2):
            continue
        if dst[0] == code_box_id and src[0] in boxes:
            toks = _tokens(boxes[src[0]])
            if len(toks) >= 2 and toks[0] == "in":
                try:
                    ins.setdefault(int(dst[1]) + 1, int(float(toks[1])) - 1)
                except ValueError:
                    pass
        if src[0] == code_box_id and dst[0] in boxes:
            toks = _tokens(boxes[dst[0]])
            if len(toks) >= 2 and toks[0] == "out":
                try:
                    outs.setdefault(int(src[1]) + 1, []).append(int(float(toks[1])) - 1)
                except ValueError:
                    pass
    return ins, outs
