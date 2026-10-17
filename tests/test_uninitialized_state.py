"""Q24 uninitialized-state check (review §4.4 R8, §4.1 class 4 "Load-time init").

``structure_critic._check_uninitialized_state`` reports a UI value holder
whose control output reaches DSP when nothing sets it at load (a parameter
initial value, a loadmess / loadbang / live.thisdevice path, a pattr /
pattrstorage restore or a slaved gain~ input). The finding is a warning on
an edit and a blocker on a new patch (``is_new=True``; the save gate sets it
for a file with no baseline).

Locked decisions (CONTEXT.md; the plan's D-labels):
  - D-01: the value-holder maxclasses (gain~, live.gain~, slider, dial,
    number, flonum, live.dial, live.slider, live.numbox, toggle,
    live.toggle, umenu, live.menu, tab, live.tab, radiogroup); every other
    class is never reported.
  - D-02: pattr binding is per control (a cord to / from a pattr, ``pattr
    @bindto``, or a varname under autopattr with a pattrstorage in the tree).
  - D-03: reach follows the full control graph (cords, port-exact
    subpatcher crossing, send/receive, value, pv, ``;`` remote messages)
    to the first DSP box, cycle-safe and bounded at depth 64.

Every patch here is built in memory; no committed patch file is written.
The save-gate tests save into a throwaway repo under ``tmp_path``.
"""

from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

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


_Q24 = "Uninitialized state: "

_SUGGESTION = (
    "Initialize it at load: parameter_enable 1 with parameter_initial_enable 1 "
    "and a parameter_initial value, or loadmess <value> (or loadbang -> message) "
    "into it, or a pattr binding (or a varname under autopattr with a "
    "pattrstorage); a slave gain~ takes the master gain~'s right outlet into "
    "its left inlet."
)


def _gain_text(label, box_id):
    return (
        f"Uninitialized state: '{label}' ({box_id}) is a gain stage that nothing "
        "sets at load (no parameter initial value, loadmess/loadbang path, "
        "pattr/pattrstorage restore or slaved gain~ input) -- it loads at its "
        "default (a plain gain~ at 0, silent) until touched"
    )


def _generic_text(label, box_id, dsp_label, dsp_id):
    return (
        f"Uninitialized state: '{label}' ({box_id}) drives DSP at '{dsp_label}' "
        f"({dsp_id}) but nothing sets it at load (no parameter initial value, "
        "loadmess/loadbang path, pattr/pattrstorage restore or slaved gain~ "
        "input) -- it shows its default until touched while the DSP runs on "
        "its own value"
    )


def _q24(results):
    """Q24 findings, by the structured CriticResult rule (Q33)."""
    return [r for r in results if getattr(r, "rule", "") == "uninitialized_state"]


def _q24_ids(results):
    return [r.box_ids[0] if r.box_ids else None for r in _q24(results)]


def _review(boxes, lines, db, **kw):
    return review_structure(_make_patch(boxes, lines), db=db, **kw)


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

def _gain(box_id, outlettype=None):
    box = _box(box_id, maxclass="gain~", numinlets=1, numoutlets=2,
               outlettype=outlettype or ["signal", ""])
    box["parameter_enable"] = 0
    return box


def _live_gain(box_id, parameter_enable=0, initial=False):
    box = _box(box_id, maxclass="live.gain~", numinlets=2, numoutlets=5,
               outlettype=["signal", "signal", "", "float", "list"])
    box["parameter_enable"] = parameter_enable
    if initial:
        box["saved_attribute_attributes"] = {"valueof": {
            "parameter_initial_enable": 1, "parameter_initial": [-6.0],
            "parameter_longname": "vol", "parameter_type": 0}}
    return box


def _loadmess(box_id, text="loadmess 100"):
    return _box(box_id, text, numinlets=1, numoutlets=1, outlettype=[""])


def _loadbang(box_id):
    return _box(box_id, "loadbang", numinlets=1, numoutlets=1, outlettype=["bang"])


def _msg(box_id, text):
    return _box(box_id, text, maxclass="message", numinlets=2, numoutlets=1,
                outlettype=[""])


def _obj(box_id, text, numinlets=1, numoutlets=1, outlettype=None):
    return _box(box_id, text, numinlets=numinlets, numoutlets=numoutlets,
                outlettype=outlettype)


def _cycle(box_id):
    return _box(box_id, "cycle~ 440", numinlets=2, numoutlets=1, outlettype=["signal"])


def _ezdac(box_id):
    return _box(box_id, maxclass="ezdac~", numinlets=2, numoutlets=0, outlettype=[])


def _inlet(box_id, x=10.0):
    box = _box(box_id, maxclass="inlet", numinlets=0, numoutlets=1, outlettype=[""])
    box["patching_rect"] = [x, 10.0, 30.0, 30.0]
    return box


def _outlet(box_id, x=10.0):
    box = _box(box_id, maxclass="outlet", numinlets=1, numoutlets=0, outlettype=[])
    box["patching_rect"] = [x, 200.0, 30.0, 30.0]
    return box


def _container(box_id, label, boxes, lines, numinlets=1, numoutlets=1,
               outlettype=None, classnamespace=None, maxclass="newobj"):
    inner = {"boxes": [{"box": b} for b in boxes],
             "lines": [{"patchline": pl} for pl in lines]}
    if classnamespace:
        inner["classnamespace"] = classnamespace
    box = _box(box_id, label, maxclass=maxclass, numinlets=numinlets,
               numoutlets=numoutlets, outlettype=outlettype)
    box["patcher"] = inner
    return box


def _latent():
    """The Q24 latent shape: cycle~ -> plain gain~ (master) -> ezdac~, with
    a slave gain~ fed by the master's outlet 1."""
    boxes = [_cycle("obj-1"), _gain("obj-2"), _ezdac("obj-3"), _gain("obj-4")]
    lines = [
        _ln("obj-1", 0, "obj-2", 0),
        _ln("obj-2", 0, "obj-3", 0),
        _ln("obj-1", 0, "obj-4", 0),
        _ln("obj-2", 1, "obj-4", 0),
        _ln("obj-4", 0, "obj-3", 1),
    ]
    return boxes, lines


def _gain_with_feeders(feeders, feeder_lines, gain_id="obj-2"):
    """cycle~ obj-1 -> gain~ *gain_id* -> ezdac~ obj-3, plus *feeders*."""
    boxes = [_cycle("obj-1"), _gain(gain_id), _ezdac("obj-3")] + list(feeders)
    lines = [
        _ln("obj-1", 0, gain_id, 0),
        _ln(gain_id, 0, "obj-3", 0),
        _ln(gain_id, 0, "obj-3", 1),
    ] + list(feeder_lines)
    return boxes, lines


def _ids(pairs):
    return [box_id for _scope, box_id in pairs]


