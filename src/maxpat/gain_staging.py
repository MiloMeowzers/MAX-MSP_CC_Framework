"""Missing-gain-staging rule shared by validation and the DSP critic.

One traversal and one oscillator vocabulary (fix-plan Q33 / review S7):
validation.py Layer 4 reports a warning (base oscillators, ``"signal"``
cords) and the DSP critic a blocker (base and mc oscillators,
``SIGNAL_OUTLET_TYPES`` cords). Each caller builds its own signal adjacency
and passes the gain-stage / output-terminal sets from
:mod:`src.maxpat.dsp_roles`, so the two keep today's findings.
"""

from __future__ import annotations

from collections import deque

from src.maxpat import walk

# Oscillator objects that need gain staging before an output terminal
OSCILLATOR_NAMES = frozenset({
    "cycle~", "saw~", "rect~", "tri~", "noise~", "pink~",
})

# Multichannel oscillators (the DSP critic checks these too)
MC_OSCILLATOR_NAMES = frozenset({
    "mc.cycle~", "mc.saw~", "mc.rect~", "mc.tri~",
})


def find_ungained_paths(
    box_lookup: dict[str, dict],
    signal_adj: dict[str, list[str]],
    oscillator_names,
    gain_names,
    terminal_names,
) -> list[tuple[str, str, str, str]]:
    """Oscillators that reach an output terminal without a gain stage.

    BFS from each oscillator (box ids in *box_lookup* order) over
    *signal_adj*, tracking whether a box in *gain_names* was passed. A
    neighbour missing from *box_lookup* is skipped; a terminal in
    *terminal_names* is reported when reached ungained and never traversed
    past. Returns ``(osc_id, osc_name, terminal_id, terminal_name)`` tuples
    in emission order.
    """
    hits: list[tuple[str, str, str, str]] = []

    osc_ids = [
        box_id for box_id, box in box_lookup.items()
        if walk.box_name(box) in oscillator_names
    ]

    for osc_id in osc_ids:
        osc_name = walk.box_name(box_lookup[osc_id])
        queue = deque([(osc_id, False)])  # (current_id, passed_through_gain)
        visited: set[tuple[str, bool]] = set()

        while queue:
            current_id, has_gain = queue.popleft()
            state = (current_id, has_gain)
            if state in visited:
                continue
            visited.add(state)

            for next_id in signal_adj.get(current_id, []):
                next_box = box_lookup.get(next_id)
                if not next_box:
                    continue
                next_name = walk.box_name(next_box)

                next_has_gain = has_gain or (next_name in gain_names)

                if next_name in terminal_names:
                    if not next_has_gain:
                        hits.append((osc_id, osc_name, next_id, next_name))
                    continue  # Don't traverse past the terminal

                queue.append((next_id, next_has_gain))

    return hits
