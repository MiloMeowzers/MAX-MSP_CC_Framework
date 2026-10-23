"""Tests for ObjectDatabase empty-I/O health check.

Guards against silent patch-generation failures caused by DB entries with
empty inlets AND empty outlets (130 such entries on the live DB as of
2026-04-19; most recent regression was live.scope~). Verifies:
  - has_complete_io() predicate, including the variable_io exemption
    short-circuit (exercised via monkey-patched fake entry)
  - lookup() emits one-time UserWarning for empty-I/O entries
  - audit_empty_io() segmentation report, with variable_io_ok mirroring
    the _variable_io_rules registry
  - lookup()'s warning predicate fires only when BOTH sides are empty
    (MF-03 / D-01), so legitimate zero-outlet sinks and zero-inlet
    sources stay silent, asserted set-equal to audit_empty_io()'s
    both-empty buckets over the whole DB
  - audit_half_empty_io() reports the one-side-empty set as sinks /
    sources (NH-02 / D-02), checked against a brute-force oracle
"""

from __future__ import annotations

import re
import warnings

import pytest

from src.maxpat.db_lookup import ObjectDatabase


# ── has_complete_io ─────────────────────────────────────────────

def test_has_complete_io_true_for_cycle_tilde():
    db = ObjectDatabase()
    assert db.has_complete_io("cycle~") is True


def test_has_complete_io_false_for_empty_entry():
    # "dsp" is a stable doc-artifact entry in max/objects.json with empty
    # inlets AND outlets and no variable_io_rules entry. If this test
    # starts failing, the DB changed -- inspect audit_empty_io()["critical"]
    # to pick a new stable empty-I/O target ("project" is a fallback).
    db = ObjectDatabase()
    assert db.has_complete_io("dsp") is False


def test_has_complete_io_true_for_variable_io():
    # trigger has a variable_io_rules entry. Today its default I/O arrays
    # happen to be populated; the variable_io short-circuit still returns
    # True regardless.
    db = ObjectDatabase()
    assert db.has_complete_io("trigger") is True


def test_has_complete_io_resolves_alias():
    db = ObjectDatabase()
    assert db.has_complete_io("t") is True  # t -> trigger


def test_has_complete_io_false_for_unknown():
    db = ObjectDatabase()
    assert db.has_complete_io("__does_not_exist__") is False


def test_has_complete_io_respects_variable_io_exemption():
    """Cover the defensive variable_io short-circuit branch via monkey-patch.

    Real data does not currently exercise this branch (every variable_io
    rules target has populated default I/O), but we inject a fake entry
    that is BOTH empty-I/O AND has a rules entry to prove the
    short-circuit returns True instead of falling through to the
    inlets/outlets emptiness check.
    """
    db = ObjectDatabase()
    db._objects["__test_var_io__"] = {
        "name": "__test_var_io__",
        "inlets": [],
        "outlets": [],
    }
    db._variable_io_rules["__test_var_io__"] = {
        "inlet_count": "arg_count",
        "outlet_count": "arg_count",
    }
    assert db.has_complete_io("__test_var_io__") is True


# ── lookup() warning behavior ───────────────────────────────────

def test_lookup_warns_once_per_empty_io_name():
    db = ObjectDatabase()
    # First call: warning fires
    with pytest.warns(UserWarning, match="empty inlets/outlets"):
        result = db.lookup("dsp")
    assert result is not None  # object is still returned

    # Second call: warning is suppressed (dedup via _empty_io_warned)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        db.lookup("dsp")
    user_warnings = [w for w in caught if issubclass(w.category, UserWarning)]
    assert len(user_warnings) == 0, (
        f"Second lookup must not re-warn; got {len(user_warnings)} warnings"
    )


def test_lookup_does_not_warn_for_variable_io():
    db = ObjectDatabase()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        db.lookup("trigger")
    user_warnings = [w for w in caught if issubclass(w.category, UserWarning)]
    assert len(user_warnings) == 0


def test_lookup_does_not_warn_for_complete_io():
    db = ObjectDatabase()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        db.lookup("cycle~")
    user_warnings = [w for w in caught if issubclass(w.category, UserWarning)]
    assert len(user_warnings) == 0


def test_lookup_does_not_warn_when_object_not_found():
    db = ObjectDatabase()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = db.lookup("__does_not_exist__")
    assert result is None
    user_warnings = [w for w in caught if issubclass(w.category, UserWarning)]
    assert len(user_warnings) == 0


