"""Multi-layer validation pipeline for MAX patches.

Layers run sequentially per patcher scope, stopping early on structural errors:
  Layer 1 (json):        JSON structure checks (patcher, boxes, lines, entry
                         shapes, duplicate box ids)
  Layer 2 (objects):     Object existence against ObjectDatabase, plus the
                         implied RNBO/Gen restriction of rnbo/gen-only names
                         against the patch scope (max / gen / rnbo; Q12 / C3)
  Layer 3 (connections): Connection index bounds and signal/control type checks
  Layer 4 (domain):      Domain-specific rules (gain staging, unterminated chains, feedback)
  Layer 4b / 5:          Explicit domain restrictions; embedded GenExpr codeboxes

Recursive (Q19 / review A7): the top level runs first, unchanged; then every
embedded patcher (``p``, embedded bpatcher / poly~, gen~, mc.gen~
``data.patcher``, jit.gen, rnbo~ ...) found by ``walk.iter_patchers`` runs
the same layers with its own scope, in walker pre-order. A nested finding
carries ``ValidationResult.path`` (the box-id chain, ``obj-1/obj-2``) and a
``[p synth > gen~] `` message prefix; a top-level finding has ``path == ""``
and an unprefixed message. A gen scope skips Layer 4 (MSP / Max-UI domain
rules). External abstractions are never loaded.

Validation is pure: ``validate_patch`` never mutates its input, and dict and
Patcher input produce identical results. A cord Layer 3 considers invalid is
reported as an ``error`` whose ``proposed_removal`` is the 4-tuple
``(src_id, src_outlet, dst_id, dst_inlet)``; nothing is removed unless the
caller explicitly calls ``apply_fixes(patch, results)`` (review A2).

Proposed removals block new patches (``has_blocking_errors(results)`` with the
default ``is_new=True``); on the edit path (``is_new=False``) they are
reported but not blocking. Container boxes accept any cord, signal_role
mismatches are warnings, and known companion pairs from relationships.json
are never flagged (review A1).
"""

from __future__ import annotations

import re as _re
from collections import defaultdict
from typing import TYPE_CHECKING

from src.maxpat import dsp_roles, walk
from src.maxpat.db_lookup import DOMAIN_SCOPES, ObjectDatabase, detect_patcher_scope
from src.maxpat.maxclass_map import is_ui_object, UI_MAXCLASSES

if TYPE_CHECKING:
    from src.maxpat.patcher import Patcher


# Maxclasses the maxclass-usage check (Layer 2b) exempts. MAX never saves
# maxclass "patcher" -- p/patcher is a newobj box carrying an embedded patcher
# (review C4) -- so that check does not exempt it, while
# walk.STRUCTURAL_MAXCLASSES keeps "patcher" for name extraction
# (walk.object_name returns None for it).
_MAXCLASS_USAGE_SKIP = frozenset({"inlet", "outlet", "bpatcher"})

# Oscillator objects that need gain staging before dac~/ezdac~
_OSCILLATOR_NAMES = frozenset({
    "cycle~", "saw~", "rect~", "tri~", "noise~", "pink~",
})

# Gain stages, output terminals and chain terminals come from
# src.maxpat.dsp_roles (DB-driven, shared with the DSP critic; Q26 / E6).

# Objects that provide delay in a feedback loop
_DELAY_NAMES = frozenset({"tapin~", "tapout~", "gen~"})


# Role-aware connection tier table (D-04, D-19, VALID-01). Maps
# (src_outlet_role, dst_inlet_kind) -> (level, suggestion).
# Q1 / review A1: role mismatches WARN and never remove or propose removal --
# signal_role data is curated but not authoritative enough to delete a cord
# (scala-synth-voice `in 1` -> `peek~` was stripped by the old ERROR rows).
# Absent keys mean "fall through to legacy signal:bool branch unchanged"
# (D-02). Audio-source keys are INTENTIONALLY ABSENT — the legacy branch
# retains exclusive control of audio source paths so existing
# test_signal_to_signal_passes / test_signal_to_control_only_inlet_detected
# regression anchors remain unchanged (RESEARCH.md R2, R10).
_ROLE_TIER_TABLE: dict[tuple[str, str], tuple[str, str]] = {
    # Mechanical fix exists
    ("status",  "signal"): ("warning", "use snapshot~"),
    ("trigger", "signal"): ("warning", "use sig~ or click~"),
    ("data",    "signal"): ("warning", "role mismatch; data outlet cannot drive signal inlet"),
    ("list",    "signal"): ("warning", "role mismatch; list outlet cannot drive signal inlet"),
    # Judgment-laden intent
    ("trigger", "float"):  ("warning", "trigger feeding float; user may intend bang counting"),
    ("list",    "float"):  ("warning", "list outlet feeding float; bach.* often does this — verify"),
}


# Container boxes (review A1): they forward whatever arrives to an inner
# patcher, so any cord into them is valid and their outlets carry no
# signal_role. Any box with an embedded patcher dict is also a container.
_CONTAINER_NAMES = frozenset({
    "p", "patcher", "bpatcher", "poly~", "mc.poly~", "pfft~", "rnbo~",
})

_PROPOSED_SUFFIX = "-- proposed removal (not applied; see apply_fixes)"


# UI maxclasses whose primary inlet displays a float number. The DB
# annotates these inlets as type="control" because they accept any control
# message, but for role-aware tier-table lookup they classify as "float"
# (so trigger/list -> flonum/number triggers the WARNING tier). Keep this
# list narrow: only widgets whose inlet 0 explicitly stores/displays a
# numeric value.
_FLOAT_DISPLAY_MAXCLASSES = frozenset({
    "flonum", "number", "live.numbox",
})


# ===========================================================================
# ValidationResult
# ===========================================================================

class ValidationResult:
    """A single validation finding.

    Attributes:
        layer: Which validation layer produced this ("json", "objects",
               "connections", "domain").
        level: Severity ("error", "warning", "info", "fixed").
        message: Human-readable description.
        auto_fixed: Legacy flag kept for back-compatibility; validate_patch
            never sets it (validation no longer modifies anything).
        proposed_removal: ``(src_id, src_outlet, dst_id, dst_inlet)`` of a
            cord the validator considers invalid, or None. The ids are local
            to the patcher named by *path*. Applied only by an explicit
            ``apply_fixes`` call.
        path: Scope of the finding (Q19): ``""`` at the top level, otherwise
            the box-id chain of the embedded patcher it was found in
            (``obj-1/obj-2``). Nested findings also carry the label prefix
            (``[p synth > gen~] ``) in *message*.
    """

    __slots__ = ("layer", "level", "message", "auto_fixed", "proposed_removal", "path")

    def __init__(
        self,
        layer: str,
        level: str,
        message: str,
        auto_fixed: bool = False,
        proposed_removal: tuple | list | None = None,
        path: str = "",
    ):
        self.layer = layer
        self.level = level
        self.message = message
        self.auto_fixed = auto_fixed
        self.proposed_removal = (
            tuple(proposed_removal) if proposed_removal is not None else None
        )
        self.path = path

    def __repr__(self) -> str:
        return f"[{self.layer}:{self.level}] {self.message}"


# ===========================================================================
# Public API
# ===========================================================================

