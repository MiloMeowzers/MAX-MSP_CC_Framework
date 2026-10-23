"""Machine-applicable quick-fix payloads for critic findings (fix-plan Q39, review §5.6 item 7).

A :class:`Fix` rides on :attr:`CriticResult.fix` (optional, default None).
It is pure data: a ``kind`` from :data:`FIX_KINDS`, a one-line
``description`` for the user, and ``ops``, a tuple of frozen :class:`FixOp`
whose ``op`` is one of :data:`FIX_OPS`. It holds no callables and no scope
path (the applier reads ``CriticResult.path``); only
:mod:`src.maxpat.quickfix` applies one, and only through the Patcher API.

Kinds:
  - ``insert_trigger``: a reconverging fan-out (structure critic) gets a
    ``t ...`` whose outlets fire the branches in a safe order.
  - ``rewrite_gen_param``: a gen~ ``@param $1`` message becomes ``param $1``.
  - ``insert_gain_normalizer``: an unsafe gain source gets ``scale <lo> <hi>
    0. 1.`` (bounded source) or ``clip 0. 1.`` (constant source).
  - ``set_bach_out``: a bach box feeding non-bach objects gets ``@out t``.

Ops:
  - ``add_box``: ``box`` is a placeholder id (``$new1``; a real MAX box id
    never starts with ``$``), ``text`` the full box text, ``near`` the real
    box it is placed below.
  - ``remove_cord`` / ``add_cord``: ``src``, ``outlet``, ``dst``, ``inlet``;
    add_cord ends may be placeholders.
  - ``set_text``: ``box``, the new ``text`` and the ``old_text`` it must
    currently have.

:func:`check_fix_contract` checks the per-kind shape; every builder's
output passes it. This module imports no Patcher.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

FIX_KINDS = ("insert_trigger", "rewrite_gen_param", "insert_gain_normalizer", "set_bach_out")
FIX_OPS = ("add_box", "remove_cord", "add_cord", "set_text")
ADDABLE_NAMES = frozenset({"t", "trigger", "scale", "clip"})
NEW_REF_PREFIX = "$new"

_TRIGGER_LETTERS = frozenset("bifls")


@dataclass(frozen=True)
class FixOp:
    """One edit step of a :class:`Fix` (fields per op in the module docstring)."""

    op: str
    box: str | None = None
    text: str | None = None
    old_text: str | None = None
    src: str | None = None
    outlet: int | None = None
    dst: str | None = None
    inlet: int | None = None
    near: str | None = None

    def __post_init__(self):
        if self.op not in FIX_OPS:
            raise ValueError(f"unknown fix op {self.op!r} (expected one of {FIX_OPS})")


@dataclass(frozen=True)
class Fix:
    """A machine-applicable fix: ``kind``, one-line ``description``, ``ops`` tuple."""

    kind: str
    description: str
    ops: tuple = ()

    def __post_init__(self):
        if self.kind not in FIX_KINDS:
            raise ValueError(f"unknown fix kind {self.kind!r} (expected one of {FIX_KINDS})")
        if not isinstance(self.ops, tuple):
            raise ValueError("Fix.ops must be a tuple of FixOp")
        for op in self.ops:
            if not isinstance(op, FixOp):
                raise ValueError(f"Fix.ops holds a non-FixOp {op!r}")


def is_new_ref(box_id) -> bool:
    """True for an add_box placeholder id (``$new1``)."""
    return isinstance(box_id, str) and box_id.startswith(NEW_REF_PREFIX)


def _cord_ok(op: FixOp) -> bool:
    return (
        isinstance(op.src, str) and op.src
        and isinstance(op.dst, str) and op.dst
        and isinstance(op.outlet, int) and op.outlet >= 0
        and isinstance(op.inlet, int) and op.inlet >= 0
    )


def _split(ops) -> dict:
    out = {name: [] for name in FIX_OPS}
    for op in ops:
        out[op.op].append(op)
    return out


def _check_add_box(op: FixOp) -> list[str]:
    if not is_new_ref(op.box):
        raise ValueError(f"add_box id {op.box!r} is not a {NEW_REF_PREFIX} placeholder")
    if not isinstance(op.text, str) or not op.text.split():
        raise ValueError("add_box has no text")
    tokens = op.text.split()
    if tokens[0] not in ADDABLE_NAMES:
        raise ValueError(f"add_box name {tokens[0]!r} is not one of {sorted(ADDABLE_NAMES)}")
    return tokens


def check_fix_contract(fix: Fix) -> None:
    """Raise ValueError naming the breach when *fix* does not fit its kind.

    insert_trigger: one add_box ``t``/``trigger`` with N >= 2 letters in
    b/i/f/l/s; N remove_cord sharing one (src, outlet) with distinct
    (dst, inlet); one add_cord (src, outlet) -> placeholder inlet 0; N
    add_cord from placeholder outlets 0..N-1, each once, whose (dst, inlet)
    set equals the removed set.

    insert_gain_normalizer: one add_box ``scale``/``clip``, one remove_cord
    (s, o -> d, i) and the two add_cords s:o -> new:0 and new:0 -> d:i.

    rewrite_gen_param / set_bach_out: exactly one set_text with ``text`` and
    ``old_text`` set and different.
    """
    if not isinstance(fix, Fix):
        raise ValueError(f"not a Fix: {fix!r}")
    ops = _split(fix.ops)
    for op in ops["remove_cord"] + ops["add_cord"]:
        if not _cord_ok(op):
            raise ValueError(f"{op.op} needs src, outlet, dst and inlet: {op!r}")
    for op in ops["remove_cord"]:
        if is_new_ref(op.src) or is_new_ref(op.dst):
            raise ValueError("remove_cord cannot name a placeholder box")

    if fix.kind in ("rewrite_gen_param", "set_bach_out"):
        if len(fix.ops) != 1 or len(ops["set_text"]) != 1:
            raise ValueError(f"{fix.kind} must be exactly one set_text")
        op = ops["set_text"][0]
        if not isinstance(op.box, str) or not op.box or is_new_ref(op.box):
            raise ValueError("set_text needs a real box id")
        if not isinstance(op.text, str) or not isinstance(op.old_text, str):
            raise ValueError("set_text needs text and old_text")
        if not op.text.strip() or op.text == op.old_text:
            raise ValueError("set_text text must be non-empty and differ from old_text")
        return

    if ops["set_text"]:
        raise ValueError(f"{fix.kind} takes no set_text")
    if len(ops["add_box"]) != 1:
        raise ValueError(f"{fix.kind} needs exactly one add_box")
    add = ops["add_box"][0]
    tokens = _check_add_box(add)
    new = add.box
    for op in ops["add_cord"]:
        for end in (op.src, op.dst):
            if is_new_ref(end) and end != new:
                raise ValueError(f"add_cord names an undeclared placeholder {end!r}")

    if fix.kind == "insert_trigger":
        if tokens[0] not in ("t", "trigger"):
            raise ValueError(f"insert_trigger adds {tokens[0]!r}, not t/trigger")
        letters = tokens[1:]
        n = len(letters)
        if n < 2 or any(l not in _TRIGGER_LETTERS for l in letters):
            raise ValueError(f"insert_trigger letters {letters!r} must be >= 2 of b/i/f/l/s")
        removed = ops["remove_cord"]
        if len(removed) != n:
            raise ValueError(f"insert_trigger removes {len(removed)} cords for {n} outlets")
        sources = {(op.src, op.outlet) for op in removed}
        if len(sources) != 1:
            raise ValueError("insert_trigger remove_cords must share one source outlet")
        src, outlet = next(iter(sources))
        removed_set = {(op.dst, op.inlet) for op in removed}
        if len(removed_set) != n:
            raise ValueError("insert_trigger removes a duplicate cord")
        feeds = [op for op in ops["add_cord"] if op.dst == new]
        outs = [op for op in ops["add_cord"] if op.src == new]
        if len(feeds) + len(outs) != len(ops["add_cord"]):
            raise ValueError("insert_trigger add_cord must touch the new box")
        if len(feeds) != 1 or (feeds[0].src, feeds[0].outlet, feeds[0].inlet) != (src, outlet, 0):
            raise ValueError("insert_trigger needs one add_cord source outlet -> new inlet 0")
        if sorted(op.outlet for op in outs) != list(range(n)):
            raise ValueError("insert_trigger must use each trigger outlet 0..N-1 once")
        if {(op.dst, op.inlet) for op in outs} != removed_set or any(is_new_ref(op.dst) for op in outs):
            raise ValueError("insert_trigger outlets must cover exactly the removed destinations")
        return

    # insert_gain_normalizer
    if tokens[0] not in ("scale", "clip"):
        raise ValueError(f"insert_gain_normalizer adds {tokens[0]!r}, not scale/clip")
    if len(ops["remove_cord"]) != 1 or len(ops["add_cord"]) != 2:
        raise ValueError("insert_gain_normalizer is one remove_cord and two add_cords")
    rm = ops["remove_cord"][0]
    want = {(rm.src, rm.outlet, new, 0), (new, 0, rm.dst, rm.inlet)}
    got = {(op.src, op.outlet, op.dst, op.inlet) for op in ops["add_cord"]}
    if got != want:
        raise ValueError("insert_gain_normalizer must reroute src -> new:0 -> dst")


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

_NEW = NEW_REF_PREFIX + "1"


def trigger_fix(src_id: str, src_outlet: int, src_label: str, letter: str, ordered) -> Fix:
    """insert_trigger for a fan-out from ``src_id:src_outlet``.

    *ordered* lists the branches ``(dst_id, dst_inlet, dst_label)`` in firing
    order, first to last. Trigger outlets fire right to left, so the k-th
    fired branch goes on outlet N-1-k and the last one on outlet 0.
    """
    ordered = list(ordered)
    n = len(ordered)
    text = "t " + " ".join([letter] * n)
    ops = [FixOp("add_box", box=_NEW, text=text, near=src_id)]
    for dst, inlet, _label in ordered:
        ops.append(FixOp("remove_cord", src=src_id, outlet=src_outlet, dst=dst, inlet=inlet))
    ops.append(FixOp("add_cord", src=src_id, outlet=src_outlet, dst=_NEW, inlet=0))
    parts = []
    for k, (dst, inlet, label) in enumerate(ordered):
        out = n - 1 - k
        ops.append(FixOp("add_cord", src=_NEW, outlet=out, dst=dst, inlet=inlet))
        parts.append(f"outlet {out} -> '{label}' ({dst}) inlet {inlet}")
    description = (
        f"insert '{text}' after '{src_label}' ({src_id}) outlet {src_outlet}, "
        f"firing {', then '.join(parts)}"
    )
    return Fix("insert_trigger", description, tuple(ops))


_GEN_PARAM_RE = re.compile(r"(?<!\S)@(\w+)(?=\s+\$)")


def gen_param_fix(msg_id: str, old_text: str) -> Fix:
    """rewrite_gen_param: drop the ``@`` before each selector followed by a
    ``$`` argument (``@depth $1`` -> ``depth $1``)."""
    new_text = _GEN_PARAM_RE.sub(r"\1", old_text)
    return Fix(
        "rewrite_gen_param",
        f"rewrite message ({msg_id}) '{old_text}' -> '{new_text}' "
        f"(gen~ params take plain name messages)",
        (FixOp("set_text", box=msg_id, text=new_text, old_text=old_text),),
    )


def max_float(v) -> str:
    """A MAX float atom: integer-valued -> ``127.`` / ``-12.``, else the
    shortest fixed-point repr with no exponent."""
    v = float(v)
    if v == int(v):
        return f"{int(v)}."
    s = repr(v)
    if "e" in s or "E" in s:
        s = f"{v:.12f}".rstrip("0")
        if s.endswith("."):
            s += "0"
    return s


def gain_normalizer_fix(
    src_id: str,
    src_outlet: int,
    src_label: str,
    dst_id: str,
    dst_inlet: int,
    dst_label: str,
    text: str,
) -> Fix:
    """insert_gain_normalizer: route ``src:outlet -> dst:inlet`` through a new
    ``scale <lo> <hi> 0. 1.`` or ``clip 0. 1.`` box placed below the source."""
    ops = (
        FixOp("add_box", box=_NEW, text=text, near=src_id),
        FixOp("remove_cord", src=src_id, outlet=src_outlet, dst=dst_id, inlet=dst_inlet),
        FixOp("add_cord", src=src_id, outlet=src_outlet, dst=_NEW, inlet=0),
        FixOp("add_cord", src=_NEW, outlet=0, dst=dst_id, inlet=dst_inlet),
    )
    return Fix(
        "insert_gain_normalizer",
        f"insert '{text}' between '{src_label}' ({src_id}) outlet {src_outlet} and "
        f"'{dst_label}' ({dst_id}) inlet {dst_inlet}",
        ops,
    )


def bach_out_fix(box_id: str, old_text: str) -> Fix:
    """set_bach_out: append `` @out t``, or replace the token after ``@out``
    with ``t`` repeated to that token's length (``@out tn`` -> ``@out tt``)."""
    tokens = old_text.split()
    if "@out" not in tokens:
        tokens += ["@out", "t"]
    else:
        i = tokens.index("@out") + 1
        if i < len(tokens) and not tokens[i].startswith("@"):
            tokens[i] = "t" * len(tokens[i])
        else:
            tokens.insert(i, "t")
    new_text = " ".join(tokens)
    return Fix(
        "set_bach_out",
        f"set '{old_text}' ({box_id}) to '{new_text}' so non-bach objects get plain MAX lists",
        (FixOp("set_text", box=box_id, text=new_text, old_text=old_text),),
    )


__all__ = [
    "FIX_KINDS",
    "FIX_OPS",
    "ADDABLE_NAMES",
    "NEW_REF_PREFIX",
    "Fix",
    "FixOp",
    "check_fix_contract",
    "is_new_ref",
    "trigger_fix",
    "gen_param_fix",
    "gain_normalizer_fix",
    "bach_out_fix",
    "max_float",
]
