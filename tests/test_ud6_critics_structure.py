"""Structure critic fixes (quick 261022-ud6 WP3): CR-02 fan-out hot/cold and
trigger-fix order, IN-02 single report, WR-01 $N arity from outlettype.
"""

from __future__ import annotations

import pytest

from src.maxpat.critics import review_patch
from src.maxpat.db_lookup import ObjectDatabase
from tests.test_critics_recursive import _box, _container, _inner, _line, _patch


@pytest.fixture(scope="module")
def db():
    return ObjectDatabase()


def _rule(results, rule, severity=None):
    return [r for r in results if r.rule == rule and (severity is None or r.severity == severity)]


def _blockers(results):
    return [r for r in results if r.severity == "blocker"]


def _sig_box(box_id, text, n_in=2, n_out=1):
    return _box(box_id, text, n_in, n_out, outlettype=["signal"] * n_out)


def _msg(box_id, text):
    return _box(box_id, text, 2, 1, maxclass="message", outlettype=[""])


def _dac(box_id="obj-99"):
    return _box(box_id, "dac~", 2, 0, outlettype=[])


# ---------------------------------------------------------------------------
# CR-02 -- fan-out reconvergence respects hot/cold
# ---------------------------------------------------------------------------


def _flonum(box_id):
    return _box(box_id, None, 1, 2, maxclass="flonum", outlettype=["", "bang"])


class TestFanOutHotCold:
    def test_both_cold_is_warning(self, db):
        """flonum -> pack inlet 1 and flonum -> * 2. -> pack inlet 2: nothing outputs."""
        boxes = [
            _flonum("obj-1"),
            _box("obj-2", "* 2.", 2, 1, outlettype=["float"]),
            _box("obj-3", "pack 0. 0. 0.", 3, 1, outlettype=[""]),
            _box("obj-4", "print", 1, 0, outlettype=[]),
        ]
        lines = [
            _line("obj-1", 0, "obj-3", 1), _line("obj-1", 0, "obj-2", 0),
            _line("obj-2", 0, "obj-3", 2), _line("obj-3", 0, "obj-4", 0),
        ]
        fan = _rule(review_patch(_patch(boxes, lines), db=db), "fan_out_without_trigger")
        assert len(fan) == 1
        assert fan[0].severity == "warning" and fan[0].fix is None

    def test_no_expansion_past_cold_entry(self, db):
        """flonum -> + 0. inlet 1 (cold), flonum -> * 2. -> pack inlet 1; + -> pack inlet 0.
        Branch 1 never reaches pack: the + only outputs when metro -> f bangs it."""
        boxes = [
            _flonum("obj-1"),
            _box("obj-2", "+ 0.", 2, 1, outlettype=["float"]),
            _box("obj-3", "* 2.", 2, 1, outlettype=["float"]),
            _box("obj-4", "pack 0. 0.", 2, 1, outlettype=[""]),
            _box("obj-5", "metro 100", 2, 1, outlettype=["bang"]),
            _box("obj-6", "f", 2, 1, outlettype=["float"]),
            _box("obj-7", "print", 1, 0, outlettype=[]),
        ]
        lines = [
            _line("obj-1", 0, "obj-2", 1), _line("obj-1", 0, "obj-3", 0),
            _line("obj-3", 0, "obj-4", 1), _line("obj-2", 0, "obj-4", 0),
            _line("obj-5", 0, "obj-6", 0), _line("obj-6", 0, "obj-2", 0),
            _line("obj-4", 0, "obj-7", 0),
        ]
        fan = _rule(review_patch(_patch(boxes, lines), db=db), "fan_out_without_trigger")
        assert [r.severity for r in fan if r.box_ids[0] == "obj-1"] == ["warning"]

    def test_hot_and_cold_still_blocks_with_right_to_left_fix(self, db):
        """number -> + inlet 0 (first cord) and number -> * 2 -> + inlet 1:
        the cold branch must fire first, so it goes on the trigger's outlet 1."""
        boxes = [
            _box("obj-1", None, 1, 2, maxclass="number", outlettype=["int", "bang"]),
            _box("obj-2", "+", 2, 1, outlettype=["int"]),
            _box("obj-3", "* 2", 2, 1, outlettype=["int"]),
            _box("obj-4", "print", 1, 0, outlettype=[]),
        ]
        lines = [
            _line("obj-1", 0, "obj-2", 0), _line("obj-1", 0, "obj-3", 0),
            _line("obj-3", 0, "obj-2", 1), _line("obj-2", 0, "obj-4", 0),
        ]
        fan = _rule(review_patch(_patch(boxes, lines), db=db), "fan_out_without_trigger")
        assert len(fan) == 1 and fan[0].severity == "blocker"
        fx = fan[0].fix
        assert fx is not None and fx.kind == "insert_trigger"
        new = [o for o in fx.ops if o.op == "add_box"][0].box
        outs = {o.outlet: (o.dst, o.inlet) for o in fx.ops if o.op == "add_cord" and o.src == new}
        assert outs == {0: ("obj-2", 0), 1: ("obj-3", 0)}

    def test_fix_ignores_cold_entry_constraints(self, db):
        """A branch that enters a box at a cold inlet sets no order constraint
        downstream of it. Branch A (t i i obj-5) reaches M1 inlet 0 and M2
        inlet 1; branch B (t i i obj-6) reaches M1 inlet 1, and M2 inlet 0 only
        through '+ 5' inlet 1 (cold, no output). Before CR-02 the spurious
        "B hot at M2" made the constraints cyclic (no fix); now B fires first
        (outlet 1) and A last (outlet 0)."""
        boxes = [
            _box("obj-1", None, 1, 2, maxclass="number", outlettype=["int", "bang"]),
            _box("obj-2", "pack 0 0", 2, 1, outlettype=[""]),       # M1
            _box("obj-3", "pack 0 0", 2, 1, outlettype=[""]),       # M2
            _box("obj-5", "t i i", 1, 2, outlettype=["int", "int"]),
            _box("obj-6", "t i i", 1, 2, outlettype=["int", "int"]),
            _box("obj-7", "+ 5", 2, 1, outlettype=["int"]),
            _box("obj-8", "print", 1, 0, outlettype=[]),
        ]
        lines = [
            _line("obj-1", 0, "obj-5", 0),   # branch A
            _line("obj-1", 0, "obj-6", 0),   # branch B
            _line("obj-5", 1, "obj-3", 1),
            _line("obj-5", 0, "obj-2", 0),
            _line("obj-6", 1, "obj-2", 1),
            _line("obj-6", 0, "obj-7", 1),   # cold entry: no output
            _line("obj-7", 0, "obj-3", 0),
            _line("obj-2", 0, "obj-8", 0),
            _line("obj-3", 0, "obj-8", 0),
        ]
        fan = [r for r in _rule(review_patch(_patch(boxes, lines), db=db), "fan_out_without_trigger")
               if r.box_ids[0] == "obj-1"]
        assert len(fan) == 1 and fan[0].severity == "blocker"
        fx = fan[0].fix
        assert fx is not None
        new = [o for o in fx.ops if o.op == "add_box"][0].box
        outs = {o.outlet: (o.dst, o.inlet) for o in fx.ops if o.op == "add_cord" and o.src == new}
        assert outs == {0: ("obj-5", 0), 1: ("obj-6", 0)}


