"""Q21 ordering and message-shape checks (review §4.4 R4, §4.1 class 2).

``structure_critic`` gains three blocker checks, run on every non-gen scope
of the shared PatchGraph:

  - ``Invalid trigger type: `` -- a single lower-case letter other than
    b, i, f, l, s in a trigger (``t a`` outputs the literal symbol ``a``).
  - ``Message $N arity: `` -- a message box's highest ``$N`` is above the
    atoms every inlet-0 feeder together can supply (the resend idiom, a
    bang beside a value feeder, is not flagged).
  - ``Trigger order: `` -- one trigger feeds both the hot inlet 0 and a
    cold inlet of a box (directly or through one hop) and the hot feeder
    is not the lowest outlet index.

The probe tests rebuild, in memory, the real pre-fix and fixed shapes of
14f2221 (``p slicer``), 2e40f06 (``p player``) and 503f92f (top level),
taken from their companion save commits (3c9452a5, cc361028, b9c324d3).
No patch file is read from git or written, except the save-gate test,
which saves into a throwaway repo under ``tmp_path``.
"""

from __future__ import annotations

import copy
import shutil

import pytest

from src.maxpat.critics import review_patch
from src.maxpat.critics.structure_critic import review_structure
from src.maxpat.db_lookup import ObjectDatabase
from src.maxpat.graph import PatchGraph
from tests.test_critic_precision import _box, _ln
from tests.test_critics import _make_patch
from tests.test_critics_recursive import _repo


@pytest.fixture(scope="module")
def db() -> ObjectDatabase:
    return ObjectDatabase()


_TYPE = "Invalid trigger type: "
_ARITY = "Message $N arity: "
_ORDER = "Trigger order: "
_Q21 = (_TYPE, _ARITY, _ORDER)


def _strip_prefix(finding: str) -> str:
    if finding.startswith("[") and "] " in finding:
        return finding.split("] ", 1)[1]
    return finding


def _q21(results, kind=None):
    kinds = (kind,) if kind else _Q21
    return [r for r in results if _strip_prefix(r.finding).startswith(kinds)]


def _review(boxes, lines, db):
    return review_structure(_make_patch(boxes, lines), db=db)


def _nested(label, boxes, lines, box_id="obj-1", classnamespace=None):
    inner = {"boxes": [{"box": b} for b in boxes],
             "lines": [{"patchline": pl} for pl in lines]}
    if classnamespace:
        inner["classnamespace"] = classnamespace
    box = _box(box_id, label, numinlets=1, numoutlets=1)
    box["patcher"] = inner
    return {"patcher": {"boxes": [{"box": box}], "lines": []}}


def _t(box_id, text, n_out=None):
    n = n_out if n_out is not None else max(len(text.split()) - 1, 2)
    return _box(box_id, text, numinlets=1, numoutlets=n)


def _msg(box_id, text):
    return _box(box_id, text, maxclass="message", numinlets=2, numoutlets=1)


def _button(box_id):
    return _box(box_id, maxclass="button", numinlets=1, numoutlets=1,
                outlettype=["bang"])


def _toggle(box_id):
    return _box(box_id, maxclass="toggle", numinlets=1, numoutlets=1,
                outlettype=["int"])


def _number(box_id):
    return _box(box_id, maxclass="number", numinlets=1, numoutlets=2,
                outlettype=["", "bang"])


# ===========================================================================
# Trigger types
# ===========================================================================


class TestTriggerTypes:
    def test_t_a_exact_text(self, db):
        res = _review([_t("obj-1", "t a", 1)], [], db)
        found = _q21(res)
        assert len(found) == 1
        r = found[0]
        assert r.severity == "blocker"
        assert r.finding == (
            "Invalid trigger type: 't a' (obj-1) argument 'a' is not a trigger "
            "type (b, i, f, l, s) -- it outputs the literal symbol 'a'"
        )
        assert r.suggestion == (
            "Use b, i, f, l or s; any other symbol is output as a constant. "
            "For an anything message where order does not matter, fan out "
            "directly; where order matters use 't l l' or 't s s'."
        )

    def test_trigger_a_b(self, db):
        found = _q21(_review([_t("obj-1", "trigger a b")], [], db), _TYPE)
        assert len(found) == 1 and found[0].severity == "blocker"
        assert "'trigger a b' (obj-1) argument 'a'" in found[0].finding

    def test_t_a_a_one_finding(self, db):
        assert len(_q21(_review([_t("obj-1", "t a a")], [], db))) == 1

    def test_t_p(self, db):
        found = _q21(_review([_t("obj-1", "t p", 1)], [], db), _TYPE)
        assert len(found) == 1 and "argument 'p'" in found[0].finding

    @pytest.mark.parametrize("text", [
        "t b i f l s", "t 0 1. set foo", "t #1 b", "t", "t B",
    ])
    def test_valid_or_skipped(self, db, text):
        assert _q21(_review([_t("obj-1", text)], [], db)) == []


