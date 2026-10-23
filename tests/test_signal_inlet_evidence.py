"""CR-01 (review-validation, quick 261022-ud6 WP1): signal-accepting inlets
the DB marked control-only.

Q1 / Q7 turned "Signal outlet to control-only inlet" from a silent strip
into a save-gate blocker, so every DB inlet wrongly marked control refuses a
valid new patch. Evidence for each correction (Max 9.2.0 bundle):

* idioms.json -- the 25 signal cords MAX's own help patches ship into
  inlets the DB had as control-only (``mc.sum~`` 0, ``mc.selector~`` 2,
  ``mc.tapout~`` / ``mcs.tapout~`` 1-2, ``phasor~`` 1, ``sig~`` 0,
  ``live.remote~`` 0, ``mc.bands~`` 0, ``mcp.record~`` 0,
  ``windowed-fft~`` 0, ``jit.cellblock`` 0);
* refpages -- ``phasor~`` inlet 1 "Trigger Reset (signal)", ``jit.vcr``
  inlets 0-1 "MSP audio in", ``mc.selector~`` inlets 1..N signal,
  ``pitchshift~`` factor inlet type Signal;
* MAX-saved boxes -- ``record~ this 2`` (C74/media/legacy-tutorials/
  msp-tut/mypvoc2~.maxpat) ships ``phasewrap~ -> record~ this 2`` inlet 1:
  ``record~ buf N`` is N signal inlets + start + end (``trailing_inlets``).

Guards keep the gaps from coming back: no placeholder control inlet on a
``~`` object without a reviewed reason, no shipped signal idiom landing on
a control-only DB inlet, and the idiom exemption also covers an inlet any
shipped signal cord feeds (not only the exact source name).
"""

from __future__ import annotations

import copy

import pytest

from src.maxpat.db_lookup import ObjectDatabase
from src.maxpat.patcher import Patcher
from src.maxpat.validation import (
    _inlet_accepts_signal,
    has_blocking_errors,
    validate_patch,
)
from tests.test_validation import _make_box, _make_line, _make_patch_dict


@pytest.fixture(scope="module")
def db():
    return ObjectDatabase()


def _box(text):
    return {"maxclass": "newobj", "text": text}


def _conn(results):
    return [r for r in results if r.layer == "connections"]


def _proposed(results):
    return [r for r in results if r.proposed_removal is not None]


# ---------------------------------------------------------------------------
# The review's failure scenario: a Patcher-built MC mixdown
# ---------------------------------------------------------------------------

class TestMcMixdownSaves:

    def _build(self):
        p = Patcher()
        osc = p.add_box("mc.cycle~", ["440"])
        g = p.add_box("mc.*~", ["0.2"])
        s = p.add_box("mc.sum~", [])
        d = p.add_box("dac~", [])
        p.add_connection(osc, 0, g, 0)
        p.add_connection(g, 0, s, 0)
        p.add_connection(s, 0, d, 0)
        p.add_connection(s, 0, d, 1)
        return p

    def test_no_connection_findings(self, db):
        results = validate_patch(self._build().to_dict(), db=db)
        assert _conn(results) == [], [str(r) for r in _conn(results)]
        assert not has_blocking_errors(_proposed(results))

    def test_save_gate_accepts_new_file(self, tmp_path):
        from src.maxpat.hooks import save_patch_roundtrip

        path = tmp_path / "mcsum-test.maxpat"
        with pytest.warns(Warning):  # not a patches/<project> path: no commit
            save_patch_roundtrip(self._build().to_dict(), str(path))
        assert path.exists()


# ---------------------------------------------------------------------------
# Cords MAX accepts (review table + sweep)
# ---------------------------------------------------------------------------

_CYC = ("cycle~ 440", 2, 1, ["signal"])

# (id, dst_text, dst_numinlets, dst_numoutlets, dst_inlet)
_VALID = [
    ("mc.selector~-2", "mc.selector~ 2", 3, 1, 2),
    ("mc.tapout~-1", "mc.tapout~ 100 200", 2, 2, 1),
    ("mcs.tapout~-1", "mcs.tapout~ 100 200", 2, 1, 1),
    ("phasor~-1", "phasor~ 4", 2, 1, 1),
    ("sig~-0", "sig~ 660", 1, 1, 0),
    ("record~-ch2", "record~ buf 2", 4, 1, 1),
    ("record~-ch1", "record~ buf 2", 4, 1, 0),
    ("mc.sum~-0", "mc.sum~", 1, 1, 0),
    ("mc.bands~-0", "mc.bands~ 16", 5, 3, 0),
    ("live.remote~-0", "live.remote~", 2, 1, 0),
    ("windowed-fft~-0", "windowed-fft~ 1024", 2, 2, 0),
    ("mcp.record~-0", "mcp.record~ ted 1", 3, 1, 0),
    ("jit.vcr-0", "jit.vcr 640 480", 3, 2, 0),
    ("jit.vcr-1", "jit.vcr 640 480", 3, 2, 1),
    ("pitchshift~-factor", "pitchshift~ 2", 3, 3, 2),
    ("sfrecord~-ch8", "sfrecord~ 8", 8, 1, 7),
    ("jit.catch~-ch7", "jit.catch~ 7", 7, 2, 6),
]


