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


# ---------------------------------------------------------------------------
# Task 2 helpers
# ---------------------------------------------------------------------------

from src.maxpat import layout as _layout  # noqa: E402
from src.maxpat.defaults import LayoutOptions  # noqa: E402

H_GUTTER = LayoutOptions().h_gutter


def apply_layout(patcher, *args, **kwargs):
    return _layout.apply_layout(patcher, *args, **kwargs)


def _content_rects(p):
    return [(b, rendered_rect(b)) for b in p.boxes
            if b.maxclass not in ("comment", "panel")]


def _assert_no_intersections(p):
    rects = _content_rects(p)
    for i in range(len(rects)):
        for j in range(i + 1, len(rects)):
            a, ra = rects[i]
            b, rb = rects[j]
            assert not _intersect(ra, rb), (
                f"{a.text or a.maxclass} {ra} intersects {b.text or b.maxclass} {rb}")


# ---------------------------------------------------------------------------
# F1: no status-role overlay
# ---------------------------------------------------------------------------

class TestF1NoStatusOverlay:

    def test_role_map_status_has_no_companion(self):
        assert _layout._ROLE_COMPANION_MAP["status"] == {"companion": None, "placement": None}
        assert len(_layout._ROLE_COMPANION_MAP) == 6

    def test_dspstate_flonum_not_stacked(self):
        p = Patcher()
        src = p.add_box("dspstate~")
        num = p.add_box("flonum")
        p.add_connection(src, 1, num, 0)
        apply_layout(p)
        assert not _intersect(src.patching_rect, num.patching_rect)
        assert "ignoreclick" not in num.extra_attrs
        assert num.patching_rect[1] > src.patching_rect[1]


# ---------------------------------------------------------------------------
# F2: controls feeding one object sit in a band above it
# ---------------------------------------------------------------------------

def _pack_with_controls(p, x=0.0):
    pack = p.add_box("pack", ["0.", "0.", "0."], x=x)
    a = p.add_box("flonum", x=x)
    b = p.add_box("flonum", x=x)
    d = p.add_box("dial", x=x)
    # cords created out of inlet order
    p.add_connection(d, 0, pack, 2)
    p.add_connection(b, 0, pack, 1)
    p.add_connection(a, 0, pack, 0)
    return pack, [a, b, d]


class TestF2ControlBand:

    def test_three_controls_in_one_band_above_pack(self):
        p = Patcher()
        pack, controls = _pack_with_controls(p)
        out = p.add_box("print")
        p.add_connection(pack, 0, out, 0)
        apply_layout(p)
        top = pack.patching_rect[1]
        for c in controls:
            assert c.patching_rect[1] + c.patching_rect[3] <= top + 1e-9
        for i in range(3):
            for j in range(i + 1, 3):
                ci, cj = controls[i].patching_rect, controls[j].patching_rect
                assert ci[1] < cj[1] + cj[3] and cj[1] < ci[1] + ci[3]
        for prev, cur in zip(controls, controls[1:]):
            prev_right = rendered_rect(prev)[0] + rendered_rect(prev)[2]
            assert cur.patching_rect[0] >= prev_right + H_GUTTER - 1e-9
        _assert_no_intersections(p)

    def test_two_packs_in_one_row_do_not_collide(self):
        p = Patcher()
        pack1, _ = _pack_with_controls(p)
        pack2, _ = _pack_with_controls(p)
        out = p.add_box("print")
        p.add_connection(pack1, 0, out, 0)
        p.add_connection(pack2, 0, out, 0)
        apply_layout(p)
        assert pack1.patching_rect[1] == pack2.patching_rect[1]
        _assert_no_intersections(p)

    def test_dial_scale_mul_does_not_land_on_cycle(self):
        p = Patcher()
        dial = p.add_box("dial")
        sc = p.add_box("scale", ["0", "127", "0.", "1."])
        osc = p.add_box("cycle~", ["440"])
        mul = p.add_box("*~")
        dac = p.add_box("dac~")
        p.add_connection(dial, 0, sc, 0)
        p.add_connection(sc, 0, mul, 1)
        p.add_connection(osc, 0, mul, 0)
        p.add_connection(mul, 0, dac, 0)
        apply_layout(p)
        _assert_no_intersections(p)

    def test_control_feeding_control_stays_in_rows(self):
        p = Patcher()
        dial = p.add_box("dial")
        num = p.add_box("flonum")
        out = p.add_box("print")
        p.add_connection(dial, 0, num, 0)
        p.add_connection(num, 0, out, 0)
        apply_layout(p)
        assert dial.patching_rect[1] < num.patching_rect[1] < out.patching_rect[1]
        _assert_no_intersections(p)


