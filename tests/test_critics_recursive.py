"""Recursive, path-tagged critics on one shared graph (Q20; review A7, S1, G9, G10).

review_patch builds one :class:`src.maxpat.graph.PatchGraph` per call from
``walk.iter_patchers`` and hands it to every critic. Each critic reviews
every scope; nested findings carry ``CriticResult.path`` (the box-id chain,
``obj-1/obj-2``) and a ``[label > label] `` finding prefix, while top-level
findings keep ``path == ""`` and byte-identical text.

Saves run inside a throwaway git repo under ``tmp_path`` (fixture and
helpers copied from tests/test_validation_recursive.py, not imported).
"""

from __future__ import annotations

import copy
import shutil
import subprocess
from pathlib import Path

import pytest

from src.maxpat import walk
from src.maxpat.critics import review_patch
from src.maxpat.critics.base import CriticResult
from src.maxpat.critics.structure_critic import review_structure
from src.maxpat.db_lookup import ObjectDatabase
from src.maxpat.graph import PatchGraph, outlet_is_signal
from src.maxpat.patcher import Patcher


@pytest.fixture(scope="module")
def db():
    return ObjectDatabase()


# ---------------------------------------------------------------------------
# Builders (local, in the style of tests/test_validation_recursive.py)
# ---------------------------------------------------------------------------


def _box(box_id, text, n_in=1, n_out=1, maxclass="newobj", outlettype=None, **extra):
    box = {
        "id": box_id,
        "maxclass": maxclass,
        "numinlets": n_in,
        "numoutlets": n_out,
        "outlettype": outlettype if outlettype is not None else [""] * n_out,
        "patching_rect": [10.0, 10.0, 80.0, 22.0],
    }
    if text is not None:
        box["text"] = text
    box.update(extra)
    return {"box": box}


def _line(src, outlet, dst, inlet):
    return {"patchline": {"source": [src, outlet], "destination": [dst, inlet]}}


def _inner(boxes=None, lines=None, **keys):
    d = {"boxes": boxes if boxes is not None else [], "lines": lines if lines is not None else []}
    d.update(keys)
    return d


def _container(box_id, text, inner, n_in=1, n_out=1, maxclass="newobj", **extra):
    entry = _box(box_id, text, n_in=n_in, n_out=n_out, maxclass=maxclass, **extra)
    entry["box"]["patcher"] = inner
    return entry


def _patch(boxes=None, lines=None, **keys):
    return {"patcher": _inner(boxes, lines, **keys)}


def _wrap(boxes, lines, label="p synth", box_id="obj-1"):
    """*boxes*/*lines* wrapped inside one subpatcher box."""
    return _patch([_container(box_id, label, _inner(boxes, lines))])


def _sig(results):
    return [(r.severity, r.finding, r.suggestion, r.path) for r in results]


def _gen_inner(boxes, lines=None):
    return _inner(boxes, lines, classnamespace="dsp.gen")


# --- shared content ---------------------------------------------------------


def _reconverge_content():
    """button obj-2 outlet 0 -> pack 0 0 obj-3 inlets 0 and 1 (blocker)."""
    boxes = [
        _box("obj-2", "button", 1, 1, maxclass="button", outlettype=["bang"]),
        _box("obj-3", "pack 0 0", 2, 1, outlettype=["list"]),
    ]
    lines = [_line("obj-2", 0, "obj-3", 0), _line("obj-2", 0, "obj-3", 1)]
    return boxes, lines


def _fanout_warning_content():
    """button -> two independent prints with outgoing cords (warning)."""
    boxes = [
        _box("obj-2", "button", 1, 1, maxclass="button", outlettype=["bang"]),
        _box("obj-3", "+ 1", 2, 1, outlettype=["int"]),
        _box("obj-4", "+ 2", 2, 1, outlettype=["int"]),
        _box("obj-5", "print a", 1, 0, outlettype=[]),
        _box("obj-6", "print b", 1, 0, outlettype=[]),
    ]
    lines = [
        _line("obj-2", 0, "obj-3", 0),
        _line("obj-2", 0, "obj-4", 0),
        _line("obj-3", 0, "obj-5", 0),
        _line("obj-4", 0, "obj-6", 0),
    ]
    return boxes, lines


def _hot_cold_content():
    """Two separate number boxes into + inlets 0 and 1 (warning)."""
    boxes = [
        _box("obj-2", None, 1, 2, maxclass="number", outlettype=["", "bang"]),
        _box("obj-3", None, 1, 2, maxclass="number", outlettype=["", "bang"]),
        _box("obj-4", "+", 2, 1, outlettype=["int"]),
    ]
    lines = [_line("obj-2", 0, "obj-4", 0), _line("obj-3", 0, "obj-4", 1)]
    return boxes, lines


def _duplicate_content():
    boxes = [
        _box("obj-2", "loadbang", 1, 1, outlettype=["bang"]),
        _box("obj-3", "print", 1, 0, outlettype=[]),
    ]
    lines = [_line("obj-2", 0, "obj-3", 0), _line("obj-2", 0, "obj-3", 0)]
    return boxes, lines


# ---------------------------------------------------------------------------
# TestPatchGraph
# ---------------------------------------------------------------------------


