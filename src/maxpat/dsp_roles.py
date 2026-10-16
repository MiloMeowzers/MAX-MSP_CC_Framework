"""DB-driven DSP roles: gain stages, output terminals and chain terminals.

Fix-plan Q26 / review E6 (planner decision PD-5). validation.py (Layer 4
unterminated-chain and gain-staging rules) and the DSP critic
(``dsp_critic``) take their sets from here, so the two agree on what
attenuates a signal and where a signal chain may end.

The object database has no "gain stage" or "terminal" field, and the role
cannot be derived from I/O alone: ``plugout~.maxref.xml`` documents two
signal pass-thru outlets, so "a signal sink with no audio outlet" would miss
it. This module therefore holds a small documented base vocabulary and lets
the DB decide the rest. Each base name and its ``mc.`` counterpart is kept
only when:

* ``db.lookup(name)`` is a dict (the object exists in this DB);
* at least one of its inlets has ``signal`` True (it takes audio);
* ``db.get_effective_restrictions(name)`` is not a non-empty subset of
  ``{"rnbo", "gen"}`` (it can be used in a Max patcher, CLAUDE.md Rule #1).

A DB re-sync that adds or drops an mc.* variant (``mc.plugout~`` is absent
today) changes the sets with no code edit. Under the repo DB:

* gain stages: ``*~``, ``mc.*~``, ``gain~``, ``mc.gain~``, ``live.gain~``,
  ``mc.live.gain~``;
* output terminals: ``dac~``, ``mc.dac~``, ``ezdac~``, ``mc.ezdac~``,
  ``plugout~``;
* chain terminals: the output terminals plus ``send~``, ``mc.send~``,
  ``out~``, ``mc.out~``.

``db=None`` uses one process-wide cached ObjectDatabase (the
``hooks._gate_db`` precedent). Callers use these module-qualified
(``dsp_roles.gain_stage_names(db)``) so tests can monkeypatch them.
"""

from __future__ import annotations

import functools

# Objects that attenuate a signal (Rule: gain staging before an output).
GAIN_STAGE_BASES = ("*~", "gain~", "live.gain~")

# Objects where audio leaves the patch for the hardware or the host.
OUTPUT_TERMINAL_BASES = ("dac~", "ezdac~", "plugout~")

# Objects where a signal chain legitimately ends without a downstream cord:
# it is routed elsewhere by name or leaves an RNBO / poly~ patcher.
ROUTE_TERMINAL_BASES = ("send~", "out~")

_NON_MAX_SCOPES = frozenset({"rnbo", "gen"})


@functools.lru_cache(maxsize=1)
def _default_db():
    """One process-wide ObjectDatabase for ``db=None`` callers (cached)."""
    from src.maxpat.db_lookup import ObjectDatabase

    return ObjectDatabase()


def _takes_signal(obj: dict) -> bool:
    inlets = obj.get("inlets")
    if not isinstance(inlets, list):
        return False
    return any(isinstance(i, dict) and i.get("signal") is True for i in inlets)


def _usable_in_max(db, name: str) -> bool:
    try:
        restrictions = db.get_effective_restrictions(name)
    except Exception:
        return True
    if not isinstance(restrictions, (list, tuple, set, frozenset)):
        return True
    scopes = set(restrictions)
    return not (scopes and scopes <= _NON_MAX_SCOPES)


def _derive(bases, db) -> frozenset:
    if db is None:
        db = _default_db()
    names = set()
    for base in bases:
        for name in (base, "mc." + base):
            try:
                obj = db.lookup(name)
            except Exception:
                obj = None
            if not isinstance(obj, dict):
                continue
            if not _takes_signal(obj) or not _usable_in_max(db, name):
                continue
            names.add(name)
    return frozenset(names)


def gain_stage_names(db=None) -> frozenset:
    """Names of the gain stages (``GAIN_STAGE_BASES`` and mc.* variants) in *db*."""
    return _derive(GAIN_STAGE_BASES, db)


def output_terminal_names(db=None) -> frozenset:
    """Names of the output terminals (``OUTPUT_TERMINAL_BASES`` and mc.*) in *db*."""
    return _derive(OUTPUT_TERMINAL_BASES, db)


def chain_terminal_names(db=None) -> frozenset:
    """Output terminals plus route terminals (``send~``, ``out~`` and mc.*)."""
    return output_terminal_names(db) | _derive(ROUTE_TERMINAL_BASES, db)