def validate_patch(
    patch,
    db: ObjectDatabase | None = None,
    allowed_packages: list[str] | None = None,
    *,
    scope: str | None = None,
) -> list[ValidationResult]:
    """Run the full validation pipeline on a patch and every embedded patcher.

    Args:
        patch: Either a Patcher instance or a raw dict in .maxpat format.
        db: ObjectDatabase for lookups. If *patch* is a Patcher instance
            and *db* is None, the Patcher's own db is used.
        allowed_packages: Package filter for Layer 2c. None=skip package
            check (default), []=core only, ["BEAP"]=core+BEAP objects.
            If *patch* is a Patcher instance and *allowed_packages* is
            None, the Patcher's own allowed_packages is used.
        scope: Keyword-only. The patcher scope of the top level: "max",
            "gen" or "rnbo" (Q12 / C3). Resolved in this order: this
            argument (anything outside DOMAIN_SCOPES raises ValueError);
            else a Patcher's ``domain_context``; else
            ``detect_patcher_scope`` on the dict (classnamespace dsp.gen /
            jit.gen -> gen, rnbo -> rnbo; else a top-level maxclass codebox
            -> gen; else max). Layer 2 errors on rnbo/gen-only names outside
            their scope; Layer 4b skips explicit restrictions that include
            the scope.

    Returns:
        Combined list of ValidationResult from all layers and scopes: the
        top level first (exactly as before Q19), then each embedded
        patcher in ``walk.iter_patchers`` pre-order.

    Recursion (Q19 / review A7): every embedded patcher dict (``p``,
    embedded bpatcher / poly~, gen~ / mc.gen~ ``data.patcher`` / jit.gen,
    rnbo~ ...) runs Layers 1-5 with its own scope (``walk.scope_of`` of its
    context; a ``p`` inherits its parent's gen / rnbo scope). Nested results
    get ``path`` (the box-id chain) and a ``[label > label] `` message
    prefix. A nested Layer-1 error skips that scope and every scope under
    it; sibling scopes still run. A gen scope skips Layer 4 (MSP / Max-UI
    rules). Layer 2d warns once per unextracted package per call. In a
    nested rnbo~ scope, an object that is not rnbo_compatible (raw or
    alias-resolved) is a ``rnbo-objects`` warning, and Layer 3 checks only
    bounds / missing boxes / malformed cords (no signal or role type
    checks); a top-level rnbo scope (.rnbopat) is unchanged. Layer 5 checks
    the codeboxes of every gen patcher embedded in a scope, reported at that
    scope. External files are never loaded.

    The input is never mutated (dict or Patcher). Cords Layer 3 considers
    invalid come back as errors with ``proposed_removal`` set; apply them
    with ``apply_fixes(patch, results)`` only when removal is wanted.
    """
    # Import here to avoid circular imports at module level
    from src.maxpat.patcher import Patcher as PatcherClass

    if scope is not None and scope not in DOMAIN_SCOPES:
        raise ValueError(
            f"validate_patch scope must be one of {DOMAIN_SCOPES}, got {scope!r}"
        )

    # Accept Patcher instance: extract db and convert to dict
    if isinstance(patch, PatcherClass):
        if db is None:
            db = patch.db
        if allowed_packages is None:
            allowed_packages = getattr(patch, "allowed_packages", None)
        if scope is None:
            context = getattr(patch, "domain_context", None)
            if context in DOMAIN_SCOPES:
                scope = context
        patch_dict = patch.to_dict()
    else:
        patch_dict = patch

    if scope is None:
        scope = detect_patcher_scope(patch_dict)

    if db is None:
        db = ObjectDatabase()

    results: list[ValidationResult] = []

    # Layer 1: JSON structure
    layer1 = _validate_json_structure(patch_dict)
    results.extend(layer1)
    if any(r.level == "error" for r in layer1):
        return results  # Stop early -- structure is broken

    state = _ScopeState()

    # Layers 2-5 on the top level (unchanged order and messages)
    results.extend(_validate_scope_layers(
        patch_dict, db, allowed_packages, scope, nested=False, state=state,
    ))

    # Every embedded patcher, in walker pre-order (Q19 / A7)
    results.extend(_validate_nested_scopes(
        patch_dict, db, allowed_packages, scope, state,
    ))

    return results


class _ScopeState:
    """Per-``validate_patch`` state shared across scopes."""

    __slots__ = ("warned_packages",)

    def __init__(self) -> None:
        self.warned_packages: set[str] = set()


def _validate_scope_layers(
    patch_dict: dict,
    db: ObjectDatabase,
    allowed_packages: list[str] | None,
    scope: str,
    *,
    nested: bool,
    state: _ScopeState,
) -> list[ValidationResult]:
    """Layers 2-5 on one scope (``patch_dict`` is ``{"patcher": ...}``)."""
    results: list[ValidationResult] = []

    # Layer 2: Object existence
    results.extend(_validate_objects_exist(patch_dict, db, scope))

    # Layer 2b: Maxclass usage (non-UI objects should use "newobj")
    results.extend(_validate_maxclass_usage(patch_dict))

    # Layer 2c: Package gating (defense in depth)
    results.extend(_validate_package_gating(patch_dict, db, allowed_packages))

    # Layer 2d: Community package extracted check (once per package per call)
    results.extend(_validate_community_extracted(
        patch_dict, db, warned_packages=state.warned_packages,
    ))

    # Nested rnbo~ scope: rnbo_compatible:false warns (never blocks), and
    # Layer 3 checks bounds only (RNBO I/O types are not modelled by the DB)
    nested_rnbo = nested and scope == "rnbo"
    if nested_rnbo:
        results.extend(_validate_rnbo_compat(patch_dict, db))

    # Layer 3: Connection bounds and signal types (pure; proposes removals)
    results.extend(_validate_connections(patch_dict, db, type_checks=not nested_rnbo))

    # Layer 4: Domain-specific rules -- MSP / Max-UI only, skipped in gen
    if scope != "gen":
        results.extend(_validate_domain_rules(patch_dict, db))

    # Layer 4b: Domain restriction guard (Phase 29 / VALID-02)
    results.extend(_validate_domain_restrictions(patch_dict, db, scope))

    # Layer 5: GenExpr codeboxes of the gen patchers embedded in this scope
    results.extend(_validate_embedded_genexpr(patch_dict, db, scope))

    return results


_RNBO_DB_CACHE: list = []


def _rnbo_db():
    """Process-wide RNBODatabase, built on first use (lazy import)."""
    if not _RNBO_DB_CACHE:
        from src.maxpat.rnbo import RNBODatabase

        _RNBO_DB_CACHE.append(RNBODatabase())
    return _RNBO_DB_CACHE[0]


def _validate_rnbo_compat(
    patch_dict: dict,
    db: ObjectDatabase,
) -> list[ValidationResult]:
    """Nested rnbo~ scope: warn on objects that are not rnbo_compatible.

    A name is compatible when ``RNBODatabase.is_rnbo_compatible`` accepts it
    raw or alias-resolved (``t`` -> ``trigger``). Warning level, never a
    save blocker (Q19 decision; the rnbo_compatible data has gaps). The
    message matches ``rnbo_validation.validate_rnbo_patch``.
    """
    rnbo_db = _rnbo_db()
    aliases = getattr(db, "_aliases", {}) or {}
    results: list[ValidationResult] = []
    for box_entry in patch_dict["patcher"]["boxes"]:
        box = box_entry.get("box") if isinstance(box_entry, dict) else None
        if not isinstance(box, dict):
            continue
        name = walk.object_name(box)
        if not name:
            continue
        canonical = aliases.get(name, name)
        if rnbo_db.is_rnbo_compatible(name) or rnbo_db.is_rnbo_compatible(canonical):
            continue
        results.append(ValidationResult(
            "rnbo-objects", "warning",
            f"Object '{name}' is not RNBO-compatible -- "
            f"cannot be used in RNBO patches",
        ))
    return results


def _tag(results: list[ValidationResult], path: tuple) -> list[ValidationResult]:
    """Set ``path`` and the label prefix on nested results (in place)."""
    ids = walk.path_ids(path)
    prefix = walk.path_prefix(path)
    for r in results:
        r.path = ids
        r.message = prefix + r.message
    return results


def _validate_nested_scopes(
    patch_dict: dict,
    db: ObjectDatabase,
    allowed_packages: list[str] | None,
    scope: str,
    state: _ScopeState,
) -> list[ValidationResult]:
    """Layers 1-5 on every embedded patcher, tagged with its path."""
    results: list[ValidationResult] = []
    pruned: list[tuple] = []
    for path, inner, context in walk.iter_patchers(patch_dict, scope=scope):
        if not path:
            continue
        if any(path[:len(p)] == p for p in pruned):
            continue
        wrapped = {"patcher": inner}
        layer1 = _tag(_validate_json_structure(wrapped), path)
        results.extend(layer1)
        if any(r.level == "error" for r in layer1):
            pruned.append(path)
            continue
        results.extend(_tag(
            _validate_scope_layers(
                wrapped, db, allowed_packages, walk.scope_of(context),
                nested=True, state=state,
            ),
            path,
        ))
    return results


def has_blocking_errors(
    results: list[ValidationResult],
    is_new: bool = True,
) -> bool:
    """Check whether any error should block output.

    Only results at level ``error`` count; warnings and info never block.

    - An error carrying a ``proposed_removal`` blocks when *is_new* is True
      (the default -- a new patch must not ship a cord the validator would
      drop). With ``is_new=False`` (the edit path) it is reported but not
      blocking.
    - A legacy ``auto_fixed=True`` error without a proposal does not block.
    - Every other error blocks.

    Returns:
        True if output should be blocked.
    """
    for r in results:
        if r.level != "error":
            continue
        if r.proposed_removal is not None:
            if is_new:
                return True
            continue
        if r.auto_fixed:
            continue
        return True
    return False


