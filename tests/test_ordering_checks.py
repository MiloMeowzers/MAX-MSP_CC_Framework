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
