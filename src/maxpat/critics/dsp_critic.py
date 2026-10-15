"""DSP critic -- checks signal flow, gen~ I/O matching, and gain staging.

Catches semantic DSP issues that the mechanical validation pipeline does
not detect:
  - gen~ I/O mismatches between GenExpr code and wrapper box. Boxes are
    detected by name (``gen~`` / ``mc.gen~``), not maxclass, because MAX and
    add_gen write them as ``newobj``; mc.gen~'s gen patcher is read from
    ``data.patcher`` (MAX's mc wrapper) as well as ``patcher`` (Q4 / E3,
    quick 261012-egf).
  - Missing gain staging before dac~/ezdac~

The former control-rate-to-signal-rate check was removed by Q3 / E2 (quick
261012-di7): it was ~100% noise (399 corpus hits, including the mandated
`param $1` -> gen~ form and number -> sig~) and its advice was harmful.

Every non-gen scope of the shared :class:`src.maxpat.graph.PatchGraph` is
reviewed on its own boxes and cords (Q20); nested findings carry
``CriticResult.path`` and a ``[p synth] `` prefix. Gen scopes are skipped
(GenExpr operators are not MSP objects). ``code_context["gen~_code"]`` is
keyed by top-level box id and applies to the top scope only.

NOTE: Does NOT duplicate validation.py Layer 4 checks (unterminated chains,
feedback loops). Focus is on semantic issues validation misses.
"""

from __future__ import annotations

import re
from collections import deque

from src.maxpat import walk
from src.maxpat.critics.base import CriticResult, tag_results
from src.maxpat.codegen import parse_genexpr_io
from src.maxpat.graph import SIGNAL_OUTLET_TYPES, PatchGraph


# Oscillator objects that need gain staging before dac~/ezdac~
_OSCILLATOR_NAMES = frozenset({
    "cycle~", "saw~", "rect~", "tri~", "noise~", "pink~",
    "mc.cycle~", "mc.saw~", "mc.rect~", "mc.tri~",
})

# Gain objects that attenuate signal (includes MC variants)
_GAIN_NAMES = frozenset({"*~", "gain~", "mc.*~", "mc.gain~"})

# Terminal signal objects
_TERMINAL_NAMES = frozenset({"dac~", "ezdac~"})

# Objects known to output MIDI-range (0-127) or UI-range values
_MIDI_RANGE_SOURCES = frozenset({
    "ctlin", "notein", "slider", "kslider",
    "live.dial", "live.slider", "live.numbox",
    "number", "flonum",
})

# Objects that normalize/scale values into safe ranges
_NORMALIZER_NAMES = frozenset({"scale", "zmap", "clip", "clip~"})

# Outlet type strings that carry audio: MAX writes "multichannelsignal" for
# mc.* outlets (and DB-derived saves mirror that), so a bare == "signal"
# check misclassifies every mc lane as control-rate.
_SIGNAL_OUTLET_TYPES = SIGNAL_OUTLET_TYPES

# Box names whose embedded gen patcher is checked against the box's I/O
# (Q4 / E3). Matched with walk.box_name, so newobj `gen~ ...` / `mc.gen~ ...`
# and maxclass-gen~ fixtures are all covered.
_GEN_BOX_NAMES = frozenset({"gen~", "mc.gen~"})


def review_dsp(
    patch_dict: dict,
    code_context: dict | None = None,
    *,
    graph: "PatchGraph | None" = None,
) -> list[CriticResult]:
    """Review DSP aspects of a patch.

    Checks:
      1. gen~ I/O match between GenExpr code and wrapper box (gen~ and
         mc.gen~ detected by box name; mc.gen~ code read from data.patcher
         too -- Q4 / E3)
      2. Gain staging: oscillators connected to dac~ without *~ or gain~
      3. Unsafe gain sources (see _check_unsafe_gain_sources)

    Args:
        patch_dict: A .maxpat-format dict.
        code_context: Optional dict with gen~ code strings keyed by
            top-level box id (top scope only).
            Format: {"gen~_code": {"obj-1": "out1 = in1 * 0.5;"}}
        graph: The shared PatchGraph of *patch_dict* (review_patch passes
            it); built here when None.

    Returns:
        List of CriticResult findings, top level first, nested scopes in
        pre-order.
    """
    if graph is None:
        graph = PatchGraph.build(patch_dict)
    results: list[CriticResult] = []
    for scope in graph.scopes:
        if scope.context == "gen":
            continue
        ctx = code_context if scope.path == () else None
        found: list[CriticResult] = []
        found.extend(_check_gen_io_match(scope.boxes, ctx))
        found.extend(_check_gain_staging(scope.boxes, scope.edges))
        found.extend(_check_unsafe_gain_sources(scope.boxes, scope.edges))
        results.extend(tag_results(found, scope.path))
    return results


