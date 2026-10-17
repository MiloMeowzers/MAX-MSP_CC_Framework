"""DSP critic -- checks signal flow, gen~ I/O matching, and gain staging.

Catches semantic DSP issues that the mechanical validation pipeline does
not detect:
  - gen~ I/O mismatches between GenExpr code and wrapper box. Boxes are
    detected by name (``gen~`` / ``mc.gen~``), not maxclass, because MAX and
    add_gen write them as ``newobj``; mc.gen~'s gen patcher is read from
    ``data.patcher`` (MAX's mc wrapper) as well as ``patcher`` (Q4 / E3,
    quick 261012-egf).
  - Missing gain staging before an output terminal (Q26 / E6, PD-5): the
    gain stages and output terminals come from :mod:`src.maxpat.dsp_roles`
    (DB-driven, shared with validation.py): live.gain~ is a gain stage,
    mc.dac~ and plugout~ are terminals. The oscillator vocabulary and the
    traversal are :mod:`src.maxpat.gain_staging`, shared with validation.py
    Layer 4 (Q33 / S7); the critic adds the mc oscillators and reports a
    blocker
  - Unsafe gain sources (Q26 / E6, PD-4): a bounds-propagating backward
    trace into both inlets of every ``*~`` / ``mc.*~`` that reads comma
    segments, line~ target/time pairs, ``* k`` / ``/ k`` / scale / zmap /
    clip and each source's own range, and stops at unknown boxes

The former control-rate-to-signal-rate check was removed by Q3 / E2 (quick
261012-di7): it was ~100% noise (399 corpus hits, including the mandated
`param $1` -> gen~ form and number -> sig~) and its advice was harmful.

Every non-gen scope of the shared :class:`src.maxpat.graph.PatchGraph` is
reviewed on its own boxes and cords (Q20); nested findings carry
``CriticResult.path`` and a ``[p synth] `` prefix. Gen scopes are skipped
(GenExpr operators are not MSP objects). ``code_context["gen~_code"]`` is
keyed by top-level box id and applies to the top scope only.

NOTE: Gain staging is reported by both layers from one shared
implementation (src.maxpat.gain_staging). Unterminated chains and feedback
loops stay validation-only (validation.py Layer 4).
"""

from __future__ import annotations

import math
import re
from collections import deque

from src.maxpat import dsp_roles, gain_staging, walk
from src.maxpat.critics.base import CriticResult, tag_results
from src.maxpat.codegen import parse_genexpr_io
from src.maxpat.graph import SIGNAL_OUTLET_TYPES, PatchGraph
from src.maxpat.io_resolvers import split_box_text


# Back-compat exports (Q26 / E6, PD-5): the checks take their sets from
# dsp_roles(db); these equal the repo-DB values and a test pins them equal.
_GAIN_NAMES = frozenset({
    "*~", "mc.*~", "gain~", "mc.gain~", "live.gain~", "mc.live.gain~",
})
_TERMINAL_NAMES = frozenset({"dac~", "mc.dac~", "ezdac~", "mc.ezdac~", "plugout~"})