# ---------------------------------------------------------------------------
# F4: embedded bpatcher faces are never re-laid out
# ---------------------------------------------------------------------------

class TestF4BpatcherFace:

    def test_bpatcher_inner_rects_unchanged(self):
        p = Patcher()
        bp, inner = p.add_bpatcher(embedded=True, width=120.0, height=80.0)
        dial = inner.add_box("dial", x=10.0, y=10.0)
        lbl = inner.add_comment("freq", x=55.0, y=20.0)
        dial.presentation = True
        dial.presentation_rect = [10.0, 10.0, 40.0, 40.0]
        before = [list(dial.patching_rect), list(lbl.patching_rect)]
        src = p.add_box("loadbang")
        p.add_connection(src, 0, bp, 0)
        apply_layout(p)
        assert [dial.patching_rect, lbl.patching_rect] == before
        assert dial.presentation_rect == [10.0, 10.0, 40.0, 40.0]

    def test_subpatcher_still_laid_out(self):
        p = Patcher()
        sp, inner = p.add_subpatcher("work", inlets=0, outlets=0)
        a = inner.add_box("loadbang", x=300.0, y=300.0)
        b = inner.add_box("print", x=300.0, y=200.0)
        inner.add_connection(a, 0, b, 0)
        apply_layout(p)
        assert a.patching_rect[1] < b.patching_rect[1]
        assert a.patching_rect[:2] != [300.0, 300.0]


# ---------------------------------------------------------------------------
# F5: refusal guard
# ---------------------------------------------------------------------------

def _saved_patch(version):
    p = Patcher()
    a = p.add_box("loadbang", x=400.0, y=400.0)
    b = p.add_box("print", x=100.0, y=100.0)
    p.add_box("metro", ["100"], x=700.0, y=10.0)
    p.add_connection(a, 0, b, 0)
    d = p.to_dict()
    d["patcher"]["appversion"] = dict(d["patcher"]["appversion"], **version)
    return Patcher.from_dict(d)


class TestF5Guard:

    def test_max_saved_patch_refused_unchanged(self):
        p = _saved_patch({"major": 9, "minor": 1, "revision": 5})
        before = [list(b.patching_rect) for b in p.boxes]
        with pytest.raises(_layout.LayoutRefusedError) as exc:
            apply_layout(p)
        assert "saved by MAX 9.1.5" in str(exc.value)
        assert "force=True" in str(exc.value)
        assert isinstance(exc.value, ValueError)
        assert [list(b.patching_rect) for b in p.boxes] == before

    def test_force_lays_out(self):
        p = _saved_patch({"major": 9, "minor": 1, "revision": 5})
        before = [list(b.patching_rect) for b in p.boxes]
        apply_layout(p, force=True)
        assert [list(b.patching_rect) for b in p.boxes] != before

    def test_generator_version_lays_out(self):
        p = _saved_patch({})
        apply_layout(p)

    def test_box_limit(self):
        p = Patcher()
        for _ in range(121):
            p.add_box("print", skip_overlap_check=True)
        with pytest.raises(_layout.LayoutRefusedError, match=r"121 boxes \(limit 120\)"):
            apply_layout(p)
        p.boxes.pop()
        apply_layout(p)

    def test_inner_patcher_checked_too(self):
        p = Patcher()
        sp, inner = p.add_subpatcher("big", inlets=0, outlets=0)
        for _ in range(121):
            inner.add_box("print", skip_overlap_check=True)
        with pytest.raises(_layout.LayoutRefusedError):
            apply_layout(p)
        apply_layout(p, force=True)


