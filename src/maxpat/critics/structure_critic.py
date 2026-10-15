"""Structure critic -- checks patch architecture and connection patterns.

Catches structural issues that the mechanical validation pipeline does
not detect:
  - Fan-out without trigger (ordering ambiguity): blocker when branches
    reconverge on one box at different inlets, otherwise warning (Q3 / E1)
  - Hot/cold inlet ordering issues (stale value computation)
  - Invalid trigger types (Q21 / R4): ``t a`` and any other single
    lower-case letter outside b, i, f, l, s outputs the literal symbol
  - ``$N`` arity (Q21 / R4): a message box's highest ``$N`` above the
    atoms its inlet-0 feeders can together supply
  - Redundant/duplicate patchlines

Every scope of the shared :class:`src.maxpat.graph.PatchGraph` is reviewed
on its own boxes and cords (Q20); nested findings carry
``CriticResult.path`` and a ``[p synth] `` prefix. Gen scopes (including a
top-level .gendsp) run only the duplicate-patchline check: Gen is
synchronous per-sample dataflow, so Rule #3 ordering does not apply. A
reconvergence walk ends at a Jitter attribute/method message (a setter
message box cabled into a ``jit.*`` object), which emits nothing.

NOTE: Does NOT duplicate validation.py checks. Focus is on architectural
patterns a MAX expert would flag during code review.
"""

from __future__ import annotations

import re
from collections import defaultdict, deque

from src.maxpat import walk
from src.maxpat.critics.base import CriticResult, tag_results
from src.maxpat.graph import SIGNAL_OUTLET_TYPES, PatchGraph, outlet_is_signal


# Object names that provide explicit ordering (used by the hot/cold check)
_TRIGGER_NAMES = frozenset({"trigger", "t"})

# Outlet types that carry audio; fan-out from these is never flagged (Rule #3)
_SIGNAL_OUTLET_TYPES = SIGNAL_OUTLET_TYPES

# Display-only sinks: dropped from a fan-out when they have no outgoing cord
# (Q3 / E1 -- e.g. minitaur scale/expr -> send + display flonum)
_DISPLAY_SINK_NAMES = frozenset({
    "flonum", "number", "print", "comment", "meter~", "levelmeter~",
    "live.meter~",
})

# preset outlets 0/2/4 are include/exclude/capture membership cords
# (preset.maxref.xml), not ordered data -- e.g. timestretch obj-51 outlet 2
_PRESET_MEMBERSHIP_OUTLETS = frozenset({0, 2, 4})

# Boxes with no cold inlet that can hold a stale value, or that route each
# inlet to an independent inner path: a reconvergence on them is not a hazard
_ALL_HOT_NAMES = frozenset({
    "js", "jsui", "v8", "v8ui", "v8.codebox", "node.script", "node.codebox",
    "p", "patcher", "bpatcher", "poly~", "mc.poly~", "pfft~", "rnbo~",
    "gen~", "mc.gen~",
})


def review_structure(
    patch_dict: dict,
    *,
    graph: "PatchGraph | None" = None,
    db=None,
) -> list[CriticResult]:
    """Review structural aspects of a patch, every scope (Q20).

    Checks, per scope of the shared graph:
      1. Fan-out without trigger (2+ non-display destinations from one
         control outlet; blocker only on reconvergence -- Q3 / E1)
      2. Hot/cold inlet ordering (multiple inlets fed without trigger ordering)
      3. Invalid trigger types (blocker; Q21 / R4)
      4. Message ``$N`` arity (blocker; Q21 / R4)
      5. Redundant/duplicate patchlines

    Gen scopes run only check 5. Top-level results come first, nested
    scopes follow in pre-order, tagged with their path.

    Args:
        patch_dict: A .maxpat-format dict.
        graph: The shared PatchGraph of *patch_dict* (review_patch passes
            it); built here when None.
        db: Keyword-only ObjectDatabase for the Q21 checks (inlet ``hot``
            flags, outlet types). review_patch passes its own; when None,
            one is built here, at most once per call and only when a check
            needs it.

    Returns:
        List of CriticResult findings.
    """
    if graph is None:
        graph = PatchGraph.build(patch_dict)
    dbh = _LazyDB(db)
    results: list[CriticResult] = []
    for scope in graph.scopes:
        found: list[CriticResult] = []
        if scope.context != "gen":
            found.extend(_check_fan_out_without_trigger(scope.boxes, scope.edges))
            found.extend(_check_hot_cold_ordering(scope.boxes, scope.edges))
            found.extend(_check_trigger_types(scope))
            found.extend(_check_dollar_arity(scope, dbh))
        found.extend(_check_redundant_connections(scope.edges))
        results.extend(tag_results(found, scope.path))
    return results


