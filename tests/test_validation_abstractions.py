"""IN-02 (review-validation, quick 261022-ud6 WP1): unknown-object findings for
abstractions that sit beside the patch.

Q19 recursion made nested scopes report ``Unknown object`` for
``terrain-osc`` / ``terrain-osc-b`` / ``terrain-lfo`` -- .maxpat
abstractions in ``patches/terrain-synth/generated/``. The fix is the
fix-plan Q23 D3 abstraction lookup: ``validate_patch(..., patch_path=p)``
resolves NAME.maxpat / NAME.js / NAME.gendsp in p's directory (and, under
``patches/<project>/``, anywhere in the project) and then reports nothing;
an unresolved unknown on that path is an error. Without patch_path the old
warning is byte-identical.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from src.maxpat.db_lookup import ObjectDatabase
from src.maxpat.validation import _project_abstractions, validate_patch
from tests.test_validation import _make_box, _make_patch_dict

_REPO = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def db():
    return ObjectDatabase()


def _unknown(results):
    return [r for r in results if r.message.startswith("Unknown object")
            or "Unknown object" in r.message]


def _one_box(text="zzabs"):
    return _make_patch_dict(boxes=[
        _make_box("obj-1", text=text, numinlets=1, numoutlets=1, outlettype=[""]),
    ])


def _write(path: Path, text="{}"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


class TestPatchPath:

    def test_without_patch_path_warning_is_unchanged(self, db):
        [r] = _unknown(validate_patch(_one_box(), db=db))
        assert r.level == "warning"
        assert r.message == "Unknown object: 'zzabs' -- not in database"

    def test_unresolved_with_patch_path_is_an_error(self, db, tmp_path):
        top = _write(tmp_path / "a" / "top.maxpat")
        [r] = _unknown(validate_patch(_one_box(), db=db, patch_path=top))
        assert r.level == "error"
        assert r.message.startswith("Unknown object: 'zzabs' (obj-1) -- not in database")
        assert "No such object" in r.message
        assert r.rule == "unknown_object" and r.box_ids == ("obj-1",)

    @pytest.mark.parametrize("fname", ["zzabs.maxpat", "zzabs.js", "zzabs.gendsp", "ZZabs.maxpat"])
    def test_abstraction_beside_the_patch_resolves(self, db, tmp_path, fname):
        top = _write(tmp_path / "a" / "top.maxpat")
        _write(tmp_path / "a" / fname)
        assert _unknown(validate_patch(_one_box(), db=db, patch_path=top)) == []

    def test_project_tree_resolves_sibling_project_does_not(self, db, tmp_path):
        top = _write(tmp_path / "patches" / "proj" / "generated" / "top.maxpat")
        _write(tmp_path / "patches" / "proj" / "abstractions" / "zzabs.maxpat")
        assert _unknown(validate_patch(_one_box(), db=db, patch_path=top)) == []
        other = _write(tmp_path / "patches" / "other" / "top.maxpat")
        assert len(_unknown(validate_patch(_one_box(), db=db, patch_path=other))) == 1

    def test_nested_unknown_gets_prefixed_error(self, db, tmp_path):
        top = _write(tmp_path / "a" / "top.maxpat")
        inner = _one_box()["patcher"]
        outer = _make_patch_dict(boxes=[{"box": {
            "id": "obj-9", "maxclass": "newobj", "text": "p x",
            "numinlets": 0, "numoutlets": 0, "patching_rect": [0, 0, 40, 22],
            "patcher": inner,
        }}])
        [r] = _unknown(validate_patch(outer, db=db, patch_path=top))
        assert r.level == "error" and r.path == "obj-9"
        assert r.message.startswith("[p x] Unknown object: 'zzabs' (obj-1)")

    def test_pd_and_ui_names_unchanged(self, db, tmp_path):
        top = _write(tmp_path / "a" / "top.maxpat")
        pd = validate_patch(_one_box("osc~ 440"), db=db, patch_path=top)
        assert [r.message for r in pd if "Pure Data" in r.message]
        assert _unknown(pd) == []

    def test_missing_directory_never_raises(self, tmp_path):
        assert _project_abstractions(tmp_path / "nope" / "x.maxpat") == frozenset()


class TestTerrainSynth:
    """The review's IN-02 instance: 7 nested warnings on two committed patches."""

    @pytest.mark.parametrize("rel", [
        "patches/terrain-synth/generated/terrain-synth.maxpat",
        "patches/terrain-synth/generated/terrain-voice.maxpat",
    ])
    def test_sibling_abstractions_resolve(self, db, rel):
        path = _REPO / rel
        patch = json.loads(path.read_text())
        assert _unknown(validate_patch(copy.deepcopy(patch), db=db)), "precondition"
        assert _unknown(validate_patch(patch, db=db, patch_path=path)) == []