class TestPatchGraph:
    def _nested(self):
        gen = _container("obj-2", "gen~", _gen_inner([_box("obj-20", "in 1")]))
        mcgen = _box("obj-3", "mc.gen~", 1, 1)
        mcgen["box"]["data"] = {"patcher": _gen_inner([_box("obj-30", "out 1")])}
        bp = _container("obj-4", None, _inner([_box("obj-40", "print")]), maxclass="bpatcher")
        rnbo = _container("obj-5", "rnbo~", _inner([_box("obj-50", "in~ 1")], classnamespace="rnbo"))
        p = _container("obj-1", "p synth", _inner([_box("obj-10", "cycle~ 440")]))
        return _patch([p, gen, mcgen, bp, rnbo])

    def test_scopes_follow_walker(self):
        d = self._nested()
        g = PatchGraph.build(d)
        walked = list(walk.iter_patchers(d))
        assert [s.path for s in g.scopes] == [p for p, _, _ in walked]
        assert [s.context for s in g.scopes] == [c for _, _, c in walked]
        assert [s.key for s in g.scopes] == [walk.path_ids(p) for p, _, _ in walked]
        assert [s.prefix for s in g.scopes] == [walk.path_prefix(p) for p, _, _ in walked]
        assert [s.scope for s in g.scopes] == [walk.scope_of(c) for _, _, c in walked]
        assert g.top is g.scopes[0]
        assert g.top.path == ()
        contexts = {s.key: s.context for s in g.scopes}
        assert contexts["obj-1"] == "max"
        assert contexts["obj-2"] == "gen"
        assert contexts["obj-3"] == "gen"
        assert contexts["obj-4"] == "bpatcher"
        assert contexts["obj-5"] == "rnbo"

    @pytest.mark.parametrize("d", [{}, {"patcher": {}}, None, {"patcher": 5}])
    def test_degenerate_gives_one_empty_top(self, d):
        g = PatchGraph.build(d)
        assert len(g.scopes) == 1
        top = g.top
        assert top.path == () and top.key == "" and top.prefix == ""
        assert top.boxes == {} and top.box_list == [] and top.edges == []

    def test_duplicate_ids_first_position_last_box(self):
        d = _patch([
            _box("obj-1", "print a"),
            _box("obj-2", "print b"),
            _box("obj-1", "print c"),
        ])
        s = PatchGraph.build(d).top
        assert list(s.boxes) == ["obj-1", "obj-2"]
        assert s.boxes["obj-1"]["text"] == "print c"
        assert [b["text"] for b in s.box_list] == ["print a", "print b", "print c"]

    def test_bare_box_and_bare_patchline_entries(self):
        d = {"patcher": {
            "boxes": [
                {"id": "obj-1", "maxclass": "newobj", "text": "loadbang", "outlettype": ["bang"]},
                _box("obj-2", "print"),
            ],
            "lines": [{"source": ["obj-1", 0], "destination": ["obj-2", 0]}],
        }}
        s = PatchGraph.build(d).top
        assert set(s.boxes) == {"obj-1", "obj-2"}
        assert [(e.src, e.outlet, e.dst, e.inlet) for e in s.edges] == [("obj-1", 0, "obj-2", 0)]

    def test_malformed_cords_skipped(self):
        bad = [
            {"patchline": {"source": None, "destination": ["obj-2", 0]}},
            {"patchline": {"source": ["obj-1"], "destination": ["obj-2", 0]}},
            {"patchline": {"source": "obj-1", "destination": ["obj-2", 0]}},
            {"patchline": {"source": [["obj-1"], 0], "destination": ["obj-2", 0]}},
            {"patchline": {"source": ["obj-1", "0"], "destination": ["obj-2", 0]}},
            {"patchline": {"source": ["obj-1", 0.0], "destination": ["obj-2", 0]}},
            {"patchline": {"source": ["obj-1", True], "destination": ["obj-2", 0]}},
            {"patchline": {"source": ["obj-1", 0], "destination": ["obj-2", None]}},
            "not a line",
            None,
            {"patchline": 7},
        ]
        good = _line("obj-1", 0, "obj-2", 0)
        d = _patch([_box("obj-1", "loadbang"), _box("obj-2", "print")], bad + [good])
        s = PatchGraph.build(d).top
        assert [(e.src, e.outlet, e.dst, e.inlet) for e in s.edges] == [("obj-1", 0, "obj-2", 0)]
        assert [e.dst for e in s.out_edges["obj-1"]] == ["obj-2"]
        assert [e.src for e in s.in_edges["obj-2"]] == ["obj-1"]

    def test_edge_signal_follows_outlettype(self):
        d = _patch(
            [
                _box("obj-1", "mc.cycle~ 440", 2, 1, outlettype=["multichannelsignal"]),
                _box("obj-2", "snapshot~", 2, 1, outlettype=["float"]),
                _box("obj-3", "cycle~ 440", 2, 1, outlettype=[]),
                _box("obj-4", "print", 1, 0, outlettype=[]),
            ],
            [
                _line("obj-1", 0, "obj-4", 0),
                _line("obj-2", 0, "obj-4", 0),
                _line("obj-3", 0, "obj-4", 0),
            ],
        )
        s = PatchGraph.build(d).top
        assert [e.signal for e in s.edges] == [True, False, True]
        assert outlet_is_signal(s.boxes["obj-2"], 0) is False
        assert outlet_is_signal(None, 0) is False

    def test_children_and_subtree(self):
        inner_b = _container("obj-11", "p b", _inner([_box("obj-12", "print")]))
        a = _container("obj-1", "p a", _inner([inner_b]))
        other = _container("obj-2", "p c", _inner([]))
        g = PatchGraph.build(_patch([a, other]))
        top = g.top
        assert [s.key for s in g.children(top)] == ["obj-1", "obj-2"]
        assert [s.key for s in g.subtree(top, "obj-1")] == ["obj-1", "obj-1/obj-11"]
        assert [s.key for s in g.subtree(top, "obj-2")] == ["obj-2"]
        assert g.subtree(top, "obj-99") == []
        child = g.children(top)[0]
        assert child.parent is top and child.container == "obj-1"

    def test_build_is_pure(self):
        d = TestPatchGraph()._nested()
        d["patcher"]["lines"].append(_line("obj-1", 0, "obj-2", 0))
        before = copy.deepcopy(d)
        PatchGraph.build(d)
        assert d == before


# ---------------------------------------------------------------------------
# TestStructureNested
# ---------------------------------------------------------------------------


_PARITY_CONTENT = {
    "fanout_reconverge": _reconverge_content,
    "fanout_warning": _fanout_warning_content,
    "hot_cold": _hot_cold_content,
    "duplicate": _duplicate_content,
}


