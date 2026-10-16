"""Edit fidelity II (fix-plan Q29): review findings B4, B8, B9 and B10.

- B9: saves keep the file's own JSON layout (MAX 9 inline scalar arrays, or
  the framework's expanded json.dumps arrays), so a no-op save is
  byte-identical.
- B8: write_gendsp edits an existing .gendsp in place (codebox code and
  in/out ports) instead of regenerating it.
- B4 / B10: replace_box identity and in-range rewire; add_box placement
  (added by Task 2).

These tests read committed patches only (read_text / json.loads /
read_patch) and save only to tmp_path copies. They never write the two
MAX-saved reference files (FDNVerb.maxhelp, sample-layers.maxpat), not even
with identical bytes.
"""

from __future__ import annotations

import copy
import difflib
import hashlib
import json
import pathlib
import shutil
import warnings

import pytest

from src.maxpat.patcher import Patcher

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
PATCHES_DIR = PROJECT_ROOT / "patches"

REF_FILES = [
    PATCHES_DIR / "FDNVerb" / "generated" / "FDNVerb.maxhelp",
    PATCHES_DIR / "sample-layers" / "generated" / "sample-layers.maxpat",
]
GONG_GENDSP = PATCHES_DIR / "gong-model" / "generated" / "gong-engine.gendsp"

# Saves to tmp_path are outside any repository: the auto-commit warns.
pytestmark = pytest.mark.filterwarnings(
    "ignore:.*not auto-committed:UserWarning"
)


@pytest.fixture(autouse=True)
def _no_git_env(monkeypatch):
    """Keep auto-commit away from the repo, whatever the caller's env."""
    monkeypatch.delenv("GIT_DIR", raising=False)
    monkeypatch.delenv("GIT_WORK_TREE", raising=False)


def _sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _committed_patch_files() -> list[pathlib.Path]:
    out = []
    for suffix in (".maxpat", ".maxhelp", ".gendsp"):
        out.extend(PATCHES_DIR.rglob(f"*{suffix}"))
    return sorted(out)


# ---------------------------------------------------------------------------
# B9: tracer -- read -> no-op save -> disk is byte-identical
# ---------------------------------------------------------------------------


class TestB9TracerNoOpSave:
    @pytest.mark.parametrize("ref", REF_FILES, ids=lambda p: p.name)
    def test_noop_save_of_max_saved_copy_is_byte_identical(self, ref, tmp_path):
        from src.maxpat.hooks import read_patch, save_patch_roundtrip

        before = _sha(ref)
        copy_path = tmp_path / ref.name
        copy_path.write_bytes(ref.read_bytes())

        p, T = read_patch(copy_path)
        save_patch_roundtrip(p.to_dict(), copy_path, original_text=T)

        assert copy_path.read_bytes() == ref.read_bytes()
        assert _sha(ref) == before


# ---------------------------------------------------------------------------
# B9: the MAX-style writer
# ---------------------------------------------------------------------------


