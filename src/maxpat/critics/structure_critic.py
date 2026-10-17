"""Structure critic -- checks patch architecture and connection patterns.

Catches structural issues that the mechanical validation pipeline does
not detect:
  - Fan-out without trigger (ordering ambiguity): blocker when branches
    reconverge on one box at different inlets, otherwise warning (Q3 / E1)
  - Hot/cold inlet ordering (Q26 / E5): one upstream event reaching a box's
    hot inlet 0 and a DB-cold inlet, with the cold update fired at or after
    the last hot firing (right-to-left outlet order at the divergence box).
    Independent sources, p / bpatcher / js and storage targets, exclusive
    routers and the targets Q21's trigger-order check owns are not reported.
  - Invalid trigger types (Q21 / R4): ``t a`` and any other single
    lower-case letter outside b, i, f, l, s outputs the literal symbol
  - ``$N`` arity (Q21 / R4): a message box's highest ``$N`` above the
    atoms its inlet-0 feeders can together supply
  - Trigger order (Q21 / R4): one trigger feeding a box's hot inlet 0 from
    a higher outlet than a cold inlet (directly or through one hop).
    Task 2 decision ``idiom-exempt``: Max's previous-value / delta idioms
    (storage targets, same-value direct feeds, waveform~) are not reported.
  - Redundant/duplicate patchlines
  - Uninitialized state (Q24 / R8, review §4.1 class 4 "Load-time init"):
    a UI value holder (D-01) whose control output reaches DSP (D-03,
    :meth:`PatchGraph.control_walk`) with nothing that sets it at load --
    no parameter initial value, loadmess / loadbang / live.thisdevice path,
    pattr / pattrstorage restore (D-02) or slaved gain~ input. A warning on
    an edit, a blocker for a new patch (``is_new``; the save gate sets it
    for a file with no baseline).

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
from src.maxpat.critics.base import CriticResult, finding_ids, tag_results
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
    is_new: bool = False,
) -> list[CriticResult]:
    """Review structural aspects of a patch, every scope (Q20).

    Checks, per scope of the shared graph:
      1. Fan-out without trigger (2+ non-display destinations from one
         control outlet; blocker only on reconvergence -- Q3 / E1)
      2. Hot/cold inlet ordering (warning; Q26 / E5, PD-1..PD-3): one
         upstream event updates a cold inlet at or after the hot inlet 0
         fires. Targets a trigger reaches at inlet 0 and a cold inlet
         (directly or through one hop) are left to check 5, which runs
         first; results keep the order below.
      3. Invalid trigger types (blocker; Q21 / R4)
      4. Message ``$N`` arity (blocker; Q21 / R4)
      5. Trigger order: one trigger feeding a hot inlet after a cold one
         (blocker; Q21 / R4; previous-value idioms exempt)
      6. Redundant/duplicate patchlines
      7. Uninitialized state (Q24 / R8): a UI value holder (D-01) whose
         control output reaches DSP (D-03) with nothing that sets it at
         load (parameter initial value, loadmess / loadbang path, pattr /
         pattrstorage restore -- D-02 -- or a slaved gain~ input). A
         warning, or a blocker when *is_new*. Not run in rnbo scopes.

    Gen scopes run only check 6. Top-level results come first, nested
    scopes follow in pre-order, tagged with their path.

    Args:
        patch_dict: A .maxpat-format dict.
        graph: The shared PatchGraph of *patch_dict* (review_patch passes
            it); built here when None.
        db: Keyword-only ObjectDatabase for the Q21 checks (inlet ``hot``
            flags, outlet types) and the Q24 DSP / slaved-gain tests.
            review_patch passes its own; when None, one is built here, at
            most once per call and only when a check needs it.
        is_new: Keyword-only. True for a new patch (the save gate sets it
            for a file with no baseline): a Q24 uninitialized-state finding
            is then a blocker. False (default, every edit) keeps it a
            warning. No other check reads it.

    Returns:
        List of CriticResult findings.
    """
    if graph is None:
        graph = PatchGraph.build(patch_dict)
    dbh = _LazyDB(db)
    ctx = _InitContext(graph)
    results: list[CriticResult] = []
    for scope in graph.scopes:
        found: list[CriticResult] = []
        if scope.context != "gen":
            trigger_order = _check_trigger_order(scope, dbh)
            found.extend(_check_fan_out_without_trigger(scope.boxes, scope.edges))
            found.extend(_check_hot_cold_ordering(scope, dbh, _q21_targets(scope, dbh)))
            found.extend(_check_trigger_types(scope))
            found.extend(_check_dollar_arity(scope, dbh))
            found.extend(trigger_order)
            found.extend(_check_uninitialized_state(graph, scope, dbh, is_new, ctx))
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
            rule="fan_out_without_trigger",
            box_ids=finding_ids(src_id, *(d for d, _ in branches), meet_id),
            port=src_outlet,
        ))

    return results


# ---------------------------------------------------------------------------
# Check 2: Hot/cold inlet ordering
# ---------------------------------------------------------------------------

# Divergence boxes that send each event out of exactly one outlet (planner
# decision PD-1, Q26 / E5): a hot and a cold path leaving different outlets
# of one of these never carry the same event (terrain-source
# ``route backup restore``).
_EXCLUSIVE_ROUTER_NAMES = frozenset({
    "route", "routepass", "select", "sel", "gate", "ggate", "gswitch2",
    "split", "spray", "if",
})

_HOT_COLD_SUGGESTION = (
    "Feed both from one 'trigger' (t) with the hot inlet on its lowest "
    "outlet: trigger outlets fire right to left, so the cold inlets are set first."
)


def _hot_cold_upstream(scope, seeds, target_id, dbh) -> set:
    """Boxes whose control event can reach a seed (seeds included; Q26 / E5).

    Walks control in-cords upstream from *seeds*. A cord is followed only
    when it enters its box at a hot inlet (not :func:`_inlet_is_cold`), is
    not a Jitter setter hop (:func:`_is_jitter_setter_hop`) and does not
    leave the target itself. An event that enters a box at a cold inlet
    stops there (notein -> poly inlet 1 is not a shared ancestor).
    """
    seen = set(seeds)
    queue = deque(seeds)
    while queue:
        box_id = queue.popleft()
        box = scope.boxes.get(box_id)
        if box is None:
            continue
        for edge in scope.in_edges.get(box_id, ()):
            if edge.signal or edge.src == target_id or edge.src in seen:
                continue
            if _inlet_is_cold(box, edge.inlet, dbh):
                continue
            src_box = scope.boxes.get(edge.src)
            if src_box is None or _is_jitter_setter_hop(src_box, box):
                continue
            seen.add(edge.src)
            queue.append(edge.src)
    return seen


def _cord_reaches(scope, edge, target_id, side_cords, side_up, dbh) -> bool:
    """True when control cord *edge* carries its event to one side of the target.

    *side_cords* holds ``id()`` of the target's own cords on that side (Edge
    carries its line dict, so it is not hashable); *side_up* is that side's
    upstream set.
    """
    if id(edge) in side_cords:
        return True
    if edge.dst == target_id or edge.dst not in side_up:
        return False
    dst_box = scope.boxes.get(edge.dst)
    src_box = scope.boxes.get(edge.src)
    if dst_box is None or src_box is None:
        return False
    if _inlet_is_cold(dst_box, edge.inlet, dbh):
        return False
    return not _is_jitter_setter_hop(src_box, dst_box)


def _is_opaque_divergence(box, dbh) -> bool:
    """A box whose outlet order is not knowable here (PD-1): exclusive
    routers, all-hot containers, embedded patchers and DB-unknown names."""
    name = walk.box_name(box)
    if name in _EXCLUSIVE_ROUTER_NAMES or name in _ALL_HOT_NAMES:
        return True
    if walk.inner_patcher(box) is not None:
        return True
    return dbh.lookup(name) is None


def _is_hot_cold_target(box) -> bool:
    """False for the targets the hot/cold check never reports (PD-1)."""
    name = walk.box_name(box)
    if name in _ORDER_EXCLUDED_NAMES or walk.inner_patcher(box) is not None:
        return False
    if name in _ORDER_STORAGE_NAMES or _is_zl_reg(box) or name in _ORDER_IDIOM_TARGETS:
        return False
    return True


def _check_hot_cold_ordering(scope, dbh, q21_targets=frozenset()) -> list[CriticResult]:
    """Flag a box whose cold inlet is updated after its hot inlet by one event.

    Q26 / E5 (planner decisions PD-1 to PD-3). Per CLAUDE.md Rule #3 cold
    inlets must be set before the hot inlet 0 fires. Two independent
    sources feeding hot and cold inlets are not a hazard (the review
    measured that shape as noise); one upstream event that reaches both is.

    * Targets: a box with control cords into inlet 0 and into at least one
      DB-cold inlet (:func:`_inlet_is_cold`), except the gate/switch family,
      pak, funnel, all-hot containers (p, bpatcher, js, poly~, ...), any box
      with an embedded patcher, the Q21 storage / idiom targets, and every
      target Q21 owns (*q21_targets*, PD-2). Signal cords never count.
    * Upstream sets: for the hot cords and the cold cords separately,
      :func:`_hot_cold_upstream` from the cord sources. No shared box: no
      finding.
    * Divergence: each shared ancestor in sorted id order, skipping
      exclusive routers and opaque boxes (:func:`_is_opaque_divergence`).
      Its control out-cords are classified as reaching hot only (H), cold
      only (C) or both (B). Outlets fire right to left, so a hazard is
      C non-empty, H or B non-empty and min(C) <= min(H | B): a cold update
      at a lower outlet arrives after the last hot firing, and an equal
      outlet is a fan-out in undefined order (PD-3). B-only shapes are not
      hazards: each B wave sets its own cold inlets first.
    * One warning per target, from the first hazardous ancestor.
    """
    results: list[CriticResult] = []
    for dst_id, dst_box in scope.boxes.items():
        in_edges = [e for e in scope.in_edges.get(dst_id, ()) if not e.signal]
        if not in_edges:
            continue
        hot_cords = [e for e in in_edges if e.inlet == 0]
        if not hot_cords or all(e.inlet == 0 for e in in_edges):
            continue
        if dst_id in q21_targets or not _is_hot_cold_target(dst_box):
            continue
        cold_by_inlet: dict = defaultdict(list)
        for e in in_edges:
            if isinstance(e.inlet, int) and e.inlet > 0 and _inlet_is_cold(dst_box, e.inlet, dbh):
                cold_by_inlet[e.inlet].append(e)
        if not cold_by_inlet:
            continue
        cold_cords = [e for i in sorted(cold_by_inlet) for e in cold_by_inlet[i]]
        hot_up = _hot_cold_upstream(scope, [e.src for e in hot_cords], dst_id, dbh)
        cold_up_by_inlet = {
            i: _hot_cold_upstream(scope, [e.src for e in es], dst_id, dbh)
            for i, es in cold_by_inlet.items()
        }
        cold_up = set().union(*cold_up_by_inlet.values())
        shared = hot_up & cold_up
        if not shared:
            continue
        hot_set = {id(e) for e in hot_cords}
        cold_set = {id(e) for e in cold_cords}
        for anc in sorted(shared, key=str):
            anc_box = scope.boxes.get(anc)
            if anc_box is None or _is_opaque_divergence(anc_box, dbh):
                continue
            h_out: set = set()
            c_out: set = set()
            b_out: set = set()
            for edge in scope.out_edges.get(anc, ()):
                if edge.signal or not isinstance(edge.outlet, int):
                    continue
                to_hot = _cord_reaches(scope, edge, dst_id, hot_set, hot_up, dbh)
                to_cold = _cord_reaches(scope, edge, dst_id, cold_set, cold_up, dbh)
                if to_hot and to_cold:
                    b_out.add(edge.outlet)
                elif to_hot:
                    h_out.add(edge.outlet)
                elif to_cold:
                    c_out.add(edge.outlet)
            if not c_out or not (h_out or b_out):
                continue
            c = min(c_out)
            h = min(h_out | b_out)
            if c > h:
                continue
            name = walk.box_name(dst_box)
            cold_desc = ", ".join(
                str(i) for i in sorted(cold_up_by_inlet) if anc in cold_up_by_inlet[i]
            )
            label = _box_label(anc_box)
            if c < h:
                finding = (
                    f"Hot/cold inlet ordering issue: '{name}' ({dst_id}) gets hot inlet 0 "
                    f"and cold inlet(s) {cold_desc} from one event at '{label}' ({anc}), "
                    f"but outlet {c} (cold) fires after outlet {h} (hot) -- '{name}' "
                    f"outputs with a stale cold value"
                )
            else:
                finding = (
                    f"Hot/cold inlet ordering issue: '{name}' ({dst_id}) gets hot inlet 0 "
                    f"and cold inlet(s) {cold_desc} from one event at '{label}' ({anc}) "
                    f"outlet {c}, which fans out to both in undefined order -- '{name}' "
                    f"may output with a stale cold value"
                )
            results.append(CriticResult(
                "warning", finding, _HOT_COLD_SUGGESTION,
                rule="hot_cold_ordering",
                box_ids=finding_ids(dst_id, anc),
            ))
            break
    return results


def _q21_targets(scope, dbh) -> set:
    """Targets a trigger reaches (directly or through one Q21 hop) at inlet 0
    and at a DB-cold inlet: the trigger-order check owns them (PD-2)."""
    owned: set = set()
    for t_id, t_box in scope.boxes.items():
        if walk.box_name(t_box) not in _TRIGGER_NAMES:
            continue
        for dst_id, inlets in _trigger_reach(scope, t_id).items():
            dst_box = scope.boxes.get(dst_id)
            if dst_box is None or 0 not in inlets:
                continue
            if any(isinstance(i, int) and i > 0 and _inlet_is_cold(dst_box, i, dbh) for i in inlets):
                owned.add(dst_id)
    return owned


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
                    rule="trigger_types",
                    box_ids=finding_ids(box_id),
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
            rule="dollar_arity",
            box_ids=finding_ids(box_id, *(e.src for e in feeders)),
        ))
    return results


# ---------------------------------------------------------------------------
# Check 5: Trigger order (Q21 / R4)
# ---------------------------------------------------------------------------

# Targets never checked (planner decision 4): gate/switch and their graphic
# siblings take a control inlet first; pak and funnel are all-hot in Max
# (the DB marks their inlet 1 cold -- an overrides follow-up); and
# _ALL_HOT_NAMES boxes route each inlet independently.
_ORDER_EXCLUDED_NAMES = frozenset({
    "gate", "switch", "ggate", "gswitch", "gswitch2", "pak", "funnel",
}) | _ALL_HOT_NAMES

# One-hop relays (planner decision 5): entered at inlet 0, they pass on
# through outlet 0. ``zl`` counts only as ``zl reg``.
_ORDER_HOP_NAMES = frozenset({"zl.reg", "f", "float", "i", "int", "prepend"})

# Task 2 decision ``idiom-exempt``: storage targets output the previous
# value on purpose (``t i b`` -> ``i``, fibonacci ``t b b`` -> ``int``) ...
_ORDER_STORAGE_NAMES = frozenset({"i", "int", "f", "float", "zl.reg"})
# ... and waveform~ (BEAP's UI cases).
_ORDER_IDIOM_TARGETS = frozenset({"waveform~"})


def _is_zl_reg(box) -> bool:
    if walk.box_name(box) == "zl.reg":
        return True
    args = walk.box_args(box)
    return walk.box_name(box) == "zl" and bool(args) and args[0] == "reg"


def _is_order_hop(box) -> bool:
    if walk.box_maxclass(box) == "message":
        return True
    return walk.box_name(box) in _ORDER_HOP_NAMES or _is_zl_reg(box)


def _inlet_is_cold(box, inlet: int, dbh) -> bool:
    """True when the DB marks *box* inlet *inlet* (> 0) ``hot: false``.

    Planner decision 3: unknown objects have no cold inlets. For a
    ``variable_io`` object an inlet past the DB list takes the last listed
    inlet's flag when 2+ inlets are listed (pack), and is cold when only
    inlet 0 is listed (expr, vexpr, if, sprintf).
    """
    if inlet <= 0:
        return False
    obj = dbh.lookup(walk.box_name(box))
    if obj is None:
        return False
    inlets = obj.get("inlets")
    if not isinstance(inlets, list):
        return False
    entry = _db_entry(inlets, inlet) if inlet < len(inlets) else None
    if entry is not None:
        return entry.get("hot") is False
    if not obj.get("variable_io"):
        return False
    if len(inlets) >= 2:
        last = inlets[-1]
        return isinstance(last, dict) and last.get("hot") is False
    return len(inlets) == 1


def _is_order_idiom(dst_box, letters, hot, cold) -> bool:
    """The previous-value / delta idiom shapes exempted by the Task 2
    decision ``idiom-exempt``: a storage target (whatever the feed), a
    waveform~ target, or a target whose hot and cold inlets are all fed
    directly by value outlets (i/f/l/s) of the trigger -- the "correct"
    order would compute x op x there."""
    name = walk.box_name(dst_box)
    if name in _ORDER_STORAGE_NAMES or _is_zl_reg(dst_box):
        return True
    if name in _ORDER_IDIOM_TARGETS:
        return True
    feeds = list(hot) + list(cold)
    return bool(feeds) and all(
        how == "direct"
        and outlet < len(letters)
        and letters[outlet] in _TRIGGER_VALUE_LETTERS
        for outlet, how in feeds
    )


def _trigger_reach(scope, t_id) -> dict:
    """``dst_id -> inlet -> {(outlet, "direct" | "hop")}`` for trigger *t_id*.

    Every (box, inlet) the trigger reaches directly or through one hop
    (planner decision 5: :func:`_is_order_hop`, entered at inlet 0 and left
    by outlet 0); cords back into the trigger are ignored. Shared by
    :func:`_check_trigger_order` and the hot/cold skip set (Q26 PD-2).
    """
    reach: dict = defaultdict(lambda: defaultdict(set))
    for edge in scope.out_edges.get(t_id, ()):
        if edge.dst == t_id:
            continue
        reach[edge.dst][edge.inlet].add((edge.outlet, "direct"))
        hop_box = scope.boxes.get(edge.dst)
        if edge.inlet != 0 or hop_box is None or not _is_order_hop(hop_box):
            continue
        for nxt in scope.out_edges.get(edge.dst, ()):
            if nxt.outlet != 0 or nxt.dst == t_id:
                continue
            reach[nxt.dst][nxt.inlet].add((edge.outlet, "hop"))
    return reach


def _check_trigger_order(scope, dbh) -> list[CriticResult]:
    """Flag a trigger that feeds a box's hot inlet before its cold inlets.

    Trigger outlets fire right to left, so the hot inlet 0 must be fed by
    the lowest outlet index (Rule #3; Q21 / R4). For each trigger, every
    (box, inlet) it reaches directly or through one hop (planner decision
    5: a message box, ``zl.reg`` / ``zl reg``, f/float, i/int or prepend,
    entered at inlet 0 and left by outlet 0) is collected. A target that is
    the trigger itself, is in ``_ORDER_EXCLUDED_NAMES`` (decision 4) or is
    not reached at inlet 0 is skipped. Cold inlets follow
    :func:`_inlet_is_cold` (decision 3). One blocker per (trigger, target)
    when min(hot outlets) > min(cold outlets); one outlet feeding both is
    the fan-out critic's concern.

    Task 2 decision: ``idiom-exempt`` -- the previous-value / delta shapes
    of :func:`_is_order_idiom` are never reported.
    """
    results: list[CriticResult] = []
    for t_id, t_box in scope.boxes.items():
        if walk.box_name(t_box) not in _TRIGGER_NAMES:
            continue
        letters = _trigger_letters(t_box)
        reach = _trigger_reach(scope, t_id)

        for dst_id, inlets in reach.items():
            dst_box = scope.boxes.get(dst_id)
            if dst_box is None or 0 not in inlets:
                continue
            d_name = walk.box_name(dst_box)
            if d_name in _ORDER_EXCLUDED_NAMES:
                continue
            hot = inlets[0]
            cold_inlets = sorted(
                i for i in inlets if i > 0 and _inlet_is_cold(dst_box, i, dbh)
            )
            if not cold_inlets:
                continue
            cold = set()
            for i in cold_inlets:
                cold |= inlets[i]
            h = min(o for o, _ in hot)
            if h <= min(o for o, _ in cold):
                continue
            if _is_order_idiom(dst_box, letters, hot, cold):
                continue
            ci = ", ".join(str(i) for i in cold_inlets)
            co = ", ".join(str(o) for o in sorted({o for o, _ in cold}))
            results.append(CriticResult(
                "blocker",
                f"Trigger order: '{walk.box_text(t_box)}' ({t_id}) feeds the hot "
                f"inlet 0 of '{d_name}' ({dst_id}) from outlet {h} but cold "
                f"inlet(s) {ci} from outlet(s) {co} -- trigger outlets fire "
                f"right to left, so outlet {h} fires first and '{d_name}' "
                f"outputs with stale cold values",
                "Reorder the trigger so the hot inlet is fed by the lowest "
                "outlet index (outlet 0 fires last), e.g. 't l b' -> 't b l'.",
                rule="trigger_order",
                box_ids=finding_ids(t_id, dst_id),
            ))
    return results


# ---------------------------------------------------------------------------
# Check 6: Redundant/duplicate connections
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
                rule="redundant_connections",
                box_ids=finding_ids(edge.src, edge.dst),
            ))
        else:
            seen.add(key)

    return results


# ---------------------------------------------------------------------------
# Check 7: Uninitialized state (Q24 / R8)
# ---------------------------------------------------------------------------

# Gain stages: value holders that are DSP themselves, so they always reach
# DSP (planner decision 4) and get the gain-stage finding text.
_GAIN_STAGES = frozenset({"gain~", "live.gain~"})

# D-01: the other value holders, by maxclass. Every class not listed here
# or in _GAIN_STAGES (button, kslider, multislider, textedit, nodes,
# matrixctrl, mc.live.gain~, ...) is never reported.
_VALUE_HOLDERS = frozenset({
    "slider", "dial", "number", "flonum", "live.dial", "live.slider",
    "live.numbox", "toggle", "live.toggle", "umenu", "live.menu", "tab",
    "live.tab", "radiogroup",
})

_ALL_VALUE_HOLDERS = _VALUE_HOLDERS | _GAIN_STAGES

# D-03: DSP targets by name (the walk stops at the first DSP box).
_DSP_NAMES = frozenset({
    "gen~", "mc.gen~", "rnbo~", "poly~", "mc.poly~", "*~", "mc.*~",
    "gain~", "live.gain~",
})

# Planner decision 4: the audio switches are never DSP targets. Their
# control input is the global audio on/off, off at load like an unset
# toggle (adc~ stays a target: a channel number is real state).
_AUDIO_SWITCHES = frozenset({"dac~", "ezdac~", "mc.dac~", "ezadc~"})

# Sources that fire at load (planner decision 3).
_LOAD_SOURCES = frozenset({"loadbang", "loadmess", "live.thisdevice"})

_UNINIT_ROUTES = (
    "(no parameter initial value, loadmess/loadbang path, "
    "pattr/pattrstorage restore or slaved gain~ input)"
)

_UNINIT_SUGGESTION = (
    "Initialize it at load: parameter_enable 1 with parameter_initial_enable 1 "
    "and a parameter_initial value, or loadmess <value> (or loadbang -> message) "
    "into it, or a pattr binding (or a varname under autopattr with a "
    "pattrstorage); a slave gain~ takes the master gain~'s right outlet into "
    "its left inlet."
)


def _attr_value(tokens: list, attr: str) -> "str | None":
    """The token after ``@attr`` in *tokens*, or None."""
    for index, token in enumerate(tokens):
        if token == attr:
            return tokens[index + 1] if index + 1 < len(tokens) else None
    return None


def _is_zero(token) -> bool:
    try:
        return float(token) == 0.0
    except (TypeError, ValueError):
        return False


class _InitContext:
    """Whole-graph facts for the Q24 check, computed lazily once per call.

    ``has_pattrstorage``: a ``pattrstorage`` box in any scope (D-02).
    ``bindto``: the ``pattr @bindto`` targets of every scope, whole and by
    last ``::`` segment (D-02). ``autopattrs(scope)``: the autopattr boxes
    of one scope.
    """

    __slots__ = ("graph", "_storage", "_bindto", "_autopattrs")

    def __init__(self, graph):
        self.graph = graph
        self._storage = None
        self._bindto = None
        self._autopattrs: dict = {}

    @property
    def has_pattrstorage(self) -> bool:
        if self._storage is None:
            self._storage = any(
                walk.box_name(box) == "pattrstorage"
                for scope in self.graph.scopes
                for box in scope.boxes.values()
            )
        return self._storage

    @property
    def bindto(self) -> frozenset:
        if self._bindto is None:
            names: set = set()
            for scope in self.graph.scopes:
                for box in scope.boxes.values():
                    if walk.box_name(box) != "pattr":
                        continue
                    target = _attr_value(walk.box_args(box), "@bindto")
                    if target:
                        names.add(target)
                        names.add(target.split("::")[-1])
            self._bindto = frozenset(names)
        return self._bindto

    def autopattrs(self, scope) -> list:
        key = id(scope)
        found = self._autopattrs.get(key)
        if found is None:
            found = [box for box in scope.boxes.values() if walk.box_name(box) == "autopattr"]
            self._autopattrs[key] = found
        return found


def _has_parameter_initial(box) -> bool:
    """``parameter_enable`` 1 plus ``saved_attribute_attributes.valueof``
    with ``parameter_initial_enable`` 1 and a ``parameter_initial`` key
    (planner decision 3: the proven plain-dial / add_m4l_gen_synth form)."""
    if box.get("parameter_enable") != 1:
        return False
    saved = box.get("saved_attribute_attributes")
    if not isinstance(saved, dict):
        return False
    valueof = saved.get("valueof")
    if not isinstance(valueof, dict):
        return False
    return valueof.get("parameter_initial_enable") == 1 and "parameter_initial" in valueof


def _db_outlet_is_signal(dbh, name, outlet) -> "bool | None":
    """The DB ``signal`` flag of *name*'s outlet *outlet*, or None when unknown."""
    entry = dbh.lookup(name)
    if entry is None:
        return None
    outlets = entry.get("outlets")
    port = _db_entry(outlets, outlet) if isinstance(outlets, list) else None
    if not isinstance(port, dict) or "signal" not in port:
        return None
    return port.get("signal") is True


def _is_slaved_gain(scope, box_id, dbh) -> bool:
    """A gain~ / live.gain~ fed at inlet 0 by another gain stage's outlet
    whose DB entry is not signal (gain~ outlet 1). Decided by the DB, not
    ``Edge.signal``: mixer-bus saves the master's outlettype as
    ``["signal", "signal"]`` (planner decision 3)."""
    for e in scope.in_edges.get(box_id, ()):
        if e.inlet != 0 or e.src == box_id:
            continue
        src = scope.boxes.get(e.src)
        if src is None or walk.box_maxclass(src) not in _GAIN_STAGES:
            continue
        if _db_outlet_is_signal(dbh, walk.box_maxclass(src), e.outlet) is False:
            return True
    return False


def _db_has_signal_port(dbh, name) -> bool:
    """True when the DB entry of *name* has a signal inlet or outlet."""
    entry = dbh.lookup(name)
    if entry is None:
        return False
    for key in ("inlets", "outlets"):
        ports = entry.get(key)
        for port in ports if isinstance(ports, list) else ():
            if isinstance(port, dict) and port.get("signal") is True:
                return True
    return False


def _is_dsp_box(box, dbh) -> bool:
    """D-03 / planner decision 4: a box that ends the reach walk.

    Never the audio switches (dac~, ezdac~, mc.dac~, ezadc~); then a DSP
    name (gen~, mc.gen~, rnbo~, poly~, mc.poly~, ``*~``, ``mc.*~``, gain~,
    live.gain~), a signal ``outlettype`` entry, or a DB signal inlet /
    outlet. Embedded p / bpatcher containers never get here (the walk
    crosses them); opaque boxes are judged by name, outlettype or DB.
    """
    if not isinstance(box, dict):
        return False
    name = walk.box_name(box)
    if name in _AUDIO_SWITCHES:
        return False
    if name in _DSP_NAMES:
        return True
    outlettype = box.get("outlettype")
    if isinstance(outlettype, list) and any(
        isinstance(t, str) and t in SIGNAL_OUTLET_TYPES for t in outlettype
    ):
        return True
    db_name = walk.object_name(box)
    return bool(db_name) and _db_has_signal_port(dbh, db_name)


def _first_dsp(graph, scope, box_id, dbh):
    """The first DSP ``(scope, box_id, box)`` the downstream control walk
    reaches (D-03), or None."""
    for s, b in graph.control_walk(scope, box_id, downstream=True):
        target = s.boxes.get(b)
        if _is_dsp_box(target, dbh):
            return s, b, target
    return None


def _is_pattr_bound(scope, box_id, box, ctx) -> bool:
    """D-02 per-control binding: a cord to or from a ``pattr``, a ``pattr
    @bindto`` naming the varname (whole or last ``::`` segment), or a
    varname in a patcher holding autopattr when a pattrstorage exists
    anywhere in the tree."""
    for e in scope.in_edges.get(box_id, ()):
        if walk.box_name(scope.boxes.get(e.src)) == "pattr":
            return True
    for e in scope.out_edges.get(box_id, ()):
        if walk.box_name(scope.boxes.get(e.dst)) == "pattr":
            return True
    varname = box.get("varname")
    if not isinstance(varname, str) or not varname:
        return False
    if varname in ctx.bindto:
        return True
    autopattrs = ctx.autopattrs(scope)
    if autopattrs and ctx.has_pattrstorage:
        return True
    return _autopattr_restores(autopattrs, varname)


def _autopattr_restores(autopattrs, varname) -> bool:
    """Planner decision 3: *varname* is a key of a same-patcher autopattr's
    ``restore`` dict and that autopattr does not carry ``@autorestore 0``
    (autopattr.maxref.xml: autorestore defaults to 1 and outputs the last
    saved values at load)."""
    for ap in autopattrs:
        restore = ap.get("restore")
        if not isinstance(restore, dict) or varname not in restore:
            continue
        if _is_zero(_attr_value(walk.box_args(ap), "@autorestore")):
            continue
        return True
    return False


def _upstream_initialized(graph, scope, box_id) -> bool:
    """One upstream control walk: True on a load source (loadbang,
    loadmess, live.thisdevice), or on a value holder outside the control's
    own downstream control set (a follower -- planner decision 3: that
    holder is initialized and drives this one at load, or is reported
    itself). The downstream set is computed lazily, once."""
    downstream_set = None
    for s, b in graph.control_walk(scope, box_id, downstream=False):
        upstream_box = s.boxes.get(b)
        if walk.box_name(upstream_box) in _LOAD_SOURCES:
            return True
        if walk.box_maxclass(upstream_box) not in _ALL_VALUE_HOLDERS:
            continue
        if downstream_set is None:
            downstream_set = {
                (id(ds), db_id)
                for ds, db_id in graph.control_walk(scope, box_id, downstream=True)
            }
        if (id(s), b) not in downstream_set:
            return True
    return False


def _is_initialized(graph, scope, box_id, box, dbh, ctx) -> bool:
    """True when something sets the control at load, cheapest route first:
    parameter initial value, D-02 pattr binding / autopattr restore,
    slaved gain~ (planner decision 3), then the upstream walk."""
    if _has_parameter_initial(box):
        return True
    if _is_pattr_bound(scope, box_id, box, ctx):
        return True
    if walk.box_maxclass(box) in _GAIN_STAGES and _is_slaved_gain(scope, box_id, dbh):
        return True
    return _upstream_initialized(graph, scope, box_id)


def _check_uninitialized_state(graph, scope, dbh, is_new, ctx) -> list[CriticResult]:
    """Q24 / R8: a value holder that reaches DSP must be set at load.

    D-01 value holders only (gain~ / live.gain~ always reach DSP, planner
    decision 4); the others when the downstream control walk reaches a DSP
    box (D-03). One finding per uninitialized control (never per DSP
    target): a blocker when *is_new* (a new patch), else a warning (planner
    decision 2). Not run in rnbo scopes. Read-only; malformed boxes never
    raise.
    """
    if scope.scope == "rnbo":
        return []
    severity = "blocker" if is_new else "warning"
    results: list[CriticResult] = []
    for box_id, box in scope.boxes.items():
        maxclass = walk.box_maxclass(box)
        if maxclass in _GAIN_STAGES:
            dsp = None
        elif maxclass in _VALUE_HOLDERS:
            dsp = _first_dsp(graph, scope, box_id, dbh)
            if dsp is None:
                continue
        else:
            continue
        if _is_initialized(graph, scope, box_id, box, dbh, ctx):
            continue
        label = _box_label(box)
        if dsp is None:
            finding = (
                f"Uninitialized state: '{label}' ({box_id}) is a gain stage that "
                f"nothing sets at load {_UNINIT_ROUTES} -- it loads at its default "
                "(a plain gain~ at 0, silent) until touched"
            )
        else:
            _dsp_scope, dsp_id, dsp_box = dsp
            finding = (
                f"Uninitialized state: '{label}' ({box_id}) drives DSP at "
                f"'{_box_label(dsp_box)}' ({dsp_id}) but nothing sets it at load "
                f"{_UNINIT_ROUTES} -- it shows its default until touched while "
                "the DSP runs on its own value"
            )
        results.append(CriticResult(
            severity, finding, _UNINIT_SUGGESTION,
            rule="uninitialized_state",
            box_ids=finding_ids(box_id, dsp[1] if dsp is not None else None),
        ))
    return results