# Objects known to output MIDI-range (0-127) or UI-range values (back-compat;
# the Q26 trace reads each source's own bounds, see _bounded_source)
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
    db=None,
) -> list[CriticResult]:
    """Review DSP aspects of a patch.

    Checks:
      1. gen~ I/O match between GenExpr code and wrapper box (gen~ and
         mc.gen~ detected by box name; mc.gen~ code read from data.patcher
         too -- Q4 / E3)
      2. Gain staging: oscillators reaching an output terminal without a
         gain stage; both sets come from ``dsp_roles(db)`` (Q26 / E6, PD-5)
      3. Unsafe gain sources: a value range above 1.0 reaching either
         inlet of a ``*~`` / ``mc.*~`` (Q26 / E6, PD-4; see
         _check_unsafe_gain_sources)

    Args:
        patch_dict: A .maxpat-format dict.
        code_context: Optional dict with gen~ code strings keyed by
            top-level box id (top scope only).
            Format: {"gen~_code": {"obj-1": "out1 = in1 * 0.5;"}}
        graph: The shared PatchGraph of *patch_dict* (review_patch passes
            it); built here when None.
        db: Keyword-only ObjectDatabase for the DB-driven gain-stage and
            output-terminal sets (:mod:`src.maxpat.dsp_roles`). review_patch
            passes its own; None uses dsp_roles' cached default DB.

    Returns:
        List of CriticResult findings, top level first, nested scopes in
        pre-order.
    """
    if graph is None:
        graph = PatchGraph.build(patch_dict)
    gain_names = dsp_roles.gain_stage_names(db)
    terminal_names = dsp_roles.output_terminal_names(db)
    results: list[CriticResult] = []
    for scope in graph.scopes:
        if scope.context == "gen":
            continue
        ctx = code_context if scope.path == () else None
        found: list[CriticResult] = []
        found.extend(_check_gen_io_match(scope.boxes, ctx))
        found.extend(_check_gain_staging(scope.boxes, scope.edges, gain_names, terminal_names))
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
    gain_names=None,
    terminal_names=None,
) -> list[CriticResult]:
    """Detect oscillators reaching an output terminal without gain staging.

    Uses :func:`gain_staging.find_ungained_paths` (base and mc
    oscillators). If an oscillator reaches a terminal in *terminal_names*
    without passing through a gain stage in *gain_names*, emit a blocker. Both default to ``dsp_roles(None)`` (Q26 / E6, PD-5).
    For plugout~ the suggestion names only ``*~``: the M4L critic forbids
    gain~ / live.gain~ before plugout~.
    """
    if gain_names is None:
        gain_names = dsp_roles.gain_stage_names()
    if terminal_names is None:
        terminal_names = dsp_roles.output_terminal_names()
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
            0 <= edge.outlet < len(src_outlettype)
            and src_outlettype[edge.outlet] in _SIGNAL_OUTLET_TYPES
        )

        if is_signal:
            signal_adj.setdefault(edge.src, []).append(edge.dst)

    for osc_id, osc_name, next_id, next_name in gain_staging.find_ungained_paths(
        box_lookup, signal_adj,
        gain_staging.OSCILLATOR_NAMES | gain_staging.MC_OSCILLATOR_NAMES,
        gain_names, terminal_names,
    ):
        if next_name.endswith("plugout~"):
            suggestion = (
                f"Insert a '*~ 0.5' between '{osc_name}' and "
                f"'{next_name}' to control volume (no gain stage "
                f"object before plugout~ in Max for Live)"
            )
        else:
            suggestion = (
                f"Insert a '*~ 0.5' or 'gain~' between "
                f"'{osc_name}' and '{next_name}' to control volume"
            )
        results.append(CriticResult(
            "blocker",
            f"Missing gain staging: '{osc_name}' ({osc_id}) "
            f"connected to '{next_name}' ({next_id}) without "
            f"passing through *~ or gain~",
            suggestion,
        ))

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
    Kept for back-compat; the Q26 trace splits comma segments itself
    (:func:`_message_segments`).
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


# ---------------------------------------------------------------------------
# Q26 / E6 (PD-4): bounds-propagating unsafe-gain trace
# ---------------------------------------------------------------------------

# Boxes whose two inlets are both traced (mc.gain~ / gain~ take slider
# positions, not 0-1 gains, and are out of Q26 scope).
_GAIN_INLET_NAMES = frozenset({"*~", "mc.*~"})

_TRACE_HOP_LIMIT = 64
_TRACE_STATE_CAP = 4096

_DOLLAR_ATOM_RE = re.compile(r"^\$[1-9]$")
_NUMBER_ATOM_RE = re.compile(r"^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$")

_UNSAFE_GAIN_SUGGESTION = (
    "Normalize before the gain input, e.g. 'scale 0 127 0. 1.' or '/ 127.' "
    "for a 0-127 source, so the value stays within 0.0-1.0"
)


