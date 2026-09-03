"""ccamxd -- read / inspect / byte-preserving re-inject of a ChopChop .amxd.

The .amxd is an `ampf` chunked container. After the `mx@c` marker the main
patcher is stored as *minified* JSON, preceded by a run of space padding
immediately after its opening `{`. Editing = parse that blob, mutate the dict,
re-minify, and re-pad to the identical byte span so the file size never changes
(the delivery checklist requires 1,705,180 bytes exactly for v6_174).

Verified on ChopChop_v6_174_BASE.amxd:
  - json.dumps(obj, separators=(",", ":")) reproduces Max's bytes exactly, so a
    no-op extract->inject is byte-identical (see `identity_ok`).
  - main-patcher slot 1,596,959 bytes, real content ~455 KB, ~1.14 MB of
    space headroom for edits.
  - a second small pretty-printed patcher + embedded .js follow the main blob;
    we never touch anything outside the main blob's brace span.

CLI:
  python ccamxd.py FILE --identity          # assert no-op round-trip is byte-exact
  python ccamxd.py FILE --scopes            # list every subpatcher scope
  python ccamxd.py FILE --dump "p Playback" # boxes + internal lines of one scope
  python ccamxd.py FILE --find rolling      # grep boxes by text/varname/maxclass
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

MARKER = b"mx@c"


# --------------------------------------------------------------------------- IO

def _match_brace(data: bytes, i: int) -> int:
    """Index of the `}` that closes the `{` at data[i], honouring strings/escapes."""
    depth = 0
    instr = False
    esc = False
    j = i
    n = len(data)
    while j < n:
        ch = data[j]
        if esc:
            esc = False
        elif ch == 0x5C:  # backslash
            esc = True
        elif ch == 0x22:  # quote
            instr = not instr
        elif not instr:
            if ch == 0x7B:  # {
                depth += 1
            elif ch == 0x7D:  # }
                depth -= 1
                if depth == 0:
                    return j
        j += 1
    raise ValueError("unbalanced brace from offset %d" % i)


@dataclass
class Amxd:
    path: Path
    raw: bytes
    i1: int                 # byte offset of the main blob's opening '{'
    j1: int                 # byte offset of its closing '}'
    patcher: dict           # parsed {"patcher": {...}}

    @property
    def slot(self) -> int:
        return self.j1 - self.i1 + 1

    def minified(self) -> bytes:
        return json.dumps(self.patcher, separators=(",", ":")).encode("utf-8")

    def headroom(self) -> int:
        return self.slot - len(self.minified())

    def rebuild(self) -> bytes:
        """Serialise current `patcher` back into a full-file byte string, same length."""
        body = self.minified()
        if len(body) > self.slot:
            raise ValueError(
                "edited patcher is %d bytes over the %d-byte slot (need to grow the "
                "container and fix length fields -- not supported)"
                % (len(body) - self.slot, self.slot)
            )
        if not body.startswith(b"{"):
            raise ValueError("serialised patcher does not start with '{'")
        pad = b" " * (self.slot - len(body))
        blob = b"{" + pad + body[1:]
        assert len(blob) == self.slot
        out = self.raw[: self.i1] + blob + self.raw[self.j1 + 1 :]
        if len(out) != len(self.raw):
            raise AssertionError(
                "size drift: %d != %d" % (len(out), len(self.raw))
            )
        return out

    def save(self, path: str | Path) -> None:
        Path(path).write_bytes(self.rebuild())

    def identity_ok(self) -> bool:
        """True iff a no-op extract->inject reproduces the original file byte-for-byte."""
        return self.rebuild() == self.raw


def load(path: str | Path) -> Amxd:
    path = Path(path)
    data = path.read_bytes()
    m = data.find(MARKER)
    if m < 0:
        # some .amxd are bare JSON
        i1 = data.find(b"{")
        j1 = _match_brace(data, i1)
        return Amxd(path, data, i1, j1, json.loads(data[i1 : j1 + 1]))
    i1 = data.find(b"{", m)
    j1 = _match_brace(data, i1)
    patcher = json.loads(data[i1 : j1 + 1].decode("utf-8"))
    return Amxd(path, data, i1, j1, patcher)


# ------------------------------------------------------------------------ model

@dataclass
class Scope:
    """One patcher level: root or a subpatcher. IDs are unique only within a scope."""

    path: str
    patcher: dict
    parent: "Scope | None" = None
    owner_text: str = ""          # text of the box that contains this subpatcher
    boxes: dict = field(default_factory=dict)   # id -> box dict

    def __post_init__(self):
        for entry in self.patcher.get("boxes", []):
            b = entry.get("box", entry)
            self.boxes[b.get("id")] = b

    # -- box helpers -------------------------------------------------------
    def label(self, box_id: str) -> str:
        b = self.boxes.get(box_id)
        if not b:
            return f"<missing {box_id}>"
        return b.get("text") or b.get("varname") or b.get("maxclass") or box_id

    def numinlets(self, box_id: str) -> int | None:
        b = self.boxes.get(box_id)
        return None if not b else b.get("numinlets")

    def numoutlets(self, box_id: str) -> int | None:
        b = self.boxes.get(box_id)
        return None if not b else b.get("numoutlets")

    def lines(self):
        for entry in self.patcher.get("lines", []):
            pl = entry.get("patchline", entry)
            src = pl.get("source")
            dst = pl.get("destination")
            if src and dst:
                yield src[0], int(src[1]), dst[0], int(dst[1])

    def iter_boxes(self):
        return self.boxes.items()


def iter_scopes(patcher_root: dict):
    """Yield every Scope (root first, then depth-first into subpatchers)."""
    root_pat = patcher_root.get("patcher", patcher_root)
    stack = [Scope("/", root_pat, None, "")]
    while stack:
        sc = stack.pop(0)
        yield sc
        children = []
        for entry in sc.patcher.get("boxes", []):
            b = entry.get("box", entry)
            sub = b.get("patcher")
            if sub is not None:
                name = (b.get("text") or b.get("varname") or "?").replace("p ", "").strip()
                child = Scope(sc.path + name[:28] + "/", sub, sc, b.get("text", ""))
                children.append(child)
        stack = children + stack


def find_scope(patcher_root: dict, name: str) -> Scope | None:
    want = name.replace("p ", "").strip().lower()
    for sc in iter_scopes(patcher_root):
        if sc.path == name:
            return sc
        seg = sc.path.rstrip("/").rsplit("/", 1)[-1].lower()
        if seg == want or sc.owner_text.lower() == name.lower():
            return sc
    return None


# -------------------------------------------------------------------------- CLI

def _cli(argv):
    if not argv:
        print(__doc__)
        return 2
    f = argv[0]
    rest = argv[1:]
    amx = load(f)

    if "--identity" in rest:
        ok = amx.identity_ok()
        print(f"identity round-trip: {'OK (byte-exact)' if ok else 'MISMATCH'}")
        print(f"  slot={amx.slot}  content={len(amx.minified())}  headroom={amx.headroom()}")
        return 0 if ok else 1

    if "--scopes" in rest:
        for sc in iter_scopes(amx.patcher):
            nb = len(sc.boxes)
            nl = sum(1 for _ in sc.lines())
            print(f"{sc.path:<52} {nb:>4} boxes  {nl:>4} lines")
        return 0

    if "--dump" in rest:
        name = rest[rest.index("--dump") + 1]
        sc = find_scope(amx.patcher, name)
        if not sc:
            print("scope not found:", name)
            return 1
        for bid, b in sc.iter_boxes():
            t = b.get("text") or b.get("maxclass")
            extra = " ".join(
                f"{k}={b[k]}" for k in ("varname", "numinlets", "numoutlets") if b.get(k) not in (None, "")
            )
            inner = "  [+subpatcher]" if b.get("patcher") else ""
            print(f"{bid:>14}  {t}   {extra}{inner}")
        print("--- lines (src[outlet] -> dst[inlet]) ---")
        for s, so, d, di in sc.lines():
            print(f"  {sc.label(s)} [{so}] -> [{di}] {sc.label(d)}")
        return 0

    if "--find" in rest:
        q = rest[rest.index("--find") + 1].lower()
        for sc in iter_scopes(amx.patcher):
            for bid, b in sc.iter_boxes():
                hay = f"{b.get('text','')} {b.get('varname','')} {b.get('maxclass','')}".lower()
                if q in hay:
                    print(f"[{sc.path}] {bid:>12}  varname={b.get('varname','-'):<20} "
                          f"{b.get('maxclass',''):<12} :: {(b.get('text') or '')[:90]}")
        return 0

    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(_cli(sys.argv[1:]))