class TestStructureNested:
    def test_reconvergence_in_p_synth_is_blocker_with_path(self):
        boxes, lines = _reconverge_content()
        results = review_structure(_wrap(boxes, lines))
        blockers = [r for r in results if r.severity == "blocker"]
        assert len(blockers) == 1
        assert blockers[0].path == "obj-1"
        assert blockers[0].finding.startswith(
            "[p synth] Fan-out without trigger: 'button' (obj-2) outlet 0"
        )

    def test_two_level_nest(self):
        boxes, lines = _reconverge_content()
        inner_b = _container("obj-2", "p b", _inner(boxes, lines))
        d = _patch([_container("obj-1", "p a", _inner([inner_b]))])
        blockers = [r for r in review_structure(d) if r.severity == "blocker"]
        assert len(blockers) == 1
        assert blockers[0].path == "obj-1/obj-2"
        assert blockers[0].finding.startswith("[p a > p b] Fan-out without trigger: ")

    def test_gen_scope_skips_ordering(self):
        rb, rl = _reconverge_content()
        hb, hl = _hot_cold_content()
        hb = [copy.deepcopy(b) for b in hb]
        for b in hb:
            b["box"]["id"] = b["box"]["id"].replace("obj-", "obj-1")
        hl = [_line("obj-12", 0, "obj-14", 0), _line("obj-13", 0, "obj-14", 1)]
        content_boxes = rb + hb
        content_lines = rl + hl
        assert review_structure(_patch(copy.deepcopy(content_boxes), copy.deepcopy(content_lines)))
        nested = _patch([_container("obj-1", "gen~", _gen_inner(content_boxes, content_lines))])
        assert review_structure(nested) == []
        top_gen = {"patcher": _gen_inner(copy.deepcopy(content_boxes), copy.deepcopy(content_lines))}
        assert review_structure(top_gen) == []

    def test_gen_scope_still_reports_duplicates(self):
        boxes, lines = _duplicate_content()
        d = _patch([_container("obj-1", "gen~", _gen_inner(boxes, lines))])
        results = review_structure(d)
        assert len(results) == 1
        assert results[0].path == "obj-1"
        assert results[0].finding.startswith("[gen~] Duplicate patchline: ")

    def test_top_level_first_then_preorder(self):
        rb, rl = _reconverge_content()
        db_, dl = _duplicate_content()
        a = _container("obj-10", "p a", _inner(copy.deepcopy(rb), copy.deepcopy(rl)))
        b = _container("obj-11", "p b", _inner(copy.deepcopy(db_), copy.deepcopy(dl)))
        top_boxes = copy.deepcopy(db_) + [a, b]
        d = _patch(top_boxes, copy.deepcopy(dl))
        paths = [r.path for r in review_structure(d)]
        # obj-10: fan-out blocker + hot/cold warning on the pack
        assert paths == ["", "obj-10", "obj-10", "obj-11"]


# ---------------------------------------------------------------------------
# TestJitterSetter
# ---------------------------------------------------------------------------


def _terrain_view(second="exprfill 0 snorm[1]", first="exprfill 0 snorm[0]"):
    """loadbang fans out to two exprfill messages -> jit.matrix -> jit.pack."""
    boxes = [
        _box("obj-10", "loadbang", 1, 1, outlettype=["bang"]),
        _box("obj-11", first, 2, 1, maxclass="message", outlettype=[""]),
        _box("obj-12", second, 2, 1, maxclass="message", outlettype=[""]),
        _box("obj-13", "jit.matrix 1 float32 64 64", 1, 2, outlettype=["jit_matrix", ""]),
        _box("obj-14", "jit.matrix 1 float32 64 64", 1, 2, outlettype=["jit_matrix", ""]),
        _box("obj-19", "jit.pack 3", 3, 2, outlettype=["jit_matrix", ""]),
    ]
    lines = [
        _line("obj-10", 0, "obj-11", 0),
        _line("obj-10", 0, "obj-12", 0),
        _line("obj-11", 0, "obj-13", 0),
        _line("obj-12", 0, "obj-14", 0),
        _line("obj-13", 0, "obj-19", 0),
        _line("obj-14", 0, "obj-19", 2),
    ]
    return boxes, lines


def _fan(results):
    return [r for r in results if "Fan-out without trigger" in r.finding]


class TestJitterSetter:
    def test_terrain_view_is_warning(self):
        boxes, lines = _terrain_view()
        for d in (_patch(copy.deepcopy(boxes), copy.deepcopy(lines)), _wrap(boxes, lines)):
            fan = _fan(review_structure(d))
            assert len(fan) == 1
            assert fan[0].severity == "warning"
            assert fan[0].finding.endswith("execution order is undefined")

    def test_bang_segment_still_propagates(self):
        boxes, lines = _terrain_view(
            first="exprfill 0 snorm[0], bang", second="exprfill 0 snorm[1], bang"
        )
        fan = _fan(review_structure(_patch(boxes, lines)))
        assert [r.severity for r in fan] == ["blocker"]

    def test_setter_as_fanout_source(self):
        boxes = [
            _box("obj-11", "exprfill 0 snorm[0]", 2, 1, maxclass="message", outlettype=[""]),
            _box("obj-13", "jit.matrix 1 float32 64 64", 1, 2, outlettype=["jit_matrix", ""]),
            _box("obj-14", "jit.matrix 1 float32 64 64", 1, 2, outlettype=["jit_matrix", ""]),
            _box("obj-19", "jit.pack 3", 3, 2, outlettype=["jit_matrix", ""]),
        ]
        lines = [
            _line("obj-11", 0, "obj-13", 0),
            _line("obj-11", 0, "obj-14", 0),
            _line("obj-13", 0, "obj-19", 0),
            _line("obj-14", 0, "obj-19", 2),
        ]
        fan = _fan(review_structure(_patch(boxes, lines)))
        assert len(fan) == 1 and fan[0].severity == "warning"

    @pytest.mark.parametrize("text", ["getdim", "$1 $1", "5 5"])
    def test_non_setter_messages_propagate(self, text):
        boxes, lines = _terrain_view(first=text, second=text)
        fan = _fan(review_structure(_patch(boxes, lines)))
        assert [r.severity for r in fan] == ["blocker"]