def test_lookup_does_not_warn_when_package_filtered():
    """Empty-I/O package objects must not warn when allowed_packages excludes them.

    Proves _maybe_warn_empty_io runs only on the SUCCESS path of lookup()
    (after the package filter). "opensoundcontrol" is a known empty-I/O
    package object from CNMAT externals (it's a documentation pseudo-class
    that survived quick-260427-l2t cleanup). Passing allowed_packages=[]
    rejects it before the warn helper fires.

    Previously used "ease" as the canary; quick-260427-l2t auto-extracted
    I/O for it from the ease-max helpfile, so it's no longer empty-I/O.
    """
    db = ObjectDatabase()
    # Sanity: "opensoundcontrol" IS an empty-I/O package object today. If
    # this precondition fails, pick another empty-I/O package object by
    # scanning: [n for n,o in db._objects.items() if not o.get("inlets")
    #           and not o.get("outlets") and "package" in o]
    osc = db._objects.get("opensoundcontrol")
    assert osc is not None, "precondition: 'opensoundcontrol' must exist in DB"
    assert "package" in osc, "precondition: 'opensoundcontrol' must be a package object"
    assert not osc.get("inlets") and not osc.get("outlets"), (
        "precondition: 'opensoundcontrol' must be empty-I/O"
    )

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = db.lookup("opensoundcontrol", allowed_packages=[])
    assert result is None, "'opensoundcontrol' must be filtered out with allowed_packages=[]"
    user_warnings = [w for w in caught if issubclass(w.category, UserWarning)]
    assert len(user_warnings) == 0, (
        f"filtered-out empty-I/O objects must not warn; got {len(user_warnings)}"
    )


# ── lookup_strict() ─────────────────────────────────────────────

def test_lookup_strict_returns_object_for_normal_hit():
    db = ObjectDatabase()
    result = db.lookup_strict("cycle~")
    assert result is not None
    assert result["name"] == "cycle~"


def test_lookup_strict_returns_none_for_empty_io_entry():
    """'dsp' is the same stable empty-I/O canary used by has_complete_io
    tests above. lookup() still returns it (with a UserWarning); the
    strict variant must return None so callers fail fast."""
    db = ObjectDatabase()
    # Suppress the expected one-time UserWarning from the lookup()
    # delegation -- it's the documented behavior, not what this test guards.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        assert db.lookup("dsp") is not None  # baseline: lookup still hits
        assert db.lookup_strict("dsp") is None  # strict variant rejects


def test_lookup_strict_returns_object_for_variable_io_with_empty_defaults():
    """Defensive variable_io exemption: an entry with empty default I/O
    but a variable_io_rules registration is a legitimate dynamically-
    sized object (its real I/O is computed by compute_io_counts at
    connection time). Must NOT be rejected.

    Real DB has no such entry today (every variable_io_rules target ships
    with populated defaults), so we inject one -- same pattern as
    test_has_complete_io_respects_variable_io_exemption."""
    db = ObjectDatabase()
    db._objects["__test_var_io_strict__"] = {
        "name": "__test_var_io_strict__",
        "inlets": [],
        "outlets": [],
    }
    db._variable_io_rules["__test_var_io_strict__"] = {
        "inlet_count": "arg_count",
        "outlet_count": "arg_count",
    }
    result = db.lookup_strict("__test_var_io_strict__")
    assert result is not None
    assert result["name"] == "__test_var_io_strict__"


def test_lookup_strict_resolves_alias():
    """t -> trigger; lookup_strict must use the same alias map as lookup()."""
    db = ObjectDatabase()
    result = db.lookup_strict("t")
    assert result is not None
    assert result["name"] == "trigger"


# ── audit_empty_io() ────────────────────────────────────────────

def test_audit_empty_io_segments():
    db = ObjectDatabase()
    audit = db.audit_empty_io()

    # Shape (by_source is an additive dict view -- checked separately in
    # test_audit_empty_io_covers_all_domain_files)
    assert set(audit.keys()) == {
        "critical", "covered_by_override", "variable_io_ok", "by_source"
    }
    for key in ("critical", "covered_by_override", "variable_io_ok"):
        bucket = audit[key]
        assert isinstance(bucket, list), f"{key} must be a list"
        assert all(isinstance(x, str) for x in bucket), f"{key} must contain only str"
        assert bucket == sorted(bucket), f"{key} must be sorted"

    # variable_io_ok mirrors the rules registry (new semantics: not gated
    # on empty I/O; lists ALL canonical names with a rules entry)
    assert len(audit["variable_io_ok"]) == len(db._variable_io_rules), (
        "variable_io_ok must contain every key in _variable_io_rules"
    )
    assert set(audit["variable_io_ok"]) == set(db._variable_io_rules.keys())
    assert "trigger" in audit["variable_io_ok"]

    # Disjoint in practice on current DB (permitted to overlap if a
    # future rules entry has empty defaults -- this assertion is a
    # present-day regression guard, not a spec invariant).
    crit = set(audit["critical"])
    cov = set(audit["covered_by_override"])
    var = set(audit["variable_io_ok"])
    assert crit.isdisjoint(cov), "critical and covered_by_override overlap"
    assert crit.isdisjoint(var), "critical and variable_io_ok overlap today"
    assert cov.isdisjoint(var), "covered_by_override and variable_io_ok overlap today"

    # cycle~ has complete I/O and no rules entry -- must not appear
    all_names = crit | cov | var
    assert "cycle~" not in all_names

    # critical bucket is non-empty. Lower bound was 50 pre-cleanup; after
    # quick-260427-l2t the bucket dropped to ~7 (documentation pseudo-classes
    # left as known leftovers). The >=1 floor proves the bucket exists
    # without locking in a specific count -- the upper bound is enforced by
    # test_audit_empty_io_critical_bound below.
    assert len(crit) >= 1, (
        f"expected critical bucket to have real entries, got {len(crit)}"
    )

    # covered_by_override may be empty today (0 empty-I/O entries have
    # overrides); just confirm the key is present and the list is a list
    assert isinstance(audit["covered_by_override"], list)


