"""One GenExpr tokenizer and statement parser (Q22 / S5).

Replaces the three regex copies that used to live in ``codegen``
(``parse_genexpr_io``, ``reorder_genexpr_declarations``), ``rnbo``
(``parse_genexpr_params``) and ``code_validation`` (``validate_genexpr``).
The copies disagreed, and two corrupted user code: I/O counted inside
comments (G2), declarations revived from ``/* */`` comments and multi-line
Params split by the line-based reorder (G1), and Param parsing that failed on
whitespace, kwargs and non-literal defaults (G4).

Contracts:

* **Offset-preserving.** :func:`mask` returns a string of the same length as
  its input in which every comment character and every string-literal content
  character is a space; newlines (``\\n`` and ``\\r``) are kept. Offsets and
  line numbers on the mask therefore map 1:1 onto the original text, so
  callers run their regexes on the mask and slice the ORIGINAL text by the
  spans the parser returns.
* **Never raises.** Every public function accepts any input (a non-str is
  treated as ``""``) and handles unterminated comments and strings,
  unbalanced parens and braces, ``for(;;)`` headers and CRLF text.
* **Stdlib only.** Nothing from ``src.maxpat`` is imported, so ``codegen``,
  ``rnbo`` and ``code_validation`` can import this module at top level
  without an import cycle.
"""

from __future__ import annotations

import bisect
import re
from dataclasses import dataclass

DECL_TYPES = ("Param", "History", "Delay", "Buffer", "Data")

# Q22's 13 lower-case constant names (dsp_sim.genexpr_interp asserts this
# exact set against its value table).
CONSTANTS = frozenset({
    "e", "pi", "twopi", "halfpi", "invpi", "ln2", "ln10", "log10e", "log2e",
    "sqrt2", "sqrt1_2", "degtorad", "radtodeg",
})

# Every GenExpr built-in constant name: CONSTANTS, phi (Gen refpage
# gen_common_phi.maxref.xml) and the upper-case aliases the Max 9 Gen
# operator guide lists (gen_common_operators.json: PI, TWOPI, ..., PHI, E).
# Assigning to any of them has no effect -- the constant wins silently
# (review WR-04, quick 261022-ud6). validate_genexpr Checks 11 and 14 use it.
BUILTIN_CONSTANTS = (CONSTANTS | {"phi"}) | frozenset(
    n.upper() for n in CONSTANTS | {"phi"})

_DECL_RE = re.compile(r"(Param|History|Delay|Buffer|Data)\s")
_IDENT_RE = re.compile(r"\s*([A-Za-z_]\w*)")
_BARE_IDENT_RE = re.compile(r"[A-Za-z_]\w*$")
_KWARG_RE = re.compile(r"\s*([A-Za-z_]\w*)\s*=(?!=)")
_NUM_RE = re.compile(r"[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?$")
_IN_RE = re.compile(r"\bin(\d+)\b")
_OUT_RE = re.compile(r"\bout(\d+)\b")
_BLOCK_KEYWORDS = ("for", "if", "else", "while")


def _str(code) -> str:
    return code if isinstance(code, str) else ""


# ---------------------------------------------------------------------------
# Mask
# ---------------------------------------------------------------------------