def _cord_patch(src, dst_text, dst_in, dst_out, dst_inlet):
    s_text, s_in, s_out, s_ot = src
    return _make_patch_dict(
        boxes=[
            _make_box("obj-1", text=s_text, numinlets=s_in, numoutlets=s_out,
                      outlettype=s_ot),
            _make_box("obj-2", text=dst_text, numinlets=dst_in,
                      numoutlets=dst_out, outlettype=[""] * dst_out or None),
        ],
        lines=[_make_line("obj-1", 0, "obj-2", dst_inlet)],
    )


class TestSignalCordsMaxAccepts:

    @pytest.mark.parametrize("case", _VALID, ids=[c[0] for c in _VALID])
    def test_cycle_into_inlet_not_proposed(self, db, case):
        _id, text, n_in, n_out, inlet = case
        results = validate_patch(_cord_patch(_CYC, text, n_in, n_out, inlet), db=db)
        assert _proposed(results) == [], [str(r) for r in results]

    def test_click_into_phasor_reset(self, db):
        """The idiom exemption used to pass `<~ -> phasor~ 1` only."""
        src = ("click~", 1, 1, ["signal"])
        results = validate_patch(_cord_patch(src, "phasor~ 4", 2, 1, 1), db=db)
        assert _proposed(results) == [], [str(r) for r in results]


class TestRecordInletLayout:
    """record~ buf N: N signal inlets, then start / end points (trailing 2)."""

    @pytest.mark.parametrize("text,inlet,accepts", [
        ("record~ buf", 0, True),
        ("record~ buf", 1, False),
        ("record~ buf", 2, False),
        ("record~ buf 2", 0, True),
        ("record~ buf 2", 1, True),
        ("record~ buf 2", 2, False),
        ("record~ buf 2", 3, False),
        ("record~ buf 4", 3, True),
        ("record~ buf 4", 4, False),
        ("record~ buf 4", 5, False),
    ])
    def test_inlet_accepts_signal(self, db, text, inlet, accepts):
        assert _inlet_accepts_signal(_box(text), inlet, db) is accepts

    def test_anchor_signal_into_start_point_still_proposed(self, db):
        results = validate_patch(_cord_patch(_CYC, "record~ buf 2", 4, 1, 2), db=db)
        assert [r.proposed_removal for r in _proposed(results)] == [
            ("obj-1", 0, "obj-2", 2),
        ]

    def test_resolve_inlet_api(self, db):
        assert db.resolve_inlet("record~", 1, ["buf", "2"])["signal"] is True
        assert db.resolve_inlet("record~", 2, ["buf", "2"])["digest"].startswith(
            "Recording Start"
        )
        assert db.resolve_inlet("record~", 1, ["buf"])["digest"].startswith(
            "Recording Start"
        )
        assert db.resolve_inlet("record~", 9, ["buf", "2"]) is None


class TestAnchorsStillFlagged:

    def test_signal_into_print_still_proposed(self, db):
        results = validate_patch(_cord_patch(_CYC, "print", 1, 0, 0), db=db)
        assert len(_proposed(results)) == 1

    def test_signal_into_windowed_fft_window_inlet_proposed(self, db):
        """windowed-fft~ inlet 1 feeds a message box in the abstraction."""
        results = validate_patch(
            _cord_patch(_CYC, "windowed-fft~ 1024", 2, 2, 1), db=db)
        assert len(_proposed(results)) == 1


# ---------------------------------------------------------------------------
# Idiom exemption keyed by destination inlet (cause 3)
# ---------------------------------------------------------------------------