def apply_fixes(patch, results: list[ValidationResult]) -> list[tuple]:
    """Remove the cords proposed for removal in *results*, in their own scope.

    This is the ONLY code path that removes cords; ``validate_patch`` never
    does. Accepts a raw .maxpat dict (lines are removed by slice-assignment
    so caller references stay valid) or a Patcher (``lines`` filtered in
    place).

    Proposals are grouped by ``ValidationResult.path`` (Q19). The top level
    (``path == ""``) behaves exactly as before. A nested proposal is removed
    only from the lines of the patcher whose box-id chain equals its path:
    for a dict via ``walk.iter_patchers``; for a Patcher via each box's
    inner Patcher, or the mc.gen~ ``data.patcher`` dict kept in the box's
    raw attributes. Every other lines list is untouched, including one
    holding a cord with the same 4-tuple. A path that names no scope, or
    more than one, removes nothing.

    Returns the distinct matched proposals in result order: the 4-tuple
    ``(src_id, src_outlet, dst_id, dst_inlet)`` for a top-level cord, the
    5-tuple ``(path, src_id, src_outlet, dst_id, dst_inlet)`` for a nested
    one. A no-op returning ``[]`` when nothing is proposed or matches.
    Re-run ``validate_patch`` afterwards: removing a cord can change other
    findings.
    """
    from src.maxpat.patcher import Patcher as PatcherClass

    order: list[tuple[str, tuple]] = []
    for r in results:
        key = getattr(r, "proposed_removal", None)
        if key is None:
            continue
        path = getattr(r, "path", "")
        if not isinstance(path, str):
            path = ""
        item = (path, key)
        if item not in order:
            order.append(item)
    if not order:
        return []

    by_path: dict[str, list[tuple]] = {}
    for path, key in order:
        by_path.setdefault(path, []).append(key)

    matched: set[tuple[str, tuple]] = set()
    is_patcher = isinstance(patch, PatcherClass)
    scopes = None
    for path, keys in by_path.items():
        if path == "":
            for k in _apply_top_level(patch, keys, is_patcher):
                matched.add(("", k))
            continue
        if scopes is None:
            scopes = _patcher_scope_map(patch) if is_patcher else _dict_scope_map(patch)
        targets = scopes.get(path, [])
        if len(targets) != 1:
            continue  # unknown or ambiguous path: remove nothing
        for k in _filter_scope_lines(targets[0], set(keys)):
            matched.add((path, k))

    out: list[tuple] = []
    for path, key in order:
        if (path, key) in matched:
            out.append(key if path == "" else (path,) + tuple(key))
    return out


def _apply_top_level(patch, keys: list[tuple], is_patcher: bool) -> set[tuple]:
    """Top-level removal, unchanged from pre-Q19 apply_fixes."""
    wanted = set(keys)
    matched: set[tuple] = set()

    if is_patcher:
        kept = []
        for line in patch.lines:
            k = (line.source_id, line.source_outlet, line.dest_id, line.dest_inlet)
            if k in wanted:
                matched.add(k)
            else:
                kept.append(line)
        patch.lines[:] = kept
    else:
        patcher = patch.get("patcher") if isinstance(patch, dict) else None
        lines = patcher.get("lines") if isinstance(patcher, dict) else None
        if not isinstance(lines, list):
            return matched
        kept = []
        for entry in lines:
            patchline = entry.get("patchline", {}) if isinstance(entry, dict) else {}
            if not isinstance(patchline, dict):
                patchline = {}
            k = _line_key(patchline)
            if k in wanted:
                matched.add(k)
            else:
                kept.append(entry)
        lines[:] = kept

    return matched


def _filter_scope_lines(target, wanted: set[tuple]) -> set[tuple]:
    """Remove *wanted* cords from one scope (a Patcher or a patcher dict)."""
    from src.maxpat.patcher import Patcher as PatcherClass

    matched: set[tuple] = set()
    if isinstance(target, PatcherClass):
        kept = []
        for line in target.lines:
            k = (line.source_id, line.source_outlet, line.dest_id, line.dest_inlet)
            if k in wanted:
                matched.add(k)
            else:
                kept.append(line)
        target.lines[:] = kept
        return matched
    lines = target.get("lines") if isinstance(target, dict) else None
    if not isinstance(lines, list):
        return matched
    kept = []
    for entry in lines:
        patchline = entry.get("patchline", {}) if isinstance(entry, dict) else {}
        if not isinstance(patchline, dict):
            patchline = {}
        k = _line_key(patchline)
        if k in wanted:
            matched.add(k)
        else:
            kept.append(entry)
    lines[:] = kept
    return matched


def _dict_scope_map(patch) -> dict[str, list]:
    """``path_ids`` -> [patcher dict] for every nested scope of a dict."""
    scopes: dict[str, list] = {}
    for path, inner, _ in walk.iter_patchers(patch):
        if path:
            scopes.setdefault(walk.path_ids(path), []).append(inner)
    return scopes


def _patcher_scope_map(patcher) -> dict[str, list]:
    """``path_ids`` -> [inner Patcher or patcher dict] for a Patcher.

    Mirrors the ids ``validate_patch`` sees through ``Patcher.to_dict()``:
    a box's inner Patcher (``_inner_patcher``) when present, else the
    mc.gen~ ``data.patcher`` dict in the box's raw attributes (``_raw``
    for a loaded box, ``extra_attrs`` for a created one), walked in dict
    mode below that.
    """
    from src.maxpat.patcher import Patcher as PatcherClass

    scopes: dict[str, list] = {}
    stack: list[tuple[str, object]] = [("", patcher)]
    seen: set[int] = set()
    while stack:
        path, node = stack.pop()
        if id(node) in seen:
            continue
        seen.add(id(node))
        if path:
            scopes.setdefault(path, []).append(node)
        if isinstance(node, PatcherClass):
            for box in node.boxes:
                box_id = str(box.id) if box.id is not None else "?"
                child_path = f"{path}/{box_id}" if path else box_id
                inner = getattr(box, "_inner_patcher", None)
                if inner is not None:
                    stack.append((child_path, inner))
                    continue
                raw = box._raw if getattr(box, "_raw", None) is not None else box.extra_attrs
                data_inner = walk.inner_patcher({"data": raw.get("data")}) if isinstance(raw, dict) else None
                if data_inner is not None:
                    stack.append((child_path, data_inner))
        elif isinstance(node, dict):
            boxes = node.get("boxes")
            if not isinstance(boxes, list):
                continue
            for entry in boxes:
                box = entry.get("box") if isinstance(entry, dict) else None
                inner = walk.inner_patcher(box)
                if inner is None:
                    continue
                box_id = box.get("id")
                box_id = str(box_id) if box_id is not None else "?"
                stack.append((f"{path}/{box_id}", inner))
    return scopes


# ===========================================================================
# Layer 1: JSON Structure
# ===========================================================================

def _validate_json_structure(patch_dict: dict) -> list[ValidationResult]:
    """Check that the patch dict has the required .maxpat structure.

    Errors (Layer 1; any error stops the top level and prunes a nested
    scope): missing ``patcher``; ``boxes`` / ``lines`` not a list; a box
    entry that is not a dict or whose ``box`` value is not a dict; a line
    entry that is not a dict or whose ``patchline`` value is not a dict
    (a dict entry without the key stays tolerated); duplicate box ids
    (str / int ``id``), one error per id in first-appearance order (Q19).
    """
    results: list[ValidationResult] = []

    if "patcher" not in patch_dict:
        results.append(ValidationResult(
            "json", "error",
            "Missing 'patcher' key at top level",
        ))
        return results

    patcher = patch_dict["patcher"]

    if not isinstance(patcher.get("boxes"), list):
        results.append(ValidationResult(
            "json", "error",
            "Missing or invalid 'boxes' array in patcher",
        ))

    if not isinstance(patcher.get("lines"), list):
        results.append(ValidationResult(
            "json", "error",
            "Missing or invalid 'lines' array in patcher",
        ))

    boxes = patcher.get("boxes")
    lines = patcher.get("lines")

    if isinstance(boxes, list):
        for idx, entry in enumerate(boxes):
            if not isinstance(entry, dict) or (
                "box" in entry and not isinstance(entry["box"], dict)
            ):
                results.append(ValidationResult(
                    "json", "error",
                    f'Malformed box entry at index {idx}: expected {{"box": {{...}}}}',
                ))

    if isinstance(lines, list):
        for idx, entry in enumerate(lines):
            if not isinstance(entry, dict) or (
                "patchline" in entry and not isinstance(entry["patchline"], dict)
            ):
                results.append(ValidationResult(
                    "json", "error",
                    f'Malformed line entry at index {idx}: expected {{"patchline": {{...}}}}',
                ))

    if isinstance(boxes, list):
        counts: dict = {}
        for entry in boxes:
            box = entry.get("box") if isinstance(entry, dict) else None
            if not isinstance(box, dict):
                continue
            box_id = box.get("id")
            if isinstance(box_id, bool) or not isinstance(box_id, (str, int)):
                continue
            counts[box_id] = counts.get(box_id, 0) + 1
        for box_id, n in counts.items():
            if n > 1:
                results.append(ValidationResult(
                    "json", "error",
                    f"Duplicate box id '{box_id}' ({n} boxes)",
                ))

    return results


# ===========================================================================
# Layer 2: Object Existence
# ===========================================================================

_SCOPE_PLACEMENT = {
    "rnbo": "inside an rnbo~ patcher",
    "gen": "inside a gen~ patcher or codebox",
}