def _scan(code: str) -> tuple[str, set]:
    """Single left-to-right scan. Returns (mask, line-comment start offsets)."""
    out = list(code)
    n = len(code)
    line_comment_starts: set = set()
    i = 0
    state = 0  # 0 normal, 1 line comment, 2 block comment, 3 string
    while i < n:
        c = code[i]
        if state == 0:
            if c == "/" and i + 1 < n and code[i + 1] == "/":
                line_comment_starts.add(i)
                out[i] = out[i + 1] = " "
                i += 2
                state = 1
                continue
            if c == "/" and i + 1 < n and code[i + 1] == "*":
                out[i] = out[i + 1] = " "
                i += 2
                state = 2
                continue
            if c == '"':
                state = 3
            i += 1
        elif state == 1:
            if c == "\n":
                state = 0
            elif c != "\r":
                out[i] = " "
            i += 1
        elif state == 2:
            if c == "*" and i + 1 < n and code[i + 1] == "/":
                out[i] = out[i + 1] = " "
                i += 2
                state = 0
                continue
            if c not in "\r\n":
                out[i] = " "
            i += 1
        else:  # string
            if c == "\\" and i + 1 < n:
                out[i] = " "
                if code[i + 1] not in "\r\n":
                    out[i + 1] = " "
                i += 2
                continue
            if c == '"':
                state = 0
            elif c not in "\r\n":
                out[i] = " "
            i += 1
    return "".join(out), line_comment_starts


def mask(code) -> str:
    """Return *code* with comments and string contents blanked to spaces.

    Same length as *code*. ``//`` and ``/* */`` comment characters become
    spaces except ``\\n`` / ``\\r``; double-quoted string contents become
    spaces while the quotes stay (a backslash escapes the next character).
    An unterminated comment or string runs to EOF. ``//`` inside a string,
    ``"`` inside a comment and ``/*`` inside ``//`` are inert.
    """
    return _scan(_str(code))[0]


# ---------------------------------------------------------------------------
# Statements
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Stmt:
    """One GenExpr statement.

    start/end: span in the ORIGINAL text (end exclusive, includes the ``;``
    or ``{`` that ended it). text: the masked slice. depth: brace depth at
    the start. line: 1-based line of the first non-space character. kind:
    "decl" | "assign" | "expr" | "header". parents: enclosing blocks'
    keywords, outermost first ("for", "if", "else", "while", else "func").
    terminated: True when the statement ended with ``;``.
    """

    start: int
    end: int
    text: str
    depth: int
    line: int
    kind: str
    parents: tuple
    terminated: bool


def _find_assign(text: str) -> tuple[int, int]:
    """(op_start, op_end) of the first paren-depth-0 assignment operator in
    *text* (``=``, ``+=``, ``-=``, ``*=``, ``/=``), or (-1, -1)."""
    depth = 0
    n = len(text)
    for i, c in enumerate(text):
        if c in "([":
            depth += 1
        elif c in ")]":
            if depth > 0:
                depth -= 1
        elif c == "=" and depth == 0:
            prev = text[i - 1] if i > 0 else ""
            nxt = text[i + 1] if i + 1 < n else ""
            if nxt == "=" or prev in ("=", "<", ">", "!"):
                continue
            if prev in ("+", "-", "*", "/", "%"):
                return i - 1, i + 1
            return i, i + 1
    return -1, -1


def _keyword(text: str) -> str:
    m = _IDENT_RE.match(text)
    if m and m.group(1) in _BLOCK_KEYWORDS:
        return m.group(1)
    return "func"


def _line_starts(code: str) -> list:
    starts = [0]
    for i, c in enumerate(code):
        if c == "\n":
            starts.append(i + 1)
    return starts


def _line_of(starts: list, pos: int) -> int:
    return bisect.bisect_right(starts, pos)


def _statements_from(code: str, m: str) -> list:
    starts = _line_starts(code)
    stmts: list = []
    stack: list = []
    paren = 0
    seg = 0

    def emit(a: int, b: int, ended_by: str) -> None:
        s = a
        while s < b and m[s].isspace():
            s += 1
        if s >= b:
            return
        text = m[s:b]
        stripped = text.strip()
        if _DECL_RE.match(stripped):
            kind = "decl"
        elif ended_by == "{":
            kind = "header"
        elif _find_assign(stripped)[0] >= 0:
            kind = "assign"
        else:
            kind = "expr"
        stmts.append(Stmt(
            start=s, end=b, text=text, depth=len(stack),
            line=_line_of(starts, s), kind=kind, parents=tuple(stack),
            terminated=(ended_by == ";"),
        ))

    for i, c in enumerate(m):
        if c == "(":
            paren += 1
        elif c == ")":
            if paren > 0:
                paren -= 1
        elif c == ";" and paren == 0:
            emit(seg, i + 1, ";")
            seg = i + 1
        elif c == "{":
            text = m[seg:i]
            emit(seg, i + 1, "{")
            stack.append(_keyword(text))
            paren = 0
            seg = i + 1
        elif c == "}":
            emit(seg, i, "}")
            if stack:
                stack.pop()
            paren = 0
            seg = i + 1
    emit(seg, len(m), "")
    return stmts