# ===========================================================================
# $N arity
# ===========================================================================


def _arity(feeders, msg_text, lines, db):
    boxes = list(feeders) + [_msg("obj-9", msg_text)]
    return _q21(_review(boxes, lines, db), _ARITY)


class TestDollarArity:
    def test_t_b_into_dollar1(self, db):
        f = _arity([_t("obj-1", "t b", 1)], "$1", [_ln("obj-1", 0, "obj-9", 0)], db)
        assert len(f) == 1 and f[0].severity == "blocker"
        assert f[0].finding == (
            "Message $N arity: '$1' (obj-9) uses $1 but its feeders supply at most "
            "0 atom(s): 't b' (obj-1) outlet 0 -- $ arguments above 0 keep their "
            "stored value (0 until set)"
        )
        assert f[0].suggestion == (
            "Feed it from an outlet that carries all 1 values (a 't l' outlet, "
            "pack or another list source), or lower the highest $N."
        )

    def test_button_into_dollar1(self, db):
        f = _arity([_button("obj-1")], "$1", [_ln("obj-1", 0, "obj-9", 0)], db)
        assert len(f) == 1
        assert "'button' (obj-1) outlet 0" in f[0].finding

    def test_t_f_into_two(self, db):
        f = _arity([_t("obj-1", "t f", 1)], "$1 $2", [_ln("obj-1", 0, "obj-9", 0)], db)
        assert len(f) == 1 and "uses $2" in f[0].finding

    def test_t_f_into_one(self, db):
        assert _arity([_t("obj-1", "t f", 1)], "$1", [_ln("obj-1", 0, "obj-9", 0)], db) == []

    def test_t_l_into_three(self, db):
        assert _arity([_t("obj-1", "t l", 1)], "$1 $2 $3",
                      [_ln("obj-1", 0, "obj-9", 0)], db) == []

    def test_number_unknown(self, db):
        assert _arity([_number("obj-1")], "$1", [_ln("obj-1", 0, "obj-9", 0)], db) == []

    def test_resend_idiom_bang_beside_list_feeder_not_flagged(self, db):
        """Invariant (assumption delta): feeders are judged together, never per cord."""
        f = _arity(
            [_button("obj-1"), _t("obj-2", "t l", 1)], "$1 $2",
            [_ln("obj-1", 0, "obj-9", 0), _ln("obj-2", 0, "obj-9", 0)], db,
        )
        assert f == []

    def test_bang_plus_toggle_one(self, db):
        f = _arity(
            [_button("obj-1"), _toggle("obj-2")], "$1",
            [_ln("obj-1", 0, "obj-9", 0), _ln("obj-2", 0, "obj-9", 0)], db,
        )
        assert f == []

    def test_bang_plus_toggle_two(self, db):
        f = _arity(
            [_button("obj-1"), _toggle("obj-2")], "$1 $2",
            [_ln("obj-1", 0, "obj-9", 0), _ln("obj-2", 0, "obj-9", 0)], db,
        )
        assert len(f) == 1
        assert ("feeders supply at most 1 atom(s): 'button' (obj-1) outlet 0, "
                "'toggle' (obj-2) outlet 0 --") in f[0].finding

    def test_inlet1_fed_not_flagged(self, db):
        f = _arity(
            [_t("obj-1", "t b", 1), _t("obj-2", "t s", 1)], "$1",
            [_ln("obj-1", 0, "obj-9", 0), _ln("obj-2", 0, "obj-9", 1)], db,
        )
        assert f == []

    def test_no_feeders(self, db):
        assert _arity([], "$1 $2", [], db) == []

    def test_escaped_dollar(self, db):
        assert _arity([_t("obj-1", "t b", 1)], "\\$1",
                      [_ln("obj-1", 0, "obj-9", 0)], db) == []

    def test_argless_t_acts_as_i_i(self, db):
        f = _arity([_t("obj-1", "t", 2)], "$1 $2", [_ln("obj-1", 0, "obj-9", 0)], db)
        assert len(f) == 1 and "at most 1 atom(s)" in f[0].finding