class _LazyDB:
    """An ObjectDatabase handle built on first use (at most one per call)."""

    __slots__ = ("_db",)

    def __init__(self, db=None):
        self._db = db

    def get(self):
        if self._db is None:
            from src.maxpat.db_lookup import ObjectDatabase

            self._db = ObjectDatabase()
        return self._db

    def lookup(self, name):
        if not isinstance(name, str) or not name:
            return None
        try:
            obj = self.get().lookup(name)
        except Exception:
            return None
        return obj if isinstance(obj, dict) else None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_trigger_object(box: dict) -> bool:
    """Check if a box is a trigger/t object."""
    name = walk.box_name(box)
    return name in _TRIGGER_NAMES


def _is_signal_object(box: dict) -> bool:
    """Check if a box is a signal-rate (~) object."""
    name = walk.box_name(box)
    return name.endswith("~")


# ---------------------------------------------------------------------------
# Check 1: Fan-out without trigger
# ---------------------------------------------------------------------------

# Moved to src.maxpat.graph.outlet_is_signal (Q20); kept as an alias.
_outlet_is_signal = outlet_is_signal

# Message selectors that make a Jitter object output (not attribute setters)
_JIT_OUTPUT_SELECTORS = frozenset({
    "bang", "outputmatrix", "jit_matrix", "jit_gl_texture",
})


def _is_number(token: str) -> bool:
    try:
        float(token)
    except ValueError:
        return False
    return True


def _is_setter_message(box) -> bool:
    """True for a message box whose every segment starts with a symbol
    selector (an attribute or method call, not output-triggering).

    Segments are split at unescaped commas (a token that is ``,`` or ends
    in ``,`` but not ``\\,``). A selector is a symbol when it is not a
    number, does not start with ``$`` or ``;``, is not one of
    ``_JIT_OUTPUT_SELECTORS`` and does not start with ``get``.
    """
    if walk.box_maxclass(box) != "message":
        return False
    segments: list[list[str]] = [[]]
    for token in walk.box_tokens(box):
        if token == ",":
            segments.append([])
            continue
        if token.endswith(",") and not token.endswith("\\,"):
            segments[-1].append(token[:-1])
            segments.append([])
            continue
        segments[-1].append(token)
    selectors = [seg[0] for seg in segments if seg and seg[0]]
    if not selectors:
        return False
    for sel in selectors:
        if _is_number(sel) or sel.startswith(("$", ";")):
            return False
        if sel in _JIT_OUTPUT_SELECTORS or sel.startswith("get"):
            return False
    return True


def _is_jitter_setter_hop(src_box, dst_box) -> bool:
    """True when a cord from *src_box* into *dst_box* ends a reconvergence path.

    A setter message (``exprfill 0 snorm[0]``, ``dim $1 $1``,
    ``scale $1 $1 $1``) into a ``jit.*`` object is an attribute or method
    call that emits nothing: the object needs a separate ``bang`` to
    output. Evidence: the user-confirmed terrain-synth, whose
    ``[p terrain-view-a]`` / ``[p terrain-source]`` fan-outs reach
    jit.pack / jit.xfade only through such messages (Q20). A message
    containing ``bang`` still propagates.
    """
    return walk.box_name(dst_box).startswith("jit.") and _is_setter_message(src_box)


