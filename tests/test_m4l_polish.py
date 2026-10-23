"""Tests for M4L polish -- parameter naming intelligence.

Covers POLISH-01: auto-derive longname, shortname, varname for M4L
live.* controls. Tests verify D-01 (preserve existing), D-02 (longname
from varname), D-03 (shortname abbreviation), D-04 (varname from longname).
"""

from __future__ import annotations

import copy
import re
import warnings

import pytest

from src.maxpat.utils import get_box_name


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_live_control(
    box_id: str = "obj-1",
    maxclass: str = "live.dial",
    varname: str | None = None,
    longname: str | None = None,
    shortname: str | None = None,
    parameter_enable: int = 1,
    text: str | None = None,
) -> dict:
    """Build a live.* control box dict with configurable naming."""
    box: dict = {
        "id": box_id,
        "maxclass": maxclass,
        "numinlets": 1,
        "numoutlets": 2,
        "outlettype": ["", "float"],
        "parameter_enable": parameter_enable,
    }
    if varname is not None:
        box["varname"] = varname
    if text is not None:
        box["text"] = text

    # Build saved_attribute_attributes.valueof if any param name is set
    valueof: dict = {}
    if longname is not None:
        valueof["parameter_longname"] = longname
    if shortname is not None:
        valueof["parameter_shortname"] = shortname
    if valueof:
        box["saved_attribute_attributes"] = {"valueof": valueof}

    return box


def _banks(patch: dict) -> list[dict]:
    """Push banks in MAX's storage, patcher.parameters.parameterbanks, in order."""
    pb = patch["patcher"]["parameters"]["parameterbanks"]
    return [pb[k] for k in sorted(pb, key=int)]


def _banks_box(patch: dict) -> dict | None:
    """The live.banks box in either form (newobj text or legacy maxclass)."""
    for entry in patch["patcher"]["boxes"]:
        box = entry.get("box", entry)
        if get_box_name(box) == "live.banks":
            return box
    return None