# ---------------------------------------------------------------------------
# TestReviewPatchSharedGraph
# ---------------------------------------------------------------------------


def _count_builds(monkeypatch):
    calls = []
    real = PatchGraph.build.__func__

    def spy(cls, *args, **kwargs):
        calls.append(1)
        return real(cls, *args, **kwargs)

    monkeypatch.setattr(PatchGraph, "build", classmethod(spy))
    return calls


class TestReviewPatchSharedGraph:
    def test_one_graph_per_review_patch(self, monkeypatch, db):
        calls = _count_builds(monkeypatch)
        boxes, lines = _reconverge_content()
        review_patch(_wrap(boxes, lines), db=db)
        assert len(calls) == 1

    def test_structure_with_graph_builds_none(self, monkeypatch):
        boxes, lines = _reconverge_content()
        d = _wrap(boxes, lines)
        g = PatchGraph.build(d)
        calls = _count_builds(monkeypatch)
        results = review_structure(d, graph=g)
        assert calls == []
        assert [r.path for r in results if r.severity == "blocker"] == ["obj-1"]

    def test_at_most_one_db(self, monkeypatch):
        import src.maxpat.db_lookup as db_lookup

        made = []
        real = db_lookup.ObjectDatabase

        class Spy(real):
            def __init__(self, *a, **k):
                made.append(1)
                super().__init__(*a, **k)

        monkeypatch.setattr(db_lookup, "ObjectDatabase", Spy)
        import src.maxpat.critics.package_critic as pc
        monkeypatch.setattr(pc, "ObjectDatabase", Spy)
        boxes, lines = _reconverge_content()
        review_patch(_wrap(boxes, lines))
        assert len(made) <= 1

    def test_review_patch_is_pure(self, db):
        boxes, lines = _reconverge_content()
        d = _wrap(boxes, lines)
        before = copy.deepcopy(d)
        review_patch(d, db=db)
        assert d == before


# ---------------------------------------------------------------------------
# Save gate: a nested critic blocker refuses a new file
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolate_git_env(monkeypatch):
    """Make sure no inherited git env var can redirect git to another repo."""
    for var in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        monkeypatch.delenv(var, raising=False)


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=str(root), capture_output=True, text=True, check=True,
    )
    return result.stdout


def _repo(tmp_path: Path) -> Path:
    """Create a throwaway git repo at tmp_path/repo and return its resolved root."""
    root = tmp_path / "repo"
    root.mkdir()
    hooks = tmp_path / "empty-hooks"
    hooks.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Save Gate Test")
    _git(root, "config", "commit.gpgsign", "false")
    _git(root, "config", "core.hooksPath", str(hooks))
    return root.resolve()


def _p_synth_reconverge():
    boxes, lines = _reconverge_content()
    return _container("obj-1", "p synth", _inner(boxes, lines))


@pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")
class TestSaveGateNestedCritic:
    def test_new_file_with_nested_fanout_refused(self, tmp_path):
        from src.maxpat.hooks import PatchValidationError, save_patch_roundtrip

        root = _repo(tmp_path)
        P = root / "patches" / "demo" / "generated" / "demo.maxpat"
        d = Patcher().to_dict()
        d["patcher"]["boxes"].append(_p_synth_reconverge())

        with pytest.raises(PatchValidationError) as excinfo:
            save_patch_roundtrip(d, P)

        cfind = [
            f for f in excinfo.value.findings
            if isinstance(f, CriticResult) and f.path == "obj-1"
        ]
        assert cfind, excinfo.value.findings
        assert cfind[0].finding.startswith("[p synth] Fan-out without trigger: ")
        assert not P.exists()

    def test_moved_nested_blocker_is_new(self):
        from src.maxpat.hooks import _gate_report

        def voice(box_id, with_blocker):
            if with_blocker:
                boxes, lines = _reconverge_content()
            else:
                boxes, lines = _reconverge_content()
                lines = lines[:1]
            return _container(box_id, "p voice", _inner(boxes, lines))

        baseline = _patch([voice("obj-1", True), voice("obj-2", False)])
        new = _patch([voice("obj-1", False), voice("obj-2", True)])
        report = _gate_report(new, baseline, [])
        assert len(report.new_blockers) == 1, report.new_blockers
        crit = [r for r in report.new_blockers if isinstance(r, CriticResult)]
        assert len(crit) == 1
        assert crit[0].path == "obj-2"


# ===========================================================================
# Task 2: dsp, package, rnbo, m4l and layout critics on the shared graph
# ===========================================================================

from src.maxpat.critics import (  # noqa: E402
    _has_package_boxes,
    _has_rnbo_boxes,
    review_dsp,
    review_layout,
    review_m4l,
    review_packages,
    review_rnbo,
)
from src.maxpat.critics.m4l_critic import detect_m4l_device_type  # noqa: E402


def _plugout(box_id="obj-90"):
    return _box(box_id, "plugout~", 2, 0, outlettype=[])


def _codebox_gen(n_in_code=2):
    """gen patcher whose wired codebox uses in1..in<n>."""
    code = "out1 = " + " + ".join(f"in{i}" for i in range(1, n_in_code + 1)) + ";"
    boxes = [
        _box("obj-20", None, n_in_code, 1, maxclass="codebox", code=code),
        _box("obj-21", "out 1", 1, 0, outlettype=[]),
    ]
    return _gen_inner(boxes, [_line("obj-20", 0, "obj-21", 0)])


# --- parity content: (boxes, lines, patcher_keys) ---------------------------


def _c_dsp_gain():
    return ([
        _box("obj-2", "cycle~ 440", 2, 1, outlettype=["signal"]),
        _box("obj-3", "dac~", 2, 0, outlettype=[]),
    ], [_line("obj-2", 0, "obj-3", 0)], {})


