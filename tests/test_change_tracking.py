"""Q28 regression tests: edit fidelity for loaded patches.

Findings (``.planning/reviews/2026-10-11-repo-review.md``):

- B5: edits to loaded boxes (extra_attrs, fontname/fontsize) and cords
  (order, hidden, midpoints, color, extra_attrs) never reached disk.
- B6: ``Patcher.from_dict`` shared nested objects with the caller's dict, so
  edits wrote through to it.
- S4: the change-tracking semantics (load snapshot + diff at serialize) and
  the retired manual ``_raw`` copies.
- B7: adding or removing an inlet/outlet box inside a subpatcher resyncs
  the parent box's ports and renumbers parent cords like MAX (x-rank);
  parent cords on a removed port are returned in parent_orphaned.

Committed patches are only read (``json.load`` / ``read_patch``), never
written. The tracer save goes to ``tmp_path`` with GIT_DIR / GIT_WORK_TREE
unset.
"""

from __future__ import annotations

import copy
import json
import pathlib

import pytest

from src.maxpat.patcher import Patcher, Patchline
from src.maxpat import aesthetics
from src.maxpat.aesthetics import set_object_bgcolor
from src.maxpat.defaults import AESTHETIC_PALETTE

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
BASSOON = PROJECT_ROOT / "patches" / "bassoon-model" / "generated" / "bassoon-model.maxpat"
COLORED_LINES = PROJECT_ROOT / "tests" / "fixtures" / "colored_patchlines.maxpat"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_json(path: pathlib.Path) -> dict:
    with open(path, "r") as f:
        return json.load(f)


def _load_bassoon() -> tuple[Patcher, dict]:
    """Fresh in-memory load of the committed bassoon patch (read only)."""
    data = _load_json(BASSOON)
    return Patcher.from_dict(data), data


def _out_boxes(out: dict, prefix: str = "") -> dict[str, dict]:
    """Map every box in a to_dict() result by id path.

    Top-level boxes are keyed by id ("obj-10"); nested boxes by the parent
    path ("obj-85/obj-1").
    """
    result: dict[str, dict] = {}
    patcher = out.get("patcher", out)
    for entry in patcher.get("boxes", []):
        bd = entry["box"]
        key = f"{prefix}{bd['id']}"
        result[key] = bd
        if isinstance(bd.get("patcher"), dict):
            result.update(_out_boxes(bd["patcher"], prefix=f"{key}/"))
    return result


def _box(p: Patcher, box_id: str):
    for b in p.boxes:
        if b.id == box_id:
            return b
    raise KeyError(box_id)


def _line(p: Patcher, src: str, src_out: int, dst: str, dst_in: int) -> Patchline:
    for pl in p.lines:
        if (pl.source_id, pl.source_outlet, pl.dest_id, pl.dest_inlet) == (
            src, src_out, dst, dst_in
        ):
            return pl
    raise KeyError((src, src_out, dst, dst_in))


def _out_line(out: dict, src: str, src_out: int, dst: str, dst_in: int) -> dict:
    for entry in out["patcher"]["lines"]:
        d = entry["patchline"]
        if d["source"] == [src, src_out] and d["destination"] == [dst, dst_in]:
            return d
    raise KeyError((src, src_out, dst, dst_in))


def _first_newobj_without_bgcolor(p: Patcher):
    for b in p.boxes:
        if b.maxclass == "newobj" and "bgcolor" not in b._raw:
            return b
    raise AssertionError("no newobj box without bgcolor in bassoon")


# ---------------------------------------------------------------------------
# Tracer: load -> edit -> save -> disk
# ---------------------------------------------------------------------------


class TestTracerLoadEditSaveDisk:
    """A loaded box's bgcolor edit lands in the file save_patch_roundtrip writes."""

    def test_bgcolor_reaches_saved_file(self, tmp_path, monkeypatch):
        from src.maxpat.hooks import read_patch, save_patch_roundtrip

        monkeypatch.delenv("GIT_DIR", raising=False)
        monkeypatch.delenv("GIT_WORK_TREE", raising=False)

        p, text = read_patch(BASSOON)
        box = _first_newobj_without_bgcolor(p)
        color = [0.2, 0.3, 0.4, 1.0]
        set_object_bgcolor(box, color=color)

        target = tmp_path / "bassoon-model.maxpat"
        save_patch_roundtrip(p.to_dict(), target, original_text=text)

        written = _load_json(target)
        assert _out_boxes(written)[box.id].get("bgcolor") == color