def statements(code) -> list:
    """Split GenExpr *code* into :class:`Stmt` records (works on the mask).

    A statement ends at ``;`` at paren depth 0 (a ``for (...;...;...)``
    header stays whole) or at ``{`` (a "header", which pushes its keyword).
    At ``}`` any pending non-blank text becomes an unterminated statement;
    pending text at EOF does too. Whitespace-only segments are dropped and
    depths never go below 0.
    """
    code = _str(code)
    try:
        return _statements_from(code, _scan(code)[0])
    except Exception:  # pragma: no cover - defensive, never raise
        return []


def split_args(s) -> list:
    """Split *s* on top-level commas (paren- and bracket-aware)."""
    s = _str(s)
    parts: list = []
    depth = 0
    cur = 0
    for i, c in enumerate(s):
        if c in "([":
            depth += 1
        elif c in ")]":
            if depth > 0:
                depth -= 1
        elif c == "," and depth == 0:
            parts.append(s[cur:i])
            cur = i + 1
    parts.append(s[cur:])
    return parts


def _balanced_group(text: str, open_pos: int) -> int:
    """Index just past the paren that closes the one at *open_pos*, or
    len(text) when it never closes."""
    depth = 0
    for i in range(open_pos, len(text)):
        c = text[i]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return i + 1
    return len(text)


def _paren_content(text: str, open_pos: int) -> str:
    """Text inside the paren group opened at *open_pos* (to EOF when it
    never closes)."""
    depth = 0
    for i in range(open_pos, len(text)):
        c = text[i]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return text[open_pos + 1:i]
    return text[open_pos + 1:]


def _decl_items(stmt: Stmt) -> tuple:
    """(type, [(name, args_or_None), ...]) of a decl statement."""
    text = stmt.text.strip()
    if text.endswith(";"):
        text = text[:-1]
    m = _DECL_RE.match(text)
    if not m:
        return "", []
    dtype = m.group(1)
    items = []
    for item in split_args(text[m.end():]):
        im = _IDENT_RE.match(item)
        if not im:
            continue
        name = im.group(1)
        rest = item[im.end():]
        p = rest.find("(")
        args = None
        if p >= 0 and not rest[:p].strip():
            args = _paren_content(rest, p)
        items.append((name, args))
    return dtype, items


def declarations(code) -> list:
    """(type, names, stmt) for every "decl" statement at any depth.

    *names* holds every top-level comma item's leading identifier, so
    ``History a(0), b(0);`` gives ``["a", "b"]``.
    """
    out: list = []
    for st in statements(code):
        if st.kind != "decl":
            continue
        dtype, items = _decl_items(st)
        if dtype:
            out.append((dtype, [name for name, _a in items], st))
    return out


def _literal(value: str):
    v = value.strip()
    if _NUM_RE.match(v):
        try:
            return float(v)
        except ValueError:
            return None
    return None