# ===========================================================================
# 503f92f probe (b9c324d3, top level)
# ===========================================================================


def _B(box_id, maxclass, text, numinlets, numoutlets, outlettype):
    """A box from a ``<reference_data>`` tuple (id, maxclass, text, in, out, outlettype)."""
    return _box(box_id, text, maxclass=maxclass, numinlets=numinlets,
                numoutlets=numoutlets, outlettype=outlettype)


def _probe_503f92f(fixed: bool):
    t_id = "obj-124" if fixed else "obj-104"
    t_text = "t f f l" if fixed else "t l f f"
    boxes = [
        _B("obj-103", "newobj", "receive bach_note", 1, 1, [""]),
        _B(t_id, "newobj", t_text, 1, 3, ["", "", ""]),
        _B("obj-105", "newobj", "expr max(0.\\, $f1 - 18000.)", 1, 1, [""]),
        _B("obj-106", "newobj", "expr max(20000.\\, $f1 + 2000.)", 1, 1, [""]),
        _B("obj-107", "message", "addchord [ $1 [ $2 $3 $4 ] ]", 2, 1, [""]),
        _B("obj-108", "newobj", "pack 0. 0.", 2, 1, [""]),
    ]
    if fixed:
        lines = [
            _ln("obj-103", 0, t_id, 0),
            _ln(t_id, 0, "obj-105", 0),
            _ln(t_id, 1, "obj-106", 0),
            _ln(t_id, 2, "obj-107", 0),
            _ln("obj-106", 0, "obj-108", 1),
            _ln("obj-105", 0, "obj-108", 0),
        ]
    else:
        lines = [
            _ln("obj-103", 0, t_id, 0),
            _ln(t_id, 2, "obj-107", 0),
            _ln(t_id, 1, "obj-106", 0),
            _ln(t_id, 0, "obj-105", 0),
            _ln("obj-106", 0, "obj-108", 1),
            _ln("obj-105", 0, "obj-108", 0),
        ]
    return _make_patch(boxes, lines)


class TestProbe503f92f:
    def test_prefix_caught(self, db):
        res = review_structure(_probe_503f92f(False), db=db)
        found = _q21(res)
        assert len(found) == 1
        assert found[0].severity == "blocker"
        assert found[0].finding.startswith(
            "Message $N arity: 'addchord [ $1 [ $2 $3 $4 ] ]' (obj-107) uses $4 but "
            "its feeders supply at most 1 atom(s): 't l f f' (obj-104) outlet 2"
        )

    def test_fixed_clean(self, db):
        assert _q21(review_structure(_probe_503f92f(True), db=db)) == []


# ===========================================================================
# End to end: nesting, gen, review_patch, one DB, save gate, junk
# ===========================================================================