# ===========================================================================
# control_walk (upstream)
# ===========================================================================


class TestControlWalkUpstream:
    def _up(self, boxes, lines, start="obj-2", scope=None):
        g = PatchGraph.build(_make_patch(boxes, lines))
        return list(g.control_walk(scope or g.top, start, downstream=False))

    def test_loadmess_direct(self):
        boxes, lines = _gain_with_feeders([_loadmess("obj-10")], [_ln("obj-10", 0, "obj-2", 0)])
        assert "obj-10" in _ids(self._up(boxes, lines))

    def test_loadbang_through_trigger_and_message(self):
        boxes, lines = _gain_with_feeders(
            [_loadbang("obj-10"), _obj("obj-11", "t b"), _msg("obj-12", "100")],
            [_ln("obj-10", 0, "obj-11", 0), _ln("obj-11", 0, "obj-12", 0),
             _ln("obj-12", 0, "obj-2", 0)],
        )
        ids = _ids(self._up(boxes, lines))
        assert ids[:3] == ["obj-12", "obj-11", "obj-10"]

    def test_signal_cord_never_followed(self):
        boxes, lines = _gain_with_feeders([], [])
        assert "obj-1" not in _ids(self._up(boxes, lines))

    def test_crosses_p_outlet_port_exactly(self):
        inner = [_loadmess("in-1"), _outlet("in-2")]
        p = _container("obj-5", "p init", inner, [_ln("in-1", 0, "in-2", 0)],
                       numinlets=0, numoutlets=1)
        boxes, lines = _gain_with_feeders([p], [_ln("obj-5", 0, "obj-2", 0)])
        pairs = self._up(boxes, lines)
        ids = _ids(pairs)
        assert "in-1" in ids
        assert "obj-5" not in ids and "in-2" not in ids
        scope = next(s for s, b in pairs if b == "in-1")
        assert scope.key == "obj-5"

    def test_send_receive_bridge(self):
        boxes, lines = _gain_with_feeders(
            [_loadmess("obj-10"), _obj("obj-11", "s vol", numoutlets=0, outlettype=[]),
             _obj("obj-12", "r vol", numinlets=0)],
            [_ln("obj-10", 0, "obj-11", 0), _ln("obj-12", 0, "obj-2", 0)],
        )
        ids = _ids(self._up(boxes, lines))
        assert ids[:3] == ["obj-12", "obj-11", "obj-10"]

    def test_start_never_yielded_and_no_duplicates(self):
        boxes, lines = _gain_with_feeders(
            [_loadbang("obj-10"), _obj("obj-11", "t b b", numoutlets=2),
             _msg("obj-12", "100")],
            [_ln("obj-10", 0, "obj-11", 0), _ln("obj-11", 0, "obj-12", 0),
             _ln("obj-11", 1, "obj-12", 0), _ln("obj-12", 0, "obj-2", 0),
             _ln("obj-2", 1, "obj-12", 0)],
        )
        ids = _ids(self._up(boxes, lines))
        assert "obj-2" not in ids
        assert len(ids) == len(set(ids))


# ===========================================================================
# Gain stages (gain~ / live.gain~)
# ===========================================================================


class TestGainStage:
    def test_latent_shape_one_finding_on_master(self, db):
        boxes, lines = _latent()
        found = _q24(_review(boxes, lines, db))
        assert len(found) == 1
        r = found[0]
        assert r.finding == _gain_text("gain~", "obj-2")
        assert r.suggestion == _SUGGESTION
        assert r.path == ""

    def test_loadmess_clears(self, db):
        boxes, lines = _gain_with_feeders([_loadmess("obj-10")], [_ln("obj-10", 0, "obj-2", 0)])
        assert _q24(_review(boxes, lines, db)) == []

    def test_loadbang_path_clears(self, db):
        boxes, lines = _gain_with_feeders(
            [_loadbang("obj-10"), _obj("obj-11", "t b"), _msg("obj-12", "100")],
            [_ln("obj-10", 0, "obj-11", 0), _ln("obj-11", 0, "obj-12", 0),
             _ln("obj-12", 0, "obj-2", 0)],
        )
        assert _q24(_review(boxes, lines, db)) == []

    def test_send_receive_clears(self, db):
        boxes, lines = _gain_with_feeders(
            [_loadmess("obj-10"), _obj("obj-11", "s vol", numoutlets=0, outlettype=[]),
             _obj("obj-12", "r vol", numinlets=0)],
            [_ln("obj-10", 0, "obj-11", 0), _ln("obj-12", 0, "obj-2", 0)],
        )
        assert _q24(_review(boxes, lines, db)) == []

    def test_slave_with_signal_typed_master_outlet(self, db):
        """mixer-bus saves the master's outlettype as ["signal", "signal"]:
        the DB (outlet 1 is not signal) decides the slave route."""
        boxes, lines = _latent()
        boxes[1] = _gain("obj-2", outlettype=["signal", "signal"])
        ids = _q24_ids(_review(boxes, lines, db))
        assert ids == ["obj-2"]

    def test_live_gain_parameter_initial_clears(self, db):
        boxes = [_cycle("obj-1"), _live_gain("obj-2", 1, initial=True), _ezdac("obj-3")]
        lines = [_ln("obj-1", 0, "obj-2", 0), _ln("obj-2", 0, "obj-3", 0)]
        assert _q24(_review(boxes, lines, db)) == []

    def test_live_gain_without_init_reported(self, db):
        boxes = [_cycle("obj-1"), _live_gain("obj-2", 0), _ezdac("obj-3")]
        lines = [_ln("obj-1", 0, "obj-2", 0), _ln("obj-2", 0, "obj-3", 0)]
        found = _q24(_review(boxes, lines, db))
        assert [r.finding for r in found] == [_gain_text("live.gain~", "obj-2")]

    def test_signal_only_load_path_not_initialized(self, db):
        boxes, lines = _gain_with_feeders(
            [_loadmess("obj-10"), _obj("obj-11", "sig~", outlettype=["signal"])],
            [_ln("obj-10", 0, "obj-11", 0), _ln("obj-11", 0, "obj-2", 0)],
        )
        assert _q24_ids(_review(boxes, lines, db)) == ["obj-2"]

    def test_nested_in_p(self, db):
        boxes, lines = _latent()
        p = _container("obj-1", "p out", boxes, lines, numinlets=0, numoutlets=0)
        d = {"patcher": {"boxes": [{"box": p}], "lines": []}}
        found = _q24(review_structure(d, db=db))
        assert len(found) == 1
        assert found[0].path == "obj-1"
        assert found[0].finding.startswith("[p out] Uninitialized state: ")

    def test_gen_scope_never_checked(self, db):
        boxes, lines = _latent()
        gen = _container("obj-1", "gen~", boxes, lines, numinlets=1, numoutlets=1,
                         outlettype=["signal"], classnamespace="dsp.gen")
        d = {"patcher": {"boxes": [{"box": gen}], "lines": []}}
        assert _q24(review_structure(d, db=db)) == []


