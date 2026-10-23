"""WP7a (quick 261022-ud6): WP5 handoff. The phasor-domain timing patterns
carry a ``// smoke:`` directive (``in1=phasor:2 control out1``), so a bare
``smoke`` run drives them with a phasor like their pattern tests do and
judges out1 as control, at every corner.
"""
import json
from pathlib import Path

import pytest

from src.maxpat.dsp_sim.smoke import smoke_file

_REPO = Path(__file__).resolve().parents[2]
_TIMING = _REPO / "patterns" / "gen" / "timing"


@pytest.mark.parametrize("name", ["swing-generator.gendsp", "subdivider.gendsp"])
def test_codebox_carries_smoke_directive(name):
    d = json.loads((_TIMING / name).read_text())
    (code,) = [b["box"]["code"] for b in d["patcher"]["boxes"] if b["box"]["maxclass"] == "codebox"]
    assert "// smoke: in1=phasor:2 control out1" in code


@pytest.mark.parametrize("name", ["swing-generator.gendsp", "subdivider.gendsp"])
def test_bare_smoke_passes_at_every_corner(name):
    (r,) = smoke_file(_TIMING / name, seconds=0.25, corners="all")
    assert r.verdict == "pass", r