class TestAtomChecksEndToEnd:
    def test_nested_prefix_and_path(self, db):
        d = _nested("p x", [_t("obj-1", "t a", 1)], [])
        found = _q21(review_structure(d, db=db))
        assert len(found) == 1
        assert found[0].finding.startswith("[p x] Invalid trigger type: ")
        assert found[0].path == "obj-1"

    def test_gen_scope_skipped(self, db):
        d = _nested("gen~", [_t("obj-1", "t a", 1)], [], classnamespace="dsp.gen")
        assert _q21(review_structure(d, db=db)) == []

    def test_review_patch_has_both(self, db):
        boxes = [_t("obj-1", "t a", 1), _t("obj-2", "t b", 1), _msg("obj-3", "$1")]
        d = _make_patch(boxes, [_ln("obj-2", 0, "obj-3", 0)])
        res = review_patch(d, db=db)
        assert [r.severity for r in _q21(res, _TYPE)] == ["blocker"]
        assert [r.severity for r in _q21(res, _ARITY)] == ["blocker"]

    def _spy(self, monkeypatch):
        import src.maxpat.db_lookup as db_lookup
        import src.maxpat.critics.package_critic as pc

        made = []
        real = db_lookup.ObjectDatabase

        class Spy(real):
            def __init__(self, *a, **k):
                made.append(1)
                super().__init__(*a, **k)

        monkeypatch.setattr(db_lookup, "ObjectDatabase", Spy)
        monkeypatch.setattr(pc, "ObjectDatabase", Spy)
        return made

    def _probe_patch(self):
        boxes = [_t("obj-1", "t a", 1), _t("obj-2", "t b", 1), _msg("obj-3", "$1")]
        return _make_patch(boxes, [_ln("obj-2", 0, "obj-3", 0)])

    def test_review_patch_one_db(self, monkeypatch):
        made = self._spy(monkeypatch)
        res = review_patch(self._probe_patch())
        assert _q21(res, _ARITY)
        assert len(made) <= 1

    def test_review_structure_with_db_builds_none(self, monkeypatch, db):
        d = self._probe_patch()
        g = PatchGraph.build(d)
        made = self._spy(monkeypatch)
        res = review_structure(d, graph=g, db=db)
        assert made == []
        assert _q21(res, _ARITY)

    def test_review_structure_without_db_builds_own(self):
        assert _q21(review_structure(self._probe_patch()), _ARITY)

    @pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")
    def test_save_gate_refuses_t_a(self, tmp_path):
        from src.maxpat.hooks import PatchValidationError, save_patch_roundtrip
        from src.maxpat.patcher import Patcher

        root = _repo(tmp_path)
        P = root / "patches" / "demo" / "generated" / "demo.maxpat"
        d = Patcher().to_dict()
        box = _t("obj-1", "t a", 1)
        box["patching_rect"] = [10.0, 10.0, 40.0, 22.0]
        d["patcher"]["boxes"].append({"box": box})

        with pytest.raises(PatchValidationError) as excinfo:
            save_patch_roundtrip(d, P)
        texts = [getattr(f, "finding", "") for f in excinfo.value.findings]
        assert any(t.startswith("Invalid trigger type: 't a' (obj-1)") for t in texts), texts
        assert not P.exists()

    def test_junk_never_raises(self, db):
        boxes = [
            {"id": "obj-1", "maxclass": "newobj", "text": None},
            {"id": "obj-2", "maxclass": "newobj", "text": 5},
            {"id": "obj-3", "maxclass": "newobj", "text": ["t", "a"]},
            _t("obj-4", "t @x", 1),
            _t("obj-5", "trigger @x 1", 1),
            _msg("obj-6", "$1 $2"),
            {"id": "obj-7", "maxclass": "message", "text": None, "outlettype": "x"},
            {"id": "obj-8", "maxclass": ["x"], "text": "t a", "outlettype": None},
            _t("obj-10", "t b", 1),
        ]
        lines = [
            _ln("obj-missing", 0, "obj-6", 0),
            _ln("obj-10", "0", "obj-6", 0),
            _ln("obj-10", 0.5, "obj-6", 0),
            _ln("obj-1", 0, "obj-7", 0),
            _ln("obj-8", 3, "obj-6", 0),
            _ln("obj-4", 0, "obj-6", 0),
        ]
        d = _make_patch(boxes, lines)
        assert isinstance(review_structure(d, db=db), list)
        assert isinstance(review_patch(copy.deepcopy(d), db=db), list)


# ===========================================================================
# Trigger order (Task 3)
# ===========================================================================

# The Task 2 decision (quick 261015-bt8, Q/decision.txt): Max's previous-value
# / delta idioms are exempt from the trigger-order blocker.
_DECISION = "idiom-exempt"


def _order(boxes, lines, db):
    return _q21(_review(boxes, lines, db), _ORDER)


def _pack(box_id="obj-9", text="pack 0 0", n_in=2):
    return _box(box_id, text, numinlets=n_in, numoutlets=1)


def _hop(box_id, kind):
    if kind == "message":
        return _msg(box_id, "go")
    return _box(box_id, kind, numinlets=2, numoutlets=1)


_HOPS = ["zl.reg", "zl reg", "f", "float", "i", "int", "message", "prepend foo"]