def _validate_objects_exist(
    patch_dict: dict,
    db: ObjectDatabase,
    scope: str = "max",
) -> list[ValidationResult]:
    """Check every object in the patch exists in the database.

    A name whose DB entries all come from rnbo/ and/or gen/ (and has no
    explicit domain_restricted key) exists only in RNBO / Gen: outside its
    scope MAX says "No such object", so it is an error here (Q12 / C3).
    Top-level boxes only; *scope* is the top-level patcher's scope.
    """
    results: list[ValidationResult] = []

    for box_entry in patch_dict["patcher"]["boxes"]:
        box = box_entry.get("box", {})
        name = walk.object_name(box)

        if name is None:
            continue  # structural maxclass -- skip

        # Check existence (resolves aliases internally)
        if db.exists(name):
            implied = db.get_implied_restrictions(name)
            if implied and scope not in implied:
                where = " or ".join(
                    _SCOPE_PLACEMENT.get(d, f"inside a {d} patcher") for d in implied
                )
                msg = (
                    f"'{name}' exists only in {implied} -- No such object in a "
                    f"{scope} patcher. Use it {where}."
                )
                equivalent = db.suggest_max_equivalent(name)
                if equivalent:
                    msg += f" MAX equivalent: {equivalent}"
                results.append(ValidationResult("objects", "error", msg))
            continue

        # Check if it is a PD object with a MAX equivalent
        if db.is_pd_object(name):
            equivalent = db.get_pd_equivalent(name)
            results.append(ValidationResult(
                "objects", "error",
                f"'{name}' is a Pure Data object, not MAX. "
                f"Use {equivalent} instead.",
            ))
        else:
            # Check if it is a known UI maxclass that might not be in the db
            if is_ui_object(name):
                continue  # UI objects may not have db entries; that is OK
            results.append(ValidationResult(
                "objects", "warning",
                f"Unknown object: '{name}' -- not in database",
            ))

    return results


def _validate_maxclass_usage(patch_dict: dict) -> list[ValidationResult]:
    """Check that non-UI objects use maxclass='newobj', not their own name.

    Objects whose maxclass is neither 'newobj' nor a known UI maxclass are
    authored with incorrect maxclass values. For example, a box with
    maxclass='cycle~' instead of maxclass='newobj' with text='cycle~' will
    not load correctly in MAX (raises "invalid attribute maxclass" errors).

    Skips:
    - Structural maxclasses (inlet, outlet, bpatcher).
    - Boxes with an embedded ``patcher`` key (legitimate subpatcher
      containers like ``gen~``, ``poly~``, ``rnbo~``, ``codebox`` in
      embedded mode that carry their own maxclass with an inline patcher).

    A maxclass-``patcher`` box without an embedded patcher is flagged: MAX
    saves p/patcher only as newobj (review C4).

    Emits ``error`` (not warning) — this is a hard correctness check.
    """
    results: list[ValidationResult] = []

    for box_entry in patch_dict["patcher"]["boxes"]:
        box = box_entry.get("box", {})
        maxclass = box.get("maxclass", "")

        # Skip structural maxclasses
        if maxclass in _MAXCLASS_USAGE_SKIP:
            continue

        # Subpatcher containers (gen~, poly~, rnbo~, codebox in embedded mode)
        # carry their own maxclass legitimately when an embedded `patcher` key
        # is present.
        if "patcher" in box:
            continue

        # newobj is always correct for non-UI objects
        if maxclass == "newobj":
            continue

        # Known UI maxclasses are correct when used as their own maxclass
        if maxclass in UI_MAXCLASSES:
            continue

        # Non-UI, non-structural maxclass that isn't newobj -- flag as error.
        name = walk.object_name(box) or maxclass
        results.append(ValidationResult(
            "objects", "error",
            f"Wrong maxclass: object '{name}' uses maxclass='{maxclass}' "
            f"but should use maxclass='newobj' with text='{name} ...' "
            f"(only UI widgets use their own name as maxclass; see "
            f"UI_MAXCLASSES in src/maxpat/maxclass_map.py)",
        ))

    return results


# ===========================================================================
# Layer 2c: Package Gating (Defense in Depth)
# ===========================================================================

def _validate_package_gating(
    patch_dict: dict,
    db: ObjectDatabase,
    allowed_packages: list[str] | None,
) -> list[ValidationResult]:
    """Check that no objects from non-allowed packages appear in the patch.

    This is defense-in-depth: Patcher-level gating should catch these during
    generation, but this catches violations in loaded/edited patches.

    Args:
        patch_dict: The .maxpat-style dict to validate.
        db: ObjectDatabase for package lookups.
        allowed_packages: Package filter. None=skip check, []=core only,
            ["BEAP"]=core+BEAP objects.

    Returns:
        List of ValidationResult for package violations.
    """
    if allowed_packages is None:
        return []  # No package config -- skip check

    results: list[ValidationResult] = []
    for box_entry in patch_dict["patcher"]["boxes"]:
        box = box_entry.get("box", {})
        name = walk.object_name(box)
        if name is None:
            continue
        package = db.get_package(name)
        if package and package not in allowed_packages:
            results.append(ValidationResult(
                "packages", "error",
                f"Object '{name}' from package '{package}' not in allowed "
                f"packages (allowed: {allowed_packages})",
            ))
    return results


# ===========================================================================
# Layer 2d: Community Package Extracted Check
# ===========================================================================

def _validate_community_extracted(
    patch_dict: dict,
    db: ObjectDatabase,
    warned_packages: set | None = None,
) -> list[ValidationResult]:
    """Layer 2d: Warn when patch uses objects from unextracted community packages.

    Per D-07/D-09: Block generation with community packages that have not been
    locally extracted. The check uses the ``extracted`` flag in package_info.json
    (no filesystem probing). *warned_packages* is shared across the scopes of
    one ``validate_patch`` call so a package warns once per patch (Q19);
    None starts a fresh set.
    """
    results: list[ValidationResult] = []
    if warned_packages is None:
        warned_packages = set()

    for box_entry in patch_dict["patcher"]["boxes"]:
        box = box_entry.get("box", {})
        name = walk.object_name(box)
        if name is None:
            continue
        package = db.get_package(name)
        if package is None or package in warned_packages:
            continue
        info = db.get_package_info(package)
        if info is None:
            continue
        tier = info.get("tier", "")
        if tier not in ("community", "licensed"):
            continue  # Bundled packages always available
        if info.get("extracted", False):
            continue  # Already extracted locally

        warned_packages.add(package)
        install_method = info.get("install_method", "package_manager")

        # IRCAM Spat gets a specific message per RESEARCH.md
        if package == "IRCAM Spat":
            msg = (
                "IRCAM Spat is not extracted. "
                "Download from https://forum.ircam.fr/projects/detail/spat/ "
                "(free IRCAM Forum account required), copy the spat5 folder to "
                "~/Documents/Max 9/Packages/, then run: "
                "python .claude/scripts/extract_objects.py --package \"IRCAM Spat\""
            )
        elif install_method == "package_manager":
            msg = (
                f"{package} is not extracted. "
                f"Install via MAX Package Manager (Help -> Package Manager -> search '{package}'), "
                f"then run: python .claude/scripts/extract_objects.py --package \"{package}\""
            )
        else:
            msg = (
                f"{package} is not extracted. "
                f"Download from the official source and copy to ~/Documents/Max 9/Packages/, "
                f"then run: python .claude/scripts/extract_objects.py --package \"{package}\""
            )

        results.append(ValidationResult("packages", "warning", msg))

    return results


# ===========================================================================
# Layer 3: Connection Validation (Bounds + Signal Types)
# ===========================================================================

def _line_key(patchline: dict) -> tuple:
    """Return ``(src_id, src_outlet, dst_id, dst_inlet)`` for a patchline.

    A non-list source/destination is treated as empty and missing elements
    are padded with None, so malformed lines still get a stable key that
    ``apply_fixes`` can match.
    """
    source = patchline.get("source")
    destination = patchline.get("destination")
    src = list(source[:2]) if isinstance(source, list) else []
    dst = list(destination[:2]) if isinstance(destination, list) else []
    src += [None] * (2 - len(src))
    dst += [None] * (2 - len(dst))
    return (src[0], src[1], dst[0], dst[1])


def _is_container_box(box: dict) -> bool:
    """True for boxes that forward any cord to an inner patcher (review A1).

    Any box with an embedded patcher dict, maxclass patcher/bpatcher, or a
    newobj whose first token is in _CONTAINER_NAMES.
    """
    if isinstance(box.get("patcher"), dict):
        return True
    maxclass = box.get("maxclass", "")
    if maxclass in ("patcher", "bpatcher"):
        return True
    if maxclass == "newobj":
        return walk.box_name(box) in _CONTAINER_NAMES
    return False