def _c_dsp_unsafe():
    return ([
        _box("obj-2", None, 1, 1, maxclass="slider", outlettype=[""]),
        _box("obj-3", "cycle~ 440", 2, 1, outlettype=["signal"]),
        _box("obj-4", "*~", 2, 1, outlettype=["signal"]),
    ], [_line("obj-3", 0, "obj-4", 0), _line("obj-2", 0, "obj-4", 1)], {})


def _c_dsp_gen_io():
    return ([_container("obj-2", "gen~", _codebox_gen(2), 1, 1, outlettype=["signal"])], [], {})


def _c_bach():
    return ([
        _box("obj-2", "pack 0 0", 2, 1, outlettype=[""]),
        _box("obj-3", "bach.score", 1, 1, outlettype=[""]),
    ], [_line("obj-2", 0, "obj-3", 0)], {})


def _c_ezdac():
    return ([_box("obj-2", "ezdac~", 2, 0, maxclass="ezdac~", outlettype=[])], [], {})


def _c_live_dial():
    return ([_box("obj-2", None, 1, 2, maxclass="live.dial", outlettype=["", "float"])], [], {})


def _c_overlap():
    return ([_box("obj-2", "print a", 1, 0, outlettype=[]),
             _box("obj-3", "print b", 1, 0, outlettype=[])], [], {})


def _c_midpoints():
    a = _box("obj-2", "loadbang", 1, 1, outlettype=["bang"])
    b = _box("obj-3", "print", 1, 0, outlettype=[])
    b["box"]["patching_rect"] = [400.0, 100.0, 60.0, 22.0]
    return [a, b], [_line("obj-2", 0, "obj-3", 0)], {}


def _c_out_of_bounds():
    a = _box("obj-2", "print", 1, 0, outlettype=[])
    a["box"]["patching_rect"] = [-20.0, 10.0, 60.0, 22.0]
    return [a], [], {}


def _c_low_contrast():
    c = _box("obj-2", "a label", 1, 0, maxclass="comment", outlettype=[],
             textcolor=[0.9, 0.9, 0.9, 1.0])
    c["box"]["patching_rect"] = [10.0, 200.0, 80.0, 20.0]
    return [c], [], {"bgcolor": [1.0, 1.0, 1.0, 1.0]}


def _c_low_contrast_fallback():
    c = _box("obj-2", "a label", 1, 0, maxclass="comment", outlettype=[],
             textcolor=[0.3, 0.3, 0.3, 1.0])
    c["box"]["patching_rect"] = [10.0, 200.0, 80.0, 20.0]
    return [c], [], {}


def _c_presentation():
    c = _box("obj-2", "title", 1, 0, maxclass="comment", outlettype=[],
             presentation=1, presentation_rect=[0.0, 0.0, 50.0, 20.0])
    c["box"]["patching_rect"] = [10.0, 200.0, 80.0, 20.0]
    t = _box("obj-3", None, 1, 1, maxclass="toggle", outlettype=["int"])
    t["box"]["patching_rect"] = [200.0, 200.0, 24.0, 24.0]
    return [c, t], [], {}


def _m(text):
    return lambda r: text in r.finding


def _run_structure(d, db):
    return review_structure(d)


def _run_dsp(d, db):
    return review_dsp(d)


def _run_packages(d, db):
    return review_packages(d, db=db)


def _run_m4l(d, db):
    return review_m4l(d, device_type="instrument")


def _run_layout(d, db):
    return review_layout(d)


def _structure_case(fn):
    def content():
        boxes, lines = fn()
        return boxes, lines, {}
    return content


# name -> (content, run, match, top_extra boxes factory)
_PARITY_CASES = {
    "structure_fanout_reconverge": (_structure_case(_reconverge_content), _run_structure, _m(""), None),
    "structure_fanout_warning": (_structure_case(_fanout_warning_content), _run_structure, _m(""), None),
    "structure_hot_cold": (_structure_case(_hot_cold_content), _run_structure, _m(""), None),
    "structure_duplicate": (_structure_case(_duplicate_content), _run_structure, _m(""), None),
    "dsp_missing_gain": (_c_dsp_gain, _run_dsp, _m("Missing gain staging"), None),
    "dsp_unsafe_gain_source": (_c_dsp_unsafe, _run_dsp, _m("Unsafe gain source"), None),
    "dsp_gen_io_mismatch": (_c_dsp_gen_io, _run_dsp, _m("gen~ I/O"), None),
    "package_bach_llll": (_c_bach, _run_packages, _m("Bach llll"), None),
    "m4l_ezdac": (_c_ezdac, _run_m4l, _m("ezdac~ ("), _plugout),
    "m4l_parameter_enable": (_c_live_dial, _run_m4l, _m("missing parameter_enable"), _plugout),
    "layout_overlap": (_c_overlap, _run_layout, _m("Overlapping boxes"), None),
    "layout_midpoints": (_c_midpoints, _run_layout, _m("Missing midpoints"), None),
    "layout_out_of_bounds": (_c_out_of_bounds, _run_layout, _m("Out-of-bounds"), None),
    "layout_low_contrast": (_c_low_contrast, _run_layout, _m("Low contrast"), None),
    "layout_low_contrast_fallback": (_c_low_contrast_fallback, _run_layout, _m("Low contrast"), None),
    "layout_presentation_coverage": (_c_presentation, _run_layout, _m("Presentation coverage"), None),
}