def _walk_keys(obj):
    """Yield every dict key in a nested JSON-like structure."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _walk_keys(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk_keys(v)


def _make_patch_with_controls(controls: list[dict], **patcher_props) -> dict:
    """Wrap control box dicts in proper patch_dict structure."""
    patcher = {
        "boxes": [{"box": c} for c in controls],
        "lines": [],
    }
    patcher.update(patcher_props)
    return {"patcher": patcher}


# ===========================================================================
# TestNameDerivation -- POLISH-01
# ===========================================================================

class TestNameDerivation:
    """Test derive_parameter_names auto-derives longname/shortname/varname."""

    def test_longname_from_varname(self):
        """D-02: box with varname="filter_cutoff", no longname -> longname "Filter Cutoff"."""
        from src.maxpat.m4l_polish import derive_parameter_names

        ctrl = _make_live_control(varname="filter_cutoff")
        patch = _make_patch_with_controls([ctrl])
        derive_parameter_names(patch)

        valueof = patch["patcher"]["boxes"][0]["box"]["saved_attribute_attributes"]["valueof"]
        assert valueof["parameter_longname"] == "Filter Cutoff"

    def test_longname_from_box_text(self):
        """Box with no varname, text="live.dial pitch_start" -> longname from text tokens."""
        from src.maxpat.m4l_polish import derive_parameter_names

        ctrl = _make_live_control(text="live.dial pitch_start")
        patch = _make_patch_with_controls([ctrl])
        derive_parameter_names(patch)

        valueof = patch["patcher"]["boxes"][0]["box"]["saved_attribute_attributes"]["valueof"]
        # Should derive from "pitch_start" token
        assert valueof["parameter_longname"] == "Pitch Start"

    def test_shortname_abbreviation(self):
        """D-03: longname="Filter Frequency" -> shortname abbreviates words."""
        from src.maxpat.m4l_polish import derive_parameter_names

        ctrl = _make_live_control(longname="Filter Frequency")
        patch = _make_patch_with_controls([ctrl])
        derive_parameter_names(patch)

        valueof = patch["patcher"]["boxes"][0]["box"]["saved_attribute_attributes"]["valueof"]
        short = valueof["parameter_shortname"]
        assert "Filt" in short or "Freq" in short
        assert len(short) <= 8

    def test_shortname_truncation(self):
        """Shortname never exceeds 8 characters even after abbreviation."""
        from src.maxpat.m4l_polish import derive_parameter_names

        ctrl = _make_live_control(longname="Modulation Depth Amount")
        patch = _make_patch_with_controls([ctrl])
        derive_parameter_names(patch)

        valueof = patch["patcher"]["boxes"][0]["box"]["saved_attribute_attributes"]["valueof"]
        assert len(valueof["parameter_shortname"]) <= 8

    def test_shortname_short_already(self):
        """longname="Pan" -> shortname="Pan" (no abbreviation needed)."""
        from src.maxpat.m4l_polish import derive_parameter_names

        ctrl = _make_live_control(longname="Pan")
        patch = _make_patch_with_controls([ctrl])
        derive_parameter_names(patch)

        valueof = patch["patcher"]["boxes"][0]["box"]["saved_attribute_attributes"]["valueof"]
        assert valueof["parameter_shortname"] == "Pan"

    def test_varname_from_longname(self):
        """D-04: longname="Filter Cutoff", no varname -> varname="filter_cutoff"."""
        from src.maxpat.m4l_polish import derive_parameter_names

        ctrl = _make_live_control(longname="Filter Cutoff")
        patch = _make_patch_with_controls([ctrl])
        derive_parameter_names(patch)

        box = patch["patcher"]["boxes"][0]["box"]
        assert box["varname"] == "filter_cutoff"

    def test_preserves_existing_longname(self):
        """D-01: box already has longname="My Custom Name" -> not overridden."""
        from src.maxpat.m4l_polish import derive_parameter_names

        ctrl = _make_live_control(
            varname="some_var",
            longname="My Custom Name",
        )
        patch = _make_patch_with_controls([ctrl])
        derive_parameter_names(patch)

        valueof = patch["patcher"]["boxes"][0]["box"]["saved_attribute_attributes"]["valueof"]
        assert valueof["parameter_longname"] == "My Custom Name"

    def test_preserves_existing_shortname(self):
        """D-01: box already has shortname="Custom" -> not overridden."""
        from src.maxpat.m4l_polish import derive_parameter_names

        ctrl = _make_live_control(
            longname="Some Long Name",
            shortname="Custom",
        )
        patch = _make_patch_with_controls([ctrl])
        derive_parameter_names(patch)

        valueof = patch["patcher"]["boxes"][0]["box"]["saved_attribute_attributes"]["valueof"]
        assert valueof["parameter_shortname"] == "Custom"

    def test_preserves_existing_varname(self):
        """D-01: box already has varname="my_var" -> not overridden."""
        from src.maxpat.m4l_polish import derive_parameter_names

        ctrl = _make_live_control(
            varname="my_var",
            longname="Filter Cutoff",
        )
        patch = _make_patch_with_controls([ctrl])
        derive_parameter_names(patch)

        box = patch["patcher"]["boxes"][0]["box"]
        assert box["varname"] == "my_var"

    def test_skips_non_parameter_live_objects(self):
        """live.thisdevice, live.banks etc. untouched."""
        from src.maxpat.m4l_polish import derive_parameter_names

        boxes = [
            {
                "id": "obj-1",
                "maxclass": "live.thisdevice",
                "numinlets": 1,
                "numoutlets": 2,
                "outlettype": ["", ""],
            },
            {
                "id": "obj-2",
                "maxclass": "live.banks",
                "numinlets": 1,
                "numoutlets": 1,
                "outlettype": [""],
            },
        ]
        patch = _make_patch_with_controls(boxes)
        # Should not raise, and should not add any parameter naming attributes
        derive_parameter_names(patch)
        for box_entry in patch["patcher"]["boxes"]:
            box = box_entry["box"]
            assert "saved_attribute_attributes" not in box or \
                "valueof" not in box.get("saved_attribute_attributes", {}) or \
                "parameter_longname" not in box["saved_attribute_attributes"]["valueof"]

    def test_recurses_into_subpatchers(self):
        """live.dial inside a subpatcher gets names derived."""
        from src.maxpat.m4l_polish import derive_parameter_names

        inner_ctrl = _make_live_control(
            box_id="sub-obj-1",
            varname="reverb_size",
        )
        subpatcher_box = {
            "id": "obj-2",
            "maxclass": "newobj",
            "text": "p effects",
            "numinlets": 1,
            "numoutlets": 1,
            "outlettype": [""],
            "patcher": {
                "boxes": [{"box": inner_ctrl}],
                "lines": [],
            },
        }
        patch = {
            "patcher": {
                "boxes": [{"box": subpatcher_box}],
                "lines": [],
            },
        }
        derive_parameter_names(patch)

        inner_box = patch["patcher"]["boxes"][0]["box"]["patcher"]["boxes"][0]["box"]
        valueof = inner_box["saved_attribute_attributes"]["valueof"]
        assert valueof["parameter_longname"] == "Reverb Size"

    def test_no_duplicate_longnames(self):
        """If derivation would create duplicate longname, append index suffix."""
        from src.maxpat.m4l_polish import derive_parameter_names

        ctrl1 = _make_live_control(
            box_id="obj-1",
            varname="filter_cutoff",
        )
        ctrl2 = _make_live_control(
            box_id="obj-2",
            varname="filter_cutoff",
        )
        patch = _make_patch_with_controls([ctrl1, ctrl2])
        derive_parameter_names(patch)

        boxes = patch["patcher"]["boxes"]
        ln1 = boxes[0]["box"]["saved_attribute_attributes"]["valueof"]["parameter_longname"]
        ln2 = boxes[1]["box"]["saved_attribute_attributes"]["valueof"]["parameter_longname"]
        assert ln1 != ln2
        # One should be base name, other should have suffix
        assert "Filter Cutoff" in ln1 or "Filter Cutoff" in ln2


# ===========================================================================
# TestPushBanks -- POLISH-02
# ===========================================================================

def _make_named_control(
    box_id: str,
    longname: str,
    maxclass: str = "live.dial",
    unitstyle: int | None = None,
    mmin: float | None = None,
    mmax: float | None = None,
) -> dict:
    """Build a live.* control with parameter_longname already set.

    Used for bank tests where naming has already run.
    """
    valueof: dict = {"parameter_longname": longname}
    if unitstyle is not None:
        valueof["parameter_unitstyle"] = unitstyle
    if mmin is not None:
        valueof["parameter_mmin"] = mmin
    if mmax is not None:
        valueof["parameter_mmax"] = mmax
    return {
        "id": box_id,
        "maxclass": maxclass,
        "numinlets": 1,
        "numoutlets": 2,
        "outlettype": ["", "float"],
        "parameter_enable": 1,
        "saved_attribute_attributes": {"valueof": valueof},
    }


class TestPushBanks:
    """Test organize_push_banks groups parameters into semantic Push banks."""

    def test_semantic_grouping(self):
        """D-05: 3 pitch params + 2 filter params -> 2 separate banks."""
        from src.maxpat.m4l_polish import organize_push_banks

        controls = [
            _make_named_control("obj-1", "Pitch Start"),
            _make_named_control("obj-2", "Pitch End"),
            _make_named_control("obj-3", "Pitch Decay"),
            _make_named_control("obj-4", "Filter Cutoff"),
            _make_named_control("obj-5", "Filter Resonance"),
        ]
        patch = _make_patch_with_controls(controls)
        organize_push_banks(patch)

        # Find live.banks box
        banks_box = _banks_box(patch)
        assert banks_box is not None, "live.banks box not found"

        banks = _banks(patch)
        bank_names = [b["name"] for b in banks]
        assert "Pitch" in bank_names
        assert "Filter" in bank_names
        # Pitch and Filter in different banks
        pitch_bank = next(b for b in banks if b["name"] == "Pitch")
        filter_bank = next(b for b in banks if b["name"] == "Filter")
        assert "Pitch Start" in pitch_bank["parameters"]
        assert "Filter Cutoff" in filter_bank["parameters"]

    def test_bank_padding(self):
        """D-07: bank with 3 params -> padded with 5 '-' slots to fill 8."""
        from src.maxpat.m4l_polish import organize_push_banks

        controls = [
            _make_named_control("obj-1", "Pitch Start"),
            _make_named_control("obj-2", "Pitch End"),
            _make_named_control("obj-3", "Pitch Decay"),
        ]
        patch = _make_patch_with_controls(controls)
        organize_push_banks(patch)

        banks_box = _banks_box(patch)
        assert banks_box is not None

        bank = _banks(patch)[0]
        assert len(bank["parameters"]) == 8
        assert bank["parameters"].count("-") == 5

    def test_bank_naming(self):
        """D-06: bank containing Cutoff/Resonance/Drive -> name 'Filter'."""
        from src.maxpat.m4l_polish import organize_push_banks

        controls = [
            _make_named_control("obj-1", "Cutoff"),
            _make_named_control("obj-2", "Resonance"),
            _make_named_control("obj-3", "Drive"),
        ]
        patch = _make_patch_with_controls(controls)
        organize_push_banks(patch)

        banks_box = _banks_box(patch)
        assert banks_box is not None

        bank = _banks(patch)[0]
        assert bank["name"] == "Filter"

    def test_bank_naming_amp(self):
        """Bank containing Amp Decay/Amp Curve/Body Level -> name 'Amp'."""
        from src.maxpat.m4l_polish import organize_push_banks

        controls = [
            _make_named_control("obj-1", "Amp Decay"),
            _make_named_control("obj-2", "Amp Curve"),
            _make_named_control("obj-3", "Body Level"),
        ]
        patch = _make_patch_with_controls(controls)
        organize_push_banks(patch)

        banks_box = _banks_box(patch)
        assert banks_box is not None

        bank = _banks(patch)[0]
        assert bank["name"] == "Amp"

    def test_banks_of_eight(self):
        """10 params in same group -> split into 2 banks (8 + 2 padded)."""
        from src.maxpat.m4l_polish import organize_push_banks

        controls = [
            _make_named_control(f"obj-{i}", f"Filter Param {i}")
            for i in range(10)
        ]
        patch = _make_patch_with_controls(controls)
        organize_push_banks(patch)

        banks_box = _banks_box(patch)
        assert banks_box is not None

        banks = _banks(patch)
        filter_banks = [b for b in banks if b["name"].startswith("Filter")]
        assert len(filter_banks) == 2
        assert len(filter_banks[0]["parameters"]) == 8
        assert len(filter_banks[1]["parameters"]) == 8
        # Second bank should be padded
        non_dash = [p for p in filter_banks[1]["parameters"] if p != "-"]
        assert len(non_dash) == 2

    def test_main_fallback(self):
        """Params with no keyword match -> bank named 'Main'."""
        from src.maxpat.m4l_polish import organize_push_banks

        controls = [
            _make_named_control("obj-1", "Brightness"),
            _make_named_control("obj-2", "Warmth"),
        ]
        patch = _make_patch_with_controls(controls)
        organize_push_banks(patch)

        banks_box = _banks_box(patch)
        assert banks_box is not None

        bank = _banks(patch)[0]
        assert bank["name"] == "Main"

    def test_live_banks_box_created(self):
        """If no live.banks box exists, one is added to patch."""
        from src.maxpat.m4l_polish import organize_push_banks

        controls = [_make_named_control("obj-1", "Filter Cutoff")]
        patch = _make_patch_with_controls(controls)
        # Verify no live.banks exists before
        assert _banks_box(patch) is None

        organize_push_banks(patch)

        created = _banks_box(patch)
        assert created is not None, "live.banks box should have been created"
        # MAX saves live.banks as a newobj (help/m4l/live.banks.maxhelp);
        # maxclass "live.banks" is refused by validate_patch.
        assert created["maxclass"] == "newobj"
        assert created["text"] == "live.banks"

    def test_live_banks_box_reused(self):
        """An existing live.banks is reused and its stale _parameter_banks dropped."""
        from src.maxpat.m4l_polish import organize_push_banks

        existing_banks_box = {
            "id": "obj-banks",
            "maxclass": "live.banks",
            "numinlets": 1,
            "numoutlets": 1,
            "outlettype": [""],
            "patching_rect": [20.0, 20.0, 315.0, 45.0],
            "_parameter_banks": {"banks": []},
        }
        controls = [_make_named_control("obj-1", "Filter Cutoff")]
        patch = _make_patch_with_controls(controls + [existing_banks_box])
        organize_push_banks(patch)

        # Should still have only one live.banks box
        banks_boxes = [
            entry.get("box", entry)
            for entry in patch["patcher"]["boxes"]
            if get_box_name(entry.get("box", entry)) == "live.banks"
        ]
        assert len(banks_boxes) == 1
        assert "_parameter_banks" not in banks_boxes[0]
        assert len(_banks(patch)) > 0

    def test_reuses_newobj_live_banks(self):
        """An existing newobj-form live.banks is reused, not duplicated."""
        from src.maxpat.m4l_polish import organize_push_banks

        existing = {
            "id": "obj-banks",
            "maxclass": "newobj",
            "text": "live.banks",
            "numinlets": 1,
            "numoutlets": 1,
            "outlettype": [""],
            "patching_rect": [20.0, 20.0, 70.0, 22.0],
        }
        controls = [_make_named_control("obj-1", "Filter Cutoff")]
        patch = _make_patch_with_controls(controls + [existing])
        organize_push_banks(patch)

        banks_boxes = [
            entry["box"] for entry in patch["patcher"]["boxes"]
            if get_box_name(entry["box"]) == "live.banks"
        ]
        assert banks_boxes == [existing]
        assert _banks(patch)[0]["parameters"][0] == "Filter Cutoff"

    def test_parameterbanks_shape(self):
        """(a) MAX's saved shape: string keys, index/name/parameters x 8."""
        from src.maxpat.m4l_polish import organize_push_banks

        patch = _make_patch_with_controls(
            [_make_named_control("obj-1", "Filter Cutoff")]
        )
        organize_push_banks(patch)

        assert patch["patcher"]["parameters"]["parameterbanks"] == {
            "0": {
                "index": 0,
                "name": "Filter",
                "parameters": ["Filter Cutoff", "-", "-", "-",
                               "-", "-", "-", "-"],
            },
        }

    def test_parameters_siblings_preserved(self):
        """(b) Other keys under patcher.parameters survive."""
        from src.maxpat.m4l_polish import organize_push_banks

        patch = _make_patch_with_controls(
            [_make_named_control("obj-1", "Filter Cutoff")],
            parameters={"obj-20": ["Cutoff", "Cut", 0], "inherited_shortname": 1},
        )
        organize_push_banks(patch)

        params = patch["patcher"]["parameters"]
        assert params["obj-20"] == ["Cutoff", "Cut", 0]
        assert params["inherited_shortname"] == 1
        assert "parameterbanks" in params

    def test_max_placeholder_bank_replaced(self):
        """(c) MAX's all-'-' default bank is replaced by the computed banks."""
        from src.maxpat.m4l_polish import organize_push_banks

        patch = _make_patch_with_controls(
            [_make_named_control("obj-1", "Filter Cutoff")],
            parameters={"parameterbanks": {
                "0": {"index": 0, "name": "", "parameters": ["-"] * 8},
            }},
        )
        organize_push_banks(patch)

        banks = _banks(patch)
        assert banks[0]["name"] == "Filter"
        assert banks[0]["parameters"][0] == "Filter Cutoff"

    def test_user_defined_banks_preserved(self):
        """(d) A parameterbanks with any real slot is left untouched (D-01)."""
        from src.maxpat.m4l_polish import organize_push_banks

        user = {
            "0": {"index": 0, "name": "Mine",
                  "parameters": ["Pitch Start", "-", "-", "-",
                                 "-", "-", "-", "-"]},
        }
        patch = _make_patch_with_controls(
            [_make_named_control("obj-1", "Filter Cutoff")],
            parameters={"parameterbanks": copy.deepcopy(user)},
        )
        organize_push_banks(patch)

        assert patch["patcher"]["parameters"]["parameterbanks"] == user

    def test_no_private_bank_key_anywhere(self):
        """(e) No _parameter_banks key anywhere in polished output."""
        from src.maxpat.m4l_polish import polish_m4l_device

        patch = _make_patch_with_controls([
            _make_live_control("obj-1", varname="filter_cutoff"),
            _make_live_control("obj-2", varname="amp_level"),
        ])
        polish_m4l_device(patch)

        assert "_parameter_banks" not in set(_walk_keys(patch))

    def test_empty_device_writes_no_parameterbanks(self):
        """(f) No controls -> patcher gains no parameters key."""
        from src.maxpat.m4l_polish import organize_push_banks

        patch = _make_patch_with_controls([])
        organize_push_banks(patch)
        assert "parameters" not in patch["patcher"]

    def test_params_referenced_by_longname(self):
        """A2: bank parameter entries use parameter_longname values."""
        from src.maxpat.m4l_polish import organize_push_banks

        controls = [_make_named_control("obj-1", "Filter Cutoff")]
        patch = _make_patch_with_controls(controls)
        organize_push_banks(patch)

        banks_box = _banks_box(patch)
        assert banks_box is not None

        bank = _banks(patch)[0]
        assert "Filter Cutoff" in bank["parameters"]

    def test_empty_device_no_banks(self):
        """Device with zero parameters -> no banks created."""
        from src.maxpat.m4l_polish import organize_push_banks

        patch = _make_patch_with_controls([])
        organize_push_banks(patch)

        # Should not have created a live.banks box
        for entry in patch["patcher"]["boxes"]:
            box = entry.get("box", entry)
            assert get_box_name(box) != "live.banks"