def _validate_connections(
    patch_dict: dict,
    db: ObjectDatabase,
    *,
    type_checks: bool = True,
) -> list[ValidationResult]:
    """Validate connection index bounds and signal/control type compatibility.

    Pure: never writes to *patch_dict*. A cord considered invalid is
    reported as an error carrying ``proposed_removal`` (its 4-tuple key);
    removal happens only via ``apply_fixes``. Check order per cord:
    bounds (always, even for containers and known pairs) -> known pair
    from relationships.json (e.g. tapin~ -> tapout~; no type/role checks)
    -> container destination (no type/role checks) -> role dispatch
    (skipped for container sources; mismatches warn, cord kept) -> legacy
    signal/control check. With ``type_checks=False`` (nested rnbo~ scopes,
    Q19) a cord whose bounds pass is not checked further.
    """
    results: list[ValidationResult] = []

    # Build box lookup: id -> box dict
    box_lookup: dict[str, dict] = {}
    for box_entry in patch_dict["patcher"]["boxes"]:
        box = box_entry.get("box", {})
        box_id = box.get("id")
        if box_id:
            box_lookup[box_id] = box

    lines = patch_dict["patcher"]["lines"]

    for idx, line_entry in enumerate(lines):
        patchline = line_entry.get("patchline", {})
        source = patchline.get("source", [])
        destination = patchline.get("destination", [])
        key = _line_key(patchline)

        if (
            not isinstance(source, list) or not isinstance(destination, list)
            or len(source) < 2 or len(destination) < 2
        ):
            results.append(ValidationResult(
                "connections", "error",
                f"Malformed patchline at index {idx}: "
                f"source={source}, destination={destination} "
                f"{_PROPOSED_SUFFIX}",
                proposed_removal=key,
            ))
            continue

        src_id, src_outlet = source[0], source[1]
        dst_id, dst_inlet = destination[0], destination[1]

        src_box = box_lookup.get(src_id)
        dst_box = box_lookup.get(dst_id)

        if src_box is None or dst_box is None:
            results.append(ValidationResult(
                "connections", "error",
                f"Connection references missing box: "
                f"source={src_id}, dest={dst_id} {_PROPOSED_SUFFIX}",
                proposed_removal=key,
            ))
            continue

        out_of_bounds = False

        # --- Check outlet bounds ---
        src_numoutlets = src_box.get("numoutlets", 0)
        if src_outlet >= src_numoutlets:
            results.append(ValidationResult(
                "connections", "error",
                f"Outlet index {src_outlet} out of bounds on '{src_id}' "
                f"(has {src_numoutlets} outlet(s)) {_PROPOSED_SUFFIX}",
                proposed_removal=key,
            ))
            out_of_bounds = True

        # --- Check inlet bounds ---
        dst_numinlets = dst_box.get("numinlets", 0)
        if dst_inlet >= dst_numinlets:
            results.append(ValidationResult(
                "connections", "error",
                f"Inlet index {dst_inlet} out of bounds on '{dst_id}' "
                f"(has {dst_numinlets} inlet(s)) {_PROPOSED_SUFFIX}",
                proposed_removal=key,
            ))
            out_of_bounds = True

        if out_of_bounds or not type_checks:
            continue

        # --- Known companion pair (relationships.json): no type/role checks ---
        src_name = walk.object_name(src_box)
        dst_name = walk.object_name(dst_box)
        if (
            src_name is not None and dst_name is not None
            and db.is_known_pair(src_name, dst_name)
        ):
            continue

        # --- Container destination: accepts any cord (A1) ---
        if _is_container_box(dst_box):
            continue

        src_is_container = _is_container_box(src_box)

        # --- Role-aware tier dispatch (VALID-01, D-01..D-04) ---
        # Runs BEFORE legacy signal:bool check. When src outlet has a
        # curated signal_role (Phase 28), look up (role, dst_kind) in
        # _ROLE_TIER_TABLE. Hit -> warn (cord kept) and skip legacy branch
        # (D-02). Miss / None / audio source -> fall through unchanged.
        # Container outlets carry no signal_role (A1).
        if src_name is not None and not src_is_container:
            # args make the role layout-aware: `sfplay~ 2` outlet 1 is
            # audio, not the 1-channel form's done-bang (barnett-dbap
            # v0.4.0 lost its stereo file cord to that misread)
            src_args = (
                walk.box_args(src_box)
                if src_box.get("maxclass") == "newobj" else None
            )
            src_role = db.get_signal_role(src_name, src_outlet, args=src_args)
            if src_role is not None and src_role != "audio":
                tier = _classify_role_mismatch(
                    src_role, dst_box, dst_inlet, db
                )
                if tier is not None:
                    level, message = tier
                    results.append(ValidationResult(
                        "connections", level,
                        f"{message} ('{src_id}' outlet {src_outlet} -> "
                        f"'{dst_id}' inlet {dst_inlet}) -- connection kept",
                    ))
                    # Tier result is final — skip legacy is_signal_source
                    # branch for this line (D-02 clean separation).
                    continue

        # --- Signal type compatibility (bounds are OK) ---
        src_outlettype = src_box.get("outlettype", [])
        is_signal_source = (
            src_outlet < len(src_outlettype)
            and src_outlettype[src_outlet] == "signal"
        )

        if is_signal_source:
            # Guard: non-overridden MSP objects have unverified outlet types.
            # The MSP domain extraction marked ALL outlets as signal=true,
            # so for uncorrected objects a valid control outlet would be
            # incorrectly flagged. Emit a warning and preserve the connection.
            if src_name and src_name.endswith("~") and not db.is_overridden(src_name):
                results.append(ValidationResult(
                    "connections", "warning",
                    f"Unverified outlet types: '{src_name}' outlet "
                    f"{src_outlet} -> '{dst_id}' inlet {dst_inlet} "
                    f"-- source MSP object not in overrides, "
                    f"connection preserved",
                ))
            else:
                # Overridden MSP or non-MSP: propose removal
                dst_accepts_signal = _inlet_accepts_signal(dst_box, dst_inlet, db)
                if not dst_accepts_signal:
                    results.append(ValidationResult(
                        "connections", "error",
                        f"Signal outlet to control-only inlet: "
                        f"'{src_id}' outlet {src_outlet} -> "
                        f"'{dst_id}' inlet {dst_inlet} {_PROPOSED_SUFFIX}",
                        proposed_removal=key,
                    ))

    return results


def _inlet_accepts_signal(box_dict: dict, inlet_idx: int, db: ObjectDatabase) -> bool:
    """Determine if a specific inlet on a box can accept a signal connection.

    Per CLAUDE.md: "signal/float inlets accept both signal and control connections."
    So we only return False when the inlet is purely control-only (signal: false
    and not a signal/float type).
    """
    # Try to get inlet info from the database
    name = walk.object_name(box_dict)
    if name is None:
        return True  # structural objects -- allow anything

    obj_data = db.lookup(name)
    if obj_data is None:
        # Unknown object -- be permissive
        return True

    inlets = obj_data.get("inlets", [])
    if inlet_idx < len(inlets):
        inlet = inlets[inlet_idx]
        # If the inlet is marked as signal, it accepts signal
        if inlet.get("signal"):
            return True
        # Check the type field for "signal/float" pattern
        inlet_type = inlet.get("type", "").lower()
        if "signal" in inlet_type:
            return True
        # Purely control inlet
        return False

    # Inlet index beyond what database knows (e.g., variable I/O)
    # Be permissive
    return True


def _classify_dst_inlet(dst_box: dict, dst_inlet: int, db: ObjectDatabase) -> str:
    """Classify a destination inlet for role-aware tier-table lookup.

    Returns one of:
      "signal"   — inlet accepts signal (includes signal/float hybrid inlets;
                   the tier table treats both as a mechanical-fix mismatch
                   when the source role is status/trigger/data/list)
      "float"    — inlet stores/displays a numeric value (UI float widgets
                   like flonum/number, or control inlets with type='float')
      "control"  — generic control inlet OR unknown / structural box

    Used by _classify_role_mismatch to look up the dst_kind side of
    _ROLE_TIER_TABLE keys (D-04 message-format requirement).
    """
    # UI maxclass float-display widgets (flonum, number, live.numbox) carry
    # type="control" inlets in the DB but are float-display by nature — the
    # WARNING tier (trigger/list -> float) targets these by intent.
    maxclass = dst_box.get("maxclass", "")
    if maxclass in _FLOAT_DISPLAY_MAXCLASSES and dst_inlet == 0:
        return "float"

    name = walk.object_name(dst_box)
    if name is None:
        return "control"  # structural maxclass; conservative
    obj = db.lookup(name)
    if obj is None:
        return "control"
    inlets = obj.get("inlets", [])
    if dst_inlet >= len(inlets):
        return "control"
    inlet = inlets[dst_inlet]
    inlet_type = (inlet.get("type") or "").lower()
    # "signal/float" inlets are still classified as "signal" for tier-table
    # purposes: a status/trigger/list/data outlet is an event-message stream,
    # not a numeric value, so the mechanical-fix tier still applies (snapshot~,
    # sig~, etc.). The tier table itself decides what's a mismatch — the
    # dst-kind label is intentionally coarse here.
    if inlet.get("signal"):
        return "signal"
    if "float" in inlet_type or inlet_type == "float":
        return "float"
    return "control"


