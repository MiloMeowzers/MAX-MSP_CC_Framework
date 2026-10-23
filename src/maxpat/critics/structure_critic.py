"""Structure critic -- checks patch architecture and connection patterns.

Catches structural issues that the mechanical validation pipeline does
not detect:
  - Fan-out without trigger (ordering ambiguity): blocker when one branch
    reaches a box's hot inlet 0 and another a DB-cold inlet of it (Q3 / E1;
    hot/cold-aware since quick 261022-ud6 CR-02), otherwise warning.
    The blocker carries an ``insert_trigger`` quick-fix payload
    (``CriticResult.fix``, Q39) ordering cold-inlet branches first.
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
  - Q23 vocabulary (fix-plan Q23; review §4.4 R7 / R10): int truncation
    (warning; a float source into arg-less ``+ - * /`` / ``ftom`` or an
    integer-range ``scale``, D7), MC bare list (note; a bare list into an
    ``mc.*`` wrapper, D9) -- both in max scopes -- and unmatched send /
    receive / value / buffer names (warning; once per review over the
    whole tree, closed trees only, D6).

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
         control outlet; blocker only when branches reach one box's hot
         inlet 0 and a cold inlet -- Q3 / E1, CR-02)
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
      8. Int truncation (warning; Q23 D7) and MC bare list (note; Q23 D9),
         max scopes only.
      9. Unmatched names (warning; Q23 D6): once, after the per-scope
         loop, over every max scope of a closed tree; each finding is
         tagged with its own scope.

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
            found.extend(_check_fan_out_without_trigger(scope.boxes, scope.edges, dbh))
            found.extend(_check_hot_cold_ordering(scope, dbh, _q21_targets(scope, dbh)))
            found.extend(_check_trigger_types(scope))
            found.extend(_check_dollar_arity(scope, dbh))
            found.extend(trigger_order)
            found.extend(_check_uninitialized_state(graph, scope, dbh, is_new, ctx))
            if scope.scope != "rnbo":
                # Q23 (D7, D9): RNBO math is float and has no MC wrappers
                found.extend(_check_int_truncation(scope, dbh))
                found.extend(_check_mc_bare_list(scope, dbh))
        found.extend(_check_redundant_connections(scope.edges))
        results.extend(tag_results(found, scope.path))
    # Q23 (D6): one pass over the whole tree, each finding tagged in its scope
    results.extend(_check_unmatched_names(graph, dbh))
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


def _enters_hot(box, inlet, dbh) -> bool:
    """True when an event entering *box* at *inlet* makes it output (CR-02).

    Inlet 0 is hot; an inlet > 0 is hot unless the DB marks it cold
    (:func:`_inlet_is_cold`). ``_ALL_HOT_NAMES`` boxes route every inlet to
    their own inner path, so every inlet counts as hot. Without a DB handle
    every inlet counts as hot (the pre-261022-ud6 behaviour).
    """
    if dbh is None or box is None:
        return True
    if walk.box_name(box) in _ALL_HOT_NAMES:
        return True
    return not (isinstance(inlet, int) and _inlet_is_cold(box, inlet, dbh))


def _is_cold_hit(box, inlet, dbh) -> bool:
    """True for an inlet > 0 that stores a value without output (CR-02).

    With a DB handle: a DB-cold inlet. Without one: any inlet > 0 (the
    pre-261022-ud6 behaviour).
    """
    if not isinstance(inlet, int) or inlet <= 0:
        return False
    if dbh is None:
        return True
    return _inlet_is_cold(box, inlet, dbh)


def _branch_hits(
    src_id: str,
    branches: list[tuple[str, int]],
    ctrl_adj: dict[str, list[tuple[str, int]]],
    box_lookup: dict[str, dict],
    dbh=None,
) -> list[dict[str, set[int]]]:
    """One ``box id -> inlets reached`` map per branch (Q3; factored out for Q39).

    Each branch ``(dst_id, inlet)`` is walked breadth-first over control
    cords, recording every inlet reached on every box. A box is expanded
    only once a branch enters it at a hot inlet (:func:`_enters_hot`,
    quick 261022-ud6 CR-02): an event stored at a cold inlet emits nothing,
    so the walk records the hit and stops there. A Jitter setter hop
    (:func:`_is_jitter_setter_hop`), including the first hop from the
    fan-out source, records the hit at the jit.* box but does not expand
    past it (Q20).
    """
    src_box = box_lookup.get(src_id)
    hit_maps: list[dict[str, set[int]]] = []
    for dst_id, dst_inlet in branches:
        hits: dict[str, set[int]] = defaultdict(set)
        hits[dst_id].add(dst_inlet)
        seen: set = set()
        queue = deque()
        dst_box = box_lookup.get(dst_id)
        if not _is_jitter_setter_hop(src_box, dst_box) and _enters_hot(dst_box, dst_inlet, dbh):
            seen.add(dst_id)
            queue.append(dst_id)
        while queue:
            node = queue.popleft()
            node_box = box_lookup.get(node)
            for nxt, nxt_inlet in ctrl_adj.get(node, ()):
                hits[nxt].add(nxt_inlet)
                nxt_box = box_lookup.get(nxt)
                if _is_jitter_setter_hop(node_box, nxt_box):
                    continue
                if nxt in seen or nxt == src_id:
                    continue
                if not _enters_hot(nxt_box, nxt_inlet, dbh):
                    continue
                seen.add(nxt)
                queue.append(nxt)
        hit_maps.append(hits)
    return hit_maps


def _meeting_boxes(
    hit_maps: list[dict[str, set[int]]], box_lookup: dict[str, dict], dbh=None,
) -> set:
    """Every box (outside ``_ALL_HOT_NAMES``) where one branch reaches the
    hot inlet 0 and a different branch a cold inlet (quick 261022-ud6 CR-02:
    :func:`_is_cold_hit`). Two cold updates, or two hot ones, cannot leave
    a stale value behind, so they are not a meeting."""
    meeting: set[str] = set()
    for k in range(len(hit_maps)):
        for l in range(len(hit_maps)):
            if k == l:
                continue
            hits_k, hits_l = hit_maps[k], hit_maps[l]
            for box_id in hits_k.keys() & hits_l.keys():
                if box_id in meeting or 0 not in hits_k[box_id]:
                    continue
                box = box_lookup.get(box_id)
                if box is not None and walk.box_name(box) in _ALL_HOT_NAMES:
                    continue
                if any(_is_cold_hit(box, i, dbh) for i in hits_l[box_id]):
                    meeting.add(box_id)
    return meeting


# Source outlettype -> trigger letter for the Q39 insert_trigger payload
_FIX_TRIGGER_LETTER = {"bang": "b", "int": "i", "float": "f", "list": "l", "": "l"}


def _fan_out_trigger_fix(
    src_box: dict,
    src_id: str,
    src_outlet: int,
    branches: list[tuple[str, int]],
    hit_maps: list[dict[str, set[int]]],
    meetings: set,
    box_lookup: dict[str, dict],
    dbh=None,
):
    """insert_trigger payload for a reconverging fan-out, or None (Q39).

    Letter from the source outlettype (bang -> b, int -> i, float -> f,
    list or "" -> l); any other type, a missing entry or a duplicate branch
    cord gives None. Order: at every meeting box, a branch reaching it at a
    cold inlet (:func:`_is_cold_hit`, CR-02) fires before a different branch
    reaching it at inlet 0 (cold before hot). A stable topological sort
    keeps ties in cord order; a cycle (conflicting constraints) gives None.
    :func:`src.maxpat.critics.fixes.trigger_fix` puts the first-fired branch
    on the highest outlet (trigger outlets fire right to left).
    """
    from src.maxpat.critics.fixes import trigger_fix

    outlettype = src_box.get("outlettype") if isinstance(src_box, dict) else None
    if not isinstance(outlettype, list) or not (0 <= src_outlet < len(outlettype)):
        return None
    kind = outlettype[src_outlet]
    if not isinstance(kind, str) or kind not in _FIX_TRIGGER_LETTER:
        return None
    letter = _FIX_TRIGGER_LETTER[kind]
    if len(set(branches)) != len(branches) or len(branches) != len(hit_maps):
        return None

    n = len(branches)
    before: dict[int, set[int]] = {i: set() for i in range(n)}  # j in before[i]: j fires before i
    for m in meetings:
        m_box = box_lookup.get(m)
        cold = [c for c in range(n) if any(_is_cold_hit(m_box, x, dbh) for x in hit_maps[c].get(m, ()))]
        hot = [h for h in range(n) if 0 in hit_maps[h].get(m, ())]
        for c in cold:
            for h in hot:
                if c != h:
                    before[h].add(c)

    order: list[int] = []
    placed: set[int] = set()
    while len(order) < n:
        nxt = next((i for i in range(n) if i not in placed and before[i] <= placed), None)
        if nxt is None:
            return None  # cycle: no safe order
        order.append(nxt)
        placed.add(nxt)

    ordered = []
    for i in order:
        dst_id, dst_inlet = branches[i]
        dst_box = box_lookup.get(dst_id)
        ordered.append((dst_id, dst_inlet, walk.box_name(dst_box) if dst_box else dst_id))
    return trigger_fix(src_id, src_outlet, walk.box_name(src_box), letter, ordered)


def _fan_out_branches(box_lookup, src_id, src_outlet, dests, has_outgoing) -> list:
    """The branches of one source outlet the fan-out check counts, or [].

    [] for a signal outlet (Rule #3), a ``preset`` membership outlet, or
    fewer than 2 destinations once display-only sinks (``_DISPLAY_SINK_NAMES``
    with no outgoing cord) are dropped. Shared with the hot/cold check,
    which leaves these outlets to the fan-out check (IN-02).
    """
    if len(dests) < 2:
        return []
    src_box = box_lookup.get(src_id)
    if not src_box or _outlet_is_signal(src_box, src_outlet):
        return []
    if walk.box_name(src_box) == "preset" and src_outlet in _PRESET_MEMBERSHIP_OUTLETS:
        return []
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
    return branches if len(branches) >= 2 else []


def _check_fan_out_without_trigger(
    box_lookup: dict[str, dict],
    edges: list,
    dbh=None,
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

    Severity: BLOCKER only when two branches reconverge on one box (outside
    ``_ALL_HOT_NAMES``) with one branch at the hot inlet 0 and another at a
    DB-cold inlet -- then execution order changes the result. A branch that
    enters a box at a cold inlet stops there (the box emits nothing), and two
    cold updates cannot leave a stale value (quick 261022-ud6 CR-02; *dbh*
    supplies the inlet flags, None treats every inlet > 0 as cold and every
    inlet as expanding). Otherwise WARNING. (History: promoted to an
    unconditional blocker by 260427-hox §P0-1; narrowed by Q3 because most
    of those blockers were false positives.)

    The blocker carries an ``insert_trigger`` quick-fix payload (Q39,
    :func:`_fan_out_trigger_fix`) when a safe cold-before-hot order exists;
    a warning never does.
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
        branches = _fan_out_branches(box_lookup, src_id, src_outlet, dests, has_outgoing)
        if not branches:
            continue
        src_box = box_lookup[src_id]
        src_name = walk.box_name(src_box)

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
        hit_maps = _branch_hits(src_id, branches, ctrl_adj, box_lookup, dbh)
        meetings = _meeting_boxes(hit_maps, box_lookup, dbh)
        meet_id = min(meetings) if meetings else None
        fix = None
        if meet_id is not None:
            meet_box = box_lookup.get(meet_id)
            meet_name = walk.box_name(meet_box) if meet_box else meet_id
            severity = "blocker"
            finding = (
                f"{prefix} paths reconverge on '{meet_name}' ({meet_id}) at "
                f"different inlets, so execution order changes the result"
            )
            fix = _fan_out_trigger_fix(
                src_box, src_id, src_outlet, branches, hit_maps,
                meetings, box_lookup, dbh,
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
            fix=fix,
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
      hazards: each B wave sets its own cold inlets first. An equal outlet
      the fan-out check already reports (:func:`_fan_out_owns`) is skipped,
      so one defect gives one finding (IN-02, quick 261022-ud6).
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
            if c == h and _fan_out_owns(scope, anc, c):
                # IN-02 (quick 261022-ud6): one outlet feeding both sides is a
                # fan-out; the fan-out check reports it (blocker when the
                # branches meet hot and cold), so it is not reported twice.
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


def _fan_out_owns(scope, src_id, outlet) -> bool:
    """True when the fan-out check reports (*src_id*, *outlet*) (IN-02)."""
    dests = [
        (e.dst, e.inlet) for e in scope.out_edges.get(src_id, ()) if e.outlet == outlet
    ]
    has_outgoing = {b for b in scope.boxes if scope.out_edges.get(b)}
    return bool(_fan_out_branches(scope.boxes, src_id, outlet, dests, has_outgoing))


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

    Precedence (Q21, planner decision 6; reordered by quick 261022-ud6
    WR-01 -- what MAX saved beats the extracted DB):
      a. a trigger/t outlet takes its type letter (:func:`_trigger_letters`);
         an outlet past the argument count is unknown;
      b. otherwise the box's MAX-saved ``outlettype`` at that index:
         ``bang`` = 0, ``int`` / ``float`` = 1; any other non-empty entry
         (``list``, ``signal``, ...) is unknown;
      c. only when that entry is missing or ``""``, for a DB object that is
         not ``variable_io``, the DB outlet ``type``: ``bang`` = 0,
         ``int`` / ``float`` / ``symbol`` = 1 -- unless its
         ``signal_role`` says ``list`` (the DB type disagrees with itself:
         zplane~'s coordinate-pair outlets), which is unknown.
    ``signal_role`` is a validator concept, never an atom count. Anything
    else is unknown.
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

    outlettype = box.get("outlettype")
    if isinstance(outlettype, list) and outlet < len(outlettype):
        saved = outlettype[outlet]
        if saved == "bang":
            return 0
        if saved in ("int", "float"):
            return 1
        if isinstance(saved, str) and saved:
            return None

    obj = dbh.lookup(name)
    if obj is not None and not obj.get("variable_io"):
        entry = _db_entry(obj.get("outlets"), outlet)
        if entry is not None:
            if entry.get("signal_role") == "list":
                return None
            otype = entry.get("type")
            if otype == "bang":
                return 0
            if otype in ("int", "float", "symbol"):
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
    # Design note (quick 261022-ud6 IN-05, locked D-01 -- behaviour kept): a
    # transport toggle -> metro -> message -> line~ is reported although the
    # toggle and the metro both start off at load, so the state already
    # agrees. With the build loop now passing is_new=True (CR-04), every new
    # patch with a play toggle needs a redundant `loadmess 0`. A possible
    # refinement, pending a user decision: stop the reach walk at a clock
    # (metro, tempo, qmetro) when the holder is a toggle.
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


# ===========================================================================
# Q23 vocabulary checks (fix-plan Q23; review §4.4 R7 / R10; quick 261022-ud6
# WP7b, review-docs-completion CR-01). Graph-shaped, so they live in the
# critic (planner decision D1); none is a blocker.
# ===========================================================================


def _db_exists(dbh, name) -> bool:
    """Guarded ``exists``: False on any error or a non-str name."""
    if not isinstance(name, str) or not name:
        return False
    try:
        return bool(dbh.get().exists(name))
    except Exception:
        return False


def _db_messages(dbh, name) -> list:
    """Guarded ``messages``: ``[]`` on any error or an unknown name."""
    if not isinstance(name, str) or not name:
        return []
    try:
        out = dbh.get().messages(name)
    except Exception:
        return []
    return out if isinstance(out, list) else []


def _positional_args(box) -> list:
    """newobj argument tokens up to the first ``@`` attribute."""
    out: list = []
    for token in walk.box_args(box):
        if token.startswith("@"):
            break
        out.append(token)
    return out


# ---------------------------------------------------------------------------
# Unmatched send / receive / value / buffer names (D6)
# ---------------------------------------------------------------------------

_SEND_NAMES = frozenset({"s", "send"})
_RECEIVE_NAMES = frozenset({"r", "receive"})
_SEND_SIG_NAMES = frozenset({"send~", "mc.send~"})
_RECEIVE_SIG_NAMES = frozenset({"receive~", "mc.receive~"})
_VALUE_NAMES = {"v": "value", "value": "value", "pv": "pv"}
_BUFFER_DEFINERS = frozenset({"buffer~", "jit.buffer~"})
_POLYBUFFER_NAMES = frozenset({"polybuffer~"})
# Buffer users: name -> positional index of the buffer~ name
_BUFFER_USERS = {
    "play~": 0, "groove~": 0, "index~": 0, "peek~": 0, "wave~": 0,
    "record~": 0, "poke~": 0, "buffir~": 0, "lookup~": 0, "info~": 0,
    "2d.wave~": 0, "mc.play~": 0, "mc.groove~": 0, "mcs.play~": 0,
    "mcs.groove~": 0, "mc.record~": 0, "cycle~": 1,
}
# Receivers MAX itself binds: a ``; max ...`` message is never unmatched
_SYSTEM_RECEIVERS = frozenset({"max", "dsp", "jitter"})
# Boxes that send or receive by computed names (scripts, forward)
_OPEN_TREE_NAMES = frozenset({
    "js", "jsui", "v8", "v8ui", "v8.codebox", "node.script", "node.codebox",
    "forward", "pattrforward",
})
_ABSTRACTION_PORT_NAMES = frozenset({"in", "out", "in~", "out~", "thispoly~"})
_FILE_CONTAINER_NAMES = frozenset({"poly~", "mc.poly~", "mcs.poly~", "pfft~"})
_NAME_ARG_REQUIRED = (
    _SEND_NAMES | _RECEIVE_NAMES | _SEND_SIG_NAMES | _RECEIVE_SIG_NAMES
)

_UNMATCHED_SUGGESTION = (
    "Check the name for a typo (names are case-sensitive). If the other end "
    "lives in another patch, an abstraction or a script, ignore this warning."
)


def _usable_name(token) -> bool:
    """A literal file-local name: not ``#N``-substituted, not ``$``-built,
    not a Max for Live ``---`` device-scoped name (shared by every file of
    the device; bundle FilterTaps/bdband2), not a number (``send 15`` is a
    "bad arguments" box -- max-bridge fx-badargs fixture)."""
    return (isinstance(token, str) and bool(token) and "#" not in token
            and not token.startswith(("$", "---")) and not _is_number(token))


def _tree_is_open(graph, scopes) -> bool:
    """D6: True when names may be matched outside this file (skip the check)."""
    for box in graph.top.boxes.values():
        maxclass = walk.box_maxclass(box)
        if maxclass in ("inlet", "outlet"):
            return True
        if maxclass == "newobj" and walk.box_name(box) in _ABSTRACTION_PORT_NAMES:
            return True
    for scope in scopes:
        for box in scope.boxes.values():
            maxclass = walk.box_maxclass(box)
            name = walk.box_name(box)
            if maxclass == "bpatcher" and walk.inner_patcher(box) is None:
                return True
            if name in _OPEN_TREE_NAMES:
                return True
            if maxclass != "newobj":
                continue
            if name in _FILE_CONTAINER_NAMES and walk.inner_patcher(box) is None:
                return True
            if name in _NAME_ARG_REQUIRED and not _positional_args(box):
                return True
    return False


def _check_unmatched_names(graph, dbh) -> list[CriticResult]:
    """Warn on send / receive / value / buffer names with no other end (D6).

    Q23 / R7 (review §4.1 class 7). Runs once per review over every max /
    poly / bpatcher scope (gen and rnbo boxes are ignored) and only on a
    CLOSED tree (:func:`_tree_is_open`): the top scope has no inlet /
    outlet / ``in`` / ``out`` / ``thispoly~`` (it is not an abstraction or
    voice), no bpatcher or poly~ / pfft~ loads a file, no script or
    ``forward`` exists, every send / receive has a name and the DB knows
    every newobj name (checked last, only when a named box was collected).
    ``#N`` / ``$`` names are ignored; ``; max`` / ``; dsp`` / ``; jitter``
    are never unmatched; a ``;`` target also matches any buffer~ /
    polybuffer~ / value name (objects MAX binds to their names). Buffers
    are checked one way (a user with no definer); an unused buffer~ is
    normal.
    """
    scopes = [s for s in graph.scopes if s.scope not in ("gen", "rnbo")]
    if not scopes or _tree_is_open(graph, scopes):
        return []

    sends: list = []      # (scope, box_id, box, name, kind) kind: ctl/sig/remote
    receives: list = []   # (scope, box_id, box, name, kind)
    values: list = []     # (scope, box_id, box, name, flavour)
    users: list = []      # (scope, box_id, box, name)
    defined: set = set()
    poly_prefixes: set = set()
    newobj_names: set = set()
    for scope in scopes:
        for box_id, box in scope.boxes.items():
            for target in walk.message_remote_targets(box):
                if _usable_name(target):
                    sends.append((scope, box_id, box, target, "remote"))
            if walk.box_maxclass(box) != "newobj":
                continue
            name = walk.box_name(box)
            if not name:
                continue
            newobj_names.add(name)
            args = _positional_args(box)
            first = args[0] if args else None
            if name in _SEND_NAMES and _usable_name(first):
                sends.append((scope, box_id, box, first, "ctl"))
            elif name in _RECEIVE_NAMES and _usable_name(first):
                receives.append((scope, box_id, box, first, "ctl"))
            elif name in _SEND_SIG_NAMES and _usable_name(first):
                sends.append((scope, box_id, box, first, "sig"))
            elif name in _RECEIVE_SIG_NAMES and _usable_name(first):
                receives.append((scope, box_id, box, first, "sig"))
            elif name in _VALUE_NAMES and _usable_name(first):
                values.append((scope, box_id, box, first, _VALUE_NAMES[name]))
            elif name in _BUFFER_DEFINERS and _usable_name(first):
                defined.add(first)
            elif name in _POLYBUFFER_NAMES and _usable_name(first):
                defined.add(first)
                poly_prefixes.add(first + ".")
            elif name in _BUFFER_USERS:
                index = _BUFFER_USERS[name]
                token = args[index] if len(args) > index else None
                if _usable_name(token) and not _is_number(token):
                    users.append((scope, box_id, box, token))

    if not (sends or receives or values or users):
        return []
    # Unknown newobj names are abstractions or externals: open tree (D6)
    if any(not _db_exists(dbh, n) for n in sorted(newobj_names)):
        return []

    ctl_rx = {n for _, _, _, n, k in receives if k == "ctl"}
    sig_rx = {n for _, _, _, n, k in receives if k == "sig"}
    ctl_tx = {n for _, _, _, n, k in sends if k in ("ctl", "remote")}
    sig_tx = {n for _, _, _, n, k in sends if k == "sig"}
    value_names = {n for _, _, _, n, _ in values}
    value_counts: dict = defaultdict(int)
    for _, _, _, n, flavour in values:
        value_counts[(flavour, n)] += 1

    per_scope: dict = defaultdict(list)

    def add(scope, finding, box_id):
        per_scope[scope.path].append(CriticResult(
            "warning", finding, _UNMATCHED_SUGGESTION,
            rule="unmatched_names", box_ids=finding_ids(box_id),
        ))

    for scope, box_id, box, name, kind in sends:
        text = walk.box_text(box)
        if kind in ("ctl", "sig"):
            if name not in (sig_rx if kind == "sig" else ctl_rx):
                add(scope, f"Unmatched send: '{text}' ({box_id}) -- nothing in "
                           f"this patch tree receives '{name}'", box_id)
        elif (name not in ctl_rx and name not in _SYSTEM_RECEIVERS
              and name not in defined and name not in value_names):
            add(scope, f"Unmatched send: message '{text}' ({box_id}) targets "
                       f"';{name}' -- nothing in this patch tree receives "
                       f"'{name}'", box_id)
    for scope, box_id, box, name, kind in receives:
        if name not in (sig_tx if kind == "sig" else ctl_tx):
            add(scope, f"Unmatched receive: '{walk.box_text(box)}' ({box_id}) -- "
                       f"nothing in this patch tree sends to '{name}'", box_id)
    for scope, box_id, box, name, flavour in values:
        if value_counts[(flavour, name)] == 1:
            add(scope, f"Unmatched value: '{walk.box_text(box)}' ({box_id}) is "
                       f"the only {flavour} named '{name}' in this patch tree", box_id)
    for scope, box_id, box, name in users:
        if name in defined or any(name.startswith(p) for p in poly_prefixes):
            continue
        add(scope, f"Unmatched buffer: '{walk.box_text(box)}' ({box_id}) reads "
                   f"buffer~ '{name}', but no buffer~, polybuffer~ or jit.buffer~ "
                   f"named '{name}' is in this patch tree", box_id)

    results: list[CriticResult] = []
    for scope in scopes:
        found = per_scope.get(scope.path)
        if found:
            results.extend(tag_results(found, scope.path))
    return results


# ---------------------------------------------------------------------------
# Int truncation (D7)
# ---------------------------------------------------------------------------

_INT_MATH_NAMES = frozenset({"+", "-", "*", "/"})
_FLOAT_ARG_MATH_NAMES = frozenset({"+", "-", "*", "/", "!-", "!/", "%", "pow"})
_LIVE_NUMERIC_UI = frozenset({"live.dial", "live.numbox", "live.slider"})
_INT_LITERAL_RE = re.compile(r"[+-]?\d+")


def _live_parameter_type(box):
    saa = box.get("saved_attribute_attributes")
    valueof = saa.get("valueof") if isinstance(saa, dict) else None
    return valueof.get("parameter_type") if isinstance(valueof, dict) else None


def _is_float_source(box, outlet, dbh) -> bool:
    """D7: True when *box* outlet *outlet* emits floats.

    A UI box's saved outlettype is never trusted (MAX saves ``float`` for
    every dial whatever ``floatoutput`` says).
    """
    maxclass = walk.box_maxclass(box)
    if maxclass == "flonum":
        return outlet == 0
    if maxclass in ("dial", "slider"):
        return outlet == 0 and box.get("floatoutput") == 1
    if maxclass in _LIVE_NUMERIC_UI:
        return outlet == 0 and _live_parameter_type(box) not in (1, 2)
    if maxclass != "newobj":
        return False
    name = walk.box_name(box)
    if name in _TRIGGER_NAMES:
        letters = _trigger_letters(box)
        return 0 <= outlet < len(letters) and letters[outlet] == "f"
    if name in ("f", "float"):
        return outlet == 0
    if name in _FLOAT_ARG_MATH_NAMES:
        if outlet == 0 and any("." in a for a in _positional_args(box)):
            return True
    saved = box.get("outlettype")
    if isinstance(saved, list) and 0 <= outlet < len(saved) and saved[outlet] == "float":
        return True
    obj = dbh.lookup(name)
    if obj is not None and not obj.get("variable_io"):
        entry = _db_entry(obj.get("outlets"), outlet)
        if isinstance(entry, dict) and entry.get("type") == "float":
            return True
    return False


def _int_mode_kind(box) -> "str | None":
    """D7: the kind of int-mode destination *box* is, or None.

    ``"math"`` for arg-less ``+ - * /`` (any inlet), ``"ftom"`` for arg-less
    ``ftom`` (inlet 0), ``"scale"`` for ``scale`` with two integer input
    range arguments (inlet 0).
    """
    if walk.box_maxclass(box) != "newobj":
        return None
    name = walk.box_name(box)
    args = _positional_args(box)
    if name in _INT_MATH_NAMES and not args:
        return "math"
    if name == "ftom" and not args:
        return "ftom"
    if (name == "scale" and len(args) >= 2
            and _INT_LITERAL_RE.fullmatch(args[0]) and _INT_LITERAL_RE.fullmatch(args[1])):
        return "scale"
    return None


def _check_int_truncation(scope, dbh) -> list[CriticResult]:
    """Warn on a float source feeding an int-mode box (D7; review §4.1 class 13).

    Arg-less ``+ - * /`` and ``ftom`` and integer-range ``scale`` truncate
    floats (TCI ``f -> + 0.0025 -> -``; 0f1becf, 503f92f). Max scopes only.
    """
    results: list[CriticResult] = []
    for edge in scope.edges:
        dst = scope.boxes.get(edge.dst)
        src = scope.boxes.get(edge.src)
        if not dst or not src or edge.signal:
            continue
        kind = _int_mode_kind(dst)
        if kind is None or (kind != "math" and edge.inlet != 0):
            continue
        if not _is_float_source(src, edge.outlet, dbh):
            continue
        name = walk.box_name(dst)
        if kind == "math":
            suggestion = f"Give it a float argument (e.g. '{name} 0.')."
        elif kind == "ftom":
            suggestion = "Use 'ftom 0.' for float output."
        else:
            suggestion = "Use float input-range arguments (e.g. 'scale 0. 127. 0. 1.')."
        results.append(CriticResult(
            "warning",
            f"Int truncation: '{walk.box_text(dst)}' ({edge.dst}) runs in int mode "
            f"but inlet {edge.inlet} is fed by float source '{_box_label(src)}' "
            f"({edge.src}) outlet {edge.outlet} -- the fractional part is dropped",
            suggestion,
            rule="int_truncation", box_ids=finding_ids(edge.dst, edge.src),
            port=edge.inlet,
        ))
    return results


# ---------------------------------------------------------------------------
# MC bare list (D9)
# ---------------------------------------------------------------------------

# A list into these MC objects is a ramp for every channel, by design
_MC_LIST_RAMPS = frozenset({"mc.line~", "mc.curve~"})
_DOLLAR_ARG_RE = re.compile(r"\$[1-9]")


def _is_list_atom(token) -> bool:
    return isinstance(token, str) and (
        _is_number(token) or bool(_DOLLAR_ARG_RE.fullmatch(token)))


def _sends_bare_list(box, outlet) -> bool:
    """D9: a message with a 2+ token numeric segment, or a numeric pack/pak."""
    if walk.box_maxclass(box) == "message":
        return any(len(seg) >= 2 and _is_list_atom(seg[0])
                   for seg in walk.message_segments(box))
    if walk.box_maxclass(box) == "newobj" and outlet == 0:
        if walk.box_name(box) in ("pack", "pak"):
            args = _positional_args(box)
            return not args or _is_number(args[0])
    return False


def _check_mc_bare_list(scope, dbh) -> list[CriticResult]:
    """Note a bare list into an MC wrapper (D9; review §4.1 class 6).

    Every channel of an ``mc.*`` wrapper receives the whole list (memory:
    ji-harmonizer v0.0.2 ``440 550 660 -> mc.cycle~``); ``applyvalues``
    distributes it. A wrapper is an ``mc.*`` newobj whose ``db.messages``
    include ``applyvalues`` (groups.json, Q14), except mc.line~ /
    mc.curve~ (a list there is a ramp for every channel).
    """
    results: list[CriticResult] = []
    for edge in scope.edges:
        dst = scope.boxes.get(edge.dst)
        src = scope.boxes.get(edge.src)
        if not dst or not src or edge.signal or walk.box_maxclass(dst) != "newobj":
            continue
        name = walk.box_name(dst)
        if not name.startswith("mc.") or name in _MC_LIST_RAMPS:
            continue
        if not _sends_bare_list(src, edge.outlet):
            continue
        if "applyvalues" not in _db_messages(dbh, name):
            continue
        results.append(CriticResult(
            "note",
            f"MC bare list: '{_box_label(src)}' ({edge.src}) sends a bare list to "
            f"MC wrapper '{name}' ({edge.dst}) inlet {edge.inlet} -- every channel "
            f"receives the whole list; it is not distributed one value per channel",
            "Prefix it with applyvalues (value k -> channel k), replicatevalues or "
            "setvalue <chan> (e.g. 'prepend applyvalues').",
            rule="mc_bare_list", box_ids=finding_ids(edge.src, edge.dst),
            port=edge.inlet,
        ))
    return results