def _paths_reconverge(
    src_id: str,
    branches: list[tuple[str, int]],
    ctrl_adj: dict[str, list[tuple[str, int]]],
    box_lookup: dict[str, dict],
) -> str | None:
    """Return the id of a box where two branches meet at different inlets.

    Each branch ``(dst_id, inlet)`` is walked breadth-first over control
    cords, recording every inlet reached on every box. Two branches
    reconverge when some box outside ``_ALL_HOT_NAMES`` is reached by both
    at different inlets (the stale-cold-value hazard). Returns the first
    such box in sorted id order, or None.

    A Jitter setter hop (:func:`_is_jitter_setter_hop`), including the
    first hop from the fan-out source, records the hit at the jit.* box
    but does not expand past it (Q20).
    """
    src_box = box_lookup.get(src_id)
    hit_maps: list[dict[str, set[int]]] = []
    for dst_id, dst_inlet in branches:
        hits: dict[str, set[int]] = defaultdict(set)
        hits[dst_id].add(dst_inlet)
        seen = {dst_id}
        queue = deque()
        if not _is_jitter_setter_hop(src_box, box_lookup.get(dst_id)):
            queue.append(dst_id)
        while queue:
            node = queue.popleft()
            node_box = box_lookup.get(node)
            for nxt, nxt_inlet in ctrl_adj.get(node, ()):
                hits[nxt].add(nxt_inlet)
                if _is_jitter_setter_hop(node_box, box_lookup.get(nxt)):
                    continue
                if nxt not in seen and nxt != src_id:
                    seen.add(nxt)
                    queue.append(nxt)
        hit_maps.append(hits)

    meeting: set[str] = set()
    for k in range(len(hit_maps)):
        for l in range(k + 1, len(hit_maps)):
            hits_k, hits_l = hit_maps[k], hit_maps[l]
            for box_id in hits_k.keys() & hits_l.keys():
                box = box_lookup.get(box_id)
                if box is not None and walk.box_name(box) in _ALL_HOT_NAMES:
                    continue
                if any(a != b for a in hits_k[box_id] for b in hits_l[box_id]):
                    meeting.add(box_id)
    return min(meeting) if meeting else None


def _check_fan_out_without_trigger(
    box_lookup: dict[str, dict],
    edges: list,
) -> list[CriticResult]:
    """Detect control outlets connected to 2+ destinations without trigger.

    Per CLAUDE.md Rule #4: "Use explicit trigger objects for fan-out
    instead of connecting one outlet to multiple inlets."

    Skips (Q3 / E1, quick 261012-di7):
      - Signal outlets, decided by ``outlettype`` (``signal`` /
        ``multichannelsignal``); the ``~`` name is only a fallback when the
        box has no outlettype entry for that outlet. Rule #3: all signal
        inlets are hot, ordering does not apply in the audio domain.
      - ``preset`` outlets 0/2/4: include/exclude/capture membership cords
        (preset.maxref.xml), where a trigger cannot be inserted.
      - Display-only destinations (``_DISPLAY_SINK_NAMES`` with no outgoing
        cord) are dropped before counting; fewer than 2 left -> no finding.

    Trigger sources are checked like any other box: a trigger outlet that
    itself feeds 2+ destinations has undefined order between those cords.

    Severity: BLOCKER only when two branches reconverge on one box at
    different inlets (outside ``_ALL_HOT_NAMES``) -- then execution order
    changes the result. Otherwise WARNING. (History: promoted to an
    unconditional blocker by 260427-hox §P0-1; narrowed by Q3 because most
    of those blockers were false positives.)
    """
    results: list[CriticResult] = []

    # Outgoing-cord sources (for display-sink detection) and control-cord
    # adjacency (for reconvergence) are built from the same line pass.
    has_outgoing: set[str] = set()
    ctrl_adj: dict[str, list[tuple[str, int]]] = defaultdict(list)
    fan_out: dict[tuple[str, int], list[tuple[str, int]]] = defaultdict(list)

    for edge in edges:
        has_outgoing.add(edge.src)
        fan_out[(edge.src, edge.outlet)].append((edge.dst, edge.inlet))
        if not edge.signal:
            ctrl_adj[edge.src].append((edge.dst, edge.inlet))

    for (src_id, src_outlet), dests in fan_out.items():
        if len(dests) < 2:
            continue

        src_box = box_lookup.get(src_id)
        if not src_box:
            continue

        # Signal outlets: all signal inlets are hot per Rule #3
        if _outlet_is_signal(src_box, src_outlet):
            continue

        src_name = walk.box_name(src_box)

        # preset include/exclude/capture membership cords
        if src_name == "preset" and src_outlet in _PRESET_MEMBERSHIP_OUTLETS:
            continue

        # Drop display-only sinks (no outgoing cord of their own)
        branches = []
        for dst_id, dst_inlet in dests:
            dst_box = box_lookup.get(dst_id)
            if (
                dst_box is not None
                and walk.box_name(dst_box) in _DISPLAY_SINK_NAMES
                and dst_id not in has_outgoing
            ):
                continue
            branches.append((dst_id, dst_inlet))
        if len(branches) < 2:
            continue

        dst_names = []
        for dst_id, _inlet in branches:
            dst_box = box_lookup.get(dst_id)
            if dst_box:
                dst_names.append(f"'{walk.box_name(dst_box)}' ({dst_id})")
            else:
                dst_names.append(dst_id)

        prefix = (
            f"Fan-out without trigger: '{src_name}' ({src_id}) outlet "
            f"{src_outlet} connected to {len(branches)} destinations "
            f"({', '.join(dst_names)}) --"
        )
        meet_id = _paths_reconverge(src_id, branches, ctrl_adj, box_lookup)
        if meet_id is not None:
            meet_box = box_lookup.get(meet_id)
            meet_name = walk.box_name(meet_box) if meet_box else meet_id
            severity = "blocker"
            finding = (
                f"{prefix} paths reconverge on '{meet_name}' ({meet_id}) at "
                f"different inlets, so execution order changes the result"
            )
        else:
            severity = "warning"
            finding = f"{prefix} execution order is undefined"

        results.append(CriticResult(
            severity,
            finding,
            "Use a 'trigger' (t) object to explicitly control the order "
            "of execution for multiple destinations",
        ))

    return results