class TestIdiomDestinationExemption:

    def _db_with(self, db, idioms):
        clone = copy.copy(db)
        clone._objects = copy.deepcopy(db._objects)
        clone._objects["phasor~"]["inlets"][1] = {
            "id": 1, "type": "float", "signal": False, "digest": "Phase",
        }
        clone._idioms = set(idioms)
        clone._idiom_signal_inlets = None
        return clone

    def test_shipped_signal_cord_from_other_source_exempts_inlet(self, db):
        fake = self._db_with(db, {("<~", 0, "signal", "phasor~", 1)})
        src = ("click~", 1, 1, ["signal"])
        results = validate_patch(_cord_patch(src, "phasor~ 4", 2, 1, 1), db=fake)
        assert _proposed(results) == []

    def test_without_idiom_inlet_is_flagged(self, db):
        fake = self._db_with(db, set())
        src = ("click~", 1, 1, ["signal"])
        results = validate_patch(_cord_patch(src, "phasor~ 4", 2, 1, 1), db=fake)
        assert len(_proposed(results)) == 1

    def test_control_idiom_does_not_exempt_signal(self, db):
        fake = self._db_with(db, {("flonum", 0, "control", "phasor~", 1)})
        src = ("click~", 1, 1, ["signal"])
        results = validate_patch(_cord_patch(src, "phasor~ 4", 2, 1, 1), db=fake)
        assert len(_proposed(results)) == 1


# ---------------------------------------------------------------------------
# DB guards
# ---------------------------------------------------------------------------

def _accepts(port: dict) -> bool:
    return bool(port.get("signal")) or "signal" in (port.get("type") or "").lower()


class TestNoShippedSignalIdiomIntoControlInlet:

    def test_every_signal_idiom_lands_on_a_signal_accepting_inlet(self, db):
        bad = []
        for (src, outlet, cls, dst, inlet) in sorted(db._idioms):
            if cls != "signal":
                continue
            obj = db.lookup(dst)
            if obj is None or inlet >= len(obj.get("inlets", [])):
                continue
            if not _accepts(obj["inlets"][inlet]):
                bad.append((dst, inlet, src, outlet))
        assert bad == [], bad


# Reviewed placeholder inlets (type "", digest "", signal False) on `~`
# objects: control on evidence. Anything else must be filled in.
_PLACEHOLDER_CONTROL_REVIEWED: dict[tuple[str, int], str] = {
    ("pfft~", 1): "pfft~ is a container (validation never type-checks a cord into it); its inlets come from the loaded patcher",
}


class TestNoUnreviewedPlaceholderInlets:

    def _placeholders(self, db):
        found = []
        for name, obj in sorted(db._objects.items()):
            if not name.endswith("~"):
                continue
            for i, port in enumerate(obj.get("inlets", [])):
                if (
                    isinstance(port, dict) and (port.get("type") or "") == ""
                    and (port.get("digest") or "") == "" and not port.get("signal")
                ):
                    found.append((name, i))
        return found

    def test_no_unreviewed_placeholders(self, db):
        bad = [k for k in self._placeholders(db) if k not in _PLACEHOLDER_CONTROL_REVIEWED]
        assert bad == [], bad

    def test_reviewed_entries_are_live(self, db):
        live = set(self._placeholders(db))
        for key, reason in _PLACEHOLDER_CONTROL_REVIEWED.items():
            assert key in live, f"stale reviewed placeholder {key}"
            assert reason.strip()


# ---------------------------------------------------------------------------
# MC outlet flavour (cause 4)
# ---------------------------------------------------------------------------

class TestMcOutletFlavour:
    """MAX saves MC outlets as ``multichannelsignal``; the DB said ``signal``
    for most, so Patcher-built MC boxes differed from MAX-saved ones."""

    @pytest.mark.parametrize("name,args,expected", [
        ("mc.cycle~", ["440"], ["multichannelsignal"]),
        ("mc.*~", ["0.2"], ["multichannelsignal"]),
        ("mc.pack~", ["2"], ["multichannelsignal"]),
        ("mc.tapout~", ["100", "200", "300"], ["multichannelsignal"] * 3),
        ("mcs.tapout~", ["100", "200", "300"], ["multichannelsignal"]),
        ("mc.selector~", ["2", "1"], ["multichannelsignal"]),
        ("gridmeter~", [], ["multichannelsignal"]),
        # saved as plain `signal` by MAX (single-channel outlets)
        ("mc.sum~", [], ["signal"]),
        ("mc.unpack~", ["2"], ["signal", "signal"]),
        ("mc.unpack~", ["4"], ["signal"] * 4),
        ("cycle~", ["440"], ["signal"]),
    ])
    def test_get_outlet_types(self, db, name, args, expected):
        assert db.get_outlet_types(name, args) == expected

    def test_patcher_box_matches(self):
        p = Patcher()
        assert p.add_box("mc.cycle~", ["440"]).outlettype == ["multichannelsignal"]
        assert p.add_box("mc.sum~", []).outlettype == ["signal"]