class TestTriggerOrder:
    def test_bang_fed_hot_exact_text(self, db):
        f = _order(
            [_t("obj-1", "t l b"), _pack()],
            [_ln("obj-1", 1, "obj-9", 0), _ln("obj-1", 0, "obj-9", 1)], db,
        )
        assert len(f) == 1 and f[0].severity == "blocker"
        assert f[0].finding == (
            "Trigger order: 't l b' (obj-1) feeds the hot inlet 0 of 'pack' (obj-9) "
            "from outlet 1 but cold inlet(s) 1 from outlet(s) 0 -- trigger outlets "
            "fire right to left, so outlet 1 fires first and 'pack' outputs with "
            "stale cold values"
        )
        assert f[0].suggestion == (
            "Reorder the trigger so the hot inlet is fed by the lowest outlet index "
            "(outlet 0 fires last), e.g. 't l b' -> 't b l'."
        )

    def test_correct_order_clean(self, db):
        assert _order(
            [_t("obj-1", "t b l"), _pack()],
            [_ln("obj-1", 0, "obj-9", 0), _ln("obj-1", 1, "obj-9", 1)], db,
        ) == []

    @pytest.mark.parametrize("kind", _HOPS)
    def test_one_hop_counts(self, db, kind):
        f = _order(
            [_t("obj-1", "t l b"), _hop("obj-2", kind), _pack()],
            [_ln("obj-1", 1, "obj-2", 0), _ln("obj-2", 0, "obj-9", 0),
             _ln("obj-1", 0, "obj-9", 1)], db,
        )
        assert len(f) == 1 and f[0].severity == "blocker"
        assert "of 'pack' (obj-9) from outlet 1" in f[0].finding

    def test_two_hops_do_not_count(self, db):
        assert _order(
            [_t("obj-1", "t l b"), _hop("obj-2", "f"), _hop("obj-3", "i"), _pack()],
            [_ln("obj-1", 1, "obj-2", 0), _ln("obj-2", 0, "obj-3", 0),
             _ln("obj-3", 0, "obj-9", 0), _ln("obj-1", 0, "obj-9", 1)], db,
        ) == []

    def test_hop_fed_at_inlet1_does_not_propagate(self, db):
        assert _order(
            [_t("obj-1", "t l b"), _hop("obj-2", "f"), _pack()],
            [_ln("obj-1", 1, "obj-2", 1), _ln("obj-2", 0, "obj-9", 0),
             _ln("obj-1", 0, "obj-9", 1)], db,
        ) == []

    def test_same_outlet_hot_and_cold(self, db):
        assert _order(
            [_t("obj-1", "t l b"), _pack()],
            [_ln("obj-1", 0, "obj-9", 0), _ln("obj-1", 0, "obj-9", 1)], db,
        ) == []

    @pytest.mark.parametrize("text", [
        "gate 2", "switch 2", "ggate", "gswitch", "poly~ voice 4", "js foo.js",
        "p sub", "pak 0 0", "funnel 2",
    ])
    def test_excluded_targets(self, db, text):
        assert _order(
            [_t("obj-1", "t l b"), _box("obj-9", text, numinlets=3, numoutlets=1)],
            [_ln("obj-1", 1, "obj-9", 0), _ln("obj-1", 0, "obj-9", 1)], db,
        ) == []

    def test_groove_inlet1_is_hot(self, db):
        assert _order(
            [_t("obj-1", "t l b"),
             _box("obj-9", "groove~ buf 2", numinlets=3, numoutlets=3,
                  outlettype=["signal", "signal", "signal"])],
            [_ln("obj-1", 1, "obj-9", 0), _ln("obj-1", 0, "obj-9", 1)], db,
        ) == []

    def test_unknown_object(self, db):
        assert _order(
            [_t("obj-1", "t l b"), _box("obj-9", "foobar 1 2", numinlets=2)],
            [_ln("obj-1", 1, "obj-9", 0), _ln("obj-1", 0, "obj-9", 1)], db,
        ) == []

    def test_gen_scope(self, db):
        d = _nested(
            "gen~",
            [_t("obj-2", "t l b"), _pack()],
            [_ln("obj-2", 1, "obj-9", 0), _ln("obj-2", 0, "obj-9", 1)],
            classnamespace="dsp.gen",
        )
        assert _q21(review_structure(d, db=db), _ORDER) == []

    def test_pack_variable_io_inlet2_cold(self, db):
        f = _order(
            [_t("obj-1", "t l b"), _pack(text="pack 0 0 0", n_in=3)],
            [_ln("obj-1", 1, "obj-9", 0), _ln("obj-1", 0, "obj-9", 2)], db,
        )
        assert len(f) == 1 and "cold inlet(s) 2 from outlet(s) 0" in f[0].finding

    def test_expr_inlet1_cold(self, db):
        f = _order(
            [_t("obj-1", "t i b"), _box("obj-9", "expr $i1+$i2", numinlets=2)],
            [_ln("obj-1", 1, "obj-9", 0), _ln("obj-1", 0, "obj-9", 1)], db,
        )
        assert len(f) == 1 and "of 'expr' (obj-9)" in f[0].finding