# ---------------------------------------------------------------------------
# Check 2: Hot/cold inlet ordering
# ---------------------------------------------------------------------------

def _check_hot_cold_ordering(
    box_lookup: dict[str, dict],
    edges: list,
) -> list[CriticResult]:
    """Detect hot/cold inlet ordering issues.

    When multiple separate sources feed different inlets of the same
    destination box, and neither source comes from a trigger object that
    controls ordering, the computation may use stale values.

    Per CLAUDE.md Rule #3: "Send to cold inlets FIRST (right to left),
    send to hot inlet LAST (leftmost, inlet 0) -- this triggers computation."

    Skip signal (~) connections -- all signal inlets are hot in the audio
    domain (Rule #3).
    """
    results: list[CriticResult] = []

    # Group connections by destination box
    # dst_id -> {inlet_idx -> list of (src_id, src_outlet)}
    dst_inlets: dict[str, dict[int, list[tuple[str, int]]]] = defaultdict(
        lambda: defaultdict(list)
    )

    for edge in edges:
        dst_inlets[edge.dst][edge.inlet].append((edge.src, edge.outlet))

    for dst_id, inlets_map in dst_inlets.items():
        dst_box = box_lookup.get(dst_id)
        if not dst_box:
            continue

        # Skip signal objects -- all inlets hot in audio domain
        if _is_signal_object(dst_box):
            continue

        # Only flag if multiple inlets are being fed (hot + cold)
        if len(inlets_map) < 2:
            continue

        # Check if inlet 0 (hot) is present
        if 0 not in inlets_map:
            continue

        # Get all source box IDs feeding this destination
        all_source_ids: set[str] = set()
        for inlet_sources in inlets_map.values():
            for src_id, _ in inlet_sources:
                all_source_ids.add(src_id)

        # Check if sources feeding hot inlet come from a trigger
        hot_sources = inlets_map[0]
        cold_inlet_indices = [idx for idx in inlets_map if idx > 0]

        # If a trigger feeds the hot inlet AND also feeds the cold inlets
        # (through different outlets), ordering is explicit -- no warning
        hot_from_trigger = False
        for src_id, _ in hot_sources:
            src_box = box_lookup.get(src_id)
            if src_box and _is_trigger_object(src_box):
                hot_from_trigger = True
                break

        if hot_from_trigger:
            continue

        # Multiple separate sources feeding hot and cold inlets
        # without trigger-based ordering
        dst_name = walk.box_name(dst_box)
        cold_desc = ", ".join(str(idx) for idx in sorted(cold_inlet_indices))

        results.append(CriticResult(
            "warning",
            f"Hot/cold inlet ordering issue: '{dst_name}' ({dst_id}) "
            f"receives data on inlet 0 (hot) and inlet(s) {cold_desc} "
            f"(cold) from separate sources without trigger ordering -- "
            f"cold inlets may contain stale values when hot inlet triggers",
            f"Use a 'trigger' (t) object to ensure cold inlets are "
            f"updated before hot inlet fires",
        ))

    return results


