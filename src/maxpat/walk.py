"""Shared patcher walker and quote-aware box helpers (Q19; review A7, S1, S2).

One walker, one name extractor. :func:`iter_patchers` yields every embedded
patcher of a .maxpat dict with its path and context; the ``box_*`` helpers
read a box's maxclass, text, name and arguments through the quote-aware MAX
tokenizer (:func:`src.maxpat.io_resolvers.split_box_text`, Q10), so
``t "a b" c`` has two arguments and empty, whitespace-only, ``None`` or
non-string text never raises.

Contexts (one per yielded patcher):

* ``max``      -- the top level of a Max patch, or a ``p`` / ``patcher``
  subpatcher in Max scope;
* ``gen``      -- a gen~ / mc.gen~ / mcs.gen~ / gen / jit.gen / jit.pix /
  jit.gl.pix patcher, or any subpatcher inside one;
* ``rnbo``     -- an rnbo~ patcher, or any subpatcher inside one;
* ``poly``     -- an embedded poly~ / mc.poly~ patcher (Max scope);
* ``bpatcher`` -- an embedded bpatcher (Max scope).

:func:`scope_of` maps a context to the validation scope (max / gen / rnbo).

Only embedded patcher dicts are walked: ``box["patcher"]``, or
``box["data"]["patcher"]`` for mc.gen~ (MAX's mc wrapper). External files
(abstractions, a bpatcher with only ``name``, ``poly~ voice 8``) are never
loaded. Everything here is pure: no mutation, no I/O, and malformed input
yields less rather than raising.

The remaining walkers and extractors (``hooks._iter_patchers``,
``utils.get_box_name``, the critics, analysis, testing, graph, layout) move
onto this module in Q20.
"""

from __future__ import annotations

from typing import Iterator

from src.maxpat.db_lookup import (
    DOMAIN_SCOPES,
    GEN_CONTAINER_NAMES,
    detect_patcher_scope,
    inner_patcher_scope,
)
from src.maxpat.io_resolvers import split_box_text

CONTEXTS = ("max", "gen", "rnbo", "poly", "bpatcher")

# Patcher infrastructure, not user objects: object_name() returns None.
STRUCTURAL_MAXCLASSES = frozenset({"inlet", "outlet", "patcher", "bpatcher"})

_POLY_NAMES = frozenset({"poly~", "mc.poly~"})


# ---------------------------------------------------------------------------
# Box helpers
# ---------------------------------------------------------------------------


def box_maxclass(box) -> str:
    """The box's maxclass if it is a str, else ``""``."""
    if not isinstance(box, dict):
        return ""
    mc = box.get("maxclass")
    return mc if isinstance(mc, str) else ""


def box_text(box) -> str:
    """The box's text if it is a str, else ``""`` (None / numbers / lists)."""
    if not isinstance(box, dict):
        return ""
    text = box.get("text")
    return text if isinstance(text, str) else ""


def box_tokens(box) -> list[str]:
    """Quote-aware tokens of the box text (``split_box_text``)."""
    return split_box_text(box_text(box))


def box_name(box) -> str:
    """Object name: the first token for a newobj (``""`` when empty), else
    the maxclass (``""`` when it is not a str)."""
    maxclass = box_maxclass(box)
    if maxclass == "newobj":
        tokens = box_tokens(box)
        return tokens[0] if tokens else ""
    return maxclass


def box_args(box) -> list[str]:
    """Raw tokens after the name for a newobj (``@attrs`` and escapes kept,
    the drop-in for ``text.split()[1:]``); ``[]`` for any other box."""
    if box_maxclass(box) != "newobj":
        return []
    return box_tokens(box)[1:]


def object_name(box) -> str | None:
    """Name for object-database checks, or None when the box is skipped.

    None for the structural maxclasses (inlet / outlet / patcher /
    bpatcher), for a non-str maxclass and for a newobj with no tokens. A
    newobj gives its first token; any other box its maxclass (``""`` when
    the key is missing).
    """
    if not isinstance(box, dict):
        return None
    maxclass = box.get("maxclass", "")
    if not isinstance(maxclass, str):
        return None
    if maxclass in STRUCTURAL_MAXCLASSES:
        return None
    if maxclass == "newobj":
        tokens = box_tokens(box)
        return tokens[0] if tokens else None
    return maxclass


def inner_patcher(box) -> dict | None:
    """The embedded patcher dict: ``box["patcher"]``, else
    ``box["data"]["patcher"]`` (mc.gen~), else None."""
    if not isinstance(box, dict):
        return None
    inner = box.get("patcher")
    if isinstance(inner, dict):
        return inner
    data = box.get("data")
    if isinstance(data, dict):
        inner = data.get("patcher")
        if isinstance(inner, dict):
            return inner
    return None


def is_gen_container(box) -> bool:
    """True for a box whose embedded patcher is a Gen patcher by name
    (:data:`GEN_CONTAINER_NAMES`) or maxclass ``gen~``."""
    return box_name(box) in GEN_CONTAINER_NAMES or box_maxclass(box) == "gen~"