# ===========================================================================
# TestInfoText -- POLISH-03
# ===========================================================================

class TestInfoText:
    """Test populate_info_text sets annotation and annotation_name."""

    def test_annotation_set(self):
        """D-08: control with longname, no annotation -> annotation set."""
        from src.maxpat.m4l_polish import populate_info_text

        ctrl = _make_named_control("obj-1", "Filter Cutoff")
        patch = _make_patch_with_controls([ctrl])
        populate_info_text(patch)

        box = patch["patcher"]["boxes"][0]["box"]
        assert box.get("annotation"), "annotation should be set"
        assert "Filter Cutoff" in box["annotation"]

    def test_annotation_name_set(self):
        """Control with longname -> annotation_name set to longname."""
        from src.maxpat.m4l_polish import populate_info_text

        ctrl = _make_named_control("obj-1", "Filter Cutoff")
        patch = _make_patch_with_controls([ctrl])
        populate_info_text(patch)

        box = patch["patcher"]["boxes"][0]["box"]
        assert box.get("annotation_name") == "Filter Cutoff"

    def test_range_formatting_hertz(self):
        """D-09: unitstyle=3 (HERTZ), mmin=20, mmax=20000 -> 'Range: 20-20000 Hz'."""
        from src.maxpat.m4l_polish import populate_info_text

        ctrl = _make_named_control(
            "obj-1", "Filter Cutoff", unitstyle=3, mmin=20.0, mmax=20000.0,
        )
        patch = _make_patch_with_controls([ctrl])
        populate_info_text(patch)

        box = patch["patcher"]["boxes"][0]["box"]
        assert "Range: 20-20000 Hz" in box["annotation"]

    def test_range_formatting_decibel(self):
        """unitstyle=4 (DECIBEL), mmin=-70, mmax=6 -> 'Range: -70-6 dB'."""
        from src.maxpat.m4l_polish import populate_info_text

        ctrl = _make_named_control(
            "obj-1", "Volume", unitstyle=4, mmin=-70.0, mmax=6.0,
        )
        patch = _make_patch_with_controls([ctrl])
        populate_info_text(patch)

        box = patch["patcher"]["boxes"][0]["box"]
        assert "Range: -70-6 dB" in box["annotation"]

    def test_range_formatting_percent(self):
        """unitstyle=5 (PERCENT), mmin=0, mmax=100 -> 'Range: 0-100 %'."""
        from src.maxpat.m4l_polish import populate_info_text

        ctrl = _make_named_control(
            "obj-1", "Mix Level", unitstyle=5, mmin=0.0, mmax=100.0,
        )
        patch = _make_patch_with_controls([ctrl])
        populate_info_text(patch)

        box = patch["patcher"]["boxes"][0]["box"]
        assert "Range: 0-100 %" in box["annotation"]

    def test_range_formatting_midi(self):
        """unitstyle=8 (MIDI) -> 'Range: 0-127 (MIDI)'."""
        from src.maxpat.m4l_polish import populate_info_text

        ctrl = _make_named_control(
            "obj-1", "Note", unitstyle=8, mmin=0.0, mmax=127.0,
        )
        patch = _make_patch_with_controls([ctrl])
        populate_info_text(patch)

        box = patch["patcher"]["boxes"][0]["box"]
        assert "Range: 0-127 (MIDI)" in box["annotation"]

    def test_no_range_when_missing(self):
        """No mmin/mmax -> no 'Range:' in annotation."""
        from src.maxpat.m4l_polish import populate_info_text

        ctrl = _make_named_control("obj-1", "Filter Cutoff")
        patch = _make_patch_with_controls([ctrl])
        populate_info_text(patch)

        box = patch["patcher"]["boxes"][0]["box"]
        assert "Range:" not in box.get("annotation", "")

    def test_preserves_existing_annotation(self):
        """D-10: box with annotation already set -> not overridden."""
        from src.maxpat.m4l_polish import populate_info_text

        ctrl = _make_named_control("obj-1", "Filter Cutoff")
        ctrl["annotation"] = "My custom info text"
        patch = _make_patch_with_controls([ctrl])
        populate_info_text(patch)

        box = patch["patcher"]["boxes"][0]["box"]
        assert box["annotation"] == "My custom info text"

    def test_preserves_existing_annotation_name(self):
        """Box with annotation_name set -> not overridden."""
        from src.maxpat.m4l_polish import populate_info_text

        ctrl = _make_named_control("obj-1", "Filter Cutoff")
        ctrl["annotation_name"] = "Custom Header"
        patch = _make_patch_with_controls([ctrl])
        populate_info_text(patch)

        box = patch["patcher"]["boxes"][0]["box"]
        assert box["annotation_name"] == "Custom Header"

    def test_annotation_is_top_level_box_attr(self):
        """Annotation set on box dict, NOT inside saved_attribute_attributes."""
        from src.maxpat.m4l_polish import populate_info_text

        ctrl = _make_named_control("obj-1", "Filter Cutoff")
        patch = _make_patch_with_controls([ctrl])
        populate_info_text(patch)

        box = patch["patcher"]["boxes"][0]["box"]
        # Should be top-level
        assert "annotation" in box
        assert "annotation_name" in box
        # Should NOT be inside saved_attribute_attributes
        saa = box.get("saved_attribute_attributes", {})
        valueof = saa.get("valueof", {})
        assert "annotation" not in valueof
        assert "annotation_name" not in valueof


