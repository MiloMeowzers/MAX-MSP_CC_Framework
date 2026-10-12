"""Q1 regression tests: validate_patch is non-destructive.

Review findings A2 / A1 (API part) / A8 (.planning/reviews/2026-10-11-*):
  - validate_patch never mutates its input; dict and Patcher input agree.
  - Cords the validator would drop are reported as ``proposed_removal``
    4-tuples and only removed by an explicit ``apply_fixes`` call.
  - ``has_blocking_errors`` blocks proposed removals for new patches.
  - Container boxes (p / patcher / bpatcher / poly~ / mc.poly~ / pfft~ /
    rnbo~ / any embedded patcher) accept any cord.
  - signal_role mismatches warn, never remove.
  - The 3 committed patches that used to lose a working cord keep it.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from src.maxpat.db_lookup import ObjectDatabase
from src.maxpat.patcher import Patcher
from src.maxpat.validation import (
    ValidationResult,
    apply_fixes,
    has_blocking_errors,
    validate_patch,
)
from tests.test_validation import _make_box, _make_line, _make_patch_dict

_REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def db():
    """Shared ObjectDatabase for all tests in this module."""
    return ObjectDatabase()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _fixture_dict():
    """line~ -> print (legacy signal into control-only inlet),
    cycle~ outlet 2 -> *~ (out of bounds), cycle~ -> *~ (valid)."""
    boxes = [
        _make_box("obj-1", text="line~", numinlets=2, numoutlets=2,
                  outlettype=["signal", ""]),
        _make_box("obj-2", text="print", numinlets=1, numoutlets=0,
                  outlettype=[]),
        _make_box("obj-3", text="cycle~ 440", numinlets=2, numoutlets=1,
                  outlettype=["signal"]),
        _make_box("obj-4", text="*~ 0.5", numinlets=2, numoutlets=1,
                  outlettype=["signal"]),
    ]
    lines = [
        _make_line("obj-1", 0, "obj-2", 0),
        _make_line("obj-3", 2, "obj-4", 0),
        _make_line("obj-3", 0, "obj-4", 0),
    ]
    return _make_patch_dict(boxes=boxes, lines=lines)


def _sig(results):
    return [(r.layer, r.level, r.message, r.proposed_removal) for r in results]


def _keys(patch_dict):
    return [
        (ln["patchline"]["source"][0], ln["patchline"]["source"][1],
         ln["patchline"]["destination"][0], ln["patchline"]["destination"][1])
        for ln in patch_dict["patcher"]["lines"]
    ]


def _conn(results):
    return [r for r in results if r.layer == "connections"]


def _proposed(results):
    return [r.proposed_removal for r in results if r.proposed_removal is not None]


# ===========================================================================
# Tests 1-2: purity and dict/Patcher identity (A2)
# ===========================================================================

class TestPurity:

    def test_dict_input_unchanged(self, db):
        patch = _fixture_dict()
        before = copy.deepcopy(patch)
        validate_patch(patch, db=db)
        assert patch == before

    def test_patcher_input_unchanged(self, db):
        p = Patcher.from_dict(copy.deepcopy(_fixture_dict()), db=db)
        before = p.to_dict()
        validate_patch(p, db=db)
        assert len(p.lines) == 3
        assert p.to_dict() == before

    def test_dict_and_patcher_results_identical(self, db):
        patch = _fixture_dict()
        p = Patcher.from_dict(copy.deepcopy(patch), db=db)
        assert _sig(validate_patch(patch, db=db)) == _sig(validate_patch(p, db=db))


# ===========================================================================
# Tests 3-5: proposed removals are data
# ===========================================================================

class TestProposedRemoval:

    def test_out_of_bounds_outlet_proposed(self, db):
        results = validate_patch(_fixture_dict(), db=db)
        hits = [r for r in results if r.proposed_removal == ("obj-3", 2, "obj-4", 0)]
        assert len(hits) == 1
        assert hits[0].level == "error"
        assert "proposed removal" in hits[0].message

    def test_out_of_bounds_inlet_proposed(self, db):
        patch = _make_patch_dict(
            boxes=[
                _make_box("obj-3", text="cycle~ 440", numoutlets=1),
                _make_box("obj-4", text="*~ 0.5", numinlets=2, numoutlets=1),
            ],
            lines=[_make_line("obj-3", 0, "obj-4", 5)],
        )
        results = validate_patch(patch, db=db)
        hits = [r for r in results if r.proposed_removal == ("obj-3", 0, "obj-4", 5)]
        assert len(hits) == 1
        assert hits[0].level == "error"
        assert "proposed removal" in hits[0].message

    def test_signal_to_control_proposed_and_valid_cord_not(self, db):
        results = validate_patch(_fixture_dict(), db=db)
        proposed = _proposed(results)
        assert ("obj-1", 0, "obj-2", 0) in proposed
        assert ("obj-3", 0, "obj-4", 0) not in proposed

    def test_malformed_line_proposed_and_applied(self, db):
        patch = _make_patch_dict(
            boxes=[
                _make_box("obj-1", text="cycle~ 440", numoutlets=1),
                _make_box("obj-2", text="*~ 0.5", numinlets=2, numoutlets=1),
            ],
            lines=[{"patchline": {"source": ["obj-1"], "destination": ["obj-2", 0]}}],
        )
        results = validate_patch(patch, db=db)
        hits = [r for r in results
                if r.proposed_removal == ("obj-1", None, "obj-2", 0)]
        assert len(hits) == 1 and hits[0].level == "error"
        assert len(patch["patcher"]["lines"]) == 1  # not removed by validation
        assert apply_fixes(patch, results) == [("obj-1", None, "obj-2", 0)]
        assert patch["patcher"]["lines"] == []

    def test_validation_result_default_and_coercion(self):
        assert ValidationResult("json", "error", "m").proposed_removal is None
        r = ValidationResult("connections", "error", "m",
                             proposed_removal=["obj-1", 0, "obj-2", 0])
        assert r.proposed_removal == ("obj-1", 0, "obj-2", 0)
        assert isinstance(r.proposed_removal, tuple)


# ===========================================================================
# Tests 6-7: apply_fixes is the only path that removes
# ===========================================================================

class TestApplyFixes:

    def test_package_export(self):
        from src.maxpat import apply_fixes as exported
        assert exported is apply_fixes

    def test_apply_fixes_dict(self, db):
        patch = _fixture_dict()
        lines_ref = patch["patcher"]["lines"]
        results = validate_patch(patch, db=db)
        applied = apply_fixes(patch, results)
        assert sorted(applied, key=str) == sorted(
            [("obj-1", 0, "obj-2", 0), ("obj-3", 2, "obj-4", 0)], key=str)
        assert _keys(patch) == [("obj-3", 0, "obj-4", 0)]
        assert patch["patcher"]["lines"] is lines_ref  # slice-assigned
        assert _proposed(validate_patch(patch, db=db)) == []
        assert apply_fixes(patch, results) == []

    def test_apply_fixes_patcher(self, db):
        p = Patcher.from_dict(copy.deepcopy(_fixture_dict()), db=db)
        results = validate_patch(p, db=db)
        applied = apply_fixes(p, results)
        assert len(applied) == 2
        assert len(p.lines) == 1
        line = p.lines[0]
        assert (line.source_id, line.source_outlet, line.dest_id, line.dest_inlet) \
            == ("obj-3", 0, "obj-4", 0)
        assert apply_fixes(p, results) == []

    def test_warning_only_results_change_nothing(self, db):
        patch = _fixture_dict()
        before = copy.deepcopy(patch)
        warns = [ValidationResult("connections", "warning", "w")]
        assert apply_fixes(patch, warns) == []
        assert patch == before

    def test_dict_without_lines_is_noop(self):
        results = [ValidationResult("connections", "error", "e",
                                    proposed_removal=("a", 0, "b", 0))]
        assert apply_fixes({"patcher": {}}, results) == []
        assert apply_fixes({}, results) == []


# ===========================================================================
# Test 8: has_blocking_errors blocks proposed removals for new patches
# ===========================================================================

class TestHasBlockingErrorsQ1:

    def test_proposed_removals_block_new(self, db):
        results = validate_patch(_fixture_dict(), db=db)
        errors = [r for r in results if r.level == "error"]
        assert errors and all(r.proposed_removal is not None for r in errors)
        assert has_blocking_errors(results) is True
        assert has_blocking_errors(results, is_new=True) is True
        assert has_blocking_errors(results, is_new=False) is False

    def test_plain_error_blocks_both(self):
        results = [ValidationResult("objects", "error", "unknown")]
        assert has_blocking_errors(results) is True
        assert has_blocking_errors(results, is_new=False) is True

    def test_legacy_auto_fixed_does_not_block(self):
        results = [ValidationResult("connections", "error", "x", auto_fixed=True)]
        assert has_blocking_errors(results) is False
        assert has_blocking_errors(results, is_new=False) is False


# ===========================================================================
# Tests 9-11: containers accept any cord (A1)
# ===========================================================================

_EMBED = {"boxes": [], "lines": []}


def _container_box(kind):
    if kind == "bpatcher":
        b = _make_box("obj-2", maxclass="bpatcher", text="", numinlets=1,
                      numoutlets=1, outlettype=[""])
        b["box"].pop("text")
        return b
    text = {
        "poly~": "poly~ voice 4",
        "mc.poly~": "mc.poly~ voice 4",
        "pfft~": "pfft~ fx 1024",
        "rnbo~": "rnbo~",
        "p": "p synth",
        "patcher": "patcher synth",
        "embedded-print": "print",
    }[kind]
    b = _make_box("obj-2", text=text, numinlets=1, numoutlets=1, outlettype=[""])
    if kind in ("p", "patcher", "embedded-print"):
        b["box"]["patcher"] = copy.deepcopy(_EMBED)
    return b


class TestContainers:

    @pytest.mark.parametrize("kind", [
        "poly~", "mc.poly~", "pfft~", "rnbo~", "p", "patcher", "bpatcher",
        "embedded-print",
    ])
    def test_signal_into_container_kept(self, db, kind):
        patch = _make_patch_dict(
            boxes=[
                _make_box("obj-1", text="cycle~ 440", numoutlets=1),
                _container_box(kind),
            ],
            lines=[_make_line("obj-1", 0, "obj-2", 0)],
        )
        before = copy.deepcopy(patch)
        results = validate_patch(patch, db=db)
        assert _conn(results) == [], [str(r) for r in _conn(results)]
        assert _keys(patch) == [("obj-1", 0, "obj-2", 0)]
        assert patch == before

    @pytest.mark.parametrize("text", ["pfft~ fx 1024", "mc.poly~ voice 4"])
    def test_container_source_has_no_role(self, db, text):
        patch = _make_patch_dict(
            boxes=[
                _make_box("obj-1", text=text, numinlets=1, numoutlets=1,
                          outlettype=["signal"]),
                _make_box("obj-2", text="*~ 0.5", numinlets=2, numoutlets=1),
            ],
            lines=[_make_line("obj-1", 0, "obj-2", 0)],
        )
        results = validate_patch(patch, db=db)
        assert _conn(results) == [], [str(r) for r in _conn(results)]

    def test_container_bounds_still_enforced(self, db):
        patch = _make_patch_dict(
            boxes=[
                _make_box("obj-1", text="cycle~ 440", numoutlets=1),
                _container_box("p"),
            ],
            lines=[_make_line("obj-1", 0, "obj-2", 3)],
        )
        results = validate_patch(patch, db=db)
        assert ("obj-1", 0, "obj-2", 3) in _proposed(results)


# ===========================================================================
# Test 12: role mismatches warn, never remove (A1)
# ===========================================================================

class TestRoleMismatchWarns:

    def test_status_into_signal_is_warning(self, db, monkeypatch):
        monkeypatch.setattr(
            db, "get_signal_role",
            lambda name, outlet, args=None: "status" if name == "status_x" else None,
        )
        patch = _make_patch_dict(
            boxes=[
                _make_box("obj-1", text="status_x", numoutlets=1),
                _make_box("obj-2", text="*~ 0.5", numinlets=2, numoutlets=1),
            ],
            lines=[_make_line("obj-1", 0, "obj-2", 0)],
        )
        results = validate_patch(patch, db=db)
        conn = _conn(results)
        assert len(conn) == 1, [str(r) for r in conn]
        r = conn[0]
        assert r.level == "warning"
        assert r.proposed_removal is None
        assert "use snapshot~" in r.message
        assert "'obj-1'" in r.message and "'obj-2'" in r.message
        assert _keys(patch) == [("obj-1", 0, "obj-2", 0)]

    def test_tier_table_is_warning_only(self):
        from src.maxpat.validation import _ROLE_TIER_TABLE
        assert all(v[0] == "warning" for v in _ROLE_TIER_TABLE.values())


# ===========================================================================
# Test 13: the 3 committed patches that used to lose a cord (A1/A8)
# ===========================================================================

class TestCommittedStrips:

    @pytest.mark.parametrize("rel,src,outlet,dst,inlet", [
        ("patches/mixer/generated/mixer-strip.maxpat", "obj-15", 0, "obj-37", 0),
        ("patches/terrain-synth/generated/terrain-voice.maxpat", "obj-16", 0, "obj-60", 0),
        ("patches/scala-synth/generated/scala-synth-voice.maxpat", "obj-1", 0, "obj-3", 0),
    ])
    def test_cord_kept(self, db, rel, src, outlet, dst, inlet):
        with open(_REPO_ROOT / rel) as f:
            patch = json.load(f)
        before = copy.deepcopy(patch)
        results = validate_patch(patch, db=db)
        assert patch == before
        assert _proposed(results) == [], [str(r) for r in results
                                          if r.proposed_removal is not None]
        assert (src, outlet, dst, inlet) in _keys(patch)
        if "terrain-voice" in rel:
            assert not [r for r in results
                        if "Unterminated signal chain: '*~' (obj-16)" in r.message]


# ===========================================================================
# Tests 14-17: relationships.json pairs are never flagged (A1)
# ===========================================================================

class TestKnownPairs:

    def _tap_patch(self, src_outlet=0):
        return _make_patch_dict(
            boxes=[
                _make_box("obj-1", text="tapin~ 1000", numinlets=1,
                          numoutlets=1, outlettype=["tapconnect"]),
                _make_box("obj-2", text="tapout~ 500", numinlets=1,
                          numoutlets=1, outlettype=["signal"]),
            ],
            lines=[_make_line("obj-1", src_outlet, "obj-2", 0)],
        )

    def test_tapin_to_tapout_not_flagged(self, db):
        patch = self._tap_patch()
        before = copy.deepcopy(patch)
        results = validate_patch(patch, db=db)
        assert _conn(results) == [], [str(r) for r in _conn(results)]
        assert _keys(patch) == [("obj-1", 0, "obj-2", 0)]
        assert patch == before

    def test_is_known_pair(self, db):
        assert db.is_known_pair("tapin~", "tapout~")
        assert db.is_known_pair("tapout~", "tapin~")
        assert db.is_known_pair("pfft~", "fftin~")
        assert db.is_known_pair("fftin~", "fftout~")
        assert db.is_known_pair("s", "r")
        assert not db.is_known_pair("cycle~", "dac~")
        assert not db.is_known_pair("tapin~", "tapin~")

    def test_known_pair_bounds_still_enforced(self, db):
        results = validate_patch(self._tap_patch(src_outlet=3), db=db)
        hits = [r for r in results if r.proposed_removal == ("obj-1", 3, "obj-2", 0)]
        assert len(hits) == 1 and hits[0].level == "error"

    def test_missing_relationships_file(self, tmp_path):
        empty_db = ObjectDatabase(db_root=tmp_path)
        assert empty_db.is_known_pair("tapin~", "tapout~") is False
