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


# ---------------------------------------------------------------------------
# Task 2: shared helpers (review S7, S12)
# ---------------------------------------------------------------------------


def _module_assigns(rel: str, name: str) -> bool:
    tree = ast.parse((REPO_ROOT / rel).read_text(encoding="utf-8"))
    for node in tree.body:
        targets = []
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        if any(isinstance(t, ast.Name) and t.id == name for t in targets):
            return True
    return False


def _defines_function(rel: str, name: str) -> bool:
    tree = ast.parse((REPO_ROOT / rel).read_text(encoding="utf-8"))
    return any(
        isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name
        for n in ast.walk(tree)
    )


_LAYOUT_BAND_PRE_Q33 = frozenset({
    "toggle", "slider", "dial", "number", "flonum",
    "rslider", "button", "multislider", "kslider",
    "nslider", "led", "radiogroup", "umenu",
    "live.dial", "live.slider", "live.numbox",
    "live.toggle", "live.button",
})
_PRESENTATION_PRE_Q33 = frozenset({
    "flonum", "number", "umenu", "toggle", "textedit", "kslider",
    "dial", "slider", "multislider", "rslider", "incdec", "tab",
    "pictslider", "matrixctrl", "textbutton",
    "live.dial", "live.slider", "live.numbox", "live.menu",
    "live.toggle", "live.tab", "live.text", "live.button",
})
_PARAMETER_LIST_PRE_Q33 = frozenset({
    "slider", "dial", "rslider", "multislider",
    "number", "flonum", "toggle", "button",
    "kslider", "nslider", "umenu", "textbutton",
    "tab", "gain~", "live.dial", "live.slider",
    "live.numbox", "live.toggle", "live.button",
    "live.menu", "live.tab", "live.gain~",
})