def _classify_role_mismatch(
    src_role: str,
    dst_box: dict,
    dst_inlet: int,
    db: ObjectDatabase,
) -> tuple[str, str] | None:
    """Look up (src_role, dst_kind) in _ROLE_TIER_TABLE.

    Returns (level, message) when a tier-table entry matches, or None to
    signal "fall through to legacy signal:bool branch" (D-02). Every level
    is "warning" (Q1 / A1): a role mismatch never removes a cord.

    Per D-04, the message is formatted as
    "{src_role} outlet → {dst_kind} inlet: {suggestion}" — concrete and
    suggestion-bearing, never generic "type mismatch". The dst_kind label
    is folded into the pre-formatted message and not returned separately;
    the only caller (the role-aware tier dispatch in
    `_validate_connection_bounds`) consumed the message verbatim.

    A destination inlet whose DB ``type`` names the source role as one of
    its ``/``-separated tokens accepts that role outright (Q2 / A1):
    biquad~ inlet 0 is ``signal/list`` because its refpage documents the
    five-coefficient list there, so filtergraph~ -> biquad~ returns None
    here and falls through to the legacy branch. Plain ``signal`` inlets
    carry no role token and still warn.
    """
    name = walk.object_name(dst_box)
    if name is not None:
        obj = db.lookup(name)
        if obj is not None:
            inlets = obj.get("inlets", [])
            if 0 <= dst_inlet < len(inlets):
                inlet_type = (inlets[dst_inlet].get("type") or "").lower()
                if src_role in inlet_type.split("/"):
                    return None
    dst_kind = _classify_dst_inlet(dst_box, dst_inlet, db)
    entry = _ROLE_TIER_TABLE.get((src_role, dst_kind))
    if entry is None:
        return None
    level, suggestion = entry
    message = f"{src_role} outlet → {dst_kind} inlet: {suggestion}"
    return (level, message)


# ===========================================================================
# Layer 4: Domain-Specific Rules
# ===========================================================================

def _validate_domain_rules(
    patch_dict: dict,
    db: ObjectDatabase,
) -> list[ValidationResult]:
    """Check domain-specific rules for MSP signal chains."""
    results: list[ValidationResult] = []

    boxes = patch_dict["patcher"]["boxes"]
    lines = patch_dict["patcher"]["lines"]

    # Build lookup structures
    box_lookup: dict[str, dict] = {}
    for box_entry in boxes:
        box = box_entry.get("box", {})
        box_id = box.get("id")
        if box_id:
            box_lookup[box_id] = box

    # Build signal graph (adjacency list): src_id -> list of dst_ids
    signal_adj: dict[str, list[str]] = defaultdict(list)
    # Also track which boxes have signal connections going OUT and IN
    has_signal_out: set[str] = set()
    has_signal_in: set[str] = set()

    for line_entry in lines:
        patchline = line_entry.get("patchline", {})
        source = patchline.get("source", [])
        destination = patchline.get("destination", [])
        if len(source) < 2 or len(destination) < 2:
            continue

        src_id, src_outlet = source[0], source[1]
        dst_id = destination[0]

        src_box = box_lookup.get(src_id)
        if not src_box:
            continue

        # Determine if this is a signal connection
        src_outlettype = src_box.get("outlettype", [])
        is_signal = (
            src_outlet < len(src_outlettype)
            and src_outlettype[src_outlet] == "signal"
        )

        if is_signal:
            signal_adj[src_id].append(dst_id)
            has_signal_out.add(src_id)
            has_signal_in.add(dst_id)

    # Build control adjacency: src_id -> list of dst_ids (non-signal connections)
    ctrl_adj: dict[str, list[str]] = defaultdict(list)

    for line_entry in lines:
        patchline = line_entry.get("patchline", {})
        source = patchline.get("source", [])
        destination = patchline.get("destination", [])
        if len(source) < 2 or len(destination) < 2:
            continue

        src_id, src_outlet = source[0], source[1]
        dst_id = destination[0]

        src_box = box_lookup.get(src_id)
        if not src_box:
            continue

        src_outlettype = src_box.get("outlettype", [])
        is_sig = (
            src_outlet < len(src_outlettype)
            and src_outlettype[src_outlet] == "signal"
        )
        if not is_sig:
            ctrl_adj[src_id].append(dst_id)

    # --- Rule: Compound #N argument substitution ---
    results.extend(_check_compound_argument_substitution(box_lookup))

    # --- Rule: Unterminated signal chains ---
    results.extend(_check_unterminated_chains(
        box_lookup, has_signal_out, dsp_roles.chain_terminal_names(db),
    ))

    # --- Rule: Missing gain staging ---
    results.extend(_check_gain_staging(
        box_lookup, signal_adj,
        dsp_roles.gain_stage_names(db), dsp_roles.output_terminal_names(db),
    ))

    # --- Rule: Unsafe gain values ---
    results.extend(_check_unsafe_gain_values(box_lookup))

    # --- Rule: Feedback loop detection ---
    results.extend(_check_feedback_loops(box_lookup, signal_adj))

    # --- Rule: GenExpr I/O syntax ---
    results.extend(_check_genexpr_io_syntax(box_lookup))

    # --- Rule: GenExpr delay usage ---
    results.extend(_check_genexpr_delay_usage(box_lookup))

    # --- Rule: gen~ @param message syntax ---
    results.extend(_check_gen_param_message_syntax(box_lookup, ctrl_adj))

    # --- Rule: Comment #N substitution ---
    results.extend(_check_comment_hash_substitution(box_lookup, ctrl_adj))

    # --- Rule: line~ comma messages ---
    results.extend(_check_line_tilde_comma_messages(box_lookup, ctrl_adj))

    # --- Rule: multislider fetchindex ---
    results.extend(_check_multislider_fetchindex(box_lookup))

    # --- Rule: umenu items format ---
    results.extend(_check_umenu_items_format(box_lookup))

    # --- Rule: Assistance comments ---
    results.extend(_check_assistance_comments(box_lookup))

    return results


# ===========================================================================
# Layer 4b: Domain Restriction Guard (Phase 29 / VALID-02 / D-05..D-08)
# ===========================================================================

def _validate_domain_restrictions(
    patch_dict: dict,
    db: ObjectDatabase,
    scope: str = "max",
) -> list[ValidationResult]:
    """Hard-block boxes whose domain_restricted whitelist forbids the scope
    of the patcher they sit in (*scope*: max / gen / rnbo; Q12).

    Per D-05 (kept): explicit `domain_restricted` only — implied RNBO/Gen
    restrictions live in Layer 2. A box whose explicit restriction includes
    *scope* is allowed (``floor~`` in an rnbo patcher). At Max scope the
    message is unchanged. Runs in every scope: ``validate_patch`` calls it
    for the top level and for each embedded patcher with that patcher's own
    scope (Q19 retired D-07, "top-level only"), so ``floor~`` inside gen~
    or inside a ``p`` in a Max patch is flagged with its path. Per D-08:
    always ERROR severity, auto_fixed=False (auto-removing the box would
    mangle the patch; emit error and let the caller decide).
    """
    results: list[ValidationResult] = []
    for box_entry in patch_dict["patcher"]["boxes"]:
        box = box_entry.get("box", {})
        # Subpatcher containers (gen~/rnbo~/m4l-anything) carry their own
        # maxclass legitimately and may someday acquire domain_restricted
        # markers — skip them so we don't false-positive on the canonical
        # gen~/rnbo~ at top level. Mirrors the escape hatch in
        # _validate_maxclass_usage.
        if "patcher" in box:
            continue
        name = walk.object_name(box)
        if name is None:
            continue
        restrictions = db.get_domain_restrictions(name)
        if not restrictions or scope in restrictions:
            continue
        if scope != "max":
            results.append(ValidationResult(
                "domain", "error",
                f"'{name}' is restricted to {restrictions}; "
                f"not allowed in a {scope} patcher.",
                auto_fixed=False,
            ))
            continue
        # A Max top-level patcher is NOT inside any rnbo~/m4l/gen~
        # container. Any restriction list is a violation here (D-07).
        results.append(ValidationResult(
            "domain", "error",
            f"'{name}' is restricted to {restrictions}; "
            f"not allowed at MSP/Max top level. "
            f"Wrap in {restrictions[0]}~ container or use a non-restricted equivalent.",
            auto_fixed=False,
        ))
    return results