# ===========================================================================
# TestPolishCompositor -- polish_m4l_device
# ===========================================================================

class TestPolishCompositor:
    """Test polish_m4l_device composes naming, banks, and info text."""

    def test_polish_calls_all_three(self):
        """Patch with unnamed controls -> after polish, longname derived, banks created, annotation set."""
        from src.maxpat.m4l_polish import polish_m4l_device

        ctrl = _make_live_control(varname="filter_cutoff")
        patch = _make_patch_with_controls([ctrl])
        polish_m4l_device(patch)

        box = patch["patcher"]["boxes"][0]["box"]
        # Naming should have run
        valueof = box["saved_attribute_attributes"]["valueof"]
        assert valueof.get("parameter_longname") == "Filter Cutoff"
        # Banks should have been created
        banks_box = _banks_box(patch)
        assert banks_box is not None
        # Info text should have been set
        assert box.get("annotation")

    def test_polish_ordering(self):
        """Naming runs before banks (so banks reference correct longnames)."""
        from src.maxpat.m4l_polish import polish_m4l_device

        ctrl = _make_live_control(varname="filter_cutoff")
        patch = _make_patch_with_controls([ctrl])
        polish_m4l_device(patch)

        # Banks should reference "Filter Cutoff" (derived longname)
        banks_box = _banks_box(patch)
        assert banks_box is not None
        bank = _banks(patch)[0]
        assert "Filter Cutoff" in bank["parameters"]

    def test_polish_returns_patch_dict(self):
        """Return value is the same dict (mutated in place)."""
        from src.maxpat.m4l_polish import polish_m4l_device

        patch = _make_patch_with_controls([])
        result = polish_m4l_device(patch)
        assert result is patch

    def test_polish_empty_patch(self):
        """Patch with no live.* controls -> no error, returns unchanged."""
        from src.maxpat.m4l_polish import polish_m4l_device

        patch = _make_patch_with_controls([])
        result = polish_m4l_device(patch)
        assert result is patch
        # No banks created
        for entry in result["patcher"]["boxes"]:
            box = entry.get("box", entry)
            assert get_box_name(box) != "live.banks"


    def test_polished_skeleton_passes_save_gate(self, tmp_path):
        """A polished add_m4l_gen_synth device saves as a new file (no blockers)."""
        from src.maxpat.hooks import save_patch_roundtrip
        from src.maxpat.m4l_polish import polish_m4l_device
        from src.maxpat.patcher import Patcher

        p = Patcher()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            p.add_m4l_gen_synth([("freq", 20.0, 2000.0), ("amp", 0.0, 0.5)])
            d = p.to_dict()
            polish_m4l_device(d)
            save_patch_roundtrip(d, tmp_path / "dev.maxpat")
        assert (tmp_path / "dev.maxpat").exists()


