"""Regression tests for the 261022-ud6 WP2 review fixes (patch model + save path).

Finding ids refer to review-patcher.md of quick task 261022-ud6. Committed
patches under ``patches/`` are only read (json.load + deepcopy); every write
goes to pytest's ``tmp_path``.
"""

from __future__ import annotations

import copy
import json
import warnings
from pathlib import Path

import pytest

from src.maxpat.patcher import Patcher

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load(rel: str) -> Patcher:
    """A Patcher from a committed patch, read-only."""
    with open(REPO_ROOT / rel) as fh:
        return Patcher.from_dict(json.load(fh))


def _box(p: Patcher, box_id: str):
    for b in p.boxes:
        if b.id == box_id:
            return b
    raise KeyError(box_id)


def _box_dict(d: dict, box_id: str) -> dict:
    for e in d["patcher"]["boxes"]:
        if e["box"]["id"] == box_id:
            return e["box"]
    raise KeyError(box_id)


# ---------------------------------------------------------------------------
# CR-01: replace_box never silently drops an embedded patcher
# ---------------------------------------------------------------------------

AMP = "patches/amplitude-follower/generated/amplitude-follower.maxpat"


class TestReplaceKeepsEmbeddedPatcher:
    def test_gen_to_gen_keeps_code_and_io(self):
        p = _load(AMP)
        old = _box(p, "obj-8")
        inner_before = old._inner_patcher.to_dict()
        io_before = (old.numinlets, old.numoutlets, list(old.outlettype))

        result = p.replace_box_safe(old, "gen~")

        new = result.box
        assert new._inner_patcher is not None
        assert new._inner_patcher.to_dict() == inner_before
        assert new._inner_patcher._parent_box is new
        assert new._inner_patcher._parent_patcher is p
        assert (new.numinlets, new.numoutlets, list(new.outlettype)) == io_before
        assert result.orphaned == []
        d = _box_dict(p.to_dict(), new.id)
        assert d["patcher"] == inner_before["patcher"]

    def test_gen_to_mc_gen_keeps_code(self):
        p = _load(AMP)
        old = _box(p, "obj-8")
        inner_before = old._inner_patcher.to_dict()

        result = p.replace_box_safe(old, "mc.gen~")

        new = result.box
        assert new.text == "mc.gen~"
        assert new._inner_patcher.to_dict() == inner_before
        assert new.numinlets == 1 and new.numoutlets == 1
        assert new.outlettype == ["multichannelsignal"]
        assert result.orphaned == []

    def test_incompatible_replacement_refused_before_any_change(self):
        p = _load(AMP)
        old = _box(p, "obj-8")
        before = p.to_dict()

        with pytest.raises(ValueError, match="embedded patcher"):
            p.replace_box(old, "cycle~")
        with pytest.raises(ValueError, match="embedded patcher"):
            p.replace_box_safe(old, "cycle~")

        assert p.to_dict() == before
        assert old in p.boxes

    def test_subpatcher_replacement_refused(self):
        p = Patcher()
        box, inner = p.add_subpatcher("ctl", inlets=1, outlets=1)
        with pytest.raises(ValueError, match="embedded patcher"):
            p.replace_box(box, "t", args=["b"])
        assert box in p.boxes and box._inner_patcher is inner


# ---------------------------------------------------------------------------
# WR-02: the replacement keeps the old box id
# ---------------------------------------------------------------------------


class TestReplaceKeepsId:
    def test_new_box_reuses_old_id(self):
        p = Patcher()
        old = p.add_box("cycle~", ["440"])
        dst = p.add_box("dac~")
        p.add_connection(old, 0, dst, 0)
        old_id = old.id

        result = p.replace_box_safe(old, "saw~", args=["220"])

        assert result.box.id == old_id
        assert old not in p.boxes
        assert [(l.source_id, l.dest_id) for l in p.lines] == [(old_id, dst.id)]

    def test_replace_box_plain_reuses_id(self):
        p = Patcher()
        old = p.add_box("cycle~", ["440"])
        old_id = old.id
        result = p.replace_box(old, "saw~")
        assert result.box.id == old_id
        assert result.orphaned == []

    def test_preexisting_blocker_still_saves_after_replace(self, tmp_path):
        """slot.maxpat carries a fan-out blocker on buffer~ obj-1: replacing
        that box with itself introduces nothing, so the gate must not refuse."""
        from src.maxpat.hooks import _gate_report

        with open(REPO_ROOT / "patches/rhythmic-sampler/generated/slot.maxpat") as fh:
            baseline = json.load(fh)
        p = Patcher.from_dict(baseline)
        p.replace_box_safe(_box(p, "obj-1"), "buffer~", args=["#1"])
        report = _gate_report(p.to_dict(), baseline, [baseline])
        assert report.new_blockers == []


# ---------------------------------------------------------------------------
# IN-02: a same-class replacement keeps the box size
# ---------------------------------------------------------------------------


