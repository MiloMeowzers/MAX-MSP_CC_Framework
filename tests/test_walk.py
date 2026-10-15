"""Tests for src/maxpat/walk.py -- the shared patcher walker (Q19, review S1/S2).

Covers the quote-aware box helpers (box_text / box_tokens / box_name /
box_args / object_name), inner-patcher discovery (``patcher`` and mc.gen~
``data.patcher``), scope / context derivation, path labels, and the walker's
robustness against malformed, very deep and cyclic input.
"""

from __future__ import annotations

import pytest

from src.maxpat import walk
from src.maxpat.db_lookup import GEN_CONTAINER_NAMES


# ---------------------------------------------------------------------------
# Builders (local)
# ---------------------------------------------------------------------------


def _box(box_id, text=None, maxclass="newobj", **extra):
    box = {"id": box_id, "maxclass": maxclass}
    if text is not None:
        box["text"] = text
    box.update(extra)
    return {"box": box}


def _inner(boxes=None, lines=None, **keys):
    d = {"boxes": boxes or [], "lines": lines or []}
    d.update(keys)
    return d


def _container(box_id, text, inner, maxclass="newobj", **extra):
    entry = _box(box_id, text, maxclass=maxclass, **extra)
    entry["box"]["patcher"] = inner
    return entry


def _patch(boxes=None, lines=None, **keys):
    return {"patcher": _inner(boxes, lines, **keys)}


def _ctx(patch, **kw):
    return [(walk.path_ids(p), c) for p, _, c in walk.iter_patchers(patch, **kw)]


# ---------------------------------------------------------------------------
# Tokenizer helpers
# ---------------------------------------------------------------------------


class TestBoxHelpers:
    def test_box_tokens_keep_quoted_groups(self):
        assert walk.box_tokens({"maxclass": "newobj", "text": 't "a b" c'}) == [
            "t", '"a b"', "c",
        ]

    def test_box_args_raw_tokens_after_name(self):
        box = {"maxclass": "newobj", "text": r"expr $f1 \, 2 @foo 1"}
        assert walk.box_args(box) == ["$f1", r"\,", "2", "@foo", "1"]

    def test_box_args_empty_for_non_newobj(self):
        assert walk.box_args({"maxclass": "message", "text": "set 1 2"}) == []

    @pytest.mark.parametrize("text", ["", "   ", None, 5, ["a"]])
    def test_name_and_text_never_raise(self, text):
        box = {"maxclass": "newobj", "text": text}
        assert walk.box_name(box) == ""
        assert walk.box_text(box) == ("" if not isinstance(text, str) else text)
        assert walk.box_args(box) == []
        assert walk.box_tokens(box) == []

    def test_box_text_non_dict_box(self):
        assert walk.box_text(None) == ""
        assert walk.box_name(5) == ""

    def test_box_name_ui_is_maxclass(self):
        assert walk.box_name({"maxclass": "flonum"}) == "flonum"
        assert walk.box_name({"maxclass": ["newobj"]}) == ""

    @pytest.mark.parametrize("mc", ["inlet", "outlet", "patcher", "bpatcher"])
    def test_object_name_structural_none(self, mc):
        assert walk.object_name({"maxclass": mc, "text": "x"}) is None

    def test_object_name_rules(self):
        assert walk.object_name({"maxclass": ["newobj"]}) is None
        assert walk.object_name({"maxclass": "newobj", "text": ""}) is None
        assert walk.object_name({"maxclass": "newobj", "text": "   "}) is None
        assert walk.object_name({"maxclass": "newobj", "text": "cycle~ 440"}) == "cycle~"
        assert walk.object_name({"maxclass": "flonum"}) == "flonum"