class TestB9MaxJsonWriter:
    @pytest.mark.parametrize("ref", REF_FILES, ids=lambda p: p.name)
    def test_reference_file_in_memory(self, ref):
        from src.maxpat.hooks import format_patch_text

        t = ref.read_text()
        assert format_patch_text(Patcher.from_dict(json.loads(t)).to_dict(), t) == t

    def test_empty_list(self):
        from src.maxpat.maxjson import dumps_max

        assert dumps_max({"a": []}) == '{\n    "a": []\n}'

    def test_empty_dict_closing_pad_inside_braces(self):
        from src.maxpat.maxjson import dumps_max

        text = dumps_max({"a": {"b": {}}})
        assert '"b": {' + " " * 8 + "}" in text

    def test_scalar_list_inline(self):
        from src.maxpat.maxjson import dumps_max

        assert dumps_max([1, 2.5, "x", True, None]) == '[ 1, 2.5, "x", true, null ]'

    def test_list_holding_dict_expands(self):
        from src.maxpat.maxjson import dumps_max

        assert dumps_max({"l": [{"a": 1}]}) == (
            '{\n    "l": [\n        {\n            "a": 1\n        }\n    ]\n}'
        )

    def test_list_of_lists_expands_outer_inner_inline(self):
        from src.maxpat.maxjson import dumps_max

        assert dumps_max([[1, 2], [3]]) == "[\n    [ 1, 2 ],\n    [ 3 ]\n]"

    def test_non_ascii_kept_raw(self):
        from src.maxpat.maxjson import dumps_max

        assert dumps_max({"t": "café ♪"}) == '{\n    "t": "café ♪"\n}'

    def test_non_str_keys_convert_like_json(self):
        from src.maxpat.maxjson import dumps_max

        # True == 1 as a dict key, so each key gets its own dict.
        assert dumps_max({True: 0}) == '{\n    "true": 0\n}'
        assert dumps_max({False: 0}) == '{\n    "false": 0\n}'
        assert dumps_max({None: 0}) == '{\n    "null": 0\n}'
        assert dumps_max({1: 0}) == '{\n    "1": 0\n}'
        assert dumps_max({1.5: 0}) == '{\n    "1.5": 0\n}'

    def test_tuple_is_a_list(self):
        from src.maxpat.maxjson import dumps_max

        assert dumps_max({"r": (1.0, 2.0)}) == '{\n    "r": [ 1.0, 2.0 ]\n}'

    def test_round_trip_property(self):
        from src.maxpat.maxjson import dumps_max

        x = {
            "patcher": {
                "rect": [0.0, 1.5, 2, -3],
                "boxes": [{"box": {"id": "obj-1", "text": "a\nb [", "o": []}}],
                "lines": [],
                "nested": {"e": {}, "l": [[1, [2, {"k": None}]], "s"]},
            }
        }
        assert json.loads(dumps_max(x)) == x
        assert json.loads(dumps_max(x, indent="\t")) == x

    def test_has_expanded_arrays(self):
        from src.maxpat.maxjson import dumps_max, has_expanded_arrays

        patch = {"patcher": {"rect": [1.0, 2.0, 3.0, 4.0], "boxes": []}}
        assert has_expanded_arrays(json.dumps(patch, indent=2)) is True
        assert has_expanded_arrays(dumps_max(patch)) is False
        tricky = {"patcher": {"text": "x [\n1", "rect": [1.0]}}
        assert has_expanded_arrays(dumps_max(tricky)) is False

    def test_every_committed_patch_noop_text_identical(self):
        from src.maxpat.hooks import format_patch_text

        files = _committed_patch_files()
        assert len(files) >= 69
        bad = []
        for f in files:
            t = f.read_text()
            out = format_patch_text(Patcher.from_dict(json.loads(t)).to_dict(), t)
            if out != t:
                bad.append(str(f.relative_to(PROJECT_ROOT)))
        assert bad == []

    def test_new_file_is_max_layout(self, tmp_path):
        from src.maxpat.hooks import format_patch_text, save_patch_roundtrip

        p = Patcher()
        p.add_box("cycle~", ["440"], x=30.0, y=30.0)
        d = p.to_dict()
        path = tmp_path / "new.maxpat"
        save_patch_roundtrip(d, path)
        text = path.read_text()
        assert text == format_patch_text(d)
        assert '"rect": [ ' in text
        assert not any(
            line.strip().rstrip(",").replace(".", "", 1).lstrip("-").isdigit()
            for line in text.splitlines()
        )

    def test_expanded_file_stays_expanded(self, tmp_path):
        from src.maxpat.hooks import read_patch, save_patch_roundtrip

        p = Patcher()
        a = p.add_box("cycle~", ["440"], x=30.0, y=30.0)
        b = p.add_box("*~", ["0.2"], x=30.0, y=80.0)
        p.add_connection(a, 0, b, 0)
        path = tmp_path / "exp.maxpat"
        original = json.dumps(p.to_dict(), indent=2)
        path.write_text(original)

        q, T = read_patch(path)
        save_patch_roundtrip(q.to_dict(), path, original_text=T)
        assert path.read_text() == original

    def test_real_edit_changes_one_line(self, tmp_path):
        from src.maxpat.hooks import read_patch, save_patch_roundtrip

        ref = REF_FILES[1]
        copy_path = tmp_path / ref.name
        copy_path.write_bytes(ref.read_bytes())
        p, T = read_patch(copy_path)
        box = next(b for b in p.boxes if b.maxclass == "comment")
        x, y = box.patching_rect[0], box.patching_rect[1]
        p.modify_box(box, position=[x + 10.0, y + 10.0])
        save_patch_roundtrip(p.to_dict(), copy_path, original_text=T)

        diff = [
            ln for ln in difflib.unified_diff(
                T.splitlines(), copy_path.read_text().splitlines(), lineterm="", n=0
            )
            if ln.startswith(("+", "-")) and not ln.startswith(("+++", "---"))
        ]
        assert len(diff) == 2, diff
        assert ref.read_bytes() != copy_path.read_bytes()


