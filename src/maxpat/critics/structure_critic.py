"""Structure critic -- checks patch architecture and connection patterns.

Catches structural issues that the mechanical validation pipeline does
not detect:
  - Fan-out without trigger (ordering ambiguity): blocker when branches
    reconverge on one box at different inlets, otherwise warning (Q3 / E1)
  - Hot/cold inlet ordering issues (stale value computation)
  - Redundant/duplicate patchlines

NOTE: Does NOT duplicate validation.py checks. Focus is on architectural
patterns a MAX expert would flag during code review.
"""

from __future__ import annotations

from collections import defaultdict, deque

from src.maxpat.critics.base import CriticResult
from src.maxpat.utils import get_box_name


# Object names that provide explicit ordering (used by the hot/cold check)
_TRIGGER_NAMES = frozenset({"trigger", "t"})

# Outlet types that carry audio; fan-out from these is never flagged (Rule #3)
_SIGNAL_OUTLET_TYPES = frozenset({"signal", "multichannelsignal"})

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


def review_structure(patch_dict: dict) -> list[CriticResult]:
    """Review structural aspects of a patch.

    Checks:
      1. Fan-out without trigger (2+ non-display destinations from one
         control outlet; blocker only on reconvergence -- Q3 / E1)
      2. Hot/cold inlet ordering (multiple inlets fed without trigger ordering)
      3. Redundant/duplicate patchlines

    Args:
        patch_dict: A .maxpat-format dict.

    Returns:
        List of CriticResult findings.
    """
    results: list[CriticResult] = []

    patcher = patch_dict.get("patcher", {})
    boxes = patcher.get("boxes", [])
    lines = patcher.get("lines", [])

    # Build box lookup
    box_lookup: dict[str, dict] = {}
    for box_entry in boxes:
        box = box_entry.get("box", {})
        box_id = box.get("id")
        if box_id:
            box_lookup[box_id] = box

    # Run checks
    results.extend(_check_fan_out_without_trigger(box_lookup, lines))
    results.extend(_check_hot_cold_ordering(box_lookup, lines))
    results.extend(_check_redundant_connections(lines))

    return results


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_trigger_object(box: dict) -> bool:
    """Check if a box is a trigger/t object."""
    name = get_box_name(box)
    return name in _TRIGGER_NAMES


def _is_signal_object(box: dict) -> bool:
    """Check if a box is a signal-rate (~) object."""
    name = get_box_name(box)
    return name.endswith("~")


# ---------------------------------------------------------------------------
# Check 1: Fan-out without trigger
# ---------------------------------------------------------------------------

def _outlet_is_signal(box: dict, outlet: int) -> bool:
    """True when `box` outlet `outlet` carries audio (Q3 / E1).

    Decided by the box's ``outlettype`` entry at that index. Only when the
    box has no entry there (hand-built dicts) does it fall back to the legacy
    ``~``-name test.
    """
    outlettype = box.get("outlettype")
    if isinstance(outlettype, list) and 0 <= outlet < len(outlettype):
        return outlettype[outlet] in _SIGNAL_OUTLET_TYPES
    return _is_signal_object(box)


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
    """
    hit_maps: list[dict[str, set[int]]] = []
    for dst_id, dst_inlet in branches:
        hits: dict[str, set[int]] = defaultdict(set)
        hits[dst_id].add(dst_inlet)
        seen = {dst_id}
        queue = deque([dst_id])
        while queue:
            node = queue.popleft()
            for nxt, nxt_inlet in ctrl_adj.get(node, ()):
                hits[nxt].add(nxt_inlet)
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
                if box is not None and get_box_name(box) in _ALL_HOT_NAMES:
                    continue
                if any(a != b for a in hits_k[box_id] for b in hits_l[box_id]):
                    meeting.add(box_id)
    return min(meeting) if meeting else None


def _check_fan_out_without_trigger(
    box_lookup: dict[str, dict],
    lines: list[dict],
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

    for line_entry in lines:
        patchline = line_entry.get("patchline", line_entry)
        source = patchline.get("source", [])
        destination = patchline.get("destination", [])
        if len(source) < 2 or len(destination) < 2:
            continue

        src_id, src_outlet = source[0], source[1]
        dst_id, dst_inlet = destination[0], destination[1]
        has_outgoing.add(src_id)
        fan_out[(src_id, src_outlet)].append((dst_id, dst_inlet))

        src_box = box_lookup.get(src_id)
        if src_box is None or not _outlet_is_signal(src_box, src_outlet):
            ctrl_adj[src_id].append((dst_id, dst_inlet))

    for (src_id, src_outlet), dests in fan_out.items():
        if len(dests) < 2:
            continue

        src_box = box_lookup.get(src_id)
        if not src_box:
            continue

        # Signal outlets: all signal inlets are hot per Rule #3
        if _outlet_is_signal(src_box, src_outlet):
            continue

        src_name = get_box_name(src_box)

        # preset include/exclude/capture membership cords
        if src_name == "preset" and src_outlet in _PRESET_MEMBERSHIP_OUTLETS:
            continue

        # Drop display-only sinks (no outgoing cord of their own)
        branches = []
        for dst_id, dst_inlet in dests:
            dst_box = box_lookup.get(dst_id)
            if (
                dst_box is not None
                and get_box_name(dst_box) in _DISPLAY_SINK_NAMES
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
                dst_names.append(f"'{get_box_name(dst_box)}' ({dst_id})")
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
            meet_name = get_box_name(meet_box) if meet_box else meet_id
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
    lines: list[dict],
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

    for line_entry in lines:
        patchline = line_entry.get("patchline", line_entry)
        source = patchline.get("source", [])
        destination = patchline.get("destination", [])
        if len(source) < 2 or len(destination) < 2:
            continue

        src_id, src_outlet = source[0], source[1]
        dst_id, dst_inlet = destination[0], destination[1]
        dst_inlets[dst_id][dst_inlet].append((src_id, src_outlet))

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
        dst_name = get_box_name(dst_box)
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
# Check 3: Redundant/duplicate connections
# ---------------------------------------------------------------------------

def _check_redundant_connections(
    lines: list[dict],
) -> list[CriticResult]:
    """Detect duplicate patchlines (same source -> same destination)."""
    results: list[CriticResult] = []

    seen: set[tuple[str, int, str, int]] = set()

    for line_entry in lines:
        patchline = line_entry.get("patchline", line_entry)
        source = patchline.get("source", [])
        destination = patchline.get("destination", [])
        if len(source) < 2 or len(destination) < 2:
            continue

        key = (source[0], source[1], destination[0], destination[1])

        if key in seen:
            results.append(CriticResult(
                "warning",
                f"Duplicate patchline: {source[0]} outlet {source[1]} -> "
                f"{destination[0]} inlet {destination[1]} appears multiple times",
                "Remove the duplicate connection",
            ))
        else:
            seen.add(key)

    return results
