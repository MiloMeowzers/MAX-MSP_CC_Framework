"""Repo-wide smoke verdict pin (261022-ud6 CR-01 / spec gap 2).

Every committed .gendsp and gen~ .maxpat is smoked and each codebox's
verdict is compared with tests/dsp_sim/fixtures/repo_smoke_verdicts.json, so
a change to the smoke checks shows its false-FAIL delta on real, mostly
MAX-confirmed codeboxes instead of only on fixtures.

* Default run: the default corner at 0.05 s (about 10 s).
* ``DSP_SIM_REPO_SWEEP=1``: also every corner at 0.25 s (about 15 minutes),
  the setting the 261022-ud6 review used.

A pinned verdict that changes fails; so does a new committed codebox whose
verdict is fail or unsupported (pin it, with a reason, if that is intended).
A pinned codebox that no longer exists is ignored.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from src.maxpat.dsp_sim.smoke import discover_codeboxes, smoke_file

_REPO = Path(__file__).resolve().parents[2]
_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "repo_smoke_verdicts.json"


def _committed_gen_files() -> list:
    try:
        out = subprocess.run(
            ["git", "ls-files", "*.gendsp", "*.maxpat"], cwd=_REPO,
            capture_output=True, text=True, timeout=60, check=True,
        ).stdout.split()
    except (OSError, subprocess.SubprocessError):
        pytest.skip("git ls-files unavailable")
    files = []
    for rel in out:
        path = _REPO / rel
        if not path.is_file():
            continue
        if rel.endswith(".maxpat") and "gen~" not in path.read_text(errors="ignore"):
            continue
        files.append(rel)
    return files


def _sweep(seconds: float, corners: str) -> dict:
    verdicts: dict = {}
    for rel in _committed_gen_files():
        for r in smoke_file(_REPO / rel, seconds=seconds, corners=corners):
            verdicts[f"{rel} :: {r.label}"] = r.verdict
    return verdicts


def _compare(actual: dict, pinned: dict) -> None:
    changed = {k: f"{pinned[k]} -> {v}" for k, v in actual.items() if k in pinned and pinned[k] != v}
    new_bad = {k: v for k, v in actual.items() if k not in pinned and v in ("fail", "unsupported")}
    msg = []
    if changed:
        msg.append("verdicts changed:\n" + "\n".join(f"  {k}: {d}" for k, d in sorted(changed.items())))
    if new_bad:
        msg.append("new failing/unsupported codeboxes (pin them with a reason if intended):\n"
                   + "\n".join(f"  {k}: {v}" for k, v in sorted(new_bad.items())))
    assert not msg, "\n".join(msg)


def _pinned(section: str) -> dict:
    return json.loads(_FIXTURE.read_text())[section]


def test_repo_smoke_default_corner_verdicts_are_pinned():
    _compare(_sweep(0.05, "default"), _pinned("default_corner_0.05s"))


@pytest.mark.slow
@pytest.mark.skipif(os.environ.get("DSP_SIM_REPO_SWEEP") != "1",
                    reason="full repo smoke sweep (~15 min): set DSP_SIM_REPO_SWEEP=1")
def test_repo_smoke_all_corner_verdicts_are_pinned():
    _compare(_sweep(0.25, "all"), _pinned("all_corners_0.25s"))


# The review's false FAILs: each outlet that carries Hz, ms, sample indices,
# voice data or state flags is control; each trigger inlet is trigger.
_REVIEW_PORTS = [
    ("patches/minitaur/generated/minitaur.maxpat", "p filter > gen~ > codebox 1", "out", 1, "control"),
    ("patches/minitaur/generated/minitaur.maxpat", "p glide > gen~ > codebox 1", "out", 1, "control"),
    ("patches/granularsynthtest/generated/granular-sched.gendsp", "codebox 1", "out", 2, "control"),
    ("patches/granularsynthtest/generated/granular-sched.gendsp", "codebox 1", "out", 4, "control"),
    ("patches/sample-layers/generated/sample-layers-slot.maxpat", "codebox 1", "out", 3, "control"),
    ("patches/sample-layers/generated/sample-layers-slot.maxpat", "codebox 1", "out", 4, "control"),
    ("patches/sample-layers/generated/sample-layers-slot.maxpat", "codebox 1", "out", 1, "audio"),
    ("patches/terrain-synth/generated/terrain-voice.maxpat", "codebox 1 (#4)", "out", 1, "control"),
    ("patches/timestretch/generated/timestretch.maxpat", "codebox 1", "out", 2, "control"),
    ("patches/timestretch/generated/timestretch.maxpat", "codebox 1", "out", 1, "audio"),
    ("patches/kicksynth/generated/kicksynth.maxpat", "gen~ > codebox 1", "in", 1, "trigger"),
    ("patches/kicksynth/generated/kicksynth.maxpat", "gen~ > codebox 1", "out", 1, "audio"),
    ("patches/stutter/generated/stutter-engine.gendsp", "codebox 1", "out", 1, "audio"),
    ("patches/stutter/generated/stutter-engine.gendsp", "codebox 1", "out", 2, "audio"),
    ("patches/stutter/generated/stutter-engine.gendsp", "codebox 1", "out", 3, "control"),
    ("patches/terrain-synth/generated/terrain-osc.maxpat", "codebox 1", "in", 1, "control"),
    ("patches/terrain-synth/generated/terrain-osc.maxpat", "codebox 1", "out", 1, "audio"),
    ("patches/ji-harmonizer/generated/ji-harmonizer.maxpat", "mc.gen~ > codebox 1", "out", 1, "audio"),
]


@pytest.mark.parametrize("rel,label,side,k,kind", _REVIEW_PORTS,
                         ids=[f"{Path(r).stem}-{s}{k}" for r, _l, s, k, _x in _REVIEW_PORTS])
def test_review_codebox_port_kinds(rel, label, side, k, kind):
    entries = [e for e in discover_codeboxes(_REPO / rel)
               if e.status == "ok" and e.label.endswith(label)]
    assert entries, [e.label for e in discover_codeboxes(_REPO / rel)]
    ports = entries[0].ports
    assert ports is not None, entries[0].label
    got = (ports.inputs if side == "in" else ports.outputs)[k]
    assert got == kind, (entries[0].label, ports.notes)