# ---------------------------------------------------------------------------
# F5: ~1600 px width cap
# ---------------------------------------------------------------------------

CAP_RIGHT = 30.0 + 1600.0


def _right(b):
    r = rendered_rect(b)
    return r[0] + r[2]


class TestF5WidthCap:

    def test_twenty_chains_wrap_into_bands(self):
        p = Patcher()
        pairs = []
        for _ in range(20):
            m = p.add_box("metro", ["100"])
            o = p.add_box("print")
            p.add_connection(m, 0, o, 0)
            pairs.append((m, o))
        apply_layout(p)
        assert max(_right(b) for b in p.boxes) <= CAP_RIGHT
        first_bottom = max(b.patching_rect[1] + b.patching_rect[3] for b in pairs[0])
        assert any(m.patching_rect[1] > first_bottom for m, _ in pairs)
        _assert_no_intersections(p)

    def test_thirty_sources_one_sink_wraps(self):
        p = Patcher()
        out = p.add_box("print")
        srcs = []
        for _ in range(30):
            s = p.add_box("loadbang")
            p.add_connection(s, 0, out, 0)
            srcs.append(s)
        apply_layout(p)
        assert max(_right(b) for b in p.boxes) <= CAP_RIGHT
        assert all(out.patching_rect[1] > s.patching_rect[1] + s.patching_rect[3]
                   for s in srcs)
        _assert_no_intersections(p)

    @pytest.mark.parametrize("n", [15, 18])
    def test_disconnected_inside_cap(self, n):
        p = Patcher()
        out = p.add_box("print")
        for _ in range(n):
            p.add_connection(p.add_box("loadbang"), 0, out, 0)
        loose = [p.add_box("metro", ["100"]) for _ in range(5)]
        apply_layout(p)
        assert all(_right(b) <= CAP_RIGHT for b in loose)
        assert max(_right(b) for b in p.boxes) <= CAP_RIGHT
        _assert_no_intersections(p)

    def test_oversize_box_terminates_alone_past_cap(self):
        p = Patcher()
        src = p.add_box("loadbang")
        outs = [p.add_box("print") for _ in range(3)]
        outs[1].patching_rect[2] = 2000.0
        for o in outs:
            p.add_connection(src, 0, o, 0)
        apply_layout(p)
        past = [b for b in p.boxes if _right(b) > CAP_RIGHT]
        assert past == [outs[1]]
        _assert_no_intersections(p)


# ---------------------------------------------------------------------------
# F5: presentation auto-grid with a running x offset
# ---------------------------------------------------------------------------

class TestF5PresentationGrid:

    def test_mixed_widths_do_not_overlap(self):
        p = Patcher()
        boxes = [p.add_box("multislider"), p.add_box("toggle"), p.add_box("slider")]
        for b in boxes:
            b.presentation = True
        apply_layout(p)
        rects = [b.presentation_rect for b in boxes]
        for i in range(3):
            for j in range(i + 1, 3):
                assert not _intersect(rects[i], rects[j]), rects

    def test_uniform_widths_reproduce_old_grid(self):
        p = Patcher()
        toggles = [p.add_box("toggle") for _ in range(3)]
        for t in toggles:
            t.presentation = True
        apply_layout(p)
        assert [t.presentation_rect[:2] for t in toggles] == [
            [20.0, 20.0], [104.0, 20.0], [188.0, 20.0]]


# ---------------------------------------------------------------------------
# F7: add_overlay_readout presentation copy and empty comment text
# ---------------------------------------------------------------------------

def _serialized(p, box):
    for entry in p.to_dict()["patcher"]["boxes"]:
        if entry["box"]["id"] == box.id:
            return entry["box"]
    raise AssertionError(box.id)