# ---------------------------------------------------------------------------
# Q21 / R4 helpers: trigger letters and outlet atom counts
# ---------------------------------------------------------------------------

# trigger.maxref.xml lists only these type letters; any other symbol argument
# is output as a constant.
_TRIGGER_TYPE_LETTERS = frozenset("bifls")

# Trigger letters that pass the incoming value on (not a bang or a constant).
_TRIGGER_VALUE_LETTERS = frozenset("ifls")

_DOLLAR_RE = re.compile(r"(?<!\\)\$([1-9])")


def _box_label(box) -> str:
    """The box text when it has one (``'t l f f'``), else its name (``'button'``)."""
    return walk.box_text(box) or walk.box_name(box)


def _trigger_letters(box) -> list[str]:
    """The type arguments of a trigger box: the tokens after the name up to
    the first ``@`` attribute, or ``["i", "i"]`` when there are none (an
    argument-less ``t`` acts as ``t i i``)."""
    letters: list[str] = []
    for token in walk.box_args(box):
        if token.startswith("@"):
            break
        letters.append(token)
    return letters or ["i", "i"]


def _trigger_letter_atoms(token: str) -> "int | None":
    """Atoms a trigger outlet of type *token* emits (planner decision 6a)."""
    if not token or token[0] in "#$":
        return None
    if token == "b":
        return 0
    if token == "l":
        return None
    if token in ("i", "f", "s"):
        return 1
    if len(token) == 1 and token.isalpha() and token.isupper():
        # Upper-case letters: Max behaviour undocumented -> unknown
        return None
    # A number or another symbol is output as one constant atom
    return 1


def _db_entry(entries, index: int):
    """The DB inlet/outlet entry with ``id == index`` (else list position)."""
    if not isinstance(entries, list):
        return None
    for entry in entries:
        if isinstance(entry, dict) and entry.get("id") == index:
            return entry
    if 0 <= index < len(entries) and isinstance(entries[index], dict):
        return entries[index]
    return None


def _outlet_atoms(box, outlet, dbh) -> "int | None":
    """Atom count *box* outlet *outlet* emits, or None when unknown.

    Precedence (Q21, planner decision 6):
      a. a trigger/t outlet takes its type letter (:func:`_trigger_letters`);
         an outlet past the argument count is unknown;
      b. otherwise, for a DB object that is not ``variable_io``, the DB
         outlet: ``type`` bang or ``signal_role`` trigger = 0; ``type``
         int/float/symbol or ``signal_role`` float = 1;
      c. otherwise the box's MAX-saved ``outlettype`` at that index:
         ``bang`` = 0, ``int`` / ``float`` = 1.
    Anything else is unknown.
    """
    if not isinstance(box, dict) or not isinstance(outlet, int) or isinstance(outlet, bool):
        return None
    if outlet < 0:
        return None
    name = walk.box_name(box)
    if name in _TRIGGER_NAMES:
        letters = _trigger_letters(box)
        if outlet >= len(letters):
            return None
        return _trigger_letter_atoms(letters[outlet])

    obj = dbh.lookup(name)
    if obj is not None and not obj.get("variable_io"):
        entry = _db_entry(obj.get("outlets"), outlet)
        if entry is not None:
            otype = entry.get("type")
            role = entry.get("signal_role")
            if otype == "bang" or role == "trigger":
                return 0
            if otype in ("int", "float", "symbol") or role == "float":
                return 1

    outlettype = box.get("outlettype")
    if isinstance(outlettype, list) and outlet < len(outlettype):
        saved = outlettype[outlet]
        if saved == "bang":
            return 0
        if saved in ("int", "float"):
            return 1
    return None


# ---------------------------------------------------------------------------
# Check 3: Invalid trigger types (Q21 / R4)
# ---------------------------------------------------------------------------