# ===========================================================================
# 14f2221 probe (3c9452a5, inside obj-24 `p slicer`)
# ===========================================================================


def _probe_14f2221(fixed: bool):
    boxes = [
        _B("obj-900", "newobj", "fluid.buf2list", 2, 1, ["list"]),
        _B("obj-19", "newobj", "t b l" if fixed else "t l b", 1, 2,
           ["", ""] if fixed else ["", "bang"]),
        _B("obj-17", "newobj", "zl.reg", 2, 2, ["", ""]),
        _B("obj-18", "newobj", "ears.slice~ @timeunit samps", 2, 2, ["", ""]),
    ]
    if fixed:
        lines = [
            _ln("obj-900", 0, "obj-19", 0),
            _ln("obj-19", 0, "obj-17", 0),
            _ln("obj-17", 0, "obj-18", 0),
            _ln("obj-19", 1, "obj-18", 1),
        ]
    else:
        lines = [
            _ln("obj-900", 0, "obj-19", 0),
            _ln("obj-19", 1, "obj-17", 0),
            _ln("obj-17", 0, "obj-18", 0),
            _ln("obj-19", 0, "obj-18", 1),
        ]
    return boxes, lines


_14F_TEXT = (
    "Trigger order: 't l b' (obj-19) feeds the hot inlet 0 of 'ears.slice~' "
    "(obj-18) from outlet 1 but cold inlet(s) 1 from outlet(s) 0"
)


class TestProbe14f2221:
    def test_prefix_caught_top_level(self, db):
        res = _review(*_probe_14f2221(False), db)
        blockers = [r for r in res if r.severity == "blocker"]
        assert len(blockers) == 1
        assert blockers[0].finding.startswith(_14F_TEXT)
        assert blockers[0].path == ""

    def test_prefix_caught_nested(self, db):
        d = _nested("p slicer", *_probe_14f2221(False), box_id="obj-24")
        res = review_structure(d, db=db)
        blockers = [r for r in res if r.severity == "blocker"]
        assert len(blockers) == 1
        assert blockers[0].path == "obj-24"
        assert blockers[0].finding.startswith("[p slicer] " + _14F_TEXT)

    def test_fixed_clean(self, db):
        for d in (_make_patch(*_probe_14f2221(True)),
                  _nested("p slicer", *_probe_14f2221(True), box_id="obj-24")):
            res = review_structure(d, db=db)
            assert _q21(res) == []
            assert [r for r in res if r.severity == "blocker"] == []


# ===========================================================================
# 2e40f06 probe (cc361028, inside obj-26 `p player`)
# ===========================================================================


def _probe_2e40f06(fixed: bool):
    boxes = [
        _B("obj-10", "newobj", "route symbol", 2, 2, ["", ""]),
        _B("obj-6", "newobj", "t b s" if fixed else "t s b", 1, 2,
           ["", ""] if fixed else ["", "bang"]),
        _B("obj-5", "message", "set $1", 2, 1, [""]),
        _B("obj-7", "message", "0", 2, 1, [""]),
        _B("obj-9", "newobj", "groove~ rcc_dummy 2", 3, 3, ["signal", "signal", "signal"]),
    ]
    if fixed:
        lines = [
            _ln("obj-10", 0, "obj-6", 0),
            _ln("obj-6", 1, "obj-5", 0),
            _ln("obj-5", 0, "obj-9", 0),
            _ln("obj-6", 0, "obj-7", 0),
            _ln("obj-7", 0, "obj-9", 1),
        ]
    else:
        lines = [
            _ln("obj-10", 0, "obj-6", 0),
            _ln("obj-6", 0, "obj-5", 0),
            _ln("obj-5", 0, "obj-9", 0),
            _ln("obj-6", 1, "obj-7", 0),
            _ln("obj-7", 0, "obj-9", 1),
        ]
    return _nested("p player", boxes, lines, box_id="obj-26")


