"""Q4 critic-revival regression tests (quick 261012-egf).

Covers `.planning/reviews/2026-10-11-fix-plan.md` Q4 and review findings:
  - E3: dead detectors. The gen~ code-vs-box I/O blocker and the RNBO
    critic gated on ``maxclass``, but MAX (and ``add_gen``) write these boxes
    as ``newobj``. They are now detected by box name (``gen~``, ``mc.gen~``,
    ``rnbo~``), and mc.gen~'s gen patcher is read from ``data.patcher`` (MAX's
    mc wrapper) as well as ``patcher``. Only a codebox that appears in at
    least one patchline of its gen patcher is compared (OQ1-A).
  - D4: ``review_patch`` now calls ``review_m4l`` when plugin~, plugout~ or
    live.thisdevice is present, with reduced required-object sets, gain stages
    flagged on any signal path to plugout~, and ezdac~ flagged in devices.

Committed patches are opened read-only and every critic call gets a freshly
loaded dict (deep-copied before any mutation). No committed patch file is
ever written.
"""

from __future__ import annotations

import copy
import json
import warnings
from pathlib import Path

from src.maxpat.critics import _has_rnbo_boxes, review_patch
from src.maxpat.critics.dsp_critic import review_dsp
from src.maxpat.critics.rnbo_critic import review_rnbo
from src.maxpat.patcher import Patcher
from tests.test_critics import (
    _gen_io_mismatch_patch,
    _gen_output_mismatch_patch,
    _make_patch,
    _rnbo_patch_clean,
    _rnbo_patch_duplicate_params,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent

_JI = "patches/ji-harmonizer/generated/ji-harmonizer.maxpat"
_WORMHOLE = "patches/wormhole/generated/wormhole.maxpat"


def _load(rel: str) -> dict:
    """Load a committed patch read-only (fresh dict on every call)."""
    with open(_REPO_ROOT / rel) as f:
        return json.load(f)


def _find_box(patch: dict, box_id: str) -> dict:
    for entry in patch["patcher"]["boxes"]:
        if entry["box"].get("id") == box_id:
            return entry["box"]
    raise KeyError(box_id)


def _gen_findings(results):
    return [r for r in results if r.finding.startswith("gen~ I/O")]


def _input_blockers(results):
    return [r for r in results
            if r.severity == "blocker"
            and r.finding.startswith("gen~ I/O input mismatch")]


def _output_blockers(results):
    return [r for r in results
            if r.severity == "blocker"
            and r.finding.startswith("gen~ I/O output mismatch")]


# ===========================================================================
# gen~ fixtures
# ===========================================================================

_MISMATCH_CODE = "out1 = in1 + in2 + in3; out2 = in1;"
_UNWIRED_CODE = "out1 = in1 + in2 + in3 + in4; out2 = in1; out3 = in2;"


def _wired_gen_patcher(code: str) -> dict:
    """Gen patcher shaped like add_gen output: `in 1` -> codebox -> `out 1`."""
    return {
        "boxes": [
            {"box": {"id": "g-in1", "maxclass": "newobj", "text": "in 1",
                     "numinlets": 0, "numoutlets": 1}},
            {"box": {"id": "g-cb", "maxclass": "codebox", "code": code,
                     "numinlets": 3, "numoutlets": 2}},
            {"box": {"id": "g-out1", "maxclass": "newobj", "text": "out 1",
                     "numinlets": 1, "numoutlets": 0}},
        ],
        "lines": [
            {"patchline": {"source": ["g-in1", 0],
                           "destination": ["g-cb", 0]}},
            {"patchline": {"source": ["g-cb", 0],
                           "destination": ["g-out1", 0]}},
        ],
    }


def _unwired_gen_patcher(code: str) -> dict:
    """Gen patcher whose only codebox appears in no patchline."""
    return {
        "boxes": [
            {"box": {"id": "g-cb", "maxclass": "codebox", "code": code,
                     "numinlets": 4, "numoutlets": 3}},
        ],
        "lines": [],
    }


def _newobj_gen_patch(code: str = _MISMATCH_CODE, text: str = "gen~",
                      numinlets: int = 1, numoutlets: int = 1) -> dict:
    return _make_patch([{
        "id": "obj-1",
        "maxclass": "newobj",
        "text": text,
        "numinlets": numinlets,
        "numoutlets": numoutlets,
        "outlettype": ["signal"] * numoutlets,
        "patcher": _wired_gen_patcher(code),
    }], [])


def _mc_gen_patch(location: str) -> dict:
    box = {
        "id": "obj-1",
        "maxclass": "newobj",
        "text": "mc.gen~",
        "numinlets": 1,
        "numoutlets": 1,
        "outlettype": ["multichannelsignal"],
    }
    if location == "data":
        box["data"] = {"patcher": _wired_gen_patcher(_MISMATCH_CODE)}
        box["wrapper_uniquekey"] = "u123"
    else:
        box["patcher"] = _wired_gen_patcher(_MISMATCH_CODE)
    return _make_patch([box], [])


def _unwired_gen_patch(maxclass: str) -> dict:
    box = {
        "id": "obj-1",
        "maxclass": maxclass,
        "text": "gen~",
        "numinlets": 1,
        "numoutlets": 1,
        "outlettype": ["signal"],
        "patcher": _unwired_gen_patcher(_UNWIRED_CODE),
    }
    return _make_patch([box], [])


class TestGenIOByName:
    """E3: the gen~ code-vs-box I/O blocker fires on newobj gen~/mc.gen~."""

    def test_newobj_gen_mismatch_blocks(self):
        results = review_dsp(_newobj_gen_patch())
        gen = _gen_findings(results)
        assert len(gen) == 2
        inp = _input_blockers(results)
        out = _output_blockers(results)
        assert len(inp) == 1 and "uses 3 inputs" in inp[0].finding
        assert len(out) == 1 and "uses 2 outputs" in out[0].finding

    def test_newobj_gen_with_args_blocks(self):
        results = review_dsp(_newobj_gen_patch(text="gen~ @title demo"))
        assert len(_input_blockers(results)) == 1
        assert len(_output_blockers(results)) == 1

    def test_mc_gen_data_patcher_blocks(self):
        results = review_dsp(_mc_gen_patch("data"))
        assert len(_input_blockers(results)) == 1

    def test_mc_gen_patcher_key_blocks(self):
        results = review_dsp(_mc_gen_patch("patcher"))
        assert len(_input_blockers(results)) == 1

    def test_add_gen_builder_repro_blocks(self):
        p = Patcher()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            p.add_gen("out1 = in1 + in2 + in3;\nout2 = in1;",
                      num_inputs=1, num_outputs=1)
        results = review_dsp(p.to_dict())
        assert len(_input_blockers(results)) == 1
        assert len(_output_blockers(results)) == 1

    def test_ji_harmonizer_mc_gen_unmutated_clean(self):
        results = review_dsp(_load(_JI))
        assert not [r for r in _gen_findings(results) if "obj-88" in r.finding]

    def test_ji_harmonizer_mc_gen_inlet_mismatch(self):
        d = copy.deepcopy(_load(_JI))
        box = _find_box(d, "obj-88")
        assert box["text"].split()[0] == "mc.gen~"
        assert "patcher" in box.get("data", {})
        box["numinlets"] = 2
        inp = _input_blockers(review_dsp(d))
        assert any("obj-88" in r.finding for r in inp)

    def test_wormhole_gen_outlet_mismatch(self):
        d = copy.deepcopy(_load(_WORMHOLE))
        box = _find_box(d, "obj-12")
        assert box["text"].split()[0] == "gen~"
        box["numoutlets"] = 1
        out = _output_blockers(review_dsp(d))
        assert any("obj-12" in r.finding for r in out)

    def test_matched_newobj_gen_clean(self):
        results = review_dsp(_newobj_gen_patch(code="out1 = in1 * 0.5;"))
        assert _gen_findings(results) == []

    def test_external_gendsp_skipped(self):
        patch = _make_patch([{
            "id": "obj-1", "maxclass": "newobj", "text": "gen~ @gen foo.gendsp",
            "numinlets": 1, "numoutlets": 1, "outlettype": ["signal"],
        }], [])
        assert _gen_findings(review_dsp(patch)) == []

    def test_maxclass_input_fixture_still_blocks(self):
        patch, ctx = _gen_io_mismatch_patch()
        assert len(_input_blockers(review_dsp(patch, code_context=ctx))) == 1

    def test_maxclass_output_fixture_still_blocks(self):
        patch, ctx = _gen_output_mismatch_patch()
        assert len(_output_blockers(review_dsp(patch, code_context=ctx))) == 1

    def test_unwired_codebox_maxclass_skipped(self):
        """OQ1-A: a codebox in no patchline is not compared."""
        assert _gen_findings(review_dsp(_unwired_gen_patch("gen~"))) == []

    def test_unwired_codebox_newobj_skipped(self):
        assert _gen_findings(review_dsp(_unwired_gen_patch("newobj"))) == []

    def test_unwired_codebox_code_context_fallback(self):
        ctx = {"gen~_code": {"obj-1": _UNWIRED_CODE}}
        results = review_dsp(_unwired_gen_patch("gen~"), code_context=ctx)
        assert len(_input_blockers(results)) == 1

    def test_review_patch_end_to_end(self):
        results = review_patch(_newobj_gen_patch())
        assert len(_input_blockers(results)) == 1
        assert len(_output_blockers(results)) == 1


# ===========================================================================
# RNBO fixtures (MAX shape: newobj rnbo~)
# ===========================================================================

def _newobj_rnbo_patch(params: list[str]) -> dict:
    inner_boxes = [
        {"box": {"id": "r-in", "maxclass": "newobj", "text": "in~ 1",
                 "numinlets": 0, "numoutlets": 1}},
        {"box": {"id": "r-out", "maxclass": "newobj", "text": "out~ 1",
                 "numinlets": 1, "numoutlets": 0}},
    ]
    for i, text in enumerate(params):
        inner_boxes.append({"box": {
            "id": f"r-p{i}", "maxclass": "newobj", "text": text,
            "numinlets": 2, "numoutlets": 2,
        }})
    return _make_patch([{
        "id": "obj-1",
        "maxclass": "newobj",
        "text": "rnbo~ @title demo",
        "numinlets": 1,
        "numoutlets": 1,
        "outlettype": ["signal"],
        "patcher": {
            "classnamespace": "rnbo",
            "boxes": inner_boxes,
            "lines": [],
        },
    }], [])


def _duplicate_blockers(results):
    return [r for r in results
            if r.severity == "blocker" and "duplicate" in r.finding.lower()]


class TestRNBOByName:
    """E3: the RNBO critic runs on newobj rnbo~ boxes (dispatch and review)."""

    _DUP = ["param @name gain @min 0 @max 1", "param @name gain @min 0 @max 1"]

    def test_review_rnbo_newobj_duplicate(self):
        assert _duplicate_blockers(review_rnbo(_newobj_rnbo_patch(self._DUP)))

    def test_review_patch_newobj_duplicate(self):
        assert _duplicate_blockers(review_patch(_newobj_rnbo_patch(self._DUP)))

    def test_review_patch_newobj_naming(self):
        patch = _newobj_rnbo_patch([
            "param @name GainLevel @min 0 @max 1",
            "param @name FilterCutoff @min 20 @max 20000",
        ])
        warns = [r for r in review_patch(patch) if r.severity == "warning"
                 and "naming convention" in r.finding]
        text = " ".join(r.finding for r in warns)
        assert "GainLevel" in text and "FilterCutoff" in text

    def test_review_patch_newobj_clean(self):
        patch = _newobj_rnbo_patch(["param @name gain_level @min 0 @max 1"])
        hits = [r for r in review_patch(patch)
                if "rnbo~" in r.finding or "param" in r.finding]
        assert hits == []

    def test_has_rnbo_boxes_newobj(self):
        assert _has_rnbo_boxes(_newobj_rnbo_patch([])) is True

    def test_has_rnbo_boxes_maxclass(self):
        assert _has_rnbo_boxes(_rnbo_patch_clean()) is True

    def test_has_rnbo_boxes_false_for_gen(self):
        patch = _make_patch([{
            "id": "obj-1", "maxclass": "newobj", "text": "gen~",
            "numinlets": 1, "numoutlets": 1,
        }], [])
        assert _has_rnbo_boxes(patch) is False

    def test_maxclass_duplicate_fixture_unchanged(self):
        assert _duplicate_blockers(review_patch(_rnbo_patch_duplicate_params()))

    def test_maxclass_clean_fixture_unchanged(self):
        hits = [r for r in review_patch(_rnbo_patch_clean())
                if "rnbo~" in r.finding or "RNBO" in r.finding]
        assert hits == []
