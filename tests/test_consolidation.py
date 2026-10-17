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


# ---------------------------------------------------------------------------
# Task 3: structured CriticResult fields (review S7)
# ---------------------------------------------------------------------------

_RULE_RE = __import__("re").compile(r"^[a-z][a-z0-9_]*$")
_PATCH_FILES = sorted(REPO_ROOT.glob("patches/*/generated/*.maxpat"))


@pytest.fixture(scope="module")
def corpus_reviews(db):
    """(rel, patch_dict, results) per committed generated patch."""
    from src.maxpat.critics import review_patch

    out = []
    for path in _PATCH_FILES:
        with open(path) as f:
            d = json.load(f)
        out.append((path.relative_to(REPO_ROOT).as_posix(), d,
                    review_patch(json.loads(json.dumps(d)), db=db)))
    return out


def _all_box_ids(patch: dict) -> set[str]:
    from src.maxpat import walk

    ids = set()
    for _path, patcher, _ctx in walk.iter_patchers(patch):
        for entry in patcher.get("boxes", []):
            if not isinstance(entry, dict):
                continue
            box = entry.get("box", entry)
            if isinstance(box, dict) and isinstance(box.get("id"), str):
                ids.add(box["id"])
    return ids


class TestCriticResultFields:
    def test_defaults_and_keyword_only(self):
        from src.maxpat.critics.base import CriticResult

        r = CriticResult("note", "f", "s")
        assert r.rule == ""
        assert r.box_ids == ()
        assert r.port is None
        assert r.path == ""
        with pytest.raises(TypeError):
            CriticResult("note", "f", "s", "", "rule")
        assert CriticResult("note", "f", "s", box_ids=["a"]).box_ids == ("a",)

    def test_every_site_names_a_rule(self):
        count = 0
        for path in sorted((REPO_ROOT / "src/maxpat/critics").glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                        and node.func.id == "CriticResult"):
                    continue
                count += 1
                kw = {k.arg: k.value for k in node.keywords}
                assert "rule" in kw, f"{path.name}:{node.lineno} has no rule="
                value = kw["rule"]
                assert isinstance(value, ast.Constant) and isinstance(value.value, str), (
                    f"{path.name}:{node.lineno} rule is not a str literal")
                assert _RULE_RE.match(value.value), f"{path.name}:{node.lineno}"
        assert count >= 49

    def test_corpus_results_are_structured(self, corpus_reviews):
        import re

        assert corpus_reviews
        for rel, d, results in corpus_reviews:
            ids = _all_box_ids(d)
            alternation = "|".join(re.escape(i) for i in sorted(ids, key=len, reverse=True))
            id_re = re.compile(rf"(?<![\w.-])({alternation})(?![\w-])") if ids else None
            for r in results:
                assert r.rule, (rel, r.finding)
                assert isinstance(r.box_ids, tuple), (rel, r.finding)
                for i in r.box_ids:
                    assert isinstance(i, str) and i in ids, (rel, i, r.finding)
                named: list[str] = []
                if id_re is not None:
                    for m in id_re.finditer(r.finding):
                        if m.group(1) not in named:
                            named.append(m.group(1))
                assert named == [i for i in r.box_ids if i in named], (
                    rel, r.rule, r.box_ids, r.finding)
                assert r.port is None or (isinstance(r.port, int)
                                          and not isinstance(r.port, bool)), (rel, r.finding)

    def test_allowlist_rules_carry_ports(self, corpus_reviews, db):
        for rel, _d, results in corpus_reviews:
            for r in results:
                if r.severity == "blocker" and r.rule in (
                    "fan_out_without_trigger", "unsafe_gain_sources",
                ):
                    assert isinstance(r.port, int), (rel, r.finding)

        if db.lookup("bach.score") is None:
            pytest.skip("bach package not in DB")
        from src.maxpat.critics.package_critic import review_packages

        patch = {"patcher": {
            "boxes": [
                {"box": {"id": "obj-1", "maxclass": "newobj", "text": "pack 0 0",
                         "numinlets": 2, "numoutlets": 1, "outlettype": [""]}},
                {"box": {"id": "obj-2", "maxclass": "newobj", "text": "bach.score",
                         "numinlets": 1, "numoutlets": 1, "outlettype": [""]}},
            ],
            "lines": [{"patchline": {"source": ["obj-1", 0],
                                     "destination": ["obj-2", 0]}}],
        }}
        hits = [r for r in review_packages(patch) if r.rule == "bach_llll_types"]
        assert hits
        assert hits[0].box_ids == ("obj-1", "obj-2")
        assert hits[0].port == 0

    def test_allowlist_is_structured(self):
        from src.maxpat.critics.base import CriticResult
        import tests.test_integration_patches as tip

        data = json.loads((REPO_ROOT / "tests/review_blocker_allowlist.json").read_text())
        for entries in data["patches"].values():
            for e in entries:
                assert isinstance(e.get("rule"), str) and e["rule"]
                assert isinstance(e.get("box_ids"), list)
                assert all(isinstance(i, str) for i in e["box_ids"])
                assert "port" in e and (e["port"] is None or isinstance(e["port"], int))
                assert "path" in e
                assert e.get("severity")
                assert e.get("reason")
                for gone in ("kind", "source_id", "outlet", "gain_id", "inlet",
                             "destinations"):
                    assert gone not in e

        tree = ast.parse((REPO_ROOT / "tests/test_integration_patches.py").read_text())
        defined = set()
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                defined.add(node.name)
            elif isinstance(node, ast.Assign):
                defined.update(t.id for t in node.targets if isinstance(t, ast.Name))
        for name in ("_FANOUT_RE", "_BACH_RE", "_UNSAFE_GAIN_RE", "_DST_NAME_RE",
                     "_blocker_match_key", "_entry_key"):
            assert name not in defined, name

        r = CriticResult("blocker", "x", "s", path="p", rule="r", box_ids=("a",), port=1)
        assert tip._result_key(r) == ("r", ("a",), 1, "p")

    def test_q24_helpers_are_structured(self):
        import inspect

        import tests.test_uninitialized_state as tus

        tree = ast.parse((REPO_ROOT / "tests/test_uninitialized_state.py").read_text())
        for node in tree.body:
            if isinstance(node, ast.Assign):
                assert not any(isinstance(t, ast.Name) and t.id == "_ID_RE"
                               for t in node.targets)
        assert "rule" in inspect.getsource(tus._q24)
