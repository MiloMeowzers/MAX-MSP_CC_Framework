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
