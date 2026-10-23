"""The RNBO builder writes MAX's rnbo~ box shape (quick 261022-ud6 WP4, review WR-05 / E8).

Golden: tests/fixtures/expected/rnbo_box_shapes.json, copied from MAX-saved
rnbo~ boxes in the Max 9.2 bundle's RNBO help patches. EXPERIMENTAL: the
builder's output itself has not been opened in MAX yet.
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import pytest

from src.maxpat.patcher import Patcher
from src.maxpat.rnbo import add_rnbo, generate_rnbo_wrapper

GOLDEN = json.loads(
    (Path(__file__).parent / "fixtures" / "expected" / "rnbo_box_shapes.json").read_text())
SHAPES = GOLDEN["shapes"]


def _rnbo_dict(p: Patcher) -> dict:
    (box,) = [e["box"] for e in p.to_dict()["patcher"]["boxes"]
              if str(e["box"].get("text", "")).split()[:1] == ["rnbo~"]]
    return box


def _io(info) -> list:
    return [(x["type"], x["index"]) for x in info["IOInfo"]]


@pytest.mark.parametrize("key", sorted(SHAPES))
def test_box_matches_max_saved_shape(key):
    shape = SHAPES[key]
    p = Patcher()
    add_rnbo(p, audio_ins=shape["in~"], audio_outs=shape["out~"])
    box = _rnbo_dict(p)
    assert box["maxclass"] == "newobj"
    assert box["text"] == "rnbo~"
    assert box["numinlets"] == shape["numinlets"]
    assert box["numoutlets"] == shape["numoutlets"]
    assert box["outlettype"] == shape["outlettype"]
    assert box["patcher"]["classnamespace"] == shape["inner_classnamespace"] == "rnbo"
    assert _io(box["inletInfo"]) == _io(shape["inletInfo"])
    assert _io(box["outletInfo"]) == _io(shape["outletInfo"])


def test_wrapper_cords_stay_in_range_and_validate():
    from src.maxpat.validation import validate_patch

    p = generate_rnbo_wrapper(audio_ins=2, audio_outs=2)
    box = _rnbo_dict(p)
    assert (box["numinlets"], box["numoutlets"]) == (2, 3)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        results = validate_patch(p.to_dict())
    assert not [r for r in results if r.level == "error"], [r.message for r in results]


@pytest.mark.parametrize("param, text", [
    ({"name": "gain", "default": 0.5, "min": 0.0, "max": 1.0}, "param gain 0.5 @min 0.0 @max 1.0"),
    ({"name": "g", "default": None, "min": None, "max": None}, "param g"),
    ({"name": "g", "default": 0.25, "min": None, "max": 2}, "param g 0.25 @max 2"),
    ({"name": "g"}, "param g 0.0 @min 0.0 @max 1.0"),
])
def test_param_uses_positional_name_and_initial(param, text):
    _box, inner = add_rnbo(Patcher(), params=[param], audio_ins=1, audio_outs=1)
    (pbox,) = [b for b in inner.boxes if b.name == "param"]
    assert pbox.text == text
    assert "@name" not in pbox.text and "@initial" not in pbox.text


def test_rnbo_critic_reads_builder_params():
    """The RNBO critic parses the positional name (Q26), so duplicates still surface."""
    from src.maxpat.critics import review_patch

    p = Patcher()
    add_rnbo(p, params=[{"name": "gain", "default": 0.5, "min": 0.0, "max": 1.0},
                        {"name": "gain", "default": 0.1, "min": 0.0, "max": 1.0}],
             audio_ins=1, audio_outs=1)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        findings = [r.finding for r in review_patch(p.to_dict())]
    assert any("gain" in f and ("uplicate" in f) for f in findings), findings