# ---------------------------------------------------------------------------
# B5: box fields
# ---------------------------------------------------------------------------


class TestB5BoxFields:
    """Box extra_attrs and font edits on loaded boxes reach to_dict()."""

    def test_set_object_bgcolor_palette_key(self):
        p, _ = _load_bassoon()
        box = _first_newobj_without_bgcolor(p)
        set_object_bgcolor(box, palette_key="emphasis_processor")
        out = _out_boxes(p.to_dict())
        assert out[box.id]["bgcolor"] == list(AESTHETIC_PALETTE["emphasis_processor"])

    def test_set_object_bgcolor_color(self):
        p, _ = _load_bassoon()
        box = _box(p, "obj-10")  # has a bgcolor in the file
        set_object_bgcolor(box, color=[0.5, 0.25, 0.125, 1.0])
        out = _out_boxes(p.to_dict())
        assert out["obj-10"]["bgcolor"] == [0.5, 0.25, 0.125, 1.0]

    def test_modify_box_color(self):
        p, _ = _load_bassoon()
        box = _first_newobj_without_bgcolor(p)
        p.modify_box(box, color=[0.1, 0.2, 0.3, 1.0])
        out = _out_boxes(p.to_dict())
        assert out[box.id]["bgcolor"] == [0.1, 0.2, 0.3, 1.0]

    def test_fontsize_assignment(self):
        p, _ = _load_bassoon()
        box = _box(p, "obj-4")
        box.fontsize = 20
        out = _out_boxes(p.to_dict())
        assert out["obj-4"]["fontsize"] == 20

    def test_fontname_assignment(self):
        p, _ = _load_bassoon()
        box = _box(p, "obj-4")
        box.fontname = "Arial Bold"
        out = _out_boxes(p.to_dict())
        assert out["obj-4"]["fontname"] == "Arial Bold"

    def test_modify_box_extra_attrs_fontsize_on_disk(self):
        p, _ = _load_bassoon()
        box = _box(p, "obj-4")
        p.modify_box(box, extra_attrs={"fontsize": 20, "hint": "x"})
        out = _out_boxes(p.to_dict())
        assert out["obj-4"]["fontsize"] == 20
        assert out["obj-4"]["hint"] == "x"

    def test_modify_box_extra_attrs_fontsize_in_memory(self):
        p, _ = _load_bassoon()
        box = _box(p, "obj-4")
        p.modify_box(box, extra_attrs={"fontsize": 20})
        assert box.fontsize == 20

    def test_inner_inlet_comment(self):
        p, _ = _load_bassoon()
        inner = _box(p, "obj-85")._inner_patcher
        inlet = _box(inner, "obj-1")
        inlet.extra_attrs["comment"] = "Tongue trigger (edited)"
        out = _out_boxes(p.to_dict())
        assert out["obj-85/obj-1"]["comment"] == "Tongue trigger (edited)"


# ---------------------------------------------------------------------------
# B5: cord fields
# ---------------------------------------------------------------------------