# ===========================================================================
# Layer 5: Embedded GenExpr Codebox Walker (Phase 29 / VALID-04 / D-17)
# ===========================================================================

def _validate_embedded_genexpr(
    patch_dict: dict,
    db: ObjectDatabase,
    scope: str = "max",
) -> list[ValidationResult]:
    """Check the GenExpr codeboxes of every gen patcher embedded in this scope.

    For every box B of this scope (*scope*: max / gen / rnbo) whose embedded
    patcher (``walk.inner_patcher``: ``patcher`` or mc.gen~ ``data.patcher``)
    is a gen scope (``walk.inner_scope``: gen~, mc.gen~, mcs.gen~, gen,
    jit.gen, jit.pix, jit.gl.pix, or any subpatcher of a gen patcher), each
    ``maxclass == "codebox"`` box in that patcher with a non-empty ``code``
    str runs validate_genexpr (Checks 1-9: the gen-domain operator check 6,
    delay() 7 and init-before-if/else 9; Check 8, the clip() rejection, was
    retired in Q12 -- GenExpr has clip()). Findings are emitted in THIS
    scope as ``<container> '<id>' codebox: <msg>`` (container = B's name,
    else its maxclass), so they carry this scope's path and prefix. A
    top-level gen~ gives exactly the pre-Q19 ``gen~ '<id>' codebox: `` form.

    Reporting rule (Q19): every codebox is reported exactly once, by the
    scope that holds its container. The walker still visits the gen patcher
    itself, but that scope's own codeboxes are its parent's job, so a
    top-level gen file's own codeboxes (``.gendsp``) stay unchecked here --
    ``hooks.validate_code_file`` covers them.

    Note (RESEARCH.md R1): existing Layer 4 helpers
    `_check_genexpr_io_syntax` and `_check_genexpr_delay_usage` iterate
    box_lookup and match boxes whose maxclass=='newobj' with text starting
    'codebox'. Embedded codeboxes inside gen patchers have
    maxclass=='codebox' (not 'newobj') and live in the inner patcher (not
    box_lookup), so the two channels do NOT overlap in the canonical
    embedded-codebox case. Top-level codeboxes remain a duplicate-emission
    corner case (rare in practice). Consolidating to a single channel is
    OUT OF SCOPE here; Phase 33-class cleanup.
    """
    # Deferred import -- code_validation imports validation, so avoid a
    # circular import at module top.
    from src.maxpat.code_validation import validate_genexpr

    if scope not in DOMAIN_SCOPES:
        scope = "max"
    results: list[ValidationResult] = []
    for box_entry in patch_dict["patcher"]["boxes"]:
        box = box_entry.get("box") if isinstance(box_entry, dict) else None
        if not isinstance(box, dict):
            continue
        inner = walk.inner_patcher(box)
        if inner is None:
            continue
        if walk.inner_scope(box, scope) != "gen":
            continue
        inner_boxes = inner.get("boxes")
        if not isinstance(inner_boxes, list):
            continue
        container = walk.box_name(box) or walk.box_maxclass(box)
        box_id = box.get("id", "<unknown>")
        for inner_entry in inner_boxes:
            inner_box = inner_entry.get("box") if isinstance(inner_entry, dict) else None
            if not isinstance(inner_box, dict):
                continue
            if inner_box.get("maxclass") != "codebox":
                continue
            code = inner_box.get("code")
            if not isinstance(code, str) or not code:
                continue
            for r in validate_genexpr(code, db=db):
                results.append(ValidationResult(
                    r.layer, r.level,
                    f"{container} '{box_id}' codebox: {r.message}",
                    auto_fixed=r.auto_fixed,
                ))
    return results


# Pattern matching compound #N usage: text containing #N preceded or followed
# by non-whitespace characters (e.g., "slot-#1", "#1-out", "my#2thing").
# Standalone #N (space-delimited or at start/end of text) is fine.
_COMPOUND_ARG_PATTERN = _re.compile(r'(?:\S)#\d+|#\d+(?=\S)')


def _check_compound_argument_substitution(
    box_lookup: dict[str, dict],
) -> list[ValidationResult]:
    """Warn about compound #N argument substitution in object/message text.

    In bpatchers and abstractions, #1 etc. must be standalone tokens.
    Compound forms like 'slot-#1' or '#1-out' do not substitute correctly.
    """
    results: list[ValidationResult] = []

    for box_id, box in box_lookup.items():
        text = walk.box_text(box)
        if not text:
            continue

        # Only check objects/messages that actually use #N
        if "#" not in text:
            continue

        matches = _COMPOUND_ARG_PATTERN.findall(text)
        if matches:
            results.append(ValidationResult(
                "domain", "warning",
                f"Compound #N substitution in '{text}' ({box_id}) -- "
                f"#N must be a standalone token (e.g., 'buffer~ #1' not "
                f"'buffer~ slot-#1'). Pass the full name as the bpatcher arg.",
            ))

    return results


def _check_unterminated_chains(
    box_lookup: dict[str, dict],
    has_signal_out: set[str],
    terminal_names=frozenset(),
) -> list[ValidationResult]:
    """Find MSP objects with signal outlets but no downstream signal connection.

    Exceptions: the chain terminals in *terminal_names* (from
    ``dsp_roles.chain_terminal_names(db)``: dac~, ezdac~, plugout~, send~,
    out~ and their mc.* variants; Q26 / E6), and objects that do have a
    downstream signal connection.
    """
    results: list[ValidationResult] = []

    for box_id, box in box_lookup.items():
        name = walk.box_name(box)

        # Only check MSP objects (name ends with ~)
        if not name.endswith("~"):
            continue

        # Skip terminal objects
        if name in terminal_names:
            continue

        # Check if this object has signal outlets
        outlettype = box.get("outlettype", [])
        has_signal_outlet = any(ot == "signal" for ot in outlettype)
        if not has_signal_outlet:
            continue

        # Check if it has any downstream signal connection
        if box_id in has_signal_out:
            continue

        results.append(ValidationResult(
            "domain", "warning",
            f"Unterminated signal chain: '{name}' ({box_id}) has signal "
            f"outlet(s) but no downstream signal connection",
        ))

    return results


def _check_gain_staging(
    box_lookup: dict[str, dict],
    signal_adj: dict[str, list[str]],
    gain_names=frozenset(),
    terminal_names=frozenset(),
) -> list[ValidationResult]:
    """Detect oscillators reaching an output terminal without gain.

    Uses BFS from each oscillator. If it reaches an output terminal in
    *terminal_names* without passing through a gain stage in *gain_names*,
    emit a warning. Both sets come from ``dsp_roles(db)`` (Q26 / E6): the
    gain stages include live.gain~ and the mc.* variants, the terminals
    mc.dac~ and plugout~.
    """
    results: list[ValidationResult] = []

    # Find all oscillator box ids
    osc_ids = []
    for box_id, box in box_lookup.items():
        name = walk.box_name(box)
        if name in _OSCILLATOR_NAMES:
            osc_ids.append(box_id)

    # For each oscillator, BFS to see if it reaches dac~/ezdac~ without gain
    for osc_id in osc_ids:
        osc_name = walk.box_name(box_lookup[osc_id])
        # BFS: track (current_id, passed_through_gain)
        from collections import deque
        queue = deque([(osc_id, False)])
        visited: set[tuple[str, bool]] = set()

        while queue:
            current_id, has_gain = queue.popleft()
            if (current_id, has_gain) in visited:
                continue
            visited.add((current_id, has_gain))

            for next_id in signal_adj.get(current_id, []):
                next_box = box_lookup.get(next_id)
                if not next_box:
                    continue
                next_name = walk.box_name(next_box)

                next_has_gain = has_gain or (next_name in gain_names)

                # Reached an output terminal
                if next_name in terminal_names:
                    if not next_has_gain:
                        results.append(ValidationResult(
                            "domain", "warning",
                            f"Missing gain staging: '{osc_name}' ({osc_id}) "
                            f"connected to '{next_name}' ({next_id}) without "
                            f"passing through a gain object (*~ or gain~)",
                        ))
                    # Don't continue past dac~
                    continue

                queue.append((next_id, next_has_gain))

    return results


def _check_unsafe_gain_values(
    box_lookup: dict[str, dict],
) -> list[ValidationResult]:
    """Detect *~ objects with literal gain arguments > 1.0.

    A *~ with a constant multiplier > 1.0 amplifies signal beyond unity gain,
    which is dangerous for audio output. Values <= 1.0 are safe.
    """
    results: list[ValidationResult] = []

    for box_id, box in box_lookup.items():
        name = walk.box_name(box)
        if name != "*~":
            continue

        args = walk.box_args(box)
        if not args:
            continue  # No argument -- skip

        arg_str = args[0]
        try:
            arg_val = float(arg_str)
        except ValueError:
            continue  # Not a number literal (could be a variable)

        if arg_val > 1.0:
            results.append(ValidationResult(
                "domain", "warning",
                f"Unsafe gain multiplier: '*~ {arg_str}' ({box_id}) has value "
                f"> 1.0 -- gain values should be 0.0-1.0 to prevent dangerous "
                f"audio levels",
            ))

    return results