def parse_params(code) -> list:
    """One dict per Param name with exactly the keys name, default, min, max.

    default is ``float()`` of the first positional argument, or None when it
    is absent or not a plain numeric literal. min/max come from ``min =`` /
    ``max =`` kwargs anywhere in the arguments; None when absent or
    non-literal.
    """
    out: list = []
    for st in statements(code):
        if st.kind != "decl":
            continue
        dtype, items = _decl_items(st)
        if dtype != "Param":
            continue
        for name, args in items:
            default = mn = mx = None
            seen_positional = False
            if args is not None:
                for arg in split_args(args):
                    km = _KWARG_RE.match(arg)
                    if km:
                        key = km.group(1)
                        val = _literal(arg[km.end():])
                        if key == "min":
                            mn = val
                        elif key == "max":
                            mx = val
                        continue
                    if not seen_positional:
                        seen_positional = True
                        default = _literal(arg)
            out.append({"name": name, "default": default, "min": mn, "max": mx})
    return out


@dataclass(frozen=True)
class ParamItem:
    """One Param name of a declaration: its kwarg keys in order (``min``,
    ``max``, ...), whether it has an argument list, and its statement."""

    name: str
    kwargs: tuple
    has_args: bool
    stmt: Stmt


def param_items(code) -> list:
    """:class:`ParamItem` for every Param name (comma lists included).

    Kwarg keys come from the top-level comma items of the argument list
    (``name =`` at item start), so a call default such as
    ``Param g(max(1, 2), min=0, max=10)`` keeps both of its ranges
    (review IN-01).
    """
    out: list = []
    for st in statements(code):
        if st.kind != "decl":
            continue
        dtype, items = _decl_items(st)
        if dtype != "Param":
            continue
        for name, args in items:
            keys = []
            if args is not None:
                for arg in split_args(args):
                    km = _KWARG_RE.match(arg)
                    if km:
                        keys.append(km.group(1))
            out.append(ParamItem(name=name, kwargs=tuple(keys),
                                 has_args=args is not None, stmt=st))
    return out


_FUNC_HEADER_RE = re.compile(r"\s*([A-Za-z_]\w*)\s*\(([^()]*)\)\s*", re.S)


@dataclass(frozen=True)
class FuncDef:
    """A depth-0 GenExpr function definition.

    start/end: span in the ORIGINAL text from the name to just past the
    closing ``}`` (EOF when it never closes). line: 1-based line of the
    name. header: the header :class:`Stmt` (ends with the ``{``).
    """

    name: str
    start: int
    end: int
    line: int
    header: Stmt


def is_function_header(st) -> bool:
    """True for a depth-0 header ``name(args) {`` that is not if/for/while/else."""
    if not isinstance(st, Stmt) or st.kind != "header" or st.depth != 0:
        return False
    text = st.text.rstrip()
    if text.endswith("{"):
        text = text[:-1]
    m = _FUNC_HEADER_RE.fullmatch(text)
    return bool(m) and m.group(1) not in _BLOCK_KEYWORDS