class TestInnerPatcher:
    def test_prefers_patcher_over_data(self):
        a, b = _inner(), _inner()
        assert walk.inner_patcher({"patcher": a, "data": {"patcher": b}}) is a

    def test_data_patcher(self):
        b = _inner()
        assert walk.inner_patcher({"maxclass": "newobj", "data": {"patcher": b}}) is b

    @pytest.mark.parametrize("box", [
        {}, {"patcher": []}, {"patcher": "x"}, {"data": []},
        {"data": {"patcher": 3}}, None, 7,
    ])
    def test_non_dict_values_none(self, box):
        assert walk.inner_patcher(box) is None

    @pytest.mark.parametrize("name", sorted(GEN_CONTAINER_NAMES))
    def test_is_gen_container_names(self, name):
        assert walk.is_gen_container({"maxclass": "newobj", "text": f"{name} @x 1"})

    def test_is_gen_container_maxclass_and_p(self):
        assert walk.is_gen_container({"maxclass": "gen~"})
        assert not walk.is_gen_container({"maxclass": "newobj", "text": "p synth"})


class TestLabels:
    def test_newobj_first_positional(self):
        assert walk.box_label({"maxclass": "newobj", "text": "p synth"}) == "p synth"
        assert walk.box_label({"maxclass": "newobj", "text": "poly~ voice 4"}) == "poly~ voice"
        assert walk.box_label({"maxclass": "newobj", "text": "gen~"}) == "gen~"
        assert walk.box_label({"maxclass": "newobj", "text": "mc.gen~ @chans 32"}) == "mc.gen~"

    def test_bpatcher_and_other(self):
        assert walk.box_label({"maxclass": "bpatcher"}) == "bpatcher"
        assert walk.box_label({"maxclass": "bpatcher", "name": "x.maxpat"}) == "bpatcher x.maxpat"
        assert walk.box_label({"maxclass": "gen~"}) == "gen~"
        assert walk.box_label({"maxclass": "newobj", "text": ""}) == "?"
        assert walk.box_label({}) == "?"

    def test_path_ids_and_prefix(self):
        path = (("obj-1", "p synth"), ("obj-2", "gen~"))
        assert walk.path_ids(path) == "obj-1/obj-2"
        assert walk.path_prefix(path) == "[p synth > gen~] "
        assert walk.path_ids(()) == ""
        assert walk.path_prefix(()) == ""

    def test_scope_of(self):
        assert walk.scope_of("gen") == "gen"
        assert walk.scope_of("rnbo") == "rnbo"
        for c in ("max", "poly", "bpatcher"):
            assert walk.scope_of(c) == "max"


# ---------------------------------------------------------------------------
# iter_patchers
# ---------------------------------------------------------------------------