# ---------------------------------------------------------------------------
# Check 1: gen~ I/O match
# ---------------------------------------------------------------------------

def _check_gen_io_match(
    box_lookup: dict[str, dict],
    code_context: dict | None,
) -> list[CriticResult]:
    """Find gen~ boxes and verify I/O counts match embedded GenExpr code.

    Boxes are selected by name (``gen~`` / ``mc.gen~``, Q4 / E3): MAX and
    add_gen write them as ``newobj``, so the former ``maxclass == "gen~"``
    gate never fired on real patches. The compared code is the first
    *wired* codebox of the embedded gen patcher (see _extract_codebox_code);
    when there is none, code_context supplies externally-provided code.
    """
    results: list[CriticResult] = []

    for box_id, box in box_lookup.items():
        # Only check gen~ / mc.gen~ boxes (by name, not maxclass -- Q4 / E3)
        if walk.box_name(box) not in _GEN_BOX_NAMES:
            continue

        gen_numinlets = box.get("numinlets", 0)
        gen_numoutlets = box.get("numoutlets", 0)
        if not isinstance(gen_numinlets, (int, float)) or isinstance(gen_numinlets, bool):
            gen_numinlets = 0
        if not isinstance(gen_numoutlets, (int, float)) or isinstance(gen_numoutlets, bool):
            gen_numoutlets = 0

        # Find codebox code from embedded patcher
        code = _extract_codebox_code(box)

        # Also check code_context for externally-provided code
        if code is None and isinstance(code_context, dict):
            gen_codes = code_context.get("gen~_code", {})
            if isinstance(gen_codes, dict):
                code = gen_codes.get(box_id)

        if not isinstance(code, str):
            continue  # No code to check

        # Parse I/O from GenExpr code
        code_inputs, code_outputs = parse_genexpr_io(code)

        # Compare inputs
        if code_inputs > gen_numinlets:
            results.append(CriticResult(
                "blocker",
                f"gen~ I/O input mismatch: GenExpr code uses {code_inputs} "
                f"inputs (in1..in{code_inputs}) but gen~ box '{box_id}' "
                f"has only {gen_numinlets} inlet(s)",
                f"Update gen~ box to have {code_inputs} inlets, or reduce "
                f"the number of inputs in the GenExpr code",
            ))

        # Compare outputs
        if code_outputs > gen_numoutlets:
            results.append(CriticResult(
                "blocker",
                f"gen~ I/O output mismatch: GenExpr code uses {code_outputs} "
                f"outputs (out1..out{code_outputs}) but gen~ box '{box_id}' "
                f"has only {gen_numoutlets} outlet(s)",
                f"Update gen~ box to have {code_outputs} outlets, or reduce "
                f"the number of outputs in the GenExpr code",
            ))

    return results


# Moved to walk.inner_patcher (Q20); kept as an alias.
_gen_inner_patcher = walk.inner_patcher


def _extract_codebox_code(gen_box: dict) -> str | None:
    """Extract GenExpr code from the first wired codebox inside a gen~ box.

    Only a codebox that appears as the source or destination of at least one
    patchline in its gen patcher is used (Q4 OQ1-A): an unwired codebox is
    demonstration or dead code whose in/out usage says nothing about the
    gen~ box's inlets (MAX's own gen~.maxhelp has one). Returns None when no
    wired codebox has code, so the caller falls back to code_context.
    """
    inner_patcher = walk.inner_patcher(gen_box)
    if not inner_patcher:
        return None

    wired_ids: set = set()
    lines = inner_patcher.get("lines")
    for line_entry in lines if isinstance(lines, list) else ():
        if not isinstance(line_entry, dict):
            continue
        patchline = line_entry.get("patchline", line_entry)
        if not isinstance(patchline, dict):
            continue
        for key in ("source", "destination"):
            end = patchline.get(key)
            if isinstance(end, list) and end and isinstance(end[0], (str, int)):
                wired_ids.add(end[0])

    boxes = inner_patcher.get("boxes")
    for entry in boxes if isinstance(boxes, list) else ():
        inner_box = entry.get("box") if isinstance(entry, dict) else None
        if not isinstance(inner_box, dict):
            continue
        if inner_box.get("maxclass") != "codebox":
            continue
        inner_id = inner_box.get("id")
        if not isinstance(inner_id, (str, int)) or inner_id not in wired_ids:
            continue
        code = inner_box.get("code")
        if code and isinstance(code, str):
            return code

    return None


# ---------------------------------------------------------------------------
# Check 2: Gain staging
# ---------------------------------------------------------------------------