class TestB5LineFields:
    """Patchline order/hidden/midpoints/color/extra_attrs edits reach to_dict()."""

    def test_order_written(self):
        p, _ = _load_bassoon()
        _line(p, "obj-86", 0, "obj-85", 0).order = 3
        assert _out_line(p.to_dict(), "obj-86", 0, "obj-85", 0)["order"] == 3

    def test_order_changed_to_zero_written(self):
        p, _ = _load_bassoon()
        _line(p, "obj-4", 0, "obj-11", 0).order = 0  # file has order 2
        assert _out_line(p.to_dict(), "obj-4", 0, "obj-11", 0)["order"] == 0

    def test_hidden_true_then_false(self):
        p, _ = _load_bassoon()
        pl = _line(p, "obj-86", 0, "obj-85", 0)
        pl.hidden = True
        assert _out_line(p.to_dict(), "obj-86", 0, "obj-85", 0)["hidden"] == 1
        pl.hidden = False
        assert "hidden" not in _out_line(p.to_dict(), "obj-86", 0, "obj-85", 0)

    def test_line_extra_attrs_added(self):
        p, _ = _load_bassoon()
        _line(p, "obj-86", 0, "obj-85", 0).extra_attrs["custom_line_attr"] = 7
        out = _out_line(p.to_dict(), "obj-86", 0, "obj-85", 0)
        assert out["custom_line_attr"] == 7

    def test_midpoints_rebound(self):
        p, _ = _load_bassoon()
        pl = _line(p, "obj-69", 0, "obj-85", 1)
        pl.midpoints = [1.0, 2.0, 3.0, 4.0]
        out = _out_line(p.to_dict(), "obj-69", 0, "obj-85", 1)
        assert out["midpoints"] == [1.0, 2.0, 3.0, 4.0]

    def test_midpoints_none_removes_key(self):
        p, _ = _load_bassoon()
        _line(p, "obj-69", 0, "obj-85", 1).midpoints = None
        assert "midpoints" not in _out_line(p.to_dict(), "obj-69", 0, "obj-85", 1)

    def test_color_none_removes_key(self):
        p = Patcher.from_dict(_load_json(COLORED_LINES))
        pl = p.lines[0]
        pl.color = None
        out = p.to_dict()["patcher"]["lines"][0]["patchline"]
        assert "color" not in out
        assert out["custom_line_attr"] == 42


# ---------------------------------------------------------------------------
# B6: input isolation
# ---------------------------------------------------------------------------


class TestB6InputIsolation:
    """from_dict never shares a nested object with the caller's dict."""

    def test_edits_do_not_write_through(self):
        data = _load_json(BASSOON)
        pristine = copy.deepcopy(data)
        p = Patcher.from_dict(data)

        p.modify_box(_box(p, "obj-4"), position=[999, 999])
        _box(p, "obj-10").extra_attrs["bgcolor"][3] = 0.5
        inner = _box(p, "obj-85")._inner_patcher
        _box(inner, "obj-5").patching_rect[0] = 777.0
        _line(p, "obj-69", 0, "obj-85", 1).midpoints[0] = 1.0

        assert data == pristine

    def test_no_shared_objects(self):
        data = _load_json(BASSOON)
        p = Patcher.from_dict(data)
        by_id = {e["box"]["id"]: e["box"] for e in data["patcher"]["boxes"]}
        for box in p.boxes:
            src = by_id[box.id]
            assert box.patching_rect is not src["patching_rect"]
            for k, v in box.extra_attrs.items():
                if isinstance(v, (list, dict)):
                    assert v is not src[k], f"{box.id}.{k} aliases the input"


# ---------------------------------------------------------------------------
# S4: tracking semantics
# ---------------------------------------------------------------------------


