"""Semantic patch diff tests (quick 261022-i07, fix-plan Q36, D-06 / D-07).

Committed patches are only read, through ``git show HEAD:<path>``, and edited
in memory; nothing under ``patches/`` is ever opened for writing.
"""

from __future__ import annotations

import copy
import functools
import json
import subprocess
from pathlib import Path

import pytest

from src.maxpat.patcher import Patcher
from src.maxpat.patch_diff import DIFF_KINDS, PatchDiff, diff_patch_dicts

REPO_ROOT = Path(__file__).resolve().parent.parent
JI = "patches/ji-harmonizer/generated/ji-harmonizer.maxpat"


def _tracked() -> list:
    try:
        out = subprocess.run(
            ["git", "ls-files", "-z", "--", "patches/*.maxpat"],
            cwd=str(REPO_ROOT), capture_output=True, check=True,
        ).stdout
        return sorted(p for p in out.decode("utf-8").split("\0") if p)
    except Exception:
        return []


TRACKED = _tracked()


@functools.lru_cache(maxsize=None)
def _head_text(rel: str) -> str:
    return subprocess.run(
        ["git", "show", f"HEAD:{rel}"],
        cwd=str(REPO_ROOT), capture_output=True, check=True,
    ).stdout.decode("utf-8")


def _load(rel: str) -> dict:
    return json.loads(_head_text(rel))


def _bid(p: Patcher, box_id: str):
    for b in p.boxes:
        if b.id == box_id:
            return b
    raise KeyError(box_id)


def _dbox(patcher: dict, box_id: str) -> dict:
    for entry in patcher["boxes"]:
        if entry["box"]["id"] == box_id:
            return entry["box"]
    raise KeyError(box_id)


def _kinds(diff: PatchDiff) -> list:
    return [e.kind for e in diff]


# Synthetic dict helpers ------------------------------------------------------


def _box(box_id, text=None, x=0, y=0, **extra) -> dict:
    b = {
        "id": box_id,
        "maxclass": extra.pop("maxclass", "newobj"),
        "numinlets": 1,
        "numoutlets": 1,
        "patching_rect": [x, y, 60.0, 22.0],
    }
    if text is not None:
        b["text"] = text
    b.update(extra)
    return {"box": b}


def _line(src, o, dst, i, **extra) -> dict:
    pl = {"source": [src, o], "destination": [dst, i]}
    pl.update(extra)
    return {"patchline": pl}


def _patch(boxes, lines=(), **props) -> dict:
    p = {"boxes": list(boxes), "lines": list(lines)}
    p.update(props)
    return {"patcher": p}


def _inner(boxes, lines=()) -> dict:
    return {"boxes": list(boxes), "lines": list(lines)}


# ---------------------------------------------------------------------------
# Round trip over every committed patch
# ---------------------------------------------------------------------------


def test_committed_list_not_empty():
    assert len(TRACKED) >= 60


@pytest.mark.parametrize("rel", TRACKED)
def test_round_trip_diff_empty(rel):
    d = _load(rel)
    for other in (Patcher.from_dict(d).to_dict(), copy.deepcopy(d)):
        diff = diff_patch_dicts(d, other)
        assert not diff, diff.render()
        assert len(diff) == 0
        assert diff.render() == "no changes"


# ---------------------------------------------------------------------------
# ji-harmonizer edits through the Patcher API
# ---------------------------------------------------------------------------


@pytest.fixture
def ji():
    d = _load(JI)
    return d, Patcher.from_dict(d), Patcher.from_dict(d)


def test_moved(ji):
    _, before, after = ji
    box = _bid(after, "obj-64")
    x, y = box.patching_rect[0], box.patching_rect[1]
    after.modify_box(box, position=[x + 40, y])
    diff = before.diff(after)
    assert _kinds(diff) == ["moved"]
    e = diff.entries[0]
    assert (e.box_id, e.path, e.where) == ("obj-64", (), "")
    assert e.old == (x, y) and e.new == (x + 40, y)
    assert "obj-64 [*~ 0.1] moved" in diff.render()


def test_resized(ji):
    _, before, after = ji
    box = _bid(after, "obj-64")
    x, y, w, h = box.patching_rect
    box.patching_rect = [x, y, w + 30, h]
    diff = before.diff(after)
    assert _kinds(diff) == ["resized"]
    assert diff.entries[0].old == (w, h)
    assert diff.entries[0].new == (w + 30, h)


def test_text(ji):
    _, before, after = ji
    after.modify_box(_bid(after, "obj-64"), args=["0.2"])
    diff = before.diff(after)
    assert _kinds(diff) == ["text"]
    e = diff.entries[0]
    assert (e.old, e.new) == ("*~ 0.1", "*~ 0.2")
    assert '~ obj-64 text "*~ 0.1" -> "*~ 0.2"' in diff.render()


def test_attrs_textcolor(ji):
    _, before, after = ji
    _bid(after, "obj-85").extra_attrs["textcolor"] = [1.0, 1.0, 1.0, 1.0]
    diff = before.diff(after)
    assert _kinds(diff) == ["attrs"]
    assert diff.entries[0].new == ("textcolor",)
    assert "obj-85 [comment degree enable] attrs textcolor" in diff.render()