# ===========================================================================
# TestParameterCapableSet -- D5: refpage-grounded parameter-capable live.*
# ===========================================================================

_REFPAGE_PARAMETER_LIVE = frozenset({
    "live.arrows", "live.button", "live.dial", "live.drop", "live.gain~",
    "live.grid", "live.menu", "live.numbox", "live.slider", "live.step",
    "live.tab", "live.text", "live.toggle",
})


class TestParameterCapableSet:
    """Only refpage parameter-capable live.* classes get parameter attributes."""

    def test_set_is_refpage_literal(self):
        from src.maxpat.critics.m4l_critic import LIVE_PARAMETER_OBJECTS

        assert LIVE_PARAMETER_OBJECTS == _REFPAGE_PARAMETER_LIVE

    @pytest.mark.parametrize("maxclass", ["live.comment", "live.line", "live.meter~"])
    def test_non_parameters_get_no_parameter_attrs(self, maxclass):
        from src.maxpat.m4l_polish import polish_m4l_device

        box = {"id": "obj-1", "maxclass": maxclass, "numinlets": 1, "numoutlets": 1}
        patch = _make_patch_with_controls([box])
        polish_m4l_device(patch)

        for key in ("parameter_enable", "saved_attribute_attributes", "varname",
                    "annotation", "annotation_name"):
            assert key not in box, f"{maxclass} gained {key}"

    def test_critic_ignores_non_parameters(self):
        from src.maxpat.critics.m4l_critic import review_m4l

        boxes = [
            {"id": "obj-1", "maxclass": "newobj", "text": "plugout~",
             "numinlets": 2, "numoutlets": 2, "outlettype": ["signal", "signal"]},
            {"id": "obj-2", "maxclass": "live.comment", "numinlets": 1, "numoutlets": 0},
            {"id": "obj-3", "maxclass": "live.line", "numinlets": 1, "numoutlets": 0},
            {"id": "obj-4", "maxclass": "live.meter~", "numinlets": 1, "numoutlets": 1},
            {"id": "obj-5", "maxclass": "live.dial", "numinlets": 1, "numoutlets": 2},
        ]
        patch = _make_patch_with_controls(boxes)
        findings = [r.finding for r in review_m4l(patch, "instrument")
                    if "missing parameter_enable" in r.finding]
        assert len(findings) == 1
        assert findings[0].startswith("live.dial (obj-5)")

    @pytest.mark.parametrize(
        "maxclass", ["live.dial", "live.numbox", "live.slider", "live.gain~"])
    def test_float_native_defaults(self, maxclass):
        from src.maxpat.m4l_polish import ensure_parameter_enable

        box = {"id": "obj-1", "maxclass": maxclass, "numinlets": 1, "numoutlets": 2}
        ensure_parameter_enable(_make_patch_with_controls([box]))

        valueof = box["saved_attribute_attributes"]["valueof"]
        assert valueof["parameter_type"] == 0       # Float
        assert valueof["parameter_unitstyle"] == 1  # Float

    @pytest.mark.parametrize(
        "maxclass",
        ["live.tab", "live.menu", "live.text", "live.toggle", "live.button"])
    def test_enum_native_gets_no_type_default(self, maxclass):
        from src.maxpat.m4l_polish import ensure_parameter_enable

        box = {"id": "obj-1", "maxclass": maxclass, "numinlets": 1, "numoutlets": 2}
        ensure_parameter_enable(_make_patch_with_controls([box]))

        assert box["parameter_enable"] == 1
        valueof = box["saved_attribute_attributes"]["valueof"]
        assert "parameter_type" not in valueof
        assert "parameter_unitstyle" not in valueof

    def test_existing_type_never_overridden(self):
        from src.maxpat.m4l_polish import ensure_parameter_enable

        box = {"id": "obj-1", "maxclass": "live.tab", "numinlets": 1,
               "numoutlets": 3, "parameter_enable": 1,
               "saved_attribute_attributes": {"valueof": {"parameter_type": 2}}}
        ensure_parameter_enable(_make_patch_with_controls([box]))
        assert box["saved_attribute_attributes"]["valueof"]["parameter_type"] == 2

    @pytest.mark.requires_max
    def test_set_matches_refpages(self):
        """The set is exactly the live.* refpages carrying <parameter />."""
        from src.maxpat.critics.m4l_critic import LIVE_PARAMETER_OBJECTS
        from tests.conftest import MAX_APP_PATH

        refpages = MAX_APP_PATH / "Contents" / "Resources" / "C74" / "docs" / "refpages"
        name_re = re.compile(r'<c74object\b[^>]*\bname="([^"]+)"')
        param_re = re.compile(r"<parameter\s*/?>")
        found = set()
        for path in refpages.rglob("*.maxref.xml"):
            text = path.read_text(encoding="utf-8", errors="replace")
            m = name_re.search(text)
            if m and m.group(1).startswith("live.") and param_re.search(text):
                found.add(m.group(1))
        assert found == set(LIVE_PARAMETER_OBJECTS)


# ===========================================================================
# TestParameterEnableEnforcement -- SCAFFOLD-04
# ===========================================================================

