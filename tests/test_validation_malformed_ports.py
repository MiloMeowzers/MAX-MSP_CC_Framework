"""WR-01 (review-validation, quick 261022-ud6 WP1): non-int / negative port
indices on a patchline.

Q19 promised malformed-entry robustness, but Layer 3 only checked the
endpoint lengths: ``"0"`` / None raised TypeError from ``>=``, a float
raised from ``outlettype[0.0]``, and ``-1`` passed the bounds check and
read the LAST outlet. Every such cord is now the existing "Malformed
patchline" error with a proposed removal, and Layer 4 / the graph skip it.
"""

from __future__ import annotations

import copy

import pytest

from src.maxpat.db_lookup import ObjectDatabase
from src.maxpat.graph import PatchGraph
from src.maxpat.validation import apply_fixes, has_blocking_errors, validate_patch
from tests.test_validation import _make_box, _make_line, _make_patch_dict


@pytest.fixture(scope="module")
def db():
    return ObjectDatabase()


def _patch(src_port, dst_port):
    return _make_patch_dict(
        boxes=[
            _make_box("obj-1", text="cycle~ 440", numinlets=2, numoutlets=1),
            _make_box("obj-2", text="*~ 0.1", numinlets=2, numoutlets=1),
            _make_box("obj-3", text="dac~", numinlets=2, numoutlets=0,
                      outlettype=[]),
        ],
        lines=[
            _make_line("obj-1", src_port, "obj-2", dst_port),
            _make_line("obj-2", 0, "obj-3", 0),
            _make_line("obj-2", 0, "obj-3", 1),
        ],
    )


_BAD = ["0", None, 0.0, 1.5, True, -1, [0]]


def _malformed(results):
    return [r for r in results if r.message.startswith("Malformed patchline")]


class TestNonIntPortIndex:

    @pytest.mark.parametrize("bad", _BAD, ids=repr)
    def test_bad_outlet_is_malformed_not_a_crash(self, db, bad):
        results = validate_patch(_patch(bad, 0), db=db)
        bad_rows = _malformed(results)
        assert len(bad_rows) == 1, [str(r) for r in results]
        assert bad_rows[0].level == "error"
        assert bad_rows[0].proposed_removal is not None
        assert has_blocking_errors(results)

    @pytest.mark.parametrize("bad", _BAD, ids=repr)
    def test_bad_inlet_is_malformed_not_a_crash(self, db, bad):
        results = validate_patch(_patch(0, bad), db=db)
        assert len(_malformed(results)) == 1, [str(r) for r in results]

    def test_negative_index_no_longer_passes(self, db):
        results = validate_patch(_patch(-1, -1), db=db)
        assert len(_malformed(results)) == 1

    def test_apply_fixes_removes_the_malformed_cord(self, db):
        patch = _patch("0", 0)
        results = validate_patch(copy.deepcopy(patch), db=db)
        removed = apply_fixes(patch, results)
        assert len(removed) == 1
        assert len(patch["patcher"]["lines"]) == 2

    def test_non_int_box_counts_do_not_crash(self, db):
        patch = _patch(0, 0)
        patch["patcher"]["boxes"][1]["box"]["numinlets"] = "2"
        patch["patcher"]["boxes"][0]["box"]["outlettype"] = "signal"
        validate_patch(patch, db=db)  # must not raise

    def test_unhashable_box_id_is_malformed(self, db):
        patch = _patch(0, 0)
        patch["patcher"]["lines"][0]["patchline"]["source"] = [["obj-1"], 0]
        results = validate_patch(patch, db=db)
        assert len(_malformed(results)) == 1

    def test_valid_cords_unchanged(self, db):
        results = validate_patch(_patch(0, 0), db=db)
        assert _malformed(results) == []


class TestSaveGateNoRawTypeError:

    def test_save_raises_patch_validation_error(self, db, tmp_path):
        from src.maxpat.hooks import PatchValidationError, save_patch_roundtrip

        with pytest.raises(PatchValidationError):
            save_patch_roundtrip(_patch("0", 0), str(tmp_path / "bad.maxpat"))
        assert not (tmp_path / "bad.maxpat").exists()


class TestGraphRejectsNegativePorts:

    def test_negative_port_edge_skipped(self):
        graph = PatchGraph.build(_patch(-1, 0))
        top = graph.top
        assert all(e.outlet >= 0 and e.inlet >= 0 for e in top.edges)
        assert len(top.edges) == 2
