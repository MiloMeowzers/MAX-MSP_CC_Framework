"""WP7a (quick 261022-ud6): save-path plumbing handoffs (WP1 / WP2 / WP4).

* Q22 tabs decision: an error on generated / edited codebox code, a warning
  on tab lines already present in a loaded codebox. ``validate_patch``
  Layer 5 takes ``original=`` (the loaded patch) and forwards each
  codebox's baseline code to ``validate_genexpr(original=...)``; the save
  gate passes its baseline on both sides; ``validate_file`` and
  ``validate_code_file`` treat the file on disk as loaded.
* ``_edit_gendsp_in_place`` (WP4 IN-02): codebox numinlets is
  ``max(1, n_in)``, and a 0-input codebox's 1 inlet is not a port, so an
  edit never adds a spurious ``in 1``.
* Q23 D3 on the save path (WP1 -> WP2): ``patch_path`` reaches
  ``validate_patch`` from the save gate and from ``validate_file``.
"""
from __future__ import annotations

import copy
import json
import warnings
from pathlib import Path

import pytest

from src.maxpat.hooks import (
    PatchValidationError,
    _gate_report,
    save_patch_roundtrip,
    validate_code_file,
    validate_file,
    write_gendsp,
)
from src.maxpat.validation import validate_patch

TABBED = "x = in1 * 0.5;\n\tout1 = x;\n"


def _gen_patch(code: str, container_id: str = "obj-1") -> dict:
    inner = {"boxes": [{"box": {
        "id": "obj-1", "maxclass": "codebox", "code": code,
        "numinlets": 1, "numoutlets": 1, "outlettype": [""],
        "patching_rect": [10, 10, 200, 100],
    }}], "lines": []}
    return {"patcher": {"boxes": [{"box": {
        "id": container_id, "maxclass": "newobj", "text": "gen~",
        "numinlets": 1, "numoutlets": 1, "outlettype": ["signal"],
        "patching_rect": [10, 10, 60, 22], "patcher": inner,
    }}], "lines": []}}


def _nested(code: str) -> dict:
    gen = _gen_patch(code, "obj-7")["patcher"]
    return {"patcher": {"boxes": [{"box": {
        "id": "obj-3", "maxclass": "newobj", "text": "p voice",
        "numinlets": 0, "numoutlets": 0, "outlettype": [],
        "patching_rect": [10, 10, 60, 22], "patcher": gen,
    }}], "lines": []}}


def _tabs(results, level):
    return [r for r in results if "Tab character" in r.message and r.level == level]


class TestLayer5Original:
    def test_no_original_tabs_error(self):
        assert _tabs(validate_patch(_gen_patch(TABBED)), "error")

    def test_loaded_tabs_warn(self):
        d = _gen_patch(TABBED)
        res = validate_patch(d, original=copy.deepcopy(d))
        assert not _tabs(res, "error")
        assert len(_tabs(res, "warning")) == 1

    def test_new_tab_line_in_loaded_codebox_errors(self):
        base = _gen_patch(TABBED)
        edited = _gen_patch(TABBED + "\tout1 = x * 2;\n")
        res = validate_patch(edited, original=base)
        assert len(_tabs(res, "error")) == 1
        assert len(_tabs(res, "warning")) == 1

    def test_nested_codebox_matched_by_path(self):
        d = _nested(TABBED)
        res = validate_patch(d, original=copy.deepcopy(d))
        assert not _tabs(res, "error") and _tabs(res, "warning")

    def test_other_container_is_not_the_original(self):
        """The tab line was in obj-1's codebox; obj-2's new codebox gets it fresh."""
        base = _gen_patch(TABBED, "obj-1")
        moved = _gen_patch(TABBED, "obj-2")
        assert _tabs(validate_patch(moved, original=base), "error")

    def test_original_accepts_patcher(self):
        from src.maxpat.patcher import Patcher

        d = _gen_patch(TABBED)
        res = validate_patch(d, original=Patcher.from_dict(copy.deepcopy(d)))
        assert not _tabs(res, "error")


class TestSaveGateTabs:
    def test_new_tab_line_in_tabbed_codebox_is_a_new_blocker(self):
        base = _gen_patch(TABBED)
        edited = _gen_patch(TABBED + "\tout1 = x * 2;\n")
        report = _gate_report(edited, base, [base])
        assert any("Tab character" in getattr(r, "message", "") for r in report.new_blockers)

    def test_untouched_tabbed_codebox_saves(self):
        base = _gen_patch(TABBED)
        edited = copy.deepcopy(base)
        edited["patcher"]["boxes"][0]["box"]["patching_rect"] = [40, 40, 60, 22]
        assert _gate_report(edited, base, [base]).new_blockers == []

    def test_save_roundtrip_of_loaded_tabbed_patch(self, tmp_path):
        p = tmp_path / "t.maxpat"
        text = json.dumps(_gen_patch(TABBED), indent=4)
        p.write_text(text)
        d = json.loads(text)
        d["patcher"]["boxes"][0]["box"]["patching_rect"] = [50, 50, 60, 22]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            save_patch_roundtrip(d, p, text)
        assert json.loads(p.read_text())["patcher"]["boxes"][0]["box"]["patching_rect"][0] == 50