# ===========================================================================
# Severity: warning on edits, blocker on new patches
# ===========================================================================


class TestSeverity:
    def test_review_structure_default_is_warning(self, db):
        boxes, lines = _latent()
        found = _q24(_review(boxes, lines, db))
        assert [r.severity for r in found] == ["warning"]

    def test_review_structure_is_new_is_blocker(self, db):
        boxes, lines = _latent()
        found = _q24(_review(boxes, lines, db, is_new=True))
        assert [r.severity for r in found] == ["blocker"]

    def test_review_patch_default_is_warning(self, db):
        boxes, lines = _latent()
        found = _q24(review_patch(_make_patch(boxes, lines), db=db))
        assert [r.severity for r in found] == ["warning"]

    def test_review_patch_is_new_is_blocker(self, db):
        boxes, lines = _latent()
        found = _q24(review_patch(_make_patch(boxes, lines), db=db, is_new=True))
        assert [r.severity for r in found] == ["blocker"]

    def test_severity_split_is_only_is_new(self, db):
        """Invariant (assumption delta, add-alongside): is_new changes only
        the Q24 severity, never the findings or any other result."""
        boxes, lines = _latent()
        d = _make_patch(boxes, lines)
        edit = review_patch(copy.deepcopy(d), db=db)
        new = review_patch(copy.deepcopy(d), db=db, is_new=True)
        q_edit, q_new = _q24(edit), _q24(new)
        assert q_edit and [r.finding for r in q_edit] == [r.finding for r in q_new]
        assert {r.severity for r in q_edit} == {"warning"}
        assert {r.severity for r in q_new} == {"blocker"}
        rest = lambda rs: [(r.severity, r.finding, r.suggestion, r.path)
                           for r in rs if r not in _q24(rs)]
        assert rest(edit) == rest(new)

    def test_review_patch_builds_at_most_one_db(self, monkeypatch):
        import src.maxpat.critics.package_critic as pc
        import src.maxpat.db_lookup as db_lookup

        made = []
        real = db_lookup.ObjectDatabase

        class Spy(real):
            def __init__(self, *a, **k):
                made.append(1)
                super().__init__(*a, **k)

        monkeypatch.setattr(db_lookup, "ObjectDatabase", Spy)
        monkeypatch.setattr(pc, "ObjectDatabase", Spy)
        boxes, lines = _latent()
        assert _q24(review_patch(_make_patch(boxes, lines)))
        assert len(made) <= 1


# ===========================================================================
# Save gate: a new file is refused, an edit saves
# ===========================================================================


def _rect(box, x, y):
    box["patching_rect"] = [float(x), float(y), 60.0, 22.0]
    return box


def _gate_patch(extra_gain=False):
    from src.maxpat.patcher import Patcher

    d = Patcher().to_dict()
    boxes = [_rect(_cycle("obj-1"), 20, 20), _rect(_gain("obj-2"), 20, 80),
             _rect(_ezdac("obj-3"), 20, 260)]
    lines = [_ln("obj-1", 0, "obj-2", 0), _ln("obj-2", 0, "obj-3", 0)]
    if extra_gain:
        boxes.append(_rect(_gain("obj-4"), 160, 80))
        lines += [_ln("obj-1", 0, "obj-4", 0), _ln("obj-4", 0, "obj-3", 1)]
    d["patcher"]["boxes"].extend({"box": b} for b in boxes)
    d["patcher"]["lines"].extend({"patchline": pl} for pl in lines)
    return d


@pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")
class TestSaveGate:
    def test_new_file_refused(self, tmp_path):
        from src.maxpat.critics.base import CriticResult
        from src.maxpat.hooks import PatchValidationError, save_patch_roundtrip

        root = _repo(tmp_path)
        P = root / "patches" / "demo" / "generated" / "demo.maxpat"
        with pytest.raises(PatchValidationError) as excinfo:
            save_patch_roundtrip(_gate_patch(), P)
        q24 = [f for f in excinfo.value.findings
               if isinstance(f, CriticResult) and f.finding.startswith(_Q24)]
        assert q24 and all(f.severity == "blocker" for f in q24)
        assert not P.exists()

    def test_edit_saves(self, tmp_path):
        from src.maxpat.hooks import save_patch_roundtrip
        from tests.test_save_gate import _seed

        root = _repo(tmp_path)
        P = root / "patches" / "demo" / "generated" / "demo.maxpat"
        text = _seed(root, P, _gate_patch())
        save_patch_roundtrip(_gate_patch(extra_gain=True), P, original_text=text)
        saved = json.loads(P.read_text())
        ids = [e["box"]["id"] for e in saved["patcher"]["boxes"]]
        assert "obj-4" in ids

    def test_gate_report_new_vs_edit(self):
        from src.maxpat.hooks import _gate_report

        d = _gate_patch()
        new = _gate_report(d, None, [])
        assert any(getattr(r, "finding", "").startswith(_Q24) for r in new.new_blockers)
        edit = _gate_report(d, copy.deepcopy(d), [copy.deepcopy(d)])
        assert not any(getattr(r, "finding", "").startswith(_Q24) for r in edit.new_blockers)


# ===========================================================================
# Task 2 builders: value holders, DSP targets, bridges
# ===========================================================================

_HOLDER_CLASSES = (
    "slider", "dial", "number", "flonum", "live.dial", "live.slider",
    "live.numbox", "toggle", "live.toggle", "umenu", "live.menu", "tab",
    "live.tab", "radiogroup",
)
_EXCLUDED_CLASSES = ("button", "kslider", "multislider", "textedit", "nodes", "matrixctrl")


def _ui(box_id, maxclass="dial", varname=None, **attrs):
    box = _box(box_id, maxclass=maxclass, numinlets=1, numoutlets=2,
               outlettype=["", ""])
    if maxclass.startswith("live."):
        box["parameter_enable"] = 0
    if varname is not None:
        box["varname"] = varname
    box.update(attrs)
    return box


def _dial(box_id="obj-1", **kw):
    return _ui(box_id, "dial", **kw)


def _flonum(box_id, **kw):
    return _ui(box_id, "flonum", **kw)


def _gen(box_id):
    return _box(box_id, "gen~", numinlets=2, numoutlets=1, outlettype=["signal"])


def _prepend(box_id, text="prepend cut"):
    return _obj(box_id, text)


def _send(box_id, text):
    return _obj(box_id, text, numinlets=1, numoutlets=0, outlettype=[])


def _recv(box_id, text):
    return _obj(box_id, text, numinlets=0, numoutlets=1)


def _param_initial(value=0.5):
    return {"parameter_enable": 1, "saved_attribute_attributes": {"valueof": {
        "parameter_initial_enable": 1, "parameter_initial": [value],
        "parameter_longname": "cut", "parameter_type": 0}}}