@pytest.mark.parametrize("name", sorted(_PARITY_CASES))
def test_nested_parity_with_top_level(name, db):
    """Content wrapped in ``p synth`` gives exactly its top-level findings,
    prefixed ``[p synth] `` with path ``obj-1`` (A7 invariant, Q20)."""
    content, run, match, extra = _PARITY_CASES[name]
    if name == "package_bach_llll" and db.lookup("bach.score") is None:
        pytest.skip("bach is not in the repo DB")
    boxes, lines, keys = content()
    top_boxes = copy.deepcopy(boxes) + ([extra()] if extra else [])
    top = [r for r in run(_patch(top_boxes, copy.deepcopy(lines), **keys), db) if match(r)]
    assert top, name
    assert all(r.path == "" for r in top)

    nested_top = [extra()] if extra else []
    nested_dict = _patch(nested_top + [_container("obj-1", "p synth", _inner(boxes, lines, **keys))])
    nested = [r for r in run(nested_dict, db) if match(r) and r.path == "obj-1"]
    assert _sig(nested) == [
        (r.severity, "[p synth] " + r.finding, r.suggestion, "obj-1") for r in top
    ]


# ---------------------------------------------------------------------------
# DSP
# ---------------------------------------------------------------------------


class TestDspNested:
    def test_nested_gen_io_mismatch(self):
        boxes, lines, _ = _c_dsp_gen_io()
        results = review_dsp(_wrap(boxes, lines))
        blockers = [r for r in results if r.severity == "blocker"]
        assert [r.path for r in blockers] == ["obj-1"]
        assert blockers[0].finding.startswith("[p synth] gen~ I/O input mismatch")

    def test_code_context_applies_to_top_scope_only(self):
        ctx = {"gen~_code": {"obj-2": "out1 = in1 + in2;"}}
        top = _patch([_box("obj-2", "gen~", 1, 1, outlettype=["signal"])])
        assert [r.path for r in review_dsp(top, code_context=ctx)] == [""]
        nested = _wrap([_box("obj-2", "gen~", 1, 1, outlettype=["signal"])], [])
        assert review_dsp(nested, code_context=ctx) == []

    def test_no_finding_from_gen_scope(self):
        gen = _gen_inner([
            _box("obj-20", "cycle~ 440", 2, 1, outlettype=["signal"]),
            _box("obj-21", "dac~", 2, 0, outlettype=[]),
        ], [_line("obj-20", 0, "obj-21", 0)])
        d = _patch([_container("obj-1", "gen~", gen, 1, 1, outlettype=["signal"])])
        assert review_dsp(d) == []


# ---------------------------------------------------------------------------
# Package
# ---------------------------------------------------------------------------


def _unextract_flucoma(db, monkeypatch):
    info = db.get_package_info("FluCoMa")
    if not info:
        pytest.skip("FluCoMa package info not in the repo DB")
    patched = dict(info)
    patched["extracted"] = False
    monkeypatch.setitem(db._package_info, "FluCoMa", patched)


def _fluid(box_id):
    return _box(box_id, "fluid.mfcc~ 13", 1, 1, outlettype=[""])


def _unextracted(results):
    return [r for r in results if "Unextracted community package" in r.finding]


class TestPackageNested:
    def test_unextracted_top_and_nested_warns_once_at_top(self, db, monkeypatch):
        _unextract_flucoma(db, monkeypatch)
        d = _patch([_fluid("obj-2"), _container("obj-1", "p synth", _inner([_fluid("obj-3")]))])
        hits = _unextracted(review_packages(d, db=db))
        assert [r.path for r in hits] == [""]

    def test_unextracted_nested_only_warns_once_with_path(self, db, monkeypatch):
        _unextract_flucoma(db, monkeypatch)
        d = _patch([
            _container("obj-1", "p a", _inner([_fluid("obj-3")])),
            _container("obj-2", "p b", _inner([_fluid("obj-3")])),
        ])
        hits = _unextracted(review_packages(d, db=db))
        assert [r.path for r in hits] == ["obj-1"]
        assert hits[0].finding.startswith("[p a] Unextracted community package")

    def test_install_state_false_once_at_first_scope(self, db, monkeypatch):
        monkeypatch.setattr(db, "get_install_state", lambda name: False if name == "print" else None)
        d = _patch([
            _container("obj-1", "p a", _inner([_box("obj-3", "print", 1, 0, outlettype=[])])),
            _container("obj-2", "p b", _inner([_box("obj-3", "print", 1, 0, outlettype=[])])),
        ])
        hits = [r for r in review_packages(d, db=db) if "Object not installed" in r.finding]
        assert [(r.severity, r.path) for r in hits] == [("blocker", "obj-1")]

    def test_has_package_boxes_nested_only(self, db):
        if not db.get_package("fluid.mfcc~"):
            pytest.skip("fluid.mfcc~ has no package in the repo DB")
        d = _wrap([_fluid("obj-3")], [])
        assert _has_package_boxes(d, db=db) is True
        assert _has_package_boxes(_patch([]), db=db) is False

    def test_beap_chain_in_p_reviewed_with_path(self, db):
        osc = {"box": {"id": "obj-2", "maxclass": "bpatcher", "name": "bp.Oscillator",
                       "numinlets": 1, "numoutlets": 1, "outlettype": ["signal"]}}
        out = {"box": {"id": "obj-3", "maxclass": "bpatcher", "name": "bp.Stereo",
                       "numinlets": 2, "numoutlets": 0, "outlettype": []}}
        if db.get_package("bp.Oscillator") != "BEAP":
            pytest.skip("BEAP not in the repo DB")
        d = _wrap([osc, out], [_line("obj-2", 0, "obj-3", 0)])
        vca = [r for r in review_packages(d, db=db) if "BEAP missing VCA" in r.finding]
        assert [r.path for r in vca] == ["obj-1"]
        assert vca[0].finding.startswith("[p synth] BEAP missing VCA: 'bp.Oscillator' (obj-2)")


# ---------------------------------------------------------------------------
# RNBO
# ---------------------------------------------------------------------------


def _rnbo(box_id, inner_boxes, inner_lines=None):
    return _container(box_id, "rnbo~", _inner(inner_boxes, inner_lines, classnamespace="rnbo"), 1, 1,
                      outlettype=["signal"])


