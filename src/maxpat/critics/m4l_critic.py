"""M4L critic -- semantic review of Max for Live devices.

Catches M4L-specific issues that the mechanical validation pipeline
does not detect:
  - gain~ / live.gain~ on any signal path to plugout~, and any ezdac~
    (Live's channel strip handles output and volume)
  - Missing required objects per device type (audio_effect / instrument
    need plugout~; midi_effect needs midiin + midiout; live.thisdevice is
    not required)
  - Duplicate parameter_longname across device (including subpatchers)
  - Device quality: openinpresentation, devicewidth, parameter_enable on
    parameter-capable live.* controls (LIVE_PARAMETER_OBJECTS; review D5)
  - Missing info text (annotation) on parameter controls
  - Missing live.banks for Push controller bank organization

review_patch invokes this critic via detect_m4l_device_type when any
non-gen scope contains plugin~, plugout~ or live.thisdevice (Q4 / D4, quick
261012-egf; Q20).

Scopes (Q20): device-level checks (completeness, openinpresentation /
devicewidth on the top patcher, parameter_longname uniqueness across all
scopes, live.banks against parameter controls in any scope) run once and are
reported at the top level. Per-scope checks (gain stage on a scope-local
signal path to plugout~, ezdac~, parameter_enable, empty longname, missing
info text) run on every non-gen scope of the shared
:class:`src.maxpat.graph.PatchGraph`; nested findings carry
``CriticResult.path`` and a ``[p synth] `` prefix.
"""

from __future__ import annotations

from collections import deque

from src.maxpat import walk
from src.maxpat.critics.base import CriticResult, tag_results
from src.maxpat.graph import PatchGraph, outlet_is_signal


# Required objects per M4L device type (Q4 / D4). Instruments take MIDI from
# Live's track without midiin/midiout (notein etc. work), and live.thisdevice
# is not required by any device type (OQ2-A): the framework's own
# add_m4l_gen_synth and the user-confirmed kicksynth-m4l device omit it.
_REQUIRED_OBJECTS = {
    "audio_effect": {"plugout~"},
    "instrument": {"plugout~"},
    "midi_effect": {"midiin", "midiout"},
}

# Gain stages that must not sit on a signal path to plugout~ (Q4 / D4).
_M4L_GAIN_STAGE_NAMES = frozenset({"gain~", "live.gain~"})

# Top-level box names that mark a patch as an M4L device (Q4 / D4).
_M4L_MARKER_NAMES = frozenset({"plugin~", "plugout~", "live.thisdevice"})

# Parameter-capable live.* classes (review D5, Q15): exactly the live.*
# refpages in Max 9.2.0 m4l-ref that carry a <parameter /> element (name read
# from <c74object name>, never the filename). Pinned by
# tests/test_m4l_polish.py::TestParameterCapableSet::test_set_matches_refpages
# (requires_max). live.comment, live.line, live.meter~, live.banks,
# live.thisdevice, live.observer etc. carry none. mc.live.gain~ also carries
# <parameter /> but sits outside the "live." prefix scans that use this set.
LIVE_PARAMETER_OBJECTS = frozenset({
    "live.arrows", "live.button", "live.dial", "live.drop", "live.gain~",
    "live.grid", "live.menu", "live.numbox", "live.slider", "live.step",
    "live.tab", "live.text", "live.toggle",
})


def _scope_boxes(scope) -> list:
    """Box dicts of a scope's raw boxes array (bare boxes accepted)."""
    raw = scope.patcher.get("boxes")
    out = []
    for entry in raw if isinstance(raw, list) else ():
        if not isinstance(entry, dict):
            continue
        box = entry.get("box", entry)
        if isinstance(box, dict):
            out.append(box)
    return out


def _device_scopes(graph: PatchGraph) -> list:
    """Every non-gen scope (GenExpr operators are not Max objects)."""
    return [s for s in graph.scopes if s.context != "gen"]