def _to_gen(control, extra=(), extra_lines=()):
    """*control* (obj-1) -> prepend cut (obj-2) -> gen~ (obj-3)."""
    boxes = [control, _prepend("obj-2"), _gen("obj-3")] + list(extra)
    lines = [_ln(control["id"], 0, "obj-2", 0), _ln("obj-2", 0, "obj-3", 0)] + list(extra_lines)
    return boxes, lines


def _nest(box_id, label, boxes, lines, **kw):
    return _container(box_id, label, boxes, lines,
                      numinlets=kw.pop("numinlets", 0), numoutlets=kw.pop("numoutlets", 0), **kw)


def _patch(boxes, lines=()):
    return _make_patch(list(boxes), list(lines))


# ===========================================================================
# control_walk (downstream, bridges, `;` parser, depth)
# ===========================================================================


class TestControlWalkDownstream:
    def _down(self, d, start="obj-1", scope=None, **kw):
        g = PatchGraph.build(d)
        return list(g.control_walk(scope or g.top, start, downstream=True, **kw))

    def test_send_receive(self):
        d = _patch([_dial(), _send("obj-2", "s cut"), _recv("obj-3", "r cut"), _gen("obj-4")],
                   [_ln("obj-1", 0, "obj-2", 0), _ln("obj-3", 0, "obj-4", 0)])
        assert _ids(self._down(d)) == ["obj-2", "obj-3", "obj-4"]

    def test_send_long_names(self):
        d = _patch([_dial(), _send("obj-2", "send cut"), _recv("obj-3", "receive cut")],
                   [_ln("obj-1", 0, "obj-2", 0)])
        assert _ids(self._down(d)) == ["obj-2", "obj-3"]

    def test_other_channel_not_bridged(self):
        d = _patch([_dial(), _send("obj-2", "s cut"), _recv("obj-3", "r res")],
                   [_ln("obj-1", 0, "obj-2", 0)])
        assert _ids(self._down(d)) == ["obj-2"]

    def test_value_bridge(self):
        d = _patch([_dial(), _obj("obj-2", "v cut"), _obj("obj-3", "value cut"), _gen("obj-4")],
                   [_ln("obj-1", 0, "obj-2", 0), _ln("obj-3", 0, "obj-4", 0)])
        assert _ids(self._down(d)) == ["obj-2", "obj-3", "obj-4"]

    def test_pv_related_scopes_only(self):
        inner_a = _nest("obj-5", "p a", [_obj("in-1", "pv cut")], [])
        inner_b = _nest("obj-6", "p b", [_obj("in-1", "pv cut")], [])
        d = _patch([_dial(), _obj("obj-2", "pv cut"), inner_a],
                   [_ln("obj-1", 0, "obj-2", 0)])
        pairs = self._down(d)
        assert [(s.key, b) for s, b in pairs] == [("", "obj-2"), ("obj-5", "in-1")]
        # sibling subpatchers are not related to each other
        d2 = _patch([inner_a, inner_b])
        g = PatchGraph.build(d2)
        a = next(s for s in g.scopes if s.key == "obj-5")
        assert list(g.control_walk(a, "in-1", downstream=True)) == []

    def test_message_remote_targets(self):
        d = _patch([_dial(), _msg("obj-2", "; cut $1; res 0"), _recv("obj-3", "r cut"),
                    _obj("obj-4", "v res"), _recv("obj-5", "r other")],
                   [_ln("obj-1", 0, "obj-2", 0)])
        assert _ids(self._down(d)) == ["obj-2", "obj-3", "obj-4"]

    def test_message_carriage_return_target(self):
        d = _patch([_dial(), _msg("obj-2", ";\rwhrt pitch 7"), _recv("obj-3", "r whrt")],
                   [_ln("obj-1", 0, "obj-2", 0)])
        assert _ids(self._down(d)) == ["obj-2", "obj-3"]

    def test_escaped_semicolon_is_not_a_segment(self):
        d = _patch([_dial(), _msg("obj-2", "a \\; cut 1"), _recv("obj-3", "r cut")],
                   [_ln("obj-1", 0, "obj-2", 0)])
        assert _ids(self._down(d)) == ["obj-2"]

    def test_parser(self):
        from src.maxpat.graph import _message_remote_targets

        assert _message_remote_targets(_msg("m", "; cut 1; res 2")) == ["cut", "res"]
        assert _message_remote_targets(_msg("m", ";\rwhrt pitch 7")) == ["whrt"]
        assert _message_remote_targets(_msg("m", "1 2")) == []
        assert _message_remote_targets(_msg("m", ";")) == []
        assert _message_remote_targets({"maxclass": "message", "text": 7}) == []
        assert _message_remote_targets(_obj("m", "; cut 1")) == []

    def test_upstream_receive_reaches_message_and_send(self):
        d = _patch([_loadbang("obj-1"), _msg("obj-2", "; cut 0.5"), _recv("obj-3", "r cut"),
                    _dial("obj-4"), _send("obj-5", "s cut")],
                   [_ln("obj-1", 0, "obj-2", 0), _ln("obj-3", 0, "obj-4", 0)])
        g = PatchGraph.build(d)
        ids = _ids(g.control_walk(g.top, "obj-4", downstream=False))
        assert ids[:3] == ["obj-3", "obj-5", "obj-2"]
        assert "obj-1" in ids

    def test_signal_cord_never_followed(self):
        d = _patch([_cycle("obj-1"), _gen("obj-2")], [_ln("obj-1", 0, "obj-2", 0)])
        assert self._down(d) == []

    def test_crossing_into_p_and_out(self):
        inner = [_inlet("in-1"), _prepend("in-2", "prepend x"), _outlet("in-3")]
        p = _container("obj-2", "p route", inner,
                       [_ln("in-1", 0, "in-2", 0), _ln("in-2", 0, "in-3", 0)])
        d = _patch([_dial(), p, _gen("obj-3")],
                   [_ln("obj-1", 0, "obj-2", 0), _ln("obj-2", 0, "obj-3", 0)])
        assert _ids(self._down(d)) == ["in-2", "obj-3"]

    def test_depth_bound(self):
        boxes = [_dial()] + [_obj(f"obj-{i}", "t i") for i in range(2, 6)]
        lines = [_ln(f"obj-{i}", 0, f"obj-{i + 1}", 0) for i in range(1, 5)]
        d = _patch(boxes, lines)
        assert _ids(self._down(d, max_depth=2)) == ["obj-2", "obj-3"]
        assert _ids(self._down(d)) == ["obj-2", "obj-3", "obj-4", "obj-5"]

    def test_gen_scope_not_bridged(self):
        gen = _container("obj-9", "gen~", [_send("in-1", "s cut")], [],
                         numinlets=1, numoutlets=1, outlettype=["signal"],
                         classnamespace="dsp.gen")
        d = _patch([_dial(), _send("obj-2", "s cut"), gen, _recv("obj-3", "r cut")],
                   [_ln("obj-1", 0, "obj-2", 0)])
        g = PatchGraph.build(d)
        inner = next(s for s in g.scopes if s.key == "obj-9")
        assert list(g.control_walk(inner, "in-1", downstream=True)) == []


