"""RNBO critic -- semantic review of RNBO patches.

Catches RNBO-specific issues that the mechanical RNBO validation pipeline
does not detect:
  - Param naming conventions (lowercase_with_underscores preferred)
  - I/O completeness: a missing out~ is a blocker; a missing in~ is a note
    (Q26 / E8) -- a generator takes no audio input, and MAX's own
    rnbo_triangle~.maxhelp has none
  - Duplicate param names
  - Target fitness warnings (e.g., cpp with many params)

Param names (Q26 / E8): the ``@name`` value wins when present; otherwise the
first positional argument after ``param`` names it (``param freq 440``), unless
it starts with ``@`` or is a number. Both forms are checked for naming and
duplicates.

NOTE: Overlaps intentionally with rnbo_validation.py at the semantic level.
rnbo_validation checks structural correctness (is it valid?), while this
critic checks design quality (is it well-designed?).

rnbo~ boxes are detected by name via is_rnbo_box (Q4 / E3, quick 261012-egf):
MAX writes them as ``newobj`` (``rnbo~ @title ...``), so a maxclass gate
skipped every MAX-authored rnbo~.

rnbo~ boxes are found in every scope of the shared
:class:`src.maxpat.graph.PatchGraph` (Q20). Each one's findings are reported
at the path of the scope that holds the rnbo~ box (the Q19 Layer-5 rule).
Params are collected across the rnbo~ box's whole subtree; a param below the
rnbo~'s top inner patcher is referenced by its id chain from that patcher
(``obj-7/obj-3``), a param in the top inner patcher by its plain id.
"""

from __future__ import annotations

import re

from src.maxpat import walk
from src.maxpat.critics.base import CriticResult, finding_ids, tag_results
from src.maxpat.graph import PatchGraph
from src.maxpat.io_resolvers import split_box_text


# Regex for lowercase_with_underscores convention
_LOWERCASE_UNDERSCORE_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def is_rnbo_box(box: dict) -> bool:
    """True when ``box`` is an rnbo~ box, by name (Q4 / E3).

    Covers MAX's ``newobj`` shape (text ``rnbo~ ...``) and the builder's
    maxclass ``rnbo~`` shape, since walk.box_name returns the maxclass for
    non-newobj boxes. Shared by review_rnbo and review_patch's dispatch so
    the two agree on what counts as rnbo~.
    """
    return walk.box_name(box) == "rnbo~"


def _raw_boxes(patcher) -> list:
    """Box dicts of a patcher's boxes array (entries without a box skipped)."""
    raw = patcher.get("boxes") if isinstance(patcher, dict) else None
    out = []
    for entry in raw if isinstance(raw, list) else ():
        box = entry.get("box") if isinstance(entry, dict) else None
        if isinstance(box, dict):
            out.append(box)
    return out


def review_rnbo(
    patch_dict: dict,
    code_context: dict | None = None,
    *,
    graph: "PatchGraph | None" = None,
) -> list[CriticResult]:
    """Review RNBO aspects of a patch.

    Scans every scope for rnbo~ boxes and reviews their inner patchers
    for semantic issues: param naming, I/O completeness, duplicates,
    and target fitness. Params are named by ``@name`` or, failing that,
    their first positional argument (Q26 / E8). A missing out~ is a
    blocker; a missing in~ is a note, since a generator (MAX's own
    rnbo_triangle~ help) has no audio input.

    Args:
        patch_dict: A .maxpat-format dict.
        code_context: Optional dict. If it contains "rnbo_target", validates
            target-specific constraints.
        graph: The shared PatchGraph of *patch_dict* (review_patch passes
            it); built here when None.

    Returns:
        List of CriticResult findings.
    """
    if graph is None:
        graph = PatchGraph.build(patch_dict)
    results: list[CriticResult] = []

    for scope in graph.scopes:
        found: list[CriticResult] = []
        for box in _raw_boxes(scope.patcher):
            if not is_rnbo_box(box):
                continue

            inner_patcher = box.get("patcher")
            if not isinstance(inner_patcher, dict) or not inner_patcher:
                found.append(CriticResult(
                    "blocker",
                    f"rnbo~ box '{box.get('id', '?')}' has no inner patcher",
                    "Add an inner patcher with in~/out~ and param objects",
                    rule="rnbo_missing_inner_patcher",
                    box_ids=finding_ids(box.get("id")),
                ))
                continue

            inner_boxes = _raw_boxes(inner_patcher)
            params = _collect_params(graph, scope, box, inner_patcher)
            found.extend(_check_io_completeness(box, inner_boxes))
            found.extend(_check_param_naming(params))
            found.extend(_check_duplicate_params(params))

            # Target fitness check
            if isinstance(code_context, dict) and "rnbo_target" in code_context:
                target = code_context["rnbo_target"]
                found.extend(_check_target_fitness(params, target))
        results.extend(tag_results(found, scope.path))

    return results