class TestProbe2e40f06:
    """2e40f06 cannot satisfy "pre-fix caught, fixed passes" (planner decision 2).

    The pre-fix ``t s b`` fed ``set $1`` (groove~ inlet 0) from outlet 0,
    which fires last, and ``0`` (groove~ inlet 1) from outlet 1: it already
    obeys R4. The fix ``t b s`` sends the hot message first, the opposite
    of R4. groove~ inlet 1 is Loop Min (groove~.maxref.xml), a signal/float
    inlet the DB marks ``hot: true``, and ``set`` does not consume it;
    v0.0.5 (d76608b7) later replaced that cord with ``startloop``. So it was
    not a hot/cold bug, and neither form fires (the user kept this probe in
    Task 2 to pin that).
    """

    @pytest.mark.parametrize("fixed", [False, True])
    def test_neither_form_fires(self, db, fixed):
        assert _q21(review_structure(_probe_2e40f06(fixed), db=db)) == []


# ===========================================================================
# Previous-value / delta idioms (Task 2 decision: _DECISION)
# ===========================================================================


def _expect_idiom(found):
    assert _DECISION == "idiom-exempt"
    assert found == []


class TestPreviousValueIdiom:
    def test_t_f_f_into_minus(self, db):
        _expect_idiom(_order(
            [_t("obj-1", "t f f"), _box("obj-9", "- 0.", numinlets=2)],
            [_ln("obj-1", 1, "obj-9", 0), _ln("obj-1", 0, "obj-9", 1)], db,
        ))

    def test_t_i_b_into_i(self, db):
        _expect_idiom(_order(
            [_t("obj-1", "t i b"), _box("obj-9", "i", numinlets=2)],
            [_ln("obj-1", 1, "obj-9", 0), _ln("obj-1", 0, "obj-9", 1)], db,
        ))

    def test_t_f_b_into_f(self, db):
        _expect_idiom(_order(
            [_t("obj-1", "t f b"), _box("obj-9", "f 0.", numinlets=2)],
            [_ln("obj-1", 1, "obj-9", 0), _ln("obj-1", 0, "obj-9", 1)], db,
        ))

    def test_t_f_f_into_greater(self, db):
        _expect_idiom(_order(
            [_t("obj-1", "t f f"), _box("obj-9", "> 0.", numinlets=2)],
            [_ln("obj-1", 1, "obj-9", 0), _ln("obj-1", 0, "obj-9", 1)], db,
        ))

    def test_t_l_l_b_into_vexpr(self, db):
        _expect_idiom(_order(
            [_t("obj-1", "t l l b"), _box("obj-9", "vexpr $f1-$f2", numinlets=2)],
            [_ln("obj-1", 1, "obj-9", 0), _ln("obj-1", 0, "obj-9", 1)], db,
        ))

    def test_fibonacci_t_b_b_into_int_one_hop(self, db):
        _expect_idiom(_order(
            [_t("obj-1", "t b b"), _box("obj-2", "int", numinlets=2),
             _box("obj-3", "int", numinlets=2)],
            [_ln("obj-1", 1, "obj-2", 0), _ln("obj-1", 0, "obj-3", 0),
             _ln("obj-3", 0, "obj-2", 1)], db,
        ))

    def test_t_b_l_into_waveform(self, db):
        _expect_idiom(_order(
            [_t("obj-1", "t b l"), _msg("obj-3", "go"),
             _box("obj-9", "waveform~", maxclass="waveform~", numinlets=5,
                  numoutlets=6)],
            [_ln("obj-1", 1, "obj-9", 0), _ln("obj-1", 0, "obj-3", 0),
             _ln("obj-3", 0, "obj-9", 4)], db,
        ))

    def test_non_idiom_control_blocks(self, db):
        f = _order(
            [_t("obj-1", "t l b"), _pack()],
            [_ln("obj-1", 1, "obj-9", 0), _ln("obj-1", 0, "obj-9", 1)], db,
        )
        assert [r.severity for r in f] == ["blocker"]


# ===========================================================================
# Purity
# ===========================================================================


class TestPurity:
    def test_review_patch_does_not_mutate(self, db):
        boxes = [
            _t("obj-1", "t a", 1),
            _t("obj-2", "t b", 1), _msg("obj-3", "$1"),
            _t("obj-4", "t l b"), _pack(),
        ]
        lines = [
            _ln("obj-2", 0, "obj-3", 0),
            _ln("obj-4", 1, "obj-9", 0), _ln("obj-4", 0, "obj-9", 1),
        ]
        d = _make_patch(boxes, lines)
        before = copy.deepcopy(d)
        res = review_patch(d, db=db)
        assert d == before
        for kind in _Q21:
            assert _q21(res, kind), kind