# ===========================================================================
# D-01: which classes are value holders
# ===========================================================================


class TestValueHolderClasses:
    @pytest.mark.parametrize("maxclass", _HOLDER_CLASSES)
    def test_holder_reported(self, maxclass, db):
        control = _ui("obj-1", maxclass)
        boxes, lines = _to_gen(control)
        boxes[1] = _prepend("obj-2", "prepend x")
        found = _q24(_review(boxes, lines, db))
        assert [r.finding for r in found] == [_generic_text(maxclass, "obj-1", "gen~", "obj-3")]
        assert found[0].suggestion == _SUGGESTION

    @pytest.mark.parametrize("maxclass", _EXCLUDED_CLASSES + ("mc.live.gain~", "comment"))
    def test_excluded_never_reported(self, maxclass, db):
        boxes, lines = _to_gen(_ui("obj-1", maxclass))
        assert _q24(_review(boxes, lines, db)) == []

    def test_dial_into_print_only(self, db):
        boxes = [_dial(), _send("obj-2", "print x")]
        assert _q24(_review(boxes, [_ln("obj-1", 0, "obj-2", 0)], db)) == []


# ===========================================================================
# D-03: reach
# ===========================================================================


class TestReach:
    def _one(self, d, db):
        found = _q24(review_structure(d, db=db))
        assert len(found) == 1, [r.finding for r in found]
        return found[0]

    def test_times_tilde_inlet_1(self, db):
        d = _patch([_dial(), _obj("obj-2", "*~ 0.", numinlets=2, outlettype=["signal"])],
                   [_ln("obj-1", 0, "obj-2", 1)])
        assert self._one(d, db).finding == _generic_text("dial", "obj-1", "*~ 0.", "obj-2")

    def test_through_embedded_p(self, db):
        inner = [_inlet("in-1"), _prepend("in-2", "prepend x"), _outlet("in-3")]
        p = _container("obj-2", "p route", inner,
                       [_ln("in-1", 0, "in-2", 0), _ln("in-2", 0, "in-3", 0)])
        d = _patch([_dial(), p, _gen("obj-3")],
                   [_ln("obj-1", 0, "obj-2", 0), _ln("obj-2", 0, "obj-3", 0)])
        assert self._one(d, db).finding == _generic_text("dial", "obj-1", "gen~", "obj-3")

    def test_into_embedded_bpatcher(self, db):
        inner = [_inlet("in-1"), _obj("in-2", "*~ 0.", numinlets=2, outlettype=["signal"])]
        bp = _container("obj-2", "", inner, [_ln("in-1", 0, "in-2", 1)],
                        maxclass="bpatcher", numinlets=1, numoutlets=0)
        d = _patch([_dial(), bp], [_ln("obj-1", 0, "obj-2", 0)])
        assert self._one(d, db).finding == _generic_text("dial", "obj-1", "*~ 0.", "in-2")

    def test_dial_inside_p_reaches_top(self, db):
        inner = [_dial("in-1"), _outlet("in-2")]
        p = _container("obj-1", "p ui", inner, [_ln("in-1", 0, "in-2", 0)],
                       numinlets=0, numoutlets=1)
        d = _patch([p, _prepend("obj-2"), _gen("obj-3")],
                   [_ln("obj-1", 0, "obj-2", 0), _ln("obj-2", 0, "obj-3", 0)])
        r = self._one(d, db)
        assert r.path == "obj-1"
        assert r.finding == "[p ui] " + _generic_text("dial", "in-1", "gen~", "obj-3")

    def test_external_bpatcher(self, db):
        bp = _box("obj-2", maxclass="bpatcher", numinlets=1, numoutlets=1,
                  outlettype=["signal"])
        bp["name"] = "voice.maxpat"
        d = _patch([_dial(), bp], [_ln("obj-1", 0, "obj-2", 0)])
        assert self._one(d, db).finding == _generic_text("dial", "obj-1", "bpatcher", "obj-2")

    def test_send_receive(self, db):
        d = _patch([_dial(), _send("obj-2", "s cut"), _recv("obj-3", "r cut"), _gen("obj-4")],
                   [_ln("obj-1", 0, "obj-2", 0), _ln("obj-3", 0, "obj-4", 0)])
        assert self._one(d, db).finding == _generic_text("dial", "obj-1", "gen~", "obj-4")

    def test_remote_message(self, db):
        d = _patch([_dial(), _msg("obj-2", "; cut $1"), _recv("obj-3", "r cut"), _gen("obj-4")],
                   [_ln("obj-1", 0, "obj-2", 0), _ln("obj-3", 0, "obj-4", 0)])
        assert self._one(d, db).finding == _generic_text("dial", "obj-1", "gen~", "obj-4")

    def test_value(self, db):
        d = _patch([_dial(), _obj("obj-2", "v cut"), _obj("obj-3", "v cut"), _gen("obj-4")],
                   [_ln("obj-1", 0, "obj-2", 0), _ln("obj-3", 0, "obj-4", 0)])
        assert self._one(d, db).finding == _generic_text("dial", "obj-1", "gen~", "obj-4")

    def test_pv_from_subpatcher_to_parent(self, db):
        inner = _nest("obj-1", "p a", [_dial("in-1"), _obj("in-2", "pv cut")],
                      [_ln("in-1", 0, "in-2", 0)])
        d = _patch([inner, _obj("obj-2", "pv cut"), _prepend("obj-3"), _gen("obj-4")],
                   [_ln("obj-2", 0, "obj-3", 0), _ln("obj-3", 0, "obj-4", 0)])
        r = self._one(d, db)
        assert r.path == "obj-1"
        assert r.finding == "[p a] " + _generic_text("dial", "in-1", "gen~", "obj-4")


# ===========================================================================
# Exclusions: the audio switches, rnbo scopes
# ===========================================================================