class TestSharedHelpers:
    # -- gain staging --------------------------------------------------------

    def test_gain_staging_vocabulary(self):
        from src.maxpat import gain_staging

        assert gain_staging.OSCILLATOR_NAMES == {
            "cycle~", "saw~", "rect~", "tri~", "noise~", "pink~",
        }
        assert gain_staging.MC_OSCILLATOR_NAMES == {
            "mc.cycle~", "mc.saw~", "mc.rect~", "mc.tri~",
        }

    def test_find_ungained_paths(self):
        from src.maxpat import gain_staging as g

        gains = frozenset({"*~"})
        terms = frozenset({"dac~"})

        def b(text):
            return {"maxclass": "newobj", "text": text}

        lookup = {"o": b("cycle~ 440"), "d": b("dac~")}
        assert g.find_ungained_paths(lookup, {"o": ["d"]}, g.OSCILLATOR_NAMES,
                                     gains, terms) == [("o", "cycle~", "d", "dac~")]

        lookup = {"o": b("cycle~ 440"), "m": b("*~ 0.5"), "d": b("dac~")}
        assert g.find_ungained_paths(lookup, {"o": ["m"], "m": ["d"]},
                                     g.OSCILLATOR_NAMES, gains, terms) == []

        lookup = {"o": b("mc.cycle~ 440"), "d": b("dac~")}
        adj = {"o": ["d"]}
        assert g.find_ungained_paths(lookup, adj, g.OSCILLATOR_NAMES, gains, terms) == []
        assert g.find_ungained_paths(
            lookup, adj, g.OSCILLATOR_NAMES | g.MC_OSCILLATOR_NAMES, gains, terms,
        ) == [("o", "mc.cycle~", "d", "dac~")]

        lookup = {"o": b("cycle~ 440"), "d": b("dac~")}
        assert g.find_ungained_paths(lookup, {"o": ["missing", "d"]},
                                     g.OSCILLATOR_NAMES, gains, terms) == [
            ("o", "cycle~", "d", "dac~")]

    def test_both_layers_delegate(self):
        import inspect

        from src.maxpat import validation
        from src.maxpat.critics import dsp_critic

        assert "find_ungained_paths" in inspect.getsource(validation._check_gain_staging)
        assert "find_ungained_paths" in inspect.getsource(dsp_critic._check_gain_staging)
        assert not _module_assigns("src/maxpat/validation.py", "_OSCILLATOR_NAMES")
        assert not _module_assigns("src/maxpat/critics/dsp_critic.py", "_OSCILLATOR_NAMES")

    # -- geometry ------------------------------------------------------------

    def test_port_geometry(self):
        from src.maxpat import sizing

        d = {"patching_rect": [10, 0, 100, 22], "numoutlets": 3, "numinlets": 3}
        assert sizing.outlet_x(d, 2) == 103.0
        assert sizing.inlet_x(d, 2) == 103.0
        lone = {"patching_rect": [10, 0, 100, 22], "numoutlets": 1, "numinlets": 1}
        assert sizing.outlet_x(lone, 0) == 17.0
        assert sizing.inlet_x(lone, 0) == 17.0
        assert sizing.outlet_x({}, 0) == 7.0
        assert sizing.inlet_x({}, 0) == 7.0

        box = Box.structural("newobj", "x", 3, 3, ["", "", ""], [10, 0, 100, 22],
                             box_id="obj-1")
        for i in range(3):
            assert sizing.outlet_x(box, i) == sizing.outlet_x(d, i)
            assert sizing.inlet_x(box, i) == sizing.inlet_x(d, i)
        lone_box = Box.structural("newobj", "x", 1, 1, [""], [10, 0, 100, 22],
                                  box_id="obj-2")
        assert sizing.outlet_x(lone_box, 0) == 17.0
        assert sizing.inlet_x(lone_box, 0) == 17.0

    def test_one_geometry_site(self):
        from src.maxpat import layout, sizing
        from src.maxpat.critics import layout_critic

        assert layout._outlet_x is sizing.outlet_x
        assert layout._inlet_x is sizing.inlet_x
        assert layout_critic._outlet_x is sizing.outlet_x
        assert layout_critic._inlet_x is sizing.inlet_x
        for rel in ("src/maxpat/layout.py", "src/maxpat/critics/layout_critic.py"):
            assert not _defines_function(rel, "_outlet_x")
            assert not _defines_function(rel, "_inlet_x")
            assert not _module_assigns(rel, "_IO_MARGIN")
        for rel in ("src/maxpat/aesthetics.py", "src/maxpat/critics/layout_critic.py"):
            assert not _defines_function(rel, "_resolve_patcher_bg")

    # -- UI controls ---------------------------------------------------------

    def test_ui_control_names_is_db_derived(self, db):
        from src.maxpat.maxclass_map import UI_MAXCLASSES, ui_control_names

        names = ui_control_names(db)
        assert names <= UI_MAXCLASSES
        for n in ("toggle", "flonum", "number", "live.dial", "gain~", "textedit", "button"):
            assert n in names
        for n in ("comment", "panel", "message", "meter~"):
            assert n not in names

    @pytest.mark.parametrize("attr, pinned", [
        ("LAYOUT_BAND_CONTROLS", _LAYOUT_BAND_PRE_Q33),
        ("PRESENTATION_CONTROLS", _PRESENTATION_PRE_Q33),
        ("PARAMETER_LIST_CONTROLS", _PARAMETER_LIST_PRE_Q33),
    ])
    def test_purpose_sets(self, db, attr, pinned):
        from src.maxpat import maxclass_map

        value = getattr(maxclass_map, attr)
        assert value <= maxclass_map.ui_control_names(db)
        assert value == pinned

    def test_consumers_import_the_sets(self):
        import inspect

        from src.maxpat.patcher import Patcher

        assert not _module_assigns("src/maxpat/layout.py", "_UI_CONTROL_NAMES")
        assert not _module_assigns("src/maxpat/critics/layout_critic.py",
                                   "_INTERACTIVE_MAXCLASSES")
        assert "PARAMETER_LIST_CONTROLS" in inspect.getsource(Patcher._parameter_lines)
