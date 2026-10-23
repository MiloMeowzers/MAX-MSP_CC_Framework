"""Apply critic quick-fix payloads to a Patcher (fix-plan Q39, review §5.6 item 7).

Flow (``/max-iterate --fix``)::

    from src.maxpat import edit_patch, fixable_findings, preview_quick_fixes, apply_quick_fixes

    patcher, _ = read_patch(path)
    candidates = fixable_findings(patcher)            # 1. list
    selected = [...]                                  #    the user picks
    print(preview_quick_fixes(path, selected).render())  # 2. preview, writes nothing
    session = edit_patch(path)                        # 3. apply + save in ONE session
    with session as p:
        apply_quick_fixes(p, selected)
    print(session.diff.render())

A finding is selected by its key ``(rule, box_ids, port, path)`` -- the same
identity tests/review_blocker_allowlist.json uses (:func:`finding_key`) --
or by the CriticResult itself. The save gate's own blocker key is
``hooks._finding_key``; it is not guaranteed to equal this one (a finding
reworded without a rule change is new to a text-keyed gate but not to this
selection; review-validation IN-01).

This module never saves, writes or commits: saving is the edit_patch
session's job (stale check, save gate, atomic write, path-scoped commit,
fix-plan Q36), and the gate is never bypassed here. The preview is a
separate read because a with-block cannot span the user's confirmation;
:func:`apply_quick_fixes` re-runs review_patch on the session's fresh read
before each key, so a MAX save between preview and apply surfaces as a
:class:`FixError` (the finding or its payload changed) or as the session's
StaleFileError.

Every op of a payload is validated against the current scope before any
mutation (op/kind contract, add_box name allowlist, boxes and cords exist,
ports in range, set_text ``old_text`` equals the box text, the scope path
resolves to one Patcher); a failed fix raises FixError and leaves the
patcher untouched.
"""

from __future__ import annotations

import copy
import json

from src.maxpat.critics.fixes import (
    ADDABLE_NAMES,
    check_fix_contract,
    is_new_ref,
)


class FixError(ValueError):
    """A quick fix cannot be applied (missing finding, stale or invalid payload)."""


def finding_key(result) -> tuple:
    """``(rule, box_ids, port, path)`` of a CriticResult or (since quick
    261022-ud6 WP1) a ValidationResult; a 4-tuple passes through."""
    if isinstance(result, tuple):
        if len(result) != 4:
            raise FixError(f"a finding key is (rule, box_ids, port, path), got {result!r}")
        rule, box_ids, port, path = result
        return (rule, tuple(box_ids), port, path)
    return (result.rule, tuple(result.box_ids), result.port, result.path)


def _db_or_new(db):
    if db is None:
        from src.maxpat.db_lookup import ObjectDatabase

        db = ObjectDatabase()
    return db


def _review(patch_dict: dict, db) -> list:
    from src.maxpat.critics import review_patch

    return review_patch(patch_dict, db=db)


def fixable_findings(patch, *, db=None) -> list:
    """The review findings of *patch* that carry a fix, in review order, first per key.

    *patch* is a Patcher or a .maxpat dict; review_patch runs on a deepcopy,
    so the input is never mutated.
    """
    from src.maxpat.patcher import Patcher

    d = patch.to_dict() if isinstance(patch, Patcher) else copy.deepcopy(patch)
    out: list = []
    seen: set = set()
    for r in _review(d, _db_or_new(db)):
        if getattr(r, "fix", None) is None:
            continue
        key = finding_key(r)
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def _resolve_scope(patcher, path: str):
    from src.maxpat.patcher import Patcher
    from src.maxpat.validation import _patcher_scope_map

    if path == "":
        return patcher
    targets = _patcher_scope_map(patcher).get(path, [])
    if len(targets) != 1 or not isinstance(targets[0], Patcher):
        raise FixError(f"scope path {path!r} names no single editable patcher")
    return targets[0]


def _box_counts(scope, name: str, args: list) -> tuple[int, int]:
    db = getattr(scope, "db", None)
    if db is None:
        raise FixError("the patcher has no object database to size a new box")
    try:
        return db.compute_io_counts(name, args)
    except Exception as exc:  # pragma: no cover - defensive
        raise FixError(f"cannot size new box {name!r}: {exc}") from exc


def _check_ops(scope, fix) -> None:
    """Validate every op of *fix* against *scope*; raise FixError, mutate nothing."""
    boxes = {b.id: b for b in scope.boxes}
    cords = {(pl.source_id, pl.source_outlet, pl.dest_id, pl.dest_inlet) for pl in scope.lines}
    new_io: dict[str, tuple[int, int]] = {}

    for op in fix.ops:
        if op.op != "add_box":
            continue
        tokens = (op.text or "").split()
        if not tokens or tokens[0] not in ADDABLE_NAMES:
            raise FixError(f"add_box name {tokens[:1]!r} is not one of {sorted(ADDABLE_NAMES)}")
        if op.near is not None and op.near not in boxes:
            raise FixError(f"add_box near box {op.near!r} not found")
        new_io[op.box] = _box_counts(scope, tokens[0], tokens[1:])

    def io(box_id):
        if is_new_ref(box_id):
            if box_id not in new_io:
                raise FixError(f"undeclared placeholder {box_id!r}")
            return new_io[box_id]
        box = boxes.get(box_id)
        if box is None:
            raise FixError(f"box {box_id!r} not found in scope")
        return box.numinlets, box.numoutlets

    removed: set = set()
    for op in fix.ops:
        if op.op in ("remove_cord", "add_cord"):
            n_out = io(op.src)[1]
            n_in = io(op.dst)[0]
            if not (0 <= op.outlet < n_out) or not (0 <= op.inlet < n_in):
                raise FixError(
                    f"{op.op} {op.src}:{op.outlet} -> {op.dst}:{op.inlet} is out of range"
                )
            key = (op.src, op.outlet, op.dst, op.inlet)
            if op.op == "remove_cord":
                if key not in cords or key in removed:
                    raise FixError(f"cord {op.src}:{op.outlet} -> {op.dst}:{op.inlet} not found")
                removed.add(key)
        elif op.op == "set_text":
            box = boxes.get(op.box)
            if box is None:
                raise FixError(f"box {op.box!r} not found in scope")
            if (box.text or "") != op.old_text:
                raise FixError(
                    f"box {op.box} text is {box.text!r}, payload expected {op.old_text!r}"
                )
            if " ".join(op.text.split()) != op.text:
                raise FixError(f"set_text text {op.text!r} is not single-spaced")
            if fix.kind == "rewrite_gen_param":
                if box.maxclass != "message":
                    raise FixError(f"rewrite_gen_param targets a {box.maxclass}, not a message box")
            elif fix.kind == "set_bach_out":
                _check_bach_box(scope, box, op.text)
            else:  # pragma: no cover - contract forbids it
                raise FixError(f"{fix.kind} takes no set_text")