# ---------------------------------------------------------------------------
# B8: write_gendsp round-trips an existing .gendsp
# ---------------------------------------------------------------------------


def _gong_copy(tmp_path) -> pathlib.Path:
    dst = tmp_path / "gong-engine.gendsp"
    shutil.copyfile(GONG_GENDSP, dst)
    return dst


def _boxes_by_id(d: dict) -> dict:
    return {b["box"]["id"]: b["box"] for b in d["patcher"]["boxes"]}


def _codebox(d: dict) -> dict:
    return next(b["box"] for b in d["patcher"]["boxes"] if b["box"]["maxclass"] == "codebox")


def _lines(d: dict) -> list[tuple]:
    return [
        (tuple(l["patchline"]["source"]), tuple(l["patchline"]["destination"]))
        for l in d["patcher"]["lines"]
    ]


def _box_with_text(d: dict, text: str) -> dict | None:
    for b in d["patcher"]["boxes"]:
        if b["box"].get("text") == text:
            return b["box"]
    return None


def _quiet_write_gendsp(*args, **kwargs):
    from src.maxpat.hooks import SaveGateWarning, write_gendsp

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", SaveGateWarning)
        return write_gendsp(*args, **kwargs)


class TestB8GendspRoundTrip:
    def test_noop_write_is_byte_identical(self, tmp_path):
        from src.maxpat.hooks import write_gendsp

        path = _gong_copy(tmp_path)
        original = path.read_bytes()
        code = _codebox(json.loads(original))["code"]
        write_gendsp(code, path)
        assert path.read_bytes() == original
        assert '"v1.12.1"' in path.read_text()

    def test_new_code_same_io_changes_only_code(self, tmp_path):
        from src.maxpat.hooks import write_gendsp

        path = _gong_copy(tmp_path)
        before = json.loads(path.read_text())
        new_code = _codebox(before)["code"] + "\n// edited by Q29 test\n"
        result = write_gendsp(new_code, path)
        after = json.loads(path.read_text())

        expected = copy.deepcopy(before)
        _codebox(expected)["code"] = new_code
        assert after == expected
        assert result.orphaned == []

    def test_added_output_grows_ports(self, tmp_path):
        from src.maxpat.hooks import write_gendsp

        path = _gong_copy(tmp_path)
        before = json.loads(path.read_text())
        new_code = _codebox(before)["code"] + "\nout3 = 0;\n"
        result = write_gendsp(new_code, path)
        after = json.loads(path.read_text())

        out3 = _box_with_text(after, "out 3")
        assert out3 is not None
        cb = _codebox(after)
        assert (cb["id"], 2) in [s for s, d in _lines(after) if d == (out3["id"], 0)]
        assert cb["numoutlets"] == 3
        assert cb["outlettype"] == ["", "", ""]
        assert result.orphaned == []
        after_ids = _boxes_by_id(after)
        for bid, box in _boxes_by_id(before).items():
            if box["maxclass"] == "codebox":
                continue
            assert after_ids[bid] == box

    def test_removed_output_removes_port_box(self, tmp_path):
        path = _gong_copy(tmp_path)
        before = json.loads(path.read_text())
        cb_id = _codebox(before)["id"]
        out2 = _box_with_text(before, "out 2")
        result = _quiet_write_gendsp("out1 = in1;\n", path)
        after = json.loads(path.read_text())

        assert _box_with_text(after, "out 2") is None
        assert result.orphaned == [{
            "source_id": cb_id, "source_outlet": 1,
            "dest_id": out2["id"], "dest_inlet": 0,
        }]
        assert _codebox(after)["numoutlets"] == 1
        assert '"v1.12.1"' in path.read_text()

    def test_added_input_grows_ports(self, tmp_path):
        from src.maxpat.hooks import write_gendsp

        path = _gong_copy(tmp_path)
        write_gendsp("out1 = in1 + in2;\nout2 = in1;\n", path)
        after = json.loads(path.read_text())
        in2 = _box_with_text(after, "in 2")
        assert in2 is not None
        cb = _codebox(after)
        assert ((in2["id"], 0), (cb["id"], 1)) in _lines(after)
        assert cb["numinlets"] == 2
        assert _box_with_text(after, "v1.12.1") is not None

    def test_surplus_input_feeding_user_graph_is_kept(self, tmp_path):
        from src.maxpat.codegen import generate_gendsp

        d = generate_gendsp("out1 = in1 + in2;\nout2 = in2;\n")
        in2 = _box_with_text(d, "in 2")
        out2 = _box_with_text(d, "out 2")
        d["patcher"]["lines"].append(
            {"patchline": {"source": [in2["id"], 0], "destination": [out2["id"], 0]}}
        )
        path = tmp_path / "user.gendsp"
        path.write_text(json.dumps(d, indent=2))
        cb_id = _codebox(d)["id"]

        result = _quiet_write_gendsp("out1 = in1;\nout2 = in1;\n", path)
        after = json.loads(path.read_text())
        assert _box_with_text(after, "in 2") is not None
        assert ((in2["id"], 0), (out2["id"], 0)) in _lines(after)
        assert ((in2["id"], 0), (cb_id, 1)) not in _lines(after)
        assert {
            "source_id": in2["id"], "source_outlet": 0,
            "dest_id": cb_id, "dest_inlet": 1,
        } in result.orphaned
        assert _codebox(after)["numinlets"] == 1

    @pytest.mark.parametrize("n_codeboxes", [0, 2])
    def test_not_single_codebox_raises(self, tmp_path, n_codeboxes):
        from src.maxpat.codegen import generate_gendsp
        from src.maxpat.hooks import write_gendsp

        d = generate_gendsp("out1 = in1;\n")
        boxes = d["patcher"]["boxes"]
        cb = next(b for b in boxes if b["box"]["maxclass"] == "codebox")
        if n_codeboxes == 0:
            boxes.remove(cb)
            d["patcher"]["lines"] = []
        else:
            extra = copy.deepcopy(cb)
            extra["box"]["id"] = "obj-99"
            extra["box"]["patching_rect"] = [500.0, 80.0, 400.0, 200.0]
            boxes.append(extra)
        path = tmp_path / "multi.gendsp"
        path.write_text(json.dumps(d, indent=2))
        original = path.read_bytes()

        with pytest.raises(ValueError, match="codebox"):
            write_gendsp("out1 = in1 * 2;\n", path)
        assert path.read_bytes() == original

    def test_explicit_counts_override_detection(self, tmp_path):
        from src.maxpat.hooks import write_gendsp

        path = _gong_copy(tmp_path)
        code = _codebox(json.loads(path.read_text()))["code"]
        write_gendsp(code, path, num_outputs=3)
        after = json.loads(path.read_text())
        assert _box_with_text(after, "out 3") is not None
        assert _codebox(after)["numoutlets"] == 3
        assert _box_with_text(after, "v1.12.1") is not None

    def test_max_layout_gendsp_stays_max_layout(self, tmp_path):
        from src.maxpat.hooks import write_gendsp
        from src.maxpat.maxjson import dumps_max

        path = tmp_path / "gong-engine.gendsp"
        before = json.loads(GONG_GENDSP.read_text())
        T = dumps_max(before)
        path.write_text(T)
        new_code = _codebox(before)["code"] + "\n// edited\n"
        write_gendsp(new_code, path)

        changed = [
            ln for ln in difflib.unified_diff(
                T.splitlines(), path.read_text().splitlines(), lineterm="", n=0
            )
            if ln.startswith(("+", "-")) and not ln.startswith(("+++", "---"))
        ]
        assert len(changed) == 2
        assert all('"code": ' in ln for ln in changed)

    def test_missing_path_still_generates(self, tmp_path):
        from src.maxpat.codegen import generate_gendsp
        from src.maxpat.hooks import write_gendsp

        code = "out1 = in1 * 0.5;\nout2 = in2;\n"
        path = tmp_path / "fresh.gendsp"
        result = write_gendsp(code, path)
        written = json.loads(path.read_text())
        assert len(written["patcher"]["boxes"]) == len(
            generate_gendsp(code)["patcher"]["boxes"]
        )
        assert result.orphaned == []