class TestF7OverlayReadout:

    def test_comment_readout_text_empty(self):
        p = Patcher()
        dial = p.add_box("dial", x=30.0, y=30.0)
        r = p.add_overlay_readout(dial, type="comment")
        assert _serialized(p, r)["text"] == ""

    def test_presentation_copied_with_offsets(self):
        p = Patcher()
        dial = p.add_box("dial", x=30.0, y=30.0)
        p.add_to_presentation(dial, [100.0, 50.0, 40.0, 40.0])
        r = p.add_overlay_readout(dial, offset_x=5.0, offset_y=4.0)
        assert r.presentation is True
        assert r.presentation_rect == [105.0, 54.0, 40.0, 40.0]

    def test_not_in_presentation_when_target_is_not(self):
        p = Patcher()
        dial = p.add_box("dial", x=30.0, y=30.0)
        r = p.add_overlay_readout(dial)
        assert r.presentation is False
        assert r.presentation_rect is None


class TestF5AddBoxNewBoxRenderedDims:

    def test_new_message_measured_by_rendered_width(self):
        p = Patcher()
        t = p.add_box("toggle", x=105.0, y=30.0, skip_overlap_check=True)
        m = p.add_box("message", x=30.0, y=30.0)
        assert not _intersect(rendered_rect(m), t.patching_rect)


# ---------------------------------------------------------------------------
# F3: contrast after layout; panels, headers and labels move with their boxes
# ---------------------------------------------------------------------------

def _evidence_patch():
    from src.maxpat.aesthetics import auto_size_panel

    p = Patcher()
    osc = p.add_box("cycle~", ["440"], x=60.0, y=60.0)
    mul = p.add_box("*~", ["0.5"], x=60.0, y=120.0)
    dac = p.add_box("ezdac~", x=60.0, y=180.0)
    p.add_connection(osc, 0, mul, 0)
    p.add_connection(mul, 0, dac, 0)
    x, y, w, h = auto_size_panel([osc, mul, dac], padding=18)
    panel = p.add_panel(x, y, w + 80, h, gradient=False)
    panel.extra_attrs["bgcolor"] = [0.94, 0.94, 0.94, 1.0]
    gain = p.add_comment(
        "gain", x=mul.patching_rect[0] + mul.patching_rect[2] + 8, y=120.0)
    met = p.add_box("metro", ["100"], x=400.0, y=60.0)
    out = p.add_box("print", x=400.0, y=120.0)
    p.add_connection(met, 0, out, 0)
    tick = p.add_comment(
        "tick", x=out.patching_rect[0] + out.patching_rect[2] + 8, y=120.0)
    header = p.add_section_header("SYNTH", x, y - 30)
    return p, dict(osc=osc, mul=mul, dac=dac, panel=panel, gain=gain,
                   met=met, out=out, tick=tick, header=header)


def _contains(outer, inner):
    return (outer[0] <= inner[0] and outer[1] <= inner[1]
            and inner[0] + inner[2] <= outer[0] + outer[2]
            and inner[1] + inner[3] <= outer[1] + outer[3])


