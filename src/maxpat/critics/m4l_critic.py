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
261012-egf; Q20). A patch with live.thisdevice and none of plugin~,
plugout~, midiin, midiout is a helper abstraction (``M4L_ABSTRACTION``,
quick 261022-ud6 WR-02): it gets the per-scope checks and parameter
uniqueness only, never the device completeness / quality checks.

Scopes (Q20): device-level checks (completeness, openinpresentation /
devicewidth on the top patcher, parameter_longname uniqueness across all
scopes, live.banks against parameter controls in any scope) run once and are
reported at the top level. Per-scope checks (gain stage on a scope-local
signal path to plugout~, ezdac~, parameter_enable, empty longname, missing
info text) run on every non-gen scope of the shared
:class:`src.maxpat.graph.PatchGraph`; nested findings carry
``CriticResult.path`` and a ``[p synth] `` prefix.

Q40 device checks (quick 261022-pqu) -- EXPERIMENTAL, not yet confirmed in
Live, so every one is a warning or a note and none blocks a save:
  - per scope (tagged like the checks above): ``stereo_out`` (a bare
    plugout~ fed on only one inlet), ``midi_passthrough`` (midi_effect only:
    a midiin with no outgoing cord or a midiout with no incoming one),
    ``shortname_length`` (note: shortname over 8 characters),
    ``int_param_range`` (Int type spanning more than 256 values),
    ``param_range`` (mmin >= mmax, or parameter_initial outside the range);
  - device level (once, at the top): ``shortname_unique``, ``bank_refs``
    (a parameterbanks slot naming no device parameter), ``device_height``
    (a presentation box below Live's 169 px device height).
"""

from __future__ import annotations

from collections import deque

from src.maxpat import walk
from src.maxpat.critics.base import CriticResult, finding_ids, tag_results
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

# detect_m4l_device_type's value for a patch whose only marker is
# live.thisdevice (WR-02): a helper abstraction / bpatcher face, reviewed with
# the per-scope checks only.
M4L_ABSTRACTION = "m4l_abstraction"

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
    else plugout~ -> "instrument", else midiin or midiout ->
    "midi_effect", else (live.thisdevice alone) ``M4L_ABSTRACTION`` -- a
    helper abstraction or bpatcher face that uses live.thisdevice for init
    (quick 261022-ud6 WR-02). That value is not a device kind:
    ``export_amxd`` refuses it.
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
    if names & {"midiin", "midiout"}:
        return "midi_effect"
    return M4L_ABSTRACTION


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
        device_type: One of "audio_effect", "instrument", "midi_effect", or
            ``M4L_ABSTRACTION`` (a live.thisdevice helper abstraction: the
            per-scope checks and parameter uniqueness only -- WR-02).
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

    if device_type == M4L_ABSTRACTION:
        # WR-02: a helper abstraction is part of a device, not one -- only the
        # per-scope checks (and parameter uniqueness, which still clashes in
        # the host device) apply; completeness, device quality, live.banks and
        # the Q40 device-level checks do not.
        results.extend(_check_parameter_uniqueness(all_params))
        for scope in scopes:
            boxes = _scope_boxes(scope)
            found: list[CriticResult] = []
            found.extend(_check_gain_plugout(scope))
            found.extend(_check_empty_longnames(scope))
            found.extend(_check_parameter_enable(boxes))
            found.extend(_check_missing_info_text(boxes))
            found.extend(_q40_scope_checks(scope, device_type))
            results.extend(tag_results(found, scope.path))
        return results

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

    # Q40 (EXPERIMENTAL, non-blocking): per-scope checks on the top level,
    # then the device-level ones.
    if top_is_device:
        results.extend(_q40_scope_checks(top, device_type))
    results.extend(_check_shortname_unique(graph))
    results.extend(_check_bank_refs(
        top.patcher, {ln for ln, _ref, status in all_params if status == "ok"}
    ))
    results.extend(_check_device_height(top.patcher, _scope_boxes(top) if top_is_device else []))

    for scope in scopes:
        if scope is top:
            continue
        boxes = _scope_boxes(scope)
        found: list[CriticResult] = []
        found.extend(_check_gain_plugout(scope))
        found.extend(_check_empty_longnames(scope))
        found.extend(_check_parameter_enable(boxes))
        found.extend(_check_missing_info_text(boxes))
        found.extend(_q40_scope_checks(scope, device_type))
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
            rule="gain_plugout",
            box_ids=finding_ids(stage_id, plugout_id),
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
                rule="gain_plugout",
                box_ids=finding_ids(box_id),
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
                rule="device_completeness",
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
                rule="empty_longnames",
                box_ids=finding_ids(box_id),
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
                rule="parameter_uniqueness",
                box_ids=finding_ids(*seen[longname].split("/"), *box_id.split("/")),
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
            rule="device_quality",
        ))

    if not patcher.get("devicewidth"):
        results.append(CriticResult(
            "warning",
            "M4L device missing devicewidth -- Ableton will use default width",
            "Set devicewidth to control device width in Ableton (e.g., 300.0)",
            rule="device_quality",
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
                rule="parameter_enable",
                box_ids=finding_ids(box_id),
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
                    rule="missing_info_text",
                    box_ids=finding_ids(box_id),
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
            rule="missing_live_banks",
        )]

    return []


# ---------------------------------------------------------------------------
# Q40 device checks (quick 261022-pqu) -- EXPERIMENTAL, all non-blocking
# ---------------------------------------------------------------------------

# Live's device view is 169 px tall (Live 12 template openrect [0, 0, 0, 169]
# and its "Device vertical limit" comment at y 170).
_DEVICE_HEIGHT = 169.0
# parameters.maxref.xml Short Name: about 5-7 characters fit; the builder
# and polish abbreviate to 8.
_SHORTNAME_MAX = 8
# parameters.maxref.xml Type: the Int type holds 256 values.
_INT_TYPE_MAX_SPAN = 255


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _valueof(box: dict):
    """saved_attribute_attributes.valueof of a box, or None when malformed."""
    saa = box.get("saved_attribute_attributes")
    if not isinstance(saa, dict):
        return None
    valueof = saa.get("valueof")
    return valueof if isinstance(valueof, dict) else None


def _param_valueofs(boxes: list):
    """(box_id, valueof) for parameter-capable live.* boxes with a valueof dict."""
    for box in boxes:
        if walk.box_maxclass(box) not in LIVE_PARAMETER_OBJECTS:
            continue
        valueof = _valueof(box)
        if valueof is not None:
            yield box.get("id", "?"), valueof


def _q40_scope_checks(scope, device_type: str) -> list[CriticResult]:
    """The Q40 per-scope checks for one scope, in a fixed order."""
    boxes = _scope_boxes(scope)
    found: list[CriticResult] = []
    found.extend(_check_stereo_out(scope))
    found.extend(_check_midi_passthrough(scope, device_type))
    found.extend(_check_shortname_length(boxes))
    found.extend(_check_int_param_range(boxes))
    found.extend(_check_param_range(boxes))
    return found


def _check_stereo_out(scope) -> list[CriticResult]:
    """A bare plugout~ that gets signal on only one of its two inlets.

    A bare ``plugout~`` is the stereo pair; feeding one inlet leaves the
    other channel silent (Q15 D3: a mono source feeds inlets 0 AND 1). A
    plugout~ with channel arguments, or with no signal cord at all (Live's
    instrument template), is not checked.
    """
    results: list[CriticResult] = []
    for box in scope.box_list:
        text = box.get("text")
        if not (isinstance(text, str) and text.strip() == "plugout~"):
            continue
        box_id = box.get("id")
        fed = {e.inlet for e in scope.edges if e.dst == box_id and e.signal and e.inlet in (0, 1)}
        if len(fed) != 1:
            continue
        inlet = next(iter(fed))
        results.append(CriticResult(
            "warning",
            f"plugout~ ({box_id}) receives signal on inlet {inlet} only -- the "
            f"other channel is silent",
            "Feed both plugout~ inlets: a mono source goes to inlet 0 AND "
            "inlet 1; a stereo source sends L to 0 and R to 1",
            rule="stereo_out",
            box_ids=finding_ids(box_id),
        ))
    return results


def _check_midi_passthrough(scope, device_type: str) -> list[CriticResult]:
    """midi_effect only: a midiin with no outgoing cord, a midiout with no incoming one.

    Live's MIDI Effect template wires midiin -> midiout; a MIDI effect that
    cuts the path blocks the track's MIDI.
    """
    if device_type != "midi_effect":
        return []
    results: list[CriticResult] = []
    sources = {e.src for e in scope.edges}
    dests = {e.dst for e in scope.edges}
    for box in scope.box_list:
        name = walk.box_name(box)
        box_id = box.get("id")
        if name == "midiin" and box_id not in sources:
            finding = (f"midiin ({box_id}) has no outgoing cord -- the MIDI "
                       f"effect does not pass the track's MIDI on")
        elif name == "midiout" and box_id not in dests:
            finding = (f"midiout ({box_id}) has no incoming cord -- the MIDI "
                       f"effect sends no MIDI to the track")
        else:
            continue
        results.append(CriticResult(
            "warning",
            finding,
            "Wire midiin through your processing (or directly) into midiout, "
            "as Live's MIDI Effect template does",
            rule="midi_passthrough",
            box_ids=finding_ids(box_id),
        ))
    return results


def _check_shortname_length(boxes: list) -> list[CriticResult]:
    """Note: a parameter shortname longer than 8 characters (Push / device title)."""
    results: list[CriticResult] = []
    for box_id, valueof in _param_valueofs(boxes):
        short = valueof.get("parameter_shortname")
        if isinstance(short, str) and len(short) > _SHORTNAME_MAX:
            results.append(CriticResult(
                "note",
                f"parameter_shortname '{short}' ({box_id}) is {len(short)} "
                f"characters -- Live shows about 5-7",
                f"Shorten parameter_shortname to {_SHORTNAME_MAX} characters "
                f"or fewer",
                rule="shortname_length",
                box_ids=finding_ids(box_id),
            ))
    return results


def _check_int_param_range(boxes: list) -> list[CriticResult]:
    """An Int-type parameter whose range spans more than 256 values."""
    results: list[CriticResult] = []
    for box_id, valueof in _param_valueofs(boxes):
        ptype = valueof.get("parameter_type")
        mn = valueof.get("parameter_mmin")
        mx = valueof.get("parameter_mmax")
        if not (_is_number(ptype) and ptype == 1 and _is_number(mn) and _is_number(mx)):
            continue
        if mx - mn > _INT_TYPE_MAX_SPAN:
            results.append(CriticResult(
                "warning",
                f"Int parameter ({box_id}) spans {mn}..{mx} -- Live's Int type "
                f"holds 256 values, so the range is clipped",
                "Set parameter_type to Float (0) and parameter_unitstyle to "
                "Int (0) for wide integer ranges",
                rule="int_param_range",
                box_ids=finding_ids(box_id),
            ))
    return results


def _check_param_range(boxes: list) -> list[CriticResult]:
    """mmin >= mmax, or a parameter_initial outside [mmin, mmax]."""
    results: list[CriticResult] = []
    for box_id, valueof in _param_valueofs(boxes):
        mn = valueof.get("parameter_mmin")
        mx = valueof.get("parameter_mmax")
        if not (_is_number(mn) and _is_number(mx)):
            continue
        if mn >= mx:
            finding = f"Parameter ({box_id}) has mmin {mn} >= mmax {mx}"
        else:
            initial = valueof.get("parameter_initial")
            first = initial[0] if isinstance(initial, list) and initial else None
            if not _is_number(first) or mn <= first <= mx:
                continue
            finding = (f"Parameter ({box_id}) parameter_initial {first} is outside "
                       f"its range {mn}..{mx}")
        results.append(CriticResult(
            "warning",
            finding,
            "Set parameter_mmin < parameter_mmax and an initial value inside "
            "the range",
            rule="param_range",
            box_ids=finding_ids(box_id),
        ))
    return results


def _check_shortname_unique(graph: PatchGraph) -> list[CriticResult]:
    """Duplicate parameter_shortname across the device (every non-gen scope)."""
    results: list[CriticResult] = []
    seen: dict[str, str] = {}
    for scope in _device_scopes(graph):
        for box_id, valueof in _param_valueofs(_scope_boxes(scope)):
            short = valueof.get("parameter_shortname")
            if not isinstance(short, str) or not short.strip():
                continue
            ref = f"{scope.key}/{box_id}" if scope.key else box_id
            if short in seen:
                results.append(CriticResult(
                    "warning",
                    f"Duplicate parameter_shortname '{short}' in boxes "
                    f"'{seen[short]}' and '{ref}' -- Live and Push show the "
                    f"two parameters with the same label",
                    f"Give one of the '{short}' parameters a distinct "
                    f"parameter_shortname",
                    rule="shortname_unique",
                    box_ids=finding_ids(*seen[short].split("/"), *ref.split("/")),
                ))
            else:
                seen[short] = ref
    return results


def _check_bank_refs(patcher: dict, longnames: set) -> list[CriticResult]:
    """parameterbanks slots that name no parameter longname of the device."""
    parameters = patcher.get("parameters") if isinstance(patcher, dict) else None
    banks = parameters.get("parameterbanks") if isinstance(parameters, dict) else None
    if not isinstance(banks, dict):
        return []
    missing: list[str] = []
    for bank in banks.values():
        slots = bank.get("parameters") if isinstance(bank, dict) else None
        if not isinstance(slots, list):
            continue
        for slot in slots:
            if isinstance(slot, str) and slot != "-" and slot not in longnames and slot not in missing:
                missing.append(slot)
    if not missing:
        return []
    names = ", ".join(f"'{m}'" for m in missing)
    return [CriticResult(
        "warning",
        f"parameterbanks name parameters that are not in the device: {names}",
        "Remove the stale slots (use \"-\") or rename them to existing "
        "parameter_longname values",
        rule="bank_refs",
    )]


def _check_device_height(patcher: dict, boxes: list) -> list[CriticResult]:
    """Presentation boxes that end below Live's 169 px device height."""
    if not isinstance(patcher, dict) or not patcher.get("openinpresentation"):
        return []
    over: list[str] = []
    for box in boxes:
        if not box.get("presentation"):
            continue
        rect = box.get("presentation_rect")
        if not (isinstance(rect, list) and len(rect) == 4 and all(_is_number(v) for v in rect)):
            continue
        if rect[1] + rect[3] > _DEVICE_HEIGHT:
            over.append(box.get("id", "?"))
    if not over:
        return []
    ids = finding_ids(*over)
    return [CriticResult(
        "warning",
        f"Presentation boxes end below Live's {int(_DEVICE_HEIGHT)} px device "
        f"height and are clipped: {', '.join(ids) or '?'}",
        f"Keep every presentation_rect bottom at or above y "
        f"{int(_DEVICE_HEIGHT)}",
        rule="device_height",
        box_ids=ids,
    )]