def _collect_params(graph: PatchGraph, scope, rnbo_box: dict, inner_patcher: dict) -> list:
    """``(ref, box)`` for every ``param`` box in the rnbo~ box's subtree.

    Pre-order over ``graph.subtree``; *ref* is the plain id in the top
    inner patcher, else the id chain from it (``obj-7/obj-3``).
    """
    box_id = rnbo_box.get("id")
    subtree = graph.subtree(scope, box_id if box_id is not None else "?")
    if not subtree or subtree[0].patcher is not inner_patcher:
        layers = [("", inner_patcher)]
    else:
        root_key = subtree[0].key
        layers = []
        for s in subtree:
            rel = s.key[len(root_key) + 1:] if s is not subtree[0] else ""
            layers.append((rel, s.patcher))

    params = []
    for rel, patcher in layers:
        for box in _raw_boxes(patcher):
            if walk.box_name(box) != "param":
                continue
            pid = box.get("id", "?")
            ref = f"{rel}/{pid}" if rel else pid
            params.append((ref, box))
    return params


def _check_io_completeness(
    rnbo_box: dict,
    inner_boxes: list[dict],
) -> list[CriticResult]:
    """Check the inner RNBO patcher for in~ and out~.

    No out~ is a blocker (no audio output) unless the patcher has an event
    output (``_RNBO_EVENT_OUTPUTS``: midiout, noteout, ctlout, ..., outport,
    out): a MIDI-only or event-only RNBO patch then gets a note (Q26
    follow-up, quick 261022-ud6). No in~ is a note (Q26 / E8): a generator
    takes no audio input by design.
    """
    results: list[CriticResult] = []

    has_in = False
    has_out = False
    has_event_out = False

    for box in inner_boxes:
        name = walk.box_name(box)
        if name == "in~":
            has_in = True
        elif name == "out~":
            has_out = True
        elif name in _RNBO_EVENT_OUTPUTS:
            has_event_out = True

    rnbo_id = rnbo_box.get("id", "?")

    if not has_in:
        results.append(CriticResult(
            "note",
            f"rnbo~ '{rnbo_id}' inner patcher has no in~ object -- "
            f"it takes no audio input, which is expected for a generator",
            "If the patch should process audio input, add an 'in~ 1' object "
            "to the inner RNBO patcher",
            rule="io_completeness",
            box_ids=finding_ids(rnbo_id),
        ))

    if not has_out and has_event_out:
        results.append(CriticResult(
            "note",
            f"rnbo~ '{rnbo_id}' inner patcher has no out~ object -- "
            f"it outputs events only (MIDI / outport / out), which is "
            f"expected for a MIDI or control generator",
            "If the patch should also output audio, add an 'out~ 1' object "
            "to the inner RNBO patcher",
            rule="io_completeness",
            box_ids=finding_ids(rnbo_id),
        ))
    elif not has_out:
        results.append(CriticResult(
            "blocker",
            f"rnbo~ '{rnbo_id}' inner patcher has no out~ object -- "
            f"audio output will not work",
            "Add at least one 'out~' object to the inner RNBO patcher",
            rule="io_completeness",
            box_ids=finding_ids(rnbo_id),
        ))

    return results