def detect_m4l_device_type(
    patch_dict: dict, *, graph: "PatchGraph | None" = None
) -> str | None:
    """Infer the M4L device type from a patch's boxes (Q4 / D4; Q20).

    Returns None unless some non-gen scope contains plugin~, plugout~ or
    live.thisdevice (newobj or maxclass). Then plugin~ -> "audio_effect",
    else plugout~ -> "instrument", else "midi_effect".
    """
    if graph is None:
        graph = PatchGraph.build(patch_dict)
    names = _present_names(graph)

    if not names & _M4L_MARKER_NAMES:
        return None
    if "plugin~" in names:
        return "audio_effect"
    if "plugout~" in names:
        return "instrument"
    return "midi_effect"


def _present_names(graph: PatchGraph) -> set:
    """Object names in every non-gen scope."""
    names: set[str] = set()
    for scope in _device_scopes(graph):
        for box in _scope_boxes(scope):
            name = walk.box_name(box)
            if name:
                names.add(name)
    return names


def review_m4l(
    patch_dict: dict,
    device_type: str | None = None,
    *,
    graph: "PatchGraph | None" = None,
) -> list[CriticResult]:
    """Review M4L aspects of a patch.

    Args:
        patch_dict: A .maxpat-format dict.
        device_type: One of "audio_effect", "instrument", "midi_effect".
            If None, returns empty list (caller should detect type).
        graph: The shared PatchGraph of *patch_dict* (review_patch passes
            it); built here when None.

    Returns:
        List of CriticResult findings: the top level (gain/ezdac,
        completeness, uniqueness, quality, info text, live.banks) first,
        then nested per-scope findings in pre-order.
    """
    if device_type is None:
        return []
    if graph is None:
        graph = PatchGraph.build(patch_dict)

    results: list[CriticResult] = []
    top = graph.top
    scopes = _device_scopes(graph)
    top_is_device = top.context != "gen"
    all_params = _collect_parameter_longnames(graph)

    if top_is_device:
        results.extend(_check_gain_plugout(top))
    results.extend(_check_device_completeness(_present_names(graph), device_type))
    if top_is_device:
        results.extend(_check_empty_longnames(top))
    results.extend(_check_parameter_uniqueness(all_params))
    results.extend(_check_device_quality(top.patcher, _scope_boxes(top) if top_is_device else []))
    if top_is_device:
        results.extend(_check_missing_info_text(_scope_boxes(top)))
    results.extend(_check_missing_live_banks([b for s in scopes for b in _scope_boxes(s)]))

    for scope in scopes:
        if scope is top:
            continue
        boxes = _scope_boxes(scope)
        found: list[CriticResult] = []
        found.extend(_check_gain_plugout(scope))
        found.extend(_check_empty_longnames(scope))
        found.extend(_check_parameter_enable(boxes))
        found.extend(_check_missing_info_text(boxes))
        results.extend(tag_results(found, scope.path))

    return results


# ---------------------------------------------------------------------------
# Check 1: gain stages on a signal path to plugout~, and ezdac~
# ---------------------------------------------------------------------------

def _check_gain_plugout(scope) -> list[CriticResult]:
    """Flag gain stages upstream of plugout~ and any ezdac~ in *scope*.

    In M4L devices, Ableton's channel strip handles volume, so a gain~ or
    live.gain~ before plugout~ is redundant and (gain~ defaults to 0) can
    silence the device. Q4 / D4: every gain stage on *any* signal path to a
    plugout~ (direct or through other boxes) is exactly one blocker per
    (stage, plugout~) pair. Only cords whose source outlet carries audio
    (graph.outlet_is_signal, via ``edge.signal``) count as a path, so control
    cords do not. ezdac~ has no outlets, so it can never be upstream of
    plugout~; any ezdac~ in a device is a blocker instead (OQ3-A).

    The path is scope-local: subpatcher ports and send~/receive~ pairs are
    not followed (Q20 keeps critic checks scope-local).
    """
    results: list[CriticResult] = []

    box_lookup = scope.boxes
    order = [b.get("id") for b in scope.box_list]

    # Reverse signal graph: destination id -> source ids
    rev: dict[str, list[str]] = {}
    for edge in scope.edges:
        if edge.src not in box_lookup or edge.dst not in box_lookup:
            continue
        if not edge.signal:
            continue
        rev.setdefault(edge.dst, []).append(edge.src)

    pairs: set[tuple[str, str]] = set()
    for plugout_id in order:
        if walk.box_name(box_lookup[plugout_id]) != "plugout~":
            continue
        visited = {plugout_id}
        queue = deque([plugout_id])
        while queue:
            node = queue.popleft()
            for src_id in rev.get(node, []):
                if src_id in visited:
                    continue
                visited.add(src_id)
                queue.append(src_id)
                if walk.box_name(box_lookup[src_id]) in _M4L_GAIN_STAGE_NAMES:
                    pairs.add((plugout_id, src_id))

    for plugout_id, stage_id in sorted(pairs):
        name = walk.box_name(box_lookup[stage_id])
        results.append(CriticResult(
            "blocker",
            f"{name} ({stage_id}) is on the signal path to plugout~ "
            f"({plugout_id}) -- Ableton's channel strip handles volume, so "
            f"a gain stage before plugout~ is redundant and can silence the "
            f"device",
            f"Remove {name} and route the final processing stage directly "
            f"to plugout~",
        ))

    for box_id in order:
        if walk.box_name(box_lookup[box_id]) == "ezdac~":
            results.append(CriticResult(
                "blocker",
                f"ezdac~ ({box_id}) in an M4L device -- Live's channel strip "
                f"handles output and volume; route the final processing "
                f"stage to plugout~",
                "Remove ezdac~ and connect the final processing stage to "
                "plugout~",
            ))

    return results