class TestParameterEnableEnforcement:
    """Test ensure_parameter_enable sets parameter_enable=1 and saa defaults."""

    def test_sets_parameter_enable_when_missing(self):
        """Control with parameter_enable=0 -> after ensure_parameter_enable() -> 1."""
        from src.maxpat.m4l_polish import ensure_parameter_enable

        ctrl = _make_live_control(parameter_enable=0)
        patch = _make_patch_with_controls([ctrl])
        ensure_parameter_enable(patch)

        box = patch["patcher"]["boxes"][0]["box"]
        assert box["parameter_enable"] == 1

    def test_creates_saved_attribute_attributes(self):
        """Control with parameter_enable=0, no saa -> saa.valueof has type and unitstyle."""
        from src.maxpat.m4l_polish import ensure_parameter_enable

        ctrl = _make_live_control(parameter_enable=0)
        # Remove any saa that _make_live_control may have created
        ctrl.pop("saved_attribute_attributes", None)
        patch = _make_patch_with_controls([ctrl])
        ensure_parameter_enable(patch)

        box = patch["patcher"]["boxes"][0]["box"]
        saa = box.get("saved_attribute_attributes", {})
        valueof = saa.get("valueof", {})
        # Float is index 0 of parameter_type in parameters.maxref.xml.
        assert valueof.get("parameter_type") == 0  # ParamType.FLOAT
        assert valueof.get("parameter_unitstyle") == 1  # UnitStyle.FLOAT

    def test_preserves_existing_parameter_enable(self):
        """Control already has parameter_enable=1 and custom saa -> unchanged."""
        from src.maxpat.m4l_polish import ensure_parameter_enable

        ctrl = _make_live_control(parameter_enable=1, longname="My Param")
        ctrl["saved_attribute_attributes"]["valueof"]["parameter_type"] = 2
        ctrl["saved_attribute_attributes"]["valueof"]["parameter_unitstyle"] = 3
        patch = _make_patch_with_controls([ctrl])
        ensure_parameter_enable(patch)

        box = patch["patcher"]["boxes"][0]["box"]
        assert box["parameter_enable"] == 1
        valueof = box["saved_attribute_attributes"]["valueof"]
        assert valueof["parameter_type"] == 2
        assert valueof["parameter_unitstyle"] == 3

    def test_preserves_existing_saa_values(self):
        """Control with parameter_enable=0 but has saa.valueof.parameter_type=0 -> type stays 0."""
        from src.maxpat.m4l_polish import ensure_parameter_enable

        ctrl = _make_live_control(parameter_enable=0, longname="My Param")
        ctrl["saved_attribute_attributes"]["valueof"]["parameter_type"] = 0
        patch = _make_patch_with_controls([ctrl])
        ensure_parameter_enable(patch)

        box = patch["patcher"]["boxes"][0]["box"]
        assert box["parameter_enable"] == 1
        valueof = box["saved_attribute_attributes"]["valueof"]
        assert valueof["parameter_type"] == 0  # Preserved, not overridden to 1

    def test_skips_non_parameter_live_objects(self):
        """live.thisdevice -> not modified (no parameter_enable set, no saa created)."""
        from src.maxpat.m4l_polish import ensure_parameter_enable

        thisdevice = {
            "id": "obj-1",
            "maxclass": "live.thisdevice",
            "numinlets": 1,
            "numoutlets": 2,
            "outlettype": ["", ""],
        }
        patch = _make_patch_with_controls([thisdevice])
        ensure_parameter_enable(patch)

        box = patch["patcher"]["boxes"][0]["box"]
        assert "parameter_enable" not in box
        assert "saved_attribute_attributes" not in box

    def test_idempotent(self):
        """Running twice produces the same result as running once."""
        from src.maxpat.m4l_polish import ensure_parameter_enable
        import copy

        ctrl = _make_live_control(parameter_enable=0)
        ctrl.pop("saved_attribute_attributes", None)
        patch = _make_patch_with_controls([ctrl])
        ensure_parameter_enable(patch)
        snapshot = copy.deepcopy(patch)
        ensure_parameter_enable(patch)
        assert patch == snapshot

    def test_recurses_into_subpatchers(self):
        """live.dial inside a subpatcher -> gets parameter_enable=1."""
        from src.maxpat.m4l_polish import ensure_parameter_enable

        inner_ctrl = _make_live_control(box_id="sub-obj-1", parameter_enable=0)
        inner_ctrl.pop("saved_attribute_attributes", None)
        subpatcher_box = {
            "id": "obj-2",
            "maxclass": "newobj",
            "text": "p effects",
            "numinlets": 1,
            "numoutlets": 1,
            "outlettype": [""],
            "patcher": {
                "boxes": [{"box": inner_ctrl}],
                "lines": [],
            },
        }
        patch = {
            "patcher": {
                "boxes": [{"box": subpatcher_box}],
                "lines": [],
            },
        }
        ensure_parameter_enable(patch)

        inner_box = patch["patcher"]["boxes"][0]["box"]["patcher"]["boxes"][0]["box"]
        assert inner_box["parameter_enable"] == 1
        saa = inner_box.get("saved_attribute_attributes", {})
        valueof = saa.get("valueof", {})
        # Float is index 0 of parameter_type in parameters.maxref.xml.
        assert valueof.get("parameter_type") == 0
        assert valueof.get("parameter_unitstyle") == 1


# ===========================================================================
# TestM4LPrefixEnforcement -- SCAFFOLD-05
# ===========================================================================