# ---------------------------------------------------------------------------
# B4: replace_box keeps the box's identity
# ---------------------------------------------------------------------------


def _reload(p: Patcher) -> Patcher:
    """to_dict -> from_dict so every box is a loaded (round-trip) box."""
    return Patcher.from_dict(p.to_dict())


def _box_dict(d: dict, box_id: str) -> dict:
    return next(b["box"] for b in d["patcher"]["boxes"] if b["box"]["id"] == box_id)


def _index_of(d: dict, box_id: str) -> int:
    return [b["box"]["id"] for b in d["patcher"]["boxes"]].index(box_id)


def _three_box_patch(middle_name, middle_args=None, middle_attrs=None,
                     presentation_rect=None):
    p = Patcher()
    p.add_box("loadbang", x=30.0, y=30.0)
    mid = p.add_box(middle_name, middle_args, x=30.0, y=90.0)
    p.add_box("print", x=30.0, y=200.0)
    if middle_attrs:
        mid.extra_attrs.update(copy.deepcopy(middle_attrs))
    if presentation_rect is not None:
        p.add_to_presentation(mid, presentation_rect)
    q = _reload(p)
    return q, q.boxes[1]


_VALUEOF = {
    "parameter_longname": "Cutoff",
    "parameter_shortname": "Cutoff",
    "parameter_type": 0,
    "parameter_mmax": 127.0,
}


