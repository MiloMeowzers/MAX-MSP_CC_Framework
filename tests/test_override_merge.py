"""quick-261013-e43 (Q11): overrides merge per port and match MAX-saved boxes.

Review findings (.planning/reviews/2026-10-11-repo-review.md):

* C6 -- ``overrides.json`` ``inlets``/``outlets`` arrays used to replace the
  base arrays whole, so a generator-written port (digest "Control output",
  type "") wiped the base digest, ``hot`` flag and type. They now merge per
  port: the override sets the port count, and each port replaces only the
  keys it sets (generator placeholders never replace base text).
* C7 -- override keys that are aliases (``r``, ``del``, ``v``) were silently
  ignored. Keys are now canonicalized through ``aliases.json``; an unknown or
  duplicate key fails at load.

Test hygiene: everything except ``requires_max`` classes uses only the repo
DB (CI runs Python 3.10 / 3.12 without Max). Tests never write to the repo;
tmp_path only.
"""

from __future__ import annotations

import copy
import json
import warnings
from pathlib import Path

import pytest

from src.maxpat.db_lookup import (
    DOMAIN_LOAD_ORDER,
    OVERRIDE_PLACEHOLDER_DIGESTS,
    ObjectDatabase,
    merge_override_ports,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_ROOT = REPO_ROOT / ".claude" / "max-objects"


@pytest.fixture(scope="module")
def db() -> ObjectDatabase:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return ObjectDatabase()


def _base_entries() -> dict:
    """Pre-override domain-file entries, rebuilt the way ObjectDatabase._load
    does it: DOMAIN_LOAD_ORDER, package subdirectories sorted, last wins."""
    base: dict = {}
    for domain in DOMAIN_LOAD_ORDER:
        if domain == "packages":
            pkg_root = DB_ROOT / "packages"
            if not pkg_root.is_dir():
                continue
            for pkg_dir in sorted(pkg_root.iterdir()):
                path = pkg_dir / "objects.json"
                if pkg_dir.is_dir() and path.exists():
                    base.update(json.loads(path.read_text()))
        else:
            path = DB_ROOT / domain / "objects.json"
            if path.exists():
                base.update(json.loads(path.read_text()))
    return base


def _override_objects() -> dict:
    return json.loads((DB_ROOT / "overrides.json").read_text()).get("objects", {})


def _aliases() -> dict:
    return json.loads((DB_ROOT / "aliases.json").read_text()).get("aliases", {})


# ---------------------------------------------------------------------------
# merge_override_ports (pure function)
# ---------------------------------------------------------------------------

_CTRL = {
    "id": 0, "type": "control", "signal": False,
    "digest": "Start", "hot": True, "name": "start", "optional": False,
}
_SIG = {"id": 1, "type": "signal", "signal": True, "digest": "Audio", "hot": True}


class TestMergeOverridePorts:

    def test_override_key_wins(self):
        out = merge_override_ports([_CTRL], [{"id": 0, "digest": "New text"}])
        assert out[0]["digest"] == "New text"

    def test_missing_keys_keep_base(self):
        out = merge_override_ports([_CTRL], [{"id": 0, "signal": False}])
        assert out[0]["hot"] is True
        assert out[0]["name"] == "start"
        assert out[0]["optional"] is False

    @pytest.mark.parametrize("placeholder", sorted(OVERRIDE_PLACEHOLDER_DIGESTS))
    def test_placeholder_digest_keeps_base(self, placeholder):
        out = merge_override_ports([_CTRL], [{"id": 0, "digest": placeholder}])
        assert out[0]["digest"] == "Start"

    @pytest.mark.parametrize("placeholder", sorted(OVERRIDE_PLACEHOLDER_DIGESTS))
    def test_placeholder_digest_fills_empty_base(self, placeholder):
        empty = dict(_CTRL, digest="")
        assert merge_override_ports([empty], [{"digest": placeholder}])[0]["digest"] == placeholder
        missing = {k: v for k, v in _CTRL.items() if not k == "digest"}
        assert merge_override_ports([missing], [{"digest": placeholder}])[0]["digest"] == placeholder

    def test_placeholder_description_keeps_base(self):
        base = {"id": 0, "description": "Real text"}
        out = merge_override_ports([base], [{"id": 0, "description": "Control output"}])
        assert out[0]["description"] == "Real text"

    def test_empty_type_on_control_base_keeps_base_type(self):
        out = merge_override_ports([_CTRL], [{"id": 0, "type": "", "signal": False}])
        assert out[0]["type"] == "control"

    def test_empty_type_on_signal_base_applies(self):
        out = merge_override_ports([_SIG], [{"id": 0, "type": "", "signal": False}])
        assert out[0]["type"] == ""
        assert out[0]["signal"] is False
        # A "signal" type alone (no signal: true) also counts as a signal port.
        typed = {"id": 0, "type": "signal/float", "digest": "x"}
        assert merge_override_ports([typed], [{"type": ""}])[0]["type"] == ""

    def test_non_empty_type_always_applies(self):
        out = merge_override_ports([_CTRL], [{"id": 0, "type": "int"}])
        assert out[0]["type"] == "int"

    def test_id_stub_inherits_base_port(self):
        base = [dict(_CTRL, id=i) for i in range(4)]
        out = merge_override_ports(base, [{"id": 0}, {"id": 1}, {"id": 2}, {"id": 3}])
        assert out[3] == base[3]

    def test_longer_override_appends_copies(self):
        extra = {"id": 1, "type": "", "signal": False, "digest": "Control output"}
        out = merge_override_ports([_CTRL], [{"id": 0}, extra])
        assert len(out) == 2
        assert out[1] == extra
        assert out[1] is not extra

    def test_shorter_override_truncates(self):
        out = merge_override_ports([_CTRL, _SIG], [{"id": 0}])
        assert len(out) == 1

    def test_inputs_not_mutated(self):
        base = [copy.deepcopy(_CTRL), copy.deepcopy(_SIG)]
        over = [{"id": 0, "digest": "x", "type": ""}, {"id": 1, "signal_role": "audio"}]
        base_before, over_before = copy.deepcopy(base), copy.deepcopy(over)
        out = merge_override_ports(base, over)
        out[0]["hot"] = "mutated"
        assert base == base_before
        assert over == over_before

    def test_non_dict_override_passes_through(self):
        assert merge_override_ports([_CTRL], ["junk"]) == ["junk"]
        assert merge_override_ports(["junk"], [{"id": 0}]) == [{"id": 0}]


# ---------------------------------------------------------------------------
# Real DB anchors: base metadata survives the merge
# ---------------------------------------------------------------------------

class TestRealDbRestore:

    def test_line_tilde(self, db):
        obj = db.lookup("line~")
        assert obj["inlets"][1]["digest"] == "Ramp Time"
        assert obj["inlets"][1]["hot"] is True
        assert obj["outlets"][0]["digest"] == "Output Ramp"

    def test_uzi(self, db):
        obj = db.lookup("uzi")
        assert obj["outlets"][1]["digest"] == "Done banging bang (carry)"
        assert obj["inlets"][0]["hot"] is True

    def test_coll(self, db):
        assert db.lookup("coll")["outlets"][0]["digest"] == "Data Contents"

    def test_no_placeholder_clobbers_base_digest(self, db):
        base = _base_entries()
        clobbered = []
        for name in sorted(db._overridden_objects):
            b = base.get(name)
            merged = db._objects.get(name)
            if not isinstance(b, dict) or merged is None:
                continue
            for side in ("inlets", "outlets"):
                bp, mp = b.get(side) or [], merged.get(side) or []
                for i in range(min(len(bp), len(mp))):
                    if not isinstance(bp[i], dict) or not isinstance(mp[i], dict):
                        continue
                    bd = bp[i].get("digest")
                    # Some domain files themselves carry placeholder text
                    # (e.g. jit.* "Control output"); keeping it is not a
                    # clobber, so only real base text counts.
                    real = isinstance(bd, str) and bd not in OVERRIDE_PLACEHOLDER_DIGESTS
                    if real and mp[i].get("digest") in OVERRIDE_PLACEHOLDER_DIGESTS:
                        clobbered.append((name, side, i))
        assert clobbered == []


# ---------------------------------------------------------------------------
# Alias canonicalization and data hygiene (C7)
# ---------------------------------------------------------------------------

class TestAliasCanonicalization:

    def test_alias_lookup_resolves_override(self, db):
        assert db.lookup("del") == db.lookup("delay")
        assert db.lookup("del")["name"] == "delay"
        assert db.is_overridden("del") is True
        assert db.is_overridden("value") is True

    def test_no_override_key_is_an_alias(self):
        aliases = _aliases()
        assert sorted(k for k in _override_objects() if k in aliases) == []

    def test_r_override_removed(self, db):
        assert "r" not in _override_objects()
        assert db.compute_io_counts("r", ["foo"]) == (0, 1)
        assert db.compute_io_counts("receive", []) == (1, 1)

    def test_no_stale_inactive_notes(self):
        stale = [
            k for k, v in _override_objects().items()
            if isinstance(v, dict) and "No base domain entry" in str(v.get("_note", ""))
        ]
        assert stale == []


def _make_db(tmp_path: Path, overrides: dict, aliases: dict | None = None) -> Path:
    root = tmp_path / "db"
    (root / "max").mkdir(parents=True)
    objects = {
        "metro": {
            "name": "metro",
            "inlets": [
                {"id": 0, "type": "control", "signal": False, "digest": "On/Off", "hot": True},
                {"id": 1, "type": "control", "signal": False, "digest": "Interval", "hot": False},
            ],
            "outlets": [{"id": 0, "type": "control", "signal": False, "digest": "Output"}],
        },
    }
    (root / "max" / "objects.json").write_text(json.dumps(objects))
    (root / "aliases.json").write_text(json.dumps({"aliases": aliases or {}}))
    (root / "overrides.json").write_text(
        json.dumps({"objects": overrides, "variable_io_rules": {}})
    )
    return root


class TestOverrideKeyFailFast:

    def test_unknown_key_raises(self, tmp_path):
        root = _make_db(tmp_path, {"nosuchobj": {"inlets": []}})
        with pytest.raises(ValueError, match="nosuchobj"):
            ObjectDatabase(root)

    def test_alias_plus_canonical_raises(self, tmp_path):
        root = _make_db(
            tmp_path,
            {"m": {"_note": "x"}, "metro": {"_note": "y"}},
            aliases={"m": "metro"},
        )
        with pytest.raises(ValueError) as exc:
            ObjectDatabase(root)
        assert "'m'" in str(exc.value) and "'metro'" in str(exc.value)

    def test_alias_only_key_applies_to_canonical(self, tmp_path):
        root = _make_db(
            tmp_path,
            {"m": {"outlets": [{"id": 0, "type": "", "signal": False, "digest": "Control output"}]}},
            aliases={"m": "metro"},
        )
        mdb = ObjectDatabase(root)
        assert mdb.is_overridden("metro")
        out = mdb.lookup("metro")["outlets"][0]
        assert out["digest"] == "Output"
        assert out["type"] == "control"
        assert mdb.lookup("metro")["inlets"][0]["hot"] is True


# ---------------------------------------------------------------------------
# Task 2 (C2): override I/O counts match MAX-saved help boxes
# ---------------------------------------------------------------------------

def _classes(db: ObjectDatabase, name: str, args: list) -> str:
    """'S' per signal/multichannelsignal outlet, 'c' per control outlet."""
    return "".join(
        "S" if t in ("signal", "multichannelsignal") else "c"
        for t in db.get_outlet_types(name, args)
    )


Q11_COUNT_TARGETS = (
    "coll", "spectroscope~", "index~", "poke~", "vst~", "thispoly~",
    "live.scope~", "gridmeter~", "bucket", "mousestate", "live.adsr~",
    "live.adsrui", "dict.view", "jit.polymovie", "jit.line", "mxj~",
    "mira.motion",
    # Task 3: their count fixes expose a wrong outlet-2 role, so the count
    # and the role are fixed together (rows in MAX_SAVED_ROLES).
    "retune~", "playlist~",
)

# The 16 C9 bundle names whose outlet signal class contradicted MAX-saved
# boxes (the live oracle's bundle type-mismatch names at 45f23b4).
Q11_ROLE_TARGETS = (
    "bp.arc.accum-2", "bp.arc.knob", "gen", "jweb~", "mc.adsr~",
    "mc.live.gain~", "mc.playlist~", "mc.route", "mc.selector~", "mc.stash~",
    "mcs.poly~", "mcs.tapout~", "pitchshift~", "sfrecord~", "stash~",
    "stretch~",
)

# Boxes saved by older Max versions with the pre-9 count. The oracle may
# still report these exact signatures and nothing else for the name.
OLDER_SIGNATURES = {
    "mousestate": "count args=0 max=1,5 db=1,10",
    "thispoly~": "count args=0 max=1,2 db=1,3",
    "index~": "count args=1 max=2,1 db=2,2",
    "poke~": "count args=1 max=3,0 db=3,1",
}

# (name, args, (inlets, outlets), outlet classes, roles or None, citation).
# Every row is a box MAX itself serialized.
MAX_SAVED_COUNTS = [
    ("coll", [], (1, 4), "cccc", None,
     "C74/help/max/coll.maxhelp (9.2.0) `coll` (1,4) [\"\" x4]; 169/169 boxes"),
    ("spectroscope~", [], (2, 1), "c", ("status",),
     "C74/help/msp/cross~.maxhelp (9.0.0) `spectroscope~` (2,1) [\"\"]; 57/57 bundle boxes"),
    ("index~", ["buf"], (2, 2), "SS", ("audio", "audio"),
     "C74/help/msp/index~.maxhelp (9.0.0) `index~ poke_index` (2,2) [signal, signal]"),
    ("poke~", ["buf"], (3, 1), "S", ("audio",),
     "C74/help/max/gen.maxhelp (9.1.0) `poke~ window` (3,1) [signal]"),
    ("vst~", [], (2, 8), "SScccccc",
     ("audio", "audio", "list", "data", "float", "status", "status", "status"),
     "C74/help/msp/mc.midiplayer~.maxhelp (9.0.0) `vst~` (2,8) "
     "[signal, signal, \"\", list, int, \"\", \"\", \"\"]"),
    ("thispoly~", [], (1, 3), "ccc", ("data", "status", "float"),
     "C74/help/msp/thispoly~.maxhelp (9.0.5) `thispoly~ @automute 1` (1,3) [int, int, int]"),
    ("live.scope~", [], (2, 1), "c", None,
     "C74/help/m4l/live.routing.maxhelp (9.0.0) `live.scope~` (2,1) [bang]; 224 boxes"),
    ("gridmeter~", [], (1, 1), "S", ("audio",),
     "C74/help/msp/gridmeter~.maxhelp (9.0.0) `gridmeter~` (1,1) [multichannelsignal]"),
    ("bucket", [], (1, 1), "c", None,
     "C74/help/max/anal.maxhelp (9.0.0) `bucket` (1,1) [\"\"]"),
    ("bucket", ["4"], (1, 4), "cccc", None,
     "C74/help/max/bucket.maxhelp `bucket 4 1` (1,4)"),
    ("mousestate", [], (1, 10), "c" * 10, None,
     "C74/help/max/mousestate.maxhelp (9.0.5) `mousestate` (1,10) [int x7, float, float, list]"),
    ("live.adsr~", [], (11, 3), "SSc", ("audio", "audio", "status"),
     "C74/packages/maxforlive-elements/help/live.adsr~.maxhelp (8.2.0) "
     "`live.adsr~ 600. 100. 0.5 1000.` (11,3) [signal, signal, \"\"]"),
    ("live.adsrui", [], (10, 10), "c" * 10, ("status",) * 10,
     "C74/packages/maxforlive-elements/help/live.adsrui.maxhelp (8.5.6) `live.adsrui` (10,10)"),
    ("dict.view", [], (1, 0), "", None,
     "C74/help/max/dict.pack.maxhelp (9.0.0) `dict.view` (1,0) []; 70 bundle boxes"),
    ("jit.polymovie", [], (1, 3), "ccc", ("data", "status", "status"),
     "C74/packages/Jitter Tools/help/jit.polymovie.maxhelp (9.1.0) "
     "`jit.polymovie @vol 0` (1,3) [jit_matrix, \"\", \"\"]"),
    ("jit.line", [], (1, 2), "cc", ("status", "status"),
     "C74/packages/Jitter Tools/help/jit.fx-help/jit.fx.camera.maxhelp (9.1.0) "
     "`jit.line` (1,2) [\"\", \"\"]"),
    ("mxj~", ["noise"], (1, 2), "Sc", ("audio", "status"),
     "C74/packages/max-mxj/help/mxj~.maxhelp (7.0.0) `mxj~ noise` (1,2) [signal, \"\"]"),
    ("mira.motion", [], (1, 1), "c", ("status",),
     "C74/packages/mira/help/mira.motion.maxhelp (7.3.1) `mira.motion` (1,1) [\"\"]"),
]


def _row_id(row) -> str:
    return row[0] + ("(" + " ".join(row[1]) + ")" if row[1] else "")


def _assert_row(db, name, args, counts, classes, roles):
    assert db.compute_io_counts(name, list(args)) == counts
    assert _classes(db, name, list(args)) == classes
    if roles is not None:
        got = tuple(db.get_signal_role(name, i, list(args)) for i in range(counts[1]))
        assert got == tuple(roles)


class TestMaxSavedCounts:

    @pytest.mark.parametrize(
        "name,args,counts,classes,roles,citation", MAX_SAVED_COUNTS,
        ids=[_row_id(r) for r in MAX_SAVED_COUNTS],
    )
    def test_matches_max_saved_box(self, db, name, args, counts, classes, roles, citation):
        _assert_row(db, name, args, counts, classes, roles)

    def test_every_target_has_a_row(self):
        rows = {r[0] for r in MAX_SAVED_COUNTS} | {r[0] for r in MAX_SAVED_ROLES}
        assert set(Q11_COUNT_TARGETS) <= rows

    def test_live_adsr_inlets(self, db):
        inlets = db.lookup("live.adsr~")["inlets"]
        assert len(inlets) == 11
        for i in range(5):
            assert inlets[i]["signal"] is True and inlets[i]["type"] == "signal/float"
        for i in range(5, 11):
            assert inlets[i]["signal"] is False

    def test_coll_single_hot_inlet(self, db):
        inlets = db.lookup("coll")["inlets"]
        assert len(inlets) == 1
        assert inlets[0]["digest"] == "Messages and data"
        assert inlets[0]["hot"] is True

    def test_dict_view_has_no_outlets(self, db):
        assert db.lookup("dict.view")["outlets"] == []

    def test_mousestate_stub_inherits_base_digest(self, db):
        assert db.lookup("mousestate")["outlets"][9]["digest"].startswith("Mousewheel Flags")

    def test_role_ports_carry_no_signal_key(self):
        ov = _override_objects()
        both = [
            (name, p.get("id"))
            for name in Q11_COUNT_TARGETS
            for p in ov[name].get("outlets", [])
            if "signal_role" in p and "signal" in p
        ]
        assert both == []


# ---------------------------------------------------------------------------
# Task 3 (C9): outlet signal roles match MAX-saved help boxes
# ---------------------------------------------------------------------------

MAX_SAVED_ROLES = [
    ("retune~", ["440"], (3, 5), "SSSSc", ("audio",) * 4 + ("list",),
     "C74/help/msp/retune~.maxhelp (9.0.0) `retune~ 440` (3,5) [signal x4, list]"),
    ("playlist~", [], (1, 5), "SSScc", ("audio", "audio", "audio", "status", "data"),
     "C74/help/max/chooser.maxhelp (9.0.0) `playlist~` (1,5) "
     "[signal, signal, signal, \"\", dictionary]; 25 bundle boxes"),
    ("bp.arc.accum-2", ["1", "-1000", "1000"], (2, 1), "c", ("status",),
     "C74/packages/BEAP/Help/bp.Granular.maxhelp (8.0.6) "
     "`bp.arc.accum-2 1 -1000 1000` (2,1) [\"\"]; 12 boxes"),
    ("bp.arc.knob", ["1", "0", "bandwidth"], (3, 1), "c", ("status",),
     "C74/packages/BEAP/Help/bp.Granular.maxhelp (8.0.6) "
     "`bp.arc.knob 1 0 bandwidth` (3,1) [\"\"]; 12 boxes"),
    ("gen", [], (2, 1), "c", ("float",),
     "C74/help/max/gen.maxhelp (9.1.0) `gen` (2,1) [float]; all 21 gen boxes"),
    ("jweb~", [], (1, 3), "SSc", ("audio", "audio", "status"),
     "C74/help/msp/jweb~.maxhelp (9.0.0) `jweb~` (1,3) [signal, signal, \"\"]; 1 box"),
    ("mc.adsr~", ["10", "150", "0", "100"], (5, 5), "SSccc",
     ("audio", "audio", "status", "status", "status"),
     "C74/help/max/mc.assign.maxhelp (9.0.0) `mc.adsr~ 10 150 0 100 @chans 6` (5,5) "
     "[multichannelsignal x2, \"\", \"\", \"\"]"),
    ("mc.live.gain~", [], (1, 4), "Sccc", ("audio", "status", "float", "float"),
     "C74/help/max/mc.assign.maxhelp (9.0.0) `mc.live.gain~` (1,4) "
     "[multichannelsignal, \"\", float, list]; 109 boxes"),
    ("mc.playlist~", [], (1, 4), "SScc", ("audio", "audio", "status", "list"),
     "C74/help/msp/matrix~.maxhelp (9.0.0) `mc.playlist~` (1,4) "
     "[multichannelsignal, signal, \"\", dictionary]; 19 boxes"),
    ("mc.route", ["4"], (2, 4), "cccc", ("status", "status", None, None),
     "C74/help/msp/mc.pack~.maxhelp (9.0.0) `mc.route 4` (2,4) [\"\" x4]; 11 boxes"),
    ("mc.selector~", ["2", "1"], (3, 1), "S", ("audio",),
     "C74/help/msp/stash~.maxhelp (9.0.0) `mc.selector~ 2 1 @ramptime 100` (3,1) "
     "[multichannelsignal]"),
    ("mc.stash~", [], (4, 2), "SS", ("audio", "audio"),
     "C74/help/msp/stash~.maxhelp (9.0.0) `mc.stash~` (4,2) [multichannelsignal x2]"),
    ("mcs.poly~", ["mcout_subpatcher", "1"], (1, 1), "S", ("audio",),
     "C74/help/msp/out~.maxhelp (9.0.5) `mcs.poly~ mcout_subpatcher 1` (1,1) "
     "[multichannelsignal]"),
    ("mcs.tapout~", ["100", "200", "300"], (3, 1), "S", ("audio",),
     "C74/help/msp/tapout~.maxhelp (9.0.0) `mcs.tapout~ 100 200 300` (3,1) "
     "[multichannelsignal]"),
    ("pitchshift~", ["2"], (3, 3), "SSc", ("audio", "audio", "status"),
     "C74/help/msp/pitchshift~.maxhelp (9.0.0) `pitchshift~ 2` (3,3) [signal, signal, \"\"]"),
    ("sfrecord~", ["2"], (2, 1), "S", ("audio",),
     "C74/help/msp/adoutput~.maxhelp (9.0.0) `sfrecord~ 2` (2,1) [signal]"),
    ("stash~", [], (4, 2), "SS", ("audio", "audio"),
     "C74/help/msp/stash~.maxhelp (9.0.0) `stash~` (4,2) [signal, signal]; 7 boxes"),
    ("stretch~", ["stretchy"], (1, 2), "cc", ("float", "trigger"),
     "C74/help/msp/stretch~.maxhelp (9.0.0) `stretch~ stretchy` (1,2) [float, bang]; 2 boxes"),
]


class TestMaxSavedRoles:

    @pytest.mark.parametrize(
        "name,args,counts,classes,roles,citation", MAX_SAVED_ROLES,
        ids=[_row_id(r) for r in MAX_SAVED_ROLES],
    )
    def test_matches_max_saved_box(self, db, name, args, counts, classes, roles, citation):
        _assert_row(db, name, args, counts, classes, roles)

    def test_rows_cover_role_targets(self):
        assert {r[0] for r in MAX_SAVED_ROLES} == set(Q11_ROLE_TARGETS) | {"retune~", "playlist~"}

    def test_role_ports_carry_no_signal_key(self):
        ov = _override_objects()
        both = [
            (name, p.get("id"))
            for name in Q11_ROLE_TARGETS + ("retune~", "playlist~")
            for p in ov[name].get("outlets", [])
            if "signal_role" in p and "signal" in p
        ]
        assert both == []


# ---------------------------------------------------------------------------
# Outlet downgrade guard (Q2 OQ1-A hand-off)
# ---------------------------------------------------------------------------

def _outlet_flips(db: ObjectDatabase) -> list:
    """Every (name, i) where the base outlet is signal, the MERGED outlet is
    control, and the override port has no curated signal_role. Computed on
    the merged DB so ``{"id": N}`` stubs and roles count. Indices beyond
    either the base or the override array are not flips."""
    base = _base_entries()
    aliases = _aliases()
    flips = []
    for key, entry in _override_objects().items():
        if key.startswith("_") or not isinstance(entry, dict):
            continue
        ov_outlets = entry.get("outlets")
        if not isinstance(ov_outlets, list):
            continue
        name = aliases.get(key, key)
        base_outlets = (base.get(name) or {}).get("outlets") or []
        merged = db._objects[name].get("outlets") or []
        for i in range(min(len(base_outlets), len(ov_outlets))):
            b, o, m = base_outlets[i], ov_outlets[i], merged[i]
            if not all(isinstance(x, dict) for x in (b, o, m)):
                continue
            if b.get("signal") is True and not m.get("signal") and "signal_role" not in o:
                flips.append((name, i))
    return sorted(flips)


_GEN_REASON = (
    "Gen operator: MAX saves outlettype \"\" for every box inside a gen "
    "patcher; the help-io oracle skips gen internals (Q2 OQ1-A, 2026-10-12)"
)
_GEN_FLIP_OPERATORS = (
    "bool", "buffer", "channels", "constant", "dcblock", "delta", "dim",
    "fixnan", "fold", "fract", "history", "hypot", "isnan", "latch", "min",
    "mix", "mstosamps", "noise", "or", "phasewrap", "phasor", "pi", "radians",
    "sah", "samplerate", "sampstoms", "selector", "train", "triangle", "trunc",
    "wrap",
)

# Reviewed exceptions: base says signal, overrides say control, on evidence.
_OUTLET_DOWNGRADE_ALLOWLIST: dict = {
    ("pong", 0): (
        "MAX saves `pong 0. 1. @mode fold` with outlettype [\"\"] "
        "(C74/help/max/pong.maxhelp, 9.0.0)"
    ),
    ("buffer~", 0): (
        "MAX saves buffer~ outlettype [\"float\", \"bang\"] in 275+ boxes, "
        "e.g. C74/help/max/array.tobuffer.maxhelp"
    ),
    ("buffer~", 1): (
        "MAX saves buffer~ outlettype [\"float\", \"bang\"] in 275+ boxes, "
        "e.g. C74/help/max/array.tobuffer.maxhelp"
    ),
    ("jit.peek~", 1): (
        "MAX saves jit.peek~ outlettype [\"signal\", \"\"] (jit.peek~.maxhelp)"
    ),
    ("jit.poke~", 0): (
        "MAX saves jit.poke~ outlettype [\"\"] (jit.poke~.maxhelp)"
    ),
    ("jit.release~", 1): (
        "MAX saves jit.release~ outlettype [\"signal\", \"\"] (jit.release~.maxhelp)"
    ),
    ("amxd~", 2): (
        "MAX saves amxd~ outlettype [\"signal\", \"signal\", \"\", \"\"] "
        "(C74/help/max/autopattr.maxhelp)"
    ),
    ("amxd~", 3): (
        "MAX saves amxd~ outlettype [\"signal\", \"signal\", \"\", \"\"] "
        "(C74/help/max/autopattr.maxhelp)"
    ),
    ("live.modulate~", 0): (
        "MAX saves live.modulate~ outlettype [\"\"] "
        "(C74/help/m4l/live.modulate~.maxhelp, 9.1.3)"
    ),
}
_OUTLET_DOWNGRADE_ALLOWLIST.update({(op, 0): _GEN_REASON for op in _GEN_FLIP_OPERATORS})


class TestOutletDowngradeGuard:

    def test_allowlist_is_the_q2_handoff(self):
        assert len(_OUTLET_DOWNGRADE_ALLOWLIST) == 40
        assert len({k[0] for k in _OUTLET_DOWNGRADE_ALLOWLIST}) == 38

    def test_no_unreviewed_outlet_downgrades(self, db):
        unreviewed = [f for f in _outlet_flips(db) if f not in _OUTLET_DOWNGRADE_ALLOWLIST]
        assert unreviewed == [], (
            f"{len(unreviewed)} override outlet(s) turn a base signal outlet "
            f"into control without a curated signal_role: {unreviewed}"
        )

    def test_allowlist_entries_are_live_and_reasoned(self, db):
        live = set(_outlet_flips(db))
        for key, reason in _OUTLET_DOWNGRADE_ALLOWLIST.items():
            assert key in live, f"stale allowlist entry {key}: not a live flip"
            assert isinstance(reason, str) and reason.strip(), (
                f"allowlist entry {key} has no reason"
            )


# ---------------------------------------------------------------------------
# Live oracle (requires the Max bundle)
# ---------------------------------------------------------------------------

BASELINE = REPO_ROOT / "tests" / "fixtures" / "help_io_baseline.json"


@pytest.fixture(scope="module")
def live_section() -> dict:
    import tools.audit_db as audit_db
    from tests.conftest import MAX_APP_PATH
    from tools import help_io

    envelope = audit_db.run_help_io(max_app=MAX_APP_PATH)
    section = envelope["help_io"]
    assert section["available"], section.get("reason")
    return help_io.build_baseline(section)


def _skip_if_stale(live_section: dict) -> None:
    from tools import help_io

    committed = json.loads(BASELINE.read_text())
    stale = help_io.diff_baselines(committed, live_section)["stale_sources"].get("bundle")
    if stale is not None:
        pytest.skip(
            f"help-io baseline recorded against Max {stale['baseline']}, "
            f"installed {stale['live']}"
        )


@pytest.mark.requires_max
class TestOracleQ11:
    """Q11 targets agree with MAX-saved bundle boxes (older-version boxes
    excepted by exact signature)."""

    def test_count_targets_clean_in_bundle(self, live_section):
        _skip_if_stale(live_section)
        bundle = live_section["names"].get("bundle", {})
        bad = {}
        for name in Q11_COUNT_TARGETS:
            entry = bundle.get(name)
            if entry is None:
                continue
            allowed = {OLDER_SIGNATURES[name]} if name in OLDER_SIGNATURES else set()
            if not set(entry["signatures"]) <= allowed or entry["type_mismatches"]:
                bad[name] = entry["signatures"]
        assert not bad, bad

    def test_role_targets_clean_in_bundle(self, live_section):
        _skip_if_stale(live_section)
        bundle = live_section["names"].get("bundle", {})
        bad = {
            name: bundle[name]["signatures"]
            for name in Q11_ROLE_TARGETS
            if bundle.get(name, {}).get("type_mismatches", 0)
        }
        assert not bad, bad

    def test_bundle_has_no_type_mismatches(self, live_section):
        _skip_if_stale(live_section)
        bundle = live_section["names"].get("bundle", {})
        assert sorted(n for n, e in bundle.items() if e["type_mismatches"]) == []