def test_presentation(ji):
    _, before, after = ji
    after.add_to_presentation(_bid(after, "obj-85"), [10, 10, 100, 20])
    diff = before.diff(after)
    assert _kinds(diff) == ["presentation"]
    e = diff.entries[0]
    assert e.old == (False, None)
    assert e.new == (True, (10, 10, 100, 20))
    assert "presentation off -> on [10,10,100,20]" in diff.render()


def test_box_removed_with_cords(ji):
    d, before, after = ji
    n_cords = sum(
        1 for l in d["patcher"]["lines"]
        if "obj-64" in (l["patchline"]["source"][0], l["patchline"]["destination"][0])
    )
    assert n_cords > 0
    after.remove_box(_bid(after, "obj-64"))
    diff = before.diff(after)
    assert len(diff.of("box_removed")) == 1
    assert len(diff.of("cord_removed")) == n_cords
    assert set(_kinds(diff)) == {"box_removed", "cord_removed"}


def test_zorder(ji):
    _, before, after = ji
    last = after.boxes[-1]
    assert after.boxes[0] is not last
    after.bring_to_front(last)
    diff = before.diff(after)
    assert _kinds(diff) == ["zorder"]
    assert "z-order changed (1 boxes)" in diff.render()


def test_patcher_diff_does_not_mutate(ji):
    d, before, after = ji
    before.diff(after)
    assert diff_patch_dicts(d, before.to_dict()).entries == []
    assert diff_patch_dicts(d, after.to_dict()).entries == []


# ---------------------------------------------------------------------------
# Nested (D-07)
# ---------------------------------------------------------------------------


def test_nested_move_path_prefixed(ji):
    _, before, after = ji
    inner = _bid(after, "obj-15")._inner_patcher
    ib = inner.boxes[0]
    inner.modify_box(ib, position=[ib.patching_rect[0] + 25, ib.patching_rect[1]])
    diff = before.diff(after)
    assert _kinds(diff) == ["moved"]
    e = diff.entries[0]
    assert e.path == ("obj-15",)
    assert e.box_id == ib.id
    assert e.where.startswith("p params/")
    assert "p params/obj-" in diff.render()


def test_rename_p_keeps_inner_ids():
    d = _load(JI)
    d2 = copy.deepcopy(d)
    obj15 = _dbox(d2["patcher"], "obj-15")
    obj15["text"] = "p params2"
    inner_box = obj15["patcher"]["boxes"][0]["box"]
    inner_box["patching_rect"][0] += 10
    diff = diff_patch_dicts(d, d2)
    assert _kinds(diff) == ["text", "moved"]
    assert diff.entries[0].box_id == "obj-15" and diff.entries[0].path == ()
    moved = diff.entries[1]
    assert moved.path == ("obj-15",) and moved.box_id == inner_box["id"]
    assert moved.where.startswith("p params2/")
    assert not diff.of("box_added", "box_removed")


def test_mc_gen_data_patcher_code():
    d = _load(JI)
    d2 = copy.deepcopy(d)
    inner = _dbox(d2["patcher"], "obj-88")["data"]["patcher"]
    codebox = next(e["box"] for e in inner["boxes"] if e["box"]["maxclass"] == "codebox")
    assert "code" in codebox
    codebox["code"] = codebox["code"] + "\n// edited"
    diff = diff_patch_dicts(d, d2)
    assert len(diff) == 1
    e = diff.entries[0]
    assert e.kind == "attrs" and e.new == ("code",)
    assert e.path == ("obj-88",) and e.box_id == codebox["id"]
    assert [x for x in diff.of("attrs") if x.path == () and x.box_id == "obj-88"] == []


# ---------------------------------------------------------------------------
# Synthetic cases
# ---------------------------------------------------------------------------


def test_external_bpatcher_args_not_recursed():
    old = _patch([_box("obj-1", maxclass="bpatcher", name="x.maxpat", args=["a"])])
    new = _patch([_box("obj-1", maxclass="bpatcher", name="x.maxpat", args=["b"])])
    diff = diff_patch_dicts(old, new)
    assert _kinds(diff) == ["attrs"]
    assert diff.entries[0].new == ("args",)


def test_subpatcher_added_and_removed():
    inner = _inner([_box("obj-1", "print"), _box("obj-2", "print")])
    plain = _patch([_box("obj-1", "p x")])
    embedded = _patch([_box("obj-1", "p x", patcher=inner)])
    added = diff_patch_dicts(plain, embedded)
    assert _kinds(added) == ["subpatcher_added"]
    assert added.entries[0].new == 2
    assert "+ obj-1 [p x] subpatcher (2 boxes)" in added.render()
    removed = diff_patch_dicts(embedded, plain)
    assert _kinds(removed) == ["subpatcher_removed"]
    assert removed.entries[0].old == 2
    assert "- obj-1 [p x] subpatcher (2 boxes)" in removed.render()


