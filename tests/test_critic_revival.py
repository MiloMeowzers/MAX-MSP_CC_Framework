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
from src.maxpat.critics.m4l_critic import detect_m4l_device_type, review_m4l
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


# ===========================================================================
# M4L fixtures (D4) -- real outlettypes so _outlet_is_signal reads them
# ===========================================================================

_OUTLETTYPES = {
    "plugin~": ["signal", "signal"],
    "plugout~": ["signal", "signal"],
    "gen~": ["signal"],
    "gain~": ["signal", ""],
    "live.gain~": ["signal", "signal", "", "", ""],
    "*~": ["signal"],
    "number": ["", "bang"],
    "cycle~": ["signal"],
    "dac~": [],
    "ezdac~": [],
    "meter~": ["float"],
    "notein": ["int", "int", "int"],
    "midiin": ["int"],
    "live.thisdevice": ["bang", "int", "int"],
}

_UI = {"gain~", "live.gain~", "number", "meter~", "ezdac~"}


def _b(box_id: str, text: str, numinlets: int = 2) -> dict:
    """Box with MAX's shape: UI maxclass for widgets, else newobj."""
    name = text.split()[0]
    box = {
        "id": box_id,
        "numinlets": numinlets,
        "numoutlets": len(_OUTLETTYPES[name]),
        "outlettype": list(_OUTLETTYPES[name]),
    }
    if name in _UI:
        box["maxclass"] = name
    else:
        box["maxclass"] = "newobj"
        box["text"] = text
    return box


def _l(src: str, so: int, dst: str, di: int) -> dict:
    return {"source": [src, so], "destination": [dst, di]}


def _gain_findings(results):
    return [r for r in results
            if "is on the signal path to plugout~" in r.finding]


def _blockers(results):
    return [r for r in results if r.severity == "blocker"]


def _audio_effect_passthrough() -> dict:
    return _make_patch(
        [_b("obj-1", "plugin~"), _b("obj-2", "plugout~")],
        [_l("obj-1", 0, "obj-2", 0), _l("obj-1", 1, "obj-2", 1)],
    )


def _instrument_patch() -> dict:
    return _make_patch(
        [_b("obj-1", "notein", 1), _b("obj-2", "gen~", 1),
         _b("obj-3", "plugout~")],
        [_l("obj-2", 0, "obj-3", 0), _l("obj-2", 0, "obj-3", 1)],
    )


def _plain_audio_patch() -> dict:
    return _make_patch(
        [_b("obj-1", "cycle~ 440"), _b("obj-2", "*~ 0.5"),
         _b("obj-3", "dac~")],
        [_l("obj-1", 0, "obj-2", 0), _l("obj-2", 0, "obj-3", 0),
         _l("obj-2", 0, "obj-3", 1)],
    )


class TestM4LDispatch:
    """D4: review_patch detects M4L devices and calls review_m4l."""

    def test_detect_audio_effect(self):
        assert detect_m4l_device_type(_audio_effect_passthrough()) == "audio_effect"

    def test_detect_instrument(self):
        assert detect_m4l_device_type(_instrument_patch()) == "instrument"

    def test_detect_midi_effect_newobj(self):
        patch = _make_patch(
            [_b("obj-1", "live.thisdevice", 1), _b("obj-2", "midiin", 1)], [])
        assert detect_m4l_device_type(patch) == "midi_effect"

    def test_detect_midi_effect_maxclass_thisdevice(self):
        patch = _make_patch([{
            "id": "obj-1", "maxclass": "live.thisdevice",
            "numinlets": 1, "numoutlets": 3,
            "outlettype": ["bang", "int", "int"],
        }], [])
        assert detect_m4l_device_type(patch) == "midi_effect"

    def test_detect_none_for_plain_patch(self):
        assert detect_m4l_device_type(_plain_audio_patch()) is None

    def test_review_patch_plain_patch_no_m4l(self):
        hits = [r for r in review_patch(_plain_audio_patch())
                if "M4L" in r.finding or "plugout~" in r.finding]
        assert hits == []

    def test_review_patch_runs_m4l_critic(self):
        results = review_patch(_audio_effect_passthrough())
        assert any(r.severity == "warning"
                   and r.finding.startswith("M4L device missing openinpresentation")
                   for r in results)


class TestM4LRequiredObjects:
    """D4 / OQ2-A: reduced required-object sets; live.thisdevice optional."""

    def test_instrument_needs_no_midi(self):
        results = review_m4l(_instrument_patch(), "instrument")
        assert not [r for r in results if "missing required object" in r.finding]

    def test_audio_effect_needs_no_thisdevice(self):
        results = review_m4l(_audio_effect_passthrough(), "audio_effect")
        assert not [r for r in results if "missing required object" in r.finding]

    def test_midi_effect_requires_midiin_midiout(self):
        patch = _make_patch([_b("obj-1", "live.thisdevice", 1)], [])
        blockers = sorted(r.finding for r in _blockers(review_patch(patch)))
        assert blockers == [
            "M4L midi_effect missing required object: midiin",
            "M4L midi_effect missing required object: midiout",
        ]

    def test_audio_effect_requires_plugout(self):
        patch = _make_patch(
            [_b("obj-1", "plugin~"), _b("obj-2", "*~ 0.5")],
            [_l("obj-1", 0, "obj-2", 0)],
        )
        assert any(
            r.severity == "blocker"
            and r.finding == "M4L audio_effect missing required object: plugout~"
            for r in review_patch(patch)
        )


