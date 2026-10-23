"""WP7a (quick 261022-ud6): contrast handoffs.

* WP2 -> WP3: the layout critic skips self-painted boxes
  (``aesthetics.paints_unknown_background``), the same rule the repair pass
  already follows -- bach.roll's text sits on its own white staff.
* WP3 -> aesthetics (Q26 follow-up): untinted ``number`` / ``flonum`` /
  ``textbutton`` boxes paint a theme fill. PROVENANCE (Max 9.2.0):
  number.maxref.xml ``bgcolor`` dynamiccolor_default ``bgcolor`` -> the
  default.maxtheme styledefaults ``bgcolor`` 0.125 (flonum is the same
  object); textbutton.maxref.xml ``bgcolor`` dynamiccolor_default
  ``live_control_bg`` -> default.maxtheme colour 0.262.
"""
import copy
import json
from pathlib import Path

import pytest

from src.maxpat.aesthetics import (
    THEME_FILL_MAXCLASSES,
    paints_unknown_background,
    repair_text_contrast,
    resolve_effective_background,
)
from src.maxpat.critics.layout_critic import review_layout
from src.maxpat.patcher import Patcher

REPO_ROOT = Path(__file__).resolve().parent.parent
PHYS = REPO_ROOT / "patches/physics-composition/generated/physics-composition.maxpat"

CANVAS = [0.235, 0.235, 0.235, 1.0]


def _contrast(results):
    return [r for r in results if r.rule == "text_contrast"]


class TestLayoutCriticSkipsSelfPainted:
    def test_bach_roll_on_physics_composition_not_flagged(self):
        d = json.loads(PHYS.read_text())
        hits = [r for r in _contrast(review_layout(d)) if "obj-67" in r.box_ids]
        assert hits == []

    def test_synthetic_bach_roll_not_flagged(self):
        d = {"patcher": {"boxes": [{"box": {
            "id": "obj-1", "maxclass": "bach.roll",
            "patching_rect": [10, 10, 300, 100], "numinlets": 6, "numoutlets": 9,
            "textcolor": [0.0, 0.0, 0.0, 1.0],
        }}], "lines": []}}
        assert _contrast(review_layout(d)) == []

    def test_comment_still_flagged(self):
        d = {"patcher": {"boxes": [{"box": {
            "id": "obj-1", "maxclass": "comment", "text": "dark",
            "patching_rect": [10, 10, 100, 20], "numinlets": 1, "numoutlets": 0,
            "textcolor": [0.1, 0.1, 0.1, 1.0],
        }}], "lines": []}}
        assert len(_contrast(review_layout(d))) == 1


class TestThemeFills:
    @pytest.mark.parametrize("maxclass,grey", [
        ("number", 0.125), ("flonum", 0.125), ("textbutton", 0.262),
        ("newobj", 0.172), ("message", 0.172), ("umenu", 0.172),
    ])
    def test_untinted_box_resolves_to_theme_fill(self, maxclass, grey):
        assert maxclass in THEME_FILL_MAXCLASSES
        res = resolve_effective_background(
            {}, [0, 0, 50, 20], False, None, [], [], CANVAS, maxclass=maxclass)
        assert res.space == "own"
        assert res.color[:3] == pytest.approx([grey] * 3, abs=1e-3)
        assert not paints_unknown_background(maxclass, {})

    @pytest.mark.parametrize("maxclass", ["number", "flonum", "textbutton"])
    def test_transparent_fill_falls_through(self, maxclass):
        res = resolve_effective_background(
            {"bgcolor": [0, 0, 0, 0]}, [0, 0, 50, 20], False, None, [], [],
            CANVAS, maxclass=maxclass)
        assert res.space == "patching"
        assert res.color == CANVAS

    def test_unknown_self_painted_class_still_unknown(self):
        assert paints_unknown_background("bach.roll", {})
        assert paints_unknown_background("jit.cellblock", {})

    def test_repair_recolours_dark_text_on_untinted_number(self):
        p = Patcher()
        nb = p.add_box("number", [], x=20, y=20)
        nb.extra_attrs["textcolor"] = [0.0, 0.0, 0.0, 1.0]
        # A light panel underneath must not decide: the number paints 0.125.
        panel = p.add_panel(0, 0, 200, 100, gradient=False)
        panel.extra_attrs["bgcolor"] = [0.95, 0.95, 0.95, 1.0]
        assert repair_text_contrast(p) == 1
        assert sum(nb.extra_attrs["textcolor"][:3]) / 3 > 0.5

    def test_critic_scores_untinted_number_on_its_own_fill(self):
        d = {"patcher": {"boxes": [
            {"box": {"id": "obj-1", "maxclass": "number",
                     "patching_rect": [20, 20, 50, 22], "numinlets": 1,
                     "numoutlets": 2, "textcolor": [0.0, 0.0, 0.0, 1.0]}},
            {"box": {"id": "obj-2", "maxclass": "panel",
                     "patching_rect": [0, 0, 200, 100], "numinlets": 1,
                     "numoutlets": 0, "bgcolor": [0.95, 0.95, 0.95, 1.0]}},
        ], "lines": []}}
        hits = _contrast(review_layout(copy.deepcopy(d)))
        assert len(hits) == 1 and "own background" in hits[0].finding
