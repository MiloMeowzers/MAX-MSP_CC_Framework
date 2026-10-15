"""Critic system -- semantic/architectural review of generated patches.

Provides review_patch() which combines DSP, structure, layout, RNBO,
M4L, package, and external critics to catch design problems that the
mechanical validation pipeline does not detect.

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
from src.maxpat.critics.package_critic import review_packages
from src.maxpat.graph import PatchGraph
from src.maxpat.utils import get_box_name


def _has_rnbo_boxes(patch_dict: dict) -> bool:
    """Check if a patch contains any top-level rnbo~ boxes.

    Detected by name via is_rnbo_box (Q4 / E3): MAX writes rnbo~ as
    ``newobj``, so the former maxclass test never matched a MAX-authored box.
    """
    patcher = patch_dict.get("patcher", {})
    boxes = patcher.get("boxes", [])
    for box_entry in boxes:
        box = box_entry.get("box", {})
        if is_rnbo_box(box):
            return True
    return False


def _has_package_boxes(patch_dict: dict, db=None) -> bool:
    """Check if a patch contains any package objects.

    *db* is an ObjectDatabase; one is constructed only when it is None.
    """
    if db is None:
        from src.maxpat.db_lookup import ObjectDatabase
        db = ObjectDatabase()
    patcher = patch_dict.get("patcher", {})
    for box_entry in patcher.get("boxes", []):
        box = box_entry.get("box", {})
        # Handle bpatchers (BEAP, Vizzie) via name attribute
        if box.get("maxclass") == "bpatcher":
            name = box.get("name", "")
        else:
            name = get_box_name(box)
        if name and db.get_package(name):
            return True
    return False


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

    The RNBO critic is only invoked when rnbo~ boxes are detected
    in the patch (by name, Q4 / E3). The M4L critic is only invoked when
    plugin~, plugout~ or live.thisdevice is present; the device type is
    inferred by detect_m4l_device_type (Q4 / D4). The package critic is only invoked when package
    objects (BEAP, Bach, community) are detected. The external critic
    is only invoked when ext_code is provided.

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
    results.extend(review_dsp(patch_dict, code_context=code_context))
    results.extend(review_structure(patch_dict, graph=graph))
    results.extend(review_layout(patch_dict))

    # RNBO critic: auto-invoke when rnbo~ boxes detected
    if _has_rnbo_boxes(patch_dict):
        results.extend(review_rnbo(patch_dict, code_context=code_context))

    # M4L critic: auto-invoke when plugin~/plugout~/live.thisdevice detected
    m4l_device_type = detect_m4l_device_type(patch_dict)
    if m4l_device_type is not None:
        results.extend(review_m4l(patch_dict, device_type=m4l_device_type))

    # External critic: invoke when ext_code provided
    if ext_code is not None:
        results.extend(review_external(ext_code, archetype=ext_archetype))

    # Package critic: auto-invoke when package objects detected
    if _has_package_boxes(patch_dict, db=db):
        results.extend(review_packages(patch_dict, db=db))

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