def _num(token) -> "float | None":
    """A MAX numeric atom as float, else None (``5``, ``-0.5``, ``1e3``)."""
    if not isinstance(token, str) or not _NUMBER_ATOM_RE.match(token):
        return None
    try:
        value = float(token)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def _attr_num(value, default: float) -> float:
    """A numeric box attribute (int/float, not bool, finite), else *default*."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    value = float(value)
    return value if math.isfinite(value) else default


def _message_segments(text) -> list:
    """Comma segments of a message box's text, up to the first unescaped ``;``.

    A comma is a ``,`` token or a token ending in an unescaped ``,`` (the
    structure critic's ``_is_setter_message`` rule). Everything from the
    first unescaped ``;`` on is a remote message and is ignored.
    """
    if not isinstance(text, str):
        return []
    segments: list = [[]]
    for token in split_box_text(text):
        semi = _unescaped_index(token, ";")
        if semi is not None:
            head = token[:semi]
            if head:
                segments[-1].append(head)
            break
        if token == ",":
            segments.append([])
            continue
        if token.endswith(",") and not token.endswith("\\,"):
            segments[-1].append(token[:-1])
            segments.append([])
            continue
        segments[-1].append(token)
    return [seg for seg in segments if seg]


def _unescaped_index(token: str, char: str) -> "int | None":
    for i, c in enumerate(token):
        if c == char and (i == 0 or token[i - 1] != "\\"):
            return i
    return None


def _bounded_source(box) -> "tuple | None":
    """``(lo, hi)`` of a UI / MIDI source's output (PD-4 rule 2), else None."""
    name = walk.box_name(box)
    if name in ("slider", "dial"):
        size = _attr_num(box.get("size"), 128.0)
        mult = _attr_num(box.get("mult"), 1.0)
        base = _attr_num(box.get("min"), 0.0)
        top = size if box.get("floatoutput") in (1, True) else size - 1.0
        a, b = base, top * mult + base
        return (min(a, b), max(a, b))
    if name in ("number", "flonum"):
        lo = _attr_num(box.get("minimum"), 0.0)
        hi = _attr_num(box.get("maximum"), 127.0)
        return (min(lo, hi), max(lo, hi))
    if name in ("live.dial", "live.slider", "live.numbox"):
        saved = box.get("saved_attribute_attributes")
        valueof = saved.get("valueof") if isinstance(saved, dict) else None
        if not isinstance(valueof, dict):
            valueof = {}
        lo = _attr_num(valueof.get("parameter_mmin"), 0.0)
        hi = _attr_num(valueof.get("parameter_mmax"), 127.0)
        return (min(lo, hi), max(lo, hi))
    if name in ("kslider", "ctlin", "notein"):
        return (0.0, 127.0)
    return None


def _op_of(box) -> "tuple | None":
    """The value op of a ``* k`` / ``/ k`` / scale / zmap / clip box, else None."""
    name = walk.box_name(box)
    args = [_num(t) for t in walk.box_args(box)]
    if name in ("*", "/"):
        if not args or args[0] is None:
            return None
        k = args[0]
        if name == "/":
            if k == 0:
                return None
            k = 1.0 / k
        return ("mul", k)
    if name in ("scale", "zmap"):
        if len(args) < 4 or any(a is None for a in args[:4]):
            return None
        a, b, c, d = args[:4]
        if a == b:
            return None
        return ("map", a, b, c, d, name == "zmap")
    if name == "clip":
        if len(args) < 2 or args[0] is None or args[1] is None:
            return None
        return ("clip", min(args[0], args[1]), max(args[0], args[1]))
    return None


def _apply_ops(interval: tuple, ops: tuple) -> "tuple | None":
    """Apply *ops* (source -> gain order) to *interval*; None when not finite."""
    lo, hi = interval
    for op in ops:
        if op[0] == "mul":
            a, b = lo * op[1], hi * op[1]
        elif op[0] == "map":
            _, x0, x1, y0, y1, clamp = op
            k = (y1 - y0) / (x1 - x0)
            a, b = y0 + (lo - x0) * k, y0 + (hi - x0) * k
            if clamp:
                c_lo, c_hi = min(y0, y1), max(y0, y1)
                a = min(max(a, c_lo), c_hi)
                b = min(max(b, c_lo), c_hi)
        else:  # clip
            _, c_lo, c_hi = op
            a = min(max(lo, c_lo), c_hi)
            b = min(max(hi, c_lo), c_hi)
        lo, hi = min(a, b), max(a, b)
        if not (math.isfinite(lo) and math.isfinite(hi)):
            return None
    return (lo, hi)


def _gain_source_label(box) -> str:
    if walk.box_maxclass(box) == "message":
        return f"message '{walk.box_text(box)}'"
    return f"'{walk.box_name(box)}'"


def _trigger_outlet_kind(box, outlet: int) -> "tuple | None":
    """("value",) / ("const", x) / None for trigger outlet *outlet* (PD-4 rule 5)."""
    letters = []
    for token in walk.box_args(box):
        if token.startswith("@"):
            break
        letters.append(token)
    if not letters:
        letters = ["i", "i"]
    if not (0 <= outlet < len(letters)):
        return None
    token = letters[outlet]
    if token in ("i", "f", "l"):
        return ("value",)
    value = _num(token)
    if value is not None:
        return ("const", value)
    return None


def _check_unsafe_gain_sources(
    box_lookup: dict[str, dict],
    edges: list,
) -> list[CriticResult]:
    """Flag a value source that can drive a ``*~`` / ``mc.*~`` input above 1.0.

    Q26 / E6 (planner decision PD-4). For each ``*~`` / ``mc.*~`` box and
    each of its two inlets, a backward BFS from the control cords into the
    inlet -- and from the control cords into inlet 0 of a ``line~`` whose
    signal feeds it -- carries an op chain of the value transforms passed:

    1. message box: comma segments up to the first unescaped ``;``; a
       segment starting with a symbol is a command (``set``, ``stop``) and
       carries no value; a message feeding line~ directly contributes only
       its even (target) positions, odd positions being ramp times; numbers
       are a constant interval, each ``$N`` continues to the message's
       inlet-0 feeders;
    2. bounded sources (:func:`_bounded_source`): slider / dial
       ``value * mult + min``, number / flonum ``minimum`` / ``maximum``
       (missing sides 0 / 127), live.dial / live.slider / live.numbox
       ``parameter_mmin`` / ``parameter_mmax``, kslider / ctlin / notein
       0-127;
    3. ``* k``, ``/ k``, ``scale`` / ``zmap a b c d`` and ``clip lo hi``
       (:func:`_op_of`) prepend their op and continue to inlet-0 feeders;
    4. an expr / vexpr matching :func:`_is_normalizer` is safe;
    5. trigger value outlets (i, f, l) and f / float / i / int pass the
       value on; numeric arguments are constant sources;
    6. anything else stops with an unknown range and no finding.

    For inlet 0 of a ``*~ k`` with nothing on inlet 1, the chain starts
    with multiply-by-k (``line~`` -> ``*~ 0.01`` is judged as the product).
    One blocker per (source, gain box, inlet) whose propagated range leaves
    -1.0..1.0. A visited set, a 64-hop limit and a 4096-state cap per
    (gain box, inlet) bound the walk.
    """
    results: list[CriticResult] = []

    # (dst_id, inlet) -> control edges into it
    ctrl_in: dict = {}
    for edge in edges:
        src_box = box_lookup.get(edge.src)
        if not src_box or not isinstance(edge.outlet, int) or edge.outlet < 0:
            continue
        src_outlettype = _outlettype(src_box)
        if edge.outlet < len(src_outlettype) and src_outlettype[edge.outlet] in _SIGNAL_OUTLET_TYPES:
            continue
        ctrl_in.setdefault((edge.dst, edge.inlet), []).append(edge)

    # (dst_id, inlet) -> signal edges into it
    sig_in: dict = {}
    fed_inlets: set = set()
    for edge in edges:
        fed_inlets.add((edge.dst, edge.inlet))
        src_box = box_lookup.get(edge.src)
        if not src_box or not isinstance(edge.outlet, int) or edge.outlet < 0:
            continue
        src_outlettype = _outlettype(src_box)
        if edge.outlet < len(src_outlettype) and src_outlettype[edge.outlet] in _SIGNAL_OUTLET_TYPES:
            sig_in.setdefault((edge.dst, edge.inlet), []).append(edge)

    for gain_id, gain_box in box_lookup.items():
        gain_name = walk.box_name(gain_box)
        if gain_name not in _GAIN_INLET_NAMES:
            continue
        for inlet in (0, 1):
            base_ops: tuple = ()
            if inlet == 0 and (gain_id, 1) not in fed_inlets:
                args = walk.box_args(gain_box)
                k = _num(args[0]) if args else None
                if k is not None:
                    base_ops = (("mul", k),)
            seeds = []
            for edge in ctrl_in.get((gain_id, inlet), ()):
                seeds.append((edge.src, edge.outlet, base_ops, False, False))
            for sig_edge in sig_in.get((gain_id, inlet), ()):
                line_box = box_lookup.get(sig_edge.src)
                if line_box is None or walk.box_name(line_box) != "line~":
                    continue
                for edge in ctrl_in.get((sig_edge.src, 0), ()):
                    seeds.append((edge.src, edge.outlet, base_ops, True, True))
            if seeds:
                results.extend(_trace_gain_inlet(
                    box_lookup, ctrl_in, gain_id, gain_name, inlet, seeds,
                ))
    return results


def _trace_gain_inlet(box_lookup, ctrl_in, gain_id, gain_name, inlet, seeds) -> list:
    """The PD-4 backward BFS for one (gain box, inlet); see the caller."""
    # source id -> [lo, hi, via, order]
    unsafe: dict = {}
    seen: set = set()
    queue = deque((state, 0) for state in seeds)
    states = 0

    def reach(src_id, interval, ops, crossed):
        value = _apply_ops(interval, ops)
        if value is None:
            return
        lo, hi = value
        if max(abs(lo), abs(hi)) <= 1.0:
            return
        entry = unsafe.get(src_id)
        if entry is None:
            unsafe[src_id] = [lo, hi, crossed, len(unsafe)]
        else:
            entry[0] = min(entry[0], lo)
            entry[1] = max(entry[1], hi)
            entry[2] = entry[2] or crossed

    def feeders(box_id, inlets, ops, into_line, crossed, hops):
        for i in inlets:
            for edge in ctrl_in.get((box_id, i), ()):
                queue.append(((edge.src, edge.outlet, ops, into_line, crossed), hops + 1))

    while queue:
        state, hops = queue.popleft()
        if state in seen or hops > _TRACE_HOP_LIMIT:
            continue
        seen.add(state)
        states += 1
        if states > _TRACE_STATE_CAP:
            break
        box_id, outlet, ops, into_line, crossed = state
        box = box_lookup.get(box_id)
        if not isinstance(box, dict):
            continue
        name = walk.box_name(box)

        if walk.box_maxclass(box) == "message":
            numbers = []
            follow = False
            for seg in _message_segments(box.get("text")):
                first = seg[0]
                if _num(first) is None and not _DOLLAR_ATOM_RE.match(first):
                    continue  # a command segment carries no value
                atoms = seg[0::2] if into_line else seg
                for atom in atoms:
                    value = _num(atom)
                    if value is not None:
                        numbers.append(value)
                    elif _DOLLAR_ATOM_RE.match(atom):
                        follow = True
            if numbers:
                reach(box_id, (min(numbers), max(numbers)), ops, crossed)
            if follow:
                feeders(box_id, (0,), ops, False, crossed, hops)
            continue

        bounds = _bounded_source(box)
        if bounds is not None:
            reach(box_id, bounds, ops, crossed)
            continue

        op = _op_of(box)
        if op is not None:
            feeders(box_id, (0,), (op,) + ops, False, crossed, hops)
            continue

        if name in ("expr", "vexpr"):
            continue  # a normalizer is safe; any other expr is unknown

        if name in ("trigger", "t"):
            kind = _trigger_outlet_kind(box, outlet)
            if kind is None:
                continue
            if kind[0] == "const":
                reach(box_id, (kind[1], kind[1]), ops, crossed)
                continue
            feeders(box_id, (0,), ops, False, crossed, hops)
            continue

        if name in ("f", "float", "i", "int"):
            args = walk.box_args(box)
            value = _num(args[0]) if args else None
            if value is not None:
                reach(box_id, (value, value), ops, crossed)
            feeders(box_id, (0, 1), ops, False, crossed, hops)
            continue
        # anything else: unknown range, the trace stops here (PD-4 rule 6)

    results = []
    for src_id, (lo, hi, crossed, _order) in sorted(unsafe.items(), key=lambda kv: kv[1][3]):
        label = _gain_source_label(box_lookup.get(src_id))
        via = " via line~" if crossed else ""
        peak = max(abs(lo), abs(hi))
        results.append(CriticResult(
            "blocker",
            f"Unsafe gain source: {label} ({src_id}) reaches '{gain_name}' "
            f"({gain_id}) inlet {inlet}{via} with values up to {peak:g} "
            f"(range {lo:g} to {hi:g}) -- gain inputs must stay within 0.0-1.0",
            _UNSAFE_GAIN_SUGGESTION,
        ))
    return results