def test_duplicate_sibling_labels_disambiguated():
    def build(dx):
        return _patch([
            _box("obj-1", "p x", patcher=_inner([_box("obj-1", "print", 10 + dx, 10)])),
            _box("obj-2", "p x", 100, patcher=_inner([_box("obj-1", "print", 10 + dx, 10)])),
        ])

    diff = diff_patch_dicts(build(0), build(5))
    assert [e.where for e in diff] == ["p x (obj-1)/", "p x (obj-2)/"]


def test_deep_chain_no_recursion_error():
    def chain(depth, x):
        inner = _inner([_box("obj-1", "print", x, 0)])
        for _ in range(depth):
            inner = _inner([_box("obj-1", "p d", patcher=inner)])
        return {"patcher": inner}

    diff = diff_patch_dicts(chain(1500, 0), chain(1500, 7))
    assert len(diff) == 1
    e = diff.entries[0]
    assert e.kind == "moved"
    assert len(e.path) == 1500


def test_cord_rerouted():
    boxes = [_box("obj-1", "number"), _box("obj-2", "print", 0, 100)]
    old = _patch(boxes, [_line("obj-1", 0, "obj-2", 0)])
    new = _patch(copy.deepcopy(boxes), [_line("obj-1", 0, "obj-2", 0, midpoints=[5, 50, 5, 80])])
    diff = diff_patch_dicts(old, new)
    assert _kinds(diff) == ["cord_rerouted"]
    assert diff.entries[0].new == (5, 50, 5, 80)
    assert "~ cord obj-1:0 -> obj-2:0 rerouted" in diff.render()


def test_props_change():
    old = _patch([_box("obj-1", "print")], bgcolor=[0, 0, 0, 1])
    new = _patch([_box("obj-1", "print")], bgcolor=[1, 1, 1, 1])
    diff = diff_patch_dicts(old, new)
    assert _kinds(diff) == ["props"]
    assert diff.entries[0].new == ("bgcolor",)
    assert "~ patcher props bgcolor" in diff.render()


def test_missing_patcher_raises():
    with pytest.raises(ValueError, match="old"):
        diff_patch_dicts({}, _patch([]))
    with pytest.raises(ValueError, match="new"):
        diff_patch_dicts(_patch([]), {"patcher": None})


def test_malformed_entries_skipped():
    old = _patch([_box("obj-1", "print")])
    new = _patch(
        [_box("obj-1", "print"), "junk", {"box": {"maxclass": "newobj"}}, {"box": 3}],
        ["junk", {"patchline": {"source": ["obj-1"], "destination": ["obj-2", 0]}}],
    )
    assert not diff_patch_dicts(old, new)


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------


def test_render_truncation_and_summary():
    old = _patch([])
    new = _patch([_box(f"obj-{i}", "print", i * 10, 20) for i in range(1, 6)])
    diff = diff_patch_dicts(old, new)
    assert len(diff) == 5
    lines = diff.render(max_lines=2).splitlines()
    assert lines == [
        "+ obj-1 [print] @10,20",
        "+ obj-2 [print] @20,20",
        "... 3 more",
        "5 change(s): 5 box_added",
    ]
    assert str(diff) == diff.render()
    assert diff.counts() == {"box_added": 5}


def test_render_line_formats():
    old = _patch(
        [
            _box("obj-1", "number", 10, 10),
            _box("obj-2", "print", 10, 100),
            _box("obj-3", "cycle~ 440", 200, 10),
            _box("obj-4", maxclass="comment", text="hi", x=0, y=0, presentation=1,
                 presentation_rect=[1, 2, 3, 4]),
        ],
        [_line("obj-1", 0, "obj-2", 0)],
    )
    new = _patch(
        [
            _box("obj-1", "number", 50, 10),
            _box("obj-2", "print abc", 10, 100),
            _box("obj-4", maxclass="comment", text="hi", x=0, y=0),
            _box("obj-5", "+ 1", 30, 40),
        ],
        [_line("obj-1", 0, "obj-5", 0)],
    )
    lines = diff_patch_dicts(old, new).render().splitlines()
    assert lines == [
        "~ obj-1 [number] moved 10,10 -> 50,10",
        '~ obj-2 text "print" -> "print abc"',
        "~ obj-4 [comment hi] presentation on [1,2,3,4] -> off",
        "+ obj-5 [+ 1] @30,40",
        "- obj-3 [cycle~ 440]",
        "+ cord obj-1:0 -> obj-5:0",
        "- cord obj-1:0 -> obj-2:0",
        "7 change(s): 1 box_added, 1 box_removed, 1 moved, 1 text, 1 presentation,"
        " 1 cord_added, 1 cord_removed",
    ]


def test_diff_kinds_complete():
    assert DIFF_KINDS == (
        "box_added", "box_removed", "moved", "resized", "text", "attrs",
        "presentation", "subpatcher_added", "subpatcher_removed", "cord_added",
        "cord_removed", "cord_rerouted", "props", "zorder",
    )
