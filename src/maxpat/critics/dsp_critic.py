"""DSP critic -- checks signal flow, gen~ I/O matching, and gain staging.

Catches semantic DSP issues that the mechanical validation pipeline does
not detect:
  - gen~ I/O mismatches between the gen patcher and the wrapper box. Boxes
    are detected by name (``gen~`` / ``mc.gen~``), not maxclass, because MAX
    and add_gen write them as ``newobj``; mc.gen~'s gen patcher is read from
    ``data.patcher`` (MAX's mc wrapper) as well as ``patcher`` (Q4 / E3,
    quick 261012-egf). The box's ports are the ``in N`` / ``out N``
    operators; a codebox counts only through inputs / outputs it uses but
    nothing wires (quick 261022-ud6 CR-03), so codeboxes in series or fed by
    params pass.
  - Missing gain staging before an output terminal (Q26 / E6, PD-5): the
    gain stages and output terminals come from :mod:`src.maxpat.dsp_roles`
    (DB-driven, shared with validation.py): live.gain~ is a gain stage,
    mc.dac~ and plugout~ are terminals. The oscillator vocabulary and the
    traversal are :mod:`src.maxpat.gain_staging`, shared with validation.py
    Layer 4 (Q33 / S7); the critic adds the mc oscillators and reports a
    blocker
  - Unsafe gain sources (Q26 / E6, PD-4): a bounds-propagating backward
    trace into both inlets of every ``*~`` / ``mc.*~`` acting as a gain stage
    (an audio operand on the other inlet, output not feeding an oscillator's
    frequency / phase inlets -- quick 261022-ud6 CR-01 / WR-04) that reads comma
    segments, line~ target/time pairs, ``* k`` / ``/ k`` / scale / zmap /
    clip and each source's own range, and stops at unknown boxes. The
    blocker carries an ``insert_gain_normalizer`` quick-fix payload (Q39:
    ``scale <lo> <hi> 0. 1.`` for a bounded source, ``clip 0. 1.`` for a
    constant) when exactly one traced cord leaves the source and every op
    chain keeps a 0-1 input safe
  - gen~ ``@param $1`` messages (Q39): a message box matching
    ``@name $N`` cabled into gen~ -- the same condition as validation.py
    Layer 4's warning, reported here too (like gain staging) so it can carry
    a ``rewrite_gen_param`` quick-fix payload

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

from src.maxpat import dsp_roles, gain_staging, genexpr_parse, walk
from src.maxpat.critics.base import CriticResult, finding_ids, tag_results
from src.maxpat.critics.fixes import gain_normalizer_fix, gen_param_fix, max_float
from src.maxpat.codegen import parse_genexpr_io
from src.maxpat.graph import SIGNAL_OUTLET_TYPES, PatchGraph
from src.maxpat.io_resolvers import split_box_text


# Back-compat exports (Q26 / E6, PD-5): the checks take their sets from
# dsp_roles(db); these equal the repo-DB values and a test pins them equal.
_GAIN_NAMES = frozenset({
    "*~", "mc.*~", "gain~", "mc.gain~", "live.gain~", "mc.live.gain~",
})
_TERMINAL_NAMES = frozenset({"dac~", "mc.dac~", "ezdac~", "mc.ezdac~", "plugout~"})

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
      1. gen~ I/O match between the gen patcher and the wrapper box (gen~
         and mc.gen~ detected by box name; mc.gen~ code read from
         data.patcher too -- Q4 / E3): ``in N`` / ``out N`` operators, and
         codebox inputs / outputs only where they are unwired (CR-03)
      2. Gain staging: oscillators reaching an output terminal without a
         gain stage; both sets come from ``dsp_roles(db)`` (Q26 / E6, PD-5)
      3. Unsafe gain sources: a value range above 1.0 reaching either
         inlet of a ``*~`` / ``mc.*~`` (Q26 / E6, PD-4; see
         _check_unsafe_gain_sources)
      4. gen~ ``@param $1`` message syntax (warning, Q39): mirrors the
         validation.py Layer 4 warning, as gain staging does, and carries a
         ``rewrite_gen_param`` fix

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
        found.extend(_check_gen_param_message_syntax(scope.boxes, scope.edges))
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
    gate never fired on real patches.

    The gen~ box's ports are the ``in N`` / ``out N`` operators of its gen
    patcher, not a codebox's ``inK`` / ``outK`` (quick 261022-ud6 CR-03): a
    codebox may be fed by params, history or another codebox. Two counts are
    compared with the box's ``numinlets`` / ``numoutlets``:

    * the highest ``in N`` / ``out N`` operator (:func:`_gen_operator_io`);
    * for a *wired* codebox (OQ1-A), the code's input / output count when
      some ``inK`` / ``outK`` it uses has no cord on that codebox port
      (:func:`_unwired_codebox_io`) -- the add_gen layout with
      ``num_inputs`` below the code's count.

    The larger count is reported. Only when the gen patcher has no wired
    codebox with code does ``code_context`` supply externally-provided code,
    compared as a whole.
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

        inner = walk.inner_patcher(box)
        op_inputs, op_outputs = _gen_operator_io(inner)
        cb_inputs, cb_outputs, wired_code = _unwired_codebox_io(inner)
        code_inputs = max(op_inputs, cb_inputs)
        code_outputs = max(op_outputs, cb_outputs)

        # Externally-provided code when no wired codebox carries any
        if not wired_code and isinstance(code_context, dict):
            gen_codes = code_context.get("gen~_code", {})
            code = gen_codes.get(box_id) if isinstance(gen_codes, dict) else None
            if isinstance(code, str):
                ctx_inputs, ctx_outputs = parse_genexpr_io(code)
                code_inputs = max(code_inputs, ctx_inputs)
                code_outputs = max(code_outputs, ctx_outputs)

        # Compare inputs
        if code_inputs > gen_numinlets:
            results.append(CriticResult(
                "blocker",
                f"gen~ I/O input mismatch: GenExpr code uses {code_inputs} "
                f"inputs (in1..in{code_inputs}) but gen~ box '{box_id}' "
                f"has only {gen_numinlets} inlet(s)",
                f"Update gen~ box to have {code_inputs} inlets, or reduce "
                f"the number of inputs in the GenExpr code",
                rule="gen_io_match",
                box_ids=finding_ids(box_id),
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
                rule="gen_io_match",
                box_ids=finding_ids(box_id),
            ))

    return results


# Moved to walk.inner_patcher (Q20); kept as an alias.
_gen_inner_patcher = walk.inner_patcher


_CODE_IN_RE = re.compile(r"\bin(\d+)\b")
_CODE_OUT_RE = re.compile(r"\bout(\d+)\b")


def _gen_patcher_parts(inner_patcher) -> tuple:
    """``(boxes, ports)`` of a gen patcher: its box dicts, and the set of
    ``(box_id, "in" | "out", port)`` ends of its patchlines."""
    if not isinstance(inner_patcher, dict):
        return [], set()
    ports: set = set()
    lines = inner_patcher.get("lines")
    for line_entry in lines if isinstance(lines, list) else ():
        if not isinstance(line_entry, dict):
            continue
        patchline = line_entry.get("patchline", line_entry)
        if not isinstance(patchline, dict):
            continue
        for key, side in (("source", "out"), ("destination", "in")):
            end = patchline.get(key)
            if (
                isinstance(end, list) and len(end) >= 2
                and isinstance(end[0], (str, int))
                and isinstance(end[1], int) and not isinstance(end[1], bool)
            ):
                ports.add((end[0], side, end[1]))
    boxes = []
    raw = inner_patcher.get("boxes")
    for entry in raw if isinstance(raw, list) else ():
        inner_box = entry.get("box") if isinstance(entry, dict) else None
        if isinstance(inner_box, dict):
            boxes.append(inner_box)
    return boxes, ports


def _gen_operator_io(inner_patcher) -> tuple:
    """Highest ``in N`` / ``out N`` operator numbers of a gen patcher (CR-03)."""
    boxes, _ports = _gen_patcher_parts(inner_patcher)
    top = {"in": 0, "out": 0}
    for inner_box in boxes:
        name = walk.box_name(inner_box)
        if name not in top:
            continue
        args = walk.box_args(inner_box)
        n = _num(args[0]) if args else None
        if n is not None and n == int(n) and n >= 1:
            top[name] = max(top[name], int(n))
    return top["in"], top["out"]


def _unwired_codebox_io(inner_patcher) -> tuple:
    """``(inputs, outputs, wired_code)`` from the wired codeboxes (CR-03).

    Only a codebox that appears in at least one patchline of its gen patcher
    is read (Q4 OQ1-A): an unwired codebox is demonstration or dead code
    (MAX's own gen~.maxhelp has one). For each, its code's input count
    counts only when some ``inK`` it uses has no cord into codebox inlet
    K-1, and its output count only when some ``outK`` has no cord out of
    codebox outlet K-1: a fully wired codebox's ports are its own, fed by
    ``in N`` operators, params, history or another codebox. *wired_code*
    is True when any wired codebox carries code.
    """
    boxes, ports = _gen_patcher_parts(inner_patcher)
    wired_ids = {box_id for box_id, _side, _port in ports}
    inputs = outputs = 0
    wired_code = False
    for inner_box in boxes:
        if inner_box.get("maxclass") != "codebox":
            continue
        inner_id = inner_box.get("id")
        if not isinstance(inner_id, (str, int)) or inner_id not in wired_ids:
            continue
        code = inner_box.get("code")
        if not code or not isinstance(code, str):
            continue
        wired_code = True
        n_in, n_out = parse_genexpr_io(code)
        masked = genexpr_parse.mask(code)  # comments / strings blanked (Q22)
        used_in = {int(k) for k in _CODE_IN_RE.findall(masked)}
        used_out = {int(k) for k in _CODE_OUT_RE.findall(masked)}
        if any((inner_id, "in", k - 1) not in ports for k in used_in if k >= 1):
            inputs = max(inputs, n_in)
        if any((inner_id, "out", k - 1) not in ports for k in used_out if k >= 1):
            outputs = max(outputs, n_out)
    return inputs, outputs, wired_code


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
            rule="gain_staging",
            box_ids=finding_ids(osc_id, next_id),
        ))

    return results


# ---------------------------------------------------------------------------
# Q39: gen~ @param message syntax (parity with validation.py Layer 4)
# ---------------------------------------------------------------------------

_GEN_AT_PARAM_RE = re.compile(r"@\w+\s+\$")


def _check_gen_param_message_syntax(box_lookup: dict[str, dict], edges: list) -> list[CriticResult]:
    """Flag a ``@param $1`` message cabled into gen~ (should be ``param $1``).

    The condition is validation.py's ``_check_gen_param_message_syntax``:
    a ``message`` box whose text matches ``@\\w+\\s+\\$`` with a control cord
    into a box named ``gen~``; one warning per message box (the first gen~
    cord in edge order). Carries a ``rewrite_gen_param`` fix (Q39).
    """
    results: list[CriticResult] = []
    done: set = set()
    for edge in edges:
        if edge.signal or edge.src in done:
            continue
        box = box_lookup.get(edge.src)
        if walk.box_maxclass(box) != "message":
            continue
        text = walk.box_text(box)
        if not _GEN_AT_PARAM_RE.search(text):
            continue
        dst = box_lookup.get(edge.dst)
        if not dst or walk.box_name(dst) != "gen~":
            continue
        done.add(edge.src)
        fix = gen_param_fix(edge.src, text)
        results.append(CriticResult(
            "warning",
            f"gen~ param message '{text}' ({edge.src}) into 'gen~' ({edge.dst}) uses "
            f"'@name' -- gen~ params take plain name messages",
            f"Send 'param_name $1' with no '@' prefix (here '{fix.ops[0].text}')",
            rule="gen_param_message_syntax",
            box_ids=finding_ids(edge.src, edge.dst),
            fix=fix,
        ))
    return results


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

    Q26 / E6 (planner decision PD-4), narrowed to gain stages by quick
    261022-ud6 (CR-01 / WR-04). A ``*~`` / ``mc.*~`` box is judged only as
    a gain stage:

    * a box whose signal output reaches any inlet of an oscillator
      (cycle~, saw~, rect~, tri~, phasor~ and mc. forms), or a filter /
      delay parameter inlet (lores~ cutoff, svf~, onepole~, reson~ freq/Q,
      cross~, comb~ / allpass~ delay; :data:`_PARAMETER_INLETS`), directly
      or through signal arithmetic / mtof~, scales a frequency or phase and
      is skipped (:func:`_feeds_oscillator`);
    * an inlet is traced only when the *other* inlet carries audio
      (:func:`_inlet_has_audio`): a ramp source (line~, curve~, sig~,
      adsr~, number~), a constant ``*~ k`` argument with inlet 1 unfed, or a
      control cord there makes the box arithmetic. An inlet 0 with no cord
      at all counts as audio (the gain's audio input is not wired yet).

    For each judged inlet, a backward BFS from the control cords into the
    inlet -- and, through :func:`_ramp_seeds`, from the control cords into
    inlet 0 of a ``line~`` whose signal feeds it, directly or through
    arithmetic ``*~ k`` boxes (multiply-by-k prepended) -- carries an op
    chain of the value transforms passed:

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
    4. an expr / vexpr stops with an unknown range (no finding);
    5. trigger value outlets (i, f, l) and f / float / i / int pass the
       value on; numeric arguments are constant sources;
    6. anything else stops with an unknown range and no finding.

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

    # src_id -> signal edges out of it (the forward modulation walk)
    sig_out: dict = {}
    for edges_in in sig_in.values():
        for edge in edges_in:
            sig_out.setdefault(edge.src, []).append(edge)

    audio_memo: dict = {}
    for gain_id, gain_box in box_lookup.items():
        gain_name = walk.box_name(gain_box)
        if gain_name not in _GAIN_INLET_NAMES:
            continue
        # CR-01 / WR-04 (quick 261022-ud6): a *~ whose output sets an
        # oscillator's frequency or phase scales Hz; it is not a gain stage.
        if _feeds_oscillator(gain_id, box_lookup, sig_out):
            continue
        for inlet in (0, 1):
            # CR-01: the traced inlet is a gain input only when the other
            # operand carries audio. A ramp, a constant ``*~ k`` argument
            # (inlet 1 unfed) or a control cord there makes the box plain
            # arithmetic, judged where its output reaches a real gain. An
            # inlet 0 with no cord at all is the not-yet-wired audio input of
            # a gain whose control inlet is fed: judged as audio.
            other = 1 - inlet
            if other == 0 and (gain_id, 0) not in fed_inlets:
                pass
            elif not _inlet_has_audio(gain_id, other, box_lookup, sig_in, audio_memo):
                continue
            seeds = []
            seed_via = []  # the consumer cord (dst, inlet) of each seed (Q39)
            for edge in ctrl_in.get((gain_id, inlet), ()):
                seeds.append((edge.src, edge.outlet, (), False, False))
                seed_via.append((edge.dst, edge.inlet))
            for sig_edge in sig_in.get((gain_id, inlet), ()):
                _ramp_seeds(
                    sig_edge.src, (), box_lookup, ctrl_in, sig_in, seeds, seed_via, set(),
                )
            if seeds:
                results.extend(_trace_gain_inlet(
                    box_lookup, ctrl_in, gain_id, gain_name, inlet, seeds, seed_via,
                ))
    return results


# CR-01 / WR-04: oscillators whose every inlet is a frequency, phase or shape
# control (gain_staging's set adds noise~ / pink~, which have none, and has no
# phasor~).
_MODULATED_OSCILLATORS = frozenset(
    name
    for base in ("cycle~", "saw~", "rect~", "tri~", "phasor~")
    for name in (base, "mc." + base)
)

# WP3 follow-up (quick 261022-ud6 WP7a): filter / delay inlets that take a
# frequency, resonance or delay time, never audio or a gain (DB digests:
# lores~ 1 cutoff / 2 resonance, svf~ 1 cutoff / 2 resonance, onepole~ 1
# cutoff, reson~ 2 centre frequency / 3 Q -- inlet 1 is its input GAIN and
# stays out --, cross~ 1 crossover, comb~ / allpass~ 1 delay ms,
# filtercoeff~ 0 frequency / 2 Q). A *~ whose output reaches one of these
# scales Hz like an oscillator's frequency input.
_PARAMETER_INLETS = {
    name: inlets
    for base, inlets in (
        ("lores~", frozenset({1, 2})),
        ("svf~", frozenset({1, 2})),
        ("onepole~", frozenset({1})),
        ("reson~", frozenset({2, 3})),
        ("cross~", frozenset({1})),
        ("comb~", frozenset({1})),
        ("allpass~", frozenset({1})),
        ("filtercoeff~", frozenset({0, 2})),
    )
    for name in (base, "mc." + base)
}

# Signal arithmetic: a value passes through it unchanged in kind.
_SIGNAL_ARITH = frozenset(
    name
    for base in ("+~", "-~", "*~", "/~", "!-~", "!/~")
    for name in (base, "mc." + base)
)

# Frequency converters: the forward modulation walk continues through them.
_FREQ_CONVERTERS = frozenset({"mtof~", "mc.mtof~"})

# Signal sources that carry a control value, not audio (CR-01).
_RAMP_SOURCES = frozenset(
    name
    for base in ("line~", "curve~", "sig~", "adsr~", "number~")
    for name in (base, "mc." + base)
)

_WALK_LIMIT = 256


def _feeds_oscillator(box_id, box_lookup, sig_out) -> bool:
    """True when *box_id*'s signal output reaches an oscillator inlet (CR-01).

    Forward walk over signal cords through signal arithmetic (``+~``, ``*~``,
    ...) and ``mtof~``. Every inlet of cycle~ / saw~ / rect~ / tri~ / phasor~
    (and the mc. forms) is a frequency, phase or shape input, never a gain;
    so are the filter / delay parameter inlets in :data:`_PARAMETER_INLETS`
    (an LFO depth into a lores~ cutoff, WP7a).
    """
    seen = {box_id}
    queue = deque([box_id])
    steps = 0
    while queue and steps < _WALK_LIMIT:
        steps += 1
        node = queue.popleft()
        for edge in sig_out.get(node, ()):
            dst = box_lookup.get(edge.dst)
            if dst is None:
                continue
            name = walk.box_name(dst)
            if name in _MODULATED_OSCILLATORS:
                return True
            if edge.inlet in _PARAMETER_INLETS.get(name, ()):
                return True
            if (name in _SIGNAL_ARITH or name in _FREQ_CONVERTERS) and edge.dst not in seen:
                seen.add(edge.dst)
                queue.append(edge.dst)
    return False


def _inlet_has_audio(box_id, inlet, box_lookup, sig_in, memo, stack=None) -> bool:
    """True when a signal cord into (*box_id*, *inlet*) carries audio (CR-01).

    Ramp sources (line~, curve~, sig~, adsr~, number~) carry a control
    value; signal arithmetic carries audio only when one of its own inputs
    does (``line~ -> *~ 440.`` is a scaled ramp). Every other signal source
    is audio. A control cord, or no cord, is never audio.
    """
    if stack is None:
        stack = set()
    for edge in sig_in.get((box_id, inlet), ()):
        if _is_audio_source(edge.src, box_lookup, sig_in, memo, stack):
            return True
    return False


def _is_audio_source(src_id, box_lookup, sig_in, memo, stack) -> bool:
    if src_id in memo:
        return memo[src_id]
    box = box_lookup.get(src_id)
    if box is None:
        return False
    name = walk.box_name(box)
    if name in _RAMP_SOURCES:
        memo[src_id] = False
        return False
    if name not in _SIGNAL_ARITH:
        memo[src_id] = True
        return True
    if src_id in stack:
        return False  # an arithmetic-only cycle carries no audio of its own
    stack.add(src_id)
    value = any(
        _inlet_has_audio(src_id, i, box_lookup, sig_in, memo, stack) for i in (0, 1)
    )
    stack.discard(src_id)
    memo[src_id] = value
    return value


def _ramp_seeds(src_id, ops, box_lookup, ctrl_in, sig_in, seeds, seed_via, seen) -> None:
    """Seed the trace through a control-valued signal source (CR-01).

    A ``line~`` seeds the control cords into its inlet 0 (``into_line``).
    A ``*~ k`` / ``mc.*~ k`` with nothing on inlet 1 and no audio on inlet 0
    is a scaled ramp: multiply-by-*k* is prepended and the walk continues
    into its inlet 0, so ``line~ -> *~ 0.5 -> *~`` is judged as the product
    at the gain. Anything else gives no seed (unknown range).
    """
    if src_id in seen or len(seen) > _TRACE_HOP_LIMIT:
        return
    seen.add(src_id)
    box = box_lookup.get(src_id)
    if box is None:
        return
    name = walk.box_name(box)
    if name == "line~":
        for edge in ctrl_in.get((src_id, 0), ()):
            seeds.append((edge.src, edge.outlet, ops, True, True))
            seed_via.append((edge.dst, edge.inlet))
        return
    if name not in _GAIN_INLET_NAMES:
        return
    if (src_id, 1) in ctrl_in or (src_id, 1) in sig_in:
        return  # a fed multiplier has its own (untraced) range
    args = walk.box_args(box)
    k = _num(args[0]) if args else None
    if k is None:
        return  # *~ with no argument and nothing on inlet 1 multiplies by 0
    if _inlet_has_audio(src_id, 0, box_lookup, sig_in, {}):
        return
    ops = (("mul", k),) + ops
    for edge in ctrl_in.get((src_id, 0), ()):
        seeds.append((edge.src, edge.outlet, ops, False, False))
        seed_via.append((edge.dst, edge.inlet))
    for edge in sig_in.get((src_id, 0), ()):
        _ramp_seeds(edge.src, ops, box_lookup, ctrl_in, sig_in, seeds, seed_via, seen)


def _trace_gain_inlet(box_lookup, ctrl_in, gain_id, gain_name, inlet, seeds, seed_via=None) -> list:
    """The PD-4 backward BFS for one (gain box, inlet); see the caller.

    *seed_via* gives each seed's consumer cord ``(dst, inlet)`` (Q39). Every
    enqueued state records the consumer cords it was reached through, and
    every :func:`reach` records the source's path cords, op chains, kind and
    into_line flag; :func:`_gain_fix` builds the quick-fix payload from them.
    """
    # source id -> [lo, hi, via, order]
    unsafe: dict = {}
    seen: set = set()
    queue = deque((state, 0) for state in seeds)
    states = 0
    via: dict = {}  # state -> {(consumer dst, inlet)} (Q39)
    for i, state in enumerate(seeds):
        if seed_via is not None and i < len(seed_via):
            via.setdefault(state, set()).add(seed_via[i])
    # source id -> {"states": {state}, "ops": {ops}, "kind", "into_line"} (Q39);
    # the path cords are read from ``via`` after the walk, when it is complete
    info: dict = {}

    def note(state, kind):
        src_id, _outlet, ops, into_line, _crossed = state
        entry = info.setdefault(src_id, {"states": set(), "ops": set(), "kind": kind, "into_line": False})
        entry["states"].add(state)
        entry["ops"].add(ops)
        entry["into_line"] = entry["into_line"] or bool(into_line)
        if entry["kind"] != kind:
            entry["kind"] = None

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
                nxt = (edge.src, edge.outlet, ops, into_line, crossed)
                via.setdefault(nxt, set()).add((edge.dst, edge.inlet))
                queue.append((nxt, hops + 1))

    truncated = False  # a bounded walk gives no fix (Q39)
    while queue:
        state, hops = queue.popleft()
        if state in seen or hops > _TRACE_HOP_LIMIT:
            truncated = truncated or state not in seen
            continue
        seen.add(state)
        states += 1
        if states > _TRACE_STATE_CAP:
            truncated = True
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
                note(state, "const")
                reach(box_id, (min(numbers), max(numbers)), ops, crossed)
            if follow:
                feeders(box_id, (0,), ops, False, crossed, hops)
            continue

        bounds = _bounded_source(box)
        if bounds is not None:
            note(state, "bounded")
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
                note(state, "const")
                reach(box_id, (kind[1], kind[1]), ops, crossed)
                continue
            feeders(box_id, (0,), ops, False, crossed, hops)
            continue

        if name in ("f", "float", "i", "int"):
            args = walk.box_args(box)
            value = _num(args[0]) if args else None
            if value is not None:
                note(state, "const")
                reach(box_id, (value, value), ops, crossed)
            feeders(box_id, (0, 1), ops, False, crossed, hops)
            continue
        # anything else: unknown range, the trace stops here (PD-4 rule 6)

    results = []
    for src_id, (lo, hi, crossed, _order) in sorted(unsafe.items(), key=lambda kv: kv[1][3]):
        src_box = box_lookup.get(src_id)
        label = _gain_source_label(src_box)
        via_text = " via line~" if crossed else ""
        peak = max(abs(lo), abs(hi))
        results.append(CriticResult(
            "blocker",
            f"Unsafe gain source: {label} ({src_id}) reaches '{gain_name}' "
            f"({gain_id}) inlet {inlet}{via_text} with values up to {peak:g} "
            f"(range {lo:g} to {hi:g}) -- gain inputs must stay within 0.0-1.0",
            _UNSAFE_GAIN_SUGGESTION,
            rule="unsafe_gain_sources",
            box_ids=finding_ids(src_id, gain_id),
            port=inlet,
            fix=None if truncated else _gain_fix(box_lookup, src_id, src_box, info.get(src_id), via),
        ))
    return results


def _gain_fix(box_lookup, src_id, src_box, entry, via):
    """insert_gain_normalizer for one unsafe source, or None (Q39).

    Requires exactly one distinct traced cord out of the source and every
    recorded op chain keeping [0.0, 1.0] within [-1.0, 1.0]. A bounded
    source (:func:`_bounded_source`, its own bounds, lo < hi) gets
    ``scale <lo> <hi> 0. 1.``; a constant source (message numbers, trigger
    constant, f / int argument) gets ``clip 0. 1.``, except a message that
    feeds line~ directly (its odd atoms are ramp times).
    """
    if not entry or not isinstance(src_box, dict):
        return None
    cords = {
        (state[1], dst, dst_inlet)
        for state in entry["states"]
        for dst, dst_inlet in via.get(state, ())
    }
    if len(cords) != 1:
        return None
    for ops in entry["ops"]:
        value = _apply_ops((0.0, 1.0), ops)
        if value is None or value[0] < -1.0 or value[1] > 1.0:
            return None
    kind = entry["kind"]
    if kind == "bounded":
        bounds = _bounded_source(src_box)
        if bounds is None or not bounds[0] < bounds[1]:
            return None
        text = f"scale {max_float(bounds[0])} {max_float(bounds[1])} 0. 1."
    elif kind == "const":
        if walk.box_maxclass(src_box) == "message" and entry["into_line"]:
            return None
        text = "clip 0. 1."
    else:
        return None
    ((outlet, dst_id, dst_inlet),) = tuple(cords)
    if not isinstance(outlet, int) or not isinstance(dst_inlet, int):
        return None
    dst_box = box_lookup.get(dst_id)
    return gain_normalizer_fix(
        src_id, outlet, walk.box_name(src_box),
        dst_id, dst_inlet, walk.box_name(dst_box) if dst_box else dst_id, text,
    )