# ---------------------------------------------------------------------------
# Check 2: Device completeness
# ---------------------------------------------------------------------------

def _check_device_completeness(
    present_names: set,
    device_type: str,
) -> list[CriticResult]:
    """Check that all required objects are present for the device type.

    *present_names* is every object name in any non-gen scope (Q20).
    """
    results: list[CriticResult] = []

    required = _REQUIRED_OBJECTS.get(device_type)
    if not required:
        return results

    for obj_name in sorted(required):
        if obj_name not in present_names:
            results.append(CriticResult(
                "blocker",
                f"M4L {device_type} missing required object: {obj_name}",
                f"Add {obj_name} to the device",
            ))

    return results


# ---------------------------------------------------------------------------
# Check 3: Parameter longname uniqueness
# ---------------------------------------------------------------------------

def _box_longname(box: dict):
    """``parameter_longname`` from saved_attribute_attributes.valueof, or None."""
    saa = box.get("saved_attribute_attributes")
    if not isinstance(saa, dict):
        return None
    valueof = saa.get("valueof")
    if not isinstance(valueof, dict):
        return None
    longname = valueof.get("parameter_longname")
    return longname if isinstance(longname, str) else None


def _scope_longnames(scope) -> list:
    """``(longname, box_id, status)`` for one scope's boxes.

    status is "ok" for non-empty longnames, "empty" for empty/blank.
    """
    found = []
    for box in _scope_boxes(scope):
        longname = _box_longname(box)
        if longname is None:
            continue
        box_id = box.get("id", "?")
        found.append((longname, box_id, "empty" if not longname.strip() else "ok"))
    return found


def _collect_parameter_longnames(graph: PatchGraph) -> list:
    """``(longname, ref, status)`` across every non-gen scope, pre-order.

    *ref* is the plain box id at the top level, ``<scope key>/<id>`` in a
    nested scope (Q20).
    """
    results = []
    for scope in _device_scopes(graph):
        for longname, box_id, status in _scope_longnames(scope):
            ref = f"{scope.key}/{box_id}" if scope.key else box_id
            results.append((longname, ref, status))
    return results


def _check_empty_longnames(scope) -> list[CriticResult]:
    """Warn about parameters with an empty longname in *scope*."""
    results: list[CriticResult] = []
    for _longname, box_id, status in _scope_longnames(scope):
        if status == "empty":
            results.append(CriticResult(
                "warning",
                f"Parameter in box '{box_id}' has empty longname -- "
                f"parameter_enable is set but no explicit parameter_longname",
                "Set a descriptive parameter_longname for the control",
            ))
    return results


def _check_parameter_uniqueness(
    all_params: list,
) -> list[CriticResult]:
    """Check for duplicate parameter_longname across the entire device."""
    results: list[CriticResult] = []

    # Check for duplicates among non-empty longnames
    seen: dict[str, str] = {}  # longname -> first box ref
    for longname, box_id, status in all_params:
        if status != "ok":
            continue
        if longname in seen:
            results.append(CriticResult(
                "blocker",
                f"Duplicate parameter_longname '{longname}' in boxes "
                f"'{seen[longname]}' and '{box_id}' -- each parameter must "
                f"have a unique longname",
                f"Rename one of the duplicate '{longname}' parameters",
            ))
        else:
            seen[longname] = box_id

    return results


