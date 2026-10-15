"""Integration tests: run validate_patch() and review_patch() on every real .maxpat.

Parametrized over patches/*/generated/*.maxpat to catch regressions.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from src.maxpat.db_lookup import ObjectDatabase
from src.maxpat.validation import validate_patch, has_blocking_errors
from src.maxpat.critics import review_patch

# ---------------------------------------------------------------------------
# Discover all real .maxpat files
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent
_PATCH_FILES = sorted(_REPO_ROOT.glob("patches/*/generated/*.maxpat"))

# ---------------------------------------------------------------------------
# Review-blocker allowlist (true positives in frozen committed patches)
# ---------------------------------------------------------------------------
# The committed .maxpat files are frozen (never edited to satisfy critics).
# review_blocker_allowlist.json exempts specific, signature-scoped blockers in
# those patches for test_review_patch_no_blockers only. Until Q3 (quick
# 261012-di7) it held 120 "debt" entries; most were critic false positives
# (display-only sinks, preset membership cords, non-reconvergent fan-out, Bach
# command messages) and were removed once the critics stopped emitting them.
# Every remaining entry is a live true positive with a written `reason`;
# test_review_allowlist_entries_are_live fails on stale entries, missing files
# and missing reasons, and calibration-project patches may never appear here.
# A NEW patch (path absent from the allowlist) or a NEW blocker (signature not
# explicitly listed for its patch) is never exempted -- it still fails.
# Keys include the CriticResult path (Q20): an entry's optional `path`
# (default "", the top level) must equal the blocker's scope path, so a
# nested blocker is never exempted by a top-level entry with the same id.
_ALLOWLIST_PATH = Path(__file__).resolve().parent / "review_blocker_allowlist.json"
with open(_ALLOWLIST_PATH) as _f:
    _ALLOWLIST = json.load(_f).get("patches", {})

# Blocker finding-string formats are fixed by the critics:
#   Fan-out:  "Fan-out without trigger: '<name>' (<source_id>) outlet <N> ..."
#   Bach-llll: "Bach llll type mismatch: '<name>' (<source_id>) connected to
#               '<dst>' (<dst_id>) inlet <N> which expects llll data ..."
_FANOUT_RE = re.compile(
    r"Fan-out without trigger: '[^']*' \(([^)]+)\) outlet (\d+) "
    r"connected to \d+ destinations \((.*?)\) --"
)
_BACH_RE = re.compile(
    r"Bach llll type mismatch: '[^']*' \(([^)]+)\) connected to "
    r"'([^']*)' \([^)]+\) inlet (\d+)"
)
_DST_NAME_RE = re.compile(r"'([^']*)' \([^)]+\)")


def _blocker_match_key(finding: str):
    """Derive a signature key from a blocker finding string, or None if the
    blocker is not an allowlist-eligible kind (fan-out / Bach-llll).

    Keys mirror the allowlist entry keys:
      fan-out   -> ("fanout", source_id, outlet)
      Bach-llll -> ("bach_llll", source_id, inlet, (sorted destinations))
    """
    m = _FANOUT_RE.search(finding)
    if m:
        source_id, outlet, _dsts = m.groups()
        return ("fanout", source_id, int(outlet))
    mb = _BACH_RE.search(finding)
    if mb:
        source_id, dst, inlet = mb.groups()
        return ("bach_llll", source_id, int(inlet), (dst,))
    return None


def _entry_key(entry: dict):
    """Derive the same signature key from an allowlist entry."""
    kind = entry.get("kind")
    if kind == "fanout":
        return ("fanout", entry["source_id"], int(entry["outlet"]))
    if kind == "bach_llll":
        dsts = tuple(sorted(entry.get("destinations", [])))
        return ("bach_llll", entry["source_id"], int(entry["inlet"]), dsts)
    return None


def _result_key(result):
    """Signature key of a CriticResult blocker: finding key + scope path."""
    key = _blocker_match_key(result.finding)
    if key is None:
        return None
    return key + (getattr(result, "path", ""),)


def _allow_key(entry: dict):
    """Signature key of an allowlist entry: entry key + its `path` (default "")."""
    key = _entry_key(entry)
    if key is None:
        return None
    return key + (entry.get("path", ""),)


def _is_allowlisted(patch_rel: str, result) -> bool:
    """True only if `patch_rel` has an allowlist list AND the blocker's
    signature (including its CriticResult path) matches one of that patch's
    explicit entries."""
    entries = _ALLOWLIST.get(patch_rel)
    if not entries:
        return False
    key = _result_key(result)
    if key is None:
        return False
    return any(_allow_key(e) == key for e in entries)

# Known issues: patches that fail specific tests with documented reasons.
# Marked xfail(strict=True): when the blocker is fixed the case XPASSes and
# fails, forcing the entry to be deleted (review A8).
_REVIEW_XFAILS: dict[str, str] = {}


@pytest.fixture(scope="module")
def db() -> ObjectDatabase:
    """Module-scoped ObjectDatabase (expensive to construct)."""
    return ObjectDatabase()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_review_params() -> list:
    """Build parametrize list, applying xfail marks to known-failing patches."""
    params = []
    for p in _PATCH_FILES:
        reason = _REVIEW_XFAILS.get(p.name)
        if reason:
            params.append(pytest.param(
                p, marks=pytest.mark.xfail(reason=reason, strict=True)))
        else:
            params.append(p)
    return params


# ---------------------------------------------------------------------------
# Test 1: validate_patch produces zero errors and zero proposed removals
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "patch_path",
    _PATCH_FILES,
    ids=[str(p.relative_to(_REPO_ROOT)) for p in _PATCH_FILES],
)
def test_validate_patch_no_errors(patch_path: Path, db: ObjectDatabase) -> None:
    with open(patch_path) as f:
        patch_dict = json.load(f)

    results = validate_patch(patch_dict, db)
    # A proposed removal means the validator would drop a cord from a
    # committed (user-confirmed) patch -- that is a failure, not a fix (A8).
    blocking = [
        r for r in results
        if r.level == "error" or r.proposed_removal is not None
    ]

    assert not blocking, (
        f"{len(blocking)} error(s) / proposed removal(s) in {patch_path.name}:\n"
        + "\n".join(
            f"  - {r}"
            + (f"  [proposed_removal={r.proposed_removal}]"
               if r.proposed_removal is not None else "")
            for r in blocking
        )
    )


# ---------------------------------------------------------------------------
# Test 2: review_patch produces zero blockers
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "patch_path",
    _make_review_params(),
    ids=[str(p.relative_to(_REPO_ROOT)) for p in _PATCH_FILES],
)
def test_review_patch_no_blockers(patch_path: Path, db: ObjectDatabase) -> None:
    with open(patch_path) as f:
        patch_dict = json.load(f)

    results = review_patch(patch_dict)
    blockers = [r for r in results if r.severity == "blocker"]

    # Filter out documented pre-existing blocker debt via the per-patch,
    # signature-scoped allowlist. A blocker survives filtering unless the
    # current patch has an explicit allowlist entry matching its signature,
    # so new patches / new blockers still fail this test.
    patch_rel = patch_path.relative_to(_REPO_ROOT).as_posix()
    remaining = [b for b in blockers if not _is_allowlisted(patch_rel, b)]

    assert not remaining, (
        f"{len(remaining)} unallowlisted blocker(s) in {patch_path.name}:\n"
        + "\n".join(f"  - {r}" for r in remaining)
    )


# ---------------------------------------------------------------------------
# Test 3: allowlist hygiene (Q3, S10)
# ---------------------------------------------------------------------------

# User-confirmed projects (review §0 / §4.3 / §4.4 R3, fix-plan Q3): their
# generated patches must review with zero blockers and no allowlist.
_CALIBRATION_PROJECTS = (
    "ji-harmonizer", "terrain-synth", "wormhole", "timestretch", "gong-model",
    "gen-eq", "kicksynth", "granularsynthtest", "performancepatchtest",
    "physics-composition", "barnett-dbap", "scala-synth",
)
_CALIBRATION_FILES = [
    path
    for project in _CALIBRATION_PROJECTS
    for path in sorted(_REPO_ROOT.glob(f"patches/{project}/generated/*.maxpat"))
]


def _project_of(patch_rel: str) -> str:
    parts = patch_rel.split("/")
    return parts[1] if len(parts) > 1 and parts[0] == "patches" else ""


def test_review_allowlist_entries_are_live() -> None:
    """Every allowlist entry names an existing file, carries a reason, and
    matches a blocker review_patch emits on that file today."""
    problems = []
    for patch_rel, entries in sorted(_ALLOWLIST.items()):
        path = _REPO_ROOT / patch_rel
        if not path.is_file():
            problems.append(f"{patch_rel}: file missing ({len(entries)} entries)")
            continue
        with open(path) as f:
            live = {
                _result_key(r)
                for r in review_patch(json.load(f))
                if r.severity == "blocker"
            }
        for entry in entries:
            reason = entry.get("reason")
            if not (isinstance(reason, str) and reason.strip()):
                problems.append(f"{patch_rel}: no reason for {_allow_key(entry)}")
            if _allow_key(entry) not in live:
                problems.append(f"{patch_rel}: stale (does not fire) {_allow_key(entry)}")
    assert not problems, (
        f"{len(problems)} allowlist problem(s):\n"
        + "\n".join(f"  - {p}" for p in problems)
    )


def test_review_allowlist_excludes_calibration_projects() -> None:
    bad = sorted(k for k in _ALLOWLIST if _project_of(k) in _CALIBRATION_PROJECTS)
    assert not bad, f"calibration-project patches in the allowlist: {bad}"


def test_calibration_projects_have_patches() -> None:
    """A rename must not silently empty the calibration gate."""
    empty = [
        p for p in _CALIBRATION_PROJECTS
        if not list(_REPO_ROOT.glob(f"patches/{p}/generated/*.maxpat"))
    ]
    assert not empty, f"calibration projects with no generated patches: {empty}"


# ---------------------------------------------------------------------------
# Test 4: user-confirmed calibration patches have zero blockers (Q3, S9)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "patch_path",
    _CALIBRATION_FILES,
    ids=[str(p.relative_to(_REPO_ROOT)) for p in _CALIBRATION_FILES],
)
def test_calibration_zero_blockers(patch_path: Path) -> None:
    """No allowlist: a blocker on a user-confirmed patch is a critic bug."""
    with open(patch_path) as f:
        patch_dict = json.load(f)
    blockers = [r for r in review_patch(patch_dict) if r.severity == "blocker"]
    assert blockers == [], (
        f"{len(blockers)} blocker(s) in user-confirmed {patch_path.name}:\n"
        + "\n".join(f"  - {r}" for r in blockers)
    )


def test_allowlist_key_includes_path() -> None:
    """A nested blocker never matches a top-level allowlist entry (Q20)."""
    from src.maxpat.critics.base import CriticResult

    patch_rel = "patches/rhythmic-sampler/generated/slot.maxpat"
    finding = (
        "Fan-out without trigger: 'buffer~' (obj-1) outlet 1 connected to 2 "
        "destinations ('message' (obj-27), 'message' (obj-28)) -- paths "
        "reconverge on 'waveform~' (obj-4) at different inlets, so execution "
        "order changes the result"
    )
    nested = CriticResult("blocker", "[p x] " + finding, "s", path="obj-9")
    top = CriticResult("blocker", finding, "s")
    assert not _is_allowlisted(patch_rel, nested)
    assert _is_allowlisted(patch_rel, top)