class TestIterPatchers:
    def test_top_first_then_preorder(self):
        d = _patch([
            _container("obj-1", "p a", _inner([
                _container("obj-2", "p b", _inner()),
            ])),
            _container("obj-3", "p c", _inner()),
        ])
        out = list(walk.iter_patchers(d))
        assert out[0][0] == ()
        assert out[0][1] is d["patcher"]
        assert out[0][2] == "max"
        assert [walk.path_ids(p) for p, _, _ in out] == ["", "obj-1", "obj-1/obj-2", "obj-3"]
        assert walk.path_prefix(out[2][0]) == "[p a > p b] "

    def test_contexts(self):
        d = _patch([
            _container("obj-1", "p synth", _inner()),
            _container("obj-2", None, _inner(), maxclass="bpatcher", embed=1),
            _container("obj-3", "poly~ voice 4", _inner()),
            _container("obj-4", "gen~", _inner([
                _container("obj-41", "p sub", _inner()),
            ])),
            _box("obj-5", "mc.gen~ @chans 4", data={"patcher": _inner()}),
            _container("obj-6", "jit.gen", _inner()),
            _container("obj-7", "rnbo~", _inner([
                _container("obj-71", "p r", _inner()),
            ], classnamespace="rnbo")),
        ])
        got = dict(_ctx(d))
        assert got == {
            "": "max",
            "obj-1": "max",
            "obj-2": "bpatcher",
            "obj-3": "poly",
            "obj-4": "gen",
            "obj-4/obj-41": "gen",
            "obj-5": "gen",
            "obj-6": "gen",
            "obj-7": "rnbo",
            "obj-7/obj-71": "rnbo",
        }
        labels = {walk.path_ids(p): p[-1][1] for p, _, _ in walk.iter_patchers(d) if p}
        assert labels["obj-2"] == "bpatcher"
        assert labels["obj-3"] == "poly~ voice"
        assert labels["obj-5"] == "mc.gen~"

    def test_top_context_from_scope_or_detection(self):
        d = _patch([_container("obj-1", "p x", _inner())])
        assert _ctx(d, scope="rnbo") == [("", "rnbo"), ("obj-1", "rnbo")]
        g = _patch([], classnamespace="dsp.gen")
        assert _ctx(g) == [("", "gen")]

    def test_bare_patcher_dict(self):
        inner = _inner([_container("obj-1", "p x", _inner())])
        assert [c for _, c in _ctx(inner)] == ["max", "max"]

    def test_external_not_yielded(self):
        d = _patch([
            _box("obj-1", None, maxclass="bpatcher", name="ext.maxpat"),
            _box("obj-2", "poly~ x 8"),
        ])
        assert _ctx(d) == [("", "max")]

    def test_malformed_never_raises(self):
        d = _patch([
            3,
            None,
            {"box": 5},
            {"box": None},
            {"nobox": 1},
            _container("obj-1", "p a", _inner(boxes=7)),
            _container("obj-2", "p b", _inner(classnamespace=["x"])),
            {"box": {"id": "obj-3", "maxclass": ["newobj"], "patcher": _inner()}},
            {"box": {"id": "obj-4", "maxclass": "newobj", "text": None, "patcher": _inner()}},
        ], classnamespace=["weird"])
        out = _ctx(d)
        assert out[0] == ("", "max")
        assert {p for p, _ in out} == {"", "obj-1", "obj-2", "obj-3", "obj-4"}

    @pytest.mark.parametrize("patch", [None, 5, "x", [], {}, {"patcher": 3}])
    def test_non_patch_yields_nothing(self, patch):
        assert list(walk.iter_patchers(patch)) == []

    def test_deep_chain_no_recursion_error(self):
        leaf = _inner()
        cur = leaf
        for i in range(1500, 0, -1):
            cur = _inner([_container(f"obj-{i}", f"p d{i}", cur)])
        d = {"patcher": cur}
        n = 0
        for _ in walk.iter_patchers(d):
            n += 1
        assert n == 1501

    def test_cyclic_dict_terminates(self):
        top = _inner()
        top["boxes"].append(_container("obj-1", "p loop", top))
        d = {"patcher": top}
        out = list(walk.iter_patchers(d))
        assert len(out) == 1

    def test_pure(self):
        import copy

        d = _patch([_container("obj-1", "p a", _inner([_box("obj-2", "cycle~")]))])
        before = copy.deepcopy(d)
        list(walk.iter_patchers(d))
        assert d == before


# ---------------------------------------------------------------------------
# One name extractor (Q19 / S2)
# ---------------------------------------------------------------------------


class TestDedupe:
    def test_validation_extractors_gone(self):
        from src.maxpat import validation

        assert not hasattr(validation, "_get_box_name")
        assert not hasattr(validation, "_extract_object_name")

    def test_rnbo_validation_extractor_gone(self):
        from src.maxpat import rnbo_validation

        assert not hasattr(rnbo_validation, "_extract_object_name")

    @pytest.mark.parametrize("module", ["validation", "rnbo_validation"])
    def test_no_bare_split_in_validators(self, module):
        import re
        from pathlib import Path

        src = (Path(__file__).resolve().parent.parent / "src" / "maxpat" / f"{module}.py").read_text()
        assert re.findall(r"\.split\(\s*\)", src) == []