def _dial_attrs():
    return {
        "varname": "cutoff",
        "parameter_enable": 1,
        "needlecolor": [1.0, 0.0, 0.0, 1.0],
        "bgcolor": [0.2, 0.2, 0.2, 1.0],
        "saved_attribute_attributes": {
            "valueof": copy.deepcopy(_VALUEOF),
            "bgcolor": {"expression": ""},
        },
    }


class TestB4ReplaceIdentity:
    def test_newobj_identity_kept(self):
        attrs = {
            "varname": "osc",
            "bgcolor": [0.1, 0.2, 0.3, 1.0],
            "hint": "the oscillator",
            "annotation": "Main oscillator",
        }
        p, old = _three_box_patch("cycle~", ["440"], attrs, [10.0, 20.0, 80.0, 22.0])
        result = p.replace_box(old, "saw~")
        d = p.to_dict()
        new = _box_dict(d, result.box.id)
        assert _index_of(d, result.box.id) == 1
        assert new["presentation"] == 1
        assert new["presentation_rect"] == [10.0, 20.0, 80.0, 22.0]
        for k, v in attrs.items():
            assert new[k] == v

    def test_dial_to_live_dial_keeps_parameter_blocks(self):
        p, old = _three_box_patch("dial", None, _dial_attrs())
        result = p.replace_box(old, "live.dial")
        new = _box_dict(p.to_dict(), result.box.id)
        assert new["varname"] == "cutoff"
        assert new["parameter_enable"] == 1
        assert new["needlecolor"] == [1.0, 0.0, 0.0, 1.0]
        assert new["saved_attribute_attributes"]["valueof"] == _VALUEOF
        assert "bgcolor" not in new
        assert "bgcolor" not in new["saved_attribute_attributes"]

    def test_dial_to_cycle_drops_parameter_blocks(self):
        p, old = _three_box_patch("dial", None, _dial_attrs())
        result = p.replace_box(old, "cycle~", args=["440"])
        new = _box_dict(p.to_dict(), result.box.id)
        assert new["varname"] == "cutoff"
        assert "parameter_enable" not in new
        assert "needlecolor" not in new
        assert "valueof" not in new.get("saved_attribute_attributes", {})

    def test_playlist_colour_and_expression_kept(self):
        attrs = {
            "candicane2": [0.5, 0.5, 0.5, 1.0],
            "saved_attribute_attributes": {
                "candicane2": {"expression": ""},
            },
        }
        p, old = _three_box_patch("playlist~", None, attrs)
        result = p.replace_box(old, "playlist~")
        new = _box_dict(p.to_dict(), result.box.id)
        assert new["candicane2"] == [0.5, 0.5, 0.5, 1.0]
        assert new["saved_attribute_attributes"]["candicane2"] == {"expression": ""}

    def test_replace_box_safe_keeps_identity(self):
        attrs = {"varname": "osc", "hint": "h"}
        p, old = _three_box_patch("cycle~", ["440"], attrs, [5.0, 5.0, 80.0, 22.0])
        result = p.replace_box_safe(old, "saw~")
        d = p.to_dict()
        new = _box_dict(d, result.box.id)
        assert _index_of(d, result.box.id) == 1
        assert new["varname"] == "osc"
        assert new["hint"] == "h"
        assert new["presentation_rect"] == [5.0, 5.0, 80.0, 22.0]

    def test_plain_replace_box_still_orphans_every_cord(self):
        p = Patcher()
        src = p.add_box("number", x=30.0, y=30.0)
        old = p.add_box("pack", ["0", "0"], x=30.0, y=90.0)
        dst = p.add_box("print", x=30.0, y=150.0)
        p.add_connection(src, 0, old, 0)
        p.add_connection(old, 0, dst, 0)
        result = p.replace_box(old, "pack", args=["0", "0", "0"])
        assert len(result.orphaned) == 2
        assert p.lines == []