class TestExclusions:
    @pytest.mark.parametrize("target", [
        _obj("obj-2", "dac~", numinlets=2, numoutlets=0, outlettype=[]),
        _box("obj-2", maxclass="ezdac~", numinlets=2, numoutlets=0, outlettype=[]),
        _obj("obj-2", "mc.dac~", numinlets=1, numoutlets=0, outlettype=[]),
        _box("obj-2", maxclass="ezadc~", numinlets=1, numoutlets=2,
             outlettype=["signal", "signal"]),
    ], ids=["dac~", "ezdac~", "mc.dac~", "ezadc~"])
    def test_audio_switch_is_not_dsp(self, target, db):
        d = _patch([_ui("obj-1", "toggle"), target], [_ln("obj-1", 0, "obj-2", 0)])
        assert _q24(review_structure(d, db=db)) == []

    def test_adc_is_dsp(self, db):
        adc = _obj("obj-2", "adc~", numinlets=1, numoutlets=2, outlettype=["signal", "signal"])
        d = _patch([_ui("obj-1", "toggle"), adc], [_ln("obj-1", 0, "obj-2", 0)])
        assert _q24_ids(review_structure(d, db=db)) == ["obj-1"]

    def test_rnbo_scope_never_checked(self, db):
        boxes = [_dial("in-1"), _obj("in-2", "*~ 0.", numinlets=2, outlettype=["signal"])]
        lines = [_ln("in-1", 0, "in-2", 1)]
        rnbo = _container("obj-1", "rnbo~", boxes, lines, numinlets=1, numoutlets=1,
                          outlettype=["signal"], classnamespace="rnbo")
        assert _q24(review_structure(_patch([rnbo]), db=db)) == []


# ===========================================================================
# D-03: depth bound and cycles
# ===========================================================================


def _chain(n, tail_gen=True):
    boxes = [_dial()] + [_obj(f"obj-{i}", "t i") for i in range(2, n + 2)]
    lines = [_ln(f"obj-{i}", 0, f"obj-{i + 1}", 0) for i in range(1, n + 1)]
    if tail_gen:
        boxes.append(_gen("obj-999"))
        lines.append(_ln(f"obj-{n + 1}", 0, "obj-999", 0))
    return boxes, lines


class TestDepthAndCycles:
    def test_gen_at_depth_64_found(self, db):
        boxes, lines = _chain(63)
        assert _q24_ids(_review(boxes, lines, db)) == ["obj-1"]

    def test_gen_beyond_depth_64_not_found(self, db):
        boxes, lines = _chain(64)
        assert _q24(_review(boxes, lines, db)) == []

    def _loop(self, with_gen):
        boxes = [_dial(), _obj("obj-2", "t i"), _obj("obj-3", "+ 0", numinlets=2)]
        lines = [_ln("obj-1", 0, "obj-2", 0), _ln("obj-2", 0, "obj-3", 0),
                 _ln("obj-3", 0, "obj-2", 0)]
        if with_gen:
            boxes.append(_gen("obj-4"))
            lines.append(_ln("obj-3", 0, "obj-4", 0))
        return boxes, lines

    def test_cycle_without_dsp(self, db):
        boxes, lines = self._loop(False)
        assert _q24(_review(boxes, lines, db)) == []

    def test_cycle_with_dsp(self, db):
        boxes, lines = self._loop(True)
        assert _q24_ids(_review(boxes, lines, db)) == ["obj-1"]


# ===========================================================================
# Init routes (dial -> prepend cut -> gen~)
# ===========================================================================


class TestInitRoutes:
    def _ids(self, boxes, lines, db):
        return _q24_ids(_review(boxes, lines, db))

    def test_parameter_initial_clears(self, db):
        boxes, lines = _to_gen(_dial(**_param_initial()))
        assert self._ids(boxes, lines, db) == []

    def test_parameter_enable_without_initial_enable(self, db):
        attrs = _param_initial()
        del attrs["saved_attribute_attributes"]["valueof"]["parameter_initial_enable"]
        boxes, lines = _to_gen(_dial(**attrs))
        assert self._ids(boxes, lines, db) == ["obj-1"]

    def test_parameter_disabled_with_valueof_initial(self, db):
        attrs = _param_initial()
        attrs["parameter_enable"] = 0
        boxes, lines = _to_gen(_dial(**attrs))
        assert self._ids(boxes, lines, db) == ["obj-1"]

    def test_live_dial_parameter_initial(self, db):
        boxes, lines = _to_gen(_ui("obj-1", "live.dial", **_param_initial()))
        assert self._ids(boxes, lines, db) == []

    def test_loadmess(self, db):
        boxes, lines = _to_gen(_dial(), [_loadmess("obj-10", "loadmess 0.5")],
                               [_ln("obj-10", 0, "obj-1", 0)])
        assert self._ids(boxes, lines, db) == []

    def test_loadbang_trigger_message(self, db):
        boxes, lines = _to_gen(
            _dial(), [_loadbang("obj-10"), _obj("obj-11", "t b"), _msg("obj-12", "0.5")],
            [_ln("obj-10", 0, "obj-11", 0), _ln("obj-11", 0, "obj-12", 0),
             _ln("obj-12", 0, "obj-1", 0)])
        assert self._ids(boxes, lines, db) == []

    def test_live_thisdevice(self, db):
        boxes, lines = _to_gen(
            _dial(), [_obj("obj-10", "live.thisdevice", numoutlets=3), _msg("obj-12", "0.5")],
            [_ln("obj-10", 0, "obj-12", 0), _ln("obj-12", 0, "obj-1", 0)])
        assert self._ids(boxes, lines, db) == []

    @pytest.mark.parametrize("text", ["; cut 0.5", ";\rcut 0.5"])
    def test_loadbang_remote_message(self, text, db):
        boxes, lines = _to_gen(
            _dial(), [_loadbang("obj-10"), _msg("obj-11", text), _recv("obj-12", "r cut")],
            [_ln("obj-10", 0, "obj-11", 0), _ln("obj-12", 0, "obj-1", 0)])
        assert self._ids(boxes, lines, db) == []

    def test_loadmess_send_receive(self, db):
        boxes, lines = _to_gen(
            _dial(), [_loadmess("obj-10"), _send("obj-11", "s cutin"), _recv("obj-12", "r cutin")],
            [_ln("obj-10", 0, "obj-11", 0), _ln("obj-12", 0, "obj-1", 0)])
        assert self._ids(boxes, lines, db) == []

    def test_loadmess_value(self, db):
        boxes, lines = _to_gen(
            _dial(), [_loadmess("obj-10"), _obj("obj-11", "v cutin"), _obj("obj-12", "v cutin")],
            [_ln("obj-10", 0, "obj-11", 0), _ln("obj-12", 0, "obj-1", 0)])
        assert self._ids(boxes, lines, db) == []

    def test_loadmess_inside_p(self, db):
        p = _container("obj-10", "p init", [_loadmess("in-1"), _outlet("in-2")],
                       [_ln("in-1", 0, "in-2", 0)], numinlets=0, numoutlets=1)
        boxes, lines = _to_gen(_dial(), [p], [_ln("obj-10", 0, "obj-1", 0)])
        assert self._ids(boxes, lines, db) == []

    def test_no_route_reported(self, db):
        boxes, lines = _to_gen(_dial())
        assert self._ids(boxes, lines, db) == ["obj-1"]


# ===========================================================================
# D-02: per-control pattr binding (dial varname "cut")
# ===========================================================================