def _check_bach_box(scope, box, text: str) -> None:
    if box.maxclass != "newobj":
        raise FixError(f"set_bach_out targets a {box.maxclass}, not an object box")
    db = getattr(scope, "db", None)
    entry = db.lookup(box.name) if db is not None else None
    if not isinstance(entry, dict) or entry.get("package") != "Bach":
        raise FixError(f"set_bach_out targets {box.name!r}, not a Bach object")
    tokens = text.split()
    if not tokens or tokens[0] != box.name:
        raise FixError(f"set_bach_out text {text!r} must start with {box.name!r}")
    if not scope._io_is_content_defined(box):
        counts = db.compute_io_counts(box.name, tokens[1:])
        if tuple(counts) != (box.numinlets, box.numoutlets):
            raise FixError(f"set_bach_out would change the I/O of {box.id}")


def apply_fix(patcher, result) -> list:
    """Apply *result*.fix in the scope named by *result*.path; return the new Boxes.

    Raises FixError (patcher untouched) when the result has no fix, the path
    names no single Patcher, the payload breaks its kind's contract, or any
    op does not fit the current scope.
    """
    fix = getattr(result, "fix", None)
    if fix is None:
        raise FixError("the finding carries no fix")
    scope = _resolve_scope(patcher, getattr(result, "path", "") or "")
    try:
        check_fix_contract(fix)
    except ValueError as exc:
        raise FixError(str(exc)) from exc
    _check_ops(scope, fix)

    saved_boxes = list(scope.boxes)
    saved_lines = list(scope.lines)
    boxes = {b.id: b for b in scope.boxes}
    created: list = []
    refs: dict = {}
    try:
        for op in fix.ops:
            if op.op == "add_box":
                tokens = op.text.split()
                box = scope.add_box(tokens[0], tokens[1:], skip_overlap_check=True)
                scope._auto_position(box, near_box=boxes.get(op.near))
                refs[op.box] = box
                created.append(box)
            elif op.op == "remove_cord":
                scope.remove_connection(boxes[op.src], op.outlet, boxes[op.dst], op.inlet)
            elif op.op == "add_cord":
                src = refs[op.src] if is_new_ref(op.src) else boxes[op.src]
                dst = refs[op.dst] if is_new_ref(op.dst) else boxes[op.dst]
                scope.add_connection(src, op.outlet, dst, op.inlet)
            elif op.op == "set_text":
                box = boxes[op.box]
                tokens = op.text.split()
                args = tokens if box.maxclass == "message" else tokens[1:]
                scope.modify_box(box, args=args)
                if box.text != op.text:
                    raise FixError(f"box {box.id} text became {box.text!r}, not {op.text!r}")
    except FixError:
        scope.boxes[:] = saved_boxes
        scope.lines[:] = saved_lines
        raise
    except Exception as exc:
        scope.boxes[:] = saved_boxes
        scope.lines[:] = saved_lines
        raise FixError(f"applying {fix.kind} failed: {exc}") from exc
    return created


def apply_quick_fixes(patcher, selection, *, db=None) -> list:
    """Apply the fixes of the selected findings to *patcher*, in selection order.

    *selection* holds finding keys (:func:`finding_key`) or CriticResults.
    Before each key, review_patch re-runs on ``patcher.to_dict()`` and the
    current result with that key and a fix is applied; none -> FixError
    naming the key. Fixes applied before the failing key stay applied (use
    inside ``edit_patch``, where the exception discards the whole edit).
    Returns the applied CriticResults.
    """
    db = _db_or_new(db)
    keys = [finding_key(item) for item in selection]
    applied: list = []
    for key in keys:
        match = None
        for r in _review(patcher.to_dict(), db):
            if getattr(r, "fix", None) is not None and finding_key(r) == key:
                match = r
                break
        if match is None:
            raise FixError(f"no fixable finding with key {key!r} in the current patch")
        apply_fix(patcher, match)
        applied.append(match)
    return applied


def preview_quick_fixes(path, selection, *, db=None):
    """The PatchDiff the selected fixes would make to the file at *path*.

    Reads the file, applies the fixes in memory and diffs against the file
    as read. Writes and commits nothing.
    """
    from src.maxpat.hooks import read_patch
    from src.maxpat.patch_diff import diff_patch_dicts

    patcher, original_text = read_patch(path)
    apply_quick_fixes(patcher, selection, db=db)
    return diff_patch_dicts(json.loads(original_text), patcher.to_dict())


__all__ = [
    "FixError",
    "finding_key",
    "fixable_findings",
    "apply_fix",
    "apply_quick_fixes",
    "preview_quick_fixes",
]