class TestM4LGainPath:
    """D4 / OQ3-A: gain stages on any signal path to plugout~; ezdac~."""

    def test_gain_direct_one_blocker_per_pair(self):
        patch = _make_patch(
            [_b("obj-1", "gen~", 1), _b("obj-2", "gain~"),
             _b("obj-3", "plugout~")],
            [_l("obj-1", 0, "obj-2", 0), _l("obj-2", 0, "obj-3", 0),
             _l("obj-2", 0, "obj-3", 1)],
        )
        gain = _gain_findings(review_patch(patch))
        assert len(gain) == 1
        assert gain[0].severity == "blocker"
        assert "obj-2" in gain[0].finding and "obj-3" in gain[0].finding

    def test_live_gain_direct(self):
        patch = _make_patch(
            [_b("obj-1", "gen~", 1), _b("obj-2", "live.gain~"),
             _b("obj-3", "plugout~")],
            [_l("obj-1", 0, "obj-2", 0), _l("obj-2", 0, "obj-3", 0),
             _l("obj-2", 1, "obj-3", 1)],
        )
        gain = _gain_findings(review_patch(patch))
        assert len(gain) == 1
        assert gain[0].severity == "blocker"
        assert gain[0].finding.startswith("live.gain~ (obj-2)")

    def test_gain_indirect(self):
        patch = _make_patch(
            [_b("obj-1", "gen~", 1), _b("obj-2", "gain~"),
             _b("obj-3", "*~ 0.5"), _b("obj-4", "plugout~")],
            [_l("obj-1", 0, "obj-2", 0), _l("obj-2", 0, "obj-3", 0),
             _l("obj-3", 0, "obj-4", 0)],
        )
        gain = _gain_findings(review_patch(patch))
        assert len(gain) == 1
        assert gain[0].finding.startswith("gain~ (obj-2)")

    def test_gain_chain_two_blockers(self):
        patch = _make_patch(
            [_b("obj-1", "gen~", 1), _b("obj-2", "gain~"),
             _b("obj-3", "live.gain~"), _b("obj-4", "plugout~")],
            [_l("obj-1", 0, "obj-2", 0), _l("obj-2", 0, "obj-3", 0),
             _l("obj-3", 0, "obj-4", 0)],
        )
        gain = _gain_findings(review_patch(patch))
        assert len(gain) == 2
        assert all(r.severity == "blocker" for r in gain)
        assert sorted(r.finding.split()[0] for r in gain) == ["gain~", "live.gain~"]

    def test_side_branch_not_flagged(self):
        patch = _make_patch(
            [_b("obj-1", "plugin~"), _b("obj-2", "plugout~"),
             _b("obj-3", "gain~"), _b("obj-4", "meter~", 1)],
            [_l("obj-1", 0, "obj-2", 0), _l("obj-1", 1, "obj-2", 1),
             _l("obj-1", 0, "obj-3", 0), _l("obj-3", 0, "obj-4", 0)],
        )
        assert _gain_findings(review_patch(patch)) == []

    def test_control_cord_not_a_path(self):
        patch = _make_patch(
            [_b("obj-1", "plugin~"), _b("obj-2", "gain~"),
             _b("obj-3", "number", 1), _b("obj-4", "*~"),
             _b("obj-5", "plugout~")],
            [_l("obj-2", 1, "obj-3", 0), _l("obj-3", 0, "obj-4", 1),
             _l("obj-1", 0, "obj-4", 0), _l("obj-4", 0, "obj-5", 0)],
        )
        assert _gain_findings(review_patch(patch)) == []

    def test_ezdac_in_device_blocks(self):
        patch = _make_patch(
            [_b("obj-1", "plugin~"), _b("obj-2", "plugout~"),
             _b("obj-3", "ezdac~")],
            [_l("obj-1", 0, "obj-2", 0), _l("obj-1", 1, "obj-2", 1),
             _l("obj-1", 0, "obj-3", 0)],
        )
        ez = [r for r in review_patch(patch) if r.finding.startswith("ezdac~ (")]
        assert len(ez) == 1
        assert ez[0].severity == "blocker"
        assert "M4L device" in ez[0].finding


def _m4l_gen_synth_dict() -> dict:
    p = Patcher()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        p.add_m4l_gen_synth([("freq", 20.0, 2000.0), ("amp", 0.0, 1.0)])
    return p.to_dict()


class TestM4LBuilderClean:
    """D4: the framework's own add_m4l_gen_synth skeleton reviews clean."""

    def test_review_patch_runs_m4l_with_zero_blockers(self):
        results = review_patch(_m4l_gen_synth_dict())
        assert any(r.finding.startswith("M4L device") for r in results)
        assert _blockers(results) == []

    def test_review_m4l_instrument_zero_blockers(self):
        assert _blockers(review_m4l(_m4l_gen_synth_dict(), "instrument")) == []