class TestMcSignalIsCheckedLikeSignal:
    """A multichannelsignal outlet used to skip the legacy check and Layer 4
    entirely; now both flavours are signal (MAX-saved and built boxes agree).
    """

    _MC = ("mc.cycle~ 440", 2, 1, ["multichannelsignal"])

    def test_mc_into_print_proposed(self, db):
        results = validate_patch(_cord_patch(self._MC, "print", 1, 0, 0), db=db)
        assert len(_proposed(results)) == 1

    def test_mc_into_mc_sum_accepted(self, db):
        results = validate_patch(_cord_patch(self._MC, "mc.sum~", 1, 1, 0), db=db)
        assert _proposed(results) == []

    def test_unterminated_mc_chain_warns(self, db):
        patch = _make_patch_dict(boxes=[
            _make_box("obj-1", text="mc.cycle~ 440", numinlets=2, numoutlets=1,
                      outlettype=["multichannelsignal"]),
        ])
        results = validate_patch(patch, db=db)
        assert any("Unterminated signal chain" in r.message for r in results)


class TestInletBoxSource:
    """An `inlet` box saves "signal" when its parent cord is a signal; BEAP
    help ships such an inlet into `routepass` (packages/BEAP/Help/
    bp.Gigaverb.maxhelp [p SawtoothEnv]), so its cords are not type-checked.
    """

    def test_signal_typed_inlet_into_routepass_not_proposed(self, db):
        patch = _make_patch_dict(
            boxes=[
                {"box": {"maxclass": "inlet", "id": "obj-1", "numinlets": 0,
                         "numoutlets": 1, "outlettype": ["signal"],
                         "patching_rect": [0, 0, 30, 30]}},
                _make_box("obj-2", text="routepass signal variation", numinlets=1,
                          numoutlets=3, outlettype=["", "", ""]),
            ],
            lines=[_make_line("obj-1", 0, "obj-2", 0)],
        )
        assert _proposed(validate_patch(patch, db=db)) == []


# ---------------------------------------------------------------------------
# WR-03 / WR-06: argument-dependent inlet counts, inlet / outlet boxes
# ---------------------------------------------------------------------------

class TestArgumentDependentInletCounts:

    @pytest.mark.parametrize("name,args,expected", [
        ("sfrecord~", ["2"], (2, 1)),
        ("sfrecord~", ["4"], (4, 1)),
        ("sfrecord~", ["8"], (8, 1)),
        ("sfrecord~", [], (1, 1)),
        ("jit.catch~", ["7"], (7, 2)),
        ("jit.catch~", ["2", "@mode", "2"], (2, 2)),
        ("jit.catch~", ["@mode", "0"], (1, 2)),
        ("jit.catch~", [], (1, 2)),
        ("record~", ["buf"], (3, 1)),
        ("record~", ["buf", "2"], (4, 1)),
    ])
    def test_counts(self, db, name, args, expected):
        assert db.compute_io_counts(name, args) == expected

    def test_patcher_builds_four_channel_sfrecord(self):
        p = Patcher()
        rec = p.add_box("sfrecord~", ["4"])
        assert rec.numinlets == 4
        osc = p.add_box("cycle~", ["440"])
        p.add_connection(osc, 0, rec, 3)  # channel 4: bounds-checked, must not raise

    def test_every_sfrecord_channel_inlet_accepts_signal(self, db):
        for i in range(8):
            assert _inlet_accepts_signal(_box("sfrecord~ 8"), i, db)


class TestInletOutletBoxCounts:
    """WR-06: MAX's `inlet` has no inlet, `outlet` has one (1845 / 1629
    MAX-saved bundle boxes, every version 7.0.0-9.3.0)."""

    def test_counts(self, db):
        assert db.compute_io_counts("inlet") == (0, 1)
        assert db.compute_io_counts("outlet") == (1, 0)

    def test_patcher_boxes(self):
        p = Patcher()
        i, o = p.add_box("inlet"), p.add_box("outlet")
        assert (i.numinlets, i.numoutlets) == (0, 1)
        assert (o.numinlets, o.numoutlets) == (1, 0)

    def test_subpatcher_ports(self):
        p = Patcher()
        _box_, inner = p.add_subpatcher("sub", inlets=2, outlets=1)
        assert [(b.numinlets, b.numoutlets) for b in inner.get_inlets()] == [(0, 1)] * 2
        assert [(b.numinlets, b.numoutlets) for b in inner.get_outlets()] == [(1, 0)]

    def test_cords_into_inlet_or_outlet_1_are_out_of_bounds(self, db):
        p = Patcher()
        p.add_message("hi")
        p.add_box("inlet")
        p.add_box("outlet")
        d = p.to_dict()
        ids = {b["box"]["maxclass"]: b["box"]["id"] for b in d["patcher"]["boxes"]}
        d["patcher"]["lines"] = [
            _make_line(ids["message"], 0, ids["inlet"], 0),
            _make_line(ids["message"], 0, ids["outlet"], 1),
        ]
        errors = [r for r in validate_patch(d, db=db) if "out of bounds" in r.message]
        assert len(errors) == 2, [str(r) for r in errors]