def _block_end(m: str, open_pos: int) -> int:
    depth = 0
    for i in range(open_pos, len(m)):
        c = m[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i + 1
    return len(m)


def function_defs(code) -> list:
    """:class:`FuncDef` for every depth-0 function definition, in order.

    A header is ``name(args)`` + ``{`` (K&R or Allman, comments allowed in
    between) whose name is not ``if`` / ``for`` / ``while`` / ``else``.
    The Max user guide ("Defining GenExpr Functions") requires functions
    before all statements; every Gen codebox Cycling '74 ships puts them
    first, then declarations, then statements.
    """
    code = _str(code)
    try:
        m = _scan(code)[0]
        out: list = []
        for st in statements(code):
            if not is_function_header(st):
                continue
            name = _FUNC_HEADER_RE.match(st.text).group(1)
            out.append(FuncDef(name=name, start=st.start, end=_block_end(m, st.end - 1),
                               line=st.line, header=st))
        return out
    except Exception:  # pragma: no cover - defensive, never raise
        return []


def _strip_prefixes(text: str) -> int:
    """Offset into *text* after a leading ``else`` and/or ``if``/``while``/
    ``for`` keyword with its balanced paren group."""
    pos = 0
    for _ in range(8):
        m = _IDENT_RE.match(text, pos)
        if not m:
            break
        word = m.group(1)
        if word == "else":
            pos = m.end()
            continue
        if word in ("if", "while", "for"):
            p = m.end()
            while p < len(text) and text[p].isspace():
                p += 1
            if p < len(text) and text[p] == "(":
                pos = _balanced_group(text, p)
                continue
        break
    return pos


def _lhs_names(text: str, base: int, starts: list, out: dict) -> None:
    """Record bare-identifier LHS names of an assignment in *text*.

    *base* is text's offset in the original code (for line numbers).
    """
    a, _b = _find_assign(text)
    if a < 0:
        return
    lhs = text[:a]
    offset = 0
    for item in split_args(lhs):
        name = item.strip()
        if _BARE_IDENT_RE.match(name):
            pos = base + offset + item.find(name)
            out.setdefault(name, []).append(_line_of(starts, pos))
        offset += len(item) + 1


def _split_top(text: str, sep: str) -> list:
    """Split on *sep* at paren depth 0, returning (offset, part) pairs."""
    parts = []
    depth = 0
    cur = 0
    for i, c in enumerate(text):
        if c in "([":
            depth += 1
        elif c in ")]":
            if depth > 0:
                depth -= 1
        elif c == sep and depth == 0:
            parts.append((cur, text[cur:i]))
            cur = i + 1
    parts.append((cur, text[cur:]))
    return parts


def _for_parts(text: str):
    """(content_offset, [(offset, part), ...]) of a ``for (...)`` header's
    paren content split on top-level ``;``, or None."""
    m = _IDENT_RE.match(text)
    if not m or m.group(1) != "for":
        return None
    p = text.find("(", m.end())
    if p < 0 or text[m.end():p].strip():
        return None
    return p + 1, _split_top(_paren_content(text, p), ";")


def assigned_names(code) -> dict:
    """name -> 1-based lines of each assignment.

    Sources: every non-decl statement at any depth (after stripping a
    leading ``else`` and ``if``/``while``/``for`` keyword with its paren
    group), plus a ``for`` header's init and increment parts. The LHS may be
    a comma list (``a, b = peek(...)``); only bare identifiers count.
    Comparisons, ``kw=`` arguments inside parens and declarations are
    excluded.
    """
    code = _str(code)
    out: dict = {}
    try:
        starts = _line_starts(code)
        for st in statements(code):
            if st.kind == "decl":
                continue
            if st.kind == "header":
                fp = _for_parts(st.text)
                if fp is not None:
                    base, parts = fp
                    for idx in (0, 2):
                        if idx < len(parts):
                            off, part = parts[idx]
                            for sub_off, sub in _split_top(part, ","):
                                _lhs_names(sub, st.start + base + off + sub_off, starts, out)
                continue
            text = st.text
            pos = _strip_prefixes(text)
            _lhs_names(text[pos:], st.start + pos, starts, out)
    except Exception:  # pragma: no cover - defensive, never raise
        return out
    return out


def io_counts(code) -> tuple:
    """(max inN, max outN) on the mask; (0, 0) when none."""
    m = mask(code)
    max_in = max((int(n) for n in _IN_RE.findall(m)), default=0)
    max_out = max((int(n) for n in _OUT_RE.findall(m)), default=0)
    return (max_in, max_out)


def line_paren_depths(code) -> list:
    """For each ``code.split("\\n")`` line: (paren depth at line start, at
    line end), on the mask, clamped at 0. Braces reset the depth (recovery
    from an unbalanced paren)."""
    m = mask(code)
    out: list = []
    depth = 0
    for line in m.split("\n"):
        start = depth
        for c in line:
            if c == "(":
                depth += 1
            elif c == ")":
                if depth > 0:
                    depth -= 1
            elif c in "{}":
                depth = 0
        out.append((start, depth))
    return out


def line_comment_starts(code) -> set:
    """Offsets where a ``//`` line comment begins (outside strings and block
    comments). Used by the reorder to recognise whole-line ``//`` comments."""
    return _scan(_str(code))[1]