# ---------------------------------------------------------------------------
# IN-02 -- one defect reported once
# ---------------------------------------------------------------------------


class TestFanOutOwnsDirectHotCold:
    def test_number_into_plus_both_inlets_once(self, db):
        boxes = [
            _box("obj-1", None, 1, 2, maxclass="number", outlettype=["int", "bang"]),
            _box("obj-2", "+ 1", 2, 1, outlettype=["int"]),
            _box("obj-3", "print", 1, 0, outlettype=[]),
        ]
        lines = [
            _line("obj-1", 0, "obj-2", 0), _line("obj-1", 0, "obj-2", 1),
            _line("obj-2", 0, "obj-3", 0),
        ]
        results = review_patch(_patch(boxes, lines), db=db)
        assert len(_rule(results, "fan_out_without_trigger", "blocker")) == 1
        assert _rule(results, "hot_cold_ordering") == []


# ---------------------------------------------------------------------------
# WR-01 -- $N arity reads the saved outlettype first
# ---------------------------------------------------------------------------


class TestDollarArityOutlettype:
    def _arity(self, src, outlet, text, db):
        boxes = [src, _msg("obj-2", text), _box("obj-3", "print", 1, 0, outlettype=[])]
        lines = [_line("obj-1", outlet, "obj-2", 0), _line("obj-2", 0, "obj-3", 0)]
        return _rule(review_patch(_patch(boxes, lines), db=db), "dollar_arity")

    def test_zplane_list_outlet(self, db):
        src = _box("obj-1", "zplane~", 4, 4, outlettype=["list", "list", "list", "list"])
        assert self._arity(src, 1, "zeros $1 $2", db) == []

    def test_zplane_no_saved_type_db_role_list(self, db):
        src = _box("obj-1", "zplane~", 4, 4, outlettype=[])
        assert self._arity(src, 1, "zeros $1 $2", db) == []

    def test_mc_range_list_outlet(self, db):
        src = _box("obj-1", "mc.range~", 1, 3, outlettype=["multichannelsignal", "", ""])
        assert self._arity(src, 1, "$1 $2", db) == []

    def test_seq_symbol_outlet_is_one_atom(self, db):
        src = _box("obj-1", "seq~", 1, 3, outlettype=["", "", ""])
        assert self._arity(src, 2, "$1", db) == []
        found = self._arity(src, 2, "$1 $2", db)
        assert len(found) == 1 and "supply at most 1 atom(s)" in found[0].finding

    def test_saved_int_still_blocks(self, db):
        src = _box("obj-1", None, 1, 2, maxclass="number", outlettype=["int", "bang"])
        assert len(self._arity(src, 0, "$1 $2", db)) == 1
