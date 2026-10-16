"""Q28 regression tests: edit fidelity for loaded patches.

Findings (``.planning/reviews/2026-10-11-repo-review.md``):

- B5: edits to loaded boxes (extra_attrs, fontname/fontsize) and cords
  (order, hidden, midpoints, color, extra_attrs) never reached disk.
- B6: ``Patcher.from_dict`` shared nested objects with the caller's dict, so
  edits wrote through to it.
- S4: the change-tracking semantics (load snapshot + diff at serialize) and
  the retired manual ``_raw`` copies.

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