class TestM4LPrefixEnforcement:
    """Test ensure_m4l_prefixes adds --- prefix to named objects."""

    def test_adds_prefix_to_named_objects(self):
        """Box with text='send myname' -> text=='send ---myname'."""
        from src.maxpat.m4l_polish import ensure_m4l_prefixes

        box = {
            "id": "obj-1",
            "maxclass": "newobj",
            "text": "send myname",
            "numinlets": 1,
            "numoutlets": 0,
            "outlettype": [],
        }
        patch = _make_patch_with_controls([box])
        ensure_m4l_prefixes(patch)

        result_box = patch["patcher"]["boxes"][0]["box"]
        assert result_box["text"] == "send ---myname"

    def test_all_named_object_types(self):
        """One box for each named type -> all get --- prefix."""
        from src.maxpat.m4l_polish import ensure_m4l_prefixes

        named_types = ["buffer~", "coll", "dict", "send", "receive",
                       "send~", "receive~", "value"]
        boxes = []
        for i, obj_type in enumerate(named_types):
            boxes.append({
                "id": f"obj-{i}",
                "maxclass": "newobj",
                "text": f"{obj_type} myname{i}",
                "numinlets": 1,
                "numoutlets": 1,
                "outlettype": [""],
            })
        patch = _make_patch_with_controls(boxes)
        ensure_m4l_prefixes(patch)

        for i, entry in enumerate(patch["patcher"]["boxes"]):
            box = entry["box"]
            tokens = box["text"].split()
            assert tokens[1].startswith("---"), f"{named_types[i]} not prefixed: {box['text']}"

    def test_skips_already_prefixed(self):
        """Box with text='send ---myname' -> text unchanged."""
        from src.maxpat.m4l_polish import ensure_m4l_prefixes

        box = {
            "id": "obj-1",
            "maxclass": "newobj",
            "text": "send ---myname",
            "numinlets": 1,
            "numoutlets": 0,
            "outlettype": [],
        }
        patch = _make_patch_with_controls([box])
        ensure_m4l_prefixes(patch)

        result_box = patch["patcher"]["boxes"][0]["box"]
        assert result_box["text"] == "send ---myname"

    def test_skips_hash_substitution(self):
        """Box with text='buffer~ #1' -> text unchanged."""
        from src.maxpat.m4l_polish import ensure_m4l_prefixes

        box = {
            "id": "obj-1",
            "maxclass": "newobj",
            "text": "buffer~ #1",
            "numinlets": 1,
            "numoutlets": 2,
            "outlettype": ["float", "bang"],
        }
        patch = _make_patch_with_controls([box])
        ensure_m4l_prefixes(patch)

        result_box = patch["patcher"]["boxes"][0]["box"]
        assert result_box["text"] == "buffer~ #1"

    def test_skips_unnamed_objects(self):
        """Box with text='coll' (no name arg) -> text unchanged."""
        from src.maxpat.m4l_polish import ensure_m4l_prefixes

        box = {
            "id": "obj-1",
            "maxclass": "newobj",
            "text": "coll",
            "numinlets": 1,
            "numoutlets": 4,
            "outlettype": ["", "", "", ""],
        }
        patch = _make_patch_with_controls([box])
        ensure_m4l_prefixes(patch)

        result_box = patch["patcher"]["boxes"][0]["box"]
        assert result_box["text"] == "coll"

    def test_preserves_extra_arguments(self):
        """Box with text='buffer~ mybuf 1000' -> text=='buffer~ ---mybuf 1000'."""
        from src.maxpat.m4l_polish import ensure_m4l_prefixes

        box = {
            "id": "obj-1",
            "maxclass": "newobj",
            "text": "buffer~ mybuf 1000",
            "numinlets": 1,
            "numoutlets": 2,
            "outlettype": ["float", "bang"],
        }
        patch = _make_patch_with_controls([box])
        ensure_m4l_prefixes(patch)

        result_box = patch["patcher"]["boxes"][0]["box"]
        assert result_box["text"] == "buffer~ ---mybuf 1000"

    def test_idempotent(self):
        """Running twice -> same result."""
        from src.maxpat.m4l_polish import ensure_m4l_prefixes
        import copy

        box = {
            "id": "obj-1",
            "maxclass": "newobj",
            "text": "send myname",
            "numinlets": 1,
            "numoutlets": 0,
            "outlettype": [],
        }
        patch = _make_patch_with_controls([box])
        ensure_m4l_prefixes(patch)
        snapshot = copy.deepcopy(patch)
        ensure_m4l_prefixes(patch)
        assert patch == snapshot

    def test_recurses_into_subpatchers(self):
        """send inside subpatcher -> gets --- prefix."""
        from src.maxpat.m4l_polish import ensure_m4l_prefixes

        inner_box = {
            "id": "sub-obj-1",
            "maxclass": "newobj",
            "text": "send myname",
            "numinlets": 1,
            "numoutlets": 0,
            "outlettype": [],
        }
        subpatcher_box = {
            "id": "obj-2",
            "maxclass": "newobj",
            "text": "p effects",
            "numinlets": 1,
            "numoutlets": 1,
            "outlettype": [""],
            "patcher": {
                "boxes": [{"box": inner_box}],
                "lines": [],
            },
        }
        patch = {
            "patcher": {
                "boxes": [{"box": subpatcher_box}],
                "lines": [],
            },
        }
        ensure_m4l_prefixes(patch)

        result_box = patch["patcher"]["boxes"][0]["box"]["patcher"]["boxes"][0]["box"]
        assert result_box["text"] == "send ---myname"


    # -- D2 (Q15): consistent renaming or report-only ----------------------

    @staticmethod
    def _texts(patch):
        return [e["box"].get("text") for e in patch["patcher"]["boxes"]]

    def test_send_and_short_receive_renamed_together(self):
        from src.maxpat.m4l_polish import ensure_m4l_prefixes

        patch = _make_patch_with_controls([
            _nb("obj-1", "send level"),
            _nb("obj-2", "r level"),
            _comment("obj-3", "send the dry signal"),
        ])
        ensure_m4l_prefixes(patch)
        assert self._texts(patch) == [
            "send ---level", "r ---level", "send the dry signal",
        ]

    def test_buffer_and_users_renamed_together(self):
        from src.maxpat.m4l_polish import ensure_m4l_prefixes

        patch = _buffer_users_patch()
        ensure_m4l_prefixes(patch)
        assert self._texts(patch) == [
            "buffer~ ---grains",
            "play~ ---grains 2",
            "groove~ ---grains 2",
            "index~ ---grains",
            "peek~ ---grains",
            "poke~ ---grains",
            "info~ ---grains",
            "set ---grains, bang",
            None,
        ]
        assert patch["patcher"]["boxes"][-1]["box"]["buffername"] == "---grains"

    def test_value_pv_and_signal_names(self):
        from src.maxpat.m4l_polish import ensure_m4l_prefixes

        patch = _make_patch_with_controls([
            _nb("obj-1", "s x1"), _nb("obj-2", "receive x1"),
            _nb("obj-3", "v x2"), _nb("obj-4", "value x2"),
            _nb("obj-5", "pv x3"), _nb("obj-6", "pv x3"),
            _nb("obj-7", "send~ x4"), _nb("obj-8", "receive~ x4"),
        ])
        ensure_m4l_prefixes(patch)
        assert self._texts(patch) == [
            "s ---x1", "receive ---x1", "v ---x2", "value ---x2",
            "pv ---x3", "pv ---x3", "send~ ---x4", "receive~ ---x4",
        ]

    def test_semicolon_message_blocks_rename(self):
        from src.maxpat.m4l_polish import ensure_m4l_prefixes, plan_m4l_prefixes

        patch = _make_patch_with_controls([
            _nb("obj-1", "send level"),
            _nb("obj-2", "r level"),
            _msg("obj-3", "; level 0.5"),
        ])
        assert "level" in plan_m4l_prefixes(patch)["report_only"]
        with pytest.warns(UserWarning, match="level"):
            ensure_m4l_prefixes(patch)
        assert self._texts(patch) == ["send level", "r level", "; level 0.5"]

    def test_unhandled_consumer_blocks_rename(self):
        from src.maxpat.m4l_polish import ensure_m4l_prefixes, plan_m4l_prefixes

        patch = _make_patch_with_controls([
            _nb("obj-1", "buffer~ grains"), _nb("obj-2", "record~ grains"),
        ])
        assert "grains" in plan_m4l_prefixes(patch)["report_only"]
        with pytest.warns(UserWarning, match="grains"):
            ensure_m4l_prefixes(patch)
        assert self._texts(patch) == ["buffer~ grains", "record~ grains"]

    def test_buffer_user_without_local_buffer_blocks(self):
        from src.maxpat.m4l_polish import ensure_m4l_prefixes, plan_m4l_prefixes

        patch = _make_patch_with_controls([
            _nb("obj-1", "send grains"), _nb("obj-2", "play~ grains"),
        ])
        assert "grains" in plan_m4l_prefixes(patch)["report_only"]
        with pytest.warns(UserWarning, match="grains"):
            ensure_m4l_prefixes(patch)
        assert self._texts(patch) == ["send grains", "play~ grains"]

    @pytest.mark.parametrize("external", [
        {"maxclass": "newobj", "text": "js helper.js"},
        {"maxclass": "jsui"},
        {"maxclass": "newobj", "text": "poly~ voice 4"},
        {"maxclass": "newobj", "text": "myabstraction"},
    ], ids=["js", "jsui", "poly~", "abstraction"])
    def test_external_script_blocks_everything(self, external):
        from src.maxpat.m4l_polish import ensure_m4l_prefixes, plan_m4l_prefixes

        ext = dict(external, id="obj-9", numinlets=1, numoutlets=1)
        patch = _make_patch_with_controls([
            ext, _nb("obj-1", "send a"), _nb("obj-2", "r a"),
        ])
        before = copy.deepcopy(patch)
        assert "a" in plan_m4l_prefixes(patch)["report_only"]
        with pytest.warns(UserWarning, match=r"unprefixed: a \(external"):
            ensure_m4l_prefixes(patch)
        assert patch == before

    def test_codebox_reference_blocks(self):
        from src.maxpat.m4l_polish import ensure_m4l_prefixes, plan_m4l_prefixes

        gen = _nb("obj-2", "gen~")
        gen["patcher"] = {"boxes": [{"box": {
            "id": "obj-1", "maxclass": "codebox", "numinlets": 0,
            "numoutlets": 1,
            "code": 'Buffer b("grains");\nout1 = peek(b, 0, 0);',
        }}], "lines": []}
        patch = _make_patch_with_controls([_nb("obj-1", "buffer~ grains"), gen])
        assert "grains" in plan_m4l_prefixes(patch)["report_only"]
        with pytest.warns(UserWarning, match="grains"):
            ensure_m4l_prefixes(patch)
        assert self._texts(patch)[0] == "buffer~ grains"

    def test_gen_and_rnbo_inner_names_not_collected(self):
        from src.maxpat.m4l_polish import ensure_m4l_prefixes, plan_m4l_prefixes

        rnbo = _nb("obj-1", "rnbo~")
        rnbo["patcher"] = {"boxes": [{"box": _nb("obj-1", "send foo")}],
                           "lines": []}
        patch = _make_patch_with_controls([rnbo])
        before = copy.deepcopy(patch)
        assert plan_m4l_prefixes(patch) == {"rename": [], "report_only": {}}
        ensure_m4l_prefixes(patch)
        assert patch == before

    def test_prefixed_collision_blocks(self):
        from src.maxpat.m4l_polish import ensure_m4l_prefixes, plan_m4l_prefixes

        patch = _make_patch_with_controls([
            _nb("obj-1", "send level"), _nb("obj-2", "receive ---level"),
        ])
        assert "level" in plan_m4l_prefixes(patch)["report_only"]
        with pytest.warns(UserWarning, match="level"):
            ensure_m4l_prefixes(patch)
        assert self._texts(patch) == ["send level", "receive ---level"]

    def test_message_box_is_not_a_declarer(self):
        from src.maxpat.m4l_polish import ensure_m4l_prefixes, plan_m4l_prefixes

        patch = _make_patch_with_controls([_msg("obj-1", "send level")])
        assert plan_m4l_prefixes(patch) == {"rename": [], "report_only": {}}
        ensure_m4l_prefixes(patch)
        assert self._texts(patch) == ["send level"]

    def test_subpatcher_title_does_not_block(self):
        from src.maxpat.m4l_polish import ensure_m4l_prefixes

        sub = _nb("obj-3", "p fx")
        sub["patcher"] = {"boxes": [], "lines": []}
        patch = _make_patch_with_controls([
            _nb("obj-1", "send fx"), _nb("obj-2", "r fx"), sub,
        ])
        ensure_m4l_prefixes(patch)
        assert self._texts(patch) == ["send ---fx", "r ---fx", "p fx"]

    def test_plan_is_pure(self):
        from src.maxpat.m4l_polish import plan_m4l_prefixes

        patch = _buffer_users_patch()
        before = copy.deepcopy(patch)
        plan = plan_m4l_prefixes(patch)
        assert patch == before
        assert plan == {"rename": ["grains"], "report_only": {}}

    def test_nested_rename_is_consistent(self):
        from src.maxpat.m4l_polish import ensure_m4l_prefixes

        sub = _nb("obj-2", "p effects")
        sub["patcher"] = {"boxes": [{"box": _nb("obj-1", "r level")}],
                          "lines": []}
        patch = _make_patch_with_controls([_nb("obj-1", "send level"), sub])
        ensure_m4l_prefixes(patch)
        assert self._texts(patch)[0] == "send ---level"
        inner = patch["patcher"]["boxes"][1]["box"]["patcher"]["boxes"][0]["box"]
        assert inner["text"] == "r ---level"

    def test_idempotent_with_reports(self):
        from src.maxpat.m4l_polish import ensure_m4l_prefixes

        patch = _buffer_users_patch()
        patch["patcher"]["boxes"] += [
            {"box": _nb("obj-20", "send level")},
            {"box": _nb("obj-21", "r level")},
            {"box": _msg("obj-22", "; level 0.5")},
        ]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            ensure_m4l_prefixes(patch)
            once = copy.deepcopy(patch)
            ensure_m4l_prefixes(patch)
        assert patch == once
        assert once["patcher"]["boxes"][0]["box"]["text"] == "buffer~ ---grains"
        assert once["patcher"]["boxes"][-3]["box"]["text"] == "send level"