# ---------------------------------------------------------------------------
# Check 4: Device quality
# ---------------------------------------------------------------------------

def _check_device_quality(
    patcher: dict,
    boxes: list[dict],
) -> list[CriticResult]:
    """Check M4L device quality: presentation mode, width, parameter_enable."""
    results: list[CriticResult] = []

    # Check patcher-level properties
    if not patcher.get("openinpresentation"):
        results.append(CriticResult(
            "warning",
            "M4L device missing openinpresentation=1 -- device UI will not "
            "display in Ableton",
            "Set openinpresentation=1 on the patcher",
        ))

    if not patcher.get("devicewidth"):
        results.append(CriticResult(
            "warning",
            "M4L device missing devicewidth -- Ableton will use default width",
            "Set devicewidth to control device width in Ableton (e.g., 300.0)",
        ))

    results.extend(_check_parameter_enable(boxes))
    return results


def _check_parameter_enable(boxes: list) -> list[CriticResult]:
    """Parameter-capable live.* controls without parameter_enable (one scope)."""
    results: list[CriticResult] = []
    for box in boxes:
        maxclass = walk.box_maxclass(box)

        # Only parameter-capable live.* controls need parameter_enable
        if maxclass not in LIVE_PARAMETER_OBJECTS:
            continue

        if not box.get("parameter_enable"):
            box_id = box.get("id", "?")
            results.append(CriticResult(
                "warning",
                f"{maxclass} ({box_id}) missing parameter_enable=1 -- "
                f"control will not be automatable or saveable in Ableton",
                f"Set parameter_enable=1 on {maxclass} and add "
                f"saved_attribute_attributes with longname/shortname",
            ))

    return results


# ---------------------------------------------------------------------------
# Check 5: Missing info text (annotation) on parameter controls
# ---------------------------------------------------------------------------

def _check_missing_info_text(
    boxes: list[dict],
) -> list[CriticResult]:
    """Warn when parameterized live.* controls lack annotation text.

    Without annotation, Ableton's Info View shows no description when
    the user hovers over the control.  This is a polish warning (not a
    blocker) -- the device still works, but looks unprofessional.
    *boxes* is one scope's boxes; review_m4l tags nested scopes (Q20).
    """
    results: list[CriticResult] = []

    for box in boxes:
        maxclass = walk.box_maxclass(box)

        if maxclass in LIVE_PARAMETER_OBJECTS:
            if box.get("parameter_enable") and not box.get("annotation"):
                box_id = box.get("id", "?")
                results.append(CriticResult(
                    "warning",
                    f"{maxclass} ({box_id}) missing info text -- "
                    f"Ableton Info View will show no description",
                    "Run polish_m4l_device() or set annotation attribute "
                    "manually",
                ))

    return results


# ---------------------------------------------------------------------------
# Check 6: Missing live.banks for Push controller bank organization
# ---------------------------------------------------------------------------

def _check_missing_live_banks(
    boxes: list[dict],
) -> list[CriticResult]:
    """Warn when a device has parameter controls but no live.banks.

    Without live.banks, Ableton/Push uses default bank layout which
    may not match the intended parameter grouping. *boxes* is every box of
    every non-gen scope (Q20).
    """
    has_param_controls = False
    has_live_banks = False

    for box in boxes:
        maxclass = walk.box_maxclass(box)

        # MAX saves live.banks as newobj text; the legacy maxclass form
        # still counts (walk.box_name covers both).
        if walk.box_name(box) == "live.banks":
            has_live_banks = True

        if (maxclass in LIVE_PARAMETER_OBJECTS
                and box.get("parameter_enable")):
            has_param_controls = True

    if has_param_controls and not has_live_banks:
        return [CriticResult(
            "warning",
            "M4L device has parameter controls but no live.banks -- "
            "Push controller layout will use Ableton defaults",
            "Run polish_m4l_device() or add live.banks for explicit "
            "Push bank control",
        )]

    return []
