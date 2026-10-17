"""GenExpr code builder, .gendsp file generation, and JavaScript code generators.

Provides tools for building syntactically correct GenExpr DSP code,
generating standalone .gendsp files with correct patcher structure,
and generating Node for Max (N4M) and js object (Legacy Engine, ES5) JavaScript.

Exports:
- parse_genexpr_io: Extract input/output counts from GenExpr code
- build_genexpr: Build formatted GenExpr code with Params and sections
- generate_gendsp: Generate a complete .gendsp JSON dict
- generate_n4m_script: Generate Node for Max JavaScript with CommonJS require
  (dict names become valid, unique JS identifiers; literals JSON-escaped)
- generate_js_script: Generate js object (Legacy Engine, ES5) JavaScript with
  handlers (``anything()`` reads ``messagename`` and ``arrayfromargs(arguments)``)
"""

from __future__ import annotations

import copy
import json
import re

from src.maxpat.defaults import DEFAULT_PATCHER_PROPS, FONT_NAME, FONT_SIZE, GEN_PATCHER_BGCOLOR
from src.maxpat.genexpr_parse import io_counts, line_comment_starts, mask, statements


def parse_genexpr_io(code: str) -> tuple[int, int]:
    """Extract input and output counts from GenExpr code.

    Scans for ``in1``, ``in2``, ... and ``out1``, ``out2``, ... with
    word-boundary-aware regexes (so ``index`` / ``input`` never match) on
    the comment/string mask from :mod:`src.maxpat.genexpr_parse`, so I/O
    names inside ``//`` / ``/* */`` comments and string literals are
    ignored (Q22 / G2: ``// mix in4 and out3`` no longer yields 4 inlets).

    Args:
        code: GenExpr source code string.

    Returns:
        (num_inputs, num_outputs) tuple. Returns (0, 0) if none found.
    """
    return io_counts(code)


def build_genexpr(
    params: list[dict],
    code_body: str,
    num_inputs: int = 1,
    num_outputs: int = 1,
) -> str:
    """Build a complete, well-formatted GenExpr code string.

    Follows the project's locked style decisions:
    - Section headers with ``// === SECTION_NAME ===`` format
    - Full Param range specs: ``Param name(default, min=min_val, max=max_val);``
    - Descriptive variable names in code_body

    Args:
        params: List of parameter dicts, each with keys:
            ``name``, ``default``, ``min``, ``max``.
        code_body: The DSP logic section (raw GenExpr code). May already
            contain ``out1 = ...`` lines.
        num_inputs: Number of inputs (informational, not used in output).
        num_outputs: Number of outputs (informational, not used in output).

    Returns:
        Formatted GenExpr code string.
    """
    sections: list[str] = []

    # Parameters section
    if params:
        lines = ["// === PARAMETERS ==="]
        for p in params:
            name = p["name"]
            default = p["default"]
            min_val = p["min"]
            max_val = p["max"]
            lines.append(f"Param {name}({default}, min={min_val}, max={max_val});")
        sections.append("\n".join(lines))

    # Code body section
    if code_body.strip():
        sections.append(code_body.strip())

    return "\n\n".join(sections) + "\n"


_TYPE_ORDER = {"Param": 0, "History": 1, "Delay": 2, "Buffer": 3, "Data": 3}
_METHOD_CALL = re.compile(r"\w+\.\w+\(")


def _is_expression_stmt(st) -> bool:
    return st.kind != "decl" and ("=" in st.text or _METHOD_CALL.search(st.text) is not None)