def test_audit_empty_io_critical_bound():
    """Regression guard for FINDINGS § P1-6 cleanup (quick-260427-l2t).

    After Pass A (4 doc-page non-objects deleted from per-domain JSONs) and
    Pass B (~120 package objects populated via tools/extract_pkg_io.py), the
    critical bucket dropped from 130 to ~7. This test locks in the cleanup
    and surfaces regressions:

      - If a new package gets extracted with empty I/O and added to the DB,
        this count creeps up and the test fails -- the fix is to extend
        tools/extract_pkg_io.py (add to MANUAL_FALLBACK or rely on a
        helpfile match) and re-run it.

      - If overrides.json gets corrupted or the deep-merge logic regresses,
        this fails.

    Threshold = 20 (current ~7 expected, headroom for natural drift like a
    new package landing with a few empty-I/O entries before someone runs
    the curator).
    """
    db = ObjectDatabase()
    audit = db.audit_empty_io()
    crit = audit["critical"]
    assert len(crit) < 20, (
        f"empty-I/O critical bucket regressed: {len(crit)} entries (expected <20).\n"
        f"Names: {crit}\n"
        f"Fix: extend tools/extract_pkg_io.py (helpfile match or MANUAL_FALLBACK) "
        f"and re-run it, or add direct overrides for the new entries."
    )


def test_audit_empty_io_covers_all_domain_files():
    """audit_empty_io()['by_source'] surfaces EVERY raw empty-I/O entry.

    The merged self._objects dict holds one entry per canonical name, so
    package entries that share a name with a populated core-domain object
    are shadowed and never appear in critical/covered/variable_io_ok. The
    additive by_source key mirrors the raw per-file state and must expose
    them.

    This test is an INDEPENDENT oracle: it walks the domain JSON files
    itself and never calls any production helper to compute the expected
    total or per-source counts.
    """
    import json as _json
    from pathlib import Path as _Path

    import src.maxpat.db_lookup as _dbmod

    max_objects_root = (
        _Path(_dbmod.__file__).resolve().parents[2] / ".claude" / "max-objects"
    )

    # Exact empty predicate -- must match production capture bit-for-bit.
    def _is_empty(obj):
        return not obj.get("inlets") and not obj.get("outlets")

    # Independent brute-force per-source counts.
    expected_by_source_count: dict[str, int] = {}
    for domain in ("max", "msp", "jitter", "mc", "gen", "m4l", "rnbo"):
        json_path = max_objects_root / domain / "objects.json"
        if not json_path.exists():
            continue
        data = _json.loads(json_path.read_text())
        count = sum(1 for obj in data.values() if _is_empty(obj))
        if count:
            expected_by_source_count[domain] = count

    pkg_root = max_objects_root / "packages"
    if pkg_root.is_dir():
        for pkg_dir in sorted(pkg_root.iterdir()):
            if not pkg_dir.is_dir():
                continue
            json_path = pkg_dir / "objects.json"
            if not json_path.exists():
                continue
            data = _json.loads(json_path.read_text())
            count = sum(1 for obj in data.values() if _is_empty(obj))
            if count:
                expected_by_source_count[f"packages/{pkg_dir.name}"] = count

    brute_force_total = sum(expected_by_source_count.values())

    db = ObjectDatabase()
    audit = db.audit_empty_io()

    # Additive key exists and is a dict of sorted str lists.
    assert isinstance(audit["by_source"], dict)
    for src, names in audit["by_source"].items():
        assert isinstance(names, list), f"by_source[{src}] must be a list"
        assert all(isinstance(x, str) for x in names)
        assert names == sorted(names), f"by_source[{src}] must be sorted"

    # Grand total equals the independent brute-force count.
    audit_total = sum(len(v) for v in audit["by_source"].values())
    assert audit_total == brute_force_total, (
        f"by_source total {audit_total} != brute-force {brute_force_total}"
    )

    # Per-source grouping matches the brute-force per-file counts.
    audit_by_source_count = {
        src: len(names) for src, names in audit["by_source"].items()
    }
    assert audit_by_source_count == expected_by_source_count

    # Shadow-fix regression: previously-invisible package entries surface
    # under their source, but do NOT appear in critical (they are shadowed
    # by populated same-named core entries).
    assert "bach.hypercomment" in audit["by_source"]["packages/Bach"]
    assert "osc-route" in audit["by_source"]["packages/CNMAT"]
    assert "jit.gl.textureset" in audit["by_source"]["packages/Jitter Tools"]

    critical = set(audit["critical"])
    assert "bach.hypercomment" not in critical
    assert "osc-route" not in critical
    assert "jit.gl.textureset" not in critical


# ── aligned empty-I/O warning predicate (MF-03, D-01) ───────────