# ---------------------------------------------------------------------------
# B4: replace_box_safe rewires every in-range cord
# ---------------------------------------------------------------------------


def _cords(p: Patcher) -> set:
    return {
        (pl.source_id, pl.source_outlet, pl.dest_id, pl.dest_inlet)
        for pl in p.lines
    }


class TestB4Rewire:
    def test_pack_grow_review_repro(self):
        p = Patcher()
        a = p.add_box("number", x=30.0, y=30.0)
        b = p.add_box("number", x=120.0, y=30.0)
        old = p.add_box("pack", ["0", "0"], x=30.0, y=90.0)
        out = p.add_box("print", x=30.0, y=150.0)
        p.add_connection(a, 0, old, 0)
        p.add_connection(b, 0, old, 1)
        p.add_connection(old, 0, out, 0)
        result = p.replace_box_safe(old, "pack", args=["0", "0", "0"])
        new = result.box
        assert result.orphaned == []
        assert _cords(p) == {
            (a.id, 0, new.id, 0), (b.id, 0, new.id, 1), (new.id, 0, out.id, 0),
        }

    def test_pack_shrink_orphans_only_out_of_range(self):
        p = Patcher()
        srcs = [p.add_box("number", x=30.0 + 90.0 * i, y=30.0) for i in range(3)]
        old = p.add_box("pack", ["0", "0", "0"], x=30.0, y=90.0)
        for i, s in enumerate(srcs):
            p.add_connection(s, 0, old, i)
        result = p.replace_box_safe(old, "pack", args=["0", "0"])
        assert result.orphaned == [{
            "source_id": srcs[2].id, "source_outlet": 0,
            "dest_id": old.id, "dest_inlet": 2,
        }]
        assert _cords(p) == {
            (srcs[0].id, 0, result.box.id, 0), (srcs[1].id, 0, result.box.id, 1),
        }

    def test_loaded_cord_attributes_kept(self):
        p = Patcher()
        a = p.add_box("number", x=30.0, y=30.0)
        old = p.add_box("pack", ["0", "0"], x=30.0, y=90.0)
        p.add_connection(a, 0, old, 1)
        d = p.to_dict()
        pl = d["patcher"]["lines"][0]["patchline"]
        pl["midpoints"] = [40.0, 60.0, 100.0, 60.0]
        pl["order"] = 2
        pl["color"] = [1.0, 0.0, 0.0, 1.0]
        pl["hidden"] = 1
        q = Patcher.from_dict(d)
        old_q = next(b for b in q.boxes if b.id == old.id)
        result = q.replace_box_safe(old_q, "pack", args=["0", "0", "0"])
        assert result.orphaned == []
        lines = q.to_dict()["patcher"]["lines"]
        assert len(lines) == 1
        out = lines[0]["patchline"]
        assert out["destination"] == [result.box.id, 1]
        assert out["midpoints"] == [40.0, 60.0, 100.0, 60.0]
        assert out["order"] == 2
        assert out["color"] == [1.0, 0.0, 0.0, 1.0]
        assert out["hidden"] == 1

    def test_signal_into_control_only_inlet_stays_orphaned(self):
        p = Patcher()
        num = p.add_box("number", x=30.0, y=30.0)
        old = p.add_box("snapshot~", x=30.0, y=90.0)
        out = p.add_box("print", x=30.0, y=150.0)
        p.add_connection(num, 0, old, 0)
        p.add_connection(old, 0, out, 0)
        result = p.replace_box_safe(old, "cycle~", args=["440"])
        assert result.orphaned == [{
            "source_id": old.id, "source_outlet": 0,
            "dest_id": out.id, "dest_inlet": 0,
        }]
        assert _cords(p) == {(num.id, 0, result.box.id, 0)}

    def test_manual_returns_every_cord(self):
        p = Patcher()
        a = p.add_box("number", x=30.0, y=30.0)
        old = p.add_box("pack", ["0", "0"], x=30.0, y=90.0)
        p.add_connection(a, 0, old, 0)
        result = p.replace_box_safe(old, "pack", args=["0", "0", "0"], rewire="manual")
        assert len(result.orphaned) == 1
        assert p.lines == []

    def test_equal_count_unchanged(self):
        p = Patcher()
        num = p.add_box("number", x=30.0, y=30.0)
        old = p.add_box("cycle~", ["440"], x=30.0, y=90.0)
        dac = p.add_box("ezdac~", x=30.0, y=150.0)
        p.add_connection(num, 0, old, 0)
        p.add_connection(old, 0, dac, 0)
        p.add_connection(old, 0, dac, 1)
        result = p.replace_box_safe(old, "saw~")
        assert result.orphaned == []
        assert len(p.lines) == 3

    def test_unverified_msp_source_stays_rewired(self):
        """ears.split~ (outlets marked signal, not overridden) -> trigger."""
        p = Patcher()
        old = p.add_box("ears.split~", x=30.0, y=90.0)
        t = p.add_box("trigger", ["b"], x=30.0, y=150.0)
        p.add_connection(old, 1, t, 0)
        result = p.replace_box_safe(old, "ears.split~")
        assert result.orphaned == []
        assert _cords(p) == {(result.box.id, 1, t.id, 0)}


