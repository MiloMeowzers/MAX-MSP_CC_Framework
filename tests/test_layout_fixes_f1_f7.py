"""Regression tests for fix-plan Q27: layout findings F1-F7 of the
2026-10-11 repo review (.planning/reviews/2026-10-11-repo-review.md, 1F).

One test class per finding, plus the shared ``rendered_rect`` model
(F5) and robustness / purity checks on malformed input.
"""

from __future__ import annotations

import copy

import pytest

from src.maxpat.critics.layout_critic import review_layout
from src.maxpat.patcher import Patcher
from src.maxpat import sizing as _sizing


def rendered_rect(box, **kw):
    """Late-bound so each test reports its own failure (not one import error)."""
    return _sizing.rendered_rect(box, **kw)


def is_max_saved(props):
    return _sizing.is_max_saved(props)


def _make_patch(boxes: list[dict], lines: list[dict] | None = None,
                appversion: dict | None = None) -> dict:
    patcher: dict = {
        "boxes": [{"box": b} for b in boxes],
        "lines": [{"patchline": pl} for pl in (lines or [])],
    }
    if appversion is not None:
        patcher["appversion"] = appversion
    return {"patcher": patcher}


def _overlaps(results) -> list:
    return [r for r in results if r.finding.startswith("Overlapping boxes: ")]


def _intersect(a, b) -> bool:
    ax, ay, aw, ah = a[:4]
    bx, by, bw, bh = b[:4]
    return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah


# ---------------------------------------------------------------------------
# F5: the shared rendered_rect model
# ---------------------------------------------------------------------------