# The empty-I/O warning message fragment. _maybe_warn_install_state emits
# the same UserWarning category, so every sweep below filters on this text
# rather than on the category alone.
_EMPTY_IO_FRAGMENT = "empty inlets/outlets"
_EMPTY_IO_NAME_RE = re.compile(r"Object '(?P<name>[^']+)' has empty inlets/outlets")


def _sweep_empty_io_warned_names(db) -> set[str]:
    """Look up every canonical in the DB and return the names carried by
    empty-I/O warnings. Independent of any production audit helper."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        for name in list(db._objects.keys()):
            db.lookup(name)
    warned: set[str] = set()
    for w in caught:
        msg = str(w.message)
        if _EMPTY_IO_FRAGMENT not in msg:
            continue
        match = _EMPTY_IO_NAME_RE.search(msg)
        if match:
            warned.add(match.group("name"))
    return warned


def test_lookup_does_not_warn_for_zero_outlet_sink():
    """A zero-outlet sink is legitimate DB data, not a defect (D-01).

    'midiout' is the canary: populated inlets, genuinely no outlets, no
    variable_io_rules entry. (Was 'dac~' until 2026-09-27, when dac~ gained
    an arg_count_or_default rule for its per-channel inlets.)
    Before MF-03 this fired the "patch generation may fail silently"
    warning on every lookup. Fallback if the DB changes, rescan with:
      [n for n, o in db._objects.items()
       if o.get("inlets") and not o.get("outlets")
       and n not in db._variable_io_rules]
    """
    db = ObjectDatabase()
    sink = db._objects.get("midiout")
    assert sink is not None, "precondition: 'midiout' must exist in DB"
    assert sink.get("inlets"), "precondition: 'midiout' must have populated inlets"
    assert not sink.get("outlets"), "precondition: 'midiout' must have empty outlets"
    assert "midiout" not in db._variable_io_rules, (
        "precondition: 'midiout' must have no variable_io_rules entry"
    )

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = db.lookup("midiout")
    assert result is not None
    user_warnings = [w for w in caught if issubclass(w.category, UserWarning)]
    assert len(user_warnings) == 0, (
        "zero-outlet sinks must not warn; got "
        f"{[str(w.message) for w in user_warnings]}"
    )


def test_lookup_does_not_warn_for_zero_inlet_source():
    """A zero-inlet source is legitimate DB data, not a defect (D-01).

    'begin~' is the canary: 0 inlets, populated outlets, no
    variable_io_rules entry (0 inlets / 1 outlet measured 2026-09-21).
    Fallback if the DB changes -- same style as
    test_lookup_does_not_warn_when_package_filtered -- rescan with:
      [n for n, o in db._objects.items()
       if o.get("outlets") and not o.get("inlets")
       and n not in db._variable_io_rules]
    """
    db = ObjectDatabase()
    source = db._objects.get("begin~")
    assert source is not None, "precondition: 'begin~' must exist in DB"
    assert source.get("outlets"), "precondition: 'begin~' must have populated outlets"
    assert not source.get("inlets"), "precondition: 'begin~' must have empty inlets"
    assert "begin~" not in db._variable_io_rules, (
        "precondition: 'begin~' must have no variable_io_rules entry"
    )

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = db.lookup("begin~")
    assert result is not None
    user_warnings = [w for w in caught if issubclass(w.category, UserWarning)]
    assert len(user_warnings) == 0, (
        "zero-inlet sources must not warn; got "
        f"{[str(w.message) for w in user_warnings]}"
    )


def test_empty_io_warning_message_names_the_object():
    """Both-sides-empty entries still warn, and the message names the object.

    Dedup and the once-per-name contract are covered by
    test_lookup_warns_once_per_empty_io_name; this pins the message
    contract so the D-01 predicate change cannot silently alter it.
    """
    db = ObjectDatabase()
    entry = db._objects.get("dsp")
    assert entry is not None, "precondition: 'dsp' must exist in DB"
    assert not entry.get("inlets") and not entry.get("outlets"), (
        "precondition: 'dsp' must be both-sides-empty"
    )

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        db.lookup("dsp")
    empty_io = [
        w for w in caught
        if issubclass(w.category, UserWarning)
        and _EMPTY_IO_FRAGMENT in str(w.message)
    ]
    assert len(empty_io) == 1, f"expected exactly 1 warning, got {len(empty_io)}"
    assert "'dsp'" in str(empty_io[0].message)


def test_warning_predicate_matches_audit_empty_io_exactly():
    """THE MF-03 invariant: the warning and the audit apply the same rule.

    Sweeps lookup() over the whole DB and asserts the set of warned
    canonical names EQUALS audit_empty_io()'s both-sides-empty buckets.
    Equality (not a count) is what stops the two predicates drifting
    apart again -- before this task the warning fired on 218 names while
    the audit reported 9.
    """
    db = ObjectDatabase()
    warned = _sweep_empty_io_warned_names(db)

    audit = db.audit_empty_io()
    audit_both_empty = set(audit["critical"]) | set(audit["covered_by_override"])

    assert sorted(warned) == sorted(audit_both_empty), (
        "empty-I/O warning predicate and audit_empty_io() disagree.\n"
        f"warned only: {sorted(warned - audit_both_empty)}\n"
        f"audit only:  {sorted(audit_both_empty - warned)}"
    )


# ── audit_half_empty_io() (NH-02, D-02) ─────────────────────────

def test_audit_half_empty_io_shape():
    """Shape contract for the surface that carries the one-side-empty set.

    The information the warning no longer reports is not deleted -- it
    moves here, split into sinks (inlets populated, no outlets) and
    sources (outlets populated, no inlets).
    """
    db = ObjectDatabase()
    half = db.audit_half_empty_io()

    assert set(half.keys()) == {"sinks", "sources"}
    for key in ("sinks", "sources"):
        bucket = half[key]
        assert isinstance(bucket, list), f"{key} must be a list"
        assert all(isinstance(x, str) for x in bucket), f"{key} must contain only str"
        assert bucket == sorted(bucket), f"{key} must be sorted"

    sinks = set(half["sinks"])
    sources = set(half["sources"])
    assert sinks.isdisjoint(sources), "sinks and sources must be disjoint"

    assert "midiout" in sinks, "'midiout' (inlets, 0 outlets) must be a sink"
    assert "begin~" in sources, "'begin~' (0 inlets, 1 outlet) must be a source"

    # The half-empty set is orthogonal to every audit_empty_io() bucket.
    audit = db.audit_empty_io()
    for key in ("critical", "covered_by_override", "variable_io_ok"):
        bucket = set(audit[key])
        assert sinks.isdisjoint(bucket), f"sinks overlaps audit_empty_io()['{key}']"
        assert sources.isdisjoint(bucket), f"sources overlaps audit_empty_io()['{key}']"


def test_audit_half_empty_io_matches_brute_force_oracle():
    """Independent oracle for audit_half_empty_io() (NH-02).

    Recomputes both buckets directly from db._objects without calling the
    production helper under test -- same style as
    test_audit_empty_io_covers_all_domain_files. Both buckets must be
    non-empty (109 sinks / 100 sources measured 2026-09-21; the floor is
    asserted without locking in those numbers).
    """
    db = ObjectDatabase()

    expected_sinks: list[str] = []
    expected_sources: list[str] = []
    for canonical, obj in db._objects.items():
        if canonical in db._variable_io_rules:
            continue
        has_in = bool(obj.get("inlets"))
        has_out = bool(obj.get("outlets"))
        if has_in and not has_out:
            expected_sinks.append(canonical)
        elif has_out and not has_in:
            expected_sources.append(canonical)

    half = db.audit_half_empty_io()
    assert half["sinks"] == sorted(expected_sinks)
    assert half["sources"] == sorted(expected_sources)

    assert len(half["sinks"]) >= 1, "expected real zero-outlet sinks in the DB"
    assert len(half["sources"]) >= 1, "expected real zero-inlet sources in the DB"


# ── compute_io_counts regression (REVIEW 260420-j15 FN-01) ──────

def test_compute_io_counts_honors_overrides_rules_for_lifted_objects():
    """Regression: cycle / combine / router were silently mis-counted.

    See .planning/quick/260420-j15-review-the-objects-database-entries-and-/
    260420-j15-REVIEW.md FN-01 + DQ-02. These three core MAX objects have
    variable_io=true plus an inline io_rule in their per-domain JSON, but
    db_lookup only consults overrides.json:variable_io_rules. Before
    quick-260420-j15 lifted the rules into the loaded registry,
    compute_io_counts fell through to raw default-array lengths (e.g.
    router(['4','6']) returned (4, 5), not (4, 6)). This test locks in the
    fix: if a future edit removes any of the three rules, the test fails
    loudly.
    """
    db = ObjectDatabase()

    # cycle: first arg = outlet count; no-arg = 2 outlets
    assert db.compute_io_counts("cycle", ["5"]) == (1, 5)
    assert db.compute_io_counts("cycle", []) == (1, 2)

    # combine: arg count = inlet count; 2 outlets (combined symbol + the
    # trigger-done outlet). Q10 / C1 (261013-cyg): MAX evidence overturns
    # FN-03 of REVIEW 260420-j15 -- MAX saves `combine sound 74 @triggers 1`
    # as (2,2) (C74/help/max/combine.maxhelp) and bare `combine` as (1,2)
    # (dada/help/dada.machines.maxhelp), so bare uses the defaults and
    # there are always 2 outlets.
    assert db.compute_io_counts("combine", ["a", "b", "c"]) == (3, 2)
    assert db.compute_io_counts("combine", []) == (1, 2)

    # router: first_arg inlets, second_arg outlets; no-arg = 2x2
    # (first_arg/second_arg keep their default-fallback semantics)
    assert db.compute_io_counts("router", ["4", "6"]) == (4, 6)
    assert db.compute_io_counts("router", []) == (2, 2)


# ── compute_io_counts TC-01 (REVIEW 260420-j15) ─────────────────

def test_compute_io_counts_unknown_object_returns_zero_zero():
    db = ObjectDatabase()
    assert db.compute_io_counts("__does_not_exist__", []) == (0, 0)
    assert db.compute_io_counts("__does_not_exist__", ["a", "b"]) == (0, 0)


def test_compute_io_counts_non_variable_io_returns_db_arrays():
    db = ObjectDatabase()
    # cycle~: 2 inlets (signal freq + phase), 1 outlet (signal). Not variable_io.
    assert db.compute_io_counts("cycle~", []) == (2, 1)
    # Args are ignored for non-variable_io objects.
    assert db.compute_io_counts("cycle~", ["440"]) == (2, 1)


def test_compute_io_counts_trigger_with_full_args():
    db = ObjectDatabase()
    # trigger b i f -> 1 inlet, 3 outlets (one per type letter)
    assert db.compute_io_counts("trigger", ["b", "i", "f"]) == (1, 3)


def test_compute_io_counts_trigger_no_args_matches_refpage():
    """Q10 / C1 (261013-cyg): bare trigger = (1,2).

    MAX evidence overturns FN-03 of REVIEW 260420-j15 (which expected 0
    outlets): trigger.maxref.xml says "If there are no arguments, there are
    two outlets", so the rule is now arg_count_or_default with
    default_outlets 2. No MAX-saved bare trigger box exists (refpage-derived).
    """
    db = ObjectDatabase()
    assert db.compute_io_counts("trigger", []) == (1, 2)


def test_compute_io_counts_route_no_args_matches_refpage():
    """Q10 / C1 (261013-cyg): bare route = (2,2).

    MAX evidence overturns FN-03 of REVIEW 260420-j15 (which expected (1,1)).
    route is now an I/O resolver (src/maxpat/io_resolvers.py): N args give
    N+1 inlets and N+1 outlets (MAX-saved `route time transport` = (3,3),
    C74/help/jitter/jit.avc.maxhelp). No MAX-saved bare `route` box exists;
    route.maxref.xml says "If there is no argument, there is one other
    outlet, which is assigned the number 0", so bare = (2,2).
    """
    db = ObjectDatabase()
    assert db.compute_io_counts("route", []) == (2, 2)


# ── get_outlet_types TC-02 (REVIEW 260420-j15) ──────────────────

def test_get_outlet_types_all_signal():
    db = ObjectDatabase()
    # cycle~ has a single signal outlet
    assert db.get_outlet_types("cycle~", []) == ["signal"]


def test_get_outlet_types_mixed_signal_and_control():
    db = ObjectDatabase()
    # sfplay~: signal channels + control bang on completion. The exact
    # channel count varies by argument, but the multi-outlet result must
    # contain BOTH "signal" and "" entries to prove mixed-type rendering.
    types = db.get_outlet_types("sfplay~", [])
    assert "signal" in types, types
    assert "" in types, types


def test_get_outlet_types_variable_expansion_inherits_control():
    """trigger b i f: 3 control outlets (no signal). Tests the expansion
    path in get_outlet_types where num_outlets exceeds len(db_outlets) and
    types are inherited from the last DB outlet.
    """
    db = ObjectDatabase()
    types = db.get_outlet_types("trigger", ["b", "i", "f"])
    assert types == ["", "", ""], types


def test_get_outlet_types_unknown_returns_empty():
    db = ObjectDatabase()
    assert db.get_outlet_types("__does_not_exist__", []) == []


# ── variable_io registry refactor (REVIEW 260421-b3a FN-01 / DQ-02) ────

def test_compute_io_counts_routepass_resolver():
    """Q10 / C1 (261013-cyg): routepass N args = (N+1, N+1).

    Supersedes the REVIEW 260421-b3a formula-path test, which expected
    (1,3)/(1,4): MAX saves `routepass 0 1` as (3,3)
    (C74/help/jitter/jit.displays.maxhelp) -- every match also gets an
    inlet that sets it. routepass moved from a variable_io_rules formula to
    an I/O resolver, and a rule must not coexist with it.
    """
    from src.maxpat.io_resolvers import IO_RESOLVERS

    db = ObjectDatabase()
    assert db.compute_io_counts("routepass", ["a", "b"]) == (3, 3)
    assert db.compute_io_counts("routepass", ["a", "b", "c"]) == (4, 4)
    assert "routepass" in IO_RESOLVERS
    assert "routepass" not in db._variable_io_rules


def test_compute_io_counts_routepass_normalized_default_outlets():
    """Q10 / C1 (261013-cyg): routepass counts with and without args.

    The quick-260421-bti rule shape this anchored no longer exists
    (routepass is an I/O resolver). `routepass 0 1` = (3,3) is MAX-saved
    (C74/help/jitter/jit.displays.maxhelp); bare routepass = (2,2) follows
    routepass.maxref.xml ("If there is no argument, there is one other
    outlet").
    """
    db = ObjectDatabase()
    assert db.compute_io_counts("routepass", ["a", "b"]) == (3, 3)
    assert db.compute_io_counts("routepass", []) == (2, 2)


def test_load_time_validation_rejects_unknown_formula(tmp_path):
    """Negative test: ObjectDatabase construction raises ValueError when
    overrides.json:variable_io_rules contains an unsupported formula.

    This validation is the safety net for the refactor — it makes the
    silent-fallback class of bug (stale formula name like
    'arg_count_plus_1') impossible at load time.
    """
    import json

    import pytest

    overrides = {
        "variable_io_rules": {
            "bogus_obj": {
                "inlet_count": "fixed:1",
                "outlet_count": "bogus_formula",
                "default_inlets": 1,
                "default_outlets": 1,
            }
        },
        "objects": {},
    }
    (tmp_path / "overrides.json").write_text(json.dumps(overrides))

    with pytest.raises(ValueError) as excinfo:
        ObjectDatabase(db_root=tmp_path)
    msg = str(excinfo.value)
    assert "bogus_formula" in msg, msg
    assert "bogus_obj" in msg, msg
    assert "outlet_count" in msg, msg


def test_load_time_validation_accepts_live_overrides():
    """Sanity: the real overrides.json in .claude/max-objects/ must pass
    the validator. If this fails, someone added a rule with a formula
    that _apply_io_formula doesn't know about — fix the rule, don't
    loosen the validator.
    """
    ObjectDatabase()  # must not raise


# ── compute_io_counts mc.* (quick-260421-bx3 DQ-07) ────────────
#
# Lock in the 10 argument-driven mc.* objects promoted to variable_io=true
# with matching overrides.json:variable_io_rules entries. These mirror the
# TC-01 / TC-02 pattern above and guard against a regression where a mc.*
# rule gets a default/formula drift (the REVIEW-260420-j15 DQ-07 class of
# bug). Critical disambiguation: most mc.* int args set channel count
# INSIDE a single MC outlet, not outlet count at the connection level —
# those stay variable_io=false and are NOT tested here.


def test_compute_io_counts_mc_pack():
    """mc.pack~ N → N inlets, 1 outlet. first_arg (single int), not arg_count."""
    db = ObjectDatabase()
    assert db.compute_io_counts("mc.pack~", ["4"]) == (4, 1)
    assert db.compute_io_counts("mc.pack~", []) == (2, 1)  # default


def test_compute_io_counts_mc_unpack():
    """mc.unpack~ N → 1 inlet, N outlets."""
    db = ObjectDatabase()
    assert db.compute_io_counts("mc.unpack~", ["6"]) == (1, 6)
    assert db.compute_io_counts("mc.unpack~", []) == (1, 2)  # default


def test_compute_io_counts_mc_separate():
    """mc.separate~ a b c → 1 inlet, arg_count=3 outlets. Only mc.* using arg_count."""
    db = ObjectDatabase()
    assert db.compute_io_counts("mc.separate~", ["2", "2", "4"]) == (1, 3)
    # arg_count with empty args falls through to default_outlets=2 via
    # the same semantic as pack/combine (see test_compute_io_counts_pack_
    # no_args in TC-01 for precedent).


def test_compute_io_counts_mc_combine():
    """mc.combine~ N → N inlets, 1 outlet (first_arg, not arg_count like core combine)."""
    db = ObjectDatabase()
    assert db.compute_io_counts("mc.combine~", ["3"]) == (3, 1)


def test_compute_io_counts_mc_gate():
    """mc.gate~ mirrors gate: fixed 2 inlets (signal+route), N outlets."""
    db = ObjectDatabase()
    assert db.compute_io_counts("mc.gate~", ["4"]) == (2, 4)


def test_compute_io_counts_mc_selector():
    """mc.selector~ mirrors selector~: first_arg+1 inlets (N inputs + selector)."""
    db = ObjectDatabase()
    assert db.compute_io_counts("mc.selector~", ["3"]) == (4, 1)  # 3+1


def test_compute_io_counts_mc_matrix():
    """mc.matrix~ N M → N inlets, M signal outlets + 2 control outlets.

    MAX-saved help boxes: `mc.matrix~ 3 2` and `mc.matrix~ 4 2` both save
    4 outlets (multichannelsignal x2, "", ""). Q2 / OQ2-A: the count follows
    MAX, not the 9.2 refpage's 3-outlet template.
    """
    db = ObjectDatabase()
    assert db.compute_io_counts("mc.matrix~", ["3", "2"]) == (3, 4)
    assert db.compute_io_counts("mc.matrix~", ["4", "2"]) == (4, 4)
    assert db.compute_io_counts("mc.matrix~", ["4", "6"]) == (4, 8)


def test_mc_pack_is_variable_io():
    """Post-fix anchor: mc.pack~ flag flipped and rule registered.

    This test fails loudly if a future DB refresh re-extracts mc.pack~
    with variable_io=false (losing the DQ-07 fix) or if the overrides.json
    rule is accidentally removed.
    """
    db = ObjectDatabase()
    obj = db.lookup("mc.pack~")
    assert obj["variable_io"] is True
    assert "mc.pack~" in db._variable_io_rules


# ---------------------------------------------------------------------------
# trailing_outlets: arg-aware outlet layout (sfplay~ N, 2026-10-11)
# ---------------------------------------------------------------------------


def test_sfplay_signal_roles_follow_channel_count():
    """`sfplay~ N` = N audio outlets + the done-bang. With args, outlet roles
    resolve by layout; without args, plain indexing is unchanged."""
    db = ObjectDatabase()
    assert [db.get_signal_role("sfplay~", i, ["2"]) for i in range(3)] == [
        "audio", "audio", "trigger"]
    assert [db.get_signal_role("sfplay~", i, ["4"]) for i in range(6)] == [
        "audio", "audio", "audio", "audio", "trigger", None]
    assert [db.get_signal_role("sfplay~", i, []) for i in range(2)] == [
        "audio", "trigger"]
    # no args: the legacy index lookup
    assert db.get_signal_role("sfplay~", 1) == "trigger"


def test_sfplay_outlet_types_follow_channel_count():
    db = ObjectDatabase()
    assert db.get_outlet_types("sfplay~", ["2"]) == ["signal", "signal", ""]
    assert db.get_outlet_types("sfplay~", ["1"]) == ["signal", ""]
    assert db.get_outlet_types("sfplay~", []) == ["signal", ""]


def test_trailing_outlets_must_be_positive_int():
    db = ObjectDatabase()
    for bad in (0, -1, "1", 1.0, True):
        db._variable_io_rules = {"sfplay~": {
            "inlet_count": "fixed:2", "outlet_count": "first_arg+1",
            "trailing_outlets": bad}}
        with pytest.raises(ValueError, match="trailing_outlets"):
            db._validate_variable_io_rules()


# ---------------------------------------------------------------------------
# trailing_outlets: matrix~ N M, mc.matrix~ N M, play~ buf N (Q2 / A1)
# Counts are the MAX-saved help boxes (observed_facts in 261012-c5i).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("args,expected", [
    (["4", "1", "1."], (4, 2)),
    (["4", "2"], (4, 3)),
    (["4", "4", "1."], (4, 5)),
    (["2", "2", "1.", "@ramp", "74"], (2, 3)),
    (["2", "4"], (2, 5)),
])
def test_matrix_counts_include_dump_outlet(args, expected):
    """`matrix~ N M` = N inlets, M audio outlets + the list dump outlet."""
    db = ObjectDatabase()
    assert db.compute_io_counts("matrix~", args) == expected


@pytest.mark.parametrize("args,expected", [
    (["foo", "2"], (1, 3)),
    (["playme"], (1, 2)),
    ([], (1, 2)),
])
def test_play_counts_follow_channel_arg(args, expected):
    """`play~ buf N` = N audio outlets + the done-bang (refpage args:
    buffer-name, number-of-output-channels, default 1)."""
    db = ObjectDatabase()
    assert db.compute_io_counts("play~", args) == expected


def test_mc_matrix_counts_follow_help_boxes():
    db = ObjectDatabase()
    assert db.compute_io_counts("mc.matrix~", ["3", "2"]) == (3, 4)
    assert db.compute_io_counts("mc.matrix~", ["4", "2"]) == (4, 4)
    assert db.compute_io_counts("mc.matrix~", ["4", "6"]) == (4, 8)


def test_trailing_signal_roles_matrix_play_mc_matrix():
    db = ObjectDatabase()
    assert [db.get_signal_role("matrix~", i, ["2", "4"]) for i in range(5)] == [
        "audio", "audio", "audio", "audio", "list"]
    assert [db.get_signal_role("play~", i, ["foo", "2"]) for i in range(3)] == [
        "audio", "audio", "trigger"]
    assert [db.get_signal_role("play~", i, ["playme"]) for i in range(2)] == [
        "audio", "trigger"]
    assert db.get_signal_role("play~", 1) == "trigger"
    assert [db.get_signal_role("mc.matrix~", i, ["3", "2"]) for i in range(4)] == [
        "audio", "audio", "list", None]


def test_trailing_outlet_types_matrix_play_mc_matrix():
    db = ObjectDatabase()
    assert db.get_outlet_types("matrix~", ["4", "2", "1."]) == [
        "signal", "signal", ""]
    assert db.get_outlet_types("play~", ["foo", "2"]) == [
        "signal", "signal", ""]
    # MAX saves `mc.matrix~ 3 2` as (multichannelsignal x2, "", "")
    # (bundle help; CR-01 MC outlet flavour)
    assert db.get_outlet_types("mc.matrix~", ["3", "2"]) == [
        "multichannelsignal", "multichannelsignal", "", ""]


def test_patcher_builds_matrix_and_play_with_trailing_outlet():
    from src.maxpat.patcher import Patcher

    p = Patcher()
    assert p.add_box("matrix~", args=["2", "4"]).numoutlets == 5
    assert p.add_box("play~", args=["buf", "2"]).numoutlets == 3


def test_second_arg_plus_formulas():
    db = ObjectDatabase()
    assert db._apply_io_formula("second_arg+1", ["x", "3"], 9) == 4
    assert db._apply_io_formula("second_arg+1", ["x"], 9) == 9
    assert db._apply_io_formula("second_arg+2", ["x", "3"], 9) == 5
    assert db._apply_io_formula("second_arg+2", [], 9) == 9
    with pytest.warns(UserWarning, match="non-integer"):
        assert db._apply_io_formula("second_arg+1", ["x", "q"], 9) == 9
    db._variable_io_rules = {"probe~": {
        "inlet_count": "", "outlet_count": "second_arg+1",
        "trailing_outlets": 1}}
    db._validate_variable_io_rules()  # must not raise