class TestF3DecorationsAndContrastOrder:

    def test_evidence_patch(self):
        from src.maxpat.hooks import finalize_patch

        p, b = _evidence_patch()
        header_off = (b["header"].patching_rect[0] - b["osc"].patching_rect[0],
                      b["header"].patching_rect[1] - b["osc"].patching_rect[1])
        assert header_off == (-18.0, -48.0)
        finalize_patch(p, is_new=True)

        panel = b["panel"].patching_rect
        for key in ("osc", "mul", "dac"):
            assert _contains(panel, rendered_rect(b[key])), key
        assert _contains(panel, rendered_rect(b["gain"]))
        for key in ("met", "out"):
            assert not _intersect(panel, rendered_rect(b[key])), key

        for label, anchor in (("gain", "mul"), ("tick", "out")):
            lr, ar = b[label].patching_rect, b[anchor].patching_rect
            assert lr[0] - ar[0] == pytest.approx(ar[2] + 8, abs=0.01)
            assert lr[1] - ar[1] == pytest.approx(0.0, abs=0.01)
        hr, orr = b["header"].patching_rect, b["osc"].patching_rect
        assert (hr[0] - orr[0], hr[1] - orr[1]) == pytest.approx((-18.0, -48.0))

        for box in p.boxes:
            assert box.patching_rect[0] >= 0 and box.patching_rect[1] >= 0

        findings = [r.finding for r in review_layout(p.to_dict())]
        assert not [f for f in findings if "Low contrast text" in f], findings
        assert not [f for f in findings if "Out-of-bounds placement" in f], findings

    def test_contrast_runs_after_layout_once(self, monkeypatch):
        import src.maxpat.aesthetics as aesthetics
        import src.maxpat.layout as layout_mod
        from src.maxpat.hooks import finalize_patch

        calls = []
        real_layout = layout_mod.apply_layout
        real_contrast = aesthetics.ensure_text_contrast

        def rec_layout(patcher, *a, **k):
            calls.append("layout")
            return real_layout(patcher, *a, **k)

        def rec_contrast(patcher, *a, **k):
            calls.append("contrast")
            return real_contrast(patcher, *a, **k)

        monkeypatch.setattr(layout_mod, "apply_layout", rec_layout)
        monkeypatch.setattr(aesthetics, "ensure_text_contrast", rec_contrast)
        p, _ = _evidence_patch()
        finalize_patch(p, is_new=True)
        assert calls == ["layout", "contrast"]

    def test_apply_auto_styling_contrast_flag(self):
        from src.maxpat.aesthetics import apply_auto_styling

        p = Patcher()
        c = p.add_comment("hello", 30.0, 30.0)
        apply_auto_styling(p, contrast=False)
        assert "textcolor" not in c.extra_attrs
        apply_auto_styling(p)
        assert "textcolor" in c.extra_attrs

    def test_row_reserves_label_width(self):
        p = Patcher()
        osc = p.add_box("cycle~", ["440"], x=60.0, y=60.0)
        a = p.add_box("*~", ["0.5"], x=60.0, y=120.0)
        b2 = p.add_box("*~", ["0.3"], x=240.0, y=120.0)
        p.add_connection(osc, 0, a, 0)
        p.add_connection(osc, 0, b2, 0)
        lbl = p.add_comment("amp", x=a.patching_rect[0] + a.patching_rect[2] + 8, y=120.0)
        apply_layout(p)
        lr = rendered_rect(lbl)
        anchor, other = (a, b2) if a.patching_rect[0] < b2.patching_rect[0] else (b2, a)
        assert lbl.patching_rect[0] == pytest.approx(
            a.patching_rect[0] + a.patching_rect[2] + 8)
        if anchor is a:
            assert other.patching_rect[0] >= lr[0] + lr[2] + H_GUTTER - 1e-9
        assert not _intersect(lr, other.patching_rect)

    def test_panel_anchored_note_keeps_offset(self):
        p = Patcher()
        src = p.add_box("loadbang", x=60.0, y=60.0)
        dst = p.add_box("print", x=60.0, y=120.0)
        p.add_connection(src, 0, dst, 0)
        panel = p.add_panel(40.0, 40.0, 400.0, 220.0, gradient=False)
        note = p.add_comment("note", x=300.0, y=220.0)
        far = p.add_comment("far away", x=900.0, y=900.0)
        off = (note.patching_rect[0] - panel.patching_rect[0],
               note.patching_rect[1] - panel.patching_rect[1])
        apply_layout(p)
        assert (note.patching_rect[0] - panel.patching_rect[0],
                note.patching_rect[1] - panel.patching_rect[1]) == pytest.approx(off)
        assert far.patching_rect[:2] != [900.0, 900.0]
        assert far.patching_rect[0] >= panel.patching_rect[0] + panel.patching_rect[2]

    def test_panel_is_not_a_routing_obstacle(self):
        from src.maxpat.layout import _generate_midpoints

        def build(with_panel):
            p = Patcher()
            a = p.add_box("loadbang", x=30, y=30, skip_overlap_check=True)
            b = p.add_box("print", x=30, y=200, skip_overlap_check=True)
            p.add_box("metro", ["100"], x=20, y=110, skip_overlap_check=True)
            p.add_connection(a, 0, b, 0)
            if with_panel:
                p.add_panel(0, 0, 400, 300, gradient=False)
            _generate_midpoints(p)
            return p.lines[0].midpoints

        plain = build(False)
        assert plain
        assert build(True) == plain

    def test_finalize_refuses_max_saved_unless_forced(self):
        from src.maxpat.hooks import finalize_patch

        p = _saved_patch({"major": 9, "minor": 1, "revision": 5})
        with pytest.raises(_layout.LayoutRefusedError):
            finalize_patch(p, is_new=True)
        p = _saved_patch({"major": 9, "minor": 1, "revision": 5})
        finalize_patch(p, is_new=True, force_layout=True)