class TestFilesFromDisk:
    def test_validate_file_treats_disk_codebox_as_loaded(self, tmp_path):
        p = tmp_path / "t.maxpat"
        p.write_text(json.dumps(_gen_patch(TABBED)))
        res = validate_file(p)
        assert not _tabs(res, "error") and _tabs(res, "warning")

    def _gendsp(self, tmp_path, code):
        from src.maxpat.codegen import generate_gendsp

        p = tmp_path / "t.gendsp"
        p.write_text(json.dumps(generate_gendsp(code)))
        return p

    def test_validate_code_file_loaded_tabs_warn(self, tmp_path):
        res = validate_code_file(self._gendsp(tmp_path, TABBED))
        assert not _tabs(res, "error") and _tabs(res, "warning")

    def test_validate_code_file_loaded_false_errors(self, tmp_path):
        res = validate_code_file(self._gendsp(tmp_path, TABBED), loaded=False)
        assert _tabs(res, "error")


class TestGendspInletCount:
    def _boxes(self, p):
        return [b["box"] for b in json.loads(p.read_text())["patcher"]["boxes"]]

    def test_zero_input_edit_adds_no_in_port(self, tmp_path):
        p = tmp_path / "z.gendsp"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            write_gendsp("out1 = noise();", p)
            write_gendsp("out1 = noise() * 0.5;", p)
        boxes = self._boxes(p)
        assert not [b for b in boxes if str(b.get("text", "")).startswith("in ")]
        (cb,) = [b for b in boxes if b["maxclass"] == "codebox"]
        assert cb["numinlets"] == 1

    def test_explicit_zero_inputs_keeps_one_inlet(self, tmp_path):
        p = tmp_path / "z.gendsp"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            write_gendsp("out1 = in1;", p)
            write_gendsp("out1 = noise();", p, num_inputs=0)
        boxes = self._boxes(p)
        (cb,) = [b for b in boxes if b["maxclass"] == "codebox"]
        assert cb["numinlets"] == 1
        assert not [b for b in boxes if str(b.get("text", "")).startswith("in ")]

    def test_wired_input_still_kept(self, tmp_path):
        """WR-08 unchanged: code that stops reading in1 keeps ``in 1``."""
        p = tmp_path / "w.gendsp"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            write_gendsp("out1 = in1;", p)
            write_gendsp("out1 = noise();", p)
        assert [b for b in self._boxes(p) if b.get("text") == "in 1"]


def _unknown_patch() -> dict:
    return {"patcher": {"boxes": [{"box": {
        "id": "obj-1", "maxclass": "newobj", "text": "zzmyabstraction 1",
        "numinlets": 1, "numoutlets": 1, "outlettype": [""],
        "patching_rect": [10, 10, 100, 22],
    }}], "lines": []}}


class TestPatchPathOnSavePath:
    def test_validate_file_unknown_is_error(self, tmp_path):
        p = tmp_path / "host.maxpat"
        p.write_text(json.dumps(_unknown_patch()))
        res = [r for r in validate_file(p) if r.rule == "unknown_object"]
        assert res and res[0].level == "error"

    def test_validate_file_resolves_abstraction_beside(self, tmp_path):
        p = tmp_path / "host.maxpat"
        p.write_text(json.dumps(_unknown_patch()))
        (tmp_path / "zzmyabstraction.maxpat").write_text(json.dumps({"patcher": {"boxes": [], "lines": []}}))
        assert not [r for r in validate_file(p) if r.rule == "unknown_object"]

    def test_save_gate_refuses_unresolved_name_in_new_file(self, tmp_path):
        with pytest.raises(PatchValidationError):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                save_patch_roundtrip(_unknown_patch(), tmp_path / "host.maxpat")

    def test_save_gate_accepts_abstraction_beside(self, tmp_path):
        (tmp_path / "zzmyabstraction.maxpat").write_text(json.dumps({"patcher": {"boxes": [], "lines": []}}))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            save_patch_roundtrip(_unknown_patch(), tmp_path / "host.maxpat")
        assert (tmp_path / "host.maxpat").exists()