class TestReplaceKeepsSize:
    def test_same_ui_class_keeps_size(self):
        p = _load("patches/FDNVerb/generated/FDNVerb.maxpat")
        old = _box(p, "obj-33")
        rect = list(old.patching_rect)
        result = p.replace_box_safe(old, "live.dial")
        assert result.box.patching_rect == rect

    def test_same_text_newobj_keeps_size(self):
        p = _load(AMP)
        rect = list(_box(p, "obj-8").patching_rect)
        result = p.replace_box_safe(_box(p, "obj-8"), "gen~")
        assert result.box.patching_rect == rect

    def test_different_newobj_text_is_resized(self):
        p = Patcher()
        old = p.add_box("cycle~", ["440"], x=40, y=50)
        old.patching_rect[2] = 300.0
        result = p.replace_box(old, "saw~")
        assert result.box.patching_rect[:2] == [40.0, 50.0]
        assert result.box.patching_rect[2] != 300.0


# ---------------------------------------------------------------------------
# WR-01: the gate's patcher paths key on box id, not box text
# ---------------------------------------------------------------------------


def _sub_dict() -> dict:
    """Top-level ``p ctl`` (inner inlets obj-1 x50 / obj-2 x130, outlet obj-3)."""
    p = Patcher()
    box, inner = p.add_subpatcher("ctl", inlets=2, outlets=1)
    inner.add_connection(inner.get_inlets()[0], 0, inner.get_outlets()[0], 0)
    n = p.add_box("number")
    pr = p.add_box("print")
    p.add_connection(n, 0, box, 0)
    p.add_connection(box, 0, pr, 0)
    return p.to_dict()


def _ctl(d: dict) -> dict:
    for e in d["patcher"]["boxes"]:
        if (e["box"].get("text") or "").startswith("p ctl"):
            return e["box"]
    raise KeyError("p ctl")


class TestGatePathsKeyOnId:
    def test_inlet_swap_plus_rename_still_refused(self):
        from src.maxpat.hooks import _gate_report

        base = _sub_dict()
        new = copy.deepcopy(base)
        ctl = _ctl(new)
        inner = {e["box"]["id"]: e["box"] for e in ctl["patcher"]["boxes"]}
        a, b = inner["obj-1"]["patching_rect"], inner["obj-2"]["patching_rect"]
        a[0], b[0] = b[0], a[0]
        ctl["text"] = "p ctl x"

        report = _gate_report(new, base, [base])
        assert report.port_changes, report

    def test_rename_alone_reports_no_removed_cords(self):
        from src.maxpat.hooks import _gate_report

        base = _sub_dict()
        new = copy.deepcopy(base)
        _ctl(new)["text"] = "p ctl renamed"

        report = _gate_report(new, base, [base])
        assert report.removed_cords == []
        assert report.port_changes == []

    def test_labels_still_name_the_subpatcher(self):
        from src.maxpat.hooks import _gate_report, _path_labels

        base = _sub_dict()
        new = copy.deepcopy(base)
        _ctl(new)["patcher"]["lines"] = []
        report = _gate_report(new, base, [base])
        (cpath, *_rest), = report.removed_cords
        assert "p ctl" in _path_labels(new)[cpath]


# ---------------------------------------------------------------------------
# Q7 / Q33 (validation IN-01): the gate keys on structured rule + box ids
# ---------------------------------------------------------------------------


class TestStructuredFindingKey:
    def test_reworded_critic_finding_with_same_rule_matches(self):
        from src.maxpat.critics import CriticResult
        from src.maxpat.hooks import _finding_key

        a = CriticResult("blocker", "Fan-out without trigger on 'x' (obj-3)", "s",
                         rule="fan_out_without_trigger", box_ids=("obj-3",), port=0)
        b = CriticResult("blocker", "Outlet 0 of obj-3 fans out with no trigger", "t",
                         rule="fan_out_without_trigger", box_ids=("obj-3",), port=0)
        assert _finding_key(a) == _finding_key(b)

    def test_rule_box_ids_port_and_path_distinguish(self):
        from src.maxpat.critics import CriticResult
        from src.maxpat.hooks import _finding_key

        base = dict(rule="fan_out_without_trigger", box_ids=("obj-3",), port=0)
        a = CriticResult("blocker", "same", "s", **base)
        for change in ({"rule": "gain_staging"}, {"box_ids": ("obj-4",)}, {"port": 1}):
            kw = {**base, **change}
            assert _finding_key(a) != _finding_key(CriticResult("blocker", "same", "s", **kw))
        assert _finding_key(a) != _finding_key(
            CriticResult("blocker", "same", "s", "obj-9", **base))

    def test_rule_without_box_ids_keeps_text_template(self):
        from src.maxpat.critics import CriticResult
        from src.maxpat.hooks import _finding_key

        a = CriticResult("blocker", "Patch has no output stage", "s", rule="r")
        b = CriticResult("blocker", "Something else entirely", "s", rule="r")
        assert _finding_key(a) != _finding_key(b)

    def test_validation_result_with_structured_ids(self):
        """WP1 adds ``rule`` / ``box_ids`` to ValidationResult; the key uses them
        when present (a subclass stands in for the new slots here)."""
        from src.maxpat.hooks import _finding_key
        from src.maxpat.validation import ValidationResult

        class VR(ValidationResult):
            pass

        a = VR("objects", "error", "Unknown object 'foo' (obj-2)")
        a.rule, a.box_ids = "unknown_object", ("obj-2",)
        b = VR("objects", "error", "No such object: foo [obj-2]")
        b.rule, b.box_ids = "unknown_object", ("obj-2",)
        assert _finding_key(a) == _finding_key(b)
        c = ValidationResult("objects", "error", "Unknown object 'foo' (obj-2)")
        assert _finding_key(c) != _finding_key(a)