class TestRnboNested:
    def test_rnbo_in_p_without_in(self):
        r = _rnbo("obj-2", [_box("obj-10", "out~ 1", 1, 0, outlettype=[])])
        d = _patch([_container("obj-1", "p synth", _inner([r]))])
        results = review_rnbo(d)
        assert [(x.severity, x.path) for x in results] == [("note", "obj-1")]
        assert results[0].finding == (
            "[p synth] rnbo~ 'obj-2' inner patcher has no in~ object -- "
            "it takes no audio input, which is expected for a generator"
        )

    def test_duplicate_params_across_inner_p(self):
        inner_p = _container("obj-11", "p voice", _inner([
            _box("obj-10", "param @name gain", 1, 2, outlettype=["", ""]),
            _box("obj-12", "param @name MyGain", 1, 2, outlettype=["", ""]),
        ]))
        r = _rnbo("obj-2", [
            _box("obj-5", "in~ 1", 1, 1, outlettype=["signal"]),
            _box("obj-6", "out~ 1", 1, 0, outlettype=[]),
            _box("obj-10", "param @name gain", 1, 2, outlettype=["", ""]),
            inner_p,
        ])
        results = review_rnbo(_patch([r]))
        dups = [x for x in results if "Duplicate RNBO param" in x.finding]
        assert [(x.severity, x.path) for x in dups] == [("blocker", "")]
        assert "'obj-10' and 'obj-11/obj-10'" in dups[0].finding
        naming = [x for x in results if "naming convention" in x.finding]
        assert [x.finding.split("'")[1] for x in naming] == ["MyGain"]

    def test_has_rnbo_boxes_nested(self):
        r = _rnbo("obj-2", [])
        assert _has_rnbo_boxes(_patch([_container("obj-1", "p synth", _inner([r]))])) is True
        assert _has_rnbo_boxes(_patch([_box("obj-1", "print")])) is False


# ---------------------------------------------------------------------------
# M4L
# ---------------------------------------------------------------------------


def _dial(box_id, longname=None, enable=True, annotation=None):
    extra = {}
    if enable:
        extra["parameter_enable"] = 1
    if longname is not None:
        extra["saved_attribute_attributes"] = {"valueof": {"parameter_longname": longname}}
    if annotation is not None:
        extra["annotation"] = annotation
    return _box(box_id, None, 1, 2, maxclass="live.dial", outlettype=["", "float"], **extra)


class TestM4lNested:
    def test_plugout_only_nested_detects_instrument(self):
        d = _wrap([_plugout("obj-2")], [])
        assert detect_m4l_device_type(d) == "instrument"
        results = review_m4l(d, device_type="instrument")
        assert not [r for r in results if "missing required object" in r.finding]

    def test_ezdac_in_p(self):
        d = _patch([_plugout(), _container("obj-1", "p synth", _inner(_c_ezdac()[0]))])
        hits = [r for r in review_m4l(d, device_type="instrument") if "ezdac~ (" in r.finding]
        assert [(r.severity, r.path) for r in hits] == [("blocker", "obj-1")]

    def test_gain_to_plugout_in_same_p(self):
        inner = _inner([
            _box("obj-2", "gain~", 2, 2, outlettype=["signal", ""]),
            _plugout("obj-3"),
        ], [_line("obj-2", 0, "obj-3", 0)])
        d = _patch([_container("obj-1", "p out", inner)])
        hits = [r for r in review_m4l(d, device_type="instrument") if "on the signal path to plugout~" in r.finding]
        assert [(r.severity, r.path) for r in hits] == [("blocker", "obj-1")]
        assert hits[0].finding.startswith("[p out] gain~ (obj-2) is on the signal path to plugout~ (obj-3)")

    def test_duplicate_longname_top_and_nested(self):
        d = _patch([
            _plugout(),
            _dial("obj-3", "Cutoff", annotation="x"),
            _container("obj-1", "p synth", _inner([_dial("obj-3", "Cutoff", annotation="x")])),
        ])
        dups = [r for r in review_m4l(d, device_type="instrument") if "Duplicate parameter_longname" in r.finding]
        assert [(r.severity, r.path) for r in dups] == [("blocker", "")]
        assert "'obj-3' and 'obj-1/obj-3'" in dups[0].finding

    def test_missing_info_text_nested_is_tagged(self):
        d = _patch([_plugout(), _container("obj-1", "p synth", _inner([_dial("obj-3", "Cutoff")]))])
        hits = [r for r in review_m4l(d, device_type="instrument") if "missing info text" in r.finding]
        assert [r.path for r in hits] == ["obj-1"]
        assert hits[0].finding.startswith("[p synth] live.dial (obj-3) missing info text")

    def test_nested_live_banks_satisfies_check(self):
        banks = _box("obj-4", "live.banks", 1, 1, outlettype=[""])
        d = _patch([_plugout(), _dial("obj-3", "Cutoff", annotation="x"),
                    _container("obj-1", "p banks", _inner([banks]))])
        assert not [r for r in review_m4l(d, device_type="instrument") if "no live.banks" in r.finding]
        d2 = _patch([_plugout(), _dial("obj-3", "Cutoff", annotation="x")])
        assert [r for r in review_m4l(d2, device_type="instrument") if "no live.banks" in r.finding]


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------


class TestLayoutNested:
    def test_low_contrast_against_own_bgcolor(self):
        boxes, lines, keys = _c_low_contrast()
        d = _patch([_container("obj-1", "p synth", _inner(boxes, lines, **keys))])
        hits = [r for r in review_layout(d) if "Low contrast" in r.finding]
        assert [(r.severity, r.path) for r in hits] == [("warning", "obj-1")]
        # Without the inner bgcolor the light text sits on the dark palette canvas
        d2 = _patch([_container("obj-1", "p synth", _inner(copy.deepcopy(boxes), lines))])
        assert not [r for r in review_layout(d2) if "Low contrast" in r.finding and r.path]

    def test_whitespace_text_never_raises(self, db):
        inner = _inner([
            _box("obj-2", "   ", 1, 1),
            _box("obj-3", "", 1, 1),
            _box("obj-4", "   ", 1, 0, maxclass="comment", outlettype=[]),
        ])
        d = _patch([_box("obj-9", "  ", 1, 1), _container("obj-1", "p synth", inner)])
        assert isinstance(review_layout(d), list)
        assert isinstance(review_patch(d, db=db), list)