def _pattr(box_id, text="pattr cutp"):
    return _obj(box_id, text, numinlets=1, numoutlets=3)


def _autopattr(box_id, text="autopattr", restore=None):
    box = _obj(box_id, text, numinlets=1, numoutlets=4)
    if restore is not None:
        box["restore"] = restore
    return box


def _pattrstorage(box_id, text="pattrstorage presets"):
    return _obj(box_id, text, numinlets=1, numoutlets=5)


class TestPattrBinding:
    def _ids(self, boxes, lines=(), db=None):
        return _q24_ids(review_structure(_patch(boxes, lines), db=db))

    def _base(self, varname="cut"):
        return _to_gen(_dial(varname=varname) if varname else _dial())

    def test_cord_into_pattr(self, db):
        boxes, lines = self._base()
        assert self._ids(boxes + [_pattr("obj-10")],
                         lines + [_ln("obj-1", 0, "obj-10", 0)], db) == []

    def test_cord_out_of_pattr(self, db):
        boxes, lines = self._base()
        assert self._ids(boxes + [_pattr("obj-10")],
                         lines + [_ln("obj-10", 1, "obj-1", 0)], db) == []

    def test_bindto_anywhere(self, db):
        boxes, lines = self._base()
        sub = _nest("obj-10", "p state", [_pattr("in-1", "pattr x @bindto cut")], [])
        assert self._ids(boxes + [sub], lines, db) == []

    def test_bindto_hierarchical(self, db):
        boxes, lines = self._base()
        assert self._ids(boxes + [_pattr("obj-10", "pattr x @bindto sub::cut")], lines, db) == []

    def test_bindto_other_name_reported(self, db):
        boxes, lines = self._base()
        assert self._ids(boxes + [_pattr("obj-10", "pattr x @bindto res")], lines, db) == ["obj-1"]

    def test_autopattr_with_pattrstorage_in_subpatcher(self, db):
        boxes, lines = self._base()
        presets = _nest("obj-11", "p presets", [_pattrstorage("in-1")], [])
        assert self._ids(boxes + [_autopattr("obj-10"), presets], lines, db) == []

    def test_autopattr_restore_dict(self, db):
        boxes, lines = self._base()
        ap = _autopattr("obj-10", restore={"cut": [0.5]})
        assert self._ids(boxes + [ap], lines, db) == []

    def test_autopattr_restore_dict_autorestore_off(self, db):
        boxes, lines = self._base()
        ap = _autopattr("obj-10", "autopattr @autorestore 0", restore={"cut": [0.5]})
        assert self._ids(boxes + [ap], lines, db) == ["obj-1"]

    def test_autopattr_without_varname_reported(self, db):
        boxes, lines = self._base(varname=None)
        assert self._ids(boxes + [_autopattr("obj-10"), _pattrstorage("obj-11")],
                         lines, db) == ["obj-1"]

    def test_autopattr_in_other_subpatcher_reported(self, db):
        boxes, lines = self._base()
        other = _nest("obj-10", "p other", [_autopattr("in-1")], [])
        assert self._ids(boxes + [other, _pattrstorage("obj-11")], lines, db) == ["obj-1"]

    def test_unbound_control_in_pattr_patch_still_reported(self, db):
        boxes = [_dial("obj-1", varname="cut"), _dial("obj-4"), _prepend("obj-2"),
                 _gen("obj-3"), _autopattr("obj-10"), _pattrstorage("obj-11")]
        lines = [_ln("obj-1", 0, "obj-2", 0), _ln("obj-4", 0, "obj-2", 0),
                 _ln("obj-2", 0, "obj-3", 0)]
        assert self._ids(boxes, lines, db) == ["obj-4"]


# ===========================================================================
# Followers: a holder driven by another holder
# ===========================================================================


def _follower_chain(dial, extra=(), extra_lines=()):
    """dial (obj-1) -> scale -> flonum (obj-3) -> prepend cut -> gen~."""
    boxes = [dial, _obj("obj-2", "scale 0 127 0. 1."), _flonum("obj-3"),
             _prepend("obj-4"), _gen("obj-5")] + list(extra)
    lines = [_ln("obj-1", 0, "obj-2", 0), _ln("obj-2", 0, "obj-3", 0),
             _ln("obj-3", 0, "obj-4", 0), _ln("obj-4", 0, "obj-5", 0)] + list(extra_lines)
    return boxes, lines


class TestFollower:
    _chain = staticmethod(_follower_chain)

    def test_initialized_leader(self, db):
        boxes, lines = self._chain(_dial(), [_loadmess("obj-10")], [_ln("obj-10", 0, "obj-1", 0)])
        assert _q24_ids(_review(boxes, lines, db)) == []

    def test_uninitialized_leader_reported_once(self, db):
        boxes, lines = self._chain(_dial())
        assert _q24_ids(_review(boxes, lines, db)) == ["obj-1"]

    def test_parameter_initial_leader(self, db):
        boxes, lines = self._chain(_dial(**_param_initial()))
        assert _q24_ids(_review(boxes, lines, db)) == []

    def test_mutual_pair_both_reported(self, db):
        boxes = [_dial(), _flonum("obj-2"), _prepend("obj-3", "prepend set"),
                 _prepend("obj-4"), _gen("obj-5")]
        lines = [_ln("obj-1", 0, "obj-2", 0), _ln("obj-2", 0, "obj-3", 0),
                 _ln("obj-3", 0, "obj-1", 0), _ln("obj-2", 0, "obj-4", 0),
                 _ln("obj-4", 0, "obj-5", 0)]
        assert sorted(_q24_ids(_review(boxes, lines, db))) == ["obj-1", "obj-2"]


# ===========================================================================
# Robustness and purity
# ===========================================================================


def _junk_boxes():
    return [
        {"id": "obj-1", "maxclass": "live.dial", "parameter_enable": 1,
         "saved_attribute_attributes": 5, "outlettype": ["", ""]},
        {"id": "obj-2", "maxclass": "live.dial", "parameter_enable": 1,
         "saved_attribute_attributes": {"valueof": 3}, "outlettype": ["", ""]},
        {"id": "obj-3", "maxclass": "dial", "varname": 5, "outlettype": [""]},
        _autopattr("obj-4", restore="x"),
        {"id": "obj-5", "maxclass": "newobj", "text": None},
        _pattr("obj-6", "pattr @bindto"),
        {"id": "obj-7", "maxclass": "message", "text": 7},
        _send("obj-8", "s"), _recv("obj-9", "r"), _obj("obj-10", "v"), _obj("obj-11", "pv"),
        _gen("obj-12"), _pattrstorage("obj-13"),
        {"id": "obj-14", "maxclass": "gain~", "outlettype": None, "parameter_enable": "x"},
        {"id": "obj-15", "maxclass": "toggle", "outlettype": "int"},
    ]