class TestRenderedRect:

    def test_message_uses_len8_plus_25(self):
        d = {"maxclass": "message", "text": "set foo bar baz qux",
             "patching_rect": [30.0, 30.0, 149.0, 22.0]}
        assert rendered_rect(d) == [30.0, 30.0, 177.0, 22.0]

    def test_message_keeps_wider_stored_width(self):
        d = {"maxclass": "message", "text": "go",
             "patching_rect": [0.0, 0.0, 100.0, 22.0]}
        assert rendered_rect(d)[2] == 100.0

    def test_message_longest_line(self):
        d = {"maxclass": "message", "text": "ab\rabcd\nabc",
             "patching_rect": [0.0, 0.0, 10.0, 22.0]}
        assert rendered_rect(d)[2] == 4 * 8 + 25

    def test_message_max_saved_keeps_stored_width(self):
        d = {"maxclass": "message", "text": "set foo bar baz qux",
             "patching_rect": [30.0, 30.0, 149.0, 22.0]}
        assert rendered_rect(d, max_saved=True) == [30.0, 30.0, 149.0, 22.0]

    def test_comment_single_line_text_extent(self):
        d = {"maxclass": "comment", "text": "hello world label",
             "patching_rect": [10.0, 20.0, 135.0, 20.0]}
        r = rendered_rect(d)
        assert r[:2] == [10.0, 20.0]
        assert r[2] == pytest.approx(105.2)
        assert r[3] == pytest.approx(20.0)

    def test_comment_wraps_at_stored_width(self):
        d = {"maxclass": "comment", "text": "x" * 100,
             "patching_rect": [0.0, 0.0, 150.0, 20.0]}
        r = rendered_rect(d)
        assert r[2] == pytest.approx(150.0)
        assert r[3] == pytest.approx(62.0)

    def test_comment_below_wrap_ratio_overflows_one_line(self):
        d = {"maxclass": "comment", "text": "y" * 50,
             "patching_rect": [0.0, 0.0, 200.0, 20.0]}
        r = rendered_rect(d)
        assert r[2] == pytest.approx(290.0)
        assert r[3] == pytest.approx(20.0)

    def test_comment_fontsize_scales(self):
        d = {"maxclass": "comment", "text": "hello world label",
             "patching_rect": [0.0, 0.0, 400.0, 20.0], "fontsize": 24.0}
        r = rendered_rect(d)
        assert r[2] == pytest.approx(17 * 5.6 * 2 + 10)
        assert r[3] == pytest.approx(6 + 28)

    def test_comment_with_fill_keeps_stored_rect(self):
        d = {"maxclass": "comment", "text": "hi",
             "patching_rect": [0.0, 0.0, 120.0, 24.0],
             "bgcolor": [0.2, 0.2, 0.2, 1.0]}
        assert rendered_rect(d) == [0.0, 0.0, 120.0, 24.0]

    def test_comment_bubble_keeps_stored_rect(self):
        d = {"maxclass": "comment", "text": "hi", "bubble": 1,
             "patching_rect": [0.0, 0.0, 120.0, 24.0]}
        assert rendered_rect(d) == [0.0, 0.0, 120.0, 24.0]

    def test_other_maxclass_copies_stored_rect(self):
        rect = [5.0, 6.0, 70.0, 22.0]
        d = {"maxclass": "newobj", "text": "metro 100", "patching_rect": rect}
        r = rendered_rect(d)
        assert r == rect and r is not rect

    def test_box_object_same_as_dict(self):
        p = Patcher()
        m = p.add_message("set foo bar baz qux", x=30.0, y=30.0)
        c = p.add_comment("hello world label", x=10.0, y=20.0)
        assert rendered_rect(m)[2] == 19 * 8 + 25
        assert rendered_rect(c)[2] == pytest.approx(105.2)

    def test_box_extra_attrs_fill(self):
        p = Patcher()
        h = p.add_section_header("SYNTH", 0.0, 0.0)
        r = rendered_rect(h)
        # a filled comment covers at least its stored rect
        assert r[:2] == h.patching_rect[:2]
        assert r[2] >= h.patching_rect[2] and r[3] >= h.patching_rect[3]
        assert r[2] > 5 * 5.6 * 16 / 12 + 10

    def test_invalid_rects_give_none(self):
        for rect in (None, [], [1, 2, 3], ["a", "b", "c", "d"],
                     [True, 0, 10, 10], "1 2 3 4", 7):
            assert rendered_rect({"maxclass": "newobj", "patching_rect": rect}) is None

    def test_junk_text_and_fontsize(self):
        for text in (None, 5, {"a": 1}, ["x"]):
            for fs in (True, 0, -3, "12", None):
                for mc in ("message", "comment", "newobj"):
                    d = {"maxclass": mc, "text": text, "fontsize": fs,
                         "patching_rect": [0, 0, 40, 22]}
                    r = rendered_rect(d)
                    assert isinstance(r, list) and len(r) == 4

    def test_does_not_mutate(self):
        d = {"maxclass": "message", "text": "set foo bar baz qux",
             "patching_rect": [30.0, 30.0, 149.0, 22.0]}
        before = copy.deepcopy(d)
        rendered_rect(d)
        assert d == before
        p = Patcher()
        m = p.add_message("set foo bar baz qux", x=30.0, y=30.0)
        stored = list(m.patching_rect)
        rendered_rect(m)
        assert m.patching_rect == stored


class TestIsMaxSaved:

    def test_generator_version_is_not_max_saved(self):
        assert is_max_saved(Patcher().props) is False
        assert is_max_saved({"appversion": {"major": 9, "minor": 0, "revision": 0}}) is False

    def test_max_versions(self):
        assert is_max_saved({"appversion": {"major": 9, "minor": 1, "revision": 5}}) is True
        assert is_max_saved({"appversion": {"major": 9, "minor": 2, "revision": 0}}) is True

    def test_missing_or_junk(self):
        assert is_max_saved({}) is False
        assert is_max_saved({"appversion": "9.1.5"}) is False
        assert is_max_saved(None) is False


# ---------------------------------------------------------------------------
# F5: add_box measures existing boxes by their rendered rect
# ---------------------------------------------------------------------------

