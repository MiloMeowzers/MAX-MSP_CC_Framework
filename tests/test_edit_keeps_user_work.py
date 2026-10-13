"""Q6 regression tests: the edit path keeps user work.

Quick task 261012-pkh implements Q6 of
``.planning/reviews/2026-10-11-fix-plan.md`` (review findings B1, B2, B3):

- B1: ``finalize_patch(is_new=False)`` must never clear existing cord
  midpoints. It routes only cords that have none and are new or touch a box
  added or moved in this edit.
- B2: ``modify_box(args=...)`` keeps I/O counts and cords for
  content-defined boxes and recomputes only for DB ``variable_io`` objects.
- B3: ``modify_box(args=...)`` on message/comment boxes writes the joined
  args with no maxclass prefix.
- Plus: ``populate_assistance_comments`` writes ``_raw["comment"]`` so the
  inferred comments reach disk on loaded subpatchers.

Real patches (ji-harmonizer, FDNVerb) are only read with ``json.load`` and
deep-copied; everything is inspected in memory. No test writes a file or
runs git.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from src.maxpat.db_lookup import ObjectDatabase
from src.maxpat.hooks import finalize_patch
from src.maxpat.patcher import Patcher

REPO = Path(__file__).resolve().parents[1]
JH = "patches/ji-harmonizer/generated/ji-harmonizer.maxpat"
FD = "patches/FDNVerb/generated/FDNVerb.maxpat"


@pytest.fixture(scope="module")
def db():
    return ObjectDatabase()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_json(rel):
    with open(REPO / rel, encoding="utf-8") as f:
        return json.load(f)


def _load(rel, db):
    return Patcher.from_dict(copy.deepcopy(_read_json(rel)), db=db)


def _walk(patcher, path="top"):
    """Yield (path, patcher) recursively through embedded patchers."""
    yield path, patcher
    for box in patcher.boxes:
        if box._inner_patcher is not None:
            yield from _walk(box._inner_patcher, path + "/" + box.id)


def _walk_dict(pd, path="top"):
    """Yield (path, patcher_dict) recursively through a serialized patcher."""
    yield path, pd
    for entry in pd.get("boxes", []):
        bx = entry["box"]
        if isinstance(bx.get("patcher"), dict):
            yield from _walk_dict(bx["patcher"], path + "/" + bx["id"])


def _reload(p, db):
    """Serialize and reload so API-built boxes become loaded boxes with _raw."""
    return Patcher.from_dict(p.to_dict(), db=db)


def _snapshot(patcher):
    snap = {}
    for path, pp in _walk(patcher):
        for i, line in enumerate(pp.lines):
            snap[(path, i)] = list(line.midpoints) if line.midpoints else None
    return snap


def _box(patcher, box_id):
    return next(b for b in patcher.boxes if b.id == box_id)


def _find_line(patcher, src, dst):
    for line in patcher.lines:
        if line.source_id == src.id and line.dest_id == dst.id:
            return line
    raise AssertionError(f"no line {src.id} -> {dst.id}")


# ---------------------------------------------------------------------------
# B1: finalize_patch(is_new=False) keeps routing
# ---------------------------------------------------------------------------

class TestFinalizeKeepsRouting:

    def test_ji_harmonizer_unchanged_keeps_every_midpoint(self, db):
        p = _load(JH, db)
        before = _snapshot(p)
        routed = [k for k, v in before.items() if v]
        straight = [k for k, v in before.items() if not v]
        assert len(routed) == 367
        assert len(straight) == 23

        finalize_patch(p, is_new=False)
        after = _snapshot(p)

        kept = sum(1 for k in routed if after[k] == before[k])
        rerouted_straight = [k for k in straight if after[k]]
        assert kept == 367, f"only {kept}/367 routed cords kept their midpoints"
        assert rerouted_straight == [], (
            f"{len(rerouted_straight)} straight cords were routed"
        )

        # Serialized lines equal the file's, in every patcher.
        file_dicts = dict(_walk_dict(_read_json(JH)["patcher"]))
        out_dicts = dict(_walk_dict(p.to_dict()["patcher"]))
        assert set(file_dicts) == set(out_dicts)
        for path, fpd in file_dicts.items():
            assert out_dicts[path].get("lines", []) == fpd.get("lines", []), path

    def test_ji_harmonizer_with_added_box_routes_only_the_new_cord(self, db):
        p = _load(JH, db)
        before = _snapshot(p)

        src = next(
            b for b in p.boxes
            if b.maxclass == "newobj" and b.numoutlets >= 1
            and b._inner_patcher is None
        )
        new = p.add_box(
            "print", ["q6"],
            x=src.patching_rect[0] + 300, y=src.patching_rect[1] + 200,
            skip_overlap_check=True,
        )
        new_line = p.add_connection(src, 0, new, 0)

        finalize_patch(p, is_new=False)

        assert new_line.midpoints, "the new cord should be routed"
        after = _snapshot(p)
        for key, mids in before.items():
            assert after[key] == mids, f"pre-existing line {key} changed"

    def test_moved_box_routes_its_unrouted_cords_only(self, db):
        p = Patcher(db=db)
        a = p.add_box("metro", ["100"], x=30, y=30, skip_overlap_check=True)
        b = p.add_box("t", ["b"], x=30, y=100, skip_overlap_check=True)
        c = p.add_box("print", x=30, y=170, skip_overlap_check=True)
        p.add_connection(a, 0, b, 0)
        p.add_connection(b, 0, c, 0, midpoints=[40, 140, 40, 150])

        q = _reload(p, db)
        qa, qb, qc = (_box(q, x.id) for x in (a, b, c))
        assert not _find_line(q, qa, qb).midpoints

        q.modify_box(qb, position=[300, 100])
        finalize_patch(q, is_new=False)

        assert _find_line(q, qa, qb).midpoints, "A->B touches a moved box"
        assert list(_find_line(q, qb, qc).midpoints) == [40, 140, 40, 150]

    def test_unmoved_straight_cord_stays_straight(self, db):
        p = Patcher(db=db)
        a = p.add_box("metro", ["100"], x=30, y=30, skip_overlap_check=True)
        b = p.add_box("print", x=300, y=100, skip_overlap_check=True)
        p.add_connection(a, 0, b, 0)

        q = _reload(p, db)
        qa, qb = _box(q, a.id), _box(q, b.id)
        finalize_patch(q, is_new=False)

        assert not _find_line(q, qa, qb).midpoints

    def test_resize_alone_is_not_a_move(self, db):
        p = Patcher(db=db)
        a = p.add_box("metro", ["100"], x=30, y=30, skip_overlap_check=True)
        b = p.add_box("print", x=300, y=100, skip_overlap_check=True)
        p.add_connection(a, 0, b, 0)

        q = _reload(p, db)
        qa, qb = _box(q, a.id), _box(q, b.id)
        qb.patching_rect[2] += 40  # width change only
        finalize_patch(q, is_new=False)

        assert not _find_line(q, qa, qb).midpoints


# ---------------------------------------------------------------------------
# Assistance comments reach disk
# ---------------------------------------------------------------------------

class TestAssistanceCommentsPersist:

    def test_synthetic_subpatcher_comments_serialize(self, db):
        p = Patcher(db=db)
        _, inner = p.add_subpatcher("sub", inlets=1, outlets=1, x=30, y=30)
        ins, outs = inner.get_inlets(), inner.get_outlets()
        t = inner.add_box("t", ["b"], x=50, y=120, skip_overlap_check=True)
        inner.add_connection(ins[0], 0, t, 0)
        inner.add_connection(t, 0, outs[0], 0)
        p.add_subpatcher(
            "sub2", inlets=1, outlets=0, x=200, y=30,
            inlet_comments=["keep me"],
        )

        q = _reload(p, db)
        q.populate_assistance_comments()
        out = q.to_dict()["patcher"]

        subs = [e["box"] for e in out["boxes"] if "patcher" in e["box"]]
        by_text = {s["text"]: s for s in subs}
        first = by_text["p sub"]["patcher"]["boxes"]
        ports = [e["box"] for e in first
                 if e["box"]["maxclass"] in ("inlet", "outlet")]
        assert len(ports) == 2
        for port in ports:
            assert port.get("comment"), f"empty comment on disk: {port['id']}"

        second = by_text["p sub2"]["patcher"]["boxes"]
        kept = [e["box"] for e in second if e["box"]["maxclass"] == "inlet"]
        assert kept[0]["comment"] == "keep me"

    def test_ji_harmonizer_empty_port_comments_serialize(self, db):
        p = _load(JH, db)
        finalize_patch(p, is_new=False)
        out = p.to_dict()["patcher"]

        checked = 0
        for _, pd in _walk_dict(out):
            for entry in pd.get("boxes", []):
                bx = entry["box"]
                text = bx.get("text") or ""
                if text not in ("p init", "p wtctl", "p ratioset"):
                    continue
                for inner in bx["patcher"]["boxes"]:
                    ib = inner["box"]
                    if ib["maxclass"] in ("inlet", "outlet"):
                        checked += 1
                        assert ib.get("comment"), (
                            f"{text}/{ib['id']} has an empty comment on disk"
                        )
        assert checked == 13 + 10 + 13


# ---------------------------------------------------------------------------
# B2 / B3: modify_box(args=...) keeps user work
# ---------------------------------------------------------------------------

def _obj(box_id, text, nin, nout, x=30.0, y=30.0, maxclass="newobj", **extra):
    box = {
        "id": box_id,
        "maxclass": maxclass,
        "numinlets": nin,
        "numoutlets": nout,
        "outlettype": [""] * nout,
        "patching_rect": [x, y, 80.0, 22.0],
    }
    if text is not None:
        box["text"] = text
    box.update(extra)
    return {"box": box}


def _cord(src, outlet, dst, inlet):
    return {"patchline": {"source": [src, outlet], "destination": [dst, inlet]}}


def _loaded(boxes, lines, db):
    return Patcher.from_dict(
        {"patcher": {"boxes": boxes, "lines": lines}}, db=db,
    )


def _cords_of(patcher, box):
    return sorted(
        (l.source_id, l.source_outlet, l.dest_id, l.dest_inlet)
        for l in patcher.lines
        if l.source_id == box.id or l.dest_id == box.id
    )


def _fd_box4(p):
    matches = [
        b for b in p.boxes
        if b.maxclass == "newobj" and b.text == "gen~ FDNverb"
    ]
    assert len(matches) == 1
    return matches[0]


def _port_harness(center_text, nin, nout, db, **center_extra):
    """A loaded box with a cord into every inlet and out of every outlet."""
    boxes = [_obj("obj-1", center_text, nin, nout, x=200, y=200, **center_extra)]
    lines = []
    for i in range(nin):
        boxes.append(_obj(f"obj-in{i}", "t b", 1, 1, x=100 + i * 90, y=100))
        lines.append(_cord(f"obj-in{i}", 0, "obj-1", i))
    for o in range(nout):
        boxes.append(_obj(f"obj-out{o}", "print", 1, 0, x=100 + o * 90, y=300))
        lines.append(_cord("obj-1", o, f"obj-out{o}", 0))
    p = _loaded(boxes, lines, db)
    return p, _box(p, "obj-1")


class TestModifyBoxContentDefined:

    def test_fdnverb_same_args_keeps_io_and_cords(self, db):
        p = _load(FD, db)
        box4 = _fd_box4(p)
        assert (box4.numinlets, box4.numoutlets) == (2, 2)
        assert len(p.lines) == 41
        rect_before = list(box4.patching_rect)

        result = p.modify_box(box4, args=["FDNverb"])

        assert (box4.numinlets, box4.numoutlets) == (2, 2)
        assert len(p.lines) == 41
        assert result.orphaned == []
        assert list(box4.patching_rect) == rect_before
        assert p.to_dict()["patcher"]["lines"] == _read_json(FD)["patcher"]["lines"]

    def test_fdnverb_changed_args_keeps_io_and_cords(self, db):
        p = _load(FD, db)
        box4 = _fd_box4(p)

        result = p.modify_box(box4, args=["FDNverb2"])

        assert box4.text == "gen~ FDNverb2"
        assert (box4.numinlets, box4.numoutlets) == (2, 2)
        assert len(p.lines) == 41
        assert result.orphaned == []
        assert box4._raw["numoutlets"] == 2
        assert box4._raw["text"] == "gen~ FDNverb2"

    def test_p_subpatcher_keeps_io_and_cords(self, db):
        p = Patcher(db=db)
        sub, _ = p.add_subpatcher("articulation", inlets=2, outlets=2, x=200, y=200)
        srcs = [p.add_box("t", ["b"], x=100 + i * 90, y=100, skip_overlap_check=True)
                for i in range(2)]
        dsts = [p.add_box("print", x=100 + i * 90, y=300, skip_overlap_check=True)
                for i in range(2)]
        for i in range(2):
            p.add_connection(srcs[i], 0, sub, i)
            p.add_connection(sub, i, dsts[i], 0)

        q = _reload(p, db)
        qsub = _box(q, sub.id)
        before = _cords_of(q, qsub)
        assert len(before) == 4

        result = q.modify_box(qsub, args=["phrasing"])

        assert qsub.text == "p phrasing"
        assert (qsub.numinlets, qsub.numoutlets) == (2, 2)
        assert _cords_of(q, qsub) == before
        assert result.orphaned == []

    def test_js_keeps_io_and_cords(self, db):
        boxes = [
            _obj("obj-1", "js engine.js", 3, 2, x=200, y=200),
            _obj("obj-2", "t b", 1, 1, x=100, y=100),
            _obj("obj-3", "t b", 1, 1, x=190, y=100),
            _obj("obj-4", "t b", 1, 1, x=280, y=100),
            _obj("obj-5", "print", 1, 0, x=200, y=300),
        ]
        lines = [
            _cord("obj-2", 0, "obj-1", 0),
            _cord("obj-3", 0, "obj-1", 1),
            _cord("obj-4", 0, "obj-1", 2),
            _cord("obj-1", 1, "obj-5", 0),
        ]
        p = _loaded(boxes, lines, db)
        js = _box(p, "obj-1")

        result = p.modify_box(js, args=["engine2.js"])

        assert js.text == "js engine2.js"
        assert (js.numinlets, js.numoutlets) == (3, 2)
        assert len(p.lines) == 4
        assert result.orphaned == []

    def test_unknown_abstraction_keeps_io_and_cords(self, db):
        p, box = _port_harness("q6-test-abstraction 1", 2, 2, db)
        before = _cords_of(p, box)
        assert len(before) == 4

        result = p.modify_box(box, args=["2"])

        assert box.text == "q6-test-abstraction 2"
        assert (box.numinlets, box.numoutlets) == (2, 2)
        assert _cords_of(p, box) == before
        assert result.orphaned == []

    def test_io_is_content_defined_predicate(self, db):
        fd = _load(FD, db)
        assert fd._io_is_content_defined(_fd_box4(fd)) is True

        p = Patcher(db=db)
        sub, _ = p.add_subpatcher("x", inlets=1, outlets=1)
        assert p._io_is_content_defined(sub) is True

        boxes = [
            _obj("obj-1", None, 1, 1, maxclass="bpatcher", name="child.maxpat"),
            _obj("obj-2", "js thing.js", 1, 1),
            _obj("obj-3", "node.script s.js", 1, 2),
            _obj("obj-4", "q6-unknown-thing", 1, 1),
            _obj("obj-5", "cycle~ 440", 2, 1),
            _obj("obj-6", "trigger b b", 1, 2),
            _obj("obj-7", "pack 0 0", 2, 1),
            _obj("obj-8", "expr $f1+$f2", 2, 1),
        ]
        q = _loaded(boxes, [], db)
        for bid in ("obj-1", "obj-2", "obj-3", "obj-4", "obj-5"):
            assert q._io_is_content_defined(_box(q, bid)) is True, bid
        for bid in ("obj-6", "obj-7", "obj-8"):
            assert q._io_is_content_defined(_box(q, bid)) is False, bid


class TestModifyBoxVariableIO:

    def test_pack_shrink_orphans_only_out_of_range_cord(self, db):
        p, box = _port_harness("pack 0 0 0", 3, 0, db)

        result = p.modify_box(box, args=["0", "0"])

        assert box.numinlets == 2
        assert result.orphaned == [{
            "source_id": "obj-in2", "source_outlet": 0,
            "dest_id": "obj-1", "dest_inlet": 2,
        }]
        assert _cords_of(p, box) == [
            ("obj-in0", 0, "obj-1", 0), ("obj-in1", 0, "obj-1", 1),
        ]
        assert box._raw["numinlets"] == 2

    def test_trigger_grow_keeps_all_cords(self, db):
        p, box = _port_harness("trigger b i f", 0, 3, db)
        before = _cords_of(p, box)

        result = p.modify_box(box, args=["b", "b", "b", "b"])

        assert box.numoutlets == 4
        assert _cords_of(p, box) == before
        assert result.orphaned == []

    def test_unchanged_text_is_a_noop(self, db):
        p, box = _port_harness("expr $f1+$f2", 2, 1, db)
        before = _cords_of(p, box)
        rect_before = list(box.patching_rect)

        result = p.modify_box(box, args=["$f1+$f2"])

        assert box.numinlets == 2
        assert _cords_of(p, box) == before
        assert list(box.patching_rect) == rect_before
        assert result.orphaned == []


class TestModifyBoxText:

    def test_new_message_text_has_no_prefix(self, db):
        p = Patcher(db=db)
        msg = p.add_message("read a.wav")
        io = (msg.numinlets, msg.numoutlets)

        p.modify_box(msg, args=["read", "drums.wav"])

        assert msg.text == "read drums.wav"
        assert (msg.numinlets, msg.numoutlets) == io

    def test_loaded_message_text_reaches_disk(self, db):
        p = Patcher(db=db)
        msg = p.add_message("read a.wav", x=30, y=30)
        pr = p.add_box("print", x=30, y=100, skip_overlap_check=True)
        p.add_connection(msg, 0, pr, 0)

        q = _reload(p, db)
        qmsg = _box(q, msg.id)
        io = (qmsg.numinlets, qmsg.numoutlets)

        result = q.modify_box(qmsg, args=["read", "drums.wav"])

        assert qmsg.text == "read drums.wav"
        assert qmsg._raw["text"] == "read drums.wav"
        assert (qmsg.numinlets, qmsg.numoutlets) == io
        assert len(q.lines) == 1
        assert result.orphaned == []
        out = {e["box"]["id"]: e["box"] for e in q.to_dict()["patcher"]["boxes"]}
        assert out[msg.id]["text"] == "read drums.wav"

    def test_new_comment_text_has_no_prefix(self, db):
        p = Patcher(db=db)
        c = p.add_comment("Old")

        p.modify_box(c, args=["New", "label"])

        assert c.text == "New label"