def _junk_lines():
    lines = []
    for i in range(1, 16):
        lines.append(_ln(f"obj-{i}", 0, "obj-12", 0))
    lines += [
        _ln("obj-1", "0", "obj-12", 0),
        _ln("obj-2", 0.5, "obj-12", 0),
        _ln("obj-missing", 0, "obj-3", 0),
        _ln("obj-3", 0, "obj-missing", 0),
        _ln("obj-7", 0, "obj-1", 0),
        _ln("obj-8", 0, "obj-9", 0),
    ]
    return lines


class TestRobustness:
    def test_review_structure_never_raises(self, db):
        d = _patch(_junk_boxes(), _junk_lines())
        assert isinstance(review_structure(d, db=db, is_new=True), list)
        nested = _patch([_nest("obj-1", "p junk", _junk_boxes(), _junk_lines())])
        assert isinstance(review_structure(nested, db=db), list)

    def test_control_walk_never_raises(self):
        d = _patch(_junk_boxes(), _junk_lines())
        g = PatchGraph.build(d)
        for box_id in list(g.top.boxes) + ["obj-missing", None, 5]:
            for downstream in (True, False):
                assert isinstance(list(g.control_walk(g.top, box_id, downstream=downstream)), list)


def _every_shape_patch():
    shapes = []
    shapes.append(_latent())
    shapes.append(_to_gen(_dial(varname="cut")))
    shapes.append(_follower_chain(_dial()))
    shapes.append((_junk_boxes(), _junk_lines()))
    for maxclass in _HOLDER_CLASSES + _EXCLUDED_CLASSES:
        shapes.append(_to_gen(_ui("obj-1", maxclass)))
    shapes.append(_to_gen(_dial(), [_loadbang("obj-10"), _msg("obj-11", "; cut 0.5"),
                                    _recv("obj-12", "r cut")],
                          [_ln("obj-10", 0, "obj-11", 0), _ln("obj-12", 0, "obj-1", 0)]))
    shapes.append(_to_gen(_dial(varname="cut"), [_autopattr("obj-10", restore={"cut": [1]}),
                                                 _pattr("obj-11", "pattr x @bindto cut")]))
    boxes = [_nest(f"obj-{i + 1}", f"p s{i}", b, l) for i, (b, l) in enumerate(shapes)]
    boxes.append(_pattrstorage("obj-900"))
    return _patch(boxes)


class TestPurity:
    def test_review_patch_does_not_mutate(self, db):
        d = _every_shape_patch()
        before = copy.deepcopy(d)
        res = review_patch(d, db=db, is_new=True)
        assert _q24(res)
        assert d == before


# ===========================================================================
# Committed corpus: every Q24 finding is a pinned, reasoned warning
# ===========================================================================

_REPO_ROOT = Path(__file__).resolve().parent.parent
_ALLOWLIST_PATH = Path(__file__).resolve().parent / "uninitialized_state_allowlist.json"
_CORPUS = sorted(
    {p.relative_to(_REPO_ROOT).as_posix()
     for pattern in ("*.maxpat", "*.maxhelp")
     for p in (_REPO_ROOT / "patches").rglob(pattern)}
)
_LATENT_CASES = (
    ("patches/FDNVerb/generated/FDNVerb.maxhelp", "obj-29"),
    ("patches/disintegrate/generated/disintegrate-helper.maxpat", "obj-10"),
    ("patches/granularsynthtest/generated/granularsynthtest.maxpat", "obj-26"),
    ("patches/spectraldetector/generated/spectraldetector.maxpat", "obj-8"),
)


def _allowlist() -> dict:
    with open(_ALLOWLIST_PATH) as f:
        return json.load(f)


def _load_rel(rel: str) -> dict:
    with open(_REPO_ROOT / rel) as f:
        return json.load(f)


_CORPUS_CACHE: dict = {}


def _corpus_q24(rel: str, db) -> list:
    """``(path, box_id, severity)`` of every Q24 finding of *rel*, from
    ``review_patch(d, db=db)`` (the default edit severity); cached."""
    if rel not in _CORPUS_CACHE:
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res = review_patch(_load_rel(rel), db=db)
        out = []
        for r in _q24(res):
            out.append((r.path, r.box_ids[0] if r.box_ids else None, r.severity))
        _CORPUS_CACHE[rel] = out
    return _CORPUS_CACHE[rel]


def _box_at(d: dict, path: str, box_id: str):
    patcher = d.get("patcher", {})
    for step in [s for s in path.split("/") if s]:
        nxt = None
        for entry in patcher.get("boxes", []):
            box = entry.get("box", {})
            if box.get("id") == step and isinstance(box.get("patcher"), dict):
                nxt = box["patcher"]
        if nxt is None:
            return None
        patcher = nxt
    for entry in patcher.get("boxes", []):
        box = entry.get("box", {})
        if box.get("id") == box_id:
            return box
    return None


class TestCommittedCorpus:
    def test_corpus_found(self):
        assert len(_CORPUS) >= 50

    @pytest.mark.parametrize("rel", _CORPUS)
    def test_committed_q24_findings_match_allowlist(self, rel, db):
        found = _corpus_q24(rel, db)
        entries = _allowlist()["patches"].get(rel, [])
        assert {(p, b) for p, b, _s in found} == {(e["path"], e["box_id"]) for e in entries}
        assert len(found) == len(entries)
        assert all(s == "warning" for _p, _b, s in found), found

    def test_allowlist_entries_are_valid(self):
        data = _allowlist()
        assert data.get("_doc", "").strip()
        assert data["patches"]
        for rel, entries in data["patches"].items():
            assert (_REPO_ROOT / rel).is_file(), rel
            assert entries, f"{rel} is listed with no entries"
            d = _load_rel(rel)
            for e in entries:
                assert e.get("reason", "").strip(), (rel, e)
                assert e.get("severity") == "warning", (rel, e)
                assert e.get("kind") == "uninitialized_state", (rel, e)
                box = _box_at(d, e.get("path", ""), e.get("box_id"))
                assert box is not None, (rel, e)
                assert box.get("maxclass") == e.get("maxclass"), (rel, e, box.get("maxclass"))

    @pytest.mark.parametrize("rel,box_id", _LATENT_CASES)
    def test_spec_latent_cases_are_warnings(self, rel, box_id, db):
        entries = _allowlist()["patches"].get(rel, [])
        assert any(e["box_id"] == box_id and e["path"] == "" for e in entries)
        hits = [s for p, b, s in _corpus_q24(rel, db) if p == "" and b == box_id]
        assert hits == ["warning"]

    def test_corpus_has_no_q24_blocker(self, db):
        blockers = [
            (rel, p, b) for rel in _CORPUS
            for p, b, s in _corpus_q24(rel, db) if s == "blocker"
        ]
        assert blockers == []