def _check_feedback_loops(
    box_lookup: dict[str, dict],
    signal_adj: dict[str, list[str]],
) -> list[ValidationResult]:
    """Detect signal feedback loops without delay objects.

    Uses DFS cycle detection. If a cycle is found and none of its nodes are
    tapin~, tapout~, or gen~, emit a warning.
    """
    results: list[ValidationResult] = []

    # Standard DFS cycle detection with path tracking
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = defaultdict(int)  # default WHITE
    parent: dict[str, str | None] = {}
    cycles_found: list[list[str]] = []

    def dfs(node: str, path: list[str]) -> None:
        color[node] = GRAY
        path.append(node)

        for neighbor in signal_adj.get(node, []):
            if color[neighbor] == GRAY:
                # Found a back edge -- extract cycle
                cycle_start = path.index(neighbor)
                cycle = path[cycle_start:]
                cycles_found.append(list(cycle))
            elif color[neighbor] == WHITE:
                parent[neighbor] = node
                dfs(neighbor, path)

        path.pop()
        color[node] = BLACK

    # Run DFS from all nodes
    all_nodes = set(signal_adj.keys())
    for targets in signal_adj.values():
        all_nodes.update(targets)

    for node in all_nodes:
        if color[node] == WHITE:
            dfs(node, [])

    # Check each cycle for delay objects
    reported_cycles: set[frozenset[str]] = set()
    for cycle in cycles_found:
        cycle_key = frozenset(cycle)
        if cycle_key in reported_cycles:
            continue
        reported_cycles.add(cycle_key)

        # Check if cycle contains delay objects
        cycle_names = [walk.box_name(box_lookup[bid]) for bid in cycle if bid in box_lookup]
        has_delay = any(name in _DELAY_NAMES for name in cycle_names)

        if not has_delay:
            node_desc = ", ".join(
                f"{walk.box_name(box_lookup.get(bid, {}))} ({bid})"
                for bid in cycle
            )
            results.append(ValidationResult(
                "domain", "warning",
                f"Signal feedback loop without delay detected: {node_desc}",
            ))

    return results


# ===========================================================================
# Layer 4: GenExpr and API-usage checks
# ===========================================================================

def _check_genexpr_io_syntax(
    box_lookup: dict[str, dict],
) -> list[ValidationResult]:
    """Catch GenExpr codebox using 'in 1'/'out 2' instead of 'in1'/'out2'."""
    results: list[ValidationResult] = []

    for box_id, box in box_lookup.items():
        if box.get("maxclass") != "newobj":
            continue
        if not walk.box_text(box).startswith("codebox"):
            continue
        code = box.get("code", "")
        if not isinstance(code, str) or not code:
            continue
        if _re.search(r'\b(in|out)\s+\d', code):
            results.append(ValidationResult(
                "domain", "error",
                f"GenExpr codebox uses 'in1'/'out1' (no space), not "
                f"'in 1'/'out 1' ({box_id})",
            ))

    return results


def _check_genexpr_delay_usage(
    box_lookup: dict[str, dict],
) -> list[ValidationResult]:
    """Catch GenExpr codebox using delay() instead of Delay.read()/Delay.write()."""
    results: list[ValidationResult] = []

    for box_id, box in box_lookup.items():
        if box.get("maxclass") != "newobj":
            continue
        if not walk.box_text(box).startswith("codebox"):
            continue
        code = box.get("code", "")
        if not isinstance(code, str) or not code:
            continue
        if _re.search(r'\bdelay\s*\(', code):
            results.append(ValidationResult(
                "domain", "error",
                f"GenExpr uses Delay.read()/Delay.write(), not delay() "
                f"function ({box_id})",
            ))

    return results


def _check_gen_param_message_syntax(
    box_lookup: dict[str, dict],
    ctrl_adj: dict[str, list[str]],
) -> list[ValidationResult]:
    """Catch '@param $1' message syntax connected to gen~ (should be 'param $1')."""
    results: list[ValidationResult] = []

    for box_id, box in box_lookup.items():
        if box.get("maxclass") != "message":
            continue
        text = walk.box_text(box)
        if not _re.search(r'@\w+\s+\$', text):
            continue
        # Check if any downstream box is gen~
        for dst_id in ctrl_adj.get(box_id, []):
            dst_box = box_lookup.get(dst_id)
            if not dst_box:
                continue
            dst_name = walk.box_name(dst_box)
            if dst_name == "gen~":
                results.append(ValidationResult(
                    "domain", "warning",
                    f"gen~ params use plain name messages ('depth $1'), "
                    f"not '@depth $1' ({box_id})",
                ))
                break  # one warning per message box

    return results


def _check_comment_hash_substitution(
    box_lookup: dict[str, dict],
    ctrl_adj: dict[str, list[str]],
) -> list[ValidationResult]:
    """Warn about #N text in comment boxes (comment doesn't support substitution).

    A comment fed directly by a message box ``set ... #N`` is skipped (Q3,
    review §4.4 R3): that is the sanctioned loadbang -> message -> set chain,
    and the comment's stored text is just the pre-substitution placeholder.
    Only direct feeders count (no ``prepend set`` chains).
    """
    results: list[ValidationResult] = []

    set_fed: set[str] = set()
    for src_id, dst_ids in ctrl_adj.items():
        src_box = box_lookup.get(src_id)
        if not src_box or src_box.get("maxclass") != "message":
            continue
        src_text = walk.box_text(src_box)
        if _re.match(r'\s*set\s', src_text) and _re.search(r'#\d+', src_text):
            set_fed.update(dst_ids)

    for box_id, box in box_lookup.items():
        if box.get("maxclass") != "comment":
            continue
        if box_id in set_fed:
            continue
        text = walk.box_text(box)
        if _re.search(r'#\d+', text):
            results.append(ValidationResult(
                "domain", "warning",
                f"Comment boxes don't support #N substitution; use "
                f"loadbang -> message -> set chain ({box_id})",
            ))

    return results


def _check_line_tilde_comma_messages(
    box_lookup: dict[str, dict],
    ctrl_adj: dict[str, list[str]],
) -> list[ValidationResult]:
    """Catch messages with commas connected to line~ (commas restart ramps)."""
    results: list[ValidationResult] = []

    for box_id, box in box_lookup.items():
        if box.get("maxclass") != "message":
            continue
        text = walk.box_text(box)
        if "," not in text:
            continue
        # Check if any downstream box is line~
        for dst_id in ctrl_adj.get(box_id, []):
            dst_box = box_lookup.get(dst_id)
            if not dst_box:
                continue
            dst_name = walk.box_name(dst_box)
            if dst_name == "line~":
                results.append(ValidationResult(
                    "domain", "warning",
                    f"line~ replaces ramps on new messages; use single list "
                    f"without comma separators ({box_id})",
                ))
                break

    return results


def _check_multislider_fetchindex(
    box_lookup: dict[str, dict],
) -> list[ValidationResult]:
    """Catch messages using 'fetchindex' (doesn't exist; use 'fetch')."""
    results: list[ValidationResult] = []

    for box_id, box in box_lookup.items():
        if box.get("maxclass") != "message":
            continue
        text = walk.box_text(box)
        if "fetchindex" in text:
            results.append(ValidationResult(
                "domain", "error",
                f"multislider uses 'fetch' not 'fetchindex'; "
                f"fetchindex does not exist ({box_id})",
            ))

    return results


def _check_umenu_items_format(
    box_lookup: dict[str, dict],
) -> list[ValidationResult]:
    """Catch umenu items without comma separators."""
    results: list[ValidationResult] = []

    for box_id, box in box_lookup.items():
        # umenu can be a UI maxclass or newobj with text "umenu"
        if walk.box_name(box) != "umenu":
            continue
        items = box.get("items")
        if not isinstance(items, list):
            continue
        if len(items) <= 1:
            continue
        if "," not in items:
            results.append(ValidationResult(
                "domain", "warning",
                f"umenu items need comma separators: "
                f"['LP', ',', 'HP', ',', 'BP'] ({box_id})",
            ))

    return results


def _check_assistance_comments(
    box_lookup: dict[str, dict],
) -> list[ValidationResult]:
    """Flag inlet/outlet boxes missing assistance comment tooltips."""
    results: list[ValidationResult] = []

    for box_id, box in box_lookup.items():
        maxclass = box.get("maxclass", "")
        if maxclass not in ("inlet", "outlet"):
            continue
        comment = box.get("comment", "")
        if not comment:
            results.append(ValidationResult(
                "domain", "info",
                f"{maxclass} missing assistance comment (tooltip) ({box_id})",
            ))

    return results