def _outlettype(box: dict) -> list:
    """The box's ``outlettype`` as a list of str entries (non-str -> "").

    The dsp checks decide signal-ness from the source box's outlettype
    alone (no ``~``-name fallback), exactly as before Q20; the read sites
    are pinned by tests/test_signal_role_migration.py.
    """
    outlettype = box.get("outlettype")
    if not isinstance(outlettype, list):
        return []
    return [t if isinstance(t, str) else "" for t in outlettype]


def _check_gain_staging(
    box_lookup: dict[str, dict],
    edges: list,
) -> list[CriticResult]:
    """Detect oscillators connected to dac~/ezdac~ without gain staging.

    Uses BFS from each oscillator. If it reaches dac~/ezdac~ without passing
    through a gain object (*~ or gain~), emit a warning.
    """
    results: list[CriticResult] = []

    # Build signal adjacency from the scope's edges
    signal_adj: dict[str, list[str]] = {}
    for edge in edges:
        src_box = box_lookup.get(edge.src)
        if not src_box:
            continue

        # Check if this is a signal connection (source outlettype only)
        src_outlettype = _outlettype(src_box)
        is_signal = (
            edge.outlet < len(src_outlettype)
            and src_outlettype[edge.outlet] in _SIGNAL_OUTLET_TYPES
        )

        if is_signal:
            signal_adj.setdefault(edge.src, []).append(edge.dst)

    # Find oscillator boxes
    osc_ids = [
        box_id for box_id, box in box_lookup.items()
        if walk.box_name(box) in _OSCILLATOR_NAMES
    ]

    # BFS from each oscillator
    for osc_id in osc_ids:
        osc_name = walk.box_name(box_lookup[osc_id])
        queue = deque([(osc_id, False)])  # (current_id, passed_through_gain)
        visited: set[tuple[str, bool]] = set()

        while queue:
            current_id, has_gain = queue.popleft()
            state = (current_id, has_gain)
            if state in visited:
                continue
            visited.add(state)

            for next_id in signal_adj.get(current_id, []):
                next_box = box_lookup.get(next_id)
                if not next_box:
                    continue
                next_name = walk.box_name(next_box)

                next_has_gain = has_gain or (next_name in _GAIN_NAMES)

                if next_name in _TERMINAL_NAMES:
                    if not next_has_gain:
                        results.append(CriticResult(
                            "blocker",
                            f"Missing gain staging: '{osc_name}' ({osc_id}) "
                            f"connected to '{next_name}' ({next_id}) without "
                            f"passing through *~ or gain~",
                            f"Insert a '*~ 0.5' or 'gain~' between "
                            f"'{osc_name}' and '{next_name}' to control volume",
                        ))
                    continue  # Don't traverse past dac~

                queue.append((next_id, next_has_gain))

    return results


# ---------------------------------------------------------------------------
# Check 3: Unsafe gain sources
# ---------------------------------------------------------------------------

def _is_normalizer(box: dict) -> bool:
    """Check if a box is a normalizer/scaler that constrains values to safe range."""
    name = walk.box_name(box)
    if name in _NORMALIZER_NAMES:
        return True

    text = walk.box_text(box)
    # Division by 127 normalizes MIDI range: "/ 127." or "!/ 127."
    if text.startswith("/ 127") or text.startswith("!/ 127"):
        return True
    # Small multiplication factor like "* 0.007" (approx 1/127)
    if text.startswith("* 0.00") and not text.startswith("* 0.0 "):
        return True
    # expr/vexpr: only treat as normalizer if text contains division/scaling patterns
    if name in ("expr", "vexpr"):
        # Division by common ranges, or multiplication by small constant < 1.0
        if re.search(r'[/!]\s*127|[/!]\s*255|[/!]\s*100|\*\s*0\.\d', text):
            return True
        return False

    return False


def _parse_line_tilde_targets(text: str) -> list[float]:
    """Parse target values from a message box feeding line~.

    line~ message format: target1 time1 target2 time2 ...
    Values at even indices (0, 2, 4...) are target values.
    A single number with no time is also a valid target.
    """
    targets: list[float] = []
    parts = text.split()
    for i, part in enumerate(parts):
        if i % 2 == 0:  # even indices are target values
            try:
                targets.append(float(part))
            except ValueError:
                pass
    return targets