# ---------------------------------------------------------------------------
# B10: add_box moves a box only on a real overlap, and reports it
# ---------------------------------------------------------------------------


def _rendered(p: Patcher, box):
    from src.maxpat.sizing import is_max_saved, rendered_rect

    r = rendered_rect(box, max_saved=is_max_saved(p.props))
    return r if r is not None else list(box.patching_rect)


class TestB10AddBoxPlacement:
    def test_explicit_position_kept(self):
        p = Patcher()
        box = p.add_box("cycle~", ["440"], x=37, y=52)
        assert box.patching_rect[0:2] == [37.0, 52.0]
        assert getattr(box, "nudged_from", None) is None

    def test_companion_meter_beside_gain_stays_put(self):
        from src.maxpat.patcher import BoxMovedWarning

        p = Patcher()
        gain = p.add_box("gain~", x=30.0, y=60.0)
        gx, gy, gw, _ = _rendered(p, gain)
        with warnings.catch_warnings():
            warnings.simplefilter("error", BoxMovedWarning)
            meter = p.add_box("meter~", x=gx + gw + 5.0, y=gy)
        assert meter.patching_rect[0:2] == [gx + gw + 5.0, gy]
        assert getattr(meter, "nudged_from", None) is None

    def test_real_overlap_moves_down_and_warns(self):
        from src.maxpat.patcher import BoxMovedWarning

        p = Patcher()
        blocker = p.add_box("cycle~", ["440"], x=60.0, y=60.0)
        with pytest.warns(BoxMovedWarning) as rec:
            box = p.add_box("print", x=65.0, y=62.0)
        msg = str(rec[0].message)
        assert blocker.id in msg and box.id in msg
        assert box.nudged_from == (65.0, 62.0)
        assert box.patching_rect[0] == 65.0
        bx, by, bw, bh = _rendered(p, box)
        for other in p.boxes:
            if other is box:
                continue
            ox, oy, ow, oh = _rendered(p, other)
            clear = (
                bx + bw + 5.0 <= ox or ox + ow + 5.0 <= bx
                or by + bh + 5.0 <= oy or oy + oh + 5.0 <= by
            )
            assert clear, (other.id, (bx, by, bw, bh), (ox, oy, ow, oh))

    def test_default_origin_moves_silently(self):
        from src.maxpat.patcher import BoxMovedWarning

        p = Patcher()
        p.add_box("loadbang")
        with warnings.catch_warnings():
            warnings.simplefilter("error", BoxMovedWarning)
            second = p.add_box("print")
        assert second.patching_rect[0:2] != [0.0, 0.0]
        assert second.nudged_from == (0.0, 0.0)

    def test_skip_overlap_check_never_moves(self):
        p = Patcher()
        p.add_box("cycle~", ["440"], x=60.0, y=60.0)
        box = p.add_box("print", x=61.0, y=61.0, skip_overlap_check=True)
        assert box.patching_rect[0:2] == [61.0, 61.0]
        assert getattr(box, "nudged_from", None) is None
