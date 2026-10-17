"""Curated waveguide topology library for the DSP pre-flight simulator.

Per CONTEXT.md D-01: two topologies cover the bassoon shapes -- `reed_bore`
(bore + McIntyre-Woodhouse reed; v0.3.x ancestor) and
`reed_bore_post_radiation` (the genrun-parity-tested port of the shipped
patches/bassoon-model/generated/bassoon.gendsp loop, with the post-loop reed
BPF, body formant and bell LPF).

Each topology class declares its parameter surface as a class-level
`PARAMS` frozenset (Q25 / H4). run_simulation(topology=...) rejects any
sweep_param or params key outside it with TopologyError before rendering,
so a misspelled param can no longer be silently ignored and pass.

`bore_only` was removed in Q25: under constant drive it settled to DC at
every setting (the old detector read 4009 Hz), an impulse ring-down mostly
fell below the amplitude floor, and a pitch-locked drive would measure the
drive rather than the bore. None of those is a meaningful pre-flight.

The custom-mirror escape hatch (run_simulation(mirror=callable)) covers
off-catalogue patches; this catalog covers the canonical bassoon path.

Usage:
    from src.maxpat.dsp_sim.topologies import get_topology, TOPOLOGIES

    cls = get_topology("reed_bore_post_radiation")
    stepper = cls(sample_rate=44100, params={"freq": 220.0, "breath": 0.6, ...})
    out = stepper.step(220.0, 0.6)
"""

from __future__ import annotations

from src.maxpat.dsp_sim.topologies.reed_bore import ReedBore
from src.maxpat.dsp_sim.topologies.reed_bore_post_radiation import (
    ReedBorePostRadiation,
)
from src.maxpat.dsp_sim.runner import TopologyError


TOPOLOGIES: dict[str, type] = {
    "reed_bore": ReedBore,
    "reed_bore_post_radiation": ReedBorePostRadiation,
}


def get_topology(name: str) -> type:
    """Return the topology class for `name` or raise TopologyError.

    Args:
        name: Registry key -- 'reed_bore' or 'reed_bore_post_radiation'
            ('bore_only' was removed in Q25 and now raises).

    Returns:
        The topology class (instantiate with sample_rate + params). Its
        `PARAMS` frozenset is the declared parameter surface.

    Raises:
        TopologyError: If `name` is not a registered topology. Matches the
            D-01 contract used by run_simulation's _resolve_stepper_factory.
    """
    if name not in TOPOLOGIES:
        known = ", ".join(sorted(TOPOLOGIES.keys()))
        raise TopologyError(f"unknown topology '{name}'. Known: {known}")
    return TOPOLOGIES[name]


__all__ = [
    "TOPOLOGIES",
    "get_topology",
    "TopologyError",
    "ReedBore",
    "ReedBorePostRadiation",
]