# RNBO objects that send events out of the rnbo~ patcher (no audio): MIDI
# outputs, outport and the control-rate ``out`` (Q26 follow-up).
_RNBO_EVENT_OUTPUTS = frozenset({
    "midiout", "noteout", "ctlout", "bendout", "pgmout", "touchout",
    "outport", "out",
})


_NUMBER_RE = re.compile(r"^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$")


def _is_number(token: str) -> bool:
    """True for a MAX numeric atom (``5``, ``-3``, ``0.5``, ``1e3``)."""
    return bool(_NUMBER_RE.match(token))


def _extract_param_name(text) -> str | None:
    """The param name of box text ``param ...`` (Q26 / E8), or None.

    The ``@name`` value wins when present (``param @name foo @min 0``).
    Otherwise the first argument after ``param`` names it
    (``param freq 440``) unless it starts with ``@`` or parses as a
    number. Non-str text gives None. Tokens come from the quote-aware
    ``split_box_text``.
    """
    if not isinstance(text, str):
        return None
    tokens = split_box_text(text)
    for i, tok in enumerate(tokens[:-1]):
        if tok == "@name":
            return tokens[i + 1]
    if len(tokens) < 2 or tokens[0] != "param":
        return None
    first = tokens[1]
    if first.startswith("@") or _is_number(first):
        return None
    return first


def _check_param_naming(
    params: list,
) -> list[CriticResult]:
    """Check that param names follow lowercase_with_underscores convention.

    *params* is ``(ref, box)`` pairs from :func:`_collect_params`.
    """
    results: list[CriticResult] = []

    for _ref, box in params:
        text = walk.box_text(box)
        param_name = _extract_param_name(text)
        if param_name is None:
            continue

        if not _LOWERCASE_UNDERSCORE_RE.match(param_name):
            results.append(CriticResult(
                "warning",
                f"RNBO param '{param_name}' does not follow "
                f"lowercase_with_underscores naming convention",
                f"Rename to '{_to_snake_case(param_name)}' for consistency "
                f"with RNBO parameter naming best practices",
                rule="param_naming",
                box_ids=finding_ids(box.get("id")),
            ))

    return results


def _to_snake_case(name: str) -> str:
    """Convert PascalCase or camelCase to snake_case."""
    # Insert underscore before uppercase letters
    s1 = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    s2 = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1)
    return s2.lower()


def _check_duplicate_params(
    params: list,
) -> list[CriticResult]:
    """Check for duplicate param names across the rnbo~ subtree.

    *params* is ``(ref, box)`` pairs from :func:`_collect_params`.
    """
    results: list[CriticResult] = []
    seen_names: dict[str, str] = {}  # name -> first box ref

    for box_id, box in params:
        text = walk.box_text(box)
        param_name = _extract_param_name(text)
        if param_name is None:
            continue

        if param_name in seen_names:
            results.append(CriticResult(
                "blocker",
                f"Duplicate RNBO param name '{param_name}' in boxes "
                f"'{seen_names[param_name]}' and '{box_id}'",
                f"Each RNBO param must have a unique @name -- "
                f"rename one of the duplicate '{param_name}' params",
                rule="duplicate_params",
                box_ids=finding_ids(*seen_names[param_name].split("/"), *box_id.split("/")),
            ))
        else:
            seen_names[param_name] = box_id

    return results


def _check_target_fitness(
    params: list,
    target: str,
) -> list[CriticResult]:
    """Check target-specific fitness issues.

    For 'cpp' target: warn if many params (>128 practical limit).
    *params* is ``(ref, box)`` pairs across the rnbo~ subtree.
    """
    results: list[CriticResult] = []

    param_count = len(params)

    if target == "cpp" and param_count > 128:
        results.append(CriticResult(
            "warning",
            f"C++ embedded target has a practical limit of 128 params "
            f"(MIDI CC count), but patch has {param_count} params",
            "Reduce the number of params or use a different export target",
            rule="target_fitness",
        ))

    return results
