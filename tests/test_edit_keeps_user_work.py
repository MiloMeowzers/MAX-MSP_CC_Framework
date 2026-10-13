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
