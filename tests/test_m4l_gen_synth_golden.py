"""Golden characterization of Patcher.add_m4l_gen_synth (quick 261022-pqu, Q40).

Committed BEFORE add_m4l_gen_synth was refactored onto add_m4l_device: the
fixture is the serialized output of the pre-refactor builder for four
representative inputs, and the comparison is on ``json.dumps(..., indent=2)``
text, so it is sensitive to key order as well as values (json.load keeps
order). If this test fails after a builder change, fix the builder, never
the fixture.
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import pytest

from src.maxpat.patcher import Patcher

FIXTURE = Path(__file__).parent / "fixtures" / "expected" / "m4l_gen_synth_golden.json"

CUSTOM_CODE = (
    "Param cutoff(10010, min=20, max=20000);\n"
    "Param res(0.5, min=0, max=1);\n"
    "out1 = noise() * res;"
)

CASES = {
    "default": {
        "params": [("freq", 20.0, 2000.0), ("amp", 0.0, 1.0)],
        "kwargs": {},
    },
    "varname_osc": {
        "params": [("freq", 100.0, 1000.0)],
        "kwargs": {"gen_varname": "osc"},
    },
    "custom_code": {
        "params": [("cutoff", 20.0, 20000.0), ("res", 0.0, 1.0)],
        "kwargs": {"gen_code": CUSTOM_CODE},
    },
    "ten_params": {
        "params": [
            ("freq", 20.0, 2000.0),
            ("amp", 0.0, 1.0),
            ("attack_ms", 1.0, 500.0),
            ("cutoffHz", 20.0, 20000.0),
            ("gain_db", -70.0, 0.0),
            ("octave", -2, 2),
            ("steps", 1, 16),
            ("pan", -1.0, 1.0),
            ("Filter Envelope Amount", 0.0, 1.0),
            ("mix", 0.0, 1.0),
        ],
        "kwargs": {},
    },
}


def build_case(name: str):
    """Build one golden case; returns (patch_dict, (gen, dials, plugout))."""
    case = CASES[name]
    p = Patcher()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result = p.add_m4l_gen_synth(list(case["params"]), **case["kwargs"])
        d = p.to_dict()
    return d, result


@pytest.fixture(scope="module")
def golden():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_fixture_has_exactly_the_four_cases(golden):
    assert list(golden) == list(CASES)


@pytest.mark.parametrize("name", list(CASES))
def test_serialized_output_matches_golden(golden, name):
    actual, _ = build_case(name)
    assert json.dumps(actual, indent=2) == json.dumps(golden[name], indent=2)


@pytest.mark.parametrize("name", list(CASES))
def test_returned_box_ids(name):
    _, (gen, dials, plugout) = build_case(name)
    n = len(CASES[name]["params"])
    assert gen.id == "obj-1"
    assert plugout.id == "obj-2"
    assert [d.id for d in dials] == ["obj-%d" % (3 + i) for i in range(n)]