def _patcher_view(patcher) -> dict:
    """Sanitized shallow view for db_lookup scope detection (never raises)."""
    view: dict = {}
    if isinstance(patcher, dict):
        cn = patcher.get("classnamespace")
        if isinstance(cn, str):
            view["classnamespace"] = cn
        boxes = patcher.get("boxes")
        view["boxes"] = boxes if isinstance(boxes, list) else []
    return view


def inner_scope(box, parent_scope: str) -> str:
    """Scope (max / gen / rnbo) of the patcher embedded in *box*.

    ``inner_patcher_scope`` on a sanitized view: gen / rnbo containers by
    name, else the inner patcher's classnamespace / codebox, else
    *parent_scope* (subpatchers inherit).
    """
    if parent_scope not in DOMAIN_SCOPES:
        parent_scope = "max"
    view = {
        "maxclass": box_maxclass(box),
        "text": box_text(box),
        "patcher": _patcher_view(inner_patcher(box)),
    }
    return inner_patcher_scope(view, parent_scope)


def box_label(box) -> str:
    """Path label: ``p synth`` / ``poly~ voice`` / ``gen~`` (name plus the
    first positional argument) for a newobj, ``bpatcher`` (plus its file
    ``name``) for a bpatcher, the maxclass otherwise; ``?`` as fallback."""
    maxclass = box_maxclass(box)
    if maxclass == "newobj":
        tokens = box_tokens(box)
        if not tokens:
            return "?"
        if len(tokens) > 1 and not tokens[1].startswith("@"):
            return f"{tokens[0]} {tokens[1]}"
        return tokens[0]
    if maxclass == "bpatcher":
        name = box.get("name") if isinstance(box, dict) else None
        if isinstance(name, str) and name:
            return f"bpatcher {name}"
        return "bpatcher"
    return maxclass or "?"


# ---------------------------------------------------------------------------
# Paths and contexts
# ---------------------------------------------------------------------------


def path_ids(path: tuple) -> str:
    """Box-id chain of *path* joined by ``/`` (``obj-1/obj-2``); ``""`` at top."""
    return "/".join(box_id for box_id, _ in path)


def path_prefix(path: tuple) -> str:
    """Message prefix ``[p synth > gen~] `` of *path*; ``""`` at top."""
    if not path:
        return ""
    return "[" + " > ".join(label for _, label in path) + "] "


def scope_of(context: str) -> str:
    """Validation scope of a context: gen and rnbo map to themselves,
    every other context (max / poly / bpatcher) to ``max``."""
    return context if context in ("gen", "rnbo") else "max"


def _child_context(box: dict, parent_scope: str) -> str:
    scope = inner_scope(box, parent_scope)
    if scope in ("gen", "rnbo"):
        return scope
    if box_maxclass(box) == "bpatcher":
        return "bpatcher"
    if box_name(box) in _POLY_NAMES:
        return "poly"
    return "max"


def iter_patchers(patch, scope: str | None = None) -> Iterator[tuple[tuple, dict, str]]:
    """Yield ``(path, patcher_dict, context)`` for every patcher in *patch*.

    *patch* is a file dict with a dict ``patcher``, or a bare patcher dict
    with a ``boxes`` key; anything else yields nothing. The top level comes
    first with ``path == ()`` and context *scope* (when it is in
    DOMAIN_SCOPES) or the detected scope; embedded patchers follow in
    pre-order. ``path`` is a tuple of ``(box_id, label)`` pairs
    (:func:`box_label`; ``"?"`` for a box without an id).

    Iterative (an explicit stack), so deep nesting never hits the recursion
    limit; a patcher dict already visited (a cycle) is not yielded again.
    Non-dict entries and boxes are skipped; external files are never loaded.
    """
    if not isinstance(patch, dict):
        return
    top = patch.get("patcher")
    if not isinstance(top, dict):
        if "boxes" in patch:
            top = patch
        else:
            return
    if scope in DOMAIN_SCOPES:
        top_scope = scope
    else:
        top_scope = detect_patcher_scope(_patcher_view(top))

    stack: list[tuple[tuple, dict, str]] = [((), top, top_scope)]
    seen: set[int] = set()
    while stack:
        path, patcher, context = stack.pop()
        if id(patcher) in seen:
            continue
        seen.add(id(patcher))
        yield path, patcher, context

        boxes = patcher.get("boxes")
        if not isinstance(boxes, list):
            continue
        parent_scope = scope_of(context)
        children = []
        for entry in boxes:
            if not isinstance(entry, dict):
                continue
            box = entry.get("box")
            if not isinstance(box, dict):
                continue
            inner = inner_patcher(box)
            if inner is None or id(inner) in seen:
                continue
            box_id = box.get("id")
            box_id = str(box_id) if box_id is not None else "?"
            children.append((
                path + ((box_id, box_label(box)),),
                inner,
                _child_context(box, parent_scope),
            ))
        stack.extend(reversed(children))
