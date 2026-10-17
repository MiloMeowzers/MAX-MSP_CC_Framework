"""Q33 consolidation guard: one Box factory, shared helpers, structured critic fields."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from src.maxpat.db_lookup import ObjectDatabase
from src.maxpat.defaults import FONT_NAME, FONT_SIZE
from src.maxpat.patcher import Box

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def db() -> ObjectDatabase:
    return ObjectDatabase()


def _calls(path: Path, attr: str, owner: str) -> list[ast.Call]:
    """Call nodes in *path* whose func is ``<owner>.<attr>``."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [
        n for n in ast.walk(tree)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and n.func.attr == attr
        and isinstance(n.func.value, ast.Name)
        and n.func.value.id == owner
    ]


# ---------------------------------------------------------------------------
# Task 1: Box.structural (review S3)
# ---------------------------------------------------------------------------


class TestBoxStructural:
    def test_attribute_set_matches_init(self, db):
        s = Box.structural("panel", "", 1, 0, [], [0.0, 0.0, 10.0, 10.0], box_id="obj-1")
        b = Box("toggle", box_id="obj-2", db=db)
        assert set(vars(s)) == set(vars(b))

    def test_fields_and_defaults(self):
        rect = [1.0, 2.0, 30.0, 22.0]
        otype = ["signal"]
        b = Box.structural("newobj", "in 1", 0, 1, otype, rect, box_id="obj-7")
        assert b.maxclass == "newobj"
        assert b.text == "in 1"
        assert b.numinlets == 0
        assert b.numoutlets == 1
        assert b.outlettype is otype
        assert b.patching_rect is rect
        assert b.id == "obj-7"
        assert b.name == "in"
        assert b.args == []
        assert b.fontname == FONT_NAME
        assert b.fontsize == FONT_SIZE
        assert b.extra_attrs == {}
        assert b.presentation is False
        for attr in ("presentation_rect", "target_id", "nudged_from", "_raw",
                     "_loaded_rect", "_loaded", "_inner_patcher",
                     "_saved_object_attributes", "_bpatcher_attrs"):
            assert getattr(b, attr) is None, attr

        assert Box.structural("panel", "", 1, 0, [], [0, 0, 1, 1], box_id="a").name == "panel"
        assert Box.structural("newobj", "p x", 1, 1, [""], [0, 0, 1, 1], box_id="a",
                              name="patcher").name == "patcher"

        args = ["a", 0]
        inner = object()
        saved = {"k": 1}
        bp = {"args": args}
        b2 = Box.structural("bpatcher", "", 1, 1, [""], [0, 0, 1, 1], box_id="b",
                            args=args, font=("Arial", 11.0), inner=inner,
                            saved_attrs=saved, bpatcher_attrs=bp)
        assert b2.args is args
        assert (b2.fontname, b2.fontsize) == ("Arial", 11.0)
        assert b2._inner_patcher is inner
        assert b2._saved_object_attributes is saved
        assert b2._bpatcher_attrs is bp

    def test_extra_attrs_may_reuse_positional_names(self):
        b = Box.structural("textbutton", "", 1, 3, ["", "", "int"], [0, 0, 24, 24],
                           box_id="m", text="3", fontname="Arial")
        assert b.extra_attrs == {"text": "3", "fontname": "Arial"}
        assert b.text == ""

    def test_to_dict_matches_hand_built(self):
        code = "out1 = in1;"
        s = Box.structural("codebox", "", 1, 1, [""], [50.0, 50.0, 400.0, 200.0],
                           box_id="obj-3", code=code, fontname=FONT_NAME,
                           fontsize=FONT_SIZE)
        h = Box.__new__(Box)
        h.name = "codebox"
        h.args = []
        h.id = "obj-3"
        h.maxclass = "codebox"
        h.text = ""
        h.numinlets = 1
        h.numoutlets = 1
        h.outlettype = [""]
        h.patching_rect = [50.0, 50.0, 400.0, 200.0]
        h.fontname = FONT_NAME
        h.fontsize = FONT_SIZE
        h.presentation = False
        h.presentation_rect = None
        h.target_id = None
        h._inner_patcher = None
        h._saved_object_attributes = None
        h._bpatcher_attrs = None
        h._raw = None
        h.extra_attrs = {"code": code, "fontname": FONT_NAME, "fontsize": FONT_SIZE}
        assert json.dumps(s.to_dict()) == json.dumps(h.to_dict())

    @pytest.mark.parametrize(
        "rel", ["src/maxpat/builders.py", "src/maxpat/rnbo.py", "src/maxpat/externals.py"]
    )
    def test_builders_use_the_factory(self, rel):
        path = REPO_ROOT / rel
        assert _calls(path, "__new__", "Box") == []
        assert _calls(path, "structural", "Box")