# ---------------------------------------------------------------------------
# F6: list-wrapped fill dicts
# ---------------------------------------------------------------------------

_DARK_WRAPPED = [{"type": "color", "color": [0.13, 0.13, 0.13, 1.0]}]
_LIGHT_WRAPPED = [{"type": "color", "color": [0.94, 0.94, 0.94, 1.0]}]


class TestF6ListWrappedFill:

    def test_unwraps_bgcolor(self):
        from src.maxpat.aesthetics import resolve_fill_color

        assert resolve_fill_color({"bgcolor": _DARK_WRAPPED}) == [0.13, 0.13, 0.13, 1.0]

    def test_unwraps_bgfillcolor_color1(self):
        from src.maxpat.aesthetics import resolve_fill_color

        attrs = {"bgfillcolor": [{"type": "gradient", "color1": [0.5, 0.5, 0.5, 1.0],
                                  "color": [0.1, 0.1, 0.1, 1.0]}]}
        assert resolve_fill_color(attrs) == [0.5, 0.5, 0.5, 1.0]

    def test_no_color_gives_none(self):
        from src.maxpat.aesthetics import resolve_fill_color

        assert resolve_fill_color({"bgcolor": [{"type": "color"}]}) is None
        assert resolve_fill_color({"bgcolor": ["a", "b", "c"]}) is None

    def test_contrast_ratio_does_not_raise(self):
        from src.maxpat.aesthetics import contrast_ratio, resolve_panel_background

        bg = resolve_panel_background({"bgcolor": _DARK_WRAPPED}).color
        assert contrast_ratio([1.0, 1.0, 1.0, 1.0], bg) > 4.5

    def _panel_patch(self):
        return _make_patch([
            {"id": "obj-1", "maxclass": "comment", "text": "hello",
             "textcolor": [0.8, 0.8, 0.8, 1.0], "patching_rect": [20, 20, 100, 20]},
            {"id": "obj-2", "maxclass": "panel", "background": 1,
             "bgcolor": copy.deepcopy(_LIGHT_WRAPPED),
             "patching_rect": [0, 0, 300, 200]},
        ])

    def test_light_wrapped_panel_low_contrast_warning(self):
        res = [r for r in review_layout(self._panel_patch())
               if r.finding.startswith("Low contrast text") and r.severity == "warning"]
        assert len(res) == 1

    def test_generic_editor_shape_never_raises(self):
        from src.maxpat.aesthetics import ensure_text_contrast

        patch = self._panel_patch()
        patch["patcher"]["boxes"][1]["box"].pop("background")
        review_layout(copy.deepcopy(patch))
        ensure_text_contrast(Patcher.from_dict(copy.deepcopy(patch)))

    def test_junk_never_raises(self):
        from src.maxpat.aesthetics import resolve_fill_color, resolve_panel_background

        for v in (None, "red", 5, [], [[]], [[{}]], [None], [{}], [{"color": "x"}],
                  {"color1": None}, ["a"], [[1, 2, 3]], ({"color": [1, 1, 1]},)):
            for key in ("bgfillcolor", "grad1", "bgcolor"):
                resolve_fill_color({key: v})
                resolve_panel_background({key: v})