class TestF5AddBoxRenderedOverlap:

    def test_toggle_inside_rendered_message_is_nudged(self):
        p = Patcher()
        m = p.add_message("set foo bar baz qux", x=30.0, y=30.0)
        stored_right = m.patching_rect[0] + m.patching_rect[2]
        rendered_right = rendered_rect(m)[0] + rendered_rect(m)[2]
        assert stored_right < 195.0 < rendered_right
        t = p.add_box("toggle", x=195.0, y=30.0)
        assert not _intersect(t.patching_rect, rendered_rect(m))
        assert t.patching_rect[1] > m.patching_rect[1]


# ---------------------------------------------------------------------------
# F5: the overlap critic reads rendered rects and exempts deliberate overlays
# ---------------------------------------------------------------------------

def _two_messages():
    return [
        {"id": "obj-1", "maxclass": "message", "text": "set foo bar baz qux",
         "patching_rect": [30.0, 30.0, 149.0, 22.0], "numinlets": 2, "numoutlets": 1},
        {"id": "obj-2", "maxclass": "message", "text": "bang",
         "patching_rect": [189.0, 30.0, 40.0, 22.0], "numinlets": 2, "numoutlets": 1},
    ]


class TestF5OverlapCritic:

    def test_rendered_width_collision_warns_once(self):
        res = _overlaps(review_layout(_make_patch(_two_messages())))
        assert len(res) == 1
        assert "obj-1" in res[0].finding and "obj-2" in res[0].finding

    def test_max_saved_patch_keeps_stored_message_width(self):
        patch = _make_patch(_two_messages(),
                            appversion={"major": 9, "minor": 1, "revision": 5})
        assert _overlaps(review_layout(patch)) == []

    def test_overlay_readout_is_not_an_overlap(self):
        p = Patcher()
        dial = p.add_box("dial", x=30.0, y=30.0)
        p.add_overlay_readout(dial)
        assert _overlaps(review_layout(p.to_dict())) == []

    def test_editable_overlap_still_warns(self):
        boxes = [
            {"id": "obj-1", "maxclass": "dial", "patching_rect": [30, 30, 40, 40]},
            {"id": "obj-2", "maxclass": "flonum", "patching_rect": [30, 30, 40, 40]},
        ]
        assert len(_overlaps(review_layout(_make_patch(boxes)))) == 1

    def test_comment_and_panel_still_excluded(self):
        boxes = [
            {"id": "obj-1", "maxclass": "comment", "text": "x" * 80,
             "patching_rect": [30, 30, 50, 20]},
            {"id": "obj-2", "maxclass": "newobj", "text": "metro 5",
             "patching_rect": [60, 30, 60, 22]},
        ]
        assert _overlaps(review_layout(_make_patch(boxes))) == []


class TestF5Robustness:

    _JUNK = [
        {"id": "a", "maxclass": "message", "text": None, "patching_rect": None},
        {"id": "b", "maxclass": "message", "text": 5, "patching_rect": [0, 0]},
        {"id": "c", "maxclass": "comment", "text": {"x": 1},
         "patching_rect": ["a", "b", "c", "d"], "fontsize": True},
        {"id": "d", "maxclass": "message", "text": ["x"],
         "patching_rect": [0, 0, 30, 22], "fontsize": 0},
        {"id": "e", "maxclass": "comment", "text": "hi",
         "patching_rect": [0, 0, 0, 0], "fontsize": "big"},
        {"id": "f", "maxclass": "flonum", "patching_rect": [0, 0, 30, 22],
         "ignoreclick": 1},
    ]

    def test_review_layout_never_raises_on_junk(self):
        review_layout(_make_patch(copy.deepcopy(self._JUNK)))

    def test_review_layout_is_pure(self):
        patch = _make_patch(copy.deepcopy(self._JUNK) + _two_messages(),
                            appversion={"major": 9, "minor": 0, "revision": 0})
        before = copy.deepcopy(patch)
        review_layout(patch)
        assert patch == before