class TestS4TrackingSemantics:
    """Snapshot + diff semantics."""

    def test_in_place_nested_edit_reaches_disk(self):
        p, _ = _load_bassoon()
        _box(p, "obj-10").extra_attrs["bgcolor"][3] = 0.5
        assert _out_boxes(p.to_dict())["obj-10"]["bgcolor"][3] == 0.5

    def test_deleted_key_absent(self):
        p, _ = _load_bassoon()
        del _box(p, "obj-10").extra_attrs["bgcolor"]
        assert "bgcolor" not in _out_boxes(p.to_dict())["obj-10"]

    def test_added_key_appends_and_order_kept(self):
        p, data = _load_bassoon()
        original_keys = [
            k for e in data["patcher"]["boxes"] if e["box"]["id"] == "obj-10"
            for k in e["box"]
        ]
        _box(p, "obj-10").extra_attrs["hint"] = "added"
        keys = list(_out_boxes(p.to_dict())["obj-10"].keys())
        assert keys[-1] == "hint"
        assert keys[:-1] == original_keys

    def test_second_to_dict_sees_further_in_place_edit(self):
        p, _ = _load_bassoon()
        box = _box(p, "obj-10")
        box.extra_attrs["newlist"] = [1, 2]
        assert _out_boxes(p.to_dict())["obj-10"]["newlist"] == [1, 2]
        box.extra_attrs["newlist"].append(3)
        assert _out_boxes(p.to_dict())["obj-10"]["newlist"] == [1, 2, 3]

    def test_direct_raw_write_new_key(self):
        p, _ = _load_bassoon()
        _box(p, "obj-10")._raw["hint2"] = "raw"
        assert _out_boxes(p.to_dict())["obj-10"]["hint2"] == "raw"

    def test_direct_raw_write_unchanged_fontsize(self):
        p, _ = _load_bassoon()
        _box(p, "obj-4")._raw["fontsize"] = 18.0
        assert _out_boxes(p.to_dict())["obj-4"]["fontsize"] == 18.0

    def test_changed_extra_attr_beats_raw_write(self):
        p, _ = _load_bassoon()
        box = _box(p, "obj-10")
        box.extra_attrs["bgcolor"] = [0.1, 0.1, 0.1, 1.0]
        box._raw["bgcolor"] = [0.9, 0.9, 0.9, 1.0]
        assert _out_boxes(p.to_dict())["obj-10"]["bgcolor"] == [0.1, 0.1, 0.1, 1.0]

    def test_line_direct_raw_order_write(self):
        p, _ = _load_bassoon()
        pl = _line(p, "obj-86", 0, "obj-85", 0)
        pl._raw["order"] = 5
        assert _out_line(p.to_dict(), "obj-86", 0, "obj-85", 0)["order"] == 5


# ---------------------------------------------------------------------------
# S4: retired raw-dict copies
# ---------------------------------------------------------------------------


class TestRawCopiesRetired:
    """The manual _raw copies are gone; tracking carries the value to disk."""

    def test_modify_box_color(self):
        p, _ = _load_bassoon()
        box = _first_newobj_without_bgcolor(p)
        p.modify_box(box, color=[0.1, 0.2, 0.3, 1.0])
        assert "bgcolor" not in box._raw
        assert _out_boxes(p.to_dict())[box.id]["bgcolor"] == [0.1, 0.2, 0.3, 1.0]

    def test_modify_box_extra_attrs(self):
        p, _ = _load_bassoon()
        box = _box(p, "obj-4")
        p.modify_box(box, extra_attrs={"hint": 1})
        assert "hint" not in box._raw
        assert _out_boxes(p.to_dict())["obj-4"]["hint"] == 1

    def test_set_assistance_comment(self):
        p, _ = _load_bassoon()
        inlet = _box(_box(p, "obj-85")._inner_patcher, "obj-1")
        before = inlet._raw["comment"]
        Patcher._set_assistance_comment(inlet, "inferred comment")
        assert inlet._raw["comment"] == before
        assert _out_boxes(p.to_dict())["obj-85/obj-1"]["comment"] == "inferred comment"

    def test_set_textcolor(self):
        p, _ = _load_bassoon()
        comment = _box(p, "obj-23")
        before = copy.deepcopy(comment._raw["textcolor"])
        aesthetics._set_textcolor(comment, [0.25, 0.5, 0.75, 1.0])
        assert comment._raw["textcolor"] == before
        assert _out_boxes(p.to_dict())["obj-23"]["textcolor"] == [0.25, 0.5, 0.75, 1.0]

    def test_modify_box_structural_key_still_in_raw(self):
        p, _ = _load_bassoon()
        box = _box(p, "obj-4")
        p.modify_box(box, extra_attrs={"fontsize": 20})
        assert box._raw["fontsize"] == 20


# ---------------------------------------------------------------------------
# B7: parent port sync
# ---------------------------------------------------------------------------


def _orphan(src, src_out, dst, dst_in) -> dict:
    return {"source_id": src, "source_outlet": src_out,
            "dest_id": dst, "dest_inlet": dst_in}


def _cords(p: Patcher) -> list[tuple]:
    return [(pl.source_id, pl.source_outlet, pl.dest_id, pl.dest_inlet)
            for pl in p.lines]