def _check_trigger_types(scope) -> list[CriticResult]:
    """Flag single lower-case letters a trigger does not know (Q21 / R4).

    trigger.maxref.xml lists only b, i, f, l and s; every other symbol is
    output as a constant, so ``t a`` (meant as "anything") outputs the
    literal symbol ``a``. Planner decision 8: flag any single lower-case
    ASCII letter outside b/i/f/l/s (covers ``a``, PD's ``p`` and typos);
    skip upper case (undocumented), ``@`` / ``#`` / ``$`` tokens and
    multi-character constants. One blocker per distinct token per box.
    """
    results: list[CriticResult] = []
    for box_id, box in scope.boxes.items():
        if walk.box_maxclass(box) != "newobj" or walk.box_name(box) not in _TRIGGER_NAMES:
            continue
        seen: set[str] = set()
        for tok in walk.box_args(box):
            if tok.startswith("@"):
                break
            if (
                len(tok) == 1
                and "a" <= tok <= "z"
                and tok not in _TRIGGER_TYPE_LETTERS
                and tok not in seen
            ):
                seen.add(tok)
                results.append(CriticResult(
                    "blocker",
                    f"Invalid trigger type: '{walk.box_text(box)}' ({box_id}) "
                    f"argument '{tok}' is not a trigger type (b, i, f, l, s) "
                    f"-- it outputs the literal symbol '{tok}'",
                    "Use b, i, f, l or s; any other symbol is output as a "
                    "constant. For an anything message where order does not "
                    "matter, fan out directly; where order matters use "
                    "'t l l' or 't s s'.",
                ))
    return results


# ---------------------------------------------------------------------------
# Check 4: Message $N arity (Q21 / R4)
# ---------------------------------------------------------------------------

def _check_dollar_arity(scope, dbh) -> list[CriticResult]:
    """Flag a message box whose highest ``$N`` its feeders can never fill.

    ``$N`` is ``(?<!\\\\)\\$([1-9])`` on the message text. The unit is the
    set of inlet-0 feeders (planner decision 7, assumption delta): Max
    stores ``$`` arguments and a bang resends them (message.maxref.xml), so
    a bang beside a value feeder is the resend idiom. A box is flagged only
    when nothing feeds inlet 1 (a ``set`` there replaces the text), at
    least one cord feeds inlet 0, every inlet-0 feeder's atom count is known
    (:func:`_outlet_atoms`, planner decision 6) and the largest is below
    the highest N.
    """
    results: list[CriticResult] = []
    for box_id, box in scope.boxes.items():
        if walk.box_maxclass(box) != "message":
            continue
        text = walk.box_text(box)
        if not text:
            continue
        ns = [int(m) for m in _DOLLAR_RE.findall(text)]
        if not ns:
            continue
        n = max(ns)
        in_edges = scope.in_edges.get(box_id, ())
        if any(e.inlet == 1 for e in in_edges):
            continue
        feeders = [e for e in in_edges if e.inlet == 0]
        if not feeders:
            continue
        counts = []
        for e in feeders:
            src = scope.boxes.get(e.src)
            k = _outlet_atoms(src, e.outlet, dbh) if src is not None else None
            if k is None:
                counts = None
                break
            counts.append(k)
        if counts is None:
            continue
        k = max(counts)
        if k >= n:
            continue
        feeder_desc = ", ".join(
            f"'{_box_label(scope.boxes.get(e.src))}' ({e.src}) outlet {e.outlet}"
            for e in feeders
        )
        results.append(CriticResult(
            "blocker",
            f"Message $N arity: '{text}' ({box_id}) uses ${n} but its feeders "
            f"supply at most {k} atom(s): {feeder_desc} -- $ arguments above "
            f"{k} keep their stored value (0 until set)",
            f"Feed it from an outlet that carries all {n} values (a 't l' "
            f"outlet, pack or another list source), or lower the highest $N.",
        ))
    return results


# ---------------------------------------------------------------------------
# Check 5: Redundant/duplicate connections
# ---------------------------------------------------------------------------

def _check_redundant_connections(
    edges: list,
) -> list[CriticResult]:
    """Detect duplicate patchlines (same source -> same destination)."""
    results: list[CriticResult] = []

    seen: set[tuple[str, int, str, int]] = set()

    for edge in edges:
        key = (edge.src, edge.outlet, edge.dst, edge.inlet)

        if key in seen:
            results.append(CriticResult(
                "warning",
                f"Duplicate patchline: {edge.src} outlet {edge.outlet} -> "
                f"{edge.dst} inlet {edge.inlet} appears multiple times",
                "Remove the duplicate connection",
            ))
        else:
            seen.add(key)

    return results