def reorder_genexpr_declarations(code: str) -> str:
    """Reorder GenExpr code so all declarations precede expressions.

    GenExpr requires Param, History, Delay, Buffer, and Data declarations
    to appear before any expression or assignment. This works on whole
    STATEMENTS from :mod:`src.maxpat.genexpr_parse` (Q22 / G1), not lines:

    * Only depth-0 declarations move; a declaration inside a brace block
      (a function body) is never touched.
    * A declaration inside a ``/* */`` or ``//`` comment is not a statement,
      so it stays inside its comment, in place.
    * A multi-line ``Param g(0.5,\n  min=0, max=1);`` moves as one verbatim
      piece, together with the whole-line ``//`` comments directly above it
      and a trailing comment on its last line.

    Pieces are emitted grouped Param, History, Delay, Buffer/Data (stable
    within each group), then one blank line, then the remaining code. Every
    piece is sliced from the ORIGINAL text, so comments survive.

    If no depth-0 declaration follows an expression statement, the input is
    returned byte-identical.

    Args:
        code: GenExpr source code string.

    Returns:
        Reordered GenExpr code string.
    """
    if not isinstance(code, str) or not code:
        return code

    stmts = statements(code)
    seen_expr = False
    needed = False
    for st in stmts:
        if st.kind == "decl":
            if st.depth == 0 and seen_expr:
                needed = True
                break
        elif _is_expression_stmt(st):
            seen_expr = True
    if not needed:
        return code

    m = mask(code)
    comment_starts = line_comment_starts(code)

    def line_start(pos: int) -> int:
        return code.rfind("\n", 0, pos) + 1

    def line_end(pos: int) -> int:
        e = code.find("\n", pos)
        return len(code) if e < 0 else e

    def whole_line_comment(ls: int, le: int) -> bool:
        if m[ls:le].strip():
            return False
        k = ls
        while k < le and code[k] in " \t\r":
            k += 1
        return k in comment_starts

    pieces: list[tuple[int, int, int]] = []  # (start, end, group)
    for st in stmts:
        if st.kind != "decl" or st.depth != 0:
            continue
        dtype = st.text.split(None, 1)[0]
        group = _TYPE_ORDER.get(dtype, 3)
        ps = st.start
        ls = line_start(ps)
        if not m[ls:ps].strip():
            ps = ls
            while ps > 0:
                prev_ls = line_start(ps - 1)
                prev_le = ps - 1
                if prev_ls == ps or not whole_line_comment(prev_ls, prev_le):
                    break
                if pieces and prev_ls < pieces[-1][1]:
                    break
                ps = prev_ls
        pe = st.end
        le = line_end(pe)
        if not m[pe:le].strip():
            pe = le + 1 if le < len(code) else le
        pieces.append((ps, pe, group))

    removed = [False] * len(code)
    for ps, pe, _g in pieces:
        for k in range(ps, pe):
            removed[k] = True

    remainder: list[str] = []
    pos = 0
    n = len(code)
    while pos < n:
        nl = code.find("\n", pos)
        content_end = n if nl < 0 else nl
        kept = "".join(code[k] for k in range(pos, content_end) if not removed[k])
        touched = any(removed[k] for k in range(pos, content_end + (0 if nl < 0 else 1)))
        if touched and not kept.strip():
            pass  # left whitespace-only by a removal: drop the line
        else:
            remainder.append(kept + ("" if nl < 0 else "\n"))
        pos = content_end + 1

    rest = "".join(remainder)
    while rest:
        nl = rest.find("\n")
        if nl < 0:
            if not rest.strip():
                rest = ""
            break
        if rest[:nl].strip():
            break
        rest = rest[nl + 1:]

    out: list[str] = []
    for gid in (0, 1, 2, 3):
        for ps, pe, g in pieces:
            if g != gid:
                continue
            piece = code[ps:pe]
            if not piece.endswith("\n"):
                piece += "\n"
            out.append(piece)
    return "".join(out) + "\n" + rest