def _nb(box_id: str, text: str) -> dict:
    """A newobj box dict."""
    return {"id": box_id, "maxclass": "newobj", "text": text,
            "numinlets": 1, "numoutlets": 1, "outlettype": [""]}


def _msg(box_id: str, text: str) -> dict:
    """A message box dict."""
    return {"id": box_id, "maxclass": "message", "text": text,
            "numinlets": 2, "numoutlets": 1, "outlettype": [""]}


def _comment(box_id: str, text: str) -> dict:
    """A comment box dict."""
    return {"id": box_id, "maxclass": "comment", "text": text,
            "numinlets": 1, "numoutlets": 0}


def _buffer_users_patch() -> dict:
    """buffer~ grains plus every handled buffer user (D2 repro, case 2).

    The ``set grains, bang`` message cords into groove~: since quick
    261022-ud6 WP4 (review IN-05) only a ``set`` that feeds a declarer,
    buffer user or waveform~ is a rewritable position.
    """
    patch = _make_patch_with_controls([
        _nb("obj-1", "buffer~ grains"),
        _nb("obj-2", "play~ grains 2"),
        _nb("obj-3", "groove~ grains 2"),
        _nb("obj-4", "index~ grains"),
        _nb("obj-5", "peek~ grains"),
        _nb("obj-6", "poke~ grains"),
        _nb("obj-7", "info~ grains"),
        _msg("obj-8", "set grains, bang"),
        {"id": "obj-9", "maxclass": "waveform~", "buffername": "grains",
         "numinlets": 5, "numoutlets": 6},
    ])
    patch["patcher"]["lines"] = [
        {"patchline": {"source": ["obj-8", 0], "destination": ["obj-3", 0]}},
    ]
    return patch


# ===========================================================================
# TestEnforcementIntegration -- SCAFFOLD-04 + SCAFFOLD-05 via polish_m4l_device
# ===========================================================================

class TestEnforcementIntegration:
    """Test ensure_parameter_enable and ensure_m4l_prefixes via polish_m4l_device."""

    def test_scaffold_polish_integration(self):
        """polish_m4l_device enforces parameter_enable and --- prefix."""
        from src.maxpat.m4l_polish import polish_m4l_device

        dial = _make_live_control(
            box_id="obj-1",
            parameter_enable=0,
            varname="filter_cutoff",
        )
        # Remove saa so ensure_parameter_enable must create it
        dial.pop("saved_attribute_attributes", None)

        send_box = {
            "id": "obj-2",
            "maxclass": "newobj",
            "text": "send myname",
            "numinlets": 1,
            "numoutlets": 0,
            "outlettype": [],
        }

        patch = _make_patch_with_controls([dial, send_box])
        polish_m4l_device(patch)

        # SCAFFOLD-04: parameter_enable set and saa created
        dial_box = patch["patcher"]["boxes"][0]["box"]
        assert dial_box["parameter_enable"] == 1
        saa = dial_box.get("saved_attribute_attributes", {})
        valueof = saa.get("valueof", {})
        assert "parameter_type" in valueof
        assert "parameter_unitstyle" in valueof

        # SCAFFOLD-05: send box prefixed
        send_result = patch["patcher"]["boxes"][1]["box"]
        assert send_result["text"] == "send ---myname"

        # POLISH-01: longname derived from varname
        assert valueof.get("parameter_longname") == "Filter Cutoff"
