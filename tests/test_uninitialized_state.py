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
import re
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


def _strip_prefix(finding: str) -> str:
    if finding.startswith("[") and "] " in finding:
        return finding.split("] ", 1)[1]
    return finding


def _q24(results):
    return [r for r in results if _strip_prefix(r.finding).startswith(_Q24)]


_ID_RE = re.compile(r"Uninitialized state: '[^']*' \((obj-\d+)\)")


def _q24_ids(results):
    out = []
    for r in _q24(results):
        m = _ID_RE.search(_strip_prefix(r.finding))
        out.append(m.group(1) if m else None)
    return out


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