class TestB7PortSync:
    """Port boxes added/removed inside a subpatcher resync the parent box."""

    def _articulation(self):
        p, data = _load_bassoon()
        art = _box(p, "obj-85")
        return p, data, art, art._inner_patcher

    def test_add_inlet_grows_parent_and_connects(self):
        p, _, art, inner = self._articulation()
        inner.add_box("inlet", x=600, y=20, skip_overlap_check=True)
        assert art.numinlets == 3
        btn = p.add_box("button")
        p.add_connection(btn, 0, art, 2)
        assert _out_boxes(p.to_dict())["obj-85"]["numinlets"] == 3

    def test_add_outlet_grows_parent(self):
        _, _, art, inner = self._articulation()
        inner.add_box("outlet", x=600, y=200, skip_overlap_check=True)
        assert art.numoutlets == 3
        assert art.outlettype == ["", "", ""]

    def test_remove_added_inlet_returns_parent_cord(self):
        p, _, art, inner = self._articulation()
        new_inlet = inner.add_box("inlet", x=600, y=20, skip_overlap_check=True)
        btn = p.add_box("button")
        p.add_connection(btn, 0, art, 2)
        result = inner.remove_box(new_inlet)
        # WR-01 (Q28 review): parent cords only in parent_orphaned; the new
        # inlet had no cords in its own patcher, so orphaned is empty.
        assert result.orphaned == []
        assert result.parent_orphaned == [_orphan(btn.id, 0, "obj-85", 2)]
        assert (btn.id, 0, "obj-85", 2) not in _cords(p)
        assert art.numinlets == 2

    def test_remove_added_outlet(self):
        _, _, art, inner = self._articulation()
        new_outlet = inner.add_box("outlet", x=600, y=200, skip_overlap_check=True)
        inner.remove_box(new_outlet)
        assert art.numoutlets == 2
        assert art.outlettype == ["", ""]

    def test_middle_removal_renumbers_like_max(self):
        """CR-02 (Q28 review): removing inlet rank 0 orphans the cord on port 0
        and shifts the cord on port 1 down to 0, as MAX renumbers on load.

        The save gate is unchanged: the surviving inlet's x-rank changed
        (1 -> 0), so the gate still reports a port change and refuses an
        unforced save. That is current gate behaviour, kept on purpose.
        """
        from src.maxpat import hooks

        p, data, art, inner = self._articulation()
        base = copy.deepcopy(data)
        result = inner.remove_box(_box(inner, "obj-1"))
        assert art.numinlets == 1
        assert result.parent_orphaned == [_orphan("obj-86", 0, "obj-85", 0)]
        to_art = [c for c in _cords(p) if c[2] == "obj-85"]
        assert to_art == [("obj-69", 0, "obj-85", 0)]
        report = hooks._gate_report(p.to_dict(), base, [base])
        assert report.port_changes

    def test_middle_outlet_removal_renumbers_cords_and_types(self):
        """CR-02: outlet removal keeps outlettype and cords aligned."""
        p, _, art, inner = self._articulation()
        art.outlettype = ["bang", "signal"]
        result = inner.remove_box(_box(inner, "obj-3"))
        assert art.numoutlets == 1
        assert art.outlettype == ["signal"]
        assert result.parent_orphaned == [_orphan("obj-85", 0, "obj-4", 0)]
        from_art = [c for c in _cords(p) if c[0] == "obj-85"]
        assert from_art == [("obj-85", 0, "obj-73", 1)]

    def test_middle_of_three_removal(self):
        """CR-02: ports below k keep their index, ports above k shift down."""
        p = Patcher()
        sub, inner = p.add_subpatcher("s", inlets=3, outlets=1)
        srcs = [p.add_box("button") for _ in range(3)]
        for i, b in enumerate(srcs):
            p.add_connection(b, 0, sub, i)
        mid = inner.get_inlets()[1]
        result = inner.remove_box(mid)
        assert sub.numinlets == 2
        assert result.parent_orphaned == [_orphan(srcs[1].id, 0, sub.id, 1)]
        assert [c for c in _cords(p) if c[2] == sub.id] == [
            (srcs[0].id, 0, sub.id, 0), (srcs[2].id, 0, sub.id, 1)]

    def test_replace_port_with_non_port_renumbers(self):
        """CR-02: replace_box's different-kind path uses the old port's rank."""
        p, _, art, inner = self._articulation()
        result = inner.replace_box(_box(inner, "obj-1"), "print")
        assert art.numinlets == 1
        assert result.parent_orphaned == [_orphan("obj-86", 0, "obj-85", 0)]
        assert [c for c in _cords(p) if c[2] == "obj-85"] == [
            ("obj-69", 0, "obj-85", 0)]

    def test_add_inlet_left_shifts_parent_cords_up(self):
        """WR-02 (Q28 review): a new inlet at rank 0 shifts cords on ports >= 0."""
        p, _, art, inner = self._articulation()
        inner.add_box("inlet", x=0, y=20, skip_overlap_check=True)
        assert art.numinlets == 3
        assert [c for c in _cords(p) if c[2] == "obj-85"] == [
            ("obj-86", 0, "obj-85", 1), ("obj-69", 0, "obj-85", 2)]

    def test_add_inlet_middle_shifts_only_ports_at_or_above_rank(self):
        """WR-02: a new inlet at rank 1 leaves port 0 and shifts port 1 up."""
        p, _, art, inner = self._articulation()
        inner.add_box("inlet", x=200, y=20, skip_overlap_check=True)
        assert [c for c in _cords(p) if c[2] == "obj-85"] == [
            ("obj-86", 0, "obj-85", 0), ("obj-69", 0, "obj-85", 2)]

    def test_add_outlet_left_shifts_cords_and_types(self):
        """WR-02: outlettype and cords stay aligned after a left insert."""
        p, _, art, inner = self._articulation()
        art.outlettype = ["bang", "signal"]
        inner.add_box("outlet", x=0, y=200, skip_overlap_check=True)
        assert art.numoutlets == 3
        assert art.outlettype == ["", "bang", "signal"]
        assert [c for c in _cords(p) if c[0] == "obj-85"] == [
            ("obj-85", 1, "obj-4", 0), ("obj-85", 2, "obj-73", 1)]

    def test_add_then_remove_left_port_restores_cords(self):
        """WR-02 + CR-02: add at rank 0 then remove it is a no-op on the parent."""
        p, _, art, inner = self._articulation()
        before = _cords(p)
        new_inlet = inner.add_box("inlet", x=0, y=20, skip_overlap_check=True)
        result = inner.remove_box(new_inlet)
        assert result.parent_orphaned == []
        assert _cords(p) == before
        assert art.numinlets == 2

    def test_embedded_bpatcher_declared_ports_not_shifted(self):
        """WR-02: ports the bpatcher declared before its inner ports existed are
        filled in, not inserted, so their cords keep their index. Once an add
        grows the count past the declared one, it is a real insert and shifts.
        """
        p = Patcher()
        bp, inner = p.add_bpatcher(embedded=True, numinlets=2, numoutlets=1)
        a = p.add_box("button")
        b = p.add_box("button")
        p.add_connection(a, 0, bp, 0)
        p.add_connection(b, 0, bp, 1)
        inner.add_box("inlet", x=100, y=20, skip_overlap_check=True)
        inner.add_box("inlet", x=10, y=20, skip_overlap_check=True)
        assert bp.numinlets == 2
        assert [c for c in _cords(p) if c[2] == bp.id] == [
            (a.id, 0, bp.id, 0), (b.id, 0, bp.id, 1)]
        inner.add_box("inlet", x=0, y=20, skip_overlap_check=True)
        assert bp.numinlets == 3
        assert [c for c in _cords(p) if c[2] == bp.id] == [
            (a.id, 0, bp.id, 1), (b.id, 0, bp.id, 2)]

    def test_replace_left_port_with_port_does_not_shift(self):
        """Same-kind port replacement at the same x keeps every parent cord."""
        p, _, art, inner = self._articulation()
        before = _cords(p)
        result = inner.replace_box(_box(inner, "obj-1"), "inlet")
        assert art.numinlets == 2
        assert _cords(p) == before
        assert result.parent_orphaned == []
        res2 = inner.replace_box(_box(inner, "obj-3"), "outlet")
        assert _cords(p) == before
        assert res2.parent_orphaned == []

    def test_api_built_subpatcher(self):
        p = Patcher()
        parent, inner = p.add_subpatcher("s", inlets=1, outlets=1)
        i2 = inner.add_box("inlet", x=300, y=30, skip_overlap_check=True)
        o2 = inner.add_box("outlet", x=300, y=250, skip_overlap_check=True)
        assert (parent.numinlets, parent.numoutlets) == (2, 2)
        assert parent.outlettype == ["", ""]
        inner.remove_box(i2)
        inner.remove_box(o2)
        assert (parent.numinlets, parent.numoutlets) == (1, 1)
        assert parent.outlettype == [""]

    def test_embedded_bpatcher_grow_only(self):
        p = Patcher()
        bp, inner = p.add_bpatcher(embedded=True, numinlets=2, numoutlets=1)
        src = p.add_box("button")
        p.add_connection(src, 0, bp, 1)
        inner.add_box("inlet", x=30, y=20, skip_overlap_check=True)
        assert bp.numinlets == 2
        assert (src.id, 0, bp.id, 1) in _cords(p)

    def test_replace_port_with_port_keeps_parent(self):
        p, _, art, inner = self._articulation()
        before = [c for c in _cords(p) if c[2] == "obj-85"]
        result = inner.replace_box(_box(inner, "obj-2"), "inlet")
        assert art.numinlets == 2
        assert [c for c in _cords(p) if c[2] == "obj-85"] == before
        assert result.parent_orphaned == []

    def test_top_level_port_box_no_sync(self):
        p, _ = _load_bassoon()
        before = p.to_dict()
        b = p.add_box("inlet", x=2000, y=2000, skip_overlap_check=True)
        result = p.remove_box(b)
        assert result.orphaned == [] and result.parent_orphaned == []
        assert p.to_dict() == before

    def test_gen_subpatcher_no_sync(self):
        p = Patcher()
        gbox, ginner = p.add_gen("out1 = in1 * in2;")
        counts = (gbox.numinlets, gbox.numoutlets, list(gbox.outlettype))
        in_box = next(b for b in ginner.boxes if (b.text or "").startswith("in "))
        result = ginner.remove_box(in_box)
        assert (gbox.numinlets, gbox.numoutlets, list(gbox.outlettype)) == counts
        assert result.parent_orphaned == []

    def test_replace_box_safe_auto_keeps_parent_orphaned(self):
        """CR-01 (Q28 review): the auto-rewire path passes parent_orphaned through.

        A loaded outlet box is 2 in / 0 out, like dac~, so this takes the
        auto-rewire branch.
        """
        p, _, art, inner = self._articulation()
        result = inner.replace_box_safe(_box(inner, "obj-4"), "dac~")
        assert result.orphaned == []
        assert result.parent_orphaned == [_orphan("obj-85", 1, "obj-73", 1)]
        assert ("obj-85", 1, "obj-73", 1) not in _cords(p)
        assert art.numoutlets == 1

    def test_remove_non_port_box_returns_own_cords(self):
        """WR-01 (Q28 review): orphaned holds the cords removed from this patcher."""
        p, _, _, inner = self._articulation()
        box = _box(inner, "obj-5")
        result = inner.remove_box(box)
        assert result.box is box
        assert result.orphaned == [
            _orphan("obj-1", 0, "obj-5", 0),
            _orphan("obj-5", 1, "obj-7", 0),
            _orphan("obj-5", 0, "obj-6", 0),
        ]
        assert result.parent_orphaned == []

    def test_remove_port_box_splits_own_and_parent_cords(self):
        """WR-01 (Q28 review): a port's own cords and the parent's never mix."""
        p, _, art, inner = self._articulation()
        result = inner.remove_box(_box(inner, "obj-2"))
        assert result.orphaned == [_orphan("obj-2", 0, "obj-10", 0)]
        assert result.parent_orphaned == [_orphan("obj-69", 0, "obj-85", 1)]
