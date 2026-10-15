"""Critic system -- semantic/architectural review of generated patches.

Provides review_patch() which combines DSP, structure, layout, RNBO,
M4L, package, and external critics to catch design problems that the
mechanical validation pipeline does not detect.

Every patch critic reviews every scope (top level, ``p`` / bpatcher / poly~
/ gen~ / rnbo~ patchers) of one shared :class:`src.maxpat.graph.PatchGraph`,
built once per review_patch call (S1, Q20). Nested findings carry
``CriticResult.path`` (the box-id chain, ``obj-1/obj-2``) and a
``[p synth > gen~] `` finding prefix; top-level findings are unchanged.

Usage:
    from src.maxpat.critics import review_patch, CriticResult

    results = review_patch(patch_dict)
    for r in results:
        print(r)  # [severity] finding
"""

from __future__ import annotations

from src.maxpat.critics.base import CriticResult
from src.maxpat.critics.dsp_critic import review_dsp
from src.maxpat.critics.structure_critic import review_structure
from src.maxpat.critics.layout_critic import review_layout
from src.maxpat.critics.rnbo_critic import is_rnbo_box, review_rnbo
from src.maxpat.critics.m4l_critic import detect_m4l_device_type, review_m4l
from src.maxpat.critics.ext_critic import review_external
from src.maxpat.critics.package_critic import collect_packages_used, review_packages
from src.maxpat.graph import PatchGraph


def _has_rnbo_boxes(patch_dict: dict, graph: "PatchGraph | None" = None) -> bool:
    """Check if any scope of a patch contains an rnbo~ box (Q20).

    Detected by name via is_rnbo_box (Q4 / E3): MAX writes rnbo~ as
    ``newobj``, so the former maxclass test never matched a MAX-authored box.
    """
    if graph is None:
        graph = PatchGraph.build(patch_dict)
    for scope in graph.scopes:
        raw = scope.patcher.get("boxes")
        for entry in raw if isinstance(raw, list) else ():
            box = entry.get("box") if isinstance(entry, dict) else None
            if isinstance(box, dict) and is_rnbo_box(box):
                return True
    return False


def _has_package_boxes(patch_dict: dict, db=None, graph: "PatchGraph | None" = None) -> bool:
    """Check if any non-gen scope of a patch contains package objects (Q20).

    *db* is an ObjectDatabase; one is constructed only when it is None.
    """
    if db is None:
        from src.maxpat.db_lookup import ObjectDatabase
        db = ObjectDatabase()
    if graph is None:
        graph = PatchGraph.build(patch_dict)
    return bool(collect_packages_used(graph, db))


def review_patch(
    patch_dict: dict,
    code_context: dict | None = None,
    ext_code: str | None = None,
    ext_archetype: str = "message",
    *,
    db=None,
) -> list[CriticResult]:
    """Run all critics on a patch and return combined results.

    Combines DSP critic (signal flow, gen~ I/O, gain staging),
    structure critic (fan-out, hot/cold ordering, duplicates),
    RNBO critic (param naming, I/O completeness, duplicates),
    M4L critic (gain stages before plugout~, required objects, device
    quality, parameter uniqueness),
    package critic (BEAP conventions, Bach llll types, community extraction),
    and external critic (code structure, archetype requirements).

    Every patch critic reviews every scope of one shared PatchGraph built
    here (S1, Q20); nested findings are path-tagged (``CriticResult.path``
    and a ``[p synth] `` prefix). The RNBO critic is only invoked when an
    rnbo~ box is detected in any scope (by name, Q4 / E3). The M4L critic
    is only invoked when plugin~, plugout~ or live.thisdevice is present
    in any non-gen scope; the device type is inferred by
    detect_m4l_device_type (Q4 / D4). The package critic is only invoked
    when package objects (BEAP, Bach, community) are detected in any
    non-gen scope. The external critic is only invoked when ext_code is
    provided.

    Args:
        patch_dict: A .maxpat-format dict.
        code_context: Optional dict with code strings for gen~ boxes, etc.
            May also contain "rnbo_target" for RNBO target fitness checks.
        ext_code: Optional C++ source code string for external code review.
        ext_archetype: Archetype for external code review ("message", "dsp",
            "scheduler"). Only used when ext_code is provided.
        db: Keyword-only ObjectDatabase used for package detection and the
            package critic. None (default) constructs exactly one per call;
            the save gate passes one cached instance (Q7).

    One shared :class:`src.maxpat.graph.PatchGraph` is built per call and
    passed to the critics (S1, Q20).

    Returns:
        Combined list of CriticResult from all active critics.
    """
    if db is None:
        from src.maxpat.db_lookup import ObjectDatabase
        db = ObjectDatabase()
    graph = PatchGraph.build(patch_dict)

    results: list[CriticResult] = []
    results.extend(review_dsp(patch_dict, code_context=code_context, graph=graph))
    results.extend(review_structure(patch_dict, graph=graph))
    results.extend(review_layout(patch_dict, graph=graph))

    # RNBO critic: auto-invoke when rnbo~ boxes detected (any scope)
    if _has_rnbo_boxes(patch_dict, graph=graph):
        results.extend(review_rnbo(patch_dict, code_context=code_context, graph=graph))

    # M4L critic: auto-invoke when plugin~/plugout~/live.thisdevice detected
    m4l_device_type = detect_m4l_device_type(patch_dict, graph=graph)
    if m4l_device_type is not None:
        results.extend(review_m4l(patch_dict, device_type=m4l_device_type, graph=graph))

    # External critic: invoke when ext_code provided
    if ext_code is not None:
        results.extend(review_external(ext_code, archetype=ext_archetype))

    # Package critic: auto-invoke when package objects detected
    if _has_package_boxes(patch_dict, db=db, graph=graph):
        results.extend(review_packages(patch_dict, db=db, graph=graph))

    return results


__all__ = [
    "review_patch",
    "review_dsp",
    "review_structure",
    "review_layout",
    "review_rnbo",
    "review_m4l",
    "review_external",
    "review_packages",
    "CriticResult",
]
