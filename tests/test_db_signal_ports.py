"""Q2 regression tests: DB data that made the validator flag valid cords.

Review findings (.planning/reviews/2026-10-11-repo-review.md):
  - A1 (data part): valid cords were flagged/stripped because the audit tool
    wrote ``signal: false`` inlets onto ~36 MSP/MC/Gen objects, and because
    biquad~ / in / peek~ / matrix~ / play~ disagreed with their refpages and
    MAX-saved help boxes.
  - C9 (cause only): ``OverrideGenerator._build_inlet_array`` hard-coded
    ``signal: False``. It now copies signal/type from the current DB entry.

The guard test forbids any overrides.json entry from turning a base signal
inlet into a control inlet unless it is on the reviewed allowlist below.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from src.maxpat.audit.overrides import OverrideGenerator
from src.maxpat.db_lookup import DOMAIN_LOAD_ORDER, ObjectDatabase
from src.maxpat.validation import validate_patch
from tests.test_audit_reporter import (
    make_db_mock_with_objects,
    make_findings,
    make_mock_overrides_file,
)
from tests.test_validation import _make_box, _make_line, _make_patch_dict

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DB_ROOT = _REPO_ROOT / ".claude" / "max-objects"


@pytest.fixture(scope="module")
def db():
    """Shared ObjectDatabase for all tests in this module."""
    return ObjectDatabase()


# ---------------------------------------------------------------------------
# Guard helpers (S1 / S2)
# ---------------------------------------------------------------------------

def _base_entries() -> dict:
    """Pre-override domain-file entries, rebuilt the way ObjectDatabase._load
    does it: DOMAIN_LOAD_ORDER, package subdirectories sorted, last wins."""
    base: dict = {}
    for domain in DOMAIN_LOAD_ORDER:
        if domain == "packages":
            pkg_root = _DB_ROOT / "packages"
            if not pkg_root.is_dir():
                continue
            for pkg_dir in sorted(pkg_root.iterdir()):
                path = pkg_dir / "objects.json"
                if pkg_dir.is_dir() and path.exists():
                    base.update(json.loads(path.read_text()))
        else:
            path = _DB_ROOT / domain / "objects.json"
            if path.exists():
                base.update(json.loads(path.read_text()))
    return base


def _override_objects() -> dict:
    data = json.loads((_DB_ROOT / "overrides.json").read_text())
    return data.get("objects", {})


def _inlet_flips() -> list[tuple[str, int]]:
    """Every (name, index) where an override inlet is control but the base
    inlet at the same index is signal. Indices beyond either array are not
    flips (OQ3-A: those ports belong to Q10)."""
    base = _base_entries()
    flips = []
    for name, ov in _override_objects().items():
        if name.startswith("_") or not isinstance(ov, dict):
            continue
        ov_inlets = ov.get("inlets")
        base_entry = base.get(name)
        if not isinstance(ov_inlets, list) or not isinstance(base_entry, dict):
            continue
        base_inlets = base_entry.get("inlets") or []
        for i in range(min(len(ov_inlets), len(base_inlets))):
            b, o = base_inlets[i], ov_inlets[i]
            if not isinstance(b, dict) or not isinstance(o, dict):
                continue
            if b.get("signal") is True and not o.get("signal"):
                flips.append((name, i))
    return sorted(flips)


# Reviewed exceptions: base says signal, overrides say control, on evidence.
_SIGNAL_DOWNGRADE_ALLOWLIST: dict[tuple[str, int], str] = {
    ("adc~", 0): (
        "adc~ inlet 0 takes only messages (start/stop/set); manual entry "
        "from msp-ref adc~.maxref.xml + saved .maxpat instances, verified "
        "2026-09-27"
    ),
}


class TestOverrideSignalGuard:

    def test_no_unreviewed_signal_downgrades(self):
        unreviewed = [
            f for f in _inlet_flips() if f not in _SIGNAL_DOWNGRADE_ALLOWLIST
        ]
        assert unreviewed == [], (
            f"{len(unreviewed)} override inlet(s) turn a base signal inlet "
            f"into control: {unreviewed}"
        )

    def test_allowlist_entries_are_live_and_reasoned(self):
        live = set(_inlet_flips())
        for key, reason in _SIGNAL_DOWNGRADE_ALLOWLIST.items():
            assert key in live, f"stale allowlist entry {key}: not a live flip"
            assert isinstance(reason, str) and reason.strip(), (
                f"allowlist entry {key} has no reason"
            )


# ---------------------------------------------------------------------------
# Generator (S5)
# ---------------------------------------------------------------------------

_SIGOBJ = {
    "sigobj": {
        "name": "sigobj",
        "domain": "msp",
        "inlets": [
            {"id": 0, "type": "signal", "signal": True},
            {"id": 1, "type": "float", "signal": False},
        ],
        "outlets": [{"id": 0, "type": "signal", "signal": True}],
    },
}


def _generator(tmp_path, objects=None):
    db = make_db_mock_with_objects(copy.deepcopy(objects or _SIGOBJ))
    return OverrideGenerator(db, make_mock_overrides_file(tmp_path))


class TestBuildInletArrayNeverDowngrades:

    def test_io_count_path_copies_signal_and_type(self, tmp_path):
        gen = _generator(tmp_path)
        findings = {
            "sigobj": make_findings(
                name="sigobj",
                io_count_finding={
                    "confidence": "HIGH", "agreement": 1.0, "help_inlets": 3,
                },
            ),
        }
        inlets = gen.generate_proposed_overrides(findings)["objects"]["sigobj"]["inlets"]
        assert [i["signal"] for i in inlets] == [True, False, False]
        assert [i["type"] for i in inlets] == ["signal", "float", ""]

    def test_empty_io_path_copies_signal(self, tmp_path):
        gen = _generator(tmp_path)
        proposed = gen.generate_proposed_overrides(
            {},
            empty_io_data={"objects": {"sigobj": {
                "has_help_data": True, "proposed_inlets": 2,
                "proposed_outlets": 1,
            }}},
        )
        inlets = proposed["objects"]["sigobj"]["inlets"]
        assert inlets[0]["signal"] is True
        assert inlets[0]["type"] == "signal"

    def test_unknown_object_gets_control_default(self, tmp_path):
        gen = _generator(tmp_path)
        proposed = gen.generate_proposed_overrides(
            {},
            empty_io_data={"objects": {"nosuchobj": {
                "has_help_data": True, "proposed_inlets": 2,
                "proposed_outlets": 0,
            }}},
        )
        inlets = proposed["objects"]["nosuchobj"]["inlets"]
        assert [(i["type"], i["signal"]) for i in inlets] == [
            ("", False), ("", False),
        ]

    def test_beyond_db_array_gets_control_default(self, tmp_path):
        gen = _generator(tmp_path)
        arr = gen._build_inlet_array(4, "sigobj")
        assert [(i["type"], i["signal"]) for i in arr] == [
            ("signal", True), ("float", False), ("", False), ("", False),
        ]
        assert all(i["digest"] == "" for i in arr)
        assert [i["id"] for i in arr] == [0, 1, 2, 3]


# ---------------------------------------------------------------------------
# A1 repros
# ---------------------------------------------------------------------------

_EMBED = {"boxes": [], "lines": []}

_CYC = ("cycle~ 440", 2, 1, ["signal"])

# (id, src_text, src_in, src_out, src_outlettype,
#  dst_text, dst_in, dst_out, src_outlet, dst_inlet, embed_patcher)
_A1_REPROS = [
    ("tapin-tapout", "tapin~ 1000", 1, 1, ["tapconnect"],
     "tapout~ 500", 1, 1, 0, 0, False),
    ("cycle-poly", *_CYC, "poly~ voice 4", 1, 1, 0, 0, False),
    ("cycle-pfft", *_CYC, "pfft~ fx 1024", 1, 1, 0, 0, False),
    ("cycle-rnbo", *_CYC, "rnbo~", 1, 1, 0, 0, False),
    ("cycle-p", *_CYC, "p synth", 1, 1, 0, 0, True),
    ("cycle-sfrecord", *_CYC, "sfrecord~ 2", 2, 1, 0, 0, False),
    ("cycle-vst", *_CYC, "vst~", 2, 8, 0, 0, False),
    ("cycle-pitchshift", *_CYC, "pitchshift~", 3, 1, 0, 0, False),
    ("cycle-fffb", *_CYC, "fffb~ 4", 1, 4, 0, 0, False),
    ("cycle-mc.snapshot", *_CYC, "mc.snapshot~", 2, 1, 0, 0, False),
]


def _two_box_patch(src_text, src_in, src_out, src_outlettype,
                   dst_text, dst_in, dst_out, src_outlet, dst_inlet,
                   embed=False):
    dst = _make_box("obj-2", text=dst_text, numinlets=dst_in,
                    numoutlets=dst_out, outlettype=[""] * dst_out or None)
    if embed:
        dst["box"]["patcher"] = copy.deepcopy(_EMBED)
    return _make_patch_dict(
        boxes=[
            _make_box("obj-1", text=src_text, numinlets=src_in,
                      numoutlets=src_out, outlettype=src_outlettype),
            dst,
        ],
        lines=[_make_line("obj-1", src_outlet, "obj-2", dst_inlet)],
    )


def _conn(results):
    return [r for r in results if r.layer == "connections"]


def _keys(patch_dict):
    return [
        (ln["patchline"]["source"][0], ln["patchline"]["source"][1],
         ln["patchline"]["destination"][0], ln["patchline"]["destination"][1])
        for ln in patch_dict["patcher"]["lines"]
    ]


class TestA1Repros:

    @pytest.mark.parametrize(
        "case", _A1_REPROS, ids=[c[0] for c in _A1_REPROS],
    )
    def test_cord_kept_without_connection_findings(self, db, case):
        (_id, s_text, s_in, s_out, s_ot, d_text, d_in, d_out,
         s_outlet, d_inlet, embed) = case
        patch = _two_box_patch(s_text, s_in, s_out, s_ot, d_text, d_in,
                               d_out, s_outlet, d_inlet, embed)
        before = copy.deepcopy(patch)
        results = validate_patch(patch, db=db)
        assert _conn(results) == [], [str(r) for r in _conn(results)]
        assert patch == before
        assert _keys(patch) == [("obj-1", s_outlet, "obj-2", d_inlet)]

    def test_anchor_signal_into_print_still_proposed(self, db):
        patch = _two_box_patch(*_CYC, "print", 1, 0, 0, 0)
        results = validate_patch(patch, db=db)
        proposed = [r.proposed_removal for r in results
                    if r.proposed_removal is not None]
        assert proposed == [("obj-1", 0, "obj-2", 0)]


# ---------------------------------------------------------------------------
# Committed patches (read-only)
# ---------------------------------------------------------------------------

_COMMITTED = [
    "patches/mixer/generated/mixer-strip.maxpat",
    "patches/terrain-synth/generated/terrain-voice.maxpat",
    "patches/scala-synth/generated/scala-synth-voice.maxpat",
]


def _load_patch(rel):
    with open(_REPO_ROOT / rel) as f:
        return copy.deepcopy(json.load(f))


class TestCommittedPatchesZeroProposed:

    @pytest.mark.parametrize("rel", _COMMITTED)
    def test_zero_proposed_removals(self, db, rel):
        results = validate_patch(_load_patch(rel), db=db)
        proposed = [r for r in results if r.proposed_removal is not None]
        assert proposed == [], [str(r) for r in proposed]
