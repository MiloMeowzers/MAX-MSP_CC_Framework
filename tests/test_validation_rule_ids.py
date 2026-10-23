"""Structured identity on ValidationResult (quick 261022-ud6 WP1; Q7 / Q33
gap, review-validation IN-01).

Q33 gave CriticResult ``rule`` / ``box_ids`` / ``port``; validation results
had only their text, so the save gate keyed blockers on a normalised text
template. Every result ``validate_patch`` emits now carries a stable
``rule`` and the ``box_ids`` it is about, so ``(rule, box_ids, port, path)``
identifies a finding independently of its wording.
"""

from __future__ import annotations

import copy
import glob
import json
import warnings
from pathlib import Path

import pytest

from src.maxpat import walk
from src.maxpat.db_lookup import ObjectDatabase
from src.maxpat.validation import ValidationResult, validate_patch
from tests.test_validation import _make_box, _make_line, _make_patch_dict

_REPO = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def db():
    return ObjectDatabase()


def _scope_ids(patch: dict) -> dict:
    """path key -> set of box ids in that scope."""
    out: dict = {}
    for path, inner, _ctx in walk.iter_patchers(patch):
        ids = set()
        for entry in inner.get("boxes", []) if isinstance(inner, dict) else []:
            box = entry.get("box") if isinstance(entry, dict) else None
            if isinstance(box, dict) and "id" in box:
                ids.add(box["id"])
        out[walk.path_ids(path) if path else ""] = ids
    return out


def _many_findings_patch() -> dict:
    boxes = [
        _make_box("obj-1", text="cycle~ 440", numinlets=2, numoutlets=1),
        _make_box("obj-2", text="print", numinlets=1, numoutlets=0, outlettype=[]),
        _make_box("obj-3", text="osc~ 440", numinlets=2, numoutlets=1),
        _make_box("obj-4", text="frobnicate", numinlets=1, numoutlets=1, outlettype=[""]),
        _make_box("obj-5", text="*~ 2.", numinlets=2, numoutlets=1),
        _make_box("obj-6", text="dac~", numinlets=2, numoutlets=0, outlettype=[]),
        _make_box("obj-7", maxclass="cycle~", text="cycle~", numinlets=2, numoutlets=1),
        _make_box("obj-8", text="buffer~ slot-#1", numinlets=1, numoutlets=2,
                  outlettype=["float", "bang"]),
    ]
    lines = [
        _make_line("obj-1", 0, "obj-2", 0),      # signal -> control-only
        _make_line("obj-1", 3, "obj-2", 0),      # outlet out of bounds
        _make_line("obj-1", 0, "obj-9", 0),      # missing box
        _make_line("obj-1", "0", "obj-2", 0),    # malformed
        _make_line("obj-1", 0, "obj-5", 0),
        _make_line("obj-5", 0, "obj-6", 0),
    ]
    return _make_patch_dict(boxes=boxes, lines=lines)


def _check_identity(results, patch):
    scopes = _scope_ids(patch)
    bad = []
    for r in results:
        if not r.rule:
            bad.append(("no rule", str(r)))
            continue
        ids = scopes.get(r.path, set())
        for i in r.box_ids:
            if i not in ids and r.rule not in ("missing_box", "malformed_patchline"):
                bad.append(("unknown id", i, str(r)))
        if r.proposed_removal is not None and r.rule != "malformed_patchline":
            src, _o, dst, _i = r.proposed_removal
            assert set(r.box_ids) <= {src, dst}, r
    return bad


class TestEveryResultHasARule:

    def test_synthetic_patch(self, db):
        patch = _many_findings_patch()
        results = validate_patch(copy.deepcopy(patch), db=db)
        rules = {r.rule for r in results}
        assert {"signal_to_control_inlet", "outlet_out_of_bounds", "missing_box",
                "malformed_patchline", "pd_object", "unknown_object",
                "unsafe_gain_value", "wrong_maxclass",
                "compound_arg_substitution"} <= rules, rules
        assert _check_identity(results, patch) == []

    def test_cord_identity(self, db):
        patch = _many_findings_patch()
        [r] = [r for r in validate_patch(patch, db=db)
               if r.rule == "signal_to_control_inlet"]
        assert r.box_ids == ("obj-1", "obj-2")
        assert r.port is None

    @pytest.mark.parametrize("rel", sorted(
        p for p in glob.glob(str(_REPO / "patches/**/*.maxpat"), recursive=True)
    ))
    def test_committed_patches(self, db, rel):
        patch = json.loads(Path(rel).read_text())
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            results = validate_patch(copy.deepcopy(patch), db=db)
        assert _check_identity(results, patch) == []

    def test_nested_results_keep_rule_and_ids(self, db):
        inner = _many_findings_patch()["patcher"]
        outer = _make_patch_dict(boxes=[{"box": {
            "id": "obj-90", "maxclass": "newobj", "text": "p sub",
            "numinlets": 0, "numoutlets": 0, "patching_rect": [0, 0, 50, 22],
            "patcher": inner,
        }}])
        nested = [r for r in validate_patch(outer, db=db) if r.path == "obj-90"]
        assert nested and all(r.rule for r in nested)
        [r] = [r for r in nested if r.rule == "signal_to_control_inlet"]
        assert r.box_ids == ("obj-1", "obj-2")


class TestConstructor:

    def test_defaults_back_compatible(self):
        r = ValidationResult("domain", "warning", "x")
        assert (r.rule, r.box_ids, r.port) == ("", (), None)

    def test_box_ids_dedup_and_filter(self):
        r = ValidationResult("domain", "warning", "x", rule="r",
                             box_ids=("obj-1", None, "?", "obj-1", "", "obj-2"))
        assert r.box_ids == ("obj-1", "obj-2")
