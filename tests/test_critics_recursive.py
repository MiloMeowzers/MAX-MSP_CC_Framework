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

    @pytest.mark.parametrize("name", sorted(_PARITY_CONTENT))
    def test_nested_parity_with_top_level(self, name):
        boxes, lines = _PARITY_CONTENT[name]()
        top = review_structure(_patch(copy.deepcopy(boxes), copy.deepcopy(lines)))
        assert top, name
        nested = review_structure(_wrap(boxes, lines))
        assert [(r.severity, "[p synth] " + r.finding, r.suggestion, "obj-1") for r in top] == _sig(nested)
        assert all(r.path == "" for r in top)

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