# ---------------------------------------------------------------------------
# Shared graph, purity and robustness with every critic active
# ---------------------------------------------------------------------------


def _all_critics_patch(db):
    if not db.get_package("fluid.mfcc~"):
        pytest.skip("fluid.mfcc~ has no package in the repo DB")
    r = _rnbo("obj-5", [_box("obj-50", "out~ 1", 1, 0, outlettype=[])])
    return _patch([
        _plugout("obj-2"),
        _container("obj-1", "p synth", _inner([r, _fluid("obj-6")])),
    ])


class TestReviewPatchAllCritics:
    def test_every_critic_gets_the_one_graph(self, db, monkeypatch):
        import src.maxpat.critics as critics

        calls = _count_builds(monkeypatch)
        seen = {}
        for name in ("review_dsp", "review_structure", "review_layout", "review_rnbo",
                     "review_m4l", "review_packages", "detect_m4l_device_type"):
            real = getattr(critics, name)

            def spy(*a, _real=real, _name=name, **k):
                seen[_name] = k.get("graph")
                return _real(*a, **k)

            monkeypatch.setattr(critics, name, spy)
        results = review_patch(_all_critics_patch(db), db=db)
        assert len(calls) == 1
        assert set(seen) == {"review_dsp", "review_structure", "review_layout", "review_rnbo",
                             "review_m4l", "review_packages", "detect_m4l_device_type"}
        graphs = set(id(g) for g in seen.values())
        assert len(graphs) == 1 and None not in seen.values()
        assert [r for r in results if "no in~" in r.finding and r.path == "obj-1"]

    def test_review_patch_pure_with_every_critic(self, db):
        d = _all_critics_patch(db)
        before = copy.deepcopy(d)
        review_patch(d, db=db)
        assert d == before


def _junk_scope():
    return _inner(
        [
            "junk",
            None,
            {"box": "not a dict"},
            {"box": {"id": "obj-5", "maxclass": ["x"], "text": None}},
            {"box": {"id": "obj-6", "maxclass": "live.dial", "parameter_enable": 1,
                     "saved_attribute_attributes": 5}},
            {"box": {"id": "obj-7", "maxclass": "live.dial", "parameter_enable": 1,
                     "saved_attribute_attributes": {"valueof": 3}}},
            {"box": {"id": "obj-8", "maxclass": "newobj", "text": "rnbo~", "outlettype": "signal",
                     "patcher": 3}},
            {"box": {"id": "obj-9", "maxclass": "newobj", "text": "   ", "outlettype": None}},
            {"box": {"id": "obj-10", "maxclass": "comment", "text": 5}},
            {"box": {"id": "obj-11", "maxclass": "newobj", "text": "gen~", "numinlets": None,
                     "patcher": {"boxes": [{"box": {"id": "obj-1", "maxclass": "codebox",
                                                    "code": 7}}], "lines": ["x"]}}},
        ],
        [
            "junk",
            None,
            {"patchline": "x"},
            {"patchline": {"source": ["obj-8", 0], "destination": ["obj-9", 0]}},
            {"patchline": {"source": ["obj-5", 0], "destination": ["obj-6", "0"]}},
        ],
    )


_CRITIC_RUNNERS = {
    "structure": lambda d, db: review_structure(d),
    "dsp": lambda d, db: review_dsp(d, code_context={"gen~_code": 5}),
    "layout": lambda d, db: review_layout(d),
    "rnbo": lambda d, db: review_rnbo(d, code_context={"rnbo_target": "cpp"}),
    "m4l": lambda d, db: review_m4l(d, device_type="instrument"),
    "m4l_detect": lambda d, db: [detect_m4l_device_type(d)],
    "packages": lambda d, db: review_packages(d, db=db),
    "review_patch": lambda d, db: review_patch(d, db=db),
}


@pytest.mark.parametrize("critic", sorted(_CRITIC_RUNNERS))
def test_nested_junk_never_raises(critic, db):
    d = _patch([_plugout(), _container("obj-1", "p junk", _junk_scope())])
    assert isinstance(_CRITIC_RUNNERS[critic](d, db), list)


# ===========================================================================
# Task 3: no-crash sweep over the installed Max 9 bundle
# ===========================================================================


class TestBundleSweep:
    @pytest.mark.requires_max
    def test_bundle_sweep_never_raises(self, db):
        import json
        import warnings

        from tests.conftest import MAX_APP_PATH
        from src.maxpat.testing import generate_test_checklist

        root = MAX_APP_PATH / "Contents" / "Resources" / "C74"
        files = sorted(list(root.rglob("*.maxpat")) + list(root.rglob("*.maxhelp")))
        assert files
        raised = []
        checked = 0
        for f in files:
            try:
                d = json.loads(f.read_text(errors="replace"))
            except (ValueError, OSError):
                continue
            if not isinstance(d, dict) or not isinstance(d.get("patcher"), dict):
                continue
            checked += 1
            rel = str(f.relative_to(root))
            step = "review_patch"
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    review_patch(d, db=db)
                    step = "generate_test_checklist"
                    generate_test_checklist(d, f.stem)
                    step = "PatchGraph.build"
                    g = PatchGraph.build(d)
                    top = g.top
                    start = next((bid for bid in top.boxes if top.out_edges.get(bid)), None)
                    if start is not None:
                        step = "downstream"
                        g.downstream(top, start, db=db)
                        step = "downstream(signal_only)"
                        g.downstream(top, start, signal_only=True, db=db)
                        step = "upstream"
                        g.upstream(top, start, db=db)
            except Exception as exc:  # noqa: BLE001 -- collect every crash
                raised.append((rel, step, repr(exc)))
        assert raised == []
        assert checked > len(files) // 2