def generate_gendsp(
    code: str,
    num_inputs: int | None = None,
    num_outputs: int | None = None,
) -> dict:
    """Generate a complete .gendsp JSON dict.

    Builds the standard .gendsp file structure: a patcher wrapper containing
    ``in`` objects, a codebox with GenExpr code, ``out`` objects, and
    patchlines connecting them.

    Args:
        code: GenExpr source code for the codebox.
        num_inputs: Number of inputs. Auto-detected from code if None.
        num_outputs: Number of outputs. Auto-detected from code if None.

    Returns:
        Complete .gendsp JSON-serializable dict with ``"patcher"`` top-level key.
    """
    # Auto-detect I/O from code if not specified
    if num_inputs is None or num_outputs is None:
        detected_in, detected_out = parse_genexpr_io(code)
        if num_inputs is None:
            num_inputs = detected_in
        if num_outputs is None:
            num_outputs = detected_out

    # Build patcher properties
    patcher = copy.deepcopy(DEFAULT_PATCHER_PROPS)
    patcher["bgcolor"] = list(GEN_PATCHER_BGCOLOR)
    patcher["rect"] = [100.0, 100.0, 600.0, 450.0]

    boxes: list[dict] = []
    lines: list[dict] = []
    next_id = 1

    def gen_id() -> str:
        nonlocal next_id
        box_id = f"obj-{next_id}"
        next_id += 1
        return box_id

    # Create in objects (positioned at top)
    in_ids: list[str] = []
    for i in range(num_inputs):
        box_id = gen_id()
        in_ids.append(box_id)
        boxes.append({
            "box": {
                "maxclass": "newobj",
                "text": f"in {i + 1}",
                "id": box_id,
                "numinlets": 0,
                "numoutlets": 1,
                "outlettype": [""],
                "patching_rect": [50.0 + i * 80.0, 20.0, 30.0, 22.0],
                "fontname": FONT_NAME,
                "fontsize": FONT_SIZE,
            }
        })

    # Create codebox
    codebox_id = gen_id()
    boxes.append({
        "box": {
            "maxclass": "codebox",
            "id": codebox_id,
            "code": code,
            "numinlets": num_inputs,
            "numoutlets": num_outputs,
            "outlettype": [""] * num_outputs,
            "patching_rect": [50.0, 80.0, 400.0, 200.0],
            "fontname": FONT_NAME,
            "fontsize": FONT_SIZE,
        }
    })

    # Create out objects (positioned at bottom)
    out_ids: list[str] = []
    for i in range(num_outputs):
        box_id = gen_id()
        out_ids.append(box_id)
        boxes.append({
            "box": {
                "maxclass": "newobj",
                "text": f"out {i + 1}",
                "id": box_id,
                "numinlets": 1,
                "numoutlets": 0,
                "outlettype": [],
                "patching_rect": [50.0 + i * 80.0, 320.0, 30.0, 22.0],
                "fontname": FONT_NAME,
                "fontsize": FONT_SIZE,
            }
        })

    # Create patchlines: in -> codebox
    for i, in_id in enumerate(in_ids):
        lines.append({
            "patchline": {
                "source": [in_id, 0],
                "destination": [codebox_id, i],
            }
        })

    # Create patchlines: codebox -> out
    for i, out_id in enumerate(out_ids):
        lines.append({
            "patchline": {
                "source": [codebox_id, i],
                "destination": [out_id, 0],
            }
        })

    patcher["boxes"] = boxes
    patcher["lines"] = lines

    return {"patcher": patcher}