def _check_unsafe_gain_sources(
    box_lookup: dict[str, dict],
    edges: list,
) -> list[CriticResult]:
    """Detect MIDI-range control sources feeding *~ gain inlet without normalization.

    Traces backward from *~ inlet 1 (the gain/multiplier inlet) through
    control-rate connections. If it reaches a MIDI-range source (ctlin, notein,
    number, slider, etc.) without passing through a normalizer (scale, clip,
    / 127.), emit a blocker.

    Also traces through line~ (signal-rate) to detect >1.0 message values
    and MIDI sources feeding the gain inlet indirectly.
    """
    results: list[CriticResult] = []

    # Build control adjacency: for each (dst_id, dst_inlet) -> list of src_ids
    # Only non-signal connections
    ctrl_predecessors: dict[tuple[str, int], list[str]] = {}
    # Build signal adjacency: for each (dst_id, dst_inlet) -> list of src_ids
    sig_predecessors: dict[tuple[str, int], list[str]] = {}

    for edge in edges:
        src_box = box_lookup.get(edge.src)
        if not src_box:
            continue

        src_outlettype = _outlettype(src_box)
        is_signal = (
            edge.outlet < len(src_outlettype)
            and src_outlettype[edge.outlet] in _SIGNAL_OUTLET_TYPES
        )

        key = (edge.dst, edge.inlet)
        if is_signal:
            sig_predecessors.setdefault(key, []).append(edge.src)
        else:
            ctrl_predecessors.setdefault(key, []).append(edge.src)

    # Also build general control backward adjacency (any inlet) for tracing
    ctrl_backward: dict[str, list[str]] = {}
    for edge in edges:
        src_box = box_lookup.get(edge.src)
        if not src_box:
            continue

        src_outlettype = _outlettype(src_box)
        is_signal = (
            edge.outlet < len(src_outlettype)
            and src_outlettype[edge.outlet] in _SIGNAL_OUTLET_TYPES
        )
        if is_signal:
            continue

        ctrl_backward.setdefault(edge.dst, []).append(edge.src)

    # Names with a gain inlet at index 1 (mc.gain~ excluded: only 1 inlet)
    _GAIN_INLET_1_NAMES = frozenset({"*~", "mc.*~"})

    def _trace_ctrl_backward(start_ids: list[str], gain_name: str, gain_id: str):
        """BFS backward from control sources to find MIDI-range origins."""
        for start_src in start_ids:
            queue = deque([start_src])
            visited: set[str] = set()

            while queue:
                current_id = queue.popleft()
                if current_id in visited:
                    continue
                visited.add(current_id)

                current_box = box_lookup.get(current_id)
                if not current_box:
                    continue

                current_name = walk.box_name(current_box)

                # If we hit a normalizer, this path is safe -- stop tracing
                if _is_normalizer(current_box):
                    continue

                # Check message boxes for >1.0 target values (line~ path)
                if current_box.get("maxclass") == "message":
                    targets = _parse_line_tilde_targets(
                        walk.box_text(current_box),
                    )
                    if any(abs(t) > 1.0 for t in targets):
                        results.append(CriticResult(
                            "blocker",
                            f"Unsafe gain source: message '{walk.box_text(current_box)}' "
                            f"({current_id}) feeds '{gain_name}' ({gain_id}) "
                            f"inlet 1 via line~ with value >1.0 "
                            f"-- will cause dangerous audio levels",
                            f"Keep message target values in 0.0-1.0 range "
                            f"for gain control",
                        ))
                    continue

                # If we hit a MIDI-range source, flag it
                if current_name in _MIDI_RANGE_SOURCES:
                    results.append(CriticResult(
                        "blocker",
                        f"Unsafe gain source: '{current_name}' ({current_id}) "
                        f"feeds '{gain_name}' ({gain_id}) inlet 1 without "
                        f"normalization -- raw MIDI/UI values (0-127) will "
                        f"cause dangerous audio levels",
                        f"Insert 'scale 0 127 0. 1.' or '/ 127.' before the "
                        f"gain input",
                    ))
                    continue

                # Continue tracing backward
                for prev_id in ctrl_backward.get(current_id, []):
                    queue.append(prev_id)

    # Find all *~/mc.*~ boxes and check what feeds inlet 1
    for box_id, box in box_lookup.items():
        name = walk.box_name(box)
        if name not in _GAIN_INLET_1_NAMES:
            continue

        # Get control sources feeding inlet 1 (gain inlet) -- direct control
        inlet_1_ctrl = ctrl_predecessors.get((box_id, 1), [])

        # Get signal sources feeding inlet 1 -- check for line~
        inlet_1_sig = sig_predecessors.get((box_id, 1), [])
        line_tilde_ctrl_sources: list[str] = []
        for sig_src_id in inlet_1_sig:
            sig_src_box = box_lookup.get(sig_src_id)
            if sig_src_box and walk.box_name(sig_src_box) == "line~":
                # Trace backward from line~'s control inputs
                line_ctrl = ctrl_backward.get(sig_src_id, [])
                line_tilde_ctrl_sources.extend(line_ctrl)

        # Trace from direct control sources
        if inlet_1_ctrl:
            _trace_ctrl_backward(inlet_1_ctrl, name, box_id)

        # Trace from line~ control inputs (line~ acts as signal bridge)
        if line_tilde_ctrl_sources:
            _trace_ctrl_backward(line_tilde_ctrl_sources, name, box_id)

    return results