def generate_n4m_script(
    handlers: list[dict],
    dict_access: list[str] | None = None,
) -> str:
    """Generate a complete Node for Max JavaScript string.

    Produces CommonJS-style code with ``require("max-api")``, handler
    registrations via ``maxAPI.addHandler``, and optional async dict
    access functions with try/catch error handling.

    Args:
        handlers: List of handler dicts, each with keys:
            ``name`` (str), ``args`` (list[str]), ``body`` (str).
        dict_access: Optional list of dict names to generate async
            getter/setter helper functions for.

    Dict helper names (Q31 / G6): each dict name (``str(name)``; exact
    duplicates emitted once) maps to the suffix
    ``re.sub(r"[^A-Za-z0-9_$]", "_", name)`` (``_`` when empty), giving
    ``getDict_<suffix>()`` / ``setDict_<suffix>(data)``; a suffix already
    used gets ``_2``, ``_3``, ... (``my-dict`` -> ``getDict_my_dict``, then
    ``my_dict`` -> ``getDict_my_dict_2``). Every dict-name string literal
    and post-message prefix is ``json.dumps``-escaped, so a name never
    becomes code. Plain names keep their function names and messages.

    Returns:
        Complete N4M JavaScript source string.
    """
    sections: list[str] = []

    # Require statement
    sections.append('const maxAPI = require("max-api");')

    # Dict access helpers (async with try/catch)
    if dict_access:
        sections.append("")
        sections.append("// === DICT ACCESS ===")
        seen_names: set[str] = set()
        used_suffixes: set[str] = set()
        for raw_name in dict_access:
            dict_name = str(raw_name)
            if dict_name in seen_names:
                continue
            seen_names.add(dict_name)

            base = re.sub(r"[^A-Za-z0-9_$]", "_", dict_name) or "_"
            suffix = base
            n = 2
            while suffix in used_suffixes:
                suffix = f"{base}_{n}"
                n += 1
            used_suffixes.add(suffix)

            name_lit = json.dumps(dict_name)
            get_err = json.dumps("Error getting dict " + dict_name + ": ")
            set_err = json.dumps("Error setting dict " + dict_name + ": ")
            sections.append(f"""
// dict {name_lit} -> getDict_{suffix}() / setDict_{suffix}(data)
async function getDict_{suffix}() {{
    try {{
        const data = await maxAPI.getDict({name_lit});
        return data;
    }} catch (e) {{
        maxAPI.post({get_err} + e.message);
        return null;
    }}
}}

async function setDict_{suffix}(data) {{
    try {{
        await maxAPI.setDict({name_lit}, data);
    }} catch (e) {{
        maxAPI.post({set_err} + e.message);
    }}
}}""".rstrip())

    # Handlers
    sections.append("")
    sections.append("// === HANDLERS ===")
    for handler in handlers:
        name = handler["name"]
        args = handler.get("args", [])
        body = handler.get("body", "")
        args_str = ", ".join(args)

        # Indent body lines
        body_lines = body.strip().split("\n")
        indented_body = "\n".join(f"    {line}" for line in body_lines)

        sections.append(f"""
maxAPI.addHandler("{name}", ({args_str}) => {{
{indented_body}
}});""".rstrip())

    return "\n".join(sections) + "\n"


def generate_js_script(
    num_inlets: int = 1,
    num_outlets: int = 1,
    handlers: list[dict] | None = None,
) -> str:
    """Generate a complete js object (Legacy Engine, ES5) JavaScript string.

    Produces code with ``inlets``/``outlets`` declarations and handler
    functions. If no handlers are specified, generates default handlers
    for bang, msg_int, msg_float, and list with placeholder bodies.

    Args:
        num_inlets: Number of inlets to declare.
        num_outlets: Number of outlets to declare.
        handlers: Optional list of handler dicts, each with keys:
            ``type`` (str -- one of bang, msg_int, msg_float, list,
            anything) and ``body`` (str).
            If None, default handlers are generated.

    ``anything`` handlers (Q31 / G6, J1): MAX passes the selector in the
    ``messagename`` global and the arguments in ``arguments``, never as
    named parameters, so the generated ``function anything() {`` takes no
    parameters and its body starts with
    ``var args = arrayfromargs(arguments);``; the caller's body reads
    ``messagename`` and ``args``. Output is ES5 only (``var`` /
    ``function``).

    Returns:
        Complete js object (Legacy Engine, ES5) JavaScript source string.
    """
    sections: list[str] = []

    # I/O declarations
    sections.append(f"inlets = {num_inlets};")
    sections.append(f"outlets = {num_outlets};")

    if handlers is None:
        # Default handlers with placeholder bodies
        handlers = [
            {"type": "bang", "body": "outlet(0, \"bang\");"},
            {"type": "msg_int", "body": "outlet(0, v);"},
            {"type": "msg_float", "body": "outlet(0, v);"},
            {"type": "list", "body": "outlet(0, arrayfromargs(arguments));"},
        ]

    # Standard argument signatures for handler types
    _handler_args = {
        "bang": "",
        "msg_int": "v",
        "msg_float": "v",
        "list": "",
        "anything": "",
    }

    for handler in handlers:
        handler_type = handler["type"]
        body = handler.get("body", "")
        args_str = _handler_args.get(handler_type, "")

        # Indent body lines
        body_lines = body.strip().split("\n")
        if handler_type == "anything":
            body_lines = ["var args = arrayfromargs(arguments);"] + body_lines
        indented_body = "\n".join(f"    {line}" for line in body_lines)

        sections.append(f"""
function {handler_type}({args_str}) {{
{indented_body}
}}""".rstrip())

    return "\n".join(sections) + "\n"
